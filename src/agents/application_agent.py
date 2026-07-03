"""
Application Agent — único ejecutor de aplicaciones a jobs.

Lee la cola BD (status='found', score>=75, <14 días), prioriza por score+fecha
y aplica vía linkedin_easy_apply_api (Voyager HTTP API — sin browser, sin Playwright).

Regla global: el fin último de toda aplicación es entregar el CV más actualizado
(data/cv_alejandro_en.pdf) al reclutador. Si no se puede garantizar eso
(archivo no existe, CV cambiado), el ciclo se aborta.

Rate limits, horario humano, gap entre apps, presupuesto global de la cuenta y
ban/recovery viven en `src/tools/linkedin_governor.py` — el choke point único de
actividad de la cuenta. Este agente NO duplica esa política: pregunta `gov.can_act(APPLY)` como skip
temprano del ciclo. El registro real en el ledger (`record_action(APPLY)`) lo
hace `linkedin_easy_apply_api` en el submit HTTP, que es el choke point único
por el que pasan también los scripts sueltos.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

from config import settings
from src.agents import master_agent
from src.db.tracker import JobTracker
from src.tools import linkedin_easy_apply_api, linkedin_governor as gov, whatsapp_tool

# ── Configuración ────────────────────────────────────────────────────────────

CV_PATH = "data/cv_alejandro_en.pdf"  # Fuente de verdad del CV
RESUME_JSON = "data/resume.json"

APPLY_SCORE_THRESHOLD = 75
JOB_MAX_AGE_DAYS = 14
MAX_JOBS_PER_CYCLE = 1
MAX_ATTEMPTS = 3

# Rate-limits, horario, ban y recovery viven en linkedin_governor (choke point
# único de la cuenta). Este agente solo consume esa política; no la duplica.
BAN_SIGNALS = gov.BAN_SIGNALS

# Estados que NO son ban pero requieren escalar a manual
MANUAL_SIGNALS = {
    "need_user",
    "apply_needs_manual",
    "blocked_cv",
    "generic_url",
    "captcha",
    "blocked_captcha",
}


# ── Helpers ──────────────────────────────────────────────────────────────────

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


def _record_ban(reason: str, status: str):
    """Delega en el governor (política de ban a nivel cuenta)."""
    gov.record_ban(reason=reason, status=status, notify=whatsapp_tool.send_message)


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
    Aplica a un job individual usando linkedin_easy_apply_api (Voyager HTTP API,
    sin browser). Más estable que Playwright porque no depende de selectors CSS
    ni de una pantalla/display.

    Retorna dict con resultado enriquecido.
    """
    job_url = job.get("url") or job.get("applied_url")
    cover_letter = ""
    try:
        cover_letter = master_agent.generate_cover_letter(job, resume) or ""
    except Exception as e:
        logger.warning(f"[app_agent] Cover letter failed, aplicando sin ella: {e}")

    # Delay humano antes de aplicar (jitter no-lineal, definido en el governor).
    await gov.human_delay_async(gov.APPLY)

    try:
        # Voyager API: no abre browser, usa cookies HTTP directamente
        result = await asyncio.to_thread(
            linkedin_easy_apply_api.submit_easy_apply,
            job_url=job_url,
            resume=resume,
            cover_letter=cover_letter,
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
        # El ledger (record_action APPLY) lo escribe linkedin_easy_apply_api en el
        # submit real — aquí solo avanzamos el estado de recovery.
        gov.record_successful_apply()
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
        # Detectar si el job no es Easy Apply → enrutar a cola externa
        is_not_easy_apply = (
            status in ("api_error_400", "external_apply", "not_easy_apply")
            or "no es Easy Apply" in message
            or "not easy apply" in message.lower()
            or "bad gateway" in message.lower()
        )
        if is_not_easy_apply:
            # Mover a external_apply_queue y marcar job como deferred
            tracker._enqueue_externals([job])
            logger.info(
                f"[app_agent] 📦 Externo detectado → external_apply_queue: "
                f"{job.get('title')} @ {job.get('company')}"
            )
            return

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

    # 2. Governor: ban, horario humano, cap diario/horario, gap mínimo y
    #    presupuesto global de la cuenta — todo decidido en un solo lugar.
    ok, reason = gov.can_act(gov.APPLY)
    if not ok:
        stats["skipped_reason"] = reason
        logger.debug(f"[app_agent] governor bloqueó apply: {reason}")
        return stats

    tracker = JobTracker()
    today_count = tracker.count_applications_today()
    cap = gov.apply_daily_cap()

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
        easy_apply_only=True,  # solo Easy Apply; externos van a external_apply_queue
    )
    if not queue:
        stats["skipped_reason"] = "empty_queue_easy_apply"
        logger.debug("[app_agent] Cola Easy Apply vacía — externos en external_apply_queue")
        return stats

    logger.info(f"[app_agent] Cola Easy Apply: {len(queue)} jobs | hoy: {today_count}/{cap}")

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
    return gov.get_ban_state()


if __name__ == "__main__":
    # Dry-run manual
    import pprint

    logger.info("=== Application Agent — dry run ===")
    pprint.pp(get_queue_snapshot(5))
    logger.info(f"Ban state: {get_ban_state()}")
    logger.info(f"can_act(APPLY): {gov.can_act(gov.APPLY)}")
    logger.info(f"CV exists: {_verify_cv_exists()}")
