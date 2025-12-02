# managers/update_manager.py
"""
════════════════════════════════════════════════════════════════════════════════
UpdateManager - Фоновая проверка обновлений после загрузки GUI
════════════════════════════════════════════════════════════════════════════════

Менеджер для запуска проверки обновлений ТОЛЬКО после того, как GUI полностью
загрузился и готов к работе. Вся работа выполняется в фоне без блокировки UI.
"""

from PyQt6.QtCore import QObject, QThread, QTimer, pyqtSignal
from log import log
from typing import Optional, Callable


class UpdateCheckWorker(QObject):
    """
    Воркер для фоновой проверки обновлений.
    Выполняет проверку в отдельном потоке и эмитит результаты.
    """
    
    # Сигналы
    progress = pyqtSignal(str)              # Статус проверки
    update_available = pyqtSignal(dict)     # Найдено обновление (release_info)
    no_update = pyqtSignal(str)             # Обновлений нет (текущая версия)
    check_failed = pyqtSignal(str)          # Ошибка проверки
    finished = pyqtSignal(bool)             # Завершено (успех/неудача)
    
    def __init__(self, silent: bool = True):
        super().__init__()
        self._silent = silent
        self._cancelled = False
    
    def cancel(self):
        """Отменить проверку"""
        self._cancelled = True
    
    def run(self):
        """Основная логика проверки обновлений"""
        try:
            if self._cancelled:
                self.finished.emit(False)
                return
            
            self.progress.emit("🔄 Проверка обновлений...")
            log("🔄 UpdateCheckWorker: начало проверки обновлений", "🔄 UPDATE")
            
            # ═══════════════════════════════════════════════════════════════
            # 1. Проверяем настройку автообновлений
            # ═══════════════════════════════════════════════════════════════
            from config import get_auto_update_enabled
            
            if self._silent and not get_auto_update_enabled():
                log("Автоматическая проверка обновлений отключена пользователем", "🔄 UPDATE")
                self.progress.emit("Автообновления отключены")
                self.finished.emit(False)
                return
            
            # ═══════════════════════════════════════════════════════════════
            # 2. Проверяем rate limit
            # ═══════════════════════════════════════════════════════════════
            from updater import UpdateRateLimiter
            
            can_check, error_msg = UpdateRateLimiter.can_check_update(is_auto=self._silent)
            
            if not can_check:
                log(f"⏱️ Проверка заблокирована rate limiter: {error_msg}", "🔄 UPDATE")
                self.progress.emit(error_msg or "Проверка обновлений отложена")
                self.finished.emit(False)
                return
            
            # Записываем факт проверки
            UpdateRateLimiter.record_check(is_auto=self._silent)
            
            # ═══════════════════════════════════════════════════════════════
            # 3. Получаем информацию о релизе
            # ═══════════════════════════════════════════════════════════════
            from config import CHANNEL, APP_VERSION
            from updater import get_latest_release
            from updater.github_release import normalize_version
            
            # Автообновления используют кэш, ручные — нет
            use_cache = self._silent
            
            log(f"🔄 Проверка канала {CHANNEL}, use_cache={use_cache}", "🔄 UPDATE")
            
            release_info = get_latest_release(CHANNEL, use_cache=use_cache)
            
            if not release_info:
                error = "Не удалось получить информацию о релизе"
                log(f"❌ {error}", "🔄 UPDATE")
                self.progress.emit(error)
                self.check_failed.emit(error)
                self.finished.emit(False)
                return
            
            # ═══════════════════════════════════════════════════════════════
            # 4. Сравниваем версии
            # ═══════════════════════════════════════════════════════════════
            new_ver = release_info.get("version", "0.0.0")
            
            try:
                app_ver_norm = normalize_version(APP_VERSION)
            except ValueError as e:
                log(f"❌ Неверный формат APP_VERSION: {APP_VERSION}", "🔄 UPDATE")
                self.check_failed.emit(f"Ошибка версии: {e}")
                self.finished.emit(False)
                return
            
            from updater.update import compare_versions
            cmp_result = compare_versions(app_ver_norm, new_ver)
            
            log(f"🔄 Сравнение версий: local={app_ver_norm}, remote={new_ver}, result={cmp_result}", "🔄 UPDATE")
            
            # ═══════════════════════════════════════════════════════════════
            # 5. Возвращаем результат
            # ═══════════════════════════════════════════════════════════════
            if cmp_result >= 0:
                # Установлена актуальная или более новая версия
                msg = f"✅ Обновлений нет (v{app_ver_norm})"
                log(msg, "🔄 UPDATE")
                self.progress.emit(msg)
                self.no_update.emit(app_ver_norm)
                self.finished.emit(False)
            else:
                # Доступна новая версия
                log(f"🆕 Доступна новая версия: {new_ver}", "🔄 UPDATE")
                self.progress.emit(f"🆕 Доступна версия {new_ver}")
                self.update_available.emit(release_info)
                self.finished.emit(True)
                
        except Exception as e:
            error_msg = f"Ошибка проверки обновлений: {e}"
            log(f"❌ {error_msg}", "🔄 UPDATE")
            import traceback
            log(traceback.format_exc(), "DEBUG")
            
            self.progress.emit(f"❌ {e}")
            self.check_failed.emit(str(e))
            self.finished.emit(False)


class UpdateManager(QObject):
    """
    Менеджер фоновой проверки обновлений.
    
    Запускается ТОЛЬКО после полной загрузки GUI.
    Вся работа выполняется в отдельном потоке.
    """
    
    # Публичные сигналы для подключения UI
    status_changed = pyqtSignal(str)        # Изменение статуса
    update_available = pyqtSignal(dict)     # Доступно обновление
    check_completed = pyqtSignal(bool)      # Проверка завершена
    
    def __init__(self, app_instance):
        super().__init__()
        self.app = app_instance
        
        # Состояние
        self._check_thread: Optional[QThread] = None
        self._check_worker: Optional[UpdateCheckWorker] = None
        self._is_checking = False
        self._check_count = 0
        
        # Задержка перед первой проверкой (после загрузки GUI)
        self._initial_delay_ms = 3000  # 3 секунды
        
        # Интервал периодической проверки (только для текущей сессии)
        self._periodic_check_interval_ms = 6 * 60 * 60 * 1000  # 6 часов
        
        # Таймеры
        self._initial_timer: Optional[QTimer] = None
        self._periodic_timer: Optional[QTimer] = None
        
        log("📦 UpdateManager: инициализирован", "DEBUG")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Публичные методы
    # ═══════════════════════════════════════════════════════════════════════════
    
    def start_background_check(self, delay_ms: int = None):
        """
        Запуск фоновой проверки обновлений с опциональной задержкой.
        
        Args:
            delay_ms: Задержка перед проверкой (мс). Если None, используется _initial_delay_ms
        """
        delay = delay_ms if delay_ms is not None else self._initial_delay_ms
        
        log(f"📦 UpdateManager: запланирована фоновая проверка через {delay}мс", "DEBUG")
        
        if self._initial_timer:
            self._initial_timer.stop()
            self._initial_timer.deleteLater()
        
        self._initial_timer = QTimer()
        self._initial_timer.setSingleShot(True)
        self._initial_timer.timeout.connect(lambda: self._run_check(silent=True))
        self._initial_timer.start(delay)
    
    def check_now(self, silent: bool = False):
        """
        Немедленная проверка обновлений.
        
        Args:
            silent: True для тихой проверки (без диалогов)
        """
        if self._is_checking:
            log("📦 UpdateManager: проверка уже выполняется", "DEBUG")
            return
        
        self._run_check(silent=silent)
    
    def start_periodic_checks(self):
        """Запуск периодических проверок обновлений (раз в 6 часов)"""
        if self._periodic_timer:
            return  # Уже запущен
        
        self._periodic_timer = QTimer()
        self._periodic_timer.timeout.connect(lambda: self._run_check(silent=True))
        self._periodic_timer.start(self._periodic_check_interval_ms)
        
        log(f"📦 UpdateManager: периодические проверки запущены (каждые {self._periodic_check_interval_ms // 3600000}ч)", "DEBUG")
    
    def stop_periodic_checks(self):
        """Остановка периодических проверок"""
        if self._periodic_timer:
            self._periodic_timer.stop()
            self._periodic_timer.deleteLater()
            self._periodic_timer = None
            log("📦 UpdateManager: периодические проверки остановлены", "DEBUG")
    
    def cancel_check(self):
        """Отменить текущую проверку"""
        if self._check_worker:
            self._check_worker.cancel()
            log("📦 UpdateManager: проверка отменена", "DEBUG")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Приватные методы
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _run_check(self, silent: bool = True):
        """
        Запуск проверки обновлений в фоновом потоке.
        
        Args:
            silent: True для тихой проверки
        """
        if self._is_checking:
            log("📦 UpdateManager: пропуск - проверка уже запущена", "DEBUG")
            return
        
        self._is_checking = True
        self._check_count += 1
        
        log(f"📦 UpdateManager: запуск проверки #{self._check_count} (silent={silent})", "🔄 UPDATE")
        
        # Создаем поток
        self._check_thread = QThread()
        self._check_worker = UpdateCheckWorker(silent=silent)
        self._check_worker.moveToThread(self._check_thread)
        
        # Подключаем сигналы worker -> manager
        self._check_worker.progress.connect(self._on_progress)
        self._check_worker.update_available.connect(self._on_update_available)
        self._check_worker.no_update.connect(self._on_no_update)
        self._check_worker.check_failed.connect(self._on_check_failed)
        self._check_worker.finished.connect(self._on_finished)
        
        # Управление потоком
        self._check_thread.started.connect(self._check_worker.run)
        self._check_worker.finished.connect(self._check_thread.quit)
        self._check_worker.finished.connect(self._check_worker.deleteLater)
        self._check_thread.finished.connect(self._check_thread.deleteLater)
        self._check_thread.finished.connect(self._on_thread_finished)
        
        # Запуск
        self._check_thread.start()
    
    def _on_progress(self, message: str):
        """Обработка статуса проверки"""
        self.status_changed.emit(message)
        
        # Обновляем статус в приложении
        if hasattr(self.app, 'set_status'):
            try:
                self.app.set_status(message)
            except Exception:
                pass
    
    def _on_update_available(self, release_info: dict):
        """Обработка найденного обновления"""
        version = release_info.get('version', 'unknown')
        log(f"📦 UpdateManager: обнаружено обновление v{version}", "🔄 UPDATE")
        
        self.update_available.emit(release_info)
        
        # Запускаем диалог обновления
        self._start_update_process(release_info)
    
    def _on_no_update(self, current_version: str):
        """Обработка случая когда обновлений нет"""
        log(f"📦 UpdateManager: обновлений нет (v{current_version})", "🔄 UPDATE")
        self.check_completed.emit(False)
    
    def _on_check_failed(self, error: str):
        """Обработка ошибки проверки"""
        log(f"📦 UpdateManager: ошибка проверки - {error}", "🔄 UPDATE")
        self.check_completed.emit(False)
    
    def _on_finished(self, has_update: bool):
        """Обработка завершения проверки"""
        log(f"📦 UpdateManager: проверка завершена, has_update={has_update}", "DEBUG")
        self._is_checking = False
        self.check_completed.emit(has_update)
    
    def _on_thread_finished(self):
        """Очистка после завершения потока"""
        self._check_thread = None
        self._check_worker = None
    
    def _start_update_process(self, release_info: dict):
        """
        Запуск процесса обновления (скачивание и установка).
        Использует существующую инфраструктуру из updater.update.
        """
        try:
            from updater import run_update_async
            
            log(f"📦 UpdateManager: запуск процесса обновления", "🔄 UPDATE")
            
            # run_update_async создает свой воркер и поток
            # silent=True чтобы не показывать повторный диалог подтверждения
            # (мы уже знаем что обновление доступно)
            thread = run_update_async(parent=self.app, silent=True)
            
            # Сохраняем ссылки чтобы поток не был уничтожен
            if not hasattr(self.app, '_update_threads'):
                self.app._update_threads = []
            self.app._update_threads.append(thread)
            
            # Очистка после завершения
            def cleanup():
                if thread in self.app._update_threads:
                    self.app._update_threads.remove(thread)
            
            thread.finished.connect(cleanup)
            
        except Exception as e:
            log(f"📦 UpdateManager: ошибка запуска обновления - {e}", "❌ ERROR")
            import traceback
            log(traceback.format_exc(), "DEBUG")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Очистка
    # ═══════════════════════════════════════════════════════════════════════════
    
    def cleanup(self):
        """Очистка ресурсов при закрытии приложения"""
        log("📦 UpdateManager: очистка ресурсов", "DEBUG")
        
        # Останавливаем таймеры
        if self._initial_timer:
            self._initial_timer.stop()
            self._initial_timer.deleteLater()
            self._initial_timer = None
        
        self.stop_periodic_checks()
        
        # Отменяем текущую проверку
        self.cancel_check()
        
        # Ждем завершения потока
        if self._check_thread and self._check_thread.isRunning():
            self._check_thread.quit()
            self._check_thread.wait(2000)

