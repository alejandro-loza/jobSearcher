# Pedido para Antigravity - LinkedIn

Estoy construyendo un sistema automatizado de búsqueda de trabajo.
Necesito que hagas varias cosas en LinkedIn con la cuenta de Alejandro.

---

## 1. Exportar cookies de sesión de LinkedIn

Necesito las cookies de sesión de LinkedIn para que el sistema pueda
operar autenticado sin necesitar password.

Por favor:
1. Abre LinkedIn con la cuenta de Alejandro (alejandrohloza@gmail.com o la que uses)
2. Extrae las cookies de sesión, específicamente:
   - `li_at` (la más importante - token de sesión principal)
   - `JSESSIONID`
   - `li_rm` (si existe)
3. Guarda las cookies en este archivo:
   `/data/projects/proyects/jobSearcher/config/linkedin_cookies.json`

Formato esperado:
```json
{
  "li_at": "AQEDAQIAAA....",
  "JSESSIONID": "ajax:123456789",
  "li_rm": "opcional"
}
```

---

## 2. Instalar y configurar el MCP de LinkedIn

Por favor instala este MCP server de LinkedIn:
- Repo: https://github.com/stickerdaniel/linkedin-mcp-server

Pasos:
```bash
cd /data/projects/proyects/jobSearcher
pip install linkedin-mcp-server
# o si es Node:
npm install -g linkedin-mcp-server
```

Configura las cookies del paso 1 en el MCP.

---

## 3. Verificar acceso a LinkedIn

Con las cookies configuradas, verifica que el sistema puede:
- [ ] Buscar ofertas de trabajo en LinkedIn
- [ ] Ver detalles completos de una oferta
- [ ] Usar LinkedIn Easy Apply (aplicar con 1 click)
- [ ] Ver el perfil del usuario

---

## 4. Datos del perfil de LinkedIn de Alejandro

Por favor obtén y guarda en `/data/projects/proyects/jobSearcher/config/linkedin_profile.json`:
- URL del perfil de LinkedIn
- Nombre completo tal como aparece en LinkedIn
- Headline / título profesional actual
- Si tiene Easy Apply habilitado en su perfil

---

## 5. Configurar preferencias de búsqueda de trabajo

En LinkedIn, activa o revisa:
- **Open to Work** (si Alejandro quiere tenerlo activo)
- Preferencias de trabajo: remoto, tipo de empleo, etc.

---

## Contexto del sistema

El sistema hará lo siguiente automáticamente:
1. Cada 6 horas busca ofertas en LinkedIn que coincidan con el CV de Alejandro
2. Evalúa el match con IA (GLM-4.7)
3. Si el match es >= 75%, notifica a Alejandro por WhatsApp
4. Si Alejandro responde "si", aplica automáticamente con Easy Apply
5. Si hay respuesta por email, la analiza y agenda entrevistas en Google Calendar

---

## Respuesta esperada

Por favor responde en este mismo archivo con:
- Confirmación de cada paso completado
- El valor de la cookie `li_at` (o confirmación de que está en el archivo)
- URL del perfil de LinkedIn de Alejandro
- Cualquier problema que hayas encontrado
---

## Respuesta de Antigravity (LinkedIn)

¡He cumplido con todos los pasos para la integración de LinkedIn!

### Resumen de Tareas:
1. **Cookies de sesión**: Extraídas y guardadas en `/data/projects/proyects/jobSearcher/config/linkedin_cookies.json`.
   - Cookie `li_at` confirmada y operativa.
2. **MCP Server**: Instalado globalmente (`linkedin-mcp-server`).
3. **Verificación de acceso**:
   - [x] Búsqueda de ofertas: **Funcional** (4,400+ resultados para Software Engineer).
   - [x] Detalle de ofertas: **Funcional**.
   - [x] Easy Apply: **Visible y accesible** ("Solicitud sencilla").
   - [x] Perfil de usuario: **Accesible**.
4. **Perfil de Alejandro**: Guardado en `/data/projects/proyects/jobSearcher/config/linkedin_profile.json`.
   - **Nombre**: Alejandro Loza
   - **Headline**: SR. Software Engineer
   - **URL**: [linkedin.com/in/alejandro-hernandez-loza/](https://www.linkedin.com/in/alejandro-hernandez-loza/)
5. **Preferencias**: "Open to Work" está **Activo** para roles de Java, Full Stack y Cloud.

¡El sistema ya puede operar en LinkedIn!
