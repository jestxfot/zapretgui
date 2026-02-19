# ui/pages/zapret2/direct_control_page.py
"""Direct Zapret2 management page (Strategies landing for direct_zapret2)."""

import os
import re
import webbrowser

from PyQt6.QtCore import Qt, QObject, pyqtSignal, QThread
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
)
import qtawesome as qta

from ui.pages.base_page import BasePage
from ui.pages.strategies_page_base import ResetActionButton
from ui.compat_widgets import ActionButton, PrimaryActionButton, PulsingDot, SettingsCard, SettingsRow, set_tooltip
from ui.theme import get_theme_tokens

try:
    from qfluentwidgets import (
        CaptionLabel, StrongBodyLabel, SubtitleLabel, BodyLabel,
        IndeterminateProgressBar, MessageBox, InfoBar,
        SegmentedWidget, MessageBoxBase, CardWidget,
        PushButton, TransparentPushButton, FluentIcon,
    )
    _HAS_FLUENT_LABELS = True
except ImportError:
    from PyQt6.QtWidgets import QProgressBar as IndeterminateProgressBar  # type: ignore[assignment]
    MessageBox = None
    InfoBar = None
    MessageBoxBase = object  # type: ignore[assignment]
    SegmentedWidget = None  # type: ignore[assignment]
    CardWidget = None  # type: ignore[assignment]
    PushButton = None  # type: ignore[assignment]
    TransparentPushButton = None  # type: ignore[assignment]
    FluentIcon = None  # type: ignore[assignment]
    _HAS_FLUENT_LABELS = False


class DirectLaunchModeDialog(MessageBoxBase):
    """Диалог выбора Basic / Advanced режима прямого запуска."""

    def __init__(self, current_mode: str, parent=None):
        super().__init__(parent)
        self.titleLabel = SubtitleLabel("Режим прямого запуска", self.widget)
        self.mode_seg = SegmentedWidget(self.widget)
        self.mode_seg.addItem("basic", "Basic")
        self.mode_seg.addItem("advanced", "Advanced")
        self.mode_seg.setCurrentItem(
            current_mode if current_mode in ("basic", "advanced") else "basic"
        )
        self.basic_desc = BodyLabel(
            "Прямой запуск поддерживает несколько режимов: упрощенный и расширенный для профи. Настройки не сохраняются между режимами Вы можете выбрать любой. Рекомендуем начать с базового. Бывает что базовый из-за готовых стратегий плохо пробивает сайты, тогда рекомендуем попробовать продвинутый в котором можно более тонко настроить техники дурения.",
            self.widget,
        )
        self.basic_desc = BodyLabel(
            "Basic (базовый) — готовая таблица стратегий без понятия фаз. "
            "Собирать свои стратегии нельзя.",
            self.widget,
        )
        self.adv_desc = BodyLabel(
            "Advanced (продвинутый) — каждая функция настраивается индивидуально, "
            "можно выбирать несколько фаз и смешивать их друг с другом.",
            self.widget,
        )
        self.basic_desc.setWordWrap(True)
        self.adv_desc.setWordWrap(True)
        self.viewLayout.addWidget(self.titleLabel)
        self.viewLayout.addSpacing(8)
        self.viewLayout.addWidget(self.mode_seg)
        self.viewLayout.addSpacing(8)
        self.viewLayout.addWidget(self.basic_desc)
        self.viewLayout.addWidget(self.adv_desc)
        self.yesButton.setText("Применить")
        self.cancelButton.setText("Отмена")
        self.widget.setMinimumWidth(440)

    def get_mode(self) -> str:
        return self.mode_seg.currentRouteKey()


def _accent_fg_for_tokens(tokens) -> str:
    try:
        r, g, b = tokens.accent_rgb
        yiq = (r * 299 + g * 587 + b * 114) / 1000
        return "rgba(0, 0, 0, 0.90)" if yiq >= 160 else "rgba(245, 245, 245, 0.92)"
    except Exception:
        return "rgba(0, 0, 0, 0.90)"


_LIST_FILE_ARG_RE = re.compile(r"--(?:hostlist|ipset|hostlist-exclude|ipset-exclude)=([^\s]+)")
# Display only hostlist files (not ipset) in the preset card widget
_HOSTLIST_DISPLAY_RE = re.compile(r"--(?:hostlist|hostlist-exclude)=([^\s]+)")


class _CertificateInstallWorker(QObject):
    finished = pyqtSignal(bool, str)  # success, message

    def run(self) -> None:
        try:
            from startup.certificate_installer import reset_certificate_declined_flag, auto_install_certificate

            reset_certificate_declined_flag()
            success, message = auto_install_certificate(silent=True)
            self.finished.emit(bool(success), str(message))
        except Exception as e:
            self.finished.emit(False, str(e))


class BigActionButton(PrimaryActionButton):
    """Большая кнопка запуска (акцентная, PrimaryPushButton)."""

    def __init__(self, text: str, icon_name: str | None = None, accent: bool = True, parent=None):
        super().__init__(text, icon_name, parent)


class StopButton(ActionButton):
    """Кнопка остановки (нейтральная, PushButton)."""

    def __init__(self, text: str, icon_name: str | None = None, accent: bool = False, parent=None):
        super().__init__(text, icon_name, accent=False, parent=parent)


class Zapret2DirectControlPage(BasePage):
    """Страница управления для direct_zapret2 (главная вкладка раздела "Стратегии")."""

    navigate_to_presets = pyqtSignal()        # → PageName.ZAPRET2_USER_PRESETS
    navigate_to_direct_launch = pyqtSignal()  # → PageName.ZAPRET2_DIRECT
    navigate_to_blobs = pyqtSignal()          # → PageName.BLOBS
    direct_mode_changed = pyqtSignal(str)     # "basic" | "advanced"

    def __init__(self, parent=None):
        super().__init__(
            "Управление",
            "Настройка и запуск Zapret 2. Выберите готовые пресеты-конфиги (как раньше .bat), "
            "а при необходимости выполните тонкую настройку для каждой категории в разделе «Прямой запуск».",
            parent,
        )

        self._cert_install_thread: QThread | None = None
        self._cert_install_worker: _CertificateInstallWorker | None = None

        self._build_ui()
        self._update_stop_winws_button_text()

    def showEvent(self, a0):
        super().showEvent(a0)
        try:
            self._sync_program_settings()
        except Exception:
            pass
        try:
            self._load_advanced_settings()
        except Exception:
            pass
        try:
            self._refresh_direct_mode_label()
        except Exception:
            pass

    def _build_ui(self):
        # Статус работы
        self.add_section_title("Статус работы")

        status_card = SettingsCard()
        status_layout = QHBoxLayout()
        status_layout.setSpacing(16)

        self.status_dot = PulsingDot()
        status_layout.addWidget(self.status_dot)

        status_text = QVBoxLayout()
        status_text.setContentsMargins(0, 0, 0, 0)
        status_text.setSpacing(2)

        if _HAS_FLUENT_LABELS:
            self.status_title = StrongBodyLabel("Проверка...")
            self.status_desc = CaptionLabel("Определение состояния процесса")
        else:
            self.status_title = QLabel("Проверка...")
            self.status_title.setStyleSheet("QLabel { font-size: 15px; font-weight: 600; }")
            self.status_desc = QLabel("Определение состояния процесса")
            self.status_desc.setStyleSheet("QLabel { font-size: 12px; }")
        status_text.addWidget(self.status_title)
        status_text.addWidget(self.status_desc)

        status_layout.addLayout(status_text, 1)
        status_card.add_layout(status_layout)
        self.add_widget(status_card)

        self.add_spacing(16)

        # Управление
        self.add_section_title("Управление Zapret 2")

        control_card = SettingsCard()

        # Индикатор загрузки (бегающая полоска) - показываем рядом с кнопками управления
        self.progress_bar = IndeterminateProgressBar(self)
        self.progress_bar.setVisible(False)
        control_card.add_widget(self.progress_bar)

        if _HAS_FLUENT_LABELS:
            self.loading_label = CaptionLabel("")
        else:
            self.loading_label = QLabel("")
            self.loading_label.setStyleSheet("QLabel { font-size: 12px; padding-top: 4px; }")
        self.loading_label.setVisible(False)
        control_card.add_widget(self.loading_label)

        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(12)

        self.start_btn = BigActionButton("Запустить Zapret", "fa5s.play", accent=True)
        buttons_layout.addWidget(self.start_btn)

        self.stop_winws_btn = StopButton("Остановить только winws.exe", "fa5s.stop")
        self.stop_winws_btn.setVisible(False)
        buttons_layout.addWidget(self.stop_winws_btn)

        self.stop_and_exit_btn = StopButton("Остановить и закрыть программу", "fa5s.power-off")
        self.stop_and_exit_btn.setVisible(False)
        buttons_layout.addWidget(self.stop_and_exit_btn)

        buttons_layout.addStretch()
        control_card.add_layout(buttons_layout)
        self.add_widget(control_card)

        self.add_spacing(16)

        # ── Запуск: две вертикальные WinUI-карточки ──────────────────────
        self.add_section_title("Сменить пресет обхода блокировок")

        # Card A — Активный пресет (single-row: icon | text | button)
        preset_card = CardWidget()
        preset_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        preset_row = QHBoxLayout(preset_card)
        preset_row.setContentsMargins(16, 14, 16, 14)
        preset_row.setSpacing(12)

        preset_icon_lbl = QLabel()
        preset_icon_lbl.setPixmap(qta.icon("fa5s.star", color="#ffc107").pixmap(20, 20))
        preset_icon_lbl.setFixedSize(24, 24)
        preset_row.addWidget(preset_icon_lbl, 0, Qt.AlignmentFlag.AlignVCenter)

        preset_col = QVBoxLayout()
        preset_col.setSpacing(2)
        self.preset_name_label = StrongBodyLabel("Не выбран")
        self.active_preset_label = self.preset_name_label  # backward-compat alias
        if _HAS_FLUENT_LABELS:
            self.strategy_label = CaptionLabel("Нет активных листов")
        else:
            self.strategy_label = QLabel("Нет активных листов")
            self.strategy_label.setStyleSheet("QLabel { font-size: 11px; }")
        self.strategy_label.setWordWrap(True)
        self.strategy_label.setVisible(False)
        preset_col.addWidget(self.preset_name_label)
        preset_col.addWidget(CaptionLabel("Текущий активный пресет"))
        preset_row.addLayout(preset_col, 1)

        presets_btn = PushButton()
        presets_btn.setText("Мои пресеты")
        presets_btn.setIcon(FluentIcon.FOLDER)
        presets_btn.clicked.connect(self.navigate_to_presets.emit)
        preset_row.addWidget(presets_btn, 0, Qt.AlignmentFlag.AlignVCenter)
        self.add_widget(preset_card)

        self.add_spacing(8)

        # ── Запуск: две вертикальные WinUI-карточки ──────────────────────
        self.add_section_title("Настройте пресет более тонко через прямой запуск")

        # Card B — Прямой запуск (single-row: icon | text | buttons)
        direct_card = CardWidget()
        direct_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        direct_row = QHBoxLayout(direct_card)
        direct_row.setContentsMargins(16, 14, 16, 14)
        direct_row.setSpacing(12)

        direct_icon_lbl = QLabel()
        direct_icon_lbl.setPixmap(qta.icon("fa5s.play", color="#60cdff").pixmap(20, 20))
        direct_icon_lbl.setFixedSize(24, 24)
        direct_row.addWidget(direct_icon_lbl, 0, Qt.AlignmentFlag.AlignVCenter)

        direct_col = QVBoxLayout()
        direct_col.setSpacing(2)
        self.direct_mode_label = StrongBodyLabel("Basic")
        direct_col.addWidget(self.direct_mode_label)
        direct_col.addWidget(CaptionLabel("Режим прямого запуска"))
        direct_row.addLayout(direct_col, 1)

        direct_btns = QHBoxLayout()
        direct_btns.setSpacing(4)
        open_btn = PushButton()
        open_btn.setText("Открыть")
        open_btn.setIcon(FluentIcon.PLAY)
        open_btn.clicked.connect(self.navigate_to_direct_launch.emit)
        mode_btn = TransparentPushButton()
        mode_btn.setText("Изменить режим")
        mode_btn.clicked.connect(self._open_direct_mode_dialog)
        direct_btns.addWidget(open_btn)
        direct_btns.addWidget(mode_btn)
        direct_row.addLayout(direct_btns)
        self.add_widget(direct_card)

        self.add_spacing(8)

        # Backward-compat hidden attributes
        self.active_preset_desc = CaptionLabel("")
        self.active_preset_desc.setVisible(False)
        self.strategy_desc = CaptionLabel("")
        self.strategy_desc.setVisible(False)

        self.add_spacing(16)

        # Настройки программы
        self.add_section_title("Настройки программы")
        program_settings_card = SettingsCard()

        try:
            from ui.pages.dpi_settings_page import Win11ToggleSwitch
        except Exception:
            Win11ToggleSwitch = None  # type: ignore[assignment]

        auto_row = SettingsRow(
            "fa5s.bolt",
            "Автозагрузка DPI",
            "Запускать Zapret автоматически при старте программы",
        )
        self.auto_dpi_toggle = Win11ToggleSwitch() if Win11ToggleSwitch else ActionButton("Вкл/Выкл")
        self.auto_dpi_toggle.setProperty("noDrag", True)
        if hasattr(self.auto_dpi_toggle, "toggled"):
            self.auto_dpi_toggle.toggled.connect(self._on_auto_dpi_toggled)
        auto_row.set_control(self.auto_dpi_toggle)
        program_settings_card.add_widget(auto_row)

        defender_row = SettingsRow(
            "fa5s.shield-alt",
            "Отключить Windows Defender",
            "Требуются права администратора",
        )
        self.defender_toggle = Win11ToggleSwitch() if Win11ToggleSwitch else ActionButton("Вкл/Выкл")
        self.defender_toggle.setProperty("noDrag", True)
        if hasattr(self.defender_toggle, "toggled"):
            self.defender_toggle.toggled.connect(self._on_defender_toggled)
        defender_row.set_control(self.defender_toggle)
        program_settings_card.add_widget(defender_row)

        max_row = SettingsRow(
            "fa5s.ban",
            "Блокировать установку MAX",
            "Блокирует запуск/установку MAX и домены в hosts",
        )
        self.max_block_toggle = Win11ToggleSwitch() if Win11ToggleSwitch else ActionButton("Вкл/Выкл")
        self.max_block_toggle.setProperty("noDrag", True)
        if hasattr(self.max_block_toggle, "toggled"):
            self.max_block_toggle.toggled.connect(self._on_max_blocker_toggled)
        max_row.set_control(self.max_block_toggle)
        program_settings_card.add_widget(max_row)

        reset_row = SettingsRow(
            "fa5s.undo",
            "Сбросить программу",
            "Очистить кэш проверок запуска (без удаления пресетов/настроек)",
        )
        self.reset_program_btn = ResetActionButton("Сбросить", confirm_text="Сбросить?")
        self.reset_program_btn.setProperty("noDrag", True)
        self.reset_program_btn.reset_confirmed.connect(self._on_reset_program_clicked)
        reset_row.set_control(self.reset_program_btn)
        program_settings_card.add_widget(reset_row)

        cert_row = SettingsRow(
            "fa5s.certificate",
            "Установить сертификат",
            "Необязательно. Добавляет корневой сертификат Zapret Developer в доверенные (текущий пользователь)",
        )
        self.install_cert_btn = ActionButton("Установить")
        self.install_cert_btn.setProperty("noDrag", True)
        self.install_cert_btn.clicked.connect(self._on_install_certificate_clicked)
        cert_row.set_control(self.install_cert_btn)
        program_settings_card.add_widget(cert_row)

        self.add_widget(program_settings_card)

        self.add_spacing(16)

        # ДОПОЛНИТЕЛЬНЫЕ НАСТРОЙКИ (direct_zapret2)
        self.add_section_title("Дополнительные настройки")

        self.advanced_card = SettingsCard("ДОПОЛНИТЕЛЬНЫЕ НАСТРОЙКИ")
        advanced_layout = QVBoxLayout()
        advanced_layout.setSpacing(6)

        advanced_desc = CaptionLabel("⚠ Изменяйте только если знаете что делаете") if _HAS_FLUENT_LABELS else QLabel("⚠ Изменяйте только если знаете что делаете")
        advanced_desc.setStyleSheet("color: #ff9800; padding-bottom: 8px;")
        advanced_layout.addWidget(advanced_desc)

        try:
            from ui.pages.dpi_settings_page import Win11ToggleRow
        except Exception:
            Win11ToggleRow = None  # type: ignore[assignment]

        self.discord_restart_toggle = (
            Win11ToggleRow(
                "mdi.discord",
                "Перезапуск Discord",
                "Автоперезапуск при смене стратегии",
                "#7289da",
            )
            if Win11ToggleRow
            else None
        )
        if self.discord_restart_toggle:
            self.discord_restart_toggle.toggled.connect(self._on_discord_restart_changed)
            advanced_layout.addWidget(self.discord_restart_toggle)

        self.wssize_toggle = (
            Win11ToggleRow(
                "fa5s.ruler-horizontal",
                "Включить --wssize",
                "Добавляет параметр размера окна TCP",
                "#9c27b0",
            )
            if Win11ToggleRow
            else None
        )
        if self.wssize_toggle:
            self.wssize_toggle.toggled.connect(self._on_wssize_toggled)
            advanced_layout.addWidget(self.wssize_toggle)

        self.debug_log_toggle = (
            Win11ToggleRow(
                "mdi.file-document-outline",
                "Включить лог-файл (--debug)",
                "Записывает логи winws в папку logs",
                "#00bcd4",
            )
            if Win11ToggleRow
            else None
        )
        if self.debug_log_toggle:
            self.debug_log_toggle.toggled.connect(self._on_debug_log_toggled)
            advanced_layout.addWidget(self.debug_log_toggle)

        self.advanced_card.add_layout(advanced_layout)
        self.add_widget(self.advanced_card)

        # Card C — Блобы (ссылка на страницу)
        blobs_card = CardWidget()
        blobs_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        blobs_row = QHBoxLayout(blobs_card)
        blobs_row.setContentsMargins(16, 14, 16, 14)
        blobs_row.setSpacing(12)

        blobs_icon_lbl = QLabel()
        blobs_icon_lbl.setPixmap(qta.icon("fa5s.file-archive", color="#9c27b0").pixmap(20, 20))
        blobs_icon_lbl.setFixedSize(24, 24)
        blobs_row.addWidget(blobs_icon_lbl, 0, Qt.AlignmentFlag.AlignVCenter)

        blobs_col = QVBoxLayout()
        blobs_col.setSpacing(2)
        blobs_col.addWidget(StrongBodyLabel("Блобы"))
        blobs_col.addWidget(CaptionLabel("Бинарные данные (.bin / hex) для стратегий"))
        blobs_row.addLayout(blobs_col, 1)

        blobs_open_btn = PushButton()
        blobs_open_btn.setText("Открыть")
        blobs_open_btn.setIcon(FluentIcon.FOLDER)
        blobs_open_btn.clicked.connect(self.navigate_to_blobs.emit)
        blobs_row.addWidget(blobs_open_btn, 0, Qt.AlignmentFlag.AlignVCenter)
        self.add_widget(blobs_card)
        
        # Дополнительные действия
        self.add_section_title("Дополнительно")
        extra_card = SettingsCard()
        extra_layout = QHBoxLayout()
        extra_layout.setSpacing(8)
        self.test_btn = ActionButton("Тест соединения", "fa5s.wifi")
        extra_layout.addWidget(self.test_btn)
        self.folder_btn = ActionButton("Открыть папку", "fa5s.folder-open")
        extra_layout.addWidget(self.folder_btn)
        self.docs_btn = ActionButton("Документация", "fa5s.book")
        self.docs_btn.clicked.connect(self._open_docs)
        extra_layout.addWidget(self.docs_btn)
        extra_layout.addStretch()
        extra_card.add_layout(extra_layout)
        self.add_widget(extra_card)

        self._sync_program_settings()

        # Advanced settings initial state
        self._load_advanced_settings()

    def _on_install_certificate_clicked(self) -> None:
        try:
            from startup.certificate_installer import is_certificate_installed
        except Exception as e:
            InfoBar.error(title="Сертификат", content=f"Не удалось загрузить установщик сертификата: {e}", parent=self.window())
            return

        thumbprint = "F507DDA6CB772F4332ECC2C5686623F39D9DA450"
        if is_certificate_installed(thumbprint):
            InfoBar.info(title="Сертификат", content="Сертификат уже установлен.", parent=self.window())
            return

        box = MessageBox(
            "Установка сертификата",
            "Установить корневой сертификат Zapret Developer?\n\n"
            "Это необязательно. После установки Windows будет доверять сертификатам, "
            "выпущенным этим центром сертификации, для текущего пользователя.\n\n"
            "Продолжить?",
            self.window(),
        )
        if not box.exec():
            return

        if self._cert_install_thread is not None:
            return

        old_text = self.install_cert_btn.text()
        self.install_cert_btn.setEnabled(False)
        self.install_cert_btn.setText("Установка...")
        self._set_status("Установка сертификата...")

        self._cert_install_thread = QThread()
        self._cert_install_worker = _CertificateInstallWorker()
        self._cert_install_worker.moveToThread(self._cert_install_thread)
        self._cert_install_thread.started.connect(self._cert_install_worker.run)

        def _finish(success: bool, message: str) -> None:
            try:
                self.install_cert_btn.setEnabled(True)
                self.install_cert_btn.setText(old_text)

                if success:
                    self._set_status("Сертификат установлен")
                    InfoBar.success(title="Сертификат", content=message or "Сертификат установлен", parent=self.window())
                else:
                    self._set_status("Не удалось установить сертификат")
                    InfoBar.error(title="Сертификат", content=message or "Не удалось установить сертификат", parent=self.window())
            finally:
                thr = self._cert_install_thread
                worker = self._cert_install_worker

                try:
                    if thr is not None:
                        thr.quit()
                        thr.wait(3000)
                except Exception:
                    pass
                try:
                    if worker is not None:
                        worker.deleteLater()
                except Exception:
                    pass
                try:
                    if thr is not None:
                        thr.deleteLater()
                except Exception:
                    pass
                self._cert_install_thread = None
                self._cert_install_worker = None

        self._cert_install_worker.finished.connect(_finish)
        self._cert_install_thread.start()

    def _load_advanced_settings(self) -> None:
        """Sync advanced toggles from registry."""
        try:
            from strategy_menu import get_wssize_enabled, get_debug_log_enabled

            try:
                from discord.discord_restart import get_discord_restart_setting

                toggle = getattr(self, "discord_restart_toggle", None)
                set_checked = getattr(toggle, "setChecked", None)
                if callable(set_checked):
                    set_checked(get_discord_restart_setting(default=True), block_signals=True)
            except Exception:
                pass

            wssize_toggle = getattr(self, "wssize_toggle", None)
            set_checked = getattr(wssize_toggle, "setChecked", None)
            if callable(set_checked):
                set_checked(bool(get_wssize_enabled()), block_signals=True)

            debug_toggle = getattr(self, "debug_log_toggle", None)
            set_checked = getattr(debug_toggle, "setChecked", None)
            if callable(set_checked):
                set_checked(bool(get_debug_log_enabled()), block_signals=True)
        except Exception:
            pass

    def _on_discord_restart_changed(self, enabled: bool) -> None:
        try:
            from discord.discord_restart import set_discord_restart_setting

            set_discord_restart_setting(bool(enabled))
        except Exception:
            pass

    def _on_wssize_toggled(self, enabled: bool) -> None:
        try:
            from strategy_menu import set_wssize_enabled

            set_wssize_enabled(bool(enabled))
        except Exception:
            pass

    def _on_debug_log_toggled(self, enabled: bool) -> None:
        try:
            from strategy_menu import set_debug_log_enabled

            set_debug_log_enabled(bool(enabled))
        except Exception:
            pass

        # direct_zapret2: keep preset-zapret2.txt in sync with runtime --debug setting
        try:
            from preset_zapret2 import PresetManager, ensure_default_preset_exists

            if not ensure_default_preset_exists():
                return
            manager = PresetManager()
            preset = manager.get_active_preset()
            if preset:
                manager.sync_preset_to_active_file(preset)
        except Exception:
            pass

    # ==================== Direct mode UI: Basic/Advanced ====================

    def _get_direct_launch_mode_setting(self) -> str:
        try:
            from strategy_menu import get_direct_zapret2_ui_mode

            mode = (get_direct_zapret2_ui_mode() or "").strip().lower()
            if mode in ("basic", "advanced"):
                return mode
        except Exception:
            pass
        return "advanced"

    def _sync_direct_launch_mode_from_settings(self) -> None:
        self._refresh_direct_mode_label()

    def _open_direct_mode_dialog(self) -> None:
        try:
            from strategy_menu import get_direct_zapret2_ui_mode
        except ImportError:
            return
        current = get_direct_zapret2_ui_mode()
        dlg = DirectLaunchModeDialog(current, self.window())
        if dlg.exec():
            new_mode = dlg.get_mode()
            if new_mode != current:
                self._on_direct_launch_mode_selected(new_mode)
                self.direct_mode_changed.emit(new_mode)

    def _refresh_direct_mode_label(self) -> None:
        try:
            from strategy_menu import get_direct_zapret2_ui_mode
            mode = get_direct_zapret2_ui_mode()
            self.direct_mode_label.setText("Basic" if mode == "basic" else "Advanced")
        except Exception:
            pass

    def _on_direct_launch_mode_selected(self, mode: str) -> None:
        wanted = str(mode or "").strip().lower()
        if wanted not in ("basic", "advanced"):
            return

        current = self._get_direct_launch_mode_setting()
        if wanted == current:
            self._sync_direct_launch_mode_from_settings()
            return

        try:
            from strategy_menu import set_direct_zapret2_ui_mode

            set_direct_zapret2_ui_mode(wanted)
        except Exception:
            pass

        # Reload strategy catalogs for the selected set.
        try:
            from strategy_menu.strategies_registry import registry

            registry.reload_strategies()
        except Exception:
            pass

        # Rebuild preset-zapret2.txt from the currently selected strategy IDs
        # using the newly selected strategies catalog (basic vs default).
        try:
            from dpi.zapret2_core_restart import trigger_dpi_reload
            from preset_zapret2 import PresetManager, ensure_default_preset_exists

            if ensure_default_preset_exists():
                pm = PresetManager(
                    on_dpi_reload_needed=lambda: trigger_dpi_reload(
                        self.parent_app,
                        reason="direct_launch_mode_changed",
                    )
                )
                preset = pm.get_active_preset()
                if preset:
                    try:
                        selections = pm.get_strategy_selections() or {}
                        pm.set_strategy_selections(selections, save_and_sync=False)
                    except Exception:
                        pass

                    try:
                        pm.save_preset(preset)
                    except Exception:
                        pass

                    pm.sync_preset_to_active_file(preset)
        except Exception:
            pass

        # Refresh labels that depend on active strategy args.
        try:
            self.update_strategy("")
        except Exception:
            pass

        self._sync_direct_launch_mode_from_settings()

    def _set_toggle_checked(self, toggle, checked: bool) -> None:
        try:
            toggle.blockSignals(True)
        except Exception:
            pass

        try:
            if hasattr(toggle, "setChecked"):
                toggle.setChecked(bool(checked))
        except Exception:
            pass

        try:
            toggle._circle_position = (toggle.width() - 18) if checked else 4.0  # type: ignore[attr-defined]
            toggle.update()
        except Exception:
            pass

        try:
            toggle.blockSignals(False)
        except Exception:
            pass

    def _sync_program_settings(self) -> None:
        try:
            from config import get_dpi_autostart

            self._set_toggle_checked(self.auto_dpi_toggle, bool(get_dpi_autostart()))
        except Exception:
            pass

        try:
            from altmenu.defender_manager import WindowsDefenderManager

            self._set_toggle_checked(self.defender_toggle, bool(WindowsDefenderManager().is_defender_disabled()))
        except Exception:
            pass

        try:
            from altmenu.max_blocker import is_max_blocked

            self._set_toggle_checked(self.max_block_toggle, bool(is_max_blocked()))
        except Exception:
            pass

    def _set_status(self, msg: str) -> None:
        try:
            if self.parent_app and hasattr(self.parent_app, "set_status"):
                self.parent_app.set_status(msg)
        except Exception:
            pass

    def _on_auto_dpi_toggled(self, enabled: bool) -> None:
        try:
            from config import set_dpi_autostart

            set_dpi_autostart(bool(enabled))
            msg = (
                "DPI будет включаться автоматически при старте программы"
                if enabled
                else "Автозагрузка DPI отключена"
            )
            self._set_status(msg)
            InfoBar.success(title="Автозагрузка DPI", content=msg, parent=self.window())
        finally:
            self._sync_program_settings()

    def _on_defender_toggled(self, disable: bool) -> None:
        import ctypes

        if not ctypes.windll.shell32.IsUserAnAdmin():
            InfoBar.error(title="Требуются права администратора", content="Для управления Windows Defender требуются права администратора. Перезапустите программу от имени администратора.", parent=self.window())
            self._set_toggle_checked(self.defender_toggle, not disable)
            return

        try:
            from altmenu.defender_manager import WindowsDefenderManager, set_defender_disabled

            manager = WindowsDefenderManager(status_callback=self._set_status)

            if disable:
                box = MessageBox(
                    "Отключение Windows Defender",
                    "Вы действительно хотите отключить Windows Defender?\n\n"
                    "Отключение Windows Defender:\n"
                    "• Отключит защиту в реальном времени\n"
                    "• Отключит облачную защиту\n"
                    "• Отключит автоматическую отправку образцов\n"
                    "• Может потребовать перезагрузки для полного применения",
                    self.window(),
                )
                if not box.exec():
                    self._set_toggle_checked(self.defender_toggle, False)
                    return

                self._set_status("Отключение Windows Defender...")
                success, count = manager.disable_defender()

                if success:
                    set_defender_disabled(True)
                    InfoBar.success(title="Windows Defender отключен", content=f"Windows Defender успешно отключен. Применено {count} настроек. Может потребоваться перезагрузка.", parent=self.window())
                else:
                    InfoBar.error(title="Ошибка", content="Не удалось отключить Windows Defender. Возможно, некоторые настройки заблокированы системой.", parent=self.window())
                    self._set_toggle_checked(self.defender_toggle, False)
            else:
                box = MessageBox(
                    "Включение Windows Defender",
                    "Включить Windows Defender обратно?\n\n"
                    "Это восстановит защиту вашего компьютера.",
                    self.window(),
                )
                if not box.exec():
                    self._set_toggle_checked(self.defender_toggle, True)
                    return

                self._set_status("Включение Windows Defender...")
                success, count = manager.enable_defender()

                if success:
                    set_defender_disabled(False)
                    InfoBar.success(title="Windows Defender включен", content="Windows Defender успешно включен. Защита вашего компьютера восстановлена.", parent=self.window())
                else:
                    InfoBar.warning(title="Частичный успех", content="Windows Defender включен частично. Некоторые настройки могут потребовать ручного исправления.", parent=self.window())

            self._set_status("Готово")

        except Exception as e:
            InfoBar.error(title="Ошибка", content=f"Произошла ошибка при изменении настроек Windows Defender: {e}", parent=self.window())
        finally:
            self._sync_program_settings()

    def _on_max_blocker_toggled(self, enable: bool) -> None:
        try:
            from altmenu.max_blocker import MaxBlockerManager

            manager = MaxBlockerManager(status_callback=self._set_status)

            if enable:
                box = MessageBox(
                    "Блокировка MAX",
                    "Включить блокировку установки и работы программы MAX?\n\n"
                    "• Заблокирует запуск max.exe, max.msi и других файлов MAX\n"
                    "• Добавит правила блокировки в Windows Firewall\n"
                    "• Заблокирует домены MAX в файле hosts",
                    self.window(),
                )
                if not box.exec():
                    self._set_toggle_checked(self.max_block_toggle, False)
                    return

                success, message = manager.enable_blocking()
                if success:
                    InfoBar.success(title="Блокировка включена", content=message, parent=self.window())
                else:
                    InfoBar.warning(title="Ошибка", content=f"Не удалось полностью включить блокировку: {message}", parent=self.window())
                    self._set_toggle_checked(self.max_block_toggle, False)
            else:
                box = MessageBox(
                    "Отключение блокировки MAX",
                    "Отключить блокировку программы MAX?\n\n"
                    "Это удалит все созданные блокировки и правила.",
                    self.window(),
                )
                if not box.exec():
                    self._set_toggle_checked(self.max_block_toggle, True)
                    return

                success, message = manager.disable_blocking()
                if success:
                    InfoBar.success(title="Блокировка отключена", content=message, parent=self.window())
                else:
                    InfoBar.warning(title="Ошибка", content=f"Не удалось полностью отключить блокировку: {message}", parent=self.window())

            self._set_status("Готово")

        except Exception as e:
            InfoBar.error(title="Ошибка", content=f"Ошибка при переключении блокировки MAX: {e}", parent=self.window())
        finally:
            self._sync_program_settings()

    def _on_reset_program_clicked(self) -> None:
        from startup.check_cache import startup_cache
        from log import log

        try:
            startup_cache.invalidate_cache()
            log("Кэш проверок запуска очищен пользователем", "INFO")
            self._set_status("Кэш проверок запуска очищен")
        except Exception as e:
            InfoBar.warning(title="Ошибка", content=f"Не удалось очистить кэш: {e}", parent=self.window())
            log(f"Ошибка очистки кэша: {e}", "❌ ERROR")
        finally:
            self._sync_program_settings()

    def _update_stop_winws_button_text(self):
        try:
            from strategy_menu import get_strategy_launch_method
            from config import get_winws_exe_for_method

            method = get_strategy_launch_method()
            exe_name = os.path.basename(get_winws_exe_for_method(method)) or "winws.exe"
            self.stop_winws_btn.setText(f"Остановить только {exe_name}")
        except Exception:
            self.stop_winws_btn.setText("Остановить только winws.exe")

    def set_loading(self, loading: bool, text: str = ""):
        if _HAS_FLUENT_LABELS:
            if loading:
                self.progress_bar.start()
            else:
                self.progress_bar.stop()
        self.progress_bar.setVisible(loading)
        self.loading_label.setVisible(loading and bool(text))
        self.loading_label.setText(text)

        self.start_btn.setEnabled(not loading)
        self.stop_winws_btn.setEnabled(not loading)
        self.stop_and_exit_btn.setEnabled(not loading)

    def update_status(self, is_running: bool):
        if is_running:
            self.status_title.setText("Zapret работает")
            self.status_desc.setText("Обход блокировок активен")
            self.status_dot.set_color("#6ccb5f")
            self.status_dot.start_pulse()
            self.start_btn.setVisible(False)
            self._update_stop_winws_button_text()
            self.stop_winws_btn.setVisible(True)
            self.stop_and_exit_btn.setVisible(True)
        else:
            self.status_title.setText("Zapret остановлен")
            self.status_desc.setText("Нажмите «Запустить» для активации")
            self.status_dot.set_color("#ff6b6b")
            self.status_dot.stop_pulse()
            self.start_btn.setVisible(True)
            self.stop_winws_btn.setVisible(False)
            self.stop_and_exit_btn.setVisible(False)

    def update_strategy(self, name: str):
        self._update_stop_winws_button_text()

        show_filter_lists = False
        active_preset_name = ""

        try:
            from preset_zapret2 import PresetManager

            preset_manager = PresetManager()
            active_preset_name = (preset_manager.get_active_preset_name() or "").strip()
            if not active_preset_name:
                preset = preset_manager.get_active_preset()
                active_preset_name = (getattr(preset, "name", "") or "").strip()
        except Exception:
            active_preset_name = ""

        try:
            from strategy_menu import get_strategy_launch_method

            method = get_strategy_launch_method()
            if method in ("direct_zapret2", "direct_zapret2_orchestra", "direct_zapret1"):
                show_filter_lists = True
                from strategy_menu import get_direct_strategy_selections
                from strategy_menu.strategies_registry import registry

                selections = get_direct_strategy_selections() or {}
                active_lists: list[str] = []
                seen_lists: set[str] = set()

                for cat_key in registry.get_all_category_keys_by_command_order():
                    sid = selections.get(cat_key, "none") or "none"
                    if sid == "none":
                        continue

                    args = registry.get_strategy_args_safe(cat_key, sid) or ""
                    for value in _HOSTLIST_DISPLAY_RE.findall(args):
                        list_path = value.strip().strip('"').strip("'")
                        if not list_path:
                            continue

                        normalized = list_path.replace("\\", "/")
                        list_name = normalized.rsplit("/", 1)[-1]
                        if not list_name:
                            continue

                        dedupe_key = list_name.lower()
                        if dedupe_key in seen_lists:
                            continue
                        seen_lists.add(dedupe_key)
                        active_lists.append(list_name)

                if not active_lists:
                    name = "Не выбрана"
                    set_tooltip(self.strategy_label, "")
                else:
                    name = " • ".join(active_lists)
                    set_tooltip(self.strategy_label, "\n".join(active_lists))
        except Exception:
            pass

        if active_preset_name:
            self.preset_name_label.setText(active_preset_name)
            set_tooltip(self.preset_name_label, active_preset_name)
        else:
            self.preset_name_label.setText("Не выбран")
            set_tooltip(self.preset_name_label, "")

        if name and name != "Автостарт DPI отключен":
            self.strategy_label.setText(name)
        else:
            self.strategy_label.setText("Нет активных листов")

    def _open_docs(self) -> None:
        try:
            from config.urls import DOCS_URL

            webbrowser.open(DOCS_URL)
        except Exception as e:
            InfoBar.warning(title="Документация", content=f"Не удалось открыть документацию: {e}", parent=self.window())
