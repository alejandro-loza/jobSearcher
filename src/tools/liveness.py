"""
Ghost posting detection — detecta si un job posting está muerto antes de
desperdiciar tokens generando cover letters / evaluaciones.

Port de career-ops/liveness-core.mjs adaptado al paradigma de jobSearcher:
- clasifica un posting como 'active' / 'expired' / 'uncertain'
- detecta red flags en el título + descripción sin necesidad de fetch HTTP
- opcionalmente hace fetch para verificación profunda
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal, Optional

import httpx
from loguru import logger

LivenessResult = Literal["active", "expired", "uncertain"]

HARD_EXPIRED_PATTERNS = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"job (is )?no longer available",
        r"job.*no longer open",
        r"position has been filled",
        r"this job has expired",
        r"job posting has expired",
        r"no longer accepting applications",
        r"this (position|role|job) (is )?no longer",
        r"this job (listing )?is closed",
        r"job (listing )?not found",
        r"the page you are looking for doesn.t exist",
        # es
        r"esta (oferta|vacante|posición) (ya no|no) está disponible",
        r"esta oferta ha (expirado|caducado|finalizado)",
        r"(vacante|plaza) (cubierta|cerrada)",
        # de/fr
        r"diese stelle (ist )?(nicht mehr|bereits) besetzt",
        r"offre (expirée|n'est plus disponible)",
    ]
]

LISTING_PAGE_PATTERNS = [
    re.compile(p, re.IGNORECASE)
    for p in [r"\d+\s+jobs?\s+found", r"search for jobs page is loaded"]
]

EXPIRED_URL_PATTERNS = [re.compile(r"[?&]error=true", re.IGNORECASE)]

APPLY_PATTERNS = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"\bapply\b",
        r"\bsolicitar\b",
        r"\baplicar\b",
        r"\bpostular\b",
        r"submit application",
        r"easy apply",
        r"start application",
    ]
]

# Red flags en título que sugieren posting falso/ghost
TITLE_RED_FLAGS = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"^[\*\-\s]*$",  # título vacío
        r"multiple (roles|positions)",
        r"various (roles|positions)",
        r"general application",
        r"talent (pool|pipeline|community)",
        r"future opportunities",
        r"join our talent",
    ]
]

MIN_CONTENT_CHARS = 300


@dataclass
class LivenessCheck:
    result: LivenessResult
    reason: str
    score: int  # 0-100, confianza de que está activo


def _first_match(patterns, text: str) -> Optional[re.Pattern]:
    if not text:
        return None
    for p in patterns:
        if p.search(text):
            return p
    return None


def classify_job(
    title: str = "",
    description: str = "",
    url: str = "",
    num_applicants: Optional[int] = None,
    days_posted: Optional[int] = None,
) -> LivenessCheck:
    """
    Clasifica un job posting SIN hacer HTTP. Usa solo el texto/metadata que ya
    tenemos de JobSpy o del scanner.

    Returns:
        LivenessCheck con result, reason y score de confianza (0-100).
    """
    # URL con error
    if url and _first_match(EXPIRED_URL_PATTERNS, url):
        return LivenessCheck("expired", f"URL marcada como error: {url}", 0)

    # Descripción indica que ya no está disponible
    body_match = _first_match(HARD_EXPIRED_PATTERNS, description)
    if body_match:
        return LivenessCheck(
            "expired", f"descripción indica posting cerrado: {body_match.pattern}", 0
        )

    # Página de listado (no un job real)
    if _first_match(LISTING_PAGE_PATTERNS, description):
        return LivenessCheck("expired", "página de listado, no un posting individual", 0)

    # Título sospechoso
    title_match = _first_match(TITLE_RED_FLAGS, title or "")
    if title_match:
        return LivenessCheck(
            "uncertain",
            f"título genérico/ghost: {title_match.pattern}",
            30,
        )

    # Descripción muy corta
    if description and len(description.strip()) < MIN_CONTENT_CHARS:
        return LivenessCheck(
            "uncertain",
            f"descripción muy corta ({len(description)} chars) — posible posting incompleto",
            40,
        )

    # Posting muy viejo con muchos aplicantes = probable ghost
    if days_posted is not None and days_posted > 60:
        return LivenessCheck(
            "uncertain", f"posting de hace {days_posted} días — probable ghost", 35
        )

    # Señal positiva: menciona apply explícito
    if _first_match(APPLY_PATTERNS, description):
        score = 90
        if num_applicants is not None and num_applicants > 500:
            score = 70  # mucho aplicante = mucha competencia pero posting vivo
        return LivenessCheck("active", "apply control detectado en descripción", score)

    # Default: incierto pero con contenido razonable
    return LivenessCheck(
        "uncertain", "sin señales claras ni expiración ni apply", 60
    )


def classify_url(url: str, timeout: float = 10.0) -> LivenessCheck:
    """
    Verificación profunda por HTTP. Úsalo ANTES de aplicar a portales externos,
    NO para cada job en búsquedas masivas (cuesta tiempo).

    Returns:
        LivenessCheck — 'expired' si HTTP 404/410 o texto indica cerrado.
    """
    try:
        with httpx.Client(
            timeout=timeout, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"}
        ) as client:
            resp = client.get(url)
    except Exception as e:
        return LivenessCheck("uncertain", f"fetch falló: {e}", 50)

    if resp.status_code in (404, 410):
        return LivenessCheck("expired", f"HTTP {resp.status_code}", 0)

    final_url = str(resp.url)
    if _first_match(EXPIRED_URL_PATTERNS, final_url):
        return LivenessCheck("expired", f"redirect a {final_url}", 0)

    body = resp.text or ""
    body_match = _first_match(HARD_EXPIRED_PATTERNS, body)
    if body_match:
        return LivenessCheck(
            "expired", f"body matched: {body_match.pattern}", 0
        )

    # Busca botón apply en HTML
    if _first_match(APPLY_PATTERNS, body):
        return LivenessCheck("active", "apply control detectado en HTML", 90)

    if _first_match(LISTING_PAGE_PATTERNS, body):
        return LivenessCheck("expired", "página de listado, no posting individual", 0)

    if len(body.strip()) < MIN_CONTENT_CHARS:
        return LivenessCheck(
            "expired", "contenido insuficiente — probable nav/footer", 10
        )

    return LivenessCheck("uncertain", "contenido presente sin apply visible", 55)


def should_skip_job(job: dict, strict: bool = False) -> tuple[bool, str]:
    """
    Helper para integrar en pipelines: decide si saltar un job sin gastar tokens.

    Args:
        job: dict con title, description, url, num_applicants, etc.
        strict: si True, descarta también 'uncertain'. Default False (solo expired).

    Returns:
        (skip, reason)
    """
    check = classify_job(
        title=job.get("title", ""),
        description=job.get("description", ""),
        url=job.get("url", ""),
        num_applicants=job.get("num_applicants"),
        days_posted=job.get("days_posted"),
    )

    if check.result == "expired":
        return True, f"expired: {check.reason}"
    if strict and check.result == "uncertain":
        return True, f"uncertain (strict): {check.reason}"
    return False, check.reason
