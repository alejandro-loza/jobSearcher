"""
Anti-Spam Agent — gatekeeper para todos los emails salientes.

Ningún email puede enviarse sin pasar por check_outgoing_email().
Decisiones posibles:
  SEND    — el email es legítimo, proceder
  BLOCK   — spam/duplicado/blocklist, no enviar
  APPROVE — enviar a WhatsApp para aprobación manual de Alejandro
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional

from loguru import logger

# ── Blocklists ────────────────────────────────────────────────────────────────

BLOCKED_ADDRESSES: set[str] = {
    "padma@ptechpartners.com",
    # Nathan Shen — recruiter de Audible. Alejandro maneja esta relación personalmente.
    "vsnathan@audible.com",
    # David Han — recruiting coordinator de Audible
    "davihany@audible.com",
    # Martha Carolina Ornelas — scheduling team Audible
    "mcaroloe@audible.com",
}

# Contactos personales — NUNCA enviar emails automáticos
BLOCKED_PERSONAL_NAMES: set[str] = {
    "sam lewis",
    "melba ruiz",
    "melba ruiz moron",
}

BLOCKED_KEYWORDS: set[str] = {
    "noreply", "no-reply", "do-not-reply", "donotreply",
    "notifications", "mailer", "bounce", "updates@e.mission",
    "ccsend.com", "hire.lever.co", "greenhouse-mail",
    "inmail-hit-reply", "hit-reply@linkedin",
}

# ── CVs aprobados (deben mencionar Thomson Reuters) ──────────────────────────

APPROVED_CV_PATHS: set[str] = {
    "data/cv_alejandro_es.pdf",
    "data/cv_alejandro_en.pdf",
    "/home/pinky/Descargas/_AlejandroATSResumeFull español.docx",
    "/home/pinky/Descargas/_AlejandroATSResumeFull español.pdf",
    "/home/pinky/Descargas/AlejandroATSResumeFull 2026.pdf",
}

CV_ARCHIVE_DIR = "/home/pinky/Descargas/cv_old"

# ── Límites ───────────────────────────────────────────────────────────────────

MAX_EMAILS_PER_RECIPIENT_7D = 2     # máximo 2 emails a la misma persona en 7 días
MAX_EMAILS_PER_THREAD = 1           # máximo 1 respuesta automática por thread


class Decision(Enum):
    SEND = "send"
    BLOCK = "block"
    APPROVE = "approve"   # escalar a WhatsApp


@dataclass
class SpamCheckResult:
    decision: Decision
    reason: str


# ── Helpers de DB ─────────────────────────────────────────────────────────────

def _get_sent_count_to_recipient(db_path: str, to: str, days: int = 7) -> int:
    """Cuenta emails enviados al mismo destinatario en los últimos N días."""
    try:
        since = (datetime.utcnow() - timedelta(days=days)).isoformat()
        with sqlite3.connect(db_path) as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM sent_emails WHERE to_address = ? AND sent_at >= ?",
                (to.lower(), since),
            ).fetchone()
            return row[0] if row else 0
    except Exception:
        return 0


def _get_sent_count_in_thread(db_path: str, thread_id: str) -> int:
    """Cuenta emails automáticos ya enviados en este thread."""
    try:
        with sqlite3.connect(db_path) as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM sent_emails WHERE thread_id = ?",
                (thread_id,),
            ).fetchone()
            return row[0] if row else 0
    except Exception:
        return 0


def _record_sent_email(
    db_path: str, to: str, subject: str, thread_id: Optional[str], body: str = ""
) -> None:
    """Registra un email enviado en la tabla sent_emails (incluyendo cuerpo)."""
    try:
        with sqlite3.connect(db_path) as conn:
            # Migración: agregar columna body si no existe
            cols = {r[1] for r in conn.execute("PRAGMA table_info(sent_emails)").fetchall()}
            if "body" not in cols:
                conn.execute("ALTER TABLE sent_emails ADD COLUMN body TEXT DEFAULT ''")
            conn.execute(
                "INSERT INTO sent_emails (to_address, subject, thread_id, body, sent_at) VALUES (?, ?, ?, ?, ?)",
                (to.lower(), subject, thread_id, body, datetime.utcnow().isoformat()),
            )
    except Exception as e:
        logger.warning(f"[antispam] Error registrando email enviado: {e}")


# ── Función principal ─────────────────────────────────────────────────────────

def check_attachments(attachments: list[str]) -> SpamCheckResult:
    """Verifica que los adjuntos sean CVs aprobados (con Thomson Reuters)."""
    import os
    for path in attachments:
        abs_path = os.path.abspath(path)
        # Bloquear si viene del directorio de CVs archivados
        if CV_ARCHIVE_DIR in abs_path:
            return SpamCheckResult(Decision.BLOCK, f"CV archivado no aprobado: {path}")
        # Bloquear si no está en la lista de CVs aprobados
        if path not in APPROVED_CV_PATHS and abs_path not in {os.path.abspath(p) for p in APPROVED_CV_PATHS}:
            return SpamCheckResult(Decision.BLOCK, f"CV no aprobado (sin Thomson Reuters): {path}")
    return SpamCheckResult(Decision.SEND, "OK")


def check_outgoing_email(
    to: str,
    subject: str,
    body: str,
    thread_id: Optional[str] = None,
    attachments: Optional[list[str]] = None,
    db_path: str = "data/jobsearcher.db",
) -> SpamCheckResult:
    """
    Verifica si un email debe enviarse, bloquearse o escalarse a aprobación.

    Args:
        to:        Destinatario
        subject:   Asunto
        body:      Cuerpo del email
        thread_id: ID del thread de Gmail (para dedup)
        db_path:   Ruta a la base de datos SQLite

    Returns:
        SpamCheckResult con Decision y razón
    """
    addr = to.lower().strip()

    # 1. Blocklist de direcciones específicas
    if addr in BLOCKED_ADDRESSES:
        return SpamCheckResult(Decision.BLOCK, f"Dirección bloqueada: {addr}")

    # 2. Blocklist de dominios/keywords (noreply, mailers, ATS)
    if any(kw in addr for kw in BLOCKED_KEYWORDS):
        return SpamCheckResult(Decision.BLOCK, f"Dominio de notificaciones bloqueado: {addr}")

    # 3. Dedup por thread — máximo 1 respuesta automática por thread
    if thread_id:
        sent_in_thread = _get_sent_count_in_thread(db_path, thread_id)
        if sent_in_thread >= MAX_EMAILS_PER_THREAD:
            return SpamCheckResult(
                Decision.BLOCK,
                f"Ya enviamos {sent_in_thread} email(s) en el thread {thread_id[:8]} — dedup",
            )

    # 4. Límite por destinatario — máximo 2 en 7 días
    sent_to_recipient = _get_sent_count_to_recipient(db_path, addr, days=7)
    if sent_to_recipient >= MAX_EMAILS_PER_RECIPIENT_7D:
        return SpamCheckResult(
            Decision.APPROVE,
            f"Ya enviamos {sent_to_recipient} emails a {addr} esta semana — requiere aprobación manual",
        )

    # 5. Validar adjuntos (CVs deben tener Thomson Reuters)
    if attachments:
        cv_check = check_attachments(attachments)
        if cv_check.decision != Decision.SEND:
            return cv_check

    # 6. Cuerpo vacío o muy corto
    if not body or len(body.strip()) < 20:
        return SpamCheckResult(Decision.BLOCK, "Cuerpo del email vacío o demasiado corto")

    return SpamCheckResult(Decision.SEND, "OK")


def record_sent(
    to: str,
    subject: str,
    thread_id: Optional[str] = None,
    body: str = "",
    db_path: str = "data/jobsearcher.db",
) -> None:
    """Registrar que se envió un email (llamar después de envío exitoso)."""
    _record_sent_email(db_path, to, subject, thread_id, body)
