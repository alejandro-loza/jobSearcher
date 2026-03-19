"""
Browser Tool: Playwright + GLM-4.7 visión para aplicar a jobs en páginas externas.

Flujo:
1. Navega a la URL del job
2. Toma screenshot
3. GLM-4.7 analiza la página y da instrucciones de llenado
4. Ejecuta las acciones (click, fill, select)
5. Repite hasta submit exitoso o error
6. Si hay CAPTCHA/ambigüedad → notifica por WhatsApp
"""
import asyncio
import base64
import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from loguru import logger

from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from langchain_core.messages import HumanMessage

from config import settings
from src.agents import coordinator


SCREENSHOTS_DIR = Path("data/screenshots")
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

MAX_STEPS = 15  # Máximo de pasos por aplicación


async def _linkedin_upload_resume(page: Page, abs_cv: Path, already_uploaded: bool) -> bool:
    """
    Handle LinkedIn Easy Apply resume upload.
    LinkedIn uses a special flow: button "Upload resume" reveals a hidden file input.
    """
    if already_uploaded or not abs_cv.exists():
        return already_uploaded

    try:
        # Strategy 1: Click "Upload resume" / "Subir currículum" button which reveals file input
        upload_buttons = [
            'button:has-text("Upload resume")',
            'button:has-text("Subir currículum")',
            'button:has-text("Upload CV")',
            'label:has-text("Upload resume")',
            'label:has-text("Subir currículum")',
            '[aria-label*="Upload resume"]',
            '[aria-label*="upload resume"]',
            'button.jobs-resume-picker__upload-btn',
        ]
        for btn_sel in upload_buttons:
            try:
                btn = page.locator(btn_sel)
                if await btn.count() > 0:
                    # Use file chooser pattern: click button and catch the file dialog
                    async with page.expect_file_chooser(timeout=5000) as fc_info:
                        await btn.first.click()
                    file_chooser = await fc_info.value
                    await file_chooser.set_files(str(abs_cv))
                    logger.info(f"LinkedIn CV uploaded via file chooser: {btn_sel}")
                    await page.wait_for_timeout(2000)
                    return True
            except Exception:
                continue

        # Strategy 2: Hidden file input (LinkedIn sometimes has input[type=file] hidden)
        file_inputs = page.locator('input[type="file"]')
        count = await file_inputs.count()
        for i in range(count):
            try:
                await file_inputs.nth(i).set_input_files(str(abs_cv))
                logger.info(f"LinkedIn CV uploaded via hidden file input #{i}")
                await page.wait_for_timeout(1000)
                return True
            except Exception:
                continue

        # Strategy 3: If there's already a resume shown (LinkedIn saves previous uploads),
        # check if "Be sure to include an updated resume" or similar text exists
        # In this case, LinkedIn uses the previously uploaded resume — that's OK
        resume_indicators = [
            'text="Resume"',
            '.jobs-document-upload-redesign-card',
            '[data-test-resume-upload]',
            '.jobs-resume-picker__resume-card',
        ]
        for indicator in resume_indicators:
            try:
                if await page.locator(indicator).count() > 0:
                    logger.info("LinkedIn: Resume already present from previous upload")
                    return True
            except Exception:
                continue

    except Exception as e:
        logger.debug(f"LinkedIn resume upload attempt: {e}")

    return False


async def _linkedin_easy_apply(
    page: Page,
    resume: Dict,
    abs_cv: Path,
    cover_letter: str = "",
) -> Dict[str, Any]:
    """
    Dedicated LinkedIn Easy Apply handler.
    Handles the multi-step modal flow without relying on LLM for navigation.
    Returns: {success: bool, status: str, message: str}
    """
    # Step 1: Click "Easy Apply" / "Solicitud sencilla" button (may be <button> or <a>)
    easy_apply_clicked = False
    for sel in [
        'button.jobs-apply-button',
        'button:has-text("Easy Apply")',
        'button:has-text("Solicitud sencilla")',
        'button[aria-label*="Easy Apply"]',
        'button[aria-label*="Solicitud sencilla"]',
        '.jobs-apply-button--top-card button',
        'a:has-text("Easy Apply")',
        'a:has-text("Solicitud sencilla")',
        'a[aria-label*="Easy Apply"]',
        'a[aria-label*="Solicitud sencilla"]',
    ]:
        try:
            btn = page.locator(sel).first
            if await btn.is_visible(timeout=2000):
                await btn.click()
                easy_apply_clicked = True
                logger.info(f"LinkedIn Easy Apply: clicked via {sel}")
                await page.wait_for_timeout(2000)
                break
        except Exception:
            continue

    if not easy_apply_clicked:
        # Check if already in the modal or already applied
        page_text = await page.evaluate("() => document.body.innerText")
        if any(w in page_text.lower() for w in ["already applied", "ya aplicaste", "ya has enviado"]):
            return {"success": False, "status": "done", "message": "Already applied to this job"}
        return {"success": False, "status": "error", "message": "Could not find Easy Apply button"}

    # Step 2: Navigate through modal steps
    max_modal_steps = 15
    cv_uploaded = False

    for modal_step in range(max_modal_steps):
        await page.wait_for_timeout(1500)

        # Get modal text to understand current step
        modal_text = ""
        try:
            modal = page.locator('.artdeco-modal, .jobs-easy-apply-modal, [role="dialog"]').first
            if await modal.is_visible(timeout=3000):
                modal_text = (await modal.inner_text())[:2000].lower()
        except Exception:
            modal_text = (await page.evaluate("() => document.body.innerText"))[:2000].lower()

        logger.info(f"LinkedIn Easy Apply step {modal_step + 1}, modal text: {modal_text[:100]}...")

        # Check if we've completed (success page)
        if any(w in modal_text for w in [
            "application sent", "candidatura enviada", "solicitud enviada",
            "you applied", "has enviado tu solicitud", "your application was sent",
        ]):
            return {"success": True, "status": "success", "message": "LinkedIn Easy Apply submitted successfully"}

        # Try to upload CV on resume step
        if not cv_uploaded and any(w in modal_text for w in ["resume", "cv", "currículum", "curriculum"]):
            cv_uploaded = await _linkedin_upload_resume(page, abs_cv, cv_uploaded)
            if cv_uploaded:
                logger.info(f"LinkedIn Easy Apply: CV uploaded at step {modal_step + 1}")

        # Also try upload on any step (LinkedIn might have file input)
        if not cv_uploaded:
            try:
                file_inputs = page.locator('input[type="file"]')
                if await file_inputs.count() > 0 and abs_cv.exists():
                    await file_inputs.first.set_input_files(str(abs_cv))
                    cv_uploaded = True
                    logger.info(f"LinkedIn Easy Apply: CV uploaded via file input at step {modal_step + 1}")
            except Exception:
                pass

        # Fill common fields using LinkedIn's specific patterns
        await _linkedin_fill_modal_fields(page, resume, cover_letter, modal_text)

        # Try to click "Next" / "Siguiente" / "Review" / "Revisar"
        next_clicked = False
        for next_sel in [
            'button[aria-label="Continue to next step"]',
            'button[aria-label="Continuar al siguiente paso"]',
            'button[aria-label="Review your application"]',
            'button[aria-label="Revisar tu solicitud"]',
            'button:has-text("Next")',
            'button:has-text("Siguiente")',
            'button:has-text("Review")',
            'button:has-text("Revisar")',
            'button:has-text("Continue")',
            'button:has-text("Continuar")',
        ]:
            try:
                btn = page.locator(next_sel).first
                if await btn.is_visible(timeout=1000) and await btn.is_enabled(timeout=500):
                    await btn.click()
                    next_clicked = True
                    logger.info(f"LinkedIn Easy Apply: clicked '{next_sel}' at step {modal_step + 1}")
                    await page.wait_for_timeout(1500)
                    break
            except Exception:
                continue

        # If no "Next", try "Submit" / "Enviar candidatura"
        if not next_clicked:
            for submit_sel in [
                'button[aria-label="Submit application"]',
                'button[aria-label="Enviar candidatura"]',
                'button:has-text("Submit application")',
                'button:has-text("Enviar candidatura")',
                'button:has-text("Submit")',
                'button:has-text("Enviar")',
            ]:
                try:
                    btn = page.locator(submit_sel).first
                    if await btn.is_visible(timeout=1000) and await btn.is_enabled(timeout=500):
                        await btn.click()
                        logger.info(f"LinkedIn Easy Apply: clicked SUBMIT '{submit_sel}'")
                        await page.wait_for_timeout(3000)

                        # Check if submission was successful
                        post_text = (await page.evaluate("() => document.body.innerText"))[:1000].lower()
                        if any(w in post_text for w in [
                            "application sent", "candidatura enviada", "solicitud enviada",
                            "your application was sent",
                        ]):
                            return {"success": True, "status": "success", "message": "LinkedIn Easy Apply submitted"}
                        # Even if we don't see confirmation text, if we clicked submit, assume success
                        return {"success": True, "status": "success", "message": "LinkedIn Easy Apply submit clicked"}
                except Exception:
                    continue

        # If neither Next nor Submit worked, check for dismiss/close scenarios
        if not next_clicked:
            # Check for error messages requiring field fixes
            error_msgs = page.locator('.artdeco-inline-feedback--error, .fb-dash-form-element__error-field')
            if await error_msgs.count() > 0:
                error_text = await error_msgs.first.inner_text()
                logger.warning(f"LinkedIn Easy Apply: form error at step {modal_step + 1}: {error_text}")
                # Use LLM to fill required fields based on error
                await _linkedin_fill_with_llm(page, resume, cover_letter, modal_text)
                # Try Next again after fix
                for next_sel in ['button:has-text("Next")', 'button:has-text("Siguiente")']:
                    try:
                        btn = page.locator(next_sel).first
                        if await btn.is_visible(timeout=1000):
                            await btn.click()
                            break
                    except Exception:
                        continue
            else:
                logger.warning(f"LinkedIn Easy Apply: stuck at step {modal_step + 1}, no Next/Submit found")
                # Last resort: use LLM vision
                await _linkedin_fill_with_llm(page, resume, cover_letter, modal_text)

    return {"success": False, "status": "error", "message": "LinkedIn Easy Apply: exceeded max steps"}


async def _linkedin_fill_modal_fields(
    page: Page,
    resume: Dict,
    cover_letter: str,
    modal_text: str,
) -> None:
    """Fill common LinkedIn Easy Apply modal fields without LLM."""
    field_map = {
        "phone": resume.get("phone", "+52 56 4144 6948"),
        "mobile": resume.get("phone", "+52 56 4144 6948"),
        "teléfono": resume.get("phone", "+52 56 4144 6948"),
        "city": "Ciudad de México",
        "ciudad": "Ciudad de México",
    }

    # Fill text inputs by label matching
    inputs = page.locator('input[type="text"], input:not([type])')
    count = await inputs.count()
    for i in range(min(count, 15)):
        try:
            inp = inputs.nth(i)
            if not await inp.is_visible(timeout=500):
                continue
            # Get the associated label or placeholder
            label = await inp.evaluate("""el => {
                let label = el.closest('div')?.querySelector('label')?.innerText || '';
                return label || el.placeholder || el.getAttribute('aria-label') || '';
            }""")
            label_lower = label.lower().strip()

            # Skip already filled fields
            current_val = await inp.input_value()
            if current_val.strip():
                continue

            # Match known fields
            filled = False
            for key, val in field_map.items():
                if key in label_lower:
                    await inp.fill(val)
                    logger.debug(f"LinkedIn auto-fill: '{label}' = '{val}'")
                    filled = True
                    break

            # Years of experience
            if not filled and any(w in label_lower for w in ["years", "años", "experience"]):
                await inp.fill("12")
                logger.debug(f"LinkedIn auto-fill: '{label}' = '12'")

            # Salary
            if not filled and any(w in label_lower for w in ["salary", "salario", "compensation"]):
                await inp.fill("Negotiable")
                logger.debug(f"LinkedIn auto-fill: '{label}' = 'Negotiable'")

            # How did you hear
            if not filled and any(w in label_lower for w in ["hear about", "enteraste", "cómo supiste"]):
                await inp.fill("LinkedIn")

            # LinkedIn URL
            if not filled and any(w in label_lower for w in ["linkedin", "profile url"]):
                await inp.fill(resume.get("linkedin_url", "https://www.linkedin.com/in/alejandro-hernandez-loza/"))

            # Website / Portfolio
            if not filled and any(w in label_lower for w in ["website", "portfolio", "github"]):
                await inp.fill(resume.get("github_url", "https://github.com/alejandro-loza"))

        except Exception:
            continue

    # Fill textareas (cover letter, additional info)
    textareas = page.locator('textarea')
    ta_count = await textareas.count()
    for i in range(min(ta_count, 5)):
        try:
            ta = textareas.nth(i)
            if not await ta.is_visible(timeout=500):
                continue
            current_val = await ta.input_value()
            if current_val.strip():
                continue
            label = await ta.evaluate("""el => {
                let label = el.closest('div')?.querySelector('label')?.innerText || '';
                return label || el.placeholder || el.getAttribute('aria-label') || '';
            }""")
            if cover_letter:
                await ta.fill(cover_letter[:3000])
                logger.debug(f"LinkedIn auto-fill textarea: '{label[:30]}' with cover letter")
            else:
                summary = resume.get("experience_summary", resume.get("summary", ""))
                if summary:
                    await ta.fill(summary[:3000])
        except Exception:
            continue

    # Handle select/dropdown fields
    selects = page.locator('select')
    sel_count = await selects.count()
    for i in range(min(sel_count, 10)):
        try:
            sel = selects.nth(i)
            if not await sel.is_visible(timeout=500):
                continue
            label = await sel.evaluate("""el => {
                let label = el.closest('div')?.querySelector('label')?.innerText || '';
                return label || el.getAttribute('aria-label') || '';
            }""")
            label_lower = label.lower()
            # Try common answers
            if any(w in label_lower for w in ["gender", "género"]):
                await sel.select_option(label="Prefer not to say")
            elif any(w in label_lower for w in ["veteran", "disability", "discapacidad"]):
                await sel.select_option(label="Prefer not to say")
            elif any(w in label_lower for w in ["authorization", "autorización", "work permit"]):
                await sel.select_option(label="Yes")
            elif any(w in label_lower for w in ["sponsor", "visa"]):
                await sel.select_option(label="No")
        except Exception:
            continue

    # Handle radio buttons — check first option that says "Yes" for work authorization
    radios = page.locator('input[type="radio"]')
    radio_count = await radios.count()
    for i in range(min(radio_count, 10)):
        try:
            radio = radios.nth(i)
            label = await radio.evaluate("""el => {
                let label = el.closest('label')?.innerText || el.nextElementSibling?.innerText || '';
                return label;
            }""")
            group_label = await radio.evaluate("""el => {
                let fieldset = el.closest('fieldset');
                return fieldset?.querySelector('legend')?.innerText || '';
            }""")
            group_lower = group_label.lower()

            # Work authorization questions - answer Yes
            if any(w in group_lower for w in ["authorized", "autorizado", "legally"]):
                if "yes" in label.lower() or "sí" in label.lower():
                    await radio.check()
            # Sponsorship questions - answer Yes (Mexico-based, needs visa for US/EU)
            elif any(w in group_lower for w in ["sponsor", "visa"]):
                if "yes" in label.lower() and "future" not in label.lower():
                    await radio.check()
        except Exception:
            continue

    # Handle LinkedIn custom fieldsets with label-based options (not standard radio/checkbox)
    # LinkedIn may use custom components where clicking the <label> triggers the selection
    try:
        answered = await page.evaluate("""() => {
            const modal = document.querySelector('[role="dialog"]') || document.body;
            const fieldsets = modal.querySelectorAll('fieldset');
            let answered = false;
            for (const fs of fieldsets) {
                const legend = (fs.querySelector('legend')?.innerText || '').toLowerCase();
                const labels = fs.querySelectorAll('label');
                // Skip if already has a checked input
                if (fs.querySelector('input:checked')) continue;
                if (labels.length === 0) continue;

                let targetText = null;
                if (legend.includes('visa') || legend.includes('sponsor')) {
                    targetText = 'yes';
                } else if (legend.includes('authorized') || legend.includes('right to work') || legend.includes('legally')) {
                    targetText = 'yes';
                } else if (legend.includes('commute') || legend.includes('relocate')) {
                    targetText = 'yes';
                }

                if (targetText) {
                    for (const lbl of labels) {
                        if (lbl.innerText.trim().toLowerCase() === targetText) {
                            lbl.click();
                            answered = true;
                            break;
                        }
                    }
                } else {
                    // Generic: click first label option
                    labels[0].click();
                    answered = true;
                }
            }
            return answered;
        }""")
        if answered:
            logger.debug("LinkedIn auto-fill: answered fieldset questions via label click")
    except Exception:
        pass

    # Also handle error-indicated required fields by clicking "Yes" label
    try:
        error_visible = await page.locator(
            '[role="dialog"] :text("Please make a selection"), '
            '[role="dialog"] :text("Selecciona")'
        ).first.is_visible(timeout=500)
        if error_visible:
            for text in ["Yes", "Sí", "No"]:
                label = page.locator(f'[role="dialog"] fieldset label:has-text("{text}")').first
                if await label.is_visible(timeout=500):
                    await label.click()
                    logger.debug(f"LinkedIn auto-fill: clicked label '{text}' for required field")
                    break
    except Exception:
        pass


async def _linkedin_fill_with_llm(
    page: Page,
    resume: Dict,
    cover_letter: str,
    modal_text: str,
) -> None:
    """Fallback: use LLM to analyze and fill remaining fields."""
    try:
        img_b64 = await _screenshot_b64(page, 99)
        prompt = f"""You are filling out a LinkedIn Easy Apply form. Here is the current modal content:
{modal_text[:1500]}

Candidate info:
- Name: {resume.get('full_name', 'Alejandro Hernandez Loza')}
- Email: {resume.get('email', 'alejandrohloza@gmail.com')}
- Phone: {resume.get('phone', '+52 56 4144 6948')}
- Location: Ciudad de México, México
- Years experience: 12
- Work authorization: Yes (Mexican citizen)
- Visa sponsorship needed: Yes (for USA/EU)

Return JSON with actions to fill remaining empty fields:
{{"actions": [{{"type": "fill", "selector": "CSS selector or label", "value": "value to fill"}}]}}
Return ONLY JSON."""

        content = await asyncio.to_thread(_invoke_page_analysis, prompt)
        content = content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        result = json.loads(content)
        for action in result.get("actions", []):
            await _execute_action(page, action)
            await page.wait_for_timeout(300)
    except Exception as e:
        logger.debug(f"LinkedIn LLM fill fallback failed: {e}")


def _invoke_page_analysis(prompt: str) -> str:
    """Invoca el LLM para analizar páginas. Usa el coordinator con fallback completo."""
    return coordinator.invoke("browser_vision", [HumanMessage(content=prompt)], temperature=0.3, max_tokens=2048)


async def _screenshot_b64(page: Page, step: int = 0) -> str:
    """Toma screenshot y retorna en base64."""
    path = SCREENSHOTS_DIR / f"step_{step}_{int(time.time())}.png"
    await page.screenshot(path=str(path), full_page=False)
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


async def _analyze_page(
    page: Page,
    resume: Dict,
    step: int,
    history: List[str],
    cv_pdf_path: str = "data/cv_alejandro_en.pdf",
    cover_letter: str = "",
) -> Dict[str, Any]:
    """
    GLM-4.7 analiza la página actual y decide qué hacer.

    Returns:
        Dict con:
        - status: "fill|submit|success|error|captcha|need_user|done"
        - actions: lista de acciones a ejecutar
        - message: descripción de lo que ve/hace
    """
    # Obtener texto de la página además del screenshot
    page_text = await page.evaluate("() => document.body.innerText")
    page_url = page.url

    img_b64 = await _screenshot_b64(page, step)

    history_text = "\n".join(f"  Paso {i+1}: {h}" for i, h in enumerate(history[-5:]))

    # Build experience summary for the prompt
    exp_lines = []
    for exp in resume.get("work_experience", []):
        highlights = "; ".join(exp.get("highlights", []))
        exp_lines.append(f"  {exp.get('role','')} @ {exp.get('company','')} ({exp.get('start','')}-{exp.get('end','')}): {highlights}")
    experience_block = "\n".join(exp_lines) if exp_lines else "12 years in Java, Spring Boot, Full Stack, Cloud"

    achievements_block = "\n".join(f"  - {a}" for a in resume.get("achievements", [])[:5])

    cover_letter_block = ""
    if cover_letter:
        cover_letter_block = f"""
COVER LETTER (usa este texto para campos "cover letter", "message to hiring manager", "why do you want this job",
"additional information", "carta de presentación", o cualquier campo de texto largo para el reclutador):
{cover_letter}
"""

    prompt = f"""Eres un agente que está aplicando a un trabajo en nombre del candidato.

DATOS COMPLETOS DEL CANDIDATO (usa estos datos para llenar TODOS los campos del formulario):
- Nombre completo: {resume.get('full_name', 'Alejandro Hernandez Loza')}
- Primer nombre (First Name): Alejandro
- Apellido (Last Name): Hernandez Loza
- Email: {resume.get('email', 'alejandrohloza@gmail.com')}
- Teléfono: {resume.get('phone', '+52 56 4144 6948')}
- Código de país: +52 (México)
- Título profesional: {resume.get('professional_title', 'SR. Software Engineer')}
- Años de experiencia: {resume.get('years_of_experience', 12)}
- Ubicación actual: {resume.get('location', 'Ciudad de México, México')}
- Ciudad: Ciudad de México / Mexico City
- País: México / Mexico
- Modalidad preferida: {resume.get('preferred_location', 'Remote')}
- Disponibilidad: Inmediata / Immediately
- Autorización de trabajo: Ciudadano mexicano, requiere visa para USA/EU
- Expectativa salarial: Negociable / Negotiable (si el campo es obligatorio: $50,000 MXN o $4,000 USD mensual)
- LinkedIn: {resume.get('linkedin_url', 'https://www.linkedin.com/in/alejandro-hernandez-loza/')}
- GitHub: {resume.get('github_url', 'https://github.com/alejandro-loza')}
- Website/Portfolio: {resume.get('portfolio_url', 'https://github.com/alejandro-loza')}
- CV/Resume PDF: {cv_pdf_path} (para upload)
- Educación: {resume.get('education', 'B.S. Computer Systems Engineering - UAEH (2007-2012)')}
- Universidad: Universidad Autónoma del Estado de Hidalgo (UAEH)
- Grado: Ingeniero en Sistemas Computacionales / B.S. Computer Systems Engineering
- Año graduación: 2012
- Idiomas: Español (nativo), Inglés (profesional/fluent)

SKILLS TÉCNICOS: {', '.join(resume.get('technical_skills', []))}

RESUMEN PROFESIONAL (para campos "summary", "about you", "professional summary"):
{resume.get('experience_summary', resume.get('summary', ''))}

EXPERIENCIA LABORAL:
{experience_block}

LOGROS DESTACADOS:
{achievements_block}
{cover_letter_block}
REGLAS IMPORTANTES:
1. Si hay campo para subir CV/Resume (input type=file), usa action type "upload" con value "{cv_pdf_path}" — OBLIGATORIO
2. Llena TODOS los campos visibles con la información del candidato
3. Para campos de texto largo (cover letter, why this job, additional info), usa la COVER LETTER proporcionada arriba
4. Si un campo pregunta "how did you hear about us" → responde "LinkedIn"
5. Si pide salary → "Negotiable" o "$50,000 MXN" si es obligatorio
6. Si pide years of experience → "12"
7. Si hay checkbox de terms/conditions → márcalo (check)
8. Si pide gender/ethnicity/veteran → selecciona "Prefer not to say" o "Decline to answer"
9. Si pide referral → "No" o dejar vacío
10. Si hay campo de notas/comentarios adicionales y no tienes cover letter → usa el RESUMEN PROFESIONAL

URL ACTUAL: {page_url}
HISTORIAL DE PASOS: {history_text if history_text else "Primer paso"}

TEXTO DE LA PÁGINA (primeros 2000 chars):
{page_text[:2000]}

Analiza la página y dime qué hacer. Responde SOLO con JSON válido:
{{
  "status": "fill|submit|success|error|captcha|need_user|done",
  "message": "descripción de lo que ves en 1 oración",
  "actions": [
    {{
      "type": "fill|click|select|upload|check|wait",
      "selector": "selector CSS o texto del elemento",
      "value": "valor a ingresar (si aplica)",
      "description": "qué hace esta acción"
    }}
  ]
}}

status:
- fill: hay campos que llenar
- submit: todo listo para enviar
- success: aplicación enviada exitosamente
- error: error en la página
- captcha: hay captcha que no puedo resolver
- need_user: necesito información que no tengo
- done: ya no hay nada más que hacer

REGLAS DE NAVEGACIÓN (MUY IMPORTANTE):
1. Después de llenar campos, SIEMPRE incluye click en el botón "Siguiente", "Next", "Continuar", "Continue" en las mismas acciones — nunca dejes un form lleno sin avanzar.
2. Si el historial muestra que ya llenaste los mismos campos en pasos anteriores y la página se ve igual → el form no avanzó. En ese caso: busca botón "Siguiente"/"Next"/"Continuar" y haz click SIN rellenar campos.
3. Si el historial tiene 3+ pasos seguidos con el mismo status/descripción → cambia de estrategia: intenta click en cualquier botón de avance visible.
4. Para botones "Siguiente"/"Next": selector preferido → `button:has-text("Siguiente")`, `button:has-text("Next")`, `button[aria-label*="Next"]`.
5. Para submit final: selector → `button:has-text("Enviar candidatura")`, `button:has-text("Submit application")`, `button[aria-label*="Submit"]`.
6. Para selectors usa: texto visible, placeholder, label, name, id, o aria-label.
7. Prefiere selectores por texto visible o placeholder sobre CSS genérico.
8. Si es página de confirmación o "Thank you" → status = success.
9. Si ya aplicaste antes (duplicate) → status = done.
"""

    try:
        content = await asyncio.to_thread(_invoke_page_analysis, prompt)
        content = content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        return json.loads(content)

    except Exception as e:
        logger.error(f"Error analizando página: {e}")
        return {
            "status": "error",
            "message": f"No pude analizar la página: {e}",
            "actions": [],
        }


async def _execute_action(page: Page, action: Dict) -> bool:
    """Ejecuta una acción en la página."""
    action_type = action.get("type", "")
    selector = action.get("selector", "")
    value = action.get("value", "")

    try:
        if action_type == "fill":
            # Intentar múltiples estrategias de selector
            for strategy in [
                f'[placeholder*="{selector}"]',
                f'[name*="{selector}"]',
                f'[id*="{selector}"]',
                f'[aria-label*="{selector}"]',
                f'input[type="text"]',
            ]:
                try:
                    await page.fill(strategy, value, timeout=3000)
                    logger.debug(f"Fill '{selector}' = '{value}' via {strategy}")
                    return True
                except Exception:
                    continue

            # Último intento: por texto del label
            try:
                await page.get_by_label(selector).fill(value, timeout=3000)
                return True
            except Exception:
                pass

            # Por placeholder exacto
            try:
                await page.get_by_placeholder(selector).fill(value, timeout=3000)
                return True
            except Exception:
                logger.warning(f"No pude hacer fill en '{selector}'")
                return False

        elif action_type == "click":
            for strategy in [
                f'text="{selector}"',
                f'button:has-text("{selector}")',
                f'[aria-label*="{selector}"]',
                selector,
            ]:
                try:
                    await page.click(strategy, timeout=5000)
                    await page.wait_for_timeout(1000)
                    logger.debug(f"Click en '{selector}'")
                    return True
                except Exception:
                    continue

            try:
                await page.get_by_role("button", name=selector).click(timeout=5000)
                return True
            except Exception:
                logger.warning(f"No pude hacer click en '{selector}'")
                return False

        elif action_type == "select":
            try:
                await page.select_option(selector, label=value, timeout=3000)
                return True
            except Exception:
                try:
                    await page.select_option(selector, value=value, timeout=3000)
                    return True
                except Exception:
                    return False

        elif action_type == "upload":
            # Subir archivo (CV/Resume PDF)
            try:
                cv_path = value or "data/cv_alejandro_en.pdf"
                # Resolver ruta absoluta
                from pathlib import Path as _Path
                abs_path = _Path(cv_path).resolve()
                if not abs_path.exists():
                    abs_path = _Path("/data/projects/proyects/jobSearcher") / cv_path
                if abs_path.exists():
                    file_input = page.locator(f'input[type="file"]')
                    if await file_input.count() > 0:
                        await file_input.first.set_input_files(str(abs_path))
                        logger.info(f"Upload CV: {abs_path}")
                        return True
                    # Intentar por selector específico
                    file_input = page.locator(selector)
                    await file_input.set_input_files(str(abs_path))
                    logger.info(f"Upload CV via selector: {abs_path}")
                    return True
                else:
                    logger.warning(f"CV no encontrado: {abs_path}")
                    return False
            except Exception as e:
                logger.warning(f"Error subiendo CV: {e}")
                return False

        elif action_type == "check":
            try:
                await page.check(selector, timeout=3000)
                return True
            except Exception:
                return False

        elif action_type == "wait":
            await page.wait_for_timeout(int(value) if value.isdigit() else 2000)
            return True

    except Exception as e:
        logger.warning(f"Error ejecutando acción {action_type} en '{selector}': {e}")
        return False

    return False


async def apply_to_job_url(
    job_url: str,
    resume: Dict,
    job_title: str = "",
    company: str = "",
    cover_letter: str = "",
) -> Dict[str, Any]:
    """
    Navega y aplica a un trabajo en una URL externa usando Playwright + GLM-4.7.

    Args:
        job_url: URL de la página de aplicación
        resume: Datos del CV de Alejandro
        job_title: Título del puesto (para logs)
        company: Empresa (para logs)

    Returns:
        Dict con: success, status, message, screenshot_path
    """
    logger.info(f"Browser agent iniciando aplicación: {job_title} @ {company} → {job_url}")

    from src.tools import whatsapp_tool

    async with async_playwright() as p:
        browser: Browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox"],
        )
        context: BrowserContext = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
        )

        # Cargar cookies de LinkedIn si la URL es de LinkedIn
        if "linkedin.com" in job_url:
            try:
                import json as _json
                with open(settings.linkedin_cookies_file) as f:
                    linkedin_cookies = _json.load(f)
                cookies = []
                if isinstance(linkedin_cookies, dict):
                    for name, value in linkedin_cookies.items():
                        cookies.append({"name": name, "value": value, "domain": ".linkedin.com", "path": "/"})
                elif isinstance(linkedin_cookies, list):
                    cookies = linkedin_cookies
                await context.add_cookies(cookies)
                logger.debug("Cookies de LinkedIn cargadas en el browser")
            except Exception as e:
                logger.warning(f"No se pudieron cargar cookies de LinkedIn: {e}")

        page: Page = await context.new_page()

        try:
            await page.goto(job_url, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(2000)

            history = []
            final_status = "error"
            final_message = "No se pudo completar la aplicación"

            # Detectar idioma de la página para elegir CV correcto
            page_text_initial = await page.evaluate("() => document.body.innerText")
            _is_spanish_page = any(w in page_text_initial.lower() for w in [
                'aplicar', 'postular', 'enviar solicitud', 'currículum', 'experiencia laboral',
                'datos personales', 'nombre completo'
            ])
            cv_pdf_path = "data/cv_alejandro_es.pdf" if _is_spanish_page else "data/cv_alejandro_en.pdf"
            logger.info(f"CV seleccionado: {cv_pdf_path} (español={_is_spanish_page})")

            # Resolver ruta absoluta del CV
            from pathlib import Path as _Path
            abs_cv = (_Path("/data/projects/proyects/jobSearcher") / cv_pdf_path).resolve()
            cv_uploaded = False

            # LinkedIn Easy Apply: use dedicated handler
            if "linkedin.com" in job_url:
                result = await _linkedin_easy_apply(page, resume, abs_cv, cover_letter)
                if result.get("success") or result.get("status") == "done":
                    return {
                        "success": result.get("success", False),
                        "status": result.get("status", "done"),
                        "message": result.get("message", ""),
                        "screenshot_path": str(SCREENSHOTS_DIR / f"final_{int(time.time())}.png"),
                        "url": job_url,
                    }
                # If LinkedIn handler failed, fall through to generic handler
                logger.warning(f"LinkedIn Easy Apply handler failed: {result.get('message')}, trying generic flow")

            # Auto-upload: si hay input[type=file] visible, subir CV inmediatamente
            try:
                file_inputs = page.locator('input[type="file"]')
                if await file_inputs.count() > 0 and abs_cv.exists():
                    await file_inputs.first.set_input_files(str(abs_cv))
                    cv_uploaded = True
                    logger.info(f"Auto-upload CV en primer paso: {abs_cv}")
                    history.append("Auto-uploaded CV/Resume PDF")
            except Exception as e:
                logger.debug(f"No file input en primera carga: {e}")

            for step in range(MAX_STEPS):
                analysis = await _analyze_page(page, resume, step, history, cv_pdf_path, cover_letter)
                status = analysis.get("status", "error")
                message = analysis.get("message", "")
                actions = analysis.get("actions", [])

                logger.info(f"Paso {step+1}: {status} - {message}")
                history.append(f"{status}: {message}")

                if status == "success":
                    final_status = "success"
                    final_message = message
                    whatsapp_tool.send_message(
                        f"✅ *Aplicación enviada*\n"
                        f"*{job_title}* @ *{company}*\n"
                        f"URL: {job_url}"
                    )
                    break

                elif status in ("done", "error"):
                    final_status = status
                    final_message = message
                    break

                elif status == "captcha":
                    final_status = "captcha"
                    final_message = "Hay un CAPTCHA que no puedo resolver"
                    screenshot_b64 = await _screenshot_b64(page, step)
                    whatsapp_tool.send_message(
                        f"⚠️ *CAPTCHA detectado*\n"
                        f"*{job_title}* @ *{company}*\n"
                        f"Necesito que apliques manualmente: {job_url}"
                    )
                    break

                elif status == "need_user":
                    final_status = "need_user"
                    final_message = message
                    whatsapp_tool.send_message(
                        f"❓ *Necesito información*\n"
                        f"Para aplicar a *{job_title}* @ *{company}*:\n"
                        f"{message}\n\n"
                        f"Responde con la información o aplica manualmente: {job_url}"
                    )
                    break

                # Detectar loop: si los últimos 3 mensajes son iguales, forzar click en "Siguiente"
                if len(history) >= 3 and len(set(history[-3:])) == 1:
                    logger.warning(f"Loop detectado en paso {step+1}, forzando click en botón de avance")
                    for next_btn in ["Siguiente", "Next", "Continue", "Continuar", "Revisar", "Review"]:
                        try:
                            await page.get_by_role("button", name=next_btn).click(timeout=3000)
                            logger.info(f"Loop break: click forzado en '{next_btn}'")
                            await page.wait_for_timeout(2000)
                            break
                        except Exception:
                            continue

                # Ejecutar acciones
                for action in actions:
                    await _execute_action(page, action)
                    await page.wait_for_timeout(500)

                # Auto-upload CV en cada paso si hay file input sin archivo
                if not cv_uploaded:
                    try:
                        file_inputs = page.locator('input[type="file"]')
                        if await file_inputs.count() > 0:
                            has_file = await file_inputs.first.evaluate("el => el.files && el.files.length > 0")
                            if not has_file and abs_cv.exists():
                                await file_inputs.first.set_input_files(str(abs_cv))
                                cv_uploaded = True
                                logger.info(f"Auto-upload CV en paso {step+1}")
                    except Exception:
                        pass

                # Esperar carga de página
                try:
                    await page.wait_for_load_state("networkidle", timeout=5000)
                except Exception:
                    await page.wait_for_timeout(2000)

            screenshot_path = str(SCREENSHOTS_DIR / f"final_{int(time.time())}.png")
            await page.screenshot(path=screenshot_path)

            return {
                "success": final_status == "success",
                "status": final_status,
                "message": final_message,
                "screenshot_path": screenshot_path,
                "url": job_url,
            }

        except Exception as e:
            logger.error(f"Error en browser agent: {e}")
            whatsapp_tool.send_message(
                f"❌ Error al aplicar a *{job_title}* @ *{company}*\n"
                f"Aplica manualmente: {job_url}"
            )
            return {
                "success": False,
                "status": "error",
                "message": str(e),
                "screenshot_path": None,
                "url": job_url,
            }
        finally:
            await browser.close()


def apply_to_job_sync(
    job_url: str,
    resume: Dict,
    job_title: str = "",
    company: str = "",
    cover_letter: str = "",
) -> Dict[str, Any]:
    """Versión síncrona del browser agent para usar desde el orchestrator."""
    # Auto-generate cover letter if not provided
    if not cover_letter and job_title:
        try:
            from src.agents import master_agent
            job = {"title": job_title, "company": company, "url": job_url}
            cover_letter = master_agent.generate_cover_letter(job, resume)
            logger.info(f"Auto-generated cover letter for {job_title} @ {company}")
        except Exception as e:
            logger.warning(f"Could not auto-generate cover letter: {e}")
            cover_letter = ""

    return asyncio.run(apply_to_job_url(job_url, resume, job_title, company, cover_letter))
