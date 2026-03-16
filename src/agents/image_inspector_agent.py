"""
Image Inspector Agent.

Inspects infographic images for LinkedIn posts:
1. Factual accuracy — verifies all text/data in the image matches source data
2. Design quality — checks readability, layout, visual appeal
3. Deletes failing images, auto-publishes passing ones
"""

import base64
import json
import os
import re
from datetime import datetime
from typing import Optional

from langchain_core.messages import HumanMessage, SystemMessage
from loguru import logger

from config import settings
from src.agents import coordinator
from src.tools import linkedin_post_tool

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

POSTS_LOG_FILE = "data/linkedin_posts_log.json"
IMAGES_DIR = "data/linkedin_images"

DESIGN_QUALITY_THRESHOLD = 60  # 0-100
FACTUAL_THRESHOLD = 0.70       # 0-1


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_log() -> dict:
    if os.path.exists(POSTS_LOG_FILE):
        with open(POSTS_LOG_FILE) as f:
            return json.load(f)
    return {"posts": [], "topics_used": []}


def _save_log(data: dict):
    with open(POSTS_LOG_FILE, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)


def _load_image_b64(image_path: str) -> Optional[str]:
    """Read PNG from disk, return base64 string."""
    if not image_path or not os.path.exists(image_path):
        return None
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def _extract_json(raw: str) -> Optional[dict]:
    """Extract JSON from LLM response (handles markdown blocks)."""
    # Try direct parse
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    # Try markdown block
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    # Try any JSON object
    m = re.search(r"\{.*\}", raw, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass
    return None


# ---------------------------------------------------------------------------
# Inspection functions
# ---------------------------------------------------------------------------

def extract_infographic_text(image_b64: str) -> Optional[dict]:
    """Use vision LLM to extract all text visible in the infographic."""
    prompt = """You are inspecting an infographic image for a LinkedIn post.
Extract ALL visible text from this image and return it as structured JSON.

Return format:
{
  "title": "exact title text",
  "subtitle": "exact subtitle if any",
  "type": "tips|code|comparison|flow",
  "items": [
    {"label": "item label/title", "content": "item description or value"}
  ],
  "all_text_readable": true or false,
  "truncated_text": ["list any text that appears cut off or unreadable"],
  "overlapping_text": ["list any text that overlaps with other elements"],
  "technical_terms": ["list all version numbers, API names, class names, metrics mentioned"]
}

Return ONLY the JSON, no extra text."""

    try:
        raw = coordinator.invoke_vision("image_inspection", prompt, image_b64)
        return _extract_json(raw)
    except Exception as e:
        logger.error(f"[image_inspector] Vision extraction failed: {e}")
        return None


def verify_factual_accuracy(
    extracted: dict,
    post_text: str,
) -> tuple[bool, float, str]:
    """
    Cross-check extracted text from image against the post text.
    Uses text LLM to verify technical facts.
    """
    terms = extracted.get("technical_terms", [])
    items = extracted.get("items", [])
    truncated = extracted.get("truncated_text", [])
    overlapping = extracted.get("overlapping_text", [])

    # Immediate fail: unreadable text
    if not extracted.get("all_text_readable", True):
        issues = []
        if truncated:
            issues.append(f"Truncated: {truncated}")
        if overlapping:
            issues.append(f"Overlapping: {overlapping}")
        return False, 0.3, f"Text readability issues: {'; '.join(issues)}"

    # Build verification prompt
    items_text = "\n".join(
        f"- {it.get('label', '')}: {it.get('content', '')}" for it in items
    )

    prompt = f"""You are a technical fact-checker. Verify the accuracy of this infographic content.

POST TEXT (source of truth):
{post_text}

INFOGRAPHIC CONTENT (extracted from image):
Title: {extracted.get('title', 'N/A')}
Subtitle: {extracted.get('subtitle', 'N/A')}
Items:
{items_text}

Technical terms found: {', '.join(terms) if terms else 'none'}

IMPORTANT CONTEXT: An infographic is a SUMMARY — it cannot contain everything from the post.
It's OK if the infographic only covers the main points. What matters is:
1. Are the facts SHOWN in the infographic correct? (no wrong versions, no fabricated data)
2. Are technical terms (versions, APIs, class names) accurate?
3. Is anything shown WRONG or misleading? (this is the main failure criterion)
4. Minor omissions are acceptable — infographics summarize, they don't replicate the full post.

Return JSON:
{{
  "accuracy_score": 0.0-1.0,
  "facts_correct": ["list of verified correct facts"],
  "facts_wrong": ["list of ACTUALLY incorrect or fabricated facts"],
  "verdict": "pass" or "fail",
  "notes": "brief explanation"
}}

Only mark verdict "fail" if there are genuinely WRONG facts shown in the image.
Omissions or incomplete coverage are NOT failures.

Return ONLY JSON."""

    try:
        raw = coordinator.invoke(
            "content_validation",
            [HumanMessage(content=prompt)],
            temperature=0.2,
            max_tokens=1500,
        )
        result = _extract_json(raw)
        if not result:
            return False, 0.0, "Could not parse validation response"

        score = float(result.get("accuracy_score", 0))
        passed = result.get("verdict", "fail") == "pass" and score >= FACTUAL_THRESHOLD
        notes = result.get("notes", "")
        wrong = result.get("facts_wrong", [])
        if wrong:
            notes += f" | Wrong facts: {wrong}"

        return passed, score, notes

    except Exception as e:
        logger.error(f"[image_inspector] Factual verification failed: {e}")
        return False, 0.0, f"Verification error: {str(e)[:100]}"


def assess_design_quality(image_b64: str) -> tuple[bool, int, str]:
    """Use vision LLM to assess infographic design quality."""
    prompt = """You are a design quality inspector for LinkedIn infographic images.
Rate this infographic on the following criteria (0-25 each, total 0-100):

1. TEXT READABILITY (0-25): Can all text be read clearly? No overlapping, no cut-off, appropriate font sizes?
2. LAYOUT & SPACING (0-25): Well-organized elements? Consistent alignment? Good use of whitespace?
3. COLOR CONTRAST (0-25): Text legible against backgrounds? Sufficient contrast ratios?
4. VISUAL APPEAL (0-25): Professional appearance? Consistent design language? LinkedIn-worthy?

Return JSON:
{
  "text_readability": {"score": 0, "notes": "..."},
  "layout_spacing": {"score": 0, "notes": "..."},
  "color_contrast": {"score": 0, "notes": "..."},
  "visual_appeal": {"score": 0, "notes": "..."},
  "total_score": 0,
  "critical_issues": ["list any dealbreaker issues like unreadable text, broken layout"],
  "recommendation": "publish" or "reject"
}

Be strict but fair. This will be posted publicly on LinkedIn.
Return ONLY JSON."""

    try:
        raw = coordinator.invoke_vision("image_inspection", prompt, image_b64)
        result = _extract_json(raw)
        if not result:
            return False, 0, "Could not parse design assessment"

        score = int(result.get("total_score", 0))
        critical = result.get("critical_issues", [])
        rec = result.get("recommendation", "reject")

        # Critical issues only block if score is also low
        if critical and score < 50:
            return False, score, f"Critical issues: {critical}"

        passed = score >= DESIGN_QUALITY_THRESHOLD
        notes_parts = []
        for key in ["text_readability", "layout_spacing", "color_contrast", "visual_appeal"]:
            sub = result.get(key, {})
            notes_parts.append(f"{key}: {sub.get('score', '?')}/25")
        notes = " | ".join(notes_parts)

        return passed, score, notes

    except Exception as e:
        logger.error(f"[image_inspector] Design assessment failed: {e}")
        return False, 0, f"Assessment error: {str(e)[:100]}"


# ---------------------------------------------------------------------------
# Main inspection
# ---------------------------------------------------------------------------

def inspect_image(post_entry: dict) -> dict:
    """
    Full inspection of a single post's infographic.
    Returns inspection result dict.
    """
    image_path = post_entry.get("image_path", "")
    post_text = post_entry.get("text", "")
    topic = post_entry.get("topic", "")

    logger.info(f"[image_inspector] Inspecting: {topic}")
    logger.info(f"[image_inspector] Image: {image_path}")

    image_b64 = _load_image_b64(image_path)
    if not image_b64:
        return {
            "passed": False,
            "error": f"Image not found: {image_path}",
            "inspected_at": datetime.now().isoformat(),
        }

    # Pass 1: Extract text from image
    extracted = extract_infographic_text(image_b64)
    if not extracted:
        return {
            "passed": False,
            "error": "Vision LLM could not extract text from image",
            "inspected_at": datetime.now().isoformat(),
        }

    # Pass 2: Verify factual accuracy
    fact_passed, fact_score, fact_notes = verify_factual_accuracy(extracted, post_text)
    logger.info(f"[image_inspector] Factual: passed={fact_passed}, score={fact_score:.2f}")

    # Pass 3: Assess design quality
    design_passed, design_score, design_notes = assess_design_quality(image_b64)
    logger.info(f"[image_inspector] Design: passed={design_passed}, score={design_score}/100")

    overall_passed = fact_passed and design_passed

    return {
        "passed": overall_passed,
        "factual_accuracy": {
            "passed": fact_passed,
            "confidence": fact_score,
            "notes": fact_notes,
        },
        "design_quality": {
            "passed": design_passed,
            "score": design_score,
            "notes": design_notes,
        },
        "extracted_text": extracted,
        "inspected_at": datetime.now().isoformat(),
    }


def inspect_and_process_pending_posts() -> dict:
    """
    Main entry point. Inspects all pending_review posts:
    - Passes → publish to LinkedIn
    - Fails → delete image, mark rejected
    """
    log = _load_log()
    posts = log.get("posts", [])

    stats = {"inspected": 0, "approved": 0, "rejected": 0, "errors": 0, "skipped": 0}

    for i, post in enumerate(posts):
        if post.get("status") != "pending_review":
            continue

        image_path = post.get("image_path", "")
        if not image_path:
            logger.warning(f"[image_inspector] Post {i} has no image, skipping")
            stats["skipped"] += 1
            continue

        if not os.path.exists(image_path):
            logger.warning(f"[image_inspector] Image missing: {image_path}, skipping")
            stats["skipped"] += 1
            continue

        try:
            result = inspect_image(post)
            stats["inspected"] += 1

            post["inspection"] = result

            if result["passed"]:
                # Publish to LinkedIn — MUST include image
                logger.info(f"[image_inspector] APPROVED: {post.get('topic')}")
                try:
                    success = linkedin_post_tool.post_to_linkedin(
                        text=post.get("text", ""),
                        image_path=image_path,
                    )
                    if success:
                        post["status"] = "published"
                        post["published"] = True
                        post["published_at"] = datetime.now().isoformat()
                        stats["approved"] += 1
                        logger.success(f"[image_inspector] Published: {post.get('topic')}")
                    else:
                        post["status"] = "approved_not_published"
                        post["publish_error"] = "post_to_linkedin returned False"
                        stats["errors"] += 1
                        logger.warning(f"[image_inspector] Publish returned False: {post.get('topic')}")
                except Exception as e:
                    logger.error(f"[image_inspector] Publish failed: {e}")
                    post["status"] = "approved_not_published"
                    post["publish_error"] = str(e)[:200]
                    stats["errors"] += 1
            else:
                # Reject and delete image
                logger.warning(f"[image_inspector] REJECTED: {post.get('topic')}")
                reason = result.get("error", "")
                if not reason:
                    parts = []
                    fa = result.get("factual_accuracy", {})
                    dq = result.get("design_quality", {})
                    if not fa.get("passed", True):
                        parts.append(f"Factual: {fa.get('notes', 'failed')}")
                    if not dq.get("passed", True):
                        parts.append(f"Design ({dq.get('score', 0)}/100): {dq.get('notes', 'failed')}")
                    reason = " | ".join(parts)

                post["status"] = "rejected"
                post["rejection_reason"] = reason
                post["rejected_at"] = datetime.now().isoformat()

                # Delete the image file
                try:
                    os.remove(image_path)
                    logger.info(f"[image_inspector] Deleted: {image_path}")
                except OSError as e:
                    logger.warning(f"[image_inspector] Could not delete {image_path}: {e}")

                stats["rejected"] += 1

        except Exception as e:
            logger.error(f"[image_inspector] Error inspecting post {i}: {e}")
            stats["errors"] += 1

    _save_log(log)
    logger.info(f"[image_inspector] Done: {stats}")
    return stats
