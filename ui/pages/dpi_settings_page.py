# ui/pages/dpi_settings_page.py
"""Страница настроек DPI"""

from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, pyqtProperty, QRectF, pyqtSignal, QTimer
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QFrame, QCheckBox, QSpinBox, QComboBox)
from PyQt6.QtGui import QPainter, QColor, QPainterPath, QFont
import qtawesome as qta

from .base_page import BasePage
from ui.sidebar import SettingsCard, ActionButton
from log import log


class Win11ToggleSwitch(QCheckBox):
    """Toggle Switch в стиле Windows 11"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(44, 22)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self._circle_position = 4.0
        self._color_blend = 0.0  # Для совместимости с servers_page версией
        
        self._animation = QPropertyAnimation(self, b"circle_position", self)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._animation.setDuration(150)
        
        self.stateChanged.connect(self._animate)
        
    def _get_circle_position(self):
        return self._circle_position
        
    def _set_circle_position(self, pos):
        self._circle_position = pos
        self.update()
        
    circle_position = pyqtProperty(float, _get_circle_position, _set_circle_position)
    
    def _get_color_blend(self):
        return self._color_blend
    
    def _set_color_blend(self, value):
        self._color_blend = value
        self.update()
    
    color_blend = pyqtProperty(float, _get_color_blend, _set_color_blend)
    
    def _animate(self, state):
        if not self._animation:
            return
        self._animation.stop()
        if state:
            self._animation.setStartValue(self._circle_position)
            self._animation.setEndValue(self.width() - 18)
        else:
            self._animation.setStartValue(self._circle_position)
            self._animation.setEndValue(4.0)
        self._animation.start()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Фон
        if self.isChecked():
            bg_color = QColor("#60cdff")
        else:
            bg_color = QColor(80, 80, 80)
            
        path = QPainterPath()
        path.addRoundedRect(QRectF(0, 0, self.width(), self.height()), 11, 11)
        painter.fillPath(path, bg_color)
        
        # Рамка
        painter.setPen(QColor(100, 100, 100) if not self.isChecked() else Qt.GlobalColor.transparent)
        painter.drawPath(path)
        
        # Круг
        circle_color = QColor("#ffffff")
        painter.setBrush(circle_color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QRectF(self._circle_position, 4, 14, 14))
        
        painter.end()
        
    def hitButton(self, pos):
        return self.rect().contains(pos)


class Win11ToggleRow(QWidget):
    """Строка с toggle switch в стиле Windows 11"""
    
    toggled = pyqtSignal(bool)
    
    def __init__(self, icon_name: str, title: str, description: str = "", 
                 icon_color: str = "#60cdff", parent=None):
        super().__init__(parent)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 6, 0, 6)
        layout.setSpacing(12)
        
        # Иконка
        icon_label = QLabel()
        icon_label.setPixmap(qta.icon(icon_name, color=icon_color).pixmap(18, 18))
        icon_label.setFixedSize(22, 22)
        layout.addWidget(icon_label)
        
        # Текст
        text_layout = QVBoxLayout()
        text_layout.setSpacing(1)
        text_layout.setContentsMargins(0, 0, 0, 0)
        
        title_label = QLabel(title)
        title_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 13px;
                font-weight: 500;
            }
        """)
        text_layout.addWidget(title_label)
        
        if description:
            desc_label = QLabel(description)
            desc_label.setWordWrap(True)
            desc_label.setStyleSheet("""
                QLabel {
                    color: rgba(255, 255, 255, 0.5);
                    font-size: 11px;
                }
            """)
            text_layout.addWidget(desc_label)
            
        layout.addLayout(text_layout, 1)
        
        # Toggle
        self.toggle = Win11ToggleSwitch()
        self.toggle.toggled.connect(self.toggled.emit)
        layout.addWidget(self.toggle)
        
    def setChecked(self, checked: bool, block_signals: bool = False):
        if block_signals:
            self.toggle.blockSignals(True)
        self.toggle.setChecked(checked)
        if block_signals:
            self.toggle.blockSignals(False)
            # Обновляем позицию круга без анимации
            self.toggle._circle_position = (self.toggle.width() - 18) if checked else 4.0
            self.toggle.update()
        
    def isChecked(self) -> bool:
        return self.toggle.isChecked()


class Win11RadioOption(QWidget):
    """Радио-опция в стиле Windows 11"""
    
    clicked = pyqtSignal()
    
    def __init__(self, title: str, description: str, icon_name: str = None, 
                 icon_color: str = "#60cdff", recommended: bool = False, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self._selected = False
        self._hover = False
        self._recommended = recommended
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)
        
        # Радио-круг
        self.radio_circle = QWidget()
        self.radio_circle.setFixedSize(20, 20)
        layout.addWidget(self.radio_circle)
        
        # Иконка (опционально)
        if icon_name:
            icon_label = QLabel()
            icon_label.setPixmap(qta.icon(icon_name, color=icon_color).pixmap(24, 24))
            icon_label.setFixedSize(28, 28)
            layout.addWidget(icon_label)
        
        # Текстовый блок
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        text_layout.setContentsMargins(0, 0, 0, 0)
        
        # Заголовок с бейджем
        title_layout = QHBoxLayout()
        title_layout.setSpacing(8)
        title_layout.setContentsMargins(0, 0, 0, 0)
        
        title_label = QLabel(title)
        title_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 14px;
                font-weight: 600;
            }
        """)
        title_layout.addWidget(title_label)
        
        if recommended:
            badge = QLabel("рекомендуется")
            badge.setStyleSheet("""
                QLabel {
                    color: #000000;
                    background-color: #60cdff;
                    font-size: 10px;
                    font-weight: 600;
                    padding: 2px 6px;
                    border-radius: 3px;
                }
            """)
            title_layout.addWidget(badge)
        
        title_layout.addStretch()
        text_layout.addLayout(title_layout)
        
        # Описание
        desc_label = QLabel(description)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("""
            QLabel {
                color: rgba(255, 255, 255, 0.55);
                font-size: 12px;
                line-height: 1.3;
            }
        """)
        text_layout.addWidget(desc_label)
        
        layout.addLayout(text_layout, 1)
        
        self._update_style()
        
    def setSelected(self, selected: bool):
        self._selected = selected
        self._update_style()
        
    def isSelected(self) -> bool:
        return self._selected
        
    def _update_style(self):
        if self._selected:
            bg = "rgba(96, 205, 255, 0.15)"
            border = "rgba(96, 205, 255, 0.6)"
        elif self._hover:
            bg = "rgba(255, 255, 255, 0.06)"
            border = "rgba(255, 255, 255, 0.15)"
        else:
            bg = "rgba(255, 255, 255, 0.03)"
            border = "rgba(255, 255, 255, 0.08)"
            
        self.setStyleSheet(f"""
            Win11RadioOption {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 8px;
            }}
        """)
        self.update()
        
    def enterEvent(self, event):
        self._hover = True
        self._update_style()
        super().enterEvent(event)
        
    def leaveEvent(self, event):
        self._hover = False
        self._update_style()
        super().leaveEvent(event)
        
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)
        
    def paintEvent(self, event):
        super().paintEvent(event)
        
        # Рисуем радио-круг
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Позиция круга
        circle_x = 12 + 10  # margin + half width
        circle_y = self.height() // 2
        
        # Внешний круг
        if self._selected:
            painter.setPen(QColor("#60cdff"))
            painter.setBrush(Qt.BrushStyle.NoBrush)
        else:
            painter.setPen(QColor(100, 100, 100))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            
        painter.drawEllipse(circle_x - 8, circle_y - 8, 16, 16)
        
        # Внутренний круг (если выбран)
        if self._selected:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor("#60cdff"))
            painter.drawEllipse(circle_x - 4, circle_y - 4, 8, 8)
            
        painter.end()


class Win11NumberRow(QWidget):
    """Строка с числовым вводом в стиле Windows 11"""
    
    valueChanged = pyqtSignal(int)
    
    def __init__(self, icon_name: str, title: str, description: str = "", 
                 icon_color: str = "#60cdff", min_val: int = 0, max_val: int = 999,
                 default_val: int = 10, suffix: str = "", parent=None):
        super().__init__(parent)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 6, 0, 6)
        layout.setSpacing(12)
        
        # Иконка
        icon_label = QLabel()
        icon_label.setPixmap(qta.icon(icon_name, color=icon_color).pixmap(18, 18))
        icon_label.setFixedSize(22, 22)
        layout.addWidget(icon_label)
        
        # Текст
        text_layout = QVBoxLayout()
        text_layout.setSpacing(1)
        text_layout.setContentsMargins(0, 0, 0, 0)
        
        title_label = QLabel(title)
        title_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 13px;
                font-weight: 500;
            }
        """)
        text_layout.addWidget(title_label)
        
        if description:
            desc_label = QLabel(description)
            desc_label.setWordWrap(True)
            desc_label.setStyleSheet("""
                QLabel {
                    color: rgba(255, 255, 255, 0.5);
                    font-size: 11px;
                }
            """)
            text_layout.addWidget(desc_label)
            
        layout.addLayout(text_layout, 1)
        
        # SpinBox
        self.spinbox = QSpinBox()
        self.spinbox.setMinimum(min_val)
        self.spinbox.setMaximum(max_val)
        self.spinbox.setValue(default_val)
        self.spinbox.setSuffix(suffix)
        self.spinbox.setFixedWidth(80)
        self.spinbox.setFixedHeight(28)
        self.spinbox.setStyleSheet("""
            QSpinBox {
                background-color: rgba(255, 255, 255, 0.06);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 4px;
                padding: 2px 10px;
                color: #ffffff;
                font-size: 12px;
            }
            QSpinBox:hover {
                background-color: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(96, 205, 255, 0.3);
            }
            QSpinBox:focus {
                border: 1px solid #60cdff;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                width: 0px;
                height: 0px;
                border: none;
                background: none;
            }
            QSpinBox::up-arrow, QSpinBox::down-arrow {
                width: 0px;
                height: 0px;
            }
        """)
        self.spinbox.valueChanged.connect(self.valueChanged.emit)
        layout.addWidget(self.spinbox)
        
    def setValue(self, value: int, block_signals: bool = False):
        if block_signals:
            self.spinbox.blockSignals(True)
        self.spinbox.setValue(value)
        if block_signals:
            self.spinbox.blockSignals(False)

    def value(self) -> int:
        return self.spinbox.value()


class Win11ComboRow(QWidget):
    """Строка с выпадающим списком в стиле Windows 11"""

    currentIndexChanged = pyqtSignal(int)
    currentTextChanged = pyqtSignal(str)

    def __init__(self, icon_name: str, title: str, description: str = "",
                 icon_color: str = "#60cdff", items: list = None, parent=None):
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 6, 0, 6)
        layout.setSpacing(12)

        # Иконка
        icon_label = QLabel()
        icon_label.setPixmap(qta.icon(icon_name, color=icon_color).pixmap(18, 18))
        icon_label.setFixedSize(22, 22)
        layout.addWidget(icon_label)

        # Текст
        text_layout = QVBoxLayout()
        text_layout.setSpacing(1)
        text_layout.setContentsMargins(0, 0, 0, 0)

        title_label = QLabel(title)
        title_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 13px;
                font-weight: 500;
            }
        """)
        text_layout.addWidget(title_label)

        if description:
            desc_label = QLabel(description)
            desc_label.setWordWrap(True)
            desc_label.setStyleSheet("""
                QLabel {
                    color: rgba(255, 255, 255, 0.5);
                    font-size: 11px;
                }
            """)
            text_layout.addWidget(desc_label)

        layout.addLayout(text_layout, 1)

        # ComboBox
        self.combo = QComboBox()
        self.combo.setFixedWidth(160)
        self.combo.setFixedHeight(28)
        self.combo.setStyleSheet(f"""
            QComboBox {{
                background-color: rgba(255, 255, 255, 0.06);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 4px;
                padding: 2px 10px;
                color: #ffffff;
                font-size: 12px;
            }}
            QComboBox:hover {{
                background-color: #33444E;
                border: 1px solid rgba(51, 68, 78, 0.8);
            }}
            QComboBox:focus {{
                border: 1px solid {icon_color};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 5px solid #ffffff;
                margin-right: 5px;
            }}
            QComboBox QAbstractItemView {{
                background-color: #2d2d2d;
                border: 1px solid rgba(255, 255, 255, 0.1);
                selection-background-color: #33444E;
                color: #ffffff;
                outline: none;
            }}
            QComboBox QAbstractItemView::item {{
                background-color: transparent;
                padding: 4px 8px;
            }}
            QComboBox QAbstractItemView::item:hover {{
                background-color: #3d5058;
            }}
            QComboBox QAbstractItemView::item:selected {{
                background-color: #33444E;
            }}
            QScrollBar:vertical {{
                width: 0px;
            }}
            QScrollBar:horizontal {{
                height: 0px;
            }}
            QComboBox::indicator {{
                width: 0px;
                height: 0px;
            }}
        """)

        if items:
            for text, data in items:
                self.combo.addItem(text, data)

        self.combo.currentIndexChanged.connect(self.currentIndexChanged.emit)
        self.combo.currentTextChanged.connect(self.currentTextChanged.emit)
        layout.addWidget(self.combo)

    def setCurrentData(self, data, block_signals: bool = False):
        """Устанавливает текущий элемент по данным"""
        if block_signals:
            self.combo.blockSignals(True)
        index = self.combo.findData(data)
        if index >= 0:
            self.combo.setCurrentIndex(index)
        if block_signals:
            self.combo.blockSignals(False)

    def currentData(self):
        """Возвращает данные текущего элемента"""
        return self.combo.currentData()

    def setCurrentIndex(self, index: int, block_signals: bool = False):
        if block_signals:
            self.combo.blockSignals(True)
        self.combo.setCurrentIndex(index)
        if block_signals:
            self.combo.blockSignals(False)

    def currentIndex(self) -> int:
        return self.combo.currentIndex()


class DpiSettingsPage(BasePage):
    """Страница настроек DPI"""

    launch_method_changed = pyqtSignal(str)
    filters_changed = pyqtSignal()  # Сигнал при изменении фильтров
    
    def __init__(self, parent=None):
        super().__init__("Настройки DPI", "Параметры обхода блокировок", parent)
        self._build_ui()
        self._load_settings()
        
    def _build_ui(self):
        """Строит UI страницы"""
        
        # Метод запуска
        method_card = SettingsCard("Метод запуска стратегий")
        method_layout = QVBoxLayout()
        method_layout.setSpacing(10)
        
        method_desc = QLabel("Выберите способ запуска обхода блокировок")
        method_desc.setStyleSheet("color: rgba(255, 255, 255, 0.6); font-size: 12px;")
        method_layout.addWidget(method_desc)

        # ═══════════════════════════════════════
        # ZAPRET 2 (winws2.exe)
        # ═══════════════════════════════════════
        zapret2_header = QLabel("Zapret 2 (winws2.exe)")
        zapret2_header.setStyleSheet("""
            QLabel {
                color: #60cdff;
                font-size: 13px;
                font-weight: 600;
                padding: 8px 0 4px 0;
            }
        """)
        method_layout.addWidget(zapret2_header)

        # Zapret 2 (direct) - рекомендуется
        self.method_direct = Win11RadioOption(
            "Zapret 2",
            "Прямой запуск с гибкими настройками. Поддерживает фильтры трафика и раздельные стратегии.",
            icon_name="mdi.rocket-launch",
            icon_color="#60cdff",
            recommended=True
        )
        self.method_direct.clicked.connect(lambda: self._select_method("direct_zapret2"))
        method_layout.addWidget(self.method_direct)

        # Оркестратор Zapret 2 (direct с другим набором стратегий)
        self.method_direct_zapret2_orchestra = Win11RadioOption(
            "Оркестраторный Zapret 2",
            "Запуск Zapret 2 со стратегиями оркестратора внутри каждого профиля. Позволяет настроить для каждого сайта свой оркерстратор. Не сохраняет состояние для повышенной агрессии обхода.",
            icon_name="mdi.brain",
            icon_color="#9c27b0"
        )
        self.method_direct_zapret2_orchestra.clicked.connect(lambda: self._select_method("direct_zapret2_orchestra"))
        method_layout.addWidget(self.method_direct_zapret2_orchestra)

        # Оркестр (auto-learning)
        self.method_orchestra = Win11RadioOption(
            "Оркестратор v0.9.6 (Beta)",
            "Автоматическое обучение. Система сама подбирает лучшие стратегии для каждого домена. Запоминает результаты между запусками.",
            icon_name="mdi.brain",
            icon_color="#9c27b0"
        )
        self.method_orchestra.clicked.connect(lambda: self._select_method("orchestra"))
        method_layout.addWidget(self.method_orchestra)

        # ───────────────────────────────────────
        # ZAPRET 1 (winws.exe)
        # ───────────────────────────────────────
        zapret1_header = QLabel("Zapret 1 (winws.exe)")
        zapret1_header.setStyleSheet("""
            QLabel {
                color: #ff9800;
                font-size: 13px;
                font-weight: 600;
                padding: 12px 0 4px 0;
            }
        """)
        method_layout.addWidget(zapret1_header)

        # Zapret 1 Direct (прямой запуск winws.exe с JSON стратегиями)
        self.method_direct_zapret1 = Win11RadioOption(
            "Zapret 1 Direct",
            "Прямой запуск Zapret 1 (winws.exe) с гибкими настройками как у Zapret 2. Не использует Lua.",
            icon_name="mdi.rocket-launch-outline",
            icon_color="#ff9800"
        )
        self.method_direct_zapret1.clicked.connect(lambda: self._select_method("direct_zapret1"))
        method_layout.addWidget(self.method_direct_zapret1)

        # Zapret 1 (bat)
        self.method_bat = Win11RadioOption(
            "Zapret 1 BAT",
            "Запуск через .bat файлы. Классический метод, использует готовые скрипты из папки zapret.",
            icon_name="mdi.file-code",
            icon_color="#ff9800"
        )
        self.method_bat.clicked.connect(lambda: self._select_method("bat"))
        method_layout.addWidget(self.method_bat)

        # Разделитель 2
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.Shape.HLine)
        separator2.setStyleSheet("background-color: rgba(255, 255, 255, 0.08); margin: 8px 0;")
        separator2.setFixedHeight(1)
        method_layout.addWidget(separator2)

        # Перезапуск Discord (только для Zapret 1/2)
        self.discord_restart_container = QWidget()
        discord_layout = QVBoxLayout(self.discord_restart_container)
        discord_layout.setContentsMargins(0, 0, 0, 0)
        discord_layout.setSpacing(0)

        self.discord_restart_toggle = Win11ToggleRow(
            "mdi.discord", "Перезапуск Discord",
            "Автоперезапуск при смене стратегии", "#7289da")
        discord_layout.addWidget(self.discord_restart_toggle)
        method_layout.addWidget(self.discord_restart_container)

        # ─────────────────────────────────────────────────────────────────────
        # НАСТРОЙКИ ОРКЕСТРАТОРА (только в режиме оркестратора)
        # ─────────────────────────────────────────────────────────────────────
        self.orchestra_settings_container = QWidget()
        orchestra_settings_layout = QVBoxLayout(self.orchestra_settings_container)
        orchestra_settings_layout.setContentsMargins(0, 0, 0, 0)
        orchestra_settings_layout.setSpacing(6)

        orchestra_label = QLabel("Настройки оркестратора")
        orchestra_label.setStyleSheet("color: #9c27b0; font-size: 12px; font-weight: 600;")
        orchestra_settings_layout.addWidget(orchestra_label)

        self.strict_detection_toggle = Win11ToggleRow(
            "mdi.check-decagram", "Строгий режим детекции",
            "HTTP 200 + проверка блок-страниц", "#4CAF50")
        orchestra_settings_layout.addWidget(self.strict_detection_toggle)

        self.debug_file_toggle = Win11ToggleRow(
            "mdi.file-document-outline", "Сохранять debug файл",
            "Сырой debug файл для отладки", "#8a2be2")
        orchestra_settings_layout.addWidget(self.debug_file_toggle)

        self.auto_restart_discord_toggle = Win11ToggleRow(
            "mdi.discord", "Авторестарт Discord при FAIL",
            "Перезапуск Discord при неудачном обходе", "#7289da")
        orchestra_settings_layout.addWidget(self.auto_restart_discord_toggle)

        # Количество фейлов для рестарта Discord
        self.discord_fails_spin = Win11NumberRow(
            "mdi.discord", "Фейлов для рестарта Discord",
            "Сколько FAIL подряд для перезапуска Discord", "#7289da",
            min_val=1, max_val=10, default_val=3)
        orchestra_settings_layout.addWidget(self.discord_fails_spin)

        # Успехов для LOCK (сколько успехов подряд для закрепления стратегии)
        self.lock_successes_spin = Win11NumberRow(
            "mdi.lock", "Успехов для LOCK",
            "Количество успешных обходов для закрепления стратегии", "#4CAF50",
            min_val=1, max_val=10, default_val=3)
        orchestra_settings_layout.addWidget(self.lock_successes_spin)

        # Ошибок для AUTO-UNLOCK (сколько ошибок подряд для разблокировки)
        self.unlock_fails_spin = Win11NumberRow(
            "mdi.lock-open", "Ошибок для AUTO-UNLOCK",
            "Количество ошибок для автоматической разблокировки стратегии", "#FF5722",
            min_val=1, max_val=10, default_val=3)
        orchestra_settings_layout.addWidget(self.unlock_fails_spin)

        method_layout.addWidget(self.orchestra_settings_container)

        method_card.add_layout(method_layout)
        self.layout.addWidget(method_card)
        
        # ═══════════════════════════════════════════════════════════════════════
        # ДОПОЛНИТЕЛЬНЫЕ НАСТРОЙКИ
        # ═══════════════════════════════════════════════════════════════════════
        self.advanced_card = SettingsCard("ДОПОЛНИТЕЛЬНЫЕ НАСТРОЙКИ")
        advanced_layout = QVBoxLayout()
        advanced_layout.setSpacing(6)
        
        # Описание
        advanced_desc = QLabel("⚠ Изменяйте только если знаете что делаете")
        advanced_desc.setStyleSheet("color: #ff9800; font-size: 11px; padding-bottom: 8px;")
        advanced_layout.addWidget(advanced_desc)
        
        # WSSize
        self.wssize_toggle = Win11ToggleRow(
            "fa5s.ruler-horizontal", "Включить --wssize", 
            "Добавляет параметр размера окна TCP", "#9c27b0")
        advanced_layout.addWidget(self.wssize_toggle)
        
        # Debug лог
        self.debug_log_toggle = Win11ToggleRow(
            "mdi.file-document-outline", "Включить лог-файл (--debug)", 
            "Записывает логи winws в папку logs", "#00bcd4")
        advanced_layout.addWidget(self.debug_log_toggle)
        
        self.advanced_card.add_layout(advanced_layout)
        self.layout.addWidget(self.advanced_card)
        
        self.layout.addStretch()
        
    def _load_settings(self):
        """Загружает настройки"""
        try:
            from strategy_menu import get_strategy_launch_method
            method = get_strategy_launch_method()

            # Устанавливаем выбранный метод
            self._update_method_selection(method)

            # Discord restart setting
            self._load_discord_restart_setting()

            # Orchestra settings
            self._load_orchestra_settings()

            self._update_filters_visibility()
            self._load_filter_settings()

        except Exception as e:
            log(f"Ошибка загрузки настроек DPI: {e}", "WARNING")
    
    def _update_method_selection(self, method: str):
        """Обновляет визуальное состояние выбора метода"""
        self.method_direct.setSelected(method == "direct_zapret2")
        self.method_direct_zapret2_orchestra.setSelected(method == "direct_zapret2_orchestra")
        self.method_direct_zapret1.setSelected(method == "direct_zapret1")
        self.method_bat.setSelected(method == "bat")
        self.method_orchestra.setSelected(method == "orchestra")
    
    def _select_method(self, method: str):
        """Обработчик выбора метода"""
        try:
            from strategy_menu import (
                set_strategy_launch_method, get_strategy_launch_method, invalidate_direct_selections_cache,
                is_direct_zapret2_orchestra_initialized, set_direct_zapret2_orchestra_initialized, clear_direct_zapret2_orchestra_strategies
            )
            from strategy_menu.strategies_registry import registry

            # Запоминаем предыдущий метод для определения необходимости перезагрузки стратегий
            previous_method = get_strategy_launch_method()

            # ✅ При ПЕРВОМ переключении на direct_zapret2_orchestra - сбрасываем все стратегии в "none"
            if method == "direct_zapret2_orchestra" and not is_direct_zapret2_orchestra_initialized():
                log("🆕 Первая инициализация режима DirectOrchestra - сброс всех стратегий в 'none'", "INFO")
                clear_direct_zapret2_orchestra_strategies()
                set_direct_zapret2_orchestra_initialized(True)

            set_strategy_launch_method(method)
            self._update_method_selection(method)
            self._update_filters_visibility()

            # Перезагружаем стратегии если меняется набор стратегий
            # (например с direct на direct_zapret2_orchestra, direct_zapret1 или наоборот)
            direct_methods = ("direct_zapret2", "direct_zapret2_orchestra", "direct_zapret1")
            if previous_method in direct_methods or method in direct_methods:
                if previous_method != method:
                    log(f"Смена метода {previous_method} -> {method}, перезагрузка стратегий...", "INFO")
                    # Сбрасываем кэш выборов - они будут перечитаны из реестра
                    invalidate_direct_selections_cache()
                    registry.reload_strategies()

            self.launch_method_changed.emit(method)
        except Exception as e:
            log(f"Ошибка смены метода: {e}", "ERROR")
    
    def _load_discord_restart_setting(self):
        """Загружает настройку перезапуска Discord"""
        try:
            from discord.discord_restart import get_discord_restart_setting, set_discord_restart_setting
            
            # Загружаем текущее значение (по умолчанию True), блокируя сигналы
            self.discord_restart_toggle.setChecked(get_discord_restart_setting(default=True), block_signals=True)
            
            # Подключаем сигнал сохранения
            self.discord_restart_toggle.toggled.connect(self._on_discord_restart_changed)
            
        except Exception as e:
            log(f"Ошибка загрузки настройки Discord: {e}", "WARNING")
    
    def _on_discord_restart_changed(self, enabled: bool):
        """Обработчик изменения настройки перезапуска Discord"""
        try:
            from discord.discord_restart import set_discord_restart_setting
            set_discord_restart_setting(enabled)
            status = "включён" if enabled else "отключён"
            log(f"Автоперезапуск Discord {status}", "INFO")
        except Exception as e:
            log(f"Ошибка сохранения настройки Discord: {e}", "ERROR")

    def _load_orchestra_settings(self):
        """Загружает настройки оркестратора"""
        try:
            from config import REGISTRY_PATH
            from config.reg import reg

            # Строгий режим детекции (по умолчанию включён)
            saved_strict = reg(f"{REGISTRY_PATH}\\Orchestra", "StrictDetection")
            self.strict_detection_toggle.setChecked(saved_strict is None or bool(saved_strict), block_signals=True)
            self.strict_detection_toggle.toggled.connect(self._on_strict_detection_changed)

            # Debug файл (по умолчанию выключен)
            saved_debug = reg(f"{REGISTRY_PATH}\\Orchestra", "KeepDebugFile")
            self.debug_file_toggle.setChecked(bool(saved_debug), block_signals=True)
            self.debug_file_toggle.toggled.connect(self._on_debug_file_changed)

            # Авторестарт при Discord FAIL (по умолчанию включён)
            saved_auto_restart = reg(f"{REGISTRY_PATH}\\Orchestra", "AutoRestartOnDiscordFail")
            self.auto_restart_discord_toggle.setChecked(saved_auto_restart is None or bool(saved_auto_restart), block_signals=True)
            self.auto_restart_discord_toggle.toggled.connect(self._on_auto_restart_discord_changed)

            # Количество фейлов для рестарта Discord (по умолчанию 3)
            saved_discord_fails = reg(f"{REGISTRY_PATH}\\Orchestra", "DiscordFailsForRestart")
            if saved_discord_fails is not None:
                self.discord_fails_spin.setValue(int(saved_discord_fails))
            self.discord_fails_spin.valueChanged.connect(self._on_discord_fails_changed)

            # Успехов для LOCK (по умолчанию 3)
            saved_lock_successes = reg(f"{REGISTRY_PATH}\\Orchestra", "LockSuccesses")
            if saved_lock_successes is not None:
                self.lock_successes_spin.setValue(int(saved_lock_successes))
            self.lock_successes_spin.valueChanged.connect(self._on_lock_successes_changed)

            # Ошибок для AUTO-UNLOCK (по умолчанию 3)
            saved_unlock_fails = reg(f"{REGISTRY_PATH}\\Orchestra", "UnlockFails")
            if saved_unlock_fails is not None:
                self.unlock_fails_spin.setValue(int(saved_unlock_fails))
            self.unlock_fails_spin.valueChanged.connect(self._on_unlock_fails_changed)

        except Exception as e:
            log(f"Ошибка загрузки настроек оркестратора: {e}", "WARNING")

    def _on_strict_detection_changed(self, enabled: bool):
        """Обработчик изменения строгого режима детекции"""
        try:
            from config import REGISTRY_PATH
            from config.reg import reg

            reg(f"{REGISTRY_PATH}\\Orchestra", "StrictDetection", 1 if enabled else 0)
            log(f"Строгий режим детекции: {'включён' if enabled else 'выключен'}", "INFO")

            # Обновляем orchestra_runner если запущен
            app = self._get_app()
            if app and hasattr(app, 'orchestra_runner') and app.orchestra_runner:
                app.orchestra_runner.set_strict_detection(enabled)

        except Exception as e:
            log(f"Ошибка сохранения настройки строгого режима: {e}", "ERROR")

    def _on_debug_file_changed(self, enabled: bool):
        """Обработчик изменения сохранения debug файла"""
        try:
            from config import REGISTRY_PATH
            from config.reg import reg

            reg(f"{REGISTRY_PATH}\\Orchestra", "KeepDebugFile", 1 if enabled else 0)
            log(f"Сохранение debug файла: {'включено' if enabled else 'выключено'}", "INFO")

        except Exception as e:
            log(f"Ошибка сохранения настройки debug файла: {e}", "ERROR")

    def _on_auto_restart_discord_changed(self, enabled: bool):
        """Обработчик изменения авторестарта при Discord FAIL"""
        try:
            from config import REGISTRY_PATH
            from config.reg import reg

            reg(f"{REGISTRY_PATH}\\Orchestra", "AutoRestartOnDiscordFail", 1 if enabled else 0)
            log(f"Авторестарт при Discord FAIL: {'включён' if enabled else 'выключен'}", "INFO")

            # Обновляем orchestra_runner если запущен
            app = self._get_app()
            if app and hasattr(app, 'orchestra_runner') and app.orchestra_runner:
                app.orchestra_runner.auto_restart_on_discord_fail = enabled

        except Exception as e:
            log(f"Ошибка сохранения настройки авторестарта Discord: {e}", "ERROR")

    def _on_discord_fails_changed(self, value: int):
        """Обработчик изменения количества фейлов для рестарта Discord"""
        try:
            from config import REGISTRY_PATH
            from config.reg import reg

            reg(f"{REGISTRY_PATH}\\Orchestra", "DiscordFailsForRestart", value)
            log(f"Фейлов для рестарта Discord: {value}", "INFO")

            # Обновляем orchestra_runner если запущен
            app = self._get_app()
            if app and hasattr(app, 'orchestra_runner') and app.orchestra_runner:
                app.orchestra_runner.discord_fails_for_restart = value

        except Exception as e:
            log(f"Ошибка сохранения настройки DiscordFailsForRestart: {e}", "ERROR")

    def _on_lock_successes_changed(self, value: int):
        """Обработчик изменения количества успехов для LOCK"""
        try:
            from config import REGISTRY_PATH
            from config.reg import reg

            reg(f"{REGISTRY_PATH}\\Orchestra", "LockSuccesses", value)
            log(f"Успехов для LOCK: {value}", "INFO")

            # Обновляем orchestra_runner если запущен
            app = self._get_app()
            if app and hasattr(app, 'orchestra_runner') and app.orchestra_runner:
                app.orchestra_runner.lock_successes_threshold = value

        except Exception as e:
            log(f"Ошибка сохранения настройки LockSuccesses: {e}", "ERROR")

    def _on_unlock_fails_changed(self, value: int):
        """Обработчик изменения количества ошибок для AUTO-UNLOCK"""
        try:
            from config import REGISTRY_PATH
            from config.reg import reg

            reg(f"{REGISTRY_PATH}\\Orchestra", "UnlockFails", value)
            log(f"Ошибок для AUTO-UNLOCK: {value}", "INFO")

            # Обновляем orchestra_runner если запущен
            app = self._get_app()
            if app and hasattr(app, 'orchestra_runner') and app.orchestra_runner:
                app.orchestra_runner.unlock_fails_threshold = value

        except Exception as e:
            log(f"Ошибка сохранения настройки UnlockFails: {e}", "ERROR")

    def _get_app(self):
        """Получает ссылку на главное приложение"""
        try:
            # Ищем через parent виджетов
            widget = self
            while widget:
                if hasattr(widget, 'dpi_controller'):
                    return widget
                if hasattr(widget, 'parent_app'):
                    return widget.parent_app
                widget = widget.parent()
            
            # Пробуем через QApplication
            from PyQt6.QtWidgets import QApplication
            app = QApplication.instance()
            if hasattr(app, 'dpi_controller'):
                return app
                
            # Пробуем через main_window
            for widget in QApplication.topLevelWidgets():
                if hasattr(widget, 'parent_app'):
                    return widget.parent_app
        except:
            pass
        return None
    
    def _restart_dpi_async(self):
        """Асинхронно перезапускает DPI если он запущен"""
        try:
            app = self._get_app()
            if not app or not hasattr(app, 'dpi_controller'):
                log("DPI контроллер не найден для перезапуска", "DEBUG")
                return

            # Для режима direct_zapret2 используем унифицированный механизм
            from strategy_menu import get_strategy_launch_method
            launch_method = get_strategy_launch_method()

            if launch_method == "direct_zapret2":
                from dpi.zapret2_core_restart import trigger_dpi_reload
                trigger_dpi_reload(app, reason="settings_changed")
                return

            # Для остальных режимов (orchestra, zapret1, bat) - старая логика
            # Проверяем, запущен ли процесс
            if not app.dpi_starter.check_process_running_wmi(silent=True):
                log("DPI не запущен, перезапуск не требуется", "DEBUG")
                return

            log("Перезапуск DPI после изменения настроек...", "INFO")

            # Асинхронно останавливаем
            app.dpi_controller.stop_dpi_async()

            # Запускаем таймер для проверки остановки и перезапуска
            self._restart_check_count = 0
            if not hasattr(self, '_restart_timer') or self._restart_timer is None:
                self._restart_timer = QTimer(self)
                self._restart_timer.timeout.connect(self._check_stopped_and_restart)
            self._restart_timer.start(300)  # Проверяем каждые 300мс

        except Exception as e:
            log(f"Ошибка перезапуска DPI: {e}", "ERROR")
    
    def _check_stopped_and_restart(self):
        """Проверяет остановку DPI и запускает заново"""
        try:
            app = self._get_app()
            if not app:
                self._restart_timer.stop()
                return
                
            self._restart_check_count += 1
            
            # Максимум 30 проверок (9 секунд)
            if self._restart_check_count > 30:
                self._restart_timer.stop()
                log("⚠️ Таймаут ожидания остановки DPI", "WARNING")
                self._start_dpi_after_stop()
                return
            
            # Проверяем, остановлен ли процесс
            if not app.dpi_starter.check_process_running_wmi(silent=True):
                self._restart_timer.stop()
                # Небольшая пауза и запуск
                QTimer.singleShot(200, self._start_dpi_after_stop)
                
        except Exception as e:
            if hasattr(self, '_restart_timer'):
                self._restart_timer.stop()
            log(f"Ошибка проверки остановки: {e}", "ERROR")
    
    def _start_dpi_after_stop(self):
        """Запускает DPI после остановки"""
        try:
            app = self._get_app()
            if not app or not hasattr(app, 'dpi_controller'):
                return
                
            from strategy_menu import get_strategy_launch_method
            launch_method = get_strategy_launch_method()
            
            if launch_method in ("direct_zapret2", "direct_zapret2_orchestra", "direct_zapret1"):
                # Прямой запуск - берём текущие настройки
                from strategy_menu import get_direct_strategy_selections
                from launcher_common import combine_strategies

                selections = get_direct_strategy_selections()
                combined = combine_strategies(**selections)

                # Формируем данные в правильном формате
                selected_mode = {
                    'is_combined': True,
                    'name': combined.get('description', 'Перезапуск'),
                    'args': combined.get('args', ''),
                    'category_strategies': combined.get('category_strategies', {})
                }
                app.dpi_controller.start_dpi_async(selected_mode=selected_mode)
            else:
                # BAT режим
                app.dpi_controller.start_dpi_async()
                
            log("✅ DPI перезапущен с новыми настройками", "INFO")
            
        except Exception as e:
            log(f"Ошибка запуска DPI: {e}", "ERROR")
        
    def _load_filter_settings(self):
        """Загружает настройки фильтров"""
        try:
            from strategy_menu import (
                get_wssize_enabled, set_wssize_enabled,
                get_debug_log_enabled, set_debug_log_enabled
            )

            # ═══════════════════════════════════════════════════════════════════════
            # ДОПОЛНИТЕЛЬНЫЕ НАСТРОЙКИ — остаются активными
            # ═══════════════════════════════════════════════════════════════════════
            self.wssize_toggle.setChecked(get_wssize_enabled(), block_signals=True)
            self.debug_log_toggle.setChecked(get_debug_log_enabled(), block_signals=True)

            # Подключаем сигналы только для дополнительных настроек
            self.wssize_toggle.toggled.connect(lambda v: self._on_filter_changed(set_wssize_enabled, v))
            self.debug_log_toggle.toggled.connect(lambda v: self._on_filter_changed(set_debug_log_enabled, v))

        except Exception as e:
            log(f"Ошибка загрузки фильтров: {e}", "WARNING")
            import traceback
            log(traceback.format_exc(), "DEBUG")

    def update_filter_display(self, filters: dict):
        """
        Совместимость: раньше показывало «Фильтры перехвата трафика» в GUI.
        Теперь блок удалён, метод оставлен как no-op для старых вызовов.
        """
        _ = filters
        return
                
    def _on_filter_changed(self, setter_func, value):
        """Обработчик изменения фильтра"""
        setter_func(value)

        # Для direct_zapret2 физически пишем --debug в preset-zapret2.txt,
        # чтобы winws2 получал его из @file (а не только из CLI).
        try:
            if getattr(setter_func, "__name__", "") == "set_debug_log_enabled":
                from strategy_menu import get_strategy_launch_method
                if get_strategy_launch_method() == "direct_zapret2":
                    from preset_zapret2 import PresetManager, ensure_default_preset_exists

                    ensure_default_preset_exists()
                    manager = PresetManager()
                    preset = manager.get_active_preset()
                    if preset:
                        manager.sync_preset_to_active_file(preset)
        except Exception as e:
            log(f"Ошибка обновления preset-zapret2.txt для --debug: {e}", "DEBUG")

        self.filters_changed.emit()
        
    def _update_filters_visibility(self):
        """Обновляет видимость фильтров и секций"""
        try:
            from strategy_menu import get_strategy_launch_method
            method = get_strategy_launch_method()

            # Режимы
            is_direct_mode = method in ("direct_zapret2", "direct_zapret2_orchestra", "direct_zapret1")
            is_orchestra_mode = method in ("orchestra", "direct_zapret2_orchestra")
            is_zapret_mode = method in ("direct_zapret2", "bat", "direct_zapret1")  # Zapret 1/2 без оркестратора

            # For direct_zapret2 these options are shown on the Strategies/Management page
            # (ui/pages/zapret2/direct_control_page.py), so hide them here.
            self.advanced_card.setVisible(is_direct_mode and method != "direct_zapret2")

            # Discord restart только для Zapret 1/2 (без оркестратора)
            self.discord_restart_container.setVisible(is_zapret_mode)

            # Настройки оркестратора только для режимов оркестратора
            self.orchestra_settings_container.setVisible(is_orchestra_mode)

        except:
            pass
