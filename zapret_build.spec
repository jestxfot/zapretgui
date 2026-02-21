# -*- mode: python ; coding: utf-8 -*-
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
    pathex=[r'H:\Privacy\zapretgui'],  # ВАЖНО: путь к проекту!
    binaries=[
        (os.path.join(_pyqt6_dir, 'QtXml.pyd'), 'PyQt6'),
        (os.path.join(_pyqt6_qt6_bin, 'Qt6Xml.dll'), 'PyQt6/Qt6/bin'),
    ],
    datas=[(r'H:\Privacy\zapretgui\preset_zapret1\basic_strategies\discord_udp_zapret1.txt', r'preset_zapret1/basic_strategies'), (r'H:\Privacy\zapretgui\preset_zapret1\basic_strategies\discord_voice_zapret1.txt', r'preset_zapret1/basic_strategies'), (r'H:\Privacy\zapretgui\preset_zapret1\basic_strategies\http80_zapret1.txt', r'preset_zapret1/basic_strategies'), (r'H:\Privacy\zapretgui\preset_zapret1\basic_strategies\tcp_zapret1.txt', r'preset_zapret1/basic_strategies'), (r'H:\Privacy\zapretgui\preset_zapret1\basic_strategies\udp_zapret1.txt', r'preset_zapret1/basic_strategies')],  # Включаем data файлы
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