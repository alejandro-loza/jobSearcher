#!/usr/bin/env python3
"""
Top Companies Stalker Agent.

Realiza búsqueda activa y programada (rate-limited) sobre la lista de las
100 mejores empresas, procesándolas en lotes (chunks) para no recibir bloqueos.
"""

import json
import sys
from pathlib import Path
from loguru import logger

# Add project root to path
PROJECT_ROOT = str(Path(__file__).parent.parent.parent)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.agents.job_discovery_agent import TOP_TIER_COMPANIES
from src.agents.company_stalker_agent import stalk_multiple

STATE_FILE = "data/top_companies_state.json"


def _load_state() -> dict:
    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"current_index": 0}


def _save_state(state: dict):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def run_stalker_chunk(chunk_size: int = 5) -> dict:
    """
    Toma las siguientes 'chunk_size' empresas de la lista de TOP_TIER_COMPANIES
    y ejecuta stalk_multiple sobre ellas. Actualiza el índice guardado.
    """
    logger.info(f"[top_companies] Iniciando chunk de búsqueda activa ({chunk_size} empresas)")
    
    if not TOP_TIER_COMPANIES:
        logger.error("[top_companies] La lista de empresas está vacía.")
        return {"error": "lista_vacia"}

    state = _load_state()
    start_idx = state.get("current_index", 0)
    
    # Asegurarnos de que el índice es válido
    if start_idx >= len(TOP_TIER_COMPANIES):
        start_idx = 0

    end_idx = start_idx + chunk_size
    companies_chunk = TOP_TIER_COMPANIES[start_idx:end_idx]
    
    logger.info(f"[top_companies] Procesando empresas desde el índice {start_idx} al {start_idx + len(companies_chunk) - 1}: {companies_chunk}")
    
    # Llamar al stalker de empresas
    results = stalk_multiple(
        companies_chunk, 
        locations=["Mexico"],
        auto_apply=False, 
        notify_whatsapp=True
    )
    
    # Actualizar estado
    next_idx = end_idx if end_idx < len(TOP_TIER_COMPANIES) else 0
    state["current_index"] = next_idx
    _save_state(state)
    
    logger.success(f"[top_companies] Chunk finalizado. Próximo índice: {next_idx}")
    
    return {
        "processed_companies": companies_chunk,
        "results": results,
        "next_index": next_idx
    }

if __name__ == "__main__":
    result = run_stalker_chunk(5)
    print(json.dumps(result, indent=2, default=str))
