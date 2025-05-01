# autostart_strategy.py

from pathlib import Path
import json, sys, os, subprocess
from log import log


def _resolve_bin_folder(bin_folder: str) -> Path:
    """Возвращает абсолютный путь к bin, учитывая PyInstaller one-file."""
    p = Path(bin_folder)
    if p.is_absolute():
        return p

    # 1) <cwd>\bin
    cwd_variant = (Path.cwd() / p).resolve()
    if cwd_variant.exists():
        return cwd_variant

    # 2) рядом с exe / _MEIPASS
    base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    exe_variant = (base / p).resolve()
    if exe_variant.exists():
        return exe_variant

    return p.resolve()


def _get_startup_shortcut_path(filename: str = "ZapretStrategy.lnk") -> Path:
    """Возвращает %APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\<filename>"""
    startup_dir = (
        Path(os.environ["APPDATA"])
        / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
    )
    startup_dir.mkdir(parents=True, exist_ok=True)
    return startup_dir / filename


def setup_autostart_for_strategy(
    selected_mode: str,
    bin_folder: str,
    index_path: str | None = None,
) -> bool:
    """
    Создаёт ярлык в папке «Автозагрузка» на BAT-файл выбранной стратегии.

    Args:
        selected_mode: отображаемое имя стратегии (поле "name" в index.json)
        bin_folder:    каталог с *.bat* и index.json
        index_path:    путь к index.json (по­умолчанию <bin_folder>/index.json)

    Returns:
        True  – ярлык создан;
        False – возникла ошибка (подробности в log()).
    """
    try:
        # ----------- ищем BAT ------------------------------------------------
        bin_dir = _resolve_bin_folder(bin_folder)

        idx_path = Path(index_path) if index_path else bin_dir / "index.json"
        if not idx_path.is_file():
            log(f"index.json не найден: {idx_path}", "ERROR")
            return False

        with idx_path.open(encoding="utf-8") as f:
            data: dict = json.load(f)

        entry_key, entry_val = next(
            ((k, v) for k, v in data.items()
             if isinstance(v, dict) and v.get("name") == selected_mode),
            (None, None)
        )
        if not entry_key:
            log(f"Стратегия «{selected_mode}» не найдена", "ERROR")
            return False

        # берём file_path, если указан
        if isinstance(entry_val, dict) and entry_val.get("file_path"):
            bat_name = entry_val["file_path"]
        else:
            bat_name = entry_key if entry_key.lower().endswith(".bat") \
                                 else f"{entry_key}.bat"

        bat_path = (bin_dir / bat_name).resolve()
        if not bat_path.is_file():
            log(f".bat отсутствует: {bat_path}", "ERROR")
            return False

        # ----------- создаём ярлык ------------------------------------------
        try:
            from win32com.client import dynamic  # lazy-import
        except ImportError as e:
            log("pywin32 (win32com) не установлен – ярлык не создать", "ERROR")
            return False

        shortcut_path = _get_startup_shortcut_path()

        # удаляем старый ярлык, если был
        if shortcut_path.exists():
            try:
                shortcut_path.unlink()
            except Exception:
                pass

        shell = dynamic.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortcut(str(shortcut_path))
        shortcut.Targetpath      = str(bat_path)
        shortcut.WorkingDirectory= str(bat_path.parent)
        shortcut.WindowStyle     = 7          # Minimized
        shortcut.IconLocation    = str(bat_path)
        shortcut.Save()                       # важно: с заглавной S

        log(f"Ярлык автозапуска создан: {shortcut_path}", "INFO")
        return True

    except Exception as exc:
        log(f"setup_autostart_for_strategy: {exc}", "ERROR")
        return False