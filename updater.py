# update.py
# -----------------------------------------------------------------
# Проверяет https://gitflic.ru/.../version.json и, если версия новее,
# качает ZapretSetup.exe, запускает его /VERYSILENT и закрывает программу.
# -----------------------------------------------------------------
import os, sys, tempfile, subprocess, shutil, time
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtCore    import QTimer
from start import DPIStarter

META_URL = "https://gitflic.ru/project/main1234/main1234/blob/raw?file=version.json"          # <- ваш JSON
TIMEOUT  = 10                                      # сек.

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
def check_and_run_update(parent=None, status_cb=None, slient=False):
    """
    • читает META_URL;
    • если есть новая версия, спрашивает пользователя (если not silent);
    • скачивает Setup.exe → TEMP;
    • запускает его /VERYSILENT и через 1.5 с закрывает Zapret.
    """
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
        log(f"Не удалось проверить обновления: {e}")
        set_status("Не удалось проверить обновления.")
        return False

    new_ver   = meta.get("version")
    upd_url   = meta.get("update_url")
    notes     = meta.get("release_notes", "")

    if not new_ver or not upd_url:
        set_status("version.json неполон (нет version/update_url).")
        return False

    from config import APP_VERSION
    if version.parse(new_ver) <= version.parse(APP_VERSION):
        if not silent:
            QMessageBox.information(parent, "Обновление",
                                     f"У вас установлена последняя версия {APP_VERSION}.")
        return False

    # ─ step 3.  спрашиваем пользователя ────────────────────────
    if not silent:
        txt = (f"Доступна новая версия {new_ver} (у вас {APP_VERSION}).\n\n"
               f"{notes}\n\nУстановить сейчас?")
        if QMessageBox.question(parent, "Доступно обновление",
                                txt, QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
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
        from stop import stop_dpi
        stop_dpi()
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