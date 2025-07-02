# autostart_menu.py
# -------------------------------------------------------------
# Диалог «Настройка автозапуска» –
# даёт выбрать, что именно будет запускаться автоматически:
#   1) само GUI-приложение
#   2) выбранная стратегия (.bat)
#
# Изменения 24.06.2025:
#   • В enable_strategy_autostart передаём ПОЛНЫЙ путь к
#     ...\json\index.json, а не каталог json_folder.
# -------------------------------------------------------------

from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QPushButton,
    QLabel,
    QMessageBox,
)

from .autostart_exe      import setup_autostart_for_exe
from .autostart_strategy import setup_autostart_for_strategy
from .autostart_service  import setup_service_for_strategy
from log                 import log


class AutoStartMenu(QDialog):
    """
    Мини-диалог с двумя кнопками:
        1. Автозапуск главного приложения
        2. Автозапуск выбранной стратегии (.bat)

    Параметры
    ---------
    parent : QWidget | None
        Окно-родитель.
    strategy_name : str
        Имя выбранной пользователем стратегии.
    bat_folder : str
        Каталог, где лежат .bat-файлы стратегий.
    json_folder : str
        Каталог, в котором находится index.json (конкретно файл лежит
        по пути  <json_folder>/index.json).
    check_autostart_cb : Callable[[], bool]
        Колбэк: возвращает True, если автозапуск включён.
    update_ui_cb : Callable[[bool], None]
        Обновить внешний интерфейс (поставить/снять галочку и пр.).
    status_cb : Callable[[str], None]
        Вывести строку статуса в главное окно.
    """

    # ----------------------------------------------------------
    # Конструктор
    # ----------------------------------------------------------
    def __init__(
        self,
        parent,
        strategy_name: str,
        bat_folder: str,
        json_folder: str,
        check_autostart_cb,
        update_ui_cb,
        status_cb,
    ):
        super().__init__(parent)
        self.setWindowTitle("Настройка автозапуска")

        # ---- сохранённые параметры ---------------------------------
        self.strategy_name   = strategy_name
        self.bat_folder      = bat_folder
        self.json_folder     = json_folder
        self.check_autostart = check_autostart_cb
        self.update_ui       = update_ui_cb
        self.status          = status_cb

        # ---- UI -----------------------------------------------------
        layout = QVBoxLayout(self)

        info = QLabel(
            "Выберите, что именно должно\n"
            "автоматически стартовать при входе в Windows:"
        )
        layout.addWidget(info)

        self.exe_btn = QPushButton("Автозапуск GUI-приложения")
        self.bat_btn = QPushButton("Автозапуск выбранной стратегии (планировщик .bat)")
        self.svc_btn = QPushButton("Автозапуск выбранной стратегии (служка .bat)")

        layout.addWidget(self.exe_btn)
        layout.addWidget(self.bat_btn)
        layout.addWidget(self.svc_btn)

        self.exe_btn.clicked.connect(self.enable_exe_autostart)
        self.bat_btn.clicked.connect(self.enable_strategy_autostart)
        self.svc_btn.clicked.connect(self.enable_strategy_service)

    # ==========================================================
    # 1. Автозапуск главного приложения
    # ==========================================================
    def enable_exe_autostart(self):
        log("Включаем автозапуск GUI", "INFO")

        ok = setup_autostart_for_exe(
            selected_mode=self.strategy_name,
            status_cb=self.status,
        )

        if ok:
            self.status("Автозапуск GUI настроен")
            self.update_ui(True)
            QMessageBox.information(
                self,
                "Успех",
                "Автозапуск главного приложения настроен",
            )
            self.accept()
        else:
            QMessageBox.critical(
                self,
                "Ошибка",
                "Не удалось настроить автозапуск.\nСм. журнал.",
            )

    # ==========================================================
    # 2. Автозапуск выбранной стратегии (.bat)
    # ==========================================================
    def enable_strategy_autostart(self):
        log("Включаем автозапуск стратегии", "INFO")

        # ------------------------------------------------------
        # Колбэк: вывод подробного сообщения, если schtasks
        # вернёт ошибку.
        # ------------------------------------------------------
        def _show_error(msg: str):
            QMessageBox.critical(self, "Автозапуск стратегии", msg)

        # ------------------------------------------------------
        # Ключевой момент: формируем путь ИМЕННО К ФАЙЛУ,
        # а не к каталогу json_folder.
        # ------------------------------------------------------
        index_json_path = (Path(self.json_folder) / "index.json").resolve()
        log(f"[DEBUG] Передаём index_path: {index_json_path}", "DEBUG")

        ok = setup_autostart_for_strategy(
            selected_mode=self.strategy_name,
            bat_folder=self.bat_folder,
            index_path=str(index_json_path),   # ← полный путь к index.json
            ui_error_cb=_show_error,
        )

        if ok:
            self.status("Автозапуск стратегии настроен")
            self.update_ui(True)
            QMessageBox.information(
                self,
                "Успех",
                f"Стратегия «{self.strategy_name}» будет "
                f"запускаться автоматически",
            )
            self.accept()
        # Если ok == False, подробное окно уже показано в _show_error


    # ==========================================================
    # 3. Стратегия в виде службы Windows
    # ==========================================================
    def enable_strategy_service(self):
        log("Создаём/обновляем службу для стратегии", "INFO")

        def _show_error(msg: str):
            QMessageBox.critical(self, "Служба стратегии", msg)

        index_json_path = (Path(self.json_folder) / "index.json").resolve()
        log(f"[DEBUG] Service: index_path = {index_json_path}", "DEBUG")

        ok = setup_service_for_strategy(
            selected_mode=self.strategy_name,
            bat_folder=self.bat_folder,
            index_path=str(index_json_path),
            ui_error_cb=_show_error,
        )

        if ok:
            self.status("Служба стратегии настроена")
            self.update_ui(True)
            QMessageBox.information(
                self,
                "Успех",
                f"Стратегия «{self.strategy_name}» будет "
                f"запускаться как служба Windows",
            )
            self.accept()