# strategy_menu/preset_configuration_zapret2/sync.py
"""
Sync - координация сохранения настроек и перезапуска DPI.

ГЛАВНЫЙ МОДУЛЬ для изменения настроек категорий!
Все изменения настроек должны проходить через этот модуль.

Использование:
    from strategy_menu.preset_configuration_zapret2 import sync

    # Изменить filter_mode и перезапустить DPI
    sync.apply_filter_mode("youtube", "ipset")

    # Изменить out-range и перезапустить DPI
    sync.apply_out_range("youtube", {"mode": "n", "value": 10})

    # Изменить syndata и перезапустить DPI
    sync.apply_syndata("youtube", {"enabled": True, "blob": "tls_google", ...})

    # Универсальный метод
    sync.apply_setting("youtube", "filter_mode", "ipset")
"""

from typing import Any, Dict, Optional, Callable
from log import log

from . import registry_settings as rs


# ═══════════════════════════════════════════════════════════════════════════════
# CALLBACKS (устанавливаются извне для интеграции с UI/DPI)
# ═══════════════════════════════════════════════════════════════════════════════

# Callback для перегенерации preset файла
_regenerate_callback: Optional[Callable[[], None]] = None

# Callback для перезапуска DPI (принимает category_key, strategy_id)
_restart_callback: Optional[Callable[[str, str], None]] = None

# Callback для получения текущей стратегии категории
_get_current_strategy_callback: Optional[Callable[[str], str]] = None


def set_regenerate_callback(callback: Callable[[], None]):
    """Устанавливает callback для перегенерации preset файла"""
    global _regenerate_callback
    _regenerate_callback = callback
    log("Sync: regenerate callback set", "DEBUG")


def set_restart_callback(callback: Callable[[str, str], None]):
    """Устанавливает callback для перезапуска DPI"""
    global _restart_callback
    _restart_callback = callback
    log("Sync: restart callback set", "DEBUG")


def set_get_current_strategy_callback(callback: Callable[[str], str]):
    """Устанавливает callback для получения текущей стратегии"""
    global _get_current_strategy_callback
    _get_current_strategy_callback = callback
    log("Sync: get_current_strategy callback set", "DEBUG")


# ═══════════════════════════════════════════════════════════════════════════════
# INTERNAL: Regenerate & Restart
# ═══════════════════════════════════════════════════════════════════════════════

def _regenerate_preset():
    """Перегенерирует preset-zapret2.txt"""
    if _regenerate_callback:
        try:
            _regenerate_callback()
            log("Preset file regenerated", "DEBUG")
        except Exception as e:
            log(f"Failed to regenerate preset: {e}", "ERROR")
    else:
        # Fallback - прямой вызов через локальный модуль
        try:
            from . import preset_regenerator
            preset_regenerator.regenerate()
            log("Preset file regenerated (fallback)", "DEBUG")
        except Exception as e:
            log(f"Failed to regenerate preset (fallback): {e}", "ERROR")


def _get_current_strategy(category_key: str) -> str:
    """Получает текущую стратегию для категории"""
    if _get_current_strategy_callback:
        try:
            return _get_current_strategy_callback(category_key)
        except Exception as e:
            log(f"Failed to get current strategy: {e}", "ERROR")

    # Fallback - читаем из реестра напрямую через локальный модуль
    try:
        from . import strategy_selections
        return strategy_selections.get(category_key)
    except Exception as e:
        log(f"Failed to get current strategy (fallback): {e}", "ERROR")
        return "none"


def _restart_dpi_if_active(category_key: str):
    """Перезапускает DPI если категория активна"""
    strategy_id = _get_current_strategy(category_key)

    if not strategy_id or strategy_id == "none":
        log(f"Category {category_key} is disabled, skipping DPI restart", "DEBUG")
        return

    if _restart_callback:
        try:
            _restart_callback(category_key, strategy_id)
            log(f"DPI restart triggered for {category_key}", "DEBUG")
        except Exception as e:
            log(f"Failed to restart DPI: {e}", "ERROR")
    else:
        log("No restart callback set, DPI not restarted", "WARNING")


def _apply_and_sync(category_key: str):
    """Общая логика: перегенерировать preset + перезапустить DPI"""
    _regenerate_preset()
    _restart_dpi_if_active(category_key)


# ═══════════════════════════════════════════════════════════════════════════════
# PUBLIC API: Apply Settings
# ═══════════════════════════════════════════════════════════════════════════════

def apply_filter_mode(category_key: str, mode: str) -> bool:
    """
    Сохраняет filter_mode и перезапускает DPI.

    Args:
        category_key: Ключ категории
        mode: "hostlist" или "ipset"

    Returns:
        True если успешно
    """
    log(f"Applying filter_mode: {category_key} = {mode}", "INFO")

    if not rs.save_filter_mode(category_key, mode):
        return False

    _apply_and_sync(category_key)
    return True


def apply_out_range(category_key: str, settings: Dict[str, Any]) -> bool:
    """
    Сохраняет out_range и перезапускает DPI.

    Args:
        category_key: Ключ категории
        settings: {"mode": "d"|"n", "value": int}

    Returns:
        True если успешно
    """
    log(f"Applying out_range: {category_key} = {settings}", "INFO")

    if not rs.save_out_range(category_key, settings):
        return False

    _apply_and_sync(category_key)
    return True


def apply_syndata(category_key: str, settings: Dict[str, Any]) -> bool:
    """
    Сохраняет syndata и перезапускает DPI.

    Args:
        category_key: Ключ категории
        settings: Словарь с настройками syndata

    Returns:
        True если успешно
    """
    log(f"Applying syndata: {category_key}", "INFO")

    if not rs.save_syndata(category_key, settings):
        return False

    _apply_and_sync(category_key)
    return True


def apply_setting(category_key: str, setting_type: str, value: Any) -> bool:
    """
    Универсальный метод для применения любой настройки.

    Args:
        category_key: Ключ категории
        setting_type: "filter_mode", "out_range", "syndata", "sort_order"
        value: Значение настройки

    Returns:
        True если успешно
    """
    if setting_type == "filter_mode":
        return apply_filter_mode(category_key, value)
    elif setting_type == "out_range":
        return apply_out_range(category_key, value)
    elif setting_type == "syndata":
        return apply_syndata(category_key, value)
    elif setting_type == "sort_order":
        # Sort order не требует перезапуска DPI
        return rs.save_sort_order(category_key, value)
    else:
        log(f"Unknown setting type: {setting_type}", "WARNING")
        return False


def reset_and_apply(category_key: str) -> bool:
    """
    Сбрасывает все настройки категории и перезапускает DPI.

    Returns:
        True если успешно
    """
    log(f"Resetting all settings for: {category_key}", "INFO")

    if not rs.reset_category_settings(category_key):
        return False

    _apply_and_sync(category_key)
    return True


# ═══════════════════════════════════════════════════════════════════════════════
# BATCH OPERATIONS
# ═══════════════════════════════════════════════════════════════════════════════

def apply_multiple(category_key: str, settings: Dict[str, Any]) -> bool:
    """
    Применяет несколько настроек за один раз (один перезапуск DPI).

    Args:
        category_key: Ключ категории
        settings: {
            "filter_mode": "ipset",
            "out_range": {"mode": "n", "value": 4},
            "syndata": {...}
        }

    Returns:
        True если все успешно
    """
    log(f"Applying multiple settings for: {category_key}", "INFO")

    success = True

    if "filter_mode" in settings:
        success &= rs.save_filter_mode(category_key, settings["filter_mode"])

    if "out_range" in settings:
        success &= rs.save_out_range(category_key, settings["out_range"])

    if "syndata" in settings:
        success &= rs.save_syndata(category_key, settings["syndata"])

    if "sort_order" in settings:
        success &= rs.save_sort_order(category_key, settings["sort_order"])

    if success:
        _apply_and_sync(category_key)

    return success


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Callbacks setup
    'set_regenerate_callback',
    'set_restart_callback',
    'set_get_current_strategy_callback',
    # Apply single setting
    'apply_filter_mode',
    'apply_out_range',
    'apply_syndata',
    'apply_setting',
    # Batch & reset
    'apply_multiple',
    'reset_and_apply',
]
