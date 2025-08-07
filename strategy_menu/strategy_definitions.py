# strategy_menu/strategy_definitions.py

"""
Определения встроенных стратегий для Zapret
Содержит массив всех доступных стратегий с их параметрами и аргументами командной строки
"""

from datetime import datetime
from .strategy_lists import BUILTIN_STRATEGIES
from .constants import LABEL_RECOMMENDED, LABEL_CAUTION, LABEL_EXPERIMENTAL, LABEL_STABLE, LABEL_WARP

# Функции для работы со стратегиями
def get_strategy_by_id(strategy_id: str) -> dict | None:
    """Получает стратегию по ID"""
    return BUILTIN_STRATEGIES.get(strategy_id)

def get_all_strategies() -> dict:
    """Возвращает все доступные стратегии"""
    return BUILTIN_STRATEGIES.copy()

def get_strategies_by_provider(provider: str) -> dict:
    """Возвращает стратегии для конкретного провайдера"""
    result = {}
    for strategy_id, strategy_info in BUILTIN_STRATEGIES.items():
        if strategy_info.get('provider') == provider or strategy_info.get('provider') == 'universal':
            result[strategy_id] = strategy_info
    return result

def get_strategies_by_label(label: str) -> dict:
    """Возвращает стратегии с определенной меткой"""
    result = {}
    for strategy_id, strategy_info in BUILTIN_STRATEGIES.items():
        if strategy_info.get('label') == label:
            result[strategy_id] = strategy_info
    return result

def get_recommended_strategies() -> dict:
    """Возвращает рекомендуемые стратегии"""
    return get_strategies_by_label(LABEL_RECOMMENDED)

def get_strategy_args(strategy_id: str) -> list | None:
    """Возвращает аргументы командной строки для стратегии"""
    strategy = get_strategy_by_id(strategy_id)
    if strategy:
        args_str = strategy.get('args', '')
        if args_str:
            # Заменяем переносы строк на пробелы
            args_str = ' '.join(args_str.split())
            import shlex
            return shlex.split(args_str)
    return None

def validate_strategy(strategy_data: dict) -> bool:
    """Проверяет корректность данных стратегии"""
    required_fields = ['name', 'description', 'version', 'provider', 'author', 'updated', 'args']
    
    for field in required_fields:
        if field not in strategy_data:
            return False
    
    # Проверяем, что args является строкой
    if not isinstance(strategy_data['args'], str):
        return False
    
    return True

def search_strategies(query: str) -> dict:
    """Поиск стратегий по названию или описанию"""
    query = query.lower()
    result = {}
    
    for strategy_id, strategy_info in BUILTIN_STRATEGIES.items():
        name = strategy_info.get('name', '').lower()
        description = strategy_info.get('description', '').lower()
        
        if query in name or query in description:
            result[strategy_id] = strategy_info
    
    return result

# Мета-информация о файле
__version__ = "1.0.0"
__author__ = "Zapret Team"
__description__ = "Определения встроенных стратегий для системы обхода блокировок Zapret"
__total_strategies__ = len(BUILTIN_STRATEGIES)

# Статистика по стратегиям
def get_strategies_stats() -> dict:
    """Возвращает статистику по стратегиям"""
    stats = {
        'total': len(BUILTIN_STRATEGIES),
        'by_provider': {},
        'by_label': {},
        'all_sites_count': 0,
        'specific_sites_count': 0
    }
    
    for strategy_info in BUILTIN_STRATEGIES.values():
        # По провайдерам
        provider = strategy_info.get('provider', 'unknown')
        stats['by_provider'][provider] = stats['by_provider'].get(provider, 0) + 1
        
        # По меткам
        label = strategy_info.get('label', 'unlabeled')
        stats['by_label'][label] = stats['by_label'].get(label, 0) + 1
        
        # По типу сайтов
        if strategy_info.get('all_sites', False):
            stats['all_sites_count'] += 1
        else:
            stats['specific_sites_count'] += 1
    
    return stats

def extract_host_lists_from_args(args: list) -> list:
    """Извлекает список хостлистов из аргументов командной строки"""
    host_lists = []
    
    # Если args это строка, конвертируем в список
    if isinstance(args, str):
        import shlex
        args = shlex.split(args)
    
    for arg in args:
        if arg.startswith("--hostlist="):
            host_file = arg.split("=", 1)[1]
            if host_file not in host_lists:
                host_lists.append(host_file)
        elif arg.startswith("--ipset="):
            ipset_file = arg.split("=", 1)[1]
            if ipset_file not in host_lists:
                host_lists.append(ipset_file)
    
    return host_lists

def extract_domains_from_args(args: list) -> list:
    """Извлекает домены из аргументов --hostlist-domains"""
    domains = []
    
    # Если args это строка, конвертируем в список
    if isinstance(args, str):
        import shlex
        args = shlex.split(args)
    
    for arg in args:
        if arg.startswith("--hostlist-domains="):
            domain_list = arg.split("=", 1)[1]
            domains.extend(domain_list.split(","))
    
    return domains

def extract_ports_from_args(args: list) -> list:
    """Извлекает порты из аргументов --filter-tcp и --filter-udp"""
    ports = set()
    
    # Если args это строка, конвертируем в список
    if isinstance(args, str):
        import shlex
        args = shlex.split(args)
    
    for arg in args:
        if arg.startswith("--filter-tcp=") or arg.startswith("--filter-udp="):
            port_spec = arg.split("=", 1)[1]
            # Парсим порты (80,443,1024-65535)
            for port_part in port_spec.split(","):
                if "-" in port_part:
                    # Диапазон портов
                    start, end = port_part.split("-")
                    ports.add(f"{start}-{end}")
                else:
                    # Отдельный порт
                    ports.add(port_part)
    
    return sorted(list(ports))

def get_strategy_metadata(strategy_id: str) -> dict:
    """Возвращает метаданные стратегии с автоматически извлеченной информацией"""
    strategy = get_strategy_by_id(strategy_id)
    if not strategy:
        return {}
    
    args = strategy.get('args', '')
    
    return {
        **strategy,
        'parsed_host_lists': extract_host_lists_from_args(args),
        'parsed_domains': extract_domains_from_args(args),
        'parsed_ports': extract_ports_from_args(args),
        'uses_quic': 'quic' in args.lower() if args else False,
        'uses_tls_fake': 'fake-tls' in args if args else False,
        'uses_autottl': 'autottl' in args if args else False
    }

if __name__ == "__main__":
    # Тестирование функций
    print(f"Всего стратегий: {__total_strategies__}")
    print("\nСтатистика:")
    stats = get_strategies_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    print("\nРекомендуемые стратегии:")
    recommended = get_recommended_strategies()
    for strategy_id, strategy_info in recommended.items():
        print(f"  {strategy_id}: {strategy_info['name']}")