# ui/pages/base_page.py
"""Базовый класс для страниц"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QScrollArea, QFrame
from PyQt6.QtGui import QFont


class BasePage(QScrollArea):
    """Базовый класс для страниц контента"""
    
    def __init__(self, title: str, subtitle: str = "", parent=None):
        super().__init__(parent)
        self.parent_app = parent
        
        # Настройка ScrollArea
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setStyleSheet("""
            QScrollArea {
                background-color: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background: rgba(255, 255, 255, 0.05);
                width: 8px;
                border-radius: 4px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 0.2);
                border-radius: 4px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(255, 255, 255, 0.3);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0;
            }
        """)
        
        # Контейнер контента (с явным родителем!)
        self.content = QWidget(self)  # ✅ Родитель = self (QScrollArea)
        self.content.setStyleSheet("background-color: transparent;")
        self.setWidget(self.content)
        
        # Основной layout
        self.layout = QVBoxLayout(self.content)
        self.layout.setContentsMargins(32, 24, 32, 24)
        self.layout.setSpacing(16)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # Заголовок страницы
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 28px;
                font-weight: 600;
                font-family: 'Segoe UI Variable Display', 'Segoe UI', sans-serif;
                padding-bottom: 4px;
            }
        """)
        self.layout.addWidget(self.title_label)
        
        # Подзаголовок
        if subtitle:
            self.subtitle_label = QLabel(subtitle)
            self.subtitle_label.setStyleSheet("""
                QLabel {
                    color: rgba(255, 255, 255, 0.6);
                    font-size: 13px;
                    padding-bottom: 16px;
                }
            """)
            self.subtitle_label.setWordWrap(True)
            self.layout.addWidget(self.subtitle_label)
        
    def add_widget(self, widget: QWidget):
        """Добавляет виджет на страницу"""
        self.layout.addWidget(widget)
        
    def add_spacing(self, height: int = 16):
        """Добавляет вертикальный отступ"""
        from PyQt6.QtWidgets import QSpacerItem, QSizePolicy
        spacer = QSpacerItem(0, height, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        self.layout.addItem(spacer)
        
    def add_section_title(self, text: str, return_widget: bool = False):
        """Добавляет заголовок секции"""
        label = QLabel(text)
        label.setStyleSheet("""
            QLabel {
                color: rgba(255, 255, 255, 0.8);
                font-size: 13px;
                font-weight: 600;
                padding-top: 8px;
                padding-bottom: 4px;
            }
        """)
        self.layout.addWidget(label)
        if return_widget:
            return label

