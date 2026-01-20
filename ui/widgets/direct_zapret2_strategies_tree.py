from __future__ import annotations

from dataclasses import dataclass
import re
import time
from typing import Dict, Iterable, Optional, Set

from PyQt6.QtCore import QEvent, Qt, pyqtSignal, QSize, QTimer, QPoint, QRect
from PyQt6.QtGui import QBrush, QColor, QFont, QPen, QIcon, QPainter, QPainterPath, QPixmap, QCursor
from PyQt6.QtWidgets import (
    QApplication,
    QAbstractScrollArea,
    QDialog,
    QHBoxLayout,
    QPushButton,
    QPlainTextEdit,
    QScrollArea,
    QStyle,
    QStyleOptionViewItem,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
)


@dataclass(frozen=True)
class StrategyTreeRow:
    strategy_id: str
    name: str
    args: list[str]
    is_favorite: bool = False
    is_working: Optional[bool] = None


class DirectZapret2StrategiesTree(QTreeWidget):
    """
    Лёгкий список стратегий на базе QTreeWidget (без множества QWidget-строк).

    Две секции:
    - ★ Избранные
    - Все стратегии

    Columns:
      0: star
      1: name
    """

    strategy_clicked = pyqtSignal(str)
    favorite_toggled = pyqtSignal(str, bool)
    working_mark_requested = pyqtSignal(str, object)  # bool|None
    preview_requested = pyqtSignal(str, object)  # strategy_id, global_pos(QPoint)
    preview_pinned_requested = pyqtSignal(str, object)  # strategy_id, global_pos(QPoint)
    preview_hide_requested = pyqtSignal()

    _ROLE_STRATEGY_ID = int(Qt.ItemDataRole.UserRole) + 1
    _ROLE_ARGS_TEXT = int(Qt.ItemDataRole.UserRole) + 2
    _ROLE_ARGS_FULL = int(Qt.ItemDataRole.UserRole) + 6
    _ROLE_IS_FAVORITE = int(Qt.ItemDataRole.UserRole) + 3
    _ROLE_IS_WORKING = int(Qt.ItemDataRole.UserRole) + 4
    _ROLE_INSERT_INDEX = int(Qt.ItemDataRole.UserRole) + 5

    def __init__(self, parent=None):
        super().__init__(parent)
        self._hover_delay_ms = 180
        self.setColumnCount(2)
        self.setHeaderHidden(True)
        self.setRootIsDecorated(False)
        self.setIndentation(0)
        self.setUniformRowHeights(True)
        self.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.setSelectionMode(QTreeWidget.SelectionMode.SingleSelection)
        self.setSelectionBehavior(QTreeWidget.SelectionBehavior.SelectRows)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.DefaultContextMenu)
        self.setMouseTracking(True)
        self.setIconSize(QSize(14, 14))

        # Use internal scrolling (more reliable than growing-by-height inside BasePage/QScrollArea).
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        from PyQt6.QtWidgets import QSizePolicy
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        # Avoid a huge sizeHint based on all rows; we want a stable viewport + internal scrollbar.
        self.setSizeAdjustPolicy(QAbstractScrollArea.SizeAdjustPolicy.AdjustIgnored)
        # Larger viewport: strategy lists are long, so give the tree more room by default.
        self.setMinimumHeight(1000)

        header = self.header()
        header.setSectionResizeMode(0, header.ResizeMode.Fixed)
        header.setSectionResizeMode(1, header.ResizeMode.Stretch)
        self._star_col_w = 45
        self.setColumnWidth(0, self._star_col_w)

        self._row_height = 28
        self._section_height = 26

        self.setStyleSheet("""
            QTreeWidget {
                background: rgba(255, 255, 255, 0.02);
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 8px;
                padding: 6px;
                outline: none;
            }
            QTreeWidget::item {
                padding: 4px 8px;
                min-height: 28px;
                color: rgba(255, 255, 255, 0.9);
                border-radius: 6px;
            }
            /* Selection/marks are painted in drawRow() to avoid theme/QSS conflicts. */
        """)

        self._mono_font = QFont("Consolas", 9)
        self._name_font = QFont("Segoe UI", 10)
        self._section_font = QFont("Segoe UI", 10)
        self._section_font.setBold(True)

        self._rows: Dict[str, QTreeWidgetItem] = {}
        self._sort_mode = "default"  # default, name_asc, name_desc
        self._insert_counter = 0
        self._active_strategy_id: str = "none"
        self._tech_icon_cache: Dict[str, QIcon] = {}

        self._hover_timer = QTimer(self)
        self._hover_timer.setSingleShot(True)
        self._hover_timer.timeout.connect(self._emit_hover_preview)
        self._hover_strategy_id: Optional[str] = None
        self._hover_global_pos: Optional[QPoint] = None
        self._hover_delay_ms = 180
        self._hover_emit_last_ts = 0.0
        self._hover_emit_throttle_s = 0.06  # avoid flooding updates while fast scrolling

        self._geom_timer = QTimer(self)
        self._geom_timer.setSingleShot(True)
        self._geom_timer.timeout.connect(self._propagate_geometry_change)

        self._fav_root = self._add_section("★ Избранные")
        self._all_root = self._add_section("Все стратегии")

        self.itemClicked.connect(self._on_item_clicked)

    def _sync_hover_from_cursor(self, *, immediate: bool) -> None:
        """
        Keep hover preview in sync even when the list scrolls under a stationary cursor.

        Qt often won't emit MouseMove when users scroll with the wheel/scrollbar,
        so we re-check what's under the cursor after scroll changes.
        """
        try:
            gp = QCursor.pos()
            vp_pos = self.viewport().mapFromGlobal(gp)
        except Exception:
            return

        # When RMB preview is open, disable all hover previews.
        try:
            app = QApplication.instance()
            if app and bool(app.property("zapretgui_args_preview_open")):
                self._cancel_hover_preview()
                return
        except Exception:
            pass

        # Show hover preview ONLY when cursor is actually over our viewport.
        try:
            w = QApplication.widgetAt(gp)
            if (w is None) or (w is not self.viewport() and (not self.viewport().isAncestorOf(w))):
                self._cancel_hover_preview()
                return
        except Exception:
            pass

        try:
            if not self.viewport().rect().contains(vp_pos):
                self._cancel_hover_preview()
                return
        except Exception:
            pass

        item = self.itemAt(vp_pos)
        sid = None
        if item:
            sid = item.data(0, self._ROLE_STRATEGY_ID)
        sid = str(sid) if sid else None

        if not sid or sid == "none":
            self._cancel_hover_preview()
            return

        # Update hover target + position
        changed = (sid != self._hover_strategy_id)
        self._hover_strategy_id = sid
        self._hover_global_pos = gp

        if immediate:
            # Immediate refresh when scrolling: show correct strategy without waiting.
            now = time.monotonic()
            if changed or (now - self._hover_emit_last_ts) >= self._hover_emit_throttle_s:
                self._hover_emit_last_ts = now
                try:
                    self.preview_requested.emit(sid, gp)
                except Exception:
                    pass
            else:
                # Too frequent: schedule a delayed emit.
                self._hover_timer.start(self._hover_delay_ms)
        else:
            if changed:
                self._hover_timer.start(self._hover_delay_ms)

    def drawRow(self, painter, options: QStyleOptionViewItem, index) -> None:  # noqa: N802 (Qt override)
        """
        Paint selection and working/broken tint manually.

        This avoids conflicts with global app QSS (theme) which can override
        `QTreeWidget::item:selected` and per-item BackgroundRole brushes.
        """
        item = self.itemFromIndex(index)
        if not item or item.flags() == Qt.ItemFlag.NoItemFlags:
            return super().drawRow(painter, options, index)

        sid = item.data(0, self._ROLE_STRATEGY_ID)
        sid = str(sid) if sid else ""
        is_active = bool(sid) and sid == (self._active_strategy_id or "none")
        is_hover = bool(options.state & QStyle.StateFlag.State_MouseOver)
        is_working = item.data(0, self._ROLE_IS_WORKING)
        if is_working not in (True, False, None):
            is_working = None

        r = options.rect.adjusted(4, 2, -4, -2)

        # Base tint (working/broken)
        base_bg = None
        if is_working is True:
            base_bg = QColor(74, 222, 128, 64)   # light green
        elif is_working is False:
            base_bg = QColor(248, 113, 113, 64)  # light red

        # Hover tint (only if not selected)
        hover_bg = QColor(255, 255, 255, 18) if is_hover and not is_active else None

        painter.save()
        painter.setRenderHint(painter.RenderHint.Antialiasing, True)

        if base_bg is not None:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(base_bg))
            painter.drawRoundedRect(r, 6, 6)

        if hover_bg is not None:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(hover_bg))
            painter.drawRoundedRect(r, 6, 6)

        if is_active:
            # Ensure active selection is always visible, even on top of working/broken tint.
            sel_bg = QColor(96, 205, 255, 34)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(sel_bg))
            painter.drawRoundedRect(r, 6, 6)

            pen = QPen(QColor(96, 205, 255, 140))
            pen.setWidth(1)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(r, 6, 6)

            # Left accent bar
            bar = r.adjusted(0, 2, -(r.width() - 2), -2)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(96, 205, 255, 220)))
            painter.drawRoundedRect(bar, 2, 2)

        painter.restore()

        # Draw text/icons without letting the style paint its own selection background.
        opt = QStyleOptionViewItem(options)
        opt.state &= ~QStyle.StateFlag.State_Selected
        opt.state &= ~QStyle.StateFlag.State_MouseOver
        return super().drawRow(painter, opt, index)

    def _add_section(self, title: str) -> QTreeWidgetItem:
        root = QTreeWidgetItem(self)
        root.setFirstColumnSpanned(True)
        root.setText(0, title)
        root.setFont(0, self._section_font)
        root.setForeground(0, QBrush(QColor(255, 255, 255, 170)))
        root.setFlags(Qt.ItemFlag.NoItemFlags)
        root.setExpanded(True)
        root.setHidden(True)
        root.setSizeHint(0, QSize(0, self._section_height))
        return root

    def clear_strategies(self) -> None:
        self._rows.clear()
        self._fav_root.takeChildren()
        self._all_root.takeChildren()
        self._fav_root.setHidden(True)
        self._all_root.setHidden(True)
        self._insert_counter = 0
        self._active_strategy_id = "none"
        self._update_height_to_contents()

    def has_rows(self) -> bool:
        return bool(self._rows)

    def has_strategy(self, strategy_id: str) -> bool:
        return (strategy_id or "") in self._rows

    def get_strategy_item_rect(self, strategy_id: str) -> Optional[QRect]:
        item = self._rows.get(strategy_id or "")
        if not item:
            return None
        try:
            return self.visualItemRect(item)
        except Exception:
            return None

    def is_strategy_visible(self, strategy_id: str) -> bool:
        item = self._rows.get(strategy_id or "")
        if not item:
            return False
        return not bool(item.isHidden())

    def set_sort_mode(self, mode: str) -> None:
        if mode in ("default", "name_asc", "name_desc"):
            self._sort_mode = mode

    def _args_preview_text(self, args: list[str]) -> str:
        # kept for compatibility (search/filter); not shown in UI
        if not args:
            return ""
        parts = [str(a).strip() for a in args if str(a).strip()]
        return " ".join(parts)

    @staticmethod
    def _map_desync_value_to_technique(val: str) -> Optional[str]:
        v = (val or "").strip().lower()
        if not v:
            return None
        if "syndata" in v:
            return "syndata"
        if "oob" in v:
            return "oob"
        if "disorder" in v:
            return "disorder"
        if "multisplit" in v:
            return "multisplit"
        if "split" in v:
            return "split"
        if "fake" in v or "hostfakesplit" in v:
            return "fake"
        return None

    @classmethod
    def _infer_techniques(cls, strategy_id: str, args_text_lower: str) -> list[str]:
        """
        Best-effort detect techniques for an icon.

        If there are multiple `--lua-desync/--dpi-desync` entries, we return multiple
        techniques in order; the icon can be split diagonally into two colors.
        """
        sid = (strategy_id or "").lower()
        txt = (args_text_lower or "")

        # Primary source: explicit desync values (can be multiple)
        out: list[str] = []
        for val in re.findall(r"--(?:lua-desync|dpi-desync)=([a-z0-9_-]+)", txt):
            tech = cls._map_desync_value_to_technique(val)
            if tech and tech not in out:
                out.append(tech)
        if out:
            return out

        # Fallback by substring (order matters: multisplit before split)
        hay = f"{sid} {txt}"
        fallback = []
        for tech in ("syndata", "oob", "disorder", "multisplit", "split", "fake"):
            if tech in hay:
                fallback.append(tech)
                break
        return fallback

    @staticmethod
    def _compose_diagonal_pixmap(pix_a: QPixmap, pix_b: QPixmap) -> QPixmap:
        w = max(1, pix_a.width())
        h = max(1, pix_a.height())
        out = QPixmap(w, h)
        out.fill(Qt.GlobalColor.transparent)

        p = QPainter(out)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        # Split by diagonal (top-left -> bottom-right)
        path_a = QPainterPath()
        path_a.moveTo(0, 0)
        path_a.lineTo(w, 0)
        path_a.lineTo(0, h)
        path_a.closeSubpath()

        path_b = QPainterPath()
        path_b.moveTo(w, 0)
        path_b.lineTo(w, h)
        path_b.lineTo(0, h)
        path_b.closeSubpath()

        p.save()
        p.setClipPath(path_a)
        p.drawPixmap(0, 0, pix_a)
        p.restore()

        p.save()
        p.setClipPath(path_b)
        p.drawPixmap(0, 0, pix_b)
        p.restore()

        p.end()
        return out

    @staticmethod
    def _fixed_icon_from_pixmap(pix: QPixmap) -> QIcon:
        """
        Freeze icon colors across view states.

        Some Qt styles auto-generate Disabled/Selected pixmaps by tinting/grayscaling.
        To keep our pastel colors, we provide the same pixmap for all modes.
        """
        icon = QIcon()
        for mode in (QIcon.Mode.Normal, QIcon.Mode.Disabled, QIcon.Mode.Active, QIcon.Mode.Selected):
            icon.addPixmap(pix, mode, QIcon.State.Off)
            icon.addPixmap(pix, mode, QIcon.State.On)
        return icon

    def _get_tech_icon(self, techniques: list[str]) -> Optional[QIcon]:
        if not techniques:
            return None
        key = "+".join(techniques[:2])
        if key in self._tech_icon_cache:
            return self._tech_icon_cache[key]

        # Lazy import to avoid hard dependency during early app startup.
        try:
            import qtawesome as qta  # type: ignore
        except Exception:
            return None

        # Minimalistic icons + pastel palette (no emoji).
        # Colors per request:
        # - fake: red
        # - multisplit: blue
        # - (multi)disorder: green
        mapping = {
            "fake": ("fa5s.magic", "#f87171"),
            "split": ("fa5s.cut", "#fbbf24"),
            "multisplit": ("fa5s.stream", "#60cdff"),
            "disorder": ("fa5s.random", "#4ade80"),
            "oob": ("fa5s.external-link-alt", "#f472b6"),
            "syndata": ("fa5s.database", "#94a3b8"),
        }

        primary = techniques[0]
        icon_name, color_a = mapping.get(primary, (None, None))
        if not icon_name or not color_a:
            return None

        try:
            if len(techniques) >= 2 and techniques[1] != primary:
                secondary = techniques[1]
                _, color_b = mapping.get(secondary, (icon_name, color_a))
                base_a = qta.icon(icon_name, color=color_a).pixmap(self.iconSize())
                base_b = qta.icon(icon_name, color=color_b).pixmap(self.iconSize())
                pix = self._compose_diagonal_pixmap(base_a, base_b)
                icon = self._fixed_icon_from_pixmap(pix)
            else:
                pix = qta.icon(icon_name, color=color_a).pixmap(self.iconSize())
                icon = self._fixed_icon_from_pixmap(pix)
        except Exception:
            return None

        self._tech_icon_cache[key] = icon
        return icon

    def add_strategy(self, row: StrategyTreeRow) -> None:
        parent = self._fav_root if row.is_favorite else self._all_root
        item = QTreeWidgetItem(parent)

        item.setData(0, self._ROLE_STRATEGY_ID, row.strategy_id)
        args_joined = self._args_preview_text(row.args)
        item.setData(0, self._ROLE_ARGS_TEXT, args_joined.lower())
        item.setData(0, self._ROLE_ARGS_FULL, "\n".join(row.args))
        item.setData(0, self._ROLE_IS_FAVORITE, bool(row.is_favorite))
        item.setData(0, self._ROLE_IS_WORKING, row.is_working)
        item.setData(0, self._ROLE_INSERT_INDEX, self._insert_counter)
        self._insert_counter += 1

        item.setText(1, row.name)
        item.setFont(1, self._name_font)
        item.setToolTip(1, "Наведение — показать args")
        if row.strategy_id != "none":
            techniques = self._infer_techniques(row.strategy_id, args_joined.lower())
            icon = self._get_tech_icon(techniques[:2])
            if icon:
                item.setIcon(1, icon)

        self._apply_star(item, row.is_favorite, allow=(row.strategy_id != "none"))
        self._apply_working_style(item, row.is_working)
        item.setSizeHint(0, QSize(0, self._row_height))
        item.setSizeHint(1, QSize(0, self._row_height))

        self._rows[row.strategy_id] = item
        self._refresh_sections_visibility()
        self._update_height_to_contents()

    def set_selected_strategy(self, strategy_id: str) -> None:
        self._active_strategy_id = strategy_id or "none"
        item = self._rows.get(self._active_strategy_id)
        if item:
            self.clearSelection()
            self.setCurrentItem(item)
            item.setSelected(True)
        self.viewport().update()

    def get_strategy_ids(self) -> list[str]:
        return list(self._rows.keys())

    def set_working_state(self, strategy_id: str, is_working: Optional[bool]) -> None:
        item = self._rows.get(strategy_id)
        if not item:
            return
        item.setData(0, self._ROLE_IS_WORKING, is_working)
        self._apply_working_style(item, is_working)
        # Ensure repaint even if global QSS overrides item roles.
        self.viewport().update()

    def set_favorite_state(self, strategy_id: str, is_favorite: bool) -> None:
        item = self._rows.get(strategy_id)
        if not item:
            return
        if strategy_id == "none":
            is_favorite = False
        if bool(item.data(0, self._ROLE_IS_FAVORITE)) == bool(is_favorite):
            return

        item.setData(0, self._ROLE_IS_FAVORITE, bool(is_favorite))
        self._apply_star(item, bool(is_favorite), allow=(strategy_id != "none"))

        was_selected = bool(item.isSelected())

        # Move between sections
        src_parent = item.parent()
        dst_parent = self._fav_root if is_favorite else self._all_root
        if src_parent is not None and src_parent is not dst_parent:
            idx = src_parent.indexOfChild(item)
            moved = src_parent.takeChild(idx)
            self._insert_sorted(dst_parent, moved)

        self._refresh_sections_visibility()
        self._update_height_to_contents()
        if was_selected:
            self.set_selected_strategy(strategy_id)

    def apply_filter(self, search_text: str, techniques: Set[str]) -> None:
        search = (search_text or "").strip().lower()
        tech = {t.strip().lower() for t in (techniques or set()) if t and t.strip()}

        selected_id = self._active_strategy_id or self._get_selected_strategy_id()
        for sid, item in self._rows.items():
            visible = True
            args_text = str(item.data(0, self._ROLE_ARGS_TEXT) or "")
            if search:
                visible = (search in args_text) or (search in (item.text(1) or "").lower())
            if visible and tech:
                visible = any(t in args_text for t in tech)
            item.setHidden(not visible)

        self._refresh_sections_visibility()
        self._update_height_to_contents()
        if selected_id and self.has_strategy(selected_id) and not self._rows[selected_id].isHidden():
            self.set_selected_strategy(selected_id)

    def apply_sort(self) -> None:
        selected_id = self._active_strategy_id or self._get_selected_strategy_id()
        self._sort_section(self._fav_root)
        self._sort_section(self._all_root)
        self._update_height_to_contents()
        if selected_id:
            self.set_selected_strategy(selected_id)

    def _sort_section(self, root: QTreeWidgetItem) -> None:
        children = [root.child(i) for i in range(root.childCount())]
        if not children:
            return

        if self._sort_mode == "name_asc":
            children.sort(key=lambda it: (it.text(1) or "").lower())
        elif self._sort_mode == "name_desc":
            children.sort(key=lambda it: (it.text(1) or "").lower(), reverse=True)
        else:
            children.sort(key=lambda it: int(it.data(0, self._ROLE_INSERT_INDEX) or 0))

        root.takeChildren()
        for child in children:
            root.addChild(child)

    def _insert_sorted(self, root: QTreeWidgetItem, item: QTreeWidgetItem) -> None:
        if self._sort_mode == "name_asc":
            key = (item.text(1) or "").lower()
            for i in range(root.childCount()):
                if key < (root.child(i).text(1) or "").lower():
                    root.insertChild(i, item)
                    return
        elif self._sort_mode == "name_desc":
            key = (item.text(1) or "").lower()
            for i in range(root.childCount()):
                if key > (root.child(i).text(1) or "").lower():
                    root.insertChild(i, item)
                    return
        else:
            idx = int(item.data(0, self._ROLE_INSERT_INDEX) or 0)
            for i in range(root.childCount()):
                other = root.child(i)
                other_idx = int(other.data(0, self._ROLE_INSERT_INDEX) or 0)
                if idx < other_idx:
                    root.insertChild(i, item)
                    return
        root.addChild(item)

    def _refresh_sections_visibility(self) -> None:
        fav_visible = any(not self._fav_root.child(i).isHidden() for i in range(self._fav_root.childCount()))
        all_visible = any(not self._all_root.child(i).isHidden() for i in range(self._all_root.childCount()))
        self._fav_root.setHidden(not fav_visible)
        self._all_root.setHidden(not all_visible)

        self.expandItem(self._fav_root)
        self.expandItem(self._all_root)

    def _update_height_to_contents(self) -> None:
        # Internal scrollbar mode: keep a stable viewport height.
        # Still request a layout/paint update after bulk changes.
        try:
            self.updateGeometry()
            self.viewport().update()
        except Exception:
            pass

    def _schedule_geometry_update(self) -> None:
        # Coalesce multiple updates during batch loads (e.g. lazy strategy load).
        if self._geom_timer.isActive():
            return
        self._geom_timer.start(0)

    def _propagate_geometry_change(self) -> None:
        try:
            self.updateGeometry()
        except Exception:
            pass

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.setColumnWidth(0, self._star_col_w)

    def wheelEvent(self, event) -> None:  # noqa: N802 (Qt override)
        """
        Always consume wheel events so the parent page (QScrollArea/BasePage)
        does not scroll when the cursor is over the strategies list.
        """
        super().wheelEvent(event)
        # QAbstractItemView may scroll contents without moving the cursor,
        # so update hover target right away.
        try:
            self._sync_hover_from_cursor(immediate=True)
        except Exception:
            pass
        try:
            event.accept()
        except Exception:
            pass

    def scrollContentsBy(self, dx: int, dy: int) -> None:  # noqa: N802 (Qt override)
        super().scrollContentsBy(dx, dy)
        try:
            if dx or dy:
                self._sync_hover_from_cursor(immediate=True)
        except Exception:
            pass

    def _apply_star(self, item: QTreeWidgetItem, is_favorite: bool, allow: bool) -> None:
        if not allow:
            item.setText(0, "")
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            return
        item.setText(0, "★" if is_favorite else "☆")
        item.setTextAlignment(0, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        item.setForeground(0, QBrush(QColor(255, 193, 7, 255 if is_favorite else 80)))

    def _apply_working_style(self, item: QTreeWidgetItem, is_working: Optional[bool]) -> None:
        # We keep the state in a data role and paint in drawRow().
        # Also, clear any previously set background to avoid theme/QSS conflicts.
        item.setData(0, self._ROLE_IS_WORKING, is_working if is_working in (True, False) else None)
        for col in range(2):
            item.setData(col, Qt.ItemDataRole.BackgroundRole, None)

    def _get_selected_strategy_id(self) -> Optional[str]:
        item = self.currentItem()
        if not item:
            sel = self.selectedItems()
            item = sel[0] if sel else None
        if not item:
            return None
        sid = item.data(0, self._ROLE_STRATEGY_ID)
        return str(sid) if sid else None

    def _on_item_clicked(self, item: QTreeWidgetItem, column: int):
        strategy_id = item.data(0, self._ROLE_STRATEGY_ID)
        if not strategy_id:
            return

        if column == 0:
            if strategy_id == "none":
                return
            new_state = not bool(item.data(0, self._ROLE_IS_FAVORITE))
            # UI сразу обновляем, persistence пусть делает владелец
            self.set_favorite_state(strategy_id, new_state)
            self.favorite_toggled.emit(strategy_id, new_state)
            return

        # Click should immediately sync the preview to the clicked strategy.
        # This avoids "stale" hover previews when users scroll/click quickly.
        try:
            self._hover_timer.stop()
        except Exception:
            pass
        try:
            sid = str(strategy_id)
            gp = QCursor.pos()
            self._hover_strategy_id = sid
            self._hover_global_pos = gp
            self._hover_emit_last_ts = time.monotonic()
            self.preview_requested.emit(sid, gp)
        except Exception:
            pass

        self.strategy_clicked.emit(strategy_id)

    def viewportEvent(self, event):
        et = event.type()
        if et == QEvent.Type.Wheel:
            handled = super().viewportEvent(event)
            try:
                event.accept()
            except Exception:
                pass
            return True
        if et in (QEvent.Type.MouseMove, QEvent.Type.HoverMove):
            # When RMB preview is open, disable all hover previews to avoid conflicts.
            try:
                app = QApplication.instance()
                if app and bool(app.property("zapretgui_args_preview_open")):
                    self._cancel_hover_preview()
                    return super().viewportEvent(event)
            except Exception:
                pass
            # Use cursor-based sync to keep behavior consistent with scroll updates.
            try:
                self._sync_hover_from_cursor(immediate=False)
            except Exception:
                pass
            return super().viewportEvent(event)

        if et in (QEvent.Type.Leave, QEvent.Type.HoverLeave):
            self._cancel_hover_preview()
            return super().viewportEvent(event)

        return super().viewportEvent(event)

    def _cancel_hover_preview(self) -> None:
        had = bool(self._hover_strategy_id)
        self._hover_timer.stop()
        self._hover_strategy_id = None
        self._hover_global_pos = None
        if had:
            try:
                self.preview_hide_requested.emit()
            except Exception:
                pass

    def _emit_hover_preview(self) -> None:
        sid = self._hover_strategy_id
        if not sid:
            return

        # When RMB preview is open, disable all hover previews.
        try:
            app = QApplication.instance()
            if app and bool(app.property("zapretgui_args_preview_open")):
                self._cancel_hover_preview()
                return
        except Exception:
            pass

        # Validate that the cursor is still over the same item.
        try:
            gp = QCursor.pos()
            # Only show while cursor is inside the strategies list viewport.
            w = QApplication.widgetAt(gp)
            if (w is None) or (w is not self.viewport() and (not self.viewport().isAncestorOf(w))):
                self._cancel_hover_preview()
                return
            vp_pos = self.viewport().mapFromGlobal(gp)
            if not self.viewport().rect().contains(vp_pos):
                self._cancel_hover_preview()
                return
            item = self.itemAt(vp_pos)
            current = item.data(0, self._ROLE_STRATEGY_ID) if item else None
            current = str(current) if current else None
            if current and current != sid:
                self._sync_hover_from_cursor(immediate=False)
                return
        except Exception:
            pass

        item = self._rows.get(sid)
        if not item or item.isHidden():
            return
        pos = self._hover_global_pos or self.mapToGlobal(self.rect().center())
        try:
            self.preview_requested.emit(sid, pos)
        except Exception:
            pass

    def _show_args_dialog(self, item: QTreeWidgetItem) -> None:
        full = str(item.data(0, self._ROLE_ARGS_FULL) or "").strip()
        if not full:
            return

        dlg = QDialog(self)
        dlg.setWindowTitle("Аргументы стратегии")
        dlg.setModal(True)
        dlg.setStyleSheet("""
            QDialog { background: #2a2a2a; }
            QPushButton {
                background: rgba(255, 255, 255, 0.06);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 6px;
                color: rgba(255,255,255,0.8);
                padding: 6px 12px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover { background: rgba(255, 255, 255, 0.1); }
        """)

        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        edit = QPlainTextEdit()
        edit.setReadOnly(True)
        edit.setPlainText(full)
        edit.setStyleSheet("""
            QPlainTextEdit {
                background: rgba(0,0,0,0.25);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 8px;
                color: rgba(255,255,255,0.8);
                font-family: 'Consolas', monospace;
                font-size: 10px;
                padding: 10px;
            }
        """)
        edit.setMinimumHeight(200)
        layout.addWidget(edit, 1)

        btns = QHBoxLayout()
        btns.addStretch()

        copy_btn = QPushButton("Копировать")
        copy_btn.clicked.connect(lambda: QApplication.clipboard().setText(full))
        btns.addWidget(copy_btn)

        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(dlg.accept)
        btns.addWidget(close_btn)

        layout.addLayout(btns)
        dlg.resize(640, 360)
        dlg.exec()

    def contextMenuEvent(self, event):
        # If RMB preview is already open, first RMB closes it (consumed globally),
        # so do not open another preview on the same click.
        try:
            app = QApplication.instance()
            if app and bool(app.property("zapretgui_args_preview_open")):
                return
        except Exception:
            pass
        self._cancel_hover_preview()
        item = self.itemAt(event.pos())
        if not item:
            return
        strategy_id = item.data(0, self._ROLE_STRATEGY_ID)
        if not strategy_id or strategy_id == "none":
            return

        # ПКМ: показать интерактивное окно (как в direct_zapret1), а не контекстное меню.
        self.preview_pinned_requested.emit(str(strategy_id), event.globalPos())

    def hideEvent(self, event):  # noqa: N802 (Qt override)
        # When the page/window is hidden, ensure we never show a delayed hover preview.
        try:
            self._cancel_hover_preview()
        except Exception:
            pass
        return super().hideEvent(event)
