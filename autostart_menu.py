from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QPushButton, QLabel, QMessageBox
)
from autostart_exe      import setup_autostart_for_exe
from autostart_strategy import setup_autostart_for_strategy
from log                import log

BIN_FOLDER = None  # если хотите, можете импортировать из config прямо здесь


class AutoStartMenu(QDialog):
    """
    Мини-диалог с двумя кнопками:
        1. Автозапуск главного приложения
        2. Автозапуск выбранной стратегии (.bat)

    parent               – окно-родитель
    strategy_name        – текущее имя стратегии (label text)
    bin_folder           – каталог bin c .bat и index.json
    check_autostart_cb() – сообщает, включён ли автозапуск (True/False)
    update_ui_cb()       – обновляет интерфейс после успеха
    status_cb(msg)       – выводит строку статуса
    """

    def __init__(self,
                 parent,
                 strategy_name: str,
                 bin_folder: str,
                 check_autostart_cb,
                 update_ui_cb,
                 status_cb):

        super().__init__(parent)
        self.setWindowTitle("Настройка автозапуска")
        self.strategy_name     = strategy_name
        self.bin_folder        = bin_folder
        self.check_autostart   = check_autostart_cb
        self.update_ui         = update_ui_cb
        self.status            = status_cb

        # ---------------- UI ----------------
        layout = QVBoxLayout(self)

        info = QLabel(
            "Выберите, что именно должно\nавтоматически стартовать при входе "
            "в Windows:"
        )
        layout.addWidget(info)

        self.exe_btn = QPushButton("Автозапуск GUI-приложения")
        self.bat_btn = QPushButton("Автозапуск выбранной стратегии (.bat)")

        layout.addWidget(self.exe_btn)
        layout.addWidget(self.bat_btn)

        self.exe_btn.clicked.connect(self.enable_exe_autostart)
        self.bat_btn.clicked.connect(self.enable_strategy_autostart)

    # ------------------------------------------------------------------
    # 1. Главное приложение
    # ------------------------------------------------------------------
    def enable_exe_autostart(self):
        log("Включаем автозапуск GUI", "INFO")
        ok = setup_autostart_for_exe(
            selected_mode=self.strategy_name,
            status_cb=self.status
        )
        if ok:
            self.status("Автозапуск GUI настроен")
            self.update_ui(True)
            QMessageBox.information(self, "Успех",
                                    "Автозапуск главного приложения настроен")
            self.accept()
        else:
            QMessageBox.critical(self, "Ошибка",
                                 "Не удалось настроить автозапуск.\nСм. журнал.")

    # ------------------------------------------------------------------
    # 2. BAT-файл стратегии
    # ------------------------------------------------------------------
    def enable_strategy_autostart(self):
        log("Включаем автозапуск стратегии", "INFO")
        ok = setup_autostart_for_strategy(
            selected_mode=self.strategy_name,
            bin_folder=self.bin_folder
        )
        if ok:
            self.status("Автозапуск стратегии настроен")
            self.update_ui(True)
            QMessageBox.information(
                self, "Успех",
                f"Стратегия «{self.strategy_name}» будет запускаться автоматически"
            )
            self.accept()
        else:
            QMessageBox.critical(self, "Ошибка",
                "Не удалось настроить автозапуск стратегии.\nСм. журнал.")