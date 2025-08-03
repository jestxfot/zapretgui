"""
pyinstaller_builder.py - Модуль для сборки через PyInstaller
"""

from __future__ import annotations
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any, Optional


def create_spec_file(channel: str, root_path: Path) -> Path:
    """
    Создает spec файл для PyInstaller
    
    Args:
        channel: Канал сборки ('stable' или 'test')
        root_path: Корневая папка проекта
        
    Returns:
        Path: Путь к созданному spec файлу
    """
    icon_file = 'ZapretDevLogo3.ico' if channel == 'test' else 'Zapret1.ico'
    
    spec_content = f"""# -*- mode: python ; coding: utf-8 -*-

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
    hooksconfig={{}},
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
    console=False,
    disable_windowed_traceback=True,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    uac_admin=True,
    icon='{icon_file}',
    version='version_info.txt',
)"""
    
    spec_path = root_path / "zapret_build.spec"
    spec_path.write_text(spec_content, encoding='utf-8')
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
            
        run_func([
            sys.executable, "-m", "PyInstaller",
            "--workpath", str(work),
            "--distpath", str(out),
            "--clean",
            "--noconfirm",
            str(spec_path)
        ])
        
        if log_queue:
            log_queue.put("✅ PyInstaller завершен успешно")
            
    except Exception as e:
        if log_queue:
            log_queue.put(f"❌ Ошибка PyInstaller: {e}")
        raise
        
    finally:
        # Очистка временных файлов
        if work.exists():
            shutil.rmtree(work, ignore_errors=True)
            if log_queue:
                log_queue.put(f"🧹 Удалена временная папка: {work}")
                
        if spec_path.exists():
            spec_path.unlink()
            if log_queue:
                log_queue.put(f"🧹 Удален spec файл: {spec_path}")


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