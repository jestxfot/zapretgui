# dpi/start.py
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
    
    def set_status(self, text):
        """Отображает статусное сообщение."""
        if self.status_callback:
            self.status_callback(text)
        else:
            print(text)
    
    def check_process_running(self, silent=False):
        import re
        """Проверяет, запущен ли процесс winws.exe"""
        try:
            if not silent:
                log("=================== check_process_running ==========================", level="START")
            
            # Метод 1: Проверка через tasklist (может быть заблокирована)
            if not silent:
                log("Метод 1: Проверка через tasklist", level="START")
            
            try:
                result = subprocess.run(
                    'C:\\Windows\\System32\\tasklist.exe /FI "IMAGENAME eq winws.exe" /FO CSV /NH',
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=5  # Добавляем таймаут
                )
                
                if result.returncode == 0 and "winws.exe" in result.stdout:
                    # Извлекаем PID процесса
                    import re
                    pid_match = re.search(r'"winws\.exe","(\d+)"', result.stdout)
                    if pid_match:
                        pid = pid_match.group(1)
                        if not silent:
                            log(f"Найден PID процесса: {pid}", level="START")
                        return True
                    
                    if not silent:
                        log("Процесс найден, но не удалось определить PID", level="START")
                    return True
                
                # Если tasklist вернула ошибку
                if result.returncode != 0:
                    error_msg = result.stderr.strip() if result.stderr else "неизвестная ошибка"
                    if not silent:
                        log(f"tasklist завершился с кодом {result.returncode}: {error_msg}", level="⚠ WARNING")
                        log("Переходим к альтернативным методам проверки", level="⚠ WARNING")
                
            except subprocess.TimeoutExpired:
                if not silent:
                    log("tasklist превысила таймаут, переходим к другим методам", level="⚠ WARNING")
            except Exception as e:
                if not silent:
                    log(f"Ошибка при выполнении tasklist: {e}", level="⚠ WARNING")
            
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
                        'C:\\Windows\\System32\\wbem\\wmic.exe process where "name=\'winws.exe\'" get processid',
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
                        'C:\\Windows\\System32\\tasklist.exe | C:\\Windows\\System32\\findstr.exe "winws"',
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
    def cleanup_windivert_service(self):
        """Принудительно останавливает и удаляет службу windivert"""
        try:
            log("=================== cleanup_windivert_service ==========================", level="START")
            
            # Шаг 1: Проверяем состояние службы
            log("Проверяем состояние службы windivert...", level="INFO")
            check_result = subprocess.run(
                'C:\\Windows\\System32\\sc.exe query windivert',
                shell=True,
                capture_output=True,
                text=True,
                encoding='cp866'
            )
            
            if "SERVICE_NAME: windivert" not in check_result.stdout:
                log("Служба windivert не найдена в списке служб", level="INFO")
                # Если службы нет, просто выходим - не нужно делать агрессивную очистку
                return True
            
            # Шаг 2: Останавливаем службу
            log("Останавливаем службу windivert...", level="INFO")
            stop_result = subprocess.run(
                'C:\\Windows\\System32\\sc.exe stop windivert',
                shell=True,
                capture_output=True,
                text=True,
                encoding='cp866'
            )
            
            # Ждем остановки службы
            for i in range(10):
                time.sleep(0.5)
                query_result = subprocess.run(
                    'C:\\Windows\\System32\\sc.exe query windivert',
                    shell=True,
                    capture_output=True,
                    text=True,
                    encoding='cp866'
                )
                if "STOPPED" in query_result.stdout:
                    log(f"Служба остановлена (попытка {i+1})", level="INFO")
                    break
            
            # Шаг 3: Удаление службы
            log("Удаляем службу windivert...", level="INFO")
            delete_result = subprocess.run(
                'C:\\Windows\\System32\\sc.exe delete windivert',
                shell=True,
                capture_output=True,
                text=True,
                encoding='cp866'
            )
            
            if delete_result.returncode == 0 or "1060" in delete_result.stderr:
                log("Служба windivert удалена", level="✅ SUCCESS")
            else:
                log(f"Ошибка удаления службы: {delete_result.stderr}", level="⚠ WARNING")
            
            # Небольшая пауза для завершения операций
            time.sleep(1)
            
            # Финальная проверка
            final_check = subprocess.run(
                'C:\\Windows\\System32\\sc.exe query windivert',
                shell=True,
                capture_output=True,
                text=True,
                encoding='cp866'
            )
            
            if "SERVICE_NAME: windivert" not in final_check.stdout:
                log("Служба windivert успешно удалена", level="✅ SUCCESS")
                return True
            else:
                log("Служба все еще присутствует, но продолжаем", level="⚠ WARNING")
                return True
                        
        except Exception as e:
            log(f"Ошибка при очистке службы windivert: {e}", level="⚠ WARNING")
            return True  # Продолжаем работу даже при ошибке

    def stop_all_processes(self):
        """Останавливает все процессы DPI через stop.bat"""
        try:
            log("=================== stop_all_processes ==========================", level="START")
            
            # Путь к stop.bat
            stop_bat_path = os.path.join(os.path.dirname(self.winws_exe), "stop.bat")
            
            # Проверяем существование файла
            if not os.path.exists(stop_bat_path):
                log(f"Файл stop.bat не найден: {stop_bat_path}", level="⚠ WARNING")
                # Создаем файл stop.bat если его нет
                log("Создаем stop.bat...", level="INFO")
                with open(stop_bat_path, 'w') as f:
                    f.write("""@echo off
    net session >nul 2>&1
    if %errorlevel% neq 0 (
        echo Requesting administrator privileges...
        echo Set UAC = CreateObject^("Shell.Application"^) > "%temp%\getadmin.vbs"
        echo UAC.ShellExecute "%~f0", "", "", "runas", 1 >> "%temp%\getadmin.vbs"
        "%temp%\getadmin.vbs"
        del "%temp%\getadmin.vbs"
        exit /b
    )                  
    taskkill /F /IM winws.exe /T
    sc stop windivert
    sc delete windivert
    exit /b 0
    """)
            
            # Запускаем stop.bat
            log(f"Запускаем {stop_bat_path}...", level="INFO")
            
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            
            # Используем полный путь до cmd.exe
            cmd_path = r'C:\Windows\System32\cmd.exe'
            
            result = subprocess.run(
                [cmd_path, '/c', stop_bat_path],
                shell=False,  # Изменяем на False, так как используем прямой вызов
                startupinfo=startupinfo,
                capture_output=True,
                text=True,
                encoding='cp866',  # Добавляем кодировку для корректного вывода
                timeout=10
            )
            
            if result.returncode == 0:
                log("stop.bat выполнен успешно", level="✅ SUCCESS")
            else:
                log(f"stop.bat вернул код: {result.returncode}", level="⚠ WARNING")
                if result.stdout:
                    log(f"Вывод: {result.stdout}", level="DEBUG")
                if result.stderr:
                    log(f"Ошибки: {result.stderr}", level="⚠ WARNING")
                
            # Небольшая пауза для завершения всех операций
            time.sleep(0.3)
            
            # Проверяем, что процесс действительно остановлен
            if not self.check_process_running(silent=True):
                log("Все процессы успешно остановлены", level="✅ SUCCESS")
                return True
            else:
                log("Процесс winws.exe все еще работает", level="⚠ WARNING")
                return False
                
        except subprocess.TimeoutExpired:
            log("Таймаут при выполнении stop.bat", level="❌ ERROR")
            return False
        except Exception as e:
            log(f"Ошибка при выполнении stop.bat: {e}", level="❌ ERROR")
            return False
        
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

        from config import BAT_FOLDER, INDEXJSON_FOLDER, DEFAULT_STRAT

        # Добавим отладку путей
        log(f"[DPIStarter] BAT_FOLDER: {BAT_FOLDER}", level="DEBUG")
        log(f"[DPIStarter] Проверяем существование папки: {os.path.exists(BAT_FOLDER)}", level="DEBUG")

        index_path = os.path.join(INDEXJSON_FOLDER, "index.json")
        log(f"[DPIStarter] Полный путь к index.json: {index_path}", level="DEBUG")
        log(f"[DPIStarter] Файл index.json существует: {os.path.exists(index_path)}", level="DEBUG")

        def diagnose_environment():
            """Диагностика окружения для отладки"""
            import platform, sys
            from main import is_admin

            bat_path = os.path.normpath(os.path.join(BAT_FOLDER))
            log("=== ДИАГНОСТИКА ОКРУЖЕНИЯ ===", level="🔹 INFO")
            log(f"OS: {platform.system()} {platform.version()}", level="🔹 INFO")
            log(f"Python: {sys.version}", level="🔹 INFO")
            log(f"Текущий пользователь: {os.environ.get('USERNAME', 'unknown')}", level="🔹 INFO")
            log(f"Права админа: {is_admin()}", level="🔹 INFO")
            log(f"Рабочая директория: {os.getcwd()}", level="🔹 INFO")
            log(f"BAT exists: {os.path.exists(bat_path)}", level="🔹 INFO")
            log(f"BAT readable: {os.access(bat_path, os.R_OK)}", level="🔹 INFO")
            log(f"BAT executable: {os.access(bat_path, os.X_OK)}", level="🔹 INFO")
        diagnose_environment()

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
                index_path = os.path.join(INDEXJSON_FOLDER, "index.json")
                
                # Если index.json отсутствует, попробуем его скачать
                if not os.path.exists(index_path):
                    log(f"[DPIStarter] index.json не найден, пытаемся скачать...", level="⚠ WARNING")
                    try:
                        from strategy_menu.manager import StrategyManager
                        
                        manager = StrategyManager(
                            local_dir=BAT_FOLDER,
                            status_callback=self._set_status
                        )
                        
                        # Принудительно скачиваем индекс
                        strategies = manager.get_strategies_list(force_update=True)
                        if strategies:
                            log(f"[DPIStarter] index.json успешно скачан", level="INFO")
                        else:
                            raise Exception("Пустой список стратегий")
                            
                    except Exception as download_error:
                        log(f"[DPIStarter] Не удалось скачать index.json: {download_error}", level="❌ ERROR")
                        self._set_status("Ошибка: не удалось загрузить список стратегий")
                        return False
                
                # Читаем файл с правильной кодировкой
                try:
                    # Сначала пробуем utf-8-sig для файлов с BOM
                    with open(index_path, "r", encoding="utf-8-sig") as f:
                        self._idx = json.load(f)
                except UnicodeDecodeError:
                    # Если не получилось, пробуем обычный utf-8
                    with open(index_path, "r", encoding="utf-8") as f:
                        self._idx = json.load(f)
                except json.JSONDecodeError as je:
                    # Если JSON поврежден, пробуем прочитать и исправить
                    log(f"[DPIStarter] JSON decode error: {je}", level="❌ ERROR")
                    
                    # Читаем содержимое файла
                    with open(index_path, "rb") as f:
                        content = f.read()
                    
                    # Удаляем BOM если есть
                    if content.startswith(b'\xef\xbb\xbf'):
                        content = content[3:]
                    
                    # Пробуем декодировать и парсить
                    try:
                        text = content.decode('utf-8')
                        self._idx = json.loads(text)
                    except Exception as e2:
                        log(f"[DPIStarter] Не удалось исправить JSON: {e2}", level="❌ ERROR")
                        raise
                        
        except Exception as e:
            log(f"[DPIStarter] index.json error: {e}", level="❌ ERROR")
            
            # Если index.json не читается, попробуем создать временный из списка файлов
            bat_files = [f for f in os.listdir(BAT_FOLDER) if f.endswith('.bat')]
            if bat_files:
                log(f"[DPIStarter] Создаем временный индекс из {len(bat_files)} .bat файлов", level="⚠ WARNING")
                
                # Создаем простой индекс
                self._idx = {}
                for bat_file in bat_files:
                    name = bat_file[:-4]  # убираем .bat
                    self._idx[name] = {
                        "name": name,
                        "file_path": bat_file,
                        "description": f"Стратегия {name}"
                    }
                
                self._set_status(f"Используется временный список из {len(bat_files)} стратегий")
            else:
                log(f"[DPIStarter] Содержимое папки {BAT_FOLDER}: {os.listdir(BAT_FOLDER) if os.path.exists(BAT_FOLDER) else 'папка не существует'}", level="❌ ERROR")
                self._set_status("index.json не найден и не удалось создать временный")
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
            log(f"[DPIStarter] не найден .bat для '{selected_mode}'", level="❌ ERROR")
            self._set_status("Ошибка: стратегия не найдена")
            return False

        # убираем дублирующий «bin\\»
        while bat_rel.lower().startswith(("bin\\", "bin/")):
            bat_rel = bat_rel[4:]
        bat_path = os.path.normpath(os.path.join(BAT_FOLDER, bat_rel))

        if not os.path.isfile(bat_path):
            log(f"[DPIStarter] файл не найден: {bat_path}", level="❌ ERROR")
            self._set_status("Ошибка: файл стратегии не найден")
            return False

        # -------- 3. Внутренняя функция реального запуска -----------------
        def _do_start() -> bool:
            # Путь к файлу блокировки
            lock_file = os.path.join(os.path.dirname(self.winws_exe), "winws_starting.lock")
            
            # Проверяем, не идет ли уже процесс запуска
            if os.path.exists(lock_file):
                try:
                    # Проверяем возраст lock-файла (может быть "зависший")
                    lock_age = time.time() - os.path.getmtime(lock_file)
                    if lock_age > 30:  # Если файл старше 30 секунд
                        log(f"[DPIStarter] Обнаружен старый lock-файл ({lock_age:.1f} сек), удаляем", level="⚠ WARNING")
                        os.remove(lock_file)
                    else:
                        log("[DPIStarter] Уже идет процесс запуска (lock-файл существует)", level="⚠ WARNING")
                        return False
                except Exception as e:
                    log(f"[DPIStarter] Ошибка при проверке lock-файла: {e}", level="⚠ WARNING")
            
            # Создаем lock-файл
            try:
                with open(lock_file, 'w') as f:
                    f.write(f"{os.getpid()}\n{time.time()}")
                log(f"[DPIStarter] Создан lock-файл: {lock_file}", level="DEBUG")
            except Exception as e:
                log(f"[DPIStarter] Не удалось создать lock-файл: {e}", level="❌ ERROR")
                return False
            
            # Основная логика запуска в блоке try-finally
            try:
                # УПРОЩЕННАЯ ЛОГИКА: Используем stop.bat для остановки всего
                log("[DPIStarter] Останавливаем все процессы через stop.bat...", level="INFO")
                self.stop_all_processes()
                
                # Дополнительная пауза для гарантии
                time.sleep(0.3)
                
                abs_bat = os.path.abspath(bat_path)
                
                # ===============================================
                # Способ 1: Основной метод
                # ===============================================
                log("[DPIStarter] Попытка 1: Основной метод через cmd /c", level="INFO")
                try:
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    startupinfo.wShowWindow = subprocess.SW_HIDE
                    
                    cmd = f'C:\\Windows\\System32\\cmd.exe /c start /b cmd /c "{abs_bat}"'
                    log(f"[DPIStarter] RUN: {cmd} (hidden)", level="INFO")
                    
                    # В методе _do_start()
                    work_dir = os.path.dirname(abs_bat)
                    if not os.path.exists(work_dir):
                        log(f"[DPIStarter] Рабочая директория не существует: {work_dir}", level="❌ ERROR")
                        return False

                    process = subprocess.Popen(
                        ['C:\\Windows\\System32\\cmd.exe', '/c', abs_bat],
                        shell=True,
                        cwd=work_dir,  # Явно указываем рабочую директорию
                        startupinfo=startupinfo,
                        creationflags=subprocess.CREATE_NO_WINDOW
                    )

                    # Ждем немного
                    time.sleep(0.3)
                    
                    # Проверяем, не завершился ли процесс с ошибкой
                    if process.poll() is not None and process.returncode != 0:
                        log(f"[DPIStarter] Процесс завершился с кодом {process.returncode}", level="⚠ WARNING")
                    else:
                        # Проверяем несколько раз, запустился ли winws.exe
                        for i in range(5):  # 5 попыток с интервалом
                            if self.check_process_running(silent=True):
                                log(f"[DPIStarter] ✅ Успех! Запущена стратегия: {selected_mode} (основной метод, попытка {i+1})", level="INFO")
                                self._update_ui(True)
                                return True
                            time.sleep(0.3)
                        
                        # Если процесс все еще работает, но winws.exe не найден
                        if process.poll() is None:
                            log("[DPIStarter] BAT-процесс работает, но winws.exe не обнаружен", level="⚠ WARNING")
                                
                except WindowsError as e:
                    if e.winerror == 5:  # Access Denied
                        log("[DPIStarter] Ошибка доступа при основном методе", level="⚠ WARNING")
                    else:
                        log(f"[DPIStarter] Windows ошибка: {e}", level="❌ ERROR")
                except Exception as e:
                    log(f"[DPIStarter] Ошибка основного метода: {e}", level="⚠ WARNING")
                
                # ===============================================
                # ВАЖНО: Проверяем еще раз перед следующей попыткой
                # ===============================================
                time.sleep(0.5)
                if self.check_process_running(silent=True):
                    log("[DPIStarter] ✅ Процесс запущен после первой попытки!", level="INFO")
                    self._update_ui(True)
                    return True
                
                # ===============================================
                # Способ 2: Альтернативный метод через start
                # ===============================================
                log("[DPIStarter] Попытка 2: Альтернативный метод через start /b", level="INFO")
                
                try:
                    alt_cmd = f'C:\\Windows\\System32\\cmd.exe /c start /b cmd /c "{abs_bat}"'
                    result = subprocess.run(
                        alt_cmd,
                        shell=True,
                        cwd=os.path.dirname(abs_bat),
                        capture_output=True,
                        text=True
                    )
                    
                    if result.returncode != 0:
                        log(f"[DPIStarter] start вернул код {result.returncode}: {result.stderr}", level="⚠ WARNING")
                    
                    # Даем время на запуск
                    time.sleep(0.3)
                    
                    # Проверяем несколько раз
                    for i in range(5):
                        if self.check_process_running(silent=True):
                            log(f"[DPIStarter] ✅ Успех! Запуск через start (попытка {i+1})", level="INFO")
                            self._update_ui(True)
                            return True
                        time.sleep(0.3)

                except Exception as alt_error:
                    log(f"[DPIStarter] start не сработал: {alt_error}", level="⚠ WARNING")
                
                # ===============================================
                # ВАЖНО: Проверяем еще раз перед последней попыткой
                # ===============================================
                time.sleep(0.5)
                if self.check_process_running(silent=True):
                    log("[DPIStarter] ✅ Процесс запущен после второй попытки!", level="INFO")
                    self._update_ui(True)
                    return True
                
                # ===============================================
                # Способ 3: Через прямой вызов
                # ===============================================
                log("[DPIStarter] Попытка 3: Прямой запуск bat-файла", level="INFO")
                
                try:
                    # Запускаем напрямую без cmd /c
                    process = subprocess.Popen(
                        ['C:\\Windows\\System32\\cmd.exe', '/c', abs_bat],
                        shell=False,
                        cwd=os.path.dirname(abs_bat),
                        startupinfo=startupinfo,
                        creationflags=subprocess.CREATE_NO_WINDOW
                    )
                    
                    # Даем время на запуск
                    time.sleep(1)
                    
                    # Проверяем несколько раз
                    for i in range(5):
                        if self.check_process_running(silent=True):
                            log(f"[DPIStarter] ✅ Успех! Прямой запуск (попытка {i+1})", level="INFO")
                            self._update_ui(True)
                            return True
                        time.sleep(0.5)
                        
                except Exception as direct_error:
                    log(f"[DPIStarter] Прямой запуск не сработал: {direct_error}", level="⚠ WARNING")
                
                # ===============================================
                # Финальная проверка
                # ===============================================
                time.sleep(1)
                if self.check_process_running(silent=True):
                    log("[DPIStarter] ✅ Процесс все-таки запустился!", level="INFO")
                    self._update_ui(True)
                    return True
                
                # Если ничего не помогло
                log("[DPIStarter] ❌ Все методы запуска не сработали", level="❌ ERROR")
                self._set_status("Не удалось запустить DPI")
                return False

            except Exception as e:
                log(f"[DPIStarter] Критическая ошибка запуска: {e}", level="❌ ERROR")
                self._set_status(f"Ошибка запуска: {e}")
                return False
            
            finally:
                # Всегда удаляем lock-файл в конце
                try:
                    if os.path.exists(lock_file):
                        os.remove(lock_file)
                        log(f"[DPIStarter] Удален lock-файл: {lock_file}", level="DEBUG")
                except Exception as e:
                    log(f"[DPIStarter] Ошибка при удалении lock-файла: {e}", level="⚠ WARNING")

        # -------- 4. Запускаем сразу или с задержкой ----------------------
        if delay_ms > 0:
            QTimer.singleShot(delay_ms, _do_start)
            log(f"[DPIStarter] запуск отложен на {delay_ms} мс", level="DEBUG")
            return True
        return _do_start()