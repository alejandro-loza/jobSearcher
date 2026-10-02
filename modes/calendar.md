# Modo: calendar — Google Calendar + entrevistas

## Slots libres

```bash
venv/bin/python -c "
from src.tools import calendar_tool

slots = calendar_tool.get_free_slots(days_ahead=14, duration_minutes=60)
for s in slots:
    print(s['label'])   # 'Lunes 9 Mar 9:00 AM - 10:00 AM'
"
```

**Regla de Alejandro**: solo L-V, 9-11am o 3-4pm hora CDMX. El tool ya la aplica.

## Crear evento de entrevista

```bash
venv/bin/python -c "
from src.tools import calendar_tool
from datetime import datetime

event_id = calendar_tool.create_interview_event(
    job_title='Senior Java Developer',
    company='Globant',
    start_datetime=datetime(2026, 3, 10, 9, 0),
    duration_minutes=60,
)
print(f'Evento creado: {event_id}')
"
```

## Registrar entrevista en DB

```bash
venv/bin/python -c "
from src.db.tracker import JobTracker
t = JobTracker()
t.record_interview_completed(job_id='JOB_ID')  # marca last_interview_at + status='interview'
"
```

## Reglas

- **Siempre** `get_free_slots()` antes de proponer horario al reclutador
- Después de agendar: `create_interview_event()` + notificar a Alejandro por WhatsApp
- Al completarse la entrevista: `tracker.record_interview_completed()` → activa cadencia thank-you día +1
