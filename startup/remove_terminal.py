# remove_terminal.py

import os, subprocess, ctypes, sys
from pathlib import Path

# ---------------------------------------------------------------------------
# 1) Мини-хелперы
# ---------------------------------------------------------------------------

def _is_windows_11() -> bool:
    "Очень грубая проверка – номер сборки 22000+ ⇒ Windows 11."
    return sys.getwindowsversion().build >= 22000

def _wt_stub_exists() -> bool:
    """
    Быстрая проверка: у MS-Store-версии всегда присутствует stub
    %USERPROFILE%\\AppData\\Local\\Microsoft\\WindowsApps\\wt.exe.
    """
    stub = (
        Path(os.environ["USERPROFILE"])
        / "AppData" / "Local" / "Microsoft" / "WindowsApps" / "wt.exe"
    )
    return stub.exists()

# ---------------------------------------------------------------------------
# 2) Основная функция
# ---------------------------------------------------------------------------

def remove_windows_terminal_if_win11():
    """
    На Windows 11 удаляет MS-Store-версию Windows Terminal,
    но делает это ТОЛЬКО если:
    1. Терминал действительно установлен
    2. Пользователь включил эту опцию в настройках
    Если wt.exe-стаба нет или функция отключена – функция мгновенно возвращает управление.
    """
    from log import log   # импорт здесь, чтобы не тащить log в глобалы

    try:
        # 0. Проверяем настройку пользователя в реестре
        from config import get_remove_windows_terminal
        
        if not get_remove_windows_terminal():
            log("Удаление Windows Terminal отключено пользователем в настройках", level="INFO")
            return
        
        # 1. Требования к запуску
        if not _is_windows_11():
            return                  # не Win11 → ничего не делаем

        if not _wt_stub_exists():
            log("Windows Terminal не обнаружен – пропускаем удаление.")
            return                  # терминала нет → выходим

        log("Обнаружен Windows Terminal – выполняем удаление (согласно настройкам пользователя)…")

        # PowerShell-команды
        ps_remove_user = (
            'Get-AppxPackage -Name Microsoft.WindowsTerminal '
            '| Remove-AppxPackage -AllUsers'
        )
        ps_remove_prov = (
            'Get-AppxProvisionedPackage -Online '
            '| Where-Object {$_.PackageName -like "*WindowsTerminal*"} '
            '| Remove-AppxProvisionedPackage -Online'
        )

        for cmd in (ps_remove_user, ps_remove_prov):
            subprocess.run(
                ["powershell", "-NoLogo", "-NoProfile", "-Command", cmd],
                check=False,                       # ошибки не критичны
                creationflags=subprocess.CREATE_NO_WINDOW
            )

        log("Windows Terminal удалён (или уже отсутствовал).")

    except Exception as e:
        log(f"remove_windows_terminal_if_win11: {e}")