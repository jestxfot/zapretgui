"""
nuitka_builder.py - Модуль для сборки через Nuitka.

Сборка делается в режиме onedir (standalone), чтобы приложение работало из папки
установки и корректно определяло пути (onefile часто запускается из временной
папки распаковки).
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional, Tuple


def _log(log_queue: Optional[Any], text: str) -> None:
    if log_queue:
        log_queue.put(text)


def cleanup_all_cache(root_path: Path, log_queue: Optional[Any] = None) -> int:
    """
    Полная очистка всего кэша перед сборкой:
    - __pycache__ во всём проекте
    - .pyc файлы
    - *.build и *.dist папки Nuitka

    Args:
        root_path: Корневая папка проекта
        log_queue: Очередь для логов

    Returns:
        int: Количество удалённых элементов
    """
    cleaned = 0

    _log(log_queue, "🧹 Очистка всего кэша проекта...")

    # 1. Удаляем все __pycache__ папки
    for cache_dir in root_path.rglob("__pycache__"):
        if cache_dir.is_dir():
            try:
                shutil.rmtree(cache_dir, ignore_errors=True)
                cleaned += 1
            except Exception:
                pass

    _log(log_queue, f"   ✓ Удалено __pycache__ папок: {cleaned}")

    # 2. Удаляем .pyc файлы
    pyc_count = 0
    for pyc_file in root_path.rglob("*.pyc"):
        try:
            pyc_file.unlink(missing_ok=True)
            pyc_count += 1
        except Exception:
            pass

    if pyc_count:
        _log(log_queue, f"   ✓ Удалено .pyc файлов: {pyc_count}")
    cleaned += pyc_count

    # 3. Удаляем *.build и *.dist папки Nuitka
    for build_dir in root_path.glob("*.build"):
        if build_dir.is_dir():
            try:
                shutil.rmtree(build_dir, ignore_errors=True)
                cleaned += 1
                _log(log_queue, f"   ✓ Удалена: {build_dir.name}")
            except Exception:
                pass

    for dist_dir in root_path.glob("*.dist"):
        if dist_dir.is_dir():
            try:
                shutil.rmtree(dist_dir, ignore_errors=True)
                cleaned += 1
                _log(log_queue, f"   ✓ Удалена: {dist_dir.name}")
            except Exception:
                pass

    # 4. Удаляем __pycache__ в build_zapret/
    build_zapret_cache = Path(__file__).parent / "__pycache__"
    if build_zapret_cache.exists():
        try:
            shutil.rmtree(build_zapret_cache, ignore_errors=True)
            cleaned += 1
            _log(log_queue, f"   ✓ Удалён кэш build_zapret/")
        except Exception:
            pass

    _log(log_queue, f"🧹 Очистка завершена: {cleaned} элементов удалено")

    return cleaned


def _is_windows_store_python(python_exe: str) -> bool:
    p = python_exe.replace("/", "\\").lower()
    return (
        "\\windowsapps\\" in p
        or "pythonsoftwarefoundation.python" in p
        or p.endswith("\\windowsapps\\python.exe")
        or "\\windowsapps\\python" in p
    )


def _exception_text(exc: Exception) -> str:
    parts: list[str] = [str(exc)]
    for attr in ("stdout", "output", "stderr"):
        try:
            val = getattr(exc, attr, None)
        except Exception:
            val = None
        if not val:
            continue
        if isinstance(val, bytes):
            try:
                val = val.decode("utf-8", errors="ignore")
            except Exception:
                val = ""
        if isinstance(val, str) and val.strip():
            parts.append(val)
    return "\n".join(parts)


def create_version_info(channel: str, version: str, root_path: Path) -> Path:
    """
    Создает файл с метаданными версии (VSVersionInfo).
    Сейчас используется как совместимость с существующим API сборщиков.
    """
    version_parts = version.split(".")
    while len(version_parts) < 4:
        version_parts.append("0")
    version_tuple = ", ".join(version_parts[:4])

    product_name = "Zapret Dev" if channel == "test" else "Zapret"
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
        StringStruct(u'OriginalFilename', u'Zapret.exe'),
        StringStruct(u'ProductName', u'{product_name}'),
        StringStruct(u'ProductVersion', u'{version}')])
      ]),
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)
"""

    version_file = root_path / "version_info.txt"
    version_file.write_text(version_info, encoding="utf-8")
    return version_file


def check_and_install_nuitka(
    python_exe: str, run_func: Any, log_queue: Optional[Any] = None
) -> Tuple[bool, str]:
    """
    Проверяет наличие Nuitka, при необходимости пытается установить.
    """
    python_exe = python_exe.replace("pythonw.exe", "python.exe")
    if sys.platform == "win32" and _is_windows_store_python(python_exe):
        _log(
            log_queue,
            "❌ Nuitka не поддерживает Python из Microsoft Store (WindowsApps). "
            "Установите python.org (обычный CPython) и запускайте сборку через него.",
        )
        return False, python_exe

    try:
        result = run_func([python_exe, "-m", "nuitka", "--version"], capture=True)
        _log(log_queue, f"✔ Nuitka найден: {str(result).strip()}")
        return True, python_exe
    except Exception as e:
        msg = _exception_text(e)
        if "windows app store" in msg.lower() or "not supported" in msg.lower():
            _log(log_queue, f"❌ Nuitka не может работать с этим Python:\n{msg}")
            return False, python_exe

    _log(log_queue, "⚠ Nuitka не найден, пытаемся установить...")

    try:
        install_cmd = [python_exe, "-m", "pip", "install", "--upgrade", "nuitka"]
        _log(log_queue, f"Команда установки: {' '.join(install_cmd)}")
        run_func(install_cmd)

        result = run_func([python_exe, "-m", "nuitka", "--version"], capture=True)
        _log(log_queue, f"✔ Nuitka успешно установлен: {str(result).strip()}")
        return True, python_exe
    except Exception as e:
        _log(log_queue, f"❌ Не удалось установить Nuitka: {e}")
        return False, python_exe


def _module_source_exists(root_path: Path, module_name: str) -> bool:
    rel = Path(*module_name.split("."))
    return (root_path / f"{rel}.py").exists() or (root_path / rel / "__init__.py").exists()


def _pick_dist_dir(root_path: Path) -> Path:
    dist_candidates = [p for p in root_path.glob("*.dist") if p.is_dir()]
    if not dist_candidates:
        raise FileNotFoundError("Nuitka не создал папку *.dist (ожидается --standalone)")
    return max(dist_candidates, key=lambda p: p.stat().st_mtime)


def _clear_dir(path: Path) -> None:
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)
        return
    for entry in path.iterdir():
        if entry.is_dir():
            shutil.rmtree(entry, ignore_errors=True)
        else:
            entry.unlink(missing_ok=True)


def run_nuitka(
    channel: str,
    version: str,
    root_path: Path,
    python_exe: str,
    run_func: Any,
    log_queue: Optional[Any] = None,
    *,
    target_dir: Optional[Path] = None,
) -> Path:
    """
    Собирает Zapret GUI через Nuitka в режиме onedir (standalone) и копирует
    содержимое *.dist в target_dir.
    """
    nuitka_available, python_exe = check_and_install_nuitka(python_exe, run_func, log_queue)
    if not nuitka_available:
        if sys.platform == "win32" and _is_windows_store_python(python_exe):
            raise Exception(
                "Nuitka не поддерживает Python из Microsoft Store (WindowsApps). "
                "Поставьте CPython с python.org и запустите сборку через него."
            )
        raise Exception("Nuitka недоступен. Установите python.org + pip install nuitka")

    root_path = Path(root_path).resolve()
    if target_dir is None:
        # Inno Setup (*.iss) ожидает файлы в "{#SourcePath}\\Zapret\\*"
        target_dir = root_path.parent / "zapret" / "Zapret"
    target_dir = Path(target_dir).resolve()
    target_dir.mkdir(parents=True, exist_ok=True)

    # ✅ ОЧИСТКА ВСЕГО КЭША ПЕРЕД СБОРКОЙ
    cleanup_all_cache(root_path, log_queue)

    try:
        icon_file = "ZapretDevLogo3.ico" if channel == "test" else "Zapret1.ico"
        icon_path = root_path / icon_file

        product_name = "Zapret Dev" if channel == "test" else "Zapret"

        nuitka_args: list[str] = [
            python_exe,
            "-m",
            "nuitka",
            "--standalone",
            "--remove-output",
            "--windows-console-mode=disable",
            "--assume-yes-for-downloads",
            "--windows-uac-admin",
            "--python-flag=-O",
            "--follow-imports",
            "--enable-plugin=pyqt6",
            "--include-qt-plugins=all",
            f"--windows-file-version={version}",
            f"--windows-product-version={version}",
            "--windows-company-name=Zapret Project",
            f"--windows-product-name={product_name}",
            "--windows-file-description=Zapret - DPI bypass tool",
        ]

        if icon_path.exists():
            nuitka_args.append(f"--windows-icon-from-ico={icon_path}")
        else:
            _log(log_queue, f"⚠ Иконка не найдена: {icon_path}")

        # Built-in presets are installed to %APPDATA%\zapret\presets by Inno Setup.

        # Включаем пакеты проекта (часть импортов делается динамически)
        packages_to_include = [
            "altmenu",
            "autostart",
            "config",
            "discord",
            "dns",
            "donater",
            "dpi",
            "hosts",
            "launcher_common",
            "log",
            "managers",
            "orchestra",
            "preset_zapret2",
            "startup",
            "strategy_menu",
            "tgram",
            "ui",
            "updater",
            "utils",
            "widgets",
            "zapret1_launcher",
            "zapret2_launcher",
        ]

        for pkg in packages_to_include:
            pkg_dir = root_path / pkg
            if pkg_dir.is_dir() and any(pkg_dir.rglob("*.py")):
                nuitka_args.append(f"--include-package={pkg}")

        # Явные модули (только если реально есть в исходниках)
        modules_to_include = [
            "ui.dialogs.add_category_dialog",
            "ui.pages.home_page",
            "ui.pages.control_page",
            "ui.pages.network_page",
        ]
        for mod in modules_to_include:
            if _module_source_exists(root_path, mod):
                nuitka_args.append(f"--include-module={mod}")

        # Опциональные зависимости
        for mod in [
            "win32com",
            "win32com.client",
            "pythoncom",
            "win32api",
            "win32con",
            "win32service",
            "win32serviceutil",
            "pkg_resources",
            "paramiko",
            "psutil",
            "packaging",
        ]:
            try:
                __import__(mod)
            except Exception:
                continue
            nuitka_args.append(f"--include-module={mod}")

        # Имя exe
        nuitka_args.append("--output-filename=Zapret.exe")
        nuitka_args.append("main.py")

        _log(log_queue, "🔨 Запуск Nuitka...")
        _log(log_queue, "⏳ Это может занять 5-15 минут...")

        process = subprocess.Popen(
            nuitka_args,
            cwd=root_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )

        all_output: list[str] = []
        assert process.stdout is not None
        while True:
            output = process.stdout.readline()
            if output == "" and process.poll() is not None:
                break
            if output:
                line = output.strip()
                all_output.append(line)
                if log_queue and line:
                    if any(
                        k in line.lower()
                        for k in ("error", "fatal", "warning", "nuitka:", "compiling", "linking", "creating")
                    ):
                        _log(log_queue, f"Nuitka: {line}")

        return_code = process.poll()
        if return_code != 0:
            if log_queue:
                _log(log_queue, "❌ Ошибка компиляции Nuitka!")
                _log(log_queue, "📋 Последние строки вывода:")
                for line in all_output[-30:]:
                    if line.strip():
                        _log(log_queue, f"   {line}")
            raise Exception(f"Ошибка компиляции Nuitka (код {return_code})")

        dist_dir = _pick_dist_dir(root_path)
        exe_in_dist = dist_dir / "Zapret.exe"
        if not exe_in_dist.exists():
            candidates = [p for p in dist_dir.glob("*.exe") if p.is_file()]
            if not candidates:
                raise FileNotFoundError(f"В {dist_dir} нет *.exe после сборки Nuitka")
            exe_in_dist = max(candidates, key=lambda p: p.stat().st_size)

        _clear_dir(target_dir)
        for src in dist_dir.iterdir():
            dst = target_dir / src.name
            if src.is_dir():
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)

        produced = target_dir / exe_in_dist.name
        if produced.name.lower() != "zapret.exe":
            # На всякий случай нормализуем имя под Inno Setup ярлыки/иконку
            normalized = target_dir / "Zapret.exe"
            if normalized.exists():
                normalized.unlink(missing_ok=True)
            produced.replace(normalized)
            produced = normalized

        size_mb = produced.stat().st_size / (1024 * 1024)
        _log(log_queue, f"✔ Создан onedir: {dist_dir.name} ({produced.name} {size_mb:.1f} MB)")
        _log(log_queue, f"✔ Скопировано в {target_dir}")
        return produced

    finally:
        for build_dir in root_path.glob("*.build"):
            if build_dir.is_dir():
                shutil.rmtree(build_dir, ignore_errors=True)
        for dist_dir in root_path.glob("*.dist"):
            if dist_dir.is_dir():
                shutil.rmtree(dist_dir, ignore_errors=True)


def check_nuitka_available() -> bool:
    try:
        import nuitka  # noqa: F401
        return True
    except Exception:
        return False


def get_nuitka_version() -> str:
    try:
        import nuitka
        return getattr(nuitka, "__version__", "unknown")
    except Exception:
        try:
            res = subprocess.run(
                [sys.executable, "-m", "nuitka", "--version"],
                capture_output=True,
                text=True,
            )
            if res.returncode == 0:
                return res.stdout.strip()
        except Exception:
            pass
        return "Nuitka не установлен"
