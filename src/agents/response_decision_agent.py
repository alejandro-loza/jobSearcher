"""
Response Decision Agent — tiene la ÚLTIMA PALABRA sobre si responder un mensaje.

Aplica tanto a emails como a mensajes de LinkedIn.

Decisiones posibles:
  AUTO_RESPOND  — el agente genera borrador y lo envía
  ESCALATE      — Alejandro debe responder personalmente (notifica por WhatsApp)
  SKIP          — no responder (spam, duplicado, irrelevante, ya respondido)
  ASK_USER      — necesita input de Alejandro antes de poder responder

Orden de evaluación:
  1. Contacto bloqueado → SKIP / ESCALATE
  2. Ya respondimos en este hilo → SKIP
  3. Mensaje muy corto / vacío → SKIP
  4. LLM: spam / no relacionado con empleo → SKIP
  5. LLM: tecnologías fuera del CV → ESCALATE
  6. Contexto sensible (Thomson Reuters, contactos personales) → ESCALATE
  7. LLM: pregunta info que el agente no tiene → ASK_USER
  8. Evaluación de oportunidad (ubicación, tipo contrato, salario) → SKIP / ESCALATE
  9. Todo OK → AUTO_RESPOND
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Any

from langchain_core.messages import HumanMessage
from loguru import logger

from src.agents import coordinator
from src.agents.antispam_agent import (
    BLOCKED_ADDRESSES,
    BLOCKED_PERSONAL_NAMES,
    BLOCKED_KEYWORDS,
)

# ── Tecnologías que no están en el CV y requieren decisión de Alejandro ────────
# Usa palabras completas (word-boundary match) para evitar falsos positivos
TECH_MISMATCH_PATTERNS: list[str] = [
    r"\bakamai\b",
    r"\bsap hana\b", r"\bsap basis\b", r"\bsap abap\b", r"\b\.net\b", r"\bc#\b",
    r"\basp\.net\b", r"\bsharepoint\b", r"\bdynamics 365\b", r"\bpower platform\b",
    r"\bmainframe\b", r"\bcobol\b", r"\bfortran\b", r"\bperl\b",
    r"\bsalesforce apex\b", r"\bservicenow\b",
    r"\bunity engine\b", r"\bunreal engine\b",
    r"\bembedded systems\b", r"\bfpga\b", r"\bvhdl\b", r"\bverilog\b",
]

# Patrones de contexto sensible (siempre ESCALATE)
SENSITIVE_PATTERNS: list[str] = [
    r"thomson reuters",
    r"sam lewis",
    r"melba ruiz",
]

# Skills del CV de Alejandro (para el prompt del LLM)
_CV_SKILLS = [
    "Java", "Spring Boot", "Micronaut", "Groovy", "Kotlin",
    "JavaScript", "TypeScript", "Node.js", "Ember", "Angular", "React",
    "AWS", "GCP", "Docker", "Kubernetes", "Kafka", "SAP CPI",
    "MySQL", "PostgreSQL", "MongoDB", "Redis", "Oracle",
    "Python", "Go", "Microservices", "REST", "CI/CD", "Linux",
]


class ResponseDecision(Enum):
    AUTO_RESPOND = "auto_respond"
    ESCALATE     = "escalate"
    SKIP         = "skip"
    ASK_USER     = "ask_user"


@dataclass
class DecisionResult:
    decision:       ResponseDecision
    reason:         str
    draft_response: Optional[str] = None    # solo cuando AUTO_RESPOND
    user_question:  Optional[str] = None    # solo cuando ASK_USER
    escalation_msg: Optional[str] = None    # mensaje WhatsApp cuando ESCALATE
    llm_analysis:   Dict[str, Any] = field(default_factory=dict)


# ── LLM classification ─────────────────────────────────────────────────────────

def _llm_classify(
    message_body: str,
    subject_or_title: str,
    sender_name_or_addr: str,
    conversation_history: Optional[List[Dict]] = None,
    source: str = "email",
) -> Dict[str, Any]:
    """
    Llama al LLM para clasificar el mensaje entrante.

    Retorna dict con:
      is_job_related, is_spam, is_recruiter_outreach,
      mentions_tech_not_in_cv (list), mentions_sensitive_context,
      asks_for_unknown_info, salary_mentioned, salary_meets_threshold,
      location_ok, employment_type_ok, llm_summary, llm_suggested_draft
    """
    history_text = ""
    if conversation_history:
        history_text = "\nHistorial del hilo (cronológico):\n"
        for msg in conversation_history[-8:]:
            who = "Alejandro" if msg.get("from_me") else sender_name_or_addr
            body = msg.get("body") or msg.get("message_text") or msg.get("content") or ""
            history_text += f"  [{who}]: {body[:300]}\n"

    prompt = f"""Eres un agente filtro para Alejandro Loza, Sr. Software Engineer (Java/Spring Boot/Cloud, 12 años XP, CDMX México, remoto).

Analiza este mensaje de {source} y clasifícalo.

De: {sender_name_or_addr}
Asunto/Título: {subject_or_title}
Mensaje:
{message_body[:2000]}
{history_text}

Skills en el CV de Alejandro: {', '.join(_CV_SKILLS)}

Restricciones de Alejandro:
- Salario mínimo: $50,000 MXN/mes o $2,500 USD/mes
- Solo nómina formal (IMSS) o payroll internacional (Deel/Remote.com) — NO honorarios, NO freelance, NO por hora
- Ubicación: solo remoto o México
- NO acepta reubicación a otras ciudades o países

Responde ÚNICAMENTE con JSON válido:
{{
  "is_job_related": true/false,
  "is_spam": true/false,
  "is_recruiter_outreach": true/false,
  "mentions_tech_not_in_cv": ["lista de tecnologías requeridas que NO están en el CV"],
  "mentions_sensitive_context": true/false,
  "asks_for_unknown_info": true/false,
  "salary_mentioned": "texto o null",
  "salary_meets_threshold": true/false/null,
  "location_ok": true/false,
  "employment_type_ok": true/false,
  "llm_summary": "resumen en 1 oración",
  "llm_suggested_draft": "borrador de respuesta profesional en el mismo idioma del mensaje (es/en), máximo 150 palabras, o null si no aplica"
}}

Notas:
- mentions_tech_not_in_cv: SOLO tecnologías explícitamente requeridas que NO están en el CV
- asks_for_unknown_info: true si pregunta algo que el agente no puede responder por Alejandro (negociación, decisiones personales, info específica no disponible)
- employment_type_ok: false si menciona honorarios, freelance, esquema por hora
- is_spam: true si es correo masivo/comercial no relacionado con vacante específica para Alejandro
- llm_suggested_draft: si is_job_related=true y todo OK, genera un borrador conciso para concretar entrevista
"""
    try:
        raw = coordinator.invoke(
            "response_decision",
            [HumanMessage(content=prompt)],
            max_tokens=1024,
        ).strip()
        # strip markdown code fences if present
        if raw.startswith("```"):
            parts = raw.split("```")
            raw = parts[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw)
    except Exception as e:
        logger.error(f"[response_decision] LLM classify error: {e}")
        return {
            "is_job_related": False,
            "is_spam": False,
            "is_recruiter_outreach": False,
            "mentions_tech_not_in_cv": [],
            "mentions_sensitive_context": False,
            "asks_for_unknown_info": True,
            "salary_mentioned": None,
            "salary_meets_threshold": None,
            "location_ok": True,
            "employment_type_ok": True,
            "llm_summary": "No se pudo clasificar el mensaje",
            "llm_suggested_draft": None,
        }


# ── Main decision function ─────────────────────────────────────────────────────

def decide(
    *,
    from_address: str = "",
    sender_name: str = "",
    message_body: str,
    subject_or_title: str = "",
    thread_id_or_conv_id: str = "",
    last_message_is_ours: bool = False,
    conversation_history: Optional[List[Dict]] = None,
    source: str = "email",
) -> DecisionResult:
    """
    Función principal — retorna la decisión definitiva sobre si/cómo responder.

    Args:
        from_address:          Email del remitente (para email; vacío para LinkedIn)
        sender_name:           Nombre del remitente
        message_body:          Cuerpo del mensaje entrante
        subject_or_title:      Asunto del email o título del reclutador en LinkedIn
        thread_id_or_conv_id:  ID del hilo/conversación (para logging)
        last_message_is_ours:  True si el último mensaje del hilo es nuestro
        conversation_history:  Lista de dicts {body/message_text, from_me}
        source:                "email" o "linkedin"
    """
    addr_lower = (from_address or "").lower().strip()
    name_lower = (sender_name or "").lower().strip()
    display    = sender_name or from_address or "desconocido"

    # ── 1. Contactos bloqueados ────────────────────────────────────────────────
    if addr_lower in BLOCKED_ADDRESSES:
        return DecisionResult(
            decision=ResponseDecision.SKIP,
            reason=f"Dirección en lista de bloqueo: {addr_lower}",
        )

    for personal in BLOCKED_PERSONAL_NAMES:
        if personal in name_lower:
            return DecisionResult(
                decision=ResponseDecision.ESCALATE,
                reason=f"Contacto personal — Alejandro debe responder: {sender_name}",
                escalation_msg=(
                    f"{'📧' if source == 'email' else '💬'} Mensaje de *{sender_name}* — contacto personal.\n"
                    f"Revisa y responde tú manualmente.\n\n"
                    f"{'Asunto' if source == 'email' else 'Contexto'}: {subject_or_title}\n"
                    f"Extracto: {message_body[:250]}"
                ),
            )

    if any(kw in addr_lower for kw in BLOCKED_KEYWORDS):
        return DecisionResult(
            decision=ResponseDecision.SKIP,
            reason=f"Dominio de notificaciones/mailer: {addr_lower}",
        )

    # ── 2. Ya respondimos en este hilo ────────────────────────────────────────
    if last_message_is_ours:
        return DecisionResult(
            decision=ResponseDecision.SKIP,
            reason="Último mensaje del hilo es nuestro — esperando respuesta",
        )

    # ── 3. Mensaje vacío o demasiado corto ────────────────────────────────────
    if not message_body or len(message_body.strip()) < 15:
        return DecisionResult(
            decision=ResponseDecision.SKIP,
            reason="Mensaje demasiado corto para clasificar",
        )

    # ── Clasificación LLM (usada en pasos 4-9) ────────────────────────────────
    analysis = _llm_classify(
        message_body=message_body,
        subject_or_title=subject_or_title,
        sender_name_or_addr=sender_name or from_address,
        conversation_history=conversation_history,
        source=source,
    )

    # ── 4. Spam / no relacionado con empleo ───────────────────────────────────
    if analysis.get("is_spam"):
        return DecisionResult(
            decision=ResponseDecision.SKIP,
            reason="LLM: spam / correo masivo no solicitado",
            llm_analysis=analysis,
        )

    if not analysis.get("is_job_related") and not analysis.get("is_recruiter_outreach"):
        return DecisionResult(
            decision=ResponseDecision.SKIP,
            reason=f"LLM: no relacionado con búsqueda de empleo — {analysis.get('llm_summary', '')}",
            llm_analysis=analysis,
        )

    # ── 5. Tecnologías fuera del CV ────────────────────────────────────────────
    llm_mismatches = [t.lower() for t in analysis.get("mentions_tech_not_in_cv", [])]
    body_lower = message_body.lower()
    static_mismatches = [
        p.strip(r"\b") for p in TECH_MISMATCH_PATTERNS
        if re.search(p, body_lower)
    ]
    all_mismatches = list(set(llm_mismatches + static_mismatches))

    if all_mismatches:
        techs_str = ", ".join(all_mismatches[:5])
        return DecisionResult(
            decision=ResponseDecision.ESCALATE,
            reason=f"Requiere tecnología fuera del CV: {techs_str}",
            escalation_msg=(
                f"{'📧' if source == 'email' else '💬'} *{display}* — vacante con tech fuera de tu CV\n"
                f"Tecnologías detectadas: *{techs_str}*\n\n"
                f"Resumen: {analysis.get('llm_summary', '')}\n"
                f"Extracto: {message_body[:300]}\n\n"
                f"¿Quieres que responda yo o lo manejas tú?"
            ),
            llm_analysis=analysis,
        )

    # ── 6. Contexto sensible ──────────────────────────────────────────────────
    body_and_subject = (message_body + " " + subject_or_title).lower()
    static_sensitive = any(re.search(p, body_and_subject) for p in SENSITIVE_PATTERNS)
    if analysis.get("mentions_sensitive_context") or static_sensitive:
        return DecisionResult(
            decision=ResponseDecision.ESCALATE,
            reason="Contexto sensible (Thomson Reuters / contacto personal)",
            escalation_msg=(
                f"{'📧' if source == 'email' else '💬'} *{display}* — contexto sensible\n"
                f"Resumen: {analysis.get('llm_summary', '')}\n"
                f"Extracto: {message_body[:300]}\n\n"
                f"Maneja esto personalmente."
            ),
            llm_analysis=analysis,
        )

    # ── 7. Necesita input de Alejandro ────────────────────────────────────────
    if analysis.get("asks_for_unknown_info"):
        draft = analysis.get("llm_suggested_draft") or ""
        return DecisionResult(
            decision=ResponseDecision.ASK_USER,
            reason="El mensaje requiere información o decisión de Alejandro",
            draft_response=draft,
            user_question=(
                f"{'📧' if source == 'email' else '💬'} *{display}* necesita tu respuesta:\n\n"
                f"{message_body[:400]}\n\n"
                f"{'Borrador sugerido: ' + draft[:200] if draft else 'No tengo borrador para esto.'}\n\n"
                f"¿Qué le contesto?"
            ),
            llm_analysis=analysis,
        )

    # ── 8. Evaluar calidad de la oportunidad ──────────────────────────────────
    if not analysis.get("location_ok", True):
        return DecisionResult(
            decision=ResponseDecision.SKIP,
            reason=f"Ubicación no aceptable (no es remoto ni México): {analysis.get('llm_summary', '')}",
            llm_analysis=analysis,
        )

    if not analysis.get("employment_type_ok", True):
        return DecisionResult(
            decision=ResponseDecision.ESCALATE,
            reason="Esquema de contratación no aceptable (honorarios/por hora/freelance)",
            escalation_msg=(
                f"{'📧' if source == 'email' else '💬'} *{display}* — esquema de contrato no aceptable\n"
                f"Resumen: {analysis.get('llm_summary', '')}\n"
                f"Extracto: {message_body[:300]}\n\n"
                f"¿Rechazo amablemente o lo manejas tú?"
            ),
            draft_response=analysis.get("llm_suggested_draft"),
            llm_analysis=analysis,
        )

    salary_ok = analysis.get("salary_meets_threshold")  # None = no mencionado = OK
    if salary_ok is False:
        return DecisionResult(
            decision=ResponseDecision.ESCALATE,
            reason=f"Salario por debajo del mínimo: {analysis.get('salary_mentioned', '')}",
            escalation_msg=(
                f"{'📧' if source == 'email' else '💬'} *{display}* — salario bajo el mínimo\n"
                f"Salario mencionado: *{analysis.get('salary_mentioned', 'no especificado')}*\n"
                f"Resumen: {analysis.get('llm_summary', '')}\n\n"
                f"¿Rechazo o negocias tú?"
            ),
            llm_analysis=analysis,
        )

    # ── 9. Todo OK → AUTO_RESPOND ─────────────────────────────────────────────
    draft = analysis.get("llm_suggested_draft") or ""
    return DecisionResult(
        decision=ResponseDecision.AUTO_RESPOND,
        reason=f"Oportunidad válida: {analysis.get('llm_summary', '')}",
        draft_response=draft,
        llm_analysis=analysis,
    )


# ── Outgoing message gate — called by send_email / send_message ───────────────

def approve_outgoing(
    *,
    to: str,
    subject: str,
    body: str,
    conversation_history: List[Dict],
    sender_name: str = "",
    source: str = "email",
) -> tuple[bool, str]:
    """
    Verifica si un mensaje SALIENTE debe enviarse.
    Llamado por gmail_tool.send_email() y linkedin_messages_tool.send_message().

    Requiere conversation_history para tener contexto completo del hilo.

    Returns:
        (approved: bool, reason: str)
    """
    display = sender_name or to

    # 1. Sin historial = sin contexto = no enviar
    if not conversation_history:
        reason = f"SIN HISTORIAL — no se puede enviar sin contexto de conversación a {display}"
        logger.warning(f"[approve_outgoing] {reason}")
        return False, reason

    # 2. Contacto bloqueado
    to_lower = to.lower().strip()
    name_lower = (sender_name or "").lower().strip()

    if to_lower in BLOCKED_ADDRESSES:
        return False, f"Dirección bloqueada: {to_lower}"

    for personal in BLOCKED_PERSONAL_NAMES:
        if personal in name_lower or personal in to_lower:
            return False, f"Contacto personal bloqueado: {display}"

    if any(kw in to_lower for kw in BLOCKED_KEYWORDS):
        return False, f"Dominio de notificaciones: {to_lower}"

    # 3. Último mensaje es nuestro → no enviar doble
    if conversation_history:
        last = conversation_history[-1]
        if last.get("from_me"):
            return False, f"Último mensaje del hilo ya es nuestro — no enviar doble a {display}"

    # 4. Body vacío o genérico (template spam)
    if not body or len(body.strip()) < 20:
        return False, "Cuerpo del mensaje vacío o demasiado corto"

    SPAM_TEMPLATE_SIGNATURES = [
        "Thank you for reaching out about this opportunity",
        "I'm a Senior Software Engineer with 12+ years",
        "Please find my attached resume for your review",
    ]
    body_lower = body.lower()
    matches = sum(1 for sig in SPAM_TEMPLATE_SIGNATURES if sig.lower() in body_lower)
    if matches >= 2:
        return False, f"Detectado template genérico de spam ({matches} firmas coinciden)"

    # 5. LLM: validar que el mensaje saliente tiene sentido en el contexto
    history_text = ""
    for msg in conversation_history[-6:]:
        who = "Alejandro" if msg.get("from_me") else display
        msg_body = msg.get("body") or msg.get("message_text") or msg.get("content") or ""
        history_text += f"  [{who}]: {msg_body[:300]}\n"

    prompt = f"""Eres un filtro anti-spam para emails/mensajes salientes de Alejandro Loza (Sr. Software Engineer).

Historial de la conversación con {display}:
{history_text}

Mensaje que Alejandro quiere enviar AHORA:
{body[:1000]}

Evalúa si este mensaje:
1. Tiene sentido en el contexto de la conversación
2. NO es un template genérico copiado/pegado sin personalización
3. NO es spam o duplicado de algo ya enviado
4. Aporta valor a la conversación (no es ruido)

Responde ÚNICAMENTE con JSON:
{{"approve": true/false, "reason": "explicación breve"}}"""

    try:
        raw = coordinator.invoke(
            "response_decision",
            [HumanMessage(content=prompt)],
            max_tokens=256,
        ).strip()
        if raw.startswith("```"):
            parts = raw.split("```")
            raw = parts[1]
            if raw.startswith("json"):
                raw = raw[4:]
        result = json.loads(raw)
        approved = result.get("approve", False)
        reason = result.get("reason", "Sin razón")
        logger.info(f"[approve_outgoing] {source} → {display} | approved={approved} | {reason}")
        return approved, reason
    except Exception as e:
        # Si el LLM falla, NO enviar por seguridad
        reason = f"LLM error — bloqueando por seguridad: {e}"
        logger.error(f"[approve_outgoing] {reason}")
        return False, reason


def decide_and_log(
    *,
    from_address: str = "",
    sender_name: str = "",
    message_body: str,
    subject_or_title: str = "",
    thread_id_or_conv_id: str = "",
    last_message_is_ours: bool = False,
    conversation_history: Optional[List[Dict]] = None,
    source: str = "email",
) -> DecisionResult:
    """Wrapper con logging automático."""
    result = decide(
        from_address=from_address,
        sender_name=sender_name,
        message_body=message_body,
        subject_or_title=subject_or_title,
        thread_id_or_conv_id=thread_id_or_conv_id,
        last_message_is_ours=last_message_is_ours,
        conversation_history=conversation_history,
        source=source,
    )
    display = sender_name or from_address or "?"
    logger.info(
        f"[response_decision] {source} | {display[:40]} "
        f"→ {result.decision.value} | {result.reason[:80]}"
    )
    return result
