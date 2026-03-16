#!/usr/bin/env python3
"""
Classify LinkedIn jobs as Easy Apply vs External, then:
- Easy Apply → re-apply with CV using dedicated handler
- External → save to data/antigravity_jobs.md for Antigravity to handle
"""
import asyncio
import json
import sqlite3
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from config import settings
from playwright.async_api import async_playwright


async def classify_jobs(rows, cookies):
    """Classify all jobs as easy_apply or external in a single browser session."""
    li_at = cookies.get("li_at", "")
    jsessionid = cookies.get("JSESSIONID", "").replace('"', '')

    easy_apply_jobs = []
    external_jobs = []
    closed_jobs = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        )
        await context.add_cookies([
            {"name": "li_at", "value": li_at, "domain": ".linkedin.com", "path": "/"},
            {"name": "JSESSIONID", "value": jsessionid, "domain": ".linkedin.com", "path": "/"},
        ])
        page = await context.new_page()
        page.set_default_timeout(15000)

        for i, row in enumerate(rows, 1):
            url = row["url"]
            title = row["title"] or "Unknown"
            company = row["company"] or "Unknown"
            app_id = row["app_id"]

            logger.info(f"[{i}/{len(rows)}] Checking: {title} @ {company}")

            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=15000)
                await page.wait_for_timeout(2000)

                # Check for "Easy Apply" / "Solicitud sencilla" BUTTON specifically
                is_easy = False
                for sel in [
                    'button.jobs-apply-button:has-text("Easy Apply")',
                    'button.jobs-apply-button:has-text("Solicitud sencilla")',
                ]:
                    try:
                        if await page.locator(sel).first.is_visible(timeout=1500):
                            is_easy = True
                            break
                    except Exception:
                        continue

                # Check if job is closed/expired
                page_text = (await page.evaluate("() => document.body.innerText"))[:1500].lower()
                is_closed = any(w in page_text for w in [
                    "no longer accepting", "ya no acepta",
                    "this job is no longer", "esta oferta ya no",
                    "position has been filled", "puesto ha sido cubierto",
                ])

                if is_closed:
                    closed_jobs.append({"app_id": app_id, "title": title, "company": company, "url": url})
                    logger.info(f"  🔒 Closed/expired")
                elif is_easy:
                    easy_apply_jobs.append({"app_id": app_id, "title": title, "company": company, "url": url, "description": row.get("description", "")})
                    logger.info(f"  ✅ Easy Apply")
                else:
                    external_jobs.append({"app_id": app_id, "title": title, "company": company, "url": url})
                    logger.info(f"  🔗 External portal")

            except Exception as e:
                logger.warning(f"  ❌ Error checking: {str(e)[:80]}")
                external_jobs.append({"app_id": app_id, "title": title, "company": company, "url": url})

            # Small delay between checks
            await page.wait_for_timeout(1000)

        await browser.close()

    return easy_apply_jobs, external_jobs, closed_jobs


def save_antigravity_jobs(external_jobs):
    """Save external portal jobs to data/antigravity_jobs.md for Antigravity."""
    lines = [
        "# Jobs para Antigravity (External Portal Apply)",
        "",
        "Estas vacantes requieren aplicar en portales externos.",
        "Antigravity debe navegar a cada URL y completar el formulario con el CV.",
        "",
        f"**Total: {len(external_jobs)} vacantes**",
        "",
        "| # | Title | Company | URL |",
        "|---|-------|---------|-----|",
    ]
    for i, job in enumerate(external_jobs, 1):
        lines.append(f"| {i} | {job['title']} | {job['company']} | {job['url']} |")

    lines.append("")
    lines.append("## Datos del candidato")
    lines.append("- **Nombre**: Alejandro Hernandez Loza")
    lines.append("- **Email**: alejandrohloza@gmail.com")
    lines.append("- **Teléfono**: +52 56 4144 6948")
    lines.append("- **LinkedIn**: https://www.linkedin.com/in/alejandro-hernandez-loza/")
    lines.append("- **CV PDF**: data/cv_alejandro_en.pdf (inglés), data/cv_alejandro_es.pdf (español)")
    lines.append("- **Ubicación**: Ciudad de México, México")
    lines.append("- **Disponibilidad**: Inmediata")
    lines.append("")

    with open("data/antigravity_jobs.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    logger.info(f"Saved {len(external_jobs)} jobs to data/antigravity_jobs.md")


async def reapply_easy_apply(easy_apply_jobs, resume, conn):
    """Re-apply to Easy Apply jobs with CV."""
    from src.tools import browser_tool

    reapplied = 0
    failed = 0

    for i, job in enumerate(easy_apply_jobs, 1):
        logger.info(f"\n[Re-apply {i}/{len(easy_apply_jobs)}] {job['title']} @ {job['company']}")

        try:
            result = browser_tool.apply_to_job_sync(
                job_url=job["url"],
                resume=resume,
                job_title=job["title"],
                company=job["company"],
                cover_letter="",  # auto-generated
            )

            if result.get("success"):
                reapplied += 1
                logger.success(f"  ✅ Re-applied with CV")
                conn.execute(
                    "UPDATE applications SET cover_letter = ?, notes = ? WHERE id = ?",
                    ("auto-generated (reapply)", "Re-applied with CV 2026-03-15", job["app_id"]),
                )
                conn.commit()
            else:
                status = result.get("status", "unknown")
                msg = result.get("message", "")
                if "already" in msg.lower() or status == "done":
                    logger.info(f"  → Already applied or closed")
                else:
                    failed += 1
                    logger.warning(f"  ❌ Failed: {status} - {msg[:80]}")

        except Exception as e:
            failed += 1
            logger.error(f"  ❌ Error: {str(e)[:100]}")

        time.sleep(8)

    return reapplied, failed


async def main():
    resume = json.load(open("data/resume.json"))
    cookies = json.load(open("config/linkedin_cookies.json"))
    conn = sqlite3.connect(settings.db_path)
    conn.row_factory = sqlite3.Row

    rows = conn.execute('''
        SELECT a.id as app_id, a.job_id, j.title, j.company, j.url, j.description
        FROM applications a
        LEFT JOIN jobs j ON a.job_id = j.id
        WHERE a.method = 'browser_agent'
        AND (a.cover_letter IS NULL OR a.cover_letter = '')
        AND a.status = 'applied'
        AND j.url IS NOT NULL
        AND j.url LIKE '%linkedin.com/jobs%'
    ''').fetchall()

    logger.info(f"Total LinkedIn jobs sin CV: {len(rows)}")

    # Phase 1: Classify all jobs
    logger.info("\n=== PHASE 1: Classifying jobs ===")
    easy_apply_jobs, external_jobs, closed_jobs = await classify_jobs(rows, cookies)

    logger.info(f"\nClassification results:")
    logger.info(f"  ✅ Easy Apply: {len(easy_apply_jobs)}")
    logger.info(f"  🔗 External portal: {len(external_jobs)}")
    logger.info(f"  🔒 Closed/expired: {len(closed_jobs)}")

    # Save external jobs for Antigravity
    if external_jobs:
        save_antigravity_jobs(external_jobs)

    # Mark closed jobs
    for job in closed_jobs:
        conn.execute(
            "UPDATE applications SET notes = ? WHERE id = ?",
            ("job_closed_or_expired", job["app_id"]),
        )
    conn.commit()

    # Phase 2: Re-apply to Easy Apply jobs
    if easy_apply_jobs:
        logger.info(f"\n=== PHASE 2: Re-applying to {len(easy_apply_jobs)} Easy Apply jobs ===")
        reapplied, failed = await reapply_easy_apply(easy_apply_jobs, resume, conn)
        logger.info(f"\nRe-apply results: ✅ {reapplied} | ❌ {failed}")
    else:
        logger.info("\nNo Easy Apply jobs to re-apply to")

    conn.close()

    logger.info(f"\n{'='*50}")
    logger.info(f"DONE!")
    logger.info(f"  ✅ Easy Apply re-applied: {len(easy_apply_jobs)}")
    logger.info(f"  🔗 External (saved for Antigravity): {len(external_jobs)}")
    logger.info(f"  🔒 Closed/expired: {len(closed_jobs)}")


if __name__ == "__main__":
    asyncio.run(main())
