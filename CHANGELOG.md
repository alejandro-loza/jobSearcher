# Changelog

Todos los cambios notables en este proyecto se documentarán en este archivo.

El formato se basa en [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
y este proyecto adhiere a [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Agregado
- Integración con CrewAI para orquestación de agentes
- LinkedIn MCP Tool para búsqueda de empleos
- 4 agentes especializados:
  - JobSearchAgent
  - ResumeMatcherAgent
  - ApplicationStrategyAgent
  - InterviewPrepAgent
- Interfaz de línea de comandos completa
- Sistema de almacenamiento de datos
- Generador de reportes
- Docker y docker-compose support
- Tests unitarios básicos
- Documentación de arquitectura
- Guía de contribución

### Cambiado
- Estructura de directorios modular

## [0.1.0] - 2024-02-12

### Agregado
- Versión inicial del proyecto
- Estructura base con Python 3.10+
- Configuración con pydantic-settings
- Integración con OpenAI y Anthropic
- Sistema de logging con loguru
- CLI con argparse
- Soporte para LinkedIn MCP

[Unreleased]: https://github.com/yourusername/jobsearcher/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/yourusername/jobsearcher/releases/tag/v0.1.0
