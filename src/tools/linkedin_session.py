"""
LinkedIn session — contexto de navegador PERSISTENTE y único (fingerprint estable).

Fuente de verdad para la sesión de navegador de LinkedIn. Todas las herramientas
que abren un browser (post, auth, moderate, browser_tool) deben usar esto en vez
de `browser.new_context()`, que crea un fingerprint fresco cada vez y termina
invalidando la sesión (JSESSIONID) — una de las señales técnicas que LinkedIn usa
para detectar automatización (2026).

Un solo `user_data_dir` = misma "computadora" siempre: localStorage, IndexedDB,
cookies de navegador, historial. Mismo UA (el del governor), viewport, locale
es-MX y timezone America/Mexico_City → fingerprint coherente con la IP residencial
de CDMX desde donde corre.
"""

from __future__ import annotations

import json
import os
from typing import Optional, Tuple

from loguru import logger

from config import settings
from src.tools import linkedin_governor as gov

_PROFILE_DIR = "data/linkedin_browser_profile"

# Fingerprint coherente con la ubicación real (CDMX).
_LOCALE = "es-MX"
_TIMEZONE = "America/Mexico_City"
_VIEWPORT = {"width": 1280, "height": 800}
_LAUNCH_ARGS = ["--no-sandbox", "--disable-blink-features=AutomationControlled"]
_STEALTH_INIT = "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"


def _load_cookies() -> dict:
    try:
        with open(settings.linkedin_cookies_file) as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"[li_session] no pude cargar cookies: {e}")
        return {}


def _cookie_records() -> list[dict]:
    cookies = _load_cookies()
    li_at = cookies.get("li_at", "")
    jsessionid = cookies.get("JSESSIONID", "").replace('"', "")
    recs = []
    if li_at:
        recs.append({"name": "li_at", "value": li_at, "domain": ".linkedin.com", "path": "/"})
    if jsessionid:
        recs.append({"name": "JSESSIONID", "value": f'"{jsessionid}"',
                     "domain": ".www.linkedin.com", "path": "/"})
    return recs


def build_persistent_context(headless: bool = True) -> Tuple[object, object, object]:
    """
    Sync: (playwright, context, page) con el perfil persistente único.
    El persistent context ES browser+context (no hay objeto browser aparte).
    """
    from playwright.sync_api import sync_playwright

    os.makedirs(_PROFILE_DIR, exist_ok=True)
    pw = sync_playwright().start()
    context = pw.chromium.launch_persistent_context(
        user_data_dir=_PROFILE_DIR,
        headless=headless,
        args=_LAUNCH_ARGS,
        user_agent=gov.USER_AGENT,
        viewport=_VIEWPORT,
        locale=_LOCALE,
        timezone_id=_TIMEZONE,
    )
    context.add_init_script(_STEALTH_INIT)
    recs = _cookie_records()
    if recs:
        context.add_cookies(recs)
    page = context.pages[0] if context.pages else context.new_page()
    return pw, context, page


async def build_persistent_context_async(headless: bool = True) -> Tuple[object, object, object]:
    """Async (para browser_tool): (playwright, context, page) con el mismo perfil."""
    from playwright.async_api import async_playwright

    os.makedirs(_PROFILE_DIR, exist_ok=True)
    pw = await async_playwright().start()
    context = await pw.chromium.launch_persistent_context(
        user_data_dir=_PROFILE_DIR,
        headless=headless,
        args=_LAUNCH_ARGS,
        user_agent=gov.USER_AGENT,
        viewport=_VIEWPORT,
        locale=_LOCALE,
        timezone_id=_TIMEZONE,
    )
    await context.add_init_script(_STEALTH_INIT)
    recs = _cookie_records()
    if recs:
        await context.add_cookies(recs)
    page = context.pages[0] if context.pages else await context.new_page()
    return pw, context, page
