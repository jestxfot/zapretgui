# preset_zapret1/strategies_loader.py
"""Self-contained V1 strategy loader for Zapret 1 (direct_zapret1) mode.

No dependency on strategy_menu/. Reads from preset_zapret1/basic_strategies/.

Usage:
    from preset_zapret1.strategies_loader import load_v1_strategies
    strategies = load_v1_strategies("youtube")  # -> {id: {...}, ...}
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Optional

from log import log

# Путь к директории со стратегиями V1
BASIC_STRATEGIES_DIR = Path(__file__).parent / "basic_strategies"

# Кеш: cache_key -> (mtime_ns, size, data)
_CACHE: Dict[str, tuple[int, int, Any]] = {}

# Допустимые значения label
_LABEL_MAP = {
    "recommended": "recommended",
    "stable":      "stable",
    "experimental":"experimental",
    "game":        "game",
    "caution":     "caution",
}


# ── Cache helpers ─────────────────────────────────────────────────────────────

def _cache_key(path: Path) -> str:
    try:
        return str(path.resolve())
    except Exception:
        return str(path)


def _file_sig(path: Path) -> tuple[int, int]:
    st = path.stat()
    mtime_ns = int(getattr(st, "st_mtime_ns", int(st.st_mtime * 1_000_000_000)))
    return mtime_ns, int(st.st_size)


# ── TXT parser ────────────────────────────────────────────────────────────────

def _load_txt(filepath: Path) -> Optional[Dict]:
    """Parse INI-style TXT file → {'strategies': [...]}.

    Format:
        [strategy_id]
        name = Название
        label = recommended|stable|experimental|game|caution
        description = Описание
        --dpi-desync=fake
        --dpi-desync-fake-tls=...
    """
    if not filepath.exists():
        return None

    key = _cache_key(filepath)

    try:
        sig = _file_sig(filepath)
    except Exception:
        sig = (0, 0)

    cached = _CACHE.get(key)
    if cached and (cached[0], cached[1]) == sig:
        return deepcopy(cached[2])

    try:
        content = filepath.read_text(encoding="utf-8")
    except Exception as e:
        log(f"V1 strategies_loader: cannot read {filepath.name}: {e}", "ERROR")
        return None

    strategies = []
    current: Optional[dict] = None
    current_args: list[str] = []

    for line in content.splitlines():
        line = line.rstrip()
        if not line or line.startswith("#"):
            continue

        if line.startswith("[") and line.endswith("]"):
            if current is not None:
                current["args"] = "\n".join(current_args)
                strategies.append(current)
            sid = line[1:-1].strip()
            current = {
                "id": sid, "name": sid,
                "description": "", "label": None, "args": "",
            }
            current_args = []
            continue

        if current is None:
            continue

        if line.startswith("--"):
            current_args.append(line)
            continue

        if "=" in line:
            k, _, v = line.partition("=")
            k = k.strip().lower()
            v = v.strip()
            if k == "name":
                current["name"] = v
            elif k == "label":
                current["label"] = v or None
            elif k == "description":
                current["description"] = v

    if current is not None:
        current["args"] = "\n".join(current_args)
        strategies.append(current)

    result = {"strategies": strategies}
    _CACHE[key] = (sig[0], sig[1], deepcopy(result))
    log(f"V1 strategies_loader: loaded {len(strategies)} from {filepath.name}", "DEBUG")
    return result


# ── Normalization ─────────────────────────────────────────────────────────────

def _normalize(raw: dict) -> dict:
    label_raw = str(raw.get("label") or "").lower()
    return {
        "id":          raw.get("id", ""),
        "name":        raw.get("name", "Без названия"),
        "description": raw.get("description", ""),
        "label":       _LABEL_MAP.get(label_raw),
        "args":        raw.get("args", "").strip(),
        "_source":     "builtin",
    }


def _is_valid_id(sid: str) -> bool:
    return bool(sid) and all(c.isalnum() or c == "_" for c in sid)


# ── Public API ────────────────────────────────────────────────────────────────

def load_v1_strategies(category: str) -> Dict[str, Dict]:
    """Return {strategy_id: strategy_dict} for the given V1 category.

    Maps category name → file in preset_zapret1/basic_strategies/:
        udp_* / *_udp       → udp_zapret1.txt
        discord_voice_*     → discord_voice_zapret1.txt (fallback udp_zapret1.txt)
        http80_* / *_http80 → http80_zapret1.txt (fallback tcp_zapret1.txt)
        everything else     → tcp_zapret1.txt
    """
    z1_dir = BASIC_STRATEGIES_DIR
    if not z1_dir.exists():
        log(f"V1 strategies_loader: directory not found: {z1_dir}", "WARNING")
        return {}

    cat = category.lower()
    if cat == "udp" or cat.endswith("_udp") or cat.startswith("udp_"):
        candidates = ["udp_zapret1"]
    elif "discord_voice" in cat or cat.endswith("_voice"):
        candidates = ["discord_voice_zapret1", "udp_zapret1"]
    elif cat == "http80" or cat.endswith("_http80"):
        candidates = ["http80_zapret1", "tcp_zapret1"]
    else:
        candidates = ["tcp_zapret1"]

    raw_data: Optional[Dict] = None
    for basename in candidates:
        raw_data = _load_txt(z1_dir / f"{basename}.txt")
        if raw_data:
            log(f"V1: '{category}' → {basename}.txt ({len(raw_data.get('strategies', []))} стратегий)", "DEBUG")
            break

    if not raw_data:
        return {}

    result: Dict[str, Dict] = {}
    for strat in raw_data.get("strategies", []):
        sid = strat.get("id", "").strip()
        if not _is_valid_id(sid):
            continue
        result[sid] = _normalize(strat)

    return result


def invalidate_cache(filepath: Optional[Path] = None) -> None:
    """Invalidate cache for a specific file (or clear all if None)."""
    if filepath is None:
        _CACHE.clear()
    else:
        _CACHE.pop(_cache_key(filepath), None)
