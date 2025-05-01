# tg_log_delta.py
"""
Отправляем «дельту» лога Zapret в Telegram-бота.
• Каждые INTERVAL секунд читаем ТОЛЬКО новые строки.
• В шапке сообщения — UUID клиента + имя ПК → легко различать, чей лог.
"""

# ──────────────── настройки ────────────────
TOKEN     = "7541112559:AAHS8aqz-Jq_MqbtNGpH9DHq_UfO-jCJtRM"
CHAT_ID   = 6483277608
INTERVAL  = 10       # секунд  (≥3, чтобы не словить flood-ban)
MAX_CHUNK = 3500     # символов на сообщение (<4096 c запасом)
# ────────────────────────────────────────────

import os, sys, uuid, platform, threading, requests, pathlib, winreg, traceback
from datetime import datetime
from typing import Optional
from config import APP_VERSION

try:
    from PyQt5.QtCore import QTimer
except ImportError:
    QTimer = None      # чтобы модуль можно было импортировать без PyQt5

# ---------- Client-ID (тот же, что в реестре / файле) ----------

def _reg_get() -> Optional[str]:
    try:
        k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Zapret")
        cid, _ = winreg.QueryValueEx(k, "ClientID")
        return cid
    except Exception:
        return None

def _reg_set(cid: str):
    k = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Zapret")
    winreg.SetValueEx(k, "ClientID", 0, winreg.REG_SZ, cid)

def get_client_id() -> str:
    if sys.platform.startswith("win"):
        cid = _reg_get()
        if cid:
            return cid
        cid = str(uuid.uuid4())
        _reg_set(cid)
        return cid

    path = pathlib.Path.home() / ".zapret_client_id"
    if path.exists():
        return path.read_text().strip()
    cid = str(uuid.uuid4())
    path.write_text(cid)
    return cid

CID  = get_client_id()
HOST = platform.node() or "unknown-pc"

# ---------- Telegram helpers -----------------------------------

API = f"https://api.telegram.org/bot{TOKEN}"

def _async_post(url: str, **kw):
    threading.Thread(
        target=requests.post,
        kwargs=dict(url=url, timeout=30, **kw),
        daemon=True).start()

def _chunks(txt: str, n: int = MAX_CHUNK):
    for i in range(0, len(txt), n):
        yield txt[i:i+n]

def _send(text: str):
    for part in _chunks(text):
        _async_post(
            f"{API}/sendMessage",
            data=dict(chat_id=CHAT_ID,
                      text=f"<pre>{part}</pre>",
                      parse_mode="HTML",
                      disable_web_page_preview=True))

# ---------- отправитель «дельты» --------------------------------

class LogTailSender:
    """
    Каждые N секунд отправляет новые строки файла `path`.
    """
    def __init__(self, path: str):
        self.path = path
        self.pos  = os.path.getsize(path) if os.path.isfile(path) else 0

    # формируем «шапку» с ID / host / временем
    @staticmethod
    def _make_header(lines: int) -> str:
        return (
            "────────\n"
            f"ID  : {CID}\n"
            f"Zapret v{APP_VERSION}\n"       # ← новая строка
            f"Host: {HOST}\n"
            f"Δ {datetime.now():%H:%M:%S}  ({lines} lines)\n"
            "────────\n"
        )

    def send_delta(self):
        """Читает добавленные байты и шлёт их (если они есть)."""
        try:
            if not (TOKEN and CHAT_ID):
                return

            if not os.path.isfile(self.path):
                self.pos = 0
                return

            size = os.path.getsize(self.path)

            # лог был ротирован / обнулён
            if size < self.pos:
                self.pos = 0

            if size == self.pos:           # новых данных нет
                return

            with open(self.path, "r", encoding="utf-8", errors="ignore") as f:
                f.seek(self.pos)
                delta = f.read()
                self.pos = f.tell()

            if not delta.strip():
                return

            lines_cnt = delta.count("\n") or 1
            header = self._make_header(lines_cnt)
            _send(header + delta)

        except Exception as e:
            # Логируем локально, чтобы не потерять информацию
            print("send_delta error:", e)
            traceback.print_exc()

# ---------- QTimer-обёртка --------------------------------------

class LogDeltaDaemon:
    """
    Создайте один экземпляр – и он будет слать «дельту» каждые `interval` сек.
    parent – любой QObject (окно / QApplication), чтобы таймер автоматически
    уничтожался при закрытии GUI.
    """
    def __init__(self, log_path: str, interval: int = INTERVAL, parent=None):
        if QTimer is None:
            raise RuntimeError("PyQt5 не установлена – LogDeltaDaemon недоступен")

        if interval < 3:
            raise ValueError("Интервал должен быть ≥ 3 сек (флуд-лимит Telegram)")

        self.sender = LogTailSender(log_path)

        self.timer = QTimer(parent)
        self.timer.setInterval(interval * 1000)
        self.timer.timeout.connect(self.sender.send_delta)
        self.timer.start()

        # Первая проверка через interval секунд, чтобы не слать весь старый лог