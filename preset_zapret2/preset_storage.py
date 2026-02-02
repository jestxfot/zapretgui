from __future__ import annotations

# presets/preset_storage.py
"""Storage layer for preset system.

Handles reading/writing preset files to disk.

Presets are stored in a stable per-user directory (Windows):
  %APPDATA%\\zapret\\presets

This avoids reliance on the installation folder location.

Active preset name is stored in an INI file:
  %APPDATA%\\zapret\\zapret2_active_preset.ini
"""

import configparser
import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple, TYPE_CHECKING

from log import log

if TYPE_CHECKING:
    from .preset_model import Preset

# Lazy imports to avoid circular dependencies
# NOTE: APP_CORE_PATH is where the app is installed / located (where Zapret.exe lives).
_APP_CORE_PATH: Optional[str] = None
_PRESETS_ROOT_PATH: Optional[str] = None
_MAIN_DIRECTORY: Optional[str] = None

_ACTIVE_PRESET_SECTION = "direct_zapret2"
_ACTIVE_PRESET_KEY = "ActivePreset"
_ACTIVE_PRESET_INI_NAME = "zapret2_active_preset.ini"


def _get_app_core_path() -> str:
    """Lazily gets the app core path (APP_CORE_PATH) to avoid import cycles."""
    global _APP_CORE_PATH
    if _APP_CORE_PATH is None:
        from config import APP_CORE_PATH

        _APP_CORE_PATH = APP_CORE_PATH
    return _APP_CORE_PATH


def _get_presets_root_path() -> str:
    """Returns the stable presets root (prefer %APPDATA%\\zapret\\presets)."""
    global _PRESETS_ROOT_PATH
    if _PRESETS_ROOT_PATH is None:
        try:
            from config import get_zapret_presets_dir

            p = (get_zapret_presets_dir() or "").strip()
            _PRESETS_ROOT_PATH = p
        except Exception:
            _PRESETS_ROOT_PATH = ""

        if not _PRESETS_ROOT_PATH:
            # Fallback for non-Windows/dev environments.
            _PRESETS_ROOT_PATH = str(Path(_get_app_core_path()) / "presets")
    return _PRESETS_ROOT_PATH


def _get_main_directory() -> str:
    """Lazily gets MAIN_DIRECTORY to avoid import cycles."""
    global _MAIN_DIRECTORY
    if _MAIN_DIRECTORY is None:
        from config import MAIN_DIRECTORY
        _MAIN_DIRECTORY = MAIN_DIRECTORY
    return _MAIN_DIRECTORY


def get_active_preset_state_path() -> Path:
    """Returns path to the active preset state INI file.

    Primary target (Windows): %APPDATA%\\zapret\\zapret2_active_preset.ini
    Fallback (non-Windows/dev): <userdata>/zapret2_active_preset.ini
    """
    try:
        from config import get_zapret_userdata_dir

        base = (get_zapret_userdata_dir() or "").strip()
        if base:
            return Path(base) / _ACTIVE_PRESET_INI_NAME
    except Exception:
        pass

    appdata = (os.environ.get("APPDATA") or "").strip()
    if appdata:
        return Path(appdata) / "zapret" / _ACTIVE_PRESET_INI_NAME

    return Path(_get_app_core_path()) / _ACTIVE_PRESET_INI_NAME


# ============================================================================
# PATH FUNCTIONS
# ============================================================================

def get_presets_dir() -> Path:
    """
    Returns path to presets directory.

    Creates directory if it doesn't exist.

    Returns:
        Path to %APPDATA%/zapret/presets/
    """
    presets_dir = Path(_get_presets_root_path())
    presets_dir.mkdir(parents=True, exist_ok=True)
    return presets_dir


def get_builtin_overrides_dir() -> Path:
    """
    Returns path to built-in presets overrides directory.

    Built-in presets (Default/Gaming/...) are stored as in-code templates and are read-only.
    User changes to a built-in preset are persisted as an override file here.

    Returns:
        Path to %APPDATA%/zapret/presets/_builtin_overrides/
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
        Path to {APP_CORE_PATH}/preset-zapret2.txt
    """
    return Path(_get_app_core_path()) / "preset-zapret2.txt"


def get_user_settings_path() -> Path:
    """
    Returns path to user settings file.

    This stores user-specific settings like active preset name.

    Returns:
        Path to %APPDATA%/zapret/presets/user_settings.json
    """
    return get_presets_dir() / "user_settings.json"


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

    presets: set[str] = set()

    if presets_dir.exists():
        for f in presets_dir.glob("*.txt"):
            if f.is_file():
                # Do not treat the active runtime file as a user preset.
                if f.stem.lower() == "preset-zapret2":
                    continue
                presets.add(f.stem)

    # Virtual built-ins must be visible even if
    # `%APPDATA%/zapret/presets/{Name}.txt` does not exist.
    try:
        from .preset_defaults import get_builtin_preset_names
        presets.update(get_builtin_preset_names())
    except Exception:
        pass

    return sorted(presets, key=lambda s: s.lower())


def preset_exists(name: str) -> bool:
    """
    Checks if preset with given name exists.

    Args:
        name: Preset name

    Returns:
        True if preset file exists
    """
    try:
        from .preset_defaults import is_builtin_preset_name
        if is_builtin_preset_name(name):
            return True
    except Exception:
        pass
    return get_preset_path(name).exists()


# ============================================================================
# LOAD/SAVE OPERATIONS
# ============================================================================

def load_preset(name: str) -> Optional[Preset]:
    """
    Loads preset from file.

    Args:
        name: Preset name

    Returns:
        Preset object or None if not found
    """
    from .preset_model import Preset, CategoryConfig, SyndataSettings
    from .txt_preset_parser import PresetData, parse_preset_content, parse_preset_file

    preset_path = get_preset_path(name)

    data: PresetData
    try:
        from .preset_defaults import get_builtin_preset_content, is_builtin_preset_name
        if is_builtin_preset_name(name):
            content = get_builtin_preset_content(name)
            if content is None:
                return None
            data = parse_preset_content(content)
            data.name = name
            data.active_preset = name
            data.is_builtin = True
        else:
            if not preset_path.exists():
                log(f"Preset not found: {preset_path}", "WARNING")
                return None
            data = parse_preset_file(preset_path)
    except Exception:
        if not preset_path.exists():
            log(f"Preset not found: {preset_path}", "WARNING")
            return None
        data = parse_preset_file(preset_path)

    try:
        # `data` is ready (from disk or virtual template)

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


def save_preset(preset: Preset) -> bool:
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
    Gets name of currently active preset from the INI file.

    Returns:
        Active preset name or None if not set
    """
    path = get_active_preset_state_path()
    try:
        if not path.exists():
            return None

        cfg = configparser.ConfigParser()
        cfg.read(path, encoding="utf-8")
        value = cfg.get(_ACTIVE_PRESET_SECTION, _ACTIVE_PRESET_KEY, fallback="").strip()
        return value or None
    except Exception as e:
        log(f"Error reading active preset from ini: {e}", "DEBUG")
        return None


def set_active_preset_name(name: str) -> bool:
    """
    Sets name of active preset in the INI file.

    Args:
        name: Preset name

    Returns:
        True if saved successfully
    """
    path = get_active_preset_state_path()
    value = (name or "").strip()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)

        cfg = configparser.ConfigParser()
        if path.exists():
            cfg.read(path, encoding="utf-8")

        if _ACTIVE_PRESET_SECTION not in cfg:
            cfg[_ACTIVE_PRESET_SECTION] = {}

        if value:
            cfg[_ACTIVE_PRESET_SECTION][_ACTIVE_PRESET_KEY] = value
        else:
            try:
                cfg.remove_option(_ACTIVE_PRESET_SECTION, _ACTIVE_PRESET_KEY)
            except Exception:
                pass

        # Atomic write
        fd, tmp_name = tempfile.mkstemp(
            prefix=f"{path.stem}_",
            suffix=".tmp",
            dir=str(path.parent),
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
                cfg.write(f)
                f.flush()
                try:
                    os.fsync(f.fileno())
                except Exception:
                    pass
            os.replace(tmp_name, str(path))
        finally:
            try:
                if os.path.exists(tmp_name):
                    os.unlink(tmp_name)
            except Exception:
                pass

        log(f"Set active preset to '{value}'", "DEBUG")
        return True
    except Exception as e:
        log(f"Error saving active preset to ini: {e}", "ERROR")
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

    # Check for existing (includes virtual built-ins)
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
