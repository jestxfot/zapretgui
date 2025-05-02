# main.py

import sys, os, ctypes, subprocess, webbrowser, time

from PyQt5.QtCore    import QTimer, QThread
from PyQt5.QtWidgets import QMessageBox, QWidget, QApplication, QMenu

from ui_main import MainWindowUI
from admin_check import is_admin
from process_monitor import ProcessMonitorThread
from heavy_worker import HeavyWorker
from heavy_init_worker import HeavyInitWorker
from downloader    import DOWNLOAD_URLS
from config import APP_VERSION, BIN_FOLDER, BIN_DIR, LISTS_FOLDER, WINWS_EXE, ICON_PATH, WIDTH, HEIGHT
from hosts import HostsManager
from service import ServiceManager
from autostart_remove import AutoStartCleaner
from start import DPIStarter
from theme import ThemeManager, BUTTON_STYLE, COMMON_STYLE
from tray import SystemTrayManager
from dns import DNSSettingsDialog
from urls import AUTHOR_URL, INFO_URL
from updater import check_and_run_update
from strategy_selector import StrategySelector

from tg_log_delta import LogDeltaDaemon, get_client_id

from reg import get_last_strategy, set_last_strategy

def get_version():
    """Возвращает текущую версию программы"""
    return APP_VERSION

def _handle_update_mode():
    """
    updater.py запускает:
        main.py --update <old_exe> <new_exe>

    Меняем файл и перезапускаем обновлённый exe.
    """
    import os, sys, time, shutil, subprocess
    from log import log

    if len(sys.argv) < 4:
        log("--update: недостаточно аргументов", "ERROR")
        return

    old_exe, new_exe = sys.argv[2], sys.argv[3]

    # ждём, пока старый exe освободится
    for _ in range(10):  # 10 × 0.5 c = 5 сек
        if not os.path.exists(old_exe) or os.access(old_exe, os.W_OK):
            break
        time.sleep(0.5)

    try:
        shutil.copy2(new_exe, old_exe)
        subprocess.Popen([old_exe])          # запускаем новую версию
        log("Файл обновления применён", "INFO")
    except Exception as e:
        log(f"Ошибка в режиме --update: {e}", "ERROR")
    finally:
        try:
            os.remove(new_exe)
        except FileNotFoundError:
            pass
    # ничего не возвращаем — вызывающая сторона сделает sys.exit(0)

class LupiDPIApp(QWidget, MainWindowUI):
    def closeEvent(self, event):
        """Обрабатывает событие закрытия окна"""
        # Останавливаем поток мониторинга
        if hasattr(self, 'process_monitor') and self.process_monitor is not None:
            self.process_monitor.stop()
        
        # Стандартная обработка события
        super().closeEvent(event)
        
    def set_status(self, text):
        """Sets the status text."""
        self.status_label.setText(text)

    def update_ui(self, running):
        """Обновляет состояние кнопок и элементов интерфейса в зависимости от статуса запуска"""
        # Проверяем, активен ли автозапуск
        autostart_active = False
        if hasattr(self, 'service_manager'):
            autostart_active = self.service_manager.check_autostart_exists()
        
        # Если автозапуск активен, не обновляем кнопки запуска/остановки
        # так как они должны управляться методом update_autostart_ui
        if not autostart_active:
            # Обновляем кнопки запуска/остановки только если нет автозапуска
            self.start_btn.setVisible(not running)
            self.stop_btn.setVisible(running)
        
    def check_if_process_started_correctly(self):
        """Проверяет, что процесс успешно запустился и продолжает работать"""
        from log import log
        
        # Проверяем флаг намеренного запуска и сбрасываем его
        intentional_start = getattr(self, 'intentional_start', False)
        
        # Не сбрасываем флаг intentional_start здесь, чтобы предотвратить конфликты
        # self.intentional_start = False
        
        # Если процесс находится в процессе перезапуска или был остановлен намеренно, пропускаем проверку
        if hasattr(self, 'process_restarting') and self.process_restarting:
            log("Пропускаем проверку: процесс перезапускается", level="INFO") 
            self.process_restarting = False  # Сбрасываем флаг
            self.on_process_status_changed(self.dpi_starter.check_process_running(silent=True))
            return
            
        if hasattr(self, 'manually_stopped') and self.manually_stopped:
            log("Пропускаем проверку: процесс остановлен вручную", level="INFO")
            self.manually_stopped = False  # Сбрасываем флаг
            self.on_process_status_changed(self.dpi_starter.check_process_running(silent=True))
            return
        
        # Проверяем, был ли недавно изменен режим (стратегия)
        current_time = time.time()
        if hasattr(self, 'last_strategy_change_time') and current_time - self.last_strategy_change_time < 5:
            # Пропускаем проверку, если стратегия была изменена менее 5 секунд назад
            log("Пропускаем проверку: недавно изменена стратегия", level="INFO")
            self.on_process_status_changed(self.dpi_starter.check_process_running(silent=True))
            return
        
        # Проверяем, запущен ли процесс на данный момент
        process_running = self.dpi_starter.check_process_running()
        
        # Если процесс запущен, всё в порядке
        if process_running:
            log("Процесс запущен и работает нормально", level="INFO")
            self.update_ui(running=True)
            return
            
        # Если флаг намеренного запуска установлен, но процесс не запущен
        if intentional_start and not process_running:
            # Вместо показа ошибки просто логируем информацию
            log("Процесс не запустился после намеренного запуска", level="WARNING")
            self.update_ui(running=False)
        elif not intentional_start and not process_running:
            # Если процесс не запущен, и это не связано с переключением стратегии, показываем ошибку
            exe_path = os.path.abspath(WINWS_EXE)
            # Добавляем проверку, чтобы не показывать сообщение, если процесс был недавно остановлен вручную
            if not hasattr(self, 'recently_stopped') or not self.recently_stopped:
                QMessageBox.critical(self, "Ошибка запуска", 
                                f"Процесс winws.exe запустился, но затем неожиданно завершился.\n\n"
                                f"Путь к программе: {exe_path}\n\n"
                                "Это может быть вызвано:\n"
                                "1. Антивирус удалил часть критически важных файлов программы - переустановите программу заново\n"
                                "2. Какие-то файлы удалены из программы - скачате ZIP архив заново\n\n"
                                "Перед переустановкой программы создайте исключение в антивирусе.")
            self.update_ui(running=False)
        
        # В любом случае обновляем статус
        self.on_process_status_changed(self.dpi_starter.check_process_running(silent=True))
        
    def select_strategy(self):
        """Открывает диалог выбора стратегии. При первом вызове
        скачивает index.json и все .bat-файлы."""
        try:
            if not hasattr(self, 'strategy_manager') or not self.strategy_manager:
                from log import log
                log("Ошибка: менеджер стратегий не инициализирован", level="ERROR")
                self.set_status("Ошибка: менеджер стратегий не инициализирован")
                return

            # ---------- первая загрузка стратегий ---------------------
            if not self.strategy_manager.already_loaded:
                self.set_status("Загружаю список стратегий…")
                QApplication.processEvents()          # сразу обновим строку статуса
                self.strategy_manager.preload_strategies()
                self.update_strategies_list(force_update=True)
                self.set_status("Список стратегий загружен")

            # ---------- определяем текущую стратегию ------------------
            current_strategy = self.current_strategy_label.text()
            if current_strategy == "Не выбрана":
                current_strategy = get_last_strategy()

            # ---------- создаём и показываем диалог -------------------
            selector = StrategySelector(
                parent              = self,
                strategy_manager    = self.strategy_manager,
                current_strategy_name = current_strategy
            )
            selector.strategySelected.connect(self.on_strategy_selected_from_dialog)
            selector.exec_()

        except Exception as e:
            from log import log
            log(f"Ошибка при открытии диалога выбора стратегии: {str(e)}", level="ERROR")
            self.set_status(f"Ошибка при выборе стратегии: {str(e)}")

    def on_strategy_selected_from_dialog(self, strategy_id, strategy_name):
        """Обрабатывает выбор стратегии из диалога."""
        try:
            from log import log
            log(f"Выбрана стратегия: {strategy_name} (ID: {strategy_id})", level="INFO")
            
            # Сохраняем ID и имя выбранной стратегии в атрибутах класса
            self.current_strategy_id = strategy_id
            self.current_strategy_name = strategy_name
            
            # Обновляем метку с текущей стратегией
            self.current_strategy_label.setText(strategy_name)
            
            # Сохраняем выбранную стратегию в реестр
            set_last_strategy(strategy_name)
            
            # Записываем время изменения стратегии
            self.last_strategy_change_time = time.time()
            
            # Запускаем стратегию
            self.dpi_starter.start_dpi(selected_mode=strategy_name)
            
            # Перезапускаем Discord только если:
            # 1. Это не первый запуск
            # 2. Автоперезапуск включен в настройках
            from discord_restart import get_discord_restart_setting
            if not self.first_start and get_discord_restart_setting():
                self.discord_manager.restart_discord_if_running()
            else:
                self.first_start = False  # Сбрасываем флаг первого запуска
        except Exception as e:
            log(f"Ошибка при установке выбранной стратегии: {str(e)}", level="ERROR")
            self.set_status(f"Ошибка при установке стратегии: {str(e)}")

    
    def _load_strategy_index(self) -> dict:
        """
        Загружает и кэширует словарь из bin/index.json
        """
        if hasattr(self, "_strategy_index") and self._strategy_index:
            return self._strategy_index            # уже загружен

        index_path = os.path.join(BIN_DIR, "index.json")
        from log import log

        if not os.path.isfile(index_path):
            log(f"index.json не найден по пути {index_path}", level="ERROR")
            self.set_status("Ошибка: index.json не найден")
            self._strategy_index = {}
            return self._strategy_index

        try:
            with open(index_path, "r", encoding="utf-8") as f:
                import json
                self._strategy_index = json.load(f)
            log(f"Загружено стратегий: {len(self._strategy_index)}", level="DEBUG")
        except Exception as e:
            log(f"Не удалось прочитать index.json: {e}", level="ERROR")
            self.set_status(f"Ошибка чтения index.json: {e}")
            self._strategy_index = {}

        return self._strategy_index

    def update_autostart_ui(self, service_running: bool | None):
        """
        Обновляет интерфейс при включении / выключении автозапуска.
        • start_btn, stop_btn скрываются если автозапуск активен
        • autostart_enable_btn скрывается если автозапуск активен
        • autostart_disable_btn растягивается на 2-колонки
        """
        if service_running is None and hasattr(self, 'service_manager'):
            service_running = self.service_manager.check_autostart_exists()

        enable_btn  = self.autostart_enable_btn
        disable_btn = self.autostart_disable_btn
        start_btn   = getattr(self, 'start_btn',  None)
        stop_btn    = getattr(self, 'stop_btn',   None)

        # --- если автозапуск активен -----------------------------------------
        if service_running:
            if start_btn:  start_btn.setVisible(False)
            if stop_btn:   stop_btn.setVisible(False)
            enable_btn.setVisible(False)

            # Сначала удаляем кнопку отключения из сетки, чтобы не было дублирования
            self.button_grid.removeWidget(disable_btn)
            
            # Затем добавляем её снова, но растянутую на 2 колонки
            self.button_grid.addWidget(disable_btn, 0, 0, 1, 2)
            
            # Показываем кнопку отключения автозапуска
            disable_btn.setVisible(True)
            disable_btn.setText('Выкл. автозапуск')  # Гарантируем правильный текст
            
            # ИЗМЕНЕНО: Оставляем кнопку выбора стратегии видимой всегда
            # self.select_strategy_btn.setVisible(False)

            # Удаляем предупреждение о смене стратегии
            if hasattr(self, 'service_info_label'):
                self.service_info_label.setVisible(False)
                self.layout().removeWidget(self.service_info_label)
                self.service_info_label.deleteLater()
                self.service_info_label = None

        # --- автозапуск выключен ---------------------------------------------
        else:
            # Сначала удаляем кнопку отключения из сетки
            self.button_grid.removeWidget(disable_btn)
            
            # Возвращаем стандартную раскладку
            if start_btn:  
                start_btn.setVisible(True)
                self.button_grid.addWidget(start_btn, 0, 0)
                    
            if stop_btn:   
                stop_btn.setVisible(False)
                self.button_grid.addWidget(stop_btn, 0, 0)
                    
            enable_btn.setVisible(True)
            self.button_grid.addWidget(enable_btn, 0, 1)
            
            # Добавляем кнопку отключения автозапуска на правильное место
            self.button_grid.addWidget(disable_btn, 0, 1)
            disable_btn.setVisible(False)  # Но скрываем её, так как автозапуск выключен
            
    def update_strategies_list(self, force_update=False):
        """Обновляет список доступных стратегий"""
        try:
            from log import log
            
            # Получаем список стратегий
            strategies = self.strategy_manager.get_strategies_list(force_update=force_update)
            
            if not strategies:
                log("Не удалось получить список стратегий", level="ERROR")
                return
            
            # Выводим список стратегий в лог для отладки
            #log(f"Получены стратегии: {list(strategies.keys())}", level="DEBUG")
            for strategy_id, info in strategies.items():
                #log(f"Стратегия ID: {strategy_id}, Name: {info.get('name')}, Path: {info.get('file_path')}", level="DEBUG")
                pass  # Убираем лишний лог, если не нужно
            
            # Сохраняем текущий выбор
            current_strategy = None
            if hasattr(self, 'current_strategy_name') and self.current_strategy_name:
                current_strategy = self.current_strategy_name
            else:
                current_strategy = self.current_strategy_label.text()
                if current_strategy == "Не выбрана":
                    current_strategy = get_last_strategy()
            
            # Обновляем текущую метку, если стратегия выбрана
            if current_strategy and current_strategy != "Не выбрана":
                self.current_strategy_label.setText(current_strategy)
            
            log(f"Загружено {len(strategies)} стратегий", level="INFO")
            
        except Exception as e:
            error_msg = f"Ошибка при обновлении списка стратегий: {str(e)}"
            from log import log
            log(error_msg, level="ERROR")
            self.set_status(error_msg)
        
    def init_strategy_manager(self):
        """Инициализирует менеджер стратегий"""
        try:
            from strategy_manager import StrategyManager
            from log import log
            
            # Импортируем настройки из config
            from config import GITHUB_STRATEGIES_BASE_URL, STRATEGIES_FOLDER, GITHUB_STRATEGIES_JSON_URL
            
            # Создаем директорию для стратегий, если она не существует
            if not os.path.exists(STRATEGIES_FOLDER):
                os.makedirs(STRATEGIES_FOLDER, exist_ok=True)
            
            # Инициализируем менеджер стратегий
            self.strategy_manager = StrategyManager(
                base_url=GITHUB_STRATEGIES_BASE_URL,
                local_dir=STRATEGIES_FOLDER,
                status_callback=self.set_status,
                json_url=GITHUB_STRATEGIES_JSON_URL  # Прямая ссылка на JSON
            )
            
            # Предзагружаем все стратегии
            self.strategy_manager.preload_strategies()
            
            # Обновляем список стратегий с обработкой ошибок
            try:
                # Обновляем список доступных стратегий
                self.update_strategies_list()
                
                # Устанавливаем последнюю сохраненную стратегию в текстовую метку
                last_strategy = get_last_strategy()
                if last_strategy:
                    self.current_strategy_label.setText(last_strategy)
                    self.current_strategy_name = last_strategy
            except Exception as e:
                log(f"Ошибка при обновлении списка стратегий: {str(e)}", level="ERROR")
                self.set_status(f"Не удалось загрузить стратегии: {str(e)}")
        except Exception as e:
            from log import log
            log(f"Ошибка при инициализации менеджера стратегий: {str(e)}", level="ERROR")
            self.set_status(f"Ошибка стратегий: {str(e)}")
            
            # Создаем заглушку для strategy_manager
            self.strategy_manager = None

    def initialize_managers_and_services(self):
        """
        Быстрая (лёгкая) инициализация и запуск HeavyInitWorker.
        Теперь StrategyManager создаётся «ленивым» – ничего не качает,
        пока пользователь не откроет Меню стратегий.
        """
        from log import log
        log("initialize_managers_and_services: quick part", "INFO")

        # --- лёгкие вещи (≈10-50 мс) ----------------------------------
        self.init_process_monitor()
        self.last_strategy_change_time = time.time()

        from discord import DiscordManager
        self.discord_manager = DiscordManager(status_callback=self.set_status)
        self.hosts_manager   = HostsManager   (status_callback=self.set_status)

        # StrategyManager  (preload=False  ⇒  ничего не скачивает)
        from strategy_manager import StrategyManager
        from config import (GITHUB_STRATEGIES_BASE_URL, STRATEGIES_FOLDER,
                            GITHUB_STRATEGIES_JSON_URL)
        os.makedirs(STRATEGIES_FOLDER, exist_ok=True)
        self.strategy_manager = StrategyManager(
            base_url        = GITHUB_STRATEGIES_BASE_URL,
            local_dir       = STRATEGIES_FOLDER,
            status_callback = self.set_status,
            json_url        = GITHUB_STRATEGIES_JSON_URL,
            preload         = False)           # ← ключ

        # ThemeManager
        self.theme_manager = ThemeManager(
            app           = QApplication.instance(),
            widget        = self,
            status_label  = self.status_label,
            author_label  = self.author_label,
            support_label = self.support_label,
            bin_folder    = BIN_FOLDER,
            author_url    = AUTHOR_URL,
            bol_van_url   = self.bol_van_url)
        self.theme_combo.setCurrentText(self.theme_manager.current_theme)
        self.theme_manager.apply_theme()

        # ServiceManager
        self.service_manager = ServiceManager(
            winws_exe    = WINWS_EXE,
            bin_folder   = BIN_FOLDER,
            lists_folder = LISTS_FOLDER,
            status_callback = self.set_status,
            ui_callback     = self.update_ui)

        # стартовое состояние интерфейса
        self.update_autostart_ui(self.service_manager.check_autostart_exists())
        self.update_ui(running=False)

        # --- HeavyInitWorker (качает winws.exe, списки и т.п.) --------
        self.set_status("Инициализация…")

        self._hthr = QThread(self)
        self._hwrk = HeavyInitWorker(self.dpi_starter, DOWNLOAD_URLS)
        self._hwrk.moveToThread(self._hthr)

        # сигналы
        self._hthr.started.connect(self._hwrk.run)
        self._hwrk.progress.connect(self.set_status)
        self._hwrk.finished.connect(self._on_heavy_done)
        self._hwrk.finished.connect(self._hthr.quit)
        self._hwrk.finished.connect(self._hwrk.deleteLater)
        self._hthr.finished.connect(self._hthr.deleteLater)

        self._hthr.start()
        
    def _on_heavy_done(self, ok: bool, err: str):
        """GUI-поток: получаем результат тяжёлой работы."""
        if not ok:
            QMessageBox.critical(self, "Ошибка инициализации", err)
            self.set_status("Ошибка инициализации")
            return

        # index.json и winws.exe готовы (если они требовались)
        if self.strategy_manager.already_loaded:
            self.update_strategies_list()

        self.delayed_dpi_start()
        self.update_proxy_button_state()

        # combobox-фикс
        for d in (0, 100, 200):
            QTimer.singleShot(d, self.force_enable_combos)

        QTimer.singleShot(4000, lambda: check_and_run_update(
            parent=self, status_cb=self.set_status, silent=False))

        self.set_status("Готово")
    
    def init_process_monitor(self):
        """Инициализирует поток мониторинга процесса"""
        if hasattr(self, 'process_monitor') and self.process_monitor is not None:
            self.process_monitor.stop()
        
        self.process_monitor = ProcessMonitorThread(self.dpi_starter)
        self.process_monitor.processStatusChanged.connect(self.on_process_status_changed)
        self.process_monitor.start()

    def on_process_status_changed(self, is_running):
        """Обрабатывает сигнал изменения статуса процесса"""
        from log import log
        
        # Проверяем, изменилось ли состояние автозапуска
        autostart_active = self.service_manager.check_autostart_exists() \
                        if hasattr(self, 'service_manager') else False
        
        # Сохраняем текущее состояние для сравнения в будущем
        self._prev_autostart = autostart_active
        self._prev_running = is_running
        
        # Обновляем UI
        if is_running or autostart_active:
            if hasattr(self, 'start_btn'):
                self.start_btn.setVisible(False)
            if hasattr(self, 'stop_btn'):
                self.stop_btn.setVisible(True)
        else:
            if hasattr(self, 'start_btn'):
                self.start_btn.setVisible(True)
            if hasattr(self, 'stop_btn'):
                self.stop_btn.setVisible(False)
        
        # Обновляем статус
        if autostart_active:
            self.process_status_value.setText("АВТОЗАПУСК АКТИВЕН")
            self.process_status_value.setStyleSheet("color: purple; font-weight: bold;")
        else:
            if is_running:
                self.process_status_value.setText("ВКЛЮЧЕН")
                self.process_status_value.setStyleSheet("color: green; font-weight: bold;")
            else:
                self.process_status_value.setText("ВЫКЛЮЧЕН")
                self.process_status_value.setStyleSheet("color: red; font-weight: bold;")
        
        # ИЗМЕНЕНО: Оставляем кнопку выбора стратегии всегда видимой
        # if hasattr(self, 'select_strategy_btn'):
        #     self.select_strategy_btn.setVisible(not autostart_active)
            
    def delayed_dpi_start(self):
        """Выполняет отложенный запуск DPI с проверкой наличия автозапуска"""
        from log import log
        
        # ВАЖНО: Проверяем, инициализирован ли dpi_starter
        if not hasattr(self, 'dpi_starter') or self.dpi_starter is None:
            log("DPI Starter еще не инициализирован, откладываем запуск", level="WARNING")
            # Повторяем попытку через секунду
            QTimer.singleShot(100, self.delayed_dpi_start)
            return
        
        # Сначала проверяем, активен ли автозапуск через планировщик задач
        # ВАЖНО: делаем прямой запрос к планировщику задач Windows для гарантии актуальности данных
        try:
            task_name = "ZapretCensorliber"
            check_cmd = f'schtasks /Query /TN "{task_name}" 2>nul'
            result = subprocess.run(check_cmd, shell=True, capture_output=True)
            
            if result.returncode == 0:
                log("Обнаружена активная задача планировщика ZapretCensorliber, пропускаем ручной запуск", level="INFO")
                self.update_ui(running=True)
                self.on_process_status_changed(self.dpi_starter.check_process_running(silent=True))
                return
        except Exception as e:
            log(f"Ошибка при проверке задачи планировщика: {str(e)}", level="WARNING")
        
        # Затем проверяем, запущен ли уже процесс winws.exe
        if self.dpi_starter.check_process_running():
            log("Процесс winws.exe уже запущен, пропускаем ручной запуск", level="INFO")
            self.update_ui(running=True)
            return
        
        log("Выполняем запуск DPI", level="INFO")
        self.dpi_starter.start_dpi()
    
    def finish_initialization(self):
        """Завершает процесс инициализации"""
        from log import log
        
        self.initializing = False
        self.protected_process = False
        
        # Удаляем маркерный файл защиты после завершения инициализации
        marker_file = os.path.join(os.path.dirname(WINWS_EXE), "process_protected.txt")
        try:
            if os.path.exists(marker_file):
                os.remove(marker_file)
        except Exception as e:
            log(f"Не удалось удалить маркер защиты процесса: {str(e)}", level="WARNING")
        
        # Проверяем существование dpi_starter перед использованием
        if hasattr(self, 'dpi_starter') and self.dpi_starter:
            # Проверяем состояние процесса для обновления UI
            if self.dpi_starter.check_process_running():
                self.update_ui(running=True)
            else:
                # Если процесс не найден, повторяем запуск
                log("Процесс не найден после инициализации, повторяем запуск", level="INFO")
                
                # Получаем стратегию из метки или используем последнюю сохраненную
                strategy_name = None
                if hasattr(self, 'current_strategy_name') and self.current_strategy_name:
                    strategy_name = self.current_strategy_name
                else:
                    strategy_name = self.current_strategy_label.text()
                    if strategy_name == "Не выбрана":
                        strategy_name = get_last_strategy()
                
                log(f"Выбранная стратегия для запуска: {strategy_name}", level="INFO")
                lambda: self.dpi_starter.start_dpi(selected_mode=strategy_name)
        else:
            log("DPI Starter не инициализирован, пропускаем проверку процесса", level="WARNING")
        
        log("Процесс инициализации завершен", level="INFO")

    def __init__(self):
        self.process_monitor = None  # Будет инициализирован позже

        super().__init__()

        self.dpi_starter = DPIStarter(
            winws_exe   = WINWS_EXE,
            bin_folder  = BIN_FOLDER,
            lists_folder= LISTS_FOLDER,
            status_callback = self.set_status,
            ui_callback     = self.update_ui
        )

        self.setWindowTitle(f'Zapret v{APP_VERSION}')  # Добавляем версию в заголовок

        self.first_start = True  # Флаг для отслеживания первого запуска

        # Устанавливаем иконку приложения
        icon_path = os.path.abspath(ICON_PATH)
        if os.path.exists(icon_path):
            from PyQt5.QtGui import QIcon
            app_icon = QIcon(icon_path)
            self.setWindowIcon(app_icon)
            QApplication.instance().setWindowIcon(app_icon)
        
        # Инициализируем интерфейс
        self.build_ui(width=WIDTH, height=HEIGHT)
        QTimer.singleShot(0, self.initialize_managers_and_services)
        
        # подключаем логику к новым кнопкам
        self.select_strategy_clicked.connect(self.select_strategy)
        self.start_clicked.connect(self.dpi_starter.start_dpi)
        self.stop_clicked.connect(self.show_stop_menu)
        self.autostart_enable_clicked.connect(self.show_autostart_options)
        self.autostart_disable_clicked.connect(self.remove_autostart)
        self.theme_changed.connect(self.change_theme)

        # дополнительные кнопки (по тексту)
        self.extra_2_0_btn.clicked.connect(self.open_folder)
        self.extra_2_1_btn.clicked.connect(self.open_connection_test)
        self.extra_3_0_btn.clicked.connect(self.update_other_list)
        self.extra_3_1_btn.clicked.connect(self.open_general)
        self.extra_4_0_btn.clicked.connect(self.update_winws_exe)
        self.extra_4_1_btn.clicked.connect(self.open_dns_settings)
        self.extra_5_0_btn.clicked.connect(self.toggle_proxy_domains)
        self.extra_6_0_btn.clicked.connect(self.open_info)
        self.extra_7_0_btn.clicked.connect(self.show_logs)
        self.extra_7_1_btn.clicked.connect(self.send_log_to_tg)
        self.extra_8_0_btn.clicked.connect(lambda: check_and_run_update(parent=self, status_cb=self.set_status))
        
        # Инициализируем атрибуты для работы со стратегиями
        self.current_strategy_id = None
        self.current_strategy_name = None
        
        # Инициализируем системный трей после создания всех элементов интерфейса
        self.tray_manager = SystemTrayManager(
            parent=self,
            icon_path=os.path.abspath(ICON_PATH),
            app_version=APP_VERSION
        )

        # после создания GUI и инициализации логгера:
        from tg_log_full import FullLogDaemon
        self.log_sender = FullLogDaemon(
                log_path = "zapret_log.txt",
                interval = 120,      # интервал отправки в секундах
                parent   = self)
        
    def force_enable_combos(self):
        """Принудительно включает комбо-боксы тем"""
        try:
            if hasattr(self, 'theme_combo'):
                # Полное восстановление состояния комбо-бокса тем
                self.theme_combo.setEnabled(True)
                self.theme_combo.show()
                self.theme_combo.setStyleSheet(f"{COMMON_STYLE} text-align: center;")

            # Принудительное обновление UI
            QApplication.processEvents()
            
            # Возвращаем True если комбо-бокс существует и активен
            return hasattr(self, 'theme_combo') and self.theme_combo.isEnabled()
        except Exception as e:
            from log import log
            log(f"Ошибка при активации комбо-бокса тем: {str(e)}")
            return False

    def on_mode_changed(self, selected_mode):
        """Обработчик смены режима в combobox"""
        # Проверяем, активен ли автозапуск
        if hasattr(self, 'service_manager') and self.service_manager.check_autostart_exists():
            # Если автозапуск активен, игнорируем смену режима и восстанавливаем предыдущий выбор
            from log import log
            log("Смена стратегии недоступна при активном автозапуске", level="WARNING")
            return
        
        # Обновляем отображение текущей стратегии
        self.current_strategy_label.setText(selected_mode)

        # Записываем время изменения стратегии
        self.last_strategy_change_time = time.time()
        
        # Сохраняем выбранную стратегию в реестр
        set_last_strategy(selected_mode)
        
        # Запускаем DPI с новым режимом - теперь это безопасно,
        # так как stop.bat гарантированно остановит предыдущий процесс
        self.dpi_starter.start_dpi(selected_mode=selected_mode)
        
        # Перезапускаем Discord только если:
        # 1. Это не первый запуск
        # 2. Автоперезапуск включен в настройках
        from discord_restart import get_discord_restart_setting
        if not self.first_start and get_discord_restart_setting():
            self.discord_manager.restart_discord_if_running()
        else:
            self.first_start = False  # Сбрасываем флаг первого запуска
            
    def change_theme(self, theme_name):
        """Изменяет тему приложения"""
        success, message = self.theme_manager.apply_theme(theme_name)
        if success:
            self.set_status(f"Тема изменена на: {theme_name}")
        else:
            self.set_status(message)

    def open_info(self):
        """Opens the info website."""
        try:
            webbrowser.open(INFO_URL)
            self.set_status("Открываю руководство...")
        except Exception as e:
            error_msg = f"Ошибка при открытии руководства: {str(e)}"
            print(error_msg)
            self.set_status(error_msg)

    def open_folder(self):
        """Opens the DPI folder."""
        try:
            subprocess.Popen('explorer.exe .', shell=True)
        except Exception as e:
            self.set_status(f"Ошибка при открытии папки: {str(e)}")

    def open_general(self):
        """Opens the list-general.txt file."""
        try:
            general_path = os.path.join(LISTS_FOLDER, 'other.txt')
            # Проверяем существование файла и создаем его при необходимости
            if not os.path.exists(general_path):
                os.makedirs(os.path.dirname(general_path), exist_ok=True)
                with open(general_path, 'w', encoding='utf-8') as f:
                    f.write("# Добавьте сюда свои домены, по одному на строку\n")
            
            subprocess.Popen(f'notepad.exe "{general_path}"', shell=True)
        except Exception as e:
            self.set_status(f"Ошибка при открытии файла: {str(e)}")

    def show_autostart_options(self):
        """Показывает диалог автозапуска (вместо старого подменю)."""
        from autostart_menu import AutoStartMenu
        from log import log

        # Если уже есть автозапуск — предупредим и выйдем
        if self.service_manager.check_autostart_exists():
            log("Автозапуск уже активен", "WARNING")
            self.set_status("Сначала отключите текущий автозапуск")
            return

        # как называется текущая стратегия
        strategy_name = self.current_strategy_label.text()
        if strategy_name == "Не выбрана":
            strategy_name = get_last_strategy()

        dlg = AutoStartMenu(
            parent             = self,
            strategy_name      = strategy_name,
            bin_folder         = BIN_FOLDER,
            check_autostart_cb = self.service_manager.check_autostart_exists,
            update_ui_cb       = self.update_autostart_ui,
            status_cb          = self.set_status
        )
        dlg.exec_()
        
    def show_stop_menu(self):
        """Показывает меню с вариантами остановки программы"""
        from stop import stop_dpi
        from log import log
        log("Отображение меню остановки Zapret", level="INFO")
        
        # Создаем меню
        menu = QMenu(self)
        
        # Добавляем пункты меню
        stop_winws_action = menu.addAction("Остановить только winws.exe")
        stop_and_exit_action = menu.addAction("Остановить и закрыть программу")
        
        # Получаем положение кнопки для отображения меню
        button_pos = self.stop_btn.mapToGlobal(self.stop_btn.rect().bottomLeft())
        
        # Показываем меню и получаем выбранное действие
        action = menu.exec_(button_pos)
        
        # Обрабатываем выбор
        if action == stop_winws_action:
            log("Выбрано: Остановить только winws.exe", level="INFO")
            stop_dpi(self)
        elif action == stop_and_exit_action:
            log("Выбрано: Остановить и закрыть программу", level="INFO")
            self.set_status("Останавливаю Zapret и закрываю программу...")
            
            # Сначала останавливаем процесс
            stop_dpi(self)
            
            # Затем завершаем приложение
            QApplication.quit()

    def remove_autostart(self):
        cleaner = AutoStartCleaner(
            status_cb=self.set_status      # передаём вашу строку статуса
        )
        if cleaner.run():
            self.update_autostart_ui(False)
            self.on_process_status_changed(
                self.dpi_starter.check_process_running(silent=True)
            )

    def update_proxy_button_state(self):
        """Обновляет состояние кнопки разблокировки в зависимости от наличия записей в hosts"""
        if hasattr(self, 'proxy_button'):
            is_active = self.hosts_manager.is_proxy_domains_active()
            if is_active:
                self.proxy_button.setText('Отключить разблокировку ChatGPT, Spotify, Notion')
                self.proxy_button.setStyleSheet(BUTTON_STYLE.format("255, 93, 174"))  # Красноватый цвет
            else:
                self.proxy_button.setText('Разблокировать ChatGPT, Spotify, Notion и др.')
                self.proxy_button.setStyleSheet(BUTTON_STYLE.format("218, 165, 32"))  # Золотистый цвет

    def toggle_proxy_domains(self):
        """Переключает состояние разблокировки: добавляет или удаляет записи из hosts"""
        is_active = self.hosts_manager.is_proxy_domains_active()
        
        if is_active:
            # Показываем информационное сообщение о отключении
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Question)
            msg.setWindowTitle("Отключение разблокировки")
            msg.setText("Отключить разблокировку сервисов через hosts-файл?")
            
            msg.setInformativeText(
                "Это действие удалит добавленные ранее записи из файла hosts.\n\n"
                "Для применения изменений ОБЯЗАТЕЛЬНО СЛЕДУЕТ закрыть и открыть веб-браузер и/или приложение Spotify!"
            )
            
            msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            result = msg.exec_()
            
            if result == QMessageBox.Yes:
                if self.hosts_manager.remove_proxy_domains():
                    self.set_status("Разблокировка отключена. Перезапустите браузер.")
                    self.update_proxy_button_state()
                else:
                    self.set_status("Не удалось отключить разблокировку.")
            else:
                self.set_status("Операция отменена.")
        else:
            # Показываем информационное сообщение о включении
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Information)
            msg.setWindowTitle("Разблокировка через hosts-файл")
            msg.setText("Установка соединения к proxy-серверу через файл hosts")
            
            msg.setInformativeText(
                "Добавление этих сайтов в обычные списки Zapret не поможет их разблокировать, "
                "так как доступ к ним заблокирован для территории РФ со стороны самих сервисов "
                "(без участия Роскомнадзора).\n\n"
                "Для применения изменений ОБЯЗАТЕЛЬНО СЛЕДУЕТ закрыть и открыть веб-браузер (не только сайт, а всю программу) и/или приложение Spotify!"
            )
            
            msg.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
            result = msg.exec_()
            
            if result == QMessageBox.Ok:
                if self.hosts_manager.add_proxy_domains():
                    self.set_status("Разблокировка включена. Перезапустите браузер.")
                    self.update_proxy_button_state()
                else:
                    self.set_status("Не удалось включить разблокировку.")
            else:
                self.set_status("Операция отменена.")

    def open_connection_test(self):
        """Открывает окно тестирования соединения."""
        # Импортируем модуль тестирования
        from connection_test import ConnectionTestDialog
        dialog = ConnectionTestDialog(self)
        dialog.exec_()

    def update_other_list(self):
        """Обновляет файл списка other.txt с удаленного сервера"""
        from update_other import update_other_list as _update_other_list
        _update_other_list(parent=self, status_callback=self.set_status)

    def open_dns_settings(self):
        """Открывает диалог настройки DNS-серверов"""
        try:
            # Показываем индикатор в статусной строке
            self.set_status("Открываем настройки DNS (загрузка данных)...")
        
            # Передаем текущий стиль в диалог
            dns_dialog = DNSSettingsDialog(self, common_style=COMMON_STYLE)
            dns_dialog.exec_()
            
            # Сбрасываем статус после закрытия диалога
            self.set_status("Настройки DNS закрыты")
        except Exception as e:
            error_msg = f"Ошибка при открытии настроек DNS: {str(e)}"
            from log import log
            log(f"Ошибка при открытии настроек DNS: {str(e)}", level="ERROR")
            self.set_status(error_msg)

    def update_winws_exe(self):
        """Обновляет файл winws.exe до последней версии с GitHub"""
        from update_winws import update_winws_exe as _update_winws_exe
        _update_winws_exe(self)

    def show_logs(self):
        """Shows the application logs in a dialog"""
        try: 
            from log import get_log_content, LogViewerDialog
            log_content = get_log_content()
            log_dialog = LogViewerDialog(self, log_content)
            log_dialog.exec_()
        except Exception as e:
            self.set_status(f"Ошибка при открытии журнала: {str(e)}")

    def send_log_to_tg(self):
        """Отправляет текущий лог-файл в Telegram."""
        try:
            from tg_sender import send_log_to_tg
            # путь к вашему лог-файлу (как в модуле log)
            LOG_PATH = "zapret_log.txt"

            caption = f"Zapret log  (ID: {get_client_id()}, v{APP_VERSION})"
            send_log_to_tg(LOG_PATH, caption)

            QMessageBox.information(self, "Отправка",
                                    "Лог отправлен боту.")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка",
                                f"Не удалось отправить лог:\n{e}")

    def init_tray_if_needed(self):
        """Инициализирует системный трей, если он еще не был инициализирован"""
        if not hasattr(self, 'tray_manager') or self.tray_manager is None:
            from log import log
            log("Инициализация менеджера системного трея", level="INFO")
            
            # Проверяем наличие пути к иконке
            icon_path = os.path.abspath(ICON_PATH)
            if not os.path.exists(icon_path):
                log(f"Предупреждение: иконка {icon_path} не найдена", level="WARNING")
                
            # Инициализируем трей
            from tray import SystemTrayManager
            self.tray_manager = SystemTrayManager(
                parent=self,
                icon_path=icon_path,
                app_version=APP_VERSION
            )
            
            # Проверяем, запущены ли мы с аргументом --tray
            if len(sys.argv) > 1 and sys.argv[1] == "--tray":
                log("Программа запущена с аргументом --tray, скрываем окно", level="INFO")
                # Гарантируем, что окно скрыто
                self.hide()

def main():
    # ---------------- одно-экземплярный mutex -------------------------
    from single_instance import create_mutex, release_mutex
    mutex_handle, already_running = create_mutex("ZapretSingleInstance")
    if already_running:
        ctypes.windll.user32.MessageBoxW(
            None, "Экземпляр Zapret уже запущен и/или работает в трее!",
            "Zapret", 0x40)
        sys.exit(0)
    import atexit;  atexit.register(lambda: release_mutex(mutex_handle))

    # ---------------- быстрые проверки (без Qt) -----------------------
    from bfe_util import ensure_bfe_running
    if not ensure_bfe_running(show_ui=True):
        sys.exit(1)

    # ---------------- разбор аргументов CLI ---------------------------
    start_in_tray = "--tray" in sys.argv
    if "--version" in sys.argv:
        ctypes.windll.user32.MessageBoxW(None, APP_VERSION,
                                        "Zapret – версия", 0x40)
        sys.exit(0)

    if "--update" in sys.argv and len(sys.argv) > 3:
        _handle_update_mode()           # ваша функция обновления
        sys.exit(0)

    # ---------------- создаём QApplication РАНЬШЕ QMessageBox-ов ------
    from log import log
    try:
        os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
        from PyQt5.QtWidgets import QApplication
        from PyQt5.QtCore import QCoreApplication
        from PyQt5.QtCore import Qt
        QCoreApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)   # общий скейлинг
        QCoreApplication.setAttribute(Qt.AA_UseHighDpiPixmaps,  True)     # иконки

        app = QApplication(sys.argv)
        app.setQuitOnLastWindowClosed(False)   #  ← добавьте эту строку
    except Exception as e:
        ctypes.windll.user32.MessageBoxW(None,
            f"Ошибка инициализации Qt: {e}", "Zapret", 0x10)
        sys.exit(1)

    # ---------------- предупреждения, требующие Qt --------------------
    from check_start import display_startup_warnings

    warnings_ok = display_startup_warnings()
    if not warnings_ok and not start_in_tray:      # <── ключевое отличие
        sys.exit(1)

    # ---- admin elevation (после предупреждений, до создания окна) ----
    if not is_admin():
        # формируем строку параметров для нового процесса
        params = " ".join(sys.argv[1:])            # ←  главное изменение
        # если нужны кавычки для «пробельных» аргументов:
        # params = " ".join(f'"{a}"' for a in sys.argv[1:])

        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable,
            params,            # ←  передаём обычную строку
            None, 1
        )
        sys.exit(0)

    from remove_terminal import remove_windows_terminal_if_win11
    remove_windows_terminal_if_win11()

    # ---------------- основное окно ----------------------------------
    window = LupiDPIApp()
    window.init_tray_if_needed()

    if start_in_tray:
        log("Запуск приложения скрыто в трее", "TRAY")
        # окно не показываем
    else:
        log("Запуск приложения в обычном режиме", "TRAY")
        window.show()
    
    # Если запуск в трее, уведомляем пользователя
    if start_in_tray and hasattr(window, 'tray_manager'):
        window.tray_manager.show_notification("Zapret работает в трее", 
                                                "Приложение запущено в фоновом режиме")
        

    sys.exit(app.exec_())

if __name__ == "__main__":
    main()