# Modo: email — Gmail + follow-ups

## Leer emails de trabajo

```bash
venv/bin/python -c "
from src.tools import gmail_tool

emails = gmail_tool.get_recent_job_emails(processed_ids=set(), max_results=20)
for e in emails:
    print(f\"De: {e['from_address']}\")
    print(f\"Asunto: {e['subject']} — {e['date']}\")
    print(f\"Body: {e['content'][:200]}\")
"
```

## Enviar email

```bash
venv/bin/python -c "
from src.tools import gmail_tool

gmail_tool.send_email(
    to='recruiter@company.com',
    subject='Re: Senior Java Developer Position',
    body='Hi, thank you for...',
    thread_id=None,  # o thread_id para responder en hilo
)
"
```

## Analizar respuesta de empresa (LLM)

```bash
venv/bin/python -c "
from src.agents import master_agent

result = master_agent.analyze_email_response(
    email_content='We are pleased to invite you to an interview...',
    email_subject='Interview Invitation',
    from_address='hr@company.com',
)
print(result['sentiment'])  # positive|negative|interview|neutral
print(result['action'])     # schedule_interview|send_followup|none
print(result['summary'])
"
```

## Follow-up con cadencia diferenciada

Cadencia automática basada en estado. **No usar "7 días fijo"**, usa:

```bash
venv/bin/python -c "
from src.tools import followup_cadence

# Para una aplicación dada:
decision = followup_cadence.decide_from_app(app)
# O manual:
decision = followup_cadence.decide(
    status='applied',           # applied|responded|interview|offer|rejected
    applied_at='2026-04-01T10:00:00Z',
    last_followup_at=None,
    followup_count=0,
)

print(f'should_send={decision.should_send}')
print(f'kind={decision.followup_kind}')     # first_apply|second_apply|thank_you|...
print(f'reason={decision.reason}')
"
```

**Cadencias**:
| Estado | Día 1er follow-up | Días subsiguientes | Máx |
|---|---|---|---|
| `applied` | día 7 | día 14 | 2 |
| `responded` | día 1 | día 3 | 2 |
| `interview` | día 1 (thank-you) | — | 1 |
| `offer`/`rejected`/`skip` | no follow-up | — | 0 |

## Generar email de follow-up con tono adaptado

```bash
venv/bin/python -c "
from src.agents import master_agent
import json

resume = json.load(open('data/resume.json'))
job = {'title': '...', 'company': '...'}

email = master_agent.generate_followup_email(
    job, resume, days_since_apply=7, kind='first_apply'
)
print(email['subject'])
print(email['body'])
"
```

`kind`: `first_apply` | `second_apply` | `responded_first` | `responded_second` | `thank_you`

## Registrar follow-up enviado

```bash
venv/bin/python -c "
from src.db.tracker import JobTracker
t = JobTracker()
t.record_followup_sent(app_id=123)  # incrementa contador + fecha
"
```

## Reglas

- Antes de enviar: verificar que `followup_cadence.decide()` retorna `should_send=True`
- Registrar cada envío con `tracker.record_followup_sent(app_id)` para que la cadencia cuente
- Si cambia de `applied` a `responded`: `tracker.record_response_received(job_id)`
- Blocklist: no enviar a remitentes en `data/blocklist_senders.json`
- Máx 2 follow-ups por ciclo (anti-spam global)
