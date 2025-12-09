"""
Утилита для остановки процессов через Windows API.
Быстрее и надёжнее чем taskkill.exe
"""

import ctypes
from ctypes import wintypes
import psutil
from log import log
from typing import List, Optional

# Windows API константы
PROCESS_TERMINATE = 0x0001
PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
SYNCHRONIZE = 0x00100000

# Загрузка Windows API функций
kernel32 = ctypes.windll.kernel32

OpenProcess = kernel32.OpenProcess
OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
OpenProcess.restype = wintypes.HANDLE

TerminateProcess = kernel32.TerminateProcess
TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
TerminateProcess.restype = wintypes.BOOL

CloseHandle = kernel32.CloseHandle
CloseHandle.argtypes = [wintypes.HANDLE]
CloseHandle.restype = wintypes.BOOL


def kill_process_by_pid(pid: int, force: bool = True) -> bool:
    """
    Завершает процесс по PID через Windows API с fallback на psutil.
    
    Args:
        pid: ID процесса
        force: True для принудительного завершения
        
    Returns:
        True если процесс успешно завершён
    """
    # Сначала пробуем через Win API с расширенными правами
    try:
        # Открываем процесс с максимальными правами
        h_process = OpenProcess(
            PROCESS_TERMINATE | PROCESS_QUERY_INFORMATION | SYNCHRONIZE,
            False,
            pid
        )
        
        if h_process:
            try:
                # Завершаем процесс (код выхода = 1)
                exit_code = 1
                result = TerminateProcess(h_process, exit_code)
                
                if result:
                    log(f"✅ Процесс PID={pid} завершён через Win API", "DEBUG")
                    return True
                    
            finally:
                # Всегда закрываем handle
                CloseHandle(h_process)
                
    except Exception as e:
        log(f"Win API не сработал для PID={pid}: {e}", "DEBUG")
    
    # Fallback на psutil (работает с любыми привилегиями)
    try:
        proc = psutil.Process(pid)
        proc_name = proc.name()
        
        if force:
            proc.kill()  # SIGKILL
            log(f"✅ Процесс {proc_name} (PID={pid}) завершён через psutil.kill()", "DEBUG")
        else:
            proc.terminate()  # SIGTERM
            log(f"✅ Процесс {proc_name} (PID={pid}) завершён через psutil.terminate()", "DEBUG")
        
        return True
        
    except psutil.NoSuchProcess:
        log(f"Процесс PID={pid} уже завершён", "DEBUG")
        return True
    except psutil.AccessDenied:
        log(f"❌ Нет прав для завершения процесса PID={pid} (требуются права администратора)", "WARNING")
        return False
    except Exception as e:
        log(f"❌ Ошибка завершения процесса PID={pid}: {e}", "WARNING")
        return False


def kill_process_by_name(process_name: str, kill_all: bool = True) -> int:
    """
    Завершает все процессы с указанным именем через Windows API.
    
    Args:
        process_name: Имя процесса (например "winws.exe")
        kill_all: True для завершения всех найденных процессов
        
    Returns:
        Количество завершённых процессов
    """
    killed_count = 0
    process_name_lower = process_name.lower()
    
    try:
        # Ищем все процессы с указанным именем через psutil
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                proc_name = proc.info['name']
                if proc_name and proc_name.lower() == process_name_lower:
                    pid = proc.info['pid']
                    
                    if kill_process_by_pid(pid):
                        killed_count += 1
                        
                        if not kill_all:
                            break
                            
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
                
    except Exception as e:
        log(f"Ошибка поиска процесса {process_name}: {e}", "WARNING")
    
    if killed_count > 0:
        log(f"Завершено {killed_count} процессов {process_name}", "INFO")
    else:
        log(f"Процессы {process_name} не найдены или уже завершены", "DEBUG")
    
    return killed_count


def kill_winws_all() -> bool:
    """
    Завершает все процессы winws.exe и winws2.exe.
    
    Returns:
        True если хотя бы один процесс был завершён
    """
    total_killed = 0
    
    # Завершаем winws.exe
    total_killed += kill_process_by_name("winws.exe", kill_all=True)
    
    # Завершаем winws2.exe
    total_killed += kill_process_by_name("winws2.exe", kill_all=True)
    
    if total_killed > 0:
        log(f"✅ Всего завершено {total_killed} процессов winws", "INFO")
        return True
    else:
        log("Процессы winws не найдены", "DEBUG")
        return False


def is_process_running(process_name: str) -> bool:
    """
    Быстрая проверка запущен ли процесс.
    
    Args:
        process_name: Имя процесса (например "winws.exe")
        
    Returns:
        True если процесс найден
    """
    process_name_lower = process_name.lower()
    
    try:
        for proc in psutil.process_iter(['name']):
            try:
                proc_name = proc.info['name']
                if proc_name and proc_name.lower() == process_name_lower:
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
    except Exception as e:
        log(f"Ошибка проверки процесса {process_name}: {e}", "DEBUG")
    
    return False


def get_process_pids(process_name: str) -> List[int]:
    """
    Возвращает список PID всех процессов с указанным именем.
    
    Args:
        process_name: Имя процесса
        
    Returns:
        Список PID процессов
    """
    pids = []
    process_name_lower = process_name.lower()
    
    try:
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                proc_name = proc.info['name']
                if proc_name and proc_name.lower() == process_name_lower:
                    pids.append(proc.info['pid'])
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
    except Exception as e:
        log(f"Ошибка получения PID {process_name}: {e}", "DEBUG")
    
    return pids


def kill_process_tree(pid: int) -> bool:
    """
    Завершает процесс и все его дочерние процессы.
    
    Args:
        pid: ID родительского процесса
        
    Returns:
        True если процесс завершён
    """
    try:
        parent = psutil.Process(pid)
        
        # Сначала завершаем дочерние процессы
        children = parent.children(recursive=True)
        for child in children:
            try:
                kill_process_by_pid(child.pid)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        # Затем завершаем родительский процесс
        return kill_process_by_pid(pid)
        
    except psutil.NoSuchProcess:
        log(f"Процесс PID={pid} уже завершён", "DEBUG")
        return False
    except Exception as e:
        log(f"Ошибка завершения дерева процессов PID={pid}: {e}", "WARNING")
        return False

