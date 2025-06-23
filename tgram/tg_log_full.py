"""
tgram/tg_log_full.py
────────────────────
Демон, который периодически шлёт файл лога в Telegram-бота.

Новое:
    • отправка выполняется в отдельном QThread (не блокирует GUI);
    • Flood-wait (429) обрабатывается в tgram/tg_sender.send_file_to_tg →
      если был 429 – демон делает паузу ещё на 60 с поверх ответа сервера.
"""

from __future__ import annotations

import hashlib
import io
import os
import platform
import time
from pathlib import Path

from PyQt6.QtCore import QObject, QThread, QTimer, pyqtSignal

from config import APP_VERSION # build_info moved to config/__init__.py
from log import log
from tgram import get_client_id            # UUID устройства


# ──────────────────────────────────────────────────────────────────
def _file_hash(path: str) -> str:
    """
    MD5 из первых и последних 64 КБ – быстро, но надёжно,
    достаточно для проверки «файл изменился?».
    """
    h = hashlib.md5()
    with open(path, "rb") as f:
        first = f.read(64 * 1024)
        if len(first) < 64 * 1024:          # маленький файл
            h.update(first)
            return h.hexdigest()

        f.seek(-64 * 1024, io.SEEK_END)
        last = f.read(64 * 1024)

    h.update(first)
    h.update(last)
    return h.hexdigest()


# ──────────────────────────────────────────────────────────────────
class TgSendWorker(QObject):
    """Воркер, работающий в отдельном потоке: отправляет один файл."""
    finished = pyqtSignal(bool, float)      # ok, extra_wait_seconds

    def __init__(self, path: str, caption: str):
        super().__init__()
        self._path = path
        self._cap = caption

    def run(self):
        from tgram import send_file_to_tg
        try:
            ok = send_file_to_tg(self._path, self._cap)
            self.finished.emit(ok, 0.0)
        except Exception as e:
            # send_file_to_tg уже залогировал; если это flood-wait,
            # функция внутри сама ждала, но мы дадим ещё 60 с запаса
            log(f"[FullLogDaemon] worker error: {e}", "ERROR")
            self.finished.emit(False, 60.0)


# ──────────────────────────────────────────────────────────────────
class FullLogDaemon(QObject):
    """
    Отправляет «полный» лог-файл в TG:
      • каждые interval секунд;
      • только если файл изменился;
      • в caption – доп. инфо + последние ERROR-строки.
    """

    def __init__(self, log_path: str, interval: int = 120, parent=None):
        super().__init__(parent)

        self.log_path = Path(log_path).absolute()
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.log_path.touch(exist_ok=True)

        # снимок предыдущего состояния
        self.last_hash = None
        self.last_line_count = 0

        # если был Flood-wait – ждём до этого времени
        self._suspend_until = 0.0
        # ссылка на активный поток отправки
        self._busy_thread: QThread | None = None

        # начальный snapshot
        self._snapshot(first_time=True)

        # таймер опроса
        self.timer = QTimer(self)
        self.timer.setInterval(interval * 1000)
        self.timer.timeout.connect(self._tick)
        self.timer.start()

    # ───────────────────────────────────────────────────────────
    def _tick(self):
        # пауза после flood-wait
        if time.time() < self._suspend_until:
            return

        # уже идёт отправка
        if self._busy_thread is not None:
            return

        changed, added, added_lines = self._snapshot()
        if not changed:
            return

        # ---- формируем caption --------------------------------
        error_lines = [ln for ln in added_lines if "[ERROR]" in ln]

        caption_parts = [
            "📄 Полный лог Zapret",
            f"Zapret v{APP_VERSION}",
            f"Host: {platform.node()}",
            f"🆔 {get_client_id()}",
            f"🕒 {time.strftime('%d.%m.%Y %H:%M:%S')}",
            f"➕ {added} строк(и)",
        ]

        if error_lines:
            snippet = "\n".join(error_lines[-3:])
            # Telegram: caption ≤ 1024 символа
            caption_parts.append("⚠️ ERROR:\n" + snippet[-800:])

        caption = "\n".join(caption_parts)

        # ---- запускаем воркер в потоке -------------------------
        thread = QThread(self)
        worker = TgSendWorker(str(self.log_path), caption)
        worker.moveToThread(thread)

        thread.started.connect(worker.run)

        def _on_done(ok: bool, extra_wait: float):
            if not ok:
                self._suspend_until = time.time() + extra_wait
            worker.deleteLater()
            thread.quit()
            thread.wait()
            self._busy_thread = None

        worker.finished.connect(_on_done)

        self._busy_thread = thread
        thread.start()

    # ───────────────────────────────────────────────────────────
    def _snapshot(self, *, first_time=False):
        """
        Возвращает: changed?, added_count, added_lines_list
        """
        added_lines: list[str] = []
        line_count = 0

        with self.log_path.open("r", encoding="utf-8", errors="replace") as f:
            for idx, line in enumerate(f, 1):
                if idx > self.last_line_count:
                    added_lines.append(line.rstrip("\n"))
                line_count = idx

        file_hash = _file_hash(str(self.log_path))

        if first_time:
            self.last_hash = file_hash
            self.last_line_count = line_count
            return False, 0, []

        # ротация? строк стало меньше
        if line_count < self.last_line_count:
            added_lines = self._read_all_lines()
            added = line_count
            changed = True
        else:
            added = line_count - self.last_line_count
            changed = (file_hash != self.last_hash)

        if changed:
            self.last_hash = file_hash
            self.last_line_count = line_count

        return changed, added, added_lines

    # ----------------------------------------------------------------
    def _read_all_lines(self) -> list[str]:
        with self.log_path.open("r", encoding="utf-8", errors="replace") as f:
            return [ln.rstrip("\n") for ln in f]