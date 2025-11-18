"""
Модуль для применения различных модификаций к аргументам стратегий
"""

import os
from log import log


def apply_remove_hostlists(args: list) -> list:
    """
    Удаляет все упоминания hostlist из аргументов (применить ко ВСЕМ САЙТАМ)
    
    Убирает:
    - --hostlist=...
    - --hostlist-domains=...
    - --hostlist-exclude=...
    
    Оставляет только --filter и --dpi-desync (и другие аргументы)
    
    Args:
        args: Список аргументов командной строки
        
    Returns:
        Модифицированный список аргументов без hostlist
    """
    from strategy_menu import get_remove_hostlists_enabled
    
    if not get_remove_hostlists_enabled():
        return args
    
    # Префиксы для удаления
    remove_prefixes = [
        "--hostlist=",
        "--hostlist-domains=",
        "--hostlist-exclude="
    ]
    
    new_args = []
    removed_count = 0
    
    for arg in args:
        # Проверяем, начинается ли аргумент с одного из префиксов для удаления
        should_remove = False
        for prefix in remove_prefixes:
            if arg.startswith(prefix):
                should_remove = True
                removed_count += 1
                log(f"Удален аргумент hostlist: {arg}", "DEBUG")
                break
        
        if not should_remove:
            new_args.append(arg)
    
    if removed_count > 0:
        log(f"✅ Применен фильтр 'ко всем сайтам': удалено {removed_count} аргументов hostlist", "SUCCESS")
    
    return new_args


def apply_remove_ipsets(args: list) -> list:
    """
    Удаляет все упоминания ipset из аргументов (применить ко ВСЕМ IP-АДРЕСАМ)
    
    Убирает:
    - --ipset=...
    - --ipset-ip=...
    - --ipset-exclude=...
    
    Оставляет только --filter и --dpi-desync (и другие аргументы)
    
    Args:
        args: Список аргументов командной строки
        
    Returns:
        Модифицированный список аргументов без ipset
    """
    from strategy_menu import get_remove_ipsets_enabled
    
    if not get_remove_ipsets_enabled():
        return args
    
    # Префиксы для удаления
    remove_prefixes = [
        "--ipset=",
        "--ipset-ip=",
        "--ipset-exclude="
    ]
    
    new_args = []
    removed_count = 0
    
    for arg in args:
        # Проверяем, начинается ли аргумент с одного из префиксов для удаления
        should_remove = False
        for prefix in remove_prefixes:
            if arg.startswith(prefix):
                should_remove = True
                removed_count += 1
                log(f"Удален аргумент ipset: {arg}", "DEBUG")
                break
        
        if not should_remove:
            new_args.append(arg)
    
    if removed_count > 0:
        log(f"✅ Применен фильтр 'ко всем IP-адресам': удалено {removed_count} аргументов ipset", "SUCCESS")
    
    return new_args


def apply_allzone_replacement(args: list) -> list:
    """
    Заменяет other.txt на allzone.txt в хостлистах если включено в настройках
    
    Args:
        args: Список аргументов командной строки
        
    Returns:
        Модифицированный список аргументов с замененными хостлистами
    """
    from strategy_menu import get_allzone_hostlist_enabled
    
    # Если замена выключена, возвращаем аргументы без изменений
    if not get_allzone_hostlist_enabled():
        return args
    
    new_args = []
    replacements_count = 0
    
    for arg in args:
        if arg.startswith("--hostlist="):
            hostlist_value = arg.split("=", 1)[1]
            
            # Проверяем, содержит ли путь other.txt
            if "other.txt" in hostlist_value:
                # Заменяем other.txt на allzone.txt
                new_value = hostlist_value.replace("other.txt", "allzone.txt")
                new_args.append(f"--hostlist={new_value}")
                replacements_count += 1
                log(f"Заменен хостлист: other.txt → allzone.txt", "DEBUG")
            else:
                new_args.append(arg)
        else:
            new_args.append(arg)
    
    if replacements_count > 0:
        log(f"✅ Выполнена замена other.txt на allzone.txt ({replacements_count} замен)", "SUCCESS")
    
    return new_args


def _has_port_443(ports_part: str) -> bool:
    """
    Проверяет, содержит ли строка с портами порт 443
    
    Args:
        ports_part: Строка с портами (например: "80,443" или "444-65535")
        
    Returns:
        True если порт 443 присутствует
    """
    for port_spec in ports_part.split(","):
        port_spec = port_spec.strip()
        
        if "-" in port_spec:
            # Диапазон портов (например: 80-8080, 444-65535)
            try:
                parts = port_spec.split("-", 1)
                start = int(parts[0].strip())
                end = int(parts[1].strip())
                if start <= 443 <= end:
                    return True
            except (ValueError, IndexError):
                continue
        else:
            # Отдельный порт
            try:
                if int(port_spec) == 443:
                    return True
            except ValueError:
                continue
    
    return False


def apply_wssize_parameter(args: list) -> list:
    """
    Применяет параметры --wssize 1:6 и --wssize-forced-cutoff=0 к аргументам стратегии если включено в настройках
    
    Args:
        args: Список аргументов командной строки
        
    Returns:
        Модифицированный список аргументов с добавленными wssize параметрами
    """
    from strategy_menu import get_wssize_enabled
    
    if not get_wssize_enabled():
        return args
    
    new_args = []
    i = 0
    
    while i < len(args):
        arg = args[i]
        new_args.append(arg)
        
        # Ищем --filter-tcp с портом 443
        if arg.startswith("--filter-tcp="):
            ports_part = arg.split("=", 1)[1]
            has_port_443 = _has_port_443(ports_part)
            
            if has_port_443:
                # Копируем все аргументы этого фильтра до следующего --new или конца
                j = i + 1
                filter_args = []
                
                while j < len(args) and args[j] != "--new":
                    filter_args.append(args[j])
                    j += 1
                
                # Добавляем аргументы фильтра
                new_args.extend(filter_args)
                
                # Проверяем, нет ли уже параметров wssize в этом блоке
                has_wssize = any("--wssize" in arg for arg in filter_args)
                has_cutoff = any("--wssize-forced-cutoff" in arg for arg in filter_args)
                
                if not has_wssize:
                    # Разделяем на два отдельных аргумента
                    new_args.append("--wssize")
                    new_args.append("1:6")
                    log(f"Добавлен параметр --wssize 1:6 после {arg}", "DEBUG")
                
                if not has_cutoff:
                    new_args.append("--wssize-forced-cutoff=0")
                    log(f"Добавлен параметр --wssize-forced-cutoff=0 после {arg}", "DEBUG")
                
                # Переходим к следующему аргументу (пропускаем уже обработанные)
                i = j - 1  # -1 потому что в конце цикла будет i += 1
        
        i += 1
    
    return new_args


def apply_all_filters(args: list, lists_dir: str) -> list:
    """
    Применяет все фильтры в правильном порядке
    
    ПОРЯДОК ВАЖЕН:
    1. Сначала удаляем hostlist (если включено "ко всем сайтам")
    2. Затем удаляем ipset (если включено "ко всем IP-адресам")
    3. Затем заменяем other.txt на allzone.txt (если включено)
    4. Затем применяем Game Filter (расширение портов)
    5. В конце применяем wssize параметры
    
    Args:
        args: Исходный список аргументов
        lists_dir: Путь к директории со списками
        
    Returns:
        Полностью обработанный список аргументов
    """
    # 1. Удаляем все hostlist (если включено)
    args = apply_remove_hostlists(args)
    
    # 2. Удаляем все ipset (если включено)
    args = apply_remove_ipsets(args)
    
    # 3. Заменяем other.txt на allzone.txt (если включено)
    args = apply_allzone_replacement(args)
    
    # 5. Применяем wssize параметры (если включено)
    args = apply_wssize_parameter(args)
    
    return args