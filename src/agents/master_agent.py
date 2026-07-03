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


# Empleo ACTUAL de Alejandro — línea base que toda vacante nueva debe SUPERAR.
# Aceptado jun-2026. Cambiar de trabajo solo tiene sentido si la nueva oferta es
# una mejor opción que esto. Ver modes/_profile.md.
CURRENT_JOB = {
    "empresa": "ISOL (Ingeniería de Soluciones), colocado en cliente Liverpool (El Puerto de Liverpool)",
    "rol": "Desarrollador Backend Java / Sr Software Engineer",
    "compensacion": "~$50,000 MXN mixta (≈25k nómina formal IMSS + 25k asimilados)",
    "modalidad": "Híbrida mixta: mitad presencial en CDMX, mitad remoto",
    "ingreso": "16 jun 2026",
}


def evaluate_job_match(
    job: Dict[str, Any],
    resume: Dict[str, Any],
) -> Tuple[int, str]:
    """
    Evalúa qué tan bien encaja un trabajo con el CV Y si es una MEJOR OPCIÓN que
    el empleo actual (CURRENT_JOB). Cambiar de trabajo solo vale la pena si la
    vacante supera lo que Alejandro ya tiene.

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

EMPLEO ACTUAL DE ALEJANDRO (línea base que la vacante DEBE superar):
- Empresa: {CURRENT_JOB['empresa']}
- Rol: {CURRENT_JOB['rol']}
- Compensación: {CURRENT_JOB['compensacion']}
- Modalidad: {CURRENT_JOB['modalidad']}

CRITERIOS DE EVALUACIÓN:
- El candidato busca roles Sr Backend/Full Stack con Java, Spring Boot, Microservices, Cloud
- Prefiere remoto o híbrido en CDMX
- NO le interesan: frontend puro, QA, data science, DevOps/SRE puro, SAP, Salesforce
- PISO SALARIAL: $60,000 MXN 100% nómina formal (IMSS). Si el salario mencionado en la oferta es < $60k nómina, el score MÁXIMO es 30.
  - Modalidad mixta (nómina + asimilados) solo si total ≥ $70k MXN → máximo score 60 si modalidad
  - Honorarios, freelance o por hora → score máximo 20 (auto-rechazo)
- REPUTACIÓN Y CRECIMIENTO: Si la empresa no tiene reputación conocida o el rol no tiene perspectiva de crecimiento clara → penalizar -10 puntos

CRITERIO CLAVE — ¿ES MEJOR OPCIÓN QUE EL EMPLEO ACTUAL?
Alejandro YA tiene empleo (el de arriba). Cambiarse solo vale la pena si la vacante es
CLARAMENTE una mejor opción. Pregúntate explícitamente: "¿esta vacante es mejor que lo
que ya tiene?" Una vacante es mejor si supera al empleo actual en al menos uno de estos
ejes SIN empeorar los demás de forma relevante:
  1. Compensación total claramente mayor (o mismo monto pero 100% nómina formal vs. mixta)
  2. Modalidad más favorable (100% remoto > híbrido mixto presencial/remoto)
  3. Empresa con mucha mejor reputación, estabilidad o crecimiento
  4. Rol con mejor seniority/impacto/tecnología
Reglas de tope por esta comparación:
  - Si la vacante NO es claramente mejor que el empleo actual → score MÁXIMO 55.
  - Si es peor tanto en compensación como en modalidad → score MÁXIMO 35.
  - Solo puede superar 75 si es estrictamente una MEJOR OPCIÓN que el empleo actual.
- Score >= 75: match técnico directo + salario sobre el piso + empresa con reputación + MEJOR opción que el empleo actual.
- Score >= 90: match casi perfecto en stack, seniority, modalidad y compensación, y claramente superior al empleo actual.
- Score < 50 para: roles que no coinciden con el perfil, salario bajo el piso, honorarios, empresa sin reputación, o vacantes que no superan al empleo actual.

Responde SOLO con JSON válido:
{{
  "score": 85,
  "better_than_current": true,
  "reasons": "Explicación breve incluyendo por qué es (o no) mejor opción que el empleo actual (máx 2 oraciones)",
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
        score = int(result.get("score", 0) or 0)
        reasons = result.get("reasons", "")
        better = result.get("better_than_current")

        # Red de seguridad determinista: si no supera al empleo actual, topamos el
        # score aunque el LLM lo haya puesto alto. Solo aplica si el modelo devolvió
        # el flag explícitamente (better is not None).
        if better is False and score > 55:
            logger.info(
                f"[match] '{job.get('title','')}' @ {job.get('company','')}: "
                f"no supera al empleo actual → tope 55 (LLM dio {score})"
            )
            score = 55
            reasons = f"[No supera al empleo actual ISOL/Liverpool] {reasons}"

        return score, reasons
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


_FOLLOWUP_TONE = {
    "first_apply":      "Primer follow-up, tono educado, recordar aplicación y expresar interés genuino.",
    "second_apply":     "Segundo (y último) follow-up, más breve que el primero, cerrar con invitación a responder aunque sea un 'no' para no quedar en limbo.",
    "responded_first":  "Reclutador ya respondió y no hemos avanzado en 1 día. Recordatorio breve y amable.",
    "responded_second": "Reclutador respondió pero conversación se enfrió (3+ días). Propón un próximo paso concreto.",
    "thank_you":        "Post-entrevista: agradecer tiempo del entrevistador, reforzar 1-2 puntos clave discutidos, reafirmar interés.",
}


def generate_followup_email(
    job: Dict[str, Any],
    resume: Dict[str, Any],
    days_since_apply: int,
    kind: Optional[str] = None,
) -> Dict[str, str]:
    """
    Genera email de follow-up. `kind` viene de followup_cadence.decide() y
    ajusta el tono del mensaje (first_apply, second_apply, responded_first,
    responded_second, thank_you).
    """
    tone = _FOLLOWUP_TONE.get(kind or "first_apply", _FOLLOWUP_TONE["first_apply"])

    prompt = f"""Escribe un email de follow-up profesional para una aplicación de trabajo.

Tipo de follow-up: {kind or 'first_apply'}
Contexto de tono: {tone}

Han pasado {days_since_apply} días desde el último contacto relevante.

Candidato: {resume.get('full_name', '')} ({resume.get('professional_title', '')})
Puesto aplicado: {job.get('title', '')}
Empresa: {job.get('company', '')}

El email debe:
- Ser breve (máx 100 palabras)
- Respetar el tono del tipo indicado
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
