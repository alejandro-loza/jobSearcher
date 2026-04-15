#!/usr/bin/env python3
"""
Test simple del AI Chat - envía un mensaje y muestra respuesta.
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = str(Path(__file__).parent)
sys.path.insert(0, PROJECT_ROOT)

from src.agents import ai_orchestrator_agent


def main():
    """Función principal del test."""
    print("🧪 Test de AI Chat - Enviando mensaje al AI Orchestrator Agent")
    print()
    
    test_message = "¿cuántos jobs hay en cola para aplicar?"
    
    print(f"📱 Enviando: {test_message}")
    print()
    
    # Procesar mensaje
    response = ai_orchestrator_agent.process_message(test_message)
    
    print(f"🤖 Respuesta: {response}")
    print()


if __name__ == "__main__":
    main()
