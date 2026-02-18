# ui/pages/presets_page.py
"""Страница управления пресетами настроек DPI"""

from datetime import datetime
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, QEvent, pyqtSignal, QSize, QTimer, QFileSystemWatcher
from PyQt6.QtGui import QColor, QIcon
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QPushButton, QLineEdit,
    QFileDialog, QSizePolicy
)
import qtawesome as qta

from .base_page import BasePage
from ui.compat_widgets import ActionButton, PrimaryActionButton, SettingsCard, set_tooltip
from ui.theme import get_theme_tokens, get_card_gradient_qss, get_selected_surface_gradient_qss
from log import log

try:
    from qfluentwidgets import (
        BodyLabel, CaptionLabel, StrongBodyLabel, LineEdit, MessageBox, InfoBar,
        SegmentedWidget, TransparentToolButton, FluentIcon,
        MessageBoxBase, SubtitleLabel,
    )
    _HAS_FLUENT = True
except ImportError:
    BodyLabel = QLabel
    CaptionLabel = QLabel
    StrongBodyLabel = QLabel
    LineEdit = QLineEdit
    MessageBox = None
    InfoBar = None
    SegmentedWidget = None
    TransparentToolButton = None
    FluentIcon = None
    MessageBoxBase = None
    SubtitleLabel = QLabel
    _HAS_FLUENT = False


# ── Icon cache ───────────────────────────────────────────────────────────
# qta.icon() renders SVG every call; cache the resulting QIcons globally.
_icon_cache: dict[str, QIcon] = {}


def _cached_icon(name: str, color) -> QIcon:
    """Returns a cached QIcon for the given qtawesome name + color key."""
    key = f"{name}|{color}"
    icon = _icon_cache.get(key)
    if icon is None:
        icon = qta.icon(name, color=color)
        _icon_cache[key] = icon
    return icon


def _cached_pixmap(name: str, color, w: int = 20, h: int = 20):
    """Returns a cached QPixmap via _cached_icon."""
    return _cached_icon(name, color).pixmap(w, h)


def _accent_fg_for_tokens(tokens) -> str:
    """Chooses readable foreground for the current accent color."""
    try:
        return str(tokens.accent_fg)
    except Exception:
        return "rgba(18, 18, 18, 0.90)"


class _DestructiveConfirmButton(QPushButton):
    """Кнопка опасного действия с двойным подтверждением (без модального окна)."""

    confirmed = pyqtSignal()

    def __init__(self, text: str, confirm_text: str, icon_name: str, busy_text: str = "Удаление…", parent=None):
        super().__init__(text, parent)
        self._default_text = text
        self._confirm_text = confirm_text
        self._icon_name = icon_name
        self._busy_text = busy_text
        self._pending = False
        self._hovered = False
        self._applying_theme_styles = False

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
        if self._applying_theme_styles:
            return

        self._applying_theme_styles = True
        try:
            tokens = get_theme_tokens()
            if self._pending:
                icon_color = "#ff6b6b"
                bg = "rgba(255, 107, 107, 0.28)" if self._hovered else "rgba(255, 107, 107, 0.20)"
                text_color = "#ff6b6b"
                border = f"1px solid {tokens.surface_border}"
            else:
                icon_color = tokens.fg
                bg = tokens.surface_bg_hover if self._hovered else tokens.surface_bg
                text_color = tokens.fg
                border = f"1px solid {tokens.surface_border_hover if self._hovered else tokens.surface_border}"

            self.setIcon(_cached_icon(self._icon_name, icon_color))
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {bg};
                    border: {border};
                    border-radius: 4px;
                    color: {text_color};
                    padding: 0 12px;
                    font-size: 11px;
                    font-weight: 600;
                    font-family: 'Segoe UI Variable', 'Segoe UI', sans-serif;
                }}
            """)
        finally:
            self._applying_theme_styles = False

    def changeEvent(self, event):  # noqa: N802 (Qt override)
        try:
            if event.type() in (QEvent.Type.StyleChange, QEvent.Type.PaletteChange):
                if self._applying_theme_styles:
                    return super().changeEvent(event)
                self._update_icon_and_style()
        except Exception:
            pass
        super().changeEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self._pending:
                self._reset_timer.stop()
                self.setEnabled(False)
                self.setText(self._busy_text)
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


class _DestructiveIconConfirmButton(QPushButton):
    """Icon-only destructive action with double-confirm (no modal window)."""

    confirmed = pyqtSignal()

    def __init__(
        self,
        icon_name: str,
        tooltip: str,
        confirm_tooltip: str = "Нажмите ещё раз для подтверждения",
        busy_tooltip: str = "Выполняется…",
        parent=None,
    ):
        super().__init__(parent)
        self._icon_name = icon_name
        self._base_tooltip = tooltip
        self._confirm_tooltip = confirm_tooltip
        self._busy_tooltip = busy_tooltip
        self._pending = False
        self._hovered = False
        self._applying_theme_styles = False

        self.setText("")
        self.setIconSize(QSize(14, 14))
        self.setFixedSize(28, 28)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._reset_timer = QTimer(self)
        self._reset_timer.setSingleShot(True)
        self._reset_timer.timeout.connect(self._reset_state)

        self._update_icon_and_style()

    def _reset_state(self):
        self._pending = False
        self.setEnabled(True)
        self._update_icon_and_style()

    def _update_icon_and_style(self):
        if self._applying_theme_styles:
            return

        self._applying_theme_styles = True
        try:
            tokens = get_theme_tokens()
            if self.isEnabled():
                if self._pending:
                    icon_color = "#ff6b6b"
                    bg = "rgba(255, 107, 107, 0.28)" if self._hovered else "rgba(255, 107, 107, 0.20)"
                    border = "none"
                    set_tooltip(self, f"{self._base_tooltip}\n{self._confirm_tooltip}")
                else:
                    icon_color = tokens.fg
                    bg = tokens.surface_bg_hover if self._hovered else tokens.surface_bg
                    border = f"1px solid {tokens.surface_border_hover if self._hovered else tokens.surface_border}"
                    set_tooltip(self, self._base_tooltip)
            else:
                icon_color = "#ff6b6b"
                bg = "rgba(255, 107, 107, 0.18)"
                border = "none"
                set_tooltip(self, self._busy_tooltip)

            self.setIcon(_cached_icon(self._icon_name, icon_color))
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {bg};
                    border: {border};
                    border-radius: 6px;
                }}
            """)
        finally:
            self._applying_theme_styles = False

    def changeEvent(self, event):  # noqa: N802 (Qt override)
        try:
            if event.type() in (QEvent.Type.StyleChange, QEvent.Type.PaletteChange):
                if self._applying_theme_styles:
                    return super().changeEvent(event)
                self._update_icon_and_style()
        except Exception:
            pass
        super().changeEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self._pending:
                self._reset_timer.stop()
                self.setEnabled(False)
                self._update_icon_and_style()
                self.confirmed.emit()
                QTimer.singleShot(800, self._reset_state)
            else:
                self._pending = True
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
    reset_clicked = pyqtSignal(str)     # name
    delete_clicked = pyqtSignal(str)    # name
    export_clicked = pyqtSignal(str)    # name

    def __init__(
        self,
        name: str,
        description: str = "",
        modified: str = "",
        is_active: bool = False,
        is_builtin: bool = False,
        compact_actions: bool = False,
        parent=None,
    ):
        super().__init__(parent)
        self.preset_name = name
        self._is_active = is_active
        self._is_builtin = False  # builtin concept removed; parameter kept for compat
        self._compact_actions = compact_actions
        self._hovered = False
        self._applying_theme_styles = False
        self._active_badge: QLabel | None = None

        self.setObjectName("presetCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self._build_ui(name, description, modified)
        self._update_style()

    def _build_ui(self, name: str, description: str, modified: str):
        """Строит UI карточки"""
        tokens = get_theme_tokens()

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 10, 16, 10)
        main_layout.setSpacing(8)

        # Верхняя строка: иконка + название + бейдж активности
        top_row = QHBoxLayout()
        top_row.setSpacing(10)

        # Иконка (звезда для активного, папка для остальных)
        icon_name = "fa5s.star" if self._is_active else "fa5s.file-alt"
        icon_color = tokens.accent_hex if self._is_active else tokens.fg_muted
        self.icon_label = QLabel()
        self.icon_label.setPixmap(_cached_pixmap(icon_name, icon_color, 20, 20))
        self.icon_label.setFixedSize(24, 24)
        top_row.addWidget(self.icon_label)

        # Название
        self.name_label = StrongBodyLabel(name)
        # Allow long names to shrink/clamp so right-side badges/actions stay visible.
        self.name_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.name_label.setMinimumWidth(0)
        top_row.addWidget(self.name_label)

        # Дата изменения (inline, справа от названия)
        if modified:
            try:
                dt = datetime.fromisoformat(modified.replace('Z', '+00:00'))
                formatted_date = dt.strftime("%d.%m.%Y %H:%M")
            except Exception:
                formatted_date = modified

            date_label = CaptionLabel(formatted_date)
            top_row.addWidget(date_label)

        top_row.addStretch()

        # Бейдж "Активен"
        if self._is_active:
            self._active_badge = QLabel("Активен")
            self._active_badge.setStyleSheet(
                f"""
                QLabel {{
                    color: {_accent_fg_for_tokens(tokens)};
                    background-color: {tokens.accent_hex};
                    font-size: 10px;
                    font-weight: 600;
                    padding: 3px 8px;
                    border-radius: 4px;
                }}
                """
            )
            top_row.addWidget(self._active_badge)

        # Compact actions: small icon buttons on the right.
        if self._compact_actions:
            actions_row = QHBoxLayout()
            actions_row.setContentsMargins(0, 0, 0, 0)
            actions_row.setSpacing(6)

            actions_widget = QWidget()
            actions_widget.setLayout(actions_row)
            actions_widget.setStyleSheet("background: transparent;")
            self._actions_widget = actions_widget

            rename_btn = self._create_icon_action_button("fa5s.edit", "Переименовать")
            rename_btn.clicked.connect(lambda: self.rename_clicked.emit(self.preset_name))
            actions_row.addWidget(rename_btn)

            duplicate_btn = self._create_icon_action_button("fa5s.copy", "Дублировать")
            duplicate_btn.clicked.connect(lambda: self.duplicate_clicked.emit(self.preset_name))
            actions_row.addWidget(duplicate_btn)

            reset_btn = _DestructiveIconConfirmButton(
                icon_name="fa5s.broom",
                tooltip=(
                    "Сбросить\n"
                    "Сбросит этот пресет к настройкам из шаблона.\n"
                    "Пресет будет активирован."
                ),
                confirm_tooltip="Нажмите ещё раз для подтверждения",
                busy_tooltip="Сброс…",
                parent=self,
            )
            reset_btn.confirmed.connect(lambda: self.reset_clicked.emit(self.preset_name))
            actions_row.addWidget(reset_btn)

            if not self._is_active:
                delete_btn = _DestructiveIconConfirmButton(
                    icon_name="fa5s.trash",
                    tooltip="Удалить",
                    confirm_tooltip="Нажмите ещё раз для подтверждения",
                    busy_tooltip="Удаление…",
                    parent=self,
                )
                delete_btn.confirmed.connect(lambda: self.delete_clicked.emit(self.preset_name))
                actions_row.addWidget(delete_btn)

            export_btn = self._create_icon_action_button("fa5s.file-export", "Экспорт")
            export_btn.clicked.connect(lambda: self.export_clicked.emit(self.preset_name))
            actions_row.addWidget(export_btn)

            top_row.addWidget(actions_widget)
        else:
            self._actions_widget = None

        main_layout.addLayout(top_row)

        # Описание (если есть)
        if description:
            desc_label = BodyLabel(description)
            desc_label.setWordWrap(True)
            main_layout.addWidget(desc_label)

        if not self._compact_actions:
            # Кнопки действий
            buttons_row = QHBoxLayout()
            buttons_row.setSpacing(8)

            # Переименовать
            self.rename_btn = self._create_action_button("Переименовать", "fa5s.edit")
            self.rename_btn.clicked.connect(lambda: self.rename_clicked.emit(self.preset_name))
            buttons_row.addWidget(self.rename_btn)

            # Дублировать
            self.duplicate_btn = self._create_action_button("Дублировать", "fa5s.copy")
            self.duplicate_btn.clicked.connect(lambda: self.duplicate_clicked.emit(self.preset_name))
            buttons_row.addWidget(self.duplicate_btn)

            # Сбросить
            self.reset_btn = _DestructiveConfirmButton(
                "Сбросить",
                confirm_text="Подтвердить",
                icon_name="fa5s.broom",
                busy_text="Сброс…",
                parent=self,
            )
            set_tooltip(
                self.reset_btn,
                "Сбросит этот пресет к настройкам из шаблона.\n"
                "Пресет будет активирован."
            )
            self.reset_btn.confirmed.connect(lambda: self.reset_clicked.emit(self.preset_name))
            buttons_row.addWidget(self.reset_btn)

            # Удалить (недоступно для активного)
            if not self._is_active:
                self.delete_btn = _DestructiveConfirmButton(
                    "Удалить",
                    confirm_text="Подтвердить",
                    icon_name="fa5s.trash",
                    busy_text="Удаление…",
                    parent=self,
                )
                self.delete_btn.confirmed.connect(lambda: self.delete_clicked.emit(self.preset_name))
                buttons_row.addWidget(self.delete_btn)

            # Экспорт
            self.export_btn = self._create_action_button("Экспорт", "fa5s.file-export")
            self.export_btn.clicked.connect(lambda: self.export_clicked.emit(self.preset_name))
            buttons_row.addWidget(self.export_btn)

            buttons_row.addStretch()
            main_layout.addLayout(buttons_row)

    def _create_action_button(self, text: str, icon_name: str):
        """Создает кнопку действия в нейтральном стиле"""
        btn = ActionButton(text, icon_name)
        btn.setProperty("_preset_icon_name", icon_name)
        btn.setFixedHeight(28)
        return btn

    def _create_icon_action_button(self, icon_name: str, tooltip: str, icon_color: str = "white"):
        """Создает кнопку-иконку действия"""
        try:
            icon = qta.icon(icon_name, color=get_theme_tokens().fg)
            btn = TransparentToolButton(icon)
        except Exception:
            btn = TransparentToolButton()
        btn.setProperty("_preset_icon_name", icon_name)
        set_tooltip(btn, tooltip)
        btn.setIconSize(QSize(14, 14))
        btn.setFixedSize(28, 28)
        btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        return btn

    def _refresh_action_buttons_theme(self) -> None:
        tokens = get_theme_tokens()
        from PyQt6.QtWidgets import QAbstractButton
        for btn in self.findChildren(QAbstractButton):
            try:
                icon_name = btn.property("_preset_icon_name")
                if icon_name:
                    btn.setIcon(_cached_icon(str(icon_name), tokens.fg))
            except Exception:
                pass

    def _update_style(self):
        """Обновляет стиль карточки"""
        if self._applying_theme_styles:
            return

        tokens = get_theme_tokens()

        if self._is_active:
            if self._hovered:
                bg = get_selected_surface_gradient_qss(tokens.theme_name, hover=True)
            else:
                bg = get_selected_surface_gradient_qss(tokens.theme_name)
            border = f"1px solid {tokens.accent_hex}"
        else:
            bg = get_card_gradient_qss(tokens.theme_name, hover=self._hovered)
            border = f"1px solid {tokens.surface_border_hover if self._hovered else tokens.surface_border}"

        self._applying_theme_styles = True
        try:
            self.setStyleSheet(
                f"""
                QFrame#presetCard {{
                    background: {bg};
                    border: {border};
                    border-radius: 8px;
                }}
                """
            )
        finally:
            self._applying_theme_styles = False

    def _apply_theme(self) -> None:
        tokens = get_theme_tokens()

        try:
            icon_name = "fa5s.star" if self._is_active else "fa5s.file-alt"
            icon_color = tokens.accent_hex if self._is_active else tokens.fg_muted
            self.icon_label.setPixmap(_cached_pixmap(icon_name, icon_color, 20, 20))
        except Exception:
            pass

        try:
            if self._active_badge is not None:
                self._active_badge.setStyleSheet(
                    f"""
                    QLabel {{
                        color: {_accent_fg_for_tokens(tokens)};
                        background-color: {tokens.accent_hex};
                        font-size: 10px;
                        font-weight: 600;
                        padding: 3px 8px;
                        border-radius: 4px;
                    }}
                    """
                )
        except Exception:
            pass

        try:
            self._refresh_action_buttons_theme()
        except Exception:
            pass

        self._update_style()

    def changeEvent(self, event):  # noqa: N802 (Qt override)
        try:
            if event.type() in (QEvent.Type.StyleChange, QEvent.Type.PaletteChange):
                if self._applying_theme_styles:
                    return super().changeEvent(event)
                self._apply_theme()
        except Exception:
            pass
        super().changeEvent(event)

    def enterEvent(self, event):
        self._hovered = True
        self._update_style()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        self._update_style()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        """ЛКМ по карточке активирует пресет (если не активен)."""
        if event.button() == Qt.MouseButton.LeftButton and not self._is_active:
            child = self.childAt(event.pos())
            if isinstance(child, QPushButton):
                super().mousePressEvent(event)
                return

            actions_widget = getattr(self, "_actions_widget", None)
            if actions_widget is not None and child is not None:
                # Prevent accidental activation when clicking around action icons.
                try:
                    if child == actions_widget or actions_widget.isAncestorOf(child):
                        super().mousePressEvent(event)
                        return
                except Exception:
                    pass

            self.activate_clicked.emit(self.preset_name)
            event.accept()
            return

        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        # Single click already activates.
        super().mouseDoubleClickEvent(event)


class _CreatePresetDialog(MessageBoxBase):
    """WinUI диалог создания нового пресета."""

    def __init__(self, existing_names: list, parent=None):
        super().__init__(parent)
        self._existing_names = list(existing_names)
        self._source = "current"

        self.titleLabel = SubtitleLabel("Новый пресет", self)
        self.subtitleLabel = BodyLabel(
            "Сохраните текущие настройки как отдельный пресет, "
            "чтобы быстро переключаться между конфигурациями.",
            self,
        )
        self.subtitleLabel.setWordWrap(True)

        name_label = BodyLabel("Название", self)
        self.nameEdit = LineEdit(self)
        self.nameEdit.setPlaceholderText("Например: Игры / YouTube / Дом")
        self.nameEdit.setClearButtonEnabled(True)

        source_row = QHBoxLayout()
        source_label = BodyLabel("Создать на основе", self)
        source_row.addWidget(source_label)
        source_row.addStretch()
        self._source_seg = SegmentedWidget(self)
        self._source_seg.addItem("current", "Текущего активного")
        self._source_seg.addItem("empty", "Пустого")
        self._source_seg.setCurrentItem("current")
        self._source_seg.currentItemChanged.connect(lambda k: setattr(self, "_source", k))
        source_row.addWidget(self._source_seg)

        self.warningLabel = CaptionLabel("", self)
        self.warningLabel.setTextColor("#cf1010", QColor(255, 28, 32))
        self.warningLabel.hide()

        self.viewLayout.addWidget(self.titleLabel)
        self.viewLayout.addWidget(self.subtitleLabel)
        self.viewLayout.addWidget(name_label)
        self.viewLayout.addWidget(self.nameEdit)
        self.viewLayout.addLayout(source_row)
        self.viewLayout.addWidget(self.warningLabel)

        self.yesButton.setText("Создать")
        self.cancelButton.setText("Отмена")
        self.widget.setMinimumWidth(420)

    def validate(self) -> bool:
        name = self.nameEdit.text().strip()
        if not name:
            self.warningLabel.setText("Введите название.")
            self.warningLabel.show()
            return False
        if name in self._existing_names:
            self.warningLabel.setText(f"Пресет «{name}» уже существует.")
            self.warningLabel.show()
            return False
        self.warningLabel.hide()
        return True


class _RenamePresetDialog(MessageBoxBase):
    """WinUI диалог переименования пресета."""

    def __init__(self, current_name: str, existing_names: list, parent=None):
        super().__init__(parent)
        self._current_name = str(current_name or "")
        self._existing_names = list(existing_names)

        self.titleLabel = SubtitleLabel("Переименовать", self)
        self.subtitleLabel = BodyLabel(
            "Имя пресета отображается в списке и используется для переключения.",
            self,
        )
        self.subtitleLabel.setWordWrap(True)

        from_label = CaptionLabel(f"Текущее имя: {self._current_name}", self)
        name_label = BodyLabel("Новое имя", self)
        self.nameEdit = LineEdit(self)
        self.nameEdit.setText(self._current_name)
        self.nameEdit.selectAll()
        self.nameEdit.setPlaceholderText("Новое имя…")
        self.nameEdit.setClearButtonEnabled(True)

        self.warningLabel = CaptionLabel("", self)
        self.warningLabel.setTextColor("#cf1010", QColor(255, 28, 32))
        self.warningLabel.hide()

        self.viewLayout.addWidget(self.titleLabel)
        self.viewLayout.addWidget(self.subtitleLabel)
        self.viewLayout.addWidget(from_label)
        self.viewLayout.addWidget(name_label)
        self.viewLayout.addWidget(self.nameEdit)
        self.viewLayout.addWidget(self.warningLabel)

        self.yesButton.setText("Переименовать")
        self.cancelButton.setText("Отмена")
        self.widget.setMinimumWidth(420)

    def validate(self) -> bool:
        name = self.nameEdit.text().strip()
        if not name:
            self.warningLabel.setText("Введите название.")
            self.warningLabel.show()
            return False
        if name == self._current_name:
            return True
        if name in self._existing_names:
            self.warningLabel.setText(f"Пресет «{name}» уже существует.")
            self.warningLabel.show()
            return False
        self.warningLabel.hide()
        return True


class PresetsPage(BasePage):
    """Страница управления пресетами настроек"""

    # Сигналы
    preset_switched = pyqtSignal(str)   # При переключении пресета
    preset_created = pyqtSignal(str)    # При создании
    preset_deleted = pyqtSignal(str)    # При удалении

    def __init__(self, parent=None):
        super().__init__("Управление пресетами", "Здесь Вы можете сохранять, переключать, экспортировать и импортировать пресеты (наборы настроек Zapret). Любой из пресетов добавляются в файл preset_zapret2.txt, который по умолчанию являются активным пресетом (содержимое файла просто заменяется целиком). Изменить это нельзя.", parent)

        self._preset_cards = []  # Список карточек для обновления
        self._manager = None     # Lazy init
        self._ui_dirty = True    # needs rebuild on next show
        self._file_watcher: Optional[QFileSystemWatcher] = None
        self._watcher_active = False
        self._watcher_reload_timer = QTimer(self)
        self._watcher_reload_timer.setSingleShot(True)
        self._watcher_reload_timer.timeout.connect(self._reload_presets_from_watcher)

        self._build_ui()
        self._load_presets()

        # Subscribe to central store signals
        try:
            from preset_zapret2.preset_store import get_preset_store
            store = get_preset_store()
            store.presets_changed.connect(self._on_store_changed)
            store.preset_switched.connect(self._on_store_switched)
        except Exception:
            pass

    def _on_store_changed(self):
        """Central store says the preset list changed."""
        self._ui_dirty = True
        if self.isVisible():
            self._load_presets()

    def _on_store_switched(self, _name: str):
        """Central store says the active preset switched."""
        self._ui_dirty = True
        if self.isVisible():
            self._load_presets()

    def showEvent(self, event):
        """При открытии страницы включаем мониторинг папки пресетов."""
        super().showEvent(event)
        self._start_watching_presets()
        if self._ui_dirty:
            self._load_presets()

    def hideEvent(self, event):
        """При скрытии страницы отключаем мониторинг (экономия ресурсов)."""
        self._stop_watching_presets()
        super().hideEvent(event)

    def _get_manager(self):
        """Получает или создает PresetManager"""
        if self._manager is None:
            from preset_zapret2 import PresetManager
            self._manager = PresetManager(
                on_preset_switched=self._on_preset_switched_callback,
                on_dpi_reload_needed=self._on_dpi_reload_needed
            )
        return self._manager

    def _start_watching_presets(self):
        """Запускает мониторинг папки presets/ и .txt файлов внутри."""
        try:
            if self._watcher_active:
                return

            from preset_zapret2 import get_presets_dir
            presets_dir = get_presets_dir()
            presets_dir.mkdir(parents=True, exist_ok=True)

            if not self._file_watcher:
                self._file_watcher = QFileSystemWatcher(self)
                self._file_watcher.directoryChanged.connect(self._on_presets_dir_changed)
                self._file_watcher.fileChanged.connect(self._on_preset_file_changed)

            dir_path = str(presets_dir)
            if dir_path not in self._file_watcher.directories():
                self._file_watcher.addPath(dir_path)

            self._watcher_active = True
            self._update_watched_preset_files()

        except Exception as e:
            log(f"Ошибка запуска мониторинга пресетов: {e}", "DEBUG")

    def _stop_watching_presets(self):
        """Останавливает мониторинг папки presets/."""
        try:
            if not self._watcher_active:
                return

            if self._file_watcher:
                directories = self._file_watcher.directories()
                files = self._file_watcher.files()
                if directories:
                    self._file_watcher.removePaths(directories)
                if files:
                    self._file_watcher.removePaths(files)

            self._watcher_active = False

        except Exception as e:
            log(f"Ошибка остановки мониторинга пресетов: {e}", "DEBUG")

    def _update_watched_preset_files(self):
        """Обновляет список отслеживаемых .txt файлов."""
        try:
            if not self._watcher_active or not self._file_watcher:
                return

            from preset_zapret2 import get_presets_dir
            presets_dir = get_presets_dir()

            current_files = self._file_watcher.files()
            if current_files:
                self._file_watcher.removePaths(current_files)

            preset_files = []
            if presets_dir.exists():
                preset_files.extend([str(p) for p in presets_dir.glob("*.txt") if p.is_file()])
            if preset_files:
                self._file_watcher.addPaths(preset_files)

        except Exception as e:
            log(f"Ошибка обновления мониторинга пресетов: {e}", "DEBUG")

    def _on_presets_dir_changed(self, path: str):
        """Изменения в папке presets/ (создание/удаление/переименование)."""
        try:
            log(f"Обнаружены изменения в папке пресетов: {path}", "DEBUG")
            self._update_watched_preset_files()
            self._schedule_presets_reload()
        except Exception as e:
            log(f"Ошибка обработки изменений папки пресетов: {e}", "DEBUG")

    def _on_preset_file_changed(self, path: str):
        """Изменение содержимого пресета."""
        try:
            log(f"Обнаружены изменения в пресете: {Path(path).name}", "DEBUG")
            self._schedule_presets_reload()
        except Exception as e:
            log(f"Ошибка обработки изменений пресета: {e}", "DEBUG")

    def _schedule_presets_reload(self, delay_ms: int = 500):
        """Дебаунс: пересобираем UI списка пресетов после серии изменений."""
        try:
            self._watcher_reload_timer.stop()
            self._watcher_reload_timer.start(delay_ms)
        except Exception as e:
            log(f"Ошибка планирования обновления пресетов: {e}", "DEBUG")

    def _reload_presets_from_watcher(self):
        """Перезагружает список пресетов после файловых изменений."""
        if not self.isVisible():
            return
        try:
            from preset_zapret2.preset_store import get_preset_store
            get_preset_store().notify_presets_changed()
        except Exception:
            self._load_presets()
        # После atomic-write некоторые пути отваливаются из watcher → пересобрать.
        self._update_watched_preset_files()

    def _build_ui(self):
        """Строит UI страницы"""

        tokens = get_theme_tokens()

        # Быстрый доступ к посту с актуальными конфигами
        configs_card = SettingsCard()
        configs_layout = QHBoxLayout()
        configs_layout.setSpacing(12)

        self._configs_icon = QLabel()
        self._configs_icon.setPixmap(qta.icon("fa5b.telegram", color=tokens.accent_hex).pixmap(18, 18))
        configs_layout.addWidget(self._configs_icon)

        configs_title = StrongBodyLabel("Обменивайтесь категориями на нашем форуме-сайте через Telegram-бота: безопасно и анонимно")
        configs_title.setWordWrap(True)
        configs_title.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        configs_title.setMinimumWidth(0)
        configs_layout.addWidget(configs_title, 1)

        get_configs_btn = ActionButton("Получить конфиги", "fa5s.external-link-alt", accent=True)
        get_configs_btn.setFixedHeight(36)
        get_configs_btn.clicked.connect(self._open_new_configs_post)
        configs_layout.addWidget(get_configs_btn)

        configs_card.add_layout(configs_layout)
        self.add_widget(configs_card)

        self.add_spacing(12)

        # Карточка с активным пресетом
        self.active_card = SettingsCard("Активный пресет")
        active_layout = QHBoxLayout()
        active_layout.setSpacing(12)

        # Иконка
        self._active_icon = QLabel()
        self._active_icon.setPixmap(qta.icon('fa5s.star', color=tokens.accent_hex).pixmap(20, 20))
        active_layout.addWidget(self._active_icon)

        # Название активного пресета
        self.active_preset_label = BodyLabel("Загрузка...")
        active_layout.addWidget(self.active_preset_label)

        active_layout.addStretch()

        self.active_card.add_layout(active_layout)
        self.add_widget(self.active_card)

        self.add_spacing(12)

        # Короткая подсказка как работают официальные пресеты/копии
        info_card = SettingsCard("Как это работает")
        info_layout = QHBoxLayout()
        info_layout.setSpacing(12)
        self._info_icon = QLabel()
        self._info_icon.setPixmap(qta.icon("fa5s.info-circle", color=tokens.fg_muted).pixmap(16, 16))
        info_layout.addWidget(self._info_icon)
        info_text = BodyLabel(
            "Официальные пресеты — это шаблоны (их нельзя изменить). "
            "Если вы меняете настройки, автоматически создаётся редактируемая копия "
            "в виде отдельного пресета «(копия)»."
        )
        info_text.setWordWrap(True)
        info_layout.addWidget(info_text, 1)
        info_card.add_layout(info_layout)
        self.add_widget(info_card)

        self.add_spacing(12)

        # Секция "Шаблоны"
        self.add_section_title("Шаблоны")

        self.official_container = QWidget()
        self.official_layout = QVBoxLayout(self.official_container)
        self.official_layout.setContentsMargins(0, 0, 0, 0)
        self.official_layout.setSpacing(8)
        self.add_widget(self.official_container)

        self.add_spacing(12)

        # Секция "Пользовательские"
        self.add_section_title("Пользовательские")

        # Контейнер для карточек пользовательских пресетов
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

        self._apply_theme_styles()

    def _apply_theme_styles(self) -> None:
        tokens = get_theme_tokens()

        # Top icons
        try:
            if hasattr(self, "_configs_icon") and self._configs_icon is not None:
                self._configs_icon.setPixmap(qta.icon("fa5b.telegram", color=tokens.accent_hex).pixmap(18, 18))
        except Exception:
            pass

        try:
            if hasattr(self, "_active_icon") and self._active_icon is not None:
                self._active_icon.setPixmap(qta.icon("fa5s.star", color=tokens.accent_hex).pixmap(20, 20))
        except Exception:
            pass

        try:
            if hasattr(self, "_info_icon") and self._info_icon is not None:
                self._info_icon.setPixmap(qta.icon("fa5s.info-circle", color=tokens.fg_muted).pixmap(16, 16))
        except Exception:
            pass

        # qfluentwidgets widgets manage their own theming — no manual CSS overrides needed.

    def changeEvent(self, event):  # noqa: N802 (Qt override)
        try:
            if event.type() in (QEvent.Type.StyleChange, QEvent.Type.PaletteChange):
                self._apply_theme_styles()
        except Exception:
            pass
        super().changeEvent(event)

    def _create_main_button(self, text: str, icon_name: str, accent: bool = False):
        """Создает основную кнопку действия"""
        if accent:
            btn = PrimaryActionButton(text, icon_name)
        else:
            btn = ActionButton(text, icon_name)
        return btn

    def _load_presets(self):
        """Загружает и отображает список пресетов"""
        self._ui_dirty = False
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

            # Очищаем контейнеры (на случай если были empty label'ы)
            def _clear_layout(layout):
                while layout.count():
                    item = layout.takeAt(0)
                    if item.widget():
                        item.widget().deleteLater()

            _clear_layout(self.official_layout)
            _clear_layout(self.presets_layout)

            # Создаем карточки
            user_items = []

            for name in preset_names:
                preset = manager.load_preset(name)
                if preset:
                    card = PresetCard(
                        name=name,
                        description=preset.description,
                        modified=preset.modified,
                        is_active=(name == active_name),
                        parent=self
                    )

                    # Подключаем сигналы
                    card.activate_clicked.connect(self._on_activate_preset)
                    card.rename_clicked.connect(self._on_rename_preset)
                    card.duplicate_clicked.connect(self._on_duplicate_preset)
                    card.reset_clicked.connect(self._on_reset_preset)
                    card.delete_clicked.connect(self._on_delete_preset)
                    card.export_clicked.connect(self._on_export_preset)

                    user_items.append(card)
                    self._preset_cards.append(card)

            for card in user_items:
                self.presets_layout.addWidget(card)

            # Если нет пользовательских пресетов - показываем подсказку
            if not user_items:
                empty_label = BodyLabel("Нет пользовательских пресетов. Создайте новый или сделайте копию официального.")
                empty_label.setContentsMargins(20, 20, 20, 20)
                empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.presets_layout.addWidget(empty_label)

        except Exception as e:
            log(f"Ошибка загрузки пресетов: {e}", "ERROR")

    def _on_create_clicked(self):
        """Обработчик создания нового пресета"""
        try:
            existing = self._get_manager().list_presets()
        except Exception:
            existing = []

        dlg = _CreatePresetDialog(existing, parent=self.window())
        if not dlg.exec():
            return

        name = dlg.nameEdit.text().strip()
        from_current = dlg._source == "current"
        try:
            manager = self._get_manager()
            preset = manager.create_preset(name, from_current=from_current)
            if preset:
                log(f"Создан пресет '{name}'", "INFO")
                self.preset_created.emit(name)
                self._load_presets()
            else:
                InfoBar.error(title="Ошибка", content="Не удалось создать пресет.", parent=self.window())
        except Exception as e:
            log(f"Ошибка создания пресета: {e}", "ERROR")
            InfoBar.error(title="Ошибка", content=f"Ошибка: {e}", parent=self.window())

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
                    box = MessageBox(
                        "Пресет существует",
                        f"Пресет '{name}' уже существует. Импортировать с другим именем?",
                        self.window(),
                    )
                    if box.exec():
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
                    InfoBar.warning(title="Ошибка", content="Не удалось импортировать пресет", parent=self.window())

            except Exception as e:
                log(f"Ошибка импорта пресета: {e}", "ERROR")
                InfoBar.error(title="Ошибка", content=f"Ошибка импорта: {e}", parent=self.window())

    def _on_activate_preset(self, name: str):
        """Активирует пресет"""
        try:
            manager = self._get_manager()

            if manager.switch_preset(name, reload_dpi=True):
                log(f"Активирован пресет '{name}'", "INFO")
                self.preset_switched.emit(name)
                self._load_presets()
            else:
                InfoBar.warning(title="Ошибка", content=f"Не удалось активировать пресет '{name}'", parent=self.window())

        except Exception as e:
            log(f"Ошибка активации пресета: {e}", "ERROR")
            InfoBar.error(title="Ошибка", content=f"Ошибка: {e}", parent=self.window())

    def _on_rename_preset(self, name: str):
        """Переименовывает пресет"""
        try:
            existing = self._get_manager().list_presets()
        except Exception:
            existing = []

        dlg = _RenamePresetDialog(name, existing, parent=self.window())
        if not dlg.exec():
            return

        new_name = dlg.nameEdit.text().strip()
        if new_name == name:
            return
        try:
            manager = self._get_manager()
            if not manager.rename_preset(name, new_name):
                InfoBar.error(title="Ошибка", content="Не удалось переименовать пресет.", parent=self.window())
                return
            log(f"Пресет '{name}' переименован в '{new_name}'", "INFO")
            self._load_presets()
        except Exception as e:
            log(f"Ошибка переименования пресета: {e}", "ERROR")
            InfoBar.error(title="Ошибка", content=f"Ошибка: {e}", parent=self.window())

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
                InfoBar.warning(title="Ошибка", content="Не удалось дублировать пресет", parent=self.window())

        except Exception as e:
            log(f"Ошибка дублирования пресета: {e}", "ERROR")
            InfoBar.error(title="Ошибка", content=f"Ошибка: {e}", parent=self.window())

    def _on_reset_preset(self, name: str):
        """Сбрасывает пресет к шаблону Default и активирует его."""
        try:
            manager = self._get_manager()

            if not manager.reset_preset_to_default_template(name):
                InfoBar.warning(title="Ошибка", content="Не удалось сбросить пресет к настройкам Default", parent=self.window())
                return

            log(f"Сброшен пресет '{name}' к Default", "INFO")

            # Уведомить MainWindow для обновления связанных страниц.
            self.preset_switched.emit(name)

            # Обновить список и бейджи
            self._load_presets()

        except Exception as e:
            log(f"Ошибка сброса пресета: {e}", "ERROR")
            InfoBar.error(title="Ошибка", content=f"Ошибка: {e}", parent=self.window())

    def _on_delete_preset(self, name: str):
        """Удаляет пресет"""
        try:
            manager = self._get_manager()

            if manager.delete_preset(name):
                log(f"Удалён пресет '{name}'", "INFO")
                self.preset_deleted.emit(name)
                self._load_presets()
            else:
                InfoBar.warning(title="Ошибка", content="Не удалось удалить пресет", parent=self.window())

        except Exception as e:
            log(f"Ошибка удаления пресета: {e}", "ERROR")
            InfoBar.error(title="Ошибка", content=f"Ошибка: {e}", parent=self.window())

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
                    InfoBar.success(title="Успех", content=f"Пресет экспортирован: {file_path}", parent=self.window())
                else:
                    InfoBar.warning(title="Ошибка", content="Не удалось экспортировать пресет", parent=self.window())

            except Exception as e:
                log(f"Ошибка экспорта пресета: {e}", "ERROR")
                InfoBar.error(title="Ошибка", content=f"Ошибка: {e}", parent=self.window())

    def _on_preset_switched_callback(self, name: str):
        """Колбэк при переключении пресета (из PresetManager)"""
        pass  # Сигнал уже эмитится из _on_activate_preset

    def _on_dpi_reload_needed(self):
        """Колбэк для перезапуска DPI"""
        try:
            # direct_zapret2: winws2 runner has hot-reload on preset-zapret2.txt.
            # Explicit restart here can race with StrategyRunnerV2 watcher on rapid preset switching.
            try:
                from strategy_menu import get_strategy_launch_method

                method = (get_strategy_launch_method() or "").strip().lower()
            except Exception:
                method = ""

            # Ищем dpi_controller в родительских виджетах
            widget = self
            while widget:
                if hasattr(widget, 'dpi_controller'):
                    if method in ("direct_zapret2", "direct_zapret2_orchestra"):
                        try:
                            from dpi.zapret2_core_restart import trigger_dpi_reload
                            trigger_dpi_reload(widget, reason="preset_switched")
                            log("Preset switched: hot-reload will apply config", "DEBUG")
                        except Exception:
                            pass
                        return

                    widget.dpi_controller.restart_dpi_async()
                    log("DPI перезапущен после смены пресета", "INFO")
                    return
                widget = widget.parent()

            # Альтернативный способ через QApplication
            from PyQt6.QtWidgets import QApplication
            for w in QApplication.topLevelWidgets():
                if hasattr(w, 'dpi_controller'):
                    if method in ("direct_zapret2", "direct_zapret2_orchestra"):
                        try:
                            from dpi.zapret2_core_restart import trigger_dpi_reload
                            trigger_dpi_reload(w, reason="preset_switched")
                            log("Preset switched: hot-reload will apply config", "DEBUG")
                        except Exception:
                            pass
                        return

                    w.dpi_controller.restart_dpi_async()
                    log("DPI перезапущен после смены пресета", "INFO")
                    return

            log("DPI контроллер не найден для перезапуска", "WARNING")

        except Exception as e:
            log(f"Ошибка перезапуска DPI: {e}", "ERROR")

    def refresh(self):
        """Обновляет список пресетов"""
        self._load_presets()

    def _open_new_configs_post(self):
        """Открывает Telegram-бота с актуальными конфигами."""
        try:
            from config.telegram_links import open_telegram_link
            open_telegram_link("nozapretinrussia_bot")
        except Exception as e:
            log(f"Ошибка открытия Telegram: {e}", "ERROR")
            InfoBar.warning(title="Ошибка", content=f"Не удалось открыть Telegram: {e}", parent=self.window())
