# preset_zapret2/preset_defaults.py
"""preset_zapret2 built-in preset templates.

There are two kinds of presets:

1) User presets (editable files):
   - Stored in `{PROGRAMDATA_PATH}/presets/*.txt`.

2) Built-in presets (virtual templates):
   - Loaded from `%APPDATA%/zapret/presets/_builtin/*.txt`.
   - `Default.txt` and `Gaming.txt` are required.

Built-in presets do NOT require corresponding files in the *user* presets root.
They are shown in the UI as official presets and can be activated directly.

How to add a new built-in preset:
   - Create: `%APPDATA%/zapret/presets/_builtin/<PresetName>.txt`
   - Encoding: UTF-8
   - The preset name is derived from the filename.
   - Files starting with '_' are ignored.
"""

from pathlib import Path
from typing import Optional

_REQUIRED_BUILTIN_PRESET_NAMES: tuple[str, ...] = ("Default", "Gaming")

_BUILTIN_PRESETS_CACHE: Optional[dict[str, str]] = None
_MISSING_REQUIRED_LOGGED: bool = False

_REQUIRED_CANONICAL_NAME_BY_KEY: dict[str, str] = {
    n.lower(): n for n in _REQUIRED_BUILTIN_PRESET_NAMES
}


def _template_sanity_ok(text: str) -> bool:
    """Quick sanity checks to skip obviously broken/truncated templates."""
    s = (text or "").strip()
    if not s:
        return False
    # Base args are always present in our presets.
    if "--lua-init=" not in s:
        return False
    # Category blocks should exist for meaningful presets.
    if "--filter-" not in s:
        return False
    return True


def _normalize_template_header(content: str, preset_name: str) -> str:
    """Ensure # Preset / # ActivePreset match the filename-derived name."""
    name = str(preset_name or "").strip()
    text = (content or "").replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")

    # Header = leading comment/empty lines until the first non-comment, non-empty line.
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
        stripped = raw.strip()
        low = stripped.lower()
        if low.startswith("# preset:"):
            out_header.append(f"# Preset: {name}")
            saw_preset = True
            continue
        if low.startswith("# activepreset:"):
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


def _load_builtin_preset_templates_from_disk() -> dict[str, str]:
    """Loads built-in templates from `%APPDATA%/zapret/presets/_builtin/*.txt`."""
    templates: dict[str, str] = {}

    try:
        from config import get_zapret_presets_dir

        presets_dir = Path(get_zapret_presets_dir()) / "_builtin"
    except Exception:
        return templates

    if not presets_dir.exists() or not presets_dir.is_dir():
        try:
            from log import log

            log(f"Built-in preset templates directory not found: {presets_dir}", "ERROR")
        except Exception:
            pass
        return templates

    for file_path in sorted(presets_dir.glob("*.txt"), key=lambda p: p.name.lower()):
        name = (file_path.stem or "").strip()
        if not name or name.startswith("_"):
            continue

        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        content = _normalize_template_header(content, name)
        if not _template_sanity_ok(content):
            continue

        templates[name] = content

    global _MISSING_REQUIRED_LOGGED
    if not _MISSING_REQUIRED_LOGGED:
        missing = [n for n in _REQUIRED_BUILTIN_PRESET_NAMES if n not in templates]
        if missing:
            try:
                from log import log

                for n in missing:
                    log(
                        f"Missing required built-in preset template: {n}. "
                        f"Expected file: {presets_dir / (n + '.txt')}",
                        "ERROR",
                    )
            except Exception:
                pass
            _MISSING_REQUIRED_LOGGED = True

    return templates


def get_builtin_preset_templates() -> dict[str, str]:
    """Returns built-in templates (virtual presets).

    Built-ins are not persisted in `{PROGRAMDATA}/presets/*.txt`.
    """
    global _BUILTIN_PRESETS_CACHE
    if _BUILTIN_PRESETS_CACHE is not None:
        return _BUILTIN_PRESETS_CACHE

    templates = _load_builtin_preset_templates_from_disk()
    _BUILTIN_PRESETS_CACHE = {k: templates[k] for k in sorted(templates.keys(), key=lambda s: s.lower())}
    return _BUILTIN_PRESETS_CACHE


def get_builtin_preset_names() -> list[str]:
    templates = get_builtin_preset_templates()
    names = set(templates.keys())
    names.update(_REQUIRED_BUILTIN_PRESET_NAMES)
    return sorted(names, key=lambda s: s.lower())


BUILTIN_PRESET_TEMPLATES: dict[str, str] = get_builtin_preset_templates()

_BUILTIN_PRESET_TEMPLATE_BY_KEY: dict[str, str] = {
    canonical.lower(): content for canonical, content in BUILTIN_PRESET_TEMPLATES.items()
}

_BUILTIN_PRESET_CANONICAL_NAME_BY_KEY: dict[str, str] = {
    canonical.lower(): canonical for canonical in BUILTIN_PRESET_TEMPLATES.keys()
}

BUILTIN_COPY_SUFFIX = " (копия)"


def get_builtin_preset_content(name: str) -> Optional[str]:
    key = (name or "").strip().lower()
    if not key:
        return None
    return _BUILTIN_PRESET_TEMPLATE_BY_KEY.get(key)


def get_builtin_preset_canonical_name(name: str) -> Optional[str]:
    key = (name or "").strip().lower()
    if not key:
        return None
    return _BUILTIN_PRESET_CANONICAL_NAME_BY_KEY.get(key) or _REQUIRED_CANONICAL_NAME_BY_KEY.get(key)


def is_builtin_preset_name(name: str) -> bool:
    return get_builtin_preset_canonical_name(name) is not None


def get_builtin_copy_name(builtin_name: str) -> Optional[str]:
    canonical = get_builtin_preset_canonical_name(builtin_name)
    if not canonical:
        return None
    return f"{canonical}{BUILTIN_COPY_SUFFIX}"


def get_builtin_base_from_copy_name(name: str) -> Optional[str]:
    raw = (name or "").strip()
    if not raw or not raw.endswith(BUILTIN_COPY_SUFFIX):
        return None
    base = raw[: -len(BUILTIN_COPY_SUFFIX)].strip()
    return get_builtin_preset_canonical_name(base)


# ═══════════════════════════════════════════════════════════════════════════════
# DEFAULT SETTINGS PARSER
# ═══════════════════════════════════════════════════════════════════════════════

_DEFAULT_SETTINGS_CACHE = None


def get_default_category_settings() -> dict:
    """
    Парсит built-in пресет `Default` и возвращает дефолтные настройки для всех категорий.

    Возвращает словарь вида:
    {
        "youtube": {
            "filter_mode": "hostlist",
            "tcp_enabled": True,
            "tcp_port": "80,443",
            "tcp_args": "--lua-desync=multidisorder_legacy:pos=1,midsld",
            "udp_enabled": False,
        },
        "YouTube QUIC": {
            "filter_mode": "ipset",
            "tcp_enabled": False,
            "udp_enabled": True,
            "udp_port": "443",
            "udp_args": "--lua-desync=multidisorder_legacy:pos=1,midsld",
        },
        ...
    }

    Кэширует результат при первом вызове.

    Returns:
        dict: Словарь с дефолтными настройками категорий
    """
    global _DEFAULT_SETTINGS_CACHE

    # Возвращаем из кэша если уже парсили
    if _DEFAULT_SETTINGS_CACHE is not None:
        return _DEFAULT_SETTINGS_CACHE

    from .txt_preset_parser import parse_preset_content

    try:
        template = get_builtin_preset_content("Default")
        if not template:
            from log import log

            log(
                "Cannot parse default category settings: built-in preset 'Default' is missing. "
                "Expected: %APPDATA%/zapret/presets/_builtin/Default.txt",
                "ERROR",
            )
            return {}

        preset_data = parse_preset_content(template)

        # Конвертируем CategoryBlock в удобный формат
        settings = {}

        for block in preset_data.categories:
            category_name = block.category

            if category_name not in settings:
                settings[category_name] = {
                    "filter_mode": block.filter_mode,
                    "tcp_enabled": False,
                    "tcp_port": "",
                    "tcp_args": "",
                    "udp_enabled": False,
                    "udp_port": "",
                    "udp_args": "",
                    # Parsed per-protocol overrides from DEFAULT_PRESET_CONTENT.
                    # Keys are compatible with SyndataSettings.from_dict().
                    "syndata_overrides_tcp": {},
                    "syndata_overrides_udp": {},
                }

            cat_settings = settings[category_name]

            # Merge per-protocol overrides (if any) from the block.
            # NOTE: txt_preset_parser extracts these separately from strategy_args,
            # so we must take them from block.syndata_dict.
            overrides = getattr(block, "syndata_dict", None) or {}
            if overrides:
                target = "syndata_overrides_tcp" if block.protocol == "tcp" else "syndata_overrides_udp"
                cat_settings[target].update(overrides)

            # Записываем настройки по протоколу
            if block.protocol == "tcp":
                cat_settings["tcp_enabled"] = True
                cat_settings["tcp_port"] = block.port
                cat_settings["tcp_args"] = block.strategy_args
                # TCP filter_mode имеет приоритет (обычно hostlist)
                cat_settings["filter_mode"] = block.filter_mode
            elif block.protocol == "udp":
                cat_settings["udp_enabled"] = True
                cat_settings["udp_port"] = block.port
                cat_settings["udp_args"] = block.strategy_args
                # Обновляем filter_mode для UDP только если TCP нет
                if not cat_settings["tcp_enabled"]:
                    cat_settings["filter_mode"] = block.filter_mode

        # Кэшируем результат
        _DEFAULT_SETTINGS_CACHE = settings
        return settings

    except Exception as e:
        # Если парсинг не удался, возвращаем пустой словарь
        from log import log
        log(f"Failed to parse built-in preset 'Default': {e}", "ERROR")
        return {}


def get_category_default_filter_mode(category_name: str) -> str:
    """
    Возвращает дефолтный filter_mode для категории из DEFAULT_PRESET_CONTENT.

    Args:
        category_name: Имя категории (например "youtube", "YouTube QUIC")

    Returns:
        str: "hostlist", "ipset" или "hostlist" (fallback)
    """
    settings = get_default_category_settings()

    if category_name in settings:
        return settings[category_name].get("filter_mode", "hostlist")

    # Fallback: hostlist
    return "hostlist"


def parse_syndata_from_args(args_str: str) -> dict:
    """
    Парсит syndata настройки из строки аргументов.

    Извлекает параметры из строк вида:
    - --lua-desync=send:repeats=2:ttl=0
    - --lua-desync=syndata:blob=tls_google:ip_autottl=-2,3-20
    - --out-range=-n8

    Args:
        args_str: Строка с аргументами (может содержать несколько строк)

    Returns:
        dict: Словарь с параметрами syndata/send/out_range
    """
    result = {
        "enabled": False,
        "blob": "tls_google",
        "tls_mod": "none",
        "autottl_delta": 0,
        "autottl_min": 3,
        "autottl_max": 20,
        "tcp_flags_unset": "none",
        "out_range": 0,
        "out_range_mode": "n",
        "send_enabled": False,
        "send_repeats": 0,
        "send_ip_ttl": 0,
        "send_ip6_ttl": 0,
        "send_ip_id": "none",
        "send_badsum": False,
    }

    import re

    # Парсим --lua-desync=syndata:...
    syndata_match = re.search(r'--lua-desync=syndata:([^\n]+)', args_str)
    if syndata_match:
        result["enabled"] = True
        syndata_str = syndata_match.group(1)

        # blob=tls_google
        blob_match = re.search(r'blob=([^:]+)', syndata_str)
        if blob_match:
            result["blob"] = blob_match.group(1)

        # ip_autottl=-2,3-20
        autottl_match = re.search(r'ip_autottl=(-?\d+),(\d+)-(\d+)', syndata_str)
        if autottl_match:
            result["autottl_delta"] = int(autottl_match.group(1))
            result["autottl_min"] = int(autottl_match.group(2))
            result["autottl_max"] = int(autottl_match.group(3))

        # tls_mod=...
        tls_mod_match = re.search(r'tls_mod=([^:]+)', syndata_str)
        if tls_mod_match:
            result["tls_mod"] = tls_mod_match.group(1)

    # Парсим --lua-desync=send:...
    send_match = re.search(r'--lua-desync=send:([^\n]+)', args_str)
    if send_match:
        result["send_enabled"] = True
        send_str = send_match.group(1)

        # repeats=2
        repeats_match = re.search(r'repeats=(\d+)', send_str)
        if repeats_match:
            result["send_repeats"] = int(repeats_match.group(1))

        # ttl=...
        ttl_match = re.search(r'ttl=(\d+)', send_str)
        if ttl_match:
            result["send_ip_ttl"] = int(ttl_match.group(1))

        # ttl6=...
        ttl6_match = re.search(r'ttl6=(\d+)', send_str)
        if ttl6_match:
            result["send_ip6_ttl"] = int(ttl6_match.group(1))

        # badsum=true
        if 'badsum=true' in send_str:
            result["send_badsum"] = True

    # Парсим --out-range=-n8 или -d10
    out_range_match = re.search(r'--out-range=-([nd])(\d+)', args_str)
    if out_range_match:
        result["out_range_mode"] = out_range_match.group(1)
        result["out_range"] = int(out_range_match.group(2))

    return result


def get_category_default_syndata(category_name: str, protocol: str = "tcp") -> dict:
    """
    Возвращает дефолтные syndata настройки для категории из DEFAULT_PRESET_CONTENT.

    Args:
        category_name: Имя категории (например "youtube", "discord")
        protocol: "tcp" или "udp" (udp также покрывает QUIC/L7)

    Returns:
        dict: Словарь с параметрами (enabled, blob, autottl_*, send_*, out_range)
    """
    # Base defaults come from code (UI expectations), then overridden by
    # any values present in DEFAULT_PRESET_CONTENT (e.g. out-range for discord_voice).
    from .preset_model import SyndataSettings

    proto = (protocol or "").strip().lower()
    if proto in ("udp", "quic", "l7", "raw"):
        base = SyndataSettings.get_defaults_udp().to_dict()
        key = "syndata_overrides_udp"
    else:
        base = SyndataSettings.get_defaults().to_dict()
        key = "syndata_overrides_tcp"

    settings = get_default_category_settings()
    overrides = (settings.get(category_name) or {}).get(key) or {}
    if isinstance(overrides, dict) and overrides:
        base.update(overrides)

    return base
