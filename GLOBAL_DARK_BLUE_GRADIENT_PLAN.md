# Global dark-blue surface styling plan

## Goals
- Move card/widget background styling to global theme CSS (`ui/theme.py`) for the `Темная синяя` theme.
- Remove neutral borders from non-selected widgets.
- Keep border emphasis only for highlighted states (selected/accent/disabled where needed).
- Eliminate hardcoded dark card color (`#252B3B/#252B3C`-like look) from DNS rows and use theme-derived surfaces.

## Stage 1 — Zapret2 critical surfaces
1. Update global selectors for primary card containers (`QFrame#settingsCard`) to use a smoother dark-blue gradient and no neutral border.
2. Add global selectors for `#categoryToolbarFrame` and `#categoryStrategiesBlock` (including `[categoryDisabled="true"]`) so local page CSS is no longer needed.
3. Ensure Zapret2 strategy list surfaces use global styling (no local frame gradient overrides where possible).

## Stage 2 — Network DNS consistency
1. Move `#dnsCard` visual states (default/hover/selected) into global theme CSS.
2. Remove local per-card CSS generation in `ui/pages/network_page.py`; keep only runtime state via dynamic property (`selected=true/false`).
3. Keep selected state readable with tinted gradient + accent border; neutral state borderless.

## Stage 3 — Secondary frames consistency
1. Apply global no-border + smooth-gradient rule to secondary card-like frames (for dark-blue theme only).
2. Keep global selectors strict by objectName/property to avoid regressions in input controls.

## Verification checklist
1. Zapret2: `Управление`, `Прямой запуск`, strategy details blocks.
2. Network: DNS provider list (default/hover/selected) and no hardcoded dark card color.
3. Regression: light themes should keep current behavior; dark-blue should show smooth gradients without neutral borders.
