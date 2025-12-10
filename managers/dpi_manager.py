from PyQt6.QtCore import QObject
from log import log

class DPIManager(QObject):
    """⚡ Упрощенный менеджер для управления DPI операциями"""
    
    def __init__(self, app_instance):
        super().__init__()
        self.app = app_instance
        self._autostart_initiated = False

    def delayed_dpi_start(self) -> None:
        """⚡ Быстрый автозапуск DPI при старте приложения"""
        
        # Защита от двойного вызова
        if self._autostart_initiated:
            log("Автозапуск DPI уже выполнен", "DEBUG")
            return
        
        self._autostart_initiated = True
        
        # 1. Проверяем, включен ли автозапуск
        from config import get_dpi_autostart
        if not get_dpi_autostart():
            log("Автозапуск DPI отключён", "INFO")
            self._finish_splash("Готово", "Автозапуск отключен")
            self._update_ui(running=False)
            return

        # 2. Определяем режим запуска (Direct или BAT)
        from strategy_menu import get_strategy_launch_method
        launch_method = get_strategy_launch_method()
        
        # 3. Запускаем соответствующий режим
        if launch_method == "direct":
            self._start_direct_mode()
        else:
            self._start_bat_mode()
    
    def _update_ui(self, running: bool):
        """Обновляет UI состояние"""
        if hasattr(self.app, 'ui_manager'):
            self.app.ui_manager.update_ui_state(running=running)
    
    def _update_splash(self, progress: int, message: str, subtitle: str = ""):
        """Обновляет splash screen"""
        if hasattr(self.app, 'splash') and self.app.splash:
            self.app.splash.set_progress(progress, message, subtitle)
    
    def _finish_splash(self, message: str, subtitle: str = ""):
        """Завершает splash screen"""
        self._update_splash(100, message, subtitle)

    def _start_direct_mode(self):
        """⚡ Запускает Direct режим (комбинированные стратегии)"""
        from strategy_menu import get_direct_strategy_selections
        from strategy_menu.strategy_lists_separated import combine_strategies
        
        # Получаем выборы пользователя и комбинируем стратегии
        selections = get_direct_strategy_selections()
        combined = combine_strategies(**selections)
        
        # Проверка: есть ли активные категории?
        if combined.get('_active_categories', 0) == 0:
            log("Автозапуск пропущен: нет активных категорий", "INFO")
            self.app.set_status("⚠️ Выберите хотя бы одну категорию")
            self._finish_splash("Готово", "Категории не выбраны")
            self._update_ui(running=False)
            return
        
        # Подготавливаем данные для запуска
        strategy_data = {
            'id': 'DIRECT_MODE',
            'name': 'Прямой запуск',
            'is_combined': True,
            'args': combined['args'],
            'selections': selections
        }
        
        log(f"Автозапуск Direct: {selections}", "INFO")
        
        # Обновляем UI и запускаем
        self.app.current_strategy_label.setText("Прямой запуск")
        self.app.current_strategy_name = "Прямой запуск"
        self._update_splash(65, "Запуск Direct режима...")
        self.app.dpi_controller.start_dpi_async(selected_mode=strategy_data)
        self._update_ui(running=True)

    def _start_bat_mode(self):
        """⚡ Запускает BAT стратегию"""
        from config.reg import get_last_bat_strategy
        
        strategy_name = get_last_bat_strategy()
        log(f"Автозапуск BAT: «{strategy_name}»", "INFO")
        
        # Обновляем UI и запускаем
        self.app.current_strategy_label.setText(strategy_name)
        self.app.current_strategy_name = strategy_name
        self._update_splash(65, f"Запуск '{strategy_name}'...")
        self.app.dpi_controller.start_dpi_async(selected_mode=strategy_name)
        self._update_ui(running=True)