# JobSearcher - AI-Powered Job Search Agent System

Sistema robusto de búsqueda de empleo en Python que utiliza CrewAI y LinkedIn MCP para automatizar el proceso de búsqueda, análisis y postulación a ofertas de trabajo.

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![CrewAI](https://img.shields.io/badge/CrewAI-0.80.0-orange.svg)](https://www.crewai.com/)

## 🌟 Características

- 🔍 **Búsqueda Automatizada**: Busca empleos en LinkedIn con filtros avanzados
- 🤖 **Agentes IA**: 4 agentes especializados que trabajan en conjunto
- 📊 **Análisis de Matching**: Compara tu CV con requisitos del puesto
- 📝 **Estrategias Personalizadas**: CVs optimizados, cover letters, networking
- 🎯 **Preparación de Entrevistas**: Preguntas técnicas y comportamentales
- 💾 **Persistencia de Datos**: Guarda empleos, análisis y estrategias
- 📈 **Reportes Detallados**: Análisis completo en formato estructurado
- 🐳 **Docker Ready**: Containerización fácil para despliegue

## 🏗️ Arquitectura

```
┌─────────────────────────────────────────────────────────────────┐
│                        JobSearcher CLI                          │
└─────────────────────────┬───────────────────────────────────────┘
                          │
              ┌───────────┼───────────┐
              │                       │
        ┌─────▼─────┐           ┌────▼─────┐
        │ CrewAI    │           │ LinkedIn  │
        │ Orchestrator         │ MCP       │
        └─────┬─────┘           └───────────┘
              │
    ┌─────────┼─────────┐
    │         │         │
┌───▼──┐  ┌──▼───┐  ┌──▼───┐
│Job   │  │Resume│  │App   │
│Search│  │Match │  │Strat │
└───┬──┘  └──┬───┘  └──┬───┘
    │        │        │
    └────────┼────────┘
             │
        ┌────▼────┐
        │Interview│
        │Prep     │
        └─────────┘
```

## 🚀 Instalación Rápida

### Prerrequisitos

- Python 3.10 o superior
- pip
- (Opcional) Docker y Docker Compose

### Opción 1: Instalación Manual

```bash
# Clonar el repositorio
git clone https://github.com/yourusername/jobsearcher.git
cd jobsearcher

# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# o
venv\Scripts\activate  # Windows

# Ejecutar script de setup
python scripts/setup.py
```

### Opción 2: Docker

```bash
# Clonar el repositorio
git clone https://github.com/yourusername/jobsearcher.git
cd jobsearcher

# Copiar y configurar .env
cp .env.example .env
# Editar .env con tus API keys

# Iniciar con Docker Compose
docker-compose up -d

# Entrar al contenedor
docker-compose exec jobsearcher /bin/bash
```

## ⚙️ Configuración

1. **API Keys** - Editar `.env`:
```bash
OPENAI_API_KEY=sk-proj-XXXXXXXXXXXXXXXXXXXXXXXXXXXX
ANTHROPIC_API_KEY=sk-ant-XXXXXXXXXXXXXXXXXXXXXXXXXXXX
```

2. **LinkedIn MCP** - Instalar y configurar:
```bash
# Seguir instrucciones en https://linkedapi.io/mcp/installation/
LINKEDIN_MCP_ENABLED=true
LINKEDIN_MCP_SERVER_URL=http://localhost:3000
```

3. **CV del Usuario** - Cargar tu CV:
```bash
# Usar el ejemplo o crear el tuyo
cp data/resume_example.json data/resume.json
# Editar data/resume.json con tu información
```

## 💻 Uso

### Comandos Disponibles

```bash
# Ver ayuda
python -m src.cli --help

# Búsqueda básica
python -m src.cli search --keywords "python developer" --location remote

# Búsqueda avanzada
python -m src.cli search \
  --keywords "senior python developer" \
  --location "Madrid" \
  --job-type "full-time" \
  --limit 20

# Análisis completo de un puesto
python -m src.cli analyze --job-id "job_123"

# Análisis de matching
python -m src.cli match --limit 10

# Generar estrategia de aplicación
python -m src.cli strategy --job-id "job_123"

# Preparación de entrevista
python -m src.cli interview --job-id "job_123"

# Modo interactivo
python -m src.cli interactive
```

### Usando Makefile (Linux/Mac)

```bash
make setup          # Ejecutar setup inicial
make install        # Instalar dependencias
make test           # Ejecutar tests
make search         # Búsqueda de ejemplo
make docker-up      # Iniciar Docker
make docker-down    # Detener Docker
```

## 🤖 Agentes

### 1. Job Search Agent 📊

**Rol**: Job Search Specialist  
**Objetivo**: Encontrar las mejores oportunidades de empleo en LinkedIn

**Funcionalidades**:
- Búsqueda avanzada con múltiples filtros
- Análisis de descripciones de puestos
- Evaluación de salary ranges
- Análisis de compañía

**Herramientas**: LinkedIn MCP (search_jobs, get_job_details, get_company_info)

### 2. Resume Matcher Agent 🎯

**Rol**: Resume Matching Specialist  
**Objetivo**: Analizar el match entre perfil y requisitos

**Funcionalidades**:
- Comparación de habilidades técnicas y blandas
- Identificación de gaps
- Análisis de experiencia relevante
- Score de matching (0-100)

**Output**: Reporte con matched skills, missing skills, strengths, improvements

### 3. Application Strategist Agent 📝

**Rol**: Application Strategy Specialist  
**Objetivo**: Diseñar estrategias para maximizar chances de éxito

**Funcionalidades**:
- Optimización de CV (ATS-friendly)
- Cover letters personalizadas
- Mensajes para networking
- Timing y posicionamiento

**Output**: CV optimizado, cover letter, connection message, checklist

### 4. Interview Prep Agent 🎤

**Rol**: Interview Preparation Specialist  
**Objetivo**: Preparar para entrevistas

**Funcionalidades**:
- Preguntas técnicas con soluciones
- Preguntas comportamentales (STAR)
- Research de la empresa
- Mock interviews

**Output**: Preguntas y respuestas, STAR stories, research guide, success tips

## 📊 Ejemplos de Uso

### Ejemplo 1: Búsqueda Simple

```python
from src.crew import JobSearchCrew
from src.utils.storage import DataStorage

# Cargar CV
storage = DataStorage()
resume = storage.load_resume()

# Buscar empleos
crew_manager = JobSearchCrew()
crew_manager.initialize()

crew = crew_manager.create_job_search_crew(
    search_params={
        "keywords": "python developer",
        "location": "remote",
        "limit": 10
    },
    resume_data=resume
)

result = await crew.kickoff()
print(result)
```

### Ejemplo 2: Análisis Completo

```python
# Búsqueda + Matching + Estrategia + Preparación
crew = crew_manager.create_full_analysis_crew(
    search_params={...},
    resume_data=resume,
    job_details=job,
    matching_score=75
)

result = await crew.kickoff()
```

Ver más ejemplos en `examples/`:
- `basic_usage.py` - Ejemplos básicos
- `advanced_usage.py` - Workflows avanzados

## 📁 Estructura del Proyecto

```
jobSearcher/
├── src/
│   ├── agents/          # Agentes CrewAI
│   ├── tasks/           # Definición de tareas
│   ├── tools/           # Herramientas externas
│   ├── crew/            # Configuración de crews
│   ├── models/          # Modelos de datos
│   ├── utils/           # Utilidades
│   ├── cli.py           # Interfaz CLI
│   └── main.py          # Main entry point
├── tests/               # Tests
├── examples/            # Ejemplos de uso
├── data/                # Datos almacenados
├── logs/                # Logs de ejecución
├── docs/                # Documentación
├── scripts/             # Scripts utilitarios
├── config/              # Configuración
├── requirements.txt     # Dependencias
├── .env.example        # Template de variables
├── Dockerfile          # Configuración Docker
├── docker-compose.yml  # Orquestación Docker
└── README.md           # Este archivo
```

## 🔧 Desarrollo

### Ejecutar Tests

```bash
# Con pytest
pytest tests/ -v

# O con el script
python scripts/run_tests.py
```

### Formatear Código

```bash
# Con black
black src/ tests/ examples/

# Con ruff
ruff check src/ tests/ examples/
```

### Linter

```bash
# Con flake8
flake8 src/ tests/ examples/
```

## 📖 Documentación

- [Arquitectura](docs/ARCHITECTURE.md) - Detalles de arquitectura del sistema
- [Contributing](CONTRIBUTING.md) - Guía para contribuidores
- [Changelog](CHANGELOG.md) - Historial de cambios
- [LinkedIn MCP](https://linkedapi.io/mcp/) - Documentación oficial de LinkedIn MCP

## 🐛 Troubleshooting

### LinkedIn MCP no conecta

```bash
# Verificar que el servidor MCP está corriendo
curl http://localhost:3000/health

# Revisar logs del servidor MCP
docker logs linkedin-mcp-server
```

### Error de API Key

```bash
# Verificar que las API keys están configuradas
cat .env | grep API_KEY

# Asegurarse de no tener espacios en blanco
```

### Tests fallan

```bash
# Asegurarse de estar en el entorno virtual
source venv/bin/activate

# Reinstalar dependencias
pip install -r requirements.txt
```

## 🚧 Roadmap

- [ ] Interfaz web (FastAPI + React)
- [ ] Integración con más plataformas (Indeed, Glassdoor)
- [ ] Base de datos PostgreSQL
- [ ] Sistema de notificaciones
- [ ] Dashboard de métricas
- [ ] Análisis de mercado salarial
- [ ] Integración con ATS
- [ ] Modo batch para múltiples CVs

## 🤝 Contribución

¡Las contribuciones son bienvenidas! Por favor lee [CONTRIBUTING.md](CONTRIBUTING.md) para detalles.

### Cómo Contribuir

1. Fork el proyecto
2. Crea una rama (`git checkout -b feature/nueva-feature`)
3. Commit tus cambios (`git commit -m 'feat: add nueva feature'`)
4. Push a la rama (`git push origin feature/nueva-feature`)
5. Abre un Pull Request

## 📝 Licencia

Este proyecto está licenciado bajo la Licencia MIT - ver el archivo [LICENSE](LICENSE) para detalles.

## 🙏 Reconocimientos

- [CrewAI](https://www.crewai.com/) - Framework de orquestación de agentes
- [LinkedIn MCP](https://github.com/Linked-API/linkedapi-mcp) - Integración con LinkedIn
- [LangChain](https://www.langchain.com/) - Framework de LLMs

## 📧 Contacto

- GitHub Issues: [Reportar bugs o sugerir features](https://github.com/yourusername/jobsearcher/issues)
- Email: contact@jobsearcher.dev

---

⭐ Si te gusta este proyecto, ¡dame una estrella en GitHub!
