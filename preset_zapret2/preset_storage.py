# presets/preset_storage.py
"""
Storage layer for preset system.

Handles reading/writing preset files to disk.
Presets are stored as txt files in {PROGRAMDATA_PATH}/presets/.
Active preset name is stored in registry.
"""

import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

from log import log

# Lazy imports to avoid circular dependencies
_PROGRAMDATA_PATH: Optional[str] = None
_MAIN_DIRECTORY: Optional[str] = None


def _get_programdata_path() -> str:
    """Lazily gets PROGRAMDATA_PATH to avoid import cycles."""
    global _PROGRAMDATA_PATH
    if _PROGRAMDATA_PATH is None:
        from config import PROGRAMDATA_PATH
        _PROGRAMDATA_PATH = PROGRAMDATA_PATH
    return _PROGRAMDATA_PATH


def _get_main_directory() -> str:
    """Lazily gets MAIN_DIRECTORY to avoid import cycles."""
    global _MAIN_DIRECTORY
    if _MAIN_DIRECTORY is None:
        from config import MAIN_DIRECTORY
        _MAIN_DIRECTORY = MAIN_DIRECTORY
    return _MAIN_DIRECTORY


# ============================================================================
# PATH FUNCTIONS
# ============================================================================

def get_presets_dir() -> Path:
    """
    Returns path to presets directory.

    Creates directory if it doesn't exist.

    Returns:
        Path to {PROGRAMDATA_PATH}/presets/
    """
    presets_dir = Path(_get_programdata_path()) / "presets"
    presets_dir.mkdir(parents=True, exist_ok=True)
    return presets_dir


def get_builtin_overrides_dir() -> Path:
    """
    Returns path to built-in presets overrides directory.

    Built-in presets (Default/Gaming/...) are stored as in-code templates and are read-only.
    User changes to a built-in preset are persisted as an override file here.

    Returns:
        Path to {PROGRAMDATA_PATH}/presets/_builtin_overrides/
    """
    overrides_dir = get_presets_dir() / "_builtin_overrides"
    overrides_dir.mkdir(parents=True, exist_ok=True)
    return overrides_dir


def get_builtin_override_path(name: str) -> Path:
    """
    Returns path to a built-in preset override file.

    Args:
        name: Built-in preset name

    Returns:
        Path to presets/_builtin_overrides/{name}.txt
    """
    safe_name = _sanitize_filename(name)
    return get_builtin_overrides_dir() / f"{safe_name}.txt"


def builtin_override_exists(name: str) -> bool:
    """Checks if a built-in preset override exists."""
    try:
        return get_builtin_override_path(name).exists()
    except Exception:
        return False


def delete_builtin_override(name: str) -> bool:
    """Deletes a built-in preset override file (if present)."""
    try:
        path = get_builtin_override_path(name)
        if path.exists():
            path.unlink()
        return True
    except Exception as e:
        log(f"Error deleting built-in override for '{name}': {e}", "DEBUG")
        return False


def save_builtin_override_from_path(name: str, src_path: Path) -> bool:
    """
    Saves built-in preset override by copying a source preset file.

    Uses atomic write (temp file + replace) for safety.
    """
    try:
        src_path = Path(src_path)
        if not src_path.exists():
            return False

        dest_path = get_builtin_override_path(name)
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        fd, tmp_name = tempfile.mkstemp(
            prefix=f"{dest_path.stem}_",
            suffix=".tmp",
            dir=str(dest_path.parent),
        )
        os.close(fd)
        tmp_path = Path(tmp_name)

        try:
            shutil.copy2(src_path, tmp_path)
            os.replace(str(tmp_path), str(dest_path))
            return True
        finally:
            try:
                if tmp_path.exists():
                    tmp_path.unlink()
            except Exception:
                pass

    except Exception as e:
        log(f"Error saving built-in override for '{name}': {e}", "DEBUG")
        return False


def save_builtin_override_from_active(name: str) -> bool:
    """Saves built-in preset override from the current active preset file."""
    return save_builtin_override_from_path(name, get_active_preset_path())


def get_preset_path(name: str) -> Path:
    """
    Returns path to a specific preset file.

    Args:
        name: Preset name (without .txt extension)

    Returns:
        Path to presets/{name}.txt
    """
    # Sanitize name (remove dangerous characters)
    safe_name = _sanitize_filename(name)
    return get_presets_dir() / f"{safe_name}.txt"


def get_active_preset_path() -> Path:
    """
    Returns path to active preset file (preset-zapret2.txt).

    This is the file that winws2 reads.

    Returns:
        Path to {PROGRAMDATA_PATH}/preset-zapret2.txt
    """
    return Path(_get_programdata_path()) / "preset-zapret2.txt"


def get_user_settings_path() -> Path:
    """
    Returns path to user settings file.

    This stores user-specific settings like active preset name.

    Returns:
        Path to {PROGRAMDATA_PATH}/user_settings.json
    """
    return Path(_get_programdata_path()) / "user_settings.json"


def _sanitize_filename(name: str) -> str:
    """
    Sanitizes filename by removing dangerous characters.

    Args:
        name: Original filename

    Returns:
        Safe filename
    """
    # Remove path separators and other dangerous chars
    dangerous = ['/', '\\', ':', '*', '?', '"', '<', '>', '|', '\0']
    safe_name = name
    for char in dangerous:
        safe_name = safe_name.replace(char, '_')
    # Limit length
    return safe_name[:100]


# ============================================================================
# LIST OPERATIONS
# ============================================================================

def list_presets() -> List[str]:
    """
    Lists all available preset names.

    Returns:
        List of preset names (without .txt extension), sorted alphabetically.
    """
    presets_dir = get_presets_dir()

    if not presets_dir.exists():
        return []

    presets = []
    for f in presets_dir.glob("*.txt"):
        if f.is_file():
            presets.append(f.stem)

    return sorted(presets)


def preset_exists(name: str) -> bool:
    """
    Checks if preset with given name exists.

    Args:
        name: Preset name

    Returns:
        True if preset file exists
    """
    return get_preset_path(name).exists()


# ============================================================================
# LOAD/SAVE OPERATIONS
# ============================================================================

def load_preset(name: str) -> Optional["Preset"]:
    """
    Loads preset from file.

    Args:
        name: Preset name

    Returns:
        Preset object or None if not found
    """
    from .preset_model import Preset, CategoryConfig, SyndataSettings
    from .txt_preset_parser import parse_preset_file, PresetData

    preset_path = get_preset_path(name)

    if not preset_path.exists():
        log(f"Preset not found: {preset_path}", "WARNING")
        return None

    try:
        # Parse txt file
        data: PresetData = parse_preset_file(preset_path)

        # Convert to Preset model
        # Force is_builtin=True for built-in presets by well-known name.
        from .preset_defaults import is_builtin_preset_name
        is_builtin = bool(data.is_builtin) or is_builtin_preset_name(name)
        preset = Preset(
            name=data.name if data.name != "Unnamed" else name,
            base_args=data.base_args,
            is_builtin=is_builtin,
        )

        # Parse metadata from raw_header
        preset.created, preset.modified, preset.description = _parse_metadata_from_header(data.raw_header)

        # Convert category blocks to CategoryConfig
        for block in data.categories:
            cat_name = block.category

            # Get or create category config
            if cat_name not in preset.categories:
                preset.categories[cat_name] = CategoryConfig(
                    name=cat_name,
                    filter_mode=block.filter_mode,
                )

            cat = preset.categories[cat_name]

            # Restore per-protocol advanced settings from syndata_dict (if available).
            if hasattr(block, 'syndata_dict') and block.syndata_dict:
                if block.protocol == "tcp":
                    base = cat.syndata_tcp.to_dict()
                    base.update(block.syndata_dict)
                    cat.syndata_tcp = SyndataSettings.from_dict(base)
                elif block.protocol == "udp":
                    base = cat.syndata_udp.to_dict()
                    base.update(block.syndata_dict)
                    cat.syndata_udp = SyndataSettings.from_dict(base)

            # Set args based on protocol
            if block.protocol == "tcp":
                cat.tcp_args = block.strategy_args
                cat.tcp_port = block.port
                cat.tcp_enabled = True
                # TCP filter_mode takes priority over UDP
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

            # Try UDP if TCP didn't work or is empty
            if cat.udp_args and cat.udp_args.strip():
                inferred_id = infer_strategy_id_from_args(
                    category_key=cat_name,
                    args=cat.udp_args,
                    protocol="udp"
                )
                if inferred_id != "none":
                    cat.strategy_id = inferred_id

        log(f"Loaded preset '{name}': {len(preset.categories)} categories", "DEBUG")
        return preset

    except Exception as e:
        log(f"Error loading preset '{name}': {e}", "ERROR")
        return None


def _parse_metadata_from_header(header: str) -> Tuple[str, str, str]:
    """
    Parses created/modified/description metadata from header comments.

    Args:
        header: Raw header string

    Returns:
        Tuple of (created, modified, description)
    """
    import re

    created = datetime.now().isoformat()
    modified = datetime.now().isoformat()
    description = ""

    for line in (header or "").split('\n'):
        created_match = re.match(r'#\s*Created:\s*(.+)', line, re.IGNORECASE)
        if created_match:
            created = created_match.group(1).strip()

        modified_match = re.match(r'#\s*Modified:\s*(.+)', line, re.IGNORECASE)
        if modified_match:
            modified = modified_match.group(1).strip()

        desc_match = re.match(r'#\s*Description:\s*(.*)', line, re.IGNORECASE)
        if desc_match:
            description = desc_match.group(1).strip()

    return created, modified, description


def _parse_timestamps_from_header(header: str) -> Tuple[str, str]:
    """Backward-compatible helper returning (created, modified) only."""
    created, modified, _desc = _parse_metadata_from_header(header)
    return created, modified


def save_preset(preset: "Preset") -> bool:
    """
    Saves preset to file.

    Uses atomic write (temp file + rename) for safety.

    Args:
        preset: Preset object to save

    Returns:
        True if successful
    """
    from .txt_preset_parser import PresetData, CategoryBlock, generate_preset_file

    # ЗАЩИТА: Cannot save built-in presets (default.txt и другие)
    if preset.is_builtin:
        log(f"Cannot save built-in preset '{preset.name}' - it's read-only", "WARNING")
        return False

    preset_path = get_preset_path(preset.name)

    try:
        # Convert Preset to PresetData
        data = PresetData(
            name=preset.name,
            base_args=preset.base_args,
            is_builtin=preset.is_builtin,
        )

        # Build raw header
        data.raw_header = f"""# Preset: {preset.name}
# Created: {preset.created}
# Modified: {datetime.now().isoformat()}
# Description: {preset.description}"""

        # Convert categories to CategoryBlocks
        for cat_name, cat in preset.categories.items():
            # TCP block
            if cat.tcp_enabled and cat.has_tcp():
                from .base_filter import build_category_base_filter_lines
                base_filter_lines = build_category_base_filter_lines(cat_name, cat.filter_mode)

                args_lines = list(base_filter_lines)
                if not args_lines:
                    filter_file_relative = cat.get_hostlist_file() if cat.filter_mode == "hostlist" else cat.get_ipset_file()
                    filter_file = os.path.normpath(os.path.join(_get_main_directory(), filter_file_relative))
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

            # UDP block
            if cat.udp_enabled and cat.has_udp():
                from .base_filter import build_category_base_filter_lines
                base_filter_lines = build_category_base_filter_lines(cat_name, cat.filter_mode)

                args_lines = list(base_filter_lines)
                if not args_lines:
                    filter_file_relative = cat.get_ipset_file() if cat.filter_mode == "ipset" else cat.get_hostlist_file()
                    filter_file = os.path.normpath(os.path.join(_get_main_directory(), filter_file_relative))
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

        # Write file
        success = generate_preset_file(data, preset_path, atomic=True)

        if success:
            log(f"Saved preset '{preset.name}' to {preset_path}", "DEBUG")
        else:
            log(f"Failed to save preset '{preset.name}'", "ERROR")

        return success

    except PermissionError as e:
        log(f"Cannot write preset file (locked by winws2?): {e}", "ERROR")
        raise
    except Exception as e:
        log(f"Error saving preset '{preset.name}': {e}", "ERROR")
        return False


# ============================================================================
# DELETE/RENAME OPERATIONS
# ============================================================================

def delete_preset(name: str) -> bool:
    """
    Deletes preset file.

    Cannot delete built-in presets (is_builtin=True).

    Args:
        name: Preset name

    Returns:
        True if deleted successfully
    """
    # Check if preset is builtin
    preset = load_preset(name)
    if preset and preset.is_builtin:
        log(f"Cannot delete built-in preset '{name}'", "WARNING")
        return False

    preset_path = get_preset_path(name)

    if not preset_path.exists():
        log(f"Cannot delete: preset '{name}' not found", "WARNING")
        return False

    try:
        preset_path.unlink()
        log(f"Deleted preset '{name}'", "DEBUG")
        return True
    except Exception as e:
        log(f"Error deleting preset '{name}': {e}", "ERROR")
        return False


def rename_preset(old_name: str, new_name: str) -> bool:
    """
    Renames preset file.

    Cannot rename built-in presets (is_builtin=True).

    Args:
        old_name: Current preset name
        new_name: New preset name

    Returns:
        True if renamed successfully
    """
    # Check if preset is builtin
    preset = load_preset(old_name)
    if preset and preset.is_builtin:
        log(f"Cannot rename built-in preset '{old_name}'", "WARNING")
        return False

    old_path = get_preset_path(old_name)
    new_path = get_preset_path(new_name)

    if not old_path.exists():
        log(f"Cannot rename: preset '{old_name}' not found", "WARNING")
        return False

    if new_path.exists():
        log(f"Cannot rename: preset '{new_name}' already exists", "WARNING")
        return False

    try:
        # We already loaded preset above, just update name
        if preset is None:
            return False

        preset.name = new_name
        preset.touch()

        if save_preset(preset):
            # Delete old file
            old_path.unlink()
            log(f"Renamed preset '{old_name}' to '{new_name}'", "DEBUG")
            return True
        else:
            return False

    except Exception as e:
        log(f"Error renaming preset: {e}", "ERROR")
        return False


# ============================================================================
# ACTIVE PRESET OPERATIONS
# ============================================================================

def get_active_preset_name() -> Optional[str]:
    """
    Gets name of currently active preset from registry.

    Returns:
        Active preset name or None if not set
    """
    try:
        import winreg
        from config import REGISTRY_PATH

        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_PATH, 0, winreg.KEY_READ)
        try:
            name = winreg.QueryValueEx(key, "ActivePreset")[0]
            winreg.CloseKey(key)
            return name
        except FileNotFoundError:
            winreg.CloseKey(key)
            return None
    except Exception as e:
        log(f"Error reading active preset from registry: {e}", "DEBUG")
        return None


def set_active_preset_name(name: str) -> bool:
    """
    Sets name of active preset in registry.

    Args:
        name: Preset name

    Returns:
        True if saved successfully
    """
    try:
        import winreg
        from config import REGISTRY_PATH

        key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, REGISTRY_PATH)
        winreg.SetValueEx(key, "ActivePreset", 0, winreg.REG_SZ, name)
        winreg.CloseKey(key)
        log(f"Set active preset to '{name}'", "DEBUG")
        return True
    except Exception as e:
        log(f"Error saving active preset to registry: {e}", "ERROR")
        return False


# ============================================================================
# IMPORT/EXPORT OPERATIONS
# ============================================================================

def export_preset(name: str, dest_path: Path) -> bool:
    """
    Exports preset to external file.

    Cannot export built-in presets (is_builtin=True).

    Args:
        name: Preset name
        dest_path: Destination path

    Returns:
        True if exported successfully
    """
    # Check if preset is builtin
    preset = load_preset(name)
    if preset and preset.is_builtin:
        log(f"Cannot export built-in preset '{name}'", "WARNING")
        return False

    preset_path = get_preset_path(name)

    if not preset_path.exists():
        log(f"Cannot export: preset '{name}' not found", "WARNING")
        return False

    try:
        shutil.copy2(preset_path, dest_path)
        log(f"Exported preset '{name}' to {dest_path}", "DEBUG")
        return True
    except Exception as e:
        log(f"Error exporting preset: {e}", "ERROR")
        return False


def import_preset(src_path: Path, name: Optional[str] = None) -> bool:
    """
    Imports preset from external file.

    Args:
        src_path: Source file path
        name: Optional name for imported preset (uses filename if None)

    Returns:
        True if imported successfully
    """
    src_path = Path(src_path)

    if not src_path.exists():
        log(f"Cannot import: file '{src_path}' not found", "WARNING")
        return False

    # Determine name
    if name is None:
        name = src_path.stem

    # Check for existing
    if preset_exists(name):
        log(f"Cannot import: preset '{name}' already exists", "WARNING")
        return False

    try:
        dest_path = get_preset_path(name)
        shutil.copy2(src_path, dest_path)
        log(f"Imported preset '{name}' from {src_path}", "DEBUG")
        return True
    except Exception as e:
        log(f"Error importing preset: {e}", "ERROR")
        return False


def duplicate_preset(name: str, new_name: str) -> bool:
    """
    Creates a copy of preset with new name.

    Args:
        name: Source preset name
        new_name: Name for the copy

    Returns:
        True if duplicated successfully
    """
    if not preset_exists(name):
        log(f"Cannot duplicate: preset '{name}' not found", "WARNING")
        return False

    if preset_exists(new_name):
        log(f"Cannot duplicate: preset '{new_name}' already exists", "WARNING")
        return False

    try:
        preset = load_preset(name)
        if preset is None:
            return False

        preset.name = new_name
        preset.created = datetime.now().isoformat()
        preset.modified = datetime.now().isoformat()
        preset.is_builtin = False  # Copies are never builtin

        return save_preset(preset)

    except Exception as e:
        log(f"Error duplicating preset: {e}", "ERROR")
        return False
