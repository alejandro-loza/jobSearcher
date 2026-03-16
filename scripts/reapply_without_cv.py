#!/usr/bin/env python3
"""
Re-apply to jobs where we didn't send CV/cover letter.
Only LinkedIn jobs (Easy Apply). Glassdoor/Indeed redirect to external portals.
"""
import json
import sqlite3
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from config import settings
from src.tools import browser_tool

def main():
    resume = json.load(open("data/resume.json"))
    conn = sqlite3.connect(settings.db_path)
    conn.row_factory = sqlite3.Row

    # Get LinkedIn jobs applied without CV
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

    logger.info(f"🔄 Re-aplicando a {len(rows)} vacantes LinkedIn sin CV")

    reapplied = 0
    failed = 0
    skipped = 0

    for i, row in enumerate(rows, 1):
        url = row["url"]
        title = row["title"] or "Unknown"
        company = row["company"] or "Unknown"
        app_id = row["app_id"]
        description = row["description"] or ""

        logger.info(f"\n[{i}/{len(rows)}] {title} @ {company}")
        logger.info(f"  URL: {url}")

        try:
            # apply_to_job_sync now auto-generates cover letter
            result = browser_tool.apply_to_job_sync(
                job_url=url,
                resume=resume,
                job_title=title,
                company=company,
                cover_letter="",  # will be auto-generated
            )

            if result.get("success"):
                reapplied += 1
                logger.success(f"  ✅ Re-aplicada con CV")
                # Update application record with cover letter
                conn.execute(
                    "UPDATE applications SET cover_letter = ?, notes = ? WHERE id = ?",
                    ("auto-generated (reapply)", "Re-applied with CV on 2026-03-15", app_id),
                )
                conn.commit()
            else:
                status = result.get("status", "unknown")
                msg = result.get("message", "")
                failed += 1
                logger.warning(f"  ❌ Falló: {status} - {msg[:80]}")

                # If already applied (duplicate), just update the record
                if "already" in msg.lower() or "duplicate" in msg.lower() or status == "done":
                    skipped += 1
                    failed -= 1
                    logger.info(f"  → Ya aplicada anteriormente, marcando")

        except Exception as e:
            failed += 1
            logger.error(f"  ❌ Error: {str(e)[:100]}")

        # Pause between applications
        time.sleep(5)

    conn.close()

    logger.info(f"\n{'='*50}")
    logger.info(f"✅ Re-aplicadas con CV: {reapplied}")
    logger.info(f"❌ Fallidas: {failed}")
    logger.info(f"⏭️ Duplicadas/saltadas: {skipped}")
    logger.info(f"Total procesadas: {len(rows)}")


if __name__ == "__main__":
    main()
