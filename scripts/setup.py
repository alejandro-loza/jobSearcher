#!/usr/bin/env python3
"""
Script de setup para JobSearcher

Este script facilita la instalación inicial del proyecto.
"""

import sys
import subprocess
import os
from pathlib import Path


def run_command(cmd, description):
    """Ejecuta un comando y muestra progreso"""
    print(f"\n{description}...")
    try:
        subprocess.run(cmd, check=True, shell=True)
        print(f"✓ {description} completado")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Error: {e}")
        return False


def main():
    """Función principal de setup"""
    print("=" * 60)
    print("JOBSSEARCHER - SETUP INICIAL")
    print("=" * 60)

    # Verificar Python version
    print("\nVerificando versión de Python...")
    if sys.version_info < (3, 10):
        print("✗ Error: Se requiere Python 3.10 o superior")
        sys.exit(1)
    print(
        f"✓ Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    )

    # Crear entorno virtual
    print("\nCreando entorno virtual...")
    venv_path = Path("venv")
    if venv_path.exists():
        print("✓ El entorno virtual ya existe")
    else:
        if not run_command(f"{sys.executable} -m venv venv", "Creando entorno virtual"):
            sys.exit(1)

    # Determinar comando de activación
    if os.name == "nt":  # Windows
        pip_cmd = "venv\\Scripts\\pip"
        python_cmd = "venv\\Scripts\\python"
    else:  # Linux/Mac
        pip_cmd = "venv/bin/pip"
        python_cmd = "venv/bin/python"

    # Actualizar pip
    if not run_command(f"{pip_cmd} install --upgrade pip", "Actualizando pip"):
        sys.exit(1)

    # Instalar dependencias
    if not run_command(
        f"{pip_cmd} install -r requirements.txt", "Instalando dependencias"
    ):
        sys.exit(1)

    # Crear directorios necesarios
    print("\nCreando directorios...")
    directories = ["data", "data/strategies", "data/interview_preps", "logs"]
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
    print("✓ Directorios creados")

    # Crear archivo .env si no existe
    env_file = Path(".env")
    if not env_file.exists():
        print("\nCreando archivo .env...")
        if not run_command("cp .env.example .env", "Copiando .env.example"):
            sys.exit(1)
        print("✓ Archivo .env creado")
        print("⚠ IMPORTANTE: Edita el archivo .env y agrega tus API keys")
    else:
        print("✓ Archivo .env ya existe")

    # Copiar CV de ejemplo
    print("\nCopiando CV de ejemplo...")
    if not run_command("cp data/resume_example.json data/resume.json", "Copiando CV"):
        sys.exit(1)
    print("✓ CV de ejemplo copiado")

    # Instalar proyecto en modo desarrollo
    print("\nInstalando proyecto...")
    if not run_command(f"{pip_cmd} install -e .", "Instalando JobSearcher"):
        sys.exit(1)

    # Ejecutar tests
    print("\nEjecutando tests...")
    result = run_command(f"{python_cmd} -m pytest tests/ -v", "Ejecutando tests")
    if not result:
        print("⚠ Los tests fallaron, pero la instalación continúa")

    # Mostrar instrucciones finales
    print("\n" + "=" * 60)
    print("¡SETUP COMPLETADO!")
    print("=" * 60)
    print("\nPasos siguientes:")
    print("1. Edita el archivo .env y agrega tus API keys:")
    print("   - OPENAI_API_KEY")
    print("   - ANTHROPIC_API_KEY (opcional)")
    print("\n2. Configura LinkedIn MCP:")
    print("   - Sigue las instrucciones en: https://linkedapi.io/mcp/installation/")
    print("\n3. Activa el entorno virtual:")
    if os.name == "nt":
        print("   venv\\Scripts\\activate")
    else:
        print("   source venv/bin/activate")

    print("\n4. Ejecuta el comando de ayuda:")
    print("   python -m src.cli --help")

    print("\n5. Ejecuta una búsqueda de ejemplo:")
    print("   python -m src.cli search --keywords 'python developer'")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
