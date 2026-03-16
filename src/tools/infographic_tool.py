"""
Infographic Tool — genera imágenes profesionales para LinkedIn posts.

Usa matplotlib + Pillow para crear infografías con:
- Dark gradient backgrounds con textura
- Glassmorphism cards
- Syntax-highlighted code blocks
- Comparison tables con columnas coloreadas
- Flow/architecture diagrams
- Branded header con info profesional

NO usa IA generativa — todo el contenido es texto real verificado.
"""
import os
import re
import time
import textwrap
from typing import Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import matplotlib.patheffects as patheffects
from matplotlib.colors import LinearSegmentedColormap
import numpy as np
from loguru import logger

# ---------------------------------------------------------------------------
# Color palette — modern gradient dark theme
# ---------------------------------------------------------------------------
GRADIENT_COLORS = ["#0f0c29", "#302b63", "#24243e"]
ACCENT_BLUE = "#00d2ff"
ACCENT_PURPLE = "#7c3aed"
ACCENT_GREEN = "#50fa7b"
ACCENT_PINK = "#ff79c6"
ACCENT_YELLOW = "#f1fa8c"
ACCENT_CYAN = "#8be9fd"
ACCENT_ORANGE = "#ffb86c"
ACCENT_RED = "#ff5555"

COLORS = {
    "bg_top": "#0f0c29",
    "bg_mid": "#302b63",
    "bg_bot": "#24243e",
    "card": "#ffffff10",
    "card_border": "#ffffff20",
    "glass_highlight": "#ffffff08",
    "accent": ACCENT_BLUE,
    "accent2": ACCENT_GREEN,
    "accent3": ACCENT_PURPLE,
    "text": "#e2e8f0",
    "text_dim": "#94a3b8",
    "text_bright": "#ffffff",
    "code_bg": "#0d1117",
    "code_border": "#30363d",
    "line_num_bg": "#0a0e14",
    "header_bg": "#ffffff0a",
    "left_col": "#ff6b35",
    "right_col": "#00c9a7",
    "vs_bg": "#7c3aed",
    "number_badge": "#7c3aed",
}

# Syntax highlighting colors (Dracula-inspired)
SYNTAX = {
    "keyword": "#ff79c6",
    "string": "#f1fa8c",
    "comment": "#6272a4",
    "method": "#50fa7b",
    "type": "#8be9fd",
    "number": "#bd93f9",
    "operator": "#ff79c6",
    "default": "#f8f8f2",
}

BRAND_TEXT = "Alejandro Hernandez Loza  |  Sr. Software Engineer  |  Java · Spring Boot · Cloud"

# Java keywords for syntax highlighting
JAVA_KEYWORDS = {
    "try", "catch", "finally", "var", "new", "return", "if", "else", "for",
    "while", "do", "switch", "case", "break", "continue", "throw", "throws",
    "import", "package", "class", "interface", "extends", "implements", "static",
    "final", "void", "public", "private", "protected", "abstract", "synchronized",
    "volatile", "transient", "native", "int", "long", "double", "float", "boolean",
    "char", "byte", "short", "String", "true", "false", "null", "this", "super",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _draw_gradient_background(fig, ax):
    """Draw a vertical gradient background from top to bottom."""
    gradient = np.linspace(0, 1, 256).reshape(-1, 1)
    gradient = np.hstack([gradient, gradient])

    cmap = LinearSegmentedColormap.from_list(
        "bg_grad",
        [(0, "#0f0c29"), (0.5, "#302b63"), (1, "#24243e")],
    )
    ax.imshow(
        gradient, aspect="auto", cmap=cmap,
        extent=[ax.get_xlim()[0], ax.get_xlim()[1], ax.get_ylim()[0], ax.get_ylim()[1]],
        zorder=0,
    )


def _draw_dot_texture(ax, xlim, ylim, spacing=0.8, alpha=0.03):
    """Draw subtle dot grid pattern for texture."""
    x_dots = np.arange(xlim[0] + 0.4, xlim[1], spacing)
    y_dots = np.arange(ylim[0] + 0.4, ylim[1], spacing)
    for x in x_dots:
        for y in y_dots:
            ax.plot(x, y, "o", color="white", markersize=0.5, alpha=alpha, zorder=1)


def _draw_branded_header(ax, y_top, x_left, x_right):
    """Draw the branded header bar at the top."""
    header_height = 0.55
    header = FancyBboxPatch(
        (x_left, y_top - header_height), x_right - x_left, header_height,
        boxstyle="round,pad=0.05",
        facecolor=COLORS["header_bg"],
        edgecolor=COLORS["card_border"],
        linewidth=0.5, zorder=5,
    )
    ax.add_patch(header)

    # LinkedIn icon placeholder (small circle)
    icon_x = x_left + 0.4
    icon_y = y_top - header_height / 2
    circle = plt.Circle((icon_x, icon_y), 0.15, color=ACCENT_BLUE, alpha=0.8, zorder=6)
    ax.add_patch(circle)
    ax.text(icon_x, icon_y, "in", fontsize=7, fontweight="bold",
            color="white", ha="center", va="center", zorder=7)

    # Brand text
    ax.text(
        icon_x + 0.45, icon_y, BRAND_TEXT,
        fontsize=7.5, color=COLORS["text_dim"],
        fontfamily="DejaVu Sans", ha="left", va="center", zorder=6,
    )

    return y_top - header_height - 0.3


def _draw_title_with_glow(ax, x, y, text, fontsize=26):
    """Draw title text with subtle glow effect."""
    # Glow layer (blurred via thick stroke)
    glow = ax.text(
        x, y, text, fontsize=fontsize, fontweight="bold",
        fontfamily="DejaVu Sans", color=ACCENT_BLUE,
        ha="left", va="top", zorder=9,
    )
    glow.set_path_effects([
        patheffects.withStroke(linewidth=8, foreground=ACCENT_BLUE + "30"),
    ])

    # Sharp white text on top
    sharp = ax.text(
        x, y, text, fontsize=fontsize, fontweight="bold",
        fontfamily="DejaVu Sans", color=COLORS["text_bright"],
        ha="left", va="top", zorder=10,
    )
    return sharp


def _draw_subtitle(ax, x, y, text, fontsize=14):
    """Draw subtitle in accent color."""
    ax.text(
        x, y, text, fontsize=fontsize,
        fontfamily="DejaVu Sans", color=ACCENT_PURPLE,
        ha="left", va="top", zorder=10,
    )


def _draw_gradient_bar(ax, x1, x2, y, height=0.06):
    """Draw a horizontal gradient bar (accent underline)."""
    gradient = np.linspace(0, 1, 256).reshape(1, -1)
    cmap = LinearSegmentedColormap.from_list("bar", [ACCENT_BLUE, ACCENT_PURPLE])
    ax.imshow(
        gradient, aspect="auto", cmap=cmap,
        extent=[x1, x2, y - height, y],
        zorder=8, alpha=0.8,
    )


def _draw_glass_card(ax, x, y, w, h, border_color=None, border_side="left"):
    """Draw a glassmorphism card with optional colored left border."""
    card = FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.08",
        facecolor="#ffffff0a",
        edgecolor="#ffffff18",
        linewidth=0.8, zorder=4,
    )
    ax.add_patch(card)

    # Accent border (left side by default)
    if border_color and border_side == "left":
        border = FancyBboxPatch(
            (x, y), 0.06, h,
            boxstyle="round,pad=0.01",
            facecolor=border_color,
            edgecolor="none",
            linewidth=0, zorder=5,
        )
        ax.add_patch(border)


def _draw_number_badge(ax, x, y, number, color=None):
    """Draw a numbered circle badge."""
    c = color or COLORS["number_badge"]
    circle = plt.Circle((x, y), 0.22, color=c, alpha=0.9, zorder=6)
    ax.add_patch(circle)
    ax.text(x, y, str(number), fontsize=11, fontweight="bold",
            color="white", ha="center", va="center", zorder=7)


def _draw_footer(ax, y, x_center, xlim):
    """Draw footer separator and text."""
    ax.plot(
        [xlim[0] + 0.5, xlim[1] - 0.5], [y + 0.2, y + 0.2],
        color="#ffffff15", linewidth=0.5, zorder=5,
    )
    ax.text(
        x_center, y, BRAND_TEXT,
        fontsize=8, color=COLORS["text_dim"],
        fontfamily="DejaVu Sans", ha="center", va="top", zorder=5,
    )


def _get_badge_colors():
    """Return rotating list of badge colors."""
    return [ACCENT_BLUE, ACCENT_PURPLE, ACCENT_GREEN, ACCENT_PINK, ACCENT_ORANGE, ACCENT_CYAN]


# ---------------------------------------------------------------------------
# Syntax highlighting helper
# ---------------------------------------------------------------------------

def _syntax_highlight_line(ax, x, y, line, fontsize=10.5):
    """Render a line of Java-ish code with syntax colors."""
    tokens = _tokenize_code(line)
    cur_x = x
    for text, color in tokens:
        t = ax.text(
            cur_x, y, text, fontsize=fontsize,
            fontfamily="DejaVu Sans Mono", color=color,
            ha="left", va="center", zorder=10,
        )
        # Estimate character width for positioning
        cur_x += len(text) * 0.115


def _tokenize_code(line):
    """Simple tokenizer for Java-like syntax highlighting."""
    tokens = []
    i = 0
    s = line

    while i < len(s):
        # Leading whitespace
        if s[i] == " ":
            j = i
            while j < len(s) and s[j] == " ":
                j += 1
            tokens.append((s[i:j], SYNTAX["default"]))
            i = j
            continue

        # Line comment
        if s[i:i+2] == "//":
            tokens.append((s[i:], SYNTAX["comment"]))
            break

        # String literal
        if s[i] == '"':
            j = i + 1
            while j < len(s) and s[j] != '"':
                if s[j] == '\\':
                    j += 1
                j += 1
            j = min(j + 1, len(s))
            tokens.append((s[i:j], SYNTAX["string"]))
            i = j
            continue

        # Number
        if s[i].isdigit() or (s[i] == '.' and i + 1 < len(s) and s[i+1].isdigit()):
            j = i
            while j < len(s) and (s[j].isdigit() or s[j] in "._xXabcdefABCDEFL"):
                j += 1
            tokens.append((s[i:j], SYNTAX["number"]))
            i = j
            continue

        # Word (keyword, method, type, identifier)
        if s[i].isalpha() or s[i] == '_':
            j = i
            while j < len(s) and (s[j].isalnum() or s[j] == '_'):
                j += 1
            word = s[i:j]

            if word in JAVA_KEYWORDS:
                tokens.append((word, SYNTAX["keyword"]))
            elif j < len(s) and s[j] == "(":
                tokens.append((word, SYNTAX["method"]))
            elif word[0].isupper():
                tokens.append((word, SYNTAX["type"]))
            else:
                tokens.append((word, SYNTAX["default"]))
            i = j
            continue

        # Operators and punctuation
        if s[i] in "-><=!&|+*/%^~?:":
            j = i
            while j < len(s) and s[j] in "-><=!&|+*/%^~?:":
                j += 1
            tokens.append((s[i:j], SYNTAX["operator"]))
            i = j
            continue

        # Anything else (parens, braces, dots, commas, semicolons)
        tokens.append((s[i], SYNTAX["default"]))
        i += 1

    return tokens


# ---------------------------------------------------------------------------
# Main generators
# ---------------------------------------------------------------------------

def generate_tips_infographic(
    title: str,
    subtitle: str,
    tips: list[dict],
    footer: str = None,
    output_dir: str = "data/linkedin_images",
) -> str:
    """
    Generate a tips/bullet-points infographic with glassmorphism cards.

    Args:
        title: Main title
        subtitle: Subtitle text
        tips: List of {icon, title, description}
        footer: Optional footer override
        output_dir: Output directory

    Returns:
        Path to the generated PNG file
    """
    n_tips = len(tips)
    card_height = 1.15
    fig_height = max(12, 3.5 + n_tips * (card_height + 0.25) + 1.5)
    fig_width = 10

    fig, ax = plt.subplots(1, 1, figsize=(fig_width, fig_height), dpi=150)
    ax.set_xlim(0, 12)
    ax.set_ylim(0, fig_height)
    ax.axis("off")

    # Background
    _draw_gradient_background(fig, ax)
    _draw_dot_texture(ax, (0, 12), (0, fig_height))

    y = fig_height - 0.3

    # Branded header
    y = _draw_branded_header(ax, y, 0.5, 11.5)

    # Title with glow
    _draw_title_with_glow(ax, 0.7, y, title, fontsize=24)
    y -= 0.75

    # Subtitle
    _draw_subtitle(ax, 0.7, y, subtitle, fontsize=13)
    y -= 0.45

    # Gradient underline bar
    _draw_gradient_bar(ax, 0.7, 6.0, y, height=0.06)
    y -= 0.6

    # Tips cards
    badge_colors = _get_badge_colors()
    for i, tip in enumerate(tips):
        tip_title = tip.get("title", "")
        desc = tip.get("description", "")
        badge_color = badge_colors[i % len(badge_colors)]

        # Wrap description to estimate card height
        wrapped = textwrap.fill(desc, width=72)
        desc_lines = wrapped.split("\n")
        this_card_h = max(card_height, 0.55 + len(desc_lines) * 0.28)

        # Glass card with accent left border
        _draw_glass_card(ax, 0.7, y - this_card_h, 10.6, this_card_h, border_color=badge_color)

        # Number badge
        _draw_number_badge(ax, 1.25, y - 0.35, i + 1, color=badge_color)

        # Tip title (bold)
        ax.text(
            1.7, y - 0.22, tip_title,
            fontsize=12.5, fontweight="bold", color=COLORS["text_bright"],
            fontfamily="DejaVu Sans", ha="left", va="top", zorder=10,
        )

        # Description
        desc_y = y - 0.55
        for dl in desc_lines:
            ax.text(
                1.7, desc_y, dl,
                fontsize=10.5, color=COLORS["text_dim"],
                fontfamily="DejaVu Sans", ha="left", va="top", zorder=10,
            )
            desc_y -= 0.28

        y -= this_card_h + 0.2

    # Footer
    _draw_footer(ax, 0.4, 6.0, (0, 12))

    os.makedirs(output_dir, exist_ok=True)
    timestamp = int(time.time())
    path = os.path.join(output_dir, f"infographic_{timestamp}.png")
    fig.savefig(path, bbox_inches="tight", facecolor=COLORS["bg_top"], edgecolor="none", pad_inches=0.2)
    plt.close(fig)

    logger.info(f"[infographic] Tips infographic saved: {path}")
    return path


def generate_code_infographic(
    title: str,
    subtitle: str,
    code: str,
    language: str = "Java",
    explanation_points: list[str] = None,
    footer: str = None,
    output_dir: str = "data/linkedin_images",
) -> str:
    """
    Generate a code snippet infographic with syntax highlighting.

    Args:
        title: Main title
        subtitle: Subtitle
        code: Source code string
        language: Language label for badge
        explanation_points: List of explanation strings
        footer: Optional footer override
        output_dir: Output directory

    Returns:
        Path to the generated PNG file
    """
    code_lines = code.strip().split("\n")
    n_code = len(code_lines)
    n_explain = len(explanation_points or [])
    fig_height = max(12, 4.0 + n_code * 0.40 + n_explain * 0.65 + 2.0)
    fig_width = 11

    fig, ax = plt.subplots(1, 1, figsize=(fig_width, fig_height), dpi=150)
    ax.set_xlim(0, 13)
    ax.set_ylim(0, fig_height)
    ax.axis("off")

    _draw_gradient_background(fig, ax)
    _draw_dot_texture(ax, (0, 13), (0, fig_height))

    y = fig_height - 0.3

    # Header
    y = _draw_branded_header(ax, y, 0.5, 12.5)

    # Title
    _draw_title_with_glow(ax, 0.7, y, title, fontsize=24)
    y -= 0.75

    # Subtitle
    _draw_subtitle(ax, 0.7, y, subtitle, fontsize=13)
    y -= 0.45

    _draw_gradient_bar(ax, 0.7, 6.0, y, height=0.06)
    y -= 0.6

    # Code block
    code_block_h = n_code * 0.40 + 0.6
    line_num_width = 0.9

    # Code background (dark)
    code_bg = FancyBboxPatch(
        (0.7, y - code_block_h), 11.6, code_block_h,
        boxstyle="round,pad=0.12",
        facecolor=COLORS["code_bg"],
        edgecolor=COLORS["code_border"],
        linewidth=1.2, zorder=4,
    )
    ax.add_patch(code_bg)

    # Line number column (darker)
    ln_bg = FancyBboxPatch(
        (0.7, y - code_block_h), line_num_width + 0.2, code_block_h,
        boxstyle="round,pad=0.12",
        facecolor=COLORS["line_num_bg"],
        edgecolor="none",
        linewidth=0, zorder=4,
    )
    ax.add_patch(ln_bg)

    # Separator between line nums and code
    ax.plot(
        [0.7 + line_num_width + 0.2, 0.7 + line_num_width + 0.2],
        [y - code_block_h + 0.1, y - 0.1],
        color=COLORS["code_border"], linewidth=0.5, zorder=5,
    )

    # Language badge (top-right pill)
    badge_w = len(language) * 0.12 + 0.5
    badge_x = 12.3 - badge_w
    badge = FancyBboxPatch(
        (badge_x, y - 0.38), badge_w, 0.32,
        boxstyle="round,pad=0.08",
        facecolor=ACCENT_PURPLE + "cc",
        edgecolor="none",
        linewidth=0, zorder=6,
    )
    ax.add_patch(badge)
    ax.text(
        badge_x + badge_w / 2, y - 0.22, language,
        fontsize=8.5, fontweight="bold", color="white",
        fontfamily="DejaVu Sans", ha="center", va="center", zorder=7,
    )

    # Code lines with syntax highlighting
    code_y = y - 0.45
    for i, line in enumerate(code_lines):
        # Line number
        ax.text(
            1.4, code_y, f"{i + 1}", fontsize=9,
            fontfamily="DejaVu Sans Mono", color=COLORS["text_dim"],
            ha="right", va="center", zorder=6, alpha=0.6,
        )
        # Syntax-highlighted code
        _syntax_highlight_line(ax, 1.9, code_y, line, fontsize=10.5)
        code_y -= 0.40

    y -= code_block_h + 0.5

    # Explanation section
    if explanation_points:
        ax.text(
            0.7, y, "¿Qué hace este código?",
            fontsize=14, fontweight="bold", color=ACCENT_GREEN,
            fontfamily="DejaVu Sans", ha="left", va="top", zorder=10,
        )
        y -= 0.55

        for j, point in enumerate(explanation_points):
            wrapped = textwrap.fill(point, width=75)
            lines = wrapped.split("\n")
            card_h = max(0.5, len(lines) * 0.28 + 0.15)

            # Glass card for each explanation point
            _draw_glass_card(ax, 0.7, y - card_h, 11.6, card_h, border_color=ACCENT_GREEN)

            # Green arrow icon
            ax.text(
                1.1, y - 0.18, "▶",
                fontsize=9, color=ACCENT_GREEN,
                ha="center", va="top", zorder=10,
            )

            # Point text
            pt_y = y - 0.18
            for ln in lines:
                ax.text(
                    1.5, pt_y, ln,
                    fontsize=10.5, color=COLORS["text"],
                    fontfamily="DejaVu Sans", ha="left", va="top", zorder=10,
                )
                pt_y -= 0.28

            y -= card_h + 0.15

    # Footer
    _draw_footer(ax, 0.4, 6.5, (0, 13))

    os.makedirs(output_dir, exist_ok=True)
    timestamp = int(time.time())
    path = os.path.join(output_dir, f"code_infographic_{timestamp}.png")
    fig.savefig(path, bbox_inches="tight", facecolor=COLORS["bg_top"], edgecolor="none", pad_inches=0.2)
    plt.close(fig)

    logger.info(f"[infographic] Code infographic saved: {path}")
    return path


def generate_comparison_infographic(
    title: str,
    subtitle: str,
    left_label: str,
    right_label: str,
    comparisons: list[dict],
    footer: str = None,
    output_dir: str = "data/linkedin_images",
) -> str:
    """
    Generate a side-by-side comparison infographic.

    Args:
        title: Main title
        subtitle: Subtitle
        left_label: Left column name
        right_label: Right column name
        comparisons: List of {aspect, left, right}
        footer: Optional footer override
        output_dir: Output directory

    Returns:
        Path to the generated PNG file
    """
    n_rows = len(comparisons)
    row_height = 1.35
    fig_height = max(12, 4.0 + n_rows * row_height + 2.0)
    fig_width = 12

    fig, ax = plt.subplots(1, 1, figsize=(fig_width, fig_height), dpi=150)
    ax.set_xlim(0, 14)
    ax.set_ylim(0, fig_height)
    ax.axis("off")

    _draw_gradient_background(fig, ax)
    _draw_dot_texture(ax, (0, 14), (0, fig_height))

    y = fig_height - 0.3

    # Header
    y = _draw_branded_header(ax, y, 0.5, 13.5)

    # Title (centered)
    _draw_title_with_glow(ax, 7.0 - len(title) * 0.13, y, title, fontsize=24)
    y -= 0.75

    # Subtitle (centered)
    ax.text(
        7.0, y, subtitle, fontsize=13,
        fontfamily="DejaVu Sans", color=ACCENT_PURPLE,
        ha="center", va="top", zorder=10,
    )
    y -= 0.45

    _draw_gradient_bar(ax, 2.0, 12.0, y, height=0.06)
    y -= 0.7

    # Column headers
    # Left header (red/orange gradient pill)
    left_pill = FancyBboxPatch(
        (1.0, y - 0.45), 5.0, 0.45,
        boxstyle="round,pad=0.1",
        facecolor="#ff6b3530",
        edgecolor="#ff6b35aa",
        linewidth=1.5, zorder=5,
    )
    ax.add_patch(left_pill)
    ax.text(
        3.5, y - 0.22, left_label,
        fontsize=13, fontweight="bold", color="#ff6b35",
        fontfamily="DejaVu Sans", ha="center", va="center", zorder=6,
    )

    # VS badge (center)
    vs_circle = plt.Circle((7.0, y - 0.22), 0.3, color=COLORS["vs_bg"], alpha=0.9, zorder=7)
    ax.add_patch(vs_circle)
    ax.text(
        7.0, y - 0.22, "VS",
        fontsize=10, fontweight="bold", color="white",
        ha="center", va="center", zorder=8,
    )

    # Right header (green/teal gradient pill)
    right_pill = FancyBboxPatch(
        (8.0, y - 0.45), 5.0, 0.45,
        boxstyle="round,pad=0.1",
        facecolor="#00c9a730",
        edgecolor="#00c9a7aa",
        linewidth=1.5, zorder=5,
    )
    ax.add_patch(right_pill)
    ax.text(
        10.5, y - 0.22, right_label,
        fontsize=13, fontweight="bold", color="#00c9a7",
        fontfamily="DejaVu Sans", ha="center", va="center", zorder=6,
    )

    y -= 0.75

    # Comparison rows
    for idx, comp in enumerate(comparisons):
        aspect = comp.get("aspect", "")
        left = comp.get("left", "")
        right = comp.get("right", "")

        # Aspect label (centered)
        ax.text(
            7.0, y, aspect,
            fontsize=11, fontweight="bold", color=COLORS["text_bright"],
            fontfamily="DejaVu Sans", ha="center", va="top", zorder=10,
        )
        y -= 0.35

        card_h = 0.55

        # Left card (orange tinted)
        left_card = FancyBboxPatch(
            (1.0, y - card_h), 5.0, card_h,
            boxstyle="round,pad=0.08",
            facecolor="#ff6b3510",
            edgecolor="#ff6b3540",
            linewidth=1, zorder=5,
        )
        ax.add_patch(left_card)
        left_wrapped = textwrap.fill(left, width=32)
        ax.text(
            3.5, y - card_h / 2, left_wrapped,
            fontsize=10.5, fontweight="bold", color="#ffb4a0",
            fontfamily="DejaVu Sans", ha="center", va="center", zorder=6,
        )

        # Right card (green tinted)
        right_card = FancyBboxPatch(
            (8.0, y - card_h), 5.0, card_h,
            boxstyle="round,pad=0.08",
            facecolor="#00c9a710",
            edgecolor="#00c9a740",
            linewidth=1, zorder=5,
        )
        ax.add_patch(right_card)
        right_wrapped = textwrap.fill(right, width=32)
        ax.text(
            10.5, y - card_h / 2, right_wrapped,
            fontsize=10.5, fontweight="bold", color="#7dffe0",
            fontfamily="DejaVu Sans", ha="center", va="center", zorder=6,
        )

        # Separator line between rows
        y -= card_h + 0.15
        if idx < len(comparisons) - 1:
            ax.plot(
                [2.0, 12.0], [y, y],
                color="#ffffff10", linewidth=0.5, zorder=3,
            )
            y -= 0.15

    # Footer
    _draw_footer(ax, 0.4, 7.0, (0, 14))

    os.makedirs(output_dir, exist_ok=True)
    timestamp = int(time.time())
    path = os.path.join(output_dir, f"comparison_{timestamp}.png")
    fig.savefig(path, bbox_inches="tight", facecolor=COLORS["bg_top"], edgecolor="none", pad_inches=0.2)
    plt.close(fig)

    logger.info(f"[infographic] Comparison infographic saved: {path}")
    return path


def generate_flow_infographic(
    title: str,
    subtitle: str,
    steps: list[dict],
    footer: str = None,
    output_dir: str = "data/linkedin_images",
) -> str:
    """
    Generate a process/architecture flow diagram.

    Args:
        title: Main title
        subtitle: Subtitle
        steps: List of {icon, title, description, arrow_label (optional)}
               arrow_label is the text on the arrow TO the next step.
        footer: Optional footer override
        output_dir: Output directory

    Returns:
        Path to the generated PNG file
    """
    n_steps = len(steps)
    fig_width = 12
    fig_height = max(12, 4.0 + n_steps * 1.8 + 1.5)

    fig, ax = plt.subplots(1, 1, figsize=(fig_width, fig_height), dpi=150)
    ax.set_xlim(0, 14)
    ax.set_ylim(0, fig_height)
    ax.axis("off")

    _draw_gradient_background(fig, ax)
    _draw_dot_texture(ax, (0, 14), (0, fig_height))

    y = fig_height - 0.3

    # Header
    y = _draw_branded_header(ax, y, 0.5, 13.5)

    # Title
    _draw_title_with_glow(ax, 0.7, y, title, fontsize=24)
    y -= 0.75

    _draw_subtitle(ax, 0.7, y, subtitle, fontsize=13)
    y -= 0.45

    _draw_gradient_bar(ax, 0.7, 6.0, y, height=0.06)
    y -= 0.8

    badge_colors = _get_badge_colors()
    box_width = 10.0
    box_height = 1.1

    for i, step in enumerate(steps):
        icon = step.get("icon", "")
        step_title = step.get("title", "")
        desc = step.get("description", "")
        arrow_label = step.get("arrow_label", "")
        color = badge_colors[i % len(badge_colors)]

        # Step box (glass card)
        box_x = 2.0
        box_y = y - box_height

        _draw_glass_card(ax, box_x, box_y, box_width, box_height, border_color=color)

        # Icon
        icon_circle = plt.Circle(
            (box_x + 0.6, box_y + box_height / 2), 0.3,
            color=color, alpha=0.2, zorder=6,
        )
        ax.add_patch(icon_circle)
        ax.text(
            box_x + 0.6, box_y + box_height / 2, icon,
            fontsize=16, ha="center", va="center", zorder=7,
        )

        # Step title
        ax.text(
            box_x + 1.3, box_y + box_height - 0.25, step_title,
            fontsize=13, fontweight="bold", color=COLORS["text_bright"],
            fontfamily="DejaVu Sans", ha="left", va="top", zorder=10,
        )

        # Step description
        wrapped = textwrap.fill(desc, width=65)
        desc_lines = wrapped.split("\n")
        dy = box_y + box_height - 0.58
        for dl in desc_lines:
            ax.text(
                box_x + 1.3, dy, dl,
                fontsize=10, color=COLORS["text_dim"],
                fontfamily="DejaVu Sans", ha="left", va="top", zorder=10,
            )
            dy -= 0.25

        y -= box_height

        # Arrow to next step
        if i < n_steps - 1:
            arrow_center_x = 7.0
            arrow_top = y
            arrow_bot = y - 0.55

            # Arrow line
            ax.annotate(
                "", xy=(arrow_center_x, arrow_bot), xytext=(arrow_center_x, arrow_top),
                arrowprops=dict(
                    arrowstyle="->",
                    color=COLORS["text_dim"],
                    lw=1.5,
                    connectionstyle="arc3,rad=0",
                ),
                zorder=5,
            )

            # Arrow label
            if arrow_label:
                ax.text(
                    arrow_center_x + 0.3, (arrow_top + arrow_bot) / 2, arrow_label,
                    fontsize=8.5, color=ACCENT_CYAN, fontstyle="italic",
                    fontfamily="DejaVu Sans", ha="left", va="center", zorder=6,
                )

            y -= 0.65

    # Footer
    _draw_footer(ax, 0.4, 7.0, (0, 14))

    os.makedirs(output_dir, exist_ok=True)
    timestamp = int(time.time())
    path = os.path.join(output_dir, f"flow_{timestamp}.png")
    fig.savefig(path, bbox_inches="tight", facecolor=COLORS["bg_top"], edgecolor="none", pad_inches=0.2)
    plt.close(fig)

    logger.info(f"[infographic] Flow infographic saved: {path}")
    return path
