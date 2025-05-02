# autostart_exe.py

import os, sys, winreg
from pathlib import Path
from log import log
from reg import reg

def _startup_shortcut_path() -> Path:
    return (Path(os.environ["APPDATA"]) /
            "Microsoft/Windows/Start Menu/Programs/Startup/ZapretGUI.lnk")


def setup_autostart_for_exe(selected_mode: str | None = None,
                            status_cb=None) -> bool:
    def _status(msg): (status_cb or (lambda *_: None))(msg)
    
    try:
        # 1. импортируем pywin32
        try:
            from win32com.client import dynamic, gencache, pywintypes
        except ImportError:
            log("pywin32 не установлен", "ERROR")
            _status("pywin32 не установлен")
            return False

        # 2. готовим ярлык
        sc_path = _startup_shortcut_path()
        sc_path.parent.mkdir(parents=True, exist_ok=True)

        gencache.is_readonly = True            # <-- главное изменение
        try:
            shell = dynamic.Dispatch("WScript.Shell")
        except pywintypes.com_error as ce:
            log(f"COM-ошибка WScript.Shell: {ce}", "ERROR")
            _status("Не удалось создать ярлык (COM error)")
            return False

        sc = shell.CreateShortcut(str(sc_path))
        sc.Targetpath       = sys.executable
        sc.Arguments        = "--tray"
        sc.WorkingDirectory = str(Path(sys.executable).parent)
        sc.WindowStyle      = 7
        sc.IconLocation     = sys.executable
        sc.Save()

        # 3. при необходимости – записываем стратегию
        if selected_mode:
            ok = reg(r"Software\Zapret", "LastStrategy", selected_mode)
            if not ok:
                log("Не удалось записать LastStrategy в реестр", "WARNING")

        log(f"Автозапуск настроен: {sc_path}", "INFO")
        _status("Автозапуск успешно настроен")
        return True

    except Exception as exc:
        log(f"setup_autostart_for_exe: {exc}", "ERROR")
        _status(f"Ошибка: {exc}")
        return False