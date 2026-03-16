#!/usr/bin/env python3
"""
Script para ejecutar tests
"""

import sys
import subprocess
from pathlib import Path


def main():
    """Ejecuta los tests"""
    print("=" * 60)
    print("EJECUTANDO TESTS")
    print("=" * 60)

    # Agregar el directorio src al path
    src_path = Path(__file__).parent.parent / "src"
    sys.path.insert(0, str(src_path))

    # Ejecutar pytest
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short"],
        cwd=Path(__file__).parent.parent,
    )

    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
