# ui/pages/telegram_proxy_page.py
"""Telegram WebSocket Proxy — UI page.

Provides controls for starting/stopping the proxy, mode selection,
port configuration, and quick-setup deep link for Telegram.
"""

from __future__ import annotations

import webbrowser
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QStackedWidget,
)
from PyQt6.QtGui import QGuiApplication

from .base_page import BasePage, ScrollBlockingPlainTextEdit
from ui.compat_widgets import SettingsCard, ActionButton
from ui.theme import get_theme_tokens
from log import log

try:
    from qfluentwidgets import (
        BodyLabel, CaptionLabel, StrongBodyLabel,
        SpinBox, InfoBar, InfoBarPosition,
        SegmentedWidget,
    )
    _HAS_FLUENT = True
except ImportError:
    from PyQt6.QtWidgets import QSpinBox as SpinBox
    BodyLabel = QLabel
    CaptionLabel = QLabel
    StrongBodyLabel = QLabel
    InfoBar = None
    SegmentedWidget = None
    _HAS_FLUENT = True

if TYPE_CHECKING:
    from main import LupiDPIApp

# Lazy import to avoid circular deps
_proxy_manager = None


def _get_proxy_manager():
    global _proxy_manager
    if _proxy_manager is None:
        from telegram_proxy.manager import TelegramProxyManager
        _proxy_manager = TelegramProxyManager()
    return _proxy_manager


# How often (ms) the GUI reads new log lines from the ring buffer
_LOG_REFRESH_MS = 500


class _StatusDot(QWidget):
    """Small colored circle indicator."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(12, 12)
        self._active = False

    def set_active(self, active: bool):
        self._active = active
        self.update()

    def paintEvent(self, event):
        from PyQt6.QtGui import QPainter, QColor
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = QColor("#4CAF50") if self._active else QColor("#888888")
        p.setBrush(color)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(1, 1, 10, 10)
        p.end()


class TelegramProxyPage(BasePage):
    """Telegram WebSocket Proxy settings page."""

    def __init__(self, parent=None):
        super().__init__(
            "Telegram Proxy",
            "Маршрутизация трафика Telegram через WebSocket для обхода ЗАМЕДЛЕНИЯ (не поддерживает полный блок) по IP",
            parent,
        )
        self.parent_app = parent
        self._setup_ui()
        self._connect_signals()
        # Load settings AFTER range is set (see _setup_ui)
        QTimer.singleShot(0, self._load_settings)
        # Log refresh timer — drains ring buffer every 500ms
        self._log_timer = QTimer(self)
        self._log_timer.timeout.connect(self._flush_log_buffer)
        self._log_timer.start(_LOG_REFRESH_MS)
        # Auto-start if enabled
        QTimer.singleShot(500, self._auto_start_check)

    def _setup_ui(self):
        # ── Tabs (SegmentedWidget) ──
        if SegmentedWidget is not None:
            self._pivot = SegmentedWidget(self)
        else:
            self._pivot = None

        self._stacked = QStackedWidget(self)

        # -- Panel 0: Settings --
        settings_panel = QWidget()
        settings_layout = QVBoxLayout(settings_panel)
        settings_layout.setContentsMargins(0, 0, 0, 0)
        settings_layout.setSpacing(12)

        self._build_settings_panel(settings_layout)
        self._stacked.addWidget(settings_panel)

        # -- Panel 1: Logs --
        logs_panel = QWidget()
        logs_layout = QVBoxLayout(logs_panel)
        logs_layout.setContentsMargins(0, 0, 0, 0)
        logs_layout.setSpacing(8)

        self._build_logs_panel(logs_layout)
        self._stacked.addWidget(logs_panel)

        # -- Panel 2: Diagnostics --
        diag_panel = QWidget()
        diag_layout = QVBoxLayout(diag_panel)
        diag_layout.setContentsMargins(0, 0, 0, 0)
        diag_layout.setSpacing(8)

        self._build_diag_panel(diag_layout)
        self._stacked.addWidget(diag_panel)

        # Wire up tabs
        if self._pivot is not None:
            self._pivot.addItem("settings", "Настройки", lambda: self._switch_tab(0))
            self._pivot.addItem("logs", "Логи", lambda: self._switch_tab(1))
            self._pivot.addItem("diag", "Диагностика", lambda: self._switch_tab(2))
            self._pivot.setCurrentItem("settings")
            self.add_widget(self._pivot)

        self.add_widget(self._stacked)
        self._switch_tab(0)

    def _switch_tab(self, index: int):
        self._stacked.setCurrentIndex(index)
        if self._pivot is not None:
            keys = ["settings", "logs", "diag"]
            if 0 <= index < len(keys):
                self._pivot.setCurrentItem(keys[index])

    def _build_settings_panel(self, layout: QVBoxLayout):
        # -- Status card --
        self._status_card = SettingsCard()

        status_header = QHBoxLayout()
        self._status_dot = _StatusDot()
        self._status_label = StrongBodyLabel("Остановлен")
        status_header.addWidget(self._status_dot)
        status_header.addWidget(self._status_label)
        status_header.addStretch()

        self._btn_toggle = ActionButton("Запустить")
        self._btn_toggle.setFixedWidth(140)
        self._btn_toggle.clicked.connect(self._on_toggle_proxy)
        status_header.addWidget(self._btn_toggle)
        self._status_card.add_layout(status_header)

        self._stats_label = CaptionLabel("")
        self._status_card.add_widget(self._stats_label)
        layout.addWidget(self._status_card)

        # -- Quick setup card --
        layout.addWidget(StrongBodyLabel("Быстрая настройка Telegram"))
        self._setup_card = SettingsCard()

        setup_desc = CaptionLabel(
            "Нажмите кнопку ниже - Telegram автоматически добавит прокси. "
            "Настройка требуется один раз.\nЕсли Telegram не открывается попробуйте скопировать ссылку и отправить в любой чат Telegram или кому-то в ЛС — после чего нажмите на отправленную ссылку и подтвердите добавление прокси в Telegram клиент.\nРекомендуем полностью ПЕРЕЗАПУСТИТЬ клиент для более корректного работа прокси после включения Zapret 2 GUI!"
        )
        setup_desc.setWordWrap(True)
        self._setup_card.add_widget(setup_desc)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self._btn_open_tg = ActionButton("Добавить прокси в Telegram")
        self._btn_open_tg.setToolTip("Откроет ссылку для автоматической настройки прокси")
        self._btn_open_tg.clicked.connect(self._on_open_in_telegram)
        btn_row.addWidget(self._btn_open_tg)

        self._btn_copy_link = ActionButton("Скопировать ссылку")
        self._btn_copy_link.clicked.connect(self._on_copy_link)
        btn_row.addWidget(self._btn_copy_link)

        btn_row.addStretch()
        self._setup_card.add_layout(btn_row)

        layout.addWidget(self._setup_card)

        # -- Settings card --
        layout.addWidget(StrongBodyLabel("Настройки"))
        self._settings_card = SettingsCard()

        # Port setting
        port_row = QHBoxLayout()
        port_label = BodyLabel("Порт:")
        port_row.addWidget(port_label)
        self._port_spin = SpinBox()
        self._port_spin.setRange(1024, 65535)
        self._port_spin.setValue(1353)
        self._port_spin.setFixedWidth(100)
        port_row.addWidget(self._port_spin)
        port_row.addStretch()
        self._settings_card.add_layout(port_row)

        # Auto-start toggle
        from ui.pages.dpi_settings_page import Win11ToggleRow
        self._autostart_toggle = Win11ToggleRow(
            "mdi.play-circle-outline",
            "Автозапуск прокси",
            "Запускать прокси автоматически при старте программы",
        )
        self._autostart_toggle.toggle.setChecked(True)
        self._settings_card.add_widget(self._autostart_toggle)

        # Auto-open deep link toggle
        self._auto_deeplink_toggle = Win11ToggleRow(
            "mdi.telegram",
            "Авто-настройка Telegram",
            "При первом запуске прокси автоматически открыть ссылку настройки в Telegram",
        )
        self._auto_deeplink_toggle.toggle.setChecked(True)
        self._settings_card.add_widget(self._auto_deeplink_toggle)

        layout.addWidget(self._settings_card)

        # -- Instructions card --
        layout.addWidget(StrongBodyLabel("Ручная настройка"))
        self._instructions_card = SettingsCard()

        instructions = [
            "Если автоматическая настройка не сработала:",
            "  Telegram -> Настройки -> Продвинутые -> Тип соединения -> Прокси",
            "  Тип: SOCKS5  |  Хост: 127.0.0.1  |  Порт: 1353",
        ]
        for line in instructions:
            lbl = CaptionLabel(line)
            lbl.setWordWrap(True)
            self._instructions_card.add_widget(lbl)

        layout.addWidget(self._instructions_card)
        layout.addStretch()

    def _build_logs_panel(self, layout: QVBoxLayout):
        # Toolbar row
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        self._btn_copy_logs = ActionButton("Копировать все")
        self._btn_copy_logs.clicked.connect(self._on_copy_all_logs)
        toolbar.addWidget(self._btn_copy_logs)

        self._btn_open_log_file = ActionButton("Открыть файл лога")
        self._btn_open_log_file.clicked.connect(self._on_open_log_file)
        toolbar.addWidget(self._btn_open_log_file)

        self._btn_clear_logs = ActionButton("Очистить")
        self._btn_clear_logs.clicked.connect(self._on_clear_logs)
        toolbar.addWidget(self._btn_clear_logs)

        toolbar.addStretch()
        layout.addLayout(toolbar)

        # Log text widget — no height limit, no trimming
        self._log_edit = ScrollBlockingPlainTextEdit()
        self._log_edit.setReadOnly(True)
        self._log_edit.setPlaceholderText("Лог подключений появится здесь...")
        layout.addWidget(self._log_edit)

    def _build_diag_panel(self, layout: QVBoxLayout):
        desc = CaptionLabel(
            "Проверка соединений к Telegram DC — TCP connect, TLS handshake, "
            "определение типа блокировки (по IP или SNI)."
        )
        desc.setWordWrap(True)
        layout.addWidget(desc)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        self._btn_run_diag = ActionButton("Запустить диагностику")
        self._btn_run_diag.clicked.connect(self._on_run_diagnostics)
        toolbar.addWidget(self._btn_run_diag)

        self._btn_copy_diag = ActionButton("Копировать результат")
        self._btn_copy_diag.clicked.connect(self._on_copy_diag)
        toolbar.addWidget(self._btn_copy_diag)

        toolbar.addStretch()
        layout.addLayout(toolbar)

        self._diag_edit = ScrollBlockingPlainTextEdit()
        self._diag_edit.setReadOnly(True)
        self._diag_edit.setPlaceholderText("Нажмите 'Запустить диагностику'...")
        layout.addWidget(self._diag_edit)

    def _on_run_diagnostics(self):
        """Run network diagnostics in a background thread."""
        self._btn_run_diag.setEnabled(False)
        self._btn_run_diag.setText("Тестирование...")
        self._diag_edit.clear()
        self._diag_edit.appendPlainText("Запуск диагностики Telegram DC...\n")

        self._diag_result = None  # shared with thread
        self._diag_thread_done = False

        import threading
        t = threading.Thread(target=self._run_diag_tests, daemon=True)
        t.start()

        # Poll for result every 200ms
        self._diag_poll_timer = QTimer(self)
        self._diag_poll_timer.timeout.connect(self._poll_diag)
        self._diag_poll_timer.start(200)

    def _poll_diag(self):
        """Check if diag thread has new results."""
        if self._diag_result is not None:
            self._diag_edit.setPlainText(self._diag_result)
            sb = self._diag_edit.verticalScrollBar()
            if sb:
                sb.setValue(sb.maximum())
        if self._diag_thread_done:
            self._diag_poll_timer.stop()
            self._diag_finished()

    def _run_diag_tests(self):
        """Background thread: test all Telegram DCs in parallel."""
        import concurrent.futures
        import time

        targets = [
            ("149.154.167.220", "WSS relay",  "—"),
            ("149.154.167.50",  "DC2",        "kws2"),
            ("149.154.167.41",  "DC2",        "kws2"),
            ("149.154.167.91",  "DC4",        "kws4"),
            ("149.154.175.53",  "DC1",        "—"),
            ("149.154.175.55",  "DC1",        "—"),
            ("91.108.56.134",   "DC5",        "—"),
            ("91.108.56.149",   "DC5",        "—"),
            ("91.105.192.100",  "DC203 CDN",  "—"),
        ]

        header = [
            f"{'IP':<20} {'DC':<12} {'TCP':>8}  {'TLS':>8}  {'Статус'}",
            "=" * 72,
        ]
        results = list(header)

        t0 = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(targets)) as ex:
            futures = {
                ex.submit(self._test_single_ip, ip, dc, wss): (ip, dc)
                for ip, dc, wss in targets
            }
            for f in concurrent.futures.as_completed(futures):
                results.append(f.result())
                self._diag_result = "\n".join(results)

        results.append("")
        results.append("── Определение типа блокировки ──")
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
            sni_f = ex.submit(self._test_sni_vs_ip)
            http_f = ex.submit(self._test_http_port80)
            results.append(sni_f.result())
            results.append("")
            results.append("── HTTP порт 80 (без TLS) ──")
            results.append(http_f.result())

        elapsed = time.time() - t0
        results.append("")
        results.append("=" * 72)
        results.append(self._build_summary(results))
        results.append(f"\nВремя тестирования: {elapsed:.1f}s")

        self._diag_result = "\n".join(results)
        self._diag_thread_done = True

    def _test_single_ip(self, ip: str, dc: str, wss: str) -> str:
        import socket, ssl, time

        # TCP connect
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5)
        t0 = time.time()
        try:
            s.connect((ip, 443))
            tcp_ms = (time.time() - t0) * 1000
        except Exception:
            s.close()
            return f"{ip:<20} {dc:<12} {'FAIL':>8}  {'—':>8}  TCP не подключается"

        # TLS handshake
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        t1 = time.time()
        try:
            ss = ctx.wrap_socket(s, server_hostname="telegram.org")
            tls_ms = (time.time() - t1) * 1000
            ss.close()
            return f"{ip:<20} {dc:<12} {tcp_ms:>6.0f}ms  {tls_ms:>6.0f}ms  OK"
        except ssl.SSLError as e:
            tls_ms = (time.time() - t1) * 1000
            s.close()
            return f"{ip:<20} {dc:<12} {tcp_ms:>6.0f}ms  {tls_ms:>6.0f}ms  BLOCKED ({e.reason})"
        except socket.timeout:
            s.close()
            return f"{ip:<20} {dc:<12} {tcp_ms:>6.0f}ms  {'5000':>6}ms  TIMEOUT"
        except Exception as e:
            s.close()
            return f"{ip:<20} {dc:<12} {tcp_ms:>6.0f}ms  {'—':>8}  {type(e).__name__}"

    def _test_sni_vs_ip(self) -> str:
        """Test if blocking is SNI-based or IP-based."""
        import socket, ssl, time

        ip = "149.154.167.50"  # DC2
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5)
        try:
            s.connect((ip, 443))
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            t0 = time.time()
            ss = ctx.wrap_socket(s, server_hostname="example.com")
            ms = (time.time() - t0) * 1000
            ss.close()
            return f"TLS с чужим SNI (example.com → {ip}): OK ({ms:.0f}ms) → блокировка по SNI"
        except ssl.SSLError:
            s.close()
            return f"TLS с чужим SNI (example.com → {ip}): BLOCKED → блокировка по IP (не SNI)"
        except socket.timeout:
            s.close()
            return f"TLS с чужим SNI (example.com → {ip}): TIMEOUT → блокировка по IP (не SNI)"
        except Exception as e:
            s.close()
            return f"TLS с чужим SNI: {type(e).__name__}"

    def _test_http_port80(self) -> str:
        """Test HTTP on port 80 (no TLS)."""
        import socket, time

        ip = "149.154.167.50"
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5)
        try:
            t0 = time.time()
            s.connect((ip, 80))
            s.send(b"GET / HTTP/1.0\r\nHost: test\r\n\r\n")
            s.settimeout(3)
            data = s.recv(1024)
            ms = (time.time() - t0) * 1000
            s.close()
            return f"HTTP {ip}:80 → {len(data)} байт ({ms:.0f}ms) — НЕ блокируется"
        except socket.timeout:
            s.close()
            return f"HTTP {ip}:80 → TIMEOUT — блокируется"
        except Exception as e:
            s.close()
            return f"HTTP {ip}:80 → {type(e).__name__}"

    def _build_summary(self, lines: list[str]) -> str:
        blocked = sum(1 for l in lines if "BLOCKED" in l or "TIMEOUT" in l)
        ok = sum(1 for l in lines if l.strip().endswith("OK"))
        sni_block = any("блокировка по SNI" in l for l in lines)
        ip_block = any("блокировка по IP" in l for l in lines)
        http_ok = any("НЕ блокируется" in l for l in lines)

        summary = ["Итог:"]
        summary.append(f"  Доступно: {ok}  |  Заблокировано: {blocked}")
        if sni_block:
            summary.append("  Тип: блокировка по SNI → winws2 фрагментация ClientHello поможет")
        elif ip_block:
            if http_ok:
                summary.append("  Тип: блокировка TLS к IP (HTTP работает) → winws2 может помочь")
            else:
                summary.append("  Тип: полная блокировка по IP → только VPN или WSS прокси")
        summary.append(f"  WSS relay (149.154.167.220): {'доступен' if any('WSS relay' in l and 'OK' in l for l in lines) else 'недоступен'}")
        return "\n".join(summary)

    def _update_diag(self, text: str):
        self._diag_edit.setPlainText(text)
        sb = self._diag_edit.verticalScrollBar()
        if sb:
            sb.setValue(sb.maximum())

    def _diag_finished(self):
        self._btn_run_diag.setEnabled(True)
        self._btn_run_diag.setText("Запустить диагностику")

    def _on_copy_diag(self):
        text = self._diag_edit.toPlainText()
        clipboard = QGuiApplication.clipboard()
        if clipboard and text:
            clipboard.setText(text)
            if _HAS_FLUENT and InfoBar is not None:
                try:
                    InfoBar.success(
                        title="Скопировано",
                        content="Результат диагностики",
                        parent=self,
                        duration=2000,
                        position=InfoBarPosition.TOP,
                    )
                except Exception:
                    pass

    def _connect_signals(self):
        mgr = _get_proxy_manager()
        mgr.status_changed.connect(self._on_status_changed)
        mgr.stats_updated.connect(self._on_stats_updated)

        self._autostart_toggle.toggled.connect(self._on_autostart_changed)
        self._port_spin.valueChanged.connect(self._on_port_changed)

    def _load_settings(self):
        """Load settings from registry."""
        try:
            from config.reg import get_tg_proxy_port, get_tg_proxy_autostart
            port = get_tg_proxy_port()
            if port is None or port < 1024 or port > 65535:
                port = 1353
            self._port_spin.blockSignals(True)
            self._port_spin.setValue(port)
            self._port_spin.blockSignals(False)
            self._autostart_toggle.toggle.setChecked(get_tg_proxy_autostart())
        except Exception as e:
            log(f"TelegramProxyPage: load settings error: {e}", "WARNING")
            self._port_spin.blockSignals(True)
            self._port_spin.setValue(1353)
            self._port_spin.blockSignals(False)

    def _auto_start_check(self):
        """Auto-start proxy if autostart is enabled."""
        try:
            from config.reg import get_tg_proxy_autostart
            if get_tg_proxy_autostart():
                self._start_proxy()
                self._try_auto_deeplink()
        except Exception:
            pass

    def _try_auto_deeplink(self):
        """Open tg:// deep link automatically on first start."""
        try:
            from config.reg import reg
            from config import REGISTRY_PATH
            done = reg(REGISTRY_PATH, "TgProxyDeeplinkDone")
            if done:
                return
            reg(REGISTRY_PATH, "TgProxyDeeplinkDone", 1)
            QTimer.singleShot(2000, self._on_open_in_telegram)
            self._append_log_line("Auto-opening Telegram proxy setup link...")
        except Exception:
            pass

    # -- Log display (throttled via QTimer, no trimming) --

    def _flush_log_buffer(self):
        """Called every 500ms by QTimer. Drains new lines from ProxyLogger."""
        mgr = _get_proxy_manager()
        new_lines = mgr.proxy_logger.drain()
        if not new_lines:
            return

        self._log_edit.setUpdatesEnabled(False)
        try:
            for line in new_lines:
                self._log_edit.appendPlainText(line)
        finally:
            self._log_edit.setUpdatesEnabled(True)

        # Auto-scroll to bottom
        sb = self._log_edit.verticalScrollBar()
        if sb:
            sb.setValue(sb.maximum())

    def _append_log_line(self, msg: str):
        """Append a single line to the log."""
        mgr = _get_proxy_manager()
        mgr.proxy_logger.log(msg)

    # -- Log tab buttons --

    def _on_copy_all_logs(self):
        text = self._log_edit.toPlainText()
        clipboard = QGuiApplication.clipboard()
        if clipboard and text:
            clipboard.setText(text)
            if _HAS_FLUENT and InfoBar is not None:
                try:
                    InfoBar.success(
                        title="Скопировано",
                        content=f"{len(text.splitlines())} строк",
                        parent=self,
                        duration=2000,
                        position=InfoBarPosition.TOP,
                    )
                except Exception:
                    pass

    def _on_open_log_file(self):
        import os, subprocess
        mgr = _get_proxy_manager()
        path = mgr.proxy_logger.log_file_path
        if os.path.exists(path):
            subprocess.Popen(["explorer", "/select,", os.path.normpath(path)])
        else:
            self._append_log_line(f"Log file not found: {path}")

    def _on_clear_logs(self):
        self._log_edit.clear()

    # -- Handlers --

    def _on_toggle_proxy(self):
        mgr = _get_proxy_manager()
        if mgr.is_running:
            self._stop_proxy()
        else:
            self._start_proxy()

    def _start_proxy(self):
        mgr = _get_proxy_manager()
        port = self._port_spin.value()
        ok = mgr.start_proxy(port=port, mode="socks5")
        if ok:
            try:
                from config.reg import set_tg_proxy_enabled
                set_tg_proxy_enabled(True)
            except Exception:
                pass

    def _stop_proxy(self):
        mgr = _get_proxy_manager()
        mgr.stop_proxy()
        try:
            from config.reg import set_tg_proxy_enabled
            set_tg_proxy_enabled(False)
        except Exception:
            pass

    def _on_status_changed(self, running: bool):
        self._status_dot.set_active(running)
        if running:
            port = _get_proxy_manager().port
            self._status_label.setText(f"Работает на 127.0.0.1:{port}")
            self._btn_toggle.setText("Остановить")
        else:
            self._status_label.setText("Остановлен")
            self._btn_toggle.setText("Запустить")
            self._stats_label.setText("")

        self._port_spin.setEnabled(not running)

    def _on_stats_updated(self, stats):
        if stats is None:
            return

        def _fmt_bytes(n: int) -> str:
            if n < 1024:
                return f"{n} B"
            if n < 1024 * 1024:
                return f"{n / 1024:.1f} KB"
            if n < 1024 * 1024 * 1024:
                return f"{n / (1024 * 1024):.1f} MB"
            return f"{n / (1024 * 1024 * 1024):.2f} GB"

        def _fmt_speed(n: int, secs: float) -> str:
            if secs <= 0:
                return "0 B/s"
            rate = n / secs
            if rate < 1024:
                return f"{rate:.0f} B/s"
            if rate < 1024 * 1024:
                return f"{rate / 1024:.1f} KB/s"
            return f"{rate / (1024 * 1024):.1f} MB/s"

        uptime = stats.uptime_seconds
        mins, secs = divmod(int(uptime), 60)
        hrs, mins = divmod(mins, 60)
        uptime_str = f"{hrs}:{mins:02d}:{secs:02d}" if hrs else f"{mins}:{secs:02d}"

        now_sent = stats.bytes_sent
        now_recv = stats.bytes_received
        prev_sent = getattr(self, '_prev_bytes_sent', 0)
        prev_recv = getattr(self, '_prev_bytes_received', 0)
        delta_sent = now_sent - prev_sent
        delta_recv = now_recv - prev_recv
        self._prev_bytes_sent = now_sent
        self._prev_bytes_received = now_recv
        interval = 2.0

        self._stats_label.setText(
            f"Подключения: {stats.active_connections} акт. / {stats.total_connections} всего  |  "
            f"↑ {_fmt_bytes(now_sent)} ({_fmt_speed(delta_sent, interval)})  "
            f"↓ {_fmt_bytes(now_recv)} ({_fmt_speed(delta_recv, interval)})  |  "
            f"Uptime: {uptime_str}"
        )

    def _on_autostart_changed(self, checked: bool):
        try:
            from config.reg import set_tg_proxy_autostart
            set_tg_proxy_autostart(checked)
        except Exception:
            pass

    def _on_port_changed(self, port: int):
        try:
            from config.reg import set_tg_proxy_port
            set_tg_proxy_port(port)
        except Exception:
            pass

    def _on_open_in_telegram(self):
        """Open tg://socks deep link to auto-configure Telegram."""
        port = self._port_spin.value()
        url = f"tg://socks?server=127.0.0.1&port={port}"
        try:
            webbrowser.open(url)
            self._append_log_line(f"Opened deep link: {url}")
        except Exception as e:
            self._append_log_line(f"Failed to open link: {e}")

    def _on_copy_link(self):
        """Copy proxy deep link to clipboard."""
        port = self._port_spin.value()
        url = f"tg://socks?server=127.0.0.1&port={port}"
        clipboard = QGuiApplication.clipboard()
        if clipboard:
            clipboard.setText(url)
            self._append_log_line(f"Copied to clipboard: {url}")
            if _HAS_FLUENT and InfoBar is not None:
                try:
                    InfoBar.success(
                        title="Скопировано",
                        content=url,
                        parent=self,
                        duration=2000,
                        position=InfoBarPosition.TOP,
                    )
                except Exception:
                    pass

    def cleanup(self):
        """Called on app exit."""
        self._log_timer.stop()
        mgr = _get_proxy_manager()
        mgr.cleanup()
