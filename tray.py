import os

from PyQt6.QtWidgets import QMenu, QWidget, QApplication, QMessageBox, QStyle, QSystemTrayIcon
from PyQt6.QtGui     import QAction, QIcon, QCursor
from PyQt6.QtCore    import Qt, QEvent

from reg import get_dpi_autostart, set_dpi_autostart
from reg import get_strategy_autoload, set_strategy_autoload

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
        self._shown_hint   = False            # показано ли «свернуто в трей»

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
                QApplication.style().standardIcon(QStyle.SP_ComputerIcon)
            )
            print(f"ОШИБКА: Файл иконки {icon_path} не найден")

        # tooltip с версией
        self.tray_icon.setToolTip(f"Zapret v{self.app_version}")

    # ------------------------------------------------------------------
    #  КОНТЕКСТНОЕ МЕНЮ
    # ------------------------------------------------------------------
    def setup_menu(self):
        menu = QMenu()

        # показать окно
        show_act = QAction("Показать", self.parent)
        show_act.triggered.connect(self.show_window)
        menu.addAction(show_act)

        # копировать ID
        copy_id_act = QAction("Скопировать ID устройства", self.parent)
        copy_id_act.triggered.connect(self.copy_device_id_to_clipboard)
        menu.addAction(copy_id_act)

        # ──── НОВЫЙ ПУНКТ: "Автозапуск DPI" ────
        self.auto_dpi_act = QAction("Автозапуск DPI", self.parent,
                                    checkable=True)
        self.auto_dpi_act.setChecked(get_dpi_autostart())     # текущее состояние
        self.auto_dpi_act.toggled.connect(self.toggle_dpi_autostart)
        menu.addAction(self.auto_dpi_act)
        # ───────────────────────────────────────

        self.auto_strat_act = QAction("Автозагрузка стратегий", self.parent,
                                    checkable=True)
        self.auto_strat_act.setChecked(get_strategy_autoload())
        self.auto_strat_act.toggled.connect(self.toggle_strategy_autoload)
        menu.addAction(self.auto_strat_act)

        menu.addSeparator()

        # консоль
        console_act = QAction("Консоль", self.parent)
        console_act.triggered.connect(self.show_console)
        menu.addAction(console_act)

        menu.addSeparator()

        # ─── ДВА ОТДЕЛЬНЫХ ВЫХОДА ──────────────────────────
        exit_only_act = QAction("Выход", self.parent)
        exit_only_act.triggered.connect(self.exit_only)          # ← NEW
        menu.addAction(exit_only_act)

        exit_stop_act = QAction("Выход и остановить DPI", self.parent)
        exit_stop_act.triggered.connect(self.exit_and_stop)      # ← NEW
        menu.addAction(exit_stop_act)
        # ───────────────────────────────────────────────────

        self.tray_icon.setContextMenu(menu)

    # ------------------------------------------------------------------
    # 1) ПРОСТО закрыть GUI, winws.exe оставить жить
    # ------------------------------------------------------------------
    def exit_only(self):
        """Закрывает GUI, процесс winws.exe остаётся запущенным."""
        from log import log
        log("Выход без остановки DPI (только GUI)", level="INFO")

        # останавливаем мониторинг (он будет «пустым» без окна)
        if hasattr(self.parent, 'process_monitor') and self.parent.process_monitor:
            self.parent.process_monitor.stop()

        self.tray_icon.hide()
        QApplication.quit()

    def toggle_strategy_autoload(self, enabled: bool):
        """
        При выключении показываем страшное предупреждение.
        Если пользователь нажмёт «Нет» – ничего не меняем.
        """
        # пользователь хочет ОТКЛЮЧИТЬ авто-скачивание
        if not enabled:
            warn = (
                "<b>Вы действительно хотите ОТКЛЮЧИТЬ автозагрузку "
                "стратегий?</b><br><br>"
                "⚠️  Это <span style='color:red;font-weight:bold;'>сломает</span> "
                "быстрое и удобное обновление стратегий "
                "<u>без</u> переустановки всей программы! "
                "<br>Будьте аккуратны!"
            )
            resp = QMessageBox.question(
                self.parent,
                "Отключить автозагрузку стратегий?",
                warn,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if resp != QMessageBox.StandardButton.Yes:
                # Пользователь передумал – возвращаем галку и выходим
                self.auto_strat_act.blockSignals(True)
                self.auto_strat_act.setChecked(True)
                self.auto_strat_act.blockSignals(False)
                return        # в реестр ничего не пишем

        # сохраняем выбор
        set_strategy_autoload(enabled)

        # уведомление
        msg = ("Стратегии будут скачиваться автоматически"
               if enabled
               else "Автозагрузка стратегий отключена")
        self.show_notification("Zapret", msg)

    # ------------------------------------------------------------------
    # 2) СТАРОЕ ПОВЕДЕНИЕ – остановить DPI и выйти
    # ------------------------------------------------------------------
    def exit_and_stop(self):
        """Останавливает winws.exe, затем закрывает GUI."""
        from stop import stop_dpi
        from log import log

        log("Выход + остановка DPI", level="INFO")

        if hasattr(self.parent, 'dpi_starter'):
            stop_dpi(self)

        if hasattr(self.parent, 'process_monitor') and self.parent.process_monitor:
            self.parent.process_monitor.stop()

        self.tray_icon.hide()
        QApplication.quit()

    # ------------------------------------------------------------------
    #  КОПИРОВАНИЕ ID  ★ NEW
    # ------------------------------------------------------------------
    def copy_device_id_to_clipboard(self):
        """Копирует client-ID бота в буфер обмена и показывает всплывашку."""
        try:
            # импортируем только когда нужно, чтобы не тянуть TG-логгер при запуске
            from tg_log_delta import get_client_id
            cid = str(get_client_id())

            QApplication.clipboard().setText(cid)
            self.show_notification("ID устройства скопирован", cid, 3000)
        except Exception as e:
            # на всякий случай продублируем ошибку
            QMessageBox.warning(self.parent, "Ошибка",
                                f"Не удалось получить ID устройства:\n{e}")

    # ------------------------------------------------------------------
    #  РЕАКЦИЯ НА КЛИКИ ПО ИКОНКЕ
    # ------------------------------------------------------------------
    def on_tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:          # левая кнопка
            if self.parent.isVisible():
                self.parent.hide()
            else:
                self.show_window()

    # ------------------------------------------------------------------
    #  КОНСОЛЬ
    # ------------------------------------------------------------------
    def show_console(self):
        from PyQt6.QtWidgets import QInputDialog, QLineEdit
        from discord_restart import toggle_discord_restart

        cmd, ok = QInputDialog.getText(
            self.parent, "Консоль", "Введите команду:",
            QLineEdit.Normal, ""
        )
        if ok and cmd:
            if cmd.lower() == "ркн":
                toggle_discord_restart(
                    self.parent,
                    status_callback=lambda m: self.show_notification("Консоль", m)
                )

    # ------------------------------------------------------------------
    #  ПРОЧИЕ ДЕЙСТВИЯ
    # ------------------------------------------------------------------
    def show_window(self):
        self.parent.showNormal()
        self.parent.activateWindow()
        self.parent.raise_()

    # ---------- обработчик переключателя -----------------------------
    def toggle_dpi_autostart(self, enabled: bool):
        set_dpi_autostart(enabled)
        msg = "DPI будет запускаться автоматически при старте программы" if enabled \
              else "Автоматическое включение DPI при старте программы отключено"
        self.show_notification("Zapret", msg)

    # ------------------------------------------------------------------
    #  ВСПОМОГАТЕЛЬНЫЕ
    # ------------------------------------------------------------------
    def install_event_handlers(self):
        self._orig_close  = self.parent.closeEvent
        self._orig_change = self.parent.changeEvent
        self.parent.closeEvent  = self._close_event
        self.parent.changeEvent = self._change_event

    def _close_event(self, ev):
        if not getattr(self.parent, '_allow_close', False):
            if not self._shown_hint:
                self.show_notification(
                    "Zapret продолжает работать",
                    "Свернуто в трей. Кликните по иконке, чтобы открыть окно."
                )
                self._shown_hint = True
            self.parent.hide()
            ev.ignore()
        else:
            self._orig_close(ev)

    def _change_event(self, ev):
        if ev.type() == QEvent.WindowStateChange and self.parent.isMinimized():
            ev.ignore()
            self.parent.hide()
            if not self._shown_hint:
                self.show_notification(
                    "Zapret продолжает работать",
                    "Свернуто в трей. Кликните по иконке, чтобы открыть окно."
                )
                self._shown_hint = True
        else:
            self._orig_change(ev)