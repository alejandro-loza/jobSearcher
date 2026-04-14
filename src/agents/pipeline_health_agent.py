"""
Pipeline Health Agent — observador del pipeline completo.

Corre cada 4 horas. Para cada job activo (< 30 días):
  - Detecta si está en "proceso activo" (Gmail / LinkedIn / Calendar)
  - Decide: re-encolar aplicación, marcar ghosted, o solo monitorear
  - Detecta eventos raros (rechazos, ofertas, silencios largos)

Principios:
  1. NUNCA habla con reclutadores. No envía emails, no manda LinkedIn mensajes,
     no agenda entrevistas. Solo lee estado y actúa sobre el pipeline interno.
  2. El ÚNICO canal de salida es WhatsApp → notifica a Alejandro cuando detecta
     algo que merece su atención.
  3. Las comunicaciones con reclutadores siguen pasando por:
        response_decision_agent → recruiter_agent → antispam_agent → gmail/linkedin
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

from src.agents import master_agent
from src.db.tracker import JobTracker
from src.tools import whatsapp_tool

# ── Configuración ────────────────────────────────────────────────────────────

REVIEW_MAX_AGE_DAYS = 30          # Solo revisar jobs < 30 días
APPLY_SCORE_THRESHOLD = 75
REAPPLY_MAX_AGE_DAYS = 14         # Solo re-encolar jobs < 14 días
FOLLOWUP_MIN_DAYS = 7             # Avisar follow-up a partir de 7 días
GHOST_THRESHOLD_DAYS = 21         # Marcar ghosted tras 21 días
MANUAL_REMINDER_DAYS = 3          # Recordar jobs pendientes manuales tras 3d

STATE_FILE = "data/pipeline_health_state.json"

# Estados de proceso activo (de alta a baja intensidad)
ACTIVE_STATES = {
    "interview_scheduled",
    "offer_received",
    "linkedin_active",
    "email_response",
}


# ── Estado persistido ────────────────────────────────────────────────────────

def _load_state() -> Dict:
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"last_run": None, "notified_jobs": {}}


def _save_state(state: Dict):
    Path(STATE_FILE).parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2, default=str)


def _was_notified(state: Dict, job_id: str, event_type: str) -> bool:
    """Evita notificar múltiples veces el mismo evento."""
    key = f"{job_id}:{event_type}"
    return key in state.get("notified_jobs", {})


def _mark_notified(state: Dict, job_id: str, event_type: str):
    key = f"{job_id}:{event_type}"
    state.setdefault("notified_jobs", {})[key] = datetime.now().isoformat()


# ── Detección de proceso activo ──────────────────────────────────────────────

def is_active_process(
    tracker: JobTracker, job_id: str, company: str
) -> Tuple[bool, Optional[str], Dict]:
    """
    Detecta si hay proceso activo con la empresa.

    Retorna (está_activo, tipo_estado, evidencia).
    Prioridad: Calendar > Emails > LinkedIn.
    """
    # 1. Entrevista en Calendar → nivel máximo
    interviews = tracker.get_interviews_for_job(job_id)
    active_interviews = [
        i for i in interviews if i.get("status") in ("scheduled", "completed")
    ]
    if active_interviews:
        return True, "interview_scheduled", {"interviews": active_interviews}

    # 2. Email con sentiment relevante
    emails = tracker.get_emails_for_job(job_id)
    if not emails and company:
        emails = tracker.get_emails_by_company(company, days=30)
    relevant_emails = [
        e for e in emails
        if (e.get("sentiment") or "").lower() in {"positive", "interview", "neutral_response", "response"}
    ]
    if relevant_emails:
        return True, "email_response", {"emails": relevant_emails[:3]}

    # 3. Conversación LinkedIn activa
    if company:
        convs = tracker.get_conversations_by_company(company)
        active_convs = [
            c for c in convs
            if (c.get("state") or "").lower() in {"responded", "awaiting_reply", "escalated"}
        ]
        if active_convs:
            return True, "linkedin_active", {"conversations": active_convs[:3]}

    return False, None, {}


# ── Análisis de estado ───────────────────────────────────────────────────────

def _analyze_active_process(
    tracker: JobTracker, job: Dict, evidence: Dict, state_type: str
) -> Optional[str]:
    """
    Si hay proceso activo, analiza si hay algo raro que Alejandro deba saber.
    Retorna mensaje de WA o None.

    NO toma acciones hacia afuera — solo genera alertas internas.
    """
    job_id = job["id"]
    company = job.get("company", "")
    title = job.get("title", "")

    # Rechazo detectado en emails recientes
    for email in evidence.get("emails", []):
        sentiment = (email.get("sentiment") or "").lower()
        subject = email.get("subject", "")
        if sentiment == "negative" or "reject" in subject.lower() or "unfortunately" in subject.lower():
            return (
                f"❌ Posible rechazo — {company}\n"
                f"Job: {title}\n"
                f"Asunto: {subject}\n"
                f"Revisa Gmail para confirmar."
            )

        # Oferta detectada → escalación crítica
        if sentiment == "interview" and "offer" in (email.get("content") or "").lower()[:500]:
            return (
                f"🎯 Posible OFERTA — {company}\n"
                f"Job: {title}\n"
                f"Asunto: {subject}\n"
                f"Revisa Gmail urgente."
            )

    # Entrevista agendada pero sin confirmación reciente
    if state_type == "interview_scheduled":
        interviews = evidence.get("interviews", [])
        if interviews and not _is_interview_confirmed(interviews[0]):
            return (
                f"📅 Entrevista sin confirmación clara — {company}\n"
                f"Job: {title}\n"
                f"Verifica el email / Calendar."
            )

    return None


def _is_interview_confirmed(interview: Dict) -> bool:
    """Heurística: si tiene calendar_event_id, asumimos que está confirmada."""
    return bool(interview.get("calendar_event_id"))


# ── Acciones sobre el pipeline interno ───────────────────────────────────────

def _requeue_for_application(tracker: JobTracker, job: Dict) -> bool:
    """
    Re-encola un job para que application_agent lo procese.
    Solo cambia estados internos — no comunica con nada exterior.
    """
    job_id = job["id"]
    # Resetear status='found' si estaba en un estado intermedio no terminal
    current_status = (job.get("status") or "").lower()
    if current_status in ("apply_failed", "apply_captcha", "found"):
        tracker.update_job_status(job_id, "found")
        logger.info(f"[pipeline] Re-encolado: {job.get('title')} @ {job.get('company')}")
        return True
    return False


# ── Core ─────────────────────────────────────────────────────────────────────

def run_pipeline_review() -> Dict[str, Any]:
    """
    Ciclo principal — ejecutado cada 4h.
    Retorna stats y lista de alertas generadas.
    """
    tracker = JobTracker()
    state = _load_state()

    jobs = tracker.get_all_jobs(limit=500)
    now = datetime.now()

    # Filtrar a jobs razonables (< 30 días)
    def _within_window(job):
        try:
            found = datetime.fromisoformat(job["found_at"].replace("Z", ""))
            return (now - found).days <= REVIEW_MAX_AGE_DAYS
        except Exception:
            return False

    jobs = [j for j in jobs if _within_window(j)]

    stats = {
        "reviewed": len(jobs),
        "active_processes": 0,
        "requeued_for_apply": 0,
        "ghosted": 0,
        "alerts": [],
    }

    for job in jobs:
        job_id = job["id"]
        company = job.get("company", "")
        title = job.get("title", "")
        status = (job.get("status") or "").lower()
        score = int(job.get("match_score") or 0)

        # skip si está en procesamiento técnico
        if job.get("being_processed"):
            continue

        active, state_type, evidence = is_active_process(tracker, job_id, company)

        # ── PROCESO ACTIVO → solo monitorear, alertar si hay algo raro ──
        if active:
            stats["active_processes"] += 1
            alert = _analyze_active_process(tracker, job, evidence, state_type)
            if alert and not _was_notified(state, job_id, state_type):
                stats["alerts"].append(alert)
                _mark_notified(state, job_id, state_type)
            continue

        # ── SIN PROCESO ACTIVO → evaluar acción ──

        # 1. Job encontrado pero nunca aplicado → re-encolar
        if status == "found" and score >= APPLY_SCORE_THRESHOLD:
            try:
                found = datetime.fromisoformat(job["found_at"].replace("Z", ""))
                age_days = (now - found).days
            except Exception:
                age_days = 999
            if age_days <= REAPPLY_MAX_AGE_DAYS:
                # Ya está en 'found', no necesita re-encolar, application_agent lo procesará
                # Solo loguear que está en cola
                continue

        # 2. Aplicado sin respuesta → follow-up o ghost
        if status == "applied":
            days = tracker.days_since_applied(job_id)
            if days is None:
                continue

            if days >= GHOST_THRESHOLD_DAYS:
                if not _was_notified(state, job_id, "ghosted"):
                    tracker.mark_job_ghosted(
                        job_id, notes=f"no response in {days}d"
                    )
                    stats["ghosted"] += 1
                    stats["alerts"].append(
                        f"👻 Cerrando — {company}: {title} ({days}d sin respuesta)"
                    )
                    _mark_notified(state, job_id, "ghosted")
            elif days >= FOLLOWUP_MIN_DAYS:
                if not _was_notified(state, job_id, "followup_needed"):
                    stats["alerts"].append(
                        f"⏱ Sin respuesta {days}d — {company}: {title}\n"
                        f"¿Quieres hacer follow-up?"
                    )
                    _mark_notified(state, job_id, "followup_needed")

        # 3. Aplicación manual pendiente por más de N días
        if status == "apply_needs_manual":
            try:
                attempted = job.get("last_attempt_at") or job.get("found_at")
                dt = datetime.fromisoformat(attempted.replace("Z", ""))
                age = (now - dt).days
            except Exception:
                age = 0
            if age >= MANUAL_REMINDER_DAYS and not _was_notified(state, job_id, "manual_reminder"):
                stats["alerts"].append(
                    f"🔧 Pendiente manual — {company}: {title} ({age}d)"
                )
                _mark_notified(state, job_id, "manual_reminder")

    # ── Notificar a Alejandro si hay alertas ──
    if stats["alerts"]:
        summary = "📊 Pipeline Health Review\n\n" + "\n\n".join(stats["alerts"][:10])
        if len(stats["alerts"]) > 10:
            summary += f"\n\n...y {len(stats['alerts']) - 10} alertas más"
        summary += (
            f"\n\n—\nRevisados: {stats['reviewed']} | "
            f"Activos: {stats['active_processes']} | "
            f"Ghosted: {stats['ghosted']}"
        )
        try:
            whatsapp_tool.send_message(summary)
        except Exception as e:
            logger.error(f"[pipeline] No se pudo notificar por WA: {e}")

    state["last_run"] = now.isoformat()
    _save_state(state)

    logger.info(
        f"[pipeline] review — revisados={stats['reviewed']} "
        f"activos={stats['active_processes']} ghosted={stats['ghosted']} "
        f"alertas={len(stats['alerts'])}"
    )
    return stats


# ── Utilidades ───────────────────────────────────────────────────────────────

def get_pipeline_snapshot() -> Dict[str, Any]:
    """Resumen rápido del pipeline actual (para dashboard)."""
    tracker = JobTracker()
    with tracker._get_conn() as conn:
        counts = {}
        for row in conn.execute(
            "SELECT status, COUNT(*) as n FROM jobs GROUP BY status"
        ).fetchall():
            counts[row["status"] or "unknown"] = row["n"]
    return {
        "by_status": counts,
        "applications_today": tracker.count_applications_today(),
        "last_run": _load_state().get("last_run"),
    }


if __name__ == "__main__":
    import pprint
    logger.info("=== Pipeline Health — dry run ===")
    pprint.pp(get_pipeline_snapshot())
    result = run_pipeline_review()
    logger.info(f"Resultado: {result}")
