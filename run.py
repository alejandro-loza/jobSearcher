"""Entry point: inicia el orchestrator."""
import sys
import uvicorn
from loguru import logger
from config import settings

# Configurar loguru para output en consola con formato claro
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}",
    level="DEBUG",
    colorize=True,
)

if __name__ == "__main__":
    print("\n" + "="*60)
    print("  JobSearcher Agent - Iniciando...")
    print("  WhatsApp + Terminal output activos")
    print("="*60 + "\n")
    uvicorn.run(
        "src.orchestrator:app",
        host=settings.orchestrator_host,
        port=settings.orchestrator_port,
        reload=False,
        log_level="info",
    )
