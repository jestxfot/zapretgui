#!/usr/bin/env python3

import os
import asyncio
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
    session_file = session_base.with_suffix(".session")
    print("Telegram auth (Pyrogram)")
    print(f"Session file: {session_file}")
    if proxy:
        print(f"Proxy: socks5://{proxy['hostname']}:{proxy['port']}")

    client_kwargs: dict = {"api_id": api_id, "api_hash": api_hash}
    if proxy:
        client_kwargs["proxy"] = proxy
    app = Client(str(session_base), **client_kwargs)

    try:
        # If session already exists, try to reuse it first.
        if session_file.exists():
            print("Checking existing session...")
            try:
                await asyncio.wait_for(app.connect(), timeout=45)
                me = await asyncio.wait_for(app.get_me(), timeout=30)
                who = getattr(me, "username", None) or getattr(me, "first_name", None) or "(unknown)"
                print(f"OK: already authorized as {who}")
                return 0
            except Exception as e:
                try:
                    from pyrogram.errors import Unauthorized, AuthKeyUnregistered, SessionRevoked  # type: ignore

                    if isinstance(e, (Unauthorized, AuthKeyUnregistered, SessionRevoked)):
                        print("Session exists but is not authorized. Re-authorizing...")
                except Exception:
                    pass
                try:
                    await app.disconnect()
                except Exception:
                    pass

        phone = (input("Phone (+...): ") or "").strip()
        if not phone:
            print("Phone is empty")
            return 2

        print("Connecting to Telegram...")
        await asyncio.wait_for(app.connect(), timeout=45)

        sent = await asyncio.wait_for(app.send_code(phone), timeout=60)
        code = (input("Code: ") or "").strip()
        if not code:
            print("Code is empty")
            return 2

        try:
            res = await asyncio.wait_for(app.sign_in(phone, sent.phone_code_hash, code), timeout=60)
        except Exception as e:
            # 2FA flow
            from pyrogram.errors import SessionPasswordNeeded  # type: ignore

            if isinstance(e, SessionPasswordNeeded):
                import getpass

                pw = getpass.getpass("2FA password: ")
                await asyncio.wait_for(app.check_password(pw), timeout=60)
                res = True
            else:
                raise

        try:
            from pyrogram import types  # type: ignore

            if isinstance(res, getattr(types, "TermsOfService", object)):
                print("Telegram requires accepting Terms of Service:")
                text = getattr(res, "text", "")
                if text:
                    print(text)
                tos_id = getattr(res, "id", None)
                if tos_id:
                    ans = (input("Type YES to accept: ") or "").strip().upper()
                    if ans == "YES":
                        ok = await asyncio.wait_for(app.accept_terms_of_service(tos_id), timeout=60)
                        if not ok:
                            print("Failed to accept Terms of Service")
                            return 2
                    else:
                        print("Terms of Service not accepted")
                        return 2
        except Exception:
            # If ToS handling fails, continue; user can retry.
            pass

        me = await asyncio.wait_for(app.get_me(), timeout=30)
        who = getattr(me, "username", None) or getattr(me, "first_name", None) or "(unknown)"
        print(f"OK: authorized as {who}")
        return 0
    except TimeoutError:
        print("Timeout while connecting/authorizing.")
        print("Check that SOCKS5 proxy is reachable and Telegram is accessible.")
        return 2
    finally:
        try:
            if getattr(app, "is_connected", False):
                await app.disconnect()
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
