# ui/pages/zapret1/direct_zapret1_page.py
"""Страница выбора стратегий для режима direct_zapret1 (preset-based)."""

from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QSize
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QFrame, QSizePolicy,
)
import qtawesome as qta

from ui.pages.base_page import BasePage
from ui.compat_widgets import SettingsCard, ActionButton, RefreshButton
from ui.widgets import UnifiedStrategiesList
from ui.theme import get_theme_tokens
from strategy_menu.strategies_registry import registry
from log import log

try:
    from qfluentwidgets import (
        CaptionLabel, BodyLabel, PushButton, TransparentPushButton, BreadcrumbBar,
    )
    _HAS_FLUENT_LABELS = True
except ImportError:
    from PyQt6.QtWidgets import QLabel as BodyLabel, QLabel as CaptionLabel, QPushButton as PushButton  # type: ignore
    TransparentPushButton = PushButton  # type: ignore
    BreadcrumbBar = None  # type: ignore
    _HAS_FLUENT_LABELS = False


class Zapret1StrategiesPage(BasePage):
    """
    Страница выбора стратегий для direct_zapret1 с единым списком категорий.
    """

    strategy_selected = pyqtSignal(str, str)  # category_key, strategy_id
    strategies_changed = pyqtSignal(dict)
    back_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(
            title="Стратегии Zapret 1",
            parent=parent,
        )
        self.parent_app = parent

        # Breadcrumb / back navigation
        self._breadcrumb = None
        try:
            if BreadcrumbBar is not None:
                self._breadcrumb = BreadcrumbBar()
                self._breadcrumb.addItem("zapret1_control", "Управление")
                self._breadcrumb.addItem("zapret1_strategies", "Стратегии")
                self._breadcrumb.currentItemChanged.connect(self._on_breadcrumb_item_changed)
                self.layout.insertWidget(0, self._breadcrumb)
        except Exception:
            self._breadcrumb = None
            try:
                from PyQt6.QtWidgets import QHBoxLayout as _QHB, QWidget as _QW
                _tokens = get_theme_tokens()
                _back_btn = TransparentPushButton()
                _back_btn.setText("Управление")
                _back_btn.setIcon(qta.icon("fa5s.chevron-left", color=_tokens.fg_muted))
                _back_btn.setIconSize(QSize(12, 12))
                _back_btn.clicked.connect(self.back_clicked.emit)
                _back_layout = _QHB()
                _back_layout.setContentsMargins(0, 0, 0, 0)
                _back_layout.setSpacing(0)
                _back_layout.addWidget(_back_btn)
                _back_layout.addStretch()
                _back_widget = _QW()
                _back_widget.setLayout(_back_layout)
                self.layout.insertWidget(0, _back_widget)
            except Exception:
                pass

        self.category_selections = {}
        self._unified_list = None
        self._built = False
        self._build_scheduled = False
        self._strategy_set_snapshot = None

    def _on_breadcrumb_item_changed(self, index) -> None:
        try:
            route_key = getattr(index, 'routeKey', lambda: None)()
            if not route_key:
                route_key = str(index)
            if "control" in str(route_key).lower():
                self.back_clicked.emit()
        except Exception:
            pass

    def showEvent(self, a0):
        super().showEvent(a0)
        try:
            from strategy_menu.strategies_registry import get_current_strategy_set
            snapshot = get_current_strategy_set()
        except Exception:
            snapshot = None

        if not self._built or snapshot != self._strategy_set_snapshot:
            self._strategy_set_snapshot = snapshot
            self._schedule_build()

    def _schedule_build(self):
        if self._build_scheduled:
            return
        self._build_scheduled = True
        QTimer.singleShot(0, self._build_content)

    def _build_content(self):
        self._build_scheduled = False
        try:
            self._do_build()
        except Exception as e:
            log(f"Error building Zapret1StrategiesPage: {e}", "ERROR")
        self._built = True

    def _do_build(self):
        # Clear existing unified list if any
        if self._unified_list is not None:
            try:
                self._unified_list.setParent(None)
            except Exception:
                pass
            self._unified_list = None

        # Clear any old content in the page's vBoxLayout beyond the header widgets.
        # BasePage.add_widget appends to self.vBoxLayout (alias: self.layout).
        # We keep title_label, subtitle_label and any back/breadcrumb widget
        # inserted at index 0, and remove everything else.
        layout = self.vBoxLayout
        keep_widgets = set()
        if getattr(self, "title_label", None) is not None:
            keep_widgets.add(self.title_label)
        if getattr(self, "subtitle_label", None) is not None:
            keep_widgets.add(self.subtitle_label)
        if self._breadcrumb is not None:
            keep_widgets.add(self._breadcrumb)

        # Collect indices to remove (iterate backwards to avoid index shifts)
        to_remove = []
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item and item.widget() and item.widget() not in keep_widgets:
                to_remove.append(item.widget())
        for w in to_remove:
            layout.removeWidget(w)
            w.setParent(None)

        # Instructions
        if _HAS_FLUENT_LABELS:
            info_label = CaptionLabel(
                "Выберите стратегию для каждой категории. "
                "Изменения применяются автоматически в preset-zapret1.txt."
            )
        else:
            from PyQt6.QtWidgets import QLabel
            info_label = QLabel(
                "Выберите стратегию для каждой категории."
            )
        info_label.setWordWrap(True)
        self.add_widget(info_label)
        self.add_spacing(8)

        # Preset manager for strategy selections
        preset_manager = None
        current_selections = {}
        filter_modes = {}
        try:
            from preset_zapret1 import PresetManagerV1, ensure_default_preset_exists_v1
            ensure_default_preset_exists_v1()
            preset_manager = PresetManagerV1()
            current_selections = preset_manager.get_strategy_selections() or {}
            preset = preset_manager.get_active_preset()
            if preset:
                filter_modes = {k: v.filter_mode for k, v in preset.categories.items()}
        except Exception:
            pass

        # Unified strategies list
        try:
            self._unified_list = UnifiedStrategiesList(parent=self)
            self._unified_list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            self._unified_list.setMinimumHeight(400)

            # Build the list with categories from registry (same as V2)
            categories = registry.categories
            self._unified_list.build_list(categories, current_selections, filter_modes=filter_modes)

            if hasattr(self._unified_list, 'strategy_selected'):
                self._unified_list.strategy_selected.connect(
                    lambda cat, sid: self._on_strategy_changed(cat, sid, preset_manager)
                )

            self.add_widget(self._unified_list)
        except Exception as e:
            log(f"Could not create UnifiedStrategiesList: {e}", "WARNING")
            if _HAS_FLUENT_LABELS:
                err_label = BodyLabel(f"Ошибка загрузки стратегий: {e}")
            else:
                from PyQt6.QtWidgets import QLabel
                err_label = QLabel(f"Ошибка загрузки стратегий: {e}")
            self.add_widget(err_label)

    def _on_strategy_changed(self, category_key: str, strategy_id: str, preset_manager) -> None:
        """Called when user selects a strategy in the unified list."""
        if preset_manager is None:
            return
        try:
            # Skip if same strategy already selected (avoids unnecessary winws restart)
            current = preset_manager.get_strategy_selections() or {}
            if current.get(category_key) == strategy_id:
                log(f"V1 strategy unchanged, skip: {category_key} = {strategy_id}", "DEBUG")
                return

            preset_manager.set_strategy_selection(category_key, strategy_id, save_and_sync=True)
            self.strategy_selected.emit(category_key, strategy_id)
            log(f"V1 strategy set: {category_key} = {strategy_id}", "DEBUG")
        except Exception as e:
            log(f"Error setting V1 strategy: {e}", "ERROR")

    def reload_for_mode_change(self):
        self._built = False
        self._strategy_set_snapshot = None
        if self.isVisible():
            self._schedule_build()

    def update_current_strategy(self, name: str):
        pass
