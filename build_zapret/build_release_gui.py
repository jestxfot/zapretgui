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


def parse_version(version_string: str) -> tuple:
    """Парсит версию в кортеж чисел для правильного сравнения"""
    try:
        # Убираем префикс 'v' если есть
        version = version_string.lstrip('v')
        # Разбиваем на части и конвертируем в числа
        parts = [int(x) for x in version.split('.')]
        # Дополняем до 5 частей нулями если нужно
        while len(parts) < 5:
            parts.append(0)
        return tuple(parts)
    except (ValueError, AttributeError):
        return (0, 0, 0, 0, 0)

def fetch_local_versions() -> dict[str, str]:
    """Получает текущие версии из локального JSON файла"""
    try:
        # Путь к файлу версий
        versions_file = Path(__file__).parent / "versions.json"
        
        if not versions_file.exists():
            # Создаем файл с дефолтными версиями если его нет
            default_versions = {
                "stable": {
                    "version": "16.2.1.3.0",
                    "description": "Стабильная версия",
                    "release_date": "2025-07-15"
                },
                "test": {
                    "version": "16.4.1.9.0", 
                    "description": "Тестовая версия",
                    "release_date": "2025-07-28"
                },
                "next_suggested": {
                    "stable": "16.2.1.3.1",
                    "test": "16.4.1.9.1"
                },
                "metadata": {
                    "last_updated": "2025-07-30",
                    "updated_by": "build_system"
                }
            }
            
            with open(versions_file, 'w', encoding='utf-8') as f:
                json.dump(default_versions, f, indent=2, ensure_ascii=False)
        
        # Читаем файл
        with open(versions_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        versions = {
            "stable": data.get("stable", {}).get("version", "16.2.1.3.0"),
            "test": data.get("test", {}).get("version", "16.4.1.9.0")
        }
        
        return versions
        
    except Exception as e:
        # Fallback версии
        return {"stable": "16.2.1.3.0", "test": "16.4.1.9.0"}

def update_versions_file(channel: str, new_version: str):
    """Обновляет файл версий после успешной сборки"""
    try:
        from datetime import datetime
        
        versions_file = Path(__file__).parent / "versions.json"
        
        # Читаем текущие данные
        if versions_file.exists():
            with open(versions_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            data = {"stable": {}, "test": {}, "next_suggested": {}, "metadata": {}}
        
        # Обновляем версию для канала
        data[channel] = {
            "version": new_version,
            "description": f"{'Стабильная' if channel == 'stable' else 'Тестовая'} версия",
            "release_date": datetime.now().strftime("%Y-%m-%d")
        }
        
        # Обновляем предложения для следующих версий
        if "next_suggested" not in data:
            data["next_suggested"] = {}
            
        data["next_suggested"][channel] = suggest_next(new_version)
        
        # Обновляем метаданные
        data["metadata"] = {
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "updated_by": "build_system"
        }
        
        # Сохраняем обратно
        with open(versions_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            
        if hasattr(run, 'log_queue'):
            run.log_queue.put(f"✔ Версии обновлены в {versions_file}")
            
    except Exception as e:
        if hasattr(run, 'log_queue'):
            run.log_queue.put(f"⚠️ Ошибка обновления версий: {e}")

def suggest_next(ver: str) -> str:
    """Предлагает следующую версию"""
    try:
        # Парсим текущую версию
        current_parts = parse_version(ver)
        # Увеличиваем последнюю часть
        new_parts = list(current_parts[:5])  # Берем только первые 5 частей
        new_parts[-1] += 1
        
        return ".".join(map(str, new_parts))
    except:
        # Fallback к старому методу
        nums = [int(x) for x in (ver.split(".") + ["0"] * 5)[:5]]
        nums[-1] += 1
        return ".".join(map(str, nums))

def get_suggested_version(channel: str) -> str:
    """Получает предложенную версию из файла"""
    try:
        versions_file = Path(__file__).parent / "versions.json"
        
        if versions_file.exists():
            with open(versions_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            suggested = data.get("next_suggested", {}).get(channel)
            if suggested:
                return suggested
        
        # Fallback - вычисляем из текущей версии
        versions = fetch_local_versions()
        current = versions.get(channel, "0.0.0.0.0")
        return suggest_next(current)
        
    except Exception:
        return "1.0.0.0.0"

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

def _ensure_uninstall_delete(text: str, path: str) -> str:
    """Вставляет/заменяет блок [UninstallDelete]"""
    block = f"[UninstallDelete]\nType: filesandordirs; Name: \"{path}\""
    pat   = r"(?is)\[UninstallDelete\].*?(?=\n\[|\Z)"
    if re.search(pat, text):
        text = re.sub(pat, lambda _: block, text)
    else:
        text += "\n" + block
    return text

def prepare_iss(channel: str, version: str) -> Path:
    """Создаёт zapret_<channel>.iss с нужными полями."""
    src = ROOT / "zapret.iss"
    if not src.exists():
        raise FileNotFoundError("zapret.iss not found")

    txt = src.read_text(encoding="utf-8-sig")

    if not version.strip():
        import re
        m = re.search(r"^AppVersion\s*=\s*([0-9\.]+)", txt, re.MULTILINE)
        current = m.group(1) if m else "0.0.0.0.0"
        version = suggest_next(current)

    txt = _sub("AppVersion", version, txt)

    base_guid = "5C71C1DC-7627-4E57-9B1A-6B5D1F3A57F0"

    if channel == "test":
        txt = _sub("AppName",            "Zapret Dev",           txt)
        txt = _sub("OutputBaseFilename", "ZapretSetup_TEST",     txt)
        txt = _sub("AppId",              f"{{{{{base_guid}-TEST}}}}", txt)
        txt = _sub("DefaultGroupName",   "Zapret Dev",           txt)
        txt = txt.replace(r"{commonappdata}\Zapret",
                          r"{commonappdata}\ZapretDev")
        txt = _ensure_uninstall_delete(txt,
                          r"{commonappdata}\ZapretDev")
        txt = _sub("SetupIconFile",      "ZapretDevLogo3.ico",    txt)
    else:
        txt = _sub("AppName",            "Zapret",               txt)
        txt = _sub("OutputBaseFilename", "ZapretSetup",          txt)
        txt = _sub("AppId",              f"{{{{{base_guid}}}}}", txt)
        txt = _sub("DefaultGroupName",   "Zapret",               txt)
        txt = _ensure_uninstall_delete(txt,
                          r"{commonappdata}\Zapret")
        txt = _sub("SetupIconFile",      "Zapret1.ico",           txt)

    outdir_line = f'OutputDir="{ROOT}"'
    txt = _sub("OutputDir", outdir_line.split("=", 1)[1].lstrip(), txt)

    patched = ROOT / f"zapret_{channel}.iss"
    patched.write_text(txt, encoding="utf-8-sig")
    return patched

def write_build_info(channel: str, version: str):
    dst = ROOT / "config" / "build_info.py"
    dst.parent.mkdir(exist_ok=True)
    dst.write_text(f"# AUTOGENERATED\nCHANNEL={channel!r}\nAPP_VERSION={version!r}\n",
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
            self.versions_info = {"stable": "16.2.1.3.0", "test": "16.4.1.9.0"}
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
        version = self.version_var.get().strip()
        if not version:
            messagebox.showerror("Ошибка", "Укажите версию!")
            return
            
        VERSION_RE = re.compile(r"^\d+\.\d+\.\d+\.\d+(?:\.\d+)?$")
        if not VERSION_RE.fullmatch(version):
            messagebox.showerror("Ошибка", f"Неверный формат версии: {version}\n"
                                          "Используйте формат X.X.X.X.X")
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
                (10, "Обновление build_info.py", lambda: write_build_info(channel, version)),
                (20, "Остановка Zapret", stop_running_zapret),
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

    def deploy_to_ssh(self, channel):
        """Деплой на VPS через SSH"""
        produced = ROOT / f"ZapretSetup{'_TEST' if channel == 'test' else ''}.exe"
        if not produced.exists():
            raise FileNotFoundError(f"{produced} not found")
        
        # Получаем версию и release notes
        version = self.version_var.get().strip()
        notes = self.notes_text.get('1.0', 'end').strip()
        
        # Выполняем деплой с передачей всех параметров
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
                
    def run_inno_setup(self, channel, version):
        """Запуск Inno Setup"""
        iss_file = prepare_iss(channel, version)
        run([INNO_ISCC, str(iss_file)])
        
    def create_github_release(self, channel, version, notes):
        """Создание GitHub release"""
        produced = ROOT / f"ZapretSetup{'_TEST' if channel == 'test' else ''}.exe"
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
                           creationflags=subprocess.CREATE_NO_WINDOW)
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