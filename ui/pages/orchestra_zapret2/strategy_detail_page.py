from ui.pages.zapret2.strategy_detail_page import StrategyDetailPage


class OrchestraZapret2StrategyDetailPage(StrategyDetailPage):
    def showEvent(self, event):
        super().showEvent(event)
        try:
            self.title_label.setText("Детали стратегии Orchestra Z2")
        except Exception:
            pass
