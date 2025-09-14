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
            
            # Закрываем splash только если автозапуск отключен
            if hasattr(self.app, 'splash') and self.app.splash:
                self.app.splash.set_progress(100, "Готово", "Автозапуск DPI отключен")
            
            return

        # 2. Получаем метод запуска
        from strategy_menu import get_strategy_launch_method
        launch_method = get_strategy_launch_method()
        
        # 3. Определяем, какую стратегию запускать
        from config import get_last_strategy
        strategy_name = get_last_strategy()
        
        # Обновляем прогресс
        if hasattr(self.app, 'splash') and self.app.splash:
            self.app.splash.set_progress(65, f"Запуск стратегии '{strategy_name}'...", "")
        
        # Проверяем, является ли это комбинированной стратегией
        if strategy_name == "COMBINED_DIRECT":
            self._start_combined_strategy(launch_method)
        else:
            self._start_regular_strategy(strategy_name, launch_method)

        # 5. Обновляем интерфейс через UI Manager
        if hasattr(self.app, 'ui_manager'):
            self.app.ui_manager.update_ui_state(running=True)

    def _start_combined_strategy(self, launch_method: str) -> None:
        """Запускает комбинированную стратегию"""
        from strategy_menu import get_strategy_launch_method
        
        # Проверяем, что мы в режиме прямого запуска
        if get_strategy_launch_method() == "direct":
            from strategy_menu import get_direct_strategy_selections
            from strategy_menu.strategy_lists_separated import combine_strategies
            
            selections = get_direct_strategy_selections()
            combined = combine_strategies(
                selections.get('youtube'),
                selections.get('youtube_udp'),
                selections.get('googlevideo_tcp'),
                selections.get('discord'),
                selections.get('discord_voice_udp'),
                selections.get('rutracker_tcp'),
                selections.get('ntcparty_tcp'),
                selections.get('twitch_tcp'),
                selections.get('phasmophobia_udp'),
                selections.get('other'),
                selections.get('hostlist_80port'),
                selections.get('ipset'),
                selections.get('ipset_udp'),
            )
            
            # Создаем объект комбинированной стратегии
            combined_data = {
                'id': 'COMBINED_DIRECT',
                'name': 'Прямой запуск',
                'is_combined': True,
                'args': combined['args'],
                'selections': selections
            }
            
            log(f"Автозапуск комбинированной стратегии с выборами: {selections}", level="INFO")
            
            # Обновляем UI
            self.app.current_strategy_label.setText("Прямой запуск")
            self.app.current_strategy_name = "Прямой запуск"
            
            # Запускаем с комбинированными данными
            self.app.dpi_controller.start_dpi_async(selected_mode=combined_data)
        else:
            # Если не в режиме прямого запуска, используем fallback
            log("Комбинированная стратегия недоступна в классическом режиме", level="⚠ WARNING")
            # Используем стратегию по умолчанию
            self.app.dpi_controller.start_dpi_async(selected_mode="default")

    def _start_regular_strategy(self, strategy_name: str, launch_method: str) -> None:
        """Запускает обычную стратегию"""
        log(f"Автозапуск DPI: стратегия «{strategy_name}»", level="INFO")
        
        # ИСПРАВЛЕНИЕ: Проверяем совместимость режима и стратегии
        if launch_method == "direct":
            log(f"Обычная стратегия '{strategy_name}' несовместима с Direct режимом", "⚠ WARNING")
            
            # Вариант А: Переключаемся на BAT режим для этой стратегии
            log("Переключаемся на BAT режим для запуска обычной стратегии", "INFO")
            from strategy_menu import set_strategy_launch_method
            set_strategy_launch_method("bat")
            
            # Обновляем UI
            self.app.current_strategy_label.setText(strategy_name)
            self.app.current_strategy_name = strategy_name
            
            # Запускаем через BAT
            self.app.dpi_controller.start_dpi_async(selected_mode=strategy_name)
            
        else:
            # BAT режим - запускаем как обычно
            self.app.current_strategy_label.setText(strategy_name)
            self.app.current_strategy_name = strategy_name
            self.app.dpi_controller.start_dpi_async(selected_mode=strategy_name)