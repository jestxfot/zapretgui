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
# ✅ УБРАНО: Очистка _MEI* папок больше не нужна
# Приложение собирается в режиме --onedir (папка с файлами)
# вместо --onefile, поэтому временные папки не создаются
# ──────────────────────────────────────────────────────────────

# ──────────────────────────────────────────────────────────────
# Устанавливаем глобальный обработчик крашей (ДО всех импортов!)
# ──────────────────────────────────────────────────────────────
from log.crash_handler import install_crash_handler
install_crash_handler()

# ──────────────────────────────────────────────────────────────
# Предзагрузка медленных модулей в фоне (ускоряет старт на ~300ms)
# ──────────────────────────────────────────────────────────────
def _preload_slow_modules():
    """Загружает медленные модули в фоновом потоке.
    
    Когда основной код дойдёт до импорта этих модулей,
    они уже будут в sys.modules - импорт будет мгновенным.
    """
    import threading
    
    def _preload():
        try:
            # Порядок важен! PyQt должен быть загружен до qt_material
            import PyQt6.QtWidgets  # ~17ms
            import PyQt6.QtCore
            import PyQt6.QtGui
            import jinja2            # ~1ms, но нужен qt_material
            import requests          # ~99ms
            import qtawesome         # ~115ms (нужен после PyQt)
            import qt_material       # ~90ms (нужен после PyQt)
            import psutil            # ~10ms
            import json              # для config и API
            import winreg            # для реестра Windows
        except Exception:
            pass  # Ошибки при предзагрузке не критичны
    
    t = threading.Thread(target=_preload, daemon=True)
    t.start()

_preload_slow_modules()

# ──────────────────────────────────────────────────────────────
# дальше можно импортировать всё остальное
# ──────────────────────────────────────────────────────────────
import subprocess, time

from PyQt6.QtCore    import QTimer, QEvent
from PyQt6.QtWidgets import QMessageBox, QWidget, QApplication

from ui.main_window import MainWindowUI
from ui.splash_screen import SplashScreen
from ui.custom_titlebar import CustomTitleBar, FramelessWindowMixin
from ui.garland_widget import GarlandWidget
from ui.snowflakes_widget import SnowflakesWidget

from startup.admin_check import is_admin

from config import ICON_PATH, ICON_TEST_PATH, WIDTH, HEIGHT, MIN_WIDTH
from config import get_last_strategy, set_last_strategy
from config import APP_VERSION
from utils import run_hidden

from ui.theme_subscription_manager import ThemeSubscriptionManager

# DNS настройки теперь интегрированы в network_page
from log import log

from config import CHANNEL
from ui.page_names import PageName, SectionName

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
    from managers.process_monitor_manager import ProcessMonitorManager
    from managers.subscription_manager import SubscriptionManager
    from managers.initialization_manager import InitializationManager

class LupiDPIApp(QWidget, MainWindowUI, ThemeSubscriptionManager, FramelessWindowMixin):
    """Главное окно приложения с поддержкой тем и подписок"""

    from ui.theme import ThemeHandler
    # ✅ ДОБАВЛЯЕМ TYPE HINTS для менеджеров
    ui_manager: 'UIManager'
    dpi_manager: 'DPIManager'
    process_monitor_manager: 'ProcessMonitorManager'
    subscription_manager: 'SubscriptionManager'
    initialization_manager: 'InitializationManager'
    theme_handler: 'ThemeHandler'

    def closeEvent(self, event):
        """Обрабатывает событие закрытия окна"""
        self._is_exiting = True
        
        # ✅ Гарантированно сохраняем геометрию/состояние окна при выходе
        try:
            self._persist_window_geometry_now(force=True)
        except Exception as e:
            log(f"Ошибка сохранения геометрии окна при закрытии: {e}", "❌ ERROR")
        
        # ✅ Очищаем менеджеры через их методы
        if hasattr(self, 'process_monitor_manager'):
            self.process_monitor_manager.stop_monitoring()
        
        # ✅ Очищаем DNS UI Manager
        if hasattr(self, 'dns_ui_manager'):
            self.dns_ui_manager.cleanup()
        
        # ✅ Очищаем Theme Manager
        if hasattr(self, 'theme_handler') and hasattr(self.theme_handler, 'theme_manager'):
            try:
                self.theme_handler.theme_manager.cleanup()
            except Exception as e:
                log(f"Ошибка при очистке theme_manager: {e}", "DEBUG")
        
        # ✅ Очищаем страницы с потоками
        try:
            if hasattr(self, 'logs_page') and hasattr(self.logs_page, 'cleanup'):
                self.logs_page.cleanup()
            if hasattr(self, 'servers_page') and hasattr(self.servers_page, 'cleanup'):
                self.servers_page.cleanup()
            if hasattr(self, 'connection_page') and hasattr(self.connection_page, 'cleanup'):
                self.connection_page.cleanup()
            if hasattr(self, 'dns_check_page') and hasattr(self.dns_check_page, 'cleanup'):
                self.dns_check_page.cleanup()
            if hasattr(self, 'hosts_page') and hasattr(self.hosts_page, 'cleanup'):
                self.hosts_page.cleanup()
        except Exception as e:
            log(f"Ошибка при очистке страниц: {e}", "DEBUG")
        
        # ✅ Очищаем потоки через контроллер
        if hasattr(self, 'dpi_controller'):
            self.dpi_controller.cleanup_threads()

        # ✅ ВАЖНО: winws/winws2 не должны останавливаться при "Выход" из трея/меню.
        # Останавливаем процессы только если явно запрошен "Выход и остановить DPI".
        if getattr(self, "_stop_dpi_on_exit", False):
            try:
                from utils.process_killer import kill_winws_force
                kill_winws_force()
                log("Процессы winws завершены при закрытии приложения (stop_dpi_on_exit=True)", "DEBUG")
            except Exception as e:
                log(f"Ошибка остановки winws при закрытии: {e}", "DEBUG")
        else:
            log("Выход без остановки DPI: winws не трогаем", "DEBUG")

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

    def _dismiss_transient_ui_safe(self, *, reason: str) -> None:
        """Безопасно закрывает попапы/tooltip-окна и сбрасывает grabs/cursor.

        На Windows "замирание" и артефакты часто вызваны зависшими Popup/ToolTip окнами
        (они могут оставаться поверх при сворачивании/переключении приложений).
        """
        if getattr(self, "_transient_ui_cleanup_in_progress", False):
            return
        self._transient_ui_cleanup_in_progress = True
        try:
            try:
                self._dismiss_transient_ui(reason=reason)
            except Exception:
                pass
        finally:
            self._transient_ui_cleanup_in_progress = False

    def _snapshot_interaction_state_for_debug(self) -> dict:
        """Срез состояния UI (для диагностики залипаний hover/cursor)."""
        state: dict = {}
        try:
            from PyQt6.QtCore import Qt
            from PyQt6.QtWidgets import QApplication, QWidget

            def _enum_to_int(value):
                try:
                    return int(value)
                except Exception:
                    try:
                        return int(value.value)
                    except Exception:
                        return str(value)

            def _get_mouse_grabber(app_):
                for obj in (app_, QApplication, QWidget):
                    try:
                        return obj.mouseGrabber()  # type: ignore[attr-defined]
                    except Exception:
                        continue
                return None

            def _get_keyboard_grabber(app_):
                for obj in (app_, QApplication, QWidget):
                    try:
                        return obj.keyboardGrabber()  # type: ignore[attr-defined]
                    except Exception:
                        continue
                return None

            app = QApplication.instance()
            if not app:
                return state

            try:
                oc = QApplication.overrideCursor()
                state["overrideCursor"] = _enum_to_int(oc.shape()) if oc is not None else None
            except Exception:
                state["overrideCursor"] = "err"

            try:
                state["mouseButtons"] = _enum_to_int(QApplication.mouseButtons())
            except Exception:
                state["mouseButtons"] = "err"

            try:
                mg = _get_mouse_grabber(app)
                state["mouseGrabber"] = mg.__class__.__name__ if mg is not None else None
            except Exception:
                state["mouseGrabber"] = "err"

            try:
                kg = _get_keyboard_grabber(app)
                state["keyboardGrabber"] = kg.__class__.__name__ if kg is not None else None
            except Exception:
                state["keyboardGrabber"] = "err"

            try:
                ap = app.activePopupWidget()
                state["activePopupWidget"] = ap.__class__.__name__ if ap is not None else None
            except Exception:
                state["activePopupWidget"] = "err"

            try:
                state["windowCursorShape"] = _enum_to_int(self.cursor().shape())
            except Exception:
                state["windowCursorShape"] = "err"

            try:
                state["windowHasCursor"] = bool(self.testAttribute(Qt.WidgetAttribute.WA_SetCursor))
            except Exception:
                state["windowHasCursor"] = "err"

            try:
                state["isResizing"] = bool(getattr(self, "_is_resizing", False))
                state["resizeEdge"] = getattr(self, "_resize_edge", None)
            except Exception:
                state["isResizing"] = "err"
                state["resizeEdge"] = "err"

            try:
                state["isDragging"] = bool(getattr(self, "_is_dragging", False))
            except Exception:
                state["isDragging"] = "err"

            try:
                tb = getattr(self, "title_bar", None)
                if tb is not None:
                    state["titlebarMoving"] = bool(getattr(tb, "_is_moving", False))
                    state["titlebarSystemMoving"] = bool(getattr(tb, "_is_system_moving", False))
            except Exception:
                state["titlebarMoving"] = "err"
                state["titlebarSystemMoving"] = "err"
        except Exception:
            return state

        return state

    def _force_release_interaction_states(self, *, reason: str) -> None:
        """Сбрасывает состояния drag/resize/cursor, которые могут залипать при потере фокуса."""
        cancelled: list[str] = []
        need_win_cancelmode = False

        aggressive_win_cancelmode = reason.startswith("deactivate:") or reason.startswith("app_state_inactive")

        # Cancel frameless resize if focus changed mid-resize.
        try:
            if bool(getattr(self, "_is_resizing", False)) and hasattr(self, "_end_resize"):
                self._end_resize()
                cancelled.append("resize")
                need_win_cancelmode = True
        except Exception:
            pass

        # Cancel window dragging if focus changed mid-drag.
        try:
            if bool(getattr(self, "_is_dragging", False)):
                self._is_dragging = False
                self._drag_start_pos = None
                self._drag_window_pos = None
                cancelled.append("drag_window")
                need_win_cancelmode = True
        except Exception:
            pass

        # Cancel titlebar move flags (can stick if mouse released outside app).
        try:
            tb = getattr(self, "title_bar", None)
            if tb is not None:
                was_moving = bool(getattr(tb, "_is_moving", False) or getattr(tb, "_is_system_moving", False))
                if was_moving:
                    tb._is_moving = False
                    tb._is_system_moving = False
                    tb._drag_pos = None
                    tb._window_pos = None
                    cancelled.append("titlebar_move")
                    need_win_cancelmode = True
        except Exception:
            pass

        # Clear stuck override cursor stack (e.g. WaitCursor/PointingHandCursor).
        try:
            from PyQt6.QtWidgets import QApplication

            if QApplication.overrideCursor() is not None:
                cancelled.append("overrideCursor")
                need_win_cancelmode = True
            while QApplication.overrideCursor() is not None:
                QApplication.restoreOverrideCursor()
        except Exception:
            pass

        # Release mouse/keyboard grabs if something grabbed input.
        try:
            from PyQt6.QtWidgets import QApplication, QWidget

            app = QApplication.instance()
            if app is not None:
                mg = None
                for obj in (app, QApplication, QWidget):
                    try:
                        mg = obj.mouseGrabber()  # type: ignore[attr-defined]
                        break
                    except Exception:
                        continue
                if mg is not None:
                    try:
                        mg.releaseMouse()
                        cancelled.append(f"mouseGrabber:{mg.__class__.__name__}")
                        need_win_cancelmode = True
                    except Exception:
                        pass

                kg = None
                for obj in (app, QApplication, QWidget):
                    try:
                        kg = obj.keyboardGrabber()  # type: ignore[attr-defined]
                        break
                    except Exception:
                        continue
                if kg is not None:
                    try:
                        kg.releaseKeyboard()
                        cancelled.append(f"keyboardGrabber:{kg.__class__.__name__}")
                        need_win_cancelmode = True
                    except Exception:
                        pass
        except Exception:
            pass

        # Clear window-level cursor that can remain set after interrupted resize.
        try:
            from PyQt6.QtCore import Qt

            had_window_cursor = bool(self.testAttribute(Qt.WidgetAttribute.WA_SetCursor))
            self.unsetCursor()
            if had_window_cursor:
                cancelled.append("windowCursor")
        except Exception:
            pass

        # Windows: cancel stuck capture / native modal loops (system move/resize).
        try:
            if sys.platform.startswith("win"):
                import ctypes

                try:
                    ctypes.windll.user32.ReleaseCapture()
                except Exception:
                    pass

                try:
                    if aggressive_win_cancelmode or need_win_cancelmode:
                        hwnd = int(self.winId())
                        WM_CANCELMODE = 0x001F
                        ctypes.windll.user32.SendMessageW(hwnd, WM_CANCELMODE, 0, 0)
                        cancelled.append("win_cancelmode")
                except Exception:
                    pass
        except Exception:
            pass

        if cancelled:
            try:
                log(f"Force-released interaction states ({reason}): {', '.join(cancelled)}", "DEBUG")
            except Exception:
                pass

    def hideEvent(self, event):  # noqa: N802 (Qt override)
        try:
            self._dismiss_transient_ui_safe(reason="main_window_hide")
        except Exception:
            pass
        super().hideEvent(event)

    def event(self, event):  # noqa: N802 (Qt override)
        try:
            et = event.type()
            if et == QEvent.Type.WindowDeactivate:
                # Не ломаем нормальные Qt popups (QMenu/QComboBox/меню трея): они могут
                # деактивировать главное окно, но приложение остаётся активным.
                try:
                    app = QApplication.instance()
                    if app and app.activePopupWidget() is not None:
                        return super().event(event)
                except Exception:
                    pass

                try:
                    snap = self._snapshot_interaction_state_for_debug()
                    log(f"Focus change: window_deactivate ({et}) snap={snap}", "DEBUG")
                except Exception:
                    pass

                self._dismiss_transient_ui_safe(reason=f"main_window_deactivate:{et}")
                self._force_release_interaction_states(reason=f"deactivate:{et}")

            elif et == QEvent.Type.ApplicationDeactivate:
                try:
                    snap = self._snapshot_interaction_state_for_debug()
                    log(f"Focus change: app_deactivate ({et}) snap={snap}", "DEBUG")
                except Exception:
                    pass

                self._dismiss_transient_ui_safe(reason=f"app_deactivate:{et}")
                self._force_release_interaction_states(reason=f"deactivate:{et}")

            elif et in (QEvent.Type.WindowActivate, QEvent.Type.ApplicationActivate):
                try:
                    snap = self._snapshot_interaction_state_for_debug()
                    log(f"Focus change: activate ({et}) snap={snap}", "DEBUG")
                except Exception:
                    pass

                # Не закрываем попапы при активации — только сброс input-состояний.
                self._force_release_interaction_states(reason=f"activate:{et}")

            elif et == QEvent.Type.ActivationChange:
                # ActivationChange может происходить при открытии QMenu/QComboBox.
                # Не вмешиваемся, если видим активный popup.
                try:
                    app = QApplication.instance()
                    if app and app.activePopupWidget() is not None:
                        return super().event(event)
                except Exception:
                    pass

                try:
                    snap = self._snapshot_interaction_state_for_debug()
                    log("Focus change: activation_change snap=%s" % (snap,), "DEBUG")
                except Exception:
                    pass

                self._force_release_interaction_states(reason="activation_change")
        except Exception:
            pass
        return super().event(event)

    def request_exit(self, stop_dpi: bool) -> None:
        """Единая точка выхода из приложения.

        - stop_dpi=False: закрыть GUI, DPI оставить работать.
        - stop_dpi=True: остановить DPI и выйти (учитывает текущий launch_method).
        """
        from PyQt6.QtWidgets import QApplication

        self._stop_dpi_on_exit = bool(stop_dpi)

        # Разрешаем закрытие (иначе треевый перехватчик свернёт окно в трей).
        self._allow_close = True
        self._closing_completely = True

        # Сохраняем геометрию/состояние окна сразу (без debounce).
        try:
            self._persist_window_geometry_now(force=True)
        except Exception as e:
            log(f"Ошибка сохранения геометрии окна при request_exit: {e}", "DEBUG")

        # Скрываем иконку трея (если есть) — пользователь выбрал полный выход.
        try:
            if hasattr(self, "tray_manager") and self.tray_manager:
                self.tray_manager.tray_icon.hide()
        except Exception:
            pass

        if stop_dpi:
            log("Запрошен выход: остановить DPI и выйти", "INFO")

            # Предпочтительно: асинхронная остановка + выход.
            try:
                if hasattr(self, "dpi_controller") and self.dpi_controller:
                    self.dpi_controller.stop_and_exit_async()
                    return
            except Exception as e:
                log(f"stop_and_exit_async не удалось: {e}", "WARNING")

            # Fallback: синхронная остановка.
            try:
                from dpi.stop import stop_dpi
                stop_dpi(self)
            except Exception as e:
                log(f"Ошибка остановки DPI перед выходом: {e}", "WARNING")

        else:
            log("Запрошен выход: выйти без остановки DPI", "INFO")

        QApplication.quit()

    def restore_window_geometry(self):
        """Восстанавливает сохраненную позицию и размер окна"""
        self._geometry_restore_in_progress = True
        try:
            from config import get_window_position, get_window_size, get_window_maximized, WIDTH, HEIGHT

            min_width = MIN_WIDTH
            min_height = 400

            # Размер
            saved_size = get_window_size()
            if saved_size:
                width, height = saved_size
                if width >= min_width and height >= min_height:
                    self.resize(width, height)
                    log(f"Восстановлен размер окна: {width}x{height}", "DEBUG")
                else:
                    log(f"Сохраненный размер слишком мал ({width}x{height}), используем по умолчанию", "DEBUG")
                    self.resize(WIDTH, HEIGHT)
            else:
                self.resize(WIDTH, HEIGHT)

            # Позиция
            saved_pos = get_window_position()
            screen_geometry = QApplication.primaryScreen().availableGeometry()
            screens = QApplication.screens()

            if saved_pos:
                x, y = saved_pos

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
                    self.move(
                        screen_geometry.center().x() - self.width() // 2,
                        screen_geometry.center().y() - self.height() // 2
                    )
                    log("Сохраненная позиция за пределами экранов, окно отцентрировано", "WARNING")
            else:
                self.move(
                    screen_geometry.center().x() - self.width() // 2,
                    screen_geometry.center().y() - self.height() // 2
                )
                log("Позиция не сохранена, окно отцентрировано", "DEBUG")

            # Сохраняем нормальную геометрию (для корректного закрытия из maximized)
            self._last_normal_geometry = (int(self.x()), int(self.y()), int(self.width()), int(self.height()))

            # Maximized будем применять при первом showEvent (особенно важно для start_in_tray/splash)
            saved_maximized = get_window_maximized()
            self._pending_restore_maximized = bool(saved_maximized)

        except Exception as e:
            log(f"Ошибка восстановления геометрии окна: {e}", "❌ ERROR")
            from config import WIDTH, HEIGHT
            self.resize(WIDTH, HEIGHT)
        finally:
            self._geometry_restore_in_progress = False

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

    def on_strategy_selected_from_dialog(self, strategy_id: str, strategy_name: str) -> None:
        """Обрабатывает выбор стратегии из диалога."""
        try:
            log(f"Выбрана стратегия: {strategy_name} (ID: {strategy_id})", level="INFO")
            
            # Сохраняем ID и имя выбранной стратегии в атрибутах класса
            self.current_strategy_id = strategy_id
            self.current_strategy_name = strategy_name
            
            # ДЛЯ DIRECT РЕЖИМА ИСПОЛЬЗУЕМ ПРОСТОЕ НАЗВАНИЕ
            from strategy_menu import get_strategy_launch_method
            launch_method = get_strategy_launch_method()
            
            if launch_method == "direct_zapret2":
                # direct_zapret2 is preset-based; do not show a phantom single-strategy name.
                try:
                    from preset_zapret2 import get_active_preset_name
                    preset_name = get_active_preset_name() or "Default"
                    display_name = f"Пресет: {preset_name}"
                except Exception:
                    display_name = "Пресет"
                self.current_strategy_name = display_name
                strategy_name = display_name
                log(f"Установлено имя пресета для direct_zapret2: {display_name}", "DEBUG")
            elif strategy_id == "DIRECT_MODE" or launch_method in ("direct_zapret2_orchestra", "direct_zapret1"):
                if launch_method == "direct_zapret2_orchestra":
                    display_name = "Оркестратор Z2"
                else:
                    display_name = "Прямой Z1"
                self.current_strategy_name = display_name
                strategy_name = display_name
                log(f"Установлено простое название для режима {launch_method}: {display_name}", "DEBUG")
            else:
                # Для BAT режима сохраняем последнюю стратегию
                from config.reg import set_last_bat_strategy
                set_last_bat_strategy(strategy_name)
            
            # Обновляем новые страницы интерфейса
            if hasattr(self, 'update_current_strategy_display'):
                self.update_current_strategy_display(strategy_name)

            # Записываем время изменения стратегии
            self.last_strategy_change_time = time.time()
            
            # ✅ ИСПРАВЛЕННАЯ ЛОГИКА для обработки Direct режимов
            if launch_method in ("direct_zapret2", "direct_zapret2_orchestra", "direct_zapret1"):
                if strategy_id == "DIRECT_MODE" or strategy_id == "combined":
                    
                    # ✅ ДЛЯ direct_zapret2 - ИСПОЛЬЗУЕМ PRESET ФАЙЛ
                    if launch_method == "direct_zapret2":
                        from preset_zapret2 import get_active_preset_path, get_active_preset_name, ensure_default_preset_exists

                        # Создаем файл если не существует (первый запуск)
                        ensure_default_preset_exists()

                        preset_path = get_active_preset_path()
                        preset_name = get_active_preset_name() or "Default"

                        # Проверяем что файл не пустой и содержит фильтры
                        try:
                            content = preset_path.read_text(encoding='utf-8').strip()
                            has_filters = any(f in content for f in ['--wf-tcp-out', '--wf-udp-out', '--wf-raw-part'])
                            if not has_filters:
                                log("Preset файл не содержит активных фильтров", "WARNING")
                                self.set_status("Выберите хотя бы одну категорию для запуска")
                                return
                        except Exception as e:
                            log(f"Ошибка чтения preset файла: {e}", "ERROR")
                            self.set_status(f"Ошибка чтения preset: {e}")
                            return

                        # ✅ ИСПОЛЬЗУЕМ СУЩЕСТВУЮЩИЙ ФАЙЛ БЕЗ ИЗМЕНЕНИЙ!
                        combined_data = {
                            'is_preset_file': True,
                            'name': f"Пресет: {preset_name}",
                            'preset_path': str(preset_path)
                        }

                        log(f"Запуск из preset файла: {preset_path}", "INFO")
                        self.dpi_controller.start_dpi_async(selected_mode=combined_data, launch_method=launch_method)
                    
                    # ✅ ДЛЯ ДРУГИХ РЕЖИМОВ - используем combine_strategies
                    else:
                        from launcher_common import combine_strategies
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
                        
                        self.dpi_controller.start_dpi_async(selected_mode=combined_data, launch_method=launch_method)
                        
                else:
                    self.dpi_controller.start_dpi_async(selected_mode=(strategy_id, strategy_name), launch_method=launch_method)
            else:
                # BAT режим
                try:
                    strategies = self.strategy_manager.get_strategies_list()
                    strategy_info = strategies.get(strategy_id, {})
                    
                    if not strategy_info:
                        strategy_info = {
                            'name': strategy_name,
                            'file_path': f"{strategy_id}.bat"
                        }
                        log(f"Не удалось найти информацию о стратегии {strategy_id}, используем базовую", "⚠ WARNING")
                    
                    self.dpi_controller.start_dpi_async(selected_mode=strategy_info, launch_method=launch_method)
                    
                except Exception as strategy_error:
                    log(f"Ошибка при получении информации о стратегии: {strategy_error}", "❌ ERROR")
                    self.dpi_controller.start_dpi_async(selected_mode=strategy_name, launch_method=launch_method)
                
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
        self._is_exiting = False
        self._stop_dpi_on_exit = False  # True только для "Выход и остановить DPI"

        # ✅ Современное сохранение/восстановление геометрии окна (debounce)
        self._geometry_restore_in_progress = False
        self._geometry_persistence_enabled = False
        self._pending_restore_maximized = False
        self._applied_saved_maximize_state = False
        self._last_normal_geometry = None  # (x, y, w, h) для normal state
        self._last_persisted_geometry = None
        self._last_persisted_maximized = None

        self._geometry_save_timer = QTimer(self)
        self._geometry_save_timer.setSingleShot(True)
        self._geometry_save_timer.setInterval(450)
        self._geometry_save_timer.timeout.connect(self._persist_window_geometry_now)

        # ✅ FRAMELESS WINDOW - убираем стандартную рамку
        from PyQt6.QtCore import Qt
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowSystemMenuHint |
            Qt.WindowType.WindowMinMaxButtonsHint
        )
        # Включаем прозрачный фон для скругленных углов
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Устанавливаем основные параметры окна
        self.setWindowTitle(f"Zapret2 v{APP_VERSION} - загрузка...")

        # ✅ УСТАНАВЛИВАЕМ ПРАВИЛЬНЫЙ МИНИМАЛЬНЫЙ РАЗМЕР ОКНА (компактный)
        self.setMinimumSize(MIN_WIDTH, 400)

        # ✅ Восстанавливаем сохраненную геометрию окна (размер/позиция/развернутость)
        self.restore_window_geometry()
                
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
        # ⚠️ НЕ применяем inline стили - они будут из темы QApplication

        # Инициализируем функционал безрамочного resize
        # Важно: делаем resize-оверлеи дочерними контейнера, иначе "прозрачные" оверлеи
        # могут давать визуальные щели по краям (особенно при WA_TranslucentBackground).
        self.init_frameless(resize_target=self.container)
        
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
        
        # ✅ НОВОГОДНЯЯ ГИРЛЯНДА (Premium) - поверх всего контента
        self.garland = GarlandWidget(self.container)
        self.garland.setGeometry(0, 32, self.container.width(), self.garland.maximumHeight())  # Под title bar
        self.garland.raise_()  # Поверх всех виджетов
        
        # ✅ СНЕЖИНКИ (Premium) - поверх всего окна (как "живой" фон)
        # Важно: делаем оверлеем, иначе их может перекрывать viewport QScrollArea/QAbstractScrollArea.
        self.snowflakes = SnowflakesWidget(self)
        self.snowflakes.raise_()

        # Обновляем зоны resize после создания titlebar,
        # иначе верхний правый угол будет рассчитан без учёта кнопок
        self._update_resize_handles()
        
        # Создаем QStackedWidget для переключения между экранами
        self.stacked_widget = QStackedWidget()
        # ⚠️ НЕ применяем inline стили - они будут из темы QApplication
        container_layout.addWidget(self.stacked_widget)
        
        # Главный layout окна
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.container)
        
        # Создаем основной виджет (с родителем чтобы не было отдельного окна!)
        self.main_widget = QWidget(self.stacked_widget)  # ✅ Родитель = stacked_widget
        # ⚠️ НЕ применяем inline стили - они будут из темы QApplication
        # ✅ Только минимальная ширина, высота динамическая
        self.main_widget.setMinimumWidth(MIN_WIDTH)

        # ✅ НЕ СОЗДАЕМ theme_handler ЗДЕСЬ - создадим его после theme_manager

        # Добавляем main_widget в stack
        self.main_index = self.stacked_widget.addWidget(self.main_widget)
        self.stacked_widget.setCurrentIndex(self.main_index)
        
        # ✅ ВОЗВРАЩАЕМ SPLASH но главное окно НЕ показываем пока CSS не готов
        self._css_applied_at_startup = False
        self._startup_theme = None
        
        if not self.start_in_tray:
            # Создаём splash
            self.splash = SplashScreen(parent=self)
            self.splash.load_complete.connect(self._on_splash_complete)
            self.splash.show()
            
            QApplication.processEvents()
            
            self.splash.set_progress(5, "Запуск Zapret...", "Подготовка")
            QApplication.processEvents()
            
            # Главное окно НЕ показываем - оно создано но скрыто
            # Splash анимируется, а главное окно ждёт применения CSS
            log("Splash показан, главное окно скрыто", "DEBUG")
        else:
            # Если в трее - без splash
            self.splash = None
            self._css_applied_at_startup = False

        # ✅ Пытаемся применить CSS из кеша ДО построения основного UI.
        # Это резко снижает стоимость QApplication.setStyleSheet(),
        # потому что виджетов ещё мало.
        self._apply_cached_css_at_startup()

        # Splash больше не используется - окно показывается сразу
        
        # Инициализируем атрибуты
        self.process_monitor = None
        self.first_start = True
        self.current_strategy_id = None
        self.current_strategy_name = None
        
        # Теперь строим UI в main_widget (не в self)
        self._build_main_ui()
        
        # Обновляем прогресс splash
        if self.splash:
            self.splash.set_progress(35, "Создание интерфейса...", "")
        
        # Создаем менеджеры
        from managers.initialization_manager import InitializationManager
        from managers.subscription_manager import SubscriptionManager
        from managers.process_monitor_manager import ProcessMonitorManager
        from managers.ui_manager import UIManager
        from managers.dpi_manager import DPIManager

        self.initialization_manager = InitializationManager(self)
        self.subscription_manager = SubscriptionManager(self)
        self.process_monitor_manager = ProcessMonitorManager(self)
        self.ui_manager = UIManager(self)
        self.dpi_manager = DPIManager(self)
        
        # Обновляем прогресс splash
        if self.splash:
            self.splash.set_progress(50, "Проверка подписки...", "")

        # Инициализируем donate checker
        self._init_real_donate_checker()  # Упрощенная версия
        self.update_title_with_subscription_status(False, None, 0, source="init")
        
        # Запускаем асинхронную инициализацию через менеджер
        QTimer.singleShot(50, self.initialization_manager.run_async_init)
        QTimer.singleShot(1000, self.subscription_manager.initialize_async)
        # Гирлянда инициализируется автоматически в subscription_manager после проверки подписки

    def init_theme_handler(self):
        """Инициализирует theme_handler после создания theme_manager"""
        if not hasattr(self, 'theme_handler'):
            from ui.theme import ThemeHandler
            self.theme_handler = ThemeHandler(self, target_widget=self.main_widget)
            
            # Если theme_manager уже создан, устанавливаем его
            if hasattr(self, 'theme_manager'):
                self.theme_handler.set_theme_manager(self.theme_manager)
                
            log("ThemeHandler инициализирован", "DEBUG")

    def _apply_cached_css_at_startup(self) -> None:
        """Быстро применяет CSS из кеша на старте (если доступен)."""
        try:
            from PyQt6.QtWidgets import QApplication
            from PyQt6.QtGui import QPalette
            import time as _time

            app = QApplication.instance()
            if app is None:
                return

            # Импортируем лениво: большой модуль, но нужен только на старте.
            from ui.theme import THEMES, get_selected_theme, load_cached_css_sync

            selected = get_selected_theme("Темная синяя") or "Темная синяя"
            if selected not in THEMES:
                selected = "Темная синяя"

            # Премиум темы не применяем до проверки подписки (поведение ThemeManager).
            info = THEMES.get(selected, {})
            is_premium_theme = (
                selected in ("РКН Тян", "РКН Тян 2", "Полностью черная")
                or selected.startswith("AMOLED")
                or info.get("amoled", False)
                or info.get("pure_black", False)
            )
            theme_to_apply = "Темная синяя" if is_premium_theme else selected

            css = load_cached_css_sync(theme_to_apply)
            if not css:
                return

            t0 = _time.perf_counter()
            app.setStyleSheet(css)
            # Сбрасываем палитру чтобы стили гарантированно применились
            self.setPalette(QPalette())
            elapsed_ms = (_time.perf_counter() - t0) * 1000

            self._css_applied_at_startup = True
            self._startup_theme = theme_to_apply
            self._startup_css_hash = hash(css)

            log(f"🎨 Startup CSS applied from cache: {elapsed_ms:.0f}ms (theme='{theme_to_apply}')", "DEBUG")

        except Exception as e:
            log(f"Ошибка применения CSS из кеша при старте: {e}", "DEBUG")

    # ═══════════════════════════════════════════════════════════════════════
    # FRAMELESS WINDOW: Обработчики событий мыши для изменения размера
    # ═══════════════════════════════════════════════════════════════════════
    
    def setWindowTitle(self, title: str):
        """Переопределяем setWindowTitle для обновления кастомного titlebar"""
        super().setWindowTitle(title)
        if hasattr(self, 'title_bar'):
            self.title_bar.set_title(title)

    def _enable_geometry_persistence(self) -> None:
        if getattr(self, "_geometry_persistence_enabled", False):
            return
        self._geometry_persistence_enabled = True

    def _schedule_window_geometry_save(self) -> None:
        if not getattr(self, "_geometry_persistence_enabled", False):
            return
        if getattr(self, "_geometry_restore_in_progress", False):
            return
        if getattr(self, "_is_exiting", False):
            return

        try:
            if self.isMinimized():
                return
        except Exception:
            return

        try:
            if hasattr(self, "_geometry_save_timer") and self._geometry_save_timer is not None:
                self._geometry_save_timer.start()
        except Exception:
            pass

    def _on_window_geometry_changed(self) -> None:
        if getattr(self, "_geometry_restore_in_progress", False):
            return

        try:
            if self.isMinimized() or self.isMaximized():
                return
        except Exception:
            return

        self._last_normal_geometry = (int(self.x()), int(self.y()), int(self.width()), int(self.height()))
        self._schedule_window_geometry_save()

    def _get_normal_geometry_to_save(self, is_maximized: bool):
        if not is_maximized:
            return (int(self.x()), int(self.y()), int(self.width()), int(self.height()))

        # Если окно maximized — сохраняем "normal" геометрию, чтобы корректно восстановить при следующем запуске.
        try:
            normal_geo = self.normalGeometry()
            w = int(normal_geo.width())
            h = int(normal_geo.height())
            if w > 0 and h > 0:
                return (int(normal_geo.x()), int(normal_geo.y()), w, h)
        except Exception:
            pass

        if self._last_normal_geometry:
            return self._last_normal_geometry

        return None

    def _persist_window_geometry_now(self, force: bool = False) -> None:
        if not force:
            if not getattr(self, "_geometry_persistence_enabled", False):
                return
            if getattr(self, "_geometry_restore_in_progress", False):
                return
            if getattr(self, "_is_exiting", False):
                return

        try:
            if self.isMinimized():
                return
        except Exception:
            pass

        try:
            from config import set_window_position, set_window_size, set_window_maximized

            is_maximized = False
            try:
                is_maximized = bool(self.isMaximized())
            except Exception:
                is_maximized = False

            if force or self._last_persisted_maximized != is_maximized:
                set_window_maximized(is_maximized)
                self._last_persisted_maximized = is_maximized

            geometry = self._get_normal_geometry_to_save(is_maximized)
            if geometry is None:
                return

            x, y, w, h = geometry
            w = max(int(w), MIN_WIDTH)
            h = max(int(h), 400)
            geometry = (int(x), int(y), int(w), int(h))

            if force or self._last_persisted_geometry != geometry:
                set_window_position(geometry[0], geometry[1])
                set_window_size(geometry[2], geometry[3])
                self._last_persisted_geometry = geometry

        except Exception as e:
            log(f"Ошибка сохранения геометрии окна: {e}", "DEBUG")

    def _apply_saved_maximized_state_if_needed(self) -> None:
        if getattr(self, "_applied_saved_maximize_state", False):
            return

        self._applied_saved_maximize_state = True

        if getattr(self, "_pending_restore_maximized", False):
            try:
                if not self.isMaximized():
                    self._geometry_restore_in_progress = True
                    self.showMaximized()
            except Exception:
                pass
            finally:
                self._geometry_restore_in_progress = False

    def changeEvent(self, event):
        if event.type() == QEvent.Type.WindowStateChange:
            is_maximized = self.isMaximized()

            if hasattr(self, "_was_maximized"):
                self._was_maximized = is_maximized

            if hasattr(self, "_update_border_radius"):
                self._update_border_radius(not is_maximized)

            if hasattr(self, "_set_handles_visible"):
                self._set_handles_visible(not is_maximized)

            if hasattr(self, "title_bar") and hasattr(self.title_bar, "maximize_btn"):
                self.title_bar.maximize_btn.set_maximized(is_maximized)

            # Persist maximized state immediately (размер/позиция — по debounce)
            try:
                from config import set_window_maximized
                if self._last_persisted_maximized != bool(is_maximized):
                    set_window_maximized(bool(is_maximized))
                    self._last_persisted_maximized = bool(is_maximized)
            except Exception:
                pass

        super().changeEvent(event)

    def moveEvent(self, event):
        super().moveEvent(event)
        self._on_window_geometry_changed()
    
    def mousePressEvent(self, event):
        """Обработка нажатия мыши"""
        super().mousePressEvent(event)
        
    def mouseMoveEvent(self, event):
        """Обработка движения мыши"""
        super().mouseMoveEvent(event)
        
    def mouseReleaseEvent(self, event):
        """Обработка отпускания мыши"""
        super().mouseReleaseEvent(event)

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
        
        # ⚠️ НЕ применяем inline стили к main_widget - они будут из темы QApplication
        
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
        """Обработчик завершения splash - показываем главное окно"""
        if self._splash_closed:
            log("Splash уже закрыт, пропускаем", "DEBUG")
            return
        
        self._splash_closed = True
        log("Splash завершён, показываем главное окно", "DEBUG")
        
        # Показываем главное окно
        if not self.start_in_tray and not self.isVisible():
            self.show()
            log("Основное окно показано", "DEBUG")
        
        # Принудительно обновляем стили
        QTimer.singleShot(10, self._force_style_refresh)
        
        # Проверяем РКН Тян темы
        if hasattr(self, 'theme_manager'):
            current_theme = self.theme_manager.current_theme
            if current_theme == "РКН Тян":
                QTimer.singleShot(200, lambda: self.theme_manager.apply_rkn_background())
            elif current_theme == "РКН Тян 2":
                QTimer.singleShot(200, lambda: self.theme_manager.apply_rkn2_background())
        
        self.splash = None
    
    def _apply_deferred_css_if_needed(self) -> None:
        """Применяет отложенный полный CSS (вызывается через 300ms после показа окна)"""
        log(f"🎨 _apply_deferred_css_if_needed вызван, has_deferred={hasattr(self, '_deferred_css')}", "DEBUG")
        
        if not hasattr(self, '_deferred_css'):
            return
            
        log("🎨 Применяем полный CSS (300ms после показа окна)", "DEBUG")
        try:
            import time as _time
            _t = _time.perf_counter()
            
            QApplication.instance().setStyleSheet(self._deferred_css)
            self.setStyleSheet(self._deferred_css)
            
            from PyQt6.QtGui import QPalette
            self.setPalette(QPalette())
            
            elapsed_ms = (_time.perf_counter()-_t)*1000
            log(f"  setStyleSheet took {elapsed_ms:.0f}ms (полный CSS)", "DEBUG")
            
            # Обновляем theme_manager
            if hasattr(self, 'theme_manager'):
                self.theme_manager._current_css_hash = hash(self.styleSheet())
                self.theme_manager._theme_applied = True
                self.theme_manager.current_theme = getattr(self, '_deferred_theme_name', self.theme_manager.current_theme)
                
                if getattr(self, '_deferred_persist', False):
                    from ui.theme import set_selected_theme
                    set_selected_theme(self.theme_manager.current_theme)
            
            # Принудительно обновляем стили виджетов
            QTimer.singleShot(10, self._force_style_refresh)
            
            # Проверяем РКН Тян темы
            if hasattr(self, 'theme_manager'):
                current_theme = self.theme_manager.current_theme
                if current_theme == "РКН Тян":
                    QTimer.singleShot(200, lambda: self.theme_manager.apply_rkn_background())
                elif current_theme == "РКН Тян 2":
                    QTimer.singleShot(200, lambda: self.theme_manager.apply_rkn2_background())
            
            # Очищаем отложенные данные
            delattr(self, '_deferred_css')
            if hasattr(self, '_deferred_theme_name'):
                delattr(self, '_deferred_theme_name')
            if hasattr(self, '_deferred_persist'):
                delattr(self, '_deferred_persist')
                
        except Exception as e:
            log(f"Ошибка применения отложенного CSS: {e}", "ERROR")
    
    def _force_style_refresh(self) -> None:
        """Принудительно обновляет стили всех виджетов после показа окна
        
        Необходимо потому что CSS применяется к QApplication ДО создания/показа виджетов.
        unpolish/polish заставляет Qt пересчитать стили для каждого виджета.
        """
        try:
            # unpolish/polish принудительно пересчитывает стили виджета
            for widget in self.findChildren(QWidget):
                widget.style().unpolish(widget)
                widget.style().polish(widget)
            
            log("🎨 Принудительное обновление стилей выполнено после показа окна", "DEBUG")
        except Exception as e:
            log(f"Ошибка обновления стилей: {e}", "DEBUG")
    
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
            # Переключаемся на страницу Premium через sidebar (используя SectionName)
            if hasattr(self, 'side_nav'):
                self.side_nav.set_section_by_name(SectionName.PREMIUM)

        except Exception as e:
            log(f"Ошибка при переходе на страницу Premium: {e}", level="❌ ERROR")
            self.set_status(f"Ошибка: {e}")
            
    def open_folder(self) -> None:
        """Opens the DPI folder."""
        try:
            run_hidden('explorer.exe .', shell=True)
        except Exception as e:
            self.set_status(f"Ошибка при открытии папки: {str(e)}")

    def open_connection_test(self) -> None:
        """Переключает на вкладку диагностики соединений."""
        try:
            # Используем новый API навигации через PageName
            if self.show_page(PageName.CONNECTION_TEST):
                if hasattr(self, "side_nav"):
                    self.side_nav.set_page_by_name(PageName.CONNECTION_TEST, emit_signal=False)
                try:
                    self.connection_page.start_btn.setFocus()
                except Exception:
                    pass
                log("Открыта вкладка диагностики соединения", "INFO")
        except Exception as e:
            log(f"Ошибка при открытии вкладки тестирования: {e}", "❌ ERROR")
            self.set_status(f"Ошибка: {e}")

    def set_garland_enabled(self, enabled: bool) -> None:
        """Включает или выключает новогоднюю гирлянду (Premium функция)"""
        try:
            if hasattr(self, 'garland'):
                self._update_garland_geometry()
                self.garland.set_enabled(enabled)
                self.garland.raise_()  # Поднимаем поверх всего
                log(f"Гирлянда {'включена' if enabled else 'выключена'}", "DEBUG")
        except Exception as e:
            log(f"Ошибка при изменении состояния гирлянды: {e}", "❌ ERROR")
    
    def _update_garland_geometry(self) -> None:
        """Обновляет позицию и размер гирлянды"""
        if hasattr(self, 'garland') and hasattr(self, 'container'):
            # Позиционируем под title bar на всю ширину контейнера
            self.garland.setGeometry(0, 32, self.container.width(), self.garland.maximumHeight())
            self.garland.raise_()
    
    def set_snowflakes_enabled(self, enabled: bool) -> None:
        """Включает или выключает снежинки (Premium функция)"""
        try:
            if hasattr(self, 'snowflakes'):
                self._update_snowflakes_geometry()
                self.snowflakes.set_enabled(enabled)
                self.snowflakes.raise_()  # Оверлей поверх контента
                log(f"Снежинки {'включены' if enabled else 'выключены'}", "DEBUG")
        except Exception as e:
            log(f"Ошибка при изменении состояния снежинок: {e}", "❌ ERROR")
    
    def _update_snowflakes_geometry(self) -> None:
        """Обновляет позицию и размер снежинок"""
        if hasattr(self, 'snowflakes'):
            # Покрываем всё окно полностью
            self.snowflakes.setGeometry(0, 0, self.width(), self.height())
            self.snowflakes.raise_()

    def set_blur_effect_enabled(self, enabled: bool) -> None:
        """Включает или выключает эффект размытия окна (Acrylic/Mica)"""
        try:
            from ui.theme import BlurEffect

            # Получаем HWND окна
            hwnd = int(self.winId())

            if enabled:
                success = BlurEffect.enable(hwnd, blur_type="acrylic")
                if success:
                    log("✅ Эффект размытия включён", "INFO")
                else:
                    log("⚠️ Не удалось включить эффект размытия", "WARNING")
            else:
                BlurEffect.disable(hwnd)
                log("✅ Эффект размытия выключен", "INFO")

            # Переприменяем тему чтобы обновить все стили с учётом нового состояния blur
            if hasattr(self, 'theme_manager') and self.theme_manager:
                current_theme = self.theme_manager.current_theme
                if current_theme:
                    self.theme_manager.apply_theme_async(current_theme, persist=False)

        except Exception as e:
            log(f"❌ Ошибка при изменении эффекта размытия: {e}", "ERROR")

    def set_window_opacity(self, value: int) -> None:
        """Устанавливает прозрачность окна (0-100%)"""
        try:
            # Преобразуем процент в значение 0.0-1.0
            opacity = max(0.0, min(1.0, value / 100.0))
            self.setWindowOpacity(opacity)
            log(f"Прозрачность окна установлена: {value}%", "DEBUG")
        except Exception as e:
            log(f"❌ Ошибка при установке прозрачности окна: {e}", "ERROR")

    def _update_container_opacity(self, blur_enabled: bool) -> None:
        """Обновляет прозрачность контейнера в зависимости от состояния blur"""
        try:
            if not hasattr(self, 'container'):
                return

            # Определяем непрозрачность: меньше для blur, полностью непрозрачно без него
            opacity = 180 if blur_enabled else 255

            # Получаем текущие цвета темы
            from ui.theme import ThemeManager
            theme_manager = ThemeManager.instance()
            if theme_manager and hasattr(theme_manager, '_current_theme'):
                theme_name = theme_manager._current_theme
                theme_config = theme_manager._themes.get(theme_name, {})
                theme_bg = theme_config.get('theme_bg', '30, 30, 30')
                border_color = "rgba(80, 80, 80, 200)" if 'Светлая' not in theme_name else "rgba(200, 200, 200, 220)"
            else:
                theme_bg = '30, 30, 30'
                border_color = "rgba(80, 80, 80, 200)"

            self.container.setStyleSheet(f"""
                QFrame#mainContainer {{
                    background-color: rgba({theme_bg}, {opacity});
                    border-radius: 10px;
                    border: 1px solid {border_color};
                }}
            """)
            log(f"Контейнер обновлён: opacity={opacity}", "DEBUG")
        except Exception as e:
            log(f"Ошибка обновления контейнера: {e}", "WARNING")

    def resizeEvent(self, event):
        """Обновляем декорации при изменении размера окна"""
        super().resizeEvent(event)
        try:
            if hasattr(self, "_update_resize_handles"):
                self._update_resize_handles()
        except Exception:
            pass
        self._update_garland_geometry()
        self._update_snowflakes_geometry()
        self._on_window_geometry_changed()
    
    def showEvent(self, event):
        """Устанавливаем геометрию декораций при первом показе окна"""
        super().showEvent(event)
        self._update_garland_geometry()
        self._update_snowflakes_geometry()

        # Отключаем системное скругление углов на Windows 11
        # чтобы избежать белых треугольников по краям при использовании CSS border-radius
        try:
            from ui.theme import BlurEffect
            hwnd = int(self.winId())
            BlurEffect.disable_window_rounding(hwnd)
        except Exception:
            pass

        # Применяем сохранённое maximized состояние при первом показе
        self._apply_saved_maximized_state_if_needed()

        # Включаем автосохранение геометрии (после первого show + небольшой паузы)
        QTimer.singleShot(350, self._enable_geometry_persistence)

    def _init_garland_from_registry(self) -> None:
        """Загружает состояние гирлянды и снежинок из реестра при старте"""
        try:
            from config.reg import get_garland_enabled, get_snowflakes_enabled
            
            garland_saved = get_garland_enabled()
            snowflakes_saved = get_snowflakes_enabled()
            log(f"🎄 Инициализация: гирлянда={garland_saved}, снежинки={snowflakes_saved}", "DEBUG")
            
            # Проверяем премиум статус
            is_premium = False
            if hasattr(self, 'donate_checker') and self.donate_checker:
                try:
                    is_premium, _, _ = self.donate_checker.check_subscription_status(use_cache=True)
                    log(f"🎄 Премиум статус: {is_premium}", "DEBUG")
                except Exception as e:
                    log(f"🎄 Ошибка проверки премиума: {e}", "DEBUG")
            
            # Гирлянда
            should_enable_garland = is_premium and garland_saved
            if should_enable_garland:
                self.set_garland_enabled(True)
            if hasattr(self, 'appearance_page'):
                self.appearance_page.set_garland_state(should_enable_garland)
            
            # Снежинки
            should_enable_snowflakes = is_premium and snowflakes_saved
            if should_enable_snowflakes:
                self.set_snowflakes_enabled(True)
            if hasattr(self, 'appearance_page'):
                self.appearance_page.set_snowflakes_state(should_enable_snowflakes)

            # Эффект размытия (не зависит от премиума)
            from config.reg import get_blur_effect_enabled
            blur_saved = get_blur_effect_enabled()
            log(f"🔮 Инициализация: blur={blur_saved}", "DEBUG")
            if blur_saved:
                self.set_blur_effect_enabled(True)
            if hasattr(self, 'appearance_page'):
                self.appearance_page.set_blur_effect_state(blur_saved)

            # Прозрачность окна (не зависит от премиума)
            from config.reg import get_window_opacity
            opacity_saved = get_window_opacity()
            log(f"🔮 Инициализация: opacity={opacity_saved}%", "DEBUG")
            self.set_window_opacity(opacity_saved)
            if hasattr(self, 'appearance_page'):
                self.appearance_page.set_opacity_value(opacity_saved)

        except Exception as e:
            log(f"❌ Ошибка загрузки состояния декораций: {e}", "ERROR")
            import traceback
            log(traceback.format_exc(), "DEBUG")


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
    
    # ✅ Автоматическая установка сертификата (асинхронно, не блокирует запуск)
    def _install_certificate_async():
        try:
            from startup.certificate_installer import check_and_install_on_startup
            check_and_install_on_startup()
        except Exception:
            pass  # Не критично
    
    import threading
    threading.Thread(target=_install_certificate_async, daemon=True).start()

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

    # ✅ Проверки перед созданием QApplication (не блокируют запуск)
    from startup.check_start import check_goodbyedpi, check_mitmproxy
    from startup.check_start import _native_message
    
    critical_warnings = []
    
    # Проверка GoodbyeDPI: пытаемся удалить службы, но не блокируем запуск
    has_gdpi, gdpi_msg = check_goodbyedpi()
    if has_gdpi:
        log("WARNING: GoodbyeDPI обнаружен - продолжим работу после предупреждения", "⚠ WARNING")
        if gdpi_msg:
            critical_warnings.append(gdpi_msg)
    
    # Проверка mitmproxy: только предупреждаем
    has_mitmproxy, mitmproxy_msg = check_mitmproxy()
    if has_mitmproxy:
        log("WARNING: mitmproxy обнаружен - продолжим работу после предупреждения", "⚠ WARNING")
        if mitmproxy_msg:
            critical_warnings.append(mitmproxy_msg)
    
    if critical_warnings:
        _native_message(
            "Предупреждение",
            "\n\n".join(critical_warnings),
            0x30  # MB_ICONWARNING
        )

    # ---------------- Создаём QApplication ----------------
    try:
        os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
        _set_attr_if_exists("AA_EnableHighDpiScaling")
        _set_attr_if_exists("AA_UseHighDpiPixmaps")

        app = QApplication(sys.argv)

        # На Windows принудительно отключаем "transient/overlay" скроллбары
        # (иначе они могут не отображаться/быть практически невидимыми).
        try:
            import platform
            if platform.system() == "Windows":
                from PyQt6.QtWidgets import QProxyStyle, QStyle

                class _NoTransientScrollbarsStyle(QProxyStyle):
                    def styleHint(self, hint, option=None, widget=None, returnData=None):
                        if hint == QStyle.StyleHint.SH_ScrollBar_Transient:
                            return 0
                        return super().styleHint(hint, option, widget, returnData)

                app.setStyle(_NoTransientScrollbarsStyle(app.style()))
        except Exception:
            pass

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
        
        # Тема применяется позже в ThemeManager.__init__ - убран дублирующий вызов
        
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
            from startup.admin_check_debug import debug_admin_status

            preload_service_status("BFE")

            if not ensure_bfe_running(show_ui=True):
                log("BFE не запущен, продолжаем работу после предупреждения", "⚠ WARNING")

            # ✅ ТОЛЬКО НЕКРИТИЧЕСКИЕ ПРОВЕРКИ (пути, команды, архив)
            warnings_ok = display_startup_warnings()
            if not warnings_ok and not start_in_tray:
                log("Некритические проверки не пройдены, продолжаем работу после предупреждения", "⚠ WARNING")

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
