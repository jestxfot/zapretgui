# strategy_menu/selector.py

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                            QWidget, QTabWidget, QTabBar, QLabel, QMessageBox, QGroupBox,
                            QTextBrowser, QSizePolicy, QFrame, QScrollArea, 
                            QRadioButton, QButtonGroup, QCheckBox, QProgressBar,
                            QTextEdit)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QTimer, QSize, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QFont, QTextCursor, QPainter, QTextOption, QTextOption, QPen, QCursor, QColor

from log import log
from strategy_menu import get_strategy_launch_method

from .constants import MINIMUM_WIDTH, MINIMIM_HEIGHT
from .widgets import CompactStrategyItem
from .strategy_table_widget_favorites import StrategyTableWithFavoritesFilter as StrategyTableWidget
from .workers import InternetStrategyLoader
from .command_line_dialog import show_command_line_dialog

class HorizontalTextTabBar(QTabBar):
    """TabBar с горизонтальным текстом для вертикальных табов"""
    
    def __init__(self):
        super().__init__()
        self.setDrawBase(False)
    
    def tabSizeHint(self, index):
        """Возвращает размер таба"""
        size = super().tabSizeHint(index)
        # Меняем местами ширину и высоту для горизонтального текста
        return QSize(size.height(), 35)  # Убрали +20
    
    def paintEvent(self, event):
        """Рисуем табы с горизонтальным текстом"""
        painter = QPainter(self)
        
        for index in range(self.count()):
            rect = self.tabRect(index)
            
            # Определяем стиль таба
            is_selected = index == self.currentIndex()
            is_hovered = rect.contains(self.mapFromGlobal(QCursor.pos()))
            
            # Фон таба
            if is_selected:
                painter.fillRect(rect, QColor("#3a3a3a"))
                # Правая граница для выбранного таба
                painter.setPen(QPen(QColor("#2196F3"), 2))
                painter.drawLine(rect.right() - 1, rect.top(), rect.right() - 1, rect.bottom())
            elif is_hovered:
                painter.fillRect(rect, QColor("#333"))
                # Правая граница при наведении
                painter.setPen(QPen(QColor("#2196F3"), 2))
                painter.drawLine(rect.right() - 1, rect.top(), rect.right() - 1, rect.bottom())
            else:
                painter.fillRect(rect, QColor("#2a2a2a"))
            
            # Рамка таба
            painter.setPen(QPen(QColor("#444"), 1))
            painter.drawRect(rect.adjusted(0, 0, -1, -1))
            
            # Текст
            text = self.tabText(index)
            text_color = QColor("#2196F3") if is_selected else (QColor("#fff") if is_hovered else QColor("#aaa"))
            painter.setPen(text_color)
            
            font = painter.font()
            if is_selected:
                font.setBold(True)
            font.setPointSize(8)  # Уменьшили с 9
            painter.setFont(font)
            
            # Рисуем текст горизонтально с меньшими отступами
            text_rect = rect.adjusted(5, 3, -3, -3)  # Уменьшены отступы
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, text)
        
        painter.end()


class AnimatedTabWidget(QTabWidget):
    """TabWidget с анимированными табами"""
    
    def __init__(self):
        super().__init__()
        self.custom_tab_bar = HorizontalTextTabBar()
        self.setTabBar(self.custom_tab_bar)
        self.collapsed_width = 45  # Было 60
        self.expanded_width = 160  # Было 220
        self.is_expanded = False
        
        # Анимация для tabBar
        from PyQt6.QtCore import QPropertyAnimation, QEasingCurve
        self.tab_animation = QPropertyAnimation(self.custom_tab_bar, b"minimumWidth")
        self.tab_animation.setDuration(200)
        self.tab_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        
        # Устанавливаем начальную ширину
        self.custom_tab_bar.setMinimumWidth(self.collapsed_width)
        self.custom_tab_bar.setMaximumWidth(self.collapsed_width)

class StrategySelector(QDialog):
    """Диалог для выбора стратегии обхода блокировок"""
    
    strategySelected = pyqtSignal(str, str)  # (strategy_id, strategy_name)
    
    def __init__(self, parent=None, strategy_manager=None, current_strategy_name=None):
        super().__init__(parent)

        # Устанавливаем стиль для tooltip
        self.setStyleSheet("""
            QToolTip {
                background-color: #2a2a2a;
                color: white;
                border: 1px solid #2196F3;
                padding: 8px;
                font-size: 10pt;
                border-radius: 4px;
            }
        """)
        
        self.strategy_manager = strategy_manager
        self.current_strategy_name = current_strategy_name
        self.selected_strategy_id = None
        self.selected_strategy_name = None
        
        # Инициализируем атрибуты для комбинированных стратегий
        self._combined_args = None
        self._combined_strategy_data = None
        self.category_selections = {}
        
        # НОВОЕ: Для асинхронной загрузки Direct режима
        self._category_widgets_cache = {}  # Кэш созданных виджетов категорий (если нужен)
        self._loading_in_progress = False
        self._categories_loaded = set()  # Множество загруженных категорий
        
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
        
        # ИЗМЕНЕНИЕ: Для Direct режима запускаем асинхронную загрузку после показа UI
        if self.is_direct_mode:
            QTimer.singleShot(10, self._async_load_builtin_strategies)
        else:
            self.load_local_strategies()

    def _init_direct_mode_ui(self, layout):
        """Инициализирует интерфейс для прямого режима"""
        from strategy_menu import get_direct_strategy_selections
        from .strategy_lists_separated import get_default_selections
        
        # Загружаем сохраненные выборы
        try:
            self.category_selections = get_direct_strategy_selections()
        except Exception as e:
            log(f"Ошибка загрузки выборов: {e}", "⚠ WARNING")
            self.category_selections = get_default_selections()
        
        # Заголовок
        title = QLabel("Выберите стратегию для каждого типа трафика чтобы собрать пресет")
        title.setStyleSheet("font-weight: bold; font-size: 10pt; color: #2196F3; margin: 5px;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # НОВОЕ: Прогресс бар для загрузки
        self.loading_progress = QProgressBar()
        self.loading_progress.setFixedHeight(3)
        self.loading_progress.setTextVisible(False)
        self.loading_progress.setStyleSheet("""
            QProgressBar {
                border: none;
                background: #2a2a2a;
            }
            QProgressBar::chunk {
                background: #2196F3;
            }
        """)
        self.loading_progress.setVisible(False)
        layout.addWidget(self.loading_progress)
        
        # ИЗМЕНЕНО: Используем кастомный TabWidget
        self.category_tabs = AnimatedTabWidget()
        self.category_tabs.setTabPosition(QTabWidget.TabPosition.West)
        self.category_tabs.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        # Стиль для содержимого табов
        self.category_tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #444;
                background: #2a2a2a;
                border-radius: 5px;
                margin-left: -1px;  /* Прижимаем к табам */
                margin-right: 0px;  /* Убираем правый отступ */
            }
        """)
        
        # Подключаем обработчик для анимации
        self.category_tabs.tabBar().installEventFilter(self)
        
        # Сохраняем информацию для отложенной загрузки
        self.category_tabs.currentChanged.connect(self._save_last_tab_index)
        self._pending_categories = []
        self._categories_loaded = set()
        
        # Получаем подсказки
        self.tab_tooltips = self._get_tab_tooltips()
        
        # Сохраняем короткие и полные названия табов
        self.tab_names = {
            'youtube': ("🎬", "🎬 YouTube TCP"),
            'youtube_udp': ("📺", "📺 YouTube QUIC"),  # Изменена иконка
            'googlevideo_tcp': ("📹", "📹 GoogleVideo"),
            'discord': ("💬", "💬 Discord"),
            'discord_voice': ("🔊", "🔊 Discord Voice"),
            'other': ("🌐", "🌐 Hostlist"),
            'ipset': ("🔢", "🔢 IPset TCP"),
            'ipset_udp': ("🎮", "🎮 Games UDP"),
        }
        
        # Добавляем заглушки с короткими названиями
        tab_data = [
            ('youtube',),
            ('youtube_udp',),
            ('googlevideo_tcp',),
            ('discord',),
            ('discord_voice',),
            ('other',),
            ('ipset',),
            ('ipset_udp',),
        ]
        
        for category_key, in tab_data:
            short_name, _ = self.tab_names[category_key]
            self._add_category_tab(short_name, None, category_key)
            # Устанавливаем tooltip сразу после добавления вкладки
            tab_index = self.category_tabs.count() - 1
            if category_key in self.tab_tooltips:
                self.category_tabs.setTabToolTip(tab_index, self.tab_tooltips[category_key])
        
        layout.addWidget(self.category_tabs, 1)
        
        # Предпросмотр
        self._create_preview_widget(layout)
        
        # Статус
        self.status_label = QLabel("⏳ Загрузка стратегий...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("font-weight: bold; color: #ffa500; font-size: 9pt; padding: 3px;")
        self.status_label.setFixedHeight(25)
        layout.addWidget(self.status_label)
        
        self.select_button.setEnabled(False)

    def eventFilter(self, obj, event):
        """Обработчик событий для анимации табов"""
        from PyQt6.QtCore import QEvent
        
        if obj == self.category_tabs.tabBar() and self.is_direct_mode:
            if event.type() == QEvent.Type.HoverEnter:
                # При наведении расширяем табы и показываем полные названия
                if not self.category_tabs.is_expanded:
                    self._expand_all_tabs()
                    # Анимация расширения
                    self.category_tabs.tab_animation.setStartValue(self.category_tabs.collapsed_width)
                    self.category_tabs.tab_animation.setEndValue(self.category_tabs.expanded_width)
                    self.category_tabs.tab_animation.finished.connect(
                        lambda: self.category_tabs.custom_tab_bar.setMaximumWidth(self.category_tabs.expanded_width)
                    )
                    self.category_tabs.tab_animation.start()
                    self.category_tabs.is_expanded = True
                    
            elif event.type() == QEvent.Type.HoverLeave:
                # При уходе сворачиваем табы
                if self.category_tabs.is_expanded:
                    self._collapse_all_tabs()
                    # Анимация сворачивания
                    self.category_tabs.tab_animation.setStartValue(self.category_tabs.expanded_width)
                    self.category_tabs.tab_animation.setEndValue(self.category_tabs.collapsed_width)
                    self.category_tabs.tab_animation.finished.connect(
                        lambda: self.category_tabs.custom_tab_bar.setMaximumWidth(self.category_tabs.collapsed_width)
                    )
                    self.category_tabs.tab_animation.start()
                    self.category_tabs.is_expanded = False
        
        return super().eventFilter(obj, event)

    def _expand_all_tabs(self):
        """Разворачивает ВСЕ табы при наведении"""
        category_keys = list(self.tab_names.keys())
        
        for i, category_key in enumerate(category_keys):
            if i < self.category_tabs.count():
                _, full_name = self.tab_names[category_key]
                self.category_tabs.setTabText(i, full_name)

    def _collapse_all_tabs(self):
        """Сворачивает ВСЕ табы при уходе мышки"""
        category_keys = list(self.tab_names.keys())
        
        for i, category_key in enumerate(category_keys):
            if i < self.category_tabs.count():
                short_name, _ = self.tab_names[category_key]
                self.category_tabs.setTabText(i, short_name)

    def _save_last_tab_index(self, index):
        """Сохраняет индекс последней открытой вкладки"""
        if self.is_direct_mode and not self._loading_in_progress and index >= 0:
            from strategy_menu import set_last_category_tab_index
            set_last_category_tab_index(index)
            log(f"Сохранен индекс вкладки: {index}", "DEBUG")

    def _load_next_category_async(self):
        """Загружает следующую категорию (переименован чтобы не конфликтовать)"""
        if self._load_index >= len(self._pending_categories):
            # Все загружено
            self._finalize_loading()
            return
        
        tab_name, category_key = self._pending_categories[self._load_index]
        
        # Импортируем стратегии только сейчас
        from .strategy_lists_separated import (
            YOUTUBE_STRATEGIES, YOUTUBE_QUIC_STRATEGIES, GOOGLEVIDEO_STRATEGIES,
            DISCORD_STRATEGIES, DISCORD_VOICE_STRATEGIES, IPSET_TCP_STRATEGIES, IPSET_UDP_STRATEGIES
        )

        from .OTHER_STRATEGIES import OTHER_STRATEGIES
        
        strategies_map = {
            'youtube': YOUTUBE_STRATEGIES,
            'youtube_udp': YOUTUBE_QUIC_STRATEGIES,
            'googlevideo_tcp': GOOGLEVIDEO_STRATEGIES,
            'discord': DISCORD_STRATEGIES,
            'discord_voice': DISCORD_VOICE_STRATEGIES,
            'other': OTHER_STRATEGIES,
            'ipset': IPSET_TCP_STRATEGIES,
            'ipset_udp': IPSET_UDP_STRATEGIES
        }
        
        strategies = strategies_map.get(category_key, {})
        
        # Заменяем заглушку на реальную вкладку
        self._add_category_tab(tab_name, strategies, category_key)
        
        # Обновляем прогресс
        if hasattr(self, 'loading_progress'):
            self.loading_progress.setValue(self._load_index + 1)
        
        self._load_index += 1
        
        # Планируем загрузку следующей
        QTimer.singleShot(20, self._load_next_category_async)

    def _get_tab_tooltips(self):
        """Возвращает словарь с подсказками для вкладок"""
        return {
            'youtube': """🎬 YouTube через TCP протокол (порты 80, 443)
    Обходит блокировку обычного YouTube трафика через стандартные веб-порты.
    TCP - это надежный протокол передачи данных, используется для загрузки веб-страниц и видео.
    Работает с youtube.com и youtu.be.""",
            
            'youtube_udp': """🎬 YouTube через QUIC/UDP протокол (порт 443)
    Обходит блокировку YouTube при использовании современного протокола QUIC (HTTP/3).
    QUIC работает поверх UDP и обеспечивает более быструю загрузку видео.
    Многие браузеры автоматически используют QUIC для YouTube.""",
            
            'googlevideo_tcp': """🎬 YouTube видео с CDN серверов GoogleVideo
    Обходит блокировку видеопотоков с серверов *.googlevideo.com (порт 443).
    Это серверы доставки контента (CDN), откуда загружаются сами видеофайлы YouTube.
    Нужно включать если видео не загружаются при работающем основном YouTube.""",
            
            'discord': """💬 Discord мессенджер (порты 80, 443)
    Обходит блокировку текстовых чатов и загрузки файлов в Discord.
    Работает с основным трафиком Discord через TCP протокол.
    Включите если не работают текстовые сообщения и картинки.""",
            
            'discord_voice': """🔊 Discord голосовые звонки (UDP порты)
    Обходит блокировку голосовой связи и видеозвонков в Discord.
    Использует UDP протокол для передачи голоса в реальном времени.
    Включите если не работают голосовые каналы и звонки.""",
            
            'other': """🌐 Заблокированные сайты из списка (порты 80, 443)
    Обходит блокировку сайтов из файла other.txt через TCP.
    Включает сотни популярных заблокированных сайтов и сервисов.
    Можно редактировать список сайтов во вкладке Hostlist.""",
            
            'ipset': """🔢 Блокировка по IP адресам (порты 80, 443)
    Обходит блокировку сервисов по их IP адресам через TCP.
    Работает когда провайдер блокирует не домены, а конкретные IP.
    Полезно для сервисов с фиксированными IP адресами.""",

            'ipset_udp': """🔢 Блокировка по IP адресам (UDP для игр)
    Обходит блокировку сервисов по их IP адресам через UDP.
    Работает когда провайдер блокирует не домены, а конкретные IP.
    Полезно для сервисов с фиксированными IP адресами.""",
        }

    def _async_load_builtin_strategies(self):
        """Асинхронно загружает встроенные стратегии"""
        log("Начало асинхронной загрузки стратегий Direct режима", "DEBUG")
        
        self._loading_in_progress = True
        
        if hasattr(self, 'loading_progress'):
            self.loading_progress.setVisible(True)
            self.loading_progress.setRange(0, len(self._pending_categories))
            self.loading_progress.setValue(0)
        
        # Начинаем загрузку
        self._load_index = 0
        QTimer.singleShot(1, self._load_next_category_async)

    def _finalize_loading(self):
        """Завершает процесс загрузки"""
        self._loading_in_progress = False
        
        if hasattr(self, 'loading_progress'):
            self.loading_progress.setVisible(False)
        
        # Обновляем статус
        self.status_label.setText("✅ Готово к выбору")
        self.status_label.setStyleSheet("font-weight: bold; color: #4CAF50; font-size: 9pt; padding: 3px;")
        
        # Включаем кнопку выбора
        self.select_button.setEnabled(True)
        
        # Восстанавливаем последнюю вкладку
        from strategy_menu import get_last_category_tab_index
        last_index = get_last_category_tab_index()
        if 0 <= last_index < self.category_tabs.count():
            self.category_tabs.setCurrentIndex(last_index)
            log(f"Восстановлен индекс вкладки: {last_index}", "DEBUG")
        
        # Обновляем предпросмотр
        self.update_combined_preview()
        
        log("Встроенные стратегии готовы", "INFO")

    def _add_category_tab(self, tab_name, strategies, category_key):
        """Добавляет вкладку категории (с заглушкой если strategies=None)"""
        
        # Если strategies=None, создаем заглушку
        if strategies is None:
            placeholder = QWidget()
            layout = QVBoxLayout(placeholder)
            layout.setContentsMargins(10, 10, 10, 10)
            
            loading_label = QLabel("⏳ Загрузка...")
            loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            loading_label.setStyleSheet("color: #888; font-style: italic; font-size: 10pt;")
            layout.addWidget(loading_label)
            layout.addStretch()
            
            # Добавляем вкладку и сохраняем её индекс
            tab_index = self.category_tabs.addTab(placeholder, tab_name)
            
            # Сохраняем для отложенной загрузки с правильным индексом
            self._pending_categories.append((tab_name, category_key))
            # Сохраняем соответствие категории и индекса
            if not hasattr(self, '_category_tab_indices'):
                self._category_tab_indices = {}
            self._category_tab_indices[category_key] = tab_index
            return
        
        # Иначе создаем полноценную вкладку
        tab_widget = QWidget()
        tab_layout = QVBoxLayout(tab_widget)
        tab_layout.setContentsMargins(10, 10, 10, 10)
        tab_layout.setSpacing(5)
        
        # Заголовок категории
        category_title = self._get_category_title(category_key)
        title_label = QLabel(category_title)
        title_label.setStyleSheet("font-weight: bold; font-size: 10pt; color: #2196F3; margin-bottom: 5px;")
        tab_layout.addWidget(title_label)
        
        # Счетчик избранных
        favorites_label = QLabel("")
        favorites_label.setStyleSheet("color: #ffd700; font-weight: bold; font-size: 8pt; margin: 2px;")
        favorites_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        tab_layout.addWidget(favorites_label)
        
        # Прокручиваемая область для стратегий
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollBar:vertical {
                width: 10px;
                background: #2a2a2a;
            }
            QScrollBar::handle:vertical {
                background: #555;
                border-radius: 5px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #666;
            }
        """)
        
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setContentsMargins(5, 5, 5, 5)
        scroll_layout.setSpacing(3)
        
        button_group = QButtonGroup()
        
        # Сортируем стратегии - избранные вверху
        sorted_strategies = self._sort_category_strategies(strategies)
        favorites_count = 0
        
        for idx, (strat_id, strat_data) in enumerate(sorted_strategies):
            from .widgets_favorites import FavoriteCompactStrategyItem
            strategy_item = FavoriteCompactStrategyItem(strat_id, strat_data)
            
            # Считаем избранные
            from strategy_menu import is_favorite_strategy
            if is_favorite_strategy(strat_id):
                favorites_count += 1
            
            if strat_id == self.category_selections.get(category_key):
                strategy_item.set_checked(True)
            
            strategy_item.clicked.connect(
                lambda sid, cat=category_key: self.on_category_selection_changed(cat, sid)
            )
            
            strategy_item.favoriteToggled.connect(
                lambda sid, is_fav: self._on_direct_favorite_toggled(sid, is_fav)
            )
            
            strategy_item.favoriteToggled.connect(
                lambda sid, is_fav, cat=category_key, fl=favorites_label: 
                self._on_category_favorite_toggled(cat, sid, is_fav, fl, scroll_widget)
            )
            
            button_group.addButton(strategy_item.radio, idx)
            scroll_layout.addWidget(strategy_item)
        
        # Обновляем счетчик избранных
        if favorites_count > 0:
            favorites_label.setText(f"⭐ {favorites_count}")
        
        setattr(self, f"{category_key}_button_group", button_group)
        setattr(self, f"{category_key}_favorites_label", favorites_label)
        
        scroll_layout.addStretch()
        scroll_area.setWidget(scroll_widget)
        tab_layout.addWidget(scroll_area)
        
        # Находим правильный индекс вкладки для замены
        if hasattr(self, '_category_tab_indices') and category_key in self._category_tab_indices:
            correct_index = self._category_tab_indices[category_key]
            if correct_index < self.category_tabs.count():
                self.category_tabs.removeTab(correct_index)
                self.category_tabs.insertTab(correct_index, tab_widget, tab_name)
                # Восстанавливаем tooltip после замены вкладки
                if hasattr(self, 'tab_tooltips') and category_key in self.tab_tooltips:
                    self.category_tabs.setTabToolTip(correct_index, self.tab_tooltips[category_key])
                # Обновляем индексы после вставки
                self._update_category_indices()

    def _update_category_indices(self):
        """Обновляет индексы категорий после изменения табов"""
        if hasattr(self, '_category_tab_indices'):
            category_keys = ['youtube', 'youtube_udp', 'googlevideo_tcp', 'discord', 
                            'discord_voice', 'other', 'ipset', 'ipset_udp']
            for i, key in enumerate(category_keys):
                if i < self.category_tabs.count():
                    self._category_tab_indices[key] = i
                
    def _get_category_title(self, category_key):
        """Возвращает полный заголовок для категории"""
        titles = {
            'youtube': "YouTube через TCP (порты 80, 443) - основной трафик www.youtube.com",
            'youtube_udp': "YouTube через QUIC/UDP (порт 443) - если включен QUIC в браузере",
            'googlevideo_tcp': "GoogleVideo CDN серверы - если не загружаются видео со стандартными стратегиями",
            'discord': "Discord мессенджер (TCP) - основной трафик discord.com",
            'discord_voice': "Discord голосовые звонки (UDP) - голосовые каналы и звонки",
            'other': "Заблокированные сайты из списка other.txt (TCP)",
            'ipset': "Блокировка по IP адресам (TCP) ipset-all.txt",
            'ipset_udp': "Блокировка по IP адресам (UDP/в основном игры) ipset-all.txt",
        }
        return titles.get(category_key, "Стратегии")

    def _on_direct_favorite_toggled(self, strategy_id, is_favorite):
        """Обработчик изменения избранного в Direct режиме"""
        action = "добавлена в" if is_favorite else "удалена из"
        log(f"Стратегия {strategy_id} {action} избранных", "INFO")
        
        # Обновляем статус
        self.status_label.setText(f"{'⭐ Добавлено в избранные' if is_favorite else '☆ Удалено из избранных'}")
        self.status_label.setStyleSheet("font-weight: bold; color: #ffd700; font-size: 9pt; padding: 3px;")
        
        # Сбрасываем статус через 2 секунды
        QTimer.singleShot(2000, lambda: self.status_label.setText("✅ Готово к выбору"))

    def _sort_category_strategies(self, strategies):
        """Сортирует стратегии категории: избранные вверху"""
        from strategy_menu import is_favorite_strategy
        
        # Разделяем на избранные и обычные
        favorites = []
        regular = []
        
        for strat_id, strat_data in strategies.items():
            if is_favorite_strategy(strat_id):
                favorites.append((strat_id, strat_data))
            else:
                regular.append((strat_id, strat_data))
        
        # Сортируем каждую группу по имени
        favorites.sort(key=lambda x: x[1].get('name', x[0]).lower())
        #regular.sort(key=lambda x: x[1].get('name', x[0]).lower())
        
        # Объединяем: сначала избранные, потом обычные
        return favorites + regular

    def _on_category_favorite_toggled(self, category_key, strategy_id, is_favorite, favorites_label, scroll_widget):
        """Обработчик изменения избранного в категории"""
        from strategy_menu import is_favorite_strategy
        
        # Пересчитываем количество избранных в категории
        favorites_count = 0
        for child in scroll_widget.findChildren(CompactStrategyItem):
            if is_favorite_strategy(child.strategy_id):
                favorites_count += 1
        
        # Обновляем счетчик
        if favorites_count > 0:
            favorites_label.setText(f"⭐ {favorites_count}")
        else:
            favorites_label.setText("")
        
        # Логируем
        action = "добавлена в" if is_favorite else "удалена из"
        log(f"Стратегия {strategy_id} {action} избранных", "INFO")
        
        # Пересортировываем стратегии в категории через небольшую задержку
        QTimer.singleShot(500, lambda: self._resort_category_strategies(category_key))

    def _resort_category_strategies(self, category_key):
        """Пересортировывает стратегии в категории с учетом избранных"""
        # Находим вкладку по ключу категории
        tab_index = -1
        category_map = {
            'youtube': 0,
            'youtube_udp': 1,
            'googlevideo_tcp': 2,
            'discord': 3,
            'discord_voice': 4,
            'other': 5,
            'ipset': 6,
            'ipset_udp': 7
        }
        
        tab_index = category_map.get(category_key, -1)
        if tab_index == -1 or tab_index >= self.category_tabs.count():
            return
        
        # Получаем текущую вкладку
        tab_widget = self.category_tabs.widget(tab_index)
        if not tab_widget:
            return
        
        # Находим scroll area и его виджет
        scroll_area = None
        for child in tab_widget.findChildren(QScrollArea):
            scroll_area = child
            break
        
        if not scroll_area:
            return
        
        scroll_widget = scroll_area.widget()
        if not scroll_widget:
            return
        
        # Собираем все стратегии из виджетов
        strategy_items = []
        for child in scroll_widget.findChildren(CompactStrategyItem):
            strategy_items.append({
                'widget': child,
                'id': child.strategy_id,
                'data': child.strategy_data,
                'is_checked': child.radio.isChecked()
            })
        
        # Очищаем layout
        layout = scroll_widget.layout()
        while layout.count() > 0:
            item = layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
        
        # Сортируем: избранные вверху
        from strategy_menu import is_favorite_strategy
        
        favorites = []
        regular = []
        
        for item in strategy_items:
            if is_favorite_strategy(item['id']):
                favorites.append(item)
            else:
                regular.append(item)
        
        # Сортируем по имени внутри групп
        favorites.sort(key=lambda x: x['data'].get('name', x['id']).lower())
        regular.sort(key=lambda x: x['data'].get('name', x['id']).lower())
        
        # Добавляем обратно в правильном порядке
        all_sorted = favorites + regular
        
        button_group = getattr(self, f"{category_key}_button_group", None)
        
        for idx, item in enumerate(all_sorted):
            layout.addWidget(item['widget'])
            
            # Восстанавливаем состояние
            if item['is_checked']:
                item['widget'].set_checked(True)
            
            # Обновляем button group
            if button_group:
                button_group.addButton(item['widget'].radio, idx)
        
        # Добавляем растяжку в конец
        layout.addStretch()

    def init_ui(self):
        """Инициализация интерфейса"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Создаем кнопки управления
        self._create_control_buttons()
        
        # Создаем вкладки
        self._create_tabs()
        
        layout.addWidget(self.tab_widget)
        layout.addWidget(self.buttons_widget)

    def _create_control_buttons(self):
        """Создает кнопки управления"""
        self.buttons_layout = QHBoxLayout()
        self.buttons_layout.setSpacing(10)
        
        self.select_button = QPushButton("✅ Выбрать")
        self.select_button.clicked.connect(self.accept)
        self.select_button.setEnabled(False)
        self.select_button.setMinimumHeight(30)
        self.buttons_layout.addWidget(self.select_button)
        
        self.cancel_button = QPushButton("❌ Отмена")
        self.cancel_button.clicked.connect(self.reject)
        self.cancel_button.setMinimumHeight(30)
        self.buttons_layout.addWidget(self.cancel_button)
        
        self.buttons_widget = QWidget()
        self.buttons_widget.setLayout(self.buttons_layout)

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
        
        # Вкладка стратегий
        self.strategies_tab = QWidget()
        self._init_strategies_tab()
        self.tab_widget.addTab(self.strategies_tab, "📋 Стратегии")
        
        # Хостлисты
        from .hostlists_tab import HostlistsTab
        self.hostlists_tab = HostlistsTab()
        self.hostlists_tab.hostlists_changed.connect(self._on_hostlists_changed)
        self.tab_widget.addTab(self.hostlists_tab, "🌐 Hostlist")

        # IPsets
        from .ipsets_tab import IpsetsTab
        self.ipsets_tab = IpsetsTab()
        self.ipsets_tab.ipsets_changed.connect(self._on_ipsets_changed)
        self.tab_widget.addTab(self.ipsets_tab, "🔢 IPSet")

        # Вкладка настроек
        self.settings_tab = QWidget()
        self._init_settings_tab()
        self.tab_widget.addTab(self.settings_tab, "⚙️ Настройки")
        
        self.tab_widget.currentChanged.connect(self._on_tab_changed)

    def _on_hostlists_changed(self):
        """Обработчик изменения хостлистов"""
        log("Хостлисты изменены, может потребоваться перезапуск DPI", "INFO")

    def _on_ipsets_changed(self):
        """Обработчик изменения IPsets"""
        log("IPsets изменены, может потребоваться перезапуск DPI", "INFO")
        
    def _init_strategies_tab(self):
        """Инициализирует вкладку стратегий"""
        layout = QVBoxLayout(self.strategies_tab)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        if self.is_direct_mode:
            self._init_direct_mode_ui(layout)
        else:
            self._init_bat_mode_ui(layout)

    def _init_bat_mode_ui(self, layout):
        """Инициализирует интерфейс для BAT режима"""
        # Создаем виджет таблицы стратегий
        self.strategy_table = StrategyTableWidget(self.strategy_manager, self)
        
        # Подключаем сигналы
        self.strategy_table.strategy_selected.connect(self._on_table_strategy_selected)
        self.strategy_table.strategy_double_clicked.connect(self._on_table_strategy_double_clicked)
        self.strategy_table.refresh_button.clicked.connect(self.refresh_strategies)
        self.strategy_table.download_all_button.clicked.connect(self.strategy_table.download_all_strategies_async)
        
        layout.addWidget(self.strategy_table)

    def _create_preview_widget(self, layout):
        """Создает виджет предпросмотра"""
        preview_widget = QFrame()
        preview_widget.setFrameStyle(QFrame.Shape.Box)
        preview_widget.setMaximumHeight(100)
        preview_layout = QVBoxLayout(preview_widget)
        preview_layout.setContentsMargins(5, 5, 5, 5)
        preview_layout.setSpacing(2)
        
        preview_label = QLabel("📋 Итоговый пресет (активные типы трафика):")
        preview_label.setStyleSheet("font-weight: bold; font-size: 9pt;")
        preview_layout.addWidget(preview_label)
        
        # Добавляем подсказку
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
        
        # Делаем текст кликабельным
        self.preview_text.setOpenExternalLinks(False)
        self.preview_text.mousePressEvent = self._preview_clicked
        
        preview_layout.addWidget(self.preview_text)
        
        layout.addWidget(preview_widget, 0)

    def _preview_clicked(self, event):
        """Обработчик клика по предпросмотру"""
        if event.button() == Qt.MouseButton.LeftButton:
            show_command_line_dialog(self)
            
    def _init_settings_tab(self):
        """Инициализирует вкладку настроек с прокруткой"""
        # Основной layout для вкладки
        tab_layout = QVBoxLayout(self.settings_tab)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        
        # Создаем область прокрутки
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameStyle(QFrame.Shape.NoFrame)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollBar:vertical {
                width: 12px;
                background: #2a2a2a;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background: #555;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #666;
            }
        """)
        
        # Виджет содержимого для прокрутки
        scroll_widget = QWidget()
        layout = QVBoxLayout(scroll_widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Заголовок
        title_label = QLabel("Выберите метод запуска стратегий")
        title_font = title_label.font()
        title_font.setBold(True)
        title_font.setPointSize(11)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("margin: 5px; color: #2196F3;")
        layout.addWidget(title_label)
        
        # Группа методов запуска
        method_group = QGroupBox("Метод запуска стратегий")
        method_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #444;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
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
        
        # Параметры запуска
        self._create_launch_params(layout)
        
        # Информация о методах
        info_group = QGroupBox("Информация")
        info_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #444;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
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
        
        # Уведомление об автоматическом обновлении
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
        
        # Добавляем растяжку в конец
        layout.addStretch()
        
        # Устанавливаем виджет в область прокрутки
        scroll_area.setWidget(scroll_widget)
        
        # Добавляем область прокрутки на вкладку
        tab_layout.addWidget(scroll_area)

    def _create_launch_params(self, layout):
        """Создает параметры запуска"""
        from strategy_menu import get_wssize_enabled, get_allzone_hostlist_enabled, get_game_filter_enabled

        params_group = QGroupBox("Параметры запуска")
        params_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #444;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #ffa500;
            }
        """)
        params_layout = QVBoxLayout(params_group)
        params_layout.setSpacing(8)
        
        # Заголовок с предупреждением
        warning_label = QLabel("⚠️ Перезапустите стратегию после изменения параметров")
        warning_label.setStyleSheet("color: #ffa500; font-weight: bold; font-size: 9pt; margin-bottom: 5px;")
        params_layout.addWidget(warning_label)
        
        # НОВЫЙ ЧЕКБОКС ALLZONE - В САМОМ ВЕРХУ
        allzone_widget = QWidget()
        allzone_layout = QVBoxLayout(allzone_widget)
        allzone_layout.setContentsMargins(0, 0, 0, 0)
        allzone_layout.setSpacing(3)
        
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
        
        game_widget = QWidget()
        game_layout = QVBoxLayout(game_widget)
        game_layout.setContentsMargins(0, 0, 0, 0)
        game_layout.setSpacing(3)
        
        self.ipset_all_checkbox = QCheckBox("Включить фильтр для игр (Game Filter)")
        self.ipset_all_checkbox.setToolTip(
            "Расширяет диапазон портов с 80,443 на 80,443,444-65535\n"
            "для стратегий с хостлистами other.txt.\n"
            "Полезно для игр и приложений на нестандартных портах."
        )
        self.ipset_all_checkbox.setStyleSheet("font-weight: bold;")
        self.ipset_all_checkbox.setChecked(get_game_filter_enabled())
        self.ipset_all_checkbox.stateChanged.connect(self._on_game_filter_changed)
        game_layout.addWidget(self.ipset_all_checkbox)
        
        ipset_info = QLabel("Расширяет фильтрацию на порты 444-65535 для игрового трафика")
        ipset_info.setWordWrap(True)
        ipset_info.setStyleSheet("padding-left: 20px; color: #aaa; font-size: 8pt;")
        game_layout.addWidget(ipset_info)
        
        params_layout.addWidget(game_widget)
        params_layout.addWidget(self._create_separator())
        
        # Чекбокс wssize
        wssize_widget = QWidget()
        wssize_layout = QVBoxLayout(wssize_widget)
        wssize_layout.setContentsMargins(0, 0, 0, 0)
        wssize_layout.setSpacing(3)
        
        self.wssize_checkbox = QCheckBox("Изменить размер окна интернета wssize (МОЖЕТ УМЕНЬШИТЬ СКОРОСТЬ!)")
        self.wssize_checkbox.setToolTip(
            "Включает параметр --wssize=1:6 для всех TCP соединений на порту 443.\n"
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
        
        # Место для будущих параметров
        params_layout.addSpacing(10)
        future_params_label = QLabel("Другие параметры будут добавлены в следующих версиях")
        future_params_label.setStyleSheet("color: #666; font-style: italic; padding: 5px; font-size: 8pt;")
        future_params_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        params_layout.addWidget(future_params_label)
        
        layout.addWidget(params_group)

    def _create_separator(self):
        """Создает визуальный разделитель"""
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        separator.setStyleSheet("QFrame { background-color: #444; max-height: 1px; margin: 5px 0; }")
        return separator

    def _on_allzone_changed(self, state):
        """Обработчик изменения allzone.txt"""
        from strategy_menu import set_allzone_hostlist_enabled
        enabled = (state == Qt.CheckState.Checked.value)
        set_allzone_hostlist_enabled(enabled)
        log(f"Замена other.txt на allzone.txt {'включена' if enabled else 'выключена'}", "INFO")

    def _on_tab_changed(self, index):
        """Обработчик смены вкладок"""
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
        """Обработчик изменения метода запуска"""
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
        """Планирует перезапуск диалога"""
        parent_window = self.parent()
        self.close()
        
        def restart_dialog():
            if parent_window and hasattr(parent_window, '_show_strategy_dialog'):
                parent_window._show_strategy_dialog()
        
        QTimer.singleShot(100, restart_dialog)

    def _on_game_filter_changed(self, state):
        """Обработчик изменения ipset-all"""
        from strategy_menu import set_game_filter_enabled

        enabled = (state == Qt.CheckState.Checked.value)
        set_game_filter_enabled(enabled)
        log(f"Параметр ipset-all {'включен' if enabled else 'выключен'}", "INFO")

    def _on_wssize_changed(self, state):
        """Обработчик изменения wssize"""
        from strategy_menu import set_wssize_enabled
        enabled = (state == Qt.CheckState.Checked.value)
        set_wssize_enabled(enabled)
        log(f"Параметр --wssize=1:6 {'включен' if enabled else 'выключен'}", "INFO")

    def _on_table_strategy_selected(self, strategy_id, strategy_name):
        """Обработчик выбора стратегии в таблице"""
        self.selected_strategy_id = strategy_id
        self.selected_strategy_name = strategy_name
        self.select_button.setEnabled(True)
        log(f"Выбрана стратегия: {strategy_name}", "DEBUG")

    def _on_table_strategy_double_clicked(self, strategy_id, strategy_name):
        """Обработчик двойного клика на стратегии"""
        self.selected_strategy_id = strategy_id
        self.selected_strategy_name = strategy_name
        self.accept()

    def on_category_selection_changed(self, category, strategy_id):
        """Обработчик изменения выбора в категории"""

        from strategy_menu import set_direct_strategy_youtube, set_direct_strategy_youtube_udp, set_direct_strategy_googlevideo, set_direct_strategy_discord, set_direct_strategy_other, set_direct_strategy_discord_voice, set_direct_strategy_ipset, set_direct_strategy_udp_ipset

        self.category_selections[category] = strategy_id
        self.update_combined_preview()
        
        # Сохраняем выбор
        try:
            if category == 'youtube':
                set_direct_strategy_youtube(strategy_id)
            elif category == 'youtube_udp':
                set_direct_strategy_youtube_udp(strategy_id)
            elif category == 'googlevideo_tcp':
                set_direct_strategy_googlevideo(strategy_id)
            elif category == 'discord':
                set_direct_strategy_discord(strategy_id)
            elif category == 'discord_voice':
                set_direct_strategy_discord_voice(strategy_id)
            elif category == 'other':
                set_direct_strategy_other(strategy_id)
            elif category == 'ipset':
                set_direct_strategy_ipset(strategy_id)
            elif category == 'ipset_udp':
                set_direct_strategy_udp_ipset(strategy_id)

            log(f"Сохранена {category} стратегия: {strategy_id}", "DEBUG")
        except Exception as e:
            log(f"Ошибка сохранения {category} стратегии: {e}", "⚠ WARNING")
        
        self.select_button.setEnabled(True)

    def update_combined_preview(self):
        """Обновляет предпросмотр комбинированной стратегии"""
        if not hasattr(self, 'preview_text'):
            return
        
        from .strategy_lists_separated import combine_strategies
        
        combined = combine_strategies(
            self.category_selections.get('youtube'),
            self.category_selections.get('youtube_udp'),
            self.category_selections.get('googlevideo_tcp'),
            self.category_selections.get('discord'),
            self.category_selections.get('discord_voice'),
            self.category_selections.get('other'),
            self.category_selections.get('ipset'),
            self.category_selections.get('ipset_udp')
        )
        
        active = []
        # НОВОЕ: Добавляем звездочки для избранных стратегий
        from strategy_menu import is_favorite_strategy
        
        def format_strategy(category_name, category_key, color):
            strategy_id = self.category_selections.get(category_key)
            if strategy_id and strategy_id != f'{category_key}_none':
                star = "⭐ " if is_favorite_strategy(strategy_id) else ""
                return f"{star}<span style='color: {color};'>{category_name}</span>"
            return None
        
        items = [
            format_strategy("YouTube TCP (80 & 443)", 'youtube', '#ff6666'),
            format_strategy("YouTube QUIC/UDP (443)", 'youtube_udp', '#ffcc00'),
            format_strategy("GoogleVideo TCP (443)", 'googlevideo_tcp', '#ff9900'),
            format_strategy("Discord TCP (80 & 443)", 'discord', '#7289da'),
            format_strategy("Discord Voice UDP (all stun ports)", 'discord_voice', '#9b59b6'),
            format_strategy("Сайты TCP (80 & 443)", 'other', '#66ff66'),
            format_strategy("IPset TCP (80 & 443)", 'ipset', '#ffa500'),
            format_strategy("IPset UDP (all ports)", 'ipset_udp', "#ae00ff"),
        ]
        
        active = [item for item in items if item]
        
        if active:
            preview_html = f"<b>Активные:</b> {', '.join(active)}"
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
        """Загружает встроенные стратегии (вызывается если нужна синхронная загрузка)"""
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
        """Загружает локальные BAT стратегии"""
        try:
            # Показываем прогресс только во время загрузки
            if hasattr(self, 'strategy_table'):
                self.strategy_table.set_progress_visible(True)
                self.strategy_table.set_status("📂 Загрузка локальных стратегий...", "info")
            
            strategies = self.strategy_manager.get_local_strategies_only()
            
            if strategies and hasattr(self, 'strategy_table'):
                self.strategy_table.populate_strategies(strategies)
                
                # Скрываем прогресс после загрузки
                self.strategy_table.set_progress_visible(False)
                
                # Выбираем текущую стратегию
                if self.current_strategy_name:
                    self.strategy_table.select_strategy_by_name(self.current_strategy_name)
                
                log(f"Загружено {len(strategies)} локальных стратегий", "INFO")
            else:
                self.strategy_table.set_status(
                    "⚠️ Локальные стратегии не найдены. Нажмите 'Обновить'", 
                    "warning"
                )
                # Скрываем прогресс даже если нет стратегий
                self.strategy_table.set_progress_visible(False)
                
        except Exception as e:
            log(f"Ошибка загрузки локальных стратегий: {e}", "❌ ERROR")
            if hasattr(self, 'strategy_table'):
                self.strategy_table.set_status(f"❌ Ошибка: {e}", "error")
                # Скрываем прогресс при ошибке
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
        
        # Обновляем UI
        self.strategy_table.set_status("🌐 Загрузка стратегий из интернета...", "info")
        self.strategy_table.set_progress_visible(True)
        self.strategy_table.refresh_button.setEnabled(False)
        self.strategy_table.download_all_button.setEnabled(False)
        
        # Создаем поток для загрузки
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
        
        # Восстанавливаем UI
        self.strategy_table.set_progress_visible(False)
        self.strategy_table.refresh_button.setEnabled(True)
        self.strategy_table.download_all_button.setEnabled(True)
        
        if error_message:
            self.strategy_table.set_status(f"❌ {error_message}", "error")
            return
        
        if not strategies:
            self.strategy_table.set_status("⚠️ Список стратегий пуст", "warning")
            return
        
        # Заполняем таблицу
        self.strategy_table.populate_strategies(strategies)
        
        # Выбираем текущую стратегию
        if self.current_strategy_name:
            self.strategy_table.select_strategy_by_name(self.current_strategy_name)
        
        log(f"Загружено {len(strategies)} стратегий", "INFO")

    def accept(self):
        """Обрабатывает выбор стратегии"""
        if self.is_direct_mode:
            # Режим прямого запуска
            from .strategy_lists_separated import combine_strategies, get_default_selections
            
            if not self.category_selections:
                self.category_selections = get_default_selections()
            
            combined = combine_strategies(
                self.category_selections.get('youtube'),
                self.category_selections.get('youtube_udp'),
                self.category_selections.get('googlevideo_tcp'),
                self.category_selections.get('discord'),
                self.category_selections.get('discord_voice'),
                self.category_selections.get('other'),
                self.category_selections.get('ipset'),
                self.category_selections.get('ipset_udp')
            )
            
            # ВАЖНО: Сохраняем данные в атрибуты диалога для доступа из main.py
            self._combined_args = combined['args']
            self._combined_strategy_data = {
                'is_combined': True,
                'name': combined['description'],
                'args': combined['args'],
                'selections': self.category_selections
            }
            # Устанавливаем ID и имя для сигнала
            self.selected_strategy_id = "COMBINED_DIRECT"
            self.selected_strategy_name = combined['description']
            
            log(f"Выбрана комбинированная стратегия: {self.selected_strategy_name}", "INFO")
            log(f"Сохранены аргументы: {len(self._combined_args)} символов", "DEBUG")
            log(f"Выборы категорий: {self.category_selections}", "DEBUG")
            
        else:
            # BAT режим
            if not self.selected_strategy_id or not self.selected_strategy_name:
                QMessageBox.warning(self, "Выбор стратегии", 
                                "Пожалуйста, выберите стратегию из списка")
                return
            
            # Для совместимости создаем пустые атрибуты
            self._combined_args = None
            self._combined_strategy_data = None
            
            log(f"Выбрана стратегия: {self.selected_strategy_name}", "INFO")
        
        # Эмитим сигнал
        self.strategySelected.emit(self.selected_strategy_id, self.selected_strategy_name)
        
        # НЕ закрываем диалог здесь, так как main.py может еще обращаться к атрибутам
        # Диалог закроется автоматически после обработки сигнала

    def reject(self):
        """Обрабатывает отмену выбора"""
        self.close()
        log("Диалог выбора стратегии отменен", "INFO")

    def closeEvent(self, event):
        """Безопасное закрытие диалога"""
        # Останавливаем потоки если они запущены
        try:
            if hasattr(self, 'loader_thread') and self.loader_thread:
                if self.loader_thread.isRunning():
                    self.loader_thread.quit()  # Используем quit() вместо terminate()
                    if not self.loader_thread.wait(2000):
                        self.loader_thread.terminate()
                        self.loader_thread.wait(1000)
        except RuntimeError:
            # Объект QThread уже удален
            pass
        
        event.accept()