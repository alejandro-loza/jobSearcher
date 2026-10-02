# Modo: search — buscar jobs

Dos fuentes, **úsalas en este orden**:

## 1. Portal Scanner (zero-token) — PREFERIDO

Escanea APIs públicas de Greenhouse/Ashby/Lever sin gastar tokens de LLM.
Empresas en `config/portals.yml`.

```bash
venv/bin/python -c "
from src.tools import portal_scanner
result = portal_scanner.scan_all(dry_run=False, check_liveness=True)
portal_scanner.print_summary(result)
"
```

Una sola empresa:
```bash
venv/bin/python -c "
from src.tools import portal_scanner
r = portal_scanner.scan_company('Anthropic')
portal_scanner.print_summary(r)
"
```

Trigger HTTP manual:
```bash
curl -X POST http://localhost:8777/trigger/portal-scan
```

**Config**: `config/portals.yml` define filtros (`title_filter.positive/negative`) y empresas (`tracked_companies`).

Jobs se guardan en SQLite con `source='greenhouse-api'` / `ashby-api` / `lever-api` y `status='found'`.

## 2. JobSpy (LinkedIn + Indeed + Glassdoor)

Cuando necesites buscar más allá de `portals.yml`:

```bash
venv/bin/python -c "
from src.tools import jobspy_tool

jobs = jobspy_tool.search_jobs(
    search_term='Senior Java Developer',
    location='remote',          # o 'Ciudad de Mexico'
    results_wanted=15,
    hours_old=168,              # 168h = 7 días
    site_names=['linkedin', 'indeed', 'glassdoor'],
    easy_apply_only=False,
)

for j in jobs:
    print(f\"{j['title']} @ {j['company']} | score={j.get('match_score','?')}\")
"
```

**Liveness automático**: `jobspy_tool.search_jobs()` ya filtra ghost postings internamente. No necesitas llamar `liveness.py` manualmente aquí.

## Evaluar match de un job

```bash
venv/bin/python -c "
from src.agents import master_agent
import json

resume = json.load(open('data/resume.json'))
job = { 'title': '...', 'company': '...', 'description': '...' }
score, reasons = master_agent.evaluate_job_match(job, resume)
print(f'Score: {score}/100 — {reasons}')
"
```

Umbral: score >= 75 → notificar a Alejandro por WhatsApp.

## Ghost detection manual (sin LLM, gratis)

Si quieres filtrar antes de evaluar match:
```bash
venv/bin/python -c "
from src.tools import liveness

check = liveness.classify_job(
    title='Senior Java Developer',
    description='...',
    num_applicants=450,
    days_posted=12,
)
print(f'{check.result} ({check.score}/100) — {check.reason}')
"
```

Resultados: `active` | `expired` | `uncertain`.

## Reglas

- **Antes de JobSpy**, revisa si la empresa está en `portals.yml` y usa portal_scanner (cero tokens)
- **No busques mismo término 2 veces al día** — la DB ya tiene dedup por hash
- **Location**: "Ciudad de Mexico" / "Mexico City" / "remote"
- Jobs con < 50 applicantes tienen prioridad (oportunidad alta)
