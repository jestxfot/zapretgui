# ui/pages/orchestra/orchestra_settings_page.py
"""Объединённая страница настроек оркестратора с вкладками.

Содержит:
  - Залоченные стратегии (OrchestraLockedPage)
  - Заблокированные стратегии (OrchestraBlockedPage)
  - Белый список (OrchestraWhitelistPage)
  - Рейтинги (OrchestraRatingsPage)
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget

try:
    from qfluentwidgets import SegmentedWidget
    _PIVOT_OK = True
except ImportError:
    SegmentedWidget = None
    _PIVOT_OK = False


class OrchestraSettingsPage(QWidget):
    """Контейнерная страница настроек оркестратора с вкладками."""

    TAB_KEYS   = ["locked", "blocked", "whitelist", "ratings"]
    TAB_LABELS = ["Залоченные", "Заблокированные", "Белый список", "Рейтинги"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("OrchestraSettingsPage")

        app_parent = parent

        from ui.pages.orchestra.locked_page import OrchestraLockedPage
        from ui.pages.orchestra.blocked_page import OrchestraBlockedPage
        from ui.pages.orchestra.whitelist_page import OrchestraWhitelistPage
        from ui.pages.orchestra.ratings_page import OrchestraRatingsPage

        self.locked_page    = OrchestraLockedPage(app_parent)
        self.blocked_page   = OrchestraBlockedPage(app_parent)
        self.whitelist_page = OrchestraWhitelistPage(app_parent)
        self.ratings_page   = OrchestraRatingsPage(app_parent)

        # Stacked widget
        self.stacked = QStackedWidget(self)
        self.stacked.addWidget(self.locked_page)     # 0
        self.stacked.addWidget(self.blocked_page)    # 1
        self.stacked.addWidget(self.whitelist_page)  # 2
        self.stacked.addWidget(self.ratings_page)    # 3

        # Pivot tab bar
        if _PIVOT_OK:
            self.pivot = SegmentedWidget(self)
            for i, (key, label) in enumerate(zip(self.TAB_KEYS, self.TAB_LABELS)):
                self.pivot.addItem(key, label, lambda *_, idx=i: self._switch_tab(idx))
            self.pivot.setCurrentItem("locked")
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
        for page in (self.locked_page, self.blocked_page,
                     self.whitelist_page, self.ratings_page):
            if hasattr(page, "cleanup"):
                try:
                    page.cleanup()
                except Exception:
                    pass
