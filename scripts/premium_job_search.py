#!/usr/bin/env python3
"""
Premium Job Search — busca los mejores empleos para Alejandro.
Evalúa con CV completo, notifica por WhatsApp las mejores oportunidades.
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from src.agents import master_agent
from src.db.tracker import JobTracker
from src.tools import jobspy_tool, whatsapp_tool

# Términos de búsqueda que cubren todo el perfil
PREMIUM_SEARCHES = [
    # Java core
    {"term": "Senior Java Developer", "location": "remote"},
    {"term": "Sr Java Spring Boot Developer", "location": "remote"},
    {"term": "Senior Backend Engineer Java", "location": "remote"},
    {"term": "Java Microservices Architect", "location": "remote"},
    # Groovy / Grails
    {"term": "Groovy Developer Senior", "location": "remote"},
    {"term": "Grails Developer Senior", "location": "remote"},
    # AI / LLM backend
    {"term": "Backend Engineer LLM AI", "location": "remote"},
    {"term": "AI Software Engineer Java", "location": "remote"},
    {"term": "LLM Integration Engineer", "location": "remote"},
    # Full Stack
    {"term": "Full Stack Java Senior Engineer", "location": "remote"},
    {"term": "Sr Full Stack Developer Java", "location": "Mexico City"},
    # Cloud / Microservices
    {"term": "Cloud Java Engineer Senior", "location": "remote"},
    {"term": "Microservices Java Developer", "location": "remote"},
    # Tech Lead
    {"term": "Tech Lead Java Backend", "location": "remote"},
    {"term": "Staff Engineer Java Backend", "location": "remote"},
]

PREMIUM_SCORE_THRESHOLD = 82  # Solo los mejores
SEEN_URLS = set()


def run_premium_search():
    resume = json.load(open("data/resume.json"))
    tracker = JobTracker()
    premium_jobs = []

    logger.info(f"🔍 Iniciando búsqueda premium — {len(PREMIUM_SEARCHES)} términos")

    for search in PREMIUM_SEARCHES:
        term = search["term"]
        loc = search["location"]
        logger.info(f"  Buscando: '{term}' en {loc}...")

        try:
            jobs = jobspy_tool.search_jobs(
                search_term=term,
                location=loc,
                results_wanted=20,
                hours_old=72,  # últimas 72h = 3 días (frescos)
                site_names=["linkedin", "indeed", "glassdoor"],
                easy_apply_only=False,
            )
        except Exception as e:
            logger.error(f"  Error buscando '{term}': {e}")
            continue

        logger.info(f"  → {len(jobs)} resultados")

        for job in jobs:
            url = job.get("url", "")
            if not url or url in SEEN_URLS:
                continue
            SEEN_URLS.add(url)

            # Evaluar match
            try:
                score, reasons = master_agent.evaluate_job_match(job, resume)
                job["match_score"] = score
                job["match_reasons"] = reasons
            except Exception as e:
                logger.error(f"  Error evaluando {job.get('title','')}: {e}")
                continue

            if score >= PREMIUM_SCORE_THRESHOLD:
                premium_jobs.append(job)
                logger.info(
                    f"  ⭐ PREMIUM ({score}%): {job.get('title','')} @ {job.get('company','')} — {job.get('location','')}"
                )

            # Guardar en DB siempre si >= 75
            if score >= 75:
                try:
                    tracker.save_job(
                        job_id=job.get("id", url),
                        title=job.get("title", ""),
                        company=job.get("company", ""),
                        location=job.get("location", ""),
                        url=url,
                        description=job.get("description", ""),
                        match_score=score,
                        source=job.get("source", "jobspy"),
                        easy_apply=job.get("easy_apply", False),
                    )
                except Exception:
                    pass

            time.sleep(0.2)

        time.sleep(2)  # pausa entre búsquedas para no sobrecargar

    # Ordenar por score
    premium_jobs.sort(key=lambda x: x.get("match_score", 0), reverse=True)

    logger.info(f"\n✅ Búsqueda premium completa: {len(premium_jobs)} trabajos premium encontrados")

    if not premium_jobs:
        whatsapp_tool.send_message(
            "🔍 Búsqueda premium completada. No se encontraron nuevos trabajos con score >= 82% esta vez. Intenta de nuevo mañana."
        )
        return

    # Preparar reporte WhatsApp
    top = premium_jobs[:10]  # máximo 10 en WhatsApp
    lines = [f"⭐ *Búsqueda Premium — {len(premium_jobs)} trabajos top encontrados*\n"]
    for i, j in enumerate(top, 1):
        score = j.get("match_score", 0)
        title = j.get("title", "")[:40]
        company = j.get("company", "")[:30]
        loc = j.get("location", "")[:25]
        url = j.get("url", "N/A")
        easy = " 🟢 Easy Apply" if j.get("easy_apply") else ""
        lines.append(f"{i}. *{title}*\n   {company} | {loc}\n   Score: {score}%{easy}\n   {url}\n")

    if len(premium_jobs) > 10:
        lines.append(f"_...y {len(premium_jobs) - 10} más en la DB_")

    lines.append("\n💡 Aplica manualmente a los que te interesen. ¡Estos son los mejores match!")

    msg = "\n".join(lines)
    whatsapp_tool.send_message(msg)
    logger.info("📱 Notificación WhatsApp enviada")

    # Guardar reporte en archivo
    report_path = "data/premium_jobs_report.json"
    with open(report_path, "w") as f:
        json.dump(premium_jobs, f, ensure_ascii=False, indent=2)
    logger.info(f"📄 Reporte guardado en {report_path}")


if __name__ == "__main__":
    run_premium_search()
