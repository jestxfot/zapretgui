"""
pip install pyinstaller packaging PyQt6 requests pywin32 python-telegram-bot psutil qt_material urllib3 nuitka paramiko qtawesome wmi
"""
import sys, os

# ──────────────────────────────────────────────────────────────
# Делаем рабочей директорией папку, где лежит exe/скрипт
# Нужно выполнить до любых других импортов!
# ──────────────────────────────────────────────────────────────
def _set_workdir_to_app():
    """Устанавливает рабочую директорию"""
    try:
        # Nuitka
        if "__compiled__" in globals():
            app_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        # PyInstaller
        elif getattr(sys, 'frozen', False):
            app_dir = os.path.dirname(sys.executable)
        # Обычный Python
        else:
            app_dir = os.path.dirname(os.path.abspath(__file__))

        os.chdir(app_dir)
        
        # Отладочная информация
        debug_info = f"""
=== ZAPRET STARTUP DEBUG ===
Compiled mode: {'__compiled__' in globals()}
Frozen mode: {getattr(sys, 'frozen', False)}
sys.executable: {sys.executable}
sys.argv[0]: {sys.argv[0]}
Working directory: {app_dir}
Directory exists: {os.path.exists(app_dir)}
Directory contents: {os.listdir(app_dir) if os.path.exists(app_dir) else 'N/A'}
========================
"""
        
        with open("zapret_startup.log", "w", encoding="utf-8") as f:
            f.write(debug_info)
            
    except Exception as e:
        with open("zapret_startup_error.log", "w", encoding="utf-8") as f:
            f.write(f"Error setting workdir: {e}\n")
            import traceback
            f.write(traceback.format_exc())

_set_workdir_to_app()

# ──────────────────────────────────────────────────────────────
# дальше можно импортировать всё остальное
# ──────────────────────────────────────────────────────────────
import subprocess, webbrowser, time

from PyQt6.QtCore    import QThread
from PyQt6.QtWidgets import QMessageBox, QWidget, QApplication, QMenu

from ui.main_window import MainWindowUI
from ui.theme import ThemeManager, COMMON_STYLE
from ui.splash_screen import SplashScreen

from startup.admin_check import is_admin

from dpi.dpi_controller import DPIController

from config import THEME_FOLDER, BAT_FOLDER, INDEXJSON_FOLDER, WINWS_EXE, ICON_PATH, ICON_TEST_PATH, WIDTH, HEIGHT
from config import get_last_strategy, set_last_strategy
from config import APP_VERSION
from utils import run_hidden

from autostart.autostart_remove import AutoStartCleaner
from ui.theme_subscription_manager import ThemeSubscriptionManager, apply_initial_theme

from dns import DNSSettingsDialog
from log import log

from config import CHANNEL

def _set_attr_if_exists(name: str, on: bool = True) -> None:
    """Безопасно включает атрибут, если он есть в текущей версии Qt."""
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
    """updater.py запускает: main.py --update <old_exe> <new_exe>"""
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

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from managers.ui_manager import UIManager
    from managers.dpi_manager import DPIManager
    from managers.heavy_init_manager import HeavyInitManager
    from managers.process_monitor_manager import ProcessMonitorManager
    from managers.subscription_manager import SubscriptionManager
    from managers.initialization_manager import InitializationManager

class LupiDPIApp(QWidget, MainWindowUI, ThemeSubscriptionManager):
    """Главное окно приложения с поддержкой тем и подписок"""

    from ui.theme import ThemeHandler
    # ✅ ДОБАВЛЯЕМ TYPE HINTS для менеджеров
    ui_manager: 'UIManager'
    dpi_manager: 'DPIManager' 
    heavy_init_manager: 'HeavyInitManager'
    process_monitor_manager: 'ProcessMonitorManager'
    subscription_manager: 'SubscriptionManager'
    initialization_manager: 'InitializationManager'
    theme_handler: 'ThemeHandler'

    def apply_background_image(self, image_path: str):
        """Применяет фоновое изображение к правильному виджету"""
        if not hasattr(self, 'main_widget'):
            log("main_widget не существует, применяем фон к self", "WARNING")
            target_widget = self
        else:
            log("Применяем фон к main_widget", "DEBUG")
            target_widget = self.main_widget
        
        # Проверяем существование файла
        if not os.path.exists(image_path):
            log(f"Файл фона не найден: {image_path}", "ERROR")
            return False
        
        # Применяем стиль с фоном
        style = f"""
        QWidget {{
            background-image: url({image_path});
            background-position: center;
            background-repeat: no-repeat;
        }}
        """
        
        # Сохраняем текущие стили и добавляем фон
        current_style = target_widget.styleSheet()
        if "background-image:" not in current_style:
            target_widget.setStyleSheet(current_style + style)
        else:
            # Заменяем существующий фон
            target_widget.setStyleSheet(style + current_style)
        
        log(f"Фон применен к {target_widget.__class__.__name__}", "INFO")
        return True

    def closeEvent(self, event):
        """Обрабатывает событие закрытия окна"""
        self._is_exiting = True
        
        # ✅ Очищаем менеджеры через их методы
        if hasattr(self, 'heavy_init_manager'):
            self.heavy_init_manager.cleanup()
        
        if hasattr(self, 'process_monitor_manager'):
            self.process_monitor_manager.stop_monitoring()
        
        # ✅ Очищаем DNS UI Manager
        if hasattr(self, 'dns_ui_manager'):
            self.dns_ui_manager.cleanup()
        
        # ✅ Очищаем потоки через контроллер
        if hasattr(self, 'dpi_controller'):
            self.dpi_controller.cleanup_threads()
        
        # Останавливаем все асинхронные операции без уведомлений
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
        
        super().closeEvent(event)
        
    def set_status(self, text: str) -> None:
        """Sets the status text."""
        self.status_label.setText(text)

    def update_ui(self, running: bool) -> None:
        """Обновляет состояние кнопок в зависимости от статуса запуска"""
        if hasattr(self, 'ui_manager'):
            self.ui_manager.update_ui_state(running)

    def update_strategies_list(self, force_update: bool = False) -> None:
        """Обновляет список доступных стратегий"""
        if hasattr(self, 'ui_manager'):
            self.ui_manager.update_strategies_list(force_update)

    def delayed_dpi_start(self) -> None:
        """Выполняет отложенный запуск DPI с проверкой наличия автозапуска"""
        if hasattr(self, 'dpi_manager'):
            self.dpi_manager.delayed_dpi_start()

    def update_autostart_ui(self, service_running: bool) -> None:
        """Обновляет интерфейс при включении/выключении автозапуска"""
        if hasattr(self, 'ui_manager'):
            self.ui_manager.update_autostart_ui(service_running)

    def force_enable_combos(self) -> bool:
        """Принудительно включает комбо-боксы тем"""
        if hasattr(self, 'ui_manager'):
            return self.ui_manager.force_enable_combos()
        return False
        
    def select_strategy(self) -> None:
        """Открывает диалог выбора стратегии БЕЗ загрузки из интернета"""
        try:
            if not hasattr(self, 'strategy_manager') or not self.strategy_manager:
                log("Ошибка: менеджер стратегий не инициализирован", "❌ ERROR")
                self.set_status("Ошибка: менеджер стратегий не инициализирован")
                return

            # ✅ Всегда используем только локальные стратегии
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

    def _show_strategy_dialog(self) -> None:
        """Показывает диалог выбора стратегии"""
        try:
            # ✅ ЗАКРЫВАЕМ ПРЕДЫДУЩИЙ ДИАЛОГ ЕСЛИ ОН ЕСТЬ
            if hasattr(self, '_strategy_selector_dialog') and self._strategy_selector_dialog:
                if self._strategy_selector_dialog.isVisible():
                    # Если диалог видим, но мы пытаемся открыть новый - закрываем старый
                    log("Закрытие предыдущего диалога стратегий", "DEBUG")
                    self._strategy_selector_dialog.close()
                    self._strategy_selector_dialog = None

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

    def on_strategy_selected_from_dialog(self, strategy_id: str, strategy_name: str) -> None:
        """Обрабатывает выбор стратегии из диалога."""
        try:
            log(f"Выбрана стратегия: {strategy_name} (ID: {strategy_id})", level="INFO")
            
            # Сохраняем ID и имя выбранной стратегии в атрибутах класса
            self.current_strategy_id = strategy_id
            self.current_strategy_name = strategy_name
            
            # ✅ ДЛЯ КОМБИНИРОВАННЫХ СТРАТЕГИЙ ИСПОЛЬЗУЕМ ПРОСТОЕ НАЗВАНИЕ
            if strategy_id == "COMBINED_DIRECT":
                # Просто устанавливаем "Прямой запуск" без деталей
                display_name = "Прямой запуск"
                self.current_strategy_name = display_name
                strategy_name = display_name
                
                # ✅ ВАЖНО: Сохраняем специальный маркер "COMBINED_DIRECT" в реестр
                set_last_strategy("COMBINED_DIRECT")  # <-- Сохраняем ID, а не название!
                
                log(f"Установлено простое название для комбинированной стратегии: {display_name}", "DEBUG")
            else:
                # Для обычных стратегий сохраняем имя как раньше
                set_last_strategy(strategy_name)
            
            # Обновляем метку с текущей стратегией
            self.current_strategy_label.setText(strategy_name)
    
            # Записываем время изменения стратегии
            self.last_strategy_change_time = time.time()
            
            # ✅ ИСПРАВЛЕННАЯ ЛОГИКА для обработки комбинированных стратегий
            from strategy_menu import get_strategy_launch_method
            launch_method = get_strategy_launch_method()
            
            if launch_method == "direct":
                # Проверяем, является ли это комбинированной стратегией
                if strategy_id == "COMBINED_DIRECT":
                    # ✅ ИСПРАВЛЕНИЕ: Используем правильное имя атрибута
                    combined_data = {
                        'id': strategy_id,
                        'name': strategy_name,
                        'is_combined': True
                    }
                    
                    # Пытаемся получить данные из диалога
                    combined_args = None
                    category_selections = None
                    
                    # ✅ ПРАВИЛЬНОЕ ОБРАЩЕНИЕ К ДИАЛОГУ
                    if hasattr(self, '_strategy_selector_dialog') and self._strategy_selector_dialog is not None:
                        if hasattr(self._strategy_selector_dialog, '_combined_args'):
                            combined_args = self._strategy_selector_dialog._combined_args
                            log(f"Получены аргументы из диалога: {len(combined_args)} символов", "DEBUG")
                        
                        if hasattr(self._strategy_selector_dialog, 'category_selections'):
                            category_selections = self._strategy_selector_dialog.category_selections
                            log(f"Получены выборы категорий: {category_selections}", "DEBUG")
                    
                    # Если данные не получены из диалога, создаем заново
                    if not combined_args or not category_selections:
                        log("Создаем комбинированную стратегию заново из значений по умолчанию", "⚠ WARNING")
                        from strategy_menu.strategy_lists_separated import combine_strategies, get_default_selections
                        
                        default_selections = get_default_selections()
                        combined_strategy = combine_strategies(
                            default_selections.get('youtube'),
                            default_selections.get('youtube_udp'),
                            default_selections.get('googlevideo_tcp'),
                            default_selections.get('discord'), 
                            default_selections.get('discord_voice_udp'),
                            default_selections.get('twitch_tcp'),
                            default_selections.get('other'),
                            default_selections.get('ipset'),
                            default_selections.get('ipset_udp'),
                        )
                        
                        combined_args = combined_strategy['args']
                        category_selections = default_selections
                    
                    # Добавляем данные в объект
                    if combined_args:
                        combined_data['args'] = combined_args
                        log(f"Добавлены аргументы: {len(combined_args)} символов", "DEBUG")
                    if category_selections:
                        combined_data['selections'] = category_selections
                        log(f"Добавлены выборы: {category_selections}", "DEBUG")
                    
                    # Сохраняем для следующего раза
                    self._last_combined_args = combined_args
                    self._last_category_selections = category_selections
                    
                    # Запускаем DPI контроллер
                    self.dpi_controller.start_dpi_async(selected_mode=combined_data)
                    
                else:
                    # Обычная встроенная стратегия
                    self.dpi_controller.start_dpi_async(selected_mode=(strategy_id, strategy_name))
            else:
                # Для BAT метода получаем полную информацию
                try:
                    strategies = self.strategy_manager.get_strategies_list()
                    strategy_info = strategies.get(strategy_id, {})
                    
                    if not strategy_info:
                        strategy_info = {
                            'name': strategy_name,
                            'file_path': f"{strategy_id}.bat"
                        }
                        log(f"Не удалось найти информацию о стратегии {strategy_id}, используем базовую", "⚠ WARNING")
                    
                    self.dpi_controller.start_dpi_async(selected_mode=strategy_info)
                    
                except Exception as strategy_error:
                    log(f"Ошибка при получении информации о стратегии: {strategy_error}", "❌ ERROR")
                    self.dpi_controller.start_dpi_async(selected_mode=strategy_name)
            
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

    def __init__(self):
        super().__init__()
        QWidget.__init__(self)
        
        # Флаги для защиты от двойных вызовов
        self._splash_closed = False
        self._dpi_autostart_initiated = False
        self._heavy_init_started = False
        self._heavy_init_thread = None

        # Устанавливаем основные параметры окна
        self.setWindowTitle(f"Zapret v{APP_VERSION} - загрузка...")

        # ✅ УСТАНАВЛИВАЕМ ПРАВИЛЬНЫЙ РАЗМЕР ОКНА
        self.setMinimumSize(WIDTH, HEIGHT)  # Минимальный размер
        self.resize(WIDTH, HEIGHT)          # Текущий размер
                
        # Устанавливаем иконку
        icon_path = ICON_TEST_PATH if CHANNEL == "test" else ICON_PATH
        if os.path.exists(icon_path):
            from PyQt6.QtGui import QIcon
            app_icon = QIcon(icon_path)
            self.setWindowIcon(app_icon)
            QApplication.instance().setWindowIcon(app_icon)
        
        from PyQt6.QtWidgets import QStackedWidget
        # Создаем QStackedWidget для переключения между экранами
        self.stacked_widget = QStackedWidget()
        from PyQt6.QtWidgets import QVBoxLayout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.stacked_widget)
        
        # Создаем загрузочный экран
        self.splash = SplashScreen(self)
        self.splash.load_complete.connect(self._on_splash_complete)
        
        # Создаем основной виджет (будет содержать весь UI)
        self.main_widget = QWidget()
        # ✅ УСТАНАВЛИВАЕМ РАЗМЕР ДЛЯ MAIN_WIDGET
        self.main_widget.setMinimumSize(WIDTH, HEIGHT)

        # ✅ НЕ СОЗДАЕМ theme_handler ЗДЕСЬ - создадим его после theme_manager

        # Добавляем оба виджета в stack
        self.splash_index = self.stacked_widget.addWidget(self.splash)
        self.main_index = self.stacked_widget.addWidget(self.main_widget)
        
        # Показываем загрузочный экран
        self.stacked_widget.setCurrentIndex(self.splash_index)
        
        # Показываем окно
        self.show()
        
        # Обновляем прогресс
        self.splash.set_progress(5, "Запуск Zapret...", "Инициализация компонентов")
        
        # Инициализируем атрибуты
        self.process_monitor = None
        self.first_start = True
        self.current_strategy_id = None
        self.current_strategy_name = None
        
        # Теперь строим UI в main_widget (не в self)
        self._build_main_ui()
        
        # Обновляем прогресс
        self.splash.set_progress(6, "Создание интерфейса...", "")

        # Создаем менеджеры
        from managers.initialization_manager import InitializationManager
        from managers.subscription_manager import SubscriptionManager
        from managers.heavy_init_manager import HeavyInitManager
        from managers.process_monitor_manager import ProcessMonitorManager
        from managers.ui_manager import UIManager
        from managers.dpi_manager import DPIManager

        self.initialization_manager = InitializationManager(self)
        self.subscription_manager = SubscriptionManager(self)
        self.heavy_init_manager = HeavyInitManager(self)
        self.process_monitor_manager = ProcessMonitorManager(self)
        self.ui_manager = UIManager(self)
        self.dpi_manager = DPIManager(self)

        # Инициализируем donate checker
        self.splash.set_progress(10, "Проверка подписки...", "")
        self._init_real_donate_checker()  # Упрощенная версия
        self.update_title_with_subscription_status(False, None, 0)
        
        # Запускаем асинхронную инициализацию через менеджер
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(50, self.initialization_manager.run_async_init)
        QTimer.singleShot(1000, self.subscription_manager.initialize_async)

    def init_theme_handler(self):
        """Инициализирует theme_handler после создания theme_manager"""
        if not hasattr(self, 'theme_handler'):
            from ui.theme import ThemeHandler
            self.theme_handler = ThemeHandler(self, target_widget=self.main_widget)
            
            # Если theme_manager уже создан, устанавливаем его
            if hasattr(self, 'theme_manager'):
                self.theme_handler.set_theme_manager(self.theme_manager)
                
            log("ThemeHandler инициализирован", "DEBUG")

    def _build_main_ui(self) -> None:
        """Строит основной UI в main_widget"""
        # Временно меняем self на main_widget для build_ui
        old_layout = self.main_widget.layout()
        if old_layout is not None:
            while old_layout.count():
                item = old_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            QWidget().setLayout(old_layout)
        
        # Создаем layout для main_widget
        from ui.theme import STYLE_SHEET
        self.main_widget.setStyleSheet(STYLE_SHEET)
        
        # Вызываем build_ui но с модификацией - все виджеты создаются как дети main_widget
        # Для этого временно подменяем методы
        original_method = self.build_ui
        
        # Создаем модифицированный build_ui
        def modified_build_ui(width, height):
            # Сохраняем оригинальные методы
            original_setStyleSheet = self.setStyleSheet
            original_setMinimumSize = self.setMinimumSize
            original_layout = self.layout
            
            # Временно перенаправляем на main_widget
            self.setStyleSheet = self.main_widget.setStyleSheet
            self.setMinimumSize = self.main_widget.setMinimumSize
            self.layout = self.main_widget.layout
            
            # Вызываем оригинальный build_ui
            original_method(width, height)
            
            # Восстанавливаем методы
            self.setStyleSheet = original_setStyleSheet
            self.setMinimumSize = original_setMinimumSize
            self.layout = original_layout
        
        # Вызываем модифицированный метод
        modified_build_ui(WIDTH, HEIGHT)

    def _on_splash_complete(self) -> None:
        """Обработчик завершения загрузки"""
        if self._splash_closed:
            log("Splash уже закрыт, пропускаем", "DEBUG")
            return
            
        self._splash_closed = True
        log("Загрузочный экран завершен, переключаемся на главный интерфейс", "INFO")
        
        # Переключаемся на основной виджет
        self.stacked_widget.setCurrentIndex(self.main_index)
        
        # ✅ ВАЖНО: Повторно применяем тему РКН Тян если она выбрана
        if hasattr(self, 'theme_manager') and self.theme_manager.current_theme == "РКН Тян":
            log("Повторное применение темы РКН Тян после переключения виджетов", "DEBUG")
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(200, lambda: self.theme_manager.apply_rkn_background())
        
        self.splash = None

    def _init_real_donate_checker(self) -> None:
        """Создает базовый DonateChecker (полная инициализация в SubscriptionManager)"""
        try:
            from donater import DonateChecker
            self.donate_checker = DonateChecker()
            log("Базовый DonateChecker создан", "DEBUG")
        except Exception as e:
            log(f"Ошибка создания DonateChecker: {e}", "❌ ERROR")

    def show_subscription_dialog(self) -> None:
        """Показывает диалог управления подписками"""
        try:  
            self.set_status("Проверяю статус подписки...")
            QApplication.processEvents()
            
            from donater import SubscriptionDialog
            dialog = SubscriptionDialog(self)
            result = dialog.exec()
            
            # После закрытия диалога обновляем статус в заголовке
            if hasattr(self, 'subscription_manager'):
                self.subscription_manager.update_subscription_ui()
            
            # Используем UI Manager
            if hasattr(self, 'theme_manager') and hasattr(self, 'ui_manager'):
                available_themes = self.theme_manager.get_available_themes()
                self.ui_manager.update_theme_combo(available_themes)
                
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
            
    def manual_update_check(self) -> None:
        """Ручная проверка обновлений (кнопка) - АСИНХРОННАЯ версия"""
        log("Запуск ручной проверки обновлений...", level="INFO")
        self.set_status("Проверка обновлений…")
        
        try:
            from updater import run_update_async
            
            # Создаём асинхронный поток для проверки
            thread = run_update_async(parent=self, silent=False)
            
            # Сохраняем ссылку на поток
            self._manual_update_thread = thread
            
            # Подключаем обработчик завершения
            if hasattr(thread, '_worker'):
                worker = thread._worker
                
                def _manual_update_done(ok: bool):
                    if ok:
                        self.set_status("🔄 Обновление запущено")
                    else:
                        # Проверяем, было ли найдено обновление или нет
                        self.set_status("✅ Проверка завершена")
                    
                    # Удаляем ссылки
                    if hasattr(self, '_manual_update_thread'):
                        del self._manual_update_thread
                
                worker.finished.connect(_manual_update_done)
                
                # Блокируем кнопку на время проверки
                if hasattr(self, 'update_check_btn'):
                    self.update_check_btn.setEnabled(False)
                    worker.finished.connect(lambda: self.update_check_btn.setEnabled(True))
            
        except Exception as e:
            log(f"Ошибка при запуске проверки обновлений: {e}", "❌ ERROR")
            self.set_status(f"Ошибка проверки: {e}")
            
            # Разблокируем кнопку в случае ошибки
            if hasattr(self, 'update_check_btn'):
                self.update_check_btn.setEnabled(True)
        
    def open_folder(self) -> None:
        """Opens the DPI folder."""
        try:
            run_hidden('explorer.exe .', shell=True)
        except Exception as e:
            self.set_status(f"Ошибка при открытии папки: {str(e)}")

    def show_autostart_options(self) -> None:
        """Показывает диалог автозапуска с поддержкой Direct режима"""
        from autostart.autostart_menu import AutoStartMenu
        from strategy_menu import get_strategy_launch_method
        
        # Если уже есть автозапуск — предупредим и выйдем
        from autostart.registry_check import is_autostart_enabled
        if is_autostart_enabled():
            log("Автозапуск уже активен", "⚠ WARNING")
            self.set_status("Сначала отключите текущий автозапуск.<br>Если он уже отключён - перезагрузите ПК.")
            return

        # Определяем режим запуска
        launch_method = get_strategy_launch_method()
        is_direct_mode = (launch_method == "direct")
        
        # Определяем название стратегии
        if is_direct_mode:
            # Для Direct режима получаем название из комбинированной стратегии
            from strategy_menu import get_direct_strategy_selections
            from strategy_menu.strategy_lists_separated import combine_strategies
            
            try:
                selections = get_direct_strategy_selections()
                combined = combine_strategies(
                    selections.get('youtube_udp'),
                    selections.get('youtube'),
                    selections.get('googlevideo_tcp'),
                    selections.get('discord'),
                    selections.get('discord_voice_udp'),
                    selections.get('twitch_tcp'),
                    selections.get('other'),
                    selections.get('ipset'),
                    selections.get('ipset_udp'),
                )
                strategy_name = combined['description']
            except:
                # Fallback на текущую метку или последнюю стратегию
                strategy_name = self.current_strategy_label.text()
                if strategy_name == "Автостарт DPI отключен":
                    strategy_name = get_last_strategy()
        else:
            # Для BAT режима используем текущую метку
            strategy_name = self.current_strategy_label.text()
            if strategy_name == "Автостарт DPI отключен":
                strategy_name = get_last_strategy()
        
        log(f"Открытие диалога автозапуска (режим: {launch_method}, стратегия: {strategy_name})", "INFO")

        dlg = AutoStartMenu(
            parent             = self,
            strategy_name      = strategy_name,
            bat_folder         = BAT_FOLDER,
            json_folder        = INDEXJSON_FOLDER,
            check_autostart_cb = self.service_manager.check_autostart_exists,
            update_ui_cb       = self.update_autostart_ui,
            status_cb          = self.set_status,
            app_instance       = self  # НОВОЕ - передаем экземпляр приложения для Direct режима
        )
        dlg.exec()

    def show_stop_menu(self) -> None:
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
            self.dpi_controller.stop_dpi_async()
        elif action == stop_and_exit_action:
            log("Выбрано: Остановить и закрыть программу", level="INFO")
            self.set_status("Останавливаю Zapret и закрываю программу...")
            
            # ✅ УСТАНАВЛИВАЕМ флаг полного закрытия перед остановкой
            self._closing_completely = True
            
            # ✅ НЕ показываем уведомление - программа полностью закрывается
            self.dpi_controller.stop_and_exit_async()

    def remove_autostart(self) -> None:
        """Удаляет автозапуск через AutoStartCleaner"""
        cleaner = AutoStartCleaner(status_cb=self.set_status)
        if cleaner.run():
            self.update_autostart_ui(False)
            if hasattr(self, 'process_monitor_manager'):
                # Проверяем статус процесса через dpi_starter
                is_running = False
                if hasattr(self, 'dpi_starter'):
                    is_running = self.dpi_starter.check_process_running_wmi(silent=True)
                self.process_monitor_manager.on_process_status_changed(is_running)

        from autostart.autostart_exe import remove_all_autostart_mechanisms
        if remove_all_autostart_mechanisms():
            self.set_status("Автозапуск отключен")
            self.update_autostart_ui(False)
            if hasattr(self, 'process_monitor_manager'):
                # Проверяем статус процесса через dpi_starter
                is_running = False
                if hasattr(self, 'dpi_starter'):
                    is_running = self.dpi_starter.check_process_running_wmi(silent=True)
                self.process_monitor_manager.on_process_status_changed(is_running)
        else:
            self.set_status("Ошибка отключения автозапуска")
    
    def toggle_proxy_domains(self) -> None:
        """Переключает состояние разблокировки: добавляет или удаляет записи из hosts"""
        if not hasattr(self, 'hosts_ui_manager'):
            self.set_status("Ошибка: менеджер hosts UI не инициализирован")
            return
        
        self.hosts_ui_manager.toggle_proxy_domains(self.proxy_button)

    def open_connection_test(self) -> None:
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

    def open_dns_settings(self) -> None:
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

def set_batfile_association() -> bool:
    """
    Устанавливает ассоциацию типа файла для .bat файлов
    """
    try:
        # Используем максимально скрытый режим
        command = r'ftype batfile="%SystemRoot%\System32\cmd.exe" /c "%1" %*'

        result = subprocess.run(command, shell=True, check=True, 
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)

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
    log(APP_VERSION, "🔹 main")

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
    from startup.ipc_manager import IPCManager
    
    mutex_handle, already_running = create_mutex("ZapretSingleInstance")
    if already_running:
        ipc = IPCManager()
        if ipc.send_show_command():
            log("Отправлена команда показать окно запущенному экземпляру", "INFO")
        else:
            ctypes.windll.user32.MessageBoxW(None, 
                "Экземпляр Zapret уже запущен, но не удалось показать окно!", "Zapret", 0x40)
        sys.exit(0)
    
    atexit.register(lambda: release_mutex(mutex_handle))

    # ---------------- Создаём QApplication СРАЗУ ----------------
    try:
        os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
        _set_attr_if_exists("AA_EnableHighDpiScaling")
        _set_attr_if_exists("AA_UseHighDpiPixmaps")

        app = QApplication(sys.argv)
        app.setQuitOnLastWindowClosed(False)
        
        # ✅ ИСПОЛЬЗУЕМ НОВЫЙ МОДУЛЬ ДЛЯ ПРИМЕНЕНИЯ ТЕМЫ
        apply_initial_theme(app)
        
    except Exception as e:
        ctypes.windll.user32.MessageBoxW(None,
            f"Ошибка инициализации Qt: {e}", "Zapret", 0x10)
        sys.exit(1)

    # ---------- проверяем Касперского + показываем диалог -----------------
    try:
        kaspersky_detected = _check_kaspersky_antivirus(None)
    except Exception:
        kaspersky_detected = False

    if kaspersky_detected:
        log("Обнаружен антивирус Kaspersky", "⚠️ KASPERSKY")
        try:
            from startup.kaspersky import show_kaspersky_warning
            show_kaspersky_warning()
        except Exception as e:
            log(f"Не удалось показать предупреждение Kaspersky: {e}",
                "⚠️ KASPERSKY")

    # ---------------- СОЗДАЁМ И ПОКАЗЫВАЕМ ОКНО СРАЗУ ----------------
    window = LupiDPIApp()
    
    # ✅ ЗАПУСКАЕМ IPC СЕРВЕР ДЛЯ ПРИЕМА КОМАНД
    ipc_manager = IPCManager()
    ipc_manager.start_server(window)
    atexit.register(ipc_manager.stop)
    
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
            from startup.bfe_util import preload_service_status, ensure_bfe_running, cleanup as bfe_cleanup
            from startup.check_start import check_startup_conditions, display_startup_warnings
            from startup.remove_terminal import remove_windows_terminal_if_win11
            from startup.admin_check_debug import debug_admin_status
            
            preload_service_status("BFE")
            
            if not ensure_bfe_running(show_ui=True):
                return
            
            conditions_ok, error_msg = check_startup_conditions()
            if not conditions_ok and not start_in_tray:
                if error_msg:
                    QMessageBox.critical(window, "Ошибка запуска", error_msg)
                return
            
            warnings_ok = display_startup_warnings()
            if not warnings_ok and not start_in_tray:
                return
            
            remove_windows_terminal_if_win11()
            debug_admin_status()
            set_batfile_association()
            
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