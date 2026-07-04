"""
ATS filler — llena el formulario por SELECTOR conocido (de la API), no por visión.

Recibe la estructura del formulario (ats_forms.ATSForm) y las respuestas ya
resueltas (master_agent.answer_application) y las escribe con Playwright targeteando
cada campo por su `name` real. Maneja text/textarea/file y los dropdowns React-Select
de Greenhouse. Dos modos:
  - assist (default): llena todo y se DETIENE antes de enviar (screenshot para revisión).
  - submit: además clickea el botón de envío.

Sin visión, sin loop de 15 pasos: una pasada determinista.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Dict, List

from loguru import logger

CV_PATH = "data/cv_alejandro_en.pdf"


async def _fill_text(page, name: str, value: str) -> bool:
    # Selector por atributo [id="..."] maneja nombres con corchetes/puntos.
    for sel in (f'textarea[name="{name}"]', f'input[name="{name}"]',
                f'[id="{name}"]', f'textarea[id="{name}"]'):
        try:
            loc = page.locator(sel).first
            if await loc.count() > 0:
                await loc.fill(str(value), timeout=4000)
                # Disparar el setter nativo + eventos para que React registre el
                # valor (algunos inputs controlados ignoran el fill directo) y blur.
                await loc.evaluate(
                    """(el, v) => {
                        const proto = el.tagName === 'TEXTAREA'
                          ? window.HTMLTextAreaElement.prototype
                          : window.HTMLInputElement.prototype;
                        const setter = Object.getOwnPropertyDescriptor(proto, 'value').set;
                        setter.call(el, v);
                        el.dispatchEvent(new Event('input', {bubbles: true}));
                        el.dispatchEvent(new Event('change', {bubbles: true}));
                        el.blur();
                    }""",
                    str(value),
                )
                return True
        except Exception:
            continue
    return False


async def _fill_file(page, name: str, path: str) -> bool:
    for sel in (f'input[type="file"][name="{name}"]', f'input[type="file"]#{name}',
                'input[type="file"]'):
        try:
            loc = page.locator(sel).first
            if await loc.count() > 0:
                await loc.set_input_files(path, timeout=6000)
                return True
        except Exception:
            continue
    return False


async def _open_select(page, name: str) -> bool:
    """Abre el control React-Select del campo (por id con corchetes, o vía el label)."""
    base = name.rstrip("[]")
    for ctrl_sel in (
        f'[id="{name}"]',                       # input react-select (id con [] incluido)
        f'[id="{base}"]',
        f'label[for="{name}"] ~ * .select__control',
        f'label[for="{name}"]',                 # click en el label enfoca el control
    ):
        try:
            ctrl = page.locator(ctrl_sel).first
            if await ctrl.count() > 0:
                await ctrl.click(timeout=2500)
                await page.wait_for_timeout(300)
                return True
        except Exception:
            continue
    return False


async def _fill_select(page, name: str, labels: List[str]) -> bool:
    """Dropdown: <select> nativo, o React-Select (Greenhouse). Soporta multi."""
    # 1) select nativo (por atributo, maneja corchetes en el name)
    try:
        sel = page.locator(f'select[name="{name}"], select[id="{name}"]').first
        if await sel.count() > 0:
            await sel.select_option(label=[str(l) for l in labels], timeout=3000)
            return True
    except Exception:
        pass

    # 2) React-Select. Para multi, el menú sigue abierto entre clicks → abrir una vez.
    ok_any = False
    if not await _open_select(page, name):
        return False
    for lbl in labels:
        clicked = False
        for opt_sel in ('.select__option', '[role="option"]', '.select__menu-list div'):
            try:
                opt = page.locator(opt_sel, has_text=str(lbl)).first
                if await opt.count() > 0:
                    await opt.click(timeout=2500)
                    clicked = True
                    ok_any = True
                    break
            except Exception:
                continue
        if not clicked:
            # fallback: teclear el label y Enter
            try:
                await page.keyboard.type(str(lbl), delay=30)
                await page.wait_for_timeout(250)
                await page.keyboard.press("Enter")
                ok_any = True
            except Exception:
                pass
        await page.wait_for_timeout(200)
        # reabrir para el siguiente valor (por si el menú se cerró)
        if lbl != labels[-1]:
            await _open_select(page, name)
    # cerrar el menú
    try:
        await page.keyboard.press("Escape")
    except Exception:
        pass
    return ok_any


async def fill_greenhouse_application(
    url: str,
    answers: Dict[str, Dict],
    cv_path: str = CV_PATH,
    submit: bool = False,
    headless: bool = True,
) -> Dict:
    """Llena (y opcionalmente envía) un formulario de Greenhouse por selector."""
    from playwright.async_api import async_playwright

    abs_cv = str(Path(cv_path).resolve())
    result = {"filled": [], "failed": [], "skipped": [], "submitted": False, "status": "", "screenshot": ""}

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=headless,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
        )
        context = await browser.new_context(viewport={"width": 1280, "height": 1200})
        page = await context.new_page()
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=45000)
            await page.wait_for_timeout(3000)

            # Llenar en orden: primero archivos, luego texto, luego selects.
            order = {"file_cv": 0, "profile": 1, "llm": 1, "llm_fallback": 1}
            items = sorted(answers.items(), key=lambda kv: order.get(kv[1].get("source"), 1))

            for name, a in items:
                atype = a["type"]
                src = a.get("source")
                try:
                    if src == "file_cv" or atype == "file":
                        ok = await _fill_file(page, name, abs_cv)
                    elif atype in ("select_single", "select_multi"):
                        if a["value"] in (None, "", []):
                            result["skipped"].append(f"{a['label'][:40]} (sin respuesta)")
                            continue
                        labels = a["value"] if isinstance(a["value"], list) else [a["value"]]
                        ok = await _fill_select(page, name, [str(x) for x in labels])
                    else:
                        if a["value"] in (None, ""):
                            continue
                        ok = await _fill_text(page, name, a["value"])
                    (result["filled"] if ok else result["failed"]).append(
                        f"{a['label'][:40]} ({atype})")
                    await page.wait_for_timeout(200)
                except Exception as e:
                    result["failed"].append(f"{a['label'][:40]}: {str(e)[:50]}")

            await page.wait_for_timeout(800)
            shot = f"data/screenshots/ats_fill_{int(asyncio.get_event_loop().time())}.png"
            try:
                await page.screenshot(path=shot, full_page=True)
                result["screenshot"] = shot
            except Exception:
                pass

            if not submit:
                result["status"] = "assist_ready"
                logger.info(f"[ats_filler] ASSIST — llenado {len(result['filled'])} campos, "
                            f"{len(result['failed'])} fallidos. Revisar: {shot}")
            else:
                clicked = False
                for sel in ('button:has-text("Submit application")',
                            'button:has-text("Submit Application")',
                            'button[type="submit"]',
                            'input[type="submit"]'):
                    try:
                        btn = page.locator(sel).first
                        if await btn.count() > 0 and await btn.is_enabled(timeout=1500):
                            await btn.click(timeout=4000)
                            clicked = True
                            break
                    except Exception:
                        continue
                await page.wait_for_timeout(4000)
                body = (await page.evaluate("() => document.body.innerText")).lower()
                success = any(k in body for k in (
                    "thank you for applying", "application submitted",
                    "gracias por", "we received your application", "your application has been"))
                result["submitted"] = clicked and success
                result["status"] = "submitted" if result["submitted"] else (
                    "submit_unconfirmed" if clicked else "submit_button_not_found")
                try:
                    shot2 = f"data/screenshots/ats_submit_{int(asyncio.get_event_loop().time())}.png"
                    await page.screenshot(path=shot2, full_page=True)
                    result["screenshot"] = shot2
                except Exception:
                    pass
        except Exception as e:
            result["status"] = f"error:{str(e)[:80]}"
            logger.error(f"[ats_filler] error: {e}")
        finally:
            await context.close()
            await browser.close()

    return result
