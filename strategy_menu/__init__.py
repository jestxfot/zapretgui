# strategy_menu/__init__.py
"""
Модуль управления стратегиями DPI-обхода.
Предоставляет единый интерфейс для работы со стратегиями.
"""

import winreg
import json
from log import log
from config import reg

REGISTRY_PATH = r"Software\ZapretReg2"
DIRECT_PATH = r"Software\ZapretReg2\DirectMethod"
DIRECT_STRATEGY_KEY = r"Software\ZapretReg2\DirectStrategy"

# ==================== МЕТОД ЗАПУСКА ====================

def get_strategy_launch_method():
    """Получает метод запуска стратегий из реестра"""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_PATH) as key:
            value, _ = winreg.QueryValueEx(key, "StrategyLaunchMethod")
            return value.lower() if value else "direct"
    except:
        default_method = "direct"
        set_strategy_launch_method(default_method)
        log(f"Установлен метод запуска по умолчанию: {default_method}", "INFO")
        return default_method

def set_strategy_launch_method(method: str):
    """Сохраняет метод запуска стратегий в реестр"""
    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, REGISTRY_PATH) as key:
            winreg.SetValueEx(key, "StrategyLaunchMethod", 0, winreg.REG_SZ, method)
            log(f"Метод запуска стратегий изменен на: {method}", "INFO")
            return True
    except Exception as e:
        log(f"Ошибка сохранения метода запуска: {e}", "❌ ERROR")
        return False


# ==================== НАСТРОЙКИ UI ДИАЛОГА ====================

def get_tabs_pinned() -> bool:
    """Получает состояние закрепления боковой панели табов"""
    result = reg(DIRECT_PATH, "TabsPinned")
    if result is not None:
        try:
            return bool(int(result))
        except (ValueError, TypeError):
            return False
    return True

def set_tabs_pinned(pinned: bool) -> bool:
    """Сохраняет состояние закрепления боковой панели табов"""
    success = reg(DIRECT_PATH, "TabsPinned", int(pinned))
    if success:
        log(f"Настройка закрепления табов: {'закреплено' if pinned else 'не закреплено'}", "DEBUG")
    return success

def get_keep_dialog_open() -> bool:
    """Получает настройку сохранения диалога открытым"""
    result = reg(DIRECT_PATH, "KeepDialogOpen")
    if result is not None:
        try:
            return bool(int(result))
        except (ValueError, TypeError):
            return False
    return False

def set_keep_dialog_open(enabled: bool) -> bool:
    """Сохраняет настройку сохранения диалога открытым"""
    success = reg(DIRECT_PATH, "KeepDialogOpen", int(enabled))
    if success:
        log(f"Настройка 'не закрывать окно': {'вкл' if enabled else 'выкл'}", "DEBUG")
    return success


# ==================== КЭШИРОВАНИЕ ИЗБРАННЫХ ====================

_favorites_cache = {}
_favorites_cache_time = 0
FAVORITES_CACHE_TTL = 0.5

def get_favorites_for_category(category_key):
    """Получает избранные стратегии для категории (с кэшем)"""
    import time
    global _favorites_cache, _favorites_cache_time
    
    current_time = time.time()
    
    if current_time - _favorites_cache_time < FAVORITES_CACHE_TTL:
        return _favorites_cache.get(category_key, set())
    
    favorites = get_favorite_strategies()
    _favorites_cache = {
        key: set(values) for key, values in favorites.items()
    }
    _favorites_cache_time = current_time
    
    return _favorites_cache.get(category_key, set())

def invalidate_favorites_cache():
    """Сбрасывает кэш избранных"""
    global _favorites_cache_time
    _favorites_cache_time = 0


# ==================== ИЗБРАННЫЕ СТРАТЕГИИ ====================

def get_favorite_strategies(category=None):
    """
    Получает избранные стратегии.
    
    Args:
        category: категория или None для всех
    
    Returns:
        list (если category) или dict {category: [strategy_ids]}
    """
    try:
        result = reg(REGISTRY_PATH, "FavoriteStrategiesByCategory")
        if result:
            favorites_dict = json.loads(result)
            if category:
                return favorites_dict.get(category, [])
            return favorites_dict
        return [] if category else {}
    except Exception as e:
        log(f"Ошибка загрузки избранных: {e}", "DEBUG")
        return [] if category else {}

def add_favorite_strategy(strategy_id, category):
    """Добавляет стратегию в избранные"""
    try:
        favorites_dict = get_favorite_strategies()
        if not isinstance(favorites_dict, dict):
            favorites_dict = {}
        
        if category not in favorites_dict:
            favorites_dict[category] = []
        
        if strategy_id not in favorites_dict[category]:
            favorites_dict[category].append(strategy_id)
            reg(REGISTRY_PATH, "FavoriteStrategiesByCategory", json.dumps(favorites_dict))
            invalidate_favorites_cache()
            log(f"Стратегия {strategy_id} добавлена в избранные ({category})", "DEBUG")
            return True
        return False
    except Exception as e:
        log(f"Ошибка добавления в избранные: {e}", "ERROR")
        return False

def remove_favorite_strategy(strategy_id, category):
    """Удаляет стратегию из избранных"""
    try:
        favorites_dict = get_favorite_strategies()
        if not isinstance(favorites_dict, dict):
            return False
        
        if category in favorites_dict and strategy_id in favorites_dict[category]:
            favorites_dict[category].remove(strategy_id)
            
            if not favorites_dict[category]:
                del favorites_dict[category]
                
            reg(REGISTRY_PATH, "FavoriteStrategiesByCategory", json.dumps(favorites_dict))
            invalidate_favorites_cache()
            log(f"Стратегия {strategy_id} удалена из избранных ({category})", "DEBUG")
            return True
        return False
    except Exception as e:
        log(f"Ошибка удаления из избранных: {e}", "ERROR")
        return False

def is_favorite_strategy(strategy_id, category=None):
    """Проверяет, является ли стратегия избранной"""
    favorites_dict = get_favorite_strategies()
    if not isinstance(favorites_dict, dict):
        return False
    
    if category:
        return strategy_id in favorites_dict.get(category, [])
    else:
        for cat_favorites in favorites_dict.values():
            if strategy_id in cat_favorites:
                return True
        return False

def toggle_favorite_strategy(strategy_id, category):
    """Переключает статус избранной стратегии"""
    if is_favorite_strategy(strategy_id, category):
        remove_favorite_strategy(strategy_id, category)
        return False
    else:
        add_favorite_strategy(strategy_id, category)
        return True

def clear_favorite_strategies(category=None):
    """Очищает избранные стратегии"""
    try:
        if category:
            favorites_dict = get_favorite_strategies()
            if isinstance(favorites_dict, dict) and category in favorites_dict:
                del favorites_dict[category]
                reg(REGISTRY_PATH, "FavoriteStrategiesByCategory", json.dumps(favorites_dict))
                invalidate_favorites_cache()
        else:
            reg(REGISTRY_PATH, "FavoriteStrategiesByCategory", json.dumps({}))
            invalidate_favorites_cache()
        return True
    except Exception as e:
        log(f"Ошибка очистки избранных: {e}", "ERROR")
        return False

def get_all_favorite_strategies_flat():
    """Возвращает плоский список всех избранных"""
    favorites_dict = get_favorite_strategies()
    if not isinstance(favorites_dict, dict):
        return []
    
    all_favorites = set()
    for cat_favorites in favorites_dict.values():
        all_favorites.update(cat_favorites)
    
    return list(all_favorites)


# ==================== LEGACY ИЗБРАННЫЕ (для совместимости) ====================

def get_favorite_strategies_legacy():
    """[LEGACY] Получает список ID избранных стратегий"""
    try:
        result = reg(REGISTRY_PATH, "FavoriteStrategies")
        if result:
            return json.loads(result)
        return []
    except:
        return []

def is_favorite_strategy_legacy(strategy_id):
    """[LEGACY] Проверяет, является ли стратегия избранной"""
    return strategy_id in get_favorite_strategies_legacy()

def toggle_favorite_strategy_legacy(strategy_id):
    """[LEGACY] Переключает статус избранной"""
    favorites = get_favorite_strategies_legacy()
    if strategy_id in favorites:
        favorites.remove(strategy_id)
    else:
        favorites.append(strategy_id)
    reg(REGISTRY_PATH, "FavoriteStrategies", json.dumps(favorites))
    return strategy_id in favorites


# ==================== НАСТРОЙКИ ПРЯМОГО РЕЖИМА ====================

def get_base_args_selection() -> str:
    """Получает выбранный вариант базовых аргументов"""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, DIRECT_PATH) as key:
            value, _ = winreg.QueryValueEx(key, "BaseArgsSelection")
            return value
    except:
        return "windivert_all"

def set_base_args_selection(selection: str) -> bool:
    """Сохраняет вариант базовых аргументов"""
    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, DIRECT_PATH) as key:
            winreg.SetValueEx(key, "BaseArgsSelection", 0, winreg.REG_SZ, selection)
            log(f"Базовые аргументы: {selection}", "INFO")
            return True
    except Exception as e:
        log(f"Ошибка сохранения базовых аргументов: {e}", "❌ ERROR")
        return False

def get_allzone_hostlist_enabled() -> bool:
    """Получает состояние замены other.txt на allzone.txt"""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, DIRECT_PATH) as key:
            value, _ = winreg.QueryValueEx(key, "AllzoneHostlistEnabled")
            return bool(value)
    except:
        return False

def set_allzone_hostlist_enabled(enabled: bool) -> bool:
    """Сохраняет состояние замены other.txt на allzone.txt"""
    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, DIRECT_PATH) as key:
            winreg.SetValueEx(key, "AllzoneHostlistEnabled", 0, winreg.REG_DWORD, int(enabled))
            return True
    except:
        return False

def get_wssize_enabled() -> bool:
    """Получает настройку включения --wssize"""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, DIRECT_PATH) as key:
            value, _ = winreg.QueryValueEx(key, "WSSizeEnabled")
            return bool(value)
    except:
        return False

def set_wssize_enabled(enabled: bool) -> bool:
    """Сохраняет настройку --wssize"""
    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, DIRECT_PATH) as key:
            winreg.SetValueEx(key, "WSSizeEnabled", 0, winreg.REG_DWORD, int(enabled))
            return True
    except:
        return False

def get_remove_hostlists_enabled() -> bool:
    """Получает состояние 'применить ко всем сайтам'"""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, DIRECT_PATH) as key:
            value, _ = winreg.QueryValueEx(key, "RemoveHostlistsEnabled")
            return bool(value)
    except:
        return False

def set_remove_hostlists_enabled(enabled: bool) -> bool:
    """Сохраняет 'применить ко всем сайтам'"""
    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, DIRECT_PATH) as key:
            winreg.SetValueEx(key, "RemoveHostlistsEnabled", 0, winreg.REG_DWORD, int(enabled))
            return True
    except:
        return False

def get_remove_ipsets_enabled() -> bool:
    """Получает состояние 'применить ко всем IP'"""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, DIRECT_PATH) as key:
            value, _ = winreg.QueryValueEx(key, "RemoveIpsetsEnabled")
            return bool(value)
    except:
        return False

def set_remove_ipsets_enabled(enabled: bool) -> bool:
    """Сохраняет 'применить ко всем IP'"""
    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, DIRECT_PATH) as key:
            winreg.SetValueEx(key, "RemoveIpsetsEnabled", 0, winreg.REG_DWORD, int(enabled))
            return True
    except:
        return False


# ==================== ВЫБОРЫ СТРАТЕГИЙ ====================

def _category_to_reg_key(category_key: str) -> str:
    """Преобразует ключ категории в ключ реестра"""
    # youtube_udp -> YoutubeUdp
    parts = category_key.split('_')
    return "DirectStrategy" + ''.join(part.capitalize() for part in parts)


def get_direct_strategy_selections() -> dict:
    """Возвращает сохраненные выборы стратегий для прямого запуска"""
    from .strategies_registry import registry
    
    try:
        selections = {}
        
        for category_key in registry.get_all_category_keys():
            reg_key = _category_to_reg_key(category_key)
            value = reg(DIRECT_STRATEGY_KEY, reg_key)
            if value:
                selections[category_key] = value
        
        # Заполняем недостающие значения по умолчанию
        default_selections = registry.get_default_selections()
        for key, default_value in default_selections.items():
            if key not in selections:
                selections[key] = default_value
                
        return selections
        
    except Exception as e:
        log(f"Ошибка загрузки выборов стратегий: {e}", "❌ ERROR")
        from .strategies_registry import registry
        return registry.get_default_selections()


def set_direct_strategy_selections(selections: dict) -> bool:
    """Сохраняет выборы стратегий для прямого запуска"""
    from .strategies_registry import registry
    
    try:
        success = True
        
        for category_key, strategy_id in selections.items():
            if category_key in registry.get_all_category_keys():
                reg_key = _category_to_reg_key(category_key)
                result = reg(DIRECT_STRATEGY_KEY, reg_key, strategy_id)
                success = success and (result is not False)
        
        if success:
            log("Выборы стратегий сохранены", "DEBUG")
        
        return success
        
    except Exception as e:
        log(f"Ошибка сохранения выборов: {e}", "❌ ERROR")
        return False


def get_direct_strategy_for_category(category_key: str) -> str:
    """Получает выбранную стратегию для конкретной категории"""
    from .strategies_registry import registry
    
    reg_key = _category_to_reg_key(category_key)
    value = reg(DIRECT_STRATEGY_KEY, reg_key)
    
    if value:
        return value
    
    # Возвращаем значение по умолчанию
    category_info = registry.get_category_info(category_key)
    if category_info:
        return category_info.default_strategy
    
    return "none"


def set_direct_strategy_for_category(category_key: str, strategy_id: str) -> bool:
    """Сохраняет выбранную стратегию для категории"""
    reg_key = _category_to_reg_key(category_key)
    return reg(DIRECT_STRATEGY_KEY, reg_key, strategy_id)


# ==================== ИМПОРТ СТРАТЕГИЙ ====================

from .strategies_registry import (
    registry,
    get_strategies_registry,
    get_category_strategies,
    get_category_info,
    get_tab_names,
    get_tab_tooltips,
    get_default_selections,
    get_category_icon,
    CATEGORIES_REGISTRY,
    CategoryInfo,
)


# ==================== ЭКСПОРТ ====================

__all__ = [
    # Реестр стратегий
    'registry',
    'get_strategies_registry',
    'get_category_strategies', 
    'get_category_info',
    'get_tab_names',
    'get_tab_tooltips',
    'get_default_selections',
    'get_category_icon',
    'CATEGORIES_REGISTRY',
    'CategoryInfo',
    
    # Настройки UI
    'get_tabs_pinned',
    'set_tabs_pinned',
    'get_keep_dialog_open',
    'set_keep_dialog_open',
    
    # Методы запуска
    'get_strategy_launch_method',
    'set_strategy_launch_method',
    
    # Избранные стратегии
    'get_favorite_strategies',
    'get_favorites_for_category',
    'invalidate_favorites_cache',
    'add_favorite_strategy',
    'remove_favorite_strategy',
    'is_favorite_strategy',
    'toggle_favorite_strategy',
    'clear_favorite_strategies',
    'get_all_favorite_strategies_flat',
    
    # Legacy избранные
    'get_favorite_strategies_legacy',
    'is_favorite_strategy_legacy',
    'toggle_favorite_strategy_legacy',
    
    # Настройки прямого режима
    'get_base_args_selection',
    'set_base_args_selection',
    'get_allzone_hostlist_enabled',
    'set_allzone_hostlist_enabled',
    'get_wssize_enabled',
    'set_wssize_enabled',
    'get_remove_hostlists_enabled',
    'set_remove_hostlists_enabled',
    'get_remove_ipsets_enabled',
    'set_remove_ipsets_enabled',
    
    # Выборы стратегий
    'get_direct_strategy_selections',
    'set_direct_strategy_selections',
    'get_direct_strategy_for_category',
    'set_direct_strategy_for_category',
]