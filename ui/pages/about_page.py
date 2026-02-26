# ui/pages/about_page.py
"""Страница О программе — версия, подписка, поддержка, справка"""

from __future__ import annotations

import os
import subprocess
import sys
import time
import webbrowser

import qtawesome as qta
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QStackedWidget,
    QFrame, QSizePolicy,
)

from .base_page import BasePage
from ui.compat_widgets import SettingsCard, ActionButton, SettingsRow
from ui.theme import get_theme_tokens
from log import log

try:
    from qfluentwidgets import (
        SubtitleLabel, BodyLabel, StrongBodyLabel, CaptionLabel,
        SegmentedWidget, InfoBar,
        HyperlinkCard, PushSettingCard, SettingCardGroup, FluentIcon,
    )
    _HAS_FLUENT = True
except ImportError:
    _HAS_FLUENT = False
    FluentIcon = None
    InfoBar = None

try:
    from ui.theme_semantic import get_semantic_palette
    _HAS_SEMANTIC = True
except ImportError:
    _HAS_SEMANTIC = False
    get_semantic_palette = None


def _make_section_label(text: str, parent: QWidget | None = None) -> QLabel:
    """Создаёт заголовок секции для использования внутри sub-layout."""
    if _HAS_FLUENT:
        lbl = StrongBodyLabel(text, parent)
    else:
        lbl = QLabel(text, parent)
        lbl.setStyleSheet("font-size: 13px; font-weight: 600; padding-top: 8px; padding-bottom: 4px;")
    lbl.setProperty("tone", "primary")
    return lbl


class AboutPage(BasePage):
    """Страница О программе с вкладками: О программе / Поддержка / Справка"""

    _POLL_INTERVAL_MS = 1500
    _POLL_TIMEOUT_S = 120

    def __init__(self, parent=None):
        super().__init__("О программе", "Версия, подписка и информация", parent)

        # ZapretHub state
        self._zaphub_exe: str | None = None
        self._zaphub_installing: bool = False
        self._poll_timer: QTimer | None = None
        self._poll_deadline_ts: float | None = None

        # UI refs (support tab)
        self._zaphub_status_label: QLabel | None = None
        self._zaphub_action_btn: ActionButton | None = None
        self._hub_icon_label: QLabel | None = None

        # Tab lazy init flags
        self._support_tab_initialized = False
        self._help_tab_initialized = False

        from qfluentwidgets import qconfig
        qconfig.themeChanged.connect(lambda _: self._apply_theme())
        qconfig.themeColorChanged.connect(lambda _: self._apply_theme())

        self._build_ui()

    # ─────────────────────────────────────────────────────────────────────────
    # UI building
    # ─────────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        # ── Pivot (tabs) ──────────────────────────────────────────────────
        if _HAS_FLUENT:
            self.tabs_pivot = SegmentedWidget()
            self.tabs_pivot.addItem(routeKey="about", text=" О ПРОГРАММЕ",
                                    onClick=lambda: self._switch_tab(0))
            self.tabs_pivot.addItem(routeKey="support", text=" ПОДДЕРЖКА",
                                    onClick=lambda: self._switch_tab(1))
            self.tabs_pivot.addItem(routeKey="help", text=" СПРАВКА",
                                    onClick=lambda: self._switch_tab(2))
            self.tabs_pivot.setCurrentItem("about")
            self.tabs_pivot.setItemFontSize(13)
            self.add_widget(self.tabs_pivot)

        # ── QStackedWidget ────────────────────────────────────────────────
        self.stacked_widget = QStackedWidget()

        # Tab 0: О программе
        self._about_tab = QWidget()
        about_layout = QVBoxLayout(self._about_tab)
        about_layout.setContentsMargins(0, 0, 0, 0)
        about_layout.setSpacing(16)
        self._build_about_content(about_layout)

        # Tab 1: Поддержка (lazy)
        self._support_tab = QWidget()
        self._support_layout = QVBoxLayout(self._support_tab)
        self._support_layout.setContentsMargins(0, 0, 0, 0)
        self._support_layout.setSpacing(16)

        # Tab 2: Справка (lazy)
        self._help_tab = QWidget()
        self._help_layout = QVBoxLayout(self._help_tab)
        self._help_layout.setContentsMargins(0, 0, 0, 0)
        self._help_layout.setSpacing(16)

        self.stacked_widget.addWidget(self._about_tab)
        self.stacked_widget.addWidget(self._support_tab)
        self.stacked_widget.addWidget(self._help_tab)

        self.add_widget(self.stacked_widget)

    def _switch_tab(self, index: int):
        if index == 1 and not self._support_tab_initialized:
            self._support_tab_initialized = True
            try:
                self._build_support_content(self._support_layout)
            except Exception as e:
                log(f"Ошибка построения вкладки поддержки: {e}", "ERROR")

        if index == 2 and not self._help_tab_initialized:
            self._help_tab_initialized = True
            try:
                self._build_help_content(self._help_layout)
            except Exception as e:
                log(f"Ошибка построения вкладки справки: {e}", "ERROR")

        self.stacked_widget.setCurrentIndex(index)

        if _HAS_FLUENT and hasattr(self, "tabs_pivot"):
            keys = ["about", "support", "help"]
            try:
                self.tabs_pivot.setCurrentItem(keys[index])
            except Exception:
                pass

        if index == 1:
            try:
                self._refresh_zaphub_state()
            except Exception:
                pass

    # ─────────────────────────────────────────────────────────────────────────
    # Tab 0: О программе
    # ─────────────────────────────────────────────────────────────────────────

    def _build_about_content(self, layout: QVBoxLayout):
        from config import APP_VERSION
        tokens = get_theme_tokens()

        # ── Версия ────────────────────────────────────────────────────────
        layout.addWidget(_make_section_label("Версия"))

        version_card = SettingsCard()
        version_layout = QHBoxLayout()
        version_layout.setSpacing(16)

        icon_label = QLabel()
        icon_label.setPixmap(qta.icon('fa5s.shield-alt', color=tokens.accent_hex).pixmap(40, 40))
        icon_label.setFixedSize(48, 48)
        version_layout.addWidget(icon_label)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        if _HAS_FLUENT:
            name_label = SubtitleLabel("Zapret 2 GUI")
            version_label = CaptionLabel(f"Версия {APP_VERSION}")
        else:
            name_label = QLabel("Zapret 2 GUI")
            name_label.setStyleSheet(f"color: {tokens.fg}; font-size: 16px; font-weight: 600;")
            version_label = QLabel(f"Версия {APP_VERSION}")
            version_label.setStyleSheet(f"color: {tokens.fg_muted}; font-size: 12px;")
        text_layout.addWidget(name_label)
        text_layout.addWidget(version_label)
        version_layout.addLayout(text_layout, 1)

        self.update_btn = ActionButton("Настройка обновлений", "fa5s.sync-alt")
        self.update_btn.setFixedHeight(36)
        version_layout.addWidget(self.update_btn)

        version_card.add_layout(version_layout)
        layout.addWidget(version_card)

        layout.addSpacing(16)

        # ── Устройство ────────────────────────────────────────────────────
        layout.addWidget(_make_section_label("Устройство"))

        device_card = SettingsCard()
        device_layout = QHBoxLayout()
        device_layout.setSpacing(16)

        device_icon = QLabel()
        device_icon.setPixmap(qta.icon('fa5s.key', color=tokens.accent_hex).pixmap(20, 20))
        device_icon.setFixedSize(24, 24)
        device_layout.addWidget(device_icon)

        try:
            from tgram import get_client_id
            client_id = get_client_id()
        except Exception:
            client_id = ""

        device_text_layout = QVBoxLayout()
        device_text_layout.setSpacing(2)
        if _HAS_FLUENT:
            device_title = BodyLabel("ID устройства")
            self.client_id_label = CaptionLabel(client_id or "—")
        else:
            device_title = QLabel("ID устройства")
            device_title.setStyleSheet(f"color: {tokens.fg}; font-size: 13px; font-weight: 500;")
            self.client_id_label = QLabel(client_id or "—")
            self.client_id_label.setStyleSheet(f"color: {tokens.fg_muted}; font-size: 12px;")
        self.client_id_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        device_text_layout.addWidget(device_title)
        device_text_layout.addWidget(self.client_id_label)
        device_layout.addLayout(device_text_layout, 1)

        copy_btn = ActionButton("Копировать ID", "fa5s.copy")
        copy_btn.setFixedHeight(36)
        copy_btn.clicked.connect(self._copy_client_id)
        device_layout.addWidget(copy_btn)

        device_card.add_layout(device_layout)
        layout.addWidget(device_card)

        layout.addSpacing(16)

        # ── Подписка ──────────────────────────────────────────────────────
        layout.addWidget(_make_section_label("Подписка"))

        sub_card = SettingsCard()
        sub_layout = QVBoxLayout()
        sub_layout.setSpacing(12)

        sub_status_layout = QHBoxLayout()
        sub_status_layout.setSpacing(8)

        self.sub_status_icon = QLabel()
        self.sub_status_icon.setPixmap(qta.icon('fa5s.user', color=tokens.fg_faint).pixmap(18, 18))
        self.sub_status_icon.setFixedSize(22, 22)
        sub_status_layout.addWidget(self.sub_status_icon)

        if _HAS_FLUENT:
            self.sub_status_label = StrongBodyLabel("Free версия")
        else:
            self.sub_status_label = QLabel("Free версия")
            self.sub_status_label.setStyleSheet(f"color: {tokens.fg}; font-size: 13px; font-weight: 500;")
        sub_status_layout.addWidget(self.sub_status_label, 1)
        sub_layout.addLayout(sub_status_layout)

        if _HAS_FLUENT:
            sub_desc = CaptionLabel(
                "Подписка Zapret Premium открывает доступ к дополнительным темам, "
                "приоритетной поддержке и VPN-сервису."
            )
        else:
            sub_desc = QLabel(
                "Подписка Zapret Premium открывает доступ к дополнительным темам, "
                "приоритетной поддержке и VPN-сервису."
            )
            sub_desc.setStyleSheet(f"color: {tokens.fg_muted}; font-size: 11px;")
        sub_desc.setWordWrap(True)
        sub_layout.addWidget(sub_desc)

        sub_btns = QHBoxLayout()
        sub_btns.setSpacing(8)
        self.premium_btn = ActionButton("Premium и VPN", "fa5s.star", accent=True)
        self.premium_btn.setFixedHeight(36)
        sub_btns.addWidget(self.premium_btn)
        sub_btns.addStretch()
        sub_layout.addLayout(sub_btns)

        sub_card.add_layout(sub_layout)
        layout.addWidget(sub_card)

        layout.addStretch()

    def _copy_client_id(self) -> None:
        try:
            cid = self.client_id_label.text().strip() if hasattr(self, "client_id_label") else ""
            if not cid or cid == "—":
                return
            QGuiApplication.clipboard().setText(cid)
        except Exception as e:
            log(f"Ошибка копирования ID: {e}", "DEBUG")

    def update_subscription_status(self, is_premium: bool, days: int | None = None):
        """Обновляет отображение статуса подписки"""
        tokens = get_theme_tokens()
        if is_premium:
            self.sub_status_icon.setPixmap(qta.icon('fa5s.star', color='#ffc107').pixmap(18, 18))
            if days:
                self.sub_status_label.setText(f"Premium (осталось {days} дней)")
            else:
                self.sub_status_label.setText("Premium активен")
        else:
            self.sub_status_icon.setPixmap(qta.icon('fa5s.user', color=tokens.fg_faint).pixmap(18, 18))
            self.sub_status_label.setText("Free версия")

    # ─────────────────────────────────────────────────────────────────────────
    # Tab 1: Поддержка
    # ─────────────────────────────────────────────────────────────────────────

    def _build_support_content(self, layout: QVBoxLayout):
        tokens = get_theme_tokens()

        # ── ZapretHub ─────────────────────────────────────────────────────
        layout.addWidget(_make_section_label("ZapretHub"))

        hub_card = SettingsCard()
        hub_layout = QHBoxLayout()
        hub_layout.setSpacing(16)

        icon_label = QLabel()
        icon_label.setPixmap(qta.icon("fa5s.users", color=tokens.accent_hex).pixmap(36, 36))
        icon_label.setFixedSize(44, 44)
        self._hub_icon_label = icon_label
        hub_layout.addWidget(icon_label)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)

        if _HAS_FLUENT:
            title = StrongBodyLabel("ZapretHub")
            title.setProperty("tone", "primary")
            text_layout.addWidget(title)
            desc = CaptionLabel("Центр сообщества Zapret: стратегии, пресеты и форум.")
            desc.setWordWrap(True)
            desc.setProperty("tone", "muted")
            text_layout.addWidget(desc)
            self._zaphub_status_label = CaptionLabel("Статус: проверяю…")
        else:
            title = QLabel("ZapretHub")
            text_layout.addWidget(title)
            desc = QLabel("Центр сообщества Zapret: стратегии, пресеты и форум.")
            desc.setWordWrap(True)
            text_layout.addWidget(desc)
            self._zaphub_status_label = QLabel("Статус: проверяю…")

        self._zaphub_status_label.setStyleSheet(f"color: {tokens.fg_muted};")
        text_layout.addWidget(self._zaphub_status_label)
        hub_layout.addLayout(text_layout, 1)

        self._zaphub_action_btn = ActionButton("…", "fa5s.download", accent=True)
        self._zaphub_action_btn.setProperty("noDrag", True)
        self._zaphub_action_btn.setFixedHeight(36)
        self._zaphub_action_btn.clicked.connect(self._on_zaphub_action_clicked)
        hub_layout.addWidget(self._zaphub_action_btn)

        hub_card.add_layout(hub_layout)
        layout.addWidget(hub_card)

        layout.addSpacing(16)

        # ── Каналы поддержки ──────────────────────────────────────────────
        layout.addWidget(_make_section_label("Каналы поддержки"))

        channels_card = SettingsCard()

        tg_row = SettingsRow(
            "fa5b.telegram",
            "Telegram поддержка",
            "Помощь и вопросы по использованию",
        )
        tg_btn = ActionButton("Открыть", "fa5s.external-link-alt", accent=False)
        tg_btn.setProperty("noDrag", True)
        tg_btn.clicked.connect(self._open_telegram_support)
        tg_row.set_control(tg_btn)
        channels_card.add_widget(tg_row)

        dc_row = SettingsRow(
            "fa5b.discord",
            "Discord сервер",
            "Сообщество и живое общение",
        )
        dc_btn = ActionButton("Открыть", "fa5s.external-link-alt", accent=False)
        dc_btn.setProperty("noDrag", True)
        dc_btn.clicked.connect(self._open_discord)
        dc_row.set_control(dc_btn)
        channels_card.add_widget(dc_row)

        layout.addWidget(channels_card)

        layout.addStretch()

        # Начальное состояние
        self._refresh_zaphub_state()

    # ZapretHub logic --------------------------------------------------------

    def _on_zaphub_action_clicked(self) -> None:
        try:
            self._refresh_zaphub_state()
        except Exception:
            pass
        if self._zaphub_exe and os.path.exists(self._zaphub_exe):
            self._open_zaphub()
            return
        self._install_zaphub()

    def _refresh_zaphub_state(self) -> None:
        exe = self._detect_zaphub_exe()
        self._zaphub_exe = exe

        status_label = self._zaphub_status_label
        action_btn = self._zaphub_action_btn
        if status_label is None or action_btn is None:
            return

        if exe and os.path.exists(exe):
            self._zaphub_installing = False
            status_label.setText("Статус: установлен")
            if _HAS_SEMANTIC and get_semantic_palette:
                semantic = get_semantic_palette()
                status_label.setStyleSheet(f"color: {semantic.success};")
            action_btn.setText("Открыть")
            action_btn.setIcon(qta.icon("fa5s.play", color=get_theme_tokens().fg))
            action_btn.setEnabled(True)
        elif self._zaphub_installing:
            action_btn.setEnabled(False)
        else:
            status_label.setText("Статус: не установлен")
            tokens = get_theme_tokens()
            status_label.setStyleSheet(f"color: {tokens.fg_muted};")
            action_btn.setText("Установить")
            action_btn.setIcon(qta.icon("fa5s.download", color=tokens.fg))
            action_btn.setEnabled(True)

    def _open_zaphub(self) -> None:
        try:
            if not self._zaphub_exe:
                raise FileNotFoundError("ZapretHub не найден")
            os.startfile(self._zaphub_exe)  # noqa: S606
            log(f"Открыт ZapretHub: {self._zaphub_exe}", "INFO")
        except Exception as e:
            if InfoBar:
                InfoBar.warning(title="ZapretHub", content=f"Не удалось открыть ZapretHub:\n{e}",
                                parent=self.window())

    def _install_zaphub(self) -> None:
        installer = self._find_zaphub_installer()
        if not installer:
            if InfoBar:
                InfoBar.warning(
                    title="ZapretHub",
                    content="Установщик ZapretHub не найден.\n\nПереустановите Zapret2 или установите ZapretHub через основной установщик.",
                    parent=self.window(),
                )
            return

        action_btn = self._zaphub_action_btn
        status_label = self._zaphub_status_label
        if action_btn is not None:
            action_btn.setEnabled(False)
            action_btn.setText("Установка…")
            action_btn.setIcon(qta.icon("fa5s.spinner", color=get_theme_tokens().fg))
        if status_label is not None:
            status_label.setText("Статус: установка запущена…")
            if _HAS_SEMANTIC and get_semantic_palette:
                semantic = get_semantic_palette()
                status_label.setStyleSheet(f"color: {semantic.warning};")

        self._zaphub_installing = True
        args = [installer, "/S", "/SP-", "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"]

        try:
            try:
                subprocess.Popen(args)  # noqa: S603
            except OSError as e:
                if getattr(e, "winerror", None) == 740 and sys.platform == "win32":
                    try:
                        from updater.update import launch_installer_winapi
                        ok = launch_installer_winapi(installer, " ".join(args[1:]), os.path.dirname(installer))
                        if not ok:
                            raise
                    except Exception:
                        raise
                else:
                    raise

            log(f"Запущен установщик ZapretHub: {installer}", "INFO")
            self._start_polling_zaphub_install()
        except Exception as e:
            self._zaphub_installing = False
            if action_btn is not None:
                action_btn.setEnabled(True)
            if InfoBar:
                InfoBar.warning(title="ZapretHub", content=f"Не удалось запустить установку:\n{e}",
                                parent=self.window())
            try:
                self._refresh_zaphub_state()
            except Exception:
                pass

    def _start_polling_zaphub_install(self) -> None:
        now = time.time()
        self._poll_deadline_ts = now + self._POLL_TIMEOUT_S
        if self._poll_timer is None:
            self._poll_timer = QTimer(self)
            self._poll_timer.timeout.connect(self._poll_zaphub_install)
        self._poll_timer.start(self._POLL_INTERVAL_MS)

    def _poll_zaphub_install(self) -> None:
        try:
            self._refresh_zaphub_state()
        except Exception:
            pass
        if self._zaphub_exe and os.path.exists(self._zaphub_exe):
            if self._poll_timer is not None:
                self._poll_timer.stop()
            return
        if self._poll_deadline_ts is not None and time.time() >= self._poll_deadline_ts:
            if self._poll_timer is not None:
                self._poll_timer.stop()
            self._zaphub_installing = False
            try:
                self._refresh_zaphub_state()
            except Exception:
                pass

    def _find_zaphub_installer(self) -> str | None:
        try:
            appdata = os.environ.get("APPDATA", "")
            if appdata:
                p = os.path.join(appdata, "zaprettracker", "ZapretHub-Setup.exe")
                if os.path.exists(p):
                    return p
        except Exception:
            pass
        try:
            repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
            p = os.path.join(repo_root, "tracker", "ZapretHub-Setup-1.0.0.exe")
            if os.path.exists(p):
                return p
        except Exception:
            pass
        return None

    def _detect_zaphub_exe(self) -> str | None:
        try:
            local_appdata = os.environ.get("LOCALAPPDATA", "")
            appdata = os.environ.get("APPDATA", "")
            candidates: list[str] = []
            for base in (local_appdata, appdata):
                if not base:
                    continue
                candidates.extend([
                    os.path.join(base, "Programs", "ZapretHub", "ZapretHub.exe"),
                    os.path.join(base, "ZapretHub", "ZapretHub.exe"),
                    os.path.join(base, "zaprethub", "ZapretHub.exe"),
                    os.path.join(base, "zaprettracker", "ZapretHub.exe"),
                    os.path.join(base, "zaprettracker", "ZapretTracker.exe"),
                ])
            for p in candidates:
                if p and os.path.exists(p):
                    return p
        except Exception:
            pass

        if sys.platform != "win32":
            return None

        try:
            import winreg
        except Exception:
            return None

        hints = ("zaprethub", "zapret hub", "zapret-hub")
        exe_names = ("zaprethub.exe", "zaprettracker.exe", "zapret hub.exe")

        def _parse_display_icon(raw: str) -> str:
            raw = (raw or "").strip().strip('"')
            if "," in raw:
                raw = raw.split(",", 1)[0].strip().strip('"')
            return raw

        def _safe_get_value(hkey, name: str) -> str:
            try:
                v, _t = winreg.QueryValueEx(hkey, name)
                return str(v)
            except Exception:
                return ""

        def _has_hint(s: str) -> bool:
            s = (s or "").lower()
            if not s:
                return False
            s_compact = s.replace(" ", "").replace("-", "")
            for h in hints:
                h_l = h.lower()
                if h_l in s or h_l.replace(" ", "").replace("-", "") in s_compact:
                    return True
            return False

        roots = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        ]
        views: list[int] = []
        try:
            views.append(winreg.KEY_WOW64_64KEY)
            views.append(winreg.KEY_WOW64_32KEY)
        except Exception:
            views.append(0)

        matches: list[tuple[int, str]] = []

        for hive, root_path in roots:
            for view in views:
                try:
                    root = winreg.OpenKey(hive, root_path, 0, winreg.KEY_READ | view)
                except Exception:
                    continue
                try:
                    i = 0
                    while True:
                        try:
                            subkey_name = winreg.EnumKey(root, i)
                        except OSError:
                            break
                        i += 1
                        try:
                            h = winreg.OpenKey(root, subkey_name, 0, winreg.KEY_READ | view)
                        except Exception:
                            continue
                        try:
                            display_name = _safe_get_value(h, "DisplayName")
                            if not (_has_hint(display_name) or _has_hint(subkey_name)):
                                continue
                            install_location = _safe_get_value(h, "InstallLocation")
                            app_path = _safe_get_value(h, "Inno Setup: App Path")
                            display_icon = _parse_display_icon(_safe_get_value(h, "DisplayIcon"))

                            candidate: str | None = None
                            if display_icon.lower().endswith(".exe"):
                                candidate = display_icon
                            elif install_location:
                                candidate = os.path.join(install_location, "ZapretHub.exe")
                            elif app_path:
                                candidate = os.path.join(app_path, "ZapretHub.exe")

                            if not candidate:
                                continue

                            cand_l = candidate.lower().replace("/", "\\")
                            score = 0
                            dn_l = (display_name or "").lower()
                            sk_l = (subkey_name or "").lower()

                            if "zaprethub" in dn_l:
                                score += 120
                            if "zaprethub" in sk_l:
                                score += 120
                            if ("zapret" in dn_l and "hub" in dn_l) or ("zapret" in sk_l and "hub" in sk_l):
                                score += 60
                            if any(cand_l.endswith("\\" + n) for n in exe_names):
                                score += 25
                            if cand_l.endswith("\\zaprethub.exe"):
                                score += 10

                            if score > 0:
                                matches.append((score, candidate))
                        finally:
                            try:
                                winreg.CloseKey(h)
                            except Exception:
                                pass
                finally:
                    try:
                        winreg.CloseKey(root)
                    except Exception:
                        pass

        if not matches:
            return None

        matches.sort(key=lambda t: t[0], reverse=True)
        for _score, path in matches:
            try:
                if os.path.exists(path):
                    return path
            except Exception:
                continue

        return matches[0][1]

    def _open_telegram_support(self) -> None:
        try:
            from config.telegram_links import open_telegram_link
            open_telegram_link("zaprethelp")
            log("Открыт Telegram: zaprethelp", "INFO")
        except Exception as e:
            if InfoBar:
                InfoBar.warning(title="Ошибка", content=f"Не удалось открыть Telegram:\n{e}",
                                parent=self.window())

    def _open_discord(self) -> None:
        try:
            url = "https://discord.gg/kkcBDG2uws"
            webbrowser.open(url)
            log(f"Открыт Discord: {url}", "INFO")
        except Exception as e:
            if InfoBar:
                InfoBar.warning(title="Ошибка", content=f"Не удалось открыть Discord:\n{e}",
                                parent=self.window())

    # ─────────────────────────────────────────────────────────────────────────
    # Tab 2: Справка
    # ─────────────────────────────────────────────────────────────────────────

    def _build_help_content(self, layout: QVBoxLayout):
        self._add_motto_block(layout)
        layout.addSpacing(6)
        layout.addWidget(_make_section_label("Ссылки"))

        try:
            from config.urls import INFO_URL, ANDROID_URL
        except Exception:
            INFO_URL = ""
            ANDROID_URL = ""

        if not _HAS_FLUENT:
            layout.addStretch()
            return

        # ── Документация ──────────────────────────────────────────────────
        docs_group = SettingCardGroup("Документация", self.content)

        forum_card = PushSettingCard(
            "Открыть", FluentIcon.SEND,
            "Сайт-форум для новичков",
            "Авторизация через Telegram-бота",
        )
        forum_card.clicked.connect(self._open_forum_for_beginners)

        info_card = HyperlinkCard(
            INFO_URL, "Открыть",
            FluentIcon.INFO,
            "Что это такое?",
            "Руководство и ответы на вопросы",
        )

        folder_card = PushSettingCard(
            "Открыть", FluentIcon.FOLDER,
            "Папка с инструкциями",
            "Открыть локальную папку help",
        )
        folder_card.clicked.connect(self._open_help_folder)

        android_card = HyperlinkCard(
            ANDROID_URL, "Открыть",
            FluentIcon.PHONE,
            "На Android (Magisk Zapret, ByeByeDPI и др.)",
            "Открыть инструкцию на сайте",
        )

        github_card = HyperlinkCard(
            "https://github.com/youtubediscord/zapret", "Открыть",
            FluentIcon.GITHUB,
            "GitHub",
            "Исходный код и документация",
        )

        docs_group.addSettingCards([forum_card, info_card, folder_card, android_card, github_card])
        layout.addWidget(docs_group)
        layout.addSpacing(8)

        # ── Новости ───────────────────────────────────────────────────────
        news_group = SettingCardGroup("Новости", self.content)

        telegram_card = PushSettingCard(
            "Открыть", FluentIcon.MEGAPHONE,
            "Telegram канал",
            "Новости и обновления",
        )
        telegram_card.clicked.connect(self._open_telegram_news)

        youtube_card = HyperlinkCard(
            "https://www.youtube.com/@приватность", "Открыть",
            FluentIcon.PLAY,
            "YouTube канал",
            "Видео и обновления",
        )

        mastodon_card = HyperlinkCard(
            "https://mastodon.social/@zapret", "Открыть",
            FluentIcon.GLOBE,
            "Mastodon профиль",
            "Новости в Fediverse",
        )

        bastyon_card = HyperlinkCard(
            "https://bastyon.com/zapretgui", "Открыть",
            FluentIcon.GLOBE,
            "Bastyon профиль",
            "Новости в Bastyon",
        )

        news_group.addSettingCards([telegram_card, youtube_card, mastodon_card, bastyon_card])
        layout.addWidget(news_group)

        layout.addStretch()

    def _add_motto_block(self, layout: QVBoxLayout):
        tokens = get_theme_tokens()
        motto_wrap = QFrame()
        motto_wrap.setStyleSheet("QFrame { background: transparent; border: none; }")

        motto_row = QHBoxLayout(motto_wrap)
        motto_row.setContentsMargins(0, 0, 0, 0)
        motto_row.setSpacing(0)

        motto_text_wrap = QFrame()
        motto_text_wrap.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        motto_text_wrap.setStyleSheet("QFrame { background: transparent; border: none; }")

        motto_text_layout = QVBoxLayout(motto_text_wrap)
        motto_text_layout.setContentsMargins(0, 0, 0, 0)
        motto_text_layout.setSpacing(2)

        motto_title = QLabel("keep thinking, keep searching, keep learning....")
        motto_title.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
        motto_title.setWordWrap(True)
        motto_title.setStyleSheet(
            f"QLabel {{ color: {tokens.fg}; font-size: 25px; font-weight: 700; "
            f"letter-spacing: 0.8px; "
            f"font-family: 'Segoe UI Variable Display', 'Segoe UI', sans-serif; }}"
        )

        motto_translate = QLabel("Продолжай думать, продолжай искать, продолжай учиться....")
        motto_translate.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
        motto_translate.setWordWrap(True)
        motto_translate.setStyleSheet(
            f"QLabel {{ color: {tokens.fg_muted}; font-size: 17px; font-style: italic; "
            f"font-weight: 600; letter-spacing: 0.5px; "
            f"font-family: 'Palatino Linotype', 'Book Antiqua', 'Georgia', serif; "
            f"padding-top: 2px; }}"
        )

        motto_cta = QLabel("Zapret2 - думай свободно, ищи смелее, учись всегда.")
        motto_cta.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
        motto_cta.setWordWrap(True)
        motto_cta.setStyleSheet(
            f"QLabel {{ color: {tokens.fg_faint}; font-size: 12px; letter-spacing: 1.1px; "
            f"font-family: 'Segoe UI', sans-serif; text-transform: uppercase; "
            f"padding-top: 6px; }}"
        )

        motto_text_layout.addWidget(motto_title)
        motto_text_layout.addWidget(motto_translate)
        motto_text_layout.addWidget(motto_cta)
        motto_row.addWidget(motto_text_wrap, 1)
        layout.addWidget(motto_wrap)

    def _open_forum_for_beginners(self):
        try:
            from config.telegram_links import open_telegram_link
            open_telegram_link("nozapretinrussia_bot")
            log("Открыт Telegram-бот: nozapretinrussia_bot", "INFO")
        except Exception as e:
            if InfoBar:
                InfoBar.warning(title="Ошибка", content=f"Не удалось открыть Telegram-бота:\n{e}",
                                parent=self.window())

    def _open_help_folder(self):
        try:
            from config import HELP_FOLDER
            if os.path.exists(HELP_FOLDER):
                subprocess.Popen(f'explorer "{HELP_FOLDER}"')
                log(f"Открыта папка: {HELP_FOLDER}", "INFO")
            else:
                if InfoBar:
                    InfoBar.warning(title="Ошибка", content="Папка с инструкциями не найдена",
                                    parent=self.window())
        except Exception as e:
            if InfoBar:
                InfoBar.warning(title="Ошибка", content=f"Не удалось открыть папку:\n{e}",
                                parent=self.window())

    def _open_telegram_news(self):
        try:
            from config.telegram_links import open_telegram_link
            open_telegram_link("bypassblock")
            log("Открыт Telegram: bypassblock", "INFO")
        except Exception as e:
            if InfoBar:
                InfoBar.warning(title="Ошибка", content=f"Не удалось открыть Telegram:\n{e}",
                                parent=self.window())

    # ─────────────────────────────────────────────────────────────────────────
    # Theme
    # ─────────────────────────────────────────────────────────────────────────

    def _apply_theme(self) -> None:
        tokens = get_theme_tokens()
        if self._hub_icon_label is not None:
            try:
                self._hub_icon_label.setPixmap(
                    qta.icon("fa5s.users", color=tokens.accent_hex).pixmap(36, 36)
                )
            except Exception:
                pass
        try:
            self._refresh_zaphub_state()
        except Exception:
            pass

    # ─────────────────────────────────────────────────────────────────────────
    # showEvent
    # ─────────────────────────────────────────────────────────────────────────

    def showEvent(self, event):
        super().showEvent(event)
        if self._support_tab_initialized:
            try:
                self._refresh_zaphub_state()
            except Exception:
                pass
