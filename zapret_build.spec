# -*- mode: python ; coding: utf-8 -*-
import sys
from PyInstaller.utils.hooks import collect_submodules

# Собираем ВСЕ подмодули ui пакета
ui_hiddenimports = collect_submodules('ui')
log_hiddenimports = collect_submodules('log')
managers_hiddenimports = collect_submodules('managers')
strategy_hiddenimports = collect_submodules('strategy_menu')

a = Analysis(
    ['main.py'],
    pathex=[r'H:\Privacy\zapretgui'],  # ✅ ВАЖНО: путь к проекту!
    binaries=[],
    datas=[(r'H:\Privacy\zapretgui\build_zapret\zapret_certificate.cer', '.')],  # ✅ Включаем сертификат и другие data файлы
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
        
        # ============= STARTUP MODULES =============
        'startup',
        'startup.admin_check',
        'startup.single_instance',
        'startup.kaspersky',
        'startup.ipc_manager',
        'startup.check_start',
        'startup.bfe_util',
        'startup.remove_terminal',
        'startup.admin_check_debug',
        'startup.certificate_installer',  # ✅ Автоустановка сертификата
        
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
    hooksconfig={},
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
        # Qt bindings - оставляем только PyQt6
        'PySide6',
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        'PySide2',
        'PyQt5',
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
    icon=r'H:\Privacy\zapretgui\ZapretDevLogo4.ico',
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
)