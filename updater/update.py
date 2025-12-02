"""
updater/update.py
────────────────────────────────────────────────────────────────
ОПТИМИЗИРОВАННАЯ ВЕРСИЯ ДЛЯ БЫСТРОГО СКАЧИВАНИЯ
"""
from __future__ import annotations

import os, sys, tempfile, subprocess, shutil, time, requests
import threading
from typing import Callable
from time import sleep

from PyQt6.QtCore    import QObject, QThread, pyqtSignal, QTimer
from PyQt6.QtWidgets import QMessageBox
from packaging import version
from utils import run_hidden

from .release_manager import get_latest_release
from .github_release import normalize_version
from config import CHANNEL, APP_VERSION
from log import log
from .download_dialog import DownloadDialog
from .rate_limiter import UpdateRateLimiter  # ✅ НОВОЕ


TIMEOUT = 15  # Увеличен с 10 до 15 сек для медленных соединений

# ──────────────────────────── вспомогательные утилиты ─────────────────────
def _safe_set_status(parent, msg: str):
    """Пишем в status-label, если она есть; иначе в консоль."""
    if parent and hasattr(parent, "set_status"):
        parent.set_status(msg)
    else:
        print(msg)

def _download_with_retry(url: str, dest: str, on_progress: Callable[[int, int], None] | None, 
                         verify_ssl: bool = True, max_retries: int = 2):
    """
    ОПТИМИЗИРОВАННОЕ скачивание с защитой от повторных загрузок
    """
    import requests
    from time import sleep, time
    import os
    
    # ═══════════════════════════════════════════════════════════
    # ✅ ЗАЩИТА ОТ ПОВТОРНОГО СКАЧИВАНИЯ (в течение 30 секунд)
    # ═══════════════════════════════════════════════════════════
    if os.path.exists(dest):
        file_age = time() - os.path.getmtime(dest)
        file_size = os.path.getsize(dest)
        
        # Если файл скачан недавно И имеет правильный размер (>60MB)
        if file_age < 30 and file_size > 60000000:
            log(
                f"⏭️ Файл уже скачан {int(file_age)}с назад "
                f"({file_size/1024/1024:.1f}MB), повторное скачивание пропущено",
                "🔄 DOWNLOAD"
            )
            return  # НЕ СКАЧИВАЕМ ПОВТОРНО!
    
    last_error = None
    
    for attempt in range(max_retries):
        try:
            session = requests.Session()
            
            session.headers.update({
                'User-Agent': 'Zapret-Updater/3.1',  # ✅ Обновлена версия
                'Accept': 'application/octet-stream',
                'Accept-Encoding': 'identity',
                'Connection': 'keep-alive'
            })
            
            # ✅ УМЕНЬШЕН пул соединений
            adapter = requests.adapters.HTTPAdapter(
                pool_connections=2,
                pool_maxsize=2,
                max_retries=requests.adapters.Retry(
                    total=0,
                    backoff_factor=0,
                    status_forcelist=None
                )
            )
            session.mount('https://', adapter)
            session.mount('http://', adapter)
            
            if not verify_ssl:
                session.verify = False
                import urllib3
                urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            
            log(f"Попытка {attempt + 1}/{max_retries} скачивания", "🔄 DOWNLOAD")
            
            chunk_size = 2097152  # 2MB
            timeout = (10, 90)
            
            # ✅ Resume ТОЛЬКО со второй попытки
            resume_from = 0
            if os.path.exists(dest) and attempt > 0:
                resume_from = os.path.getsize(dest)
                if resume_from > 1048576:  # > 1MB
                    log(f"📥 Возобновление с {resume_from/1024/1024:.1f} МБ", "🔄 DOWNLOAD")
                    session.headers['Range'] = f'bytes={resume_from}-'
                else:
                    resume_from = 0
            
            with session.get(url, stream=True, timeout=timeout, verify=verify_ssl) as resp:
                resp.raise_for_status()
                
                if resp.status_code == 206:
                    content_range = resp.headers.get('Content-Range', '')
                    if content_range:
                        total = int(content_range.split('/')[-1])
                    else:
                        total = resume_from + int(resp.headers.get("content-length", 0))
                else:
                    total = int(resp.headers.get("content-length", 0))
                    resume_from = 0
                
                done = resume_from
                
                if total > 0:
                    log(f"📦 Размер: {total/(1024*1024):.1f} MB", "🔄 DOWNLOAD")
                
                last_update_time = 0
                update_interval = 2.0
                
                mode = "ab" if resume_from > 0 else "wb"
                
                with open(dest, mode, buffering=4194304) as fp:
                    start_time = time()
                    
                    try:
                        for chunk in resp.iter_content(chunk_size=chunk_size):
                            if chunk:
                                fp.write(chunk)
                                done += len(chunk)
                                
                                current_time = time()
                                if on_progress and total:
                                    if (current_time - last_update_time) >= update_interval:
                                        on_progress(done, total)
                                        last_update_time = current_time
                        
                        if on_progress and total:
                            on_progress(total, total)
                        
                        elapsed = time() - start_time
                        if elapsed > 0 and total > 0:
                            avg_speed = ((done - resume_from) / elapsed) / (1024 * 1024)
                            log(f"✅ Скачано {total/(1024*1024):.1f} MB за {elapsed:.1f}с ({avg_speed:.2f} MB/s)", "🔄 DOWNLOAD")
                        
                    except requests.exceptions.ChunkedEncodingError as e:
                        raise requests.exceptions.ConnectionError(f"Incomplete download: {e}")
            
            # ✅ Проверяем размер файла
            if os.path.exists(dest):
                actual_size = os.path.getsize(dest)
                if total > 0 and actual_size != total:
                    raise Exception(f"Размер не совпадает: {actual_size} != {total}")
                
                # ✅ Устанавливаем время модификации файла для защиты
                os.utime(dest, None)  # Обновляем mtime
            
            log(f"✅ Файл скачан с попытки {attempt + 1}", "🔄 DOWNLOAD")
            return
            
        except Exception as e:
            last_error = str(e)
            log(f"❌ Попытка {attempt + 1} не удалась: {last_error}", "🔄 DOWNLOAD")
        
        # Удаляем файл если не resume-able ошибка
        if os.path.exists(dest) and "Incomplete download" not in str(last_error):
            try:
                os.remove(dest)
            except:
                pass
        
        if attempt < max_retries - 1:
            wait_time = min(2 ** (attempt + 1), 30)
            log(f"⏳ Ожидание {wait_time}с перед повтором...", "🔄 DOWNLOAD")
            sleep(wait_time)
    
    raise Exception(f"Не удалось скачать после {max_retries} попыток. Ошибка: {last_error}")

def compare_versions(v1: str, v2: str) -> int:
    """Сравнивает две версии"""
    from packaging import version
    
    try:
        v1_norm = normalize_version(v1)
        v2_norm = normalize_version(v2)
        
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
        return -1 if v1 < v2 else (1 if v1 > v2 else 0)

# ──────────────────────────── фоновой воркер ──────────────────────────────
class UpdateWorker(QObject):
    progress = pyqtSignal(str)
    progress_value = pyqtSignal(int)
    progress_bytes = pyqtSignal(int, int, int)
    finished = pyqtSignal(bool)
    ask_user = pyqtSignal(str, str, bool)
    show_no_updates = pyqtSignal(str)
    show_download_dialog = pyqtSignal(str)
    hide_download_dialog = pyqtSignal()
    download_complete = pyqtSignal()
    download_failed = pyqtSignal(str)
    retry_download = pyqtSignal()

    def __init__(self, parent=None, silent: bool = False):
        super().__init__()
        self._parent = parent
        self._silent = silent
        self._should_continue = True
        self._user_response = None
        self._response_event = threading.Event()
        self._retry_requested = False
        self._last_release_info = None

    def set_user_response(self, response: bool):
        log(f"UpdateWorker: получен ответ: {response}", "🔁 UPDATE")
        self._user_response = response
        self._response_event.set()

    def _emit(self, msg: str):
        self.progress.emit(msg)

    def _emit_progress(self, percent: int):
        self.progress_value.emit(percent)
    
    def _ask_user_dialog(self, new_ver: str, notes: str, is_pre: bool):
        if self._silent:
            log("UpdateWorker: тихий режим - автоустановка", "🔁 UPDATE")
            self._user_response = True
            return True
        
        self._user_response = None
        self._response_event.clear()
        
        log(f"UpdateWorker: запрос разрешения для v{new_ver}", "🔁 UPDATE")
        self.ask_user.emit(new_ver, notes, is_pre)
        
        if self._response_event.wait(timeout=60):
            log(f"UpdateWorker: ответ получен: {self._user_response}", "🔁 UPDATE")
            return self._user_response
        else:
            log("UpdateWorker: таймаут ожидания ответа", "🔁 UPDATE")
            return False
    
    def request_retry(self):
        self._retry_requested = True
        if self._last_release_info:
            self._download_update(self._last_release_info, is_retry=True)
    
    def _get_download_urls(self, release_info: dict) -> list:
        """Формирует список URL в порядке приоритета"""
        urls = []
        upd_url = release_info["update_url"]
        verify_ssl = release_info.get("verify_ssl", True)
        
        # 1. Основной URL
        urls.append((upd_url, verify_ssl))
        
        # 2. Если это GitHub, добавляем прокси если есть
        if "github.com" in upd_url or "githubusercontent.com" in upd_url:
            proxy_url = os.getenv("ZAPRET_GITHUB_PROXY")
            if proxy_url:
                proxied = upd_url.replace("https://github.com", proxy_url)
                proxied = proxied.replace("https://github-releases.githubusercontent.com", proxy_url)
                urls.append((proxied, False))
        
        return urls
    
    def _download_update(self, release_info: dict, is_retry: bool = False) -> bool:
        new_ver = release_info["version"]
        
        if not is_retry:
            log(f"UpdateWorker: показываем диалог загрузки v{new_ver}", "🔁 UPDATE")
            self.show_download_dialog.emit(new_ver)
        else:
            log(f"UpdateWorker: retry - используем существующий диалог", "🔁 UPDATE")
        
        tmp_dir = tempfile.mkdtemp(prefix="zapret_upd_")
        setup_exe = os.path.join(tmp_dir, "Zapret2Setup.exe")
        
        def _prog(done, total):
            percent = done * 100 // total if total > 0 else 0
            self.progress_bytes.emit(percent, done, total)
            self._emit(f"Скачивание… {percent}%")
        
        download_urls = self._get_download_urls(release_info)
        
        download_error = None
        for idx, (url, verify_ssl) in enumerate(download_urls):
            try:
                log(f"Попытка #{idx+1} с {url} (SSL={verify_ssl})", "🔁 UPDATE")
                
                # Для тихих автообновлений не долбим сервер — максимум 1 попытка,
                # для ручного режима можно 2.
                retries = 1 if self._silent else 2
                
                _download_with_retry(
                    url,
                    setup_exe,
                    _prog,
                    verify_ssl=verify_ssl,
                    max_retries=retries
                )
                
                download_error = None
                self.download_complete.emit()
                break
                
            except Exception as e:
                download_error = e
                log(f"❌ Ошибка: {e}", "🔁❌ ERROR")
                
                if idx < len(download_urls) - 1:
                    self._emit("Пробуем альтернативный источник...")
                    time.sleep(1)
        
        if download_error:
            self._last_release_info = release_info
            
            error_msg = str(download_error)
            if "ConnectionPool" in error_msg or "Connection" in error_msg:
                error_msg = "Ошибка подключения. Проверьте интернет."
            
            self.download_failed.emit(error_msg)
            self._emit(f"Ошибка: {error_msg}")
            shutil.rmtree(tmp_dir, True)
            return False
        
        # Запуск установщика
        try:
            self._emit("Запуск установщика…")

            # ✅ ИСПРАВЛЕНО: убрали /CLOSEAPPLICATIONS чтобы не убивать процесс
            setup_args = [
                setup_exe,
                "/SILENT",              # Тихая установка
                "/SUPPRESSMSGBOXES",    # Без диалогов
                "/NORESTART",           # Не перезагружать систему
                "/NOCANCEL",            # Нельзя отменить
                "/DIR=" + os.path.dirname(sys.executable)  # Установить в ту же папку
            ]

            # ✅ Запускаем установщик
            log(f"🚀 Запуск: {' '.join(setup_args)}", "🔁 UPDATE")
            
            run_hidden(
                ["C:\\Windows\\System32\\cmd.exe", "/c", "start", ""] + setup_args, 
                shell=False
            )
            
            # ✅ Закрываем приложение через 2 секунды (даем время установщику запуститься)
            log("⏳ Закрытие через 2с для установки обновления...", "🔁 UPDATE")
            QTimer.singleShot(2000, lambda: os._exit(0))
            
            return True
            
        except Exception as e:
            self._emit(f"Ошибка запуска: {e}")
            log(f"❌ Ошибка запуска установщика: {e}", "🔁❌ ERROR")
            shutil.rmtree(tmp_dir, True)
            return False

    def run(self):
        try:
            ok = self._check_and_run_update()
            self.finished.emit(ok)
        except Exception as e:
            log(f"UpdateWorker error: {e}", "🔁❌ ERROR")
            self._emit(f"Ошибка: {e}")
            self.finished.emit(False)

    def _check_and_run_update(self) -> bool:
        self._emit("Проверка обновлений…")
        
        # ═══════════════════════════════════════════════════════════════
        # ✅ ПРОВЕРКА RATE LIMIT
        # ═══════════════════════════════════════════════════════════════
        is_auto = self._silent
        can_check, error_msg = UpdateRateLimiter.can_check_update(is_auto=is_auto)
        
        if not can_check:
            self._emit(error_msg)
            log(f"⏱️ Проверка заблокирована rate limiter: {error_msg}", "🔁 UPDATE")
            
            # Для ручных проверок показываем сообщение (кроме dev/test версий)
            if not self._silent and CHANNEL not in ('dev', 'test'):
                self.show_no_updates.emit(f"Rate limit: {error_msg}")
            
            return False
        
        # Записываем факт проверки
        UpdateRateLimiter.record_check(is_auto=is_auto)
        
        # ✅ АВТООБНОВЛЕНИЯ ИСПОЛЬЗУЮТ КЭШ, РУЧНЫЕ - НЕТ
        use_cache = self._silent  # silent=True для автопроверок
        
        if not use_cache:
            log("🔄 Принудительная проверка обновлений (кэш игнорируется)", "🔁 UPDATE")
        
        release_info = get_latest_release(CHANNEL, use_cache=use_cache)
        
        if not release_info:
            self._emit("Не удалось проверить обновления.")
            return False

        new_ver = release_info["version"]
        notes   = release_info["release_notes"]
        is_pre  = release_info["prerelease"]
        
        try:
            app_ver_norm = normalize_version(APP_VERSION)
        except ValueError:
            log(f"Invalid APP_VERSION: {APP_VERSION}", "🔁❌ ERROR")
            self._emit("Ошибка версии.")
            return False
        
        log(f"Update check: {CHANNEL}, local={app_ver_norm}, remote={new_ver}, use_cache={use_cache}", "🔁 UPDATE")

        cmp_result = compare_versions(app_ver_norm, new_ver)
        
        if cmp_result >= 0:
            self._emit(f"✅ Обновлений нет (v{app_ver_norm})")
            if not self._silent:
                self.show_no_updates.emit(app_ver_norm)
            return False

        user_confirmed = self._ask_user_dialog(new_ver, notes, is_pre)
        
        if not user_confirmed:
            self._emit("Обновление отменено")
            return False

        return self._download_update(release_info)

# ──────────────────────────── public-API ──────────────────────────────────
def run_update_async(parent=None, *, silent: bool = False) -> QThread:
    """Запускает асинхронное обновление"""
    thr = QThread(parent)
    worker = UpdateWorker(parent, silent)
    worker.moveToThread(thr)

    thr.started.connect(worker.run)
    worker.finished.connect(thr.quit)
    worker.finished.connect(worker.deleteLater)
    thr.finished.connect(thr.deleteLater)

    worker.progress.connect(lambda m: _safe_set_status(parent, m))
    worker.progress.connect(lambda m: log(f'{m}', "🔁 UPDATE"))
    
    download_dialog = None
    
    def show_download_dialog(version):
        nonlocal download_dialog
        
        if download_dialog is not None:
            try:
                log("Закрываем старый диалог", "🔁 UPDATE")
                download_dialog.close()
                download_dialog.deleteLater()
                download_dialog = None
            except Exception as e:
                log(f"Ошибка закрытия: {e}", "🔁 UPDATE")
        
        if parent:
            download_dialog = DownloadDialog(parent, version)
            
            worker.progress_bytes.connect(
                lambda p, d, t: download_dialog.update_progress(p, d, t) if download_dialog else None
            )
            
            download_dialog.retry_requested.connect(worker.request_retry)
            download_dialog.show()
            
            if silent:
                download_dialog.set_status("🔄 Автообновление Zapret")
                
            log(f"Показан диалог для v{version} (silent={silent})", "🔁 UPDATE")
    
    def hide_download_dialog():
        nonlocal download_dialog
        if download_dialog:
            download_dialog.accept()
            download_dialog = None
    
    def on_download_complete():
        if download_dialog:
            download_dialog.download_complete()
    
    def on_download_failed(error):
        if download_dialog:
            download_dialog.download_failed(error)
    
    def handle_user_dialog(new_ver, notes, is_pre):
        if not parent or silent:
            worker.set_user_response(True)
            return
        
        try:  
            version_type = " (предварительная)" if is_pre else ""
            txt = (f"Доступна новая версия {new_ver}{version_type} (у вас {APP_VERSION}).\n\n"
                   f"{notes[:500] if notes else 'Обновление содержит исправления.'}\n\n"
                   f"Установить?")
            
            btn = QMessageBox.question(
                parent, "Обновление",
                txt,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            worker.set_user_response(btn == QMessageBox.StandardButton.Yes)
            
        except Exception as e:
            log(f"Ошибка диалога: {e}", "🔁❌ ERROR")
            worker.set_user_response(False)
    
    def handle_no_updates_dialog(current_version):
        if parent and not silent:
            try:
                QMessageBox.information(
                    parent, 
                    "Обновление", 
                    f"У вас последняя версия ({current_version})."
                )
            except Exception as e:
                log(f"Ошибка: {e}", "🔁❌ ERROR")
    
    worker.ask_user.connect(handle_user_dialog)
    worker.show_no_updates.connect(handle_no_updates_dialog)
    worker.show_download_dialog.connect(show_download_dialog)
    worker.hide_download_dialog.connect(hide_download_dialog)
    worker.download_complete.connect(on_download_complete)
    worker.download_failed.connect(on_download_failed)

    thr._worker = worker
    thr.start()

    if parent is not None:
        lst = getattr(parent, "_active_upd_threads", [])
        lst.append(thr)
        parent._active_upd_threads = lst
        thr.finished.connect(lambda *, l=lst, t=thr: l.remove(t) if t in l else None)

    return thr