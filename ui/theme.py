# ui/theme.py
import os
import re
from collections import OrderedDict
from dataclasses import dataclass
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint, pyqtProperty, QThread, QObject, pyqtSignal
from PyQt6.QtGui import QPixmap, QPalette, QBrush, QPainter, QColor
from PyQt6.QtWidgets import QPushButton, QApplication, QMenu, QWidget
from config import reg, HKCU, THEME_FOLDER
from log import log
from typing import Optional, Tuple
import time

try:
    from qfluentwidgets import InfoBar as _InfoBar
except ImportError:
    _InfoBar = None


_THEME_SWITCH_METRICS_ACTIVE: dict[str, object] | None = None
_THEME_SWITCH_METRICS_NEXT_ID = 0
_THEME_TOKENS_CACHE: dict[tuple, "ThemeTokens"] = {}

_DEFAULT_CARD_GRADIENT_STOPS = ("#292B37", "#252A3E")
_DEFAULT_CARD_GRADIENT_STOPS_HOVER = ("#2D3040", "#2A2F45")
_DEFAULT_CARD_DISABLED_GRADIENT_STOPS = ("#1E2232", "#171B29")
_DEFAULT_DNS_SELECTED_GRADIENT_STOPS = (
    "rgba(95, 205, 254, 0.26)",
    "rgba(95, 205, 254, 0.18)",
)
_DEFAULT_DNS_SELECTED_GRADIENT_STOPS_HOVER = (
    "rgba(95, 205, 254, 0.34)",
    "rgba(95, 205, 254, 0.24)",
)
_DEFAULT_DNS_SELECTED_BORDER = "rgba(95, 205, 254, 0.50)"
_DEFAULT_DNS_SELECTED_BORDER_HOVER = "rgba(95, 205, 254, 0.64)"
_DEFAULT_SUCCESS_SURFACE_GRADIENT_STOPS_LIGHT = (
    "rgba(82, 196, 119, 0.18)",
    "rgba(46, 160, 92, 0.12)",
)
_DEFAULT_SUCCESS_SURFACE_GRADIENT_STOPS_HOVER_LIGHT = (
    "rgba(82, 196, 119, 0.24)",
    "rgba(46, 160, 92, 0.16)",
)
_DEFAULT_SUCCESS_SURFACE_GRADIENT_STOPS_DARK = (
    "rgba(98, 214, 129, 0.22)",
    "rgba(54, 148, 88, 0.16)",
)
_DEFAULT_SUCCESS_SURFACE_GRADIENT_STOPS_HOVER_DARK = (
    "rgba(108, 224, 139, 0.30)",
    "rgba(64, 158, 98, 0.22)",
)
_DEFAULT_CONTROL_GRADIENT_STOPS_LIGHT = ("rgba(255, 255, 255, 0.92)", "rgba(243, 246, 251, 0.82)")
_DEFAULT_CONTROL_GRADIENT_STOPS_DARK = ("rgba(255, 255, 255, 0.080)", "rgba(255, 255, 255, 0.040)")
_DEFAULT_LIST_GRADIENT_STOPS_LIGHT = ("rgba(255, 255, 255, 0.88)", "rgba(244, 247, 252, 0.74)")
_DEFAULT_LIST_GRADIENT_STOPS_DARK = ("rgba(255, 255, 255, 0.075)", "rgba(255, 255, 255, 0.030)")
_DEFAULT_ITEM_HOVER_BG_LIGHT = "rgba(0, 0, 0, 0.055)"
_DEFAULT_ITEM_HOVER_BG_DARK = "rgba(255, 255, 255, 0.080)"
_DEFAULT_ITEM_SELECTED_BG_LIGHT = "rgba(68, 136, 217, 0.22)"
_DEFAULT_ITEM_SELECTED_BG_DARK = "rgba(95, 205, 254, 0.25)"
_DEFAULT_NEUTRAL_CARD_BORDER_LIGHT = "rgba(0, 0, 0, 0.10)"
_DEFAULT_NEUTRAL_CARD_BORDER_HOVER_LIGHT = "rgba(0, 0, 0, 0.16)"
_DEFAULT_NEUTRAL_CARD_BORDER_DISABLED_LIGHT = "rgba(0, 0, 0, 0.06)"
_DEFAULT_NEUTRAL_LIST_BORDER_LIGHT = "rgba(0, 0, 0, 0.10)"
_DEFAULT_NEUTRAL_CARD_BORDER_DARK = "rgba(255, 255, 255, 0.12)"
_DEFAULT_NEUTRAL_CARD_BORDER_HOVER_DARK = "rgba(255, 255, 255, 0.20)"
_DEFAULT_NEUTRAL_CARD_BORDER_DISABLED_DARK = "rgba(255, 255, 255, 0.06)"
_DEFAULT_NEUTRAL_LIST_BORDER_DARK = "rgba(255, 255, 255, 0.12)"

_DEFAULT_CARD_GRADIENT_STOPS_LIGHT = ("#FFFFFF", "#EDF3FC")
_DEFAULT_CARD_GRADIENT_STOPS_HOVER_LIGHT = ("#FFFFFF", "#E6EEFA")
_DEFAULT_CARD_DISABLED_GRADIENT_STOPS_LIGHT = ("#F3F7FD", "#E6EEF9")

_QTA_PIXMAP_CACHE_MAX = 512
_QTA_PIXMAP_CACHE: OrderedDict[tuple[str, str, int], QPixmap] = OrderedDict()

_THEME_DYNAMIC_LAYER_BEGIN = "/* __THEME_DYNAMIC_LAYER_BEGIN__ */"
_THEME_DYNAMIC_LAYER_END = "/* __THEME_DYNAMIC_LAYER_END__ */"



def start_theme_switch_metrics(theme_name: str, *, source: str = "unknown", click_started_at: float | None = None) -> int:
    return 0


def bump_theme_refresh_counter(page_name: str) -> None:
    pass


def note_theme_css_apply_duration(elapsed_ms: float) -> None:
    pass


def finish_theme_switch_metrics(switch_id: int | None, *, success: bool, message: str, theme_name: str) -> None:
    pass



def get_selected_theme(default: str | None = None, *, log_read: bool = True) -> str | None:
    """Возвращает сохранённую тему или default."""
    from config import REGISTRY_PATH
    saved = reg(REGISTRY_PATH, "SelectedTheme")
    if log_read:
        from log import log
        log(f"📦 Чтение темы из реестра [{REGISTRY_PATH}]: '{saved}' (default: '{default}')", "DEBUG")
    return saved or default

def set_selected_theme(theme_name: str) -> bool:
    """Записывает строку SelectedTheme"""
    from config import REGISTRY_PATH
    from log import log
    result = reg(REGISTRY_PATH, "SelectedTheme", theme_name)
    log(f"💾 Сохранение темы в реестр [{REGISTRY_PATH}]: '{theme_name}' -> {result}", "DEBUG")
    return result


def get_theme_bg_color(theme_name: str) -> str:
    """Returns background color RGB string for the current mode."""
    try:
        from qfluentwidgets import isDarkTheme
        is_light = not isDarkTheme()
    except Exception:
        is_light = False
    if str(theme_name).startswith("Светлая") or str(theme_name) == "light":
        is_light = True
    return "243, 243, 243" if is_light else "26, 26, 26"


def get_theme_content_bg_color(theme_name: str) -> str:
    """Returns content area background color (slightly lighter than bg)."""
    bg = get_theme_bg_color(theme_name)
    try:
        r, g, b = [int(x.strip()) for x in bg.split(',')]
        r = min(255, r + 7)
        g = min(255, g + 7)
        b = min(255, b + 7)
        return f"{r}, {g}, {b}"
    except Exception:
        return "39, 39, 39"


def _parse_rgb(rgb: str, *, default: tuple[int, int, int] = (0, 0, 0)) -> tuple[int, int, int]:
    try:
        parts = [int(x.strip()) for x in rgb.split(",")]
        if len(parts) != 3:
            return default
        r, g, b = parts
        r = max(0, min(255, r))
        g = max(0, min(255, g))
        b = max(0, min(255, b))
        return (r, g, b)
    except Exception:
        return default


def _rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    r, g, b = rgb
    return f"#{r:02x}{g:02x}{b:02x}"


def _mix_rgb(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    """Linear mix between a and b. t in [0..1]."""
    t = 0.0 if t < 0.0 else (1.0 if t > 1.0 else t)
    ar, ag, ab = a
    br, bg, bb = b
    r = int(round(ar + (br - ar) * t))
    g = int(round(ag + (bg - ag) * t))
    b2 = int(round(ab + (bb - ab) * t))
    return (
        max(0, min(255, r)),
        max(0, min(255, g)),
        max(0, min(255, b2)),
    )


def _accent_foreground_color(accent_rgb: tuple[int, int, int]) -> str:
    """Returns readable text color over accent backgrounds."""
    r, g, b = accent_rgb
    yiq = (r * 299 + g * 587 + b * 114) / 1000
    if yiq >= 160:
        return "rgba(18, 18, 18, 0.90)"
    return "rgba(245, 245, 245, 0.95)"


def _normalize_theme_name(theme_name: str | None) -> str:
    """Returns 'light' for light themes, 'dark' for dark themes."""
    raw = str(theme_name or "").strip()
    if not raw or raw == "dark":
        return "dark"
    if raw == "light":
        return "light"
    # Legacy: theme names starting with 'Светлая' → light
    if raw.startswith("Светлая"):
        return "light"
    return "dark"


def set_active_theme_name(theme_name: str | None) -> str:
    """No-op: theme name is now derived from isDarkTheme(). Kept for compatibility."""
    return _normalize_theme_name(theme_name)


def get_active_theme_name() -> str:
    """Returns 'Светлая синяя' if light mode, else 'Темная синяя'. Backward compat."""
    try:
        from qfluentwidgets import isDarkTheme
        return "Светлая синяя" if not isDarkTheme() else "Темная синяя"
    except Exception:
        return "Темная синяя"


def clear_qta_pixmap_cache() -> None:
    """Clears shared qtawesome pixmap cache."""
    _QTA_PIXMAP_CACHE.clear()


def invalidate_theme_tokens_cache() -> None:
    """Clears the theme tokens cache.

    Call when accent color changes so the next get_theme_tokens() call
    recomputes tokens with the new themeColor().
    """
    global _THEME_TOKENS_CACHE
    _THEME_TOKENS_CACHE.clear()


def _get_qfluent_themecolor() -> tuple[int, int, int] | None:
    """Returns the current qfluentwidgets theme accent as (r, g, b), or None."""
    try:
        from qfluentwidgets import themeColor
        c = themeColor()
        return (c.red(), c.green(), c.blue())
    except Exception:
        return None


def connect_qfluent_accent_signal() -> None:
    """Connects qconfig.themeColorChanged → invalidate_theme_tokens_cache.

    Call once after QApplication is created (typically in main.py).
    This ensures that whenever setThemeColor() is called, the tokens cache
    is cleared so pages re-compute CSS with the new accent.
    """
    try:
        from qfluentwidgets.common.config import qconfig
        qconfig.themeColorChanged.connect(lambda _color: invalidate_theme_tokens_cache())
    except Exception:
        pass


def apply_window_background(window, theme_name: str | None = None, preset: str | None = None) -> None:
    """Apply background color/image to FluentWindow based on preset."""
    if window is None:
        return

    # Determine preset
    if preset is None:
        try:
            from config.reg import get_background_preset
            preset = get_background_preset()
        except Exception:
            preset = "standard"

    # Handle background image (set_background_image if available)
    if hasattr(window, 'set_background_image'):
        if preset == "rkn_chan":
            import os
            rkn_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "rkn_chan_bg.png")
            window.set_background_image(rkn_path if os.path.exists(rkn_path) else None)
        else:
            window.set_background_image(None)

    if not hasattr(window, 'setCustomBackgroundColor'):
        return

    try:
        from PyQt6.QtGui import QColor as _QColor

        if preset == "amoled" or preset == "rkn_chan":
            bg = _QColor(0, 0, 0)
            window.setCustomBackgroundColor(bg, bg)
            return

        # Standard preset: compute light AND dark backgrounds separately.
        # setCustomBackgroundColor(light, dark) — first arg is light-mode color!
        light_bg_rgb = (243, 243, 243)
        dark_bg_rgb = (26, 26, 26)

        try:
            from config.reg import get_tinted_background, get_tinted_background_intensity
            if get_tinted_background():
                intensity = get_tinted_background_intensity()
                accent_rgb = _get_qfluent_themecolor()
                if accent_rgb is not None and intensity > 0:
                    light_bg_rgb = _mix_rgb(light_bg_rgb, accent_rgb, intensity / 100.0)
                    dark_bg_rgb = _mix_rgb(dark_bg_rgb, accent_rgb, intensity / 100.0)
        except Exception:
            pass

        window.setCustomBackgroundColor(_QColor(*light_bg_rgb), _QColor(*dark_bg_rgb))
    except Exception:
        pass


def _sync_theme_mode_to_qfluent(theme_name: str, window=None) -> None:
    """Calls setTheme(DARK/LIGHT) to match dark/light mode hint.

    theme_name: 'Светлая*' or 'light' → LIGHT, 'system' → AUTO, anything else → DARK.
    window: if provided, also applies window background.
    """
    try:
        from qfluentwidgets import setTheme, Theme
        if str(theme_name) == "system":
            setTheme(Theme.AUTO)
        elif str(theme_name).startswith("Светлая") or str(theme_name) == "light":
            setTheme(Theme.LIGHT)
        else:
            setTheme(Theme.DARK)

        if window is not None:
            apply_window_background(window)
    except Exception:
        pass


def _sync_theme_accent_to_qfluent(theme_name: str) -> None:
    """Syncs qfluentwidgets themeColor from saved custom accent or default."""
    try:
        from qfluentwidgets.common.config import qconfig
        from PyQt6.QtGui import QColor as _QColor

        try:
            from config.reg import get_accent_color
            hex_color = get_accent_color()
            if hex_color:
                c = _QColor(hex_color)
                if c.isValid():
                    qconfig.set(qconfig.themeColor, c)
                    return
        except Exception:
            pass

        # Default accent: Windows 11 blue
        qconfig.set(qconfig.themeColor, _QColor(0, 120, 212))
    except Exception:
        pass


@dataclass(frozen=True)
class ThemeTokens:
    """Small set of QSS-ready tokens derived from theme_name.

    Keep this minimal and semantic: callers should use tokens instead of hard-coded
    rgba(255,255,255,...) that breaks light themes.
    """

    theme_name: str
    is_light: bool
    accent_rgb: tuple[int, int, int]
    accent_rgb_str: str
    accent_hex: str
    accent_hover_hex: str
    accent_pressed_hex: str
    accent_fg: str

    fg: str
    fg_muted: str
    fg_faint: str
    icon_fg: str
    icon_fg_muted: str
    icon_fg_faint: str

    divider: str
    divider_strong: str

    surface_bg: str
    surface_bg_hover: str
    surface_bg_pressed: str
    surface_bg_disabled: str

    surface_border: str
    surface_border_hover: str
    surface_border_disabled: str

    accent_soft_bg: str
    accent_soft_bg_hover: str

    scrollbar_track: str
    scrollbar_handle: str
    scrollbar_handle_hover: str

    toggle_off_bg: str
    toggle_off_bg_hover: str
    toggle_off_border: str
    toggle_off_disabled_bg: str
    toggle_off_disabled_border: str

    font_family_qss: str


def get_theme_tokens(theme_name: str | None = None) -> ThemeTokens:
    """Returns QSS tokens for theme-aware custom widgets.

    Accent is always the live qfluentwidgets themeColor().
    Dark/light is derived from isDarkTheme() (overrideable by theme_name hint).
    """
    try:
        from qfluentwidgets import isDarkTheme
        is_light = not isDarkTheme()
    except Exception:
        is_light = False

    # Backward compat: explicit theme_name starting with "Светлая" forces light palette
    if theme_name is not None:
        raw = str(theme_name).strip()
        if raw.startswith("Светлая") or raw == "light":
            is_light = True
        elif raw.startswith("Темная") or raw == "dark":
            is_light = False

    accent_rgb = _get_qfluent_themecolor() or (0, 120, 212)

    # Cache keyed on palette + accent (cleared on accent change)
    cache_key = ("light" if is_light else "dark", accent_rgb)
    cached = _THEME_TOKENS_CACHE.get(cache_key)
    if cached is not None:
        return cached

    token_theme_name = "light" if is_light else "dark"
    accent_rgb_str = f"{accent_rgb[0]}, {accent_rgb[1]}, {accent_rgb[2]}"
    accent_hex = _rgb_to_hex(accent_rgb)
    accent_hover_hex = _rgb_to_hex(_mix_rgb(accent_rgb, (255, 255, 255), 0.12))
    accent_pressed_hex = _rgb_to_hex(_mix_rgb(accent_rgb, (0, 0, 0), 0.12))
    accent_fg = _accent_foreground_color(accent_rgb)

    if is_light:
        fg = "rgba(0, 0, 0, 0.90)"
        fg_muted = "rgba(0, 0, 0, 0.65)"
        fg_faint = "rgba(0, 0, 0, 0.40)"
        icon_fg = "#6b7280"
        icon_fg_muted = "#7d8594"
        icon_fg_faint = "#9aa2af"
        divider = "rgba(0, 0, 0, 0.08)"
        divider_strong = "rgba(0, 0, 0, 0.14)"
        surface_bg = "rgba(0, 0, 0, 0.035)"
        surface_bg_hover = "rgba(0, 0, 0, 0.055)"
        surface_bg_pressed = "rgba(0, 0, 0, 0.075)"
        surface_bg_disabled = "rgba(0, 0, 0, 0.020)"
        surface_border = "rgba(0, 0, 0, 0.10)"
        surface_border_hover = "rgba(0, 0, 0, 0.16)"
        surface_border_disabled = "rgba(0, 0, 0, 0.06)"
        scrollbar_track = "rgba(0, 0, 0, 0.04)"
        scrollbar_handle = "rgba(0, 0, 0, 0.18)"
        scrollbar_handle_hover = "rgba(0, 0, 0, 0.28)"
        toggle_off_bg = "rgba(142, 148, 158, 0.42)"
        toggle_off_bg_hover = "rgba(134, 141, 151, 0.52)"
        toggle_off_border = "rgba(120, 127, 138, 0.64)"
        toggle_off_disabled_bg = "rgba(154, 160, 170, 0.26)"
        toggle_off_disabled_border = "rgba(138, 145, 156, 0.34)"
    else:
        fg = "rgba(255, 255, 255, 0.92)"
        fg_muted = "rgba(255, 255, 255, 0.65)"
        fg_faint = "rgba(255, 255, 255, 0.35)"
        icon_fg = "#f5f5f5"
        icon_fg_muted = "#d2d7df"
        icon_fg_faint = "#aeb5c1"
        divider = "rgba(255, 255, 255, 0.06)"
        divider_strong = "rgba(255, 255, 255, 0.10)"
        surface_bg = "rgba(255, 255, 255, 0.04)"
        surface_bg_hover = "rgba(255, 255, 255, 0.07)"
        surface_bg_pressed = "rgba(255, 255, 255, 0.10)"
        surface_bg_disabled = "rgba(255, 255, 255, 0.02)"
        surface_border = "rgba(255, 255, 255, 0.12)"
        surface_border_hover = "rgba(255, 255, 255, 0.20)"
        surface_border_disabled = "rgba(255, 255, 255, 0.06)"
        scrollbar_track = "rgba(255, 255, 255, 0.03)"
        scrollbar_handle = "rgba(255, 255, 255, 0.15)"
        scrollbar_handle_hover = "rgba(255, 255, 255, 0.25)"
        toggle_off_bg = "rgba(132, 140, 154, 0.58)"
        toggle_off_bg_hover = "rgba(144, 152, 166, 0.70)"
        toggle_off_border = "rgba(170, 178, 192, 0.84)"
        toggle_off_disabled_bg = "rgba(122, 130, 144, 0.34)"
        toggle_off_disabled_border = "rgba(150, 158, 172, 0.48)"

    accent_soft_bg = f"rgba({accent_rgb_str}, 0.15)"
    accent_soft_bg_hover = f"rgba({accent_rgb_str}, 0.20)"

    tokens = ThemeTokens(
        theme_name=token_theme_name,
        is_light=is_light,
        accent_rgb=accent_rgb,
        accent_rgb_str=accent_rgb_str,
        accent_hex=accent_hex,
        accent_hover_hex=accent_hover_hex,
        accent_pressed_hex=accent_pressed_hex,
        accent_fg=accent_fg,
        fg=fg,
        fg_muted=fg_muted,
        fg_faint=fg_faint,
        icon_fg=icon_fg,
        icon_fg_muted=icon_fg_muted,
        icon_fg_faint=icon_fg_faint,
        divider=divider,
        divider_strong=divider_strong,
        surface_bg=surface_bg,
        surface_bg_hover=surface_bg_hover,
        surface_bg_pressed=surface_bg_pressed,
        surface_bg_disabled=surface_bg_disabled,
        surface_border=surface_border,
        surface_border_hover=surface_border_hover,
        surface_border_disabled=surface_border_disabled,
        accent_soft_bg=accent_soft_bg,
        accent_soft_bg_hover=accent_soft_bg_hover,
        scrollbar_track=scrollbar_track,
        scrollbar_handle=scrollbar_handle,
        scrollbar_handle_hover=scrollbar_handle_hover,
        toggle_off_bg=toggle_off_bg,
        toggle_off_bg_hover=toggle_off_bg_hover,
        toggle_off_border=toggle_off_border,
        toggle_off_disabled_bg=toggle_off_disabled_bg,
        toggle_off_disabled_border=toggle_off_disabled_border,
        font_family_qss="'Segoe UI Variable', 'Segoe UI', Arial, sans-serif",
    )

    _THEME_TOKENS_CACHE[cache_key] = tokens
    return tokens


_RGBA_COLOR_RE = re.compile(
    r"^\s*rgba?\(\s*([0-9]{1,3})\s*,\s*([0-9]{1,3})\s*,\s*([0-9]{1,3})\s*(?:,\s*([0-9]*\.?[0-9]+)\s*)?\)\s*$",
    re.IGNORECASE,
)
_QTA_ICON_PATCHED = False


def _theme_tokens_for_icons(theme_name: str | None = None) -> ThemeTokens:
    return get_theme_tokens(theme_name)


def _parse_css_rgba_color(raw: str) -> QColor | None:
    text = str(raw or "").strip()
    match = _RGBA_COLOR_RE.fullmatch(text)
    if not match:
        return None

    try:
        r = max(0, min(255, int(match.group(1))))
        g = max(0, min(255, int(match.group(2))))
        b = max(0, min(255, int(match.group(3))))
        alpha_raw = match.group(4)

        if alpha_raw is None:
            a = 255
        else:
            a_float = float(alpha_raw)
            # Accept both [0..1] and [0..255] alpha notations.
            if a_float <= 1.0:
                a = int(round(max(0.0, min(1.0, a_float)) * 255.0))
            else:
                a = int(round(max(0.0, min(255.0, a_float))))

        return QColor(r, g, b, a)
    except Exception:
        return None


def _to_qcolor(value) -> QColor | None:
    if isinstance(value, QColor):
        return value if value.isValid() else None

    text = str(value or "").strip()
    if not text:
        return None

    # QColor does not parse CSS rgba(..., 0.92) reliably; handle it explicitly.
    parsed = _parse_css_rgba_color(text)
    if parsed is not None and parsed.isValid():
        return parsed

    color = QColor(text)
    if color.isValid():
        return color
    return None


def to_qcolor(value, fallback=None) -> QColor:
    """Parses theme/QSS color strings (including rgba with fractional alpha).

    Always returns a valid QColor (falls back to black if both values are invalid).
    """
    color = _to_qcolor(value)
    if color is not None and color.isValid():
        return QColor(color)

    fb = _to_qcolor(fallback)
    if fb is not None and fb.isValid():
        return QColor(fb)

    return QColor(0, 0, 0)


def _qcolor_to_qss_rgba(color: QColor) -> str:
    return f"rgba({color.red()}, {color.green()}, {color.blue()}, {color.alpha()})"


def build_vertical_gradient_qss(top_color: str, bottom_color: str) -> str:
    """Builds a true vertical qlineargradient from two color stops."""
    return (
        "qlineargradient(x1:0, y1:0, x2:0, y2:1, "
        f"stop:0 {top_color}, stop:1 {bottom_color})"
    )


def _get_theme_gradient_stops_from_keys(
    theme_name: str,
    *,
    top_key: str,
    bottom_key: str,
    fallback: tuple[str, str],
    hover: bool = False,
    hover_top_key: str | None = None,
    hover_bottom_key: str | None = None,
    hover_fallback: tuple[str, str] | None = None,
) -> tuple[str, str]:
    """Returns default top/bottom gradient pair based on dark/light."""
    # Without THEMES dict, always return the appropriate defaults.
    if hover and hover_fallback is not None:
        return hover_fallback
    return fallback


def _get_theme_card_gradient_stops(theme_name: str, *, hover: bool = False) -> tuple[str, str]:
    """Returns card gradient stops based on dark/light mode."""
    is_light = _is_light_theme_name(theme_name)
    if is_light:
        fallback = _DEFAULT_CARD_GRADIENT_STOPS_LIGHT
        hover_fallback = _DEFAULT_CARD_GRADIENT_STOPS_HOVER_LIGHT
    else:
        fallback = _DEFAULT_CARD_GRADIENT_STOPS
        hover_fallback = _DEFAULT_CARD_GRADIENT_STOPS_HOVER
    return _get_theme_gradient_stops_from_keys(
        theme_name,
        top_key="card_gradient_top",
        bottom_key="card_gradient_bottom",
        fallback=fallback,
        hover=hover,
        hover_top_key="card_gradient_hover_top",
        hover_bottom_key="card_gradient_hover_bottom",
        hover_fallback=hover_fallback,
    )


def _get_theme_card_disabled_gradient_stops(theme_name: str) -> tuple[str, str]:
    """Returns disabled-card gradient stops based on dark/light mode."""
    is_light = _is_light_theme_name(theme_name)
    if is_light:
        fallback = _DEFAULT_CARD_DISABLED_GRADIENT_STOPS_LIGHT
    else:
        fallback = _DEFAULT_CARD_DISABLED_GRADIENT_STOPS
    return _get_theme_gradient_stops_from_keys(
        theme_name,
        top_key="card_gradient_disabled_top",
        bottom_key="card_gradient_disabled_bottom",
        fallback=fallback,
    )


def _get_theme_dns_selected_gradient_stops(
    theme_name: str,
    *,
    hover: bool = False,
) -> tuple[str, str]:
    """Returns DNS-selected gradient using live accent color."""
    tokens = get_theme_tokens(theme_name)
    r, g, b = tokens.accent_rgb
    if hover:
        return (f"rgba({r}, {g}, {b}, 0.34)", f"rgba({r}, {g}, {b}, 0.24)")
    return (f"rgba({r}, {g}, {b}, 0.26)", f"rgba({r}, {g}, {b}, 0.18)")


def _get_theme_dns_selected_border_color(theme_name: str, *, hover: bool = False) -> str:
    """Returns DNS-selected border color using live accent."""
    tokens = get_theme_tokens(theme_name)
    r, g, b = tokens.accent_rgb
    return f"rgba({r}, {g}, {b}, {'0.64' if hover else '0.50'})"


def _get_theme_success_gradient_stops(theme_name: str, *, hover: bool = False) -> tuple[str, str]:
    """Returns centralized success-surface gradient stops for a theme."""
    is_light = _is_light_theme_name(theme_name)
    fallback = (
        _DEFAULT_SUCCESS_SURFACE_GRADIENT_STOPS_LIGHT
        if is_light
        else _DEFAULT_SUCCESS_SURFACE_GRADIENT_STOPS_DARK
    )
    hover_fallback = (
        _DEFAULT_SUCCESS_SURFACE_GRADIENT_STOPS_HOVER_LIGHT
        if is_light
        else _DEFAULT_SUCCESS_SURFACE_GRADIENT_STOPS_HOVER_DARK
    )
    return _get_theme_gradient_stops_from_keys(
        theme_name,
        top_key="success_gradient_top",
        bottom_key="success_gradient_bottom",
        fallback=fallback,
        hover=hover,
        hover_top_key="success_gradient_hover_top",
        hover_bottom_key="success_gradient_hover_bottom",
        hover_fallback=hover_fallback,
    )


def _is_light_theme_name(theme_name: str) -> bool:
    s = str(theme_name)
    return s == "light" or s.startswith("Светлая")


def _get_theme_color_value(theme_name: str, key: str, fallback: str) -> str:
    return fallback


def _get_theme_control_gradient_stops(theme_name: str) -> tuple[str, str]:
    """Returns centralized header/control gradient stops for a theme."""
    is_light = _is_light_theme_name(theme_name)
    fallback = _DEFAULT_CONTROL_GRADIENT_STOPS_LIGHT if is_light else _DEFAULT_CONTROL_GRADIENT_STOPS_DARK
    return _get_theme_gradient_stops_from_keys(
        theme_name,
        top_key="control_gradient_top",
        bottom_key="control_gradient_bottom",
        fallback=fallback,
    )


def _get_theme_list_gradient_stops(theme_name: str) -> tuple[str, str]:
    """Returns centralized list/tree/table gradient stops for a theme."""
    is_light = _is_light_theme_name(theme_name)
    fallback = _DEFAULT_LIST_GRADIENT_STOPS_LIGHT if is_light else _DEFAULT_LIST_GRADIENT_STOPS_DARK
    return _get_theme_gradient_stops_from_keys(
        theme_name,
        top_key="list_gradient_top",
        bottom_key="list_gradient_bottom",
        fallback=fallback,
    )


def _get_theme_item_hover_bg(theme_name: str) -> str:
    """Returns centralized item hover background for a theme."""
    fallback = _DEFAULT_ITEM_HOVER_BG_LIGHT if _is_light_theme_name(theme_name) else _DEFAULT_ITEM_HOVER_BG_DARK
    return _get_theme_color_value(theme_name, "item_hover_bg", fallback)


def _get_theme_item_selected_bg(theme_name: str) -> str:
    """Returns item selected background using live accent color."""
    tokens = get_theme_tokens(theme_name)
    r, g, b = tokens.accent_rgb
    return f"rgba({r}, {g}, {b}, 0.22)"


def _get_theme_neutral_card_border_color(
    theme_name: str,
    *,
    hover: bool = False,
    disabled: bool = False,
) -> str:
    """Returns centralized neutral card border colors for a theme."""
    is_light = _is_light_theme_name(theme_name)
    if disabled:
        key = "neutral_card_disabled_border"
        fallback = _DEFAULT_NEUTRAL_CARD_BORDER_DISABLED_LIGHT if is_light else _DEFAULT_NEUTRAL_CARD_BORDER_DISABLED_DARK
    elif hover:
        key = "neutral_card_border_hover"
        fallback = _DEFAULT_NEUTRAL_CARD_BORDER_HOVER_LIGHT if is_light else _DEFAULT_NEUTRAL_CARD_BORDER_HOVER_DARK
    else:
        key = "neutral_card_border"
        fallback = _DEFAULT_NEUTRAL_CARD_BORDER_LIGHT if is_light else _DEFAULT_NEUTRAL_CARD_BORDER_DARK
    return _get_theme_color_value(theme_name, key, fallback)


def _get_theme_neutral_list_border_color(theme_name: str) -> str:
    """Returns centralized neutral list border color for a theme."""
    fallback = _DEFAULT_NEUTRAL_LIST_BORDER_LIGHT if _is_light_theme_name(theme_name) else _DEFAULT_NEUTRAL_LIST_BORDER_DARK
    return _get_theme_color_value(theme_name, "neutral_list_border", fallback)


def get_card_gradient_qss(theme_name: str | None = None, *, hover: bool = False) -> str:
    """Returns centralized card gradient used across framed surfaces."""
    theme = get_theme_tokens(theme_name).theme_name
    top, bottom = _get_theme_card_gradient_stops(theme, hover=hover)
    return build_vertical_gradient_qss(top, bottom)


def get_control_gradient_qss(theme_name: str | None = None) -> str:
    """Returns centralized control/header gradient."""
    theme = get_theme_tokens(theme_name).theme_name
    top, bottom = _get_theme_control_gradient_stops(theme)
    return build_vertical_gradient_qss(top, bottom)


def get_list_gradient_qss(theme_name: str | None = None) -> str:
    """Returns centralized list/tree/table gradient."""
    theme = get_theme_tokens(theme_name).theme_name
    top, bottom = _get_theme_list_gradient_stops(theme)
    return build_vertical_gradient_qss(top, bottom)


def get_item_hover_bg_qss(theme_name: str | None = None) -> str:
    """Returns centralized item hover background color."""
    theme = get_theme_tokens(theme_name).theme_name
    return _get_theme_item_hover_bg(theme)


def get_item_selected_bg_qss(theme_name: str | None = None) -> str:
    """Returns centralized item selected background color."""
    theme = get_theme_tokens(theme_name).theme_name
    return _get_theme_item_selected_bg(theme)


def get_neutral_card_border_qss(
    theme_name: str | None = None,
    *,
    hover: bool = False,
    disabled: bool = False,
) -> str:
    """Returns centralized neutral card border color."""
    theme = get_theme_tokens(theme_name).theme_name
    return _get_theme_neutral_card_border_color(theme, hover=hover, disabled=disabled)


def get_neutral_list_border_qss(theme_name: str | None = None) -> str:
    """Returns centralized neutral list border color."""
    theme = get_theme_tokens(theme_name).theme_name
    return _get_theme_neutral_list_border_color(theme)


def get_card_disabled_gradient_qss(theme_name: str | None = None) -> str:
    """Returns centralized disabled card gradient used across framed surfaces."""
    theme = get_theme_tokens(theme_name).theme_name
    top, bottom = _get_theme_card_disabled_gradient_stops(theme)
    return build_vertical_gradient_qss(top, bottom)


def get_dns_selected_gradient_qss(theme_name: str | None = None, *, hover: bool = False) -> str:
    """Returns centralized DNS selected gradient used by DNS cards."""
    theme = get_theme_tokens(theme_name).theme_name
    top, bottom = _get_theme_dns_selected_gradient_stops(theme, hover=hover)
    return build_vertical_gradient_qss(top, bottom)


def get_dns_selected_border_qss(theme_name: str | None = None, *, hover: bool = False) -> str:
    """Returns centralized DNS selected border color."""
    theme = get_theme_tokens(theme_name).theme_name
    return _get_theme_dns_selected_border_color(theme, hover=hover)


def get_selected_surface_gradient_qss(theme_name: str | None = None, *, hover: bool = False) -> str:
    """Returns centralized selected/accent surface gradient."""
    return get_dns_selected_gradient_qss(theme_name, hover=hover)


def get_success_surface_gradient_qss(theme_name: str | None = None, *, hover: bool = False) -> str:
    """Returns centralized success surface gradient."""
    theme = get_theme_tokens(theme_name).theme_name
    top, bottom = _get_theme_success_gradient_stops(theme, hover=hover)
    return build_vertical_gradient_qss(top, bottom)


def get_tinted_surface_gradient_qss(
    base_color: str,
    *,
    theme_name: str | None = None,
    hover: bool = False,
) -> str:
    """Builds a theme-aware real gradient from an arbitrary base color."""
    tokens = get_theme_tokens(theme_name)
    parsed = _to_qcolor(base_color)
    if parsed is None:
        return get_card_gradient_qss(tokens.theme_name, hover=hover)

    alpha = max(0, min(255, parsed.alpha()))
    base_rgb = (parsed.red(), parsed.green(), parsed.blue())
    if tokens.is_light:
        top_mix = 0.16 if hover else 0.11
        bottom_mix = 0.10 if hover else 0.06
    else:
        top_mix = 0.12 if hover else 0.08
        bottom_mix = 0.18 if hover else 0.13

    top_rgb = _mix_rgb(base_rgb, (255, 255, 255), top_mix)
    bottom_rgb = _mix_rgb(base_rgb, (0, 0, 0), bottom_mix)
    top = _qcolor_to_qss_rgba(QColor(top_rgb[0], top_rgb[1], top_rgb[2], alpha))
    bottom = _qcolor_to_qss_rgba(QColor(bottom_rgb[0], bottom_rgb[1], bottom_rgb[2], alpha))
    return build_vertical_gradient_qss(top, bottom)


def get_theme_icon_color(theme_name: str | None = None, muted: bool = False, faint: bool = False) -> str:
    """Returns global icon color for current theme.

    Light themes -> dark gray icons.
    Dark themes -> light icons.
    """
    tokens = _theme_tokens_for_icons(theme_name)
    if faint:
        return tokens.icon_fg_faint
    if muted:
        return tokens.icon_fg_muted
    return tokens.icon_fg


def get_theme_accent_foreground(theme_name: str | None = None) -> str:
    """Returns readable text/icon color for accent-filled controls."""
    return get_theme_tokens(theme_name).accent_fg


def resolve_icon_color(color=None, *, theme_name: str | None = None, muted_fallback: bool = False) -> str:
    """Converts arbitrary icon color input to a qtawesome/QColor-safe color string."""
    tokens = _theme_tokens_for_icons(theme_name)
    fallback = tokens.icon_fg_muted if muted_fallback else tokens.icon_fg

    if color is None:
        return fallback

    # Map semantic text tokens to dedicated icon palette.
    raw = str(color).strip()
    if raw == tokens.fg:
        return tokens.icon_fg
    if raw == tokens.fg_muted:
        return tokens.icon_fg_muted
    if raw == tokens.fg_faint:
        return tokens.icon_fg_faint

    parsed = _to_qcolor(color)
    if parsed is None:
        return fallback

    # Normalize near-black icon colors to theme fallback:
    # light themes -> gray, dark themes -> light icon color.
    if parsed.red() < 26 and parsed.green() < 26 and parsed.blue() < 26:
        return fallback

    return parsed.name(QColor.NameFormat.HexArgb)


def get_cached_qta_pixmap(
    icon_name: str,
    *,
    color=None,
    size: int = 16,
    theme_name: str | None = None,
    muted_fallback: bool = False,
) -> QPixmap:
    """Returns cached qtawesome pixmap for icon+color+size."""
    try:
        import qtawesome as qta
    except Exception:
        return QPixmap()

    safe_size = max(1, int(size))
    resolved_color = resolve_icon_color(color, theme_name=theme_name, muted_fallback=muted_fallback)
    key = (str(icon_name or ""), resolved_color, safe_size)

    cached = _QTA_PIXMAP_CACHE.get(key)
    if cached is not None and not cached.isNull():
        _QTA_PIXMAP_CACHE.move_to_end(key)
        return QPixmap(cached)

    try:
        pixmap = qta.icon(icon_name, color=resolved_color).pixmap(safe_size, safe_size)
    except Exception:
        return QPixmap()

    _QTA_PIXMAP_CACHE[key] = QPixmap(pixmap)
    _QTA_PIXMAP_CACHE.move_to_end(key)
    while len(_QTA_PIXMAP_CACHE) > _QTA_PIXMAP_CACHE_MAX:
        _QTA_PIXMAP_CACHE.popitem(last=False)

    return pixmap


def install_qtawesome_icon_theme_patch() -> None:
    """Installs global qtawesome icon color defaults and rgba() normalization."""
    global _QTA_ICON_PATCHED
    if _QTA_ICON_PATCHED:
        return

    try:
        import qtawesome as qta
    except Exception as e:
        log(f"⚠️ Не удалось импортировать qtawesome для icon patch: {e}", "DEBUG")
        return

    original_icon = getattr(qta, "icon", None)
    if not callable(original_icon):
        return

    def _patched_qta_icon(*args, **kwargs):
        local_kwargs = dict(kwargs)

        # Normalize known color arguments.
        local_kwargs["color"] = resolve_icon_color(local_kwargs.get("color"), muted_fallback=False)
        if "color_disabled" in local_kwargs:
            local_kwargs["color_disabled"] = resolve_icon_color(local_kwargs.get("color_disabled"), muted_fallback=True)
        if "color_active" in local_kwargs:
            local_kwargs["color_active"] = resolve_icon_color(local_kwargs.get("color_active"), muted_fallback=False)
        if "color_selected" in local_kwargs:
            local_kwargs["color_selected"] = resolve_icon_color(local_kwargs.get("color_selected"), muted_fallback=False)
        if "color_on" in local_kwargs:
            local_kwargs["color_on"] = resolve_icon_color(local_kwargs.get("color_on"), muted_fallback=False)
        if "color_off" in local_kwargs:
            local_kwargs["color_off"] = resolve_icon_color(local_kwargs.get("color_off"), muted_fallback=True)

        return original_icon(*args, **local_kwargs)

    try:
        _patched_qta_icon.__name__ = getattr(original_icon, "__name__", "icon")
        _patched_qta_icon.__doc__ = getattr(original_icon, "__doc__", None)
    except Exception:
        pass

    qta.icon = _patched_qta_icon
    _QTA_ICON_PATCHED = True



def _build_dynamic_style_sheet(theme_name: str) -> str:
    """Legacy CSS pipeline — returns empty string (qfluentwidgets handles styling)."""
    return ""


def _assemble_final_css(
    base_css: str,
    theme_name: str,
    *,
    is_amoled: bool = False,
    is_pure_black: bool = False,
    is_rkn_tyan: bool = False,
    is_rkn_tyan_2: bool = False,
) -> str:
    """Legacy CSS assembly — returns base_css unmodified (qfluentwidgets handles styling)."""
    return base_css


def _split_final_css_layers(final_css: str) -> tuple[str, str]:
    """Legacy CSS layer split — returns (full_css, empty_overlay)."""
    return (final_css, "")



class ThemeBuildWorker(QObject):
    """Worker for theme CSS preparation. Returns empty CSS (qfluentwidgets handles styling)."""

    finished = pyqtSignal(str, str)  # final_css, theme_name
    error = pyqtSignal(str)
    progress = pyqtSignal(str)  # status message

    def __init__(self, theme_file: str, theme_name: str, cache_file: str,
                 is_amoled: bool = False, is_pure_black: bool = False, is_rkn_tyan: bool = False, is_rkn_tyan_2: bool = False):
        super().__init__()
        self.theme_file = theme_file
        self.theme_name = theme_name
        self.cache_file = cache_file
        self.is_amoled = is_amoled
        self.is_pure_black = is_pure_black
        self.is_rkn_tyan = is_rkn_tyan
        self.is_rkn_tyan_2 = is_rkn_tyan_2

    def run(self):
        try:
            self.progress.emit("Applying theme...")
            self.finished.emit("", self.theme_name)
        except Exception as e:
            self.error.emit(str(e))


class PremiumCheckWorker(QObject):
    """Воркер для асинхронной проверки премиум статуса"""
    
    finished = pyqtSignal(bool, str, object)  # is_premium, message, days
    error = pyqtSignal(str)
    
    def __init__(self, donate_checker):
        super().__init__()
        self.donate_checker = donate_checker
    
    def run(self):
        """Выполнить проверку подписки"""
        try:
            log("Начало асинхронной проверки подписки", "DEBUG")
            start_time = time.time()
            
            if not self.donate_checker:
                self.finished.emit(False, "Checker не доступен", None)
                return
            
            # Проверяем тип checker'а
            checker_type = self.donate_checker.__class__.__name__
            if checker_type == 'DummyChecker':
                self.finished.emit(False, "Dummy checker", None)
                return
            
            # Выполняем проверку
            is_premium, message, days = self.donate_checker.check_subscription_status(use_cache=False)
            
            elapsed = time.time() - start_time
            log(f"Асинхронная проверка завершена за {elapsed:.2f}с: premium={is_premium}", "DEBUG")
            
            self.finished.emit(is_premium, message, days)
            
        except Exception as e:
            log(f"Ошибка в PremiumCheckWorker: {e}", "❌ ERROR")
            self.error.emit(str(e))
            self.finished.emit(False, f"Ошибка: {e}", None)





class ThemeManager:
    """Класс для управления темами приложения"""

    def __init__(self, app, widget, status_label=None, theme_folder=None, donate_checker=None, apply_on_init=True):
        self.app = app
        self.widget = widget
        # status_label больше не используется в новом интерфейсе
        self.theme_folder = theme_folder
        self.donate_checker = donate_checker
        self._fallback_due_to_premium: str | None = None
        self._theme_applied = False
        
        # Кеш для премиум статуса
        self._premium_cache: Optional[Tuple[bool, str, Optional[int]]] = None
        self._cache_time: Optional[float] = None
        self._cache_duration = 60  # 60 секунд кеша
        
        # Потоки для асинхронных проверок
        self._check_thread: Optional[QThread] = None
        self._check_worker: Optional[PremiumCheckWorker] = None
        
        # Потоки для асинхронной генерации CSS темы
        self._theme_build_thread: Optional[QThread] = None
        self._theme_build_worker: Optional[ThemeBuildWorker] = None
        self._pending_theme_data: Optional[dict] = None  # legacy поле (не используется для новых запросов)
        self._theme_request_seq = 0
        self._latest_theme_request_id = 0
        self._latest_requested_theme: str | None = None
        self._active_theme_build_jobs: dict[int, tuple[QThread, ThemeBuildWorker]] = {}
        
        # Хеш текущего CSS для оптимизации (не применять повторно)
        self._current_css_hash: Optional[int] = None
        self._current_base_css_hash: Optional[int] = None
        self._current_overlay_css_hash: Optional[int] = None
        self._app_base_initialized = False
        self._palette_reset_once_done = False
        self._final_css_cache_max = 8
        self._final_css_memory_cache: OrderedDict[str, str] = OrderedDict()

        # список тем — теперь пустой (тема определяется isDarkTheme() системно)
        self.themes = []
        # Initialize from current qfluentwidgets state to avoid overriding startup setTheme()
        self.current_theme = get_active_theme_name()
        log("🎨 ThemeManager: режим из isDarkTheme(), тема не выбирается", "DEBUG")

        # Тема применяется асинхронно через apply_theme_async() после инициализации
        # apply_on_init больше не используется - всегда False
        if apply_on_init:
            # Для обратной совместимости - используем async
            self.apply_theme_async(self.current_theme, persist=False)
        # Минимальный CSS теперь применяется в main.py ДО показа окна

    def __del__(self):
        """Деструктор для очистки ресурсов"""
        try:
            # Останавливаем поток если он запущен
            if hasattr(self, '_check_thread') and self._check_thread is not None:
                try:
                    if self._check_thread.isRunning():
                        self._check_thread.quit()
                        self._check_thread.wait(500)  # Ждем максимум 0.5 секунды
                except RuntimeError:
                    pass
        except Exception:
            pass

    def cleanup(self):
        """Безопасная очистка всех ресурсов"""
        try:
            # Очищаем кеш
            self._premium_cache = None
            self._cache_time = None
            self._final_css_memory_cache.clear()
            
            # Останавливаем поток проверки
            if hasattr(self, '_check_thread') and self._check_thread is not None:
                try:
                    if self._check_thread.isRunning():
                        log("Останавливаем поток проверки премиума", "DEBUG")
                        self._check_thread.quit()
                        if not self._check_thread.wait(1000):
                            log("Принудительное завершение потока", "WARNING")
                            self._check_thread.terminate()
                            self._check_thread.wait()
                except RuntimeError:
                    pass
                finally:
                    self._check_thread = None
                    self._check_worker = None

            # Останавливаем фоновые задачи сборки тем (если остались)
            for _, (thread, _) in list(self._active_theme_build_jobs.items()):
                try:
                    if thread.isRunning():
                        thread.quit()
                        thread.wait(100)
                except RuntimeError:
                    pass
            self._cleanup_theme_build_thread()
                    
            log("ThemeManager очищен", "DEBUG")
            
        except Exception as e:
            log(f"Ошибка при очистке ThemeManager: {e}", "ERROR")

    def _is_premium_theme(self, theme_name: str) -> bool:
        """Проверяет, является ли тема премиум."""
        return False  # Без THEMES-словаря Premium = bg preset, not theme name

    def _is_premium_available(self) -> bool:
        """Проверяет доступность премиума (использует кеш)"""
        if not self.donate_checker:
            return False
        
        # Проверяем кеш
        if self._premium_cache and self._cache_time:
            cache_age = time.time() - self._cache_time
            if cache_age < self._cache_duration:
                log(f"Используем кешированный премиум статус: {self._premium_cache[0]}", "DEBUG")
                return self._premium_cache[0]
        
        # Если кеша нет, возвращаем False и запускаем асинхронную проверку
        log("Кеш премиума отсутствует, запускаем асинхронную проверку", "DEBUG")
        self._start_async_premium_check()
        return False

    def _start_async_premium_check(self):
        """Запускает асинхронную проверку премиум статуса"""
        if not self.donate_checker:
            return
        
        # ✅ ДОБАВИТЬ ЗАЩИТУ
        if hasattr(self, '_check_in_progress') and self._check_in_progress:
            log("Проверка премиума уже выполняется, пропускаем", "DEBUG")
            return
        
        self._check_in_progress = True
            
        # Проверяем тип checker'а
        checker_type = self.donate_checker.__class__.__name__
        if checker_type == 'DummyChecker':
            log("DummyChecker обнаружен, пропускаем асинхронную проверку", "DEBUG")
            return
        
        # Проверяем существование потока перед проверкой isRunning
        if self._check_thread is not None:
            try:
                if self._check_thread.isRunning():
                    log("Асинхронная проверка уже выполняется", "DEBUG")
                    return
            except RuntimeError:
                # Поток был удален, сбрасываем ссылку
                log("Предыдущий поток был удален, создаем новый", "DEBUG")
                self._check_thread = None
                self._check_worker = None
        
        log("Запуск асинхронной проверки премиум статуса", "DEBUG")
        
        # Очищаем старые ссылки перед созданием новых
        if self._check_thread is not None:
            try:
                if self._check_thread.isRunning():
                    self._check_thread.quit()
                    self._check_thread.wait(1000)  # Ждем максимум 1 секунду
            except RuntimeError:
                pass
            self._check_thread = None
            self._check_worker = None
        
        # Создаем воркер и поток
        self._check_thread = QThread()
        self._check_worker = PremiumCheckWorker(self.donate_checker)
        self._check_worker.moveToThread(self._check_thread)
        
        # Подключаем сигналы
        self._check_thread.started.connect(self._check_worker.run)
        self._check_worker.finished.connect(self._on_premium_check_finished)
        self._check_worker.error.connect(self._on_premium_check_error)
        
        # Правильная очистка потока после завершения
        def cleanup_thread():
            try:
                self._check_in_progress = False
                if self._check_worker:
                    self._check_worker.deleteLater()
                    self._check_worker = None
                if self._check_thread:
                    self._check_thread.deleteLater()
                    self._check_thread = None
            except RuntimeError:
                # Объекты уже удалены
                self._check_worker = None
                self._check_thread = None
        
        self._check_worker.finished.connect(self._check_thread.quit)
        self._check_thread.finished.connect(cleanup_thread)
        
        # Запускаем поток
        try:
            self._check_thread.start()
        except RuntimeError as e:
            log(f"Ошибка запуска потока проверки премиума: {e}", "❌ ERROR")
            self._check_thread = None
            self._check_worker = None

    def _on_premium_check_finished(self, is_premium: bool, message: str, days: Optional[int]):
        """Обработчик завершения асинхронной проверки"""
        log(f"Асинхронная проверка завершена: premium={is_premium}, msg='{message}', days={days}", "DEBUG")
        
        # Обновляем кеш
        self._premium_cache = (is_premium, message, days)
        self._cache_time = time.time()
        
        # Обновляем заголовок окна
        if hasattr(self.widget, "update_title_with_subscription_status"):
            try:
                self.widget.update_title_with_subscription_status(is_premium, self.current_theme, days)
            except Exception as e:
                log(f"Ошибка обновления заголовка: {e}", "❌ ERROR")
        
        # Если есть отложенная премиум тема и премиум доступен, применяем её асинхронно
        if self._fallback_due_to_premium and is_premium:
            log(f"Восстанавливаем отложенную премиум тему: {self._fallback_due_to_premium}", "INFO")
            theme_to_restore = self._fallback_due_to_premium
            self._fallback_due_to_premium = None
            self.apply_theme_async(theme_to_restore, persist=True)
        
        # Обновляем список доступных тем в UI
        if hasattr(self.widget, 'theme_handler'):
            try:
                self.widget.theme_handler.update_available_themes()
            except Exception as e:
                log(f"Ошибка обновления списка тем: {e}", "DEBUG")

    def _on_premium_check_error(self, error: str):
        """Обработчик ошибки асинхронной проверки"""
        log(f"Ошибка асинхронной проверки премиума: {error}", "❌ ERROR")
        
        # Устанавливаем кеш с негативным результатом
        self._premium_cache = (False, f"Ошибка: {error}", None)
        self._cache_time = time.time()

    def reapply_saved_theme_if_premium(self):
        """Восстанавливает премиум-тему после инициализации DonateChecker"""
        log(f"🔄 reapply_saved_theme_if_premium: fallback={self._fallback_due_to_premium}", "DEBUG")
        # Запускаем асинхронную проверку
        self._start_async_premium_check()

    def get_available_themes(self):
        """Returns empty list (theme selection removed)."""
        return []

    def get_clean_theme_name(self, display_name):
        """Извлекает чистое имя темы из отображаемого названия"""
        clean_name = display_name
        suffixes = [" (заблокировано)", " (AMOLED Premium)", " (Pure Black Premium)"]
        for suffix in suffixes:
            clean_name = clean_name.replace(suffix, "")
        return clean_name

    def _is_amoled_theme(self, theme_name: str) -> bool:
        return False

    def _is_pure_black_theme(self, theme_name: str) -> bool:
        return False

    def _apply_rkn_with_protection(self):
        """Применяет фон РКН Тян с защитой от перезаписи"""
        try:
            log("Применение фона РКН Тян с защитой", "DEBUG")
            success = self.apply_rkn_background()
            if success:
                # Дополнительная защита - повторная проверка через 200мс
                QTimer.singleShot(200, self._verify_rkn_background)
                log("Фон РКН Тян успешно применён", "INFO")
            else:
                log("Не удалось применить фон РКН Тян", "WARNING")
        except Exception as e:
            log(f"Ошибка при применении фона РКН Тян: {e}", "❌ ERROR")

    def _verify_rkn_background(self):
        """Проверяет что фон РКН Тян всё ещё применён"""
        try:
            # Определяем правильный виджет
            target_widget = self.widget
            if hasattr(self.widget, 'main_widget'):
                target_widget = self.widget.main_widget
            
            if not target_widget.autoFillBackground() or not target_widget.property("hasCustomBackground"):
                log("Фон РКН Тян был сброшен, восстанавливаем", "WARNING")
                self.apply_rkn_background()
            else:
                log("Фон РКН Тян успешно сохранён", "DEBUG")
        except Exception as e:
            log(f"Ошибка проверки фона РКН Тян: {e}", "ERROR")

    def _apply_rkn2_with_protection(self):
        """Применяет фон РКН Тян 2 с защитой от перезаписи"""
        try:
            log("Применение фона РКН Тян 2 с защитой", "DEBUG")
            success = self.apply_rkn2_background()
            if success:
                # Дополнительная защита - повторная проверка через 200мс
                QTimer.singleShot(200, self._verify_rkn2_background)
                log("Фон РКН Тян 2 успешно применён", "INFO")
            else:
                log("Не удалось применить фон РКН Тян 2", "WARNING")
        except Exception as e:
            log(f"Ошибка при применении фона РКН Тян 2: {e}", "❌ ERROR")

    def _verify_rkn2_background(self):
        """Проверяет что фон РКН Тян 2 всё ещё применён"""
        try:
            # Определяем правильный виджет
            target_widget = self.widget
            if hasattr(self.widget, 'main_widget'):
                target_widget = self.widget.main_widget
            
            if not target_widget.autoFillBackground() or not target_widget.property("hasCustomBackground"):
                log("Фон РКН Тян 2 был сброшен, восстанавливаем", "WARNING")
                self.apply_rkn2_background()
            else:
                log("Фон РКН Тян 2 успешно сохранён", "DEBUG")
        except Exception as e:
            log(f"Ошибка проверки фона РКН Тян 2: {e}", "ERROR")

    def _build_final_css_cache_key(self, theme_name: str) -> str:
        return self.get_clean_theme_name(theme_name)

    def _get_final_css_from_memory_cache(self, cache_key: str) -> str | None:
        if not cache_key:
            return None
        cached = self._final_css_memory_cache.get(cache_key)
        if not cached:
            return None
        self._final_css_memory_cache.move_to_end(cache_key)
        return cached

    def _remember_final_css(self, cache_key: str, final_css: str) -> None:
        if not cache_key or not final_css:
            return
        self._final_css_memory_cache[cache_key] = final_css
        self._final_css_memory_cache.move_to_end(cache_key)
        while len(self._final_css_memory_cache) > self._final_css_cache_max:
            self._final_css_memory_cache.popitem(last=False)

    def apply_theme_async(self, theme_name: str | None = None, *, persist: bool = True,
                          progress_callback=None, done_callback=None) -> None:
        """
        Асинхронно применяет тему (не блокирует UI).
        CSS генерируется в фоновом потоке, применяется в главном.

        Args:
            theme_name: Имя темы (если None, используется текущая)
            persist: Сохранять ли выбор в реестр
            progress_callback: Функция для обновления прогресса (str)
            done_callback: Функция вызываемая после завершения (bool success, str message)
        """
        if theme_name is None:
            theme_name = self.current_theme

        clean = self.get_clean_theme_name(theme_name)

        # Быстрый дедуп одинакового последнего запроса, если он всё ещё в работе.
        if self._latest_requested_theme == clean and self._latest_theme_request_id in self._active_theme_build_jobs:
            log(f"⏭️ Тема '{clean}' уже запрошена, игнорируем дубликат", "DEBUG")
            return

        # Проверка премиум (используем кеш, не блокируем UI)
        if self._is_premium_theme(clean):
            is_available = self._premium_cache[0] if self._premium_cache else False
            if not is_available:
                theme_type = self._get_theme_type_name(clean)
                if _InfoBar:
                    _InfoBar.warning(
                        title=theme_type,
                        content=f"{theme_type} «{clean}» доступна только для подписчиков Zapret Premium.",
                        parent=self.widget,
                        duration=4000
                    )
                self._start_async_premium_check()
                if done_callback:
                    done_callback(False, "need premium")
                return

        try:
            # Пути к кешу (theme file name derived from clean name)
            cache_dir = os.path.join(self.theme_folder or "themes", "cache")
            os.makedirs(cache_dir, exist_ok=True)
            cache_file = os.path.join(cache_dir, f"{clean}.css")

            if progress_callback:
                progress_callback("Подготовка темы...")

            self._theme_request_seq += 1
            request_id = self._theme_request_seq
            self._latest_theme_request_id = request_id
            self._latest_requested_theme = clean
            final_css_cache_key = self._build_final_css_cache_key(clean)

            request_data = {
                'theme_name': clean,
                'persist': persist,
                'done_callback': done_callback,
                'progress_callback': progress_callback,
                'final_css_cache_key': final_css_cache_key,
            }

            cached_final_css = self._get_final_css_from_memory_cache(final_css_cache_key)
            if cached_final_css:
                log(
                    f"⚡ Используем in-memory CSS кэш для темы: {clean} ({final_css_cache_key})",
                    "DEBUG",
                )
                if progress_callback:
                    progress_callback("Применяем тему из памяти...")
                QTimer.singleShot(
                    0,
                    lambda css=cached_final_css, theme=clean, rid=request_id, data=request_data:
                    self._on_theme_css_ready(css, theme, rid, data),
                )
                return

            log(
                f"🎨 Запуск асинхронной подготовки CSS для темы: {clean} (request_id={request_id})",
                "DEBUG",
            )

            thread = QThread()
            worker = ThemeBuildWorker(
                theme_file=f"{clean}.xml",
                theme_name=clean,
                cache_file=cache_file,
                is_amoled=self._is_amoled_theme(clean),
                is_pure_black=self._is_pure_black_theme(clean),
                is_rkn_tyan=(clean == "РКН Тян"),
                is_rkn_tyan_2=(clean == "РКН Тян 2"),
            )
            worker.moveToThread(thread)

            thread.started.connect(worker.run)
            worker.finished.connect(
                lambda final_css, built_theme, rid=request_id, data=request_data:
                self._on_theme_css_ready(final_css, built_theme, rid, data)
            )
            worker.error.connect(
                lambda error, rid=request_id, data=request_data:
                self._on_theme_build_error(error, rid, data)
            )
            if progress_callback:
                worker.progress.connect(
                    lambda status, rid=request_id, cb=progress_callback:
                    (rid == self._latest_theme_request_id) and cb(status)
                )

            # Важно: завершаем поток и при успехе, и при ошибке.
            worker.finished.connect(thread.quit)
            worker.error.connect(thread.quit)
            thread.finished.connect(lambda rid=request_id: self._cleanup_theme_build_thread(rid))

            self._active_theme_build_jobs[request_id] = (thread, worker)
            self._theme_build_thread = thread
            self._theme_build_worker = worker
            thread.start()

        except Exception as e:
            log(f"Ошибка запуска асинхронного применения темы: {e}", "❌ ERROR")
            if done_callback:
                done_callback(False, str(e))

    def _on_theme_css_ready(
        self,
        final_css: str,
        theme_name: str,
        request_id: int | None = None,
        request_data: Optional[dict] = None,
    ):
        """Обработчик готовности CSS (вызывается из главного потока).

        Применяет CSS только для актуального (последнего) запроса.
        """
        done_callback = None
        try:
            data = request_data or {}
            requested_theme = str(data.get('theme_name') or theme_name)
            persist = bool(data.get('persist', True))
            done_callback = data.get('done_callback')
            progress_callback = data.get('progress_callback')

            if request_id is not None and request_id != self._latest_theme_request_id:
                log(
                    f"⏭️ Игнорируем устаревший CSS результат (request_id={request_id}, latest={self._latest_theme_request_id})",
                    "DEBUG",
                )
                return

            cache_key_raw = data.get('final_css_cache_key')
            if isinstance(cache_key_raw, str) and cache_key_raw:
                self._remember_final_css(cache_key_raw, final_css)

            if progress_callback:
                progress_callback("Применяем тему...")

            log(
                f"🎨 CSS готов ({len(final_css)} символов), применяем: {requested_theme} (request_id={request_id})",
                "DEBUG",
            )

            # Применяем готовый CSS - это ЕДИНСТВЕННАЯ синхронная операция!
            self._apply_css_only(final_css, requested_theme, persist)

            if done_callback:
                try:
                    done_callback(True, "ok")
                except Exception as cb_error:
                    log(f"Ошибка в done_callback: {cb_error}", "WARNING")

        except Exception as e:
            log(f"Ошибка применения готового CSS: {e}", "❌ ERROR")
            import traceback
            log(traceback.format_exc(), "DEBUG")

            if done_callback:
                try:
                    done_callback(False, str(e))
                except Exception as cb_error:
                    log(f"Ошибка в error callback: {cb_error}", "WARNING")

    def _on_theme_build_error(
        self,
        error: str,
        request_id: int | None = None,
        request_data: Optional[dict] = None,
    ):
        """Обработчик ошибки генерации CSS"""
        log(f"❌ Ошибка генерации CSS темы: {error}", "ERROR")

        if request_id is not None and request_id != self._latest_theme_request_id:
            log(
                f"⏭️ Игнорируем устаревшую ошибку темы (request_id={request_id}, latest={self._latest_theme_request_id})",
                "DEBUG",
            )
            return

        done_callback = None
        if request_data:
            done_callback = request_data.get('done_callback')
        if done_callback:
            done_callback(False, error)

    def _cleanup_theme_build_thread(self, request_id: int | None = None):
        """Очистка потока генерации CSS по request_id."""
        try:
            ids_to_cleanup = [request_id] if request_id is not None else list(self._active_theme_build_jobs.keys())
            for rid in ids_to_cleanup:
                if rid is None:
                    continue
                job = self._active_theme_build_jobs.pop(rid, None)
                if not job:
                    continue
                thread, worker = job
                try:
                    worker.deleteLater()
                except RuntimeError:
                    pass
                try:
                    thread.deleteLater()
                except RuntimeError:
                    pass

            latest_job = self._active_theme_build_jobs.get(self._latest_theme_request_id)
            if latest_job:
                self._theme_build_thread, self._theme_build_worker = latest_job
            else:
                self._theme_build_thread = None
                self._theme_build_worker = None

        except RuntimeError:
            self._theme_build_worker = None
            self._theme_build_thread = None
    
    def _apply_css_only(self, final_css: str, theme_name: str, persist: bool):
        """Применяет готовый CSS - ЕДИНСТВЕННАЯ синхронная операция.

        CSS уже полностью собран в фоновом потоке.
        Здесь только setStyleSheet() и пост-обработка.
        """
        import time as _time
        from PyQt6.QtWidgets import QApplication

        try:
            # Проверяем что виджеты ещё существуют
            if not self.widget or not self.app:
                log("⚠️ Виджет или приложение удалены, пропускаем применение темы", "WARNING")
                return

            clean = set_active_theme_name(theme_name)

            # Sync qfluentwidgets dark/light mode with the new theme.
            # setTheme(DARK/LIGHT) updates all native qfluentwidgets widgets (ComboBox, etc.).
            _sync_theme_mode_to_qfluent(clean, window=self.widget)

            # Sync qfluentwidgets accent with the new theme (silent — no updateStyleSheet).
            # Invalidate tokens so pages recompute CSS with the correct accent on next StyleChange.
            _sync_theme_accent_to_qfluent(clean)
            invalidate_theme_tokens_cache()

            # Проверяем хеш CSS - не применяем если не изменился
            css_hash = hash(final_css)
            if self._current_css_hash == css_hash and self.current_theme == clean:
                log(f"⏭ CSS не изменился, пропускаем setStyleSheet", "DEBUG")
                return

            base_css, overlay_css = _split_final_css_layers(final_css)
            if not overlay_css:
                overlay_css = final_css

            base_css_hash = hash(base_css) if base_css else None
            overlay_css_hash = hash(overlay_css)

            current_theme_name = str(self.current_theme or "")
            current_special = (
                current_theme_name in ("РКН Тян", "РКН Тян 2")
                or self._is_amoled_theme(current_theme_name)
                or self._is_pure_black_theme(current_theme_name)
            )
            target_special = (
                clean in ("РКН Тян", "РКН Тян 2")
                or self._is_amoled_theme(clean)
                or self._is_pure_black_theme(clean)
            )

            same_luminance = True
            try:
                current_tokens = get_theme_tokens(current_theme_name)
                target_tokens = get_theme_tokens(clean)
                same_luminance = bool(current_tokens.is_light) == bool(target_tokens.is_light)
            except Exception:
                same_luminance = True

            should_apply_base = False
            if base_css and base_css_hash is not None:
                if not self._app_base_initialized:
                    should_apply_base = True
                elif self._current_base_css_hash != base_css_hash:
                    # Fast path: внутри одного светлотного режима обновляем только overlay.
                    # Полный base обновляем только при переключении light<->dark или special-тем.
                    should_apply_base = (not same_luminance) or current_special or target_special

            # Определяем правильный виджет для сброса фона
            target_widget = self.widget
            if hasattr(self.widget, 'main_widget') and self.widget.main_widget:
                target_widget = self.widget.main_widget

            # Сбрасываем фон если это НЕ РКН Тян и НЕ РКН Тян 2
            if clean not in ("РКН Тян", "РКН Тян 2"):
                target_widget.setAutoFillBackground(False)
                target_widget.setProperty("hasCustomBackground", False)

            main_window = self.widget

            # Показываем курсор ожидания
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)

            # ═══════════════════════════════════════════════════════════════
            # ОПТИМИЗАЦИЯ: Скрываем тяжёлые виджеты во время применения CSS
            # Qt быстрее применяет стили к скрытым виджетам
            # ═══════════════════════════════════════════════════════════════
            hidden_widgets = []

            # Скрываем pages_stack (основной контент со всеми страницами)
            if hasattr(main_window, 'pages_stack'):
                pages_stack = main_window.pages_stack
                if pages_stack.isVisible():
                    pages_stack.hide()
                    hidden_widgets.append(pages_stack)

            # Скрываем side_nav (навигация с кнопками)
            if hasattr(main_window, 'side_nav'):
                side_nav = main_window.side_nav
                if side_nav.isVisible():
                    side_nav.hide()
                    hidden_widgets.append(side_nav)

            was_updates_enabled = main_window.updatesEnabled()
            main_window.setUpdatesEnabled(False)

            try:
                _t = _time.perf_counter()
                base_apply_ms = 0.0
                if should_apply_base and base_css:
                    _tb = _time.perf_counter()
                    self.app.setStyleSheet(base_css)
                    base_apply_ms = (_time.perf_counter() - _tb) * 1000
                    self._current_base_css_hash = base_css_hash
                    self._app_base_initialized = True

                # Overlay применяется к основному окну (subtree), это заметно быстрее,
                # чем полная переустановка CSS на QApplication при каждой смене темы.
                _to = _time.perf_counter()
                main_window.setStyleSheet(overlay_css)
                overlay_apply_ms = (_time.perf_counter() - _to) * 1000
                self._current_overlay_css_hash = overlay_css_hash

                # ✅ Сбрасываем палитру чтобы CSS точно применился
                if not self._palette_reset_once_done:
                    from PyQt6.QtGui import QPalette
                    main_window.setPalette(QPalette())
                    self._palette_reset_once_done = True
                    palette_reset_note = " + palette reset"
                else:
                    palette_reset_note = ""

                elapsed_ms = (_time.perf_counter()-_t)*1000
                apply_mode = "base+overlay" if should_apply_base else "overlay-only"
                log(
                    (
                        f"  setStyleSheet took {elapsed_ms:.0f}ms "
                        f"({apply_mode}, base={base_apply_ms:.0f}ms, overlay={overlay_apply_ms:.0f}ms{palette_reset_note})"
                    ),
                    "DEBUG",
                )
                note_theme_css_apply_duration(elapsed_ms)
            finally:
                main_window.setUpdatesEnabled(was_updates_enabled)
                # Возвращаем видимость скрытых виджетов
                for widget in hidden_widgets:
                    widget.show()
                # Восстанавливаем курсор
                QApplication.restoreOverrideCursor()
            
            # ⚠️ НЕ обновляем стили здесь - это делается в main.py после показа окна
            # Обновление до показа окна не эффективно для невидимых виджетов
            
            # Сохраняем хеш примененного CSS
            self._current_css_hash = css_hash
            self._theme_applied = True
            
            if persist:
                result = set_selected_theme(clean)
                log(f"💾 Тема сохранена в реестр: '{clean}' -> {result}", "DEBUG")
            else:
                log(f"⏭️ Тема НЕ сохранена в реестр (persist=False): '{clean}'", "DEBUG")
            self.current_theme = clean
            
            # Обновление заголовка (отложенно) - используем слабую ссылку
            try:
                import weakref
                weak_self = weakref.ref(self)
                QTimer.singleShot(10, lambda: weak_self() and weak_self()._update_title_async(clean))
            except Exception as e:
                log(f"Ошибка отложенного обновления заголовка: {e}", "DEBUG")
            
            # Фон РКН Тян / РКН Тян 2 - используем слабую ссылку
            if clean == "РКН Тян":
                try:
                    import weakref
                    weak_self = weakref.ref(self)
                    QTimer.singleShot(50, lambda: weak_self() and weak_self()._apply_rkn_with_protection())
                except Exception as e:
                    log(f"Ошибка отложенного применения фона РКН Тян: {e}", "DEBUG")
            elif clean == "РКН Тян 2":
                try:
                    import weakref
                    weak_self = weakref.ref(self)
                    QTimer.singleShot(50, lambda: weak_self() and weak_self()._apply_rkn2_with_protection())
                except Exception as e:
                    log(f"Ошибка отложенного применения фона РКН Тян 2: {e}", "DEBUG")
                
        except Exception as e:
            log(f"Ошибка в _apply_css_only: {e}", "❌ ERROR")

    def apply_rkn_background(self):
        """Применяет фоновое изображение для темы РКН Тян"""
        try:
            # ✅ ИСПРАВЛЕНИЕ: Определяем правильный виджет для применения фона
            target_widget = self.widget
            
            # Если widget имеет main_widget, применяем к нему
            if hasattr(self.widget, 'main_widget'):
                target_widget = self.widget.main_widget
                log("Применяем фон РКН Тян к main_widget", "DEBUG")
            else:
                log("Применяем фон РКН Тян к основному виджету", "DEBUG")
            
            img_path = os.path.join(self.theme_folder or THEME_FOLDER, "rkn_tyan", "rkn_background.jpg")
            
            if not os.path.exists(img_path):
                log(f"Фон РКН Тян не найден по пути: {img_path}", "WARNING")
                return False

            if os.path.exists(img_path):
                pixmap = QPixmap(img_path)
                if not pixmap.isNull():
                    # Помечаем виджет
                    target_widget.setProperty("hasCustomBackground", True)
                    
                    # Устанавливаем палитру для target_widget
                    palette = target_widget.palette()
                    brush = QBrush(pixmap.scaled(
                        target_widget.size(),
                        Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                        Qt.TransformationMode.SmoothTransformation
                    ))
                    palette.setBrush(QPalette.ColorRole.Window, brush)
                    target_widget.setPalette(palette)
                    target_widget.setAutoFillBackground(True)
                    
                    # Защитный стиль
                    widget_style = """
                    QWidget {
                        background: transparent !important;
                    }
                    """
                    existing_style = target_widget.styleSheet()
                    if "background: transparent" not in existing_style:
                        target_widget.setStyleSheet(existing_style + widget_style)
                    
                    log(f"Фон РКН Тян успешно установлен на {target_widget.__class__.__name__}", "INFO")
                    return True
                    
        except Exception as e:
            log(f"Ошибка при применении фона РКН Тян: {str(e)}", "❌ ERROR")
        
        return False

    def apply_rkn2_background(self):
        """Применяет фоновое изображение для темы РКН Тян 2"""
        try:
            # Определяем правильный виджет для применения фона
            target_widget = self.widget
            
            # Если widget имеет main_widget, применяем к нему
            if hasattr(self.widget, 'main_widget'):
                target_widget = self.widget.main_widget
                log("Применяем фон РКН Тян 2 к main_widget", "DEBUG")
            else:
                log("Применяем фон РКН Тян 2 к основному виджету", "DEBUG")
            
            img_path = os.path.join(self.theme_folder or THEME_FOLDER, "rkn_tyan_2", "rkn_background_2.jpg")
            
            if not os.path.exists(img_path):
                log(f"Фон РКН Тян 2 не найден по пути: {img_path}", "WARNING")
                return False

            if os.path.exists(img_path):
                pixmap = QPixmap(img_path)
                if not pixmap.isNull():
                    # Помечаем виджет
                    target_widget.setProperty("hasCustomBackground", True)
                    
                    # Устанавливаем палитру для target_widget
                    palette = target_widget.palette()
                    brush = QBrush(pixmap.scaled(
                        target_widget.size(),
                        Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                        Qt.TransformationMode.SmoothTransformation
                    ))
                    palette.setBrush(QPalette.ColorRole.Window, brush)
                    target_widget.setPalette(palette)
                    target_widget.setAutoFillBackground(True)
                    
                    # Защитный стиль
                    widget_style = """
                    QWidget {
                        background: transparent !important;
                    }
                    """
                    existing_style = target_widget.styleSheet()
                    if "background: transparent" not in existing_style:
                        target_widget.setStyleSheet(existing_style + widget_style)
                    
                    log(f"Фон РКН Тян 2 успешно установлен на {target_widget.__class__.__name__}", "INFO")
                    return True
                    
        except Exception as e:
            log(f"Ошибка при применении фона РКН Тян 2: {str(e)}", "❌ ERROR")
        
        return False

    def _update_title_async(self, current_theme):
        """Асинхронно обновляет заголовок окна"""
        try:
            # Используем кешированный результат если есть
            if self._premium_cache and hasattr(self.widget, "update_title_with_subscription_status"):
                is_premium, message, days = self._premium_cache
                self.widget.update_title_with_subscription_status(is_premium, current_theme, days)
            else:
                # Показываем FREE статус и запускаем асинхронную проверку
                if hasattr(self.widget, "update_title_with_subscription_status"):
                    self.widget.update_title_with_subscription_status(False, current_theme, None)
                # Запускаем асинхронную проверку
                self._start_async_premium_check()
                
        except Exception as e:
            log(f"Ошибка обновления заголовка: {e}", "❌ ERROR")

    def _get_theme_type_name(self, theme_name: str) -> str:
        """Возвращает красивое название типа темы"""
        if theme_name.startswith("AMOLED"):
            return "AMOLED тема"
        elif theme_name == "Полностью черная":
            return "Pure Black тема"
        elif theme_name in ("РКН Тян", "РКН Тян 2"):
            return "Премиум-тема"
        else:
            return "Премиум-тема"

    def _apply_pure_black_enhancements_inline(self):
        """Возвращает CSS для улучшений полностью черной темы (для inline применения)"""
        # Применяется через combined_style в apply_theme
        pass

    def apply_pure_black_enhancements(self):
        """Применяет дополнительные улучшения для полностью черной темы (legacy)"""
        try:
            additional_style = self._get_pure_black_enhancement_css()
            current_style = self.app.styleSheet()
            self.app.setStyleSheet(current_style + additional_style)
            log("Pure Black улучшения применены", "DEBUG")
        except Exception as e:
            log(f"Ошибка при применении Pure Black улучшений: {e}", "DEBUG")
    
    def _get_pure_black_enhancement_css(self) -> str:
        """Возвращает CSS улучшений для Pure Black темы"""
        return """
            QFrame[frameShape="4"] {
                color: #1a1a1a;
            }
            QPushButton:focus {
                border: 2px solid rgba(255, 255, 255, 0.2);
            }
            QComboBox:focus {
                border: 2px solid rgba(255, 255, 255, 0.2);
            }
            QLabel[objectName="title_label"] {
                text-shadow: 0px 0px 5px rgba(255, 255, 255, 0.1);
            }
            """


    def _apply_amoled_enhancements_inline(self):
        """Возвращает CSS для улучшений AMOLED темы (для inline применения)"""
        # Применяется через combined_style в apply_theme
        pass

    def apply_amoled_enhancements(self):
        """Применяет дополнительные улучшения для AMOLED тем (legacy)"""
        try:
            additional_style = self._get_amoled_enhancement_css()
            current_style = self.app.styleSheet()
            self.app.setStyleSheet(current_style + additional_style)
            log("AMOLED улучшения применены", "DEBUG")
        except Exception as e:
            log(f"Ошибка при применении AMOLED улучшений: {e}", "DEBUG")
    
    def _get_amoled_enhancement_css(self) -> str:
        """Возвращает CSS улучшений для AMOLED темы"""
        return """
            /* Убираем все лишние рамки */
            QFrame {
                border: none;
            }
            /* Рамка только при наведении на кнопки */
            QPushButton:hover {
                border: 1px solid rgba(255, 255, 255, 0.1);
            }
            /* Убираем text-shadow который создает размытие */
            QLabel {
                text-shadow: none;
            }
            /* Фокус на комбобоксе */
            QComboBox:focus {
                border: 1px solid rgba(255, 255, 255, 0.3);
            }
            /* Только горизонтальные линии оставляем видимыми */
            QFrame[frameShape="4"] {
                color: #222222;
                max-height: 1px;
                border: none;
            }
            /* Убираем отступы где возможно */
            QWidget {
                outline: none;
            }
            /* Компактные отступы для контейнеров */
            QStackedWidget {
                margin: 0;
                padding: 0;
            }
            """

    def _update_color_in_style(self, current_style, new_color):
        """Обновляет цвет в существующем стиле"""
        import re
        if 'color:' in current_style:
            updated_style = re.sub(r'color:\s*[^;]+;', f'color: {new_color};', current_style)
        else:
            updated_style = current_style + f' color: {new_color};'
        return updated_style
    
    def _set_status(self, text):
        """Устанавливает текст статуса (через главное окно)"""
        if hasattr(self.widget, 'set_status'):
            self.widget.set_status(text)


class ThemeHandler:
    def __init__(self, app_instance, target_widget=None):
        self.app = app_instance
        self.app_window = app_instance
        self.target_widget = target_widget if target_widget else app_instance
        self.theme_manager = None  # Будет установлен позже

    def set_theme_manager(self, theme_manager):
        """Устанавливает theme_manager после его создания"""
        self.theme_manager = theme_manager
        log("ThemeManager установлен в ThemeHandler", "DEBUG")

    
    def apply_theme_background(self, theme_name):
        """Применяет фон для темы"""
        # Применяем к target_widget, а не к self.app
        widget_to_style = self.target_widget
        
        if theme_name == "РКН Тян":
            # Применяем фон именно к target_widget
            if self.theme_manager and hasattr(self.theme_manager, 'apply_rkn_background'):
                self.theme_manager.apply_rkn_background()
                log(f"Фон РКН Тян применен через theme_manager", "INFO")
            else:
                log("theme_manager не доступен для применения фона РКН Тян", "WARNING")
        elif theme_name == "РКН Тян 2":
            # Применяем фон РКН Тян 2
            if self.theme_manager and hasattr(self.theme_manager, 'apply_rkn2_background'):
                self.theme_manager.apply_rkn2_background()
                log(f"Фон РКН Тян 2 применен через theme_manager", "INFO")
            else:
                log("theme_manager не доступен для применения фона РКН Тян 2", "WARNING")

    def update_subscription_status_in_title(self):
        """Обновляет статус подписки в title_label"""
        try:
            # Проверяем наличие необходимых компонентов
            if not hasattr(self.app_window, 'donate_checker') or not self.app_window.donate_checker:
                log("donate_checker не инициализирован", "⚠ WARNING")
                return
            
            if not self.theme_manager:
                log("theme_manager не инициализирован", "⚠ WARNING")
                return

            # Используем кэшированные данные для быстрого обновления
            donate_checker = self.app_window.donate_checker
            is_premium, status_msg, days_remaining = donate_checker.check_subscription_status(use_cache=True)
            current_theme = self.theme_manager.current_theme if self.theme_manager else None
            
            # Получаем полную информацию о подписке
            sub_info = donate_checker.get_full_subscription_info(use_cache=True)
            
            # Обновляем заголовок
            self.app_window.update_title_with_subscription_status(
                sub_info['is_premium'], 
                current_theme, 
                sub_info['days_remaining']
            )
            
            # Также обновляем текст кнопки подписки если нужно
            if hasattr(self.app_window, 'update_subscription_button_text'):
                self.app_window.update_subscription_button_text(
                    sub_info['is_premium'],
                    sub_info['days_remaining']
                )
            
            log(f"Заголовок обновлен для темы '{current_theme}'", "DEBUG")
            
        except Exception as e:
            log(f"Ошибка при обновлении статуса подписки: {e}", "❌ ERROR")
            # В случае ошибки показываем базовый заголовок
            try:
                self.app_window.update_title_with_subscription_status(False, None, 0)
            except:
                pass  # Игнорируем вторичные ошибки
    
    def change_theme(self, theme_name):
        """Обработчик изменения темы (асинхронная версия - не блокирует UI)"""
        try:
            if not self.theme_manager:
                self.theme_manager = getattr(self.app_window, 'theme_manager', None)
                if not self.theme_manager:
                    return
            
            clean_theme_name = self.theme_manager.get_clean_theme_name(theme_name)
            click_started_at = None
            try:
                appearance_page = getattr(self.app_window, 'appearance_page', None)
                if appearance_page is not None:
                    clicked_theme = getattr(appearance_page, '_last_theme_click_theme', None)
                    clicked_at = getattr(appearance_page, '_last_theme_click_started_at', None)
                    if clicked_theme in (theme_name, clean_theme_name) and isinstance(clicked_at, (int, float)):
                        click_started_at = float(clicked_at)
                    appearance_page._last_theme_click_theme = None
                    appearance_page._last_theme_click_started_at = None
            except Exception:
                click_started_at = None

            switch_metrics_id = start_theme_switch_metrics(
                clean_theme_name,
                source="ThemeHandler.change_theme",
                click_started_at=click_started_at,
            )
            
            # Показываем статус
            if hasattr(self.app_window, 'set_status'):
                self.app_window.set_status("🎨 Применяем тему...")
            
            # Применяем тему АСИНХРОННО (не блокирует UI!)
            self.theme_manager.apply_theme_async(
                clean_theme_name,
                persist=True,
                progress_callback=self._on_theme_progress,
                done_callback=lambda success, msg: self._on_theme_change_done(
                    success,
                    msg,
                    theme_name,
                    switch_metrics_id,
                )
            )
                
        except Exception as e:
            log(f"Ошибка смены темы: {e}", "ERROR")
    
    def _on_theme_progress(self, status: str):
        """Обработчик прогресса смены темы"""
        if hasattr(self.app_window, 'set_status'):
            self.app_window.set_status(f"🎨 {status}")
    
    def _on_theme_change_done(
        self,
        success: bool,
        message: str,
        theme_name: str,
        switch_metrics_id: int | None = None,
    ):
        """Обработчик завершения смены темы"""
        try:
            if not success:
                log(f"Ошибка смены темы: {message}", "WARNING")
                # Возвращаем выбор на текущую тему в галерее
                if hasattr(self.app_window, 'appearance_page') and self.theme_manager:
                    self.app_window.appearance_page.set_current_theme(self.theme_manager.current_theme)
                if hasattr(self.app_window, 'set_status'):
                    self.app_window.set_status(f"⚠ {message}")
                finish_theme_switch_metrics(
                    switch_metrics_id,
                    success=False,
                    message=message,
                    theme_name=theme_name,
                )
                return
            
            # Успех - обновляем UI
            if hasattr(self.app_window, 'set_status'):
                self.app_window.set_status("✅ Тема применена")
            
            # Отложенное обновление UI
            QTimer.singleShot(
                100,
                lambda: self._post_theme_change_update(theme_name, switch_metrics_id, message),
            )
                
        except Exception as e:
            log(f"Ошибка в _on_theme_change_done: {e}", "ERROR")
            finish_theme_switch_metrics(
                switch_metrics_id,
                success=False,
                message=str(e),
                theme_name=theme_name,
            )
    
    def _post_theme_change_update(
        self,
        theme_name: str,
        switch_metrics_id: int | None = None,
        completion_message: str = "ok",
    ):
        """Выполняет все обновления UI после смены темы за один раз"""
        try:
            # Обновляем выбранную тему в галерее
            if hasattr(self.app_window, 'appearance_page'):
                self.app_window.appearance_page.set_current_theme(theme_name)
            
            # Обновляем цвета кастомного titlebar
            self._update_titlebar_theme(theme_name)
            
            # Обновляем статус подписки
            self.update_subscription_status_in_title()
            finish_theme_switch_metrics(
                switch_metrics_id,
                success=True,
                message=completion_message,
                theme_name=theme_name,
            )
        except Exception as e:
            log(f"Ошибка в _post_theme_change_update: {e}", "DEBUG")
            finish_theme_switch_metrics(
                switch_metrics_id,
                success=False,
                message=str(e),
                theme_name=theme_name,
            )

    def _update_titlebar_theme(self, theme_name: str):
        """Обновляет цвета кастомного titlebar в соответствии с темой"""
        try:
            if not hasattr(self.app_window, 'title_bar'):
                return
            
            if not hasattr(self.app_window, 'container'):
                return
            
            clean_name = self.theme_manager.get_clean_theme_name(theme_name) if self.theme_manager else theme_name

            # Centralized tokens (colors + typography)
            tokens = get_theme_tokens(clean_name)

            # Получаем цвет фона из конфигурации темы
            theme_bg = get_theme_bg_color(clean_name)
            theme_content_bg = get_theme_content_bg_color(clean_name)

            base_alpha = 255
            border_alpha = 255
            container_opacity = 255
            container_opacity_light = 255
            container_opacity_amoled = 255

            # Определяем цвета в зависимости от темы
            is_light = "Светлая" in clean_name
            is_amoled = "AMOLED" in clean_name or clean_name == "Полностью черная"

            if is_amoled:
                # AMOLED и полностью черная тема
                bg_color = f"rgba(0, 0, 0, {base_alpha})"
                text_color = "#ffffff"
                container_bg = f"rgba(0, 0, 0, {container_opacity_amoled})"
                border_color = f"rgba(30, 30, 30, {border_alpha})"
                menubar_bg = f"rgba(0, 0, 0, {base_alpha})"
                menu_text = "#ffffff"
                hover_bg = "#222222"
                menu_dropdown_bg = f"rgba(10, 10, 10, {base_alpha})"
            elif is_light:
                # Светлые темы - используем цвет из конфига
                bg_color = f"rgba({theme_bg}, {base_alpha})"
                text_color = "#000000"
                container_bg = f"rgba({theme_content_bg}, {container_opacity_light})"
                border_color = f"rgba(200, 200, 200, {border_alpha})"
                menubar_bg = f"rgba({theme_bg}, {base_alpha})"
                menu_text = "#000000"
                hover_bg = "#d0d0d0"
                menu_dropdown_bg = f"rgba({theme_content_bg}, {base_alpha})"
            else:
                # Темные темы - используем цвет фона из конфига темы
                bg_color = f"rgba({theme_bg}, {base_alpha})"
                text_color = "#ffffff"
                container_bg = f"rgba({theme_bg}, {container_opacity})"
                border_color = f"rgba(80, 80, 80, {border_alpha})"
                menubar_bg = f"rgba({theme_bg}, {base_alpha})"
                menu_text = "#ffffff"
                # Рассчитываем hover_bg как более светлый оттенок
                try:
                    r, g, b = [int(x.strip()) for x in theme_bg.split(',')]
                    hover_r = min(255, r + 20)
                    hover_g = min(255, g + 20)
                    hover_b = min(255, b + 20)
                    hover_bg = f"rgb({hover_r}, {hover_g}, {hover_b})"
                except:
                    hover_bg = "#333333"
                menu_dropdown_bg = f"rgba({theme_content_bg}, {base_alpha})"
            
            # Обновляем titlebar
            self.app_window.title_bar.set_theme_colors(bg_color, text_color)
            
            # Обновляем контейнер
            self.app_window.container.setStyleSheet(f"""
                QFrame#mainContainer {{
                    background-color: {container_bg};
                    border-radius: 10px;
                    border: 1px solid {border_color};
                }}
            """)
            
            # Обновляем область контента (если есть)
            if hasattr(self.app_window, 'main_widget'):
                content_area = self.app_window.main_widget.findChild(QWidget, "contentArea")
                if content_area:
                    content_area.setStyleSheet(f"""
                        QWidget#contentArea {{
                            background-color: rgba({theme_content_bg}, 0.75);
                            border-top-right-radius: 10px;
                            border-bottom-right-radius: 10px;
                        }}
                    """)
            
            # Обновляем стиль menubar если есть
            if hasattr(self.app_window, 'menubar_widget'):
                self.app_window.menubar_widget.setStyleSheet(f"""
                    QWidget#menubarWidget {{
                        background-color: {menubar_bg};
                        border-bottom: 1px solid {border_color};
                    }}
                """)
                
                # Обновляем стиль самого меню
                if hasattr(self.app_window, 'menu_bar'):
                    self.app_window.menu_bar.setStyleSheet(f"""
                        QMenuBar {{
                            background-color: transparent;
                            color: {menu_text};
                            border: none;
                            font-size: 11px;
                            font-family: {tokens.font_family_qss};
                        }}
                        QMenuBar::item {{
                            background-color: transparent;
                            color: {menu_text};
                            padding: 4px 10px;
                            border-radius: 4px;
                            margin: 2px 1px;
                        }}
                        QMenuBar::item:selected {{
                            background-color: {hover_bg};
                        }}
                        QMenu {{
                            background-color: {menu_dropdown_bg};
                            border: 1px solid {border_color};
                            border-radius: 6px;
                            padding: 4px;
                        }}
                        QMenu::item {{
                            padding: 6px 24px 6px 12px;
                            border-radius: 4px;
                            color: {menu_text};
                        }}
                        QMenu::item:selected {{
                            background-color: {hover_bg};
                        }}
                        QMenu::separator {{
                            height: 1px;
                            background-color: {border_color};
                            margin: 4px 8px;
                        }}
                    """)
            
            log(f"Цвета titlebar обновлены для темы: {clean_name}", "DEBUG")
            
        except Exception as e:
            log(f"Ошибка обновления titlebar: {e}", "DEBUG")

    def update_theme_gallery(self):
        """Обновляет галерею тем на странице оформления"""
        if not hasattr(self.app_window, 'appearance_page'):
            log("appearance_page не найден в app_window", "DEBUG")
            return
        
        # Проверяем theme_manager
        if not self.theme_manager:
            if hasattr(self.app_window, 'theme_manager'):
                self.theme_manager = self.app_window.theme_manager
            else:
                log("theme_manager не доступен", "DEBUG")
                return
        
        try:
            # Обновляем премиум статус
            is_premium = False
            if self.theme_manager._premium_cache:
                is_premium = self.theme_manager._premium_cache[0]
            
            self.app_window.appearance_page.set_premium_status(is_premium)
            
            # Обновляем текущую тему
            current_theme = self.theme_manager.current_theme
            self.app_window.appearance_page.set_current_theme(current_theme)
            
            log("Галерея тем обновлена", "DEBUG")
        except Exception as e:
            log(f"Ошибка обновления галереи тем: {e}", "❌ ERROR")

    def update_available_themes(self):
        """Обновляет галерею тем (для совместимости)"""
        self.update_theme_gallery()
