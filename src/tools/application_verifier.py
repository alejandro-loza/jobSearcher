"""
Verifica si las aplicaciones realmente se enviaron buscando emails de confirmación en Gmail.
Actualiza verified=True en la DB cuando encuentra confirmación.
"""
import re
from typing import List, Dict, Tuple
from loguru import logger
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
import os, json

from config import settings
from src.db.tracker import JobTracker

# Patrones de asunto que indican confirmación de aplicación
CONFIRMATION_SUBJECTS = [
    r"application received",
    r"thank you for applying",
    r"thanks for applying",
    r"we received your application",
    r"your application",
    r"application submitted",
    r"application confirmed",
    r"aplicación recibida",
    r"gracias por aplicar",
    r"hemos recibido tu",
    r"solicitud recibida",
    r"next steps",
    r"complete next steps",
    r"action required",
]

REJECTION_SUBJECTS = [
    r"unfortunately",
    r"we have decided",
    r"not moving forward",
    r"other candidates",
    r"position has been filled",
    r"lamentablemente",
    r"no continuaremos",
]


def _get_gmail():
    creds = Credentials.from_authorized_user_file(settings.gmail_token_file)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return build("gmail", "v1", credentials=creds)


def verify_applications_via_gmail(days_back: int = 60) -> Dict[str, int]:
    """
    Busca en Gmail emails de confirmación y rechazos de aplicaciones.
    Actualiza la DB con los resultados.

    Returns:
        Dict con conteos: confirmed, rejected, total_checked
    """
    tracker = JobTracker()
    apps = tracker.get_full_pipeline(limit=500)

    if not apps:
        return {"confirmed": 0, "rejected": 0, "total_checked": 0}

    # Obtener todos los emails de los últimos N días
    try:
        service = _get_gmail()
        query = f"newer_than:{days_back}d"
        results = service.users().messages().list(
            userId="me", q=query, maxResults=500
        ).execute()
        messages = results.get("messages", [])
    except Exception as e:
        logger.error(f"Error obteniendo emails de Gmail: {e}")
        return {"confirmed": 0, "rejected": 0, "total_checked": 0}

    # Obtener subjects y senders de los emails
    email_data = []
    for msg in messages[:200]:  # máx 200 para no agotar quota
        try:
            m = service.users().messages().get(
                userId="me", id=msg["id"], format="metadata",
                metadataHeaders=["Subject", "From"]
            ).execute()
            headers = {h["name"]: h["value"] for h in m.get("payload", {}).get("headers", [])}
            email_data.append({
                "id": msg["id"],
                "subject": headers.get("Subject", "").lower(),
                "from": headers.get("From", "").lower(),
            })
        except Exception:
            continue

    confirmed = 0
    rejected = 0

    for app in apps:
        if app.get("verified"):
            continue  # ya verificada

        company = (app.get("company") or "").lower()
        title = (app.get("title") or "").lower()

        # Buscar email de esta empresa
        for email in email_data:
            subject = email["subject"]
            sender = email["from"]

            # Ver si el email es de esta empresa
            company_words = [w for w in company.split() if len(w) > 3]
            company_match = any(w in sender or w in subject for w in company_words)

            if not company_match:
                continue

            # Verificar si es confirmación
            is_confirmation = any(re.search(p, subject) for p in CONFIRMATION_SUBJECTS)
            is_rejection = any(re.search(p, subject) for p in REJECTION_SUBJECTS)

            if is_confirmation:
                tracker.mark_verified(app["app_id"] if "app_id" in app else app.get("job_id", ""), True)
                # Usar job_id para advance_pipeline
                job_id = _get_job_id_from_app(tracker, app)
                if job_id:
                    tracker.advance_pipeline(job_id, "response", f"Email confirmación: {email['subject'][:80]}")
                confirmed += 1
                logger.success(f"✅ Verificada: {app['company']} - {app['title'][:40]}")
                break

            if is_rejection:
                job_id = _get_job_id_from_app(tracker, app)
                if job_id:
                    tracker.advance_pipeline(job_id, "rejected", f"Email rechazo: {email['subject'][:80]}")
                rejected += 1
                logger.info(f"❌ Rechazada: {app['company']} - {app['title'][:40]}")
                break

    result = {"confirmed": confirmed, "rejected": rejected, "total_checked": len(apps)}
    logger.info(f"Verificación: {confirmed} confirmadas, {rejected} rechazadas de {len(apps)} apps")
    return result


def _get_job_id_from_app(tracker: JobTracker, app: dict) -> str:
    """Obtiene el job_id de una aplicación."""
    with tracker._get_conn() as conn:
        row = conn.execute(
            "SELECT job_id FROM applications WHERE id=?", (app.get("app_id"),)
        ).fetchone()
        return row["job_id"] if row else None


def verify_capital_one(tracker: JobTracker = None):
    """
    Capital One tiene 3 emails 'Action Required' - verificar y avanzar pipeline.
    """
    if not tracker:
        tracker = JobTracker()
    try:
        service = _get_gmail()
        results = service.users().messages().list(
            userId="me",
            q="from:capitalone subject:\"Action Required\" newer_than:60d",
            maxResults=10
        ).execute()
        msgs = results.get("messages", [])
        if msgs:
            logger.info(f"Capital One: {len(msgs)} emails 'Action Required' encontrados")
            # Buscar en DB aplicaciones de Capital One
            with tracker._get_conn() as conn:
                import sqlite3
                conn.row_factory = sqlite3.Row
                rows = conn.execute(
                    "SELECT j.id FROM jobs j JOIN applications a ON j.id=a.job_id WHERE LOWER(j.company) LIKE '%capital one%'"
                ).fetchall()
                for row in rows:
                    tracker.advance_pipeline(row["id"], "response", "Capital One: Action Required email recibido - completar próximos pasos")
                    tracker.mark_verified(row["id"], True)
                    logger.success(f"Capital One job {row['id']} marcado como verificado con acción pendiente")
        return len(msgs)
    except Exception as e:
        logger.error(f"Error verificando Capital One: {e}")
        return 0
