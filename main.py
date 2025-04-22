import threading
import ctypes, sys, os, winreg, subprocess, webbrowser, time, shutil

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout, QComboBox, QMessageBox, QApplication, QFrame, QSpacerItem, QSizePolicy

from downloader import DOWNLOAD_URLS
from config import DPI_COMMANDS, APP_VERSION, BIN_FOLDER, LISTS_FOLDER, WINWS_EXE, ICON_PATH
from hosts import HostsManager
from service import ServiceManager
from start import DPIStarter

from theme import ThemeManager, RippleButton, THEMES, BUTTON_STYLE, COMMON_STYLE, BUTTON_HEIGHT, STYLE_SHEET
from tray import SystemTrayManager
from dns import DNSSettingsDialog
from urls import AUTHOR_URL, INFO_URL
from updater import check_for_update

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

def get_version(self):
    """Возвращает текущую версию программы"""
    return APP_VERSION

class LupiDPIApp(QWidget):
    def set_status(self, text):
        """Sets the status text."""
        self.status_label.setText(text)

    def update_ui(self, running):
        """Обновляет состояние кнопок и элементов интерфейса в зависимости от статуса запуска"""
        # Обновляем только кнопки запуска/остановки
        self.start_btn.setVisible(not running)
        self.stop_btn.setVisible(running)

    def check_process_status(self):
        """Проверяет статус процесса и обновляет интерфейс"""
        # Используем блокировку чтобы предотвратить одновременные проверки
        if not hasattr(self, 'status_check_lock') or not self.status_check_lock.acquire(blocking=False):
            return
        
        try:
            # Проверяем, не слишком ли часто выполняем проверки
            current_time = time.time()
            if hasattr(self, 'last_status_time') and current_time - self.last_status_time < self.status_check_interval:
                # Слишком малый интервал, пропускаем проверку
                return
                
            self.last_status_time = current_time
            
            # Проверяем статус службы
            service_running = self.service_manager.check_service_exists()
            
            # Проверяем статус процесса
            process_running = self.dpi_starter.check_process_running()
            
            # Сохраняем текущий статус для сравнения
            current_status = (process_running, service_running)
            
            # Проверяем, изменился ли статус с последней проверки
            if hasattr(self, 'last_status') and self.last_status == current_status:
                # Статус не изменился, не обновляем UI
                return
                
            # Сохраняем новый статус
            self.last_status = current_status
            
            # Обновляем состояние элементов интерфейса
            if process_running or service_running:
                self.start_btn.setVisible(False)
                self.stop_btn.setVisible(True)
                
                # Если служба активна, отображаем это
                if service_running:
                    self.process_status_value.setText("СЛУЖБА АКТИВНА")
                    self.process_status_value.setStyleSheet("color: purple; font-weight: bold;")
                else:
                    # Иначе показываем обычный статус
                    self.process_status_value.setText("ВКЛЮЧЕН")
                    self.process_status_value.setStyleSheet("color: green; font-weight: bold;")
            else:
                self.start_btn.setVisible(True)
                self.stop_btn.setVisible(False)
                self.process_status_value.setText("ВЫКЛЮЧЕН")
                self.process_status_value.setStyleSheet("color: red; font-weight: bold;")
        finally:
            self.status_check_lock.release()

    def check_if_process_started_correctly(self):
        """Проверяет, что процесс успешно запустился и продолжает работать"""
        # Если процесс находится в процессе перезапуска или был остановлен намеренно, пропускаем проверку
        if hasattr(self, 'process_restarting') and self.process_restarting:
            self.process_restarting = False  # Сбрасываем флаг
            self.check_process_status()  # Просто обновляем статус
            return
            
        if hasattr(self, 'manually_stopped') and self.manually_stopped:
            self.manually_stopped = False  # Сбрасываем флаг
            self.check_process_status()
            return
        
        # Проверяем, был ли недавно изменен режим (стратегия)
        current_time = time.time()
        if hasattr(self, 'last_strategy_change_time') and current_time - self.last_strategy_change_time < 5:
            # Пропускаем проверку, если стратегия была изменена менее 5 секунд назад
            self.check_process_status()
            return
            
        if not self.dpi_starter.check_process_running():
            # Если процесс не запущен, и это не связано с переключением стратегии, показываем ошибку
            exe_path = os.path.abspath(WINWS_EXE)
            QMessageBox.critical(self, "Ошибка запуска", 
                            f"Процесс winws.exe запустился, но затем неожиданно завершился.\n\n"
                            f"Путь к программе: {exe_path}\n\n"
                            "Это может быть вызвано:\n"
                            "1. Антивирус удалил часть критически важных файлов программы - переустановите программу заново\n"
                            "2. Какие-то файлы удалены из программы - скачате ZIP архив заново\n\n"
                            "Перед переустановкой программы создайте исключение в антивирусе.")
            self.update_ui(running=False)
        
        # В любом случае обновляем статус
        self.check_process_status()

    def start_dpi(self, selected_mode=None):
        """Запускает DPI с текущей конфигурацией, если служба ZapretCensorliber не установлена"""
        try:
            # Проверяем инициализирован ли service_manager
            if not hasattr(self, 'service_manager'):
                self.set_status("Инициализация менеджеров...")
                # Отложим запуск до полной инициализации
                QTimer.singleShot(1000, lambda: self.start_dpi(selected_mode))
                return False
            
            # Используем существующий метод проверки службы из ServiceManager
            service_found = self.service_manager.check_service_exists()
            
            if service_found:
                # При необходимости здесь можно показать предупреждение
                return False
            
            last_strategy = get_last_strategy()
            from log import log
            log("Загруженная стратегия: " + str(last_strategy))

            if selected_mode is None:
                # Если не указан конкретный режим, используем комбобокс
                selected_mode = self.start_mode_combo.currentText()

            # Проверяем, есть ли менеджер стратегий и работает ли он
            if hasattr(self, 'strategy_manager') and self.strategy_manager:
                try:
                    # Пытаемся использовать стратегию из менеджера
                    strategy_id = None
                    for i in range(self.start_mode_combo.count()):
                        if self.start_mode_combo.itemText(i) == selected_mode:
                            strategy_id = self.start_mode_combo.itemData(i)
                            break
                    
                    if strategy_id:
                        success = self.strategy_manager.execute_strategy(strategy_id)
                        if success:
                            self.update_ui(running=True)
                            # Сохраняем выбранную стратегию
                            set_last_strategy(selected_mode)
                            # Проверяем, не завершился ли процесс сразу после запуска
                            QTimer.singleShot(3000, self.check_if_process_started_correctly)
                            return success
                except Exception as e:
                    log(f"Ошибка при запуске стратегии: {str(e)}", level="ERROR")
                    # Если произошла ошибка, продолжаем с обычным методом запуска
            
            # Если менеджер стратегий не работает или вызвал ошибку, используем стандартный метод
            success = self.dpi_starter.start_with_progress(
                selected_mode, 
                DPI_COMMANDS, 
                DOWNLOAD_URLS,
                parent_widget=self,
            )

            # Проверяем, был ли процесс успешно запущен
            if success:
                self.update_ui(running=True)
                # Проверяем, не завершился ли процесс сразу после запуска
                QTimer.singleShot(3000, self.check_if_process_started_correctly)
            else:
                self.check_process_status()  # Обновляем статус в интерфейсе

            return success
        except Exception as e:
            from log import log
            log(f"Неожиданная ошибка при запуске DPI: {str(e)}", level="ERROR")
            self.set_status(f"Ошибка при запуске: {str(e)}")
            self.check_process_status()
            return False
    
    def update_autostart_ui(self, service_running):
        """Обновляет состояние кнопок и элементов интерфейса в зависимости от статуса службы"""
        # Обновляем видимость кнопок включения/отключения автозапуска
        self.autostart_enable_btn.setVisible(not service_running)
        self.autostart_disable_btn.setVisible(service_running)
        
        # Обновляем доступность выбора стратегии
        if service_running:
            # Если служба запущена, скрываем выбор стратегии и показываем сообщение
            self.start_mode_combo.setVisible(False)
            
            # Если метки еще нет, создаем её
            if not hasattr(self, 'service_info_label'):
                from PyQt5.QtWidgets import QLabel
                self.service_info_label = QLabel("Служба запущена с фиксированной стратегией!\nСменить стратегию НЕЛЬЗЯ!", self)
                self.service_info_label.setAlignment(Qt.AlignCenter)
                self.service_info_label.setStyleSheet("color: red; font-weight: bold;")
                
                # Находим индекс start_mode_combo в layout
                layout = self.layout()
                for i in range(layout.count()):
                    if layout.itemAt(i).widget() == self.start_mode_combo:
                        layout.insertWidget(i, self.service_info_label)
                        break
            
            # Показываем информационную метку
            self.service_info_label.setVisible(True)
        else:
            # Если служба остановлена, показываем выбор стратегии и скрываем сообщение
            self.start_mode_combo.setVisible(True)
            
            # Скрываем информационную метку, если она существует
            if hasattr(self, 'service_info_label'):
                self.service_info_label.setVisible(False)

    def update_strategies_list(self, force_update=False):
        """Обновляет список доступных стратегий"""
        try:
            # Получаем список стратегий
            strategies = self.strategy_manager.get_strategies_list(force_update=force_update)
            
            if not strategies:
                from log import log  # Перемещено внутрь функции
                log("Не удалось получить список стратегий", level="ERROR")
                return
            
            # Сохраняем текущий выбор
            current_selection = self.start_mode_combo.currentText()
            
            # Очищаем комбобокс со стратегиями
            self.start_mode_combo.clear()
            
            # Добавляем стратегии в комбобокс
            for strategy_id, strategy_info in strategies.items():
                # Используем name или id, если name отсутствует
                display_name = strategy_info.get('name', strategy_id)
                self.start_mode_combo.addItem(display_name, strategy_id)
            
            # Восстанавливаем выбор, если возможно
            index = self.start_mode_combo.findText(current_selection)
            if index >= 0:
                self.start_mode_combo.setCurrentIndex(index)
            else:
                # Если предыдущего выбора нет, берем последнюю сохраненную стратегию
                last_strategy = get_last_strategy()
                if last_strategy:
                    index = self.start_mode_combo.findText(last_strategy)
                    if index >= 0:
                        self.start_mode_combo.setCurrentIndex(index)
            
            from log import log  # Перемещено внутрь функции
            log(f"Загружено {len(strategies)} стратегий", level="INFO")
            
        except Exception as e:
            error_msg = f"Ошибка при обновлении списка стратегий: {str(e)}"
            from log import log  # Перемещено внутрь функции
            log(error_msg, level="ERROR")
            self.set_status(error_msg)
        
    def init_strategy_manager(self):
        """Инициализирует менеджер стратегий"""
        try:
            from strategy_manager import StrategyManager
            
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
            
            # Обновляем список стратегий с обработкой ошибок
            try:
                self.update_strategies_list()
            except Exception as e:
                from log import log
                log(f"Ошибка при обновлении списка стратегий: {str(e)}", level="ERROR")
                self.set_status(f"Не удалось загрузить стратегии: {str(e)}")
                
                # Заполняем комбо-бокс стратегиями из config.py
                if hasattr(self, 'start_mode_combo') and self.start_mode_combo:
                    self.start_mode_combo.clear()
                    from config import DPI_COMMANDS
                    self.start_mode_combo.addItems(DPI_COMMANDS.keys())
        except Exception as e:
            from log import log
            log(f"Ошибка при инициализации менеджера стратегий: {str(e)}", level="ERROR")
            self.set_status(f"Ошибка стратегий: {str(e)}")
            
            # Создаем заглушку для strategy_manager
            self.strategy_manager = None
            
            # Заполняем комбо-бокс стратегиями из config.py если он существует
            if hasattr(self, 'start_mode_combo') and self.start_mode_combo:
                from config import DPI_COMMANDS
                self.start_mode_combo.clear()
                self.start_mode_combo.addItems(DPI_COMMANDS.keys())

    def initialize_managers_and_services(self):
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
            status_callback=self.set_status
        )
        
        # Инициализируем стартер DPI
        self.dpi_starter = DPIStarter(
            winws_exe=WINWS_EXE,
            bin_folder=BIN_FOLDER,
            lists_folder=LISTS_FOLDER,
            status_callback=self.set_status
        )
        
        # Проверяем и обновляем UI службы
        service_running = self.service_manager.check_service_exists()
        self.update_autostart_ui(service_running)
        
        # Обновляем UI состояния запуска
        self.update_ui(running=True)
        
        # Проверяем наличие необходимых файлов
        self.set_status("Проверка файлов...")
        self.dpi_starter.download_files(DOWNLOAD_URLS)
        
        # Безопасно запускаем DPI после инициализации всех менеджеров
        QTimer.singleShot(500, self.start_dpi)

        # Обновляем состояние кнопки прокси
        QTimer.singleShot(500, self.update_proxy_button_state)
    
    def __init__(self, fast_load=False):
        self.fast_load = fast_load

        # Добавляем защиту от гонок данных при проверке статуса
        self.status_check_lock = threading.Lock()
        self.last_status = None
        self.last_status_time = 0
        self.status_check_interval = 0.5  # минимальный интервал между проверками в секундах

        super().__init__()
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
        """Принудительно включает комбо-боксы даже если они были отключены"""
        try:
                
            if hasattr(self, 'theme_combo'):
                # Полное восстановление состояния комбо-бокса тем
                self.theme_combo.setEnabled(True)
                self.theme_combo.show()
                self.theme_combo.setStyleSheet(f"{COMMON_STYLE} text-align: center;")

            if hasattr(self, 'start_mode_combo'):
                # Полное восстановление состояния комбо-бокса
                self.start_mode_combo.setEnabled(True)
                self.start_mode_combo.show()
                self.start_mode_combo.setStyleSheet(f"{COMMON_STYLE} text-align: center;")

            # Принудительное обновление UI
            QApplication.processEvents()
            
            # Возвращаем True если оба комбо-бокса существуют и активны
            return (hasattr(self, 'start_mode_combo') and self.start_mode_combo.isEnabled() and
                    hasattr(self, 'theme_combo') and self.theme_combo.isEnabled())
        except Exception as e:
            from log import log
            log(f"Ошибка при активации комбо-боксов: {str(e)}")
            return False
    
    def delayed_combo_enabler(self):
        from log import log
        """Повторно проверяет и активирует комбо-боксы через таймер"""
        if self.force_enable_combos():
            # Если успешно активировали, останавливаемся
            log("Комбо-боксы успешно активированы")
        else:
            # Если нет, повторяем через полсекунды
            log("Повторная попытка активации комбо-боксов")
            QTimer.singleShot(500, self.delayed_combo_enabler)

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
            QTimer.singleShot(500, self.delayed_combo_enabler)

    def on_mode_changed(self, selected_mode):
        """Обработчик смены режима в combobox"""
        # Записываем время изменения стратегии
        self.last_strategy_change_time = time.time()
        
        # Перезапускаем Discord только если:
        # 1. Это не первый запуск
        # 2. Автоперезапуск включен в настройках
        from discord_restart import get_discord_restart_setting
        if not self.first_start and get_discord_restart_setting():
            self.discord_manager.restart_discord_if_running()
        else:
            self.first_start = False  # Сбрасываем флаг первого запуска
        
        # Сохраняем выбранную стратегию в реестр
        set_last_strategy(selected_mode)
        
        # Запускаем DPI с новым режимом
        self.start_dpi(selected_mode=selected_mode)

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
        """Останавливает процесс DPI."""
        # Устанавливаем флаг намеренной остановки
        self.manually_stopped = True
        
        if self.dpi_starter.stop_dpi():
            self.update_ui(running=False)
        else:
            # Показываем сообщение об ошибке, если метод вернул False
            QMessageBox.warning(self, "Невозможно остановить", 
                            "Невозможно остановить Zapret, пока установлена служба.\n\n"
                            "Пожалуйста, сначала отключите автозапуск (нажмите на кнопку 'Отключить автозапуск').")
        self.check_process_status()  # Обновляем статус в интерфейсе

    def install_service(self):
        """Устанавливает службу DPI с текущей конфигурацией"""
        selected_config = self.start_mode_combo.currentText()
        if selected_config not in DPI_COMMANDS:
            self.set_status(f"Недопустимая конфигурация: {selected_config}")
            return
            
        # Получаем аргументы командной строки для выбранной конфигурации
        command_args = DPI_COMMANDS.get(selected_config, [])
        
        # Устанавливаем службу через ServiceManager и обновляем UI, если успешно
        if self.service_manager.install_service(command_args, config_name=selected_config):
            self.update_autostart_ui(True)
            self.check_process_status()

    def remove_service(self):
        """Удаляет службу DPI"""
        if self.service_manager.remove_service():
            self.update_autostart_ui(False)
            self.check_process_status()

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

        # Статусная строка
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

        self.start_mode_combo = QComboBox(self)
        self.start_mode_combo.setStyleSheet(f"{COMMON_STYLE} text-align: center;")
        self.start_mode_combo.addItems(DPI_COMMANDS.keys())

        last_strategy = get_last_strategy()
        if last_strategy in DPI_COMMANDS.keys():
            self.start_mode_combo.setCurrentText(last_strategy)
        self.start_mode_combo.currentTextChanged.connect(self.on_mode_changed)
        layout.addWidget(self.start_mode_combo)

        from PyQt5.QtWidgets import QGridLayout
        button_grid = QGridLayout()

        self.start_btn = RippleButton('Запустить Zapret', self, "54, 153, 70")
        self.start_btn.setStyleSheet(BUTTON_STYLE.format("54, 153, 70"))
        self.start_btn.setMinimumHeight(BUTTON_HEIGHT)
        self.start_btn.clicked.connect(self.start_dpi)

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

        # Добавляем все кнопки напрямую в сетку вместо использования контейнеров
        button_grid = QGridLayout()

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
        self.setFixedSize(450, 650) # ширина, высота окна

        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.check_process_status)
        self.status_timer.start(3000)

    def moveEvent(self, event):
        """Вызывается при перемещении окна"""
        # Временно останавливаем таймер
        was_active = self.status_timer.isActive()
        if was_active:
            self.status_timer.stop()
        
        # Выполняем стандартную обработку события
        super().moveEvent(event)
        
        # Перезапускаем таймер после небольшой задержки
        if was_active:
            QTimer.singleShot(200, lambda: self.status_timer.start())

def main():
    try:
        from log import log
        log("========================= ZAPRET ЗАПУСКАЕТСЯ ========================", level="START")
    except Exception as e:
        log(f"Failed to initialize logger: {e}", level="ERROR")

    app = QApplication(sys.argv)

    try:
        from check_start import display_startup_warnings
        can_continue = display_startup_warnings()
        if not can_continue:
            sys.exit(1)
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
        window.show()
        
        # Выполняем дополнительные проверки ПОСЛЕ отображения UI
        QTimer.singleShot(100, lambda: window.perform_delayed_checks())
        
        # Дополнительная гарантия, что комбо-боксы будут активны
        QTimer.singleShot(1000, lambda: window.force_enable_combos())
        QTimer.singleShot(2000, lambda: window.force_enable_combos())

        sys.exit(app.exec_())
    except Exception as e:
        QMessageBox.critical(None, "Ошибка", f"Произошла ошибка: {str(e)}")
        log(f"Ошибка при запуске приложения: {str(e)}", level="ERROR")
        sys.exit(1)

if __name__ == "__main__":
    main()