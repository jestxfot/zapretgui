# ui/sidebar.py
"""
Боковая панель навигации в стиле Windows 11 Settings
"""
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, QSize, QTimer, pyqtProperty, QPoint, QRect
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QScrollArea, QSizePolicy
)
from PyQt6.QtGui import QFont, QIcon, QColor, QPainter, QPainterPath, QTransform
import qtawesome as qta

from ui.page_names import PageName, SectionName, SECTION_TO_PAGE, SECTION_CHILDREN, ORCHESTRA_ONLY_SECTIONS


class ShimmerMixin:
    """Миксин для добавления эффекта подсветки иконки"""
    
    def init_shimmer(self):
        """Инициализация эффекта подсветки"""
        self._shimmer_brightness = 0.0  # Яркость подсветки (0-1)
        
        # Анимация подсветки (плавное нарастание)
        self._shimmer_animation = QPropertyAnimation(self, b"shimmer_brightness")
        self._shimmer_animation.setDuration(400)
        self._shimmer_animation.setStartValue(0.0)
        self._shimmer_animation.setEndValue(1.0)
        self._shimmer_animation.setEasingCurve(QEasingCurve.Type.OutQuad)
        self._shimmer_animation.finished.connect(self._update_icon_glow)
        
        # Анимация затухания
        self._fadeout_animation = QPropertyAnimation(self, b"shimmer_brightness")
        self._fadeout_animation.setDuration(500)
        self._fadeout_animation.setStartValue(1.0)
        self._fadeout_animation.setEndValue(0.0)
        self._fadeout_animation.setEasingCurve(QEasingCurve.Type.InQuad)
        
        # Таймер задержки перед затуханием
        self._fadeout_timer = QTimer(self)
        self._fadeout_timer.setSingleShot(True)
        self._fadeout_timer.timeout.connect(self._start_fadeout)
    
    def _get_shimmer_brightness(self):
        return self._shimmer_brightness
    
    def _set_shimmer_brightness(self, val):
        self._shimmer_brightness = val
        self._update_icon_glow()
    
    shimmer_brightness = pyqtProperty(float, _get_shimmer_brightness, _set_shimmer_brightness)
    
    def start_shimmer(self):
        """Запускает анимацию подсветки"""
        # Отменяем затухание если оно было запланировано
        self._fadeout_timer.stop()
        self._fadeout_animation.stop()
        
        if self._shimmer_animation.state() != QPropertyAnimation.State.Running:
            self._shimmer_animation.start()
    
    def stop_shimmer(self):
        """Запускает задержку перед затуханием"""
        self._shimmer_animation.stop()
        # Запускаем таймер на 1.5 секунды перед затуханием
        self._fadeout_timer.start(1500)
    
    def _start_fadeout(self):
        """Начинает плавное затухание"""
        self._fadeout_animation.setStartValue(self._shimmer_brightness)
        self._fadeout_animation.start()
    
    def _update_icon_glow(self):
        """Обновляет иконку с эффектом свечения - реализуется в дочерних классах"""
        pass


class ShakeMixin:
    """Миксин для добавления эффекта лёгкого покачивания иконки"""
    
    def init_shake(self):
        """Инициализация shake эффекта"""
        self._shake_step = 0
        self._shake_timer = QTimer(self)
        self._shake_timer.timeout.connect(self._animate_shake)
    
    def _animate_shake(self):
        """Анимация лёгкого покачивания иконки"""
        self._shake_step += 1
        if self._shake_step > 4:
            self._shake_timer.stop()
            self._shake_step = 0
            self._apply_icon_rotation(0)  # Возвращаем в нормальное положение
            return
        
        # Лёгкое покачивание (ещё мягче)
        rotations = [0, -3, 3, -2, 0]
        rotation = rotations[min(self._shake_step, len(rotations) - 1)]
        self._apply_icon_rotation(rotation)
    
    def _apply_icon_rotation(self, rotation: int):
        """Применяет поворот к иконке - реализуется в дочерних классах"""
        pass
    
    def start_shake(self):
        """Запускает анимацию покачивания"""
        if not self._shake_timer.isActive():
            self._shake_step = 0
            self._shake_timer.start(80)  # Медленнее (80мс между кадрами)


class NavButton(QPushButton, ShimmerMixin, ShakeMixin):
    """Кнопка навигации в стиле Windows 11 с объёмными иконками"""
    
    def __init__(self, icon_name: str, text: str, parent=None):
        super().__init__(parent)
        self._selected = False
        self._hovered = False
        self.icon_name = icon_name
        self._text = text
        self._collapsed = False
        
        # Инициализация анимаций
        self.init_shimmer()
        self.init_shake()
        
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
        
        padding = "22px" if not self._collapsed else "0px"
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
        self._set_icon_with_brightness()
        
    def _set_icon_with_brightness(self):
        """Устанавливает иконку с учётом яркости (для эффекта свечения)"""
        brightness = getattr(self, '_shimmer_brightness', 0.0)
        
        if self._selected:
            # Выбранная иконка - используем FluentIcon или яркий цвет
            try:
                from ui.fluent_icons import FluentIcon
                self.setIcon(FluentIcon.create_icon(self.icon_name, 20))
                return
            except:
                base_color = QColor('#60cdff')
        else:
            base_color = QColor('#9e9e9e')
        
        # Интерполируем к белому при свечении
        if brightness > 0:
            glow_color = QColor('#ffffff')
            r = int(base_color.red() + (glow_color.red() - base_color.red()) * brightness * 0.6)
            g = int(base_color.green() + (glow_color.green() - base_color.green()) * brightness * 0.6)
            b = int(base_color.blue() + (glow_color.blue() - base_color.blue()) * brightness * 0.6)
            color = QColor(r, g, b)
            self.setIcon(qta.icon(self.icon_name, color=color.name()))
        else:
            self.setIcon(qta.icon(self.icon_name, color=base_color.name()))
    
    def _update_icon_glow(self):
        """Обновляет иконку с эффектом свечения"""
        self._set_icon_with_brightness()
    
    def _apply_icon_rotation(self, rotation: int):
        """Поворачивает текущий pixmap иконки без смены цвета"""
        if rotation == 0:
            self._set_icon_with_brightness()
            return
        
        icon = self.icon()
        if icon.isNull():
            return
        
        pix = icon.pixmap(self.iconSize())
        if pix.isNull():
            return
        
        transform = QTransform().rotate(rotation)
        rotated = pix.transformed(transform, Qt.TransformationMode.SmoothTransformation)
        self.setIcon(QIcon(rotated))
        
    def set_selected(self, selected: bool):
        was_selected = self._selected
        self._selected = selected
        self._update_style()
        # Покачивание при выборе
        if selected and not was_selected:
            self.start_shake()
        
    def enterEvent(self, event):
        self._hovered = True
        self._update_style()
        # Запускаем подсветку при наведении
        self.start_shimmer()
        super().enterEvent(event)
        
    def leaveEvent(self, event):
        self._hovered = False
        self.stop_shimmer()  # Останавливаем и сбрасываем
        self._update_style()
        super().leaveEvent(event)


class SubNavButton(QPushButton, ShimmerMixin, ShakeMixin):
    """Вложенная кнопка навигации (подпункт) - меньше и тоньше"""
    
    def __init__(self, icon_name: str, text: str, parent=None):
        super().__init__(parent)
        self._selected = False
        self._hovered = False
        self.icon_name = icon_name
        self._text = text
        self._collapsed = False
        
        # Инициализация анимаций
        self.init_shimmer()
        self.init_shake()
        
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
        self._set_icon_with_brightness()
        
    def _set_icon_with_brightness(self):
        """Устанавливает иконку с учётом яркости (для эффекта свечения)"""
        brightness = getattr(self, '_shimmer_brightness', 0.0)
        
        if self._selected:
            base_color = QColor('#60cdff')
        else:
            base_color = QColor('#707070')
        
        # Интерполируем к белому при свечении
        if brightness > 0:
            glow_color = QColor('#ffffff')
            r = int(base_color.red() + (glow_color.red() - base_color.red()) * brightness * 0.6)
            g = int(base_color.green() + (glow_color.green() - base_color.green()) * brightness * 0.6)
            b = int(base_color.blue() + (glow_color.blue() - base_color.blue()) * brightness * 0.6)
            color = QColor(r, g, b)
            self.setIcon(qta.icon(self.icon_name, color=color.name()))
        else:
            self.setIcon(qta.icon(self.icon_name, color=base_color.name()))
    
    def _update_icon_glow(self):
        """Обновляет иконку с эффектом свечения"""
        self._set_icon_with_brightness()
    
    def _apply_icon_rotation(self, rotation: int):
        """Поворачивает текущий pixmap иконки без смены цвета"""
        if rotation == 0:
            self._set_icon_with_brightness()
            return
        
        icon = self.icon()
        if icon.isNull():
            return
        
        pix = icon.pixmap(self.iconSize())
        if pix.isNull():
            return
        
        transform = QTransform().rotate(rotation)
        rotated = pix.transformed(transform, Qt.TransformationMode.SmoothTransformation)
        self.setIcon(QIcon(rotated))
        
    def set_selected(self, selected: bool):
        was_selected = self._selected
        self._selected = selected
        self._update_style()
        # Покачивание при выборе
        if selected and not was_selected:
            self.start_shake()
        
    def enterEvent(self, event):
        self._hovered = True
        self._update_style()
        # Запускаем подсветку при наведении
        self.start_shimmer()
        super().enterEvent(event)
        
    def leaveEvent(self, event):
        self._hovered = False
        self.stop_shimmer()  # Останавливаем и сбрасываем
        self._update_style()
        super().leaveEvent(event)


class CollapsibleHeader(QPushButton):
    """Текстовый заголовок секции с возможностью сворачивания подпунктов"""

    toggled = pyqtSignal(bool)  # True = expanded, False = collapsed

    def __init__(self, text: str, parent=None):
        super().__init__(parent)
        self._expanded = True
        self._collapsed_sidebar = False
        self._base_text = text
        self.setText(f"  {text}")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(26)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self._update_style()

    def _update_style(self):
        self.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: rgba(255, 255, 255, 0.6);
                font-size: 10px;
                font-weight: 600;
                padding: 6px 12px 4px 24px;
                text-align: left;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.06);
            }
        """)

    @property
    def is_expanded(self):
        return self._expanded

    def set_collapsed_sidebar(self, collapsed: bool):
        self._collapsed_sidebar = collapsed
        self.setVisible(not collapsed)
        if collapsed:
            self.setText("")
        else:
            self.setText(f"  {self._base_text}")
        self.update()

    def toggle_expanded(self):
        self._expanded = not self._expanded
        self.toggled.emit(self._expanded)
        self.update()

    def set_expanded(self, expanded: bool):
        if self._expanded != expanded:
            self._expanded = expanded
            self.toggled.emit(self._expanded)
        self.update()

    def mousePressEvent(self, event):
        # ЛКМ и ПКМ переключают сворачивание
        if event.button() in (Qt.MouseButton.LeftButton, Qt.MouseButton.RightButton):
            self.toggle_expanded()
            event.accept()
            return
        super().mousePressEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event)
        if self._collapsed_sidebar:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        chevron_x = self.width() - 18
        chevron_y = self.height() // 2
        color = QColor('#a0a0a0')
        painter.setPen(color)
        painter.setBrush(color)

        from PyQt6.QtGui import QPolygonF
        from PyQt6.QtCore import QPointF

        if self._expanded:
            points = [
                QPointF(chevron_x - 4, chevron_y - 2),
                QPointF(chevron_x + 4, chevron_y - 2),
                QPointF(chevron_x, chevron_y + 3)
            ]
        else:
            points = [
                QPointF(chevron_x - 2, chevron_y - 4),
                QPointF(chevron_x - 2, chevron_y + 4),
                QPointF(chevron_x + 3, chevron_y)
            ]

        polygon = QPolygonF(points)
        painter.drawPolygon(polygon)
        painter.end()


class CollapsibleNavButton(NavButton):
    """Кнопка навигации со сворачиваемыми подпунктами"""
    
    # Сигнал для toggle подпунктов
    toggled = pyqtSignal(bool)  # True = expanded, False = collapsed
    
    def __init__(self, icon_name: str, text: str, parent=None):
        super().__init__(icon_name, text, parent)
        self._expanded = True
        self._chevron_hovered = False
        
        # Добавляем область для шеврона справа
        self._update_chevron()
    
    def _update_chevron(self):
        """Обновляет отображение шеврона"""
        pass  # Шеврон рисуется в paintEvent
    
    @property
    def is_expanded(self):
        return self._expanded
    
    def toggle_expanded(self):
        """Переключает состояние развёрнутости"""
        self._expanded = not self._expanded
        self.toggled.emit(self._expanded)
        self.update()
    
    def set_expanded(self, expanded: bool):
        """Устанавливает состояние развёрнутости"""
        if self._expanded != expanded:
            self._expanded = expanded
            self.toggled.emit(self._expanded)
            self.update()
    
    def mousePressEvent(self, event):
        """Проверяем клик по шеврону или ПКМ в любом месте"""
        # В свёрнутом сайдбаре шеврон не виден, поэтому ЛКМ должен работать как обычный клик,
        # а не перехватываться "областью шеврона" (иначе кнопка не открывает страницу).
        if self._collapsed and event.button() == Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return

        # ПКМ в любом месте кнопки переключает сворачивание
        if event.button() == Qt.MouseButton.RightButton:
            self.toggle_expanded()
            event.accept()
            return
        
        # ЛКМ по области шеврона тоже переключает
        chevron_area = QRect(self.width() - 30, 0, 30, self.height())
        if event.button() == Qt.MouseButton.LeftButton and chevron_area.contains(event.pos()):
            # Если секция уже активна, ЛКМ по шеврону должен вести себя как обычный клик
            # (например, вернуться из detail-страницы на главный список).
            if self._selected:
                super().mousePressEvent(event)
                return

            self.toggle_expanded()
            event.accept()
            return
        super().mousePressEvent(event)
    
    def paintEvent(self, event):
        """Рисуем шеврон"""
        super().paintEvent(event)
        
        if self._collapsed:
            return  # Не рисуем шеврон в свёрнутом режиме сайдбара
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Рисуем шеврон справа
        chevron_x = self.width() - 22
        chevron_y = self.height() // 2
        
        # Цвет шеврона
        if self._selected:
            color = QColor('#60cdff')
        else:
            color = QColor('#707070')
        
        painter.setPen(color)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        
        # Рисуем треугольник/шеврон
        from PyQt6.QtGui import QPolygonF
        from PyQt6.QtCore import QPointF
        
        if self._expanded:
            # Шеврон вниз ▼
            points = [
                QPointF(chevron_x - 4, chevron_y - 2),
                QPointF(chevron_x + 4, chevron_y - 2),
                QPointF(chevron_x, chevron_y + 3)
            ]
        else:
            # Шеврон вправо ►
            points = [
                QPointF(chevron_x - 2, chevron_y - 4),
                QPointF(chevron_x - 2, chevron_y + 4),
                QPointF(chevron_x + 3, chevron_y)
            ]
        
        polygon = QPolygonF(points)
        painter.setBrush(color)
        painter.drawPolygon(polygon)
        
        painter.end()


class SideNavBar(QWidget):
    """Боковая панель навигации со сворачиванием"""

    # Сигналы
    section_changed = pyqtSignal(object)  # Эмитит PageName (или None для заголовков)
    pin_state_changed = pyqtSignal(bool)  # True = pinned, False = unpinned (floating)
    
    # Константы размеров
    EXPANDED_WIDTH = 220
    COLLAPSED_WIDTH = 56
    TRIGGER_WIDTH = 24  # Полоска-триггер для плавающего режима (достаточно широкая для hover)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.buttons = []
        self.current_section: SectionName | None = None
        self._is_pinned = True  # По умолчанию закреплено
        self._is_collapsed = False
        self._is_hovering = False
        self._is_floating = False  # Плавающий режим (открепленный)
        self._width_value = self.EXPANDED_WIDTH
        self._parent_widget = parent
        self._loading_state = False  # Флаг, чтобы не сохранять при загрузке
        # Ключи реестра для запоминания сворачивания групп
        # Используем SectionName для читаемости
        self._collapsible_registry_keys = {
            SectionName.STRATEGIES: "SidebarStrategiesExpanded",
            SectionName.MY_LISTS_HEADER: "SidebarMyListsExpanded",
            SectionName.DIAGNOSTICS: "SidebarDiagnosticsExpanded",
            SectionName.ABOUT: "SidebarAboutExpanded",
        }
        
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
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)  # Включаем hover события
        
        # Основной layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 16, 8, 8)
        layout.setSpacing(2)
        
        # Заголовок с кнопкой закрепления
        self.header_widget = QWidget()
        self.header_widget.setFixedHeight(60)  # Фиксированная высота для сохранения позиции
        header_layout = QHBoxLayout(self.header_widget)
        header_layout.setContentsMargins(14, 8, 4, 16)  # Левый отступ увеличен для выравнивания
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
        
        # ═══════════════════════════════════════════════════════════════
        # ПРОКРУЧИВАЕМАЯ ОБЛАСТЬ ДЛЯ НАВИГАЦИОННЫХ КНОПОК
        # ═══════════════════════════════════════════════════════════════
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollArea > QWidget > QWidget {
                background: transparent;
            }
            QScrollBar:vertical {
                background: transparent;
                width: 6px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 0.15);
                border-radius: 3px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(255, 255, 255, 0.25);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: transparent;
            }
        """)
        
        # Контейнер для кнопок внутри scroll area
        self.nav_container = QWidget()
        self.nav_container.setStyleSheet("background: transparent;")
        nav_layout = QVBoxLayout(self.nav_container)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setSpacing(2)
        
        # Навигационные кнопки с подпунктами
        # is_sub: False = основной пункт, True = подпункт,
        #          "collapsible" = секция со сворачиваемыми подпунктами,
        #          "collapsible_header" = текстовый заголовок со сворачиванием подпунктов
        self.sections = [
            (SectionName.HOME, "fa5s.home", "Главная", False),
            (SectionName.CONTROL, "fa5s.play-circle", "Управление", False),
            (SectionName.STRATEGIES, "fa5s.cog", "Стратегии", "collapsible"),
            (SectionName.STRATEGY_SORT, "fa5s.sliders-h", "Сортировка", True),
            (SectionName.PRESET_CONFIG, "fa5s.file-code", "Активный пресет", True),
            (SectionName.PRESETS, "mdi.folder-cog", "Мои пресеты", True),
            (SectionName.DIRECT_RUN, "fa5s.play", "Прямой запуск", True),
            (SectionName.HOSTLIST, "fa5s.list", "Hostlist", True),
            (SectionName.IPSET, "fa5s.server", "IPset", True),
            (SectionName.ORCHESTRA_LOCKED, "fa5s.lock", "Залоченные", True),
            (SectionName.ORCHESTRA_BLOCKED, "fa5s.ban", "Заблокированные", True),
            (SectionName.ORCHESTRA_RATINGS, "mdi.chart-bar", "Рейтинги", True),
            (SectionName.DPI_SETTINGS, "fa5s.cogs", "Настройки DPI", True),
            (SectionName.MY_LISTS_HEADER, None, "Кастомные настройки", "collapsible_header"),
            (SectionName.MY_CATEGORIES, "fa5s.folder-plus", "Мои категории", True),
            (SectionName.NETROGAT, "fa5s.ban", "Исключения", True),
            (SectionName.ORCHESTRA_WHITELIST, "fa5s.shield-alt", "Белый список", True),
            (SectionName.CUSTOM_HOSTLIST, "fa5s.plus-circle", "Мои hostlist", True),
            (SectionName.CUSTOM_IPSET, "fa5s.network-wired", "Мои ipset", True),
            (SectionName.EDITOR, "fa5s.edit", "Мои стратегии", True),
            (SectionName.BLOBS, "fa5s.cube", "Блобы", True),
            (SectionName.AUTOSTART, "fa5s.rocket", "Автозапуск", False),
            (SectionName.NETWORK, "fa5s.network-wired", "Сеть", False),
            (SectionName.DIAGNOSTICS, "fa5s.wifi", "Диагностика", "collapsible"),
            (SectionName.DNS_CHECK, "fa5s.search", "DNS подмена", True),
            (SectionName.HOSTS, "fa5s.globe", "Hosts", False),
            (SectionName.BLOCKCHECK, "fa5s.shield-alt", "BlockCheck", False),
            (SectionName.APPEARANCE, "fa5s.palette", "Оформление", False),
            (SectionName.PREMIUM, "fa5s.star", "Донат", False),
            (SectionName.LOGS, "fa5s.file-alt", "Логи", False),
            (SectionName.ABOUT, "fa5s.info-circle", "О программе", "collapsible"),
            (SectionName.SERVERS, "fa5s.sync-alt", "Обновления", True),
            (SectionName.HELP, "fa5s.question-circle", "Справка", True),
        ]

        self._section_widgets: dict[SectionName, QWidget] = {}
        self._header_labels = []  # Заголовки секций/групп для скрытия при сворачивании
        self._sub_buttons = []  # Подпункты для скрытия при сворачивании сайдбара
        self._blobs_button = None  # Ссылка на кнопку "Блобы" для управления видимостью
        self._control_button = None  # Кнопка "Управление" (скрывается в direct_zapret2)

        # Кнопки для переключения режима оркестратора
        self._strategies_button = None       # Кнопка "Стратегии" / "Оркестратор"
        self._strategy_sort_button = None    # Кнопка "Сортировка"
        self._preset_config_button = None    # Кнопка "Активный пресет"
        self._my_categories_button = None    # Кнопка "Мои категории"
        self._hostlist_button = None
        self._ipset_button = None
        self._editor_button = None
        self._orchestra_locked_button = None
        self._orchestra_blocked_button = None
        self._orchestra_ratings_button = None  # Кнопка "Рейтинги"
        self._dpi_settings_button = None
        self._netrogat_button = None         # Кнопка "Исключения"
        self._whitelist_button = None        # Кнопка "Белый список"
        self._custom_hostlist_button = None  # Кнопка "Мои hostlist"
        self._custom_ipset_button = None     # Кнопка "Мои ipset"
        self._presets_button = None          # Кнопка "Мои пресеты"
        self._direct_run_button = None       # Кнопка "Прямой запуск" (direct_zapret2)

        # Группы подпунктов для сворачивания
        self._collapsible_groups: dict[SectionName, list[QWidget]] = {}
        current_collapsible_parent: SectionName | None = None

        for section_name, icon, text, is_sub in self.sections:
            page_name = SECTION_TO_PAGE.get(section_name)

            if is_sub == "collapsible":
                # Сворачиваемая секция с подпунктами
                btn = CollapsibleNavButton(icon, text, self)
                btn.setMinimumHeight(36)
                btn.clicked.connect(lambda checked, sn=section_name: self._on_button_clicked(sn))
                btn.toggled.connect(lambda expanded, sn=section_name: self._on_group_toggled(sn, expanded))
                self.buttons.append(btn)
                nav_layout.addWidget(btn)
                self._section_widgets[section_name] = btn
                current_collapsible_parent = section_name
                self._collapsible_groups[section_name] = []
                if section_name == SectionName.STRATEGIES:
                    self._strategies_button = btn
            elif is_sub == "collapsible_header":
                header = CollapsibleHeader(text, self)
                nav_layout.addWidget(header)
                self.buttons.append(header)
                self._section_widgets[section_name] = header
                # Отдельная группа для этого заголовка
                current_collapsible_parent = section_name
                self._collapsible_groups[section_name] = []
                header.toggled.connect(lambda expanded, sn=section_name: self._on_group_toggled(sn, expanded))
                self._header_labels.append(header)
            elif is_sub:
                btn = SubNavButton(icon, text, self)
                btn.setMinimumHeight(28)
                btn.clicked.connect(lambda checked, sn=section_name: self._on_button_clicked(sn))
                self.buttons.append(btn)
                nav_layout.addWidget(btn)
                self._section_widgets[section_name] = btn

                self._sub_buttons.append(btn)  # Сохраняем для скрытия при сворачивании сайдбара
                # Добавляем в группу текущего родителя
                if current_collapsible_parent is not None:
                    self._collapsible_groups[current_collapsible_parent].append(btn)

                # Сохраняем ссылки на кнопки для управления видимостью
                if section_name == SectionName.STRATEGY_SORT:
                    self._strategy_sort_button = btn
                elif section_name == SectionName.PRESET_CONFIG:
                    self._preset_config_button = btn
                elif section_name == SectionName.MY_CATEGORIES:
                    self._my_categories_button = btn
                elif section_name == SectionName.BLOBS:
                    self._blobs_button = btn
                elif section_name == SectionName.HOSTLIST:
                    self._hostlist_button = btn
                elif section_name == SectionName.IPSET:
                    self._ipset_button = btn
                elif section_name == SectionName.EDITOR:
                    self._editor_button = btn
                elif section_name == SectionName.ORCHESTRA_LOCKED:
                    self._orchestra_locked_button = btn
                elif section_name == SectionName.ORCHESTRA_BLOCKED:
                    self._orchestra_blocked_button = btn
                elif section_name == SectionName.ORCHESTRA_RATINGS:
                    self._orchestra_ratings_button = btn
                elif section_name == SectionName.DPI_SETTINGS:
                    self._dpi_settings_button = btn
                elif section_name == SectionName.NETROGAT:
                    self._netrogat_button = btn
                elif section_name == SectionName.ORCHESTRA_WHITELIST:
                    self._whitelist_button = btn
                elif section_name == SectionName.CUSTOM_HOSTLIST:
                    self._custom_hostlist_button = btn
                elif section_name == SectionName.CUSTOM_IPSET:
                    self._custom_ipset_button = btn
                elif section_name == SectionName.PRESETS:
                    self._presets_button = btn
                elif section_name == SectionName.DIRECT_RUN:
                    self._direct_run_button = btn
            else:
                btn = NavButton(icon, text, self)
                btn.setMinimumHeight(36)
                btn.clicked.connect(lambda checked, sn=section_name: self._on_button_clicked(sn))
                self.buttons.append(btn)
                nav_layout.addWidget(btn)
                self._section_widgets[section_name] = btn
                current_collapsible_parent = None  # Сбрасываем родителя

                if section_name == SectionName.CONTROL:
                    self._control_button = btn

        # Выбираем кнопку HOME
        self.current_section = SectionName.HOME
        home_btn = self._section_widgets.get(SectionName.HOME)
        if home_btn is not None and hasattr(home_btn, "set_selected"):
            home_btn.set_selected(True)
        
        # Загружаем состояния сворачивания групп из реестра
        self._load_collapsible_state()

        # Обновляем видимость вкладок в зависимости от режима
        self.update_strategies_submenu_visibility()
        self.update_orchestra_visibility()
        self.update_presets_visibility()

        # Растягивающий спейсер внутри контейнера
        nav_layout.addStretch(1)
        
        self.scroll_area.setWidget(self.nav_container)
        layout.addWidget(self.scroll_area, 1)  # stretch=1 чтобы занимало всё доступное место
        
        # ═══════════════════════════════════════════════════════════════
        
        # Версия внизу (вне прокрутки)
        from config import APP_VERSION
        self.version_label = QLabel(f"v{APP_VERSION}")
        self.version_label.setStyleSheet("""
            QLabel {
                color: rgba(255, 255, 255, 0.4);
                font-size: 11px;
                padding: 4px 12px;
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
        w = int(width)
        
        if self._is_floating:
            # В плавающем режиме используем min/max для гибкости
            self.setMinimumWidth(w)
            self.setMaximumWidth(w)
        else:
            self.setFixedWidth(w)
        
        # Обновляем видимость текста (только для обычного режима)
        collapsed = width < (self.EXPANDED_WIDTH + self.COLLAPSED_WIDTH) / 2
        if collapsed != self._is_collapsed:
            self._is_collapsed = collapsed
            self._update_collapsed_state()
    
    panel_width = pyqtProperty(float, _get_panel_width, _set_panel_width)
    
    def _update_collapsed_state(self):
        """Обновляет состояние всех элементов при сворачивании/разворачивании"""
        # В плавающем режиме используем другую логику
        if self._is_floating:
            return
        
        # Обновляем основные кнопки (пропускаем None - заголовки секций)
        for btn in self.buttons:
            if btn is not None:
                btn.set_collapsed(self._is_collapsed)
        
        # Скрываем/показываем заголовки секций и подпункты
        for header in self._header_labels:
            header.setVisible(not self._is_collapsed)
        
        for sub_btn in self._sub_buttons:
            sub_btn.setVisible(not self._is_collapsed)
        
        # Скрываем текст заголовка и версии
        if self._is_collapsed:
            self.header_label.setText("Z")  # Короткий заголовок
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
            tooltip = "Открепить панель (плавающий режим)"
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
    
    def _load_collapsible_state(self):
        """Читает из реестра состояния свернутых групп"""
        try:
            import winreg
            from config import REGISTRY_PATH_GUI
            sidebar_key_path = rf"{REGISTRY_PATH_GUI}\Sidebar"
            key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, sidebar_key_path)
        except Exception:
            return

        self._loading_state = True
        for section_name, reg_value_name in self._collapsible_registry_keys.items():
            btn = self._section_widgets.get(section_name)
            if not isinstance(btn, (CollapsibleNavButton, CollapsibleHeader)):
                continue
            try:
                value, _ = winreg.QueryValueEx(key, reg_value_name)
                expanded = bool(value)
            except FileNotFoundError:
                expanded = True  # по умолчанию развёрнуто
            except Exception:
                expanded = True
            btn.set_expanded(expanded)
        self._loading_state = False

    def _save_collapsible_state(self, section_name: SectionName, expanded: bool):
        """Сохраняет в реестр состояние свернутой группы

        Args:
            section_name: имя collapsible-секции
            expanded: состояние развёрнутости
        """
        if section_name not in self._collapsible_registry_keys:
            return

        try:
            import winreg
            from config import REGISTRY_PATH_GUI
            sidebar_key_path = rf"{REGISTRY_PATH_GUI}\Sidebar"
            key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, sidebar_key_path)
            winreg.SetValueEx(key, self._collapsible_registry_keys[section_name], 0, winreg.REG_DWORD, int(bool(expanded)))
            winreg.CloseKey(key)
        except Exception:
            pass
    
    def _toggle_pin(self):
        """Переключает закрепление панели"""
        self._is_pinned = not self._is_pinned
        self._update_pin_button()
        
        if not self._is_pinned:
            # Включаем плавающий режим
            self._enable_floating_mode()
        else:
            # Выключаем плавающий режим
            self._disable_floating_mode()
        
        # Уведомляем родителя о смене режима
        self.pin_state_changed.emit(self._is_pinned)
    
    def _enable_floating_mode(self):
        """Включает плавающий режим - панель поверх контента"""
        from log import log
        log("SideNav: enabling floating mode", "DEBUG")
        
        self._is_floating = True
        
        # Поднимаем виджет наверх (поверх остальных)
        self.raise_()
        
        # Добавляем тень для визуального отделения
        self.setStyleSheet("""
            QWidget#sideNavBar {
                background-color: rgba(28, 28, 28, 0.98);
                border-right: 1px solid rgba(255, 255, 255, 0.1);
            }
        """)
        
        # Сразу скрываем после небольшой задержки
        log("Starting collapse timer (400ms)", "DEBUG")
        self._collapse_timer.start(400)
    
    def _disable_floating_mode(self):
        """Выключает плавающий режим - панель часть layout"""
        self._is_floating = False
        self._collapse_timer.stop()
        
        # Возвращаем обычный стиль
        self.setStyleSheet("""
            QWidget#sideNavBar {
                background-color: rgba(28, 28, 28, 0.85);
                border-right: 1px solid rgba(255, 255, 255, 0.06);
            }
        """)
        
        # Разворачиваем панель
        self._animate_width(self.EXPANDED_WIDTH)
        self._show_all_elements()
    
    def _do_collapse(self):
        """Сворачивает/скрывает панель"""
        from log import log
        log(f"SideNav _do_collapse: pinned={self._is_pinned}, hovering={self._is_hovering}, floating={self._is_floating}", "DEBUG")
        
        if not self._is_pinned and not self._is_hovering:
            if self._is_floating:
                # В плавающем режиме - полностью скрываем
                log(f"Collapsing to TRIGGER_WIDTH={self.TRIGGER_WIDTH}", "DEBUG")
                self._hide_all_elements()
                self._animate_width(self.TRIGGER_WIDTH)
            else:
                self._animate_width(self.COLLAPSED_WIDTH)
    
    def _do_expand(self):
        """Разворачивает панель"""
        from log import log
        from PyQt6.QtWidgets import QApplication
        
        log(f"SideNav _do_expand: floating={self._is_floating}, current_width={self._width_value}", "DEBUG")
        
        self._collapse_timer.stop()
        
        if self._is_floating:
            self.raise_()  # Поднимаем наверх в плавающем режиме
            log("SideNav raised to top", "DEBUG")
        
        # Показываем элементы
        self._show_all_elements()
        
        # Обновляем layout (без processEvents — иначе реентрантность с focus-событиями)
        self.updateGeometry()
        
        # Анимируем ширину
        self._animate_width(self.EXPANDED_WIDTH)
    
    def _hide_all_elements(self):
        """Скрывает все элементы панели (для плавающего режима)"""
        # Скрываем элементы, но НЕ scroll_area - он нужен для приёма событий мыши
        self.header_label.setVisible(False)
        self.header_widget.setVisible(False)
        self.pin_btn.setVisible(False)
        self.version_label.setVisible(False)
        
        # Скрываем содержимое, но оставляем scroll_area видимым для hover событий
        self.nav_container.setVisible(False)
        
        # Показываем тонкую линию-индикатор с градиентом
        self.setStyleSheet("""
            QWidget#sideNavBar {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(96, 205, 255, 0.2),
                    stop:1 rgba(50, 50, 50, 0.95));
                border-right: 2px solid rgba(96, 205, 255, 0.6);
            }
        """)
    
    def _show_all_elements(self):
        """Показывает все элементы панели"""
        self.header_widget.setVisible(True)
        self.header_label.setVisible(True)
        self.header_label.setText("Zapret")
        self.pin_btn.setVisible(True)
        self.nav_container.setVisible(True)
        self.scroll_area.setVisible(True)
        
        from config import APP_VERSION
        self.version_label.setVisible(True)
        self.version_label.setText(f"v{APP_VERSION}")
        
        # Показываем заголовки и подпункты
        for header in self._header_labels:
            header.setVisible(True)
        for sub_btn in self._sub_buttons:
            sub_btn.setVisible(True)
        
        # Возвращаем стиль
        if self._is_floating:
            self.setStyleSheet("""
                QWidget#sideNavBar {
                    background-color: rgba(28, 28, 28, 0.98);
                    border-right: 1px solid rgba(255, 255, 255, 0.1);
                }
            """)
        else:
            self.setStyleSheet("""
                QWidget#sideNavBar {
                    background-color: rgba(28, 28, 28, 0.85);
                    border-right: 1px solid rgba(255, 255, 255, 0.06);
                }
            """)
    
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
            self._collapse_timer.start(250)
        super().leaveEvent(event)

    def _on_group_toggled(self, parent_section: SectionName, expanded: bool):
        """Переключает видимость элементов группы (подпункты и заголовки)"""
        self._apply_group_visibility(parent_section)
        # Сохраняем состояние, если это не загрузка
        if not getattr(self, "_loading_state", False):
            self._save_collapsible_state(parent_section, expanded)

    def _refresh_nav_layout(self) -> None:
        """Форсирует перерасчёт layout для sidebar после массовых setVisible()."""
        try:
            lay = self.nav_container.layout()
            if lay is not None:
                lay.invalidate()
                lay.activate()
        except Exception:
            pass
        try:
            self.nav_container.updateGeometry()
            self.nav_container.adjustSize()
        except Exception:
            pass
        try:
            self.scroll_area.viewport().update()
        except Exception:
            pass

    @staticmethod
    def _prop_mode_visible_name() -> str:
        return "_mode_visible"

    def _set_mode_visible(self, widget: QWidget | None, visible: bool) -> None:
        if widget is None:
            return
        try:
            widget.setProperty(self._prop_mode_visible_name(), bool(visible))
        except Exception:
            pass

    def _get_mode_visible(self, widget: QWidget | None) -> bool:
        if widget is None:
            return False
        try:
            v = widget.property(self._prop_mode_visible_name())
        except Exception:
            v = None
        # If unset, default to visible.
        if v is None:
            return True
        return bool(v)

    def _is_group_expanded(self, parent_section: SectionName) -> bool:
        btn = self._section_widgets.get(parent_section)
        if btn is None:
            return True
        try:
            attr = getattr(btn, "is_expanded", None)
            if attr is None:
                return True
            # Support both @property and method-style implementations.
            if callable(attr):
                return bool(attr())
            return bool(attr)
        except Exception:
            return True
        return True

    def _apply_group_visibility(self, parent_section: SectionName) -> None:
        """
        Applies effective visibility for all widgets in a collapsible group.

        Effective = group_expanded AND mode_visible AND (not sidebar_collapsed for sub-buttons).
        """
        if parent_section not in self._collapsible_groups:
            return

        expanded = self._is_group_expanded(parent_section)
        for widget in self._collapsible_groups[parent_section]:
            try:
                if self._is_collapsed and widget in self._sub_buttons:
                    widget.setVisible(False)
                    continue
                widget.setVisible(bool(expanded and self._get_mode_visible(widget)))
            except Exception:
                pass

        self._refresh_nav_layout()

    def _apply_all_groups_visibility(self) -> None:
        for parent_section in list(self._collapsible_groups.keys()):
            self._apply_group_visibility(parent_section)

    def _update_mode_dependent_visibility(self) -> None:
        """Единая точка: пересчитать видимость вкладок по текущему режиму запуска."""
        try:
            from strategy_menu import get_strategy_launch_method
            method = get_strategy_launch_method()
        except Exception:
            method = ""

        is_direct = method in ("direct_zapret2", "direct_zapret2_orchestra", "direct_zapret1")
        is_orchestra = method in ("orchestra", "direct_zapret2_orchestra")
        is_full_orchestra = method == "orchestra"

        # In direct_zapret2 "Управление" is the main Strategies landing (subtab),
        # so hide the standalone sidebar entry to avoid duplication.
        show_control = method != "direct_zapret2"
        try:
            if self._control_button is not None:
                self._control_button.setVisible(bool(show_control))
        except Exception:
            pass
        if not show_control and self.current_section == SectionName.CONTROL:
            # If we just hid the selected section, keep sidebar highlight sensible.
            try:
                self.set_section_by_name(SectionName.STRATEGIES, emit_signal=False)
            except Exception:
                pass

        show_sorting = method in ("direct_zapret2_orchestra", "direct_zapret1")
        show_config = is_direct
        show_my_categories = is_direct
        show_blobs = is_direct
        if is_orchestra:
            # In orchestra modes, sorting/config are hidden only for full orchestra.
            show_sorting = not is_full_orchestra
            show_config = not is_full_orchestra
            show_my_categories = not is_full_orchestra

        # "Стратегии" sub-items
        self._set_mode_visible(self._blobs_button, show_blobs)
        self._set_mode_visible(self._preset_config_button, show_config)
        self._set_mode_visible(self._my_categories_button, show_my_categories)
        self._set_mode_visible(self._strategy_sort_button, show_sorting)

        # Hostlist/IPset/Editor hidden for orchestra modes
        self._set_mode_visible(self._hostlist_button, not is_orchestra)
        self._set_mode_visible(self._ipset_button, not is_orchestra)
        self._set_mode_visible(self._editor_button, not is_orchestra)

        # Orchestra-specific tabs
        self._set_mode_visible(self._orchestra_locked_button, is_orchestra)
        self._set_mode_visible(self._orchestra_blocked_button, is_orchestra)
        self._set_mode_visible(self._orchestra_ratings_button, is_orchestra)

        # Presets available only in direct_zapret2
        self._set_mode_visible(self._presets_button, method == "direct_zapret2")
        self._set_mode_visible(self._direct_run_button, method == "direct_zapret2")

        # My lists group
        self._set_mode_visible(self._netrogat_button, not is_orchestra)
        self._set_mode_visible(self._whitelist_button, is_orchestra)
        self._set_mode_visible(self._custom_hostlist_button, not is_orchestra)
        self._set_mode_visible(self._custom_ipset_button, not is_orchestra)

        # Re-apply group visibility (respects collapsed/expanded state).
        self._apply_all_groups_visibility()

        # Top-level button visibility changes may need a relayout too.
        self._refresh_nav_layout()
        
    def _on_button_clicked(self, section: SectionName):
        if section == self.current_section:
            # Allow re-click on collapsible groups (e.g. "Стратегии", "Диагностика")
            # to navigate to the group's main page even when the section is active.
            btn = self._section_widgets.get(section)
            # IMPORTANT: only do this for real user clicks. Programmatic calls like
            # `set_section_by_name()` should not trigger navigation.
            sender = None
            try:
                sender = self.sender()
            except Exception:
                sender = None

            if isinstance(btn, CollapsibleNavButton) and (sender is btn):
                page_name = SECTION_TO_PAGE.get(section)
                self.section_changed.emit(page_name)
            return

        self._select_section(section, emit_signal=True)

    def _select_section(self, section: SectionName, *, emit_signal: bool) -> None:
        """Selects a sidebar section and optionally emits navigation signal.

        NOTE: This method never triggers "re-click" navigation; it's meant for
        programmatic selection/highlighting. User-click re-navigation is handled
        in `_on_button_clicked`.
        """
        if section == self.current_section:
            return

        # Если выбираем подпункт, убедимся что его родительская группа развёрнута,
        # иначе подсветка будет "невидимой" при свернутой группе.
        try:
            for parent_section, children in SECTION_CHILDREN.items():
                if section in children:
                    parent_btn = self._section_widgets.get(parent_section)
                    if parent_btn is not None and hasattr(parent_btn, "set_expanded"):
                        parent_btn.set_expanded(True)
                    break
        except Exception:
            pass

        old_btn = self._section_widgets.get(self.current_section) if self.current_section else None
        if old_btn is not None and hasattr(old_btn, "set_selected"):
            old_btn.set_selected(False)

        new_btn = self._section_widgets.get(section)
        if new_btn is None or not hasattr(new_btn, "set_selected"):
            if old_btn is not None and hasattr(old_btn, "set_selected"):
                old_btn.set_selected(True)
            return

        self.current_section = section
        new_btn.set_selected(True)

        if emit_signal:
            # Эмитим сигнал с PageName (не числовым индексом!)
            page_name = SECTION_TO_PAGE.get(section)
            # Always emit - main_window handles None for collapsible groups dynamically
            self.section_changed.emit(page_name)

    def set_section_by_name(self, section: SectionName, *, emit_signal: bool = True):
        """Программно устанавливает раздел по SectionName"""
        self._select_section(section, emit_signal=emit_signal)

    def set_page(self, page_name: PageName):
        """Программно устанавливает раздел по PageName

        Это алиас для set_page_by_name для обратной совместимости.
        """
        self.set_page_by_name(page_name)

    def set_page_by_name(self, page_name: PageName, *, emit_signal: bool = True):
        """Программно устанавливает страницу по PageName

        Находит секцию, которая соответствует этой странице через SECTION_TO_PAGE
        и переключает sidebar на неё.
        """
        for section, page in SECTION_TO_PAGE.items():
            if page == page_name:
                self.set_section_by_name(section, emit_signal=emit_signal)
                return
    
    def update_strategies_submenu_visibility(self):
        """Обновляет видимость подпунктов в группе 'Стратегии' по режиму запуска.

        Управляет: 'Блобы', 'Конфиг', 'Сортировка'.
        """
        self._update_mode_dependent_visibility()

    def update_blobs_visibility(self):
        """Совместимость: раньше функция называлась update_blobs_visibility()."""
        self.update_strategies_submenu_visibility()

    def update_orchestra_visibility(self):
        """
        Обновляет видимость вкладок оркестратора.
        При включённом режиме оркестратора:
        - Скрываем: Hostlist, IPset, Редактор
        - Показываем: Залоченные, Заблокированные
        - Меняем название "Стратегии" на "Оркестратор" и иконку
        При обычном режиме - наоборот.

        ВАЖНО: direct_zapret2_orchestra - это гибридный режим, который:
        - Показывает вкладки оркестратора (Залоченные, Заблокированные)
        - НО НЕ скрывает Конфиг и Сортировка (они нужны для настройки стратегий)
        """
        try:
            from strategy_menu import get_strategy_launch_method
            method = get_strategy_launch_method()
            is_orchestra = method in ("orchestra", "direct_zapret2_orchestra")
        except Exception:
            method = ""
            is_orchestra = False
        is_full_orchestra = method == "orchestra"

        # Keep the old side-effects (title/icon), but centralize visibility rules.
        self._update_mode_dependent_visibility()

        # Меняем название и иконку секции "Стратегии" / "Оркестратор"
        if self._strategies_button:
            if is_orchestra:
                self._strategies_button._text = "Оркестратор"
                self._strategies_button.icon_name = "mdi.brain"
            else:
                self._strategies_button._text = "Стратегии"
                self._strategies_button.icon_name = "fa5s.cog"
            # Обновляем текст и иконку
            if not self._strategies_button._collapsed:
                self._strategies_button.setText(f"   {self._strategies_button._text}")
            self._strategies_button._update_style()

        # В группе "Мои списки":
        # (visibility rules handled by _update_mode_dependent_visibility)

    def update_presets_visibility(self):
        """
        Обновляет видимость вкладки 'Пресеты'.
        Пресеты доступны ТОЛЬКО в режиме direct_zapret2.
        """
        self._update_mode_dependent_visibility()


class SettingsCard(QFrame):
    """Карточка настроек в стиле Windows 11"""
    
    def __init__(self, title: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("settingsCard")
        # ✅ Политика размера: растягивается по горизонтали, но не бесконечно
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        
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
        # ✅ Кнопка не растягивается бесконечно - подстраивается под текст
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
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


class PulsingDot(QWidget):
    """Пульсирующая точка-индикатор с эффектом свечения"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._color = QColor("#888888")
        self._pulse_phase = 0.0  # 0.0 - 1.0
        self._is_pulsing = False

        # Размер виджета (больше для видимости пульсации)
        self.setFixedSize(28, 28)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Таймер для анимации
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate)
        self._timer.setInterval(30)  # ~33 FPS

    def set_color(self, color: str):
        """Устанавливает цвет точки"""
        self._color = QColor(color)
        self.update()

    def start_pulse(self):
        """Запускает анимацию пульсации"""
        if not self._is_pulsing:
            self._is_pulsing = True
            self._pulse_phase = 0.0
            self._timer.start()

    def stop_pulse(self):
        """Останавливает анимацию пульсации"""
        self._is_pulsing = False
        self._timer.stop()
        self._pulse_phase = 0.0
        self.update()

    def _animate(self):
        """Обновление анимации"""
        self._pulse_phase += 0.025  # Скорость анимации
        if self._pulse_phase >= 1.0:
            self._pulse_phase = 0.0
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        center_x = self.width() / 2
        center_y = self.height() / 2
        base_radius = 5

        # Рисуем пульсирующие кольца (если активна анимация)
        if self._is_pulsing:
            # Первое кольцо
            phase1 = self._pulse_phase
            opacity1 = max(0, 0.5 * (1.0 - phase1))
            radius1 = base_radius + (10 * phase1)

            pulse_color1 = QColor(self._color)
            pulse_color1.setAlphaF(opacity1)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(pulse_color1)
            painter.drawEllipse(
                int(center_x - radius1),
                int(center_y - radius1),
                int(radius1 * 2),
                int(radius1 * 2)
            )

            # Второе кольцо (со сдвигом фазы)
            phase2 = (self._pulse_phase + 0.5) % 1.0
            opacity2 = max(0, 0.5 * (1.0 - phase2))
            radius2 = base_radius + (10 * phase2)

            pulse_color2 = QColor(self._color)
            pulse_color2.setAlphaF(opacity2)
            painter.setBrush(pulse_color2)
            painter.drawEllipse(
                int(center_x - radius2),
                int(center_y - radius2),
                int(radius2 * 2),
                int(radius2 * 2)
            )

        # Внешнее свечение (статичное)
        glow_color = QColor(self._color)
        glow_color.setAlphaF(0.3)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(glow_color)
        painter.drawEllipse(
            int(center_x - base_radius - 2),
            int(center_y - base_radius - 2),
            int((base_radius + 2) * 2),
            int((base_radius + 2) * 2)
        )

        # Основная точка
        painter.setBrush(self._color)
        painter.drawEllipse(
            int(center_x - base_radius),
            int(center_y - base_radius),
            int(base_radius * 2),
            int(base_radius * 2)
        )

        # Блик для объёма
        highlight = QColor(255, 255, 255, 90)
        painter.setBrush(highlight)
        painter.drawEllipse(int(center_x - 2), int(center_y - 3), 3, 3)


class StatusIndicator(QWidget):
    """Индикатор статуса (точка + текст) с эффектом пульсации"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_status = "neutral"

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Пульсирующая точка-индикатор
        self.dot = PulsingDot()
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
        self._current_status = status

        colors = {
            'running': '#6ccb5f',  # Зеленый
            'stopped': '#ff6b6b',  # Красный
            'warning': '#ffc107',  # Желтый
            'neutral': '#888888',  # Серый
        }

        color = colors.get(status, colors['neutral'])
        self.dot.set_color(color)

        # Пульсация только для активного статуса
        if status == 'running':
            self.dot.start_pulse()
        else:
            self.dot.stop_pulse()
