# dns/dns_worker.py
from PyQt6.QtCore import QThread, QObject, pyqtSignal, QEventLoop, QTimer
from log import log
import time
import sys
import traceback

class SafeDNSWorker(QThread):
    """Безопасный воркер для DNS операций с защитой от крашей"""
    status_update = pyqtSignal(str)
    finished_with_result = pyqtSignal(bool)
    
    def __init__(self, skip_on_startup=False):
        super().__init__()
        self.skip_on_startup = skip_on_startup
        
    def run(self):
        """Безопасное выполнение DNS операций"""
        try:
            log("🔵 SafeDNSWorker: начало работы", "DEBUG")
            
            # ЗАЩИТА: Добавляем задержку при запуске
            if self.skip_on_startup:
                log("⏳ Задержка DNS операций при запуске на 3 секунды", "INFO")
                time.sleep(3)
            
            # ЗАЩИТА: Проверяем что модули доступны
            try:
                from .dns_force import ensure_default_force_dns, DNSForceManager
            except ImportError as e:
                log(f"❌ Не удалось импортировать DNS модули: {e}", "❌ ERROR")
                self.status_update.emit("❌ DNS модули недоступны")
                self.finished_with_result.emit(False)
                return
            
            # Создаём ключ если нет
            try:
                ensure_default_force_dns()
            except Exception as e:
                log(f"⚠ Не удалось создать ключ DNS: {e}", "⚠ WARNING")
            
            # ЗАЩИТА: Используем синхронный manager вместо асинхронного
            try:
                manager = DNSForceManager()
            except Exception as e:
                log(f"❌ Не удалось создать DNSForceManager: {e}", "❌ ERROR")
                self.status_update.emit("❌ Ошибка инициализации DNS")
                self.finished_with_result.emit(False)
                return
            
            # Проверяем, включен ли force DNS
            try:
                if not manager.is_force_dns_enabled():
                    self.status_update.emit("ℹ️ Принудительный DNS отключен")
                    log("Принудительный DNS отключен в настройках", "INFO")
                    self.finished_with_result.emit(False)
                    return
            except Exception as e:
                log(f"❌ Ошибка проверки состояния DNS: {e}", "❌ ERROR")
                self.finished_with_result.emit(False)
                return
            
            # ЗАЩИТА: Выполняем установку DNS в защищенном режиме
            self.status_update.emit("⏳ Применение DNS настроек...")
            
            try:
                # Используем синхронную версию с ограничениями
                success_count, total_count = manager.force_dns_on_all_adapters(
                    include_disconnected=False,  # Только подключенные адаптеры
                    enable_ipv6=False  # Отключаем IPv6 для безопасности
                )
                
                if success_count > 0:
                    self.status_update.emit(f"✅ DNS применен: {success_count}/{total_count} адаптеров")
                    self.finished_with_result.emit(True)
                else:
                    self.status_update.emit("⚠️ DNS не удалось применить")
                    self.finished_with_result.emit(False)
                    
            except Exception as e:
                log(f"❌ Ошибка применения DNS: {e}", "❌ ERROR")
                self.status_update.emit(f"❌ Ошибка: {str(e)[:50]}")
                self.finished_with_result.emit(False)
                
        except Exception as e:
            log(f"❌ Критическая ошибка в DNS worker: {e}", "❌ ERROR")
            log(f"Traceback: {traceback.format_exc()}", "❌ ERROR")
            try:
                self.status_update.emit("❌ Критическая ошибка DNS")
            except:
                pass
            self.finished_with_result.emit(False)


class DNSUIManager:
    """Безопасный менеджер UI для DNS операций"""
    
    def __init__(self, parent, status_callback=None):
        self.parent = parent
        self.status_callback = status_callback or (lambda msg: None)
        self.dns_worker = None
        self.startup_protection = True  # Защита от крашей при запуске
    
    def apply_dns_settings_async(self, skip_on_startup=False):
        """Безопасно применяет DNS настройки"""
        try:
            # Проверяем, не запущен ли уже worker
            if self.dns_worker and self.dns_worker.isRunning():
                log("DNS worker уже запущен, пропускаем", "⚠ WARNING")
                return False
            
            log("🔵 Запуск безопасного DNS worker", "DEBUG")
            
            # Создаем безопасный worker
            self.dns_worker = SafeDNSWorker(skip_on_startup=skip_on_startup)
            
            # Подключаем сигналы с защитой
            try:
                self.dns_worker.status_update.connect(self._safe_status_update)
                self.dns_worker.finished_with_result.connect(self._safe_dns_finished)
            except Exception as e:
                log(f"⚠ Ошибка подключения сигналов: {e}", "⚠ WARNING")
            
            # Запускаем worker
            self.dns_worker.start()
            
            self._safe_status_update("⏳ Запуск DNS настроек...")
            return True
            
        except Exception as e:
            log(f"❌ Ошибка при запуске DNS worker: {e}", "❌ ERROR")
            self._safe_status_update(f"❌ Ошибка DNS")
            return False
    
    def _safe_status_update(self, msg):
        """Безопасное обновление статуса"""
        try:
            if self.status_callback:
                self.status_callback(msg)
        except Exception as e:
            log(f"Ошибка обновления статуса: {e}", "DEBUG")
    
    def _safe_dns_finished(self, success):
        """Безопасный обработчик завершения DNS операции"""
        try:
            if success:
                self._safe_status_update("✅ DNS настройки применены")
                log("DNS настройки успешно применены", "✅ SUCCESS")
            else:
                self._safe_status_update("⚠️ DNS настройки не применены")
                log("DNS настройки не применены", "⚠ WARNING")
            
            # Безопасная очистка worker
            self._cleanup_worker()
                
        except Exception as e:
            log(f"Ошибка в обработчике DNS: {e}", "DEBUG")
    
    def _cleanup_worker(self):
        """Безопасная очистка worker"""
        try:
            if self.dns_worker:
                if self.dns_worker.isRunning():
                    self.dns_worker.quit()
                    if not self.dns_worker.wait(500):  # Ждем только 500мс
                        log("DNS worker не завершился вовремя", "DEBUG")
                
                self.dns_worker.deleteLater()
                self.dns_worker = None
        except Exception as e:
            log(f"Ошибка очистки DNS worker: {e}", "DEBUG")
    
    def cleanup(self):
        """Очистка ресурсов"""
        self._cleanup_worker()


class DNSStartupManager:
    """Безопасный менеджер для применения DNS при запуске"""
    
    # Флаг для предотвращения DNS при запуске (временное решение)
    DISABLE_ON_STARTUP = False  # ← УСТАНОВИТЕ В True ЧТОБЫ ВРЕМЕННО ОТКЛЮЧИТЬ
    
    @staticmethod
    def apply_dns_on_startup_async(status_callback=None):
        """Безопасно применяет DNS настройки при запуске"""
        try:
            # ВРЕМЕННОЕ РЕШЕНИЕ: Полностью отключаем DNS при запуске
            if DNSStartupManager.DISABLE_ON_STARTUP:
                log("⚠️ DNS при запуске временно отключен для предотвращения крашей", "⚠ WARNING")
                if status_callback:
                    status_callback("DNS при запуске отключен")
                return False
            
            log("Отложенное применение DNS при запуске", "INFO")
            
            # Используем QTimer для отложенного запуска
            def delayed_dns_apply():
                try:
                    from .dns_force import DNSForceManager
                    
                    manager = DNSForceManager()
                    if not manager.is_force_dns_enabled():
                        log("DNS отключен в настройках", "INFO")
                        return
                    
                    # Применяем с ограничениями
                    success, total = manager.force_dns_on_all_adapters(
                        include_disconnected=False,
                        enable_ipv6=False
                    )
                    
                    if success > 0:
                        log(f"✅ DNS применен при запуске: {success}/{total}", "✅ SUCCESS")
                        if status_callback:
                            status_callback(f"✅ DNS применен: {success}/{total}")
                    else:
                        log("⚠️ DNS не применен при запуске", "⚠ WARNING")
                        
                except Exception as e:
                    log(f"❌ Ошибка отложенного DNS: {e}", "❌ ERROR")
            
            # Запускаем через 5 секунд после старта
            QTimer.singleShot(5000, delayed_dns_apply)
            
            if status_callback:
                status_callback("DNS будет применен через 5 секунд")
            
            return True
            
        except Exception as e:
            log(f"❌ Ошибка DNS при запуске: {e}", "❌ ERROR")
            if status_callback:
                status_callback("❌ Ошибка DNS")
            return False


# Функция для безопасного отключения DNS если есть проблемы
def disable_dns_if_crashing():
    """Аварийное отключение DNS если обнаружены краши"""
    try:
        import winreg
        path = r"Software\ZapretReg2"
        
        # Читаем счетчик крашей
        crash_count = 0
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path) as key:
                crash_count, _ = winreg.QueryValueEx(key, "DNSCrashCount")
        except:
            pass
        
        # Если больше 3 крашей - отключаем DNS
        if crash_count > 3:
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, path) as key:
                winreg.SetValueEx(key, "ForceDNS", 0, winreg.REG_DWORD, 0)
                winreg.DeleteValue(key, "DNSCrashCount")
            log("⚠️ DNS автоматически отключен после множественных крашей", "⚠ WARNING")
            return True
            
        # Увеличиваем счетчик
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, path) as key:
            winreg.SetValueEx(key, "DNSCrashCount", 0, winreg.REG_DWORD, crash_count + 1)
            
    except Exception as e:
        log(f"Ошибка в disable_dns_if_crashing: {e}", "DEBUG")
    
    return False


# Вызовите эту функцию при успешном запуске чтобы сбросить счетчик
def reset_crash_counter():
    """Сбрасывает счетчик крашей после успешного запуска"""
    try:
        import winreg
        path = r"Software\ZapretReg2"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_SET_VALUE) as key:
            try:
                winreg.DeleteValue(key, "DNSCrashCount")
            except:
                pass
    except:
        pass