# autostart_remove.py
# ────────────────────────────────────────────────────────────────────────────
# «Пылесос» для всех видов автозапуска Zapret
#
#   • ярлыки в %APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
#   • ветка HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\Run
#   • задачи Планировщика  (ZapretStrategy / ZapretCensorliber)
#   • службы Windows       (ZapretCensorliber – старая; ZapretStrategyService – новая)
#
# Если появляется ещё одна служба/задача/ярлык — просто добавьте имя в
# соответствующий список/кортеж ниже, и чистильщик автоматически удалит её.
# ────────────────────────────────────────────────────────────────────────────

from __future__ import annotations
import os, subprocess, time, winreg
from pathlib import Path
from typing import Callable, Iterable

from log import log         # тот же логгер, что и в проекте


class AutoStartCleaner:
    """
    Полностью убирает все механизмы автозапуска, связанные с проектом Zapret.
    """

    # что именно ищем/удаляем — вынесено в «константы» для наглядности
    STARTUP_SHORTCUTS: tuple[str, ...] = ("ZapretGUI.lnk", "ZapretStrategy.lnk")
    SCHEDULER_TASKS:   tuple[str, ...] = ("ZapretStrategy", "ZapretCensorliber")
    SERVICE_NAMES:     tuple[str, ...] = ("ZapretCensorliber", "ZapretStrategyService")

    def __init__(
        self,
        *,
        service_names: Iterable[str] | None = None,
        status_cb: Callable[[str], None] | None = None,
    ):
        """
        Parameters
        ----------
        service_names : Iterable[str] | None
            Перечень имён служб, которые нужно удалить.
            Если None – берутся значения из SERVICE_NAMES класса.
        status_cb : Callable[[str], None] | None
            Колбэк для отображения статуса в GUI; можно None.
        """
        self.service_names = tuple(service_names) if service_names else self.SERVICE_NAMES
        self._status_cb = status_cb

    # ───────────────────────────────────────────────────────────── helpers ──
    def _status(self, msg: str):
        if self._status_cb:
            self._status_cb(msg)

    # ======================================================================
    # 1) ЯРЛЫКИ  %APPDATA%\...\Startup
    # ======================================================================
    def _remove_startup_shortcuts(self) -> bool:
        startup_dir = (Path(os.environ["APPDATA"]) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup")
        removed = False
        for lnk in self.STARTUP_SHORTCUTS:
            p = startup_dir / lnk
            if p.exists():
                try:
                    p.unlink()
                    log(f"Ярлык автозапуска удалён: {p}", "INFO")
                    removed = True
                except Exception as exc:
                    log(f"Не удалось удалить ярлык {p}: {exc}", "⚠ WARNING")
        return removed

    # ======================================================================
    # 2) Реестр  HKCU\...\Run
    # ======================================================================
    @staticmethod
    def _remove_autostart_registry() -> bool:
        key_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_WRITE) as key:
                try:
                    winreg.DeleteValue(key, "ZapretGUI")
                    log("Запись автозапуска в реестре удалена", "INFO")
                    return True
                except FileNotFoundError:
                    return False
        except Exception as exc:
            log(f"Ошибка удаления из реестра: {exc}", "❌ ERROR")
            return False

    # ======================================================================
    # 3) Планировщик задач
    # ======================================================================
    @classmethod
    def _remove_scheduler_tasks(cls) -> bool:
        removed_any = False
        for task in cls.SCHEDULER_TASKS:
            check = subprocess.run(
                ["C:\\Windows\\System32\\schtasks.exe", "/Query", "/TN", task],
                capture_output=True,
                text=True,
                encoding="cp866",
                errors="ignore",
            )
            if check.returncode == 0:
                log(f"Найдена задача {task}, удаляем…", "INFO")
                subprocess.run(
                    ["C:\\Windows\\System32\\schtasks.exe", "/Delete", "/TN", task, "/F"],
                    capture_output=True,
                    text=True,
                )
                removed_any = True
        return removed_any

    # ======================================================================
    # 4) Службы Windows
    # ======================================================================
    def _remove_service(self, svc_name: str) -> bool:
        """
        Удаляет конкретную службу.
        Return True, если служба была удалена (или попробовали удалить)  
        False – служба не найдена.
        """
        query = subprocess.run(
            ["sc", "query", svc_name],
            capture_output=True,
            text=True,
            encoding="cp866",     # sc выводит CP866 в русской локали
            errors="ignore",
        )
        if query.returncode != 0:
            return False     # службы нет – нечего удалять

        self._status(f"Остановка службы «{svc_name}»…")
        log(f"Останавливаем службу {svc_name}", "INFO")
        subprocess.run(["C:\\Windows\\System32\\sc.exe", "stop", svc_name], capture_output=True)

        time.sleep(1)  # даём службе погаснуть

        self._status(f"Удаление службы «{svc_name}»…")
        log(f"Удаляем службу {svc_name}", "INFO")
        delete = subprocess.run(
            ["C:\\Windows\\System32\\sc.exe", "delete", svc_name],
            capture_output=True,
            text=True,
            encoding="cp866",
            errors="ignore",
        )
        if delete.returncode == 0:
            log(f"Служба {svc_name} успешно удалена", "INFO")
            return True
        else:
            err = delete.stderr.strip() or delete.stdout.strip()
            log(f"Ошибка удаления службы {svc_name}: {err}", "❌ ERROR")
            return True    # Служба была, попытались удалить ⇒ считаем «что-то удалили»

    # ======================================================================
    # 5) ПУБЛИЧНЫЙ МЕТОД
    # ======================================================================
    def run(self) -> bool:
        """
        Запускает полное «подметание».

        Returns
        -------
        bool
            True  – удалось удалить хотя бы один механизм автозапуска;  
            False – ничего не найдено.
        """
        log("Удаление всех механизмов автозапуска…", "INFO")

        shortcuts = self._remove_startup_shortcuts()
        tasks     = self._remove_scheduler_tasks()
        registry  = self._remove_autostart_registry()

        services_removed_any = False
        for svc in self.service_names:
            if self._remove_service(svc):
                services_removed_any = True

        removed_any = any((shortcuts, tasks, services_removed_any, registry))
        if removed_any:
            log("Механизмы автозапуска удалены", "INFO")
        else:
            log("Механизмы автозапуска не найдены", "INFO")

        return removed_any