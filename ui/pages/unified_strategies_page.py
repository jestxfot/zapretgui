# ui/pages/unified_strategies_page.py
"""
Альтернативная страница выбора стратегий с единым списком и фильтрацией.
Заменяет вкладочный интерфейс CategoriesTabPanel на unified список с группировкой.
"""

from PyQt6.QtWidgets import QHBoxLayout
from PyQt6.QtCore import pyqtSignal

from .base_page import BasePage
from ui.sidebar import SettingsCard, ActionButton
from ui.widgets import UnifiedStrategiesList
from log import log


class UnifiedStrategiesPage(BasePage):
    """
    Страница с единым списком стратегий и фильтрацией.

    Заменяет вкладочный интерфейс CategoriesTabPanel на:
    - FilterButtonGroup сверху (TCP, UDP, Discord, Voice, Games)
    - Сворачиваемые группы по сервисам
    - Быстрая фильтрация без перестроения списка
    """

    strategy_selected = pyqtSignal(str, str)  # category_key, strategy_id
    strategies_changed = pyqtSignal(dict)  # все выборы

    def __init__(self, parent=None, parent_app=None):
        super().__init__(
            title="Стратегии",
            subtitle="Выберите стратегии обхода DPI для каждого сервиса",
            parent=parent
        )
        self.parent_app = parent_app
        self.category_selections = {}
        self._unified_list = None
        self._built = False

        # Создаем content_layout для совместимости с BasePage
        self.content_layout = self.layout
        self.content_container = self.content

    def showEvent(self, event):
        """При показе страницы загружаем контент"""
        super().showEvent(event)
        if not self._built:
            self._build_content()

    def _build_content(self):
        """Строит содержимое страницы"""
        try:
            from strategy_menu.strategies_registry import registry
            from strategy_menu import get_direct_strategy_selections

            # Панель действий
            actions_card = SettingsCard()
            actions_layout = QHBoxLayout()
            actions_layout.setSpacing(8)

            reload_btn = ActionButton("Обновить", "fa5s.sync-alt")
            reload_btn.clicked.connect(self._reload_strategies)
            actions_layout.addWidget(reload_btn)

            expand_btn = ActionButton("Развернуть все", "fa5s.expand-alt")
            expand_btn.clicked.connect(self._expand_all)
            actions_layout.addWidget(expand_btn)

            collapse_btn = ActionButton("Свернуть все", "fa5s.compress-alt")
            collapse_btn.clicked.connect(self._collapse_all)
            actions_layout.addWidget(collapse_btn)

            actions_layout.addStretch()
            actions_card.add_layout(actions_layout)
            self.content_layout.addWidget(actions_card)

            # Загружаем выборы из реестра
            self.category_selections = get_direct_strategy_selections()

            # Создаем unified список
            self._unified_list = UnifiedStrategiesList(self)
            self._unified_list.strategy_selected.connect(self._on_strategy_selected)
            self._unified_list.selections_changed.connect(self._on_selections_changed)

            # Строим список
            categories = registry.categories
            self._unified_list.build_list(categories, self.category_selections)

            self.content_layout.addWidget(self._unified_list, 1)

            self._built = True
            log("UnifiedStrategiesPage построена", "INFO")

        except Exception as e:
            log(f"Ошибка построения UnifiedStrategiesPage: {e}", "ERROR")
            import traceback
            log(traceback.format_exc(), "DEBUG")

    def _on_strategy_selected(self, category_key: str, strategy_id: str):
        """Обработчик выбора стратегии из ComboBox в списке"""
        try:
            from strategy_menu import save_direct_strategy_selection, regenerate_preset_file

            # Сохраняем выбор
            save_direct_strategy_selection(category_key, strategy_id)
            self.category_selections[category_key] = strategy_id

            # Обновляем UI
            if self._unified_list:
                self._unified_list.update_selection(category_key, strategy_id)

            # Перегенерируем preset
            regenerate_preset_file()

            # Эмитим сигнал
            self.strategy_selected.emit(category_key, strategy_id)
            self.strategies_changed.emit(self.category_selections)

            log(f"Выбрана стратегия: {category_key} = {strategy_id}", "INFO")

            # Перезапускаем DPI
            self._apply_changes()

        except Exception as e:
            log(f"Ошибка сохранения выбора: {e}", "ERROR")

    def _on_selections_changed(self, selections: dict):
        """Обработчик изменения выборов"""
        self.category_selections = selections
        self.strategies_changed.emit(selections)

    def _apply_changes(self):
        """Применяет изменения - перезапускает DPI"""
        try:
            from strategy_menu import combine_strategies

            # Проверяем есть ли активные стратегии
            has_active = any(
                sid and sid != 'none'
                for sid in self.category_selections.values()
            )

            app = self.parent_app
            if not hasattr(app, 'dpi_controller') or not app.dpi_controller:
                return

            if not has_active:
                app.dpi_controller.stop_dpi_async()
                return

            # Комбинируем стратегии
            combined = combine_strategies(**self.category_selections)
            combined_data = {
                'id': 'DIRECT_MODE',
                'name': 'Прямой запуск (Запрет 2)',
                'is_combined': True,
                'args': combined['args'],
                'selections': self.category_selections.copy()
            }

            app.dpi_controller.start_dpi_async(selected_mode=combined_data)

        except Exception as e:
            log(f"Ошибка применения изменений: {e}", "ERROR")

    def _reload_strategies(self):
        """Перезагружает стратегии"""
        try:
            from strategy_menu.strategies_registry import registry

            registry.reload_strategies()
            self._built = False
            self._build_content()

        except Exception as e:
            log(f"Ошибка перезагрузки: {e}", "ERROR")

    def _expand_all(self):
        """Разворачивает все группы"""
        if self._unified_list:
            self._unified_list.expand_all()

    def _collapse_all(self):
        """Сворачивает все группы"""
        if self._unified_list:
            self._unified_list.collapse_all()
