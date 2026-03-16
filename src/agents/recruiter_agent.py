"""
Recruiter Agent: GLM-4.7 que habla con reclutadores en nombre de Alejandro.
- Detecta idioma y responde en el mismo (español/inglés)
- Propone slots del calendario cuando piden disponibilidad
- Manda borradores a WhatsApp para aprobación antes de enviar
"""
import json
import os
from typing import Dict, Any, List, Optional, Tuple
from loguru import logger
from langchain_core.messages import HumanMessage

from config import settings
from src.agents import coordinator


def _load_resume() -> Dict:
    resume_file = getattr(settings, "resume_file", "data/resume.json")
    try:
        with open(resume_file) as f:
            return json.load(f)
    except Exception:
        return {}


ALEJANDRO_CONTEXT = """
Eres el asistente personal de Alejandro Loza, un SR. Software Engineer
especializado en Java, Full Stack y Cloud con sede en Ciudad de México (trabaja remoto).

Hablas EN SU NOMBRE con reclutadores de forma profesional y amigable.
Detectas el idioma del reclutador y respondes en el mismo idioma (español o inglés).

Perfil de Alejandro:
- Nombre: Alejandro Loza
- Rol actual: SR. Software Engineer
- Skills: Java, Spring Boot, Full Stack, JavaScript, Cloud (AWS/GCP), Microservices, Docker, Kubernetes
- Ubicación: Ciudad de México, México (remoto)
- LinkedIn: https://www.linkedin.com/in/alejandro-hernandez-loza/
- Open to Work: Sí
- Modalidad preferida: Remoto
- Disponibilidad para entrevistas: Lunes a Viernes, 9-11am o 3-4pm hora México

RESTRICCIONES DE NEGOCIACIÓN (NO negociables, rechazar amablemente si aplican):
1. NO acepta contratos por honorarios (freelance/independiente en México)
2. NO acepta esquemas por hora (tarifa por hora)
3. NO acepta cualquier modalidad donde él deba declarar ante el SAT como honorarios
4. NO acepta ofertas menores a $50,000 MXN mensuales brutos
5. SOLO acepta: empleo formal con nómina (IMSS), trabajo en relación de dependencia,
   o contratos internacionales vía payroll (Deel, Remote.com, etc.)
6. Si la oferta es en USD: mínimo aceptable ~$2,500 USD/mes (equivalente a ~50k MXN)

Al detectar una oferta que viola estas restricciones:
- Rechaza de forma educada y profesional
- Explica brevemente que busca empleo formal con prestaciones de ley
- No cierres la puerta si la empresa puede ajustar la modalidad

Principios al responder:
1. Siempre profesional pero cercano
2. Muestra interés genuino en las oportunidades que cumplen los requisitos
3. Si preguntan salario, indica que busca +$50,000 MXN en nómina formal
4. Si piden disponibilidad, propones los slots del calendario
5. Si hay algo que no puedes decidir, lo consultas con Alejandro
6. Nunca prometes lo que no puedes cumplir
7. Respuestas concisas (máx 150 palabras)
"""




def analyze_recruiter_message(
    message: str,
    sender_name: str,
    sender_title: str,
    conversation_history: List[Dict] = None,
    free_slots: List[Dict] = None,
) -> Dict[str, Any]:
    """
    Analiza un mensaje de reclutador y genera respuesta borrador.

    Returns:
        Dict con:
        - intent: "schedule|info|rejection|offer|general"
        - urgency: "high|medium|low"
        - draft_response: texto de respuesta sugerida
        - needs_user_input: bool (si requiere decisión de Alejandro)
        - user_question: pregunta para Alejandro si needs_user_input=True
        - language: "es|en"
        - summary: resumen de 1 línea del mensaje
    """
    slots_text = ""
    if free_slots:
        slots_text = "\n\nSlots disponibles en calendario de Alejandro:\n"
        for i, slot in enumerate(free_slots, 1):
            slots_text += f"  {i}. {slot['label']}\n"

    history_text = ""
    if conversation_history:
        history_text = "\n\nHistorial de conversación (más reciente primero):\n"
        for msg in conversation_history[:5]:
            who = "Alejandro" if msg.get("from_me") else sender_name
            history_text += f"  [{who}]: {msg.get('body', '')[:200]}\n"

    prompt = f"""{ALEJANDRO_CONTEXT}

Mensaje recibido de {sender_name} ({sender_title}):
"{message}"
{history_text}
{slots_text}

Analiza el mensaje y genera una respuesta apropiada en nombre de Alejandro.

Responde SOLO con JSON válido:
{{
  "intent": "schedule|info|rejection|offer|general",
  "urgency": "high|medium|low",
  "language": "es|en",
  "summary": "resumen de 1 oración de qué quiere el reclutador",
  "draft_response": "respuesta completa en nombre de Alejandro (máx 150 palabras)",
  "needs_user_input": false,
  "user_question": "pregunta para Alejandro si necesita decidir algo, sino null",
  "propose_slots": false
}}

intent:
- schedule: quiere agendar entrevista o pide disponibilidad
- info: pide información del perfil/experiencia
- offer: hace una oferta de trabajo
- rejection: rechazo o posición cerrada
- general: networking/contacto general

needs_user_input = true solo si hay algo que ALEJANDRO debe decidir
(salario específico, si acepta oferta, si le interesa la empresa, etc.)

Si intent=schedule, usa los slots del calendario en la respuesta.
"""

    try:
        content = coordinator.invoke("recruiter_reply", [HumanMessage(content=prompt)], max_tokens=1024).strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        result = json.loads(content)

        # Comunicación agente-a-agente:
        # Si es una oferta, pedirle a master_agent que evalúe el match con el CV
        if result.get("intent") == "offer":
            try:
                from src.agents.agent_bus import bus
                import json as _json
                resume = _load_resume()
                job_hint = {
                    "title": sender_title,
                    "company": sender_name,
                    "description": message,
                    "location": "remote",
                }
                score, reasons = bus.call("master_agent.evaluate_job", job=job_hint, resume=resume)
                result["job_match_score"] = score
                result["job_match_reasons"] = reasons
                logger.info(f"[recruiter→master] match score para oferta de {sender_name}: {score}")
            except Exception as e:
                logger.warning(f"[recruiter→master] no pudo evaluar match: {e}")

        # Si pide disponibilidad, pedirle a calendar_agent los slots
        if result.get("intent") == "schedule" and not free_slots:
            try:
                from src.agents.agent_bus import bus
                slots = bus.call("calendar_agent.free_slots", days_ahead=7)
                result["calendar_slots"] = slots
                logger.info(f"[recruiter→calendar] obtuvo {len(slots)} slots libres")
            except Exception as e:
                logger.warning(f"[recruiter→calendar] no pudo obtener slots: {e}")

        return result
    except Exception as e:
        logger.error(f"Error analizando mensaje de reclutador: {e}")
        return {
            "intent": "general",
            "urgency": "low",
            "language": "es",
            "summary": "Mensaje de reclutador",
            "draft_response": "Hola, gracias por contactarme. ¿Podrías darme más detalles sobre la oportunidad?",
            "needs_user_input": True,
            "user_question": "¿Cómo quieres responder a este reclutador?",
            "propose_slots": False,
        }


def format_whatsapp_approval_request(
    sender_name: str,
    sender_title: str,
    original_message: str,
    analysis: Dict[str, Any],
    source: str = "LinkedIn",
) -> str:
    """
    Formatea el mensaje de WhatsApp para pedir aprobación a Alejandro.

    Returns:
        Texto formateado para WhatsApp
    """
    intent_icons = {
        "schedule": "📅",
        "info": "ℹ️",
        "offer": "💼",
        "rejection": "❌",
        "general": "💬",
    }
    urgency_icons = {"high": "🔴", "medium": "🟡", "low": "🟢"}

    icon = intent_icons.get(analysis["intent"], "💬")
    urgency = urgency_icons.get(analysis["urgency"], "🟢")

    msg = (
        f"{icon} *Mensaje en {source}*\n"
        f"De: *{sender_name}* ({sender_title})\n"
        f"Urgencia: {urgency}\n\n"
        f"*Dice:* {original_message[:300]}\n\n"
        f"*Resumen:* {analysis['summary']}\n\n"
    )

    if analysis.get("needs_user_input") and analysis.get("user_question"):
        msg += f"*Pregunta:* {analysis['user_question']}\n\n"
        msg += "Responde con tu decisión y luego confirmaré."
    else:
        msg += f"*Mi respuesta sugerida:*\n_{analysis['draft_response']}_\n\n"
        msg += "¿Envío? Responde *si* / *editar [tu versión]* / *no*"

    return msg


def refine_response(
    original_draft: str,
    user_feedback: str,
    language: str = "es",
) -> str:
    """
    Refina la respuesta con el feedback del usuario.
    Ej: usuario dice "editar sé más formal" o "editar menciona X años de experiencia"
    """
    prompt = f"""{ALEJANDRO_CONTEXT}

Borrador original de respuesta al reclutador:
"{original_draft}"

Alejandro quiere que lo modifiques así:
"{user_feedback}"

Idioma: {"español" if language == "es" else "inglés"}

Genera la versión mejorada. SOLO el texto de la respuesta, sin explicaciones.
Máximo 150 palabras.
"""
    try:
        return coordinator.invoke("refine_response", [HumanMessage(content=prompt)], max_tokens=1024).strip()
    except Exception as e:
        logger.error(f"Error refinando respuesta: {e}")
        return original_draft


def generate_email_to_recruiter(
    recruiter_name: str,
    recruiter_email: str,
    company: str,
    job_title: str,
    context: str,
    language: str = "es",
) -> Dict[str, str]:
    """
    Genera un email profesional para un reclutador.

    Returns:
        Dict con subject y body
    """
    prompt = f"""{ALEJANDRO_CONTEXT}

Escribe un email profesional de Alejandro Loza al reclutador {recruiter_name}
de la empresa {company} sobre el puesto "{job_title}".

Contexto adicional: {context}
Idioma: {"español" if language == "es" else "inglés"}

El email debe ser breve (máx 150 palabras), profesional y mostrar interés genuino.

Responde SOLO con JSON:
{{
  "subject": "asunto del email",
  "body": "cuerpo completo del email con saludo y despedida"
}}
"""
    try:
        content = coordinator.invoke("recruiter_reply", [HumanMessage(content=prompt)], max_tokens=1024).strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        return json.loads(content)
    except Exception as e:
        logger.error(f"Error generando email: {e}")
        return {
            "subject": f"Interés en posición {job_title} - {company}",
            "body": f"Hola {recruiter_name},\n\nGracias por contactarme. Me interesa conocer más sobre la posición de {job_title} en {company}.\n\nQuedo a tu disposición.\n\nAlejandro Loza",
        }
