#!/usr/bin/env python3

import argparse
import os
import sys
import time
from contextlib import contextmanager
from pathlib import Path


def _bootstrap_repo_path() -> None:
    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))


def _set_asyncio_policy() -> None:
    import asyncio

    if sys.platform != "win32":
        return

    if os.environ.get("ZAPRET_ASYNCIO_WINDOWS_SELECTOR") not in {"1", "true", "TRUE", "yes", "YES"}:
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
        tags = "#zapret #zapretgui #запрет #запретгуи #РКН #роскомнадзор #роскомпозор #ВПН #VPN #обходблокировок #stable"
    else:
        tags = "#zapret #zapretgui #запрет #запретгуи #РКН #роскомнадзор #роскомпозор #ВПН #VPN #обходблокировок"

    return (
        f"{emoji}\n"
        f"Стабильные: {stable_link} | Дев: {dev_link}\n"
        f"{release_kind}\n\n"
        f"{changes}\n\n"
        f"{tags}"
    ).strip()


def _load_api_creds_from_env() -> tuple[int, str]:
    api_id = (os.getenv("TELEGRAM_API_ID") or os.getenv("ZAPRET_TELEGRAM_API_ID") or "").strip()
    api_hash = (os.getenv("TELEGRAM_API_HASH") or os.getenv("ZAPRET_TELEGRAM_API_HASH") or "").strip()
    if not api_id or not api_hash:
        raise RuntimeError(
            "Missing Telegram API credentials. Provide api_id/api_hash args or set TELEGRAM_API_ID and TELEGRAM_API_HASH."
        )
    try:
        return int(api_id), api_hash
    except Exception as e:
        raise RuntimeError(f"TELEGRAM_API_ID must be an integer: {e}")


def _load_proxy() -> dict | None:
    if (os.environ.get("ZAPRET_TG_NO_PROXY") or "").strip().lower() in {"1", "true", "yes", "on"}:
        return None
    if (os.environ.get("ZAPRET_TG_NO_SOCKS") or "").strip().lower() in {"1", "true", "yes", "on"}:
        return None

    scheme = (os.environ.get("ZAPRET_TG_PROXY_SCHEME") or os.environ.get("ZAPRET_PROXY_SCHEME") or "socks5").strip().lower()
    if scheme in {"https"}:
        scheme = "http"
    if scheme not in {"socks5", "http"}:
        return None

    host = (os.environ.get("ZAPRET_PROXY_HOST") or os.environ.get("ZAPRET_SOCKS5_HOST") or "").strip()
    port = (os.environ.get("ZAPRET_PROXY_PORT") or os.environ.get("ZAPRET_SOCKS5_PORT") or "").strip()
    if not host or not port:
        return None
    try:
        port_i = int(port)
    except Exception:
        return None

    user = (
        os.environ.get("ZAPRET_PROXY_USER")
        or os.environ.get("ZAPRET_PROXY_USERNAME")
        or os.environ.get("ZAPRET_SOCKS5_USER")
        or os.environ.get("ZAPRET_SOCKS5_USERNAME")
        or ""
    ).strip()
    password = (
        os.environ.get("ZAPRET_PROXY_PASS")
        or os.environ.get("ZAPRET_PROXY_PASSWORD")
        or os.environ.get("ZAPRET_SOCKS5_PASS")
        or os.environ.get("ZAPRET_SOCKS5_PASSWORD")
        or ""
    ).strip()

    proxy: dict = {"scheme": scheme, "hostname": host, "port": port_i}
    if user:
        proxy["username"] = user
    if password:
        proxy["password"] = password
    return proxy


@contextmanager
def _session_lock(lock_path: Path, timeout_s: int = 900):
    """Cross-platform exclusive lock for the pyrogram session sqlite file."""
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    f = lock_path.open("a+", encoding="utf-8", errors="ignore")
    start = time.time()
    while True:
        try:
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            break
        except OSError:
            if time.time() - start > timeout_s:
                raise TimeoutError(f"Timed out waiting for session lock: {lock_path}")
            time.sleep(0.5)

    try:
        yield
    finally:
        try:
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        finally:
            try:
                f.close()
            except Exception:
                pass


async def _run(argv: list[str]) -> int:
    _bootstrap_repo_path()

    p = argparse.ArgumentParser(description="Upload a build to Telegram using Pyrogram session.")
    p.add_argument("file", help="Path to file to send")
    p.add_argument("channel", help="stable/test (or @username)")
    p.add_argument("version", help="Version string")
    p.add_argument("notes", help="Caption text")
    p.add_argument("api_id", nargs="?", default=None, help="Telegram API ID (optional if TELEGRAM_API_ID is set)")
    p.add_argument("api_hash", nargs="?", default=None, help="Telegram API hash (optional if TELEGRAM_API_HASH is set)")
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
        if args.api_id is None or args.api_hash is None:
            api_id, api_hash = _load_api_creds_from_env()
        else:
            api_id = int(str(args.api_id).strip())
            api_hash = str(args.api_hash).strip()
            if not api_hash:
                raise RuntimeError("api_hash is empty")
    except Exception as e:
        print(str(e))
        return 2

    channel_username = _resolve_channel_username(args.channel)
    chat_id = f"@{channel_username}"
    caption = _build_caption(file_path=file_path, channel=args.channel, version=args.version, notes=args.notes)

    proxy = _load_proxy()

    session_base = Path(__file__).resolve().parent / "zapret_uploader_pyrogram"
    session_file = session_base.with_suffix(".session")
    lock_file = session_base.with_suffix(".session.lock")
    if not session_file.exists():
        print(f"Missing session: {session_file}")
        print("Run: python build_zapret/telegram_auth_pyrogram.py")
        return 3

    print(f"Uploading via Pyrogram to {chat_id}")
    print(f"File: {file_path} ({file_path.stat().st_size / 1024 / 1024:.1f} MB)")
    if proxy:
        print(f"Proxy: {proxy.get('scheme','?')}://{proxy['hostname']}:{proxy['port']}")

    client_kwargs: dict = {"api_id": api_id, "api_hash": api_hash}
    if proxy:
        client_kwargs["proxy"] = proxy
    progress_start = time.time()
    progress_last_pct = -5

    def _progress(current: int, total: int):
        nonlocal progress_last_pct
        try:
            if not total:
                return
            pct = int((current / total) * 100)
            now = time.time()
            elapsed = max(now - progress_start, 0.001)
            if pct >= progress_last_pct + 5 or pct == 100:
                mb_cur = current / 1024 / 1024
                mb_tot = total / 1024 / 1024
                speed = mb_cur / elapsed
                progress_last_pct = pct
                print(f"  {pct:3d}% ({mb_cur:.1f}/{mb_tot:.1f} MB) {speed:.1f} MB/s", flush=True)
        except Exception:
            return

    # Prevent concurrent access to pyrogram sqlite session.
    with _session_lock(lock_file):
        app = Client(str(session_base), **client_kwargs)
        try:
            await app.start()
            size_mb = file_path.stat().st_size / 1024 / 1024
            timeout = 7200 if size_mb > 100 else 3600
            import asyncio

            await asyncio.wait_for(
                app.send_document(chat_id=chat_id, document=str(file_path), caption=caption, progress=_progress),
                timeout=timeout,
            )
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
