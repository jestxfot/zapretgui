# main.py

"""
pip install pyinstaller packaging PyQt6 requests pywin32 python-telegram-bot psutil qt_material
"""

import sys, os, subprocess, webbrowser, time

from PyQt6.QtCore    import QThread
from PyQt6.QtWidgets import QMessageBox, QWidget, QApplication, QMenu

from ui.theme import ThemeManager, BUTTON_STYLE, COMMON_STYLE
from ui.main_window import MainWindowUI

from startup.admin_check import is_admin

from config.process_monitor import ProcessMonitorThread
from heavy_init_worker import HeavyInitWorker
from downloader import DOWNLOAD_URLS

from config import THEME_FOLDER, BAT_FOLDER, INDEXJSON_FOLDER, WINWS_EXE, ICON_PATH, ICON_TEST_PATH, WIDTH, HEIGHT
from config import get_last_strategy, set_last_strategy
from config import APP_VERSION # build_info moved to config/__init__.py
from utils import run_hidden

from hosts.hosts import HostsManager

from autostart.checker import CheckerManager
from autostart.autostart_remove import AutoStartCleaner

from dpi.start import DPIStarter

from tray import SystemTrayManager
from dns import DNSSettingsDialog
from altmenu.app_menubar import AppMenuBar
from log import log

from config import CHANNEL # config/__init__.py

def _set_attr_if_exists(name: str, on: bool = True) -> None:
    """
    Безопасно включает атрибут, если он есть в текущей версии Qt.
    Работает и в PyQt5, и в PyQt6.
    """

    from PyQt6.QtCore import QCoreApplication
    from PyQt6.QtCore import Qt
    
    # 1) PyQt6 ‑ ищем в Qt.ApplicationAttribute
    attr = getattr(Qt.ApplicationAttribute, name, None)
    # 2) PyQt5 ‑ там всё лежит прямо в Qt
    if attr is None:
        attr = getattr(Qt, name, None)

    if attr is not None:
        QCoreApplication.setAttribute(attr, on)

def _handle_update_mode():
    """
    updater.py запускает:
        main.py --update <old_exe> <new_exe>

    Меняем файл и перезапускаем обновлённый exe.
    """
    import os, sys, time, shutil, subprocess
    

    if len(sys.argv) < 4:
        log("--update: недостаточно аргументов", "❌ ERROR")
        return

    old_exe, new_exe = sys.argv[2], sys.argv[3]

    # ждём, пока старый exe освободится
    for _ in range(10):  # 10 × 0.5 c = 5 сек
        if not os.path.exists(old_exe) or os.access(old_exe, os.W_OK):
            break
        time.sleep(0.5)

    try:
        shutil.copy2(new_exe, old_exe)
        run_hidden([old_exe])          # запускаем новую версию
        log("Файл обновления применён", "INFO")
    except Exception as e:
        log(f"Ошибка в режиме --update: {e}", "❌ ERROR")
    finally:
        try:
            os.remove(new_exe)
        except FileNotFoundError:
            pass
    # ничего не возвращаем — вызывающая сторона сделает sys.exit(0)

from PyQt6.QtCore import QThread, pyqtSignal

class DNSWorker(QThread):
    """Worker для применения DNS в отдельном потоке"""
    status_update = pyqtSignal(str)
    
    def run(self):
        try:
            from dns import apply_force_dns_if_enabled, ensure_default_force_dns
            
            # 0) создаём ключ ForceDNS=1, если его нет
            ensure_default_force_dns()
            
            # 1) применяем принудительный DNS с thread-safe callback
            def safe_status_callback(msg):
                self.status_update.emit(msg)
            
            apply_force_dns_if_enabled(status_callback=safe_status_callback)
            
        except Exception as e:
            log(f"Ошибка в DNS worker: {e}", "❌ ERROR")
            
class LupiDPIApp(QWidget, MainWindowUI):
    def closeEvent(self, event):
        """Обрабатывает событие закрытия окна"""
        # ✅ УСТАНАВЛИВАЕМ флаг закрытия
        self._is_exiting = True
        
        # Останавливаем поток мониторинга
        if hasattr(self, 'process_monitor') and self.process_monitor is not None:
            self.process_monitor.stop()
        
        # ✅ ОСТАНАВЛИВАЕМ ВСЕ АСИНХРОННЫЕ ОПЕРАЦИИ без уведомлений
        try:
            if hasattr(self, '_dpi_start_thread') and self._dpi_start_thread:
                try:
                    if self._dpi_start_thread.isRunning():
                        self._dpi_start_thread.quit()
                        self._dpi_start_thread.wait(1000)
                except RuntimeError:
                    pass
            
            if hasattr(self, '_dpi_stop_thread') and self._dpi_stop_thread:
                try:
                    if self._dpi_stop_thread.isRunning():
                        self._dpi_stop_thread.quit()
                        self._dpi_stop_thread.wait(1000)
                except RuntimeError:
                    pass
        except Exception as e:
            log(f"Ошибка при очистке потоков: {e}", "❌ ERROR")
        
        # Стандартная обработка события
        super().closeEvent(event)
        
    def set_status(self, text):
        """Sets the status text."""
        self.status_label.setText(text)

    def update_ui(self, running):
        """Обновляет состояние кнопок в зависимости от статуса запуска"""
        autostart_active = False
        if hasattr(self, 'service_manager'):
            autostart_active = self.service_manager.check_autostart_exists()
        
        # Если автозапуск НЕ активен, управляем кнопками запуска/остановки
        if not autostart_active:
            if running:
                # Показываем кнопку остановки
                self.start_stop_stack.setCurrentWidget(self.stop_btn)
            else:
                # Показываем кнопку запуска
                self.start_stop_stack.setCurrentWidget(self.start_btn)
        
    def check_if_process_started_correctly(self):
        """Проверяет, что процесс успешно запустился и продолжает работать"""
        
        
        # Проверяем флаг намеренного запуска и сбрасываем его
        intentional_start = getattr(self, 'intentional_start', False)
        
        # Не сбрасываем флаг intentional_start здесь, чтобы предотвратить конфликты
        # self.intentional_start = False
        
        # Если процесс находится в процессе перезапуска или был остановлен намеренно, пропускаем проверку
        if hasattr(self, 'process_restarting') and self.process_restarting:
            log("Пропускаем проверку: процесс перезапускается", level="INFO") 
            self.process_restarting = False  # Сбрасываем флаг
            self.on_process_status_changed(self.dpi_starter.check_process_running_wmi(silent=True))
            return
            
        if hasattr(self, 'manually_stopped') and self.manually_stopped:
            log("Пропускаем проверку: процесс остановлен вручную", level="INFO")
            self.manually_stopped = False  # Сбрасываем флаг
            self.on_process_status_changed(self.dpi_starter.check_process_running_wmi(silent=True))
            return
        
        # Проверяем, был ли недавно изменен режим (стратегия)
        current_time = time.time()
        if hasattr(self, 'last_strategy_change_time') and current_time - self.last_strategy_change_time < 5:
            # Пропускаем проверку, если стратегия была изменена менее 5 секунд назад
            log("Пропускаем проверку: недавно изменена стратегия", level="INFO")
            self.on_process_status_changed(self.dpi_starter.check_process_running_wmi(silent=True))
            return
        
        # Проверяем, запущен ли процесс на данный момент
        process_running = self.dpi_starter.check_process_running_wmi()
        
        # Если процесс запущен, всё в порядке
        if process_running:
            log("Процесс запущен и работает нормально", level="INFO")
            self.update_ui(running=True)
            return
            
        # Если флаг намеренного запуска установлен, но процесс не запущен
        if intentional_start and not process_running:
            # Вместо показа ошибки просто логируем информацию
            log("Процесс не запустился после намеренного запуска", level="⚠ WARNING")
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
        self.on_process_status_changed(self.dpi_starter.check_process_running_wmi(silent=True))
        
    def select_strategy(self):
        """Открывает диалог выбора стратегии БЕЗ загрузки из интернета"""
        try:
            if not hasattr(self, 'strategy_manager') or not self.strategy_manager:
                log("Ошибка: менеджер стратегий не инициализирован", "❌ ERROR")
                self.set_status("Ошибка: менеджер стратегий не инициализирован")
                return

            # ✅ НОВОЕ: Всегда используем только локальные стратегии
            local_strategies = self.strategy_manager.get_local_strategies_only()
            
            if not local_strategies:
                # Если локальных стратегий нет, показываем сообщение
                QMessageBox.information(self, "Стратегии не найдены", 
                                    "Локальный список стратегий не найден.\n\n"
                                    "Нажмите кнопку обновления для загрузки стратегий из интернета.")
                return

            # Показываем диалог с локальными стратегиями
            self._show_strategy_dialog()

        except Exception as e:
            log(f"Ошибка при открытии диалога выбора стратегии: {e}", "❌ ERROR")
            self.set_status(f"Ошибка при выборе стратегии: {e}")

    def download_strategies_list(self):
        """НОВЫЙ МЕТОД: Явно загружает список стратегий из интернета"""
        from PyQt6.QtCore import QThread, QObject, pyqtSignal
        
        class StrategyListDownloader(QObject):
            finished = pyqtSignal(bool, str, int)  # success, error_msg, count
            progress = pyqtSignal(str)
            
            def __init__(self, strategy_manager):
                super().__init__()
                self.strategy_manager = strategy_manager
            
            def run(self):
                try:
                    self.progress.emit("Загрузка списка стратегий из интернета...")
                    
                    strategies = self.strategy_manager.download_strategies_index_from_internet()
                    
                    if strategies:
                        self.finished.emit(True, "", len(strategies))
                    else:
                        self.finished.emit(False, "Не удалось загрузить стратегии", 0)
                        
                except Exception as e:
                    self.finished.emit(False, str(e), 0)
        
        # Создаем и запускаем поток
        self._download_thread = QThread()
        self._download_worker = StrategyListDownloader(self.strategy_manager)
        self._download_worker.moveToThread(self._download_thread)
        
        self._download_thread.started.connect(self._download_worker.run)
        self._download_worker.progress.connect(self.set_status)
        self._download_worker.finished.connect(self._on_strategies_download_finished)
        self._download_worker.finished.connect(self._download_thread.quit)
        self._download_worker.finished.connect(self._download_worker.deleteLater)
        self._download_thread.finished.connect(self._download_thread.deleteLater)
        
        self._download_thread.start()

    def _on_strategies_download_finished(self, success, error_msg, count):
        """Обработчик завершения загрузки списка стратегий"""
        if success:
            self.set_status(f"✅ Загружено {count} стратегий")
            QMessageBox.information(self, "Успех", 
                                f"Список стратегий успешно обновлен.\n"
                                f"Загружено стратегий: {count}")
        else:
            self.set_status(f"❌ Ошибка загрузки: {error_msg}")
            QMessageBox.critical(self, "Ошибка", 
                            f"Не удалось загрузить список стратегий.\n\n"
                            f"Ошибка: {error_msg}")

    def download_strategy_files(self):
        """НОВЫЙ МЕТОД: Загружает .bat файлы выбранных стратегий"""
        # Здесь можно добавить диалог выбора стратегий для загрузки
        # или загружать все стратегии из списка
        pass

    def _show_strategy_dialog(self):
        """Показывает диалог выбора стратегии"""
        try:
            # Проверяем, не открыт ли уже диалог
            if hasattr(self, '_strategy_selector_dialog') and self._strategy_selector_dialog:
                if self._strategy_selector_dialog.isVisible():
                    # Поднимаем существующее окно на передний план
                    self._strategy_selector_dialog.raise_()
                    self._strategy_selector_dialog.activateWindow()
                    return

            # Определяем текущую стратегию
            current_strategy = self.current_strategy_label.text()
            if current_strategy == "Автостарт DPI отключен":
                current_strategy = get_last_strategy()

            # Создаём диалог
            from strategy_menu.selector import StrategySelector
            self._strategy_selector_dialog = StrategySelector(
                parent=self,
                strategy_manager=self.strategy_manager,
                current_strategy_name=current_strategy
            )
            
            # Подключаем сигналы
            self._strategy_selector_dialog.strategySelected.connect(self.on_strategy_selected_from_dialog)
            
            # ✅ ПОКАЗЫВАЕМ БЕЗ БЛОКИРОВКИ!
            self._strategy_selector_dialog.show()  # НЕ exec()!
            
            # Поднимаем на передний план
            self._strategy_selector_dialog.raise_()
            self._strategy_selector_dialog.activateWindow()
            
            log("Открыт диалог выбора стратегии (неблокирующий)", "INFO")
            
        except Exception as e:
            log(f"Ошибка при показе диалога стратегий: {e}", "❌ ERROR")
            self.set_status(f"Ошибка диалога: {e}")
        
    def on_strategy_selected_from_dialog(self, strategy_id, strategy_name):
        """Обрабатывает выбор стратегии из диалога."""
        try:
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
            
            # ✅ ИСПРАВЛЕНИЕ: Получаем полную информацию о стратегии
            try:
                # Получаем информацию о стратегии из менеджера
                strategies = self.strategy_manager.get_strategies_list()
                strategy_info = strategies.get(strategy_id, {})
                
                # Если не удалось получить информацию, создаем минимальную структуру
                if not strategy_info:
                    strategy_info = {
                        'name': strategy_name,
                        'file_path': f"{strategy_id}.bat"
                    }
                    log(f"Не удалось найти информацию о стратегии {strategy_id}, используем базовую", "⚠ WARNING")
                
                # Запускаем стратегию с полной информацией
                self.start_dpi_async(selected_mode=strategy_info)
                
            except Exception as strategy_error:
                log(f"Ошибка при получении информации о стратегии: {strategy_error}", "❌ ERROR")
                # Fallback - запускаем с именем стратегии
                self.start_dpi_async(selected_mode=strategy_name)
            
            # Перезапускаем Discord только если:
            # 1. Это не первый запуск
            # 2. Автоперезапуск включен в настройках
            from discord.discord_restart import get_discord_restart_setting
            if not self.first_start and get_discord_restart_setting():
                self.discord_manager.restart_discord_if_running()
            else:
                self.first_start = False  # Сбрасываем флаг первого запуска
                
        except Exception as e:
            log(f"Ошибка при установке выбранной стратегии: {str(e)}", level="❌ ERROR")
            self.set_status(f"Ошибка при установке стратегии: {str(e)}")

    def update_autostart_ui(self, service_running: bool | None):
        """Обновляет интерфейс при включении/выключении автозапуска"""
        if service_running is None and hasattr(self, 'service_manager'):
            service_running = self.service_manager.check_autostart_exists()

        if service_running:
            # ✅ АВТОЗАПУСК АКТИВЕН
            # Скрываем левую колонку (кнопки запуска/остановки)
            self.start_stop_stack.setVisible(False)
            
            # Показываем кнопку отключения автозапуска
            self.autostart_stack.setCurrentWidget(self.autostart_disable_btn)
            
            # Удаляем стек автозапуска из текущей позиции
            self.button_grid.removeWidget(self.autostart_stack)
            
            # Добавляем его обратно на 2 колонки
            self.button_grid.addWidget(self.autostart_stack, 0, 0, 1, 2)
            
        else:
            # ✅ АВТОЗАПУСК ВЫКЛЮЧЕН
            # Сначала удаляем все виджеты из первой строки
            self.button_grid.removeWidget(self.autostart_stack)
            self.button_grid.removeWidget(self.start_stop_stack)
            
            # Показываем левую колонку
            self.start_stop_stack.setVisible(True)
            
            # Добавляем виджеты в правильном порядке
            self.button_grid.addWidget(self.start_stop_stack, 0, 0)
            self.button_grid.addWidget(self.autostart_stack, 0, 1)
            
            # Показываем кнопку включения автозапуска
            self.autostart_stack.setCurrentWidget(self.autostart_enable_btn)
            
            # Обновляем состояние кнопок запуска/остановки
            process_running = self.dpi_starter.check_process_running_wmi(silent=True) if hasattr(self, 'dpi_starter') else False
            if process_running:
                self.start_stop_stack.setCurrentWidget(self.stop_btn)
            else:
                self.start_stop_stack.setCurrentWidget(self.start_btn)
            
        # Принудительное обновление layout
        self.button_grid.update()
        QApplication.processEvents()

    def show_start_button(self):
        """Показывает кнопку запуска"""
        self.start_stop_stack.setCurrentWidget(self.start_btn)

    def show_stop_button(self):
        """Показывает кнопку остановки"""
        self.start_stop_stack.setCurrentWidget(self.stop_btn)

    def show_autostart_enable_button(self):
        """Показывает кнопку включения автозапуска"""
        self.autostart_stack.setCurrentWidget(self.autostart_enable_btn)

    def show_autostart_disable_button(self):
        """Показывает кнопку отключения автозапуска"""
        self.autostart_stack.setCurrentWidget(self.autostart_disable_btn)

    def update_strategies_list(self, force_update=False):
        """Обновляет список доступных стратегий"""
        try:
            
            
            # Получаем список стратегий
            strategies = self.strategy_manager.get_strategies_list(force_update=force_update)
            
            if not strategies:
                log("Не удалось получить список стратегий", level="❌ ERROR")
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
                if current_strategy == "Автостарт DPI отключен":
                    current_strategy = get_last_strategy()
            
            # Обновляем текущую метку, если стратегия выбрана
            if current_strategy and current_strategy != "Автостарт DPI отключен":
                self.current_strategy_label.setText(current_strategy)
            
            log(f"Загружено {len(strategies)} стратегий", level="INFO")
            
        except Exception as e:
            error_msg = f"Ошибка при обновлении списка стратегий: {str(e)}"
            
            log(error_msg, level="❌ ERROR")
            self.set_status(error_msg)

    def initialize_managers_and_services(self):
        """
        Быстрая (лёгкая) инициализация и запуск HeavyInitWorker.
        """
        
        log("initialize_managers_and_services: quick part", "INFO")

        # --- лёгкие вещи (≈10-50 мс) ----------------------------------
        self.init_process_monitor()
        self.last_strategy_change_time = time.time()

        from discord.discord import DiscordManager
        self.discord_manager = DiscordManager(status_callback=self.set_status)
        self.hosts_manager   = HostsManager   (status_callback=self.set_status)

        # ✅ НОВОЕ: DNS worker в отдельном QThread
        self.dns_worker = DNSWorker()
        self.dns_worker.status_update.connect(self.set_status)
        self.dns_worker.finished.connect(self._on_dns_worker_finished)
        self.dns_worker.start()

        # StrategyManager  (preload=False  ⇒  ничего не скачивает)
        from strategy_menu.manager import StrategyManager
        from config import (STRATEGIES_FOLDER)
        os.makedirs(STRATEGIES_FOLDER, exist_ok=True)

        # Создаем StrategyManager в локальном режиме
        self.strategy_manager = StrategyManager(
            local_dir       = STRATEGIES_FOLDER,
            json_dir        = INDEXJSON_FOLDER,
            status_callback = self.set_status,
            preload         = False
        )

        # Убеждаемся что включен локальный режим
        self.strategy_manager.local_only_mode = True

        # Загружаем только локальные стратегии
        self.strategy_manager.get_local_strategies_only()

        # ThemeManager с передачей donate_checker
        self.theme_manager = ThemeManager(
            app           = QApplication.instance(),
            widget        = self,
            status_label  = self.status_label,
            theme_folder  = THEME_FOLDER,
            donate_checker = self.donate_checker  # ← передаем проверяльщик подписки
        )

        # Обновляем доступные темы в комбо-боксе на основе статуса подписки
        available_themes = self.theme_manager.get_available_themes()
        self.update_theme_combo(available_themes)

        self.theme_combo.setCurrentText(self.theme_manager.current_theme)
        self.theme_manager.apply_theme()

        # CheckerManager
        self.service_manager = CheckerManager(
            winws_exe    = WINWS_EXE,
            status_callback = self.set_status,
            ui_callback     = self.update_ui)

        # стартовое состояние интерфейса
        self.update_autostart_ui(self.service_manager.check_autostart_exists())
        self.update_ui(running=False)

        # НЕ запускаем subscription_timer здесь - он запустится после готовности checker'а

        # Убираем автоматический запуск тяжелой инициализации
        # Запускаем HeavyInitWorker только при необходимости
        from config import get_auto_download_enabled
        
        if get_auto_download_enabled():  # Новая настройка в реестре
            # --- HeavyInitWorker (качает winws.exe, списки и т.п.) --------
            self.set_status("Инициализация…")
            self._start_heavy_init()
        else:
            log("Автозагрузка отключена - работаем с локальными файлами", "INFO")
            self.set_status("Готово (автономный режим)")
            
            # Проверяем локальные файлы
            self._check_local_files()
            
            # Сразу переходим к финальной инициализации
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(100, lambda: self._on_heavy_done(True, ""))

    def _on_dns_worker_finished(self):
        """Обработчик завершения DNS worker"""
        log("DNS worker завершен", "DNS")
        if hasattr(self, 'dns_worker'):
            self.dns_worker.deleteLater()
            self.dns_worker = None

    def _start_heavy_init(self):
        """Запускает тяжелую инициализацию"""
        self.set_status("Запуск инициализации...")
        
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

        # ДОБАВЛЯЕМ больше отладки
        self._hwrk.progress.connect(lambda msg: log(f"HeavyInit прогресс: {msg}", "DEBUG"))
        
        # Отслеживаем старт потока
        self._hthr.started.connect(lambda: log("HeavyInit поток запущен", "DEBUG"))
        self._hthr.finished.connect(lambda: log("HeavyInit поток завершен", "DEBUG"))

        log("Запускаем HeavyInit поток...", "DEBUG")
        self._hthr.start()

    def _check_local_files(self):
        """Проверяет наличие критически важных локальных файлов"""
        if not os.path.exists(WINWS_EXE):
            self.set_status("❌ winws.exe не найден - включите автозагрузку")
            return False
        
        self.set_status("✅ Локальные файлы найдены")
        return True

    def periodic_subscription_check(self):
        """Периодическая проверка статуса подписки в фоне"""
        try:
            # Быстрая проверка кэша
            prev_premium, _, _ = self.donate_checker.check_subscription_status(use_cache=True)
            
            # Запускаем сетевую проверку в фоне
            self._check_subscription_async(prev_premium)
            
        except Exception as e:
            log(f"Ошибка при периодической проверке подписки: {e}", level="❌ ERROR")

    def _check_subscription_async(self, prev_premium):
        """Асинхронная проверка подписки"""
        from PyQt6.QtCore import QThread, QObject, pyqtSignal
        
        class SubscriptionCheckWorker(QObject):
            finished = pyqtSignal(bool, bool, str, int)  # prev_premium, is_premium, status_msg, days_remaining
            
            def __init__(self, donate_checker, prev_premium):
                super().__init__()
                self.donate_checker = donate_checker
                self.prev_premium = prev_premium
                
            def run(self):
                try:
                    # Сетевая проверка в фоне
                    is_premium, status_msg, days_remaining = self.donate_checker.check_subscription_status(use_cache=False)
                    self.finished.emit(self.prev_premium, is_premium, status_msg, days_remaining)
                except Exception as e:
                    log(f"Ошибка фоновой проверки подписки: {e}", "❌ ERROR")
                    # В случае ошибки возвращаем кэшированные данные
                    self.finished.emit(self.prev_premium, self.prev_premium, "Ошибка проверки", 0)
        
        # Создаем worker только если еще не запущен
        if hasattr(self, '_subscription_check_thread') and self._subscription_check_thread.isRunning():
            log("Проверка подписки уже выполняется, пропускаем", "DEBUG")
            return
        
        self._subscription_check_thread = QThread()
        self._subscription_check_worker = SubscriptionCheckWorker(self.donate_checker, prev_premium)
        self._subscription_check_worker.moveToThread(self._subscription_check_thread)
        
        self._subscription_check_thread.started.connect(self._subscription_check_worker.run)
        self._subscription_check_worker.finished.connect(self._on_subscription_check_done)
        self._subscription_check_worker.finished.connect(self._subscription_check_thread.quit)
        self._subscription_check_worker.finished.connect(self._subscription_check_worker.deleteLater)
        self._subscription_check_thread.finished.connect(self._subscription_check_thread.deleteLater)
        
        self._subscription_check_thread.start()

    def _on_subscription_check_done(self, prev_premium, is_premium, status_msg, days_remaining):
        """Обрабатывает результат фоновой проверки подписки"""
        try:
            # Обновляем заголовок с текущей темой
            current_theme = self.theme_manager.current_theme if hasattr(self, 'theme_manager') else None
            self.update_title_with_subscription_status(is_premium, current_theme, days_remaining)
            
            # Если статус изменился, обновляем интерфейс
            if prev_premium != is_premium:
                log(f"Статус подписки изменился: {prev_premium} -> {is_premium}", level="INFO")
                
                # Обновляем ThemeManager с новым статусом
                if hasattr(self, 'theme_manager'):
                    available_themes = self.theme_manager.get_available_themes()
                    current_selection = self.theme_combo.currentText()
                    
                    # Обновляем список тем
                    self.update_theme_combo(available_themes)
                    
                    # Восстанавливаем выбор если возможно
                    if current_selection in [theme for theme in available_themes]:
                        self.theme_combo.setCurrentText(current_selection)
                    else:
                        # Если текущая тема стала недоступна, ищем ближайшую доступную
                        clean_theme_name = self.theme_manager.get_clean_theme_name(current_selection)
                        for theme in available_themes:
                            if self.theme_manager.get_clean_theme_name(theme) == clean_theme_name:
                                self.theme_combo.setCurrentText(theme)
                                break
                        else:
                            # Если не нашли, выбираем первую доступную тему
                            if available_themes:
                                self.theme_combo.setCurrentText(available_themes[0])
                
                # Показываем уведомление пользователю о изменении статуса
                if is_premium and not prev_premium:
                    self.set_status("✅ Подписка активирована! Премиум темы доступны")
                    # Показываем уведомление в трее, если доступно
                    if hasattr(self, 'tray_manager') and self.tray_manager:
                        self.tray_manager.show_notification(
                            "Подписка активирована", 
                            "Премиум темы теперь доступны!"
                        )
                elif not is_premium and prev_premium:
                    self.set_status("❌ Подписка истекла. Премиум темы недоступны")
                    # Показываем уведомление в трее, если доступно
                    if hasattr(self, 'tray_manager') and self.tray_manager:
                        self.tray_manager.show_notification(
                            "Подписка истекла", 
                            "Премиум темы больше недоступны"
                        )
            else:
                # Статус не изменился, просто обновляем статусную строку
                if is_premium:
                    if days_remaining > 0:
                        self.set_status(f"✅ Подписка активна (осталось {days_remaining} дней)")
                    else:
                        self.set_status("✅ Подписка активна")
                else:
                    self.set_status("ℹ️ Проверка подписки завершена")
            
            log(f"Фоновая проверка подписки завершена: premium={is_premium}, статус='{status_msg}'", level="DEBUG")
            
        except Exception as e:
            log(f"Ошибка при обработке результата проверки подписки: {e}", level="❌ ERROR")
            # В случае ошибки показываем базовый статус
            try:
                current_theme = self.theme_manager.current_theme if hasattr(self, 'theme_manager') else None
                self.update_title_with_subscription_status(False, current_theme, 0)
                self.set_status("Ошибка при обработке проверки подписки")
            except Exception as inner_e:
                log(f"Критическая ошибка при восстановлении статуса: {inner_e}", level="❌ ERROR")

    def _on_heavy_done(self, ok: bool, err: str):
        """GUI-поток: тяжёлая инициализация завершена."""
        if not ok:
            QMessageBox.critical(self, "Ошибка инициализации", err)
            self.set_status("Ошибка инициализации")
            return

        # index.json и winws.exe готовы
        if self.strategy_manager.already_loaded:
            self.update_strategies_list()

        self.delayed_dpi_start()
        self.update_proxy_button_state()

        # combobox-фикс
        for d in (0, 100, 200):
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(d, self.force_enable_combos)

        # ---------- АВТО-ОБНОВЛЕНИЕ ---------------------------------
        #  Новая логика: проверяем ВСЕГДА, но берём только свой канал
        QTimer.singleShot(1000, self._start_auto_update)

        self.set_status("Инициализация завершена")
        # подписка проверяется асинхронно – ничего не трогаем


    def _start_auto_update(self):
        """
        Плановая (тихая) проверка обновлений в фоне.
        Вызывается один раз из _on_heavy_done().
        """
        self.set_status("Плановая проверка обновлений…")

        # --- запускаем воркер ---
        try:
            from updater import run_update_async           # из updater/__init__.py
        except Exception as e:
            log(f"Auto-update: import error {e}", "❌ ERROR")
            self.set_status("Не удалось запустить авто-апдейт")
            return

        # создаём поток/воркер
        thread = run_update_async(parent=self, silent=True)
        worker = thread._worker            # ссылка, которую мы сохранили в run_update_async

        # --------- обработчик завершения ----------
        def _upd_done(ok: bool):
            if ok:
                self.set_status("🔄 Обновление установлено – Zapret перезапустится")
            else:
                self.set_status("✅ Обновлений нет")
            log(f"Auto-update finished, ok={ok}", "DEBUG")

            # убираем ссылки, чтобы thread/worker мог закрыться
            if hasattr(self, "_auto_upd_thread"):
                del self._auto_upd_thread
            if hasattr(self, "_auto_upd_worker"):
                del self._auto_upd_worker

        # подключаемся к сигналу *worker*.finished(bool)
        worker.finished.connect(_upd_done)

        # храним ссылки, чтобы объекты не удалились преждевременно
        self._auto_upd_thread = thread
        self._auto_upd_worker = worker
    
    def init_process_monitor(self):
        """Инициализирует поток мониторинга процесса"""
        if hasattr(self, 'process_monitor') and self.process_monitor is not None:
            self.process_monitor.stop()
        
        self.process_monitor = ProcessMonitorThread(self.dpi_starter)
        self.process_monitor.processStatusChanged.connect(self.on_process_status_changed)
        self.process_monitor.start()

    def on_process_status_changed(self, is_running):
        """Обрабатывает сигнал изменения статуса процесса"""
        try:
            # Проверяем, изменилось ли состояние автозапуска
            autostart_active = self.service_manager.check_autostart_exists() \
                            if hasattr(self, 'service_manager') else False
            
            # Сохраняем текущее состояние для сравнения в будущем
            if not hasattr(self, '_prev_autostart'):
                self._prev_autostart = False
            if not hasattr(self, '_prev_running'):
                self._prev_running = False
                
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
        except Exception as e:
            log(f"Ошибка в on_process_status_changed: {e}", level="❌ ERROR")
            
    def delayed_dpi_start(self):
        """Выполняет отложенный запуск DPI с проверкой наличия автозапуска"""
        from config import get_dpi_autostart

        # 1. Автозапуск DPI включён?
        if not get_dpi_autostart():
            log("Автозапуск DPI отключён пользователем.", level="INFO")
            self.update_ui(running=False)
            return

        # 3. Определяем, какую стратегию запускать ---------------------- ☆ NEW
        strategy_name = None

        # 3.1 Сначала смотрим, есть ли уже выбранная стратегия
        if getattr(self, "current_strategy_name", None):
            strategy_name = self.current_strategy_name
        else:
            label_text = self.current_strategy_label.text()
            if label_text and label_text != "Автостарт DPI отключен":
                strategy_name = label_text

        # 3.2 Если до сих пор None – берём последнюю из реестра
        if not strategy_name:
            strategy_name = get_last_strategy()

            # Обновляем UI, чтобы пользователь видел, какой режим запущен
            self.current_strategy_label.setText(strategy_name)
            self.current_strategy_name = strategy_name

            # Если у вас есть комбобокс со стратегиями – тоже поставим его
            if hasattr(self, "strategy_manager") and self.strategy_manager:
                try:
                    self.strategy_manager.set_current_in_combobox(strategy_name)
                except AttributeError:
                    pass  # метод не обязательный

        log(f"Автозапуск DPI: стратегия «{strategy_name}»", level="INFO")

        # 4. Запускаем DPI
        self.start_dpi_async(selected_mode=strategy_name)

        # 5. Обновляем интерфейс
        self.update_ui(running=True)

    def __init__(self):
        QWidget.__init__(self)  # Явно инициализируем QWidget
        
        # Показываем минимальное окно СРАЗУ
        self.setWindowTitle("Zapret - загрузка...")
        self.resize(WIDTH, HEIGHT)
        
        # Создаем только загрузочный индикатор
        from PyQt6.QtWidgets import QLabel
        from PyQt6.QtCore import Qt, QTimer
        loading_label = QLabel("Загрузка приложения...")
        loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # ВСЁ остальное - асинхронно
        QTimer.singleShot(0, self._build_full_ui)

    def _build_full_ui(self):        
        # ---- Быстрая инициализация UI ----
        self.process_monitor = None
        self.first_start = True
        
        # Инициализируем атрибуты для работы со стратегиями
        self.current_strategy_id = None
        self.current_strategy_name = None
        
        # Создаем минимальный UI сразу
        self.build_ui(width=WIDTH, height=HEIGHT)
        self._init_dummy_donate_checker()
        self.update_title_with_subscription_status(False, None, 0)
        
        # Устанавливаем иконку
        icon_path = ICON_TEST_PATH if CHANNEL == "test" else ICON_PATH
        if os.path.exists(icon_path):
            from PyQt6.QtGui import QIcon
            app_icon = QIcon(icon_path)
            self.setWindowIcon(app_icon)
            QApplication.instance().setWindowIcon(app_icon)
        else:
            log(f"Иконка приложения не найдена: {icon_path}", "❌ ERROR")
        
        # ---- Все тяжелые операции - асинхронно ----
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(0, self._async_init)

    def _async_init(self):
        """Асинхронная инициализация всех компонентов"""
        try:
            # DPI Starter
            self.dpi_starter = DPIStarter(
                winws_exe=WINWS_EXE,
                status_callback=self.set_status,
                ui_callback=self.update_ui
            )
            
            # Меню
            self.menu_bar = AppMenuBar(self)
            self.layout().setMenuBar(self.menu_bar)
            
            # Подключаем сигналы
            self._connect_signals()
            
            # Инициализация менеджеров
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(100, self.initialize_managers_and_services)
            
            # Инициализация трея
            QTimer.singleShot(200, self._init_tray)
            
            # Инициализация логгера
            QTimer.singleShot(300, self._init_logger)
            
            # Проверка подписки
            QTimer.singleShot(1000, self._init_donate_checker_async)
            
        except Exception as e:
            log(f"Ошибка асинхронной инициализации: {e}", "❌ ERROR")
            self.set_status(f"Ошибка инициализации: {e}")


    def _connect_signals(self):
        """Подключение всех сигналов"""
        self.select_strategy_clicked.connect(self.select_strategy)
        self.start_clicked.connect(self.start_dpi_async)
        self.stop_clicked.connect(self.show_stop_menu)
        self.autostart_enable_clicked.connect(self.show_autostart_options)
        self.autostart_disable_clicked.connect(self.remove_autostart)
        self.theme_changed.connect(self.change_theme)
        
        self.open_folder_btn.clicked.connect(self.open_folder)
        self.test_connection_btn.clicked.connect(self.open_connection_test)
        self.subscription_btn.clicked.connect(self.show_subscription_dialog)
        self.dns_settings_btn.clicked.connect(self.open_dns_settings)
        self.proxy_button.clicked.connect(self.toggle_proxy_domains)
        self.update_check_btn.clicked.connect(self.manual_update_check)

    def _init_tray(self):
        """Инициализация системного трея"""
        self.tray_manager = SystemTrayManager(
            parent=self,
            icon_path=os.path.abspath(ICON_PATH),
            app_version=APP_VERSION
        )

    def _init_logger(self):
        """Инициализация логгера"""
        from log import LOG_FILE  # импортируем путь к лог-файлу
        from tgram import FullLogDaemon
        
        self.log_sender = FullLogDaemon(
            log_path=LOG_FILE,  # используем глобальный путь
            interval=120,
            parent=self
        )

    def _init_dummy_donate_checker(self):
        """Создает временную заглушку для DonateChecker"""
        class DummyChecker:
            def check_subscription_status(self, use_cache=True):
                return False, "Проверка подписки...", 0
            def get_email_from_registry(self):
                return None
        
        self.donate_checker = DummyChecker()
        log("Инициализирована заглушка DonateChecker", "DEBUG")

    def _init_donate_checker_async(self):
        """Асинхронная инициализация проверяльщика подписки"""
        from PyQt6.QtCore import QThread, QObject, pyqtSignal
        
        class DonateCheckerWorker(QObject):
            finished = pyqtSignal(object)  # DonateChecker instance
            progress = pyqtSignal(str)     # Статус загрузки
            
            def run(self):
                try:
                    self.progress.emit("Инициализация проверки подписки...")
                    
                    from donater import DonateChecker
                    checker = DonateChecker()
                    
                    self.progress.emit("Проверка статуса подписки...")
                    # Делаем первую проверку сразу
                    checker.check_subscription_status(use_cache=False)
                    
                    self.finished.emit(checker)
                except Exception as e:
                    log(f"Ошибка инициализации DonateChecker: {e}", "❌ ERROR")
                    self.finished.emit(None)
        
        # Показываем что идет загрузка
        self.set_status("Инициализация проверки подписки...")
        
        self._donate_thread = QThread()
        self._donate_worker = DonateCheckerWorker()
        self._donate_worker.moveToThread(self._donate_thread)
        
        self._donate_thread.started.connect(self._donate_worker.run)
        self._donate_worker.progress.connect(self.set_status)
        self._donate_worker.finished.connect(self._on_donate_checker_ready)
        self._donate_worker.finished.connect(self._donate_thread.quit)
        self._donate_worker.finished.connect(self._donate_worker.deleteLater)
        self._donate_thread.finished.connect(self._donate_thread.deleteLater)
        
        self._donate_thread.start()

    def _on_donate_checker_ready(self, checker):
        """Колбэк фонового потока DonateChecker."""
        if not checker:
            log("DonateChecker не инициализирован – работаем без премиума", "⚠ WARNING")
            return

        self.donate_checker = checker
        self.theme_manager.donate_checker = checker

        # 1. восстанавливаем премиум-тему, если надо
        log("Пробуем вернуть премиум-тему…", "DEBUG")
        self.theme_manager.reapply_saved_theme_if_premium()

        # 2. запрашиваем статус подписки
        try:
            is_premium, status_msg, days_remaining = checker.check_subscription_status()
        except Exception as e:
            log(f"Ошибка проверки подписки: {e}", "❌ ERROR")
            is_premium, status_msg, days_remaining = False, "", None

        # 3. обновляем заголовок
        self.update_title_with_subscription_status(
            is_premium,
            self.theme_manager.current_theme,
            days_remaining
        )

        # 4. перезаполняем список тем в комбобоксе
        self.update_theme_combo(self.theme_manager.get_available_themes())

        # 5. запускаем периодический таймер проверки
        self._start_subscription_timer()



    def _update_subscription_ui(self):
        """Обновляет UI с реальным статусом подписки"""
        try:
            is_premium, status_msg, days_remaining = self.donate_checker.check_subscription_status()
            current_theme = self.theme_manager.current_theme if hasattr(self, 'theme_manager') else None
            self.update_title_with_subscription_status(is_premium, current_theme, days_remaining)
            
            # Если статус изменился, обновляем темы
            if hasattr(self, 'theme_manager'):
                available_themes = self.theme_manager.get_available_themes()
                current_selection = self.theme_combo.currentText()
                
                # Обновляем список тем
                self.update_theme_combo(available_themes)
                
                # Восстанавливаем выбор если возможно
                if current_selection in [theme for theme in available_themes]:
                    self.theme_combo.setCurrentText(current_selection)
            
            self.set_status("Проверка подписки завершена")
            log(f"Статус подписки обновлен: {'Premium' if is_premium else 'Free'}", "INFO")
            
        except Exception as e:
            log(f"Ошибка при обновлении UI подписки: {e}", "❌ ERROR")
            self.set_status("Ошибка проверки подписки")

    def _start_subscription_timer(self):
        """Запускает таймер периодической проверки подписки"""
        if not hasattr(self, 'subscription_timer'):
            from PyQt6.QtCore import QTimer
            self.subscription_timer = QTimer()
            self.subscription_timer.timeout.connect(self.periodic_subscription_check)
        
        # Получаем интервал из настроек (по умолчанию 10 минут)
        from config import get_subscription_check_interval
        interval_minutes = get_subscription_check_interval()
        
        # Ограничиваем разумными пределами
        interval_minutes = max(1, min(interval_minutes, 60))  # от 1 до 60 минут
        
        self.subscription_timer.start(interval_minutes * 60 * 1000)
        log(f"Таймер периодической проверки подписки запущен ({interval_minutes} мин)", "DEBUG")

    def update_subscription_status_in_title(self):
        """Обновляет статус подписки в title_label"""
        try:
            if not self.donate_checker:
                return
                
            # Проверяем, не заглушка ли это
            if hasattr(self.donate_checker, '__class__') and self.donate_checker.__class__.__name__ == 'DummyChecker':
                return
                
            is_premium, status_msg, days_remaining = self.donate_checker.check_subscription_status()
            current_theme = self.theme_manager.current_theme if hasattr(self, 'theme_manager') else None
            self.update_title_with_subscription_status(is_premium, current_theme, days_remaining)
            
        except Exception as e:
            log(f"Ошибка при обновлении статуса подписки: {e}", "❌ ERROR")
            # Не падаем, просто показываем базовый заголовок
            self.update_title_with_subscription_status(False)

    def show_subscription_dialog(self):
        """Показывает диалог управления подписками"""
        try:
            # Проверяем, готов ли DonateChecker
            if (hasattr(self.donate_checker, '__class__') and 
                self.donate_checker.__class__.__name__ == 'DummyChecker'):
                QMessageBox.information(self, "Подписка", 
                                      "Система проверки подписки еще инициализируется.\n"
                                      "Попробуйте через несколько секунд.")
                return
            
            from donater import SubscriptionDialog
            
            self.set_status("Проверяю статус подписки...")
            QApplication.processEvents()
            
            dialog = SubscriptionDialog(self)
            result = dialog.exec()
            
            # После закрытия диалога обновляем статус в заголовке
            self._update_subscription_ui()
            
            # Обновляем доступные темы на основе нового статуса подписки
            if hasattr(self, 'theme_manager'):
                available_themes = self.theme_manager.get_available_themes()
                self.update_theme_combo(available_themes)
                
                # Если текущая тема стала доступна (убрали пометку), обновляем выбор
                current_displayed = self.theme_combo.currentText()
                current_clean = self.theme_manager.get_clean_theme_name(current_displayed)
                
                # Ищем правильное отображение для текущей темы
                for theme in available_themes:
                    if self.theme_manager.get_clean_theme_name(theme) == current_clean:
                        if theme != current_displayed:
                            self.theme_combo.blockSignals(True)
                            self.theme_combo.setCurrentText(theme)
                            self.theme_combo.blockSignals(False)
                        break
            
            self.set_status("Готово")
            
        except Exception as e:
            log(f"Ошибка при открытии диалога подписки: {e}", level="❌ ERROR")
            self.set_status(f"Ошибка: {e}")
            
            # Fallback - показываем простое сообщение
            if (not hasattr(self.donate_checker, '__class__') or 
                self.donate_checker.__class__.__name__ != 'DummyChecker'):
                
                email = self.donate_checker.get_email_from_registry()
                is_premium, status_msg, days_remaining = self.donate_checker.check_subscription_status()
                
                status_text = "✅ Активна" if is_premium else "❌ Неактивна"
                
                if email:
                    QMessageBox.information(self, "Информация о подписке",
                        f"Email пользователя:\n{email}\n\n"
                        f"Статус подписки: {status_text}\n"
                        f"Детали: {status_msg}")
                else:
                    QMessageBox.information(self, "Информация о подписке",
                        f"Email не найден в реестре.\n\n"
                        f"Статус подписки: {status_text}\n"
                        f"Детали: {status_msg}")

    # УБИРАЕМ все автоматические вызовы проверки подписки из других методов
    # Например, из _on_heavy_done убираем:
    # QTimer.singleShot(3000, self.post_init_subscription_check)
            
    def manual_update_check(self):
        """Ручная проверка обновлений (кнопка)"""

        log("Запуск ручной проверки обновлений...", level="INFO")
        # работаем синхронно – GUI-поток, появится QMessageBox
        from updater import check_and_run_update
        check_and_run_update(parent=self, status_cb=self.set_status, silent=False)

        self.set_status("Проверка обновлений…")

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
            
            log(f"Ошибка при активации комбо-бокса тем: {str(e)}")
            return False

    def on_mode_changed(self, selected_mode):
        """Обработчик смены режима в combobox"""
        # Проверяем, активен ли автозапуск
        if hasattr(self, 'service_manager') and self.service_manager.check_autostart_exists():
            # Если автозапуск активен, игнорируем смену режима и восстанавливаем предыдущий выбор
            log("Смена стратегии недоступна при активном автозапуске", level="⚠ WARNING")
            return
        
        # Обновляем отображение текущей стратегии
        self.current_strategy_label.setText(selected_mode)

        # Записываем время изменения стратегии
        self.last_strategy_change_time = time.time()
        
        # Сохраняем выбранную стратегию в реестр
        set_last_strategy(selected_mode)
        
        # ✅ ЗАМЕНЯЕМ эту строку:
        # self.dpi_starter.start_dpi(selected_mode=selected_mode)
        # НА:
        self.start_dpi_async(selected_mode=selected_mode)
        
        # Перезапускаем Discord только если:
        # 1. Это не первый запуск
        # 2. Автоперезапуск включен в настройках
        from discord.discord_restart import get_discord_restart_setting
        if not self.first_start and get_discord_restart_setting():
            self.discord_manager.restart_discord_if_running()
        else:
            self.first_start = False  # Сбрасываем флаг первого запуска
 
    # ------------------------------------------- Асинхронные методы запуска и остановки DPI -------------------------------------------
    def start_dpi_async(self, selected_mode=None):
        """✅ Асинхронно запускает DPI без блокировки UI (оптимизированная версия)"""
        from PyQt6.QtCore import QThread, QObject, pyqtSignal
        
        # ✅ БЫСТРАЯ И НАДЕЖНАЯ ПРОВЕРКА без sip
        try:
            if (hasattr(self, '_dpi_start_thread') and 
                self._dpi_start_thread is not None):
                # Пытаемся проверить состояние потока в try-catch
                if self._dpi_start_thread.isRunning():
                    log("Запуск DPI уже выполняется", "DEBUG")
                    return
        except RuntimeError:
            # Объект уже удален - это нормально, продолжаем
            log("Предыдущий поток запуска уже удален", "DEBUG")
            self._dpi_start_thread = None
        except Exception as e:
            # Любая другая ошибка - тоже продолжаем
            log(f"Ошибка проверки потока запуска: {e}", "DEBUG")
            self._dpi_start_thread = None
        
        class DPIStartWorker(QObject):
            finished = pyqtSignal(bool, str)  # success, error_message
            progress = pyqtSignal(str)        # status_message
            
            def __init__(self, dpi_starter, selected_mode):
                super().__init__()
                self.dpi_starter = dpi_starter
                self.selected_mode = selected_mode
            
            def run(self):
                try:
                    self.progress.emit("Подготовка к запуску...")
                    
                    # Проверяем, не запущен ли уже процесс
                    if self.dpi_starter.check_process_running_wmi(silent=True):
                        self.progress.emit("Останавливаем предыдущий процесс...")
                        self.progress.emit("Запуск DPI...")
                    # ✅ ИСПРАВЛЕНИЕ: Нормализуем selected_mode
                    mode_param = self.selected_mode
                    
                    # Если передан словарь, извлекаем имя стратегии
                    if isinstance(mode_param, dict):
                        # Правильно извлекаем значения из словаря
                        name_value = mode_param.get('name')
                        file_path_value = mode_param.get('file_path')
                        mode_param = name_value or file_path_value or 'default'
                        log(f"Извлечено имя стратегии из словаря: {mode_param}", "DEBUG")
                    elif mode_param is None:
                        mode_param = 'default'
                        log("Используется стратегия по умолчанию", "DEBUG")
                    
                    # Вызываем синхронный метод в отдельном потоке
                    success = self.dpi_starter.start_dpi(selected_mode=mode_param)
                    
                    if success:
                        self.progress.emit("DPI успешно запущен")
                        self.finished.emit(True, "")
                    else:
                        self.finished.emit(False, "Не удалось запустить DPI")
                        
                except Exception as e:
                    error_msg = f"Ошибка запуска DPI: {str(e)}"
                    log(error_msg, "❌ ERROR")
                    self.finished.emit(False, error_msg)
        
        # Показываем состояние запуска
        self.set_status("🚀 Запуск DPI...")
        
        # Блокируем кнопки во время операции
        if hasattr(self, 'start_btn'):
            self.start_btn.setEnabled(False)
        if hasattr(self, 'stop_btn'):
            self.stop_btn.setEnabled(False)
        
        # ✅ СОЗДАЕМ НОВЫЙ ПОТОК (простое создание)
        self._dpi_start_thread = QThread()
        self._dpi_start_worker = DPIStartWorker(self.dpi_starter, selected_mode)
        self._dpi_start_worker.moveToThread(self._dpi_start_thread)
        
        # ✅ ПОДКЛЮЧЕНИЕ СИГНАЛОВ
        self._dpi_start_thread.started.connect(self._dpi_start_worker.run)
        self._dpi_start_worker.progress.connect(self.set_status)
        self._dpi_start_worker.finished.connect(self._on_dpi_start_finished)
        
        # ✅ УПРОЩЕННАЯ ОЧИСТКА РЕСУРСОВ
        def cleanup_start_thread():
            try:
                if hasattr(self, '_dpi_start_thread') and self._dpi_start_thread:
                    self._dpi_start_thread.quit()
                    self._dpi_start_thread.wait(2000)  # Без terminate() - надежнее
                    self._dpi_start_thread = None
                    
                if hasattr(self, '_dpi_start_worker') and self._dpi_start_worker:
                    self._dpi_start_worker.deleteLater()
                    self._dpi_start_worker = None
            except Exception as e:
                log(f"Ошибка при очистке потока запуска: {e}", "❌ ERROR")
        
        self._dpi_start_worker.finished.connect(cleanup_start_thread)
        
        # Запускаем поток
        self._dpi_start_thread.start()
        
        # ✅ ИСПРАВЛЕНИЕ: Логируем правильную информацию
        mode_name = selected_mode
        if isinstance(selected_mode, dict):
            mode_name = selected_mode.get('name', str(selected_mode))
        
        log(f"Запуск асинхронного старта DPI: {mode_name}", "INFO")

    def stop_dpi_async(self):
        """✅ Асинхронно останавливает DPI без блокировки UI (оптимизированная версия)"""
        from PyQt6.QtCore import QThread, QObject, pyqtSignal
        
        # ✅ БЫСТРАЯ И НАДЕЖНАЯ ПРОВЕРКА без sip
        try:
            if (hasattr(self, '_dpi_stop_thread') and 
                self._dpi_stop_thread is not None):
                # Пытаемся проверить состояние потока в try-catch
                if self._dpi_stop_thread.isRunning():
                    log("Остановка DPI уже выполняется", "DEBUG")
                    return
        except RuntimeError:
            # Объект уже удален - это нормально, продолжаем
            log("Предыдущий поток остановки уже удален", "DEBUG")
            self._dpi_stop_thread = None
        except Exception as e:
            # Любая другая ошибка - тоже продолжаем
            log(f"Ошибка проверки потока остановки: {e}", "DEBUG")
            self._dpi_stop_thread = None
        
        class DPIStopWorker(QObject):
            finished = pyqtSignal(bool, str)  # success, error_message
            progress = pyqtSignal(str)        # status_message
            
            def __init__(self, app_instance):
                super().__init__()
                self.app_instance = app_instance
            
            def run(self):
                try:
                    self.progress.emit("Остановка DPI...")
                    
                    # Проверяем, запущен ли процесс
                    if not self.app_instance.dpi_starter.check_process_running_wmi(silent=True):
                        self.progress.emit("DPI уже остановлен")
                        self.finished.emit(True, "DPI уже был остановлен")
                        return
                    
                    self.progress.emit("Завершение процессов...")
                    
                    # ✅ Вызываем синхронную остановку в отдельном потоке
                    from dpi.stop import stop_dpi
                    stop_dpi(self.app_instance)
                    
                    # Проверяем результат
                    if not self.app_instance.dpi_starter.check_process_running_wmi(silent=True):
                        self.progress.emit("DPI успешно остановлен")
                        self.finished.emit(True, "")
                    else:
                        self.finished.emit(False, "Не удалось полностью остановить процесс")
                        
                except Exception as e:
                    error_msg = f"Ошибка остановки DPI: {str(e)}"
                    log(error_msg, "❌ ERROR")
                    self.finished.emit(False, error_msg)
        
        # Показываем состояние остановки
        self.set_status("🛑 Остановка DPI...")
        
        # Блокируем кнопки во время операции
        if hasattr(self, 'start_btn'):
            self.start_btn.setEnabled(False)
        if hasattr(self, 'stop_btn'):
            self.stop_btn.setEnabled(False)
        
        # ✅ СОЗДАЕМ НОВЫЙ ПОТОК (простое создание)
        self._dpi_stop_thread = QThread()
        self._dpi_stop_worker = DPIStopWorker(self)
        self._dpi_stop_worker.moveToThread(self._dpi_stop_thread)
        
        # ✅ ПОДКЛЮЧЕНИЕ СИГНАЛОВ
        self._dpi_stop_thread.started.connect(self._dpi_stop_worker.run)
        self._dpi_stop_worker.progress.connect(self.set_status)
        self._dpi_stop_worker.finished.connect(self._on_dpi_stop_finished)
        
        # ✅ УПРОЩЕННАЯ ОЧИСТКА РЕСУРСОВ
        def cleanup_stop_thread():
            try:
                if hasattr(self, '_dpi_stop_thread') and self._dpi_stop_thread:
                    self._dpi_stop_thread.quit()
                    self._dpi_stop_thread.wait(2000)  # Без terminate() - надежнее
                    self._dpi_stop_thread = None
                    
                if hasattr(self, '_dpi_stop_worker') and self._dpi_stop_worker:
                    self._dpi_stop_worker.deleteLater()
                    self._dpi_stop_worker = None
            except Exception as e:
                log(f"Ошибка при очистке потока остановки: {e}", "❌ ERROR")
        
        self._dpi_stop_worker.finished.connect(cleanup_stop_thread)
        
        # Устанавливаем флаг ручной остановки
        self.manually_stopped = True
        
        # Запускаем поток
        self._dpi_stop_thread.start()
        
        log("Запуск асинхронной остановки DPI", "INFO")

    def _on_dpi_start_finished(self, success, error_message):
        """Обрабатывает завершение асинхронного запуска DPI"""
        try:
            # Восстанавливаем кнопки
            if hasattr(self, 'start_btn'):
                self.start_btn.setEnabled(True)
            if hasattr(self, 'stop_btn'):
                self.stop_btn.setEnabled(True)
            
            if success:
                log("DPI запущен асинхронно", "INFO")
                self.set_status("✅ DPI успешно запущен")
                
                # Обновляем UI
                self.update_ui(running=True)
                
                # Обновляем статус процесса
                self.on_process_status_changed(True)
                
                # Устанавливаем флаг намеренного запуска
                self.intentional_start = True
                
                # Перезапускаем Discord если нужно
                from discord.discord_restart import get_discord_restart_setting
                if not self.first_start and get_discord_restart_setting():
                    self.discord_manager.restart_discord_if_running()
                else:
                    self.first_start = False
                    
            else:
                log(f"Ошибка асинхронного запуска DPI: {error_message}", "❌ ERROR")
                self.set_status(f"❌ Ошибка запуска: {error_message}")
                
                # Обновляем UI как неактивный
                self.update_ui(running=False)
                self.on_process_status_changed(False)
                
        except Exception as e:
            log(f"Ошибка при обработке результата запуска DPI: {e}", "❌ ERROR")
            self.set_status(f"Ошибка: {e}")

    def _on_dpi_stop_finished(self, success, error_message):
        """Обрабатывает завершение асинхронной остановки DPI"""
        try:
            # Восстанавливаем кнопки
            if hasattr(self, 'start_btn'):
                self.start_btn.setEnabled(True)
            if hasattr(self, 'stop_btn'):
                self.stop_btn.setEnabled(True)
            
            if success:
                log("DPI остановлен асинхронно", "INFO")
                if error_message:
                    self.set_status(f"✅ {error_message}")
                else:
                    self.set_status("✅ DPI успешно остановлен")
                
                # Обновляем UI
                self.update_ui(running=False)
                
                # Обновляем статус процесса
                self.on_process_status_changed(False)
                
            else:
                log(f"Ошибка асинхронной остановки DPI: {error_message}", "❌ ERROR")
                self.set_status(f"❌ Ошибка остановки: {error_message}")
                
                # Проверяем реальный статус процесса
                is_running = self.dpi_starter.check_process_running_wmi(silent=True)
                self.update_ui(running=is_running)
                self.on_process_status_changed(is_running)
                
        except Exception as e:
            log(f"Ошибка при обработке результата остановки DPI: {e}", "❌ ERROR")
            self.set_status(f"Ошибка: {e}")

    def _stop_and_exit_async(self):
        """Асинхронно останавливает DPI и закрывает программу"""
        from PyQt6.QtCore import QThread, QObject, pyqtSignal
        
        # ✅ ДОБАВЛЯЕМ флаг, что программа закрывается
        self._is_exiting = True
        
        class StopAndExitWorker(QObject):
            finished = pyqtSignal()
            progress = pyqtSignal(str)
            
            def __init__(self, app_instance):
                super().__init__()
                self.app_instance = app_instance
            
            def run(self):
                try:
                    self.progress.emit("Остановка DPI перед закрытием...")
                    
                    # Останавливаем DPI
                    from dpi.stop import stop_dpi
                    stop_dpi(self.app_instance)
                    
                    self.progress.emit("Завершение работы...")
                    self.finished.emit()
                    
                except Exception as e:
                    log(f"Ошибка при остановке перед закрытием: {e}", "❌ ERROR")
                    self.finished.emit()
        
        # Создаем worker и поток
        self._stop_exit_thread = QThread()
        self._stop_exit_worker = StopAndExitWorker(self)
        self._stop_exit_worker.moveToThread(self._stop_exit_thread)
        
        # Подключаем сигналы
        self._stop_exit_thread.started.connect(self._stop_exit_worker.run)
        self._stop_exit_worker.progress.connect(self.set_status)
        self._stop_exit_worker.finished.connect(self._on_stop_and_exit_finished)
        self._stop_exit_worker.finished.connect(self._stop_exit_thread.quit)
        self._stop_exit_worker.finished.connect(self._stop_exit_worker.deleteLater)
        self._stop_exit_thread.finished.connect(self._stop_exit_thread.deleteLater)
        
        # Запускаем поток
        self._stop_exit_thread.start()

    def _on_stop_and_exit_finished(self):
        """Завершает приложение после остановки DPI"""
        self.set_status("Завершение...")
        QApplication.quit()

    def change_theme(self, theme_name):
        """Обработчик изменения темы"""
        try:
            # Проверяем, не является ли тема заблокированной
            if "(заблокировано)" in theme_name:
                clean_theme_name = theme_name.replace(" (заблокировано)", "")
                
                # Показываем предупреждение о заблокированной теме
                success, message = self.theme_manager.apply_theme(clean_theme_name)
                
                if not success:
                    # Возвращаемся к текущей теме
                    available_themes = self.theme_manager.get_available_themes()
                    for theme in available_themes:
                        if self.theme_manager.get_clean_theme_name(theme) == self.theme_manager.current_theme:
                            self.theme_combo.blockSignals(True)
                            self.theme_combo.setCurrentText(theme)
                            self.theme_combo.blockSignals(False)
                            break
                    return
            
            # Применяем тему
            success, message = self.theme_manager.apply_theme(theme_name)
            
            if success:
                log(f"Тема изменена на: {theme_name}", level="INFO")
                self.set_status(f"Тема изменена: {theme_name}")
                
                # Дополнительно обновляем статус подписки с новой темой
                # через небольшую задержку, чтобы тема успела примениться
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(100, self.update_subscription_status_in_title)
            else:
                log(f"Ошибка при изменении темы: {message}", level="❌ ERROR")
                self.set_status(f"Ошибка изменения темы: {message}")
                
        except Exception as e:
            log(f"Ошибка при обработке изменения темы: {e}", level="❌ ERROR")
            self.set_status(f"Ошибка: {e}")

    def open_folder(self):
        """Opens the DPI folder."""
        try:
            run_hidden('explorer.exe .', shell=True)
        except Exception as e:
            self.set_status(f"Ошибка при открытии папки: {str(e)}")

    def show_autostart_options(self):
        """Показывает диалог автозапуска (вместо старого подменю)."""
        from autostart.autostart_menu import AutoStartMenu
        

        # Если уже есть автозапуск — предупредим и выйдем
        if self.service_manager.check_autostart_exists():
            log("Автозапуск уже активен", "⚠ WARNING")
            self.set_status("Сначала отключите текущий автозапуск")
            return

        # как называется текущая стратегия
        strategy_name = self.current_strategy_label.text()
        if strategy_name == "Автостарт DPI отключен":
            strategy_name = get_last_strategy()

        dlg = AutoStartMenu(
            parent             = self,
            strategy_name      = strategy_name,
            bat_folder         = BAT_FOLDER,
            json_folder        = INDEXJSON_FOLDER,
            check_autostart_cb = self.service_manager.check_autostart_exists,
            update_ui_cb       = self.update_autostart_ui,
            status_cb          = self.set_status
        )
        dlg.exec()
        
    def show_stop_menu(self):
        """Показывает меню с вариантами остановки программы"""
        log("Отображение меню остановки Zapret", level="INFO")
        
        # Создаем меню
        menu = QMenu(self)
        
        # Добавляем пункты меню
        stop_winws_action = menu.addAction("Остановить только winws.exe")
        stop_and_exit_action = menu.addAction("Остановить и закрыть программу")
        
        # Получаем положение кнопки для отображения меню
        button_pos = self.stop_btn.mapToGlobal(self.stop_btn.rect().bottomLeft())
        
        # Показываем меню и получаем выбранное действие
        action = menu.exec(button_pos)
        
        # Обрабатываем выбор
        if action == stop_winws_action:
            log("Выбрано: Остановить только winws.exe", level="INFO")
            self.stop_dpi_async()
        elif action == stop_and_exit_action:
            log("Выбрано: Остановить и закрыть программу", level="INFO")
            self.set_status("Останавливаю Zapret и закрываю программу...")
            
            # ✅ УСТАНАВЛИВАЕМ флаг полного закрытия перед остановкой
            self._closing_completely = True
            
            # ✅ НЕ показываем уведомление - программа полностью закрывается
            self._stop_and_exit_async()

    def remove_autostart(self):
        """Удаляет автозапуск ВЕСЬ вообще и обновляет UI"""
        cleaner = AutoStartCleaner(
            status_cb=self.set_status      # передаём вашу строку статуса
        )
        if cleaner.run():
            self.update_autostart_ui(False)
            self.on_process_status_changed(
                self.dpi_starter.check_process_running_wmi(silent=True)
            )

    def update_proxy_button_state(self):
        """Обновляет состояние кнопки разблокировки (вызывает метод UI)"""
        if hasattr(self, 'hosts_manager'):
            is_active = self.hosts_manager.is_proxy_domains_active()
            # Вызываем метод UI с определенным состоянием
            super().update_proxy_button_state(is_active)
        else:
            # Если hosts_manager недоступен, вызываем без параметров
            super().update_proxy_button_state()

    def toggle_proxy_domains(self):
        """Переключает состояние разблокировки: добавляет или удаляет записи из hosts"""
        if not hasattr(self, 'hosts_manager'):
            self.set_status("Ошибка: менеджер hosts не инициализирован")
            return
            
        is_active = self.hosts_manager.is_proxy_domains_active()
        
        if is_active:
            # Показываем меню с вариантами отключения
            menu = QMenu(self)
            
            disable_all_action = menu.addAction("Отключить всю разблокировку")
            select_domains_action = menu.addAction("Выбрать домены для отключения")
            
            # Получаем положение кнопки для отображения меню
            button_pos = self.proxy_button.mapToGlobal(self.proxy_button.rect().bottomLeft())
            
            # Показываем меню и получаем выбранное действие
            action = menu.exec(button_pos)
            
            if action == disable_all_action:
                self._handle_proxy_disable_all()
            elif action == select_domains_action:
                self._handle_proxy_select_domains()
                
        else:
            # Показываем меню с вариантами включения
            menu = QMenu(self)
            
            enable_all_action = menu.addAction("Включить всю разблокировку")
            select_domains_action = menu.addAction("Выбрать домены для включения")
            
            # Получаем положение кнопки для отображения меню
            button_pos = self.proxy_button.mapToGlobal(self.proxy_button.rect().bottomLeft())
            
            # Показываем меню и получаем выбранное действие
            action = menu.exec(button_pos)
            
            if action == enable_all_action:
                self._handle_proxy_enable_all()
            elif action == select_domains_action:
                self._handle_proxy_select_domains()

    def _handle_proxy_disable_all(self):
        """Обрабатывает отключение всей разблокировки"""
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Question)
        msg.setWindowTitle("Отключение разблокировки")
        msg.setText("Отключить разблокировку сервисов через hosts-файл?")
        
        msg.setInformativeText(
            "Это действие удалит добавленные ранее записи из файла hosts.\n\n"
            "Для применения изменений ОБЯЗАТЕЛЬНО СЛЕДУЕТ закрыть и открыть веб-браузер и/или приложение Spotify!"
        )
        
        msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        result = msg.exec()
        
        if result == QMessageBox.StandardButton.Yes:
            # Показываем состояние загрузки
            self.set_proxy_button_loading(True, "Отключение...")
            
            if self.hosts_manager.remove_proxy_domains():
                self.set_status("Разблокировка отключена. Перезапустите браузер.")
                
                # Обновляем состояние кнопки с небольшой задержкой
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(100, self.update_proxy_button_state)
            else:
                self.set_status("Не удалось отключить разблокировку.")
                
            # Отключаем состояние загрузки
            self.set_proxy_button_loading(False)
        else:
            self.set_status("Операция отменена.")

    def _handle_proxy_enable_all(self):
        """Обрабатывает включение всей разблокировки"""
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setWindowTitle("Разблокировка через hosts-файл")
        msg.setText("Установка соединения к proxy-серверу через файл hosts")
        
        msg.setInformativeText(
            "Добавление этих сайтов в обычные списки Zapret не поможет их разблокировать, "
            "так как доступ к ним заблокирован для территории РФ со стороны самих сервисов "
            "(без участия Роскомнадзора).\n\n"
            "Для применения изменений ОБЯЗАТЕЛЬНО СЛЕДУЕТ закрыть и открыть веб-браузер (не только сайт, а всю программу) и/или приложение Spotify!"
        )
        
        msg.setStandardButtons(QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel)
        result = msg.exec()
        
        if result == QMessageBox.StandardButton.Ok:
            # Показываем состояние загрузки

            self.set_proxy_button_loading(True, "Включение...")
            
            if self.hosts_manager.add_proxy_domains():
                self.set_status("Разблокировка включена. Перезапустите браузер.")
                
                # Обновляем состояние кнопки с небольшой задержкой
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(100, self.update_proxy_button_state)
            else:
                self.set_status("Не удалось включить разблокировку.")
                
            # Отключаем состояние загрузки
            self.set_proxy_button_loading(False)
        else:
            self.set_status("Операция отменена.")

    def _handle_proxy_select_domains(self):
        """Обрабатывает выбор доменов для разблокировки"""
        if self.hosts_manager.show_hosts_selector_dialog(self):
            # Обновляем состояние кнопки после изменений
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(100, self.update_proxy_button_state)
            
    def show_hosts_selector_dialog(self):
        """Показывает селектор доменов для hosts файла"""
        if hasattr(self, 'hosts_manager'):
            if self.hosts_manager.show_hosts_selector_dialog(self):
                self.update_proxy_button_state()
        else:
            self.set_status("Ошибка: менеджер hosts не инициализирован")

    def open_connection_test(self):
        """✅ Открывает неблокирующее окно тестирования соединения."""
        try:
            # Проверяем, не открыто ли уже окно
            if hasattr(self, '_connection_test_dialog') and self._connection_test_dialog:
                if self._connection_test_dialog.isVisible():
                    # Поднимаем существующее окно на передний план
                    self._connection_test_dialog.raise_()
                    self._connection_test_dialog.activateWindow()
                    return
            
            # Создаем новое окно
            from connection_test import ConnectionTestDialog
            self._connection_test_dialog = ConnectionTestDialog(self)
            
            # ✅ ПОКАЗЫВАЕМ БЕЗ БЛОКИРОВКИ!
            self._connection_test_dialog.show()  # НЕ exec()!
            
            # Поднимаем на передний план
            self._connection_test_dialog.raise_()
            self._connection_test_dialog.activateWindow()
            
            log("Открыто окно тестирования соединения (неблокирующее)", "INFO")
            
        except Exception as e:
            log(f"Ошибка при открытии окна тестирования: {e}", "❌ ERROR")
            self.set_status(f"Ошибка: {e}")

    def open_dns_settings(self):
        """Открывает диалог настройки DNS-серверов"""
        try:
            # Показываем индикатор в статусной строке
            self.set_status("Открываем настройки DNS (загрузка данных)...")
        
            # Передаем текущий стиль в диалог
            dns_dialog = DNSSettingsDialog(self, common_style=COMMON_STYLE)
            dns_dialog.exec()
            
            # Сбрасываем статус после закрытия диалога
            self.set_status("Настройки DNS закрыты")
        except Exception as e:
            error_msg = f"Ошибка при открытии настроек DNS: {str(e)}"
            
            log(f"Ошибка при открытии настроек DNS: {str(e)}", level="❌ ERROR")
            self.set_status(error_msg)

def set_batfile_association():
    """
    Устанавливает ассоциацию типа файла для .bat файлов
    """
    try:
        # Используем максимально скрытый режим
        command = 'ftype batfile="%SystemRoot%\\System32\\cmd.exe" /c "%1" %*'
        
        result = run_hidden(
            command,
            shell=True,
            capture_output=True,
            text=True,
            encoding='utf-8',
            use_vbs_for_bat=False  # Для команд ftype не используем VBS
        )

        if result.returncode == 0:
            log("Ассоциация успешно установлена", level="INFO")
            return True
        else:
            log(f"Ошибка при выполнении команды: {result.stderr}", level="❌ ERROR")
            return False
            
    except Exception as e:
        log(f"Произошла ошибка: {e}", level="❌ ERROR")
        return False

def main():
    import sys, ctypes, os, atexit
    log("=== ЗАПУСК ПРИЛОЖЕНИЯ ===", "🔹 main")
    # ---------------- Быстрая обработка специальных аргументов ----------------
    if "--version" in sys.argv:
        ctypes.windll.user32.MessageBoxW(None, APP_VERSION, "Zapret – версия", 0x40)
        sys.exit(0)

    if "--update" in sys.argv and len(sys.argv) > 3:
        _handle_update_mode()
        sys.exit(0)
    
    start_in_tray = "--tray" in sys.argv
    
    # ---------------- Проверка прав администратора ----------------
    if not is_admin():
        params = " ".join(sys.argv[1:])
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, None, 1)
        sys.exit(0)

    # ---------------- Проверка single instance ----------------
    from startup.single_instance import create_mutex, release_mutex
    from startup.kaspersky import _check_kaspersky_antivirus, show_kaspersky_warning
    mutex_handle, already_running = create_mutex("ZapretSingleInstance")
    if already_running:
        ctypes.windll.user32.MessageBoxW(None, 
            "Экземпляр Zapret уже запущен и/или работает в трее!", "Zapret", 0x40)
        sys.exit(0)
    atexit.register(lambda: release_mutex(mutex_handle))

    # ---------------- Создаём QApplication СРАЗУ ----------------
    try:
        os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
        _set_attr_if_exists("AA_EnableHighDpiScaling")
        _set_attr_if_exists("AA_UseHighDpiPixmaps")

        app = QApplication(sys.argv)
        app.setQuitOnLastWindowClosed(False)
        
        import qt_material
        qt_material.apply_stylesheet(app, 'dark_blue.xml')
    except Exception as e:
        ctypes.windll.user32.MessageBoxW(None,
            f"Ошибка инициализации Qt: {e}", "Zapret", 0x10)
        sys.exit(1)

    # ---------- проверяем Касперского + показываем диалог -----------------
    try:
        kaspersky_detected = _check_kaspersky_antivirus(None)   # self не нужен
    except Exception:
        kaspersky_detected = False

    if kaspersky_detected:
        log("Обнаружен антивирус Kaspersky", "⚠️ KASPERSKY")
        try:
            from startup.kaspersky import show_kaspersky_warning
            show_kaspersky_warning()          # QApplication уже создан
        except Exception as e:
            log(f"Не удалось показать предупреждение Kaspersky: {e}",
                "⚠️ KASPERSKY")

    # ---------------- СОЗДАЁМ И ПОКАЗЫВАЕМ ОКНО СРАЗУ ----------------
    window = LupiDPIApp()
    
    if not start_in_tray:
        window.show()
        log("Запуск приложения в обычном режиме", "TRAY")
    else:
        log("Запуск приложения скрыто в трее", "TRAY")
        if hasattr(window, 'tray_manager'):
            window.tray_manager.show_notification(
                "Zapret работает в трее", 
                "Приложение запущено в фоновом режиме"
            )
    from PyQt6.QtCore import QTimer
    # ---------------- АСИНХРОННЫЕ ПРОВЕРКИ ПОСЛЕ ПОКАЗА ОКНА ----------------
    def async_startup_checks():
        """Выполняет все стартовые проверки асинхронно"""
        try:
            # 1. Предзагрузка службы BFE
            from startup.bfe_util import preload_service_status, ensure_bfe_running
            preload_service_status("BFE")
            
            # 2. Проверка BFE
            if not ensure_bfe_running(show_ui=True):
                return
            
            # 3. Проверка условий запуска
            from startup.check_start import check_startup_conditions
            conditions_ok, error_msg = check_startup_conditions()
            if not conditions_ok and not start_in_tray:
                if error_msg:
                    QMessageBox.critical(window, "Ошибка запуска", error_msg)
                return
            
            # 4. Показ предупреждений
            from startup.check_start import display_startup_warnings
            warnings_ok = display_startup_warnings()
            if not warnings_ok and not start_in_tray:
                return
            
            # 5. Дополнительные проверки
            from startup.remove_terminal import remove_windows_terminal_if_win11
            remove_windows_terminal_if_win11()
            
            from startup.admin_check_debug import debug_admin_status
            debug_admin_status()
            
            set_batfile_association()
            
            # 6. Регистрация очистки ресурсов
            from startup.bfe_util import cleanup as bfe_cleanup
            atexit.register(bfe_cleanup)
            
            log("✅ Все проверки пройдены", "🔹 main - async_startup_checks")
            
        except Exception as e:
            log(f"Ошибка при асинхронных проверках: {e}", "❌ ERROR")
            window.set_status(f"Ошибка проверок: {e}")
    
    # Запускаем проверки через 100ms после показа окна
    QTimer.singleShot(100, async_startup_checks)
    
    # Exception handler
    def global_exception_handler(exctype, value, traceback):
        import traceback as tb
        error_msg = ''.join(tb.format_exception(exctype, value, traceback))
        log(f"UNCAUGHT EXCEPTION: {error_msg}", level="❌ CRITICAL")

    sys.excepthook = global_exception_handler
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()