"""
LinkedIn Post Tool.

Publishes posts to LinkedIn via Playwright browser automation.
Uses the same cookie-based authentication pattern as linkedin_messages_tool.py.
"""
import json
import time
from typing import Optional

from loguru import logger

from config import settings


# ---------------------------------------------------------------------------
# Cookie helpers
# ---------------------------------------------------------------------------

def _load_cookies() -> dict:
    try:
        with open(settings.linkedin_cookies_file, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"[linkedin_post] Error loading cookies: {e}")
        return {}


def _build_playwright_context(headless: bool = True):
    """Returns (playwright, browser, context, page).

    Usa el contexto PERSISTENTE compartido (src/tools/linkedin_session.py) para
    fingerprint/sesión consistentes — antes cada post abría un new_context fresco
    y terminaba invalidando el JSESSIONID. `browser` se retorna como None porque
    el persistent context es browser+context en uno (el caller solo cierra context).
    """
    from src.tools import linkedin_session

    pw, context, page = linkedin_session.build_persistent_context(headless=headless)
    return pw, None, context, page


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def post_to_linkedin(
    text: str, image_path: Optional[str] = None, headless: bool = True
) -> bool:
    """Publish a post to LinkedIn. Returns True if successful."""
    pw = None
    browser = None
    try:
        pw, browser, context, page = _build_playwright_context(headless=headless)

        logger.info("[linkedin_post] Navigating to LinkedIn feed...")
        # domcontentloaded en vez de load: el feed de LinkedIn nunca dispara
        # 'load' del todo (streaming infinito) → timeout. domcontentloaded basta
        # para que el compositor exista; damos margen extra con el sleep.
        page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded", timeout=45000)
        time.sleep(6)

        # Click "Start a post" / "Iniciar una publicación"
        start_post_selectors = [
            # div-based selectors (LinkedIn 2024+ UI — "Start a post" es un div clickeable)
            'div.share-box-feed-entry__top-bar',
            'div[data-placeholder="Start a post, try a video or a document"]',
            'div[data-placeholder*="Start a post"]',
            'div.share-creation-state__placeholder',
            # button-based selectors (UI anterior)
            'button[aria-label="Start a post"]',
            'button[aria-label="Iniciar una publicación"]',
            'button.share-box-feed-entry__trigger',
            '[data-control-name="share.sharebox_feed_entry"]',
            'div.share-box-feed-entry__top-bar button',
            'button:has-text("Start a post")',
            'button:has-text("Iniciar una publicación")',
            # placeholders genéricos
            '[placeholder="Start a post, try a video or a document"]',
            'div:has-text("Start a post"):not(:has(div))',
        ]

        clicked = False
        for selector in start_post_selectors:
            try:
                elem = page.locator(selector).first
                if elem.is_visible(timeout=3000):
                    elem.click()
                    logger.info(f"[linkedin_post] Clicked start post button via: {selector}")
                    clicked = True
                    break
            except Exception:
                continue

        if not clicked:
            logger.error("[linkedin_post] Could not find 'Start a post' button")
            return False

        time.sleep(2)

        # Upload image FIRST (before text) — LinkedIn opens image editor modal
        if image_path:
            logger.info(f"[linkedin_post] Uploading image: {image_path}")
            image_uploaded = _upload_image(page, image_path)
            if not image_uploaded:
                logger.error("[linkedin_post] Image upload failed — aborting post (no posts without image)")
                return False
            time.sleep(2)

        # Find the text editor and type the post content
        text_editor_selectors = [
            'div[role="textbox"][contenteditable="true"]',
            '.ql-editor[contenteditable="true"]',
            '[data-placeholder="What do you want to talk about?"]',
            '[data-placeholder="¿De qué quieres hablar?"]',
            '.share-creation-state__editable-area [contenteditable="true"]',
            'div.editor-content[contenteditable="true"]',
        ]

        typed = False
        for selector in text_editor_selectors:
            try:
                editor = page.locator(selector).first
                if editor.is_visible(timeout=3000):
                    editor.click()
                    time.sleep(0.5)
                    editor.fill(text)
                    logger.info(f"[linkedin_post] Typed post text via: {selector}")
                    typed = True
                    break
            except Exception:
                continue

        if not typed:
            # Fallback: try keyboard type after clicking editor area
            try:
                page.keyboard.type(text, delay=20)
                typed = True
                logger.info("[linkedin_post] Typed post text via keyboard fallback")
            except Exception as e:
                logger.error(f"[linkedin_post] Could not type post text: {e}")
                return False

        time.sleep(1)

        # Click Post / Publicar button
        post_button_selectors = [
            'button.share-actions__primary-action',
            'button[aria-label="Post"]',
            'button[aria-label="Publicar"]',
            'button:has-text("Post")',
            'button:has-text("Publicar")',
            '.share-box_actions button.artdeco-button--primary',
            'button.artdeco-button--primary:has-text("Post")',
            'button.artdeco-button--primary:has-text("Publicar")',
        ]

        posted = False
        for selector in post_button_selectors:
            try:
                btn = page.locator(selector).first
                if btn.is_visible(timeout=3000) and btn.is_enabled(timeout=1000):
                    btn.click()
                    logger.info(f"[linkedin_post] Clicked post button via: {selector}")
                    posted = True
                    break
            except Exception:
                continue

        if not posted:
            # Debug: screenshot + dump visible buttons
            try:
                page.screenshot(path="data/screenshots/post_debug_buttons.png")
                btns = page.locator('button').all()
                for b in btns[:30]:
                    try:
                        txt = b.inner_text(timeout=500).strip()
                        if txt:
                            logger.info(f"[linkedin_post] visible button: '{txt[:60]}'")
                    except Exception:
                        pass
            except Exception:
                pass

            # Last resort: try any primary button in the modal
            try:
                modal_primary = page.locator('.artdeco-modal button.artdeco-button--primary').first
                if modal_primary.is_visible(timeout=2000):
                    btn_text = modal_primary.inner_text(timeout=1000).strip()
                    logger.info(f"[linkedin_post] Clicking modal primary button: '{btn_text}'")
                    modal_primary.click()
                    posted = True
            except Exception:
                pass

        if not posted:
            logger.error("[linkedin_post] Could not find Post/Publicar button")
            return False

        # Wait for post to be submitted
        time.sleep(4)

        # Verify success: page should still be at feed, no modal visible
        try:
            # Check if the modal/dialog was dismissed (means post was sent)
            modal_still_open = page.locator('.share-creation-state').is_visible(timeout=2000)
            if modal_still_open:
                logger.warning("[linkedin_post] Post modal still open after clicking Post")
                return False
        except Exception:
            pass  # Modal gone = success

        logger.info("[linkedin_post] Post published successfully")
        return True

    except Exception as e:
        logger.error(f"[linkedin_post] Error publishing post: {e}")
        return False
    finally:
        try:
            if browser:
                browser.close()
            else:
                context.close()  # persistent context = browser+context en uno
            if pw:
                pw.stop()
        except Exception:
            pass


def _upload_image(page, image_path: str) -> bool:
    """Upload an image to a LinkedIn post draft. Returns True if successful."""
    from pathlib import Path as _Path
    abs_path = str(_Path(image_path).resolve())

    def _confirm_editor() -> None:
        """El editor de imagen de LinkedIn pide Siguiente/Next/Done tras subir."""
        for next_sel in [
            'button:has-text("Siguiente")',
            'button:has-text("Next")',
            'button:has-text("Done")',
            'button:has-text("Listo")',
        ]:
            try:
                nb = page.locator(next_sel).first
                if nb.is_visible(timeout=3000):
                    nb.click()
                    logger.info(f"[linkedin_post] Editor de imagen: click {next_sel}")
                    time.sleep(2)
                    break
            except Exception:
                continue

    # Estrategia PREFERIDA: set_input_files directo sobre el <input type=file>
    # — programático, NO abre el diálogo nativo del SO (que congela el renderer).
    try:
        file_inputs = page.locator('input[type="file"]')
        if file_inputs.count() > 0:
            file_inputs.first.set_input_files(abs_path)
            time.sleep(4)
            logger.info("[linkedin_post] Imagen subida vía set_input_files (directo)")
            _confirm_editor()
            return True
    except Exception as e:
        logger.debug(f"[linkedin_post] set_input_files directo falló: {e}")

    # Click "Añadir contenido" / "Add media" button and catch file chooser
    media_selectors = [
        'button[aria-label="Añadir contenido"]',
        'button[aria-label="Add media"]',
        'button[aria-label="Add a photo"]',
        'button[aria-label="Agregar una foto"]',
        'button[aria-label*="photo"]',
        'button[aria-label*="media"]',
        'button[aria-label*="contenido"]',
    ]

    for selector in media_selectors:
        try:
            btn = page.locator(selector).first
            if not btn.is_visible(timeout=2000):
                continue

            with page.expect_file_chooser(timeout=10000) as fc_info:
                btn.click()
            file_chooser = fc_info.value
            file_chooser.set_files(abs_path)
            logger.info(f"[linkedin_post] Image uploaded via file_chooser: {selector}")
            time.sleep(4)

            # LinkedIn shows an image editor — click "Siguiente" / "Next" / "Done"
            for next_sel in [
                'button:has-text("Siguiente")',
                'button:has-text("Next")',
                'button:has-text("Done")',
                'button:has-text("Listo")',
            ]:
                try:
                    next_btn = page.locator(next_sel).first
                    if next_btn.is_visible(timeout=3000):
                        next_btn.click()
                        logger.info(f"[linkedin_post] Clicked next/done in image editor: {next_sel}")
                        time.sleep(2)
                        break
                except Exception:
                    continue

            return True
        except Exception as e:
            logger.debug(f"[linkedin_post] {selector} failed: {e}")
            continue

    # Fallback: try set_input_files on any file input
    try:
        file_inputs = page.locator('input[type="file"]')
        if file_inputs.count() > 0:
            file_inputs.first.set_input_files(abs_path)
            time.sleep(3)
            logger.info(f"[linkedin_post] Image uploaded via set_input_files fallback")
            return True
    except Exception as e:
        logger.debug(f"[linkedin_post] set_input_files fallback failed: {e}")

    logger.error(f"[linkedin_post] All image upload strategies failed for: {image_path}")
    return False
