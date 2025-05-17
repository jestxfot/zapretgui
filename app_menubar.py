# app_menubar.py
from PyQt6.QtWidgets import QMenuBar, QWidget, QMessageBox
from PyQt6.QtGui     import QAction
from config import APP_VERSION
from urls import INFO_URL
from about_dialog import AboutDialog

import webbrowser

class AppMenuBar(QMenuBar):
    """
    Верхняя строка меню («Alt-меню»), вынесенная
    в отдельный модуль, чтобы не захламлять main.py.
    parent  –  экземпляр LupiDPIApp (или любого QWidget,
               содержащего нужные методы-слоты).
    """
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._set_status = getattr(parent, "set_status", lambda *_: None)

        # ---------- 1.  Файл -------------------------------------------------
        file_menu = self.addMenu("&Файл")          # Alt+Ф

        act_exit = QAction("Выйти из GUI", self, shortcut="Ctrl+Q")
        act_exit.triggered.connect( parent.close )

        file_menu.addAction(act_exit)

        # ---------- 2.  Телеметрия -----------------------------------------
        tools_menu = self.addMenu("&Телеметрия")  # Alt+И

        act_logs          = QAction("Показать лог-файл",    self)
        act_logs.triggered.connect(getattr(parent, "show_logs", lambda: None))

        act_about = QAction("О программе...",  self)
        act_about.triggered.connect(lambda: AboutDialog(parent).exec())

        tools_menu.addActions([act_logs, act_about])

        # ---------- 3.  Справка ---------------------------------------------
        help_menu = self.addMenu("&Справка")       # Alt+С

        act_help  = QAction("Что это такое? (руководство по программе)",     self)
        act_help.triggered.connect(getattr(self, "open_info", lambda: None))

        help_menu.addAction(act_help)
        
    def open_info(self):
        """Opens the info website."""
        try:
            webbrowser.open(INFO_URL)
            self._set_status("Открываю руководство...")
        except Exception as e:
            error_msg = f"Ошибка при открытии руководства: {str(e)}"
            print(error_msg)
            self._set_status(error_msg)