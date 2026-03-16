#!/usr/bin/env python3
"""
Re-apply to LinkedIn Easy Apply jobs where we didn't send CV/cover letter.
Only processes Easy Apply jobs. External portal jobs are skipped for Antigravity.
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


async def is_easy_apply(job_url: str, cookies: dict) -> bool:
    """Check if a LinkedIn job URL is Easy Apply by loading the page."""
    li_at = cookies.get("li_at", "")
    jsessionid = cookies.get("JSESSIONID", "").replace('"', '')

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
        try:
            await page.goto(job_url, wait_until="domcontentloaded", timeout=20000)
            await page.wait_for_timeout(2000)

            page_text = await page.evaluate("() => document.body.innerText")
            page_lower = page_text.lower()

            # Check for Easy Apply button
            for sel in [
                'button:has-text("Easy Apply")',
                'button:has-text("Solicitud sencilla")',
                'button.jobs-apply-button:has-text("Easy")',
                'button.jobs-apply-button:has-text("sencilla")',
            ]:
                try:
                    if await page.locator(sel).first.is_visible(timeout=1000):
                        await browser.close()
                        return True
                except Exception:
                    continue

            # Check page text for easy apply indicators
            if "easy apply" in page_lower or "solicitud sencilla" in page_lower:
                await browser.close()
                return True

            await browser.close()
            return False
        except Exception as e:
            logger.debug(f"Error checking {job_url}: {e}")
            try:
                await browser.close()
            except Exception:
                pass
            return False


async def main():
    resume = json.load(open("data/resume.json"))
    cookies = json.load(open("config/linkedin_cookies.json"))
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

    logger.info(f"Total LinkedIn jobs sin CV: {len(rows)}")

    from src.tools import browser_tool

    reapplied = 0
    skipped_external = 0
    skipped_closed = 0
    failed = 0

    for i, row in enumerate(rows, 1):
        url = row["url"]
        title = row["title"] or "Unknown"
        company = row["company"] or "Unknown"
        app_id = row["app_id"]

        logger.info(f"\n[{i}/{len(rows)}] {title} @ {company}")

        # Check if it's Easy Apply
        easy = await is_easy_apply(url, cookies)
        if not easy:
            skipped_external += 1
            logger.info(f"  ⏭️ External apply (not Easy Apply) — skipping for Antigravity")
            conn.execute(
                "UPDATE applications SET notes = ? WHERE id = ?",
                ("external_portal_needs_antigravity", app_id),
            )
            conn.commit()
            continue

        logger.info(f"  ✅ Easy Apply detected, re-applying with CV...")

        try:
            result = browser_tool.apply_to_job_sync(
                job_url=url,
                resume=resume,
                job_title=title,
                company=company,
                cover_letter="",  # auto-generated
            )

            if result.get("success"):
                reapplied += 1
                logger.success(f"  ✅ Re-applied with CV")
                conn.execute(
                    "UPDATE applications SET cover_letter = ?, notes = ? WHERE id = ?",
                    ("auto-generated (reapply)", "Re-applied with CV on 2026-03-15", app_id),
                )
                conn.commit()
            else:
                status = result.get("status", "unknown")
                msg = result.get("message", "")

                if "already" in msg.lower() or status == "done":
                    skipped_closed += 1
                    logger.info(f"  → Already applied or closed")
                    conn.execute(
                        "UPDATE applications SET notes = ? WHERE id = ?",
                        ("already_applied_or_closed", app_id),
                    )
                    conn.commit()
                else:
                    failed += 1
                    logger.warning(f"  ❌ Failed: {status} - {msg[:80]}")

        except Exception as e:
            failed += 1
            logger.error(f"  ❌ Error: {str(e)[:100]}")

        # Pause between applications to avoid rate limiting
        time.sleep(8)

    conn.close()

    logger.info(f"\n{'='*50}")
    logger.info(f"✅ Re-applied with CV: {reapplied}")
    logger.info(f"⏭️ External portal (Antigravity): {skipped_external}")
    logger.info(f"🔒 Already applied/closed: {skipped_closed}")
    logger.info(f"❌ Failed: {failed}")
    logger.info(f"Total processed: {len(rows)}")


if __name__ == "__main__":
    asyncio.run(main())
