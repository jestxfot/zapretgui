#!/usr/bin/env python3

import os
import sys
from pathlib import Path


def _bootstrap_dotenv() -> None:
    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    try:
        from utils.dotenv import load_dotenv  # type: ignore
    except Exception:
        load_dotenv = None

    if load_dotenv is not None:
        load_dotenv(root / ".env", root / "build_zapret" / ".env")


def _load_api_creds() -> tuple[int, str]:
    api_id = (os.getenv("TELEGRAM_API_ID") or os.getenv("ZAPRET_TELEGRAM_API_ID") or "").strip()
    api_hash = (os.getenv("TELEGRAM_API_HASH") or os.getenv("ZAPRET_TELEGRAM_API_HASH") or "").strip()
    if not api_id or not api_hash:
        raise RuntimeError(
            "Missing Telegram API credentials. Set TELEGRAM_API_ID and TELEGRAM_API_HASH (or ZAPRET_* variants)."
        )
    try:
        return int(api_id), api_hash
    except Exception as e:
        raise RuntimeError(f"TELEGRAM_API_ID must be an integer: {e}")


async def _run() -> int:
    _bootstrap_dotenv()

    try:
        from telethon import TelegramClient  # type: ignore
    except Exception as e:
        print(f"telethon is not available: {e}")
        print("Install dependencies: pip install -r requirements.txt")
        return 2

    api_id, api_hash = _load_api_creds()
    session_base = Path(__file__).resolve().parent / "zapret_uploader"
    print("Telegram auth (Telethon)")
    print(f"Session file: {session_base}.session")
    print("You will be asked for phone/code/2FA password in the console.")

    client = TelegramClient(str(session_base), api_id, api_hash)
    await client.start()
    me = await client.get_me()
    who = getattr(me, "username", None) or getattr(me, "first_name", None) or "(unknown)"
    print(f"OK: authorized as {who}")
    await client.disconnect()
    return 0


def main() -> int:
    import asyncio

    try:
        return asyncio.run(_run())
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
