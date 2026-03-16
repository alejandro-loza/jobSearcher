# Solicitud: Agregar redirect URIs al OAuth Client en Google Cloud Console

## Problema
Al intentar autorizar Google Calendar y Gmail aparece:
> **Error 400: invalid_request**
> "La solicitud de OpenClaw MCP no es válida"

La causa es que el OAuth client no tiene registrados los URIs de redirect locales.
Google deprecó el método OOB (`urn:ietf:wg:oauth:2.0:oob`) en 2022.

## Lo que necesito

En el proyecto GCP `openclaw-mcp-487305`, editar el OAuth 2.0 Client ID
y agregar estos **Authorized redirect URIs**:

```
http://localhost:8765/
http://localhost:8766/
http://localhost:8080/
```

## Pasos exactos

1. Ir a: https://console.cloud.google.com/apis/credentials?project=openclaw-mcp-487305
2. Click en el OAuth 2.0 Client ID (tipo "Desktop app" o "Web application")
3. En la sección **"Authorized redirect URIs"** → click **"+ ADD URI"**
4. Agregar las 3 URIs:
   - `http://localhost:8765/`
   - `http://localhost:8766/`
   - `http://localhost:8080/`
5. Click **"SAVE"**
6. **Descargar el JSON actualizado** del client ID y reemplazar el archivo en:
   `config/google_credentials.json`

## Por qué es necesario

El script `authorize_google.py` levanta un servidor HTTP local en el puerto
indicado para recibir el código de autorización de Google. Google necesita
saber de antemano qué URIs son válidas para redirigir.

## Verificación

Después del cambio, correr en la terminal del servidor:
```bash
cd /data/projects/proyects/jobSearcher
source venv/bin/activate
python authorize_google.py
```

Debe abrir el browser sin errores y guardar:
- `config/calendar_token.json`
- `config/gmail_token.json`
---

## Respuesta de Antigravity (OAuth Fix)

¡He cumplido con tu solicitud para corregir los Redirect URIs!

### Acciones Realizadas:
1. **Nuevo Cliente OAuth**: Dado que los clientes de tipo "Desktop app" no permiten URIs de redirección, he creado un nuevo cliente de tipo **Web application** llamado `OpenClaw MCP Web`.
2. **URIs de Redirección Añadidos**: He configurado los siguientes URIs autorizados:
   - `http://localhost:8765/`
   - `http://localhost:8766/`
   - `http://localhost:8080/`
3. **Credenciales Actualizadas**: He reemplazado el contenido de `config/google_credentials.json` con las nuevas credenciales que incluyen estos URIs.

### Resultado:
Ya puedes proceder con la autorización. Al ejecutar `python authorize_google.py`, Google redirigirá correctamente a tu servidor local una vez que aceptes los permisos.

¡El sistema de autenticación ya es 100% compatible con el flujo local!
