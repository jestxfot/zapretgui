# strategy_menu/widgets.py

from PyQt6.QtWidgets import (QFrame, QHBoxLayout, QVBoxLayout, QLabel, 
                            QRadioButton, QWidget, QListWidgetItem)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QBrush

from .constants import LABEL_TEXTS, LABEL_COLORS


class CompactStrategyItem(QFrame):
    """Компактный виджет для отображения стратегии"""
    
    clicked = pyqtSignal(str)  # Сигнал при клике
    
    def __init__(self, strategy_id, strategy_data, parent=None):
        super().__init__(parent)
        self.strategy_id = strategy_id
        self.strategy_data = strategy_data
        self.is_selected = False
        
        self.setFrameStyle(QFrame.Shape.Box)
        self.setStyleSheet("""
            CompactStrategyItem {
                border: 1px solid #444;
                border-radius: 4px;
                padding: 0px;
                margin: 2px;
            }
            CompactStrategyItem:hover {
                background: #3a3a3a;
                border: 1px solid #555;
            }
        """)
        
        self.init_ui()
        
    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)
        
        # Радиокнопка
        self.radio = QRadioButton()
        self.radio.toggled.connect(self.on_radio_toggled)
        layout.addWidget(self.radio)
        
        # Контейнер для текста
        text_layout = QVBoxLayout()
        text_layout.setSpacing(0)
        
        # Название стратегии
        name_label = QLabel(self.strategy_data.get('name', self.strategy_id))
        name_label.setStyleSheet("font-weight: bold; font-size: 9pt;")
        text_layout.addWidget(name_label)
        
        # Краткое описание
        desc_text = self.strategy_data.get('description', '')
        if len(desc_text) > 60:
            desc_text = desc_text[:57] + "..."
        desc_label = QLabel(desc_text)
        desc_label.setStyleSheet("color: #888; font-size: 8pt;")
        text_layout.addWidget(desc_label)
        
        layout.addLayout(text_layout)
        layout.addStretch()
        
        # Метка
        label = self.strategy_data.get('label')
        if label and label in LABEL_TEXTS:
            label_widget = QLabel(LABEL_TEXTS[label])
            label_widget.setStyleSheet(
                f"color: {LABEL_COLORS[label]}; font-weight: bold; font-size: 8pt; "
                f"padding: 2px 6px; border: 1px solid {LABEL_COLORS[label]}; "
                f"border-radius: 3px;"
            )
            layout.addWidget(label_widget)
    
    def on_radio_toggled(self, checked):
        if checked:
            self.is_selected = True
            self.setStyleSheet("""
                CompactStrategyItem {
                    border: 2px solid #2196F3;
                    border-radius: 4px;
                    background: #2a2a3a;
                    padding: 0px;
                    margin: 2px;
                }
            """)
            self.clicked.emit(self.strategy_id)
        else:
            self.is_selected = False
            self.setStyleSheet("""
                CompactStrategyItem {
                    border: 1px solid #444;
                    border-radius: 4px;
                    padding: 0px;
                    margin: 2px;
                }
                CompactStrategyItem:hover {
                    background: #3a3a3a;
                    border: 1px solid #555;
                }
            """)
    
    def set_checked(self, checked):
        self.radio.setChecked(checked)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.radio.setChecked(True)
        super().mousePressEvent(event)


class ProviderHeaderItem(QListWidgetItem):
    """Специальный элемент для заголовка группы провайдера"""
    def __init__(self, provider_name):
        super().__init__(f"{provider_name}")
        font = self.font()
        font.setBold(True)
        self.setFont(font)
        self.setBackground(QBrush(QColor(240, 240, 240)))
        self.setFlags(Qt.ItemFlag.NoItemFlags)


class StrategyItem(QWidget):
    """Виджет для отображения элемента стратегии с цветной меткой"""
    def __init__(self, display_name, label=None, strategy_number=None, 
                 version_status=None, parent=None):
        super().__init__(parent)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(8)
        
        # Основной текст
        text = ""
        if strategy_number is not None:
            text = f"{strategy_number}. "
        text += display_name
        
        self.main_label = QLabel(text)
        self.main_label.setWordWrap(False)
        self.main_label.setMinimumHeight(20)
        self.main_label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        self.main_label.setStyleSheet("font-size: 10pt; margin: 0; padding: 0;")
        layout.addWidget(self.main_label)
        
        # Статус версии
        if version_status and version_status != 'current':
            version_text = ""
            version_color = ""
            
            if version_status == 'outdated':
                version_text = "ОБНОВИТЬ"
                version_color = "#FF6600"
            elif version_status == 'not_downloaded':
                version_text = "НЕ СКАЧАНА"
                version_color = "#CC0000"
            elif version_status == 'unknown':
                version_text = "?"
                version_color = "#888888"
                
            if version_text:
                self.version_label = QLabel(version_text)
                self.version_label.setStyleSheet(
                    f"color: {version_color}; font-weight: bold; font-size: 8pt; "
                    f"margin: 0; padding: 2px 4px; "
                    f"border: 1px solid {version_color}; border-radius: 3px;"
                )
                self.version_label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignCenter)
                self.version_label.setMinimumHeight(16)
                layout.addWidget(self.version_label)
        
        # Метка
        if label and label in LABEL_TEXTS:
            self.tag_label = QLabel(LABEL_TEXTS[label])
            self.tag_label.setStyleSheet(
                f"color: {LABEL_COLORS[label]}; font-weight: bold; font-size: 9pt; "
                f"margin: 0; padding: 0;"
            )
            self.tag_label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight)
            self.tag_label.setMinimumHeight(20)
            layout.addWidget(self.tag_label)
            
        layout.addStretch()
        self.setMinimumHeight(30)