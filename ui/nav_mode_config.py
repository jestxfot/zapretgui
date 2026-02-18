# ui/nav_mode_config.py
"""Mode-based navigation visibility configuration.

Single source of truth for which pages are visible in the sidebar
per launch method. Import and use get_nav_visibility(method) in
_sync_nav_visibility() instead of a hardcoded targets dict.

Adding a new mode-specific page:
  1. Add the rule to get_nav_visibility() below.
  2. Add _add(PageName.YOUR_PAGE) to _init_navigation() in main_window.py
     (right after CONTROL/ZAPRET2_DIRECT_CONTROL block).
  3. Add icon + label to _NAV_ICONS / _NAV_LABELS in main_window.py.
"""

from ui.page_names import PageName


def get_nav_visibility(method: str) -> dict[PageName, bool]:
    """Return {PageName: should_be_visible} for the given launch method.

    All pages listed here must be present in _nav_items (added via _add()
    in _init_navigation). Pages absent from the dict are not touched.
    """
    m = (method or "").strip().lower()

    is_direct_zapret2          = m == "direct_zapret2"
    is_direct_zapret2_orchestra = m == "direct_zapret2_orchestra"
    is_direct_zapret1          = m == "direct_zapret1"
    is_bat                     = m == "bat"
    is_pure_orchestra          = m == "orchestra"

    # "orchestra" in a broad sense: any mode that uses the orchestra runner
    is_any_orchestra = is_direct_zapret2_orchestra or is_pure_orchestra

    # zapret2 family (direct or orchestra variant)
    is_zapret2_family = is_direct_zapret2 or is_direct_zapret2_orchestra

    return {
        # ── Верх: "Управление" vs "Стратегии" (direct_zapret2 entry point) ───
        PageName.CONTROL:                  not is_direct_zapret2,
        PageName.ZAPRET2_DIRECT_CONTROL:   is_direct_zapret2,

        # ── Strategy entry-point pages (one visible at a time) ───────────────
        PageName.ORCHESTRA:                is_pure_orchestra,
        PageName.ZAPRET2_ORCHESTRA:        is_direct_zapret2_orchestra,
        PageName.ZAPRET1_DIRECT:           is_direct_zapret1,
        PageName.BAT_STRATEGIES:           is_bat,

        # ── Zapret2 sub-section ──────────────────────────────────────────────
        PageName.PRESET_CONFIG:            is_zapret2_family,

        # Subpages navigated to via buttons — never in sidebar
        PageName.ZAPRET2_USER_PRESETS:     False,
        PageName.ZAPRET2_DIRECT:           False,

        # ── Orchestra sub-pages ───────────────────────────────────────────────
        PageName.ORCHESTRA_LOCKED:         is_any_orchestra,
        PageName.ORCHESTRA_BLOCKED:        is_any_orchestra,
        PageName.ORCHESTRA_RATINGS:        is_any_orchestra,
        PageName.ORCHESTRA_WHITELIST:      is_any_orchestra,
    }
