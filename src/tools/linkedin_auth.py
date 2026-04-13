"""
LinkedIn Auto-Login.

Hace login con email+password via Playwright y guarda todas las cookies
en config/linkedin_cookies.json. El orchestrator lo ejecuta cada 12h.
"""
import json
import time
from pathlib import Path

from loguru import logger
from playwright.sync_api import sync_playwright

from config import settings


def login_and_save_cookies() -> bool:
    """
    Abre LinkedIn, hace login con email+password, guarda cookies.
    Retorna True si el login fue exitoso.
    """
    email = settings.linkedin_email
    password = settings.linkedin_password

    if not email or not password:
        logger.error("[li_auth] LINKEDIN_EMAIL o LINKEDIN_PASSWORD no configurados en .env")
        return False

    logger.info(f"[li_auth] Iniciando login de LinkedIn para {email}...")

    pw = None
    browser = None
    try:
        pw = sync_playwright().start()
        browser = pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
        )
        ctx = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1366, "height": 768},
        )
        page = ctx.new_page()
        page.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )

        # Ir a la página de login
        page.goto("https://www.linkedin.com/login", wait_until="domcontentloaded", timeout=20000)
        time.sleep(2)

        # Verificar si ya está logueado (redirect al feed)
        if "/feed" in page.url:
            logger.info("[li_auth] Ya hay sesión activa, extrayendo cookies...")
            _save_cookies(ctx)
            return True

        # Llenar email
        page.fill('input[id="username"]', email)
        time.sleep(0.5)

        # Llenar password
        page.fill('input[id="password"]', password)
        time.sleep(0.5)

        # Click en Sign in
        page.click('button[type="submit"]')
        time.sleep(4)

        current_url = page.url
        logger.info(f"[li_auth] URL después de login: {current_url}")

        # Verificar si hay verificación de 2FA o CAPTCHA
        if "checkpoint" in current_url or "challenge" in current_url:
            logger.warning("[li_auth] LinkedIn pidió verificación adicional (2FA/CAPTCHA)")
            # Esperar hasta 30s por si el usuario lo completa manualmente
            for _ in range(6):
                time.sleep(5)
                if "/feed" in page.url:
                    break
            if "/feed" not in page.url:
                logger.error("[li_auth] No se pudo completar la verificación automáticamente")
                return False

        if "/feed" in page.url or "mynetwork" in page.url or "jobs" in page.url:
            logger.success("[li_auth] Login exitoso!")
            _save_cookies(ctx)
            return True
        else:
            logger.error(f"[li_auth] Login falló — URL final: {page.url}")
            # Tomar screenshot para diagnóstico
            try:
                Path("data/screenshots").mkdir(exist_ok=True)
                page.screenshot(path="data/screenshots/linkedin_login_failed.png")
            except Exception:
                pass
            return False

    except Exception as e:
        logger.error(f"[li_auth] Error durante login: {e}")
        return False
    finally:
        try:
            if browser:
                browser.close()
            if pw:
                pw.stop()
        except Exception:
            pass


def _save_cookies(ctx) -> None:
    """Extrae y guarda las cookies de LinkedIn del contexto del browser."""
    all_cookies = ctx.cookies("https://www.linkedin.com")

    cookie_map = {}
    important = {"li_at", "JSESSIONID", "bcookie", "bscookie", "lidc", "lang"}

    for c in all_cookies:
        if c["name"] in important:
            cookie_map[c["name"]] = c["value"]

    if "li_at" not in cookie_map:
        logger.warning("[li_auth] li_at no encontrado en cookies después del login")
        return

    # Guardar en el archivo de cookies
    cookies_file = Path(settings.linkedin_cookies_file)
    cookies_file.parent.mkdir(exist_ok=True)

    with open(cookies_file, "w") as f:
        json.dump(cookie_map, f, indent=2)

    logger.success(f"[li_auth] Cookies guardadas: {list(cookie_map.keys())}")


def verify_session() -> bool:
    """Verifica si la sesión actual de LinkedIn es válida (sin abrir browser)."""
    import requests

    try:
        with open(settings.linkedin_cookies_file) as f:
            cookies = json.load(f)
    except Exception:
        return False

    li_at = cookies.get("li_at", "")
    jsessionid = cookies.get("JSESSIONID", "").replace('"', '')
    bcookie = cookies.get("bcookie", "").replace('"', '')

    if not li_at:
        return False

    session = requests.Session()
    session.cookies.set("li_at", li_at, domain=".linkedin.com")
    session.cookies.set("JSESSIONID", f'"{jsessionid}"', domain=".www.linkedin.com")
    if bcookie:
        session.cookies.set("bcookie", f'"{bcookie}"', domain=".linkedin.com")

    session.headers.update({
        "csrf-token": jsessionid,
        "x-restli-protocol-version": "2.0.0",
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/vnd.linkedin.normalized+json+2.1",
    })

    try:
        r = session.get(
            "https://www.linkedin.com/voyager/api/me",
            timeout=10,
            allow_redirects=False,
        )
        return r.status_code == 200
    except Exception:
        return False


def ensure_session() -> bool:
    """
    Verifica la sesión y hace login automático si expiró.
    Llama a esto antes de cualquier operación de LinkedIn.
    """
    if verify_session():
        logger.debug("[li_auth] Sesión de LinkedIn válida")
        return True

    logger.info("[li_auth] Sesión expirada, haciendo login automático...")
    return login_and_save_cookies()


if __name__ == "__main__":
    success = login_and_save_cookies()
    print(f"Login {'exitoso' if success else 'falló'}")
    if success:
        print(f"Sesión válida: {verify_session()}")
