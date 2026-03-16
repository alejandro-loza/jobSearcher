# Pedido para Antigravity — Dashboard con Chatbot

Fecha: 2026-03-08

## Resumen

Rediseña el dashboard del sistema JobSearcher (`src/dashboard.py`) para que sea un
panel de control completo con **chatbot integrado** para interactuar con la IA.

El dashboard actual es básico (solo muestra pipeline de aplicaciones).
Necesitamos algo mucho más completo y funcional.

---

## Requisitos del Dashboard

### 1. Vista general (Home)
- **Estadísticas clave** en cards:
  - Total jobs encontrados
  - Aplicaciones enviadas hoy / total
  - Entrevistas agendadas
  - Tasa de respuesta (%)
  - Jobs con score >= 75% sin aplicar
- **Gráfica** de aplicaciones por día (últimos 30 días)
- **Pipeline visual** (kanban-style):
  Applied → Viewed → Response → Interview → Technical Test → Offer → Accepted/Rejected

### 2. Lista de Jobs
- Tabla con todos los jobs encontrados
- Columnas: título, empresa, ubicación, score, estado, fecha, URL
- Filtros: por score (>= 75, >= 85, >= 90), por empresa, por ubicación, por estado
- Ordenar por: score, fecha, empresa
- Acción: botón "Aplicar" para jobs pendientes

### 3. Aplicaciones
- Lista de todas las aplicaciones con su estado en el pipeline
- Detalle: cover letter generada, método de aplicación, fecha
- Botón para avanzar el stage manualmente

### 4. LinkedIn Conversations
- Lista de conversaciones con reclutadores
- Estado: pending, responded, escalated
- Último mensaje de cada conversación
- Acción: ver historial completo

### 5. Entrevistas
- Calendario con entrevistas agendadas
- Próxima entrevista destacada
- Link de videollamada si existe

### 6. Chatbot (IMPORTANTE)
- **Panel de chat** en la esquina inferior derecha (floating) o en sidebar
- El usuario puede escribir mensajes como:
  - "busca trabajo de Java en Guadalajara"
  - "¿cuántas aplicaciones llevo hoy?"
  - "aplica a todos los jobs con score >= 90"
  - "muéstrame las conversaciones de LinkedIn"
  - "agenda entrevista el lunes a las 9am"
  - "estado del sistema"
- **Backend**: crear endpoint `POST /chat` que reciba `{"message": "..."}` y retorne `{"response": "..."}`
- El endpoint debe:
  1. Parsear el intent del mensaje (buscar, aplicar, estado, agendar, etc.)
  2. Ejecutar la acción correspondiente usando las herramientas existentes
  3. Retornar la respuesta en texto
- Usar `master_agent.handle_whatsapp_command()` como base (ya parsea comandos)
- O crear un nuevo handler más completo en `src/agents/chat_agent.py`
- El chat debe recordar contexto de la conversación (al menos últimos 10 mensajes)
- Mostrar respuestas con formato (markdown rendered)

---

## Arquitectura

### Frontend
- **HTML + CSS + JavaScript** puro (sin frameworks pesados)
- Usar Tailwind CSS via CDN para estilos modernos
- El HTML se genera en `src/dashboard.py` → `generate_dashboard_html()`
- Hacer fetch a los endpoints API del orchestrator para datos dinámicos
- WebSocket o polling cada 10s para actualizar stats en tiempo real

### Backend (endpoints necesarios)
Ya existen:
- `GET /health` → stats generales
- `GET /dashboard` → HTML del dashboard
- `GET /pipeline` → pipeline JSON
- `POST /trigger/search` → trigger búsqueda
- `POST /trigger/apply-all` → aplicar a todos

**Nuevos endpoints necesarios:**
- `POST /chat` → chatbot (recibe message, retorna response)
- `GET /api/jobs?score_min=75&status=found&limit=50` → lista de jobs filtrada
- `GET /api/applications?limit=50` → lista de aplicaciones
- `GET /api/conversations` → conversaciones LinkedIn
- `GET /api/stats` → estadísticas para el dashboard
- `GET /api/interviews` → entrevistas agendadas

### Archivos a modificar/crear
- `src/dashboard.py` — reescribir completamente con nuevo HTML
- `src/orchestrator.py` — agregar nuevos endpoints API
- `src/agents/chat_agent.py` — (nuevo) handler de chatbot

---

## Datos disponibles en la DB

```python
from src.db.tracker import JobTracker
t = JobTracker()

# Stats
t.get_stats()  # {total_found, applied, interviews_scheduled, rejected, pending}

# Jobs
t.get_jobs_by_status('found')  # lista de jobs
t.get_all_jobs(limit=100)  # todos los jobs

# Applications
t.get_full_pipeline(limit=100)  # aplicaciones con pipeline stage
t.get_pipeline_summary()  # conteo por stage

# Conversations
t.get_unprocessed_conversations()  # pendientes
t.get_conversation_history(conv_id)  # historial de un thread

# Interviews
# Consultar directamente: SELECT * FROM interviews
```

### Schema de la DB (SQLite: data/jobsearcher.db)

```sql
-- Jobs encontrados
CREATE TABLE jobs (
    id TEXT PRIMARY KEY,
    title TEXT, company TEXT, location TEXT,
    description TEXT, url TEXT, salary TEXT,
    source TEXT, match_score INTEGER DEFAULT 0,
    found_at TIMESTAMP, status TEXT DEFAULT 'found',
    raw_data TEXT, applied_url TEXT
);

-- Aplicaciones
CREATE TABLE applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT, method TEXT, cover_letter TEXT,
    applied_at TIMESTAMP, status TEXT DEFAULT 'applied',
    pipeline_stage TEXT DEFAULT 'applied',
    stage_updated_at TIMESTAMP, notes TEXT
);

-- Conversaciones LinkedIn
CREATE TABLE linkedin_conversations (
    conversation_id TEXT PRIMARY KEY,
    participant_name TEXT, participant_title TEXT,
    last_message TEXT, last_message_at TIMESTAMP,
    state TEXT DEFAULT 'new', notes TEXT,
    created_at TIMESTAMP, updated_at TIMESTAMP
);

-- Mensajes LinkedIn
CREATE TABLE linkedin_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT, body TEXT,
    from_me BOOLEAN, sender_name TEXT,
    linkedin_timestamp TEXT, processed BOOLEAN DEFAULT 0,
    created_at TIMESTAMP
);
```

---

## Estilo visual

- **Dark theme** (fondo oscuro, texto claro)
- Colores de accent: azul (#3b82f6) para acciones, verde para éxito, rojo para errores
- Cards con bordes redondeados y sombras sutiles
- Responsive (funcionar en mobile también)
- El chatbot debe verse como un chat moderno (burbujas, timestamps)

---

## Cómo probar

```bash
cd /data/projects/proyects/jobSearcher

# El orchestrator ya corre en http://localhost:8777
# Dashboard: http://localhost:8777/dashboard

# Para reiniciar después de cambios:
# Ctrl+C y luego:
venv/bin/python run.py
```

---

## Datos de contexto

- El proyecto está en `/data/projects/proyects/jobSearcher`
- venv: `venv/bin/python`
- DB: `data/jobsearcher.db`
- CV: `data/resume.json`
- El orchestrator corre en puerto 8777
- Lee el `CLAUDE.md` en la raíz del proyecto para entender todas las herramientas
- El dashboard actual está en `src/dashboard.py` (función `generate_dashboard_html()`)
- Los endpoints existentes están en `src/orchestrator.py`
