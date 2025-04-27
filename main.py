import sys, os, ctypes, winreg, subprocess, webbrowser, time, shutil

from PyQt5.QtCore    import Qt, QTimer, QThread, pyqtSignal
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QHBoxLayout,
                             QComboBox, QMessageBox, QApplication, QFrame,
                             QSpacerItem, QSizePolicy)


from downloader import DOWNLOAD_URLS
from config import APP_VERSION, BIN_FOLDER, LISTS_FOLDER, WINWS_EXE, ICON_PATH
from hosts import HostsManager
from service import ServiceManager
from start import DPIStarter

from theme import ThemeManager, RippleButton, THEMES, BUTTON_STYLE, COMMON_STYLE, BUTTON_HEIGHT, STYLE_SHEET
from tray import SystemTrayManager
from dns import DNSSettingsDialog
from urls import AUTHOR_URL, INFO_URL
from updater import check_for_update
from strategy_selector import StrategySelector

WIDTH = 450
HEIGHT = 700

def get_last_strategy():
    """Получает последнюю выбранную стратегию обхода из реестра"""
    try:
        registry = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Zapret"
        )
        value, _ = winreg.QueryValueEx(registry, "LastStrategy")
        winreg.CloseKey(registry)
        return value
    except:
        # По умолчанию возвращаем None, чтобы использовать первую стратегию из списка
        return "Оригинальная bol-van v2 (07.04.2025)"
    
def set_last_strategy(strategy_name):
    """Сохраняет последнюю выбранную стратегию обхода в реестр"""
    try:
        # Пытаемся открыть ключ, если его нет - создаем
        try:
            registry = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Zapret",
                0, 
                winreg.KEY_WRITE
            )
        except:
            registry = winreg.CreateKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Zapret"
            )
        
        # Записываем значение
        winreg.SetValueEx(registry, "LastStrategy", 0, winreg.REG_SZ, strategy_name)
        winreg.CloseKey(registry)
        return True
    except Exception as e:
        print(f"Ошибка при сохранении стратегии: {str(e)}")
        return False

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def get_version():
    """Возвращает текущую версию программы"""
    return APP_VERSION

BIN_DIR = os.path.join(os.getcwd(), "bin")     # при необходимости переопределите

import platform
import subprocess
import ctypes

def remove_windows_terminal_if_win11():

    from log import log
    """
    На Windows 11 удаляет Windows Terminal (Store-версию) двумя способами:
    1) `Remove-AppxPackage` – удаляет у текущего пользователя
    2) `Remove-AppxProvisionedPackage` – убирает «заготовку» для новых учёток

    Требуются права администратора.  
    При любой ошибке пишет в лог, но не прерывает запуск программы.
    """
    try:
        # 2. Проверяем права администратора
        if not ctypes.windll.shell32.IsUserAnAdmin():
            log("remove_windows_terminal: нет прав администратора – пропуск")
            return

        log("Удаляем Windows Terminal…")

        # 3. Команды PowerShell
        ps_remove_user = (
            'Get-AppxPackage -Name Microsoft.WindowsTerminal '
            '| Remove-AppxPackage -AllUsers'
        )
        ps_remove_prov = (
            'Get-AppxProvisionedPackage -Online '
            '| Where-Object {$_.PackageName -like "*WindowsTerminal*"} '
            '| Remove-AppxProvisionedPackage -Online'
        )

        for cmd in (ps_remove_user, ps_remove_prov):
            subprocess.run(
                ["powershell", "-NoLogo", "-NoProfile", "-Command", cmd],
                check=False,  # ошибки не критичны
                creationflags=subprocess.CREATE_NO_WINDOW
            )

        log("Windows Terminal удалён (или не был установлен).")

    except Exception as e:
        log(f"remove_windows_terminal: {e}")

def remove_scheduler_tasks():
    """Принудительно удаляет все задачи планировщика, связанные с Zapret"""
    try:
        from log import log
        task_name = "ZapretCensorliber"
        
        # Проверяем существование задачи
        check_cmd = f'schtasks /Query /TN "{task_name}" 2>nul'
        result = subprocess.run(check_cmd, shell=True, capture_output=True)
        
        if result.returncode == 0:
            log(f"Обнаружена задача планировщика {task_name}, удаляем...", level="INFO")
            delete_cmd = f'schtasks /Delete /TN "{task_name}" /F'
            subprocess.run(delete_cmd, shell=True, check=False)
            return True
        
        return False  # Задача не найдена
    except Exception as e:
        from log import log
        log(f"Ошибка при удалении задачи планировщика: {str(e)}", level="ERROR")
        return False

class ProcessMonitorThread(QThread):
    """Поток для мониторинга процесса winws.exe"""
    processStatusChanged = pyqtSignal(bool)  # Сигнал: процесс запущен/остановлен
    
    def __init__(self, dpi_starter):
        super().__init__()
        self.dpi_starter = dpi_starter
        self.running = True
        self.current_status = None
    
    def run(self):
        from log import log
        log("Поток мониторинга процесса запущен", level="INFO")
        
        while self.running:
            try:
                # Проверяем текущий статус процесса
                is_running = self.dpi_starter.check_process_running(silent=True)
                
                # Если статус изменился, отправляем сигнал
                if is_running != self.current_status:
                    log(f"Изменение статуса процесса winws.exe: {is_running}", level="INFO")
                    self.current_status = is_running
                    self.processStatusChanged.emit(is_running)
            except Exception as e:
                log(f"Ошибка в потоке мониторинга: {str(e)}", level="ERROR")
            
            # Проверка каждые 2 секунды достаточна
            self.msleep(2000)
    
    def stop(self):
        """Останавливает поток мониторинга"""
        self.running = False
        self.wait()

class LupiDPIApp(QWidget):
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
        """Открывает диалог выбора стратегии."""
        try:
            if not hasattr(self, 'strategy_manager') or not self.strategy_manager:
                from log import log
                log("Ошибка: менеджер стратегий не инициализирован", level="ERROR")
                self.set_status("Ошибка: менеджер стратегий не инициализирован")
                return
            
            # Получаем текущую выбранную стратегию из метки
            current_strategy = self.current_strategy_label.text()
            if current_strategy == "Не выбрана":
                current_strategy = get_last_strategy()
            
            # Создаем и показываем диалог выбора стратегии
            selector = StrategySelector(
                parent=self,
                strategy_manager=self.strategy_manager,
                current_strategy_name=current_strategy
            )
            
            # Подключаем сигнал выбора стратегии
            selector.strategySelected.connect(self.on_strategy_selected_from_dialog)
            
            # Показываем диалог
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
            log(f"Получены стратегии: {list(strategies.keys())}", level="DEBUG")
            for strategy_id, info in strategies.items():
                log(f"Стратегия ID: {strategy_id}, Name: {info.get('name')}, Path: {info.get('file_path')}", level="DEBUG")
            
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
        # Добавляем флаг инициализации
        self.initializing = True
        
        # Добавляем флаг защиты процесса от автоматического завершения
        self.protected_process = True
        self.init_process_monitor()
        
        # Инициализируем последнее время смены стратегии
        self.last_strategy_change_time = time.time()

        # Инициализируем Discord Manager
        from discord import DiscordManager
        self.discord_manager = DiscordManager(status_callback=self.set_status)

        # Инициализируем hosts_manager
        self.hosts_manager = HostsManager(status_callback=self.set_status)
        
        # Инициализируем менеджер стратегий
        self.init_strategy_manager()
        
        # Инициализируем менеджер тем
        self.theme_manager = ThemeManager(
            app=QApplication.instance(),
            widget=self,
            status_label=self.status_label,
            author_label=self.author_label,
            support_label=self.support_label,
            bin_folder=BIN_FOLDER,
            author_url=AUTHOR_URL,
            bol_van_url=self.bol_van_url
        )
        
        self.theme_combo.setCurrentText(self.theme_manager.current_theme)
        self.theme_manager.apply_theme()
        
        # Инициализируем менеджер служб
        self.service_manager = ServiceManager(
            winws_exe=WINWS_EXE,
            bin_folder=BIN_FOLDER,
            lists_folder=LISTS_FOLDER,
            status_callback=self.set_status,
            ui_callback = self.update_ui    
        )
        
        # Проверяем и обновляем UI службы/задачи
        autostart_running = self.service_manager.check_autostart_exists()
        self.update_autostart_ui(autostart_running)

        service_running = self.service_manager.check_service_exists()
        self.update_autostart_ui(service_running)
        
        # Обновляем UI состояния запуска
        self.update_ui(running=True)
        
        # Проверяем наличие необходимых файлов
        self.set_status("Проверка файлов...")
        self.dpi_starter.download_files(DOWNLOAD_URLS)
        
        # Безопасно запускаем DPI после инициализации всех менеджеров
        # Увеличиваем задержку до 4 секунд, чтобы уменьшить риск конфликтов
        QTimer.singleShot(4000, self.delayed_dpi_start)
        
        # Обновляем состояние кнопки прокси через 4.5 секунды
        QTimer.singleShot(4500, self.update_proxy_button_state)
        
        # Снимаем флаг инициализации и защиты через 8 секунд
        QTimer.singleShot(8000, self.finish_initialization)


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
            QTimer.singleShot(1000, self.delayed_dpi_start)
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
        
        # Если автозапуск не активен и процесс не запущен, выполняем обычный запуск
        log("Выполняем отложенный запуск DPI", level="INFO")
        self.dpi_starter.start_dpi(delay_ms=1000)   # задержка 1 с
    
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
                # Запускаем с задержкой 500 мс
                QTimer.singleShot(500, lambda: self.dpi_starter.start_dpi(selected_mode=strategy_name))
        else:
            log("DPI Starter не инициализирован, пропускаем проверку процесса", level="WARNING")
        
        log("Процесс инициализации завершен", level="INFO")

    def __init__(self, fast_load=False):
        self.fast_load = fast_load

        self.status_timer = None  # Удаляем стандартный таймер
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
        self.init_ui()
        
        # Инициализируем атрибуты для работы со стратегиями
        self.current_strategy_id = None
        self.current_strategy_name = None
        
        # При быстрой загрузке откладываем тяжелые операции
        if not self.fast_load:
            self.initialize_managers_and_services()
        
        # Инициализируем системный трей после создания всех элементов интерфейса
        self.tray_manager = SystemTrayManager(
            parent=self,
            icon_path=os.path.abspath(ICON_PATH),
            app_version=APP_VERSION
        )

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
    
    def delayed_combo_enabler(self):
        from log import log
        """Повторно проверяет и активирует комбо-боксы через таймер"""
        if self.force_enable_combos():
            # Если успешно активировали, останавливаемся
            log("Комбо-бокс тем успешно активирован")
        else:
            # Если нет, повторяем через полсекунды
            log("Повторная попытка активации комбо-бокса тем")
            QTimer.singleShot(100, self.delayed_combo_enabler)

    def perform_delayed_checks(self):
        """Выполняет отложенные проверки после отображения UI"""
        if self.fast_load:
            # Первая попытка активации комбо-боксов
            self.force_enable_combos()
            
            # Инициализируем менеджеры и службы
            self.initialize_managers_and_services()
            
            # Вторая попытка активации комбо-боксов после инициализации
            self.force_enable_combos()
            
            # Запускаем таймер для повторных проверок активации
            # Это гарантирует, что комбо-боксы точно станут активными
            QTimer.singleShot(100, self.delayed_combo_enabler)

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

    def stop_dpi(self):
        """Останавливает процесс DPI, используя прямые команды остановки"""
        try:
            from log import log
            log("Остановка Zapret", level="INFO")
            
            # Используем прямые команды остановки вместо ненадежного stop.bat
            process_stopped = False
            
            # Метод 1: taskkill (наиболее надежный)
            log("Метод 1: Остановка через taskkill /F /IM winws.exe /T", level="INFO")
            try:
                subprocess.run(
                    "taskkill /F /IM winws.exe /T", 
                    shell=True, 
                    check=False, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE
                )
                # Даем время системе на обработку команды
                time.sleep(1)
                if not self.dpi_starter.check_process_running():
                    process_stopped = True
                    log("Процесс успешно остановлен через taskkill", level="INFO")
            except Exception as e:
                log(f"Ошибка при использовании taskkill: {str(e)}", level="ERROR")
            
            # Если taskkill не помог, пробуем метод 2: PowerShell
            if not process_stopped:
                log("Метод 2: Остановка через PowerShell", level="INFO")
                try:
                    subprocess.run(
                        'powershell -Command "Get-Process winws -ErrorAction SilentlyContinue | Stop-Process -Force"',
                        shell=True,
                        check=False,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE
                    )
                    # Даем время системе на обработку команды
                    time.sleep(1)
                    if not self.dpi_starter.check_process_running():
                        process_stopped = True
                        log("Процесс успешно остановлен через PowerShell", level="INFO")
                except Exception as e:
                    log(f"Ошибка при использовании PowerShell: {str(e)}", level="ERROR")
            
            # Метод 3: wmic
            if not process_stopped:
                log("Метод 3: Остановка через wmic", level="INFO")
                try:
                    subprocess.run(
                        "wmic process where name='winws.exe' call terminate",
                        shell=True,
                        check=False,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE
                    )
                    # Даем время системе на обработку команды
                    time.sleep(1)
                    if not self.dpi_starter.check_process_running():
                        process_stopped = True
                        log("Процесс успешно остановлен через wmic", level="INFO")
                except Exception as e:
                    log(f"Ошибка при использовании wmic: {str(e)}", level="ERROR")
            
            # Дополнительно останавливаем службы
            try:
                log("Остановка служб WinDivert", level="INFO")
                subprocess.run("sc stop windivert", shell=True, check=False)
                subprocess.run("sc delete windivert", shell=True, check=False)
            except Exception as e:
                log(f"Ошибка при остановке служб: {str(e)}", level="ERROR")
            
            # Финальная проверка
            if self.dpi_starter.check_process_running():
                log("ВНИМАНИЕ: Не удалось остановить все процессы winws.exe", level="WARNING")
                self.set_status("Не удалось полностью остановить Zapret")
            else:
                # Обновляем UI
                self.update_ui(running=False)
                self.set_status("Zapret успешно остановлен")
                log("Запрет успешно остановлен", level="INFO")
            
            # Обновляем статус
            self.on_process_status_changed(self.dpi_starter.check_process_running(silent=True))
                
        except Exception as e:
            from log import log
            log(f"Ошибка при остановке DPI: {str(e)}", level="ERROR")
            self.set_status(f"Ошибка при остановке: {str(e)}")

    def install_service(self) -> bool:
        """
        Вызывается из GUI при нажатии «Автозапуск».
        Делегирует всё ServiceManager’у.
        """
        from log import log

        # текущая стратегия
        selected = getattr(self, "current_strategy_name", None) \
               or self.current_strategy_label.text()
        if selected == "Не выбрана":
            selected = get_last_strategy()

        if not selected:
            QMessageBox.critical(self, "Ошибка", "Стратегия не выбрана")
            self.set_status("Ошибка: стратегия не выбрана")
            return False

        log(f"Установка автозапуска для стратегии: {selected}", level="INFO")

        ok = self.service_manager.install_autostart_by_strategy(
                selected_mode=selected,
                strategy_manager=self.strategy_manager)

        if ok:
            self.update_autostart_ui(True)
            QMessageBox.information(self, "Успех",
                                     f"Автозапуск настроен для режима:\n{selected}")
            return True

        QMessageBox.critical(self, "Ошибка",
                             "Не удалось настроить автозапуск.\nСм. журнал.")
        return False
    
    def remove_service(self):
        """Удаляет службу DPI"""
        if self.service_manager.remove_service():
            self.update_autostart_ui(False)
            self.on_process_status_changed(self.dpi_starter.check_process_running(silent=True))

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

    def init_ui(self):
        """Creates the user interface elements."""
        self.setStyleSheet(STYLE_SHEET)
        layout = QVBoxLayout()

        header_layout = QVBoxLayout()

        title_label = QLabel('Zapret GUI')
        title_label.setStyleSheet(f"{COMMON_STYLE} font: 16pt Arial;")
        header_layout.addWidget(title_label, alignment=Qt.AlignCenter)
        layout.addLayout(header_layout)

        # Добавляем разделитель
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)

        ################# Статус программы #################
        status_layout = QVBoxLayout()
        
        # Статус запуска программы
        process_status_layout = QHBoxLayout()
        process_status_label = QLabel("Статус программы:")
        process_status_label.setStyleSheet("font-weight: bold;")
        process_status_layout.addWidget(process_status_label)
        
        self.process_status_value = QLabel("проверка...")
        process_status_layout.addWidget(self.process_status_value)
        process_status_layout.addStretch(1)  # Добавляем растяжку для центрирования
        
        status_layout.addLayout(process_status_layout)

        layout.addLayout(status_layout)

        ############# Стратегия обхода блокировок #############
        strategy_layout = QVBoxLayout()

        # Сначала добавляем метку с текущей стратегией на всю ширину
        strategy_header = QLabel("Текущая стратегия:")
        strategy_header.setStyleSheet(f"{COMMON_STYLE} font-weight: bold;")
        strategy_header.setAlignment(Qt.AlignCenter)
        strategy_layout.addWidget(strategy_header)

        # Метка с текущей стратегией (увеличиваем шрифт и делаем его заметным)
        self.current_strategy_label = QLabel("Не выбрана")
        self.current_strategy_label.setStyleSheet(f"{COMMON_STYLE} font-weight: bold; font-size: 12pt; color: #0077ff;")
        self.current_strategy_label.setAlignment(Qt.AlignCenter)
        self.current_strategy_label.setWordWrap(True)  # Разрешаем перенос длинных названий
        self.current_strategy_label.setMinimumHeight(40)  # Достаточная высота для двух строк текста
        strategy_layout.addWidget(self.current_strategy_label)

        # Добавляем небольшой интервал между меткой и кнопкой
        strategy_layout.addSpacing(5)

        # Затем добавляем кнопку выбора стратегии
        self.select_strategy_btn = RippleButton('Сменить стратегию обхода блокировок...', self, "0, 119, 255")
        self.select_strategy_btn.setStyleSheet(BUTTON_STYLE.format("0, 119, 255"))
        self.select_strategy_btn.setMinimumHeight(BUTTON_HEIGHT)
        self.select_strategy_btn.clicked.connect(self.select_strategy)
        strategy_layout.addWidget(self.select_strategy_btn)

        layout.addLayout(strategy_layout)

        ################## Кнопки управления #################
        from PyQt5.QtWidgets import QGridLayout

        self.start_btn = RippleButton('Запустить Zapret', self, "54, 153, 70")
        self.start_btn.setStyleSheet(BUTTON_STYLE.format("54, 153, 70"))
        self.start_btn.setMinimumHeight(BUTTON_HEIGHT)
        self.start_btn.clicked.connect(self.dpi_starter.start_dpi)

        self.stop_btn = RippleButton('Остановить Zapret', self, "255, 93, 174")
        self.stop_btn.setStyleSheet(BUTTON_STYLE.format("255, 93, 174"))
        self.stop_btn.setMinimumHeight(BUTTON_HEIGHT)
        self.stop_btn.clicked.connect(self.stop_dpi)

        self.autostart_enable_btn = RippleButton('Вкл. автозапуск', self, "54, 153, 70")
        self.autostart_enable_btn.setStyleSheet(BUTTON_STYLE.format("54, 153, 70"))
        self.autostart_enable_btn.setMinimumHeight(BUTTON_HEIGHT)
        self.autostart_enable_btn.clicked.connect(self.install_service)

        self.autostart_disable_btn = RippleButton('Выкл. автозапуск', self, "255, 93, 174") 
        self.autostart_disable_btn.setStyleSheet(BUTTON_STYLE.format("255, 93, 174"))
        self.autostart_disable_btn.setMinimumHeight(BUTTON_HEIGHT)
        self.autostart_disable_btn.clicked.connect(self.remove_service)

        self.button_grid = QGridLayout()          # ← сохранить как атрибут
        button_grid = self.button_grid            # локальное alias, чтобы не менять дальше

        # Устанавливаем равномерное распределение пространства между колонками
        button_grid.setColumnStretch(0, 1)  # Левая колонка растягивается с коэффициентом 1
        button_grid.setColumnStretch(1, 1)  # Правая колонка растягивается с коэффициентом 1

        # Добавляем кнопки напрямую в grid layout
        button_grid.addWidget(self.start_btn, 0, 0)
        button_grid.addWidget(self.autostart_enable_btn, 0, 1)
        button_grid.addWidget(self.stop_btn, 0, 0)
        button_grid.addWidget(self.autostart_disable_btn, 0, 1)

        # По умолчанию устанавливаем правильную видимость кнопок
        self.start_btn.setVisible(True)
        self.stop_btn.setVisible(False)
        self.autostart_enable_btn.setVisible(True)
        self.autostart_disable_btn.setVisible(False)

        # Определяем кнопки
        button_configs = [            
            ('Открыть папку Zapret', self.open_folder, "0, 119, 255", 2, 0),
            ('Тест соединения', self.open_connection_test, "0, 119, 255", 2, 1),
            ('Обновить список сайтов', self.update_other_list, "0, 119, 255", 3, 0),
            ('Добавить свои сайты', self.open_general, "0, 119, 255", 3, 1),
            ('Обновить winws.exe', self.update_winws_exe, "0, 119, 255", 4, 0),
            ('Настройка DNS-серверов', self.open_dns_settings, "0, 119, 255", 4, 1),
            ('Разблокировать ChatGPT, Spotify, Notion и др.', self.toggle_proxy_domains, "218, 165, 32", 5, 0, 2),  # col_span=2
            ('Что это такое?', self.open_info, "38, 38, 38", 6, 0),
            ('Логи', self.show_logs, "38, 38, 38", 6, 1),  # col_span=2
            ('Проверить обновления', lambda: check_for_update(parent=self, status_callback=self.set_status), "38, 38, 38", 7, 0, 2),  # col_span=2
        ]

        # Создаем и размещаем кнопки в сетке
        for button_info in button_configs:
            text, callback, color, row, col = button_info[:5]
            
            # Определяем col_span
            col_span = button_info[5] if len(button_info) > 5 else (2 if (row == 10) else 1)
            
            btn = RippleButton(text, self, color)
            btn.setStyleSheet(BUTTON_STYLE.format(color))
            btn.setMinimumHeight(BUTTON_HEIGHT)
            btn.clicked.connect(callback)
            
            button_grid.addWidget(btn, row, col, 1, col_span)
            
            # Сохраняем ссылку на кнопку разблокировки
            if 'ChatGPT' in text:
                self.proxy_button = btn
            
            # Сохраняем ссылку на кнопку запуска
            if text == 'Запустить Zapret':
                self.start_btn = btn
        
        # Добавляем сетку с кнопками в основной лейаут
        layout.addLayout(button_grid)

        theme_layout = QVBoxLayout()
        theme_label = QLabel('Тема оформления:')
        theme_label.setStyleSheet(COMMON_STYLE)
        theme_layout.addWidget(theme_label, alignment=Qt.AlignCenter)
    
        self.theme_combo = QComboBox(self)
        self.theme_combo.setStyleSheet(f"{COMMON_STYLE} text-align: center;")
        self.theme_combo.addItems(THEMES.keys())
        self.theme_combo.currentTextChanged.connect(self.change_theme)

        theme_layout.addWidget(self.theme_combo)
        layout.addLayout(theme_layout)

        # Предупреждение
        #self.warning_label = QLabel('Не закрывайте открывшийся терминал!')  # Доступ нужен
        #self.warning_label.setStyleSheet("color:rgb(255, 93, 174);")
        #layout.addWidget(self.warning_label, alignment=Qt.AlignCenter)

        # Статусная строка
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color:rgb(0, 0, 0);")
        
        layout.addWidget(self.status_label)
        
        spacer = QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding)
        layout.addItem(spacer)

        self.author_label = QLabel('Автор: <a href="https://t.me/bypassblock">t.me/bypassblock</a>')
        self.support_label = QLabel('Поддержка: <a href="https://t.me/youtubenotwork">t.me/youtubenotwork</a>\n или на почту <a href="mail:fuckyourkn@yandex.ru">fuckyourkn@yandex.ru</a>')
        self.bol_van_url = QLabel('<a href="https://github.com/bol-van">github.com/bol-van</a>')

        self.bol_van_url.setOpenExternalLinks(True)  # Разрешаем открытие внешних ссылок
        self.bol_van_url.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.bol_van_url)

        self.author_label.setOpenExternalLinks(True)  # Разрешаем открытие внешних ссылок
        self.author_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.author_label)

        self.support_label.setOpenExternalLinks(True)  # Разрешаем открытие внешних ссылок
        self.support_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.support_label)
        
        self.setLayout(layout)
        self.setMinimumSize(WIDTH, HEIGHT) # Минимальный размер окна

def main():
    try:
        from log import log
        log("========================= ZAPRET ЗАПУСКАЕТСЯ ========================", level="START")
    except Exception as e:
        log(f"Failed to initialize logger: {e}", level="ERROR")

    start_in_tray = False

    # Проверяем наличие и удаляем устаревшие задачи планировщика
    remove_scheduler_tasks()
    
    try:
        from check_start import display_startup_warnings
        can_continue = display_startup_warnings()
        if not can_continue:
            sys.exit(1)

        remove_windows_terminal_if_win11()  # Удаляем терминал Windows 11, если он установлен
        
        app = QApplication(sys.argv)
        
    except Exception as e:
        log(f"Failed to perform startup checks: {e}", level="ERROR")
        # Показываем ошибку пользователю
        QMessageBox.critical(None, "Ошибка при проверке запуска", 
                         f"Не удалось выполнить проверки запуска: {str(e)}")
        sys.exit(1)
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--version":
            log(APP_VERSION)
            sys.exit(0)
        elif sys.argv[1] == "--tray":
            start_in_tray = True
        elif sys.argv[1] == "--update" and len(sys.argv) > 3:
            # Режим обновления: updater.py запускает main.py --update old_exe new_exe
            old_exe = sys.argv[2]
            new_exe = sys.argv[3]
            
            # Ждем, пока старый exe-файл будет доступен для замены
            for i in range(10):  # 10 попыток с интервалом 0.5 сек
                try:
                    if not os.path.exists(old_exe) or os.access(old_exe, os.W_OK):
                        break
                    time.sleep(0.5)
                except:
                    time.sleep(0.5)
            
            # Копируем новый файл поверх старого
            try:
                shutil.copy2(new_exe, old_exe)
                # Запускаем обновленное приложение
                subprocess.Popen([old_exe])
            except Exception as e:
                log(f"Ошибка при обновлении: {str(e)}", level="ERROR")
            finally:
                # Удаляем временный файл
                try:
                    os.remove(new_exe)
                except:
                    pass
                sys.exit(0)

    # ВАЖНЫЙ МОМЕНТ - проверяем админские права до создания окна
    if not is_admin():
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
        sys.exit(0)
    
    try:
        # Создаем окно с параметром fast_load=True
        window = LupiDPIApp(fast_load=True)

        # Если запуск в трее, не показываем окно сразу
        if not start_in_tray:
            window.show()
        
        # удаляем устаревшую службу ZapretCensorliber, если она ещё есть
        def _remove_legacy_service():
            if hasattr(window, "service_manager") and window.service_manager:
                window.service_manager.remove_legacy_windows_service()
                log("Входим в службу", level="SERVICE")
            else:
                log("Менеджер служб не инициализирован", level="SERVICE")

        QTimer.singleShot(0, _remove_legacy_service)        
        # Выполняем дополнительные проверки ПОСЛЕ отображения UI
        window.perform_delayed_checks()
        
        # Если запуск в трее, уведомляем пользователя
        if start_in_tray and hasattr(window, 'tray_manager'):
            window.tray_manager.show_notification("Zapret работает в трее", 
                                                    "Приложение запущено в фоновом режиме")
                    
        # Дополнительная гарантия, что комбо-боксы будут активны
        window.force_enable_combos()

        sys.exit(app.exec_())
        
    except Exception as e:
        QMessageBox.critical(None, "Ошибка", f"Произошла ошибка: {str(e)}")
        log(f"Ошибка при запуске приложения: {str(e)}", level="ERROR")
        sys.exit(1)

if __name__ == "__main__":
    main()