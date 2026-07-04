"""
External ATS Agent — aplica a jobs en Greenhouse/Lever/Ashby vía browser + Kimi visión.

Flujo:
  1. Lee cola: jobs con source=greenhouse-api/lever-api/ashby-api + external_apply_queue
  2. Filtra por ATS soportado (greenhouse, lever, ashby) — omite workday/icims/taleo
  3. Genera cover letter via master_agent (Kimi)
  4. Aplica con browser_tool.apply_to_job_url() (Playwright + Kimi visión)
  5. Registra resultado en tracker

Sin riesgo de ban de LinkedIn — todo el flujo es externo a LinkedIn.
Rate limit conservador: 10 apps/día, delays 30-90s entre applies.
"""

from __future__ import annotations

import asyncio
import json
import random
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

from src.agents import master_agent
from src.db.tracker import JobTracker
from src.tools import browser_tool, whatsapp_tool

# ── Configuración ─────────────────────────────────────────────────────────────

CV_PATH = "data/cv_alejandro_en.pdf"
RESUME_JSON = "data/resume.json"

# Kill switch: si este archivo existe, el agente NO aplica (ni scheduler ni
# /trigger/external-ats). Crear/borrar el archivo no requiere reiniciar nada:
#   touch data/pause_external_apply.flag   # pausar
#   rm data/pause_external_apply.flag      # reanudar
PAUSE_FLAG = Path("data/pause_external_apply.flag")

APPLY_SCORE_THRESHOLD = 75
JOB_MAX_AGE_DAYS = 21          # ATS externos duran más que LinkedIn
DAILY_CAP = 10                 # Sin riesgo LinkedIn → podemos ir más rápido
MAX_JOBS_PER_CYCLE = 3         # Máx por ejecución (el agente corre N veces/día)
DELAY_BETWEEN_APPS = (30, 90)  # segundos

# ATS que el browser_tool puede manejar sin CAPTCHA habitual
SUPPORTED_ATS = {"greenhouse", "lever", "ashby"}

# ATS que típicamente tienen CAPTCHA o flujos muy complejos → escalamos a manual
SKIP_ATS = {"workday", "taleo", "icims", "smartrecruiters"}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _load_resume() -> Optional[Dict]:
    try:
        return json.loads(Path(RESUME_JSON).read_text())
    except Exception as e:
        logger.error(f"[ext_ats] resume.json no encontrado: {e}")
        return None


def _verify_cv() -> bool:
    cv = Path(CV_PATH)
    if not cv.exists():
        logger.error(f"[ext_ats] CV no encontrado en {CV_PATH}")
        return False
    return True


def _detect_ats(url: str) -> str:
    """Detecta ATS por URL; complementa detect_ats_type() de browser_tool."""
    url_l = url.lower()
    # Stripe usa su propia página pero con Greenhouse backend (gh_jid param)
    if "stripe.com/jobs" in url_l and "gh_jid" in url_l:
        return "greenhouse"
    return browser_tool.detect_ats_type(url)


def _count_today_external(tracker: JobTracker) -> int:
    """Cuenta aplicaciones externas de hoy (method='external_ats')."""
    with tracker._get_conn() as conn:
        row = conn.execute(
            """SELECT COUNT(*) FROM applications
               WHERE method = 'external_ats'
                 AND date(last_activity) = date('now')""",
        ).fetchone()
        return (row[0] or 0) if row else 0


# ── Obtener cola ──────────────────────────────────────────────────────────────

def _get_queue(tracker: JobTracker, min_score: int, max_age_days: int, limit: int) -> List[Dict]:
    """
    Une dos fuentes:
      A) jobs table: source=*-api, status=found, score>=min_score
      B) external_apply_queue: status=pending, score>=min_score
    Dedup por job_id. Filtra por ATS soportado.
    """
    seen: set = set()
    queue: List[Dict] = []

    with tracker._get_conn() as conn:
        # Fuente A: portal_scanner jobs aún en status=found
        rows_a = conn.execute(
            """SELECT id, title, company, location, url, match_score, description
               FROM jobs
               WHERE source IN ('greenhouse-api','lever-api','ashby-api')
                 AND status = 'found'
                 AND COALESCE(match_score,0) >= ?
                 AND url IS NOT NULL AND url != ''
                 AND datetime(found_at) >= datetime('now', ?)
               ORDER BY match_score DESC, found_at DESC
               LIMIT ?""",
            (min_score, f"-{max_age_days} days", limit * 2),
        ).fetchall()

        for r in rows_a:
            d = dict(r)
            jid = d["id"]
            if jid in seen:
                continue
            ats = _detect_ats(d["url"])
            if ats not in SUPPORTED_ATS:
                if ats in SKIP_ATS:
                    logger.debug(f"[ext_ats] Skip ATS {ats}: {d['title']} @ {d['company']}")
                continue
            d["ats_type"] = ats
            d["_source"] = "jobs_table"
            seen.add(jid)
            queue.append(d)

        # Fuente B: external_apply_queue (jobs enrutados por application_agent)
        rows_b = conn.execute(
            """SELECT job_id as id, title, company, location, url, match_score, ats_type
               FROM external_apply_queue
               WHERE status = 'pending'
                 AND COALESCE(match_score,0) >= ?
               ORDER BY priority DESC, match_score DESC
               LIMIT ?""",
            (min_score, limit * 2),
        ).fetchall()

        for r in rows_b:
            d = dict(r)
            jid = d["id"]
            if jid in seen:
                continue
            ats = d.get("ats_type") or _detect_ats(d.get("url", ""))
            if ats not in SUPPORTED_ATS:
                continue
            d["ats_type"] = ats
            d["_source"] = "external_queue"
            # Cargar descripción desde jobs table para cover letter
            row_desc = conn.execute(
                "SELECT description FROM jobs WHERE id=?", (jid,)
            ).fetchone()
            d["description"] = row_desc[0] if row_desc else ""
            seen.add(jid)
            queue.append(d)

    return queue[:limit]


# ── Apply individual ──────────────────────────────────────────────────────────

# Envío automático de aplicaciones API-driven. Por defecto FALSE (assist): llena
# todo incl. ensayos y se detiene antes de enviar para revisión humana — las
# respuestas de ensayo deciden si te contratan. Ponlo True para submit autónomo.
AUTO_SUBMIT_API = False


async def _apply_via_api(job: Dict, resume: Dict) -> Optional[Dict[str, Any]]:
    """Apply DIRIGIDO POR API (Greenhouse/Ashby): lee el form por API, genera
    respuestas de una vez y llena por selector. Retorna None si el ATS no expone
    el form por API (→ el caller cae al flujo de visión)."""
    from src.tools import ats_forms, ats_filler

    url = job.get("url", "")
    form = ats_forms.fetch_form(url, company=job.get("company", ""))
    if not form or not form.fields:
        return None

    logger.info(f"[ext_ats] API-driven ({form.ats}): {len(form.fields)} campos, "
                f"{len(form.required_fields())} obligatorios")
    answers = await asyncio.to_thread(master_agent.answer_application, form, resume, job)

    if form.ats != "greenhouse":
        # Filler de Ashby aún no implementado → dejamos que el caller use visión.
        logger.debug("[ext_ats] form API no-Greenhouse — sin filler dedicado aún")
        return None

    res = await ats_filler.fill_greenhouse_application(
        url, answers, cv_path=CV_PATH, submit=AUTO_SUBMIT_API, headless=True,
    )
    # Normalizar al formato de resultado del agente.
    if res.get("submitted"):
        status = "applied"
        success = True
    elif res.get("status") == "assist_ready":
        status = "need_user"   # llenado y listo para que Alejandro revise/envíe
        success = False
    else:
        status = "error"
        success = False
    n_fill = len(res.get("filled", []))
    n_fail = len(res.get("failed", []))
    return {
        "success": success,
        "status": status,
        "message": f"API-driven {res.get('status')} — llenados {n_fill}, fallidos {n_fail}",
        "method": "api_driven",
        "screenshot_path": res.get("screenshot", ""),
    }


async def _apply_one(job: Dict, resume: Dict) -> Dict[str, Any]:
    """Aplica: primero intenta API-driven (Greenhouse); si no, visión. Retorna resultado."""
    title = job.get("title", "")
    company = job.get("company", "")
    url = job.get("url", "")
    ats = job.get("ats_type", "unknown")

    logger.info(f"[ext_ats] Aplicando: {title} @ {company} | ATS={ats} | URL={url[:60]}")

    # Ruta preferida: API-driven (determinista, 1 llamada LLM, maneja ensayos+dropdowns).
    try:
        api_res = await _apply_via_api(job, resume)
        if api_res is not None:
            api_res["cover_letter"] = ""
            api_res["job_id"] = job["id"]
            return api_res
    except Exception as e:
        logger.warning(f"[ext_ats] API-driven falló ({e}); cae a visión")

    # Fallback: flujo de visión (para ATS sin form por API).
    cover_letter = ""
    try:
        cover_letter = master_agent.generate_cover_letter(job, resume) or ""
        logger.debug(f"[ext_ats] Cover letter generada ({len(cover_letter)} chars)")
    except Exception as e:
        logger.warning(f"[ext_ats] Cover letter falló, aplicando sin ella: {e}")

    # Delay humano antes de aplicar
    delay = random.uniform(*DELAY_BETWEEN_APPS)
    logger.debug(f"[ext_ats] Delay pre-apply: {delay:.0f}s")
    await asyncio.sleep(delay)

    # Aplicar via browser_tool
    try:
        result = await browser_tool.apply_to_job_url(
            job_url=url,
            resume=resume,
            job_title=title,
            company=company,
            cover_letter=cover_letter,
            headless=True,
        )
    except Exception as e:
        logger.exception(f"[ext_ats] Excepción en browser_tool: {e}")
        result = {"success": False, "status": "exception", "message": str(e)[:300]}

    result["cover_letter"] = cover_letter
    result["job_id"] = job["id"]
    return result


# ── Persistencia ──────────────────────────────────────────────────────────────

def _persist(tracker: JobTracker, job: Dict, result: Dict):
    """Actualiza jobs + applications + external_apply_queue según resultado."""
    job_id = job["id"]
    success = result.get("success", False)
    status = result.get("status", "error")
    message = result.get("message", "")[:300]
    cover_letter = result.get("cover_letter", "")
    source = job.get("_source", "jobs_table")

    is_api_assist = result.get("method") == "api_driven" and status == "need_user"

    if success or status in ("applied", "external_submitted", "success"):
        app_status = "applied"
        logger.success(f"[ext_ats] ✅ {job['title']} @ {job['company']}")
    elif is_api_assist:
        # Formulario ya LLENO (incl. ensayos) esperando revisión + envío de Alejandro.
        app_status = "apply_ready_review"
        logger.success(f"[ext_ats] 📝 Listo para revisar/enviar: {job['title']} @ {job['company']}")
        try:
            whatsapp_tool.send_message(
                f"📝 Aplicación LISTA para tu revisión (todo lleno, incl. ensayos):\n"
                f"*{job['title']}* @ {job['company']}\n"
                f"Revisa el formulario y dale Enviar: {job['url']}\n"
                f"{message}"
            )
        except Exception:
            pass
    elif status in ("captcha", "blocked_captcha", "need_user"):
        app_status = "apply_needs_manual"
        logger.warning(f"[ext_ats] 🔧 CAPTCHA/manual: {job['title']} — {message[:80]}")
        try:
            whatsapp_tool.send_message(
                f"🤖 External ATS necesita intervención manual:\n"
                f"*{job['title']}* @ {job['company']}\n"
                f"URL: {job['url']}\n"
                f"Motivo: {status}"
            )
        except Exception:
            pass
    elif status == "generic_url":
        app_status = "apply_needs_manual"
        logger.warning(f"[ext_ats] URL genérica — manual: {job['url']}")
    else:
        app_status = "apply_failed"
        logger.warning(f"[ext_ats] ❌ Falló: {job['title']} — {status}: {message[:80]}")

    tracker.save_application(
        job_id=job_id,
        method="external_ats",
        cover_letter=cover_letter,
        status=app_status,
        failure_reason="" if app_status == "applied" else f"{status}:{message[:100]}",
        method_detail=f"ats={job.get('ats_type','?')}",
    )

    # Marcar en external_apply_queue si venía de ahí
    if source == "external_queue":
        ext_status = "completed" if app_status == "applied" else (
            "manual" if app_status == "apply_needs_manual" else "failed"
        )
        tracker.mark_external_done(job_id, handled_by="external_ats_agent", status=ext_status)


# ── Entry point ───────────────────────────────────────────────────────────────

async def run_external_apply_cycle(
    min_score: int = APPLY_SCORE_THRESHOLD,
    max_age_days: int = JOB_MAX_AGE_DAYS,
    max_jobs: int = MAX_JOBS_PER_CYCLE,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Ciclo completo de aplicaciones externas.
    dry_run=True: muestra la cola sin aplicar.
    """
    stats = {
        "attempted": 0,
        "applied": 0,
        "failed": 0,
        "manual_queued": 0,
        "skipped_reason": None,
        "jobs": [],
    }

    # Kill switch por archivo — el dry_run sí se permite (no aplica nada).
    if PAUSE_FLAG.exists() and not dry_run:
        stats["skipped_reason"] = "paused_by_flag"
        logger.info(f"[ext_ats] pausado por {PAUSE_FLAG} — no se aplica")
        return stats

    if not _verify_cv():
        stats["skipped_reason"] = "cv_missing"
        return stats

    resume = _load_resume()
    if not resume:
        stats["skipped_reason"] = "resume_load_failed"
        return stats

    tracker = JobTracker()

    # Daily cap
    today_count = _count_today_external(tracker)
    if today_count >= DAILY_CAP:
        stats["skipped_reason"] = f"daily_cap:{today_count}/{DAILY_CAP}"
        logger.info(f"[ext_ats] Cap diario alcanzado: {today_count}/{DAILY_CAP}")
        return stats

    available = DAILY_CAP - today_count
    limit = min(max_jobs, available)

    queue = _get_queue(tracker, min_score=min_score, max_age_days=max_age_days, limit=limit)
    if not queue:
        stats["skipped_reason"] = "empty_queue"
        logger.info(f"[ext_ats] Cola vacía (score>={min_score}, age<={max_age_days}d)")
        return stats

    logger.info(f"[ext_ats] Cola: {len(queue)} jobs | hoy externas: {today_count}/{DAILY_CAP}")

    if dry_run:
        stats["skipped_reason"] = "dry_run"
        for j in queue:
            logger.info(f"  [{j.get('match_score',0)}] {j['title']} @ {j['company']} | {j['ats_type']} | {j['url'][:60]}")
            stats["jobs"].append({"title": j["title"], "company": j["company"],
                                  "ats": j["ats_type"], "score": j.get("match_score", 0),
                                  "url": j["url"]})
        return stats

    for job in queue:
        if not tracker.lock_job_for_processing(job["id"]):
            logger.debug(f"[ext_ats] Job locked por otro proceso: {job['id']}")
            continue

        stats["attempted"] += 1
        try:
            result = await _apply_one(job, resume)
            _persist(tracker, job, result)

            app_status = result.get("status", "")
            if result.get("success") or app_status in ("applied", "external_submitted"):
                stats["applied"] += 1
            elif app_status in ("captcha", "need_user", "generic_url", "blocked_captcha"):
                stats["manual_queued"] += 1
            else:
                stats["failed"] += 1

            stats["jobs"].append({
                "title": job["title"],
                "company": job["company"],
                "ats": job["ats_type"],
                "score": job.get("match_score", 0),
                "url": job["url"],
                "result": app_status,
            })
        except Exception as e:
            logger.exception(f"[ext_ats] Error inesperado: {job['title']}: {e}")
            stats["failed"] += 1
        finally:
            tracker.release_job_lock(job["id"])

    logger.info(
        f"[ext_ats] Ciclo completo — "
        f"applied={stats['applied']} failed={stats['failed']} manual={stats['manual_queued']}"
    )
    return stats


def run_external_apply_cycle_sync(
    min_score: int = APPLY_SCORE_THRESHOLD,
    max_age_days: int = JOB_MAX_AGE_DAYS,
    max_jobs: int = MAX_JOBS_PER_CYCLE,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Wrapper síncrono para APScheduler / CLI."""
    return asyncio.run(run_external_apply_cycle(
        min_score=min_score,
        max_age_days=max_age_days,
        max_jobs=max_jobs,
        dry_run=dry_run,
    ))


# ── Preview de cola (para dashboard / diagnóstico) ────────────────────────────

def get_queue_preview(min_score: int = APPLY_SCORE_THRESHOLD) -> List[Dict]:
    tracker = JobTracker()
    return _get_queue(tracker, min_score=min_score, max_age_days=JOB_MAX_AGE_DAYS, limit=20)


if __name__ == "__main__":
    import pprint
    logger.info("=== External ATS Agent — dry run ===")
    result = run_external_apply_cycle_sync(dry_run=True)
    pprint.pp(result)
