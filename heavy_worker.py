# heavy_worker.py

from PyQt6.QtCore import QObject, pyqtSignal
import traceback

class HeavyWorker(QObject):
    progress = pyqtSignal(str)            # текст для status_bar
    finished = pyqtSignal(bool, str)      # ok, err_text

    def __init__(self, strategy_manager, dpi_starter, download_urls):
        super().__init__()
        self.sm   = strategy_manager
        self.dpi  = dpi_starter
        self.urls = download_urls

    def run(self):
        from log import log
        try:
            self.progress.emit("Загрузка списка стратегий…")
            self.sm.preload_strategies()          # сеть + JSON

            self.progress.emit("Проверка winws.exe…")
            self.dpi.download_files(self.urls)    # SHA/скачивание

            self.progress.emit("Инициализация завершена")
            self.finished.emit(True, "")
        except Exception as e:
            err = f"{e}\n{traceback.format_exc()}"
            log(err, "ERROR")
            self.finished.emit(False, err)