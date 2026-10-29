from dataclasses import dataclass
from typing import Literal, get_args

from portfolio.schema import FontPairing, SectionName, Theme

TemplateId = Literal["classic", "modern", "minimal", "dark"]
TEMPLATE_IDS = get_args(TemplateId)
MIN_CONTRAST = 4.5  # WCAG AA for normal text

GOOGLE_FONTS = "https://fonts.googleapis.com/css2?display=swap&family="


@dataclass(frozen=True)
class Font:
    url: str
    heading: str
    body: str


FONTS: dict[FontPairing, Font] = {
    "serif": Font(
        GOOGLE_FONTS + "Inter:wght@400;600&family=Source+Serif+4:ital,opsz,wght@0,8..60,600;1,8..60,400",
        '"Source Serif 4", Georgia, serif',
        "Inter, system-ui, sans-serif",
    ),
    "sans": Font(
        GOOGLE_FONTS + "Inter:wght@400;600;700",
        "Inter, system-ui, sans-serif",
        "Inter, system-ui, sans-serif",
    ),
    "mono": Font(
        GOOGLE_FONTS + "JetBrains+Mono:wght@400;600",
        '"JetBrains Mono", ui-monospace, Consolas, monospace',
        '"JetBrains Mono", ui-monospace, Consolas, monospace',
    ),
    "display": Font(
        GOOGLE_FONTS + "Inter:wght@400;600&family=Playfair+Display:ital,wght@0,600;1,400",
        '"Playfair Display", Georgia, serif',
        "Inter, system-ui, sans-serif",
    ),
}


@dataclass(frozen=True)
class TemplateDefaults:
    accent: str
    accent_on: tuple[str, ...]  # backgrounds the accent color must stay readable on
    font: FontPairing
    sections: tuple[SectionName, ...]


ALL_SECTIONS: tuple[SectionName, ...] = get_args(SectionName)

TEMPLATES: dict[TemplateId, TemplateDefaults] = {
    "classic": TemplateDefaults("#8b2e2e", ("#fdfcfa",), "serif", ALL_SECTIONS),
    "modern": TemplateDefaults("#1e3a8a", ("#ffffff", "#f1f5f9"), "sans", ALL_SECTIONS),
    "minimal": TemplateDefaults("#555555", ("#fafafa",), "mono", ALL_SECTIONS),
    "dark": TemplateDefaults("#fbbf24", ("#0b0f17", "#151b28"), "sans", ALL_SECTIONS),
}


class ThemeError(ValueError):
    pass


@dataclass(frozen=True)
class ResolvedTheme:
    accent: str
    font: Font
    sections: list[SectionName]


def contrast_ratio(a: str, b: str) -> float:
    def luminance(hex_color: str) -> float:
        channels = [int(hex_color[i : i + 2], 16) / 255 for i in (1, 3, 5)]
        r, g, b = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
        return 0.2126 * r + 0.7152 * g + 0.0722 * b

    light, dark = sorted([luminance(a), luminance(b)], reverse=True)
    return (light + 0.05) / (dark + 0.05)


def resolve_theme(template_id: TemplateId, theme: Theme | None) -> ResolvedTheme:
    """Fill in the template's defaults for anything the user didn't pick, and reject
    accent colors that would make text unreadable on that template."""
    defaults = TEMPLATES[template_id]
    theme = theme or Theme()

    accent = (theme.accent or defaults.accent).lower()
    for background in defaults.accent_on:
        if contrast_ratio(accent, background) < MIN_CONTRAST:
            raise ThemeError(f"Accent {accent} is too hard to read on the {template_id} template")

    order = list(theme.section_order or [])
    order += [s for s in defaults.sections if s not in order]

    return ResolvedTheme(accent, FONTS[theme.font or defaults.font], order)


def theme_css(theme: ResolvedTheme) -> str:
    """CSS variables every template's style.css reads. Values only come from
    validated hex colors and the fixed FONTS table, so this is safe to inline."""
    return (
        f":root {{ --accent: {theme.accent}; "
        f"--font-heading: {theme.font.heading}; --font-body: {theme.font.body}; }}"
    )
