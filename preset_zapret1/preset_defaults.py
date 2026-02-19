# preset_zapret1/preset_defaults.py
"""Builtin preset templates for Zapret 1.

Template sync flow:
  1. Installer copies builtin_presets/*.txt → presets_v1_template/  (production)
  2. _seed_v1_templates_from_repo() copies the same in dev mode
  3. ensure_v1_templates_copied_to_presets() copies missing → presets_v1/
  4. ensure_default_preset_exists_v1() orchestrates all of the above
"""

import os
import shutil
import sys
from pathlib import Path
from typing import Optional

from log import log

_BUILTIN_DIR = Path(__file__).resolve().parent / "builtin_presets"

# Fallback template if builtin file is missing (e.g. PyInstaller, broken install)
_DEFAULT_TEMPLATE_CONTENT = """\
# Preset: Default
# Created: 2026-01-01T00:00:00
# IconColor: #60cdff
# Description: Default Zapret 1 preset

--wf-tcp=443
--wf-udp=443
"""


def _get_v1_templates_dir() -> Path:
    """Returns the presets_v1_template/ directory path."""
    try:
        from config import get_zapret_presets_v1_template_dir
        return Path(get_zapret_presets_v1_template_dir())
    except Exception:
        appdata = (os.environ.get("APPDATA") or "").strip()
        if appdata:
            return Path(appdata) / "zapret" / "presets_v1_template"
        return Path.cwd() / "presets_v1_template"


def _load_v1_templates_from_disk() -> dict[str, Path]:
    """Reads *.txt from presets_v1_template/, returns {name: path}."""
    templates: dict[str, Path] = {}
    tpl_dir = _get_v1_templates_dir()
    try:
        if tpl_dir.is_dir():
            for f in tpl_dir.glob("*.txt"):
                if f.is_file() and not f.name.startswith("_"):
                    templates[f.stem] = f
    except Exception as e:
        log(f"Error reading V1 templates dir: {e}", "DEBUG")
    return templates


def _seed_v1_templates_from_repo() -> int:
    """Dev-mode: copy missing builtin_presets/*.txt → presets_v1_template/.

    Only runs when NOT frozen (i.e. running from source).
    Returns number of files copied.
    """
    if getattr(sys, "frozen", False):
        return 0

    if not _BUILTIN_DIR.is_dir():
        return 0

    tpl_dir = _get_v1_templates_dir()
    try:
        tpl_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        log(f"Cannot create V1 templates dir: {e}", "ERROR")
        return 0

    copied = 0
    try:
        for src in _BUILTIN_DIR.glob("*.txt"):
            if not src.is_file() or src.name.startswith("_"):
                continue
            dest = tpl_dir / src.name
            if not dest.exists():
                try:
                    shutil.copy2(str(src), str(dest))
                    copied += 1
                except Exception as e:
                    log(f"Failed to seed V1 template {src.name}: {e}", "DEBUG")
    except Exception as e:
        log(f"Error seeding V1 templates from repo: {e}", "ERROR")

    if copied:
        log(f"Seeded {copied} V1 templates from builtin_presets/ to {tpl_dir}", "DEBUG")
    return copied


def ensure_v1_templates_copied_to_presets() -> int:
    """Copy missing templates from presets_v1_template/ → presets_v1/.

    Only copies files that do NOT already exist in presets_v1/.
    Returns number of files copied.
    """
    from .preset_storage import get_presets_dir_v1

    templates = _load_v1_templates_from_disk()
    if not templates:
        return 0

    presets_dir = get_presets_dir_v1()
    copied = 0
    for name, src_path in templates.items():
        dest = presets_dir / f"{name}.txt"
        if not dest.exists():
            try:
                shutil.copy2(str(src_path), str(dest))
                copied += 1
            except Exception as e:
                log(f"Failed to copy V1 template '{name}' to presets: {e}", "DEBUG")

    if copied:
        log(f"Copied {copied} V1 templates to {presets_dir}", "DEBUG")
    return copied


def get_builtin_preset_content_v1(name: str) -> Optional[str]:
    """Returns content of a builtin preset template by name."""
    try:
        path = _BUILTIN_DIR / f"{name}.txt"
        if path.exists():
            return path.read_text(encoding="utf-8")
    except Exception:
        pass
    # Try case-insensitive
    try:
        if _BUILTIN_DIR.is_dir():
            for f in _BUILTIN_DIR.glob("*.txt"):
                if f.stem.lower() == name.lower():
                    return f.read_text(encoding="utf-8")
    except Exception:
        pass
    # Self-healing: return hardcoded default if file missing
    if name.lower() == "default":
        return _DEFAULT_TEMPLATE_CONTENT
    return None


def get_default_builtin_preset_name_v1() -> Optional[str]:
    """Returns name of the default builtin preset."""
    try:
        path = _BUILTIN_DIR / "Default.txt"
        if path.exists():
            return "Default"
        for f in _BUILTIN_DIR.glob("*.txt"):
            if f.is_file():
                return f.stem
    except Exception:
        pass
    return None


def get_all_builtin_preset_names_v1() -> list[str]:
    """Returns sorted list of all builtin preset names (excluding Default)."""
    names: list[str] = []
    try:
        if _BUILTIN_DIR.is_dir():
            for f in _BUILTIN_DIR.glob("*.txt"):
                if f.is_file() and f.stem.lower() != "default":
                    names.append(f.stem)
    except Exception:
        pass
    names.sort(key=lambda s: s.lower())
    return names


def ensure_default_preset_exists_v1() -> bool:
    """Ensures presets_v1/ is populated and Default preset exists.

    Flow:
      1. Dev mode: seed templates from builtin_presets/ → presets_v1_template/
      2. Copy missing templates from presets_v1_template/ → presets_v1/
      3. If Default still missing, create from embedded fallback

    Returns True if Default preset exists or was created successfully.
    """
    # Step 1: dev-mode seeding
    _seed_v1_templates_from_repo()

    # Step 2: copy templates to user presets
    ensure_v1_templates_copied_to_presets()

    # Step 3: check Default exists
    from .preset_storage import preset_exists_v1
    from .preset_manager import PresetManagerV1

    if preset_exists_v1("Default"):
        return True

    # Fallback: create Default from embedded content
    try:
        manager = PresetManagerV1()
        preset = manager.create_default_preset("Default")
        return preset is not None
    except Exception:
        return False
