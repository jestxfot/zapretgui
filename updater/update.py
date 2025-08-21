"""
updater/update.py
────────────────────────────────────────────────────────────────
Проверяет GitHub releases и, если в своём канале (stable / dev) 
есть более свежая версия, тихо скачивает установщик, запускает 
его и закрывает программу.
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
    """Старая функция для совместимости"""
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

def _download_with_retry(url: str, dest: str, on_progress: Callable[[int, int], None] | None, 
                         verify_ssl: bool = True, max_retries: int = 3):
    """Скачивание с автоматическими повторными попытками"""
    import requests
    from time import sleep
    
    last_error = None
    
    for attempt in range(max_retries):
        try:
            # Создаем сессию с настройками
            session = requests.Session()
            session.mount('https://', requests.adapters.HTTPAdapter(
                max_retries=requests.adapters.Retry(
                    total=3,
                    backoff_factor=0.3,
                    status_forcelist=[500, 502, 503, 504]
                )
            ))
            
            if not verify_ssl:
                session.verify = False
                import urllib3
                urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            
            # Увеличиваем таймаут для больших файлов
            timeout = (10, 30)  # (connect timeout, read timeout)
            
            log(f"Попытка {attempt + 1}/{max_retries} скачивания с {url}", "🔄 DOWNLOAD")
            
            with session.get(url, stream=True, timeout=timeout, verify=verify_ssl) as resp:
                resp.raise_for_status()
                total = int(resp.headers.get("content-length", 0))
                done = 0
                
                with open(dest, "wb") as fp:
                    for chunk in resp.iter_content(chunk_size=8192):
                        if chunk:
                            fp.write(chunk)
                            if on_progress and total:
                                done += len(chunk)
                                on_progress(done, total)
            
            # Успешно скачали
            log(f"✅ Файл успешно скачан с попытки {attempt + 1}", "🔄 DOWNLOAD")
            return
            
        except requests.exceptions.ConnectionError as e:
            last_error = f"Ошибка подключения: {e}"
            log(f"❌ Попытка {attempt + 1} не удалась: {last_error}", "🔄 DOWNLOAD")
            
        except requests.exceptions.Timeout as e:
            last_error = f"Таймаут подключения: {e}"
            log(f"❌ Попытка {attempt + 1} не удалась: {last_error}", "🔄 DOWNLOAD")
            
        except requests.exceptions.HTTPError as e:
            last_error = f"HTTP ошибка: {e}"
            log(f"❌ Попытка {attempt + 1} не удалась: {last_error}", "🔄 DOWNLOAD")
            
        except Exception as e:
            last_error = f"Неизвестная ошибка: {e}"
            log(f"❌ Попытка {attempt + 1} не удалась: {last_error}", "🔄 DOWNLOAD")
        
        # Пауза перед следующей попыткой (увеличивается с каждой попыткой)
        if attempt < max_retries - 1:
            wait_time = (attempt + 1) * 2
            log(f"⏳ Ожидание {wait_time} сек перед следующей попыткой...", "🔄 DOWNLOAD")
            sleep(wait_time)
    
    # Все попытки исчерпаны
    raise Exception(f"Не удалось скачать файл после {max_retries} попыток. Последняя ошибка: {last_error}")

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
    progress = pyqtSignal(str)        # статус-строка
    progress_value = pyqtSignal(int)  # прогресс загрузки в процентах (0-100)
    progress_bytes = pyqtSignal(int, int, int)  # (percent, downloaded, total) для диалога
    finished = pyqtSignal(bool)       # True – установщик запущен
    ask_user = pyqtSignal(str, str, bool)  # (version, notes, is_prerelease)
    show_no_updates = pyqtSignal(str)  # Сигнал для показа диалога "нет обновлений"
    show_download_dialog = pyqtSignal(str)  # Показать диалог загрузки (version)
    hide_download_dialog = pyqtSignal()  # Скрыть диалог загрузки
    download_complete = pyqtSignal()  # Загрузка завершена
    download_failed = pyqtSignal(str)  # Ошибка загрузки
    retry_download = pyqtSignal()  # Новый сигнал для повторной попытки

    def __init__(self, parent=None, silent: bool = False):
        super().__init__()
        self._parent = parent
        self._silent = silent
        self._should_continue = True
        self._user_response = None
        self._response_event = threading.Event()
        self._retry_requested = False
        self._last_release_info = None  # Сохраняем информацию для повтора

    def set_user_response(self, response: bool):
        """Устанавливает ответ пользователя из UI потока"""
        log(f"UpdateWorker: получен ответ пользователя: {response}", "🔁 UPDATE")
        self._user_response = response
        self._response_event.set()

    def _emit(self, msg: str):
        """Отправляет статус в UI поток"""
        self.progress.emit(msg)

    def _emit_progress(self, percent: int):
        """Отправляет процент загрузки в UI поток"""
        self.progress_value.emit(percent)
    
    def _ask_user_dialog(self, new_ver: str, notes: str, is_pre: bool):
        """Запрашивает у пользователя разрешение на обновление (в UI потоке)"""
        if self._silent:
            # В тихом режиме автоматически соглашаемся на обновление
            log("UpdateWorker: тихий режим - автоматически устанавливаем обновление", "🔁 UPDATE")
            self._user_response = True
            return True
        
        # Сбрасываем предыдущий ответ
        self._user_response = None
        self._response_event.clear()
        
        # Эмитим сигнал для показа диалога в UI потоке
        log(f"UpdateWorker: запрашиваем разрешение пользователя для версии {new_ver}", "🔁 UPDATE")
        self.ask_user.emit(new_ver, notes, is_pre)
        
        # Ждем ответа (максимум 60 секунд)
        if self._response_event.wait(timeout=60):
            log(f"UpdateWorker: ответ получен: {self._user_response}", "🔁 UPDATE")
            return self._user_response
        else:
            log("UpdateWorker: таймаут ожидания ответа пользователя", "🔁 UPDATE")
            return False
    
    def request_retry(self):
        """Запрос на повторную попытку скачивания"""
        self._retry_requested = True
        if self._last_release_info:
            self._download_update(self._last_release_info)
    
    def _get_download_urls(self, release_info: dict) -> list:
        """Формирует список URL для попытки скачивания"""
        urls = []
        upd_url = release_info["update_url"]
        
        # Основной URL
        verify_ssl = release_info.get("verify_ssl", True)
        urls.append((upd_url, verify_ssl))
        
        # Если это GitHub URL, пробуем альтернативные методы
        if "github.com" in upd_url or "githubusercontent.com" in upd_url:
            # Добавляем прокси если есть
            proxy_url = os.getenv("ZAPRET_GITHUB_PROXY")
            if proxy_url:
                proxied_url = upd_url.replace("https://github.com", proxy_url)
                proxied_url = proxied_url.replace("https://github-releases.githubusercontent.com", proxy_url)
                urls.append((proxied_url, False))
        
        # Если есть fallback сервер с файлом
        if release_info.get("source") and "Private" in release_info.get("source", ""):
            # Уже должен быть правильный URL от fallback сервера
            pass
        
        # Если это HTTPS URL с нашего сервера, добавляем HTTP вариант как fallback
        if upd_url.startswith("https://"):
            if "88.210.21.236:888" in upd_url:
                http_url = upd_url.replace("https://", "http://").replace(":888", ":887")
                urls.append((http_url, True))
        
        return urls
    
    def _download_update(self, release_info: dict) -> bool:
        """Отдельный метод для скачивания и установки"""
        new_ver = release_info["version"]
        
        # Показываем диалог загрузки
        log(f"UpdateWorker: показываем диалог загрузки для версии {new_ver}", "🔁 UPDATE")
        self.show_download_dialog.emit(new_ver)
        
        tmp_dir = tempfile.mkdtemp(prefix="zapret_upd_")
        setup_exe = os.path.join(tmp_dir, "ZapretSetup.exe")
        
        def _prog(done, total):
            percent = done * 100 // total if total > 0 else 0
            self.progress_bytes.emit(percent, done, total)
            self._emit(f"Скачивание обновления… {percent}%")
        
        # Формируем список URL для скачивания
        download_urls = self._get_download_urls(release_info)
        
        download_error = None
        for idx, (url, verify_ssl) in enumerate(download_urls):
            try:
                log(f"Попытка скачивания #{idx+1} с {url} (verify_ssl={verify_ssl})", "🔁 UPDATE")
                
                # Используем новую функцию с повторными попытками
                _download_with_retry(url, setup_exe, _prog, verify_ssl=verify_ssl)
                
                # Успешно скачали
                download_error = None
                self.download_complete.emit()
                break
                
            except Exception as e:
                download_error = e
                log(f"❌ Ошибка при скачивании с {url}: {e}", "🔁❌ ERROR")
                
                if idx < len(download_urls) - 1:
                    self._emit("Пробуем альтернативный источник...")
                    time.sleep(1)
        
        if download_error:
            # Сохраняем информацию для возможного повтора
            self._last_release_info = release_info
            
            error_msg = str(download_error)
            if "ConnectionPool" in error_msg or "Connection" in error_msg:
                error_msg = "Ошибка подключения к серверу. Проверьте интернет-соединение."
            
            self.download_failed.emit(error_msg)
            self._emit(f"Ошибка загрузки: {error_msg}")
            shutil.rmtree(tmp_dir, True)
            return False
        
        # Запускаем установщик
        try:
            self._emit("Запуск установщика…")

            setup_args = [setup_exe, "/SILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/CLOSEAPPLICATIONS", "/RESTARTAPPLICATIONS"]

            # Запускаем установщик в тихом режиме с автозапуском после
            run_hidden(["C:\\Windows\\System32\\cmd.exe", "/c", "start", ""] + setup_args, shell=False)
            
            # через 1,5 сек выходим, чтобы Install‐EXE смог перезаписать файлы
            QTimer.singleShot(1500, lambda: os._exit(0))
            return True
            
        except Exception as e:
            self._emit(f"Не удалось запустить установщик: {e}")
            shutil.rmtree(tmp_dir, True)
            return False

    def run(self):
        """Основная логика обновления, выполняется в отдельном потоке"""
        try:
            ok = self._check_and_run_update()
            self.finished.emit(ok)
        except Exception as e:
            log(f"UpdateWorker: ошибка в run(): {e}", "🔁❌ ERROR")
            self._emit(f"Ошибка обновления: {e}")
            self.finished.emit(False)

    def _check_and_run_update(self) -> bool:
        """
        Внутренняя реализация проверки и запуска обновления.
        """
        # — 1. Получаем информацию о последнем релизе --------------------------
        self._emit("Проверка обновлений…")
        
        release_info = get_latest_release(CHANNEL)
        if not release_info:
            self._emit("Не удалось проверить обновления.")
            return False

        new_ver = release_info["version"]
        notes   = release_info["release_notes"]
        is_pre  = release_info["prerelease"]
        
        # Нормализуем текущую версию для корректного сравнения
        try:
            app_ver_norm = normalize_version(APP_VERSION)
        except ValueError:
            log(f"Invalid APP_VERSION format: {APP_VERSION}", "🔁❌ ERROR")
            self._emit("Ошибка версии приложения.")
            return False
        
        log(f"Auto-update: channel={CHANNEL}, local={app_ver_norm}, remote={new_ver}, prerelease={is_pre}", "🔁 UPDATE")

        # Сравниваем версии
        cmp_result = compare_versions(app_ver_norm, new_ver)
        
        log(f"Version comparison: {app_ver_norm} vs {new_ver} = {cmp_result}", "🔁 UPDATE")
        
        if cmp_result >= 0:  # Текущая версия >= новой
            self._emit(f"✅ Обновлений нет (v{app_ver_norm})")
            if not self._silent:
                # Показываем диалог только если НЕ тихий режим
                self.show_no_updates.emit(app_ver_norm)
            return False

        # — 2. спрашиваем пользователя -----------------------------------------
        user_confirmed = self._ask_user_dialog(new_ver, notes, is_pre)
        
        if not user_confirmed:
            self._emit("Обновление отменено пользователем")
            log("UpdateWorker: пользователь отказался от обновления", "🔁 UPDATE")
            return False

        # — 3. Скачиваем и устанавливаем ---------------------------------------
        return self._download_update(release_info)

# ──────────────────────────── public-API ──────────────────────────────────
def run_update_async(parent=None, *, silent: bool = False) -> QThread:
    """
    Создаёт QThread + UpdateWorker для полностью асинхронного обновления.
    
    Args:
        parent: Родительское окно
        silent: Если True, не показывает диалог подтверждения и "нет обновлений",
               но ВСЕГДА показывает диалог загрузки
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
    
    # Переменная для хранения диалога загрузки
    download_dialog = None
    
    # Обработчик показа диалога загрузки - ВСЕГДА показываем
    def show_download_dialog(version):
        nonlocal download_dialog
        if parent:  # Убрали проверку на silent - показываем всегда!
            download_dialog = DownloadDialog(parent, version)
            # Подключаем обновление прогресса
            worker.progress_bytes.connect(
                lambda p, d, t: download_dialog.update_progress(p, d, t) if download_dialog else None
            )
            
            # Подключаем кнопку повтора к воркеру
            download_dialog.retry_requested.connect(worker.request_retry)
            
            # Показываем модально
            download_dialog.show()
            
            # Если это автоматическое обновление, добавляем информацию
            if silent:
                download_dialog.set_status("🔄 Автоматическое обновление Zapret")
                
            log(f"Показан диалог загрузки для версии {version} (silent={silent})", "🔁 UPDATE")
    
    # Обработчик скрытия диалога
    def hide_download_dialog():
        nonlocal download_dialog
        if download_dialog:
            download_dialog.accept()
            download_dialog = None
            log("Диалог загрузки закрыт", "🔁 UPDATE")
    
    # Обработчик завершения загрузки
    def on_download_complete():
        if download_dialog:
            download_dialog.download_complete()
            log("Загрузка завершена успешно", "🔁 UPDATE")
    
    # Обработчик ошибки загрузки
    def on_download_failed(error):
        if download_dialog:
            download_dialog.download_failed(error)
            log(f"Загрузка завершилась с ошибкой: {error}", "🔁 UPDATE")
    
    # Обработчик запроса пользователю (не показываем в silent режиме)
    def handle_user_dialog(new_ver, notes, is_pre):
        """Обработчик диалога в UI потоке"""
        log(f"handle_user_dialog: версия {new_ver}, silent={silent}", "🔁 UPDATE")
        
        if not parent or silent:
            # В тихом режиме автоматически соглашаемся
            log("handle_user_dialog: автоматическое согласие (silent mode)", "🔁 UPDATE")
            worker.set_user_response(True)
            return
        
        try:
            from config import APP_VERSION
            
            version_type = " (предварительная версия)" if is_pre else ""
            txt = (f"Доступна новая версия {new_ver}{version_type} (у вас {APP_VERSION}).\n\n"
                   f"{notes[:500] if notes else 'Обновление содержит исправления и улучшения.'}\n\n"
                   f"Установить сейчас?")
            
            btn = QMessageBox.question(
                parent, "Доступно обновление",
                txt,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            user_accepted = (btn == QMessageBox.StandardButton.Yes)
            log(f"handle_user_dialog: пользователь выбрал: {'Yes' if user_accepted else 'No'}", "🔁 UPDATE")
            worker.set_user_response(user_accepted)
            
        except Exception as e:
            log(f"handle_user_dialog: ошибка показа диалога: {e}", "🔁❌ ERROR")
            worker.set_user_response(False)
    
    # Обработчик диалога "нет обновлений" (не показываем в silent режиме)
    def handle_no_updates_dialog(current_version):
        """Показывает диалог об отсутствии обновлений в UI потоке"""
        if parent and not silent:  # Не показываем в silent режиме
            try:
                QMessageBox.information(
                    parent, 
                    "Обновление", 
                    f"У вас последняя версия ({current_version})."
                )
            except Exception as e:
                log(f"handle_no_updates_dialog: ошибка: {e}", "🔁❌ ERROR")
    
    # Подключаем все сигналы
    worker.ask_user.connect(handle_user_dialog)
    worker.show_no_updates.connect(handle_no_updates_dialog)
    worker.show_download_dialog.connect(show_download_dialog)
    worker.hide_download_dialog.connect(hide_download_dialog)
    worker.download_complete.connect(on_download_complete)
    worker.download_failed.connect(on_download_failed)

    thr._worker = worker
    thr.start()

    # держим thread в parent-окне
    if parent is not None:
        lst = getattr(parent, "_active_upd_threads", [])
        lst.append(thr)
        parent._active_upd_threads = lst
        thr.finished.connect(lambda *, l=lst, t=thr: l.remove(t) if t in l else None)

    return thr