"""
JobSpy tool: busca trabajos en LinkedIn, Indeed, Glassdoor.
Usa cookies de sesión de LinkedIn para búsqueda autenticada.
"""
import hashlib
import json
import os
from typing import List, Dict, Any, Optional
from loguru import logger

try:
    from jobspy import scrape_jobs
    JOBSPY_AVAILABLE = True
except ImportError:
    JOBSPY_AVAILABLE = False
    logger.warning("jobspy no instalado. Ejecuta: pip install python-jobspy")

from config import settings


def _load_linkedin_cookies() -> Dict[str, str]:
    """Carga cookies de sesión de LinkedIn."""
    cookies_file = settings.linkedin_cookies_file if hasattr(settings, 'linkedin_cookies_file') else "config/linkedin_cookies.json"
    if os.path.exists(cookies_file):
        with open(cookies_file, "r") as f:
            return json.load(f)
    return {}


def search_jobs(
    search_term: str,
    location: str = "remote",
    results_wanted: int = 20,
    hours_old: int = 72,
    site_names: Optional[List[str]] = None,
    easy_apply_only: bool = False,
) -> List[Dict[str, Any]]:
    """
    Busca trabajos usando JobSpy con sesión autenticada de LinkedIn.

    Args:
        search_term: Keywords de búsqueda
        location: Ubicación (ciudad, país, "remote")
        results_wanted: Cantidad de resultados por sitio
        hours_old: Solo trabajos publicados en las últimas N horas
        site_names: Lista de sitios ["linkedin", "indeed", "glassdoor"]
        easy_apply_only: Solo trabajos con Easy Apply en LinkedIn

    Returns:
        Lista de jobs formateados
    """
    if not JOBSPY_AVAILABLE:
        logger.error("jobspy no disponible")
        return []

    if site_names is None:
        site_names = ["linkedin", "indeed", "glassdoor"]

    cookies = _load_linkedin_cookies()
    li_at = cookies.get("li_at", "")

    logger.info(
        f"Buscando '{search_term}' en {location} "
        f"(sitios: {site_names}, autenticado: {bool(li_at)})"
    )

    try:
        kwargs = dict(
            site_name=site_names,
            search_term=search_term,
            location=location,
            results_wanted=results_wanted,
            hours_old=hours_old,
            linkedin_fetch_description=True,
        )

        # Usar cookies de LinkedIn si están disponibles
        if li_at:
            kwargs["linkedin_cookie"] = li_at

        # Filtrar solo Easy Apply si se solicita
        if easy_apply_only and "linkedin" in site_names:
            kwargs["easy_apply"] = True

        jobs_df = scrape_jobs(**kwargs)

        if jobs_df is None or jobs_df.empty:
            logger.info("No se encontraron trabajos")
            return []

        jobs = []
        for _, row in jobs_df.iterrows():
            job_id = _generate_job_id(row)

            # vacancy_count: número de aplicantes reportado por LinkedIn Premium
            vacancy_count = row.get("vacancy_count", None)
            try:
                vacancy_count = int(vacancy_count) if vacancy_count and str(vacancy_count) not in ["nan", "None", ""] else None
            except Exception:
                vacancy_count = None

            job = {
                "id": job_id,
                "title": str(row.get("title", "")),
                "company": str(row.get("company", "")),
                "location": str(row.get("location", "")),
                "description": str(row.get("description", ""))[:3000],
                "url": str(row.get("job_url", "")),
                "salary": _extract_salary(row),
                "source": str(row.get("site", "")),
                "job_type": str(row.get("job_type", "")),
                "date_posted": str(row.get("date_posted", "")),
                "easy_apply": bool(row.get("is_remote", False)),
                "emails_in_job": str(row.get("emails", "")),
                "company_url": str(row.get("company_url", "")),
                "applicants": vacancy_count,
                "skills": str(row.get("skills", "")),
                "job_level": str(row.get("job_level", "")),
                "company_industry": str(row.get("company_industry", "")),
            }
            jobs.append(job)

        # Ordenar: primero los que tienen pocos applicantes (LinkedIn Premium data)
        jobs_with_count = [j for j in jobs if j.get("applicants") is not None]
        jobs_without = [j for j in jobs if j.get("applicants") is None]
        jobs_with_count.sort(key=lambda x: x["applicants"])
        jobs = jobs_with_count + jobs_without

        few_applicants = [j for j in jobs_with_count if j["applicants"] < 50]
        if few_applicants:
            logger.info(f"  → {len(few_applicants)} jobs con <50 applicantes (oportunidad alta)")

        logger.success(f"Encontrados {len(jobs)} trabajos para '{search_term}'")
        return jobs

    except Exception as e:
        logger.error(f"Error en búsqueda de jobs: {e}")
        return []


def _generate_job_id(row) -> str:
    raw = f"{row.get('title', '')}{row.get('company', '')}{row.get('job_url', '')}"
    return hashlib.md5(raw.encode()).hexdigest()[:16]


def _extract_salary(row) -> str:
    min_sal = row.get("min_amount", "")
    max_sal = row.get("max_amount", "")
    currency = row.get("currency", "")
    interval = row.get("pay_period", "")
    if min_sal and max_sal:
        return f"{currency} {min_sal}-{max_sal} {interval}".strip()
    elif min_sal:
        return f"{currency} {min_sal}+ {interval}".strip()
    return ""
