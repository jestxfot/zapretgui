# zapret.spec
# -*- mode: python ; coding: utf-8 -*-
import os

# Определяем канал сборки
CHANNEL = os.environ.get('BUILD_CHANNEL', 'stable')
ICON_FILE = 'ZapretDevLogo.ico' if CHANNEL == 'test' else 'zapret.ico'

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'win32com', 
        'win32com.client', 
        'pythoncom',
        'win32api',
        'win32con',
        'win32service',
        'win32serviceutil'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='zapret',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Критически важно!
    disable_windowed_traceback=True,  # Отключает окна с ошибками
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    uac_admin=True,  # Права администратора
    icon=ICON_FILE,
    version='version_info.txt',
    # Дополнительные параметры для подавления консолей
    hide_console='hide-late',  # Скрывает консоль как можно позже
)