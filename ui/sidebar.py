# ui/sidebar.py
"""
Боковая панель навигации в стиле Windows 11 Settings
"""
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, QSize, QTimer, pyqtProperty
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFrame, QScrollArea, QSizePolicy
)
from PyQt6.QtGui import QFont, QIcon, QColor, QPainter, QPainterPath
import qtawesome as qta


class NavButton(QPushButton):
    """Кнопка навигации в стиле Windows 11 с объёмными иконками"""
    
    def __init__(self, icon_name: str, text: str, parent=None):
        super().__init__(parent)
        self._selected = False
        self._hovered = False
        self.icon_name = icon_name
        self._text = text
        self._collapsed = False
        
        # Layout
        self.setFixedHeight(40)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setText(f"   {text}")
        self.setIconSize(QSize(20, 20))
        
        self._update_style()
    
    def set_collapsed(self, collapsed: bool):
        """Устанавливает свёрнутый режим (только иконка)"""
        self._collapsed = collapsed
        if collapsed:
            self.setText("")
        else:
            self.setText(f"   {self._text}")
        self._update_style()
        
    def _update_style(self):
        if self._selected:
            bg_color = "rgba(255, 255, 255, 0.1)"
            border_left = "3px solid #60cdff"
            text_color = "#ffffff"
        elif self._hovered:
            bg_color = "rgba(255, 255, 255, 0.05)"
            border_left = "3px solid transparent"
            text_color = "#e0e0e0"
        else:
            bg_color = "transparent"
            border_left = "3px solid transparent"
            text_color = "#9e9e9e"  # Светло-серый для неактивных
        
        padding = "12px" if not self._collapsed else "0px"
        text_align = "left" if not self._collapsed else "center"
            
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg_color};
                border: none;
                border-left: {border_left};
                border-radius: 4px;
                color: {text_color};
                text-align: {text_align};
                padding-left: {padding};
                font-family: 'Segoe UI Variable', 'Segoe UI', sans-serif;
                font-size: 13px;
                font-weight: {'600' if self._selected else '400'};
            }}
        """)
        
        # Обновляем иконку - объёмная с градиентом для выбранного, светло-серая для остальных
        try:
            from ui.fluent_icons import FluentIcon
            if self._selected:
                self.setIcon(FluentIcon.create_icon(self.icon_name, 20))
            else:
                # Светло-серый цвет для неактивных иконок
                self.setIcon(qta.icon(self.icon_name, color='#9e9e9e'))
        except:
            icon_color = '#60cdff' if self._selected else '#9e9e9e'
            self.setIcon(qta.icon(self.icon_name, color=icon_color))
        
    def set_selected(self, selected: bool):
        self._selected = selected
        self._update_style()
        
    def enterEvent(self, event):
        self._hovered = True
        self._update_style()
        super().enterEvent(event)
        
    def leaveEvent(self, event):
        self._hovered = False
        self._update_style()
        super().leaveEvent(event)


class SubNavButton(QPushButton):
    """Вложенная кнопка навигации (подпункт) - меньше и тоньше"""
    
    def __init__(self, icon_name: str, text: str, parent=None):
        super().__init__(parent)
        self._selected = False
        self._hovered = False
        self.icon_name = icon_name
        self._text = text
        self._collapsed = False
        
        # Меньшая высота для подпунктов
        self.setFixedHeight(32)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setText(f"  {text}")
        self.setIconSize(QSize(14, 14))
        
        self._update_style()
    
    def set_collapsed(self, collapsed: bool):
        """Устанавливает свёрнутый режим (только иконка)"""
        self._collapsed = collapsed
        if collapsed:
            self.setText("")
        else:
            self.setText(f"  {self._text}")
        self._update_style()
        
    def _update_style(self):
        if self._selected:
            bg_color = "rgba(255, 255, 255, 0.08)"
            border_left = "2px solid #60cdff"
            text_color = "#60cdff"
        elif self._hovered:
            bg_color = "rgba(255, 255, 255, 0.04)"
            border_left = "2px solid transparent"
            text_color = "#c0c0c0"
        else:
            bg_color = "transparent"
            border_left = "2px solid transparent"
            text_color = "#808080"  # Более тёмный серый для подпунктов
        
        padding = "28px" if not self._collapsed else "0px"
        text_align = "left" if not self._collapsed else "center"
            
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg_color};
                border: none;
                border-left: {border_left};
                border-radius: 3px;
                color: {text_color};
                text-align: {text_align};
                padding-left: {padding};
                font-family: 'Segoe UI Variable', 'Segoe UI', sans-serif;
                font-size: 11px;
                font-weight: {'500' if self._selected else '400'};
            }}
        """)
        
        # Иконка меньшего размера
        icon_color = '#60cdff' if self._selected else '#707070'
        self.setIcon(qta.icon(self.icon_name, color=icon_color))
        
    def set_selected(self, selected: bool):
        self._selected = selected
        self._update_style()
        
    def enterEvent(self, event):
        self._hovered = True
        self._update_style()
        super().enterEvent(event)
        
    def leaveEvent(self, event):
        self._hovered = False
        self._update_style()
        super().leaveEvent(event)


class SideNavBar(QWidget):
    """Боковая панель навигации со сворачиванием"""
    
    # Сигналы
    section_changed = pyqtSignal(int)
    
    # Константы размеров
    EXPANDED_WIDTH = 220
    COLLAPSED_WIDTH = 56
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.buttons = []
        self.current_index = 0
        self._is_pinned = True  # По умолчанию закреплено
        self._is_collapsed = False
        self._is_hovering = False
        self._width_value = self.EXPANDED_WIDTH
        
        # Анимация ширины
        self._width_animation = QPropertyAnimation(self, b"panel_width")
        self._width_animation.setDuration(200)
        self._width_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        # Таймер для задержки сворачивания
        self._collapse_timer = QTimer(self)
        self._collapse_timer.setSingleShot(True)
        self._collapse_timer.timeout.connect(self._do_collapse)
        
        self.setFixedWidth(self.EXPANDED_WIDTH)
        self.setObjectName("sideNavBar")
        self.setMouseTracking(True)
        
        # Основной layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 16, 8, 16)
        layout.setSpacing(2)
        
        # Заголовок с кнопкой закрепления
        self.header_widget = QWidget()
        self.header_widget.setFixedHeight(60)  # Фиксированная высота для сохранения позиции
        header_layout = QHBoxLayout(self.header_widget)
        header_layout.setContentsMargins(4, 8, 4, 16)
        header_layout.setSpacing(4)
        
        self.header_label = QLabel("Zapret")
        self.header_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 22px;
                font-weight: 700;
                font-family: 'Segoe UI Variable Display', 'Segoe UI', sans-serif;
            }
        """)
        header_layout.addWidget(self.header_label, 1)
        
        # Кнопка закрепления
        self.pin_btn = QPushButton()
        self.pin_btn.setFixedSize(28, 28)
        self.pin_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.pin_btn.clicked.connect(self._toggle_pin)
        self._update_pin_button()
        header_layout.addWidget(self.pin_btn)
        
        layout.addWidget(self.header_widget)
        
        # Навигационные кнопки с подпунктами
        self.sections = [
            ("fa5s.home", "Главная", False),           # 0
            ("fa5s.play-circle", "Управление", False), # 1
            ("fa5s.cog", "Стратегии", False),          # 2
            ("fa5s.list", "Hostlist", True),           # 3 - подпункт
            ("fa5s.server", "IPset", True),            # 4 - подпункт
            ("fa5s.edit", "Редактор", True),           # 5 - подпункт (редактор стратегий)
            ("fa5s.sliders-h", "Настройки DPI", True), # 6 - подпункт
            ("fa5s.rocket", "Автозапуск", False),      # 7
            ("fa5s.network-wired", "Сеть", False),     # 8
            ("fa5s.palette", "Оформление", False),     # 9
            ("fa5s.star", "Premium", False),           # 10
            ("fa5s.file-alt", "Логи", False),          # 11
            ("fa5s.info-circle", "О программе", False),# 12
        ]
        
        for i, (icon, text, is_sub) in enumerate(self.sections):
            if is_sub:
                btn = SubNavButton(icon, text, self)
            else:
                btn = NavButton(icon, text, self)
            btn.clicked.connect(lambda checked, idx=i: self._on_button_clicked(idx))
            self.buttons.append(btn)
            layout.addWidget(btn)
            
        # Выбираем первую кнопку
        if self.buttons:
            self.buttons[0].set_selected(True)
        
        # Растягивающий спейсер
        layout.addStretch(1)
        
        # Версия внизу
        from config import APP_VERSION
        self.version_label = QLabel(f"v{APP_VERSION}")
        self.version_label.setStyleSheet("""
            QLabel {
                color: rgba(255, 255, 255, 0.4);
                font-size: 11px;
                padding: 8px 12px;
            }
        """)
        layout.addWidget(self.version_label)
        
        # Стиль панели
        self.setStyleSheet("""
            QWidget#sideNavBar {
                background-color: rgba(28, 28, 28, 0.85);
                border-right: 1px solid rgba(255, 255, 255, 0.06);
            }
        """)
    
    # Property для анимации ширины
    def _get_panel_width(self):
        return self._width_value
    
    def _set_panel_width(self, width):
        self._width_value = width
        self.setFixedWidth(int(width))
        
        # Обновляем видимость текста
        collapsed = width < (self.EXPANDED_WIDTH + self.COLLAPSED_WIDTH) / 2
        if collapsed != self._is_collapsed:
            self._is_collapsed = collapsed
            self._update_collapsed_state()
    
    panel_width = pyqtProperty(float, _get_panel_width, _set_panel_width)
    
    def _update_collapsed_state(self):
        """Обновляет состояние всех элементов при сворачивании/разворачивании"""
        for btn in self.buttons:
            btn.set_collapsed(self._is_collapsed)
        
        # Скрываем только текст, но не виджеты (чтобы кнопки оставались на месте)
        if self._is_collapsed:
            self.header_label.setText("")
            self.version_label.setText("")
            self.pin_btn.setVisible(False)
        else:
            self.header_label.setText("Zapret")
            from config import APP_VERSION
            self.version_label.setText(f"v{APP_VERSION}")
            self.pin_btn.setVisible(True)
    
    def _update_pin_button(self):
        """Обновляет иконку кнопки закрепления"""
        if self._is_pinned:
            icon = qta.icon('fa5s.thumbtack', color='#60cdff')
            tooltip = "Открепить панель"
        else:
            icon = qta.icon('fa5s.thumbtack', color='#666666', rotated=45)
            tooltip = "Закрепить панель"
        
        self.pin_btn.setIcon(icon)
        self.pin_btn.setToolTip(tooltip)
        self.pin_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.1);
            }
        """)
    
    def _toggle_pin(self):
        """Переключает закрепление панели"""
        self._is_pinned = not self._is_pinned
        self._update_pin_button()
        
        if not self._is_pinned:
            # Сразу сворачиваем если открепили
            self._collapse_timer.start(500)
    
    def _do_collapse(self):
        """Сворачивает панель"""
        if not self._is_pinned and not self._is_hovering:
            self._animate_width(self.COLLAPSED_WIDTH)
    
    def _do_expand(self):
        """Разворачивает панель"""
        self._collapse_timer.stop()
        self._animate_width(self.EXPANDED_WIDTH)
    
    def _animate_width(self, target_width):
        """Анимирует изменение ширины"""
        self._width_animation.stop()
        self._width_animation.setStartValue(self._width_value)
        self._width_animation.setEndValue(target_width)
        self._width_animation.start()
    
    def enterEvent(self, event):
        """При наведении - разворачиваем если не закреплено"""
        self._is_hovering = True
        if not self._is_pinned:
            self._do_expand()
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """При уходе мыши - сворачиваем если не закреплено"""
        self._is_hovering = False
        if not self._is_pinned:
            self._collapse_timer.start(300)
        super().leaveEvent(event)
        
    def _on_button_clicked(self, index: int):
        if index == self.current_index:
            return
            
        # Снимаем выделение со старой кнопки
        self.buttons[self.current_index].set_selected(False)
        
        # Выделяем новую
        self.current_index = index
        self.buttons[index].set_selected(True)
        
        # Эмитим сигнал
        self.section_changed.emit(index)
        
    def set_section(self, index: int):
        """Программно устанавливает раздел"""
        if 0 <= index < len(self.buttons):
            self._on_button_clicked(index)


class SettingsCard(QFrame):
    """Карточка настроек в стиле Windows 11"""
    
    def __init__(self, title: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("settingsCard")
        
        # Layout карточки
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(16, 16, 16, 16)
        self.main_layout.setSpacing(12)
        
        # Заголовок карточки
        if title:
            title_label = QLabel(title)
            title_label.setStyleSheet("""
                QLabel {
                    color: #ffffff;
                    font-size: 14px;
                    font-weight: 600;
                    font-family: 'Segoe UI Variable', 'Segoe UI', sans-serif;
                }
            """)
            self.main_layout.addWidget(title_label)
        
        # Стиль карточки (Acrylic стиль с blur)
        self.setStyleSheet("""
            QFrame#settingsCard {
                background-color: rgba(255, 255, 255, 0.04);
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 8px;
            }
            QFrame#settingsCard:hover {
                background-color: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.1);
            }
        """)
        
    def add_widget(self, widget: QWidget):
        """Добавляет виджет в карточку"""
        self.main_layout.addWidget(widget)
        
    def add_layout(self, layout):
        """Добавляет layout в карточку"""
        self.main_layout.addLayout(layout)


class SettingsRow(QWidget):
    """Строка настройки (иконка + текст слева, контрол справа)"""
    
    def __init__(self, icon_name: str, title: str, description: str = "", parent=None):
        super().__init__(parent)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(12)
        
        # Иконка
        icon_label = QLabel()
        icon_label.setPixmap(qta.icon(icon_name, color='#60cdff').pixmap(20, 20))
        icon_label.setFixedSize(24, 24)
        layout.addWidget(icon_label)
        
        # Текст
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        
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
            desc_label.setStyleSheet("""
                QLabel {
                    color: rgba(255, 255, 255, 0.6);
                    font-size: 11px;
                }
            """)
            desc_label.setWordWrap(True)
            text_layout.addWidget(desc_label)
            
        layout.addLayout(text_layout, 1)
        
        # Контейнер для контрола (добавляется извне)
        self.control_container = QHBoxLayout()
        self.control_container.setSpacing(8)
        layout.addLayout(self.control_container)
        
    def set_control(self, widget: QWidget):
        """Устанавливает контрол справа"""
        self.control_container.addWidget(widget)


class ActionButton(QPushButton):
    """Кнопка действия в стиле Windows 11"""
    
    def __init__(self, text: str, icon_name: str = None, accent: bool = False, parent=None):
        super().__init__(text, parent)
        self.accent = accent
        self._hovered = False
        
        if icon_name:
            self.setIcon(qta.icon(icon_name, color='white'))
            self.setIconSize(QSize(16, 16))
            
        self.setFixedHeight(32)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._update_style()
        
    def _update_style(self):
        if self.accent:
            if self._hovered:
                bg = "rgba(96, 205, 255, 0.9)"
            else:
                bg = "#60cdff"
            text_color = "#000000"
        else:
            if self._hovered:
                bg = "rgba(255, 255, 255, 0.15)"
            else:
                bg = "rgba(255, 255, 255, 0.08)"
            text_color = "#ffffff"
            
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg};
                border: none;
                border-radius: 4px;
                color: {text_color};
                padding: 0 16px;
                font-size: 12px;
                font-weight: 600;
                font-family: 'Segoe UI Variable', 'Segoe UI', sans-serif;
            }}
        """)
        
    def enterEvent(self, event):
        self._hovered = True
        self._update_style()
        super().enterEvent(event)
        
    def leaveEvent(self, event):
        self._hovered = False
        self._update_style()
        super().leaveEvent(event)


class StatusIndicator(QWidget):
    """Индикатор статуса (точка + текст)"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # Точка-индикатор
        self.dot = QLabel("●")
        self.dot.setStyleSheet("color: #888888; font-size: 10px;")
        layout.addWidget(self.dot)
        
        # Текст статуса
        self.text = QLabel("Проверка...")
        self.text.setStyleSheet("""
            QLabel {
                color: rgba(255, 255, 255, 0.8);
                font-size: 13px;
            }
        """)
        layout.addWidget(self.text)
        layout.addStretch()
        
    def set_status(self, text: str, status: str = "neutral"):
        """
        Устанавливает статус
        status: 'running', 'stopped', 'warning', 'neutral'
        """
        self.text.setText(text)
        
        colors = {
            'running': '#6ccb5f',  # Зеленый
            'stopped': '#ff6b6b',  # Красный
            'warning': '#ffc107',  # Желтый
            'neutral': '#888888',  # Серый
        }
        
        color = colors.get(status, colors['neutral'])
        self.dot.setStyleSheet(f"color: {color}; font-size: 10px;")
