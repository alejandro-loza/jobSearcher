"""
LLM Coordinator: enruta cada tarea al modelo óptimo.

Estrategia:
  QUALITY tasks (texto que va al mundo real) → GLM-4-Plus primero
  VOLUME tasks  (análisis interno, alta frecuencia) → Groq primero
  Siempre con fallback automático al siguiente disponible.

Tabla de routing:
  cover_letter       → GLM  (Alejandro lo envía, calidad importa)
  recruiter_reply    → GLM  (habla en nombre de Alejandro, tono/matiz)
  followup_email     → GLM  (va a empresas reales)
  refine_response    → GLM  (refinamiento de texto para enviar)
  job_match          → Groq (corre 100s de veces por búsqueda, rápido)
  email_analysis     → Groq (corre cada 30min, análisis estructurado)
  search_criteria    → Groq (una vez al inicio, tarea simple)
  whatsapp_command   → Groq (respuestas cortas, latencia importa)
  fallback           → SambaNova (cuando los otros fallan o rate-limit)
"""
from typing import Literal
from collections import defaultdict
from loguru import logger
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage

from config import settings

# Contador de tokens por proveedor y tarea (en memoria, se resetea al reiniciar)
_token_counter: dict = defaultdict(lambda: {"prompt": 0, "completion": 0, "calls": 0})

TaskType = Literal[
    "cover_letter",
    "recruiter_reply",
    "followup_email",
    "refine_response",
    "job_match",
    "email_analysis",
    "search_criteria",
    "whatsapp_command",
    "browser_vision",
    "content_generation",
    "content_validation",
    "hr_contact_note",
    "image_inspection",
    "response_decision",  # gatekeeper de respuestas (email + LinkedIn)
]

# Tareas que requieren calidad → GLM primero
QUALITY_TASKS = {
    "cover_letter", "recruiter_reply", "followup_email", "refine_response",
    "content_generation", "content_validation", "hr_contact_note",
}
# Tareas de volumen/velocidad → Groq primero (con fallback a GLM y SambaNova)
VOLUME_TASKS  = {
    "job_match", "email_analysis", "search_criteria", "whatsapp_command",
    "browser_vision", "image_inspection", "response_decision",
}


def _build_glm(temperature: float, max_tokens: int):
    return ChatOpenAI(
        model=settings.glm_model,
        api_key=settings.glm_api_key,
        base_url=settings.glm_base_url,
        temperature=temperature,
        max_tokens=max_tokens,
    )

def _build_groq(temperature: float, max_tokens: int):
    return ChatGroq(
        model=settings.groq_model,
        api_key=settings.groq_api_key,
        temperature=temperature,
        max_tokens=max_tokens,
    )

def _build_sambanova(temperature: float, max_tokens: int):
    return ChatOpenAI(
        model=settings.sambanova_model,
        api_key=settings.sambanova_api_key,
        base_url="https://api.sambanova.ai/v1",
        temperature=temperature,
        max_tokens=max_tokens,
    )


def invoke(
    task: TaskType,
    messages: list[BaseMessage],
    temperature: float = 0.7,
    max_tokens: int = 2048,
) -> str:
    """
    Invoca el LLM óptimo para la tarea dada, con fallback automático.

    Args:
        task: tipo de tarea (determina qué LLM usar primero)
        messages: lista de mensajes LangChain
        temperature: temperatura del modelo
        max_tokens: máximo de tokens en respuesta

    Returns:
        Contenido de la respuesta como string
    """
    providers = []

    if task in QUALITY_TASKS:
        # Orden: GLM → Groq → SambaNova
        if settings.glm_api_key:
            providers.append(("GLM-4-Plus", _build_glm(temperature, max_tokens)))
        if settings.groq_api_key:
            providers.append(("Groq", _build_groq(temperature, max_tokens)))
        if settings.sambanova_api_key:
            providers.append(("SambaNova", _build_sambanova(temperature, max_tokens)))
    else:
        # Orden: Groq → SambaNova → GLM
        if settings.groq_api_key:
            providers.append(("Groq", _build_groq(temperature, max_tokens)))
        if settings.sambanova_api_key:
            providers.append(("SambaNova", _build_sambanova(temperature, max_tokens)))
        if settings.glm_api_key:
            providers.append(("GLM-4-Plus", _build_glm(temperature, max_tokens)))

    if not providers:
        raise RuntimeError("No hay LLMs configurados.")

    last_error = None
    for name, llm in providers:
        try:
            response = llm.invoke(messages)
            # Contar tokens si están disponibles en usage_metadata
            usage = getattr(response, "usage_metadata", None) or getattr(response, "response_metadata", {}).get("token_usage", {})
            prompt_tokens = getattr(usage, "input_tokens", None) or (usage.get("prompt_tokens") if isinstance(usage, dict) else 0) or 0
            completion_tokens = getattr(usage, "output_tokens", None) or (usage.get("completion_tokens") if isinstance(usage, dict) else 0) or 0
            key = f"{name}:{task}"
            _token_counter[key]["prompt"] += prompt_tokens
            _token_counter[key]["completion"] += completion_tokens
            _token_counter[key]["calls"] += 1
            logger.debug(f"[coordinator] task={task} → {name} | tokens: +{prompt_tokens}p +{completion_tokens}c")
            return response.content
        except Exception as e:
            logger.warning(f"[coordinator] {name} falló para '{task}': {str(e)[:100]} — probando siguiente...")
            last_error = e

    raise RuntimeError(f"Todos los LLMs fallaron para task='{task}'. Último error: {last_error}")


def invoke_vision(
    task: TaskType,
    text_prompt: str,
    image_b64: str,
    temperature: float = 0.3,
    max_tokens: int = 2048,
) -> str:
    """
    Invoca un LLM con capacidad de visión (Groq Llama-4-Scout).
    Envía una imagen base64 junto con un prompt de texto.
    """
    from langchain_core.messages import HumanMessage as HM

    message = HM(content=[
        {"type": "text", "text": text_prompt},
        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}},
    ])

    # Groq vision model
    llm = ChatGroq(
        model=settings.groq_vision_model,
        api_key=settings.groq_api_key,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    try:
        response = llm.invoke([message])
        key = f"Groq-Vision:{task}"
        usage = getattr(response, "usage_metadata", None) or {}
        prompt_tokens = getattr(usage, "input_tokens", 0) or (usage.get("prompt_tokens", 0) if isinstance(usage, dict) else 0)
        completion_tokens = getattr(usage, "output_tokens", 0) or (usage.get("completion_tokens", 0) if isinstance(usage, dict) else 0)
        _token_counter[key]["prompt"] += prompt_tokens
        _token_counter[key]["completion"] += completion_tokens
        _token_counter[key]["calls"] += 1
        logger.debug(f"[coordinator] vision task={task} → Groq-Vision | tokens: +{prompt_tokens}p +{completion_tokens}c")
        return response.content
    except Exception as e:
        logger.error(f"[coordinator] Groq-Vision falló para '{task}': {str(e)[:150]}")
        raise


def get_token_stats() -> dict:
    """Retorna estadísticas de tokens usados desde el inicio del proceso."""
    stats = {}
    totals = defaultdict(lambda: {"prompt": 0, "completion": 0, "calls": 0})
    for key, counts in _token_counter.items():
        provider, task = key.split(":", 1)
        stats[key] = counts.copy()
        totals[provider]["prompt"] += counts["prompt"]
        totals[provider]["completion"] += counts["completion"]
        totals[provider]["calls"] += counts["calls"]
    return {"by_task": dict(stats), "by_provider": dict(totals)}
