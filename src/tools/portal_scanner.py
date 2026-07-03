"""
Portal scanner zero-token — hits APIs públicas de Greenhouse, Ashby y Lever
directamente. Cero tokens de LLM: solo HTTP + JSON.

Port de career-ops/scan.mjs adaptado a jobSearcher:
- lee config/portals.yml (lista de empresas + filtros de título)
- escanea en paralelo con httpx.AsyncClient
- filtra por keywords y dedup contra JobTracker
- guarda jobs nuevos en SQLite (status='found') con source='greenhouse-api' etc.

Usage:
    from src.tools import portal_scanner
    result = portal_scanner.scan_all()           # scan todas
    result = portal_scanner.scan_all(dry_run=True)
    result = portal_scanner.scan_company("Globant")
"""

from __future__ import annotations

import asyncio
import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

import httpx
import yaml
from loguru import logger

from src.db.tracker import JobTracker
from src.tools import liveness

PORTALS_PATH = Path("config/portals.yml")
CONCURRENCY = 10
FETCH_TIMEOUT = 10.0


# ── API detection ─────────────────────────────────────────────────────


@dataclass
class PortalAPI:
    type: str  # greenhouse | ashby | lever
    url: str


def detect_api(company: dict) -> Optional[PortalAPI]:
    """Detecta qué API usa el careers_url de la empresa."""
    if company.get("api") and "greenhouse" in company["api"]:
        return PortalAPI("greenhouse", company["api"])

    url = company.get("careers_url", "")

    m = re.search(r"jobs\.ashbyhq\.com/([^/?#]+)", url)
    if m:
        return PortalAPI(
            "ashby",
            f"https://api.ashbyhq.com/posting-api/job-board/{m.group(1)}?includeCompensation=true",
        )

    m = re.search(r"jobs\.lever\.co/([^/?#]+)", url)
    if m:
        return PortalAPI("lever", f"https://api.lever.co/v0/postings/{m.group(1)}")

    m = re.search(r"job-boards(?:\.eu)?\.greenhouse\.io/([^/?#]+)", url)
    if m:
        return PortalAPI(
            "greenhouse",
            f"https://boards-api.greenhouse.io/v1/boards/{m.group(1)}/jobs",
        )

    m = re.search(r"boards\.greenhouse\.io/([^/?#]+)", url)
    if m:
        return PortalAPI(
            "greenhouse",
            f"https://boards-api.greenhouse.io/v1/boards/{m.group(1)}/jobs?content=true",
        )

    return None


# ── API parsers — normalizan al schema de jobTracker ──────────────────


def _mk_id(company: str, url: str, title: str) -> str:
    raw = f"{company}|{url}|{title}".lower()
    return hashlib.md5(raw.encode()).hexdigest()


def parse_greenhouse(data: dict, company: str) -> list[dict]:
    jobs = []
    for j in data.get("jobs", []):
        url = j.get("absolute_url", "")
        title = j.get("title", "")
        loc = (j.get("location") or {}).get("name", "")
        jobs.append(
            {
                "id": _mk_id(company, url, title),
                "title": title,
                "company": company,
                "location": loc,
                "url": url,
                "description": (j.get("content") or "")[:5000],
                "source": "greenhouse-api",
                "easy_apply": False,
            }
        )
    return jobs


def parse_ashby(data: dict, company: str) -> list[dict]:
    jobs = []
    for j in data.get("jobs", []):
        url = j.get("jobUrl", "")
        title = j.get("title", "")
        loc = j.get("location", "") or ""
        jobs.append(
            {
                "id": _mk_id(company, url, title),
                "title": title,
                "company": company,
                "location": loc,
                "url": url,
                "description": (
                    j.get("descriptionPlain") or j.get("descriptionHtml") or ""
                )[:5000],
                "source": "ashby-api",
                "easy_apply": False,
                "salary": _ashby_salary(j),
            }
        )
    return jobs


def _ashby_salary(j: dict) -> str:
    comp = j.get("compensation") or {}
    tiers = comp.get("compensationTierSummary") or []
    if tiers:
        return " | ".join(str(t) for t in tiers)
    return ""


def parse_lever(data: list, company: str) -> list[dict]:
    if not isinstance(data, list):
        return []
    jobs = []
    for j in data:
        url = j.get("hostedUrl", "")
        title = j.get("text", "")
        cats = j.get("categories") or {}
        jobs.append(
            {
                "id": _mk_id(company, url, title),
                "title": title,
                "company": company,
                "location": cats.get("location", "") or "",
                "url": url,
                "description": (
                    j.get("descriptionPlain") or j.get("description") or ""
                )[:5000],
                "source": "lever-api",
                "easy_apply": False,
            }
        )
    return jobs


PARSERS: dict[str, Callable] = {
    "greenhouse": parse_greenhouse,
    "ashby": parse_ashby,
    "lever": parse_lever,
}


# ── Title filter ──────────────────────────────────────────────────────


def build_title_filter(cfg: dict) -> Callable[[str], bool]:
    positive = [k.lower() for k in (cfg or {}).get("positive", [])]
    negative = [k.lower() for k in (cfg or {}).get("negative", [])]

    def check(title: str) -> bool:
        low = (title or "").lower()
        has_pos = not positive or any(k in low for k in positive)
        has_neg = any(k in low for k in negative)
        return has_pos and not has_neg

    return check


def build_location_filter(cfg: dict) -> Callable[[str], bool]:
    positive = [k.lower() for k in (cfg or {}).get("positive", [])]
    negative = [k.lower() for k in (cfg or {}).get("negative", [])]
    mexico_kw = [
        "mexico",
        "mexico city",
        "cdmx",
        "polanco",
        "monterrey",
        "guadalajara",
        "latam",
    ]

    def check(location: str) -> bool:
        low = (location or "").lower()
        if not low or low in ("n/a", "na", "not specified"):
            return True
        if any(k in low for k in negative):
            return False
        if any(k in low for k in mexico_kw):
            return True
        return False

    return check


# ── Fetch ─────────────────────────────────────────────────────────────


async def _fetch(client: httpx.AsyncClient, api: PortalAPI) -> Any:
    resp = await client.get(api.url, timeout=FETCH_TIMEOUT)
    resp.raise_for_status()
    return resp.json()


# ── Main ──────────────────────────────────────────────────────────────


@dataclass
class ScanResult:
    scanned: int = 0
    found: int = 0
    filtered: int = 0
    dupes: int = 0
    added: int = 0
    skipped_expired: int = 0
    new_offers: list[dict] = field(default_factory=list)
    errors: list[dict] = field(default_factory=list)


async def _scan_async(
    companies: list[dict],
    title_filter: Callable[[str], bool],
    location_filter: Callable[[str], bool],
    tracker: JobTracker,
    dry_run: bool,
    check_liveness: bool,
) -> ScanResult:
    result = ScanResult()
    targets = [
        (c, detect_api(c)) for c in companies if c.get("enabled", True) is not False
    ]
    targets = [(c, api) for c, api in targets if api is not None]
    result.scanned = len(targets)

    sem = asyncio.Semaphore(CONCURRENCY)

    async with httpx.AsyncClient(headers={"User-Agent": "jobSearcher/1.0"}) as client:

        async def scan_one(company: dict, api: PortalAPI):
            async with sem:
                try:
                    data = await _fetch(client, api)
                    jobs = PARSERS[api.type](data, company["name"])
                    result.found += len(jobs)

                    for job in jobs:
                        if not title_filter(job["title"]):
                            result.filtered += 1
                            continue

                        if not location_filter(job.get("location", "")):
                            result.filtered += 1
                            continue

                        # dedup contra DB (por ID hash + URL)
                        if tracker.job_exists(job["id"]) or tracker.job_url_exists(
                            job["url"]
                        ):
                            result.dupes += 1
                            continue

                        if check_liveness:
                            skip, reason = liveness.should_skip_job(job)
                            if skip:
                                result.skipped_expired += 1
                                logger.debug(f"[skipped] {job['title']} — {reason}")
                                continue

                        result.new_offers.append(job)

                        if not dry_run:
                            if tracker.save_job(job):
                                result.added += 1
                except Exception as e:
                    result.errors.append({"company": company["name"], "error": str(e)})
                    logger.warning(f"[portal_scan] {company['name']} failed: {e}")

        await asyncio.gather(*[scan_one(c, api) for c, api in targets])

    return result


def scan_all(dry_run: bool = False, check_liveness: bool = True) -> ScanResult:
    """Escanea todas las empresas en portals.yml."""
    if not PORTALS_PATH.exists():
        raise FileNotFoundError(
            f"{PORTALS_PATH} no existe. Copia config/portals.example.yml primero."
        )

    cfg = yaml.safe_load(PORTALS_PATH.read_text())
    companies = cfg.get("tracked_companies", [])
    title_filter = build_title_filter(cfg.get("title_filter", {}))
    location_filter = build_location_filter(cfg.get("location_filter", {}))
    tracker = JobTracker()

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(
                asyncio.run,
                _scan_async(
                    companies,
                    title_filter,
                    location_filter,
                    tracker,
                    dry_run,
                    check_liveness,
                ),
            )
            return future.result()
    else:
        return asyncio.run(
            _scan_async(
                companies,
                title_filter,
                location_filter,
                tracker,
                dry_run,
                check_liveness,
            )
        )


def scan_company(name: str, dry_run: bool = False) -> ScanResult:
    """Escanea una sola empresa (útil para debug)."""
    if not PORTALS_PATH.exists():
        raise FileNotFoundError(f"{PORTALS_PATH} no existe.")

    cfg = yaml.safe_load(PORTALS_PATH.read_text())
    companies = [
        c
        for c in cfg.get("tracked_companies", [])
        if name.lower() in c.get("name", "").lower()
    ]
    if not companies:
        raise ValueError(f"No encontré '{name}' en portals.yml")

    title_filter = build_title_filter(cfg.get("title_filter", {}))
    location_filter = build_location_filter(cfg.get("location_filter", {}))
    tracker = JobTracker()
    return asyncio.run(
        _scan_async(
            companies,
            title_filter,
            location_filter,
            tracker,
            dry_run,
            check_liveness=True,
        )
    )


def print_summary(r: ScanResult) -> None:
    logger.info("━" * 50)
    logger.info(f"Portal Scan — {r.scanned} empresas escaneadas")
    logger.info("━" * 50)
    logger.info(f"Jobs encontrados:    {r.found}")
    logger.info(f"Filtrados (título):  {r.filtered}")
    logger.info(f"Duplicados:          {r.dupes}")
    logger.info(f"Expirados (ghost):   {r.skipped_expired}")
    logger.info(f"Nuevos agregados:    {r.added}")
    if r.errors:
        logger.warning(f"Errores: {len(r.errors)}")
        for e in r.errors:
            logger.warning(f"  ✗ {e['company']}: {e['error']}")


if __name__ == "__main__":
    import sys

    dry = "--dry-run" in sys.argv
    result = scan_all(dry_run=dry)
    print_summary(result)
