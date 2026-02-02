#!/usr/bin/env python3

import os
import sys
from pathlib import Path


def _set_asyncio_policy() -> None:
    import asyncio

    if sys.platform != "win32":
        return

    # Some asyncio-based libs work more reliably with selector loop on Windows.
    policy = getattr(asyncio, "WindowsSelectorEventLoopPolicy", None)
    if policy is None:
        return
    try:
        asyncio.set_event_loop_policy(policy())
    except Exception:
        pass


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


async def _run() -> int:
    _bootstrap_dotenv()

    try:
        from pyrogram import Client  # type: ignore
    except Exception as e:
        print(f"pyrogram is not available: {e}")
        print("Install dependencies: pip install -r requirements.txt")
        return 2

    api_id, api_hash = _load_api_creds()

    proxy = _load_socks5_proxy()

    session_base = Path(__file__).resolve().parent / "zapret_uploader_pyrogram"
    print("Telegram auth (Pyrogram)")
    print(f"Session file: {session_base}.session")
    if proxy:
        print(f"Proxy: socks5://{proxy['hostname']}:{proxy['port']}")
    print("You will be asked for phone/code/2FA password in the console.")

    client_kwargs: dict = {"api_id": api_id, "api_hash": api_hash}
    if proxy:
        client_kwargs["proxy"] = proxy
    app = Client(str(session_base), **client_kwargs)
    try:
        await app.start()
        me = await app.get_me()
        who = getattr(me, "username", None) or getattr(me, "first_name", None) or "(unknown)"
        print(f"OK: authorized as {who}")
        return 0
    finally:
        try:
            await app.stop()
        except Exception:
            pass


def main() -> int:
    import asyncio

    _set_asyncio_policy()
    try:
        return asyncio.run(_run())
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
