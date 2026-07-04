"""
LinkedIn health — el "test de baneo" SEGURO.

No provoca el baneo: vigila las señales tempranas. Dos funciones:

  probe_account_status()  → una llamada Voyager barata; clasifica la sesión en
                            ok | rate_limited | checkpoint | session_dead | restricted.
  risk_report()           → lee el ledger del governor y calcula un risk_score 0-100
                            (cercanía a caps, regularidad de timing, mezcla de acciones).

Diseño clave (aprendido del historial real de la cuenta): SESSION_DEAD (cookie
expirada / 401) NO es un ban — solo requiere refrescar cookies y NO debe escalar
el contador de bans. Solo CHECKPOINT y RESTRICTED son restricción real de LinkedIn.
"""

from __future__ import annotations

import statistics
from datetime import datetime
from typing import Dict, List

from loguru import logger

from config import settings
from src.tools import linkedin_governor as gov
from src.tools.linkedin_messages_tool import _build_session

# Estados de la sesión
OK = "ok"
RATE_LIMITED = "rate_limited"     # 999 — bajar ritmo, aún no es ban
CHECKPOINT = "checkpoint"         # challenge/verificación — restricción real
SESSION_DEAD = "session_dead"     # 401/403 — cookie muerta, refrescar (NO es ban)
RESTRICTED = "restricted"         # cuenta restringida — ban real
PROBE_ERROR = "probe_error"       # red/otro — indeterminado

# Estados que SÍ son restricción real de LinkedIn (escalan ban).
REAL_BAN_STATES = {CHECKPOINT, RESTRICTED}


def probe_account_status() -> Dict:
    """Una llamada Voyager /me autenticada. Clasifica sin provocar nada."""
    result = {"status": PROBE_ERROR, "http": None, "detail": "", "at": datetime.now().isoformat()}
    try:
        s = _build_session()
        resp = s.get(
            "https://www.linkedin.com/voyager/api/me",
            timeout=12,
            allow_redirects=False,
        )
        code = resp.status_code
        result["http"] = code
        loc = resp.headers.get("Location", "") or ""

        loc_l = loc.lower()
        if code == 200:
            result["status"] = OK
        elif code == 999:
            result["status"] = RATE_LIMITED
            result["detail"] = "HTTP 999 — LinkedIn pide bajar el ritmo"
        elif code in (301, 302, 303, 307, 308):
            if "checkpoint" in loc_l or "challenge" in loc_l:
                result["status"] = CHECKPOINT
                result["detail"] = f"redirige a checkpoint/challenge: {loc[:120]}"
            elif any(k in loc_l for k in ("login", "authwall", "uas", "signup")):
                result["status"] = SESSION_DEAD
                result["detail"] = f"redirige a login — cookie expirada (no es ban): {loc[:120]}"
            else:
                # Redirect sin login ni checkpoint: lo más seguro es tratar como
                # sesión muerta (a /me autenticado no debería redirigir estando OK).
                result["status"] = SESSION_DEAD
                result["detail"] = f"redirect inesperado a {loc[:120] or '(sin Location)'}"
        elif code in (401, 403):
            # 403 con cuerpo de restricción = ban; 401/403 sin eso = cookie muerta.
            body = (resp.text or "")[:500].lower()
            if any(k in body for k in ("restrict", "restring", "suspend", "unusual")):
                result["status"] = RESTRICTED
                result["detail"] = "cuerpo indica restricción de cuenta"
            else:
                result["status"] = SESSION_DEAD
                result["detail"] = f"HTTP {code} — cookie expirada/ inválida (no es ban)"
        else:
            result["detail"] = f"HTTP {code} inesperado"
    except Exception as e:
        result["detail"] = f"{type(e).__name__}: {str(e)[:120]}"
    return result


def _gaps_minutes(times: List[datetime]) -> List[float]:
    times = sorted(times)
    return [(times[i] - times[i - 1]).total_seconds() / 60.0 for i in range(1, len(times))]


def risk_report() -> Dict:
    """Lee el ledger `linkedin_activity` de HOY y calcula un risk_score 0-100."""
    reasons: List[str] = []
    score = 0

    # Conteos de hoy por tipo + timestamps (para regularidad).
    kinds = [gov.SEARCH, gov.APPLY, gov.MSG_READ, gov.MSG_SEND, gov.CONNECT, gov.POST, gov.PASSIVE]
    counts: Dict[str, int] = {}
    all_times: List[datetime] = []
    write_ct = read_ct = 0
    with gov._conn() as conn:
        for k in kinds:
            rows = conn.execute(
                "SELECT at FROM linkedin_activity WHERE kind=? AND date(at)=date('now')",
                (k,),
            ).fetchall()
            counts[k] = len(rows)
            for (ts,) in rows:
                try:
                    all_times.append(datetime.fromisoformat(ts))
                except (ValueError, TypeError):
                    try:
                        all_times.append(datetime.strptime(ts, "%Y-%m-%d %H:%M:%S"))
                    except ValueError:
                        pass
            if k in gov._INTERACTIVE:
                write_ct += len(rows)
            elif k in (gov.MSG_READ, gov.SEARCH, gov.PASSIVE):
                read_ct += len(rows)

    # 1. Cercanía a los caps efectivos (writes).
    near = []
    for k in gov._INTERACTIVE:
        cap = gov._effective_daily_cap(k)
        if cap and counts.get(k, 0) >= 0.8 * cap:
            near.append(f"{k} {counts[k]}/{cap}")
    if near:
        score += 25
        reasons.append("cerca del cap diario: " + ", ".join(near))

    # 2. Presupuesto global interactivo.
    global_ct = sum(counts[k] for k in gov._INTERACTIVE)
    if global_ct >= 0.8 * gov.GLOBAL_INTERACTIVE_PER_DAY:
        score += 20
        reasons.append(f"presupuesto global {global_ct}/{gov.GLOBAL_INTERACTIVE_PER_DAY}")

    # 3. Regularidad de timing (gaps casi iguales = mecánico = bot).
    gaps = _gaps_minutes(all_times)
    if len(gaps) >= 4:
        mean = statistics.mean(gaps)
        cv = (statistics.pstdev(gaps) / mean) if mean else 1.0
        if cv < 0.35:  # muy poca variación → parece script
            score += 30
            reasons.append(f"timing demasiado regular (CV={cv:.2f})")

    # 4. Mezcla de acciones: solo-escritura parece bot especializado.
    if write_ct >= 5 and read_ct == 0:
        score += 20
        reasons.append("solo escrituras, sin lecturas de cobertura (mezcla pobre)")

    score = min(100, score)
    band = "verde" if score < 30 else ("ámbar" if score < 60 else "rojo")
    return {
        "risk_score": score,
        "band": band,
        "reasons": reasons or ["dentro del envelope seguro"],
        "counts_today": counts,
        "writes": write_ct,
        "reads": read_ct,
        "at": datetime.now().isoformat(),
    }


def run_health_check(notify=None) -> Dict:
    """Probe + risk_report combinados. Si detecta restricción REAL, escala ban."""
    probe = probe_account_status()
    risk = risk_report()
    out = {"probe": probe, "risk": risk}

    if probe["status"] in REAL_BAN_STATES:
        logger.error(f"[health] restricción REAL detectada: {probe}")
        gov.record_ban(
            reason=f"health probe: {probe['status']}",
            status=probe["status"],
            notify=notify,
        )
    elif probe["status"] == SESSION_DEAD:
        # Cookie muerta — NO es ban. Solo avisar para refrescar sesión.
        logger.warning(f"[health] sesión muerta (cookie): {probe['detail']}")
        if notify:
            try:
                notify("🔑 LinkedIn: la sesión (cookie) expiró — refrescar li_at. No es ban.")
            except Exception:
                pass
    elif probe["status"] == RATE_LIMITED:
        logger.warning("[health] HTTP 999 — bajando ritmo")

    if risk["band"] == "rojo":
        logger.warning(f"[health] riesgo ALTO ({risk['risk_score']}): {risk['reasons']}")
        if notify:
            try:
                notify(f"⚠️ LinkedIn riesgo {risk['risk_score']}/100 (rojo): "
                       + "; ".join(risk["reasons"]))
            except Exception:
                pass
    return out


if __name__ == "__main__":
    import json as _json
    print(_json.dumps(run_health_check(), indent=2, ensure_ascii=False, default=str))
