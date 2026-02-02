#!/usr/bin/env python3

import argparse
import os
import sys
from pathlib import Path


def _resolve_channel_username(channel: str) -> str:
    ch = (channel or "").strip().lower()
    if ch.startswith("@"):  # allow passing @username
        return ch[1:]

    try:
        from updater.telegram_updater import TELEGRAM_CHANNELS  # type: ignore
        mapping = dict(TELEGRAM_CHANNELS)
    except Exception:
        mapping = {
            "stable": "zapretnetdiscordyoutube",
            "test": "zapretguidev",
            "dev": "zapretguidev",
        }
    return mapping.get(ch, mapping.get("stable", ch))


def _maybe_proxy():
    host = (os.environ.get("ZAPRET_SOCKS5_HOST") or "").strip()
    port = (os.environ.get("ZAPRET_SOCKS5_PORT") or "").strip()
    if not host or not port:
        return None
    try:
        port_i = int(port)
    except Exception:
        return None

    try:
        import socks  # type: ignore
        return (socks.SOCKS5, host, port_i)
    except Exception:
        # Telethon accepts proxy=None, so just skip if PySocks not available.
        return None


async def _run(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description="Upload a build to Telegram using Telethon session.")
    p.add_argument("file", help="Linux path to file to send")
    p.add_argument("channel", help="stable/test (or @username)")
    p.add_argument("version", help="Version string")
    p.add_argument("notes", help="Caption text")
    p.add_argument("api_id", help="Telegram API ID")
    p.add_argument("api_hash", help="Telegram API hash")
    args = p.parse_args(argv)

    try:
        from telethon import TelegramClient  # type: ignore
    except Exception as e:
        print(f"telethon is not available: {e}")
        return 2

    file_path = Path(args.file)
    if not file_path.exists():
        print(f"File not found: {file_path}")
        return 2

    try:
        api_id = int(str(args.api_id).strip())
    except Exception as e:
        print(f"api_id must be int: {e}")
        return 2
    api_hash = str(args.api_hash).strip()
    if not api_hash:
        print("api_hash is empty")
        return 2

    channel_username = _resolve_channel_username(args.channel)
    chat_id = f"@{channel_username}"
    caption = (args.notes or "").strip() or f"Zapret {args.version}"

    session_base = Path(__file__).resolve().parent / "zapret_uploader"
    session_file = session_base.with_suffix(".session")
    if not session_file.exists():
        print(f"Missing session: {session_file}")
        print("Run: python3 build_zapret/telegram_auth_telethon.py")
        return 3

    proxy = _maybe_proxy()

    print(f"Uploading via Telethon to {chat_id}")
    size_mb = file_path.stat().st_size / 1024 / 1024
    print(f"File: {file_path} ({size_mb:.1f} MB)")
    if proxy:
        print("Using SOCKS5 proxy")

    client = TelegramClient(str(session_base), api_id, api_hash, proxy=proxy)
    await client.start()
    await client.send_file(chat_id, str(file_path), caption=caption, force_document=True)
    await client.disconnect()
    print("OK")
    return 0


def main() -> int:
    import asyncio

    try:
        return asyncio.run(_run(sys.argv[1:]))
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
