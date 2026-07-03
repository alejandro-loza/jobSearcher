# JobSearcher — índice de agentes

> **Este archivo es un índice, no la guía completa.** Carga solo los modos que necesites para la tarea actual → menos tokens, mejor contexto.

## Orden de carga

1. **SIEMPRE**: `modes/_shared.md` (reglas globales, componentes, tasks, endpoints)
2. **SIEMPRE**: `modes/_profile.md` (datos de Alejandro, preferencias, escalación)
3. **Según tarea**: carga 1-2 modos de la tabla de abajo

## Modos disponibles

| Modo | Cargar cuando... |
|---|---|
| [`modes/search.md`](modes/search.md) | Buscas jobs (portal_scanner zero-token, JobSpy, liveness) |
| [`modes/apply.md`](modes/apply.md) | Generas cover letter o aplicas (Easy Apply, browser) |
| [`modes/recruiter.md`](modes/recruiter.md) | Respondes mensajes de reclutadores en LinkedIn |
| [`modes/email.md`](modes/email.md) | Trabajas con Gmail o follow-ups (cadencia diferenciada) |
| [`modes/calendar.md`](modes/calendar.md) | Agendas entrevistas o consultas slots |
| [`modes/db.md`](modes/db.md) | Haces queries a SQLite o registras eventos |
| [`modes/browser.md`](modes/browser.md) | Automatizas formularios externos con Playwright + vision |

## Atajos de comandos

```bash
# Arrancar orchestrator
cd /home/alejandro/Proyectos/jobSearcher && venv/bin/python run.py

# Health check
curl -s http://localhost:8777/health | python3 -m json.tool

# Triggers manuales
curl -X POST http://localhost:8777/trigger/portal-scan   # zero-token
curl -X POST http://localhost:8777/trigger/search        # JobSpy
curl -X POST http://localhost:8777/trigger/apply-all     # score >= 75
curl -X POST http://localhost:8777/trigger/email         # Gmail monitor

# Tareas browser pendientes (revisar al iniciar sesión)
cat data/pending_browser_tasks.json | python3 -m json.tool
```

## Workflow de referencia (búsqueda → entrevista)

1. **Buscar** → `modes/search.md` (portal_scanner PREFERIDO, JobSpy de respaldo)
2. **Evaluar** → `master_agent.evaluate_job_match()` → score 0-100
3. **Notificar** → si score ≥ 75, WhatsApp a Alejandro, esperar aprobación
4. **Aplicar** → `modes/apply.md` (cover letter + Easy Apply o browser)
5. **Monitorear** → Gmail (30min) + LinkedIn (15min), automático vía orchestrator
6. **Responder reclutadores** → `modes/recruiter.md` (draft → aprobar → enviar)
7. **Agendar** → `modes/calendar.md` (slots libres → proponer → crear evento)
8. **Follow-up** → `modes/email.md` (cadencia diferenciada por estado)

## Memoria persistente (claude-mem)

Scripts wrapper para acceder al worker de claude-mem (`localhost:37777`):

```bash
~/.opencode/bin/claude-mem/mem-search "query" [type] [limit]   # Buscar en memoria
~/.opencode/bin/claude-mem/mem-timeline --id <id>              # Contexto por ID
~/.opencode/bin/claude-mem/mem-timeline --query "query"        # Contexto por query
~/.opencode/bin/claude-mem/mem-get P10 P9                      # Detalles de prompts (P-prefix)
~/.opencode/bin/claude-mem/mem-get 1 2 3                       # Detalles de observaciones (numeric)
```

**Flujo**: `mem-search` → obtener IDs → `mem-get` para detalles completos.

## Principio rector: minimizar tokens

- **Prefiere `portal_scanner` antes que `JobSpy`** para empresas en `portals.yml` (zero tokens)
- **Usa `liveness.should_skip_job()`** antes de llamar al LLM (regex gratis)
- **Dedup con `tracker.job_exists()` / `job_url_exists()`** en vez del LLM
- **Carga solo el modo que necesitas**, no la guía completa
