# autostart_strategy.py

from pathlib import Path
import json, sys, subprocess, traceback
from log import log
from typing import Callable, Optional
from utils import run_hidden # обёртка для subprocess.run


def _resolve_bat_folder(bat_folder: str) -> Path:
    """Возвращает абсолютный путь к bat, учитывая PyInstaller one-file."""
    p = Path(bat_folder)
    if p.is_absolute():
        return p

    # 1) <cwd>\bat
    cwd_variant = (Path.cwd() / p).resolve()
    if cwd_variant.exists():
        return cwd_variant

    # 2) рядом с exe / _MEIPASS
    base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    exe_variant = (base / p).resolve()
    if exe_variant.exists():
        return exe_variant

    return p.resolve()

def setup_autostart_for_strategy(
    selected_mode: str,
    bat_folder: str,
    index_path: str | None = None,
    ui_error_cb: Optional[Callable[[str], None]] = None,
) -> bool:
    """
    Создаёт задачу в планировщике на BAT-файл выбранной стратегии.

    Args:
        selected_mode: отображаемое имя стратегии (поле "name" в index.json)
        bat_folder:    каталог с *.bat* и index.json
        index_path:    путь к index.json

    Returns:
        True  – ярлык создан;
        False – возникла ошибка (подробности в log()).
    """
    try:
        # ----------- ищем BAT ------------------------------------------------
        bat_dir = _resolve_bat_folder(bat_folder)

        idx_path = Path(index_path) if index_path else bat_dir / "index.json"
        if not idx_path.is_file():
            log(f"index.json не найден: {idx_path}", "❌ ERROR")
            return False

        with idx_path.open(encoding="utf-8-sig") as f:
            data: dict = json.load(f)

        entry_key, entry_val = next(
            ((k, v) for k, v in data.items()
             if isinstance(v, dict) and v.get("name") == selected_mode),
            (None, None)
        )
        if not entry_key:
            log(f"Стратегия «{selected_mode}» не найдена", "❌ ERROR")
            return False

        # берём file_path, если указан
        if isinstance(entry_val, dict) and entry_val.get("file_path"):
            bat_name = entry_val["file_path"]
        else:
            bat_name = entry_key if entry_key.lower().endswith(".bat") \
                                 else f"{entry_key}.bat"

        bat_path = (bat_dir / bat_name).resolve()
        if not bat_path.is_file():
            log(f".bat отсутствует: {bat_path}", "❌ ERROR")
            return False

        # ----------- создаём/обновляем задачу Планировщика -------------------
        ok = _create_task_scheduler_job(
                task_name="ZapretStrategy",
                bat_path = bat_path,
                ui_error_cb = ui_error_cb
        )
        return ok

    except Exception as exc:
        log(f"setup_autostart_for_strategy: {exc}", "❌ ERROR")
        return False

def _create_task_scheduler_job(
    task_name: str,
    bat_path:  Path,
    ui_error_cb: Optional[Callable[[str], None]] = None,
) -> bool:
    """
    Создаёт (или перезаписывает) задачу в Планировщике Windows.

    Args:
        task_name : Имя задачи (напр. "ZapretStrategy")
        bat_path  : Полный путь к .bat
        ui_error_cb : callback для вывода ошибки в GUI (QMessageBox/label)

    Returns:
        True  – задача успешно создана/обновлена
        False – ошибка (уже залогирована, ui_error_cb вызван)
    """
    cmd = [
        "schtasks", "/Create",
        "/TN", task_name,
        "/TR", f'"{bat_path}"',
        "/SC", "ONLOGON",        # Изменено: при входе в систему вместо при запуске
        "/RU", "SYSTEM",
        "/RL", "HIGHEST",        # Запуск с повышенными правами
        "/IT",                   # Интерактивное выполнение (важно для ONLOGON)
        "/F"                     # перезаписать, если задача уже существует
    ]

    try:
        res = run_hidden(
            cmd,
            capture_output=True,
            text=True,
            encoding="cp866",  # Используем cp866 для совместимости с русским языком
        )
        if res.returncode == 0:
            log(f'Задача "{task_name}" создана/обновлена', "INFO")
            return True

        # Ошибка — готовим информативное сообщение
        err_msg = (f'Не удалось создать задачу автозапуска "{task_name}". '
                   f'Код {res.returncode}.\n{res.stderr.strip()}')
        log(err_msg, "❌ ERROR")
        if ui_error_cb:
            ui_error_cb(err_msg)
        return False

    except FileNotFoundError:
        # schtasks отсутствует (теоретически возможно в WinPE)
        err_msg = "Команда schtasks не найдена – автозапуск невозможен"
        log(err_msg, "❌ ERROR")
        if ui_error_cb:
            ui_error_cb(err_msg)
        return False
    except UnicodeDecodeError:
        try:
            res = run_hidden(
                cmd,
                capture_output=True,
                text=True,
                encoding="cp866",
                errors="ignore"
            )
            if res.returncode == 0:
                log(f'Задача "{task_name}" создана/обновлена (триггер: при входе в систему)', "INFO")
                return True
            else:
                err_msg = (f'Не удалось создать задачу автозапуска "{task_name}". '
                          f'Код {res.returncode}.\n{res.stderr.strip()}')
                log(err_msg, "❌ ERROR")
                if ui_error_cb:
                    ui_error_cb(err_msg)
                return False
        except Exception as fallback_exc:
            err_msg = f"Ошибка кодировки при создании задачи: {fallback_exc}"
            log(err_msg, "❌ ERROR")
            if ui_error_cb:
                ui_error_cb("Ошибка кодировки; подробности в логе.")
            return False
    except Exception as exc:
        err_msg = f"_create_task_scheduler_job: {exc}\n{traceback.format_exc()}"
        log(err_msg, "❌ ERROR")
        if ui_error_cb:
            ui_error_cb("Ошибка создания задачи автозапуска; подробности в логе.")
        return False