# Plan de Estudio: Azure LangChain y LangGraph para Globant

**Objetivo**: Dominar Azure LangChain y LangGraph para desarrollar aplicaciones de IA generativa en Globant
**Duración sugerida**: 8-12 semanas (con dedicación de 10-15 horas/semana)
**Nivel**: Intermedio-Avanzado
**Fecha de inicio**: A definir
**Destinado a**: Alejandro Hernandez Loza - Sr. Software Engineer @ Globant

---

## 📋 Contenido del Plan

1. [Prerrequisitos](#1-prerrequisitos)
2. [Ruta de Aprendizaje](#2-ruta-de-aprendizaje)
3. [Cronograma Detallado](#3-cronograma-detallado)
4. [Proyectos Prácticos](#4-proyectos-prácticos)
5. [Aplicación en Globant](#5-aplicación-en-globant)
6. [Recursos Recomendados](#6-recursos-recomendados)
7. [Métricas de Éxito](#7-métricas-de-éxito)

---

## 1. Prerrequisitos

### Fundamentales
- ✅ Python (avanzado) - Decoradores, context managers, generators, async/await
- ✅ Conceptos de APIs REST - Request/Response, autenticación, rate limiting
- ✅ Git/GitHub - Repos, branches, PRs, code review
- ✅ Docker básico - Imágenes, contenedores, Dockerfile

### Deseables
- ⭐ OpenAI API Keys - Para prototipado rápido
- ⭐ Conceptos de Machine Learning básico - Modelos, embeddings, tokens
- ⭐ Experience con FastAPI o Flask
- ⭐ Knowledge de microservicios (ya tienes experiencia en Globant)

### Herramientas a instalar
```bash
# Python environment
python -m venv .venv
source .venv/bin/activate

# Paquetes base
pip install langchain langchain-openai langchain-azure langgraph
pip install openai azure-identity
pip install python-dotenv jupyter notebook

# Para desarrollo web (opcional)
pip install fastapi uvicorn streamlit
```

---

## 2. Ruta de Aprendizaje

### Fase 1: Fundamentos Azure AI (Semana 1)
**Objetivo**: Entender el ecosistema Azure AI y cómo LangChain se integra

**Temas**:
- Azure AI Services overview
  - Azure OpenAI Service
  - Azure Cognitive Services
  - Azure Machine Learning
- Autenticación en Azure
  - Azure AD vs API Keys
  - Managed Identity
- Azure OpenAI vs OpenAI directo
  - Diferencias
  - Cuándo usar cada uno
  - Pricing y límites

**Recursos**:
- [Azure AI Documentation](https://docs.microsoft.com/azure/cognitive-services/)
- [Azure OpenAI Service](https://azure.microsoft.com/en-us/products/cognitive-services/openai-service)
- [Azure AI Foundry](https://techcommunity.microsoft.com/t5/azure-ai-foundation-community)

**Ejercicios**:
1. Crear cuenta Azure gratuita (si no tienes)
2. Crear recurso Azure OpenAI
3. Generar API keys
4. Probar Azure OpenAI Playground
5. Llamada simple a GPT-4 desde Python

**Resultado esperado**:
- Comprender el ecosistema Azure AI
- Saber crear y configurar recursos Azure OpenAI
- Poder hacer llamadas básicas a Azure OpenAI desde Python

---

### Fase 2: LangChain Fundamentos (Semana 2-3)
**Objetivo**: Dominar los conceptos básicos de LangChain

**Temas**:
- Core Concepts
  - Chains (cadenas de prompts)
  - Prompts Templates
  - Output Parsers
  - Memory (conversational, summary, vector)
- LLM Integration
  - Modelos de Azure OpenAI
  - Modelos de OpenAI directo
  - Parámetros (temperature, max_tokens, etc.)
- Tools & Agents
  - Definición de tools
  - Toolkits preconstruidos
  - Agentes básicos (ReAct, Zero-shot)
- Document Loaders
  - Text, PDF, web scrapers
  - Splitters (RecursiveCharacter, etc.)

**Recursos**:
- [LangChain Documentation](https://python.langchain.com/docs/)
- [LangChain GitHub](https://github.com/langchain-ai/langchain)
- [LangChain Cheatsheet](https://github.com/gabrielchua/awesome-langchain)

**Ejercicios**:
1. Crear chain simple de prompts
2. Usar prompt templates con variables
3. Implementar chain con output parser
4. Cargar y procesar documentos con LangChain
5. Crear tool personalizada
6. Implementar agente ReAct básico

**Resultado esperado**:
- Entender chains, prompts, tools, agents
- Poder crear aplicaciones LangChain básicas
- Saber integrar Azure OpenAI en LangChain

---

### Fase 3: LangChain Avanzado (Semana 4-5)
**Objetivo**: Profundizar en features avanzadas de LangChain

**Temas**:
- Vector Stores & RAG
  - Conceptos de embeddings
  - Vector databases (Chroma, FAISS, Pinecone, Azure AI Search)
  - Retrieval Augmented Generation (RAG)
- Advanced Chains
  - Sequential chains
  - Router chains
  - Conversational chains con memory
- Agents Avanzados
  - Self-ask with search
  - BabyAGI
  - AutoGPT
- Streaming Responses
  - Streaming en LangChain
  - Manejo de tokens en tiempo real
- Callbacks & Tracing
  - LangSmith (observabilidad)
  - Callbacks personalizados
  - Debugging de chains

**Recursos**:
- [LangChain RAG Tutorial](https://python.langchain.com/docs/use_cases/question_answering.html)
- [LangSmith Platform](https://www.langchain.com/langsmith)
- [Azure AI Search](https://learn.microsoft.com/azure/search/)

**Ejercicios**:
1. Implementar RAG con Azure AI Search
2. Crear router chain para múltiples fuentes
3. Implementar conversational chain con memory
4. Crear agente BabyAGI
5. Implementar streaming responses
6. Integrar con LangSmith para tracing

**Resultado esperado**:
- Poder implementar sistemas RAG
- Crear agents avanzados
- Entender observabilidad con LangSmith
- Saber manejar streaming

---

### Fase 4: LangGraph (Semana 6-7)
**Objetivo**: Dominar LangGraph para aplicaciones complejas

**Temas**:
- LangGraph Fundamentos
  - Conceptos de grafos (nodes, edges, state)
  - Graph Architecture
  - Ciclos de ejecución
- Nodes & Edges
  - Tipos de nodes (LLM, tools, conditional)
  - Definición de edges (simple, conditional)
- State Management
  - TypedDict para estado
  - Reducers (agregación de estado)
  - Persistence de estado
- Advanced Features
  - Sub-graphs
  - Parallel execution
  - Conditional branching
  - Interrupts & Human-in-the-loop
- Integration with LangChain
  - Usar chains como nodes
  - Migración de chains a graphs

**Recursos**:
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [LangGraph Examples](https://github.com/langchain-ai/langgraph/tree/main/examples)
- [LangGraph vs LangChain](https://langchain-ai.github.io/langgraph/concepts/low_level_vs_high_level)

**Ejercicios**:
1. Crear graph simple con 2 nodes
2. Implementar conditional branching
3. Crear graph con multiple agents
4. Implementar human-in-the-loop workflow
5. Migrar chain existente a graph
6. Implementar graph con persistencia de estado

**Resultado esperado**:
- Entender arquitectura de graphs
- Poder crear aplicaciones complejas con LangGraph
- Saber migrar de LangChain a LangGraph

---

### Fase 5: Azure-Specific Features (Semana 8)
**Objetivo**: Dominar features específicos de Azure en LangChain

**Temas**:
- Azure OpenAI en LangChain
  - Configuración de AzureOpenAI
  - Uso de modelos específicos (GPT-4, GPT-3.5-Turbo)
  - Deployment types (Standard, Provisioned)
- Azure AI Search Integration
  - Vector store específico de Azure
  - Hybrid search (keyword + vector)
  - Semantic search
- Azure Functions con LangChain
  - Serverless AI applications
  - Triggers HTTP, Timer
- Azure AI Foundry
  - Custom skills
  - Orchestration básica

**Recursos**:
- [LangChain Azure Integration](https://python.langchain.com/docs/integrations/azure/)
- [Azure AI Search LangChain](https://python.langchain.com/docs/integrations/vectorstores/azuresearch)
- [Azure AI Foundry](https://techcommunity.microsoft.com/t5/azure-ai-foundation-community)

**Ejercicios**:
1. Configurar AzureOpenAI en LangChain
2. Implementar RAG con Azure AI Search
3. Crear Azure Function con LangChain
4. Probar diferentes modelos de Azure OpenAI
5. Implementar hybrid search

**Resultado esperado**:
- Saber configurar LangChain con Azure OpenAI
- Poder implementar RAG con Azure AI Search
- Crear serverless apps con Azure Functions + LangChain

---

## 3. Cronograma Detallado

### Semana 1: Azure AI Fundamentos
| Día | Tema | Ejercicios | Tiempo estimado |
|---|---|---|---|
| Lun | Azure AI Overview, Azure OpenAI Service | Crear cuenta Azure, crear recurso | 2h |
| Mar | Autenticación Azure, API Keys | Probar Azure OpenAI Playground | 2h |
| Mié | Azure OpenAI vs OpenAI directo | Comparar pricing y límites | 1h |
| Jue | Primera llamada a Azure OpenAI desde Python | Implementar cliente básico | 2h |
| Vie | Repaso y práctica | Resolver ejercicios pendientes | 2h |

### Semana 2: LangChain Básico
| Día | Tema | Ejercicios | Tiempo estimado |
|---|---|---|---|
| Lun | Instalación, conceptos básicos | Setup environment, first chain | 2h |
| Mar | Prompt Templates | Crear templates complejos | 2h |
| Mié | Output Parsers | Implementar parser estructurado | 2h |
| Jue | Document Loaders | Cargar PDFs y web docs | 2h |
| Vie | Memory en LangChain | Implementar conversational memory | 2h |

### Semana 3: LangChain Intermedio
| Día | Tema | Ejercicios | Tiempo estimado |
|---|---|---|---|
| Lun | Tools & Toolkits | Usar herramientas preconstruidas | 2h |
| Mar | Crear tools personalizadas | Implementar tool de búsqueda | 2h |
| Mié | Agents básicos | Implementar agente ReAct | 2h |
| Jue | Azure OpenAI integration | Migrar a Azure OpenAI | 2h |
| Vie | Proyecto pequeño | Chatbot con RAG simple | 3h |

### Semana 4: LangChain Avanzado I
| Día | Tema | Ejercicios | Tiempo estimado |
|---|---|---|---|
| Lun | Vector Stores & RAG | RAG con Chroma local | 2h |
| Mar | Azure AI Search | RAG con Azure AI Search | 2h |
| Mié | Sequential Chains | Chain compleja de 3+ steps | 2h |
| Jue | Router Chains | Router basado en tipo de pregunta | 2h |
| Vie | Proyecto RAG avanzado | Sistema de preguntas y respuestas | 3h |

### Semana 5: LangChain Avanzado II
| Día | Tema | Ejercicios | Tiempo estimado |
|---|---|---|---|
| Lun | Conversational Chains | Chatbot con memoria de largo plazo | 2h |
| Mar | BabyAGI | Agente auto-iterativo | 2h |
| Mié | Streaming Responses | Streaming con FastAPI | 2h |
| Jue | Callbacks & Tracing | Integración con LangSmith | 2h |
| Vie | Proyecto agente avanzado | Asistente con múltiples herramientas | 3h |

### Semana 6: LangGraph Fundamentos
| Día | Tema | Ejercicios | Tiempo estimado |
|---|---|---|---|
| Lun | Conceptos de grafos | Diagramar graph de ejemplo | 2h |
| Mar | Nodes & Edges | Crear graph simple 2 nodes | 2h |
| Mie | State Management | TypedDict para estado | 2h |
| Jue | Conditional branching | Graph con ramas | 2h |
| Vie | Proyecto graph básico | Workflow de aprobación | 3h |

### Semana 7: LangGraph Avanzado
| Día | Tema | Ejercicios | Tiempo estimado |
|---|---|---|---|
| Lun | Sub-graphs | Graph anidado | 2h |
| Mar | Parallel execution | Nodes en paralelo | 2h |
| Mié | Human-in-the-loop | Graph con aprobación humana | 2h |
| Jue | Migración chain→graph | Migrar proyecto anterior | 2h |
| Vie | Proyecto graph avanzado | Sistema multi-agente | 3h |

### Semana 8: Azure-Specific Features
| Día | Tema | Ejercicios | Tiempo estimado |
|---|---|---|---|
| Lun | Azure OpenAI en LangChain | Configuración completa | 2h |
| Mar | Azure AI Search avanzado | Hybrid search | 2h |
| Mié | Azure Functions | Serverless AI app | 2h |
| Jue | Azure AI Foundry | Custom skill básico | 2h |
| Vie | Proyecto Azure completo | RAG con Azure AI Search + Functions | 3h |

---

## 4. Proyectos Prácticos

### Proyecto 1: Chatbot con RAG (Semana 3)
**Descripción**: Chatbot que responde preguntas sobre documentos

**Tech Stack**:
- LangChain
- Azure OpenAI
- Chroma (local) o Azure AI Search
- Streamlit (UI)

**Features**:
- Cargar documentos (PDF, TXT)
- Indexar con embeddings
- Chat con contexto de documentos
- Referencias a fuentes

**Tiempo estimado**: 8-10 horas

### Proyecto 2: Agente de Búsqueda Web (Semana 4-5)
**Descripción**: Agente que busca en internet y genera respuestas

**Tech Stack**:
- LangChain
- Azure OpenAI
- SerpAPI o Google Search
- FastAPI

**Features**:
- Búsqueda en múltiples fuentes
- Resumen de resultados
- Citas y referencias
- Streaming de respuesta

**Tiempo estimado**: 10-12 horas

### Proyecto 3: Asistente Multi-Tool (Semana 6-7)
**Descripción**: Asistente con múltiples herramientas y workflow complejo

**Tech Stack**:
- LangGraph
- Azure OpenAI
- LangChain tools (calculator, search, weather)
- FastAPI

**Features**:
- Múltiples tools (cálculo, búsqueda, API)
- Workflow con branching condicional
- Estado persistente
- Human-in-the-loop para aprobaciones

**Tiempo estimado**: 12-15 horas

### Proyecto 4: Sistema RAG Empresarial (Semana 8)
**Descripción**: Sistema RAG con Azure AI Search y Azure Functions

**Tech Stack**:
- LangChain
- Azure OpenAI
- Azure AI Search (vector + keyword)
- Azure Functions
- React o Streamlit (UI)

**Features**:
- Búsqueda híbrida (keyword + vector)
- Indexado de documentos masivo
- Reranking de resultados
- Filtros por metadata
- Dashboard de administración
- Analytics de uso

**Tiempo estimado**: 15-20 horas

---

## 5. Aplicación en Globant

### Oportunidades de Aplicación

#### Proyectos Actuales en Globant
**Proyecto 1: Taulia Inc. (Thomson Reuters previo)**
- **Tech**: Spring Boot/Groovy, SAP CPI, Kafka
- **Oportunidad**: Implementar AI para optimizar procesos SAP
- **LangChain aplicable**: Sí
  - Agente para analizar errores de integración
  - RAG para documentación SAP
  - LangGraph para workflow de resolución de errores

**Proyecto 2: Flow (WeWork)**
- **Tech**: Kafka, Event-Driven, Kotlin, Go/Python
- **Oportunidad**: AI para análisis de eventos de flujo de trabajo
- **LangChain aplicable**: Sí
  - Agente para detectar anomalías en flujos de trabajo
  - LangGraph para workflow de análisis complejo
  - Streaming con LangChain para tiempo real

**Proyecto 3: Nuevos clientes de Globant**
- Investigar proyectos nuevos en Globant
- Identificar oportunidades para Azure AI/LangChain
- Proponer implementaciones de IA generativa

#### Ideas de Propuestas

**Propuesta 1: Intelligent Error Resolution Assistant**
**Contexto**: Proyectos de integración (Taulia, SAP CPI, etc.)
**Problema**: Errores de integración son difíciles de diagnosticar
**Solución**: Agente AI que:
- Analiza logs de integración
- Busca en documentación SAP/Kafka
- Propone soluciones basado en historial
- Aprende de errores previos (RAG)

**Tech Stack**:
- LangGraph para workflow de diagnóstico
- Azure OpenAI para generación
- Azure AI Search para documentación técnica
- Azure Functions para serverless
- Integración con SAP CPI logs

**Valor para Globant**:
- Reducción de tiempo de resolución de errores
- Menor dependencia de expertos SAP
- Escalabilidad a nuevos clientes
- Diferenciador en mercado de integración

**Propuesta 2: Process Optimization Agent**
**Contexto**: Proyectos de procesos de negocio
**Problema**: Procesos manuales e ineficientes
**Solución**: Agente AI que:
- Analiza workflows actuales
- Identifica cuellos de botella
- Procesa optimización de pasos
- Genera documentación de proceso mejorado

**Tech Stack**:
- LangGraph para workflow de análisis
- Azure OpenAI para análisis de procesos
- Document loaders para procesos existentes
- Dashboard para visualización de before/after

**Valor para Globant**:
- Automatización de análisis de procesos
- Identificación de oportunidades de mejora
- Reducción de costos operativos
- Selling point para nuevos proyectos

**Propuesta 3: Knowledge Base Query System**
**Contexto**: Organizaciones con mucha documentación técnica
**Problema**: Encontrar información relevante es lento
**Solución**: Sistema RAG que:
- Indexa toda la documentación técnica
- Responde preguntas específicas
- Genera código basado en ejemplos
- Propone mejores prácticas

**Tech Stack**:
- LangChain con RAG
- Azure AI Search para búsqueda vectorial
- Azure OpenAI para generación
- LangGraph para workflow de búsqueda complejo
- UI con React o Streamlit

**Valor para Globant**:
- Reducción de tiempo de búsqueda
- Menor dependencia de expertos senior
- Onboarding más rápido de nuevos miembros
- Sistema escalable para documentación masiva

#### Roadmap de Implementación

**Fase 1: PoC (2-3 semanas)**
- Elegir proyecto piloto (Error Resolution Assistant)
- Implementar MVP con LangChain básico
- Demostrar a stakeholders
- Obtener feedback

**Fase 2: Despliegue (4-6 semanas)**
- Migrar a LangGraph
- Integrar con sistemas existentes (SAP, Kafka, etc.)
- Implementar Azure AI Search
- Testing y debugging

**Fase 3: Producción (4-8 semanas)**
- Optimización de performance
- Escalabilidad
- Monitoreo y observabilidad
- Documentación y training

---

## 6. Recursos Recomendados

### Documentación Oficial
- [Azure OpenAI Documentation](https://docs.microsoft.com/azure/cognitive-services/openai/)
- [LangChain Documentation](https://python.langchain.com/docs/)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [Azure AI Search](https://learn.microsoft.com/azure/search/)

### Cursos y Tutoriales
- **LangChain Academy** (free)
  - https://academy.langchain.com/
- **Azure AI Learn** (free)
  - https://learn.microsoft.com/azure/ai-fundamentals
- **LangChain YouTube Channel**
  - https://www.youtube.com/@LangChain
- **LangGraph Examples**
  - https://github.com/langchain-ai/langgraph/tree/main/examples

### Libros y Papers
- "LangChain for LLM Application Development" (O'Reilly)
- "Building Applications with LLMs" (O'Reilly)
- ArXiv papers sobre RAG y agents

### Comunidades
- LangChain Discord: https://discord.gg/langchain
- Azure AI Community: https://techcommunity.microsoft.com/t5/azure-ai-foundation-community
- Stack Overflow tags: langchain, azure-openai, langgraph

### Herramientas
- **LangSmith** (observabilidad): https://www.langchain.com/langsmith
- **Azure Portal**: https://portal.azure.com
- **Azure Cloud Shell**: https://shell.azure.com
- **VS Code** con extensiones Python y Azure

---

## 7. Métricas de Éxito

### Corto Plazo (4-6 semanas)
- [ ] Completar fases 1-4 del cronograma
- [ ] Implementar 2 proyectos prácticos completos
- [ ] Generar 1 propuesta de valor para Globant
- [ ] Obtener feedback positivo de stakeholders

### Mediano Plazo (8-12 semanas)
- [ ] Completar todas las fases del cronograma
- [ ] Implementar 4 proyectos prácticos
- [ ] Crear PoC en proyecto actual de Globant
- [ ] Presentar propuesta formal a equipo/proyecto

### Largo Plazo (12-16 semanas)
- [ ] Desplegar solución en producción
- [ ] Documentar arquitectura y código
- [ ] Mentorear a otros desarrolladores en Globant
- [ ] Publicar caso de éxito (con permiso)

### Indicadores Clave
- Nivel de confianza en Azure OpenAI API
- Cantidad de proyectos completados
- Calidad de código (según code review)
- Feedback de peers y stakeholders
- Tiempo de implementación de PoC

---

## 🎯 Próximos Pasos

### Inmediato (Esta semana)
1. [ ] Instalar environment de desarrollo
2. [ ] Crear cuenta Azure gratuita
3. [ ] Comenzar Fase 1 (Azure AI Fundamentos)
4. [ ] Crear repositorio en GitHub para proyectos

### Esta semana
5. [ ] Completar Semana 1 del cronograma
6. [ ] Comenzar Proyecto 1 (Chatbot con RAG)
7. [ ] Identificar proyecto piloto en Globant
8. [ ] Programar reunión con stakeholders

### Próximas 2 semanas
9. [ ] Completar Semanas 2-4 del cronograma
10. [ ] Terminar Proyecto 1
11. [ ] Iniciar Proyecto 2 (Agente de Búsqueda Web)
12. [ ] Elaborar propuesta de valor para Globant

---

## 💡 Tips de Aprendizaje

1. **Practica activa**: No solo leer código, escribirlo
2. **Documentar todo**: Create repositorios READMEs detallados
3. **Compartir**: Hacer pull requests, discutir en comunidades
4. **Iterar**: Mejorar proyectos basado en feedback
5. **Real-world**: Aplicar aprendizajes a proyectos de Globant
6. **Stay updated**: Siguir releases de LangChain y LangGraph
7. **Network**: Conectar con otros desarrolladores de AI
8. **Showcase**: Preparar demo para presentar a Globant

---

## 📞 Soporte y Consultas

Para dudas o consultas durante el estudio:
- **Documentación**: Referir a documentación oficial primero
- **Comunidades**: Preguntar en Discord de LangChain, Stack Overflow
- **Colleagues**: Consultar con otros devs de Globant interesados en AI
- **Mentor**: Si hay oportunidad, buscar mentor senior en Azure AI

---

**Plan creado por**: Alejandro Hernandez Loza
**Versión**: 1.0
**Fecha**: 2026-04-03
**Guardado en**: `docs/azure_langchain_study_plan.md`
