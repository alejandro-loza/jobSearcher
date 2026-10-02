# Modo: apply — aplicar a jobs

## Generar cover letter

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

## Aplicar — Easy Apply en LinkedIn

Automático vía HTTP (sin browser, más rápido y más seguro):
```bash
# El pipeline normal ya hace esto; sólo necesitas ejecutarlo si quieres un job específico
venv/bin/python -c "
from src.tools import linkedin_easy_apply_api
result = linkedin_easy_apply_api.apply(job_url='https://...', cover_letter='...', resume_json=...)
print(result)
"
```

## Aplicar — portal externo (Workday, Greenhouse, etc.)

```bash
venv/bin/python -c "
from src.tools import browser_tool
import json

resume = json.load(open('data/resume.json'))
result = browser_tool.apply_to_job_sync(
    job_url='https://careers.company.com/apply/12345',
    resume=resume,
    job_title='Senior Java Developer',
    company='Company Name',
)
print(f\"Success: {result['success']} — Status: {result['status']}\")
# status: completed|captcha|need_user|error
"
```

**Si falla**: crear entrada en `data/pending_browser_tasks.json`:
```json
{
  "type": "apply",
  "url": "https://...",
  "context": "CAPTCHA bloqueó, aplicar manual",
  "status": "pending"
}
```

## Rate limiting

- Máximo **5 aplicaciones/hora** a LinkedIn (anti-banning)
- Pausas humanas de 5-15s entre aplicaciones
- Pausa de seguridad cada 5 apps

## Trigger "apply all" (score >= 75)

```bash
curl -X POST http://localhost:8777/trigger/apply-all
```

## Reglas

- **Antes de aplicar**: `master_agent.evaluate_job_match()` → score >= 75
- **Antes de enviar cover letter**: verificar salario en JD ≥ preferencias de Alejandro
- **Escalar al usuario**: si la oferta menciona negociación, honorarios, o C2C
- **Registrar aplicación**: `tracker.save_application(job_id, method, cover_letter)`
