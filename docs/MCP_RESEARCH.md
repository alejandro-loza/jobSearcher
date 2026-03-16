# MCPs disponibles para JobSearcher

Investigación realizada: 2026-03-07

## Conclusión principal

Existen MCPs ya construidos para los 3 servicios que necesitamos.
En lugar de construir herramientas custom, conviene usar estos MCPs directamente.

---

## 1. Gmail + Google Calendar

### Opción A: Google Workspace MCP (recomendado)
- **Repo**: https://github.com/j3k0/mcp-google-workspace
- **Cubre**: Gmail + Calendar en un solo servidor
- **Auth**: OAuth2 (mismo google_credentials.json)
- **Ventaja**: Un solo server para ambos servicios

### Opción B: MCP oficial de Google Cloud
- **Blog**: https://cloud.google.com/blog/products/ai-machine-learning/announcing-official-mcp-support-for-google-services
- **Docs**: https://docs.cloud.google.com/mcp
- **Estado**: Google lanzó soporte oficial MCP para sus servicios
- **Nota**: Gmail y Calendar no confirmados aún como managed servers,
  pero Calendar está listado como "coming soon"

### Opción C: Calendar MCP independiente
- **Repo**: https://github.com/nspady/google-calendar-mcp
- **Cubre**: Solo Calendar, bien mantenido
- **Auth**: OAuth2

### Opción D: Gmail MCP independiente
- **Listing**: https://mcpservers.org/servers/bastienchabal/gmail-mcp
- **Cubre**: Solo Gmail

---

## 2. LinkedIn

### Opción A: linkedin-mcp-server (recomendado)
- **Repo**: https://github.com/stickerdaniel/linkedin-mcp-server
- **Cubre**: Perfiles, empresas, búsqueda de jobs
- **Método**: Web scraping (sin API key)
- **Ventaja**: No requiere LinkedIn MCP server separado ni API key

### Opción B: linkedin-mcpserver (API oficial)
- **Repo**: https://github.com/felipfr/linkedin-mcpserver
- **Cubre**: LinkedIn API integration

### Opción C: linkedin_mcp (más completo)
- **Repo**: https://github.com/Rayyan9477/linkedin_mcp
- **Cubre**: Buscar jobs, generar CV y cover letters, manejar aplicaciones
- **Listing**: https://glama.ai/mcp/servers/@Rayyan9477/linkedin_mcp

### Opción D: linkedin-jobs-mcp-server (via RapidAPI)
- **Repo**: https://github.com/Rom7699/linkedin-jobs-mcp-server
- **Requiere**: RapidAPI key para LinkedIn Data API
- **Ventaja**: Más estable que scraping

---

## Arquitectura recomendada con MCPs

```
Tu WhatsApp
    ↕
WhatsApp Bridge (Node.js)
    ↕
Orchestrator (Python FastAPI + GLM-4.7)
    ├── MCP: mcp-google-workspace  → Gmail + Calendar
    └── MCP: linkedin-mcp-server   → Búsqueda de jobs
```

## Credenciales necesarias

### Google (gmail + calendar)
- [ ] `config/google_credentials.json` - OAuth2 client (Desktop app)
  - Ir a: https://console.cloud.google.com
  - APIs habilitadas: Gmail API, Google Calendar API
  - Credencial: OAuth 2.0 → Aplicación de escritorio
  - Descargar JSON → renombrar a `google_credentials.json`

### LinkedIn MCP (stickerdaniel - scraping)
- No requiere API key
- Solo requiere sesión de LinkedIn activa o cookies

### LinkedIn MCP (RapidAPI - más estable)
- [ ] `RAPIDAPI_KEY` en .env
  - Registro en: https://rapidapi.com
  - Suscribir a: LinkedIn Data API

---

## Plan de implementación con MCPs

1. Instalar mcp-google-workspace:
   ```bash
   npx @j3k0/mcp-google-workspace
   ```

2. Instalar linkedin-mcp-server:
   ```bash
   pip install linkedin-mcp-server
   # o
   npx stickerdaniel/linkedin-mcp-server
   ```

3. Conectar el orchestrator Python a estos MCP servers via HTTP/SSE

4. GLM-4.7 usa los MCPs como tools

---

## Estado actual del proyecto

Los tools ya implementados en `src/tools/` hacen lo mismo que estos MCPs
pero de forma directa (Google API + jobspy).

**Decisión pendiente**: usar MCPs externos o mantener tools propios.
- MCPs: más estandarizado, menos código propio, fácil de extender
- Tools propios: más control, sin dependencia de repos externos

Sources:
- https://github.com/j3k0/mcp-google-workspace
- https://github.com/nspady/google-calendar-mcp
- https://cloud.google.com/blog/products/ai-machine-learning/announcing-official-mcp-support-for-google-services
- https://docs.cloud.google.com/mcp
- https://github.com/stickerdaniel/linkedin-mcp-server
- https://github.com/Rayyan9477/linkedin_mcp
- https://github.com/Rom7699/linkedin-jobs-mcp-server
- https://mcpservers.org/servers/bastienchabal/gmail-mcp
