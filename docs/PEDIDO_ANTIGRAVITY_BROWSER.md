# Pedido para Antigravity — Agente de Browser

Fecha: 2026-03-08

Hola Antigravity! El sistema de búsqueda de empleo ya funciona automáticamente:
responde a reclutadores en LinkedIn, busca jobs, y monitorea emails. Pero hay
tareas que requieren **interacción real con el browser** en páginas de terceros
(calendarios, portales de aplicación, forms) que el bot no puede hacer solo.

**Tu rol: ser el "browser agent" del sistema.** Cuando el sistema detecte una
tarea que requiere browser, la pondrá en `data/pending_browser_tasks.json`.
Tú la ejecutas.

---

## Cómo funciona

### 1. Revisa tareas pendientes
```bash
cat /data/projects/proyects/jobSearcher/data/pending_browser_tasks.json
```

### 2. Para cada tarea con `"status": "pending"`:

**a) Si es `linkedin_reply`**: Abre la URL, lee el contexto, y responde.

**b) Si es `apply`**: Navega al portal, llena el form con los datos de Alejandro.

**c) Si es `schedule`**: Abre el link de calendario (Calendly, Google Calendar, etc.), elige el mejor slot disponible.

### 3. Consulta el calendario ANTES de agendar
```bash
cd /data/projects/proyects/jobSearcher
venv/bin/python -c "
from src.tools import calendar_tool
slots = calendar_tool.get_free_slots(days_ahead=14, duration_minutes=60)
for s in slots:
    print(s.get('label', s))
"
```
**Regla**: Solo agendar en slots que aparezcan ahí. Si no hay slots, propón
los siguientes disponibles al reclutador.

### 4. Después de agendar, crea el evento en Calendar
```bash
venv/bin/python -c "
from src.tools import calendar_tool
from datetime import datetime
calendar_tool.create_interview_event(
    job_title='TITULO DEL PUESTO',
    company='NOMBRE EMPRESA O RECLUTADOR',
    start_datetime=datetime(2026, 3, 9, 9, 0),  # ajustar
    duration_minutes=60,
)
print('Evento creado')
"
```

### 5. Registra lo que hiciste en la DB
```bash
venv/bin/python -c "
from src.db.tracker import JobTracker
t = JobTracker()
t.update_conversation_state('THREAD_ID', 'responded', 'Antigravity: descripción')
t.record_our_reply('THREAD_ID', 'texto exacto del mensaje enviado')
"
```

### 6. Marca la tarea como completada
Edita `data/pending_browser_tasks.json` y cambia `"status": "pending"` → `"status": "done"`.

---

## Datos de Alejandro (para llenar forms)

- **Nombre**: Alejandro Hernandez Loza
- **Email**: alejandrohloza@gmail.com
- **Teléfono**: +52 56 4144 6948
- **LinkedIn**: https://www.linkedin.com/in/alejandro-hernandez-loza/
- **Ubicación**: Ciudad de México, México
- **Título**: SR. Software Engineer
- **Skills**: Java, Spring Boot, Full Stack, JavaScript, Cloud (AWS/GCP), Docker, Kubernetes, Microservices
- **Experiencia**: 5+ años
- **Disponibilidad**: Inmediata
- **Modalidad preferida**: Remoto
- **Expectativa salarial**: 60,000 MXN libre de impuestos (negociable)
- **CV completo**: `/data/projects/proyects/jobSearcher/data/resume.json`
- **Cookies LinkedIn**: `/data/projects/proyects/jobSearcher/config/linkedin_cookies.json`

---

## Tareas pendientes actuales

Están en `data/pending_browser_tasks.json`. Al momento hay 2:

1. **Sudheer Dasari** — Proponerle slots para llamada
2. **Deepak Singh Rajput** — Pedirle más detalles de su oferta

---

## Estado del sistema

```bash
cd /data/projects/proyects/jobSearcher

# Health check
curl -s http://localhost:8777/health | python3 -m json.tool

# Dashboard web
# http://localhost:8777/dashboard

# Conversaciones sin procesar en DB
venv/bin/python -c "
from src.db.tracker import JobTracker
t = JobTracker()
for c in t.get_unprocessed_conversations():
    print(f\"{c['participant_name']} | state={c['state']}\")
"

# Leer mensajes de una conversación específica
venv/bin/python -c "
from src.tools import linkedin_messages_tool
msgs = linkedin_messages_tool.get_full_conversation('THREAD_ID_AQUI')
for m in msgs:
    tag = 'YO' if m['from_me'] else 'ELLOS'
    print(f'[{tag}] {m[\"body\"][:150]}')
"
```

---

## Reportar resultados

Agrega una sección `## Respuesta de Antigravity` al final de este archivo.
