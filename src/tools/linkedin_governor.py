"""
LinkedIn Activity Governor — punto único de control anti-ban.

LinkedIn banea por el comportamiento TOTAL de la cuenta, no por acción individual.
Este módulo es el ÚNICO choke point por el que debe pasar cualquier acción de
LinkedIn (search, apply, leer/enviar mensajes, connect, post). Registra cada
acción en un ledger SQLite y hace cumplir en un solo lugar:

  - caps por tipo de acción (día + hora)
  - gap mínimo entre acciones del mismo tipo (evita ráfagas de bot)
  - presupuesto global de la cuenta (la suma de todas las acciones interactivas)
  - horario humano por tipo (writes 9-19 L-V; reads 8-21 diario)
  - jitter humano no-mecánico
  - estado de ban / recovery a nivel cuenta (histórico persistido en JSON)
  - User-Agent único compartido por todos los módulos

Uso típico:

    from src.tools import linkedin_governor as gov

    ok, reason = gov.can_act(gov.APPLY)
    if not ok:
        logger.info(f"[gov] skip apply: {reason}")
        return
    gov.human_delay(gov.APPLY)          # o await gov.human_delay_async(...)
    ...   # ejecutar la acción
    gov.record_action(gov.APPLY, meta=job_id)

Diseño fail-closed: ante cualquier duda, can_act() devuelve False.
"""

from __future__ import annotations

import asyncio
import json
import os
import random
import sqlite3
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Tuple

from loguru import logger

from config import settings

# ── User-Agent único (todos los módulos deben usar este) ─────────────────────
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

# ── Tipos de acción ──────────────────────────────────────────────────────────
SEARCH = "search"
APPLY = "apply"
MSG_READ = "msg_read"
MSG_SEND = "msg_send"
CONNECT = "connect"
POST = "post"
LOGIN = "login"
PASSIVE = "passive"  # lectura benigna de cobertura (feed/notifs) — equilibra la mezcla

# Acciones que cuentan contra el presupuesto global de la cuenta.
# (LOGIN y MSG_READ no son "interactivas" de escritura, pero sí suman huella;
#  las incluimos con techo propio pero no en el global de escritura.)
_INTERACTIVE = {APPLY, MSG_SEND, CONNECT, POST}

# ── Políticas por tipo ───────────────────────────────────────────────────────
# per_day, per_hour, gap_min (minutos entre acciones del mismo tipo),
# hours (rango horario permitido), business_days_only
_POLICY: Dict[str, Dict] = {
    APPLY:    {"per_day": 8,  "per_hour": 3, "gap_min": 8,  "hours": (9, 19),  "biz_days": True},
    MSG_SEND: {"per_day": 15, "per_hour": 5, "gap_min": 3,  "hours": (9, 19),  "biz_days": True},
    MSG_READ: {"per_day": 12, "per_hour": 2, "gap_min": 75, "hours": (8, 21),  "biz_days": False},
    CONNECT:  {"per_day": 5,  "per_hour": 3, "gap_min": 10, "hours": (9, 19),  "biz_days": True},
    POST:     {"per_day": 3,  "per_hour": 1, "gap_min": 90, "hours": (9, 19),  "biz_days": True},
    SEARCH:   {"per_day": 12, "per_hour": 3, "gap_min": 20, "hours": (8, 21),  "biz_days": False},
    LOGIN:    {"per_day": 4,  "per_hour": 2, "gap_min": 30, "hours": (7, 22),  "biz_days": False},
    PASSIVE:  {"per_day": 6,  "per_hour": 2, "gap_min": 45, "hours": (8, 22),  "biz_days": False},
}

# Techo global de acciones interactivas de escritura por día.
GLOBAL_INTERACTIVE_PER_DAY = 35

# Jitter (segundos) antes de ejecutar cada tipo de acción. Rango amplio y
# no-lineal a propósito: el objetivo es que los intervalos NO sean mecánicos.
_JITTER: Dict[str, Tuple[float, float]] = {
    APPLY:    (90, 240),
    MSG_SEND: (20, 60),
    MSG_READ: (5, 20),
    CONNECT:  (30, 90),
    POST:     (15, 45),
    SEARCH:   (5, 25),
    LOGIN:    (2, 6),
    PASSIVE:  (8, 30),
}

BUSINESS_DAYS = {0, 1, 2, 3, 4}  # lun-vie

BAN_HISTORY_FILE = "data/linkedin_ban_history.json"
DEFAULT_DAILY_CAP = 8  # cap de apply en modo normal (referencia para recovery)

# Estados de resultado que indican posible ban (usado por callers).
BAN_SIGNALS = {"auth_failed", "linkedin_auth_failed", "blocked", "restricted"}


# ── Ledger (SQLite) ──────────────────────────────────────────────────────────

def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(settings.db_path, timeout=60, check_same_thread=False)
    conn.execute("PRAGMA busy_timeout=30000")
    return conn


def _ensure_table() -> None:
    with _conn() as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS linkedin_activity (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   kind TEXT NOT NULL,
                   at TEXT NOT NULL DEFAULT (datetime('now')),
                   meta TEXT DEFAULT ''
               )"""
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_li_activity_kind_at ON linkedin_activity(kind, at)"
        )


_ensure_table()


def _count(kind: Optional[str], since_sql: str) -> int:
    with _conn() as conn:
        if kind is None:
            placeholders = ",".join("?" for _ in _INTERACTIVE)
            row = conn.execute(
                f"SELECT COUNT(*) FROM linkedin_activity "
                f"WHERE kind IN ({placeholders}) AND at >= {since_sql}",
                tuple(_INTERACTIVE),
            ).fetchone()
        else:
            row = conn.execute(
                f"SELECT COUNT(*) FROM linkedin_activity "
                f"WHERE kind = ? AND at >= {since_sql}",
                (kind,),
            ).fetchone()
        return int(row[0]) if row else 0


def _last_action_at(kind: str) -> Optional[datetime]:
    """Última acción del tipo, convertida a hora LOCAL.

    El ledger guarda `at` con el DEFAULT datetime('now') de SQLite, que es UTC.
    Los consumidores en Python comparan contra datetime.now() (local), así que
    convertimos UTC→local aquí. Sin esta conversión el gap salía negativo
    (~-6h en CDMX) y bloqueaba cada acción ~6h de más.
    """
    with _conn() as conn:
        row = conn.execute(
            "SELECT at FROM linkedin_activity WHERE kind = ? ORDER BY at DESC LIMIT 1",
            (kind,),
        ).fetchone()
    if not row or not row[0]:
        return None
    try:
        parsed = datetime.fromisoformat(row[0])
    except ValueError:
        # SQLite datetime('now') → 'YYYY-MM-DD HH:MM:SS'
        try:
            parsed = datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return None
    # UTC (naive) → local (naive)
    return (
        parsed.replace(tzinfo=timezone.utc).astimezone().replace(tzinfo=None)
    )


def record_action(kind: str, meta: str = "") -> None:
    """Registra una acción ejecutada en el ledger."""
    try:
        with _conn() as conn:
            conn.execute(
                "INSERT INTO linkedin_activity (kind, meta) VALUES (?, ?)",
                (kind, str(meta)[:200]),
            )
    except Exception as e:
        logger.error(f"[gov] no se pudo registrar acción {kind}: {e}")


def counts_today() -> Dict[str, int]:
    """Conteo por tipo del día actual (para dashboard / diagnóstico)."""
    with _conn() as conn:
        rows = conn.execute(
            "SELECT kind, COUNT(*) FROM linkedin_activity "
            "WHERE date(at) = date('now') GROUP BY kind"
        ).fetchall()
    out = {r[0]: int(r[1]) for r in rows}
    out["_global_interactive"] = _count(None, "datetime('now','-1 day')")
    return out


# ── Ban / recovery (a nivel cuenta) ──────────────────────────────────────────

def _load_ban_history() -> Dict:
    try:
        with open(BAN_HISTORY_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {
            "ban_count": 0,
            "last_ban_at": None,
            "current_state": "ok",       # ok | banned | recovering
            "recovery_mode": False,
            "recovery_daily_limit": DEFAULT_DAILY_CAP,
            "recovery_resume_at": None,
            "ban_events": [],
        }


def _save_ban_history(history: Dict) -> None:
    os.makedirs(os.path.dirname(BAN_HISTORY_FILE), exist_ok=True)
    with open(BAN_HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2, default=str)


def is_banned() -> Tuple[bool, Optional[str]]:
    """Retorna (está_baneado, resume_at_iso). Transiciona a recovery si venció."""
    history = _load_ban_history()
    if history.get("current_state") != "banned":
        return False, None
    resume_at = history.get("recovery_resume_at")
    if not resume_at:
        return True, None
    try:
        resume_dt = datetime.fromisoformat(resume_at)
    except ValueError:
        return True, None
    if datetime.now() < resume_dt:
        return True, resume_at
    history["current_state"] = "recovering"
    history["recovery_mode"] = True
    history["recovery_daily_limit"] = 10
    _save_ban_history(history)
    logger.warning("[gov] Periodo de ban pasó → modo recovery (10 apps/día)")
    return False, None


def record_ban(reason: str, status: str, notify=None) -> None:
    """Marca ban en history y programa recovery. `notify(msg)` opcional."""
    history = _load_ban_history()
    history["ban_count"] = int(history.get("ban_count", 0)) + 1
    history["last_ban_at"] = datetime.now().isoformat()
    history["current_state"] = "banned"
    history["recovery_mode"] = True

    count = history["ban_count"]
    if count == 1:
        hours = 48
        history["recovery_daily_limit"] = 10
    elif count == 2:
        hours = 24 * 7
        history["recovery_daily_limit"] = 20
    else:
        hours = 24 * 30
        history["recovery_daily_limit"] = 0

    history["recovery_resume_at"] = (datetime.now() + timedelta(hours=hours)).isoformat()
    history["ban_events"].append({
        "at": datetime.now().isoformat(),
        "reason": reason,
        "status": status,
        "pause_hours": hours,
    })
    _save_ban_history(history)

    msg = (
        f"⚠️ LinkedIn detectó actividad (ban #{count}).\n"
        f"Pausa: {hours}h.\nRazón: {reason}\nStatus: {status}\n"
        f"Reanuda: {history['recovery_resume_at']}"
    )
    logger.error(f"[gov] {msg}")
    if notify:
        try:
            notify(msg)
        except Exception as e:
            logger.error(f"[gov] no se pudo notificar ban: {e}")


def record_successful_apply() -> None:
    """Cada éxito durante recovery acerca al límite normal."""
    history = _load_ban_history()
    if not history.get("recovery_mode"):
        return
    cap = int(history.get("recovery_daily_limit", 10))
    if cap >= DEFAULT_DAILY_CAP:
        history["recovery_mode"] = False
        history["current_state"] = "ok"
        history["recovery_daily_limit"] = DEFAULT_DAILY_CAP
        logger.success("[gov] Recovery completa — modo normal restaurado")
    _save_ban_history(history)


# ── Cap diario efectivo (aleatorización determinista + días ligeros + warmup) ──

# Duración del warmup tras (re)activar la cuenta: los caps escalan de
# WARMUP_FLOOR a 1.0 durante estos días.
WARMUP_DAYS = 28
WARMUP_FLOOR = 0.4


def _date_seed(kind: str, d) -> "random.Random":
    """RNG determinista por (fecha, tipo): mismo valor durante todo el día, distinto
    día a día. Evita el patrón mecánico de un cap fijo sin introducir aleatoriedad
    que rompa la idempotencia dentro del mismo día."""
    return random.Random(f"{d.isoformat()}::{kind}")


def _is_light_day(d) -> bool:
    """1-2 días/semana (deterministas) son 'ligeros'. Nunca golpear el cap 7/7 días
    es justo lo que recomiendan las prácticas 2026."""
    wr = random.Random(f"lightweek::{d.isocalendar()[0]}::{d.isocalendar()[1]}")
    light = set(wr.sample(range(7), k=wr.choice([1, 2])))
    return d.weekday() in light


def _warmup_multiplier(now: Optional[datetime] = None) -> float:
    """0.4→1.0 lineal durante WARMUP_DAYS desde el ancla de warmup. 1.0 si no hay
    ancla o ya maduró. El ancla se setea en set_warmup_anchor() (primer run/reset)."""
    history = _load_ban_history()
    anchor = history.get("warmup_anchor")
    if not anchor:
        return 1.0
    try:
        anchor_dt = datetime.fromisoformat(anchor)
    except (ValueError, TypeError):
        return 1.0
    now = now or datetime.now()
    days = (now - anchor_dt).total_seconds() / 86400.0
    if days >= WARMUP_DAYS:
        return 1.0
    if days < 0:
        return WARMUP_FLOOR
    return WARMUP_FLOOR + (1.0 - WARMUP_FLOOR) * (days / WARMUP_DAYS)


def set_warmup_anchor(when: Optional[datetime] = None, force: bool = False) -> None:
    """Fija el ancla de warmup (idempotente salvo force). Llamar tras un reset del
    pipeline o en el primer arranque para que la cuenta 'rampee' en vez de saltar."""
    history = _load_ban_history()
    if history.get("warmup_anchor") and not force:
        return
    history["warmup_anchor"] = (when or datetime.now()).isoformat()
    _save_ban_history(history)
    logger.info(f"[gov] warmup_anchor = {history['warmup_anchor']} ({WARMUP_DAYS}d ramp)")


def _effective_daily_cap(kind: str, now: Optional[datetime] = None) -> int:
    """Cap diario efectivo del tipo: base de _POLICY, con jitter determinista ±30%,
    día ligero (~50%) y multiplicador de warmup. APPLY además respeta recovery."""
    now = now or datetime.now()
    d = now.date()
    base = _POLICY[kind]["per_day"]

    rng = _date_seed(kind, d)
    factor = rng.uniform(0.7, 1.3)           # ±30% día a día
    if _is_light_day(d):
        factor *= 0.5                         # día ligero
    factor *= _warmup_multiplier(now)         # warmup ramp
    cap = max(1, round(base * factor))

    # Recovery de APPLY es un TECHO (nunca sube el cap), pero la aleatorización /
    # warmup / día ligero pueden bajarlo más. Una cuenta ya flageada debe ir
    # SIEMPRE por el mínimo de ambos.
    if kind == APPLY:
        history = _load_ban_history()
        if history.get("recovery_mode"):
            recovery_cap = int(history.get("recovery_daily_limit", DEFAULT_DAILY_CAP))
            cap = min(cap, recovery_cap)

    return cap


def apply_daily_cap() -> int:
    """Cap de apply vigente hoy (recovery + aleatorización + días ligeros + warmup)."""
    return _effective_daily_cap(APPLY)


def get_ban_state() -> Dict:
    return _load_ban_history()


# ── Horario humano ───────────────────────────────────────────────────────────

def _within_hours(kind: str, now: Optional[datetime] = None) -> bool:
    now = now or datetime.now()
    pol = _POLICY[kind]
    if pol["biz_days"] and now.weekday() not in BUSINESS_DAYS:
        return False
    start, end = pol["hours"]
    return start <= now.hour < end


# ── Decisión central ─────────────────────────────────────────────────────────

def can_act(kind: str, now: Optional[datetime] = None) -> Tuple[bool, str]:
    """
    ¿Se permite ejecutar una acción `kind` ahora? Fail-closed.
    Retorna (permitido, razón). La razón es útil para logs cuando es False.
    """
    if kind not in _POLICY:
        return False, f"unknown_kind:{kind}"

    now = now or datetime.now()

    # 1. Ban de cuenta
    banned, resume_at = is_banned()
    if banned:
        return False, f"banned_until:{resume_at}"

    # 2. Horario humano
    if not _within_hours(kind, now):
        return False, "outside_hours"

    pol = _POLICY[kind]

    # 3. Cap diario efectivo del tipo (aleatorizado + días ligeros + warmup;
    #    APPLY además respeta recovery). Ver _effective_daily_cap.
    per_day = _effective_daily_cap(kind, now)
    day_count = _count(kind, "datetime('now','-1 day')")
    if day_count >= per_day:
        return False, f"daily_cap:{day_count}/{per_day}"

    # 4. Cap por hora del tipo
    hour_count = _count(kind, "datetime('now','-1 hour')")
    if hour_count >= pol["per_hour"]:
        return False, f"hourly_cap:{hour_count}/{pol['per_hour']}"

    # 5. Gap mínimo desde la última acción del tipo
    last = _last_action_at(kind)
    if last is not None:
        gap = (now - last).total_seconds() / 60.0
        if gap < pol["gap_min"]:
            return False, f"gap_min:{gap:.0f}<{pol['gap_min']}min"

    # 6. Presupuesto global de la cuenta (solo acciones interactivas de escritura)
    if kind in _INTERACTIVE:
        global_count = _count(None, "datetime('now','-1 day')")
        if global_count >= GLOBAL_INTERACTIVE_PER_DAY:
            return False, f"global_cap:{global_count}/{GLOBAL_INTERACTIVE_PER_DAY}"

    return True, "ok"


# ── Jitter humano ────────────────────────────────────────────────────────────

def _jitter_seconds(kind: str) -> float:
    lo, hi = _JITTER.get(kind, (5, 20))
    return random.uniform(lo, hi)


def human_delay(kind: str) -> None:
    """Delay humano (bloqueante) antes de ejecutar la acción."""
    d = _jitter_seconds(kind)
    logger.debug(f"[gov] delay {kind}: {d:.1f}s")
    time.sleep(d)


async def human_delay_async(kind: str) -> None:
    """Delay humano (async) antes de ejecutar la acción."""
    d = _jitter_seconds(kind)
    logger.debug(f"[gov] delay {kind}: {d:.1f}s")
    await asyncio.sleep(d)


if __name__ == "__main__":
    import pprint

    print("Ban state:")
    pprint.pp(get_ban_state())
    print("\nCounts today:")
    pprint.pp(counts_today())
    print("\ncan_act por tipo:")
    for k in (APPLY, MSG_READ, MSG_SEND, CONNECT, POST, SEARCH):
        pprint.pp((k, can_act(k)))
