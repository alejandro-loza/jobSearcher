"""
LinkedIn HR Agent.

Finds HR/Recruiter contacts at target companies on LinkedIn and sends
personalized connection requests to expand Alejandro's network.
"""
import json
import os
import time
from datetime import datetime
from typing import Optional

from loguru import logger

from config import settings

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

# Search URL pattern: LinkedIn people search filtered by company and recruiter keywords
_SEARCH_URL_TEMPLATE = (
    "https://www.linkedin.com/search/results/people/"
    "?keywords={keywords}&origin=GLOBAL_SEARCH_HEADER"
)


# ---------------------------------------------------------------------------
# Cookie / Playwright helpers
# ---------------------------------------------------------------------------

def _load_cookies() -> dict:
    try:
        with open(settings.linkedin_cookies_file, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"[hr_agent] Error loading cookies: {e}")
        return {}


def _build_playwright_context():
    """Returns (playwright, browser, context, page) with LinkedIn cookies loaded."""
    from playwright.sync_api import sync_playwright

    cookies = _load_cookies()
    li_at = cookies.get("li_at", "")
    jsessionid = cookies.get("JSESSIONID", "").replace('"', '')

    pw = sync_playwright().start()
    browser = pw.chromium.launch(
        headless=True,
        args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
    )
    context = browser.new_context(
        user_agent=(
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
    )
    context.add_cookies([
        {"name": "li_at", "value": li_at, "domain": ".linkedin.com", "path": "/"},
        {"name": "JSESSIONID", "value": jsessionid, "domain": ".www.linkedin.com", "path": "/"},
    ])
    page = context.new_page()
    page.add_init_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )
    return pw, browser, context, page


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
    """Search LinkedIn for HR/Recruiter contacts at a company.
    Uses Playwright to search people with recruiter/HR keywords at the company.
    Returns list of: {name, title, profile_url, company}"""
    pw = None
    browser = None
    contacts = []

    try:
        pw, browser, context, page = _build_playwright_context()

        # Build search query: recruiter OR "talent acquisition" at company
        keywords = f'recruiter OR "talent acquisition" OR "HR" "{company}"'
        from urllib.parse import quote
        url = _SEARCH_URL_TEMPLATE.format(keywords=quote(keywords))

        logger.info(f"[hr_agent] Searching HR contacts at {company}...")
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        time.sleep(3)

        # Extract profile cards from search results
        # LinkedIn search result cards have class like entity-result__item
        result_cards = page.locator(".entity-result__item, .search-results-container li")
        count = result_cards.count()
        logger.info(f"[hr_agent] Found {count} search result cards for {company}")

        for i in range(min(count, limit * 2)):  # fetch extra to filter
            if len(contacts) >= limit:
                break
            try:
                card = result_cards.nth(i)

                # Name
                name_elem = card.locator(
                    ".entity-result__title-text a span[aria-hidden='true'], "
                    ".app-aware-link span[aria-hidden='true']"
                ).first
                name = name_elem.inner_text(timeout=2000).strip() if name_elem.is_visible(timeout=1000) else ""

                # Title
                title_elem = card.locator(
                    ".entity-result__primary-subtitle, .entity-result__secondary-subtitle"
                ).first
                title = title_elem.inner_text(timeout=2000).strip() if title_elem.is_visible(timeout=1000) else ""

                # Profile URL
                link_elem = card.locator("a.app-aware-link").first
                href = link_elem.get_attribute("href", timeout=2000) if link_elem.is_visible(timeout=1000) else ""

                # Clean URL: keep only the /in/... part
                profile_url = ""
                if href and "/in/" in href:
                    profile_url = "https://www.linkedin.com" + href.split("?")[0] if href.startswith("/") else href.split("?")[0]

                if not name or not profile_url:
                    continue

                # Filter by HR/recruiter keywords in title
                title_lower = title.lower()
                hr_keywords = ["recruiter", "talent", "hr", "human resources", "recursos humanos",
                               "reclutador", "people", "staffing", "acquisition"]
                if not any(kw in title_lower for kw in hr_keywords):
                    continue

                contacts.append({
                    "name": name,
                    "title": title,
                    "profile_url": profile_url,
                    "company": company,
                })
                logger.debug(f"[hr_agent] Found contact: {name} | {title} @ {company}")

            except Exception as card_err:
                logger.debug(f"[hr_agent] Error parsing card {i}: {card_err}")
                continue

    except Exception as e:
        logger.error(f"[hr_agent] Error searching contacts at {company}: {e}")
    finally:
        try:
            if browser:
                browser.close()
            if pw:
                pw.stop()
        except Exception:
            pass

    logger.info(f"[hr_agent] Found {len(contacts)} HR contacts at {company}")
    return contacts


def send_connection_request(
    profile_url: str,
    contact_name: str,
    candidate_name: str,
    candidate_title: str,
    company: str,
) -> bool:
    """Navigate to profile, click Connect, add personalized note, send.
    Returns True if request was sent successfully."""
    pw = None
    browser = None

    # Build personalized note (max 300 chars)
    first_name = contact_name.split()[0] if contact_name else "there"
    note = (
        f"Hola {first_name}, soy {candidate_name}, Senior Software Engineer con 12 años "
        f"de experiencia en Java/Spring Boot. Me interesa conectar y explorar oportunidades "
        f"en {company}. Tengo experiencia en {CANDIDATE_TECH}. ¡Gracias!"
    )
    # Truncate if over limit
    if len(note) > NOTE_MAX_CHARS:
        note = note[:NOTE_MAX_CHARS - 3] + "..."

    try:
        pw, browser, context, page = _build_playwright_context()

        logger.info(f"[hr_agent] Navigating to profile: {profile_url}")
        page.goto(profile_url, wait_until="domcontentloaded", timeout=30000)
        time.sleep(3)

        # Look for Connect button (may be in actions area or "More" dropdown)
        connect_selectors = [
            'button[aria-label*="Connect"]',
            'button[aria-label*="Conectar"]',
            'button:has-text("Connect")',
            'button:has-text("Conectar")',
            '.pvs-profile-actions button:has-text("Connect")',
            '.pvs-profile-actions button:has-text("Conectar")',
        ]

        clicked_connect = False
        for selector in connect_selectors:
            try:
                btn = page.locator(selector).first
                if btn.is_visible(timeout=2000) and btn.is_enabled(timeout=1000):
                    btn.click()
                    logger.info(f"[hr_agent] Clicked Connect via: {selector}")
                    clicked_connect = True
                    break
            except Exception:
                continue

        if not clicked_connect:
            # Try "More" button to expand actions
            try:
                more_btn = page.locator('button[aria-label="More actions"]').first
                if more_btn.is_visible(timeout=2000):
                    more_btn.click()
                    time.sleep(1)
                    # Now look for Connect in dropdown
                    for selector in connect_selectors:
                        try:
                            btn = page.locator(selector).first
                            if btn.is_visible(timeout=2000):
                                btn.click()
                                clicked_connect = True
                                break
                        except Exception:
                            continue
            except Exception:
                pass

        if not clicked_connect:
            logger.warning(f"[hr_agent] Connect button not found for: {profile_url}")
            return False

        time.sleep(2)

        # Look for "Add a note" option in the connection dialog
        add_note_selectors = [
            'button[aria-label="Add a note"]',
            'button[aria-label="Añadir una nota"]',
            'button:has-text("Add a note")',
            'button:has-text("Añadir una nota")',
        ]

        for selector in add_note_selectors:
            try:
                btn = page.locator(selector).first
                if btn.is_visible(timeout=3000):
                    btn.click()
                    logger.info(f"[hr_agent] Clicked 'Add a note' via: {selector}")
                    time.sleep(1)
                    break
            except Exception:
                continue

        # Type the note in the textarea
        note_textareas = [
            'textarea[name="message"]',
            'textarea#custom-message',
            'textarea[placeholder*="note"]',
            'textarea[placeholder*="nota"]',
            'div[data-test-modal] textarea',
        ]

        note_typed = False
        for selector in note_textareas:
            try:
                ta = page.locator(selector).first
                if ta.is_visible(timeout=2000):
                    ta.click()
                    ta.fill(note)
                    note_typed = True
                    logger.info("[hr_agent] Note typed successfully")
                    break
            except Exception:
                continue

        if not note_typed:
            logger.warning("[hr_agent] Could not type note, sending without note")

        time.sleep(1)

        # Click Send / Enviar
        send_selectors = [
            'button[aria-label="Send now"]',
            'button[aria-label="Enviar ahora"]',
            'button:has-text("Send")',
            'button:has-text("Enviar")',
            'button[aria-label="Send invitation"]',
            'button[aria-label="Enviar invitación"]',
            'div[data-test-modal] button.artdeco-button--primary',
        ]

        sent = False
        for selector in send_selectors:
            try:
                btn = page.locator(selector).first
                if btn.is_visible(timeout=2000) and btn.is_enabled(timeout=1000):
                    btn.click()
                    logger.info(f"[hr_agent] Clicked Send via: {selector}")
                    sent = True
                    break
            except Exception:
                continue

        if sent:
            time.sleep(2)
            logger.info(f"[hr_agent] Connection request sent to {contact_name} @ {company}")
        else:
            logger.error(f"[hr_agent] Failed to send connection request to {contact_name}")

        return sent

    except Exception as e:
        logger.error(f"[hr_agent] Error sending connection request to {profile_url}: {e}")
        return False
    finally:
        try:
            if browser:
                browser.close()
            if pw:
                pw.stop()
        except Exception:
            pass


def expand_hr_network(max_requests: int = 10) -> dict:
    """Main function: iterate target companies, find HR contacts, send requests.
    Limits to max_requests per run to avoid LinkedIn limits.
    Returns: {sent: int, failed: int, contacts_found: list}"""
    log = _load_log()
    result = {"sent": 0, "failed": 0, "contacts_found": []}

    # Check daily limit
    today_count = _requests_sent_today(log)
    if today_count >= MAX_REQUESTS_PER_DAY:
        logger.warning(f"[hr_agent] Daily limit reached ({today_count}/{MAX_REQUESTS_PER_DAY}). Skipping.")
        return result

    remaining = min(max_requests, MAX_REQUESTS_PER_DAY - today_count)
    logger.info(f"[hr_agent] Starting HR network expansion. Max requests: {remaining}")

    # Determine which companies to prioritize (ones not yet contacted recently)
    contacted_companies = set()
    for req in log.get("requests_sent", []):
        if req.get("company"):
            contacted_companies.add(req["company"])

    # Companies not yet contacted get priority
    priority = [c for c in TARGET_COMPANIES if c not in contacted_companies]
    remaining_companies = [c for c in TARGET_COMPANIES if c in contacted_companies]
    companies_to_search = priority + remaining_companies

    requests_this_run = 0

    for company in companies_to_search:
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
