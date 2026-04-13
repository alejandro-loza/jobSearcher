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

# ── GLOBAL KILL SWITCH ────────────────────────────────────────────────────────
# When True, send_message() will ALWAYS return False without sending anything.
# This is the last line of defense — no LinkedIn message leaves the system.
LINKEDIN_SENDING_BLOCKED = True

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


_PROFILE_DIR = "data/linkedin_browser_profile"


def _build_playwright_context():
    """Crea persistent browser context autenticado para Playwright.

    Usa un perfil de Chromium persistente en disco (_PROFILE_DIR) para que
    LinkedIn vea la misma "computadora" siempre — localStorage, IndexedDB,
    historial, cookies del navegador, etc. se conservan entre ejecuciones.
    Las cookies de li_at/JSESSIONID se inyectan solo si no existen ya en el perfil.
    """
    import os
    from playwright.sync_api import sync_playwright

    os.makedirs(_PROFILE_DIR, exist_ok=True)

    cookies = _load_cookies()
    li_at = cookies.get("li_at", "")
    jsessionid = cookies.get("JSESSIONID", "").replace('"', '')

    pw = sync_playwright().start()
    context = pw.chromium.launch_persistent_context(
        user_data_dir=_PROFILE_DIR,
        headless=True,
        args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
        user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        viewport={"width": 1280, "height": 800},
    )
    context.add_init_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )

    # Siempre inyectar cookies frescas del archivo (sobrescribir si ya existen en el perfil)
    new_cookies = []
    if li_at:
        new_cookies.append({"name": "li_at", "value": li_at, "domain": ".linkedin.com", "path": "/"})
    if jsessionid:
        new_cookies.append({"name": "JSESSIONID", "value": f'"{jsessionid}"', "domain": ".www.linkedin.com", "path": "/"})
    if new_cookies:
        context.add_cookies(new_cookies)
        logger.debug(f"[linkedin] Inyectadas {len(new_cookies)} cookies frescas al perfil persistente")

    # Persistent context ya tiene una página por defecto, reusar o crear
    page = context.pages[0] if context.pages else context.new_page()

    # Retornamos None como browser — persistent context es browser+context en uno
    return pw, context, page


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
# 2. Read conversation messages via Playwright (sidebar click)
# ---------------------------------------------------------------------------

def _open_conversation_in_messaging(page, sender_name: str, conversation_id: str) -> bool:
    """Navigate to /messaging/ and click on the conversation by sender name.

    Direct URL navigation to /messaging/thread/ID/ no longer works on LinkedIn
    (shows error). Instead we load /messaging/ and click the conversation item.
    """
    # Navigate to messaging page
    page.goto("https://www.linkedin.com/messaging/", timeout=20000)
    page.wait_for_load_state("domcontentloaded")
    time.sleep(4)

    # Try clicking on conversation by sender name in sidebar
    # LinkedIn sidebar items contain the sender name as text
    conv_items = page.locator('.msg-conversations-container__convo-item-link, .msg-conversation-listitem__link, li.msg-conversation-listitem')

    count = conv_items.count()
    for i in range(min(count, 25)):
        try:
            item = conv_items.nth(i)
            item_text = item.inner_text()
            if sender_name.split()[0].lower() in item_text.lower():
                item.click()
                time.sleep(3)
                return True
        except Exception:
            continue

    # Fallback: try clicking by any element containing the name
    try:
        name_el = page.locator(f'text="{sender_name}"').first
        if name_el.is_visible(timeout=2000):
            name_el.click()
            time.sleep(3)
            return True
    except Exception:
        pass

    # Fallback 2: try first name only
    first_name = sender_name.split()[0]
    try:
        name_el = page.locator(f'text="{first_name}"').first
        if name_el.is_visible(timeout=2000):
            name_el.click()
            time.sleep(3)
            return True
    except Exception:
        pass

    logger.warning(f"Could not find conversation for '{sender_name}' in sidebar")
    return False


def get_full_conversation(conversation_id: str, sender_name: str = "") -> List[Dict]:
    """Lee mensajes de una conversación clickeando en el sidebar de /messaging/.

    conversation_id = thread_id (e.g. "2-ZWNlOG...")
    sender_name = nombre del participante (para encontrarlo en el sidebar)
    """
    try:
        pw, browser, page = _build_playwright_context()

        # Open the conversation via sidebar click
        if sender_name:
            opened = _open_conversation_in_messaging(page, sender_name, conversation_id)
        else:
            # Fallback: try direct URL (may fail on some accounts)
            page.goto(
                f"https://www.linkedin.com/messaging/thread/{conversation_id}/",
                timeout=20000,
            )
            page.wait_for_load_state("domcontentloaded")
            time.sleep(5)
            opened = True

        if not opened:
            browser.close()
            pw.stop()
            return []

        # Extract messages from DOM — try multiple selector strategies
        messages = page.evaluate("""
        (myProfileId) => {
            // Strategy 1: new LinkedIn message elements
            let events = document.querySelectorAll(
                '.msg-s-event-listitem, .msg-s-message-list-content .msg-s-event, [class*="message-list"] li'
            );

            // Strategy 2: broader selectors if strategy 1 fails
            if (events.length === 0) {
                events = document.querySelectorAll(
                    '[data-control-name="message"], .msg-s-message-group, [class*="msg-s-event"]'
                );
            }

            // Strategy 3: look in the conversation detail panel
            if (events.length === 0) {
                const panel = document.querySelector(
                    '.msg-s-message-list, .msg-thread, [class*="message-list"]'
                );
                if (panel) {
                    events = panel.querySelectorAll('li, [class*="event"]');
                }
            }

            return Array.from(events).map((ev, i) => {
                // Extract message body text
                const bodyEl = ev.querySelector(
                    '.msg-s-event-listitem__body, .msg-s-event__content, ' +
                    '[class*="event-listitem__body"], p[class*="body"]'
                );
                let text = bodyEl ? bodyEl.textContent.trim() : '';

                // Fallback: get all paragraph text
                if (!text) {
                    const paras = ev.querySelectorAll('p');
                    text = Array.from(paras).map(p => p.textContent.trim()).join(' ');
                }

                // Sender name
                const nameEl = ev.querySelector(
                    '.msg-s-message-group__name, [class*="message-group__name"], ' +
                    '.msg-s-message-group__profile-link, [class*="sender"]'
                );
                const senderName = nameEl ? nameEl.textContent.trim() : '';

                // Profile link for from_me detection
                const profileLink = ev.querySelector('a[href*="/in/"]');
                const profileHref = profileLink ? profileLink.href : '';
                const isMe = profileHref.includes(myProfileId);

                // Timestamp
                const timeEl = ev.querySelector('time[datetime]');
                const dt = timeEl ? timeEl.getAttribute('datetime') : '';

                return {
                    body: text, senderName, profileHref, isMe, datetime: dt, idx: i
                };
            }).filter(m => m.body && m.body.length > 1 && !m.body.includes('eliminado'));
        }
        """, _MY_PROFILE_ID)

        browser.close()
        pw.stop()

        # Build result
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
# 3a. Send message via HTTP REST API (no browser needed)
# ---------------------------------------------------------------------------

def _send_message_http(conversation_id: str, text: str) -> bool:
    """Envía mensaje via REST API sin Playwright.

    Usa el mismo endpoint que linkedin_api: POST /messaging/conversations/{id}/events
    """
    import uuid

    session = _build_session()
    if not _test_session(session):
        logger.debug("[http_send] Sesión inválida, no se puede enviar por HTTP")
        return False

    session.headers["Content-Type"] = "application/json"

    # Extraer URN del conversation_id (formato: 2-BASE64== → necesitamos solo el ID)
    # linkedin_api usa conversation_urn_id que es el mismo formato
    payload = {
        "eventCreate": {
            "originToken": str(uuid.uuid4()),
            "value": {
                "com.linkedin.voyager.messaging.create.MessageCreate": {
                    "attributedBody": {
                        "text": text,
                        "attributes": [],
                    },
                    "attachments": [],
                }
            },
        },
        "dedupeByClientGeneratedToken": False,
    }

    url = (
        f"https://www.linkedin.com/voyager/api/messaging/conversations/"
        f"{quote(conversation_id, safe='')}/events"
    )
    try:
        resp = session.post(url, json=payload, params={"action": "create"}, timeout=15)
        if resp.status_code == 201:
            logger.success(f"[http_send] Mensaje enviado via HTTP API a {conversation_id[:20]}")
            return True
        else:
            logger.warning(f"[http_send] HTTP {resp.status_code}: {resp.text[:200]}")
            return False
    except Exception as e:
        logger.debug(f"[http_send] Error: {e}")
        return False


# ---------------------------------------------------------------------------
# 3b. Send message via Playwright (fallback, direct URL navigation)
# ---------------------------------------------------------------------------

def send_message(
    conversation_id: str,
    text: str,
    sender_name: str = "",
    conversation_history: list = None,
    _bypass_decision_agent: bool = False,
) -> bool:
    """Envía un mensaje de LinkedIn. REQUIERE aprobación del response_decision_agent.

    Args:
        conversation_id: ID de la conversación LinkedIn
        text: Texto a enviar
        sender_name: Nombre del destinatario (para contexto)
        conversation_history: OBLIGATORIO — historial [{body/message_text, from_me, ...}]
        _bypass_decision_agent: Solo True cuando Alejandro aprueba manualmente via WhatsApp
    """
    # ── GLOBAL KILL SWITCH — nothing gets sent if True ────────────────────
    if LINKEDIN_SENDING_BLOCKED:
        logger.warning(f"[KILL SWITCH] LinkedIn msg a {sender_name or conversation_id} BLOQUEADO — LINKEDIN_SENDING_BLOCKED=True")
        return False

    # ── RESPONSE DECISION AGENT — última palabra ─────────────────────────
    if not _bypass_decision_agent:
        from src.agents.response_decision_agent import approve_outgoing
        approved, reason = approve_outgoing(
            to=sender_name or conversation_id,
            subject=f"LinkedIn conversation {conversation_id[:20]}",
            body=text,
            conversation_history=conversation_history or [],
            sender_name=sender_name,
            source="linkedin",
        )
        if not approved:
            logger.warning(f"[decision_agent] LinkedIn msg a {sender_name or conversation_id} RECHAZADO — {reason}")
            return False

    # ── Intentar envío por HTTP REST API primero (sin Playwright) ──────────
    if _send_message_http(conversation_id, text):
        logger.success(f"[send] Enviado via HTTP a {sender_name or conversation_id[:20]}")
        return True
    logger.info("[send] HTTP falló, cayendo a Playwright...")

    try:
        pw, browser, page = _build_playwright_context()

        # Open conversation via sidebar
        if sender_name:
            opened = _open_conversation_in_messaging(page, sender_name, conversation_id)
        else:
            # Fallback: direct URL
            page.goto(
                f"https://www.linkedin.com/messaging/thread/{conversation_id}/",
                timeout=20000,
            )
            page.wait_for_load_state("domcontentloaded")
            time.sleep(5)
            opened = True

        if not opened:
            logger.error(f"Could not open conversation for '{sender_name}'")
            browser.close()
            pw.stop()
            return False

        # Find the message editor — try multiple selectors
        editor = None
        for sel in [
            '.msg-form__contenteditable[role="textbox"]',
            '[contenteditable="true"][class*="msg"]',
            '[role="textbox"]',
            'div[contenteditable="true"]',
        ]:
            try:
                loc = page.locator(sel).first
                if loc.is_visible(timeout=2000):
                    editor = loc
                    break
            except Exception:
                continue

        if not editor:
            logger.error("Editor de mensajes no encontrado")
            # Take screenshot for debugging
            page.screenshot(path=f"data/screenshots/send_error_{int(time.time())}.png")
            browser.close()
            pw.stop()
            return False

        # Click editor, type message, send
        editor.click()
        time.sleep(0.5)
        page.keyboard.type(text, delay=5)
        time.sleep(1)
        page.keyboard.press("Enter")
        time.sleep(3)

        # Take screenshot as proof
        proof_path = f"data/screenshots/sent_{sender_name.replace(' ','_')[:15]}_{int(time.time())}.png"
        page.screenshot(path=proof_path)
        logger.success(
            f"Mensaje enviado a {sender_name or conversation_id[:20]}: "
            f"{text[:60]}... | proof: {proof_path}"
        )

        browser.close()
        pw.stop()
        return True

    except Exception as e:
        logger.error(f"Error enviando mensaje a {sender_name or conversation_id[:20]}: {e}")
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
    """Renueva cookies de LinkedIn via login directo con contexto limpio.

    Usa un browser efímero (sin persistent profile) para el login — evita
    el redirect loop que ocurre cuando el perfil persistente tiene estado corrupto.
    Después de obtener cookies frescas, las inyecta también al perfil persistente.
    """
    import os
    from playwright.sync_api import sync_playwright

    email = settings.linkedin_email
    password = settings.linkedin_password
    if not email or not password:
        logger.warning("No hay credenciales LinkedIn (LINKEDIN_EMAIL/PASSWORD en .env)")
        return False

    try:
        pw = sync_playwright().start()
        # Contexto efímero — sin estado previo que pueda corromper el login
        # headless=False para evitar detección de bot por LinkedIn en el login
        browser = pw.chromium.launch(
            headless=False,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled",
                  "--window-size=1280,800"],
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
        )
        context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        page = context.new_page()

        logger.info("[refresh] Haciendo login en LinkedIn (ventana visible)...")
        page.goto("https://www.linkedin.com/login", wait_until="domcontentloaded", timeout=30000)
        time.sleep(3)
        page.fill("#username", email)
        time.sleep(0.5)
        page.fill("#password", password)
        time.sleep(1)
        page.click("button[type='submit']")

        try:
            page.wait_for_url("**/feed**", timeout=30000)
            time.sleep(2)
        except Exception:
            current = page.url
            if "challenge" in current or "checkpoint" in current:
                logger.warning(f"[refresh] LinkedIn CHALLENGE en {current} — se requiere verificación manual")
                page.screenshot(path="data/screenshots/linkedin_challenge.png")
                browser.close()
                pw.stop()
                return False
            logger.warning(f"[refresh] URL inesperada post-login: {current}")
            browser.close()
            pw.stop()
            return False

        # Extraer cookies frescas
        all_cookies = context.cookies("https://www.linkedin.com")
        cd = {c["name"]: c["value"] for c in all_cookies}
        li_at = cd.get("li_at", "")
        jsessionid = cd.get("JSESSIONID", "").strip('"')

        if not li_at or not jsessionid:
            logger.error("[refresh] Login exitoso pero no se encontraron cookies li_at/JSESSIONID")
            browser.close()
            pw.stop()
            return False

        # Guardar en archivo
        with open(settings.linkedin_cookies_file, "w") as f:
            json.dump({
                "li_at": li_at,
                "JSESSIONID": jsessionid,
                "li_rm": cd.get("li_rm", ""),
            }, f, indent=2)
        logger.success("[refresh] Cookies LinkedIn renovadas y guardadas")

        browser.close()
        pw.stop()

        # Limpiar el perfil persistente para que tome las cookies frescas
        import shutil
        if os.path.exists(_PROFILE_DIR):
            shutil.rmtree(_PROFILE_DIR)
            logger.info("[refresh] Perfil persistente limpiado — se recreará con cookies frescas")

        return True

    except Exception as e:
        logger.error(f"[refresh] Error renovando cookies: {e}")
        return False
