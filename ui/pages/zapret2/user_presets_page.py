# ui/pages/zapret2/user_presets_page.py
"""Zapret 2 Direct: user presets management."""

from __future__ import annotations

from datetime import datetime
import re
import webbrowser
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal, QSize, QTimer, QFileSystemWatcher, QAbstractListModel, QModelIndex, QRect, QEvent
from PyQt6.QtGui import QColor, QPainter, QFontMetrics, QMouseEvent, QHelpEvent, QTransform
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
)
import qtawesome as qta

from ui.pages.base_page import BasePage
from ui.pages.strategies_page_base import ResetActionButton
from ui.sidebar import ActionButton, SettingsCard
from ui.pages.presets_page import _RevealFrame, _SegmentedChoice
from log import log


_icon_cache: dict[str, object] = {}
_DEFAULT_PRESET_ICON_COLOR = "#60cdff"
_HEX_COLOR_RGB_RE = re.compile(r"^#(?:[0-9a-fA-F]{6})$")
_HEX_COLOR_RGBA_RE = re.compile(r"^#(?:[0-9a-fA-F]{8})$")


def _normalize_preset_icon_color(value: Optional[str]) -> str:
    raw = str(value or "").strip()
    if _HEX_COLOR_RGB_RE.fullmatch(raw):
        return raw.lower()
    if _HEX_COLOR_RGBA_RE.fullmatch(raw):
        lowered = raw.lower()
        return f"#{lowered[1:7]}"
    return _DEFAULT_PRESET_ICON_COLOR


def _cached_icon(name: str, color: str):
    key = f"{name}|{color}"
    icon = _icon_cache.get(key)
    if icon is None:
        icon = qta.icon(name, color=color)
        _icon_cache[key] = icon
    return icon


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

    _ROW_HEIGHT = 56
    _SECTION_HEIGHT = 28
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
        card_rect = option_rect.adjusted(0, 2, 0, -2)
        for action, rect in self._action_rects(card_rect, is_active):
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
        text_rect = option.rect.adjusted(4, 6, -4, -2)
        font = painter.font()
        font.setPointSize(10)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor(255, 255, 255, 204))
        painter.drawText(text_rect, int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter), text)
        painter.restore()

    def _paint_empty_row(self, painter: QPainter, option: QStyleOptionViewItem, text: str):
        painter.save()
        painter.setPen(QColor(255, 255, 255, 128))
        font = painter.font()
        font.setPointSize(10)
        painter.setFont(font)
        painter.drawText(option.rect.adjusted(8, 0, -8, 0), int(Qt.AlignmentFlag.AlignCenter), text)
        painter.restore()

    def _paint_preset_row(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex):
        name = str(index.data(_PresetListModel.NameRole) or "")
        date_text = str(index.data(_PresetListModel.DateRole) or "")
        is_active = bool(index.data(_PresetListModel.ActiveRole))

        card_rect = option.rect.adjusted(0, 2, 0, -2)
        hovered = bool(option.state & QStyle.StateFlag.State_MouseOver)

        if is_active:
            bg = QColor(96, 205, 255, 22)
        elif hovered:
            bg = QColor(255, 255, 255, 20)
        else:
            bg = QColor(255, 255, 255, 12)

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(bg)
        painter.drawRoundedRect(card_rect, 8, 8)

        icon_rect = QRect(card_rect.left() + 14, card_rect.center().y() - 10, 20, 20)
        icon_name = "fa5s.star" if is_active else "fa5s.file-alt"
        icon_color = _normalize_preset_icon_color(str(index.data(_PresetListModel.IconColorRole) or ""))
        _cached_icon(icon_name, icon_color).paint(painter, icon_rect)

        action_rects = self._action_rects(card_rect, is_active)
        right_cursor = action_rects[0][1].left() - 10 if action_rects else card_rect.right() - 12

        if is_active:
            badge_text = "Активен"
            badge_font = painter.font()
            badge_font.setPointSize(8)
            badge_font.setBold(True)
            badge_metrics = QFontMetrics(badge_font)
            badge_width = badge_metrics.horizontalAdvance(badge_text) + 14
            badge_rect = QRect(right_cursor - badge_width, card_rect.center().y() - 9, badge_width, 18)

            painter.setBrush(QColor(96, 205, 255))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(badge_rect, 4, 4)

            painter.setFont(badge_font)
            painter.setPen(QColor(0, 0, 0))
            painter.drawText(badge_rect, int(Qt.AlignmentFlag.AlignCenter), badge_text)
            right_cursor = badge_rect.left() - 10

        if date_text:
            date_font = painter.font()
            date_font.setPointSize(9)
            date_font.setBold(False)
            painter.setFont(date_font)
            date_metrics = QFontMetrics(date_font)
            date_width = date_metrics.horizontalAdvance(date_text)
            date_rect = QRect(max(card_rect.left() + 80, right_cursor - date_width), card_rect.top(), date_width, card_rect.height())
            painter.setPen(QColor(255, 255, 255, 90))
            painter.drawText(date_rect, int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter), date_text)
            right_cursor = date_rect.left() - 10

        name_left = icon_rect.right() + 10
        name_rect = QRect(name_left, card_rect.top(), max(40, right_cursor - name_left), card_rect.height())
        name_font = painter.font()
        name_font.setPointSize(11)
        name_font.setBold(True)
        painter.setFont(name_font)
        painter.setPen(QColor(255, 255, 255))
        name_metrics = QFontMetrics(name_font)
        elided_name = name_metrics.elidedText(name, Qt.TextElideMode.ElideRight, name_rect.width())
        painter.drawText(name_rect, int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter), elided_name)

        for action, action_rect in action_rects:
            pending = self._pending_destructive == (name, action)
            if pending:
                btn_bg = QColor(255, 107, 107, 50)
                icon_col = "#ff6b6b"
            else:
                btn_bg = QColor(255, 255, 255, 20)
                icon_col = "#ffffff"

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


class Zapret2UserPresetsPage(BasePage):
    preset_switched = pyqtSignal(str)
    preset_created = pyqtSignal(str)
    preset_deleted = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(
            "Мои пресеты",
            'Здесь кнопка для нубов - "хочу чтобы нажал и всё работает". Выбираете любой пресет - тыкаете - перезагружаете вкладку и смотрите что ресурс открывается (или не открывается). Если не открываете - тыкаете на следующий пресет. Также здесь можно создавать, импортировать, экспортировать и переключать пользовательские пресеты. ',
            parent,
        )

        self._presets_model: Optional[_PresetListModel] = None
        self._presets_delegate: Optional[_PresetListDelegate] = None
        self._manager = None
        self._ui_dirty = True  # needs rebuild on next show

        self._file_watcher: Optional[QFileSystemWatcher] = None
        self._watcher_active = False
        self._watcher_reload_timer = QTimer(self)
        self._watcher_reload_timer.setSingleShot(True)
        self._watcher_reload_timer.timeout.connect(self._reload_presets_from_watcher)

        self._action_mode: Optional[str] = None  # "create" | "rename"
        self._rename_source_name: Optional[str] = None

        self._bulk_reset_running = False
        self._reset_all_confirm_pending = False
        self._reset_all_confirm_timer = QTimer(self)
        self._reset_all_confirm_timer.setSingleShot(True)
        self._reset_all_confirm_timer.timeout.connect(self._clear_reset_all_confirmation)
        self._layout_resync_timer = QTimer(self)
        self._layout_resync_timer.setSingleShot(True)
        self._layout_resync_timer.timeout.connect(self._resync_layout_metrics)
        self._layout_resync_delayed_timer = QTimer(self)
        self._layout_resync_delayed_timer.setSingleShot(True)
        self._layout_resync_delayed_timer.timeout.connect(self._resync_layout_metrics)

        self._build_ui()

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

    def hideEvent(self, event):
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
        # Telegram configs link
        configs_card = SettingsCard()
        configs_card.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        configs_card.setStyleSheet(
            """
            QFrame#settingsCard {
                background-color: rgba(255, 255, 255, 0.03);
                border: none;
                border-radius: 8px;
            }
            QFrame#settingsCard:hover {
                background-color: rgba(255, 255, 255, 0.06);
                border: none;
            }
            """
        )
        configs_layout = QHBoxLayout()
        configs_layout.setSpacing(12)
        configs_icon = QLabel()
        configs_icon.setPixmap(qta.icon("fa5b.telegram", color="#60cdff").pixmap(18, 18))
        configs_layout.addWidget(configs_icon)
        configs_title = QLabel(
            "Обменивайтесь категориями на нашем форуме-сайте через Telegram-бота: безопасно и анонимно"
        )
        configs_title.setStyleSheet("color: rgba(255,255,255,0.85); font-size: 13px; font-weight: 600;")
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

        # Active preset card
        self.active_card = SettingsCard("Активный пресет")
        self.active_card.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.active_card.setStyleSheet(
            """
            QFrame#settingsCard {
                background-color: rgba(255, 255, 255, 0.04);
                border: none;
                border-radius: 8px;
            }
            QFrame#settingsCard:hover {
                background-color: rgba(255, 255, 255, 0.08);
                border: none;
            }
            """
        )
        active_layout = QHBoxLayout()
        active_layout.setSpacing(12)
        self.active_icon_label = QLabel()
        self.active_icon_label.setPixmap(qta.icon("fa5s.star", color=_DEFAULT_PRESET_ICON_COLOR).pixmap(20, 20))
        active_layout.addWidget(self.active_icon_label)
        self.active_preset_label = QLabel("Загрузка...")
        self.active_preset_label.setStyleSheet(
            """
            QLabel {
                color: #ffffff;
                font-size: 14px;
                font-weight: 500;
            }
            """
        )
        active_layout.addWidget(self.active_preset_label)
        active_layout.addStretch(1)
        self.active_card.add_layout(active_layout)
        self.add_widget(self.active_card)

        self.add_spacing(8)

        # "Restore deleted presets" button
        self._restore_deleted_btn = QPushButton("Восстановить удалённые пресеты")
        self._restore_deleted_btn.setIcon(qta.icon("fa5s.undo", color="white"))
        self._restore_deleted_btn.setIconSize(QSize(14, 14))
        self._restore_deleted_btn.setFixedHeight(32)
        self._restore_deleted_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._restore_deleted_btn.setStyleSheet(
            """
            QPushButton {
                background-color: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 8px;
                color: #ffffff;
                padding: 0 16px;
                font-size: 12px;
                font-weight: 600;
                font-family: 'Segoe UI Variable', 'Segoe UI', sans-serif;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.15);
            }
            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 0.22);
            }
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

        self.add_spacing(8)

        # Inline create/rename panel
        self._action_reveal = _RevealFrame(self)
        self._action_reveal.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self._action_reveal_layout = QVBoxLayout(self._action_reveal)
        self._action_reveal_layout.setContentsMargins(0, 0, 0, 0)
        self._action_reveal_layout.setSpacing(0)

        self._action_card = SettingsCard("")
        self._action_card.setStyleSheet(
            """
            QFrame#settingsCard {
                background-color: rgba(255, 255, 255, 0.04);
                border: none;
                border-radius: 8px;
            }
            QFrame#settingsCard:hover {
                background-color: rgba(255, 255, 255, 0.08);
                border: none;
            }
            """
        )
        self._action_card.main_layout.setSpacing(10)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(10)
        self._action_icon = QLabel()
        self._action_icon.setPixmap(qta.icon("fa5s.plus", color="#60cdff").pixmap(18, 18))
        self._action_icon.setFixedSize(22, 22)
        header.addWidget(self._action_icon)
        self._action_title = QLabel("")
        self._action_title.setStyleSheet(
            """
            QLabel {
                color: #ffffff;
                font-size: 14px;
                font-weight: 600;
                font-family: 'Segoe UI Variable', 'Segoe UI', sans-serif;
            }
            """
        )
        header.addWidget(self._action_title)
        header.addStretch(1)
        self._action_close_btn = QPushButton()
        self._action_close_btn.setIcon(qta.icon("fa5s.times", color="#ffffff"))
        self._action_close_btn.setIconSize(QSize(12, 12))
        self._action_close_btn.setFixedSize(28, 28)
        self._action_close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._action_close_btn.setStyleSheet(
            """
            QPushButton {
                background: rgba(255, 255, 255, 0.06);
                border: none;
                border-radius: 6px;
                color: rgba(255, 255, 255, 0.85);
            }
            QPushButton:hover { background: rgba(255, 255, 255, 0.10); }
            QPushButton:pressed { background: rgba(255, 255, 255, 0.14); }
            """
        )
        self._action_close_btn.clicked.connect(self._hide_inline_action)
        header.addWidget(self._action_close_btn)
        self._action_card.add_layout(header)

        self._action_subtitle = QLabel("")
        self._action_subtitle.setStyleSheet(
            """
            QLabel {
                color: rgba(255, 255, 255, 0.6);
                font-size: 12px;
            }
            """
        )
        self._action_subtitle.setWordWrap(True)
        self._action_card.add_widget(self._action_subtitle)

        self._rename_from_label = QLabel("")
        self._rename_from_label.setStyleSheet(
            """
            QLabel {
                color: rgba(255, 255, 255, 0.55);
                font-size: 12px;
            }
            """
        )
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
        self._name_input.setStyleSheet(
            """
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
        source_label.setStyleSheet("color: rgba(255, 255, 255, 0.75); font-size: 12px;")
        source_row.addWidget(source_label)
        source_row.addStretch(1)
        self._create_source = _SegmentedChoice("Текущего активного", "current", "Пустого", "empty", self)
        source_row.addWidget(self._create_source)
        self._action_card.add_widget(self._source_container)

        self._action_error = QLabel("")
        self._action_error.setStyleSheet(
            """
            QLabel {
                color: #ff6b6b;
                font-size: 12px;
            }
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
        self.presets_list.setProperty("noDrag", True)
        self.presets_list.viewport().setProperty("noDrag", True)
        self.presets_list.setStyleSheet(
            """
            QListView#userPresetsList {
                background: transparent;
                border: none;
                outline: none;
            }
            QListView#userPresetsList::item {
                border: none;
            }
            QListView#userPresetsList QScrollBar:vertical {
                background: rgba(255, 255, 255, 0.05);
                width: 12px;
                border-radius: 6px;
                margin: 2px;
            }
            QListView#userPresetsList QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 0.2);
                border-radius: 6px;
                min-height: 28px;
            }
            QListView#userPresetsList QScrollBar::handle:vertical:hover {
                background: rgba(255, 255, 255, 0.3);
            }
            QListView#userPresetsList QScrollBar::add-line:vertical,
            QListView#userPresetsList QScrollBar::sub-line:vertical {
                height: 0;
            }
            """
        )

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

        icon_color = "white"
        btn.setIcon(qta.icon(icon_name, color=icon_color))
        btn.setIconSize(QSize(16, 16))
        btn.setFixedHeight(36)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)

        if accent:
            btn.setStyleSheet(
                """
                QPushButton {
                    background-color: #60cdff;
                    border: 1px solid rgba(255, 255, 255, 0.18);
                    border-radius: 8px;
                    color: #ffffff;
                    padding: 0 20px;
                    font-size: 13px;
                    font-weight: 600;
                    font-family: 'Segoe UI Variable', 'Segoe UI', sans-serif;
                }
                QPushButton:hover {
                    background-color: rgba(96, 205, 255, 0.9);
                }
                QPushButton:pressed {
                    background-color: rgba(96, 205, 255, 0.72);
                }
                """
            )
        else:
            btn.setStyleSheet(
                """
                QPushButton {
                    background-color: rgba(255, 255, 255, 0.08);
                    border: 1px solid rgba(255, 255, 255, 0.12);
                    border-radius: 8px;
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
                    background-color: rgba(255, 255, 255, 0.22);
                }
                """
            )

        return btn

    def _secondary_row_button_style(self) -> str:
        return """
            QPushButton {
                background-color: rgba(255, 255, 255, 0.08);
                border: none;
                border-radius: 4px;
                color: #ffffff;
                padding: 0 16px;
                font-size: 12px;
                font-weight: 600;
                font-family: 'Segoe UI Variable', 'Segoe UI', sans-serif;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.15);
            }
            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 0.22);
            }
        """

    def _create_secondary_row_button(self, text: str, icon_name: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setIcon(qta.icon(icon_name, color="#ffffff"))
        btn.setIconSize(QSize(16, 16))
        btn.setFixedHeight(32)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(self._secondary_row_button_style())
        return btn

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
            self.reset_all_btn.setStyleSheet(
                """
                QPushButton {
                    background-color: rgba(255, 107, 107, 0.95);
                    border: 1px solid rgba(255, 177, 177, 0.5);
                    border-radius: 4px;
                    color: #ffffff;
                    padding: 0 16px;
                    font-size: 12px;
                    font-weight: 700;
                    font-family: 'Segoe UI Variable', 'Segoe UI', sans-serif;
                }
                QPushButton:hover {
                    background-color: rgba(255, 107, 107, 1);
                }
                QPushButton:pressed {
                    background-color: rgba(230, 85, 85, 1);
                }
                """
            )
            return

        self.reset_all_btn.setStyleSheet(self._secondary_row_button_style())

    def _arm_reset_all_confirmation(self):
        self._reset_all_confirm_pending = True
        self.reset_all_btn.setText("Это сбросит ваши настройки")
        self.reset_all_btn.setIcon(qta.icon("fa5s.exclamation-triangle", color="#ffffff"))
        self._apply_reset_all_button_style(True)
        self._reset_all_confirm_timer.start(5000)
        self._update_toolbar_buttons_layout()
        self._schedule_layout_resync()

    def _clear_reset_all_confirmation(self):
        self._reset_all_confirm_pending = False
        self._reset_all_confirm_timer.stop()
        self.reset_all_btn.setText("Сбросить все пресеты")
        self.reset_all_btn.setIcon(qta.icon("fa5s.undo", color="#ffffff"))
        self._apply_reset_all_button_style(False)
        self._update_toolbar_buttons_layout()
        if self.isVisible():
            self._schedule_layout_resync()

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
        self._action_error.hide()
        self._action_error.setText("")
        self._action_reveal.set_open(False)
        self._schedule_layout_resync(include_delayed=True)

    def _set_inline_error(self, text: str):
        self._action_error.setText(text)
        self._action_error.setVisible(bool(text))

    def _show_inline_action_create(self):
        self._action_mode = "create"
        self._rename_source_name = None
        self._set_inline_error("")
        self._action_icon.setPixmap(qta.icon("fa5s.plus", color="#60cdff").pixmap(18, 18))
        self._action_title.setText("Создать новый пресет")
        self._action_subtitle.setText(
            "Сохраните текущие настройки как отдельный пресет, чтобы быстро переключаться между конфигурациями."
        )
        self._rename_from_label.hide()
        self._source_container.show()
        self._create_source.set_value("current", emit=False)
        self._name_input.clear()
        self._name_input.setPlaceholderText("Например: Игры / YouTube / Дом")
        self._action_submit_btn.setText("Создать")
        self._action_submit_btn.setIcon(qta.icon("fa5s.check", color="#ffffff"))
        self._action_reveal.set_open(True)
        self.ensureWidgetVisible(self._action_reveal)
        self._name_input.setFocus()
        self._schedule_layout_resync(include_delayed=True)

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
        self._action_submit_btn.setIcon(qta.icon("fa5s.check", color="#ffffff"))
        self._action_reveal.set_open(True)
        self.ensureWidgetVisible(self._action_reveal)
        self._name_input.setFocus()
        self._schedule_layout_resync(include_delayed=True)

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

    def _on_create_clicked(self):
        if self._action_mode == "create" and self._action_reveal.isVisible():
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

        try:
            manager = self._get_manager()
            preset_names = manager.list_presets()
            if not preset_names:
                QMessageBox.information(self, "Сброс пресетов", "Нет пресетов для сброса.")
                return

            original_active = manager.get_active_preset_name()
            ordered_names = sorted(preset_names, key=lambda s: s.lower())
            if original_active and original_active in ordered_names:
                ordered_names = [n for n in ordered_names if n != original_active] + [original_active]

            success_count = 0
            failed: list[str] = []

            self._bulk_reset_running = True
            try:
                for name in ordered_names:
                    if manager.reset_preset_to_default_template(name):
                        success_count += 1
                    else:
                        failed.append(name)
            finally:
                self._bulk_reset_running = False

            final_active = manager.get_active_preset_name() or (original_active or "")
            if final_active:
                self.preset_switched.emit(final_active)

            self._load_presets()

            if failed:
                log(f"Сброс пресетов завершён частично: успешно={success_count}, ошибки={len(failed)}", "WARNING")
                QMessageBox.warning(
                    self,
                    "Сброс пресетов",
                    f"Сброшено: {success_count}\nНе удалось: {len(failed)}",
                )
                return

            log(f"Сброшены все пресеты к шаблонам: {success_count}", "INFO")
            QMessageBox.information(self, "Сброс пресетов", f"Сброшено пресетов: {success_count}")

        except Exception as e:
            self._bulk_reset_running = False
            log(f"Ошибка массового сброса пресетов: {e}", "ERROR")
            QMessageBox.critical(self, "Ошибка", f"Ошибка сброса пресетов: {e}")

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

            self.active_preset_label.setText(active_name or "Не выбран")
            active_preset = all_presets.get(active_name) if active_name else None
            active_icon_color = _normalize_preset_icon_color(getattr(active_preset, "icon_color", None))
            self.active_icon_label.setPixmap(qta.icon("fa5s.star", color=active_icon_color).pixmap(20, 20))

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
                if rows:
                    rows.append({"kind": "section", "text": "Пресеты которые позволяют играть в игры (Game filter для UDP портов от 444 до 65535)"})
                for name in game_filter_names:
                    add_preset_row(name)

            if all_tcp_names:
                rows.append(
                    {
                        "kind": "section",
                        "text": "Хотите чтобы Zapret работал на все сайты? Вам сюда! (ALL TCP & UDP по всем портам!)",
                    }
                )
                for name in all_tcp_names:
                    add_preset_row(name)

            if not rows:
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
        if self._action_mode == "rename" and self._rename_source_name == name and self._action_reveal.isVisible():
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
