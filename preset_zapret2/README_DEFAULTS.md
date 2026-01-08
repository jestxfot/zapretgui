# Default Preset Implementation

## Overview

The default preset is now stored as a Python constant in code, eliminating external file dependencies and providing built-in recovery mechanisms.

## Files

### `preset_defaults.py`
Contains the `DEFAULT_PRESET_CONTENT` constant with the built-in default preset template.

**Content includes:**
- Base arguments (lua-init, wf-tcp/udp filters)
- Category: youtube (TCP)
- Category: discord (TCP)
- Category: discord_voice (UDP/STUN)

### `__init__.py`
Exports two functions for working with default presets:

#### `ensure_default_preset_exists() -> bool`
Called during application startup to ensure default preset exists.

**Behavior:**
1. Checks if `preset-zapret2.txt` exists
2. If not, creates it from `DEFAULT_PRESET_CONTENT`
3. Also creates `presets/Default.txt` for preset list
4. Sets active preset name in registry

**Returns:** `True` if preset exists or was created successfully

#### `restore_default_preset() -> bool`
Restores Default.txt from the built-in code template.

**Use cases:**
- Fix corrupted Default.txt
- Reset Default.txt to factory settings
- Recover from accidental modifications

**Behavior:**
1. Overwrites `presets/Default.txt` with `DEFAULT_PRESET_CONTENT`
2. If Default is currently active, also updates `preset-zapret2.txt`
3. Logs all operations

**Returns:** `True` if restore was successful

## Usage Examples

### Import
```python
from preset_zapret2 import ensure_default_preset_exists, restore_default_preset
from preset_zapret2.preset_defaults import DEFAULT_PRESET_CONTENT
```

### Ensure Default Exists (Startup)
```python
# Called during app initialization
if not ensure_default_preset_exists():
    log("Failed to create default preset", "ERROR")
```

### Restore Default
```python
# User clicks "Restore Default" button
if restore_default_preset():
    QMessageBox.information(self, "Success", "Default preset restored successfully")
else:
    QMessageBox.critical(self, "Error", "Failed to restore default preset")
```

### Access Template Content
```python
# Get the default template content programmatically
from preset_zapret2.preset_defaults import DEFAULT_PRESET_CONTENT

print(f"Default preset size: {len(DEFAULT_PRESET_CONTENT)} bytes")
print(DEFAULT_PRESET_CONTENT)
```

## Benefits

1. **No external file dependency** - default.txt is embedded in code
2. **Always recoverable** - can restore from code at any time
3. **Version controlled** - changes to default tracked in git
4. **Corruption-proof** - always have a valid template
5. **Deployment friendly** - no need to ship default.txt separately

## Migration Notes

### Before
```python
# Old implementation read from file
default_template = Path(__file__).parent / "default.txt"
shutil.copy2(default_template, active_path)
```

### After
```python
# New implementation uses code constant
from .preset_defaults import DEFAULT_PRESET_CONTENT
active_path.write_text(DEFAULT_PRESET_CONTENT, encoding='utf-8')
```

## Maintaining Default Content

To update the default preset template:

1. Edit `DEFAULT_PRESET_CONTENT` in `preset_defaults.py`
2. Commit changes to version control
3. Users can restore to new default using `restore_default_preset()`

**Note:** The old `default.txt` file can be kept as a backup reference but is no longer used by the code.
