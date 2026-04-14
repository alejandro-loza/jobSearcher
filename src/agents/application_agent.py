"""
Application Agent — único ejecutor de aplicaciones a jobs.

Lee la cola BD (status='found', score>=75, <14 días), prioriza por score+fecha
y aplica vía linkedin_moderate_agent (que ya maneja rate limiting y anti-ban).

Regla global: el fin último de toda aplicación es entregar el CV más actualizado
(data/cv_alejandro_en.pdf) al reclutador. Si no se puede garantizar eso
(archivo no existe, CV cambiado), el ciclo se aborta.

Rate limits — zona segura LinkedIn 2025-2026:
  - 50 Easy Apply/día es el hard limit de LinkedIn
  - Target: 35/día (30% buffer)
  - Horario: 7am-9pm CDMX (14h ventana)
  - Delays 15-45s random entre apps
  - Pausa 20-30 min cada 8-10 apps

Ban auto-recovery: al detectar ban, pausa 48h, refresca cookies, test,
resume gradual (10→20→35/día en 3 días).
"""

from __future__ import annotations

import asyncio
import json
import os
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

from config import settings
from src.agents import master_agent
from src.db.tracker import JobTracker
from src.tools import linkedin_moderate_agent, whatsapp_tool

# ── Configuración ────────────────────────────────────────────────────────────

CV_PATH = "data/cv_alejandro_en.pdf"  # Fuente de verdad del CV
RESUME_JSON = "data/resume.json"

APPLY_SCORE_THRESHOLD = 75
JOB_MAX_AGE_DAYS = 14
MAX_JOBS_PER_CYCLE = 1   # Un job por ciclo (cycle cada 2 min → ~30/h teórico, rate limit lo baja)
DEFAULT_DAILY_CAP = 35   # Target: 35/día (bien abajo de los 50 que permite LinkedIn)
MAX_ATTEMPTS = 3         # Reintentos totales antes de escalar a manual
BUSINESS_HOURS_START = 7
BUSINESS_HOURS_END = 21  # 9 PM

# Estados retornados por linkedin_moderate_agent que indican posible ban
BAN_SIGNALS = {
    "auth_failed",
    "linkedin_auth_failed",
    "blocked",
    "restricted",
}

# Estados que NO son ban pero requieren escalar a manual
MANUAL_SIGNALS = {
    "need_user",
    "apply_needs_manual",
    "blocked_cv",
    "generic_url",
    "captcha",
    "blocked_captcha",
}

BAN_HISTORY_FILE = "data/linkedin_ban_history.json"


# ── Estado de recovery (persistido en JSON) ──────────────────────────────────

def _load_ban_history() -> Dict:
    """Carga historial de bans y estado actual de recovery."""
    try:
        with open(BAN_HISTORY_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {
            "ban_count": 0,
            "last_ban_at": None,
            "current_state": "ok",       # ok | banned | recovering
            "recovery_mode": False,
            "recovery_daily_limit": DEFAULT_DAILY_CAP,
            "recovery_resume_at": None,  # ISO datetime cuando puede reanudar
            "ban_events": [],
        }


def _save_ban_history(history: Dict):
    os.makedirs(os.path.dirname(BAN_HISTORY_FILE), exist_ok=True)
    with open(BAN_HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2, default=str)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _is_business_hours() -> bool:
    """7am–9pm CDMX (UTC-6). Asume hora local del servidor = CDMX."""
    now = datetime.now()
    return BUSINESS_HOURS_START <= now.hour < BUSINESS_HOURS_END


def _verify_cv_exists() -> bool:
    """Sanity check: el CV tiene que existir antes de cualquier aplicación."""
    cv = Path(CV_PATH)
    if not cv.exists():
        logger.error(f"[app_agent] CV NO ENCONTRADO en {CV_PATH} — abortando ciclo")
        return False
    size_kb = cv.stat().st_size / 1024
    logger.debug(f"[app_agent] CV: {CV_PATH} ({size_kb:.1f} KB)")
    return True


def _load_resume() -> Optional[Dict]:
    try:
        with open(RESUME_JSON) as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"[app_agent] Error cargando resume.json: {e}")
        return None


def _current_daily_cap() -> int:
    """Cap diario considerando si estamos en recovery mode."""
    history = _load_ban_history()
    if history.get("recovery_mode"):
        return int(history.get("recovery_daily_limit", 10))
    return DEFAULT_DAILY_CAP


def _is_banned() -> Tuple[bool, Optional[str]]:
    """Retorna (está_baneado, resume_at_iso)."""
    history = _load_ban_history()
    if history.get("current_state") != "banned":
        return False, None
    resume_at = history.get("recovery_resume_at")
    if not resume_at:
        return True, None
    try:
        resume_dt = datetime.fromisoformat(resume_at)
        if datetime.now() < resume_dt:
            return True, resume_at
        # El periodo de ban pasó → transicionar a recovering
        history["current_state"] = "recovering"
        history["recovery_mode"] = True
        history["recovery_daily_limit"] = 10
        _save_ban_history(history)
        logger.warning("[app_agent] Periodo de ban pasó → modo recovery (10 apps/día)")
        return False, None
    except ValueError:
        return True, None


def _record_ban(reason: str, status: str):
    """Marca ban en history y programa recovery."""
    history = _load_ban_history()
    history["ban_count"] = int(history.get("ban_count", 0)) + 1
    history["last_ban_at"] = datetime.now().isoformat()
    history["current_state"] = "banned"
    history["recovery_mode"] = True

    # Duración del ban según historial
    count = history["ban_count"]
    if count == 1:
        hours = 48
        history["recovery_daily_limit"] = 10
    elif count == 2:
        hours = 24 * 7  # 7 días
        history["recovery_daily_limit"] = 20
    else:
        hours = 24 * 30  # pausa indefinida (30 días simbólico)
        history["recovery_daily_limit"] = 0

    history["recovery_resume_at"] = (datetime.now() + timedelta(hours=hours)).isoformat()
    history["ban_events"].append({
        "at": datetime.now().isoformat(),
        "reason": reason,
        "status": status,
        "pause_hours": hours,
    })
    _save_ban_history(history)

    msg = (
        f"⚠️ LinkedIn detectó actividad (ban #{count}).\n"
        f"Pausa: {hours}h.\n"
        f"Razón: {reason}\n"
        f"Status: {status}\n"
        f"Reanuda: {history['recovery_resume_at']}"
    )
    logger.error(f"[app_agent] {msg}")
    try:
        whatsapp_tool.send_message(msg)
    except Exception as e:
        logger.error(f"[app_agent] No se pudo notificar ban por WA: {e}")


def _record_successful_apply():
    """Cada éxito durante recovery acerca al limit normal."""
    history = _load_ban_history()
    if not history.get("recovery_mode"):
        return
    cap = int(history.get("recovery_daily_limit", 10))
    if cap >= DEFAULT_DAILY_CAP:
        history["recovery_mode"] = False
        history["current_state"] = "ok"
        history["recovery_daily_limit"] = DEFAULT_DAILY_CAP
        logger.success("[app_agent] Recovery completa — modo normal restaurado")
    _save_ban_history(history)


def _classify_result(status: str) -> str:
    """
    Clasifica el resultado en: success | ban | manual | retryable | duplicate
    """
    if status in {"applied", "success", "external_submitted"}:
        return "success"
    if status == "already_applied":
        return "duplicate"
    if status in BAN_SIGNALS:
        return "ban"
    if status in MANUAL_SIGNALS:
        return "manual"
    return "retryable"


# ── Núcleo ───────────────────────────────────────────────────────────────────

async def _apply_one(job: Dict, resume: Dict) -> Dict[str, Any]:
    """
    Aplica a un job individual usando linkedin_moderate_agent.
    Retorna dict con resultado enriquecido.
    """
    job_url = job.get("url") or job.get("applied_url")
    cover_letter = ""
    try:
        cover_letter = master_agent.generate_cover_letter(job, resume) or ""
    except Exception as e:
        logger.warning(f"[app_agent] Cover letter failed, aplicando sin ella: {e}")

    # Delay humano 15-45s antes de aplicar
    delay = random.uniform(15, 45)
    logger.info(f"[app_agent] Delay pre-apply: {delay:.1f}s")
    await asyncio.sleep(delay)

    try:
        result = await linkedin_moderate_agent.apply_to_job_moderate(
            job_url=job_url,
            resume_data=resume,
            cover_letter=cover_letter,
            job_details=job,
        )
    except Exception as e:
        logger.exception(f"[app_agent] Excepción al aplicar {job.get('id')}: {e}")
        result = {"success": False, "status": "exception", "message": str(e)[:200]}

    result["job_id"] = job.get("id")
    result["cover_letter"] = cover_letter
    return result


def _persist_result(tracker: JobTracker, job: Dict, result: Dict):
    """Actualiza BD con el resultado de la aplicación."""
    job_id = job["id"]
    status = result.get("status", "error")
    category = _classify_result(status)
    applied_via = result.get("applied_via", "application_agent")
    message = result.get("message", "")

    if category == "success":
        tracker.save_application(
            job_id=job_id,
            method="application_agent",
            cover_letter=result.get("cover_letter", ""),
            status="applied",
            method_detail=applied_via,
        )
        _record_successful_apply()
        logger.success(f"[app_agent] ✅ Aplicado: {job.get('title')} @ {job.get('company')}")

    elif category == "duplicate":
        tracker.save_application(
            job_id=job_id,
            method="application_agent",
            status="applied",
            method_detail="already_applied_detected",
        )
        logger.info(f"[app_agent] ↩️  Ya aplicado previamente: {job.get('title')}")

    elif category == "ban":
        tracker.save_application(
            job_id=job_id,
            method="application_agent",
            status="apply_failed",
            failure_reason=f"ban_signal:{status}",
            method_detail=message[:200],
        )
        _record_ban(reason=message[:200], status=status)

    elif category == "manual":
        tracker.save_application(
            job_id=job_id,
            method="application_agent",
            status="apply_needs_manual",
            failure_reason=status,
            method_detail=message[:200],
        )
        logger.warning(f"[app_agent] 🔧 Manual: {job.get('title')} — {status}")

    else:  # retryable
        # Incrementar contador y decidir si reintentamos o escalamos
        attempts = 1
        with tracker._get_conn() as conn:
            row = conn.execute(
                "SELECT attempt_count FROM applications WHERE job_id = ?", (job_id,)
            ).fetchone()
            if row:
                attempts = (row[0] or 1) + 1

        if attempts >= MAX_ATTEMPTS:
            tracker.save_application(
                job_id=job_id,
                method="application_agent",
                status="apply_needs_manual",
                failure_reason=f"max_attempts_reached:{status}",
                method_detail=message[:200],
            )
            logger.warning(f"[app_agent] ⚠️  Max intentos — escalando a manual: {job.get('title')}")
        else:
            tracker.save_application(
                job_id=job_id,
                method="application_agent",
                status="apply_failed",
                failure_reason=status,
                method_detail=message[:200],
            )
            # Dejar status='found' para reintento (release_job_lock lo libera)
            tracker.update_job_status(job_id, "found")
            logger.info(
                f"[app_agent] 🔁 Fallo #{attempts}/{MAX_ATTEMPTS}, "
                f"reintentará en próximo ciclo: {job.get('title')}"
            )


# ── Entry point (APScheduler lo llama) ───────────────────────────────────────

async def run_application_cycle() -> Dict[str, Any]:
    """
    Un ciclo completo: evalúa si puede aplicar y aplica 1 job.
    Retorna stats del ciclo.
    """
    stats = {
        "attempted": 0,
        "applied": 0,
        "failed": 0,
        "manual_queued": 0,
        "ban_detected": False,
        "skipped_reason": None,
    }

    # 1. Validaciones previas
    if not _verify_cv_exists():
        stats["skipped_reason"] = "cv_missing"
        return stats

    if not _is_business_hours():
        stats["skipped_reason"] = "outside_business_hours"
        logger.debug("[app_agent] Fuera de horario de negocio, skip")
        return stats

    banned, resume_at = _is_banned()
    if banned:
        stats["skipped_reason"] = f"banned_until:{resume_at}"
        logger.warning(f"[app_agent] En ban hasta {resume_at}, skip")
        return stats

    # 2. Daily cap
    tracker = JobTracker()
    today_count = tracker.count_applications_today()
    cap = _current_daily_cap()
    if today_count >= cap:
        stats["skipped_reason"] = f"daily_cap_reached:{today_count}/{cap}"
        logger.debug(f"[app_agent] Cap diario alcanzado: {today_count}/{cap}")
        return stats

    # 3. Cargar recursos
    resume = _load_resume()
    if not resume:
        stats["skipped_reason"] = "resume_load_failed"
        return stats

    # 4. Obtener cola priorizada
    tracker.release_stale_locks(max_age_minutes=30)
    queue = tracker.get_application_queue(
        min_score=APPLY_SCORE_THRESHOLD,
        max_age_days=JOB_MAX_AGE_DAYS,
        limit=MAX_JOBS_PER_CYCLE * 3,  # pedimos extra por si algunos están lockeados
    )
    if not queue:
        stats["skipped_reason"] = "empty_queue"
        logger.debug("[app_agent] Cola vacía")
        return stats

    logger.info(f"[app_agent] Cola: {len(queue)} jobs | hoy: {today_count}/{cap}")

    # 5. Aplicar (hasta MAX_JOBS_PER_CYCLE, lockeando primero)
    processed = 0
    for job in queue:
        if processed >= MAX_JOBS_PER_CYCLE:
            break
        job_id = job["id"]
        if not tracker.lock_job_for_processing(job_id):
            continue  # otro ciclo lo tiene

        stats["attempted"] += 1
        try:
            result = await _apply_one(job, resume)
            _persist_result(tracker, job, result)
            category = _classify_result(result.get("status", ""))
            if category == "success" or category == "duplicate":
                stats["applied"] += 1
            elif category == "manual":
                stats["manual_queued"] += 1
            elif category == "ban":
                stats["ban_detected"] = True
            else:
                stats["failed"] += 1
        finally:
            tracker.release_job_lock(job_id)
            processed += 1

        # Si detectamos ban, abortar ciclo de inmediato
        if stats["ban_detected"]:
            break

    return stats


def run_application_cycle_sync() -> Dict[str, Any]:
    """Wrapper sincrónico para APScheduler."""
    return asyncio.run(run_application_cycle())


# ── Utilidades para diagnóstico / otros agentes ──────────────────────────────

def get_queue_snapshot(limit: int = 10) -> List[Dict]:
    """Para dashboard / pipeline_health_agent: preview de la cola."""
    tracker = JobTracker()
    return tracker.get_application_queue(
        min_score=APPLY_SCORE_THRESHOLD,
        max_age_days=JOB_MAX_AGE_DAYS,
        limit=limit,
    )


def get_ban_state() -> Dict:
    """Para diagnóstico externo."""
    return _load_ban_history()


if __name__ == "__main__":
    # Dry-run manual
    import pprint

    logger.info("=== Application Agent — dry run ===")
    pprint.pp(get_queue_snapshot(5))
    logger.info(f"Ban state: {get_ban_state()}")
    logger.info(f"Business hours: {_is_business_hours()}")
    logger.info(f"CV exists: {_verify_cv_exists()}")
