# ui/pages/diagnostics_tab_page.py
"""Объединённая страница диагностики с Pivot-вкладками.

Содержит:
  - Диагностика соединения (ConnectionTestPage)
  - DNS подмена (DNSCheckPage)
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget

try:
    from qfluentwidgets import SegmentedWidget
    _PIVOT_OK = True
except ImportError:
    SegmentedWidget = None
    _PIVOT_OK = False


class DiagnosticsTabPage(QWidget):
    """Контейнерная страница диагностики с вкладками: соединение + DNS."""

    TAB_KEYS   = ["connection", "dns"]
    TAB_LABELS = ["Диагностика соединения", "DNS подмена"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("DiagnosticsTabPage")

        app_parent = parent

        from ui.pages.connection_page import ConnectionTestPage
        from ui.pages.dns_check_page import DNSCheckPage

        self.connection_page = ConnectionTestPage(app_parent)
        self.dns_check_page  = DNSCheckPage(app_parent)

        # Stacked widget
        self.stacked = QStackedWidget(self)
        self.stacked.addWidget(self.connection_page)  # 0
        self.stacked.addWidget(self.dns_check_page)   # 1

        # Pivot tab bar
        if _PIVOT_OK:
            self.pivot = SegmentedWidget(self)
            for i, (key, label) in enumerate(zip(self.TAB_KEYS, self.TAB_LABELS)):
                self.pivot.addItem(key, label, lambda *_, idx=i: self._switch_tab(idx))
            self.pivot.setCurrentItem("connection")
            self.pivot.setItemFontSize(13)
        else:
            self.pivot = None

        # Layout: pivot bar with margins aligned with BasePage content
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        if self.pivot is not None:
            pivot_row = QWidget(self)
            pivot_row_layout = QHBoxLayout(pivot_row)
            pivot_row_layout.setContentsMargins(36, 8, 36, 0)
            pivot_row_layout.addWidget(self.pivot)
            main_layout.addWidget(pivot_row)

        main_layout.addWidget(self.stacked)

        self._switch_tab(0)

    # ------------------------------------------------------------------
    # Tab switching
    # ------------------------------------------------------------------

    def _switch_tab(self, index: int) -> None:
        self.stacked.setCurrentIndex(index)
        if self.pivot is not None and 0 <= index < len(self.TAB_KEYS):
            self.pivot.setCurrentItem(self.TAB_KEYS[index])

    def switch_to_tab(self, key: str) -> None:
        """External API: switch to the named tab."""
        if key in self.TAB_KEYS:
            self._switch_tab(self.TAB_KEYS.index(key))

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def cleanup(self) -> None:
        for page in (self.connection_page, self.dns_check_page):
            if hasattr(page, "cleanup"):
                try:
                    page.cleanup()
                except Exception:
                    pass
