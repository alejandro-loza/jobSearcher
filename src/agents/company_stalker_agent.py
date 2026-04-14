"""
Company Stalker Agent.

Busca vacantes en una empresa específica que hagan match con el perfil de Alejandro.
Si encuentra algo bueno (score >= 75), intenta aplicar automáticamente.
Si no puede aplicar, notifica por WhatsApp.

Usa GLM via coordinator para evaluar match.
"""

import json
import time
from datetime import datetime, date
from typing import Dict, Any, List, Optional, Tuple
from loguru import logger

from src.tools import jobspy_tool, whatsapp_tool
from src.agents import master_agent
from src.db.tracker import JobTracker

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

MATCH_THRESHOLD = 75
MAX_RESULTS = 15
HOURS_OLD = 168  # 7 días

# Empresas descartadas — no stalkear ni aplicar
BLACKLISTED_COMPANIES = [
    "Capital One",
]

# Términos de búsqueda por defecto (perfil Alejandro)
DEFAULT_SEARCH_TERMS = [
    "Java Developer",
    "Software Engineer",
    "Backend Engineer",
    "Spring Boot",
    "Full Stack Developer",
]

# Empresas a stalkear con términos específicos (override del default)
COMPANY_SEARCH_OVERRIDES: Dict[str, List[str]] = {
    "Thomson Reuters": [
        "Thomson Reuters Java",
        "Thomson Reuters software engineer",
        "Thomson Reuters developer Mexico",
        "Thomson Reuters Spring Boot",
        "Thomson Reuters backend",
    ],
}

# Log de stalking para evitar notificar duplicados
STALKER_LOG_FILE = "data/stalker_log.json"


def _load_log() -> dict:
    try:
        with open(STALKER_LOG_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"notified_jobs": {}, "applied_jobs": {}, "daily_stats": {}}


def _save_log(log: dict):
    with open(STALKER_LOG_FILE, "w") as f:
        json.dump(log, f, indent=2, default=str)


def _load_resume() -> dict:
    try:
        with open("data/resume.json", "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error cargando resume.json: {e}")
        return {}


def _already_notified(log: dict, job_id: str) -> bool:
    return job_id in log.get("notified_jobs", {})


def _already_applied(log: dict, job_id: str) -> bool:
    return job_id in log.get("applied_jobs", {})


def _record_notification(log: dict, job_id: str, job: dict, score: int):
    log.setdefault("notified_jobs", {})[job_id] = {
        "title": job.get("title", ""),
        "company": job.get("company", ""),
        "location": job.get("location", ""),
        "url": job.get("url", ""),
        "easy_apply": job.get("easy_apply", False),
        "score": score,
        "notified_at": datetime.now().isoformat(),
    }


def _record_application(log: dict, job_id: str, job: dict, method: str, success: bool):
    log.setdefault("applied_jobs", {})[job_id] = {
        "title": job.get("title", ""),
        "company": job.get("company", ""),
        "method": method,
        "success": success,
        "applied_at": datetime.now().isoformat(),
    }


def _increment_daily_stats(
    log: dict, company: str, found: int, matched: int, applied: int
):
    today = date.today().isoformat()
    stats = log.setdefault("daily_stats", {}).setdefault(today, {})
    entry = stats.setdefault(company, {"found": 0, "matched": 0, "applied": 0})
    entry["found"] += found
    entry["matched"] += matched
    entry["applied"] += applied


def _try_easy_apply(job: dict, resume: dict, tracker: JobTracker) -> Tuple[bool, str]:
    """Intenta Easy Apply via browser tool. Registra resultado en DB."""
    if not job.get("easy_apply"):
        return False, "not_easy_apply"

    # Registrar intento
    tracker.save_application(
        job_id=job["id"],
        method="easy_apply_stalker",
        status="apply_attempted",
        method_detail="linkedin_easy_apply",
    )

    try:
        from src.tools import browser_tool

        result = browser_tool.apply_to_job_sync(
            job_url=job["url"],
            resume=resume,
            job_title=job["title"],
            company=job["company"],
        )
        success = result.get("success", False)
        status = result.get("status", "error")
        message = result.get("message", "")

        if success:
            tracker.update_application_status(job["id"], "applied")
            return True, "easy_apply_ok"

        # Mapear status del browser_tool a nuestros status
        if status == "captcha":
            tracker.update_application_status(
                job["id"], "apply_captcha", f"Captcha: {message}"
            )
        elif status == "need_user":
            tracker.update_application_status(job["id"], "apply_needs_manual", message)
        else:
            tracker.update_application_status(
                job["id"], "apply_failed", f"{status}: {message}"
            )

        return False, f"easy_apply_failed:{status}"
    except Exception as e:
        tracker.update_application_status(job["id"], "apply_failed", str(e))
        logger.error(f"Error en Easy Apply para {job['title']}: {e}")
        return False, f"easy_apply_error:{e}"


def _try_external_apply(
    job: dict, resume: dict, tracker: JobTracker
) -> Tuple[bool, str]:
    """Intenta aplicar via browser tool en portal externo. Registra resultado en DB."""
    if not job.get("url"):
        tracker.save_application(
            job_id=job["id"],
            method="external_stalker",
            status="apply_failed",
            failure_reason="no_url",
        )
        return False, "no_url"

    # Registrar intento
    tracker.save_application(
        job_id=job["id"],
        method="external_stalker",
        status="apply_attempted",
        method_detail=job.get("url", ""),
    )

    try:
        from src.tools import browser_tool

        result = browser_tool.apply_to_job_sync(
            job_url=job["url"],
            resume=resume,
            job_title=job["title"],
            company=job["company"],
        )
        success = result.get("success", False)
        status = result.get("status", "error")
        message = result.get("message", "")

        if success:
            tracker.update_application_status(job["id"], "applied")
            return True, "external_apply_ok"

        if status == "captcha":
            tracker.update_application_status(
                job["id"], "apply_captcha", f"Captcha: {message}"
            )
        elif status == "need_user":
            tracker.update_application_status(job["id"], "apply_needs_manual", message)
        else:
            tracker.update_application_status(
                job["id"], "apply_failed", f"{status}: {message}"
            )

        return False, f"external_apply_failed:{status}"
    except Exception as e:
        tracker.update_application_status(job["id"], "apply_failed", str(e))
        logger.error(f"Error en external apply para {job['title']}: {e}")
        return False, f"external_apply_error:{e}"


def stalk_company(
    company: str,
    search_terms: Optional[List[str]] = None,
    locations: Optional[List[str]] = None,
    auto_apply: bool = False,
    notify_whatsapp: bool = True,
) -> dict:
    """
    Busca vacantes en una empresa específica y actúa sobre ellas.

    Args:
        company: Nombre de la empresa a stalkear
        search_terms: Términos de búsqueda (default: DEFAULT_SEARCH_TERMS con company)
        locations: Ubicaciones a buscar (default: remote + Mexico)
        auto_apply: DEPRECATED desde 2026-04 — default ahora es False. El
            application_agent (cada 2min) es el único punto de aplicación. Los
            stalkers solo guardan en BD con status='found' y dejan que la cola
            centralizada priorice y aplique con rate limiting global.
        notify_whatsapp: Notificar por WhatsApp si encuentra match

    Returns:
        dict con estadísticas del stalking
    """
    if company in BLACKLISTED_COMPANIES:
        logger.info(f"[STALKER] {company} está en blacklist — skipping")
        return {"company": company, "skipped": True}

    logger.info(f"[STALKER] Iniciando stalking de {company}...")

    log = _load_log()
    resume = _load_resume()
    if not resume:
        logger.error("[STALKER] No se pudo cargar resume.json")
        return {"error": "no_resume"}

    tracker = JobTracker()

    # Determinar términos de búsqueda
    if search_terms is None:
        search_terms = COMPANY_SEARCH_OVERRIDES.get(
            company,
            [f"{company} {term}" for term in DEFAULT_SEARCH_TERMS[:3]],
        )

    if locations is None:
        locations = ["remote", "Mexico"]

    # Buscar vacantes
    all_jobs = []
    seen_ids = set()

    for term in search_terms:
        for location in locations:
            try:
                jobs = jobspy_tool.search_jobs(
                    search_term=term,
                    location=location,
                    results_wanted=MAX_RESULTS,
                    hours_old=HOURS_OLD,
                    site_names=["linkedin", "indeed"],
                )
                for j in jobs:
                    # Filtrar: solo jobs de esta empresa
                    if company.lower() not in j.get("company", "").lower():
                        continue
                    if j["id"] not in seen_ids:
                        seen_ids.add(j["id"])
                        all_jobs.append(j)

                # Rate limit entre búsquedas
                time.sleep(2)
            except Exception as e:
                logger.error(f"[STALKER] Error buscando '{term}' en {location}: {e}")

    logger.info(f"[STALKER] {company}: {len(all_jobs)} vacantes encontradas (dedup)")

    if not all_jobs:
        _increment_daily_stats(log, company, 0, 0, 0)
        _save_log(log)
        return {
            "company": company,
            "found": 0,
            "matched": 0,
            "applied": 0,
            "notified": 0,
        }

    # Evaluar match con CV
    matched_jobs = []
    for job in all_jobs:
        # Skip si ya notificamos o aplicamos
        if _already_notified(log, job["id"]) or _already_applied(log, job["id"]):
            continue

        try:
            score, reasons = master_agent.evaluate_job_match(job, resume)
            job["match_score"] = score
            job["match_reasons"] = reasons

            if score >= MATCH_THRESHOLD:
                matched_jobs.append(job)
                logger.info(
                    f"[STALKER] MATCH {score}%: {job['title']} @ {company} | {reasons}"
                )

            # Guardar en DB
            job["match_score"] = score
            tracker.save_job(job)

            # Rate limit entre evaluaciones
            time.sleep(1)
        except Exception as e:
            logger.error(f"[STALKER] Error evaluando {job['title']}: {e}")

    # Intentar aplicar y notificar
    applied_count = 0
    notified_count = 0

    for job in matched_jobs:
        applied = False
        method = "none"

        if auto_apply:
            # Primero intentar Easy Apply
            applied, method = _try_easy_apply(job, resume, tracker)

            # Si no es Easy Apply, intentar portal externo
            if not applied and method == "not_easy_apply":
                applied, method = _try_external_apply(job, resume, tracker)

            if applied:
                applied_count += 1
                _record_application(log, job["id"], job, method, True)
                logger.success(
                    f"[STALKER] Aplicado: {job['title']} @ {company} ({method})"
                )

        # Notificar por WhatsApp
        if notify_whatsapp:
            score = job.get("match_score", 0)
            ea = "Easy Apply" if job.get("easy_apply") else "External"

            if applied:
                msg = (
                    f"*[STALKER {company}]*\n\n"
                    f"Aplique automaticamente:\n"
                    f"*{job['title']}* ({score}% match)\n"
                    f"📍 {job.get('location', 'N/A')}\n"
                    f"🔗 {job.get('url', '')}\n"
                    f"✅ Metodo: {method}"
                )
            else:
                msg = (
                    f"*[STALKER {company}]*\n\n"
                    f"Nueva vacante encontrada ({score}% match):\n"
                    f"*{job['title']}*\n"
                    f"📍 {job.get('location', 'N/A')}\n"
                    f"🔗 {job.get('url', '')}\n"
                    f"📋 {ea}\n"
                    f"❌ No pude aplicar automaticamente ({method})\n\n"
                    f"¿Quieres que lo intente de nuevo o aplicas manual?"
                )

            whatsapp_tool.send_message(msg)
            notified_count += 1
            _record_notification(log, job["id"], job, score)

    _increment_daily_stats(
        log, company, len(all_jobs), len(matched_jobs), applied_count
    )
    _save_log(log)

    result = {
        "company": company,
        "found": len(all_jobs),
        "matched": len(matched_jobs),
        "applied": applied_count,
        "notified": notified_count,
        "jobs": [
            {
                "title": j["title"],
                "score": j.get("match_score", 0),
                "url": j.get("url", ""),
                "location": j.get("location", ""),
            }
            for j in matched_jobs
        ],
    }

    logger.info(
        f"[STALKER] {company}: found={result['found']} matched={result['matched']} applied={result['applied']}"
    )
    return result


def stalk_multiple(companies: List[str], **kwargs) -> List[dict]:
    """Stalkea múltiples empresas secuencialmente con pausa entre ellas."""
    results = []
    for i, company in enumerate(companies):
        logger.info(f"[STALKER] Procesando {i + 1}/{len(companies)}: {company}")
        try:
            result = stalk_company(company, **kwargs)
            results.append(result)
        except Exception as e:
            logger.error(f"[STALKER] Error stalkeando {company}: {e}")
            results.append({"company": company, "error": str(e)})

        # Pausa entre empresas para no saturar APIs
        if i < len(companies) - 1:
            time.sleep(5)

    # Resumen
    total_found = sum(r.get("found", 0) for r in results)
    total_matched = sum(r.get("matched", 0) for r in results)
    total_applied = sum(r.get("applied", 0) for r in results)
    logger.success(
        f"[STALKER] Batch completo: {len(companies)} empresas, "
        f"{total_found} encontradas, {total_matched} matched, {total_applied} aplicadas"
    )
    return results


def get_stalker_stats() -> dict:
    """Retorna estadísticas del stalker."""
    log = _load_log()
    return {
        "total_notified": len(log.get("notified_jobs", {})),
        "total_applied": len(log.get("applied_jobs", {})),
        "daily_stats": log.get("daily_stats", {}),
    }
