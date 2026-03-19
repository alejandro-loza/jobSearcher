"""
Gmail tool: leer emails de respuestas de trabajo y enviar follow-ups.
"""

import base64
import email as email_lib
from datetime import datetime
from typing import List, Dict, Any, Optional
from loguru import logger

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import os
import pickle

from config import settings

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
]


def _get_gmail_service():
    """Obtiene servicio autenticado de Gmail."""
    creds = None
    token_file = settings.gmail_token_file

    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                settings.gmail_credentials_file, SCOPES
            )
            creds = flow.run_local_server(port=8766, open_browser=True)
        with open(token_file, "w") as f:
            f.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)


def get_recent_job_emails(
    processed_ids: set,
    max_results: int = 50,
) -> List[Dict[str, Any]]:
    """
    Lee emails recientes que pueden ser respuestas de trabajo.

    Returns:
        Lista de emails con campos: message_id, thread_id, from, subject, body, date
    """
    try:
        service = _get_gmail_service()

        # Buscar emails de los últimos días con keywords de trabajo
        query = (
            "subject:(entrevista OR interview OR aplicacion OR application OR "
            "candidatura OR oferta OR position OR job OR vacancy OR "
            "recruitment OR recruiter OR hiring) "
            "newer_than:30d"
        )

        result = (
            service.users()
            .messages()
            .list(userId="me", q=query, maxResults=max_results)
            .execute()
        )

        messages = result.get("messages", [])
        emails = []

        for msg_ref in messages:
            msg_id = msg_ref["id"]
            if msg_id in processed_ids:
                continue

            try:
                msg = (
                    service.users()
                    .messages()
                    .get(userId="me", id=msg_id, format="full")
                    .execute()
                )
                parsed = _parse_message(msg)
                if parsed:
                    emails.append(parsed)
            except Exception as e:
                logger.warning(f"Error leyendo mensaje {msg_id}: {e}")

        logger.info(f"Encontrados {len(emails)} emails nuevos de trabajo")
        return emails

    except Exception as e:
        logger.error(f"Error accediendo a Gmail: {e}")
        return []


def _parse_message(msg: Dict) -> Optional[Dict[str, Any]]:
    """Parsea un mensaje de Gmail a dict estructurado."""
    try:
        headers = {h["name"]: h["value"] for h in msg["payload"].get("headers", [])}
        body = _extract_body(msg["payload"])

        return {
            "message_id": msg["id"],
            "thread_id": msg["threadId"],
            "from_address": headers.get("From", ""),
            "subject": headers.get("Subject", ""),
            "date": headers.get("Date", ""),
            "received_at": datetime.now().isoformat(),
            "content": body[:5000],
        }
    except Exception as e:
        logger.warning(f"Error parseando mensaje: {e}")
        return None


def _extract_body(payload: Dict) -> str:
    """Extrae el texto del body del mensaje."""
    body = ""

    if "parts" in payload:
        for part in payload["parts"]:
            if part["mimeType"] == "text/plain":
                data = part["body"].get("data", "")
                if data:
                    body = base64.urlsafe_b64decode(data).decode(
                        "utf-8", errors="replace"
                    )
                    break
            elif part["mimeType"] == "text/html" and not body:
                data = part["body"].get("data", "")
                if data:
                    html = base64.urlsafe_b64decode(data).decode(
                        "utf-8", errors="replace"
                    )
                    # Extraer texto simple del HTML
                    import re

                    body = re.sub(r"<[^>]+>", " ", html)
                    body = re.sub(r"\s+", " ", body).strip()
    else:
        data = payload.get("body", {}).get("data", "")
        if data:
            body = base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")

    return body


def send_email(
    to: str,
    subject: str,
    body: str,
    thread_id: Optional[str] = None,
    attachments: Optional[List[str]] = None,
) -> bool:
    """
    Envía un email. Si se provee thread_id, responde en el mismo hilo.
    Puede adjuntar archivos.

    Args:
        to: Destinatario
        subject: Asunto
        body: Cuerpo del email
        thread_id: ID del hilo para responder (opcional)
        attachments: Lista de rutas de archivos a adjuntar (opcional)

    Returns:
        True si se envió correctamente
    """
    try:
        service = _get_gmail_service()

        message = email_lib.message.EmailMessage()
        message["To"] = to
        message["From"] = settings.gmail_my_email
        message["Subject"] = subject
        message.set_content(body)

        if attachments:
            for file_path in attachments:
                if os.path.exists(file_path):
                    with open(file_path, "rb") as f:
                        file_data = f.read()
                    file_name = os.path.basename(file_path)
                    message.add_attachment(
                        file_data,
                        maintype="application",
                        subtype="octet-stream",
                        filename=file_name,
                    )
                    logger.info(f"Adjunto agregado: {file_name}")
                else:
                    logger.warning(f"Archivo no encontrado: {file_path}")

        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        msg_body = {"raw": raw}
        if thread_id:
            msg_body["threadId"] = thread_id

        service.users().messages().send(userId="me", body=msg_body).execute()
        logger.success(f"Email enviado a {to}: {subject}")
        return True

    except Exception as e:
        logger.error(f"Error enviando email a {to}: {e}")
        return False


def mark_as_read(message_id: str):
    """Marca un email como leído."""
    try:
        service = _get_gmail_service()
        service.users().messages().modify(
            userId="me",
            id=message_id,
            body={"removeLabelIds": ["UNREAD"]},
        ).execute()
    except Exception as e:
        logger.warning(f"No se pudo marcar como leído {message_id}: {e}")
