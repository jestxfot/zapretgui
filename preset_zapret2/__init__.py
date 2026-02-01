# presets/__init__.py
"""
Preset system for direct_zapret2 mode.

Presets are stored as txt files in {PROGRAMDATA_PATH}/presets/.
Each preset contains:
- Metadata (name, created, modified)
- Base arguments (lua-init, wf-*, blobs)
- Category configurations (youtube, discord, etc.)

Switching presets = copying preset file to preset-zapret2.txt + DPI reload.

Usage:
    from presets import PresetManager, Preset

    manager = PresetManager()

    # List available presets
    presets = manager.list_presets()

    # Switch to a preset
    manager.switch_preset("Gaming")

    # Get current preset
    preset = manager.get_active_preset()

    # Create new preset from current configuration
    manager.create_preset_from_current("My Backup")

    # Edit preset
    preset = manager.load_preset("Default")
    preset.categories["youtube"].tcp_args = "--lua-desync=multisplit:pos=1"
    manager.save_preset(preset)

Low-level API:
    from presets import (
        get_presets_dir,
        list_presets,
        load_preset,
        save_preset,
        delete_preset,
        rename_preset,
    )

Parser API (for txt files):
    from presets.txt_preset_parser import (
        parse_preset_file,
        generate_preset_file,
        PresetData,
        CategoryBlock,
    )
"""

# Model classes
from .preset_model import CategoryConfig, Preset, SyndataSettings, validate_preset

# Storage functions (low-level)
from .preset_storage import (
    delete_preset,
    duplicate_preset,
    export_preset,
    get_active_preset_name,
    get_active_preset_path,
    get_preset_path,
    get_presets_dir,
    get_user_settings_path,
    import_preset,
    list_presets,
    load_preset,
    preset_exists,
    rename_preset,
    save_preset,
    set_active_preset_name,
)

# High-level manager
from .preset_manager import PresetManager

# Txt parser (for advanced usage)
from .txt_preset_parser import (
    CategoryBlock,
    PresetData,
    extract_category_from_args,
    extract_protocol_and_port,
    extract_strategy_args,
    invalidate_category_inference_cache,
    generate_preset_content,
    generate_preset_file,
    parse_preset_content,
    parse_preset_file,
    update_category_in_preset,
)

# Default settings parser
from .preset_defaults import (
    get_default_category_settings,
    get_category_default_filter_mode,
    get_category_default_syndata,
    parse_syndata_from_args,
)

# Strategy inference (for loading presets)
from .strategy_inference import (
    infer_strategy_id_from_args,
    infer_strategy_ids_batch,
    normalize_args,
)


def _atomic_write_text(path, content: str, *, encoding: str = "utf-8") -> None:
    """Writes text via temp file + replace to avoid partial files."""
    import os
    import tempfile
    from pathlib import Path

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    data = (content or "").replace("\r\n", "\n").replace("\r", "\n")
    if not data.endswith("\n"):
        data += "\n"

    fd, tmp_name = tempfile.mkstemp(
        prefix=f"{path.stem}_",
        suffix=".tmp",
        dir=str(path.parent),
    )
    try:
        with os.fdopen(fd, "w", encoding=encoding, newline="\n") as f:
            f.write(data)
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

def ensure_builtin_presets_exist() -> bool:
    """
    Ensures that built-in presets are available.

    Built-ins are treated as *virtual* presets loaded from packaged templates (and in-code fallbacks).
    We do not materialize them into `{PROGRAMDATA}/presets/*.txt` by default.


    Returns:
        True if presets exist or were created successfully.
    """
    from log import log

    try:
        # Keep presets dir present for user presets.
        presets_dir = get_presets_dir()
        presets_dir.mkdir(parents=True, exist_ok=True)

        # Built-in presets are *virtual* and are loaded from packaged templates
        # (and in-code fallbacks). We do not materialize them into presets/.
        migrate_builtin_overrides_to_visible_copies()
        return True

    except Exception as e:
        log(f"Error ensuring built-in presets: {e}", "ERROR")
        import traceback
        log(traceback.format_exc(), "DEBUG")
        return False


def migrate_builtin_overrides_to_visible_copies() -> bool:
    """
    Migrates legacy built-in overrides to visible user presets.

    Old behavior stored user edits of built-in presets (Default/Gaming) under
    `presets/_builtin_overrides/*.txt`. New UX stores them as normal presets
    (e.g. `Default (копия).txt`) so users clearly work with a copy, not the original.

    Returns:
        True if migration succeeded (or nothing to migrate), False on fatal error.
    """
    from log import log
    from .preset_defaults import BUILTIN_PRESET_TEMPLATES, get_builtin_copy_name
    from .preset_storage import get_builtin_override_path, get_preset_path, get_active_preset_path

    try:
        active_name = (get_active_preset_name() or "").strip()
        active_path = get_active_preset_path()

        for builtin_name in BUILTIN_PRESET_TEMPLATES.keys():
            override_path = get_builtin_override_path(builtin_name)
            if not override_path.exists():
                continue

            copy_name = get_builtin_copy_name(builtin_name)
            if not copy_name:
                continue

            dest_path = get_preset_path(copy_name)
            try:
                content = override_path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                content = ""

            lines = content.splitlines()
            out: list[str] = []
            saw_preset = False
            saw_active = False
            for raw in lines:
                stripped = raw.strip()
                if stripped.lower().startswith("# preset:"):
                    out.append(f"# Preset: {copy_name}")
                    saw_preset = True
                    continue
                if stripped.lower().startswith("# activepreset:"):
                    out.append(f"# ActivePreset: {copy_name}")
                    saw_active = True
                    continue
                out.append(raw)

            if not saw_preset:
                out.insert(0, f"# Preset: {copy_name}")
            if not saw_active:
                insert_idx = 1 if out and out[0].strip().lower().startswith("# preset:") else 0
                out.insert(insert_idx, f"# ActivePreset: {copy_name}")

            dest_path.parent.mkdir(parents=True, exist_ok=True)
            dest_path.write_text("\n".join(out) + "\n", encoding="utf-8")

            try:
                override_path.unlink()
            except Exception:
                pass

            log(f"Migrated built-in override '{builtin_name}' -> '{copy_name}'", "INFO")

            # If this built-in was active, switch active name to the visible copy
            # and update the active file header markers.
            if active_name and active_name.lower() == builtin_name.lower():
                set_active_preset_name(copy_name)
                if active_path.exists():
                    try:
                        active_content = active_path.read_text(encoding="utf-8", errors="replace")
                        a_lines = active_content.splitlines()
                        a_out: list[str] = []
                        a_saw_preset = False
                        a_saw_active = False
                        for raw in a_lines:
                            stripped = raw.strip()
                            if stripped.lower().startswith("# preset:"):
                                a_out.append(f"# Preset: {copy_name}")
                                a_saw_preset = True
                                continue
                            if stripped.lower().startswith("# activepreset:"):
                                a_out.append(f"# ActivePreset: {copy_name}")
                                a_saw_active = True
                                continue
                            a_out.append(raw)
                        if not a_saw_preset:
                            a_out.insert(0, f"# Preset: {copy_name}")
                        if not a_saw_active:
                            insert_idx = 1 if a_out and a_out[0].strip().lower().startswith("# preset:") else 0
                            a_out.insert(insert_idx, f"# ActivePreset: {copy_name}")
                        active_path.write_text("\n".join(a_out) + "\n", encoding="utf-8")
                    except Exception:
                        pass

        return True
    except Exception as e:
        log(f"Error migrating built-in overrides: {e}", "DEBUG")
        return False


def ensure_default_preset_exists() -> bool:
    """
    Ensures that a default preset exists for direct_zapret2 mode.

    Checks if preset-zapret2.txt exists. If not:
    1. Generates default preset from built-in template `Default.txt`

    This function should be called during application startup
    when running in direct_zapret2 mode.

    Returns:
        True if preset exists or was created successfully
    """
    from log import log
    from .preset_defaults import get_builtin_preset_content

    active_path = get_active_preset_path()

    # Ensure built-in presets exist for presets list (even if active file exists).
    ensure_builtin_presets_exist()

    # Check if active preset file already exists
    if active_path.exists():
        log("Active preset file already exists", "DEBUG")
        return True

    log("Active preset file not found, creating from code template...", "INFO")

    try:
        # Write default preset template to preset-zapret2.txt (active preset)
        template = get_builtin_preset_content("Default")
        if not template:
            log(
                "Cannot create preset-zapret2.txt: built-in preset 'Default' is missing. "
                "Expected: <exe_dir>/preset_zapret2/builtin_presets/Default.txt",
                "ERROR",
            )
            return False
        _atomic_write_text(active_path, template, encoding="utf-8")
        log(f"Created active preset from code template at {active_path}", "DEBUG")

        # Set active preset name in registry
        set_active_preset_name("Default")

        log("Default preset created from code template successfully", "INFO")
        return True

    except Exception as e:
        log(f"Error creating default preset: {e}", "ERROR")
        import traceback
        log(traceback.format_exc(), "DEBUG")
        return False


def restore_builtin_preset(preset_name: str) -> bool:
    """
    Restores a built-in preset by rewriting the active file from the template.

    Returns:
        True if restore was successful, False otherwise
    """
    from log import log
    from .preset_defaults import get_builtin_preset_content, get_builtin_preset_canonical_name

    try:
        canonical = get_builtin_preset_canonical_name(preset_name)
        content = get_builtin_preset_content(preset_name)
        if not canonical or content is None:
            log(f"Unknown built-in preset '{preset_name}'", "ERROR")
            return False

        # If this preset is currently active, update preset-zapret2.txt
        active_name = (get_active_preset_name() or "").strip()
        if active_name and active_name.lower() == canonical.lower():
            active_path = get_active_preset_path()
            active_path.write_text(content, encoding="utf-8")
            log(f"Also updated active preset at {active_path}", "SUCCESS")
        else:
            log(
                f"Built-in preset '{canonical}' restored (template checked). "
                "It is not active, so preset-zapret2.txt was not changed.",
                "INFO",
            )

        return True

    except Exception as e:
        log(f"Error restoring built-in preset '{preset_name}': {e}", "ERROR")
        import traceback
        log(traceback.format_exc(), "DEBUG")
        return False


def restore_default_preset() -> bool:
    """
    Restores Default preset from the built-in template.

    This function can be used to:
    1. Fix a corrupted Default.txt
    2. Reset Default.txt to factory settings
    3. Recover from accidental modifications

    Returns:
        True if restore was successful, False otherwise
    """
    return restore_builtin_preset("Default")


def restore_gaming_preset() -> bool:
    """
    Restores Gaming.txt preset from the built-in code template.

    Returns:
        True if restore was successful, False otherwise
    """
    return restore_builtin_preset("Gaming")


__all__ = [
    # Model
    "Preset",
    "CategoryConfig",
    "SyndataSettings",
    "validate_preset",
    # Storage functions
    "get_presets_dir",
    "get_preset_path",
    "get_active_preset_path",
    "get_user_settings_path",
    "list_presets",
    "preset_exists",
    "load_preset",
    "save_preset",
    "delete_preset",
    "rename_preset",
    "duplicate_preset",
    "export_preset",
    "import_preset",
    "get_active_preset_name",
    "set_active_preset_name",
    # Manager
    "PresetManager",
    # Utility functions
    "ensure_builtin_presets_exist",
    "ensure_default_preset_exists",
    "restore_builtin_preset",
    "restore_default_preset",
    "restore_gaming_preset",
    "get_default_category_settings",
    "get_category_default_filter_mode",
    "get_category_default_syndata",
    "parse_syndata_from_args",
    # Parser
    "PresetData",
    "CategoryBlock",
    "parse_preset_file",
    "parse_preset_content",
    "generate_preset_file",
    "generate_preset_content",
    "extract_category_from_args",
    "extract_protocol_and_port",
    "extract_strategy_args",
    "update_category_in_preset",
    # Strategy inference
    "infer_strategy_id_from_args",
    "infer_strategy_ids_batch",
    "normalize_args",
]
