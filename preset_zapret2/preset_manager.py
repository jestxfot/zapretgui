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
                log(f"[CACHE] Active preset cache HIT", "DEBUG")
                return self._active_preset_cache

        log(f"[CACHE] Active preset cache MISS, loading...", "DEBUG")

        # Cache miss or invalid - load preset
        name = get_active_preset_name()
        preset = None

        if name and preset_exists(name):
            preset = load_preset(name)

        if not preset:
            # Fallback: parse preset-zapret2.txt directly
            preset = self._load_from_active_file()

        # Update cache
        if preset:
            self._active_preset_cache = preset
            self._active_preset_mtime = self._get_active_file_mtime()
            log(f"[MANAGER] Loaded active preset: {len(preset.categories)} categories", "DEBUG")

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

            # Convert to Preset
            preset = Preset(name=name, base_args=data.base_args)

            for block in data.categories:
                cat_name = block.category

                if cat_name not in preset.categories:
                    preset.categories[cat_name] = CategoryConfig(
                        name=cat_name,
                        filter_mode=block.filter_mode,
                    )

                cat = preset.categories[cat_name]

                if block.protocol == "tcp":
                    cat.tcp_args = block.strategy_args
                    cat.tcp_port = block.port
                    cat.tcp_enabled = True
                elif block.protocol == "udp":
                    cat.udp_args = block.strategy_args
                    cat.udp_port = block.port
                    cat.udp_enabled = True

            # ✅ INFERENCE: Determine strategy_id from args for all categories
            # This is needed because preset files store args but not strategy_id
            from .strategy_inference import infer_strategy_id_from_args
            from strategy_menu.strategies_registry import registry

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
                        log(f"[INFER] {cat_name}: inferred strategy_id={inferred_id} from tcp_args", "DEBUG")
                        # ✅ CLEAN: Replace dirty args with clean args from JSON
                        strategy_data = registry.get_strategy(cat_name, inferred_id)
                        if strategy_data and "args" in strategy_data:
                            clean_args = strategy_data["args"]
                            if clean_args != cat.tcp_args:
                                log(f"[CLEAN] {cat_name}.tcp_args cleaned: {repr(cat.tcp_args[:60])} → {repr(clean_args[:60])}", "DEBUG")
                                cat.tcp_args = clean_args
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
                        log(f"[INFER] {cat_name}: inferred strategy_id={inferred_id} from udp_args", "DEBUG")
                        # ✅ CLEAN: Replace dirty args with clean args from JSON
                        strategy_data = registry.get_strategy(cat_name, inferred_id)
                        if strategy_data and "args" in strategy_data:
                            clean_args = strategy_data["args"]
                            if clean_args != cat.udp_args:
                                log(f"[CLEAN] {cat_name}.udp_args cleaned: {repr(cat.udp_args[:60])} → {repr(clean_args[:60])}", "DEBUG")
                                cat.udp_args = clean_args

            return preset

        except Exception as e:
            log(f"Error loading from active file: {e}", "ERROR")
            return None

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
            # Path to built-in default.txt template
            default_template = Path(__file__).parent / "default.txt"

            if not default_template.exists():
                log(f"Default template not found at {default_template}", "ERROR")
                return None

            # Copy template to presets folder with the given name
            dest_path = get_preset_path(name)
            shutil.copy2(default_template, dest_path)

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
            # Convert to PresetData
            data = PresetData(
                name=preset.name,
                active_preset=preset.name,
                base_args=preset.base_args,
            )

            # Build header
            data.raw_header = f"""# Preset: {preset.name}
# ActivePreset: {preset.name}
# Modified: {datetime.now().isoformat()}"""

            # Convert categories
            for cat_name, cat in preset.categories.items():
                if cat.tcp_enabled and cat.has_tcp():
                    filter_file_relative = cat.get_hostlist_file() if cat.filter_mode == "hostlist" else cat.get_ipset_file()
                    # Convert to absolute path for winws2.exe and normalize slashes
                    from config import MAIN_DIRECTORY
                    filter_file = os.path.normpath(os.path.join(MAIN_DIRECTORY, filter_file_relative))

                    args_lines = [
                        f"--filter-tcp={cat.tcp_port}",
                        f"--{cat.filter_mode}={filter_file}",
                    ]
                    # Use get_full_tcp_args() to include syndata/send/out-range
                    full_tcp_args = cat.get_full_tcp_args()
                    for line in full_tcp_args.strip().split('\n'):
                        if line.strip():
                            args_lines.append(line.strip())

                    block = CategoryBlock(
                        category=cat_name,
                        protocol="tcp",
                        filter_mode=cat.filter_mode,
                        filter_file=filter_file,
                        port=cat.tcp_port,
                        args='\n'.join(args_lines),
                        strategy_args=cat.tcp_args,
                    )
                    data.categories.append(block)

                if cat.udp_enabled and cat.has_udp():
                    # For UDP, typically use ipset
                    filter_file_relative = cat.get_ipset_file() if cat.filter_mode == "ipset" else cat.get_hostlist_file()
                    # Convert to absolute path for winws2.exe and normalize slashes
                    filter_file = os.path.normpath(os.path.join(MAIN_DIRECTORY, filter_file_relative))

                    args_lines = [
                        f"--filter-udp={cat.udp_port}",
                        f"--{cat.filter_mode}={filter_file}",
                    ]
                    # Use get_full_udp_args() to include syndata/send/out-range
                    full_udp_args = cat.get_full_udp_args()
                    for line in full_udp_args.strip().split('\n'):
                        if line.strip():
                            args_lines.append(line.strip())

                    block = CategoryBlock(
                        category=cat_name,
                        protocol="udp",
                        filter_mode=cat.filter_mode,
                        filter_file=filter_file,
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

    # ========================================================================
    # CATEGORY SETTINGS OPERATIONS
    # ========================================================================

    def get_category_syndata(self, category_key: str) -> SyndataSettings:
        """
        Gets syndata settings for a category from active preset.

        Args:
            category_key: Category name (e.g., "youtube", "discord")

        Returns:
            SyndataSettings for the category (defaults if not found)
        """
        preset = self.get_active_preset()
        if not preset:
            return SyndataSettings.get_defaults()

        category = preset.categories.get(category_key)
        if not category:
            return SyndataSettings.get_defaults()

        return category.syndata

    def update_category_syndata(
        self,
        category_key: str,
        syndata: SyndataSettings,
        save_and_sync: bool = True
    ) -> bool:
        """
        Updates syndata settings for a category.

        Args:
            category_key: Category name
            syndata: New syndata settings
            save_and_sync: If True, save preset and sync to active file

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

        preset.categories[category_key].syndata = syndata
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

        if category_key not in preset.categories:
            return True  # Nothing to reset

        # Get default filter_mode and syndata from DEFAULT_PRESET_CONTENT
        from .preset_defaults import (
            get_category_default_filter_mode,
            get_category_default_syndata
        )
        default_filter_mode = get_category_default_filter_mode(category_key)
        default_syndata = get_category_default_syndata(category_key)

        # Reset all settings to defaults
        preset.categories[category_key].syndata = default_syndata
        preset.categories[category_key].filter_mode = default_filter_mode
        preset.categories[category_key].sort_order = "default"
        # Clear strategy (will not be written to file if no args)
        preset.categories[category_key].strategy_id = "none"
        preset.categories[category_key].tcp_args = ""
        preset.categories[category_key].udp_args = ""
        preset.touch()

        return self._save_and_sync_preset(preset)

    def _save_and_sync_preset(self, preset: Preset) -> bool:
        """
        Saves preset to file and syncs to active file.

        Args:
            preset: Preset to save

        Returns:
            True if successful
        """
        # First save to presets folder if it has a name
        if preset.name and preset.name != "Current":
            save_preset(preset)

        # Then sync to active file (triggers DPI reload via callback)
        # Note: sync_preset_to_active_file() already invalidates cache
        return self.sync_preset_to_active_file(preset)

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
        from .preset_defaults import (
            get_category_default_syndata,
            get_category_default_filter_mode
        )

        # Get defaults from DEFAULT_PRESET_CONTENT
        syndata_dict = get_category_default_syndata(category_key)
        syndata = SyndataSettings.from_dict(syndata_dict)
        filter_mode = get_category_default_filter_mode(category_key)

        return CategoryConfig(
            name=category_key,
            syndata=syndata,
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
        from strategy_menu.strategies_registry import registry

        cat = preset.categories.get(category_key)
        if not cat:
            return

        if strategy_id == "none":
            # Clear args when strategy is disabled
            cat.tcp_args = ""
            cat.udp_args = ""
            return

        # Get args from registry
        args = registry.get_strategy_args_safe(category_key, strategy_id)
        log(f"[DEBUG] Strategy args from registry for {category_key}/{strategy_id}: {repr(args)}", "DEBUG")

        if args:
            # Clean args: remove filters to avoid duplication
            # (filters will be added by sync_preset_to_active_file)
            from .txt_preset_parser import extract_strategy_args
            clean_args = extract_strategy_args(args)
            log(f"[DEBUG] Cleaned args: {repr(clean_args)}", "DEBUG")

            # Determine if this is TCP or UDP strategy based on category info
            category_info = registry.get_category_info(category_key)
            if category_info:
                # Most strategies apply to TCP
                # UDP categories have special handling
                if "_udp" in category_key or category_info.strategy_type.endswith("_udp"):
                    cat.udp_args = clean_args
                    log(f"[DEBUG] Updated {category_key}.udp_args = {repr(clean_args)}", "DEBUG")
                else:
                    cat.tcp_args = clean_args
                    log(f"[DEBUG] Updated {category_key}.tcp_args = {repr(clean_args)}", "DEBUG")

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

        for cat_key, strategy_id in selections.items():
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
        Resets all strategy selections to defaults from registry.

        Returns:
            True if successful
        """
        from strategy_menu.strategies_registry import registry

        preset = self.get_active_preset()
        if not preset:
            log(f"Cannot reset strategies: no active preset", "WARNING")
            return False

        defaults = registry.get_default_selections()

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
        from strategy_menu.strategies_registry import registry

        preset = self.get_active_preset()
        if not preset:
            log(f"Cannot clear strategies: no active preset", "WARNING")
            return False

        for cat_key in registry.get_all_category_keys():
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
