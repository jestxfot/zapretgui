# build_zapret/pyinstaller_builder.py

from __future__ import annotations
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any, Optional


def cleanup_all_cache(root_path: Path, log_queue: Optional[Any] = None) -> int:
    """
    Полная очистка всего кэша перед сборкой:
    - __pycache__ во всём проекте
    - .pyc файлы
    - build/ папка PyInstaller
    - *.spec.bak файлы

    Args:
        root_path: Корневая папка проекта
        log_queue: Очередь для логов

    Returns:
        int: Количество удалённых элементов
    """
    cleaned = 0

    if log_queue:
        log_queue.put("🧹 Очистка всего кэша проекта...")

    # 1. Удаляем все __pycache__ папки
    for cache_dir in root_path.rglob("__pycache__"):
        if cache_dir.is_dir():
            try:
                shutil.rmtree(cache_dir, ignore_errors=True)
                cleaned += 1
            except Exception:
                pass

    if log_queue:
        log_queue.put(f"   ✓ Удалено __pycache__ папок: {cleaned}")

    # 2. Удаляем .pyc файлы вне __pycache__ (на всякий случай)
    pyc_count = 0
    for pyc_file in root_path.rglob("*.pyc"):
        try:
            pyc_file.unlink(missing_ok=True)
            pyc_count += 1
        except Exception:
            pass

    if pyc_count and log_queue:
        log_queue.put(f"   ✓ Удалено .pyc файлов: {pyc_count}")
    cleaned += pyc_count

    # 3. Удаляем build/ папку PyInstaller если есть
    build_dir = root_path / "build"
    if build_dir.exists():
        try:
            shutil.rmtree(build_dir, ignore_errors=True)
            cleaned += 1
            if log_queue:
                log_queue.put(f"   ✓ Удалена папка build/")
        except Exception:
            pass

    # 4. Удаляем __pycache__ в build_zapret/ отдельно
    build_zapret_cache = Path(__file__).parent / "__pycache__"
    if build_zapret_cache.exists():
        try:
            shutil.rmtree(build_zapret_cache, ignore_errors=True)
            cleaned += 1
            if log_queue:
                log_queue.put(f"   ✓ Удалён кэш build_zapret/")
        except Exception:
            pass

    # 5. Удаляем старые .spec.bak файлы
    for bak_file in root_path.glob("*.spec.bak"):
        try:
            bak_file.unlink(missing_ok=True)
            cleaned += 1
        except Exception:
            pass

    if log_queue:
        log_queue.put(f"🧹 Очистка завершена: {cleaned} элементов удалено")

    return cleaned


def embed_certificate_in_installer(root_path: Path) -> None:
    """
    Встраивает сертификат в certificate_installer.py в формате base64.
    
    Args:
        root_path: Корневая папка проекта
    """
    import base64
    
    try:
        cert_file = Path(__file__).parent / "zapret_certificate.cer"
        installer_file = root_path / "startup" / "certificate_installer.py"
        
        if not cert_file.exists() or not installer_file.exists():
            return
        
        # Читаем сертификат
        cert_data = cert_file.read_bytes()
        cert_base64 = base64.b64encode(cert_data).decode('ascii')
        
        # Читаем installer файл
        installer_content = installer_file.read_text(encoding='utf-8')
        
        # Заменяем встроенный сертификат
        import re
        new_content = re.sub(
            r'EMBEDDED_CERTIFICATE = ""',
            f'EMBEDDED_CERTIFICATE = "{cert_base64}"',
            installer_content
        )
        
        # Сохраняем
        installer_file.write_text(new_content, encoding='utf-8')
        
    except Exception:
        pass  # Не критично


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
    
    # ✅ Встраиваем сертификат перед сборкой
    embed_certificate_in_installer(root_path)
    
    icon_file = 'ZapretDevLogo4.ico' if channel == 'test' else 'Zapret2.ico'
    
    # Ищем файл иконки в разных местах
    icon_path = None
    possible_locations = [
        root_path / icon_file,  # В корне проекта
        root_path / 'ico' / icon_file,  # В папке ico
        root_path.parent / 'zapret' / 'ico' / icon_file,  # В папке сборки
        Path('H:/Privacy/zapret/ico') / icon_file,  # Абсолютный путь к папке сборки
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
    
    # ✅ Datas для PyInstaller: только встраиваемый сертификат (если есть)
    datas_items: list[tuple[str, str]] = []

    cert_file = Path(__file__).parent / "zapret_certificate.cer"
    if cert_file.exists():
        datas_items.append((str(cert_file), "."))
        if log_queue:
            log_queue.put(f"✅ Сертификат будет встроен: {cert_file}")

    # direct_zapret1 strategies must stay external-only:
    # %APPDATA%\zapret\direct_zapret1\*.txt
    # Do not embed them into PyInstaller _internal.

    if datas_items:
        datas_line = "datas=[" + ", ".join([f"(r'{src}', r'{dst}')" for src, dst in datas_items]) + "]"
    else:
        datas_line = "datas=[]"
    
    spec_content = f"""# -*- mode: python ; coding: utf-8 -*-
import sys
import os
import PyQt6 as _pyqt6

# Принудительно указываем PyQt6 для qtpy/qtawesome (иначе они выбирают PyQt5 если он установлен)
os.environ['QT_API'] = 'PyQt6'

# НЕ используем collect_submodules() для пакетов, которые импортируют PyQt6/qfluentwidgets!
# collect_submodules() запускает дочерний процесс Python, который импортирует все модули пакета.
# Модули ui, strategy_menu, managers, log импортируют PyQt6 на уровне модуля,
# а PyQt6 требует QApplication — в подпроцессе PyInstaller его нет -> Access Violation (0xC0000005).
# Вместо этого все модули перечислены вручную в hiddenimports ниже.

# qframelesswindow (зависимость qfluentwidgets) импортирует PyQt6.QtXml на уровне модуля.
# hook-PyQt6.QtXml.py возвращает 0 binaries — Qt6Xml.dll не попадает автоматически.
# Явно добавляем оба файла чтобы гарантировать попадание в сборку.
_pyqt6_dir = os.path.dirname(_pyqt6.__file__)
_pyqt6_qt6_bin = os.path.join(_pyqt6_dir, 'Qt6', 'bin')

a = Analysis(
    ['main.py'],
    pathex=[r'{root_path}'],  # ВАЖНО: путь к проекту!
    binaries=[
        (os.path.join(_pyqt6_dir, 'QtXml.pyd'), 'PyQt6'),
        (os.path.join(_pyqt6_qt6_bin, 'Qt6Xml.dll'), 'PyQt6/Qt6/bin'),
    ],
    {datas_line},  # Включаем data файлы
    hiddenimports=[
        # ============= UI МОДУЛИ (ОБЯЗАТЕЛЬНО!) =============
        'ui',
        'ui.main_window',
        'ui.theme',
        'ui.theme_semantic',
        'ui.theme_subscription_manager',
        'ui.compat_widgets',
        'ui.close_dialog',
        'ui.fluent_icons',
        'ui.fluent_app_window',
        'ui.page_names',
        'ui.zapret2_strategy_marks',
        # ui.widgets
        'ui.widgets',
        'ui.widgets.strategies_tooltip',
        'ui.widgets.line_edit_icons',
        'ui.widgets.strategy_search_bar',
        'ui.widgets.collapsible_group',
        'ui.widgets.direct_zapret2_strategies_tree',
        'ui.widgets.filter_chip_button',
        'ui.widgets.notification_banner',
        'ui.widgets.strategy_radio_item',
        'ui.widgets.unified_strategies_list',
        'ui.widgets.win11_spinner',
        # ui.pages
        'ui.pages',
        'ui.pages.base_page',
        'ui.pages.home_page',
        'ui.pages.control_page',
        'ui.pages.strategies_page_base',
        'ui.pages.zapret2_orchestra_strategies_page',
        'ui.pages.network_page',
        'ui.pages.autostart_page',
        'ui.pages.appearance_page',
        'ui.pages.about_page',
        'ui.pages.logs_page',
        'ui.pages.premium_page',
        'ui.pages.help_page',
        # ui.pages.zapret1
        'ui.pages.zapret1',
        'ui.pages.zapret1.direct_control_page',
        'ui.pages.zapret1.direct_zapret1_page',
        'ui.pages.zapret1.user_presets_page',
        'ui.pages.zapret1.strategy_detail_page_v1',
        'ui.pages.blockcheck_page',
        'ui.pages.dpi_settings_page',
        'ui.pages.blobs_page',
        'ui.pages.connection_page',
        'ui.pages.custom_domains_page',
        'ui.pages.custom_ipset_page',
        'ui.pages.dns_check_page',
        'ui.pages.hostlist_page',
        'ui.pages.hosts_page',
        'ui.pages.ipset_page',
        'ui.pages.netrogat_page',
        'ui.pages.orchestra_page',
        'ui.pages.orchestra',
        'ui.pages.orchestra.orchestra_settings_page',
        'ui.pages.orchestra.blocked_page',
        'ui.pages.orchestra.locked_page',
        'ui.pages.orchestra.whitelist_page',
        'ui.pages.orchestra.ratings_page',
        'ui.pages.diagnostics_tab_page',
        'ui.pages.preset_config_page',
        'ui.pages.servers_page',
        'ui.pages.support_page',
        # ui.pages.zapret2
        'ui.pages.zapret2',
        'ui.pages.zapret2.strategy_detail_page',
        'ui.pages.zapret2.direct_control_page',
        'ui.pages.zapret2.direct_zapret2_page',
        'ui.pages.zapret2.user_presets_page',

        # ============= PRESET ZAPRET1 =============
        'preset_zapret1',
        'preset_zapret1.preset_manager',
        'preset_zapret1.preset_model',
        'preset_zapret1.preset_storage',
        'preset_zapret1.preset_store',
        'preset_zapret1.txt_preset_parser',
        'preset_zapret1.strategy_inference',
        'preset_zapret1.preset_defaults',

        # ============= ZAPRET1 LAUNCHER =============
        'zapret1_launcher',
        'zapret1_launcher.strategy_runner',

        # ============= LOG МОДУЛИ =============
        'log',
        'log.log',
        'log.crash_handler',
        'log_tail',

        # ============= MANAGERS =============
        'managers',
        'managers.dpi_manager',
        'managers.ui_manager',
        'managers.initialization_manager',
        'managers.process_monitor_manager',
        'managers.system_paths',
        'managers.subscription_manager',

        # ============= STRATEGY MENU =============
        'strategy_menu',
        'strategy_menu.strategies_registry',
        'strategy_menu.widgets',
        'strategy_menu.widgets_favorites',
        'strategy_menu.workers',
        'strategy_menu.profiler',
        'strategy_menu.table_builder',
        'strategy_menu.categories_tab_panel',
        'strategy_menu.args_preview_dialog',
        'strategy_menu.dialogs',
        'strategy_menu.hover_tooltip',
        'strategy_menu.preset_editor_dialog',
        'strategy_menu.filter_engine',
        'strategy_menu.search_query',
        'strategy_menu.strategy_info',
        'strategy_menu.strategy_matching',
        'strategy_menu.user_categories_store',
        'strategy_menu.strategy_loader',
        'strategy_menu.command_builder',
        
        # ============= CRASH HANDLING =============
        'faulthandler',
        'threading',
        'atexit',
        'traceback',
        
        # ============= STARTUP MODULES =============
        'startup',
        'startup.admin_check',
        'startup.single_instance',
        'startup.kaspersky',
        'startup.ipc_manager',
        'startup.check_start',
        'startup.bfe_util',
        'startup.admin_check_debug',
        'startup.check_cache',
        'startup.certificate_installer',  # Автоустановка сертификата
        
        # PyQt6 extras needed by qfluentwidgets
        'PyQt6.QtXml',

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
        # ❌ УДАЛЕНО: 'email' - этот модуль НУЖЕН!
        # ✅ ИСКЛЮЧАЕМ: лишние Qt биндинги, чтобы PyInstaller не ругался
        'PySide6',
        'shiboken6',
        'PySide2',
        'shiboken2',
        # PyQt5 — конфликтует с PyQt6 при сборке PyInstaller
        'PyQt5',
        'PyQt5.QtCore',
        'PyQt5.QtGui',
        'PyQt5.QtWidgets',
        'PyQt5.QtNetwork',
        'PyQt5.QtSvg',
        'PyQt5.QtXml',
        'PyQt5.sip',
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

# ✅ ИЗМЕНЕНО: Переход с --onefile на --onedir (папка с файлами)
# Это решает проблему "Failed to start embedded python interpreter!"
# и предотвращает блокировку антивирусами
exe = EXE(
    pyz,
    a.scripts,
    [],  # ✅ УБРАЛИ a.binaries и a.datas отсюда
    exclude_binaries=True,  # ✅ ВАЖНО: binaries будут в COLLECT
    name='Zapret',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
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
)

# ✅ ДОБАВЛЕНО: COLLECT создает папку со всеми файлами
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='Zapret',
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
    exe_path = None  # Инициализируем до try блока

    # ✅ ОЧИСТКА ВСЕГО КЭША ПЕРЕД СБОРКОЙ
    #cleanup_all_cache(root_path, log_queue)

    try:
        if log_queue:
            log_queue.put("🔨 Запуск PyInstaller...")
            log_queue.put(f"   Spec: {spec_path}")
            log_queue.put(f"   Work: {work}")
            log_queue.put(f"   Out: {out}")
            
        # Создаем папку вывода если не существует
        out.mkdir(parents=True, exist_ok=True)

        # ✅ Очищаем целевую папку Zapret/ перед сборкой (как в Nuitka)
        # Это гарантирует что старые файлы не останутся в сборке
        """
        target_zapret_dir = out / "Zapret"
        if target_zapret_dir.exists():
            if log_queue:
                log_queue.put(f"🧹 Очистка целевой папки: {target_zapret_dir}")
            shutil.rmtree(target_zapret_dir, ignore_errors=True)
        """
        
        run_func([
            sys.executable, "-m", "PyInstaller",
            "--workpath", str(work),
            "--distpath", str(out),
            "--clean",
            "--noconfirm",
            str(spec_path)
        ])

        # ✅ ИЗМЕНЕНО: В режиме --onedir exe находится в подпапке
        exe_path = out / "Zapret" / "Zapret.exe"
        if not exe_path.exists():
            raise FileNotFoundError(f"Исполняемый файл не создан: {exe_path}")
        
        if log_queue:
            log_queue.put(f"✅ PyInstaller завершен успешно")
            log_queue.put(f"📦 Создан: {exe_path}")
            # ✅ ИЗМЕНЕНО: Подсчитываем размер всей папки в режиме --onedir
            total_size = sum(f.stat().st_size for f in exe_path.parent.rglob('*') if f.is_file())
            log_queue.put(f"📏 Размер папки: {total_size / 1024 / 1024:.1f} MB")
            
    except Exception as e:
        if log_queue:
            log_queue.put(f"❌ Ошибка PyInstaller: {e}")
        raise
    
    finally:
        # Очищаем временную рабочую папку
        try:
            if work.exists():
                shutil.rmtree(work, ignore_errors=True)
                if log_queue:
                    log_queue.put(f"🧹 Удалена рабочая папка: {work}")
        except Exception:
            pass

        # ✅ Подписываем exe файл если есть сертификат и сборка прошла успешно
        if exe_path is not None and exe_path.exists():
            sign_exe_if_available(exe_path, log_queue)


def cleanup_pyinstaller_temp(log_queue: Optional[Any] = None, max_age_hours: int = 1) -> int:
    """
    Удаляет старые временные папки PyInstaller (_MEI*) из TEMP.
    
    Args:
        log_queue: Очередь для логов (опционально)
        max_age_hours: Максимальный возраст папок в часах (по умолчанию 1 час)
        
    Returns:
        int: Количество удалённых папок
    """
    import os
    import time
    
    try:
        temp_dir = tempfile.gettempdir()
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        cleaned_count = 0
        cleaned_size_mb = 0
        
        # ✅ Получаем путь к папке ТЕКУЩЕГО процесса (если сборщик запущен через PyInstaller)
        current_mei_folder = getattr(sys, '_MEIPASS', None)
        
        # Находим все папки _MEI*
        for entry in os.scandir(temp_dir):
            if entry.is_dir() and entry.name.startswith('_MEI'):
                try:
                    # ✅ НЕ УДАЛЯЕМ папку текущего процесса!
                    if current_mei_folder:
                        try:
                            if os.path.samefile(entry.path, current_mei_folder):
                                continue
                        except:
                            pass
                    
                    # Проверяем возраст папки
                    folder_age = current_time - entry.stat().st_mtime
                    
                    if folder_age > max_age_seconds:
                        # Считаем размер перед удалением
                        folder_size = 0
                        try:
                            for root, dirs, files in os.walk(entry.path):
                                for f in files:
                                    try:
                                        folder_size += os.path.getsize(os.path.join(root, f))
                                    except:
                                        pass
                        except:
                            pass
                        
                        # Удаляем папку
                        shutil.rmtree(entry.path, ignore_errors=True)
                        
                        if not os.path.exists(entry.path):
                            cleaned_count += 1
                            cleaned_size_mb += folder_size / (1024 * 1024)
                            
                except (PermissionError, OSError):
                    # Папка занята другим процессом - пропускаем
                    pass
                except Exception:
                    pass
        
        if cleaned_count > 0 and log_queue:
            log_queue.put(f"🧹 Очищено {cleaned_count} старых _MEI* папок ({cleaned_size_mb:.1f} MB)")
            
        return cleaned_count
        
    except Exception as e:
        if log_queue:
            log_queue.put(f"⚠️ Ошибка очистки temp папок: {e}")
        return 0


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


def sign_exe_if_available(exe_path: Path, log_queue: Optional[Any] = None) -> bool:
    """
    Подписывает exe файл цифровой подписью если доступен сертификат.
    
    Args:
        exe_path: Путь к exe файлу
        log_queue: Очередь для логов
        
    Returns:
        bool: True если подпись выполнена успешно
    """
    import subprocess
    import glob
    
    try:
        # Ищем signtool.exe (Windows SDK)
        signtool_patterns = [
            r"C:\Program Files (x86)\Windows Kits\10\bin\*\x64\signtool.exe",
            r"C:\Program Files (x86)\Windows Kits\10\bin\x64\signtool.exe",
            r"C:\Program Files\Windows Kits\10\bin\*\x64\signtool.exe",
        ]
        
        signtool = None
        for pattern in signtool_patterns:
            matches = glob.glob(pattern)
            if matches:
                # Берем самую новую версию
                signtool = sorted(matches, reverse=True)[0]
                break
        
        if not signtool:
            if log_queue:
                log_queue.put("⚠️ signtool.exe не найден (Windows SDK не установлен)")
                log_queue.put("   Скачайте: https://developer.microsoft.com/windows/downloads/windows-sdk/")
            return False
        
        # ✅ Загружаем thumbprint из конфига (если есть)
        cert_thumbprint = None
        try:
            config_file = Path(__file__).parent / "certificate_config.py"
            if config_file.exists():
                import importlib.util
                spec = importlib.util.spec_from_file_location("cert_config", config_file)
                cert_config = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(cert_config)
                cert_thumbprint = cert_config.CERTIFICATE_THUMBPRINT
        except Exception:
            pass
        
        if not cert_thumbprint:
            if log_queue:
                log_queue.put("ℹ️ Сертификат не настроен")
                log_queue.put("   Создайте: python build_zapret/create_certificate.py")
            return False
        
        if log_queue:
            log_queue.put(f"🔐 Подпись exe файла...")
            log_queue.put(f"   Сертификат: {cert_thumbprint[:16]}...")
        
        # Подписываем файл
        cmd = [
            signtool, "sign",
            "/sha1", cert_thumbprint,
            "/fd", "sha256",
            "/tr", "http://timestamp.digicert.com",
            "/td", "sha256",
            "/v",
            str(exe_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            if log_queue:
                log_queue.put(f"✅ Файл успешно подписан цифровой подписью")
            return True
        else:
            if log_queue:
                log_queue.put(f"⚠️ Ошибка подписи:")
                for line in result.stderr.strip().split('\n'):
                    if line.strip():
                        log_queue.put(f"   {line}")
            return False
            
    except Exception as e:
        if log_queue:
            log_queue.put(f"⚠️ Ошибка при подписи exe: {e}")
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
