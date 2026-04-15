#!/usr/bin/env python3
"""
CLI de JobSearcher - Interfaz de línea de comandos con AI Orchestrator Agent.

Permite interactuar con el sistema usando lenguaje natural.
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = str(Path(__file__).parent.parent)
sys.path.insert(0, PROJECT_ROOT)

from src.agents import ai_orchestrator_agent
from loguru import logger


def print_usage():
    """Imprime instrucciones de uso."""
    print("""
╔═════════════════════════════════════════════════════════════╗
║     🤖 JobSearcher CLI - AI Orchestrator Agent                 ║
╚═════════════════════════════════════════════════════════════╝

Uso:
    python3 cli.py "tu mensaje en lenguaje natural"

Ejemplos:
    python3 cli.py "¿cuántos jobs hay en cola?"
    python3 cli.py "aplicar a los jobs de alta prioridad"
    python3 cli.py "buscar empleos en Stripe o Airbnb"
    python3 cli.py "estado del pipeline"
    python3 cli.py "revisar emails"
    python3 cli.py "pausar búsqueda"
    python3 cli.py "reanudar búsqueda"

Comandos disponibles:
    - estado_pipeline        Ver estadísticas del pipeline
    - jobs_pendientes_aplicar   Muestra jobs en cola de aplicación
    - buscar_empleos          Busca empleos con término específico
    - buscar_en_empresa        Busca en empresa específica
    - revisar_linkedin         Revisa mensajes de LinkedIn
    - revisar_email           Lee emails recientes de trabajo
    - proximas_entrevistas      Consulta entrevistas programadas
    - pausar_busqueda          Pausa búsqueda automática
    - reanudar_busqueda      Reactiva búsqueda automática
    - estado_ban_linkedin    Verifica estado de ban de LinkedIn

Notas:
    - El sistema te preguntará confirmación antes de acciones
    - Todo se procesa en español
    - Las respuestas son concisas y directas
""")


def main():
    """Función principal del CLI."""
    if len(sys.argv) < 2:
        print_usage()
        return

    # Obtener mensaje del usuario (unir todos los argumentos)
    user_message = " ".join(sys.argv[1:])
    
    logger.info(f"📱 Procesando: {user_message}")
    
    # Enviar al AI Orchestrator Agent
    try:
        response = ai_orchestrator_agent.process_message(user_message)
        print(f"\n🤖 {response}\n")
    except Exception as e:
        logger.error(f"❌ Error procesando mensaje: {e}")
        print(f"\n❌ Error: {str(e)[:200]}\n")


if __name__ == "__main__":
    main()
