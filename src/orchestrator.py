"""
Orchestrator: FastAPI + APScheduler.
Coordina búsqueda de jobs, monitoreo de emails, LinkedIn messages y WhatsApp.
"""
import asyncio
import json
import re
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from loguru import logger

from config import settings
from src.db.tracker import JobTracker
from src.agents import master_agent
from src.agents import recruiter_agent
from src.agents.chat_agent import chat_agent
from src.tools import jobspy_tool, gmail_tool, calendar_tool, whatsapp_tool
from src.tools import linkedin_messages_tool, browser_tool
from src.agents import image_inspector_agent

tracker = JobTracker()
scheduler = AsyncIOScheduler()

# Estado en memoria para aprobaciones pendientes de WhatsApp
pending_confirmations: Dict[str, Dict] = {}   # job_id -> {job, score}
pending_recruiter_replies: Dict[str, Dict] = {}  # conv_id -> {analysis, sender, message}
pending_slot_selection: Dict[str, Dict] = {}     # conv_id -> {slots, analysis, sender}


# --- TAREAS SCHEDULED ---

async def job_search_task():
    """Busca nuevos trabajos y notifica al usuario sobre los mejores matches."""
    logger.info("Iniciando búsqueda programada de trabajos...")

    try:
        resume = _load_resume()
        criteria = await asyncio.to_thread(master_agent.extract_search_criteria, resume)

        logger.info(f"Criterios de búsqueda: {criteria}")

        new_jobs_found = 0
        notified = 0

        for term in criteria.get("search_terms", [])[:3]:
            for location in criteria.get("locations", ["remote"])[:2]:
                jobs = await asyncio.to_thread(
                    jobspy_tool.search_jobs,
                    term,
                    location,
                    15,
                    int(settings.job_search_interval_hours * 2),
                )

                for job in jobs:
                    if tracker.job_exists(job["id"]):
                        continue

                    # Filtrar por ubicación: solo remote o México
                    if not _is_valid_location(job.get("location", "")):
                        logger.debug(f"Omitiendo job fuera de México/remote: {job['location']} - {job['title']}")
                        continue

                    # Evaluar match (en thread para no bloquear)
                    score, reason = await asyncio.to_thread(
                        master_agent.evaluate_job_match, job, resume
                    )
                    job["match_score"] = score

                    # Guardar en DB
                    is_new = tracker.save_job(job)
                    if not is_new:
                        continue

                    new_jobs_found += 1

                    if score >= settings.job_match_threshold:
                        # Guardar en pending_confirmations para cuando el usuario responda
                        pending_confirmations[job["id"]] = {
                            "job": job,
                            "score": score,
                            "reason": reason,
                        }

                        # Notificar al usuario
                        whatsapp_tool.send_job_notification(job, score)
                        notified += 1
                        logger.info(f"Notificado job: {job['title']} @ {job['company']} ({score}%)")

        logger.success(
            f"Búsqueda completada: {new_jobs_found} nuevos, {notified} notificados"
        )

    except Exception as e:
        logger.error(f"Error en job_search_task: {e}")
        whatsapp_tool.send_message(f"Error en búsqueda automática: {e}")


async def email_monitor_task():
    """Monitorea Gmail para respuestas de empresas."""
    logger.info("Revisando emails de trabajo...")

    try:
        resume = _load_resume()
        processed_ids = tracker.get_processed_message_ids()
        new_emails = gmail_tool.get_recent_job_emails(processed_ids)

        for email in new_emails:
            analysis = await asyncio.to_thread(
                master_agent.analyze_email_response,
                email["content"],
                email["subject"],
                email["from_address"],
            )

            # Buscar job relacionado en DB
            job_id = _find_job_for_email(analysis.get("company_name", ""))

            email_data = {
                **email,
                "job_id": job_id,
                "sentiment": analysis["sentiment"],
                "action_taken": analysis["action"],
            }
            email_db_id = tracker.save_email(email_data)
            gmail_tool.mark_as_read(email["message_id"])

            action = analysis.get("action", "none")

            if action == "update_rejected":
                if job_id:
                    tracker.update_job_status(job_id, "rejected")
                    job = tracker.get_job(job_id)
                    whatsapp_tool.send_email_alert(
                        job_title=job["title"] if job else analysis.get("job_title_hint", ""),
                        company=analysis["company_name"],
                        sentiment="negative",
                        summary=analysis["summary"],
                    )

            elif action == "schedule_interview":
                _handle_interview_scheduling(analysis, job_id, email_db_id, resume)

            elif action == "send_followup" or analysis.get("reply_needed"):
                reply = analysis.get("suggested_reply", "")
                if reply and email.get("from_address"):
                    sent = gmail_tool.send_email(
                        to=email["from_address"],
                        subject=f"Re: {email['subject']}",
                        body=reply,
                        thread_id=email["thread_id"],
                    )
                    if sent:
                        tracker.mark_followup_sent(email_db_id)

            else:
                # Notificar email neutral/positivo
                if analysis["sentiment"] in ("positive", "neutral") and job_id:
                    job = tracker.get_job(job_id)
                    whatsapp_tool.send_email_alert(
                        job_title=job["title"] if job else "",
                        company=analysis["company_name"],
                        sentiment=analysis["sentiment"],
                        summary=analysis["summary"],
                    )

        logger.success(f"Emails procesados: {len(new_emails)}")

    except Exception as e:
        logger.error(f"Error en email_monitor_task: {e}")


async def linkedin_messages_task():
    """
    Monitorea mensajes de LinkedIn de reclutadores.
    AUTÓNOMO: responde automáticamente excepto cuando necesita decisión de Alejandro.

    Usa SQLite para tracking de conversaciones (dedup, historial, estado).
    Envía respuestas via Voyager API (no Playwright) para garantizar conversación correcta.

    Solo escala a WhatsApp en estos casos:
    - Oferta de trabajo (Alejandro decide si acepta)
    - Negociación salarial o de condiciones
    - Agendar entrevista (Alejandro elige slot)
    - El agente no puede responder con confianza
    """
    logger.info("Revisando mensajes de LinkedIn...")

    try:
        # 1. Obtener conversaciones recientes
        conversations = await asyncio.to_thread(
            linkedin_messages_tool.get_unread_messages, 20
        )

        # Dedup por sender_name
        seen_senders = set()
        unique_convs = []
        for conv in conversations:
            sender = conv.get("sender_name", "")
            if sender and sender not in seen_senders:
                seen_senders.add(sender)
                unique_convs.append(conv)

        new_activity = 0

        # Contactos personales — el agente NO responde, solo notifica a Alejandro
        PERSONAL_CONTACTS_NO_AUTO_REPLY = {"Sam Lewis"}

        for conv in unique_convs:
            conv_id = conv["conversation_id"]
            sender_name = conv.get("sender_name", "Reclutador")
            sender_title = conv.get("sender_title", "")

            # Excepción: contacto personal — NO responder automáticamente
            if any(name.lower() in sender_name.lower() for name in PERSONAL_CONTACTS_NO_AUTO_REPLY):
                logger.info(f"[excepción personal] {sender_name} — notificando a Alejandro sin auto-reply")
                whatsapp_tool.send_message(
                    f"💬 *Mensaje de {sender_name}* en LinkedIn\n"
                    f"Este contacto está en tu lista personal — responde tú manualmente.\n"
                    f"No respondí automáticamente."
                )
                continue

            # 2. Guardar/actualizar conversación en DB
            tracker.save_linkedin_conversation({
                "conversation_id": conv_id,
                "participant_name": sender_name,
                "participant_profile_id": conv.get("sender_profile_id", ""),
                "participant_title": sender_title,
                "profile_url": conv.get("profile_url", ""),
                "last_message_at": conv.get("last_activity", 0),
            })

            # 3. Obtener mensajes completos y guardarlos en DB
            full_msgs = await asyncio.to_thread(
                linkedin_messages_tool.get_full_conversation, conv_id
            )
            new_msgs = 0
            latest_recruiter_msg = ""
            for msg in full_msgs:
                msg_id = tracker.save_linkedin_message({
                    "conversation_id": conv_id,
                    "message_text": msg.get("body", ""),
                    "from_me": msg.get("from_me", False),
                    "linkedin_timestamp": msg.get("deliveredAt", 0),
                })
                if msg_id is not None:
                    new_msgs += 1
                if not msg.get("from_me") and msg.get("body"):
                    latest_recruiter_msg = msg["body"]

            if new_msgs == 0:
                continue  # sin mensajes nuevos en esta conversación

            # 4. Verificar si ya respondimos (dedup)
            if tracker.conversation_has_our_reply(conv_id):
                # Ya respondimos — verificar si hay mensajes nuevos del reclutador
                history = tracker.get_conversation_history(conv_id)
                last_msg = history[-1] if history else {}
                if last_msg.get("from_me"):
                    continue  # último mensaje es nuestro, esperar respuesta

            # Saltar si ya hay una respuesta pendiente en WhatsApp
            if conv_id in pending_recruiter_replies or conv_id in pending_slot_selection:
                continue

            if not latest_recruiter_msg or len(latest_recruiter_msg.strip()) < 5:
                # Intentar con el preview del scrape
                latest_recruiter_msg = conv.get("message", "")
                if not latest_recruiter_msg or len(latest_recruiter_msg.strip()) < 5:
                    continue

            new_activity += 1

            # 5. Obtener historial de DB para contexto del LLM
            db_history = tracker.get_conversation_history(conv_id)
            history_for_llm = [
                {"body": m["message_text"], "from_me": bool(m["from_me"])}
                for m in db_history
            ]

            # 6. Obtener slots del calendario
            free_slots = await asyncio.to_thread(
                calendar_tool.get_free_slots, 7, 60
            )

            # 7. Analizar con LLM
            analysis = await asyncio.to_thread(
                recruiter_agent.analyze_recruiter_message,
                latest_recruiter_msg, sender_name, sender_title,
                history_for_llm, free_slots,
            )

            intent = analysis.get("intent", "general")
            needs_input = analysis.get("needs_user_input", False)

            logger.info(
                f"LinkedIn [{conv_id[:8]}] {sender_name}: intent={intent}, "
                f"needs_input={needs_input}"
            )

            # === DECISIONES QUE REQUIEREN A ALEJANDRO → WhatsApp ===

            if intent == "offer" or needs_input:
                pending_recruiter_replies[conv_id] = {
                    "analysis": analysis,
                    "sender_name": sender_name,
                    "sender_title": sender_title,
                    "original_message": latest_recruiter_msg,
                }
                approval_msg = recruiter_agent.format_whatsapp_approval_request(
                    sender_name=sender_name,
                    sender_title=sender_title,
                    original_message=latest_recruiter_msg,
                    analysis=analysis,
                    source="LinkedIn",
                )
                whatsapp_tool.send_message(approval_msg)
                tracker.update_conversation_state(conv_id, "escalated", f"intent={intent}")
                tracker.mark_messages_processed(conv_id)
                logger.info(f"[escalado→WhatsApp] {sender_name}")
                continue

            if intent == "schedule" and free_slots:
                pending_slot_selection[conv_id] = {
                    "slots": free_slots,
                    "analysis": analysis,
                    "sender_name": sender_name,
                    "sender_title": sender_title,
                    "original_message": latest_recruiter_msg,
                }
                slots_text = "\n".join(
                    f"  *{i+1}.* {s['label']}"
                    for i, s in enumerate(free_slots[:5])
                )
                whatsapp_tool.send_message(
                    f"📅 *{sender_name}* quiere agendar entrevista:\n"
                    f'"{latest_recruiter_msg[:200]}"\n\n'
                    f"Slots disponibles:\n{slots_text}\n\n"
                    f"¿Cuál prefieres? Responde *1*, *2* o *3*"
                )
                tracker.update_conversation_state(conv_id, "escalated", "schedule")
                tracker.mark_messages_processed(conv_id)
                logger.info(f"[escalado→WhatsApp] Entrevista {sender_name}")
                continue

            # === RESPUESTAS AUTÓNOMAS ===

            if intent == "rejection":
                whatsapp_tool.send_message(
                    f"❌ *{sender_name}*: {analysis.get('summary', 'Posición cerrada')}"
                )
                tracker.update_conversation_state(conv_id, "closed", "rejection")
                tracker.mark_messages_processed(conv_id)
                continue

            # info, general → responder automáticamente via Voyager API
            draft = analysis.get("draft_response", "")
            if draft:
                sent = await asyncio.to_thread(
                    linkedin_messages_tool.send_message, conv_id, draft
                )
                if sent:
                    tracker.record_our_reply(conv_id, draft)
                    logger.success(f"[auto-reply] {sender_name}: {draft[:60]}...")
                else:
                    logger.warning(f"[auto-reply] Falló envío a {sender_name}")
                    tracker.update_conversation_state(conv_id, "new", "send_failed")

            tracker.mark_messages_processed(conv_id)

        logger.success(
            f"LinkedIn: {len(unique_convs)} conv revisadas, {new_activity} con actividad nueva"
        )

    except Exception as e:
        logger.error(f"Error en linkedin_messages_task: {e}")


async def linkedin_content_task():
    """Publica contenido tech en LinkedIn para promocionar el perfil de Alejandro."""
    logger.info("Ejecutando linkedin_content_task...")
    try:
        from src.agents import linkedin_content_agent
        success = linkedin_content_agent.create_and_publish_post()
        if success:
            logger.success("Post LinkedIn publicado exitosamente")
        else:
            logger.warning("No se pudo publicar el post LinkedIn")
    except Exception as e:
        logger.error(f"Error en linkedin_content_task: {e}")


async def linkedin_hr_expansion_task():
    """Busca y conecta con reclutadores en LinkedIn para ampliar la red de Alejandro."""
    logger.info("Ejecutando linkedin_hr_expansion_task...")
    try:
        from src.agents import linkedin_hr_agent
        result = linkedin_hr_agent.expand_hr_network(max_requests=5)
        sent = result.get("sent", 0)
        if sent > 0:
            whatsapp_tool.send_message(
                f"🤝 Red LinkedIn ampliada: {sent} nuevas conexiones con reclutadores enviadas."
            )
        logger.info(f"HR expansion: {result}")
    except Exception as e:
        logger.error(f"Error en linkedin_hr_expansion_task: {e}")


async def premium_job_search_task():
    """Busca trabajos premium (score >= 82%) y notifica por WhatsApp."""
    logger.info("Ejecutando premium_job_search_task...")
    try:
        resume = _load_resume()
        premium_terms = [
            "Senior Java Developer remote",
            "Senior Spring Boot Engineer remote",
            "Senior Backend Engineer Java remote",
            "Staff Software Engineer Java",
            "Senior Full Stack Java remote Mexico",
            "Senior Software Engineer microservices remote",
            "Senior Cloud Engineer Java AWS remote",
            "Lead Java Developer remote",
        ]

        from src.tools import jobspy_tool
        all_premium = []

        for term in premium_terms:
            try:
                jobs = await asyncio.to_thread(
                    jobspy_tool.search_jobs,
                    search_term=term,
                    location="remote",
                    results_wanted=10,
                    hours_old=24,  # solo últimas 24h
                )
                for job in jobs:
                    score, reasons = await asyncio.to_thread(
                        master_agent.evaluate_job_match, job, resume
                    )
                    if score >= 82:
                        job["match_score"] = score
                        job["match_reasons"] = reasons
                        all_premium.append(job)
                        tracker.save_job(job, score)
            except Exception as e:
                logger.warning(f"Premium search failed for '{term}': {e}")

        if all_premium:
            # Dedup by URL
            seen = set()
            unique = []
            for j in all_premium:
                url = j.get("url", "")
                if url not in seen:
                    seen.add(url)
                    unique.append(j)

            unique.sort(key=lambda x: x.get("match_score", 0), reverse=True)
            top5 = unique[:5]
            msg = f"🏆 {len(unique)} vacantes premium encontradas (score >= 82%):\n\n"
            for j in top5:
                msg += f"• [{j.get('match_score')}%] {j.get('title', '')} @ {j.get('company', '')}\n"
            if len(unique) > 5:
                msg += f"\n...y {len(unique) - 5} más."
            whatsapp_tool.send_message(msg)

        logger.info(f"Premium search: {len(all_premium)} jobs found with score >= 82%")
    except Exception as e:
        logger.error(f"Error en premium_job_search_task: {e}")


async def image_cleanup_task():
    """Limpia imágenes huérfanas que no están asociadas a ningún post."""
    logger.info("Ejecutando image_cleanup_task...")
    try:
        import glob as glob_mod
        log_file = "data/linkedin_posts_log.json"
        if os.path.exists(log_file):
            with open(log_file) as f:
                log = json.load(f)
        else:
            log = {"posts": []}

        # Collect all image paths referenced in log
        referenced = set()
        for p in log.get("posts", []):
            img = p.get("image_path", "")
            if img:
                referenced.add(img)

        # Find all images on disk
        images_dir = "data/linkedin_images"
        if not os.path.exists(images_dir):
            return

        all_images = glob_mod.glob(os.path.join(images_dir, "*.png"))
        orphans = [img for img in all_images if img not in referenced]

        for img in orphans:
            try:
                os.remove(img)
                logger.info(f"[cleanup] Deleted orphan image: {img}")
            except OSError:
                pass

        if orphans:
            logger.info(f"[cleanup] Removed {len(orphans)} orphan images")
    except Exception as e:
        logger.error(f"Error en image_cleanup_task: {e}")


async def image_inspection_task():
    """Inspecciona infografías pendientes: verifica datos y diseño, publica o elimina."""
    logger.info("Ejecutando image_inspection_task...")
    try:
        result = await asyncio.to_thread(
            image_inspector_agent.inspect_and_process_pending_posts
        )
        logger.info(f"Image inspection: {result}")
        approved = result.get("approved", 0)
        rejected = result.get("rejected", 0)
        if approved > 0:
            whatsapp_tool.send_message(
                f"📊 Publiqué {approved} post(s) en LinkedIn tras inspección de calidad."
            )
        if rejected > 0:
            whatsapp_tool.send_message(
                f"🗑️ Rechacé {rejected} infografía(s) por problemas de calidad. "
                "Se eliminaron las imágenes defectuosas."
            )
    except Exception as e:
        logger.error(f"Error en image_inspection_task: {e}")


async def linkedin_cookie_refresh_task():
    """Renueva cookies de LinkedIn automáticamente via login."""
    logger.info("Renovando cookies de LinkedIn...")
    try:
        success = await asyncio.to_thread(
            linkedin_messages_tool.refresh_cookies
        )
        if success:
            logger.success("Cookies de LinkedIn renovadas automáticamente")
        else:
            logger.warning("No se pudieron renovar cookies de LinkedIn")
    except Exception as e:
        logger.error(f"Error renovando cookies LinkedIn: {e}")


async def followup_task():
    """Envía follow-up emails a aplicaciones sin respuesta."""
    logger.info("Revisando aplicaciones para follow-up...")

    try:
        resume = _load_resume()
        pending = tracker.get_applications_pending_followup()

        for app in pending:
            days_since = int(app.get("days_since_apply", settings.followup_days))
            followup = master_agent.generate_followup_email(app, resume, days_since)

            # Intentar obtener email de la empresa del job
            job_emails = app.get("emails_in_job", "")
            if job_emails and "@" in str(job_emails):
                to_email = str(job_emails).split(",")[0].strip()
            else:
                logger.warning(
                    f"No hay email para follow-up de {app['title']} @ {app['company']}"
                )
                continue

            sent = gmail_tool.send_email(
                to=to_email,
                subject=followup["subject"],
                body=followup["body"],
            )

            if sent:
                whatsapp_tool.send_message(
                    f"Envié follow-up a *{app['company']}* por el puesto *{app['title']}*"
                )

    except Exception as e:
        logger.error(f"Error en followup_task: {e}")


# --- HELPERS ---

_MEXICO_KEYWORDS = {
    "remote", "remoto", "anywhere", "worldwide", "global",
    "mexico", "méxico", "cdmx", "ciudad de mexico", "ciudad de méxico",
    "monterrey", "guadalajara", "jalisco", "nuevo leon", "nuevo león",
}

def _is_valid_location(location: str) -> bool:
    """Retorna True si el job es remote o está en México."""
    loc_lower = location.lower().strip()
    if not loc_lower or loc_lower in ("none", "nan", ""):
        return True  # sin ubicación = aceptar (puede ser remote)
    return any(kw in loc_lower for kw in _MEXICO_KEYWORDS)


def _load_resume() -> Dict:
    try:
        with open(settings.resume_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning(f"CV no encontrado en {settings.resume_file}, usando ejemplo")
        with open("data/resume_example.json", "r", encoding="utf-8") as f:
            return json.load(f)


def _find_job_for_email(company_name: str) -> str | None:
    """Busca en DB un job applied que coincida con el nombre de empresa."""
    if not company_name:
        return None
    jobs = tracker.get_jobs_by_status("applied")
    company_lower = company_name.lower()
    for job in jobs:
        if company_lower in job.get("company", "").lower():
            return job["id"]
    return None


def _handle_interview_scheduling(
    analysis: Dict, job_id: str, email_db_id: int, resume: Dict
):
    """Agenda entrevista en Calendar y notifica por WhatsApp."""
    try:
        date_hint = analysis.get("interview_date_hint")
        meeting_link = analysis.get("interview_link", "")
        interviewer_email = analysis.get("interviewer_email")

        # Parsear fecha del hint (best effort)
        interview_dt = None
        if date_hint:
            for fmt in ["%Y-%m-%d %H:%M", "%d/%m/%Y %H:%M", "%d de %B de %Y"]:
                try:
                    interview_dt = datetime.strptime(date_hint, fmt)
                    break
                except ValueError:
                    continue

        job = tracker.get_job(job_id) if job_id else None
        job_title = job["title"] if job else analysis.get("job_title_hint", "Posición")
        company = job["company"] if job else analysis.get("company_name", "Empresa")

        event_id = None
        date_str = date_hint or "Fecha por confirmar"

        if interview_dt:
            event_id = calendar_tool.create_interview_event(
                job_title=job_title,
                company=company,
                start_datetime=interview_dt,
                interviewer_email=interviewer_email,
                meeting_link=meeting_link or "",
            )
            date_str = interview_dt.strftime("%d/%m/%Y %H:%M")

        if job_id:
            tracker.save_interview({
                "job_id": job_id,
                "email_id": email_db_id,
                "scheduled_at": interview_dt.isoformat() if interview_dt else None,
                "calendar_event_id": event_id,
                "interviewer": interviewer_email,
            })

        whatsapp_tool.send_interview_scheduled(job_title, company, date_str)

    except Exception as e:
        logger.error(f"Error agendando entrevista: {e}")


# --- FASTAPI APP ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Iniciando orchestrator...")

    # Búsqueda de empleos: diario a medianoche
    scheduler.add_job(
        job_search_task,
        "cron",
        hour=0,
        minute=0,
        id="job_search",
    )
    # Email monitor: cada 6 horas
    scheduler.add_job(
        email_monitor_task,
        "interval",
        hours=6,
        id="email_monitor",
    )
    scheduler.add_job(
        followup_task,
        "cron",
        hour=9,
        minute=0,
        id="followup",
    )
    # LinkedIn messages: cada 6 horas
    scheduler.add_job(
        linkedin_messages_task,
        "interval",
        hours=6,
        id="linkedin_messages",
    )
    # LinkedIn content: genera 1 post diario (inspector lo revisará antes de publicar)
    scheduler.add_job(
        linkedin_content_task,
        "cron",
        hour=8,
        minute=0,
        day_of_week="mon-fri",
        id="linkedin_content",
    )
    # Búsqueda premium de empleos: diario a las 7am
    scheduler.add_job(
        premium_job_search_task,
        "cron",
        hour=7,
        minute=0,
        id="premium_job_search",
    )
    # Limpieza de imágenes huérfanas: domingos a las 3am
    scheduler.add_job(
        image_cleanup_task,
        "cron",
        hour=3,
        minute=0,
        day_of_week="sun",
        id="image_cleanup",
    )
    # Expandir red de RH: 3pm Lunes a Viernes
    scheduler.add_job(
        linkedin_hr_expansion_task,
        "cron",
        hour=15,
        minute=0,
        day_of_week="mon-fri",
        id="linkedin_hr_expansion",
    )
    # Inspección de infografías: cada 6h en horario laboral (9am, 3pm, 9pm) Lun-Vie
    scheduler.add_job(
        image_inspection_task,
        "cron",
        hour="9,15,21",
        minute=30,
        day_of_week="mon-fri",
        id="image_inspection",
    )
    # Renovar cookies de LinkedIn automáticamente cada 12h
    scheduler.add_job(
        linkedin_cookie_refresh_task,
        "interval",
        hours=12,
        id="linkedin_cookie_refresh",
    )

    scheduler.start()
    logger.success("Scheduler iniciado")

    whatsapp_tool.send_message(
        "Agente de búsqueda de empleo activo.\n\n"
        "Haré esto por ti automáticamente:\n"
        "• Buscar jobs cada " + str(settings.job_search_interval_hours) + "h\n"
        "• Revisar mensajes de LinkedIn cada 15min\n"
        "• Revisar emails cada " + str(settings.email_check_interval_minutes) + "min\n"
        "• Hablar con reclutadores en tu nombre\n"
        "• Agendar entrevistas en tu calendario\n\n"
        "Te consultaré por aquí antes de enviar cualquier respuesta.\n\n"
        "Comandos:\n"
        "• *estado* - resumen de aplicaciones\n"
        "• *buscar [rol]* - búsqueda manual\n"
        "• *entrevistas* - próximas entrevistas\n"
        "• *pausar* / *reanudar* - control del agente"
    )

    yield

    # Shutdown
    scheduler.shutdown()
    logger.info("Orchestrator detenido")


app = FastAPI(title="JobSearcher Orchestrator", lifespan=lifespan)


@app.post("/webhook/whatsapp")
async def whatsapp_webhook(request: Request):
    """Recibe mensajes de WhatsApp del bridge Node.js."""
    body = await request.json()
    message = body.get("message", "").strip().lower()
    raw_message = body.get("message", "").strip()

    logger.info(f"WhatsApp recibido: {raw_message}")

    # Procesar en background para no bloquear el bridge (evita timeout)
    asyncio.create_task(_process_whatsapp(raw_message, message))
    return {"ok": True}


async def _process_whatsapp(raw_message: str, message: str):

    # --- FLUJO 1: Selección de slot de entrevista (1, 2, 3) ---
    if pending_slot_selection and message in ("1", "2", "3"):
        await _handle_slot_selection(int(message))
        return {"ok": True}

    # --- FLUJO 2: Aprobación de respuesta a reclutador ---
    if pending_recruiter_replies:
        if message in ("si", "sí", "yes", "s"):
            await _handle_recruiter_approval(approved=True)
            return {"ok": True}
        if message in ("no", "n"):
            await _handle_recruiter_approval(approved=False)
            return {"ok": True}
        if raw_message.lower().startswith("editar "):
            custom_text = raw_message[7:].strip()
            await _handle_recruiter_approval(approved=True, custom_text=custom_text)
            return {"ok": True}

    # --- FLUJO 3: Confirmación de aplicación a job ---
    if pending_confirmations:
        if message in ("si", "sí", "yes", "s"):
            await _handle_job_confirmation(approved=True)
            return {"ok": True}
        if message in ("no", "n"):
            await _handle_job_confirmation(approved=False)
            return {"ok": True}

    # --- COMANDO: aplicar a todos los pendientes ---
    if message in ("todos", "aplica todos", "aplicar todos", "all"):
        if pending_confirmations:
            total = len(pending_confirmations)
            whatsapp_tool.send_message(f"Aplicando a los {total} trabajos pendientes...")
            # Procesar todos en background para no bloquear
            asyncio.create_task(_apply_all_pending())
        else:
            whatsapp_tool.send_message("No hay trabajos pendientes de aprobación ahora mismo.")
        return {"ok": True}

    # --- COMANDOS ---
    if "estado" in message or "reporte" in message or "status" in message:
        stats = tracker.get_stats()
        recent = tracker.get_all_jobs(limit=5)
        whatsapp_tool.send_status_report(stats, recent)

    elif message.startswith("buscar"):
        keywords = raw_message[6:].strip() or "developer"
        whatsapp_tool.send_message(f"Buscando '{keywords}'... te aviso cuando encuentre algo.")
        # Lanzar búsqueda manual en background
        scheduler.add_job(
            lambda: _manual_search(keywords),
            "date",
            id="manual_search",
            replace_existing=True,
        )

    elif "pausar" in message or "pause" in message:
        if scheduler.get_job("job_search"):
            scheduler.pause_job("job_search")
        whatsapp_tool.send_message("Búsqueda automática pausada.")

    elif "reanudar" in message or "resume" in message:
        if scheduler.get_job("job_search"):
            scheduler.resume_job("job_search")
        whatsapp_tool.send_message("Búsqueda automática reanudada.")

    elif "entrevistas" in message or "interview" in message:
        events = calendar_tool.get_upcoming_events(days=14)
        if events:
            text = "Próximas entrevistas:\n"
            for e in events:
                start = e.get("start", {}).get("dateTime", "")
                text += f"  • {e.get('summary', '')} - {start}\n"
        else:
            text = "No tienes entrevistas programadas."
        whatsapp_tool.send_message(text)

    else:
        # Respuesta libre con LLM
        resume = _load_resume()
        stats = tracker.get_stats()
        response = await asyncio.to_thread(
            master_agent.handle_whatsapp_command, raw_message, stats, resume
        )
        whatsapp_tool.send_message(response)


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    """Dashboard web de trazabilidad de aplicaciones."""
    from src.dashboard import generate_dashboard_html
    from fastapi.responses import HTMLResponse
    return HTMLResponse(content=generate_dashboard_html())


@app.get("/pipeline")
async def pipeline():
    """API JSON del pipeline para integraciones."""
    return {
        "pipeline": tracker.get_pipeline_summary(),
        "applications": tracker.get_full_pipeline(limit=100),
    }


@app.post("/application/{job_id}/stage")
async def update_stage(job_id: str, stage: str, notes: str = ""):
    """Avanza manualmente el pipeline de una aplicación."""
    if stage not in JobTracker.PIPELINE_STAGES:
        return {"error": f"Stage inválido. Opciones: {JobTracker.PIPELINE_STAGES}"}
    tracker.advance_pipeline(job_id, stage, notes)
    return {"ok": True, "job_id": job_id, "stage": stage}


@app.post("/application/{job_id}/verify")
async def verify_application(job_id: str):
    """Marca una aplicación como verificada (realmente enviada)."""
    tracker.mark_verified(job_id, True)
    return {"ok": True, "job_id": job_id, "verified": True}


@app.post("/verify/gmail")
async def verify_via_gmail(days_back: int = 60):
    """Busca emails de confirmación en Gmail y actualiza la DB."""
    from src.tools.application_verifier import verify_applications_via_gmail, verify_capital_one
    result = await asyncio.to_thread(verify_applications_via_gmail, days_back)
    capital_one = await asyncio.to_thread(verify_capital_one, tracker)
    result["capital_one_actions"] = capital_one
    return result


@app.get("/tokens")
async def token_stats():
    """Estadísticas de tokens usados por LLM y tarea."""
    from src.agents.coordinator import get_token_stats
    return get_token_stats()


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "scheduler_jobs": [j.id for j in scheduler.get_jobs()],
        "db_stats": tracker.get_stats(),
    }


# --- NEW DASHBOARD APIs ---

@app.get("/api/stats")
async def get_stats_api():
    """Estadísticas consolidadas para el dashboard."""
    return tracker.get_stats()


@app.get("/api/jobs")
async def get_jobs_api(status: str = "found", limit: int = 100):
    """Lista de jobs filtrada."""
    if status == "all":
        return tracker.get_all_jobs(limit=limit)
    return tracker.get_jobs_by_status(status)


@app.get("/api/applications")
async def get_applications_api(limit: int = 100):
    """Lista de aplicaciones con pipeline stage."""
    return tracker.get_full_pipeline(limit=limit)


@app.get("/api/conversations")
async def get_conversations_api():
    """Conversaciones de LinkedIn unread/pendientes."""
    return tracker.get_unprocessed_conversations()


@app.get("/api/interviews")
async def get_interviews_api(days: int = 14):
    """Eventos de calendario próximos."""
    return calendar_tool.get_upcoming_events(days=days)


@app.post("/api/chat")
async def chat_api(request: Request):
    """Chatbot del dashboard."""
    body = await request.json()
    message = body.get("message", "")
    if not message:
        return {"response": "No recibí ningún mensaje."}
    
    response = await chat_agent.handle_message(message)
    return {"response": response}


@app.post("/trigger/search")
async def trigger_search():
    """Trigger manual de búsqueda (para testing)."""
    scheduler.add_job(job_search_task, "date", id="manual_trigger", replace_existing=True)
    return {"ok": True, "message": "Búsqueda iniciada"}


@app.post("/trigger/apply-all")
async def trigger_apply_all():
    """Carga todos los jobs pendientes de DB y aplica a todos."""
    # Cargar jobs con score >= threshold que aún no fueron aplicados
    all_jobs = tracker.get_jobs_by_status("found")
    resume = _load_resume()
    loaded = 0
    for job in all_jobs:
        job_id = job["id"]
        score = job.get("match_score", 0)
        if score >= settings.job_match_threshold and job_id not in pending_confirmations:
            pending_confirmations[job_id] = {"job": job, "score": score, "reason": ""}
            loaded += 1

    if loaded == 0:
        return {"ok": True, "message": f"No hay jobs con score >= {settings.job_match_threshold}% listos para aplicar"}

    asyncio.create_task(_apply_all_pending())
    return {"ok": True, "message": f"Aplicando a {loaded} jobs con score >= {settings.job_match_threshold}%"}


@app.post("/trigger/email")
async def trigger_email():
    """Trigger manual de monitoreo de email (para testing)."""
    scheduler.add_job(email_monitor_task, "date", id="manual_email", replace_existing=True)
    return {"ok": True, "message": "Monitoreo de email iniciado"}


@app.post("/trigger/linkedin-post")
async def trigger_linkedin_post():
    """Trigger manual: genera y publica un post LinkedIn ahora."""
    scheduler.add_job(linkedin_content_task, "date", id="manual_linkedin_post", replace_existing=True)
    return {"ok": True, "message": "Post LinkedIn en proceso"}


@app.post("/trigger/linkedin-hr")
async def trigger_linkedin_hr():
    """Trigger manual: busca y conecta con reclutadores LinkedIn ahora."""
    scheduler.add_job(linkedin_hr_expansion_task, "date", id="manual_linkedin_hr", replace_existing=True)
    return {"ok": True, "message": "Expansión de red HR en proceso"}


@app.post("/trigger/inspect-images")
async def trigger_inspect_images():
    """Trigger manual: inspecciona infografías pendientes ahora."""
    scheduler.add_job(image_inspection_task, "date", id="manual_image_inspection", replace_existing=True)
    return {"ok": True, "message": "Inspección de imágenes en proceso"}


@app.post("/trigger/premium-search")
async def trigger_premium_search():
    """Trigger manual: búsqueda premium de empleos ahora."""
    scheduler.add_job(premium_job_search_task, "date", id="manual_premium_search", replace_existing=True)
    return {"ok": True, "message": "Búsqueda premium en proceso"}


@app.post("/trigger/image-cleanup")
async def trigger_image_cleanup():
    """Trigger manual: limpieza de imágenes huérfanas ahora."""
    scheduler.add_job(image_cleanup_task, "date", id="manual_image_cleanup", replace_existing=True)
    return {"ok": True, "message": "Limpieza de imágenes en proceso"}


@app.get("/linkedin/posts")
async def get_linkedin_posts():
    """Retorna el historial de posts publicados en LinkedIn."""
    import json as _json
    log_path = Path("data/linkedin_posts_log.json")
    if not log_path.exists():
        return {"posts": [], "total": 0}
    posts = _json.loads(log_path.read_text())
    return {"posts": posts[-20:], "total": len(posts)}


@app.get("/linkedin/hr-contacts")
async def get_hr_contacts():
    """Retorna el log de conexiones HR enviadas."""
    import json as _json
    log_path = Path("data/linkedin_hr_log.json")
    if not log_path.exists():
        return {"contacts": [], "total": 0}
    contacts = _json.loads(log_path.read_text())
    return {"contacts": contacts[-20:], "total": len(contacts)}


async def _apply_all_pending():
    """Aplica a todos los jobs pendientes de confirmación."""
    jobs_to_apply = list(pending_confirmations.items())
    applied = 0
    errors = 0
    resume = _load_resume()

    # Pausar scheduler para evitar conflictos de DB
    for job_id_sched in ["job_search", "email_monitor", "linkedin_messages"]:
        try:
            scheduler.pause_job(job_id_sched)
        except Exception:
            pass

    for job_id, item in jobs_to_apply:
        pending_confirmations.pop(job_id, None)
        job = item["job"]
        try:
            # Cover letter: intentar generarla, si falla usar plantilla simple
            try:
                cover_letter = await asyncio.to_thread(master_agent.generate_cover_letter, job, resume)
            except Exception:
                cover_letter = (
                    f"Hi, I'm {resume.get('full_name', 'Alejandro Hernandez Loza')}, "
                    f"a {resume.get('professional_title', 'SR. Software Engineer')} with "
                    f"{resume.get('years_of_experience', 12)}+ years of experience. "
                    f"I'm very interested in the {job.get('title', '')} position at {job.get('company', '')}. "
                    "I'd love to discuss how my background aligns with your needs."
                )

            job_url = job.get("url", job.get("job_url", ""))
            method = "pending_manual"
            apply_success = False

            # Try browser_tool for ALL jobs with valid URLs (including easy_apply)
            if job_url and job_url != "nan":
                try:
                    result = await asyncio.to_thread(
                        browser_tool.apply_to_job_sync, job_url, resume, job["title"], job["company"], cover_letter
                    )
                    if result.get("success"):
                        method = "browser_agent"
                        apply_success = True
                        logger.info(f"CONFIRMADO: Aplicación enviada a {job['title']} @ {job['company']}")
                    elif result.get("status") == "captcha":
                        method = "blocked_captcha"
                        logger.warning(f"CAPTCHA en {job['title']} @ {job['company']} - requiere manual")
                    elif result.get("status") == "need_user":
                        method = "needs_info"
                        logger.warning(f"Info requerida para {job['title']}: {result.get('message')}")
                    else:
                        method = "browser_failed"
                        logger.warning(f"Browser no pudo aplicar a {job['title']}: {result.get('message')}")
                except Exception as be:
                    logger.warning(f"Browser error para {job['title']}: {be}")
                    method = "browser_error"

            # Save application with actual status
            status = "applied" if apply_success else "pending_apply"
            tracker.save_application(
                job_id=job_id, method=method, cover_letter=cover_letter,
                status=status
            )

            if apply_success:
                applied += 1
            else:
                errors += 1

            logger.info(f"{'APLICADO' if apply_success else 'PENDIENTE'}: {job['title']} @ {job['company']} via {method}")

            await asyncio.sleep(8)  # pausa para no saturar rate limits

        except Exception as e:
            errors += 1
            logger.error(f"Error aplicando a {job.get('title')}: {e}")
            await asyncio.sleep(5)

    # Reanudar scheduler
    for job_id_sched in ["job_search", "email_monitor", "linkedin_messages"]:
        try:
            scheduler.resume_job(job_id_sched)
        except Exception:
            pass

    whatsapp_tool.send_message(
        f"Listo. Apliqué a *{applied}* trabajos."
        + (f" ({errors} con problemas)" if errors else "")
    )


async def _handle_job_confirmation(approved: bool):
    """Procesa confirmación si/no del usuario para aplicar a un job."""
    if not pending_confirmations:
        whatsapp_tool.send_message("No hay aplicaciones pendientes de confirmación.")
        return

    # Tomar el más reciente
    job_id = next(iter(pending_confirmations))
    item = pending_confirmations.pop(job_id)
    job = item["job"]
    resume = _load_resume()

    if approved:
        cover_letter = master_agent.generate_cover_letter(job, resume)
        job_url = job.get("url", "")
        method = job.get("source", "job_board")

        # Decidir método de aplicación
        if job.get("easy_apply") and "linkedin.com" in job_url:
            # Easy Apply de LinkedIn (directo)
            tracker.save_application(job_id=job_id, method="linkedin_easy_apply", cover_letter=cover_letter)
            whatsapp_tool.send_application_confirmation(job)
            logger.info(f"Aplicado via Easy Apply: {job['title']} @ {job['company']}")

        elif job_url and job_url != "nan":
            # URL externa → browser agent
            whatsapp_tool.send_message(
                f"Navegando para aplicar a *{job['title']}* @ *{job['company']}*...\n"
                f"Te aviso cuando termine."
            )
            result = browser_tool.apply_to_job_sync(
                job_url=job_url,
                resume=resume,
                job_title=job["title"],
                company=job["company"],
            )
            method = "browser_agent"
            tracker.save_application(job_id=job_id, method=method, cover_letter=cover_letter)
            if not result["success"]:
                tracker.update_application_status(job_id, result["status"])
        else:
            # Sin URL → guardar como pendiente
            tracker.save_application(job_id=job_id, method="manual_pending", cover_letter=cover_letter)
            whatsapp_tool.send_message(
                f"Guardé *{job['title']}* @ *{job['company']}* para aplicar.\n"
                f"No encontré URL directa — revisa LinkedIn manualmente."
            )

        logger.info(f"Procesada aplicación: {job['title']} @ {job['company']} ({method})")
    else:
        tracker.update_job_status(job_id, "skipped")
        whatsapp_tool.send_message(f"Ok, omitido: *{job['title']}* en *{job['company']}*")

        # Si hay más pendientes, enviar el siguiente
        if pending_confirmations:
            next_id = next(iter(pending_confirmations))
            next_item = pending_confirmations[next_id]
            whatsapp_tool.send_job_notification(next_item["job"], next_item["score"])


async def _manual_search(keywords: str):
    """Búsqueda manual triggered desde WhatsApp."""
    resume = _load_resume()
    jobs = jobspy_tool.search_jobs(
        search_term=keywords,
        location="remote",
        results_wanted=10,
        hours_old=168,
    )

    found = 0
    for job in jobs:
        if tracker.job_exists(job["id"]):
            continue
        score, reason = master_agent.evaluate_job_match(job, resume)
        job["match_score"] = score
        tracker.save_job(job)

        if score >= settings.job_match_threshold:
            pending_confirmations[job["id"]] = {"job": job, "score": score, "reason": reason}
            whatsapp_tool.send_job_notification(job, score)
            found += 1

    if found == 0:
        whatsapp_tool.send_message(
            f"Búsqueda de '{keywords}' completa. "
            f"No encontré matches con score >= {settings.job_match_threshold}%."
        )


async def _handle_recruiter_approval(approved: bool, custom_text: str = None):
    """Procesa aprobación/rechazo/edición de respuesta a reclutador."""
    if not pending_recruiter_replies:
        return

    conv_id = next(iter(pending_recruiter_replies))
    item = pending_recruiter_replies.pop(conv_id)
    analysis = item["analysis"]
    sender_name = item["sender_name"]

    if not approved:
        whatsapp_tool.send_message(f"Ok, no respondo a *{sender_name}* por ahora.")
        return

    # Determinar texto final a enviar
    if custom_text:
        # Usuario editó la respuesta
        final_text = recruiter_agent.refine_response(
            original_draft=analysis["draft_response"],
            user_feedback=custom_text,
            language=analysis.get("language", "es"),
        )
    else:
        final_text = analysis["draft_response"]

    sent = linkedin_messages_tool.send_message(conv_id, final_text)

    if sent:
        whatsapp_tool.send_message(
            f"Enviado a *{sender_name}* en LinkedIn:\n_{final_text[:200]}_"
        )
    else:
        whatsapp_tool.send_message(
            f"No pude enviar el mensaje a LinkedIn. Intenta manualmente."
        )


async def _handle_slot_selection(choice: int):
    """Procesa selección de slot de entrevista (1, 2 o 3)."""
    if not pending_slot_selection:
        return

    conv_id = next(iter(pending_slot_selection))
    item = pending_slot_selection.pop(conv_id)
    slots = item["slots"]
    analysis = item["analysis"]
    sender_name = item["sender_name"]

    if choice == 0 or choice > len(slots):
        whatsapp_tool.send_message(f"Ok, decliné la entrevista con *{sender_name}*.")
        linkedin_messages_tool.send_message(
            conv_id,
            "Gracias por contactarme. Por el momento no podré avanzar con el proceso. ¡Saludos!"
            if analysis.get("language") == "es"
            else "Thank you for reaching out. I won't be able to move forward at this time. Best regards!"
        )
        return

    selected_slot = slots[choice - 1]

    # Responder al reclutador con el slot seleccionado
    if analysis.get("language") == "en":
        reply = (
            f"Hi! Thank you for reaching out. "
            f"I'm available on {selected_slot['label']}. "
            f"Please let me know if that works for you. Looking forward to our conversation!"
        )
    else:
        reply = (
            f"Hola, gracias por contactarme. "
            f"Tengo disponibilidad el {selected_slot['label']}. "
            f"¿Te funciona ese horario? Quedo pendiente."
        )

    linkedin_messages_tool.send_message(conv_id, reply)

    # Crear evento en Calendar
    from datetime import datetime as dt
    try:
        slot_dt = dt.fromisoformat(selected_slot["start_iso"])
        event_id = calendar_tool.create_interview_event(
            job_title="Entrevista",
            company=sender_name,
            start_datetime=slot_dt,
            duration_minutes=60,
        )
        whatsapp_tool.send_message(
            f"Confirmé con *{sender_name}*: {selected_slot['label']}\n"
            f"Ya lo agendé en tu Google Calendar."
        )
    except Exception as e:
        logger.error(f"Error agendando slot: {e}")
        whatsapp_tool.send_message(
            f"Respondí a *{sender_name}* con el horario {selected_slot['label']}.\n"
            f"(No pude crear el evento en Calendar: {e})"
        )
