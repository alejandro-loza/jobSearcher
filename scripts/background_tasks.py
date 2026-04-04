#!/usr/bin/env python3
"""
DISABLED — Este script fue la fuente de 71 emails spam (2026-03-18 a 2026-04-02).
Enviaba un template genérico + CV a TODOS los remitentes sin contexto ni dedup.
NO EJECUTAR. Usar el orchestrator (src/orchestrator.py) con sus safety switches.
"""

import sys
print("ERROR: background_tasks.py está DESHABILITADO. Fue la fuente de spam.", file=sys.stderr)
sys.exit(1)

# --- EVERYTHING BELOW IS DEAD CODE ---

import sys
import time
from datetime import datetime
from pathlib import Path

# Añadir directorio del proyecto al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger

# Configurar logger
logger.add(
    "logs/jobsearcher_background.log",
    rotation="10 MB",
    retention="7 days",
    level="INFO",
)


def main():
    logger.info("=== INICIANDO JOBSEARCHER EN SEGUNDO PLANO ===")
    logger.info(f"Hora de inicio: {datetime.now().isoformat()}")

    try:
        # 1. Buscar nuevas vacantes
        logger.info("[1/4] Buscando nuevas vacantes...")
        from src.tools import jobspy_tool
        from src.agents import master_agent
        from src.db.tracker import JobTracker
        import json

        resume = json.load(open("data/resume.json"))
        tracker = JobTracker()

        terms = [
            ("Senior Java Developer", "remote"),
            ("Java Spring Boot Developer", "remote"),
            ("Senior Software Engineer Java", "remote"),
        ]

        all_jobs = []
        for term, location in terms:
            logger.info(f"Buscando: {term} en {location}...")
            jobs = jobspy_tool.search_jobs(
                search_term=term,
                location=location,
                results_wanted=10,
                hours_old=168,
                easy_apply_only=False,
            )
            all_jobs.extend(jobs)
            logger.info(f"Encontrados: {len(jobs)} trabajos")

        logger.info(f"Total jobs encontrados: {len(all_jobs)}")

        # Guardar jobs en DB
        for job in all_jobs:
            tracker.save_job(job)

        # 2. Contestar emails de reclutadores
        logger.info("[2/4] Revisando emails de reclutadores...")
        from src.tools import gmail_tool

        processed_ids = set()
        emails = gmail_tool.get_recent_job_emails(
            processed_ids=processed_ids, max_results=20
        )

        logger.info(f"Encontrados {len(emails)} emails de trabajo")

        # Analizar y responder emails relevantes
        for email in emails:
            from_addr = email["from_address"].lower()

            # Filtrar emails de Alejandro y noreply
            if "alejandrohloza@gmail.com" in from_addr or "noreply" in from_addr:
                continue

            # Extraer email del remitente
            if "<" in from_addr and ">" in from_addr:
                email_addr = from_addr.split("<")[1].split(">")[0]
            else:
                continue

            # Enviar CV con respuesta
            logger.info(f"Enviando CV a: {email_addr}")

            result = gmail_tool.send_email(
                to=email_addr,
                subject=f"Re: {email['subject']}",
                body=f"""Hi,

Thank you for reaching out about this opportunity.

I'm a Senior Software Engineer with 12+ years of experience specializing in Java, Spring Boot, microservices, and cloud technologies (AWS/GCP). Please find my attached resume for your review.

I'm based in Mexico City and open to remote or hybrid opportunities. Key highlights include:
- 12+ years in Java development with Spring Boot
- Extensive experience with microservices architecture
- Full stack capabilities (JavaScript, Angular/React)
- Cloud infrastructure (AWS/GCP)
- Leading development teams and mentoring

I'd be happy to discuss my qualifications and how they align with your requirements.

Best regards,
Alejandro Hernandez Loza
+52 56 4144 6948
https://www.linkedin.com/in/alejandro-hernandez-loza/""",
                attachments=["data/cv_alejandro_en.pdf"],
            )

            if result:
                logger.success(f"CV enviado a {email_addr}")
            else:
                logger.error(f"Error enviando CV a {email_addr}")

        # 3. Contestar mensajes de LinkedIn
        logger.info("[3/4] Revisando mensajes de LinkedIn...")
        from src.tools import linkedin_messages_tool
        from src.agents import recruiter_agent
        from src.tools import calendar_tool

        # Obtener conversaciones no leídas
        convs = linkedin_messages_tool.get_unread_messages(limit=10)
        logger.info(f"Conversaciones sin leer: {len(convs)}")

        for conv in convs[:5]:  # Procesar primeras 5
            conv_id = conv["conversation_id"]
            sender_name = conv["sender_name"]

            logger.info(f"Procesando conversación: {sender_name}")

            # Verificar si ya respondimos
            if tracker.conversation_has_our_reply(conv_id):
                logger.info(f"Ya respondimos a {sender_name}, saltando...")
                continue

            # Obtener historial completo
            msgs = linkedin_messages_tool.get_full_conversation(conv_id)

            # Obtener slots libres
            free_slots = calendar_tool.get_free_slots(days_ahead=7, duration_minutes=60)

            # Analizar mensaje del reclutador
            analysis = recruiter_agent.analyze_recruiter_message(
                message=conv.get("last_message", ""),
                sender_name=sender_name,
                sender_title=conv.get("sender_title", ""),
                conversation_history=msgs,
                free_slots=free_slots,
            )

            logger.info(f"Intent: {analysis['intent']}")
            logger.info(f"Urgency: {analysis['urgency']}")
            logger.info(f"Needs user input: {analysis['needs_user_input']}")

            # Si necesita input del usuario, crear tarea manual
            if analysis["needs_user_input"]:
                logger.warning(
                    f"Conversación con {sender_name} requiere input del usuario"
                )
                continue

            # Si hay borrador sugerido, enviarlo
            if analysis.get("draft_response"):
                result = linkedin_messages_tool.send_message(
                    conv_id, analysis["draft_response"]
                )

                if result:
                    logger.success(f"Mensaje enviado a {sender_name}")
                    tracker.record_our_reply(conv_id, analysis["draft_response"])
                else:
                    logger.error(f"Error enviando mensaje a {sender_name}")

        # 4. Postear infografías en LinkedIn (simulado)
        logger.info("[4/4] Posteando infografías en LinkedIn...")
        logger.info("Nota: Esta funcionalidad requiere integración con LinkedIn API")
        logger.info("Para implementar, ver docs/POST_LINKEDIN.md")

        logger.success("=== TODAS LAS TAREAS COMPLETADAS ===")
        logger.info(f"Hora de finalización: {datetime.now().isoformat()}")

    except Exception as e:
        logger.error(f"Error en ejecución: {e}")
        import traceback

        logger.error(traceback.format_exc())
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
