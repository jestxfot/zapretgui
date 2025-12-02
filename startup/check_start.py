#startup/check_start.py
import os
import sys
from PyQt6.QtWidgets import QMessageBox, QApplication
import ctypes, sys, subprocess, winreg

# Импортируем константы из конфига
from config import BIN_FOLDER

# Добавляем импорт кэша
from startup.check_cache import startup_cache
from utils import run_hidden
import psutil

def _native_message(title: str, text: str, style=0x00000010):  # MB_ICONERROR
    """
    Показывает нативное окно MessageBox (не требует QApplication)
    style: 0x10 = MB_ICONERROR,  0x30 = MB_ICONWARNING | MB_YESNO
    """
    ctypes.windll.user32.MessageBoxW(0, text, title, style)

def check_system_commands() -> tuple[bool, str]:
    """
    Проверяет доступность основных системных команд с кэшированием.
    """
    # Проверяем кэш (короткое время жизни - 1 час)
    has_cache, cached_result = startup_cache.is_cached_and_valid("system_commands")
    if has_cache:
        return cached_result, ""
    
    try:
        from log import log
        log("Проверка системных команд", "DEBUG")
    except ImportError:
        print("DEBUG: Проверка системных команд")
    
    # Определяем команды для проверки
    required_commands = [
        ("tasklist", "tasklist /FI \"IMAGENAME eq explorer.exe\" /FO CSV /NH"),
        ("sc", "sc query"),
        ("netsh", "netsh /?"),
    ]
    
    failed_commands = []
    
    # Определяем параметры для разных систем
    run_params = {
        "shell": True,
        "capture_output": True,
        "text": True,
        "timeout": 10,
        "errors": "ignore"
    }
    
    # Добавляем Windows-специфичные параметры
    if sys.platform == "win32":
        # Определяем кодировку консоли
        try:
            import locale
            console_encoding = locale.getpreferredencoding() or "utf-8"
        except:
            console_encoding = "utf-8"
        
        run_params["encoding"] = console_encoding
        
        # CREATE_NO_WINDOW доступен только на Windows
        if hasattr(subprocess, "CREATE_NO_WINDOW"):
            run_params["creationflags"] = subprocess.CREATE_NO_WINDOW
    
    for cmd_name, test_command in required_commands:
        try:
            result = run_hidden(test_command, **run_params)
            
            if cmd_name == "tasklist":
                if result.returncode != 0:
                    stderr_text = result.stderr.strip().lower()
                    # Проверяем на разных языках
                    error_indicators = [
                        "не является", "not recognized", "not found",
                        "command not found", "nicht gefunden", "introuvable",
                        "no se reconoce", "não é reconhecido"
                    ]
                    if any(indicator in stderr_text for indicator in error_indicators):
                        failed_commands.append(f"{cmd_name} (команда недоступна)")
                        try:
                            from log import log
                            log(f"ERROR: Команда {cmd_name} недоступна: {result.stderr.strip()}", level="❌ ERROR")
                        except ImportError:
                            print(f"ERROR: Команда {cmd_name} недоступна")
                        continue
            
            # Для разных команд разные допустимые коды возврата
            acceptable_codes = {
                "tasklist": [0, 1],  # 1 = процесс не найден
                "sc": [0, 1, 2],     # 1,2 = сервис не найден/остановлен
                "netsh": [0, 1]      # 1 = помощь показана
            }
            
            if result.returncode not in acceptable_codes.get(cmd_name, [0, 1]):
                failed_commands.append(f"{cmd_name} (код ошибки: {result.returncode})")
                try:
                    from log import log
                    log(f"WARNING: Команда {cmd_name} вернула код {result.returncode}", level="⚠ WARNING")
                except ImportError:
                    print(f"WARNING: Команда {cmd_name} вернула код {result.returncode}")
                    
        except subprocess.TimeoutExpired:
            failed_commands.append(f"{cmd_name} (превышен таймаут)")
            try:
                from log import log
                log(f"ERROR: Команда {cmd_name} превысила таймаут", level="❌ ERROR")
            except ImportError:
                print(f"ERROR: Команда {cmd_name} превысила таймаут")
                
        except FileNotFoundError:
            failed_commands.append(f"{cmd_name} (файл не найден)")
            try:
                from log import log
                log(f"ERROR: Команда {cmd_name} не найдена", level="❌ ERROR")
            except ImportError:
                print(f"ERROR: Команда {cmd_name} не найдена")
                
        except Exception as e:
            failed_commands.append(f"{cmd_name} ({str(e)})")
            try:
                from log import log
                log(f"ERROR: Ошибка при проверке команды {cmd_name}: {e}", level="❌ ERROR")
            except ImportError:
                print(f"ERROR: Ошибка при проверке команды {cmd_name}: {e}")
    
    has_issues = bool(failed_commands)
    
    if has_issues:
        error_message = (
            "Обнаружены проблемы с системными командами:\n\n"
            + "\n".join(f"• {cmd}" for cmd in failed_commands) + 
            "\n\nЭто может быть вызвано:\n"
            "• Блокировкой антивирусом (особенно Касперский)\n"
            "• Политиками безопасности системы\n"
            "• Повреждением системных файлов\n"
            "• Нестандартной конфигурацией Windows\n\n"
            "Рекомендации:\n"
            "1. Добавьте программу в исключения антивируса\n"
            "2. Запустите от имени администратора\n"
            "3. Проверьте целостность файлов: sfc /scannow\n\n"
            "Программа может работать с ограничениями."
        )
    else:
        error_message = ""
        try:
            from log import log
            log("Все системные команды доступны", level="☑ INFO")
        except ImportError:
            print("INFO: Все системные команды доступны")
    
    # Кэшируем результат (короткое время - 1 час)
    startup_cache.cache_result("system_commands", has_issues)
    
    return has_issues, error_message
   
def check_mitmproxy() -> tuple[bool, str]:
    """
    Проверяет, запущен ли mitmproxy с кэшированием (короткое время).
    """
    # Кэш только на 5 минут для процессов
    has_cache, cached_result = startup_cache.is_cached_and_valid("mitmproxy_check")
    if has_cache:
        return cached_result, ""
    
    # Имена исполняемых файлов mitmproxy (точное совпадение)
    MITMPROXY_EXECUTABLES = [
        "mitmproxy.exe",
        "mitmdump.exe", 
        "mitmweb.exe",
    ]
    
    # Получаем PID текущего процесса для исключения
    current_pid = os.getpid()
    
    try:
        for proc in psutil.process_iter(['pid', 'name', 'exe', 'cmdline']):
            try:
                # Пропускаем текущий процесс
                if proc.info['pid'] == current_pid:
                    continue
                    
                proc_name = proc.info['name'].lower() if proc.info['name'] else ""
                
                # Точное совпадение имени процесса с mitmproxy
                if proc_name in [exe.lower() for exe in MITMPROXY_EXECUTABLES]:
                    err = (
                        f"Обнаружен запущенный процесс mitmproxy: {proc.info['name']} (PID: {proc.info['pid']})\n\n"
                        "mitmproxy использует тот же драйвер WinDivert, что и Zapret.\n"
                        "Одновременная работа этих программ невозможна.\n\n"
                        "Пожалуйста, завершите все процессы mitmproxy и перезапустите Zapret."
                    )
                    try:
                        from log import log
                        log(f"ERROR: Найден конфликтующий процесс mitmproxy: {proc.info['name']} (PID: {proc.info['pid']})", level="❌ ERROR")
                    except ImportError:
                        print(f"ERROR: Найден конфликтующий процесс mitmproxy: {proc.info['name']}")
                    
                    startup_cache.cache_result("mitmproxy_check", True)
                    return True, err
                
                # Проверка пути исполняемого файла
                proc_exe = proc.info.get('exe', '') or ''
                if proc_exe:
                    exe_basename = os.path.basename(proc_exe).lower()
                    if exe_basename in [exe.lower() for exe in MITMPROXY_EXECUTABLES]:
                        err = (
                            f"Обнаружен запущенный процесс mitmproxy: {proc.info['name']} (PID: {proc.info['pid']})\n\n"
                            "mitmproxy использует тот же драйвер WinDivert, что и Zapret.\n"
                            "Одновременная работа этих программ невозможна.\n\n"
                            "Пожалуйста, завершите все процессы mitmproxy и перезапустите Zapret."
                        )
                        try:
                            from log import log
                            log(f"ERROR: Найден конфликтующий процесс mitmproxy по пути: {proc_exe} (PID: {proc.info['pid']})", level="❌ ERROR")
                        except ImportError:
                            print(f"ERROR: Найден конфликтующий процесс mitmproxy по пути: {proc_exe}")
                        
                        startup_cache.cache_result("mitmproxy_check", True)
                        return True, err
                        
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
                
    except Exception as e:
        try:
            from log import log
            log(f"Ошибка при проверке процессов mitmproxy: {e}", level="⚠ WARNING")
        except ImportError:
            print(f"WARNING: Ошибка при проверке процессов mitmproxy: {e}")
        
        # При ошибке не кэшируем
        return False, ""
    
    # Кэшируем положительный результат (конфликтов не найдено)
    startup_cache.cache_result("mitmproxy_check", False)
    return False, ""
    
def check_if_in_archive():
    """
    Проверяет, находится ли EXE-файл в временной директории с кэшированием.
    """
    exe_path = os.path.abspath(sys.executable)
    
    # Проверяем кэш с контекстом пути
    has_cache, cached_result = startup_cache.is_cached_and_valid("archive_check", exe_path)
    if has_cache:
        return cached_result
    
    try:
        try:
            from log import log
            log(f"Executable path: {exe_path}", level="CHECK_START")
        except ImportError:
            print(f"DEBUG: Executable path: {exe_path}")

        system32_path = os.path.abspath(os.path.join(os.environ.get("WINDIR", ""), "System32"))
        temp_env = os.environ.get("TEMP", "")
        tmp_env = os.environ.get("TMP", "")
        temp_dirs = [temp_env, tmp_env, system32_path]
        
        is_in_temp = False
        for temp_dir in temp_dirs:
            if temp_dir and exe_path.lower().startswith(os.path.abspath(temp_dir).lower()):
                try:
                    from log import log
                    log(f"EXE запущен из временной директории: {temp_dir}", level="⚠ WARNING")
                except ImportError:
                    print(f"WARNING: EXE запущен из временной директории: {temp_dir}")
                is_in_temp = True
                break
        
        # Кэшируем результат
        startup_cache.cache_result("archive_check", is_in_temp, exe_path)
        return is_in_temp
        
    except Exception as e:
        try:
            from log import log
            log(f"Ошибка при проверке расположения EXE: {str(e)}", level="DEBUG")
        except ImportError:
            print(f"DEBUG: Ошибка при проверке расположения EXE: {str(e)}")
        return False

def is_in_onedrive(path: str) -> bool:
    """
    True, если путь находится в каталоге OneDrive
    (учитывается как пользовательский, так и корпоративный вариант).
    """
    path_lower = os.path.abspath(path).lower()

    # 1) Самый надёжный способ – сравнить с переменной окружения ONEDRIVE
    onedrive_env = os.environ.get("ONEDRIVE")
    if onedrive_env and path_lower.startswith(os.path.abspath(onedrive_env).lower()):
        return True

    # 2) Резерв – ищем «onedrive» в любом сегменте пути
    #    (OneDrive, OneDrive - CompanyName и т.п.)
    return any(seg.startswith("onedrive") for seg in path_lower.split(os.sep))

def check_path_for_onedrive() -> tuple[bool, str]:
    """
    Проверяет OneDrive в путях с кэшированием.
    """
    current_path = os.path.abspath(os.getcwd())
    exe_path = os.path.abspath(sys.executable)
    paths_context = f"{current_path}|{exe_path}|{BIN_FOLDER}"
    
    # Проверяем кэш с контекстом всех путей
    has_cache, cached_result = startup_cache.is_cached_and_valid("onedrive_check", paths_context)
    if has_cache:
        return cached_result, ""

    paths_to_check = [current_path, exe_path, BIN_FOLDER]

    for path in paths_to_check:
        if is_in_onedrive(path):
            err = (
                f"Путь содержит каталог OneDrive:\n{path}\n\n"
                "OneDrive часто блокирует доступ к файлам и может вызывать ошибки.\n"
                "Переместите программу в любую локальную папку "
                "(например, C:\\zapret) и запустите её снова."
            )
            try:
                from log import log
                log(f"ERROR: Обнаружен OneDrive в пути: {path}", level="❌ ERROR")
            except ImportError:
                print(f"ERROR: Обнаружен OneDrive в пути: {path}")
            
            # Кэшируем отрицательный результат
            startup_cache.cache_result("onedrive_check", True, paths_context)
            return True, err
    
    # Кэшируем положительный результат
    startup_cache.cache_result("onedrive_check", False, paths_context)
    return False, ""

import re
def contains_special_chars(path: str) -> bool:
    """
    True, если путь содержит:
      • пробел
      • (опционально) цифру
      • символ НЕ из списка  A-Z a-z 0-9 _ . : \\ /
    """
    if " " in path:
        return True            # пробел — сразу ошибка

    # если хотите запретить цифры — раскомментируйте строку ниже
    # if re.search(r"\d", path):
    #     return True

    # проверяем оставшиеся символы
    #  ^ – отрицание; разрешаем  A-Z a-z 0-9 _ . : \ /
    return bool(re.search(r"[^A-Za-z0-9_\.:\\/]", path))

def check_path_for_special_chars():
    """Проверяет пути программы на наличие специальных символов с кэшированием"""
    current_path = os.path.abspath(os.getcwd())
    exe_path = os.path.abspath(sys.executable)
    paths_context = f"{current_path}|{exe_path}|{BIN_FOLDER}"
    
    paths_to_check = [current_path, exe_path, BIN_FOLDER]
    
    for path in paths_to_check:
        if contains_special_chars(path):
            error_message = (
                f"Путь содержит специальные символы: {path}\n\n"
                "Программа не может корректно работать в папке со специальными символами (РФ символы (недопустимы символы от А до Я!), пробелы, цифры, точки, скобки, запятые и т.д.).\n"
                "Пожалуйста, переместите программу в папку (или корень диска) без специальных символов в пути (например, по пути C:\\zapret или D:\\zapret) и запустите её снова."
            )
            try:
                from log import log
                log(f"ERROR: Путь содержит специальные символы: {path}", level="❌ ERROR")
            except ImportError:
                print(f"ERROR: Путь содержит специальные символы: {path}")
            
            # Кэшируем отрицательный результат
            startup_cache.cache_result("special_chars", True, paths_context)
            return True, error_message
    
    # Кэшируем положительный результат
    startup_cache.cache_result("special_chars", False, paths_context)
    return False, ""

def check_win10_tweaker() -> tuple[bool, str]:
    """
    Проверяет наличие Win 10 Tweaker в реестре с кэшированием.
    Отказ в доступе также считается признаком наличия твикера.
    """

    has_cache, cached_found = startup_cache.is_cached_and_valid("win10_tweaker_check")
    if has_cache:
        # если твикер найден – восстановим текст ошибки
        return cached_found, (_get_tweaker_error_message() if cached_found else "")
    
    try:
        # Проверяем наличие ключа Win 10 Tweaker в реестре
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Win 10 Tweaker",
            )
            winreg.CloseKey(key)
            
            # Ключ найден - система модифицирована
            try:
                from log import log
                log("CRITICAL ERROR: Обнаружен Win 10 Tweaker в системе!", level="❌ ERROR")
            except ImportError:
                print("CRITICAL ERROR: Обнаружен Win 10 Tweaker в системе!")
            
            # Кэшируем отрицательный результат (система заражена)
            startup_cache.cache_result("win10_tweaker_check", True)
            return True, _get_tweaker_error_message()
            
        except PermissionError as e:
            # Отказ в доступе - твикер блокирует доступ к своему ключу!
            try:
                from log import log
                log(f"CRITICAL ERROR: Win 10 Tweaker блокирует доступ к реестру! Error: {e}", level="❌ ERROR")
            except ImportError:
                print(f"CRITICAL ERROR: Win 10 Tweaker блокирует доступ к реестру! Error: {e}")
            
            # Кэшируем отрицательный результат (система заражена)
            startup_cache.cache_result("win10_tweaker_check", True)
            return True, _get_tweaker_error_message(access_denied=True)
            
        except OSError as e:
            # WinError 5 - Access is denied
            if e.winerror == 5:
                try:
                    from log import log
                    log("CRITICAL ERROR: Win 10 Tweaker блокирует доступ к реестру (WinError 5)!", level="❌ ERROR")
                except ImportError:
                    print("CRITICAL ERROR: Win 10 Tweaker блокирует доступ к реестру (WinError 5)!")
                
                # Кэшируем отрицательный результат (система заражена)
                startup_cache.cache_result("win10_tweaker_check", True)
                return True, _get_tweaker_error_message(access_denied=True)
            else:
                # Другая OSError - не связана с твикером
                raise
                
        except FileNotFoundError:
            # Ключ не найден - система чистая, это нормально
            try:
                from log import log
                log("Win 10 Tweaker не обнаружен", level="☑ INFO")
            except ImportError:
                print("INFO: Win 10 Tweaker не обнаружен")
            
            # Кэшируем положительный результат
            startup_cache.cache_result("win10_tweaker_check", False)
            return False, ""
            
    except Exception as e:
        # При любой другой ошибке считаем, что твикера нет (это нормально)
        try:
            from log import log
            log(f"Проверка Win 10 Tweaker: {e}", level="DEBUG")
        except ImportError:
            print(f"DEBUG: Проверка Win 10 Tweaker: {e}")
        
        # При неизвестной ошибке не кэшируем
        return False, ""

def _get_tweaker_error_message(access_denied=False) -> str:
    """
    Возвращает сообщение об ошибке для Win 10 Tweaker.
    """
    if access_denied:
        header = (
            "КРИТИЧЕСКАЯ ОШИБКА: Win 10 Tweaker блокирует доступ к реестру!\n\n"
            "Программа Win 10 Tweaker активно защищает себя от обнаружения, "
            "что является признаком вредоносного ПО.\n\n"
        )
    else:
        header = (
            "КРИТИЧЕСКАЯ ОШИБКА: Обнаружен Win 10 Tweaker!\n\n"
            "Ваша система была модифицирована программой Win 10 Tweaker.\n\n"
        )
    
    return header + (
        "Win 10 Tweaker - это опасная программа, которая:\n"
        "• Часто распространяется вместе с вирусами\n"
        "• Вносит критические изменения в систему\n"
        "• Нарушает работу сетевых компонентов Windows\n"
        "• Отключает критически важные службы\n"
        "• Изменяет политики безопасности\n"
        "• Может содержать скрытый вредоносный код\n\n"
        "Zapret НЕ МОЖЕТ работать в системе, где применялись твикеры!\n\n"
        "ЕДИНСТВЕННОЕ РЕШЕНИЕ:\n"
        "1. Сохраните важные данные\n"
        "2. Переустановите Windows начисто с официального образа\n"
        "3. НИКОГДА не используйте твикеры и подобные программы!\n\n"
    )

def display_startup_warnings():
    """
    Выполняет НЕКРИТИЧЕСКИЕ проверки запуска и отображает предупреждения
    
    Возвращает:
    - bool: True если запуск можно продолжать, False если запуск следует прервать
    """

    from log import log
    try:
        warnings = []
        
        # ✅ ТОЛЬКО НЕКРИТИЧЕСКИЕ ПРОВЕРКИ
        has_cmd_issues, cmd_msg = check_system_commands()
        if has_cmd_issues and cmd_msg:
            warnings.append(cmd_msg)
        
        if check_if_in_archive():
            error_message = (
                "Программа запущена из временной директории.\n\n"
                "Для корректной работы необходимо распаковать архив в постоянную директорию "
                "(например, C:\\zapretgui) и запустить программу оттуда.\n\n"
                "Продолжение работы возможно, но некоторые функции могут работать некорректно."
            )
            warnings.append(error_message)

        in_onedrive, msg = check_path_for_onedrive()
        if in_onedrive:
            warnings.append(msg)
                
        has_special_chars, error_message = check_path_for_special_chars()
        if has_special_chars:
            warnings.append(error_message)
        
        # Если есть предупреждения - показываем
        if warnings:
            full_message = "\n\n".join(warnings) + "\n\nПродолжить работу?"
            
            app_exists = QApplication.instance() is not None
            
            if app_exists:
                try:
                    result = QMessageBox.warning(
                        None, "Предупреждение",
                        full_message,
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                        QMessageBox.StandardButton.No
                    )
                    return result == QMessageBox.StandardButton.Yes
                except Exception as e:
                    log(f"Ошибка показа предупреждения: {e}", level="❌ ERROR")
                    btn = _native_message("Предупреждение",
                                        full_message,
                                        0x34)  # MB_ICONWARNING | MB_YESNO
                    return btn == 6  # IDYES
            else:
                btn = _native_message("Предупреждение", full_message, 0x34)
                return btn == 6
        
        return True
        
    except Exception as e:
        error_msg = f"Ошибка при проверке условий запуска: {str(e)}"
        log(error_msg, level="❌ CRITICAL")
        return False
        
def _service_exists_reg(name: str) -> bool:
    """
    Проверка через реестр: быстрее и не зависит от локали.
    """
    try:
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            fr"SYSTEM\CurrentControlSet\Services\{name}",
        )
        winreg.CloseKey(key)
        return True
    except FileNotFoundError:
        return False

def _service_exists_sc(name: str) -> bool:
    """
    Проверка через `sc query`.  Работает без прав администратора.
    """
    exe = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32", "sc.exe")
    proc = run_hidden(
        [exe, "query", name],
        capture_output=True,
        text=True,
        encoding="cp866",   # вывод консоли cmd.exe
        errors="ignore",
        creationflags=subprocess.CREATE_NO_WINDOW
    )
    if proc.returncode == 0:          # служба есть
        return True
    if proc.returncode == 1060:       # службы нет
        return False
    # Неопределённое состояние, но вывод всё-таки посмотрим:
    return "STATE" in proc.stdout.upper()

def _stop_and_delete_service(name: str) -> tuple[bool, str]:
    """
    Останавливает и удаляет службу Windows.
    Возвращает (успех, сообщение).
    """
    sc_exe = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32", "sc.exe")
    errors = []
    
    try:
        from log import log
    except ImportError:
        log = lambda msg, **kw: print(msg)
    
    # 1. Останавливаем службу
    try:
        log(f"Останавливаем службу {name}...", level="INFO")
        proc = run_hidden(
            [sc_exe, "stop", name],
            capture_output=True,
            text=True,
            encoding="cp866",
            errors="ignore",
            creationflags=subprocess.CREATE_NO_WINDOW,
            timeout=30
        )
        if proc.returncode == 0:
            log(f"Служба {name} остановлена", level="INFO")
        elif proc.returncode == 1062:  # служба не запущена
            log(f"Служба {name} уже остановлена", level="INFO")
        else:
            log(f"Код возврата sc stop: {proc.returncode}", level="DEBUG")
    except Exception as e:
        errors.append(f"Ошибка остановки: {e}")
        log(f"Ошибка остановки службы {name}: {e}", level="WARNING")
    
    # Небольшая пауза
    import time
    time.sleep(0.5)
    
    # 2. Удаляем службу
    try:
        log(f"Удаляем службу {name}...", level="INFO")
        proc = run_hidden(
            [sc_exe, "delete", name],
            capture_output=True,
            text=True,
            encoding="cp866",
            errors="ignore",
            creationflags=subprocess.CREATE_NO_WINDOW,
            timeout=30
        )
        if proc.returncode == 0:
            log(f"Служба {name} удалена", level="INFO")
            return True, f"Служба {name} успешно удалена"
        elif proc.returncode == 1060:  # служба не существует
            log(f"Служба {name} уже удалена", level="INFO")
            return True, f"Служба {name} уже была удалена"
        else:
            errors.append(f"Код возврата sc delete: {proc.returncode}")
            log(f"Код возврата sc delete: {proc.returncode}, stderr: {proc.stderr}", level="WARNING")
    except Exception as e:
        errors.append(f"Ошибка удаления: {e}")
        log(f"Ошибка удаления службы {name}: {e}", level="WARNING")
    
    if errors:
        return False, "; ".join(errors)
    return True, "OK"


def check_goodbyedpi() -> tuple[bool, str]:
    """
    Проверяет службы GoodbyeDPI и автоматически удаляет их.
    """
    
    SERVICE_NAMES = [
        "GoodbyeDPI",
        "GoodbyeDPI Service", 
        "GoodbyeDPI_x64",
        "GoodbyeDPI_x86",
    ]
    
    try:
        from log import log
    except ImportError:
        log = lambda msg, **kw: print(msg)

    found_services = []
    
    # Сначала находим все существующие службы
    for svc in SERVICE_NAMES:
        if _service_exists_reg(svc) or _service_exists_sc(svc):
            found_services.append(svc)
            log(f"Обнаружена служба GoodbyeDPI: {svc}", level="WARNING")
    
    if not found_services:
        # Кэшируем положительный результат
        startup_cache.cache_result("goodbyedpi_check", False)
        return False, ""
    
    # Пытаемся автоматически удалить найденные службы
    log(f"Автоматическое удаление служб GoodbyeDPI: {found_services}", level="INFO")
    
    failed_services = []
    success_services = []
    
    for svc in found_services:
        success, msg = _stop_and_delete_service(svc)
        if success:
            success_services.append(svc)
            log(f"Служба {svc}: {msg}", level="INFO")
        else:
            failed_services.append((svc, msg))
            log(f"Не удалось удалить службу {svc}: {msg}", level="ERROR")
    
    # Проверяем, остались ли службы после удаления
    still_exists = []
    for svc in found_services:
        if _service_exists_reg(svc) or _service_exists_sc(svc):
            still_exists.append(svc)
    
    if still_exists:
        # Не все службы удалены - возвращаем ошибку
        err = (
            f"Обнаружены службы GoodbyeDPI: {', '.join(still_exists)}\n\n"
            "Автоматическое удаление не удалось.\n"
            "Zapret 2 GUI несовместим с GoodbyeDPI.\n\n"
            "Удалите службы вручную командами (от администратора):\n"
        )
        for svc in still_exists:
            err += f"    sc stop {svc}\n    sc delete {svc}\n"
        err += "\nЗатем перезагрузите ПК и запустите программу снова."
        
        startup_cache.cache_result("goodbyedpi_check", True)
        return True, err
    
    # Все службы успешно удалены
    if success_services:
        log(f"Все службы GoodbyeDPI удалены: {success_services}", level="INFO")
    
    # Сбрасываем кэш так как состояние изменилось
    startup_cache.cache_result("goodbyedpi_check", False)
    return False, ""