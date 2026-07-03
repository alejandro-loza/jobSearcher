"""
Indeed auto-apply: slow-but-constant.

Strategy:
1. Pull Indeed CDMX jobs from DB (status=found, score>=threshold, not yet applied).
2. For each URL, resolve final redirect:
   - If redirects to safe ATS (greenhouse/lever/ashby) → reuse browser_tool path.
   - If stays on Indeed (internal Indeed Apply) → use browser_tool's "indeed" path.
3. Rate limits: daily cap, business hours, 120-180s delays.
4. CAPTCHA/Cloudflare detector: if hit, freeze 48h.
5. State persisted in data/indeed_apply_state.json.
"""
import json
import random
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List

from loguru import logger

from src.tools.browser_tool import apply_to_job_sync, detect_ats_type

STATE_FILE = Path("data/indeed_apply_state.json")
DB_FILE = "data/jobsearcher.db"

DAILY_CAP = 5
BUSINESS_HOURS_START = 9
BUSINESS_HOURS_END = 19
BUSINESS_DAYS = {0, 1, 2, 3, 4}
DELAY_MIN_SEC = 120
DELAY_MAX_SEC = 180
SCORE_THRESHOLD = 0
FREEZE_HOURS_ON_CAPTCHA = 48

SAFE_REDIRECT_ATS = {"greenhouse", "lever", "ashby", "smartrecruiters"}


# Indeed's HTML serves 403 to non-browser clients, so static redirect resolution is not possible.
# We delegate the navigation to browser_tool (Playwright + LLM vision) which respects anti-bot.


def _load_state() -> Dict[str, Any]:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            pass
    return {
        "applied_today": 0,
        "last_apply_date": "",
        "last_apply_at": "",
        "frozen_until": "",
        "total_applied": 0,
        "captcha_hits": 0,
    }


def _save_state(state: Dict[str, Any]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def _reset_daily_if_new_day(state: Dict[str, Any]) -> None:
    today = datetime.now().strftime("%Y-%m-%d")
    if state.get("last_apply_date") != today:
        state["applied_today"] = 0
        state["last_apply_date"] = today


def _is_business_hours() -> bool:
    now = datetime.now()
    return now.weekday() in BUSINESS_DAYS and BUSINESS_HOURS_START <= now.hour < BUSINESS_HOURS_END


def _is_frozen(state: Dict[str, Any]) -> bool:
    frozen = state.get("frozen_until", "")
    if not frozen:
        return False
    try:
        return datetime.now() < datetime.fromisoformat(frozen)
    except Exception:
        return False


def _fetch_pending_indeed_jobs(limit: int = 20) -> List[Dict[str, Any]]:
    con = sqlite3.connect(DB_FILE)
    con.row_factory = sqlite3.Row
    rows = con.execute(
        """
        SELECT id, title, company, location, url, match_score, description, ats_type
        FROM jobs
        WHERE url LIKE '%indeed.com/viewjob%'
          AND status IN ('found', 'pending')
          AND ats_type = 'indeed_apply'
          AND (applied_url IS NULL OR applied_url = '')
          AND (LOWER(location) LIKE '%mexico%'
               OR LOWER(location) LIKE '%cdmx%'
               OR LOWER(location) LIKE '%dif,%'
               OR LOWER(location) LIKE '%distrito federal%')
          AND LOWER(location) NOT LIKE '%nuevo leon%'
          AND LOWER(location) NOT LIKE '%jalisco%'
          AND LOWER(location) NOT LIKE '%queretaro%'
          AND LOWER(location) NOT LIKE '%querétaro%'
          AND LOWER(location) NOT LIKE '%guadalajara%'
          AND LOWER(location) NOT LIKE '%monterrey%'
        ORDER BY COALESCE(match_score, 0) DESC, found_at DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    con.close()
    return [dict(r) for r in rows]


def _mark_applied(job_id: str, applied_url: str) -> None:
    con = sqlite3.connect(DB_FILE)
    con.execute(
        "UPDATE jobs SET status = 'applied', applied_url = ?, last_attempt_at = ? WHERE id = ?",
        (applied_url, datetime.now().isoformat(), job_id),
    )
    con.commit()
    con.close()


def _mark_failed(job_id: str, reason: str) -> None:
    con = sqlite3.connect(DB_FILE)
    new_ats = "external_portal" if reason == "need_user" else None
    if new_ats:
        con.execute(
            "UPDATE jobs SET last_attempt_at = ?, ats_type = ? WHERE id = ?",
            (datetime.now().isoformat(), new_ats, job_id),
        )
    else:
        con.execute(
            "UPDATE jobs SET last_attempt_at = ? WHERE id = ?",
            (datetime.now().isoformat(), job_id),
        )
    con.commit()
    con.close()
    logger.debug(f"[indeed] job {job_id} marked failed: {reason}")


def _load_resume() -> Dict[str, Any]:
    resume_file = Path("data/resume.json")
    if resume_file.exists():
        return json.loads(resume_file.read_text())
    return {}


def run_indeed_apply_cycle(force: bool = False, max_apps: Optional[int] = None) -> Dict[str, Any]:
    """One pass: pick up to DAILY_CAP - applied_today jobs and apply with delays."""
    state = _load_state()
    _reset_daily_if_new_day(state)

    if _is_frozen(state):
        logger.warning(f"[indeed] frozen until {state['frozen_until']} (captcha cooldown)")
        return {"skipped": "frozen", "frozen_until": state["frozen_until"]}

    if not force and not _is_business_hours():
        logger.info("[indeed] outside business hours, skip")
        return {"skipped": "outside_business_hours"}

    remaining = DAILY_CAP - state["applied_today"]
    if max_apps is not None:
        remaining = min(remaining, max_apps)
    if remaining <= 0:
        logger.info(f"[indeed] daily cap {DAILY_CAP} reached")
        return {"skipped": "daily_cap_reached", "applied_today": state["applied_today"]}

    jobs = _fetch_pending_indeed_jobs(limit=remaining * 3)
    if not jobs:
        logger.info("[indeed] no pending Indeed CDMX jobs")
        return {"skipped": "no_jobs"}

    resume = _load_resume()
    if not resume:
        logger.error("[indeed] data/resume.json missing")
        return {"skipped": "no_resume"}

    results = {"attempted": 0, "applied": 0, "failed": 0}

    for job in jobs:
        if results["applied"] >= remaining:
            break

        url = job["url"]
        title = job["title"]
        company = job["company"]
        score = job.get("match_score") or 0

        if score and score < SCORE_THRESHOLD:
            logger.debug(f"[indeed] skip low score {score}: {title} @ {company}")
            continue

        results["attempted"] += 1
        logger.info(f"[indeed] APPLYING (Indeed): {title} @ {company}")

        try:
            res = apply_to_job_sync(
                job_url=url,
                resume=resume,
                job_title=title,
                company=company,
                headless=True,
            )
            success = bool(res.get("success"))
            msg = (res.get("message") or "").lower()

            if any(k in msg for k in ("captcha", "cloudflare", "challenge", "verify you are human")):
                state["captcha_hits"] = state.get("captcha_hits", 0) + 1
                state["frozen_until"] = (datetime.now() + timedelta(hours=FREEZE_HOURS_ON_CAPTCHA)).isoformat()
                _save_state(state)
                logger.error(f"[indeed] CAPTCHA detected, freezing {FREEZE_HOURS_ON_CAPTCHA}h")
                results["failed"] += 1
                break

            if success:
                _mark_applied(job["id"], url)
                state["applied_today"] += 1
                state["total_applied"] += 1
                state["last_apply_at"] = datetime.now().isoformat()
                _save_state(state)
                results["applied"] += 1
                logger.success(f"[indeed] applied: {title} @ {company}")
            else:
                status = res.get("status", "unknown")
                _mark_failed(job["id"], status)
                results["failed"] += 1
                if status == "need_user":
                    logger.info(f"[indeed] {title} → marked external_portal, will not retry")
                else:
                    logger.warning(f"[indeed] failed: {title} — {res.get('message')}")

        except Exception as e:
            logger.error(f"[indeed] exception applying to {title}: {e}")
            results["failed"] += 1

        if results["applied"] < remaining:
            delay = random.uniform(DELAY_MIN_SEC, DELAY_MAX_SEC)
            logger.info(f"[indeed] sleeping {delay:.0f}s before next apply")
            time.sleep(delay)

    results["applied_today"] = state["applied_today"]
    results["daily_cap"] = DAILY_CAP
    return results
