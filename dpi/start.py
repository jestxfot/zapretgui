# dpi/start.py
import os
import time
import subprocess

from log import log
from utils import run_hidden # Импортируем нашу обертку для subprocess

class DPIStarter:
    """Класс для запуска и управления процессами DPI."""

    def _set_status(self, text: str):
        if self.status_callback:
            self.status_callback(text)

    def _update_ui(self, running: bool):
        if self.ui_callback:
            self.ui_callback(running)

    def __init__(self, winws_exe, status_callback=None, ui_callback=None):
        """
        Инициализирует DPIStarter.
        
        Args:
            winws_exe (str): Путь к исполняемому файлу winws.exe
            status_callback (callable): Функция обратного вызова для отображения статуса
        """
        self.winws_exe = winws_exe
        self.status_callback = status_callback
        self.ui_callback = ui_callback
        self._idx = None  # Кэш для index.json
    
    def set_status(self, text):
        """Отображает статусное сообщение."""
        if self.status_callback:
            self.status_callback(text)
        else:
            print(text)

    def check_process_running_wmi(self, silent=False) -> bool:
        """Проверка через WMI - без окон консоли"""
        try:
            import win32com.client
            wmi = win32com.client.GetObject("winmgmts:")
            processes = wmi.ExecQuery("SELECT * FROM Win32_Process WHERE Name = 'winws.exe'")
            found = len(list(processes)) > 0
            if not silent:
                log(f"winws.exe state → {found}", "DEBUG")
            return found
        except:
            # Fallback на tasklist если WMI недоступен
            return self.check_process_running_tasklist(silent)
    
    def check_process_running(self, silent=False) -> bool:
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

    # ==================================================================
    #  ЕДИНЫЙ ЗАПУСК Стратегии (.bat)   → self.start(...)
    # ==================================================================
    def cleanup_windivert_service(self):
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
                ['С:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe', '-WindowStyle', 'Hidden', '-NoProfile', '-Command', ps_script],
                wait=True
            )
            return True
        except Exception as e:
            log(f"Ошибка очистки службы: {e}", "⚠ WARNING")
            return True

    def stop_all_processes(self) -> bool:
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

    # -------------------------------------------------- запуск стратегии
    def _load_index(self, idx_path: str) -> dict:
        if self._idx:
            return self._idx

        with open(idx_path, 'r', encoding='utf-8-sig') as f:
            import json
            self._idx = json.load(f)
        return self._idx
            
    def start_dpi(self, selected_mode: str | None = None,
                delay_ms: int = 0) -> bool:
        """
        • выбирает .bat по имени/ID;  
        • останавливает предыдущий winws;  
        • запускает bat скрытно через VBS.
        """
        from config import BAT_FOLDER, INDEXJSON_FOLDER, DEFAULT_STRAT, get_last_strategy

        # ------------------------------------------------ выбор стратегии
        if not selected_mode:
            selected_mode = get_last_strategy() or DEFAULT_STRAT

        idx_file = os.path.join(INDEXJSON_FOLDER, 'index.json')
        try:
            strategies = self._load_index(idx_file)
        except Exception as e:
            log(f"index.json error: {e}", "⚠ WARNING")
            self._set_status("index.json повреждён")
            return False

        def resolve_bat(name: str) -> str | None:
            if name in strategies:
                return strategies[name].get('file_path')
            for info in strategies.values():
                if info.get('name', '').lower() == name.lower():
                    return info.get('file_path')
            if name.lower().endswith('.bat'):
                return name
            return None

        rel_bat = resolve_bat(selected_mode)
        if not rel_bat:
            self._set_status("Стратегия не найдена")
            return False

        bat_path = os.path.abspath(os.path.join(BAT_FOLDER, rel_bat))
        if not os.path.isfile(bat_path):
            self._set_status("Файл стратегии не найден")
            return False

        # ------------------------------------------------ запускаем (с задержкой?)
        def _do_start() -> bool:
            self._set_status("Запуск DPI…")
            if not self.stop_all_processes():
                self._set_status("Не удалось остановить старый процесс")
                return False

            log(f"RUN BAT → {bat_path}", "INFO")
            # ВАЖНО: Передаем команду как список ['cmd', '/c', bat_path]
            # Это предотвращает появление окон консоли
            try:
                # Передаем команду как список
                run_hidden(
                    ['C:\\Windows\\System32\\cmd.exe', '/c', bat_path],  # Правильный формат команды
                    cwd=BAT_FOLDER,
                    use_vbs_for_bat=True
                )
            except Exception as e:
                log(f"Ошибка запуска bat: {e}", "❌ ERROR")
                self._set_status(f"Ошибка запуска: {e}")
                return False

            # ждём пару секунд и проверяем
            for _ in range(10):
                if self.check_process_running_wmi(silent=True):
                    self._update_ui(True)
                    self._set_status("DPI запущен")
                    return True
                time.sleep(0.3)

            self._set_status("Не удалось запустить DPI")
            return False

        if delay_ms:
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(delay_ms, _do_start)
            return True
        return _do_start()