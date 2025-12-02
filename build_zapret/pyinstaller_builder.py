# build_zapret/pyinstaller_builder.py

from __future__ import annotations
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any, Optional


def create_spec_file(channel: str, root_path: Path, log_queue: Optional[Any] = None) -> Path:
    """
    Создает spec файл для PyInstaller с исключением папки build_zapret
    
    Args:
        channel: Канал сборки ('stable' или 'test')
        root_path: Корневая папка проекта
        log_queue: Очередь для логов (опционально)
        
    Returns:
        Path: Путь к созданному spec файлу
    """
    icon_file = 'ZapretDevLogo4.ico' if channel == 'test' else 'Zapret2.ico'
    
    # Ищем файл иконки в разных местах
    icon_path = None
    possible_locations = [
        root_path / icon_file,  # В корне проекта
        root_path / 'ico' / icon_file,  # В папке ico
        root_path.parent / 'zapret' / 'ico' / icon_file,  # В папке сборки
        Path('D:/Privacy/zapret/ico') / icon_file,  # Абсолютный путь к папке сборки
    ]
    
    for location in possible_locations:
        if location.exists():
            icon_path = location
            break
    
    if not icon_path:
        # Если иконка не найдена, создаем spec без иконки
        if log_queue:
            log_queue.put(f"⚠️ Иконка {icon_file} не найдена, сборка без иконки")
        icon_line = ""
    else:
        # Используем абсолютный путь к иконке
        icon_line = f"icon=r'{icon_path}',"
        if log_queue:
            log_queue.put(f"✅ Используется иконка: {icon_path}")
    
    spec_content = f"""# -*- mode: python ; coding: utf-8 -*-
import sys
from PyInstaller.utils.hooks import collect_submodules

# Собираем ВСЕ подмодули ui пакета
ui_hiddenimports = collect_submodules('ui')
log_hiddenimports = collect_submodules('log')
managers_hiddenimports = collect_submodules('managers')
strategy_hiddenimports = collect_submodules('strategy_menu')

a = Analysis(
    ['main.py'],
    pathex=[r'{root_path}'],  # ✅ ВАЖНО: путь к проекту!
    binaries=[],
    datas=[],  # ✅ Python модули включаются через hiddenimports, НЕ через datas
    hiddenimports=ui_hiddenimports + log_hiddenimports + managers_hiddenimports + strategy_hiddenimports + [
        # ============= UI МОДУЛИ (ОБЯЗАТЕЛЬНО!) =============
        'ui',
        'ui.splash_screen',
        'ui.main_window', 
        'ui.theme',
        'ui.theme_subscription_manager',
        'ui.sidebar',
        'ui.custom_titlebar',
        'ui.help_dialog',
        'ui.acrylic',
        'ui.fluent_icons',
        'ui.pages',
        'ui.pages.home_page',
        'ui.pages.control_page',
        'ui.pages.strategies_page',
        'ui.pages.network_page',
        'ui.pages.autostart_page',
        'ui.pages.appearance_page',
        'ui.pages.about_page',
        'ui.pages.logs_page',
        'ui.pages.base_page',
        'ui.pages.premium_page',
        
        # ============= LOG МОДУЛИ =============
        'log',
        'log.log',
        'log.crash_handler',
        'log_tail',
        
        # ============= MANAGERS =============
        'managers',
        'managers.dpi_manager',
        'managers.ui_manager',
        'managers.heavy_init_manager',
        'managers.initialization_manager',
        'managers.process_monitor_manager',
        
        # ============= STRATEGY MENU =============
        'strategy_menu',
        'strategy_menu.selector',
        'strategy_menu.strategies_registry',
        'strategy_menu.strategy_runner',
        'strategy_menu.strategy_lists_separated',
        'strategy_menu.animated_side_panel',
        'strategy_menu.widgets',
        'strategy_menu.command_line_dialog',
        'strategy_menu.constants',
        'strategy_menu.workers',
        'strategy_menu.lazy_tab_loader',
        'strategy_menu.profiler',
        'strategy_menu.strategy_table_widget_favorites',
        
        # ============= CRASH HANDLING =============
        'faulthandler',
        'threading',
        'atexit',
        'traceback',
        
        # Windows API
        'win32com', 
        'win32com.client', 
        'pythoncom',
        'win32api',
        'win32con',
        'win32service',
        'win32serviceutil',
        
        # ✅ ДОБАВЛЕНО: email модуль и его подмодули
        'email',
        'email.mime',
        'email.mime.text',
        'email.mime.multipart',
        'email.mime.base',
        'email.mime.image',
        'email.mime.audio',
        'email.utils',
        'email.header',
        'email.charset',
        'email.encoders',
        'email.message',
        'email.parser',
        'email.generator',
        
        # ✅ ДОБАВЛЕНО: urllib3 и requests
        'urllib3',
        'urllib3.exceptions',
        'urllib3.util',
        'urllib3.util.retry',
        'urllib3.util.timeout',
        'urllib3.connection',
        'urllib3.connectionpool',
        'urllib3.poolmanager',
        'urllib3.response',
        'urllib3.contrib',
        
        'requests',
        'requests.exceptions',
        'requests.adapters',
        'requests.auth',
        'requests.models',
        'requests.structures',
        'requests.utils',
        
        # ✅ ДОБАВЛЕНО: другие зависимости
        'certifi',
        'charset_normalizer',
        'idna',
    ],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    # ✅ ИСПРАВЛЕНО: убран 'email' из excludes!
    excludes=[
        'build_zapret',           # Папка со скриптами сборки
        'build_zapret.pyinstaller_builder',
        'build_zapret.nuitka_builder',
        'build_zapret.github_release',
        'build_zapret.ssh_deploy',
        'build_zapret.telegram_publish',
        'build_zapret.build_release_gui',
        'build_zapret.keyboard_manager',
        'pyinstaller_builder',    # На случай если импортируется напрямую
        'nuitka_builder',
        'github_release',
        'ssh_deploy',
        'telegram_publish',
        'build_release_gui',
        'keyboard_manager',
        'tkinter',                # GUI сборщика не нужен в Zapret
        'tkinter.ttk',
        'turtle',                 # Стандартные ненужные модули
        'test',
        'unittest',
        'pytest',
        'setuptools',
        'pip',
        'distutils',
        # ❌ УДАЛЕНО: 'email' - этот модуль НУЖЕН!
        'http.server',
        'xmlrpc',
        'pydoc',
    ],
    noarchive=False,
)

# ✅ ДОПОЛНИТЕЛЬНАЯ ФИЛЬТРАЦИЯ: удаляем файлы из build_zapret если попали
a.datas = [x for x in a.datas if not x[0].startswith('build_zapret')]
a.binaries = [x for x in a.binaries if not x[0].startswith('build_zapret')]

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='Zapret',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # ✅ ИЗМЕНЕНО С True НА False
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=True,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    uac_admin=True,
    {icon_line}
)"""
    
    spec_path = root_path / "zapret_build.spec"
    spec_path.write_text(spec_content, encoding='utf-8')
    
    if log_queue:
        log_queue.put(f"✅ Spec файл создан: {spec_path}")
        log_queue.put(f"📌 Исключена папка: build_zapret")
        log_queue.put(f"✅ Добавлены модули: email, urllib3, requests")
    
    return spec_path


def run_pyinstaller(channel: str, root_path: Path, run_func: Any, log_queue: Optional[Any] = None) -> None:
    """
    Запускает PyInstaller для сборки
    
    Args:
        channel: Канал сборки ('stable' или 'test')  
        root_path: Корневая папка проекта
        run_func: Функция для запуска команд
        log_queue: Очередь для логов (опционально)
        
    Raises:
        Exception: При ошибке сборки
    """
    spec_path = root_path / "zapret_build.spec"
    work = Path(tempfile.mkdtemp(prefix="pyi_"))
    out = root_path.parent / "zapret"
    
    try:
        if log_queue:
            log_queue.put("🔨 Запуск PyInstaller...")
            log_queue.put(f"   Spec: {spec_path}")
            log_queue.put(f"   Work: {work}")
            log_queue.put(f"   Out: {out}")
            
        # Создаем папку вывода если не существует
        out.mkdir(parents=True, exist_ok=True)
            
        run_func([
            sys.executable, "-m", "PyInstaller",
            "--workpath", str(work),
            "--distpath", str(out),
            "--clean",
            "--noconfirm",
            str(spec_path)
        ])
        
        # Проверяем, что exe создан
        exe_path = out / "Zapret.exe"
        if not exe_path.exists():
            raise FileNotFoundError(f"Исполняемый файл не создан: {exe_path}")
        
        if log_queue:
            log_queue.put(f"✅ PyInstaller завершен успешно")
            log_queue.put(f"📦 Создан: {exe_path}")
            log_queue.put(f"📏 Размер: {exe_path.stat().st_size / 1024 / 1024:.1f} MB")
            
    except Exception as e:
        if log_queue:
            log_queue.put(f"❌ Ошибка PyInstaller: {e}")
        raise
        



def check_pyinstaller_available() -> bool:
    """
    Проверяет доступность PyInstaller
    
    Returns:
        bool: True если PyInstaller установлен
    """
    try:
        import PyInstaller
        return True
    except ImportError:
        return False


def get_pyinstaller_version() -> str:
    """
    Получает версию PyInstaller
    
    Returns:
        str: Версия PyInstaller или сообщение об ошибке
    """
    try:
        import PyInstaller
        return PyInstaller.__version__
    except ImportError:
        return "PyInstaller не установлен"