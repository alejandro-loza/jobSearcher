# Big Pickle / GLM-4.6 en JobSearcher

Big Pickle (también conocido como GLM-4.6) es un modelo de IA que usa la palabra clave `Ultrathink` para activar un modo de pensamiento más profundo y analítico.

## ¿Por qué usar Big Pickle?

Big Pickle ofrece varias ventajas para tareas de análisis de empleo:

- **Modo Ultrathink**: Pensamiento más profundo y analítico
- **Análisis detallado**: Mejor para matching complejos
- **Contexto extendido**: Mayor capacidad de contexto
- **Costo reducido**: Generalmente más económico que GPT-4

## Configuración

### 1. Instalar el plugin Pickle-Thinker

Crea o edita el archivo `.opencode/opencode.json` en tu proyecto:

```json
{
  "plugin": ["@howaboua/pickle-thinker@0.4.0"]
}
```

### 2. Actualizar .env

Agrega o actualiza la configuración para Big Pickle:

```bash
# Big Pickle / GLM-4.6 Configuration
BIG_PICKLE_ENABLED=true
BIG_PICKLE_MODEL=glm-4.6
BIG_PICKLE_API_KEY=your_api_key_here
BIG_PICKLE_BASE_URL=https://api.zai.com/v1

# O si usas OpenAI compatible endpoint
OPENAI_API_KEY=your_big_pickle_key
OPENAI_BASE_URL=https://api.zai.com/v1
```

### 3. Actualizar config/settings.py

El archivo `config/settings.py` ya tiene soporte para configuración flexible. Asegúrate de incluir:

```python
class Settings(BaseSettings):
    # Big Pickle / GLM-4.6
    big_pickle_enabled: bool = Field(default=False, env="BIG_PICKLE_ENABLED")
    big_pickle_model: str = Field(default="glm-4.6", env="BIG_PICKLE_MODEL")
    big_pickle_api_key: str = Field(default="", env="BIG_PICKLE_API_KEY")
    big_pickle_base_url: str = Field(default="https://api.zai.com/v1", env="BIG_PICKLE_BASE_URL")
```

## Uso con CrewAI

### Configurar CrewAI para usar Big Pickle

CrewAI soporta múltiples LLM providers. Aquí está cómo configurar Big Pickle:

```python
from langchain_openai import ChatOpenAI
from config import settings

def get_llm():
    """Retorna el LLM configurado (Big Pickle o OpenAI)"""
    
    if settings.big_pickle_enabled:
        return ChatOpenAI(
            model=settings.big_pickle_model,
            api_key=settings.big_pickle_api_key,
            base_url=settings.big_pickle_base_url,
            temperature=0.7,
            max_tokens=4000
        )
    else:
        # Fallback a OpenAI
        return ChatOpenAI(
            model="gpt-4o-mini",
            api_key=settings.openai_api_key,
            temperature=0.7,
            max_tokens=4000
        )

# Usar en los agentes
from crewai import Agent

agent = Agent(
    role="Job Search Specialist",
    goal="Encontrar las mejores oportunidades de empleo",
    backstory="...",
    llm=get_llm()  # Usa Big Pickle o OpenAI
)
```

## Modo Ultrathink

El plugin Pickle-Thinker automáticamente inyecta `Ultrathink` en:

1. **Cada mensaje del usuario**: Asegura que el modelo siempre piense
2. **Después de tool results**: El modelo analiza los resultados antes de continuar
3. **En outputs de tools**: Safety net adicional

### Ventajas del modo Ultrathink para JobSearcher:

- **Matching más preciso**: Análisis más profundo de CV vs requisitos
- **Análisis de compañía**: Investigación más exhaustiva
- **Estrategia mejorada**: Pensamiento más estratégico para aplicaciones
- **Preparación de entrevistas**: Preguntas más relevantes y respuestas más detalladas

## Ejemplo: Agente con Big Pickle

```python
from crewai import Agent
from langchain_openai import ChatOpenAI
from config import settings

# Crear LLM con Big Pickle
big_pickle_llm = ChatOpenAI(
    model="glm-4.6",
    api_key=settings.big_pickle_api_key,
    base_url="https://api.zai.com/v1",
    temperature=0.7
)

# Crear agente usando Big Pickle
job_search_agent = Agent(
    role="Job Search Specialist",
    goal="Encontrar las mejores oportunidades de empleo con análisis profundo",
    backstory="""
    Eres un experto en búsqueda de empleo con un enfoque analítico detallado.
    Tu capacidad de pensar profundamente sobre cada aspecto de un puesto de trabajo
    te permite encontrar oportunidades que otros pasan por alto.
    
    Siempre usas el modo Ultrathink para:
    - Analizar descripciones de puestos en profundidad
    - Evaluar requisitos implícitos
    - Identificar red flags
    - Determinar la compatibilidad cultural
    """,
    verbose=True,
    allow_delegation=False,
    llm=big_pickle_llm
)
```

## Configuración del Crew con Big Pickle

```python
from crewai import Crew, Process
from src.agents import JobSearchAgent, ResumeMatcherAgent
from src.tasks import JobSearchTask, ResumeMatcherTask
from langchain_openai import ChatOpenAI
from config import settings

def create_big_pickle_crew():
    """Crea un crew que usa Big Pickle"""
    
    # Configurar Big Pickle LLM
    big_pickle_llm = ChatOpenAI(
        model=settings.big_pickle_model,
        api_key=settings.big_pickle_api_key,
        base_url=settings.big_pickle_base_url,
        temperature=0.7
    )
    
    # Crear agentes con Big Pickle
    job_searcher = JobSearchAgent.create()
    resume_matcher = ResumeMatcherAgent.create()
    
    # Asignar LLM a los agentes
    job_searcher.llm = big_pickle_llm
    resume_matcher.llm = big_pickle_llm
    
    # Crear crew
    crew = Crew(
        agents=[job_searcher, resume_matcher],
        tasks=[job_search_task, matching_task],
        process=Process.hierarchical,
        verbose=True,
        manager_llm=big_pickle_llm  # Manager también usa Big Pickle
    )
    
    return crew
```

## Comparación: Big Pickle vs OpenAI

| Característica | Big Pickle (GLM-4.6) | OpenAI (GPT-4) |
|---------------|----------------------|-----------------|
| **Costo** | Más económico | Más costoso |
| **Modo Ultrathink** | ✅ Nativo | ❌ No disponible |
| **Análisis profundo** | ✅ Excelente | ✅ Muy bueno |
| **Velocidad** | Rápido | Rápido |
| **Contexto** | Largo | Largo |
| **Matching** | Muy preciso | Preciso |

## Recomendaciones

### Cuándo usar Big Pickle:
- ✅ Análisis de matching complejo
- ✅ Análisis de cultura de empresa
- ✅ Preparación detallada de entrevistas
- ✅ Estrategia de aplicación
- ✅ Presupuesto limitado

### Cuándo usar OpenAI:
- ✅ Tareas simples de búsqueda
- ✅ Resumir grandes volúmenes de datos
- ✅ Necesidad de máxima consistencia
- ✅ Integración con otros servicios OpenAI

## Troubleshooting

### Big Pickle no entra en modo Ultrathink

1. Verifica que el plugin Pickle-Thinker esté instalado
2. Revisa la configuración en `.opencode/pickle-thinker.jsonc`
3. Asegúrate de que el modelo sea uno de los objetivos:
   ```json
   "targetModels": [
     "glm-4.6",
     "big-pickle",
     "opencode/big-pickle"
   ]
   ```

### Error de autenticación

```bash
# Verificar API key
echo $BIG_PICKLE_API_KEY

# Test del endpoint
curl -H "Authorization: Bearer $BIG_PICKLE_API_KEY" \
  https://api.zai.com/v1/models
```

### Agentes no usan Big Pickle

Verifica que los agentes tengan asignado el LLM:

```python
agent = Agent(
    role="...",
    goal="...",
    llm=get_big_pickle_llm()  # IMPORTANTE
)
```

## Referencias

- [Pickle-Thinker Plugin](https://github.com/IgorWarzocha/Pickle-Thinker)
- [GLM-4.6 Documentation](https://docs.zai.com)
- [CrewAI LLM Configuration](https://docs.crewai.com/how-to/llms)
