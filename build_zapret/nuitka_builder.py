"""
nuitka_builder.py - Модуль для сборки через Nuitka
"""

from __future__ import annotations
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional, Tuple


def create_version_info(channel: str, version: str, root_path: Path) -> Path:
    """
    Создает файл с метаданными версии для Nuitka
    
    Args:
        channel: Канал сборки ('stable' или 'test')
        version: Версия приложения
        root_path: Корневая папка проекта
        
    Returns:
        Path: Путь к созданному файлу version_info.txt
    """
    # Парсим версию в числа
    version_parts = version.split('.')
    while len(version_parts) < 4:
        version_parts.append('0')
    version_tuple = ', '.join(version_parts[:4])
    
    # Определяем имя продукта
    product_name = "Zapret Dev" if channel == 'test' else "Zapret"
    
    version_info = f"""
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=({version_tuple}),
    prodvers=({version_tuple}),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo(
      [
      StringTable(
        u'040904B0',
        [StringStruct(u'CompanyName', u'Zapret Project'),
        StringStruct(u'FileDescription', u'{product_name} - DPI bypass tool'),
        StringStruct(u'FileVersion', u'{version}'),
        StringStruct(u'InternalName', u'zapret'),
        StringStruct(u'LegalCopyright', u'© 2024 Zapret Project'),
        StringStruct(u'OriginalFilename', u'zapret.exe'),
        StringStruct(u'ProductName', u'{product_name}'),
        StringStruct(u'ProductVersion', u'{version}')])
      ]), 
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)
"""
    
    version_file = root_path / "version_info.txt"
    version_file.write_text(version_info, encoding='utf-8')
    return version_file


def check_and_install_nuitka(python_exe: str, run_func: Any, log_queue: Optional[Any] = None) -> Tuple[bool, str]:
    """
    Проверяет и устанавливает Nuitka если нужно
    
    Args:
        python_exe: Путь к python.exe
        run_func: Функция для запуска команд
        log_queue: Очередь для логов (опционально)
        
    Returns:
        Tuple[bool, str]: (установлен ли Nuitka, путь к python.exe)
    """
    # Сначала пробуем python.exe (консольная версия)
    python_exe = python_exe.replace('pythonw.exe', 'python.exe')
    
    try:
        # Проверяем установлен ли Nuitka
        result = run_func([python_exe, "-m", "nuitka", "--version"], capture=True)
        if log_queue:
            log_queue.put(f"✔ Nuitka найден: {result.strip()}")
        return True, python_exe
    except Exception:
        pass
    
    # Если не найден, пробуем установить
    if log_queue:
        log_queue.put("⚠ Nuitka не найден, пытаемся установить...")
    
    try:
        # Устанавливаем Nuitka
        install_cmd = [python_exe, "-m", "pip", "install", "nuitka"]
        if log_queue:
            log_queue.put(f"Команда установки: {' '.join(install_cmd)}")
        
        run_func(install_cmd)
        
        # Проверяем установку еще раз
        result = run_func([python_exe, "-m", "nuitka", "--version"], capture=True)
        if log_queue:
            log_queue.put(f"✔ Nuitka успешно установлен: {result.strip()}")
        return True, python_exe
        
    except Exception as e:
        if log_queue:
            log_queue.put(f"❌ Не удалось установить Nuitka: {e}")
        return False, python_exe


def run_nuitka(channel: str, version: str, root_path: Path, python_exe: str, 
               run_func: Any, log_queue: Optional[Any] = None) -> None:
    """
    Запускает Nuitka для сборки exe
    
    Args:
        channel: Канал сборки ('stable' или 'test')
        version: Версия приложения
        root_path: Корневая папка проекта
        python_exe: Путь к python.exe
        run_func: Функция для запуска команд
        log_queue: Очередь для логов (опционально)
        
    Raises:
        Exception: При ошибке сборки
    """
    # Проверяем и устанавливаем Nuitka
    nuitka_available, python_exe = check_and_install_nuitka(python_exe, run_func, log_queue)
    if not nuitka_available:
        raise Exception("Не удалось установить Nuitka! Попробуйте вручную: pip install nuitka")
    
    # Создаем файл версии
    version_file = create_version_info(channel, version, root_path)
    
    # Определяем иконку
    icon_file = 'ZapretDevLogo3.ico' if channel == 'test' else 'Zapret1.ico'
    icon_path = root_path / icon_file
    
    if not icon_path.exists():
        if log_queue:
            log_queue.put(f"⚠ Иконка не найдена: {icon_path}")
        icon_path = None
    
    # Выходной файл
    output_path = root_path / "zapret.exe"
    
    # Удаляем старый exe если есть
    if output_path.exists():
        output_path.unlink()
        if log_queue:
            log_queue.put("✔ Удален старый zapret.exe")
    
    try:
        # Базовые параметры Nuitka
        nuitka_args = [
            python_exe, "-m", "nuitka",
            "--standalone",
            "--onefile", 
            "--remove-output",
            "--windows-console-mode=disable",
            "--assume-yes-for-downloads",
            
            # ВАЖНО: Поддержка multiprocessing и threading
            "--plugin-enable=multiprocessing",
            "--plugin-enable=anti-bloat",
            
            # Метаданные Windows
            f"--windows-file-version={version}",
            f"--windows-product-version={version}",
            "--windows-company-name=Zapret Project",
            f"--windows-product-name={'Zapret Dev' if channel == 'test' else 'Zapret'}",
            "--windows-file-description=Zapret - DPI bypass tool",
            
            # UAC админские права
            "--windows-uac-admin",
            
            # Оптимизации
            "--python-flag=-O",
            "--follow-imports",
            
            # ============= ВСЕ МОДУЛИ ИЗ ВАШЕГО ПРОЕКТА =============
            "--include-package=altmenu",
            "--include-package=autostart", 
            "--include-package=config",
            "--include-package=discord",
            "--include-package=dns",
            "--include-package=donater",
            "--include-package=dpi",
            "--include-package=hosts",
            "--include-package=log",
            "--include-package=managers",
            "--include-package=startup",
            "--include-package=strategy_menu",
            "--include-package=tgram",
            "--include-package=ui",
            "--include-package=ui.pages",  # ✅ Явно включаем подпакет pages
            "--include-package=updater",
            "--include-package=utils",
            
            # ============= ЯВНЫЕ ВКЛЮЧЕНИЯ UI МОДУЛЕЙ =============
            # (Nuitka иногда пропускает модули в пакетах)
            "--include-module=ui.splash_screen",
            "--include-module=ui.main_window",
            "--include-module=ui.theme",
            "--include-module=ui.theme_subscription_manager",
            "--include-module=ui.sidebar",
            "--include-module=ui.custom_titlebar",
            "--include-module=ui.help_dialog",
            "--include-module=ui.acrylic",
            "--include-module=ui.fluent_icons",
            "--include-module=ui.pages.home_page",
            "--include-module=ui.pages.control_page",
            "--include-module=ui.pages.strategies_page",
            "--include-module=ui.pages.zapret1_strategies_page",
            "--include-module=ui.pages.direct_zapret2_strategies_page",
            "--include-module=ui.pages.network_page",
            "--include-module=ui.pages.autostart_page",
            "--include-module=ui.pages.appearance_page",
            "--include-module=ui.pages.about_page",
            "--include-module=ui.pages.base_page",
            
            # ============= ЯВНЫЕ ВКЛЮЧЕНИЯ LOG МОДУЛЕЙ =============
            "--include-module=log.log",
            "--include-module=log.crash_handler",
            
            # Основные системные модули
            "--include-module=queue", 
            "--include-module=threading",
            "--include-module=subprocess",
            "--include-module=pathlib",
            "--include-module=json",
            "--include-module=configparser",
            "--include-module=tempfile",
            "--include-module=shutil",
            "--include-module=time",
            "--include-module=datetime",
            "--include-module=os",
            "--include-module=sys",
            "--include-module=re",
            "--include-module=urllib",
            "--include-module=urllib.request",
            "--include-module=urllib.parse",
            
            # PyQt6 и Qt материалы
            "--enable-plugin=pyqt6",
            "--include-package=PyQt6",
            "--include-package=PyQt6.QtCore",
            "--include-package=PyQt6.QtWidgets", 
            "--include-package=PyQt6.QtGui",
            "--include-package=qt_material",
            "--include-qt-plugins=all",
            
            # Windows API
            "--include-module=ctypes",
            "--include-module=ctypes.wintypes",
            
            # Сетевые модули
            "--include-module=requests",
            "--include-module=urllib3",
            
            # ============= ДАННЫЕ ФАЙЛЫ =============
            # Иконки
            f"--include-data-files={root_path / 'Zapret1.ico'}=Zapret1.ico",
            f"--include-data-files={root_path / 'ZapretDevLogo3.ico'}=ZapretDevLogo3.ico",
            
            # ⚠️ НЕ используем --include-data-dir для Python пакетов!
            # Пакеты ui, config и др. уже включены через --include-package выше.
            # --include-data-dir конфликтует с --include-package и мешает компиляции.
            
            # ============= ИСКЛЮЧЕНИЯ =============
            "--nofollow-import-to=test",
            "--nofollow-import-to=build", 
            "--nofollow-import-to=dist",
            "--nofollow-import-to=logs",
            "--nofollow-import-to=__pycache__",
            
            # Выходной файл
            f"--output-filename=zapret.exe",
            
            # Главный файл
            "main.py"
        ]
        
        # Добавляем иконку если найдена
        if icon_path:
            nuitka_args.insert(-1, f"--windows-icon-from-ico={icon_path}")
        
        # Проверяем и добавляем только существующие модули
        additional_modules = [
            "win32com", "win32com.client", "pythoncom", 
            "win32api", "win32con", "win32service", "win32serviceutil",
            "pkg_resources", "paramiko", "psutil", "packaging"
        ]

        for module in additional_modules:
            try:
                __import__(module)
                nuitka_args.insert(-1, f"--include-module={module}")
                if log_queue:
                    log_queue.put(f"✔ Включен модуль: {module}")
            except ImportError:
                if log_queue:
                    log_queue.put(f"⚠ Модуль {module} недоступен, пропускаем")
        
        if log_queue:
            log_queue.put("🔨 Запуск Nuitka...")
            log_queue.put("⏳ Это может занять 5-15 минут...")

        # Проверяем наличие дополнительных файлов данных
        data_files_to_check = [
            "build.json",
            "zapret.iss",
            "connection_test.py",
            "downloader.py", 
            "heavy_init_worker.py",
            "log.py",
            "tray.py"
        ]

        for file_name in data_files_to_check:
            file_path = root_path / file_name
            if file_path.exists():
                nuitka_args.insert(-1, f"--include-data-files={file_path}={file_name}")
                if log_queue:
                    log_queue.put(f"✔ Включен файл данных: {file_name}")
                            
        # Показываем команду для отладки (первые параметры)
        cmd_preview = ' '.join(nuitka_args[:10]) + " ... main.py"
        if log_queue:
            log_queue.put(f"Команда: {cmd_preview}")
        
        # Запускаем Nuitka с улучшенным логированием
        process = subprocess.Popen(
            nuitka_args,
            cwd=root_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        )
        
        # Собираем весь вывод
        all_output = []
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                line = output.strip()
                all_output.append(line)
                if line and log_queue:
                    # Показываем все важные сообщения
                    if any(keyword in line.lower() for keyword in 
                        ['error', 'fatal', 'warning', 'info:', 'nuitka:', 'compiling', 'linking', 'creating']):
                        log_queue.put(f"Nuitka: {line}")
                    elif len(line) < 100:  # Короткие строки тоже показываем
                        log_queue.put(f"Nuitka: {line}")
        
        return_code = process.poll()
        
        if return_code != 0:
            # Показываем последние строки вывода при ошибке
            if log_queue:
                log_queue.put("❌ Ошибка компиляции Nuitka!")
                log_queue.put("📋 Последние строки вывода:")
                for line in all_output[-20:]:  # Последние 20 строк
                    if line.strip():
                        log_queue.put(f"   {line}")
                
                # Ищем конкретные ошибки
                error_lines = [line for line in all_output if 'error' in line.lower() or 'fatal' in line.lower()]
                if error_lines:
                    log_queue.put("🔍 Найденные ошибки:")
                    for error in error_lines[-5:]:  # Последние 5 ошибок
                        log_queue.put(f"   ❌ {error}")
            
            raise Exception(f"Ошибка компиляции Nuitka (код {return_code}). Смотрите лог выше.")
        
        # Проверяем что exe создан
        if not output_path.exists():
            raise FileNotFoundError(f"Nuitka не создал {output_path}")
            
        # Получаем размер файла
        size_mb = output_path.stat().st_size / (1024 * 1024)
        if log_queue:
            log_queue.put(f"✔ Создан zapret.exe ({size_mb:.1f} MB)")
        
        # Перемещаем в нужную папку для Inno Setup
        target_dir = root_path.parent / "zapret"
        target_dir.mkdir(exist_ok=True)
        
        target_exe = target_dir / "zapret.exe"
        if target_exe.exists():
            target_exe.unlink()
            
        shutil.move(str(output_path), str(target_exe))
        if log_queue:
            log_queue.put(f"✔ Перемещен в {target_exe}")
        
    except subprocess.CalledProcessError as e:
        raise Exception(f"Ошибка компиляции Nuitka (код {e.returncode}). Смотрите лог выше.")
    except Exception as e:
        raise Exception(f"Ошибка сборки Nuitka: {str(e)}")
    finally:
        # Удаляем временные файлы
        if version_file and version_file.exists():
            version_file.unlink()
        
        # Удаляем папки сборки
        cleanup_dirs = ["zapret.build", "zapret.dist", "zapret.onefile-build"]
        for dir_name in cleanup_dirs:
            build_dir = root_path / dir_name
            if build_dir.exists():
                shutil.rmtree(build_dir, ignore_errors=True)
                if log_queue:
                    log_queue.put(f"✔ Удалена временная папка: {dir_name}")


def check_nuitka_available() -> bool:
    """
    Проверяет доступность Nuitka
    
    Returns:
        bool: True если Nuitka установлен
    """
    try:
        import nuitka
        return True
    except ImportError:
        return False


def get_nuitka_version() -> str:
    """
    Получает версию Nuitka
    
    Returns:
        str: Версия Nuitka или сообщение об ошибке
    """
    try:
        import nuitka
        return nuitka.__version__
    except ImportError:
        return "Nuitka не установлен"
    except AttributeError:
        # Если __version__ не определен, пробуем через командную строку
        try:
            import subprocess
            result = subprocess.run([sys.executable, "-m", "nuitka", "--version"], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout.strip()
        except:
            pass
        return "Версия неизвестна"
