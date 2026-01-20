"""
Загрузчик стратегий из TXT файлов (INI-подобный формат).

Стратегии загружаются из:
1. {INDEXJSON_FOLDER}/strategies/builtin/ - встроенные стратегии (обновляются с программой)
2. {INDEXJSON_FOLDER}/strategies/user/ - пользовательские стратегии (сохраняются при обновлении)

Каждая категория имеет свой TXT файл:
- tcp.txt - TCP стратегии (YouTube, Discord TCP, и т.д.)
- udp.txt - UDP стратегии (QUIC, игры)
- http80.txt - HTTP порт 80
- discord_voice.txt - Discord голос

Формат TXT файла:
    [strategy_id]
    name = Название стратегии
    author = Автор
    label = recommended|experimental|game|deprecated
    description = Описание
    blobs = blob1, blob2
    --arg1=value1
    --arg2=value2

    [another_strategy]
    ...
"""

import json
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from log import log
from config import INDEXJSON_FOLDER
from strategy_menu.user_categories_store import get_user_categories_file_path

# Путь к папке со стратегиями - используем INDEXJSON_FOLDER из конфига
# Структура: {INDEXJSON_FOLDER}/strategies/builtin/ и {INDEXJSON_FOLDER}/strategies/user/
STRATEGIES_DIR = Path(INDEXJSON_FOLDER) / "strategies"

# Fallback на локальную папку (для разработки)
_LOCAL_STRATEGIES_DIR = Path(__file__).parent

# Fallback на соседнюю папку zapret (для разработки из IDE)
# H:\Privacy\zapretgui -> H:\Privacy\zapret
_DEV_ZAPRET_DIR = Path(__file__).parent.parent.parent / "zapret" / "json" / "strategies"


def _has_categories_file(directory: Path) -> bool:
    """Проверяет наличие файла категорий (TXT или JSON)"""
    return (directory / "categories.txt").exists() or (directory / "categories.json").exists()


def _has_any_strategy_files(directory: Path) -> bool:
    """Проверяет, что директория похожа на strategies/* (есть txt/json файлы)."""
    try:
        return any(directory.glob("*.txt")) or any(directory.glob("*.json"))
    except Exception:
        return False


def _get_builtin_dir() -> Path:
    """Возвращает путь к builtin директории (с fallback)"""
    global_builtin = STRATEGIES_DIR / "builtin"
    local_builtin = _LOCAL_STRATEGIES_DIR / "builtin"
    dev_builtin = _DEV_ZAPRET_DIR / "builtin"

    # 1. Если глобальная папка существует и содержит стратегии - используем её
    if global_builtin.exists() and _has_any_strategy_files(global_builtin):
        return global_builtin

    # 2. Проверяем соседнюю папку zapret (для разработки из IDE)
    if dev_builtin.exists() and _has_any_strategy_files(dev_builtin):
        return dev_builtin

    # 3. Проверяем локальную папку strategy_menu/strategies/builtin
    if local_builtin.exists() and _has_any_strategy_files(local_builtin):
        return local_builtin

    # Возвращаем глобальную по умолчанию
    return global_builtin


def _get_user_dir() -> Path:
    """Возвращает путь к user директории"""
    global_user = STRATEGIES_DIR / "user"
    local_user = _LOCAL_STRATEGIES_DIR / "user"
    dev_user = _DEV_ZAPRET_DIR / "user"
    
    # Определяем откуда загружается builtin
    builtin_dir = _get_builtin_dir()
    
    # Если builtin из dev папки - user тоже оттуда
    if builtin_dir == _DEV_ZAPRET_DIR / "builtin":
        return dev_user
    
    # Если builtin из локальной папки - user тоже оттуда
    if builtin_dir == _LOCAL_STRATEGIES_DIR / "builtin":
        return local_user
    
    # Иначе используем глобальную
    return global_user


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
    _get_builtin_dir().mkdir(parents=True, exist_ok=True)
    _get_user_dir().mkdir(parents=True, exist_ok=True)


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


def load_txt_file(filepath: Path) -> Optional[Dict]:
    """
    Загружает стратегии из TXT файла в INI-подобном формате.

    Формат:
        [strategy_id]
        name = Название стратегии
        author = Автор
        label = recommended|experimental|game|deprecated
        description = Описание
        blobs = blob1, blob2
        --arg1=value1
        --arg2=value2

        [another_strategy]
        ...

    Returns:
        Dict в формате {'strategies': [...]} или None при ошибке
    """
    try:
        if not filepath.exists():
            return None

        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        strategies = []
        current_strategy = None
        current_args = []

        for line in content.splitlines():
            line = line.rstrip()

            # Пропускаем пустые строки
            if not line:
                continue

            # Пропускаем комментарии (строки начинающиеся с #)
            if line.startswith('#'):
                continue

            # Начало новой стратегии [id]
            if line.startswith('[') and line.endswith(']'):
                # Сохраняем предыдущую стратегию
                if current_strategy is not None:
                    current_strategy['args'] = '\n'.join(current_args)
                    strategies.append(current_strategy)

                # Начинаем новую
                strategy_id = line[1:-1].strip()
                current_strategy = {
                    'id': strategy_id,
                    'name': strategy_id,  # По умолчанию имя = id
                    'description': '',
                    'author': 'unknown',
                    'label': None,
                    'blobs': [],
                    'args': ''
                }
                current_args = []
                continue

            # Если нет текущей стратегии - пропускаем
            if current_strategy is None:
                continue

            # Аргументы (строки начинающиеся с --)
            if line.startswith('--'):
                current_args.append(line)
                continue

            # Метаданные (key = value)
            if '=' in line:
                key, _, value = line.partition('=')
                key = key.strip().lower()
                value = value.strip()

                if key == 'name':
                    current_strategy['name'] = value
                elif key == 'author':
                    current_strategy['author'] = value
                elif key == 'label':
                    current_strategy['label'] = value if value else None
                elif key == 'description':
                    current_strategy['description'] = value
                elif key == 'blobs':
                    # blobs = tls7, tls_google -> ['tls7', 'tls_google']
                    current_strategy['blobs'] = [b.strip() for b in value.split(',') if b.strip()]

        # Сохраняем последнюю стратегию
        if current_strategy is not None:
            current_strategy['args'] = '\n'.join(current_args)
            strategies.append(current_strategy)

        log(f"Загружено {len(strategies)} стратегий из TXT: {filepath.name}", "DEBUG")
        return {'strategies': strategies}

    except Exception as e:
        log(f"Ошибка чтения TXT {filepath}: {e}", "ERROR")
        return None


def save_txt_file(filepath: Path, data: Dict) -> bool:
    """
    Сохраняет стратегии в TXT файл в INI-подобном формате.

    Args:
        filepath: Путь к файлу
        data: Dict с ключом 'strategies' содержащим список стратегий

    Returns:
        True при успехе
    """
    try:
        filepath.parent.mkdir(parents=True, exist_ok=True)

        lines = []
        strategies = data.get('strategies', [])

        for i, strategy in enumerate(strategies):
            if i > 0:
                lines.append('')  # Пустая строка между стратегиями

            # [id]
            lines.append(f"[{strategy.get('id', 'unknown')}]")

            # Метаданные
            if strategy.get('name'):
                lines.append(f"name = {strategy['name']}")
            if strategy.get('author') and strategy['author'] != 'unknown':
                lines.append(f"author = {strategy['author']}")
            if strategy.get('label'):
                lines.append(f"label = {strategy['label']}")
            if strategy.get('description'):
                lines.append(f"description = {strategy['description']}")
            if strategy.get('blobs'):
                blobs = ', '.join(strategy['blobs'])
                lines.append(f"blobs = {blobs}")

            # Аргументы
            args = strategy.get('args', '')
            if args:
                # Разбиваем на строки если это одна длинная строка
                if '\n' in args:
                    for arg_line in args.split('\n'):
                        if arg_line.strip():
                            lines.append(arg_line.strip())
                else:
                    # Разбиваем по пробелам, каждый --arg на новую строку
                    for part in args.split():
                        if part.startswith('--'):
                            lines.append(part)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

        return True
    except Exception as e:
        log(f"Ошибка сохранения TXT {filepath}: {e}", "ERROR")
        return False


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


def _process_args(args: Union[str, List[str]], auto_number: bool = False) -> str:
    """
    Обрабатывает args:
    1. Если это список - склеивает в строку через пробел
    2. Если auto_number=True - добавляет :strategy=N ко ВСЕМ --lua-desync= на каждой строке
       (для combo стратегий все --lua-desync на одной строке получают одинаковый N)
    """
    if not args:
        return ''

    # Авто-нумерация стратегий (только для orchestra)
    if auto_number and isinstance(args, list):
        strategy_counter = 0
        processed_lines = []

        for line in args:
            # Пропускаем строки без lua-desync
            if '--lua-desync=' not in line:
                processed_lines.append(line)
                continue

            # Проверяем первый lua-desync на строке
            match = re.search(r'--lua-desync=([^\s]+)', line)
            if match:
                content = match.group(1)
                # circular/pass - это управление, не нумеруем
                if content.startswith('circular') or content == 'pass':
                    processed_lines.append(line)
                    continue
                # Если уже есть :strategy= - не добавляем
                if ':strategy=' in line:
                    processed_lines.append(line)
                    continue

                # Добавляем ОДИНАКОВЫЙ :strategy=N ко ВСЕМ lua-desync на строке (combo)
                strategy_counter += 1
                new_line = re.sub(
                    r'(--lua-desync=[^\s]+)',
                    rf'\1:strategy={strategy_counter}',
                    line
                )
                processed_lines.append(new_line)
            else:
                processed_lines.append(line)

        args = ' '.join(processed_lines)
    elif isinstance(args, list):
        args = ' '.join(args)

    return args


def normalize_strategy(strategy: Dict, auto_number: bool = False) -> Dict:
    """Нормализует стратегию, добавляя значения по умолчанию"""
    raw_args = strategy.get('args', '')
    processed_args = _process_args(raw_args, auto_number=auto_number)

    return {
        'id': strategy.get('id', ''),
        'name': strategy.get('name', 'Без названия'),
        'description': strategy.get('description', ''),
        'author': strategy.get('author', 'unknown'),
        'version': strategy.get('version', '1.0'),
        'label': LABEL_MAP.get(strategy.get('label'), None),
        'blobs': strategy.get('blobs', []),
        'args': processed_args,
        'enabled': strategy.get('enabled', True),
        'user_created': strategy.get('user_created', False),
    }


def _load_strategy_file(directory: Path, basename: str) -> Optional[Dict]:
    """
    Загружает файл стратегий в TXT (INI-подобном) формате.

    Args:
        directory: Директория с файлами
        basename: Имя файла без расширения (например 'tcp' или 'tcp_orchestra')

    Returns:
        Dict с ключом 'strategies' или None
    """
    txt_file = directory / f"{basename}.txt"
    if txt_file.exists():
        return load_txt_file(txt_file)

    return None


def load_category_strategies(category: str, strategy_set: str = None) -> Dict[str, Dict]:
    """
    Загружает стратегии для категории из builtin и user директорий.
    User стратегии имеют приоритет (перезаписывают builtin с тем же id).
    Поддерживает TXT (INI-подобный) и JSON форматы. TXT имеет приоритет.

    Args:
        category: Имя категории (tcp, udp, http80, discord_voice)
        strategy_set: Набор стратегий (None = стандартный, "orchestra" = tcp_orchestra и т.д.)

    Returns:
        Словарь {strategy_id: strategy_dict}
    """
    ensure_directories()
    strategies = {}

    # Определяем базовое имя файла на основе strategy_set
    if strategy_set:
        basename = f"{category}_{strategy_set}"
    else:
        basename = category

    builtin_dir = _get_builtin_dir()

    # Загружаем builtin стратегии (TXT или JSON)
    builtin_data = _load_strategy_file(builtin_dir, basename)

    # Если файл с суффиксом не найден, fallback на стандартный
    if builtin_data is None and strategy_set:
        log(f"Файл {basename}.txt/.json не найден, используем стандартный {category}", "DEBUG")
        builtin_data = _load_strategy_file(builtin_dir, category)

    # Специальная логика для Zapret 1: все UDP категории используют один файл
    if builtin_data is None and strategy_set == "zapret1":
        # UDP категории
        if category.endswith("_udp") or category.startswith("udp_") or category == "udp":
            basename = "udp_zapret1"
            builtin_data = _load_strategy_file(builtin_dir, basename)
            log(f"Zapret 1: используем {basename} для UDP категории '{category}'", "DEBUG")
        # Discord Voice
        elif category == "discord_voice":
            basename = "discord_voice_zapret1"
            builtin_data = _load_strategy_file(builtin_dir, basename)
            log(f"Zapret 1: используем {basename} для Discord Voice", "DEBUG")
        # HTTP80 категории
        elif category == "http80" or category.endswith("_http80"):
            basename = "http80_zapret1"
            builtin_data = _load_strategy_file(builtin_dir, basename)
            log(f"Zapret 1: используем {basename} для HTTP80 категории '{category}'", "DEBUG")
        # TCP категории (все остальные)
        else:
            basename = "tcp_zapret1"
            builtin_data = _load_strategy_file(builtin_dir, basename)
            log(f"Zapret 1: используем {basename} для TCP категории '{category}'", "DEBUG")

    # Авто-нумерация :strategy=N только для orchestra
    auto_number = (strategy_set == "orchestra")

    if builtin_data and 'strategies' in builtin_data:
        for strategy in builtin_data['strategies']:
            is_valid, error = validate_strategy(strategy)
            if is_valid:
                normalized = normalize_strategy(strategy, auto_number=auto_number)
                normalized['_source'] = 'builtin'
                strategies[normalized['id']] = normalized
            else:
                log(f"Пропущена невалидная builtin стратегия: {error}", "WARNING")

    # Загружаем user стратегии (перезаписывают builtin)
    user_data = _load_strategy_file(_get_user_dir(), category)

    if user_data and 'strategies' in user_data:
        for strategy in user_data['strategies']:
            is_valid, error = validate_strategy(strategy)
            if is_valid:
                normalized = normalize_strategy(strategy, auto_number=auto_number)
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
    user_file = _get_user_dir() / f"{category}.json"
    
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
    user_file = _get_user_dir() / f"{category}.json"
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
    for f in _get_builtin_dir().glob("*.json"):
        if f.name != "schema.json" and f.name != "categories.json":
            categories.add(f.stem)
    
    # Собираем из user
    for f in _get_user_dir().glob("*.json"):
        if f.name != "categories.json":
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
        output_dir = _get_builtin_dir()
    
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
def load_strategies_as_dict(category: str, strategy_set: str = None) -> Dict[str, Dict]:
    """
    Загружает стратегии и возвращает в формате совместимом со старым кодом.

    Args:
        category: Имя категории (tcp, udp, http80, discord_voice)
        strategy_set: Набор стратегий (None = стандартный, "orchestra" и т.д.)

    Returns:
        Словарь {strategy_id: {name, description, author, label, blobs, args}}
    """
    strategies = load_category_strategies(category, strategy_set)
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


# ==================== ЗАГРУЗКА КАТЕГОРИЙ ====================

def _parse_categories_txt_content(content: str, *, source_name: str) -> Optional[Dict]:
    try:
        categories = []
        current_category = None
        file_version = '1.0'
        file_description = ''

        for line in content.splitlines():
            line = line.rstrip()

            # Пропускаем пустые строки
            if not line:
                continue

            # Пропускаем комментарии (строки начинающиеся с #)
            if line.startswith('#'):
                continue

            # Начало новой категории [key]
            if line.startswith('[') and line.endswith(']'):
                # Сохраняем предыдущую категорию
                if current_category is not None:
                    categories.append(current_category)

                # Начинаем новую
                # Normalize keys to lower-case so categories match preset parsing logic
                # (preset blocks infer category keys in lower-case from filter tokens/filenames).
                raw_key = line[1:-1].strip()
                category_key = raw_key.lower()
                current_category = {
                    'key': category_key,
                    'full_name': raw_key or category_key,  # По умолчанию имя = исходный key
                }
                continue

            # Метаданные (key = value)
            if '=' in line:
                key, _, value = line.partition('=')
                key = key.strip().lower()
                value = value.strip()

                # Глобальные метаданные файла (до первой категории)
                if current_category is None:
                    if key == 'version':
                        file_version = value
                    elif key == 'description':
                        file_description = value
                    continue

                # Метаданные категории
                if key == 'full_name':
                    current_category['full_name'] = value
                elif key == 'description':
                    current_category['description'] = value
                elif key == 'tooltip':
                    # tooltip может содержать \n - оставляем как есть
                    current_category['tooltip'] = value
                elif key == 'color':
                    current_category['color'] = value
                elif key == 'default_strategy':
                    current_category['default_strategy'] = value
                elif key == 'ports':
                    current_category['ports'] = value
                elif key == 'protocol':
                    current_category['protocol'] = value
                elif key == 'order':
                    try:
                        current_category['order'] = int(value)
                    except ValueError:
                        current_category['order'] = 0
                elif key == 'command_order':
                    try:
                        current_category['command_order'] = int(value)
                    except ValueError:
                        current_category['command_order'] = 0
                elif key == 'needs_new_separator':
                    current_category['needs_new_separator'] = value.lower() == 'true'
                elif key == 'command_group':
                    current_category['command_group'] = value
                elif key == 'icon_name':
                    current_category['icon_name'] = value
                elif key == 'icon_color':
                    current_category['icon_color'] = value
                elif key == 'base_filter':
                    current_category['base_filter'] = value
                elif key == 'base_filter_ipset':
                    current_category['base_filter_ipset'] = value
                elif key == 'base_filter_hostlist':
                    current_category['base_filter_hostlist'] = value
                elif key == 'strategy_type':
                    current_category['strategy_type'] = value
                elif key == 'strip_payload':
                    current_category['strip_payload'] = value.lower() == 'true'
                elif key == 'requires_all_ports':
                    current_category['requires_all_ports'] = value.lower() == 'true'

        # Сохраняем последнюю категорию
        if current_category is not None:
            categories.append(current_category)

        log(f"Загружено {len(categories)} категорий из TXT: {source_name}", "DEBUG")
        return {
            'version': file_version,
            'description': file_description,
            'categories': categories
        }
    except Exception as e:
        log(f"Ошибка парсинга TXT категорий ({source_name}): {e}", "ERROR")
        return None


def load_categories_txt(filepath: Path) -> Optional[Dict]:
    """
    Загружает категории из TXT файла в INI-подобном формате.

    Формат:
        # Categories configuration
        version = 1.0
        description = Описание

        [category_key]
        full_name = Название категории
        description = Описание
        tooltip = Подсказка с \n для переносов строк
        color = #ff6666
        default_strategy = strategy_id
        ports = 80, 443
        protocol = TCP
        order = 1
        command_order = 3
        needs_new_separator = true
        command_group = youtube
        icon_name = fa5b.youtube
        icon_color = #FF0000
        base_filter = --filter-tcp=80,443 --ipset=ipset-youtube.txt
        strategy_type = tcp
        strip_payload = true
        requires_all_ports = true

        [another_category]
        ...

    Returns:
        Dict в формате {'version': '...', 'description': '...', 'categories': [...]} или None при ошибке
    """
    try:
        if not filepath.exists():
            return None

        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        return _parse_categories_txt_content(content, source_name=filepath.name)

    except Exception as e:
        log(f"Ошибка чтения TXT категорий {filepath}: {e}", "ERROR")
        return None


def load_categories_txt_text(text: str, *, source_name: str = "<embedded>") -> Optional[Dict]:
    """Парсит категории из TXT-строки в том же формате, что и `load_categories_txt()`."""
    return _parse_categories_txt_content(text, source_name=source_name)


def load_categories() -> Dict[str, Dict]:
    """
    Загружает категории (вкладки сервисов) из TXT или JSON файлов.

    Порядок загрузки:
    1. builtin/categories.txt (или .json как fallback) - встроенные категории
    2. один общий user_categories.txt вне папки установки - пользовательские категории (добавляются к builtin)

    Returns:
        Словарь {category_key: category_data}
    """
    ensure_directories()
    categories = {}

    builtin_dir = _get_builtin_dir()

    # Загружаем builtin категории (сначала TXT, потом JSON как fallback)
    builtin_txt = builtin_dir / "categories.txt"
    builtin_json = builtin_dir / "categories.json"

    builtin_data = None
    builtin_needs_repair = False
    if builtin_txt.exists():
        builtin_data = load_categories_txt(builtin_txt)
        if not builtin_data:
            builtin_needs_repair = True
    elif builtin_json.exists():
        builtin_data = load_json_file(builtin_json)
        if not builtin_data:
            builtin_needs_repair = True
    else:
        builtin_needs_repair = True

    if not (builtin_data and 'categories' in builtin_data):
        # Fallback: встроенная копия категорий (в коде), чтобы пережить удаление/поломку файла.
        try:
            from builtin_categories_txt import DEFAULT_CATEGORIES_TXT

            builtin_data = load_categories_txt_text(DEFAULT_CATEGORIES_TXT, source_name="builtin_categories_txt.py")
            if builtin_data and 'categories' in builtin_data:
                log("Файл categories.txt отсутствует/повреждён: использую встроенный fallback категорий", "WARNING")

                if builtin_needs_repair:
                    try:
                        builtin_txt.parent.mkdir(parents=True, exist_ok=True)
                        builtin_txt.write_text(DEFAULT_CATEGORIES_TXT, encoding="utf-8")
                        log(f"Восстановлен файл категорий: {builtin_txt}", "INFO")
                    except Exception as e:
                        log(f"Не удалось восстановить файл категорий {builtin_txt}: {e}", "WARNING")
        except Exception as e:
            log(f"Не удалось загрузить встроенный fallback категорий: {e}", "ERROR")

    if builtin_data and 'categories' in builtin_data:
        for cat in builtin_data['categories']:
            key = cat.get('key')
            if key:
                cat['_source'] = 'builtin'
                categories[key] = cat
        log(f"Загружено {len(categories)} встроенных категорий", "DEBUG")
    else:
        log(f"Не найден файл категорий в {builtin_dir}", "WARNING")

    # Загружаем user категории (добавляются к builtin, НЕ перезаписывают builtin).
    # Храним вне папки установки (pyinstaller/обновления могут затереть файлы).
    user_txt = get_user_categories_file_path()
    user_data = None
    if user_txt.exists():
        user_data = load_categories_txt(user_txt)

    if user_data and 'categories' in user_data:
        user_count = 0
        for cat in user_data['categories']:
            key = cat.get('key')
            if key:
                cat['_source'] = 'user'
                # If user forgot/typoed command_group, default to "user" so it shows
                # under the "Пользовательские" group in the GUI.
                if 'command_group' not in cat or not str(cat.get('command_group') or '').strip():
                    cat['command_group'] = 'user'
                if key in categories:
                    # User is not allowed to override built-in categories.
                    log(f"Пользовательская категория '{key}' конфликтует с системной и будет проигнорирована", "WARNING")
                else:
                    categories[key] = cat
                user_count += 1
        if user_count > 0:
            log(f"Загружено {user_count} пользовательских категорий", "DEBUG")

    return categories
