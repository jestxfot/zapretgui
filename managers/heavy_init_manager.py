from PyQt6.QtCore import QThread, QTimer
from log import log
import os


class HeavyInitManager:
    """Менеджер для управления тяжелой инициализацией"""
    
    def __init__(self, app_instance):
        self.app = app_instance
        self._heavy_init_started = False
        self._heavy_init_thread = None
        self.heavy_worker = None
        
        # Мапинг прогресса для splash screen
        self.progress_map = {
            "Проверка интернет-соединения...": (15, "🌐 Проверка соединения..."),
            "Работаем в автономном режиме": (20, "📴 Автономный режим"),
            "Проверка winws.exe...": (25, "🔍 Проверка winws.exe..."),
            "Загрузка стратегий...": (30, "📦 Загрузка стратегий..."),
            "Обновление списка стратегий...": (35, "📋 Обновление списка..."),
            "Загрузка ресурсов...": (40, "📂 Загрузка ресурсов..."),
            "Обновление ресурсов...": (50, "🔄 Обновление ресурсов...")
        }

    def start_heavy_init(self):
        """Запуск тяжелой инициализации с прогресс-баром"""
        
        # ЗАЩИТА от двойного вызова
        if self._heavy_init_started:
            log("🔵 HeavyInitManager: уже запущен, пропускаем", "⚠ WARNING")
            return
        
        self._heavy_init_started = True
        log("🔵 HeavyInitManager: запуск тяжелой инициализации", "DEBUG")
        
        # Показываем прогресс-бар
        if hasattr(self.app, 'init_progress_bar'):
            self.app.init_progress_bar.show_animated()
            self.app.init_progress_bar.set_progress(0, "🚀 Начинаем инициализацию...")
        
        try:
            log("🔵 Создаем QThread для HeavyInit", "DEBUG")
            self._heavy_init_thread = QThread()
            
            log("🔵 Создаем HeavyInitWorker", "DEBUG")
            from heavy_init_worker import HeavyInitWorker
            
            self.heavy_worker = HeavyInitWorker(
                self.app.dpi_starter if hasattr(self.app, 'dpi_starter') else None,
                getattr(self.app, 'download_urls', [])
            )
            
            log("🔵 Перемещаем worker в поток", "DEBUG")
            self.heavy_worker.moveToThread(self._heavy_init_thread)
            
            # Подключаем сигналы
            self._heavy_init_thread.started.connect(self.heavy_worker.run)
            self.heavy_worker.progress.connect(self._on_heavy_progress)
            self.heavy_worker.finished.connect(self._on_heavy_done)
            self.heavy_worker.finished.connect(self._heavy_init_thread.quit)
            
            log("Запускаем HeavyInit поток...", "DEBUG")
            self._heavy_init_thread.start()
            
        except Exception as e:
            log(f"🔵 Ошибка в HeavyInitManager: {e}", "❌ ERROR")
            self._heavy_init_started = False
            
            if hasattr(self.app, 'init_progress_bar'):
                self.app.init_progress_bar.set_progress(0, "❌ Ошибка инициализации")
                QTimer.singleShot(2000, self.app.init_progress_bar.hide_animated)
            
            import traceback
            log(f"Traceback: {traceback.format_exc()}", "❌ ERROR")

    def check_local_files(self):
        """Проверяет наличие критически важных локальных файлов"""
        from config import WINWS_EXE
        
        if not os.path.exists(WINWS_EXE):
            self.app.set_status("❌ winws.exe не найден - включите автозагрузку")
            return False
        
        self.app.set_status("✅ Локальные файлы найдены")
        return True

    def start_auto_update(self):
        """✅ НОВЫЙ ПУБЛИЧНЫЙ МЕТОД: Запуск автообновления"""
        self._start_auto_update()

    def _on_heavy_progress(self, message: str):
        """Обработка прогресса от HeavyInitWorker"""
        log(f"HeavyInit прогресс: {message}", "DEBUG")
        
        if hasattr(self.app, 'splash') and self.app.splash:
            if message in self.progress_map:
                value, display_text = self.progress_map[message]
                self.app.splash.set_progress(value, display_text, message)
            else:
                self.app.splash.set_detail(message)
        
        self.app.set_status(message)

    def _on_heavy_done(self, success: bool, error_msg: str):
        """Обработка завершения HeavyInit"""
        log("🔵 HeavyInitManager: завершение тяжелой инициализации", "DEBUG")
        
        self._heavy_init_started = False
        
        if success:
            self._handle_successful_init()
        else:
            self._handle_failed_init(error_msg)

    def _handle_successful_init(self):
        """Обработка успешной инициализации"""
        # Обновляем прогресс
        if hasattr(self.app, 'splash') and self.app.splash:
            self.app.splash.set_progress(75, "Подготовка к запуску...", "Почти готово...")
        
        # Безопасная проверка strategy_manager
        if hasattr(self.app, 'strategy_manager') and self.app.strategy_manager:
            log(f"🔵 strategy_manager.already_loaded = {self.app.strategy_manager.already_loaded}", "DEBUG")
            
            if self.app.strategy_manager.already_loaded:
                log("🔵 Вызываем update_strategies_list через UI Manager", "DEBUG")
                # ✅ ИСПОЛЬЗУЕМ UI MANAGER
                if hasattr(self.app, 'ui_manager'):
                    self.app.ui_manager.update_strategies_list()
                log("🔵 update_strategies_list завершен", "DEBUG")
        else:
            log("🔵 strategy_manager не инициализирован!", "⚠ WARNING")

        # Автозапуск DPI если настроен через DPI Manager
        log("🔵 Вызываем delayed_dpi_start через DPI Manager", "DEBUG")
        if hasattr(self.app, 'dpi_manager'):
            self.app.dpi_manager.delayed_dpi_start()
        log("🔵 delayed_dpi_start завершен", "DEBUG")
        
        # Обновление UI через UI Manager
        log("🔵 Вызываем update_proxy_button_state через UI Manager", "DEBUG")
        if hasattr(self.app, 'ui_manager'):
            self.app.ui_manager.update_proxy_button_state()
        log("🔵 update_proxy_button_state завершен", "DEBUG")

        # combobox-фикс через UI Manager
        for delay in (0, 100, 200):
            QTimer.singleShot(delay, lambda: (
                self.app.ui_manager.force_enable_combos() 
                if hasattr(self.app, 'ui_manager') else None
            ))

        self.app.set_status("Инициализация завершена")
        
        # Запускаем проверку обновлений через 2 секунды
        QTimer.singleShot(2000, self._start_auto_update)
        
        log("🔵 HeavyInitManager: успешно завершен", "DEBUG")

    def _handle_failed_init(self, error_msg: str):
        """Обработка неуспешной инициализации"""
        # Показываем ошибку и закрываем splash
        if hasattr(self.app, 'splash') and self.app.splash:
            self.app.splash.show_error(error_msg)
        
        log(f"HeavyInit завершился с ошибкой: {error_msg}", "❌ ERROR")

    def _start_auto_update(self):
        """Плановая (тихая) проверка обновлений в фоне"""
        self.app.set_status("Плановая проверка обновлений…")
        
        # Обновляем splash если он еще есть
        if hasattr(self.app, 'splash') and self.app.splash:
            self.app.splash.set_progress(85, "Проверка обновлений...", "")

        try:
            from updater import run_update_async
        except Exception as e:
            log(f"Auto-update: import error {e}", "❌ ERROR")
            self.app.set_status("Не удалось запустить авто-апдейт")
            return

        thread = run_update_async(parent=self.app, silent=True)
        
        if not hasattr(thread, '_worker'):
            log("Auto-update: worker not found in thread", "❌ ERROR")
            self.app.set_status("Ошибка проверки обновлений")
            return
            
        worker = thread._worker

        def _upd_done(ok: bool):
            if ok:
                self.app.set_status("🔄 Обновление установлено – Zapret перезапустится")
            else:
                self.app.set_status("✅ Обновлений нет")
            log(f"Auto-update finished, ok={ok}", "DEBUG")

            if hasattr(self.app, "_auto_upd_thread"):
                del self.app._auto_upd_thread
            if hasattr(self.app, "_auto_upd_worker"):
                del self.app._auto_upd_worker

        worker.finished.connect(_upd_done)

        self.app._auto_upd_thread = thread
        self.app._auto_upd_worker = worker

    def cleanup(self):
        """Очистка ресурсов при закрытии приложения"""
        try:
            if self._heavy_init_thread and self._heavy_init_thread.isRunning():
                self._heavy_init_thread.quit()
                self._heavy_init_thread.wait(1000)
            
            if self.heavy_worker:
                self.heavy_worker.deleteLater()
                
        except Exception as e:
            log(f"Ошибка при очистке HeavyInitManager: {e}", "DEBUG")