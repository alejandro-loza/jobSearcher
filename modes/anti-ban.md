# Modo anti-ban — evitar el baneo de LinkedIn

> Cargar cuando trabajes cualquier acción que toque LinkedIn (buscar, aplicar Easy
> Apply, mensajes, conexiones, posts) o al revisar salud de la cuenta.

## Contexto crítico

**La cuenta de Alejandro YA fue restringida una vez** (2026-05-11): LinkedIn detectó
*"el uso de programas que automatizan tu actividad"*. Está en `recovery_mode`. Cada
acción sobre LinkedIn se hace sobre una cuenta **ya flageada** → tolerancia mínima.

## Principio rector: ATS-first

El grueso del apply va al **ATS de la empresa** (Greenhouse/Ashby/Lever) vía
`external_ats_agent` → **cero LinkedIn, cero riesgo**. LinkedIn queda para:
- **Lectura** vía API Voyager (mensajes, badges) — bajo riesgo.
- **Escrituras mínimas** gobernadas (Easy Apply ocasional, responder reclutas).
- **Posteo**: asistido/manual (el automatizado es frágil y arriesgado).

## Todo pasa por el governor (`src/tools/linkedin_governor.py`)

Único choke point. Antes de CUALQUIER acción LinkedIn: `gov.can_act(kind)`; tras
ejecutarla: `gov.record_action(kind)`. Nunca llamar a LinkedIn saltándose esto.

El governor aplica: caps diarios **aleatorizados** (±30% por día, semilla=fecha) +
**días ligeros** (1-2/semana al 50%) + **warmup** (rampa 0.4→1.0 en 28 días desde
`warmup_anchor`) + cap de **recovery** como techo + per-hour + **gap mínimo** +
**jitter** no-lineal + **horario laboral** + **budget global** interactivo.

## Envelope seguro 2026 (referencia)

- **Conexiones**: 20-30/día seguro, <80/día, <800/mes. Cuenta nueva/flageada:
  10-15/día y subir +5/semana. Aceptación >30% (si <15% = spammer).
- **Mensajes**: 50/día free, 75 premium, 250 Sales Navigator.
- **Nunca** golpear el cap 7/7 días — 1-2 días ligeros/semana (ya automatizado).
- **Timing**: variar delays (mecánico = bot). Ya con jitter no-lineal.
- **Mezcla de acciones**: no solo escrituras — incluir lecturas de cobertura
  (`gov.PASSIVE`, task pasiva) para no parecer bot especializado.
- **Actividad 24/7 = bot**: respetar horario y off-hours (ya en `hours`).

## Técnico: fingerprint, sesión, IP

- **Un solo perfil de navegador persistente** (`src/tools/linkedin_session.py`,
  `data/linkedin_browser_profile`): mismo UA (Chrome 131), viewport, locale es-MX,
  timezone America/Mexico_City. Todas las herramientas de browser lo usan — NUNCA
  `new_context` fresco (invalida el JSESSIONID = señal de bot).
- **IP**: residencial estática de CDMX (la laptop). **NO usar proxy** — uno
  rotativo/datacenter EMPEORA (geo-shift → security review). Mismo país = clave.

## El "test" de baneo = monitorear, no provocar (`src/tools/linkedin_health.py`)

- `probe_account_status()`: una llamada Voyager `/me`; clasifica
  `ok | rate_limited(999) | checkpoint | session_dead | restricted`.
  **`session_dead` (cookie expirada) NO es ban** — solo refrescar cookie.
  Solo `checkpoint`/`restricted` escalan ban.
- `risk_report()`: risk_score 0-100 (cercanía a caps, regularidad de timing,
  mezcla escritura/lectura). Bandas verde/ámbar/rojo.
- Corre cada 2h (`linkedin_health_task`); endpoint `/health/linkedin`.

## Playbook si LinkedIn restringe

1. **Pausar todo** — el governor lo hace solo (`record_ban` → pausa escalada:
   48h → 7d → 30d+cap0 según `ban_count`).
2. Desconectar automatización, completar verificación de identidad de LinkedIn.
3. Esperar 48h antes de reintentar login.
4. Apelar por el canal oficial: conciso, cortés, **NO admitir automatización**.
5. Reanudar solo tras semanas de comportamiento compliant (el warmup ayuda).

## Nota sobre `ban_count`

Solo restricciones REALES (checkpoint/restricted) cuentan. Expiración de cookie
(`session_dead`/`auth_failed`) NO debe escalar el contador (se corrigió el inflado
histórico 3→1 el 2026-07-04). El monitor ya los distingue.
