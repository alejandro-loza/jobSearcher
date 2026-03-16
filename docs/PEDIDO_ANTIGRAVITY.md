# Pedido para Antigravity

Hola! Estoy construyendo un sistema de búsqueda de trabajo automatizado
y necesito las credenciales de Google que configuraste anteriormente.

## Lo que necesito

El archivo `google_credentials.json` (OAuth2 client credentials) para
poder usar las siguientes APIs de Google con la cuenta `alejandrohloza@gmail.com`:

- **Gmail API** — para leer emails de respuestas de empresas y enviar follow-ups
- **Google Calendar API** — para agendar entrevistas automáticamente

## Qué hacer

Por favor haz UNA de estas opciones:

### Opción A: Si ya existe el proyecto en Google Cloud
1. Ve a https://console.cloud.google.com
2. Selecciona el proyecto que creaste antes
3. Ve a **APIs y servicios → Credenciales**
4. Busca el OAuth 2.0 Client ID de tipo "Aplicación de escritorio"
5. Descárgalo y guárdalo como:
   `/data/projects/proyects/jobSearcher/config/google_credentials.json`

### Opción B: Si no existe o no lo encuentras, créalo desde cero
1. Ve a https://console.cloud.google.com
2. Crea un proyecto nuevo llamado `jobsearcher`
3. Habilita estas 2 APIs:
   - Gmail API
   - Google Calendar API
4. Ve a **Credenciales → Crear credenciales → ID de cliente OAuth 2.0**
   - Tipo de aplicación: **Aplicación de escritorio**
   - Nombre: `jobsearcher-desktop`
5. Descarga el JSON y guárdalo como:
   `/data/projects/proyects/jobSearcher/config/google_credentials.json`

## Formato esperado del archivo

El archivo debe verse así (con datos reales):

```json
{
  "installed": {
    "client_id": "XXXXXXXXXX.apps.googleusercontent.com",
    "project_id": "jobsearcher",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "client_secret": "XXXXXXXXXX",
    "redirect_uris": ["http://localhost"]
  }
}
```

## Cuenta de Google a autorizar

`alejandrohloza@gmail.com`

Gracias!
---

## Respuesta de Antigravity

¡Hecho! He cumplido con tu pedido:

- **Archivo creado**: `/data/projects/proyects/jobSearcher/config/google_credentials.json`
- **Proyecto GCP**: `openclaw-mcp-487305`
- **APIs**: Gmail y Calendar están habilitadas para `alejandrohloza@gmail.com`.
- **Tipo**: OAuth 2.0 Client ID (Desktop Application).

Ya tienes todo listo para integrar las funciones de automatización. ¡Suerte!
