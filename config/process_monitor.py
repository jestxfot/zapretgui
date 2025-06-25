from PyQt6.QtCore import QThread, pyqtSignal


class ProcessMonitorThread(QThread):
    """
    Следит за процессом winws.exe и шлёт сигнал,
    когда его состояние (запущен/остановлен) изменилось.
    """
    processStatusChanged = pyqtSignal(bool)          # True / False

    def __init__(self, dpi_starter, interval_ms: int = 2000):
        super().__init__()
        self.dpi_starter   = dpi_starter
        self.interval_ms   = interval_ms
        self._running      = True
        self._cur_state: bool | None = None

    # ------------------------- ОСНОВНОЙ ЦИКЛ --------------------------
    def run(self):
        from log import log            # импорт здесь, чтобы не было циклических импортов
        log("Process-monitor thread started", level="INFO")

        while self._running:
            try:
                is_running = self.dpi_starter.check_process_running(silent=True)

                # Если состояние изменилось — отдаём сигнал в GUI
                if is_running != self._cur_state:
                    self._cur_state = is_running
                    log(f"winws.exe state → {is_running}", level="DEBUG")
                    self.processStatusChanged.emit(is_running)

            except Exception as e:
                from log import log
                log(f"Ошибка в потоке мониторинга: {e}", level="❌ ERROR")

            self.msleep(self.interval_ms)            # 2 сек.

    # ------------------------ СТАНДАРТНЫЙ STOP ------------------------
    def stop(self):
        self._running = False
        self.wait()           # корректно ждём завершения run()