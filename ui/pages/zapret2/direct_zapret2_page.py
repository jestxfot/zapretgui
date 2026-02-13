# ui/pages/zapret2/direct_zapret2_page.py
"""
Страница выбора стратегий для режима direct_zapret2 (preset-based).
При клике на категорию открывается отдельная страница StrategyDetailPage.
"""

from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QSize
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QPushButton, QSizePolicy
)
import qtawesome as qta

from ui.pages.base_page import BasePage
from ui.sidebar import SettingsCard, ActionButton
from ui.widgets import UnifiedStrategiesList
from log import log

class Zapret2StrategiesPageNew(BasePage):
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
            title="Прямой запуск Zapret 2",
            subtitle=(
                "Здесь Вы можете ТОНКО изменить стратегию для каждой категории. "
                "Всего существует несколько фаз дурения (send, syndata, fake, multisplit и т.д.). "
                "Последовательность сама определяется программой. "
                "Вы можете писать свои пресеты ручками через txt файл или выбирать готовые стратегии в этом меню. "
                "Каждая стратегия всего лишь набор аргументов, то есть техник (дурения или же фуллинга) для того "
                "чтобы изменить содержимое пакетов по модели TCP/IP, которое отправляет Ваше устройство. "
                "Чтобы алгоритмы ТСПУ провайдера сбились и не заметили (или пропустили) запрещённый контент."
            ),
            parent=parent
        )
        self.parent_app = parent
        self.category_selections = {}
        self._unified_list = None
        self._built = False
        self._build_scheduled = False

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
        if not self._built and not self._build_scheduled:
            self._build_scheduled = True
            QTimer.singleShot(0, self._build_content)

    def _build_content(self):
        """Строит содержимое страницы"""
        try:
            self._build_scheduled = False
            if self._built:
                return

            from strategy_menu.strategies_registry import registry
            from preset_zapret2 import PresetManager

            # Загружаем выборы из preset файла
            preset_manager = PresetManager()
            self.category_selections = preset_manager.get_strategy_selections()
            preset = preset_manager.get_active_preset()
            filter_modes = {}
            if preset:
                filter_modes = {k: v.filter_mode for k, v in preset.categories.items()}

            # Карточка с кнопкой Telegram (выделенная, акцентная)
            telegram_card = SettingsCard()
            telegram_layout = QHBoxLayout()
            telegram_layout.setContentsMargins(0, 0, 0, 0)
            telegram_layout.setSpacing(16)

            # Описательный текст слева
            telegram_hint = QLabel(
                "Хотите добавить свою категорию? Напишите нам! Запрос на добавление своих сайтов можно сделать во вкладке на сайте-форуме через категорию для Zapret GUI."
            )
            telegram_hint.setWordWrap(True)
            telegram_hint.setContentsMargins(12, 0, 0, 0)
            telegram_hint.setStyleSheet("""
                QLabel {
                    background: transparent;
                    color: rgba(255, 255, 255, 0.6);
                    font-size: 13px;
                    font-family: 'Segoe UI Variable', 'Segoe UI', sans-serif;
                }
            """)
            telegram_hint.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
            telegram_hint.setMinimumWidth(0)
            telegram_layout.addWidget(telegram_hint, 1)

            # Кнопка Telegram - тёмная
            telegram_btn = QPushButton("  ОТКРЫТЬ TELEGRAM БОТА")
            telegram_btn.setIcon(qta.icon("fa5b.telegram-plane", color="#ffffff"))
            telegram_btn.setIconSize(QSize(18, 18))
            telegram_btn.setFixedHeight(36)
            telegram_btn.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
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
            telegram_layout.addWidget(telegram_btn, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

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

            actions_layout.addStretch()

            actions_card.add_layout(actions_layout)
            self.content_layout.addWidget(actions_card)

            # Выборы уже загружены в начале _build_content()

            # Список категорий (без правой панели - теперь отдельная страница)
            self._unified_list = UnifiedStrategiesList(self)
            self._unified_list.strategy_selected.connect(self._on_category_clicked)
            self._unified_list.selections_changed.connect(self._on_selections_changed)

            # Строим список
            categories = registry.categories
            self._unified_list.build_list(categories, self.category_selections, filter_modes=filter_modes)

            self.content_layout.addWidget(self._unified_list, 1)

            self._built = True
            log("Zapret2StrategiesPageNew построена", "INFO")

        except Exception as e:
            self._build_scheduled = False
            log(f"Ошибка построения Zapret2StrategiesPageNew: {e}", "ERROR")
            import traceback
            log(traceback.format_exc(), "DEBUG")

    def _on_category_clicked(self, category_key: str, strategy_id: str):
        """Обработчик клика по категории - открывает страницу выбора стратегий"""
        try:
            current_strategy = self.category_selections.get(category_key, 'none')
            # Defer navigation to the next event loop tick: prevents page switch
            # while Qt is still processing the mouse event (can break hover/cursor updates).
            QTimer.singleShot(0, lambda ck=category_key, cs=current_strategy: self.open_category_detail.emit(ck, cs))
        except Exception as e:
            log(f"Ошибка открытия детальной страницы: {e}", "ERROR")

    def apply_strategy_selection(self, category_key: str, strategy_id: str):
        """Применяет выбор стратегии (вызывается из StrategyDetailPage)"""
        try:
            from dpi.zapret2_core_restart import trigger_dpi_reload
            from preset_zapret2 import PresetManager

            # Multi-phase TCP UI persists args directly (strategy_detail_page.py).
            # Avoid clobbering preset args by re-applying a non-existent single strategy.
            if (strategy_id or "").strip().lower() == "custom":
                self.category_selections[category_key] = "custom"
                if self._unified_list:
                    self._unified_list.update_selection(category_key, "custom")
                return

            # Сохраняем в preset файл
            preset_manager = PresetManager(
                on_dpi_reload_needed=lambda: trigger_dpi_reload(
                    self.parent_app,
                    reason="strategy_changed"
                )
            )
            preset_manager.set_strategy_selection(category_key, strategy_id, save_and_sync=True)

            self.category_selections[category_key] = strategy_id

            # Обновляем UI
            if self._unified_list:
                self._unified_list.update_selection(category_key, strategy_id)

            # Эмитим сигналы
            self.strategy_selected.emit(category_key, strategy_id)
            self.strategies_changed.emit(self.category_selections)

            log(f"Выбрана стратегия: {category_key} = {strategy_id}", "INFO")

        except Exception as e:
            log(f"Ошибка сохранения выбора: {e}", "ERROR")

    def apply_filter_mode_change(self, category_key: str, filter_mode: str):
        """Обновляет badge Hostlist/IPset на главной странице без перестроения списка."""
        try:
            if self._unified_list:
                self._unified_list.update_filter_mode(category_key, filter_mode)
        except Exception as e:
            log(f"Ошибка обновления filter_mode: {e}", "DEBUG")

    def _on_selections_changed(self, selections: dict):
        """Обработчик изменения выборов"""
        self.category_selections = selections
        self.strategies_changed.emit(selections)

    def _apply_changes(self):
        """Применяет изменения - перезапускает DPI если запущен"""
        from dpi.zapret2_core_restart import trigger_dpi_reload
        trigger_dpi_reload(
            self.parent_app,
            reason="strategy_changed"
        )

    def _reload_strategies(self):
        """Перезагружает стратегии"""
        try:
            from strategy_menu.strategies_registry import registry

            # Перезагружаем реестр стратегий
            registry.reload_strategies()

            # Перестраиваем UI
            self._built = False
            self._build_scheduled = False

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

    def refresh_from_preset_switch(self):
        """
        Перечитывает активный пресет и обновляет UI списка (без перестроения).
        Вызывается асинхронно из MainWindow после активации пресета.
        """
        try:
            from preset_zapret2 import PresetManager
            from strategy_menu.strategies_registry import registry

            preset_manager = PresetManager()
            self.category_selections = preset_manager.get_strategy_selections() or {}

            preset = preset_manager.get_active_preset()
            filter_modes = {}
            if preset:
                try:
                    filter_modes = {k: v.filter_mode for k, v in (preset.categories or {}).items()}
                except Exception:
                    filter_modes = {}

            if self._unified_list:
                self._unified_list.set_selections(self.category_selections)

                # Sync badges for ALL categories so stale/invalid badges disappear.
                for cat_key in (getattr(registry, "categories", {}) or {}).keys():
                    try:
                        self._unified_list.update_filter_mode(cat_key, (filter_modes or {}).get(cat_key))
                    except Exception:
                        continue

            # Совместимость: обновить счетчик активных
            self._update_current_strategies_display()

        except Exception as e:
            log(f"Ошибка refresh_from_preset_switch: {e}", "DEBUG")

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
            from preset_zapret2 import PresetManager

            preset_manager = PresetManager()
            selections = preset_manager.get_strategy_selections()
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
        """Открывает Telegram-бота для запроса добавления сайтов"""
        from config.telegram_links import open_telegram_link
        open_telegram_link("nozapretinrussia_bot")
