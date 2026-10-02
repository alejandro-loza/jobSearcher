# Reglas globales — todos los modos

## Sistema

Agente autónomo de búsqueda de empleo. FastAPI + APScheduler + LLM (Groq/SambaNova, gratis).

- **Directorio**: `/home/alejandro/Proyectos/jobSearcher`
- **Venv**: `venv/bin/python`
- **DB**: `data/jobsearcher.db` (SQLite)
- **CV**: `data/resume.json`
- **Orchestrator**: `http://localhost:8777`

## Al iniciar sesión

1. `cd /home/alejandro/Proyectos/jobSearcher`
2. Revisa `data/pending_browser_tasks.json` — ejecuta `"status": "pending"`
3. Verifica orchestrator: `curl -s http://localhost:8777/health | python3 -m json.tool`
4. Si no corre: `venv/bin/python run.py` (puerto 8777)

## Componentes principales

| Componente | Archivo | Qué hace |
|---|---|---|
| Orchestrator | `src/orchestrator.py` | FastAPI + APScheduler, webhook WhatsApp |
| Master Agent | `src/agents/master_agent.py` | Evalúa jobs, cover letters, emails |
| Recruiter Agent | `src/agents/recruiter_agent.py` | Mensajes de reclutadores LinkedIn |
| Coordinator | `src/agents/coordinator.py` | Enruta a LLM óptimo (GLM/Groq/SambaNova) |
| JobSpy Tool | `src/tools/jobspy_tool.py` | Búsqueda (LinkedIn/Indeed/Glassdoor) |
| Portal Scanner | `src/tools/portal_scanner.py` | Scan zero-token (Greenhouse/Ashby/Lever) |
| Liveness | `src/tools/liveness.py` | Filtra ghost postings antes del LLM |
| **LinkedIn Governor** | `src/tools/linkedin_governor.py` | **Choke point único anti-ban: caps por acción + presupuesto global de cuenta, horario, gap, jitter, ban/recovery, User-Agent único. TODO camino a LinkedIn pasa por `can_act()`/`record_action()`** |
| Follow-up Cadence | `src/tools/followup_cadence.py` | Decide cuándo mandar follow-up |
| LinkedIn Tool | `src/tools/linkedin_messages_tool.py` | Mensajes LinkedIn |
| Gmail Tool | `src/tools/gmail_tool.py` | Lee/envía emails |
| Calendar Tool | `src/tools/calendar_tool.py` | Google Calendar |
| WhatsApp Tool | `src/tools/whatsapp_tool.py` | Notificaciones via bridge Node |
| Browser Tool | `src/tools/browser_tool.py` | Playwright + vision LLM |
| DB Tracker | `src/db/tracker.py` | SQLite: jobs/apps/emails/convs |

## Scheduled tasks (APScheduler)

- `portal_scan`: cada 4h — zero-token Greenhouse/Ashby/Lever
- `job_search`: cada 2h — JobSpy (con filtro liveness automático)
- `linkedin_messages`: dispara cada 15min, pero el governor lo gatea (~1 lectura/75min, 12/día)
- `email_monitor`: cada 30min — Gmail
- `followup`: diario — cadencia diferenciada por estado

## API del Orchestrator

| Endpoint | Método | Descripción |
|---|---|---|
| `/health` | GET | Estado + stats DB |
| `/dashboard` | GET | Dashboard web |
| `/pipeline` | GET | Estado del pipeline |
| `/trigger/search` | POST | JobSpy manual |
| `/trigger/portal-scan` | POST | Portal scanner manual |
| `/trigger/apply-all` | POST | Aplica a score >= 75% |
| `/trigger/email` | POST | Gmail monitor manual |
| `/webhook/whatsapp` | POST | Webhook WhatsApp |

## Reglas críticas (aplican a TODOS los modos)

### Anti-ban LinkedIn (crítico)
- **TODA acción a LinkedIn pasa por `linkedin_governor`**: `ok, _ = gov.can_act(gov.APPLY|MSG_READ|MSG_SEND|CONNECT|POST|SEARCH)` antes, `gov.record_action(...)` después.
- Nunca añadir un camino nuevo a LinkedIn sin gatearlo por el governor (LinkedIn banea por actividad TOTAL de la cuenta, no por script).
- Los caps, horario, gap, jitter, ban/recovery y User-Agent viven SOLO ahí — no duplicar en otros módulos.

### Anti-spam
- **SIEMPRE** verificar si ya respondimos antes de LinkedIn/email
- `tracker.conversation_has_our_reply(thread_id)` o último msg `from_me=True`
- Si ya respondimos → NO enviar, esperar respuesta del reclutador
- Pausa ≥ 3s entre envíos de mensajes

### Tokens (prioridad del proyecto)
- **Prefiere portal_scanner antes que JobSpy** cuando la empresa esté en `portals.yml`
- **Prefiere liveness filter antes del LLM** — `liveness.should_skip_job()` es gratis
- **No llames al LLM para dedup** — `tracker.job_exists()` / `job_url_exists()`
- Cachea resultados de evaluación (no re-evaluar el mismo job)

### Datos de Alejandro
Ver `modes/_profile.md`. No duplicar aquí.

## Modos disponibles

Cuando trabajes en un área específica, CARGA solo el modo correspondiente para minimizar contexto:

- `modes/search.md` — buscar jobs (JobSpy + portal_scanner)
- `modes/apply.md` — aplicar a jobs (cover letter + browser)
- `modes/recruiter.md` — mensajes de reclutadores LinkedIn
- `modes/email.md` — Gmail + follow-up
- `modes/calendar.md` — Calendar + entrevistas
- `modes/db.md` — queries SQLite
- `modes/browser.md` — automación de formularios externos
