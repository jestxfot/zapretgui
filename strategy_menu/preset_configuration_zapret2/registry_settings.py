# strategy_menu/preset_configuration_zapret2/registry_settings.py
"""
Registry Settings - CRUD для настроек категорий в Windows Registry.

Централизованное место для ВСЕХ операций с реестром для настроек категорий:
- filter_mode (hostlist/ipset)
- out_range (mode + value)
- syndata (blob, tls_mod, autottl, tcp_flags, send)

Использование:
    from strategy_menu.preset_configuration_zapret2 import registry_settings as rs

    # Сохранить
    rs.save_filter_mode("youtube", "ipset")
    rs.save_out_range("youtube", {"mode": "n", "value": 4})
    rs.save_syndata("youtube", {"enabled": True, "blob": "tls_google", ...})

    # Загрузить
    mode = rs.load_filter_mode("youtube")  # "hostlist" или "ipset"
    out_range = rs.load_out_range("youtube")  # {"mode": "n", "value": 4}
    syndata = rs.load_syndata("youtube")  # {...}
"""

import json
import winreg
from typing import Dict, Any, Optional
from log import log


def _get_registry_path() -> str:
    """Возвращает базовый путь реестра"""
    from config import REGISTRY_PATH
    return REGISTRY_PATH


# ═══════════════════════════════════════════════════════════════════════════════
# GENERIC HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _save_string(subkey: str, name: str, value: str) -> bool:
    """Сохраняет строку в реестр"""
    try:
        key_path = f"{_get_registry_path()}\\{subkey}"
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path) as key:
            winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)
        return True
    except Exception as e:
        log(f"Registry save error [{subkey}/{name}]: {e}", "ERROR")
        return False


def _load_string(subkey: str, name: str, default: str = "") -> str:
    """Загружает строку из реестра"""
    try:
        key_path = f"{_get_registry_path()}\\{subkey}"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
            value, _ = winreg.QueryValueEx(key, name)
            return value
    except FileNotFoundError:
        return default
    except Exception as e:
        log(f"Registry load error [{subkey}/{name}]: {e}", "DEBUG")
        return default


def _save_json(subkey: str, name: str, data: dict) -> bool:
    """Сохраняет JSON в реестр"""
    return _save_string(subkey, name, json.dumps(data))


def _load_json(subkey: str, name: str, default: dict) -> dict:
    """Загружает JSON из реестра"""
    value = _load_string(subkey, name, "")
    if not value:
        return default.copy()
    try:
        loaded = json.loads(value)
        # Merge with defaults for backward compatibility
        return {**default, **loaded}
    except json.JSONDecodeError:
        return default.copy()


def _delete_value(subkey: str, name: str) -> bool:
    """Удаляет значение из реестра"""
    try:
        key_path = f"{_get_registry_path()}\\{subkey}"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, name)
        return True
    except FileNotFoundError:
        return True  # Already deleted
    except Exception as e:
        log(f"Registry delete error [{subkey}/{name}]: {e}", "DEBUG")
        return False


# ═══════════════════════════════════════════════════════════════════════════════
# FILTER MODE (hostlist / ipset)
# ═══════════════════════════════════════════════════════════════════════════════

FILTER_MODE_KEY = "CategoryFilterMode"
FILTER_MODE_DEFAULT = "hostlist"


def save_filter_mode(category_key: str, mode: str) -> bool:
    """
    Сохраняет режим фильтрации для категории.

    Args:
        category_key: Ключ категории (например "youtube", "discord_tcp")
        mode: "hostlist" или "ipset"

    Returns:
        True если успешно
    """
    if mode not in ("hostlist", "ipset"):
        log(f"Invalid filter_mode: {mode}", "WARNING")
        mode = FILTER_MODE_DEFAULT

    log(f"[REGISTRY SAVE] {category_key} = {mode}", "DEBUG")
    success = _save_string(FILTER_MODE_KEY, category_key, mode)
    if success:
        log(f"Saved filter_mode: {category_key} = {mode}", "DEBUG")
    return success


def load_filter_mode(category_key: str) -> str:
    """
    Загружает режим фильтрации для категории.

    Returns:
        "hostlist" или "ipset"
    """
    value = _load_string(FILTER_MODE_KEY, category_key, FILTER_MODE_DEFAULT)
    result = "ipset" if value == "ipset" else "hostlist"
    log(f"[REGISTRY LOAD] {category_key}: raw='{value}' -> result='{result}'", "DEBUG")
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# OUT-RANGE
# ═══════════════════════════════════════════════════════════════════════════════

OUT_RANGE_KEY = "CategoryOutRange"
OUT_RANGE_DEFAULT = {"mode": "n", "value": 4}


def save_out_range(category_key: str, settings: Dict[str, Any]) -> bool:
    """
    Сохраняет out-range настройки для категории.

    Args:
        category_key: Ключ категории
        settings: {"mode": "d"|"n", "value": int}

    Returns:
        True если успешно
    """
    # Валидация
    mode = settings.get("mode", "n")
    if mode not in ("d", "n"):
        mode = "n"

    value = settings.get("value", 4)
    if not isinstance(value, int) or value < 0:
        value = 4

    data = {"mode": mode, "value": value}
    success = _save_json(OUT_RANGE_KEY, category_key, data)
    if success:
        log(f"Saved out_range: {category_key} = {data}", "DEBUG")
    return success


def load_out_range(category_key: str) -> Dict[str, Any]:
    """
    Загружает out-range настройки для категории.

    Returns:
        {"mode": "d"|"n", "value": int}
    """
    return _load_json(OUT_RANGE_KEY, category_key, OUT_RANGE_DEFAULT)


# ═══════════════════════════════════════════════════════════════════════════════
# SYNDATA
# ═══════════════════════════════════════════════════════════════════════════════

SYNDATA_KEY = "CategorySyndata"
SYNDATA_DEFAULT = {
    "enabled": True,
    "blob": "tls_google",
    "tls_mod": "none",
    "autottl_enabled": False,
    "autottl_delta": -1,
    "autottl_min": 3,
    "autottl_max": 20,
    "tcp_flags_unset": "none",
    "send_enabled": True,
    "send_repeats": 2,
}


def save_syndata(category_key: str, settings: Dict[str, Any]) -> bool:
    """
    Сохраняет syndata настройки для категории.

    Args:
        category_key: Ключ категории
        settings: Словарь с настройками syndata

    Returns:
        True если успешно
    """
    # Merge with defaults
    data = {**SYNDATA_DEFAULT, **settings}
    success = _save_json(SYNDATA_KEY, category_key, data)
    if success:
        log(f"Saved syndata: {category_key}", "DEBUG")
    return success


def load_syndata(category_key: str) -> Dict[str, Any]:
    """
    Загружает syndata настройки для категории.

    Returns:
        Словарь с настройками syndata
    """
    return _load_json(SYNDATA_KEY, category_key, SYNDATA_DEFAULT)


# ═══════════════════════════════════════════════════════════════════════════════
# CATEGORY SORT ORDER
# ═══════════════════════════════════════════════════════════════════════════════

SORT_KEY = "CategorySort"
SORT_DEFAULT = "default"


def save_sort_order(category_key: str, sort_order: str) -> bool:
    """Сохраняет порядок сортировки для категории"""
    if sort_order not in ("default", "name_asc", "name_desc"):
        sort_order = SORT_DEFAULT
    return _save_string(SORT_KEY, category_key, sort_order)


def load_sort_order(category_key: str) -> str:
    """Загружает порядок сортировки для категории"""
    value = _load_string(SORT_KEY, category_key, SORT_DEFAULT)
    if value in ("default", "name_asc", "name_desc"):
        return value
    return SORT_DEFAULT


# ═══════════════════════════════════════════════════════════════════════════════
# RESET TO DEFAULTS
# ═══════════════════════════════════════════════════════════════════════════════

def reset_category_settings(category_key: str) -> bool:
    """
    Сбрасывает все настройки категории к значениям по умолчанию.

    Returns:
        True если успешно
    """
    success = True
    success &= _delete_value(FILTER_MODE_KEY, category_key)
    success &= _delete_value(OUT_RANGE_KEY, category_key)
    success &= _delete_value(SYNDATA_KEY, category_key)
    success &= _delete_value(SORT_KEY, category_key)

    if success:
        log(f"Reset all settings for category: {category_key}", "INFO")
    return success


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Filter mode
    'save_filter_mode',
    'load_filter_mode',
    'FILTER_MODE_DEFAULT',
    # Out-range
    'save_out_range',
    'load_out_range',
    'OUT_RANGE_DEFAULT',
    # Syndata
    'save_syndata',
    'load_syndata',
    'SYNDATA_DEFAULT',
    # Sort
    'save_sort_order',
    'load_sort_order',
    # Reset
    'reset_category_settings',
]
