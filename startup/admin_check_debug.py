# admin_check_debug.py
import os, ctypes
from ctypes import wintypes
from log import log

def debug_admin_status():
    """Детальная диагностика прав администратора"""
    log("=== ДИАГНОСТИКА ПРАВ АДМИНИСТРАТОРА ===", level="🔍 DIAG")
    
    # 1. Старый метод
    try:
        is_admin_old = ctypes.windll.shell32.IsUserAnAdmin()
        log(f"IsUserAnAdmin(): {bool(is_admin_old)}", level="🔍 DIAG")
    except Exception as e:
        log(f"IsUserAnAdmin() failed: {e}", level="⚠ WARNING")
    
    # 2. Проверка SID
    try:
        import win32security
        admin_sid = win32security.WinBuiltinAdministratorsSid
        is_admin_sid = win32security.CheckTokenMembership(None, admin_sid)
        log(f"CheckTokenMembership(Administrators): {is_admin_sid}", level="🔍 DIAG")
    except ImportError:
        log("win32security не установлен, пропускаем SID проверку", level="⚠ WARNING")
    except Exception as e:
        log(f"SID check failed: {e}", level="⚠ WARNING")
    
    # 3. Токены
    advapi = ctypes.windll.advapi32
    kernel = ctypes.windll.kernel32
    
    TOKEN_QUERY = 0x0008
    TokenElevationType = 18
    TokenElevation = 20
    
    hTok = wintypes.HANDLE()
    if advapi.OpenProcessToken(kernel.GetCurrentProcess(), TOKEN_QUERY, ctypes.byref(hTok)):
        try:
            # Elevation Type
            etype = wintypes.DWORD()
            sz = wintypes.DWORD(ctypes.sizeof(etype))
            if advapi.GetTokenInformation(hTok, TokenElevationType, ctypes.byref(etype), sz, ctypes.byref(sz)):
                types = {1: "TokenElevationTypeDefault", 2: "TokenElevationTypeFull", 3: "TokenElevationTypeLimited"}
                log(f"TokenElevationType: {etype.value} ({types.get(etype.value, 'Unknown')})", level="🔍 DIAG")
            else:
                log("Не удалось получить TokenElevationType", level="⚠ WARNING")
            
            # Elevation Status
            elev = wintypes.DWORD()
            sz = wintypes.DWORD(ctypes.sizeof(elev))
            if advapi.GetTokenInformation(hTok, TokenElevation, ctypes.byref(elev), sz, ctypes.byref(sz)):
                log(f"TokenElevation: {bool(elev.value)}", level="🔍 DIAG")
            else:
                log("Не удалось получить TokenElevation", level="⚠ WARNING")
                
        finally:
            kernel.CloseHandle(hTok)
    else:
        log("Не удалось открыть токен процесса", level="❌ ERROR")
    
    # 4. Реальный тест
    log("=== РЕАЛЬНЫЙ ТЕСТ ПРАВ ===", level="🔍 DIAG")
    test_file = "C:\\Windows\\System32\\admin_test.tmp"
    try:
        with open(test_file, 'w') as f:
            f.write("test")
        os.remove(test_file)
        log("✅ Могу писать в System32 - ЕСТЬ права админа", level="✅ SUCCESS")
    except Exception as e:
        log(f"❌ НЕ могу писать в System32 - НЕТ прав админа ({e})", level="❌ ERROR")
    
    # 5. Проверка UAC
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 
                           r"SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System")
        uac_enabled, _ = winreg.QueryValueEx(key, "EnableLUA")
        consent_prompt, _ = winreg.QueryValueEx(key, "ConsentPromptBehaviorAdmin")
        log(f"UAC включен: {bool(uac_enabled)}", level="🔍 DIAG")
        log(f"ConsentPromptBehaviorAdmin: {consent_prompt}", level="🔍 DIAG")
        winreg.CloseKey(key)
    except Exception as e:
        log(f"Не могу проверить UAC: {e}", level="⚠ WARNING")
    
    # 6. Дополнительные проверки
    log("=== ДОПОЛНИТЕЛЬНАЯ ИНФОРМАЦИЯ ===", level="🔍 DIAG")
    
    # Проверка пользователя
    try:
        import getpass
        log(f"Текущий пользователь: {getpass.getuser()}", level="🔍 DIAG")
    except Exception as e:
        log(f"Не могу получить имя пользователя: {e}", level="⚠ WARNING")
    
    # Проверка переменных окружения
    log(f"USERNAME: {os.environ.get('USERNAME', 'не определено')}", level="🔍 DIAG")
    log(f"USERDOMAIN: {os.environ.get('USERDOMAIN', 'не определено')}", level="🔍 DIAG")
    
    # Итоговый вывод
    log("=== КОНЕЦ ДИАГНОСТИКИ ===", level="🔍 DIAG")