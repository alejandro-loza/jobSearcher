"""
WhatsApp tool: cliente HTTP al bridge de whatsapp-web.js.
"""
import httpx
from loguru import logger
from config import settings


def send_message(text: str, number: str = None) -> bool:
    """
    Envía un mensaje de WhatsApp via el bridge Node.js.

    Args:
        text: Texto del mensaje
        number: Número destino (default: WHATSAPP_MY_NUMBER)

    Returns:
        True si se envió correctamente
    """
    target = number or settings.whatsapp_my_number
    if not target:
        logger.error("WHATSAPP_MY_NUMBER no configurado")
        return False

    try:
        response = httpx.post(
            f"{settings.whatsapp_bridge_url}/send",
            json={"number": target, "message": text},
            timeout=15.0,
        )
        response.raise_for_status()
        logger.debug(f"WhatsApp enviado a {target}: {text[:60]}...")
        return True
    except httpx.HTTPError as e:
        logger.error(f"Error enviando WhatsApp: {e}")
        return False


def send_job_notification(job: dict, match_score: int) -> bool:
    """Envía notificación de nuevo job encontrado."""
    salary_text = f"\n💰 {job['salary']}" if job.get("salary") else ""
    applicants = job.get("applicants")
    if applicants is not None:
        if applicants < 25:
            applicants_text = f"\n🟢 Solo {applicants} aplicantes — alta oportunidad!"
        elif applicants < 100:
            applicants_text = f"\n🟡 {applicants} aplicantes"
        else:
            applicants_text = f"\n🔴 {applicants}+ aplicantes — competido"
    else:
        applicants_text = ""
    source_icon = {"linkedin": "in", "indeed": "Indeed", "glassdoor": "GD"}.get(job.get("source",""), "")
    msg = (
        f"*Nuevo trabajo [{source_icon}]* ({match_score}% match)\n\n"
        f"*{job['title']}* @ {job['company']}\n"
        f"📍 {job.get('location', 'N/A')}"
        f"{salary_text}"
        f"{applicants_text}\n"
        f"🔗 {job.get('url', 'Sin URL')}\n\n"
        f"¿Aplico? Responde *si* o *no*"
    )
    return send_message(msg)


def send_application_confirmation(job: dict) -> bool:
    """Confirma que se aplicó a un trabajo."""
    msg = (
        f"Apliqué a *{job['title']}* en *{job['company']}*.\n"
        f"Daré seguimiento en {settings.followup_days} días si no hay respuesta."
    )
    return send_message(msg)


def send_email_alert(job_title: str, company: str, sentiment: str, summary: str) -> bool:
    """Notifica sobre respuesta de empresa por email."""
    icon = {"positive": "✅", "negative": "❌", "interview": "🎯", "neutral": "📧"}.get(
        sentiment, "📧"
    )
    msg = (
        f"{icon} *Respuesta de {company}*\n"
        f"Puesto: {job_title}\n\n"
        f"{summary}"
    )
    return send_message(msg)


def send_interview_scheduled(job_title: str, company: str, date_str: str) -> bool:
    """Notifica que se agendó una entrevista."""
    msg = (
        f"🎯 *Entrevista agendada!*\n\n"
        f"*{job_title}* en *{company}*\n"
        f"📅 {date_str}\n\n"
        f"Ya la agendé en tu Google Calendar con recordatorios."
    )
    return send_message(msg)


def send_status_report(stats: dict, recent_jobs: list) -> bool:
    """Envía reporte de estado de aplicaciones."""
    jobs_text = ""
    for j in recent_jobs[:5]:
        jobs_text += f"  • {j['title']} @ {j['company']} [{j['status']}]\n"

    msg = (
        f"*Reporte de búsqueda de trabajo*\n\n"
        f"📊 Resumen:\n"
        f"  • Encontrados: {stats['total_found']}\n"
        f"  • Aplicados: {stats['applied']}\n"
        f"  • Entrevistas: {stats['interviews_scheduled']}\n"
        f"  • Rechazados: {stats['rejected']}\n\n"
        f"Últimas aplicaciones:\n{jobs_text}"
    )
    return send_message(msg)
