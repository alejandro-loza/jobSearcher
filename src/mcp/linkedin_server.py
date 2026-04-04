"""
LinkedIn MCP Server — FastMCP.

Expone herramientas de LinkedIn como MCP tools:
- search_jobs: buscar empleos
- get_job: detalles de un empleo
- search_people: buscar personas/reclutadores
- get_profile: ver perfil de alguien
- send_connection_request: enviar solicitud de conexión
- get_conversations: listar conversaciones
- send_message: enviar mensaje
- get_feed: ver feed
- create_post: publicar post con imagen (via Playwright)
"""

import json
import os
import sys
from pathlib import Path
from typing import Optional

from fastmcp import FastMCP
from loguru import logger

# Add project root to path
PROJECT_ROOT = str(Path(__file__).parent.parent.parent)
sys.path.insert(0, PROJECT_ROOT)

mcp = FastMCP("linkedin", instructions="LinkedIn tools for job search, networking, and content publishing")


# ---------------------------------------------------------------------------
# LinkedIn API client (singleton)
# ---------------------------------------------------------------------------

_api = None


def _get_api():
    global _api
    if _api is not None:
        return _api

    from linkedin_api import Linkedin
    from requests.cookies import RequestsCookieJar

    cookies_file = os.path.join(PROJECT_ROOT, "config", "linkedin_cookies.json")
    with open(cookies_file) as f:
        cookies = json.load(f)

    li_at = cookies.get("li_at", "")
    jsessionid = cookies.get("JSESSIONID", "").replace('"', '')

    jar = RequestsCookieJar()
    jar.set("li_at", li_at, domain=".linkedin.com")
    jar.set("JSESSIONID", f'"{jsessionid}"', domain=".linkedin.com")

    _api = Linkedin("", "", cookies=jar)
    logger.info("[linkedin_mcp] Connected to LinkedIn API")
    return _api


# ---------------------------------------------------------------------------
# Job Search Tools
# ---------------------------------------------------------------------------

@mcp.tool()
def search_jobs(
    keywords: str,
    location: str = "remote",
    limit: int = 10,
) -> list[dict]:
    """Search LinkedIn jobs by keywords and location."""
    api = _get_api()
    jobs = api.search_jobs(
        keywords=keywords,
        location_name=location,
        limit=limit,
    )
    results = []
    for j in jobs:
        tracking = j.get("trackingUrn", "")
        job_id = tracking.split(":")[-1] if tracking else ""
        results.append({
            "job_id": job_id,
            "title": j.get("title", ""),
            "company": j.get("companyName", ""),
            "location": j.get("formattedLocation", ""),
            "url": f"https://www.linkedin.com/jobs/view/{job_id}" if job_id else "",
            "listed_at": j.get("listedAt", ""),
        })
    return results


@mcp.tool()
def get_job(job_id: str) -> dict:
    """Get details of a specific LinkedIn job by ID."""
    api = _get_api()
    job = api.get_job(job_id)
    return {
        "title": job.get("title", ""),
        "company": job.get("companyDetails", {}).get("companyName", ""),
        "description": job.get("description", {}).get("text", ""),
        "location": job.get("formattedLocation", ""),
        "employment_type": job.get("employmentType", ""),
        "seniority_level": job.get("seniorityLevel", ""),
        "apply_url": job.get("applyMethod", {}).get("companyApplyUrl", ""),
        "easy_apply": "IN_APP" in str(job.get("applyMethod", {})),
    }


# ---------------------------------------------------------------------------
# People & Networking Tools
# ---------------------------------------------------------------------------

@mcp.tool()
def search_people(
    keywords: str,
    limit: int = 10,
) -> list[dict]:
    """Search LinkedIn people by keywords (e.g. 'recruiter Java Mexico')."""
    api = _get_api()
    results = api.search_people(
        keywords=keywords,
        limit=limit,
    )
    people = []
    for p in results:
        people.append({
            "name": f"{p.get('firstName', '')} {p.get('lastName', '')}".strip(),
            "headline": p.get("headline", ""),
            "location": p.get("location", ""),
            "profile_id": p.get("public_id", ""),
            "profile_url": f"https://www.linkedin.com/in/{p.get('public_id', '')}",
            "urn_id": p.get("urn_id", ""),
        })
    return people


@mcp.tool()
def get_profile(profile_id: str) -> dict:
    """Get a LinkedIn profile by public ID (e.g. 'alejandro-hernandez-loza')."""
    api = _get_api()
    profile = api.get_profile(profile_id)
    contact = api.get_profile_contact_info(profile_id)
    return {
        "name": f"{profile.get('firstName', '')} {profile.get('lastName', '')}",
        "headline": profile.get("headline", ""),
        "summary": profile.get("summary", ""),
        "location": profile.get("locationName", ""),
        "industry": profile.get("industryName", ""),
        "email": contact.get("email_address", ""),
        "websites": contact.get("websites", []),
    }


@mcp.tool()
def send_connection_request(
    profile_id: str,
    message: str = "",
) -> bool:
    """Send a connection request to a LinkedIn user. Message max 300 chars."""
    api = _get_api()
    if len(message) > 300:
        message = message[:297] + "..."
    try:
        api.add_connection(profile_id, message=message)
        logger.info(f"[linkedin_mcp] Connection request sent to {profile_id}")
        return True
    except Exception as e:
        logger.error(f"[linkedin_mcp] Connection request failed: {e}")
        return False


# ---------------------------------------------------------------------------
# Messaging Tools
# ---------------------------------------------------------------------------

@mcp.tool()
def get_conversations(limit: int = 20) -> list[dict]:
    """Get recent LinkedIn messaging conversations."""
    api = _get_api()
    convs = api.get_conversations()
    results = []
    for c in (convs.get("elements", []) or [])[:limit]:
        participants = c.get("participants", [])
        name = ""
        if participants:
            p = participants[0].get("com.linkedin.voyager.messaging.MessagingMember", {})
            mp = p.get("miniProfile", {})
            name = f"{mp.get('firstName', '')} {mp.get('lastName', '')}".strip()

        last_msg = ""
        events = c.get("events", [])
        if events:
            last_msg = events[0].get("eventContent", {}).get("com.linkedin.voyager.messaging.event.MessageEvent", {}).get("body", "")

        results.append({
            "conversation_id": c.get("entityUrn", "").split(":")[-1],
            "participant": name,
            "last_message": last_msg[:200],
            "last_activity": c.get("lastActivityAt", 0),
        })
    return results


@mcp.tool()
def send_message(
    conversation_id: str,
    message: str,
) -> bool:
    """Send a message in an existing LinkedIn conversation."""
    # KILL SWITCH — all outgoing messages blocked
    logger.warning(f"[linkedin_mcp] BLOCKED — send_message disabled (kill switch)")
    return False


# ---------------------------------------------------------------------------
# Feed & Publishing Tools
# ---------------------------------------------------------------------------

@mcp.tool()
def get_feed(limit: int = 10) -> list[dict]:
    """Get recent LinkedIn feed posts."""
    api = _get_api()
    posts = api.get_feed_posts(limit=limit)
    results = []
    for post in posts:
        author = post.get("author", "")
        text = post.get("commentary", "")
        results.append({
            "author": author,
            "text": text[:300] if text else "",
            "num_likes": post.get("numLikes", 0),
            "num_comments": post.get("numComments", 0),
        })
    return results


@mcp.tool()
def create_post(
    text: str,
    image_path: Optional[str] = None,
) -> bool:
    """Publish a post to LinkedIn. Optionally attach an image (absolute path to PNG/JPG)."""
    # KILL SWITCH — all outgoing posts blocked via MCP
    logger.warning(f"[linkedin_mcp] BLOCKED — create_post disabled (kill switch)")
    return False


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run()
