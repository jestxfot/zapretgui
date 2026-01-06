# strategy_menu/strategy_lists_separated.py

"""
Вспомогательные функции для работы со стратегиями.

Основная логика объединения стратегий перенесена в command_builder.py.
Этот модуль содержит только утилиты для отображения и валидации.
"""

from .strategies_registry import registry


# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================

def get_strategy_display_name(category_key: str, strategy_id: str) -> str:
    """Получает отображаемое имя стратегии"""
    if strategy_id == "none":
        return "⛔ Отключено"

    return registry.get_strategy_name_safe(category_key, strategy_id)


def get_active_categories_count(category_strategies: dict) -> int:
    """Подсчитывает количество активных категорий"""
    none_strategies = registry.get_none_strategies()
    count = 0

    for category_key, strategy_id in category_strategies.items():
        if strategy_id and strategy_id != none_strategies.get(category_key):
            count += 1

    return count


def validate_category_strategies(category_strategies: dict) -> list:
    """
    Проверяет корректность выбранных стратегий.
    Возвращает список ошибок (пустой если всё ок).
    """
    errors = []

    for category_key, strategy_id in category_strategies.items():
        if not strategy_id:
            continue

        if strategy_id == "none":
            continue

        # Проверяем существование категории
        category_info = registry.get_category_info(category_key)
        if not category_info:
            errors.append(f"Неизвестная категория: {category_key}")
            continue

        # Проверяем существование стратегии
        args = registry.get_strategy_args_safe(category_key, strategy_id)
        if args is None:
            errors.append(f"Стратегия '{strategy_id}' не найдена в категории '{category_key}'")

    return errors
