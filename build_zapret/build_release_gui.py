# build_zapret/build_release_gui.py

from __future__ import annotations
import ctypes, json, os, re, shutil, subprocess, sys, tempfile, textwrap, urllib.request
from pathlib import Path
from datetime import date
from typing import Sequence, Any, Optional
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading
from keyboard_manager import KeyboardManager
from queue import Queue
import time


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
    def run_nuitka(channel: str, version: str, root_path: Path, python_exe: str, 
                   run_func: Any, log_queue: Any = None):
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
    def create_github_release(*args, **kwargs):
        return None
    
    def is_github_enabled():
        return False
    
    def get_github_config_info():
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
        # Заглушки
        def deploy_to_all_servers(*args, **kwargs):
            return False, "SSH модуль недоступен"
        def is_ssh_configured():
            return False
        def get_ssh_config_info():
            return "SSH модуль недоступен (установите: pip install paramiko)"
        return deploy_to_all_servers, is_ssh_configured, get_ssh_config_info, False

# Настраиваем импорт
deploy_to_all_servers, is_ssh_configured, get_ssh_config_info, SSH_AVAILABLE = setup_ssh_imports()


def check_telegram_configured() -> tuple[bool, str]:
    """Проверяет наличие Telegram сессии Pyrogram"""
    
    session_file = Path(__file__).parent / "zapret_uploader.session"
    
    if not session_file.exists():
        return False, "⚠️ Требуется авторизация (telegram_auth_pyrogram.py)"
    
    return True, "✅ Pyrogram сессия активна"

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
    
    # Отправляем в GUI лог
    if hasattr(run, 'log_queue'):
        run.log_queue.put(f"> {shown}")
    
    # Важно: добавляем CREATE_NO_WINDOW для скрытия консольных окон подпроцессов
    startupinfo = None
    if sys.platform == "win32":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
    
    res = subprocess.run(
        cmd, 
        shell=isinstance(cmd, str), 
        cwd=cwd,
        stdout=subprocess.PIPE, 
        stderr=subprocess.PIPE, 
        text=True, 
        encoding='utf-8',
        errors='ignore',
        startupinfo=startupinfo
    )
    
    # Выводим stdout если есть
    if res.stdout and hasattr(run, 'log_queue'):
        for line in res.stdout.strip().split('\n'):
            if line.strip():
                run.log_queue.put(line)
    
    # Выводим stderr если есть ошибки
    if res.stderr and hasattr(run, 'log_queue'):
        for line in res.stderr.strip().split('\n'):
            if line.strip():
                run.log_queue.put(f"❌ {line}")
    
    # Проверяем код возврата
    if check and res.returncode != 0:
        error_msg = f"Command failed with code {res.returncode}"
        
        if res.stderr:
            error_msg += f"\n\nОшибки:\n{res.stderr}"
        if res.stdout:
            error_msg += f"\n\nВывод:\n{res.stdout}"
            
        if hasattr(run, 'log_queue'):
            run.log_queue.put(f"❌ {error_msg}")
            
        if capture:
            raise subprocess.CalledProcessError(res.returncode, cmd, res.stdout, res.stderr)
        else:
            raise RuntimeError(error_msg)
    
    if capture:
        return res.stdout
    else:
        return res.returncode

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
    
    ctypes.windll.shell32.ShellExecuteW(
        None, 
        "runas", 
        pythonw,
        f'"{Path(__file__).resolve()}"',
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
        return tuple(parts[:4])
    except Exception:
        return (0, 0, 0, 0)

def normalize_to_4(ver: str) -> str:
    """Возвращает строку-версию строго из 4 чисел X.X.X.X"""
    return ".".join(map(str, parse_version(ver)))

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
            
        if hasattr(run, 'log_queue'):
            run.log_queue.put(f"✔ Версии обновлены в {versions_file}")
            
    except Exception as e:
        if hasattr(run, 'log_queue'):
            run.log_queue.put(f"⚠️ Ошибка обновления версий: {e}")

def _taskkill(exe: str):
    run(f'taskkill /F /T /IM "{exe}" >nul 2>&1', check=False)

def stop_running_zapret():
    """Аккуратно гасит все Zapret.exe"""
    if hasattr(run, 'log_queue'):
        run.log_queue.put("Ищу запущенный Zapret.exe …")

    try:
        import psutil
        targets = []
        for p in psutil.process_iter(["name"]):
            n = (p.info["name"] or "").lower()
            if n in ("zapret.exe"):
                targets.append(p)
                try:
                    if hasattr(run, 'log_queue'):
                        run.log_queue.put(f"  → terminate PID {p.pid} ({n})")
                    p.terminate()
                except Exception:
                    pass

        if targets:
            psutil.wait_procs(targets, timeout=3)
            for p in targets:
                if p.is_running():
                    try:
                        if hasattr(run, 'log_queue'):
                            run.log_queue.put(f"  → kill PID {p.pid}")
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
    
    if hasattr(run, 'log_queue'):
        run.log_queue.put(f"✓ Скопирован ISS файл: {dst}")
    
    return dst

def write_build_info(channel: str, version: str):
    dst = ROOT / "config" / "build_info.py"
    dst.parent.mkdir(exist_ok=True)
    dst.write_text(f"# AUTOGENERATED\nCHANNEL={channel!r}\nAPP_VERSION={normalize_to_4(version)!r}\n",
                   encoding="utf-8-sig")
    if hasattr(run, 'log_queue'):
        run.log_queue.put("✔ build_info.py updated")

# ════════════════════════════════════════════════════════════════
#  GUI КЛАСС
# ════════════════════════════════════════════════════════════════
class BuildReleaseGUI:
    def __init__(self):
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
        run.log_queue = self.log_queue
        
        # Переменные
        self.channel_var = tk.StringVar(value="test")
        self.version_var = tk.StringVar()
        self.build_method_var = tk.StringVar(value="pyinstaller")
        self.publish_telegram_var = tk.BooleanVar(value=False)
        self.versions_info = {"stable": "—", "test": "—"}
        
        # Создаем интерфейс
        self.create_widgets()
        
        # Загружаем версии
        self.load_versions()
        
        # Запускаем обработчик очереди логов
        self.process_log_queue()

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
        """Запуск авторизации Telegram (Pyrogram)"""
        auth_script = Path(__file__).parent / "telegram_auth_pyrogram.py"
        
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
            subprocess.Popen(
                [python_exe, str(auth_script)],
                creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0
            )
            
            messagebox.showinfo(
                "Авторизация Pyrogram",
                "Открыто окно авторизации Telegram (Pyrogram).\n\n"
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
        elif not is_ssh_configured():
            ttk.Label(ssh_frame, text="⚠️ SSH не настроен (установите: pip install paramiko)", 
                    style='Info.TLabel', foreground='orange').pack(side='left')
        else:
            status_text = get_ssh_config_info()
            ttk.Label(ssh_frame, text=f"✅ {status_text}", 
                    style='Info.TLabel', foreground='green').pack(side='left')

        # Telegram публикация
        telegram_frame = ttk.LabelFrame(main_container, text="Telegram канал публикация", 
                                    padding=15)
        telegram_frame.pack(fill='x', pady=(0, 15))

        telegram_ok, telegram_status = check_telegram_configured()

        status_label = ttk.Label(telegram_frame, text=telegram_status, 
                                style='Info.TLabel',
                                foreground='green' if telegram_ok else 'orange')
        status_label.pack(side='left')

        # Чекбокс публикации
        self.publish_telegram_var = tk.BooleanVar(value=telegram_ok)
        self.publish_telegram_check = ttk.Checkbutton(
            telegram_frame,
            text="📢 Опубликовать в Telegram канал после SSH",
            variable=self.publish_telegram_var,
            state='normal' if telegram_ok else 'disabled'
        )
        self.publish_telegram_check.pack(side='right')

        # Кнопка авторизации
        if not telegram_ok or not (Path(__file__).parent / "zapret_uploader.session").exists():
            auth_button = ttk.Button(
                telegram_frame,
                text="🔑 Авторизация Telegram",
                command=self.run_telegram_auth
            )
            auth_button.pack(side='right', padx=(10, 0))

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
            while True:
                message = self.log_queue.get_nowait()
                self.add_log(message)
        except:
            pass
        finally:
            self.root.after(100, self.process_log_queue)
            
    def start_build(self):
        """Запуск процесса сборки"""
        if not GITHUB_AVAILABLE:
            messagebox.showerror("Ошибка", "GitHub модуль недоступен!")
            return
            
        if not is_github_enabled():
            messagebox.showerror("Ошибка", "GitHub не настроен!\n\n"
                                        "Настройте токен в build_tools/github_release.py")
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
        msg += f"Метод сборки: {build_method.upper()}\n\n"
        msg += "Релиз будет опубликован на:\n"
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
            # Базовые шаги
            steps = [
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
            
            # Общие финальные шаги
            steps.extend([
                (80, "Сборка Inno Setup", lambda: self.run_inno_setup(channel, version)),
                (95, "Создание GitHub release", lambda: self.create_github_release(channel, version, notes)),
            ])
            
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
        produced = Path("H:/Privacy/zapretgui") / f"Zapret2Setup{'_TEST' if channel == 'test' else ''}.exe"
        
        if not produced.exists():
            raise FileNotFoundError(f"{produced} not found")
        
        publish_telegram = self.publish_telegram_var.get()
        
        self.log_queue.put(f"\n📦 SSH деплой версии: {version}")
        self.log_queue.put(f"🔧 Канал: {channel.upper()}")
        
        if publish_telegram:
            self.log_queue.put(f"📢 Telegram: будет опубликовано со 2-го сервера после деплоя")
        
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


    def run_inno_setup(self, channel, version, max_retries=10):
        """Запуск Inno Setup с временным именем"""
        
        project_root = Path("H:/Privacy/zapretgui")
        universal_iss = project_root / "zapret_universal.iss"
        target_iss = project_root / f"zapret_{channel}.iss"
        
        timestamp = int(time.time())
        temp_name = f"Zapret2Setup_{channel}_{timestamp}_tmp"
        final_name = f"Zapret2Setup{'_TEST' if channel == 'test' else ''}"
        
        temp_file = project_root / f"{temp_name}.exe"
        final_file = project_root / f"{final_name}.exe"
        
        self.log_queue.put(f"📦 Сборка во временный файл: {temp_name}.exe")
        
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
        
        is_test = 1 if channel == "test" else 0
        cmd = [
            str(iscc_path),
            f'/DIS_TEST={is_test}',  # ✅ Числовой флаг — надёжнее строк
            f'/DVERSION={version}',
            str(target_iss)
        ]
        
        self.log_queue.put(f"📋 Канал: {channel} → IS_TEST={is_test}")
        self.log_queue.put(f"📋 Ожидаемая папка: {'ZapretTwoDev' if is_test else 'ZapretTwo'}")
        self.log_queue.put(f"📋 Ожидаемая иконка: {'ZapretDevLogo4.ico' if is_test else 'Zapret2.ico'}")
        
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
                
                if final_file.exists():
                    backup = final_file.with_suffix('.old.exe')
                    counter = 1
                    while backup.exists():
                        backup = final_file.with_suffix(f'.old{counter}.exe')
                        counter += 1
                    
                    try:
                        final_file.rename(backup)
                        self.log_queue.put(f"  → Старый файл → {backup.name}")
                    except Exception as e:
                        self.log_queue.put(f"  ⚠️ Не удалось переместить старый: {e}")
                
                temp_file.rename(final_file)
                self.log_queue.put(f"✅ Готово: {final_name}.exe")
                
                # Удаляем старые бэкапы
                def cleanup():
                    time.sleep(5)
                    for old in project_root.glob(f"{final_name}.old*.exe"):
                        try:
                            old.unlink()
                        except:
                            pass
                threading.Thread(target=cleanup, daemon=True).start()
                
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
                    except:
                        pass
                
                if attempt < max_retries:
                    self.log_queue.put(f"⏳ Повтор через 5 сек...")
                    time.sleep(5)
                else:
                    raise

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
  
    def create_github_release(self, channel, version, notes):
        """Создание GitHub release"""
        produced = Path("H:/Privacy/zapretgui") / f"Zapret2Setup{'_TEST' if channel == 'test' else ''}.exe"
        
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


def main():
    """Главная функция"""
    try:
        run_without_console()
        
        if not is_admin():
            print("Перезапуск с правами администратора…")
            elevate_as_admin()
            
        app = BuildReleaseGUI()
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