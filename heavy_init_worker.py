# heavy_init_worker.py

from PyQt6.QtCore import QObject, pyqtSignal
import traceback, os
from log import log

class HeavyInitWorker(QObject):
    """
    • preload_strategies   – сеть + JSON
    • download_files       – проверка/скачивание winws.exe
    Все Qt-объекты создаём ТОЛЬКО в GUI-потоке!
    """
    progress = pyqtSignal(str)            # для status-строки
    finished = pyqtSignal(bool, str)      # (ok, err_text)

    def __init__(self, dpi_starter, download_urls, parent=None):
        super().__init__(parent)
        self.dpi  = dpi_starter
        self.urls = download_urls

        # Уменьшаем таймауты для быстрого старта
        self.connection_timeout = 3    # было 10
        self.read_timeout = 10         # было 30
        self.max_retries = 1           # было 3

    def run(self):
        try:
            # Быстрая проверка сети перед загрузкой
            if not self._quick_connectivity_check():
                log("Нет интернета - пропускаем загрузку", "WARNING")
                self.progress.emit("Работаем в автономном режиме")
                self.finished.emit(True, "")
                return
            
        except Exception as e:
            log(f"Ошибка в HeavyInitWorker: {e}", "ERROR")
            self.finished.emit(False, str(e))

    def _quick_connectivity_check(self) -> bool:
        """Быстрая проверка доступности интернета"""
        try:
            import socket
            socket.setdefaulttimeout(2)
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("8.8.8.8", 53))
            return True
        except Exception:
            return False