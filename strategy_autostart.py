# strategy_autostart.py
from pathlib import Path
import json, subprocess
from log import log


def setup_autostart_for_strategy(selected_mode: str,
                                 bin_folder: str,
                                 index_path: str | None = None) -> bool:
    """
    Ищет .bat по selected_mode в index.json и запускает его.

    Args:
        selected_mode: имя стратегии в поле "name" index.json
        bin_folder:    папка с bat-файлами и index.json
        index_path:    явный путь к index.json (если None → <bin_folder>/index.json)
    """
    try:
        idx_path = Path(index_path) if index_path else Path(bin_folder) / "index.json"
        if not idx_path.is_file():
            log(f"index.json не найден: {idx_path}", "ERROR")
            return False

        with idx_path.open(encoding="utf-8") as f:
            data: dict = json.load(f)

        strategy_id = next(
            (k for k, v in data.items()
             if isinstance(v, dict) and v.get("name") == selected_mode),
            None
        )
        if not strategy_id:
            log(f"Стратегия «{selected_mode}» не найдена", "ERROR")
            return False

        bat = strategy_id if strategy_id.lower().endswith(".bat") else f"{strategy_id}.bat"
        bat_path = Path(bin_folder) / bat
        if not bat_path.is_file():
            log(f".bat отсутствует: {bat_path}", "ERROR")
            return False

        log(f"Запускаем {bat_path}", "INFO")
        subprocess.Popen(
            [str(bat_path)],
            shell=True,
            cwd=str(bat_path.parent),
            creationflags=subprocess.CREATE_NEW_CONSOLE
        )
        log(f"Стратегия «{selected_mode}» запущена", "INFO")
        return True

    except Exception as e:
        log(f"setup_autostart_for_strategy: {e}", "ERROR")
        return False