# Plan de Refactoring: LinkedIn HR Networking Agent

**Archivo**: `src/agents/linkedin_hr_agent.py` (525 líneas)
**Fecha**: 2026-04-03
**Estado actual**: ROTO — Playwright search bloqueado por LinkedIn (ERR_TOO_MANY_REDIRECTS)

---

## Problema

`search_hr_contacts()` usa Playwright para scrape de LinkedIn People Search:
- Navega a `linkedin.com/search/results/people/?keywords=...`
- Extrae links con selector `div[role="list"] a[href*="/in/"]`
- Parsea nombre/titulo del texto del link

**Por qué falla:**
1. LinkedIn bloquea navegación automatizada a `/search/` (redirects infinitos)
2. Los selectores CSS de LinkedIn cambian frecuentemente (clases ofuscadas)
3. El SPA de LinkedIn no renderiza correctamente bajo Playwright headless
4. Anti-bot detection bloquea aunque las cookies sean válidas

**Lo que SI funciona:**
- GraphQL API para listar conversaciones (`messengerConversations`)
- GraphQL API para leer mensajes (`messengerMessages`)
- `linkedin_api` Python library para `search_people()` (en MCP server)
- Playwright para enviar mensajes (navegación directa a thread)
- Playwright para enviar connection requests (navegación directa a invite URL)

---

## Solución propuesta

Reemplazar `search_hr_contacts()` (Playwright scraping) con `linkedin_api.search_people()` (API HTTP). Mantener `send_connection_request()` en Playwright (funciona, navegación directa).

### Arquitectura actual vs propuesta

```
ACTUAL (roto):
  Playwright → /search/results/people/ → scrape HTML → filtrar HR → Playwright invite

PROPUESTO:
  linkedin_api.search_people() → filtrar HR → Playwright invite
```

---

## Tareas

### Fase 1: Reemplazar búsqueda (core fix)

#### 1.1 Crear `_get_linkedin_api()` helper
- Instanciar `linkedin_api.Linkedin(li_at, jsessionid)` con cookies de `config/linkedin_cookies.json`
- Reusar la misma lógica de `_load_cookies()` que ya existe
- Manejar errores de sesión inválida (cookie expirada)
- Usar `RequestsCookieJar` como en `src/mcp/linkedin_server.py`

```python
from linkedin_api import Linkedin
from requests.cookies import RequestsCookieJar

def _get_linkedin_api():
    """Instancia autenticada de linkedin_api."""
    cookies = _load_cookies()
    li_at = cookies.get("li_at", "")
    jsessionid = cookies.get("JSESSIONID", "").replace('"', '')

    jar = RequestsCookieJar()
    jar.set("li_at", li_at, domain=".linkedin.com")
    jar.set("JSESSIONID", f'"{jsessionid}"', domain=".linkedin.com")

    return Linkedin("", "", cookies=jar)
```

**Dependencia**: Verificar que `linkedin_api` ya está instalado en venv (lo usa `src/mcp/linkedin_server.py`).

#### 1.2 Reescribir `search_hr_contacts()`
- Eliminar todo el bloque Playwright (launch browser, goto, locators, parsing)
- Usar `api.search_people(keywords=..., limit=...)`
- El keyword pattern actual es: `'recruiter OR "talent acquisition" OR "HR" "{company}"'`
- `linkedin_api.search_people()` solo acepta `keywords` como parámetro principal

```python
def search_hr_contacts(company: str, limit: int = 5) -> list:
    """Busca contactos HR/Recruiter en una empresa via LinkedIn API."""
    try:
        api = _get_linkedin_api()

        HR_TITLES = [
            "recruiter", "talent acquisition", "HR",
            "recursos humanos", "reclutador", "staffing",
        ]
        HR_TITLES_LOWER = [t.lower() for t in HR_TITLES]

        contacts = []
        for title_kw in ["recruiter", "talent acquisition", "HR"]:
            if len(contacts) >= limit:
                break
            # Construir keyword string con empresa y título
            keywords = f"{title_kw} {company}"
            results = api.search_people(
                keywords=keywords,
                limit=limit,
            )
            for r in results:
                profile_url = f"https://www.linkedin.com/in/{r.get('public_id', '')}"
                headline = r.get("headline", "") or ""

                # Filtrar: debe tener keyword HR en titulo
                if not any(kw in headline.lower() for kw in HR_TITLES_LOWER):
                    continue
                # Dedup por URL
                if any(c["profile_url"] == profile_url for c in contacts):
                    continue

                contacts.append({
                    "name": f"{r.get('firstName', '')} {r.get('lastName', '')}".strip(),
                    "title": headline,
                    "profile_url": profile_url,
                    "vanity_name": r.get("public_id", ""),
                    "company": company,
                })
                if len(contacts) >= limit:
                    break

        return contacts
    except Exception as e:
        logger.error(f"Error buscando HR en {company}: {e}")
        return []
```

**Nota**: La API de LinkedIn tiene rate limits propios (~100 requests/día). Las 3 búsquedas por empresa x 46 empresas = 138 calls, excede el límite si se ejecutan todas de golpe. Ver Fase 2.

#### 1.3 Mantener `send_connection_request()` sin cambios
- Ya funciona con Playwright (navegación directa a `/preload/custom-invite/`)
- No depende de search, solo necesita `vanity_name`
- Mantener las pausas de 5 segundos entre requests

---

### Fase 2: Optimizar ejecución

#### 2.1 Búsqueda incremental por empresa
- Actualmente busca en las 46 empresas cada ejecución
- Cambiar a round-robin: 5-8 empresas por ejecución
- Almacenar `last_company_index` en `linkedin_hr_log.json`

```python
COMPANIES_PER_RUN = 6  # ~18 API calls por run (3 title_kw x 6 companies)

def _get_next_companies(log: dict) -> list:
    idx = log.get("last_company_index", 0)
    batch = TARGET_COMPANIES[idx : idx + COMPANIES_PER_RUN]
    if len(batch) < COMPANIES_PER_RUN:
        batch += TARGET_COMPANIES[: COMPANIES_PER_RUN - len(batch)]
    log["last_company_index"] = (idx + COMPANIES_PER_RUN) % len(TARGET_COMPANIES)
    return batch
```

#### 2.2 Rate limiting
- Pausa de 2-3 segundos entre calls a `search_people()` (no solo entre invites)
- Si la API retorna 429, parar y guardar progreso
- Agregar `api_calls_today` al log para tracking

#### 2.3 Cache de contactos encontrados
- Si un contacto ya esta en `contacts_found`, no volver a buscarlo
- Crear set de `known_vanity_names` al inicio de cada run
- Evita calls redundantes a la API

---

### Fase 3: Seguridad y observabilidad

#### 3.1 Agregar kill switch
- `LINKEDIN_CONNECTIONS_BLOCKED = True` al inicio del archivo
- Verificar en `expand_hr_network()` antes de cualquier envío
- Alinear con la arquitectura de 5 capas de seguridad del proyecto

#### 3.2 Integrar con response_decision_agent (opcional)
- Las connection requests son notas de 300 chars, no conversaciones
- Se podría validar la nota con `approve_outgoing()` antes de enviar
- Bajo riesgo de spam porque el mensaje es templated y corto

#### 3.3 Mejorar logging
- Log cada búsqueda API: empresa, resultados, filtrados
- Log cada invite: nombre, empresa, éxito/fallo
- Agregar métricas al dashboard web (conexiones enviadas, tasa de aceptación)

#### 3.4 Manejo de cookies expiradas
- Si `_get_linkedin_api()` falla con auth error, loguear y abortar el run
- No intentar renovar cookies automáticamente (requiere intervención manual)
- Notificar via WhatsApp: "Cookies de LinkedIn expiradas, necesito nuevas"

---

### Fase 4: Testing

#### 4.1 Test unitario de búsqueda
- Mock de `linkedin_api.search_people()` con datos reales
- Verificar filtrado por título HR
- Verificar dedup por profile_url

#### 4.2 Test de integración (manual)
- Ejecutar `search_hr_contacts("Netflix", limit=3)` con cookies reales
- Verificar que retorna contactos HR válidos
- Ejecutar `expand_hr_network(max_requests=2)` y verificar invites enviadas

---

## Archivos a modificar

| Archivo | Cambio |
|---|---|
| `src/agents/linkedin_hr_agent.py` | Reescribir `search_hr_contacts()`, agregar `_get_linkedin_api()`, kill switch, round-robin |
| `data/linkedin_hr_log.json` | Agregar campos: `last_company_index`, `api_calls_today` |
| `src/orchestrator.py` | Sin cambios (ya llama `expand_hr_network()`) |
| `requirements.txt` | Verificar que `linkedin-api` esta listado |

## Archivos que NO se tocan

| Archivo | Razón |
|---|---|
| `src/tools/linkedin_messages_tool.py` | Funciona bien, no tiene relación |
| `src/mcp/linkedin_server.py` | Ya tiene kill switch, se queda como está |
| `send_connection_request()` en hr_agent | Funciona con Playwright directo, no usa search |

---

## Estimación de esfuerzo

| Fase | Complejidad |
|---|---|
| Fase 1: Core fix | Baja — reemplazar 1 función + agregar helper |
| Fase 2: Optimización | Media — round-robin + rate limiting + cache |
| Fase 3: Seguridad | Baja — kill switch + logging |
| Fase 4: Testing | Baja — 1 test unitario + 1 manual |

## Riesgo principal

La librería `linkedin_api` usa endpoints internos no documentados de LinkedIn. Si LinkedIn cambia su API interna, esta librería también se rompe. Sin embargo:
- Es un proyecto open-source activo con mantenimiento
- Los endpoints de búsqueda de personas son más estables que el HTML del SPA
- Fallback: se podría implementar búsqueda via GraphQL Voyager API (como ya se hace con mensajes)

---

## Orden de ejecución recomendado

1. **1.1** → `_get_linkedin_api()` helper
2. **1.2** → Reescribir `search_hr_contacts()`
3. **3.1** → Kill switch
4. **2.1** → Round-robin
5. **2.2** → Rate limiting
6. **4.2** → Test manual con 2-3 empresas
7. **2.3** → Cache
8. **3.3** → Logging mejorado
9. **3.4** → Manejo de cookies expiradas
10. **3.2** → Integración con decision agent (si se considera necesario)
