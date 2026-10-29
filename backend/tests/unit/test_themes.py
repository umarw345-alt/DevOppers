import pytest

from portfolio.schema import Theme
from portfolio.themes import (
    ALL_SECTIONS,
    FONTS,
    MIN_CONTRAST,
    TEMPLATE_IDS,
    TEMPLATES,
    ThemeError,
    contrast_ratio,
    resolve_theme,
    theme_css,
)


@pytest.mark.parametrize(
    "a, b, expected",
    [
        ("#000000", "#ffffff", 21.0),
        ("#ffffff", "#000000", 21.0),
        ("#777777", "#777777", 1.0),
        ("#767676", "#ffffff", 4.54),
    ],
)
def test_contrast_ratio(a, b, expected):
    assert contrast_ratio(a, b) == pytest.approx(expected, abs=0.01)


def test_every_template_has_defaults():
    assert set(TEMPLATES) == set(TEMPLATE_IDS)


@pytest.mark.parametrize("template_id", TEMPLATE_IDS)
def test_template_defaults_are_readable(template_id):
    defaults = TEMPLATES[template_id]
    for background in defaults.accent_on:
        assert contrast_ratio(defaults.accent, background) >= MIN_CONTRAST


def test_no_theme_uses_template_defaults():
    resolved = resolve_theme("classic", None)
    assert resolved.accent == TEMPLATES["classic"].accent
    assert resolved.font == FONTS["serif"]
    assert resolved.sections == list(ALL_SECTIONS)


def test_custom_accent_and_font_are_used():
    resolved = resolve_theme("classic", Theme(accent="#1D4ED8", font="display"))
    assert resolved.accent == "#1d4ed8"
    assert resolved.font == FONTS["display"]


@pytest.mark.parametrize(
    "template_id, accent",
    [("classic", "#ffff00"), ("modern", "#bfdbfe"), ("minimal", "#cccccc"), ("dark", "#1e3a8a")],
)
def test_unreadable_accent_is_rejected(template_id, accent):
    with pytest.raises(ThemeError):
        resolve_theme(template_id, Theme(accent=accent))


def test_partial_section_order_keeps_the_rest_in_default_order():
    resolved = resolve_theme("classic", Theme(section_order=["skills", "education"]))
    assert resolved.sections == ["skills", "education", "summary", "experience", "projects"]


def test_theme_css_contains_the_variables():
    css = theme_css(resolve_theme("classic", Theme(accent="#1d4ed8", font="mono")))
    assert "--accent: #1d4ed8;" in css
    assert f"--font-heading: {FONTS['mono'].heading};" in css
    assert f"--font-body: {FONTS['mono'].body};" in css
