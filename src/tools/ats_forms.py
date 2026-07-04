"""
ATS forms — lee la ESTRUCTURA del formulario de aplicación vía API (no visión).

Greenhouse y Ashby exponen las preguntas del formulario por API pública. En vez de
screenshotear y adivinar campo por campo (frágil, caro, hace loop), leemos los
campos de forma determinista: nombre, label, tipo, si es obligatorio y las opciones
de los dropdowns. Con esto el Answerer genera respuestas de una sola vez y el Filler
llena por selector conocido.

Tipos canónicos:
  text | textarea | file | select_single | select_multi
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional

import httpx
from loguru import logger

FETCH_TIMEOUT = 12.0
_UA = "jobSearcher/1.0"


@dataclass
class FormField:
    name: str                      # nombre del input en el DOM / payload
    label: str
    type: str                      # text|textarea|file|select_single|select_multi
    required: bool
    options: List[dict] = field(default_factory=list)  # [{label, value}]
    # Agrupación lógica: Greenhouse duplica "Resume/CV" como file + textarea.
    # group liga ambos para que el Filler suba el archivo y salte el _text.
    group: Optional[str] = None


@dataclass
class ATSForm:
    ats: str                       # greenhouse | ashby
    company: str
    job_title: str
    url: str
    fields: List[FormField]

    def required_fields(self) -> List[FormField]:
        return [f for f in self.fields if f.required]


# ── Greenhouse ────────────────────────────────────────────────────────

_GH_TYPE = {
    "input_text": "text",
    "textarea": "textarea",
    "input_file": "file",
    "multi_value_single_select": "select_single",
    "multi_value_multi_select": "select_multi",
}


def parse_greenhouse_url(url: str) -> Optional[tuple[str, str]]:
    """(board_token, job_id) desde una URL de Greenhouse, o None."""
    # https://job-boards.greenhouse.io/clara/jobs/5150839007
    # https://boards.greenhouse.io/clara/jobs/5150839007
    m = re.search(r"greenhouse\.io/([^/?#]+)/jobs/(\d+)", url)
    if m:
        return m.group(1), m.group(2)
    # Stripe-style: ?gh_jid=123 con token embebido no-estándar → no soportado aquí
    return None


def fetch_greenhouse_form(board_token: str, job_id: str, company: str = "", url: str = "") -> ATSForm:
    api = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs/{job_id}?questions=true"
    with httpx.Client(headers={"User-Agent": _UA}) as client:
        resp = client.get(api, timeout=FETCH_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()

    fields: List[FormField] = []
    for q in data.get("questions", []):
        label = (q.get("label") or "").strip()
        required = bool(q.get("required"))
        # Cada "question" puede tener varios fields (p.ej. Resume = file + textarea).
        group = None
        qfields = q.get("fields", [])
        if len(qfields) > 1:
            group = label.lower()
        for f in qfields:
            gtype = f.get("type", "")
            ctype = _GH_TYPE.get(gtype)
            if not ctype:
                logger.debug(f"[ats_forms] tipo GH desconocido '{gtype}' en '{label}'")
                continue
            options = []
            for v in (f.get("values") or []):
                options.append({"label": str(v.get("label", "")), "value": v.get("value")})
            fields.append(FormField(
                name=f.get("name", ""),
                label=label,
                type=ctype,
                required=required,
                options=options,
                group=group,
            ))

    return ATSForm(
        ats="greenhouse",
        company=company or board_token,
        job_title=data.get("title", ""),
        url=url or api,
        fields=fields,
    )


# ── Ashby ─────────────────────────────────────────────────────────────

def parse_ashby_url(url: str) -> Optional[tuple[str, str]]:
    """(org, jobPostingId) desde una URL de Ashby, o None."""
    # https://jobs.ashbyhq.com/persona/247b0dec-3fe3-41f7-a1b6-76e51cbc8ab5
    m = re.search(r"jobs\.ashbyhq\.com/([^/?#]+)/([0-9a-f-]{16,})", url)
    if m:
        return m.group(1), m.group(2)
    return None


_ASHBY_TYPE = {
    "String": "text",
    "Text": "textarea",
    "File": "file",
    "ValueSelect": "select_single",
    "MultiValueSelect": "select_multi",
    "Boolean": "select_single",
    "Email": "text",
    "Phone": "text",
    "Number": "text",
}


def fetch_ashby_form(org: str, posting_id: str, company: str = "", url: str = "") -> ATSForm:
    """Ashby expone el formulario vía su API pública de job-posting."""
    api = f"https://api.ashbyhq.com/posting-api/job-board/{org}/{posting_id}?includeCompensation=true"
    with httpx.Client(headers={"User-Agent": _UA}) as client:
        resp = client.get(api, timeout=FETCH_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()

    fields: List[FormField] = []
    # Ashby: applicationFormDefinition.sections[].fields[] (cuando está disponible).
    form_def = (data.get("applicationFormDefinition")
                or data.get("applicationForm") or {})
    sections = form_def.get("sections") or []
    for sec in sections:
        for fw in sec.get("fields", []):
            fdef = fw.get("field", fw)
            atype = fdef.get("type", "")
            ctype = _ASHBY_TYPE.get(atype)
            if not ctype:
                continue
            options = []
            for opt in (fdef.get("selectableValues") or fdef.get("options") or []):
                if isinstance(opt, dict):
                    options.append({"label": opt.get("label", opt.get("value", "")),
                                    "value": opt.get("value", opt.get("label"))})
                else:
                    options.append({"label": str(opt), "value": opt})
            if atype == "Boolean" and not options:
                options = [{"label": "Yes", "value": True}, {"label": "No", "value": False}]
            fields.append(FormField(
                name=fdef.get("path") or fdef.get("id") or fdef.get("title", ""),
                label=fdef.get("title") or fdef.get("label", ""),
                type=ctype,
                required=bool(fw.get("isRequired") or fdef.get("isRequired")),
                options=options,
            ))

    return ATSForm(
        ats="ashby",
        company=company or org,
        job_title=data.get("title", ""),
        url=url or api,
        fields=fields,
    )


# ── Dispatch ──────────────────────────────────────────────────────────

def fetch_form(url: str, company: str = "") -> Optional[ATSForm]:
    """Detecta el ATS por la URL y trae la estructura del formulario. None si no soportado."""
    gh = parse_greenhouse_url(url)
    if gh:
        try:
            return fetch_greenhouse_form(gh[0], gh[1], company=company, url=url)
        except Exception as e:
            logger.warning(f"[ats_forms] Greenhouse fetch falló: {e}")
            return None
    ash = parse_ashby_url(url)
    if ash:
        try:
            form = fetch_ashby_form(ash[0], ash[1], company=company, url=url)
            if form.fields:
                return form
            logger.debug("[ats_forms] Ashby sin form definition en API — fallback a visión")
            return None
        except Exception as e:
            logger.warning(f"[ats_forms] Ashby fetch falló: {e}")
            return None
    return None
