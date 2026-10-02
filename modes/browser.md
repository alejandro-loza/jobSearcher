# Modo: browser — automación de formularios externos

Playwright + vision LLM (Llama-4-Scout vía Groq) para llenar formularios multi-paso.

## Aplicar a portal externo

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
print(result)
# {'success': bool, 'status': 'completed|captcha|need_user|error', 'reason': '...'}
"
```

## Qué hace internamente

1. Playwright abre el URL
2. Vision LLM analiza screenshot → identifica campos
3. Llena campos con datos de `resume.json`
4. Detecta siguiente paso (hasta 15 pasos)
5. Submit si llega al final

## Cuando falla

- **CAPTCHA** → crear tarea en `data/pending_browser_tasks.json`
- **Preguntas custom** (ej: "why do you want this job?") → escalar al usuario con `need_user`
- **Form complejo (>15 pasos)** → escalar

## Tarea browser pendiente

`data/pending_browser_tasks.json` — formato:
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

Al iniciar sesión: revisar este archivo y ejecutar los `"pending"`.

## Reglas

- **No reintentar** si falla 2 veces → crear tarea manual
- **Screenshots** se guardan en `data/screenshots/` para debug
- **Rate limit**: máx 5 apps/hora en sites externos
- **Verificar aplicación real**: usar `application_verifier.py` después del submit
