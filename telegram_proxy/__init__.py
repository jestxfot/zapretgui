# telegram_proxy/__init__.py
"""Telegram WebSocket Proxy — routes Telegram traffic through WSS to bypass IP blocks.

Public API:
    from telegram_proxy import ProxyController

    controller = ProxyController(port=1353, mode="socks5")
    controller.start()
    controller.stop()
    print(controller.is_running)
    print(controller.stats)
"""

import asyncio
import logging
import threading
from dataclasses import dataclass
from typing import Optional, Callable

from telegram_proxy.wss_proxy import TelegramWSProxy, ProxyStats

log = logging.getLogger("tg_proxy")

# Default port
DEFAULT_PORT = 1353


class ProxyController:
    """Thread-safe controller for the Telegram WSS proxy.

    Runs the asyncio event loop in a dedicated daemon thread.
    Safe to call start/stop from any thread (e.g., PyQt GUI thread).
    """

    def __init__(
        self,
        port: int = DEFAULT_PORT,
        mode: str = "socks5",
        on_log: Optional[Callable[[str], None]] = None,
    ):
        self._port = port
        self._mode = mode
        self._on_log = on_log
        self._proxy: Optional[TelegramWSProxy] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._started = threading.Event()

    @property
    def is_running(self) -> bool:
        return self._proxy is not None and self._proxy.is_running

    @property
    def stats(self) -> Optional[ProxyStats]:
        return self._proxy.stats if self._proxy else None

    @property
    def port(self) -> int:
        return self._port

    @property
    def mode(self) -> str:
        return self._mode

    def start(self) -> bool:
        """Start the proxy in a background thread. Non-blocking.

        Returns True if started successfully, False if already running.
        """
        if self.is_running:
            return False

        self._loop = asyncio.new_event_loop()
        self._proxy = TelegramWSProxy(
            port=self._port,
            mode=self._mode,
            on_log=self._on_log,
        )
        self._started.clear()
        self._thread = threading.Thread(
            target=self._run_loop,
            name="tg-proxy-loop",
            daemon=True,
        )
        self._thread.start()
        # Wait for the server to actually start (max 5 seconds)
        self._started.wait(timeout=5.0)
        return self.is_running

    def stop(self) -> None:
        """Stop the proxy. Non-blocking with short timeout."""
        if not self._loop or not self._proxy:
            return

        future = asyncio.run_coroutine_threadsafe(self._proxy.stop(), self._loop)
        try:
            future.result(timeout=2.0)
        except Exception:
            pass

        self._loop.call_soon_threadsafe(self._loop.stop)
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)

        self._loop = None
        self._proxy = None
        self._thread = None

    def update_config(self, port: int = None, mode: str = None) -> None:
        """Update config. Requires restart to take effect."""
        if port is not None:
            self._port = port
        if mode is not None:
            self._mode = mode

    def restart(self) -> bool:
        """Restart with current config."""
        self.stop()
        return self.start()

    def _run_loop(self) -> None:
        """Run the asyncio event loop in a dedicated thread."""
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._proxy.start())
            self._started.set()
            self._loop.run_forever()
        except Exception:
            log.exception("Proxy event loop error")
        finally:
            # Cleanup remaining tasks
            try:
                pending = asyncio.all_tasks(self._loop)
                for task in pending:
                    task.cancel()
                if pending:
                    self._loop.run_until_complete(
                        asyncio.gather(*pending, return_exceptions=True)
                    )
                self._loop.run_until_complete(self._loop.shutdown_asyncgens())
            except Exception:
                pass
            finally:
                self._loop.close()
                self._started.set()  # Unblock start() even on failure
