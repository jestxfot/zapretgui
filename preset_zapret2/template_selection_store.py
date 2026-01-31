# preset_zapret2/template_selection_store.py

from __future__ import annotations

import configparser
import os
from pathlib import Path
from typing import Optional


_SECTION = "direct_zapret2"
_KEY = "ActivePresetTemplate"


def _get_appdata_base() -> Path:
    """Returns %APPDATA% base directory (best-effort)."""
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata)
    # Fallback used by tests/WSL.
    return Path.home() / "AppData" / "Roaming"


def get_active_preset_template_path() -> Path:
    """Path to zapret2_active_preset_templates.ini under %APPDATA%/zapret."""
    return _get_appdata_base() / "zapret" / "zapret2_active_preset_templates.ini"


def get_active_preset_template_name() -> Optional[str]:
    path = get_active_preset_template_path()
    try:
        if not path.exists():
            return None

        cfg = configparser.ConfigParser()
        cfg.read(path, encoding="utf-8")
        value = cfg.get(_SECTION, _KEY, fallback="").strip()
        return value or None
    except Exception:
        return None


def set_active_preset_template_name(name: Optional[str]) -> bool:
    path = get_active_preset_template_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)

        cfg = configparser.ConfigParser()
        if path.exists():
            cfg.read(path, encoding="utf-8")

        if _SECTION not in cfg:
            cfg[_SECTION] = {}

        value = (name or "").strip()
        if value:
            cfg[_SECTION][_KEY] = value
        else:
            # Clear key
            try:
                cfg.remove_option(_SECTION, _KEY)
            except Exception:
                pass

        with path.open("w", encoding="utf-8") as f:
            cfg.write(f)
        return True
    except Exception:
        return False
