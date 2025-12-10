# strategy_menu/simple_tab_panel.py
"""
Простая панель с вертикальными вкладками и иконками в стиле Windows 11.
Замена для AnimatedSidePanel.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QListWidget, QListWidgetItem, QStackedWidget, QFrame,
    QSizePolicy, QAbstractItemView, QPushButton, QMenu
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QPoint, QTimer
from PyQt6.QtGui import QFont, QCursor
import qtawesome as qta

from log import log


class ScrollBlockingListWidget(QListWidget):
    """QListWidget который не пропускает прокрутку к родителю"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._blocked_tabs = set()
    
    def wheelEvent(self, event):
        scrollbar = self.verticalScrollBar()
        delta = event.angleDelta().y()
        
        # Если прокручиваем вверх и уже в начале - блокируем
        if delta > 0 and scrollbar.value() == scrollbar.minimum():
            event.accept()
            return
        
        # Если прокручиваем вниз и уже в конце - блокируем
        if delta < 0 and scrollbar.value() == scrollbar.maximum():
            event.accept()
            return
        
        super().wheelEvent(event)
        event.accept()
    
    def mouseMoveEvent(self, event):
        """Обработчик движения мыши - меняем курсор для заблокированных вкладок"""
        item = self.itemAt(event.pos())
        if item:
            index = self.row(item)
            if index in self._blocked_tabs:
                self.setCursor(Qt.CursorShape.ForbiddenCursor)
                # Убираем hover эффект для заблокированных
                self.clearSelection()
            else:
                self.setCursor(Qt.CursorShape.ArrowCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)
        
        super().mouseMoveEvent(event)
    
    def leaveEvent(self, event):
        """Восстанавливаем курсор при выходе мыши"""
        self.setCursor(Qt.CursorShape.ArrowCursor)
        super().leaveEvent(event)


class SimpleTabPanel(QWidget):
    """Панель с вертикальными вкладками слева и контентом справа"""
    
    currentChanged = pyqtSignal(int)
    add_category_clicked = pyqtSignal()  # Сигнал при нажатии на кнопку добавления
    edit_category_clicked = pyqtSignal(str)  # Сигнал при редактировании (category_key)
    
    def __init__(self, parent=None, show_add_button=False):
        super().__init__(parent)
        self._tab_category_keys = []
        self._tab_icons = {}  # {index: (icon_name, icon_color)}
        self._blocked_tabs = set()  # Индексы заблокированных вкладок
        self._original_icons = {}  # {index: (icon_name, icon_color)} - сохраненные оригинальные иконки
        self._original_tooltips = {}  # {index: tooltip} - сохраненные оригинальные подсказки
        self._show_add_button = show_add_button
        self._last_selected_index = 0
        self._add_button_added = False
        self._build_ui()
        
    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Левая панель со списком вкладок
        self.tabs_container = QFrame()
        self.tabs_container.setFixedWidth(125)
        self.tabs_container.setStyleSheet("""
            QFrame {
                background: rgba(20, 20, 22, 0.8);
                border: none;
            }
        """)
        
        tabs_layout = QVBoxLayout(self.tabs_container)
        tabs_layout.setContentsMargins(1, 1, 1, 1)
        tabs_layout.setSpacing(0)
        
        # Список вкладок (с блокировкой передачи прокрутки родителю)
        self.list_widget = ScrollBlockingListWidget()
        self.list_widget._blocked_tabs = self._blocked_tabs  # Связываем с общим набором
        self.list_widget.setIconSize(QSize(11, 11))
        self.list_widget.setSpacing(0)
        self.list_widget.setFrameShape(QFrame.Shape.NoFrame)
        self.list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list_widget.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.list_widget.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.list_widget.currentRowChanged.connect(self._on_tab_changed)
        # Запрещаем перетаскивание окна при взаимодействии со списком
        self.list_widget.setProperty("noDrag", True)
        
        # Включаем контекстное меню
        self.list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self._show_context_menu)
        
        self.list_widget.setStyleSheet("""
            QListWidget {
                background: transparent;
                border: none;
                outline: none;
            }
            QListWidget::item {
                color: rgba(255, 255, 255, 0.7);
                padding: 2px 5px;
                border-radius: 3px;
                font-size: 9px;
                margin: 0;
                min-height: 18px;
            }
            QListWidget::item:hover {
                background: rgba(255, 255, 255, 0.08);
            }
            QListWidget::item:selected {
                background: rgba(96, 205, 255, 0.15);
                color: #60cdff;
                font-weight: 600;
            }
            QScrollBar:vertical {
                width: 3px;
                background: transparent;
            }
            QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 0.15);
                border-radius: 1px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(255, 255, 255, 0.25);
            }
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        
        tabs_layout.addWidget(self.list_widget)
        layout.addWidget(self.tabs_container)
        
        # Правая панель с контентом
        self.stack_widget = QStackedWidget()
        self.stack_widget.setStyleSheet("background: transparent;")
        self.stack_widget.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.stack_widget, 1)
        
    def _restore_selection(self, index):
        """Восстанавливает выделение на указанной вкладке"""
        if 0 <= index < self.list_widget.count():
            self.list_widget.blockSignals(True)
            self.list_widget.setCurrentRow(index)
            self.stack_widget.setCurrentIndex(index)
            self.list_widget.blockSignals(False)
    
    def _on_tab_changed(self, index):
        """Обработчик смены вкладки"""
        # Проверяем, не кликнули ли на кнопку добавления (последний элемент)
        if self._show_add_button and index == self.list_widget.count() - 1:
            item = self.list_widget.item(index)
            if item and item.data(Qt.ItemDataRole.UserRole) == "add_button":
                # Снимаем выделение с кнопки добавления
                self.list_widget.blockSignals(True)
                if self._last_selected_index >= 0:
                    self.list_widget.setCurrentRow(self._last_selected_index)
                self.list_widget.blockSignals(False)
                # Эмитим сигнал добавления
                self.add_category_clicked.emit()
                return
        
        # Проверяем, не заблокирована ли вкладка
        if index in self._blocked_tabs:
            # Возвращаемся к последней выбранной вкладке
            if self._last_selected_index >= 0 and self._last_selected_index not in self._blocked_tabs:
                # Используем QTimer для отложенного восстановления выделения
                # Это предотвращает конфликты с обработкой событий Qt
                QTimer.singleShot(0, lambda: self._restore_selection(self._last_selected_index))
            return
        
        # Сохраняем последний выбранный индекс (не кнопка добавления)
        self._last_selected_index = index
        
        if 0 <= index < self.stack_widget.count():
            self.stack_widget.setCurrentIndex(index)
            self.currentChanged.emit(index)
    
    def addTab(self, widget, label, category_key=None):
        """Добавляет новую вкладку"""
        index = self.stack_widget.addWidget(widget)
        
        item = QListWidgetItem(label)
        item.setFont(QFont("Segoe UI", 9))
        self.list_widget.addItem(item)
        
        # Сохраняем category_key
        if len(self._tab_category_keys) <= index:
            self._tab_category_keys.append(category_key)
        
        # Добавляем иконку если есть category_key
        if category_key:
            self._set_tab_icon(index, category_key)
        
        return index
    
    def _set_tab_icon(self, index, category_key, is_inactive=False):
        """Устанавливает иконку для вкладки"""
        try:
            # Если вкладка заблокирована - не меняем иконку (у неё иконка запрета)
            if index in self._blocked_tabs:
                return
            
            from strategy_menu.strategies_registry import registry
            
            cat_info = registry.get_category_info(category_key)
            if cat_info:
                icon_name = cat_info.icon_name or 'fa5s.globe'
                icon_color = '#888888' if is_inactive else (cat_info.icon_color or '#60cdff')
                
                self._tab_icons[index] = (icon_name, icon_color, is_inactive)
                
                item = self.list_widget.item(index)
                if item:
                    icon = qta.icon(icon_name, color=icon_color)
                    item.setIcon(icon)
        except Exception as e:
            log(f"Ошибка установки иконки: {e}", "DEBUG")
    
    def update_tab_icon_color(self, index, is_inactive=False):
        """Обновляет цвет иконки вкладки"""
        if 0 <= index < len(self._tab_category_keys):
            category_key = self._tab_category_keys[index]
            if category_key:
                self._set_tab_icon(index, category_key, is_inactive)
    
    def update_all_tab_icons(self, selections_dict):
        """Обновляет цвета всех иконок на основе выборов"""
        for index, category_key in enumerate(self._tab_category_keys):
            if category_key:
                # Пропускаем заблокированные вкладки - у них своя иконка
                if index in self._blocked_tabs:
                    continue
                    
                strategy_id = selections_dict.get(category_key, "none")
                is_inactive = (strategy_id == "none" or not strategy_id)
                self.update_tab_icon_color(index, is_inactive=is_inactive)
    
    def setTabToolTip(self, index, tooltip):
        """Устанавливает подсказку для вкладки"""
        if 0 <= index < self.list_widget.count():
            item = self.list_widget.item(index)
            if item:
                item.setToolTip(tooltip)
    
    def set_tab_blocked(self, index: int, blocked: bool, required_filter_hint: str = None):
        """
        Устанавливает состояние блокировки для вкладки.
        
        Args:
            index: Индекс вкладки
            blocked: True - заблокировать (темный текст, курсор 🚫)
            required_filter_hint: Подсказка какой фильтр нужно включить для разблокировки
        """
        if 0 <= index < self.list_widget.count():
            item = self.list_widget.item(index)
            if item:
                if blocked:
                    self._blocked_tabs.add(index)
                    # Помечаем как заблокированный
                    item.setData(Qt.ItemDataRole.UserRole + 1, "blocked")
                    # Меняем иконку на "запрещено"
                    try:
                        blocked_icon = qta.icon('fa5s.ban', color='#666666')  # Иконка запрета
                        item.setIcon(blocked_icon)
                    except Exception as e:
                        log(f"Ошибка установки иконки запрета: {e}", "DEBUG")
                    
                    # Сохраняем оригинальный tooltip и устанавливаем подсказку о фильтре
                    if index not in self._original_tooltips:
                        self._original_tooltips[index] = item.toolTip()
                    
                    if required_filter_hint:
                        item.setToolTip(f"🚫 {required_filter_hint}")
                else:
                    self._blocked_tabs.discard(index)
                    item.setData(Qt.ItemDataRole.UserRole + 1, None)
                    # НЕ восстанавливаем иконку здесь - это будет сделано через update_all_tab_icons
                    # с правильным состоянием is_inactive на основе category_selections
                    
                    # Восстанавливаем оригинальный tooltip
                    if index in self._original_tooltips:
                        item.setToolTip(self._original_tooltips[index])
                        del self._original_tooltips[index]
                
                # Принудительно обновляем отображение
                self.list_widget.update()
    
    def is_tab_blocked(self, index: int) -> bool:
        """Проверяет, заблокирована ли вкладка"""
        return index in self._blocked_tabs
    
    def clear(self):
        """Очищает все вкладки"""
        self.list_widget.clear()
        while self.stack_widget.count():
            widget = self.stack_widget.widget(0)
            self.stack_widget.removeWidget(widget)
            if widget:
                widget.deleteLater()
        self._tab_category_keys = []
        self._tab_icons = {}
        self._blocked_tabs.clear()
        self._original_tooltips.clear()
        self._original_icons.clear()
        self._add_button_added = False
        self._last_selected_index = 0
    
    def count(self):
        """Возвращает количество вкладок"""
        return self.stack_widget.count()
    
    def widget(self, index):
        """Возвращает виджет по индексу"""
        return self.stack_widget.widget(index)
    
    def currentIndex(self):
        """Возвращает индекс текущей вкладки"""
        return self.stack_widget.currentIndex()
    
    def setCurrentIndex(self, index):
        """Устанавливает текущую вкладку"""
        if 0 <= index < self.count():
            self.list_widget.setCurrentRow(index)
            self.stack_widget.setCurrentIndex(index)
    
    def blockSignals(self, block):
        """Блокирует/разблокирует сигналы"""
        super().blockSignals(block)
        self.list_widget.blockSignals(block)
        
    def add_add_button(self):
        """Добавляет кнопку '+' в конец списка (как элемент списка)"""
        if not self._show_add_button or self._add_button_added:
            return
            
        # Создаём элемент списка для кнопки добавления
        add_item = QListWidgetItem("  +  Добавить")
        add_item.setFont(QFont("Segoe UI", 9))
        add_item.setIcon(qta.icon('fa5s.plus', color='rgba(255,255,255,0.5)'))
        add_item.setToolTip("Добавить свою категорию")
        add_item.setData(Qt.ItemDataRole.UserRole, "add_button")  # Маркер что это кнопка
        
        self.list_widget.addItem(add_item)
        self._add_button_added = True
    
    def _show_context_menu(self, pos: QPoint):
        """Показывает контекстное меню для вкладки"""
        item = self.list_widget.itemAt(pos)
        if not item:
            return
        
        # Проверяем что это не кнопка добавления
        if item.data(Qt.ItemDataRole.UserRole) == "add_button":
            return
        
        # Получаем индекс элемента
        index = self.list_widget.row(item)
        if index < 0 or index >= len(self._tab_category_keys):
            return
        
        category_key = self._tab_category_keys[index]
        if not category_key:
            return
        
        # Проверяем что это пользовательская категория
        try:
            from strategy_menu.strategies_registry import registry
            cat_info = registry.get_category_info(category_key)
            if not cat_info or cat_info.command_group != "user":
                return  # Показываем меню только для пользовательских категорий
        except Exception as e:
            log(f"Ошибка проверки категории: {e}", "DEBUG")
            return
        
        # Создаём контекстное меню
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background: #2d2d2d;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 20px;
                color: white;
                border-radius: 3px;
            }
            QMenu::item:selected {
                background: rgba(96, 205, 255, 0.3);
            }
        """)
        
        edit_action = menu.addAction(qta.icon('fa5s.edit', color='white'), "  Редактировать")
        
        action = menu.exec(QCursor.pos())
        
        if action == edit_action:
            self.edit_category_clicked.emit(category_key)
    
    # Свойства для совместимости
    @property
    def is_pinned(self):
        return True  # Всегда "закреплена"
    

