# ui/pages/orchestra_ratings_page.py
"""Страница истории стратегий с рейтингами (оркестратор)"""

from PyQt6.QtCore import Qt, QSize, QTimer
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QWidget,
    QLineEdit, QPushButton, QTextEdit
)
import qtawesome as qta

from .base_page import BasePage
from ui.sidebar import SettingsCard
from ui.widgets.line_edit_icons import set_line_edit_clear_button_icon
from ui.theme import get_theme_tokens
from log import log


class OrchestraRatingsPage(BasePage):
    """Страница истории стратегий с рейтингами"""

    def __init__(self, parent=None):
        super().__init__(
            "История стратегий (рейтинги)",
            "Рейтинг = успехи / (успехи + провалы). При UNLOCK выбирается лучшая стратегия из истории.",
            parent
        )
        self.setObjectName("orchestraRatingsPage")
        self._applying_theme_styles = False
        self._theme_refresh_scheduled = False
        self._setup_ui()

        self._apply_theme()

    def _setup_ui(self):
        # === Фильтр ===
        filter_card = SettingsCard("Фильтр")
        filter_layout = QHBoxLayout()

        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("Поиск по домену...")
        self.filter_input.setClearButtonEnabled(True)
        set_line_edit_clear_button_icon(self.filter_input)
        self.filter_input.textChanged.connect(self._apply_filter)
        # Styled in _apply_theme()
        filter_layout.addWidget(self.filter_input, 1)

        self.refresh_btn = QPushButton("Обновить")
        self.refresh_btn.setIconSize(QSize(16, 16))
        self.refresh_btn.setFixedHeight(32)
        self.refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.refresh_btn.clicked.connect(self._refresh_data)
        # Styled in _apply_theme()
        filter_layout.addWidget(self.refresh_btn)

        filter_card.add_layout(filter_layout)
        self.layout.addWidget(filter_card)

        # === Статистика ===
        self.stats_label = QLabel("Загрузка...")
        self.layout.addWidget(self.stats_label)

        # === История стратегий ===
        history_card = SettingsCard("Рейтинги по доменам")
        history_layout = QVBoxLayout()

        self.history_text = QTextEdit()
        self.history_text.setReadOnly(True)
        self.history_text.setMinimumHeight(300)
        # Styled in _apply_theme()
        self.history_text.setPlainText("История стратегий появится после обучения...")
        history_layout.addWidget(self.history_text)

        history_card.add_layout(history_layout)
        self.layout.addWidget(history_card)

        # Хранилище данных для фильтрации
        self._full_history_data = {}
        self._tls_data = {}
        self._http_data = {}
        self._udp_data = {}

    def changeEvent(self, event):  # noqa: N802 (Qt override)
        try:
            from PyQt6.QtCore import QEvent

            if event.type() in (QEvent.Type.StyleChange, QEvent.Type.PaletteChange):
                self._schedule_theme_refresh()
        except Exception:
            pass
        return super().changeEvent(event)

    def _schedule_theme_refresh(self) -> None:
        if self._applying_theme_styles:
            return
        if self._theme_refresh_scheduled:
            return
        self._theme_refresh_scheduled = True
        QTimer.singleShot(0, self._on_debounced_theme_change)

    def _on_debounced_theme_change(self) -> None:
        self._theme_refresh_scheduled = False
        self._apply_theme()

    def _apply_theme(self) -> None:
        if self._applying_theme_styles:
            return

        self._applying_theme_styles = True
        try:
            tokens = get_theme_tokens()
            selection_fg = "rgba(0, 0, 0, 0.90)" if tokens.is_light else "rgba(245, 245, 245, 0.92)"

            if hasattr(self, "filter_input") and self.filter_input is not None:
                set_line_edit_clear_button_icon(self.filter_input)
                self.filter_input.setStyleSheet(
                    f"""
                    QLineEdit {{
                        background-color: {tokens.surface_bg};
                        color: {tokens.fg};
                        border: 1px solid {tokens.surface_border};
                        border-radius: 4px;
                        padding: 8px 12px;
                    }}
                    QLineEdit:hover {{
                        background-color: {tokens.surface_bg_hover};
                        border-color: {tokens.surface_border_hover};
                    }}
                    QLineEdit:focus {{
                        border: 1px solid {tokens.accent_hex};
                    }}
                    QLineEdit::placeholder {{
                        color: {tokens.fg_faint};
                    }}
                    """
                )

            if hasattr(self, "refresh_btn") and self.refresh_btn is not None:
                self.refresh_btn.setIcon(qta.icon("mdi.refresh", color=tokens.fg))
                self.refresh_btn.setStyleSheet(
                    f"""
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
                        border-color: {tokens.surface_border_hover};
                    }}
                    QPushButton:pressed {{
                        background-color: {tokens.surface_bg_pressed};
                    }}
                    """
                )

            if hasattr(self, "stats_label") and self.stats_label is not None:
                self.stats_label.setStyleSheet(
                    f"color: {tokens.fg_muted}; font-size: 12px; margin: 4px 0;"
                )

            if hasattr(self, "history_text") and self.history_text is not None:
                editor_bg = "rgba(246, 248, 252, 0.88)" if tokens.is_light else "rgba(0, 0, 0, 0.22)"
                self.history_text.setStyleSheet(
                    f"""
                    QTextEdit {{
                        background-color: {editor_bg};
                        border: 1px solid {tokens.surface_border};
                        border-radius: 6px;
                        color: {tokens.fg};
                        font-family: 'Consolas', 'Courier New', monospace;
                        font-size: 11px;
                        padding: 8px;
                    }}
                    QTextEdit::selection {{
                        background-color: {tokens.accent_soft_bg_hover};
                        color: {selection_fg};
                    }}
                    QScrollBar:vertical {{
                        background: {tokens.scrollbar_track};
                        width: 8px;
                        border-radius: 4px;
                    }}
                    QScrollBar::handle:vertical {{
                        background: {tokens.scrollbar_handle};
                        border-radius: 4px;
                        min-height: 20px;
                    }}
                    QScrollBar::handle:vertical:hover {{
                        background: {tokens.scrollbar_handle_hover};
                    }}
                    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                        height: 0px;
                    }}
                    """
                )
        finally:
            self._applying_theme_styles = False

    def showEvent(self, event):
        """При показе страницы загружаем данные"""
        super().showEvent(event)
        self._refresh_data()

    def _get_runner(self):
        """Получает orchestra_runner из главного окна"""
        app = self.window()
        if hasattr(app, 'orchestra_runner') and app.orchestra_runner:
            return app.orchestra_runner
        return None

    def _refresh_data(self):
        """Обновляет данные истории"""
        runner = self._get_runner()
        if not runner:
            self.stats_label.setText("Оркестратор не инициализирован")
            self.history_text.setPlainText("")
            return

        learned = runner.get_learned_data()
        self._full_history_data = learned.get('history', {})
        self._tls_data = learned.get('tls', {})
        self._http_data = learned.get('http', {})
        self._udp_data = learned.get('udp', {})

        self._render_history()

    def _apply_filter(self):
        """Применяет фильтр"""
        self._render_history()

    def _render_history(self):
        """Рендерит историю с учётом фильтра"""
        filter_text = self.filter_input.text().strip().lower()
        history_data = self._full_history_data

        if not history_data:
            self.stats_label.setText("Нет данных истории")
            self.history_text.setPlainText("")
            return

        lines = []
        total_strategies = 0
        shown_domains = 0

        # Сортируем домены по количеству стратегий
        sorted_domains = sorted(history_data.keys(), key=lambda d: len(history_data[d]), reverse=True)

        for domain in sorted_domains:
            # Фильтр по домену
            if filter_text and filter_text not in domain.lower():
                continue

            strategies = history_data[domain]
            if not strategies:
                continue

            shown_domains += 1

            # Определяем статус домена
            status = ""
            if domain in self._tls_data:
                status = " [TLS LOCK]"
            elif domain in self._http_data:
                status = " [HTTP LOCK]"
            elif domain in self._udp_data:
                status = " [UDP LOCK]"

            # Сортируем стратегии по рейтингу
            sorted_strats = sorted(strategies.items(), key=lambda x: x[1]['rate'], reverse=True)

            lines.append(f"═══ {domain}{status} ═══")

            for strat_num, h in sorted_strats:
                s = h['successes']
                f = h['failures']
                rate = h['rate']

                # Визуальный индикатор
                if rate >= 80:
                    bar = "████████░░"
                    indicator = "🟢"
                elif rate >= 60:
                    bar = "██████░░░░"
                    indicator = "🟡"
                elif rate >= 40:
                    bar = "████░░░░░░"
                    indicator = "🟠"
                else:
                    bar = "██░░░░░░░░"
                    indicator = "🔴"

                lines.append(f"  {indicator} #{strat_num:3d}: {bar} {rate:3d}% ({s}✓/{f}✗)")
                total_strategies += 1

            lines.append("")

        # Статистика
        total_domains = len(history_data)
        if filter_text:
            self.stats_label.setText(f"Показано: {shown_domains} из {total_domains} доменов, {total_strategies} записей")
        else:
            self.stats_label.setText(f"Всего: {total_domains} доменов, {total_strategies} записей")

        self.history_text.setPlainText("\n".join(lines))
