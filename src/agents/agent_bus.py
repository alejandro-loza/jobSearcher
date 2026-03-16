"""
Agent Bus: permite que los agentes se comuniquen entre sí sin pasar por el orchestrator.

Patrón: cualquier agente puede llamar a otro agente por nombre + acción.
El bus resuelve quién maneja cada acción y devuelve el resultado.

Acciones disponibles:
  master_agent.evaluate_job     → evalúa si un job encaja con el CV
  master_agent.cover_letter     → genera cover letter
  master_agent.analyze_email    → analiza email de empresa
  master_agent.followup_email   → genera follow-up
  recruiter_agent.analyze_msg   → analiza mensaje de reclutador
  recruiter_agent.refine        → refina una respuesta
  calendar_agent.free_slots     → obtiene slots libres del calendario
  calendar_agent.create_event   → crea evento de entrevista

Uso desde cualquier agente:
    from src.agents.agent_bus import bus
    slots = bus.call("calendar_agent.free_slots", days_ahead=7)
    match = bus.call("master_agent.evaluate_job", job=job_dict, resume=resume_dict)
"""
from typing import Any, Dict
from loguru import logger


class AgentBus:
    def __init__(self):
        self._handlers: Dict[str, Any] = {}

    def register(self, action: str, handler):
        """Registra un handler para una acción."""
        self._handlers[action] = handler
        logger.debug(f"[bus] registrado: {action}")

    def call(self, action: str, **kwargs) -> Any:
        """
        Llama a un agente por acción.

        Args:
            action: "agente.accion" (ej: "master_agent.evaluate_job")
            **kwargs: argumentos para el handler

        Returns:
            Resultado del agente llamado
        """
        handler = self._handlers.get(action)
        if not handler:
            raise ValueError(f"[bus] Acción no registrada: '{action}'. Disponibles: {list(self._handlers.keys())}")
        logger.debug(f"[bus] llamando: {action}")
        return handler(**kwargs)


# Instancia global — todos los agentes importan este mismo objeto
bus = AgentBus()


def _register_all():
    """Registra todas las acciones disponibles en el bus."""
    from src.agents import master_agent, recruiter_agent
    from src.tools import calendar_tool

    # master_agent actions
    bus.register("master_agent.evaluate_job",  master_agent.evaluate_job_match)
    bus.register("master_agent.cover_letter",  master_agent.generate_cover_letter)
    bus.register("master_agent.analyze_email", master_agent.analyze_email_response)
    bus.register("master_agent.followup_email",master_agent.generate_followup_email)
    bus.register("master_agent.whatsapp_cmd",  master_agent.handle_whatsapp_command)

    # recruiter_agent actions
    bus.register("recruiter_agent.analyze_msg", recruiter_agent.analyze_recruiter_message)
    bus.register("recruiter_agent.refine",       recruiter_agent.refine_response)
    bus.register("recruiter_agent.gen_email",    recruiter_agent.generate_email_to_recruiter)

    # calendar_tool actions (expuestos como agente)
    bus.register("calendar_agent.free_slots",    calendar_tool.get_free_slots)
    bus.register("calendar_agent.create_event",  calendar_tool.create_interview_event)
    bus.register("calendar_agent.upcoming",      calendar_tool.get_upcoming_events)

    logger.info(f"[bus] {len(bus._handlers)} acciones registradas")


# Se auto-registra al importar
_register_all()
