# bfe_util.py

from typing import Optional
import time, win32service, ctypes, win32serviceutil
from PyQt6.QtWidgets import QWidget
SERVICE_RUNNING = win32service.SERVICE_RUNNING
ERROR_SERVICE_DOES_NOT_EXIST = 1060

def _native_msg(title: str, text: str, icon: int = 0x40):
    # icon: 0x40 = MB_ICONINFORMATION, 0x10 = MB_ICONERROR
    ctypes.windll.user32.MessageBoxW(None, text, title, icon)

def is_service_running(name: str) -> bool:
    scm = win32service.OpenSCManager(None, None,
                                     win32service.SC_MANAGER_CONNECT)
    try:
        try:
            svc = win32service.OpenService(scm, name,
                                           win32service.SERVICE_QUERY_STATUS)
        except win32service.error as e:
            # Если службы нет – просто возвращаем False
            if e.winerror == ERROR_SERVICE_DOES_NOT_EXIST:
                return False
            raise                       # остальные ошибки пробрасываем
        try:
            status = win32service.QueryServiceStatus(svc)[1]
            return status == SERVICE_RUNNING
        finally:
            win32service.CloseServiceHandle(svc)
    finally:
        win32service.CloseServiceHandle(scm)
        
from startup.check_cache import startup_cache
from log import log
import subprocess

def ensure_bfe_running(show_ui: bool = False) -> bool:
    """
    Проверяет и запускает службу BFE с кэшированием результата.
    """
    
    # Проверяем кэш сначала
    has_cache, cached_result = startup_cache.is_cached_and_valid("bfe_check")
    if has_cache:
        log(f"BFE проверка из кэша: {'OK' if cached_result else 'FAIL'}", "DEBUG")
        return cached_result
    
    log("Выполняется проверка службы Base Filtering Engine (BFE)", "INFO")
    
    try:
        # Проверяем состояние службы
        result = subprocess.run(
            ["sc", "query", "BFE"],
            capture_output=True,
            text=True,
            timeout=5,  # ← ДОБАВЛЯЕМ ТАЙМАУТ
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        
        if result.returncode != 0:
            startup_cache.cache_result("bfe_check", False)
            return False
        
        # Проверяем запущена ли служба
        if "RUNNING" not in result.stdout:
            log("Служба BFE остановлена, пытаемся запустить", "WARNING")
            
            start_result = subprocess.run(
                ["sc", "start", "BFE"],
                capture_output=True,
                text=True,
                timeout=10,  # ← ТАЙМАУТ ДЛЯ ЗАПУСКА
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            if start_result.returncode != 0 and "уже запущена" not in start_result.stderr:
                startup_cache.cache_result("bfe_check", False)
                return False
        
        startup_cache.cache_result("bfe_check", True)
        return True
        
    except subprocess.TimeoutExpired:
        log("Таймаут при проверке службы BFE", "ERROR")
        startup_cache.cache_result("bfe_check", False)
        return False
    except Exception as e:
        log(f"Ошибка при проверке службы BFE: {e}", "ERROR")
        startup_cache.cache_result("bfe_check", False)
        return False