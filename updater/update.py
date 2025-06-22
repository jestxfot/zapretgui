# updater/updater.py

# -----------------------------------------------------------------
# Проверяет https://gitflic.ru/.../version.json и, если версия новее,
# качает ZapretSetup.exe, запускает его /VERYSILENT и закрывает программу.
# -----------------------------------------------------------------
import os, sys, tempfile, subprocess, shutil, time
from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtCore    import QTimer

# ──────────────────────────────────────────────────────────────────
#  Потоковая оболочка  (новое) 
# ──────────────────────────────────────────────────────────────────
from PyQt6.QtCore import QObject, QThread, pyqtSignal

META_URL = "https://zapretdpi.ru/version.json"          # <- ваш JSON
TIMEOUT  = 10                                      # сек.

class UpdateWorker(QObject):
    """Фоновая проверка и установка обновления"""
    progress = pyqtSignal(str)    # любой статус
    finished = pyqtSignal(bool)   # True – обновление запущено / False – отказ

    def __init__(self, parent=None, silent=False):
        super().__init__()
        self._parent = parent
        self._silent = silent

    def run(self):
        """Запускается внутри QThread"""
        try:
            ok = check_and_run_update(
                parent    = self._parent,
                status_cb = self._emit_status,
                silent    = self._silent
            )
            self.finished.emit(ok)
        except Exception as e:
            # Любое необработанное исключение сюда
            self._emit_status(f"Ошибка обновления: {e}")
            self.finished.emit(False)

    # ----------------------------------------------------------------
    def _emit_status(self, msg: str):
        self.progress.emit(msg)

# ──────────────────────────────────────────────────────────────────
def run_update_async(parent, silent: bool = False):
    from log import log
    """
    1. Создаёт поток и воркер;
    2. Запускает check_and_run_update() внутри него;
    3. Автоматически освобождает ресурсы.
    """
    thr  = QThread(parent)
    work = UpdateWorker(parent, silent)
    work.moveToThread(thr)

    # сигналы
    thr.started.connect(work.run)

    # а) в статус-строку
    work.progress.connect(lambda m: _safe_set_status(parent, m))
    # б) в лог для отладки
    work.progress.connect(lambda m: log(f"[Updater] {m}", "DEBUG"))
    
    work.finished.connect(thr.quit)
    work.finished.connect(work.deleteLater)
    thr.finished.connect(thr.deleteLater)

    thr._worker = work          # ← 1. Сохраняем ссылку (ключевая строчка)
    thr.start()
    
    # 2. (необязательно) держим thread в parent, чтобы и его не съели GC
    if parent is not None:
        lst = getattr(parent, "_active_upd_threads", [])
        lst.append(thr)
        parent._active_upd_threads = lst
        thr.finished.connect(lambda *, l=lst, t=thr: l.remove(t))

    return thr

# вспомогательный setter (чтобы не тянуть status_cb из main окна)
def _safe_set_status(parent, msg: str):
    if parent and hasattr(parent, "set_status"):
        parent.set_status(msg)
    else:
        print(msg)

def _kill_winws():
    """
    Безопасно пытается убить winws.exe (и дочерние),
    чтобы установщик смог заменить файл.
    """
    try:
        # /T = вместе с дочерними; /F = принудительно
        subprocess.run("taskkill /F /IM winws.exe /T",
                       shell=True, check=False,
                       stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL)
        # даём ОС мгновение завершить процесс
    except Exception:
        pass

# ────────────────────────────────────────────────────────────────
def _download(url: str, dest: str, on_progress=None):
    import requests
    r = requests.get(url, stream=True, timeout=TIMEOUT)
    r.raise_for_status()
    total = int(r.headers.get("content-length", 0))
    done = 0
    with open(dest, "wb") as fp:
        for chunk in r.iter_content(8192):
            fp.write(chunk)
            if on_progress and total:
                done += len(chunk)
                on_progress(done, total)

# ────────────────────────────────────────────────────────────────
def check_and_run_update(parent=None, status_cb=None, **kwargs):
    """
    • читает META_URL;
    • если есть новая версия, спрашивает пользователя (если not silent);
    • скачивает Setup.exe → TEMP;
    • запускает его /VERYSILENT и через 1.5 с закрывает Zapret.
    """
    silent = kwargs.get("silent", False)
    
    # Удобный вывод статуса
    def set_status(msg: str):
        if status_cb: status_cb(msg)
        elif parent and hasattr(parent, "set_status"): parent.set_status(msg)
        else: print(msg)

    # ─ step 1.  requests / packaging ────────────────────────────
    try:
        import requests
        from packaging import version
    except ImportError:
        set_status("Устанавливаю зависимости для обновления…")
        subprocess.run([sys.executable, "-m", "pip", "-q",
                        "install", "requests", "packaging"], check=True)
        import requests
        from packaging import version

    # ─ step 2.  meta-файл ───────────────────────────────────────
    try:
        meta = requests.get(META_URL, timeout=TIMEOUT).json()
    except Exception as e:
        from log import log
        log(f"Не удалось проверить обновления: {e}", "ERROR")
        set_status("Не удалось проверить обновления.")
        return False

    new_ver   = meta.get("version")
    upd_url   = meta.get("update_url")
    notes     = meta.get("release_notes", "")

    if not new_ver or not upd_url:
        log("version.json неполон (нет version/update_url).", "DEBUG")
        return False

    from config.config import APP_VERSION
    if version.parse(new_ver) <= version.parse(APP_VERSION):
        msg = f"Обновлений нет (v{APP_VERSION})"
        set_status(msg)                     # ← STATUS ДЛЯ SILENT-РЕЖИМА
        from log import log
        log(f"[Updater] {msg}", "DEBUG")    # ← в лог, чтобы было видно

        if not silent:                      # окно показываем только при ручной проверке
            QMessageBox.information(parent, "Обновление", msg)
        return False
    
    # ─ step 3.  спрашиваем пользователя ────────────────────────
    if not silent:
        txt = (f"Доступна новая версия {new_ver} (у вас {APP_VERSION}).\n\n"
               f"{notes}\n\nУстановить сейчас?")
        if QMessageBox.question(parent, "Доступно обновление",
                                txt, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
            return False

    # ─ step 4.  скачиваем Setup.exe ─────────────────────────────
    tmp_dir   = tempfile.mkdtemp(prefix="zapret_upd_")
    setup_exe = os.path.join(tmp_dir, "ZapretSetup.exe")

    def _prog(done, total): set_status(f"Скачивание… {done*100//total}%")
    try:
        _download(upd_url, setup_exe, _prog if parent else None)
    except Exception as e:
        set_status(f"Ошибка загрузки: {e}")
        shutil.rmtree(tmp_dir, True)
        return False

    # ─ step 5.  запуск установщика ─────────────────────────────
    try:
        from dpi.stop import stop_dpi
        stop_dpi(parent)  # останавливаем winws.exe
        time.sleep(0.5)       # даём время завершиться
        _kill_winws()          # убиваем winws.exe (если не остановился)
        time.sleep(2)
        subprocess.Popen(['cmd', '/c', 'start', '', setup_exe, '/NORESTART'])
        QTimer.singleShot(10, lambda: os._exit(0))
    
    except Exception as e:
        set_status(f"Не удалось запустить установщик: {e}")
        shutil.rmtree(tmp_dir, True)
        return False

    set_status("Запущен установщик обновления…")
    QTimer.singleShot(1500, lambda: sys.exit(0))   # освободить exe-файл
    return True