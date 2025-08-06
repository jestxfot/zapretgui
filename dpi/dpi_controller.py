# dpi_controller.py
"""
Контроллер для управления DPI - содержит всю логику запуска и остановки
"""

from PyQt6.QtCore import QThread, QObject, pyqtSignal
from config import get_strategy_launch_method
from log import log
import time

class DPIStartWorker(QObject):
    """Worker для асинхронного запуска DPI"""
    finished = pyqtSignal(bool, str)  # success, error_message
    progress = pyqtSignal(str)        # status_message
    
    def __init__(self, app_instance, selected_mode, launch_method):
        super().__init__()
        self.app_instance = app_instance
        self.selected_mode = selected_mode
        self.launch_method = launch_method
        self.dpi_starter = app_instance.dpi_starter
    
    def run(self):
        try:
            self.progress.emit("Подготовка к запуску...")
            
            # Проверяем, не запущен ли уже процесс
            if self.dpi_starter.check_process_running_wmi(silent=True):
                self.progress.emit("Останавливаем предыдущий процесс...")
                # Останавливаем через соответствующий метод
                if self.launch_method == "direct":
                    from strategy_menu.strategy_runner import get_strategy_runner
                    runner = get_strategy_runner(self.app_instance.dpi_starter.winws_exe)
                    runner.stop()
                else:
                    from dpi.stop import stop_dpi
                    stop_dpi(self.app_instance)
            
            self.progress.emit("Запуск DPI...")
            
            # Выбираем метод запуска
            if self.launch_method == "direct":
                success = self._start_direct()
            else:
                success = self._start_bat()
            
            if success:
                self.progress.emit("DPI успешно запущен")
                self.finished.emit(True, "")
            else:
                self.finished.emit(False, "Не удалось запустить DPI")
                
        except Exception as e:
            error_msg = f"Ошибка запуска DPI: {str(e)}"
            log(error_msg, "❌ ERROR")
            self.finished.emit(False, error_msg)
    
    def _start_direct(self):
        """Запуск через новый метод (StrategyRunner)"""
        try:
            from strategy_menu.strategy_runner import get_strategy_runner
            from strategy_menu.strategy_definitions import get_all_strategies
            
            # Создаем runner
            runner = get_strategy_runner(self.app_instance.dpi_starter.winws_exe)
            
            # Нормализуем selected_mode
            mode_param = self.selected_mode
            strategy_info = None
            strategy_name = None
            strategy_id = None
            
            # Обработка кортежа
            if isinstance(mode_param, tuple) and len(mode_param) == 2:
                # Это кортеж (strategy_id, strategy_name)
                strategy_id, strategy_name = mode_param
                log(f"Получен кортеж: ID={strategy_id}, name={strategy_name}", "DEBUG")
                
            elif isinstance(mode_param, dict):
                # Это полная информация о стратегии из index.json
                strategy_info = mode_param
                strategy_name = mode_param.get('name', 'unknown')
                strategy_id = mode_param.get('id', 'custom')
                
            elif isinstance(mode_param, str):
                # Это имя стратегии
                strategy_name = mode_param
                
            else:
                # По умолчанию
                strategy_name = "Если стратегия не работает смени её!"
            
            log(f"Прямой запуск стратегии: {strategy_name} (ID: {strategy_id})", "INFO")
            
            # Если у нас есть strategy_id, сразу запускаем его
            if strategy_id:
                log(f"Запуск стратегии по ID: {strategy_id}", "INFO")
                return runner.start_strategy(strategy_id)
            
            # Проверяем встроенные стратегии
            builtin_strategies = get_all_strategies()
            
            # Ищем среди встроенных стратегий по имени
            for bid, binfo in builtin_strategies.items():
                if binfo.get('name') == strategy_name:
                    log(f"Найдена встроенная стратегия: {bid}", "INFO")
                    return runner.start_strategy(bid)
            
            # Если встроенная стратегия не найдена, используем внешнюю
            if strategy_info:
                log("Встроенная стратегия не найдена, парсим внешнюю", "INFO")
                custom_args = runner.parse_strategy_from_index(strategy_info)
                if custom_args:
                    return runner.start_strategy("custom", custom_args)
            
            # Fallback - используем первую встроенную стратегию
            if builtin_strategies:
                first_strategy_id = next(iter(builtin_strategies.keys()))
                log(f"Fallback к встроенной стратегии: {first_strategy_id}", "INFO")
                return runner.start_strategy(first_strategy_id)
            
            log("Не найдено подходящих стратегий", "❌ ERROR")
            return False
            
        except Exception as e:
            log(f"Ошибка прямого запуска: {e}", "❌ ERROR")
            return False
    
    def _start_bat(self):
        """Запуск через старый метод (.bat файлы)"""
        try:
            # Нормализуем selected_mode
            mode_param = self.selected_mode
            
            if isinstance(mode_param, dict):
                mode_param = mode_param.get('name') or 'default'
            elif mode_param is None:
                mode_param = 'default'
            
            # Вызываем синхронный метод в отдельном потоке
            return self.dpi_starter.start_dpi(selected_mode=mode_param)
            
        except Exception as e:
            log(f"Ошибка запуска через .bat: {e}", "❌ ERROR")
            return False


class DPIStopWorker(QObject):
    """Worker для асинхронной остановки DPI"""
    finished = pyqtSignal(bool, str)  # success, error_message
    progress = pyqtSignal(str)        # status_message
    
    def __init__(self, app_instance, launch_method):
        super().__init__()
        self.app_instance = app_instance
        self.launch_method = launch_method
    
    def run(self):
        try:
            self.progress.emit("Остановка DPI...")
            
            # Проверяем, запущен ли процесс
            if not self.app_instance.dpi_starter.check_process_running_wmi(silent=True):
                self.progress.emit("DPI уже остановлен")
                self.finished.emit(True, "DPI уже был остановлен")
                return
            
            self.progress.emit("Завершение процессов...")
            
            # Выбираем метод остановки
            if self.launch_method == "direct":
                success = self._stop_direct()
            else:
                success = self._stop_bat()
            
            if success:
                self.progress.emit("DPI успешно остановлен")
                self.finished.emit(True, "")
            else:
                self.finished.emit(False, "Не удалось полностью остановить процесс")
                
        except Exception as e:
            error_msg = f"Ошибка остановки DPI: {str(e)}"
            log(error_msg, "❌ ERROR")
            self.finished.emit(False, error_msg)
    
    def _stop_direct(self):
        """Остановка через новый метод"""
        try:
            from strategy_menu.strategy_runner import get_strategy_runner
            
            runner = get_strategy_runner(self.app_instance.dpi_starter.winws_exe)
            success = runner.stop()
            
            # Дополнительно убиваем все процессы winws.exe
            if not success or self.app_instance.dpi_starter.check_process_running_wmi(silent=True):
                import subprocess
                subprocess.run(
                    ["taskkill", "/F", "/IM", "winws.exe", "/T"],
                    capture_output=True,
                    creationflags=0x08000000  # CREATE_NO_WINDOW
                )
            
            # Проверяем результат
            return not self.app_instance.dpi_starter.check_process_running_wmi(silent=True)
            
        except Exception as e:
            log(f"Ошибка прямой остановки: {e}", "❌ ERROR")
            return False
    
    def _stop_bat(self):
        """Остановка через старый метод"""
        try:
            from dpi.stop import stop_dpi
            stop_dpi(self.app_instance)
            
            # Проверяем результат
            return not self.app_instance.dpi_starter.check_process_running_wmi(silent=True)
            
        except Exception as e:
            log(f"Ошибка остановки через .bat: {e}", "❌ ERROR")
            return False


class StopAndExitWorker(QObject):
    """Worker для остановки DPI и выхода из программы"""
    finished = pyqtSignal()
    progress = pyqtSignal(str)
    
    def __init__(self, app_instance):
        super().__init__()
        self.app_instance = app_instance
        self.launch_method = get_strategy_launch_method()
    
    def run(self):
        try:
            self.progress.emit("Остановка DPI перед закрытием...")
            
            # Выбираем метод остановки
            if self.launch_method == "direct":
                from strategy_menu.strategy_runner import get_strategy_runner
                runner = get_strategy_runner(self.app_instance.dpi_starter.winws_exe)
                runner.stop()
                
                # Дополнительная очистка
                from dpi.stop import stop_dpi_direct
                stop_dpi_direct(self.app_instance)
            else:
                from dpi.stop import stop_dpi
                stop_dpi(self.app_instance)
            
            self.progress.emit("Завершение работы...")
            self.finished.emit()
            
        except Exception as e:
            log(f"Ошибка при остановке перед закрытием: {e}", "❌ ERROR")
            self.finished.emit()


class DPIController:
    """Основной контроллер для управления DPI"""
    
    def __init__(self, app_instance):
        self.app = app_instance
        self._dpi_start_thread = None
        self._dpi_stop_thread = None
        self._stop_exit_thread = None
    
    def start_dpi_async(self, selected_mode=None):
        """Асинхронно запускает DPI без блокировки UI"""
        # Проверка на уже запущенный поток
        try:
            if self._dpi_start_thread and self._dpi_start_thread.isRunning():
                log("Запуск DPI уже выполняется", "DEBUG")
                return
        except RuntimeError:
            self._dpi_start_thread = None
        
        # Проверяем выбранный метод запуска
        launch_method = get_strategy_launch_method()
        log(f"Используется метод запуска: {launch_method}", "INFO")
        
        # Показываем состояние запуска
        method_name = "прямой" if launch_method == "direct" else "классический"
        self.app.set_status(f"🚀 Запуск DPI ({method_name} метод)...")
        
        # Блокируем кнопки во время операции
        if hasattr(self.app, 'start_btn'):
            self.app.start_btn.setEnabled(False)
        if hasattr(self.app, 'stop_btn'):
            self.app.stop_btn.setEnabled(False)
        
        # Создаем поток и worker
        self._dpi_start_thread = QThread()
        self._dpi_start_worker = DPIStartWorker(self.app, selected_mode, launch_method)
        self._dpi_start_worker.moveToThread(self._dpi_start_thread)
        
        # Подключение сигналов
        self._dpi_start_thread.started.connect(self._dpi_start_worker.run)
        self._dpi_start_worker.progress.connect(self.app.set_status)
        self._dpi_start_worker.finished.connect(self._on_dpi_start_finished)
        
        # Очистка ресурсов
        def cleanup_start_thread():
            try:
                if self._dpi_start_thread:
                    self._dpi_start_thread.quit()
                    self._dpi_start_thread.wait(2000)
                    self._dpi_start_thread = None
                    
                if hasattr(self, '_dpi_start_worker'):
                    self._dpi_start_worker.deleteLater()
                    self._dpi_start_worker = None
            except Exception as e:
                log(f"Ошибка при очистке потока запуска: {e}", "❌ ERROR")
        
        self._dpi_start_worker.finished.connect(cleanup_start_thread)
        
        # Запускаем поток
        self._dpi_start_thread.start()
        
        mode_name = selected_mode
        if isinstance(selected_mode, dict):
            mode_name = selected_mode.get('name', str(selected_mode))
        elif isinstance(selected_mode, tuple) and len(selected_mode) == 2:
            mode_name = selected_mode[1]
        
        log(f"Запуск асинхронного старта DPI: {mode_name} (метод: {method_name})", "INFO")
    
    def stop_dpi_async(self):
        """Асинхронно останавливает DPI без блокировки UI"""
        # Проверка на уже запущенный поток
        try:
            if self._dpi_stop_thread and self._dpi_stop_thread.isRunning():
                log("Остановка DPI уже выполняется", "DEBUG")
                return
        except RuntimeError:
            self._dpi_stop_thread = None
        
        launch_method = get_strategy_launch_method()
        
        # Показываем состояние остановки
        method_name = "прямой" if launch_method == "direct" else "классический"
        self.app.set_status(f"🛑 Остановка DPI ({method_name} метод)...")
        
        # Блокируем кнопки во время операции
        if hasattr(self.app, 'start_btn'):
            self.app.start_btn.setEnabled(False)
        if hasattr(self.app, 'stop_btn'):
            self.app.stop_btn.setEnabled(False)
        
        # Создаем поток и worker
        self._dpi_stop_thread = QThread()
        self._dpi_stop_worker = DPIStopWorker(self.app, launch_method)
        self._dpi_stop_worker.moveToThread(self._dpi_stop_thread)
        
        # Подключение сигналов
        self._dpi_stop_thread.started.connect(self._dpi_stop_worker.run)
        self._dpi_stop_worker.progress.connect(self.app.set_status)
        self._dpi_stop_worker.finished.connect(self._on_dpi_stop_finished)
        
        # Очистка ресурсов
        def cleanup_stop_thread():
            try:
                if self._dpi_stop_thread:
                    self._dpi_stop_thread.quit()
                    self._dpi_stop_thread.wait(2000)
                    self._dpi_stop_thread = None
                    
                if hasattr(self, '_dpi_stop_worker'):
                    self._dpi_stop_worker.deleteLater()
                    self._dpi_stop_worker = None
            except Exception as e:
                log(f"Ошибка при очистке потока остановки: {e}", "❌ ERROR")
        
        self._dpi_stop_worker.finished.connect(cleanup_stop_thread)
        
        # Устанавливаем флаг ручной остановки
        self.app.manually_stopped = True
        
        # Запускаем поток
        self._dpi_stop_thread.start()
        
        log(f"Запуск асинхронной остановки DPI (метод: {method_name})", "INFO")
    
    def stop_and_exit_async(self):
        """Асинхронно останавливает DPI и закрывает программу"""
        self.app._is_exiting = True
        
        # Создаем worker и поток
        self._stop_exit_thread = QThread()
        self._stop_exit_worker = StopAndExitWorker(self.app)
        self._stop_exit_worker.moveToThread(self._stop_exit_thread)
        
        # Подключаем сигналы
        self._stop_exit_thread.started.connect(self._stop_exit_worker.run)
        self._stop_exit_worker.progress.connect(self.app.set_status)
        self._stop_exit_worker.finished.connect(self._on_stop_and_exit_finished)
        self._stop_exit_worker.finished.connect(self._stop_exit_thread.quit)
        self._stop_exit_worker.finished.connect(self._stop_exit_worker.deleteLater)
        self._stop_exit_thread.finished.connect(self._stop_exit_thread.deleteLater)
        
        # Запускаем поток
        self._stop_exit_thread.start()
    
    def _on_dpi_start_finished(self, success, error_message):
        """Обрабатывает завершение асинхронного запуска DPI"""
        try:
            # Восстанавливаем кнопки
            if hasattr(self.app, 'start_btn'):
                self.app.start_btn.setEnabled(True)
            if hasattr(self.app, 'stop_btn'):
                self.app.stop_btn.setEnabled(True)
            
            if success:
                log("DPI запущен асинхронно", "INFO")
                self.app.set_status("✅ DPI успешно запущен")
                
                # Обновляем UI
                self.app.update_ui(running=True)
                
                # Обновляем статус процесса
                self.app.on_process_status_changed(True)
                
                # Устанавливаем флаг намеренного запуска
                self.app.intentional_start = True
                
                # Перезапускаем Discord если нужно
                from discord.discord_restart import get_discord_restart_setting
                if not self.app.first_start and get_discord_restart_setting():
                    self.app.discord_manager.restart_discord_if_running()
                else:
                    self.app.first_start = False
                    
            else:
                log(f"Ошибка асинхронного запуска DPI: {error_message}", "❌ ERROR")
                self.app.set_status(f"❌ Ошибка запуска: {error_message}")
                
                # Обновляем UI как неактивный
                self.app.update_ui(running=False)
                self.app.on_process_status_changed(False)
                
        except Exception as e:
            log(f"Ошибка при обработке результата запуска DPI: {e}", "❌ ERROR")
            self.app.set_status(f"Ошибка: {e}")
    
    def _on_dpi_stop_finished(self, success, error_message):
        """Обрабатывает завершение асинхронной остановки DPI"""
        try:
            # Восстанавливаем кнопки
            if hasattr(self.app, 'start_btn'):
                self.app.start_btn.setEnabled(True)
            if hasattr(self.app, 'stop_btn'):
                self.app.stop_btn.setEnabled(True)
            
            if success:
                log("DPI остановлен асинхронно", "INFO")
                if error_message:
                    self.app.set_status(f"✅ {error_message}")
                else:
                    self.app.set_status("✅ DPI успешно остановлен")
                
                # Обновляем UI
                self.app.update_ui(running=False)
                
                # Обновляем статус процесса
                self.app.on_process_status_changed(False)
                
            else:
                log(f"Ошибка асинхронной остановки DPI: {error_message}", "❌ ERROR")
                self.app.set_status(f"❌ Ошибка остановки: {error_message}")
                
                # Проверяем реальный статус процесса
                is_running = self.app.dpi_starter.check_process_running_wmi(silent=True)
                self.app.update_ui(running=is_running)
                self.app.on_process_status_changed(is_running)
                
        except Exception as e:
            log(f"Ошибка при обработке результата остановки DPI: {e}", "❌ ERROR")
            self.app.set_status(f"Ошибка: {e}")
    
    def _on_stop_and_exit_finished(self):
        """Завершает приложение после остановки DPI"""
        self.app.set_status("Завершение...")
        from PyQt6.QtWidgets import QApplication
        QApplication.quit()
    
    def cleanup_threads(self):
        """Очищает все потоки при закрытии приложения"""
        try:
            if self._dpi_start_thread and self._dpi_start_thread.isRunning():
                self._dpi_start_thread.quit()
                self._dpi_start_thread.wait(1000)
            
            if self._dpi_stop_thread and self._dpi_stop_thread.isRunning():
                self._dpi_stop_thread.quit()
                self._dpi_stop_thread.wait(1000)
        except Exception as e:
            log(f"Ошибка при очистке потоков DPI контроллера: {e}", "❌ ERROR")