# heavy_init_worker.py

from PyQt5.QtCore import QObject, pyqtSignal
import traceback, os

class HeavyInitWorker(QObject):
    """
    • preload_strategies   – сеть + JSON
    • download_files       – проверка/скачивание winws.exe
    Все Qt-объекты создаём ТОЛЬКО в GUI-потоке!
    """
    progress = pyqtSignal(str)            # для status-строки
    finished = pyqtSignal(bool, str)      # (ok, err_text)

    def __init__(self, strategy_manager, dpi_starter, download_urls):
        super().__init__()
        self.sm   = strategy_manager
        self.dpi  = dpi_starter
        self.urls = download_urls

    def run(self):
        try:
            self.progress.emit("Загрузка списка стратегий…")
            self.sm.preload_strategies()               # сеть, JSON

            self.progress.emit("Проверка winws.exe…")
            self.dpi.download_files(self.urls)         # SHA / download

            self.finished.emit(True, "")
        except Exception as e:
            from log import log
            err = f"{e}\n{traceback.format_exc()}"
            log(err, "ERROR")
            self.finished.emit(False, err)