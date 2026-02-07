# tray.py

import os

from PyQt6.QtWidgets import QMenu, QApplication, QStyle, QSystemTrayIcon
from PyQt6.QtGui     import QAction, QIcon
from PyQt6.QtCore    import QEvent

try:
    import qtawesome as qta
    HAS_QTAWESOME = True
except ImportError:
    HAS_QTAWESOME = False

# ----------------------------------------------------------------------
#   SystemTrayManager
# ----------------------------------------------------------------------
class SystemTrayManager:
    """Управление иконкой в системном трее и соответствующим функционалом"""

    def __init__(self, parent, icon_path, app_version):
        """
        Args:
            parent       – главное окно приложения
            icon_path    – png/ico иконка
            app_version  – строка версии (для tooltip-а)
        """
        self.parent        = parent
        self.tray_icon     = QSystemTrayIcon(parent)
        self.app_version   = app_version

        # иконка + меню + сигналы
        self.set_icon(icon_path)
        self.setup_menu()                     # ← создаём меню
        self.tray_icon.activated.connect(self.on_tray_icon_activated)
        self.tray_icon.show()

        # перехватываем события окна
        self.install_event_handlers()

    # ------------------------------------------------------------------
    #  ВСПЛЫВАЮЩИЕ СООБЩЕНИЯ
    # ------------------------------------------------------------------
    def show_notification(self, title, message, msec=5000):
        self.tray_icon.showMessage(
            title, message,
            QSystemTrayIcon.MessageIcon.Information, msec
        )

    # ------------------------------------------------------------------
    #  НАСТРОЙКА ИКОНКИ
    # ------------------------------------------------------------------
    def set_icon(self, icon_path):
        if os.path.exists(icon_path):
            self.tray_icon.setIcon(QIcon(icon_path))
        else:
            self.tray_icon.setIcon(
                QApplication.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)
            )
            print(f"ОШИБКА: Файл иконки {icon_path} не найден")

        # tooltip с версией
        self.tray_icon.setToolTip(f"Zapret2 v{self.app_version}")

    # ------------------------------------------------------------------
    #  КОНТЕКСТНОЕ МЕНЮ
    # ------------------------------------------------------------------
    def setup_menu(self):
        menu = QMenu()
        self.menu = menu

        # Диагностика: помогает понять, "появляется ли" меню и не закрывается ли сразу.
        try:
            from log import log

            menu.aboutToShow.connect(lambda: log("Tray menu: aboutToShow", "DEBUG"))  # type: ignore[attr-defined]
            menu.aboutToHide.connect(lambda: log("Tray menu: aboutToHide", "DEBUG"))  # type: ignore[attr-defined]
            log(f"Tray menu initialized (hasContextMenu=True)", "DEBUG")
        except Exception:
            pass

        # Применяем стиль меню
        self._apply_menu_style(menu)

        # показать окно
        show_act = QAction("Показать", self.parent)
        if HAS_QTAWESOME:
            show_act.setIcon(qta.icon('fa5s.window-restore', color='#60cdff'))
        show_act.triggered.connect(self.show_window)
        menu.addAction(show_act)

        # Прозрачность окна (быстрые пресеты + способ восстановить видимость)
        opacity_menu = menu.addMenu("Прозрачность окна")
        if HAS_QTAWESOME:
            opacity_menu.setIcon(qta.icon('fa5s.adjust', color='#60cdff'))

        def set_opacity(value: int):
            try:
                from config.reg import set_window_opacity as _set_window_opacity
                _set_window_opacity(value)
            except Exception:
                pass

            try:
                if hasattr(self.parent, "set_window_opacity"):
                    self.parent.set_window_opacity(value)
                if hasattr(self.parent, "appearance_page") and self.parent.appearance_page:
                    self.parent.appearance_page.set_opacity_value(value)
            except Exception:
                pass

        presets = [
            (100, "100% (непрозрачное)"),
            (75, "75%"),
            (50, "50%"),
            (25, "25%"),
            (0, "0% (полностью прозрачное)"),
        ]
        for value, title in presets:
            act = QAction(title, self.parent)
            act.triggered.connect(lambda checked=False, v=value: set_opacity(v))
            opacity_menu.addAction(act)

        menu.addSeparator()

        # консоль
        console_act = QAction("Консоль", self.parent)
        if HAS_QTAWESOME:
            console_act.setIcon(qta.icon('fa5s.terminal', color='#888888'))
        console_act.triggered.connect(self.show_console)
        menu.addAction(console_act)

        menu.addSeparator()

        # ─── ДВА ОТДЕЛЬНЫХ ВЫХОДА ──────────────────────────
        exit_only_act = QAction("Выход", self.parent)
        if HAS_QTAWESOME:
            exit_only_act.setIcon(qta.icon('fa5s.sign-out-alt', color='#aaaaaa'))
        exit_only_act.triggered.connect(self.exit_only)
        menu.addAction(exit_only_act)

        exit_stop_act = QAction("Выход и остановить DPI", self.parent)
        if HAS_QTAWESOME:
            exit_stop_act.setIcon(qta.icon('fa5s.power-off', color='#e81123'))
        exit_stop_act.triggered.connect(self.exit_and_stop)
        menu.addAction(exit_stop_act)
        # ───────────────────────────────────────────────────

        self.tray_icon.setContextMenu(menu)

    def _apply_menu_style(self, menu: QMenu):
        """Применяет стиль к меню трея"""
        # Получаем цвета текущей темы
        try:
            from ui.theme import ThemeManager
            theme_manager = ThemeManager.instance()
            if theme_manager and hasattr(theme_manager, '_current_theme'):
                theme_name = theme_manager._current_theme
                theme_config = theme_manager._themes.get(theme_name, {})
                theme_bg = theme_config.get('theme_bg', '30, 30, 30')
                is_light = 'Светлая' in theme_name if theme_name else False
            else:
                theme_bg = '30, 30, 30'
                is_light = False
        except:
            theme_bg = '30, 30, 30'
            is_light = False

        # Цвета в зависимости от темы
        if is_light:
            bg_color = f"rgb({theme_bg})"
            text_color = "#000000"
            hover_bg = "rgba(0, 0, 0, 0.1)"
            border_color = "rgba(0, 0, 0, 0.2)"
            separator_color = "rgba(0, 0, 0, 0.15)"
        else:
            bg_color = f"rgb({theme_bg})"
            text_color = "#ffffff"
            hover_bg = "rgba(255, 255, 255, 0.1)"
            border_color = "rgba(255, 255, 255, 0.15)"
            separator_color = "rgba(255, 255, 255, 0.1)"

        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 6px;
                padding: 2px 0px;
            }}
            QMenu::item {{
                background-color: transparent;
                color: {text_color};
                padding: 3px 16px 3px 8px;
                margin: 0px 3px;
                border-radius: 3px;
                font-size: 11px;
            }}
            QMenu::item:selected {{
                background-color: {hover_bg};
            }}
            QMenu::separator {{
                height: 1px;
                background-color: {separator_color};
                margin: 2px 6px;
            }}
            QMenu::icon {{
                padding-left: 4px;
            }}
        """)

    # ------------------------------------------------------------------
    #  ВСПОМОГАТЕЛЬНЫЙ МЕТОД ДЛЯ СОХРАНЕНИЯ ГЕОМЕТРИИ
    # ------------------------------------------------------------------
    def _save_window_geometry(self):
        """Сохраняет текущую позицию и размер окна"""
        try:
            from config import set_window_position, set_window_size
            from log import log
            
            # Если окно видимо - сохраняем его текущую геометрию
            if self.parent.isVisible():
                pos = self.parent.pos()
                set_window_position(pos.x(), pos.y())
                
                size = self.parent.size()
                set_window_size(size.width(), size.height())
                
                log(f"Геометрия окна сохранена: ({pos.x()}, {pos.y()}), {size.width()}x{size.height()}", "DEBUG")
        except Exception as e:
            from log import log
            log(f"Ошибка сохранения геометрии окна: {e}", "❌ ERROR")

    def hide_to_tray(self, show_hint: bool = True) -> None:
        """Скрывает окно в трей (без выхода из GUI)."""
        try:
            # ✅ СОХРАНЯЕМ ПОЗИЦИЮ ПЕРЕД СКРЫТИЕМ
            self._save_window_geometry()
        except Exception:
            pass

        try:
            self.parent.hide()
        except Exception:
            return

        if not show_hint:
            return

        # ✅ ПОКАЗЫВАЕМ УВЕДОМЛЕНИЕ ТОЛЬКО ОДИН РАЗ ЗА ВСЁ ВРЕМЯ
        try:
            from config import get_tray_hint_shown, set_tray_hint_shown
            if not get_tray_hint_shown():
                self.show_notification(
                    "Zapret продолжает работать",
                    "Свернуто в трей. Кликните по иконке, чтобы открыть окно."
                )
                set_tray_hint_shown(True)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # 1) ПРОСТО закрыть GUI, winws.exe оставить жить
    # ------------------------------------------------------------------
    def exit_only(self):
        """Закрывает GUI, процесс winws.exe остаётся запущенным."""
        # Единая точка выхода: DPI не трогаем.
        if hasattr(self.parent, "request_exit"):
            self.parent.request_exit(stop_dpi=False)
            return

        # Fallback для старой архитектуры
        from log import log
        log("Выход без остановки DPI (fallback, только GUI)", level="INFO")
        self.parent._allow_close = True
        self.tray_icon.hide()
        QApplication.quit()

    # ------------------------------------------------------------------
    # 2) СТАРОЕ ПОВЕДЕНИЕ – остановить DPI и выйти
    # ------------------------------------------------------------------
    def exit_and_stop(self):
        """Останавливает winws.exe, затем закрывает GUI."""
        # Единая точка выхода: остановить DPI и выйти (учитывает все режимы).
        if hasattr(self.parent, "request_exit"):
            self.parent.request_exit(stop_dpi=True)
            return

        # Fallback для старой архитектуры
        from dpi.stop import stop_dpi
        from log import log
        log("Выход + остановка DPI (fallback)", level="INFO")
        if hasattr(self.parent, 'dpi_starter'):
            stop_dpi(self.parent)
        self.parent._allow_close = True
        self.tray_icon.hide()
        QApplication.quit()

    # ------------------------------------------------------------------
    #  РЕАКЦИЯ НА КЛИКИ ПО ИКОНКЕ
    # ------------------------------------------------------------------
    def on_tray_icon_activated(self, reason):
        # Диагностика: 1=Trigger (LMB), 2=DoubleClick, 3=MiddleClick, 4=Context (RMB)
        try:
            from log import log

            def _enum_to_int(v):
                try:
                    return int(v)
                except Exception:
                    try:
                        return int(v.value)
                    except Exception:
                        return str(v)

            log(
                f"Tray activated: reason={_enum_to_int(reason)} visible={self.parent.isVisible()}",
                "DEBUG",
            )
        except Exception:
            pass

        if reason == QSystemTrayIcon.ActivationReason.Trigger:          # левая кнопка
            if self.parent.isVisible():
                self.hide_to_tray(show_hint=False)
            else:
                self.show_window()

    # ------------------------------------------------------------------
    #  КОНСОЛЬ
    # ------------------------------------------------------------------
    def show_console(self):
        from PyQt6.QtWidgets import QInputDialog, QLineEdit
        from discord.discord_restart import toggle_discord_restart
        from github_api_toggle import toggle_github_api_removal

        cmd, ok = QInputDialog.getText(
            self.parent, "Консоль", "Введите команду:",
            QLineEdit.EchoMode.Normal, ""
        )
        if ok and cmd:
            if cmd.lower() == "ркн":
                toggle_discord_restart(
                    self.parent,
                    status_callback=lambda m: self.show_notification("Консоль", m)
                )
            elif cmd.lower() == "апигитхаб":
                toggle_github_api_removal(
                    self.parent,
                    status_callback=lambda m: self.show_notification("Консоль", m)
                )

    # ------------------------------------------------------------------
    #  ПРОЧИЕ ДЕЙСТВИЯ
    # ------------------------------------------------------------------
    def show_window(self):
        """Показывает окно и восстанавливает его на прежнем месте"""
        try:
            from log import log
            if hasattr(self.parent, "_snapshot_interaction_state_for_debug"):
                snap = self.parent._snapshot_interaction_state_for_debug()
                log(f"Tray show_window: snap={snap}", "DEBUG")
        except Exception:
            pass

        # Defensive: if we got here to "unstick" the UI, clear any grabs/popups/cursors first.
        try:
            if hasattr(self.parent, "_dismiss_transient_ui_safe"):
                self.parent._dismiss_transient_ui_safe(reason="tray_show_window")  # type: ignore[attr-defined]
        except Exception:
            pass
        try:
            if hasattr(self.parent, "_force_release_interaction_states"):
                self.parent._force_release_interaction_states(reason="tray_show_window")  # type: ignore[attr-defined]
        except Exception:
            pass

        # ✅ ПРОВЕРЯЕМ: если окно было скрыто, просто показываем
        # Позиция уже сохранена, Qt сам её помнит
        self.parent.showNormal()
        self.parent.activateWindow()
        self.parent.raise_()

    # ------------------------------------------------------------------
    #  ВСПОМОГАТЕЛЬНЫЕ
    # ------------------------------------------------------------------
    def install_event_handlers(self):
        self._orig_close  = self.parent.closeEvent
        self._orig_change = self.parent.changeEvent
        self.parent.closeEvent  = self._close_event
        self.parent.changeEvent = self._change_event

    def _close_event(self, ev):
        # ✅ ПРОВЕРЯЕМ флаг полного закрытия программы
        if hasattr(self.parent, '_closing_completely') and self.parent._closing_completely:
            # Программа полностью закрывается - вызываем оригинальный closeEvent
            # (который сохранит позицию)
            self._orig_close(ev)
            return

        # Обычное закрытие окна (Alt+F4, системное закрытие и т.д.)
        # Показываем диалог выбора: закрыть только GUI или GUI + остановить DPI
        ev.ignore()
        try:
            from ui.close_dialog import ask_close_action
            result = ask_close_action(parent=self.parent)
            if result is None:
                # Пользователь отменил
                return
            # result: False = только GUI, True = GUI + остановить DPI
            self.parent.request_exit(stop_dpi=result)
        except Exception:
            # Fallback: закрыть только GUI
            self.exit_only()

    def _change_event(self, ev):
        self._orig_change(ev)
