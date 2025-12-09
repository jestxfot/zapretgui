from PyQt6.QtCore import QObject
from log import log
import time

class DPIManager(QObject):
    """Менеджер для управления DPI операциями"""
    
    def __init__(self, app_instance):
        super().__init__()
        self.app = app_instance

    def delayed_dpi_start(self) -> None:
        """Выполняет отложенный запуск DPI с проверкой наличия автозапуска"""
        
        # ✅ ЗАЩИТА ОТ ДВОЙНОГО ВЫЗОВА
        if hasattr(self.app, '_dpi_autostart_initiated') and self.app._dpi_autostart_initiated:
            log("Автозапуск DPI уже был инициирован, пропускаем", "DEBUG")
            return
        
        self.app._dpi_autostart_initiated = True
        
        from config import get_dpi_autostart

        # 1. Автозапуск DPI включён?
        if not get_dpi_autostart():
            log("Автозапуск DPI отключён пользователем.", level="INFO")
            if hasattr(self.app, 'ui_manager'):
                self.app.ui_manager.update_ui_state(running=False)
            
            return

        # 2. Получаем метод запуска
        from strategy_menu import get_strategy_launch_method
        launch_method = get_strategy_launch_method()
        
        # 3. Определяем, какую стратегию запускать (разные ключи реестра для BAT и Direct)
        if launch_method == "direct":
            # Direct режим - используем комбинированную стратегию из selections
            strategy_name = "Прямой запуск"
            self._start_direct_mode()
        else:
            # BAT режим - используем последнюю BAT стратегию
            from config.reg import get_last_bat_strategy
            strategy_name = get_last_bat_strategy()
            self._start_bat_strategy(strategy_name)

        # 5. Обновляем интерфейс через UI Manager
        if hasattr(self.app, 'ui_manager'):
            self.app.ui_manager.update_ui_state(running=True)

    def _start_direct_mode(self) -> None:
        """Запускает Direct режим (комбинированная стратегия из selections)"""
        from strategy_menu import get_direct_strategy_selections
        from strategy_menu.strategy_lists_separated import combine_strategies
        
        selections = get_direct_strategy_selections()
        combined = combine_strategies(**selections)
        
        # ✅ ПРОВЕРКА: Если нет активных категорий, не запускаем DPI
        active_categories = combined.get('_active_categories', 0)
        if active_categories == 0:
            log("Автозапуск DPI пропущен: нет активных категорий (все выборы = 'none')", level="INFO")
            self.app.set_status("⚠️ Выберите хотя бы одну категорию для запуска")
            
            # Обновляем UI как "не запущено"
            if hasattr(self.app, 'ui_manager'):
                self.app.ui_manager.update_ui_state(running=False)
            
            return
        
        # Создаем объект для Direct режима
        combined_data = {
            'id': 'DIRECT_MODE',
            'name': 'Прямой запуск',
            'is_combined': True,
            'args': combined['args'],
            'selections': selections
        }
        
        log(f"Автозапуск Direct режима с выборами: {selections}", level="INFO")
        
        # Обновляем UI
        self.app.current_strategy_label.setText("Прямой запуск")
        self.app.current_strategy_name = "Прямой запуск"
        
        # Запускаем с комбинированными данными
        self.app.dpi_controller.start_dpi_async(selected_mode=combined_data)

    def _start_bat_strategy(self, strategy_name: str) -> None:
        """Запускает BAT стратегию"""
        log(f"Автозапуск DPI: BAT стратегия «{strategy_name}»", level="INFO")
        
        # Обновляем UI
        self.app.current_strategy_label.setText(strategy_name)
        self.app.current_strategy_name = strategy_name
        
        # Запускаем BAT стратегию
        self.app.dpi_controller.start_dpi_async(selected_mode=strategy_name)