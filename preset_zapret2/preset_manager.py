# preset_zapret2/preset_manager.py
"""
High-level preset manager for direct_zapret2 mode.

Provides a unified API for:
- Switching presets (copy to preset-zapret2.txt + DPI reload)
- Creating/editing/deleting presets
- Managing active preset

Usage:
    manager = PresetManager()

    # List available presets
    presets = manager.list_presets()

    # Switch to a preset (copies to preset-zapret2.txt)
    manager.switch_preset("Gaming")

    # Get current preset
    preset = manager.get_active_preset()

    # Create from current
    manager.create_preset_from_current("My Backup")
"""

import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Callable, List, Optional

from log import log

from .preset_model import CategoryConfig, Preset, SyndataSettings, validate_preset
from .ports import subtract_port_specs, union_port_specs
from .preset_storage import (
    delete_preset,
    duplicate_preset,
    export_preset,
    get_active_preset_name,
    get_active_preset_path,
    get_preset_path,
    get_presets_dir,
    import_preset,
    list_presets,
    load_preset,
    preset_exists,
    rename_preset,
    save_preset,
    set_active_preset_name,
)


class PresetManager:
    """
    High-level manager for preset operations.

    Handles:
    - Preset switching with DPI reload callback
    - Active preset tracking
    - Preset validation

    Attributes:
        on_preset_switched: Callback called after preset switch (name: str)
        on_dpi_reload_needed: Callback to trigger DPI service reload
    """

    def __init__(
        self,
        on_preset_switched: Optional[Callable[[str], None]] = None,
        on_dpi_reload_needed: Optional[Callable[[], None]] = None,
    ):
        """
        Initialize preset manager.

        Args:
            on_preset_switched: Callback after preset switch
            on_dpi_reload_needed: Callback to reload DPI service
        """
        self.on_preset_switched = on_preset_switched
        self.on_dpi_reload_needed = on_dpi_reload_needed

        # Cache for active preset to avoid repeated file parsing
        self._active_preset_cache: Optional[Preset] = None
        self._active_preset_mtime: float = 0.0

    # ========================================================================
    # LIST OPERATIONS
    # ========================================================================

    def list_presets(self) -> List[str]:
        """
        Lists all available preset names.

        Returns:
            List of preset names sorted alphabetically
        """
        return list_presets()

    def preset_exists(self, name: str) -> bool:
        """
        Checks if preset exists.

        Args:
            name: Preset name

        Returns:
            True if preset file exists
        """
        return preset_exists(name)

    def get_preset_count(self) -> int:
        """
        Returns number of available presets.

        Returns:
            Count of preset files
        """
        return len(list_presets())

    # ========================================================================
    # LOAD/SAVE OPERATIONS
    # ========================================================================

    def load_preset(self, name: str) -> Optional[Preset]:
        """
        Loads preset by name.

        Args:
            name: Preset name

        Returns:
            Preset object or None if not found
        """
        return load_preset(name)

    def save_preset(self, preset: Preset) -> bool:
        """
        Saves preset to file.

        Args:
            preset: Preset to save

        Returns:
            True if saved successfully
        """
        # ЗАЩИТА: Cannot save built-in presets
        if preset.is_builtin:
            log(f"Cannot save built-in preset '{preset.name}' - it's read-only", "WARNING")
            return False

        # Validate before saving
        errors = validate_preset(preset)
        if errors:
            log(f"Preset validation failed: {errors}", "WARNING")
            # Still save but log warnings

        return save_preset(preset)

    # ========================================================================
    # ACTIVE PRESET OPERATIONS
    # ========================================================================

    def get_active_preset_name(self) -> Optional[str]:
        """
        Gets name of currently active preset.

        Returns:
            Active preset name or None
        """
        return get_active_preset_name()

    def get_active_preset(self) -> Optional[Preset]:
        """
        Loads the currently active preset with caching.

        First checks cache validity (file mtime).
        If cache is invalid, loads from presets/ folder or parses preset-zapret2.txt.

        Returns:
            Active Preset or None
        """
        # Check cache validity
        if self._active_preset_cache is not None:
            current_mtime = self._get_active_file_mtime()
            if current_mtime == self._active_preset_mtime and current_mtime > 0:
                # Cache is valid
                return self._active_preset_cache

        # Source of truth for active state is preset-zapret2.txt.
        # Important: built-in presets (e.g. Default) are read-only in presets/,
        # but user changes are applied to preset-zapret2.txt, so loading from
        # presets/ would return stale data.
        preset = self._load_from_active_file()

        if not preset:
            # Fallback: load from presets/ folder if active file is missing/corrupted
            name = get_active_preset_name()
            if name and preset_exists(name):
                preset = load_preset(name)

        # Update cache
        if preset:
            self._active_preset_cache = preset
            self._active_preset_mtime = self._get_active_file_mtime()

        return preset

    def _load_from_active_file(self) -> Optional[Preset]:
        """
        Loads preset directly from preset-zapret2.txt.

        Used as fallback when active preset name is not in registry.

        Returns:
            Preset parsed from active file
        """
        from .txt_preset_parser import parse_preset_file

        active_path = get_active_preset_path()

        if not active_path.exists():
            log("Active preset file not found", "WARNING")
            return None

        try:
            data = parse_preset_file(active_path)

            # Determine name
            name = data.active_preset or data.name
            if name == "Unnamed":
                name = "Current"

            # Determine built-in flag:
            # - active file may lose "# Builtin:" header after edits (sync rewrites header),
            #   so also protect well-known built-ins by name and by the presets/ marker.
            from .preset_defaults import is_builtin_preset_name
            is_builtin = bool(data.is_builtin) or is_builtin_preset_name(name)
            try:
                active_registry_name = get_active_preset_name()
                if active_registry_name and preset_exists(active_registry_name):
                    # Lightweight header check to avoid loading full preset model.
                    preset_path = get_preset_path(active_registry_name)
                    if preset_path.exists():
                        head = preset_path.read_text(encoding="utf-8", errors="replace")[:4096]
                        for raw in head.splitlines():
                            line = raw.strip().lower()
                            if line.startswith("# builtin:"):
                                val = line.split(":", 1)[1].strip() if ":" in line else ""
                                if val in ("true", "yes", "1"):
                                    is_builtin = True
                                break
            except Exception:
                pass

            # Convert to Preset.
            # NOTE: --debug is a global runtime option; keep it in preset-zapret2.txt,
            # but don't persist it inside the preset model to avoid leaking it into
            # presets/ files.
            preset = Preset(
                name=name,
                base_args=self._strip_debug_from_base_args(data.base_args),
                is_builtin=is_builtin,
            )

            for block in data.categories:
                cat_name = block.category

                if cat_name not in preset.categories:
                    preset.categories[cat_name] = CategoryConfig(
                        name=cat_name,
                        filter_mode=block.filter_mode,
                    )

                cat = preset.categories[cat_name]

                # Restore per-protocol advanced settings from parsed dict (if present).
                if getattr(block, "syndata_dict", None):
                    if block.protocol == "tcp":
                        base = cat.syndata_tcp.to_dict()
                        base.update(block.syndata_dict)  # type: ignore[arg-type]
                        cat.syndata_tcp = SyndataSettings.from_dict(base)
                    elif block.protocol == "udp":
                        base = cat.syndata_udp.to_dict()
                        base.update(block.syndata_dict)  # type: ignore[arg-type]
                        cat.syndata_udp = SyndataSettings.from_dict(base)

                if block.protocol == "tcp":
                    cat.tcp_args = block.strategy_args
                    cat.tcp_port = block.port
                    cat.tcp_enabled = True
                    # TCP filter_mode has priority over UDP
                    cat.filter_mode = block.filter_mode
                elif block.protocol == "udp":
                    cat.udp_args = block.strategy_args
                    cat.udp_port = block.port
                    cat.udp_enabled = True
                    # UDP sets filter_mode only if TCP didn't set it
                    if not cat.filter_mode:
                        cat.filter_mode = block.filter_mode

            # ✅ INFERENCE: Determine strategy_id from args for all categories
            # This is needed because preset files store args but not strategy_id
            from .strategy_inference import infer_strategy_id_from_args

            for cat_name, cat in preset.categories.items():
                # Try TCP first (most common)
                if cat.tcp_args and cat.tcp_args.strip():
                    inferred_id = infer_strategy_id_from_args(
                        category_key=cat_name,
                        args=cat.tcp_args,
                        protocol="tcp"
                    )
                    if inferred_id != "none":
                        cat.strategy_id = inferred_id
                        continue

                # Try UDP if TCP didn't work
                if cat.udp_args and cat.udp_args.strip():
                    inferred_id = infer_strategy_id_from_args(
                        category_key=cat_name,
                        args=cat.udp_args,
                        protocol="udp"
                    )
                    if inferred_id != "none":
                        cat.strategy_id = inferred_id

            return preset

        except Exception as e:
            log(f"Error loading from active file: {e}", "ERROR")
            return None

    @staticmethod
    def _strip_debug_from_base_args(base_args: str) -> str:
        """ hookup to prevent persisting runtime --debug in preset model """
        try:
            lines = (base_args or "").splitlines()
            kept: list[str] = []
            for raw in lines:
                stripped = raw.strip()
                if not stripped:
                    continue
                if stripped.lower().startswith("--debug"):
                    continue
                kept.append(stripped)
            return "\n".join(kept).strip()
        except Exception:
            return (base_args or "").strip()

    def _maybe_inject_debug_into_base_args(self, base_args: str) -> str:
        """
        Injects or removes a `--debug=@...` line in base_args based on the global setting.

        The setting is stored in HKCU\\{REGISTRY_PATH}\\DirectMethod:
        - DebugLogEnabled (DWORD)
        - DebugLogFile (REG_SZ, relative path like "logs/zapret_winws2_debug_....log")
        """
        import winreg
        from datetime import datetime
        from config import REGISTRY_PATH

        cleaned = self._strip_debug_from_base_args(base_args)

        enabled = False
        debug_file = ""
        try:
            direct_path = rf"{REGISTRY_PATH}\DirectMethod"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, direct_path) as key:
                value, _ = winreg.QueryValueEx(key, "DebugLogEnabled")
                enabled = bool(value)
                try:
                    debug_file, _ = winreg.QueryValueEx(key, "DebugLogFile")
                except Exception:
                    debug_file = ""
        except Exception:
            enabled = False

        if not enabled:
            return cleaned

        if not debug_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            debug_file = f"logs/zapret_winws2_debug_{timestamp}.log"
            try:
                direct_path = rf"{REGISTRY_PATH}\DirectMethod"
                with winreg.CreateKey(winreg.HKEY_CURRENT_USER, direct_path) as key:
                    winreg.SetValueEx(key, "DebugLogFile", 0, winreg.REG_SZ, debug_file)
            except Exception:
                pass

        debug_file_norm = str(debug_file).replace("\\", "/").lstrip("@").lstrip("/")
        debug_line = f"--debug=@{debug_file_norm}"

        lines = cleaned.splitlines() if cleaned else []

        # Insert after last --lua-init line (if present), otherwise at the top.
        insert_at = 0
        for i, raw in enumerate(lines):
            if raw.strip().startswith("--lua-init="):
                insert_at = i + 1

        lines.insert(insert_at, debug_line)
        return "\n".join(lines).strip()

    def _get_active_file_mtime(self) -> float:
        """
        Gets modification time of active preset file.

        Returns:
            mtime as float timestamp, 0.0 if file does not exist
        """
        try:
            active_path = get_active_preset_path()
            if active_path.exists():
                return os.path.getmtime(str(active_path))
            return 0.0
        except Exception as e:
            log(f"Error getting active file mtime: {e}", "WARNING")
            return 0.0

    def _invalidate_active_preset_cache(self) -> None:
        """
        Invalidates the active preset cache.

        Should be called after any modification to the active preset.
        """
        self._active_preset_cache = None
        self._active_preset_mtime = 0.0

    # ========================================================================
    # SWITCH OPERATIONS
    # ========================================================================

    def switch_preset(self, name: str, reload_dpi: bool = True) -> bool:
        """
        Switches to a preset.

        Copies preset file to preset-zapret2.txt and optionally reloads DPI.

        Args:
            name: Preset name to switch to
            reload_dpi: Whether to trigger DPI reload after switch

        Returns:
            True if switched successfully
        """
        preset_path = get_preset_path(name)
        active_path = get_active_preset_path()

        if not preset_path.exists():
            log(f"Cannot switch: preset '{name}' not found", "ERROR")
            return False

        try:
            # Atomic copy: copy to temp, then rename
            temp_path = active_path.with_suffix('.tmp')
            shutil.copy2(preset_path, temp_path)

            # Add ActivePreset marker to file
            self._add_active_preset_marker(temp_path, name)

            # Atomic replace (works even if target exists)
            import os
            os.replace(str(temp_path), str(active_path))

            # Update registry
            set_active_preset_name(name)

            # Invalidate cache after switch
            self._invalidate_active_preset_cache()

            log(f"Switched to preset '{name}'", "INFO")

            # Callbacks
            if self.on_preset_switched:
                self.on_preset_switched(name)

            if reload_dpi and self.on_dpi_reload_needed:
                self.on_dpi_reload_needed()

            return True

        except Exception as e:
            log(f"Error switching preset: {e}", "ERROR")
            # Cleanup temp file
            temp_path = active_path.with_suffix('.tmp')
            if temp_path.exists():
                temp_path.unlink()
            return False

    def _add_active_preset_marker(self, file_path: Path, preset_name: str) -> None:
        """
        Adds ActivePreset comment to preset file.

        Args:
            file_path: Path to preset file
            preset_name: Name of active preset
        """
        try:
            content = file_path.read_text(encoding='utf-8')
            lines = content.split('\n')

            # Find if # ActivePreset: already exists
            active_idx = None
            for i, line in enumerate(lines):
                if line.strip().lower().startswith('# activepreset:'):
                    active_idx = i
                    break

            if active_idx is not None:
                # Update existing
                lines[active_idx] = f"# ActivePreset: {preset_name}"
            else:
                # Add after # Preset: line or at start
                insert_idx = 0
                for i, line in enumerate(lines):
                    if line.strip().lower().startswith('# preset:'):
                        insert_idx = i + 1
                        break

                lines.insert(insert_idx, f"# ActivePreset: {preset_name}")

            file_path.write_text('\n'.join(lines), encoding='utf-8')

        except Exception as e:
            log(f"Error adding active preset marker: {e}", "WARNING")

    # ========================================================================
    # CREATE OPERATIONS
    # ========================================================================

    def create_preset(self, name: str, from_current: bool = True) -> Optional[Preset]:
        """
        Creates a new preset.

        Args:
            name: Name for new preset
            from_current: If True, copy current preset-zapret2.txt.
                         If False, create empty preset.

        Returns:
            Created Preset or None on error
        """
        if preset_exists(name):
            log(f"Cannot create: preset '{name}' already exists", "WARNING")
            return None

        try:
            if from_current:
                # Copy from current active preset
                current = self._load_from_active_file()
                if current:
                    current.name = name
                    current.created = datetime.now().isoformat()
                    current.modified = datetime.now().isoformat()
                    current.is_builtin = False

                    if save_preset(current):
                        log(f"Created preset '{name}' from current", "INFO")
                        return current
                    return None
                else:
                    # No current, create default
                    return self.create_default_preset(name)
            else:
                return self.create_default_preset(name)

        except Exception as e:
            log(f"Error creating preset: {e}", "ERROR")
            return None

    def create_default_preset(self, name: str = "Default") -> Optional[Preset]:
        """
        Creates a default preset by copying from the built-in template.

        Args:
            name: Preset name

        Returns:
            Created Preset or None
        """
        if preset_exists(name):
            log(f"Cannot create: preset '{name}' already exists", "WARNING")
            return None

        try:
            # Create from built-in in-code template (no default.txt dependency).
            from .preset_defaults import DEFAULT_PRESET_CONTENT
            from .txt_preset_parser import parse_preset_content, generate_preset_file

            data = parse_preset_content(DEFAULT_PRESET_CONTENT)
            data.name = name
            data.active_preset = None
            data.is_builtin = False
            # generate_preset_content() preserves raw_header when present, so it must be updated
            # when we create a new preset from the Default template.
            now = datetime.now().isoformat()
            data.raw_header = f"""# Preset: {name}
# Created: {now}
# Modified: {now}
# Description: """

            dest_path = get_preset_path(name)
            if not generate_preset_file(data, dest_path, atomic=True):
                return None

            log(f"Created preset '{name}' from default template", "INFO")

            # Load and return the created preset
            return load_preset(name)

        except Exception as e:
            log(f"Error creating default preset: {e}", "ERROR")
            return None

    def create_preset_from_current(self, name: str) -> Optional[Preset]:
        """
        Creates a new preset from current configuration.

        Shorthand for create_preset(name, from_current=True).

        Args:
            name: Name for new preset

        Returns:
            Created Preset or None
        """
        return self.create_preset(name, from_current=True)

    # ========================================================================
    # DELETE/RENAME OPERATIONS
    # ========================================================================

    def delete_preset(self, name: str) -> bool:
        """
        Deletes preset.

        Cannot delete currently active preset or built-in presets.

        Args:
            name: Preset name

        Returns:
            True if deleted
        """
        # Check if active
        active_name = get_active_preset_name()
        if active_name == name:
            log(f"Cannot delete active preset '{name}'", "WARNING")
            return False

        # Check if builtin (also checked in storage layer)
        preset = load_preset(name)
        if preset and preset.is_builtin:
            log(f"Cannot delete built-in preset '{name}'", "WARNING")
            return False

        return delete_preset(name)

    def rename_preset(self, old_name: str, new_name: str) -> bool:
        """
        Renames preset.

        Cannot rename built-in presets.
        Updates active preset name in registry if renamed preset is active.

        Args:
            old_name: Current name
            new_name: New name

        Returns:
            True if renamed
        """
        # Check if builtin (also checked in storage layer)
        preset = load_preset(old_name)
        if preset and preset.is_builtin:
            log(f"Cannot rename built-in preset '{old_name}'", "WARNING")
            return False

        if rename_preset(old_name, new_name):
            # Update active preset name if this was active
            if get_active_preset_name() == old_name:
                set_active_preset_name(new_name)
            return True
        return False

    def duplicate_preset(self, name: str, new_name: str) -> bool:
        """
        Creates a copy of preset.

        Args:
            name: Source preset name
            new_name: Name for the copy

        Returns:
            True if duplicated
        """
        return duplicate_preset(name, new_name)

    # ========================================================================
    # IMPORT/EXPORT OPERATIONS
    # ========================================================================

    def export_preset(self, name: str, dest_path: Path) -> bool:
        """
        Exports preset to external file.

        Cannot export built-in presets.

        Args:
            name: Preset name
            dest_path: Destination path

        Returns:
            True if exported
        """
        # Check if builtin (also checked in storage layer)
        preset = load_preset(name)
        if preset and preset.is_builtin:
            log(f"Cannot export built-in preset '{name}'", "WARNING")
            return False

        return export_preset(name, dest_path)

    def import_preset(self, src_path: Path, name: Optional[str] = None) -> bool:
        """
        Imports preset from external file.

        Args:
            src_path: Source file path
            name: Optional name (uses filename if None)

        Returns:
            True if imported
        """
        return import_preset(src_path, name)

    # ========================================================================
    # UTILITY METHODS
    # ========================================================================

    def ensure_presets_dir(self) -> Path:
        """
        Ensures presets directory exists.

        Returns:
            Path to presets directory
        """
        return get_presets_dir()

    def get_active_preset_path(self) -> Path:
        """
        Gets path to active preset file.

        Returns:
            Path to preset-zapret2.txt
        """
        return get_active_preset_path()

    def load_current_from_registry(self) -> Optional[Preset]:
        """
        Loads preset configuration from registry.

        Legacy method for compatibility.
        Now just returns active preset.

        Returns:
            Active Preset
        """
        return self.get_active_preset()

    def sync_preset_to_active_file(self, preset: Preset) -> bool:
        """
        Writes preset directly to preset-zapret2.txt.

        Use this when editing the active preset without switching.
        Triggers DPI reload.

        Args:
            preset: Preset to write

        Returns:
            True if successful
        """
        from .txt_preset_parser import CategoryBlock, PresetData, generate_preset_file

        active_path = get_active_preset_path()

        try:
            # Keep wf-*-out in sync with enabled category port filters.
            preset.base_args = self._update_wf_out_ports_in_base_args(preset)

            # Convert to PresetData
            data = PresetData(
                name=preset.name,
                active_preset=preset.name,
                base_args=self._maybe_inject_debug_into_base_args(preset.base_args),
            )

            # Build header
            data.raw_header = f"""# Preset: {preset.name}
# ActivePreset: {preset.name}
# Modified: {datetime.now().isoformat()}"""

            # Convert categories
            for cat_name, cat in preset.categories.items():
                if cat.tcp_enabled and cat.has_tcp():
                    from .base_filter import build_category_base_filter_lines
                    base_filter_lines = build_category_base_filter_lines(cat_name, cat.filter_mode)

                    # Fallback: keep old behavior only if base_filter is missing.
                    args_lines = list(base_filter_lines)
                    if not args_lines:
                        filter_file_relative = cat.get_hostlist_file() if cat.filter_mode == "hostlist" else cat.get_ipset_file()
                        from config import MAIN_DIRECTORY
                        filter_file = os.path.normpath(os.path.join(MAIN_DIRECTORY, filter_file_relative))
                        args_lines = [f"--filter-tcp={cat.tcp_port}"]
                        if cat.filter_mode in ("hostlist", "ipset"):
                            args_lines.append(f"--{cat.filter_mode}={filter_file}")

                    # Use get_full_tcp_args() to include syndata/send/out-range
                    full_tcp_args = cat.get_full_tcp_args()
                    for line in full_tcp_args.strip().split('\n'):
                        if line.strip():
                            args_lines.append(line.strip())

                    block = CategoryBlock(
                        category=cat_name,
                        protocol="tcp",
                        filter_mode=cat.filter_mode if cat.filter_mode in ("hostlist", "ipset") else "",
                        filter_file="",
                        port=cat.tcp_port,
                        args='\n'.join(args_lines),
                        strategy_args=cat.tcp_args,
                    )
                    data.categories.append(block)

                if cat.udp_enabled and cat.has_udp():
                    from .base_filter import build_category_base_filter_lines
                    base_filter_lines = build_category_base_filter_lines(cat_name, cat.filter_mode)

                    args_lines = list(base_filter_lines)
                    if not args_lines:
                        filter_file_relative = cat.get_ipset_file() if cat.filter_mode == "ipset" else cat.get_hostlist_file()
                        from config import MAIN_DIRECTORY
                        filter_file = os.path.normpath(os.path.join(MAIN_DIRECTORY, filter_file_relative))
                        args_lines = [f"--filter-udp={cat.udp_port}"]
                        if cat.filter_mode in ("hostlist", "ipset"):
                            args_lines.append(f"--{cat.filter_mode}={filter_file}")

                    # Use get_full_udp_args() to include out-range (UDP has no syndata/send)
                    full_udp_args = cat.get_full_udp_args()
                    for line in full_udp_args.strip().split('\n'):
                        if line.strip():
                            args_lines.append(line.strip())

                    block = CategoryBlock(
                        category=cat_name,
                        protocol="udp",
                        filter_mode=cat.filter_mode if cat.filter_mode in ("hostlist", "ipset") else "",
                        filter_file="",
                        port=cat.udp_port,
                        args='\n'.join(args_lines),
                        strategy_args=cat.udp_args,
                    )
                    data.categories.append(block)

            # Deduplicate categories before writing
            data.deduplicate_categories()

            # Write
            success = generate_preset_file(data, active_path, atomic=True)

            if success:
                # Invalidate cache after sync
                self._invalidate_active_preset_cache()

                log(f"Synced preset to active file", "DEBUG")

                # Trigger DPI reload
                if self.on_dpi_reload_needed:
                    self.on_dpi_reload_needed()

            return success

        except PermissionError as e:
            log(f"Cannot write preset file (locked by winws2?): {e}", "ERROR")
            raise
        except Exception as e:
            log(f"Error syncing to active file: {e}", "ERROR")
            return False

    def _update_wf_out_ports_in_base_args(self, preset: Preset) -> str:
        """
        Updates `--wf-tcp-out` / `--wf-udp-out` in base_args based on enabled category filters.

        Behavior:
        - Treats existing `--wf-*-out=` as a base (user-controlled) port list.
        - Adds/removes extra ports required by enabled category `--filter-tcp/--filter-udp`.
        - Prevents stale ports from accumulating when categories are disabled.

        Implementation detail:
        - Remembers the previously auto-added "extra" ports in base_args via a comment line:
          `# AutoWFOutExtra: tcp=... udp=...`
          On the next sync we subtract that extra from the current `--wf-*-out` to recover base ports.

        Normalization:
        - sort ascending
        - merge ranges
        - remove duplicates (including singles covered by ranges)
        """
        from .base_filter import build_category_base_filter_lines

        base_args = preset.base_args or ""
        lines = base_args.splitlines()

        marker_prefix = "# AutoWFOutExtra:"
        marker_prefix_l = marker_prefix.lower()

        existing_wf_tcp = ""
        existing_wf_udp = ""
        prev_extra_tcp = ""
        prev_extra_udp = ""
        marker_present = False
        keep_empty_marker = False
        for raw in lines:
            stripped = raw.strip()
            if stripped.startswith("--wf-tcp-out="):
                existing_wf_tcp = stripped.split("=", 1)[1].strip()
            elif stripped.startswith("--wf-udp-out="):
                existing_wf_udp = stripped.split("=", 1)[1].strip()
            elif stripped.lower().startswith(marker_prefix_l):
                marker_present = True
                payload = stripped.split(":", 1)[1].strip() if ":" in stripped else ""
                for token in payload.split():
                    k, _, v = token.partition("=")
                    k_l = k.strip().lower()
                    if k_l == "tcp":
                        prev_extra_tcp = v.strip()
                    elif k_l == "udp":
                        prev_extra_udp = v.strip()

        # One-time cleanup for the built-in "Default" preset:
        # before this fix we used to permanently merge category ports into `--wf-*-out`,
        # so disabling a category could leave stale ports behind.
        # Here we reset the base wf ports to the template values (if available).
        if not marker_present and (preset.name or "").strip().lower() == "default":
            try:
                from .preset_defaults import DEFAULT_PRESET_CONTENT

                template_tcp = ""
                template_udp = ""
                for raw in DEFAULT_PRESET_CONTENT.splitlines():
                    s = raw.strip()
                    if s.startswith("--wf-tcp-out="):
                        template_tcp = s.split("=", 1)[1].strip()
                    elif s.startswith("--wf-udp-out="):
                        template_udp = s.split("=", 1)[1].strip()
                    if template_tcp and template_udp:
                        break

                if template_tcp:
                    existing_wf_tcp = template_tcp
                if template_udp:
                    existing_wf_udp = template_udp
                # Keep an empty marker line to avoid re-running this migration on every save/sync.
                keep_empty_marker = True
            except Exception:
                pass

        # Recover base ports by subtracting the previously auto-added extra.
        base_wf_tcp = subtract_port_specs(existing_wf_tcp, prev_extra_tcp) if prev_extra_tcp else (existing_wf_tcp or "")
        base_wf_udp = subtract_port_specs(existing_wf_udp, prev_extra_udp) if prev_extra_udp else (existing_wf_udp or "")

        if base_wf_tcp:
            base_wf_tcp = union_port_specs([base_wf_tcp])
        if base_wf_udp:
            base_wf_udp = union_port_specs([base_wf_udp])

        tcp_specs: list[str] = []
        udp_specs: list[str] = []

        for cat_name, cat in preset.categories.items():
            if cat.tcp_enabled and cat.has_tcp():
                base_filter_lines = build_category_base_filter_lines(cat_name, cat.filter_mode)
                spec = ""
                for token in base_filter_lines:
                    token_s = token.strip()
                    if token_s.startswith("--filter-tcp="):
                        spec = token_s.split("=", 1)[1].strip()
                        break
                if not spec:
                    spec = (cat.tcp_port or "").strip()
                if spec:
                    tcp_specs.append(spec)

            if cat.udp_enabled and cat.has_udp():
                base_filter_lines = build_category_base_filter_lines(cat_name, cat.filter_mode)
                spec = ""
                for token in base_filter_lines:
                    token_s = token.strip()
                    if token_s.startswith("--filter-udp="):
                        spec = token_s.split("=", 1)[1].strip()
                        break
                if not spec:
                    spec = (cat.udp_port or "").strip()
                if spec:
                    udp_specs.append(spec)

        cats_wf_tcp = union_port_specs(tcp_specs) if tcp_specs else ""
        cats_wf_udp = union_port_specs(udp_specs) if udp_specs else ""

        new_extra_tcp = subtract_port_specs(cats_wf_tcp, base_wf_tcp) if cats_wf_tcp else ""
        new_extra_udp = subtract_port_specs(cats_wf_udp, base_wf_udp) if cats_wf_udp else ""

        new_wf_tcp = union_port_specs([base_wf_tcp, new_extra_tcp]) if (base_wf_tcp or new_extra_tcp) else ""
        new_wf_udp = union_port_specs([base_wf_udp, new_extra_udp]) if (base_wf_udp or new_extra_udp) else ""

        def _replace_or_add(prefix: str, value: str) -> None:
            nonlocal lines
            if not value:
                return
            replaced = False
            out: list[str] = []
            for raw in lines:
                if raw.strip().startswith(prefix):
                    out.append(f"{prefix}{value}")
                    replaced = True
                else:
                    out.append(raw)
            if not replaced:
                # Insert after last lua-init line, otherwise near the top.
                insert_at = 0
                for i, raw in enumerate(out):
                    if raw.strip().startswith("--lua-init="):
                        insert_at = i + 1
                out.insert(insert_at, f"{prefix}{value}")
            lines = out

        def _set_marker(extra_tcp: str, extra_udp: str, keep_empty: bool = False) -> None:
            nonlocal lines
            parts: list[str] = []
            if extra_tcp:
                parts.append(f"tcp={extra_tcp}")
            if extra_udp:
                parts.append(f"udp={extra_udp}")
            if parts:
                marker_line = f"{marker_prefix} {' '.join(parts)}".rstrip()
            elif keep_empty:
                marker_line = marker_prefix
            else:
                marker_line = ""

            out: list[str] = []
            replaced = False
            for raw in lines:
                if raw.strip().lower().startswith(marker_prefix_l):
                    replaced = True
                    if marker_line:
                        out.append(marker_line)
                else:
                    out.append(raw)

            if not replaced and marker_line:
                # Insert after wf lines if present, otherwise after lua-init.
                insert_at = 0
                for i, raw in enumerate(out):
                    s = raw.strip()
                    if s.startswith("--wf-"):
                        insert_at = i + 1
                    elif s.startswith("--lua-init=") and insert_at == 0:
                        insert_at = i + 1
                out.insert(insert_at, marker_line)

            lines = out

        if new_wf_tcp:
            _replace_or_add("--wf-tcp-out=", new_wf_tcp)
        if new_wf_udp:
            _replace_or_add("--wf-udp-out=", new_wf_udp)

        # Keep marker only if it is needed to remove extra ports later.
        keep_empty_final = marker_present or keep_empty_marker
        _set_marker(new_extra_tcp, new_extra_udp, keep_empty=keep_empty_final)

        return "\n".join(lines).strip()

    # ========================================================================
    # CATEGORY SETTINGS OPERATIONS
    # ========================================================================

    @staticmethod
    def _normalize_syndata_protocol(protocol: str) -> str:
        proto = (protocol or "").strip().lower()
        if proto in ("udp", "quic", "l7", "raw"):
            return "udp"
        return "tcp"

    def get_category_syndata(self, category_key: str, protocol: str = "tcp") -> SyndataSettings:
        """
        Gets syndata settings for a category from active preset.

        Args:
            category_key: Category name (e.g., "youtube", "discord")
            protocol: "tcp" or "udp" (udp also covers QUIC/L7)

        Returns:
            SyndataSettings for the category (defaults if not found)
        """
        preset = self.get_active_preset()
        if not preset:
            return SyndataSettings.get_defaults() if self._normalize_syndata_protocol(protocol) == "tcp" else SyndataSettings.get_defaults_udp()

        category = preset.categories.get(category_key)
        if not category:
            return SyndataSettings.get_defaults() if self._normalize_syndata_protocol(protocol) == "tcp" else SyndataSettings.get_defaults_udp()

        return category.syndata_tcp if self._normalize_syndata_protocol(protocol) == "tcp" else category.syndata_udp

    def update_category_syndata(
        self,
        category_key: str,
        syndata: SyndataSettings,
        save_and_sync: bool = True,
        protocol: str = "tcp",
    ) -> bool:
        """
        Updates syndata settings for a category.

        Args:
            category_key: Category name
            syndata: New syndata settings
            save_and_sync: If True, save preset and sync to active file
            protocol: "tcp" or "udp" (udp also covers QUIC/L7)

        Returns:
            True if successful
        """
        preset = self.get_active_preset()
        if not preset:
            log(f"Cannot update syndata: no active preset", "WARNING")
            return False

        # Create category if not exists
        if category_key not in preset.categories:
            preset.categories[category_key] = self._create_category_with_defaults(category_key)

        protocol_key = self._normalize_syndata_protocol(protocol)
        if protocol_key == "udp":
            syndata.enabled = False
            syndata.send_enabled = False
            preset.categories[category_key].syndata_udp = syndata
        else:
            preset.categories[category_key].syndata_tcp = syndata
        preset.touch()

        if save_and_sync:
            return self._save_and_sync_preset(preset)

        return True

    def get_category_filter_mode(self, category_key: str) -> str:
        """
        Gets filter mode for a category.

        Args:
            category_key: Category name

        Returns:
            "hostlist" or "ipset"
        """
        preset = self.get_active_preset()
        if not preset:
            return "hostlist"

        category = preset.categories.get(category_key)
        if not category:
            return "hostlist"

        return category.filter_mode

    def update_category_filter_mode(
        self,
        category_key: str,
        filter_mode: str,
        save_and_sync: bool = True
    ) -> bool:
        """
        Updates filter mode for a category.

        Args:
            category_key: Category name
            filter_mode: "hostlist" or "ipset"
            save_and_sync: If True, save preset and sync to active file

        Returns:
            True if successful
        """
        if filter_mode not in ("hostlist", "ipset"):
            log(f"Invalid filter_mode: {filter_mode}", "WARNING")
            return False

        preset = self.get_active_preset()
        if not preset:
            log(f"Cannot update filter_mode: no active preset", "WARNING")
            return False

        # Create category if not exists
        if category_key not in preset.categories:
            preset.categories[category_key] = self._create_category_with_defaults(category_key)

        preset.categories[category_key].filter_mode = filter_mode
        preset.touch()

        if save_and_sync:
            return self._save_and_sync_preset(preset)

        return True

    def get_category_sort_order(self, category_key: str) -> str:
        """
        Gets sort order for a category.

        Args:
            category_key: Category name

        Returns:
            "default", "name_asc", or "name_desc"
        """
        preset = self.get_active_preset()
        if not preset:
            return "default"

        category = preset.categories.get(category_key)
        if not category:
            return "default"

        return category.sort_order

    def update_category_sort_order(
        self,
        category_key: str,
        sort_order: str,
        save_and_sync: bool = True
    ) -> bool:
        """
        Updates sort order for a category.

        Args:
            category_key: Category name
            sort_order: "default", "name_asc", or "name_desc"
            save_and_sync: If True, save preset and sync to active file

        Returns:
            True if successful
        """
        if sort_order not in ("default", "name_asc", "name_desc"):
            log(f"Invalid sort_order: {sort_order}", "WARNING")
            return False

        preset = self.get_active_preset()
        if not preset:
            log(f"Cannot update sort_order: no active preset", "WARNING")
            return False

        # Create category if not exists
        if category_key not in preset.categories:
            preset.categories[category_key] = self._create_category_with_defaults(category_key)

        preset.categories[category_key].sort_order = sort_order
        preset.touch()

        if save_and_sync:
            return self._save_and_sync_preset(preset)

        return True

    def reset_category_settings(self, category_key: str) -> bool:
        """
        Resets all category settings to defaults from DEFAULT_PRESET_CONTENT.

        Args:
            category_key: Category name

        Returns:
            True if successful
        """
        preset = self.get_active_preset()
        if not preset:
            return False

        # Ensure category exists so UI can reset even if it wasn't enabled before.
        if category_key not in preset.categories:
            preset.categories[category_key] = self._create_category_with_defaults(category_key)

        cat = preset.categories[category_key]

        from .preset_defaults import (
            get_default_category_settings,
            get_category_default_filter_mode,
            get_category_default_syndata,
        )
        from .strategy_inference import infer_strategy_id_from_args

        default_filter_mode = get_category_default_filter_mode(category_key)
        default_settings = get_default_category_settings().get(category_key) or {}

        # Reset non-strategy state.
        cat.syndata_tcp = SyndataSettings.from_dict(get_category_default_syndata(category_key, protocol="tcp"))
        cat.syndata_udp = SyndataSettings.from_dict(get_category_default_syndata(category_key, protocol="udp"))
        cat.filter_mode = default_filter_mode
        cat.sort_order = "default"

        # Reset args/ports from DEFAULT_PRESET_CONTENT when available, otherwise keep
        # selection but normalize args from strategy_id.
        if default_settings:
            cat.tcp_enabled = bool(default_settings.get("tcp_enabled", False))
            cat.udp_enabled = bool(default_settings.get("udp_enabled", False))
            cat.tcp_port = str(default_settings.get("tcp_port") or cat.tcp_port or "443")
            cat.udp_port = str(default_settings.get("udp_port") or cat.udp_port or "443")
            cat.tcp_args = str(default_settings.get("tcp_args") or "").strip()
            cat.udp_args = str(default_settings.get("udp_args") or "").strip()

            # Infer strategy_id for UI highlight, if possible.
            inferred = "none"
            if cat.tcp_args:
                inferred = infer_strategy_id_from_args(category_key=category_key, args=cat.tcp_args, protocol="tcp")
            if inferred == "none" and cat.udp_args:
                inferred = infer_strategy_id_from_args(category_key=category_key, args=cat.udp_args, protocol="udp")
            cat.strategy_id = inferred or "none"
        else:
            # Unknown category in template: keep current strategy_id but reset advanced settings.
            if cat.strategy_id and cat.strategy_id != "none":
                self._update_category_args_from_strategy(preset, category_key, cat.strategy_id)
            else:
                cat.tcp_args = ""
                cat.udp_args = ""
                cat.strategy_id = "none"
        preset.touch()

        return self._save_and_sync_preset(preset)

    def reset_active_preset_to_default_template(self) -> bool:
        """
        Global reset: replace active preset-zapret2.txt content with a built-in template.

        Does not depend on preset_zapret2/default.txt existing on disk.
        """
        from .preset_defaults import (
            DEFAULT_PRESET_CONTENT,
            get_builtin_preset_content,
            get_builtin_base_from_copy_name,
            is_builtin_preset_name,
        )
        from .txt_preset_parser import parse_preset_content
        from .strategy_inference import infer_strategy_id_from_args

        preset_name = get_active_preset_name() or "Current"

        try:
            template_content = DEFAULT_PRESET_CONTENT
            if is_builtin_preset_name(preset_name):
                builtin_template = get_builtin_preset_content(preset_name)
                if builtin_template is not None:
                    template_content = builtin_template
            else:
                base = get_builtin_base_from_copy_name(preset_name)
                if base:
                    builtin_template = get_builtin_preset_content(base)
                    if builtin_template is not None:
                        template_content = builtin_template

            data = parse_preset_content(template_content)

            # Build Preset model, then reuse sync logic to generate a proper active file
            # (including absolute list paths and normalized base filters).
            preset = Preset(name=preset_name, base_args=data.base_args)
            existing = load_preset(preset_name) if preset_exists(preset_name) else None
            if existing and not existing.is_builtin:
                preset.created = existing.created
                preset.description = existing.description

            for block in data.categories:
                cat_name = block.category
                if cat_name not in preset.categories:
                    preset.categories[cat_name] = CategoryConfig(
                        name=cat_name,
                        filter_mode=block.filter_mode or "hostlist",
                        syndata_tcp=SyndataSettings.get_defaults(),
                        syndata_udp=SyndataSettings.get_defaults_udp(),
                    )

                cat = preset.categories[cat_name]
                cat.filter_mode = block.filter_mode or cat.filter_mode or "hostlist"

                if block.protocol == "tcp":
                    cat.tcp_enabled = True
                    cat.tcp_port = block.port
                    cat.tcp_args = (block.strategy_args or "").strip()
                elif block.protocol == "udp":
                    cat.udp_enabled = True
                    cat.udp_port = block.port
                    cat.udp_args = (block.strategy_args or "").strip()

                # Prefer explicit overrides from the template block if present.
                if getattr(block, "syndata_dict", None):
                    if block.protocol == "tcp":
                        base = cat.syndata_tcp.to_dict()
                        base.update(block.syndata_dict)  # type: ignore[arg-type]
                        cat.syndata_tcp = SyndataSettings.from_dict(base)
                    elif block.protocol == "udp":
                        base = cat.syndata_udp.to_dict()
                        base.update(block.syndata_dict)  # type: ignore[arg-type]
                        cat.syndata_udp = SyndataSettings.from_dict(base)

            for cat_name, cat in preset.categories.items():
                inferred = "none"
                if cat.tcp_args:
                    inferred = infer_strategy_id_from_args(category_key=cat_name, args=cat.tcp_args, protocol="tcp")
                if inferred == "none" and cat.udp_args:
                    inferred = infer_strategy_id_from_args(category_key=cat_name, args=cat.udp_args, protocol="udp")
                cat.strategy_id = inferred or "none"

            # Persist reset into the preset file when active preset is a normal (non-built-in) preset.
            if preset.name and preset.name != "Current" and preset_exists(preset.name):
                existing2 = load_preset(preset.name)
                if existing2 and not existing2.is_builtin:
                    save_preset(preset)

            return self.sync_preset_to_active_file(preset)
        except Exception as e:
            log(f"Error resetting active preset to built-in template: {e}", "ERROR")
            return False

    def reset_preset_to_default_template(self, preset_name: str) -> bool:
        """
        Resets a specific (non-built-in) preset to the built-in `Default` template and activates it.

        Overwrites:
        - presets/{preset_name}.txt
        - preset-zapret2.txt
        """
        from .preset_defaults import DEFAULT_PRESET_CONTENT, get_builtin_preset_content
        from .txt_preset_parser import parse_preset_content
        from .strategy_inference import infer_strategy_id_from_args

        name = (preset_name or "").strip()
        if not name:
            return False

        try:
            if not preset_exists(name):
                log(f"Cannot reset: preset '{name}' not found", "ERROR")
                return False

            existing = load_preset(name)
            if not existing:
                log(f"Cannot reset: failed to load preset '{name}'", "ERROR")
                return False

            if existing.is_builtin:
                log(f"Cannot reset built-in preset '{name}'", "WARNING")
                return False

            template_content = get_builtin_preset_content("Default") or DEFAULT_PRESET_CONTENT
            data = parse_preset_content(template_content)

            preset = Preset(name=name, base_args=data.base_args, is_builtin=False)
            preset.created = existing.created
            preset.description = existing.description

            for block in data.categories:
                cat_name = block.category
                if cat_name not in preset.categories:
                    preset.categories[cat_name] = CategoryConfig(
                        name=cat_name,
                        filter_mode=block.filter_mode or "hostlist",
                        syndata_tcp=SyndataSettings.get_defaults(),
                        syndata_udp=SyndataSettings.get_defaults_udp(),
                    )

                cat = preset.categories[cat_name]
                cat.filter_mode = block.filter_mode or cat.filter_mode or "hostlist"

                if block.protocol == "tcp":
                    cat.tcp_enabled = True
                    cat.tcp_port = block.port
                    cat.tcp_args = (block.strategy_args or "").strip()
                elif block.protocol == "udp":
                    cat.udp_enabled = True
                    cat.udp_port = block.port
                    cat.udp_args = (block.strategy_args or "").strip()

                # Prefer explicit overrides from the template block if present.
                if getattr(block, "syndata_dict", None):
                    if block.protocol == "tcp":
                        base = cat.syndata_tcp.to_dict()
                        base.update(block.syndata_dict)  # type: ignore[arg-type]
                        cat.syndata_tcp = SyndataSettings.from_dict(base)
                    elif block.protocol == "udp":
                        base = cat.syndata_udp.to_dict()
                        base.update(block.syndata_dict)  # type: ignore[arg-type]
                        cat.syndata_udp = SyndataSettings.from_dict(base)

            for cat_name, cat in preset.categories.items():
                inferred = "none"
                if cat.tcp_args:
                    inferred = infer_strategy_id_from_args(category_key=cat_name, args=cat.tcp_args, protocol="tcp")
                if inferred == "none" and cat.udp_args:
                    inferred = infer_strategy_id_from_args(category_key=cat_name, args=cat.udp_args, protocol="udp")
                cat.strategy_id = inferred or "none"

            # Make this preset active (so UI state and active file match).
            set_active_preset_name(name)
            self._invalidate_active_preset_cache()
            if self.on_preset_switched:
                try:
                    self.on_preset_switched(name)
                except Exception:
                    pass

            return self._save_and_sync_preset(preset)

        except Exception as e:
            log(f"Error resetting preset '{name}' to Default template: {e}", "ERROR")
            return False

    def _save_and_sync_preset(self, preset: Preset) -> bool:
        """
        Saves preset to file and syncs to active file.

        Args:
            preset: Preset to save

        Returns:
            True if successful
        """
        # Normalize/update wf-*-out before persisting anywhere.
        preset.base_args = self._update_wf_out_ports_in_base_args(preset)

        preset_to_sync = preset

        # Built-in presets are templates: persist user edits as a normal preset copy
        # and switch active preset name to that copy.
        if preset.is_builtin and preset.name and preset.name != "Current":
            try:
                from .preset_defaults import get_builtin_copy_name
                copy_name = get_builtin_copy_name(preset.name) or f"{preset.name} (копия)"

                existing = load_preset(copy_name) if preset_exists(copy_name) else None
                copy_preset = Preset(
                    name=copy_name,
                    base_args=preset.base_args,
                    categories=preset.categories,
                    description=(existing.description if existing else f"Копия встроенного пресета {preset.name}"),
                    created=(existing.created if existing else datetime.now().isoformat()),
                    modified=datetime.now().isoformat(),
                    is_builtin=False,
                )

                set_active_preset_name(copy_name)
                preset_to_sync = copy_preset

                log(f"Created/updated copy preset '{copy_name}' from built-in '{preset.name}'", "INFO")
            except Exception as e:
                log(f"Failed to materialize built-in copy preset: {e}", "WARNING")

        # First save to presets folder if it has a name (normal presets only).
        if preset_to_sync.name and preset_to_sync.name != "Current" and not preset_to_sync.is_builtin:
            save_preset(preset_to_sync)

        # Then sync to active file (triggers DPI reload via callback)
        # Note: sync_preset_to_active_file() already invalidates cache
        return self.sync_preset_to_active_file(preset_to_sync)

    def _create_category_with_defaults(self, category_key: str) -> CategoryConfig:
        """
        Creates a new CategoryConfig with defaults from DEFAULT_PRESET_CONTENT.

        If category exists in DEFAULT_PRESET_CONTENT (youtube, discord, etc.),
        uses its specific settings (syndata, filter_mode).
        Otherwise, uses fallback defaults.

        Args:
            category_key: Category name (e.g., "youtube", "discord")

        Returns:
            CategoryConfig with proper defaults
        """
        category_key = str(category_key or "").strip().lower()
        from .preset_defaults import (
            get_category_default_syndata,
            get_category_default_filter_mode
        )

        # Get defaults from DEFAULT_PRESET_CONTENT
        syndata_tcp = SyndataSettings.from_dict(get_category_default_syndata(category_key, protocol="tcp"))
        syndata_udp = SyndataSettings.from_dict(get_category_default_syndata(category_key, protocol="udp"))
        filter_mode = get_category_default_filter_mode(category_key)

        return CategoryConfig(
            name=category_key,
            syndata_tcp=syndata_tcp,
            syndata_udp=syndata_udp,
            filter_mode=filter_mode
        )

    # ========================================================================
    # STRATEGY SELECTION OPERATIONS
    # ========================================================================

    def get_strategy_selections(self) -> dict:
        """
        Gets strategy selections from active preset.

        Returns:
            Dict of category_key -> strategy_id
        """
        preset = self.get_active_preset()
        if not preset:
            return {}

        selections = {}
        for cat_key, cat_config in preset.categories.items():
            selections[cat_key] = cat_config.strategy_id
        return selections

    def set_strategy_selection(
        self,
        category_key: str,
        strategy_id: str,
        save_and_sync: bool = True
    ) -> bool:
        """
        Sets strategy selection for a category.

        Args:
            category_key: Category name (e.g., "youtube")
            strategy_id: Strategy ID (e.g., "youtube_tcp_split") or "none"
            save_and_sync: If True, save preset and sync to active file

        Returns:
            True if successful
        """
        category_key = str(category_key or "").strip().lower()
        preset = self.get_active_preset()
        if not preset:
            log(f"Cannot set strategy: no active preset", "WARNING")
            return False

        # Create category if not exists
        if category_key not in preset.categories:
            preset.categories[category_key] = self._create_category_with_defaults(category_key)

        preset.categories[category_key].strategy_id = strategy_id

        # Update tcp_args/udp_args based on strategy_id
        self._update_category_args_from_strategy(preset, category_key, strategy_id)

        preset.touch()

        if save_and_sync:
            return self._save_and_sync_preset(preset)

        return True

    def _update_category_args_from_strategy(
        self,
        preset: Preset,
        category_key: str,
        strategy_id: str
    ) -> None:
        """
        Updates tcp_args/udp_args based on strategy_id.

        Args:
            preset: Preset to update
            category_key: Category name
            strategy_id: Strategy ID
        """
        cat = preset.categories.get(category_key)
        if not cat:
            return

        if strategy_id == "none":
            # Clear args when strategy is disabled
            cat.tcp_args = ""
            cat.udp_args = ""
            return

        from .catalog import load_categories, load_strategies

        categories = load_categories()
        category_info = categories.get(category_key) or {}
        strategy_type = (category_info.get("strategy_type") or "tcp").strip() or "tcp"

        strategies = load_strategies(strategy_type)
        args = (strategies.get(strategy_id) or {}).get("args", "") or ""

        # TCP presets may include strategies from tcp_fake.txt (multi-phase UI).
        # Keep selection working by falling back to that catalog file.
        if not args and strategy_type == "tcp":
            try:
                fake_strategies = load_strategies("tcp_fake")
                args = (fake_strategies.get(strategy_id) or {}).get("args", "") or ""
            except Exception:
                args = args or ""

        if args:
            protocol = (category_info.get("protocol") or "").upper()
            is_udp = any(t in protocol for t in ("UDP", "QUIC", "L7", "RAW"))
            if is_udp:
                cat.udp_args = args
                cat.tcp_args = ""
            else:
                cat.tcp_args = args
                cat.udp_args = ""

    def set_strategy_selections(
        self,
        selections: dict,
        save_and_sync: bool = True
    ) -> bool:
        """
        Sets multiple strategy selections at once.

        Args:
            selections: Dict of category_key -> strategy_id
            save_and_sync: If True, save preset and sync to active file

        Returns:
            True if successful
        """
        preset = self.get_active_preset()
        if not preset:
            log(f"Cannot set strategies: no active preset", "WARNING")
            return False

        for cat_key, strategy_id in (selections or {}).items():
            cat_key = str(cat_key or "").strip().lower()
            if not cat_key:
                continue
            if cat_key not in preset.categories:
                preset.categories[cat_key] = self._create_category_with_defaults(cat_key)
            preset.categories[cat_key].strategy_id = strategy_id
            # Update args from strategy_id
            self._update_category_args_from_strategy(preset, cat_key, strategy_id)

        preset.touch()

        if save_and_sync:
            return self._save_and_sync_preset(preset)

        return True

    def reset_strategy_selections_to_defaults(self, save_and_sync: bool = True) -> bool:
        """
        Resets all strategy selections to defaults from categories.txt.

        Returns:
            True if successful
        """
        from .catalog import load_categories

        preset = self.get_active_preset()
        if not preset:
            log(f"Cannot reset strategies: no active preset", "WARNING")
            return False

        categories = load_categories()
        defaults = {
            key: (info.get("default_strategy") or "none")
            for key, info in categories.items()
        }

        for cat_key, default_strategy in defaults.items():
            if cat_key not in preset.categories:
                preset.categories[cat_key] = self._create_category_with_defaults(cat_key)
            preset.categories[cat_key].strategy_id = default_strategy
            # Update args from strategy_id
            self._update_category_args_from_strategy(preset, cat_key, default_strategy)

        preset.touch()

        if save_and_sync:
            return self._save_and_sync_preset(preset)

        return True

    def clear_all_strategy_selections(self, save_and_sync: bool = True) -> bool:
        """
        Sets all strategy selections to "none".

        Returns:
            True if successful
        """
        from .catalog import load_categories

        preset = self.get_active_preset()
        if not preset:
            log(f"Cannot clear strategies: no active preset", "WARNING")
            return False

        for cat_key in load_categories().keys():
            if cat_key not in preset.categories:
                preset.categories[cat_key] = self._create_category_with_defaults(cat_key)
            preset.categories[cat_key].strategy_id = "none"
            # Clear args when strategy is "none"
            preset.categories[cat_key].tcp_args = ""
            preset.categories[cat_key].udp_args = ""

        preset.touch()

        if save_and_sync:
            return self._save_and_sync_preset(preset)

        return True
