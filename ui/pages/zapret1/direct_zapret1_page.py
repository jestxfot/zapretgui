# ui/pages/zapret1/direct_zapret1_page.py
"""Список категорий Zapret 1 с drill-down к деталям стратегии."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QSize
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QSizePolicy

from ui.pages.base_page import BasePage
from log import log

try:
    from qfluentwidgets import (
        SettingCard, SettingCardGroup,
        TransparentToolButton, TransparentPushButton,
        CaptionLabel, BodyLabel,
        FluentIcon as FIF,
    )
    _HAS_FLUENT = True
except ImportError:
    _HAS_FLUENT = False
    SettingCard = None          # type: ignore
    SettingCardGroup = None     # type: ignore
    TransparentToolButton = None  # type: ignore
    TransparentPushButton = None  # type: ignore
    CaptionLabel = None         # type: ignore
    BodyLabel = None            # type: ignore
    FIF = None                  # type: ignore

try:
    import qtawesome as qta
    _HAS_QTA = True
except ImportError:
    _HAS_QTA = False


# ── Category card ──────────────────────────────────────────────────────────────

class _CategoryCard(SettingCard):
    """Карточка категории: иконка + название + текущая стратегия + шеврон."""

    clicked = pyqtSignal()

    def __init__(self, icon, title: str, subtitle: str, parent=None):
        super().__init__(icon, title, subtitle, parent)

        # Шеврон вправо (не кликабельный — весь ряд кликабельный)
        self._chevron = TransparentToolButton(FIF.CARE_RIGHT, self)
        self._chevron.setFixedSize(28, 28)
        self._chevron.setEnabled(False)
        self._chevron.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.hBoxLayout.addWidget(self._chevron, 0, Qt.AlignmentFlag.AlignVCenter)
        self.hBoxLayout.addSpacing(4)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def set_subtitle(self, text: str) -> None:
        self.contentLabel.setText(text)


# ── Main page ──────────────────────────────────────────────────────────────────

class Zapret1StrategiesPage(BasePage):
    """Список категорий Zapret 1 с drill-down при клике."""

    category_clicked = pyqtSignal(str, dict)  # category_key, category_info
    back_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(title="Стратегии Zapret 1", parent=parent)
        self.parent_app = parent

        self._built = False
        self._build_scheduled = False
        self._cards: dict[str, _CategoryCard] = {}  # category_key → card

        if _HAS_FLUENT:
            back_btn = TransparentPushButton()
            back_btn.setText("← Управление")
            back_btn.setIconSize(QSize(16, 16))
            back_btn.clicked.connect(self.back_clicked.emit)
            self.add_widget(back_btn)

    # ── Build ──────────────────────────────────────────────────────────────

    def showEvent(self, a0):
        super().showEvent(a0)
        if not self._built:
            self._schedule_build()
        else:
            # Обновить субтитры (стратегии могли измениться)
            QTimer.singleShot(0, self._refresh_subtitles)

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
            log(f"Zapret1StrategiesPage: ошибка построения: {e}", "ERROR")
        self._built = True

    def _do_build(self):
        self._cards.clear()

        if not _HAS_FLUENT:
            from PyQt6.QtWidgets import QLabel
            self.add_widget(QLabel("qfluentwidgets не установлен"))
            return

        # Загружаем категории
        categories: dict = {}
        try:
            from preset_zapret2.catalog import load_categories
            categories = load_categories()
        except Exception as e:
            log(f"Zapret1StrategiesPage: cannot load categories: {e}", "ERROR")

        if not categories:
            self.add_widget(BodyLabel("Нет доступных категорий"))
            return

        # Текущие выборы стратегий
        current_selections = self._load_current_selections()

        # Группа карточек
        group = SettingCardGroup("Категории")

        for cat_key, cat_info in categories.items():
            if not self._is_v1_compatible(cat_info):
                continue

            full_name = cat_info.get("full_name", cat_key)
            icon = self._make_icon(cat_info)
            subtitle = self._strategy_subtitle(cat_key, cat_info, current_selections)

            card = _CategoryCard(icon, full_name, subtitle, group)
            card.clicked.connect(lambda k=cat_key, i=cat_info: self.category_clicked.emit(k, i))
            group.addSettingCard(card)
            self._cards[cat_key] = card

        self.add_widget(group)

    # ── Helpers ────────────────────────────────────────────────────────────

    @staticmethod
    def _is_v1_compatible(cat_info: dict) -> bool:
        """Пропускаем категории с --filter-l7= (только orchestra/V2)."""
        for key in ("base_filter", "base_filter_ipset", "base_filter_hostlist"):
            val = cat_info.get(key, "")
            if val and "--filter-l7=" in val:
                return False
        return True

    @staticmethod
    def _make_icon(cat_info: dict):
        """Иконка категории через qtawesome, fallback на FIF.GAME."""
        icon_name = cat_info.get("icon_name", "")
        icon_color = cat_info.get("icon_color", "#909090")
        if _HAS_QTA and icon_name:
            try:
                return qta.icon(icon_name, color=icon_color)
            except Exception:
                pass
        return FIF.GAME

    @staticmethod
    def _load_current_selections() -> dict:
        try:
            from preset_zapret1 import PresetManagerV1
            return PresetManagerV1().get_strategy_selections() or {}
        except Exception:
            return {}

    @staticmethod
    def _strategy_name(strategy_id: str, cat_key: str, cat_info: dict) -> str:
        """Возвращает отображаемое имя стратегии по id."""
        if not strategy_id or strategy_id == "none":
            return "Не задано"
        try:
            from preset_zapret1.strategies_loader import load_v1_strategies
            strats = load_v1_strategies(cat_key)
            info = strats.get(strategy_id)
            if info:
                return info.get("name", strategy_id)
        except Exception:
            pass
        return strategy_id

    def _strategy_subtitle(self, cat_key: str, cat_info: dict, selections: dict) -> str:
        sid = selections.get(cat_key, "none")
        return self._strategy_name(sid, cat_key, cat_info)

    def _refresh_subtitles(self) -> None:
        """Обновить субтитры карточек без полного перестроения."""
        selections = self._load_current_selections()
        try:
            from preset_zapret2.catalog import load_categories
            categories = load_categories()
        except Exception:
            return
        for cat_key, card in self._cards.items():
            cat_info = categories.get(cat_key, {})
            card.set_subtitle(self._strategy_subtitle(cat_key, cat_info, selections))

    # ── Public API ──────────────────────────────────────────────────────────

    def reload_for_mode_change(self) -> None:
        self._built = False
        self._cards.clear()
        if self.isVisible():
            self._schedule_build()

    def update_current_strategy(self, name: str) -> None:
        pass
