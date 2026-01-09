"""
Lightweight loader for Zapret 2 categories and strategies (TXT format).

This module intentionally avoids importing `strategy_menu` to keep parsing
and inference usable in non-GUI contexts and during development.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Optional


@dataclass(frozen=True)
class CatalogPaths:
    indexjson_dir: Path
    builtin_dir: Path
    user_dir: Path


_CACHED_PATHS: Optional[CatalogPaths] = None
_CACHED_CATEGORIES: Optional[Dict[str, Dict]] = None
_CACHED_STRATEGIES: Dict[tuple[str, Optional[str]], Dict[str, Dict]] = {}


def _candidate_indexjson_dirs() -> Iterable[Path]:
    env = os.environ.get("ZAPRET_INDEXJSON_FOLDER")
    if env:
        yield Path(env)

    try:
        from config import INDEXJSON_FOLDER  # type: ignore
        yield Path(INDEXJSON_FOLDER)
    except Exception:
        pass

    # Repo layout hint: /mnt/h/Privacy/zapretgui -> /mnt/h/Privacy/zapret
    try:
        here = Path(__file__).resolve()
        # preset_zapret2/catalog.py -> zapretgui -> Privacy
        privacy_dir = here.parents[2]
        yield privacy_dir / "zapret" / "json"
    except Exception:
        pass

    # Fallbacks
    yield Path.cwd() / "json"
    yield Path("/mnt/c/ProgramData/ZapretTwoDev/json")
    yield Path("/mnt/c/ProgramData/ZapretTwo/json")


def get_catalog_paths() -> Optional[CatalogPaths]:
    global _CACHED_PATHS
    if _CACHED_PATHS is not None:
        return _CACHED_PATHS

    for index_dir in _candidate_indexjson_dirs():
        index_dir = Path(index_dir)
        builtin_dir = index_dir / "strategies" / "builtin"
        if (builtin_dir / "categories.txt").exists():
            user_dir = index_dir / "strategies" / "user"
            _CACHED_PATHS = CatalogPaths(
                indexjson_dir=index_dir,
                builtin_dir=builtin_dir,
                user_dir=user_dir,
            )
            return _CACHED_PATHS

    return None


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _parse_bool(value: str) -> bool:
    return value.strip().lower() in ("true", "1", "yes", "y", "on")


def load_categories() -> Dict[str, Dict]:
    global _CACHED_CATEGORIES
    if _CACHED_CATEGORIES is not None:
        return _CACHED_CATEGORIES

    paths = get_catalog_paths()
    if paths is None:
        _CACHED_CATEGORIES = {}
        return _CACHED_CATEGORIES

    def _load_one(file_path: Path) -> Dict[str, Dict]:
        if not file_path.exists():
            return {}
        text = _read_text(file_path)
        categories: Dict[str, Dict] = {}
        current_key: Optional[str] = None
        current: Dict[str, object] = {}

        for raw in text.splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("[") and line.endswith("]"):
                if current_key:
                    categories[current_key] = dict(current)
                current_key = line[1:-1].strip()
                current = {"key": current_key}
                continue
            if "=" not in line or current_key is None:
                continue

            k, _, v = line.partition("=")
            k = k.strip()
            v = v.strip()

            if k in ("order", "command_order"):
                try:
                    current[k] = int(v)
                except ValueError:
                    current[k] = 0
            elif k in ("needs_new_separator", "strip_payload", "requires_all_ports"):
                current[k] = _parse_bool(v)
            else:
                current[k] = v

        if current_key:
            categories[current_key] = dict(current)
        return categories

    builtin = _load_one(paths.builtin_dir / "categories.txt")
    user = _load_one(paths.user_dir / "categories.txt")
    merged = dict(builtin)
    for key, data in user.items():
        if key in merged:
            merged[key].update(data)
        else:
            merged[key] = data

    _CACHED_CATEGORIES = merged
    return _CACHED_CATEGORIES


def load_strategies(strategy_type: str, strategy_set: Optional[str] = None) -> Dict[str, Dict]:
    cache_key = (strategy_type, strategy_set)
    if cache_key in _CACHED_STRATEGIES:
        return _CACHED_STRATEGIES[cache_key]

    paths = get_catalog_paths()
    if paths is None:
        _CACHED_STRATEGIES[cache_key] = {}
        return _CACHED_STRATEGIES[cache_key]

    filename = f"{strategy_type}.txt" if not strategy_set else f"{strategy_type}_{strategy_set}.txt"

    def _load_one(file_path: Path) -> Dict[str, Dict]:
        if not file_path.exists():
            return {}
        text = _read_text(file_path)
        strategies: Dict[str, Dict] = {}
        current_id: Optional[str] = None
        current: Dict[str, object] = {}
        args: list[str] = []

        def _flush() -> None:
            nonlocal current_id, current, args
            if not current_id:
                return
            current["id"] = current_id
            current["args"] = "\n".join(args).strip()
            strategies[current_id] = dict(current)

        for raw in text.splitlines():
            line = raw.rstrip()
            if not line or line.lstrip().startswith("#"):
                continue
            if line.startswith("[") and line.endswith("]"):
                _flush()
                current_id = line[1:-1].strip()
                current = {
                    "name": current_id,
                    "author": "unknown",
                    "label": None,
                    "description": "",
                    "blobs": [],
                }
                args = []
                continue

            if current_id is None:
                continue

            if line.startswith("--"):
                args.append(line.strip())
                continue

            if "=" in line:
                k, _, v = line.partition("=")
                k = k.strip().lower()
                v = v.strip()
                if k == "name":
                    current["name"] = v
                elif k == "author":
                    current["author"] = v
                elif k == "label":
                    current["label"] = v or None
                elif k == "description":
                    current["description"] = v
                elif k == "blobs":
                    current["blobs"] = [b.strip() for b in v.split(",") if b.strip()]

        _flush()
        return strategies

    builtin = _load_one(paths.builtin_dir / filename)
    user = _load_one(paths.user_dir / filename)
    merged = dict(builtin)
    merged.update(user)  # user overrides builtin by id

    _CACHED_STRATEGIES[cache_key] = merged
    return merged

