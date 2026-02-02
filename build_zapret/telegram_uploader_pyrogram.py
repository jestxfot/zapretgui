#!/usr/bin/env python3

import argparse
import os
import sys
from pathlib import Path


def _bootstrap_repo_path() -> None:
    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))


def _set_asyncio_policy() -> None:
    import asyncio

    if sys.platform != "win32":
        return
    policy = getattr(asyncio, "WindowsSelectorEventLoopPolicy", None)
    if policy is None:
        return
    try:
        asyncio.set_event_loop_policy(policy())
    except Exception:
        pass


def _resolve_channel_username(channel: str) -> str:
    ch = (channel or "").strip().lower()
    if ch.startswith("@"):  # allow passing @username
        return ch[1:]

    # Prefer the same mapping as updater uses.
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


def _load_socks5_proxy() -> dict | None:
    host = (os.environ.get("ZAPRET_SOCKS5_HOST") or "").strip()
    port = (os.environ.get("ZAPRET_SOCKS5_PORT") or "").strip()
    if not host or not port:
        return None
    try:
        port_i = int(port)
    except Exception:
        return None

    user = (os.environ.get("ZAPRET_SOCKS5_USER") or os.environ.get("ZAPRET_SOCKS5_USERNAME") or "").strip()
    password = (os.environ.get("ZAPRET_SOCKS5_PASS") or os.environ.get("ZAPRET_SOCKS5_PASSWORD") or "").strip()

    proxy: dict = {"scheme": "socks5", "hostname": host, "port": port_i}
    if user:
        proxy["username"] = user
    if password:
        proxy["password"] = password
    return proxy


async def _run(argv: list[str]) -> int:
    _bootstrap_repo_path()

    p = argparse.ArgumentParser(description="Upload a build to Telegram using Pyrogram session.")
    p.add_argument("file", help="Path to file to send")
    p.add_argument("channel", help="stable/test (or @username)")
    p.add_argument("version", help="Version string")
    p.add_argument("notes", help="Caption text")
    p.add_argument("api_id", help="Telegram API ID")
    p.add_argument("api_hash", help="Telegram API hash")
    args = p.parse_args(argv)

    try:
        from pyrogram import Client  # type: ignore
    except Exception as e:
        print(f"pyrogram is not available: {e}")
        return 2

    file_path = Path(args.file).resolve()
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

    proxy = _load_socks5_proxy()

    session_base = Path(__file__).resolve().parent / "zapret_uploader_pyrogram"
    session_file = session_base.with_suffix(".session")
    if not session_file.exists():
        print(f"Missing session: {session_file}")
        print("Run: python build_zapret/telegram_auth_pyrogram.py")
        return 3

    print(f"Uploading via Pyrogram to {chat_id}")
    print(f"File: {file_path} ({file_path.stat().st_size / 1024 / 1024:.1f} MB)")
    if proxy:
        print(f"Proxy: socks5://{proxy['hostname']}:{proxy['port']}")

    client_kwargs: dict = {"api_id": api_id, "api_hash": api_hash}
    if proxy:
        client_kwargs["proxy"] = proxy
    app = Client(str(session_base), **client_kwargs)
    try:
        await app.start()
        await app.send_document(chat_id=chat_id, document=str(file_path), caption=caption)
        print("OK")
        return 0
    finally:
        try:
            await app.stop()
        except Exception:
            pass


def main(argv: list[str]) -> int:
    import asyncio

    _set_asyncio_policy()
    try:
        return asyncio.run(_run(argv))
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
