#!/usr/bin/env python3
"""
Job Stalker Agent v2 - Persistente

Busca automáticamente nuevas vacantes para Alejandro Hernandez Loza y las guarda en la DB.
Diseñado para ejecutarse regularmente via cron o scheduler.

Uso:
    venv/bin/python src/agents/job_stalker_agent.py
"""

import json
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = str(Path(__file__).parent.parent.parent)
sys.path.insert(0, PROJECT_ROOT)

from src.tools import jobspy_tool
from src.db.tracker import JobTracker
from loguru import logger

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Términos de búsqueda optimizados para el perfil de Alejandro
SEARCH_TERMS = [
    "Java Developer",
    "Spring Boot Developer",
    "Java Spring Boot",
    "Senior Java Engineer",
    "Java Microservices",
    "Backend Java",
    "Desarrollador Java",
    "Ingeniero Java Spring Boot",
]

# Keywords de alto match para el perfil de Alejandro
HIGH_MATCH_KEYWORDS = [
    "java",
    "spring boot",
    "microservices",
    "kubernetes",
    "docker",
    "aws",
    "gcp",
    "cloud",
    "rest",
    "api",
    "senior",
    "lead",
    "principal",
    "architect",
    "full stack",
    "backend",
]

# Keywords a excluir
EXCLUDE_KEYWORDS = [
    "junior",
    "intern",
    "entry level",
    "assistant",
    "trainee",
    "python developer",
    "python engineer",
    "javascript only",
    "react only",
    "frontend only",
    "data scientist",
    "machine learning",
    "data analyst",
    "product manager",
    "project manager",
    # Modalidades que no aplican al piso salarial actual
    "honorarios",
    "freelance",
    "por hora",
]

# Piso salarial vigente: $60,000 MXN 100% nómina (basado en oferta IDS 2026-06)
SALARY_FLOOR_MXN = 60_000

# Ubicaciones a priorizar
PRIORITY_LOCATIONS = ["Remote", "United States", "Mexico"]

# Empresas top-tier para bonus en scoring
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

# Parámetros de búsqueda
MAX_RESULTS_PER_SEARCH = 40
SEARCH_HOURS_OLD = 168  # Últimas 168h (7 días) para no perder vacantes
MIN_SCORE_TO_SAVE = 65  # Guardar con score >= 65% (el application_agent filtra >= 75%)

# ---------------------------------------------------------------------------
# Scoring Functions
# ---------------------------------------------------------------------------


def calculate_base_score(job: dict) -> int:
    """
    Calcula score básico sin usar LLM.
    Fórmula: 50 + (high_match_keywords × 5) + bonuses
    """
    title = job.get("title", "").lower()
    description = job.get("description", "").lower()
    company = job.get("company", "")

    # Contar keywords de alto match
    high_match_count = sum(
        1 for kw in HIGH_MATCH_KEYWORDS if kw in title or kw in description
    )

    # Score base
    base_score = 50 + (high_match_count * 5)

    # Bonus por empresa top-tier
    if any(top in company for top in TOP_TIER_COMPANIES):
        base_score += 10

    # Bonus por título senior
    senior_keywords = ["senior", "lead", "principal", "architect", "staff"]
    if any(senior in title for senior in senior_keywords):
        base_score += 10

    # Cap score at 95
    return min(base_score, 95)


def should_exclude_job(job: dict) -> bool:
    """
    Verifica si el job debe ser excluido por keywords no deseados o salario bajo el piso.
    Piso actual: $60,000 MXN nómina formal (actualizado 2026-06 por oferta IDS).
    """
    title = job.get("title", "").lower()
    description = job.get("description", "").lower()

    exclude_count = sum(
        1 for kw in EXCLUDE_KEYWORDS if kw in title or kw in description
    )
    if exclude_count > 0:
        return True

    # Excluir si JobSpy devuelve salario estructurado bajo el piso
    max_salary = job.get("max_salary") or 0
    min_salary = job.get("min_salary") or 0
    if max_salary and max_salary < SALARY_FLOOR_MXN:
        return True
    if min_salary and max_salary == 0 and min_salary < 45_000:
        return True

    return False


# ---------------------------------------------------------------------------
# Main Stalker Function
# ---------------------------------------------------------------------------


def run_stalker_search():
    """
    Ejecuta búsqueda de jobs usando JobSpy y guarda en DB.
    """
    logger.info("[stalker] Iniciando Job Stalker Agent v2")

    tracker = JobTracker()
    all_jobs = []
    jobs_filtered = 0
    jobs_saved = 0

    # Ejecutar búsquedas
    for term in SEARCH_TERMS:  # Buscar todos los términos
        logger.info(f"[stalker] Buscando: '{term}' en Remote")

        try:
            jobs = jobspy_tool.search_jobs(
                search_term=term,
                location="Mexico",
                results_wanted=MAX_RESULTS_PER_SEARCH,
                hours_old=SEARCH_HOURS_OLD,
                site_names=["linkedin", "indeed"],
            )

            logger.info(f"[stalker] Encontrados: {len(jobs)} jobs")

            for job in jobs:
                title = job.get("title", "")
                company = job.get("company", "")

                # Excluir jobs no relevantes
                if should_exclude_job(job):
                    jobs_filtered += 1
                    continue

                # Calcular score
                score = calculate_base_score(job)

                # Solo guardar si score >= mínimo
                if score >= MIN_SCORE_TO_SAVE:
                    # Guardar en DB
                    is_new = tracker.save_job(
                        {
                            "id": job.get("id", str(hash(job.get("url", "")))),
                            "title": title,
                            "company": company,
                            "location": job.get("location", ""),
                            "description": job.get("description", ""),
                            "url": job.get("url", ""),
                            "salary": job.get("salary", ""),
                            "source": job.get("source", ""),
                            "match_score": score,
                        }
                    )

                    if is_new:
                        jobs_saved += 1

                    all_jobs.append(
                        {
                            "title": title,
                            "company": company,
                            "location": job.get("location", ""),
                            "score": score,
                            "url": job.get("url", ""),
                            "salary": job.get("salary", ""),
                        }
                    )

            logger.info(
                f"[stalker] Filtrados: {jobs_filtered}, Nuevos guardados: {jobs_saved}"
            )

        except Exception as e:
            logger.error(f"[stalker] Error buscando '{term}': {e}")
            continue

    # Filtrar jobs con score >= 75%
    high_score_jobs = [j for j in all_jobs if j["score"] >= 75]

    # Guardar reporte
    report = {
        "search_terms": SEARCH_TERMS[:5],
        "total_evaluated": len(all_jobs),
        "total_filtered": jobs_filtered,
        "jobs_saved": jobs_saved,
        "high_score_count": len(high_score_jobs),
        "high_score_jobs": high_score_jobs,
    }

    with open("data/stalker_latest_run.json", "w") as f:
        json.dump(report, f, indent=2)

    # Resumen
    logger.success(f"[stalker] === RESULTADO FINAL ===")
    logger.success(f"[stalker] Jobs evaluados: {len(all_jobs)}")
    logger.success(f"[stalker] Jobs filtrados: {jobs_filtered}")
    logger.success(f"[stalker] Jobs nuevos guardados: {jobs_saved}")
    logger.success(f"[stalker] Jobs con score >= 75%: {len(high_score_jobs)}")
    logger.info(f"[stalker] Reporte guardado en data/stalker_latest_run.json")

    return report


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    try:
        report = run_stalker_search()
        print("\n" + "=" * 60)
        print("📊 RESULTADO DEL JOB STALKER AGENT")
        print("=" * 60)
        print(f"   Jobs evaluados: {report['total_evaluated']}")
        print(f"   Jobs filtrados: {report['total_filtered']}")
        print(f"   Jobs nuevos guardados: {report['jobs_saved']}")
        print(f"   Jobs con score >= 75%: {report['high_score_count']}")
        print("=" * 60)

        if report["high_score_count"] > 0:
            print(f"\n🎯 TOP 5 VACANTES (Score >= 75%):")
            sorted_jobs = sorted(
                report["high_score_jobs"], key=lambda x: x["score"], reverse=True
            )
            for i, job in enumerate(sorted_jobs[:5], 1):
                print(
                    f"   {i}. {job['title'][:50]} @ {job['company'][:30]} | Score: {job['score']}%"
                )
                if job["salary"] and job["salary"] != "nan nan-nan":
                    print(f"      Salario: {job['salary']}")
        else:
            print("\nℹ️ No se encontraron nuevas vacantes con score >= 75%")

        sys.exit(0)

    except Exception as e:
        logger.error(f"[stalker] Error fatal: {e}")
        sys.exit(1)
