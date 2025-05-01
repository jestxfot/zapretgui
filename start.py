import os
import time
import subprocess
import win32con, sys

from PyQt5.QtWidgets import QApplication

from log import log

class DPIStarter:
    """Класс для запуска и управления процессами DPI."""

    def _set_status(self, text: str):
        if self.status_callback:
            self.status_callback(text)

    def _update_ui(self, running: bool):
        if self.ui_callback:
            self.ui_callback(running)

    def __init__(self, winws_exe, bin_folder, lists_folder, status_callback=None, ui_callback=None):
        """
        Инициализирует DPIStarter.
        
        Args:
            winws_exe (str): Путь к исполняемому файлу winws.exe
            bin_folder (str): Путь к папке с бинарными файлами
            lists_folder (str): Путь к папке со списками
            status_callback (callable): Функция обратного вызова для отображения статуса
        """
        self.winws_exe = winws_exe
        self.bin_folder = bin_folder
        self.lists_folder = lists_folder
        self.status_callback = status_callback
        self.ui_callback = ui_callback
    
    def set_status(self, text):
        """Отображает статусное сообщение."""
        if self.status_callback:
            self.status_callback(text)
        else:
            print(text)
    
    def download_files(self, download_urls):
        """
        Скачивает необходимые файлы.
        
        Args:
            download_urls (dict): Словарь с URL для скачивания
        
        Returns:
            bool: True при успешном скачивании, False при ошибке
        """
        # Эта функция может вызывать внешний загрузчик
        # или иметь собственную реализацию загрузки файлов
        from downloader import download_files
        return download_files(
            bin_folder=self.bin_folder,
            lists_folder=self.lists_folder,
            download_urls=download_urls,
            status_callback=self.set_status
        )
    
    def check_process_running(self, silent=False):
        import re
        """Проверяет, запущен ли процесс winws.exe"""
        try:
            # Метод 1: Проверка через tasklist (самый быстрый)
            if not silent:
                log("=================== check_process_running ==========================", level="START")
                log("Метод 1: Проверка через tasklist", level="START")
            
            result = subprocess.run(
                'tasklist /FI "IMAGENAME eq winws.exe" /FO CSV /NH', 
                shell=True, 
                capture_output=True, 
                text=True
            )
            
            if "winws.exe" in result.stdout:
                # Извлекаем PID процесса
                pid_match = re.search(r'"winws\.exe","(\d+)"', result.stdout)
                if pid_match:
                    pid = pid_match.group(1)
                    if not silent:
                        log(f"Найден PID процесса: {pid}", level="START")
                    return True
                
                log("Процесс найден, но не удалось определить PID", level="START")
                return True  # Процесс найден, даже если мы не смогли извлечь PID
            
            if not silent:
                # Метод 2: Проверка через PowerShell (работает лучше на некоторых системах)
                log("Метод 2: Проверка через PowerShell", level="START")
                try:
                    ps_cmd = 'powershell -Command "Get-Process -Name winws -ErrorAction SilentlyContinue | Select-Object Id"'
                    ps_result = subprocess.run(
                        ps_cmd,
                        shell=True,
                        capture_output=True,
                        text=True,
                        encoding='cp866'
                    )
                    
                    log(f"Результат PowerShell: {ps_result.stdout.strip()}", level="START")
                    
                    # Если есть любая строка, содержащая число после Id
                    if any(line.strip().isdigit() for line in ps_result.stdout.split('\n') if line.strip()):
                        log("Процесс winws.exe найден через PowerShell", level="START")
                        return True
                except Exception as ps_error:
                    log(f"Ошибка при проверке через PowerShell: {str(ps_error)}", level="START")
                
                # Метод 3: Проверка через wmic (работает даже на старых системах)
                log("Метод 3: Проверка через wmic", level="START")
                try:
                    wmic_result = subprocess.run(
                        'wmic process where "name=\'winws.exe\'" get processid',
                        shell=True,
                        capture_output=True,
                        text=True,
                        encoding='cp866'
                    )
                    
                    log(f"Результат wmic: {wmic_result.stdout.strip()}", level="START")
                    
                    lines = [line.strip() for line in wmic_result.stdout.split('\n') if line.strip()]
                    # Проверяем есть ли более одной строки (заголовок + данные)
                    if len(lines) > 1:
                        log("Процесс winws.exe найден через wmic", level="START")
                        return True
                except Exception as wmic_error:
                    log(f"Ошибка при проверке через wmic: {str(wmic_error)}", level="START")
                    
                # Метод 4: Проверка через простую команду findstr
                log("Метод 4: Проверка через tasklist и findstr", level="START")
                try:
                    findstr_result = subprocess.run(
                        'tasklist | findstr "winws"',
                        shell=True,
                        capture_output=True,
                        text=True,
                        encoding='cp866'
                    )
                    
                    log(f"Результат findstr: {findstr_result.stdout.strip()}", level="START")
                    
                    if findstr_result.stdout.strip():
                        log("Процесс winws.exe найден через findstr", level="START")
                        return True
                except Exception as findstr_error:
                    log(f"Ошибка при проверке через findstr: {str(findstr_error)}", level="START")
                
                # Проверка существования файла блокировки
                # Некоторые процессы создают файлы блокировки, которые можно проверить
                try:
                    lock_file = os.path.join(os.path.dirname(self.winws_exe), "winws.lock")
                    if os.path.exists(lock_file):
                        log(f"Найден файл блокировки {lock_file}, процесс запущен", level="START")
                        return True
                except Exception as lock_error:
                    log(f"Ошибка при проверке файла блокировки: {str(lock_error)}", level="START")
            
                # Если все методы не нашли процесс
                log("Процесс winws.exe НЕ найден ни одним из методов", level="START")
            return False
            
        except Exception as e:
            log(f"Общая ошибка при проверке статуса процесса: {str(e)}", level="START")
            return False

    # ==================================================================
    #  ЕДИНЫЙ ЗАПУСК Стратегии (.bat)   → self.start(...)
    # ==================================================================
    def start_dpi(self, selected_mode: str | None = None, delay_ms: int = 0) -> bool:
        """
        Запускает выбранный .bat скрыто.
        selected_mode может быть:
            • ID из index.json
            • «красивым» Name из index.json
            • имя .bat
            • None → берём get_last_strategy() или дефолт
        delay_ms – задержка в мс (0 = сразу)
        """
        from log import log
        from PyQt5.QtCore import QTimer
        import json, os, subprocess

        DEFAULT_STRAT = "Оригинальная bol-van v2 (07.04.2025)"
        BIN_DIR       = self.bin_folder

        # -------- 0. Какая стратегия? -------------------------------------
        if not selected_mode:
            try:
                from main import get_last_strategy     # где-то в проекте
                selected_mode = get_last_strategy()
            except Exception:
                selected_mode = None
        if not selected_mode:
            selected_mode = DEFAULT_STRAT

        # -------- 1. Загружаем / кэшируем index.json -----------------------
        try:
            if not hasattr(self, "_idx"):
                with open(os.path.join(BIN_DIR, "index.json"), "r", encoding="utf-8") as f:
                    self._idx = json.load(f)
        except Exception as e:
            log(f"[DPIStarter] index.json error: {e}", level="ERROR")
            self._set_status("index.json не найден")
            return False
        strategies = self._idx

        # -------- 2. Сопоставляем → .bat ----------------------------------
        def _resolve_bat(name: str) -> str | None:
            if name in strategies:
                return strategies[name].get("file_path")
            # поиск по Name
            for info in strategies.values():
                if info.get("name", "").strip().lower() == name.strip().lower():
                    return info.get("file_path")
            # пользователь ввёл *.bat
            if name.lower().endswith(".bat"):
                return name
            return None

        bat_rel = _resolve_bat(selected_mode)
        if not bat_rel:
            log(f"[DPIStarter] не найден .bat для '{selected_mode}'", level="ERROR")
            self._set_status("Ошибка: стратегия не найдена")
            return False

        # убираем дублирующий «bin\\»
        while bat_rel.lower().startswith(("bin\\", "bin/")):
            bat_rel = bat_rel[4:]
        bat_path = os.path.normpath(os.path.join(BIN_DIR, bat_rel))

        if not os.path.isfile(bat_path):
            log(f"[DPIStarter] файл не найден: {bat_path}", level="ERROR")
            self._set_status("Ошибка: файл стратегии не найден")
            return False

        # -------- 3. Внутренняя функция реального запуска -----------------
        def _do_start() -> bool:
            try:
                abs_bat = os.path.abspath(bat_path)          # гарантируем абсолютный
                cmd = ["cmd", "/c", abs_bat]                 # ← подставляем его
                log(f"[DPIStarter] RUN: {' '.join(cmd)} (hidden)", level="INFO")

                subprocess.Popen(
                        cmd,
                        cwd=os.path.dirname(abs_bat),        # можно BIN_DIR; главное – верный bat
                        creationflags=0x08000000)
                self._set_status(f"Запущена стратегия: {selected_mode}")
                
                # Даем процессу время запуститься
                time.sleep(1)
                
                # Теперь проверяем PID запущенного процесса
                try:
                    result = subprocess.run(
                        'tasklist /FI "IMAGENAME eq winws.exe" /FO CSV /NH', 
                        shell=True, 
                        capture_output=True, 
                        text=True
                    )
                    
                    pid = "неизвестен"
                    import re
                    pid_match = re.search(r'"winws\.exe","(\d+)"', result.stdout)
                    if pid_match:
                        pid = pid_match.group(1)
                        log(f"[DPIStarter] Определен PID процесса winws.exe: {pid}", level="INFO")
                except Exception as pid_err:
                    log(f"[DPIStarter] Не удалось определить PID: {pid_err}", level="WARNING")
                    pid = "неизвестен"

                log(f"[DPIStarter] Запущена стратегия: {selected_mode}, PID: {pid}", level="INFO")
                self._update_ui(True)
                return True
            except Exception as e:
                log(f"[DPIStarter] ошибка запуска: {e}", level="ERROR")
                self._set_status(f"Ошибка запуска: {e}")
                return False

        # -------- 4. Запускаем сразу или с задержкой ----------------------
        if delay_ms > 0:
            QTimer.singleShot(delay_ms, _do_start)
            log(f"[DPIStarter] запуск отложен на {delay_ms} мс", level="DEBUG")
            return True
        return _do_start()

    def start_strategy(self, strategy_path):
        """
        Запускает стратегию через BAT-файл.
        
        Args:
            strategy_path (str): Путь к BAT-файлу стратегии
            
        Returns:
            bool: True при успешном запуске, False при ошибке
        """
        try:
            log(f"======================== Запуск стратегии ========================", level="INFO")
            self.set_status("Подготовка запуска...")

            # Проверяем, существует ли BAT-файл
            if not os.path.exists(strategy_path) or not strategy_path.lower().endswith('.bat'):
                log(f"Ошибка: BAT-файл не найден или неверный формат: {strategy_path}", level="ERROR")
                self.set_status(f"Ошибка: BAT-файл не найден")
                return False
            
            abs_path = os.path.abspath(strategy_path)
            working_dir = os.path.dirname(abs_path)
            log(f"Запуск BAT-файла: {abs_path}", level="INFO")
            
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = win32con.SW_HIDE
            
            subprocess.Popen(
                abs_path,
                startupinfo=startupinfo,
                cwd=working_dir,
                shell=True
            )
            
            time.sleep(0.3)
            
            if self.check_process_running():
                self.set_status(f"Стратегия успешно запущена")
                log(f"winws.exe успешно запущен", level="INFO")
                return True
            else:
                # Даем еще время (особенно для BAT через VBS)
                time.sleep(1.5)
                if self.check_process_running():
                    self.set_status(f"Стратегия успешно запущена")
                    log(f"winws.exe успешно запущен после дополнительного ожидания", level="INFO")
                    return True
                else:
                    log(f"winws.exe не запущен", level="ERROR")
                    self.set_status(f"Ошибка: winws.exe не запущен")
                    return False
                    
        except Exception as e:
            log(f"Ошибка при запуске стратегии: {str(e)}", level="ERROR")
            self.set_status(f"Ошибка при запуске стратегии: {str(e)}")
            return False

    def ensure_directories_exist(self):
        """Проверяет и создает необходимые директории.
        
        Returns:
            bool: True при успешном создании директорий
        """
        try:
            for folder in [self.bin_folder, self.lists_folder]:
                if not os.path.exists(folder):
                    os.makedirs(folder, exist_ok=True)
                    self.set_status(f"Создана папка {folder}")
                    log(f"Создана папка {folder}")
            return True
        except Exception as e:
            log(f"Ошибка при создании директорий: {str(e)}", level="ERROR")
            return False

    def ensure_executable_exists(self, download_urls=None):
        """Проверяет наличие исполняемого файла и скачивает при необходимости.
        
        Args:
            download_urls (dict, optional): URL для скачивания файлов, если они отсутствуют
            
        Returns:
            bool: True если файл существует или успешно скачан, False в противном случае
            
        Raises:
            FileNotFoundError: Если файл не найден и не может быть скачан
        """
        exe_path = os.path.abspath(self.winws_exe)
        if not os.path.exists(exe_path):
            if download_urls and self.download_files(download_urls):
                self.set_status("Необходимые файлы скачаны")
                log(f"Необходимые файлы скачаны", level="START")
                return True
            else:
                log(f"Файл {exe_path} не найден и не может быть скачан", level="START")
                raise FileNotFoundError(f"Файл {exe_path} не найден и не может быть скачан")
        return True