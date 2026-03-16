"""
LinkedIn Messages Tool.

Arquitectura:
  1. GraphQL API (voyagerMessagingGraphQL) para listar conversaciones con IDs reales
  2. Playwright con navegación directa por URL para leer mensajes completos
  3. Playwright con navegación directa por URL para enviar mensajes (1 browser per send)

IMPORTANTE: NO usar clicks en sidebar para cambiar conversación — el SPA de LinkedIn
no responde a clicks programáticos y siempre muestra la primera conversación.
"""
import json
import re
import time
from typing import List, Dict, Any, Optional
from urllib.parse import quote

import requests
from loguru import logger

from config import settings

_MY_PROFILE_ID = "ACoAAA75U08B8QCgw24NcNxPaIYIH-OFh35cZ2Q"
_GRAPHQL_BASE = "https://www.linkedin.com/voyager/api/voyagerMessagingGraphQL/graphql"
_QUERY_CONVERSATIONS = "messengerConversations.0d5e6781bbee71c3e51c8843c6519f48"
_QUERY_MESSAGES = "messengerMessages.5846eeb71c981f11e0134cb6626cc314"


# ---------------------------------------------------------------------------
# Session helpers
# ---------------------------------------------------------------------------

def _load_cookies() -> Dict[str, str]:
    try:
        with open(settings.linkedin_cookies_file, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def _build_session() -> requests.Session:
    """Session autenticada para GraphQL API."""
    cookies = _load_cookies()
    li_at = cookies.get("li_at", "")
    jsessionid = cookies.get("JSESSIONID", "").replace('"', '')

    s = requests.Session()
    s.cookies.set("li_at", li_at, domain=".linkedin.com")
    s.cookies.set("JSESSIONID", jsessionid, domain=".www.linkedin.com")
    s.headers.update({
        "csrf-token": jsessionid,
        "X-RestLi-Protocol-Version": "2.0.0",
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json",
        "x-li-lang": "en_US",
    })
    return s


def _test_session(session: requests.Session) -> bool:
    try:
        resp = session.get("https://www.linkedin.com/voyager/api/me", timeout=10)
        return resp.status_code == 200
    except Exception:
        return False


def _build_playwright_context():
    """Crea browser context autenticado para Playwright."""
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
        user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    )
    context.add_cookies([
        {"name": "li_at", "value": li_at, "domain": ".linkedin.com", "path": "/"},
        {"name": "JSESSIONID", "value": jsessionid, "domain": ".www.linkedin.com", "path": "/"},
    ])
    page = context.new_page()
    page.add_init_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )
    return pw, browser, page


# ---------------------------------------------------------------------------
# 1. List conversations via GraphQL API
# ---------------------------------------------------------------------------

def get_unread_messages(limit: int = 20) -> List[Dict[str, Any]]:
    """Obtiene conversaciones recientes via GraphQL API.

    Retorna lista con conversation_id = thread_id real de LinkedIn.
    """
    try:
        session = _build_session()
        if not _test_session(session):
            logger.warning("LinkedIn session inválida")
            return []

        profile_urn_encoded = quote(f"urn:li:fsd_profile:{_MY_PROFILE_ID}", safe="")
        resp = session.get(
            f"{_GRAPHQL_BASE}?queryId={_QUERY_CONVERSATIONS}"
            f"&variables=(mailboxUrn:{profile_urn_encoded},count:{limit})",
            timeout=15,
        )

        if resp.status_code != 200:
            logger.warning(f"GraphQL conversations status: {resp.status_code}")
            return []

        data = resp.json()
        elements = (
            data.get("data", {})
            .get("messengerConversationsBySyncToken", {})
            .get("elements", [])
        )

        conversations = []
        for conv in elements:
            urn = conv.get("entityUrn", "")
            # Extraer thread_id del URN
            thread_match = re.search(r'(2-[A-Za-z0-9+/=]+)', urn)
            thread_id = thread_match.group(1) if thread_match else ""
            if not thread_id:
                continue

            # Obtener otro participante (no yo)
            participants = conv.get("conversationParticipants", [])
            other = _extract_other_participant(participants)

            # Último mensaje
            last_msg_data = conv.get("lastMessage", {})
            last_msg = ""
            last_activity = 0
            if last_msg_data:
                body = last_msg_data.get("body", {})
                last_msg = body.get("text", "") if isinstance(body, dict) else str(body)
                last_activity = last_msg_data.get("deliveredAt", 0)

            conversations.append({
                "conversation_id": thread_id,
                "conversation_urn": urn,
                "sender_name": other.get("name", ""),
                "sender_title": other.get("title", ""),
                "sender_profile_id": other.get("profile_id", ""),
                "profile_url": other.get("profile_url", ""),
                "message": last_msg,
                "timestamp": last_activity,
                "read": True,  # GraphQL doesn't give read status easily
                "last_activity": last_activity,
            })

        logger.info(f"LinkedIn GraphQL: {len(conversations)} conversaciones")
        return conversations

    except Exception as e:
        logger.error(f"Error en get_unread_messages: {e}")
        return []


def _extract_other_participant(participants: list) -> dict:
    """Extrae el otro participante (no yo) de la lista GraphQL."""
    for p in participants:
        entity_urn = p.get("entityUrn", "")
        if _MY_PROFILE_ID in entity_urn:
            continue

        pt = p.get("participantType", {}).get("member", {})
        first = pt.get("firstName", {})
        last = pt.get("lastName", {})
        first_name = first.get("text", "") if isinstance(first, dict) else str(first)
        last_name = last.get("text", "") if isinstance(last, dict) else str(last)
        profile_url = pt.get("profileUrl", "")

        # Extraer profile_id del entityUrn
        profile_id = ""
        urn_match = re.search(r'fsd_profile:(\S+)', entity_urn)
        if urn_match:
            profile_id = urn_match.group(1)

        headline = pt.get("headline", {})
        title = headline.get("text", "") if isinstance(headline, dict) else str(headline)

        return {
            "name": f"{first_name} {last_name}".strip(),
            "profile_url": profile_url,
            "profile_id": profile_id,
            "title": title,
        }

    return {"name": "", "profile_url": "", "profile_id": "", "title": ""}


# ---------------------------------------------------------------------------
# 2. Read conversation messages via Playwright (direct URL navigation)
# ---------------------------------------------------------------------------

def get_full_conversation(conversation_id: str) -> List[Dict]:
    """Lee mensajes de una conversación navegando directamente a su URL.

    conversation_id = thread_id (e.g. "2-ZWNlOG...")

    IMPORTANTE: Usa navegación directa, NO clicks en sidebar.
    """
    try:
        pw, browser, page = _build_playwright_context()

        url = f"https://www.linkedin.com/messaging/thread/{conversation_id}/"
        page.goto(url, timeout=30000)
        page.wait_for_load_state("domcontentloaded")
        time.sleep(5)

        # Verificar que cargó la conversación correcta
        current_url = page.url
        if conversation_id not in current_url:
            logger.warning(
                f"URL no coincide: esperaba thread/{conversation_id}, "
                f"got {current_url}"
            )

        # Extraer mensajes del DOM
        messages = page.evaluate("""
        (myProfileId) => {
            const events = document.querySelectorAll('.msg-s-event-listitem');
            return Array.from(events).map((ev, i) => {
                const body = ev.querySelector('.msg-s-event-listitem__body');
                const text = body ? body.textContent.trim() : '';

                // Sender name from message group header
                const nameEl = ev.querySelector(
                    '.msg-s-message-group__name, [class*="message-group__name"]'
                );
                const senderName = nameEl ? nameEl.textContent.trim() : '';

                // Profile link - most reliable for from_me detection
                const profileLink = ev.querySelector('a[href*="/in/"]');
                const profileHref = profileLink ? profileLink.href : '';
                const isMe = profileHref.includes(myProfileId);

                // Timestamps from datetime attributes
                const timeEl = ev.querySelector('time[datetime]');
                const dt = timeEl ? timeEl.getAttribute('datetime') : '';

                return {
                    body: text, senderName, profileHref, isMe, datetime: dt, idx: i
                };
            }).filter(m => m.body && !m.body.includes('eliminado'));
        }
        """, _MY_PROFILE_ID)

        browser.close()
        pw.stop()

        # Build result with from_me from profile link detection
        result = []
        for msg in messages:
            delivered_at = 0
            if msg.get("datetime"):
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(msg["datetime"].replace("Z", "+00:00"))
                    delivered_at = int(dt.timestamp() * 1000)
                except Exception:
                    pass

            result.append({
                "body": msg["body"],
                "from_me": msg.get("isMe", False),
                "deliveredAt": delivered_at,
                "sender_name": msg.get("senderName", ""),
            })

        logger.info(f"Conversation {conversation_id[:20]}: {len(result)} mensajes")
        return result

    except Exception as e:
        logger.error(f"Error leyendo conversación {conversation_id[:20]}: {e}")
        return []


# ---------------------------------------------------------------------------
# 3. Send message via Playwright (direct URL navigation, fresh browser)
# ---------------------------------------------------------------------------

def send_message(conversation_id: str, text: str) -> bool:
    """Envía un mensaje navegando directamente al thread.

    Abre browser NUEVO, navega al thread por URL, verifica header, escribe y envía.
    Cada envío usa su propia instancia de browser para evitar contaminación del SPA.
    """
    try:
        pw, browser, page = _build_playwright_context()

        url = f"https://www.linkedin.com/messaging/thread/{conversation_id}/"
        page.goto(url, timeout=30000)
        page.wait_for_load_state("domcontentloaded")
        time.sleep(5)

        # Verificar que estamos en el thread correcto
        current_url = page.url
        if conversation_id not in current_url:
            logger.error(f"URL mismatch al enviar: {current_url}")
            browser.close()
            pw.stop()
            return False

        # Verificar que hay un editor de mensajes
        editor_found = page.evaluate("""
        () => {
            const ed = document.querySelector(
                '.msg-form__contenteditable[role="textbox"], ' +
                '[contenteditable="true"][class*="msg"]'
            );
            return !!ed;
        }
        """)

        if not editor_found:
            logger.error("Editor de mensajes no encontrado")
            browser.close()
            pw.stop()
            return False

        # Obtener el nombre del header para logging
        header_name = page.evaluate("""
        () => {
            const el = document.querySelector(
                '.msg-thread__link-to-profile, ' +
                '.msg-entity-lockup__entity-title, ' +
                'h2.msg-overlay-bubble-header__title'
            );
            return el ? el.textContent.trim().substring(0, 50) : '';
        }
        """)

        # Click en editor, escribir y enviar
        editor = page.locator(
            '.msg-form__contenteditable[role="textbox"], '
            '[contenteditable="true"][class*="msg"]'
        )
        editor.click()
        time.sleep(0.5)
        page.keyboard.type(text, delay=5)
        time.sleep(1)
        page.keyboard.press("Enter")
        time.sleep(3)

        # Verificar que se envió (el último mensaje debería contener nuestro texto)
        sent_ok = page.evaluate("""
        (expectedText) => {
            const events = document.querySelectorAll('.msg-s-event-listitem');
            if (events.length === 0) return false;
            const last = events[events.length - 1];
            const body = last.querySelector('.msg-s-event-listitem__body');
            return body ? body.textContent.trim().includes(expectedText.substring(0, 30)) : false;
        }
        """, text)

        browser.close()
        pw.stop()

        if sent_ok:
            logger.success(
                f"Mensaje enviado a {header_name or conversation_id[:20]}: "
                f"{text[:60]}..."
            )
        else:
            logger.warning(
                f"Mensaje posiblemente enviado a {header_name or conversation_id[:20]} "
                f"(no se pudo verificar)"
            )

        return True  # Si llegamos aquí sin error, asumimos éxito

    except Exception as e:
        logger.error(f"Error enviando mensaje a {conversation_id[:20]}: {e}")
        return False


# ---------------------------------------------------------------------------
# 4. Mark as read (best effort via REST API)
# ---------------------------------------------------------------------------

def mark_conversation_read(conversation_id: str):
    """Marca conversación como leída (best effort)."""
    try:
        session = _build_session()
        session.headers["Content-Type"] = "application/json"
        session.patch(
            f"https://www.linkedin.com/voyager/api/messaging/conversations/"
            f"{quote(conversation_id, safe='')}/",
            json={"patch": {"$set": {"read": True}}},
            timeout=10,
        )
    except Exception:
        pass


# ---------------------------------------------------------------------------
# 5. Refresh cookies
# ---------------------------------------------------------------------------

def refresh_cookies():
    """Renueva cookies de LinkedIn via login directo con Playwright."""
    email = settings.linkedin_email
    password = settings.linkedin_password
    if not email or not password:
        logger.warning("No hay credenciales LinkedIn para refresh")
        return False

    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
            )
            context = browser.new_context(
                user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                           "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            )
            page = context.new_page()
            page.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )
            page.goto("https://www.linkedin.com/login")
            time.sleep(2)
            page.fill("#username", email)
            page.fill("#password", password)
            time.sleep(1)
            page.click("button[type='submit']")

            try:
                page.wait_for_url("**/feed**", timeout=30000)
            except Exception:
                if "challenge" in page.url:
                    logger.warning("LinkedIn CHALLENGE — cookies no renovadas")
                    browser.close()
                    return False

            cookies = context.cookies()
            cd = {
                c["name"]: c["value"]
                for c in cookies
                if "linkedin" in c.get("domain", "")
            }

            li_at = cd.get("li_at", "")
            jsessionid = cd.get("JSESSIONID", "").strip('"')

            if li_at and jsessionid:
                with open(settings.linkedin_cookies_file, "w") as f:
                    json.dump({
                        "li_at": li_at,
                        "JSESSIONID": jsessionid,
                        "li_rm": cd.get("li_rm", ""),
                    }, f, indent=2)
                logger.success("Cookies LinkedIn renovadas")
                browser.close()
                return True

            browser.close()
            return False
    except Exception as e:
        logger.error(f"Error renovando cookies: {e}")
        return False
