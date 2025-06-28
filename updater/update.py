"""
updater/update.py
────────────────────────────────────────────────────────────────
Проверяет https://zapretdpi.ru/version.json и, если в своём
канале (stable / test) есть более свежая версия, тихо
скачивает установщик, запускает его и закрывает программу.

API 100-% совместим со старым кодом:
    • run_update_async(parent, silent=False)        – создаёт поток
    • check_and_run_update(parent, status_cb, …)    – сама логика
    • сигнал UpdateWorker.finished(bool)            – остаётся bool
"""
from __future__ import annotations

import os, sys, tempfile, subprocess, shutil, time, json
from typing import Callable

from PyQt6.QtCore    import QObject, QThread, pyqtSignal, QTimer
from PyQt6.QtWidgets import QMessageBox

# ──────────────────────────── конфиг программы ────────────────────────────
from config import CHANNEL, APP_VERSION            # build_info moved to config/__init__.py
from log                import log

META_URL = "https://zapretdpi.ru/version.json"                # единый JSON
TIMEOUT  = 10                                                 # сек.

# ──────────────────────────── вспомогательные утилиты ─────────────────────
def _safe_set_status(parent, msg: str):
    """Пишем в status-label, если она есть; иначе в консоль."""
    if parent and hasattr(parent, "set_status"):
        parent.set_status(msg)
    else:
        print(msg)

def _kill_winws():
    """Мягко-агрессивно убиваем winws.exe, чтобы установщик мог заменить файл."""
    subprocess.run(
        "C:\\Windows\\System32\\taskkill.exe /F /IM winws.exe /T",
        shell=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

def _download(url: str, dest: str, on_progress: Callable[[int, int], None] | None):
    import requests

    with requests.get(url, stream=True, timeout=TIMEOUT) as resp:
        resp.raise_for_status()
        total = int(resp.headers.get("content-length", 0))
        done  = 0
        with open(dest, "wb") as fp:
            for chunk in resp.iter_content(8192):
                fp.write(chunk)
                if on_progress and total:
                    done += len(chunk)
                    on_progress(done, total)

# ──────────────────────────── фоновой воркер ──────────────────────────────
class UpdateWorker(QObject):
    progress = pyqtSignal(str)    # статус-строка
    finished = pyqtSignal(bool)   # True – установщик запущен

    def __init__(self, parent=None, silent: bool = False):
        super().__init__()
        self._parent = parent
        self._silent = silent

    # ----------------------------------------------------------
    def _emit(self, msg: str):
        self.progress.emit(msg)

    # ----------------------------------------------------------
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
    thr   = QThread(parent)
    worker = UpdateWorker(parent, silent)
    worker.moveToThread(thr)

    thr.started .connect(worker.run)
    worker.finished.connect(thr.quit)
    worker.finished.connect(worker.deleteLater)
    thr.finished.connect(thr.deleteLater)

    # status-label + логирование
    worker.progress.connect(lambda m: _safe_set_status(parent, m))
    worker.progress.connect(lambda m: log(f'{m}', "🔁 UPDATE"))

    thr._worker = worker          # 👈 защитили от GC
    thr.start()

    # держим thread в parent-окне, чтобы GC не убил раньше времени
    if parent is not None:
        lst = getattr(parent, "_active_upd_threads", [])
        lst.append(thr)
        parent._active_upd_threads = lst
        thr.finished.connect(lambda *, l=lst, t=thr: l.remove(t))

    return thr

# ──────────────────────────── основная логика ─────────────────────────────
def safe_json_response(response):
    """Безопасно парсит JSON из response, обрабатывая BOM"""
    try:
        # Сначала пробуем стандартный способ
        return response.json()
    except json.JSONDecodeError:
        # Если не получилось, пробуем с обработкой BOM
        content = response.content
        if content.startswith(b'\xef\xbb\xbf'):
            content = content[3:]
        return json.loads(content.decode('utf-8'))
    
def check_and_run_update(
    *,
    parent   = None,
    status_cb: Callable[[str], None] | None = None,
    silent   : bool = False,
) -> bool:
    """
    1) Скачивает META_URL и берёт узел CHANNEL (stable / test).
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

    from packaging import version
    import requests

    # — 1. meta-файл --------------------------------------------------------
    set_status("Проверка обновлений…")
    try:
        resp = requests.get(META_URL, timeout=TIMEOUT)
        resp.raise_for_status()
        meta_all = safe_json_response(resp)
    except Exception as e:
        log(f"Не удалось загрузить version.json: {e}", "🔁❌ ERROR")
        set_status("Не удалось проверить обновления.")
        return False

    meta = meta_all.get(CHANNEL)
    if not meta:
        log(f"В version.json отсутствует блок '{CHANNEL}'", "🔁❌ ERROR")
        return False

    new_ver = meta.get("version")
    upd_url = meta.get("update_url")
    notes   = meta.get("release_notes", "")

    if not new_ver or not upd_url:
        log("Неполный блок version/update_url.", "🔁❌ ERROR")
        return False

    log(f"Auto-update: channel={CHANNEL}, local={APP_VERSION}, remote={new_ver}", "🔁 UPDATE")

    if version.parse(new_ver) <= version.parse(APP_VERSION):
        set_status(f"✅ Обновлений нет (v{APP_VERSION})")
        if not silent:
            QMessageBox.information(parent, "Обновление", f"У вас последняя версия ({APP_VERSION}).")
        return False

    # — 2. спрашиваем пользователя -----------------------------------------
    if not silent:
        txt = (f"Доступна новая версия {new_ver} (у вас {APP_VERSION}).\n\n"
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

    def _prog(done, total): set_status(f"Скачивание… {done*100//total}%")
    try:
        _download(upd_url, setup_exe, _prog if not silent else None)
    except Exception as e:
        set_status(f"Ошибка загрузки: {e}")
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

        subprocess.Popen(["C:\\Windows\\System32\\cmd.exe", "/c", "start", "", setup_exe, "/NORESTART"], shell=False)
        set_status("Запущен установщик…")
        # через 1,5 сек выходим, чтобы Install‐EXE смог перезаписать файлы
        QTimer.singleShot(1500, lambda: os._exit(0))
        return True

    except Exception as e:
        set_status(f"Не удалось запустить установщик: {e}")
        shutil.rmtree(tmp_dir, True)
        return False
