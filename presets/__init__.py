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

def ensure_default_preset_exists() -> bool:
    """
    Ensures that a default preset exists for direct_zapret2 mode.

    Checks if preset-zapret2.txt exists. If not:
    1. Copies the built-in default.txt template to preset-zapret2.txt
    2. Also copies to presets/Default.txt for the presets list

    This function should be called during application startup
    when running in direct_zapret2 mode.

    Returns:
        True if preset exists or was created successfully
    """
    from log import log
    import shutil
    from pathlib import Path

    active_path = get_active_preset_path()

    # Check if active preset file already exists
    if active_path.exists():
        log("Active preset file already exists", "DEBUG")
        return True

    log("Active preset file not found, creating from default template...", "INFO")

    try:
        # Path to built-in default.txt template
        default_template = Path(__file__).parent / "default.txt"

        if not default_template.exists():
            log(f"Default template not found at {default_template}", "ERROR")
            return False

        # Ensure presets directory exists
        presets_dir = get_presets_dir()
        presets_dir.mkdir(parents=True, exist_ok=True)

        # Copy to preset-zapret2.txt (active preset)
        shutil.copy2(default_template, active_path)
        log(f"Copied default template to {active_path}", "DEBUG")

        # Copy to presets/Default.txt (for presets list)
        default_preset_path = presets_dir / "Default.txt"
        if not default_preset_path.exists():
            shutil.copy2(default_template, default_preset_path)
            log(f"Copied default template to {default_preset_path}", "DEBUG")

        # Set active preset name in registry
        set_active_preset_name("Default")

        log("Default preset created from template successfully", "INFO")
        return True

    except Exception as e:
        log(f"Error creating default preset: {e}", "ERROR")
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
]
