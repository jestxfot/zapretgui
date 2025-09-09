# managers/initialization_manager.py

from PyQt6.QtCore import QTimer, QThread, QObject, pyqtSignal
from log import log


class InitializationManager:
    """
    Менеджер управления асинхронной инициализацией приложения.
    Делает плановую загрузку компонентов и выполняет «мягкую» верификацию
    (несколько попыток с дедлайном), чтобы избежать ложных предупреждений.
    """

    def __init__(self, app_instance):
        self.app = app_instance
        self.init_tasks_completed = set()

        # Служебные флаги/счетчики для мягкой верификации
        self._verify_done = False
        self._verify_attempts = 0
        self._verify_max_attempts = 8       # Максимум 8 попыток
        self._verify_interval_ms = 1000     # Интервал 1 сек
        self._verify_timer_started = False
        self._post_init_scheduled = False

        # Для фоновой проверки ipsets, чтобы можно было корректно завершить поток
        self._ipsets_thread = None

    # ───────────────────────── запуск и планирование ─────────────────────────

    def run_async_init(self):
        """Полностью асинхронная инициализация"""
        log("🟡 InitializationManager: начало асинхронной инициализации", "DEBUG")

        # Показываем начальный статус
        self.app.set_status("Инициализация компонентов...")

        # Все операции запускаем с небольшой задержкой, чтобы не блокировать UI
        init_tasks = [
            (0,   self._init_dpi_starter),
            (10,  self._init_hostlists_check),
            (20,  self._init_ipsets_check),
            (30,  self._init_dpi_controller),
            (40,  self._init_menu),
            (50,  self._connect_signals),
            (100, self._initialize_managers_and_services),
            (150, self._init_tray),
            (200, self._init_logger),
        ]

        for delay, task in init_tasks:
            log(f"🟡 Планируем {task.__name__} через {delay}ms", "DEBUG")
            QTimer.singleShot(delay, task)

        # Вместо жестких 2 секунд — «мягкая» верификация с повторами
        if not self._verify_timer_started:
            self._verify_timer_started = True
            QTimer.singleShot(1500, self._verify_initialization)  # первая попытка через 1.5с

    # ───────────────────────── инициализация подсистем ───────────────────────

    def _init_strategy_manager(self):
        """Быстрая синхронная инициализация Strategy Manager (локально)"""
        try:
            # ВАЖНО: импортируем из 'strategy_menu.strategy_manager', чтобы избежать побочных эффектов
            from strategy_menu.strategy_manager import StrategyManager
            from config import STRATEGIES_FOLDER, INDEXJSON_FOLDER
            import os

            os.makedirs(STRATEGIES_FOLDER, exist_ok=True)

            self.app.strategy_manager = StrategyManager(
                local_dir=STRATEGIES_FOLDER,
                json_dir=INDEXJSON_FOLDER,
                status_callback=self.app.set_status,
                preload=False
            )
            # Работаем только с локальными стратегиями на старте
            self.app.strategy_manager.local_only_mode = True

            log("Strategy Manager инициализирован (без загрузки из интернета)", "INFO")
            self.init_tasks_completed.add('strategy_manager')

        except Exception as e:
            log(f"Ошибка инициализации Strategy Manager: {e}", "❌ ERROR")
            self.app.set_status(f"Ошибка: {e}")

    def _init_dpi_starter(self):
        """Инициализация DPI стартера"""
        try:
            from dpi.bat_start import BatDPIStart
            from config import WINWS_EXE

            self.app.dpi_starter = BatDPIStart(
                winws_exe=WINWS_EXE,
                status_callback=self.app.set_status,
                ui_callback=self._safe_ui_update,  # безопасный вызов в UI
                app_instance=self.app
            )
            log("DPI Starter инициализирован", "INFO")
            self.init_tasks_completed.add('dpi_starter')
        except Exception as e:
            log(f"Ошибка инициализации DPI Starter: {e}", "❌ ERROR")
            self.app.set_status(f"Ошибка DPI: {e}")

    def _safe_ui_update(self, running: bool):
        """Безопасное обновление UI через UI Manager"""
        if hasattr(self.app, 'ui_manager'):
            try:
                self.app.ui_manager.update_ui_state(running)
            except Exception as e:
                log(f"Ошибка при обновлении UI: {e}", "❌ ERROR")
        else:
            # Fallback, если UI Manager еще не готов
            if hasattr(self.app, 'update_ui'):
                try:
                    self.app.update_ui(running)
                except Exception as e:
                    log(f"Ошибка при обновлении UI (fallback): {e}", "❌ ERROR")

    def _init_hostlists_check(self):
        """Синхронная проверка и создание хостлистов"""
        try:
            log("🔧 Начинаем проверку хостлистов", "DEBUG")
            from utils.hostlists_manager import startup_hostlists_check
            result = startup_hostlists_check()
            if result:
                log("✅ Хостлисты проверены и готовы", "SUCCESS")
            else:
                log("⚠️ Проблемы с хостлистами, создаем минимальные", "WARNING")
            self.init_tasks_completed.add('hostlists')
        except Exception as e:
            log(f"❌ Ошибка проверки хостлистов: {e}", "ERROR")

    def _init_ipsets_check(self):
        """Асинхронная проверка IPsets"""
        class IPsetsChecker(QObject):
            finished = pyqtSignal(bool, str)
            progress = pyqtSignal(str)

            def run(self):
                try:
                    self.progress.emit("Проверка IPsets...")
                    from utils.ipsets_manager import startup_ipsets_check
                    startup_ipsets_check()
                    self.finished.emit(True, "IPsets проверены")
                except Exception as e:
                    self.finished.emit(False, str(e))

        thread = QThread()
        worker = IPsetsChecker()
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.progress.connect(self.app.set_status)
        worker.finished.connect(lambda ok, msg: (
            log(f"IPsets: {msg}", "✅" if ok else "❌"),
            self.init_tasks_completed.add('ipsets') if ok else None
        ))
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)

        thread.start()
        self._ipsets_thread = thread

    def _init_dpi_controller(self):
        """Инициализация DPI контроллера"""
        try:
            from dpi.dpi_controller import DPIController
            self.app.dpi_controller = DPIController(self.app)
            log("DPI Controller инициализирован", "INFO")
            self.init_tasks_completed.add('dpi_controller')
        except Exception as e:
            log(f"Ошибка инициализации DPI Controller: {e}", "❌ ERROR")
            self.app.set_status(f"Ошибка контроллера: {e}")

    def _init_menu(self):
        """Инициализация меню"""
        try:
            from altmenu.app_menubar import AppMenuBar
            self.app.menu_bar = AppMenuBar(self.app)
            if self.app.layout():
                self.app.layout().setMenuBar(self.app.menu_bar)
            log("Меню инициализировано", "INFO")
            self.init_tasks_completed.add('menu')
        except Exception as e:
            log(f"Ошибка инициализации меню: {e}", "❌ ERROR")

    def _connect_signals(self):
        """Подключение всех сигналов"""
        try:
            self.app.select_strategy_clicked.connect(self.app.select_strategy)
            self.app.start_clicked.connect(lambda: self.app.dpi_controller.start_dpi_async())
            self.app.stop_clicked.connect(self.app.show_stop_menu)
            self.app.autostart_enable_clicked.connect(self.app.show_autostart_options)
            self.app.autostart_disable_clicked.connect(self.app.remove_autostart)
            self.app.theme_changed.connect(self.app.change_theme)
            self.app.open_folder_btn.clicked.connect(self.app.open_folder)
            self.app.test_connection_btn.clicked.connect(self.app.open_connection_test)
            self.app.subscription_btn.clicked.connect(self.app.show_subscription_dialog)
            self.app.dns_settings_btn.clicked.connect(self.app.open_dns_settings)
            self.app.proxy_button.clicked.connect(self.app.toggle_proxy_domains)
            self.app.update_check_btn.clicked.connect(self.app.manual_update_check)

            log("Сигналы подключены", "INFO")
            self.init_tasks_completed.add('signals')
        except Exception as e:
            log(f"Ошибка при подключении сигналов: {e}", "❌ ERROR")

    def _initialize_managers_and_services(self):
        """Инициализация всех менеджеров и сервисов"""
        log("🔴 InitializationManager: инициализация менеджеров", "DEBUG")

        try:
            import time as _t
            t0 = _t.perf_counter()

            # Создаем необходимые файлы
            from utils.file_manager import ensure_required_files
            ensure_required_files()

            # DPI Manager
            from managers.dpi_manager import DPIManager
            self.app.dpi_manager = DPIManager(self.app)
            log("✅ DPI Manager создан", "DEBUG")

            # Process Monitor
            if hasattr(self.app, 'process_monitor_manager'):
                self.app.process_monitor_manager.initialize_process_monitor()
            self.app.last_strategy_change_time = __import__('time').time()

            # Discord Manager
            from discord.discord import DiscordManager
            self.app.discord_manager = DiscordManager(status_callback=self.app.set_status)
            log("✅ Discord Manager создан", "DEBUG")

            # Hosts Manager
            from hosts.hosts import HostsManager
            self.app.hosts_manager = HostsManager(status_callback=self.app.set_status)
            log("✅ Hosts Manager создан", "DEBUG")

            # Hosts UI Manager
            from hosts.hosts_ui import HostsUIManager
            self.app.hosts_ui_manager = HostsUIManager(
                parent=self.app,
                hosts_manager=self.app.hosts_manager,
                status_callback=self.app.set_status
            )
            log("✅ Hosts UI Manager создан", "DEBUG")

            # DNS UI Manager
            from dns import DNSUIManager, DNSStartupManager
            self.app.dns_ui_manager = DNSUIManager(
                parent=self.app,
                status_callback=self.app.set_status
            )
            log("✅ DNS UI Manager создан", "DEBUG")

            # Применяем DNS при запуске (асинхронно)
            DNSStartupManager.apply_dns_on_startup_async(status_callback=self.app.set_status)

            # Strategy Manager (локально)
            self._init_strategy_manager()

            # Theme Manager + ThemeHandler
            from ui.theme import ThemeManager, ThemeHandler
            from config import THEME_FOLDER
            from PyQt6.QtWidgets import QApplication

            self.app.theme_manager = ThemeManager(
                app=QApplication.instance(),
                widget=self.app,
                status_label=self.app.status_label if hasattr(self.app, 'status_label') else None,
                theme_folder=THEME_FOLDER,
                donate_checker=getattr(self.app, 'donate_checker', None)
            )

            # Handler и привязка
            self.app.theme_handler = ThemeHandler(self.app, target_widget=self.app.main_widget)
            self.app.theme_handler.set_theme_manager(self.app.theme_manager)
            self.app.theme_handler.update_available_themes()

            # Применяем текущую тему
            if hasattr(self.app, 'theme_combo'):
                self.app.theme_combo.setCurrentText(self.app.theme_manager.current_theme)
            self.app.theme_manager.apply_theme()
            log("✅ Theme Manager создан", "DEBUG")

            # Service Manager (автозапуск)
            from autostart.checker import CheckerManager
            from config import WINWS_EXE

            self.app.service_manager = CheckerManager(
                winws_exe=WINWS_EXE,
                status_callback=self.app.set_status,
                ui_callback=self._safe_ui_update
            )
            log("✅ Service Manager создан", "DEBUG")

            # Обновляем UI состояние через UI Manager
            try:
                log("🔴 Начинаем обновление UI", "DEBUG")
                from autostart.registry_check import is_autostart_enabled
                autostart_exists = is_autostart_enabled()
                log(f"🔴 autostart_exists = {autostart_exists}", "DEBUG")

                if hasattr(self.app, 'ui_manager'):
                    self.app.ui_manager.update_autostart_ui(autostart_exists)
                    self.app.ui_manager.update_ui_state(running=False)

                log("🔴 UI обновление завершено", "DEBUG")
            except Exception as ui_error:
                log(f"❌ Ошибка обновления UI: {ui_error}", "ERROR")
                import traceback
                log(traceback.format_exc(), "ERROR")

            # Всё ок — помечаем «managers» как инициализированы
            log("✅ ВСЕ менеджеры инициализированы", "SUCCESS")
            self.init_tasks_completed.add('managers')

            # Отдаем управление обработчику «после инициализации менеджеров»
            self._on_managers_init_done()

            took = (_t.perf_counter() - t0) * 1000
            log(f"Managers init took {took:.0f} ms", "DEBUG")

        except Exception as e:
            log(f"❌ Критическая ошибка инициализации менеджеров: {e}", "ERROR")
            import traceback
            log(traceback.format_exc(), "ERROR")

            # Пытаемся показать ошибку пользователю
            error_msg = f"Не удалось инициализировать компоненты: {str(e)}"
            try:
                self.app.set_status(f"❌ {error_msg}")
            except Exception:
                pass

            try:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.critical(
                    self.app,
                    "Критическая ошибка инициализации",
                    f"{error_msg}\n\nПриложение может работать нестабильно.\n\n"
                    f"Техническая информация:\n{str(e)}"
                )
            except Exception as msg_error:
                log(f"Не удалось показать сообщение об ошибке: {msg_error}", "ERROR")

    def _init_tray(self):
        """Инициализация системного трея"""
        try:
            from tray import SystemTrayManager
            from config import ICON_PATH, ICON_TEST_PATH, APP_VERSION, CHANNEL
            from PyQt6.QtGui import QIcon
            from PyQt6.QtWidgets import QApplication
            import os

            icon_path = ICON_TEST_PATH if CHANNEL.lower() == "test" else ICON_PATH
            if not os.path.exists(icon_path):
                icon_path = ICON_PATH

            app_icon = QIcon(icon_path)
            self.app.setWindowIcon(app_icon)
            QApplication.instance().setWindowIcon(app_icon)

            self.app.tray_manager = SystemTrayManager(
                parent=self.app,
                icon_path=os.path.abspath(icon_path),
                app_version=APP_VERSION
            )

            log("Системный трей инициализирован", "INFO")
            self.init_tasks_completed.add('tray')
        except Exception as e:
            log(f"Ошибка инициализации трея: {e}", "❌ ERROR")

    def _init_logger(self):
        """Инициализация отправки логов"""
        try:
            from log import global_logger
            from tgram import FullLogDaemon

            log_path = getattr(global_logger, 'log_file', None)
            if log_path:
                self.app.log_sender = FullLogDaemon(
                    log_path=log_path,
                    interval=200,
                    parent=self.app
                )
                log("Логгер инициализирован", "INFO")
            else:
                log("Не удалось инициализировать отправку логов", "⚠ WARNING")

            self.init_tasks_completed.add('logger')
        except Exception as e:
            log(f"Ошибка инициализации логгера: {e}", "❌ ERROR")

    # ───────────────────────── верификация и пост-задачи ─────────────────────

    def _required_components(self):
        """Список требуемых компонентов для успешного старта"""
        return ['dpi_starter', 'dpi_controller', 'strategy_manager', 'managers']

    def _check_and_complete_initialization(self) -> bool:
        """
        Проверяет, все ли компоненты готовы, и если да — завершает инициализацию:
        - ставит финальный статус
        - запускает отложенные post-init задачи
        - синхронизирует автозапуск
        Возвращает True если всё готово, иначе False.
        """
        required_components = self._required_components()
        missing = [c for c in required_components if c not in self.init_tasks_completed]

        if missing:
            return False

        # Все компоненты готовы
        if not self._verify_done:
            self._verify_done = True
            try:
                self.app.set_status("✅ Инициализация завершена")
            except Exception:
                pass
            log("Все компоненты успешно инициализированы", "✅ SUCCESS")

            # Финальные задачи
            QTimer.singleShot(500, self._post_init_tasks)
            QTimer.singleShot(3000, self._sync_autostart_status)

        return True

    def _verify_initialization(self):
        """
        «Мягкая» верификация: делаем несколько попыток с интервалом.
        Предупреждение показываем только после истечения дедлайна.
        """
        if self._verify_done:
            return

        if self._check_and_complete_initialization():
            return  # все ок

        # Если не готовы — подождём ещё несколько раз
        self._verify_attempts += 1
        required_components = self._required_components()
        missing = [c for c in required_components if c not in self.init_tasks_completed]
        log(
            f"Ожидание инициализации (попытка {self._verify_attempts}/{self._verify_max_attempts}), "
            f"не готовы: {', '.join(missing)}",
            "DEBUG"
        )

        if self._verify_attempts < self._verify_max_attempts:
            QTimer.singleShot(self._verify_interval_ms, self._verify_initialization)
            return

        # Дедлайн истёк — показываем предупреждение
        self._verify_done = True
        error_msg = f"Не инициализированы: {', '.join(missing)}"
        try:
            self.app.set_status(f"⚠️ {error_msg}")
        except Exception:
            pass
        log(error_msg, "❌ ERROR")

        try:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self.app,
                "Неполная инициализация",
                f"Некоторые компоненты не были инициализированы:\n{', '.join(missing)}\n\n"
                "Приложение может работать нестабильно."
            )
        except Exception as e:
            log(f"Не удалось показать предупреждение: {e}", "ERROR")

    def _sync_autostart_status(self):
        """Синхронизирует статус автозапуска с реальным состоянием"""
        try:
            from autostart.registry_check import verify_autostart_status
            real_status = verify_autostart_status()
            if hasattr(self.app, 'ui_manager'):
                self.app.ui_manager.update_autostart_ui(real_status)
            log(f"Статус автозапуска синхронизирован: {real_status}", "INFO")
        except Exception as e:
            log(f"Ошибка синхронизации автозапуска: {e}", "❌ ERROR")

    def _on_managers_init_done(self):
        """
        Обработчик успешной инициализации менеджеров:
        - запускает Heavy Init (если есть)
        - пытается «завершить» общую инициализацию сразу, без ожидания таймера
        """
        log("Менеджеры инициализированы, запускаем Heavy Init", "✅ SUCCESS")
        try:
            self.app.set_status("Инициализация завершена")
        except Exception:
            pass

        # Heavy Init
        if hasattr(self.app, 'heavy_init_manager'):
            QTimer.singleShot(100, self.app.heavy_init_manager.start_heavy_init)
            log("🔵 Heavy Init запланирован", "DEBUG")
        else:
            log("❌ Heavy Init Manager не найден", "ERROR")

        # Пробуем завершить общую инициализацию уже сейчас
        self._check_and_complete_initialization()

    def _post_init_tasks(self):
        """Задачи после успешной инициализации (запускаются один раз)"""
        if self._post_init_scheduled:
            return
        self._post_init_scheduled = True

        if hasattr(self.app, 'heavy_init_manager'):
            try:
                if self.app.heavy_init_manager.check_local_files():
                    if hasattr(self.app, 'dpi_manager'):
                        QTimer.singleShot(1000, self.app.dpi_manager.delayed_dpi_start)
                # Автообновление стратегий/ресурсов
                QTimer.singleShot(2000, self.app.heavy_init_manager.start_auto_update)
            except Exception as e:
                log(f"Ошибка post-init задач: {e}", "❌ ERROR")
        else:
            log("❌ Heavy Init Manager не найден для post init tasks", "ERROR")