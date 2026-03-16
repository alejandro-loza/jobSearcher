.PHONY: help install test lint format clean run setup docker-build docker-up docker-down

help: ## Muestra esta ayuda
	@echo "Comandos disponibles:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

setup: ## Ejecuta el script de setup inicial
	@python scripts/setup.py

install: ## Instala las dependencias
	@pip install -r requirements.txt
	@pip install -e .

test: ## Ejecuta los tests
	@python scripts/run_tests.py

lint: ## Ejecuta el linter (si tienes ruff o flake8)
	@echo "Instala ruff o flake8 para habilitar linting"

format: ## Formatea el código (si tienes black)
	@echo "Instala black para habilitar formateo"

clean: ## Limpia archivos temporales
	@find . -type f -name "*.pyc" -delete
	@find . -type d -name "__pycache__" -delete
	@find . -type d -name ".pytest_cache" -delete
	@rm -rf .mypy_cache/
	@rm -rf *.egg-info/
	@rm -rf dist/
	@rm -rf build/

run: ## Ejecuta la aplicación en modo interactivo
	@python -m src.cli interactive

search: ## Búsqueda de ejemplo
	@python -m src.cli search --keywords "python developer" --location remote

docker-build: ## Construye la imagen Docker
	@docker-compose build

docker-up: ## Inicia los contenedores Docker
	@docker-compose up -d

docker-down: ## Detiene los contenedores Docker
	@docker-compose down

docker-logs: ## Muestra los logs de Docker
	@docker-compose logs -f

docker-shell: ## Entra al shell del contenedor
	@docker-compose exec jobsearcher /bin/bash
