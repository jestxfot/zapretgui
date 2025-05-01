# admin_check.py

import os, sys, ctypes
from ctypes import wintypes

def is_admin() -> bool:
    """
    True  – процесс уже запущен с повышенными правами,
    False – обычный пользовательский токен.
    Работает одинаково на Vista-11 (UAC) и на XP.
    """
    if os.name != "nt":
        # для *nix достаточно uid==0
        return os.geteuid() == 0   # type: ignore[attr-defined]

    # На XP ещё нет разделения токенов, старый способ работает
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except AttributeError:
        return False

    # --- Vista+ -----------------------------------------------------
    #   проверяем тип токена: Limited / Split / Full
    advapi  = ctypes.windll.advapi32
    kernel  = ctypes.windll.kernel32

    TOKEN_QUERY         = 0x0008
    TokenElevationType  = 18        # TOKEN_INFORMATION_CLASS
    TokenElevation      = 20        # BOOL: 0/1

    # открываем токен текущего процесса
    hTok = wintypes.HANDLE()
    if not advapi.OpenProcessToken(kernel.GetCurrentProcess(),
                                   TOKEN_QUERY, ctypes.byref(hTok)):
        return False   # не смогли открыть – считаем, что не админ

    try:
        etype = wintypes.DWORD()
        sz    = wintypes.DWORD(ctypes.sizeof(etype))
        if advapi.GetTokenInformation(hTok, TokenElevationType,
                                      ctypes.byref(etype), sz,
                                      ctypes.byref(sz)):
            # 1 = Limited, 2 = Full (elevated), 3 = Limited-to-Full (UIAccess)
            return etype.value == 2

        # fallback ‑ XP/старые системы: TokenElevation (0/1)
        elev  = wintypes.DWORD()
        if advapi.GetTokenInformation(hTok, TokenElevation,
                                      ctypes.byref(elev), sz,
                                      ctypes.byref(sz)):
            return bool(elev.value)

        return False
    finally:
        kernel.CloseHandle(hTok)