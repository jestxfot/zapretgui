"""
Build category base filter lines for preset-zapret2.txt.

The GUI stores the active preset as a winws2 config-like text file where each
category block starts with a "base filter" (ports/L7 + hostlist/ipset/etc).

This module builds these base filter lines from `categories.txt` (loaded via
`preset_zapret2.catalog`) and converts list filenames to absolute paths.
"""

from __future__ import annotations

import os
import re
from pathlib import PureWindowsPath
from typing import List, Optional

from log import log


def _is_windows_abs(path: str) -> bool:
    return bool(re.match(r"^[A-Za-z]:[\\\\/]", path)) or path.startswith("\\\\")


def _absolutize_lists_value(value: str, main_directory: str, lists_folder: str) -> str:
    value = value.strip().strip('"').strip("'")
    if value.startswith("@"):
        value = value[1:]

    # Already absolute (Windows) or POSIX absolute.
    if _is_windows_abs(value) or os.path.isabs(value):
        return os.path.normpath(value)

    # If the value already contains folders (lists/..., json/... etc), keep relative structure.
    if "/" in value or "\\" in value:
        return os.path.normpath(os.path.join(main_directory, value))

    # Bare filename -> assume lists/ folder.
    return os.path.normpath(os.path.join(lists_folder, value))


def _split_tokens(s: str) -> List[str]:
    return [t.strip() for t in re.split(r"\s+", s.strip()) if t.strip()]


def get_category_base_filter_template(category_key: str, filter_mode: str) -> Optional[str]:
    """
    Returns the base filter template for a category.

    Preference:
    - filter_mode == "ipset" -> base_filter_ipset
    - filter_mode == "hostlist" -> base_filter_hostlist
    - fallback -> base_filter (or any available variant)
    """
    try:
        from .catalog import load_categories
        info = load_categories().get(category_key) or {}
    except Exception as e:
        log(f"Cannot load categories for base_filter: {e}", "DEBUG")
        return None

    filter_mode = (filter_mode or "").strip().lower()
    candidates = []
    if filter_mode == "ipset":
        candidates.append(info.get("base_filter_ipset"))
    if filter_mode == "hostlist":
        candidates.append(info.get("base_filter_hostlist"))
    candidates.append(info.get("base_filter"))
    candidates.append(info.get("base_filter_ipset"))
    candidates.append(info.get("base_filter_hostlist"))

    for c in candidates:
        if isinstance(c, str) and c.strip():
            return c.strip()
    return None


def build_category_base_filter_lines(category_key: str, filter_mode: str) -> List[str]:
    """
    Builds base filter lines (one arg per line) for writing to preset-zapret2.txt.

    Converts list filenames in --hostlist/--ipset/--*-exclude to absolute paths.
    """
    template = get_category_base_filter_template(category_key, filter_mode)
    if not template:
        return []

    try:
        from config import MAIN_DIRECTORY, LISTS_FOLDER
        main_directory = MAIN_DIRECTORY
        lists_folder = LISTS_FOLDER
    except Exception:
        main_directory = ""
        lists_folder = ""

    lines: List[str] = []
    for token in _split_tokens(template):
        key, sep, value = token.partition("=")
        key_l = key.lower()

        if not sep:
            lines.append(token)
            continue

        if key_l in ("--hostlist", "--ipset", "--hostlist-exclude", "--ipset-exclude"):
            abs_value = _absolutize_lists_value(value, main_directory, lists_folder)
            # Ensure Windows-style basename parsing doesn't break normalization in other parts.
            # Keep original drive casing, but normalize separators.
            abs_value = str(PureWindowsPath(abs_value))
            lines.append(f"{key}={abs_value}")
            continue

        lines.append(token)

    return lines

