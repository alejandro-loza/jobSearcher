"""
LinkedIn Content Agent.

Generates and publishes LinkedIn posts about tech topics relevant to Alejandro's profile.
Uses:
  - coordinator.invoke() for text generation (GLM/Groq/SambaNova)
  - ZhipuAI CogView-3-Plus for image generation
  - linkedin_post_tool.post_to_linkedin() for publishing
  - data/linkedin_posts_log.json for tracking posted topics
"""
import json
import os
import time
from datetime import datetime, timedelta
from typing import Optional

import requests
from langchain_core.messages import HumanMessage, SystemMessage
from loguru import logger

from config import settings
from src.agents import coordinator
from src.tools import linkedin_post_tool

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

POSTS_LOG_FILE = "data/linkedin_posts_log.json"

TECH_TOPICS = [
    # Java & Spring Boot
    "Java 21 virtual threads y concurrencia estructurada",
    "Java 21 records y sealed classes para domain modeling",
    "Java 21 pattern matching con switch expressions",
    "Spring Boot 3.x native compilation con GraalVM",
    "Spring Boot 3.x observability con Micrometer y Grafana",
    "Spring Boot Security con OAuth2 y JWT best practices",
    "Groovy metaprogramming y DSLs en proyectos reales",
    "Grails GORM patterns y consultas avanzadas",
    # Inteligencia Artificial
    "Claude Code: cómo los agentes de IA están transformando el desarrollo de software",
    "Prompt engineering para desarrolladores: mejores prácticas con LLMs",
    "RAG (Retrieval Augmented Generation): arquitectura y casos de uso reales",
    "AI Agents vs chatbots: por qué los agentes autónomos son el futuro",
    "Cómo integrar LLMs en aplicaciones empresariales Java",
    "MCP (Model Context Protocol): el estándar abierto para conectar IA con herramientas",
    "Fine-tuning vs prompting: cuándo usar cada estrategia",
    "IA generativa en producción: lecciones aprendidas y antipatrones",
    # Arquitectura de Software
    "Arquitectura hexagonal (ports and adapters): principios y beneficios",
    "Event-driven architecture con Kafka: patrones clave para microservicios",
    "Saga pattern para transacciones distribuidas en microservicios",
    "Circuit breaker con Resilience4j: resiliencia en arquitecturas distribuidas",
    "Outbox pattern para consistencia eventual en microservicios",
    "Domain-Driven Design: bounded contexts y aggregate roots en la práctica",
    "CQRS: separar lecturas y escrituras para escalar mejor",
    "API Gateway patterns: rate limiting, autenticación y routing inteligente",
    # Cloud & DevOps
    "Docker multi-stage builds para optimizar imágenes de producción",
    "Kubernetes HPA y VPA: autoscaling inteligente en la nube",
    "GCP Cloud Run para backends serverless en Java",
    "AWS Lambda con Spring Boot: estrategias para reducir cold starts",
    "Infrastructure as Code con Terraform: mejores prácticas",
    "Observabilidad moderna: métricas, logs y traces con OpenTelemetry",
]

POSTING_SCHEDULE = [
    {"hour": 9, "minute": 0},    # mañana
    {"hour": 14, "minute": 30},  # tarde
    {"hour": 18, "minute": 0},   # noche
]

# ZhipuAI CogView API
_COGVIEW_URL = "https://open.bigmodel.cn/api/paas/v4/images/generations"
_COGVIEW_MODEL = "cogview-4-250304"


# ---------------------------------------------------------------------------
# Log helpers
# ---------------------------------------------------------------------------

def _load_log() -> dict:
    """Load the posts log from disk."""
    if not os.path.exists(POSTS_LOG_FILE):
        return {"posts": [], "topics_used": []}
    try:
        with open(POSTS_LOG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"[content_agent] Error loading posts log: {e}")
        return {"posts": [], "topics_used": []}


def _save_log(log: dict) -> None:
    """Persist the posts log to disk."""
    try:
        os.makedirs("data", exist_ok=True)
        with open(POSTS_LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(log, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"[content_agent] Error saving posts log: {e}")


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------

def select_next_topic() -> str:
    """Pick next topic to post about. Rotates through topics, avoids recent ones.
    Saves last used topics to data/linkedin_posts_log.json."""
    log = _load_log()
    topics_used = log.get("topics_used", [])

    # Filter out topics used in the last 20 posts to avoid repetition
    recent = set(topics_used[-20:]) if len(topics_used) >= 20 else set(topics_used)
    available = [t for t in TECH_TOPICS if t not in recent]

    if not available:
        # All topics used recently; restart rotation
        available = TECH_TOPICS
        logger.info("[content_agent] All topics used recently, restarting rotation")

    # Pick the first available (deterministic rotation)
    chosen = available[0]
    logger.info(f"[content_agent] Selected topic: {chosen}")
    return chosen


def generate_post_content(topic: str) -> dict:
    """Generate post text and image prompt for a given topic.
    Returns: {text: str, image_prompt: str, hashtags: list}"""
    system_msg = SystemMessage(content="""Eres un experto en tecnología y ghostwriter para LinkedIn.
Escribes posts en español para Alejandro Hernandez Loza, Senior Software Engineer con 12 años de experiencia
en Java, Spring Boot, Microservicios, Cloud (GCP/AWS), Docker, Kubernetes e Inteligencia Artificial, basado en CDMX.

Estilo de posts:
- Profesionales, educativos y con perspectiva de industria
- Descripciones claras y accesibles, SIN código fuente ni snippets
- En primera persona algunas veces: "Hoy aprendí...", "¿Sabías que...", "En mi experiencia..."
- Máximo 1300 caracteres (límite de LinkedIn)
- Incluye 3-5 hashtags relevantes al final
- Audiencia: developers, tech leads y CTOs de México y LATAM
- Tono: profesional, con autoridad técnica, pero accesible

IMPORTANTE: NO incluyas código fuente, snippets, ni bloques de código.
Los posts deben ser descripciones profesionales con conceptos, beneficios y casos de uso.

Formato de respuesta (JSON):
{
  "text": "texto completo del post con hashtags al final",
  "hashtags": ["#Java", "#SpringBoot", ...],
  "infographic_data": {
    "type": "tips|comparison|flow",
    "title": "título de la infografía",
    "subtitle": "subtítulo",
    // Si type=tips:
    "tips": [{"icon": "⚡", "title": "Concepto clave", "description": "Explicación profesional con datos VERIFICABLES"}],
    // Si type=comparison:
    "left_label": "Opción A",
    "right_label": "Opción B",
    "comparisons": [{"aspect": "Criterio", "left": "valor", "right": "valor"}],
    // Si type=flow:
    "steps": [{"step": "1", "title": "Paso", "description": "Qué sucede en este paso"}]
  }
}

REGLAS PARA LA INFOGRAFÍA:
- TODOS los datos deben ser 100% verificables (versiones, nombres de APIs, métricas)
- NO inventes números — usa solo datos de documentación oficial
- NUNCA incluir código fuente — solo descripciones profesionales
- Alterna entre los 3 tipos (tips, comparison, flow) para variedad
- Tipo "flow" es ideal para explicar arquitecturas, pipelines y procesos""")

    human_msg = HumanMessage(content=f"Crea un post de LinkedIn sobre: {topic}")

    try:
        raw = coordinator.invoke(
            "content_generation",
            [system_msg, human_msg],
            temperature=0.8,
            max_tokens=1024,
        )

        # Parse JSON — try multiple extraction strategies
        result = _extract_json(raw)
        if result and "text" in result:
            if len(result.get("text", "")) > 1300:
                result["text"] = result["text"][:1297] + "..."
            logger.info(f"[content_agent] Generated post content for topic: {topic}")
            return result

        # Fallback: treat entire response as post text
        logger.warning("[content_agent] Could not parse JSON from LLM, using raw text")
        text = raw.strip()
        # Remove markdown code fences if present
        if text.startswith("```"):
            text = "\n".join(text.split("\n")[1:])
        if text.endswith("```"):
            text = text[:-3].strip()
        text = text[:1300]
        return {
            "text": text,
            "image_prompt": f"abstract geometric illustration representing {topic}, no text, no letters, dark gradient background, blue and cyan glowing shapes, minimalist tech style",
            "hashtags": ["#Java", "#SpringBoot", "#SoftwareEngineering"],
        }
    except Exception as e:
        logger.error(f"[content_agent] Error generating post content: {e}")
        raise


def _extract_json(raw: str) -> Optional[dict]:
    """Try to extract JSON from LLM response using multiple strategies."""
    import re
    # Strategy 1: direct parse
    try:
        return json.loads(raw.strip())
    except json.JSONDecodeError:
        pass
    # Strategy 2: find JSON in markdown code block
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    # Strategy 3: find first { ... } block
    m = re.search(r"\{.*\}", raw, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass
    return None


def _regenerate_post_content(topic: str, previous_issues: str) -> dict:
    """Regenerate post content incorporating feedback from validation failures.
    Instructs the LLM to avoid the specific issues found in previous attempts."""
    system_msg = SystemMessage(content="""Eres un experto en tecnología y ghostwriter para LinkedIn.
Escribes posts en español para Alejandro Hernandez Loza, Senior Software Engineer con 12 años de experiencia
en Java, Spring Boot, Microservicios, Cloud (GCP/AWS), Docker, Kubernetes e Inteligencia Artificial, basado en CDMX.

Estilo de posts:
- Profesionales, educativos y con perspectiva de industria
- Descripciones claras y accesibles, SIN código fuente ni snippets
- En primera persona algunas veces: "Hoy aprendí...", "¿Sabías que...", "En mi experiencia..."
- Máximo 1300 caracteres (límite de LinkedIn)
- Incluye 3-5 hashtags relevantes al final
- Audiencia: developers, tech leads y CTOs de México y LATAM
- Tono: profesional, con autoridad técnica, pero accesible

IMPORTANTE: NO incluyas código fuente, snippets, ni bloques de código.
Los posts deben ser descripciones profesionales con conceptos, beneficios y casos de uso.

REGLA CRÍTICA: NO inventes estadísticas, porcentajes ni métricas que no puedas respaldar
con fuentes oficiales. Si mencionas un dato numérico, debe ser de documentación oficial
o ampliamente conocido en la industria. Prefiere descripciones cualitativas sobre cuantitativas
a menos que el dato sea verificable.

Formato de respuesta (JSON):
{
  "text": "texto completo del post con hashtags al final",
  "hashtags": ["#Java", "#SpringBoot", ...],
  "infographic_data": {
    "type": "tips|comparison|flow",
    "title": "título de la infografía",
    "subtitle": "subtítulo",
    // Si type=tips:
    "tips": [{"icon": "⚡", "title": "Concepto clave", "description": "Explicación profesional con datos VERIFICABLES"}],
    // Si type=comparison:
    "left_label": "Opción A",
    "right_label": "Opción B",
    "comparisons": [{"aspect": "Criterio", "left": "valor", "right": "valor"}],
    // Si type=flow:
    "steps": [{"step": "1", "title": "Paso", "description": "Qué sucede en este paso"}]
  }
}

REGLAS PARA LA INFOGRAFÍA:
- TODOS los datos deben ser 100% verificables (versiones, nombres de APIs, métricas)
- NO inventes números — usa solo datos de documentación oficial
- NUNCA incluir código fuente — solo descripciones profesionales
- Alterna entre los 3 tipos (tips, comparison, flow) para variedad
- Tipo "flow" es ideal para explicar arquitecturas, pipelines y procesos""")

    human_msg = HumanMessage(content=f"""Crea un post de LinkedIn sobre: {topic}

ATENCIÓN: Un intento anterior fue rechazado por el validador técnico con estos problemas:
{previous_issues}

Por favor corrige esos errores. NO inventes estadísticas ni porcentajes.
Usa solo hechos verificables y ampliamente conocidos.""")

    try:
        raw = coordinator.invoke(
            "content_generation",
            [system_msg, human_msg],
            temperature=0.7,
            max_tokens=1024,
        )

        result = _extract_json(raw)
        if result and "text" in result:
            if len(result.get("text", "")) > 1300:
                result["text"] = result["text"][:1297] + "..."
            logger.info(f"[content_agent] Regenerated post content for topic: {topic}")
            return result

        # Fallback
        text = raw.strip()
        if text.startswith("```"):
            text = "\n".join(text.split("\n")[1:])
        if text.endswith("```"):
            text = text[:-3].strip()
        text = text[:1300]
        return {
            "text": text,
            "image_prompt": f"abstract geometric illustration representing {topic}, no text, no letters, dark gradient background, blue and cyan glowing shapes, minimalist tech style",
            "hashtags": ["#Java", "#SpringBoot", "#SoftwareEngineering"],
        }
    except Exception as e:
        logger.error(f"[content_agent] Error regenerating post content: {e}")
        raise


def generate_image(image_prompt: str) -> Optional[str]:
    """Generate image using CogView-3-Plus, save to /tmp/, return file path.
    Returns None if generation fails."""
    if not settings.glm_api_key:
        logger.warning("[content_agent] GLM API key not set, skipping image generation")
        return None

    try:
        headers = {
            "Authorization": f"Bearer {settings.glm_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": _COGVIEW_MODEL,
            "prompt": image_prompt,
            "size": "1024x1024",
            "n": 1,
        }

        logger.info(f"[content_agent] Generating image: {image_prompt[:80]}...")
        resp = requests.post(_COGVIEW_URL, headers=headers, json=payload, timeout=60)
        resp.raise_for_status()

        data = resp.json()
        image_url = data["data"][0]["url"]

        # Download image to data/linkedin_images/
        os.makedirs("data/linkedin_images", exist_ok=True)
        timestamp = int(time.time())
        local_path = f"data/linkedin_images/linkedin_post_{timestamp}.png"

        img_resp = requests.get(image_url, timeout=30)
        img_resp.raise_for_status()
        with open(local_path, "wb") as f:
            f.write(img_resp.content)

        logger.info(f"[content_agent] Image saved to: {local_path}")
        return local_path

    except Exception as e:
        logger.error(f"[content_agent] Image generation error: {e}")
        return None


def validate_content(text: str, topic: str) -> bool:
    """Validate that the post content is factually accurate. Returns True/False."""
    valid, _ = validate_content_with_details(text, topic)
    return valid


def validate_content_with_details(text: str, topic: str) -> tuple[bool, str]:
    """Validate post content is factually accurate. Returns (is_valid, validation_notes).

    Checks:
    - Versiones correctas de frameworks/lenguajes mencionados
    - Nombres de APIs/clases/métodos reales
    - Números y estadísticas plausibles
    - No afirmaciones falsas sobre tecnologías
    """
    system_msg = SystemMessage(content="""Eres un revisor técnico ESTRICTO experto en Java, Spring Boot,
microservicios y cloud computing. Tu tarea es verificar CADA dato técnico del post:

1. ¿Las versiones mencionadas son correctas? (ej: Java 21 sí tiene virtual threads)
2. ¿Los nombres de clases/métodos/APIs existen realmente?
3. ¿Los números y estadísticas son plausibles y verificables?
4. ¿Las comparaciones son justas y correctas?
5. ¿Hay afirmaciones exageradas o incorrectas?

Responde SOLO con un JSON:
{
  "valid": true/false,
  "facts_checked": ["dato 1 verificado: CORRECTO", "dato 2: INCORRECTO porque..."],
  "issues": ["lista de errores si los hay"],
  "confidence": 0.0-1.0
}

Marca valid: false si hay CUALQUIER error factual. Sé estricto.""")

    human_msg = HumanMessage(content=f"Tema: {topic}\n\nPost:\n{text}")

    try:
        raw = coordinator.invoke(
            "content_validation",
            [system_msg, human_msg],
            temperature=0.1,
            max_tokens=512,
        )

        result = _extract_json(raw)
        if not result:
            return True, "No se pudo parsear validación, asumiendo válido"

        is_valid = result.get("valid", True)
        facts = result.get("facts_checked", [])
        issues = result.get("issues", [])
        confidence = result.get("confidence", 0.5)

        notes = f"Confidence: {confidence}. "
        if facts:
            notes += "Facts: " + "; ".join(facts[:5]) + ". "
        if issues:
            notes += "Issues: " + "; ".join(issues)

        if not is_valid:
            logger.warning(f"[content_agent] Validation FAILED: {notes}")
        else:
            logger.info(f"[content_agent] Validation PASSED: {notes[:100]}")

        return is_valid, notes

    except Exception as e:
        logger.warning(f"[content_agent] Validation error: {e}")
        return False, f"Error en validación: {e}"  # Si falla la validación, NO publicar


def _generate_infographic(infographic_data: dict, topic: str) -> Optional[str]:
    """Genera la infografía apropiada según el tipo. Retorna ruta PNG o None."""
    if not infographic_data:
        return None
    try:
        from src.tools.infographic_tool import (
            generate_comparison_infographic,
            generate_flow_infographic,
            generate_tips_infographic,
        )
        inf_type = infographic_data.get("type", "tips")
        if inf_type == "tips":
            return generate_tips_infographic(
                title=infographic_data.get("title", topic),
                subtitle=infographic_data.get("subtitle", ""),
                tips=infographic_data.get("tips", []),
            )
        elif inf_type == "comparison":
            return generate_comparison_infographic(
                title=infographic_data.get("title", topic),
                subtitle=infographic_data.get("subtitle", ""),
                left_label=infographic_data.get("left_label", "Antes"),
                right_label=infographic_data.get("right_label", "Después"),
                comparisons=infographic_data.get("comparisons", []),
            )
        elif inf_type == "flow":
            return generate_flow_infographic(
                title=infographic_data.get("title", topic),
                subtitle=infographic_data.get("subtitle", ""),
                steps=infographic_data.get("steps", []),
            )
    except Exception as e:
        logger.error(f"[content_agent] Infographic generation failed: {e}")
    return None


def _inspector_feedback(inspection: dict) -> str:
    """Convierte resultado de image_inspector en feedback legible para el crew."""
    issues = []
    fa = inspection.get("factual_accuracy", {})
    dq = inspection.get("design_quality", {})
    if not fa.get("passed"):
        issues.append(f"Precisión factual insuficiente (score {fa.get('confidence',0):.2f}): {(fa.get('notes') or '')[:200]}")
    if not dq.get("passed"):
        issues.append(f"Diseño insuficiente (score {dq.get('score',0)}/100): {(dq.get('notes') or '')[:200]}")
    extracted = inspection.get("extracted_text", {})
    if not extracted.get("all_text_readable", True):
        issues.append("Texto truncado u overlapping en la infografía — usa títulos más cortos (máx 4 palabras)")
    return " | ".join(issues) if issues else "Inspección falló por razón desconocida"


def create_and_publish_post(max_retries: int = 2) -> bool:
    """
    Pipeline completo con CrewAI: 3 Writers → Critic → Infografía → Inspección.
    NUNCA publica directamente. Todo queda pendiente de aprobación de Alejandro.

    Flujo:
      1. Crew genera 3 variantes (tips, comparison, story)
      2. Critic elige la mejor y la mejora
      3. Se genera la infografía
      4. image_inspector valida hechos + diseño
      5. Si falla → retry con feedback al crew (max_retries veces)
      6. Si pasa → guarda como pending_review
    """
    from src.agents import content_crew, image_inspector_agent

    log = _load_log()
    topic = select_next_topic()
    feedback = ""

    for attempt in range(max_retries + 1):
        logger.info(f"[content_agent] Crew attempt {attempt + 1}/{max_retries + 1} for '{topic}'")

        # ── Paso 1: Crew genera y critica ──
        try:
            content = content_crew.run_content_crew(topic, feedback=feedback)
        except Exception as e:
            logger.error(f"[content_agent] Crew failed (attempt {attempt + 1}): {e}")
            if attempt < max_retries:
                feedback = f"Error en generación anterior: {str(e)[:100]}"
                continue
            return False

        post_text = content.get("text", "")
        if not post_text:
            logger.error("[content_agent] Crew returned empty text")
            continue

        # ── Paso 2: Generar infografía ──
        image_path = _generate_infographic(content.get("infographic_data", {}), topic)

        # ── Paso 3: Inspeccionar imagen ──
        post_entry = {
            "topic": topic,
            "text": post_text,
            "hashtags": content.get("hashtags", []),
            "image_path": image_path,
            "infographic_data": content.get("infographic_data", {}),
            "style_used": content.get("style_used", "unknown"),
            "crew_scores": content.get("scores", {}),
            "generated_at": datetime.now().isoformat(),
            "status": "pending_review",
            "published": False,
        }

        if image_path:
            inspection = image_inspector_agent.inspect_image(post_entry)
            if inspection.get("passed"):
                logger.success(f"[content_agent] Inspección OK (intento {attempt + 1}). Guardando para revisión.")
                post_entry["inspection"] = inspection
                log["posts"].append(post_entry)
                log["topics_used"] = log.get("topics_used", []) + [topic]
                _save_log(log)
                return True
            else:
                feedback = _inspector_feedback(inspection)
                logger.warning(
                    f"[content_agent] Inspección FALLÓ (intento {attempt + 1}): {feedback[:120]}"
                )
                # Borrar imagen fallida
                if image_path and os.path.exists(image_path):
                    os.remove(image_path)
        else:
            # Sin imagen: guardar de todos modos (publicará solo texto)
            logger.info(f"[content_agent] Sin imagen. Guardando post de texto para revisión.")
            log["posts"].append(post_entry)
            log["topics_used"] = log.get("topics_used", []) + [topic]
            _save_log(log)
            return True

    logger.error(f"[content_agent] Agotados {max_retries + 1} intentos para '{topic}'")
    return False


def approve_and_publish(post_index: int = -1) -> bool:
    """Aprueba y publica un post pendiente. Solo llamar después de revisión manual.
    Args:
        post_index: índice del post en el log (-1 = último)
    Returns:
        True si se publicó exitosamente
    """
    log = _load_log()
    posts = log.get("posts", [])
    if not posts:
        logger.error("[content_agent] No hay posts en el log")
        return False

    post = posts[post_index]
    if post.get("status") != "pending_review":
        logger.warning(f"[content_agent] Post no está en pending_review: {post.get('status')}")
        return False

    text = post.get("text", "")
    image_path = post.get("image_path")

    success = linkedin_post_tool.post_to_linkedin(text, image_path)

    if success:
        post["status"] = "published"
        post["published"] = True
        post["published_at"] = datetime.now().isoformat()
        log["last_post_at"] = post["published_at"]
        logger.info(f"[content_agent] Post PUBLICADO: {post.get('topic')}")
    else:
        logger.error(f"[content_agent] Error publicando: {post.get('topic')}")

    _save_log(log)
    return success


def get_pending_posts() -> list:
    """Retorna los posts pendientes de revisión."""
    log = _load_log()
    return [p for p in log.get("posts", []) if p.get("status") == "pending_review"]


def get_posting_stats() -> dict:
    """Return stats: posts_today, posts_this_week, last_post_at, topics_used."""
    log = _load_log()
    posts = log.get("posts", [])
    now = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=now.weekday())

    posts_today = 0
    posts_this_week = 0
    for p in posts:
        if not p.get("success"):
            continue
        try:
            ts = datetime.fromisoformat(p["published_at"])
            if ts >= today_start:
                posts_today += 1
            if ts >= week_start:
                posts_this_week += 1
        except Exception:
            continue

    return {
        "posts_today": posts_today,
        "posts_this_week": posts_this_week,
        "last_post_at": log.get("last_post_at"),
        "topics_used": log.get("topics_used", []),
        "total_posts": len([p for p in posts if p.get("success")]),
    }
