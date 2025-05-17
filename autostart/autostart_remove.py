# autostart_remove.py

"""
Удаление ВСЕХ способов автозапуска Zapret:
  ярлыки в Startup
  CurrentVersion\\Run
  задачи планировщика (ZapretStrategy / ZapretCensorliber)
  старая служба ZapretCensorliber
"""

import os
import subprocess
import time
import winreg
from pathlib import Path

# логгер ожидается такой же, как в проекте
from log import log


class AutoStartCleaner:
    def __init__(self,
                 service_name: str = "ZapretCensorliber",
                 status_cb=None):
        """
        Args:
            service_name : имя устаревшей службы, которую нужно снести
            status_cb    : функция status_cb(str) → None  (можно None)
        """
        self.service_name = service_name
        self._status_cb = status_cb

    # ---------- helpers --------------------------------------------------
    def _status(self, msg: str):
        if self._status_cb:
            self._status_cb(msg)

    # =====================================================================
    # 1) ЯРЛЫКИ
    # =====================================================================
    def _remove_startup_shortcuts(self) -> bool:
        startup_dir = (
            Path(os.environ["APPDATA"]) /
            "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
        )
        removed = False
        for lnk in ("ZapretGUI.lnk", "ZapretStrategy.lnk"):
            p = startup_dir / lnk
            if p.exists():
                try:
                    p.unlink()
                    log(f"Ярлык автозапуска удалён: {p}", "INFO")
                    removed = True
                except Exception as e:
                    log(f"Не удалось удалить ярлык {p}: {e}", "WARNING")
        return removed

    # =====================================================================
    # 2) CurrentVersion\Run
    # =====================================================================
    @staticmethod
    def _remove_autostart_registry() -> bool:
        try:
            key_path = "SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                key_path, 0, winreg.KEY_WRITE) as key:
                try:
                    winreg.DeleteValue(key, "ZapretGUI")
                    log("Запись автозапуска в реестре удалена", "INFO")
                    return True
                except FileNotFoundError:
                    return False
        except Exception as e:
            log(f"Ошибка удаления из реестра: {e}", "ERROR")
            return False

    # =====================================================================
    # 3) Планировщик задач
    # =====================================================================
    @staticmethod
    def _remove_scheduler_tasks() -> bool:
        removed_any = False
        for task in ("ZapretStrategy", "ZapretCensorliber"):
            check = subprocess.run(f'schtasks /Query /TN "{task}" 2>nul',
                                   shell=True, capture_output=True)
            if check.returncode == 0:
                log(f"Найдена задача {task}, удаляем…", "INFO")
                subprocess.run(f'schtasks /Delete /TN "{task}" /F',
                               shell=True, check=False)
                removed_any = True
        return removed_any or False

    # =====================================================================
    # 4) Служба Windows
    # =====================================================================
    def _remove_legacy_service(self) -> bool:
        svc = self.service_name
        query = subprocess.run(f'sc query "{svc}"',
                               shell=True,
                               capture_output=True,
                               text=True, encoding="cp866")
        if query.returncode != 0:
            return False     # службы нет – нечего удалять

        self._status("Остановка устаревшей службы…")
        log(f"Останавливаем службу {svc}", "INFO")
        subprocess.run(f'sc stop "{svc}"', shell=True, capture_output=True)
        time.sleep(1)

        self._status("Удаление устаревшей службы…")
        log(f"Удаляем службу {svc}", "INFO")
        delete = subprocess.run(f'sc delete "{svc}"',
                                shell=True,
                                capture_output=True,
                                text=True, encoding="cp866")
        ok = delete.returncode == 0
        if ok:
            log("Служба успешно удалена", "INFO")
        else:
            err = delete.stderr.strip() or delete.stdout.strip()
            log(f"Ошибка удаления службы: {err}", "ERROR")
        return ok

    # =====================================================================
    # 5) ПУБЛИЧНЫЙ МЕТОД
    # =====================================================================
    def run(self) -> bool:
        """
        Запускает полное «подметание».
        Возвращает True, если удалось удалить ХОТЯ БЫ один механизм.
        """
        log("Удаление всех механизмов автозапуска…", "INFO")
        shortcuts = self._remove_startup_shortcuts()
        tasks     = self._remove_scheduler_tasks()
        service   = self._remove_legacy_service()
        registry  = self._remove_autostart_registry()

        removed_any = any((shortcuts, tasks, service, registry))
        if removed_any:
            log("Механизмы автозапуска удалены", "INFO")
        else:
            log("Механизмы автозапуска не найдены", "INFO")

        return removed_any