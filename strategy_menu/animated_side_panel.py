"""
Анимированная боковая панель с вкладками
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QListWidget, 
                            QStackedWidget, QFrame, QScrollArea)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QPropertyAnimation, QEasingCurve, QSize
from PyQt6.QtGui import QPainter, QCursor, QColor, QPen
import qtawesome as qta

from log import log
from strategy_menu.strategies_registry import registry


class ScrollBlockingListWidget(QListWidget):
    """QListWidget который не пропускает прокрутку к родителю"""
    
    def wheelEvent(self, event):
        # Обрабатываем прокрутку и блокируем её от "провала" к родителю
        scrollbar = self.verticalScrollBar()
        
        # Проверяем направление прокрутки
        delta = event.angleDelta().y()
        
        # Если прокручиваем вверх и уже в начале - блокируем
        if delta > 0 and scrollbar.value() == scrollbar.minimum():
            event.accept()
            return
        
        # Если прокручиваем вниз и уже в конце - блокируем
        if delta < 0 and scrollbar.value() == scrollbar.maximum():
            event.accept()
            return
        
        # Иначе обрабатываем нормально
        super().wheelEvent(event)
        event.accept()  # Всегда принимаем событие чтобы не пропускать дальше


class AnimatedSidePanel(QWidget):
    """Боковая панель с анимированным изменением ширины и поддержкой закрепления"""
    
    currentChanged = pyqtSignal(int)
    
    def __init__(self):
        super().__init__()
        self.collapsed_width = 45
        self.expanded_width = 160
        self.is_expanded = False
        self.is_pinned = False
        
        # Для прокрутки текста
        self.scroll_timer = QTimer()
        self.scroll_timer.timeout.connect(self._scroll_text)
        self.current_hover_item = None
        self.current_hover_index = -1
        self.original_texts = {}
        self.scroll_position = 0
        self.scroll_pause_counter = 0
        
        # Основной layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Левая панель с списком (блокирует провал прокрутки)
        self.list_widget = ScrollBlockingListWidget()
        self.list_widget.setIconSize(QSize(16, 16))
        self.list_widget.setFrameShape(QFrame.Shape.NoFrame)
        self.list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list_widget.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # Включаем отслеживание мыши
        self.list_widget.setMouseTracking(True)
        
        # Современный стиль для списка - компактный
        self.list_widget.setStyleSheet("""
            QListWidget {
                background: transparent;
                border: none;
                outline: none;
                padding: 2px 0;
            }
            QListWidget::item {
                color: rgba(255, 255, 255, 0.6);
                padding: 6px 8px;
                margin: 1px 2px;
                border-radius: 4px;
                font-size: 11px;
                min-height: 16px;
            }
            QListWidget::item:hover {
                background: rgba(255, 255, 255, 0.08);
                color: rgba(255, 255, 255, 0.9);
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
            QScrollBar::sub-line:vertical,
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {
                height: 0px;
                background: none;
            }
        """)
        
        # Контейнер для списка с фиксированной шириной
        self.list_container = QWidget()
        self.list_container.setStyleSheet("""
            QWidget {
                background: rgba(25, 25, 25, 0.6);
                border: none;
                border-right: 1px solid rgba(255, 255, 255, 0.06);
            }
        """)
        list_layout = QVBoxLayout(self.list_container)
        list_layout.setContentsMargins(0, 0, 0, 0)
        list_layout.addWidget(self.list_widget)
        
        # Правая панель с содержимым
        self.stack_widget = QStackedWidget()
        self.stack_widget.setStyleSheet("""
            QStackedWidget {
                background: transparent;
                border: none;
            }
        """)
        
        layout.addWidget(self.list_container)
        layout.addWidget(self.stack_widget, 1)
        
        # Анимация ширины
        self.width_animation = QPropertyAnimation(self.list_container, b"maximumWidth")
        self.width_animation.setDuration(200)
        self.width_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        
        # Загружаем закрепление
        from strategy_menu import get_tabs_pinned
        self.is_pinned = get_tabs_pinned()
        
        start_w = self.expanded_width if self.is_pinned else self.collapsed_width
        self.list_container.setFixedWidth(start_w)
        self.is_expanded = self.is_pinned
        
        # Обработчики
        self.list_widget.currentRowChanged.connect(self._on_selection_changed)
        self.list_widget.installEventFilter(self)
        self.list_widget.viewport().installEventFilter(self)
        
        self.tab_names = {}
        self._tab_indices = {}

    def _get_fa_icon(self, category_key):
        """Возвращает Font Awesome иконку для категории"""
        category_info = registry.get_category_info(category_key)
        
        if category_info:
            try:
                # Проверяем валидность icon_name перед созданием
                icon_name = category_info.icon_name
                if icon_name and icon_name.startswith(('fa5s.', 'fa5b.', 'fa.', 'mdi.')):
                    icon = qta.icon(icon_name, color=category_info.icon_color)
                    return icon
                else:
                    log(f"Неизвестный префикс иконки для {category_key}: {icon_name}", "⚠ WARNING")
            except Exception as e:
                log(f"Ошибка создания иконки для {category_key}: {e}", "⚠ WARNING")
        
        # Безопасный fallback
        try:
            return qta.icon('fa5s.globe', color='#2196F3')
        except:
            return None
                
    def eventFilter(self, obj, event):
        """Обработчик событий для анимации и прокрутки текста"""
        from PyQt6.QtCore import QEvent
        
        if obj == self.list_widget:
            if event.type() == QEvent.Type.HoverEnter and not self.is_pinned:
                self._expand_animated()
            elif event.type() == QEvent.Type.HoverLeave:
                if not self.is_pinned:
                    self._collapse_animated()
                self._stop_scrolling()
                
        elif obj == self.list_widget.viewport():
            if event.type() == QEvent.Type.MouseMove:
                pos = event.pos()
                item = self.list_widget.itemAt(pos)
                
                if item:
                    row = self.list_widget.row(item)
                    if row != self.current_hover_index:
                        self._stop_scrolling()
                        self._start_scrolling(item, row)
                else:
                    self._stop_scrolling()
                    
            elif event.type() == QEvent.Type.Leave:
                self._stop_scrolling()
                
        return super().eventFilter(obj, event)
    
    def _start_scrolling(self, item, index):
        """Запускает прокрутку текста для элемента"""
        if not item:
            return
            
        text = item.text()
        
        if index not in self.original_texts:
            self.original_texts[index] = text
        else:
            text = self.original_texts[index]
        
        font_metrics = self.list_widget.fontMetrics()
        text_width = font_metrics.horizontalAdvance(text)
        
        list_rect = self.list_widget.viewport().rect()
        available_width = list_rect.width() - 10
        
        if text_width > available_width or len(text) > 15:
            self.current_hover_item = item
            self.current_hover_index = index
            self.scroll_position = 0
            self.scroll_pause_counter = 0
            self.scroll_timer.start(100)
    
    def _scroll_text(self):
        """Прокручивает текст текущего элемента"""
        if self.current_hover_item is None or self.current_hover_index == -1:
            self._stop_scrolling()
            return
            
        original_text = self.original_texts.get(self.current_hover_index, "")
        if not original_text:
            self._stop_scrolling()
            return
        
        if self.scroll_pause_counter < 10:
            self.scroll_pause_counter += 1
            return
        
        scrolling_text = original_text + "     •     " + original_text
        self.scroll_position += 1
        
        if self.scroll_position >= len(original_text) + 13:
            self.scroll_position = 0
            self.scroll_pause_counter = 0
            return
        
        visible_text = scrolling_text[self.scroll_position:]
        
        font_metrics = self.list_widget.fontMetrics()
        list_rect = self.list_widget.viewport().rect()
        available_width = list_rect.width() - 10
        
        elided_text = font_metrics.elidedText(visible_text, Qt.TextElideMode.ElideRight, available_width)
        
        try:
            self.current_hover_item.setText(elided_text)
        except:
            self._stop_scrolling()
    
    def _stop_scrolling(self):
        """Останавливает прокрутку и восстанавливает оригинальный текст"""
        self.scroll_timer.stop()
        
        if self.current_hover_item and self.current_hover_index in self.original_texts:
            try:
                self.current_hover_item.setText(self.original_texts[self.current_hover_index])
            except:
                pass
        
        self.current_hover_item = None
        self.current_hover_index = -1
        self.scroll_position = 0
        self.scroll_pause_counter = 0
        
    def tabBar(self):
        """Возвращает список для совместимости с существующим кодом"""
        return self.list_widget
        
    def set_tab_names(self, tab_names_dict):
        """Сохраняет словарь названий вкладок"""
        self.tab_names = tab_names_dict
        if self.is_pinned and self.is_expanded:
            self.show_full_names()
            
    def show_full_names(self):
        """Показывает полные названия вкладок"""
        if not self.tab_names:
            return
        for i, key in enumerate(self.tab_names.keys()):
            if i < self.list_widget.count():
                _, full = self.tab_names[key]
                item = self.list_widget.item(i)
                if item:
                    item.setText(full)
                    self.original_texts[i] = full
                
    def show_short_names(self):
        """Показывает короткие названия вкладок"""
        if not self.tab_names:
            return
        for i, key in enumerate(self.tab_names.keys()):
            if i < self.list_widget.count():
                short, _ = self.tab_names[key]
                item = self.list_widget.item(i)
                if item:
                    item.setText(short)
                    self.original_texts[i] = short
                
    def addTab(self, widget, label, category_key=None):
        """Добавляет новую вкладку с иконкой"""
        index = self.stack_widget.addWidget(widget)
        self.list_widget.addItem(label)
        
        if not hasattr(self, '_tab_category_keys'):
            self._tab_category_keys = []
        
        if len(self._tab_category_keys) <= index:
            self._tab_category_keys.append(category_key)
        
        if category_key:
            icon = self._get_fa_icon(category_key)
            if icon:
                list_item = self.list_widget.item(index)
                if list_item:
                    list_item.setIcon(icon)
        
        self.original_texts[index] = label
        return index

    def removeTab(self, index):
        """Удаляет вкладку"""
        if index < self.stack_widget.count():
            widget = self.stack_widget.widget(index)
            self.stack_widget.removeWidget(widget)
            
            item = self.list_widget.takeItem(index)
            if item:
                del item
            
            if hasattr(self, '_tab_category_keys') and index < len(self._tab_category_keys):
                self._tab_category_keys.pop(index)
            
            self._update_original_texts()

    def update_all_icons(self):
        """Обновляет иконки для всех вкладок"""
        if not hasattr(self, '_tab_category_keys'):
            return
            
        for index, category_key in enumerate(self._tab_category_keys):
            if category_key and index < self.list_widget.count():
                icon = self._get_fa_icon(category_key)
                if icon:
                    list_item = self.list_widget.item(index)
                    if list_item:
                        list_item.setIcon(icon)

    def update_tab_active_states(self, active_categories: set):
        """
        Обновляет визуальное состояние вкладок: активные - яркие, неактивные - серые.
        
        Args:
            active_categories: Множество ключей категорий с активными стратегиями
        """
        if not hasattr(self, '_tab_category_keys'):
            return
        
        for index, category_key in enumerate(self._tab_category_keys):
            if not category_key or index >= self.list_widget.count():
                continue
                
            list_item = self.list_widget.item(index)
            if not list_item:
                continue
            
            category_info = registry.get_category_info(category_key)
            if not category_info:
                continue
            
            is_active = category_key in active_categories
            
            # Цвет иконки: яркий для активных, серый для неактивных
            if is_active:
                icon_color = category_info.icon_color
                text_color = "#fff"
            else:
                icon_color = "#555"
                text_color = "#777"
            
            # Обновляем иконку
            try:
                icon_name = category_info.icon_name
                if icon_name and icon_name.startswith(('fa5s.', 'fa5b.', 'fa.', 'mdi.')):
                    icon = qta.icon(icon_name, color=icon_color)
                    list_item.setIcon(icon)
            except Exception as e:
                log(f"Ошибка обновления иконки {category_key}: {e}", "⚠ WARNING")
            
            # Обновляем цвет текста через foreground
            list_item.setForeground(QColor(text_color))

    def insertTab(self, index, widget, label, category_key=None):
        """Вставляет вкладку в определенную позицию"""
        self.stack_widget.insertWidget(index, widget)
        self.list_widget.insertItem(index, label)
        
        if not hasattr(self, '_tab_category_keys'):
            self._tab_category_keys = []
        
        if category_key:
            if index < len(self._tab_category_keys):
                self._tab_category_keys.insert(index, category_key)
            else:
                while len(self._tab_category_keys) < index:
                    self._tab_category_keys.append(None)
                self._tab_category_keys.insert(index, category_key)
            
            icon = self._get_fa_icon(category_key)
            if icon:
                list_item = self.list_widget.item(index)
                if list_item:
                    list_item.setIcon(icon)
        else:
            if index < len(self._tab_category_keys):
                self._tab_category_keys.insert(index, None)
        
        self._update_original_texts()
        return index
            
    def _update_original_texts(self):
        """Обновляет словарь с оригинальными текстами после изменения списка"""
        new_texts = {}
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item:
                if i in self.original_texts:
                    new_texts[i] = self.original_texts[i]
                else:
                    new_texts[i] = item.text()
        self.original_texts = new_texts
        
    def widget(self, index):
        """Возвращает виджет по индексу"""
        return self.stack_widget.widget(index)
        
    def count(self):
        """Возвращает количество вкладок"""
        return self.stack_widget.count()
    
    def clear(self):
        """Очищает все вкладки"""
        # Очищаем список
        self.list_widget.clear()
        
        # Удаляем все виджеты из стека
        while self.stack_widget.count() > 0:
            widget = self.stack_widget.widget(0)
            self.stack_widget.removeWidget(widget)
            if widget:
                widget.deleteLater()
        
        # Очищаем внутренние структуры
        if hasattr(self, '_tab_category_keys'):
            self._tab_category_keys = []
        if hasattr(self, 'original_texts'):
            self.original_texts = {}
        
    def currentIndex(self):
        """Возвращает индекс текущей вкладки"""
        return self.stack_widget.currentIndex()
    
    def setCurrentIndex(self, index):
        """Устанавливает текущую вкладку"""
        self.list_widget.setCurrentRow(index)
        self.stack_widget.setCurrentIndex(index)
        
    def setTabToolTip(self, index, tooltip):
        """Устанавливает подсказку для вкладки"""
        if index < self.list_widget.count():
            item = self.list_widget.item(index)
            if item:
                item.setToolTip(tooltip)
            
    def _on_selection_changed(self, index):
        """Обработчик изменения выбора"""
        if index >= 0:
            self.stack_widget.setCurrentIndex(index)
            self.currentChanged.emit(index)
            
    def _expand_animated(self):
        """Анимированное расширение панели"""
        if not self.is_expanded:
            self.width_animation.stop()
            self.width_animation.setStartValue(self.list_container.width())
            self.width_animation.setEndValue(self.expanded_width)
            self.width_animation.start()
            self.is_expanded = True
            self.show_full_names()
            self._stop_scrolling()
            
    def _collapse_animated(self):
        """Анимированное сворачивание панели"""
        if self.is_expanded and not self.is_pinned:
            self._stop_scrolling()
            
            self.width_animation.stop()
            self.width_animation.setStartValue(self.list_container.width())
            self.width_animation.setEndValue(self.collapsed_width)
            self.width_animation.start()
            self.is_expanded = False
            self.show_short_names()
            
    def _expand_tabs_animated(self):
        """Совместимость со старым кодом"""
        self._expand_animated()
        
    def _collapse_tabs_animated(self):
        """Совместимость со старым кодом"""
        self._collapse_animated()
        
    def _set_bar_width(self, w):
        """Совместимость со старым кодом"""
        self.list_container.setFixedWidth(w)