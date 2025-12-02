"""
Модуль для создания Windows службы для Direct режима (Zapret 2).
Использует прямой Windows API для максимальной скорости.
"""

import os
import time
from pathlib import Path
from typing import Optional, Callable, List
from log import log
from .registry_check import set_autostart_enabled
from .service_api import (
    create_bat_service,
    create_zapret_service,
    delete_service,
    start_service,
    stop_service,
    service_exists
)

SERVICE_NAME = "ZapretDirectService"
SERVICE_DISPLAY_NAME = "Zapret Direct Mode Service"
SERVICE_DESCRIPTION = "Запускает Zapret в Direct режиме при загрузке системы"


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
        
        # Применяем ВСЕ фильтры в правильном порядке
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


def setup_direct_service(
    winws_exe: str,
    strategy_args: List[str],
    strategy_name: str = "Direct",
    ui_error_cb: Optional[Callable[[str], None]] = None
) -> bool:
    """
    Создает Windows службу через API для запуска Direct режима.
    Использует прямой Windows API - намного быстрее чем NSSM/sc.exe!
    """
    try:
        from config import MAIN_DIRECTORY, LOGS_FOLDER
        from .autostart_direct import _resolve_file_paths
        from strategy_menu.apply_filters import apply_all_filters
        
        # Создаем папку для логов если её нет
        os.makedirs(LOGS_FOLDER, exist_ok=True)
        
        if not os.path.exists(winws_exe):
            error_msg = f"winws.exe не найден: {winws_exe}"
            log(error_msg, "❌ ERROR")
            if ui_error_cb:
                ui_error_cb(error_msg)
            return False
        
        log(f"Создание службы Direct режима через API...", "INFO")
        
        # Разрешаем пути в аргументах
        resolved_args = _resolve_file_paths(strategy_args, MAIN_DIRECTORY)
        
        # Применяем ВСЕ фильтры
        lists_dir = os.path.join(MAIN_DIRECTORY, "lists")
        resolved_args = apply_all_filters(resolved_args, lists_dir)
        
        # Метод 1: Пробуем создать службу напрямую для winws.exe
        # (работает если длина командной строки < 32767 символов)
        log("Попытка создания службы напрямую для winws.exe...", "DEBUG")
        
        if create_zapret_service(
            service_name=SERVICE_NAME,
            display_name=SERVICE_DISPLAY_NAME,
            exe_path=winws_exe,
            args=resolved_args,
            description=f"{SERVICE_DESCRIPTION} (стратегия: {strategy_name})",
            auto_start=True
        ):
            # Запускаем службу
            if start_service(SERVICE_NAME):
                log(f"Служба {SERVICE_NAME} создана и запущена", "✅ SUCCESS")
            else:
                log(f"Служба создана, но не удалось запустить (может потребоваться перезагрузка)", "WARNING")
            
            set_autostart_enabled(True, "direct_service")
            # Сообщение об успехе показывает вызывающий код
            return True
        
        # Метод 2: Если не удалось - используем .bat файл
        log("Прямой метод не сработал, используем .bat файл...", "INFO")
        
        bat_path = create_direct_service_bat(winws_exe, strategy_args, MAIN_DIRECTORY)
        if not bat_path:
            error_msg = "Не удалось создать .bat файл для службы"
            log(error_msg, "❌ ERROR")
            if ui_error_cb:
                ui_error_cb(error_msg)
            return False
        
        if create_bat_service(
            service_name=SERVICE_NAME,
            display_name=SERVICE_DISPLAY_NAME,
            bat_path=bat_path,
            description=f"{SERVICE_DESCRIPTION} (стратегия: {strategy_name})",
            auto_start=True
        ):
            # Запускаем службу
            if start_service(SERVICE_NAME):
                log(f"Служба {SERVICE_NAME} создана через .bat и запущена", "✅ SUCCESS")
            else:
                log(f"Служба создана, но не удалось запустить", "WARNING")
            
            set_autostart_enabled(True, "direct_service")
            # Сообщение об успехе показывает вызывающий код
            return True
        
        error_msg = "Не удалось создать службу ни одним из методов"
        log(error_msg, "❌ ERROR")
        if ui_error_cb:
            ui_error_cb(error_msg)
        return False
            
    except Exception as e:
        log(f"Ошибка создания службы: {e}", "❌ ERROR")
        import traceback
        log(traceback.format_exc(), "DEBUG")
        if ui_error_cb:
            ui_error_cb(f"Ошибка: {e}")
        return False


def remove_direct_service() -> bool:
    """
    Удаляет службу Direct режима через API
    """
    try:
        result = delete_service(SERVICE_NAME)
        
        # Удаляем .bat файл
        from config import MAIN_DIRECTORY
        bat_path = os.path.join(MAIN_DIRECTORY, "zapret_service.bat")
        if os.path.exists(bat_path):
            try:
                os.remove(bat_path)
                log(f"Удален файл: {bat_path}", "DEBUG")
            except:
                pass
        
        return result
        
    except Exception as e:
        log(f"Ошибка при удалении службы: {e}", "⚠ WARNING")
        return False


def check_direct_service_exists() -> bool:
    """
    Проверяет существование службы Direct режима
    """
    return service_exists(SERVICE_NAME)


def stop_direct_service() -> bool:
    """Останавливает службу Direct режима"""
    return stop_service(SERVICE_NAME)


def start_direct_service() -> bool:
    """Запускает службу Direct режима"""
    return start_service(SERVICE_NAME)
