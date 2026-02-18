# ui/pages/orchestra_ratings_page.py
"""Страница истории стратегий с рейтингами (оркестратор)"""

from PyQt6.QtCore import QSize, QTimer
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QWidget,
)

try:
    from qfluentwidgets import LineEdit, PushButton, PlainTextEdit, CaptionLabel
    _HAS_FLUENT = True
except ImportError:
    from PyQt6.QtWidgets import QLineEdit as LineEdit, QPushButton as PushButton, QTextEdit as PlainTextEdit, QLabel as CaptionLabel
    _HAS_FLUENT = False
import qtawesome as qta

from .base_page import BasePage
from ui.compat_widgets import SettingsCard, RefreshButton
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

        self.filter_input = LineEdit()
        self.filter_input.setPlaceholderText("Поиск по домену...")
        self.filter_input.setClearButtonEnabled(True)
        self.filter_input.textChanged.connect(self._apply_filter)
        # Styled in _apply_theme()
        filter_layout.addWidget(self.filter_input, 1)

        self.refresh_btn = RefreshButton()
        self.refresh_btn.clicked.connect(self._refresh_data)
        filter_layout.addWidget(self.refresh_btn)

        filter_card.add_layout(filter_layout)
        self.layout.addWidget(filter_card)

        # === Статистика ===
        self.stats_label = CaptionLabel("Загрузка...")
        self.layout.addWidget(self.stats_label)

        # === История стратегий ===
        history_card = SettingsCard("Рейтинги по доменам")
        history_layout = QVBoxLayout()

        self.history_text = PlainTextEdit()
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
            if hasattr(self, "refresh_btn") and self.refresh_btn is not None:
                self.refresh_btn.setIcon(qta.icon("mdi.refresh", color=tokens.fg))
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
        self.refresh_btn.set_loading(True)
        try:
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
        finally:
            self.refresh_btn.set_loading(False)

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
