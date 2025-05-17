# app_menubar.py
from PyQt6.QtWidgets import QMenuBar, QWidget, QMessageBox
from PyQt6.QtGui     import QAction
from config import APP_VERSION
from urls import INFO_URL

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
        file_menu.addAction(act_exit)

        # ---------- 2.  Инструменты -----------------------------------------
        tools_menu = self.addMenu("&Инструменты")  # Alt+И

        act_update_other = QAction("Обновить other.txt", self)
        act_logs          = QAction("Показать лог-файл",    self)
        tools_menu.addActions([act_update_other, act_logs])

        # ---------- 3.  Справка ---------------------------------------------
        help_menu = self.addMenu("&Справка")       # Alt+С

        act_help  = QAction("Что это такое? (руководство по программе)",     self)
        act_about = QAction("О программе...",  self)
        help_menu.addActions([act_help, act_about])

        act_about.triggered.connect(
            lambda: QMessageBox.about(
                parent,
                "О программе",
                f"Zapret\nВерсия: {APP_VERSION}"
            )
        )

        # ---------- Подключаем действия к методам главного окна -------------
        #  (специально через getattr → если метода нет, меню всё равно
        #   будет создаваться без ошибок)

        act_exit.triggered.connect( parent.close )

        act_update_other.triggered.connect(
            getattr(parent, "update_other_list", lambda: None))

        act_logs.triggered.connect(
            getattr(parent, "show_logs", lambda: None))

        act_help.triggered.connect(
            getattr(self, "open_info", lambda: None))
        
    def open_info(self):
        """Opens the info website."""
        try:
            webbrowser.open(INFO_URL)
            self._set_status("Открываю руководство...")
        except Exception as e:
            error_msg = f"Ошибка при открытии руководства: {str(e)}"
            print(error_msg)
            self._set_status(error_msg)