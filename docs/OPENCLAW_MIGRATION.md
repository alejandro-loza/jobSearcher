# 🦞 Plan de Migración de JobSearcher a OpenClaw

## 📋 Resumen Ejecutivo

**Enfoque**: Skills modulares - Cada agente/funcionalidad se convierte en un skill independiente de OpenClaw.
**Cobertura**: Migración completa de todos los componentes (job search, agentes, herramientas, canales).
**Datos**: Nueva base de datos específica para OpenClaw con migración de datos históricos.
**Canales**: WhatsApp, LinkedIn, Gmail, Telegram, Slack (prioridad completa).
**Timeline estimado**: 15-20 días (aprox. 3 semanas).
**Fecha de planificación**: Abril 6, 2026.

---

## 🏗️ Arquitectura Propuesta

### Arquitectura Actual (JobSearcher)

```
┌─────────────────────────────────────┐
│  FastAPI Orchestrator (Port 8777)  │
│  ┌───────────────────────────────┐ │
│  │ APScheduler                   │ │
│  │ - job_search (6h)            │ │
│  │ - linkedin_messages (15min)   │ │
│  │ - email_monitor (30min)       │ │
│  │ - followup (daily)            │ │
│  └───────────────────────────────┘ │
│                                   │
│  ┌───────────────────────────────┐ │
│  │ Python Agents                │ │
│  │ - master_agent               │ │
│  │ - recruiter_agent             │ │
│  │ - coordinator                 │ │
│  │ - job_stalker_agent           │ │
│  │ - linkedin_hr_agent           │ │
│  └───────────────────────────────┘ │
│                                   │
│  ┌───────────────────────────────┐ │
│  │ Tools                         │ │
│  │ - jobspy_tool                 │ │
│  │ - linkedin_messages_tool      │ │
│  │ - gmail_tool                  │ │
│  │ - calendar_tool               │ │
│  │ - whatsapp_tool               │ │
│  │ - browser_tool                │ │
│  └───────────────────────────────┘ │
└─────────────────────────────────────┘
           │
           ├── WhatsApp Bridge (Node.js)
           ├── SQLite DB
           └── Google APIs
```

### Nueva Arquitectura (OpenClaw)

```
┌──────────────────────────────────────────────────────────┐
│              OpenClaw Gateway (Port 18789)              │
│  ┌────────────────────────────────────────────────────┐ │
│  │ WebSocket Control Plane                            │ │
│  │ - Sessions Management                               │ │
│  │ - Tool Streaming                                    │ │
│  │ - Event Broadcasting                                │ │
│  └────────────────────────────────────────────────────┘ │
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │ Skills Platform (~/.openclaw/workspace/skills/)   │ │
│  │                                                     │ │
│  │ 📦 jobsearcher-core/                  │ │
│  │   └── SKILL.md                                  │ │
│  │                                                     │ │
│  │ 📦 jobsearcher-search/                │ │
│  │   ├── search_jobs.sh                     │ │
│  │   ├── stalker_jobs.sh                    │ │
│  │   └── SKILL.md                           │ │
│  │                                                     │ │
│  │ 📦 jobsearcher-evaluation/             │ │
│  │   ├── evaluate_match.sh                 │ │
│  │   ├── generate_cover_letter.sh          │ │
│  │   └── SKILL.md                           │ │
│  │                                                     │ │
│  │ 📦 jobsearcher-application/            │ │
│  │   ├── apply_easy.sh                     │ │
│  │   ├── apply_browser.sh                  │ │
│  │   └── SKILL.md                           │ │
│  │                                                     │ │
│  │ 📦 jobsearcher-linkedin/               │ │
│  │   ├── check_messages.sh                 │ │
│  │   ├── reply_recruiter.sh                │ │
│  │   ├── connect_hr.sh                     │ │
│  │   └── SKILL.md                           │ │
│  │                                                     │ │
│  │ 📦 jobsearcher-email/                  │ │
│  │   ├── monitor_emails.sh                 │ │
│  │   ├── send_email.sh                     │ │
│  │   └── SKILL.md                           │ │
│  │                                                     │ │
│  │ 📦 jobsearcher-calendar/               │ │
│  │   ├── get_slots.sh                      │ │
│  │   ├── schedule_interview.sh              │ │
│  │   └── SKILL.md                           │ │
│  │                                                     │ │
│  │ 📦 jobsearcher-browser/                 │ │
│  │   ├── apply_to_portal.sh                │ │
│  │   ├── fill_form.sh                      │ │
│  │   └── SKILL.md                           │ │
│  │                                                     │ │
│  │ 📦 jobsearcher-tracker/                 │ │
│  │   ├── get_stats.sh                      │ │
│  │   ├── list_jobs.sh                      │ │
│  │   ├── update_status.sh                  │ │
│  │   └── SKILL.md                           │ │
│  │                                                     │ │
│  │ 📦 jobsearcher-maintenance/             │ │
│  │   ├── followup_applications.sh          │ │
│  │   ├── cleanup_old_jobs.sh               │ │
│  │   └── SKILL.md                           │ │
│  │                                                     │ │
│  │ 📦 jobsearcher-orchestrator/            │ │
│  │   ├── setup_workflow.sh                  │ │
│  │   └── SKILL.md                           │ │
│  └────────────────────────────────────────────────────┘ │
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │ Channels                                             │ │
│  │ - WhatsApp (primary)                                │ │
│  │ - LinkedIn (messages + HR)                           │ │
│  │ - Gmail (monitoring)                                │ │
│  │ - Telegram (secondary)                              │ │
│  │ - Slack (work integration)                           │ │
│  └────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────┘
           │
           ├── OpenClaw Database (PostgreSQL)
           │   ├── jobs
           │   ├── applications
           │   ├── conversations
           │   ├── contacts
           │   ├── stats
           │   └── schedule
           │
           ├── JobSearcher Legacy DB (SQLite - read-only)
           │   └── For migration verification
           │
           ├── Browser Control (Chrome CDP)
           ├── Google APIs
           └── LinkedIn APIs
```

---

## 📦 Skills a Crear (Modular)

### 1. **Core Skill** (`jobsearcher-core`)

**Propósito**: Configuración central y utilidades compartidas.

**Archivos**:
- `SKILL.md` - Documentación del skill
- `config.sh` - Variables de entorno y paths
- `setup.sh` - Instalación de dependencias
- `check_health.sh` - Verificar estado del sistema

**Funcionalidades**:
- Cargar configuración (search terms, locations, thresholds)
- Validar CV y datos personales
- Verificar conectividad con APIs
- Health check general

**Comandos expuestos**:
- `setup` - Configurar JobSearcher en OpenClaw
- `config` - Ver/editar configuración
- `health` - Estado general del sistema

**Migración desde**: Config actual (`.env`, `settings.py`)

---

### 2. **Job Search Skill** (`jobsearcher-search`)

**Propósito**: Búsqueda automática y manual de trabajos.

**Archivos**:
- `SKILL.md` - Documentación
- `search_jobs.sh` - Búsqueda manual de jobs
- `stalker_jobs.sh` - Búsqueda automática (crawling)
- `filter_jobs.sh` - Filtrar por ubicación/salario

**Funcionalidades**:
- Búsqueda por término + ubicación (JobSpy)
- Stalking de empresas específicas
- Filtrado por ubicación (México/Remote)
- Filtrado por salario (≥$50k MXN o ≥$2.5k USD)
- Guardado en base de datos

**Comandos expuestos**:
- `search <term> <location> [limit]` - Búsqueda manual
- `stalk <company> [days]` - Stalking de empresa
- `search-auto` - Búsqueda automática programada
- `stats-search` - Estadísticas de búsqueda

**Migración desde**: `src/tools/jobspy_tool.py`, `src/agents/job_stalker_agent.py`, `src/agents/company_stalker_agent.py`

---

### 3. **Evaluation Skill** (`jobsearcher-evaluation`)

**Propósito**: Evaluar match de jobs vs CV y generar cover letters.

**Archivos**:
- `SKILL.md` - Documentación
- `evaluate_match.sh` - Evaluar match de job
- `generate_cover_letter.sh` - Generar cover letter
- `analyze_email.sh` - Analizar respuesta de empresa

**Funcionalidades**:
- Evaluar job vs CV (score 0-100)
- Generar cover letters personalizadas
- Analizar respuestas de empresas (sentiment, action)
- Generar follow-up emails

**Comandos expuestos**:
- `evaluate <job_id>` - Evaluar match de un job
- `generate-letter <job_id>` - Generar cover letter
- `analyze-email <email_id>` - Analizar email de empresa
- `stats-evaluation` - Estadísticas de evaluación

**Migración desde**: `src/agents/master_agent.py`, `src/agents/recruiter_agent.py`

---

### 4. **Application Skill** (`jobsearcher-application`)

**Propósito**: Aplicar a trabajos (automático y manual).

**Archivos**:
- `SKILL.md` - Documentación
- `apply_easy.sh` - LinkedIn Easy Apply
- `apply_browser.sh` - Aplicar en portales externos
- `approve_jobs.sh` - Aprobar jobs para aplicación
- `status_application.sh` - Verificar estado de aplicación

**Funcionalidades**:
- Aplicar automáticamente (LinkedIn Easy Apply)
- Aplicar vía browser automation
- Track de aplicaciones pendientes
- Verificación de estado de aplicación

**Comandos expuestos**:
- `apply-all` - Aplicar a todos los jobs con score ≥75%
- `apply <job_id>` - Aplicar a job específico
- `approve <job_id>` - Aprobar job para aplicación
- `check-status <application_id>` - Verificar estado

**Migración desde**: `src/orchestrator.py` (apply logic), `src/tools/browser_tool.py`

---

### 5. **LinkedIn Skill** (`jobsearcher-linkedin`)

**Propósito**: Monitorear y responder mensajes de LinkedIn.

**Archivos**:
- `SKILL.md` - Documentación
- `check_messages.sh` - Leer mensajes no leídos
- `reply_recruiter.sh` - Responder a reclutador
- `connect_hr.sh` - Conectar con HR de empresas
- `history_conversation.sh` - Ver historial de conversación

**Funcionalidades**:
- Leer mensajes no leídos (GraphQL API)
- Analizar intención del reclutador
- Generar borrador de respuesta
- Enviar respuesta (con aprobación)
- Conectar con HR de empresas objetivo

**Comandos expuestos**:
- `check-messages` - Revisar mensajes no leídos
- `reply <conv_id> <message>` - Responder a conversación
- `connect <profile_url>` - Conectar con perfil
- `history <conv_id>` - Ver historial
- `stats-linkedin` - Estadísticas de LinkedIn

**Migración desde**: `src/tools/linkedin_messages_tool.py`, `src/agents/linkedin_hr_agent.py`

---

### 6. **Email Skill** (`jobsearcher-email`)

**Propósito**: Monitorear y responder emails de trabajo.

**Archivos**:
- `SKILL.md` - Documentación
- `monitor_emails.sh` - Revisar nuevos emails
- `send_email.sh` - Enviar email
- `analyze_response.sh` - Analizar respuesta de empresa

**Funcionalidades**:
- Monitorear Gmail para emails de trabajo
- Analizar intención del email (entrevista, oferta, rechazo)
- Generar respuestas automáticas (con aprobación)
- Enviar emails manuales
- Filtrar spam/no relevantes

**Comandos expuestos**:
- `monitor` - Revisar nuevos emails
- `send <to> <subject> <body>` - Enviar email
- `analyze <email_id>` - Analizar email
- `stats-email` - Estadísticas de emails

**Migración desde**: `src/tools/gmail_tool.py`, `src/agents/master_agent.py` (email analysis)

---

### 7. **Calendar Skill** (`jobsearcher-calendar`)

**Propósito**: Gestión de calendario para entrevistas.

**Archivos**:
- `SKILL.md` - Documentación
- `get_slots.sh` - Obtener slots disponibles
- `schedule_interview.sh` - Agendar entrevista
- `list_events.sh` - Listar eventos próximos

**Funcionalidades**:
- Obtener slots disponibles (L-V, 9-11am, 3-4pm CDMX)
- Crear eventos de entrevista
- Sincronizar con Google Calendar
- Notificar por WhatsApp/Telegram

**Comandos expuestos**:
- `slots [days]` - Mostrar slots disponibles
- `schedule <job_title> <company> <datetime>` - Agendar entrevista
- `events` - Listar eventos próximos

**Migración desde**: `src/tools/calendar_tool.py`

---

### 8. **Browser Skill** (`jobsearcher-browser`)

**Propósito**: Automatización de navegador para aplicar en portales.

**Archivos**:
- `SKILL.md` - Documentación
- `apply_to_portal.sh` - Aplicar en portal
- `fill_form.sh` - Llenar formulario
- `upload_cv.sh` - Subir CV

**Funcionalidades**:
- Navegar a URL de trabajo
- Llenar formularios automáticamente
- Subir CV
- Manejar CAPTCHA (escalar al usuario)
- Crear tareas pendientes si falla

**Comandos expuestos**:
- `apply-browser <url>` - Aplicar en portal
- `fill <url> <fields>` - Llenar formulario
- `upload <url> <cv_path>` - Subir CV

**Migración desde**: `src/tools/browser_tool.py`

---

### 9. **Tracker Skill** (`jobsearcher-tracker`)

**Propósito**: Persistencia y tracking de jobs, aplicaciones, conversaciones.

**Archivos**:
- `SKILL.md` - Documentación
- `get_stats.sh` - Estadísticas generales
- `list_jobs.sh` - Listar jobs por estado
- `update_status.sh` - Actualizar estado de job
- `export_data.sh` - Exportar datos

**Funcionalidades**:
- Guardar jobs encontrados
- Registrar aplicaciones
- Track conversaciones LinkedIn
- Generar estadísticas
- Exportar datos (CSV/JSON)

**Comandos expuestos**:
- `stats` - Estadísticas generales
- `jobs [status]` - Listar jobs por estado
- `applications [status]` - Listar aplicaciones
- `conversations [state]` - Listar conversaciones
- `export <format>` - Exportar datos

**Migración desde**: `src/db/tracker.py`

---

### 10. **Maintenance Skill** (`jobsearcher-maintenance`)

**Propósito**: Tareas de mantenimiento y limpieza.

**Archivos**:
- `SKILL.md` - Documentación
- `followup_applications.sh` - Follow-up a aplicaciones sin respuesta
- `cleanup_old_jobs.sh` - Limpiar jobs antiguos
- `update_resume.sh` - Actualizar CV

**Funcionalidades**:
- Follow-up automático (7 días sin respuesta)
- Limpiar jobs antiguos (>30 días)
- Actualizar CV en sistema
- Re-evaluar jobs pendientes

**Comandos expuestos**:
- `followup` - Follow-up a aplicaciones
- `cleanup` - Limpiar jobs antiguos
- `update-cv` - Actualizar CV

**Migración desde**: `src/orchestrator.py` (followup logic)

---

### 11. **Orchestrator Skill** (`jobsearcher-orchestrator`)

**Propósito**: Coordinación de skills y workflows automatizados.

**Archivos**:
- `SKILL.md` - Documentación
- `setup_workflow.sh` - Configurar workflow automatizado
- `run_workflow.sh` - Ejecutar workflow
- `pause_workflow.sh` - Pausar workflow

**Funcionalidades**:
- Configurar workflow completo (search → evaluate → apply → monitor)
- Ejecutar workflow automáticamente (crons)
- Pausar/reanudar workflows
- Notificar resultados

**Comandos expuestos**:
- `workflow-setup` - Configurar workflow
- `workflow-run` - Ejecutar workflow
- `workflow-pause` - Pausar workflow
- `workflow-status` - Estado del workflow

**Migración desde**: `src/orchestrator.py` (scheduling logic)

---

## 🗄️ Base de Datos OpenClaw

### Esquema Propuesto (PostgreSQL)

```sql
-- Jobs encontrados
CREATE TABLE jobs (
    id SERIAL PRIMARY KEY,
    job_id VARCHAR(255) UNIQUE NOT NULL,
    title VARCHAR(500) NOT NULL,
    company VARCHAR(255) NOT NULL,
    location VARCHAR(255),
    description TEXT,
    url VARCHAR(1000),
    source VARCHAR(50), -- linkedin, indeed, glassdoor
    easy_apply BOOLEAN DEFAULT FALSE,
    salary_min NUMERIC,
    salary_max NUMERIC,
    currency VARCHAR(10),
    match_score INTEGER, -- 0-100
    evaluation_notes TEXT,
    status VARCHAR(50) DEFAULT 'found', -- found, evaluated, approved, applied, rejected
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    date_posted DATE
);

-- Aplicaciones a jobs
CREATE TABLE applications (
    id SERIAL PRIMARY KEY,
    job_id VARCHAR(255) REFERENCES jobs(job_id),
    method VARCHAR(50), -- linkedin_easy_apply, browser_manual, browser_auto
    cover_letter TEXT,
    status VARCHAR(50) DEFAULT 'pending', -- pending, submitted, in_review, interview, offer, rejected
    applied_at TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT
);

-- Conversaciones LinkedIn
CREATE TABLE conversations (
    id SERIAL PRIMARY KEY,
    conversation_id VARCHAR(255) UNIQUE NOT NULL,
    participant_name VARCHAR(255),
    participant_title VARCHAR(500),
    participant_url VARCHAR(1000),
    last_message TEXT,
    last_message_at TIMESTAMP,
    state VARCHAR(50) DEFAULT 'new', -- new, read, responded, followup, closed
    intent VARCHAR(50), -- schedule, info, offer, rejection, general
    urgency VARCHAR(20), -- high, medium, low
    draft_response TEXT,
    needs_user_input BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Mensajes de conversación
CREATE TABLE messages (
    id SERIAL PRIMARY KEY,
    conversation_id VARCHAR(255) REFERENCES conversations(conversation_id),
    body TEXT NOT NULL,
    from_me BOOLEAN NOT NULL,
    sender_name VARCHAR(255),
    timestamp TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Respuestas del usuario
CREATE TABLE user_replies (
    id SERIAL PRIMARY KEY,
    conversation_id VARCHAR(255) REFERENCES conversations(conversation_id),
    reply_text TEXT NOT NULL,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Emails de trabajo
CREATE TABLE emails (
    id SERIAL PRIMARY KEY,
    email_id VARCHAR(255) UNIQUE NOT NULL,
    from_address VARCHAR(255),
    subject VARCHAR(500),
    content TEXT,
    date DATE,
    sentiment VARCHAR(50), -- positive, negative, interview, neutral
    action VARCHAR(50), -- schedule_interview, send_followup, none
    summary TEXT,
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Eventos de calendario
CREATE TABLE calendar_events (
    id SERIAL PRIMARY KEY,
    event_id VARCHAR(255) UNIQUE,
    job_title VARCHAR(500),
    company VARCHAR(255),
    start_datetime TIMESTAMP NOT NULL,
    end_datetime TIMESTAMP NOT NULL,
    duration_minutes INTEGER,
    location VARCHAR(500),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Estadísticas agregadas
CREATE TABLE stats (
    id SERIAL PRIMARY KEY,
    date DATE UNIQUE,
    jobs_found INTEGER DEFAULT 0,
    jobs_evaluated INTEGER DEFAULT 0,
    jobs_applied INTEGER DEFAULT 0,
    emails_received INTEGER DEFAULT 0,
    conversations_created INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Índices para performance
CREATE INDEX idx_jobs_status ON jobs(status);
CREATE INDEX idx_jobs_match_score ON jobs(match_score);
CREATE INDEX idx_jobs_created_at ON jobs(created_at);
CREATE INDEX idx_applications_status ON applications(status);
CREATE INDEX idx_conversations_state ON conversations(state);
CREATE INDEX idx_messages_conversation ON messages(conversation_id);
CREATE INDEX idx_emails_date ON emails(date);
```

### Scripts de Migración

**1. Migrar Jobs desde SQLite a PostgreSQL** (`migrate_jobs.sh`):
```bash
#!/bin/bash
# Migración de jobs desde SQLite a PostgreSQL
# Lee desde SQLite jobsearcher.db
# Inserta en PostgreSQL OpenClaw
# Genera reporte de migración

DB_PATH="data/jobsearcher.db"
PG_DB="openclaw"
PG_USER="jobsearcher"

echo "🔄 Migrando jobs desde SQLite a PostgreSQL..."

# Extraer datos de SQLite
sqlite3 "$DB_PATH" "SELECT * FROM jobs;" > /tmp/jobs_export.csv

# Importar a PostgreSQL
psql -U "$PG_USER" -d "$PG_DB" -c "\COPY jobs FROM '/tmp/jobs_export.csv' CSV HEADER"

# Generar reporte
JOB_COUNT=$(psql -U "$PG_USER" -d "$PG_DB" -t -c "SELECT COUNT(*) FROM jobs;")
echo "✅ Migración completada: $JOB_COUNT jobs migrados"
```

**2. Migrar Aplicaciones** (`migrate_applications.sh`):
```bash
#!/bin/bash
# Migrar tabla applications
# Mapear status a nuevo esquema
# Validar referencias a jobs

DB_PATH="data/jobsearcher.db"
PG_DB="openclaw"
PG_USER="jobsearcher"

echo "🔄 Migrando aplicaciones..."

sqlite3 "$DB_PATH" "SELECT * FROM applications;" > /tmp/applications_export.csv

psql -U "$PG_USER" -d "$PG_DB" -c "\COPY applications FROM '/tmp/applications_export.csv' CSV HEADER"

APP_COUNT=$(psql -U "$PG_USER" -d "$PG_DB" -t -c "SELECT COUNT(*) FROM applications;")
echo "✅ Migración completada: $APP_COUNT aplicaciones migradas"
```

**3. Migrar Conversaciones** (`migrate_conversations.sh`):
```bash
#!/bin/bash
# Migrar tabla conversations
# Migrar tabla messages
# Reconstruir historial

DB_PATH="data/jobsearcher.db"
PG_DB="openclaw"
PG_USER="jobsearcher"

echo "🔄 Migrando conversaciones..."

sqlite3 "$DB_PATH" "SELECT * FROM conversations;" > /tmp/conversations_export.csv
sqlite3 "$DB_PATH" "SELECT * FROM messages;" > /tmp/messages_export.csv

psql -U "$PG_USER" -d "$PG_DB" -c "\COPY conversations FROM '/tmp/conversations_export.csv' CSV HEADER"
psql -U "$PG_USER" -d "$PG_DB" -c "\COPY messages FROM '/tmp/messages_export.csv' CSV HEADER"

CONV_COUNT=$(psql -U "$PG_USER" -d "$PG_DB" -t -c "SELECT COUNT(*) FROM conversations;")
MSG_COUNT=$(psql -U "$PG_USER" -d "$PG_DB" -t -c "SELECT COUNT(*) FROM messages;")
echo "✅ Migración completada: $CONV_COUNT conversaciones, $MSG_COUNT mensajes"
```

**4. Migrar Emails** (`migrate_emails.sh`):
```bash
#!/bin/bash
# Migrar emails procesados
# Mapear a nuevo esquema
# Generar estadísticas

DB_PATH="data/jobsearcher.db"
PG_DB="openclaw"
PG_USER="jobsearcher"

echo "🔄 Migrando emails..."

sqlite3 "$DB_PATH" "SELECT * FROM emails;" > /tmp/emails_export.csv

psql -U "$PG_USER" -d "$PG_DB" -c "\COPY emails FROM '/tmp/emails_export.csv' CSV HEADER"

EMAIL_COUNT=$(psql -U "$PG_USER" -d "$PG_DB" -t -c "SELECT COUNT(*) FROM emails;")
echo "✅ Migración completada: $EMAIL_COUNT emails migrados"
```

---

## 🔄 Workflow Automatizado

### Flujo Principal (OpenClaw Cron)

```json
{
  "automation": {
    "cronJobs": [
      {
        "id": "job-search",
        "cron": "0 */6 * * *",
        "command": "jobsearcher-search:search-auto --limit=30",
        "enabled": true,
        "description": "Buscar trabajos cada 6 horas"
      },
      {
        "id": "job-evaluate",
        "cron": "30 */6 * * *",
        "command": "jobsearcher-evaluation:evaluate-new --threshold=75",
        "enabled": true,
        "description": "Evaluar nuevos jobs 30min después de búsqueda"
      },
      {
        "id": "job-notify",
        "cron": "45 */6 * * *",
        "command": "jobsearcher-application:notify-high-scorers",
        "enabled": true,
        "description": "Notificar jobs de alta calidad"
      },
      {
        "id": "linkedin-messages",
        "cron": "*/15 * * * *",
        "command": "jobsearcher-linkedin:check-messages",
        "enabled": true,
        "description": "Monitorear LinkedIn messages cada 15min"
      },
      {
        "id": "email-monitor",
        "cron": "*/30 * * * *",
        "command": "jobsearcher-email:monitor",
        "enabled": true,
        "description": "Monitorear emails cada 30min"
      },
      {
        "id": "followup",
        "cron": "0 9 * * *",
        "command": "jobsearcher-maintenance:followup --days=7",
        "enabled": true,
        "description": "Follow-up a aplicaciones sin respuesta (diario 9am)"
      },
      {
        "id": "cleanup",
        "cron": "0 2 * * 0",
        "command": "jobsearcher-maintenance:cleanup --days=30",
        "enabled": true,
        "description": "Cleanup de jobs antiguos (semanal domingo 2am)"
      }
    ]
  }
}
```

---

## 📅 Timeline de Migración

### Fase 1: Preparación (1-2 días)

**Objetivo**: Configurar infraestructura de OpenClaw.

**Tasks**:
- [ ] Instalar OpenClaw (`npm install -g openclaw@latest`)
- [ ] Ejecutar `openclaw onboard --install-daemon`
- [ ] Configurar Gateway WebSocket (puerto 18789)
- [ ] Crear base de datos PostgreSQL
- [ ] Instalar dependencias Python para scripts
- [ ] Configurar variables de entorno

**Archivos a crear**:
- `.env.openclaw` - Variables de entorno para OpenClaw
- `setup_postgresql.sh` - Script de configuración de DB
- `install_dependencies.sh` - Instalación de dependencias Python

**Verificación**:
- [ ] Gateway corriendo en puerto 18789
- [ ] PostgreSQL accesible
- [ ] Python scripts ejecutables desde skills

---

### Fase 2: Migración de Datos (1 día)

**Objetivo**: Migrar datos históricos a nueva DB.

**Tasks**:
- [ ] Crear esquema PostgreSQL (ejecutar SQL de esquema)
- [ ] Migrar tabla `jobs` (854 jobs)
- [ ] Migrar tabla `applications` (201 aplicaciones)
- [ ] Migrar tabla `conversations` (LinkedIn messages)
- [ ] Migrar tabla `messages` (historial de conversaciones)
- [ ] Migrar emails procesados
- [ ] Validar migración (comparar counts)
- [ ] Archivar SQLite como backup (read-only)

**Archivos a crear**:
- `data/migration/migrate_jobs.sh`
- `data/migration/migrate_applications.sh`
- `data/migration/migrate_conversations.sh`
- `data/migration/migrate_emails.sh`
- `data/migration/validate_migration.sh`

**Verificación**:
```bash
# Comparar counts
sqlite3 data/jobsearcher.db "SELECT COUNT(*) FROM jobs;"
psql -d openclaw -c "SELECT COUNT(*) FROM jobs;"
```

---

### Fase 3: Skills Core + Search (2-3 días)

**Objetivo**: Skills básicos para búsqueda de jobs.

**Tasks**:

**Skill: jobsearcher-core**
- [ ] Crear directorio `~/.openclaw/workspace/skills/jobsearcher-core/`
- [ ] Crear `SKILL.md` con documentación
- [ ] Crear `config.sh` con variables de entorno
- [ ] Crear `setup.sh` para instalación
- [ ] Crear `check_health.sh` para health checks

**Skill: jobsearcher-search**
- [ ] Crear directorio `~/.openclaw/workspace/skills/jobsearcher-search/`
- [ ] Migrar `jobspy_tool.py` → `search_jobs.sh`
- [ ] Migrar `job_stalker_agent.py` → `stalker_jobs.sh`
- [ ] Integrar con DB PostgreSQL
- [ ] Testing manual de búsqueda

**Skill: jobsearcher-tracker**
- [ ] Crear directorio `~/.openclaw/workspace/skills/jobsearcher-tracker/`
- [ ] Migrar `tracker.py` → shell scripts
- [ ] Implementar queries PostgreSQL
- [ ] Implementar export CSV/JSON

**Verificación**:
- [ ] Buscar jobs manualmente
- [ ] Listar jobs por estado
- [ ] Exportar datos
- [ ] Health check pasa

---

### Fase 4: Skills de Evaluación (2 días)

**Objetivo**: Evaluar match y generar contenido.

**Tasks**:

**Skill: jobsearcher-evaluation**
- [ ] Crear directorio `~/.openclaw/workspace/skills/jobsearcher-evaluation/`
- [ ] Migrar `master_agent.py` (evaluate_match) → `evaluate_match.sh`
- [ ] Migrar `master_agent.py` (generate_cover_letter) → `generate_cover_letter.sh`
- [ ] Migrar `master_agent.py` (analyze_email) → `analyze_email.sh`
- [ ] Integrar LLM (GLM-4/Groq/SambaNova)
- [ ] Testing de evaluación con jobs reales
- [ ] Validar scoring vs histórico

**Verificación**:
- [ ] Evaluar 10 jobs existentes
- [ ] Scores consistentes (±5%) con histórico
- [ ] Generar cover letter para job de prueba
- [ ] Analizar email de prueba

---

### Fase 5: Skills de LinkedIn + Email (3-4 días)

**Objetivo**: Automatizar comunicación.

**Tasks**:

**Skill: jobsearcher-linkedin**
- [ ] Crear directorio `~/.openclaw/workspace/skills/jobsearcher-linkedin/`
- [ ] Migrar `linkedin_messages_tool.py` → `check_messages.sh`
- [ ] Migrar `recruiter_agent.py` → `reply_recruiter.sh`
- [ ] Migrar `linkedin_hr_agent.py` → `connect_hr.sh`
- [ ] Implementar análisis de mensajes
- [ ] Implementar generación de borradores

**Skill: jobsearcher-email**
- [ ] Crear directorio `~/.openclaw/workspace/skills/jobsearcher-email/`
- [ ] Migrar `gmail_tool.py` → `monitor_emails.sh`
- [ ] Integrar Gmail Pub/Sub (OpenClaw native)
- [ ] Implementar análisis de emails

**Configurar canales de comunicación**:
- [ ] Configurar WhatsApp (OpenClaw channel)
- [ ] Configurar LinkedIn (tool custom)
- [ ] Configurar Gmail (tool custom)
- [ ] Testing de notificaciones
- [ ] Testing de respuestas

**Verificación**:
- [ ] Recibir notificación por WhatsApp
- [ ] Leer mensajes de LinkedIn
- [ ] Monitorear emails
- [ ] Enviar respuesta a reclutador

---

### Fase 6: Skills de Aplicación + Browser (2-3 días)

**Objetivo**: Aplicar a trabajos automáticamente.

**Tasks**:

**Skill: jobsearcher-application**
- [ ] Crear directorio `~/.openclaw/workspace/skills/jobsearcher-application/`
- [ ] Migrar lógica de apply desde `orchestrator.py`
- [ ] Implementar aprobar/rechazar jobs
- [ ] Implementar track de aplicaciones

**Skill: jobsearcher-browser**
- [ ] Crear directorio `~/.openclaw/workspace/skills/jobsearcher-browser/`
- [ ] Migrar `browser_tool.py` → `apply_to_portal.sh`
- [ ] Usar OpenClaw browser tool
- [ ] Implementar manejo de CAPTCHA
- [ ] Crear tareas pendientes si falla

**Skill: jobsearcher-calendar**
- [ ] Crear directorio `~/.openclaw/workspace/skills/jobsearcher-calendar/`
- [ ] Migrar `calendar_tool.py` → `get_slots.sh`, `schedule_interview.sh`
- [ ] Integrar Google Calendar API

**Verificación**:
- [ ] Aplicar a job de prueba (Easy Apply)
- [ ] Aplicar a job de prueba (Browser)
- [ ] Obtener slots disponibles
- [ ] Agendar entrevista de prueba

---

### Fase 7: Skills de Mantenimiento + Orchestrator (1-2 días)

**Objetivo**: Tareas de mantenimiento y workflows.

**Tasks**:

**Skill: jobsearcher-maintenance**
- [ ] Crear directorio `~/.openclaw/workspace/skills/jobsearcher-maintenance/`
- [ ] Migrar followup logic → `followup_applications.sh`
- [ ] Implementar cleanup → `cleanup_old_jobs.sh`
- [ ] Implementar update CV → `update_resume.sh`

**Skill: jobsearcher-orchestrator**
- [ ] Crear directorio `~/.openclaw/workspace/skills/jobsearcher-orchestrator/`
- [ ] Configurar workflows → `setup_workflow.sh`
- [ ] Setup de crons
- [ ] Implementar coordinación entre skills

**Verificación**:
- [ ] Ejecutar follow-up a aplicaciones
- [ ] Limpiar jobs antiguos
- [ ] Ejecutar workflow completo
- [ ] Cron jobs funcionando

---

### Fase 8: Canales Adicionales (2-3 días)

**Objetivo**: Expandir a más canales de comunicación.

**Tasks**:
- [ ] Configurar Telegram channel (OpenClaw native)
- [ ] Configurar Slack channel (OpenClaw native)
- [ ] Adaptar notificaciones para múltiples canales
- [ ] Testing multi-channel
- [ ] Documentar configuración de canales

**Verificación**:
- [ ] Recibir notificación por Telegram
- [ ] Recibir notificación por Slack
- [ ] Enviar comando desde Telegram
- [ ] Enviar comando desde Slack

---

### Fase 9: Integración + Testing Final (3-4 días)

**Objetivo**: Integrar todo el sistema y testing completo.

**Tasks**:

**Testing end-to-end**:
- [ ] Buscar jobs → Evaluar → Notificar → Aplicar → Monitorear
- [ ] Testear con jobs reales (5-10 jobs)
- [ ] Testear con conversaciones reales de LinkedIn
- [ ] Testear con emails reales

**Testing de failover**:
- [ ] Simular LLM down → Verify fallback
- [ ] Simular API down → Verify retry logic
- [ ] Simular DB down → Verify error handling

**Performance testing**:
- [ ] Medir tiempos de búsqueda
- [ ] Medir tiempos de evaluación
- [ ] Medir tiempos de aplicación
- [ ] Optimizar si es necesario

**Documentation**:
- [ ] Update AGENTS.md para JobSearcher skills
- [ ] Crear guía de usuario (comandos OpenClaw)
- [ ] Crear guía de troubleshooting
- [ ] Update README.md

**User training**:
- [ ] Capacitar en comandos de OpenClaw
- [ ] Capacitar en configuración de skills
- [ ] Capacitar en troubleshooting básico

**Cutover gradual**:
- [ ] Día 1-3: Paralelo (ambos sistemas corriendo)
- [ ] Día 4: Solo lectura en JobSearcher
- [ ] Día 5: Deshabilitar JobSearcher
- [ ] Día 7: Borrar JobSearcher (luego de confirmación)

**Verificación**:
- [ ] Workflow completo funciona sin errores
- [ ] Failover funciona correctamente
- [ ] Performance aceptable (<30s para evaluación)
- [ ] Usuario capacitado y cómodo con OpenClaw

---

### Fase 10: Optimización + Documentación (1-2 días)

**Objetivo**: Optimizar performance y documentar.

**Tasks**:

**Optimización**:
- [ ] Optimizar queries PostgreSQL
- [ ] Implementar caching de evaluaciones
- [ ] Agregar logging detallado
- [ ] Implementar métricas de performance

**Documentation adicional**:
- [ ] Crear scripts de backup/restore DB
- [ ] Crear guía de actualización de skills
- [ ] Crear guía de debugging
- [ ] Documentar configuración de OAuth

**Cleanup**:
- [ ] Archivar código de JobSearcher en `legacy/`
- [ ] Borrar archivos temporales
- [ ] Limpiar logs antiguos

**Verificación**:
- [ ] Backup automatizado funciona
- [ ] Restore automatizado funciona
- [ ] Documentation completa
- [ ] Sistema limpio y organizado

---

## 🛠️ Consideraciones Técnicas

### 1. Comunicación con LLMs

**Actual**: `coordinator.py` enruta a GLM-4/Groq/SambaNova.

**OpenClaw**: Usar `agent.model` configuración nativa.

```json
{
  "agent": {
    "model": "anthropic/claude-opus-4-6",
    "modelFailover": [
      "openai/gpt-4-turbo",
      "zhipu/glm-4-plus",
      "groq/llama-3.3-70b-versatile"
    ]
  }
}
```

**Migración**:
- Eliminar `coordinator.py`
- Configurar modelo en `~/.openclaw/openclaw.json`
- Usar comandos OpenClaw para invocar LLM

---

### 2. Cron Jobs vs APScheduler

**Actual**: APScheduler en `orchestrator.py`.

**OpenClaw**: Cron jobs nativos (`automation.cron-jobs` en config).

**Migración**:
```json
{
  "automation": {
    "cronJobs": [
      {
        "id": "job-search",
        "cron": "0 */6 * * *",
        "command": "jobsearcher-search:search-auto --limit=30",
        "enabled": true
      }
    ]
  }
}
```

**Beneficios**:
- Nativos de OpenClaw
- Gestión centralizada
- Integración con logs
- UI de gestión

---

### 3. Webhooks (WhatsApp)

**Actual**: `/webhook/whatsapp` en FastAPI + Node.js bridge.

**OpenClaw**: Channel nativo de WhatsApp.

**Configuración**:
```bash
# Configurar canal WhatsApp en OpenClaw
openclaw channel add whatsapp --webhook-secret <secret>
```

**Migración**:
- Eliminar bridge Node.js
- Usar channel nativo
- Configurar webhook URL
- Validar autenticación

---

### 4. Browser Automation

**Actual**: Playwright en `browser_tool.py`.

**OpenClaw**: Browser tool nativo.

**Migración**:
```bash
# Usar browser tool nativo de OpenClaw
openclaw browser navigate --url "https://linkedin.com/jobs/123"
openclaw browser fill --selector "input[name='email']" --value "alejandrohloza@gmail.com"
openclaw browser click --selector "button[type='submit']"
```

**Beneficios**:
- Nativo de OpenClaw
- Integrado con Canvas
- Gestión de perfiles
- Snapshots automáticos

---

### 5. Database Access

**Actual**: SQLite con `tracker.py`.

**OpenClaw**: Scripts bash + `psql` commands.

**Migración**:
- Scripts Python → Scripts bash + psql
- Queries SQL directas
- Manejo de errores en shell
- Logging nativo de OpenClaw

**Ejemplo**:
```bash
#!/bin/bash
# ~/.openclaw/workspace/skills/jobsearcher-tracker/list_jobs.sh

PG_DB="openclaw"
STATUS=${1:-"found"}

psql -d "$PG_DB" -c "
  SELECT title, company, location, match_score, created_at
  FROM jobs
  WHERE status = '$STATUS'
  ORDER BY created_at DESC
  LIMIT 20;
"
```

---

### 6. File Storage

**Actual**: `data/` directory (CV, screenshots, logs).

**OpenClaw**: `~/.openclaw/workspace/data/jobsearcher/`.

**Migración**:
- Mover CV a nuevo directorio
- Mover screenshots a nuevo directorio
- Configurar paths en scripts
- Actualizar documentación

**Estructura**:
```
~/.openclaw/workspace/data/jobsearcher/
├── cv/
│   └── cv_english.pdf
├── screenshots/
├── logs/
└── cache/
```

---

### 7. Logging

**Actual**: Loguru en `orchestrator.py`.

**OpenClaw**: Logging nativo del Gateway.

**Migración**:
- Eliminar configuración de Loguru
- Usar logging nativo de OpenClaw
- Configurar nivel de logging en config
- Acceder logs vía Control UI

---

## 📊 Beneficios de la Migración

### Ventajas sobre JobSearcher actual:

1. **Multi-channel nativo**
   - WhatsApp, Telegram, Slack, Discord, etc.
   - Sin bridges personalizados
   - Configuración centralizada

2. **Skills modulares**
   - Cada agente es un skill independiente
   - Fácil de mantener/actualizar
   - Reutilizable en otros proyectos

3. **Cron jobs nativos**
   - No depende de APScheduler
   - Gestión centralizada
   - UI de gestión

4. **Browser tool nativo**
   - Playwright integrado
   - Canvas integration
   - Perfiles de navegador

5. **Model failover**
   - Routing automático entre LLMs
   - Configuración simple
   - Health checks automáticos

6. **Control UI**
   - Dashboard web nativo
   - Gestión de skills
   - Logs en tiempo real

7. **Companion apps**
   - iOS/Android para notificaciones push
   - Voice wake
   - Canvas mobile

8. **Canvas**
   - Visual workspace
   - A2UI agent-driven
   - Snapshots

9. **Tailscale**
   - Acceso remoto seguro
   - Serve/Funnel
   - SSH tunnels

10. **Security defaults**
    - DM pairing
    - Sandbox mode
    - Allowlists

---

### Riesgos:

1. **Curva de aprendizaje**
   - Nueva plataforma a aprender
   - Diferente paradigma (bash scripts vs Python)
   - Documentación menos madura

2. **Dependencia de OpenClaw**
   - Updates pueden romper compatibilidad
   - Bugs en OpenClaw afectan JobSearcher
   - Menos control sobre bugs

3. **Complexidad**
   - Más componentes a configurar
   - Más archivos a mantener
   - Debugging más difícil

4. **Python vs Shell**
   - Scripts bash menos expresivos que Python
   - Manejo de errores más complejo
   - Testing más difícil

---

## 🎯 Próximos Pasos (Inmediatos)

### 1. Validar que OpenClaw soporta los requerimientos

- [ ] ¿Soporta Python scripts como skills? → Revisar docs
- [ ] ¿Cómo integrar dependencias Python (JobSpy, Gmail API)? → Investigar
- [ ] ¿Cómo persistir datos (PostgreSQL vs SQLite)? → Decidir
- [ ] ¿Cómo ejecutar scripts Python desde OpenClaw? → Probar

### 2. Proof of Concept (PoC) (1 día)

**Objetivo**: Validar viabilidad del enfoque.

**Tasks**:
- [ ] Instalar OpenClaw
- [ ] Crear skill simple `jobsearcher-poc`
- [ ] Migrar solo `jobspy_tool.py` → `search_jobs.sh`
- [ ] Testear búsqueda de jobs
- [ ] Evaluar viabilidad del enfoque

**Criterios de éxito**:
- [ ] Skill funciona correctamente
- [ ] Búsqueda de jobs funciona
- [ ] Datos se guardan en DB
- [ ] Comandos se ejecutan sin errores

**Decision**:
- Si PoC exitoso → Continuar migración
- Si PoC falla → Reconsiderar enfoque o ajustar plan

---

### 3. Aprobación de Plan

**Tasks**:
- [ ] Revisar este plan con el usuario
- [ ] Ajustar prioridades/timeline según feedback
- [ ] Confirmar recursos disponibles
- [ ] Definir fecha de inicio
- [ ] Definir hitos críticos

---

### 4. Ejecución de Fase 1 (Preparación)

**Tasks**:
- [ ] Instalar OpenClaw
- [ ] Configurar Gateway
- [ ] Crear DB PostgreSQL
- [ ] Instalar dependencias
- [ ] Configurar variables de entorno

**Verificación**:
- [ ] Gateway corriendo en puerto 18789
- [ ] PostgreSQL accesible
- [ ] Dependencias instaladas
- [ ] Variables de entorno configuradas

---

## 📝 Archivos a Crear

### Estructura de Skills

```
~/.openclaw/workspace/skills/jobsearcher-core/
├── SKILL.md
├── config.sh
├── setup.sh
└── check_health.sh

~/.openclaw/workspace/skills/jobsearcher-search/
├── SKILL.md
├── search_jobs.sh
├── stalker_jobs.sh
└── filter_jobs.sh

~/.openclaw/workspace/skills/jobsearcher-evaluation/
├── SKILL.md
├── evaluate_match.sh
├── generate_cover_letter.sh
└── analyze_email.sh

~/.openclaw/workspace/skills/jobsearcher-application/
├── SKILL.md
├── apply_easy.sh
├── apply_browser.sh
└── approve_jobs.sh

~/.openclaw/workspace/skills/jobsearcher-linkedin/
├── SKILL.md
├── check_messages.sh
├── reply_recruiter.sh
└── connect_hr.sh

~/.openclaw/workspace/skills/jobsearcher-email/
├── SKILL.md
├── monitor_emails.sh
└── send_email.sh

~/.openclaw/workspace/skills/jobsearcher-calendar/
├── SKILL.md
├── get_slots.sh
└── schedule_interview.sh

~/.openclaw/workspace/skills/jobsearcher-browser/
├── SKILL.md
├── apply_to_portal.sh
└── fill_form.sh

~/.openclaw/workspace/skills/jobsearcher-tracker/
├── SKILL.md
├── get_stats.sh
├── list_jobs.sh
└── update_status.sh

~/.openclaw/workspace/skills/jobsearcher-maintenance/
├── SKILL.md
├── followup_applications.sh
└── cleanup_old_jobs.sh

~/.openclaw/workspace/skills/jobsearcher-orchestrator/
├── SKILL.md
├── setup_workflow.sh
└── run_workflow.sh
```

### Scripts de Migración

```
data/migration/
├── migrate_jobs.sh
├── migrate_applications.sh
├── migrate_conversations.sh
├── migrate_emails.sh
├── validate_migration.sh
└── README.md
```

### Documentación

```
docs/
├── OPENCLAW_MIGRATION.md (este archivo)
├── JOBSEARCHER_SKILLS_GUIDE.md
├── TROUBLESHOOTING.md
└── USER_GUIDE.md
```

### Scripts de Setup

```
scripts/
├── setup_openclaw.sh
├── setup_postgresql.sh
├── install_dependencies.sh
└── backup_jobsearcher.sh
```

---

## ❓ Preguntas Pendientes

### 1. Base de datos

**Pregunta**: ¿PostgreSQL o mantener SQLite en OpenClaw?

**Opciones**:
- **PostgreSQL**:
  - ✅ Más robusto y escalable
  - ✅ Soporta concurrencia
  - ✅ Mejor performance para queries complejos
  - ❌ Requiere configuración adicional
  - ❌ Más complejo de setup

- **SQLite**:
  - ✅ Más simple
  - ✅ No requiere servidor
  - ✅ Fácil de backup
  - ❌ Problemas de concurrencia
  - ❌ Menos escalable

**Recomendación**: PostgreSQL (dado que OpenClaw ya usa PostgreSQL)

---

### 2. Python vs Node.js

**Pregunta**: ¿Mantener scripts Python o reescribir en Node.js?

**Opciones**:
- **Python scripts en OpenClaw skills**:
  - ✅ Reutilizar código existente
  - ✅ Menos reescritura
  - ✅ Lógica de negocio probada
  - ❌ Menos documentado en OpenClaw
  - ❌ Dependencias Python en skills

- **Node.js scripts**:
  - ✅ Nativo en OpenClaw
  - ✅ Mejor integración
  - ✅ Más documentación
  - ❌ Reescribir todo
  - ❌ Más tiempo inicial

**Recomendación**: Python scripts (reutilizar código existente, menos riesgo)

---

### 3. Deployment

**Pregunta**: ¿Dónde correr el Gateway?

**Opciones**:
- **Local (laptop actual)**:
  - ✅ Simple de setup
  - ✅ Sin costos adicionales
  - ❌ Requiere máquina encendida
  - ❌ No accesible cuando apagado

- **Servidor Linux**:
  - ✅ Siempre encendido
  - ✅ Más robusto
  - ✅ Accesible remotamente
  - ❌ Requiere servidor
  - ❌ Costos de servidor
  - ❌ Setup más complejo

**Recomendación**: Local inicialmente, migrar a servidor si es necesario

---

### 4. Backup de JobSearcher

**Pregunta**: ¿Archivar o eliminar?

**Opciones**:
- **Archivar como backup por 30 días**:
  - ✅ Fácil de rollback
  - ✅ Datos accesibles
  - ❌ Espacio en disco

- **Eliminar inmediatamente**:
  - ✅ Limpieza inmediata
  - ❌ Riesgo de perder datos
  - ❌ Difficult rollback

**Recomendación**: Archivar 30 días, luego de confirmación eliminar

---

## ✅ Checklist de Aprobación

Antes de comenzar la migración:

- [ ] Usuario ha revisado y aprobado este plan
- [ ] Timeline realista según disponibilidad de usuario
- [ ] Recursos disponibles (máquina, tiempo, dependencias)
- [ ] Plan de rollback en caso de problemas
- [ ] Backup completo de JobSearcher (DB + código)
- [ ] Punto de contacto para soporte de OpenClaw (Discord/docs)
- [ ] PoC completado exitosamente
- [ ] Decisiones tomadas (DB, lenguaje, deployment)
- [ ] Fecha de inicio confirmada
- [ ] Responsabilidades asignadas

---

## 📚 Recursos

### Documentación de OpenClaw

- [OpenClaw Docs](https://docs.openclaw.ai)
- [Getting Started](https://docs.openclaw.ai/start/getting-started)
- [Skills](https://docs.openclaw.ai/tools/skills)
- [Channels](https://docs.openclaw.ai/channels)
- [Automation](https://docs.openclaw.ai/automation)
- [OpenClaw GitHub](https://github.com/openclaw/openclaw)
- [Discord](https://discord.gg/clawd)

### Documentación de JobSearcher

- [CLAUDE.md](../CLAUDE.md) - Guía completa para agentes
- [README.md](../README.md) - Documentación del proyecto
- [requirements.txt](../requirements.txt) - Dependencias Python

---

## 📞 Soporte

### En caso de problemas:

1. **OpenClaw issues**: GitHub issues o Discord
2. **Migration issues**: Consultar `TROUBLESHOOTING.md`
3. **Bug reports**: Crear issue en repo de JobSearcher
4. **Urgente**: WhatsApp o Telegram directo

---

## 📈 Métricas de Éxito

La migración será considerada exitosa si:

- [ ] Todos los jobs históricos migrados sin pérdida de datos
- [ ] Workflow completo funciona sin errores
- [ ] Performance igual o mejor que JobSearcher actual
- [ ] Usuario capacitado y cómodo con OpenClaw
- [ ] 0 bugs críticos en producción por 7 días
- [ ] Canales de comunicación funcionando correctamente
- [ ] Cron jobs ejecutándose según schedule
- [ ] JobSearcher legacy eliminado sin problemas

---

## 🔄 Version History

- **v1.0** (2026-04-06): Plan inicial de migración
  - Definición de arquitectura
  - 11 skills identificados
  - 10 fases de migración
  - Timeline de 15-20 días

---

## 📄 Licencia

Este plan es parte del proyecto JobSearcher y sigue la misma licencia.

---

**Plan creado**: Abril 6, 2026
**Autor**: Sistema JobSearcher AI
**Estado**: Pendiente de aprobación
