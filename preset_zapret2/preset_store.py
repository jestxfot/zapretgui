# preset_zapret2/preset_store.py
"""
Central in-memory preset store (singleton).

Provides a single source of truth for all preset data across the application.
All UI pages and backend modules should use this store instead of creating
independent PresetManager instances.

Features:
- All presets loaded into memory once, refreshed only when files change
- Qt signals for preset lifecycle events (change, switch, create, delete)
- Thread-safe singleton access via get_preset_store()

Usage:
    from preset_zapret2.preset_store import get_preset_store

    store = get_preset_store()

    # Read presets (from memory, instant)
    all_presets = store.get_all_presets()
    builtin = store.get_builtin_presets()
    user = store.get_user_presets()
    preset = store.get_preset("Default")

    # Listen for changes
    store.presets_changed.connect(my_handler)
    store.preset_switched.connect(on_switched)
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Optional

from PyQt6.QtCore import QObject, pyqtSignal

from log import log


class PresetStore(QObject):
    """
    Central in-memory preset store (singleton).

    Holds all parsed Preset objects in memory.
    Emits Qt signals when preset data changes.
    """

    # ── Signals ──────────────────────────────────────────────────────────
    # Emitted when the preset list or content changes (add/delete/rename/import/reset).
    # Listeners should refresh their preset list UI.
    presets_changed = pyqtSignal()

    # Emitted when the active preset is switched. Argument: new active preset name.
    preset_switched = pyqtSignal(str)

    # Emitted when a single preset's content is updated (save/sync).
    # Argument: preset name that was updated.
    preset_updated = pyqtSignal(str)

    # ── Singleton ────────────────────────────────────────────────────────
    _instance: Optional[PresetStore] = None

    @classmethod
    def instance(cls) -> PresetStore:
        """Returns the singleton PresetStore instance, creating it if needed."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)

        # {preset_name: Preset}  —  all presets (builtin + user)
        self._presets: Dict[str, "Preset"] = {}

        # mtime tracking for user preset files: {name: mtime}
        self._user_preset_mtimes: Dict[str, float] = {}

        # Flag: initial load done?
        self._loaded = False

        # Active preset name (cached from INI)
        self._active_name: Optional[str] = None

    # ── Public API: Read ─────────────────────────────────────────────────

    def get_all_presets(self) -> Dict[str, "Preset"]:
        """Returns all presets (builtin + user). Loads from disk on first call."""
        self._ensure_loaded()
        return dict(self._presets)

    def get_preset(self, name: str) -> Optional["Preset"]:
        """Returns a single preset by name, or None."""
        self._ensure_loaded()
        return self._presets.get(name)

    def get_preset_names(self) -> List[str]:
        """Returns sorted list of all preset names."""
        self._ensure_loaded()
        return sorted(self._presets.keys(), key=lambda s: s.lower())

    def get_builtin_presets(self) -> Dict[str, "Preset"]:
        """Returns only built-in (template) presets."""
        self._ensure_loaded()
        return {n: p for n, p in self._presets.items() if p.is_builtin}

    def get_user_presets(self) -> Dict[str, "Preset"]:
        """Returns only user (editable) presets."""
        self._ensure_loaded()
        return {n: p for n, p in self._presets.items() if not p.is_builtin}

    def get_active_preset_name(self) -> Optional[str]:
        """Returns the currently active preset name."""
        self._ensure_loaded()
        return self._active_name

    def preset_exists(self, name: str) -> bool:
        """Checks if preset exists in the store."""
        self._ensure_loaded()
        return name in self._presets

    # ── Public API: Mutate ───────────────────────────────────────────────

    def refresh(self) -> None:
        """
        Full reload from disk. Clears all in-memory state and re-reads.
        Emits presets_changed after reload.
        """
        self._do_full_load()
        self.presets_changed.emit()

    def notify_preset_saved(self, name: str) -> None:
        """
        Called after a preset file is saved/modified on disk.
        Re-reads that single preset and emits preset_updated.
        """
        self._ensure_loaded()
        self._reload_single_preset(name)
        self.preset_updated.emit(name)

    def notify_presets_changed(self) -> None:
        """
        Called after an operation that changes the preset list
        (create, delete, rename, duplicate, import).
        Performs a full reload and emits presets_changed.
        """
        self._do_full_load()
        self.presets_changed.emit()

    def notify_preset_switched(self, name: str) -> None:
        """
        Called after the active preset is switched.
        Updates the cached active name and emits preset_switched.
        """
        self._active_name = name
        self.preset_switched.emit(name)

    def notify_active_name_changed(self) -> None:
        """Re-reads the active preset name from the INI file."""
        from .preset_storage import get_active_preset_name
        self._active_name = get_active_preset_name()

    # ── Internal ─────────────────────────────────────────────────────────

    def _ensure_loaded(self) -> None:
        """Loads all presets from disk on first access."""
        if not self._loaded:
            self._do_full_load()

    def _do_full_load(self) -> None:
        """Reads all presets from disk into memory."""
        from .preset_storage import list_presets, load_preset, get_active_preset_name, get_preset_path

        self._presets.clear()
        self._user_preset_mtimes.clear()

        names = list_presets()
        for name in names:
            try:
                preset = load_preset(name)
                if preset is not None:
                    self._presets[name] = preset
                    # Track mtime for user presets
                    if not preset.is_builtin:
                        try:
                            path = get_preset_path(name)
                            if path.exists():
                                self._user_preset_mtimes[name] = os.path.getmtime(str(path))
                        except Exception:
                            pass
            except Exception as e:
                log(f"PresetStore: error loading preset '{name}': {e}", "DEBUG")

        self._active_name = get_active_preset_name()
        self._loaded = True

        log(
            f"PresetStore: loaded {len(self._presets)} presets "
            f"({sum(1 for p in self._presets.values() if p.is_builtin)} builtin, "
            f"{sum(1 for p in self._presets.values() if not p.is_builtin)} user)",
            "DEBUG",
        )

    def _reload_single_preset(self, name: str) -> None:
        """Re-reads a single preset from disk into the store."""
        from .preset_storage import load_preset, get_preset_path

        try:
            preset = load_preset(name)
            if preset is not None:
                self._presets[name] = preset
                if not preset.is_builtin:
                    try:
                        path = get_preset_path(name)
                        if path.exists():
                            self._user_preset_mtimes[name] = os.path.getmtime(str(path))
                    except Exception:
                        pass
            else:
                # Preset was deleted or became unreadable
                self._presets.pop(name, None)
                self._user_preset_mtimes.pop(name, None)
        except Exception as e:
            log(f"PresetStore: error reloading preset '{name}': {e}", "DEBUG")


def get_preset_store() -> PresetStore:
    """Returns the global PresetStore singleton."""
    return PresetStore.instance()
