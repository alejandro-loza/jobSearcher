# JobSearcher - Agente Autónomo de Búsqueda de Empleo

## ¿Qué es?

JobSearcher es un agente de inteligencia artificial que busca trabajo por ti de forma
completamente autónoma. Mientras tú estás en el trabajo, el sistema está activo 24/7
buscando vacantes, evaluando su compatibilidad con tu perfil, aplicando a las mejores
oportunidades, hablando con reclutadores en tu nombre y agendando entrevistas en tu
calendario.

La comunicación contigo es via WhatsApp — el agente te avisa de todo lo importante
y te pide aprobación antes de tomar decisiones relevantes.

---

## Arquitectura general

```
                    ┌─────────────────────────────────┐
                    │         TÚ (WhatsApp)            │
                    └──────────────┬──────────────────┘
                                   │ mensajes / aprobaciones
                    ┌──────────────▼──────────────────┐
                    │      WhatsApp Bridge (Node.js)   │
                    │      whatsapp-web.js / puerto 3001│
                    └──────────────┬──────────────────┘
                                   │ HTTP webhook
                    ┌──────────────▼──────────────────┐
                    │     Orchestrator (FastAPI)        │
                    │     APScheduler / puerto 8000     │
                    │                                   │
                    │  ┌─────────┐  ┌───────────────┐  │
                    │  │ Tareas  │  │  Webhook WA   │  │
                    │  │ Auto    │  │  (comandos)   │  │
                    │  └────┬────┘  └───────┬───────┘  │
                    └───────┼───────────────┼──────────┘
                            │               │
          ┌─────────────────┼───────────────┼──────────────────┐
          │                 │               │                  │
    ┌─────▼─────┐    ┌──────▼──────┐ ┌─────▼────┐    ┌───────▼──────┐
    │  LLM      │    │  JobSpy     │ │  Gmail   │    │  LinkedIn    │
    │  (Groq /  │    │  LinkedIn   │ │  API     │    │  Voyager API │
    │  SambaNova│    │  Indeed     │ │  OAuth2  │    │  (mensajes)  │
    └───────────┘    │  Glassdoor  │ └──────────┘    └──────────────┘
                     └─────────────┘
                            │
                    ┌───────▼──────────────┐
                    │  Google Calendar API  │
                    │  (entrevistas)        │
                    └──────────────────────┘
                            │
                    ┌───────▼──────────────┐
                    │  Playwright + LLM     │
                    │  (browser agent para  │
                    │   aplicar en sitios   │
                    │   externos)           │
                    └──────────────────────┘
                            │
                    ┌───────▼──────────────┐
                    │  SQLite Database      │
                    │  (tracker de todo)    │
                    └──────────────────────┘
```

---

## Componentes principales

### 1. Orchestrator (`src/orchestrator.py`)
El cerebro coordinador. Es una API FastAPI con APScheduler que ejecuta tareas
automáticas cada cierto tiempo y responde a los mensajes de WhatsApp.

**Tareas automáticas:**
- Cada 6 horas: busca nuevas vacantes
- Cada 15 minutos: revisa mensajes nuevos en LinkedIn
- Cada 30 minutos: monitorea Gmail por respuestas de empresas
- Cada día a las 9am: envía follow-ups a aplicaciones sin respuesta (7 días)

### 2. WhatsApp Bridge (`services/whatsapp/index.js`)
Un servidor Node.js que conecta WhatsApp con el orchestrator. Usa `whatsapp-web.js`
para simular un cliente de WhatsApp real. El QR para conectar está disponible en
`http://localhost:3001/qr`.

**Flujo de mensajes:**
- Tus mensajes de WhatsApp → bridge → orchestrator (`/webhook/whatsapp`)
- Orchestrator genera respuesta → bridge → tu WhatsApp

### 3. Motor de IA (LLM)
El sistema usa **rotación automática** entre proveedores:

| Proveedor | Modelo | Uso |
|-----------|--------|-----|
| Groq | llama-3.3-70b-versatile | Principal (100k tokens/día gratis) |
| SambaNova | Meta-Llama-3.3-70B-Instruct | Fallback automático (sin límite diario) |

El LLM realiza estas tareas:
- Analizar tu CV y generar criterios de búsqueda
- Evaluar el match de cada vacante (score 0-100)
- Generar cover letters personalizadas
- Redactar respuestas a reclutadores
- Analizar emails de empresas
- Responder tus preguntas por WhatsApp

### 4. Búsqueda de empleos (`src/tools/jobspy_tool.py`)
Usa `python-jobspy` para buscar en LinkedIn, Indeed y Glassdoor simultáneamente.
Los términos de búsqueda los genera el LLM analizando tu CV. Solo notifica las
vacantes con score >= 75%.

### 5. Agente de LinkedIn (`src/tools/linkedin_messages_tool.py`)
Monitorea tus mensajes de LinkedIn usando la API interna de LinkedIn (Voyager API)
con tu cookie `li_at`. Cuando llega un mensaje de reclutador:
1. El LLM analiza el mensaje y genera una respuesta borrador
2. Te la manda por WhatsApp para aprobación
3. Si apruebas (`si`) la envía. Si editas (`editar [texto]`) la ajusta.

### 6. Agente de browser (`src/tools/browser_tool.py`)
Usa Playwright (automatización de navegador) para aplicar en sitios externos.
El LLM con visión analiza capturas de pantalla de la página y decide qué llenar
y en qué campos. Soporta formularios de hasta 15 pasos.

### 7. Gmail (`src/tools/gmail_tool.py`)
Conectado via OAuth2. Monitorea emails relacionados con trabajo y:
- Detecta rechazos → actualiza status en DB
- Detecta convocatorias a entrevistas → agenda en Calendar
- Detecta emails que necesitan respuesta → genera y envía reply

### 8. Google Calendar (`src/tools/calendar_tool.py`)
Conectado via OAuth2. Consulta tu disponibilidad real antes de proponer horarios
a reclutadores. Tus ventanas disponibles: 9-11am y 3-4pm, Lunes-Viernes, CDMX.

### 9. Base de datos (`src/db/tracker.py`)
SQLite en `data/jobsearcher.db`. Rastrea todo:
- `jobs`: vacantes encontradas con score y status
- `applications`: aplicaciones enviadas
- `emails`: emails procesados
- `interviews`: entrevistas agendadas

---

## Flujo completo de una aplicación

```
1. Scheduler dispara job_search cada 6h
   └── LLM analiza CV → genera términos de búsqueda
       └── JobSpy busca en LinkedIn/Indeed/Glassdoor
           └── Por cada vacante nueva:
               └── LLM evalúa match (score 0-100)
                   └── Si score >= 75%:
                       └── WhatsApp: "Nuevo trabajo (85% match) - ¿Aplico?"
                           └── Tú respondes "si"
                               └── LLM genera cover letter
                                   ├── Si Easy Apply en LinkedIn:
                                   │   └── Playwright aplica con cookies LinkedIn
                                   └── Si URL externa:
                                       └── Browser agent llena formulario
                                           └── WhatsApp: "Aplicado ✅"
```

## Flujo de respuesta a reclutador (LinkedIn)

```
1. Scheduler revisa LinkedIn messages cada 15min
   └── Reclutador te escribe
       └── LLM analiza mensaje (detecta idioma, intención)
           └── LLM genera respuesta en tu nombre
               └── WhatsApp: "Reclutador de X escribe... Borrador: [texto] ¿Envío?"
                   ├── Tú: "si" → se envía
                   ├── Tú: "no" → se descarta
                   └── Tú: "editar Prefiero martes" → LLM ajusta y reenvía pregunta
                       └── Si piden disponibilidad:
                           └── Calendar consulta slots libres
                               └── WhatsApp: "¿Cuál prefieres? 1. Lunes 9am 2. Martes 3pm"
                                   └── Tú: "1"
                                       └── Reclutador recibe respuesta + Calendar event creado
```

---

## Comandos de WhatsApp

| Comando | Acción |
|---------|--------|
| `estado` | Resumen de aplicaciones, entrevistas pendientes |
| `buscar [rol]` | Búsqueda manual con término específico |
| `todos` | Aplica a todos los jobs pendientes de aprobación |
| `entrevistas` | Lista próximas entrevistas del Calendar |
| `pausar` | Detiene las búsquedas automáticas |
| `reanudar` | Reactiva las búsquedas |
| `si` | Aprueba la acción pendiente (aplicar / enviar mensaje) |
| `no` | Rechaza la acción pendiente |
| `editar [texto]` | Edita el borrador del mensaje al reclutador |
| `1` / `2` / `3` | Selecciona un slot de entrevista |
| Cualquier pregunta | El LLM responde con contexto de tu búsqueda |

---

## Stack tecnológico

| Capa | Tecnología |
|------|-----------|
| Backend principal | Python 3.12, FastAPI, APScheduler |
| WhatsApp | Node.js, whatsapp-web.js |
| LLM | Groq + SambaNova (Llama 3.3 70B) |
| Búsqueda de empleos | python-jobspy |
| Browser automation | Playwright |
| LinkedIn mensajes | Voyager API (requests + cookies) |
| Email | Gmail API (google-auth, google-api-python-client) |
| Calendario | Google Calendar API |
| Base de datos | SQLite |
| Entorno | venv Python, variables en .env |

---

## Configuración requerida

Archivo `.env` con:
- `GROQ_API_KEY` - API key de Groq (gratuita)
- `SAMBANOVA_API_KEY` - API key de SambaNova (gratuita)
- `WHATSAPP_MY_NUMBER` - Tu número de WhatsApp
- `GMAIL_MY_EMAIL` - Tu email de Gmail
- `LINKEDIN_PROFILE_URL` - URL de tu perfil de LinkedIn
- Archivos OAuth2 en `config/` para Gmail y Calendar
- Cookie `li_at` de LinkedIn en `config/linkedin_cookies.json`

---

## Estado actual del sistema

- Jobs encontrados: 230
- Aplicaciones enviadas: 29
- Entrevistas agendadas: 0
- El sistema lleva activo desde el 7 de marzo 2026

---

## Cómo iniciar el sistema

**Terminal 1 - WhatsApp Bridge:**
```bash
cd services/whatsapp
npm install
node index.js
# Abrir http://localhost:3001/qr y escanear con WhatsApp
```

**Terminal 2 - Orchestrator:**
```bash
source venv/bin/activate
python run.py
```

El agente enviará un mensaje de bienvenida por WhatsApp confirmando que está activo.
