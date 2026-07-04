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
from fastapi.middleware.cors import CORSMiddleware
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
from src.tools import linkedin_governor as gov
from src.agents import image_inspector_agent
from src.agents import job_discovery_agent

tracker = JobTracker()
scheduler = AsyncIOScheduler()

# --- SAFETY SWITCHES ---
# Deshabilitar envío automático de emails para evitar spam.
AUTO_EMAIL_DISABLED = True
# Deshabilitar respuestas automáticas de LinkedIn.
AUTO_LINKEDIN_REPLY_DISABLED = True

# Contactos NUNCA tocar — el agente NUNCA envía mensajes ni emails a estas personas.
BLOCKED_CONTACTS_NEVER_REPLY: set[str] = {
    "Sam Lewis",  # ex-jefa de Alejandro — responder manualmente
    "Melba Ruiz",  # Thomson Reuters — manejo personal de reingreso
    "Melba Ruiz Moron",  # variante de nombre
}

# ---------------------------------------------------------------------------
# Estado pendiente de aprobación — PERSISTIDO EN SQLITE (sobrevive crashes)
# Los dicts en memoria son una *vista* del DB; se recargan al arrancar.
# ---------------------------------------------------------------------------

def _load_pending_state():
    """Carga las 3 categorías de decisiones pendientes desde SQLite al arrancar."""
    global pending_confirmations, pending_recruiter_replies, pending_slot_selection
    for row in tracker.get_pending_decisions():
        pk = row["id"]
        payload = row["payload"]
        dtype = row["decision_type"]
        if dtype == "job_confirm":
            pending_confirmations[pk] = payload
        elif dtype == "recruiter_reply":
            pending_recruiter_replies[pk] = payload
        elif dtype == "slot_selection":
            pending_slot_selection[pk] = payload
    logger.info(
        f"[state] Cargado del DB — confirmaciones={len(pending_confirmations)} "
        f"recruiter={len(pending_recruiter_replies)} slots={len(pending_slot_selection)}"
    )


def _add_pending_confirmation(job_id: str, payload: dict):
    pending_confirmations[job_id] = payload
    tracker.save_pending_decision(job_id, "job_confirm", payload)


def _remove_pending_confirmation(job_id: str):
    pending_confirmations.pop(job_id, None)
    tracker.delete_pending_decision(job_id)


def _add_pending_recruiter_reply(conv_id: str, payload: dict):
    pending_recruiter_replies[conv_id] = payload
    tracker.save_pending_decision(conv_id, "recruiter_reply", payload)


def _remove_pending_recruiter_reply(conv_id: str):
    pending_recruiter_replies.pop(conv_id, None)
    tracker.delete_pending_decision(conv_id)


def _add_pending_slot_selection(conv_id: str, payload: dict):
    pending_slot_selection[conv_id] = payload
    tracker.save_pending_decision(conv_id, "slot_selection", payload)


def _remove_pending_slot_selection(conv_id: str):
    pending_slot_selection.pop(conv_id, None)
    tracker.delete_pending_decision(conv_id)


# Vistas en memoria (se inicializan vacías; _load_pending_state() las rellena en startup)
pending_confirmations: Dict[str, Dict] = {}
pending_recruiter_replies: Dict[str, Dict] = {}
pending_slot_selection: Dict[str, Dict] = {}


# --- TAREAS SCHEDULED ---


async def job_search_task():
    """Busca nuevos trabajos y notifica al usuario sobre los mejores matches."""
    # (El presupuesto SEARCH de LinkedIn se aplica dentro de jobspy_tool, en la
    #  fuente, para cubrir también stalkers y scripts sin doble-contar.)
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
                        logger.debug(
                            f"Omitiendo job fuera de México/remote: {job['location']} - {job['title']}"
                        )
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
                        # Guardar en pending_confirmations (persistido en SQLite)
                        _add_pending_confirmation(job["id"], {
                            "job": job,
                            "score": score,
                            "reason": reason,
                        })

                        # Notificar al usuario
                        whatsapp_tool.send_job_notification(job, score)
                        notified += 1
                        logger.info(
                            f"Notificado job: {job['title']} @ {job['company']} ({score}%)"
                        )

        logger.success(
            f"Búsqueda completada: {new_jobs_found} nuevos, {notified} notificados"
        )

    except Exception as e:
        logger.error(f"Error en job_search_task: {e}")
        whatsapp_tool.send_message(f"Error en búsqueda automática: {e}")


async def search_and_apply_task():
    """
    [DESACTIVADO - Reemplazado por queue_task]

    Tarea anterior: busca nuevos jobs cada hora y aplica automáticamente
    a los que tengan score >= threshold sin esperar aprobación manual.

    Ahora: Esta tarea está desactivada. El Job Queue Manager (queue_task)
    es responsable de aplicar jobs con priorización global y rate limiting.
    """
    logger.info("[search_apply] ===== TAREA DESACTIVADA =====")
    logger.info("[search_apply] Usando Job Queue Manager en su lugar")
    return {"status": "disabled", "reason": "Reemplazado por queue_task"}


async def queue_task():
    """
    Application Agent cycle — único ejecutor de aplicaciones.

    Lee cola priorizada de BD (status='found', score>=75, <14d), aplica 1 job
    por ciclo vía linkedin_moderate_agent con delays 15-45s random.
    Cap diario: 35 apps. Pausa fuera de 7am-9pm CDMX. Auto-recovery si detecta ban.

    Scheduler debe usar max_instances=1 y coalesce=True para evitar overlaps.
    """
    logger.info("[queue] ===== application_cycle =====")
    try:
        from src.agents import application_agent

        result = await application_agent.run_application_cycle()
        logger.info(f"[queue] resultado: {result}")

        # Solo notificar eventos relevantes (no cada 2min si no pasó nada)
        if result.get("ban_detected"):
            # El propio application_agent ya notificó el ban por WA
            pass
        elif result.get("applied", 0) > 0:
            applied = result["applied"]
            whatsapp_tool.send_message(
                f"✅ Aplicación enviada ({applied}). "
                f"Queue status: attempted={result['attempted']} failed={result['failed']} "
                f"manual={result['manual_queued']}"
            )
        elif result.get("manual_queued", 0) > 0:
            logger.info(f"[queue] {result['manual_queued']} job(s) escalados a manual")

        return result

    except Exception as e:
        logger.exception(f"[queue] Error en application_cycle: {e}")
        return {"attempted": 0, "applied": 0, "failed": 0, "error": str(e)}


EMAIL_BLOCKLIST = {
    "padma@ptechpartners.com",
}
EMAIL_BLOCKLIST_DOMAINS = {
    "noreply",
    "no-reply",
    "notifications",
    "mailer",
    "bounce",
    "donotreply",
    "do-not-reply",
    "updates@e.mission",
    "ccsend.com",
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
            thread_id = email.get("thread_id", "")
            content = email.get("content", "")
            subject = email.get("subject", "")

            # ── Paso 1: Response Decision Agent (ÚLTIMA PALABRA) ─────────────
            # Cargar hilo completo (recibidos + enviados) para contexto del agente
            thread_history = (
                tracker.get_email_thread_history(thread_id) if thread_id else []
            )
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
            analysis = (
                await asyncio.to_thread(
                    master_agent.analyze_email_response,
                    content,
                    subject,
                    from_addr,
                )
                if decision_result.decision
                == response_decision_agent.ResponseDecision.AUTO_RESPOND
                else {
                    "sentiment": "neutral",
                    "action": "none",
                    "company_name": "",
                    "summary": decision_result.reason,
                }
            )

            job_id = _find_job_for_email(analysis.get("company_name", ""))
            email_db_id = tracker.save_email(
                {
                    **email,
                    "job_id": job_id,
                    "sentiment": analysis.get("sentiment", "neutral"),
                    "action_taken": decision_result.decision.value,
                }
            )
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
                    decision_result.user_question
                    or (f"📧 *{from_addr}* — necesito tu input:\n{content[:400]}")
                )
                continue

            # ── AUTO_RESPOND ──────────────────────────────────────────────────
            action = analysis.get("action", "none")

            if action == "update_rejected":
                if job_id:
                    tracker.update_job_status(job_id, "rejected")
                    job = tracker.get_job(job_id)
                    whatsapp_tool.send_email_alert(
                        job_title=job["title"]
                        if job
                        else analysis.get("job_title_hint", ""),
                        company=analysis["company_name"],
                        sentiment="negative",
                        summary=analysis["summary"],
                    )
                tracker.set_email_responded_by(email_db_id, "skipped")

            elif action == "schedule_interview":
                _handle_interview_scheduling(analysis, job_id, email_db_id, resume)
                tracker.set_email_responded_by(email_db_id, "auto")

            elif action in ("send_followup", "none") and decision_result.draft_response:
                reply = decision_result.draft_response or analysis.get(
                    "suggested_reply", ""
                )

                if auto_replies_sent >= MAX_AUTO_REPLIES_PER_CYCLE:
                    logger.info(
                        f"[email-antispam] Límite {MAX_AUTO_REPLIES_PER_CYCLE} replies/ciclo alcanzado"
                    )
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

        logger.success(
            f"Emails procesados: {len(new_emails)}, auto-replies: {auto_replies_sent}"
        )

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
    # Governor: leer mensajes abre Playwright sobre linkedin.com (huella alta).
    # Se limita a gap ~75min / 12 lecturas/día aunque el scheduler dispare antes.
    ok, reason = gov.can_act(gov.MSG_READ)
    if not ok:
        logger.debug(f"[gov] skip linkedin_messages: {reason}")
        return

    logger.info("Revisando mensajes de LinkedIn...")

    try:
        gov.record_action(gov.MSG_READ)
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
            conv_id = conv["conversation_id"]
            sender_name = conv.get("sender_name", "Reclutador")
            sender_title = conv.get("sender_title", "")

            # 1. Guardar/actualizar conversación en DB
            tracker.save_linkedin_conversation(
                {
                    "conversation_id": conv_id,
                    "participant_name": sender_name,
                    "participant_profile_id": conv.get("sender_profile_id", ""),
                    "participant_title": sender_title,
                    "profile_url": conv.get("profile_url", ""),
                    "last_message_at": conv.get("last_activity", 0),
                }
            )

            # 2. Obtener mensajes completos y guardarlos en DB
            full_msgs = await asyncio.to_thread(
                linkedin_messages_tool.get_full_conversation, conv_id, sender_name
            )
            new_msgs = 0
            latest_recruiter_msg = ""
            for msg in full_msgs:
                msg_id = tracker.save_linkedin_message(
                    {
                        "conversation_id": conv_id,
                        "message_text": msg.get("body", ""),
                        "from_me": msg.get("from_me", False),
                        "linkedin_timestamp": msg.get("deliveredAt", 0),
                    }
                )
                if msg_id is not None:
                    new_msgs += 1
                if not msg.get("from_me") and msg.get("body"):
                    latest_recruiter_msg = msg["body"]

            if new_msgs == 0:
                continue  # sin mensajes nuevos

            # Saltar si ya hay respuesta pendiente en WhatsApp
            if (
                conv_id in pending_recruiter_replies
                or conv_id in pending_slot_selection
            ):
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
                last_incoming_id = tracker.get_last_incoming_linkedin_message_id(
                    conv_id
                )
                if last_incoming_id:
                    tracker.set_linkedin_message_responded_by(
                        last_incoming_id, "skipped"
                    )
                tracker.mark_messages_processed(conv_id)
                continue

            elif decision_result.decision == Decision.ESCALATE:
                last_incoming_id = tracker.get_last_incoming_linkedin_message_id(
                    conv_id
                )
                if last_incoming_id:
                    tracker.set_linkedin_message_responded_by(
                        last_incoming_id, "pending"
                    )
                msg = decision_result.escalation_msg or (
                    f"💬 *{sender_name}* (LinkedIn)\n"
                    f"Motivo: {decision_result.reason}\n"
                    f"Mensaje: {latest_recruiter_msg[:300]}"
                )
                whatsapp_tool.send_message(msg)
                tracker.update_conversation_state(
                    conv_id, "escalated", decision_result.reason[:80]
                )
                tracker.mark_messages_processed(conv_id)
                continue

            elif decision_result.decision == Decision.ASK_USER:
                last_incoming_id = tracker.get_last_incoming_linkedin_message_id(
                    conv_id
                )
                if last_incoming_id:
                    tracker.set_linkedin_message_responded_by(
                        last_incoming_id, "pending"
                    )
                _add_pending_recruiter_reply(conv_id, {
                    "analysis": decision_result.llm_analysis,
                    "sender_name": sender_name,
                    "sender_title": sender_title,
                    "original_message": latest_recruiter_msg,
                })
                whatsapp_tool.send_message(
                    decision_result.user_question
                    or (
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
                free_slots = await asyncio.to_thread(
                    calendar_tool.get_free_slots, 7, 60
                )
                analysis = await asyncio.to_thread(
                    recruiter_agent.analyze_recruiter_message,
                    latest_recruiter_msg,
                    sender_name,
                    sender_title,
                    history_for_llm,
                    free_slots,
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
                    _add_pending_slot_selection(conv_id, {
                        "slots": free_slots,
                        "analysis": analysis,
                        "sender_name": sender_name,
                        "sender_title": sender_title,
                        "original_message": latest_recruiter_msg,
                    })
                    slots_text = "\n".join(
                        f"  *{i + 1}.* {s['label']}"
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
                    continue

                draft = analysis.get("draft_response", "")

            if draft:
                if AUTO_LINKEDIN_REPLY_DISABLED:
                    logger.info(
                        f"[AUTO_LINKEDIN_DISABLED] Draft para {sender_name}: {draft[:60]}..."
                    )
                    tracker.mark_messages_processed(conv_id)
                    continue
                if replies_sent_this_run >= MAX_REPLIES_PER_RUN:
                    logger.info(
                        f"[anti-spam] Límite {MAX_REPLIES_PER_RUN}/ciclo, {sender_name} pospuesto"
                    )
                    continue
                sent = await asyncio.to_thread(
                    linkedin_messages_tool.send_message, conv_id, draft, sender_name
                )
                if sent:
                    tracker.record_our_reply(conv_id, draft)
                    last_incoming_id = tracker.get_last_incoming_linkedin_message_id(
                        conv_id
                    )
                    if last_incoming_id:
                        tracker.set_linkedin_message_responded_by(
                            last_incoming_id, "auto"
                        )
                    replies_sent_this_run += 1
                    logger.success(
                        f"[auto-reply] {sender_name}: {draft[:60]}... ({replies_sent_this_run}/{MAX_REPLIES_PER_RUN})"
                    )
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
    ok, reason = gov.can_act(gov.POST)
    if not ok:
        logger.debug(f"[gov] skip linkedin_content: {reason}")
        return
    logger.info("Ejecutando linkedin_content_task...")
    try:
        from src.agents import linkedin_content_agent

        success = linkedin_content_agent.create_and_publish_post()
        if success:
            gov.record_action(gov.POST)
        if success:
            logger.success("Post LinkedIn publicado exitosamente")
        else:
            logger.warning("No se pudo publicar el post LinkedIn")
    except Exception as e:
        logger.error(f"Error en linkedin_content_task: {e}")


async def linkedin_hr_expansion_task():
    """Busca y conecta con reclutadores en LinkedIn para ampliar la red de Alejandro."""
    ok, reason = gov.can_act(gov.CONNECT)
    if not ok:
        logger.debug(f"[gov] skip hr_expansion: {reason}")
        return
    logger.info("Ejecutando linkedin_hr_expansion_task...")
    try:
        from src.agents import linkedin_hr_agent

        result = linkedin_hr_agent.expand_hr_network(max_requests=5)
        sent = result.get("sent", 0)
        for _ in range(sent):
            gov.record_action(gov.CONNECT)
        if sent > 0:
            whatsapp_tool.send_message(
                f"🤝 Red LinkedIn ampliada: {sent} nuevas conexiones con reclutadores enviadas."
            )
        logger.info(f"HR expansion: {result}")
    except Exception as e:
        logger.error(f"Error en linkedin_hr_expansion_task: {e}")


async def top_companies_stalker_task():
    """Búsqueda activa cíclica en las 100 top companies."""
    logger.info("Ejecutando top_companies_stalker_task...")
    try:
        from src.agents import top_companies_stalker_agent
        result = await asyncio.to_thread(top_companies_stalker_agent.run_stalker_chunk, 5)
        logger.info(f"Top companies stalker completado. Próximo índice: {result.get('next_index')}")
    except Exception as e:
        logger.error(f"Error en top_companies_stalker_task: {e}")


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
                    location="Ciudad de Mexico",
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


async def job_discovery_task():
    """Búsqueda complementaria y desfasada - cada 3 horas."""
    # (Presupuesto SEARCH de LinkedIn aplicado dentro de jobspy_tool.)
    logger.info("Ejecutando job_discovery_task (búsqueda complementaria)...")
    try:
        from src.agents import job_discovery_agent

        # Ejecutar discovery en thread síncrono
        stats = await asyncio.to_thread(job_discovery_agent.discover_jobs)

        logger.success(f"Discovery completado: {stats['jobs_matched']} jobs con match")
        logger.success(f"Empresas únicas descubiertas: {stats['unique_companies']}")
        logger.success(f"High match (>=80%): {stats['high_match']}")
        logger.success(f"Medium match (70-79%): {stats['medium_match']}")
        logger.success(f"Duración: {stats['duration_seconds']:.1f}s")

        # Notificar por WhatsApp si hay buenos matches
        if stats["jobs_matched"] > 0:
            high_matches = stats.get("high_match", 0)
            if high_matches > 0:
                msg = f"🔍 Job Discovery encontró {stats['jobs_matched']} jobs con match\n"
                msg += f"• High match (>=80%): {high_matches}\n"
                msg += f"• Empresas únicas: {stats['unique_companies']}\n"
                msg += f"📊 Total searches: {stats['total_searches']}"
                whatsapp_tool.send_message(msg)

    except Exception as e:
        logger.error(f"Error en job_discovery_task: {e}")


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
    """Verifica si las cookies de LinkedIn siguen válidas. Si no, intenta renovarlas
    via login automático. Si el login falla (2FA), notifica a Alejandro."""
    logger.info("Verificando cookies de LinkedIn...")
    try:
        from src.tools import whatsapp_tool
        from src.tools.linkedin_auth import verify_session, login_and_save_cookies

        valid = await asyncio.to_thread(verify_session)

        if valid:
            logger.success("Cookies de LinkedIn OK")
            return

        logger.warning(
            "Cookies de LinkedIn EXPIRADAS — intentando renovar automáticamente..."
        )

        # Intentar login automático
        renewed = await asyncio.to_thread(login_and_save_cookies)

        if renewed:
            logger.success("Cookies de LinkedIn renovadas automáticamente via login")
            whatsapp_tool.send_message(
                "✅ *LinkedIn* — sesión renovada automáticamente"
            )
        else:
            logger.warning(
                "Login automático falló (probablemente 2FA) — notificando a Alejandro"
            )
            whatsapp_tool.send_message(
                "⚠️ *LinkedIn cookies expiradas*\n\n"
                "No pude renovarlas automáticamente (LinkedIn pidió verificación).\n\n"
                "Por favor ve a *linkedin.com* en tu browser, abre DevTools (F12) → "
                "Application → Cookies → copia estos valores:\n"
                "• `li_at`\n"
                "• `JSESSIONID`\n"
                "• `bcookie`\n\n"
                "Y pégalos aquí en el chat."
            )
    except Exception as e:
        logger.error(f"Error verificando/renovando cookies LinkedIn: {e}")


async def external_ats_task():
    """
    Aplica a jobs con URLs directas de Greenhouse/Lever/Ashby (sin LinkedIn).
    Sin riesgo de ban — todo el flujo es externo a LinkedIn.
    Cap: 10 apps/día, 3 por ciclo. Usa browser_tool (Playwright + Kimi visión).
    """
    from src.agents import external_ats_agent

    logger.info("[ext_ats] iniciando ciclo de aplicaciones externas...")
    try:
        stats = await external_ats_agent.run_external_apply_cycle()
        logger.info(
            f"[ext_ats] applied={stats['applied']} failed={stats['failed']} "
            f"manual={stats['manual_queued']} skip={stats.get('skipped_reason','')}"
        )
        if stats["applied"] > 0:
            lines = [
                f"✅ {j['title']} @ {j['company']} ({j['ats']})"
                for j in stats.get("jobs", []) if j.get("result") in ("applied", "external_submitted")
            ]
            whatsapp_tool.send_message(
                f"🤖 External ATS: {stats['applied']} aplicaciones enviadas\n" + "\n".join(lines)
            )
    except Exception as e:
        logger.error(f"[ext_ats] error: {e}")


async def linkedin_health_task():
    """Monitor de riesgo de baneo (cada ~2h): probe de sesión + risk_report.
    Escala ban SOLO ante restricción real (checkpoint/restricted); sesión muerta
    solo avisa para refrescar cookie. Cero provocación."""
    from src.tools import linkedin_health

    try:
        out = await asyncio.to_thread(
            linkedin_health.run_health_check, whatsapp_tool.send_message
        )
        p, r = out["probe"], out["risk"]
        logger.info(
            f"[li_health] sesión={p['status']} http={p['http']} | "
            f"riesgo={r['risk_score']}({r['band']}) writes={r['writes']} reads={r['reads']}"
        )
    except Exception as e:
        logger.error(f"[li_health] error: {e}")


async def linkedin_passive_task():
    """Actividad pasiva de COBERTURA: una lectura benigna gobernada (badge de
    notificaciones) para equilibrar la mezcla de acciones — que las escrituras no
    sean la única huella. Gobernada por gov.PASSIVE; se salta si no toca."""
    ok, reason = gov.can_act(gov.PASSIVE)
    if not ok:
        logger.debug(f"[li_passive] skip: {reason}")
        return
    try:
        from src.tools.linkedin_messages_tool import _build_session

        await asyncio.to_thread(gov.human_delay, gov.PASSIVE)
        s = await asyncio.to_thread(_build_session)
        # Endpoint benigno de solo-lectura (badge de notificaciones).
        resp = await asyncio.to_thread(
            lambda: s.get(
                "https://www.linkedin.com/voyager/api/voyagerNotificationsDashBadge",
                timeout=10,
            )
        )
        if resp.status_code == 200:
            gov.record_action(gov.PASSIVE, meta="notif_badge")
            logger.info("[li_passive] lectura de cobertura registrada")
        else:
            logger.debug(f"[li_passive] badge http={resp.status_code}")
    except Exception as e:
        logger.debug(f"[li_passive] error: {e}")


async def score_pending_task():
    """
    Eslabón scan→SCORE→apply del loop autónomo ATS.

    Evalúa con el LLM (GLM/coordinator) los jobs recién descubiertos por
    portal_scanner / discovery que aún NO tienen match_score (centinela=0), y
    persiste el score. Así el external_ats_agent puede aplicar automáticamente a
    los que superen el umbral (>=75) en su siguiente ciclo.

    CERO riesgo de ban: solo llama al LLM y actualiza SQLite — no toca LinkedIn.
    Prioriza fuentes ATS-api (Greenhouse/Ashby/Lever), que son las aplicables sin
    riesgo. Los jobs con score<75 quedan persistidos (no se re-evalúan); los que
    fallan la evaluación quedan en 0 y se reintentan al siguiente ciclo.
    """
    logger.info("[score] evaluando jobs sin score...")
    try:
        resume = _load_resume()
        if not resume:
            logger.warning("[score] sin resume.json — abort")
            return

        from src.db.tracker import JobTracker

        t = JobTracker()
        pending = t.get_unscored_jobs(limit=40)
        if not pending:
            logger.info("[score] no hay jobs pendientes de evaluar")
            return

        scored = qualified = errors = 0
        for job in pending:
            try:
                score, reason = await asyncio.to_thread(
                    master_agent.evaluate_job_match, job, resume
                )
            except Exception as e:
                errors += 1
                logger.warning(f"[score] fallo evaluando '{job.get('title','')}': {e}")
                continue

            if score <= 0:
                # Error/transitorio del LLM: dejamos match_score=0 → reintento
                errors += 1
                continue

            t.update_job_score(job["id"], score)
            scored += 1
            if score >= settings.job_match_threshold:
                qualified += 1
                logger.success(
                    f"[score] ✅ {score} {job['title']} @ {job['company']} "
                    f"({job['source']}) — {reason[:80]}"
                )

        logger.info(
            f"[score] evaluados={scored} calificados(>={settings.job_match_threshold})="
            f"{qualified} errores={errors} de {len(pending)}"
        )
        if qualified > 0:
            whatsapp_tool.send_message(
                f"🎯 Score: {qualified} vacante(s) ATS calificadas (>={settings.job_match_threshold}) "
                f"listas para aplicar automáticamente (sin LinkedIn)."
            )
    except Exception as e:
        logger.error(f"[score] error: {e}")


async def portal_scan_task():
    """
    Escanea APIs públicas de Greenhouse/Ashby/Lever — CERO tokens de LLM.
    Jobs nuevos quedan con status='found'; al terminar dispara score_pending_task
    para evaluarlos de inmediato (loop scan→score→apply).
    """
    from src.tools import portal_scanner

    logger.info("[portal_scan] iniciando scan zero-token...")
    try:
        result = portal_scanner.scan_all(dry_run=False, check_liveness=True)
        portal_scanner.print_summary(result)

        if result.added > 0:
            whatsapp_tool.send_message(
                f"🔍 Portal scan: {result.added} jobs nuevos "
                f"({result.scanned} empresas, {result.skipped_expired} ghosts filtrados)"
            )
            # Encadena el scoring de inmediato para cerrar el loop scan→score→apply.
            await score_pending_task()
    except FileNotFoundError as e:
        logger.warning(f"[portal_scan] config faltante: {e}")
    except Exception as e:
        logger.error(f"[portal_scan] error: {e}")


async def cleanup_stale_jobs_task():
    """
    Marca jobs stale (status='found', >14 días) como 'expired'.
    Solo aplica a jobs que nunca fueron aplicados — no toca historial.
    Corre 1 vez al día (cron 6:00 AM).
    """
    MAX_AGE_DAYS = 14
    logger.info(f"[cleanup] limpiando jobs stale (>{MAX_AGE_DAYS} días)...")
    try:
        result = tracker.mark_stale_as_expired(max_age_days=MAX_AGE_DAYS)
        count = result.get("marked_expired", 0)
        if count > 0:
            logger.info(f"[cleanup] {count} jobs marcados como 'expired'")
            whatsapp_tool.send_message(
                f"🧹 Cleanup: {count} vacantes expiradas (>{MAX_AGE_DAYS}d) eliminadas del pipeline"
            )
    except Exception as e:
        logger.error(f"[cleanup] error: {e}")


async def followup_task():
    """
    Envía follow-up emails con cadencia diferenciada por estado.
    Usa followup_cadence.decide() en lugar de "7 días fijo".
    """
    from src.tools import followup_cadence

    logger.info("Revisando aplicaciones con cadencia follow-up...")

    try:
        resume = _load_resume()
        candidates = tracker.get_applications_with_cadence_context()
        followups_sent = 0
        MAX_FOLLOWUPS_PER_CYCLE = 2

        for app in candidates:
            if followups_sent >= MAX_FOLLOWUPS_PER_CYCLE:
                logger.info(
                    f"[followup-antispam] Límite {MAX_FOLLOWUPS_PER_CYCLE}/ciclo alcanzado"
                )
                break

            decision = followup_cadence.decide_from_app(app)
            if not decision.should_send:
                logger.debug(
                    f"[cadence] skip {app['company']} ({app['title']}): {decision.reason}"
                )
                continue

            job_emails = app.get("emails_in_job", "")
            if not job_emails or "@" not in str(job_emails):
                logger.warning(
                    f"No hay email para follow-up de {app['title']} @ {app['company']}"
                )
                continue

            to_email = str(job_emails).split(",")[0].strip()
            if _is_blocked_sender(to_email):
                logger.info(f"[followup-blocklist] Ignorando {to_email}")
                continue

            days_since = int(app.get("days_since_apply", settings.followup_days) or 7)
            followup = master_agent.generate_followup_email(
                app, resume, days_since, kind=decision.followup_kind
            )

            if AUTO_EMAIL_DISABLED:
                logger.info(
                    f"[AUTO_EMAIL_DISABLED] Follow-up {decision.followup_kind} listo "
                    f"para {to_email} — revisar manualmente"
                )
                whatsapp_tool.send_message(
                    f"📧 Follow-up ({decision.followup_kind}) listo para "
                    f"*{app['company']}* ({app['title']}) — envío manual"
                )
                continue

            sent = gmail_tool.send_email(
                to=to_email,
                subject=followup["subject"],
                body=followup["body"],
            )

            if sent:
                tracker.record_followup_sent(app["app_id"])
                followups_sent += 1
                logger.info(
                    f"[followup] {decision.followup_kind} → {app['company']}: {decision.reason}"
                )
                whatsapp_tool.send_message(
                    f"Envié follow-up ({decision.followup_kind}) a *{app['company']}* "
                    f"por *{app['title']}*"
                )

    except Exception as e:
        logger.error(f"Error en followup_task: {e}")


# --- HELPERS ---

_MEXICO_KEYWORDS = {
    "cdmx",
    "ciudad de mexico",
    "ciudad de méxico",
    "mexico city",
    "méxico, méxico",
    "mexico, mexico",
    "df",
    "distrito federal",
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
            tracker.save_interview(
                {
                    "job_id": job_id,
                    "email_id": email_db_id,
                    "scheduled_at": interview_dt.isoformat() if interview_dt else None,
                    "calendar_event_id": event_id,
                    "interviewer": interviewer_email,
                }
            )

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
async def stalker_group_A():
    await stalker_group_task("A")


async def stalker_group_B():
    await stalker_group_task("B")


async def stalker_group_C():
    await stalker_group_task("C")


async def stalker_group_D():
    await stalker_group_task("D")


async def stalker_group_E():
    await stalker_group_task("E")


async def stalker_group_F():
    await stalker_group_task("F")


# --- FASTAPI APP ---


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Iniciando orchestrator...")

    # ── SCHEDULED TASKS (actualizado 2026-04-28) ────────────────────────────

    # ── ACTIVOS ───────────────────────────────────────────────────────────

    # [EMAIL MONITOR] Lee Gmail cada 30 min — detecta respuestas de reclutadores.
    # Solo lee y escala a WhatsApp. NO envía emails (AUTO_EMAIL_DISABLED=True).
    scheduler.add_job(
        email_monitor_task,
        "interval",
        minutes=30,
        id="email_monitor",
        max_instances=1,
        coalesce=True,
        replace_existing=True,
    )

    # [LINKEDIN MESSAGES] Dispara cada 15 min pero el governor lo gatea a
    # ~1 lectura cada 75 min / 12 al día (MSG_READ) para reducir la huella de bot.
    # Solo lee y escala a WhatsApp. NO responde automáticamente (AUTO_LINKEDIN_REPLY_DISABLED=True).
    scheduler.add_job(
        linkedin_messages_task,
        "interval",
        minutes=15,
        id="linkedin_messages",
        max_instances=1,
        coalesce=True,
        replace_existing=True,
    )

    # [FOLLOW-UP] Genera seguimientos a applications sin respuesta — diario 9am.
    # Solo prepara el email, NO lo envía (AUTO_EMAIL_DISABLED=True). Notifica por WA.
    scheduler.add_job(
        followup_task,
        "cron",
        hour=9,
        minute=0,
        id="followup",
        max_instances=1,
        coalesce=True,
        replace_existing=True,
    )

    # [APPLICATION AGENT] Aplica jobs priorizados cada 2 minutos.
    # max_instances=1 + coalesce: evita que dos ciclos pisen el mismo job.
    # Prioriza: score DESC, found_at DESC, filtro <14d. Cap 45 apps/día.
    # Easy Apply vía Voyager HTTP API (sin browser). Non-Easy Apply → external_apply_queue.
    scheduler.add_job(
        queue_task,
        "interval",
        minutes=2,
        id="application_agent",
        max_instances=1,
        coalesce=True,
        replace_existing=True,
    )

    # Liberar locks de processing que quedaron colgados de runs anteriores.
    try:
        from src.db.tracker import JobTracker

        _t = JobTracker()
        _t.release_stale_locks(max_age_minutes=30)
        _t.clear_expired_decisions()
    except Exception as e:
        logger.warning(f"[startup] No se pudieron liberar locks stale: {e}")

    # Restaurar estado de decisiones pendientes (survive crashes)
    try:
        _load_pending_state()
    except Exception as e:
        logger.warning(f"[startup] No se pudo restaurar estado pendiente: {e}")

    # [PIPELINE HEALTH] Revisa todo el pipeline cada 4h: detecta procesos
    # activos (Gmail/LinkedIn/Calendar), re-encola aplicaciones fallidas,
    # marca ghosted, notifica eventos raros. NO habla con reclutadores.
    async def pipeline_health_task():
        logger.info("[pipeline] ===== review cycle =====")
        try:
            from src.agents import pipeline_health_agent

            result = await asyncio.to_thread(pipeline_health_agent.run_pipeline_review)
            logger.info(f"[pipeline] resultado: {result}")
            return result
        except Exception as e:
            logger.exception(f"[pipeline] Error: {e}")
            return {"error": str(e)}

    scheduler.add_job(
        pipeline_health_task,
        "interval",
        hours=4,
        id="pipeline_health",
        max_instances=1,
        coalesce=True,
        replace_existing=True,
    )

    # [DESACTIVADO] search_and_apply_task: reemplazado por queue_task
    # scheduler.add_job(search_and_apply_task, "interval", hours=1, id="search_and_apply")

    # [DESACTIVADO] premium_job_search_task: queue manager ya prioriza por score
    # scheduler.add_job(premium_job_search_task, "interval", hours=1, start_date="2026-04-12 00:30:00", id="premium_job_search")

    # [STEALTH] Búsqueda JobSpy: 2h → 8h (LinkedIn detectó automatización 2026-05-11)
    scheduler.add_job(job_search_task, "interval", hours=8, id="job_search")

    # Portal scanner zero-token (NO toca LinkedIn): se mantiene en 4h
    scheduler.add_job(portal_scan_task, "interval", hours=4, id="portal_scan")
    scheduler.add_job(indeed_apply_task, "interval", hours=3, id="indeed_apply")

    # [SCORE] Eslabón scan→score→apply: evalúa con LLM los jobs sin score
    # (portal_scanner/discovery) para que external_ats pueda aplicarlos. Cada 2h
    # como catch-up (portal_scan ya lo encadena al terminar). Cero riesgo LinkedIn.
    scheduler.add_job(
        score_pending_task, "interval", hours=2, id="score_pending",
        max_instances=1, coalesce=True, replace_existing=True,
    )

    # [LI HEALTH] Monitor de riesgo de baneo cada 2h: probe de sesión + risk_score.
    # Detecta señales tempranas SIN provocar. Escala ban solo ante restricción real.
    scheduler.add_job(
        linkedin_health_task, "interval", hours=2, id="linkedin_health",
        max_instances=1, coalesce=True, replace_existing=True,
    )

    # [LI PASSIVE] Lectura de cobertura gobernada (~cada 3h, gateada a pocas/día)
    # para equilibrar la mezcla de acciones (no solo escrituras).
    scheduler.add_job(
        linkedin_passive_task, "interval", hours=3, id="linkedin_passive",
        max_instances=1, coalesce=True, replace_existing=True,
    )

    # External ATS apply (Greenhouse/Lever/Ashby) — sin riesgo LinkedIn, 3 apps/ciclo
    scheduler.add_job(
        external_ats_task, "interval", hours=2, id="external_ats",
        max_instances=1, coalesce=True, replace_existing=True,
    )

    # [STEALTH] Top companies stalker: 1h → 6h
    scheduler.add_job(top_companies_stalker_task, "interval", hours=6, id="top_companies_stalker")

    # Cleanup de vacantes expiradas: diario a las 6:00 AM
    scheduler.add_job(
        cleanup_stale_jobs_task,
        "cron",
        hour=6,
        minute=0,
        id="cleanup_stale",
    )

    # [STEALTH] Job Discovery: 3h → 8h (post-restricción LinkedIn 2026-05-11)
    scheduler.add_job(
        job_discovery_task,
        "interval",
        hours=8,
        start_date="2026-04-14 01:00:00",
        id="job_discovery",
    )

    # LinkedIn content: cada 5 horas (SIMPLE - NO CRON para depuración)
    scheduler.add_job(
        linkedin_content_task, "interval", hours=5, id="linkedin_content_simple"
    )

    # Inspección de infografías: L-V 9:30, 14:00, 18:00
    scheduler.add_job(
        image_inspection_task,
        "cron",
        hour="9,14,18",
        minute=30,
        day_of_week="mon-fri",
        id="image_inspection",
    )

    # Limpieza de imágenes huérfanas: domingos 3am
    scheduler.add_job(
        image_cleanup_task,
        "cron",
        hour=3,
        minute=0,
        day_of_week="sun",
        id="image_cleanup",
    )

    # [STEALTH DESACTIVADO 2026-05-11] cookie refresh automático = señal fuerte de bot.
    # Login manual semanal cuando expiren cookies. Reactivar SOLO si es indispensable.
    # scheduler.add_job(
    #     linkedin_cookie_refresh_task, "interval", hours=12, id="linkedin_cookie_refresh"
    # )

    # ── [STEALTH] TR stalker: 1h → 8h ──────────────────────────────────
    scheduler.add_job(
        thomson_reuters_stalker_task, "interval", hours=8, id="tr_stalker"
    )

    # ── [STEALTH] STALKER JOBS: 6 grupos, cada 6h, escalonados ─────────
    # Antes: cada hora (señal robótica fuerte). Ahora: cada 6h, staggered
    # de modo que solo uno corre a la vez (jitter humano).
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:00")
    scheduler.add_job(
        stalker_group_A, "interval", hours=6, id="stalker_A"
    )
    scheduler.add_job(
        stalker_group_B, "interval", hours=6, minutes=37, id="stalker_B"
    )
    scheduler.add_job(
        stalker_group_C, "interval", hours=7, minutes=11, id="stalker_C"
    )
    scheduler.add_job(
        stalker_group_D, "interval", hours=6, minutes=53, id="stalker_D"
    )
    scheduler.add_job(
        stalker_group_E, "interval", hours=7, minutes=29, id="stalker_E"
    )
    scheduler.add_job(
        stalker_group_F, "interval", hours=8, minutes=17, id="stalker_F"
    )

    scheduler.start()
    logger.success(
        "Scheduler iniciado [STEALTH] — 6 stalkers c/6-8h staggered | búsqueda c/8h | discovery c/8h | cookie-refresh DESACTIVADO"
    )

    whatsapp_tool.send_message(
        "Agente de búsqueda de empleo activo.\n\n"
        "Arquitectura OPCIÓN 3 (Mezcla Optimizada):\n"
        "• Job Queue Manager: aplica jobs priorizados (5 apps/hora max)\n"
        "• 6 Company Stalkers: aplican directamente a empresas específicas\n"
        "• Job Stalker: busca y guarda jobs en BD\n"
        "• Job Discovery: búsqueda complementaria cada 3h\n"
        "• LinkedIn Content: posts profesionales cada 5h\n\n"
        "Total: ~5-6 apps/hora (seguro, sin saturar LinkedIn)\n\n"
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


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
            whatsapp_tool.send_message(
                f"Aplicando a los {total} trabajos pendientes..."
            )
            # Procesar todos en background para no bloquear
            asyncio.create_task(_apply_all_pending())
        else:
            whatsapp_tool.send_message(
                "No hay trabajos pendientes de aprobación ahora mismo."
            )
        return {"ok": True}

    # --- COMANDOS ---
    if "estado" in message or "reporte" in message or "status" in message:
        stats = tracker.get_stats()
        recent = tracker.get_all_jobs(limit=5)
        whatsapp_tool.send_status_report(stats, recent)

    elif message.startswith("buscar"):
        keywords = raw_message[6:].strip() or "developer"
        whatsapp_tool.send_message(
            f"Buscando '{keywords}'... te aviso cuando encuentre algo."
        )
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
        # AI Orchestrator — lenguaje natural con tool calling
        from src.agents import ai_orchestrator_agent

        response = await asyncio.to_thread(
            ai_orchestrator_agent.process_message, raw_message
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
    from src.tools.application_verifier import (
        verify_applications_via_gmail,
        verify_capital_one,
    )

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


@app.get("/health/linkedin")
async def health_linkedin():
    """Monitor de riesgo de baneo: estado de sesión + risk_score (sin provocar)."""
    from src.tools import linkedin_health
    probe = await asyncio.to_thread(linkedin_health.probe_account_status)
    risk = await asyncio.to_thread(linkedin_health.risk_report)
    ban = gov.get_ban_state()
    return {
        "session": probe,
        "risk": risk,
        "ban_state": {
            "current_state": ban.get("current_state"),
            "recovery_mode": ban.get("recovery_mode"),
            "ban_count": ban.get("ban_count"),
            "warmup_anchor": ban.get("warmup_anchor"),
        },
    }


# --- NEW DASHBOARD APIs ---


@app.get("/api/stats")
async def get_stats_api():
    """Estadísticas consolidadas para el dashboard."""
    return tracker.get_stats()


@app.get("/api/jobs")
async def get_jobs_api(
    status: str = "all", limit: int = 500, min_score: int = 0, search: str = ""
):
    """Lista de jobs filtrada con búsqueda y score mínimo."""
    if status == "all":
        jobs = tracker.get_all_jobs(limit=limit)
    else:
        jobs = tracker.get_jobs_by_status(status)
    if min_score > 0:
        jobs = [j for j in jobs if (j.get("match_score") or 0) >= min_score]
    if search:
        q = search.lower()
        jobs = [
            j
            for j in jobs
            if q in (j.get("title") or "").lower()
            or q in (j.get("company") or "").lower()
        ]
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


@app.get("/api/job/{job_id}/timeline")
async def job_timeline(job_id: str):
    """
    Agrega toda la información de una vacante para el dashboard:
    job info + historial de aplicaciones + emails + LinkedIn + entrevistas.
    """
    from fastapi import HTTPException

    job = tracker.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job no encontrado")
    company = job.get("company", "")
    emails = tracker.get_emails_for_job(job_id)
    if not emails and company:
        emails = tracker.get_emails_by_company(company, days=60)
    return {
        "job": dict(job),
        "applications": tracker.get_full_pipeline_for_job(job_id),
        "emails": emails,
        "linkedin": tracker.get_conversations_by_company(company) if company else [],
        "interviews": tracker.get_interviews_for_job(job_id),
        "days_since_applied": tracker.days_since_applied(job_id),
    }


@app.post("/api/chat/reset")
async def reset_chat():
    """Limpia el historial de conversación del AI Orchestrator."""
    from src.agents import ai_orchestrator_agent

    ai_orchestrator_agent.reset_conversation()
    return {"ok": True, "message": "Historial de conversación limpiado"}


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
    scheduler.add_job(
        job_search_task, "date", id="manual_trigger", replace_existing=True
    )
    return {"ok": True, "message": "Búsqueda iniciada"}


@app.post("/trigger/portal-scan")
async def trigger_portal_scan():
    """Trigger manual del portal scanner zero-token."""
    scheduler.add_job(
        portal_scan_task, "date", id="manual_portal_scan", replace_existing=True
    )


@app.post("/trigger/external-ats")
async def trigger_external_ats():
    """Trigger manual del External ATS agent (Greenhouse/Lever/Ashby)."""
    scheduler.add_job(
        external_ats_task, "date", id="manual_external_ats", replace_existing=True
    )
    return {"ok": True, "message": "External ATS apply iniciado"}


@app.post("/trigger/discovery")
async def trigger_discovery():
    """Trigger manual del job discovery (prioriza jobs con < 10 applicantes)."""
    scheduler.add_job(
        job_discovery_task, "date", id="manual_discovery", replace_existing=True
    )
    return {
        "ok": True,
        "message": "Job discovery iniciado (prioridad: < 10 applicantes)",
    }


@app.get("/external-queue")
async def external_queue(min_score: int = 75, limit: int = 100):
    """Lista los jobs externos pendientes de procesar (Antigravity o manual)."""
    jobs = tracker.get_external_queue(min_score=min_score, limit=limit)
    by_ats = {}
    for j in jobs:
        by_ats.setdefault(j["ats_type"], 0)
        by_ats[j["ats_type"]] += 1
    return {
        "total": len(jobs),
        "by_ats_type": by_ats,
        "jobs": jobs,
    }


@app.post("/trigger/apply-all")
async def trigger_apply_all(easy_apply_only: bool = True):
    """
    Aplica a jobs con score >= threshold. Por default solo Easy Apply
    (los externos van a external_apply_queue automáticamente).
    """
    easy_apply_jobs = tracker.get_application_queue(
        min_score=settings.job_match_threshold,
        limit=100,
        easy_apply_only=easy_apply_only,
    )
    loaded = 0
    for job in easy_apply_jobs:
        job_id = job["id"]
        if job_id not in pending_confirmations:
            _add_pending_confirmation(job_id, {
                "job": job,
                "score": job.get("match_score", 0),
                "reason": "",
            })
            loaded += 1

    if loaded == 0:
        return {
            "ok": True,
            "message": (
                f"No hay jobs Easy Apply con score >= {settings.job_match_threshold}% listos"
                if easy_apply_only
                else f"No hay jobs con score >= {settings.job_match_threshold}% listos"
            ),
        }

    asyncio.create_task(_apply_all_pending())
    mode = "Easy Apply" if easy_apply_only else "todos"
    return {
        "ok": True,
        "message": f"Aplicando a {loaded} jobs {mode} con score >= {settings.job_match_threshold}%",
    }


@app.post("/trigger/email")
async def trigger_email():
    """Trigger manual de monitoreo de email (para testing)."""
    scheduler.add_job(
        email_monitor_task, "date", id="manual_email", replace_existing=True
    )
    return {"ok": True, "message": "Monitoreo de email iniciado"}


@app.post("/trigger/linkedin-post")
async def trigger_linkedin_post():
    """Trigger manual: genera y publica un post LinkedIn ahora."""
    scheduler.add_job(
        linkedin_content_task, "date", id="manual_linkedin_post", replace_existing=True
    )
    return {"ok": True, "message": "Post LinkedIn en proceso"}


@app.post("/trigger/linkedin-hr")
async def trigger_linkedin_hr():
    """Trigger manual: busca y conecta con reclutadores LinkedIn ahora."""
    scheduler.add_job(
        linkedin_hr_expansion_task,
        "date",
        id="manual_linkedin_hr",
        replace_existing=True,
    )
    return {"ok": True, "message": "Expansión de red HR en proceso"}


@app.post("/trigger/inspect-images")
async def trigger_inspect_images():
    """Trigger manual: inspecciona infografías pendientes ahora."""
    scheduler.add_job(
        image_inspection_task,
        "date",
        id="manual_image_inspection",
        replace_existing=True,
    )
    return {"ok": True, "message": "Inspección de imágenes en proceso"}


@app.post("/trigger/premium-search")
async def trigger_premium_search():
    """Trigger manual: búsqueda premium de empleos ahora."""
    scheduler.add_job(
        premium_job_search_task,
        "date",
        id="manual_premium_search",
        replace_existing=True,
    )
    return {"ok": True, "message": "Búsqueda premium en proceso"}


@app.post("/trigger/image-cleanup")
async def trigger_image_cleanup():
    """Trigger manual: limpieza de imágenes huérfanas ahora."""
    scheduler.add_job(
        image_cleanup_task, "date", id="manual_image_cleanup", replace_existing=True
    )
    return {"ok": True, "message": "Limpieza de imágenes en proceso"}


@app.post("/trigger/cleanup-stale")
async def trigger_cleanup_stale(days: int = 14):
    """Trigger manual: marca vacantes >N días como 'expired'."""
    result = tracker.mark_stale_as_expired(max_age_days=days)
    return {
        "ok": True,
        "marked_expired": result.get("marked_expired", 0),
        "max_age_days": days,
    }


async def indeed_easy_apply_search_task():
    """Búsqueda dedicada a Indeed Easy Apply CDMX. Tag ats_type='indeed_apply'."""
    logger.info("Ejecutando indeed_easy_apply_search_task...")
    try:
        from src.tools.jobspy_tool import search_jobs
        from src.db.tracker import JobTracker

        tracker = JobTracker()
        terms = [
            "Java Developer", "Backend Developer", "Software Engineer",
            "Senior Java", "Spring Boot", "Fullstack Java", "Python Developer",
            "Node.js Backend", "DevOps", "Site Reliability",
        ]
        total_new = 0
        for term in terms:
            jobs = await asyncio.to_thread(
                search_jobs, term, "Ciudad de Mexico", 15, 168, ["indeed"], True
            )
            for j in jobs:
                if tracker.save_job(j):
                    total_new += 1
            await asyncio.sleep(2)
        logger.info(f"[indeed_easy_apply_search] {total_new} jobs nuevos taggeados ats_type=indeed_apply")
    except Exception as e:
        logger.error(f"Error en indeed_easy_apply_search_task: {e}")


@app.post("/trigger/indeed-easy-apply-search")
async def trigger_indeed_easy_apply_search():
    """Trigger manual: búsqueda Indeed CDMX filtrada a Easy Apply."""
    scheduler.add_job(
        indeed_easy_apply_search_task,
        "date",
        id="manual_indeed_easy_apply_search",
        replace_existing=True,
    )
    return {"ok": True, "message": "Búsqueda Indeed Easy Apply CDMX iniciada"}


async def indeed_apply_task():
    """Indeed auto-apply: pasada limitada con rate limits y CAPTCHA detector."""
    logger.info("Ejecutando indeed_apply_task...")
    try:
        from src.tools import indeed_apply
        result = await asyncio.to_thread(indeed_apply.run_indeed_apply_cycle)
        logger.info(f"[indeed_apply] resultado: {result}")
    except Exception as e:
        logger.error(f"Error en indeed_apply_task: {e}")


@app.post("/trigger/indeed-apply")
async def trigger_indeed_apply(force: bool = False, max_apps: int = 0):
    """Trigger manual: una pasada de Indeed auto-apply.
    force=True ignora business hours (testing).
    max_apps>0 limita esta pasada (default: cap diario completo)."""
    async def _job():
        from src.tools import indeed_apply
        ma = max_apps if max_apps > 0 else None
        result = await asyncio.to_thread(indeed_apply.run_indeed_apply_cycle, force, ma)
        logger.info(f"[indeed_apply][manual] resultado: {result}")

    scheduler.add_job(_job, "date", id="manual_indeed_apply", replace_existing=True)
    return {"ok": True, "force": force, "max_apps": max_apps or 5}


@app.get("/indeed-apply/state")
async def get_indeed_apply_state():
    """Estado actual del Indeed auto-apply (cap diario, freeze, totales)."""
    try:
        from src.tools.indeed_apply import _load_state
        return _load_state()
    except Exception as e:
        return {"error": str(e)}


@app.post("/trigger/tr-stalker")
async def trigger_tr_stalker():
    """Trigger manual: stalker dedicado de Thomson Reuters."""
    scheduler.add_job(
        thomson_reuters_stalker_task,
        "date",
        id="manual_tr_stalker",
        replace_existing=True,
    )
    return {
        "ok": True,
        "message": "Thomson Reuters stalker ejecutando búsqueda exhaustiva",
    }


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
            scheduler.add_job(
                stalker_group_task,
                "date",
                args=[g],
                id=f"manual_stalker_{g}",
                replace_existing=True,
            )
        return {"ok": True, "message": "Stalker ejecutando todos los grupos"}
    if group in STALKER_GROUPS:
        scheduler.add_job(
            stalker_group_task,
            "date",
            args=[group],
            id=f"manual_stalker_{group}",
            replace_existing=True,
        )
        return {
            "ok": True,
            "message": f"Stalker grupo {group} en proceso: {STALKER_GROUPS[group]}",
        }
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
                cover_letter = await asyncio.to_thread(
                    master_agent.generate_cover_letter, job, resume
                )
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
                        browser_tool.apply_to_job_sync,
                        job_url,
                        resume,
                        job["title"],
                        job["company"],
                        cover_letter,
                    )
                    if result.get("success"):
                        method = "browser_agent"
                        apply_success = True
                        logger.info(
                            f"CONFIRMADO: Aplicación enviada a {job['title']} @ {job['company']}"
                        )
                    elif result.get("status") == "captcha":
                        method = "blocked_captcha"
                        logger.warning(
                            f"CAPTCHA en {job['title']} @ {job['company']} - requiere manual"
                        )
                    elif result.get("status") == "need_user":
                        method = "needs_info"
                        logger.warning(
                            f"Info requerida para {job['title']}: {result.get('message')}"
                        )
                    else:
                        method = "browser_failed"
                        logger.warning(
                            f"Browser no pudo aplicar a {job['title']}: {result.get('message')}"
                        )
                except Exception as be:
                    logger.warning(f"Browser error para {job['title']}: {be}")
                    method = "browser_error"

            # Save application with actual status
            status = "applied" if apply_success else "pending_apply"
            tracker.save_application(
                job_id=job_id, method=method, cover_letter=cover_letter, status=status
            )

            if apply_success:
                applied += 1
            else:
                errors += 1

            logger.info(
                f"{'APLICADO' if apply_success else 'PENDIENTE'}: {job['title']} @ {job['company']} via {method}"
            )

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
            tracker.save_application(
                job_id=job_id, method="linkedin_easy_apply", cover_letter=cover_letter
            )
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
            tracker.save_application(
                job_id=job_id, method=method, cover_letter=cover_letter
            )
            if not result["success"]:
                tracker.update_application_status(job_id, result["status"])
        else:
            # Sin URL → guardar como pendiente
            tracker.save_application(
                job_id=job_id, method="manual_pending", cover_letter=cover_letter
            )
            whatsapp_tool.send_message(
                f"Guardé *{job['title']}* @ *{job['company']}* para aplicar.\n"
                f"No encontré URL directa — revisa LinkedIn manualmente."
            )

        logger.info(
            f"Procesada aplicación: {job['title']} @ {job['company']} ({method})"
        )
    else:
        tracker.update_job_status(job_id, "skipped")
        whatsapp_tool.send_message(
            f"Ok, omitido: *{job['title']}* en *{job['company']}*"
        )

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
        location="Ciudad de Mexico",
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
            _add_pending_confirmation(job["id"], {
                "job": job,
                "score": score,
                "reason": reason,
            })
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
    item = pending_recruiter_replies[conv_id]
    _remove_pending_recruiter_reply(conv_id)
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
    item = pending_slot_selection[conv_id]
    _remove_pending_slot_selection(conv_id)
    slots = item["slots"]
    analysis = item["analysis"]
    sender_name = item["sender_name"]

    if choice == 0 or choice > len(slots):
        whatsapp_tool.send_message(f"Ok, decliné la entrevista con *{sender_name}*.")
        linkedin_messages_tool.send_message(
            conv_id,
            "Gracias por contactarme. Por el momento no podré avanzar con el proceso. ¡Saludos!"
            if analysis.get("language") == "es"
            else "Thank you for reaching out. I won't be able to move forward at this time. Best regards!",
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


# ---------------------------------------------------------------------------
# Chrome Extension API endpoints
# ---------------------------------------------------------------------------

@app.post("/api/extension/cover-letter")
async def extension_cover_letter(request: Request):
    """Genera cover letter para la extensión de Chrome usando Kimi."""
    body = await request.json()
    job = {
        "title": body.get("title", ""),
        "company": body.get("company", ""),
        "description": body.get("description", ""),
        "url": body.get("url", ""),
    }
    resume = _load_resume()
    cover_letter = ""
    try:
        cover_letter = await asyncio.to_thread(master_agent.generate_cover_letter, job, resume)
    except Exception as e:
        logger.warning(f"[extension] Cover letter falló: {e}")

    return {
        "cover_letter": cover_letter or "",
        "job": {"title": job["title"], "company": job["company"]},
    }


@app.post("/api/extension/log")
async def extension_log(request: Request):
    """Registra en DB una aplicación enviada desde la extensión de Chrome."""
    body = await request.json()
    job_id = body.get("job_id", "")
    title = body.get("title", "")
    company = body.get("company", "")
    url = body.get("url", "")
    status = body.get("status", "applied")
    method_detail = body.get("method_detail", "linkedin_extension")
    cover_letter = body.get("cover_letter", "")

    if not job_id:
        return {"saved": False, "error": "job_id requerido"}

    try:
        # Crear job en DB si no existe
        if not tracker.job_exists(job_id):
            tracker.save_job({
                "id": job_id,
                "title": title,
                "company": company,
                "url": url,
                "source": "linkedin_extension",
                "match_score": 80,
                "ats_type": "linkedin",
            })

        tracker.save_application(
            job_id=job_id,
            method="linkedin_extension",
            cover_letter=cover_letter,
            status=status,
            method_detail=method_detail,
        )
        logger.info(f"[extension] Aplicación registrada: {title} @ {company} → {status}")
        return {"saved": True}
    except Exception as e:
        logger.error(f"[extension] Error guardando aplicación: {e}")
        return {"saved": False, "error": str(e)}


@app.get("/api/extension/status")
async def extension_status():
    """Retorna estado del sistema para el popup de la extensión."""
    try:
        with tracker._get_conn() as conn:
            row = conn.execute(
                """SELECT COUNT(*) FROM applications
                   WHERE method = 'linkedin_extension'
                     AND date(applied_at) = date('now')"""
            ).fetchone()
            applied_today = (row[0] or 0) if row else 0
    except Exception:
        applied_today = 0

    return {
        "enabled": True,
        "applied_today": applied_today,
        "daily_cap": 15,
        "backend": "online",
    }
