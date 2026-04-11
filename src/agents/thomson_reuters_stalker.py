"""
Thomson Reuters Dedicated Stalker.

Agente especializado en buscar vacantes en Thomson Reuters con búsqueda
exhaustiva: múltiples términos, múltiples ubicaciones, múltiples sites.
Corre cada hora (más frecuente que los stalkers genéricos).

IMPORTANTE: No envía mensajes ni emails a Thomson Reuters HR.
Alejandro maneja el reingreso personalmente via Melba Ruiz Moron.
Solo busca, evalúa, y notifica por WhatsApp.
"""
import json
import time
from datetime import datetime, date
from typing import Dict, List, Tuple
from loguru import logger

from src.tools import jobspy_tool, whatsapp_tool
from src.agents import master_agent
from src.db.tracker import JobTracker

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

MATCH_THRESHOLD = 70  # Más permisivo que el stalker genérico (75)
HOURS_OLD = 336       # 14 días — ventana más amplia
LOG_FILE = "data/thomson_reuters_stalker_log.json"

# Búsqueda exhaustiva: todos los términos posibles que TR usa en sus vacantes
SEARCH_TERMS = [
    # Directos
    "Thomson Reuters Java",
    "Thomson Reuters software engineer",
    "Thomson Reuters backend",
    "Thomson Reuters Spring Boot",
    "Thomson Reuters developer",
    "Thomson Reuters full stack",
    "Thomson Reuters senior engineer",
    "Thomson Reuters cloud engineer",
    "Thomson Reuters microservices",
    # Productos/equipos TR
    "Thomson Reuters platform engineering",
    "Thomson Reuters AI engineer",
    "Thomson Reuters Materia",
    "Thomson Reuters Westlaw engineer",
    "Thomson Reuters CIAM",
    # Genéricos que TR publica
    "Thomson Reuters Golang",       # usan Go en platform
    "Thomson Reuters Kubernetes",
    "Thomson Reuters Mexico",
]

LOCATIONS = [
    "remote",
    "Mexico",
    "Mexico City",
    "United States",
    "Canada",
]

SITES = ["linkedin", "indeed"]


def _load_log() -> dict:
    try:
        with open(LOG_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {
            "known_jobs": {},       # job_id -> {title, score, first_seen, last_seen, notified}
            "notified_jobs": {},    # job_id -> {notified_at}
            "runs": [],            # [{timestamp, found, new, matched}]
        }


def _save_log(log: dict):
    with open(LOG_FILE, "w") as f:
        json.dump(log, f, indent=2, default=str)


def _is_thomson_reuters(company: str) -> bool:
    """Verifica si la empresa es Thomson Reuters (varias formas de escribirlo)."""
    c = company.lower().strip()
    return any(kw in c for kw in ["thomson reuters", "thomson-reuters", "thomsonreuters", "tr labs"])


def stalk() -> dict:
    """
    Búsqueda exhaustiva de vacantes en Thomson Reuters.

    Returns:
        dict con estadísticas del stalking
    """
    logger.info("[TR-STALKER] Iniciando búsqueda exhaustiva en Thomson Reuters...")
    start_time = time.time()

    log = _load_log()
    resume = _load_resume()
    if not resume:
        return {"error": "no_resume"}

    tracker = JobTracker()

    # Fase 1: Búsqueda masiva con dedup
    all_jobs = {}  # id -> job
    search_count = 0

    for term in SEARCH_TERMS:
        for location in LOCATIONS:
            try:
                jobs = jobspy_tool.search_jobs(
                    search_term=term,
                    location=location,
                    results_wanted=15,
                    hours_old=HOURS_OLD,
                    site_names=SITES,
                )
                for j in jobs:
                    if _is_thomson_reuters(j.get("company", "")) and j["id"] not in all_jobs:
                        all_jobs[j["id"]] = j

                search_count += 1
                time.sleep(1.5)  # Rate limit
            except Exception as e:
                logger.warning(f"[TR-STALKER] Error en '{term}' / {location}: {e}")

    logger.info(f"[TR-STALKER] {search_count} búsquedas → {len(all_jobs)} vacantes únicas de TR")

    # Fase 2: Identificar vacantes nuevas (no vistas antes)
    new_jobs = []
    for job_id, job in all_jobs.items():
        if job_id in log.get("known_jobs", {}):
            # Actualizar last_seen
            log["known_jobs"][job_id]["last_seen"] = datetime.now().isoformat()
        else:
            new_jobs.append(job)
            log.setdefault("known_jobs", {})[job_id] = {
                "title": job["title"],
                "company": job["company"],
                "location": job.get("location", ""),
                "url": job.get("url", ""),
                "first_seen": datetime.now().isoformat(),
                "last_seen": datetime.now().isoformat(),
                "score": None,
                "notified": False,
            }

    logger.info(f"[TR-STALKER] {len(new_jobs)} vacantes NUEVAS (no vistas antes)")

    # Fase 3: Evaluar match de vacantes nuevas con CV
    matched_jobs = []
    for job in new_jobs:
        try:
            score, reasons = master_agent.evaluate_job_match(job, resume)
            job["match_score"] = score
            job["match_reasons"] = reasons
            log["known_jobs"][job["id"]]["score"] = score

            # Guardar en DB
            tracker.save_job(job, score)

            if score >= MATCH_THRESHOLD:
                matched_jobs.append(job)
                logger.info(f"[TR-STALKER] MATCH {score}%: {job['title']} | {job.get('location','')} | {reasons}")

            time.sleep(1)
        except Exception as e:
            logger.error(f"[TR-STALKER] Error evaluando '{job['title']}': {e}")

    # Fase 4: Notificar por WhatsApp (solo vacantes nuevas con match)
    notified = 0
    for job in matched_jobs:
        job_id = job["id"]
        if log.get("notified_jobs", {}).get(job_id):
            continue  # Ya notificado

        score = job.get("match_score", 0)
        ea = "Easy Apply" if job.get("easy_apply") else "Portal externo"

        msg = (
            f"*[THOMSON REUTERS]*\n\n"
            f"Nueva vacante detectada ({score}% match):\n\n"
            f"*{job['title']}*\n"
            f"📍 {job.get('location', 'N/A')}\n"
            f"📋 {ea}\n"
            f"🔗 {job.get('url', '')}\n\n"
            f"💡 {job.get('match_reasons', '')}\n\n"
            f"_Recuerda: estas manejando el reingreso via Melba. "
            f"Esta vacante te puede servir de referencia._"
        )

        whatsapp_tool.send_message(msg)
        notified += 1
        log.setdefault("notified_jobs", {})[job_id] = {
            "title": job.get("title", ""),
            "location": job.get("location", ""),
            "url": job.get("url", ""),
            "score": job.get("match_score", 0),
            "easy_apply": job.get("easy_apply", False),
            "notified_at": datetime.now().isoformat(),
        }
        log["known_jobs"][job_id]["notified"] = True
        time.sleep(2)

    # Fase 5: Reporte resumen si hay hallazgos significativos
    if len(new_jobs) >= 3 or len(matched_jobs) >= 1:
        summary_lines = []
        for j in matched_jobs[:5]:
            summary_lines.append(f"  • {j['title']} ({j.get('match_score',0)}%) - {j.get('location','')}")

        if not summary_lines:
            summary_lines = [f"  • {j['title']} - {j.get('location','')}" for j in new_jobs[:3]]

        summary = "\n".join(summary_lines)
        whatsapp_tool.send_message(
            f"*[TR-STALKER resumen]*\n"
            f"Encontré {len(all_jobs)} vacantes totales en TR\n"
            f"{len(new_jobs)} nuevas, {len(matched_jobs)} con match >= {MATCH_THRESHOLD}%\n\n"
            f"Destacadas:\n{summary}"
        )

    # Guardar run
    elapsed = round(time.time() - start_time, 1)
    log.setdefault("runs", []).append({
        "timestamp": datetime.now().isoformat(),
        "searches": search_count,
        "total_found": len(all_jobs),
        "new": len(new_jobs),
        "matched": len(matched_jobs),
        "notified": notified,
        "elapsed_seconds": elapsed,
    })
    # Mantener solo últimos 100 runs
    log["runs"] = log["runs"][-100:]
    _save_log(log)

    result = {
        "total_found": len(all_jobs),
        "new": len(new_jobs),
        "matched": len(matched_jobs),
        "notified": notified,
        "elapsed_seconds": elapsed,
        "matched_jobs": [
            {"title": j["title"], "score": j.get("match_score", 0), "location": j.get("location", ""), "url": j.get("url", "")}
            for j in matched_jobs
        ],
    }

    logger.success(f"[TR-STALKER] Completado en {elapsed}s: {len(all_jobs)} total, {len(new_jobs)} nuevas, {len(matched_jobs)} match, {notified} notificadas")
    return result


def get_stats() -> dict:
    """Retorna estadísticas del stalker de TR."""
    log = _load_log()
    known = log.get("known_jobs", {})
    runs = log.get("runs", [])

    scored = [v for v in known.values() if v.get("score") is not None]
    high_match = [v for v in scored if v["score"] >= MATCH_THRESHOLD]

    return {
        "total_known_jobs": len(known),
        "total_scored": len(scored),
        "high_match": len(high_match),
        "total_notified": len(log.get("notified_jobs", {})),
        "total_runs": len(runs),
        "last_run": runs[-1] if runs else None,
        "top_jobs": sorted(
            [{"title": v["title"], "score": v["score"], "location": v.get("location", ""), "url": v.get("url", "")}
             for v in high_match],
            key=lambda x: x["score"],
            reverse=True,
        )[:10],
    }


def get_all_known_jobs() -> list:
    """Retorna todas las vacantes conocidas de TR, ordenadas por score."""
    log = _load_log()
    jobs = list(log.get("known_jobs", {}).values())
    jobs.sort(key=lambda x: x.get("score") or 0, reverse=True)
    return jobs


def _load_resume() -> dict:
    try:
        with open("data/resume.json", "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error cargando resume.json: {e}")
        return {}
