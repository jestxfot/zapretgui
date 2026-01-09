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

def ensure_default_preset_exists() -> bool:
    """
    Ensures that a default preset exists for direct_zapret2 mode.

    Checks if preset-zapret2.txt exists. If not:
    1. Generates default preset from code constant (no external file dependency)
    2. Also creates presets/Default.txt for the presets list

    This function should be called during application startup
    when running in direct_zapret2 mode.

    Returns:
        True if preset exists or was created successfully
    """
    from log import log
    from pathlib import Path
    from .preset_defaults import DEFAULT_PRESET_CONTENT

    active_path = get_active_preset_path()

    # Check if active preset file already exists
    if active_path.exists():
        log("Active preset file already exists", "DEBUG")
        return True

    log("Active preset file not found, creating from code template...", "INFO")

    try:
        # Ensure presets directory exists
        presets_dir = get_presets_dir()
        presets_dir.mkdir(parents=True, exist_ok=True)

        # Write default preset from code constant to preset-zapret2.txt (active preset)
        active_path.write_text(DEFAULT_PRESET_CONTENT, encoding='utf-8')
        log(f"Created active preset from code template at {active_path}", "DEBUG")

        # Write to presets/Default.txt (for presets list)
        default_preset_path = presets_dir / "Default.txt"
        if not default_preset_path.exists():
            default_preset_path.write_text(DEFAULT_PRESET_CONTENT, encoding='utf-8')
            log(f"Created Default.txt from code template at {default_preset_path}", "DEBUG")

        # Set active preset name in registry
        set_active_preset_name("Default")

        log("Default preset created from code template successfully", "INFO")
        return True

    except Exception as e:
        log(f"Error creating default preset: {e}", "ERROR")
        import traceback
        log(traceback.format_exc(), "DEBUG")
        return False


def restore_default_preset() -> bool:
    """
    Restores Default.txt preset from the built-in code template.

    This function can be used to:
    1. Fix a corrupted Default.txt
    2. Reset Default.txt to factory settings
    3. Recover from accidental modifications

    Returns:
        True if restore was successful, False otherwise
    """
    from log import log
    from .preset_defaults import DEFAULT_PRESET_CONTENT

    try:
        # Ensure presets directory exists
        presets_dir = get_presets_dir()
        presets_dir.mkdir(parents=True, exist_ok=True)

        # Path to Default.txt in presets/
        default_preset_path = presets_dir / "Default.txt"

        # Overwrite from code constant
        default_preset_path.write_text(DEFAULT_PRESET_CONTENT, encoding='utf-8')
        log(f"Restored Default.txt from code template at {default_preset_path}", "SUCCESS")

        # If Default is currently active, also update preset-zapret2.txt
        active_name = get_active_preset_name()
        if active_name == "Default":
            active_path = get_active_preset_path()
            active_path.write_text(DEFAULT_PRESET_CONTENT, encoding='utf-8')
            log(f"Also updated active preset at {active_path}", "SUCCESS")

        return True

    except Exception as e:
        log(f"Error restoring default preset: {e}", "ERROR")
        import traceback
        log(traceback.format_exc(), "DEBUG")
        return False


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
    "ensure_default_preset_exists",
    "restore_default_preset",
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
