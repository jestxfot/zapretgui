import os
import sys
from PyQt6.QtWidgets import QMessageBox, QApplication
import ctypes, sys, subprocess, winreg

# Импортируем константы из конфига
from config.config import BIN_FOLDER

def _native_message(title: str, text: str, style=0x00000010):  # MB_ICONERROR
    """
    Показывает нативное окно MessageBox (не требует QApplication)
    style: 0x10 = MB_ICONERROR,  0x30 = MB_ICONWARNING | MB_YESNO
    """
    ctypes.windll.user32.MessageBoxW(0, text, title, style)
    
def check_if_in_archive():
    """
    Проверяет, находится ли EXE-файл в временной директории,
    что обычно характерно для распаковки из архива.
    """
    try:
        exe_path = os.path.abspath(sys.executable)
        try:
            from log import log
            log(f"Executable path: {exe_path}", level="CHECK_START")
        except ImportError:
            log(f"DEBUG: Executable path: {exe_path}")

        # Получаем пути к системным временным директориям
        system32_path = os.path.abspath(os.path.join(os.environ.get("WINDIR", ""), "System32"))
        temp_env = os.environ.get("TEMP", "")
        tmp_env = os.environ.get("TMP", "")
        temp_dirs = [temp_env, tmp_env, system32_path]
        
        for temp_dir in temp_dirs:
            if temp_dir and exe_path.lower().startswith(os.path.abspath(temp_dir).lower()):
                try:
                    from log import log
                    log(f"EXE запущен из временной директории: {temp_dir}", level="WARNING")
                except ImportError:
                    log(f"WARNING: EXE запущен из временной директории: {temp_dir}")
                return True
        return False
    except Exception as e:
        log(f"DEBUG: Ошибка при проверке расположения EXE: {str(e)}")
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
    Проверяет, лежит ли программа (или вспомогательные папки) в OneDrive.
    Возвращает (True, msg) если обнаружен OneDrive, иначе (False, "").
    """
    current_path = os.path.abspath(os.getcwd())
    exe_path     = os.path.abspath(sys.executable)

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
                log(f"ERROR: Обнаружен OneDrive в пути: {path}", level="ERROR")
            except ImportError:
                log(f"ERROR: Обнаружен OneDrive в пути: {path}")
            return True, err
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
    """Проверяет пути программы на наличие специальных символов"""
    current_path = os.path.abspath(os.getcwd())
    exe_path = os.path.abspath(sys.executable)
    
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
                log(f"ERROR: Путь содержит специальные символы: {path}", level="ERROR")
            except ImportError:
                log(f"ERROR: Путь содержит специальных символов: {path}")
            return True, error_message
    return False, ""

# Изменяем функцию для работы с уже созданным QApplication
def display_startup_warnings():
    """
    Выполняет проверки запуска и отображает предупреждения если необходимо
    
    Возвращает:
    - bool: True если запуск можно продолжать, False если запуск следует прервать
    """
    success, message = check_startup_conditions()
    
    if not success:
        # Определяем, является ли ошибка критической
        is_critical = "специальные символы" in message

        app_exists = QApplication.instance() is not None

        if is_critical:
            if app_exists:
                QMessageBox.critical(None, "Критическая ошибка", message)
            else:
                _native_message("Критическая ошибка", message, 0x10)
            return False
        else:
            if app_exists:
                result = QMessageBox.warning(
                    None, "Предупреждение",
                    message,
                    QMessageBox.StandardButton.No
                )
                return result == QMessageBox.StandardButton.Yes
            else:
                btn = _native_message("Предупреждение",
                                    message + "\n\nНажмите «Да» для продолжения.",
                                    0x30)  # MB_ICONWARNING | MB_YESNO
                return btn == 6  # IDYES
    return True

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
    proc = subprocess.run(
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

def check_goodbyedpi() -> tuple[bool, str]:
    """
    True + msg, если обнаружена любая из служб GoodbyeDPI.
    """
    SERVICE_NAMES = [
        "GoodbyeDPI",            # стандартное имя из install_service.bat
        "GoodbyeDPI Service",
        "GoodbyeDPI_x64",
        "GoodbyeDPI_x86",
    ]

    for svc in SERVICE_NAMES:
        if _service_exists_reg(svc) or _service_exists_sc(svc):
            err = (
                "Обнаружена установленная служба ГудБайДипиАй "
                f"её название - {svc}.\n\n"
                "Zapret GUI несовместим с GoodbyeDPI.\n"
                "Полностью удалите службу командами:\n"
                "    sc stop GoodbyeDPI\n"
                "    sc delete GoodbyeDPI\n"
                "Затем перезагрузите ПК и запустите программу снова."
            )
            try:
                from log import log
                log(f"ERROR: Найдена служба {svc}", level="ERROR")
            except ImportError:
                print(f"ERROR: Найдена служба {svc}")
            return True, err
    return False, ""





def check_startup_conditions():
    """
    Выполняет все проверки условий запуска программы
    
    Возвращает:
    - tuple: (success, error_message)
        - success (bool): True если все проверки успешны, False в противном случае
        - error_message (str): текст сообщения об ошибке, если проверка не пройдена
    """
    try:
        has_gdpi, gdpi_msg = check_goodbyedpi()
        if has_gdpi:
            return False, gdpi_msg
        
        # Проверка на запуск из архива
        if check_if_in_archive():
            error_message = (
                "Программа запущена из временной директории.\n\n"
                "Для корректной работы необходимо распаковать архив в постоянную директорию "
                "(например, C:\\zapretgui) и запустить программу оттуда.\n\n"
                "Продолжение работы возможно, но некоторые функции могут работать некорректно."
            )
            return False, error_message

        # Проверка на наличие OneDrive в пути
        in_onedrive, msg = check_path_for_onedrive()
        if in_onedrive:
            return False, msg
                
        # Проверка на специальные символы в пути
        has_special_chars, error_message = check_path_for_special_chars()
        if has_special_chars:
            return False, error_message
        
        # Все проверки успешны
        return True, ""
    except Exception as e:
        error_message = f"Ошибка при выполнении проверок запуска: {str(e)}"
        try:
            from log import log
            log(error_message, level="ERROR")
        except ImportError:
            log(f"ERROR: {error_message}")
        return False, error_message