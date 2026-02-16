# Theme Refactor Master Plan

Last update: 2026-02-16

## Goal

Bring all GUI pages/widgets to a consistent token-based theme system (`ui/theme.py:get_theme_tokens()`), keep light/dark themes readable, and prevent `changeEvent -> setStyleSheet/setIcon -> changeEvent` recursion.

## Definition Of Done

Refactoring is considered complete when all conditions are true:

1. No critical hardcoded theme colors remain in target UI code (`#fff/#ffffff`, `rgba(255,255,255,...)`, `#60cdff`) except explicitly allowed cases.
2. Pages/widgets with custom inline styles are theme-safe:
   - debounced refresh (`QTimer.singleShot(0, ...)`) on `StyleChange/PaletteChange`;
   - reentrancy guard (`_applying_theme_styles`);
   - optional QSS caching to avoid unnecessary `setStyleSheet` loops.
3. Step 2 semantic colors are centralized (small shared module/constants), not duplicated across pages.
4. Step 3 sidebar is fully tokenized and updates cleanly on theme switch.
5. Verification passes:
   - `python -m compileall -q ...`
   - offscreen smoke: `LupiDPIApp()._build_main_ui()`

## Allowed Temporary Exceptions

- Contrast helpers tied to light/dark (`selection_fg`, light popup backgrounds) are allowed.
- Semantic colors (`success/warn/error`) may stay hardcoded only until Step 2 is completed.

## Current Progress

### Step 1: Page-By-Page Token Unification

- [x] `ui/pages/blobs_page.py`
- [x] `ui/pages/orchestra_blocked_page.py`
- [x] `ui/pages/orchestra_locked_page.py`
- [x] `ui/pages/orchestra_ratings_page.py`
- [x] `ui/pages/orchestra_whitelist_page.py`
- [x] `ui/pages/orchestra_page.py` (high priority)
- [x] `ui/pages/zapret2_orchestra_strategies_page.py` (high priority)
- [x] `ui/pages/network_page.py`
- [x] `ui/pages/my_categories_page.py`
- [x] `ui/pages/editor_page.py`
- [x] `ui/pages/custom_ipset_page.py`
- [x] `ui/pages/dpi_settings_page.py`
- [x] `ui/pages/netrogat_page.py`
- [x] `ui/pages/about_page.py`

Step 1 extension backlog (newly identified secondary pages):

- [x] `ui/pages/hostlist_page.py`
- [x] `ui/pages/help_page.py`
- [x] `ui/pages/preset_config_page.py`
- [x] `ui/pages/strategy_sort_page.py`
- [x] `ui/pages/dns_check_page.py`
- [x] `ui/pages/ipset_page.py`
- [x] `ui/pages/bat_strategies_page.py`
- [x] `ui/pages/zapret1_direct_strategies_page.py`
- [x] `ui/pages/zapret2/direct_zapret2_page.py`
- [x] `ui/pages/blockcheck_page.py`

Global audit backlog (next tranche candidates):

- [x] `ui/pages/hosts_page.py`
- [x] `ui/pages/strategies_page_base.py`
- [x] `ui/pages/autostart_page.py`
- [x] `ui/pages/support_page.py`
- [x] `ui/pages/connection_page.py`

Late audit (files likely still not fully on new engine):

- [x] `ui/pages/base_page.py` (tokenized base typography + theme refresh scaffold)

Residual hardcoded-pattern audit (tokenized pages, lower priority cleanup):

- [x] `ui/pages/home_page.py`
- [x] `ui/pages/servers_page.py`
- [x] `ui/pages/logs_page.py`
- [x] `ui/pages/presets_page.py`
- [x] `ui/pages/control_page.py`
- [x] `ui/pages/custom_domains_page.py`
- [x] `ui/pages/zapret2/strategy_detail_page.py`
- [x] `ui/pages/zapret2/user_presets_page.py`

Support helpers (theme consistency):

- [x] `ui/theme_subscription_manager.py` (FREE/PREMIUM indicator colors now based on `get_theme_tokens()`)

### Step 2: Semantic Palette Extraction

- [x] Create small shared semantic color module/constants (`success`, `warning`, `error`, `info`).
- [x] Refactor pages/widgets to consume semantic constants instead of duplicated literals.
- [x] Validate that semantic colors remain readable in light and dark themes.

Step 2 adoption progress:

- [x] `ui/pages/hosts_page.py` (status/warning/error/danger button semantics)
- [x] `ui/pages/autostart_page.py` (success badge/active state/status icon semantics)
- [x] `ui/pages/support_page.py` (ZapretHub install/open status colors now use semantic palette)
- [x] `ui/pages/strategies_page_base.py` (success indicator + warning favorites badge use semantic palette)
- [x] `ui/pages/premium_page.py` (subscription status/activation/server semantic tones centralized)

### Step 3: Sidebar Full Token Unification

- [x] Replace remaining hardcoded neutrals in `ui/sidebar.py` (including `PulsingDot`, `StatusIndicator`, misc icon neutrals).
- [x] Ensure sidebar icons/status indicators refresh correctly on theme switch.
- [x] Verify no recursive refresh behavior in sidebar controls.

### Step 4: Core UI Shells And Widgets Audit

- [x] `ui/close_dialog.py` (migrated dialogs to token/semantic palette and removed critical hardcoded literals)
- [x] `ui/custom_titlebar.py` (removed residual hardcoded white neutrals and switched resize-handle accent highlight to tokens)
- [x] `ui/fluent_icons.py` (removed legacy fixed accent/default white literals)
- [x] `ui/widgets/win11_spinner.py` (default spinner color now token accent with safe fallback)
- [x] `ui/widgets/notification_banner.py` (info/accent and close-button icon neutrals token-safe)
- [x] `ui/widgets/strategy_search_bar.py` (dark-mode foreground/hover/clear controls moved off hardcoded `#ffffff`/`rgba(255,...)`)
- [x] `ui/widgets/strategy_radio_item.py` (badge text color moved off hardcoded white literal)
- [x] `ui/widgets/direct_zapret2_strategies_tree.py` (multisplit icon accent now token-driven; dialog text neutrals token-safe)
- [x] `ui/widgets/unified_strategies_list.py` (registered in token engine path for stylesheet-bearing widget audit)
- [x] `ui/widgets/strategies_tooltip.py` (removed residual hardcoded white variants in separators/text/gradient borders)
- [x] `ui/widgets/line_edit_icons.py` (clear-button icon/hover/pressed dark-theme neutrals moved off `rgba(255,...)`)
- [x] `ui/widgets/filter_chip_button.py` (legacy hardcoded-color style docs replaced with token semantics to keep audits clean)
- [x] `ui/widgets/collapsible_group.py` (fallback divider neutral moved off `rgba(255,...)`)
- [x] `ui/pages/zapret2/direct_control_page.py` (accent foreground contrast helper moved off hardcoded white variant)
- [x] `ui/pages/orchestra_page.py` (menu/log popup light/dark residual white literals removed)
- [x] `ui/pages/orchestra_blocked_page.py` (popup and selection foreground residual white literals removed)
- [x] `ui/pages/orchestra_locked_page.py` (popup and selection foreground residual white literals removed)
- [x] `ui/pages/orchestra_ratings_page.py` (selection/editor residual white literals removed)
- [x] `ui/pages/blobs_page.py` (dialog popup and accent button foreground residual white literals removed)

## Work Cadence (How We Execute)

For each tranche:

1. Pick 1-3 files from Step 1 backlog (priority: orchestra-related first).
2. Convert styles to tokens and add debounce/guards where needed.
3. Run verification commands.
4. Mark tasks in this plan as done and append a short progress log entry.
5. If new sub-work appears, add it to this plan immediately (do not leave it implicit).

## Verification Commands

```bash
python -m compileall -q ui/pages ui/sidebar.py ui/theme.py
python -c "import os; os.environ.setdefault('QT_QPA_PLATFORM','offscreen'); from PyQt6.QtWidgets import QApplication; app=QApplication([]); from main import LupiDPIApp; w=LupiDPIApp(); w._build_main_ui(); print('ok')"
```

## Progress Log

- 2026-02-16: Step 1 tranche A completed for `blobs_page.py` and orchestra subpages (`blocked/locked/ratings/whitelist`), with tokenization + theme refresh safety patterns.
- 2026-02-16: Step 1 tranche B (part 1) completed for `orchestra_page.py`: tokenized high-visibility styles, added debounced theme refresh guards, verified via `compileall` + offscreen UI smoke.
- 2026-02-16: Step 1 tranche B (part 2) completed for `zapret2_orchestra_strategies_page.py`: removed remaining `#60cdff/#ffffff/rgba(255...)` hardcodes in target sections, verified via `compileall` + offscreen UI smoke.
- 2026-02-16: Step 1 tranche C (part 1) completed for `my_categories_page.py`: tokenized list/input/row/button neutrals + accent states with `get_theme_tokens()`, reduced white/accent hardcodes to semantic danger-only cases.
- 2026-02-16: Step 1 tranche C (part 2) completed for `editor_page.py`: tokenized combo/search/table/form/status styles and user-row accent foreground via `get_theme_tokens()`, verified via `py_compile` + offscreen UI smoke.
- 2026-02-16: Step 1 tranche C (part 3) completed for `network_page.py`: tokenized DNS/provider/adapter/loading/force-DNS styles, removed legacy hardcoded radio style, and switched selection indicators/cards to token-based style builders.
- 2026-02-16: Support helper refactor: `ui/theme_subscription_manager.py` switched FREE/PREMIUM indicator colors from theme-name/hardcoded logic to token-based resolution via `get_theme_tokens()`.
- 2026-02-16: Step 1 tranche D completed for `custom_ipset_page.py`, `netrogat_page.py`, `about_page.py`: replaced remaining neutral/accent hardcoded styles with `get_theme_tokens()` across inputs/editors/cards/status labels/icons; verified via `py_compile` + offscreen UI smoke.
- 2026-02-16: Step 1 tranche E completed for `dpi_settings_page.py`: removed remaining hardcoded neutral/accent values in custom controls (toggle/radio/combo/default icon accents), switched to token-driven colors, and verified via `py_compile` + offscreen UI smoke.
- 2026-02-16: Step 1 tranche F started (extension backlog): tokenized `hostlist_page.py` neutrals/accent labels/icons with `get_theme_tokens()` and added secondary-page backlog (`help/preset_config/strategy_sort`) for continued cleanup.
- 2026-02-16: Step 1 tranche F (part 2) completed for `strategy_sort_page.py`: replaced hardcoded toggle/section colors with token-driven active/inactive styles and tokenized typography colors.
- 2026-02-16: Step 1 tranche F (part 3) completed for `preset_config_page.py` and `help_page.py`: tokenized editor/button/link/motto/card neutrals and accent colors via `get_theme_tokens()`; verified with `py_compile` + offscreen UI smoke.
- 2026-02-16: Step 1 tranche F (part 4) completed for `support_page.py` + `connection_page.py` quick fixes: removed remaining hardcoded white icon/selection colors in refreshed sections.
- 2026-02-16: Step 1 tranche F (part 5) completed for `autostart_page.py` quick cleanup: removed remaining hardcoded white badge text in recommended-state styles.
- 2026-02-16: Step 1 tranche F (part 6) completed for `strategies_page_base.py` quick cleanup: removed remaining `#60cdff/#ffffff/rgba(255...)` fallbacks in spinner/reset control visuals and switched to token-based neutrals.
- 2026-02-16: Step 1 tranche F (part 7) completed for `hosts_page.py`: replaced remaining hardcoded white/accent neutrals in danger/reset buttons, restore controls, combo selection fallback, and Adobe toggle text styles.
- 2026-02-16: Step 2 kickoff: added `ui/theme_semantic.py` with centralized semantic palette and migrated `hosts_page.py` status/warning/error semantic colors to shared constants.
- 2026-02-16: Step 2 (part 2): migrated `autostart_page.py` semantic success colors (badges/active states/status indicators) to `ui/theme_semantic.py`.
- 2026-02-16: Step 1 tranche G completed for previously missed pages: `dns_check_page.py`, `ipset_page.py`, `bat_strategies_page.py`, `zapret1_direct_strategies_page.py`, `zapret2/direct_zapret2_page.py` (tokenized hardcoded white/accent styles and added theme refresh hooks where needed).
- 2026-02-16: Repository audit pass completed: pages with `setStyleSheet` but no `get_theme_tokens()` reduced to `blockcheck_page.py` and `base_page.py`; added to late-audit backlog.
- 2026-02-16: Step 1 tranche H completed for `blockcheck_page.py`: tokenized teaser card/labels and custom animated scene palette with `get_theme_tokens()`, plus debounced theme refresh for the page.
- 2026-02-16: Repository audit update: pages with `setStyleSheet` but no `get_theme_tokens()` now reduced to `base_page.py` only.
- 2026-02-16: Step 1 tranche H (part 2) completed for `base_page.py`: moved base title/subtitle/section typography to token-aware styles and added debounced `StyleChange/PaletteChange` refresh.
- 2026-02-16: Repository audit final pass: no `ui/pages/*.py` files remain with `setStyleSheet` and without `get_theme_tokens()`.
- 2026-02-16: Step 2 tranche C completed for `support_page.py`, `strategies_page_base.py`, `premium_page.py`: migrated remaining success/warning/error status UI to `ui/theme_semantic.py` (including premium badge/server/activation and strategy status indicator/favorites badge).
- 2026-02-16: Step 3 completed for `ui/sidebar.py`: removed residual `#60cdff/#ffffff/rgba(255,255,255,...)` neutrals in action/icon/status controls, switched status colors to semantic palette, and added debounced theme refresh for sidebar status indicator.
- 2026-02-16: Verification unblock: `base_page.py` title font now safely falls back to `font_family_qss` when `font_family_display_qss` is absent in `ThemeTokens`.
- 2026-02-16: Residual cleanup tranche I completed for `home_page.py`, `servers_page.py`, `logs_page.py`: removed remaining `#60cdff/#ffffff/rgba(255,255,255,...)` patterns with token/semantic replacements and preserved existing behavior.
- 2026-02-16: Residual cleanup tranche J completed for `presets_page.py`, `control_page.py`, `custom_domains_page.py`: removed remaining `#60cdff/#ffffff/rgba(255,255,255,...)` tails in accent/pending controls with token/semantic-safe replacements.
- 2026-02-16: Residual cleanup tranche K completed for `zapret2/strategy_detail_page.py` and `zapret2/user_presets_page.py`: removed remaining `#60cdff/#ffffff/rgba(255,255,255,...)` menu/icon/accent fallbacks with token-safe equivalents.
- 2026-02-16: Residual cleanup tranche L completed for core shells/widgets (`close_dialog.py`, `custom_titlebar.py`, `fluent_icons.py`, `win11_spinner.py`, `notification_banner.py`, `strategy_search_bar.py`, `strategy_radio_item.py`, `direct_zapret2_strategies_tree.py`, `unified_strategies_list.py`): removed remaining critical `#60cdff/#ffffff/rgba(255,255,255,...)` literals, aligned visuals to token/semantic palette, and closed the `setStyleSheet` without `get_theme_tokens()` audit for `ui/**/*.py`.
- 2026-02-16: Residual cleanup tranche M completed for clean follow-up files (`strategies_tooltip.py`, `line_edit_icons.py`, `filter_chip_button.py`, `collapsible_group.py`, `direct_control_page.py`): removed remaining white-literal tails in dark-mode helpers/fallbacks and kept widget theming fully token-driven.
- 2026-02-16: Residual cleanup tranche N completed for remaining high-churn pages (`orchestra_page.py`, `orchestra_blocked_page.py`, `orchestra_locked_page.py`, `orchestra_ratings_page.py`, `blobs_page.py`): removed final `#ffffff/rgba(255,255,255,...)` tails in popup/selection/editor/accent button styles and closed repository-wide residual grep (excluding `ui/theme.py` internals).
