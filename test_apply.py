#!/usr/bin/env python3
"""
Test simple del AI Orchestrator Agent para aplicar jobs.
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = str(Path(__file__).parent)
sys.path.insert(0, PROJECT_ROOT)

from src.agents import ai_orchestrator_agent


def main():
    """Función principal del test."""
    print("🧪 Test de AI Orchestrator Agent - Aplicar Jobs")
    print()
    
    # Simular conversación con el AI Orchestrator Agent
    print("📱 Usuario: aplicar 2 jobs")
    response1 = ai_orchestrator_agent.process_message("aplicar 2 jobs")
    print(f"🤖 AI: {response1}")
    print()
    
    # Confirmar aplicación
    print("📱 Usuario: sí")
    response2 = ai_orchestrator_agent.process_message("sí")
    print(f"🤖 AI: {response2}")
    print()
    
    return response2


if __name__ == "__main__":
    main()
