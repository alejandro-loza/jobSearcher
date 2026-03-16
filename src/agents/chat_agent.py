"""
Chat Agent: Maneja la lógica de interacción conversacional del dashboard.
Delega tareas al master_agent y coordina acciones en el sistema.
"""
import json
from typing import Dict, Any, List
from loguru import logger
from langchain_core.messages import HumanMessage, AIMessage

from src.agents import master_agent
from src.agents import coordinator
from src.db.tracker import JobTracker

class ChatAgent:
    def __init__(self):
        self.tracker = JobTracker()
        self.history = []

    async def handle_message(self, message: str) -> str:
        """
        Procesa un mensaje del usuario y retorna una respuesta.
        Intenta detectar intents específicos para ejecutar acciones.
        """
        logger.info(f"ChatAgent: procesando '{message}'")
        
        # 1. Obtener contexto del sistema para el LLM
        stats = self.tracker.get_stats()
        
        # 2. Definir el prompt del sistema para el Chat Agent
        system_prompt = f"""Eres el asistente inteligente de JobSearcher. Ayudas al usuario a gestionar su búsqueda de empleo.
Puedes realizar acciones como: buscar trabajos, ver estadísticas, revisar aplicaciones y agendar entrevistas.

ESTADO ACTUAL DEL SISTEMA:
- Trabajos encontrados: {stats['total_found']}
- Aplicaciones enviadas: {stats['applied']}
- Entrevistas agendadas: {stats['interviews_scheduled']}
- Pendientes de revisión: {stats['pending']}

REGLAS DE RESPUESTA:
- Sé profesional, conciso y amigable.
- Usa Markdown para dar formato a las respuestas (negritas, listas, etc.).
- Si el usuario pide buscar trabajo, indica que iniciarás una búsqueda.
- Si pide estadísticas, dáselas basadas en el estado actual.
- Mantén la respuesta breve (máximo 2-3 párrafos).
"""

        # 3. Construir historial de mensajes
        messages = [HumanMessage(content=system_prompt + f"\n\nMensaje del usuario: {message}")]
        
        # Podríamos usar el historial de la sesión si quisiéramos persistencia, 
        # pero para este dashboard usaremos una interacción simple por ahora.
        
        try:
            # Usamos el coordinator para elegir el mejor modelo para chat (ej: llama-3.3-70b-versatile en Groq)
            response = coordinator.invoke("whatsapp_command", messages).strip()
            
            # 4. Trigger de acciones basado en el texto (Heurística simple o LLM-based intent)
            # Nota: El master_agent.handle_whatsapp_command ya hace algo parecido,
            # pero aquí lo hacemos más "chatbot-like".
            
            return response
            
        except Exception as e:
            logger.error(f"Error en ChatAgent: {e}")
            return "Lo siento, tuve un problema al procesar tu solicitud. ¿Podrías intentar de nuevo?"

# Instancia única para compartir en el orchestrator si es necesario
chat_agent = ChatAgent()
