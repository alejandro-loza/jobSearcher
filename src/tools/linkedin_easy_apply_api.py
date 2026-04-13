"""
LinkedIn Easy Apply via Voyager API.

Submite solicitudes de Easy Apply directamente por HTTP sin usar browser,
evitando la detección de bots en las páginas de jobs.

Requiere: li_at, JSESSIONID, bcookie frescos en config/linkedin_cookies.json
"""
import json
import time
from pathlib import Path
from typing import Dict, Any, Optional, List

import requests
from loguru import logger

from config import settings


# ---------------------------------------------------------------------------
# Session setup
# ---------------------------------------------------------------------------

def _build_api_session() -> requests.Session:
    """Construye una sesión HTTP autenticada para la Voyager API."""
    cookies = {}
    try:
        with open(settings.linkedin_cookies_file) as f:
            raw = json.load(f)
        cookies = raw if isinstance(raw, dict) else {}
    except Exception as e:
        logger.error(f"[li_api] Error cargando cookies: {e}")

    li_at = cookies.get("li_at", "")
    jsessionid = cookies.get("JSESSIONID", "").replace('"', '')
    bcookie = cookies.get("bcookie", "").replace('"', '')

    session = requests.Session()
    session.cookies.set("li_at", li_at, domain=".linkedin.com")
    session.cookies.set("JSESSIONID", f'"{jsessionid}"', domain=".www.linkedin.com")
    if bcookie:
        session.cookies.set("bcookie", f'"{bcookie}"', domain=".linkedin.com")

    session.headers.update({
        "csrf-token": jsessionid,
        "x-restli-protocol-version": "2.0.0",
        "x-li-lang": "en_US",
        "x-li-track": '{"clientVersion":"1.13.1768","osName":"web","timezoneOffset":-6}',
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "application/vnd.linkedin.normalized+json+2.1",
        "Accept-Language": "en-US,en;q=0.9,es;q=0.8",
        "Referer": "https://www.linkedin.com/jobs/",
        "Origin": "https://www.linkedin.com",
    })
    return session


def _check_session(session: requests.Session) -> bool:
    """Verifica que la sesión está autenticada."""
    try:
        r = session.get(
            "https://www.linkedin.com/voyager/api/me",
            timeout=10,
            allow_redirects=False,
        )
        if r.status_code == 200:
            logger.debug("[li_api] Sesión autenticada OK")
            return True
        logger.warning(f"[li_api] Sesión no autenticada: {r.status_code}")
        return False
    except Exception as e:
        logger.error(f"[li_api] Error verificando sesión: {e}")
        return False


# ---------------------------------------------------------------------------
# Job info
# ---------------------------------------------------------------------------

def _extract_job_id(job_url: str) -> Optional[str]:
    """Extrae el ID numérico del job de la URL de LinkedIn."""
    import re
    m = re.search(r"/jobs/view/(\d+)", job_url)
    return m.group(1) if m else None


def get_job_details(session: requests.Session, job_id: str) -> Optional[Dict]:
    """Obtiene los detalles de un job posting."""
    try:
        r = session.get(
            f"https://www.linkedin.com/voyager/api/jobs/jobPostings/{job_id}",
            timeout=15,
            allow_redirects=False,
        )
        if r.status_code == 200:
            return r.json()
        logger.warning(f"[li_api] Job {job_id} retornó {r.status_code}")
        return None
    except Exception as e:
        logger.error(f"[li_api] Error obteniendo job {job_id}: {e}")
        return None


def is_easy_apply(session: requests.Session, job_id: str) -> bool:
    """Verifica si el job tiene Easy Apply habilitado."""
    try:
        r = session.get(
            "https://www.linkedin.com/voyager/api/jobs/jobPostings",
            params={"ids": f"List(urn%3Ali%3AjobPosting%3A{job_id})"},
            timeout=15,
            allow_redirects=False,
        )
        if r.status_code == 200:
            data = r.json()
            # Buscar applyMethod en los datos
            for item in data.get("results", {}).values():
                apply_method = item.get("applyMethod", {})
                if "easyApplyUrl" in apply_method or apply_method.get("com.linkedin.voyager.jobs.NormalApplyV2"):
                    return True
                if apply_method.get("com.linkedin.voyager.jobs.OffsiteApply"):
                    return False
        return False
    except Exception as e:
        logger.debug(f"[li_api] Error verificando easy apply: {e}")
        return False


# ---------------------------------------------------------------------------
# Resume upload
# ---------------------------------------------------------------------------

def upload_resume(session: requests.Session, cv_path: str) -> Optional[str]:
    """
    Sube el CV PDF a LinkedIn y retorna el upload ID.
    Usa el endpoint de media upload de LinkedIn.
    """
    try:
        cv_file = Path(cv_path)
        if not cv_file.exists():
            logger.error(f"[li_api] CV no encontrado: {cv_path}")
            return None

        # Inicializar upload
        init_r = session.post(
            "https://www.linkedin.com/voyager/api/jobs/jobApplicationFileUploads",
            json={
                "fileType": "RESUME",
                "filename": cv_file.name,
            },
            timeout=15,
            allow_redirects=False,
        )

        if init_r.status_code not in (200, 201):
            logger.warning(f"[li_api] Upload init retornó {init_r.status_code}: {init_r.text[:200]}")
            return None

        upload_data = init_r.json()
        upload_url = upload_data.get("value", {}).get("uploadUrl", "")
        upload_id = upload_data.get("value", {}).get("id", "")

        if not upload_url or not upload_id:
            logger.warning(f"[li_api] No se obtuvo upload URL/ID: {upload_data}")
            return None

        # Subir el archivo
        with open(cv_path, "rb") as f:
            file_r = requests.put(
                upload_url,
                data=f.read(),
                headers={"Content-Type": "application/pdf"},
                timeout=30,
            )

        if file_r.status_code in (200, 201, 204):
            logger.info(f"[li_api] CV subido exitosamente: {upload_id}")
            return upload_id
        else:
            logger.warning(f"[li_api] Upload de archivo retornó {file_r.status_code}")
            return None

    except Exception as e:
        logger.error(f"[li_api] Error subiendo CV: {e}")
        return None


# ---------------------------------------------------------------------------
# Application form questions
# ---------------------------------------------------------------------------

def get_application_form(session: requests.Session, job_id: str) -> Optional[Dict]:
    """Obtiene las preguntas del formulario de Easy Apply."""
    try:
        r = session.get(
            f"https://www.linkedin.com/voyager/api/jobs/jobApplicationQuestions/{job_id}",
            timeout=15,
            allow_redirects=False,
        )
        if r.status_code == 200:
            return r.json()
        logger.debug(f"[li_api] Form questions retornó {r.status_code}")
        return None
    except Exception as e:
        logger.debug(f"[li_api] Error obteniendo form questions: {e}")
        return None


def _build_answers(form_data: Optional[Dict], resume: Dict) -> List[Dict]:
    """Genera respuestas automáticas para las preguntas del formulario."""
    answers = []
    if not form_data:
        return answers

    p = resume.get("personal", resume)

    question_defaults = {
        "phone": p.get("phone", "+525641446948"),
        "email": p.get("email", "alejandrohloza@gmail.com"),
        "years_experience": "12",
        "work_authorization": "Yes",
        "sponsorship": "No",  # Para trabajos en México no necesita visa
        "salary": "Negotiable",
        "start_date": "Immediately",
        "remote": "Yes",
        "relocate": "No",
    }

    questions = form_data.get("elements", form_data.get("questions", []))
    for q in questions:
        q_type = q.get("type", "")
        q_label = q.get("label", q.get("question", "")).lower()
        q_id = q.get("id", q.get("questionId", ""))

        answer_val = None

        if "phone" in q_label or "teléfono" in q_label:
            answer_val = question_defaults["phone"]
        elif "year" in q_label and "experience" in q_label:
            answer_val = question_defaults["years_experience"]
        elif "authorized" in q_label or "work permit" in q_label:
            answer_val = question_defaults["work_authorization"]
        elif "sponsor" in q_label or "visa" in q_label:
            answer_val = question_defaults["sponsorship"]
        elif "salary" in q_label or "compensation" in q_label:
            answer_val = question_defaults["salary"]
        elif "start" in q_label and "date" in q_label:
            answer_val = question_defaults["start_date"]
        elif "remote" in q_label:
            answer_val = question_defaults["remote"]
        elif "reloc" in q_label:
            answer_val = question_defaults["relocate"]

        if answer_val and q_id:
            answers.append({
                "questionId": q_id,
                "answer": answer_val,
                "type": q_type,
            })

    return answers


# ---------------------------------------------------------------------------
# Submit application
# ---------------------------------------------------------------------------

def submit_easy_apply(
    job_url: str,
    resume: Dict,
    cover_letter: str = "",
) -> Dict[str, Any]:
    """
    Submite una solicitud de Easy Apply via Voyager API.

    Args:
        job_url: URL del job en LinkedIn (linkedin.com/jobs/view/ID)
        resume: Datos del CV (data/resume.json)
        cover_letter: Texto de la cover letter (opcional)

    Returns:
        Dict con: success, status, message
    """
    job_id = _extract_job_id(job_url)
    if not job_id:
        return {"success": False, "status": "error", "message": f"No se pudo extraer job ID de: {job_url}"}

    session = _build_api_session()

    # Verificar sesión
    if not _check_session(session):
        return {"success": False, "status": "auth_failed", "message": "Cookie de LinkedIn expirada o inválida"}

    logger.info(f"[li_api] Iniciando Easy Apply para job {job_id}")

    # Obtener detalles del job
    job_details = get_job_details(session, job_id)
    if not job_details:
        return {"success": False, "status": "error", "message": f"No se pudo obtener detalles del job {job_id}"}

    # Obtener preguntas del formulario
    form_data = get_application_form(session, job_id)
    answers = _build_answers(form_data, resume)

    # Subir CV
    cv_path = "data/cv_alejandro_en.pdf"
    resume_upload_id = upload_resume(session, cv_path)
    if resume_upload_id:
        logger.info(f"[li_api] CV subido: {resume_upload_id}")

    # Construir payload de la solicitud
    p = resume.get("personal", resume)
    payload = {
        "jobPostingUrn": f"urn:li:jobPosting:{job_id}",
        "contactInfo": {
            "firstName": p.get("name", "Alejandro").split()[0],
            "lastName": " ".join(p.get("name", "Alejandro Hernandez Loza").split()[1:]),
            "emailAddress": p.get("email", "alejandrohloza@gmail.com"),
            "phoneNumber": p.get("phone", "+525641446948").replace(" ", "").replace("+", ""),
            "phoneNumberCountryCode": "MX",
        },
        "followCompany": False,
        "additionalQuestions": answers,
    }

    if resume_upload_id:
        payload["resumeUploadId"] = resume_upload_id

    if cover_letter:
        payload["coverLetter"] = cover_letter[:3000]

    # Intentar POST al endpoint de aplicaciones
    try:
        r = session.post(
            "https://www.linkedin.com/voyager/api/jobs/jobApplications",
            json=payload,
            timeout=30,
            allow_redirects=False,
        )

        logger.info(f"[li_api] POST jobApplications → {r.status_code}")

        if r.status_code in (200, 201):
            logger.success(f"[li_api] Easy Apply exitoso para job {job_id}")
            return {"success": True, "status": "success", "message": f"Easy Apply enviado para job {job_id}"}

        elif r.status_code == 409:
            logger.warning(f"[li_api] Ya aplicaste a este job anteriormente: {job_id}")
            return {"success": False, "status": "already_applied", "message": "Ya aplicaste a este job"}

        elif r.status_code in (401, 403):
            return {"success": False, "status": "auth_failed", "message": "No autorizado — cookie expirada"}

        else:
            body = r.text[:300]
            logger.warning(f"[li_api] Respuesta inesperada {r.status_code}: {body}")
            return {
                "success": False,
                "status": f"api_error_{r.status_code}",
                "message": f"API retornó {r.status_code}: {body}",
            }

    except Exception as e:
        logger.error(f"[li_api] Error en POST jobApplications: {e}")
        return {"success": False, "status": "error", "message": str(e)}
