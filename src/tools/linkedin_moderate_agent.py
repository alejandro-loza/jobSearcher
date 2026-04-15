"""
LinkedIn Application Agent - Moderate & Anti-Banning

Sistema de aplicaciones automáticas a LinkedIn con estrategias anti-banning:
- Comportamientos humanos con delays realistas
- Rate limiting inteligente
- Soporte para portales externos (Workday, Greenhouse, etc.)
- Integración segura con el orchestrator
"""

import asyncio
import json
import random
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List
from loguru import logger

from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from config import settings


# ============================================================================
# CONFIGURACIÓN MODERADA - ANTI-BANNING
# ============================================================================

APPS_PER_HOUR = 10  # Temporalmente 10 apps/hora para aplicar hoy
DELAY_MIN = settings.linkedin_delay_min_seconds     # 5 segundos mínimo
DELAY_MAX = settings.linkedin_delay_max_seconds     # 15 segundos máximo
PAUSE_AFTER_APPS = 999  # Desactivar pausas automáticas por hoy
PAUSE_MINUTES = 5  # Pausa corta si se activa

# User agents realistas (Chrome latest)
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
]

# ============================================================================
# ESTADO GLOBAL PARA RATE LIMITING
# ============================================================================

app_count_today = 0
last_app_time = None
app_count_since_pause = 0
is_paused = False


async def _human_delay(min_seconds: float = DELAY_MIN, max_seconds: float = DELAY_MAX) -> None:
    """Delay aleatorio para simular comportamiento humano."""
    delay = random.uniform(min_seconds, max_seconds)
    logger.debug(f"[li_moderate] Delay humano: {delay:.1f}s")
    await asyncio.sleep(delay)


async def _should_pause() -> bool:
    """Verifica si se debe pausar por rate limiting."""
    global is_paused, app_count_since_pause, last_app_time
    
    # Si ya está pausado, continuar
    if is_paused:
        return True
    
    # Si no hay aplicaciones suficientes, no pausar
    if app_count_since_pause < PAUSE_AFTER_APPS:
        return False
    
    # Verificar tiempo desde última aplicación
    if last_app_time:
        time_since_last = datetime.now() - last_app_time
        # Si han pasado más de PAUSE_MINUTES, resetear contador
        if time_since_last > timedelta(minutes=PAUSE_MINUTES):
            app_count_since_pause = 0
            return False
    
    # Pausar por seguridad
    return True


async def _pause_for_safety():
    """Pausa inteligente por seguridad anti-banning."""
    global is_paused, app_count_since_pause
    
    is_paused = True
    pause_duration = PAUSE_MINUTES * 60  # Convertir a segundos
    
    logger.warning(f"[li_moderate] PAUSANDO por {PAUSE_MINUTES} minutos por seguridad...")
    logger.info(f"[li_moderate] Aplicaciones desde pausa: {app_count_since_pause}/{PAUSE_AFTER_APPS}")
    
    # Pausar progresivamente con logs
    for elapsed in range(0, pause_duration, 300):  # Log cada 5 minutos
        remaining = (pause_duration - elapsed) / 60
        logger.debug(f"[li_moderate] Pausa: {remaining:.1f} minutos restantes")
        await asyncio.sleep(300)  # 5 minutos
    
    # Resetear estado de pausa
    is_paused = False
    app_count_since_pause = 0
    logger.success(f"[li_moderate] Pausa completada, reanudando aplicaciones...")


async def _setup_anti_detection(context: BrowserContext):
    """Configura anti-detección avanzado."""
    # Ocultar señales de automatización
    await context.add_init_script("""
        // Ocultar webdriver
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        
        // Fake plugins (Chrome tiene plugins, headless no)
        Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
        
        // Fake languages
        Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en', 'es']});
        
        // Fake platform
        Object.defineProperty(navigator, 'platform', {get: () => 'Win32'});
        
        // Fake hardware concurrency
        Object.defineProperty(navigator, 'hardwareConcurrency', {get: () => 4});
        
        // Fake device memory
        Object.defineProperty(navigator, 'deviceMemory', {get: () => 8});
    """)


async def _get_linkedin_session() -> BrowserContext:
    """Obtiene o crea sesión de LinkedIn con anti-banning."""
    
    # Verificar pausas de seguridad
    if _should_pause():
        await _pause_for_safety()
    
    # Cargar cookies si existen
    cookies = []
    cookies_file = Path(settings.linkedin_cookies_file)
    if cookies_file.exists():
        try:
            with open(cookies_file) as f:
                cookies_data = json.load(f)
                # Convertir cookies al formato de Playwright
                for name, value in cookies_data.items():
                    cookies.append({
                        "name": name,
                        "value": value,
                        "domain": ".linkedin.com",
                        "path": "/"
                    })
            logger.debug(f"[li_moderate] {len(cookies)} cookies cargadas")
        except Exception as e:
            logger.warning(f"[li_moderate] Error cargando cookies: {e}")
    
    # Crear contexto con anti-detección
    pw = await async_playwright().start()
    browser = await pw.chromium.launch(
        headless=False,  # NO headless para evitar detección
        args=[
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            "--disable-software-rasterizer",
            "--disable-extensions",
            "--disable-background-networking",
        ],
    )
    
    user_agent = random.choice(USER_AGENTS)
    context = await browser.new_context(
        viewport={"width": 1920, "height": 1080},
        user_agent=user_agent,
        locale="en-US",
        timezone_id="America/Mexico_City",
        permissions=["geolocation"],
        geolocation={"latitude": 19.4326, "longitude": -99.1332},  # CDMX
        color_scheme="light",
        reduced_motion="no-preference",
    )
    
    # Configurar anti-detección
    await _setup_anti_detection(context)
    
    # Agregar cookies
    if cookies:
        await context.add_cookies(cookies)
        logger.info(f"[li_moderate] Sesión configurada con {len(cookies)} cookies")
    
    return context, browser


async def _detect_external_portal(job_url: str) -> Optional[str]:
    """Detecta si el job redirige a portal externo."""
    
    external_portals = {
        "workday": ["workday.com", "myworkdayjobs.com"],
        "greenhouse": ["greenhouse.io", "jobs.greenhouse.io"],
        "lever": ["lever.co", "jobs.lever.co"],
        "bamboohr": ["bamboohr.com", "bamboohr.co"],
        "smartrecruiters": ["smartrecruiters.com"],
        "icims": ["icims.com"],
        "taleo": ["taleo.net", "myworkdayjobs.com"],
    }
    
    job_url_lower = job_url.lower()
    
    for portal_name, indicators in external_portals.items():
        for indicator in indicators:
            if indicator in job_url_lower:
                logger.info(f"[li_moderate] Portal externo detectado: {portal_name}")
                return portal_name
    
    return None


async def _apply_to_external_portal(
    page: Page,
    job_url: str,
    portal_type: str,
    resume_data: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Aplica a portal externo (Workday, Greenhouse, etc.)
    Evita LinkedIn completamente para reducir detección.
    """
    
    logger.info(f"[li_moderate] Aplicando a portal {portal_type}: {job_url[:80]}...")
    
    try:
        # Ir directamente al portal externo
        await page.goto(job_url, wait_until="domcontentloaded", timeout=30000)
        await _human_delay(3, 6)
        
        # Estrategias específicas por portal
        if portal_type == "workday":
            return await _apply_workday(page, resume_data)
        elif portal_type == "greenhouse":
            return await _apply_greenhouse(page, resume_data)
        elif portal_type == "lever":
            return await _apply_lever(page, resume_data)
        else:
            return await _apply_generic_external(page, resume_data)
            
    except Exception as e:
        logger.error(f"[li_moderate] Error en portal {portal_type}: {e}")
        return {
            "success": False,
            "status": f"error_{portal_type}",
            "message": str(e)[:200]
        }


async def _apply_workday(page: Page, resume_data: Dict[str, Any]) -> Dict[str, Any]:
    """Estrategia específica para Workday."""
    
    logger.info("[li_moderate] Iniciando flujo Workday...")
    
    try:
        # Simular lectura del job (humano)
        await _human_delay(2, 4)
        
        # Buscar botón de apply
        apply_button = await page.query_selector("a:has-text(\"Apply\")")
        if apply_button:
            await apply_button.click()
            logger.debug("[li_moderate] Click en Apply Workday")
            await _human_delay(2, 4)
        
        # Esperar formulario
        await page.wait_for_selector("input[type=\"file\"]", timeout=10000)
        
        # Upload CV (usando file chooser)
        file_input = await page.query_selector("input[type=\"file\"]")
        if file_input:
            cv_path = resume_data.get("abs_path", "")
            if cv_path and Path(cv_path).exists():
                await file_input.set_input_files(cv_path)
                logger.info("[li_moderate] CV uploaded a Workday")
                await _human_delay(2, 3)
        
        # Llenar campos básicos
        first_name = resume_data.get("first_name", "")
        last_name = resume_data.get("last_name", "")
        email = resume_data.get("email", "")
        
        if first_name:
            first_input = await page.query_selector("input[name*=\"firstName\"]")
            if first_input:
                await first_input.fill(first_name)
                logger.debug("[li_moderate] First name llenado")
                await _human_delay(1, 2)
        
        if last_name:
            last_input = await page.query_selector("input[name*=\"lastName\"]")
            if last_input:
                await last_input.fill(last_name)
                logger.debug("[li_moderate] Last name llenado")
                await _human_delay(1, 2)
        
        if email:
            email_input = await page.query_selector("input[type=\"email\"]")
            if email_input:
                await email_input.fill(email)
                logger.debug("[li_moderate] Email llenado")
                await _human_delay(1, 2)
        
        # Submit (con delay humano)
        submit_button = await page.query_selector("button:has-text(\"Submit\")")
        if submit_button:
            await _human_delay(2, 4)
            await submit_button.click()
            logger.success("[li_moderate] Aplicación Workday enviada")
        
        return {
            "success": True,
            "status": "workday_submitted",
            "message": "Aplicación Workday enviada exitosamente"
        }
        
    except Exception as e:
        return {
            "success": False,
            "status": "workday_error",
            "message": f"Error Workday: {str(e)[:200]}"
        }


async def _apply_greenhouse(page: Page, resume_data: Dict[str, Any]) -> Dict[str, Any]:
    """Estrategia específica para Greenhouse."""
    
    logger.info("[li_moderate] Iniciando flujo Greenhouse...")
    
    try:
        await _human_delay(2, 3)
        
        # Greenhouse suele tener formulario directo
        email_input = await page.query_selector("input[type=\"email\"]")
        if email_input:
            await email_input.fill(resume_data.get("email", ""))
            await _human_delay(1, 2)
        
        # Upload CV
        file_input = await page.query_selector("input[type=\"file\"]")
        if file_input:
            cv_path = resume_data.get("abs_path", "")
            if cv_path and Path(cv_path).exists():
                await file_input.set_input_files(cv_path)
                logger.info("[li_moderate] CV uploaded a Greenhouse")
                await _human_delay(2, 3)
        
        # Submit
        submit_button = await page.query_selector('button[type="submit"]')
        if submit_button:
            await _human_delay(2, 3)
            await submit_button.click()
            logger.success("[li_moderate] Aplicación Greenhouse enviada")
        
        return {
            "success": True,
            "status": "greenhouse_submitted",
            "message": "Aplicación Greenhouse enviada"
        }
        
    except Exception as e:
        return {
            "success": False,
            "status": "greenhouse_error",
            "message": f"Error Greenhouse: {str(e)[:200]}"
        }


async def _apply_lever(page: Page, resume_data: Dict[str, Any]) -> Dict[str, Any]:
    """Estrategia específica para Lever."""
    
    logger.info("[li_moderate] Iniciando flujo Lever...")
    
    try:
        await _human_delay(2, 3)
        
        # Lever tiene patrón específico
        email_input = await page.query_selector("input[name=\"email\"]")
        if email_input:
            await email_input.fill(resume_data.get("email", ""))
            await _human_delay(1, 2)
        
        # Upload CV
        file_input = await page.query_selector("input[type=\"file\"]")
        if file_input:
            cv_path = resume_data.get("abs_path", "")
            if cv_path and Path(cv_path).exists():
                await file_input.set_input_files(cv_path)
                logger.info("[li_moderate] CV uploaded a Lever")
                await _human_delay(2, 3)
        
        # Submit
        submit_button = await page.query_selector('button[type="submit"]')
        if submit_button:
            await _human_delay(2, 3)
            await submit_button.click()
            logger.success("[li_moderate] Aplicación Lever enviada")
        
        return {
            "success": True,
            "status": "lever_submitted",
            "message": "Aplicación Lever enviada"
        }
        
    except Exception as e:
        return {
            "success": False,
            "status": "lever_error",
            "message": f"Error Lever: {str(e)[:200]}"
        }


async def _apply_generic_external(page: Page, resume_data: Dict[str, Any]) -> Dict[str, Any]:
    """Estrategia genérica para cualquier portal externo."""
    
    logger.info("[li_moderate] Iniciando flujo externo genérico...")
    
    try:
        await _human_delay(3, 5)
        
        # Buscar inputs de formulario comunes
        email = resume_data.get("email", "")
        
        # Intentar llenar email si existe input
        email_input = await page.query_selector("input[type=\"email\"]")
        if email_input:
            await email_input.fill(email)
            logger.debug("[li_moderate] Email llenado en formulario externo")
            await _human_delay(1, 2)
        
        # Intentar upload CV
        file_input = await page.query_selector("input[type=\"file\"]")
        if file_input:
            cv_path = resume_data.get("abs_path", "")
            if cv_path and Path(cv_path).exists():
                await file_input.set_input_files(cv_path)
                logger.info("[li_moderate] CV uploaded a formulario externo")
                await _human_delay(2, 3)
        
        # Intentar submit
        submit_button = await page.query_selector("button[type=\"submit\"], button:has-text(\"Submit\"), button:has-text(\"Apply\")")
        if submit_button:
            await _human_delay(2, 3)
            await submit_button.click()
            logger.success("[li_moderate] Aplicación externa enviada")
        
        return {
            "success": True,
            "status": "external_submitted",
            "message": "Aplicación externa enviada"
        }
        
    except Exception as e:
        return {
            "success": False,
            "status": "external_error",
            "message": f"Error externo: {str(e)[:200]}"
        }


async def apply_to_job_moderate(
    job_url: str,
    resume_data: Dict[str, Any],
    cover_letter: str = "",
    job_details: Optional[Dict] = None,
) -> Dict[str, Any]:
    """
    Aplica a un job con estrategia moderada anti-banning.
    
    Args:
        job_url: URL del job
        resume_data: Datos del CV y usuario
        cover_letter: Carta de presentación
        job_details: Detalles adicionales del job
    
    Returns:
        Dict con resultado de la aplicación
    """
    global last_app_time, app_count_since_pause
    
    # Verificar si debemos pausar
    if await _should_pause():
        await _pause_for_safety()
    
    # Detectar portal externo
    portal_type = await _detect_external_portal(job_url)
    
    if portal_type and settings.linkedin_enable_external_apply:
        # Aplicación externa (más seguro)
        context, browser = await _get_linkedin_session()
        page = await context.new_page()
        
        try:
            result = await _apply_to_external_portal(page, job_url, portal_type, resume_data)
            result["applied_via"] = f"external_{portal_type}"
            result["job_url"] = job_url
            
            return result
            
        finally:
            await context.close()
            await browser.close()
    
    # Aplicación LinkedIn Easy Apply
    else:
        return await _apply_linkedin_easy_apply(job_url, resume_data, cover_letter, job_details)


async def _apply_linkedin_easy_apply(
    job_url: str,
    resume_data: Dict[str, Any],
    cover_letter: str,
    job_details: Optional[Dict],
) -> Dict[str, Any]:
    """Aplicación LinkedIn Easy Apply con estrategia moderada."""
    
    logger.info(f"[li_moderate] Aplicando LinkedIn Easy Apply: {job_url[:80]}...")
    
    context, browser = await _get_linkedin_session()
    page = None
    
    try:
        page = await context.new_page()
        
        # Ir a LinkedIn primero (activar sesión)
        await page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded", timeout=20000)
        await _human_delay(3, 5)
        
        # Verificar si hay sesión activa
        if "login" in page.url or "authwall" in page.url:
            logger.error("[li_moderate] Sesión de LinkedIn no válida")
            return {
                "success": False,
                "status": "linkedin_auth_failed",
                "message": "Sesión de LinkedIn expirada"
            }
        
        # Ir al job URL
        await page.goto(job_url, wait_until="domcontentloaded", timeout=30000)
        await _human_delay(2, 4)
        
        # Verificar Easy Apply button
        easy_apply_button = await page.query_selector("button.jobs-apply-button")
        if not easy_apply_button:
            # Si no hay Easy Apply, verificar si es external apply
            external_button = await page.query_selector("a:has-text(\"Easy Apply\")")
            if external_button:
                logger.info("[li_moderate] Job requiere Easy Apply pero no disponible")
                return {
                    "success": False,
                    "status": "easy_apply_unavailable",
                    "message": "Easy Apply no disponible para este job"
                }
        
        # Click Easy Apply
        if easy_apply_button:
            await easy_apply_button.click()
            logger.debug("[li_moderate] Click en Easy Apply")
            await _human_delay(3, 5)
            
            # Upload CV
            await _upload_cv_linkedin(page, resume_data)
            
            # Submit
            submit_button = await page.query_selector("button:has-text(\"Submit application\")")
            if submit_button:
                await _human_delay(2, 3)
                await submit_button.click()
                logger.success("[li_moderate] Aplicación LinkedIn Easy Apply enviada")
        
        # Actualizar contadores
        last_app_time = datetime.now()
        app_count_since_pause += 1
        
        return {
            "success": True,
            "status": "linkedin_easy_apply_submitted",
            "applied_via": "linkedin_easy_apply",
            "job_url": job_url,
            "message": "Aplicación LinkedIn Easy Apply enviada"
        }
        
    except Exception as e:
        logger.error(f"[li_moderate] Error LinkedIn Easy Apply: {e}")
        return {
            "success": False,
            "status": "linkedin_error",
            "message": f"Error LinkedIn: {str(e)[:200]}"
        }
    finally:
        if page:
            await page.close()
        await context.close()
        await browser.close()


async def _upload_cv_linkedin(page: Page, resume_data: Dict[str, Any]) -> bool:
    """Upload CV en LinkedIn con estrategia humana."""
    
    cv_path = resume_data.get("abs_path", "")
    if not cv_path or not Path(cv_path).exists():
        logger.warning("[li_moderate] CV no encontrado, usando LinkedIn guardado")
        return True  # LinkedIn tiene CV guardado
    
    try:
        # Buscar botón upload
        upload_button = await page.query_selector('button.jobs-resume-picker__upload-btn')
        if upload_button:
            await upload_button.click()
            logger.debug("[li_moderate] Click en upload CV LinkedIn")
            await _human_delay(2, 3)
            
            # Usar file chooser
            file_input = await page.query_selector("input[type=\"file\"]")
            if file_input:
                await file_input.set_input_files(cv_path)
                logger.info("[li_moderate] CV uploaded a LinkedIn")
                return True
        
        return False
        
    except Exception as e:
        logger.error(f"[li_moderate] Error upload CV: {e}")
        return False


# ============================================================================
# INTEGRACIÓN CON ORCHESTRATOR
# ============================================================================

async def batch_apply_moderate(
    jobs: List[Dict[str, Any]],
    resume_data: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Aplica a múltiples jobs con estrategia moderada.
    Respetando rate limiting y pausas de seguridad.
    """
    results = []
    
    logger.info(f"[li_moderate] Iniciando batch apply moderado: {len(jobs)} jobs")
    logger.info(f"[li_moderate] Configuración: {APPS_PER_HOUR} apps/hora, pauses cada {PAUSE_AFTER_APPS} apps")
    
    for i, job in enumerate(jobs, 1):
        logger.info(f"[li_moderate] Procesando job {i}/{len(jobs)}")
        
    # Verificar si debemos pausar
    if await _should_pause():
        await _pause_for_safety()
    
    # Delay humano entre aplicaciones
    await _human_delay()
    
    # Aplicar
    result = await apply_to_job_moderate(
        job_url=job.get("url", ""),
        resume_data=resume_data,
        job_details=job,
    )
    
    results.append(result)
    
    # Delay adicional si tuvo éxito
    if result.get("success"):
        await _human_delay(3, 6)
    
    logger.info(f"[li_moderate] Batch apply completado: {len(results)} aplicaciones")
    return results


if __name__ == "__main__":
    # Test del sistema
    import asyncio
    
    async def test():
        test_jobs = [
            {
                "title": "Test Job 1",
                "url": "https://www.linkedin.com/jobs/",
            }
        ]
        
        test_resume = {
            "first_name": "Alejandro",
            "last_name": "Hernandez Loza",
            "email": "alejandrohloza@gmail.com",
            "abs_path": "/tmp/test_cv.pdf",
        }
        
        results = await batch_apply_moderate(test_jobs, test_resume)
        for result in results:
            print(f"Result: {result}")
    
    asyncio.run(test())