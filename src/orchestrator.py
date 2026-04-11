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
from src.agents import response_decision_agent
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

# --- SAFETY SWITCHES ---
# Deshabilitar envío automático de emails para evitar spam.
AUTO_EMAIL_DISABLED = True
# Deshabilitar respuestas automáticas de LinkedIn.
AUTO_LINKEDIN_REPLY_DISABLED = True

# Contactos NUNCA tocar — el agente NUNCA envía mensajes ni emails a estas personas.
BLOCKED_CONTACTS_NEVER_REPLY: set[str] = {
    "Sam Lewis",        # ex-jefa de Alejandro — responder manualmente
    "Melba Ruiz",       # Thomson Reuters — manejo personal de reingreso
    "Melba Ruiz Moron", # variante de nombre
}


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


EMAIL_BLOCKLIST = {
    "padma@ptechpartners.com",
}
EMAIL_BLOCKLIST_DOMAINS = {
    "noreply", "no-reply", "notifications", "mailer", "bounce",
    "donotreply", "do-not-reply", "updates@e.mission", "ccsend.com",
}
MAX_AUTO_REPLIES_PER_CYCLE = 3  # anti-spam: máximo 3 auto-replies por ciclo de 30min


def _is_blocked_sender(from_address: str) -> bool:
    """Verifica si el remitente está en blocklist o es un dominio de notificaciones."""
    addr = from_address.lower()
    if addr in EMAIL_BLOCKLIST:
        return True
    return any(blocked in addr for blocked in EMAIL_BLOCKLIST_DOMAINS)


async def email_monitor_task():
    """Monitorea Gmail para respuestas de empresas."""
    logger.info("Revisando emails de trabajo...")

    try:
        resume = _load_resume()
        processed_ids = tracker.get_processed_message_ids()
        new_emails = gmail_tool.get_recent_job_emails(processed_ids)

        auto_replies_sent = 0

        for email in new_emails:
            from_addr = email.get("from_address", "")
            thread_id  = email.get("thread_id", "")
            content    = email.get("content", "")
            subject    = email.get("subject", "")

            # ── Paso 1: Response Decision Agent (ÚLTIMA PALABRA) ─────────────
            # Cargar hilo completo (recibidos + enviados) para contexto del agente
            thread_history = tracker.get_email_thread_history(thread_id) if thread_id else []
            last_msg_ours = bool(thread_history and thread_history[-1].get("from_me"))

            decision_result = await asyncio.to_thread(
                response_decision_agent.decide_and_log,
                from_address=from_addr,
                message_body=content,
                subject_or_title=subject,
                thread_id_or_conv_id=thread_id,
                last_message_is_ours=last_msg_ours,
                conversation_history=thread_history,
                source="email",
            )

            # Siempre guardar en DB con el resultado de la decisión
            analysis = await asyncio.to_thread(
                master_agent.analyze_email_response,
                content, subject, from_addr,
            ) if decision_result.decision == response_decision_agent.ResponseDecision.AUTO_RESPOND else {
                "sentiment": "neutral", "action": "none",
                "company_name": "", "summary": decision_result.reason,
            }

            job_id = _find_job_for_email(analysis.get("company_name", ""))
            email_db_id = tracker.save_email({
                **email,
                "job_id": job_id,
                "sentiment": analysis.get("sentiment", "neutral"),
                "action_taken": decision_result.decision.value,
            })
            gmail_tool.mark_as_read(email["message_id"])

            # ── Actuar según la decisión ──────────────────────────────────────
            Decision = response_decision_agent.ResponseDecision

            if decision_result.decision == Decision.SKIP:
                tracker.set_email_responded_by(email_db_id, "skipped")
                continue

            elif decision_result.decision == Decision.ESCALATE:
                tracker.set_email_responded_by(email_db_id, "pending")
                msg = decision_result.escalation_msg or (
                    f"📧 *Email de {from_addr}*\n"
                    f"Asunto: {subject}\n"
                    f"Motivo: {decision_result.reason}\n"
                    f"Extracto: {content[:250]}"
                )
                whatsapp_tool.send_message(msg)
                continue

            elif decision_result.decision == Decision.ASK_USER:
                tracker.set_email_responded_by(email_db_id, "pending")
                whatsapp_tool.send_message(
                    decision_result.user_question or (
                        f"📧 *{from_addr}* — necesito tu input:\n{content[:400]}"
                    )
                )
                continue

            # ── AUTO_RESPOND ──────────────────────────────────────────────────
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
                tracker.set_email_responded_by(email_db_id, "skipped")

            elif action == "schedule_interview":
                _handle_interview_scheduling(analysis, job_id, email_db_id, resume)
                tracker.set_email_responded_by(email_db_id, "auto")

            elif action in ("send_followup", "none") and decision_result.draft_response:
                reply = decision_result.draft_response or analysis.get("suggested_reply", "")

                if auto_replies_sent >= MAX_AUTO_REPLIES_PER_CYCLE:
                    logger.info(f"[email-antispam] Límite {MAX_AUTO_REPLIES_PER_CYCLE} replies/ciclo alcanzado")
                    tracker.set_email_responded_by(email_db_id, "pending")
                    break

                if reply and from_addr:
                    if AUTO_EMAIL_DISABLED:
                        logger.info(f"[AUTO_EMAIL_DISABLED] No enviando a {from_addr}")
                        whatsapp_tool.send_message(
                            f"📧 *Borrador listo* para {from_addr}\n"
                            f"Asunto: {subject}\n\n{reply[:300]}\n\n"
                            f"Envío en pausa. ¿Apruebas? (si/no)"
                        )
                        tracker.set_email_responded_by(email_db_id, "pending")
                    else:
                        sent = gmail_tool.send_email(
                            to=from_addr,
                            subject=f"Re: {subject}",
                            body=reply,
                            thread_id=thread_id,
                        )
                        if sent:
                            tracker.mark_followup_sent(email_db_id)
                            tracker.set_email_responded_by(email_db_id, "auto")
                            auto_replies_sent += 1

            else:
                tracker.set_email_responded_by(email_db_id, "skipped")
                if analysis.get("sentiment") in ("positive", "interview") and job_id:
                    job = tracker.get_job(job_id)
                    whatsapp_tool.send_email_alert(
                        job_title=job["title"] if job else "",
                        company=analysis.get("company_name", ""),
                        sentiment=analysis["sentiment"],
                        summary=analysis.get("summary", ""),
                    )

        logger.success(f"Emails procesados: {len(new_emails)}, auto-replies: {auto_replies_sent}")

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
        replies_sent_this_run = 0
        MAX_REPLIES_PER_RUN = 5  # anti-spam: máximo 5 respuestas por ciclo de 5 min

        for conv in unique_convs:
            conv_id     = conv["conversation_id"]
            sender_name = conv.get("sender_name", "Reclutador")
            sender_title = conv.get("sender_title", "")

            # 1. Guardar/actualizar conversación en DB
            tracker.save_linkedin_conversation({
                "conversation_id": conv_id,
                "participant_name": sender_name,
                "participant_profile_id": conv.get("sender_profile_id", ""),
                "participant_title": sender_title,
                "profile_url": conv.get("profile_url", ""),
                "last_message_at": conv.get("last_activity", 0),
            })

            # 2. Obtener mensajes completos y guardarlos en DB
            full_msgs = await asyncio.to_thread(
                linkedin_messages_tool.get_full_conversation, conv_id, sender_name
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
                continue  # sin mensajes nuevos

            # Saltar si ya hay respuesta pendiente en WhatsApp
            if conv_id in pending_recruiter_replies or conv_id in pending_slot_selection:
                continue

            if not latest_recruiter_msg or len(latest_recruiter_msg.strip()) < 5:
                latest_recruiter_msg = conv.get("message", "")
                if not latest_recruiter_msg or len(latest_recruiter_msg.strip()) < 5:
                    continue

            # 3. Historial de DB para contexto
            db_history = tracker.get_conversation_history(conv_id)
            history_for_llm = [
                {"body": m["message_text"], "from_me": bool(m["from_me"])}
                for m in db_history
            ]

            # 4. Determinar si el último mensaje es nuestro
            last_msg = db_history[-1] if db_history else {}
            last_msg_is_ours = bool(last_msg.get("from_me"))

            # ── RESPONSE DECISION AGENT (ÚLTIMA PALABRA) ─────────────────────
            decision_result = await asyncio.to_thread(
                response_decision_agent.decide_and_log,
                sender_name=sender_name,
                message_body=latest_recruiter_msg,
                subject_or_title=sender_title,
                thread_id_or_conv_id=conv_id,
                last_message_is_ours=last_msg_is_ours,
                conversation_history=history_for_llm,
                source="linkedin",
            )

            Decision = response_decision_agent.ResponseDecision
            new_activity += 1

            if decision_result.decision == Decision.SKIP:
                last_incoming_id = tracker.get_last_incoming_linkedin_message_id(conv_id)
                if last_incoming_id:
                    tracker.set_linkedin_message_responded_by(last_incoming_id, "skipped")
                tracker.mark_messages_processed(conv_id)
                continue

            elif decision_result.decision == Decision.ESCALATE:
                last_incoming_id = tracker.get_last_incoming_linkedin_message_id(conv_id)
                if last_incoming_id:
                    tracker.set_linkedin_message_responded_by(last_incoming_id, "pending")
                msg = decision_result.escalation_msg or (
                    f"💬 *{sender_name}* (LinkedIn)\n"
                    f"Motivo: {decision_result.reason}\n"
                    f"Mensaje: {latest_recruiter_msg[:300]}"
                )
                whatsapp_tool.send_message(msg)
                tracker.update_conversation_state(conv_id, "escalated", decision_result.reason[:80])
                tracker.mark_messages_processed(conv_id)
                continue

            elif decision_result.decision == Decision.ASK_USER:
                last_incoming_id = tracker.get_last_incoming_linkedin_message_id(conv_id)
                if last_incoming_id:
                    tracker.set_linkedin_message_responded_by(last_incoming_id, "pending")
                pending_recruiter_replies[conv_id] = {
                    "analysis": decision_result.llm_analysis,
                    "sender_name": sender_name,
                    "sender_title": sender_title,
                    "original_message": latest_recruiter_msg,
                }
                whatsapp_tool.send_message(
                    decision_result.user_question or (
                        f"💬 *{sender_name}* (LinkedIn) — necesito tu input:\n{latest_recruiter_msg[:400]}"
                    )
                )
                tracker.update_conversation_state(conv_id, "escalated", "ask_user")
                tracker.mark_messages_processed(conv_id)
                continue

            # ── AUTO_RESPOND — usar draft del agente o recruiter_agent ────────
            draft = decision_result.draft_response or ""

            # Para scheduling/ofertas complejas, usar recruiter_agent completo
            if not draft:
                free_slots = await asyncio.to_thread(calendar_tool.get_free_slots, 7, 60)
                analysis = await asyncio.to_thread(
                    recruiter_agent.analyze_recruiter_message,
                    latest_recruiter_msg, sender_name, sender_title,
                    history_for_llm, free_slots,
                )
                intent = analysis.get("intent", "general")

                if intent == "rejection":
                    whatsapp_tool.send_message(
                        f"❌ *{sender_name}*: {analysis.get('summary', 'Posición cerrada')}"
                    )
                    tracker.update_conversation_state(conv_id, "closed", "rejection")
                    tracker.mark_messages_processed(conv_id)
                    continue

                if intent == "schedule" and free_slots:
                    pending_slot_selection[conv_id] = {
                        "slots": free_slots, "analysis": analysis,
                        "sender_name": sender_name, "sender_title": sender_title,
                        "original_message": latest_recruiter_msg,
                    }
                    slots_text = "\n".join(
                        f"  *{i+1}.* {s['label']}" for i, s in enumerate(free_slots[:5])
                    )
                    whatsapp_tool.send_message(
                        f"📅 *{sender_name}* quiere agendar entrevista:\n"
                        f'"{latest_recruiter_msg[:200]}"\n\n'
                        f"Slots disponibles:\n{slots_text}\n\n"
                        f"¿Cuál prefieres? Responde *1*, *2* o *3*"
                    )
                    tracker.update_conversation_state(conv_id, "escalated", "schedule")
                    tracker.mark_messages_processed(conv_id)
                    continue

                draft = analysis.get("draft_response", "")

            if draft:
                if AUTO_LINKEDIN_REPLY_DISABLED:
                    logger.info(f"[AUTO_LINKEDIN_DISABLED] Draft para {sender_name}: {draft[:60]}...")
                    tracker.mark_messages_processed(conv_id)
                    continue
                if replies_sent_this_run >= MAX_REPLIES_PER_RUN:
                    logger.info(f"[anti-spam] Límite {MAX_REPLIES_PER_RUN}/ciclo, {sender_name} pospuesto")
                    continue
                sent = await asyncio.to_thread(
                    linkedin_messages_tool.send_message, conv_id, draft, sender_name
                )
                if sent:
                    tracker.record_our_reply(conv_id, draft)
                    last_incoming_id = tracker.get_last_incoming_linkedin_message_id(conv_id)
                    if last_incoming_id:
                        tracker.set_linkedin_message_responded_by(last_incoming_id, "auto")
                    replies_sent_this_run += 1
                    logger.success(f"[auto-reply] {sender_name}: {draft[:60]}... ({replies_sent_this_run}/{MAX_REPLIES_PER_RUN})")
                    await asyncio.sleep(5)
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
    """Verifica si las cookies de LinkedIn siguen válidas y notifica si no."""
    logger.info("Verificando cookies de LinkedIn...")
    try:
        from src.tools import whatsapp_tool
        from src.tools.linkedin_messages_tool import _build_session, _test_session

        session = _build_session()
        valid = await asyncio.to_thread(_test_session, session)

        if valid:
            logger.success("Cookies de LinkedIn OK")
        else:
            logger.warning("Cookies de LinkedIn EXPIRADAS — notificando a Alejandro")
            whatsapp_tool.send_message(
                "⚠️ *LinkedIn cookies expiradas*\n\n"
                "Las cookies de LinkedIn dejaron de funcionar.\n"
                "Por favor actualiza `li_at` y `JSESSIONID` usando EditThisCookie en tu browser.\n\n"
                "Ve a linkedin.com → EditThisCookie → copia li_at y JSESSIONID → pégalos aquí."
            )
    except Exception as e:
        logger.error(f"Error verificando cookies LinkedIn: {e}")


async def followup_task():
    """Envía follow-up emails a aplicaciones sin respuesta."""
    logger.info("Revisando aplicaciones para follow-up...")

    try:
        resume = _load_resume()
        pending = tracker.get_applications_pending_followup()
        followups_sent = 0
        MAX_FOLLOWUPS_PER_CYCLE = 2  # anti-spam: máximo 2 follow-ups por día

        for app in pending:
            if followups_sent >= MAX_FOLLOWUPS_PER_CYCLE:
                logger.info(f"[followup-antispam] Límite {MAX_FOLLOWUPS_PER_CYCLE} follow-ups/día alcanzado")
                break

            # Anti-spam: no enviar si el remitente está en blocklist
            job_emails = app.get("emails_in_job", "")
            if not job_emails or "@" not in str(job_emails):
                logger.warning(f"No hay email para follow-up de {app['title']} @ {app['company']}")
                continue

            to_email = str(job_emails).split(",")[0].strip()
            if _is_blocked_sender(to_email):
                logger.info(f"[followup-blocklist] Ignorando follow-up a {to_email}")
                continue

            days_since = int(app.get("days_since_apply", settings.followup_days))
            followup = master_agent.generate_followup_email(app, resume, days_since)

            if AUTO_EMAIL_DISABLED:
                logger.info(f"[AUTO_EMAIL_DISABLED] No enviando follow-up a {to_email} — revisar manualmente")
                whatsapp_tool.send_message(
                    f"📧 Follow-up listo para *{app['company']}* ({app['title']}) — envío manual requerido."
                )
                continue

            sent = gmail_tool.send_email(
                to=to_email,
                subject=followup["subject"],
                body=followup["body"],
            )

            if sent:
                followups_sent += 1
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


# --- STALKER TASKS ---

# 30 empresas divididas en 6 grupos de 5, cada grupo corre cada 2h escalonados
STALKER_GROUPS = {
    "A": ["Thomson Reuters", "Globant", "EPAM", "Nubank", "Mercado Libre"],
    "B": ["Uber", "Stripe", "Twilio", "GitHub", "NVIDIA"],
    "C": ["Endava", "Wizeline", "Bitso", "Clip", "Rappi"],
    "D": ["Citi", "Deutsche Bank", "BlackRock", "Plaid", "HSBC"],
    "E": ["Samsara", "Roku", "Thoughtworks", "Capgemini", "Cognizant"],
    "F": ["Konfio", "Kueski", "Conekta", "Kavak", "Allstate"],
}


async def stalker_group_task(group_name: str):
    """Stalkea un grupo de empresas."""
    companies = STALKER_GROUPS.get(group_name, [])
    if not companies:
        return
    logger.info(f"[STALKER] Ejecutando grupo {group_name}: {companies}")
    try:
        from src.agents import company_stalker_agent
        results = await asyncio.to_thread(
            company_stalker_agent.stalk_multiple, companies
        )
        total_matched = sum(r.get("matched", 0) for r in results)
        total_applied = sum(r.get("applied", 0) for r in results)
        if total_matched > 0:
            logger.success(
                f"[STALKER] Grupo {group_name}: {total_matched} matches, {total_applied} aplicadas"
            )
    except Exception as e:
        logger.error(f"[STALKER] Error en grupo {group_name}: {e}")


async def thomson_reuters_stalker_task():
    """Stalker dedicado a Thomson Reuters — corre cada hora."""
    logger.info("[TR-STALKER] Ejecutando búsqueda dedicada...")
    try:
        from src.agents import thomson_reuters_stalker
        result = await asyncio.to_thread(thomson_reuters_stalker.stalk)
        matched = result.get("matched", 0)
        total = result.get("total_found", 0)
        logger.info(f"[TR-STALKER] Resultado: {total} encontradas, {matched} match")
    except Exception as e:
        logger.error(f"[TR-STALKER] Error: {e}")


# Funciones individuales para el scheduler (necesita callable sin args)
async def stalker_group_A(): await stalker_group_task("A")
async def stalker_group_B(): await stalker_group_task("B")
async def stalker_group_C(): await stalker_group_task("C")
async def stalker_group_D(): await stalker_group_task("D")
async def stalker_group_E(): await stalker_group_task("E")
async def stalker_group_F(): await stalker_group_task("F")


# --- FASTAPI APP ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Iniciando orchestrator...")

    # ── SCHEDULED TASKS (updated 2026-04-02) ────────────────────────────────
    # DESACTIVADOS (respuestas automáticas pausadas):
    # scheduler.add_job(email_monitor_task, "interval", hours=6, id="email_monitor")
    # scheduler.add_job(followup_task, "cron", hour=9, minute=0, id="followup")
    # scheduler.add_job(linkedin_messages_task, "interval", minutes=5, id="linkedin_messages")

    # ── ACTIVOS ───────────────────────────────────────────────────────────

    # Búsqueda de empleos: cada 3 horas
    scheduler.add_job(job_search_task, "interval", hours=3, id="job_search")

    # Búsqueda premium (score >= 82%): cada 3 horas, offset 90min vs job_search
    scheduler.add_job(premium_job_search_task, "interval", hours=3, start_date="2026-04-02 01:30:00", id="premium_job_search")

    # LinkedIn content: 3 posts diarios L-V (8am, 1pm, 5pm)
    scheduler.add_job(linkedin_content_task, "cron", hour=8, minute=0, day_of_week="mon-fri", id="linkedin_content_morning")
    scheduler.add_job(linkedin_content_task, "cron", hour=13, minute=0, day_of_week="mon-fri", id="linkedin_content_noon")
    scheduler.add_job(linkedin_content_task, "cron", hour=17, minute=0, day_of_week="mon-fri", id="linkedin_content_evening")

    # DESACTIVADO: LinkedIn bloquea búsqueda de personas desde servidor (API + Playwright)
    # scheduler.add_job(linkedin_hr_expansion_task, "cron", hour=15, minute=0, day_of_week="mon-fri", id="linkedin_hr_expansion")

    # Inspección de infografías: L-V 9:30, 14:00, 18:00
    scheduler.add_job(image_inspection_task, "cron", hour="9,14,18", minute=30, day_of_week="mon-fri", id="image_inspection")

    # Limpieza de imágenes huérfanas: domingos 3am
    scheduler.add_job(image_cleanup_task, "cron", hour=3, minute=0, day_of_week="sun", id="image_cleanup")

    # Renovar cookies LinkedIn: cada 12h
    scheduler.add_job(linkedin_cookie_refresh_task, "interval", hours=12, id="linkedin_cookie_refresh")

    # ── THOMSON REUTERS STALKER DEDICADO: cada hora ────────────────────
    scheduler.add_job(thomson_reuters_stalker_task, "interval", hours=1, id="tr_stalker")

    # ── STALKER JOBS: 6 grupos, cada 2h, escalonados 20min ──────────────
    # Grupo A (TR, Globant, EPAM, Nubank, MeLi): minuto 0
    scheduler.add_job(stalker_group_A, "interval", hours=2, start_date="2026-04-06 19:00:00", id="stalker_A")
    # Grupo B (Uber, Stripe, Twilio, GitHub, NVIDIA): minuto 20
    scheduler.add_job(stalker_group_B, "interval", hours=2, start_date="2026-04-06 19:20:00", id="stalker_B")
    # Grupo C (Endava, Wizeline, Bitso, Clip, Rappi): minuto 40
    scheduler.add_job(stalker_group_C, "interval", hours=2, start_date="2026-04-06 19:40:00", id="stalker_C")
    # Grupo D (Capital One, Citi, DB, BlackRock, Plaid): minuto 0 +1h
    scheduler.add_job(stalker_group_D, "interval", hours=2, start_date="2026-04-06 20:00:00", id="stalker_D")
    # Grupo E (Samsara, Roku, Thoughtworks, Capgemini, Cognizant): minuto 20 +1h
    scheduler.add_job(stalker_group_E, "interval", hours=2, start_date="2026-04-06 20:20:00", id="stalker_E")
    # Grupo F (Konfio, Kueski, Conekta, Kavak, Allstate): minuto 40 +1h
    scheduler.add_job(stalker_group_F, "interval", hours=2, start_date="2026-04-06 20:40:00", id="stalker_F")

    scheduler.start()
    logger.success("Scheduler iniciado (13 tasks activas: 7 originales + 6 stalker groups)")

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
async def get_jobs_api(status: str = "all", limit: int = 500, min_score: int = 0, search: str = ""):
    """Lista de jobs filtrada con búsqueda y score mínimo."""
    if status == "all":
        jobs = tracker.get_all_jobs(limit=limit)
    else:
        jobs = tracker.get_jobs_by_status(status)
    if min_score > 0:
        jobs = [j for j in jobs if (j.get("match_score") or 0) >= min_score]
    if search:
        q = search.lower()
        jobs = [j for j in jobs if q in (j.get("title") or "").lower() or q in (j.get("company") or "").lower()]
    return jobs


@app.get("/api/applications")
async def get_applications_api(limit: int = 100):
    """Lista de aplicaciones con pipeline stage."""
    return tracker.get_full_pipeline(limit=limit)


@app.get("/api/applications/failed")
async def get_failed_applications_api():
    """Aplicaciones que fallaron y necesitan atención."""
    return tracker.get_failed_applications()


@app.get("/api/applications/stats")
async def get_application_stats_api():
    """Estadísticas de aplicaciones por status."""
    return tracker.get_application_stats()


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


@app.post("/trigger/tr-stalker")
async def trigger_tr_stalker():
    """Trigger manual: stalker dedicado de Thomson Reuters."""
    scheduler.add_job(thomson_reuters_stalker_task, "date", id="manual_tr_stalker", replace_existing=True)
    return {"ok": True, "message": "Thomson Reuters stalker ejecutando búsqueda exhaustiva"}


@app.get("/tr-stalker/stats")
async def get_tr_stalker_stats():
    """Retorna estadísticas del stalker de Thomson Reuters."""
    try:
        from src.agents import thomson_reuters_stalker
        return thomson_reuters_stalker.get_stats()
    except Exception as e:
        return {"error": str(e)}


@app.get("/tr-stalker/jobs")
async def get_tr_stalker_jobs():
    """Retorna todas las vacantes conocidas de Thomson Reuters."""
    try:
        from src.agents import thomson_reuters_stalker
        return {"jobs": thomson_reuters_stalker.get_all_known_jobs()}
    except Exception as e:
        return {"error": str(e)}


@app.post("/trigger/stalker")
async def trigger_stalker(group: str = "A"):
    """Trigger manual: ejecutar stalker para un grupo (A-F) o 'all'."""
    if group == "all":
        for g in ["A", "B", "C", "D", "E", "F"]:
            scheduler.add_job(stalker_group_task, "date", args=[g], id=f"manual_stalker_{g}", replace_existing=True)
        return {"ok": True, "message": "Stalker ejecutando todos los grupos"}
    if group in STALKER_GROUPS:
        scheduler.add_job(stalker_group_task, "date", args=[group], id=f"manual_stalker_{group}", replace_existing=True)
        return {"ok": True, "message": f"Stalker grupo {group} en proceso: {STALKER_GROUPS[group]}"}
    return {"ok": False, "message": f"Grupo inválido: {group}. Usa A-F o 'all'"}


@app.get("/stalker/stats")
async def get_stalker_stats():
    """Retorna estadísticas del stalker."""
    try:
        from src.agents import company_stalker_agent
        return company_stalker_agent.get_stalker_stats()
    except Exception as e:
        return {"error": str(e)}


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
