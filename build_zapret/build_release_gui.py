# pyright: ignore

# build_zapret/build_release_gui.py

from __future__ import annotations

import os
import sys
import sysconfig
from pathlib import Path
import re

ROOT_HINT = Path(__file__).resolve().parents[1]
if str(ROOT_HINT) not in sys.path:
    sys.path.insert(0, str(ROOT_HINT))
# build_zapret/ contains local modules (ssh_deploy, keyboard_manager, etc.)
_BUILD_DIR = Path(__file__).resolve().parent
if str(_BUILD_DIR) not in sys.path:
    sys.path.insert(0, str(_BUILD_DIR))

try:
    from utils.dotenv import load_dotenv
except Exception:
    load_dotenv = None  # type: ignore[assignment]

if load_dotenv is not None:
    # Allow local configuration without hardcoding secrets/paths in repo.
    load_dotenv(ROOT_HINT / ".env", ROOT_HINT / "build_zapret" / ".env")

# Apply global proxy for builder if configured via ZAPRET_PROXY_*.
try:
    from utils.proxy_env import apply_zapret_proxy_env

    apply_zapret_proxy_env()
except Exception:
    pass


def _is_free_threaded_python() -> bool:
    """
    True если интерпретатор собран как free-threaded (PEP 703 / "t"-build).

    В таких сборках некоторые C-расширения/GUI-биндинги могут падать при запуске
    без GIL (как в отчёте пользователя). Поэтому для GUI сборщика безопаснее
    принудительно включать GIL через `-X gil=1`.
    """
    # 1) Самый надёжный признак, если доступен в sysconfig.
    try:
        if bool(sysconfig.get_config_var("Py_GIL_DISABLED")):
            return True
    except Exception:
        pass

    # 2) На Windows `sysconfig` может не отдавать переменную; тогда смотрим на имя exe.
    try:
        exe = Path(sys.executable).name.lower()
        if re.fullmatch(r"python(?:\d+(?:\.\d+)*)?t\.exe", exe):
            return True
        if exe.endswith("t.exe") and exe.startswith("python"):
            return True
    except Exception:
        pass

    # 3) В free-threaded сборках есть internal API для проверки GIL.
    return callable(getattr(sys, "_is_gil_enabled", None))


def _is_gil_enabled() -> bool:
    """
    Пытаемся определить, включён ли GIL в текущем процессе.
    Для обычных Python всегда True.
    """
    if not _is_free_threaded_python():
        return True

    is_gil_enabled = getattr(sys, "_is_gil_enabled", None)
    if callable(is_gil_enabled):
        try:
            return bool(is_gil_enabled())
        except Exception:
            pass

    # Фоллбек (на случай отсутствия API): доверяем явным настройкам запуска.
    if os.environ.get("PYTHON_GIL") in {"1", "true", "TRUE", "yes", "YES"}:
        return True
    if getattr(sys, "_xoptions", {}).get("gil") is not None:
        return True
    if os.environ.get("ZAPRETGUI_GIL_REEXEC_DONE") == "1":
        return True
    return False


def _maybe_reexec_with_gil_enabled() -> None:
    """
    Если запустили free-threaded Python без GIL, перезапускаем этот же скрипт с `-X gil=1`
    до импорта tkinter и других потенциально проблемных модулей.

    Отключить поведение можно, задав `ZAPRETGUI_SKIP_GIL_REEXEC=1`.
    """
    if os.environ.get("ZAPRETGUI_SKIP_GIL_REEXEC") == "1":
        return

    if sys.platform != "win32":
        return

    if not _is_free_threaded_python():
        return

    # Защита от бесконечного перезапуска.
    if os.environ.get("ZAPRETGUI_GIL_REEXEC_DONE") == "1":
        return

    if _is_gil_enabled():
        return

    os.environ["ZAPRETGUI_GIL_REEXEC_DONE"] = "1"
    os.environ.setdefault("PYTHON_GIL", "1")

    try:
        os.execv(sys.executable, [sys.executable, "-X", "gil=1", *sys.argv])
    except Exception:
        # Если re-exec невозможен — продолжаем как есть (лучше дать шанс,
        # чем падать здесь). Ошибка воспроизведётся и будет видна пользователю.
        return


_maybe_reexec_with_gil_enabled()

import ctypes
import json
import re
import shutil
import subprocess
import tempfile
import textwrap
import urllib.request
from datetime import date
from queue import Queue
from typing import Any, Optional, Sequence
import importlib.util

import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

from keyboard_manager import KeyboardManager


def ensure_inno_ico_dir(source_path: Path, project_root: Path, log_queue: Queue | None = None) -> None:
    """
    Inno Setup ожидает иконки в `{#SOURCEPATH}\\ico\\...` (см. *.iss).
    Гарантируем папку и копируем туда *.ico из корня проекта.
    """
    ico_dir = source_path / "ico"
    ico_dir.mkdir(parents=True, exist_ok=True)

    copied = 0
    for ico in project_root.glob("*.ico"):
        try:
            shutil.copy2(ico, ico_dir / ico.name)
            copied += 1
        except Exception:
            pass

    if log_queue is not None:
        log_queue.put(f"🖼️ Иконки: {ico_dir} (скопировано: {copied})")

# ════════════════════════════════════════════════════════════════
#  УНИВЕРСАЛЬНЫЙ ИМПОРТ МОДУЛЕЙ СБОРКИ
# ════════════════════════════════════════════════════════════════

# Импорт PyInstaller функций
try:
    from pyinstaller_builder import create_spec_file, run_pyinstaller, check_pyinstaller_available
    PYINSTALLER_AVAILABLE = True
except ImportError:
    PYINSTALLER_AVAILABLE = False
    def create_spec_file(channel: str, root_path: Path, log_queue: Optional[Any] = None) -> Path:
        raise ImportError("Модуль pyinstaller_builder недоступен")
    
    def run_pyinstaller(channel: str, root_path: Path, run_func: Any, log_queue: Any = None) -> None:
        raise ImportError("Модуль pyinstaller_builder недоступен")
    
    def check_pyinstaller_available() -> bool:
        return False

# Импорт Nuitka функций
try:
    from nuitka_builder import run_nuitka, check_nuitka_available, create_version_info
    NUITKA_AVAILABLE = True
except ImportError:
    NUITKA_AVAILABLE = False
    def run_nuitka(
        channel: str,
        version: str,
        root_path: Path,
        python_exe: str,
        run_func: Any,
        log_queue: Optional[Any] = None,
        *,
        target_dir: Optional[Path] = None,
    ) -> Path:
        raise ImportError("Модуль nuitka_builder недоступен")
    
    def check_nuitka_available() -> bool:
        return False
        
    def create_version_info(channel: str, version: str, root_path: Path) -> Path:
        raise ImportError("Модуль nuitka_builder недоступен")

# ════════════════════════════════════════════════════════════════
#  УНИВЕРСАЛЬНЫЙ ИМПОРТ GITHUB МОДУЛЯ
# ════════════════════════════════════════════════════════════════
def setup_github_imports():
    """Настройка импорта GitHub модуля"""
    try:
        # Способ 1: Добавляем родительскую папку в sys.path
        root_path = Path(__file__).parent.parent
        if str(root_path) not in sys.path:
            sys.path.insert(0, str(root_path))
    
        from build_zapret import (
            create_github_release, 
            is_github_enabled, 
            get_github_config_info,
            GITHUB_AVAILABLE
        )
        return create_github_release, is_github_enabled, get_github_config_info, GITHUB_AVAILABLE
    except ImportError:
        pass
    
    try:
        # Способ 2: Прямой импорт из текущей папки
        current_path = Path(__file__).parent
        if str(current_path) not in sys.path:
            sys.path.insert(0, str(current_path))
        
        import github_release
        return (
            github_release.create_github_release,
            github_release.is_github_enabled,
            github_release.get_github_config_info,
            True
        )
    except ImportError:
        pass
    
    # Способ 3: Заглушки если ничего не работает
    def create_github_release(*args, **kwargs) -> Optional[str]:
        return None
    
    def is_github_enabled() -> bool:
        return False
    
    def get_github_config_info() -> str:
        return "GitHub модуль недоступен"
    
    return create_github_release, is_github_enabled, get_github_config_info, False

# Настраиваем импорт
create_github_release, is_github_enabled, get_github_config_info, GITHUB_AVAILABLE = setup_github_imports()

# ════════════════════════════════════════════════════════════════
#  УНИВЕРСАЛЬНЫЙ ИМПОРТ SSH + TELEGRAM МОДУЛЯ
# ════════════════════════════════════════════════════════════════
def setup_ssh_imports():
    """Настройка импорта SSH модуля"""
    try:
        from ssh_deploy import deploy_to_all_servers, is_ssh_configured, get_ssh_config_info
        return deploy_to_all_servers, is_ssh_configured, get_ssh_config_info, True
    except ImportError:
        pass
    # Retry with explicit build_zapret package path
    try:
        from build_zapret.ssh_deploy import deploy_to_all_servers, is_ssh_configured, get_ssh_config_info
        return deploy_to_all_servers, is_ssh_configured, get_ssh_config_info, True
    except ImportError:
        # Заглушки
        def deploy_to_all_servers(*args, **kwargs) -> tuple[bool, str]:
            return False, "SSH модуль недоступен"
        def is_ssh_configured() -> bool:
            return False
        def get_ssh_config_info() -> str:
            return "SSH модуль недоступен (установите: pip install paramiko)"
        return deploy_to_all_servers, is_ssh_configured, get_ssh_config_info, False

# Настраиваем импорт
deploy_to_all_servers, is_ssh_configured, get_ssh_config_info, SSH_AVAILABLE = setup_ssh_imports()


def check_telegram_configured() -> tuple[bool, str]:
    """Проверяет наличие Telegram сессии (Pyrogram или Telethon)."""

    pyrogram_session = Path(__file__).parent / "zapret_uploader_pyrogram.session"
    telethon_session = Path(__file__).parent / "zapret_uploader.session"

    if pyrogram_session.exists():
        return True, "✅ Pyrogram сессия активна"
    if telethon_session.exists():
        return True, "✅ Telethon сессия активна"

    return False, "⚠️ Требуется авторизация (Pyrogram/Telethon)"

def _load_build_telegram_config() -> tuple[str, str]:
    """
    Возвращает (TELEGRAM_API_ID, TELEGRAM_API_HASH) из окружения/.env.
    """
    api_id = (os.getenv("TELEGRAM_API_ID") or os.getenv("ZAPRET_TELEGRAM_API_ID") or "").strip()
    api_hash = (os.getenv("TELEGRAM_API_HASH") or os.getenv("ZAPRET_TELEGRAM_API_HASH") or "").strip()
    if api_id and api_hash:
        return api_id, api_hash

    raise RuntimeError(
        "Telegram API ключи не найдены.\n"
        "Нужно задать TELEGRAM_API_ID и TELEGRAM_API_HASH через:\n"
        "- или переменные окружения.\n"
    )

def _env_truthy(name: str) -> bool:
    return os.environ.get(name, "").strip() in {"1", "true", "TRUE", "yes", "YES", "on", "ON"}

def _to_wsl_path(path: Path, distro: str = "Debian") -> str:
    """
    Конвертирует путь Windows/UNC в Linux-путь для запуска внутри WSL.

    Поддержка:
      - \\\\wsl.localhost\\<Distro>\\opt\\...  -> /opt/...
      - //wsl.localhost/<Distro>/opt/...       -> /opt/...
      - C:\\Users\\...                        -> /mnt/c/Users/...
    """
    s = str(path)

    if s.startswith("\\\\wsl.localhost\\"):
        parts = s.split("\\")
        if len(parts) >= 5 and parts[3].lower() == distro.lower():
            rest = [p for p in parts[4:] if p]
            return "/" + "/".join(rest)

    s_posix = path.as_posix()
    prefix = f"//wsl.localhost/{distro}/"
    if s_posix.lower().startswith(prefix.lower()):
        return "/" + s_posix[len(prefix):].lstrip("/")

    m = re.match(r"^([A-Za-z]):[\\\\/](.*)$", s)
    if m:
        drive = m.group(1).lower()
        rest = m.group(2).replace("\\", "/")
        return f"/mnt/{drive}/{rest}"

    if s.startswith("/"):
        return s
    return s

# Скрываем консоль Windows
if sys.platform == "win32":
    import ctypes
    kernel32 = ctypes.WinDLL('kernel32')
    user32 = ctypes.WinDLL('user32')
    
    # Получаем хэндл консольного окна
    hWnd = kernel32.GetConsoleWindow()
    if hWnd:
        # Скрываем окно
        user32.ShowWindow(hWnd, 0)

# ────────────────────────────────────────────────────────────────
#  КОНСТАНТЫ
# ────────────────────────────────────────────────────────────────
INNO_ISCC  = r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
PY         = sys.executable

# корневая папка
def find_project_root(start: Path) -> Path:
    for p in [start, *start.parents]:
        if (p / "main.py").exists() and (p / "config").is_dir():
            return p
    raise FileNotFoundError("main.py not found; поправьте find_project_root()")

ROOT = find_project_root(Path(__file__).resolve())

# ════════════════════════════════════════════════════════════════
#  ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ════════════════════════════════════════════════════════════════
def run(cmd: Sequence[str] | str, check: bool = True, cwd: Path | None = None, capture: bool = False):
    """Единая функция для запуска команд"""
    if isinstance(cmd, (list, tuple)):
        import shlex
        shown = " ".join(shlex.quote(str(c)) for c in cmd)
    else:
        shown = cmd
    
    log_queue = getattr(run, "log_queue", None)
    if log_queue is not None:
        log_queue.put(f"> {shown}")
    
    # Важно: добавляем CREATE_NO_WINDOW для скрытия консольных окон подпроцессов
    startupinfo = None
    if sys.platform == "win32":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
    
    process = subprocess.Popen(
        cmd, 
        shell=isinstance(cmd, str), 
        cwd=cwd,
        stdout=subprocess.PIPE, 
        stderr=subprocess.STDOUT, 
        text=True, 
        encoding='utf-8',
        errors='replace',
        startupinfo=startupinfo,
        bufsize=1
    )
    
    output_lines = []
    if process.stdout is not None:
        for line in iter(process.stdout.readline, ''):
            if not line:
                break
            stripped = line.rstrip('\n')
            if log_queue is not None and stripped:
                log_queue.put(stripped)
            output_lines.append(stripped)
            
    process.stdout.close()
    returncode = process.wait()
    full_output = '\n'.join(output_lines)
    
    # Проверяем код возврата
    if check and returncode != 0:
        error_msg = f"Command failed with code {returncode}"
        if full_output:
            error_msg += f"\n\nВывод:\n{full_output}"
            
        if log_queue is not None:
            log_queue.put(f"❌ {error_msg}")
            
        if capture:
            raise subprocess.CalledProcessError(returncode, cmd, full_output, "")
        else:
            raise RuntimeError(error_msg)
    
    if capture:
        return full_output
    else:
        return returncode

def is_admin() -> bool:
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def elevate_as_admin():
    """Перезапуск с правами администратора"""
    pythonw = PY.replace('python.exe', 'pythonw.exe')
    if not Path(pythonw).exists():
        pythonw = PY

    # Сохраняем CLI аргументы при перезапуске (важно для --fast-exe и прочего).
    args = [str(Path(__file__).resolve()), *sys.argv[1:]]
    params = subprocess.list2cmdline(args)

    ctypes.windll.shell32.ShellExecuteW(
        None, 
        "runas", 
        pythonw,
        params,
        str(ROOT), 
        1
    )
    sys.exit(0)

def parse_version(version_string: str) -> tuple[int, int, int, int]:
    """Парсит версию в кортеж из ровно 4 чисел"""
    try:
        version = (version_string or "").lstrip('v')
        parts = [int(x) for x in version.split('.') if x.strip().isdigit()]
        while len(parts) < 4:
            parts.append(0)
        return (parts[0], parts[1], parts[2], parts[3])
    except Exception:
        return (0, 0, 0, 0)

def normalize_to_4(ver: str) -> str:
    """Возвращает строку-версию строго из 4 чисел X.X.X.X"""
    return ".".join(map(str, parse_version(ver)))


def version_to_filename_suffix(ver: str) -> str:
    """Converts version string to a safe filename suffix (underscored).

    Example: 20.3.17.0 -> 20_3_17_0
    """
    v = normalize_to_4(ver)
    return v.replace(".", "_")

def suggest_next(ver: str) -> str:
    """Предлагает следующую 4-частную версию"""
    try:
        new_parts = list(parse_version(ver))
        new_parts[-1] += 1
        return ".".join(map(str, new_parts))
    except Exception:
        nums = [int(x) for x in (ver.split(".") + ["0"] * 4)[:4]]
        if nums:
            nums[-1] += 1
        return ".".join(map(str, nums))

def safe_json_write(path: Path, data: dict):
    """Атомарная запись JSON"""
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)

def fetch_local_versions() -> dict[str, str]:
    """Получает текущие версии из локального JSON файла"""
    try:
        versions_file = Path(__file__).parent / "version_Local.json"
        
        if not versions_file.exists():
            default_versions = {
                "stable": {
                    "version": "16.2.1.3",
                    "description": "Стабильная версия",
                    "release_date": "2025-07-15"
                },
                "test": {
                    "version": "16.4.1.9", 
                    "description": "Тестовая версия",
                    "release_date": "2025-07-28"
                },
                "next_suggested": {
                    "stable": "16.2.1.4",
                    "test": "16.4.1.10"
                },
                "metadata": {
                    "last_updated": "2025-07-30",
                    "updated_by": "build_system"
                }
            }
            safe_json_write(versions_file, default_versions)
            return {"stable": "16.2.1.3", "test": "16.4.1.9"}
        
        with open(versions_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        stable_raw = (data.get("stable", {}) or {}).get("version", "16.2.1.3")
        test_raw   = (data.get("test", {}) or {}).get("version", "16.4.1.9")
        stable = normalize_to_4(stable_raw)
        test   = normalize_to_4(test_raw)

        changed = (stable_raw != stable) or (test_raw != test)
        if "next_suggested" in data and isinstance(data["next_suggested"], dict):
            ns = data["next_suggested"]
            for ch in ("stable", "test"):
                if ch in ns and ns[ch]:
                    new_val = normalize_to_4(ns[ch])
                    changed = changed or (ns[ch] != new_val)
                    ns[ch] = new_val

        if "stable" not in data or not isinstance(data["stable"], dict):
            data["stable"] = {}
            changed = True
        if "test" not in data or not isinstance(data["test"], dict):
            data["test"] = {}
            changed = True

        if (data["stable"].get("version") != stable):
            data["stable"]["version"] = stable
            changed = True
        if (data["test"].get("version") != test):
            data["test"]["version"] = test
            changed = True

        if changed:
            safe_json_write(versions_file, data)

        return {"stable": stable, "test": test}
        
    except Exception:
        return {"stable": "16.2.1.3", "test": "16.4.1.9"}

def get_suggested_version(channel: str) -> str:
    """Получает предложенную версию из файла"""
    try:
        versions_file = Path(__file__).parent / "version_Local.json"
        
        if versions_file.exists():
            with open(versions_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            suggested = (data.get("next_suggested", {}) or {}).get(channel)
            if suggested:
                return normalize_to_4(suggested)
        
        versions = fetch_local_versions()
        current = versions.get(channel, "0.0.0.0")
        return normalize_to_4(suggest_next(current))
        
    except Exception:
        return "1.0.0.0"

def update_versions_file(channel: str, new_version: str):
    """Обновляет файл версий после успешной сборки"""
    try:
        from datetime import datetime
        versions_file = Path(__file__).parent / "version_Local.json"
        
        if versions_file.exists():
            with open(versions_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            data = {"stable": {}, "test": {}, "next_suggested": {}, "metadata": {}}
        
        new_version = normalize_to_4(new_version)
        
        data[channel] = {
            "version": new_version,
            "description": f"{'Стабильная' if channel == 'stable' else 'Тестовая'} версия",
            "release_date": datetime.now().strftime("%Y-%m-%d")
        }
        
        if "next_suggested" not in data or not isinstance(data["next_suggested"], dict):
            data["next_suggested"] = {}
        data["next_suggested"][channel] = normalize_to_4(suggest_next(new_version))
        
        data["metadata"] = {
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "updated_by": "build_system"
        }
        
        safe_json_write(versions_file, data)
            
        log_queue = getattr(run, "log_queue", None)
        if log_queue is not None:
            log_queue.put(f"✔ Версии обновлены в {versions_file}")
            
    except Exception as e:
        log_queue = getattr(run, "log_queue", None)
        if log_queue is not None:
            log_queue.put(f"⚠️ Ошибка обновления версий: {e}")

def _taskkill(exe: str):
    run(f'taskkill /F /T /IM "{exe}" >nul 2>&1', check=False)

def stop_running_zapret():
    """Аккуратно гасит все Zapret.exe"""
    log_queue = getattr(run, "log_queue", None)
    if log_queue is not None:
        log_queue.put("Ищу запущенный Zapret.exe …")

    try:
        import psutil
        targets = []
        for p in psutil.process_iter(["name"]):
            n = (p.info["name"] or "").lower()
            if n in ("zapret.exe"):
                targets.append(p)
                try:
                    if log_queue is not None:
                        log_queue.put(f"  → terminate PID {p.pid} ({n})")
                    p.terminate()
                except Exception:
                    pass

        if targets:
            psutil.wait_procs(targets, timeout=3)
            for p in targets:
                if p.is_running():
                    try:
                        if log_queue is not None:
                            log_queue.put(f"  → kill PID {p.pid}")
                        p.kill()
                    except Exception:
                        pass
    except ImportError:
        pass

    _taskkill("Zapret.exe")

def _sub(line: str, repl: str, text: str) -> str:
    """Безопасно заменяет строку <line>=… """
    pattern = rf"(?im)^\s*{line}\s*=.*$"
    if re.search(pattern, text):
        return re.sub(pattern,
                      lambda m: f"{m.group(0).split('=')[0]}= {repl}",
                      text)
    return text.replace("[Setup]", f"[Setup]\n{line}={repl}", 1)

def prepare_iss(channel: str, version: str) -> Path:
    """Просто копирует универсальный ISS файл"""
    src = ROOT / "zapret_universal.iss"
    if not src.exists():
        raise FileNotFoundError(f"zapret_universal.iss не найден в {ROOT}")
    
    dst = ROOT / f"zapret_{channel}.iss" 
    shutil.copy(src, dst)
    
    log_queue = getattr(run, "log_queue", None)
    if log_queue is not None:
        log_queue.put(f"✓ Скопирован ISS файл: {dst}")
    
    return dst

def write_build_info(channel: str, version: str):
    dst = ROOT / "config" / "build_info.py"
    dst.parent.mkdir(exist_ok=True)
    dst.write_text(f"# AUTOGENERATED\nCHANNEL={channel!r}\nAPP_VERSION={normalize_to_4(version)!r}\n",
                   encoding="utf-8-sig")
    log_queue = getattr(run, "log_queue", None)
    if log_queue is not None:
        log_queue.put("✔ build_info.py updated")

# ════════════════════════════════════════════════════════════════
#  GUI КЛАСС
# ════════════════════════════════════════════════════════════════
class BuildReleaseGUI:
    def __init__(self, cli: dict[str, str | bool | None] | None = None):
        self.cli = cli or {}
        self.root = tk.Tk()
        self.root.title("Zapret Release Builder")
        self.root.geometry("1100x1300")
        self.root.minsize(1100, 1300)
        
        # Стилизация
        self.setup_styles()

        # Инициализация менеджера клавиатуры
        self.keyboard_manager = KeyboardManager(self.root)

        # Очередь для логов
        self.log_queue = Queue()
        setattr(run, "log_queue", self.log_queue)

        # Нефатальные ошибки (например, сетевые сбои публикации).
        self.nonfatal_errors: list[str] = []
        
        # Переменные
        self.channel_var = tk.StringVar(value="test")
        self.version_var = tk.StringVar()
        self.build_method_var = tk.StringVar(value="pyinstaller")
        self.publish_telegram_var = tk.BooleanVar(value=False)
        # Proxy для Telegram uploader/auth (полезно выключать при full-tunnel VPN).
        proxy_host = (os.environ.get("ZAPRET_PROXY_HOST") or os.environ.get("ZAPRET_SOCKS5_HOST") or "").strip()
        proxy_port = (os.environ.get("ZAPRET_PROXY_PORT") or os.environ.get("ZAPRET_SOCKS5_PORT") or "").strip()
        default_tg_proxy = bool(proxy_host or proxy_port)
        if _env_truthy("ZAPRET_TG_NO_PROXY") or _env_truthy("ZAPRET_TG_NO_SOCKS"):
            default_tg_proxy = False
        self.telegram_use_socks_var = tk.BooleanVar(value=default_tg_proxy)
        self.fast_exe_var = tk.BooleanVar(value=bool(self.cli.get("fast_exe")))
        self.fast_exe_dest_var = tk.StringVar(value=str(self.cli.get("fast_exe_dest") or ""))
        self.auto_run_installer_var = tk.BooleanVar(value=True)
        self.last_installer_path: Path | None = None
        self.versions_info = {"stable": "—", "test": "—"}
        self.telegram_proxy_info_var = tk.StringVar(value="")
        
        # Создаем интерфейс
        self.create_widgets()
        
        # Загружаем версии
        self.load_versions()
        
        # Запускаем обработчик очереди логов
        self.process_log_queue()

        # Обновляем статус прокси Telegram в GUI
        try:
            self.telegram_use_socks_var.trace_add("write", lambda *_: self._update_telegram_proxy_info())
        except Exception:
            pass
        self._update_telegram_proxy_info()

    def _telegram_proxy_desc(self, enabled: bool) -> str:
        if not enabled:
            return "Proxy (TG): off"

        scheme = (os.environ.get("ZAPRET_TG_PROXY_SCHEME") or os.environ.get("ZAPRET_PROXY_SCHEME") or "socks5").strip().lower()
        if scheme in {"https"}:
            scheme = "http"

        host = (os.environ.get("ZAPRET_PROXY_HOST") or os.environ.get("ZAPRET_SOCKS5_HOST") or "").strip() or "127.0.0.1"
        port = (os.environ.get("ZAPRET_PROXY_PORT") or os.environ.get("ZAPRET_SOCKS5_PORT") or "").strip() or "10808"

        return f"Proxy (TG): {scheme}://{host}:{port}"

    def _update_telegram_proxy_info(self) -> None:
        try:
            enabled = bool(self.telegram_use_socks_var.get())
        except Exception:
            enabled = False
        self.telegram_proxy_info_var.set(self._telegram_proxy_desc(enabled))

    def _project_root(self) -> Path:
        return ROOT

    def _source_root(self) -> Path:
        # единый канонический путь сборки внутри репозитория
        return ROOT / "dist"

    def _produced_installer_path(self, channel: str, version: str) -> Path:
        suf = "_TEST" if channel == "test" else ""
        v = version_to_filename_suffix(version)
        return self._source_root() / f"Zapret2Setup{suf}_{v}.exe"

    def _built_exe_path(self) -> Path:
        # Canonical dist path for Inno Setup (SOURCEPATH): ./dist/Zapret.exe
        return self._source_root() / "Zapret.exe"

    def _sync_built_exe_to_source_root(self) -> None:
        """Sync build output from ./dist/Zapret/ into ./dist/.

        PyInstaller/Nuitka produce onedir into ./dist/Zapret/{Zapret.exe,_internal}.
        Inno Setup installs from SOURCEPATH=./dist, so we must refresh Zapret.exe + _internal there.
        """

        def _safe_replace(src: Path, dst: Path, label: str, *, attempts: int = 8, base_delay: float = 0.6) -> None:
            # Win32 sometimes keeps lock handles on exe/folder after build or run.
            # Retry atomic replace after trying to stop blockers.
            for attempt in range(1, attempts + 1):
                try:
                    os.replace(src, dst)
                    return
                except PermissionError as e:
                    if getattr(e, "winerror", None) != 5:
                        raise

                    if attempt >= attempts:
                        raise

                    self.log_queue.put(
                        f"⚠️ Не удалось заменить {label} (попытка {attempt}/{attempts}): доступ запрещен; "
                        "попробую завершить блокирующие процессы и повторить."
                    )

                    # Убираем процессы, которые обычно держат блокировки.
                    self._kill_blocking_processes()
                    try:
                        stop_running_zapret()
                    except Exception:
                        pass

                    time.sleep(base_delay * attempt)

        src_dir = self._source_root() / "Zapret"
        src_exe = src_dir / "Zapret.exe"
        src_internal = src_dir / "_internal"

        dst_dir = self._source_root()
        dst_exe = dst_dir / "Zapret.exe"
        dst_internal = dst_dir / "_internal"

        if not src_exe.exists():
            raise FileNotFoundError(f"Не найден собранный exe: {src_exe}")
        if not src_internal.is_dir():
            raise FileNotFoundError(f"Не найдена папка _internal: {src_internal}")

        self._kill_blocking_processes()

        # Atomically replace Zapret.exe
        tmp_exe = dst_dir / "Zapret.exe.tmp"
        if tmp_exe.exists():
            try:
                tmp_exe.unlink()
            except Exception:
                pass
        shutil.copy2(src_exe, tmp_exe)
        _safe_replace(tmp_exe, dst_exe, "Zapret.exe")

        # Replace _internal directory
        tmp_internal = dst_dir / "_internal.tmp"
        if tmp_internal.exists():
            shutil.rmtree(tmp_internal, ignore_errors=True)
        shutil.copytree(src_internal, tmp_internal)
        if dst_internal.exists():
            shutil.rmtree(dst_internal, ignore_errors=True)
        _safe_replace(tmp_internal, dst_internal, "_internal")

        size_mb = dst_exe.stat().st_size / 1024 / 1024
        self.log_queue.put(f"✅ Dist обновлён: {dst_exe} ({size_mb:.1f} MB)")

        # Remove intermediate onedir folder to avoid duplicates.
        # Set ZAPRET_KEEP_ZAPRET_SUBDIR=1 to keep it for debugging.
        try:
            if not _env_truthy("ZAPRET_KEEP_ZAPRET_SUBDIR"):
                if src_dir.exists() and src_dir.is_dir():
                    shutil.rmtree(src_dir, ignore_errors=True)
        except Exception:
            pass

    def _fast_dest_exe_path(self, channel: str) -> Path:
        override = (self.fast_exe_dest_var.get() or "").strip()
        if override:
            p = Path(override)
            if p.suffix.lower() == ".exe":
                return p
            return p / "Zapret.exe"

        env_override = (os.environ.get("ZAPRET_FAST_EXE_DEST") or "").strip()
        if env_override:
            p = Path(env_override)
            if p.suffix.lower() == ".exe":
                return p
            return p / "Zapret.exe"

        detected = self._detect_installed_zapret_exe(channel)
        if detected is not None:
            return detected

        appdata = os.environ.get("APPDATA")
        if appdata:
            base = Path(appdata)
        else:
            base = Path.home() / "AppData" / "Roaming"

        folder = "ZapretTwoDev" if channel == "test" else "ZapretTwo"
        return base / folder / "Zapret.exe"

    def _detect_installed_zapret_exe(self, channel: str) -> Path | None:
        """
        Пытаемся определить реальный путь установленной программы из реестра (Inno Setup uninstall key).

        Это нужно, потому что быстрый режим часто запускается под другим Windows-пользователем,
        а приложение установлено, например, в профиле Admin (AppData\\Roaming).
        """
        if sys.platform != "win32":
            return None

        try:
            import winreg  # stdlib on Windows
        except Exception:
            return None

        # Optional explicit AppId(s) from env for точного поиска.
        # Inno uninstall key name is usually "{APPID}_is1".
        appid_test = (os.environ.get("ZAPRET_INNO_APPID_TEST") or "").strip()
        appid_stable = (os.environ.get("ZAPRET_INNO_APPID_STABLE") or "").strip()

        # Heuristics: match by DisplayName and/or key name.
        want_test = channel == "test"
        wanted_folder = "zaprettwodev" if want_test else "zaprettwo"

        def _parse_display_icon(raw: str) -> str:
            raw = (raw or "").strip().strip('"')
            if not raw:
                return ""
            # Inno sometimes stores: "C:\\Path\\app.exe",0
            if "," in raw:
                raw = raw.split(",", 1)[0].strip().strip('"')
            return raw

        def _safe_get_value(hkey, name: str) -> str:
            try:
                v, _t = winreg.QueryValueEx(hkey, name)
                return str(v)
            except Exception:
                return ""

        def _iter_uninstall_roots():
            # Prefer searching both HKLM/HKCU and both views (64/32).
            roots = [
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
                (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
            ]
            views = []
            try:
                views.append(winreg.KEY_WOW64_64KEY)
                views.append(winreg.KEY_WOW64_32KEY)
            except Exception:
                views.append(0)

            for hive, path in roots:
                for view in views:
                    yield hive, path, view

        matches: list[tuple[int, Path]] = []

        for hive, root_path, view in _iter_uninstall_roots():
            try:
                root = winreg.OpenKey(hive, root_path, 0, winreg.KEY_READ | view)
            except Exception:
                continue

            try:
                i = 0
                while True:
                    try:
                        subkey_name = winreg.EnumKey(root, i)
                    except OSError:
                        break
                    i += 1

                    # If AppId provided, use exact key name match first.
                    if want_test and appid_test:
                        target = f"{appid_test}_is1"
                        if subkey_name.lower() != target.lower():
                            continue
                    if (not want_test) and appid_stable:
                        target = f"{appid_stable}_is1"
                        if subkey_name.lower() != target.lower():
                            continue

                    try:
                        h = winreg.OpenKey(root, subkey_name, 0, winreg.KEY_READ | view)
                    except Exception:
                        continue

                    try:
                        display_name = _safe_get_value(h, "DisplayName")
                        install_location = _safe_get_value(h, "InstallLocation")
                        app_path = _safe_get_value(h, "Inno Setup: App Path")
                        display_icon = _parse_display_icon(_safe_get_value(h, "DisplayIcon"))

                        # Candidate destination path.
                        candidate: Path | None = None
                        if display_icon.lower().endswith(".exe"):
                            candidate = Path(display_icon)
                        elif install_location:
                            candidate = Path(install_location) / "Zapret.exe"
                        elif app_path:
                            candidate = Path(app_path) / "Zapret.exe"

                        if candidate is None:
                            continue

                        # Score candidate relevance.
                        dn = (display_name or "").lower()
                        sk = (subkey_name or "").lower()
                        score = 0

                        if want_test:
                            if "test" in sk or "-test" in sk or "dev" in dn:
                                score += 100
                        else:
                            if ("test" not in sk and "-test" not in sk) and ("dev" not in dn):
                                score += 100

                        # Folder hint.
                        cand_s = str(candidate).lower().replace("/", "\\")
                        if wanted_folder in cand_s:
                            score += 50

                        if cand_s.endswith("\\zapret.exe") or cand_s.endswith("/zapret.exe"):
                            score += 20

                        # DisplayName hint.
                        if "zapret" in dn:
                            score += 10

                        if score > 0:
                            matches.append((score, candidate))
                    finally:
                        try:
                            winreg.CloseKey(h)
                        except Exception:
                            pass
            finally:
                try:
                    winreg.CloseKey(root)
                except Exception:
                    pass

        if not matches:
            return None

        # Prefer existing file if possible.
        matches.sort(key=lambda t: t[0], reverse=True)
        for _score, path in matches:
            try:
                if path.exists():
                    return path
            except Exception:
                continue
        return matches[0][1]

    def setup_styles(self):
        """Настройка стилей для современного вида"""
        style = ttk.Style()
        
        # Цветовая схема
        self.colors = {
            'bg': '#f0f0f0',
            'fg': '#333333',
            'accent': '#0078d4',
            'success': '#107c10',
            'error': '#d83b01',
            'warning': '#ff8c00',
            'frame_bg': '#ffffff',
            'button_bg': '#0078d4',
            'button_fg': '#ffffff'
        }
        
        self.root.configure(bg=self.colors['bg'])
        
        # Настройка стилей
        style.configure('Title.TLabel', font=('Segoe UI', 16, 'bold'))
        style.configure('Heading.TLabel', font=('Segoe UI', 12, 'bold'))
        style.configure('Info.TLabel', font=('Segoe UI', 10))
        style.configure('Card.TFrame', background=self.colors['frame_bg'], relief='flat', borderwidth=1)

    def run_telegram_auth(self):
        """Запуск авторизации Telegram (Telethon)."""
        auth_script = Path(__file__).parent / "telegram_auth_telethon.py"
        
        if not auth_script.exists():
            messagebox.showerror(
                "Ошибка",
                f"Скрипт авторизации не найден:\n{auth_script}"
            )
            return
        
        # Используем python.exe (с консолью)
        python_exe = sys.executable
        if python_exe.endswith('pythonw.exe'):
            python_exe = python_exe.replace('pythonw.exe', 'python.exe')
        
        if not Path(python_exe).exists():
            messagebox.showerror(
                "Ошибка",
                f"python.exe не найден:\n{python_exe}"
            )
            return
        
        try:
            env = os.environ.copy()
            if self.telegram_use_socks_var.get():
                env.pop("ZAPRET_TG_NO_SOCKS", None)
                env.pop("ZAPRET_TG_NO_PROXY", None)
            else:
                env["ZAPRET_TG_NO_SOCKS"] = "1"
                env["ZAPRET_TG_NO_PROXY"] = "1"
            subprocess.Popen(
                [python_exe, str(auth_script)],
                env=env,
                creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0
            )
            
            messagebox.showinfo(
                "Авторизация Telethon",
                "Открыто окно авторизации Telegram (Telethon).\n\n"
                "Следуйте инструкциям в консоли:\n"
                "1. Введите номер телефона с +\n"
                "2. Введите код из Telegram\n"
                "3. Если есть 2FA - введите пароль\n\n"
                "После успешной авторизации можете закрыть окно."
            )
            
        except Exception as e:
            messagebox.showerror(
                "Ошибка",
                f"Не удалось запустить авторизацию:\n{e}"
            )

    def run_telegram_auth_telethon_wsl(self):
        """Запуск авторизации Telegram (Telethon) внутри WSL."""
        if sys.platform != "win32":
            messagebox.showerror("Ошибка", "WSL авторизация доступна только на Windows")
            return
        if not shutil.which("wsl.exe"):
            messagebox.showerror("Ошибка", "wsl.exe не найден")
            return

        distro = os.environ.get("ZAPRET_WSL_DISTRO") or "Debian"
        script_linux = _to_wsl_path(Path(__file__).parent / "telegram_auth_telethon.py", distro)

        try:
            subprocess.Popen(
                ["wsl.exe", "-d", distro, "--", "python3", script_linux],
                creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0
            )
            messagebox.showinfo(
                "Авторизация Telethon (WSL)",
                "Откроется окно WSL для авторизации Telethon.\n\n"
                "1) Введите номер телефона\n"
                "2) Введите код из Telegram\n"
                "3) Если есть 2FA — пароль\n\n"
                "После завершения вернитесь в сборщик и повторите публикацию."
            )
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось запустить WSL авторизацию: {e}")
                    
    def create_widgets(self):
        """Создание всех виджетов"""
        # Главный контейнер
        main_container = ttk.Frame(self.root)
        main_container.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Заголовок
        title_frame = ttk.Frame(main_container)
        title_frame.pack(fill='x', pady=(0, 20))
        
        ttk.Label(title_frame, text="🚀 Zapret Release Builder", 
                 style='Title.TLabel').pack(side='left')
        
        # Информация о версиях
        self.version_info_frame = ttk.LabelFrame(main_container, text="Текущие версии (из файла)", 
                                                padding=15)
        self.version_info_frame.pack(fill='x', pady=(0, 15))

        self.test_label = ttk.Label(self.version_info_frame, text="Test: загрузка...", 
                                style='Info.TLabel')
        self.test_label.pack(anchor='w')
                
        self.stable_label = ttk.Label(self.version_info_frame, text="Stable: загрузка...", 
                                    style='Info.TLabel')
        self.stable_label.pack(anchor='w')

        # Информация о файле версий
        versions_file_path = Path(__file__).parent / "version_Local.json"
        file_info_label = ttk.Label(self.version_info_frame, 
                                text=f"📄 Файл: {versions_file_path.name}", 
                                style='Info.TLabel', foreground='gray')
        file_info_label.pack(anchor='w')

        # GitHub статус
        github_frame = ttk.LabelFrame(main_container, text="GitHub Release", 
                                     padding=15)
        github_frame.pack(fill='x', pady=(0, 15))
        
        if not GITHUB_AVAILABLE:
            ttk.Label(github_frame, text="❌ GitHub модуль недоступен!", 
                     style='Info.TLabel', foreground='red').pack(side='left')
        elif not is_github_enabled():
            ttk.Label(github_frame, text="⚠️ GitHub не настроен! Настройте токен в build_tools/github_release.py", 
                     style='Info.TLabel', foreground='orange').pack(side='left')
        else:
            status_text = get_github_config_info()
            ttk.Label(github_frame, text=f"✅ {status_text}", 
                     style='Info.TLabel', foreground='green').pack(side='left')

        # SSH статус
        ssh_frame = ttk.LabelFrame(main_container, text="SSH VPS деплой", 
                                padding=15)
        ssh_frame.pack(fill='x', pady=(0, 15))

        if not SSH_AVAILABLE:
            ttk.Label(ssh_frame, text="❌ SSH модуль недоступен!", 
                    style='Info.TLabel', foreground='red').pack(side='left')
        else:
            status_text = get_ssh_config_info()
            if is_ssh_configured():
                ttk.Label(ssh_frame, text=f"✅ {status_text}", 
                        style='Info.TLabel', foreground='green').pack(side='left')
            else:
                ttk.Label(ssh_frame, text=f"⚠️ {status_text}", 
                        style='Info.TLabel', foreground='orange').pack(side='left')

        # Telegram публикация
        telegram_frame = ttk.LabelFrame(main_container, text="Telegram канал публикация", 
                                    padding=15)
        telegram_frame.pack(fill='x', pady=(0, 15))

        telegram_ok, telegram_status = check_telegram_configured()

        status_label = ttk.Label(
            telegram_frame,
            text=telegram_status,
            style='Info.TLabel',
            foreground='green' if telegram_ok else 'orange'
        )
        status_label.pack(side='left')

        proxy_label = ttk.Label(
            telegram_frame,
            textvariable=self.telegram_proxy_info_var,
            style='Info.TLabel',
            foreground=self.colors['fg'],
        )
        proxy_label.pack(side='left', padx=(12, 0))

        # Чекбокс публикации
        self.publish_telegram_var = tk.BooleanVar(value=telegram_ok)
        self.publish_telegram_check = ttk.Checkbutton(
            telegram_frame,
            text="📢 Опубликовать в Telegram канал",
            variable=self.publish_telegram_var,
            state='normal' if telegram_ok else 'disabled'
        )
        self.publish_telegram_check.pack(side='right')

        # Proxy toggle (актуально для Amnezia/VPN на всю систему)
        self.telegram_socks_check = ttk.Checkbutton(
            telegram_frame,
            text="Proxy (TG)",
            variable=self.telegram_use_socks_var,
        )
        self.telegram_socks_check.pack(side='right', padx=(10, 0))

        # Кнопки авторизации (Pyrogram / Telethon WSL)
        if not telegram_ok:
            auth_button = ttk.Button(
                telegram_frame,
                text="🔑 Авторизация Telethon",
                command=self.run_telegram_auth
            )
            auth_button.pack(side='right', padx=(10, 0))

            if sys.platform == "win32":
                auth_button_wsl = ttk.Button(
                    telegram_frame,
                    text="🐧 Авторизация Telethon (WSL)",
                    command=self.run_telegram_auth_telethon_wsl
                )
                auth_button_wsl.pack(side='right', padx=(10, 0))

        # Настройки сборки
        settings_frame = ttk.LabelFrame(main_container, text="Настройки сборки", 
                                       padding=15)
        settings_frame.pack(fill='x', pady=(0, 15))
        
        # Выбор канала
        channel_frame = ttk.Frame(settings_frame)
        channel_frame.pack(fill='x', pady=(0, 10))
        
        ttk.Label(channel_frame, text="Канал:", width=15).pack(side='left')
        
        channel_buttons_frame = ttk.Frame(channel_frame)
        channel_buttons_frame.pack(side='left', padx=(10, 0))
        
        self.stable_radio = ttk.Radiobutton(channel_buttons_frame, text="Stable", 
                                           variable=self.channel_var, value="stable",
                                           command=self.on_channel_change)
        self.stable_radio.pack(side='left', padx=(0, 20))
        
        self.test_radio = ttk.Radiobutton(channel_buttons_frame, text="Test (Dev)", 
                                         variable=self.channel_var, value="test",
                                         command=self.on_channel_change)
        self.test_radio.pack(side='left')
        
        # Версия
        version_frame = ttk.Frame(settings_frame)
        version_frame.pack(fill='x', pady=(0, 10))
        
        ttk.Label(version_frame, text="Версия:", width=15).pack(side='left')
        
        self.version_entry = ttk.Entry(version_frame, textvariable=self.version_var, 
                                      width=20, font=('Segoe UI', 10))
        self.version_entry.pack(side='left', padx=(10, 10))
        
        self.suggest_button = ttk.Button(version_frame, text="Следующая", 
                                        command=self.suggest_version)
        self.suggest_button.pack(side='left')
        
        # Выбор метода сборки
        build_method_frame = ttk.Frame(settings_frame)
        build_method_frame.pack(fill='x', pady=(10, 0))
        
        ttk.Label(build_method_frame, text="Метод сборки:", width=15).pack(side='left')
        
        method_buttons_frame = ttk.Frame(build_method_frame)
        method_buttons_frame.pack(side='left', padx=(10, 0))
        
        # RadioButton для PyInstaller
        pyinstaller_status = "✅" if PYINSTALLER_AVAILABLE and check_pyinstaller_available() else "❌"
        self.pyinstaller_radio = ttk.Radiobutton(method_buttons_frame, 
                                                text=f"PyInstaller {pyinstaller_status} (рекомендуется)", 
                                                variable=self.build_method_var, 
                                                value="pyinstaller")
        self.pyinstaller_radio.pack(side='left', padx=(0, 20))

        # RadioButton для Nuitka
        nuitka_status = "✅" if NUITKA_AVAILABLE and check_nuitka_available() else "❌"
        self.nuitka_radio = ttk.Radiobutton(method_buttons_frame, 
                                        text=f"Nuitka {nuitka_status} (быстрее)", 
                                        variable=self.build_method_var, 
                                        value="nuitka")
        self.nuitka_radio.pack(side='left')

        # Информация о методах
        method_info_frame = ttk.Frame(settings_frame)
        method_info_frame.pack(fill='x', pady=(5, 0))
        
        ttk.Label(method_info_frame, 
                 text="💡 Nuitka создает более оптимизированный exe, но требует больше времени",
                 style='Info.TLabel', foreground='gray').pack(anchor='w', padx=(120, 0))

        # Быстрый режим (dev): копирование Zapret.exe в AppData и опциональная отправка в Telegram
        fast_frame = ttk.Frame(settings_frame)
        fast_frame.pack(fill='x', pady=(10, 0))

        ttk.Label(fast_frame, text="Быстро:", width=15).pack(side='left')

        self.fast_exe_check = ttk.Checkbutton(
            fast_frame,
            text="⚡ Быстрая замена Zapret.exe (пропустить Inno/GitHub/SSH)",
            variable=self.fast_exe_var
        )
        self.fast_exe_check.pack(side='left', padx=(10, 0))

        # Auto-run installer after successful build (default enabled)
        installer_frame = ttk.Frame(settings_frame)
        installer_frame.pack(fill='x', pady=(8, 0))

        ttk.Label(installer_frame, text="Установка:", width=15).pack(side='left')

        self.auto_run_installer_check = ttk.Checkbutton(
            installer_frame,
            text="Запустить установщик после сборки",
            variable=self.auto_run_installer_var,
        )
        self.auto_run_installer_check.pack(side='left', padx=(10, 0))

        fast_dest_frame = ttk.Frame(settings_frame)
        fast_dest_frame.pack(fill='x', pady=(5, 0))

        ttk.Label(fast_dest_frame, text="Fast dest:", width=15).pack(side='left')

        self.fast_exe_dest_entry = ttk.Entry(
            fast_dest_frame,
            textvariable=self.fast_exe_dest_var,
            width=70,
            font=('Segoe UI', 9)
        )
        self.fast_exe_dest_entry.pack(side='left', padx=(10, 0))

        ttk.Label(
            fast_dest_frame,
            text="(пусто = %APPDATA%\\ZapretTwoDev\\Zapret.exe)",
            style='Info.TLabel',
            foreground='gray'
        ).pack(side='left', padx=(10, 0))
        
        # Release notes
        notes_frame = ttk.LabelFrame(main_container, text="Release Notes", 
                                    padding=15)
        notes_frame.pack(fill='both', expand=True, pady=(0, 15))
        
        self.notes_text = scrolledtext.ScrolledText(notes_frame, height=6, 
                                                   font=('Segoe UI', 10),
                                                   wrap='word',
                                                   undo=True,
                                                   maxundo=20)
        self.notes_text.pack(fill='both', expand=True)
        
        # Подсказка
        hint_frame = ttk.Frame(notes_frame)
        hint_frame.pack(fill='x', pady=(5, 0))
        
        hint_label = ttk.Label(hint_frame, 
                              text="💡 Можно использовать несколько строк. Поддерживается Markdown.",
                              style='Info.TLabel', foreground='gray')
        hint_label.pack(side='left')
        
        shortcut_label = ttk.Label(hint_frame, 
                                  text="⌨️ Ctrl+V - вставить, Ctrl+A - выделить все, Ctrl+Z - отмена",
                                  style='Info.TLabel', foreground='gray')
        shortcut_label.pack(side='right')
        
        # Кнопки управления
        button_frame = ttk.Frame(main_container)
        button_frame.pack(fill='x')
        
        self.build_button = tk.Button(button_frame, text="🔨 Собрать и опубликовать", 
                                     command=self.start_build,
                                     bg=self.colors['button_bg'], 
                                     fg=self.colors['button_fg'],
                                     font=('Segoe UI', 11, 'bold'),
                                     padx=20, pady=10,
                                     cursor='hand2',
                                     relief='flat')
        self.build_button.pack(side='right')
        
        self.cancel_button = ttk.Button(button_frame, text="Отмена", 
                                       command=self.root.quit)
        self.cancel_button.pack(side='right', padx=(0, 10))
        
        # Прогресс и логи
        progress_frame = ttk.LabelFrame(main_container, text="Прогресс", 
                                       padding=10)
        progress_frame.pack(fill='both', expand=True, pady=(15, 0))
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var,
                                           maximum=100, length=300)
        self.progress_bar.pack(fill='x', pady=(0, 10))
        
        # Лог
        self.log_text = scrolledtext.ScrolledText(progress_frame, height=10, 
                                                 font=('Consolas', 9),
                                                 bg='#1e1e1e', fg='#d4d4d4',
                                                 wrap='word')
        self.log_text.pack(fill='both', expand=True)
        self.log_text.config(state='disabled')

    def load_versions(self):
        """Загрузка текущих версий из локального файла"""
        try:
            versions = fetch_local_versions()
            self.versions_info = versions
            self.update_version_labels()
        except Exception as e:
            self.log_queue.put(f"❌ Ошибка загрузки версий: {e}")
            self.versions_info = {"stable": "16.2.1.3", "test": "16.4.1.9"}
            self.update_version_labels()
        
    def update_version_labels(self):
        """Обновление меток с версиями"""
        self.test_label.config(text=f"Test: {self.versions_info['test']}")
        self.stable_label.config(text=f"Stable: {self.versions_info['stable']}")
        self.suggest_version()
        
    def on_channel_change(self):
        """При смене канала обновляем предложение версии"""
        self.suggest_version()
        
    def suggest_version(self):
        """Предложить следующую версию"""
        channel = self.channel_var.get()
        suggested = get_suggested_version(channel)
        self.version_var.set(suggested)
        
    def add_log(self, message):
        """Добавление сообщения в лог"""
        self.log_text.config(state='normal')
        self.log_text.insert('end', message + '\n')
        self.log_text.see('end')
        self.log_text.config(state='disabled')
        self.root.update_idletasks()
        
    def process_log_queue(self):
        """Обработка очереди логов"""
        try:
            batch = []
            while len(batch) < 100:
                try:
                    message = self.log_queue.get_nowait()
                    batch.append(message)
                except:
                    break
            
            if batch:
                self.log_text.config(state='normal')
                self.log_text.insert('end', '\n'.join(batch) + '\n')
                self.log_text.see('end')
                self.log_text.config(state='disabled')
                self.root.update_idletasks()
        finally:
            self.root.after(100, self.process_log_queue)
            
    def start_build(self):
        """Запуск процесса сборки"""
        fast_exe = self.fast_exe_var.get()

        skip_github = _env_truthy("ZAPRET_SKIP_GITHUB") or _env_truthy("ZAPRET_GITHUB_SKIP")

        if not fast_exe and not skip_github:
            if not GITHUB_AVAILABLE:
                messagebox.showerror("Ошибка", "GitHub модуль недоступен!")
                return
            if not is_github_enabled():
                messagebox.showerror(
                    "Ошибка",
                    "GitHub не настроен!\n\nНастройте токен в build_tools/github_release.py"
                )
                return
        
        # Валидация
        version = normalize_to_4(self.version_var.get().strip())
        if not version:
            messagebox.showerror("Ошибка", "Укажите версию!")
            return
            
        VERSION_RE = re.compile(r"^\d+\.\d+\.\d+\.\d+$")
        if not VERSION_RE.fullmatch(version):
            messagebox.showerror("Ошибка", f"Неверный формат версии: {version}\n"
                                        "Используйте формат X.X.X.X (4 цифры)")
            return
            
        notes = self.notes_text.get('1.0', 'end').strip()
        if not notes:
            notes = f"Zapret {version}"
            
        channel = self.channel_var.get()
        build_method = self.build_method_var.get()
        publish_telegram = self.publish_telegram_var.get()
        
        # Проверка доступности выбранного метода
        if build_method == "nuitka" and not NUITKA_AVAILABLE:
            messagebox.showerror("Ошибка", "Модуль nuitka_builder недоступен!")
            return
            
        if build_method == "pyinstaller" and not PYINSTALLER_AVAILABLE:
            messagebox.showerror("Ошибка", "Модуль pyinstaller_builder недоступен!")
            return
        
        # Предупреждение если Telegram включен но не настроен
        if publish_telegram:
            telegram_ok, telegram_msg = check_telegram_configured()
            if not telegram_ok:
                if not messagebox.askyesno(
                    "Предупреждение",
                    f"{telegram_msg}\n\n"
                    "Публикация в Telegram будет пропущена.\n"
                    "Продолжить сборку?"
                ):
                    return
        
        # Подтверждение
        msg = f"Канал: {channel.upper()}\nВерсия: {version}\n"
        msg += f"Метод сборки: {build_method.upper()}\n"

        if fast_exe:
            msg += "\n⚡ Быстрый режим:\n"
            msg += f"  • Копировать Zapret.exe → {self._fast_dest_exe_path(channel)}\n"
            if publish_telegram:
                msg += "  • Telegram канал ✅ (локально)\n"
            msg += "\nInno Setup / GitHub / SSH: будут пропущены.\n"
        else:
            msg += "\nРелиз будет опубликован на:\n"
            if skip_github:
                msg += "  • GitHub ⏭️ (skip)\n"
            else:
                msg += "  • GitHub ✅\n"
            if SSH_AVAILABLE and is_ssh_configured():
                msg += "  • SSH VPS ✅\n"
                if publish_telegram:
                    msg += "  • Telegram канал ✅\n"
        
        msg += "\nПродолжить сборку?"
        
        if not messagebox.askyesno("Подтверждение", msg):
            return
            
        # Блокируем интерфейс
        self.build_button.config(state='disabled', text="⏳ Идет сборка...")
        self.cancel_button.config(state='disabled')
        self.progress_var.set(0)
        
        # Запускаем сборку в отдельном потоке
        thread = threading.Thread(target=self.build_process, 
                                 args=(channel, version, notes, build_method),
                                 daemon=True)
        thread.start()
        
    def build_process(self, channel, version, notes, build_method):
        """Процесс сборки в отдельном потоке"""
        try:
            fast_exe = self.fast_exe_var.get()
            publish_telegram = self.publish_telegram_var.get()
            skip_github = _env_truthy("ZAPRET_SKIP_GITHUB") or _env_truthy("ZAPRET_GITHUB_SKIP")
            github_nonfatal = _env_truthy("ZAPRET_GITHUB_NONFATAL")

            # Базовые шаги
            steps: list[tuple[int, str, Any]] = [
                (10, "Обновление build_info.py", lambda: write_build_info(channel, version))
            ]
            
            # Добавляем шаги в зависимости от метода сборки
            if build_method == "nuitka":
                steps.extend([
                    (60, "Сборка Nuitka", lambda: run_nuitka(channel, version, ROOT, PY, run, self.log_queue)),
                ])
            else:  # pyinstaller
                steps.extend([
                    (35, "Создание spec файла", lambda: create_spec_file(channel, ROOT, self.log_queue)),
                    (60, "Сборка PyInstaller", lambda: run_pyinstaller(channel, ROOT, run, self.log_queue)),
                ])

            # Sync built Zapret.exe/_internal into SOURCEPATH (./dist)
            steps.append((70, "Синхронизация Zapret.exe", lambda: self._sync_built_exe_to_source_root()))
            
            if fast_exe:
                steps.append((80, "Быстрая замена Zapret.exe", lambda: self.fast_deploy_exe(channel)))
                if publish_telegram:
                    steps.append((95, "Telegram публикация (Zapret.exe)", lambda: self.publish_exe_to_telegram(channel, version, notes)))
            else:
                # Общие финальные шаги
                steps.append((80, "Сборка Inno Setup", lambda: self.run_inno_setup(channel, version)))

                # Запуск установщика сразу после сборки (в отдельном потоке, не блокирует загрузку)
                if self.auto_run_installer_var.get():
                    def _run_installer_async():
                        t = threading.Thread(
                            target=self.run_built_installer,
                            args=(channel, version),
                            daemon=True,
                        )
                        t.start()
                    steps.append((82, "Запуск установщика", _run_installer_async))

                if not skip_github:
                    def _github_step():
                        try:
                            self.create_github_release(channel, version, notes)
                        except Exception as e:
                            if github_nonfatal:
                                msg = f"GitHub release: {e}"
                                self.nonfatal_errors.append(msg)
                                self.log_queue.put(f"⚠️ {msg}")
                                self.log_queue.put("⚠️ Продолжаем сборку (ZAPRET_GITHUB_NONFATAL=1)")
                                return
                            raise

                    steps.append((95, "Создание GitHub release", _github_step))
                 
                # SSH деплой
                if SSH_AVAILABLE and is_ssh_configured():
                    steps.append((98, "SSH VPS деплой", lambda: self.deploy_to_ssh(channel, version, notes)))
                
            steps.append((100, "Завершение", lambda: None))
            
            for progress, status, func in steps:
                if func:
                    self.log_queue.put(f"\n{'='*50}")
                    self.log_queue.put(f"📌 {status}")
                    self.log_queue.put(f"{'='*50}")
                    
                    func()
                    
                self.root.after(0, lambda p=progress: self.progress_var.set(p))
                time.sleep(0.5)
                
            self.log_queue.put("\n✅ СБОРКА ЗАВЕРШЕНА УСПЕШНО!")
            self.root.after(0, self.build_complete)
            
        except Exception as e:
            self.log_queue.put(f"\n❌ ОШИБКА: {str(e)}")
            import traceback
            self.log_queue.put(traceback.format_exc())
            self.root.after(0, lambda: self.build_error(str(e)))

    def deploy_to_ssh(self, channel, version, notes):
        """SSH деплой на все VPS сервера"""
        produced = self._produced_installer_path(channel, version)
        
        if not produced.exists():
            raise FileNotFoundError(f"{produced} not found")
        
        publish_telegram = self.publish_telegram_var.get()
        
        self.log_queue.put(f"\n📦 SSH деплой версии: {version}")
        self.log_queue.put(f"🔧 Канал: {channel.upper()}")
        
        if publish_telegram:
            if (os.environ.get("ZAPRET_TG_SSH_HOST") or os.environ.get("ZAPRET_TG_SSH_ENABLED")):
                self.log_queue.put("📢 Telegram: будет опубликовано через SSH (Pyrogram) на удаленном сервере")
            else:
                self.log_queue.put("📢 Telegram: будет опубликовано локально с ПК через SOCKS5")
        
        # ✅ Вызываем функцию с флагом публикации
        success, message = deploy_to_all_servers(
            file_path=produced,
            channel=channel,
            version=version,
            notes=notes,
            publish_telegram=publish_telegram,  # ✅ Передаём флаг
            log_queue=self.log_queue
        )
        
        if not success:
            raise Exception(f"SSH деплой не удался: {message}")
        
        self.log_queue.put(f"\n{'='*60}")
        self.log_queue.put(f"✅ SSH ДЕПЛОЙ ЗАВЕРШЕН")
        self.log_queue.put(f"{'='*60}")
        self.log_queue.put(message)


    def _kill_blocking_processes(self):
        """Убить процессы которые могут блокировать файлы"""
        processes_to_kill = [
            "ISCC.exe",      # Inno Setup компилятор
            "compil32.exe",  # Inno Setup GUI
            "Zapret.exe",    # Наше приложение
        ]

        for proc_name in processes_to_kill:
            try:
                result = subprocess.run(
                    f'taskkill /F /IM "{proc_name}"',
                    shell=True,
                    capture_output=True,
                    timeout=5
                )
                if result.returncode == 0:
                    self.log_queue.put(f"   🔪 Убит процесс: {proc_name}")
            except Exception:
                pass

        # Небольшая пауза чтобы файлы освободились
        time.sleep(1)

    def run_inno_setup(self, channel, version, max_retries=10):
        """Запуск Inno Setup с временным именем"""

        # ✅ Убиваем блокирующие процессы перед началом
        self.log_queue.put("🔪 Завершение блокирующих процессов...")
        self._kill_blocking_processes()

        project_root = self._project_root()
        source_root = self._source_root()
        source_root.mkdir(parents=True, exist_ok=True)
        universal_iss = project_root / "zapret_universal.iss"
        iss_workdir = Path(tempfile.mkdtemp(prefix="iscc_"))
        target_iss = iss_workdir / f"zapret_{channel}.iss"
        
        timestamp = int(time.time())
        temp_name = f"Zapret2Setup_{channel}_{timestamp}_tmp"
        final_name = f"Zapret2Setup{'_TEST' if channel == 'test' else ''}_{version_to_filename_suffix(version)}"
        
        temp_file = source_root / f"{temp_name}.exe"
        final_file = source_root / f"{final_name}.exe"

        if final_file.exists():
            counter = 1
            base = final_file.with_suffix("")
            while True:
                candidate = Path(str(base) + f"_r{counter}.exe")
                if not candidate.exists():
                    final_file = candidate
                    self.log_queue.put(f"  ⚠️ Файл уже есть, сохраняем как: {final_file.name}")
                    break
                counter += 1
        
        self.log_queue.put(f"📦 Сборка во временный файл: {temp_name}.exe")
        ensure_inno_ico_dir(source_path=source_root, project_root=project_root, log_queue=self.log_queue)
        
        if not universal_iss.exists():
            raise FileNotFoundError(f"ISS не найден: {universal_iss}")
        
        iss_content = universal_iss.read_text(encoding='utf-8')
        iss_content = re.sub(
            r'OutputBaseFilename\s*=\s*.*',
            f'OutputBaseFilename={temp_name}',
            iss_content
        )
        
        target_iss.write_text(iss_content, encoding='utf-8')
        self.log_queue.put(f"✓ ISS настроен на вывод в {temp_name}.exe")
        
        iscc_path = Path(r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe")
        if not iscc_path.exists():
            iscc_path = Path(r"C:\Program Files\Inno Setup 6\ISCC.exe")
        if not iscc_path.exists():
            raise FileNotFoundError("Inno Setup не найден!")
        
        cmd = [
            str(iscc_path),
            f'/DCHANNEL={channel}',  # ✅ Строковый канал: "stable" или "test"
            f'/DVERSION={version}',
            f'/DSOURCEPATH={source_root}',
            f'/DPROJECTPATH={project_root}',
            str(target_iss)
        ]

        self.log_queue.put(f"📋 Канал: {channel}")
        self.log_queue.put(f"📋 Ожидаемая папка: {'ZapretTwoDev' if channel == 'test' else 'ZapretTwo'}")
        self.log_queue.put(f"📋 Ожидаемая иконка: {'ZapretDevLogo4.ico' if channel == 'test' else 'Zapret2.ico'}")
        
        try:
            for attempt in range(1, max_retries + 1):
                try:
                    self.log_queue.put(f"\n🔄 Попытка {attempt}/{max_retries}...")

                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        encoding='utf-8',
                        errors='ignore',
                        cwd=str(project_root),
                        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
                        timeout=300
                    )

                    if result.returncode != 0:
                        if result.stdout:
                            self.log_queue.put(result.stdout)
                        if result.stderr:
                            self.log_queue.put(f"❌ {result.stderr}")
                        raise RuntimeError(f"Inno Setup код: {result.returncode}")

                    if not temp_file.exists():
                        raise FileNotFoundError(f"Не создан: {temp_file}")

                    size_mb = temp_file.stat().st_size / 1024 / 1024
                    self.log_queue.put(f"✅ Собрано: {temp_name}.exe ({size_mb:.1f} MB)")

                    temp_file.rename(final_file)
                    self.log_queue.put(f"✅ Готово: {final_file.name}")

                    self.last_installer_path = final_file
                    return

                except subprocess.TimeoutExpired:
                    self.log_queue.put("⏱️ Таймаут! Inno Setup завис")
                    self._kill_inno_setup()
                    if temp_file.exists():
                        temp_file.unlink()
                    time.sleep(3)

                except Exception as e:
                    self.log_queue.put(f"❌ Ошибка: {e}")
                    if temp_file.exists():
                        try:
                            temp_file.unlink()
                        except Exception:
                            pass

                    if attempt < max_retries:
                        self.log_queue.put(f"⏳ Повтор через 5 сек...")
                        time.sleep(5)
                    else:
                        raise

        finally:
            try:
                shutil.rmtree(iss_workdir, ignore_errors=True)
            except Exception:
                pass

    def _kill_inno_setup(self):
        """Убить зависшие процессы Inno Setup"""
        for proc_name in ["ISCC.exe", "compil32.exe"]:
            try:
                subprocess.run(
                    f'taskkill /F /IM "{proc_name}"',
                    shell=True,
                    capture_output=True,
                    timeout=5
                )
            except:
                pass

    def _find_latest_installer(self, channel: str, version: str) -> Optional[Path]:
        project_root = self._source_root()
        v = version_to_filename_suffix(version)
        suf = "_TEST" if channel == "test" else ""
        pat = f"Zapret2Setup{suf}_{v}*.exe"
        candidates = [p for p in project_root.glob(pat) if p.is_file()]
        if not candidates:
            return None
        return max(candidates, key=lambda p: p.stat().st_mtime)

    def run_built_installer(self, channel: str, version: str) -> None:
        if sys.platform != "win32":
            return

        installer = self.last_installer_path
        if not installer or not installer.exists():
            installer = self._find_latest_installer(channel, version)

        if not installer or not installer.exists():
            raise FileNotFoundError("Установщик не найден после сборки")

        self.log_queue.put(f"▶ Запуск установщика: {installer.name}")
        try:
            self._kill_blocking_processes()
        except Exception:
            pass

        try:
            os.startfile(str(installer))
        except Exception as e:
            raise RuntimeError(f"Не удалось запустить установщик: {e}")

    def _run_process_stream(
        self,
        cmd: list[str],
        *,
        cwd: Path | None = None,
        timeout: int | None = None,
        env: dict | None = None,
    ) -> int:
        """Запускает процесс и стримит stdout/stderr в лог."""
        startupinfo = None
        creationflags = 0
        if sys.platform == "win32":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

        proc = subprocess.Popen(
            cmd,
            cwd=str(cwd) if cwd else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            universal_newlines=True,
            startupinfo=startupinfo,
            creationflags=creationflags,
            env=env,
        )

        def _reader(pipe, prefix: str):
            try:
                for line in iter(pipe.readline, ""):
                    if line.strip():
                        self.log_queue.put(f"{prefix}{line.rstrip()}")
            finally:
                try:
                    pipe.close()
                except Exception:
                    pass

        t_out = threading.Thread(target=_reader, args=(proc.stdout, "   "), daemon=True)
        t_err = threading.Thread(target=_reader, args=(proc.stderr, "   ⚠️ "), daemon=True)
        t_out.start()
        t_err.start()

        try:
            returncode = proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            try:
                proc.kill()
            except Exception:
                pass
            returncode = proc.wait(timeout=10)

        t_out.join(timeout=2)
        t_err.join(timeout=2)
        return int(returncode)

    def fast_deploy_exe(self, channel: str) -> None:
        """
        Быстрое обновление dev-билда: копирует собранный Zapret.exe + _internal в AppData.
        По умолчанию: %APPDATA%\\ZapretTwoDev\\Zapret.exe (для test).
        """
        self.log_queue.put("🔪 Завершение блокирующих процессов...")
        self._kill_blocking_processes()

        src = self._built_exe_path()
        if not src.exists():
            raise FileNotFoundError(f"Не найден собранный файл: {src}")

        src_internal = src.parent / "_internal"

        dst = self._fast_dest_exe_path(channel)
        if sys.platform == "win32" and not (self.fast_exe_dest_var.get() or "").strip() and not (os.environ.get("ZAPRET_FAST_EXE_DEST") or "").strip():
            self.log_queue.put(f"🔎 Авто-цель (реестр/APPDATA): {dst}")
        dst.parent.mkdir(parents=True, exist_ok=True)

        tmp = dst.with_suffix(".tmp.exe")
        self.log_queue.put(f"📥 Копирование: {src}")
        self.log_queue.put(f"📤 В: {dst}")

        shutil.copy2(src, tmp)

        if dst.exists():
            backup = dst.with_suffix(".old.exe")
            counter = 1
            while backup.exists():
                backup = dst.with_suffix(f".old{counter}.exe")
                counter += 1
            try:
                dst.rename(backup)
                self.log_queue.put(f"  → Бэкап: {backup.name}")
            except Exception as e:
                self.log_queue.put(f"  ⚠️ Не удалось сохранить бэкап: {e}")

        os.replace(tmp, dst)
        try:
            if dst.stat().st_size != src.stat().st_size:
                raise RuntimeError("Размер назначения не совпал с исходным файлом")
        except Exception as e:
            raise RuntimeError(f"Проверка копирования не прошла: {e}")
        size_mb = dst.stat().st_size / 1024 / 1024
        self.log_queue.put(f"✅ Обновлено: {dst} ({size_mb:.1f} MB)")

        # Синхронизируем _internal (onedir build)
        if src_internal.is_dir():
            dst_internal = dst.parent / "_internal"
            self.log_queue.put(f"📦 Синхронизация _internal → {dst_internal}")
            tmp_internal = dst.parent / "_internal.tmp"
            if tmp_internal.exists():
                shutil.rmtree(tmp_internal, ignore_errors=True)
            shutil.copytree(src_internal, tmp_internal)
            if dst_internal.exists():
                shutil.rmtree(dst_internal, ignore_errors=True)
            tmp_internal.rename(dst_internal)
            self.log_queue.put(f"✅ _internal обновлён")

    def publish_exe_to_telegram(self, channel: str, version: str, notes: str) -> None:
        """
        Публикует Zapret.exe в Telegram без Inno/SSH.

        Публикация идёт напрямую с ПК через SOCKS5 (по умолчанию 127.0.0.1:10808).
        """
        telegram_ok, telegram_msg = check_telegram_configured()
        if not telegram_ok:
            raise RuntimeError(telegram_msg)

        exe_path = self._built_exe_path()
        if not exe_path.exists():
            raise FileNotFoundError(f"Файл не найден: {exe_path}")

        TELEGRAM_API_ID, TELEGRAM_API_HASH = _load_build_telegram_config()

        uploader = Path(__file__).parent / "telegram_uploader_telethon_fixed.py"
        if not uploader.exists():
            raise FileNotFoundError(f"Uploader не найден: {uploader}")

        python_exe = sys.executable
        if python_exe.endswith("pythonw.exe"):
            python_exe = python_exe.replace("pythonw.exe", "python.exe")

        file_size_mb = exe_path.stat().st_size / 1024 / 1024
        timeout = 1800 if file_size_mb > 100 else 1200
        env = os.environ.copy()
        if self.telegram_use_socks_var.get():
            env.pop("ZAPRET_TG_NO_SOCKS", None)
            env.pop("ZAPRET_TG_NO_PROXY", None)
            tg_mode = "Telethon+Proxy"
        else:
            env["ZAPRET_TG_NO_SOCKS"] = "1"
            env["ZAPRET_TG_NO_PROXY"] = "1"
            tg_mode = "Telethon (no proxy)"

        self.log_queue.put(f"📤 Telegram ({tg_mode}): отправка {exe_path.name} ({file_size_mb:.1f} MB)")

        cmd = [
            python_exe,
            str(uploader),
            str(exe_path),
            channel,
            version,
            notes or f"Zapret {version}",
            str(TELEGRAM_API_ID),
            str(TELEGRAM_API_HASH),
        ]
        rc = self._run_process_stream(cmd, cwd=Path(__file__).parent, timeout=timeout, env=env)
        if rc != 0:
            raise RuntimeError(f"Telegram uploader завершился с кодом {rc}")
  
    def create_github_release(self, channel, version, notes):
        """Создание GitHub release"""
        produced = self._produced_installer_path(channel, version)
        
        if not produced.exists():
            raise FileNotFoundError(f"{produced} not found")
            
        url = create_github_release(channel, version, produced, notes, self.log_queue)
        if url:
            self.log_queue.put(f"🔗 GitHub release: {url}")
        else:
            raise Exception("Не удалось создать GitHub release")
        
    def build_complete(self):
        """Вызывается при успешном завершении сборки"""
        self.build_button.config(state='normal', text="🔨 Собрать и опубликовать")
        self.cancel_button.config(state='normal')
        
        channel = self.channel_var.get()
        version = self.version_var.get().strip()
        update_versions_file(channel, version)
        
        if self.nonfatal_errors:
            messagebox.showwarning(
                "Готово, но с предупреждениями",
                "Сборка завершена, но есть проблемы с публикацией:\n\n" + "\n".join(self.nonfatal_errors)
            )
            self.nonfatal_errors.clear()

        messagebox.showinfo("Успех", "Сборка и публикация завершены успешно!")
        self.load_versions()
        
    def build_error(self, error_msg):
        """Вызывается при ошибке сборки"""
        self.build_button.config(state='normal', text="🔨 Собрать и опубликовать")
        self.cancel_button.config(state='normal')
        self.progress_var.set(0)
        
        messagebox.showerror("Ошибка сборки", f"Произошла ошибка:\n\n{error_msg}")
        
    def run(self):
        """Запуск GUI"""
        self.center_window()
        self.root.mainloop()
        
    def center_window(self):
        """Центрирование окна на экране"""
        self.root.update_idletasks()
        
        window_width = self.root.winfo_width()
        window_height = self.root.winfo_height()
        
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")


def run_without_console():
    """Перезапускает скрипт через pythonw.exe"""
    if sys.executable.endswith('python.exe'):
        pythonw = sys.executable.replace('python.exe', 'pythonw.exe')
        if Path(pythonw).exists():
            subprocess.Popen([pythonw] + sys.argv, 
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            sys.exit(0)

def _parse_cli_args(argv: list[str]) -> dict[str, str | bool | None]:
    """
    Простой парсер CLI-аргументов (без argparse, чтобы не усложнять GUI-скрипт).

    Поддержка:
      --fast-exe / --quick-exe          включить быстрый режим (копирование Zapret.exe)
      --fast-exe-dest=<path>           переопределить папку/файл назначения
    """
    fast_exe = False
    fast_exe_dest: str | None = None
    for arg in argv:
        if arg in {"--fast-exe", "--quick-exe"}:
            fast_exe = True
            continue
        if arg.startswith("--fast-exe-dest="):
            fast_exe_dest = arg.split("=", 1)[1].strip() or None
            continue
    if os.environ.get("ZAPRET_FAST_EXE") in {"1", "true", "TRUE", "yes", "YES"}:
        fast_exe = True
    return {"fast_exe": fast_exe, "fast_exe_dest": fast_exe_dest}


def main():
    """Главная функция"""
    try:
        run_without_console()
        
        if not is_admin():
            print("Перезапуск с правами администратора…")
            elevate_as_admin()
            
        cli = _parse_cli_args(sys.argv[1:])
        app = BuildReleaseGUI(cli)
        app.run()
        
    except Exception as e:
        import traceback
        error_msg = f"Критическая ошибка:\n\n{str(e)}\n\n{traceback.format_exc()}"
        
        try:
            messagebox.showerror("Критическая ошибка", error_msg)
        except:
            print(error_msg)
            input("\nНажмите Enter для выхода...")
        
        sys.exit(1)


if __name__ == "__main__":
    main()
