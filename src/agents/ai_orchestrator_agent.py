"""
AI Orchestrator Agent — cerebro conversacional del sistema.

Reemplaza el bloque elif/else en _process_whatsapp(). Entiende lenguaje
natural, decide qué herramientas usar y ejecuta acciones en el sistema.

Características:
- Tool calling con Groq (llama-3.3-70b-versatile) → fallback SambaNova
- Historial de conversación persistente en SQLite (rolling 20 msgs)
- Confirma antes de ejecutar acciones que modifican el sistema
- Responde siempre en español, conciso y directo

Safety:
- Acciones de lectura: ejecuta libre (estado, jobs, emails, LinkedIn)
- Acciones que modifican: pide confirmación antes (aplicar, pausar, buscar empresa)
- El antispam_agent sigue siendo gatekeeper de toda comunicación saliente
- Los flujos si/no de aprobación siguen hardcodeados en orchestrator.py

Sobre GLM: excluido por saldo inconsistente (ver docs/POR_QUE_NO_GLM.md).
Cuando se recargue, activarlo en coordinator.py como quality provider.
"""

from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.tools import tool
from loguru import logger

from src.agents import coordinator
from src.db.tracker import JobTracker

# ── Acciones que requieren confirmación antes de ejecutar ────────────────────
CONFIRM_TOOLS = {
    "buscar_en_empresa",
    "buscar_empleos",
    "pausar_busqueda",
    "reanudar_busqueda",
    "aplicar_jobs",
}

# Pendiente de confirmación: {tool_name, tool_args, message_to_show}
_pending_confirm: dict | None = None

_tracker = JobTracker()

# ── Definición de Tools ──────────────────────────────────────────────────────

@tool
def estado_pipeline() -> str:
    """Retorna estadísticas del pipeline de búsqueda de empleo: cuántos jobs
    encontrados, aplicados hoy, activos, ghosted, en cola."""
    t = JobTracker()
    stats = t.get_stats()
    today = t.count_applications_today()
    queue = t.get_application_queue(min_score=75, max_age_days=14, limit=5)
    snapshot = {
        "encontrados_total": stats.get("total_found", 0),
        "aplicados_total": stats.get("applied", 0),
        "aplicados_hoy": today,
        "en_cola_para_aplicar": len(queue),
        "ghosted": stats.get("ghosted", 0),
        "entrevistas_agendadas": stats.get("interviews_scheduled", 0),
    }
    top = [f"  [{j['match_score']}%] {j['title'][:40]} @ {j['company'][:20]}"
           for j in queue[:3]]
    result = json.dumps(snapshot, ensure_ascii=False)
    if top:
        result += "\nTop jobs en cola:\n" + "\n".join(top)
    return result


@tool
def jobs_pendientes_aplicar() -> str:
    """Muestra los próximos jobs en la cola de aplicación (score>=75, encontrados
    hace menos de 14 días), ordenados por score."""
    t = JobTracker()
    queue = t.get_application_queue(min_score=75, max_age_days=14, limit=10)
    if not queue:
        return "No hay jobs en cola para aplicar ahora."
    lines = [f"[{j['match_score']}%] {j['title'][:50]} @ {j['company'][:30]} | {j['source']}"
             for j in queue]
    return f"{len(queue)} jobs en cola:\n" + "\n".join(lines)


@tool
def buscar_empleos(query: str, location: str = "remote") -> str:
    """Busca empleos con el término indicado y evalúa match con el CV de Alejandro.
    Retorna los mejores matches encontrados. Usar para búsquedas genéricas."""
    try:
        import json as _json
        from src.tools import jobspy_tool
        from src.agents import master_agent

        resume_path = "data/resume.json"
        with open(resume_path) as f:
            resume = _json.load(f)

        jobs = jobspy_tool.search_jobs(
            search_term=query,
            location=location,
            results_wanted=10,
            hours_old=168,
        )

        t = JobTracker()
        matches = []
        for job in jobs:
            if t.job_exists(job["id"]):
                continue
            score, reason = master_agent.evaluate_job_match(job, resume)
            job["match_score"] = score
            if score >= 75:
                t.save_job(job)
                matches.append(f"[{score}%] {job['title'][:50]} @ {job['company'][:30]}")

        if not matches:
            return f"Búsqueda '{query}' completada. No encontré matches >= 75%."
        return f"Encontré {len(matches)} matches para '{query}':\n" + "\n".join(matches)
    except Exception as e:
        return f"Error en búsqueda: {str(e)[:200]}"


@tool
def buscar_en_empresa(empresa: str) -> str:
    """Busca vacantes en una empresa específica (ej: 'Thomson Reuters', 'Stripe', 'Uber').
    Usar cuando el usuario menciona una empresa concreta."""
    try:
        from src.agents import company_stalker_agent
        result = company_stalker_agent.stalk_company(
            empresa, auto_apply=False, notify_whatsapp=False
        )
        found = result.get("found", 0)
        matched = result.get("matched", 0)
        if matched == 0:
            return f"Busqué en {empresa}: {found} vacantes encontradas, ninguna con score >= 75%."
        return (
            f"Busqué en {empresa}: {found} vacantes, {matched} con buen match.\n"
            f"Agregadas a la cola de aplicación."
        )
    except Exception as e:
        return f"Error buscando en {empresa}: {str(e)[:200]}"


@tool
def revisar_linkedin() -> str:
    """Lee mensajes no leídos de LinkedIn. Retorna lista de reclutadores que
    escribieron con su empresa y último mensaje."""
    try:
        from src.tools import linkedin_messages_tool
        msgs = linkedin_messages_tool.get_unread_messages(limit=10)
        if not msgs:
            return "No hay mensajes nuevos en LinkedIn."
        lines = []
        for m in msgs[:5]:
            name = m.get("sender_name", "?")
            title = (m.get("sender_title") or "")[:40]
            last = (m.get("last_message") or "")[:80]
            lines.append(f"• {name} ({title}): \"{last}\"")
        return f"{len(msgs)} mensajes en LinkedIn:\n" + "\n".join(lines)
    except Exception as e:
        return f"Error leyendo LinkedIn: {str(e)[:200]}"


@tool
def revisar_email() -> str:
    """Lee emails recientes relacionados con trabajo en Gmail. Retorna asunto,
    empresa y sentimiento (positivo/rechazo/entrevista)."""
    try:
        from src.tools import gmail_tool
        from src.agents import master_agent
        emails = gmail_tool.get_recent_job_emails(processed_ids=set(), max_results=10)
        if not emails:
            return "No hay emails recientes de trabajo."
        lines = []
        for e in emails[:5]:
            subject = e.get("subject", "Sin asunto")[:60]
            from_addr = e.get("from_address", "?")[:40]
            analysis = master_agent.analyze_email_response(
                e.get("content", "")[:500],
                subject,
                from_addr,
            )
            sentiment = analysis.get("sentiment", "neutral")
            icon = {"positive": "✅", "interview": "📅", "negative": "❌"}.get(sentiment, "📧")
            lines.append(f"{icon} {from_addr}: \"{subject}\"")
        return f"{len(emails)} emails recientes:\n" + "\n".join(lines)
    except Exception as e:
        return f"Error leyendo Gmail: {str(e)[:200]}"


@tool
def proximas_entrevistas() -> str:
    """Consulta Google Calendar y retorna entrevistas de trabajo programadas
    en los próximos 14 días."""
    try:
        from src.tools import calendar_tool
        events = calendar_tool.get_upcoming_events(days=14)
        if not events:
            return "No tienes entrevistas programadas en los próximos 14 días."
        lines = []
        for e in events[:5]:
            start = e.get("start", {}).get("dateTime", e.get("start", {}).get("date", "?"))
            summary = e.get("summary", "Sin título")
            lines.append(f"• {start[:16]} — {summary}")
        return f"{len(events)} entrevistas próximas:\n" + "\n".join(lines)
    except Exception as e:
        return f"Error leyendo Calendar: {str(e)[:200]}"


@tool
def pausar_busqueda() -> str:
    """Pausa el job search automático del sistema (stalkers y búsquedas periódicas).
    Usar cuando el usuario pide pausar, parar o detener el agente."""
    try:
        from src.orchestrator import scheduler
        for job_id in ["job_search", "application_agent", "stalker_A", "stalker_B",
                       "stalker_C", "stalker_D", "stalker_E", "stalker_F"]:
            try:
                scheduler.pause_job(job_id)
            except Exception:
                pass
        return "Búsqueda automática pausada. Di 'reanudar' cuando quieras continuar."
    except Exception as e:
        return f"No pude pausar el scheduler: {str(e)[:200]}"


@tool
def reanudar_busqueda() -> str:
    """Reactiva el job search automático del sistema. Usar cuando el usuario
    pide reanudar, continuar o activar el agente."""
    try:
        from src.orchestrator import scheduler
        for job_id in ["job_search", "application_agent", "stalker_A", "stalker_B",
                       "stalker_C", "stalker_D", "stalker_E", "stalker_F"]:
            try:
                scheduler.resume_job(job_id)
            except Exception:
                pass
        return "Búsqueda automática reanudada."
    except Exception as e:
        return f"No pude reanudar el scheduler: {str(e)[:200]}"


@tool
def estado_ban_linkedin() -> str:
    """Verifica si LinkedIn está baneado o en recovery mode. Muestra aplicaciones
    enviadas hoy y el daily cap configurado."""
    try:
        from src.agents.application_agent import get_ban_state, _current_daily_cap
        t = JobTracker()
        ban = get_ban_state()
        today = t.count_applications_today()
        cap = _current_daily_cap()
        state = ban.get("current_state", "ok")
        icon = {"ok": "✅", "banned": "🚫", "recovering": "⚠️"}.get(state, "❓")
        result = (
            f"{icon} LinkedIn: {state}\n"
            f"Apps hoy: {today}/{cap}\n"
            f"Bans históricos: {ban.get('ban_count', 0)}"
        )
        if ban.get("recovery_resume_at"):
            result += f"\nReanuda: {ban['recovery_resume_at'][:16]}"
        return result
    except Exception as e:
        return f"Error leyendo estado ban: {str(e)[:200]}"


@tool
def aplicar_jobs(count: int = 1) -> str:
    """Aplica a jobs pendientes usando el application_agent.
    
    Args:
        count: Número de jobs a aplicar (default 1, máximo 3 por seguridad)
    
    Aplica a jobs con score >= 75% encontrados hace menos de 14 días.
    Usa el application_agent para aplicar vía LinkedIn Easy Apply o browser tool.
    """
    try:
        import asyncio
        from src.agents import application_agent
        
        # Validar límites
        if count < 1 or count > 5:
            return "❌ El número debe ser entre 1 y 5 por seguridad."
        
        logger.info(f"[ai_orch] Aplicando {count} jobs...")
        
        # Ejecutar application_agent.run_application_cycle_sync() count veces
        results = []
        for i in range(count):
            try:
                result = application_agent.run_application_cycle_sync()
                results.append(result)
                logger.info(f"[ai_orch] Job {i+1}/{count}: applied={result.get('applied', 0)}, failed={result.get('failed', 0)}")
                
                # Si falló por ban, detener
                if result.get("ban_detected"):
                    logger.warning(f"[ai_orch] Ban detectado, deteniendo después de {i+1} aplicaciones")
                    break
                    
            except Exception as e:
                logger.error(f"[ai_orch] Error aplicando job {i+1}: {e}")
                results.append({"applied": 0, "failed": 1, "error": str(e)})
        
        # Calcular totales
        total_applied = sum(r.get("applied", 0) for r in results)
        total_failed = sum(r.get("failed", 0) for r in results)
        
        result_msg = f"✅ Aplicaciones completadas: {total_applied} exitosas, {total_failed} fallidas"
        if total_applied > 0:
            result_msg += f"\n📊 Aplicaciones hoy: {_tracker.count_applications_today()}"
        
        return result_msg
    except Exception as e:
        logger.error(f"[ai_orch] Error en aplicar_jobs: {e}")
        return f"Error aplicando jobs: {str(e)[:200]}"


# ── Lista de todas las tools ─────────────────────────────────────────────────
ALL_TOOLS = [
    estado_pipeline,
    jobs_pendientes_aplicar,
    buscar_empleos,
    buscar_en_empresa,
    revisar_linkedin,
    revisar_email,
    proximas_entrevistas,
    pausar_busqueda,
    reanudar_busqueda,
    estado_ban_linkedin,
    aplicar_jobs,
]

TOOL_MAP = {t.name: t for t in ALL_TOOLS}

# ── System prompt ────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """Eres el asistente personal de búsqueda de empleo de Alejandro Hernandez Loza.
Tienes acceso a herramientas para buscar trabajos, revisar emails y LinkedIn,
ver el pipeline completo, controlar el sistema, y aplicar a trabajos.

Perfil de Alejandro:
- Rol: Senior Software Engineer (Java, Spring Boot, Cloud, Microservices)
- Ubicación: Ciudad de México — busca remoto o híbrido CDMX
- Salario mínimo: $50,000 MXN/mes o $2,500 USD/mes (solo nómina formal o Deel/Remote)
- Stack: Java 17+, Spring Boot, AWS/GCP, Docker, Kubernetes, Kafka

Reglas de comportamiento:
1. Responde SIEMPRE en español, de forma concisa y directa
2. SIEMPRE usa las tools disponibles para responder — no inventes datos
3. Cuando el usuario pide algo, llama la tool correspondiente inmediatamente
4. Respuestas cortas — estamos en WhatsApp, no en un ensayo
5. Si no hay tool para algo, dilo brevemente"""

# ── Historial de conversación ────────────────────────────────────────────────

def _load_history() -> list[BaseMessage]:
    """Carga historial de BD y convierte a mensajes LangChain."""
    rows = _tracker.get_chat_history(limit=20)
    messages: list[BaseMessage] = []
    for row in rows:
        role = row["role"]
        content = row["content"]
        if role == "user":
            messages.append(HumanMessage(content=content))
        elif role == "assistant":
            messages.append(AIMessage(content=content))
        # tool messages no se cargan al historial para evitar problemas de formato
    return messages


def _save_message(role: str, content: str, tool_name: str = None):
    _tracker.save_chat_message(role, content, tool_name)


# ── Lógica de confirmación ───────────────────────────────────────────────────

_pending_confirm: dict | None = None


def _needs_confirm(tool_name: str) -> bool:
    return tool_name in CONFIRM_TOOLS


def _format_confirm_prompt(tool_name: str, tool_args: dict) -> str:
    descriptions = {
        "buscar_empleos": lambda a: f"buscar empleos con '{a.get('query','?')}' en {a.get('location','remote')}",
        "buscar_en_empresa": lambda a: f"buscar vacantes en {a.get('empresa','?')}",
        "pausar_busqueda": lambda _: "pausar la búsqueda automática",
        "reanudar_busqueda": lambda _: "reanudar la búsqueda automática",
        "aplicar_jobs": lambda a: f"aplicar a {a.get('count', 1)} jobs pendientes",
    }
    desc_fn = descriptions.get(tool_name, lambda a: tool_name)
    desc = desc_fn(tool_args)
    return f"Voy a {desc}. ¿Confirmas? (sí/no)"


# ── Entry point ──────────────────────────────────────────────────────────────

def process_message(user_message: str) -> str:
    """
    Procesa un mensaje en lenguaje natural.

    Flujo ReAct:
    1. Carga historial de BD
    2. Agrega mensaje del usuario
    3. LLM decide qué tools llamar (si alguna)
    4. Si la tool requiere confirmación → guarda estado y pregunta
    5. Si confirma → ejecuta tool → LLM formula respuesta
    6. Guarda en BD y retorna respuesta
    """
    global _pending_confirm

    # ── ¿Es respuesta a una confirmación pendiente? ──
    if _pending_confirm:
        normalized = user_message.strip().lower()
        if normalized in ("sí", "si", "yes", "s", "confirmo", "dale", "ok", "adelante"):
            # Ejecutar tool confirmada
            tool_name = _pending_confirm["tool_name"]
            tool_args = _pending_confirm["tool_args"]
            _pending_confirm = None
            logger.info(f"[ai_orch] Confirmado — ejecutando {tool_name}({tool_args})")
            try:
                tool_fn = TOOL_MAP[tool_name]
                tool_result = tool_fn.invoke(tool_args)
            except Exception as e:
                tool_result = f"Error ejecutando {tool_name}: {str(e)[:200]}"
            _save_message("user", user_message)
            _save_message("tool", tool_result, tool_name)
            # LLM formula respuesta basada en resultado
            response = _llm_summarize(tool_name, tool_result)
            _save_message("assistant", response)
            return response
        else:
            # Cancelado
            _pending_confirm = None
            _save_message("user", user_message)
            response = "Entendido, cancelado."
            _save_message("assistant", response)
            return response

    # ── Flujo normal ──
    _save_message("user", user_message)
    history = _load_history()

    # Construir mensajes para el LLM
    messages: list[BaseMessage] = [SystemMessage(content=SYSTEM_PROMPT)]
    messages.extend(history)

    # Primer turno: LLM decide qué tools llamar
    try:
        ai_msg = coordinator.invoke_with_tools(messages, ALL_TOOLS, temperature=0.1)
    except Exception as e:
        logger.error(f"[ai_orch] LLM falló: {e}")
        response = "Lo siento, el sistema de IA no está disponible en este momento."
        _save_message("assistant", response)
        return response

    # Sin tool calls → respuesta directa
    if not getattr(ai_msg, "tool_calls", []):
        response = ai_msg.content or "No tengo respuesta para eso."
        _save_message("assistant", response)
        return response

    # Con tool calls → procesar
    responses = []
    for tc in ai_msg.tool_calls:
        tool_name = tc["name"]
        tool_args = tc.get("args", {})

        # ¿Requiere confirmación?
        if _needs_confirm(tool_name):
            _pending_confirm = {"tool_name": tool_name, "tool_args": tool_args}
            confirm_msg = _format_confirm_prompt(tool_name, tool_args)
            _save_message("assistant", confirm_msg)
            return confirm_msg

        # Ejecutar directo
        logger.info(f"[ai_orch] Ejecutando tool: {tool_name}({tool_args})")
        try:
            tool_fn = TOOL_MAP.get(tool_name)
            if tool_fn:
                result = tool_fn.invoke(tool_args)
            else:
                result = f"Tool '{tool_name}' no encontrada."
        except Exception as e:
            result = f"Error en {tool_name}: {str(e)[:200]}"

        responses.append((tool_name, result))
        _save_message("tool", result, tool_name)

    # Segundo turno: LLM resume los resultados
    if responses:
        # Agregar resultados como tool messages al contexto
        messages.append(ai_msg)
        for tool_name, result in responses:
            messages.append(ToolMessage(content=result, tool_call_id=tool_name))

        try:
            final_msg = coordinator.invoke_with_tools(messages, ALL_TOOLS, temperature=0.3)
            response = final_msg.content or "\n".join(r for _, r in responses)
        except Exception:
            # Fallback: concatenar resultados
            response = "\n\n".join(f"**{n}:**\n{r}" for n, r in responses)
    else:
        response = ai_msg.content or "Hecho."

    _save_message("assistant", response)
    return response


def _llm_summarize(tool_name: str, tool_result: str) -> str:
    """Resume el resultado de una tool en lenguaje natural."""
    from langchain_core.messages import HumanMessage as HM
    try:
        prompt = (
            f"El usuario confirmó ejecutar '{tool_name}'. Resultado:\n{tool_result}\n\n"
            "Resume en 2-3 líneas en español qué ocurrió."
        )
        return coordinator.invoke("whatsapp_command", [HM(content=prompt)], temperature=0.3)
    except Exception:
        return tool_result


def reset_conversation():
    """Limpia historial de conversación (para /reset o debug)."""
    global _pending_confirm
    _pending_confirm = None
    _tracker.clear_chat_history()
    logger.info("[ai_orch] Conversación reseteada")
