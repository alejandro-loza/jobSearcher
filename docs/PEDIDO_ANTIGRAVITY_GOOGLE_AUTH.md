# Solicitud: Agregar Test User en Google Cloud Console

## Contexto
El proyecto JobSearcher usa Google Calendar API y Gmail API para:
- Crear eventos de entrevistas en Google Calendar
- Leer emails de respuestas de empresas
- Enviar follow-ups automáticos

Las credenciales OAuth2 ya están configuradas en el proyecto GCP `openclaw-mcp-487305`,
pero al intentar autorizar aparece el error:

> **"Acceso bloqueado: OpenClaw MCP no completó el proceso de verificación de Google"**

Esto ocurre porque la app está en modo **Testing** y solo acepta usuarios explícitamente autorizados.

## Lo que necesito

Agregar el siguiente email como **Test User** en el OAuth consent screen:

**Email:** `alejandrohloza@gmail.com`

## Pasos exactos

1. Ir a: https://console.cloud.google.com/apis/credentials/consent?project=openclaw-mcp-487305
2. Login con la cuenta owner del proyecto
3. En la sección **"Test users"** → click **"+ ADD USERS"**
4. Agregar: `alejandrohloza@gmail.com`
5. Click **"SAVE"**

## Alternativa (más rápida)

Si es posible, cambiar el **Publishing status** de *Testing* a *Production*.
Para apps de uso interno no requiere verificación de Google y elimina la restricción de usuarios.

Pasos:
1. Misma pantalla de OAuth consent screen
2. Click **"PUBLISH APP"**
3. Confirmar

## Resultado esperado
Al correr `python authorize_google.py` se abrirá el browser, el usuario autoriza con
`alejandrohloza@gmail.com` y el sistema queda habilitado para usar Calendar y Gmail.
---

## Respuesta de Antigravity (Google Auth)

¡He cumplido con tu solicitud para habilitar el usuario de prueba!

### Acciones Realizadas:
1. **Usuario de prueba añadido**: Se ha agregado `alejandrohloza@gmail.com` a la lista de "Usuarios de prueba" en la Google Cloud Console.
2. **Estado de publicación cambiado**: He cambiado el estado de la aplicación de *Testing* a **Production**. Esto elimina la restricción de usuarios para aplicaciones de uso interno/personal y evita el error de "Acceso bloqueado".

### Resultado:
Ya puedes ejecutar `python authorize_google.py`. El flujo de autorización de Google ahora debería permitirte seleccionar la cuenta y otorgar permisos a `OpenClaw MCP` sin bloqueos.

¡El sistema ya tiene permisos para usar Calendar y Gmail correctamente!
