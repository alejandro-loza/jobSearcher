"""Factory de LLMs. GLM-4.7 como principal via ZhipuAI."""
from langchain_openai import ChatOpenAI
from config import settings
from loguru import logger


def get_llm(temperature: float = None, max_tokens: int = None) -> ChatOpenAI:
    """Retorna instancia de GLM-4.7 (ZhipuAI) compatible con OpenAI API."""
    llm = ChatOpenAI(
        model=settings.glm_model,
        api_key=settings.glm_api_key,
        base_url=settings.glm_base_url,
        temperature=temperature or settings.glm_temperature,
        max_tokens=max_tokens or settings.glm_max_tokens,
    )
    logger.debug(f"LLM: {settings.glm_model} @ {settings.glm_base_url}")
    return llm


def get_llm_for_agent(agent_type: str) -> ChatOpenAI:
    """LLM configurado por tipo de agente."""
    configs = {
        "job_searcher":          {"temperature": 0.5, "max_tokens": 3000},
        "resume_matcher":        {"temperature": 0.4, "max_tokens": 4000},
        "application_strategist":{"temperature": 0.7, "max_tokens": 5000},
        "interview_prepper":     {"temperature": 0.6, "max_tokens": 4000},
        "master":                {"temperature": 0.7, "max_tokens": 4096},
    }
    cfg = configs.get(agent_type, {})
    return get_llm(
        temperature=cfg.get("temperature"),
        max_tokens=cfg.get("max_tokens"),
    )
