"""
Загрузчик стратегий из JSON файлов.

Стратегии загружаются из:
1. {INDEXJSON_FOLDER}/strategies/builtin/ - встроенные стратегии (обновляются с программой)
2. {INDEXJSON_FOLDER}/strategies/user/ - пользовательские стратегии (сохраняются при обновлении)

Каждая категория имеет свой JSON файл:
- tcp.json - TCP стратегии (YouTube, Discord TCP, и т.д.)
- udp.json - UDP стратегии (QUIC, игры)
- http80.json - HTTP порт 80
- discord_voice.json - Discord голос
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from log import log
from config import INDEXJSON_FOLDER

# Путь к папке со стратегиями - используем INDEXJSON_FOLDER из конфига
# Структура: {INDEXJSON_FOLDER}/strategies/builtin/ и {INDEXJSON_FOLDER}/strategies/user/
STRATEGIES_DIR = Path(INDEXJSON_FOLDER) / "strategies"
BUILTIN_DIR = STRATEGIES_DIR / "builtin"
USER_DIR = STRATEGIES_DIR / "user"

# Маппинг label строк на константы
LABEL_MAP = {
    "recommended": "recommended",
    "game": "game", 
    "caution": "caution",
    "experimental": "experimental",
    "stable": "stable",
    None: None,
    "null": None,
}


def ensure_directories():
    """Создаёт необходимые директории если их нет"""
    BUILTIN_DIR.mkdir(parents=True, exist_ok=True)
    USER_DIR.mkdir(parents=True, exist_ok=True)


def load_json_file(filepath: Path) -> Optional[Dict]:
    """Загружает JSON файл"""
    try:
        if not filepath.exists():
            return None
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        log(f"Ошибка парсинга JSON {filepath}: {e}", "ERROR")
        return None
    except Exception as e:
        log(f"Ошибка чтения {filepath}: {e}", "ERROR")
        return None


def save_json_file(filepath: Path, data: Dict) -> bool:
    """Сохраняет данные в JSON файл"""
    try:
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        log(f"Ошибка сохранения {filepath}: {e}", "ERROR")
        return False


def validate_strategy(strategy: Dict, strategy_id: str = None) -> tuple[bool, str]:
    """
    Валидирует стратегию.
    
    Returns:
        (is_valid, error_message)
    """
    # Обязательные поля
    if strategy_id:
        strategy['id'] = strategy_id
    
    if 'id' not in strategy or not strategy['id']:
        return False, "Отсутствует id стратегии"
    
    if 'name' not in strategy or not strategy['name']:
        return False, "Отсутствует name стратегии"
    
    if 'args' not in strategy:
        return False, "Отсутствует args стратегии"
    
    # Проверка id на допустимые символы
    strategy_id = strategy['id']
    if not all(c.isalnum() or c == '_' for c in strategy_id):
        return False, f"id '{strategy_id}' содержит недопустимые символы (разрешены: a-z, 0-9, _)"
    
    # Проверка label
    label = strategy.get('label')
    if label is not None and label not in LABEL_MAP:
        return False, f"Неизвестный label: {label}"
    
    # Проверка blobs - должен быть список
    blobs = strategy.get('blobs', [])
    if not isinstance(blobs, list):
        return False, "blobs должен быть списком"
    
    return True, ""


def normalize_strategy(strategy: Dict) -> Dict:
    """Нормализует стратегию, добавляя значения по умолчанию"""
    return {
        'id': strategy.get('id', ''),
        'name': strategy.get('name', 'Без названия'),
        'description': strategy.get('description', ''),
        'author': strategy.get('author', 'unknown'),
        'version': strategy.get('version', '1.0'),
        'label': LABEL_MAP.get(strategy.get('label'), None),
        'blobs': strategy.get('blobs', []),
        'args': strategy.get('args', ''),
        'enabled': strategy.get('enabled', True),
        'user_created': strategy.get('user_created', False),
    }


def load_category_strategies(category: str) -> Dict[str, Dict]:
    """
    Загружает стратегии для категории из builtin и user директорий.
    User стратегии имеют приоритет (перезаписывают builtin с тем же id).
    
    Args:
        category: Имя категории (tcp, udp, http80, discord_voice)
        
    Returns:
        Словарь {strategy_id: strategy_dict}
    """
    ensure_directories()
    strategies = {}
    
    # Загружаем builtin стратегии
    builtin_file = BUILTIN_DIR / f"{category}.json"
    builtin_data = load_json_file(builtin_file)
    
    if builtin_data and 'strategies' in builtin_data:
        for strategy in builtin_data['strategies']:
            is_valid, error = validate_strategy(strategy)
            if is_valid:
                normalized = normalize_strategy(strategy)
                normalized['_source'] = 'builtin'
                strategies[normalized['id']] = normalized
            else:
                log(f"Пропущена невалидная builtin стратегия: {error}", "WARNING")
    
    # Загружаем user стратегии (перезаписывают builtin)
    user_file = USER_DIR / f"{category}.json"
    user_data = load_json_file(user_file)
    
    if user_data and 'strategies' in user_data:
        for strategy in user_data['strategies']:
            is_valid, error = validate_strategy(strategy)
            if is_valid:
                normalized = normalize_strategy(strategy)
                normalized['_source'] = 'user'
                normalized['user_created'] = True
                strategies[normalized['id']] = normalized
            else:
                log(f"Пропущена невалидная user стратегия: {error}", "WARNING")
    
    log(f"Загружено {len(strategies)} стратегий для категории '{category}'", "DEBUG")
    return strategies


def save_user_strategy(category: str, strategy: Dict) -> tuple[bool, str]:
    """
    Сохраняет пользовательскую стратегию.
    
    Args:
        category: Категория (tcp, udp, http80, discord_voice)
        strategy: Словарь стратегии
        
    Returns:
        (success, error_message)
    """
    is_valid, error = validate_strategy(strategy)
    if not is_valid:
        return False, error
    
    ensure_directories()
    user_file = USER_DIR / f"{category}.json"
    
    # Загружаем существующие user стратегии
    user_data = load_json_file(user_file) or {'strategies': []}
    
    # Ищем существующую стратегию с таким же id
    strategy_id = strategy['id']
    existing_idx = None
    for i, s in enumerate(user_data['strategies']):
        if s.get('id') == strategy_id:
            existing_idx = i
            break
    
    # Помечаем как пользовательскую
    strategy['user_created'] = True
    
    if existing_idx is not None:
        # Обновляем существующую
        user_data['strategies'][existing_idx] = strategy
    else:
        # Добавляем новую
        user_data['strategies'].append(strategy)
    
    if save_json_file(user_file, user_data):
        log(f"Сохранена пользовательская стратегия '{strategy_id}' в {category}", "INFO")
        return True, ""
    else:
        return False, "Ошибка записи файла"


def delete_user_strategy(category: str, strategy_id: str) -> tuple[bool, str]:
    """
    Удаляет пользовательскую стратегию.
    
    Returns:
        (success, error_message)
    """
    user_file = USER_DIR / f"{category}.json"
    user_data = load_json_file(user_file)
    
    if not user_data or 'strategies' not in user_data:
        return False, "Файл пользовательских стратегий не найден"
    
    # Ищем и удаляем
    original_len = len(user_data['strategies'])
    user_data['strategies'] = [s for s in user_data['strategies'] if s.get('id') != strategy_id]
    
    if len(user_data['strategies']) == original_len:
        return False, f"Стратегия '{strategy_id}' не найдена"
    
    if save_json_file(user_file, user_data):
        log(f"Удалена пользовательская стратегия '{strategy_id}' из {category}", "INFO")
        return True, ""
    else:
        return False, "Ошибка записи файла"


def get_all_categories() -> List[str]:
    """Возвращает список всех категорий с JSON файлами"""
    ensure_directories()
    categories = set()
    
    # Собираем из builtin
    for f in BUILTIN_DIR.glob("*.json"):
        if f.name != "schema.json":
            categories.add(f.stem)
    
    # Собираем из user
    for f in USER_DIR.glob("*.json"):
        categories.add(f.stem)
    
    return sorted(categories)


def export_strategies_to_json(strategies_dict: Dict[str, Dict], category: str, output_dir: Path = None) -> bool:
    """
    Экспортирует словарь стратегий в JSON файл.
    Используется для конвертации из старого формата.
    
    Args:
        strategies_dict: Словарь {id: strategy_data}
        category: Имя категории
        output_dir: Директория для сохранения (по умолчанию builtin)
    """
    if output_dir is None:
        output_dir = BUILTIN_DIR
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    strategies_list = []
    for strategy_id, data in strategies_dict.items():
        strategy = {
            'id': strategy_id,
            'name': data.get('name', strategy_id),
            'description': data.get('description', ''),
            'author': data.get('author', 'unknown'),
            'label': data.get('label'),
            'blobs': data.get('blobs', []),
            'args': data.get('args', ''),
        }
        strategies_list.append(strategy)
    
    output_data = {
        'category': category,
        'version': '1.0',
        'strategies': strategies_list
    }
    
    output_file = output_dir / f"{category}.json"
    return save_json_file(output_file, output_data)


# Для обратной совместимости - загрузка в старый формат
def load_strategies_as_dict(category: str) -> Dict[str, Dict]:
    """
    Загружает стратегии и возвращает в формате совместимом со старым кодом.
    
    Returns:
        Словарь {strategy_id: {name, description, author, label, blobs, args}}
    """
    strategies = load_category_strategies(category)
    result = {}
    
    for sid, data in strategies.items():
        if not data.get('enabled', True):
            continue
        
        result[sid] = {
            'name': data['name'],
            'description': data['description'],
            'author': data['author'],
            'label': data['label'],
            'blobs': data['blobs'],
            'args': data['args'],
        }
    
    return result

