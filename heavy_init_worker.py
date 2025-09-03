# heavy_init_worker.py

from PyQt6.QtCore import QObject, pyqtSignal
import traceback, os
from log import log

class HeavyInitWorker(QObject):
    """
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
            log("HeavyInitWorker.run() начал выполнение", "DEBUG")
            
            # Быстрая проверка сети перед загрузкой
            has_internet = self._quick_connectivity_check()
            if not has_internet:
                log("Нет интернета - работаем в автономном режиме", "⚠ WARNING")
                self.progress.emit("Работаем в автономном режиме")
            else:
                log("Интернет доступен, продолжаем инициализацию", "INFO")
            
            # 1. Проверка winws.exe (БЕЗ загрузки из интернета)
            self.progress.emit("Проверка winws.exe...")
            if not self._check_winws_exists():
                log("winws.exe не найден", "❌ ERROR")
                self.finished.emit(False, "winws.exe не найден в системе")
                return
            
            # 2. Загрузка ЛОКАЛЬНЫХ стратегий (БЕЗ интернета)
            self.progress.emit("Загрузка стратегий...")
            success = self._load_local_strategies()
            if not success:
                log("Не удалось загрузить локальные стратегии", "⚠ WARNING")
                # Не критично, продолжаем
            
            # 3. Обновление списка стратегий в UI
            self.progress.emit("Обновление списка стратегий...")
            
            # 4. Проверка дополнительных локальных ресурсов
            self.progress.emit("Загрузка ресурсов...")
            self._check_local_resources()
            
            # 5. Обновление ресурсов
            self.progress.emit("Обновление ресурсов...")
            
            # Финализация
            self.progress.emit("Инициализация завершена")
            log("HeavyInitWorker завершен успешно", "INFO")
            self.finished.emit(True, "")
            
        except Exception as e:
            error_msg = f"Ошибка в HeavyInitWorker: {e}"
            log(error_msg, "❌ ERROR")
            log(f"Traceback: {traceback.format_exc()}", "❌ ERROR")
            self.progress.emit(f"Ошибка: {e}")
            self.finished.emit(False, error_msg)

    def _check_winws_exists(self) -> bool:
        """Проверяет наличие winws.exe (БЕЗ загрузки)"""
        try:
            from config import WINWS_EXE
            
            if os.path.exists(WINWS_EXE):
                log(f"winws.exe найден: {WINWS_EXE}", "DEBUG")
                return True
            else:
                log(f"winws.exe НЕ найден по пути: {WINWS_EXE}", "❌ ERROR")
                return False
                
        except Exception as e:
            log(f"Ошибка при проверке winws.exe: {e}", "❌ ERROR")
            return False

    def _load_local_strategies(self) -> bool:
        """Загружает ТОЛЬКО локальные стратегии"""
        try:
            # Проверяем наличие локального index.json
            from config import INDEXJSON_FOLDER
            index_file = os.path.join(INDEXJSON_FOLDER, "index.json")
            
            if os.path.exists(index_file):
                log(f"Локальный index.json найден: {index_file}", "DEBUG")
                # Стратегии будут загружены через StrategyManager в основном потоке
                return True
            else:
                log("Локальный index.json не найден", "⚠ WARNING")
                return False
                
        except Exception as e:
            log(f"Ошибка при загрузке локальных стратегий: {e}", "❌ ERROR")
            return False

    def _check_local_resources(self):
        """Проверяет локальные ресурсы"""
        try:
            # Проверяем наличие папок и важных файлов
            from config import BAT_FOLDER
            
            folders_to_check = [
                ("BAT файлы", BAT_FOLDER)
            ]
            
            for name, folder in folders_to_check:
                if os.path.exists(folder):
                    file_count = len([f for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f))])
                    log(f"{name}: найдено {file_count} файлов", "DEBUG")
                else:
                    log(f"{name}: папка не найдена {folder}", "⚠ WARNING")
            
            log("Дополнительные ресурсы обработаны", "DEBUG")
            
        except Exception as e:
            log(f"Ошибка при проверке локальных ресурсов: {e}", "⚠ WARNING")
            # Не критично, продолжаем

    def _quick_connectivity_check(self) -> bool:
        """Быстрая проверка доступности интернета через urllib"""
        try:
            import urllib.request
            urllib.request.urlopen('https://www.google.com', timeout=3)
            log("Интернет-соединение доступно", "DEBUG")
            return True
        except Exception as e:
            log(f"Интернет недоступен: {e}", "DEBUG")
            return False