# strategy_menu/__init__.py
import winreg
import json
from log import log
from config import reg

REGISTRY_PATH = r"Software\ZapretReg2"
DIRECT_PATH = r"Software\ZapretReg2\DirectMethod"

def get_strategy_launch_method():
    """Получает метод запуска стратегий из реестра"""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_PATH) as key:
            value, _ = winreg.QueryValueEx(key, "StrategyLaunchMethod")
            return value.lower() if value else "direct"
    except:
        # ✅ При первом запуске устанавливаем direct
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

# ───────────── Настройки UI диалога ─────────────

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
        log(f"Настройка закрепления табов сохранена: {'закреплено' if pinned else 'не закреплено'}", "INFO")
    else:
        log(f"Ошибка сохранения настройки закрепления табов", "❌ ERROR")
    return success

def get_keep_dialog_open() -> bool:
    """Получает настройку сохранения диалога открытым после выбора стратегии"""
    result = reg(DIRECT_PATH, "KeepDialogOpen")
    if result is not None:
        try:
            return bool(int(result))
        except (ValueError, TypeError):
            return False
    return False  # По умолчанию закрываем диалог

def set_keep_dialog_open(enabled: bool) -> bool:
    """Сохраняет настройку сохранения диалога открытым после выбора стратегии"""
    success = reg(DIRECT_PATH, "KeepDialogOpen", int(enabled))
    if success:
        log(f"Настройка 'не закрывать окно' сохранена: {'включено' if enabled else 'выключено'}", "INFO")
    else:
        log(f"Ошибка сохранения настройки 'не закрывать окно'", "❌ ERROR")
    return success

# ───────────── Кэширование избранных ─────────────

_favorites_cache = {}
_favorites_cache_time = 0
FAVORITES_CACHE_TTL = 0.5  # Кэш живет 0.5 секунды

def get_favorites_for_category(category_key):
    """Получает все избранные стратегии для категории (кэшированный вариант)"""
    import time
    global _favorites_cache, _favorites_cache_time
    
    current_time = time.time()
    
    # Проверяем кэш
    if current_time - _favorites_cache_time < FAVORITES_CACHE_TTL:
        return _favorites_cache.get(category_key, set())
    
    # Обновляем кэш
    favorites = get_favorite_strategies()
    _favorites_cache = {
        key: set(values) for key, values in favorites.items()
    }
    _favorites_cache_time = current_time
    
    return _favorites_cache.get(category_key, set())

def invalidate_favorites_cache():
    """Сбрасывает кэш избранных (вызывать после изменений)"""
    global _favorites_cache_time
    _favorites_cache_time = 0

# ───────────── Избранные стратегии (СТАРАЯ ВЕРСИЯ - для обратной совместимости) ─────────────

def get_favorite_strategies_legacy():
    """Получает список ID избранных стратегий (старая версия без категорий)"""
    try:
        result = reg(REGISTRY_PATH, "FavoriteStrategies")
        if result:
            return json.loads(result)
        return []
    except Exception as e:
        log(f"Ошибка загрузки избранных стратегий (legacy): {e}", "DEBUG")
        return []

def add_favorite_strategy_legacy(strategy_id):
    """Добавляет стратегию в избранные (старая версия)"""
    try:
        favorites = get_favorite_strategies_legacy()
        if strategy_id not in favorites:
            favorites.append(strategy_id)
            reg(REGISTRY_PATH, "FavoriteStrategies", json.dumps(favorites))
            log(f"Стратегия {strategy_id} добавлена в избранные (legacy)", "DEBUG")
            return True
        return False
    except Exception as e:
        log(f"Ошибка добавления стратегии в избранные (legacy): {e}", "ERROR")
        return False

def remove_favorite_strategy_legacy(strategy_id):
    """Удаляет стратегию из избранных (старая версия)"""
    try:
        favorites = get_favorite_strategies_legacy()
        if strategy_id in favorites:
            favorites.remove(strategy_id)
            reg(REGISTRY_PATH, "FavoriteStrategies", json.dumps(favorites))
            log(f"Стратегия {strategy_id} удалена из избранных (legacy)", "DEBUG")
            return True
        return False
    except Exception as e:
        log(f"Ошибка удаления стратегии из избранных (legacy): {e}", "ERROR")
        return False

def is_favorite_strategy_legacy(strategy_id):
    """Проверяет, является ли стратегия избранной (старая версия)"""
    favorites = get_favorite_strategies_legacy()
    return strategy_id in favorites

def toggle_favorite_strategy_legacy(strategy_id):
    """Переключает статус избранной стратегии (старая версия)"""
    if is_favorite_strategy_legacy(strategy_id):
        remove_favorite_strategy_legacy(strategy_id)
        return False
    else:
        add_favorite_strategy_legacy(strategy_id)
        return True

def clear_favorite_strategies_legacy():
    """Очищает список избранных стратегий (старая версия)"""
    try:
        reg(REGISTRY_PATH, "FavoriteStrategies", json.dumps([]))
        log("Список избранных стратегий очищен (legacy)", "DEBUG")
        return True
    except Exception as e:
        log(f"Ошибка очистки избранных стратегий (legacy): {e}", "ERROR")
        return False

# ───────────── Избранные стратегии (НОВАЯ ВЕРСИЯ - ПО КАТЕГОРИЯМ) ─────────────

def get_favorite_strategies(category=None):
    """
    Получает избранные стратегии
    
    Args:
        category: Если указано, возвращает избранные только для этой категории.
                 Если None, возвращает весь словарь категорий с избранными
    
    Returns:
        Если category указано: список ID избранных стратегий для категории
        Если category=None: словарь {category: [strategy_ids]}
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
        log(f"Ошибка загрузки избранных стратегий: {e}", "DEBUG")
        return [] if category else {}

def add_favorite_strategy(strategy_id, category):
    """
    Добавляет стратегию в избранные для конкретной категории
    
    Args:
        strategy_id: ID стратегии
        category: Категория (вкладка)
    """
    try:
        favorites_dict = get_favorite_strategies()
        if not isinstance(favorites_dict, dict):
            favorites_dict = {}
        
        if category not in favorites_dict:
            favorites_dict[category] = []
        
        if strategy_id not in favorites_dict[category]:
            favorites_dict[category].append(strategy_id)
            reg(REGISTRY_PATH, "FavoriteStrategiesByCategory", json.dumps(favorites_dict))
            invalidate_favorites_cache()  # ✅ Сбрасываем кэш
            log(f"Стратегия {strategy_id} добавлена в избранные для {category}", "DEBUG")
            return True
        return False
    except Exception as e:
        log(f"Ошибка добавления стратегии в избранные: {e}", "ERROR")
        return False

def remove_favorite_strategy(strategy_id, category):
    """
    Удаляет стратегию из избранных для конкретной категории
    
    Args:
        strategy_id: ID стратегии
        category: Категория (вкладка)
    """
    try:
        favorites_dict = get_favorite_strategies()
        if not isinstance(favorites_dict, dict):
            return False
        
        if category in favorites_dict and strategy_id in favorites_dict[category]:
            favorites_dict[category].remove(strategy_id)
            
            # Удаляем пустые категории
            if not favorites_dict[category]:
                del favorites_dict[category]
                
            reg(REGISTRY_PATH, "FavoriteStrategiesByCategory", json.dumps(favorites_dict))
            invalidate_favorites_cache()  # ✅ Сбрасываем кэш
            log(f"Стратегия {strategy_id} удалена из избранных для {category}", "DEBUG")
            return True
        return False
    except Exception as e:
        log(f"Ошибка удаления стратегии из избранных: {e}", "ERROR")
        return False

def is_favorite_strategy(strategy_id, category=None):
    """
    Проверяет, является ли стратегия избранной
    
    Args:
        strategy_id: ID стратегии
        category: Если указано, проверяет только для этой категории.
                 Если None, проверяет во всех категориях
    
    Returns:
        True если стратегия в избранных
    """
    favorites_dict = get_favorite_strategies()
    if not isinstance(favorites_dict, dict):
        return False
    
    if category:
        return strategy_id in favorites_dict.get(category, [])
    else:
        # Проверяем во всех категориях
        for cat_favorites in favorites_dict.values():
            if strategy_id in cat_favorites:
                return True
        return False

def toggle_favorite_strategy(strategy_id, category):
    """
    Переключает статус избранной стратегии для категории
    
    Args:
        strategy_id: ID стратегии
        category: Категория (вкладка)
    """
    if is_favorite_strategy(strategy_id, category):
        remove_favorite_strategy(strategy_id, category)
        return False
    else:
        add_favorite_strategy(strategy_id, category)
        return True

def clear_favorite_strategies(category=None):
    """
    Очищает список избранных стратегий
    
    Args:
        category: Если указано, очищает только для этой категории.
                 Если None, очищает все избранные
    """
    try:
        if category:
            favorites_dict = get_favorite_strategies()
            if not isinstance(favorites_dict, dict):
                return True
            
            if category in favorites_dict:
                del favorites_dict[category]
                reg(REGISTRY_PATH, "FavoriteStrategiesByCategory", json.dumps(favorites_dict))
                invalidate_favorites_cache()  # ✅ Сбрасываем кэш
                log(f"Список избранных стратегий для {category} очищен", "DEBUG")
        else:
            reg(REGISTRY_PATH, "FavoriteStrategiesByCategory", json.dumps({}))
            invalidate_favorites_cache()  # ✅ Сбрасываем кэш
            log("Все списки избранных стратегий очищены", "DEBUG")
        return True
    except Exception as e:
        log(f"Ошибка очистки избранных стратегий: {e}", "ERROR")
        return False

def get_all_favorite_strategies_flat():
    """
    Возвращает плоский список всех избранных стратегий из всех категорий
    (для обратной совместимости)
    """
    favorites_dict = get_favorite_strategies()
    if not isinstance(favorites_dict, dict):
        return []
    
    all_favorites = set()
    for cat_favorites in favorites_dict.values():
        all_favorites.update(cat_favorites)
    
    return list(all_favorites)
        
# ───────────── Настройки прямого метода ─────────────

def get_base_args_selection() -> str:
    """Получает выбранный вариант базовых аргументов"""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, DIRECT_PATH) as key:
            value, _ = winreg.QueryValueEx(key, "BaseArgsSelection")
            return value
    except:
        return "windivert_all"

def set_base_args_selection(selection: str) -> bool:
    """Сохраняет выбранный вариант базовых аргументов"""
    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, DIRECT_PATH) as key:
            winreg.SetValueEx(key, "BaseArgsSelection", 0, winreg.REG_SZ, selection)
            log(f"Базовые аргументы изменены на: {selection}", "INFO")
            return True
    except Exception as e:
        log(f"Ошибка сохранения базовых аргументов: {e}", "❌ ERROR")
        return False
    
def get_allzone_hostlist_enabled() -> bool:
    """Получает состояние настройки замены other.txt на allzone.txt"""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, DIRECT_PATH) as key:
            value, _ = winreg.QueryValueEx(key, "AllzoneHostlistEnabled")
            return bool(value)
    except:
        return False # По умолчанию выключено

def get_wssize_enabled():
    """Получает настройку включения параметра --wssize из реестра"""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, DIRECT_PATH) as key:
            value, _ = winreg.QueryValueEx(key, "WSSizeEnabled")
            return bool(value)
    except:
        return False # По умолчанию выключено
    
def set_allzone_hostlist_enabled(enabled: bool):
    """Сохраняет состояние настройки замены other.txt на allzone.txt"""
    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, DIRECT_PATH) as key:
            winreg.SetValueEx(key, "AllzoneHostlistEnabled", 0, winreg.REG_DWORD, int(enabled))
            log(f"Настройка allzone.txt сохранена: {enabled}", "INFO")
            return True
    except Exception as e:
        log(f"Ошибка сохранения настройки allzone.txt: {e}", "❌ ERROR")
        return False

def set_wssize_enabled(enabled: bool):
    """Сохраняет настройку включения параметра --wssize в реестр"""
    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, DIRECT_PATH) as key:
            winreg.SetValueEx(key, "WSSizeEnabled", 0, winreg.REG_DWORD, int(enabled))
            log(f"Настройка wssize_enabled сохранена: {enabled}", "INFO")
            return True
    except Exception as e:
        log(f"Ошибка сохранения настройки wssize_enabled: {e}", "❌ ERROR")
        return False


# ───────────── ЦЕНТРАЛЬНЫЕ ФУНКЦИИ ДЛЯ РАБОТЫ СО СТРАТЕГИЯМИ ─────────────

_DIRECT_STRATEGY_KEY = r"Software\ZapretReg2\DirectStrategy"

def get_direct_strategy_selections() -> dict:
    """Возвращает сохраненные выборы стратегий для прямого запуска"""
    _generate_category_functions()  # ✅ Генерируем только при необходимости
    
    from .strategies_registry import registry
    
    try:
        selections = {}
        
        # Получаем все ключи категорий из реестра
        for category_key in registry.get_all_category_keys():
            reg_key = f"DirectStrategy{category_key.title().replace('_', '')}"
            value = reg(_DIRECT_STRATEGY_KEY, reg_key)
            if value:
                selections[category_key] = value
        
        # Заполняем недостающие значения по умолчанию
        default_selections = registry.get_default_selections()
        for key, default_value in default_selections.items():
            if key not in selections:
                selections[key] = default_value
                
        log(f"Загружены выборы стратегий из реестра", "DEBUG")
        return selections
        
    except Exception as e:
        log(f"Ошибка загрузки выборов стратегий: {e}", "❌ ERROR")
        return registry.get_default_selections()

def set_direct_strategy_selections(selections: dict) -> bool:
    """Сохраняет выборы стратегий для прямого запуска в реестр"""
    _generate_category_functions()  # ✅ Генерируем только при необходимости
    
    from .strategies_registry import registry
    
    try:
        success = True
        
        for category_key, strategy_id in selections.items():
            if category_key in registry.get_all_category_keys():
                reg_key = f"DirectStrategy{category_key.title().replace('_', '')}"
                success &= reg(_DIRECT_STRATEGY_KEY, reg_key, strategy_id)
        
        if success:
            log(f"Сохранены выборы стратегий в реестр", "DEBUG")
        else:
            log("Ошибка при сохранении некоторых выборов стратегий", "⚠ WARNING")
            
        return success
        
    except Exception as e:
        log(f"Ошибка сохранения выборов стратегий: {e}", "❌ ERROR")
        return False

# Генерируем функции get/set для каждой категории динамически

_functions_generated = False

def _generate_category_functions():
    """Генерирует функции get/set для каждой категории"""
    global _functions_generated
    
    if _functions_generated:
        return
    
    from .strategies_registry import registry
    
    for category_key in registry.get_all_category_keys():
        default_strategy = registry.get_category_info(category_key).default_strategy
        reg_key = f"DirectStrategy{category_key.title().replace('_', '')}"
        
        # Создаем функции get/set для каждой категории
        def make_getter(cat_key, def_strategy, r_key):
            def getter():
                result = reg(_DIRECT_STRATEGY_KEY, r_key)
                return result if result else def_strategy
            return getter
        
        def make_setter(r_key):
            def setter(strategy_id: str):
                return reg(_DIRECT_STRATEGY_KEY, r_key, strategy_id)
            return setter
        
        # Добавляем функции в глобальное пространство имен
        getter_name = f"get_direct_strategy_{category_key}"
        setter_name = f"set_direct_strategy_{category_key}"
        
        globals()[getter_name] = make_getter(category_key, default_strategy, reg_key)
        globals()[setter_name] = make_setter(reg_key)
    
    _functions_generated = True

# ❌ НЕ вызываем функции при импорте!
# _generate_category_functions()  # Закомментировали


# ───────────── ИМПОРТ СТРАТЕГИЙ ─────────────

# Импортируем стратегии из реестра для совместимости
from .strategies_registry import (
    registry,
    get_strategies_registry,
    get_category_strategies,
    get_category_info,
    get_all_strategies,
    get_tab_names,
    get_tab_tooltips,
    get_default_selections
)

# ❌ НЕ экспортируем отдельные словари стратегий при импорте!
# def _export_individual_strategies():
#     """Экспортирует отдельные словари стратегий"""
#     strategies = registry.strategies
#     for category_key, strategy_dict in strategies.items():
#         const_name = f"{category_key.upper()}_STRATEGIES"
#         globals()[const_name] = strategy_dict

# _export_individual_strategies()  # Закомментировали

def get_remove_hostlists_enabled() -> bool:
    """Получает состояние настройки 'применить ко всем сайтам'"""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, DIRECT_PATH) as key:
            value, _ = winreg.QueryValueEx(key, "RemoveHostlistsEnabled")
            return bool(value)
    except:
        return False  # По умолчанию выключено

def set_remove_hostlists_enabled(enabled: bool) -> bool:
    """Сохраняет состояние настройки 'применить ко всем сайтам'"""
    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, DIRECT_PATH) as key:
            winreg.SetValueEx(key, "RemoveHostlistsEnabled", 0, winreg.REG_DWORD, int(enabled))
            log(f"Настройка 'применить ко всем сайтам' сохранена: {enabled}", "INFO")
            return True
    except Exception as e:
        log(f"Ошибка сохранения настройки 'применить ко всем сайтам': {e}", "❌ ERROR")
        return False

def get_remove_ipsets_enabled() -> bool:
    """Получает состояние настройки 'применить ко всем IP-адресам'"""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, DIRECT_PATH) as key:
            value, _ = winreg.QueryValueEx(key, "RemoveIpsetsEnabled")
            return bool(value)
    except:
        return False  # По умолчанию выключено

def set_remove_ipsets_enabled(enabled: bool) -> bool:
    """Сохраняет состояние настройки 'применить ко всем IP-адресам'"""
    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, DIRECT_PATH) as key:
            winreg.SetValueEx(key, "RemoveIpsetsEnabled", 0, winreg.REG_DWORD, int(enabled))
            log(f"Настройка 'применить ко всем IP-адресам' сохранена: {enabled}", "INFO")
            return True
    except Exception as e:
        log(f"Ошибка сохранения настройки 'применить ко всем IP-адресам': {e}", "❌ ERROR")
        return False

__all__ = [
    # Стратегии (реестр)
    'registry',
    'get_strategies_registry',
    'get_category_strategies', 
    'get_category_info',
    'get_all_strategies',
    'get_tab_names',
    'get_tab_tooltips',
    'get_default_selections',
    
    # Настройки UI диалога
    'get_tabs_pinned',
    'set_tabs_pinned',
    'get_keep_dialog_open',
    'set_keep_dialog_open',
    
    # Методы запуска
    'get_strategy_launch_method',
    'set_strategy_launch_method',
    
    # Избранные стратегии (новая версия)
    'get_favorite_strategies',
    'get_favorites_for_category',  # ✅ ДОБАВЛЕНО
    'invalidate_favorites_cache',   # ✅ ДОБАВЛЕНО
    'add_favorite_strategy',
    'remove_favorite_strategy',
    'is_favorite_strategy',
    'toggle_favorite_strategy',
    'clear_favorite_strategies',
    'get_all_favorite_strategies_flat',
    
    # Избранные стратегии (legacy - для совместимости)
    'get_favorite_strategies_legacy',
    'add_favorite_strategy_legacy',
    'remove_favorite_strategy_legacy',
    'is_favorite_strategy_legacy',
    'toggle_favorite_strategy_legacy',
    'clear_favorite_strategies_legacy',
    
    # Настройки прямого режима
    'get_base_args_selection',
    'set_base_args_selection',
    'get_allzone_hostlist_enabled',
    'set_allzone_hostlist_enabled',
    'get_wssize_enabled',
    'set_wssize_enabled',
    'get_remove_hostlists_enabled',  # ✅ НОВОЕ
    'set_remove_hostlists_enabled',  # ✅ НОВОЕ
    'get_remove_ipsets_enabled',     # ✅ НОВОЕ
    'set_remove_ipsets_enabled',     # ✅ НОВОЕ
    
    # Выборы стратегий
    'get_direct_strategy_selections',
    'set_direct_strategy_selections',
]