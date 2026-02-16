# Theme Switch Optimization Plan

## Problem Statement

Theme switching feels slow because several expensive operations happen around one user action:

1. Global stylesheet is reapplied to the entire app (`QApplication.setStyleSheet`).
2. Many pages react to `StyleChange/PaletteChange` and re-run their own theme styling.
3. Rapid repeated switches may wait for previous worker shutdown on the UI thread.
4. First switch for a theme may include cold CSS generation.

## Current Flow (Where Time Is Spent)

- Click handler: `ui/pages/appearance_page.py` -> `AppearancePage._on_theme_clicked`
- Signal wiring: `managers/initialization_manager.py` -> `self.app.theme_changed.connect(self.app.change_theme)`
- Theme routing: `ui/theme_subscription_manager.py` -> `change_theme`
- Async pipeline: `ui/theme.py` -> `ThemeHandler.change_theme` -> `ThemeManager.apply_theme_async`
- Background build: `ui/theme.py` -> `ThemeBuildWorker.run`
- Main-thread apply: `ui/theme.py` -> `ThemeManager._apply_css_only`
- Post updates: `ui/theme.py` -> `ThemeHandler._post_theme_change_update` and `_update_titlebar_theme`
- Additional page refreshes: `ui/pages/base_page.py` and page-specific `changeEvent` / `_apply_theme*` methods

## Root Causes

1. **Global style recalculation cost**
   - `self.app.setStyleSheet(final_css)` is heavy and blocks the main thread.
2. **Duplicate work after global apply**
   - Many widgets/pages re-apply local styles in `changeEvent`, often with many `setStyleSheet` calls.
3. **Blocking worker teardown on rapid switches**
   - Existing `wait(...)` logic can freeze interaction when switching themes quickly.
4. **Cold cache path is still expensive**
   - `qt_material.build_stylesheet(...)` is expensive for first use of a theme.

## Optimization Goals

- Keep UI responsive during switch (especially rapid toggles).
- Reduce total theme switch latency in warm cache mode.
- Minimize duplicate style work and simplify ownership of theme updates.

Suggested targets:

- Warm cache single switch: no visible freeze; main-thread blocking clearly reduced.
- Rapid 3-5 switches: latest theme wins without waiting for stale work.
- Cold cache: progress remains responsive and switch is faster after first use.

## Implementation Plan

## Progress Tracking

- [x] Phase 1 baseline instrumentation added (end-to-end timing, `setStyleSheet` timing capture, page refresh counter).
- [x] Additional readability fixes on `Мои пресеты` page for theme-aware contrast (icons, destructive states, inline/popover error styles, runtime re-theme).
- [x] Unified shared widget colors with theme tokens/semantic palette (`sidebar`, `ResetActionButton`, strategy search controls, line edit clear icons, direct strategies tree row states).
- [x] Phase 2 non-blocking worker replacement (`request_id`/latest-wins, removed UI-thread waits, stale progress/results ignored).
- [x] Phase 3 reduce duplicate page-level re-application after global stylesheet apply (theme-key dedupe in `BasePage`, shared sidebar/search widgets, and `Мои пресеты` page refresh path).
- [x] Phase 4 cache/reuse refinements completed (runtime active-theme token cache, shared qtawesome pixmap cache, theme-aware strategy-tree icon cache, bounded FluentIcon cache).
- [x] Unified card/frame gradients across pages with real `qlineargradient` (Windows 11-like dark stops `#252B3B -> #252A3E`, including autostart/home/presets/servers/dialog surfaces).
- [x] Added fast theme apply path: split CSS into base + dynamic overlay, reapply heavy base layer only when needed (light/dark or special theme boundary), apply dynamic layer to main window subtree.
- [ ] Optional idle prewarm (prepare alternate theme/cache in background after startup idle).

### Phase 1 - Baseline and Instrumentation

1. Add end-to-end timing markers:
   - Start at `AppearancePage._on_theme_clicked`.
   - Stop at `ThemeHandler._on_theme_change_done`.
2. Keep and standardize `setStyleSheet took ...` logging in `_apply_css_only`.
3. Add temporary counters for page-level theme refresh handlers (`changeEvent` -> `_apply_theme*`).
4. Capture baseline for three scenarios:
   - warm cache single switch,
   - cold cache first switch,
   - rapid repeated switching.

### Phase 2 - Remove UI-Thread Blocking and Stale Work

1. Replace blocking worker stop/wait with generation IDs:
   - Each theme request gets `request_id`.
   - Worker result includes `request_id`.
   - Apply only if `request_id == latest_request_id`; otherwise ignore stale result.
2. Remove `wait(1000)` / `wait(500)` style blocking from rapid switch path.
3. Optional: add short debounce (for click bursts) so only the final request is executed.

### Phase 3 - Eliminate Duplicate Theme Re-Application

1. Define one authoritative style pass:
   - Global app stylesheet apply remains the primary color/shape mechanism.
2. Reduce page-level `changeEvent` work:
   - Skip heavy `_apply_theme*` routines for style-only changes already covered globally.
   - Keep only non-QSS dynamic updates (rare icon/text/runtime data updates).
3. Audit pages with large local theme code and move repeated styles into centralized QSS where possible.

### Phase 4 - Cache and Reuse

1. Ensure token usage is explicit and cheap:
   - Pass `theme_name`/tokens through call chain, avoid repeated default registry lookups where not needed.
2. Cache themed icons where possible:
   - Reuse `qta.icon(...)` results by key (icon id + color + size + state).
3. Optional startup warmup:
   - Preload CSS for current theme (and optionally last-used alternate theme) when app is idle.

## Verification Plan

For each phase, compare before/after logs for:

1. End-to-end switch time.
2. Main-thread style apply time (`setStyleSheet took ...`).
3. Number of page-level theme refresh executions per switch.
4. User-visible responsiveness during rapid toggling.

Manual test matrix:

- Scenario A: warm cache, single switch
- Scenario B: cold cache, first switch to unused theme
- Scenario C: quick burst of 3-5 theme clicks

Acceptance criteria:

- No long UI stalls when rapidly switching.
- Noticeably faster completion in warm-cache path.
- Reduced count of redundant page-level theme refresh calls.

## Rollout Order

1. Phase 1 instrumentation.
2. Phase 2 non-blocking request handling.
3. Phase 3 duplicate-work reduction (small safe batches).
4. Phase 4 caching refinements.

This order gives measurable wins early and lowers risk while refactoring.
