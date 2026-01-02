# ui/pages/strategies_page.py
"""
Новая страница выбора стратегий с единым списком и фильтрацией.
Заменяет старый CategoriesTabPanel на UnifiedStrategiesList.
"""

from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QPushButton, QSizePolicy, QMessageBox, QDialog
)
from PyQt6.QtGui import QFont
import qtawesome as qta

from .base_page import BasePage
from ui.sidebar import SettingsCard, ActionButton
from ui.widgets import UnifiedStrategiesList
from log import log


class StrategySelectionDialog(QDialog):
    """
    Диалог выбора стратегии для конкретной категории.
    Открывается при клике на категорию в UnifiedStrategiesList.
    """

    strategy_selected = pyqtSignal(str, str)  # (category_key, strategy_id)

    def __init__(self, category_key: str, category_info, current_strategy: str, parent=None):
        super().__init__(parent)
        self._category_key = category_key
        self._category_info = category_info
        self._current_strategy = current_strategy
        self._build_ui()

    def _build_ui(self):
        """Создает UI диалога"""
        self.setWindowTitle(f"Выбор стратегии: {self._category_info.full_name}")
        self.setMinimumSize(550, 450)
        self.setStyleSheet("""
            QDialog {
                background: #1a1a1a;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Заголовок
        header = QLabel(self._category_info.full_name)
        header.setFont(QFont("Segoe UI Semibold", 14))
        header.setStyleSheet("color: white;")
        layout.addWidget(header)

        # Описание
        if hasattr(self._category_info, 'description') and self._category_info.description:
            desc = QLabel(self._category_info.description)
            desc.setStyleSheet("color: rgba(255,255,255,0.6);")
            desc.setWordWrap(True)
            layout.addWidget(desc)

        # Scroll area для списка стратегий
        from PyQt6.QtWidgets import QScrollArea
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("""
            QScrollArea { background: transparent; border: none; }
            QScrollBar:vertical {
                width: 6px;
                background: transparent;
            }
            QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 0.15);
                border-radius: 3px;
                min-height: 20px;
            }
        """)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(4)

        # Загружаем стратегии для этой категории
        self._load_strategies(content_layout)

        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll, 1)

        # Кнопки
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        # Кнопка "Отключить"
        disable_btn = QPushButton("Отключить")
        disable_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 100, 100, 0.2);
                border: 1px solid rgba(255, 100, 100, 0.3);
                border-radius: 6px;
                color: #ff6464;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background: rgba(255, 100, 100, 0.3);
            }
        """)
        disable_btn.clicked.connect(self._on_disable)
        buttons_layout.addWidget(disable_btn)

        # Кнопка "Отмена"
        cancel_btn = QPushButton("Отмена")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.06);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 6px;
                color: rgba(255, 255, 255, 0.8);
                padding: 8px 16px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.1);
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_btn)

        layout.addLayout(buttons_layout)

    def _load_strategies(self, layout: QVBoxLayout):
        """Загружает список стратегий для категории"""
        try:
            from strategy_menu.strategies_registry import registry

            strategies = registry.get_category_strategies(self._category_key)
            if not strategies:
                label = QLabel("Нет доступных стратегий")
                label.setStyleSheet("color: rgba(255,255,255,0.5);")
                layout.addWidget(label)
                return

            for strategy_id, strategy_data in strategies.items():
                item = self._create_strategy_item(strategy_id, strategy_data)
                layout.addWidget(item)

        except Exception as e:
            log(f"Ошибка загрузки стратегий: {e}", "ERROR")

    def _create_strategy_item(self, strategy_id: str, strategy_data: dict) -> QFrame:
        """Создает элемент стратегии"""
        frame = QFrame()
        frame.setCursor(Qt.CursorShape.PointingHandCursor)
        frame.setProperty("strategy_id", strategy_id)

        is_selected = strategy_id == self._current_strategy

        if is_selected:
            frame.setStyleSheet("""
                QFrame {
                    background: rgba(96, 205, 255, 0.15);
                    border: 1px solid rgba(96, 205, 255, 0.3);
                    border-radius: 6px;
                }
                QFrame:hover {
                    background: rgba(96, 205, 255, 0.2);
                }
            """)
        else:
            frame.setStyleSheet("""
                QFrame {
                    background: rgba(255, 255, 255, 0.03);
                    border: 1px solid rgba(255, 255, 255, 0.06);
                    border-radius: 6px;
                }
                QFrame:hover {
                    background: rgba(255, 255, 255, 0.06);
                }
            """)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)

        # Название
        name = strategy_data.get('name', strategy_id)
        name_label = QLabel(name)
        name_label.setFont(QFont("Segoe UI", 10))
        name_label.setStyleSheet("color: white; background: transparent;")
        layout.addWidget(name_label)

        # Описание
        desc = strategy_data.get('description', '')
        if desc:
            desc_label = QLabel(desc)
            desc_label.setStyleSheet("color: rgba(255,255,255,0.5); background: transparent;")
            desc_label.setWordWrap(True)
            layout.addWidget(desc_label)

        # Label (если есть)
        label = strategy_data.get('label', '')
        if label:
            label_colors = {
                "recommended": ("#4CAF50", "Рекомендуется"),
                "experimental": ("#ff9800", "Экспериментальная"),
                "game": ("#9c27b0", "Для игр"),
                "caution": ("#f44336", "Осторожно"),
            }
            if label in label_colors:
                color, text = label_colors[label]
                badge = QLabel(text)
                badge.setFont(QFont("Segoe UI", 8))
                badge.setStyleSheet(f"""
                    QLabel {{
                        background: {color}30;
                        color: {color};
                        border: 1px solid {color}50;
                        border-radius: 8px;
                        padding: 2px 8px;
                    }}
                """)
                layout.addWidget(badge)

        # Обработчик клика
        frame.mousePressEvent = lambda e, sid=strategy_id: self._on_strategy_clicked(sid)

        return frame

    def _on_strategy_clicked(self, strategy_id: str):
        """Обработчик выбора стратегии"""
        self.strategy_selected.emit(self._category_key, strategy_id)
        self.accept()

    def _on_disable(self):
        """Отключает категорию"""
        self.strategy_selected.emit(self._category_key, "none")
        self.accept()


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
    Новая страница выбора стратегий с единым списком и фильтрацией.

    Использует UnifiedStrategiesList вместо CategoriesTabPanel.
    Поддерживает фильтрацию по TCP/UDP/Discord/Voice/Games.
    """

    strategy_selected = pyqtSignal(str, str)  # category_key, strategy_id
    strategies_changed = pyqtSignal(dict)  # все выборы
    launch_method_changed = pyqtSignal(str)  # для совместимости

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

            # Панель действий
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

            # Создаем unified список
            self._unified_list = UnifiedStrategiesList(self)
            self._unified_list.strategy_selected.connect(self._on_category_clicked)
            self._unified_list.selections_changed.connect(self._on_selections_changed)

            # Строим список
            categories = registry.categories
            self._unified_list.build_list(categories, self.category_selections)

            self.content_layout.addWidget(self._unified_list, 1)

            self._built = True
            log("StrategiesPage (новая) построена", "INFO")

        except Exception as e:
            log(f"Ошибка построения StrategiesPage: {e}", "ERROR")
            import traceback
            log(traceback.format_exc(), "DEBUG")

    def _on_category_clicked(self, category_key: str, strategy_id: str):
        """Обработчик клика по категории - открывает диалог выбора"""
        try:
            from strategy_menu.strategies_registry import registry

            category_info = registry.get_category_info(category_key)
            if not category_info:
                return

            current_strategy = self.category_selections.get(category_key, 'none')

            dialog = StrategySelectionDialog(
                category_key, category_info, current_strategy, self
            )
            dialog.strategy_selected.connect(self._on_strategy_selected)
            dialog.exec()

        except Exception as e:
            log(f"Ошибка открытия диалога: {e}", "ERROR")

    def _on_strategy_selected(self, category_key: str, strategy_id: str):
        """Обработчик выбора стратегии в диалоге"""
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
