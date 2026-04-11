"""
LinkedIn HR Agent.

Finds HR/Recruiter contacts at target companies on LinkedIn and sends
personalized connection requests to expand Alejandro's network.

Uses linkedin_api (HTTP API) for searching contacts.
Uses linkedin_api for sending connection requests.
NO Playwright — avoids anti-bot blocks.
"""
import json
import os
import time
from datetime import datetime
from typing import Optional

from loguru import logger
from linkedin_api import Linkedin
from requests.cookies import RequestsCookieJar

from config import settings

# ---------------------------------------------------------------------------
# Kill switch
# ---------------------------------------------------------------------------
LINKEDIN_CONNECTIONS_BLOCKED = True  # LinkedIn blocks people search from server IPs

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

HR_LOG_FILE = "data/linkedin_hr_log.json"

TARGET_COMPANIES = [
    # Empresas de las vacantes premium (92%+ match)
    "Netflix", "Uber", "Twilio", "GitHub", "Samsara", "Acorns",
    "Included Health", "Roku", "Deutsche Bank", "Plaid",
    "Capital One", "BlackRock", "Adyen", "Nubank",
    # Tech en México / LATAM
    "Thomson Reuters", "Globant", "EPAM", "Endava", "Wizeline",
    "Clip", "Kueski", "Konfío", "Mercado Libre", "Rappi",
    "Bitso", "Conekta", "Coppel",
    # Grandes tech
    "NVIDIA", "IBM", "Stripe", "Cognizant", "Infosys", "UST",
    "Capgemini", "Deloitte", "Concentrix", "Mogi I/O",
    # Otras de las vacantes premium
    "Codelitt", "Healthie", "Nexthink", "Iterable", "ReversingLabs",
    "AgileEngine", "3Pillar", "WorkMotion", "Aledade", "Panopto",
    "Citi", "Allstate", "Penn Mutual",
]

# Candidate info (Alejandro)
CANDIDATE_NAME = "Alejandro Hernandez Loza"
CANDIDATE_TITLE = "Senior Software Engineer"
CANDIDATE_TECH = "Java, Spring Boot, Microservicios, Cloud (GCP/AWS), Docker y Kubernetes"

# LinkedIn limits: stay well below to avoid account flags
MAX_REQUESTS_PER_DAY = 20
NOTE_MAX_CHARS = 300  # LinkedIn connection note limit

# Round-robin: process N companies per run to stay within API rate limits
COMPANIES_PER_RUN = 6

# HR keywords to filter contacts by title
HR_TITLE_KEYWORDS = [
    "recruiter", "talent", "hr", "human resources", "recursos humanos",
    "reclutador", "people", "staffing", "acquisition",
]

# ---------------------------------------------------------------------------
# LinkedIn API helper (singleton)
# ---------------------------------------------------------------------------

_api_instance = None


def _get_linkedin_api() -> Linkedin:
    """Return authenticated linkedin_api instance."""
    global _api_instance
    if _api_instance is not None:
        return _api_instance

    cookies = _load_cookies()
    li_at = cookies.get("li_at", "")
    jsessionid = cookies.get("JSESSIONID", "").replace('"', '')

    if not li_at:
        raise RuntimeError("No li_at cookie found in config/linkedin_cookies.json")

    jar = RequestsCookieJar()
    jar.set("li_at", li_at, domain=".linkedin.com")
    jar.set("JSESSIONID", f'"{jsessionid}"', domain=".linkedin.com")

    _api_instance = Linkedin("", "", cookies=jar)
    logger.info("[hr_agent] LinkedIn API authenticated")
    return _api_instance


def _reset_api():
    """Reset API instance (e.g. after cookie refresh)."""
    global _api_instance
    _api_instance = None


def _load_cookies() -> dict:
    try:
        with open(settings.linkedin_cookies_file, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"[hr_agent] Error loading cookies: {e}")
        return {}


# ---------------------------------------------------------------------------
# Log helpers
# ---------------------------------------------------------------------------

def _load_log() -> dict:
    if not os.path.exists(HR_LOG_FILE):
        return {"requests_sent": [], "contacts_found": [], "daily_counts": {}}
    try:
        with open(HR_LOG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"[hr_agent] Error loading HR log: {e}")
        return {"requests_sent": [], "contacts_found": [], "daily_counts": {}}


def _save_log(log: dict) -> None:
    try:
        os.makedirs("data", exist_ok=True)
        with open(HR_LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(log, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"[hr_agent] Error saving HR log: {e}")


def _requests_sent_today(log: dict) -> int:
    today = datetime.now().strftime("%Y-%m-%d")
    return log.get("daily_counts", {}).get(today, 0)


def _increment_daily_count(log: dict) -> None:
    today = datetime.now().strftime("%Y-%m-%d")
    counts = log.setdefault("daily_counts", {})
    counts[today] = counts.get(today, 0) + 1


def _already_contacted(log: dict, profile_url: str) -> bool:
    sent = log.get("requests_sent", [])
    return any(r.get("profile_url") == profile_url for r in sent)


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------

def search_hr_contacts(company: str, limit: int = 5) -> list:
    """Search LinkedIn for HR/Recruiter contacts at a company via linkedin_api.
    Returns list of: {name, title, profile_url, vanity_name, company}"""
    contacts = []
    seen_ids = set()

    try:
        api = _get_linkedin_api()

        # Search with different HR-related title keywords
        search_titles = ["recruiter", "talent acquisition", "HR"]

        for title_kw in search_titles:
            if len(contacts) >= limit:
                break

            keywords = f"{title_kw} {company}"
            logger.info(f"[hr_agent] API search: '{keywords}'")

            try:
                results = api.search_people(keywords=keywords, limit=limit)
            except Exception as e:
                logger.warning(f"[hr_agent] API search failed for '{keywords}': {e}")
                continue

            for r in results:
                public_id = r.get("public_id", "")
                if not public_id or public_id in seen_ids:
                    continue

                headline = r.get("headline", "") or ""
                headline_lower = headline.lower()

                # Filter: must have HR keyword in headline
                if not any(kw in headline_lower for kw in HR_TITLE_KEYWORDS):
                    continue

                seen_ids.add(public_id)
                profile_url = f"https://www.linkedin.com/in/{public_id}"
                name = f"{r.get('firstName', '')} {r.get('lastName', '')}".strip()

                contacts.append({
                    "name": name,
                    "title": headline,
                    "profile_url": profile_url,
                    "vanity_name": public_id,
                    "company": company,
                })
                logger.debug(f"[hr_agent] Found: {name} | {headline} @ {company}")

                if len(contacts) >= limit:
                    break

            # Rate limit between API calls
            time.sleep(2)

    except Exception as e:
        logger.error(f"[hr_agent] Error searching contacts at {company}: {e}")

    logger.info(f"[hr_agent] Found {len(contacts)} HR contacts at {company}")
    return contacts


def send_connection_request(
    profile_url: str,
    contact_name: str,
    candidate_name: str,
    candidate_title: str,
    company: str,
    vanity_name: Optional[str] = None,
) -> bool:
    """Send a personalized connection request via linkedin_api.
    Returns True if request was sent successfully."""

    if LINKEDIN_CONNECTIONS_BLOCKED:
        logger.warning(f"[hr_agent] CONNECTIONS BLOCKED — not sending to {contact_name}")
        return False

    # Extract vanity name (public_id) from profile URL if not provided
    if not vanity_name:
        if "/in/" in profile_url:
            vanity_name = profile_url.rstrip("/").split("/in/")[-1].split("?")[0]

    if not vanity_name:
        logger.error(f"[hr_agent] Cannot extract vanity name from: {profile_url}")
        return False

    # Build personalized note (max 300 chars)
    first_name = contact_name.split()[0] if contact_name else "there"
    note = (
        f"Hola {first_name}, soy {candidate_name}, Senior Software Engineer con 12 años "
        f"de experiencia en Java/Spring Boot. Me interesa conectar y explorar oportunidades "
        f"en {company}. Tengo experiencia en {CANDIDATE_TECH}. ¡Gracias!"
    )
    if len(note) > NOTE_MAX_CHARS:
        note = note[:NOTE_MAX_CHARS - 3] + "..."

    try:
        api = _get_linkedin_api()
        api.add_connection(vanity_name, message=note)
        logger.info(f"[hr_agent] Connection request sent to {contact_name} @ {company}")
        return True
    except Exception as e:
        error_msg = str(e).lower()
        if "already" in error_msg or "pending" in error_msg:
            logger.info(f"[hr_agent] Already connected/pending: {contact_name}")
            return False
        logger.error(f"[hr_agent] Error sending connection to {contact_name}: {e}")
        return False


def expand_hr_network(max_requests: int = 10) -> dict:
    """Main function: iterate target companies, find HR contacts, send requests.
    Uses round-robin: processes COMPANIES_PER_RUN companies per execution.
    Limits to max_requests per run to avoid LinkedIn limits.
    Returns: {sent: int, failed: int, contacts_found: list}"""

    if LINKEDIN_CONNECTIONS_BLOCKED:
        logger.warning("[hr_agent] CONNECTIONS BLOCKED — skipping expansion")
        return {"sent": 0, "failed": 0, "contacts_found": []}

    log = _load_log()
    result = {"sent": 0, "failed": 0, "contacts_found": []}

    # Check daily limit
    today_count = _requests_sent_today(log)
    if today_count >= MAX_REQUESTS_PER_DAY:
        logger.warning(f"[hr_agent] Daily limit reached ({today_count}/{MAX_REQUESTS_PER_DAY}). Skipping.")
        return result

    remaining = min(max_requests, MAX_REQUESTS_PER_DAY - today_count)

    # Round-robin: pick next batch of companies
    last_idx = log.get("last_company_index", 0)
    batch = TARGET_COMPANIES[last_idx : last_idx + COMPANIES_PER_RUN]
    if len(batch) < COMPANIES_PER_RUN:
        batch += TARGET_COMPANIES[: COMPANIES_PER_RUN - len(batch)]
    next_idx = (last_idx + COMPANIES_PER_RUN) % len(TARGET_COMPANIES)
    log["last_company_index"] = next_idx

    logger.info(
        f"[hr_agent] Starting HR expansion. Batch: {batch} "
        f"(idx {last_idx}→{next_idx}). Max requests: {remaining}"
    )

    requests_this_run = 0

    for company in batch:
        if requests_this_run >= remaining:
            logger.info(f"[hr_agent] Reached request limit for this run ({remaining})")
            break

        contacts = search_hr_contacts(company, limit=5)
        result["contacts_found"].extend(contacts)

        # Log newly found contacts
        for c in contacts:
            if not any(
                fc.get("profile_url") == c["profile_url"]
                for fc in log.get("contacts_found", [])
            ):
                log.setdefault("contacts_found", []).append({
                    **c,
                    "found_at": datetime.now().isoformat(),
                })

        _save_log(log)

        for contact in contacts:
            if requests_this_run >= remaining:
                break

            profile_url = contact.get("profile_url", "")
            if not profile_url:
                continue

            # Skip already contacted profiles
            if _already_contacted(log, profile_url):
                logger.debug(f"[hr_agent] Already contacted: {contact['name']}, skipping")
                continue

            # Pause between requests to avoid LinkedIn rate limits
            if requests_this_run > 0:
                time.sleep(5)

            success = send_connection_request(
                profile_url=profile_url,
                contact_name=contact["name"],
                candidate_name=CANDIDATE_NAME,
                candidate_title=CANDIDATE_TITLE,
                company=company,
                vanity_name=contact.get("vanity_name"),
            )

            entry = {
                "profile_url": profile_url,
                "name": contact["name"],
                "title": contact.get("title", ""),
                "company": company,
                "sent_at": datetime.now().isoformat(),
                "success": success,
            }
            log.setdefault("requests_sent", []).append(entry)

            if success:
                result["sent"] += 1
                requests_this_run += 1
                _increment_daily_count(log)
            else:
                result["failed"] += 1

            _save_log(log)

    logger.info(
        f"[hr_agent] Network expansion complete. "
        f"Sent: {result['sent']}, Failed: {result['failed']}, "
        f"Contacts found: {len(result['contacts_found'])}"
    )
    return result


def get_connection_stats() -> dict:
    """Return stats from data/linkedin_hr_log.json."""
    log = _load_log()
    today = datetime.now().strftime("%Y-%m-%d")

    requests_sent = log.get("requests_sent", [])
    successful = [r for r in requests_sent if r.get("success")]

    # Count by company
    by_company: dict = {}
    for r in successful:
        company = r.get("company", "unknown")
        by_company[company] = by_company.get(company, 0) + 1

    return {
        "total_sent": len(successful),
        "total_failed": len([r for r in requests_sent if not r.get("success")]),
        "sent_today": _requests_sent_today(log),
        "daily_limit": MAX_REQUESTS_PER_DAY,
        "contacts_found": len(log.get("contacts_found", [])),
        "by_company": by_company,
        "last_run_at": requests_sent[-1]["sent_at"] if requests_sent else None,
    }
