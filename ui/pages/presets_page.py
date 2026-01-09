# ui/pages/presets_page.py
"""Страница управления пресетами настроек DPI"""

from datetime import datetime
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal, QSize, QPropertyAnimation, QEasingCurve, QTimer
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QPushButton, QLineEdit,
    QFileDialog, QMessageBox, QSizePolicy
)
import qtawesome as qta

from .base_page import BasePage
from ui.sidebar import SettingsCard
from log import log


class _DestructiveConfirmButton(QPushButton):
    """Кнопка опасного действия с двойным подтверждением (без модального окна)."""

    confirmed = pyqtSignal()

    def __init__(self, text: str, confirm_text: str, icon_name: str, parent=None):
        super().__init__(text, parent)
        self._default_text = text
        self._confirm_text = confirm_text
        self._icon_name = icon_name
        self._pending = False
        self._hovered = False

        self.setIconSize(QSize(14, 14))
        self.setFixedHeight(28)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._reset_timer = QTimer(self)
        self._reset_timer.setSingleShot(True)
        self._reset_timer.timeout.connect(self._reset_state)

        self._update_icon_and_style()

    def _reset_state(self):
        self._pending = False
        self.setEnabled(True)
        self.setText(self._default_text)
        self._update_icon_and_style()

    def _update_icon_and_style(self):
        if self._pending:
            icon_color = "#ff6b6b"
            bg = "rgba(255, 107, 107, 0.28)" if self._hovered else "rgba(255, 107, 107, 0.20)"
            text_color = "#ff6b6b"
        else:
            icon_color = "white"
            bg = "rgba(255, 255, 255, 0.15)" if self._hovered else "rgba(255, 255, 255, 0.08)"
            text_color = "#ffffff"

        self.setIcon(qta.icon(self._icon_name, color=icon_color))
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg};
                border: none;
                border-radius: 4px;
                color: {text_color};
                padding: 0 12px;
                font-size: 11px;
                font-weight: 600;
                font-family: 'Segoe UI Variable', 'Segoe UI', sans-serif;
            }}
        """)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self._pending:
                self._reset_timer.stop()
                self.setEnabled(False)
                self.setText("Удаление…")
                self._update_icon_and_style()
                self.confirmed.emit()
                QTimer.singleShot(800, self._reset_state)
            else:
                self._pending = True
                self.setText(self._confirm_text)
                self._update_icon_and_style()
                self._reset_timer.start(3000)
        super().mousePressEvent(event)

    def enterEvent(self, event):
        self._hovered = True
        self._update_icon_and_style()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        self._update_icon_and_style()
        super().leaveEvent(event)


class PresetCard(QFrame):
    """Карточка пресета в стиле Windows 11"""

    # Сигналы
    activate_clicked = pyqtSignal(str)  # name
    rename_clicked = pyqtSignal(str)    # name
    duplicate_clicked = pyqtSignal(str) # name
    delete_clicked = pyqtSignal(str)    # name
    export_clicked = pyqtSignal(str)    # name

    def __init__(self, name: str, description: str = "", modified: str = "",
                 is_active: bool = False, is_builtin: bool = False, parent=None):
        super().__init__(parent)
        self.preset_name = name
        self._is_active = is_active
        self._is_builtin = is_builtin
        self._hovered = False

        self.setObjectName("presetCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self._build_ui(name, description, modified)
        self._update_style()

    def _build_ui(self, name: str, description: str, modified: str):
        """Строит UI карточки"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 14, 16, 14)
        main_layout.setSpacing(10)

        # Верхняя строка: иконка + название + бейдж активности
        top_row = QHBoxLayout()
        top_row.setSpacing(10)

        # Иконка (звезда для активного, папка для остальных)
        icon_name = "fa5s.star" if self._is_active else "fa5s.file-alt"
        icon_color = "#60cdff" if self._is_active else "rgba(255, 255, 255, 0.6)"
        self.icon_label = QLabel()
        self.icon_label.setPixmap(qta.icon(icon_name, color=icon_color).pixmap(20, 20))
        self.icon_label.setFixedSize(24, 24)
        top_row.addWidget(self.icon_label)

        # Название
        self.name_label = QLabel(name)
        self.name_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 15px;
                font-weight: 600;
                font-family: 'Segoe UI Variable', 'Segoe UI', sans-serif;
            }
        """)
        top_row.addWidget(self.name_label)

        top_row.addStretch()

        # Бейдж "Активен"
        if self._is_active:
            active_badge = QLabel("Активен")
            active_badge.setStyleSheet("""
                QLabel {
                    color: #000000;
                    background-color: #60cdff;
                    font-size: 10px;
                    font-weight: 600;
                    padding: 3px 8px;
                    border-radius: 4px;
                }
            """)
            top_row.addWidget(active_badge)

        # Бейдж "Встроенный"
        if self._is_builtin:
            builtin_badge = QLabel("Встроенный")
            builtin_badge.setStyleSheet("""
                QLabel {
                    color: rgba(255, 255, 255, 0.7);
                    background-color: rgba(255, 255, 255, 0.1);
                    font-size: 10px;
                    font-weight: 500;
                    padding: 3px 8px;
                    border-radius: 4px;
                }
            """)
            top_row.addWidget(builtin_badge)

        main_layout.addLayout(top_row)

        # Описание (если есть)
        if description:
            desc_label = QLabel(description)
            desc_label.setStyleSheet("""
                QLabel {
                    color: rgba(255, 255, 255, 0.6);
                    font-size: 12px;
                }
            """)
            desc_label.setWordWrap(True)
            main_layout.addWidget(desc_label)

        # Дата изменения
        if modified:
            try:
                # Парсим ISO формат и форматируем красиво
                dt = datetime.fromisoformat(modified.replace('Z', '+00:00'))
                formatted_date = dt.strftime("%d.%m.%Y %H:%M")
            except:
                formatted_date = modified

            date_label = QLabel(f"Изменён: {formatted_date}")
            date_label.setStyleSheet("""
                QLabel {
                    color: rgba(255, 255, 255, 0.4);
                    font-size: 11px;
                }
            """)
            main_layout.addWidget(date_label)

        # Кнопки действий
        buttons_row = QHBoxLayout()
        buttons_row.setSpacing(8)

        # Кнопка активации (только для неактивных)
        if not self._is_active:
            self.activate_btn = self._create_action_button("Активировать", "fa5s.check")
            self.activate_btn.clicked.connect(lambda: self.activate_clicked.emit(self.preset_name))
            buttons_row.addWidget(self.activate_btn)

        # Переименовать (недоступно для встроенных)
        if not self._is_builtin:
            self.rename_btn = self._create_action_button("Переименовать", "fa5s.edit")
            self.rename_btn.clicked.connect(lambda: self.rename_clicked.emit(self.preset_name))
            buttons_row.addWidget(self.rename_btn)

        # Дублировать (доступно для всех)
        self.duplicate_btn = self._create_action_button("Дублировать", "fa5s.copy")
        self.duplicate_btn.clicked.connect(lambda: self.duplicate_clicked.emit(self.preset_name))
        buttons_row.addWidget(self.duplicate_btn)

        # Удалить (недоступно для активного и встроенных)
        if not self._is_active and not self._is_builtin:
            self.delete_btn = _DestructiveConfirmButton(
                "Удалить",
                confirm_text="Подтвердить",
                icon_name="fa5s.trash",
                parent=self,
            )
            self.delete_btn.confirmed.connect(lambda: self.delete_clicked.emit(self.preset_name))
            buttons_row.addWidget(self.delete_btn)

        # Экспорт (недоступно для встроенных)
        if not self._is_builtin:
            self.export_btn = self._create_action_button("Экспорт", "fa5s.file-export")
            self.export_btn.clicked.connect(lambda: self.export_clicked.emit(self.preset_name))
            buttons_row.addWidget(self.export_btn)

        buttons_row.addStretch()
        main_layout.addLayout(buttons_row)

    def _create_action_button(self, text: str, icon_name: str) -> QPushButton:
        """Создает кнопку действия в нейтральном стиле"""
        btn = QPushButton(text)
        btn.setIcon(qta.icon(icon_name, color="white"))
        btn.setIconSize(QSize(14, 14))
        btn.setFixedHeight(28)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.08);
                border: none;
                border-radius: 4px;
                color: #ffffff;
                padding: 0 12px;
                font-size: 11px;
                font-weight: 500;
                font-family: 'Segoe UI Variable', 'Segoe UI', sans-serif;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.15);
            }
            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 0.20);
            }
        """)
        return btn

    def _update_style(self):
        """Обновляет стиль карточки"""
        if self._is_active:
            bg = "rgba(96, 205, 255, 0.08)"
        elif self._hovered:
            bg = "rgba(255, 255, 255, 0.08)"
        else:
            bg = "rgba(255, 255, 255, 0.04)"

        self.setStyleSheet(f"""
            QFrame#presetCard {{
                background-color: {bg};
                border: none;
                border-radius: 8px;
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

    def mousePressEvent(self, event):
        """Двойной клик для активации"""
        if event.button() == Qt.MouseButton.LeftButton and not self._is_active:
            # Одиночный клик ничего не делает, используем кнопки
            pass
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        """Двойной клик активирует пресет"""
        if event.button() == Qt.MouseButton.LeftButton and not self._is_active:
            self.activate_clicked.emit(self.preset_name)
        super().mouseDoubleClickEvent(event)


class _RevealFrame(QFrame):
    """Animated show/hide container (Win11 Settings-like 'drop-down')."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMaximumHeight(0)
        self.setVisible(False)
        self._anim = QPropertyAnimation(self, b"maximumHeight", self)
        self._anim.setDuration(180)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._pending_hide = False
        self._anim.finished.connect(self._on_anim_finished)

    def _on_anim_finished(self):
        if self._pending_hide:
            self._pending_hide = False
            self.setVisible(False)
            return
        # Let the layout manage height after expand.
        self.setMaximumHeight(16777215)

    def set_open(self, open_: bool):
        self._anim.stop()
        self._pending_hide = False

        if open_:
            self.setVisible(True)
            self.setMaximumHeight(0)
            if self.layout():
                self.layout().activate()
            target = max(0, self.layout().sizeHint().height() if self.layout() else self.sizeHint().height())
            self._anim.setStartValue(self.maximumHeight())
            self._anim.setEndValue(target)
            self._anim.start()
            return

        start = self.maximumHeight()
        self._anim.setStartValue(start if start > 0 else max(0, self.sizeHint().height()))
        self._anim.setEndValue(0)
        self._pending_hide = True
        self._anim.start()


class _SegmentedChoice(QWidget):
    """Two-option segmented control."""

    changed = pyqtSignal(str)  # value

    def __init__(self, left_label: str, left_value: str, right_label: str, right_value: str, parent=None):
        super().__init__(parent)
        self._left_value = left_value
        self._right_value = right_value
        self._value = left_value

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._left_btn = QPushButton(left_label)
        self._right_btn = QPushButton(right_label)
        for btn in (self._left_btn, self._right_btn):
            btn.setFixedHeight(28)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setCheckable(True)

        self._left_btn.clicked.connect(lambda: self.set_value(self._left_value))
        self._right_btn.clicked.connect(lambda: self.set_value(self._right_value))

        layout.addWidget(self._left_btn)
        layout.addWidget(self._right_btn)

        self._update_styles()

    def value(self) -> str:
        return self._value

    def set_value(self, value: str, emit: bool = True):
        if value not in (self._left_value, self._right_value):
            return
        if value == self._value:
            return
        self._value = value
        self._update_styles()
        if emit:
            self.changed.emit(value)

    def _update_styles(self):
        active_style = """
            QPushButton {
                background: #60cdff;
                border: none;
                color: #000000;
                font-size: 11px;
                font-weight: 700;
                padding: 0 12px;
            }
        """
        inactive_style = """
            QPushButton {
                background: rgba(255, 255, 255, 0.08);
                border: none;
                color: rgba(255, 255, 255, 0.75);
                font-size: 11px;
                font-weight: 600;
                padding: 0 12px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.12);
            }
        """
        left_radius = "border-top-left-radius: 6px; border-bottom-left-radius: 6px;"
        right_radius = "border-top-right-radius: 6px; border-bottom-right-radius: 6px;"

        if self._value == self._left_value:
            self._left_btn.setStyleSheet(active_style.replace("}", left_radius + "}"))
            self._right_btn.setStyleSheet(inactive_style.replace("QPushButton {", "QPushButton { " + right_radius))
            self._left_btn.setChecked(True)
            self._right_btn.setChecked(False)
        else:
            self._left_btn.setStyleSheet(inactive_style.replace("QPushButton {", "QPushButton { " + left_radius))
            self._right_btn.setStyleSheet(active_style.replace("}", right_radius + "}"))
            self._left_btn.setChecked(False)
            self._right_btn.setChecked(True)


class PresetsPage(BasePage):
    """Страница управления пресетами настроек"""

    # Сигналы
    preset_switched = pyqtSignal(str)   # При переключении пресета
    preset_created = pyqtSignal(str)    # При создании
    preset_deleted = pyqtSignal(str)    # При удалении

    def __init__(self, parent=None):
        super().__init__("Пресеты настроек", "Сохраняйте и переключайте наборы настроек DPI", parent)

        self._preset_cards = []  # Список карточек для обновления
        self._manager = None     # Lazy init

        self._build_ui()
        self._load_presets()

    def _get_manager(self):
        """Получает или создает PresetManager"""
        if self._manager is None:
            from preset_zapret2 import PresetManager
            self._manager = PresetManager(
                on_preset_switched=self._on_preset_switched_callback,
                on_dpi_reload_needed=self._on_dpi_reload_needed
            )
        return self._manager

    def _build_ui(self):
        """Строит UI страницы"""

        # Карточка с активным пресетом
        self.active_card = SettingsCard("Активный пресет")
        # Без тонких рамок (Fluent-style)
        self.active_card.setStyleSheet("""
            QFrame#settingsCard {
                background-color: rgba(255, 255, 255, 0.04);
                border: none;
                border-radius: 8px;
            }
            QFrame#settingsCard:hover {
                background-color: rgba(255, 255, 255, 0.08);
                border: none;
            }
        """)
        active_layout = QHBoxLayout()
        active_layout.setSpacing(12)

        # Иконка
        active_icon = QLabel()
        active_icon.setPixmap(qta.icon('fa5s.star', color='#60cdff').pixmap(20, 20))
        active_layout.addWidget(active_icon)

        # Название активного пресета
        self.active_preset_label = QLabel("Загрузка...")
        self.active_preset_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 14px;
                font-weight: 500;
            }
        """)
        active_layout.addWidget(self.active_preset_label)

        active_layout.addStretch()

        self.active_card.add_layout(active_layout)
        self.add_widget(self.active_card)

        self.add_spacing(12)

        # Inline create/rename panel (replaces modal dialogs)
        self._action_mode: Optional[str] = None  # "create" | "rename"
        self._rename_source_name: Optional[str] = None

        self._action_reveal = _RevealFrame(self)
        self._action_reveal_layout = QVBoxLayout(self._action_reveal)
        self._action_reveal_layout.setContentsMargins(0, 0, 0, 0)
        self._action_reveal_layout.setSpacing(0)

        self._action_card = SettingsCard("")
        # Без тонких рамок (Fluent-style)
        self._action_card.setStyleSheet("""
            QFrame#settingsCard {
                background-color: rgba(255, 255, 255, 0.04);
                border: none;
                border-radius: 8px;
            }
            QFrame#settingsCard:hover {
                background-color: rgba(255, 255, 255, 0.08);
                border: none;
            }
        """)
        self._action_card.main_layout.setSpacing(10)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(10)

        self._action_icon = QLabel()
        self._action_icon.setPixmap(qta.icon("fa5s.plus", color="#60cdff").pixmap(18, 18))
        self._action_icon.setFixedSize(22, 22)
        header.addWidget(self._action_icon)

        self._action_title = QLabel("")
        self._action_title.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 14px;
                font-weight: 600;
                font-family: 'Segoe UI Variable', 'Segoe UI', sans-serif;
            }
        """)
        header.addWidget(self._action_title)
        header.addStretch(1)

        self._action_close_btn = QPushButton()
        self._action_close_btn.setIcon(qta.icon("fa5s.times", color="rgba(255,255,255,0.85)"))
        self._action_close_btn.setIconSize(QSize(12, 12))
        self._action_close_btn.setFixedSize(28, 28)
        self._action_close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._action_close_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.06);
                border: none;
                border-radius: 6px;
            }
            QPushButton:hover { background: rgba(255, 255, 255, 0.10); }
            QPushButton:pressed { background: rgba(255, 255, 255, 0.14); }
        """)
        self._action_close_btn.clicked.connect(self._hide_inline_action)
        header.addWidget(self._action_close_btn)

        self._action_card.add_layout(header)

        self._action_subtitle = QLabel("")
        self._action_subtitle.setStyleSheet("""
            QLabel {
                color: rgba(255, 255, 255, 0.6);
                font-size: 12px;
            }
        """)
        self._action_subtitle.setWordWrap(True)
        self._action_card.add_widget(self._action_subtitle)

        self._rename_from_label = QLabel("")
        self._rename_from_label.setStyleSheet("""
            QLabel {
                color: rgba(255, 255, 255, 0.55);
                font-size: 12px;
            }
        """)
        self._rename_from_label.setWordWrap(True)
        self._rename_from_label.hide()
        self._action_card.add_widget(self._rename_from_label)

        name_row = QVBoxLayout()
        name_row.setSpacing(6)
        name_label = QLabel("Название")
        name_label.setStyleSheet("color: rgba(255, 255, 255, 0.75); font-size: 12px;")
        name_row.addWidget(name_label)

        self._name_input = QLineEdit()
        self._name_input.setPlaceholderText("Введите название пресета…")
        self._name_input.setStyleSheet("""
            QLineEdit {
                background-color: rgba(255, 255, 255, 0.06);
                border: none;
                border-radius: 8px;
                color: #ffffff;
                padding: 10px 12px;
                font-size: 13px;
                font-family: 'Segoe UI Variable', 'Segoe UI', sans-serif;
            }
            QLineEdit:focus {
                background-color: rgba(255, 255, 255, 0.08);
            }
        """)
        self._name_input.textChanged.connect(lambda: self._set_inline_error(""))
        self._name_input.returnPressed.connect(self._submit_inline_action)
        name_row.addWidget(self._name_input)
        self._action_card.add_layout(name_row)

        # Create source selector (create mode only)
        self._source_container = QWidget()
        source_row = QHBoxLayout(self._source_container)
        source_row.setContentsMargins(0, 4, 0, 0)
        source_row.setSpacing(12)
        source_label = QLabel("Создать на основе")
        source_label.setStyleSheet("color: rgba(255, 255, 255, 0.75); font-size: 12px;")
        source_row.addWidget(source_label)
        source_row.addStretch(1)
        self._create_source = _SegmentedChoice("Текущего активного", "current", "Пустого", "empty", self)
        source_row.addWidget(self._create_source)
        self._action_card.add_widget(self._source_container)

        self._action_error = QLabel("")
        self._action_error.setStyleSheet("""
            QLabel {
                color: #ff6b6b;
                font-size: 12px;
            }
        """)
        self._action_error.setWordWrap(True)
        self._action_error.hide()
        self._action_card.add_widget(self._action_error)

        actions = QHBoxLayout()
        actions.setContentsMargins(0, 6, 0, 0)
        actions.setSpacing(10)
        actions.addStretch(1)

        self._action_cancel_btn = self._create_main_button("Отмена", "fa5s.times", accent=False)
        self._action_cancel_btn.setFixedHeight(32)
        self._action_cancel_btn.clicked.connect(self._hide_inline_action)
        actions.addWidget(self._action_cancel_btn)

        self._action_submit_btn = self._create_main_button("Готово", "fa5s.check", accent=True)
        self._action_submit_btn.setFixedHeight(32)
        self._action_submit_btn.clicked.connect(self._submit_inline_action)
        actions.addWidget(self._action_submit_btn)

        self._action_card.add_layout(actions)

        self._action_reveal_layout.addWidget(self._action_card)
        self.add_widget(self._action_reveal)

        # Секция "Все пресеты"
        self.add_section_title("Все пресеты")

        # Контейнер для карточек пресетов
        self.presets_container = QWidget()
        self.presets_layout = QVBoxLayout(self.presets_container)
        self.presets_layout.setContentsMargins(0, 0, 0, 0)
        self.presets_layout.setSpacing(8)

        self.add_widget(self.presets_container)

        self.add_spacing(16)

        # Кнопки внизу
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(12)

        # Создать новый
        self.create_btn = self._create_main_button("Создать новый", "fa5s.plus", accent=True)
        self.create_btn.clicked.connect(self._on_create_clicked)
        buttons_layout.addWidget(self.create_btn)

        # Импорт
        self.import_btn = self._create_main_button("Импорт из файла", "fa5s.file-import")
        self.import_btn.clicked.connect(self._on_import_clicked)
        buttons_layout.addWidget(self.import_btn)

        buttons_layout.addStretch()

        buttons_widget = QWidget()
        buttons_widget.setLayout(buttons_layout)
        self.add_widget(buttons_widget)

        self.layout.addStretch()

    def _create_main_button(self, text: str, icon_name: str, accent: bool = False) -> QPushButton:
        """Создает основную кнопку действия"""
        btn = QPushButton(text)

        icon_color = "#000000" if accent else "white"
        btn.setIcon(qta.icon(icon_name, color=icon_color))
        btn.setIconSize(QSize(16, 16))
        btn.setFixedHeight(36)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)

        if accent:
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #60cdff;
                    border: none;
                    border-radius: 6px;
                    color: #000000;
                    padding: 0 20px;
                    font-size: 13px;
                    font-weight: 600;
                    font-family: 'Segoe UI Variable', 'Segoe UI', sans-serif;
                }
                QPushButton:hover {
                    background-color: rgba(96, 205, 255, 0.9);
                }
                QPushButton:pressed {
                    background-color: rgba(96, 205, 255, 0.7);
                }
            """)
        else:
            btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(255, 255, 255, 0.08);
                    border: none;
                    border-radius: 6px;
                    color: #ffffff;
                    padding: 0 20px;
                    font-size: 13px;
                    font-weight: 600;
                    font-family: 'Segoe UI Variable', 'Segoe UI', sans-serif;
                }
                QPushButton:hover {
                    background-color: rgba(255, 255, 255, 0.15);
                }
                QPushButton:pressed {
                    background-color: rgba(255, 255, 255, 0.20);
                }
            """)

        return btn

    def _hide_inline_action(self):
        self._action_mode = None
        self._rename_source_name = None
        self._action_error.hide()
        self._action_error.setText("")
        self._action_reveal.set_open(False)

    def _set_inline_error(self, text: str):
        self._action_error.setText(text)
        self._action_error.setVisible(bool(text))

    def _show_inline_action_create(self):
        self._action_mode = "create"
        self._rename_source_name = None
        self._set_inline_error("")

        self._action_icon.setPixmap(qta.icon("fa5s.plus", color="#60cdff").pixmap(18, 18))
        self._action_title.setText("Создать новый пресет")
        self._action_subtitle.setText("Сохраните текущие настройки как отдельный пресет, чтобы быстро переключаться между конфигурациями.")

        self._rename_from_label.hide()
        self._source_container.show()
        self._create_source.set_value("current", emit=False)

        self._name_input.clear()
        self._name_input.setPlaceholderText("Например: Игры / YouTube / Дом")

        self._action_submit_btn.setText("Создать")
        self._action_submit_btn.setIcon(qta.icon("fa5s.check", color="#000000"))

        self._action_reveal.set_open(True)
        self.ensureWidgetVisible(self._action_reveal)
        self._name_input.setFocus()

    def _show_inline_action_rename(self, current_name: str):
        self._action_mode = "rename"
        self._rename_source_name = current_name
        self._set_inline_error("")

        self._action_icon.setPixmap(qta.icon("fa5s.edit", color="#60cdff").pixmap(18, 18))
        self._action_title.setText("Переименовать пресет")
        self._action_subtitle.setText("Имя пресета отображается в списке и используется для переключения.")

        self._rename_from_label.setText(f"Текущее имя: {current_name}")
        self._rename_from_label.show()
        self._source_container.hide()

        self._name_input.setText(current_name)
        self._name_input.selectAll()
        self._name_input.setPlaceholderText("Новое имя…")

        self._action_submit_btn.setText("Переименовать")
        self._action_submit_btn.setIcon(qta.icon("fa5s.check", color="#000000"))

        self._action_reveal.set_open(True)
        self.ensureWidgetVisible(self._action_reveal)
        self._name_input.setFocus()

    def _submit_inline_action(self):
        mode = self._action_mode
        if mode not in ("create", "rename"):
            return

        name = self._name_input.text().strip()
        if not name:
            self._set_inline_error("Введите название.")
            return

        try:
            manager = self._get_manager()

            if mode == "create":
                if manager.preset_exists(name):
                    self._set_inline_error(f"Пресет '{name}' уже существует.")
                    return

                from_current = self._create_source.value() == "current"
                preset = manager.create_preset(name, from_current=from_current)
                if not preset:
                    self._set_inline_error("Не удалось создать пресет.")
                    return

                log(f"Создан пресет '{name}'", "INFO")
                self.preset_created.emit(name)
                self._hide_inline_action()
                self._load_presets()
                return

            if mode == "rename":
                old_name = self._rename_source_name
                if not old_name:
                    self._set_inline_error("Неизвестный пресет для переименования.")
                    return
                if name == old_name:
                    self._hide_inline_action()
                    return
                if manager.preset_exists(name):
                    self._set_inline_error(f"Пресет '{name}' уже существует.")
                    return

                if not manager.rename_preset(old_name, name):
                    self._set_inline_error("Не удалось переименовать пресет.")
                    return

                log(f"Пресет '{old_name}' переименован в '{name}'", "INFO")
                self._hide_inline_action()
                self._load_presets()
                return

        except Exception as e:
            log(f"Ошибка сохранения пресета: {e}", "ERROR")
            QMessageBox.critical(self, "Ошибка", f"Ошибка: {e}")

    def _load_presets(self):
        """Загружает и отображает список пресетов"""
        try:
            manager = self._get_manager()
            preset_names = manager.list_presets()
            active_name = manager.get_active_preset_name()

            # Обновляем лейбл активного пресета
            if active_name:
                self.active_preset_label.setText(active_name)
            else:
                self.active_preset_label.setText("Не выбран")

            # Очищаем старые карточки
            for card in self._preset_cards:
                card.deleteLater()
            self._preset_cards.clear()

            # Создаем карточки для каждого пресета
            for name in preset_names:
                preset = manager.load_preset(name)
                if preset:
                    card = PresetCard(
                        name=name,
                        description=preset.description,
                        modified=preset.modified,
                        is_active=(name == active_name),
                        is_builtin=preset.is_builtin,
                        parent=self
                    )

                    # Подключаем сигналы
                    card.activate_clicked.connect(self._on_activate_preset)
                    card.rename_clicked.connect(self._on_rename_preset)
                    card.duplicate_clicked.connect(self._on_duplicate_preset)
                    card.delete_clicked.connect(self._on_delete_preset)
                    card.export_clicked.connect(self._on_export_preset)

                    self.presets_layout.addWidget(card)
                    self._preset_cards.append(card)

            # Если нет пресетов - показываем подсказку
            if not preset_names:
                empty_label = QLabel("Нет сохранённых пресетов. Создайте первый!")
                empty_label.setStyleSheet("""
                    QLabel {
                        color: rgba(255, 255, 255, 0.5);
                        font-size: 13px;
                        padding: 20px;
                    }
                """)
                empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.presets_layout.addWidget(empty_label)

        except Exception as e:
            log(f"Ошибка загрузки пресетов: {e}", "ERROR")

    def _on_create_clicked(self):
        """Обработчик создания нового пресета"""
        if self._action_mode == "create" and self._action_reveal.isVisible():
            self._hide_inline_action()
        else:
            self._show_inline_action_create()

    def _on_import_clicked(self):
        """Обработчик импорта пресета"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Импортировать пресет",
            "",
            "Preset files (*.txt);;All files (*.*)"
        )

        if file_path:
            try:
                manager = self._get_manager()

                # Получаем имя из файла
                name = Path(file_path).stem

                # Проверяем существование
                if manager.preset_exists(name):
                    result = QMessageBox.question(
                        self, "Пресет существует",
                        f"Пресет '{name}' уже существует. Импортировать с другим именем?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                    )
                    if result == QMessageBox.StandardButton.Yes:
                        # Добавляем суффикс
                        counter = 1
                        while manager.preset_exists(f"{name}_{counter}"):
                            counter += 1
                        name = f"{name}_{counter}"
                    else:
                        return

                if manager.import_preset(Path(file_path), name):
                    log(f"Импортирован пресет '{name}'", "INFO")
                    self.preset_created.emit(name)
                    self._load_presets()
                else:
                    QMessageBox.warning(self, "Ошибка", "Не удалось импортировать пресет")

            except Exception as e:
                log(f"Ошибка импорта пресета: {e}", "ERROR")
                QMessageBox.critical(self, "Ошибка", f"Ошибка импорта: {e}")

    def _on_activate_preset(self, name: str):
        """Активирует пресет"""
        try:
            manager = self._get_manager()

            if manager.switch_preset(name, reload_dpi=True):
                log(f"Активирован пресет '{name}'", "INFO")
                self.preset_switched.emit(name)
                self._load_presets()
            else:
                QMessageBox.warning(self, "Ошибка", f"Не удалось активировать пресет '{name}'")

        except Exception as e:
            log(f"Ошибка активации пресета: {e}", "ERROR")
            QMessageBox.critical(self, "Ошибка", f"Ошибка: {e}")

    def _on_rename_preset(self, name: str):
        """Переименовывает пресет"""
        if self._action_mode == "rename" and self._rename_source_name == name and self._action_reveal.isVisible():
            self._hide_inline_action()
        else:
            self._show_inline_action_rename(name)

    def _on_duplicate_preset(self, name: str):
        """Дублирует пресет"""
        try:
            manager = self._get_manager()

            # Генерируем имя для копии
            counter = 1
            new_name = f"{name} (копия)"
            while manager.preset_exists(new_name):
                counter += 1
                new_name = f"{name} (копия {counter})"

            if manager.duplicate_preset(name, new_name):
                log(f"Пресет '{name}' дублирован как '{new_name}'", "INFO")
                self.preset_created.emit(new_name)
                self._load_presets()
            else:
                QMessageBox.warning(self, "Ошибка", "Не удалось дублировать пресет")

        except Exception as e:
            log(f"Ошибка дублирования пресета: {e}", "ERROR")
            QMessageBox.critical(self, "Ошибка", f"Ошибка: {e}")

    def _on_delete_preset(self, name: str):
        """Удаляет пресет"""
        try:
            manager = self._get_manager()

            if manager.delete_preset(name):
                log(f"Удалён пресет '{name}'", "INFO")
                self.preset_deleted.emit(name)
                self._load_presets()
            else:
                QMessageBox.warning(self, "Ошибка", "Не удалось удалить пресет")

        except Exception as e:
            log(f"Ошибка удаления пресета: {e}", "ERROR")
            QMessageBox.critical(self, "Ошибка", f"Ошибка: {e}")

    def _on_export_preset(self, name: str):
        """Экспортирует пресет"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Экспортировать пресет",
            f"{name}.txt",
            "Preset files (*.txt);;All files (*.*)"
        )

        if file_path:
            try:
                manager = self._get_manager()

                if manager.export_preset(name, Path(file_path)):
                    log(f"Экспортирован пресет '{name}' в {file_path}", "INFO")
                    QMessageBox.information(self, "Успех", f"Пресет экспортирован:\n{file_path}")
                else:
                    QMessageBox.warning(self, "Ошибка", "Не удалось экспортировать пресет")

            except Exception as e:
                log(f"Ошибка экспорта пресета: {e}", "ERROR")
                QMessageBox.critical(self, "Ошибка", f"Ошибка: {e}")

    def _on_preset_switched_callback(self, name: str):
        """Колбэк при переключении пресета (из PresetManager)"""
        pass  # Сигнал уже эмитится из _on_activate_preset

    def _on_dpi_reload_needed(self):
        """Колбэк для перезапуска DPI"""
        try:
            # Ищем dpi_controller в родительских виджетах
            widget = self
            while widget:
                if hasattr(widget, 'dpi_controller'):
                    widget.dpi_controller.restart_dpi_async()
                    log("DPI перезапущен после смены пресета", "INFO")
                    return
                widget = widget.parent()

            # Альтернативный способ через QApplication
            from PyQt6.QtWidgets import QApplication
            for w in QApplication.topLevelWidgets():
                if hasattr(w, 'dpi_controller'):
                    w.dpi_controller.restart_dpi_async()
                    log("DPI перезапущен после смены пресета", "INFO")
                    return

            log("DPI контроллер не найден для перезапуска", "WARNING")

        except Exception as e:
            log(f"Ошибка перезапуска DPI: {e}", "ERROR")

    def refresh(self):
        """Обновляет список пресетов"""
        self._load_presets()
