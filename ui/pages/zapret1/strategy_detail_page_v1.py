# ui/pages/zapret1/strategy_detail_page_v1.py
"""Страница деталей стратегии для выбранной категории (Zapret 1).

Открывается при клике на категорию в Zapret1StrategiesPage.
Не требует Lua, blobs, syndata — только классические desync аргументы.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QSize
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QSizePolicy
from PyQt6.QtGui import QColor

from ui.pages.base_page import BasePage
from log import log

try:
    from qfluentwidgets import (
        SettingCard, SettingCardGroup,
        TransparentPushButton, CaptionLabel, BodyLabel, StrongBodyLabel,
        InfoBar, FluentIcon as FIF,
    )
    _HAS_FLUENT = True
except ImportError:
    _HAS_FLUENT = False
    SettingCard = None       # type: ignore
    SettingCardGroup = None  # type: ignore
    TransparentPushButton = None  # type: ignore
    CaptionLabel = None      # type: ignore
    BodyLabel = None         # type: ignore
    StrongBodyLabel = None   # type: ignore
    InfoBar = None           # type: ignore
    FIF = None               # type: ignore


# ── Strategy card ──────────────────────────────────────────────────────────────

class _StrategyCard(SettingCard):
    """Карточка стратегии: иконка + название + описание [Активна]."""

    select_requested = pyqtSignal(str)  # strategy_id

    def __init__(self, strategy_id: str, name: str, description: str,
                 label: str | None, is_active: bool, parent=None):
        icon = FIF.PIN if is_active else FIF.DOCUMENT
        super().__init__(icon, name, description or "", parent)
        self._strategy_id = strategy_id
        self._is_active = is_active

        # Label badge (recommended / experimental / ...)
        if label and label != "none":
            badge_text, badge_colors = _label_badge(label)
            if badge_text:
                lbl = CaptionLabel(badge_text, self)
                lbl.setTextColor(*badge_colors)
                self.hBoxLayout.addWidget(lbl, 0, Qt.AlignmentFlag.AlignVCenter)
                self.hBoxLayout.addSpacing(6)

        # «Активна» badge
        if is_active:
            active_lbl = CaptionLabel("Активна", self)
            active_lbl.setTextColor(
                QColor(0, 100, 180),
                QColor(96, 205, 255),
            )
            self.hBoxLayout.addWidget(active_lbl, 0, Qt.AlignmentFlag.AlignVCenter)
            self.hBoxLayout.addSpacing(8)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and not self._is_active:
            self.select_requested.emit(self._strategy_id)
        super().mousePressEvent(event)


def _label_badge(label: str) -> tuple[str, tuple]:
    """Отображаемый текст и цвета для label badge."""
    mapping = {
        "recommended": ("Рекомендовано", (QColor(0, 120, 0), QColor(96, 205, 130))),
        "stable":      ("Стабильная",    (QColor(0, 80, 160), QColor(96, 180, 255))),
        "experimental":("Эксперим.",     (QColor(160, 100, 0), QColor(255, 190, 80))),
        "game":        ("Игровая",       (QColor(100, 0, 160), QColor(180, 130, 255))),
        "caution":     ("Осторожно",     (QColor(150, 50, 0), QColor(255, 120, 60))),
    }
    entry = mapping.get(str(label).lower())
    if entry:
        return entry
    return "", (QColor(100, 100, 100), QColor(160, 160, 160))


# ── Main page ──────────────────────────────────────────────────────────────────

class Zapret1StrategyDetailPage(BasePage):
    """Страница выбора стратегии для одной категории Zapret 1."""

    strategy_selected = pyqtSignal(str, str)  # category_key, strategy_id
    back_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(title="Стратегия", parent=parent)
        self.parent_app = parent

        self._category_key: str = ""
        self._category_info: dict = {}
        self._preset_manager = None
        self._built = False

        if _HAS_FLUENT:
            back_btn = TransparentPushButton()
            back_btn.setText("← Стратегии")
            back_btn.setIconSize(QSize(16, 16))
            back_btn.clicked.connect(self.back_clicked.emit)
            self.add_widget(back_btn)

    # ── Public API ──────────────────────────────────────────────────────────

    def set_category(self, category_key: str, category_info: dict, preset_manager) -> None:
        """Настроить страницу для нужной категории перед показом."""
        self._category_key = category_key
        self._category_info = category_info
        self._preset_manager = preset_manager
        self._built = False

        full_name = category_info.get("full_name", category_key)
        self.title_label.setText(full_name)

    def showEvent(self, a0):
        super().showEvent(a0)
        if not self._built:
            QTimer.singleShot(0, self._build_content)

    # ── Build ──────────────────────────────────────────────────────────────

    def _build_content(self):
        try:
            self._do_build()
        except Exception as e:
            log(f"Zapret1StrategyDetailPage: ошибка построения: {e}", "ERROR")
        self._built = True

    def _do_build(self):
        # Удаляем предыдущий контент (кроме title/subtitle и кнопки Назад)
        self._clear_dynamic_widgets()

        if not _HAS_FLUENT:
            from PyQt6.QtWidgets import QLabel
            self.add_widget(QLabel("qfluentwidgets не установлен"))
            return

        if not self._category_key:
            self.add_widget(BodyLabel("Категория не задана"))
            return

        # Текущая выбранная стратегия
        current_sid = "none"
        if self._preset_manager:
            try:
                sels = self._preset_manager.get_strategy_selections() or {}
                current_sid = sels.get(self._category_key, "none")
            except Exception:
                pass

        # Загружаем стратегии для категории
        strategies: dict = {}
        try:
            from preset_zapret1.strategies_loader import load_v1_strategies
            strategies = load_v1_strategies(self._category_key)
        except Exception as e:
            log(f"Zapret1StrategyDetailPage: cannot load strategies: {e}", "ERROR")

        group = SettingCardGroup("Стратегии")

        # «Не задано» — всегда первым
        none_is_active = (current_sid == "none")
        none_card = _StrategyCard(
            "none", "Не задано",
            "Отключить desync для этой категории",
            None, none_is_active, group,
        )
        none_card.select_requested.connect(self._on_strategy_selected)
        group.addSettingCard(none_card)

        if not strategies:
            tip = BodyLabel("Нет стратегий. Поместите tcp_zapret1.txt в preset_zapret1/basic_strategies/")
            tip.setWordWrap(True)
            self.add_widget(tip)
            self.add_widget(group)
            return

        # Сортировка: recommended/stable первыми
        _LABEL_ORDER = {"recommended": 0, "stable": 1, None: 2, "experimental": 3, "game": 4, "caution": 5}
        sorted_strats = sorted(
            strategies.values(),
            key=lambda s: (_LABEL_ORDER.get(s.get("label"), 2), s.get("name", "").lower()),
        )

        for strat in sorted_strats:
            sid = strat.get("id", "")
            if not sid:
                continue
            is_active = (sid == current_sid)
            card = _StrategyCard(
                sid,
                strat.get("name", sid),
                strat.get("description", ""),
                strat.get("label"),
                is_active,
                group,
            )
            card.select_requested.connect(self._on_strategy_selected)
            group.addSettingCard(card)

        self.add_widget(group)

    def _clear_dynamic_widgets(self) -> None:
        """Удалить виджеты, добавленные после title/subtitle/back_btn."""
        keep = {self.title_label, self.subtitle_label}
        # Найти back_btn (TransparentPushButton добавленная первой в __init__)
        for i in range(self.vBoxLayout.count()):
            item = self.vBoxLayout.itemAt(i)
            w = item.widget() if item else None
            if w and _HAS_FLUENT and isinstance(w, TransparentPushButton):
                keep.add(w)
                break

        to_remove = []
        for i in range(self.vBoxLayout.count()):
            item = self.vBoxLayout.itemAt(i)
            w = item.widget() if item else None
            if w and w not in keep:
                to_remove.append(w)
        for w in to_remove:
            self.vBoxLayout.removeWidget(w)
            w.setParent(None)

    # ── Selection ──────────────────────────────────────────────────────────

    def _on_strategy_selected(self, strategy_id: str) -> None:
        if not self._preset_manager or not self._category_key:
            return
        try:
            self._preset_manager.set_strategy_selection(
                self._category_key, strategy_id, save_and_sync=True
            )
            self.strategy_selected.emit(self._category_key, strategy_id)
            log(f"V1 strategy set: {self._category_key} = {strategy_id}", "INFO")

            if _HAS_FLUENT and InfoBar:
                from preset_zapret1.strategies_loader import load_v1_strategies
                strats = load_v1_strategies(self._category_key)
                name = (strats.get(strategy_id) or {}).get("name", strategy_id) if strategy_id != "none" else "Не задано"
                InfoBar.success(
                    title="Стратегия применена",
                    content=name,
                    parent=self.window(),
                    duration=2000,
                )
        except Exception as e:
            log(f"V1 strategy selection error: {e}", "ERROR")
            if _HAS_FLUENT and InfoBar:
                InfoBar.error(title="Ошибка", content=str(e), parent=self.window())

        # Перестроить страницу с новым активным состоянием
        self._built = False
        QTimer.singleShot(50, self._build_content)
