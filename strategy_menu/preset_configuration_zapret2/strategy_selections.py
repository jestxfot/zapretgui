# strategy_menu/preset_configuration_zapret2/strategy_selections.py
"""
Strategy Selections - управление выбором стратегий для категорий.

Централизованное место для работы с выборами стратегий в реестре.

Использование:
    from strategy_menu.preset_configuration_zapret2 import strategy_selections

    # Получить все выборы
    selections = strategy_selections.get_all()

    # Получить/установить для категории
    strategy_id = strategy_selections.get("youtube")
    strategy_selections.set("youtube", "multisplit_tls")

    # Сохранить все
    strategy_selections.set_all({"youtube": "multisplit", "discord_tcp": "none"})
"""

import time
import winreg
from typing import Dict, Optional
from log import log
from config import reg, REGISTRY_PATH


# ═══════════════════════════════════════════════════════════════════════════════
# КОНСТАНТЫ
# ═══════════════════════════════════════════════════════════════════════════════

DIRECT_STRATEGY_KEY = rf"{REGISTRY_PATH}\DirectStrategy"
DIRECT_ORCHESTRA_STRATEGY_KEY = rf"{REGISTRY_PATH}\DirectOrchestraStrategy"
DIRECT_ZAPRET1_STRATEGY_KEY = rf"{REGISTRY_PATH}\DirectZapret1Strategy"

# Кэш выборов
_cache: Optional[Dict[str, str]] = None
_cache_time: float = 0
_CACHE_TTL: float = 5.0  # 5 секунд

# Предупреждения о невалидных стратегиях (чтобы не спамить)
_warned_invalid: set = set()


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _get_launch_method() -> str:
    """Получает метод запуска стратегий из реестра"""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_PATH) as key:
            value, _ = winreg.QueryValueEx(key, "StrategyLaunchMethod")
            return value if value in ("direct", "direct_orchestra", "direct_zapret1") else "direct"
    except:
        return "direct"


def _get_strategy_key() -> str:
    """Возвращает ключ реестра для выборов стратегий в зависимости от метода запуска"""
    method = _get_launch_method()
    if method == "direct_orchestra":
        return DIRECT_ORCHESTRA_STRATEGY_KEY
    elif method == "direct_zapret1":
        return DIRECT_ZAPRET1_STRATEGY_KEY
    return DIRECT_STRATEGY_KEY


def _category_to_reg_key(category_key: str) -> str:
    """Конвертирует ключ категории в ключ реестра"""
    return category_key.replace("_", ".")


def _reg_key_to_category(reg_key: str) -> str:
    """Конвертирует ключ реестра в ключ категории"""
    return reg_key.replace(".", "_")


# ═══════════════════════════════════════════════════════════════════════════════
# CACHE
# ═══════════════════════════════════════════════════════════════════════════════

def invalidate_cache():
    """Сбрасывает кэш выборов стратегий"""
    global _cache, _cache_time
    _cache = None
    _cache_time = 0


# ═══════════════════════════════════════════════════════════════════════════════
# GET / SET
# ═══════════════════════════════════════════════════════════════════════════════

def get(category_key: str) -> str:
    """
    Получает выбранную стратегию для категории.

    Args:
        category_key: Ключ категории (например "youtube", "discord_tcp")

    Returns:
        ID стратегии или "none"
    """
    from strategy_menu.strategies_registry import registry

    strategy_key = _get_strategy_key()
    reg_key = _category_to_reg_key(category_key)
    value = reg(strategy_key, reg_key)

    if value:
        return value

    # Для direct_orchestra по умолчанию все категории отключены
    method = _get_launch_method()
    if method == "direct_orchestra":
        return "none"

    # Для обычного direct возвращаем значение по умолчанию из категории
    category_info = registry.get_category_info(category_key)
    if category_info:
        return category_info.default_strategy

    return "none"


def set(category_key: str, strategy_id: str) -> bool:
    """
    Сохраняет выбранную стратегию для категории.

    Args:
        category_key: Ключ категории
        strategy_id: ID стратегии или "none"

    Returns:
        True если успешно
    """
    strategy_key = _get_strategy_key()
    reg_key = _category_to_reg_key(category_key)
    result = reg(strategy_key, reg_key, strategy_id)
    if result:
        invalidate_cache()
    return bool(result)


def get_all() -> Dict[str, str]:
    """
    Возвращает все сохраненные выборы стратегий.

    Кэширует результат на 5 секунд.
    Валидирует каждый strategy_id - если не найден, использует default.

    Returns:
        Dict {category_key: strategy_id}
    """
    global _cache, _cache_time

    # Проверяем кэш
    current_time = time.time()
    if _cache is not None and current_time - _cache_time < _CACHE_TTL:
        return _cache.copy()

    from strategy_menu.strategies_registry import registry

    try:
        selections = {}
        default_selections = registry.get_default_selections()
        method = _get_launch_method()
        strategy_key = _get_strategy_key()

        for category_key in registry.get_all_category_keys():
            reg_key = _category_to_reg_key(category_key)
            value = reg(strategy_key, reg_key)

            if value:
                if value == "none":
                    selections[category_key] = value
                else:
                    # Валидация: проверяем существование стратегии
                    args = registry.get_strategy_args_safe(category_key, value)
                    if args is not None:
                        selections[category_key] = value
                    else:
                        # Стратегия не найдена - используем default
                        if method == "direct_orchestra":
                            default_value = "none"
                        else:
                            default_value = default_selections.get(category_key, "none")
                        selections[category_key] = default_value

                        # Логируем один раз
                        warn_key = f"{category_key}:{value}"
                        if warn_key not in _warned_invalid:
                            _warned_invalid.add(warn_key)
                            log(f"Стратегия '{value}' не найдена в '{category_key}', "
                                f"заменена на '{default_value}'", "WARNING")

        # Заполняем недостающие значения
        for key, default_value in default_selections.items():
            if key not in selections:
                if method == "direct_orchestra":
                    selections[key] = "none"
                else:
                    selections[key] = default_value

        # Сохраняем в кэш
        _cache = selections
        _cache_time = current_time

        return selections

    except Exception as e:
        log(f"Ошибка загрузки выборов стратегий: {e}", "ERROR")
        return registry.get_default_selections()


def set_all(selections: Dict[str, str]) -> bool:
    """
    Сохраняет все выборы стратегий.

    Args:
        selections: Dict {category_key: strategy_id}

    Returns:
        True если успешно
    """
    from strategy_menu.strategies_registry import registry

    try:
        success = True
        strategy_key = _get_strategy_key()

        for category_key, strategy_id in selections.items():
            if category_key in registry.get_all_category_keys():
                reg_key = _category_to_reg_key(category_key)
                result = reg(strategy_key, reg_key, strategy_id)
                success = success and (result is not False)

        if success:
            invalidate_cache()
            log("Выборы стратегий сохранены", "DEBUG")

        return success

    except Exception as e:
        log(f"Ошибка сохранения выборов: {e}", "ERROR")
        return False


def clear_all() -> bool:
    """
    Очищает все выборы (устанавливает в "none").

    Returns:
        True если успешно
    """
    from strategy_menu.strategies_registry import registry

    try:
        strategy_key = _get_strategy_key()

        for category_key in registry.get_all_category_keys():
            reg_key = _category_to_reg_key(category_key)
            reg(strategy_key, reg_key, "none")

        invalidate_cache()
        log("Все выборы стратегий очищены", "INFO")
        return True

    except Exception as e:
        log(f"Ошибка очистки выборов: {e}", "ERROR")
        return False


__all__ = [
    'get',
    'set',
    'get_all',
    'set_all',
    'clear_all',
    'invalidate_cache',
]
