# tg_log_delta.py

"""
Дельта-лог → Telegram.
• dev-сборки (APP_VERSION начинается с 2025) шлют в отдельного бота.
"""

from __future__ import annotations
import os, sys, uuid, platform, threading, requests, pathlib, winreg, traceback
from datetime import datetime
from typing import Optional
from config import APP_VERSION, CHANNEL # build_info moved to config/__init__.py

# ───────────── определяем, test это или нет ─────────────
IS_DEV_BUILD = True if CHANNEL == "test" else False

# ───────────── cred’ы для двух ботов ───────────────────
#  прод-бот
PROD_TOKEN   = "7541112559:AAHS8aqz-Jq_MqbtNGpH9DHq_UfO-jCJtRM"
PROD_CHAT_ID = 6483277608

#  dev-бот  (создайте своего и вставьте данные)
DEV_TOKEN    = "7508331220:AAFNbBAXKQGwmfbi1ecQ8IBNZv-b1z2W3Kk"
DEV_CHAT_ID  = 6483277608

#  выбираем
TOKEN   = DEV_TOKEN   if IS_DEV_BUILD else PROD_TOKEN
CHAT_ID = DEV_CHAT_ID if IS_DEV_BUILD else PROD_CHAT_ID

# интервалы / лимиты
INTERVAL  = 10
MAX_CHUNK = 3500

# ---------- Client-ID (как было) ------------------------------------
try:
    from PyQt6.QtCore import QTimer
except ImportError:
    QTimer = None

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

# ---------- Telegram helpers ----------------------------------------
API = f"https://api.telegram.org/bot{TOKEN}"

def _async_post(url: str, **kw):
    threading.Thread(
        target=requests.post,
        kwargs=dict(url=url, timeout=30, **kw),
        daemon=True
    ).start()

def _chunks(txt: str, n: int = MAX_CHUNK):
    for i in range(0, len(txt), n):
        yield txt[i:i+n]

def _send(text: str):
    for part in _chunks(text):
        _async_post(
            f"{API}/sendMessage",
            data=dict(
                chat_id=CHAT_ID,
                text=f"<pre>{part}</pre>",
                parse_mode="HTML",
                disable_web_page_preview=True
            )
        )

# ---------- Tail-sender ---------------------------------------------
class LogTailSender:
    def __init__(self, path: str):
        self.path = path
        self.pos  = os.path.getsize(path) if os.path.isfile(path) else 0

    @staticmethod
    def _make_header(lines: int) -> str:
        return (
            "────────\n"
            f"ID  : {CID}\n"
            f"Zapret v{APP_VERSION}\n"
            f"Host: {HOST}\n"
            f"Δ {datetime.now():%H:%M:%S}  ({lines} lines)\n"
            "────────\n"
        )

    def send_delta(self):
        try:
            if not (TOKEN and CHAT_ID):
                return
            if not os.path.isfile(self.path):
                self.pos = 0
                return
            size = os.path.getsize(self.path)
            if size < self.pos:
                self.pos = 0
            if size == self.pos:
                return
            with open(self.path, "r", encoding="utf-8-sig", errors="ignore") as f:
                f.seek(self.pos)
                delta = f.read()
                self.pos = f.tell()
            if not delta.strip():
                return
            header = self._make_header(delta.count("\n") or 1)
            _send(header + delta)
        except Exception as e:
            print("send_delta error:", e)
            traceback.print_exc()

# ---------- Qt-обёртка ----------------------------------------------
class LogDeltaDaemon:
    def __init__(self, log_path: str, interval: int = INTERVAL, parent=None):
        if QTimer is None:
            raise RuntimeError("PyQt6 не установлена")
        if interval < 3:
            raise ValueError("Интервал ≥ 3 сек")
        self.sender = LogTailSender(log_path)
        self.timer  = QTimer(parent)
        self.timer.setInterval(interval * 1000)
        self.timer.timeout.connect(self.sender.send_delta)
        self.timer.start()

# ---------- Доп. функции для ручной отправки ------------------------
from pathlib import Path
import requests
def _tg_api(method: str, files=None, data=None):
    url = f"{API}/{method}"
    r   = requests.post(url, files=files, data=data, timeout=30)
    r.raise_for_status()
    return r.json()

def send_log_to_tg(log_path: str | Path, caption: str = "") -> None:
    path = Path(log_path)
    text = path.read_text(encoding="utf-8-sig", errors="replace")[-4000:]
    data = {
        "chat_id": CHAT_ID,
        "text": (caption + "\n\n" if caption else "") + text,
        "parse_mode": "HTML"
    }
    _tg_api("sendMessage", data=data)

def send_file_to_tg(file_path: str | Path, caption: str = "") -> None:
    from telegram import Bot
    Bot(token=TOKEN).send_document(
        chat_id=CHAT_ID,
        document=open(file_path, "rb"),
        caption=caption or Path(file_path).name
    )