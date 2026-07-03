#!/usr/bin/env python3
"""
Job Discovery Agent v2 - Búsqueda complementaria y desfasada

Busca empleos adicionales a los del Job Stalker principal.
Se ejecuta en horarios diferentes para distribuir la carga del sistema.
- Ejecuta cada hora pero desfasado 30 minutos
- Términos de búsqueda complementarios
- Prioriza empresas no trackingeadas por el stalker principal
"""
import json
import re
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from loguru import logger

# Add project root to path
PROJECT_ROOT = str(Path(__file__).parent.parent.parent)
sys.path.insert(0, PROJECT_ROOT)

from src.tools import jobspy_tool
from src.db.tracker import JobTracker
from src.agents import master_agent

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Términos de búsqueda complementarios (diferentes a job_stalker_agent)
DISCOVERY_SEARCH_TERMS = [
    # Java / Spring Boot — core
    "Java Spring Boot",
    "Senior Java Developer",
    "Spring Boot Microservices",
    "Java Backend Senior",
    "Desarrollador Java Senior",
    "Ingeniero Java Spring Boot",
    "Java Microservices Developer",
    "Lead Java Engineer",
    # Variantes con tecnologías del stack de Alejandro
    "Java AWS",
    "Java Kubernetes",
    "Java REST API",
    "Spring Boot REST",
    "Java Cloud Engineer",
    # En español
    "Arquitecto Java",
    "Líder Técnico Java Spring",
    "Desarrollador Backend Java Spring Boot",
    "Ingeniero Software Senior Java",
]

# Empresas top-tier adicionales (complemento a las del job_stalker)
TOP_TIER_COMPANIES = [
    "Google", "Microsoft", "Amazon", "AWS", "Apple", "Meta", "Netflix", "NVIDIA", "Adobe", 
    "Salesforce", "Oracle", "IBM", "Cisco", "LinkedIn", "Intel", "SAP",
    "Stripe", "PayPal", "Block", "Square", "Adyen", "Nubank", "Mercado Libre", "Mercado Pago", 
    "Brex", "Revolut", "Bitso", "Robinhood", "Klarna", "Plaid", "Affirm", "Wise", 
    "Checkout.com", "SoFi", "Citadel", "JPMorgan", "Goldman Sachs", "Carta",
    "Snowflake", "Databricks", "Confluent", "Datadog", "HashiCorp", "Cloudflare", "MongoDB", 
    "Elastic", "Okta", "CrowdStrike", "Palo Alto Networks", "Snyk", "GitHub", "DigitalOcean", "Fastly",
    "Atlassian", "Slack", "Zoom", "ServiceNow", "Zendesk", "HubSpot", "Monday.com", "Asana", 
    "DocuSign", "Dropbox", "Pinterest", "Shopify", "Twilio", "Figma", "Canva",
    "Airbnb", "Uber", "Lyft", "Booking.com", "Expedia", "DoorDash", "Instacart", "Rappi", 
    "Kavak", "Jüsto", "Wayfair", "Zalando", "Coupang", "eBay", "Chewy",
    "Spotify", "Disney+", "Warner Bros", "Roku", "Roblox", "Unity", "Epic Games", "Riot Games", 
    "Discord", "Reddit",
    "Clip", "Konfío", "Kueski", "Wizeline", "Globant", "BairesDev", "NTT Data", "Accenture", 
    "Tata Consultancy Services", "TCS", "Capgemini"
]

# Ubicaciones complementarias
DISCOVERY_LOCATIONS = [
    "Ciudad de Mexico",
    "CDMX",
]

# Sitios para búsqueda complementaria
DISCOVERY_SITES = ["linkedin", "indeed"]

# Parámetros de búsqueda
MAX_RESULTS_PER_SEARCH = 40
HOURS_OLD = 168  # Últimas 7 días
MATCH_THRESHOLD = 65  # application_agent filtra >= 75%, aquí somos permisivos

# Log de discovery para evitar duplicados
DISCOVERY_LOG_FILE = "data/job_discovery_log.json"


# ---------------------------------------------------------------------------
# Log helpers
# ---------------------------------------------------------------------------

def _load_log() -> dict:
    try:
        with open(DISCOVERY_LOG_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {
            "discovered_jobs": {},      # job_id -> {title, score, first_seen}
            "last_search_time": None,
            "search_count": 0,
            "unique_companies": set(),
            "stats": {
                "total_discovered": 0,
                "high_match": 0,
                "medium_match": 0,
                "low_match": 0,
            }
        }


def _save_log(log: dict):
    # Convert set to list for JSON serialization
    if isinstance(log.get("unique_companies"), set):
        log["unique_companies"] = list(log["unique_companies"])
    
    with open(DISCOVERY_LOG_FILE, "w") as f:
        json.dump(log, f, indent=2, default=str)


def _load_resume() -> dict:
    try:
        with open("data/resume.json", "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error cargando resume.json: {e}")
        return {}


def _already_discovered(log: dict, job_id: str) -> bool:
    return job_id in log.get("discovered_jobs", {})


def _record_discovery(log: dict, job_id: str, job: dict, score: int):
    log["discovered_jobs"][job_id] = {
        "title": job.get("title", ""),
        "company": job.get("company", ""),
        "location": job.get("location", ""),
        "url": job.get("url", ""),
        "score": score,
        "first_seen": datetime.now().isoformat(),
        "last_seen": datetime.now().isoformat(),
    }
    
    # Track unique companies
    company = job.get("company", "")
    if company and company not in log["unique_companies"]:
        log["unique_companies"].add(company)
    
    # Update stats
    if score >= 80:
        log["stats"]["high_match"] += 1
    elif score >= 70:
        log["stats"]["medium_match"] += 1
    else:
        log["stats"]["low_match"] += 1
    
    log["stats"]["total_discovered"] += 1


# ---------------------------------------------------------------------------
# Matching functions
# ---------------------------------------------------------------------------

def _evaluate_job_match(job: dict, resume: dict) -> tuple[int, str]:
    """
    Evalúa el match entre un job y el CV usando el master agent.
    
    Returns:
        (score, reasons) tuple
    """
    try:
        score, reasons = master_agent.evaluate_job_match(job, resume)
        return score, reasons
    except Exception as e:
        logger.error(f"Error evaluando match: {e}")
        return 0, "Error en evaluación"


def _calculate_bonus_score(job: dict) -> int:
    """
    Calcula puntaje bonus basado en factores adicionales.
    """
    bonus = 0
    
    # Bonus por empresa top-tier
    company = job.get("company", "")
    for top_company in TOP_TIER_COMPANIES:
        if top_company.lower() in company.lower():
            bonus += 10
            break
    
    # Bonus por Easy Apply
    if job.get("easy_apply", False):
        bonus += 5
    
    # Bonus por num_applicants bajo
    num_applicants = job.get("num_applicants", 0)
    if num_applicants and num_applicants < 10:
        bonus += 5
    elif num_applicants and num_applicants < 25:
        bonus += 3
    
    # Bonus por recencia
    hours_old = job.get("hours_old", 999)
    if hours_old < 24:
        bonus += 3
    elif hours_old < 48:
        bonus += 2
    
    return bonus


def _get_final_score(base_score: int, job: dict) -> int:
    """Calcula el score final combinando base + bonus."""
    bonus = _calculate_bonus_score(job)
    final_score = base_score + bonus
    return min(final_score, 100)  # Max 100


# Patrones que indican salario bajo el piso (60k MXN)
_LOW_SALARY_PATTERNS = [
    re.compile(r"\$\s*([\d,]+)\s*(?:MXN|pesos|mxp)?", re.IGNORECASE),
]
_HONORARIOS_PATTERNS = re.compile(
    r"\bhonorarios\b|\bfreelance\b|\bpor hora\b|\bby the hour\b|\bcontractor\b|\bassimilados\b",
    re.IGNORECASE,
)


def _should_reject_by_salary(job: dict) -> tuple[bool, str]:
    """
    Filtro pre-LLM: descarta jobs cuyo salario explícito está bajo el piso
    ($60,000 MXN nómina) o que son honorarios/freelance.

    Solo rechaza cuando hay evidencia clara — si el salario no aparece,
    deja pasar al LLM para evaluación completa.
    """
    description = (job.get("description") or "") + " " + (job.get("title") or "")
    min_salary = job.get("min_salary") or 0
    max_salary = job.get("max_salary") or 0

    # Rechazar honorarios / freelance explícitos
    if _HONORARIOS_PATTERNS.search(description):
        return True, "honorarios/freelance detectado en descripción"

    # Si JobSpy devuelve salario estructurado y está bajo el piso
    if max_salary and max_salary < 60_000:
        return True, f"salario máximo ${max_salary:,.0f} < $60,000 piso"
    if min_salary and max_salary == 0 and min_salary < 45_000:
        return True, f"salario mínimo ${min_salary:,.0f} muy bajo el piso"

    return False, ""


# ---------------------------------------------------------------------------
# Main discovery function
# ---------------------------------------------------------------------------

def discover_jobs() -> dict:
    """
    Ejecuta búsqueda de empleos complementaria y desfasada.
    
    Returns:
        dict con estadísticas del discovery
    """
    logger.info("[job_discovery] ===== INICIANDO DISCOVERY DE EMPLEOS =====")
    logger.info(f"[job_discovery] Términos de búsqueda: {len(DISCOVERY_SEARCH_TERMS)}")
    logger.info(f"[job_discovery] Ubicaciones: {DISCOVERY_LOCATIONS}")
    logger.info(f"[job_discovery] Empresas top-tier: {len(TOP_TIER_COMPANIES)}")
    
    start_time = datetime.now()
    log = _load_log()
    resume = _load_resume()
    
    if not resume:
        logger.error("[job_discovery] Sin resume.json — abortando")
        return {
            "success": False,
            "error": "No resume disponible"
        }
    
    jobs_discovered = []
    jobs_matched = []
    
    # Buscar con diferentes términos
    for i, term in enumerate(DISCOVERY_SEARCH_TERMS, 1):
        logger.info(f"[job_discovery] Buscando término {i}/{len(DISCOVERY_SEARCH_TERMS)}: {term}")
        
        for location in DISCOVERY_LOCATIONS:
            try:
                jobs = jobspy_tool.search_jobs(
                    search_term=term,
                    location=location,
                    results_wanted=MAX_RESULTS_PER_SEARCH,
                    hours_old=HOURS_OLD,
                    site_names=DISCOVERY_SITES,
                    easy_apply_only=False,  # Include all jobs
                )
                
                for job in jobs:
                    job_id = job.get("id", "")
                    
                    # Skip si ya fue descubierto
                    if _already_discovered(log, job_id):
                        logger.debug(f"[job_discovery] Skip (ya descubierto): {job.get('title')}")
                        continue

                    # Filtro pre-LLM: piso salarial $60k nómina
                    reject, reject_reason = _should_reject_by_salary(job)
                    if reject:
                        logger.debug(f"[job_discovery] Rechazado por salario ({reject_reason}): {job.get('title')}")
                        continue

                    # Evaluar match con CV
                    base_score, reasons = _evaluate_job_match(job, resume)
                    final_score = _get_final_score(base_score, job)
                    
                    # Solo guardar si tiene match razonable
                    if final_score >= MATCH_THRESHOLD:
                        job["match_score"] = final_score
                        job["match_reasons"] = reasons
                        
                        _record_discovery(log, job_id, job, final_score)
                        jobs_matched.append(job)
                        
                        logger.info(
                            f"[job_discovery] MATCH {final_score}%: "
                            f"{job.get('title')} @ {job.get('company')}"
                        )
                    else:
                        jobs_discovered.append(job)
                
                logger.debug(f"[job_discovery] Encontrados {len(jobs)} para {term} en {location}")
                
            except Exception as e:
                logger.warning(f"[job_discovery] Search failed '{term}' en {location}: {e}")
                continue
    
    # Actualizar timestamp
    log["last_search_time"] = datetime.now().isoformat()
    log["search_count"] = log.get("search_count", 0) + 1
    _save_log(log)
    
    # Guardar en DB
    tracker = JobTracker()
    saved_count = 0
    
    for job in jobs_matched:
        try:
            tracker.save_job(job, status="found", match_score=job.get("match_score", 0))
            saved_count += 1
        except Exception as e:
            logger.warning(f"[job_discovery] Error guardando job: {e}")
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    stats = {
        "success": True,
        "jobs_matched": len(jobs_matched),
        "jobs_discovered": len(jobs_discovered),
        "saved_to_db": saved_count,
        "unique_companies": len(log["unique_companies"]),
        "duration_seconds": duration,
        "search_terms_used": len(DISCOVERY_SEARCH_TERMS),
        "high_match": log["stats"]["high_match"],
        "medium_match": log["stats"]["medium_match"],
        "low_match": log["stats"]["low_match"],
        "total_searches": log["search_count"],
    }
    
    logger.success(f"[job_discovery] ===== DISCOVERY COMPLETADO =====")
    logger.success(f"[job_discovery] Jobs con match >= {MATCH_THRESHOLD}%: {stats['jobs_matched']}")
    logger.success(f"[job_discovery] Jobs descubiertos (match < {MATCH_THRESHOLD}%): {stats['jobs_discovered']}")
    logger.success(f"[job_discovery] Duración: {duration:.1f}s")
    logger.success(f"[job_discovery] Empresas únicas descubiertas: {stats['unique_companies']}")
    
    return stats


def get_discovery_stats() -> dict:
    """Retorna estadísticas del discovery."""
    log = _load_log()
    return {
        "last_search_time": log.get("last_search_time"),
        "search_count": log.get("search_count", 0),
        "unique_companies": len(log.get("unique_companies", [])),
        "total_discovered": log.get("stats", {}).get("total_discovered", 0),
        "high_match": log.get("stats", {}).get("high_match", 0),
        "medium_match": log.get("stats", {}).get("medium_match", 0),
        "low_match": log.get("stats", {}).get("low_match", 0),
    }


if __name__ == "__main__":
    stats = discover_jobs()
    print(f"Discovery completado: {stats['jobs_matched']} jobs con match, "
          f"{stats['jobs_discovered']} jobs descubiertos")