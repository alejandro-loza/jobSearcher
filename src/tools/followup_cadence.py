"""
Follow-up cadence — decide CUÁNDO enviar follow-up según el estado de la
aplicación. Port de career-ops/followup-cadence.mjs.

Reemplaza la lógica actual ("7 días fijo sin respuesta") por cadencias
diferenciadas por estado, con límite de follow-ups totales.

Cadencias:
    applied (sin respuesta)   → día 7, luego día 14 (máx 2 follow-ups)
    responded (reclutador me respondió) → día 1, luego día 3
    interview_scheduled       → thank-you día 1
    offer / rejected / skip   → no follow-up
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal, Optional

from loguru import logger

Status = Literal[
    "applied", "responded", "interview", "offer", "rejected", "discarded", "skip"
]

# cadencia en DÍAS desde el evento relevante
CADENCE = {
    "applied_first": 7,
    "applied_subsequent": 7,  # segundo follow-up 7 días después del primero
    "applied_max_followups": 2,
    "responded_initial": 1,
    "responded_subsequent": 3,
    "responded_max_followups": 2,
    "interview_thankyou": 1,
    "interview_max_followups": 1,
}


@dataclass
class FollowupDecision:
    should_send: bool
    reason: str
    followup_kind: Optional[str] = None  # "first_apply" | "second_apply" | "thank_you" | ...


def _days_since(iso_dt: Optional[str]) -> float:
    if not iso_dt:
        return 0.0
    try:
        dt = datetime.fromisoformat(iso_dt.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - dt).total_seconds() / 86400
    except Exception as e:
        logger.warning(f"_days_since parse failed for {iso_dt}: {e}")
        return 0.0


def decide(
    status: str,
    applied_at: Optional[str] = None,
    last_followup_at: Optional[str] = None,
    last_response_at: Optional[str] = None,
    last_interview_at: Optional[str] = None,
    followup_count: int = 0,
) -> FollowupDecision:
    """
    Decide si mandar follow-up HOY para una aplicación dada.

    Args:
        status: estado actual (normalizado)
        applied_at: ISO timestamp de cuando se aplicó
        last_followup_at: ISO timestamp del último follow-up enviado
        last_response_at: ISO timestamp de última respuesta del reclutador
        last_interview_at: ISO timestamp de entrevista completada
        followup_count: cuántos follow-ups ya se enviaron

    Returns:
        FollowupDecision
    """
    status = (status or "").lower()

    if status in ("offer", "rejected", "discarded", "skip"):
        return FollowupDecision(False, f"estado terminal: {status}")

    # interview → thank-you después de la entrevista
    if status == "interview":
        if followup_count >= CADENCE["interview_max_followups"]:
            return FollowupDecision(False, "thank-you ya enviado")
        days = _days_since(last_interview_at or applied_at)
        if days >= CADENCE["interview_thankyou"]:
            return FollowupDecision(True, f"thank-you post-interview (día {days:.1f})", "thank_you")
        return FollowupDecision(False, f"esperando día {CADENCE['interview_thankyou']}, van {days:.1f}")

    # responded → mantener conversación caliente
    if status == "responded":
        if followup_count >= CADENCE["responded_max_followups"]:
            return FollowupDecision(False, "máx follow-ups en responded alcanzado")

        reference = last_followup_at or last_response_at
        days = _days_since(reference)
        threshold = (
            CADENCE["responded_initial"]
            if followup_count == 0
            else CADENCE["responded_subsequent"]
        )
        if days >= threshold:
            kind = "responded_first" if followup_count == 0 else "responded_second"
            return FollowupDecision(True, f"responded + {days:.1f}d ≥ {threshold}d", kind)
        return FollowupDecision(False, f"esperando {threshold}d, van {days:.1f}")

    # applied → cadencia estándar
    if status == "applied":
        if followup_count >= CADENCE["applied_max_followups"]:
            return FollowupDecision(False, "máx follow-ups alcanzado (2)")

        reference = last_followup_at or applied_at
        days = _days_since(reference)
        threshold = (
            CADENCE["applied_first"]
            if followup_count == 0
            else CADENCE["applied_subsequent"]
        )
        if days >= threshold:
            kind = "first_apply" if followup_count == 0 else "second_apply"
            return FollowupDecision(True, f"applied + {days:.1f}d ≥ {threshold}d", kind)
        return FollowupDecision(False, f"esperando {threshold}d, van {days:.1f}")

    return FollowupDecision(False, f"estado no accionable: {status}")


def decide_from_app(app: dict) -> FollowupDecision:
    """Shortcut: acepta un dict de aplicación del tracker y decide."""
    return decide(
        status=app.get("status", "applied"),
        applied_at=app.get("applied_at"),
        last_followup_at=app.get("last_followup_at"),
        last_response_at=app.get("last_response_at"),
        last_interview_at=app.get("last_interview_at"),
        followup_count=int(app.get("followup_count") or 0),
    )
