# preset_zapret1/preset_defaults.py
"""Builtin preset templates for Zapret 1.

Template sync flow:
  1. Templates live in %APPDATA%/zapret/presets_v1_template/
  2. ensure_v1_templates_copied_to_presets() copies missing → presets_v1/
  3. ensure_default_preset_exists_v1() guarantees Default exists
"""

import os
import re
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

_TEMPLATES_CACHE_V1: Optional[dict[str, str]] = None
_TEMPLATE_BY_KEY_V1: Optional[dict[str, str]] = None
_CANONICAL_NAME_BY_KEY_V1: Optional[dict[str, str]] = None


def _get_v1_templates_dir() -> Path:
    """Returns the presets_v1_template/ directory path."""
    try:
        from config import get_zapret_presets_v1_template_dir
        return Path(get_zapret_presets_v1_template_dir())
    except Exception:
        appdata = (os.environ.get("APPDATA") or "").strip()
        if appdata:
            return Path(appdata) / "zapret" / "presets_v1_template"
        return Path.home() / "AppData" / "Roaming" / "zapret" / "presets_v1_template"


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


def _normalize_template_header_v1(content: str, preset_name: str) -> str:
    """Ensures # Preset / # ActivePreset correspond to template filename."""
    name = str(preset_name or "").strip()
    text = (content or "").replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")

    header_end = 0
    for i, raw in enumerate(lines):
        stripped = raw.strip()
        if stripped and not stripped.startswith("#"):
            header_end = i
            break
    else:
        header_end = len(lines)

    header = lines[:header_end]
    body = lines[header_end:]

    out_header: list[str] = []
    saw_preset = False
    saw_active = False
    for raw in header:
        stripped = raw.strip().lower()
        if stripped.startswith("# preset:"):
            out_header.append(f"# Preset: {name}")
            saw_preset = True
            continue
        if stripped.startswith("# activepreset:"):
            out_header.append(f"# ActivePreset: {name}")
            saw_active = True
            continue
        out_header.append(raw.rstrip("\n"))

    if not saw_preset:
        out_header.insert(0, f"# Preset: {name}")
    if not saw_active:
        insert_idx = 1 if out_header and out_header[0].strip().lower().startswith("# preset:") else 0
        out_header.insert(insert_idx, f"# ActivePreset: {name}")

    return "\n".join(out_header + body).rstrip("\n") + "\n"


def _load_v1_template_contents_from_disk() -> dict[str, str]:
    """Reads normalized template contents from presets_v1_template/*.txt."""
    templates: dict[str, str] = {}
    for name, path in _load_v1_templates_from_disk().items():
        clean_name = str(name or "").strip()
        if not clean_name:
            continue
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        templates[clean_name] = _normalize_template_header_v1(content, clean_name)
    return templates


def invalidate_templates_cache_v1() -> None:
    global _TEMPLATES_CACHE_V1, _TEMPLATE_BY_KEY_V1, _CANONICAL_NAME_BY_KEY_V1
    _TEMPLATES_CACHE_V1 = None
    _TEMPLATE_BY_KEY_V1 = None
    _CANONICAL_NAME_BY_KEY_V1 = None


def _ensure_templates_loaded_v1() -> None:
    global _TEMPLATES_CACHE_V1, _TEMPLATE_BY_KEY_V1, _CANONICAL_NAME_BY_KEY_V1

    if _TEMPLATES_CACHE_V1 is None:
        templates = _load_v1_template_contents_from_disk()
        _TEMPLATES_CACHE_V1 = {k: templates[k] for k in sorted(templates.keys(), key=lambda s: s.lower())}
        _TEMPLATE_BY_KEY_V1 = {
            canonical.lower(): content for canonical, content in _TEMPLATES_CACHE_V1.items()
        }
        _CANONICAL_NAME_BY_KEY_V1 = {
            canonical.lower(): canonical for canonical in _TEMPLATES_CACHE_V1.keys()
        }
        return

    if _TEMPLATE_BY_KEY_V1 is None:
        _TEMPLATE_BY_KEY_V1 = {
            canonical.lower(): content for canonical, content in (_TEMPLATES_CACHE_V1 or {}).items()
        }
    if _CANONICAL_NAME_BY_KEY_V1 is None:
        _CANONICAL_NAME_BY_KEY_V1 = {
            canonical.lower(): canonical for canonical in (_TEMPLATES_CACHE_V1 or {}).keys()
        }


def get_template_content_v1(name: str) -> Optional[str]:
    """Returns template content from presets_v1_template/ by name (case-insensitive)."""
    _ensure_templates_loaded_v1()
    key = (name or "").strip().lower()
    if not key:
        return None
    return (_TEMPLATE_BY_KEY_V1 or {}).get(key)


def get_template_canonical_name_v1(name: str) -> Optional[str]:
    """Returns canonical template name from presets_v1_template/ (case-insensitive)."""
    _ensure_templates_loaded_v1()
    key = (name or "").strip().lower()
    if not key:
        return None
    return (_CANONICAL_NAME_BY_KEY_V1 or {}).get(key)


def get_default_template_name_v1() -> Optional[str]:
    """Returns default template name from presets_v1_template/ if available."""
    canonical = get_template_canonical_name_v1("Default")
    if canonical:
        return canonical
    _ensure_templates_loaded_v1()
    names = sorted((_TEMPLATES_CACHE_V1 or {}).keys(), key=lambda s: s.lower())
    return names[0] if names else None


def get_default_template_content_v1() -> Optional[str]:
    """Returns default template content from presets_v1_template/ if available."""
    name = get_default_template_name_v1()
    if not name:
        return None
    return get_template_content_v1(name)


def get_builtin_base_from_copy_name_v1(name: str) -> Optional[str]:
    """Returns canonical base template name for '(...копия N)' names."""
    raw = (name or "").strip()
    if not raw:
        return None

    copy_suffix_re = re.compile(r"\s+\(копия(?:\s+\d+)?\)\s*$", re.IGNORECASE)
    base = raw
    changed = False
    while True:
        stripped = copy_suffix_re.sub("", base).strip()
        if stripped == base:
            break
        base = stripped
        changed = True

    if not changed or not base:
        return None
    return get_template_canonical_name_v1(base)


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
        invalidate_templates_cache_v1()
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
    """Returns template content by name.

    Source priority:
    1) External presets_v1_template/ (source of truth)
    2) Embedded default fallback for "Default"
    """
    # External templates (source of truth)
    content = get_template_content_v1(name)
    if content:
        return content

    # Self-healing: return hardcoded default if file missing
    if name.lower() == "default":
        return _normalize_template_header_v1(_DEFAULT_TEMPLATE_CONTENT, "Default")
    return None


def get_default_builtin_preset_name_v1() -> Optional[str]:
    """Returns name of the default builtin preset."""
    template_name = get_default_template_name_v1()
    return template_name


def get_all_builtin_preset_names_v1() -> list[str]:
    """Returns sorted list of all builtin preset names (excluding Default)."""
    _ensure_templates_loaded_v1()
    template_names = sorted((_TEMPLATES_CACHE_V1 or {}).keys(), key=lambda s: s.lower())
    return [n for n in template_names if n.lower() != "default"]


def ensure_default_preset_exists_v1() -> bool:
    """Ensures presets_v1/ is populated and Default preset exists.

    Flow:
      1. Copy missing templates from presets_v1_template/ → presets_v1/
      2. If Default still missing, create from embedded fallback

    Returns True if Default preset exists or was created successfully.
    """
    # Ensure direct_zapret1 strategy catalogs exist in canonical AppData location.
    try:
        from .strategies_loader import ensure_v1_strategies_exist

        ensure_v1_strategies_exist()
    except Exception as e:
        log(f"Error ensuring V1 strategies catalog: {e}", "DEBUG")

    # Step 1: copy templates to user presets
    ensure_v1_templates_copied_to_presets()

    # Step 2: check Default exists
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
