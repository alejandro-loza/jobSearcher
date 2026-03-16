# Arquitectura de JobSearcher

## Visión General

JobSearcher es un sistema de búsqueda de empleo impulsado por IA que utiliza CrewAI para orquestar múltiples agentes especializados que trabajan en conjunto para ayudar a los usuarios a encontrar, analizar y postularse a ofertas de trabajo.

## Componentes Principales

```
┌─────────────────────────────────────────────────────────────────┐
│                        JobSearcher                              │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
┌───────▼────────┐   ┌───────▼────────┐   ┌───────▼────────┐
│   CLI Layer    │   │  CrewAI Core   │   │ External APIs   │
└───────┬────────┘   └───────┬────────┘   └───────┬────────┘
        │                     │                     │
        └─────────────────────┼─────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              │               │               │
        ┌─────▼─────┐   ┌────▼─────┐   ┌────▼─────┐
        │  Agents   │   │  Tasks   │   │  Tools   │
        └───────────┘   └──────────┘   └──────────┘
```

## 1. CLI Layer (src/cli.py)

Interfaz de línea de comandos que proporciona acceso a todas las funcionalidades del sistema.

### Comandos Disponibles:

- **search**: Busca empleos en LinkedIn
- **analyze**: Análisis completo de un puesto
- **match**: Analiza matching entre CV y empleos
- **strategy**: Genera estrategia de aplicación
- **interview**: Preparación para entrevista
- **interactive**: Modo interactivo

## 2. CrewAI Core (src/crew/)

Motor de orquestación que coordina múltiples agentes para ejecutar tareas complejas.

### JobSearchCrew

Clase principal que gestiona la creación y ejecución de crews:

- `initialize()`: Configura los agentes
- `create_job_search_crew()`: Crew para búsqueda de empleos
- `create_full_analysis_crew()`: Crew para análisis completo
- `create_career_development_crew()`: Crew para desarrollo de carrera
- `create_interview_prep_crew()`: Crew para preparación de entrevistas

## 3. Agents (src/agents/)

Agentes especializados con roles y objetivos específicos:

### JobSearchAgent
- **Rol**: Job Search Specialist
- **Objetivo**: Encontrar las mejores oportunidades de empleo en LinkedIn
- **Herramientas**: LinkedInMCPTool

### ResumeMatcherAgent
- **Rol**: Resume Matching Specialist
- **Objetivo**: Analizar el match entre perfil y requisitos del puesto
- **Especialización**: Análisis de habilidades, experiencia, gaps

### ApplicationStrategyAgent
- **Rol**: Application Strategy Specialist
- **Objetivo**: Diseñar estrategias personalizadas para maximizar chances
- **Especialización**: Optimización de CV, cover letters, networking

### InterviewPrepAgent
- **Rol**: Interview Preparation Specialist
- **Objetivo**: Preparar al candidato para entrevistas
- **Especialización**: Preguntas técnicas, comportamentales, coaching

## 4. Tasks (src/tasks/)

Definiciones de tareas que ejecutan los agentes:

### JobSearchTask
- `create()`: Busca empleos según criterios
- `create_company_analysis()`: Analiza una compañía específica

### ResumeMatcherTask
- `create()`: Analiza matching entre CV y puesto
- `create_gap_analysis()`: Identifica gaps de habilidades

### ApplicationStrategyTask
- `create()`: Diseña estrategia de aplicación
- `create_resume_optimization()`: Optimiza el CV

### InterviewPrepTask
- `create()`: Preparación general de entrevista
- `create_technical_prep()`: Preparación técnica
- `create_behavioral_prep()`: Preparación comportamental

## 5. Tools (src/tools/)

Herramientas que utilizan los agentes para interactuar con servicios externos:

### LinkedInMCPTool
Interfaz con LinkedIn MCP Server:

- `search_jobs()`: Busca empleos
- `get_job_details()`: Obtiene detalles de un empleo
- `get_profile_details()`: Analiza perfiles
- `apply_to_job()`: Aplica a un empleo
- `search_profiles()`: Busca perfiles
- `get_company_info()`: Obtiene información de compañía

## 6. Data Models (src/models/)

Definiciones de modelos de datos:

```python
JobPosting          # Oferta de empleo
Resume              # CV del usuario
MatchingResult      # Resultado de matching
ApplicationStrategy # Estrategia de aplicación
InterviewPrep       # Preparación de entrevista
JobSearchResult     # Resultado de búsqueda
```

## 7. Utilities (src/utils/)

Funciones auxiliares:

### DataStorage
- `save_resume()`: Guarda CV
- `load_resume()`: Carga CV
- `save_jobs()`: Guarda empleos
- `load_jobs()`: Carga empleos
- `save_matching_results()`: Guarda resultados de matching

### ReportGenerator
- `generate_job_search_report()`: Reporte de búsqueda
- `generate_matching_report()`: Reporte de matching

## Flujo de Trabajo Típico

```
1. Usuario ejecuta comando CLI
   ↓
2. CLI crea JobSearchCrew
   ↓
3. Crew inicializa agentes
   ↓
4. Agentes ejecutan tareas usando tools
   ↓
5. Results se procesan y guardan
   ↓
6. Reportes se generan y muestran
```

## Ejemplo: Búsqueda de Empleo

```python
# 1. Inicializar crew
crew_manager = JobSearchCrew()
crew_manager.initialize()

# 2. Crear crew de búsqueda
crew = crew_manager.create_job_search_crew(
    search_params={...},
    resume_data={...}
)

# 3. Ejecutar
result = await crew.kickoff()

# 4. Procesar resultado
storage.save_jobs(jobs)
report = generate_job_search_report(...)
```

## Integración con LinkedIn MCP

JobSearcher se integra con LinkedIn MCP a través de la clase `LinkedInMCPTool`:

```
JobSearcher ──> LinkedInMCPTool ──> LinkedIn MCP Server ──> LinkedIn API
```

El servidor MCP maneja:
- Autenticación con LinkedIn
- Rate limiting
- Scraping de datos
- Manejo de errores

## Configuración

La configuración se maneja a través de:

- **settings.py**: Variables de configuración
- **.env**: Variables de entorno (API keys, etc.)

## Logging

Se usa `loguru` para logging estructurado:

```python
logger.info("Mensaje informativo")
logger.error("Mensaje de error")
logger.success("Mensaje de éxito")
```

Los logs se guardan en el directorio `logs/`.

## Tests

Los tests se encuentran en `tests/`:

- `test_basic.py`: Tests básicos de componentes
- Se usa `pytest` como framework de tests

## Despliegue

### Local
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m src.cli --help
```

### Docker
```bash
docker-compose up -d
docker-compose exec jobsearcher /bin/bash
python -m src.cli search --keywords "python developer"
```

## Extensionibilidad

El sistema está diseñado para ser extensible:

1. **Nuevos Agentes**: Agregar clases en `src/agents/`
2. **Nuevas Tareas**: Agregar clases en `src/tasks/`
3. **Nuevas Tools**: Agregar en `src/tools/`
4. **Nuevos Modelos**: Agregar en `src/models/`

## Performance Considerations

- Uso de async/await para operaciones I/O
- Caché de resultados (configurable)
- Procesamiento en lotes para múltiples jobs
- Rate limiting para llamadas a APIs

## Security

- API keys almacenadas en variables de entorno
- No se guardan credenciales en código
- Validación de inputs en todos los endpoints
- Rate limiting para prevenir abuse

## Roadmap Futuro

- [ ] Interfaz web (FastAPI/React)
- [ ] Base de datos PostgreSQL para persistencia
- [ ] Sistema de notificaciones
- [ ] Integración con más plataformas (Indeed, Glassdoor)
- [ ] Análisis de mercado y tendencias salariales
- [ ] Dashboard de métricas de búsqueda
- [ ] Integración con ATS (Applicant Tracking Systems)
