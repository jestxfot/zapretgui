"""
Модуль для создания Windows службы для Direct режима через NSSM.
NSSM должен находиться в папке exe/ рядом с winws.exe
"""

import os
import subprocess
import time
from pathlib import Path
from typing import Optional, Callable, List
from log import log
from utils import run_hidden
from .registry_check import set_autostart_enabled

SERVICE_NAME = "ZapretDirectService"
SERVICE_DISPLAY_NAME = "Zapret Direct Mode Service"
SERVICE_DESCRIPTION = "Запускает Zapret в Direct режиме при загрузке системы"

def get_nssm_path() -> Optional[str]:
    """
    Возвращает путь к nssm.exe из папки exe/
    """
    try:
        from config import EXE_FOLDER
        
        # Ищем nssm.exe в папке exe
        nssm_path = os.path.join(EXE_FOLDER, "nssm.exe")
        
        if os.path.exists(nssm_path):
            log(f"NSSM найден: {nssm_path}", "DEBUG")
            return nssm_path
        
        # Альтернативное имя (на случай если переименован)
        nssm_x64_path = os.path.join(EXE_FOLDER, "nssm-x64.exe")
        if os.path.exists(nssm_x64_path):
            log(f"NSSM найден: {nssm_x64_path}", "DEBUG")
            return nssm_x64_path
            
        log(f"NSSM не найден в {EXE_FOLDER}", "⚠ WARNING")
        return None
        
    except Exception as e:
        log(f"Ошибка поиска NSSM: {e}", "❌ ERROR")
        return None


def create_direct_service_bat(
    winws_exe: str,
    strategy_args: List[str],
    work_dir: str
) -> Optional[str]:
    """
    Создает zapret_service.bat файл для запуска из службы
    """
    try:
        from .autostart_direct import _resolve_file_paths
        from config import MAIN_DIRECTORY
        from strategy_menu.apply_filters import apply_all_filters
        
        # Разрешаем пути
        resolved_args = _resolve_file_paths(strategy_args, work_dir)
        
        # ✅ Применяем ВСЕ фильтры в правильном порядке
        lists_dir = os.path.join(work_dir, "lists")
        resolved_args = apply_all_filters(resolved_args, lists_dir)
        
        # Создаем .bat файл в корневой папке программы
        bat_path = os.path.join(MAIN_DIRECTORY, "zapret_service.bat")
        
        # Создаем содержимое .bat файла
        bat_content = f"""@echo off
chcp 65001 > nul
setlocal EnableDelayedExpansion
cd /d "{work_dir}"

echo [%date% %time%] Starting Zapret Direct Service... >> "{work_dir}\\logs\\service_start.log"
echo Working directory: %cd% >> "{work_dir}\\logs\\service_start.log"

:START
"{winws_exe}" {' '.join(resolved_args)}

set EXIT_CODE=%ERRORLEVEL%
echo [%date% %time%] Process exited with code: !EXIT_CODE! >> "{work_dir}\\logs\\service_start.log"

if !EXIT_CODE! neq 0 (
    echo Restarting in 5 seconds... >> "{work_dir}\\logs\\service_start.log"
    timeout /t 5 /nobreak > nul
    goto START
)

exit /b !EXIT_CODE!
"""
        
        # Записываем файл с UTF-8 BOM для правильной кодировки
        with open(bat_path, 'w', encoding='utf-8-sig') as f:
            f.write(bat_content)
        
        log(f"Создан .bat файл для службы: {bat_path}", "INFO")
        return bat_path
        
    except Exception as e:
        log(f"Ошибка создания .bat файла для службы: {e}", "❌ ERROR")
        return None


def setup_direct_service_alternative(
    winws_exe: str,
    strategy_args: List[str],
    work_dir: str
) -> bool:
    """
    Альтернативный метод: устанавливает службу напрямую для winws.exe через NSSM
    """
    try:
        nssm_path = get_nssm_path()
        if not nssm_path:
            return False
        
        from .autostart_direct import _resolve_file_paths
        from strategy_menu.apply_filters import apply_all_filters
        
        # Разрешаем пути
        resolved_args = _resolve_file_paths(strategy_args, work_dir)
        
        # ✅ Применяем ВСЕ фильтры в правильном порядке
        lists_dir = os.path.join(work_dir, "lists")
        resolved_args = apply_all_filters(resolved_args, lists_dir)
        
        # Удаляем старую службу
        remove_direct_service()
        
        # Устанавливаем службу напрямую для winws.exe
        install_cmd = [nssm_path, "install", SERVICE_NAME, winws_exe]
        
        # Добавляем аргументы
        for arg in resolved_args:
            install_cmd.append(arg)
        
        log(f"Альтернативная установка службы напрямую для winws.exe", "INFO")
        
        result = run_hidden(
            install_cmd,
            capture_output=True,
            text=True,
            encoding="cp866",
            errors="ignore"
        )
        
        if result.returncode == 0:
            # Настраиваем дополнительные параметры
            from config import LOGS_FOLDER
            os.makedirs(LOGS_FOLDER, exist_ok=True)
            
            settings = [
                ["set", SERVICE_NAME, "DisplayName", SERVICE_DISPLAY_NAME],
                ["set", SERVICE_NAME, "Description", SERVICE_DESCRIPTION],
                ["set", SERVICE_NAME, "AppDirectory", work_dir],
                ["set", SERVICE_NAME, "Start", "SERVICE_AUTO_START"],
                ["set", SERVICE_NAME, "AppStdout", os.path.join(LOGS_FOLDER, "winws_stdout.log")],
                ["set", SERVICE_NAME, "AppStderr", os.path.join(LOGS_FOLDER, "winws_stderr.log")],
                ["set", SERVICE_NAME, "AppRotateFiles", "1"],
                ["set", SERVICE_NAME, "AppRotateBytes", "2097152"],
                ["set", SERVICE_NAME, "AppExit", "Default", "Restart"],
                ["set", SERVICE_NAME, "AppRestartDelay", "5000"],
            ]
            
            for args in settings:
                cmd = [nssm_path] + args
                run_hidden(cmd, capture_output=True)
            
            # Запускаем службу
            run_hidden([nssm_path, "start", SERVICE_NAME], capture_output=True)
            
            return True
        
        return False
        
    except Exception as e:
        log(f"Ошибка альтернативной установки: {e}", "ERROR")
        return False


def setup_direct_service(
    winws_exe: str,
    strategy_args: List[str],
    strategy_name: str = "Direct",
    ui_error_cb: Optional[Callable[[str], None]] = None
) -> bool:
    """
    Создает Windows службу через NSSM для запуска Direct режима
    """
    try:
        # Проверяем, не запущен ли уже winws.exe
        try:
            log("Проверка запущенных процессов winws.exe...", "INFO")
            
            # Используем taskkill для остановки всех winws.exe
            kill_result = run_hidden(
                ["taskkill", "/F", "/IM", "winws.exe"],
                capture_output=True,
                text=True,
                encoding="cp866",
                errors="ignore"
            )
            
            if kill_result.returncode == 0:
                log("Остановлены существующие процессы winws.exe", "INFO")
                time.sleep(2)  # Даем время на завершение
            else:
                log("Процессы winws.exe не найдены или не удалось остановить", "DEBUG")
                
        except Exception as e:
            log(f"Ошибка при остановке процессов: {e}", "WARNING")
        
        # Проверяем наличие NSSM
        nssm_path = get_nssm_path()
        if not nssm_path:
            error_msg = (
                "NSSM.exe не найден!\n\n"
                "Для создания службы необходим NSSM (Non-Sucking Service Manager).\n"
                "Скачайте nssm.exe с https://nssm.cc/ и поместите в папку 'exe'\n"
                "рядом с winws.exe"
            )
            log(error_msg, "❌ ERROR")
            if ui_error_cb:
                ui_error_cb(error_msg)
            return False
        
        if not os.path.exists(winws_exe):
            error_msg = f"winws.exe не найден: {winws_exe}"
            log(error_msg, "❌ ERROR")
            if ui_error_cb:
                ui_error_cb(error_msg)
            return False
        
        # Определяем директории
        from config import MAIN_DIRECTORY, LOGS_FOLDER
        
        # Создаем папку для логов если её нет
        os.makedirs(LOGS_FOLDER, exist_ok=True)
        
        # Сначала пробуем альтернативный метод (напрямую winws.exe)
        log("Пробуем установить службу напрямую для winws.exe...", "INFO")
        if setup_direct_service_alternative(winws_exe, strategy_args, MAIN_DIRECTORY):
            log(f"Служба {SERVICE_NAME} успешно создана (альтернативный метод)", "✅ SUCCESS")
            set_autostart_enabled(True, "direct_service")
            
            if ui_error_cb:
                ui_error_cb(
                    "✅ Служба Windows создана!\n\n"
                    f"Служба '{SERVICE_DISPLAY_NAME}' установлена.\n"
                    "Zapret будет автоматически запускаться при загрузке системы."
                )
            return True
        
        log("Альтернативный метод не сработал, используем .bat файл...", "INFO")
        
        # Создаем .bat файл
        bat_path = create_direct_service_bat(winws_exe, strategy_args, MAIN_DIRECTORY)
        if not bat_path:
            error_msg = "Не удалось создать .bat файл для службы"
            log(error_msg, "❌ ERROR")
            if ui_error_cb:
                ui_error_cb(error_msg)
            return False
        
        # Удаляем старую службу если есть
        remove_direct_service()
        
        # Устанавливаем службу для .bat файла напрямую
        install_cmd = [nssm_path, "install", SERVICE_NAME, bat_path]
        
        log(f"Установка службы для .bat: {' '.join(install_cmd)}", "DEBUG")
        
        result = run_hidden(
            install_cmd,
            capture_output=True,
            text=True,
            encoding="cp866",
            errors="ignore"
        )
        
        if result.returncode != 0:
            error_msg = f"Не удалось установить службу через NSSM.\nКод: {result.returncode}\n{result.stderr}"
            log(error_msg, "❌ ERROR")
            if ui_error_cb:
                ui_error_cb(error_msg)
            return False
        
        log("Служба установлена, настраиваем параметры...", "INFO")
        
        # Настраиваем параметры службы
        settings = [
            ["set", SERVICE_NAME, "DisplayName", SERVICE_DISPLAY_NAME],
            ["set", SERVICE_NAME, "Description", SERVICE_DESCRIPTION],
            ["set", SERVICE_NAME, "AppDirectory", MAIN_DIRECTORY],
            ["set", SERVICE_NAME, "Start", "SERVICE_AUTO_START"],
            ["set", SERVICE_NAME, "AppStdout", os.path.join(LOGS_FOLDER, "zapret_service_stdout.log")],
            ["set", SERVICE_NAME, "AppStderr", os.path.join(LOGS_FOLDER, "zapret_service_stderr.log")],
            ["set", SERVICE_NAME, "AppRotateFiles", "1"],
            ["set", SERVICE_NAME, "AppRotateOnline", "1"],
            ["set", SERVICE_NAME, "AppRotateBytes", "2097152"],
            ["set", SERVICE_NAME, "AppExit", "Default", "Restart"],
            ["set", SERVICE_NAME, "AppRestartDelay", "5000"],
        ]
        
        for args in settings:
            cmd = [nssm_path] + args
            run_hidden(cmd, capture_output=True)
        
        # Запускаем службу
        log("Запуск службы...", "INFO")
        start_result = run_hidden(
            [nssm_path, "start", SERVICE_NAME],
            capture_output=True,
            text=True,
            encoding="cp866",
            errors="ignore"
        )
        
        if start_result.returncode != 0:
            log(f"Попытка запуска через sc...", "INFO")
            run_hidden(["sc", "start", SERVICE_NAME], capture_output=True)
        
        # Проверяем статус
        time.sleep(2)
        
        log(f"Служба {SERVICE_NAME} создана", "✅ SUCCESS")
        set_autostart_enabled(True, "direct_service")
        
        if ui_error_cb:
            ui_error_cb(
                "✅ Служба Windows создана!\n\n"
                f"Служба '{SERVICE_DISPLAY_NAME}' установлена и запущена.\n\n"
                "Zapret теперь работает как системная служба и будет\n"
                "автоматически запускаться при загрузке Windows.\n\n"
                "Примечание: GUI-версия Zapret была остановлена.\n"
                "Для управления службой используйте:\n"
                "• services.msc (Службы Windows)\n"
                "• Или кнопку 'Выкл. автозапуск' в программе"
            )
        return True
            
    except Exception as e:
        log(f"Ошибка создания службы: {e}", "❌ ERROR")
        if ui_error_cb:
            ui_error_cb(f"Ошибка: {e}")
        return False


def remove_direct_service() -> bool:
    """
    Удаляет службу Direct режима
    """
    try:
        nssm_path = get_nssm_path()
        
        if nssm_path and os.path.exists(nssm_path):
            run_hidden([nssm_path, "stop", SERVICE_NAME], capture_output=True)
            time.sleep(1)
            run_hidden([nssm_path, "remove", SERVICE_NAME, "confirm"], capture_output=True)
        
        run_hidden(["sc", "stop", SERVICE_NAME], capture_output=True)
        time.sleep(1)
        run_hidden(["sc", "delete", SERVICE_NAME], capture_output=True)
        
        # Удаляем .bat файл
        from config import MAIN_DIRECTORY
        bat_path = os.path.join(MAIN_DIRECTORY, "zapret_service.bat")
        if os.path.exists(bat_path):
            try:
                os.remove(bat_path)
                log(f"Удален файл: {bat_path}", "DEBUG")
            except:
                pass
        
        return True
        
    except Exception as e:
        log(f"Ошибка при удалении службы: {e}", "⚠ WARNING")
        return False


def check_direct_service_exists() -> bool:
    """
    Проверяет существование службы Direct режима
    """
    try:
        result = run_hidden(
            ["sc", "query", SERVICE_NAME],
            capture_output=True,
            text=True,
            encoding="cp866",
            errors="ignore"
        )
        return result.returncode == 0 and "STATE" in result.stdout
    except:
        return False