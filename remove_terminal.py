import subprocess
import ctypes

def remove_windows_terminal_if_win11():

    from log import log
    """
    На Windows 11 удаляет Windows Terminal (Store-версию) двумя способами:
    1) `Remove-AppxPackage` – удаляет у текущего пользователя
    2) `Remove-AppxProvisionedPackage` – убирает «заготовку» для новых учёток

    Требуются права администратора.  
    При любой ошибке пишет в лог, но не прерывает запуск программы.
    """
    try:
        # 2. Проверяем права администратора
        if not ctypes.windll.shell32.IsUserAnAdmin():
            log("remove_windows_terminal: нет прав администратора – пропуск")
            return

        log("Удаляем Windows Terminal…")

        # 3. Команды PowerShell
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
                check=False,  # ошибки не критичны
                creationflags=subprocess.CREATE_NO_WINDOW
            )

        log("Windows Terminal удалён (или не был установлен).")

    except Exception as e:
        log(f"remove_windows_terminal: {e}")