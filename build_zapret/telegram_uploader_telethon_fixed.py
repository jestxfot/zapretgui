#!/usr/bin/env python3

import argparse
import os
import sys
from pathlib import Path
from typing import Any


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


def _env_truthy(name: str) -> bool:
    return (os.environ.get(name) or "").strip().lower() in {"1", "true", "yes", "on"}


def _socks5_proxy_or_exit() -> tuple | None:
    """Returns Telethon proxy tuple.

    Default: SOCKS5 127.0.0.1:10808
    Disable (escape hatch): ZAPRET_TG_NO_SOCKS=1
    """
    if _env_truthy("ZAPRET_TG_NO_SOCKS"):
        return None

    host = (os.environ.get("ZAPRET_SOCKS5_HOST") or "").strip() or "127.0.0.1"
    port = (os.environ.get("ZAPRET_SOCKS5_PORT") or "").strip() or "10808"
    try:
        port_i = int(port)
    except Exception:
        print(f"Invalid ZAPRET_SOCKS5_PORT={port!r}")
        raise SystemExit(2)

    try:
        import socks  # type: ignore
    except Exception as e:
        print(f"PySocks is required for SOCKS5 proxy: {e}")
        print("Install: pip install pysocks")
        raise SystemExit(2)

    return (socks.SOCKS5, host, port_i)


def _remote_filename(file_path: Path, channel: str, version: str) -> str:
    name = file_path.name
    if name.lower().startswith("zapret2setup") and name.lower().endswith(".exe"):
        suffix = "_TEST" if (channel or "").strip().lower() in {"test", "dev"} else ""
        v = (version or "").strip()
        if v:
            return f"Zapret2Setup{suffix}_{v}.exe"
        return f"Zapret2Setup{suffix}.exe"
    return name


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
    base_caption = (args.notes or "").strip() or f"Zapret {args.version}"
    caption = (f"v{args.version}\n\n{base_caption}").strip()

    session_base = Path(__file__).resolve().parent / "zapret_uploader"
    session_file = session_base.with_suffix(".session")
    if not session_file.exists():
        print(f"Missing session: {session_file}")
        print("Run: python3 build_zapret/telegram_auth_telethon.py")
        return 3

    proxy = _socks5_proxy_or_exit()
    remote_name = _remote_filename(file_path, args.channel, args.version)

    print(f"Uploading via Telethon to {chat_id}")
    size_mb = file_path.stat().st_size / 1024 / 1024
    print(f"File: {file_path} ({size_mb:.1f} MB)")
    if proxy is None:
        print("Proxy: disabled (ZAPRET_TG_NO_SOCKS=1)")
    else:
        host = (os.environ.get("ZAPRET_SOCKS5_HOST") or "").strip() or "127.0.0.1"
        port = (os.environ.get("ZAPRET_SOCKS5_PORT") or "").strip() or "10808"
        print(f"Proxy: socks5://{host}:{port}")

    client = TelegramClient(str(session_base), api_id, api_hash, proxy=proxy)  # type: ignore[arg-type]

    await client.connect()
    if not await client.is_user_authorized():
        print("Session is not authorized")
        print("Run: python build_zapret/telegram_auth_telethon.py")
        return 3

    last_percent = -1

    def _progress(sent: int, total: int) -> None:
        nonlocal last_percent
        if total <= 0:
            return
        pct = int((sent / total) * 100)
        if pct >= last_percent + 10:
            last_percent = pct - (pct % 10)
            print(f"  {last_percent}% ({sent/1024/1024:.1f}/{total/1024/1024:.1f} MB)")

    attrs: list[Any] = []
    try:
        from telethon.tl.types import DocumentAttributeFilename  # type: ignore
        attrs = [DocumentAttributeFilename(remote_name)]
    except Exception:
        attrs = []

    msg = await client.send_file(
        chat_id,
        str(file_path),
        caption=caption,
        force_document=True,
        attributes=attrs,
        progress_callback=_progress,
    )

    try:
        pin_target = msg[-1] if isinstance(msg, list) and msg else msg
        await client.pin_message(chat_id, pin_target, notify=False)  # type: ignore[arg-type]
        print("Pinned")
    except Exception as e:
        print(f"Pin skipped: {e}")

    res = client.disconnect()
    try:
        import asyncio

        if asyncio.iscoroutine(res):
            await res
    except Exception:
        pass
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
