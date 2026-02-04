#!/usr/bin/env python3

import argparse
import asyncio
import os
import sys
import time
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


def _proxy_or_exit() -> tuple | None:
    """Telethon proxy tuple.

    Disable: ZAPRET_TG_NO_PROXY=1 (or legacy ZAPRET_TG_NO_SOCKS=1)

    Configure:
      - ZAPRET_TG_PROXY_SCHEME=socks5|http  (default: socks5)
      - ZAPRET_PROXY_HOST / ZAPRET_PROXY_PORT
      - ZAPRET_PROXY_USER / ZAPRET_PROXY_PASS (optional)

    Back-compat:
      - ZAPRET_SOCKS5_HOST / ZAPRET_SOCKS5_PORT / ZAPRET_SOCKS5_USER / ZAPRET_SOCKS5_PASS
    """
    if _env_truthy("ZAPRET_TG_NO_PROXY") or _env_truthy("ZAPRET_TG_NO_SOCKS"):
        return None

    scheme = (os.environ.get("ZAPRET_TG_PROXY_SCHEME") or os.environ.get("ZAPRET_PROXY_SCHEME") or "socks5").strip().lower()
    if scheme in {"https"}:
        scheme = "http"
    if scheme not in {"socks5", "http"}:
        print(f"Invalid proxy scheme: {scheme!r} (use socks5|http)")
        raise SystemExit(2)

    host = (os.environ.get("ZAPRET_PROXY_HOST") or os.environ.get("ZAPRET_SOCKS5_HOST") or "").strip() or "127.0.0.1"
    port = (os.environ.get("ZAPRET_PROXY_PORT") or os.environ.get("ZAPRET_SOCKS5_PORT") or "").strip() or "10808"
    try:
        port_i = int(port)
    except Exception:
        print(f"Invalid proxy port: {port!r}")
        raise SystemExit(2)

    user = (os.environ.get("ZAPRET_PROXY_USER") or os.environ.get("ZAPRET_PROXY_USERNAME") or os.environ.get("ZAPRET_SOCKS5_USER") or os.environ.get("ZAPRET_SOCKS5_USERNAME") or "").strip()
    password = (os.environ.get("ZAPRET_PROXY_PASS") or os.environ.get("ZAPRET_PROXY_PASSWORD") or os.environ.get("ZAPRET_SOCKS5_PASS") or os.environ.get("ZAPRET_SOCKS5_PASSWORD") or "").strip()

    try:
        import socks  # type: ignore
    except Exception as e:
        print(f"PySocks is required for proxy support: {e}")
        print("Install: pip install pysocks")
        raise SystemExit(2)

    if scheme == "http":
        if user:
            return (socks.HTTP, host, port_i, True, user, password)
        return (socks.HTTP, host, port_i)

    # socks5
    if user:
        return (socks.SOCKS5, host, port_i, True, user, password)
    return (socks.SOCKS5, host, port_i)


def _remote_filename(file_path: Path, channel: str, version: str) -> str:
    name = file_path.name
    if name.lower().startswith("zapret2setup") and name.lower().endswith(".exe"):
        suffix = "_TEST" if (channel or "").strip().lower() in {"test", "dev"} else ""
        v = (version or "").strip().replace(".", "_")
        if v:
            return f"Zapret2Setup{suffix}_{v}.exe"
        return f"Zapret2Setup{suffix}.exe"
    return name


def _channel_info(channel: str) -> tuple[str, str, str]:
    ch = (channel or "").strip().lower()
    if ch in {"test", "dev"}:
        return "🧪", "Dev версия", "TEST"
    if ch in {"stable", "prod", "release"}:
        return "✅", "Stable версия", "STABLE"
    return "🧪", "Dev версия", (channel or "").strip().upper() or "TEST"


def _build_caption(*, file_path: Path, channel: str, version: str, notes: str) -> str:
    emoji, release_kind, upd_channel = _channel_info(channel)
    stable_link = "https://t.me/zapretnetdiscordyoutube"
    dev_link = "https://t.me/zapretguidev"

    changes = (notes or "").strip()
    if not changes:
        changes = "(нет описания изменений)"

    if upd_channel == "STABLE":
        tags = "#zapret #stable #release"
    else:
        tags = "#zapretdev #dev #testing #beta #запретдев"

    return (
        f"{emoji} Zapret {version}\n"
        f"Стабильные: {stable_link} | Дев: {dev_link}\n"
        f"{release_kind}\n\n"
        f"{changes}\n\n"
        f"{tags}"
    ).strip()


async def _run(argv: list[str]) -> int:
    try:
        reconfig = getattr(sys.stdout, "reconfigure", None)
        if callable(reconfig):
            reconfig(line_buffering=True)
        reconfig = getattr(sys.stderr, "reconfigure", None)
        if callable(reconfig):
            reconfig(line_buffering=True)
    except Exception:
        pass

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
    caption = _build_caption(file_path=file_path, channel=args.channel, version=args.version, notes=args.notes)

    session_base = Path(__file__).resolve().parent / "zapret_uploader"
    session_file = session_base.with_suffix(".session")
    if not session_file.exists():
        print(f"Missing session: {session_file}")
        print("Run: python3 build_zapret/telegram_auth_telethon.py")
        return 3

    proxy = _proxy_or_exit()
    remote_name = _remote_filename(file_path, args.channel, args.version)

    print(f"Uploading via Telethon to {chat_id}")
    size_mb = file_path.stat().st_size / 1024 / 1024
    print(f"File: {file_path} ({size_mb:.1f} MB)")
    if proxy is None:
        print("Proxy: disabled (ZAPRET_TG_NO_PROXY=1)")
    else:
        scheme = (os.environ.get("ZAPRET_TG_PROXY_SCHEME") or os.environ.get("ZAPRET_PROXY_SCHEME") or "socks5").strip().lower()
        host = (os.environ.get("ZAPRET_PROXY_HOST") or os.environ.get("ZAPRET_SOCKS5_HOST") or "").strip() or "127.0.0.1"
        port = (os.environ.get("ZAPRET_PROXY_PORT") or os.environ.get("ZAPRET_SOCKS5_PORT") or "").strip() or "10808"
        print(f"Proxy: {scheme}://{host}:{port}")

    connect_timeout_s = int((os.environ.get("ZAPRET_TG_CONNECT_TIMEOUT") or "45").strip() or "45")
    upload_timeout_s = int((os.environ.get("ZAPRET_TG_UPLOAD_TIMEOUT") or "1800").strip() or "1800")

    client = TelegramClient(str(session_base), api_id, api_hash, proxy=proxy)  # type: ignore[arg-type]

    print(f"Connecting to Telegram... (timeout {connect_timeout_s}s)")
    await asyncio.wait_for(client.connect(), timeout=connect_timeout_s)
    if not await client.is_user_authorized():
        print("Session is not authorized")
        print("Run: python build_zapret/telegram_auth_telethon.py")
        return 3

    last_percent = -1
    last_update = 0.0
    start_time = time.time()

    def _progress(sent: int, total: int) -> None:
        nonlocal last_percent
        nonlocal last_update
        if total <= 0:
            return
        pct = int((sent / total) * 100)
        now = time.time()
        if pct >= last_percent + 10 or (now - last_update) > 15:
            shown = min(100, pct)
            elapsed = max(now - start_time, 1.0)
            speed = (sent / 1024 / 1024) / elapsed
            print(f"  {shown}% ({sent/1024/1024:.1f}/{total/1024/1024:.1f} MB) — {speed:.1f} MB/s")
            last_percent = shown - (shown % 10)
            last_update = now

    attrs: list[Any] = []
    try:
        from telethon.tl.types import DocumentAttributeFilename  # type: ignore
        attrs = [DocumentAttributeFilename(remote_name)]
    except Exception:
        attrs = []

    print(f"Sending file... (timeout {upload_timeout_s}s)")
    try:
        msg = await asyncio.wait_for(
            client.send_file(
                chat_id,
                str(file_path),
                caption=caption,
                force_document=True,
                attributes=attrs,
                progress_callback=_progress,
            ),
            timeout=upload_timeout_s,
        )
    except asyncio.TimeoutError:
        print("Timeout while uploading to Telegram.")
        print("If you use a proxy, verify it works for Telegram. Try setting ZAPRET_TG_NO_PROXY=1 if VPN is full-tunnel.")
        return 2

    try:
        pin_target = msg[-1] if isinstance(msg, list) and msg else msg
        await client.pin_message(chat_id, pin_target, notify=False)  # type: ignore[arg-type]
        print("Pinned")
    except Exception as e:
        print(f"Pin skipped: {e}")

    res = client.disconnect()
    try:
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
