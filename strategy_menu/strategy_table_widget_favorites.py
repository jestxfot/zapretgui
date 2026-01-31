# strategy_menu/strategy_table_widget_favorites.py

from .strategy_table_widget import StrategyTableWidget


class FavoriteStrategyTableWidget(StrategyTableWidget):
    """Виджет таблицы стратегий (для обратной совместимости)"""
    
    def __init__(self, strategy_manager=None, parent=None):
        super().__init__(strategy_manager, parent)


class StrategyTableWithFavoritesFilter(StrategyTableWidget):
    """Расширение с поддержкой фильтра (для обратной совместимости)"""

    def __init__(self, strategy_manager=None, parent=None):
        super().__init__(strategy_manager, parent)
        self._all_strategies = {}

    def populate_strategies(self, strategies, category_key="bat", skip_grouping=False):
        """Сохраняет все стратегии и заполняет таблицу

        Args:
            strategies: Словарь стратегий
            category_key: Ключ категории
            skip_grouping: Если True, не группировать по провайдерам (для сортировки по имени)
        """
        self._all_strategies = strategies.copy()
        super().populate_strategies(strategies, category_key, skip_grouping=skip_grouping)
