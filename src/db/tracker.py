"""
SQLite tracker para jobs, aplicaciones, emails y entrevistas.
"""
import sqlite3
import json
import threading
from datetime import datetime
from typing import Optional, List, Dict, Any
from loguru import logger
from config import settings

_db_lock = threading.Lock()


class JobTracker:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or settings.db_path
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=60, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=DELETE")
        conn.execute("PRAGMA busy_timeout=30000")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    def _init_db(self):
        with self._get_conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    company TEXT NOT NULL,
                    location TEXT,
                    description TEXT,
                    url TEXT,
                    salary TEXT,
                    source TEXT,
                    match_score INTEGER,
                    found_at TEXT DEFAULT (datetime('now')),
                    status TEXT DEFAULT 'found',
                    raw_data TEXT
                );

                CREATE TABLE IF NOT EXISTS applications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT NOT NULL,
                    applied_at TEXT DEFAULT (datetime('now')),
                    method TEXT,
                    cover_letter TEXT,
                    status TEXT DEFAULT 'applied',
                    FOREIGN KEY (job_id) REFERENCES jobs(id)
                );

                CREATE TABLE IF NOT EXISTS emails (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT,
                    gmail_thread_id TEXT,
                    gmail_message_id TEXT,
                    from_address TEXT,
                    subject TEXT,
                    received_at TEXT,
                    content TEXT,
                    sentiment TEXT,
                    action_taken TEXT,
                    followup_sent_at TEXT
                );

                CREATE TABLE IF NOT EXISTS interviews (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT NOT NULL,
                    email_id INTEGER,
                    scheduled_at TEXT,
                    calendar_event_id TEXT,
                    interviewer TEXT,
                    notes TEXT,
                    status TEXT DEFAULT 'scheduled',
                    FOREIGN KEY (job_id) REFERENCES jobs(id)
                );

                CREATE TABLE IF NOT EXISTS linkedin_conversations (
                    conversation_id TEXT PRIMARY KEY,
                    participant_name TEXT NOT NULL,
                    participant_profile_id TEXT,
                    participant_title TEXT,
                    profile_url TEXT,
                    job_id TEXT,
                    state TEXT DEFAULT 'new',
                    last_message_at INTEGER DEFAULT 0,
                    last_our_reply_at TEXT,
                    created_at TEXT DEFAULT (datetime('now')),
                    notes TEXT DEFAULT '',
                    FOREIGN KEY (job_id) REFERENCES jobs(id)
                );

                CREATE TABLE IF NOT EXISTS linkedin_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id TEXT NOT NULL,
                    message_text TEXT,
                    from_me INTEGER DEFAULT 0,
                    linkedin_timestamp INTEGER DEFAULT 0,
                    processed INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT (datetime('now')),
                    FOREIGN KEY (conversation_id) REFERENCES linkedin_conversations(conversation_id)
                );
            """)
            # Migraciones: agregar columnas nuevas si no existen
            self._migrate(conn)
        logger.debug(f"DB inicializada en {self.db_path}")

    def _migrate(self, conn):
        """Agrega columnas nuevas sin romper datos existentes."""
        migrations = [
            ("applications",        "pipeline_stage",  "TEXT DEFAULT 'applied'"),
            ("applications",        "verified",        "INTEGER DEFAULT 0"),
            ("applications",        "notes",           "TEXT DEFAULT ''"),
            ("applications",        "last_activity",   "TEXT"),
            ("applications",        "response_date",   "TEXT"),
            ("applications",        "rejection_reason","TEXT DEFAULT ''"),
            ("jobs",                "applied_url",     "TEXT DEFAULT ''"),
            # Quién respondió: 'pending' | 'auto' | 'alejandro' | 'skipped'
            ("emails",              "responded_by",    "TEXT DEFAULT 'pending'"),
            ("linkedin_messages",   "responded_by",    "TEXT DEFAULT 'pending'"),
        ]
        existing = {}
        for table, col, _ in migrations:
            if table not in existing:
                rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
                existing[table] = {r[1] for r in rows}
            if col not in existing[table]:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {_}")
                logger.debug(f"[migrate] {table}.{col} agregado")

    # --- JOBS ---

    def save_job(self, job: Dict[str, Any]) -> bool:
        """Guarda un job. Retorna True si es nuevo, False si ya existia."""
        with self._get_conn() as conn:
            existing = conn.execute(
                "SELECT id FROM jobs WHERE id = ?", (job["id"],)
            ).fetchone()
            if existing:
                return False
            conn.execute(
                """INSERT INTO jobs (id, title, company, location, description,
                   url, salary, source, match_score, raw_data)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    job["id"],
                    job.get("title", ""),
                    job.get("company", ""),
                    job.get("location", ""),
                    job.get("description", ""),
                    job.get("url", ""),
                    job.get("salary", ""),
                    job.get("source", ""),
                    job.get("match_score", 0),
                    json.dumps(job),
                ),
            )
            return True

    def update_job_status(self, job_id: str, status: str):
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE jobs SET status = ? WHERE id = ?", (status, job_id)
            )

    def get_job(self, job_id: str) -> Optional[Dict]:
        with self._get_conn() as conn:
            row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
            return dict(row) if row else None

    def get_jobs_by_status(self, status: str) -> List[Dict]:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM jobs WHERE status = ? ORDER BY found_at DESC", (status,)
            ).fetchall()
            return [dict(r) for r in rows]

    def get_all_jobs(self, limit: int = 2000) -> List[Dict]:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM jobs ORDER BY found_at DESC LIMIT ?", (limit,)
            ).fetchall()
            return [dict(r) for r in rows]

    def job_exists(self, job_id: str) -> bool:
        with self._get_conn() as conn:
            return bool(
                conn.execute(
                    "SELECT 1 FROM jobs WHERE id = ?", (job_id,)
                ).fetchone()
            )

    # --- APPLICATIONS ---

    def save_application(
        self, job_id: str, method: str = "linkedin", cover_letter: str = "",
        status: str = "applied"
    ) -> int:
        with _db_lock:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    """INSERT INTO applications (job_id, method, cover_letter, status)
                       VALUES (?, ?, ?, ?)""",
                    (job_id, method, cover_letter, status),
                )
                job_status = "applied" if status == "applied" else "pending_apply"
                conn.execute("UPDATE jobs SET status=? WHERE id=?", (job_status, job_id))
                return cursor.lastrowid

    def update_application_status(self, job_id: str, status: str):
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE applications SET status = ? WHERE job_id = ?",
                (status, job_id),
            )

    def get_applications_pending_followup(self) -> List[Dict]:
        """Jobs aplicados hace mas de FOLLOWUP_DAYS sin respuesta."""
        with self._get_conn() as conn:
            rows = conn.execute(
                f"""SELECT j.*, a.applied_at, a.id as app_id
                    FROM jobs j
                    JOIN applications a ON j.id = a.job_id
                    WHERE a.status = 'applied'
                    AND j.id NOT IN (SELECT DISTINCT job_id FROM emails WHERE job_id IS NOT NULL)
                    AND julianday('now') - julianday(a.applied_at) >= {settings.followup_days}"""
            ).fetchall()
            return [dict(r) for r in rows]

    # --- EMAILS ---

    def save_email(self, email_data: Dict[str, Any]) -> int:
        with self._get_conn() as conn:
            cursor = conn.execute(
                """INSERT INTO emails (job_id, gmail_thread_id, gmail_message_id,
                   from_address, subject, received_at, content, sentiment, action_taken)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    email_data.get("job_id"),
                    email_data.get("thread_id"),
                    email_data.get("message_id"),
                    email_data.get("from_address"),
                    email_data.get("subject"),
                    email_data.get("received_at", datetime.now().isoformat()),
                    email_data.get("content"),
                    email_data.get("sentiment"),
                    email_data.get("action_taken"),
                ),
            )
            return cursor.lastrowid

    def get_email_thread_history(self, gmail_thread_id: str) -> List[Dict]:
        """
        Retorna el hilo completo de un thread de Gmail: mensajes recibidos (emails)
        + mensajes enviados (sent_emails), ordenados cronológicamente.
        Cada dict tiene: body, from_me, subject, sent_at/received_at, from_address.
        """
        with self._get_conn() as conn:
            received = conn.execute(
                """SELECT content as body, 0 as from_me, subject,
                          received_at as ts, from_address
                   FROM emails WHERE gmail_thread_id = ?
                   ORDER BY received_at ASC""",
                (gmail_thread_id,),
            ).fetchall()
            sent = conn.execute(
                """SELECT body, 1 as from_me, subject,
                          sent_at as ts, 'alejandrohloza@gmail.com' as from_address
                   FROM sent_emails WHERE thread_id = ?
                   ORDER BY sent_at ASC""",
                (gmail_thread_id,),
            ).fetchall()

        all_msgs = [dict(r) for r in received] + [dict(r) for r in sent]
        all_msgs.sort(key=lambda x: x.get("ts") or "")
        return all_msgs

    def mark_followup_sent(self, email_id: int):
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE emails SET followup_sent_at = datetime('now') WHERE id = ?",
                (email_id,),
            )

    def get_processed_message_ids(self) -> set:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT gmail_message_id FROM emails WHERE gmail_message_id IS NOT NULL"
            ).fetchall()
            return {r["gmail_message_id"] for r in rows}

    def has_replied_to_thread(self, gmail_thread_id: str) -> bool:
        """Verifica si ya enviamos una respuesta en este thread de Gmail."""
        with self._get_conn() as conn:
            row = conn.execute(
                """SELECT 1 FROM emails
                   WHERE gmail_thread_id = ?
                   AND (followup_sent_at IS NOT NULL OR action_taken = 'send_followup')
                   LIMIT 1""",
                (gmail_thread_id,),
            ).fetchone()
            return row is not None

    # --- INTERVIEWS ---

    def save_interview(self, interview_data: Dict[str, Any]) -> int:
        with self._get_conn() as conn:
            cursor = conn.execute(
                """INSERT INTO interviews (job_id, email_id, scheduled_at,
                   calendar_event_id, interviewer, notes)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    interview_data.get("job_id"),
                    interview_data.get("email_id"),
                    interview_data.get("scheduled_at"),
                    interview_data.get("calendar_event_id"),
                    interview_data.get("interviewer"),
                    interview_data.get("notes"),
                ),
            )
            self.update_job_status(interview_data["job_id"], "interview_scheduled")
            return cursor.lastrowid

    # --- PIPELINE ---

    PIPELINE_STAGES = [
        "applied",          # aplicamos
        "viewed",           # empresa vio la aplicación
        "response",         # respondieron (positivo/neutral)
        "interview",        # entrevista agendada
        "technical_test",   # prueba técnica
        "offer",            # oferta recibida
        "accepted",         # aceptamos
        "rejected",         # rechazados
        "ghosted",          # sin respuesta tras followup
    ]

    def advance_pipeline(self, job_id: str, stage: str, notes: str = ""):
        """Avanza el pipeline de una aplicación a la siguiente etapa."""
        with _db_lock:
            with self._get_conn() as conn:
                conn.execute(
                    """UPDATE applications
                       SET pipeline_stage=?, last_activity=datetime('now'), notes=?
                       WHERE job_id=?""",
                    (stage, notes, job_id),
                )
                # Sincronizar status en jobs también
                job_status_map = {
                    "interview":      "interview_scheduled",
                    "offer":          "offer_received",
                    "accepted":       "accepted",
                    "rejected":       "rejected",
                    "ghosted":        "ghosted",
                }
                if stage in job_status_map:
                    conn.execute(
                        "UPDATE jobs SET status=? WHERE id=?",
                        (job_status_map[stage], job_id),
                    )

    def mark_verified(self, job_id: str, verified: bool = True):
        """Marca si la aplicación fue realmente enviada (verificado por email/LinkedIn)."""
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE applications SET verified=? WHERE job_id=?",
                (1 if verified else 0, job_id),
            )

    def add_note(self, job_id: str, note: str):
        """Agrega una nota a una aplicación."""
        with self._get_conn() as conn:
            conn.execute(
                """UPDATE applications
                   SET notes = COALESCE(notes,'') || char(10) || ?, last_activity=datetime('now')
                   WHERE job_id=?""",
                (f"[{datetime.now().strftime('%d/%m %H:%M')}] {note}", job_id),
            )

    def get_pipeline_summary(self) -> Dict[str, Any]:
        """Retorna conteo por etapa del pipeline."""
        with self._get_conn() as conn:
            rows = conn.execute(
                """SELECT pipeline_stage, COUNT(*) as n,
                          SUM(verified) as verified_n
                   FROM applications
                   GROUP BY pipeline_stage"""
            ).fetchall()
            stages = {r["pipeline_stage"]: {"total": r["n"], "verified": r["verified_n"] or 0}
                      for r in rows}
            # Verificados vs no verificados
            total = conn.execute("SELECT COUNT(*) FROM applications").fetchone()[0]
            verified = conn.execute("SELECT COUNT(*) FROM applications WHERE verified=1").fetchone()[0]
            return {
                "by_stage": stages,
                "total_applications": total,
                "verified_applications": verified,
                "unverified_applications": total - verified,
            }

    def get_full_pipeline(self, limit: int = 200) -> List[Dict]:
        """Retorna todas las aplicaciones con info completa para el dashboard."""
        with self._get_conn() as conn:
            rows = conn.execute(
                """SELECT
                    j.title, j.company, j.location, j.source, j.url,
                    j.match_score, j.salary, j.found_at,
                    a.id as app_id, a.applied_at, a.method, a.status,
                    a.pipeline_stage, a.verified, a.notes, a.last_activity,
                    a.response_date, a.rejection_reason,
                    (SELECT COUNT(*) FROM emails e WHERE e.job_id = j.id) as email_count,
                    (SELECT COUNT(*) FROM interviews i WHERE i.job_id = j.id) as interview_count
                   FROM applications a
                   JOIN jobs j ON a.job_id = j.id
                   ORDER BY a.applied_at DESC
                   LIMIT ?""",
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]

    # --- STATS ---

    def get_stats(self) -> Dict[str, Any]:
        with self._get_conn() as conn:
            total = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
            applied = conn.execute(
                "SELECT COUNT(*) FROM jobs WHERE status = 'applied'"
            ).fetchone()[0]
            interviews = conn.execute(
                "SELECT COUNT(*) FROM jobs WHERE status = 'interview_scheduled'"
            ).fetchone()[0]
            rejected = conn.execute(
                "SELECT COUNT(*) FROM jobs WHERE status = 'rejected'"
            ).fetchone()[0]
            return {
                "total_found": total,
                "applied": applied,
                "interviews_scheduled": interviews,
                "rejected": rejected,
                "pending": total - applied - interviews - rejected,
            }

    # --- LINKEDIN CONVERSATIONS ---

    CONVERSATION_STATES = ["new", "responded", "awaiting_reply", "escalated", "closed"]

    def save_linkedin_conversation(self, conv: Dict[str, Any]) -> bool:
        """Upsert conversación de LinkedIn. Retorna True si es nueva."""
        with self._get_conn() as conn:
            existing = conn.execute(
                "SELECT conversation_id FROM linkedin_conversations WHERE conversation_id=?",
                (conv["conversation_id"],),
            ).fetchone()
            if existing:
                conn.execute(
                    """UPDATE linkedin_conversations
                       SET participant_name=?, participant_title=?, last_message_at=?
                       WHERE conversation_id=?""",
                    (
                        conv.get("participant_name", ""),
                        conv.get("participant_title", ""),
                        conv.get("last_message_at", 0),
                        conv["conversation_id"],
                    ),
                )
                return False
            conn.execute(
                """INSERT INTO linkedin_conversations
                   (conversation_id, participant_name, participant_profile_id,
                    participant_title, profile_url, last_message_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    conv["conversation_id"],
                    conv.get("participant_name", ""),
                    conv.get("participant_profile_id", ""),
                    conv.get("participant_title", ""),
                    conv.get("profile_url", ""),
                    conv.get("last_message_at", 0),
                ),
            )
            return True

    def save_linkedin_message(self, msg: Dict[str, Any]) -> Optional[int]:
        """Guarda un mensaje. Retorna ID si es nuevo, None si ya existía."""
        with self._get_conn() as conn:
            # Dedup por conversation_id + linkedin_timestamp
            existing = conn.execute(
                """SELECT id FROM linkedin_messages
                   WHERE conversation_id=? AND linkedin_timestamp=? AND from_me=?""",
                (msg["conversation_id"], msg.get("linkedin_timestamp", 0), msg.get("from_me", 0)),
            ).fetchone()
            if existing:
                return None
            cursor = conn.execute(
                """INSERT INTO linkedin_messages
                   (conversation_id, message_text, from_me, linkedin_timestamp)
                   VALUES (?, ?, ?, ?)""",
                (
                    msg["conversation_id"],
                    msg.get("message_text", ""),
                    1 if msg.get("from_me") else 0,
                    msg.get("linkedin_timestamp", 0),
                ),
            )
            return cursor.lastrowid

    def get_unprocessed_conversations(self) -> List[Dict]:
        """Conversaciones con mensajes sin procesar."""
        with self._get_conn() as conn:
            rows = conn.execute(
                """SELECT DISTINCT c.*
                   FROM linkedin_conversations c
                   JOIN linkedin_messages m ON c.conversation_id = m.conversation_id
                   WHERE m.processed = 0 AND m.from_me = 0
                   AND c.state NOT IN ('closed', 'escalated')
                   ORDER BY c.last_message_at DESC"""
            ).fetchall()
            return [dict(r) for r in rows]

    def get_conversation_history(self, conversation_id: str, limit: int = 20) -> List[Dict]:
        """Mensajes de una conversación ordenados cronológicamente."""
        with self._get_conn() as conn:
            rows = conn.execute(
                """SELECT * FROM linkedin_messages
                   WHERE conversation_id=?
                   ORDER BY linkedin_timestamp ASC
                   LIMIT ?""",
                (conversation_id, limit),
            ).fetchall()
            return [dict(r) for r in rows]

    def update_conversation_state(self, conversation_id: str, state: str, notes: str = ""):
        """Actualiza estado de una conversación."""
        with self._get_conn() as conn:
            if notes:
                conn.execute(
                    """UPDATE linkedin_conversations
                       SET state=?, notes=COALESCE(notes,'') || char(10) || ?
                       WHERE conversation_id=?""",
                    (state, notes, conversation_id),
                )
            else:
                conn.execute(
                    "UPDATE linkedin_conversations SET state=? WHERE conversation_id=?",
                    (state, conversation_id),
                )

    def mark_messages_processed(self, conversation_id: str):
        """Marca todos los mensajes no procesados de una conversación como procesados."""
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE linkedin_messages SET processed=1 WHERE conversation_id=? AND processed=0",
                (conversation_id,),
            )

    def conversation_has_our_reply(self, conversation_id: str) -> bool:
        """Verifica si ya respondimos en esta conversación."""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT 1 FROM linkedin_messages WHERE conversation_id=? AND from_me=1 LIMIT 1",
                (conversation_id,),
            ).fetchone()
            return bool(row)

    def set_email_responded_by(self, email_id: int, responded_by: str) -> None:
        """Marca quién respondió este email. Valores: auto|alejandro|pending|skipped"""
        assert responded_by in ("auto", "alejandro", "pending", "skipped")
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE emails SET responded_by=? WHERE id=?",
                (responded_by, email_id),
            )

    def set_linkedin_message_responded_by(self, message_id: int, responded_by: str) -> None:
        """Marca quién respondió este mensaje LinkedIn. Valores: auto|alejandro|pending|skipped"""
        assert responded_by in ("auto", "alejandro", "pending", "skipped")
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE linkedin_messages SET responded_by=? WHERE id=?",
                (responded_by, message_id),
            )

    def get_last_incoming_linkedin_message_id(self, conversation_id: str) -> Optional[int]:
        """Retorna el ID del último mensaje entrante (from_me=0) en una conversación."""
        with self._get_conn() as conn:
            row = conn.execute(
                """SELECT id FROM linkedin_messages
                   WHERE conversation_id=? AND from_me=0
                   ORDER BY linkedin_timestamp DESC LIMIT 1""",
                (conversation_id,),
            ).fetchone()
            return row["id"] if row else None

    def record_our_reply(self, conversation_id: str, text: str):
        """Registra un mensaje enviado por nosotros."""
        import time as _time
        ts = int(_time.time() * 1000)
        self.save_linkedin_message({
            "conversation_id": conversation_id,
            "message_text": text,
            "from_me": True,
            "linkedin_timestamp": ts,
        })
        # Marcar como procesado inmediatamente
        with self._get_conn() as conn:
            conn.execute(
                """UPDATE linkedin_messages SET processed=1
                   WHERE conversation_id=? AND linkedin_timestamp=?""",
                (conversation_id, ts),
            )
            conn.execute(
                """UPDATE linkedin_conversations
                   SET state='responded', last_our_reply_at=datetime('now')
                   WHERE conversation_id=?""",
                (conversation_id,),
            )
