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
                CREATE TABLE IF NOT EXISTS chat_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    tool_name TEXT,
                    created_at TEXT DEFAULT (datetime('now'))
                );

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

                CREATE TABLE IF NOT EXISTS external_apply_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT NOT NULL UNIQUE,
                    title TEXT,
                    company TEXT,
                    location TEXT,
                    url TEXT,
                    match_score INTEGER,
                    ats_type TEXT DEFAULT 'unknown',
                    priority INTEGER DEFAULT 50,
                    status TEXT DEFAULT 'pending',
                    attempts INTEGER DEFAULT 0,
                    last_attempt_at TEXT,
                    error_message TEXT,
                    handled_by TEXT,
                    created_at TEXT DEFAULT (datetime('now')),
                    completed_at TEXT,
                    FOREIGN KEY (job_id) REFERENCES jobs(id)
                );
                CREATE INDEX IF NOT EXISTS idx_ext_status ON external_apply_queue(status, priority DESC);

                -- Decisiones pendientes de aprobación manual (survive crashes)
                -- decision_type: 'job_confirm' | 'recruiter_reply' | 'slot_selection'
                CREATE TABLE IF NOT EXISTS pending_decisions (
                    id TEXT PRIMARY KEY,
                    decision_type TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at TEXT DEFAULT (datetime('now')),
                    expires_at TEXT
                );
            """)
            # Migraciones: agregar columnas nuevas si no existen
            self._migrate(conn)
        logger.debug(f"DB inicializada en {self.db_path}")

    # --- PENDING DECISIONS (survive crashes) ---

    def save_pending_decision(self, decision_id: str, decision_type: str, payload: dict, ttl_hours: int = 48):
        """Persiste una decisión pendiente en SQLite."""
        from datetime import timedelta
        expires = (datetime.now() + timedelta(hours=ttl_hours)).isoformat()
        with self._get_conn() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO pending_decisions (id, decision_type, payload, expires_at)
                   VALUES (?, ?, ?, ?)""",
                (decision_id, decision_type, json.dumps(payload, default=str), expires),
            )

    def delete_pending_decision(self, decision_id: str):
        """Elimina una decisión resuelta o cancelada."""
        with self._get_conn() as conn:
            conn.execute("DELETE FROM pending_decisions WHERE id = ?", (decision_id,))

    def get_pending_decisions(self, decision_type: str = None) -> List[Dict]:
        """Carga decisiones pendientes aún no expiradas."""
        with self._get_conn() as conn:
            if decision_type:
                rows = conn.execute(
                    """SELECT * FROM pending_decisions
                       WHERE decision_type = ?
                         AND (expires_at IS NULL OR datetime(expires_at) > datetime('now'))
                       ORDER BY created_at""",
                    (decision_type,),
                ).fetchall()
            else:
                rows = conn.execute(
                    """SELECT * FROM pending_decisions
                       WHERE expires_at IS NULL OR datetime(expires_at) > datetime('now')
                       ORDER BY created_at""",
                ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            try:
                d["payload"] = json.loads(d["payload"])
            except Exception:
                pass
            result.append(d)
        return result

    def clear_expired_decisions(self):
        """Limpia decisiones expiradas — llamar en startup."""
        with self._get_conn() as conn:
            cur = conn.execute(
                "DELETE FROM pending_decisions WHERE datetime(expires_at) < datetime('now')"
            )
            if cur.rowcount:
                logger.info(f"[tracker] {cur.rowcount} decisiones expiradas eliminadas")

    def _migrate(self, conn):
        """Agrega columnas nuevas sin romper datos existentes."""
        migrations = [
            ("applications", "pipeline_stage", "TEXT DEFAULT 'applied'"),
            ("applications", "verified", "INTEGER DEFAULT 0"),
            ("applications", "notes", "TEXT DEFAULT ''"),
            ("applications", "last_activity", "TEXT"),
            ("applications", "response_date", "TEXT"),
            ("applications", "rejection_reason", "TEXT DEFAULT ''"),
            ("jobs", "applied_url", "TEXT DEFAULT ''"),
            # Quién respondió: 'pending' | 'auto' | 'alejandro' | 'skipped'
            ("emails", "responded_by", "TEXT DEFAULT 'pending'"),
            ("linkedin_messages", "responded_by", "TEXT DEFAULT 'pending'"),
            # Application attempt tracking
            ("applications", "attempt_count", "INTEGER DEFAULT 1"),
            ("applications", "failure_reason", "TEXT DEFAULT ''"),
            ("applications", "apply_method_detail", "TEXT DEFAULT ''"),
            # Application queue / pipeline health
            ("jobs", "being_processed", "INTEGER DEFAULT 0"),
            ("jobs", "last_attempt_at", "TEXT"),
            ("jobs", "ghosted_at", "TEXT"),
            # Follow-up cadence tracking
            ("applications", "followup_count", "INTEGER DEFAULT 0"),
            ("applications", "last_followup_at", "TEXT"),
            ("applications", "last_response_at", "TEXT"),
            ("applications", "last_interview_at", "TEXT"),
            # ATS type for external portal agent
            ("jobs", "ats_type", "TEXT DEFAULT 'unknown'"),
            # Soft-archive: bandera lógica para "empezar fresco" sin borrar datos.
            # archived=1 saca al job del pipeline activo pero conserva la fila.
            ("jobs", "archived", "INTEGER DEFAULT 0"),
            ("jobs", "archived_at", "TEXT"),
            ("external_apply_queue", "archived", "INTEGER DEFAULT 0"),
            ("external_apply_queue", "archived_at", "TEXT"),
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
                   url, salary, source, match_score, raw_data, ats_type)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
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
                    job.get("ats_type", "unknown"),
                ),
            )
            return True

    def update_job_status(self, job_id: str, status: str):
        with self._get_conn() as conn:
            conn.execute("UPDATE jobs SET status = ? WHERE id = ?", (status, job_id))

    def update_job_score(self, job_id: str, score: int):
        """Persiste el match_score calculado por el LLM (paso scan→score→apply)."""
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE jobs SET match_score = ? WHERE id = ?", (int(score), job_id)
            )

    def get_unscored_jobs(self, limit: int = 40) -> List[Dict[str, Any]]:
        """
        Jobs que entraron por scan/discovery pero aún NO tienen score del LLM.
        Sentinela: match_score = 0 (el LLM nunca devuelve 0 salvo error, así que
        re-evaluar 0s reintenta fallos transitorios). Prioriza fuentes ATS-api
        (Greenhouse/Ashby/Lever) porque son las que el external_ats_agent puede
        aplicar sin riesgo de LinkedIn.
        """
        with self._get_conn() as conn:
            rows = conn.execute(
                """SELECT id, title, company, location, description, url, salary,
                          source, ats_type, match_score
                   FROM jobs
                   WHERE status = 'found'
                     AND COALESCE(match_score, 0) = 0
                     AND COALESCE(archived, 0) = 0
                     AND url IS NOT NULL AND url != ''
                   ORDER BY
                     CASE WHEN source IN ('greenhouse-api','lever-api','ashby-api')
                          THEN 0 ELSE 1 END,
                     found_at DESC
                   LIMIT ?""",
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]

    def archive_all_active(self) -> Dict[str, int]:
        """
        Soft-reset del pipeline: marca archived=1 en todas las vacantes actuales
        (tabla jobs y external_apply_queue) SIN borrar ninguna fila. Reversible con
        unarchive_all(). Las vacantes archivadas quedan fuera del pipeline activo
        pero siguen contando para dedup (job_exists), así que no reaparecen.
        """
        with self._get_conn() as conn:
            j = conn.execute(
                "UPDATE jobs SET archived = 1, archived_at = datetime('now') "
                "WHERE COALESCE(archived, 0) = 0"
            ).rowcount
            e = conn.execute(
                "UPDATE external_apply_queue SET archived = 1, archived_at = datetime('now') "
                "WHERE COALESCE(archived, 0) = 0"
            ).rowcount
        logger.info(f"[archive] {j} jobs y {e} externos marcados como archived (0 filas borradas)")
        return {"jobs_archived": j, "external_archived": e}

    def unarchive_all(self) -> Dict[str, int]:
        """Revierte archive_all_active: vuelve a activar todo lo archivado."""
        with self._get_conn() as conn:
            j = conn.execute(
                "UPDATE jobs SET archived = 0, archived_at = NULL WHERE COALESCE(archived, 0) = 1"
            ).rowcount
            e = conn.execute(
                "UPDATE external_apply_queue SET archived = 0, archived_at = NULL "
                "WHERE COALESCE(archived, 0) = 1"
            ).rowcount
        logger.info(f"[archive] revertido: {j} jobs y {e} externos reactivados")
        return {"jobs_unarchived": j, "external_unarchived": e}

    def get_job(self, job_id: str) -> Optional[Dict]:
        with self._get_conn() as conn:
            row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
            return dict(row) if row else None

    def get_jobs_by_status(self, status: str) -> List[Dict]:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM jobs WHERE status = ? AND COALESCE(archived, 0) = 0 "
                "ORDER BY found_at DESC",
                (status,),
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
                conn.execute("SELECT 1 FROM jobs WHERE id = ?", (job_id,)).fetchone()
            )

    def job_url_exists(self, url: str) -> bool:
        """Dedup por URL — evita guardar el mismo job desde distintas fuentes."""
        if not url:
            return False
        with self._get_conn() as conn:
            return bool(
                conn.execute(
                    "SELECT 1 FROM jobs WHERE url = ? LIMIT 1", (url,)
                ).fetchone()
            )

    # --- APPLICATION QUEUE (application_agent) ---

    def _is_cdmx_or_remote_mx(self, location: Optional[str]) -> bool:
        """
        True si la ubicación permite trabajar desde México.

        Delegado a portal_scanner.location_allows_mexico() — única fuente de
        verdad. "Remote" genérico ahora PASA: el scorer (evaluate_job_match)
        verifica en la descripción si el remoto está restringido a otro país
        (workable_from_mexico) y topa el score a 20 si lo está, así que un job
        con score>=75 ya viene vetado. La regla anterior ("Remote genérico →
        rechazado") era redundante con eso y además marcaba skip_location
        destruyendo la cola del external_ats_agent.
        """
        # Import perezoso — portal_scanner importa tracker a nivel de módulo.
        from src.tools.portal_scanner import location_allows_mexico

        return location_allows_mexico(location or "")

    def get_application_queue(
        self, min_score: int = 75, max_age_days: int = 14, limit: int = 50,
        easy_apply_only: bool = True,
        cdmx_only: bool = True,
    ) -> List[Dict]:
        """
        Retorna jobs listos para aplicar, ordenados por prioridad:
          1. match_score DESC (mejor match primero)
          2. found_at DESC (más reciente primero)

        Filtra:
          - status='found' (no aplicados todavía)
          - being_processed=0 (no bloqueados por otra ejecución)
          - score >= min_score
          - found_at dentro de max_age_days
          - tiene URL (sin URL no se puede aplicar automáticamente)
          - si easy_apply_only=True: solo jobs con easy_apply=True en raw_data
          - si cdmx_only=True: solo jobs en CDMX, remoto México, o sin location
        """
        with self._get_conn() as conn:
            rows = conn.execute(
                """SELECT * FROM jobs
                   WHERE status = 'found'
                     AND COALESCE(archived, 0) = 0
                     AND COALESCE(being_processed, 0) = 0
                     AND COALESCE(match_score, 0) >= ?
                     AND url IS NOT NULL AND url != ''
                     AND datetime(found_at) >= datetime('now', ?)
                   ORDER BY match_score DESC, found_at DESC
                   LIMIT ?""",
                (min_score, f"-{max_age_days} days", limit * 5),
            ).fetchall()

            import json as _json
            easy_apply_jobs = []
            external_jobs = []
            skipped_location = []
            for r in rows:
                d = dict(r)
                # Filtro de ubicación
                if cdmx_only and not self._is_cdmx_or_remote_mx(d.get("location")):
                    skipped_location.append(d)
                    continue
                # Filtro Easy Apply
                try:
                    raw = _json.loads(d.get("raw_data") or "{}")
                except Exception:
                    raw = {}
                if easy_apply_only:
                    if raw.get("easy_apply"):
                        easy_apply_jobs.append(d)
                    else:
                        external_jobs.append(d)
                else:
                    easy_apply_jobs.append(d)

            # Marcar jobs fuera de CDMX como skip (no volverlos a procesar)
            if skipped_location:
                self._mark_out_of_scope(skipped_location)

            # Enrutar externos a external_apply_queue
            if external_jobs:
                self._enqueue_externals(external_jobs)

            return easy_apply_jobs[:limit]

    def _mark_out_of_scope(self, jobs: List[Dict]) -> int:
        """Marca jobs fuera de CDMX como skip para que no vuelvan a la cola."""
        if not jobs:
            return 0
        with self._get_conn() as conn:
            ids = [j["id"] for j in jobs]
            placeholders = ",".join(["?"] * len(ids))
            conn.execute(
                f"UPDATE jobs SET status='skip_location' WHERE id IN ({placeholders}) AND status='found'",
                ids,
            )
        logger.info(f"[queue] {len(jobs)} jobs marcados como skip_location (fuera de CDMX/remoto MX)")
        return len(jobs)

    def _enqueue_externals(self, jobs: List[Dict]) -> int:
        """Mueve jobs externos a external_apply_queue para procesamiento manual/Antigravity."""
        if not jobs:
            return 0
        queued = 0
        with self._get_conn() as conn:
            for j in jobs:
                url_lower = (j.get("url") or "").lower()
                ats = "unknown"
                for name, patterns in {
                    "workday": ["myworkday.com", "workday.com"],
                    "greenhouse": ["boards.greenhouse.io", "grnh.se"],
                    "lever": ["jobs.lever.co"],
                    "ashby": ["jobs.ashbyhq.com"],
                    "linkedin_external": ["linkedin.com/jobs"],
                }.items():
                    if any(p in url_lower for p in patterns):
                        ats = name
                        break
                try:
                    cur = conn.execute(
                        """INSERT OR IGNORE INTO external_apply_queue
                           (job_id, title, company, location, url, match_score, ats_type, priority)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                        (j["id"], j.get("title"), j.get("company"), j.get("location"),
                         j.get("url"), j.get("match_score", 0), ats, j.get("match_score", 50)),
                    )
                    if cur.rowcount:
                        queued += 1
                        # Mark job as deferred (no tocamos 'found' para dedup del scanner)
                        conn.execute(
                            "UPDATE jobs SET status=?, ats_type=? WHERE id=?",
                            ("external_deferred", ats, j["id"]),
                        )
                except Exception as e:
                    logger.warning(f"[queue] fallo encolando external {j['id']}: {e}")
        if queued:
            logger.info(f"[queue] {queued} jobs externos → external_apply_queue")
        return queued

    def get_external_queue(self, min_score: int = 75, limit: int = 100) -> List[Dict]:
        """Retorna jobs externos pendientes para Antigravity/manual."""
        with self._get_conn() as conn:
            rows = conn.execute(
                """SELECT * FROM external_apply_queue
                   WHERE status = 'pending'
                     AND COALESCE(archived, 0) = 0
                     AND match_score >= ?
                   ORDER BY priority DESC, match_score DESC
                   LIMIT ?""",
                (min_score, limit),
            ).fetchall()
            return [dict(r) for r in rows]

    def mark_external_done(self, job_id: str, handled_by: str, status: str = "completed"):
        """Marca un job externo como procesado."""
        with self._get_conn() as conn:
            conn.execute(
                """UPDATE external_apply_queue
                   SET status = ?, handled_by = ?, completed_at = datetime('now')
                   WHERE job_id = ?""",
                (status, handled_by, job_id),
            )

    def lock_job_for_processing(self, job_id: str) -> bool:
        """
        Lock optimista: marca job como being_processed=1 si estaba en 0.
        Retorna True si lo logró tomar, False si ya estaba siendo procesado.
        """
        with _db_lock:
            with self._get_conn() as conn:
                cur = conn.execute(
                    """UPDATE jobs
                       SET being_processed = 1,
                           last_attempt_at = datetime('now')
                       WHERE id = ?
                         AND COALESCE(being_processed, 0) = 0""",
                    (job_id,),
                )
                return cur.rowcount > 0

    def release_job_lock(self, job_id: str):
        """Libera el lock de processing."""
        with self._get_conn() as conn:
            conn.execute("UPDATE jobs SET being_processed = 0 WHERE id = ?", (job_id,))

    def release_stale_locks(self, max_age_minutes: int = 30):
        """
        Libera locks que llevan más de N minutos — protege contra procesos
        que murieron sin limpiar. Debe correr al arrancar el orchestrator.
        """
        with self._get_conn() as conn:
            cur = conn.execute(
                """UPDATE jobs
                   SET being_processed = 0
                   WHERE being_processed = 1
                     AND datetime(last_attempt_at) < datetime('now', ?)""",
                (f"-{max_age_minutes} minutes",),
            )
            if cur.rowcount:
                logger.warning(f"[tracker] Liberados {cur.rowcount} locks stale")

    def cleanup_stale_jobs(self, max_age_days: int = 14) -> Dict[str, int]:
        """
        Elimina jobs stale (status='found', >max_age_days) que nunca se aplicaron.
        Solo borra jobs sin aplicaciones asociadas para no perder historial.
        Retorna conteo de jobs eliminados y aplicaciones huérfanas limpiadas.
        """
        with _db_lock:
            with self._get_conn() as conn:
                stale_ids = conn.execute(
                    """SELECT j.id FROM jobs j
                       LEFT JOIN applications a ON a.job_id = j.id
                       WHERE j.status = 'found'
                         AND datetime(j.found_at) < datetime('now', ?)
                         AND a.id IS NULL""",
                    (f"-{max_age_days} days",),
                ).fetchall()
                stale_ids = [r[0] for r in stale_ids]

                if not stale_ids:
                    logger.info("[tracker] cleanup: no stale jobs found")
                    return {"deleted": 0}

                placeholders = ",".join("?" * len(stale_ids))
                conn.execute(
                    f"DELETE FROM jobs WHERE id IN ({placeholders})", stale_ids
                )
                logger.info(
                    f"[tracker] cleanup: deleted {len(stale_ids)} stale jobs (>{max_age_days}d)"
                )
                return {"deleted": len(stale_ids)}

    def mark_stale_as_expired(self, max_age_days: int = 14) -> Dict[str, int]:
        """
        Marca jobs stale como 'expired' en vez de borrarlos (preserva historial).
        Jobs con status='found' y found_at > max_age_days se marcan 'expired'.
        """
        with _db_lock:
            with self._get_conn() as conn:
                cur = conn.execute(
                    """UPDATE jobs
                       SET status = 'expired'
                       WHERE status = 'found'
                         AND datetime(found_at) < datetime('now', ?)""",
                    (f"-{max_age_days} days",),
                )
                count = cur.rowcount
                if count:
                    logger.info(
                        f"[tracker] marked {count} stale jobs as 'expired' (>{max_age_days}d)"
                    )
                return {"marked_expired": count}

    def count_applications_today(self) -> int:
        """Número de aplicaciones exitosas del día actual (para rate limit diario)."""
        with self._get_conn() as conn:
            row = conn.execute(
                """SELECT COUNT(*) FROM applications
                   WHERE status = 'applied'
                     AND date(applied_at) = date('now')"""
            ).fetchone()
            return int(row[0]) if row else 0

    def mark_job_ghosted(self, job_id: str, notes: str = ""):
        """Marca un job como ghosted (sin respuesta tras N días)."""
        with self._get_conn() as conn:
            conn.execute(
                """UPDATE jobs
                   SET status = 'ghosted', ghosted_at = datetime('now')
                   WHERE id = ?""",
                (job_id,),
            )
            conn.execute(
                """UPDATE applications
                   SET status = 'ghosted', last_activity = datetime('now'),
                       notes = COALESCE(notes, '') || ?
                   WHERE job_id = ?""",
                (f" | ghosted: {notes}" if notes else " | ghosted", job_id),
            )

    def get_full_pipeline_for_job(self, job_id: str) -> List[Dict]:
        """Historial de aplicaciones para un job específico (para timeline)."""
        with self._get_conn() as conn:
            rows = conn.execute(
                """SELECT * FROM applications
                   WHERE job_id = ?
                   ORDER BY applied_at DESC""",
                (job_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    # --- CHAT HISTORY (ai_orchestrator_agent) ---

    def save_chat_message(self, role: str, content: str, tool_name: str = None):
        """Guarda un mensaje en el historial de conversación."""
        with self._get_conn() as conn:
            conn.execute(
                """INSERT INTO chat_history (role, content, tool_name)
                   VALUES (?, ?, ?)""",
                (role, content, tool_name),
            )

    def get_chat_history(self, limit: int = 20) -> List[Dict]:
        """Retorna los últimos N mensajes del historial."""
        with self._get_conn() as conn:
            rows = conn.execute(
                """SELECT role, content, tool_name, created_at
                   FROM chat_history
                   ORDER BY id DESC
                   LIMIT ?""",
                (limit,),
            ).fetchall()
            return list(reversed([dict(r) for r in rows]))

    def clear_chat_history(self):
        """Limpia el historial (útil para reset manual)."""
        with self._get_conn() as conn:
            conn.execute("DELETE FROM chat_history")

    # --- PIPELINE HEALTH (pipeline_health_agent) ---

    def get_emails_for_job(self, job_id: str) -> List[Dict]:
        """Emails asociados directamente a un job_id."""
        with self._get_conn() as conn:
            rows = conn.execute(
                """SELECT * FROM emails
                   WHERE job_id = ?
                   ORDER BY received_at DESC""",
                (job_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_emails_by_company(self, company: str, days: int = 30) -> List[Dict]:
        """
        Emails cuyo 'from_address' contiene el nombre de la empresa
        (match por dominio aproximado). Útil cuando no hay job_id directo.
        """
        with self._get_conn() as conn:
            # Dominio simplificado: primera palabra de company, sin espacios, minúsculas
            domain_hint = company.split()[0].lower() if company else ""
            rows = conn.execute(
                """SELECT * FROM emails
                   WHERE (LOWER(from_address) LIKE ?
                          OR LOWER(subject) LIKE ?
                          OR LOWER(content) LIKE ?)
                     AND datetime(received_at) >= datetime('now', ?)
                   ORDER BY received_at DESC""",
                (
                    f"%{domain_hint}%",
                    f"%{company.lower()}%",
                    f"%{company.lower()}%",
                    f"-{days} days",
                ),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_conversations_by_company(self, company: str) -> List[Dict]:
        """
        Conversaciones de LinkedIn donde el participante menciona la empresa
        en su título/headline (ej. "Recruiter at Audible").
        """
        with self._get_conn() as conn:
            rows = conn.execute(
                """SELECT * FROM linkedin_conversations
                   WHERE LOWER(participant_title) LIKE ?
                   ORDER BY last_message_at DESC""",
                (f"%{company.lower()}%",),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_interviews_for_job(self, job_id: str) -> List[Dict]:
        """Entrevistas agendadas para un job (cualquier status)."""
        with self._get_conn() as conn:
            rows = conn.execute(
                """SELECT * FROM interviews
                   WHERE job_id = ?
                   ORDER BY scheduled_at DESC""",
                (job_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    def days_since_applied(self, job_id: str) -> Optional[int]:
        """Retorna días desde que se aplicó a un job (None si no se ha aplicado)."""
        with self._get_conn() as conn:
            row = conn.execute(
                """SELECT julianday('now') - julianday(applied_at) AS days
                   FROM applications WHERE job_id = ?
                   ORDER BY applied_at DESC LIMIT 1""",
                (job_id,),
            ).fetchone()
            return int(row[0]) if row and row[0] is not None else None

    # --- APPLICATIONS ---

    # Application status values:
    #   applied          - aplicación enviada exitosamente
    #   apply_attempted  - se intentó aplicar (en progreso)
    #   apply_failed     - falló el intento (browser error, form error)
    #   apply_captcha    - detenido por captcha
    #   apply_needs_manual - requiere intervención manual
    #   apply_blocked    - portal bloqueó la aplicación
    #   rejected         - empresa rechazó
    #   interview        - avanzó a entrevista
    #   offer            - recibió oferta

    def save_application(
        self,
        job_id: str,
        method: str = "linkedin",
        cover_letter: str = "",
        status: str = "applied",
        failure_reason: str = "",
        method_detail: str = "",
    ) -> int:
        with _db_lock:
            with self._get_conn() as conn:
                # Check if there's already an application for this job
                existing = conn.execute(
                    "SELECT id, attempt_count FROM applications WHERE job_id = ?",
                    (job_id,),
                ).fetchone()

                if existing:
                    # Update existing application with new attempt
                    attempt = (existing[1] or 1) + 1
                    conn.execute(
                        """UPDATE applications
                           SET status=?, method=?, failure_reason=?,
                               apply_method_detail=?, attempt_count=?,
                               last_activity=datetime('now')
                           WHERE job_id=?""",
                        (
                            status,
                            method,
                            failure_reason,
                            method_detail,
                            attempt,
                            job_id,
                        ),
                    )
                    app_id = existing[0]
                else:
                    cursor = conn.execute(
                        """INSERT INTO applications
                           (job_id, method, cover_letter, status, failure_reason,
                            apply_method_detail, attempt_count, last_activity)
                           VALUES (?, ?, ?, ?, ?, ?, 1, datetime('now'))""",
                        (
                            job_id,
                            method,
                            cover_letter,
                            status,
                            failure_reason,
                            method_detail,
                        ),
                    )
                    app_id = cursor.lastrowid

                # Update job status to match
                JOB_STATUS_MAP = {
                    "applied": "applied",
                    "apply_attempted": "applying",
                    "apply_failed": "apply_failed",
                    "apply_captcha": "apply_needs_manual",
                    "apply_needs_manual": "apply_needs_manual",
                    "apply_blocked": "apply_failed",
                    "interview": "interview",
                    "offer": "offer",
                    "rejected": "rejected",
                }
                job_status = JOB_STATUS_MAP.get(status, "found")
                conn.execute(
                    "UPDATE jobs SET status=? WHERE id=?", (job_status, job_id)
                )
                return app_id

    def update_application_status(
        self, job_id: str, status: str, failure_reason: str = ""
    ):
        with self._get_conn() as conn:
            conn.execute(
                """UPDATE applications
                   SET status=?, failure_reason=?, last_activity=datetime('now')
                   WHERE job_id=?""",
                (status, failure_reason, job_id),
            )
            # Also update job status
            JOB_STATUS_MAP = {
                "applied": "applied",
                "apply_failed": "apply_failed",
                "apply_needs_manual": "apply_needs_manual",
                "interview": "interview",
                "offer": "offer",
                "rejected": "rejected",
            }
            job_status = JOB_STATUS_MAP.get(status)
            if job_status:
                conn.execute(
                    "UPDATE jobs SET status=? WHERE id=?", (job_status, job_id)
                )

    def get_failed_applications(self) -> List[Dict]:
        """Jobs donde falló la aplicación automática."""
        with self._get_conn() as conn:
            rows = conn.execute(
                """SELECT j.*, a.status as app_status, a.failure_reason,
                          a.method, a.attempt_count, a.apply_method_detail
                   FROM jobs j
                   JOIN applications a ON j.id = a.job_id
                   WHERE a.status IN ('apply_failed', 'apply_captcha',
                                      'apply_needs_manual', 'apply_blocked')
                   ORDER BY a.last_activity DESC"""
            ).fetchall()
            return [dict(r) for r in rows]

    def get_application_stats(self) -> Dict:
        """Estadísticas de aplicaciones por status."""
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT status, COUNT(*) as count FROM applications GROUP BY status"
            ).fetchall()
            stats = {r[0]: r[1] for r in rows}
            stats["total"] = sum(stats.values())
            return stats

    def get_applications_pending_followup(self) -> List[Dict]:
        """Jobs aplicados hace mas de FOLLOWUP_DAYS sin respuesta (legacy)."""
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

    def get_applications_with_cadence_context(self) -> List[Dict]:
        """
        Retorna aplicaciones activas con los campos que necesita followup_cadence.decide():
        status, applied_at, last_followup_at, last_response_at, last_interview_at,
        followup_count. Incluye datos del job para el master_agent.
        """
        with self._get_conn() as conn:
            rows = conn.execute(
                """SELECT j.*, a.applied_at, a.id as app_id, a.status,
                          a.followup_count, a.last_followup_at,
                          a.last_response_at, a.last_interview_at,
                          (SELECT GROUP_CONCAT(from_address)
                             FROM emails e WHERE e.job_id = j.id) AS emails_in_job
                   FROM jobs j
                   JOIN applications a ON j.id = a.job_id
                   WHERE a.status IN ('applied', 'responded', 'interview')"""
            ).fetchall()
            return [dict(r) for r in rows]

    def record_followup_sent(self, app_id: int) -> None:
        """Registra un follow-up enviado: incrementa contador + fecha."""
        with self._get_conn() as conn:
            conn.execute(
                """UPDATE applications
                   SET followup_count = COALESCE(followup_count, 0) + 1,
                       last_followup_at = datetime('now')
                   WHERE id = ?""",
                (app_id,),
            )

    def record_response_received(self, job_id: str) -> None:
        """Marca que llegó respuesta del reclutador para este job."""
        with self._get_conn() as conn:
            conn.execute(
                """UPDATE applications
                   SET status = 'responded',
                       last_response_at = datetime('now')
                   WHERE job_id = ? AND status = 'applied'""",
                (job_id,),
            )

    def record_interview_completed(self, job_id: str) -> None:
        """Marca que se completó una entrevista para este job."""
        with self._get_conn() as conn:
            conn.execute(
                """UPDATE applications
                   SET status = 'interview',
                       last_interview_at = datetime('now')
                   WHERE job_id = ?""",
                (job_id,),
            )

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
        "applied",  # aplicamos
        "viewed",  # empresa vio la aplicación
        "response",  # respondieron (positivo/neutral)
        "interview",  # entrevista agendada
        "technical_test",  # prueba técnica
        "offer",  # oferta recibida
        "accepted",  # aceptamos
        "rejected",  # rechazados
        "ghosted",  # sin respuesta tras followup
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
                    "interview": "interview_scheduled",
                    "offer": "offer_received",
                    "accepted": "accepted",
                    "rejected": "rejected",
                    "ghosted": "ghosted",
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
            stages = {
                r["pipeline_stage"]: {"total": r["n"], "verified": r["verified_n"] or 0}
                for r in rows
            }
            # Verificados vs no verificados
            total = conn.execute("SELECT COUNT(*) FROM applications").fetchone()[0]
            verified = conn.execute(
                "SELECT COUNT(*) FROM applications WHERE verified=1"
            ).fetchone()[0]
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
            ghosted = conn.execute(
                "SELECT COUNT(*) FROM jobs WHERE status = 'ghosted'"
            ).fetchone()[0]
            active = conn.execute(
                """SELECT COUNT(*) FROM jobs WHERE status IN
                   ('interview_scheduled','offer_received','applying')"""
            ).fetchone()[0]
            return {
                "total_found": total,
                "applied": applied,
                "interviews_scheduled": interviews,
                "rejected": rejected,
                "ghosted": ghosted,
                "active_processes": active,
                "pending": total - applied - interviews - rejected - ghosted,
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
                (
                    msg["conversation_id"],
                    msg.get("linkedin_timestamp", 0),
                    msg.get("from_me", 0),
                ),
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

    def get_conversation_history(
        self, conversation_id: str, limit: int = 20
    ) -> List[Dict]:
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

    def update_conversation_state(
        self, conversation_id: str, state: str, notes: str = ""
    ):
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

    def set_linkedin_message_responded_by(
        self, message_id: int, responded_by: str
    ) -> None:
        """Marca quién respondió este mensaje LinkedIn. Valores: auto|alejandro|pending|skipped"""
        assert responded_by in ("auto", "alejandro", "pending", "skipped")
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE linkedin_messages SET responded_by=? WHERE id=?",
                (responded_by, message_id),
            )

    def get_last_incoming_linkedin_message_id(
        self, conversation_id: str
    ) -> Optional[int]:
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
        self.save_linkedin_message(
            {
                "conversation_id": conversation_id,
                "message_text": text,
                "from_me": True,
                "linkedin_timestamp": ts,
            }
        )
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
