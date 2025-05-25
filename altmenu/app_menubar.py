# app_menubar.py

from PyQt6.QtWidgets import QMenuBar, QWidget, QMessageBox, QApplication
from PyQt6.QtGui     import QKeySequence, QAction
import webbrowser

from config.config import APP_VERSION
from config.urls   import INFO_URL
from .about_dialog import AboutDialog

# ─── работа с реестром ──────────────────────────
from config.reg import (
    get_dpi_autostart,  set_dpi_autostart,
    get_strategy_autoload, set_strategy_autoload
)

class AppMenuBar(QMenuBar):
    """
    Верхняя строка меню («Alt-меню»).
    """

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.parent      = parent
        self._set_status = getattr(parent, "set_status", lambda *_: None)

        # -------- 1. Настройки -------------------------------------------------
        file_menu = self.addMenu("&Настройки")

        # Чек-бокс «Автозапуск DPI»
        self.auto_dpi_act = QAction("Автозапуск DPI", self, checkable=True)
        self.auto_dpi_act.setChecked(get_dpi_autostart())
        self.auto_dpi_act.toggled.connect(self.toggle_dpi_autostart)
        file_menu.addAction(self.auto_dpi_act)

        # 2Чек-бокс «Автозагрузка стратегий» (раз уж из трея убран)
        self.auto_strat_act = QAction("Автозагрузка стратегий", self, checkable=True)
        self.auto_strat_act.setChecked(get_strategy_autoload())
        self.auto_strat_act.toggled.connect(self.toggle_strategy_autoload)
        file_menu.addAction(self.auto_strat_act)

        file_menu.addSeparator()

        act_exit = QAction("Выйти из GUI", self, shortcut=QKeySequence("Ctrl+Q"))
        act_exit.triggered.connect(parent.close)
        file_menu.addAction(act_exit)

        full_exit_act = QAction("Полностью выйти", self, shortcut=QKeySequence("Ctrl+Shift+Q"))
        full_exit_act.triggered.connect(self.full_exit)
        file_menu.addAction(full_exit_act)

        # -------- 2. «Телеметрия / Настройки» ------------------------------
        telemetry_menu = self.addMenu("&Телеметрия")

        # 2 Показ журнала
        act_logs = QAction("Показать лог-файл", self)
        act_logs.triggered.connect(self.show_logs)
        telemetry_menu.addAction(act_logs)

        act_logs = QAction("Отправить лог файл", self)
        act_logs.triggered.connect(self.send_log_to_tg)
        telemetry_menu.addAction(act_logs)

        # 2 «О программе…»
        act_about = QAction("О программе…", self)
        act_about.triggered.connect(lambda: AboutDialog(parent).exec())
        telemetry_menu.addAction(act_about)

        # -------- 3. «Справка» ---------------------------------------------
        help_menu = self.addMenu("&Справка")

        act_help = QAction("Что это такое? (Руководство)", self)
        act_help.triggered.connect(self.open_info)
        help_menu.addAction(act_help)

    # ==================================================================
    #  Обработчики чек-боксов
    # ==================================================================
    def toggle_dpi_autostart(self, enabled: bool):
        """
        Включает / выключает автозапуск DPI и показывает диалог-уведомление.
        """
        set_dpi_autostart(enabled)

        msg = ("DPI будет запускаться автоматически при старте программы"
               if enabled
               else "Автоматический запуск DPI отключён")
        self._set_status(msg)
        QMessageBox.information(self.parent, "Автозапуск DPI", msg)

    def toggle_strategy_autoload(self, enabled: bool):
        """
        Повторяет логику, которая раньше была в трее: при отключении
        спрашивает подтверждение.
        """
        if not enabled:
            warn = (
                "<b>Вы действительно хотите ОТКЛЮЧИТЬ автозагрузку "
                "стратегий?</b><br><br>"
                "⚠️  Это <span style='color:red;font-weight:bold;'>сломает</span> "
                "быстрое и удобное обновление стратегий без переустановки "
                "всей программы!"
            )
            resp = QMessageBox.question(
                self.parent,
                "Отключить автозагрузку стратегий?",
                warn,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if resp != QMessageBox.StandardButton.Yes:
                # пользователь передумал – откатываем галку
                self.auto_strat_act.blockSignals(True)
                self.auto_strat_act.setChecked(True)
                self.auto_strat_act.blockSignals(False)
                return

        # сохраняем выбор
        set_strategy_autoload(enabled)
        msg = ("Стратегии будут скачиваться автоматически"
               if enabled
               else "Автозагрузка стратегий отключена")
        self._set_status(msg)
        QMessageBox.information(self.parent, "Автозагрузка стратегий", msg)

    # ==================================================================
    #  Полный выход (убираем трей +, при желании, останавливаем DPI)
    # ==================================================================

    def full_exit(self):
        # -----------------------------------------------------------------
        # 1. Диалог на русском, но с англ. подсказками в тексте
        # -----------------------------------------------------------------
        box = QMessageBox(self.parent)
        box.setWindowTitle("Выход")
        box.setIcon(QMessageBox.Icon.Question)

        # сам текст оставляем без изменений
        box.setText(
            "Остановить DPI-службу перед выходом?\n"
            "Да – остановить DPI и выйти\n"
            "Нет  – выйти, не останавливая DPI\n"
            "Отмена – остаться в программе"
        )

        # добавляем три стандартные кнопки
        box.setStandardButtons(
            QMessageBox.StandardButton.Yes |
            QMessageBox.StandardButton.No  |
            QMessageBox.StandardButton.Cancel
        )
        box.setDefaultButton(QMessageBox.StandardButton.Cancel)

        # ─── Русифицируем подписи ────────────────────────────────────────
        box.button(QMessageBox.StandardButton.Yes).setText("Да")
        box.button(QMessageBox.StandardButton.No).setText("Нет")
        box.button(QMessageBox.StandardButton.Cancel).setText("Отмена")

        # показываем диалог
        resp = box.exec()

        if resp == QMessageBox.StandardButton.Cancel:
            return                      # пользователь передумал

        stop_dpi_required = resp == QMessageBox.StandardButton.Yes

        # -----------------------------------------------------------------
        # 2. Дальше логика выхода (как раньше)
        # -----------------------------------------------------------------
        if stop_dpi_required:
            try:
                from dpi.stop import stop_dpi
                stop_dpi(self)
            except Exception as e:
                QMessageBox.warning(
                    self.parent, "Ошибка DPI",
                    f"Не удалось остановить DPI:\n{e}"
                )

        if hasattr(self.parent, "process_monitor") and self.parent.process_monitor:
            self.parent.process_monitor.stop()

        if hasattr(self.parent, "tray_manager"):
            self.parent.tray_manager.tray_icon.hide()

        self.parent._allow_close = True
        QApplication.quit()

    # ==================================================================
    #  Справка
    # ==================================================================
    def open_info(self):
        try:
            import webbrowser
            webbrowser.open(INFO_URL)
            self._set_status("Открываю руководство…")
        except Exception as e:
            err = f"Ошибка при открытии руководства: {e}"
            self._set_status(err)
            QMessageBox.warning(self.parent, "Ошибка", err)

    def show_logs(self):
        """Shows the application logs in a dialog"""
        try: 
            from log import get_log_content, LogViewerDialog
            log_content = get_log_content()
            log_dialog = LogViewerDialog(self, log_content)
            log_dialog.exec()
        except Exception as e:
            self.set_status(f"Ошибка при открытии журнала: {str(e)}")

    def send_log_to_tg(self):
        """Отправляет текущий лог-файл в Telegram."""
        try:
            from tgram.tg_sender import send_log_to_tg
            from tgram.tg_log_delta import get_client_id

            # путь к вашему лог-файлу (как в модуле log)
            LOG_PATH = "zapret_log.txt"

            caption = f"Zapret log  (ID: {get_client_id()}, v{APP_VERSION})"
            send_log_to_tg(LOG_PATH, caption)

            QMessageBox.information(self, "Отправка",
                                    "Лог отправлен боту.")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка",
                                f"Не удалось отправить лог:\n{e}")