# ui/pages/zapret1_direct_strategies_page.py
"""Страница стратегий для Direct Zapret 1 режима (winws.exe)

Этот режим использует winws.exe с JSON стратегиями (как Zapret 2, но без Lua).
"""

from PyQt6.QtCore import Qt, QTimer, QThread
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QFrame, QScrollArea, QPushButton,
                             QSizePolicy, QMessageBox,
                             QButtonGroup)
import qtawesome as qta

from .strategies_page_base import (StrategiesPageBase, ScrollBlockingScrollArea,
                                   Win11Spinner, ResetActionButton)
from ui.sidebar import SettingsCard, ActionButton
from ui.widgets import StrategySearchBar
from log import log


class Zapret1DirectStrategiesPage(StrategiesPageBase):
    """Страница стратегий для Direct Zapret 1 (winws.exe)

    Использует JSON стратегии как Zapret 2, но запускает winws.exe вместо winws2.exe.
    Не использует Lua скрипты.
    """

    # IDs for "disabled" strategy that should always be first
    _DISABLED_STRATEGY_IDS = {"none", "disabled"}
    # Full names (exact match) for disabled strategy
    _DISABLED_STRATEGY_NAMES = {"отключено", "выключено", "disabled", "none"}

    def __init__(self, parent=None):
        super().__init__(parent)
        log("Zapret1DirectStrategiesPage initialized", "DEBUG")

    def _load_content(self):
        """Загружает контент для Direct Zapret 1 режима"""
        try:
            from strategy_menu import get_strategy_launch_method
            mode = get_strategy_launch_method()

            # Если режим не изменился и контент уже загружен - пропускаем
            if mode == self._current_mode and (self._strategy_widget or self._bat_table):
                return

            self._current_mode = mode
            self._clear_content()

            # Эта страница предназначена только для direct_zapret1 режима
            if mode != "direct_zapret1":
                log(f"Zapret1DirectStrategiesPage: запрошен режим {mode}, страница рассчитана на direct_zapret1", "WARNING")

            self.stop_watching()
            self._load_direct_mode()

        except Exception as e:
            log(f"Ошибка загрузки контента Zapret1DirectStrategiesPage: {e}", "ERROR")
            import traceback
            log(traceback.format_exc(), "DEBUG")

            self._clear_content()
            error_label = QLabel(f"❌ Ошибка загрузки: {e}")
            error_label.setStyleSheet("color: #ff6b6b; font-size: 13px;")
            error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.content_layout.addWidget(error_label)

    def _load_direct_mode(self):
        """Загружает интерфейс для direct режима (Zapret 1)"""
        try:
            from strategy_menu.categories_tab_panel import CategoriesTabPanel
            from strategy_menu.strategies_registry import registry
            from strategy_menu import get_direct_strategy_selections, get_default_selections

            # Текущая стратегия (после заголовка и описания)
            if hasattr(self, 'current_widget') and self.current_widget:
                if self.current_widget.parent() != self.content_container:
                    self.content_layout.addWidget(self.current_widget)

            # Поисковая панель - только поиск по тексту
            # Фильтры и сортировка на отдельной странице StrategySortPage
            self.search_bar = StrategySearchBar(self)
            self.search_bar.search_changed.connect(self._on_direct_search_changed)
            # Скрываем фильтры и сортировку - они на отдельной странице
            self.search_bar._label_combo.hide()
            self.search_bar._desync_combo.hide()
            self.search_bar._sort_combo.hide()
            self.content_layout.addWidget(self.search_bar)

            # Панель действий
            actions_card = SettingsCard()
            actions_layout = QHBoxLayout()
            actions_layout.setSpacing(8)

            reload_btn = ActionButton("Обновить", "fa5s.sync-alt")
            reload_btn.clicked.connect(self._reload_strategies)
            actions_layout.addWidget(reload_btn)

            folder_btn = ActionButton("Папка", "fa5s.folder-open")
            folder_btn.clicked.connect(self._open_folder)
            actions_layout.addWidget(folder_btn)

            self._clear_btn = ResetActionButton("Выключить", confirm_text="Всё удалится")
            self._clear_btn.reset_confirmed.connect(self._clear_all)
            actions_layout.addWidget(self._clear_btn)

            self._reset_btn = ResetActionButton("Сбросить", confirm_text="По умолчанию")
            self._reset_btn.reset_confirmed.connect(self._reset_to_defaults)
            actions_layout.addWidget(self._reset_btn)

            actions_layout.addStretch()
            actions_card.add_layout(actions_layout)
            self.content_layout.addWidget(actions_card)

            # Загружаем выборы из реестра или восстанавливаем сохранённые
            try:
                # Если есть сохранённый выбор от перезагрузки - используем его
                if hasattr(self, '_pending_selections') and self._pending_selections:
                    self.category_selections = self._pending_selections
                    self._pending_selections = None  # Очищаем после использования
                    log(f"Восстановлены выборы стратегий после перезагрузки: {len(self.category_selections)} категорий", "DEBUG")
                else:
                    self.category_selections = get_direct_strategy_selections()
                    log(f"Загружены выборы стратегий из реестра: {len(self.category_selections)} категорий", "DEBUG")
            except Exception as e:
                log(f"Ошибка загрузки выборов из реестра: {e}, используем значения по умолчанию", "WARNING")
                self.category_selections = get_default_selections()

            # Создаём панель с вкладками категорий (с кнопкой добавления)
            self._strategy_widget = CategoriesTabPanel(show_add_button=True)
            self._strategy_widget._tab_category_keys = []
            self._strategy_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            self._strategy_widget.add_category_clicked.connect(self._show_add_category_dialog)
            self._strategy_widget.edit_category_clicked.connect(self._show_edit_category_dialog)

            # Получаем данные из реестра
            tab_tooltips = registry.get_tab_tooltips_dict()

            self._category_tab_indices = {}
            # Получаем ВСЕ категории (больше не скрываем, только блокируем)
            category_keys = registry.get_all_category_keys_sorted()

            # Очищаем существующие вкладки
            self._strategy_widget.clear()
            self._strategy_widget._tab_category_keys = []

            # Создаём вкладки для ВСЕХ категорий (по порядку)
            for idx, category_key in enumerate(category_keys):
                category_info = registry.get_category_info(category_key)
                if not category_info:
                    continue

                # Всегда используем full_name, иконки добавляются через icon_name
                display_name = category_info.full_name

                # Заглушка с сохранённым category_key
                placeholder = QWidget()
                placeholder.setProperty("category_key", category_key)
                p_layout = QVBoxLayout(placeholder)
                p_layout.setContentsMargins(20, 20, 20, 20)
                p_layout.addWidget(QLabel("Нажмите для загрузки..."))
                p_layout.addStretch()

                # Добавляем вкладку и сохраняем индекс
                actual_index = self._strategy_widget.addTab(placeholder, display_name, category_key)
                self._category_tab_indices[category_key] = actual_index

                if category_key in tab_tooltips:
                    self._strategy_widget.setTabToolTip(actual_index, tab_tooltips[category_key])

            self._strategy_widget.currentChanged.connect(self._on_tab_changed)
            self._strategy_widget.setMinimumHeight(500)  # Увеличенная высота блока стратегий
            self.content_layout.addWidget(self._strategy_widget, 1)  # stretch=1 - растягивается при увеличении окна

            # Подписываемся на изменение рейтингов для обновления подсветки
            self._setup_rating_callback()

            # Обновляем цвета иконок всех вкладок на основе выборов
            self._strategy_widget.update_all_tab_icons(self.category_selections)

            # Выбираем первую вкладку и загружаем сразу
            if self._strategy_widget.count() > 0:
                self._strategy_widget.blockSignals(True)
                self._strategy_widget.setCurrentIndex(0)
                self._strategy_widget.blockSignals(False)
                self._load_category_tab(0)

            # Добавляем кнопку "+" в конец списка категорий
            self._strategy_widget.add_add_button()

            # Обновляем отображение
            self._update_current_strategies_display()

            # Обновляем отображение фильтров на странице DPI Settings
            self._update_dpi_filters_display()

            log("Direct Zapret 1 режим загружен", "INFO")

        except Exception as e:
            log(f"Ошибка загрузки direct Zapret 1 режима: {e}", "ERROR")
            import traceback
            log(traceback.format_exc(), "DEBUG")
            raise

    # ==================== Обработчики вкладок ====================

    def _on_tab_changed(self, index):
        """При смене вкладки загружаем контент (direct режим)"""
        self._load_category_tab(index)

    def _load_category_tab(self, index):
        """Асинхронная загрузка контента вкладки категории (direct режим)"""
        if not self._strategy_widget:
            return

        widget = self._strategy_widget.widget(index)
        if not widget:
            return

        # Получаем category_key из property или из списка
        category_key = widget.property("category_key")
        if not category_key and hasattr(self._strategy_widget, '_tab_category_keys'):
            keys = self._strategy_widget._tab_category_keys
            if 0 <= index < len(keys):
                category_key = keys[index]

        if not category_key:
            log(f"Не удалось получить category_key для вкладки {index}", "WARNING")
            return

        # Проверяем, загружена ли уже вкладка
        if hasattr(widget, '_loaded') and widget._loaded:
            return

        # Проверяем, не загружается ли уже
        if hasattr(widget, '_loading') and widget._loading:
            return

        widget._loading = True

        # Показываем спиннер загрузки
        self._show_loading_indicator(widget)

        # Запускаем асинхронную загрузку
        from strategy_menu.workers import CategoryTabLoader

        loader = CategoryTabLoader(category_key)
        thread = QThread()
        loader.moveToThread(thread)

        thread.started.connect(loader.run)
        loader.finished.connect(lambda cat, strats, favs, sel:
                               self._on_category_loaded(widget, index, cat, strats, favs, sel))
        loader.error.connect(lambda cat, err:
                            self._on_category_error(widget, cat, err))
        loader.finished.connect(thread.quit)
        loader.finished.connect(loader.deleteLater)
        thread.finished.connect(thread.deleteLater)

        # Сохраняем ссылки чтобы не удалились раньше времени
        widget._loader_thread = thread
        widget._loader = loader

        thread.start()

    def _show_loading_indicator(self, widget):
        """Показывает спиннер загрузки на вкладке"""
        # Очищаем существующий контент
        old_layout = widget.layout()
        if old_layout:
            while old_layout.count():
                item = old_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
        else:
            old_layout = QVBoxLayout(widget)

        old_layout.setContentsMargins(0, 0, 0, 0)
        old_layout.setSpacing(0)

        # Создаем контейнер со спиннером
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        container_layout = QVBoxLayout(container)
        container_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        spinner = Win11Spinner(size=24, color="#60cdff")
        container_layout.addWidget(spinner, alignment=Qt.AlignmentFlag.AlignCenter)

        old_layout.addWidget(container)

    def _on_category_loaded(self, widget, index, category_key, strategies_dict, favorites_list, current_selection):
        """Callback после успешной загрузки данных категории"""
        widget._loading = False

        if not strategies_dict:
            widget._loaded = True
            return

        # Кэшируем данные для фильтрации
        self._all_direct_strategies[category_key] = strategies_dict.copy()
        self._all_direct_favorites[category_key] = list(favorites_list)
        self._all_direct_selections[category_key] = current_selection

        # Применяем текущий фильтр (если есть) перед построением UI
        query = self.search_bar.get_query() if self.search_bar else None
        filtered_strategies = self._filter_direct_strategies(strategies_dict, query)

        # Получаем параметры сортировки
        sort_key, reverse = self.search_bar.get_sort_key() if self.search_bar else ("default", False)

        # Конвертируем в List[StrategyInfo] для сортировки
        # Добавляем is_favorite для корректной сортировки
        favorites_set = set(favorites_list)
        for strategy_id, strategy_data in filtered_strategies.items():
            strategy_data['is_favorite'] = strategy_id in favorites_set

        strategy_info_list = self._convert_direct_dict_to_strategy_info_list(filtered_strategies, category_key)

        # Сортируем используя filter_engine
        sorted_strategies = self.filter_engine.sort_strategies(strategy_info_list, sort_key, reverse)

        # Конвертируем обратно в dict, СОХРАНЯЯ порядок из sorted_strategies
        sorted_dict = {}
        for strategy_info in sorted_strategies:
            strategy_id = strategy_info.id
            if strategy_id in filtered_strategies:
                sorted_dict[strategy_id] = filtered_strategies[strategy_id]

        # При сортировке по имени или рейтингу не разделяем на группы
        skip_grouping = sort_key in ("name", "rating")

        # Строим UI в главном потоке с отсортированными данными
        self._build_category_ui(widget, index, category_key, sorted_dict, favorites_list, current_selection, skip_grouping=skip_grouping)

    def _on_category_error(self, widget, category_key, error_msg):
        """Callback при ошибке загрузки категории"""
        widget._loading = False
        log(f"Ошибка загрузки категории {category_key}: {error_msg}", "ERROR")

    def _build_category_ui(self, widget, index, category_key, strategies_dict, favorites_list, current_selection, skip_grouping=False):
        """Создаёт UI элементы категории из загруженных данных

        Args:
            skip_grouping: Если True, не разделяет на избранные/остальные (для сортировки по имени)
        """
        try:
            from strategy_menu.widgets_favorites import FavoriteCompactStrategyItem

            favorites_set = set(favorites_list)

            # Выносим "Отключено" (none/disabled) в отдельную группу - всегда первая
            disabled_strategies = {}
            other_strategies = {}
            for k, v in strategies_dict.items():
                if self._is_disabled_strategy_id(k, v):
                    disabled_strategies[k] = v
                else:
                    other_strategies[k] = v

            # Разделяем на избранные и остальные (если не skip_grouping)
            if skip_grouping:
                # При сортировке по имени/рейтингу - все в одном списке, порядок из strategies_dict
                favorite_strategies = {}
                regular_strategies = other_strategies
            else:
                favorite_strategies = {k: v for k, v in other_strategies.items() if k in favorites_set}
                regular_strategies = {k: v for k, v in other_strategies.items() if k not in favorites_set}

            # Очищаем виджет
            old_layout = widget.layout()
            if old_layout:
                while old_layout.count():
                    item = old_layout.takeAt(0)
                    if item.widget():
                        item.widget().deleteLater()
            else:
                old_layout = QVBoxLayout(widget)

            old_layout.setContentsMargins(0, 0, 0, 0)
            old_layout.setSpacing(0)

            # Создаём scroll area
            scroll = ScrollBlockingScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QFrame.Shape.NoFrame)
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            scroll.setStyleSheet("QScrollArea{background:transparent;border:none}QScrollBar:vertical{background:rgba(255,255,255,0.05);width:6px}QScrollBar::handle:vertical{background:rgba(255,255,255,0.2);border-radius:3px}")

            content = QWidget()
            content.setStyleSheet("background:transparent")
            content_layout = QVBoxLayout(content)
            content_layout.setContentsMargins(8, 8, 8, 8)
            content_layout.setSpacing(4)

            log(f"Категория {category_key}: текущий выбор = {current_selection}", "DEBUG")

            # Создаём группу радиокнопок
            button_group = QButtonGroup(content)
            button_group.setExclusive(True)

            # === ОТКЛЮЧЕНО (всегда первая) ===
            for strategy_id, strategy_data in disabled_strategies.items():
                item = FavoriteCompactStrategyItem(
                    strategy_id=strategy_id,
                    strategy_data=strategy_data,
                    category_key=category_key,
                    parent=content
                )
                button_group.addButton(item.radio)
                if strategy_id == current_selection:
                    item.radio.setChecked(True)
                item.clicked.connect(lambda sid=strategy_id, cat=category_key:
                                   self._on_strategy_item_clicked(cat, sid))
                item.favoriteToggled.connect(lambda sid, is_fav, cat=category_key, idx=index:
                                            self._on_favorite_toggled_direct(cat, idx))
                content_layout.addWidget(item)

            # Разделитель после "Отключено" (если есть другие стратегии)
            if disabled_strategies and (favorite_strategies or regular_strategies):
                separator = QWidget()
                separator.setFixedHeight(1)
                separator.setStyleSheet("background: rgba(255, 255, 255, 0.08); margin: 8px 0;")
                content_layout.addWidget(separator)

            # === ИЗБРАННЫЕ (вверху) ===
            if favorite_strategies:
                fav_header = QLabel(f"Избранные ({len(favorite_strategies)})")
                fav_header.setStyleSheet("""
                    QLabel {
                        color: #ffc107;
                        font-size: 11px;
                        font-weight: 600;
                        padding: 6px 10px;
                        background: rgba(255, 193, 7, 0.08);
                        border-radius: 4px;
                        margin-bottom: 4px;
                    }
                """)
                content_layout.addWidget(fav_header)

                for strategy_id, strategy_data in favorite_strategies.items():
                    item = FavoriteCompactStrategyItem(
                        strategy_id=strategy_id,
                        strategy_data=strategy_data,
                        category_key=category_key,
                        parent=content
                    )
                    button_group.addButton(item.radio)
                    if strategy_id == current_selection:
                        item.radio.setChecked(True)
                    item.clicked.connect(lambda sid=strategy_id, cat=category_key:
                                       self._on_strategy_item_clicked(cat, sid))
                    item.favoriteToggled.connect(lambda sid, is_fav, cat=category_key, idx=index:
                                                self._on_favorite_toggled_direct(cat, idx))
                    content_layout.addWidget(item)

            # === ОСТАЛЬНЫЕ СТРАТЕГИИ ===
            if regular_strategies:
                if favorite_strategies:
                    # Разделитель
                    separator = QWidget()
                    separator.setFixedHeight(1)
                    separator.setStyleSheet("background: rgba(255, 255, 255, 0.08); margin: 8px 0;")
                    content_layout.addWidget(separator)

                for strategy_id, strategy_data in regular_strategies.items():
                    item = FavoriteCompactStrategyItem(
                        strategy_id=strategy_id,
                        strategy_data=strategy_data,
                        category_key=category_key,
                        parent=content
                    )
                    button_group.addButton(item.radio)
                    if strategy_id == current_selection:
                        item.radio.setChecked(True)
                    item.clicked.connect(lambda sid=strategy_id, cat=category_key:
                                       self._on_strategy_item_clicked(cat, sid))
                    item.favoriteToggled.connect(lambda sid, is_fav, cat=category_key, idx=index:
                                                self._on_favorite_toggled_direct(cat, idx))
                    content_layout.addWidget(item)

            content_layout.addStretch()
            scroll.setWidget(content)
            old_layout.addWidget(scroll)

            widget._loaded = True
            widget._category_key = category_key
            log(f"Загружена категория: {category_key}", "DEBUG")

        except Exception as e:
            log(f"Ошибка построения UI категории {category_key}: {e}", "ERROR")
            import traceback
            log(traceback.format_exc(), "DEBUG")

    def _is_disabled_strategy_id(self, strategy_id: str, strategy_data: dict) -> bool:
        """
        Check if strategy is the "disabled" option.

        Args:
            strategy_id: Strategy ID
            strategy_data: Strategy data dict with 'name' key

        Returns:
            True if this is the disabled/none strategy
        """
        # Check by ID (exact match)
        if strategy_id and strategy_id.lower() in self._DISABLED_STRATEGY_IDS:
            return True

        # Check by name (exact match, not substring!)
        name = strategy_data.get("name", "") if strategy_data else ""
        name_lower = name.lower().strip() if name else ""
        if name_lower in self._DISABLED_STRATEGY_NAMES:
            return True

        return False

    def _on_favorite_toggled_direct(self, category_key, tab_index):
        """Обработчик изменения избранного в Direct режиме - перезагружает вкладку"""
        if not self._strategy_widget:
            return

        widget = self._strategy_widget.widget(tab_index)
        if widget:
            widget._loaded = False
            widget._loading = False  # Сбрасываем флаг загрузки
            self._load_category_tab(tab_index)

    # ==================== Обработчики рейтинга ====================

    def _setup_rating_callback(self):
        """Подписывается на изменение рейтингов стратегий"""
        try:
            from strategy_menu.args_preview_dialog import preview_manager
            preview_manager.add_rating_change_callback(self._on_rating_changed)
        except Exception as e:
            log(f"Ошибка подписки на callback рейтинга: {e}", "WARNING")

    def _on_rating_changed(self, strategy_id, new_rating):
        """Обновляет подсветку при изменении рейтинга стратегии"""
        if not self._strategy_widget:
            return

        # Перезагружаем текущую вкладку для обновления подсветки
        current_index = self._strategy_widget.currentIndex()
        if current_index >= 0:
            widget = self._strategy_widget.widget(current_index)
            if widget:
                widget._loaded = False
                self._load_category_tab(current_index)

    # ==================== Обработчики DPI фильтров ====================

    def _update_dpi_filters_display(self):
        """Обновляет отображение фильтров на странице DPI Settings"""
        try:
            from launcher_common import calculate_required_filters

            # Вычисляем нужные фильтры по текущим выбранным категориям
            filters = calculate_required_filters(self.category_selections)

            # Обновляем UI на странице DPI Settings
            app = self.parent_app
            if hasattr(app, 'dpi_settings_page') and app.dpi_settings_page:
                app.dpi_settings_page.update_filter_display(filters)
        except Exception as e:
            log(f"Ошибка обновления отображения фильтров: {e}", "WARNING")

    # ==================== Обработчики клика по стратегии ====================

    def _on_strategy_item_clicked(self, category_key: str, strategy_id: str):
        """Обработчик клика по стратегии - сразу применяет и перезапускает winws"""
        try:
            self.category_selections[category_key] = strategy_id
            log(f"Выбрана стратегия: {category_key} = {strategy_id}", "INFO")

            # Уведомляем внешние компоненты о выборе стратегии
            from strategy_menu.strategies_registry import registry
            strategy_name = registry.get_strategy_name_safe(category_key, strategy_id)
            self.strategy_selected.emit(strategy_id, strategy_name)

            # NOTE: Zapret 1 режим НЕ использует preset-zapret2.txt, источник состояния — preset-zapret1.txt
            # Пишем preset СНАЧАЛА, чтобы UI сразу видел актуальный выбор (без ожидания асинхронного старта).
            preset_path = None
            try:
                from zapret1_launcher.preset_selections import write_preset_zapret1_from_selections
                from strategy_menu import invalidate_direct_selections_cache

                preset_path = write_preset_zapret1_from_selections(self.category_selections)
                invalidate_direct_selections_cache()
            except Exception as e:
                log(f"Не удалось записать preset-zapret1.txt перед запуском: {e}", "WARNING")

            # Обновляем цвет иконки вкладки (серая если none, цветная если активна)
            current_tab_index = self._strategy_widget.currentIndex()
            is_inactive = (strategy_id == "none" or not strategy_id)
            self._strategy_widget.update_tab_icon_color(current_tab_index, is_inactive=is_inactive)

            # Обновляем отображение текущих стратегий (читаем из preset-zapret1.txt)
            self._update_current_strategies_display()

            # Обновляем отображение фильтров на странице DPI Settings
            self._update_dpi_filters_display()

            # Проверяем, есть ли хотя бы одна активная стратегия
            if not self._has_any_active_strategy():
                log("Нет активных стратегий - останавливаем DPI", "INFO")
                # Останавливаем DPI если все стратегии "none"
                app = self.parent_app
                if hasattr(app, 'dpi_controller') and app.dpi_controller:
                    app.dpi_controller.stop_dpi_async()
                    if hasattr(app, 'current_strategy_label'):
                        app.current_strategy_label.setText("Не выбрана")
                    if hasattr(app, 'current_strategy_name'):
                        app.current_strategy_name = None
                self.show_success()
                return

            # Показываем спиннер загрузки
            self.show_loading()

            # Перезапускаем winws.exe с новыми настройками
            app = self.parent_app
            if hasattr(app, 'dpi_controller') and app.dpi_controller:
                if preset_path is None:
                    from zapret1_launcher.preset_selections import get_preset_zapret1_path
                    preset_path = get_preset_zapret1_path()

                preset_data = {
                    'is_preset_file': True,
                    'name': 'Прямой запуск (Zapret 1)',
                    'preset_path': str(preset_path),
                }

                app.dpi_controller.start_dpi_async(selected_mode=preset_data, launch_method="direct_zapret1")
                log(f"Применена стратегия: {category_key} = {strategy_id}", "DEBUG")

                # Обновляем UI
                if hasattr(app, 'current_strategy_label'):
                    app.current_strategy_label.setText("Прямой запуск (Z1)")
                if hasattr(app, 'current_strategy_name'):
                    app.current_strategy_name = "Прямой запуск (Z1)"

                # Запускаем мониторинг реального статуса процесса
                self._start_process_monitoring()
            else:
                self.show_success()

        except Exception as e:
            log(f"Ошибка применения стратегии: {e}", "ERROR")
            import traceback
            log(traceback.format_exc(), "DEBUG")
            self.show_success()  # При ошибке тоже убираем спиннер

    # ==================== Обновление отображения ====================

    def _update_current_strategies_display(self):
        """Обновляет отображение списка активных стратегий с Font Awesome иконками"""
        try:
            from strategy_menu import get_strategy_launch_method, get_direct_strategy_selections
            from strategy_menu.strategies_registry import registry

            if get_strategy_launch_method() != "direct_zapret1":
                self.current_strategy_label.setToolTip("")
                self.current_strategy_label.show()
                self.current_strategy_container.hide()
                self._has_hidden_strategies = False
                self._tooltip_strategies_data = []
                return

            selections = get_direct_strategy_selections()

            # Собираем только активные (не "none") стратегии
            tooltip_data = []  # Данные для красивого тултипа: (icon_name, icon_color, cat_name, strat_name)
            icons_data = []    # Данные для иконок: (icon_name, icon_color, strategy_name)

            for cat_key in registry.get_all_category_keys():
                strat_id = selections.get(cat_key)
                if strat_id and strat_id != "none":
                    cat_info = registry.get_category_info(cat_key)
                    if not cat_info:
                        continue

                    strategy_name = registry.get_strategy_name_safe(cat_key, strat_id)
                    icon_name = cat_info.icon_name or 'fa5s.globe'
                    icon_color = cat_info.icon_color or '#60cdff'
                    cat_full = cat_info.full_name

                    icons_data.append((icon_name, icon_color, strategy_name))
                    tooltip_data.append((icon_name, icon_color, cat_full, strategy_name))

            # Сохраняем данные для тултипа
            self._tooltip_strategies_data = tooltip_data

            if icons_data:
                # Очищаем старые иконки
                while self.current_icons_layout.count():
                    item = self.current_icons_layout.takeAt(0)
                    if item.widget():
                        item.widget().deleteLater()

                # Скрываем текстовый лейбл, показываем иконки
                self.current_strategy_label.hide()
                self.current_strategy_container.show()

                # Добавляем все иконки
                for icon_name, icon_color, strat_name in icons_data:
                    icon_label = QLabel()
                    try:
                        pixmap = qta.icon(icon_name, color=icon_color).pixmap(16, 16)
                        icon_label.setPixmap(pixmap)
                    except:
                        pixmap = qta.icon('fa5s.globe', color='#60cdff').pixmap(16, 16)
                        icon_label.setPixmap(pixmap)
                    icon_label.setFixedSize(18, 18)
                    icon_label.setToolTip(f"{strat_name}")
                    self.current_icons_layout.addWidget(icon_label)

                self._has_hidden_strategies = len(icons_data) > 3  # Тултип если > 3

            else:
                # Нет активных стратегий
                self.current_strategy_container.hide()
                self.current_strategy_label.show()
                self.current_strategy_label.setText("Не выбрана")
                self.current_strategy_label.setToolTip("")
                self._has_hidden_strategies = False

        except Exception as e:
            log(f"Ошибка обновления отображения: {e}", "ERROR")

    # ==================== Диалоги категорий ====================

    def _show_add_category_dialog(self):
        """Показывает диалог добавления категории"""
        try:
            from ui.dialogs.add_category_dialog import AddCategoryDialog

            dialog = AddCategoryDialog(self)
            dialog.category_added.connect(self._on_category_added)
            dialog.category_updated.connect(self._on_category_updated)
            dialog.category_deleted.connect(self._on_category_deleted)
            dialog.exec()

        except Exception as e:
            log(f"Ошибка открытия диалога добавления категории: {e}", "ERROR")
            import traceback
            log(traceback.format_exc(), "DEBUG")

    def _show_edit_category_dialog(self, category_key: str):
        """Показывает диалог редактирования категории"""
        try:
            from ui.dialogs.add_category_dialog import AddCategoryDialog
            from strategy_menu.strategies_registry import registry

            # Получаем данные категории
            category_info = registry.get_category_info(category_key)
            if not category_info:
                log(f"Категория '{category_key}' не найдена", "WARNING")
                return

            # Преобразуем CategoryInfo в словарь
            category_data = {
                'key': category_info.key,
                'full_name': category_info.full_name,
                'description': category_info.description,
                'tooltip': category_info.tooltip,
                'color': category_info.color,
                'default_strategy': category_info.default_strategy,
                'ports': category_info.ports,
                'protocol': getattr(category_info, 'protocol', 'TCP'),
                'order': category_info.order,
                'command_order': category_info.command_order,
                'needs_new_separator': category_info.needs_new_separator,
                'command_group': category_info.command_group,
                'icon_name': category_info.icon_name,
                'icon_color': category_info.icon_color,
                'base_filter': category_info.base_filter,
                'strategy_type': category_info.strategy_type,
                'requires_all_ports': getattr(category_info, 'requires_all_ports', False),
                'strip_payload': getattr(category_info, 'strip_payload', False)
            }

            dialog = AddCategoryDialog(self, category_data=category_data)
            dialog.category_updated.connect(self._on_category_updated)
            dialog.category_deleted.connect(self._on_category_deleted)
            dialog.exec()

        except Exception as e:
            log(f"Ошибка открытия диалога редактирования категории: {e}", "ERROR")
            import traceback
            log(traceback.format_exc(), "DEBUG")

    def _on_category_added(self, category_data: dict):
        """Обработчик добавления новой категории"""
        try:
            from strategy_menu.strategies_registry import reload_categories

            # Перезагружаем категории
            reload_categories()
            log(f"Категории перезагружены после добавления '{category_data.get('key')}'", "INFO")

            # Перезагружаем страницу
            self._reload_strategies()

        except Exception as e:
            log(f"Ошибка после добавления категории: {e}", "ERROR")

    def _on_category_updated(self, category_data: dict):
        """Обработчик обновления категории"""
        try:
            from strategy_menu.strategies_registry import reload_categories

            # Перезагружаем категории
            reload_categories()
            log(f"Категории перезагружены после обновления '{category_data.get('key')}'", "INFO")

            # Перезагружаем страницу
            self._reload_strategies()

        except Exception as e:
            log(f"Ошибка после обновления категории: {e}", "ERROR")

    def _on_category_deleted(self, category_key: str):
        """Обработчик удаления категории"""
        try:
            from strategy_menu.strategies_registry import reload_categories

            # Перезагружаем категории
            reload_categories()
            log(f"Категории перезагружены после удаления '{category_key}'", "INFO")

            # Перезагружаем страницу
            self._reload_strategies()

        except Exception as e:
            log(f"Ошибка после удаления категории: {e}", "ERROR")

    # ==================== Действия с страницей ====================

    def _reload_strategies(self):
        """Перезагружает стратегии (direct режим)"""
        try:
            from strategy_menu.strategies_registry import registry

            # Сохраняем текущий выбор ПЕРЕД перезагрузкой
            saved_selections = getattr(self, 'category_selections', {}).copy()

            registry.reload_strategies()

            self.stop_watching()  # Останавливаем мониторинг при перезагрузке
            self._current_mode = None
            self._initialized = False

            # Сохраняем выбор для восстановления после загрузки UI
            self._pending_selections = saved_selections

            self._clear_content()

            self.loading_label = QLabel("Перезагрузка...")
            self.loading_label.setStyleSheet("color: rgba(255, 255, 255, 0.6);")
            self.loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.content_layout.addWidget(self.loading_label)

            # Загружаем сразу
            QTimer.singleShot(0, self._load_content)

        except Exception as e:
            log(f"Ошибка перезагрузки: {e}", "ERROR")

    def _open_folder(self):
        """Открывает папку стратегий"""
        try:
            from config import STRATEGIES_FOLDER
            import os
            os.startfile(STRATEGIES_FOLDER)
        except Exception as e:
            log(f"Ошибка открытия папки: {e}", "ERROR")

    def _clear_all(self):
        """Сбрасывает все стратегии в 'none' и останавливает DPI"""
        try:
            from strategy_menu.strategies_registry import registry
            from zapret1_launcher.preset_selections import get_preset_zapret1_path

            # Устанавливаем все стратегии в "none"
            none_selections = {key: "none" for key in registry.get_all_category_keys()}
            self.category_selections = none_selections

            # Обновляем preset-zapret1.txt (делаем пустым, чтобы GUI тоже видел "none")
            try:
                preset_path = get_preset_zapret1_path()
                preset_path.write_text("# Strategy: Disabled\n", encoding="utf-8")
            except Exception:
                pass

            # Обновляем отображение фильтров (теперь все должны быть выключены)
            self._update_dpi_filters_display()

            # Останавливаем DPI, так как нет активных стратегий
            app = self.parent_app
            if hasattr(app, 'dpi_controller') and app.dpi_controller:
                app.dpi_controller.stop_dpi_async()
                log("DPI остановлен после сброса стратегий", "INFO")
                if hasattr(app, 'current_strategy_label'):
                    app.current_strategy_label.setText("Не выбрана")
                if hasattr(app, 'current_strategy_name'):
                    app.current_strategy_name = None

            # Перезагружаем интерфейс (командная строка обновится внутри _load_direct_mode)
            self._reload_strategies()

            log("Все стратегии выключены (установлены в 'none')", "INFO")

        except Exception as e:
            log(f"Ошибка выключения стратегий: {e}", "ERROR")

    def _reset_to_defaults(self):
        """Сбрасывает стратегии к значениям по умолчанию (через preset-zapret1.txt)"""
        try:
            from strategy_menu.strategies_registry import registry
            from strategy_menu import invalidate_direct_selections_cache
            from zapret1_launcher.preset_selections import write_preset_zapret1_from_selections

            defaults = registry.get_default_selections()
            self.category_selections = defaults
            invalidate_direct_selections_cache()
            preset_path = write_preset_zapret1_from_selections(self.category_selections)

            app = self.parent_app
            if hasattr(app, 'dpi_controller') and app.dpi_controller:
                preset_data = {
                    'is_preset_file': True,
                    'name': 'Прямой запуск (Zapret 1)',
                    'preset_path': str(preset_path),
                }
                app.dpi_controller.start_dpi_async(selected_mode=preset_data, launch_method="direct_zapret1")
                log("DPI перезапущен с настройками по умолчанию", "INFO")

            self._reload_strategies()

        except Exception as e:
            log(f"Ошибка сброса к значениям по умолчанию: {e}", "ERROR")
            import traceback
            log(traceback.format_exc(), "DEBUG")

    def reload_for_mode_change(self):
        """Перезагружает страницу при смене режима"""
        self.stop_watching()  # Останавливаем мониторинг при смене режима
        self._stop_process_monitoring()  # Останавливаем мониторинг процесса (+ абсолютный таймаут)
        self._stop_absolute_timeout()  # Дополнительная защита
        self._current_mode = None
        self._initialized = False
        self._clear_content()

        # Сбрасываем текущую стратегию при переключении режима
        self.current_strategy_label.setText("Загрузка...")
        self.current_strategy_label.show()
        self.current_strategy_container.hide()

        # Показываем спиннер загрузки
        self.show_loading()

        # Добавляем плейсхолдер
        self.loading_label = QLabel("Загрузка...")
        self.loading_label.setStyleSheet("color: rgba(255, 255, 255, 0.6); font-size: 13px;")
        self.loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.content_layout.addWidget(self.loading_label)

        # Не загружаем контент пока страница скрыта (иначе она начнёт грузить стратегии
        # для "чужого" режима и будет спамить предупреждения/ошибки).
        # При следующем показе страницы showEvent сам вызовет _load_content().
        if not self.isVisible():
            return

        # Загружаем с небольшой задержкой для плавности UI
        QTimer.singleShot(100, self._load_content)

    def stop_watching(self):
        """Останавливает мониторинг файловой системы"""
        if self._file_watcher:
            try:
                self._file_watcher.directoryChanged.disconnect()
                self._file_watcher.fileChanged.disconnect()
            except:
                pass
            self._file_watcher.deleteLater()
            self._file_watcher = None
        self._watcher_active = False
