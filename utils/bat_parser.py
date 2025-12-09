"""
Быстрый парсер .bat файлов для извлечения команды winws.exe
"""

import os
import re
from typing import Optional, List, Tuple

# Безопасный импорт log (для работы как в приложении, так и standalone)
try:
    from log import log
except ImportError:
    def log(msg, level="INFO"):
        print(f"[{level}] {msg}")


def parse_bat_file(bat_file_path: str, debug: bool = False) -> Optional[Tuple[str, List[str]]]:
    """
    Парсит .bat файл и извлекает команду запуска winws.exe
    
    Args:
        bat_file_path: Путь к .bat файлу
        debug: Включить подробный вывод отладки
        
    Returns:
        Tuple[exe_path, args] или None если не найдено
        - exe_path: Полный путь к winws.exe
        - args: Список аргументов команднойстроки
    """
    try:
        if not os.path.exists(bat_file_path):
            log(f"BAT файл не найден: {bat_file_path}", "ERROR")
            return None
        
        bat_dir = os.path.dirname(os.path.abspath(bat_file_path))
        if debug:
            log(f"Парсинг файла: {bat_file_path}", "INFO")
            log(f"Директория bat: {bat_dir}", "INFO")
        
        # Читаем все строки и склеиваем многострочные команды (с ^)
        lines = []
        with open(bat_file_path, 'r', encoding='utf-8-sig', errors='ignore') as f:
            all_lines = f.readlines()
        
        # Склеиваем строки с продолжением (^)
        i = 0
        while i < len(all_lines):
            line = all_lines[i].rstrip('\n\r')
            line_num = i + 1
            
            # Если строка заканчивается на ^, склеиваем со следующей
            while line.rstrip().endswith('^') and i + 1 < len(all_lines):
                line = line.rstrip()[:-1].rstrip() + ' ' + all_lines[i + 1].strip()
                i += 1
            
            lines.append((line_num, line.strip()))
            i += 1
        
        # Теперь парсим склеенные строки
        for line_num, line in lines:
            # Пропускаем пустые строки, комментарии, @echo
            if not line or line.startswith('REM') or line.startswith('::'):
                continue
            if line.lower().startswith('@echo'):
                continue
            
            # Ищем строку с winws.exe или winws2.exe
            if 'winws.exe' in line.lower() or 'winws2.exe' in line.lower():
                if debug:
                    log(f"Строка {line_num} содержит winws: {line[:100]}", "INFO")
                
                # Пропускаем служебные команды (остановка, очистка)
                line_lower = line.lower()
                skip_commands = ['taskkill', 'sc stop', 'sc delete', 'net stop', 'del ', 'rmdir']
                if any(cmd in line_lower for cmd in skip_commands):
                    if debug:
                        log(f"  -> Пропущено (служебная команда)", "INFO")
                    continue
                
                # Убираем start с параметрами
                # Формат: start ["название"] [/b] [/wait] путь_к_программе
                line = re.sub(r'^\s*start\s+"[^"]*"\s+/b\s+', '', line, flags=re.IGNORECASE)
                line = re.sub(r'^\s*start\s+/b\s+', '', line, flags=re.IGNORECASE)
                line = re.sub(r'^\s*start\s+"[^"]*"\s+', '', line, flags=re.IGNORECASE)
                line = re.sub(r'^\s*start\s+', '', line, flags=re.IGNORECASE)
                
                # Разворачиваем переменные окружения относительно bat_dir
                line = _expand_bat_variables(line, bat_dir)
                
                if debug:
                    log(f"  -> После обработки: {line[:150]}", "INFO")
                
                # Парсим команду
                parsed = _parse_command_line(line, bat_dir)
                if parsed:
                    exe_path, args = parsed
                    log(f"✅ Найдена команда winws в строке {line_num}: {exe_path}", "INFO")
                    return (exe_path, args)
                elif debug:
                    log(f"  -> Не удалось распарсить строку", "WARNING")
        
        log(f"❌ Команда winws не найдена в {os.path.basename(bat_file_path)}", "WARNING")
        return None
        
    except Exception as e:
        log(f"Ошибка парсинга .bat файла: {e}", "ERROR")
        return None


def _parse_command_line(line: str, bat_dir: str) -> Optional[Tuple[str, List[str]]]:
    """
    Парсит командную строку и извлекает exe и аргументы
    
    Args:
        line: Строка команды
        bat_dir: Директория где находится .bat файл
        
    Returns:
        Tuple[exe_path, args] или None
    """
    try:
        # Простой парсинг с учётом кавычек
        parts = []
        current = []
        in_quotes = False
        
        for char in line:
            if char == '"':
                in_quotes = not in_quotes
                current.append(char)
            elif char == ' ' and not in_quotes:
                if current:
                    parts.append(''.join(current))
                    current = []
            else:
                current.append(char)
        
        if current:
            parts.append(''.join(current))
        
        if not parts:
            return None
        
        # Первая часть - exe файл
        exe_part = parts[0].strip('"')
        
        # Разрешаем относительные пути
        if not os.path.isabs(exe_part):
            # Попробуем относительно bat_dir
            potential_path = os.path.join(bat_dir, exe_part)
            if os.path.exists(potential_path):
                exe_path = os.path.abspath(potential_path)
            else:
                # Попробуем относительно bat_dir/../exe
                potential_path = os.path.join(bat_dir, '..', 'exe', exe_part)
                if os.path.exists(potential_path):
                    exe_path = os.path.abspath(potential_path)
                else:
                    # Попробуем поиск winws.exe в стандартных местах
                    exe_path = _find_winws_exe(bat_dir)
                    if not exe_path:
                        log(f"winws.exe не найден для пути: {exe_part}", "WARNING")
                        return None
        else:
            exe_path = os.path.abspath(exe_part)
        
        # Проверяем что exe существует
        if not os.path.exists(exe_path):
            log(f"Исполняемый файл не найден: {exe_path}", "WARNING")
            # Попробуем найти автоматически
            exe_path = _find_winws_exe(bat_dir)
            if not exe_path:
                return None
        
        # Остальные части - аргументы
        args = []
        for part in parts[1:]:
            # Убираем внешние кавычки, но сохраняем внутренние
            part = part.strip()
            if part.startswith('"') and part.endswith('"') and len(part) > 2:
                part = part[1:-1]
            
            # Разворачиваем переменные в каждом аргументе (важно для %LISTS%, %BIN% и т.д.)
            part = _expand_bat_variables(part, bat_dir)
            
            args.append(part)
        
        return (exe_path, args)
        
    except Exception as e:
        log(f"Ошибка парсинга командной строки: {e}", "DEBUG")
        return None


def _expand_bat_variables(line: str, bat_dir: str) -> str:
    """
    Разворачивает переменные окружения в .bat файлах
    
    Args:
        line: Строка с потенциальными переменными
        bat_dir: Директория где находится .bat файл
        
    Returns:
        Строка с развёрнутыми переменными
    """
    try:
        original = line
        
        # %~dp0 - путь к директории bat файла
        line = line.replace('%~dp0', bat_dir + '\\')
        
        # Типичная структура: zapret/bat/*.bat и zapret/exe/winws.exe и zapret/lists/
        parent_dir = os.path.dirname(bat_dir)  # Родительская папка (zapret/)
        
        # %EXE% - обычно это ../exe относительно bat/
        exe_dir = os.path.join(parent_dir, 'exe')
        exe_dir = os.path.abspath(exe_dir)
        
        line = line.replace('%EXE%', exe_dir)
        line = line.replace('%exe%', exe_dir)
        
        # %LISTS% - обычно это ../lists относительно bat/
        lists_dir = os.path.join(parent_dir, 'lists')
        lists_dir = os.path.abspath(lists_dir)
        
        line = line.replace('%LISTS%', lists_dir)
        line = line.replace('%lists%', lists_dir)
        
        # %BIN% - обычно это ../bin относительно bat/
        bin_dir = os.path.join(parent_dir, 'bin')
        bin_dir = os.path.abspath(bin_dir)
        
        line = line.replace('%BIN%', bin_dir)
        line = line.replace('%bin%', bin_dir)
        
        # Также попробуем системные переменные
        line = os.path.expandvars(line)
        
        # Логируем если переменные были развёрнуты
        if line != original and '%' in original:
            log(f"📦 Переменные развёрнуты: {original[:60]}... → {line[:60]}...", "DEBUG")
        
        return line
    except Exception as e:
        log(f"Ошибка разворачивания переменных: {e}", "DEBUG")
        return line


def _find_winws_exe(bat_dir: str) -> Optional[str]:
    """
    Ищет winws.exe в стандартных местах
    
    Args:
        bat_dir: Директория где находится .bat файл
        
    Returns:
        Полный путь к winws.exe или None
    """
    # Возможные пути относительно bat_dir
    possible_paths = [
        os.path.join(bat_dir, '..', 'exe', 'winws.exe'),
        os.path.join(bat_dir, '..', 'exe', 'winws2.exe'),
        os.path.join(bat_dir, 'winws.exe'),
        os.path.join(bat_dir, 'winws2.exe'),
    ]
    
    # Также попробуем через config
    try:
        from config import WINWS_EXE, WINWS2_EXE
        possible_paths.extend([WINWS_EXE, WINWS2_EXE])
    except:
        pass
    
    for path in possible_paths:
        abs_path = os.path.abspath(path)
        if os.path.exists(abs_path):
            log(f"Найден winws.exe: {abs_path}", "DEBUG")
            return abs_path
    
    log("winws.exe не найден в стандартных местах", "WARNING")
    return None


def create_process_direct(exe_path: str, args: List[str], working_dir: Optional[str] = None) -> bool:
    """
    Запускает процесс напрямую через CreateProcess (Win API)
    
    Args:
        exe_path: Полный путь к исполняемому файлу
        args: Список аргументов
        working_dir: Рабочая директория (по умолчанию - директория exe)
        
    Returns:
        True если процесс запущен успешно
    """
    try:
        import ctypes
        from ctypes import wintypes
        
        # Рабочая директория
        if not working_dir:
            working_dir = os.path.dirname(exe_path)
        
        # Формируем командную строку
        # Заключаем exe в кавычки если есть пробелы
        if ' ' in exe_path:
            cmd_line = f'"{exe_path}"'
        else:
            cmd_line = exe_path
        
        # Добавляем аргументы
        for arg in args:
            # Заключаем в кавычки если есть пробелы и ещё не в кавычках
            if ' ' in arg and not (arg.startswith('"') and arg.endswith('"')):
                cmd_line += f' "{arg}"'
            else:
                cmd_line += f' {arg}'
        
        log(f"Запуск: {cmd_line[:200]}{'...' if len(cmd_line) > 200 else ''}", "DEBUG")
        
        # Структуры Win API
        class STARTUPINFO(ctypes.Structure):
            _fields_ = [
                ("cb", wintypes.DWORD),
                ("lpReserved", wintypes.LPWSTR),
                ("lpDesktop", wintypes.LPWSTR),
                ("lpTitle", wintypes.LPWSTR),
                ("dwX", wintypes.DWORD),
                ("dwY", wintypes.DWORD),
                ("dwXSize", wintypes.DWORD),
                ("dwYSize", wintypes.DWORD),
                ("dwXCountChars", wintypes.DWORD),
                ("dwYCountChars", wintypes.DWORD),
                ("dwFillAttribute", wintypes.DWORD),
                ("dwFlags", wintypes.DWORD),
                ("wShowWindow", wintypes.WORD),
                ("cbReserved2", wintypes.WORD),
                ("lpReserved2", ctypes.POINTER(wintypes.BYTE)),
                ("hStdInput", wintypes.HANDLE),
                ("hStdOutput", wintypes.HANDLE),
                ("hStdError", wintypes.HANDLE),
            ]
        
        class PROCESS_INFORMATION(ctypes.Structure):
            _fields_ = [
                ("hProcess", wintypes.HANDLE),
                ("hThread", wintypes.HANDLE),
                ("dwProcessId", wintypes.DWORD),
                ("dwThreadId", wintypes.DWORD),
            ]
        
        # Инициализация структур
        startup_info = STARTUPINFO()
        startup_info.cb = ctypes.sizeof(STARTUPINFO)
        startup_info.dwFlags = 0x00000001  # STARTF_USESHOWWINDOW
        startup_info.wShowWindow = 0  # SW_HIDE
        
        process_info = PROCESS_INFORMATION()
        
        # Флаги создания процесса
        CREATE_NEW_CONSOLE = 0x00000010
        CREATE_NO_WINDOW = 0x08000000
        DETACHED_PROCESS = 0x00000008
        
        # Вызываем CreateProcessW
        kernel32 = ctypes.windll.kernel32
        result = kernel32.CreateProcessW(
            exe_path,  # lpApplicationName
            cmd_line,  # lpCommandLine
            None,  # lpProcessAttributes
            None,  # lpThreadAttributes
            False,  # bInheritHandles
            CREATE_NO_WINDOW,  # dwCreationFlags
            None,  # lpEnvironment
            working_dir,  # lpCurrentDirectory
            ctypes.byref(startup_info),  # lpStartupInfo
            ctypes.byref(process_info)  # lpProcessInformation
        )
        
        if result:
            log(f"✅ Процесс запущен через CreateProcess (PID: {process_info.dwProcessId})", "SUCCESS")
            
            # Закрываем handle'ы
            kernel32.CloseHandle(process_info.hProcess)
            kernel32.CloseHandle(process_info.hThread)
            
            return True
        else:
            error_code = kernel32.GetLastError()
            log(f"❌ CreateProcess failed с кодом ошибки: {error_code}", "ERROR")
            return False
            
    except Exception as e:
        log(f"Ошибка CreateProcess: {e}", "ERROR")
        import traceback
        log(traceback.format_exc(), "DEBUG")
        return False

