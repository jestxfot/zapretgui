# ui/pages/zapret2/user_presets_page.py
"""Zapret 2 Direct: user presets management."""

from __future__ import annotations

from datetime import datetime
import re
import webbrowser
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import (
    Qt,
    pyqtSignal,
    QSize,
    QTimer,
    QFileSystemWatcher,
    QAbstractListModel,
    QModelIndex,
    QRect,
    QEvent,
    QPoint,
    QPropertyAnimation,
    QEasingCurve,
)
from PyQt6.QtGui import QColor, QPainter, QFontMetrics, QMouseEvent, QHelpEvent, QTransform, QCursor, QGuiApplication
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QFileDialog,
    QMessageBox,
    QListView,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QStyle,
    QToolTip,
    QSizePolicy,
    QDialog,
    QGraphicsDropShadowEffect,
    QApplication,
)
import qtawesome as qta

from ui.pages.base_page import BasePage
from ui.pages.strategies_page_base import ResetActionButton
from ui.sidebar import ActionButton, SettingsCard
from ui.pages.presets_page import _RevealFrame, _SegmentedChoice
from ui.widgets.line_edit_icons import set_line_edit_clear_button_icon
from ui.theme import get_theme_tokens
from ui.theme_semantic import get_semantic_palette
from log import log


_icon_cache: dict[str, object] = {}
_DEFAULT_PRESET_ICON_COLOR = "#5caee8"
_HEX_COLOR_RGB_RE = re.compile(r"^#(?:[0-9a-fA-F]{6})$")
_HEX_COLOR_RGBA_RE = re.compile(r"^#(?:[0-9a-fA-F]{8})$")
_CSS_RGBA_COLOR_RE = re.compile(
    r"^\s*rgba?\(\s*([0-9]{1,3})\s*,\s*([0-9]{1,3})\s*,\s*([0-9]{1,3})\s*(?:,\s*([0-9]*\.?[0-9]+)\s*)?\)\s*$",
    re.IGNORECASE,
)


def _accent_fg_for_tokens(tokens) -> str:
    """Chooses readable foreground for the current accent color."""
    try:
        return str(tokens.accent_fg)
    except Exception:
        return "rgba(18, 18, 18, 0.90)"


def _normalize_preset_icon_color(value: Optional[str]) -> str:
    raw = str(value or "").strip()
    if _HEX_COLOR_RGB_RE.fullmatch(raw):
        return raw.lower()
    if _HEX_COLOR_RGBA_RE.fullmatch(raw):
        lowered = raw.lower()
        return f"#{lowered[1:7]}"
    try:
        return get_theme_tokens().accent_hex
    except Exception:
        return _DEFAULT_PRESET_ICON_COLOR


def _cached_icon(name: str, color: str):
    key = f"{name}|{color}"
    icon = _icon_cache.get(key)
    if icon is None:
        icon = qta.icon(name, color=color)
        _icon_cache[key] = icon
    return icon


def _relative_luminance(color: QColor) -> float:
    def _channel_luma(channel: int) -> float:
        value = max(0.0, min(1.0, float(channel) / 255.0))
        if value <= 0.03928:
            return value / 12.92
        return ((value + 0.055) / 1.055) ** 2.4

    return (
        0.2126 * _channel_luma(color.red())
        + 0.7152 * _channel_luma(color.green())
        + 0.0722 * _channel_luma(color.blue())
    )


def _contrast_ratio(foreground: QColor, background: QColor) -> float:
    fg = QColor(foreground)
    bg = QColor(background)
    fg.setAlpha(255)
    bg.setAlpha(255)
    l1 = _relative_luminance(fg)
    l2 = _relative_luminance(bg)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def _pick_contrast_color(
    preferred_color: str,
    background_color: QColor,
    fallback_colors: list[str],
    *,
    minimum_ratio: float = 2.4,
) -> str:
    bg = QColor(background_color)
    if not bg.isValid():
        bg = QColor("#000000")
    bg.setAlpha(255)

    candidates: list[str] = []
    for raw in [preferred_color, *fallback_colors]:
        value = str(raw or "").strip()
        if value and value not in candidates:
            candidates.append(value)

    best_color = None
    best_ratio = -1.0
    for candidate in candidates:
        color = QColor(candidate)
        if not color.isValid():
            continue
        color.setAlpha(255)
        ratio = _contrast_ratio(color, bg)
        if ratio >= minimum_ratio:
            return color.name(QColor.NameFormat.HexRgb)
        if ratio > best_ratio:
            best_ratio = ratio
            best_color = color

    if best_color is not None:
        return best_color.name(QColor.NameFormat.HexRgb)
    return "#f5f5f5" if _relative_luminance(bg) < 0.45 else "#111111"


def _color_with_alpha(color_value: str, alpha: int, fallback_hex: str) -> str:
    color = QColor(color_value)
    if not color.isValid():
        color = QColor(fallback_hex)
    color.setAlpha(max(0, min(255, int(alpha))))
    return f"rgba({color.red()}, {color.green()}, {color.blue()}, {color.alpha()})"


def _to_qcolor(value, fallback_hex: str = "#000000") -> QColor:
    if isinstance(value, QColor):
        color = QColor(value)
        if color.isValid():
            return color

    text = str(value or "").strip()
    if text:
        match = _CSS_RGBA_COLOR_RE.fullmatch(text)
        if match:
            try:
                r = max(0, min(255, int(match.group(1))))
                g = max(0, min(255, int(match.group(2))))
                b = max(0, min(255, int(match.group(3))))
                alpha_raw = match.group(4)

                if alpha_raw is None:
                    a = 255
                else:
                    a_float = float(alpha_raw)
                    if a_float <= 1.0:
                        a = int(round(max(0.0, min(1.0, a_float)) * 255.0))
                    else:
                        a = int(round(max(0.0, min(255.0, a_float))))

                return QColor(r, g, b, a)
            except Exception:
                pass

        color = QColor(text)
        if color.isValid():
            return color

    fallback = QColor(fallback_hex)
    if fallback.isValid():
        return fallback
    return QColor(0, 0, 0)


class _PresetListModel(QAbstractListModel):
    KindRole = Qt.ItemDataRole.UserRole + 1
    NameRole = Qt.ItemDataRole.UserRole + 2
    DescriptionRole = Qt.ItemDataRole.UserRole + 3
    DateRole = Qt.ItemDataRole.UserRole + 4
    ActiveRole = Qt.ItemDataRole.UserRole + 5
    TextRole = Qt.ItemDataRole.UserRole + 6
    IconColorRole = Qt.ItemDataRole.UserRole + 7

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rows: list[dict[str, object]] = []

    def set_rows(self, rows: list[dict[str, object]]) -> None:
        self.beginResetModel()
        self._rows = rows
        self.endResetModel()

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._rows)

    def data(self, index: QModelIndex, role: int = int(Qt.ItemDataRole.DisplayRole)):
        if not index.isValid() or index.row() < 0 or index.row() >= len(self._rows):
            return None

        row = self._rows[index.row()]
        kind = row.get("kind", "preset")

        if role == int(Qt.ItemDataRole.DisplayRole):
            if kind == "preset":
                return row.get("name", "")
            return row.get("text", "")

        if role == self.KindRole:
            return kind
        if role == self.NameRole:
            return row.get("name", "")
        if role == self.DescriptionRole:
            return row.get("description", "")
        if role == self.DateRole:
            return row.get("date", "")
        if role == self.ActiveRole:
            return bool(row.get("is_active", False))
        if role == self.TextRole:
            return row.get("text", "")
        if role == self.IconColorRole:
            return row.get("icon_color", _DEFAULT_PRESET_ICON_COLOR)

        return None


class _LinkedWheelListView(QListView):
    def wheelEvent(self, e):
        scrollbar = self.verticalScrollBar()
        if scrollbar is None:
            super().wheelEvent(e)
            return

        delta = e.angleDelta().y()
        at_top = scrollbar.value() <= scrollbar.minimum()
        at_bottom = scrollbar.value() >= scrollbar.maximum()

        if (delta > 0 and at_top) or (delta < 0 and at_bottom):
            # Let parent scroll area handle wheel at boundaries.
            e.ignore()
            return

        super().wheelEvent(e)
        e.accept()


class _PresetListDelegate(QStyledItemDelegate):
    action_triggered = pyqtSignal(str, str)

    _ROW_HEIGHT = 44
    _SECTION_HEIGHT = 24
    _EMPTY_HEIGHT = 64
    _ACTION_SIZE = 28
    _ACTION_SPACING = 6

    _ACTION_ICONS = {
        "rename": "fa5s.edit",
        "duplicate": "fa5s.copy",
        "reset": "fa5s.broom",
        "delete": "fa5s.trash",
        "export": "fa5s.file-export",
    }

    _ACTION_TOOLTIPS = {
        "rename": "Переименовать",
        "duplicate": "Дублировать",
        "reset": "Сбросить",
        "delete": "Удалить",
        "export": "Экспорт",
    }

    _PENDING_SHAKE_ROTATIONS = (0, -8, 8, -6, 6, -4, 4, -2, 0)
    _PENDING_SHAKE_INTERVAL_MS = 50

    def __init__(self, view: QListView):
        super().__init__(view)
        self._view = view
        self._pending_destructive: Optional[tuple[str, str]] = None
        self._pending_timer = QTimer(self)
        self._pending_timer.setSingleShot(True)
        self._pending_timer.timeout.connect(self._clear_pending_destructive)
        self._pending_shake_step = 0
        self._pending_shake_rotation = 0
        self._pending_shake_timer = QTimer(self)
        self._pending_shake_timer.timeout.connect(self._advance_pending_shake)

    def reset_interaction_state(self):
        self._clear_pending_destructive(update=False)

    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QSize:
        kind = index.data(_PresetListModel.KindRole)
        if kind == "section":
            return QSize(0, self._SECTION_HEIGHT)
        if kind == "empty":
            return QSize(0, self._EMPTY_HEIGHT)
        return QSize(0, self._ROW_HEIGHT)

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex):
        kind = index.data(_PresetListModel.KindRole)

        if kind == "section":
            self._paint_section_row(painter, option, str(index.data(_PresetListModel.TextRole) or ""))
            return

        if kind == "empty":
            self._paint_empty_row(painter, option, str(index.data(_PresetListModel.TextRole) or ""))
            return

        self._paint_preset_row(painter, option, index)

    def editorEvent(self, event, model, option: QStyleOptionViewItem, index: QModelIndex):
        _ = model
        if index.data(_PresetListModel.KindRole) != "preset":
            return False
        if event.type() != QEvent.Type.MouseButtonRelease:
            return False
        if not isinstance(event, QMouseEvent):
            return False
        if event.button() != Qt.MouseButton.LeftButton:
            return False

        name = str(index.data(_PresetListModel.NameRole) or "")
        if not name:
            return False

        is_active = bool(index.data(_PresetListModel.ActiveRole))
        action = self._action_at(option.rect, is_active, event.position().toPoint())

        if action:
            self._handle_action_click(name, action, event)
            return True

        if not is_active:
            self._clear_pending_destructive(update=False)
            self.action_triggered.emit("activate", name)
            return True

        self._clear_pending_destructive(update=False)
        return False

    def helpEvent(self, event: QHelpEvent, view, option: QStyleOptionViewItem, index: QModelIndex) -> bool:
        if index.data(_PresetListModel.KindRole) != "preset":
            return super().helpEvent(event, view, option, index)

        name = str(index.data(_PresetListModel.NameRole) or "")
        is_active = bool(index.data(_PresetListModel.ActiveRole))
        action = self._action_at(option.rect, is_active, event.pos())
        if not action:
            return super().helpEvent(event, view, option, index)

        tooltip = self._ACTION_TOOLTIPS.get(action, "")
        if action in {"reset", "delete"} and self._pending_destructive == (name, action):
            tooltip = f"{tooltip}\nНажмите ещё раз для подтверждения"
        if tooltip:
            QToolTip.showText(event.globalPos(), tooltip, view)
            return True
        return super().helpEvent(event, view, option, index)

    def _handle_action_click(self, name: str, action: str, event: QMouseEvent):
        if action in {"reset", "delete"}:
            key = (name, action)
            if self._pending_destructive == key:
                self._clear_pending_destructive(update=False)
                self.action_triggered.emit(action, name)
                self._view.viewport().update()
                return

            self._pending_destructive = key
            self._start_pending_shake()
            self._pending_timer.start(3000)
            QToolTip.showText(event.globalPosition().toPoint(), "Нажмите ещё раз для подтверждения", self._view)
            self._view.viewport().update()
            return

        self._clear_pending_destructive(update=False)
        self.action_triggered.emit(action, name)
        self._view.viewport().update()

    def _clear_pending_destructive(self, update: bool = True):
        self._pending_timer.stop()
        self._pending_shake_timer.stop()
        self._pending_shake_step = 0
        self._pending_shake_rotation = 0
        if self._pending_destructive is None:
            return
        self._pending_destructive = None
        if update:
            self._view.viewport().update()

    def _start_pending_shake(self):
        self._pending_shake_timer.stop()
        self._pending_shake_step = 0
        self._pending_shake_rotation = int(self._PENDING_SHAKE_ROTATIONS[0])
        self._pending_shake_timer.start(self._PENDING_SHAKE_INTERVAL_MS)

    def _advance_pending_shake(self):
        self._pending_shake_step += 1
        if self._pending_shake_step >= len(self._PENDING_SHAKE_ROTATIONS):
            self._pending_shake_timer.stop()
            self._pending_shake_step = 0
            self._pending_shake_rotation = 0
            self._view.viewport().update()
            return

        self._pending_shake_rotation = int(self._PENDING_SHAKE_ROTATIONS[self._pending_shake_step])
        self._view.viewport().update()

    def _visible_actions(self, is_active: bool) -> list[str]:
        actions = ["rename", "duplicate", "reset"]
        if not is_active:
            actions.append("delete")
        actions.append("export")
        return actions

    def _action_rects(self, row_rect: QRect, is_active: bool) -> list[tuple[str, QRect]]:
        actions = self._visible_actions(is_active)
        if not actions:
            return []

        total_width = len(actions) * self._ACTION_SIZE + (len(actions) - 1) * self._ACTION_SPACING
        x = row_rect.right() - 12 - total_width + 1
        y = row_rect.center().y() - (self._ACTION_SIZE // 2)

        rects: list[tuple[str, QRect]] = []
        for action in actions:
            rects.append((action, QRect(x, y, self._ACTION_SIZE, self._ACTION_SIZE)))
            x += self._ACTION_SIZE + self._ACTION_SPACING
        return rects

    def _action_at(self, option_rect: QRect, is_active: bool, pos) -> Optional[str]:
        for action, rect in self._action_rects(option_rect, is_active):
            if rect.contains(pos):
                return action
        return None

    def _paint_action_icon(self, painter: QPainter, icon_name: str, icon_color: str, icon_rect: QRect, rotation: int = 0):
        icon = _cached_icon(icon_name, icon_color)
        pixmap = icon.pixmap(icon_rect.size())
        if pixmap.isNull():
            return

        if rotation:
            rotated = pixmap.transformed(QTransform().rotate(rotation), Qt.TransformationMode.SmoothTransformation)
            center = icon_rect.center()
            draw_x = center.x() - (rotated.width() // 2)
            draw_y = center.y() - (rotated.height() // 2)
            painter.drawPixmap(draw_x, draw_y, rotated)
            return

        painter.drawPixmap(icon_rect.topLeft(), pixmap)

    def _paint_section_row(self, painter: QPainter, option: QStyleOptionViewItem, text: str):
        painter.save()
        tokens = get_theme_tokens()
        rect = option.rect

        text_rect = rect.adjusted(12, 0, -12, 0)
        font = painter.font()
        font.setPointSize(9)
        font.setBold(True)
        painter.setFont(font)

        metrics = QFontMetrics(font)
        text_width = metrics.horizontalAdvance(text)

        painter.setPen(_to_qcolor(tokens.fg_muted, "#9aa2af"))
        painter.drawText(text_rect, int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter), text)

        # Draw a subtle separator line to the right of the label.
        line_x1 = text_rect.left() + text_width + 10
        line_x2 = rect.right() - 12
        if line_x2 > line_x1:
            painter.setPen(_to_qcolor(tokens.divider, "#5f6368"))
            y = rect.center().y()
            painter.drawLine(line_x1, y, line_x2, y)
        painter.restore()

    def _paint_empty_row(self, painter: QPainter, option: QStyleOptionViewItem, text: str):
        painter.save()
        tokens = get_theme_tokens()
        painter.setPen(_to_qcolor(tokens.fg_muted, "#9aa2af"))
        font = painter.font()
        font.setPointSize(10)
        painter.setFont(font)
        painter.drawText(option.rect.adjusted(8, 0, -8, 0), int(Qt.AlignmentFlag.AlignCenter), text)
        painter.restore()

    def _paint_preset_row(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex):
        tokens = get_theme_tokens()
        semantic = get_semantic_palette(tokens.theme_name)
        name = str(index.data(_PresetListModel.NameRole) or "")
        date_text = str(index.data(_PresetListModel.DateRole) or "")
        is_active = bool(index.data(_PresetListModel.ActiveRole))

        row_rect = option.rect
        hovered = bool(option.state & QStyle.StateFlag.State_MouseOver)

        if is_active:
            bg = _to_qcolor(tokens.accent_soft_bg, tokens.accent_hex)
        elif hovered:
            bg = _to_qcolor(tokens.surface_bg_hover, tokens.surface_bg)
        else:
            bg = QColor(Qt.GlobalColor.transparent)

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        if bg.alpha() > 0:
            painter.fillRect(row_rect, bg)

        icon_rect = QRect(row_rect.left() + 12, row_rect.center().y() - 10, 20, 20)
        icon_name = "fa5s.star" if is_active else "fa5s.file-alt"
        icon_color = _pick_contrast_color(
            _normalize_preset_icon_color(str(index.data(_PresetListModel.IconColorRole) or "")),
            bg,
            [tokens.accent_hex, tokens.fg],
            minimum_ratio=2.6,
        )
        _cached_icon(icon_name, icon_color).paint(painter, icon_rect)

        action_rects = self._action_rects(row_rect, is_active)
        right_cursor = action_rects[0][1].left() - 10 if action_rects else row_rect.right() - 12

        if is_active:
            badge_text = "Активен"
            badge_font = painter.font()
            badge_font.setPointSize(8)
            badge_font.setBold(True)
            badge_metrics = QFontMetrics(badge_font)
            badge_width = badge_metrics.horizontalAdvance(badge_text) + 14
            badge_rect = QRect(right_cursor - badge_width, row_rect.center().y() - 9, badge_width, 18)

            painter.setBrush(QColor(tokens.accent_hex))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(badge_rect, 4, 4)

            painter.setFont(badge_font)
            painter.setPen(_to_qcolor(_accent_fg_for_tokens(tokens), "#f5f5f5"))
            painter.drawText(badge_rect, int(Qt.AlignmentFlag.AlignCenter), badge_text)
            right_cursor = badge_rect.left() - 10

        if date_text:
            date_font = painter.font()
            date_font.setPointSize(9)
            date_font.setBold(False)
            painter.setFont(date_font)
            date_metrics = QFontMetrics(date_font)
            date_width = date_metrics.horizontalAdvance(date_text)
            date_rect = QRect(max(row_rect.left() + 80, right_cursor - date_width), row_rect.top(), date_width, row_rect.height())
            painter.setPen(_to_qcolor(tokens.fg_faint, "#aeb5c1"))
            painter.drawText(date_rect, int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter), date_text)
            right_cursor = date_rect.left() - 10

        name_left = icon_rect.right() + 10
        name_rect = QRect(name_left, row_rect.top(), max(40, right_cursor - name_left), row_rect.height())
        name_font = painter.font()
        name_font.setPointSize(10)
        name_font.setBold(True)
        painter.setFont(name_font)
        painter.setPen(_to_qcolor(tokens.fg, "#f5f5f5"))
        name_metrics = QFontMetrics(name_font)
        elided_name = name_metrics.elidedText(name, Qt.TextElideMode.ElideRight, name_rect.width())
        painter.drawText(name_rect, int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter), elided_name)

        for action, action_rect in action_rects:
            pending = self._pending_destructive == (name, action)
            if pending:
                btn_bg = _to_qcolor(semantic.error_soft_bg, semantic.error)
                icon_col = _pick_contrast_color(
                    semantic.error,
                    btn_bg,
                    [semantic.on_color, tokens.fg],
                    minimum_ratio=2.8,
                )
            else:
                btn_bg = _to_qcolor(tokens.surface_bg_hover, tokens.surface_bg)
                icon_col = _pick_contrast_color(
                    str(tokens.fg_muted),
                    btn_bg,
                    [tokens.fg],
                    minimum_ratio=2.6,
                )

            painter.setBrush(btn_bg)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(action_rect, 6, 6)

            icon_name = self._ACTION_ICONS.get(action, "fa5s.circle")
            icon_rotation = self._pending_shake_rotation if pending else 0
            self._paint_action_icon(
                painter,
                icon_name,
                icon_col,
                action_rect.adjusted(7, 7, -7, -7),
                icon_rotation,
            )

        painter.restore()


class _PresetActionPopover(QDialog):
    """Win11-like popover for preset create/rename."""

    submit_requested = pyqtSignal()
    cancel_requested = pyqtSignal()

    _WIDTH = 420
    _BORDER_RADIUS = 14
    _ANIM_MS = 170

    def __init__(self, parent=None):
        super().__init__(parent)
        self._mode = "create"  # create | rename
        self._old_name = ""

        self.setWindowFlags(
            Qt.WindowType.Popup
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setModal(False)
        self.setProperty("noDrag", True)

        self._opacity_anim = QPropertyAnimation(self, b"windowOpacity", self)
        self._opacity_anim.setDuration(self._ANIM_MS)
        self._opacity_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._pos_anim = QPropertyAnimation(self, b"pos", self)
        self._pos_anim.setDuration(self._ANIM_MS)
        self._pos_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._build_ui()
        self.setFixedWidth(self._WIDTH)
        self.setWindowOpacity(0.0)

    @staticmethod
    def _detect_light_theme() -> bool:
        try:
            return bool(get_theme_tokens().is_light)
        except Exception:
            return False

    def _build_ui(self) -> None:
        tokens = get_theme_tokens()

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)  # space for shadow
        root.setSpacing(0)

        self._container = QWidget(self)
        self._container.setObjectName("presetPopoverContainer")
        self._container.setProperty("noDrag", True)

        self._shadow = QGraphicsDropShadowEffect(self._container)
        self._shadow.setBlurRadius(38)
        self._shadow.setOffset(0, 8)
        self._shadow.setColor(QColor(0, 0, 0, 96))
        self._container.setGraphicsEffect(self._shadow)

        root.addWidget(self._container)

        layout = QVBoxLayout(self._container)
        layout.setContentsMargins(20, 18, 20, 16)
        layout.setSpacing(12)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(10)

        self._icon = QLabel()
        self._icon.setFixedSize(22, 22)
        header.addWidget(self._icon)

        self._title = QLabel("")
        try:
            self._title.setProperty("tone", "primary")
        except Exception:
            pass
        self._title.setStyleSheet("font-size: 14px; font-weight: 600; font-family: 'Segoe UI Variable', 'Segoe UI', sans-serif;")
        header.addWidget(self._title, 1)

        self._close_btn = QPushButton()
        self._close_btn.setFixedSize(28, 28)
        self._close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._close_btn.setIcon(qta.icon("fa5s.times", color=get_theme_tokens().fg))
        self._close_btn.setIconSize(QSize(12, 12))
        self._close_btn.setStyleSheet(
            """
            QPushButton {
                background: %(bg)s;
                border: 1px solid %(border)s;
                border-radius: 6px;
            }
            QPushButton:hover { background: %(bg_hover)s; }
            QPushButton:pressed { background: %(bg_pressed)s; }
            """
            % {
                "bg": tokens.surface_bg,
                "bg_hover": tokens.surface_bg_hover,
                "bg_pressed": tokens.surface_bg_pressed,
                "border": tokens.surface_border,
            }
        )
        self._close_btn.clicked.connect(self._on_cancel)
        header.addWidget(self._close_btn)

        layout.addLayout(header)

        self._subtitle = QLabel("")
        self._subtitle.setWordWrap(True)
        try:
            self._subtitle.setProperty("tone", "muted")
        except Exception:
            pass
        self._subtitle.setStyleSheet("font-size: 12px; font-family: 'Segoe UI Variable', 'Segoe UI', sans-serif;")
        layout.addWidget(self._subtitle)

        self._rename_from = QLabel("")
        self._rename_from.setWordWrap(True)
        try:
            self._rename_from.setProperty("tone", "faint")
        except Exception:
            pass
        self._rename_from.setStyleSheet("font-size: 12px; font-family: 'Segoe UI Variable', 'Segoe UI', sans-serif;")
        self._rename_from.hide()
        layout.addWidget(self._rename_from)

        name_block = QVBoxLayout()
        name_block.setContentsMargins(0, 0, 0, 0)
        name_block.setSpacing(6)

        self._name_label = QLabel("Название")
        try:
            self._name_label.setProperty("tone", "muted")
        except Exception:
            pass
        self._name_label.setStyleSheet("font-size: 12px;")
        name_block.addWidget(self._name_label)

        self._name_input = QLineEdit()
        self._name_input.setFixedHeight(36)
        self._name_input.setClearButtonEnabled(True)
        set_line_edit_clear_button_icon(self._name_input)
        self._name_input.setProperty("noDrag", True)
        tokens = get_theme_tokens()
        self._name_input.setStyleSheet(
            f"""
            QLineEdit {{
                background: {tokens.surface_bg};
                border: 1px solid {tokens.surface_border};
                border-radius: 10px;
                color: {tokens.fg};
                padding: 0 12px;
                font-size: 13px;
                font-family: 'Segoe UI Variable', 'Segoe UI', sans-serif;
            }}
            QLineEdit:hover {{ background: {tokens.surface_bg_hover}; }}
            QLineEdit:focus {{ border: 1px solid {tokens.accent_hex}; }}
            QLineEdit::placeholder {{ color: {tokens.fg_faint}; }}
            """
        )
        self._name_input.textChanged.connect(lambda: self.set_error(""))
        self._name_input.returnPressed.connect(self._on_submit)
        name_block.addWidget(self._name_input)

        layout.addLayout(name_block)

        self._source_row = QWidget(self._container)
        src_layout = QHBoxLayout(self._source_row)
        src_layout.setContentsMargins(0, 2, 0, 0)
        src_layout.setSpacing(12)
        self._source_label = QLabel("Создать на основе")
        try:
            self._source_label.setProperty("tone", "muted")
        except Exception:
            pass
        self._source_label.setStyleSheet("font-size: 12px;")
        src_layout.addWidget(self._source_label)
        src_layout.addStretch(1)
        self._source_choice = _SegmentedChoice("Текущего активного", "current", "Пустого", "empty", self)
        src_layout.addWidget(self._source_choice)
        layout.addWidget(self._source_row)

        self._error = QLabel("")
        self._error.setWordWrap(True)
        self._error.setStyleSheet("color: #ff6b6b; font-size: 12px;")
        self._error.hide()
        layout.addWidget(self._error)

        buttons = QHBoxLayout()
        buttons.setContentsMargins(0, 6, 0, 0)
        buttons.setSpacing(10)
        buttons.addStretch(1)

        self._cancel_btn = QPushButton("Отмена")
        self._cancel_btn.setFixedHeight(34)
        self._cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._cancel_btn.setStyleSheet(
            """
            QPushButton {
                background-color: %(bg)s;
                border: 1px solid %(border)s;
                border-radius: 10px;
                color: %(fg)s;
                padding: 0 18px;
                font-size: 12px;
                font-weight: 600;
                font-family: 'Segoe UI Variable', 'Segoe UI', sans-serif;
            }
            QPushButton:hover { background-color: %(bg_hover)s; }
            QPushButton:pressed { background-color: %(bg_pressed)s; }
            """
            % {
                "bg": tokens.surface_bg,
                "bg_hover": tokens.surface_bg_hover,
                "bg_pressed": tokens.surface_bg_pressed,
                "border": tokens.surface_border,
                "fg": tokens.fg,
            }
        )
        self._cancel_btn.clicked.connect(self._on_cancel)
        buttons.addWidget(self._cancel_btn)

        self._submit_btn = QPushButton("")
        self._submit_btn.setFixedHeight(34)
        self._submit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._submit_btn.setIconSize(QSize(16, 16))
        accent_fg = _accent_fg_for_tokens(tokens)
        self._submit_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {tokens.accent_hex};
                border: none;
                border-radius: 10px;
                color: {accent_fg};
                padding: 0 18px;
                font-size: 12px;
                font-weight: 700;
                font-family: 'Segoe UI Variable', 'Segoe UI', sans-serif;
            }}
            QPushButton:hover {{ background-color: {tokens.accent_hover_hex}; }}
            QPushButton:pressed {{ background-color: {tokens.accent_pressed_hex}; }}
            """
        )
        self._submit_btn.clicked.connect(self._on_submit)
        buttons.addWidget(self._submit_btn)

        layout.addLayout(buttons)

        self._apply_styles()
        self.configure_create()

    def _apply_styles(self) -> None:
        tokens = get_theme_tokens()
        semantic = get_semantic_palette(tokens.theme_name)
        is_light = bool(tokens.is_light)
        bg_top = _color_with_alpha(
            tokens.surface_bg_hover,
            248,
            "#f6f8fc" if is_light else "#2d3137",
        )
        bg_bottom = _color_with_alpha(
            tokens.surface_bg,
            246,
            "#f3f6fb" if is_light else "#23272d",
        )
        shadow_color = QColor(0, 0, 0, 66 if is_light else 124)
        error_color = _pick_contrast_color(
            semantic.error,
            _to_qcolor(bg_bottom, "#23272d" if not is_light else "#f3f6fb"),
            [tokens.fg],
            minimum_ratio=2.8,
        )

        self._shadow.setColor(shadow_color)
        radius = self._BORDER_RADIUS
        self._container.setStyleSheet(
            f"""
            QWidget#presetPopoverContainer {{
                background-color: qlineargradient(
                    x1:0, y1:0, x2:0, y2:1,
                    stop:0 {bg_top},
                    stop:1 {bg_bottom}
                );
                border: 1px solid {tokens.surface_border};
                border-radius: {radius}px;
            }}
            """
        )

        # Inner widgets (theme-aware colors).
        try:
            self._title.setStyleSheet(
                f"color: {tokens.fg}; font-size: 14px; font-weight: 600; font-family: 'Segoe UI Variable', 'Segoe UI', sans-serif;"
            )
            self._subtitle.setStyleSheet(
                f"color: {tokens.fg_muted}; font-size: 12px; font-family: 'Segoe UI Variable', 'Segoe UI', sans-serif;"
            )
            self._rename_from.setStyleSheet(
                f"color: {tokens.fg_muted}; font-size: 12px; font-family: 'Segoe UI Variable', 'Segoe UI', sans-serif;"
            )
        except Exception:
            pass

        try:
            self._name_label.setStyleSheet(f"color: {tokens.fg_muted}; font-size: 12px;")
        except Exception:
            pass

        try:
            self._source_label.setStyleSheet(f"color: {tokens.fg_muted}; font-size: 12px;")
        except Exception:
            pass

        try:
            self._name_input.setStyleSheet(
                f"""
                QLineEdit {{
                    background: {tokens.surface_bg};
                    border: 1px solid {tokens.surface_border};
                    border-radius: 10px;
                    color: {tokens.fg};
                    padding: 0 12px;
                    font-size: 13px;
                    font-family: 'Segoe UI Variable', 'Segoe UI', sans-serif;
                }}
                QLineEdit:hover {{ background: {tokens.surface_bg_hover}; }}
                QLineEdit:focus {{ border: 1px solid {tokens.accent_hex}; }}
                QLineEdit::placeholder {{ color: {tokens.fg_faint}; }}
                """
            )
        except Exception:
            pass

        try:
            set_line_edit_clear_button_icon(
                self._name_input,
                color=tokens.fg_muted,
            )
        except Exception:
            pass

        try:
            self._close_btn.setIcon(qta.icon("fa5s.times", color=tokens.fg))
            self._close_btn.setStyleSheet(
                f"""
                QPushButton {{
                    background: {tokens.surface_bg};
                    border: none;
                    border-radius: 6px;
                }}
                QPushButton:hover {{ background: {tokens.surface_bg_hover}; }}
                QPushButton:pressed {{ background: {tokens.surface_bg_pressed}; }}
                """
            )
        except Exception:
            pass

        try:
            self._cancel_btn.setStyleSheet(
                f"""
                QPushButton {{
                    background-color: {tokens.surface_bg};
                    border: 1px solid {tokens.surface_border};
                    border-radius: 10px;
                    color: {tokens.fg};
                    padding: 0 18px;
                    font-size: 12px;
                    font-weight: 600;
                    font-family: 'Segoe UI Variable', 'Segoe UI', sans-serif;
                }}
                QPushButton:hover {{ background-color: {tokens.surface_bg_hover}; }}
                QPushButton:pressed {{ background-color: {tokens.surface_bg_pressed}; }}
                """
            )
        except Exception:
            pass

        try:
            accent_fg = _accent_fg_for_tokens(tokens)
            self._submit_btn.setStyleSheet(
                f"""
                QPushButton {{
                    background-color: {tokens.accent_hex};
                    border: none;
                    border-radius: 10px;
                    color: {accent_fg};
                    padding: 0 18px;
                    font-size: 12px;
                    font-weight: 700;
                    font-family: 'Segoe UI Variable', 'Segoe UI', sans-serif;
                }}
                QPushButton:hover {{ background-color: {tokens.accent_hover_hex}; }}
                QPushButton:pressed {{ background-color: {tokens.accent_pressed_hex}; }}
                """
            )
            self._submit_btn.setIcon(qta.icon("fa5s.check", color=accent_fg))
        except Exception:
            pass

        try:
            icon_name = "fa5s.edit" if self._mode == "rename" else "fa5s.plus"
            self._icon.setPixmap(qta.icon(icon_name, color=tokens.accent_hex).pixmap(18, 18))
        except Exception:
            pass

        try:
            self._error.setStyleSheet(f"color: {error_color}; font-size: 12px;")
        except Exception:
            pass

    def configure_create(self) -> None:
        self._mode = "create"
        self._old_name = ""
        self._title.setText("Новый пресет")
        self._subtitle.setText("Сохраните текущие настройки как отдельный пресет, чтобы быстро переключаться.")
        self._icon.setPixmap(qta.icon("fa5s.plus", color=get_theme_tokens().accent_hex).pixmap(18, 18))
        self._rename_from.hide()
        self._source_row.show()
        self._source_choice.set_value("current", emit=False)
        self._name_input.clear()
        self._name_input.setPlaceholderText("Например: Игры / YouTube / Дом")
        self._submit_btn.setText("Создать")
        self._submit_btn.setIcon(qta.icon("fa5s.check", color=_accent_fg_for_tokens(get_theme_tokens())))
        self.set_error("")

    def configure_rename(self, current_name: str) -> None:
        self._mode = "rename"
        self._old_name = str(current_name or "")
        self._title.setText("Переименовать")
        self._subtitle.setText("Имя пресета отображается в списке и используется для переключения.")
        self._icon.setPixmap(qta.icon("fa5s.edit", color=get_theme_tokens().accent_hex).pixmap(18, 18))
        if self._old_name:
            self._rename_from.setText(f"Текущее имя: {self._old_name}")
            self._rename_from.show()
        else:
            self._rename_from.hide()
        self._source_row.hide()
        self._name_input.setText(self._old_name)
        self._name_input.setPlaceholderText("Новое имя...")
        self._submit_btn.setText("Переименовать")
        self._submit_btn.setIcon(qta.icon("fa5s.check", color=_accent_fg_for_tokens(get_theme_tokens())))
        self.set_error("")

    def set_error(self, text: str) -> None:
        text = str(text or "")
        self._error.setText(text)
        self._error.setVisible(bool(text))

    def name_text(self) -> str:
        return self._name_input.text() if self._name_input else ""

    def source_value(self) -> str:
        try:
            return str(self._source_choice.value() or "")
        except Exception:
            return ""

    def focus_name(self, select_all: bool = False) -> None:
        try:
            self._name_input.setFocus()
            if select_all:
                self._name_input.selectAll()
        except Exception:
            pass

    def _screen_geometry_for_point(self, p: QPoint):
        try:
            screen = QGuiApplication.screenAt(p)
        except Exception:
            screen = None
        if not screen:
            try:
                screen = QApplication.primaryScreen()
            except Exception:
                screen = None
        try:
            return screen.availableGeometry() if screen else None
        except Exception:
            return None

    def _clamp_to_screen(self, target: QPoint, *, anchor_top: int | None = None) -> QPoint:
        self.adjustSize()
        w = int(self.width() or self.sizeHint().width() or self._WIDTH)
        h = int(self.height() or self.sizeHint().height() or 240)

        screen_rect = self._screen_geometry_for_point(target)
        if not screen_rect:
            return target

        margin = 8
        x = max(screen_rect.left() + margin, min(target.x(), screen_rect.right() - w - margin))
        y = target.y()

        if y + h > screen_rect.bottom() - margin and anchor_top is not None:
            y = anchor_top - h - 8

        y = max(screen_rect.top() + margin, min(y, screen_rect.bottom() - h - margin))
        return QPoint(x, y)

    def _show_animated_at(self, target: QPoint) -> None:
        self._apply_styles()
        target = self._clamp_to_screen(target)

        try:
            self._opacity_anim.stop()
            self._pos_anim.stop()
        except Exception:
            pass

        start_pos = target + QPoint(0, 10)
        self.move(start_pos)
        self.setWindowOpacity(0.0)
        self.show()
        try:
            self.raise_()
        except Exception:
            pass

        self._opacity_anim.setStartValue(0.0)
        self._opacity_anim.setEndValue(1.0)
        self._pos_anim.setStartValue(start_pos)
        self._pos_anim.setEndValue(target)
        self._opacity_anim.start()
        self._pos_anim.start()

    def show_for_widget(self, widget: QWidget) -> None:
        try:
            top = widget.mapToGlobal(QPoint(0, 0)).y()
            below = widget.mapToGlobal(QPoint(0, widget.height() + 8))
        except Exception:
            self.show_near_point(QCursor.pos())
            return

        self.adjustSize()
        h = int(self.height() or self.sizeHint().height() or 240)
        screen_rect = self._screen_geometry_for_point(below)
        if screen_rect and below.y() + h > screen_rect.bottom() - 8:
            above = widget.mapToGlobal(QPoint(0, 0))
            target = QPoint(below.x(), above.y() - h - 8)
        else:
            target = QPoint(below.x(), below.y())

        target = self._clamp_to_screen(target, anchor_top=top)
        self._show_animated_at(target)

    def show_near_point(self, point: QPoint) -> None:
        p = QPoint(int(point.x()), int(point.y()))
        target = p + QPoint(14, 14)
        target = self._clamp_to_screen(target, anchor_top=p.y())
        self._show_animated_at(target)

    def hide_animated(self) -> None:
        if not self.isVisible():
            return

        try:
            self._opacity_anim.stop()
            self._pos_anim.stop()
        except Exception:
            pass

        start_opacity = 1.0
        try:
            start_opacity = float(self.windowOpacity())
        except Exception:
            start_opacity = 1.0

        start_pos = self.pos()
        end_pos = start_pos + QPoint(0, 10)

        self._opacity_anim.setStartValue(start_opacity)
        self._opacity_anim.setEndValue(0.0)
        self._pos_anim.setStartValue(start_pos)
        self._pos_anim.setEndValue(end_pos)

        try:
            self._opacity_anim.finished.disconnect(self._on_hide_finished)
        except Exception:
            pass
        self._opacity_anim.finished.connect(self._on_hide_finished)

        self._opacity_anim.start()
        self._pos_anim.start()

    def _on_hide_finished(self) -> None:
        try:
            self._opacity_anim.finished.disconnect(self._on_hide_finished)
        except Exception:
            pass
        try:
            self.hide()
        except Exception:
            pass

    def _on_submit(self) -> None:
        self.submit_requested.emit()

    def _on_cancel(self) -> None:
        self.cancel_requested.emit()

    def keyPressEvent(self, event):  # noqa: N802 (Qt override)
        try:
            if event.key() == Qt.Key.Key_Escape:
                self._on_cancel()
                return
        except Exception:
            pass
        return super().keyPressEvent(event)

    def closeEvent(self, event):  # noqa: N802 (Qt override)
        # Click-outside on Qt.Popup triggers close. Route to page handler.
        try:
            if event:
                event.ignore()
        except Exception:
            pass
        try:
            self._on_cancel()
        except Exception:
            pass


class Zapret2UserPresetsPage(BasePage):
    preset_switched = pyqtSignal(str)
    preset_created = pyqtSignal(str)
    preset_deleted = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(
            "Мои пресеты",
            'Здесь кнопка для нубов - "хочу чтобы нажал и всё работает". Выбираете любой пресет - тыкаете - перезагружаете вкладку и смотрите что ресурс открывается (или не открывается). Если не открывается - тыкаете на следующий пресет. Также здесь можно создавать, импортировать, экспортировать и переключать пользовательские пресеты. ',
            parent,
        )

        self._presets_model: Optional[_PresetListModel] = None
        self._presets_delegate: Optional[_PresetListDelegate] = None
        self._manager = None
        self._ui_dirty = True  # needs rebuild on next show
        self._page_theme_refresh_scheduled = False
        self._last_page_theme_key: tuple[str, str, str] | None = None

        self._file_watcher: Optional[QFileSystemWatcher] = None
        self._watcher_active = False
        self._watcher_reload_timer = QTimer(self)
        self._watcher_reload_timer.setSingleShot(True)
        self._watcher_reload_timer.timeout.connect(self._reload_presets_from_watcher)

        self._action_mode: Optional[str] = None  # "create" | "rename"
        self._rename_source_name: Optional[str] = None

        self._bulk_reset_running = False
        self._reset_all_confirm_pending = False
        self._reset_all_result_token = None
        self._reset_all_confirm_timer = QTimer(self)
        self._reset_all_confirm_timer.setSingleShot(True)
        self._reset_all_confirm_timer.timeout.connect(self._clear_reset_all_confirmation)
        self._layout_resync_timer = QTimer(self)
        self._layout_resync_timer.setSingleShot(True)
        self._layout_resync_timer.timeout.connect(self._resync_layout_metrics)
        self._layout_resync_delayed_timer = QTimer(self)
        self._layout_resync_delayed_timer.setSingleShot(True)
        self._layout_resync_delayed_timer.timeout.connect(self._resync_layout_metrics)

        self._preset_search_timer = QTimer(self)
        self._preset_search_timer.setSingleShot(True)
        self._preset_search_timer.timeout.connect(self._apply_preset_search)
        self._preset_search_input: Optional[QLineEdit] = None

        self._action_popover: Optional[_PresetActionPopover] = None

        self._build_ui()

        self._action_popover = _PresetActionPopover(self)
        self._action_popover.submit_requested.connect(self._submit_inline_action)
        self._action_popover.cancel_requested.connect(self._hide_inline_action)
        self._apply_page_theme()

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
        if self._bulk_reset_running:
            return
        if self.isVisible():
            self._load_presets()

    def _on_store_switched(self, _name: str):
        """Central store says the active preset switched."""
        self._ui_dirty = True
        if self._bulk_reset_running:
            return
        if self.isVisible():
            self._load_presets()

    def _get_manager(self):
        if self._manager is None:
            from preset_zapret2 import PresetManager

            # UI: do not restart DPI here; MainWindow handles restart via preset_switched.
            self._manager = PresetManager()
        return self._manager

    def showEvent(self, event):
        super().showEvent(event)
        self._start_watching_presets()
        self._resync_layout_metrics()
        if self._ui_dirty:
            self._load_presets()
        else:
            self._update_presets_view_height()
        self._schedule_layout_resync(include_delayed=True)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._resync_layout_metrics()
        self._schedule_layout_resync()

    def changeEvent(self, event):  # noqa: N802 (Qt override)
        try:
            if event.type() in (QEvent.Type.StyleChange, QEvent.Type.PaletteChange):
                try:
                    tokens = get_theme_tokens()
                    theme_key = (str(tokens.theme_name), str(tokens.accent_hex), str(tokens.surface_bg))
                    if theme_key == self._last_page_theme_key:
                        return super().changeEvent(event)
                except Exception:
                    pass
                if not self._page_theme_refresh_scheduled:
                    self._page_theme_refresh_scheduled = True
                    QTimer.singleShot(0, self._on_debounced_page_theme_change)
        except Exception:
            pass
        return super().changeEvent(event)

    def _on_debounced_page_theme_change(self) -> None:
        self._page_theme_refresh_scheduled = False
        self._apply_page_theme()
        self._schedule_layout_resync()

    def hideEvent(self, event):
        try:
            self._hide_inline_action()
        except Exception:
            pass
        self._layout_resync_timer.stop()
        self._layout_resync_delayed_timer.stop()
        self._stop_watching_presets()
        self._clear_reset_all_confirmation()
        super().hideEvent(event)

    def _schedule_layout_resync(self, include_delayed: bool = False):
        self._layout_resync_timer.start(0)
        if include_delayed:
            self._layout_resync_delayed_timer.start(220)

    def _resync_layout_metrics(self):
        self._update_toolbar_buttons_layout()
        self._update_presets_view_height()

    def _start_watching_presets(self):
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
        try:
            if not self._watcher_active or not self._file_watcher:
                return

            from preset_zapret2 import get_presets_dir
            presets_dir = get_presets_dir()

            current_files = self._file_watcher.files()
            if current_files:
                self._file_watcher.removePaths(current_files)

            preset_files: list[str] = []
            if presets_dir.exists():
                preset_files.extend([str(p) for p in presets_dir.glob("*.txt") if p.is_file()])
            if preset_files:
                self._file_watcher.addPaths(preset_files)

        except Exception as e:
            log(f"Ошибка обновления мониторинга пресетов: {e}", "DEBUG")

    def _on_presets_dir_changed(self, path: str):
        try:
            log(f"Обнаружены изменения в папке пресетов: {path}", "DEBUG")
            self._update_watched_preset_files()
            self._schedule_presets_reload()
        except Exception as e:
            log(f"Ошибка обработки изменений папки пресетов: {e}", "DEBUG")

    def _on_preset_file_changed(self, path: str):
        try:
            log(f"Обнаружены изменения в пресете: {Path(path).name}", "DEBUG")
            self._schedule_presets_reload()
        except Exception as e:
            log(f"Ошибка обработки изменений пресета: {e}", "DEBUG")

    def _schedule_presets_reload(self, delay_ms: int = 500):
        try:
            self._watcher_reload_timer.stop()
            self._watcher_reload_timer.start(delay_ms)
        except Exception as e:
            log(f"Ошибка планирования обновления пресетов: {e}", "DEBUG")

    def _reload_presets_from_watcher(self):
        if not self.isVisible():
            return
        try:
            from preset_zapret2.preset_store import get_preset_store
            get_preset_store().notify_presets_changed()
        except Exception:
            self._load_presets()
        self._update_watched_preset_files()

    def _build_ui(self):
        tokens = get_theme_tokens()
        semantic = get_semantic_palette(tokens.theme_name)

        # Telegram configs link
        configs_card = SettingsCard()
        configs_card.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        # SettingsCard background/border are theme-driven globally; avoid overriding them here.
        configs_card.setStyleSheet("")
        configs_layout = QHBoxLayout()
        configs_layout.setSpacing(12)
        self._configs_icon = QLabel()
        self._configs_icon.setPixmap(qta.icon("fa5b.telegram", color=tokens.accent_hex).pixmap(18, 18))
        configs_layout.addWidget(self._configs_icon)
        configs_title = QLabel(
            "Обменивайтесь категориями на нашем форуме-сайте через Telegram-бота: безопасно и анонимно"
        )
        try:
            configs_title.setProperty("tone", "primary")
        except Exception:
            pass
        configs_title.setStyleSheet("font-size: 13px; font-weight: 600;")
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

        # "Restore deleted presets" button
        self._restore_deleted_btn = QPushButton("Восстановить удалённые пресеты")
        self._restore_deleted_btn.setIcon(qta.icon("fa5s.undo", color=tokens.fg))
        self._restore_deleted_btn.setIconSize(QSize(14, 14))
        self._restore_deleted_btn.setFixedHeight(32)
        self._restore_deleted_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._restore_deleted_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {tokens.surface_bg};
                border: 1px solid {tokens.surface_border};
                border-radius: 8px;
                color: {tokens.fg};
                padding: 0 16px;
                font-size: 12px;
                font-weight: 600;
                font-family: 'Segoe UI Variable', 'Segoe UI', sans-serif;
            }}
            QPushButton:hover {{
                background-color: {tokens.surface_bg_hover};
                border: 1px solid {tokens.surface_border_hover};
            }}
            QPushButton:pressed {{
                background-color: {tokens.surface_bg_pressed};
            }}
            """
        )
        self._restore_deleted_btn.clicked.connect(self._on_restore_deleted)
        self._restore_deleted_btn.setVisible(False)
        self.add_widget(self._restore_deleted_btn)

        self.add_spacing(12)

        # Buttons: create + import (above the preset list)
        self._buttons_container = QWidget()
        self._buttons_container.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self._buttons_container_layout = QVBoxLayout(self._buttons_container)
        self._buttons_container_layout.setContentsMargins(0, 0, 0, 0)
        self._buttons_container_layout.setSpacing(8)

        self._buttons_rows: list[tuple[QWidget, QHBoxLayout]] = []
        for _ in range(5):
            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(12)
            row_widget.setVisible(False)
            self._buttons_container_layout.addWidget(row_widget)
            self._buttons_rows.append((row_widget, row_layout))

        self.create_btn = self._create_main_button("Создать новый", "fa5s.plus", accent=True)
        self.create_btn.clicked.connect(self._on_create_clicked)

        self.import_btn = self._create_secondary_row_button("Импорт из файла", "fa5s.file-import")
        self.import_btn.clicked.connect(self._on_import_clicked)

        self.reset_all_btn = self._create_secondary_row_button("Сбросить все пресеты", "fa5s.undo")
        self.reset_all_btn.clicked.connect(self._on_reset_all_presets_clicked)
        self._apply_reset_all_button_style(False)

        self.presets_info_btn = self._create_secondary_row_button("о пресетах", "fa5s.info-circle")
        self.presets_info_btn.clicked.connect(self._open_presets_info)

        self.disable_all_btn = ResetActionButton("Выключить", confirm_text="Все отключить?")
        self.disable_all_btn.reset_confirmed.connect(self._on_disable_all_strategies)

        self._toolbar_buttons = [
            self.create_btn,
            self.import_btn,
            self.reset_all_btn,
            self.presets_info_btn,
            self.disable_all_btn,
        ]
        self._update_toolbar_buttons_layout()
        self.add_widget(self._buttons_container)

        self.add_spacing(4)

        # Inline create/rename panel
        self._action_reveal = _RevealFrame(self)
        self._action_reveal.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self._action_reveal_layout = QVBoxLayout(self._action_reveal)
        self._action_reveal_layout.setContentsMargins(0, 0, 0, 0)
        self._action_reveal_layout.setSpacing(0)

        self._action_card = SettingsCard("")
        # SettingsCard background/border are theme-driven globally; avoid overriding them here.
        self._action_card.setStyleSheet("")
        self._action_card.main_layout.setSpacing(10)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(10)
        self._action_icon = QLabel()
        self._action_icon.setPixmap(qta.icon("fa5s.plus", color=tokens.accent_hex).pixmap(18, 18))
        self._action_icon.setFixedSize(22, 22)
        header.addWidget(self._action_icon)
        self._action_title = QLabel("")
        try:
            self._action_title.setProperty("tone", "primary")
        except Exception:
            pass
        self._action_title.setStyleSheet(
            """
            QLabel {
                font-size: 14px;
                font-weight: 600;
                font-family: 'Segoe UI Variable', 'Segoe UI', sans-serif;
            }
            """
        )
        header.addWidget(self._action_title)
        header.addStretch(1)
        self._action_close_btn = QPushButton()
        self._action_close_btn.setIcon(qta.icon("fa5s.times", color=tokens.fg))
        self._action_close_btn.setIconSize(QSize(12, 12))
        self._action_close_btn.setFixedSize(28, 28)
        self._action_close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._action_close_btn.setStyleSheet(
            f"""
            QPushButton {{
                background: {tokens.surface_bg};
                border: 1px solid {tokens.surface_border};
                border-radius: 6px;
                color: {tokens.fg};
            }}
            QPushButton:hover {{ background: {tokens.surface_bg_hover}; border: 1px solid {tokens.surface_border_hover}; }}
            QPushButton:pressed {{ background: {tokens.surface_bg_pressed}; }}
            """
        )
        self._action_close_btn.clicked.connect(self._hide_inline_action)
        header.addWidget(self._action_close_btn)
        self._action_card.add_layout(header)

        self._action_subtitle = QLabel("")
        try:
            self._action_subtitle.setProperty("tone", "muted")
        except Exception:
            pass
        self._action_subtitle.setStyleSheet("font-size: 12px;")
        self._action_subtitle.setWordWrap(True)
        self._action_card.add_widget(self._action_subtitle)

        self._rename_from_label = QLabel("")
        try:
            self._rename_from_label.setProperty("tone", "faint")
        except Exception:
            pass
        self._rename_from_label.setStyleSheet("font-size: 12px;")
        self._rename_from_label.setWordWrap(True)
        self._rename_from_label.hide()
        self._action_card.add_widget(self._rename_from_label)

        name_row = QVBoxLayout()
        name_row.setSpacing(6)
        name_label = QLabel("Название")
        try:
            name_label.setProperty("tone", "muted")
        except Exception:
            pass
        name_label.setStyleSheet("font-size: 12px;")
        name_row.addWidget(name_label)
        self._name_input = QLineEdit()
        self._name_input.setPlaceholderText("Введите название пресета…")
        self._name_input.setStyleSheet(
            f"""
            QLineEdit {{
                background-color: {tokens.surface_bg};
                border: 1px solid {tokens.surface_border};
                border-radius: 8px;
                color: {tokens.fg};
                padding: 10px 12px;
                font-size: 13px;
                font-family: 'Segoe UI Variable', 'Segoe UI', sans-serif;
            }}
            QLineEdit:hover {{ background-color: {tokens.surface_bg_hover}; }}
            QLineEdit:focus {{ border: 1px solid {tokens.accent_hex}; }}
            """
        )
        self._name_input.textChanged.connect(lambda: self._set_inline_error(""))
        self._name_input.returnPressed.connect(self._submit_inline_action)
        name_row.addWidget(self._name_input)
        self._action_card.add_layout(name_row)

        self._source_container = QWidget()
        source_row = QHBoxLayout(self._source_container)
        source_row.setContentsMargins(0, 4, 0, 0)
        source_row.setSpacing(12)
        source_label = QLabel("Создать на основе")
        try:
            source_label.setProperty("tone", "muted")
        except Exception:
            pass
        source_label.setStyleSheet("font-size: 12px;")
        source_row.addWidget(source_label)
        source_row.addStretch(1)
        self._create_source = _SegmentedChoice("Текущего активного", "current", "Пустого", "empty", self)
        source_row.addWidget(self._create_source)
        self._action_card.add_widget(self._source_container)

        self._action_error = QLabel("")
        self._action_error.setStyleSheet(
            f"""
            QLabel {{
                color: {semantic.error};
                font-size: 12px;
            }}
            """
        )
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

        # Search presets by name (filters the list).
        self._preset_search_input = QLineEdit()
        self._preset_search_input.setPlaceholderText("Поиск пресетов по имени...")
        self._preset_search_input.setClearButtonEnabled(True)
        set_line_edit_clear_button_icon(self._preset_search_input)
        self._preset_search_input.setFixedHeight(34)
        self._preset_search_input.setProperty("noDrag", True)
        self._preset_search_input.setStyleSheet(
            f"""
            QLineEdit {{
                background: {tokens.surface_bg};
                border: 1px solid {tokens.surface_border};
                border-radius: 8px;
                color: {tokens.fg};
                padding: 0 12px;
                font-size: 13px;
                font-family: 'Segoe UI Variable', 'Segoe UI', sans-serif;
            }}
            QLineEdit:hover {{ background: {tokens.surface_bg_hover}; }}
            QLineEdit:focus {{ border: 1px solid {tokens.accent_hex}; }}
            QLineEdit::placeholder {{
                color: {tokens.fg_faint};
            }}
            """
        )
        self._preset_search_input.textChanged.connect(self._on_preset_search_text_changed)
        self.add_widget(self._preset_search_input)

        self.presets_list = _LinkedWheelListView(self)
        self.presets_list.setObjectName("userPresetsList")
        self.presets_list.setMouseTracking(True)
        self.presets_list.setSelectionMode(QListView.SelectionMode.NoSelection)
        self.presets_list.setEditTriggers(QListView.EditTrigger.NoEditTriggers)
        self.presets_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.presets_list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.presets_list.setVerticalScrollMode(QListView.ScrollMode.ScrollPerPixel)
        self.presets_list.setUniformItemSizes(False)
        self.presets_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.presets_list.setProperty("uiList", True)
        self.presets_list.setProperty("noDrag", True)
        self.presets_list.viewport().setProperty("noDrag", True)
        # List visuals are centralized in ui/theme.py (QAbstractItemView + QScrollBar).
        self.presets_list.setStyleSheet("")

        self._presets_model = _PresetListModel(self.presets_list)
        self._presets_delegate = _PresetListDelegate(self.presets_list)
        self._presets_delegate.action_triggered.connect(self._on_preset_list_action)
        self.presets_list.setModel(self._presets_model)
        self.presets_list.setItemDelegate(self._presets_delegate)
        self.presets_list.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.presets_list.verticalScrollBar().setSingleStep(28)
        self.add_widget(self.presets_list)

        # Make outer page scrolling feel less sluggish on long lists.
        self.verticalScrollBar().setSingleStep(48)

    def _create_main_button(self, text: str, icon_name: str, accent: bool = False) -> QPushButton:
        btn = QPushButton(text)
        btn.setIconSize(QSize(16, 16))
        btn.setFixedHeight(36)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._apply_row_button_theme(btn, icon_name, accent=accent)

        return btn

    def _accent_row_button_style(self) -> str:
        tokens = get_theme_tokens()
        accent_fg = _accent_fg_for_tokens(tokens)
        return f"""
            QPushButton {{
                background-color: {tokens.accent_hex};
                border: none;
                border-radius: 8px;
                color: {accent_fg};
                padding: 0 20px;
                font-size: 13px;
                font-weight: 600;
                font-family: 'Segoe UI Variable', 'Segoe UI', sans-serif;
            }}
            QPushButton:hover {{
                background-color: {tokens.accent_hover_hex};
            }}
            QPushButton:pressed {{
                background-color: {tokens.accent_pressed_hex};
            }}
        """

    def _plain_main_button_style(self) -> str:
        tokens = get_theme_tokens()
        return f"""
            QPushButton {{
                background-color: {tokens.surface_bg};
                border: 1px solid {tokens.surface_border};
                border-radius: 8px;
                color: {tokens.fg};
                padding: 0 20px;
                font-size: 13px;
                font-weight: 600;
                font-family: 'Segoe UI Variable', 'Segoe UI', sans-serif;
            }}
            QPushButton:hover {{
                background-color: {tokens.surface_bg_hover};
                border: 1px solid {tokens.surface_border_hover};
            }}
            QPushButton:pressed {{
                background-color: {tokens.surface_bg_pressed};
            }}
        """

    def _secondary_row_button_style(self) -> str:
        tokens = get_theme_tokens()
        return f"""
            QPushButton {{
                background-color: {tokens.surface_bg};
                border: 1px solid {tokens.surface_border};
                border-radius: 4px;
                color: {tokens.fg};
                padding: 0 16px;
                font-size: 12px;
                font-weight: 600;
                font-family: 'Segoe UI Variable', 'Segoe UI', sans-serif;
            }}
            QPushButton:hover {{
                background-color: {tokens.surface_bg_hover};
                border: 1px solid {tokens.surface_border_hover};
            }}
            QPushButton:pressed {{
                background-color: {tokens.surface_bg_pressed};
            }}
        """

    def _create_secondary_row_button(self, text: str, icon_name: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setIconSize(QSize(16, 16))
        btn.setFixedHeight(32)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._apply_secondary_row_button_theme(btn, icon_name)
        return btn

    def _apply_row_button_theme(self, btn: QPushButton, icon_name: str, *, accent: bool) -> None:
        tokens = get_theme_tokens()
        if accent:
            accent_fg = _accent_fg_for_tokens(tokens)
            btn.setIcon(qta.icon(icon_name, color=accent_fg))
            btn.setStyleSheet(self._accent_row_button_style())
            return
        btn.setIcon(qta.icon(icon_name, color=tokens.fg))
        btn.setStyleSheet(self._plain_main_button_style())

    def _apply_secondary_row_button_theme(self, btn: QPushButton, icon_name: str) -> None:
        tokens = get_theme_tokens()
        btn.setIcon(qta.icon(icon_name, color=tokens.fg))
        btn.setStyleSheet(self._secondary_row_button_style())

    def _apply_page_theme(self) -> None:
        try:
            tokens = get_theme_tokens()
            theme_key = (str(tokens.theme_name), str(tokens.accent_hex), str(tokens.surface_bg))
            if theme_key == self._last_page_theme_key:
                return

            semantic = get_semantic_palette(tokens.theme_name)

            if getattr(self, "_configs_icon", None) is not None:
                self._configs_icon.setPixmap(qta.icon("fa5b.telegram", color=tokens.accent_hex).pixmap(18, 18))

            if getattr(self, "_restore_deleted_btn", None) is not None:
                self._restore_deleted_btn.setIcon(qta.icon("fa5s.undo", color=tokens.fg))
                self._restore_deleted_btn.setStyleSheet(
                    f"""
                    QPushButton {{
                        background-color: {tokens.surface_bg};
                        border: 1px solid {tokens.surface_border};
                        border-radius: 8px;
                        color: {tokens.fg};
                        padding: 0 16px;
                        font-size: 12px;
                        font-weight: 600;
                        font-family: 'Segoe UI Variable', 'Segoe UI', sans-serif;
                    }}
                    QPushButton:hover {{
                        background-color: {tokens.surface_bg_hover};
                        border: 1px solid {tokens.surface_border_hover};
                    }}
                    QPushButton:pressed {{
                        background-color: {tokens.surface_bg_pressed};
                    }}
                    """
                )

            if getattr(self, "create_btn", None) is not None:
                self._apply_row_button_theme(self.create_btn, "fa5s.plus", accent=True)
            if getattr(self, "import_btn", None) is not None:
                self._apply_secondary_row_button_theme(self.import_btn, "fa5s.file-import")
            if getattr(self, "presets_info_btn", None) is not None:
                self._apply_secondary_row_button_theme(self.presets_info_btn, "fa5s.info-circle")
            if getattr(self, "_action_cancel_btn", None) is not None:
                self._apply_row_button_theme(self._action_cancel_btn, "fa5s.times", accent=False)
            if getattr(self, "_action_submit_btn", None) is not None:
                self._apply_row_button_theme(self._action_submit_btn, "fa5s.check", accent=True)

            if getattr(self, "_action_icon", None) is not None:
                action_icon_name = "fa5s.edit" if self._action_mode == "rename" else "fa5s.plus"
                self._action_icon.setPixmap(qta.icon(action_icon_name, color=tokens.accent_hex).pixmap(18, 18))

            if getattr(self, "_action_close_btn", None) is not None:
                self._action_close_btn.setIcon(qta.icon("fa5s.times", color=tokens.fg))
                self._action_close_btn.setStyleSheet(
                    f"""
                    QPushButton {{
                        background: {tokens.surface_bg};
                        border: 1px solid {tokens.surface_border};
                        border-radius: 6px;
                        color: {tokens.fg};
                    }}
                    QPushButton:hover {{ background: {tokens.surface_bg_hover}; border: 1px solid {tokens.surface_border_hover}; }}
                    QPushButton:pressed {{ background: {tokens.surface_bg_pressed}; }}
                    """
                )

            if getattr(self, "_name_input", None) is not None:
                self._name_input.setStyleSheet(
                    f"""
                    QLineEdit {{
                        background-color: {tokens.surface_bg};
                        border: 1px solid {tokens.surface_border};
                        border-radius: 8px;
                        color: {tokens.fg};
                        padding: 10px 12px;
                        font-size: 13px;
                        font-family: 'Segoe UI Variable', 'Segoe UI', sans-serif;
                    }}
                    QLineEdit:hover {{ background-color: {tokens.surface_bg_hover}; }}
                    QLineEdit:focus {{ border: 1px solid {tokens.accent_hex}; }}
                    """
                )
                set_line_edit_clear_button_icon(self._name_input, color=tokens.fg_muted)

            if self._preset_search_input is not None:
                self._preset_search_input.setStyleSheet(
                    f"""
                    QLineEdit {{
                        background: {tokens.surface_bg};
                        border: 1px solid {tokens.surface_border};
                        border-radius: 8px;
                        color: {tokens.fg};
                        padding: 0 12px;
                        font-size: 13px;
                        font-family: 'Segoe UI Variable', 'Segoe UI', sans-serif;
                    }}
                    QLineEdit:hover {{ background: {tokens.surface_bg_hover}; }}
                    QLineEdit:focus {{ border: 1px solid {tokens.accent_hex}; }}
                    QLineEdit::placeholder {{ color: {tokens.fg_faint}; }}
                    """
                )
                set_line_edit_clear_button_icon(self._preset_search_input, color=tokens.fg_muted)

            if getattr(self, "_action_error", None) is not None:
                self._action_error.setStyleSheet(
                    f"""
                    QLabel {{
                        color: {semantic.error};
                        font-size: 12px;
                    }}
                    """
                )

            if getattr(self, "reset_all_btn", None) is not None:
                if self._reset_all_confirm_pending:
                    self._apply_reset_all_button_style(True)
                    confirm_icon_color = _pick_contrast_color(
                        semantic.on_color,
                        _to_qcolor(semantic.danger_bg, "#dc3545"),
                        [tokens.fg, "#ffffff"],
                        minimum_ratio=3.0,
                    )
                    self.reset_all_btn.setIcon(qta.icon("fa5s.exclamation-triangle", color=confirm_icon_color))
                else:
                    self._apply_reset_all_button_style(False)
                    if getattr(self, "_reset_all_result_token", None) is None:
                        self.reset_all_btn.setIcon(qta.icon("fa5s.undo", color=tokens.fg))

            pop = getattr(self, "_action_popover", None)
            if pop is not None:
                pop._apply_styles()

            if getattr(self, "presets_list", None) is not None:
                self.presets_list.viewport().update()

            self._last_page_theme_key = theme_key

        except Exception as e:
            log(f"Ошибка применения темы на странице пресетов: {e}", "DEBUG")

    def _content_inner_width(self) -> int:
        margins = self.layout.contentsMargins()
        return max(0, self.viewport().width() - margins.left() - margins.right())

    def _compute_toolbar_rows(self, available_width: int) -> list[list[QPushButton]]:
        buttons = getattr(self, "_toolbar_buttons", [])
        if not buttons:
            return []

        if available_width <= 0:
            return [buttons]

        spacing = 12
        rows: list[list[QPushButton]] = []
        current_row: list[QPushButton] = []
        current_width = 0

        for button in buttons:
            button_width = button.sizeHint().width()
            if not current_row:
                current_row = [button]
                current_width = button_width
                continue

            next_width = current_width + spacing + button_width
            if next_width <= available_width:
                current_row.append(button)
                current_width = next_width
                continue

            rows.append(current_row)
            current_row = [button]
            current_width = button_width

        if current_row:
            rows.append(current_row)

        return rows

    def _clear_toolbar_row(self, row_layout: QHBoxLayout):
        while row_layout.count():
            row_layout.takeAt(0)

    def _update_toolbar_buttons_layout(self):
        rows = getattr(self, "_buttons_rows", None)
        if not rows:
            return

        assigned_rows = self._compute_toolbar_rows(self._content_inner_width())

        for index, (row_widget, row_layout) in enumerate(rows):
            self._clear_toolbar_row(row_layout)
            row_buttons = assigned_rows[index] if index < len(assigned_rows) else []

            if row_buttons:
                for button in row_buttons:
                    row_layout.addWidget(button)
                row_layout.addStretch(1)
                row_widget.setVisible(True)
            else:
                row_widget.setVisible(False)

    def _apply_reset_all_button_style(self, confirm: bool):
        if confirm:
            tokens = get_theme_tokens()
            semantic = get_semantic_palette(tokens.theme_name)
            danger_bg = _to_qcolor(semantic.danger_bg, "#dc3545")
            confirm_fg = _pick_contrast_color(
                semantic.on_color,
                danger_bg,
                [tokens.fg, "#ffffff"],
                minimum_ratio=3.0,
            )
            self.reset_all_btn.setStyleSheet(
                f"""
                QPushButton {{
                    background-color: {semantic.danger_bg};
                    border: 1px solid {semantic.error_soft_border};
                    border-radius: 4px;
                    color: {confirm_fg};
                    padding: 0 16px;
                    font-size: 12px;
                    font-weight: 700;
                    font-family: 'Segoe UI Variable', 'Segoe UI', sans-serif;
                }}
                QPushButton:hover {{
                    background-color: {semantic.danger_bg_strong};
                }}
                QPushButton:pressed {{
                    background-color: {semantic.danger_button_hover};
                }}
                """
            )
            return

        self.reset_all_btn.setStyleSheet(self._secondary_row_button_style())

    def _arm_reset_all_confirmation(self):
        # Cancel any pending "result" restore timer.
        self._reset_all_result_token = None
        self._reset_all_confirm_pending = True
        self.reset_all_btn.setText("Это сбросит ваши настройки")
        tokens = get_theme_tokens()
        semantic = get_semantic_palette(tokens.theme_name)
        confirm_icon_color = _pick_contrast_color(
            semantic.on_color,
            _to_qcolor(semantic.danger_bg, "#dc3545"),
            [tokens.fg, "#ffffff"],
            minimum_ratio=3.0,
        )
        self.reset_all_btn.setIcon(qta.icon("fa5s.exclamation-triangle", color=confirm_icon_color))
        self._apply_reset_all_button_style(True)
        self._reset_all_confirm_timer.start(5000)
        self._update_toolbar_buttons_layout()
        self._schedule_layout_resync()

    def _clear_reset_all_confirmation(self):
        self._reset_all_confirm_pending = False
        self._reset_all_confirm_timer.stop()
        self.reset_all_btn.setText("Сбросить все пресеты")
        try:
            self.reset_all_btn.setIcon(qta.icon("fa5s.undo", color=get_theme_tokens().fg))
        except Exception:
            self.reset_all_btn.setIcon(qta.icon("fa5s.undo", color="rgba(245, 245, 245, 0.95)"))
        self._apply_reset_all_button_style(False)
        self._update_toolbar_buttons_layout()
        if self.isVisible():
            self._schedule_layout_resync()

    def _restore_reset_all_button_from_result(self, token) -> None:
        if getattr(self, "_reset_all_result_token", None) is not token:
            return
        if self._reset_all_confirm_pending:
            return
        self._reset_all_result_token = None
        self._clear_reset_all_confirmation()

    def _show_reset_all_result(self, success_count: int, total_count: int) -> None:
        # Show short numeric stats directly on the button.
        token = object()
        self._reset_all_result_token = token

        try:
            self._reset_all_confirm_pending = False
            self._reset_all_confirm_timer.stop()
        except Exception:
            pass

        total = int(total_count or 0)
        ok = int(success_count or 0)
        self.reset_all_btn.setText(f"{ok}/{total}")

        # Visual cue: green check on full success, warning otherwise.
        try:
            icon_name = "fa5s.check" if total > 0 and ok >= total else "fa5s.exclamation-triangle"
            self.reset_all_btn.setIcon(qta.icon(icon_name, color=get_theme_tokens().fg))
        except Exception:
            pass

        self._apply_reset_all_button_style(False)
        self._update_toolbar_buttons_layout()
        if self.isVisible():
            self._schedule_layout_resync()

        QTimer.singleShot(3000, lambda: self._restore_reset_all_button_from_result(token))

    def _is_game_filter_preset_name(self, name: str) -> bool:
        return "game filter" in name.lower()

    def _is_all_tcp_udp_preset_name(self, name: str) -> bool:
        return "all tcp" in name.lower()

    def _format_modified_timestamp(self, modified: str) -> str:
        if not modified:
            return ""
        try:
            dt = datetime.fromisoformat(modified.replace("Z", "+00:00"))
            return dt.strftime("%d.%m.%Y %H:%M")
        except Exception:
            return modified

    def _on_preset_search_text_changed(self, _text: str) -> None:
        # Debounce to avoid reloading on every keystroke.
        try:
            self._preset_search_timer.start(180)
        except Exception:
            self._load_presets()

    def _apply_preset_search(self) -> None:
        if not self.isVisible():
            self._ui_dirty = True
            return
        self._load_presets()

    def _update_presets_view_height(self):
        if not self._presets_model or not hasattr(self, "presets_list"):
            return

        viewport_height = self.viewport().height()
        if viewport_height <= 0:
            return

        top = max(0, self.presets_list.geometry().top())
        bottom_margin = self.layout.contentsMargins().bottom()
        target_height = max(220, viewport_height - top - bottom_margin)

        if self.presets_list.minimumHeight() != target_height:
            self.presets_list.setMinimumHeight(target_height)
        if self.presets_list.maximumHeight() != target_height:
            self.presets_list.setMaximumHeight(target_height)

    def _hide_inline_action(self):
        self._action_mode = None
        self._rename_source_name = None

        try:
            pop = getattr(self, "_action_popover", None)
            if pop and pop.isVisible():
                pop.hide_animated()
        except Exception:
            pass

        # Legacy inline panel (kept for backwards compatibility / safe fallback).
        try:
            self._action_error.hide()
            self._action_error.setText("")
            self._action_reveal.set_open(False)
        except Exception:
            pass
        self._schedule_layout_resync(include_delayed=True)

    def _set_inline_error(self, text: str):
        try:
            pop = getattr(self, "_action_popover", None)
            if pop and pop.isVisible():
                pop.set_error(text)
                return
        except Exception:
            pass

        # Fallback (legacy inline panel).
        try:
            self._action_error.setText(text)
            self._action_error.setVisible(bool(text))
        except Exception:
            pass

    def _show_inline_action_create(self):
        self._action_mode = "create"
        self._rename_source_name = None
        self._set_inline_error("")

        try:
            # Ensure old inline panel stays closed.
            self._action_reveal.set_open(False)
        except Exception:
            pass

        pop = getattr(self, "_action_popover", None)
        if not pop:
            return
        pop.configure_create()
        try:
            pop.show_for_widget(self.create_btn)
        except Exception:
            pop.show_near_point(QCursor.pos())
        pop.focus_name()

    def _show_inline_action_rename(self, current_name: str):
        self._action_mode = "rename"
        self._rename_source_name = current_name
        self._set_inline_error("")

        try:
            # Ensure old inline panel stays closed.
            self._action_reveal.set_open(False)
        except Exception:
            pass

        pop = getattr(self, "_action_popover", None)
        if not pop:
            return
        pop.configure_rename(current_name)
        pop.show_near_point(QCursor.pos())
        pop.focus_name(select_all=True)

    def _submit_inline_action(self):
        mode = self._action_mode
        if mode not in ("create", "rename"):
            return

        name = ""
        from_current = True
        try:
            pop = getattr(self, "_action_popover", None)
            if pop and pop.isVisible():
                name = pop.name_text().strip()
                from_current = pop.source_value() == "current"
        except Exception:
            name = ""

        if not name:
            # Fallback to legacy inline panel.
            try:
                name = self._name_input.text().strip()
                from_current = self._create_source.value() == "current"
            except Exception:
                name = ""

        if not name:
            self._set_inline_error("Введите название.")
            return

        try:
            manager = self._get_manager()

            if mode == "create":
                if manager.preset_exists(name):
                    self._set_inline_error(f"Пресет '{name}' уже существует.")
                    return

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

    def _on_create_clicked(self):
        try:
            pop = getattr(self, "_action_popover", None)
            pop_visible = bool(pop and pop.isVisible())
        except Exception:
            pop_visible = False

        if self._action_mode == "create" and pop_visible:
            self._hide_inline_action()
        else:
            self._show_inline_action_create()

    def _on_import_clicked(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Импортировать пресет",
            "",
            "Preset files (*.txt);;All files (*.*)",
        )

        if not file_path:
            return

        try:
            manager = self._get_manager()
            name = Path(file_path).stem

            if manager.preset_exists(name):
                result = QMessageBox.question(
                    self,
                    "Пресет существует",
                    f"Пресет '{name}' уже существует. Импортировать с другим именем?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )
                if result == QMessageBox.StandardButton.Yes:
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

    def _on_reset_all_presets_clicked(self):
        if not self._reset_all_confirm_pending:
            self._arm_reset_all_confirmation()
            return

        self._clear_reset_all_confirmation()

        self._bulk_reset_running = True
        try:
            manager = self._get_manager()

            # 1) Refresh templates and create any missing presets from templates.
            try:
                from preset_zapret2.preset_defaults import invalidate_templates_cache, ensure_templates_copied_to_presets
                invalidate_templates_cache()
                ensure_templates_copied_to_presets()
            except Exception as e:
                log(f"Ошибка обновления шаблонов пресетов: {e}", "DEBUG")

            # 2) Reload store so newly created presets appear in manager.list_presets().
            try:
                manager.invalidate_preset_cache(None)
            except Exception:
                pass

            preset_names = manager.list_presets()
            ordered_names = sorted(preset_names, key=lambda s: s.lower())
            if not ordered_names:
                self._show_reset_all_result(0, 0)
                return

            original_active = (manager.get_active_preset_name() or "").strip()

            # Reset the active preset last, then sync it once.
            if original_active and original_active in ordered_names:
                ordered_names = [n for n in ordered_names if n != original_active] + [original_active]

            success_count = 0
            failed: list[str] = []

            for name in ordered_names:
                ok = manager.reset_preset_to_default_template(
                    name,
                    make_active=False,
                    sync_active_file=False,
                    emit_switched=False,
                    invalidate_templates=False,
                )
                if ok:
                    success_count += 1
                else:
                    failed.append(name)

            # 3) Apply active preset once (single write => single hot-reload).
            active_name = (original_active or (manager.get_active_preset_name() or "")).strip()
            if active_name:
                preset = manager.load_preset(active_name)
                if preset:
                    if not manager.sync_preset_to_active_file(preset):
                        log(f"Не удалось применить активный пресет после сброса: {active_name}", "WARNING")
                else:
                    log(f"Не удалось загрузить активный пресет после сброса: {active_name}", "WARNING")

            self._load_presets()

            total = len(ordered_names)
            if failed:
                log(f"Сброс пресетов завершён частично: успешно={success_count}, ошибки={len(failed)}", "WARNING")
            else:
                log(f"Сброшены все пресеты к шаблонам: {success_count}", "INFO")

            self._show_reset_all_result(success_count, total)

        except Exception as e:
            log(f"Ошибка массового сброса пресетов: {e}", "ERROR")
            QMessageBox.critical(self, "Ошибка", f"Ошибка сброса пресетов: {e}")
        finally:
            self._bulk_reset_running = False

    def _on_disable_all_strategies(self):
        """Отключает стратегии для всех категорий в активном пресете."""
        try:
            manager = self._get_manager()
            if not manager.clear_all_strategy_selections(save_and_sync=True):
                QMessageBox.warning(self, "Ошибка", "Не удалось отключить стратегии для всех категорий.")
                return

            self._load_presets()
            self._refresh_pages_after_strategy_change()

            try:
                host = self.window()
                if host:
                    from dpi.zapret2_core_restart import trigger_dpi_reload
                    trigger_dpi_reload(host, reason="preset_clear_all")
            except Exception as e:
                log(f"Ошибка перезапуска DPI после отключения стратегий: {e}", "DEBUG")

            log("Все стратегии текущего пресета отключены", "INFO")

        except Exception as e:
            log(f"Ошибка отключения стратегий: {e}", "ERROR")
            QMessageBox.critical(self, "Ошибка", f"Ошибка отключения стратегий: {e}")

    def _refresh_pages_after_strategy_change(self):
        """Обновляет страницы Zapret2 после изменения стратегий активного пресета."""
        host = self.window()
        if not host:
            return

        try:
            if hasattr(host, "_schedule_refresh_after_preset_switch"):
                host._schedule_refresh_after_preset_switch()
                return
        except Exception as e:
            log(f"Ошибка планирования обновления UI после отключения стратегий: {e}", "DEBUG")

        try:
            page = getattr(host, "zapret2_strategies_page", None)
            if page and hasattr(page, "refresh_from_preset_switch"):
                page.refresh_from_preset_switch()
        except Exception as e:
            log(f"Ошибка обновления страницы стратегий после отключения: {e}", "DEBUG")

        try:
            detail = getattr(host, "strategy_detail_page", None)
            if detail and hasattr(detail, "refresh_from_preset_switch"):
                detail.refresh_from_preset_switch()
        except Exception as e:
            log(f"Ошибка обновления страницы категории после отключения: {e}", "DEBUG")

    def _load_presets(self):
        self._ui_dirty = False
        try:
            # ── Read data from PresetStore (in-memory, no disk I/O) ──────
            from preset_zapret2.preset_store import get_preset_store
            store = get_preset_store()
            all_presets = store.get_all_presets()       # {name: Preset}
            active_name = store.get_active_preset_name()
            sorted_names = sorted(all_presets.keys(), key=lambda s: s.lower())

            query = ""
            try:
                if self._preset_search_input is not None:
                    query = (self._preset_search_input.text() or "").strip().lower()
            except Exception:
                query = ""

            def matches(name: str) -> bool:
                if not query:
                    return True
                return query in name.lower()

            all_tcp_names = [name for name in sorted_names if self._is_all_tcp_udp_preset_name(name)]
            regular_names = [
                name
                for name in sorted_names
                if not self._is_game_filter_preset_name(name) and not self._is_all_tcp_udp_preset_name(name)
            ]
            game_filter_names = [
                name
                for name in sorted_names
                if self._is_game_filter_preset_name(name) and not self._is_all_tcp_udp_preset_name(name)
            ]

            # Apply search filter per group to keep the existing ordering.
            regular_names = [name for name in regular_names if matches(name)]
            game_filter_names = [name for name in game_filter_names if matches(name)]
            all_tcp_names = [name for name in all_tcp_names if matches(name)]

            rows: list[dict[str, object]] = []

            def add_preset_row(name: str):
                preset = all_presets.get(name)
                if not preset:
                    return
                rows.append(
                    {
                        "kind": "preset",
                        "name": name,
                        "description": preset.description or "",
                        "date": self._format_modified_timestamp(preset.modified or ""),
                        "is_active": name == active_name,
                        "icon_color": _normalize_preset_icon_color(getattr(preset, "icon_color", None)),
                    }
                )

            for name in regular_names:
                add_preset_row(name)

            if game_filter_names:
                rows.append({"kind": "section", "text": "Игры (game filter)"})
                for name in game_filter_names:
                    add_preset_row(name)

            if all_tcp_names:
                rows.append({"kind": "section", "text": "Все сайты (ALL TCP/UDP)"})
                for name in all_tcp_names:
                    add_preset_row(name)

            if not rows:
                if query:
                    rows.append({"kind": "empty", "text": "Ничего не найдено."})
                else:
                    rows.append({"kind": "empty", "text": "Нет пресетов. Создайте новый или импортируйте из файла."})

            if self._presets_delegate:
                self._presets_delegate.reset_interaction_state()
            if self._presets_model:
                self._presets_model.set_rows(rows)

            # Update restore-deleted button visibility
            try:
                from preset_zapret2.preset_defaults import get_deleted_preset_names
                has_deleted = bool(get_deleted_preset_names())
                self._restore_deleted_btn.setVisible(has_deleted)
            except Exception:
                self._restore_deleted_btn.setVisible(False)

            self._update_presets_view_height()
            self._schedule_layout_resync()

        except Exception as e:
            log(f"Ошибка загрузки пресетов: {e}", "ERROR")

    def _on_preset_list_action(self, action: str, name: str):
        handlers = {
            "activate": self._on_activate_preset,
            "rename": self._on_rename_preset,
            "duplicate": self._on_duplicate_preset,
            "reset": self._on_reset_preset,
            "delete": self._on_delete_preset,
            "export": self._on_export_preset,
        }
        handler = handlers.get(action)
        if handler:
            handler(name)

    def _on_activate_preset(self, name: str):
        try:
            manager = self._get_manager()

            if manager.switch_preset(name, reload_dpi=False):
                log(f"Активирован пресет '{name}'", "INFO")
                self.preset_switched.emit(name)
                self._load_presets()
            else:
                QMessageBox.warning(self, "Ошибка", f"Не удалось активировать пресет '{name}'")

        except Exception as e:
            log(f"Ошибка активации пресета: {e}", "ERROR")
            QMessageBox.critical(self, "Ошибка", f"Ошибка: {e}")

    def _on_rename_preset(self, name: str):
        try:
            pop = getattr(self, "_action_popover", None)
            pop_visible = bool(pop and pop.isVisible())
        except Exception:
            pop_visible = False

        if self._action_mode == "rename" and self._rename_source_name == name and pop_visible:
            self._hide_inline_action()
        else:
            self._show_inline_action_rename(name)

    def _on_duplicate_preset(self, name: str):
        try:
            manager = self._get_manager()

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

    def _on_reset_preset(self, name: str):
        try:
            manager = self._get_manager()

            if not manager.reset_preset_to_default_template(name):
                QMessageBox.warning(self, "Ошибка", "Не удалось сбросить пресет к настройкам шаблона")
                return

            log(f"Сброшен пресет '{name}' к шаблону", "INFO")
            self.preset_switched.emit(name)
            self._load_presets()

        except Exception as e:
            log(f"Ошибка сброса пресета: {e}", "ERROR")
            QMessageBox.critical(self, "Ошибка", f"Ошибка: {e}")

    def _on_delete_preset(self, name: str):
        try:
            manager = self._get_manager()

            if manager.delete_preset(name):
                log(f"Удалён пресет '{name}'", "INFO")
                # Mark as deleted so it can be restored later (if it has a matching template)
                try:
                    from preset_zapret2.preset_defaults import mark_preset_deleted
                    mark_preset_deleted(name)
                except Exception:
                    pass
                self.preset_deleted.emit(name)
                self._load_presets()
            else:
                QMessageBox.warning(self, "Ошибка", "Не удалось удалить пресет")

        except Exception as e:
            log(f"Ошибка удаления пресета: {e}", "ERROR")
            QMessageBox.critical(self, "Ошибка", f"Ошибка: {e}")

    def _on_export_preset(self, name: str):
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Экспортировать пресет",
            f"{name}.txt",
            "Preset files (*.txt);;All files (*.*)",
        )

        if not file_path:
            return

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

    def _on_restore_deleted(self):
        """Restore all previously deleted presets that have matching templates."""
        try:
            from preset_zapret2.preset_defaults import clear_all_deleted_presets, ensure_templates_copied_to_presets
            clear_all_deleted_presets()
            ensure_templates_copied_to_presets()
            log("Восстановлены удалённые пресеты", "INFO")
            self._load_presets()
        except Exception as e:
            log(f"Ошибка восстановления удалённых пресетов: {e}", "ERROR")
            QMessageBox.critical(self, "Ошибка", f"Ошибка восстановления: {e}")

    def _on_preset_switched_callback(self, name: str):
        _ = name

    def _on_dpi_reload_needed(self):
        try:
            widget = self
            while widget:
                if hasattr(widget, "dpi_controller"):
                    widget.dpi_controller.restart_dpi_async()
                    log("DPI перезапущен после смены пресета", "INFO")
                    return
                widget = widget.parent()

            from PyQt6.QtWidgets import QApplication
            for w in QApplication.topLevelWidgets():
                if hasattr(w, "dpi_controller"):
                    w.dpi_controller.restart_dpi_async()
                    log("DPI перезапущен после смены пресета", "INFO")
                    return

        except Exception as e:
            log(f"Ошибка перезапуска DPI: {e}", "ERROR")

    def _open_presets_info(self):
        """Открывает страницу с информацией о пресетах."""
        try:
            from config.urls import PRESET_INFO_URL

            webbrowser.open(PRESET_INFO_URL)
            log(f"Открыта страница о пресетах: {PRESET_INFO_URL}", "INFO")
        except Exception as e:
            log(f"Не удалось открыть страницу о пресетах: {e}", "ERROR")

    def _open_new_configs_post(self):
        try:
            from config.telegram_links import open_telegram_link

            open_telegram_link("nozapretinrussia_bot")
        except Exception as e:
            log(f"Ошибка открытия Telegram: {e}", "ERROR")
            QMessageBox.warning(self.window(), "Ошибка", f"Не удалось открыть Telegram:\n{e}")
