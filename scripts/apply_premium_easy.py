#!/usr/bin/env python3
"""
Apply to premium LinkedIn Easy Apply jobs using browser_tool.
These are simple LinkedIn forms — no external portals.
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from src.tools import browser_tool
from src.agents import master_agent
from src.db.tracker import JobTracker

def main():
    resume = json.load(open("data/resume.json"))
    tracker = JobTracker()
    premium = json.load(open("data/premium_jobs_report.json"))

    # Filter LinkedIn Easy Apply only
    easy = [j for j in premium if j.get("easy_apply") and "linkedin.com/jobs" in j.get("url", "")]
    easy.sort(key=lambda x: x.get("match_score", 0), reverse=True)

    logger.info(f"🚀 Aplicando a {len(easy)} vacantes premium Easy Apply")

    applied = 0
    failed = 0
    skipped = 0

    for i, job in enumerate(easy, 1):
        url = job.get("url", "")
        title = job.get("title", "")
        company = job.get("company", "")
        score = job.get("match_score", 0)

        logger.info(f"\n[{i}/{len(easy)}] [{score}%] {title} @ {company}")
        logger.info(f"  URL: {url}")

        # Check if already applied
        try:
            from config import settings
            import sqlite3
            conn = sqlite3.connect(settings.db_path)
            row = conn.execute("SELECT status FROM jobs WHERE url = ?", (url,)).fetchone()
            if row and row[0] == "applied":
                logger.info(f"  ⏭️ Ya aplicada, saltando")
                skipped += 1
                conn.close()
                continue
            conn.close()
        except Exception:
            pass

        # Generate cover letter
        try:
            cover_letter = master_agent.generate_cover_letter(job, resume)
        except Exception as e:
            logger.warning(f"  Cover letter failed: {e}")
            cover_letter = ""

        # Apply via browser_tool
        try:
            result = browser_tool.apply_to_job_sync(
                job_url=url,
                resume=resume,
                job_title=title,
                company=company,
                cover_letter=cover_letter,
            )

            if result.get("success"):
                applied += 1
                logger.success(f"  ✅ Aplicada exitosamente")
                tracker.save_application(
                    job_id=job.get("id", url),
                    method="linkedin_easy_apply",
                    cover_letter=cover_letter,
                    status="applied",
                )
            else:
                status = result.get("status", "unknown")
                failed += 1
                logger.warning(f"  ❌ Falló: {status}")
                if status in ("captcha", "need_user", "external_redirect"):
                    logger.info(f"  → Requiere intervención manual")

        except Exception as e:
            failed += 1
            logger.error(f"  ❌ Error: {str(e)[:100]}")

        # Pause between applications
        time.sleep(5)

    logger.info(f"\n{'='*50}")
    logger.info(f"✅ Aplicadas: {applied}")
    logger.info(f"❌ Fallidas: {failed}")
    logger.info(f"⏭️ Saltadas: {skipped}")
    logger.info(f"Total: {len(easy)}")


if __name__ == "__main__":
    main()
