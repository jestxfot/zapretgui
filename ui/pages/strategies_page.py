# ui/pages/strategies_page.py
"""
Страница выбора стратегий с единым списком категорий.
При клике на категорию открывается отдельная страница StrategyDetailPage.
"""

from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QSize
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QPushButton, QSizePolicy, QMessageBox
)
from PyQt6.QtGui import QFont
import qtawesome as qta

from .base_page import BasePage
from ui.sidebar import SettingsCard, ActionButton
from ui.widgets import UnifiedStrategiesList
from log import log


class ResetActionButton(QPushButton):
    """Кнопка сброса с двойным подтверждением"""

    reset_confirmed = pyqtSignal()

    def __init__(self, text: str = "Сбросить", confirm_text: str = "Подтвердить?", parent=None):
        super().__init__(text, parent)
        self._default_text = text
        self._confirm_text = confirm_text
        self._pending = False

        self.setFixedHeight(32)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._update_style()

        # Таймер сброса состояния
        self._reset_timer = QTimer(self)
        self._reset_timer.setSingleShot(True)
        self._reset_timer.timeout.connect(self._reset_state)

    def _update_style(self):
        """Обновляет стили кнопки"""
        if self._pending:
            bg = "rgba(74, 222, 128, 0.25)"
            text_color = "#4ade80"
            border = "1px solid rgba(74, 222, 128, 0.5)"
        else:
            bg = "rgba(255, 255, 255, 0.08)"
            text_color = "#ffffff"
            border = "none"

        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg};
                border: {border};
                border-radius: 4px;
                color: {text_color};
                padding: 0 16px;
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: rgba(255, 255, 255, 0.15);
            }}
        """)

    def _reset_state(self):
        """Сбрасывает состояние кнопки"""
        self._pending = False
        self.setText(self._default_text)
        self._update_style()

    def mousePressEvent(self, event):
        """Обработка клика"""
        if event.button() == Qt.MouseButton.LeftButton:
            if self._pending:
                # Второй клик - подтверждение
                self._reset_timer.stop()
                self._pending = False
                self.setText("Done")
                self._update_style()
                self.reset_confirmed.emit()
                QTimer.singleShot(1500, self._reset_state)
            else:
                # Первый клик - переход в режим подтверждения
                self._pending = True
                self.setText(self._confirm_text)
                self._update_style()
                self._reset_timer.start(3000)
        super().mousePressEvent(event)


class StrategiesPage(BasePage):
    """
    Страница выбора стратегий с единым списком категорий.

    При клике на категорию эмитит сигнал open_category_detail для навигации
    к отдельной странице StrategyDetailPage.
    """

    strategy_selected = pyqtSignal(str, str)  # category_key, strategy_id
    strategies_changed = pyqtSignal(dict)  # все выборы
    launch_method_changed = pyqtSignal(str)  # для совместимости
    open_category_detail = pyqtSignal(str, str)  # category_key, current_strategy_id

    def __init__(self, parent=None):
        super().__init__(
            title="Стратегии DPI",
            subtitle="Выберите стратегии обхода блокировок для разных типов трафика",
            parent=parent
        )
        self.parent_app = parent
        self.category_selections = {}
        self._unified_list = None
        self._built = False

        # Совместимость со старым кодом
        self.content_layout = self.layout
        self.content_container = self.content

        # Заглушки для совместимости с main_window.py
        self.select_strategy_btn = QPushButton()
        self.select_strategy_btn.hide()

        self.current_strategy_label = QLabel("Не выбрана")
        self.current_strategy_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 14px;
                font-weight: 500;
            }
        """)

    def showEvent(self, event):
        """При показе страницы загружаем контент"""
        super().showEvent(event)
        if not self._built:
            QTimer.singleShot(0, self._build_content)

    def _build_content(self):
        """Строит содержимое страницы"""
        try:
            from strategy_menu.strategies_registry import registry
            from strategy_menu import get_direct_strategy_selections

            # Карточка с кнопкой Telegram (выделенная, акцентная)
            telegram_card = SettingsCard()
            telegram_layout = QHBoxLayout()
            telegram_layout.setContentsMargins(0, 0, 0, 0)
            telegram_layout.setSpacing(16)

            # Описательный текст слева
            telegram_hint = QLabel("Хотите добавить свою категорию? Напишите нам!")
            telegram_hint.setStyleSheet("""
                QLabel {
                    background: transparent;
                    color: rgba(255, 255, 255, 0.6);
                    font-size: 13px;
                    font-family: 'Segoe UI Variable', 'Segoe UI', sans-serif;
                }
            """)
            telegram_layout.addWidget(telegram_hint)

            # Кнопка Telegram - тёмная
            telegram_btn = QPushButton("  ОТКРЫТЬ TELEGRAM БОТА")
            telegram_btn.setIcon(qta.icon("fa5b.telegram-plane", color="#ffffff"))
            telegram_btn.setIconSize(QSize(18, 18))
            telegram_btn.setFixedHeight(36)
            telegram_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            telegram_btn.clicked.connect(self._open_custom_domains)
            telegram_btn.setStyleSheet("""
                QPushButton {
                    background-color: #2d2d2d;
                    border: 1px solid #3d3d3d;
                    border-radius: 6px;
                    color: #ffffff;
                    padding: 0 16px;
                    font-size: 12px;
                    font-weight: 600;
                    font-family: 'Segoe UI Variable', 'Segoe UI', sans-serif;
                }
                QPushButton:hover {
                    background-color: #3a3a3a;
                    border-color: #4a4a4a;
                }
                QPushButton:pressed {
                    background-color: #252525;
                }
            """)
            telegram_layout.addWidget(telegram_btn)
            telegram_layout.addStretch()

            telegram_card.add_layout(telegram_layout)
            self.content_layout.addWidget(telegram_card)

            # Панель действий (toolbar)
            actions_card = SettingsCard()
            actions_layout = QHBoxLayout()
            actions_layout.setSpacing(8)

            reload_btn = ActionButton("Обновить", "fa5s.sync-alt")
            reload_btn.clicked.connect(self._reload_strategies)
            actions_layout.addWidget(reload_btn)

            expand_btn = ActionButton("Развернуть", "fa5s.expand-alt")
            expand_btn.clicked.connect(self._expand_all)
            actions_layout.addWidget(expand_btn)

            collapse_btn = ActionButton("Свернуть", "fa5s.compress-alt")
            collapse_btn.clicked.connect(self._collapse_all)
            actions_layout.addWidget(collapse_btn)

            # Кнопка сброса
            self._reset_btn = ResetActionButton("Сбросить", confirm_text="По умолчанию?")
            self._reset_btn.reset_confirmed.connect(self._reset_to_defaults)
            actions_layout.addWidget(self._reset_btn)

            # Кнопка выключить все
            self._clear_btn = ResetActionButton("Выключить", confirm_text="Все отключить?")
            self._clear_btn.reset_confirmed.connect(self._clear_all)
            actions_layout.addWidget(self._clear_btn)

            actions_layout.addStretch()

            actions_card.add_layout(actions_layout)
            self.content_layout.addWidget(actions_card)

            # Загружаем выборы из реестра
            self.category_selections = get_direct_strategy_selections()

            # Список категорий (без правой панели - теперь отдельная страница)
            self._unified_list = UnifiedStrategiesList(self)
            self._unified_list.strategy_selected.connect(self._on_category_clicked)
            self._unified_list.selections_changed.connect(self._on_selections_changed)

            # Строим список
            categories = registry.categories
            self._unified_list.build_list(categories, self.category_selections)

            self.content_layout.addWidget(self._unified_list, 1)

            self._built = True
            log("StrategiesPage построена", "INFO")

        except Exception as e:
            log(f"Ошибка построения StrategiesPage: {e}", "ERROR")
            import traceback
            log(traceback.format_exc(), "DEBUG")

    def _on_category_clicked(self, category_key: str, strategy_id: str):
        """Обработчик клика по категории - открывает страницу выбора стратегий"""
        try:
            current_strategy = self.category_selections.get(category_key, 'none')
            self.open_category_detail.emit(category_key, current_strategy)
        except Exception as e:
            log(f"Ошибка открытия детальной страницы: {e}", "ERROR")

    def apply_strategy_selection(self, category_key: str, strategy_id: str):
        """Применяет выбор стратегии (вызывается из StrategyDetailPage)"""
        try:
            from strategy_menu import (
                save_direct_strategy_selection,
                regenerate_preset_file,
                invalidate_direct_selections_cache
            )

            # Сохраняем выбор в реестр
            save_direct_strategy_selection(category_key, strategy_id)
            invalidate_direct_selections_cache()

            self.category_selections[category_key] = strategy_id

            # Обновляем UI
            if self._unified_list:
                self._unified_list.update_selection(category_key, strategy_id)

            # Перегенерируем preset
            regenerate_preset_file()

            # Эмитим сигналы
            self.strategy_selected.emit(category_key, strategy_id)
            self.strategies_changed.emit(self.category_selections)

            log(f"Выбрана стратегия: {category_key} = {strategy_id}", "INFO")

            # Перезапускаем DPI если запущен
            self._apply_changes()

        except Exception as e:
            log(f"Ошибка сохранения выбора: {e}", "ERROR")

    def _on_selections_changed(self, selections: dict):
        """Обработчик изменения выборов"""
        self.category_selections = selections
        self.strategies_changed.emit(selections)

    def _apply_changes(self):
        """Применяет изменения - перезапускает DPI если запущен"""
        try:
            from strategy_menu import combine_strategies

            # Проверяем есть ли активные стратегии
            has_active = any(
                sid and sid != 'none'
                for sid in self.category_selections.values()
            )

            app = self.parent_app
            if not hasattr(app, 'dpi_controller') or not app.dpi_controller:
                log("dpi_controller не найден", "DEBUG")
                return

            # Проверяем запущен ли DPI
            is_running = False
            if hasattr(app, 'dpi_starter') and app.dpi_starter:
                is_running = app.dpi_starter.check_process_running_wmi(silent=True)

            if not is_running:
                log("DPI не запущен, пропускаем перезапуск", "DEBUG")
                return

            if not has_active:
                # Нет активных стратегий - останавливаем
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
            from strategy_menu import get_direct_strategy_selections, invalidate_direct_selections_cache

            # Перезагружаем реестр
            registry.reload_strategies()
            invalidate_direct_selections_cache()

            # Перестраиваем UI
            self._built = False

            # Удаляем старые виджеты (кроме заголовков)
            while self.content_layout.count() > 2:  # title + subtitle
                item = self.content_layout.takeAt(2)
                if item.widget():
                    item.widget().deleteLater()

            self._unified_list = None
            self._build_content()

            log("Стратегии перезагружены", "INFO")

        except Exception as e:
            log(f"Ошибка перезагрузки: {e}", "ERROR")

    def _reset_to_defaults(self):
        """Сбрасывает все стратегии к значениям по умолчанию"""
        try:
            from strategy_menu.strategies_registry import registry
            from strategy_menu import (
                save_direct_strategy_selections,
                regenerate_preset_file,
                invalidate_direct_selections_cache
            )

            # Получаем значения по умолчанию
            defaults = registry.get_default_selections()

            # Сохраняем в реестр
            save_direct_strategy_selections(defaults)
            invalidate_direct_selections_cache()

            self.category_selections = defaults.copy()

            # Обновляем UI
            if self._unified_list:
                self._unified_list.set_selections(defaults)

            # Перегенерируем preset
            regenerate_preset_file()

            # Применяем изменения
            self._apply_changes()

            log("Стратегии сброшены к значениям по умолчанию", "INFO")

        except Exception as e:
            log(f"Ошибка сброса стратегий: {e}", "ERROR")

    def _clear_all(self):
        """Отключает все стратегии"""
        try:
            from strategy_menu.strategies_registry import registry
            from strategy_menu import (
                save_direct_strategy_selections,
                regenerate_preset_file,
                invalidate_direct_selections_cache
            )

            # Устанавливаем все в 'none'
            cleared = {key: 'none' for key in registry.get_all_category_keys()}

            # Сохраняем в реестр
            save_direct_strategy_selections(cleared)
            invalidate_direct_selections_cache()

            self.category_selections = cleared

            # Обновляем UI
            if self._unified_list:
                self._unified_list.set_selections(cleared)

            # Перегенерируем preset
            regenerate_preset_file()

            # Применяем изменения (остановит DPI)
            self._apply_changes()

            log("Все стратегии отключены", "INFO")

        except Exception as e:
            log(f"Ошибка отключения стратегий: {e}", "ERROR")

    def _expand_all(self):
        """Разворачивает все группы"""
        if self._unified_list:
            self._unified_list.expand_all()

    def _collapse_all(self):
        """Сворачивает все группы"""
        if self._unified_list:
            self._unified_list.collapse_all()

    # ==================== Совместимость со старым кодом ====================

    def update_current_strategy(self, name: str):
        """Совместимость: обновляет отображение текущей стратегии"""
        if name and name != "Автостарт DPI отключен":
            self.current_strategy_label.setText(name)
        else:
            self.current_strategy_label.setText("Не выбрана")

    def show_loading(self):
        """Совместимость: показывает спиннер"""
        pass

    def show_success(self):
        """Совместимость: показывает галочку"""
        pass

    def _update_current_strategies_display(self):
        """Совместимость: обновляет отображение текущих стратегий"""
        try:
            from strategy_menu import get_direct_strategy_selections
            from strategy_menu.strategies_registry import registry

            selections = get_direct_strategy_selections()
            active_count = sum(1 for s in selections.values() if s and s != 'none')

            if active_count > 0:
                self.current_strategy_label.setText(f"{active_count} активных")
            else:
                self.current_strategy_label.setText("Не выбрана")
        except Exception as e:
            log(f"Ошибка обновления отображения: {e}", "DEBUG")

    def _start_process_monitoring(self):
        """Совместимость: заглушка для мониторинга процесса"""
        pass

    def disable_categories_for_filter(self, filter_key: str):
        """Совместимость: отключает категории для фильтра"""
        log(f"disable_categories_for_filter: {filter_key}", "DEBUG")
        # В новой версии фильтры работают иначе

    def on_external_filters_changed(self, filters: dict):
        """Совместимость: обработчик внешних фильтров"""
        log(f"on_external_filters_changed: {filters}", "DEBUG")

    def on_external_sort_changed(self, sort_key: str):
        """Совместимость: обработчик внешней сортировки"""
        log(f"on_external_sort_changed: {sort_key}", "DEBUG")

    def reload_for_mode_change(self):
        """Совместимость: перезагружает страницу при смене режима"""
        self._reload_strategies()

    def _open_custom_domains(self):
        """Открывает Telegram канал с инструкциями по добавлению сайтов"""
        from config.telegram_links import open_telegram_link
        open_telegram_link("zaprethelp", post=18408)
