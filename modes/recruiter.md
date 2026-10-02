# Modo: recruiter — responder mensajes LinkedIn

## Listar conversaciones

```bash
venv/bin/python -c "
from src.tools import linkedin_messages_tool

convs = linkedin_messages_tool.get_unread_messages(limit=20)
for c in convs:
    print(f\"{c['sender_name']} ({c['sender_title'][:40]})\")
    print(f\"  Thread: {c['conversation_id']}\")
    print(f\"  Último msg: {c['last_message'][:80]}\")
"
```
Retorna: `conversation_id`, `sender_name`, `sender_title`, `last_message`, `timestamp`.

## Leer conversación completa

```bash
venv/bin/python -c "
from src.tools import linkedin_messages_tool

msgs = linkedin_messages_tool.get_full_conversation('2-THREAD_ID==')
for m in msgs:
    tag = 'YO' if m['from_me'] else 'ELLOS'
    print(f'[{tag}] {m[\"body\"][:150]}')
"
```
Cada msg: `body`, `from_me`, `sender_name`, `timestamp`.

## Enviar mensaje

**REGLA**: verificar que no hayamos respondido ya.

```bash
venv/bin/python -c "
from src.db.tracker import JobTracker
from src.tools import linkedin_messages_tool

t = JobTracker()
thread = '2-THREAD_ID=='

if t.conversation_has_our_reply(thread):
    print('Ya respondimos, NO enviar')
else:
    sent = linkedin_messages_tool.send_message(
        thread,
        'Hi! Thanks for reaching out...'
    )
    print(f'Enviado: {sent}')
    t.record_our_reply(thread, 'Hi! Thanks for reaching out...')
"
```

## Analizar mensaje de reclutador (LLM)

```bash
venv/bin/python -c "
from src.agents import recruiter_agent
from src.tools import calendar_tool

free_slots = calendar_tool.get_free_slots(days_ahead=7, duration_minutes=60)

analysis = recruiter_agent.analyze_recruiter_message(
    message='Hi Alejandro, we have a Java role. Are you available for a call?',
    sender_name='John Recruiter',
    sender_title='Technical Recruiter at Google',
    conversation_history=[],
    free_slots=free_slots,
)
print(f\"Intent: {analysis['intent']}\")       # schedule|info|offer|rejection|general
print(f\"Urgency: {analysis['urgency']}\")     # high|medium|low
print(f\"Draft: {analysis['draft_response']}\")
print(f\"Needs input: {analysis['needs_user_input']}\")
"
```

## Reglas

- Usa Playwright con navegación directa al thread (`/messaging/thread/ID/`), NO sidebar clicks
- Verifica header del chat antes de enviar (evita thread equivocado)
- Si `intent == 'offer'` → SIEMPRE escalar a Alejandro
- Si `intent == 'schedule'` → consultar Calendar primero
- Si `intent == 'rejection'` → notificar, NO responder automáticamente
- Pausa de 3+ segundos entre envíos
