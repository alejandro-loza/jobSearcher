# JobSearcher — Guía completa para agentes

## Sistema
Agente autónomo de búsqueda de empleo para **Alejandro Hernandez Loza**.
Busca jobs, aplica, responde reclutadores en LinkedIn, agenda entrevistas,
monitorea emails, y notifica por WhatsApp.

**Directorio**: `/data/projects/proyects/jobSearcher`
**Venv**: `venv/bin/python`
**DB**: `data/jobsearcher.db` (SQLite)
**CV**: `data/resume.json`

---

## Al iniciar sesión
1. `cd /data/projects/proyects/jobSearcher`
2. Revisa `data/pending_browser_tasks.json` — si hay tareas `"status": "pending"`, ejecútalas
3. Verifica el orchestrator: `curl -s http://localhost:8777/health | python3 -m json.tool`
4. Si el orchestrator no corre: `venv/bin/python run.py` (puerto 8777)

---

## Arquitectura

### Componentes principales
| Componente | Archivo | Descripción |
|---|---|---|
| Orchestrator | `src/orchestrator.py` | FastAPI + APScheduler, webhook WhatsApp |
| Master Agent | `src/agents/master_agent.py` | Evalúa jobs, genera cover letters, analiza emails |
| Recruiter Agent | `src/agents/recruiter_agent.py` | Habla con reclutadores en LinkedIn |
| Coordinator | `src/agents/coordinator.py` | Enruta tareas al LLM óptimo (GLM-4/Groq/SambaNova) |
| JobSpy Tool | `src/tools/jobspy_tool.py` | Búsqueda de jobs (LinkedIn, Indeed, Glassdoor) |
| LinkedIn Tool | `src/tools/linkedin_messages_tool.py` | Mensajes LinkedIn (GraphQL + Playwright) |
| Gmail Tool | `src/tools/gmail_tool.py` | Lee/envía emails de trabajo |
| Calendar Tool | `src/tools/calendar_tool.py` | Google Calendar (slots, crear eventos) |
| WhatsApp Tool | `src/tools/whatsapp_tool.py` | Envía mensajes via bridge Node.js |
| Browser Tool | `src/tools/browser_tool.py` | Playwright + vision LLM para llenar forms |
| DB Tracker | `src/db/tracker.py` | SQLite: jobs, applications, emails, conversations |

### Scheduled Tasks (APScheduler)
- `job_search`: cada 6h — busca jobs con JobSpy
- `linkedin_messages`: cada 15min — lee mensajes de reclutadores
- `email_monitor`: cada 30min — revisa Gmail
- `followup`: 9am diario — follow-up a aplicaciones sin respuesta

---

## Herramientas — Cómo usarlas

### 1. Buscar trabajos (JobSpy)
```bash
venv/bin/python -c "
from src.tools import jobspy_tool
import json

# Búsqueda básica
jobs = jobspy_tool.search_jobs(
    search_term='Senior Java Developer',
    location='remote',
    results_wanted=15,       # cuántos resultados
    hours_old=168,           # últimas 168h = 7 días
    site_names=['linkedin', 'indeed', 'glassdoor'],  # opcionales
    easy_apply_only=False,   # True = solo LinkedIn Easy Apply
)

for j in jobs:
    print(f\"{j['title']} @ {j['company']} | {j['location']} | score={j.get('match_score','?')}\")
    print(f\"  URL: {j.get('url','N/A')}\")
    print(f\"  Easy Apply: {j.get('easy_apply', False)}\")
    print()
"
```

**Parámetros de `search_jobs()`**:
- `search_term` (str): Término de búsqueda. Ej: "Java Spring Boot", "Senior Backend Engineer"
- `location` (str): "remote", "Ciudad de Mexico", "Mexico City", etc.
- `results_wanted` (int): Máximo de resultados (default 15)
- `hours_old` (int): Edad máxima del posting en horas (168 = 7 días)
- `site_names` (list): `['linkedin', 'indeed', 'glassdoor']` — por defecto todos
- `easy_apply_only` (bool): Solo LinkedIn Easy Apply

**Cada job retorna**: `id, title, company, location, description, url, easy_apply, date_posted, num_applicants, source`

### 2. Evaluar match de un job vs CV
```bash
venv/bin/python -c "
from src.agents import master_agent
import json

resume = json.load(open('data/resume.json'))
job = {
    'title': 'Senior Java Developer',
    'company': 'Globant',
    'location': 'Remote - Mexico',
    'description': 'Looking for a Senior Java developer with Spring Boot...',
}
score, reasons = master_agent.evaluate_job_match(job, resume)
print(f'Score: {score}/100')
print(f'Razón: {reasons}')
"
```
Score >= 75 = buen match. El sistema notifica al usuario solo si pasa ese umbral.

### 3. Generar cover letter
```bash
venv/bin/python -c "
from src.agents import master_agent
import json

resume = json.load(open('data/resume.json'))
job = {'title': 'Sr Backend Eng', 'company': 'EPAM', 'description': '...'}
letter = master_agent.generate_cover_letter(job, resume)
print(letter)
"
```

### 4. LinkedIn — Listar conversaciones
```bash
venv/bin/python -c "
from src.tools import linkedin_messages_tool

# Obtener conversaciones recientes (usa GraphQL API)
convs = linkedin_messages_tool.get_unread_messages(limit=20)
for c in convs:
    print(f\"{c['sender_name']} ({c['sender_title'][:40]})\")
    print(f\"  Thread: {c['conversation_id']}\")
    print(f\"  Último msg: {c['last_message'][:80]}\")
    print()
"
```
Retorna: `conversation_id` (thread_id), `sender_name`, `sender_title`, `last_message`, `timestamp`

### 5. LinkedIn — Leer conversación completa
```bash
venv/bin/python -c "
from src.tools import linkedin_messages_tool

# Usa Playwright: navega directo a /messaging/thread/THREAD_ID/
msgs = linkedin_messages_tool.get_full_conversation('2-THREAD_ID_BASE64==')
for m in msgs:
    tag = 'YO' if m['from_me'] else 'ELLOS'
    print(f'[{tag}] {m[\"body\"][:150]}')
"
```
Cada mensaje: `body` (str), `from_me` (bool), `sender_name` (str), `timestamp` (str)

### 6. LinkedIn — Enviar mensaje
```bash
venv/bin/python -c "
from src.tools import linkedin_messages_tool

# IMPORTANTE: Siempre verificar que no hayamos ya respondido
sent = linkedin_messages_tool.send_message(
    '2-THREAD_ID_BASE64==',
    'Hi! Thanks for reaching out. I am interested in learning more about the role.'
)
print(f'Enviado: {sent}')
"
```
- Usa Playwright con navegación directa al thread (no sidebar clicks)
- Verifica el header del chat antes de enviar para evitar enviar al thread equivocado
- Retorna `True` si se envió correctamente

### 7. LinkedIn — Analizar mensaje de reclutador
```bash
venv/bin/python -c "
from src.agents import recruiter_agent
from src.tools import calendar_tool

# Obtener slots libres para proponer
free_slots = calendar_tool.get_free_slots(days_ahead=7, duration_minutes=60)

analysis = recruiter_agent.analyze_recruiter_message(
    message='Hi Alejandro, we have a Java role. Are you available for a call?',
    sender_name='John Recruiter',
    sender_title='Technical Recruiter at Google',
    conversation_history=[],  # lista de {body, from_me}
    free_slots=free_slots,
)
print(f\"Intent: {analysis['intent']}\")      # schedule|info|offer|rejection|general
print(f\"Urgency: {analysis['urgency']}\")    # high|medium|low
print(f\"Draft: {analysis['draft_response']}\")
print(f\"Needs input: {analysis['needs_user_input']}\")
"
```

### 8. Google Calendar — Slots libres
```bash
venv/bin/python -c "
from src.tools import calendar_tool

# Slots disponibles para entrevistas
slots = calendar_tool.get_free_slots(days_ahead=14, duration_minutes=60)
for s in slots:
    print(s['label'])
    # Ej: 'Lunes 9 Mar 9:00 AM - 10:00 AM'
"
```
**Regla**: Alejandro solo agenda en L-V, 9-11am o 3-4pm hora CDMX.

### 9. Google Calendar — Crear evento de entrevista
```bash
venv/bin/python -c "
from src.tools import calendar_tool
from datetime import datetime

event_id = calendar_tool.create_interview_event(
    job_title='Senior Java Developer',
    company='Globant',
    start_datetime=datetime(2026, 3, 10, 9, 0),  # año, mes, día, hora, minuto
    duration_minutes=60,
)
print(f'Evento creado: {event_id}')
"
```

### 10. Gmail — Leer emails de trabajo
```bash
venv/bin/python -c "
from src.tools import gmail_tool

emails = gmail_tool.get_recent_job_emails(processed_ids=set(), max_results=20)
for e in emails:
    print(f\"De: {e['from_address']}\")
    print(f\"Asunto: {e['subject']}\")
    print(f\"Fecha: {e['date']}\")
    print(f\"Body: {e['content'][:200]}\")
    print()
"
```

### 11. Gmail — Enviar email
```bash
venv/bin/python -c "
from src.tools import gmail_tool

gmail_tool.send_email(
    to='recruiter@company.com',
    subject='Re: Senior Java Developer Position',
    body='Hi, thank you for the opportunity...',
    thread_id=None,  # o thread_id para responder en hilo
)
"
```

### 12. Gmail — Analizar respuesta de empresa
```bash
venv/bin/python -c "
from src.agents import master_agent

result = master_agent.analyze_email_response(
    email_content='We are pleased to invite you to an interview...',
    email_subject='Interview Invitation',
    from_address='hr@company.com',
)
print(f\"Sentiment: {result['sentiment']}\")  # positive|negative|interview|neutral
print(f\"Action: {result['action']}\")        # schedule_interview|send_followup|none
print(f\"Summary: {result['summary']}\")
"
```

### 13. DB — Consultar estado
```bash
venv/bin/python -c "
from src.db.tracker import JobTracker
t = JobTracker()

# Estadísticas generales
print(t.get_stats())

# Jobs encontrados
for j in t.get_jobs_by_status('found'):
    print(f\"{j['title']} @ {j['company']} | score={j.get('match_score')}\")

# Conversaciones LinkedIn sin procesar
for c in t.get_unprocessed_conversations():
    print(f\"{c['participant_name']} | state={c['state']}\")

# Verificar si ya respondimos a un thread
has_reply = t.conversation_has_our_reply('THREAD_ID')
print(f'Ya respondimos: {has_reply}')
"
```

### 14. DB — Registrar acciones
```bash
venv/bin/python -c "
from src.db.tracker import JobTracker
t = JobTracker()

# Guardar conversación LinkedIn
t.save_linkedin_conversation(
    conversation_id='THREAD_ID',
    participant_name='John Recruiter',
    participant_title='Recruiter at Google',
    last_message='Hi, interested in a role?',
)

# Actualizar estado de conversación
t.update_conversation_state('THREAD_ID', 'responded', 'Respondimos con interés')

# Registrar nuestra respuesta
t.record_our_reply('THREAD_ID', 'Hi John, yes I am interested!')

# Guardar aplicación a job
t.save_application(job_id='JOB_ID', method='linkedin_easy_apply', cover_letter='...')
"
```

### 15. Browser Tool — Aplicar en portales externos
```bash
venv/bin/python -c "
from src.tools import browser_tool
import json

resume = json.load(open('data/resume.json'))

# Aplica navegando al portal con Playwright + vision LLM
result = browser_tool.apply_to_job_sync(
    job_url='https://careers.company.com/apply/12345',
    resume=resume,
    job_title='Senior Java Developer',
    company='Company Name',
)
print(f\"Success: {result['success']}\")
print(f\"Status: {result['status']}\")  # completed|captcha|need_user|error
"
```
**Nota**: El browser tool usa Llama-4-Scout via Groq para vision. Puede fallar en forms complejos.
Si falla, crear una tarea en `data/pending_browser_tasks.json` para manejo manual.

---

## API del Orchestrator (http://localhost:8777)

| Endpoint | Método | Descripción |
|---|---|---|
| `/health` | GET | Estado del sistema + stats DB |
| `/dashboard` | GET | Dashboard web (HTML) |
| `/pipeline` | GET | Estado del pipeline de aplicación |
| `/trigger/search` | POST | Trigger manual de búsqueda de jobs |
| `/trigger/apply-all` | POST | Aplica a todos los jobs con score >= 75% |
| `/trigger/email` | POST | Trigger manual de monitoreo Gmail |
| `/webhook/whatsapp` | POST | Webhook para mensajes WhatsApp |
| `/tokens` | GET | Estado de tokens OAuth |

```bash
# Ejemplos
curl -s http://localhost:8777/health | python3 -m json.tool
curl -X POST http://localhost:8777/trigger/search
curl -X POST http://localhost:8777/trigger/apply-all
curl -X POST http://localhost:8777/trigger/email
```

---

## Reglas CRÍTICAS

### Anti-spam
- **SIEMPRE** verificar si ya respondimos antes de enviar un mensaje LinkedIn
- Verificar con: `tracker.conversation_has_our_reply(thread_id)` o revisando si el último mensaje es `from_me=True`
- Si ya respondimos, NO enviar otro mensaje — esperar respuesta del reclutador
- Pausa de 3+ segundos entre envíos de mensajes

### Calendario
- **SIEMPRE** consultar `calendar_tool.get_free_slots()` antes de proponer horarios
- Alejandro solo agenda L-V, 9-11am o 3-4pm hora CDMX
- Después de agendar, crear el evento con `calendar_tool.create_interview_event()`

### Preferencias de Alejandro
- **Modalidad**: Remoto (preferido) o híbrido CDMX
- **Salario**: >= $50,000 MXN brutos en nómina formal (IMSS) o ~$2,500 USD via payroll (Deel, Remote)
- **NO acepta**: Honorarios, freelance, esquemas por hora, ni ofertas < $50k MXN
- **Stack**: Java, Spring Boot, Full Stack, Cloud (AWS/GCP), Microservices, Docker, K8s
- **Experiencia**: 5+ años (10+ total)

### Escalación
- **Ofertas de trabajo**: SIEMPRE escalar a Alejandro (vía WhatsApp o nota en DB)
- **Decisiones salariales**: NUNCA responder sin consultar
- **Entrevistas agendadas**: Crear evento en Calendar + notificar
- **Rechazos**: Notificar, no responder automáticamente

---

## Tareas browser pendientes
Archivo: `data/pending_browser_tasks.json`

Formato de cada tarea:
```json
{
  "type": "linkedin_reply|apply|schedule",
  "url": "https://...",
  "contact_name": "Nombre",
  "context": "Qué hacer",
  "suggested_message": "Texto sugerido (si aplica)",
  "created_at": "2026-03-08T17:00:00",
  "status": "pending|done"
}
```

Para agregar una tarea nueva, edita el JSON y añade un objeto con `"status": "pending"`.
Para completar, cambia a `"status": "done"`.

---

## Datos de Alejandro (para llenar forms/responder)
- **Nombre**: Alejandro Hernandez Loza
- **Email**: alejandrohloza@gmail.com
- **Teléfono**: +52 56 4144 6948
- **LinkedIn**: https://www.linkedin.com/in/alejandro-hernandez-loza/
- **Ubicación**: Ciudad de México, México
- **Título**: SR. Software Engineer
- **Skills**: Java, Spring Boot, Full Stack, JavaScript, Cloud (AWS/GCP), Docker, Kubernetes, Microservices
- **Disponibilidad**: Inmediata
- **CV completo**: `data/resume.json`
- **Cookies LinkedIn**: `config/linkedin_cookies.json`

---

## Workflow completo: de búsqueda a entrevista

1. **Buscar** → `jobspy_tool.search_jobs()` con términos relevantes
2. **Evaluar** → `master_agent.evaluate_job_match(job, resume)` → score 0-100
3. **Si score >= 75** → Notificar a Alejandro por WhatsApp, esperar aprobación
4. **Si aprobado** → `master_agent.generate_cover_letter()` → aplicar
5. **Aplicar** → Easy Apply (automático) o `browser_tool.apply_to_job_sync()` o tarea manual
6. **Monitorear** → Gmail cada 30min, LinkedIn cada 15min
7. **Responder reclutadores** → `recruiter_agent.analyze_recruiter_message()` → borrador → aprobar
8. **Agendar entrevista** → `calendar_tool.get_free_slots()` → proponer → crear evento
9. **Follow-up** → Si no hay respuesta en 7 días → `master_agent.generate_followup_email()`
