"""
strategy_menu/strategy_matching.py

Модуль для сопоставления аргументов стратегии с strategy_id.
Используется для восстановления strategy_id из preset файлов.
"""

from log.log import log


def match_strategy_by_args(
    category_key: str,
    tcp_args: str,
    udp_args: str,
    protocol: str
) -> str:
    """
    Определяет strategy_id по аргументам стратегии.

    Args:
        category_key: Название категории (youtube, discord, etc.)
        tcp_args: TCP аргументы (--lua-desync=...)
        udp_args: UDP аргументы
        protocol: "tcp" или "udp"

    Returns:
        strategy_id или "none" если не найдено совпадение
    """
    from strategy_menu.strategies_registry import StrategiesRegistry

    registry = StrategiesRegistry()

    # Получить все стратегии для категории
    strategies = registry.get_category_strategies(category_key)

    if not strategies:
        return "none"

    # Выбрать нужные args
    target_args = tcp_args.strip() if protocol == "tcp" else udp_args.strip()

    if not target_args:
        return "none"

    # Поиск совпадения
    for strategy_id in strategies.keys():
        try:
            strategy_args = registry.get_strategy_args_safe(category_key, strategy_id)

            if strategy_args is None:
                continue

            if _args_match(strategy_args, target_args):
                log(f"Matched strategy: {category_key} → {strategy_id}", "DEBUG")
                return strategy_id
        except Exception as e:
            log(f"Error checking strategy {strategy_id}: {e}", "WARNING")
            continue

    # Не найдено совпадение
    log(f"No strategy match for {category_key} with args: {target_args[:50]}...", "DEBUG")
    return "none"


def _args_match(strategy_args: str, target_args: str) -> bool:
    """
    Проверяет совпадение аргументов (нормализация и сравнение).

    Игнорирует:
    - Пробелы и переносы строк
    - Порядок аргументов (не реализовано, но можно добавить)
    - Префиксы --filter-tcp/udp, --hostlist/ipset (они не часть стратегии)
    """
    # Нормализация: удалить пробелы, привести к нижнему регистру
    norm_strategy = _normalize_args(strategy_args)
    norm_target = _normalize_args(target_args)

    # Простое сравнение
    return norm_strategy == norm_target


def _normalize_args(args: str) -> str:
    """
    Нормализует аргументы для сравнения.

    Удаляет:
    - Лишние пробелы
    - Переносы строк
    - Приводит к нижнему регистру
    """
    # Удалить переносы строк
    normalized = args.replace('\n', ' ')

    # Удалить повторяющиеся пробелы
    normalized = ' '.join(normalized.split())

    # Нижний регистр
    normalized = normalized.lower().strip()

    return normalized
