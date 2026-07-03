"""Entry point: inicia el orchestrator."""
import os
import signal
import socket
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


def _free_port(port: int):
    """Mata cualquier proceso que esté usando el puerto para evitar 'address already in use'."""
    try:
        import subprocess
        result = subprocess.run(
            ["lsof", "-ti", f":{port}"],
            capture_output=True, text=True, timeout=5
        )
        pids = [p.strip() for p in result.stdout.strip().splitlines() if p.strip()]
        for pid in pids:
            try:
                os.kill(int(pid), signal.SIGTERM)
                logger.info(f"[startup] Puerto {port} liberado (PID {pid} terminado)")
            except (ProcessLookupError, ValueError):
                pass
    except Exception as e:
        logger.warning(f"[startup] No se pudo liberar puerto {port}: {e}")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("  JobSearcher Agent - Iniciando...")
    print("  WhatsApp + Terminal output activos")
    print("="*60 + "\n")

    # Liberar el puerto si está ocupado por una instancia anterior
    _free_port(settings.orchestrator_port)

    uvicorn.run(
        "src.orchestrator:app",
        host=settings.orchestrator_host,
        port=settings.orchestrator_port,
        reload=False,
        log_level="info",
    )
