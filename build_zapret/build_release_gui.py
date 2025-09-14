"""
build_tools/build_release_gui.py  –  GUI версия для сборки и публикации
Поддерживает выбор между PyInstaller и Nuitka
"""

from __future__ import annotations
import ctypes, json, os, re, shutil, subprocess, sys, tempfile, textwrap, urllib.request
from pathlib import Path
from datetime import date
from typing import Sequence, Any
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
    def create_spec_file(channel: str, root_path: Path) -> Path:
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
    
    if capture:
        res = subprocess.run(cmd, shell=isinstance(cmd, str), cwd=cwd,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                           text=True, startupinfo=startupinfo)
        if check and res.returncode:
            raise subprocess.CalledProcessError(res.returncode, cmd, res.stdout, res.stderr)
        return res.stdout
    else:
        res = subprocess.run(cmd, shell=isinstance(cmd, str), cwd=cwd,
                           startupinfo=startupinfo)
        if check and res.returncode:
            raise RuntimeError(f"Command failed with code {res.returncode}")
        return res.returncode


def is_admin() -> bool:
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def elevate_as_admin():
    """Перезапуск с правами администратора"""
    # Используем pythonw.exe вместо python.exe для запуска без консоли
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
    """Парсит версию в кортеж из ровно 4 чисел для правильного сравнения/нормализации."""
    try:
        # Убираем префикс 'v' если есть
        version = (version_string or "").lstrip('v')
        # Разбиваем на части и конвертируем в числа
        parts = [int(x) for x in version.split('.') if x.strip().isdigit()]
        # Дополняем до 4 частей нулями если нужно
        while len(parts) < 4:
            parts.append(0)
        # Берем только первые 4 части
        return tuple(parts[:4])
    except Exception:
        return (0, 0, 0, 0)

def normalize_to_4(ver: str) -> str:
    """Возвращает строку-версию строго из 4 чисел X.X.X.X"""
    return ".".join(map(str, parse_version(ver)))

def suggest_next(ver: str) -> str:
    """Предлагает следующую 4-частную версию (увеличивает последнюю часть на 1)"""
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
    """Атомарная запись JSON: пишем во временный файл, затем заменяем."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)

def fetch_local_versions() -> dict[str, str]:
    """Получает текущие версии из локального JSON файла (строго 4 части)."""
    try:
        versions_file = Path(__file__).parent / "versions.json"
        
        # Если файла нет — создаем с дефолтными значениями (4 части)
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
        
        # Читаем файл
        with open(versions_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Достаем и нормализуем версии
        stable_raw = (data.get("stable", {}) or {}).get("version", "16.2.1.3")
        test_raw   = (data.get("test", {}) or {}).get("version", "16.4.1.9")
        stable = normalize_to_4(stable_raw)
        test   = normalize_to_4(test_raw)

        # Если что-то поменялось — мигрируем файл к 4 частям
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
        # Fallback версии (4 части)
        return {"stable": "16.2.1.3", "test": "16.4.1.9"}

def get_suggested_version(channel: str) -> str:
    """Получает предложенную версию из файла (строго 4 части)"""
    try:
        versions_file = Path(__file__).parent / "versions.json"
        
        if versions_file.exists():
            with open(versions_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            suggested = (data.get("next_suggested", {}) or {}).get(channel)
            if suggested:
                return normalize_to_4(suggested)
        
        # Fallback - вычисляем из текущей версии
        versions = fetch_local_versions()
        current = versions.get(channel, "0.0.0.0")
        return normalize_to_4(suggest_next(current))
        
    except Exception:
        return "1.0.0.0"

def update_versions_file(channel: str, new_version: str):
    """Обновляет файл версий после успешной сборки (строго 4 части)"""
    try:
        from datetime import datetime
        versions_file = Path(__file__).parent / "versions.json"
        
        # Читаем текущие данные
        if versions_file.exists():
            with open(versions_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            data = {"stable": {}, "test": {}, "next_suggested": {}, "metadata": {}}
        
        # Нормализуем версию к 4 частям
        new_version = normalize_to_4(new_version)
        
        # Обновляем версию для канала
        data[channel] = {
            "version": new_version,
            "description": f"{'Стабильная' if channel == 'stable' else 'Тестовая'} версия",
            "release_date": datetime.now().strftime("%Y-%m-%d")
        }
        
        # Обновляем предложения для следующих версий (нормализовано)
        if "next_suggested" not in data or not isinstance(data["next_suggested"], dict):
            data["next_suggested"] = {}
        data["next_suggested"][channel] = normalize_to_4(suggest_next(new_version))
        
        # Обновляем метаданные
        data["metadata"] = {
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "updated_by": "build_system"
        }
        
        # Сохраняем обратно атомарно
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
    
    # Копируем файл
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

def setup_ssh_imports():
    """Настройка импорта SSH модуля"""
    try:
        from ssh_deploy import deploy_to_vps, is_ssh_configured, get_ssh_config_info
        return deploy_to_vps, is_ssh_configured, get_ssh_config_info, True
    except ImportError:
        # Заглушки
        def deploy_to_vps(*args, **kwargs):
            return False, "SSH модуль недоступен"
        def is_ssh_configured():
            return False
        def get_ssh_config_info():
            return "SSH модуль недоступен"
        return deploy_to_vps, is_ssh_configured, get_ssh_config_info, False

# Настраиваем импорт
deploy_to_vps, is_ssh_configured, get_ssh_config_info, SSH_AVAILABLE = setup_ssh_imports()

# ════════════════════════════════════════════════════════════════
#  GUI КЛАСС
# ════════════════════════════════════════════════════════════════
class BuildReleaseGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Zapret Release Builder")
        self.root.geometry("950x1000")
        self.root.minsize(950, 1000)
        
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
        versions_file_path = Path(__file__).parent / "versions.json"
        file_info_label = ttk.Label(self.version_info_frame, 
                                text=f"📄 Файл: {versions_file_path.name}", 
                                style='Info.TLabel', foreground='gray')
        file_info_label.pack(anchor='w')

        # GitHub статус
        github_frame = ttk.LabelFrame(main_container, text="GitHub Release", 
                                     padding=15)
        github_frame.pack(fill='x', pady=(0, 15))
        
        # Проверяем доступность GitHub
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

        ssh_frame = ttk.LabelFrame(main_container, text="SSH деплой на VPS", 
                                padding=15)
        ssh_frame.pack(fill='x', pady=(0, 15))

        # Проверяем доступность SSH
        if not SSH_AVAILABLE:
            ttk.Label(ssh_frame, text="❌ SSH модуль недоступен!", 
                    style='Info.TLabel', foreground='red').pack(side='left')
        elif not is_ssh_configured():
            ttk.Label(ssh_frame, text="⚠️ SSH деплой выключен (SSH_ENABLED = False)", 
                    style='Info.TLabel', foreground='orange').pack(side='left')
        else:
            status_text = get_ssh_config_info()
            ttk.Label(ssh_frame, text=f"✅ {status_text}", 
                    style='Info.TLabel', foreground='green').pack(side='left')

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
        
        # Включаем undo/redo для текстового поля
        self.notes_text = scrolledtext.ScrolledText(notes_frame, height=6, 
                                                   font=('Segoe UI', 10),
                                                   wrap='word',
                                                   undo=True,  # Включаем undo/redo
                                                   maxundo=20)  # Максимум 20 операций отмены
        self.notes_text.pack(fill='both', expand=True)
        
        # Подсказка
        hint_frame = ttk.Frame(notes_frame)
        hint_frame.pack(fill='x', pady=(5, 0))
        
        hint_label = ttk.Label(hint_frame, 
                              text="💡 Можно использовать несколько строк. Поддерживается Markdown.",
                              style='Info.TLabel', foreground='gray')
        hint_label.pack(side='left')
        
        # Подсказка о горячих клавишах
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
        
        # Делаем лог только для чтения
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
        
        # Автоматически предлагаем следующую версию
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
        # Проверка GitHub
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
            
        VERSION_RE = re.compile(r"^\d+\.\d+\.\d+\.\d+$")  # Ровно 4 части
        if not VERSION_RE.fullmatch(version):
            messagebox.showerror("Ошибка", f"Неверный формат версии: {version}\n"
                                        "Используйте формат X.X.X.X (4 цифры)")
            return
            
        notes = self.notes_text.get('1.0', 'end').strip()
        if not notes:
            notes = f"Zapret {version}"
            
        channel = self.channel_var.get()
        build_method = self.build_method_var.get()
        
        # Проверка доступности выбранного метода
        if build_method == "nuitka" and not NUITKA_AVAILABLE:
            messagebox.showerror("Ошибка", "Модуль nuitka_builder недоступен!")
            return
            
        if build_method == "pyinstaller" and not PYINSTALLER_AVAILABLE:
            messagebox.showerror("Ошибка", "Модуль pyinstaller_builder недоступен!")
            return
        
        # Подтверждение
        msg = f"Канал: {channel.upper()}\nВерсия: {version}\n"
        msg += f"Метод сборки: {build_method.upper()}\n\n"
        msg += "Релиз будет опубликован на GitHub.\n\n"
        msg += "Продолжить сборку?"
        
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
                #(20, "Остановка Zapret", stop_running_zapret),
            ]
            
            # Добавляем шаги в зависимости от метода сборки
            if build_method == "nuitka":
                steps.extend([
                    (60, "Сборка Nuitka", lambda: run_nuitka(channel, version, ROOT, PY, run, self.log_queue)),
                ])
            else:  # pyinstaller
                steps.extend([
                    (35, "Создание spec файла", lambda: create_spec_file(channel, ROOT)),
                    (60, "Сборка PyInstaller", lambda: run_pyinstaller(channel, ROOT, run, self.log_queue)),
                ])
            
            # Общие финальные шаги
            steps.extend([
                (80, "Сборка Inno Setup", lambda: self.run_inno_setup(channel, version)),
                (95, "Создание GitHub release", lambda: self.create_github_release(channel, version, notes)),
            ])
            
            # Добавляем SSH деплой если включен
            if SSH_AVAILABLE and is_ssh_configured():
                steps.append((98, "SSH деплой на VPS", lambda: self.deploy_to_ssh(channel)))
                
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

    def run_inno_setup(self, channel, version, max_retries=50):
        """Запуск Inno Setup с параметрами препроцессора и автоматическим перезапуском при ошибках доступа"""
        
        # Определяем пути
        project_root = Path("D:/Privacy/zapretgui")
        output_dir = Path("D:/Privacy/zapret")
        
        # Имя ISS файла в зависимости от канала
        iss_filename = "zapret_test.iss" if channel == "test" else "zapret_stable.iss"
        
        # Путь к универсальному ISS файлу
        universal_iss = project_root / "zapret_universal.iss"
        target_iss = project_root / iss_filename
        
        # Путь к выходному файлу установщика
        output_name = f"ZapretSetup{'_TEST' if channel == 'test' else ''}.exe"
        output_file = project_root / output_name
        
        self.log_queue.put(f"📁 Папка проекта: {project_root}")
        self.log_queue.put(f"📁 Папка сборки: {output_dir}")
        self.log_queue.put(f"📄 ISS файл: {target_iss}")
        self.log_queue.put(f"📦 Выходной файл: {output_file}")
        
        # Проверяем существование универсального ISS
        if not universal_iss.exists():
            raise FileNotFoundError(f"Универсальный ISS не найден: {universal_iss}")
        
        # Копируем универсальный ISS в целевой
        shutil.copy2(universal_iss, target_iss)
        self.log_queue.put(f"✓ Скопирован ISS файл: {target_iss}")
        
        # Проверяем существование Inno Setup
        iscc_path = Path(r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe")
        if not iscc_path.exists():
            iscc_path = Path(r"C:\Program Files\Inno Setup 6\ISCC.exe")
            if not iscc_path.exists():
                raise FileNotFoundError("Inno Setup не найден! Установите Inno Setup 6")
        
        # Команда для запуска
        cmd = [
            str(iscc_path),
            f"/DCHANNEL={channel}",
            f"/DVERSION={version}",
            str(target_iss)
        ]
        
        # Попытки запуска с обработкой ошибок блокировки файла
        for attempt in range(1, max_retries + 1):
            try:
                self.log_queue.put(f"\n🔄 Попытка {attempt}/{max_retries}: Запуск Inno Setup...")
                self.log_queue.put(f"Команда: {' '.join(cmd)}")
                
                # Если это не первая попытка, пытаемся освободить файл
                if attempt > 1 and output_file.exists():
                    self.log_queue.put(f"⚠️ Попытка освободить файл {output_file.name}...")
                    
                    # Метод 1: Попытка удалить файл
                    try:
                        output_file.unlink()
                        self.log_queue.put(f"✓ Файл удален")
                    except Exception as e:
                        self.log_queue.put(f"❌ Не удалось удалить: {e}")
                        
                        # Метод 2: Попытка переименовать файл
                        try:
                            temp_name = output_file.with_suffix('.old.exe')
                            if temp_name.exists():
                                temp_name.unlink()
                            output_file.rename(temp_name)
                            self.log_queue.put(f"✓ Файл переименован в {temp_name.name}")
                        except Exception as e2:
                            self.log_queue.put(f"❌ Не удалось переименовать: {e2}")
                            
                            # Метод 3: Принудительное закрытие процессов
                            self.force_close_file_handles(output_file)
                            
                            # Ждем немного
                            time.sleep(2)
                
                # Запускаем Inno Setup
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    encoding='cp1251',
                    cwd=str(project_root)
                )
                
                # Проверяем на ошибку доступа к файлу
                if result.returncode != 0:
                    error_text = (result.stdout or "") + (result.stderr or "")
                    
                    # Проверяем на типичные ошибки блокировки файла
                    file_locked_errors = [
                        "Процесс не может получить доступ к файлу",
                        "The process cannot access the file",
                        "Access is denied",
                        "Отказано в доступе",
                        "being used by another process",
                        "занят другим процессом"
                    ]
                    
                    is_file_locked = any(err in error_text for err in file_locked_errors)
                    
                    if is_file_locked and attempt < max_retries:
                        self.log_queue.put(f"⚠️ Файл заблокирован другим процессом")
                        self.log_queue.put(f"⏳ Ожидание 5 секунд перед повторной попыткой...")
                        time.sleep(5)
                        continue  # Переходим к следующей попытке
                    
                    # Если это не ошибка блокировки или последняя попытка - выбрасываем исключение
                    error_msg = f"Inno Setup завершился с кодом {result.returncode}"
                    if result.stdout:
                        self.log_queue.put(f"Вывод:\n{result.stdout}")
                        error_msg += f"\n\nВывод:\n{result.stdout}"
                    if result.stderr:
                        self.log_queue.put(f"Ошибки:\n{result.stderr}")
                        error_msg += f"\n\nОшибки:\n{result.stderr}"
                    raise RuntimeError(error_msg)
                
                # Успешное выполнение
                if result.stdout:
                    self.log_queue.put(f"Вывод Inno Setup:\n{result.stdout}")
                
                # Проверяем, что установщик создан
                if output_file.exists():
                    self.log_queue.put(f"✅ Установщик создан: {output_file}")
                    self.log_queue.put(f"📏 Размер: {output_file.stat().st_size / 1024 / 1024:.1f} MB")
                    return  # Успешно завершаем
                else:
                    if attempt < max_retries:
                        self.log_queue.put(f"⚠️ Установщик не найден, повторная попытка...")
                        time.sleep(3)
                        continue
                    else:
                        raise FileNotFoundError(f"Установщик не создан: {output_file}")
                        
            except Exception as e:
                if attempt < max_retries:
                    self.log_queue.put(f"❌ Ошибка на попытке {attempt}: {str(e)}")
                    self.log_queue.put(f"⏳ Повторная попытка через 5 секунд...")
                    time.sleep(5)
                else:
                    self.log_queue.put(f"❌ Все {max_retries} попытки исчерпаны")
                    raise
        
    def force_close_file_handles(self, file_path):
        """Принудительное закрытие процессов, использующих файл"""
        try:
            import psutil
            
            self.log_queue.put(f"🔍 Поиск процессов, использующих {file_path.name}...")
            
            # Получаем список всех процессов
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    # Проверяем открытые файлы процесса
                    for item in proc.open_files():
                        if str(file_path) in str(item.path):
                            self.log_queue.put(f"  → Найден процесс {proc.info['name']} (PID: {proc.info['pid']})")
                            try:
                                proc.terminate()
                                self.log_queue.put(f"  → Процесс завершен")
                            except:
                                try:
                                    proc.kill()
                                    self.log_queue.put(f"  → Процесс принудительно завершен")
                                except:
                                    pass
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
                    
        except ImportError:
            # Если psutil недоступен, используем taskkill
            self.log_queue.put(f"⚠️ psutil недоступен, использую taskkill...")
            
            # Пытаемся закрыть типичные процессы, которые могут держать файл
            possible_processes = [
                "explorer.exe",  # Проводник Windows
                "ZapretSetup_TEST.exe",  # Сам установщик
                "ZapretSetup.exe",
                "Zapret.exe"
            ]
            
            for proc_name in possible_processes:
                try:
                    result = subprocess.run(
                        f'taskkill /F /IM "{proc_name}"',
                        shell=True,
                        capture_output=True,
                        text=True
                    )
                    if result.returncode == 0:
                        self.log_queue.put(f"  → Завершен процесс {proc_name}")
                except:
                    pass
            
            # Перезапускаем проводник если закрыли его
            if "explorer.exe" in possible_processes:
                try:
                    subprocess.Popen("explorer.exe", shell=True)
                    self.log_queue.put(f"  → Проводник перезапущен")
                except:
                    pass
        
        except Exception as e:
            self.log_queue.put(f"⚠️ Ошибка при закрытии процессов: {e}")

    def deploy_to_ssh(self, channel):
        """Деплой на VPS через SSH"""
        # ✅ Абсолютный путь к установщику
        produced = Path("D:/Privacy/zapretgui") / f"ZapretSetup{'_TEST' if channel == 'test' else ''}.exe"
        
        if not produced.exists():
            raise FileNotFoundError(f"{produced} not found")
        
        version = self.version_var.get().strip()
        notes = self.notes_text.get('1.0', 'end').strip()
        
        success, message = deploy_to_vps(
            file_path=produced,
            channel=channel,
            version=version, 
            notes=notes,
            log_queue=self.log_queue
        )
        
        if not success:
            raise Exception(f"SSH деплой не удался: {message}")
            
        self.log_queue.put(f"🚀 {message}")
  
    def create_github_release(self, channel, version, notes):
        """Создание GitHub release"""
        # ✅ Абсолютный путь к установщику
        produced = Path("D:/Privacy/zapretgui") / f"ZapretSetup{'_TEST' if channel == 'test' else ''}.exe"
        
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
        
        # Обновляем файл версий
        channel = self.channel_var.get()
        version = self.version_var.get().strip()
        update_versions_file(channel, version)
        
        messagebox.showinfo("Успех", "Сборка и публикация завершены успешно!")
        
        # Перезагружаем версии из обновленного файла
        self.load_versions()
        
    def build_error(self, error_msg):
        """Вызывается при ошибке сборки"""
        self.build_button.config(state='normal', text="🔨 Собрать и опубликовать")
        self.cancel_button.config(state='normal')
        self.progress_var.set(0)
        
        messagebox.showerror("Ошибка сборки", f"Произошла ошибка:\n\n{error_msg}")
        
    def run(self):
        """Запуск GUI"""
        # Центрируем окно
        self.center_window()
        
        # Запускаем главный цикл
        self.root.mainloop()
        
    def center_window(self):
        """Центрирование окна на экране"""
        self.root.update_idletasks()
        
        # Получаем размеры окна
        window_width = self.root.winfo_width()
        window_height = self.root.winfo_height()
        
        # Получаем размеры экрана
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # Вычисляем координаты
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        
        # Устанавливаем позицию
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")


def run_without_console():
    """Перезапускает скрипт через pythonw.exe если запущен через python.exe"""
    if sys.executable.endswith('python.exe'):
        pythonw = sys.executable.replace('python.exe', 'pythonw.exe')
        if Path(pythonw).exists():
            subprocess.Popen([pythonw] + sys.argv, 
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            sys.exit(0)


def main():
    """Главная функция"""
    try:
        # Перезапускаем без консоли если нужно
        run_without_console()
        
        # Проверяем права администратора
        if not is_admin():
            print("Перезапуск с правами администратора…")
            elevate_as_admin()
            
        # Создаем и запускаем GUI
        app = BuildReleaseGUI()
        app.run()
        
    except Exception as e:
        # Если GUI не удалось запустить, показываем ошибку
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