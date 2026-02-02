#!/usr/bin/env python3

import os
import sys
from pathlib import Path
from typing import Any


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


def _env_truthy(name: str) -> bool:
    return (os.environ.get(name) or "").strip().lower() in {"1", "true", "yes", "on"}


def _proxy_or_none():
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
        raise RuntimeError(f"Invalid proxy scheme: {scheme!r} (use socks5|http)")

    host = (os.environ.get("ZAPRET_PROXY_HOST") or os.environ.get("ZAPRET_SOCKS5_HOST") or "").strip() or "127.0.0.1"
    port = (os.environ.get("ZAPRET_PROXY_PORT") or os.environ.get("ZAPRET_SOCKS5_PORT") or "").strip() or "10808"
    try:
        port_i = int(port)
    except Exception:
        raise RuntimeError(f"Invalid proxy port: {port!r}")

    user = (os.environ.get("ZAPRET_PROXY_USER") or os.environ.get("ZAPRET_PROXY_USERNAME") or os.environ.get("ZAPRET_SOCKS5_USER") or os.environ.get("ZAPRET_SOCKS5_USERNAME") or "").strip()
    password = (os.environ.get("ZAPRET_PROXY_PASS") or os.environ.get("ZAPRET_PROXY_PASSWORD") or os.environ.get("ZAPRET_SOCKS5_PASS") or os.environ.get("ZAPRET_SOCKS5_PASSWORD") or "").strip()

    try:
        import socks  # type: ignore
    except Exception as e:
        raise RuntimeError(f"PySocks is required for proxy support: {e}. Install: pip install pysocks")

    if scheme == "http":
        if user:
            return (socks.HTTP, host, port_i, True, user, password)
        return (socks.HTTP, host, port_i)

    # socks5
    if user:
        return (socks.SOCKS5, host, port_i, True, user, password)
    return (socks.SOCKS5, host, port_i)


async def _run() -> int:
    import asyncio

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
    proxy = _proxy_or_none()
    if proxy is None:
        print("Proxy: disabled (ZAPRET_TG_NO_PROXY=1)")
    else:
        scheme = (os.environ.get("ZAPRET_TG_PROXY_SCHEME") or os.environ.get("ZAPRET_PROXY_SCHEME") or "socks5").strip().lower()
        host = (os.environ.get("ZAPRET_PROXY_HOST") or os.environ.get("ZAPRET_SOCKS5_HOST") or "").strip() or "127.0.0.1"
        port = (os.environ.get("ZAPRET_PROXY_PORT") or os.environ.get("ZAPRET_SOCKS5_PORT") or "").strip() or "10808"
        print(f"Proxy: {scheme}://{host}:{port}")
    print("You will be asked for phone/code/2FA password in the console.")

    client = TelegramClient(str(session_base), api_id, api_hash, proxy=proxy)  # type: ignore[arg-type]

    res: Any = client.start()
    try:
        if asyncio.iscoroutine(res):
            await res
    except Exception:
        pass

    me = await client.get_me()
    who = getattr(me, "username", None) or getattr(me, "first_name", None) or "(unknown)"
    print(f"OK: authorized as {who}")

    res = client.disconnect()
    try:
        if asyncio.iscoroutine(res):
            await res
    except Exception:
        pass
    return 0


def main() -> int:
    import asyncio

    try:
        return asyncio.run(_run())
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
