# tg_log_full.py
import os, time, platform
from PyQt6.QtCore import QObject, QTimer

from log import log
from tg_sender import send_file_to_tg
from tg_log_delta import get_client_id          # UUID устройства
from config import APP_VERSION                  # ← версия Zapret

def _file_hash(path: str) -> str:
    """
    Быстрый MD5 из первых+последних 64 КБ – хватает, чтобы понять
    «менялся ли файл» и при этом считать хэш за миллисекунды.
    """
    import hashlib, io
    h = hashlib.md5()
    with open(path, "rb") as f:
        first = f.read(64 * 1024)
        if len(first) < 64 * 1024:      # мелкий файл
            h.update(first)
            return h.hexdigest()

        f.seek(-64 * 1024, io.SEEK_END)
        last = f.read(64 * 1024)
    h.update(first); h.update(last)
    return h.hexdigest()

class FullLogDaemon(QObject):
    """
    Демон, отсылающий файл лога в TG:
      • каждые interval секунд;
      • только если файл изменился;
      • показывает, сколько строк добавилось и
        последние добавленные строки с [ERROR].
    """
    def __init__(self, log_path: str, interval: int = 120, parent=None):
        super().__init__(parent)

        self.log_path = os.path.abspath(log_path)
        os.makedirs(os.path.dirname(self.log_path) or ".", exist_ok=True)
        if not os.path.isfile(self.log_path):
            open(self.log_path, "a", encoding="utf-8").close()

        # «снимки» прошлого состояния
        self.last_hash        = None
        self.last_line_count  = 0

        # берём начальный «снимок»
        self._snapshot(first_time=True)

        # таймер
        self.timer = QTimer(self)
        self.timer.setInterval(interval * 1000)
        self.timer.timeout.connect(self._tick)
        self.timer.start()

    # ───────────────────────────────────────────────────────────
    def _tick(self):
        try:
            changed, added, added_lines = self._snapshot()
            if not changed:
                return  # лог не изменился

            # Ищем ERROR-строки только в добавившихся строках
            error_lines = [ln for ln in added_lines if "[ERROR]" in ln]

            ts   = time.strftime("%d.%m.%Y %H:%M:%S")
            cid  = get_client_id()
            host = platform.node()

            caption_parts = [
                "📄 Полный лог Zapret",
                f"Zapret v{APP_VERSION}",
                f"Host: {host}",
                f"🆔 {cid}",
                f"🕒 {ts}",
                f"➕ {added} строк(и)"
            ]

            if error_lines:
                # берём максимум 3 последних error-строки
                snippet = "\n".join(error_lines[-3:])
                # Telegram caption ≤ 1024 символа, обрежем при необходимости
                if len(snippet) > 800:
                    snippet = snippet[-800:]
                caption_parts.append("⚠️ ERROR:\n" + snippet)

            caption = "\n".join(caption_parts)

            send_file_to_tg(self.log_path, caption)
        except Exception as e:
            log(f"[FullLogDaemon] ошибка: {e}", level="ERROR")

    # ───────────────────────────────────────────────────────────
    def _snapshot(self, *, first_time=False):
        """
        Возвращает (изменился?, сколько_добавилось, список_добавленных_строк)
        """
        added_lines = []
        line_count  = 0

        # читаем файл построчно, копим новые строки при необходимости
        with open(self.log_path, "r", encoding="utf-8", errors="replace") as f:
            for idx, line in enumerate(f, 1):
                if idx > self.last_line_count:
                    added_lines.append(line.rstrip("\n"))
                line_count = idx

        file_hash = _file_hash(self.log_path)

        if first_time:
            self.last_hash       = file_hash
            self.last_line_count = line_count
            return False, 0, []

        # ротация? если строк стало меньше – считаем весь файл «новым»
        if line_count < self.last_line_count:
            added_lines = self._read_all_lines()
            added       = line_count
            changed     = True
        else:
            added       = line_count - self.last_line_count
            changed     = (file_hash != self.last_hash)

        if changed:
            self.last_hash       = file_hash
            self.last_line_count = line_count

        return changed, added, added_lines

    # чтение всего файла (при ротации)
    def _read_all_lines(self):
        with open(self.log_path, "r", encoding="utf-8", errors="replace") as f:
            return [ln.rstrip("\n") for ln in f]