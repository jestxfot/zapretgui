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
    QFrame,
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
    )
    _HAS_FLUENT = True
except ImportError:
    from PyQt6.QtWidgets import QSpinBox as SpinBox
    BodyLabel = QLabel
    CaptionLabel = QLabel
    StrongBodyLabel = QLabel
    InfoBar = None
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
            "Маршрутизация трафика Telegram через WebSocket для обхода блокировки по IP",
            parent,
        )
        self.parent_app = parent
        self._log_lines: list[str] = []
        self._max_log_lines = 200
        self._setup_ui()
        self._connect_signals()
        self._load_settings()
        # Auto-start if enabled
        QTimer.singleShot(500, self._auto_start_check)

    def _setup_ui(self):
        # ── Status card ──
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
        self.add_widget(self._status_card)

        # ── Quick setup card ──
        self.add_section_title("Быстрая настройка Telegram")
        self._setup_card = SettingsCard()

        setup_desc = CaptionLabel(
            "Нажмите кнопку ниже - Telegram автоматически добавит прокси. "
            "Настройка требуется один раз."
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

        self.add_widget(self._setup_card)

        # ── Settings card ──
        self.add_section_title("Настройки")
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

        self.add_widget(self._settings_card)

        # ── Instructions card ──
        self.add_section_title("Ручная настройка")
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

        self.add_widget(self._instructions_card)

        # ── Log card ──
        self.add_section_title("Лог подключений")
        self._log_edit = ScrollBlockingPlainTextEdit()
        self._log_edit.setReadOnly(True)
        self._log_edit.setFixedHeight(150)
        self._log_edit.setPlaceholderText("Лог подключений появится здесь...")
        self.add_widget(self._log_edit)

    def _connect_signals(self):
        mgr = _get_proxy_manager()
        mgr.status_changed.connect(self._on_status_changed)
        mgr.log_message.connect(self._on_log_message)
        mgr.stats_updated.connect(self._on_stats_updated)

        self._autostart_toggle.toggled.connect(self._on_autostart_changed)
        self._port_spin.valueChanged.connect(self._on_port_changed)

    def _load_settings(self):
        """Load settings from registry."""
        try:
            from config.reg import get_tg_proxy_port, get_tg_proxy_autostart
            port = get_tg_proxy_port()
            if port < 1024 or port > 65535:
                port = 1353
            self._port_spin.setValue(port)
            self._autostart_toggle.toggle.setChecked(get_tg_proxy_autostart())
        except Exception as e:
            log(f"TelegramProxyPage: load settings error: {e}", "WARNING")
            self._port_spin.setValue(1353)

    def _auto_start_check(self):
        """Auto-start proxy if autostart is enabled."""
        try:
            from config.reg import get_tg_proxy_autostart
            if get_tg_proxy_autostart():
                self._start_proxy()
                # Auto-open deep link on first ever start
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
                return  # Already done once
            # Mark as done
            reg(REGISTRY_PATH, "TgProxyDeeplinkDone", 1)
            # Open deep link after short delay (proxy needs to be ready)
            QTimer.singleShot(2000, self._on_open_in_telegram)
            self._on_log_message("Auto-opening Telegram proxy setup link...")
        except Exception:
            pass

    # ── Handlers ──

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

        # Disable port while running
        self._port_spin.setEnabled(not running)

    def _on_log_message(self, msg: str):
        self._log_lines.append(msg)
        if len(self._log_lines) > self._max_log_lines:
            self._log_lines = self._log_lines[-self._max_log_lines:]
        self._log_edit.setPlainText("\n".join(self._log_lines))
        # Auto-scroll to bottom
        sb = self._log_edit.verticalScrollBar()
        if sb:
            sb.setValue(sb.maximum())

    def _on_stats_updated(self, stats):
        if stats is None:
            return

        def _fmt_bytes(n: int) -> str:
            if n < 1024:
                return f"{n} B"
            if n < 1024 * 1024:
                return f"{n / 1024:.1f} KB"
            return f"{n / (1024 * 1024):.1f} MB"

        uptime = int(stats.uptime_seconds)
        mins, secs = divmod(uptime, 60)
        hrs, mins = divmod(mins, 60)
        uptime_str = f"{hrs}:{mins:02d}:{secs:02d}" if hrs else f"{mins}:{secs:02d}"

        self._stats_label.setText(
            f"Подключения: {stats.active_connections} акт. / {stats.total_connections} всего  |  "
            f"↑ {_fmt_bytes(stats.bytes_sent)}  ↓ {_fmt_bytes(stats.bytes_received)}  |  "
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
            self._on_log_message(f"Opened deep link: {url}")
        except Exception as e:
            self._on_log_message(f"Failed to open link: {e}")

    def _on_copy_link(self):
        """Copy proxy deep link to clipboard."""
        port = self._port_spin.value()
        url = f"tg://socks?server=127.0.0.1&port={port}"
        clipboard = QGuiApplication.clipboard()
        if clipboard:
            clipboard.setText(url)
            self._on_log_message(f"Copied to clipboard: {url}")
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
        mgr = _get_proxy_manager()
        mgr.cleanup()
