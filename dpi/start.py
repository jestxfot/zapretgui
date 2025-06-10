import os
import time
import subprocess

from log import log

class DPIStarter:
    """Класс для запуска и управления процессами DPI."""

    def _set_status(self, text: str):
        if self.status_callback:
            self.status_callback(text)

    def _update_ui(self, running: bool):
        if self.ui_callback:
            self.ui_callback(running)

    def __init__(self, winws_exe, bin_folder, status_callback=None, ui_callback=None):
        """
        Инициализирует DPIStarter.
        
        Args:
            winws_exe (str): Путь к исполняемому файлу winws.exe
            bin_folder (str): Путь к папке с бинарными файлами
            status_callback (callable): Функция обратного вызова для отображения статуса
        """
        self.winws_exe = winws_exe
        self.bin_folder = bin_folder
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
        from PyQt6.QtCore import QTimer
        import json, os, subprocess

        DEFAULT_STRAT = "Оригинальная bol-van v2 (07.04.2025)"
        BIN_DIR       = self.bin_folder

        # Добавим отладку путей
        log(f"[DPIStarter] BIN_DIR: {BIN_DIR}", level="DEBUG")
        log(f"[DPIStarter] Проверяем существование папки: {os.path.exists(BIN_DIR)}", level="DEBUG")
        
        index_path = os.path.join(BIN_DIR, "index.json")
        log(f"[DPIStarter] Полный путь к index.json: {index_path}", level="DEBUG")
        log(f"[DPIStarter] Файл index.json существует: {os.path.exists(index_path)}", level="DEBUG")


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
                # Если index.json отсутствует, попробуем его скачать
                if not os.path.exists(index_path):
                    log(f"[DPIStarter] index.json не найден, пытаемся скачать...", level="WARNING")
                    try:
                        from strategy_menu.manager import StrategyManager
                        from config.config import GITHUB_STRATEGIES_BASE_URL, GITHUB_STRATEGIES_JSON_URL
                        
                        manager = StrategyManager(
                            base_url=GITHUB_STRATEGIES_BASE_URL,
                            local_dir=BIN_DIR,
                            json_url=GITHUB_STRATEGIES_JSON_URL,
                            status_callback=self._set_status
                        )
                        
                        # Принудительно скачиваем индекс
                        strategies = manager.get_strategies_list(force_update=True)
                        if strategies:
                            log(f"[DPIStarter] index.json успешно скачан", level="INFO")
                        else:
                            raise Exception("Пустой список стратегий")
                            
                    except Exception as download_error:
                        log(f"[DPIStarter] Не удалось скачать index.json: {download_error}", level="ERROR")
                        self._set_status("Ошибка: не удалось загрузить список стратегий")
                        return False
                
                with open(index_path, "r", encoding="utf-8") as f:
                    self._idx = json.load(f)
                    
        except Exception as e:
            log(f"[DPIStarter] index.json error: {e}", level="ERROR")
            log(f"[DPIStarter] Содержимое папки bin: {os.listdir(BIN_DIR) if os.path.exists(BIN_DIR) else 'папка не существует'}", level="ERROR")
            self._set_status("index.json не найден и не удалось скачать")
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
                # -----------------------------------------------------------
                # 1. Стартуем .bat
                # -----------------------------------------------------------
                abs_bat = os.path.abspath(bat_path)          # гарантируем абсолютный путь
                cmd     = ["cmd", "/c", abs_bat]
                log(f"[DPIStarter] RUN: {' '.join(cmd)} (hidden)", level="INFO")

                subprocess.Popen(
                    cmd,
                    cwd=os.path.dirname(abs_bat),            # важна правильная папка запуска
                    creationflags=0x0800_0000)               # CREATE_NO_WINDOW
                log(f"[DPIStarter] Запущена стратегия: {selected_mode}", level="INFO")

                # даём процессу время появиться в списке
                time.sleep(1)

                # -----------------------------------------------------------
                # 2. Пытаемся найти PID процесса winws.exe
                # -----------------------------------------------------------
                pid     = "неизвестен"
                result  = subprocess.run(
                    r'tasklist /FI "IMAGENAME eq winws.exe" /FO CSV /NH',
                    shell=True, capture_output=True, text=True
                )

                if result.returncode != 0:
                    # tasklist вернул ошибку (маловероятно, но бывает)
                    log(f"[DPIStarter] tasklist завершился с кодом {result.returncode}: "
                        f"{result.stderr.strip()}", level="WARNING")

                else:
                    # tasklist отработал успешно — смотрим вывод
                    if '"winws.exe"' in result.stdout:
                        # процесс найден, вытаскиваем PID
                        import re
                        m = re.search(r'"winws\.exe","(\d+)"', result.stdout)
                        if m:
                            pid = m.group(1)
                            log(f"[DPIStarter] Определён PID процесса winws.exe: {pid}", level="INFO")
                        else:
                            # имя есть, а PID не смогли вытащить (редкая ситуация)
                            log("[DPIStarter] Не удалось извлечь PID из вывода tasklist", level="WARNING")
                    else:
                        # в выводе нет строки с winws.exe
                        log("[DPIStarter] Процесс winws.exe не найден", level="WARNING")

                # -----------------------------------------------------------
                # 3. Обновляем UI и выходим
                # -----------------------------------------------------------
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