"""
Продвинутое окно предпросмотра аргументов стратегии
Показывает детальную информацию при клике правой кнопкой мыши
"""

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                            QTextEdit, QFrame, QPushButton, QWidget,
                            QGraphicsDropShadowEffect, QApplication)
from PyQt6.QtCore import (Qt, QTimer, QPropertyAnimation, QEasingCurve, 
                          pyqtSignal, QPoint, QRect, QRectF)
from PyQt6.QtGui import QFont, QColor, QPainter, QPainterPath, QRegion, QPolygonF

from log import log


class ArgsPreviewDialog(QDialog):
    """Красивое окно предпросмотра аргументов стратегии с анимацией"""
    
    closed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Настройки окна
        self.setWindowFlags(
            Qt.WindowType.Popup |  # Используем Popup вместо ToolTip
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setModal(False)
        
        # Для анимации
        self.opacity_animation = QPropertyAnimation(self, b"windowOpacity")
        self.opacity_animation.setDuration(200)
        self.opacity_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        
        self.init_ui()
        
        # Начальная прозрачность
        self.setWindowOpacity(0.0)
        
    def init_ui(self):
        """Инициализация интерфейса"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Основной контейнер с тенью
        self.container = RoundedContainer()
        
        # Добавляем тень
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 100))
        shadow.setOffset(0, 5)
        self.container.setGraphicsEffect(shadow)
        
        # Layout контейнера
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(20, 15, 20, 15)
        container_layout.setSpacing(10)
        
        # Заголовок с кнопкой закрытия
        header_layout = QHBoxLayout()
        
        self.title_label = QLabel()
        self.title_label.setStyleSheet("""
            QLabel {
                color: #2196F3;
                font-size: 13pt;
                font-weight: bold;
                padding: 5px 0;
            }
        """)
        header_layout.addWidget(self.title_label)
        
        header_layout.addStretch()
        
        # Кнопка закрытия
        close_button = QPushButton("✕")
        close_button.setFixedSize(25, 25)
        close_button.setCursor(Qt.CursorShape.PointingHandCursor)
        close_button.clicked.connect(self.close_dialog)
        close_button.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #aaa;
                border: none;
                font-size: 16pt;
                font-weight: bold;
                padding: 0;
            }
            QPushButton:hover {
                color: #ff4444;
                background: rgba(255, 68, 68, 0.1);
                border-radius: 12px;
            }
        """)
        header_layout.addWidget(close_button)
        
        container_layout.addLayout(header_layout)
        
        # Описание
        self.description_label = QLabel()
        self.description_label.setWordWrap(True)
        self.description_label.setStyleSheet("""
            QLabel {
                color: #ccc;
                font-size: 9pt;
                padding: 5px 0;
            }
        """)
        container_layout.addWidget(self.description_label)
        
        # Автор (если есть)
        self.author_label = QLabel()
        self.author_label.setStyleSheet("""
            QLabel {
                color: #888;
                font-size: 8pt;
                font-style: italic;
            }
        """)
        self.author_label.hide()
        container_layout.addWidget(self.author_label)
        
        # Разделитель
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("""
            QFrame {
                background: #444;
                max-height: 1px;
                margin: 5px 0;
            }
        """)
        container_layout.addWidget(separator)
        
        # Заголовок для аргументов с кнопкой копирования
        args_header = QHBoxLayout()
        
        args_title = QLabel("⚙️ Аргументы запуска:")
        args_title.setStyleSheet("""
            QLabel {
                color: #ffa500;
                font-weight: bold;
                font-size: 10pt;
            }
        """)
        args_header.addWidget(args_title)
        
        args_header.addStretch()
        
        # Кнопка копирования
        self.copy_button = QPushButton("📋 Копировать")
        self.copy_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.copy_button.clicked.connect(self.copy_args)
        self.copy_button.setStyleSheet("""
            QPushButton {
                background: #333;
                color: #aaa;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 8pt;
            }
            QPushButton:hover {
                background: #3a3a3a;
                color: #fff;
                border: 1px solid #2196F3;
            }
            QPushButton:pressed {
                background: #2a2a2a;
            }
        """)
        args_header.addWidget(self.copy_button)
        
        container_layout.addLayout(args_header)
        
        # Текстовое поле с аргументами
        self.args_text = QTextEdit()
        self.args_text.setReadOnly(True)
        self.args_text.setStyleSheet("""
            QTextEdit {
                background: #1a1a1a;
                border: 1px solid #444;
                border-radius: 5px;
                color: #aaa;
                font-family: 'Consolas', 'Courier New', 'Monaco', monospace;
                font-size: 9pt;
                padding: 10px;
                selection-background-color: #2196F3;
                selection-color: #fff;
            }
            QTextEdit:focus {
                border: 1px solid #2196F3;
                outline: none;
            }
            QScrollBar:vertical {
                width: 8px;
                background: #1a1a1a;
                border: none;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #555;
                border-radius: 4px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background: #666;
            }
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        self.args_text.setMinimumHeight(100)
        self.args_text.setMaximumHeight(250)
        container_layout.addWidget(self.args_text)
        
        # Метка стратегии (если есть)
        self.label_widget = QLabel()
        self.label_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_widget.hide()
        container_layout.addWidget(self.label_widget)
        
        # Подсказка внизу
        hint_label = QLabel("💡 ESC или клик вне окна для закрытия • ПКМ для контекстного меню")
        hint_label.setStyleSheet("""
            QLabel {
                color: #666;
                font-size: 8pt;
                padding: 5px 0;
            }
        """)
        hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        container_layout.addWidget(hint_label)
        
        main_layout.addWidget(self.container)
        
        # Устанавливаем фиксированную ширину
        self.setFixedWidth(650)
        
    def set_strategy_data(self, strategy_data, strategy_id=None):
        """Устанавливает данные стратегии для отображения"""
        # Заголовок
        name = strategy_data.get('name', strategy_id or 'Стратегия')
        self.title_label.setText(f"🎯 {name}")
        
        # Описание
        description = strategy_data.get('description', '')
        if description:
            self.description_label.setText(description)
            self.description_label.show()
        else:
            self.description_label.hide()
        
        # Автор
        author = strategy_data.get('author')
        if author:
            self.author_label.setText(f"👤 Автор: {author}")
            self.author_label.show()
        else:
            self.author_label.hide()
        
        # Аргументы
        args = strategy_data.get('args', '')
        if args:
            formatted_args = self._format_args(args)
            self.args_text.setPlainText(formatted_args)
            self.args_text.show()
            self.copy_button.show()
            # Сохраняем оригинальные аргументы для копирования
            self.original_args = args
        else:
            self.args_text.hide()
            self.copy_button.hide()
            self.original_args = ""
        
        # Метка
        from .constants import LABEL_TEXTS, LABEL_COLORS
        label = strategy_data.get('label')
        if label and label in LABEL_TEXTS:
            self.label_widget.setText(f"⚡ {LABEL_TEXTS[label]}")
            self.label_widget.setStyleSheet(f"""
                QLabel {{
                    color: {LABEL_COLORS[label]};
                    font-weight: bold;
                    font-size: 9pt;
                    padding: 5px 10px;
                    border: 2px solid {LABEL_COLORS[label]};
                    border-radius: 5px;
                    background: rgba(33, 150, 243, 0.1);
                }}
            """)
            self.label_widget.show()
        else:
            self.label_widget.hide()
        
        # Подгоняем размер
        self.adjustSize()
        
    def _format_args(self, args):
        """Форматирует аргументы для лучшей читаемости"""
        # Разбиваем по основным параметрам
        parts = args.split(' --')
        if len(parts) > 1:
            formatted_lines = [parts[0]]  # Первая часть без --
            
            for part in parts[1:]:
                # Добавляем отступ и -- обратно
                formatted_lines.append(f"  --{part}")
            
            # Дополнительное форматирование для длинных строк
            result = []
            for line in formatted_lines:
                if len(line) > 80 and ',' in line:
                    # Разбиваем длинные списки параметров
                    prefix = line[:line.find('=') + 1] if '=' in line else ''
                    values = line[len(prefix):].split(',')
                    if len(values) > 1:
                        result.append(prefix + values[0] + ',')
                        for value in values[1:-1]:
                            result.append(' ' * (len(prefix) + 2) + value.strip() + ',')
                        result.append(' ' * (len(prefix) + 2) + values[-1].strip())
                    else:
                        result.append(line)
                else:
                    result.append(line)
            
            return '\n'.join(result)
        
        return args
    
    def copy_args(self):
        """Копирует аргументы в буфер обмена"""
        clipboard = QApplication.clipboard()
        clipboard.setText(self.original_args)
        
        # Меняем текст кнопки временно
        self.copy_button.setText("✅ Скопировано!")
        self.copy_button.setStyleSheet("""
            QPushButton {
                background: #2a4a2a;
                color: #4CAF50;
                border: 1px solid #4CAF50;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 8pt;
                font-weight: bold;
            }
        """)
        
        # Возвращаем обратно через 2 секунды
        QTimer.singleShot(2000, self._reset_copy_button)
        
        log(f"Аргументы скопированы в буфер обмена ({len(self.original_args)} символов)", "INFO")
    
    def _reset_copy_button(self):
        """Возвращает кнопку копирования в исходное состояние"""
        self.copy_button.setText("📋 Копировать")
        self.copy_button.setStyleSheet("""
            QPushButton {
                background: #333;
                color: #aaa;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 8pt;
            }
            QPushButton:hover {
                background: #3a3a3a;
                color: #fff;
                border: 1px solid #2196F3;
            }
            QPushButton:pressed {
                background: #2a2a2a;
            }
        """)
    
    def show_animated(self, pos=None):
        """Показывает окно с анимацией"""
        if pos:
            self.move(pos)
        
        self.show()
        
        # Анимация появления
        self.opacity_animation.setStartValue(0.0)
        self.opacity_animation.setEndValue(1.0)
        self.opacity_animation.start()
    
    def close_dialog(self):
        """Закрывает диалог с анимацией"""
        self.hide_animated()
    
    def hide_animated(self):
        """Скрывает окно с анимацией"""
        self.opacity_animation.setStartValue(1.0)
        self.opacity_animation.setEndValue(0.0)
        self.opacity_animation.finished.connect(self._on_hide_finished)
        self.opacity_animation.start()
    
    def _on_hide_finished(self):
        """Вызывается после завершения анимации скрытия"""
        self.hide()
        self.closed.emit()
    
    def keyPressEvent(self, event):
        """Обработка нажатий клавиш"""
        if event.key() == Qt.Key.Key_Escape:
            self.close_dialog()
        else:
            super().keyPressEvent(event)
    
    def mousePressEvent(self, event):
        """Закрываем при клике вне окна (для Popup)"""
        super().mousePressEvent(event)


class RoundedContainer(QFrame):
    """Контейнер с закругленными углами"""
    
    def __init__(self):
        super().__init__()
        self.setStyleSheet("""
            RoundedContainer {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #2a2a2a,
                    stop: 1 #252525
                );
                border: 2px solid #2196F3;
                border-radius: 12px;
            }
        """)


class StrategyPreviewManager:
    """Менеджер для управления показом окна предпросмотра по правой кнопке мыши"""
    
    _instance = None  # Singleton instance
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.preview_dialog = None
        return cls._instance
    
    def show_preview(self, widget, strategy_id, strategy_data):
        """Показывает окно предпросмотра"""
        # Закрываем предыдущее окно если открыто
        if self.preview_dialog and self.preview_dialog.isVisible():
            self.preview_dialog.close()
        
        # Создаем новое окно
        self.preview_dialog = ArgsPreviewDialog(widget)
        self.preview_dialog.closed.connect(self._on_preview_closed)
        
        # Устанавливаем данные
        self.preview_dialog.set_strategy_data(strategy_data, strategy_id)
        
        # Позиционируем окно рядом с курсором
        cursor_pos = widget.mapToGlobal(widget.rect().center())
        
        # Проверяем границы экрана
        screen = QApplication.primaryScreen()
        if screen:
            screen_rect = screen.availableGeometry()
            dialog_width = self.preview_dialog.width()
            dialog_height = self.preview_dialog.height()
            
            # Корректируем позицию если выходит за границы
            if cursor_pos.x() + dialog_width > screen_rect.right():
                cursor_pos.setX(screen_rect.right() - dialog_width - 10)
            
            if cursor_pos.y() + dialog_height > screen_rect.bottom():
                cursor_pos.setY(screen_rect.bottom() - dialog_height - 10)
        
        self.preview_dialog.show_animated(cursor_pos)
    
    def _on_preview_closed(self):
        """Вызывается при закрытии окна предпросмотра"""
        if self.preview_dialog:
            self.preview_dialog.deleteLater()
            self.preview_dialog = None
    
    def cleanup(self):
        """Очистка ресурсов"""
        if self.preview_dialog:
            self.preview_dialog.close()
            self.preview_dialog.deleteLater()
            self.preview_dialog = None


# Глобальный менеджер предпросмотра
preview_manager = StrategyPreviewManager()