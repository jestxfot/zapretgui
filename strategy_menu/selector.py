# strategy_menu/selector.py

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                            QWidget, QTabWidget, QLabel, QMessageBox, QGroupBox,
                            QTextBrowser, QSizePolicy, QFrame, QScrollArea,
                            QRadioButton, QButtonGroup, QCheckBox, QProgressBar,
                            QComboBox)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QTimer
from PyQt6.QtGui import QFont

from log import log
from strategy_menu import get_strategy_launch_method

from .constants import MINIMUM_WIDTH, MINIMIM_HEIGHT
from .widgets import CompactStrategyItem
from .strategy_table_widget_favorites import StrategyTableWithFavoritesFilter as StrategyTableWidget
from .workers import InternetStrategyLoader
from .command_line_dialog import show_command_line_dialog
from .animated_side_panel import AnimatedSidePanel
from strategy_menu.strategies_registry import registry
from .lazy_tab_loader import LazyTabLoader
from .profiler import PerformanceProfiler

class StrategySelector(QDialog):
    """Диалог для выбора стратегии обхода блокировок"""

    strategySelected = pyqtSignal(str, str)
    
    _instance = None
    _is_initialized = False

    @classmethod
    def get_instance(cls, parent=None, strategy_manager=None, current_strategy_name=None):
        """Получить единственный экземпляр диалога (Singleton pattern)"""
        if cls._instance is None:
            log("Создание нового экземпляра StrategySelector", "DEBUG")
            cls._instance = cls(parent, strategy_manager, current_strategy_name)
        else:
            log("Переиспользование существующего экземпляра StrategySelector", "DEBUG")
            cls._instance.current_strategy_name = current_strategy_name
            cls._instance.strategy_manager = strategy_manager
            
        return cls._instance

    def __init__(self, parent=None, strategy_manager=None, current_strategy_name=None):
        if self._is_initialized:
            log("Диалог уже инициализирован, пропуск __init__", "DEBUG")
            return
            
        super().__init__(parent)

        self.setStyleSheet("""
            QToolTip {
                background-color: #2a2a2a;
                color: white;
                border: 1px solid #2196F3;
                padding: 15px;
                font-size: 10pt;
                border-radius: 4px;
            }
        """)

        self.strategy_manager = strategy_manager
        self.current_strategy_name = current_strategy_name
        self.selected_strategy_id = None
        self.selected_strategy_name = None

        self._combined_args = None
        self._combined_strategy_data = None
        self.category_selections = {}

        self._category_widgets_cache = {}
        self._loading_in_progress = False
        self._categories_loaded = set()

        self.is_loading_strategies = False
        self.loader_thread = None
        self.loader_worker = None

        self.launch_method = get_strategy_launch_method()
        self.is_direct_mode = (self.launch_method == "direct")

        self.setWindowTitle("Собери свой пресет сам (из готовых стратегий)")
        self.resize(MINIMUM_WIDTH, MINIMIM_HEIGHT)
        self.setMinimumSize(400, 350)
        self.setModal(False)

        self.init_ui()

        if self.is_direct_mode:
            self.lazy_loader = LazyTabLoader(self)
            QTimer.singleShot(10, self._init_lazy_loading)
        else:
            self.load_local_strategies()

        self._is_initialized = True
        log("Диалог StrategySelector инициализирован", "DEBUG")

    def _init_lazy_loading(self):
        """Инициализирует ленивую загрузку вкладок"""
        log("Инициализация ленивой загрузки вкладок", "DEBUG")
        
        # ✅ Загружаем ТОЛЬКО первую вкладку
        self.lazy_loader.preload_first_tab()
        
        # ✅ Подключаем обработчик переключения вкладок
        self.category_tabs.currentChanged.connect(self._on_category_tab_changed)
        
        # ✅ Включаем кнопку выбора после загрузки первой вкладки
        QTimer.singleShot(200, lambda: self.select_button.setEnabled(True))
        
        # ✅ Обновляем статус
        QTimer.singleShot(150, lambda: self._update_loading_status())
        
        # ❌ ФОНОВАЯ ЗАГРУЗКА ОТКЛЮЧЕНА!
        # Вкладки загружаются ТОЛЬКО по клику пользователя
        
        log("Ленивая загрузка инициализирована (загружена только первая вкладка)", "INFO")

    def _on_category_tab_changed(self, index):
        """
        Обработчик переключения вкладки - загружает содержимое по требованию
        ✅ Защита от повторной загрузки
        ✅ Мгновенный отклик для уже загруженных вкладок
        """
        if not hasattr(self, 'lazy_loader'):
            return
        
        # ✅ Проверяем: уже загружена?
        if index in self.lazy_loader.loaded_tabs:
            # Вкладка уже загружена, ничего не делаем
            return
        
        # ✅ Загружаем вкладку по клику
        log(f"Переключение на вкладку {index}, загружаем содержимое", "DEBUG")
        self.lazy_loader.load_tab_content(index)

    def _update_loading_status(self):
        """Обновляет статус загрузки"""
        if hasattr(self, 'status_label'):
            self.status_label.setText("✅ Готово к выбору")
            self.status_label.setStyleSheet("font-weight: bold; color: #4CAF50; font-size: 9pt; padding: 3px;")
        
        if hasattr(self, 'loading_progress'):
            self.loading_progress.setVisible(False)

    def _init_direct_mode_ui(self, layout):
        """Инициализирует интерфейс для прямого режима"""
        
        self._pending_categories = []
        self._categories_loaded = set()
        
        try:
            from strategy_menu import get_direct_strategy_selections
            self.category_selections = get_direct_strategy_selections()
        except Exception as e:
            log(f"Ошибка загрузки выборов: {e}", "⚠ WARNING")
            from strategy_menu import get_default_selections
            self.category_selections = get_default_selections()

        title = QLabel("Выберите стратегию для каждого типа трафика чтобы собрать пресет")
        title.setStyleSheet("font-weight: bold; font-size: 10pt; color: #2196F3; margin: 5px;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # Прогресс бар (теперь почти не нужен, но оставим для совместимости)
        self.loading_progress = QProgressBar()
        self.loading_progress.setFixedHeight(3)
        self.loading_progress.setTextVisible(False)
        self.loading_progress.setStyleSheet("""
            QProgressBar { border: none; background: #2a2a2a; }
            QProgressBar::chunk { background: #2196F3; }
        """)
        self.loading_progress.setVisible(True)  # Покажем на секунду
        self.loading_progress.setRange(0, 0)  # Бесконечная анимация
        layout.addWidget(self.loading_progress)

        self.category_tabs = AnimatedSidePanel()
        self.category_tabs._tab_category_keys = []
        self.category_tabs.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.category_tabs.tabBar().installEventFilter(self)

        self.tab_tooltips = registry.get_tab_tooltips_dict()
        self.tab_names = registry.get_tab_names_dict()
        self.category_tabs.set_tab_names(self.tab_names)

        self._category_tab_indices = {}
        category_keys = registry.get_all_category_keys()

        # Создаем ВСЕ вкладки сразу, но с заглушками
        for i, category_key in enumerate(category_keys):
            category_info = registry.get_category_info(category_key)
            if not category_info:
                continue
                
            self._category_tab_indices[category_key] = i
            
            if self.category_tabs.is_pinned:
                display_name = category_info.full_name
            else:
                display_name = category_info.short_name

            # Создаем заглушку (будет заменена при ленивой загрузке)
            placeholder = QWidget()
            placeholder.category_key = category_key  # ✅ Главное - сохранить ключ!
            p_layout = QVBoxLayout(placeholder)
            p_layout.setContentsMargins(20, 20, 20, 20)
            p_layout.addWidget(QLabel("⏳ Нажмите для загрузки..."))
            p_layout.addStretch()
            
            tab_index = self.category_tabs.addTab(placeholder, display_name, category_key)
            
            if category_key in self.tab_tooltips:
                self.category_tabs.setTabToolTip(tab_index, self.tab_tooltips[category_key])

        layout.addWidget(self.category_tabs, 1)

        self._create_preview_widget(layout)

        self.status_label = QLabel("⏳ Загрузка стратегий...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("font-weight: bold; color: #ffa500; font-size: 9pt; padding: 3px;")
        self.status_label.setFixedHeight(25)
        layout.addWidget(self.status_label)

        self.select_button.setEnabled(False)  # Включится после загрузки первой вкладки

    def _populate_tab_content(self, tab_widget, strategies, category_key, category_info):
        """
        Заполняет существующий виджет вкладки содержимым
        ✅ В 3-5 раз быстрее чем пересоздание вкладки через insertTab!
        """
        from .profiler import PerformanceProfiler
        from PyQt6.QtWidgets import QScrollArea, QButtonGroup
        
        profiler = PerformanceProfiler(f"populate_{category_key}")
        profiler.start()
        
        # ✅ ИСПРАВЛЕНО: Сначала блокируем обновления
        tab_widget.setUpdatesEnabled(False)
        
        # Очищаем старый layout СИНХРОННО
        old_layout = tab_widget.layout()
        if old_layout:
            while old_layout.count():
                item = old_layout.takeAt(0)
                if item.widget():
                    widget = item.widget()
                    widget.setParent(None)
                    widget.deleteLater()
            # ✅ Удаляем layout СИНХРОННО
            from PyQt6.sip import delete as sip_delete
            try:
                sip_delete(old_layout)
            except:
                old_layout.setParent(None)
                old_layout.deleteLater()
        
        profiler.checkpoint("Layout очищен")
        
        # Создаем новый layout
        tab_layout = QVBoxLayout(tab_widget)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.setSpacing(0)
        
        # Заголовок
        title_label = QLabel(category_info.description)
        title_label.setStyleSheet("""
            font-weight: bold; 
            font-size: 10pt; 
            color: #2196F3;
            padding-top: 10px;
            margin-top: 5px;
            padding-left: 5px;
        """)
        tab_layout.addWidget(title_label)
        
        # Счетчик избранных
        favorites_label = QLabel("")
        favorites_label.setStyleSheet("color: #ffd700; font-weight: bold; font-size: 8pt;")
        favorites_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        tab_layout.addWidget(favorites_label)
        
        profiler.checkpoint("Заголовки созданы")
        
        # Scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
            QScrollArea { 
                border: none; 
                background: transparent;
                margin: 0px; padding: 0px;
            }
            QScrollBar:vertical { width: 10px; background: #2a2a2a; }
            QScrollBar::handle:vertical { background: #555; border-radius: 5px; min-height: 20px; }
            QScrollBar::handle:vertical:hover { background: #666; }
        """)
        
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(3)
        
        button_group = QButtonGroup()
        
        profiler.checkpoint("Контейнеры созданы")
        
        # Сортировка
        sorted_strategies = self._sort_category_strategies(strategies, category_key)
        profiler.checkpoint(f"Сортировка ({len(sorted_strategies)} шт)")
        
        # Избранные
        from strategy_menu import get_favorites_for_category
        favorites_set = get_favorites_for_category(category_key)
        favorites_count = 0
        
        profiler.checkpoint("Избранные загружены")
        
        # Создаем виджеты
        from .widgets_favorites import get_strategy_widget
        
        for idx, (strat_id, strat_data) in enumerate(sorted_strategies):
            is_fav = strat_id in favorites_set
            if is_fav:
                favorites_count += 1
            
            strategy_item = get_strategy_widget(strat_id, strat_data, category_key)
            
            if strat_id == self.category_selections.get(category_key):
                strategy_item.set_checked(True)
            
            strategy_item.clicked.connect(
                lambda sid=strat_id, cat=category_key: 
                    self.on_category_selection_changed(cat, sid)
            )
            
            strategy_item.favoriteToggled.connect(
                lambda sid, is_fav, cat=category_key: 
                    self._on_direct_favorite_toggled(sid, is_fav, cat)
            )
            
            strategy_item.favoriteToggled.connect(
                lambda sid, is_fav, cat=category_key, fl=favorites_label:
                    self._on_category_favorite_toggled(cat, sid, is_fav, fl, scroll_widget)
            )
            
            button_group.addButton(strategy_item.radio, idx)
            scroll_layout.addWidget(strategy_item)
        
        profiler.checkpoint(f"Виджеты созданы ({len(sorted_strategies)} шт)")
        
        # Финализация
        if favorites_count > 0:
            favorites_label.setText(f"⭐ {favorites_count}")
        
        setattr(self, f"{category_key}_button_group", button_group)
        setattr(self, f"{category_key}_favorites_label", favorites_label)
        
        scroll_layout.addStretch()
        scroll_area.setWidget(scroll_widget)
        tab_layout.addWidget(scroll_area)
        
        profiler.checkpoint("Layout собран")
        
        # ✅ КЛЮЧЕВОЕ ИСПРАВЛЕНИЕ: Принудительно обновляем геометрию и перерисовку
        scroll_widget.updateGeometry()
        scroll_area.updateGeometry()
        tab_widget.updateGeometry()
        
        # ✅ Разблокируем обновления и принудительно перерисовываем
        tab_widget.setUpdatesEnabled(True)
        tab_widget.update()
        scroll_area.update()
        
        profiler.checkpoint("UI обновлен")
        profiler.end()
        
        log(f"✅ _populate_tab_content завершен для {category_key} ({len(sorted_strategies)} стратегий)", "DEBUG")

    def eventFilter(self, obj, event):
        """Обработчик событий для анимации табов"""
        return super().eventFilter(obj, event)

    def _expand_all_tabs(self):
        """Разворачивает ВСЕ табы при наведении"""
        if hasattr(self, 'category_tabs'):
            self.category_tabs.show_full_names()

    def _collapse_all_tabs(self):
        """Сворачивает ВСЕ табы при уходе мышки"""
        if hasattr(self, 'category_tabs'):
            self.category_tabs.show_short_names()

    def _get_tab_tooltips(self):
        """Возвращает словарь с подсказками для вкладок"""
        return registry.get_tab_tooltips_dict()

    def _on_direct_favorite_toggled(self, strategy_id, is_favorite, category):
        """Обработчик изменения избранного в Direct режиме"""
        action = "добавлена в" if is_favorite else "удалена из"
        log(f"Стратегия {strategy_id} {action} избранных в категории {category}", "INFO")

        self.status_label.setText(f"{'⭐ Добавлено в избранные' if is_favorite else '☆ Удалено из избранных'}")
        self.status_label.setStyleSheet("font-weight: bold; color: #ffd700; font-size: 9pt; padding: 3px;")

        QTimer.singleShot(2000, lambda: self.status_label.setText("✅ Готово к выбору"))

    def _sort_category_strategies(self, strategies, category_key):
        """
        Сортирует стратегии категории: избранные вверху
        
        Args:
            strategies: Словарь стратегий {id: data}
            category_key: Ключ категории для проверки избранных
        """
        from strategy_menu import is_favorite_strategy

        favorites = []
        regular = []

        for strat_id, strat_data in strategies.items():
            if is_favorite_strategy(strat_id, category_key):
                favorites.append((strat_id, strat_data))
            else:
                regular.append((strat_id, strat_data))

        favorites.sort(key=lambda x: x[1].get('name', x[0]).lower())
        return favorites + regular

    def _on_category_favorite_toggled(self, category_key, strategy_id, is_favorite, favorites_label, scroll_widget):
        """Обработчик изменения избранного в категории"""
        from strategy_menu import is_favorite_strategy

        favorites_count = 0
        for child in scroll_widget.findChildren(CompactStrategyItem):
            if hasattr(child, 'strategy_id') and is_favorite_strategy(child.strategy_id, category_key):
                favorites_count += 1

        favorites_label.setText(f"⭐ {favorites_count}" if favorites_count > 0 else "")

        action = "добавлена в" if is_favorite else "удалена из"
        log(f"Стратегия {strategy_id} {action} избранных в категории {category_key}", "INFO")

        QTimer.singleShot(500, lambda: self._resort_category_strategies(category_key))

    def _resort_category_strategies(self, category_key):
        """Пересортировывает стратегии в категории с учетом избранных"""
        category_keys = registry.get_all_category_keys()
        try:
            tab_index = category_keys.index(category_key)
        except ValueError:
            log(f"Категория {category_key} не найдена в реестре", "⚠ WARNING")
            return

        if tab_index == -1 or tab_index >= self.category_tabs.count():
            return

        tab_widget = self.category_tabs.widget(tab_index)
        if not tab_widget:
            return

        scroll_area = None
        for child in tab_widget.findChildren(QScrollArea):
            scroll_area = child
            break
        if not scroll_area:
            return

        scroll_widget = scroll_area.widget()
        if not scroll_widget:
            return

        strategy_items = []
        for child in scroll_widget.findChildren(CompactStrategyItem):
            strategy_items.append({
                'widget': child,
                'id': child.strategy_id,
                'data': child.strategy_data,
                'is_checked': child.radio.isChecked()
            })

        layout = scroll_widget.layout()
        while layout.count() > 0:
            item = layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)

        from strategy_menu import is_favorite_strategy

        favorites = []
        regular = []
        for item in strategy_items:
            if is_favorite_strategy(item['id'], category_key):
                favorites.append(item)
            else:
                regular.append(item)

        favorites.sort(key=lambda x: x['data'].get('name', x['id']).lower())
        regular.sort(key=lambda x: x['data'].get('name', x['id']).lower())

        all_sorted = favorites + regular
        button_group = getattr(self, f"{category_key}_button_group", None)

        for idx, item in enumerate(all_sorted):
            layout.addWidget(item['widget'])
            if item['is_checked']:
                item['widget'].set_checked(True)
            if button_group:
                button_group.addButton(item['widget'].radio, idx)

        layout.addStretch()

    def init_ui(self):
        """Инициализация интерфейса"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        self._create_control_buttons()
        self._create_tabs()

        layout.addWidget(self.tab_widget)
        layout.addWidget(self.buttons_widget)

    def _create_control_buttons(self):
        """Создает кнопки управления"""
        self.buttons_layout = QHBoxLayout()
        self.buttons_layout.setSpacing(10)

        from strategy_menu import get_keep_dialog_open
        button_text = "✅ Применить" if get_keep_dialog_open() else "✅ Выбрать"
        
        self.select_button = QPushButton(button_text)
        self.select_button.clicked.connect(self.accept)
        self.select_button.setEnabled(False)
        self.select_button.setMinimumHeight(30)
        self.buttons_layout.addWidget(self.select_button)

        self.cancel_button = QPushButton("❌ Отмена")
        self.cancel_button.clicked.connect(self.reject)
        self.cancel_button.setMinimumHeight(30)
        self.buttons_layout.addWidget(self.cancel_button)

        self.help_button = QPushButton("❓ Справка")
        self.help_button.clicked.connect(self._open_help_pdf)
        self.help_button.setMinimumHeight(30)
        self.buttons_layout.addWidget(self.help_button)

        self.help_button = QPushButton("💬 Поддержка")
        self.help_button.clicked.connect(self._open_support)
        self.help_button.setMinimumHeight(30)
        self.buttons_layout.addWidget(self.help_button)

        self.buttons_widget = QWidget()
        self.buttons_widget.setLayout(self.buttons_layout)

    def _open_support(self):
        try:
            import webbrowser
            webbrowser.open("https://t.me/zapret_support_bot")
            self._set_status("Открываю поддержку...")
        except Exception as e:
            err = f"Ошибка при открытии поддержки: {e}"
            self._set_status(err)
            QMessageBox.warning(self._pw, "Ошибка", err)

    def _open_help_pdf(self):
        """Открывает PDF руководство пользователя"""
        try:
            from config import HELP_FOLDER
            import os
            
            pdf_path = os.path.join(HELP_FOLDER, "Как пользоваться Zapret.pdf")
            
            if not os.path.exists(pdf_path):
                log(f"PDF руководство не найдено: {pdf_path}", "❌ ERROR")
                
                QMessageBox.warning(
                    self,
                    "Файл не найден",
                    f"Руководство пользователя не найдено:\n{pdf_path}\n\n"
                    "Пожалуйста, переустановите программу или обратитесь в поддержку."
                )
                return
            
            log(f"Открываем PDF руководство: {pdf_path}", "INFO")
            os.startfile(pdf_path)
            log("PDF руководство успешно открыто", "✅ SUCCESS")
            
        except Exception as e:
            log(f"Ошибка при открытии PDF руководства: {e}", "❌ ERROR")
            
            QMessageBox.critical(
                self,
                "Ошибка",
                f"Не удалось открыть руководство пользователя:\n{str(e)}\n\n"
                "Попробуйте открыть файл вручную из папки Help."
            )

    def _create_tabs(self):
        """Создает вкладки интерфейса"""
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #444;
                background: #2a2a2a;
            }
            QTabBar::tab {
                padding: 5px 10px;
                min-width: 80px;
            }
            QTabBar::tab:selected {
                background: #3a3a3a;
                border-bottom: 2px solid #2196F3;
            }
        """)

        self.strategies_tab = QWidget()
        self._init_strategies_tab()
        self.tab_widget.addTab(self.strategies_tab, "📋 Стратегии")

        from .hostlists_tab import HostlistsTab
        self.hostlists_tab = HostlistsTab()
        self.hostlists_tab.hostlists_changed.connect(self._on_hostlists_changed)
        self.tab_widget.addTab(self.hostlists_tab, "🌐 Hostlist")

        from .ipsets_tab import IpsetsTab
        self.ipsets_tab = IpsetsTab()
        self.ipsets_tab.ipsets_changed.connect(self._on_ipsets_changed)
        self.tab_widget.addTab(self.ipsets_tab, "🔢 IPSet")

        self.settings_tab = QWidget()
        self._init_settings_tab()
        self.tab_widget.addTab(self.settings_tab, "⚙️ Настройки")

        self.tab_widget.currentChanged.connect(self._on_tab_changed)

    def _on_hostlists_changed(self):
        log("Хостлисты изменены, может потребоваться перезапуск DPI", "INFO")

    def _on_ipsets_changed(self):
        log("IPsets изменены, может потребоваться перезапуск DPI", "INFO")

    def _init_strategies_tab(self):
        layout = QVBoxLayout(self.strategies_tab)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        if self.is_direct_mode:
            self._init_direct_mode_ui(layout)
        else:
            self._init_bat_mode_ui(layout)

    def _init_bat_mode_ui(self, layout):
        self.strategy_table = StrategyTableWidget(self.strategy_manager, self)
        self.strategy_table.strategy_selected.connect(self._on_table_strategy_selected)
        self.strategy_table.strategy_double_clicked.connect(self._on_table_strategy_double_clicked)
        self.strategy_table.refresh_button.clicked.connect(self.refresh_strategies)
        self.strategy_table.download_all_button.clicked.connect(self.strategy_table.download_all_strategies_async)
        layout.addWidget(self.strategy_table)

    def _create_preview_widget(self, layout):
        preview_widget = QFrame()
        preview_widget.setFrameStyle(QFrame.Shape.Box)
        preview_widget.setMaximumHeight(100)
        preview_layout = QVBoxLayout(preview_widget)
        preview_layout.setContentsMargins(5, 5, 5, 5)
        preview_layout.setSpacing(2)

        preview_label = QLabel("📋 Итоговый пресет (активные типы трафика):")
        preview_label.setStyleSheet("font-weight: bold; font-size: 9pt;")
        preview_layout.addWidget(preview_label)

        hint_label = QLabel("💡 Нажмите для просмотра полной командной строки")
        hint_label.setStyleSheet("font-size: 8pt; color: #888; font-style: italic;")
        preview_layout.addWidget(hint_label)

        self.preview_text = QTextBrowser()
        self.preview_text.setMaximumHeight(50)
        self.preview_text.setStyleSheet("""
            QTextBrowser {
                background: #222;
                border: 1px solid #444;
                font-family: Arial;
                font-size: 8pt;
                color: #aaa;
            }
            QTextBrowser:hover {
                border: 1px solid #2196F3;
                background: #2a2a2a;
                cursor: pointer;
            }
        """)

        self.preview_text.setOpenExternalLinks(False)
        self.preview_text.mousePressEvent = self._preview_clicked

        preview_layout.addWidget(self.preview_text)
        layout.addWidget(preview_widget, 0)

    def _preview_clicked(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            show_command_line_dialog(self)

    def _init_settings_tab(self):
        tab_layout = QVBoxLayout(self.settings_tab)
        tab_layout.setContentsMargins(0, 0, 0, 0)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setViewportMargins(0, 0, 0, 0)
        scroll_area.setStyleSheet("""
            QScrollArea { 
                border: none; 
                background: transparent;
                margin: 0px;
                padding: 0px;
            }
            QWidget { 
                margin: 0px;
                padding: 0px;
            }
            QScrollBar:vertical { width: 10px; background: #2a2a2a; }
            QScrollBar::handle:vertical { background: #555; border-radius: 5px; min-height: 20px; }
            QScrollBar::handle:vertical:hover { background: #666; }
        """)

        scroll_widget = QWidget()
        layout = QVBoxLayout(scroll_widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        title_label = QLabel("Выберите метод запуска стратегий")
        title_font = title_label.font()
        title_font.setBold(True)
        title_font.setPointSize(11)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet(
            "font-weight: bold; font-size: 10pt; color: #2196F3; margin: 0 0 4px 0;"
        )
        layout.addWidget(title_label)

        method_group = QGroupBox("Метод запуска стратегий")
        method_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold; border: 1px solid #444; border-radius: 5px;
                margin-top: 10px; padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin; left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        method_layout = QVBoxLayout(method_group)

        self.method_button_group = QButtonGroup()

        self.direct_method_radio = QRadioButton("Прямой запуск (рекомендуется)")
        self.direct_method_radio.setToolTip(
            "Запускает встроенные стратегии напрямую из Python.\n"
            "Не требует интернета, все стратегии включены в программу.\n"
            "Полностью скрытый запуск без окон консоли."
        )
        self.method_button_group.addButton(self.direct_method_radio, 1)
        method_layout.addWidget(self.direct_method_radio)

        self.bat_method_radio = QRadioButton("Классический метод (через .bat файлы)")
        self.bat_method_radio.setToolTip(
            "Использует .bat файлы для запуска стратегий.\n"
            "Загружает стратегии из интернета.\n"
            "Может показывать окна консоли при запуске."
        )
        self.method_button_group.addButton(self.bat_method_radio, 0)
        method_layout.addWidget(self.bat_method_radio)

        current_method = get_strategy_launch_method()
        if current_method == "direct":
            self.direct_method_radio.setChecked(True)
        else:
            self.bat_method_radio.setChecked(True)

        self.method_button_group.buttonClicked.connect(self._on_method_changed)
        layout.addWidget(method_group)

        self._create_launch_params(layout)

        info_group = QGroupBox("Информация")
        info_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold; border: 1px solid #444; border-radius: 5px;
                margin-top: 10px; padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin; left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        info_layout = QVBoxLayout(info_group)

        info_text = QLabel(
            "• Прямой запуск: использует встроенные стратегии, не требует интернета\n"
            "• Классический метод: загружает стратегии из интернета в виде .bat файлов\n"
            "• При смене метода список стратегий обновится автоматически"
        )
        info_text.setWordWrap(True)
        info_text.setStyleSheet("padding: 10px; font-weight: normal;")
        info_layout.addWidget(info_text)
        layout.addWidget(info_group)

        auto_update_note = QLabel(
            "💡 После любых изменений в этом окне следует ЗАНОВО перезапустить пресет через кнопку ✅ Выбрать"
        )
        auto_update_note.setAlignment(Qt.AlignmentFlag.AlignCenter)
        auto_update_note.setWordWrap(True)
        auto_update_note.setStyleSheet(
            "padding: 8px; background: #2196F3; color: white; "
            "border-radius: 5px; font-weight: bold; margin: 5px;"
        )
        layout.addWidget(auto_update_note)

        layout.addStretch()

        scroll_area.setWidget(scroll_widget)
        tab_layout.addWidget(scroll_area)

    def _create_launch_params(self, layout):
        """Создает параметры запуска"""
        from strategy_menu import get_wssize_enabled, get_allzone_hostlist_enabled

        params_group = QGroupBox("Параметры запуска")
        params_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold; border: 1px solid #444; border-radius: 5px;
                margin-top: 10px; padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin; left: 10px;
                padding: 0 5px 0 5px; color: #ffa500;
            }
        """)
        params_layout = QVBoxLayout(params_group)
        params_layout.setSpacing(8)

        warning_label = QLabel("⚠️ Перезапустите стратегию после изменения параметров")
        warning_label.setStyleSheet("color: #ffa500; font-weight: bold; font-size: 9pt; margin-bottom: 5px;")
        params_layout.addWidget(warning_label)

        # Чекбокс: Не закрывать окно после выбора
        keep_open_widget = QWidget()
        keep_open_layout = QVBoxLayout(keep_open_widget)
        keep_open_layout.setContentsMargins(0, 0, 0, 0)
        keep_open_layout.setSpacing(3)

        from strategy_menu import get_keep_dialog_open
        self.keep_dialog_open_checkbox = QCheckBox("🔓 Не закрывать окно после выбора стратегии")
        self.keep_dialog_open_checkbox.setToolTip(
            "Если включено, окно выбора стратегии останется открытым после применения.\n"
            "Полезно для быстрого переключения между стратегиями.\n"
            "Если выключено, окно автоматически закроется после выбора."
        )
        self.keep_dialog_open_checkbox.setStyleSheet("font-weight: bold; color: #4CAF50;")
        self.keep_dialog_open_checkbox.setChecked(get_keep_dialog_open())
        self.keep_dialog_open_checkbox.stateChanged.connect(self._on_keep_dialog_open_changed)
        keep_open_layout.addWidget(self.keep_dialog_open_checkbox)

        keep_open_info = QLabel("Окно останется открытым для быстрого переключения стратегий")
        keep_open_info.setWordWrap(True)
        keep_open_info.setStyleSheet("padding-left: 20px; color: #aaa; font-size: 8pt;")
        keep_open_layout.addWidget(keep_open_info)

        params_layout.addWidget(keep_open_widget)
        
        # Закрепление табов (только для Direct режима)
        if self.is_direct_mode:
            tabs_widget = QWidget()
            tabs_layout = QVBoxLayout(tabs_widget)
            tabs_layout.setContentsMargins(0, 0, 0, 0)
            tabs_layout.setSpacing(3)

            self.pin_tabs_checkbox = QCheckBox("📌 Закрепить боковую панель вкладок")
            self.pin_tabs_checkbox.setToolTip(
                "Если включено, боковая панель с вкладками всегда будет развернута.\n"
                "Если выключено, панель будет автоматически сворачиваться при отведении мыши."
            )
            self.pin_tabs_checkbox.setStyleSheet("font-weight: bold;")

            from strategy_menu import get_tabs_pinned
            self.pin_tabs_checkbox.setChecked(get_tabs_pinned())
            self.pin_tabs_checkbox.stateChanged.connect(self._on_pin_tabs_changed)
            tabs_layout.addWidget(self.pin_tabs_checkbox)

            tabs_info = QLabel("Панель не будет автоматически скрываться")
            tabs_info.setWordWrap(True)
            tabs_info.setStyleSheet("padding-left: 20px; color: #aaa; font-size: 8pt;")
            tabs_layout.addWidget(tabs_info)

            params_layout.addWidget(tabs_widget)
            params_layout.addWidget(self._create_separator())

        params_layout.addWidget(self._create_separator())

        if self.is_direct_mode:
            # Добавляем выбор базовых аргументов
            base_args_widget = QWidget()
            base_args_layout = QVBoxLayout(base_args_widget)
            base_args_layout.setContentsMargins(0, 0, 0, 0)
            base_args_layout.setSpacing(3)
            
            base_args_label = QLabel("🔧 Базовые аргументы запуска:")
            base_args_label.setStyleSheet("font-weight: bold; margin-bottom: 3px;")
            base_args_layout.addWidget(base_args_label)
            
            self.base_args_combo = QComboBox()
            self.base_args_combo.setStyleSheet("""
                QComboBox {
                    padding: 5px;
                    background: #333;
                    border: 1px solid #555;
                    border-radius: 3px;
                    font-size: 9pt;
                }
                QComboBox:hover {
                    border: 1px solid #2196F3;
                }
                QComboBox::drop-down {
                    border: none;
                    width: 20px;
                }
                QComboBox::down-arrow {
                    image: none;
                    border-left: 5px solid transparent;
                    border-right: 5px solid transparent;
                    border-top: 5px solid #2196F3;
                    margin-right: 5px;
                }
                QComboBox QAbstractItemView {
                    background: #2a2a2a;
                    border: 1px solid #555;
                    selection-background-color: #2196F3;
                    padding: 5px;
                }
            """)
            
            # Добавляем варианты
            base_args_options = [
                ("💚 ОЧЕНЬ аккуратный режим (лайтовый) --wf-raw=@windivert.discord_media+stun+sites.txt", "windivert-discord-media-stun-sites", 
                 "Используется самая элегантная --wf-raw=@windivert.discord_media+stun+sites.txt фильтрация с указанием портов.\nМожет работать лучше на некоторых провайдерах."),
                ("💚 Аккуратный режим (базовый) --wf-l3=ipv4,ipv6 --wf-tcp=80,443,2053,2083,2087,2096,8080,8443 --wf-udp=443,1400,19294-19344,50000-50100", "wf-l3", 
                 "Использует L3 фильтрацию с указанием портов.\nМожет работать лучше на некоторых провайдерах."),
                ("💯 Умный режим (все порты) --wf-raw=@windivert.all.txt", "windivert_all", 
                 "Использует файл wf-raw для фильтрации.\nБьёт по всем портам (может нарушать работу игр, однако старается делать это быстро)."),
                ("💥 Агрессивный режим (все порты) --wf-l3=ipv4,ipv6 --wf-tcp=80,443,444-65535 --wf-udp=443,444-65535", "wf-l3-all", 
                 "Использует медленную L3 фильтрацию чтобы гарантированно покрыть 100% всех портов и игр. Сильно нагружает систему, но может помочь для некоторых игр")
            ]
            
            for display_name, value, tooltip in base_args_options:
                self.base_args_combo.addItem(display_name, value)
                index = self.base_args_combo.count() - 1
                self.base_args_combo.setItemData(index, tooltip, Qt.ItemDataRole.ToolTipRole)
            
            # Загружаем сохраненное значение
            from strategy_menu import get_base_args_selection
            current_selection = get_base_args_selection()
            index = self.base_args_combo.findData(current_selection)
            if index >= 0:
                self.base_args_combo.setCurrentIndex(index)
            
            # Подключаем обработчик изменения
            self.base_args_combo.currentIndexChanged.connect(self._on_base_args_changed)
            
            base_args_layout.addWidget(self.base_args_combo)
            
            base_args_info = QLabel("Определяет метод перехвата и фильтрации трафика")
            base_args_info.setWordWrap(True)
            base_args_info.setStyleSheet("padding-left: 5px; color: #aaa; font-size: 8pt; margin-top: 3px;")
            base_args_layout.addWidget(base_args_info)
            
            params_layout.addWidget(base_args_widget)
            params_layout.addWidget(self._create_separator())

        if self.is_direct_mode:
            # ✅ ПАРАМЕТР 1: Применить ко всем сайтам (удалить --hostlist)
            remove_hostlists_widget = QWidget()
            remove_hostlists_layout = QVBoxLayout(remove_hostlists_widget)
            remove_hostlists_layout.setContentsMargins(0, 0, 0, 0)
            remove_hostlists_layout.setSpacing(3)

            from strategy_menu import get_remove_hostlists_enabled
            self.remove_hostlists_checkbox = QCheckBox("🌐 Применить запрет ко ВСЕМ сайтам (игнорировать hostlist)")
            self.remove_hostlists_checkbox.setToolTip(
                "Удаляет все упоминания --hostlist, --hostlist-domains и --hostlist-exclude из стратегий.\n"
                "Zapret будет применяться ко ВСЕМ доменам без исключений.\n"
                "⚠️ ВНИМАНИЕ: Может снизить скорость интернета!\n"
                "Используйте только если фильтрация по конкретным сайтам не работает."
            )
            self.remove_hostlists_checkbox.setStyleSheet("font-weight: bold; color: #ff9966;")
            self.remove_hostlists_checkbox.setChecked(get_remove_hostlists_enabled())
            self.remove_hostlists_checkbox.stateChanged.connect(self._on_remove_hostlists_changed)
            remove_hostlists_layout.addWidget(self.remove_hostlists_checkbox)

            remove_hostlists_info = QLabel("⚠️ Удаляет фильтры доменов, применяя стратегию ко всему HTTP/HTTPS трафику")
            remove_hostlists_info.setWordWrap(True)
            remove_hostlists_info.setStyleSheet("padding-left: 20px; color: #ff9966; font-size: 8pt;")
            remove_hostlists_layout.addWidget(remove_hostlists_info)

            params_layout.addWidget(remove_hostlists_widget)
            params_layout.addWidget(self._create_separator())

            # ✅ ПАРАМЕТР 2: Применить ко всем IP-адресам (удалить --ipset)
            remove_ipsets_widget = QWidget()
            remove_ipsets_layout = QVBoxLayout(remove_ipsets_widget)
            remove_ipsets_layout.setContentsMargins(0, 0, 0, 0)
            remove_ipsets_layout.setSpacing(3)

            from strategy_menu import get_remove_ipsets_enabled
            self.remove_ipsets_checkbox = QCheckBox("🔢 Применить запрет ко ВСЕМ IP-адресам (игнорировать ipset)")
            self.remove_ipsets_checkbox.setToolTip(
                "Удаляет все упоминания --ipset, --ipset-ip и --ipset-exclude из стратегий.\n"
                "Zapret будет применяться ко ВСЕМ IP-адресам без исключений.\n"
                "⚠️ ВНИМАНИЕ: Может сильно снизить скорость интернета!\n"
                "Используйте только если фильтрация по конкретным IP не работает."
            )
            self.remove_ipsets_checkbox.setStyleSheet("font-weight: bold; color: #ff6b6b;")
            self.remove_ipsets_checkbox.setChecked(get_remove_ipsets_enabled())
            self.remove_ipsets_checkbox.stateChanged.connect(self._on_remove_ipsets_changed)
            remove_ipsets_layout.addWidget(self.remove_ipsets_checkbox)

            remove_ipsets_info = QLabel("⚠️ Удаляет фильтры IP-адресов, применяя стратегию ко всему трафику")
            remove_ipsets_info.setWordWrap(True)
            remove_ipsets_info.setStyleSheet("padding-left: 20px; color: #ff6b6b; font-size: 8pt;")
            remove_ipsets_layout.addWidget(remove_ipsets_info)

            params_layout.addWidget(remove_ipsets_widget)
            params_layout.addWidget(self._create_separator())

            # ALLZONE
            allzone_widget = QWidget()
            allzone_layout = QVBoxLayout(allzone_widget)
            allzone_layout.setContentsMargins(0, 0, 0, 0)
            allzone_layout.setSpacing(3)

            from strategy_menu import get_allzone_hostlist_enabled
            self.allzone_checkbox = QCheckBox("Применять Zapret ко ВСЕМ сайтам")
            self.allzone_checkbox.setToolTip(
                "Заменяет хостлист other.txt на allzone.txt во всех стратегиях.\n"
                "allzone.txt содержит более полный список доменов.\n"
                "Может увеличить нагрузку на систему."
            )
            self.allzone_checkbox.setStyleSheet("font-weight: bold; color: #2196F3;")
            self.allzone_checkbox.setChecked(get_allzone_hostlist_enabled())
            self.allzone_checkbox.stateChanged.connect(self._on_allzone_changed)
            allzone_layout.addWidget(self.allzone_checkbox)

            allzone_info = QLabel("Использует расширенный список доменов allzone.txt вместо other.txt")
            allzone_info.setWordWrap(True)
            allzone_info.setStyleSheet("padding-left: 20px; color: #aaa; font-size: 8pt;")
            allzone_layout.addWidget(allzone_info)

            params_layout.addWidget(allzone_widget)
            params_layout.addWidget(self._create_separator())

            # wssize
            wssize_widget = QWidget()
            wssize_layout = QVBoxLayout(wssize_widget)
            wssize_layout.setContentsMargins(0, 0, 0, 0)
            wssize_layout.setSpacing(3)

            from strategy_menu import get_wssize_enabled
            self.wssize_checkbox = QCheckBox("Изменить размер окна интернета wssize (МОЖЕТ УМЕНЬШИТЬ СКОРОСТЬ!)")
            self.wssize_checkbox.setToolTip(
                "Включает параметр --wssize 1:6 для всех TCP соединений на порту 443.\n"
                "Может улучшить обход блокировок на некоторых провайдерах.\n"
                "Влияет на размер окна TCP сегментов."
            )
            self.wssize_checkbox.setStyleSheet("font-weight: bold; color: #fc7979;")
            self.wssize_checkbox.setChecked(get_wssize_enabled())
            self.wssize_checkbox.stateChanged.connect(self._on_wssize_changed)
            wssize_layout.addWidget(self.wssize_checkbox)

            wssize_info = QLabel("Изменяет размер TCP окна для порта 443, может помочь обойти DPI фильтрацию")
            wssize_info.setWordWrap(True)
            wssize_info.setStyleSheet("padding-left: 20px; color: #aaa; font-size: 8pt;")
            wssize_layout.addWidget(wssize_info)

            params_layout.addWidget(wssize_widget)

            params_layout.addSpacing(10)
            future_params_label = QLabel("Другие параметры будут добавлены в следующих версиях")
            future_params_label.setStyleSheet("color: #666; font-style: italic; padding: 5px; font-size: 8pt;")
            future_params_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            params_layout.addWidget(future_params_label)

        layout.addWidget(params_group)

    def _create_separator(self):
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        separator.setStyleSheet("QFrame { background-color: #444; max-height: 1px; margin: 5px 0; }")
        return separator

    def _on_remove_hostlists_changed(self, state):
        """Обработчик изменения настройки 'применить ко всем сайтам'"""
        from strategy_menu import set_remove_hostlists_enabled
        enabled = (state == Qt.CheckState.Checked.value)
        set_remove_hostlists_enabled(enabled)
        log(f"Настройка 'применить ко всем сайтам' {'включена' if enabled else 'выключена'}", "INFO")
        
        # Показываем предупреждение при включении
        if enabled:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self,
                "Внимание!",
                "Вы включили режим 'применить ко всем сайтам'.\n\n"
                "Это означает что Zapret будет обрабатывать ВЕСЬ HTTP/HTTPS трафик без фильтрации по доменам,\n"
                "что может снизить скорость интернета.\n\n"
                "Используйте эту опцию только если фильтрация по конкретным сайтам не работает."
            )

    def _on_remove_ipsets_changed(self, state):
        """Обработчик изменения настройки 'применить ко всем IP-адресам'"""
        from strategy_menu import set_remove_ipsets_enabled
        enabled = (state == Qt.CheckState.Checked.value)
        set_remove_ipsets_enabled(enabled)
        log(f"Настройка 'применить ко всем IP-адресам' {'включена' if enabled else 'выключена'}", "INFO")
        
        # Показываем предупреждение при включении
        if enabled:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self,
                "Внимание!",
                "Вы включили режим 'применить ко всем IP-адресам'.\n\n"
                "Это означает что Zapret будет обрабатывать ВЕСЬ трафик без фильтрации по IP,\n"
                "что может СИЛЬНО снизить скорость интернета.\n\n"
                "Используйте эту опцию только если фильтрация по конкретным IP не работает."
            )

    def _on_allzone_changed(self, state):
        from strategy_menu import set_allzone_hostlist_enabled
        enabled = (state == Qt.CheckState.Checked.value)
        set_allzone_hostlist_enabled(enabled)
        log(f"Замена other.txt на allzone.txt {'включена' if enabled else 'выключена'}", "INFO")

    def _on_base_args_changed(self, index):
        """Обработчик изменения базовых аргументов"""
        from strategy_menu import set_base_args_selection
        value = self.base_args_combo.itemData(index)
        if value:
            set_base_args_selection(value)
            log(f"Базовые аргументы изменены на: {value}", "INFO")
            
            if hasattr(self, 'update_combined_preview'):
                self.update_combined_preview()
                
    def _on_tab_changed(self, index):
        try:
            if index == 0:  # Стратегии
                self.buttons_widget.setVisible(True)
                if self.is_direct_mode:
                    self.select_button.setEnabled(True)
            elif index == 1:  # Хостлисты
                self.buttons_widget.setVisible(False)
            elif index == 2:  # Настройки
                self.buttons_widget.setVisible(False)
        except Exception as e:
            log(f"Ошибка в _on_tab_changed: {e}", "❌ ERROR")

    def _on_method_changed(self, button):
        from strategy_menu import set_strategy_launch_method
        old_method = self.launch_method

        if button == self.direct_method_radio:
            set_strategy_launch_method("direct")
            new_method = "direct"
        else:
            set_strategy_launch_method("bat")
            new_method = "bat"

        if old_method != new_method:
            log(f"Переключение с {old_method} на {new_method}...", "INFO")

            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Icon.Information)
            msg.setWindowTitle("Смена метода запуска")
            msg.setText("Метод запуска изменен!")
            msg.setInformativeText("Диалог будет перезапущен для применения изменений.")
            msg.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg.exec()

            self._schedule_dialog_restart()

    def _schedule_dialog_restart(self):
        """Перезапуск диалога при смене метода"""
        StrategySelector._is_initialized = False
        StrategySelector._instance = None
        
        parent_window = self.parent()
        
        try:
            self.strategySelected.disconnect()
        except:
            pass
        super().close()
        
        def restart_dialog():
            if parent_window and hasattr(parent_window, 'force_reload_strategy_dialog'):
                parent_window.force_reload_strategy_dialog()
                parent_window._show_strategy_dialog()

        QTimer.singleShot(100, restart_dialog)

    def _on_wssize_changed(self, state):
        from strategy_menu import set_wssize_enabled
        enabled = (state == Qt.CheckState.Checked.value)
        set_wssize_enabled(enabled)
        log(f"Параметр --wssize 1:6 {'включен' if enabled else 'выключен'}", "INFO")

    def _on_keep_dialog_open_changed(self, state):
        """Обработчик изменения настройки сохранения окна открытым"""
        from strategy_menu import set_keep_dialog_open
        enabled = (state == Qt.CheckState.Checked.value)
        set_keep_dialog_open(enabled)
        log(f"Настройка 'не закрывать окно' {'включена' if enabled else 'выключена'}", "INFO")
        
        if hasattr(self, 'select_button'):
            if enabled:
                self.select_button.setText("✅ Применить")
            else:
                self.select_button.setText("✅ Выбрать")

    def _on_pin_tabs_changed(self, state):
        """Обработчик изменения закрепления табов"""
        from strategy_menu import set_tabs_pinned
        enabled = (state == Qt.CheckState.Checked.value)
        set_tabs_pinned(enabled)

        if hasattr(self, 'category_tabs'):
            self.category_tabs.is_pinned = enabled

            if enabled:
                self.category_tabs.is_expanded = True
                self.category_tabs._set_bar_width(self.category_tabs.expanded_width)
                self.category_tabs.show_full_names()
            else:
                if not self.category_tabs.tabBar().underMouse():
                    self.category_tabs.is_expanded = False
                    self.category_tabs._set_bar_width(self.category_tabs.collapsed_width)
                    self.category_tabs.show_short_names()

        log(f"Закрепление табов {'включено' if enabled else 'выключено'}", "INFO")

    def _on_table_strategy_selected(self, strategy_id, strategy_name):
        self.selected_strategy_id = strategy_id
        self.selected_strategy_name = strategy_name
        self.select_button.setEnabled(True)
        log(f"Выбрана стратегия: {strategy_name}", "DEBUG")

    def _on_table_strategy_double_clicked(self, strategy_id, strategy_name):
        self.selected_strategy_id = strategy_id
        self.selected_strategy_name = strategy_name
        self.accept()

    def on_category_selection_changed(self, category, strategy_id):
        """Обработчик изменения выбора стратегии в категории"""
        from strategy_menu import set_direct_strategy_selections

        self.category_selections[category] = strategy_id
        self.update_combined_preview()

        try:
            set_direct_strategy_selections(self.category_selections)
            log(f"Сохранена {category} стратегия: {strategy_id}", "DEBUG")
        except Exception as e:
            log(f"Ошибка сохранения {category} стратегии: {e}", "⚠ WARNING")

        self.select_button.setEnabled(True)

    def update_combined_preview(self):
        """Обновляет предпросмотр комбинированной стратегии"""
        if not hasattr(self, 'preview_text'):
            return

        from strategy_menu.strategy_lists_separated import combine_strategies
        combined = combine_strategies(**self.category_selections)

        from strategy_menu import is_favorite_strategy
        
        none_strategies = registry.get_none_strategies()
        category_colors = registry.get_category_colors_dict()

        def format_strategy(category_key):
            strategy_id = self.category_selections.get(category_key)
            none_id = none_strategies.get(category_key)
            
            if strategy_id and strategy_id != none_id:
                category_info = registry.get_category_info(category_key)
                if category_info:
                    star = "⭐ " if is_favorite_strategy(strategy_id, category_key) else ""
                    color = category_info.color
                    display_name = category_info.full_name.replace(category_info.emoji + ' ', '')
                    return f"{star}<span style='color: {color};'>{display_name}</span>"
            return None

        items = []
        for category_key in registry.get_all_category_keys():
            formatted = format_strategy(category_key)
            if formatted:
                items.append(formatted)

        if items:
            preview_html = f"<b>Активные:</b> {', '.join(items)}"
            args_count = len(combined['args'].split())
            preview_html += f"<br><span style='color: #888; font-size: 7pt;'>Аргументов: {args_count}</span>"
        else:
            preview_html = "<span style='color: #888;'>Нет активных стратегий</span>"

        self.preview_text.setHtml(f"""
            <style>
                body {{
                    margin: 2px;
                    font-family: Arial;
                    font-size: 8pt;
                    color: #ccc;
                }}
            </style>
            <body>{preview_html}</body>
        """)

    def load_builtin_strategies(self):
        """Загружает встроенные стратегии"""
        try:
            if hasattr(self, 'status_label'):
                self.status_label.setText("✅ Готово к выбору стратегий")
                self.status_label.setStyleSheet("font-weight: bold; color: #4CAF50; padding: 5px;")

            if self.is_direct_mode:
                self.select_button.setEnabled(True)

            log("Встроенные стратегии готовы", "INFO")

        except Exception as e:
            log(f"Ошибка загрузки встроенных стратегий: {e}", "❌ ERROR")

    def load_local_strategies(self):
        """Загружает локальные стратегии (для bat режима)"""
        try:
            if hasattr(self, 'strategy_table'):
                self.strategy_table.set_progress_visible(True)
                self.strategy_table.set_status("📂 Загрузка локальных стратегий...", "info")

            strategies = self.strategy_manager.get_local_strategies_only()

            if strategies and hasattr(self, 'strategy_table'):
                self.strategy_table.populate_strategies(strategies)
                self.strategy_table.set_progress_visible(False)

                if self.current_strategy_name:
                    self.strategy_table.select_strategy_by_name(self.current_strategy_name)

                log(f"Загружено {len(strategies)} локальных стратегий", "INFO")
            else:
                self.strategy_table.set_status(
                    "⚠️ Локальные стратегии не найдены. Нажмите 'Обновить'",
                    "warning"
                )
                self.strategy_table.set_progress_visible(False)

        except Exception as e:
            log(f"Ошибка загрузки локальных стратегий: {e}", "❌ ERROR")
            if hasattr(self, 'strategy_table'):
                self.strategy_table.set_status(f"❌ Ошибка: {e}", "error")
                self.strategy_table.set_progress_visible(False)

    def refresh_strategies(self):
        """Обновляет список стратегий из интернета"""
        if self.is_loading_strategies:
            QMessageBox.information(self, "Обновление в процессе",
                                    "Обновление уже выполняется")
            return

        if self.is_direct_mode:
            self.load_builtin_strategies()
            return

        self.is_loading_strategies = True

        self.strategy_table.set_status("🌐 Загрузка стратегий из интернета...", "info")
        self.strategy_table.set_progress_visible(True)
        self.strategy_table.refresh_button.setEnabled(False)
        self.strategy_table.download_all_button.setEnabled(False)

        self.loader_thread = QThread()
        self.loader_worker = InternetStrategyLoader(self.strategy_manager)
        self.loader_worker.moveToThread(self.loader_thread)

        self.loader_thread.started.connect(self.loader_worker.run)
        self.loader_worker.progress.connect(
            lambda msg: self.strategy_table.set_status(f"🔄 {msg}", "info")
        )
        self.loader_worker.finished.connect(self._on_strategies_loaded)
        self.loader_worker.finished.connect(self.loader_thread.quit)
        self.loader_worker.finished.connect(self.loader_worker.deleteLater)
        self.loader_thread.finished.connect(self.loader_thread.deleteLater)

        self.loader_thread.start()
        log("Запуск загрузки стратегий из интернета", "INFO")

    def _on_strategies_loaded(self, strategies, error_message):
        """Обработчик завершения загрузки стратегий"""
        self.is_loading_strategies = False

        self.strategy_table.set_progress_visible(False)
        self.strategy_table.refresh_button.setEnabled(True)
        self.strategy_table.download_all_button.setEnabled(True)

        if error_message:
            self.strategy_table.set_status(f"❌ {error_message}", "error")
            return

        if not strategies:
            self.strategy_table.set_status("⚠️ Список стратегий пуст", "warning")
            return

        self.strategy_table.populate_strategies(strategies)

        if self.current_strategy_name:
            self.strategy_table.select_strategy_by_name(self.current_strategy_name)

        log(f"Загружено {len(strategies)} стратегий", "INFO")

    def accept(self):
        """Применяет выбранную стратегию"""
        if self.is_direct_mode:
            from .strategy_lists_separated import combine_strategies
            from strategy_menu import get_default_selections
            if not self.category_selections:
                self.category_selections = get_default_selections()

            combined = combine_strategies(**self.category_selections)

            self._combined_args = combined['args']
            self._combined_strategy_data = {
                'is_combined': True,
                'name': combined['description'],
                'args': combined['args'],
                'selections': self.category_selections
            }
            self.selected_strategy_id = "COMBINED_DIRECT"
            self.selected_strategy_name = combined['description']

            log(f"Выбрана комбинированная стратегия: {self.selected_strategy_name}", "INFO")
            log(f"Сохранены аргументы: {len(self._combined_args)} символов", "DEBUG")
            log(f"Выборы категорий: {self.category_selections}", "DEBUG")

        else:
            if not self.selected_strategy_id or not self.selected_strategy_name:
                QMessageBox.warning(self, "Выбор стратегии",
                                    "Пожалуйста, выберите стратегию из списка")
                return

            self._combined_args = None
            self._combined_strategy_data = None

            log(f"Выбрана стратегия: {self.selected_strategy_name}", "INFO")

        # Испускаем сигнал о выборе
        self.strategySelected.emit(self.selected_strategy_id, self.selected_strategy_name)
        
        # Проверяем настройку: Закрывать ли окно?
        from strategy_menu import get_keep_dialog_open
        if not get_keep_dialog_open():
            # Закрываем окно (скрываем)
            self.hide()
            log("Диалог закрыт после выбора", "DEBUG")
        else:
            # Оставляем окно открытым
            log("Диалог остается открытым после выбора", "DEBUG")
            
            # Показываем временное уведомление
            if hasattr(self, 'status_label'):
                self.status_label.setText("✅ Стратегия применена! Окно осталось открытым")
                self.status_label.setStyleSheet("font-weight: bold; color: #4CAF50; font-size: 9pt; padding: 3px;")
                
                # Через 3 секунды возвращаем стандартный статус
                QTimer.singleShot(3000, lambda: self.status_label.setText("✅ Готово к выбору"))

    def _update_current_selection(self):
        """Обновляет текущий выбор без полной перезагрузки"""
        if self.is_direct_mode:
            if hasattr(self, 'update_combined_preview'):
                self.update_combined_preview()
        else:
            if hasattr(self, 'strategy_table') and self.current_strategy_name:
                self.strategy_table.select_strategy_by_name(self.current_strategy_name)

    def reject(self):
        """Переопределяем закрытие - просто скрываем вместо уничтожения"""
        self.hide()
        log("Диалог выбора стратегии скрыт", "INFO")

    def closeEvent(self, event):
        """Переопределяем событие закрытия"""
        # Останавливаем потоки если есть
        try:
            if hasattr(self, 'loader_thread') and self.loader_thread:
                if self.loader_thread.isRunning():
                    self.loader_thread.quit()
                    if not self.loader_thread.wait(2000):
                        self.loader_thread.terminate()
                        self.loader_thread.wait(1000)
        except RuntimeError:
            pass

        # Скрываем вместо полного закрытия
        event.ignore()
        self.hide()