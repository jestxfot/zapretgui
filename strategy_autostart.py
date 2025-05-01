# strategy_autostart.py

from pathlib import Path
import json, subprocess, sys, os
from log import log

def _resolve_bin_folder(bin_folder: str) -> Path:
    """
    Преобразует bin_folder в абсолютный Path, учитывая:
      • относительный путь от cwd,
      • расположение exe при one-file-build (sys._MEIPASS).
    """
    p = Path(bin_folder)
    if p.is_absolute():
        return p

    # 1) cwd\bin
    cwd_variant = (Path.cwd() / p).resolve()
    if cwd_variant.exists():
        return cwd_variant

    # 2) рядом с exe / скриптом
    base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    exe_variant = (base / p).resolve()
    if exe_variant.exists():
        return exe_variant

    return p.resolve()


def setup_autostart_for_strategy(selected_mode: str,
                                 bin_folder: str,
                                 index_path: str | None = None) -> bool:
    """
    Ищет стратегию по selected_mode в index.json, берёт file_path (если указан)
    и запускает соответствующий .bat.
    """
    try:
        bin_dir = _resolve_bin_folder(bin_folder)
        if not bin_dir.exists():
            log(f"Каталог bin не найден: {bin_dir}", "ERROR")
            return False

        idx_path = Path(index_path) if index_path else bin_dir / "index.json"
        if not idx_path.is_file():
            log(f"index.json не найден: {idx_path}", "ERROR")
            return False

        with idx_path.open(encoding="utf-8") as f:
            data: dict = json.load(f)

        # ---- ищем запись с совпадающим name --------------------------------
        entry_key, entry_val = next(
            ((k, v) for k, v in data.items()
             if isinstance(v, dict) and v.get("name") == selected_mode),
            (None, None)
        )
        if not entry_key:
            log(f"Стратегия «{selected_mode}» не найдена", "ERROR")
            return False

        # ---- определяем имя .bat -------------------------------------------
        if isinstance(entry_val, dict) and entry_val.get("file_path"):
            bat_name = entry_val["file_path"]
        else:  # fallback – по ключу
            bat_name = entry_key if entry_key.lower().endswith(".bat") \
                                 else f"{entry_key}.bat"

        bat_path = (bin_dir / bat_name).resolve()
        if not bat_path.is_file():
            log(f".bat отсутствует: {bat_path}", "ERROR")
            return False

        # ---- запускаем ------------------------------------------------------
        log(f"Запускаем {bat_path}", "INFO")
        subprocess.Popen(
            [str(bat_path)],
            shell=True,
            cwd=str(bat_path.parent),
            creationflags=subprocess.CREATE_NEW_CONSOLE
        )
        log(f"Стратегия «{selected_mode}» запущена", "INFO")
        return True

    except Exception as exc:
        log(f"setup_autostart_for_strategy: {exc}", "ERROR")
        return False