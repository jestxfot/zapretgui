# updater/update.py
"""
updater/update.py
────────────────────────────────────────────────────────────────
Проверяет GitHub releases и, если в своём канале (stable / dev) 
есть более свежая версия, тихо скачивает установщик, запускает 
его и закрывает программу.

API 100-% совместим со старым кодом:
    • run_update_async(parent, silent=False)        – создаёт поток
    • check_and_run_update(parent, status_cb, …)    – сама логика
    • сигнал UpdateWorker.finished(bool)            – остаётся bool
"""
from __future__ import annotations

import os, sys, tempfile, subprocess, shutil, time, requests
from typing import Callable

from PyQt6.QtCore    import QObject, QThread, pyqtSignal, QTimer
from PyQt6.QtWidgets import QMessageBox
from packaging import version
from utils import run_hidden

from .release_manager import get_latest_release
from .github_release import normalize_version
from config import CHANNEL, APP_VERSION
from log import log

TIMEOUT = 10  # сек.

# ──────────────────────────── вспомогательные утилиты ─────────────────────
def _safe_set_status(parent, msg: str):
    """Пишем в status-label, если она есть; иначе в консоль."""
    if parent and hasattr(parent, "set_status"):
        parent.set_status(msg)
    else:
        print(msg)

def _kill_winws():
    """Мягко-агрессивно убиваем winws.exe, чтобы установщик мог заменить файл."""
    run_hidden(
        "C:\\Windows\\System32\\taskkill.exe /F /IM winws.exe /T",
        shell=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

def _download(url: str, dest: str, on_progress: Callable[[int, int], None] | None, verify_ssl: bool = True):
    import requests
    
    # Создаем сессию с настройками SSL
    session = requests.Session()
    if not verify_ssl:
        # Отключаем проверку SSL для самоподписанных сертификатов
        session.verify = False
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    with session.get(url, stream=True, timeout=TIMEOUT, verify=verify_ssl) as resp:
        resp.raise_for_status()
        total = int(resp.headers.get("content-length", 0))
        done = 0
        with open(dest, "wb") as fp:
            for chunk in resp.iter_content(8192):
                fp.write(chunk)
                if on_progress and total:
                    done += len(chunk)
                    on_progress(done, total)

def compare_versions(v1: str, v2: str) -> int:
    """
    Сравнивает две версии.
    Возвращает:
        -1 если v1 < v2
         0 если v1 == v2
         1 если v1 > v2
    """
    from packaging import version
    
    try:
        # Нормализуем версии
        v1_norm = normalize_version(v1)
        v2_norm = normalize_version(v2)
        
        # Парсим через packaging.version
        ver1 = version.parse(v1_norm)
        ver2 = version.parse(v2_norm)
        
        if ver1 < ver2:
            return -1
        elif ver1 > ver2:
            return 1
        else:
            return 0
            
    except Exception as e:
        log(f"Error comparing versions '{v1}' and '{v2}': {e}", "🔁❌ ERROR")
        # Fallback на строковое сравнение
        return -1 if v1 < v2 else (1 if v1 > v2 else 0)

# ──────────────────────────── фоновой воркер ──────────────────────────────
class UpdateWorker(QObject):
    progress = pyqtSignal(str)    # статус-строка
    finished = pyqtSignal(bool)   # True – установщик запущен

    def __init__(self, parent=None, silent: bool = False):
        super().__init__()
        self._parent = parent
        self._silent = silent

    def _emit(self, msg: str):
        self.progress.emit(msg)

    def run(self):
        try:
            ok = check_and_run_update(
                parent    = self._parent,
                status_cb = self._emit,
                silent    = self._silent,
            )
            self.finished.emit(ok)
        except Exception as e:
            self._emit(f"Ошибка обновления: {e}")
            self.finished.emit(False)

# ──────────────────────────── public-API ──────────────────────────────────
def run_update_async(parent=None, *, silent: bool = False) -> QThread:
    """
    Создаёт QThread + UpdateWorker.
    Возвращает ссылку на thread (в нём есть ._worker).
    """
    thr = QThread(parent)
    worker = UpdateWorker(parent, silent)
    worker.moveToThread(thr)

    thr.started.connect(worker.run)
    worker.finished.connect(thr.quit)
    worker.finished.connect(worker.deleteLater)
    thr.finished.connect(thr.deleteLater)

    # status-label + логирование
    worker.progress.connect(lambda m: _safe_set_status(parent, m))
    worker.progress.connect(lambda m: log(f'{m}', "🔁 UPDATE"))

    thr._worker = worker  # 👈 защитили от GC
    thr.start()

    # держим thread в parent-окне, чтобы GC не убил раньше времени
    if parent is not None:
        lst = getattr(parent, "_active_upd_threads", [])
        lst.append(thr)
        parent._active_upd_threads = lst
        thr.finished.connect(lambda *, l=lst, t=thr: l.remove(t))

    return thr
    
def check_and_run_update(
    *,
    parent   = None,
    status_cb: Callable[[str], None] | None = None,
    silent   : bool = False,
) -> bool:
    """
    1) Получает последний релиз с GitHub в зависимости от канала.
    2) Если версия новее – (optionally) спрашивает пользователя,
       затем качает .exe → TEMP, останавливает winws.exe
       и запускает установщик.
    3) Через 1,5 с закрывает текущую программу.
    """
    # локальные «шорткаты»
    def set_status(msg: str):
        if status_cb:
            status_cb(msg)
        else:
            _safe_set_status(parent, msg)

    # — 1. Получаем информацию о последнем релизе --------------------------
    set_status("Проверка обновлений…")
    
    release_info = get_latest_release(CHANNEL)
    if not release_info:
        set_status("Не удалось проверить обновления.")
        return False

    new_ver = release_info["version"]
    upd_url = release_info["update_url"]
    notes   = release_info["release_notes"]
    is_pre  = release_info["prerelease"]
    
    # Нормализуем текущую версию для корректного сравнения
    try:
        app_ver_norm = normalize_version(APP_VERSION)
    except ValueError:
        log(f"Invalid APP_VERSION format: {APP_VERSION}", "🔁❌ ERROR")
        set_status("Ошибка версии приложения.")
        return False
    
    log(f"Auto-update: channel={CHANNEL}, local={app_ver_norm}, remote={new_ver}, prerelease={is_pre}", "🔁 UPDATE")

    # Сравниваем версии
    cmp_result = compare_versions(app_ver_norm, new_ver)
    
    # Для отладки
    log(f"Version comparison: {app_ver_norm} vs {new_ver} = {cmp_result}", "🔁 UPDATE")
    
    if cmp_result >= 0:  # Текущая версия >= новой
        set_status(f"✅ Обновлений нет (v{app_ver_norm})")
        if not silent:
            QMessageBox.information(parent, "Обновление", f"У вас последняя версия ({app_ver_norm}).")
        return False

    # — 2. спрашиваем пользователя -----------------------------------------
    if not silent:
        version_type = " (предварительная версия)" if is_pre else ""
        txt = (f"Доступна новая версия {new_ver}{version_type} (у вас {app_ver_norm}).\n\n"
               f"{notes}\n\nУстановить сейчас?")
        btn = QMessageBox.question(
            parent, "Доступно обновление",
            txt,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if btn != QMessageBox.StandardButton.Yes:
            return False

    # — 3. скачиваем установщик --------------------------------------------
    tmp_dir   = tempfile.mkdtemp(prefix="zapret_upd_")
    setup_exe = os.path.join(tmp_dir, "ZapretSetup.exe")

    def _prog(done, total): 
        set_status(f"Скачивание… {done*100//total}%")
    
    # Список URL для попытки скачивания
    download_urls = [upd_url]
    
    # Если это HTTPS URL с нашего сервера, добавляем HTTP вариант как fallback
    if upd_url.startswith("https://"):
        # Заменяем https на http и порт если это наш сервер
        if "88.210.21.236:888" in upd_url:
            http_url = upd_url.replace("https://", "http://").replace(":888", ":887")
            download_urls.append(http_url)
    
    # Пытаемся скачать
    download_error = None
    for idx, url in enumerate(download_urls):
        try:
            # Определяем нужно ли проверять SSL
            verify_ssl = not (url.startswith("https://88.210.21.236") or 
                            url.startswith("https://127.0.0.1") or 
                            url.startswith("https://localhost"))
            
            log(f"Попытка скачивания с {url} (verify_ssl={verify_ssl})", "🔁 UPDATE")
            _download(url, setup_exe, _prog if not silent else None, verify_ssl=verify_ssl)
            
            # Успешно скачали
            download_error = None
            break
        
        except requests.exceptions.SSLError as e:
            download_error = e
            log(f"SSL ошибка при скачивании с {url}: {e}", "🔁❌ ERROR")
            if idx < len(download_urls) - 1:
                set_status("SSL ошибка, пробуем альтернативный сервер...")
                time.sleep(0.5)
        except Exception as e:
            download_error = e
            log(f"Ошибка при скачивании с {url}: {e}", "🔁❌ ERROR")
            if idx < len(download_urls) - 1:
                set_status("Ошибка загрузки, пробуем альтернативный сервер...")
                time.sleep(0.5)
    
    if download_error:
        set_status(f"Ошибка загрузки: {download_error}")
        shutil.rmtree(tmp_dir, True)
        return False

    # — 4. запускаем установщик --------------------------------------------
    try:
        # останавливаем DPI-процесс и убиваем, если не успел
        from dpi.stop import stop_dpi
        stop_dpi(parent)
        time.sleep(0.5)
        _kill_winws()
        time.sleep(1.5)

        run_hidden(["C:\\Windows\\System32\\cmd.exe", "/c", "start", "", setup_exe, "/NORESTART"], shell=False)
        set_status("Запущен установщик…")
        # через 1,5 сек выходим, чтобы Install‐EXE смог перезаписать файлы
        QTimer.singleShot(1500, lambda: os._exit(0))
        return True

    except Exception as e:
        set_status(f"Не удалось запустить установщик: {e}")
        shutil.rmtree(tmp_dir, True)
        return False