# Modo: db — queries SQLite

DB en `data/jobsearcher.db`. Clase: `JobTracker`.

## Estadísticas generales

```bash
venv/bin/python -c "
from src.db.tracker import JobTracker
t = JobTracker()
print(t.get_stats())
"
```

## Jobs encontrados sin aplicar

```bash
venv/bin/python -c "
from src.db.tracker import JobTracker
t = JobTracker()
for j in t.get_jobs_by_status('found'):
    print(f\"{j['title']} @ {j['company']} | score={j.get('match_score')}\")
"
```

## Conversaciones LinkedIn sin procesar

```bash
venv/bin/python -c "
from src.db.tracker import JobTracker
t = JobTracker()
for c in t.get_unprocessed_conversations():
    print(f\"{c['participant_name']} | state={c['state']}\")
"
```

## Aplicaciones activas con contexto de cadencia

```bash
venv/bin/python -c "
from src.db.tracker import JobTracker
from src.tools import followup_cadence

t = JobTracker()
for app in t.get_applications_with_cadence_context():
    d = followup_cadence.decide_from_app(app)
    flag = '📮' if d.should_send else '⏳'
    print(f\"{flag} {app['company']} — {app['status']} — {d.reason}\")
"
```

## Escritura — acciones comunes

```bash
venv/bin/python -c "
from src.db.tracker import JobTracker
t = JobTracker()

# LinkedIn conversation
t.save_linkedin_conversation(
    conversation_id='THREAD_ID',
    participant_name='John Recruiter',
    participant_title='Recruiter at Google',
    last_message='Hi, interested?',
)
t.update_conversation_state('THREAD_ID', 'responded', 'Respondimos')
t.record_our_reply('THREAD_ID', 'Hi John, yes!')

# Application
t.save_application(job_id='JOB_ID', method='linkedin_easy_apply', cover_letter='...')

# Follow-up tracking (nuevos métodos)
t.record_followup_sent(app_id=123)
t.record_response_received(job_id='JOB_ID')       # applied → responded
t.record_interview_completed(job_id='JOB_ID')     # responded → interview
"
```

## Dedup de jobs

```bash
venv/bin/python -c "
from src.db.tracker import JobTracker
t = JobTracker()
print(t.job_exists('MD5_HASH'))         # por id
print(t.job_url_exists('https://...'))  # por URL (dedup entre fuentes)
"
```

## Schema — tablas principales

- `jobs`: id (hash), title, company, url, match_score, status, source, found_at
- `applications`: id, job_id, applied_at, method, cover_letter, status, **followup_count**, **last_followup_at**, **last_response_at**, **last_interview_at**
- `emails`: job_id, thread_id, from_address, subject, sentiment, action_taken, responded_by
- `interviews`: job_id, scheduled_at, calendar_event_id
- `linkedin_conversations`: conversation_id, participant_name, state, last_our_reply_at
- `linkedin_messages`: conversation_id, message_text, from_me, processed
