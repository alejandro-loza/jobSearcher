"""
Master Agent: cerebro central del sistema.
Analiza jobs, evalúa match con CV, decide acciones, genera textos.
Usa coordinator para enrutar cada tarea al LLM óptimo.
"""
import json
from typing import Dict, Any, List, Optional, Tuple
from loguru import logger
from langchain_core.messages import HumanMessage

from config import settings
from src.agents import coordinator


def _invoke_with_fallback(messages: list, temperature: float = 0.7, max_tokens: int = 4096) -> str:
    """Compatibilidad: delega al coordinator con task=job_match (volumen)."""
    return coordinator.invoke("job_match", messages, temperature=temperature, max_tokens=max_tokens)


def _get_llm(temperature: float = 0.7, max_tokens: int = 4096):
    """Retorna el primer LLM disponible (para compatibilidad con código legacy)."""
    if settings.groq_api_key:
        return ChatGroq(
            model=settings.groq_model,
            api_key=settings.groq_api_key,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    if settings.sambanova_api_key:
        return ChatOpenAI(
            model=settings.sambanova_model,
            api_key=settings.sambanova_api_key,
            base_url="https://api.sambanova.ai/v1",
            temperature=temperature,
            max_tokens=max_tokens,
        )
    raise RuntimeError("No hay LLM disponible.")


# Alias para compatibilidad
_get_glm = _get_llm


def extract_search_criteria(resume: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analiza el CV y genera criterios de búsqueda de trabajo.

    Returns:
        Dict con: search_terms, locations, job_types, min_salary, keywords
    """
    prompt = f"""Analiza este CV y genera criterios óptimos de búsqueda de trabajo.

CV:
{json.dumps(resume, ensure_ascii=False, indent=2)}

IMPORTANTE: El candidato quiere enfocarse en roles BACKEND con estas prioridades:
1. Java/Spring Boot/Gradle/Microservicios (su especialidad principal)
2. Backend con integración de LLMs/AI (nueva área de crecimiento - tiene exp con Claude Code en Thomson Reuters)
3. Sr Software Engineer / Tech Lead backend
NO incluir: frontend puro, QA, data science, DevOps/SRE, SAP, Salesforce.
Priorizar términos como: "Senior Java Developer", "Senior Backend Engineer Java", "Java Spring Boot Gradle",
"Backend LLM Integration", "AI Backend Engineer Java", "Sr Software Engineer Java".

Responde SOLO con JSON válido con esta estructura exacta:
{{
  "search_terms": ["término1", "término2", "término3"],
  "locations": ["ubicación1", "ubicación2"],
  "job_types": ["full-time", "remote"],
  "seniority": "mid/senior/junior",
  "key_skills": ["skill1", "skill2", "skill3"],
  "industries": ["industria1", "industria2"],
  "min_experience_years": 0
}}

Los search_terms deben ser en inglés y español. Máximo 5 términos enfocados en backend.
Locations: incluye "remote" y "Ciudad de Mexico" — el candidato prefiere remoto pero acepta híbrido/presencial en CDMX.
"""

    try:
        content = coordinator.invoke("search_criteria", [HumanMessage(content=prompt)]).strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        return json.loads(content)
    except Exception as e:
        logger.error(f"Error extrayendo criterios del CV: {e}")
        return {
            "search_terms": [
                "Senior Java Developer",
                "Senior Backend Engineer Java",
                "Java Spring Boot Gradle",
                "AI Backend Engineer Java",
                "Backend LLM Integration",
            ],
            "locations": ["remote", "Ciudad de Mexico", "Mexico City"],
            "job_types": ["full-time"],
            "seniority": "senior",
            "key_skills": ["Java", "Spring Boot", "Gradle", "Microservices", "LLM", "AWS"],
            "industries": ["technology", "fintech", "software", "AI"],
            "min_experience_years": 10,
        }


def evaluate_job_match(
    job: Dict[str, Any],
    resume: Dict[str, Any],
) -> Tuple[int, str]:
    """
    Evalúa qué tan bien encaja un trabajo con el CV.

    Returns:
        Tuple (score 0-100, justificación breve)
    """
    # Build full CV context for accurate evaluation
    experience_text = ""
    for exp in resume.get("work_experience", []):
        highlights = "; ".join(exp.get("highlights", []))
        experience_text += f"  - {exp.get('role', '')} @ {exp.get('company', '')} ({exp.get('start', '')}-{exp.get('end', '')}): {highlights}\n"

    achievements_text = "; ".join(resume.get("achievements", [])[:5])
    target_roles_text = ", ".join(resume.get("target_roles", []))

    prompt = f"""Evalúa el match entre este CV y esta oferta de trabajo.

CV COMPLETO DEL CANDIDATO:
- Nombre: {resume.get('full_name', '')}
- Rol actual: {resume.get('professional_title', '')}
- Experiencia total: {resume.get('years_of_experience', 0)} años
- Resumen profesional: {resume.get('summary', '')}
- Resumen de experiencia: {resume.get('experience_summary', '')}
- Skills técnicos: {', '.join(resume.get('technical_skills', []))}
- Soft skills: {', '.join(resume.get('soft_skills', []))}
- Ubicación: {resume.get('location', '')}
- Modalidad preferida: {resume.get('preferred_location', 'Remote')}
- Roles objetivo: {target_roles_text}
- Educación: {resume.get('education', '')}

EXPERIENCIA LABORAL DETALLADA:
{experience_text}
LOGROS DESTACADOS: {achievements_text}

OFERTA DE TRABAJO:
- Título: {job.get('title', '')}
- Empresa: {job.get('company', '')}
- Ubicación: {job.get('location', '')}
- Descripción: {job.get('description', '')[:2000]}

CRITERIOS DE EVALUACIÓN:
- El candidato busca roles Sr Backend/Full Stack con Java, Spring Boot, Microservices, Cloud
- Prefiere remoto o híbrido en CDMX
- NO le interesan: frontend puro, QA, data science, DevOps/SRE puro, SAP, Salesforce
- Score >= 75 significa que el candidato tiene experiencia directa con las tecnologías clave del puesto
- Score >= 90 significa match casi perfecto en stack, seniority y modalidad
- Score < 50 para roles que no coinciden con su perfil (ej: frontend puro, tecnologías que no domina)

Responde SOLO con JSON válido:
{{
  "score": 85,
  "reasons": "Explicación breve de por qué este score (máx 2 oraciones)",
  "missing_skills": ["skill1", "skill2"],
  "strengths": ["fortaleza1", "fortaleza2"]
}}
"""

    try:
        content = coordinator.invoke("job_match", [HumanMessage(content=prompt)]).strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        result = json.loads(content)
        return result.get("score", 0), result.get("reasons", "")
    except Exception as e:
        logger.error(f"Error evaluando match de job: {e}")
        return 0, "Error en evaluación"


def generate_cover_letter(
    job: Dict[str, Any],
    resume: Dict[str, Any],
) -> str:
    """Genera una cover letter personalizada para el trabajo."""
    prompt = f"""Escribe una cover letter breve y profesional para esta postulación.

Candidato:
- Nombre: {resume.get('full_name', 'El candidato')}
- Rol: {resume.get('professional_title', '')}
- Experiencia: {resume.get('years_of_experience', 0)} años
- Skills principales: {', '.join(resume.get('technical_skills', [])[:8])}
- Logros: {'; '.join(resume.get('achievements', [])[:3])}

Puesto:
- Título: {job.get('title', '')}
- Empresa: {job.get('company', '')}
- Descripción: {job.get('description', '')[:1000]}

La cover letter debe:
- Ser en el idioma de la oferta (español si es en español, inglés si es en inglés)
- Ser concisa (máx 200 palabras)
- Destacar 2-3 logros relevantes al puesto
- Terminar con llamada a la acción
- Sonar humana y entusiasta, no genérica

Escribe SOLO la cover letter, sin encabezados ni formateo extra.
"""

    try:
        return coordinator.invoke("cover_letter", [HumanMessage(content=prompt)]).strip()
    except Exception as e:
        logger.error(f"Error generando cover letter: {e}")
        return ""


def analyze_email_response(
    email_content: str,
    email_subject: str,
    from_address: str,
) -> Dict[str, Any]:
    """
    Analiza un email de respuesta de empresa.

    Returns:
        Dict con: sentiment, action, summary, interview_date (si aplica),
                  reply_text (si hay que responder), job_company_hint
    """
    prompt = f"""Analiza este email de respuesta de una empresa a una solicitud de trabajo.

De: {from_address}
Asunto: {email_subject}
Contenido:
{email_content[:2000]}

Responde SOLO con JSON válido:
{{
  "sentiment": "positive|negative|interview|neutral|followup_needed",
  "summary": "Resumen de 1 oración de qué dice el email",
  "action": "none|schedule_interview|send_followup|update_rejected|wait",
  "interview_date_hint": "fecha mencionada o null",
  "interview_link": "link de videollamada o null",
  "interviewer_email": "email del entrevistador o null",
  "company_name": "nombre de la empresa inferido",
  "job_title_hint": "título del puesto inferido",
  "reply_needed": false,
  "suggested_reply": "texto de respuesta si reply_needed es true, sino null"
}}

sentiments:
- positive: interesados pero sin entrevista aún
- negative: rechazo
- interview: convocan a entrevista
- neutral: acuse de recibo / auto-respuesta
- followup_needed: llevan mucho tiempo sin responder (no aplica aquí)
"""

    try:
        content = coordinator.invoke("email_analysis", [HumanMessage(content=prompt)]).strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        return json.loads(content)
    except Exception as e:
        logger.error(f"Error analizando email: {e}")
        return {
            "sentiment": "neutral",
            "summary": "No se pudo analizar el email",
            "action": "none",
            "interview_date_hint": None,
            "interview_link": None,
            "interviewer_email": None,
            "company_name": "",
            "job_title_hint": "",
            "reply_needed": False,
            "suggested_reply": None,
        }


def generate_followup_email(
    job: Dict[str, Any],
    resume: Dict[str, Any],
    days_since_apply: int,
) -> Dict[str, str]:
    """
    Genera email de follow-up para una aplicación sin respuesta.

    Returns:
        Dict con: subject, body
    """
    prompt = f"""Escribe un email de follow-up profesional para una aplicación de trabajo.

Han pasado {days_since_apply} días desde que apliqué y no he recibido respuesta.

Candidato: {resume.get('full_name', '')} ({resume.get('professional_title', '')})
Puesto aplicado: {job.get('title', '')}
Empresa: {job.get('company', '')}

El email debe:
- Ser breve (máx 100 palabras)
- Mencionar la aplicación original
- Expresar interés genuino
- Pedir actualización del estado
- Ser educado y profesional

Responde SOLO con JSON:
{{
  "subject": "asunto del email",
  "body": "cuerpo del email"
}}
"""

    try:
        content = coordinator.invoke("followup_email", [HumanMessage(content=prompt)]).strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        return json.loads(content)
    except Exception as e:
        logger.error(f"Error generando follow-up: {e}")
        return {
            "subject": f"Seguimiento - {job.get('title', 'Posición')}",
            "body": f"Estimado equipo de {job.get('company', 'la empresa')},\n\nMe comunico para dar seguimiento a mi aplicación para el puesto de {job.get('title', '')}. ¿Podría indicarme el estado de mi candidatura?\n\nQuedo a su disposición.\n\nSaludos,\n{resume.get('full_name', '')}",
        }


def handle_whatsapp_command(
    message: str,
    tracker_stats: Dict,
    resume: Dict,
) -> str:
    """
    Procesa un comando enviado por WhatsApp y genera respuesta.

    Returns:
        Texto de respuesta para enviar al usuario
    """
    prompt = f"""Eres un asistente de búsqueda de trabajo que responde por WhatsApp.

El usuario te envió: "{message}"

Estado actual:
{json.dumps(tracker_stats, ensure_ascii=False)}

CV del usuario:
- Nombre: {resume.get('full_name', '')}
- Rol: {resume.get('professional_title', '')}
- Skills: {', '.join(resume.get('technical_skills', [])[:5])}

Responde de forma concisa y útil. Usa emojis apropiados.
Si el usuario pide el estado/reporte, usa los datos del estado actual.
Si pide buscar trabajo, confirma que iniciarás búsqueda manual.
Si pide pausar/reanudar, confirma la acción.
Máximo 200 caracteres en tu respuesta.

IMPORTANTE: Responde SOLO el texto del mensaje, sin formato extra.
"""

    try:
        return coordinator.invoke("whatsapp_command", [HumanMessage(content=prompt)]).strip()
    except Exception as e:
        logger.error(f"Error procesando comando WhatsApp: {e}")
        return "Lo siento, no pude procesar tu mensaje. Intenta de nuevo."
