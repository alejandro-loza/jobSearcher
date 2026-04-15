#!/usr/bin/env python3
"""
Chat interactivo con AI Orchestrator Agent.

Permite conversación continua con el agente AI usando lenguaje natural.
Similar a la interfaz de WhatsApp pero desde terminal.
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = str(Path(__file__).parent)
sys.path.insert(0, PROJECT_ROOT)

from src.agents import ai_orchestrator_agent
from loguru import logger


def print_welcome():
    """Imprime mensaje de bienvenida."""
    print("""
╔═══════════════════════════════════════════════════════════════╗
║  🤖 JobSearcher AI Chat - Interfaz interactiva              ║
║  Chat con el AI Orchestrator Agent usando lenguaje natural         ║
╚═══════════════════════════════════════════════════════════════╝

Comandos especiales:
  /exit, /quit, /q      - Salir del chat
  /reset                 - Reiniciar conversación
  /help                  - Mostrar esta ayuda

Ejemplos de uso:
  "¿cuántos jobs hay en cola?"
  "aplicar a los jobs de alta prioridad"
  "buscar empleos en Stripe"
  "estado del pipeline"
  "revisar emails recientes"
  "pausar búsqueda automática"

Escribe tu mensaje y presiona Enter para continuar...
""")


def chat_loop():
    """Loop principal del chat interactivo."""
    print_welcome()
    
    while True:
        try:
            # Leer mensaje del usuario
            user_input = input("🧑 Tú: ").strip()
            
            # Comandos especiales
            if user_input.lower() in ["/exit", "/quit", "/q"]:
                print("\n👋 ¡Hasta luego!\n")
                break
            
            if user_input.lower() == "/reset":
                ai_orchestrator_agent.reset_conversation()
                print("\n🔄 Conversación reiniciada\n")
                continue
            
            if user_input.lower() == "/help":
                print_welcome()
                continue
            
            if not user_input:
                continue
            
            # Procesar mensaje con AI Orchestrator Agent
            logger.info(f"📱 Procesando: {user_input}")
            response = ai_orchestrator_agent.process_message(user_input)
            
            # Mostrar respuesta
            print(f"\n🤖 AI: {response}\n")
            
        except KeyboardInterrupt:
            print("\n\n👋 ¡Hasta luego!\n")
            break
        
        except EOFError:
            print("\n\n👋 ¡Hasta luego!\n")
            break
        
        except Exception as e:
            logger.error(f"❌ Error: {e}")
            print(f"\n❌ Error: {str(e)[:200]}\n")


def main():
    """Función principal del chat interactivo."""
    try:
        chat_loop()
    except Exception as e:
        logger.exception(f"Error fatal en chat loop: {e}")
        print(f"\n❌ Error fatal: {str(e)[:200]}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
