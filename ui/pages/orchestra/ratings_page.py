# ui/pages/orchestra/ratings_page.py
"""Страница истории стратегий с рейтингами (оркестратор)"""

from PyQt6.QtCore import QSize
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QWidget, QFrame, QPushButton,
)

try:
    from qfluentwidgets import (
        LineEdit,
        PlainTextEdit,
        TransparentToolButton,
        CaptionLabel,
        CardWidget,
        StrongBodyLabel,
    )
    _HAS_FLUENT = True
except ImportError:
    from PyQt6.QtWidgets import QLineEdit as LineEdit, QTextEdit as PlainTextEdit, QLabel as CaptionLabel
    TransparentToolButton = QPushButton
    CardWidget = QFrame
    StrongBodyLabel = QLabel
    _HAS_FLUENT = False
import qtawesome as qta

from ..base_page import BasePage
from ui.compat_widgets import set_tooltip
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
        self._refresh_loading = False

        from qfluentwidgets import qconfig
        qconfig.themeChanged.connect(lambda _: self._apply_theme())
        qconfig.themeColorChanged.connect(lambda _: self._apply_theme())

        self._setup_ui()

        self._apply_theme()

    def _create_card(self, title: str):
        card = CardWidget(self)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(12)

        title_label = StrongBodyLabel(title, card) if _HAS_FLUENT else QLabel(title)
        if not _HAS_FLUENT:
            title_label.setStyleSheet("font-size: 14px; font-weight: 600;")
        card_layout.addWidget(title_label)

        return card, card_layout

    def _set_refresh_loading(self, loading: bool) -> None:
        self._refresh_loading = loading
        if hasattr(self, "refresh_btn") and self.refresh_btn is not None:
            self.refresh_btn.setEnabled(not loading)
        self._apply_theme()

    def _setup_ui(self):
        # === Фильтр ===
        filter_card, filter_card_layout = self._create_card("Фильтр")

        filter_row = QHBoxLayout()
        filter_row.setSpacing(10)

        self.filter_input = LineEdit()
        self.filter_input.setPlaceholderText("Поиск по домену...")
        self.filter_input.setClearButtonEnabled(True)
        self.filter_input.textChanged.connect(self._apply_filter)
        # Styled in _apply_theme()
        filter_row.addWidget(self.filter_input, 1)

        self.refresh_btn = TransparentToolButton(self)
        self.refresh_btn.setFixedSize(32, 32)
        set_tooltip(self.refresh_btn, "Обновить")
        self.refresh_btn.clicked.connect(self._refresh_data)
        filter_row.addWidget(self.refresh_btn)

        filter_card_layout.addLayout(filter_row)

        self.layout.addWidget(filter_card)

        # === Статистика ===
        self.stats_label = CaptionLabel("Загрузка...")
        self.layout.addWidget(self.stats_label)

        # === История стратегий ===
        history_card, history_layout = self._create_card("Рейтинги по доменам")

        self.history_text = PlainTextEdit()
        try:
            from config.reg import get_smooth_scroll_enabled
            from qfluentwidgets.common.smooth_scroll import SmoothMode
            from PyQt6.QtCore import Qt

            smooth_enabled = get_smooth_scroll_enabled()
            mode = SmoothMode.COSINE if smooth_enabled else SmoothMode.NO_SMOOTH
            delegate = (
                getattr(self.history_text, "scrollDelegate", None)
                or getattr(self.history_text, "scrollDelagate", None)
                or getattr(self.history_text, "delegate", None)
            )
            if delegate is not None:
                if hasattr(delegate, "useAni"):
                    if not hasattr(delegate, "_zapret_base_use_ani"):
                        delegate._zapret_base_use_ani = bool(delegate.useAni)
                    delegate.useAni = bool(delegate._zapret_base_use_ani) if smooth_enabled else False
                for smooth_attr in ("verticalSmoothScroll", "horizonSmoothScroll"):
                    smooth = getattr(delegate, smooth_attr, None)
                    smooth_setter = getattr(smooth, "setSmoothMode", None)
                    if callable(smooth_setter):
                        smooth_setter(mode)

            setter = getattr(self.history_text, "setSmoothMode", None)
            if callable(setter):
                try:
                    setter(mode, Qt.Orientation.Vertical)
                except TypeError:
                    setter(mode)
        except Exception:
            pass
        self.history_text.setReadOnly(True)
        self.history_text.setMinimumHeight(300)
        # Styled in _apply_theme()
        self.history_text.setPlainText("История стратегий появится после обучения...")
        history_layout.addWidget(self.history_text)

        self.layout.addWidget(history_card)

        # Хранилище данных для фильтрации
        self._full_history_data = {}
        self._tls_data = {}
        self._http_data = {}
        self._udp_data = {}

    def _apply_theme(self) -> None:
        tokens = get_theme_tokens()
        if hasattr(self, "refresh_btn") and self.refresh_btn is not None:
            icon_name = "mdi.loading" if self._refresh_loading else "mdi.refresh"
            icon_color = tokens.fg_faint if self._refresh_loading else tokens.fg
            self.refresh_btn.setIcon(qta.icon(icon_name, color=icon_color))

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
        self._set_refresh_loading(True)
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
            self._set_refresh_loading(False)

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
