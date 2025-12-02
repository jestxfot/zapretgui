# main.py
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
# Устанавливаем глобальный обработчик крашей (ДО всех импортов!)
# ──────────────────────────────────────────────────────────────
from log.crash_handler import install_crash_handler
install_crash_handler()

# ──────────────────────────────────────────────────────────────
# дальше можно импортировать всё остальное
# ──────────────────────────────────────────────────────────────
import subprocess, webbrowser, time

from PyQt6.QtCore    import QThread, QTimer
from PyQt6.QtWidgets import QMessageBox, QWidget, QApplication, QMenu, QDialog

from ui.main_window import MainWindowUI
from ui.theme import ThemeManager, COMMON_STYLE
from ui.splash_screen import SplashScreen
from ui.custom_titlebar import CustomTitleBar, FramelessWindowMixin

from startup.admin_check import is_admin

from dpi.dpi_controller import DPIController

from config import THEME_FOLDER, BAT_FOLDER, INDEXJSON_FOLDER, WINWS_EXE, ICON_PATH, ICON_TEST_PATH, WIDTH, HEIGHT
from config import get_last_strategy, set_last_strategy
from config import APP_VERSION
from utils import run_hidden

from autostart.autostart_remove import AutoStartCleaner
from ui.theme_subscription_manager import ThemeSubscriptionManager, apply_initial_theme

# DNS настройки теперь интегрированы в network_page
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

class LupiDPIApp(QWidget, MainWindowUI, ThemeSubscriptionManager, FramelessWindowMixin):
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
        
        # ✅ СОХРАНЯЕМ ПОЗИЦИЮ И РАЗМЕР ОКНА
        try:
            from config import set_window_position, set_window_size
            
            # Сохраняем позицию
            pos = self.pos()
            set_window_position(pos.x(), pos.y())
            
            # Сохраняем размер
            size = self.size()
            set_window_size(size.width(), size.height())
            
            log(f"Сохранена позиция окна: ({pos.x()}, {pos.y()}), размер: ({size.width()}x{size.height()})", "DEBUG")
        except Exception as e:
            log(f"Ошибка сохранения геометрии окна: {e}", "❌ ERROR")
        
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

    def restore_window_geometry(self):
        """Восстанавливает сохраненную позицию и размер окна"""
        try:
            from config import get_window_position, get_window_size, WIDTH, HEIGHT
            from PyQt6.QtWidgets import QApplication
            
            # Восстанавливаем размер
            saved_size = get_window_size()
            if saved_size:
                width, height = saved_size
                # Проверяем что размер не меньше минимального
                if width >= WIDTH and height >= HEIGHT:
                    self.resize(width, height)
                    log(f"Восстановлен размер окна: {width}x{height}", "DEBUG")
                else:
                    log(f"Сохраненный размер слишком мал, используем по умолчанию", "DEBUG")
                    self.resize(WIDTH, HEIGHT)
            else:
                self.resize(WIDTH, HEIGHT)
            
            # Восстанавливаем позицию
            saved_pos = get_window_position()
            if saved_pos:
                x, y = saved_pos
                
                # Проверяем что окно будет видимо на каком-то из экранов
                screen_geometry = QApplication.primaryScreen().availableGeometry()
                screens = QApplication.screens()
                
                # Проверяем все экраны
                is_visible = False
                for screen in screens:
                    screen_rect = screen.availableGeometry()
                    # Окно считается видимым если хотя бы 100x100 пикселей на экране
                    if (x + 100 > screen_rect.left() and 
                        x < screen_rect.right() and
                        y + 100 > screen_rect.top() and 
                        y < screen_rect.bottom()):
                        is_visible = True
                        break
                
                if is_visible:
                    self.move(x, y)
                    log(f"Восстановлена позиция окна: ({x}, {y})", "DEBUG")
                else:
                    # Если окно за пределами всех экранов - центрируем на основном
                    self.move(
                        screen_geometry.center().x() - self.width() // 2,
                        screen_geometry.center().y() - self.height() // 2
                    )
                    log(f"Сохраненная позиция за пределами экранов, окно отцентрировано", "WARNING")
            else:
                # Если позиция не сохранена - центрируем
                screen_geometry = QApplication.primaryScreen().availableGeometry()
                self.move(
                    screen_geometry.center().x() - self.width() // 2,
                    screen_geometry.center().y() - self.height() // 2
                )
                log("Позиция не сохранена, окно отцентрировано", "DEBUG")
                
        except Exception as e:
            log(f"Ошибка восстановления геометрии окна: {e}", "❌ ERROR")
            # В случае ошибки используем размер по умолчанию
            from config import WIDTH, HEIGHT
            self.resize(WIDTH, HEIGHT)

    def set_status(self, text: str) -> None:
        """Sets the status text."""
        # Обновляем статус на главной странице
        if hasattr(self, 'home_page'):
            # Определяем тип статуса по тексту
            status_type = "neutral"
            if "работает" in text.lower() or "запущен" in text.lower() or "успешно" in text.lower():
                status_type = "running"
            elif "останов" in text.lower() or "ошибка" in text.lower() or "выключен" in text.lower():
                status_type = "stopped"
            elif "внимание" in text.lower() or "предупреждение" in text.lower():
                status_type = "warning"
            self.home_page.set_status(text, status_type)

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
        """Переключает на страницу стратегий"""
        try:
            # Переключаемся на страницу стратегий в новом интерфейсе
            if hasattr(self, 'main_window') and hasattr(self.main_window, 'side_nav'):
                self.main_window.side_nav.set_section(2)  # Индекс страницы стратегий
                log("Переключение на страницу стратегий", "DEBUG")
            else:
                log("Страница стратегий недоступна", "WARNING")

        except Exception as e:
            log(f"Ошибка при открытии страницы стратегий: {e}", "❌ ERROR")
            self.set_status(f"Ошибка при выборе стратегии: {e}")
    
    def on_strategy_selected_from_dialog(self, strategy_id: str, strategy_name: str) -> None:
        """Обрабатывает выбор стратегии из диалога."""
        try:
            log(f"Выбрана стратегия: {strategy_name} (ID: {strategy_id})", level="INFO")
            
            # Сохраняем ID и имя выбранной стратегии в атрибутах класса
            self.current_strategy_id = strategy_id
            self.current_strategy_name = strategy_name
            
            # ✅ УБИРАЕМ АВТОМАТИЧЕСКОЕ СКРЫТИЕ - теперь это контролируется настройкой
            # Диалог сам решит закрываться или нет в методе accept()
            
            # ✅ ДЛЯ КОМБИНИРОВАННЫХ СТРАТЕГИЙ ИСПОЛЬЗУЕМ ПРОСТОЕ НАЗВАНИЕ
            if strategy_id == "COMBINED_DIRECT":
                display_name = "Прямой запуск"
                self.current_strategy_name = display_name
                strategy_name = display_name
                
                set_last_strategy("COMBINED_DIRECT")
                
                log(f"Установлено простое название для комбинированной стратегии: {display_name}", "DEBUG")
            else:
                set_last_strategy(strategy_name)
            
            # Обновляем метку с текущей стратегией
            self.current_strategy_label.setText(strategy_name)
            
            # Обновляем новые страницы интерфейса
            if hasattr(self, 'update_current_strategy_display'):
                self.update_current_strategy_display(strategy_name)

            # Записываем время изменения стратегии
            self.last_strategy_change_time = time.time()
            
            # ✅ ИСПРАВЛЕННАЯ ЛОГИКА для обработки комбинированных стратегий
            from strategy_menu import get_strategy_launch_method
            launch_method = get_strategy_launch_method()
            
            if launch_method == "direct":
                if strategy_id == "COMBINED_DIRECT" or strategy_id == "combined":
                    # Получаем стратегию из сохранённых настроек
                    from strategy_menu.strategy_lists_separated import combine_strategies
                    from strategy_menu import get_direct_strategy_selections, get_default_selections
                        
                    try:
                        category_selections = get_direct_strategy_selections()
                    except:
                        category_selections = get_default_selections()
                    
                    combined_strategy = combine_strategies(**category_selections)
                    combined_args = combined_strategy['args']
                    
                    combined_data = {
                        'id': strategy_id,
                        'name': strategy_name,
                        'is_combined': True,
                        'args': combined_args,
                        'selections': category_selections
                    }
                    
                    log(f"Комбинированная стратегия: {len(combined_args)} символов", "DEBUG")
                    
                    self._last_combined_args = combined_args
                    self._last_category_selections = category_selections
                    
                    self.dpi_controller.start_dpi_async(selected_mode=combined_data)
                    
                else:
                    self.dpi_controller.start_dpi_async(selected_mode=(strategy_id, strategy_name))
            else:
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
            
            # ✅ Перезапуск Discord теперь выполняется в dpi_controller._on_dpi_start_finished()
            # после успешного запуска DPI (убрано дублирование)
                
        except Exception as e:
            log(f"Ошибка при установке выбранной стратегии: {str(e)}", level="❌ ERROR")
            import traceback
            log(f"Traceback: {traceback.format_exc()}", "DEBUG")
            self.set_status(f"Ошибка при установке стратегии: {str(e)}")

    def __init__(self, start_in_tray=False):
        # ✅ Вызываем super().__init__() ОДИН раз - он инициализирует все базовые классы
        super().__init__()
        
        # ✅ ИНИЦИАЛИЗИРУЕМ МЕТОД ЗАПУСКА ПРИ ПЕРВОМ ЗАПУСКЕ
        from strategy_menu import get_strategy_launch_method
        current_method = get_strategy_launch_method()
        log(f"Метод запуска стратегий: {current_method}", "INFO")
        
        self.start_in_tray = start_in_tray
        
        # Флаги для защиты от двойных вызовов
        self._splash_closed = False
        self._dpi_autostart_initiated = False
        self._heavy_init_started = False
        self._heavy_init_thread = None

        # ✅ FRAMELESS WINDOW - убираем стандартную рамку
        from PyQt6.QtCore import Qt
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowSystemMenuHint |
            Qt.WindowType.WindowMinMaxButtonsHint
        )
        # Включаем прозрачный фон для скругленных углов
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Инициализируем resize функционал
        self.init_frameless()

        # Устанавливаем основные параметры окна
        self.setWindowTitle(f"Zapret2 v{APP_VERSION} - загрузка...")

        # ✅ ДОБАВЛЕНО: Восстанавливаем сохраненную геометрию окна
        self.restore_window_geometry()
        
        # ✅ УСТАНАВЛИВАЕМ ПРАВИЛЬНЫЙ РАЗМЕР ОКНА (компактный)
        self.setMinimumSize(WIDTH, 400)  # Минимальная высота 400, ширина из конфига
        self.resize(WIDTH, HEIGHT)       # Стартовый размер
                
        # Устанавливаем иконку
        icon_path = ICON_TEST_PATH if CHANNEL == "test" else ICON_PATH
        self._app_icon = None
        if os.path.exists(icon_path):
            from PyQt6.QtGui import QIcon
            self._app_icon = QIcon(icon_path)
            self.setWindowIcon(self._app_icon)
            QApplication.instance().setWindowIcon(self._app_icon)
        
        from PyQt6.QtWidgets import QStackedWidget, QVBoxLayout, QFrame
        
        # ✅ ГЛАВНЫЙ КОНТЕЙНЕР со скругленными углами и полупрозрачным фоном (Windows 11 style)
        self.container = QFrame(self)
        self.container.setObjectName("mainContainer")
        self.container.setStyleSheet("""
            QFrame#mainContainer {
                background-color: rgba(32, 32, 32, 0.98);
                border-radius: 10px;
                border: 1px solid rgba(255, 255, 255, 0.08);
            }
        """)
        
        # Layout для контейнера
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)
        
        # ✅ КАСТОМНЫЙ TITLEBAR
        self.title_bar = CustomTitleBar(
            self, 
            title=f"Zapret2 v{APP_VERSION} - загрузка..."
        )
        if self._app_icon:
            self.title_bar.set_icon(self._app_icon)
        container_layout.addWidget(self.title_bar)
        
        # Создаем QStackedWidget для переключения между экранами
        self.stacked_widget = QStackedWidget()
        self.stacked_widget.setStyleSheet("background-color: transparent;")
        container_layout.addWidget(self.stacked_widget)
        
        # Главный layout окна
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.container)
        
        # Создаем загрузочный экран (с родителем!)
        self.splash = SplashScreen(self.stacked_widget)  # ✅ Родитель = stacked_widget
        self.splash.load_complete.connect(self._on_splash_complete)
        self.splash.setStyleSheet("background-color: transparent;")
        
        # Создаем основной виджет (с родителем чтобы не было отдельного окна!)
        self.main_widget = QWidget(self.stacked_widget)  # ✅ Родитель = stacked_widget
        self.main_widget.setStyleSheet("background-color: transparent;")
        # ✅ Только минимальная ширина, высота динамическая
        self.main_widget.setMinimumWidth(WIDTH)

        # ✅ НЕ СОЗДАЕМ theme_handler ЗДЕСЬ - создадим его после theme_manager

        # Добавляем оба виджета в stack
        self.splash_index = self.stacked_widget.addWidget(self.splash)
        self.main_index = self.stacked_widget.addWidget(self.main_widget)
        
        # Показываем загрузочный экран ТОЛЬКО если не в трее
        if not self.start_in_tray:
            self.stacked_widget.setCurrentIndex(self.splash_index)
        else:
            # Если в трее - сразу переключаемся на основной виджет
            self.stacked_widget.setCurrentIndex(self.main_index)
            # И запускаем инициализацию без splash
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(100, self._on_splash_complete)
        
        # Показываем окно ТОЛЬКО если НЕ в трее
        if not self.start_in_tray:
            self.show()  # ← Условный показ
            # ✅ Acrylic эффекты ОТКЛЮЧЕНЫ - вызывают лаги на Windows 11
        
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
        self.update_title_with_subscription_status(False, None, 0, source="init")
        
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

    # ═══════════════════════════════════════════════════════════════════════
    # FRAMELESS WINDOW: Обработчики событий мыши для изменения размера
    # ═══════════════════════════════════════════════════════════════════════
    
    def setWindowTitle(self, title: str):
        """Переопределяем setWindowTitle для обновления кастомного titlebar"""
        super().setWindowTitle(title)
        if hasattr(self, 'title_bar'):
            self.title_bar.set_title(title)
    
    def mousePressEvent(self, event):
        """Обработка нажатия мыши для изменения размера окна"""
        if self.handle_resize_mouse_press(event):
            return
        super().mousePressEvent(event)
        
    def mouseMoveEvent(self, event):
        """Обработка движения мыши для изменения размера окна"""
        if self.handle_resize_mouse_move(event):
            return
        # Обновляем курсор при движении над краями окна
        edge = self.get_resize_edge(event.pos())
        self.update_cursor_for_edge(edge)
        super().mouseMoveEvent(event)
        
    def mouseReleaseEvent(self, event):
        """Обработка отпускания мыши"""
        self.handle_resize_mouse_release(event)
        super().mouseReleaseEvent(event)

    def _apply_acrylic_effect(self):
        """
        ✅ ОТКЛЮЧЕНО: Acrylic/Blur эффекты вызывают лаги при перемещении окна на Windows 11.
        Используем простой непрозрачный фон для стабильной работы.
        """
        self._acrylic_enabled = False
        log("Acrylic эффекты отключены для стабильности", "INFO")

    def _build_main_ui(self) -> None:
        """Строит основной UI в main_widget"""
        # Временно меняем self на main_widget для build_ui
        old_layout = self.main_widget.layout()
        if old_layout is not None:
            while old_layout.count():
                item = old_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            # ✅ Удаляем layout напрямую (НЕ через QWidget() - это создаёт призрачное окно!)
            old_layout.deleteLater()
        
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
        
        # ✅ Пересчитываем размер окна под контент
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(50, self._adjust_window_size)
        
        # ✅ ВАЖНО: Повторно применяем тему РКН Тян если она выбрана
        if hasattr(self, 'theme_manager') and self.theme_manager.current_theme == "РКН Тян":
            log("Повторное применение темы РКН Тян после переключения виджетов", "DEBUG")
            QTimer.singleShot(200, lambda: self.theme_manager.apply_rkn_background())
        
        self.splash = None
    
    def _adjust_window_size(self) -> None:
        """Корректирует размер окна под значения из config.py"""
        try:
            from config import WIDTH, HEIGHT
            
            # Используем размеры из конфига
            self.resize(WIDTH, HEIGHT)
            log(f"Размер окна установлен из конфига: {WIDTH}x{HEIGHT}", "DEBUG")
        except Exception as e:
            log(f"Ошибка корректировки размера: {e}", "DEBUG")

    def _init_real_donate_checker(self) -> None:
        """Создает базовый DonateChecker (полная инициализация в SubscriptionManager)"""
        try:
            from donater import DonateChecker
            self.donate_checker = DonateChecker()
            log("Базовый DonateChecker создан", "DEBUG")
        except Exception as e:
            log(f"Ошибка создания DonateChecker: {e}", "❌ ERROR")

    def show_subscription_dialog(self) -> None:
        """Переключается на страницу Premium"""
        try:
            # Переключаемся на страницу Premium через sidebar
            if hasattr(self, 'side_nav'):
                # Индекс страницы Premium в sidebar
                # Главная(0), Управление(1), Стратегии(2), Hostlist(3), IPset(4), Настройки DPI(5),
                # Автозапуск(6), Сеть(7), Оформление(8), Premium(9), Логи(10), О программе(11)
                premium_index = 10
                self.side_nav.set_section(premium_index)
            
        except Exception as e:
            log(f"Ошибка при переходе на страницу Premium: {e}", level="❌ ERROR")
            self.set_status(f"Ошибка: {e}")
            
    def _show_server_status(self):
        """Показывает диалог статуса серверов и версий"""
        log("Открытие диалога статуса серверов...", "INFO")
        self.set_status("Загрузка информации о серверах...")
        
        try:
            from updater.server_status_dialog import ServerStatusDialog
            
            dialog = ServerStatusDialog(self)
            
            # Подключаем сигнал для запуска обновления из диалога
            dialog.update_requested.connect(self._on_update_check_from_dialog)
            
            # Показываем диалог
            dialog.exec()
            
            self.set_status("")
            
        except Exception as e:
            log(f"Ошибка открытия диалога статуса: {e}", "❌ ERROR")
            self.set_status(f"Ошибка: {e}")
            
            # Показываем простое сообщение об ошибке
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(
                self,
                "Ошибка",
                f"Не удалось открыть диалог статуса серверов:\n{e}"
            )

    def _on_update_check_from_dialog(self):
        """Обработчик запроса обновления из диалога статуса"""
        log("Запуск проверки обновлений из диалога статуса...", "INFO")
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
                
                def _update_done(ok: bool):
                    if ok:
                        self.set_status("🔄 Обновление запущено")
                    else:
                        self.set_status("✅ Проверка завершена")
                    
                    # ✅ ОБНОВЛЯЕМ КЭШ В UI ЕСЛИ ДИАЛОГ ЕЩЕ ОТКРЫТ
                    # (это для случая если пользователь снова откроет диалог)
                    
                    # Удаляем ссылки
                    if hasattr(self, '_manual_update_thread'):
                        del self._manual_update_thread
                
                worker.finished.connect(_update_done)
                
                # Блокируем кнопку на время проверки если она есть
                if hasattr(self, 'server_status_btn'):
                    self.server_status_btn.setEnabled(False)
                    worker.finished.connect(lambda: self.server_status_btn.setEnabled(True))
            
        except Exception as e:
            log(f"Ошибка при запуске проверки обновлений: {e}", "❌ ERROR")
            self.set_status(f"Ошибка проверки: {e}")
            
            # Разблокируем кнопку в случае ошибки
            if hasattr(self, 'server_status_btn'):
                self.server_status_btn.setEnabled(True)
                    
    def open_folder(self) -> None:
        """Opens the DPI folder."""
        try:
            run_hidden('explorer.exe .', shell=True)
        except Exception as e:
            self.set_status(f"Ошибка при открытии папки: {str(e)}")

    def show_autostart_options(self) -> None:
        """Переключается на страницу автозапуска в новом интерфейсе"""
        from strategy_menu import get_strategy_launch_method
        
        # Определяем режим запуска
        launch_method = get_strategy_launch_method()
        is_direct_mode = (launch_method == "direct")
        
        # Определяем название стратегии
        if is_direct_mode:
            from strategy_menu import get_direct_strategy_selections
            from strategy_menu.strategy_lists_separated import combine_strategies
            
            try:
                selections = get_direct_strategy_selections()
                combined = combine_strategies(**selections)
                strategy_name = combined['description']
            except:
                strategy_name = self.current_strategy_label.text()
                if strategy_name == "Автостарт DPI отключен":
                    strategy_name = get_last_strategy()
        else:
            strategy_name = self.current_strategy_label.text()
            if strategy_name == "Автостарт DPI отключен":
                strategy_name = get_last_strategy()
        
        log(f"Открытие страницы автозапуска (режим: {launch_method}, стратегия: {strategy_name})", "INFO")
        
        # ✅ Инициализируем страницу автозапуска
        self.init_autostart_page(
            app_instance=self,
            bat_folder=BAT_FOLDER,
            json_folder=INDEXJSON_FOLDER,
            strategy_name=strategy_name
        )
        
        # ✅ Обновляем статус на странице
        from autostart.registry_check import is_autostart_enabled
        is_enabled = is_autostart_enabled()
        self.autostart_page.update_status(is_enabled, strategy_name)
        
        # ✅ Переключаемся на страницу автозапуска
        self.show_autostart_page()

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
        """Переходит на страницу сетевых настроек"""
        try:
            # Переходим на страницу "Сеть" через sidebar
            if hasattr(self, 'sidebar') and hasattr(self, 'pages_stack'):
                # Индекс страницы "Сеть" = 4 (после Главная, Управление, Стратегии, Автозапуск)
                self.sidebar.set_current_index(4)
                self.pages_stack.setCurrentIndex(4)
                self.set_status("Настройки DNS")
                log("Переход на страницу сетевых настроек", "INFO")
            else:
                log("Sidebar или pages_stack не найден", "WARNING")
                
        except Exception as e:
            error_msg = f"Ошибка при открытии настроек DNS: {str(e)}"
            log(error_msg, level="❌ ERROR")
            self.set_status(error_msg)
            QMessageBox.critical(
                self, 
                "Ошибка DNS", 
                f"Не удалось открыть настройки DNS:\n{str(e)}"
            )

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

    # ✅ КРИТИЧЕСКИЕ ПРОВЕРКИ ДО СОЗДАНИЯ QApplication
    from startup.check_start import check_win10_tweaker, check_goodbyedpi, check_mitmproxy
    from startup.check_start import _native_message
    
    # Проверка Win 10 Tweaker
    has_tweaker, tweaker_msg = check_win10_tweaker()
    if has_tweaker:
        log("CRITICAL: Win 10 Tweaker обнаружен - прерываем запуск", "❌ CRITICAL")
        _native_message("Критическая ошибка", tweaker_msg, 0x10)
        sys.exit(1)
    
    # Проверка GoodbyeDPI
    has_gdpi, gdpi_msg = check_goodbyedpi()
    if has_gdpi:
        log("CRITICAL: GoodbyeDPI обнаружен - прерываем запуск", "❌ CRITICAL")
        _native_message("Критическая ошибка", gdpi_msg, 0x10)
        sys.exit(1)
    
    # Проверка mitmproxy
    has_mitmproxy, mitmproxy_msg = check_mitmproxy()
    if has_mitmproxy:
        log("CRITICAL: mitmproxy обнаружен - прерываем запуск", "❌ CRITICAL")
        _native_message("Критическая ошибка", mitmproxy_msg, 0x10)
        sys.exit(1)

    # ---------------- Создаём QApplication ----------------
    try:
        os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
        _set_attr_if_exists("AA_EnableHighDpiScaling")
        _set_attr_if_exists("AA_UseHighDpiPixmaps")

        app = QApplication(sys.argv)

        # ──────────────────────────────────────────────────────────────
        # Debug: log every top-level window that becomes visible
        # Helps to track mysterious blank window reported on Windows
        # ──────────────────────────────────────────────────────────────
        from PyQt6.QtCore import QObject, QEvent, QTimer

        class _ShowDebugFilter(QObject):
            def eventFilter(self, obj, event):
                try:
                    is_window = hasattr(obj, "isWindow") and obj.isWindow()
                except Exception:
                    is_window = False

                if event.type() == QEvent.Type.Show and is_window:
                    print(f"[DEBUG SHOW] {obj.__class__.__name__} title={obj.windowTitle()!r}")
                return False

        _show_debug_filter = _ShowDebugFilter()
        app.installEventFilter(_show_debug_filter)
        app.setQuitOnLastWindowClosed(False)
        
        # Устанавливаем Qt crash handler
        from log.crash_handler import install_qt_crash_handler
        install_qt_crash_handler(app)
        
        apply_initial_theme(app)
        
    except Exception as e:
        ctypes.windll.user32.MessageBoxW(None,
            f"Ошибка инициализации Qt: {e}", "Zapret", 0x10)

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

    # СОЗДАЁМ ОКНО
    window = LupiDPIApp(start_in_tray=start_in_tray)

    # ──────────────────────────────────────────────────────────────
    # Debug helper: dump all top-level windows shortly after start
    # Helps track mysterious blank window reported by users
    # ──────────────────────────────────────────────────────────────
    def _dump_top_level_windows():
        try:
            from PyQt6.QtWidgets import QApplication
            items = []
            for w in QApplication.topLevelWidgets():
                items.append(f"{w.__class__.__name__} :: title={w.windowTitle()!r} :: visible={w.isVisible()}")
            log("DEBUG TOP-LEVEL WINDOWS:\n" + "\n".join(items), "DEBUG")
        except Exception as debug_err:
            log(f"Failed to dump top-level windows: {debug_err}", "⚠ DEBUG")

    QTimer.singleShot(1500, _dump_top_level_windows)
    
    # ✅ ЗАПУСКАЕМ IPC СЕРВЕР
    ipc_manager = IPCManager()
    ipc_manager.start_server(window)
    atexit.register(ipc_manager.stop)

    if start_in_tray:
        log("Запуск приложения скрыто в трее", "TRAY")
        if hasattr(window, 'tray_manager'):
            window.tray_manager.show_notification(
                "Zapret работает в трее", 
                "Приложение запущено в фоновом режиме"
            )
                
    # ✅ НЕКРИТИЧЕСКИЕ ПРОВЕРКИ ПОСЛЕ ПОКАЗА ОКНА
    def async_startup_checks():
        """Выполняет некритические стартовые проверки асинхронно"""
        try:
            from startup.bfe_util import preload_service_status, ensure_bfe_running, cleanup as bfe_cleanup
            from startup.check_start import display_startup_warnings
            from startup.remove_terminal import remove_windows_terminal_if_win11
            from startup.admin_check_debug import debug_admin_status
            
            preload_service_status("BFE")
            
            if not ensure_bfe_running(show_ui=True):
                log("BFE не запущен, закрываем приложение", "❌ ERROR")
                window.close()
                QApplication.quit()
                return
            
            # ✅ ТОЛЬКО НЕКРИТИЧЕСКИЕ ПРОВЕРКИ (пути, команды, архив)
            warnings_ok = display_startup_warnings()
            if not warnings_ok and not start_in_tray:
                log("Некритические проверки не пройдены, закрываем приложение", "⚠ WARNING")
                window.close()
                QApplication.quit()
                return
            
            remove_windows_terminal_if_win11()
            debug_admin_status()
            set_batfile_association()
            
            atexit.register(bfe_cleanup)
            
            log("✅ Все проверки пройдены", "🔹 main")
            
        except Exception as e:
            log(f"Ошибка при асинхронных проверках: {e}", "❌ ERROR")
            if hasattr(window, 'set_status'):
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