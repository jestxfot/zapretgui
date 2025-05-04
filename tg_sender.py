#  tg_sender.py  (положите рядом с остальными модулями)
from pathlib import Path
from telegram import Bot
import requests

from tg_log_delta import TOKEN, CHAT_ID, _tg_api as call_tg_api

TIMEOUT       = 30

bot = Bot(token=TOKEN)

def _call_tg_api(method: str, files=None, data=None):
    """Небольшой хелпер для вызова Telegram Bot API"""
    url = f"https://api.telegram.org/bot{TOKEN}/{method}"
    r   = requests.post(url, files=files, data=data, timeout=TIMEOUT)
    r.raise_for_status()          # если не 200 ⇒ вызовем исключение
    return r.json()


def send_log_to_tg(log_path: str | Path, caption: str = "") -> None:
    """
    Отправляет содержимое лог-файла ТЕКСТОВЫМ сообщением.
    Хорошо, когда лог небольшой (≤ 4000 символов).
    """
    path = Path(log_path)
    if not path.exists():
        raise FileNotFoundError(f"{path} not found")

    text = path.read_text(encoding="utf-8", errors="replace")
    # Чтобы не выйти за лимит в 4096 симв. – можно обрезать
    if len(text) > 4000:
        text = text[-4000:]                         # последние 4k

    data = {
        "chat_id" : CHAT_ID,
        "text"    : (caption + "\n\n" if caption else "") + text,
        "parse_mode": "HTML"
    }
    _call_tg_api("sendMessage", data=data)

# уже есть send_log_to_tg(text)  ? оставляем
def send_file_to_tg(file_path: str | Path, caption: str = "") -> None:
    """Шлём document в TG."""
    file_path = Path(file_path)
    with file_path.open("rb") as f:
        bot.send_document(
            chat_id=CHAT_ID,
            document=f,
            caption=caption or file_path.name
        )