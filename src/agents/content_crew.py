"""
Content Crew — pipeline multi-agente para posts de LinkedIn.

Implementa el patrón CrewAI (múltiples agentes + critic) usando LangChain
directamente. CrewAI 0.11.x es incompatible con Python 3.14; esta implementación
tiene la misma arquitectura conceptual sin la dependencia.

Flujo:
  1. 3 Writer Agents corren en paralelo (asyncio):
     - TipsWriter     → post formato tips/bullets
     - ComparisonWriter → post formato A vs B
     - StoryWriter    → post narrativo primera persona
  2. Critic Agent recibe los 3 outputs → selecciona el mejor → mejoras menores
  3. Retorna JSON estructurado con el post ganador + infographic_data
"""

import asyncio
import json
import re
from typing import Optional

from langchain_core.messages import HumanMessage, SystemMessage
from loguru import logger

from config import settings
from src.agents import coordinator


# ── Prompts base ──────────────────────────────────────────────────────────────

_ALEJANDRO_CONTEXT = """Estás escribiendo en nombre de Alejandro Hernandez Loza.
Senior Software Engineer, 12 años de experiencia. Stack: Java, Spring Boot,
Microservicios, Cloud (GCP/AWS), Docker, Kubernetes, IA con agentes LLM.
Ubicación: Ciudad de México. Trabaja remotamente.
Audiencia: developers, tech leads y CTOs de México y LATAM.
Idioma: ESPAÑOL. Límite: máximo 1300 caracteres incluyendo hashtags."""

_RULES = """REGLAS OBLIGATORIAS:
- NO incluyas código fuente ni snippets
- NO inventes estadísticas ni métricas sin fuente oficial verificable
- Solo hechos de documentación oficial o ampliamente conocidos en la industria
- Tono: profesional con autoridad técnica, accesible
- Primera persona a veces: "En mi experiencia...", "¿Sabías que...", "Hoy aprendí..."

FORMATO — retorna ÚNICAMENTE este JSON:
{
  "text": "texto completo del post con hashtags al final (máx 1300 chars)",
  "hashtags": ["#Tag1", "#Tag2", "#Tag3"],
  "infographic_data": {
    "type": "tips|comparison|flow",
    "title": "Título corto (máx 5 palabras)",
    "subtitle": "Subtítulo explicativo (máx 8 palabras)",
    "tips": [{"icon": "⚡", "title": "Título corto", "description": "Desc. verificable (máx 10 palabras)"}],
    "left_label": "Opción A (si type=comparison)",
    "right_label": "Opción B (si type=comparison)",
    "comparisons": [{"aspect": "Criterio", "left": "valor", "right": "valor"}],
    "steps": [{"step": "1", "title": "Acción corta", "description": "Qué ocurre (máx 10 palabras)"}]
  },
  "style": "tips|comparison|story"
}"""


def _extract_json(raw: str) -> Optional[dict]:
    """Extrae JSON de respuesta LLM con múltiples estrategias."""
    for strategy in [
        lambda t: json.loads(t.strip()),
        lambda t: json.loads(re.search(r"```(?:json)?\s*(\{.*?\})\s*```", t, re.DOTALL).group(1)),
        lambda t: json.loads(re.search(r"\{.*\}", t, re.DOTALL).group(0)),
    ]:
        try:
            return strategy(raw)
        except Exception:
            continue
    return None


# ── Writers (paralelo) ────────────────────────────────────────────────────────

async def _run_writer(style: str, topic: str, feedback: str = "") -> dict:
    """Ejecuta un writer agent con el estilo dado."""

    style_instructions = {
        "tips": f"""Crea un post en formato TIPS/LISTA sobre: {topic}
Usa type="tips" en infographic_data. Incluye 4-6 tips concisos y 100% verificables.
Los tips deben ser prácticos, con títulos de máximo 4 palabras y descripciones de máximo 10 palabras.""",

        "comparison": f"""Crea un post en formato COMPARACIÓN sobre: {topic}
Compara dos enfoques, versiones o tecnologías relacionadas.
Usa type="comparison" en infographic_data. Incluye 4-6 aspectos comparados con valores concretos.
Aspectos cortos (máx 3 palabras), valores cortos (máx 5 palabras cada uno).""",

        "story": f"""Crea un post NARRATIVO en primera persona sobre: {topic}
Comienza con una anécdota o reflexión personal. Genera conexión emocional.
Usa type="flow" en infographic_data. Muestra el proceso/arquitectura como 4-6 pasos.
Títulos de pasos: máx 4 palabras. Descripciones: máx 10 palabras.""",
    }

    feedback_section = f"\n\nFEEDBACK DE INTENTO ANTERIOR (corrígelo obligatoriamente):\n{feedback}" if feedback else ""

    system = SystemMessage(content=f"{_ALEJANDRO_CONTEXT}\n\n{_RULES}")
    human = HumanMessage(content=f"""{style_instructions[style]}{feedback_section}

Recuerda: máximo 1300 caracteres totales, SOLO hechos verificables.""")

    try:
        raw = await asyncio.to_thread(
            coordinator.invoke, "content_generation", [system, human], 0.8, 2048
        )
        parsed = _extract_json(raw)
        if parsed and parsed.get("text"):
            parsed["style"] = style
            logger.debug(f"[content_crew] Writer {style}: {len(parsed.get('text',''))} chars")
            return parsed
        # Fallback si no parsea JSON
        return {"text": raw[:1300], "hashtags": ["#Java", "#SoftwareEngineering"], "infographic_data": {}, "style": style}
    except Exception as e:
        logger.error(f"[content_crew] Writer {style} falló: {e}")
        return {}


# ── Critic ────────────────────────────────────────────────────────────────────

def _run_critic(variants: dict, topic: str) -> dict:
    """
    Critic agent: recibe las 3 variantes, selecciona la mejor, aplica mejoras.
    """
    variants_summary = []
    for style, v in variants.items():
        if v and v.get("text"):
            variants_summary.append(
                f"=== VARIANTE {style.upper()} ===\n"
                f"TEXTO ({len(v['text'])} chars):\n{v['text']}\n"
                f"INFOGRAFÍA type={v.get('infographic_data', {}).get('type', '?')}: "
                f"title='{v.get('infographic_data', {}).get('title', '')}'"
            )

    if not variants_summary:
        raise ValueError("Todas las variantes fallaron")

    system = SystemMessage(content="""Eres un experto en LinkedIn B2B content para ingenieros senior en LATAM.
Has analizado miles de posts de tech leaders. Conoces qué genera engagement genuino en developers y CTOs.
Eres riguroso con la precisión técnica y el formato de infografías.""")

    human = HumanMessage(content=f"""Analiza estas variantes de post sobre '{topic}' y selecciona la mejor.

{chr(10).join(variants_summary)}

Criterios de evaluación (1-10 cada uno):
1. ENGAGEMENT: ¿generará likes, comentarios, compartidos genuinos?
2. PRECISIÓN TÉCNICA: ¿todos los datos son verificables y correctos?
3. AUTENTICIDAD: ¿suena genuinamente a un senior dev de CDMX con 12 años exp?
4. VALOR EDUCATIVO: ¿el lector aprende algo concreto y aplicable?
5. INFOGRAFÍA: ¿títulos cortos (≤4 palabras)? ¿descripciones concisas (≤10 palabras)? ¿sin truncado?

Selecciona la mejor variante. Puedes aplicar mejoras menores al texto e infografía (no inventar datos).

Retorna ÚNICAMENTE este JSON:
{{
  "selected_style": "tips|comparison|story",
  "scores": {{"tips": X, "comparison": Y, "story": Z}},
  "text": "texto final del post ganador (con posibles mejoras menores)",
  "hashtags": ["#tag1", "#tag2"],
  "infographic_data": {{...datos de infographic_data del ganador con posibles mejoras...}},
  "improvements": "descripción breve de mejoras aplicadas (si las hiciste)",
  "rejection_reasons": "por qué descartaste las otras variantes"
}}""")

    raw = coordinator.invoke("content_generation", [system, human], 0.3, 3000)
    parsed = _extract_json(raw)

    if parsed and parsed.get("text"):
        return {
            "text": parsed.get("text", ""),
            "hashtags": parsed.get("hashtags", []),
            "infographic_data": parsed.get("infographic_data", {}),
            "style_used": parsed.get("selected_style", "tips"),
            "scores": parsed.get("scores", {}),
            "improvements": parsed.get("improvements", ""),
        }

    # Fallback: retorna la mejor variante disponible directamente
    logger.warning("[content_crew] Critic no retornó JSON válido, usando mejor variante directamente")
    best = max(
        ((s, v) for s, v in variants.items() if v and v.get("text")),
        key=lambda x: len(x[1].get("text", "")),
        default=(None, None),
    )
    if best[1]:
        return {
            "text": best[1].get("text", ""),
            "hashtags": best[1].get("hashtags", []),
            "infographic_data": best[1].get("infographic_data", {}),
            "style_used": best[0],
            "scores": {},
        }
    raise ValueError("Critic no pudo seleccionar variante")


# ── Entry point ───────────────────────────────────────────────────────────────

def run_content_crew(topic: str, feedback: str = "") -> dict:
    """
    Ejecuta el pipeline multi-agente completo.

    Args:
        topic: tema del post
        feedback: feedback del image_inspector de un intento previo

    Returns:
        dict con: text, hashtags, infographic_data, style_used, scores
    """
    logger.info(f"[content_crew] Iniciando crew para: '{topic}'")
    if feedback:
        logger.info(f"[content_crew] Feedback: {feedback[:120]}")

    # Paso 1: 3 writers en paralelo
    async def run_writers():
        tasks = [
            _run_writer("tips", topic, feedback),
            _run_writer("comparison", topic, feedback),
            _run_writer("story", topic, feedback),
        ]
        return await asyncio.gather(*tasks)

    tips_result, comparison_result, story_result = asyncio.run(run_writers())

    variants = {
        "tips": tips_result,
        "comparison": comparison_result,
        "story": story_result,
    }

    valid = {k: v for k, v in variants.items() if v and v.get("text")}
    logger.info(f"[content_crew] Writers completados: {list(valid.keys())}")

    if not valid:
        raise RuntimeError("Todos los writers fallaron")

    # Paso 2: Critic selecciona la mejor
    result = _run_critic(valid, topic)

    logger.success(
        f"[content_crew] Critic eligió: {result.get('style_used')} | "
        f"{len(result.get('text', ''))} chars"
    )
    return result
