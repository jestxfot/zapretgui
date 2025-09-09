# dpi/bat_start.py
import os
import time
import subprocess
from typing import Optional, Callable, Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from strategy_menu.strategy_manager import StrategyManager
    from main import LupiDPIApp

from log import log
from utils import run_hidden

class BatDPIStart:
    """Класс для запуска DPI. Отвечает только за BAT режим"""

    def __init__(self, winws_exe: str, status_callback: Optional[Callable[[str], None]] = None, 
                 ui_callback: Optional[Callable[[bool], None]] = None, 
                 app_instance: Optional['LupiDPIApp'] = None):
        """
        Инициализирует BatDPIStart.
        
        Args:
            winws_exe: Путь к исполняемому файлу winws.exe
            status_callback: Функция обратного вызова для отображения статуса
            ui_callback: Функция обратного вызова для обновления UI
            app_instance: Ссылка на главное приложение
        """
        self.winws_exe = winws_exe
        self.status_callback = status_callback
        self.ui_callback = ui_callback
        self.app_instance = app_instance
        self._idx: Optional[Dict[str, Any]] = None  # Кэш для index.json

    def _set_status(self, text: str) -> None:
        """Внутренний метод для установки статуса"""
        if self.status_callback:
            self.status_callback(text)

    def _update_ui(self, running: bool) -> None:
        """Внутренний метод для обновления UI"""
        if self.ui_callback:
            self.ui_callback(running)
    
    def set_status(self, text: str) -> None:
        """Отображает статусное сообщение."""
        if self.status_callback:
            self.status_callback(text)
        else:
            print(text)

    def check_process_running_wmi(self, silent: bool = False) -> bool:
        """Проверка через WMI - без окон консоли"""
        try:
            import win32com.client
            wmi = win32com.client.GetObject("winmgmts:")
            processes = wmi.ExecQuery("SELECT * FROM Win32_Process WHERE Name = 'winws.exe'")
            found = len(list(processes)) > 0
            if not silent:
                log(f"winws.exe state → {found}", "DEBUG")
            return found
        except Exception:
            # Fallback на tasklist если WMI недоступен
            return self.check_process_running(silent)
    
    def check_process_running(self, silent: bool = False) -> bool:
        """
        Мини-версия: только tasklist (хватает в 99% случаев).
        Никаких дополнительных окон не появляется.
        """
        cmd = ['C:\\Windows\\System32\\tasklist.exe', '/FI', 'IMAGENAME eq winws.exe', '/FO', 'CSV', '/NH']
        try:
            res = run_hidden(cmd, wait=True, capture_output=True,
                             text=True, encoding='cp866')
            found = 'winws.exe' in res.stdout
            if not silent:
                log(f"winws.exe state → {found}", "DEBUG")
            return found
        except Exception as e:
            if not silent:
                log(f"tasklist error: {e}", "⚠ WARNING")
            return False

    def cleanup_windivert_service(self) -> bool:
        """Очистка службы через PowerShell - без окон"""
        ps_script = """
        $service = Get-Service -Name windivert -ErrorAction SilentlyContinue
        if ($service) {
            Stop-Service -Name windivert -Force -ErrorAction SilentlyContinue
            Start-Sleep -Seconds 2
            sc.exe delete windivert | Out-Null
        }
        """
        
        try:
            run_hidden(
                ['C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe', 
                 '-WindowStyle', 'Hidden', '-NoProfile', '-Command', ps_script],
                wait=True
            )
            return True
        except Exception as e:
            log(f"Ошибка очистки службы: {e}", "⚠ WARNING")
            return True

    def stop_all_processes(self) -> bool:
        """Останавливает все процессы DPI"""
        stop_bat = os.path.join(os.path.dirname(self.winws_exe), 'stop.bat')
        if not os.path.isfile(stop_bat):
            log(f"stop.bat not found: {stop_bat}", "⚠ WARNING")
            return True

        log("Запускаем stop.bat …", "INFO")
        try:
            run_hidden(['C:\\Windows\\System32\\cmd.exe', '/Q', '/C', stop_bat], wait=True)
        except Exception as e:
            log(f"Ошибка stop.bat: {e}", "⚠ WARNING")

        time.sleep(0.5)
        ok = not self.check_process_running_wmi(silent=True)
        log("Все процессы остановлены" if ok else "winws.exe ещё работает",
            "✅ SUCCESS" if ok else "⚠ WARNING")
        return ok

    def _load_index(self, idx_path: str) -> Dict[str, Any]:
        """Загружает index.json с кэшированием"""
        if self._idx:
            return self._idx

        with open(idx_path, 'r', encoding='utf-8-sig') as f:
            import json
            self._idx = json.load(f)
        return self._idx

    def _get_strategy_manager(self) -> Optional['StrategyManager']:
        """Получает strategy_manager с правильной типизацией"""
        if not self.app_instance:
            return None
        
        if hasattr(self.app_instance, 'strategy_manager'):
            return self.app_instance.strategy_manager
        
        return None

    def start_dpi(self, selected_mode: Optional[Any] = None) -> bool:
        """
        Запускает DPI через BAT файлы.
        Для Direct режима используйте DPIController напрямую.
        """
        return self._start_dpi_bat(selected_mode)

    def _start_dpi_direct(self, selected_mode: Optional[Any]) -> bool:
        """Запускает DPI напрямую через StrategyRunner"""
        try:
            from strategy_menu.strategy_runner import get_strategy_runner
            
            runner = get_strategy_runner(self.winws_exe)
            
            log("Прямой запуск поддерживает только комбинированные стратегии", "ERROR")
            return False
            
        except Exception as e:
            log(f"Ошибка прямого запуска DPI: {e}", "❌ ERROR")
            return False
    
    def _start_dpi_bat(self, selected_mode: Optional[Any]) -> bool:
        """Старый метод запуска через .bat файлы"""
        try:
            log("======================== Start DPI (BAT) ========================", level="START")
            # Диагностика: выводим что передано в selected_mode
            log(f"selected_mode значение: {selected_mode}", "DEBUG")
            
            # Проверяем наличие BAT файлов
            from config import BAT_FOLDER
            bat_dir = BAT_FOLDER

            if os.path.exists(bat_dir):
                bat_files = [f for f in os.listdir(bat_dir) if f.endswith('.bat')]
                log(f"Найдено .bat файлов: {len(bat_files)}", "DEBUG")
                if len(bat_files) < 10:  # Если мало файлов, выведем список
                    log(f"Список .bat файлов: {bat_files}", "DEBUG")
            else:
                log(f"Папка bat не найдена: {bat_dir}", "⚠ WARNING")
            
            # Проверяем, запущен ли уже процесс
            if self.check_process_running_wmi(silent=True):
                log("Процесс winws.exe уже запущен, перезапускаем...", level="⚠ WARNING")
                if self.app_instance:
                    from dpi.stop import stop_dpi
                    stop_dpi(self.app_instance)
                time.sleep(2)
            
            # Определяем путь к .bat файлу
            bat_file: Optional[str] = None
            strategy_name = "Неизвестная стратегия"
            
            if selected_mode:
                if isinstance(selected_mode, dict):
                    # Передан словарь с информацией о стратегии из index.json
                    file_path = selected_mode.get('file_path')
                    strategy_name = selected_mode.get('name', 'Неизвестная стратегия')
                    
                    if file_path:
                        bat_file = os.path.join(BAT_FOLDER, file_path)
                        log(f"Используем file_path из словаря: {file_path}", "DEBUG")
                    else:
                        log("В словаре стратегии отсутствует file_path", "⚠ WARNING")
                        self.set_status("Ошибка: отсутствует file_path в информации о стратегии")
                        return False
                        
                elif isinstance(selected_mode, str):
                    # Передано имя стратегии - нужно найти file_path в index.json
                    strategy_name = selected_mode
                    log(f"Поиск file_path для стратегии: {strategy_name}", "DEBUG")
                    
                    # ✅ НОВЫЙ КОД - читаем напрямую из index.json
                    try:
                        from config import INDEXJSON_FOLDER
                        idx_path = os.path.join(INDEXJSON_FOLDER, 'index.json')
                        
                        if os.path.exists(idx_path):
                            with open(idx_path, 'r', encoding='utf-8-sig') as f:
                                import json
                                idx_data = json.load(f)
                            
                            # Ищем стратегию по имени
                            for sid, sinfo in idx_data.items():
                                if sinfo.get('name') == strategy_name:
                                    file_path = sinfo.get('file_path')
                                    if file_path:
                                        bat_file = os.path.join(BAT_FOLDER, file_path)
                                        log(f"Найден file_path для '{strategy_name}': {file_path}", "SUCCESS")
                                        break
                                    else:
                                        log(f"file_path отсутствует для стратегии {sid}", "WARNING")
                            
                            if not bat_file:
                                log(f"Стратегия '{strategy_name}' не найдена в index.json", "ERROR")
                                # Показываем первые несколько имен для отладки
                                names = [s.get('name', 'Unknown') for s in idx_data.values()][:5]
                                log(f"Примеры доступных стратегий: {names}", "DEBUG")
                        else:
                            log(f"index.json не найден: {idx_path}", "ERROR")
                            
                    except Exception as e:
                        log(f"Ошибка при чтении index.json: {e}", "ERROR")
                        
                    if not bat_file:
                        self.set_status(f"Стратегия '{strategy_name}' не найдена")
                        return False
            else:
                # Используем стратегию по умолчанию
                log("Используем стратегию по умолчанию", "DEBUG")
                
                # Получаем strategy_manager для поиска дефолтной стратегии
                strategy_manager = self._get_strategy_manager()
                
                if strategy_manager:
                    try:
                        strategies: Dict[str, Dict[str, Any]] = strategy_manager.get_strategies_list()
                        
                        # Ищем первую рекомендуемую стратегию
                        for sid, sinfo in strategies.items():
                            if sinfo.get('label') == 'recommended':
                                file_path = sinfo.get('file_path')
                                strategy_name = sinfo.get('name', 'Рекомендуемая стратегия')
                                if file_path:
                                    bat_file = os.path.join(BAT_FOLDER, file_path)
                                    log(f"Используем рекомендуемую стратегию: {strategy_name}", "INFO")
                                    break
                        
                        # Если не нашли рекомендуемую, берем первую доступную
                        if not bat_file and strategies:
                            first_strategy = next(iter(strategies.values()))
                            file_path = first_strategy.get('file_path')
                            strategy_name = first_strategy.get('name', 'Первая доступная')
                            if file_path:
                                bat_file = os.path.join(BAT_FOLDER, file_path)
                                log(f"Используем первую доступную стратегию: {strategy_name}", "INFO")
                    
                    except Exception as e:
                        log(f"Ошибка при поиске дефолтной стратегии: {e}", "❌ ERROR")
                
                # Fallback на хардкод
                if not bat_file:
                    bat_file = os.path.join(BAT_FOLDER, "original_bolvan_v2_badsum.bat")
                    strategy_name = "Fallback стратегия"
                    log(f"Используем fallback: {bat_file}", "⚠ WARNING")
            
            if not bat_file:
                log("Не удалось определить BAT файл для запуска", "❌ ERROR")
                self.set_status("Ошибка: не удалось определить файл стратегии")
                return False
            
            # Проверяем существование .bat файла
            log(f"Проверяем существование файла: {bat_file}", "DEBUG")
            if not os.path.exists(bat_file):
                log(f"BAT файл не найден: {bat_file}", level="❌ ERROR")
                self.set_status(f"Файл стратегии не найден: {os.path.basename(bat_file)}")
                
                # Пробуем скачать стратегию
                if self._try_download_strategy(bat_file, strategy_name):
                    log(f"Стратегия успешно скачана: {bat_file}", "✅ SUCCESS")
                else:
                    return False
            
            # Финальная проверка существования файла
            if not os.path.exists(bat_file):
                log(f"BAT файл все еще не существует: {bat_file}", "❌ ERROR")
                self.set_status("Критическая ошибка: файл стратегии недоступен")
                return False
            
            # Запускаем .bat файл
            return self._execute_bat_file(bat_file, strategy_name)
                
        except Exception as e:
            log(f"Критическая ошибка в _start_dpi_bat: {e}", level="❌ ERROR")
            self.set_status(f"Критическая ошибка: {e}")
            return False

    def _try_download_strategy(self, bat_file: str, strategy_name: str) -> bool:
        """Пытается скачать отсутствующую стратегию"""
        strategy_manager = self._get_strategy_manager()
        
        if not strategy_manager:
            log("strategy_manager недоступен для скачивания", "❌ ERROR")
            self.set_status("Не удалось получить доступ к менеджеру стратегий")
            return False
        
        try:
            self.set_status("Попытка скачать отсутствующую стратегию...")
            log("Пытаемся скачать отсутствующий BAT файл", "INFO")
            
            strategies: Dict[str, Dict[str, Any]] = strategy_manager.get_strategies_list()
            strategy_id: Optional[str] = None
            
            # Находим ID стратегии по file_path или имени
            target_filename = os.path.basename(bat_file)
            for sid, sinfo in strategies.items():
                if (sinfo.get('file_path') == target_filename or 
                    sinfo.get('name') == strategy_name):
                    strategy_id = sid
                    break
            
            if strategy_id:
                log(f"Найден ID стратегии для скачивания: {strategy_id}", "DEBUG")
                downloaded_path = strategy_manager.download_strategy(strategy_id)
                if downloaded_path and os.path.exists(downloaded_path):
                    return True
                else:
                    log("Скачивание стратегии не удалось", "❌ ERROR")
                    self.set_status("Не удалось скачать стратегию")
                    return False
            else:
                log(f"ID стратегии не найден для файла: {target_filename}", "❌ ERROR")
                self.set_status("Стратегия не найдена в списке для скачивания")
                return False
                
        except Exception as e:
            log(f"Ошибка при попытке скачать стратегию: {e}", "❌ ERROR")
            self.set_status(f"Ошибка скачивания: {e}")
            return False

    def _execute_bat_file(self, bat_file: str, strategy_name: str) -> bool:
        """Запуск через ShellExecuteEx"""
        self.set_status(f"Запуск стратегии: {strategy_name}")
        log(f"Запускаем BAT файл: {bat_file}", level="INFO")
        
        try:
            import ctypes
            from ctypes import wintypes, byref
            
            # Получаем абсолютный путь
            abs_bat_file = os.path.abspath(bat_file)
            
            # Структура SHELLEXECUTEINFO
            class SHELLEXECUTEINFO(ctypes.Structure):
                _fields_ = [
                    ("cbSize", wintypes.DWORD),
                    ("fMask", wintypes.ULONG),
                    ("hwnd", wintypes.HWND),
                    ("lpVerb", wintypes.LPCWSTR),
                    ("lpFile", wintypes.LPCWSTR),
                    ("lpParameters", wintypes.LPCWSTR),
                    ("lpDirectory", wintypes.LPCWSTR),
                    ("nShow", ctypes.c_int),
                    ("hInstApp", wintypes.HINSTANCE),
                    ("lpIDList", ctypes.c_void_p),
                    ("lpClass", wintypes.LPCWSTR),
                    ("hkeyClass", wintypes.HKEY),
                    ("dwHotKey", wintypes.DWORD),
                    ("hIcon", wintypes.HANDLE),
                    ("hProcess", wintypes.HANDLE)
                ]
            
            # Константы
            SEE_MASK_NOCLOSEPROCESS = 0x00000040
            SW_HIDE = 0
            
            # Заполняем структуру
            sei = SHELLEXECUTEINFO()
            sei.cbSize = ctypes.sizeof(SHELLEXECUTEINFO)
            sei.fMask = SEE_MASK_NOCLOSEPROCESS
            sei.hwnd = None
            sei.lpVerb = "open"
            sei.lpFile = abs_bat_file
            sei.lpParameters = None
            sei.lpDirectory = None
            sei.nShow = SW_HIDE
            
            # Запускаем
            shell32 = ctypes.windll.shell32
            result = shell32.ShellExecuteExW(byref(sei))
            
            if result:
                # Закрываем хэндл процесса
                if sei.hProcess:
                    ctypes.windll.kernel32.CloseHandle(sei.hProcess)
                log("BAT запущен через ShellExecuteEx", "DEBUG")
            else:
                log("Ошибка ShellExecuteEx", "ERROR")
                return False
            
            time.sleep(3)
            
            if self.check_process_running_wmi():
                log("DPI успешно запущен", level="✅ SUCCESS")
                self.set_status(f"DPI запущен: {strategy_name}")
                self._update_ui(True)
                return True
            else:
                log("Процесс winws.exe не запустился", level="❌ ERROR")
                return False
                
        except Exception as e:
            log(f"Ошибка при запуске: {e}", level="❌ ERROR")
            return False