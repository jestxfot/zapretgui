# ui/pages/zapret2/direct_control_page.py
"""Direct Zapret2 management page (Strategies landing for direct_zapret2)."""

import os
import re
import webbrowser

from PyQt6.QtCore import QSize, Qt, QObject, pyqtSignal, QThread
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QProgressBar,
    QSizePolicy,
    QMessageBox,
)
import qtawesome as qta

from ui.pages.base_page import BasePage
from ui.pages.strategies_page_base import ResetActionButton
from ui.sidebar import ActionButton, PulsingDot, SettingsCard, SettingsRow


# Стиль для индикатора загрузки (бегающая полоска)
PROGRESS_STYLE = """
QProgressBar {
    background-color: rgba(255, 255, 255, 0.05);
    border: none;
    border-radius: 2px;
    height: 4px;
    text-align: center;
}
QProgressBar::chunk {
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:0,
        stop:0 transparent,
        stop:0.3 #60cdff,
        stop:0.5 #60cdff,
        stop:0.7 #60cdff,
        stop:1 transparent
    );
    border-radius: 2px;
}
"""


_LIST_FILE_ARG_RE = re.compile(r"--(?:hostlist|ipset|hostlist-exclude|ipset-exclude)=([^\s]+)")


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


class BigActionButton(ActionButton):
    """Большая кнопка действия"""

    def __init__(self, text: str, icon_name: str | None = None, accent: bool = False, parent=None):
        super().__init__(text, icon_name, accent, parent)
        self.setFixedHeight(48)
        self.setIconSize(QSize(20, 20))

    def _update_style(self):
        if self.accent:
            bg = "rgba(96, 205, 255, 0.9)" if self._hovered else "#60cdff"
            text_color = "#000000"
        else:
            bg = "rgba(255, 255, 255, 0.15)" if self._hovered else "rgba(255, 255, 255, 0.08)"
            text_color = "#ffffff"

        self.setStyleSheet(
            f"""
            QPushButton {{
                background: {bg};
                border: none;
                border-radius: 6px;
                color: {text_color};
                padding: 0 24px;
                font-size: 14px;
                font-weight: 600;
                font-family: 'Segoe UI Variable', 'Segoe UI', sans-serif;
            }}
            """
        )


class StopButton(BigActionButton):
    """Кнопка остановки (нейтральная)"""

    def _update_style(self):
        bg = "rgba(255, 255, 255, 0.15)" if self._hovered else "rgba(255, 255, 255, 0.08)"
        self.setStyleSheet(
            f"""
            QPushButton {{
                background: {bg};
                border: none;
                border-radius: 6px;
                color: #ffffff;
                padding: 0 24px;
                font-size: 14px;
                font-weight: 600;
                font-family: 'Segoe UI Variable', 'Segoe UI', sans-serif;
            }}
            """
        )


class Zapret2DirectControlPage(BasePage):
    """Страница управления для direct_zapret2 (главная вкладка раздела "Стратегии")."""

    def __init__(self, parent=None):
        super().__init__(
            "Управление",
            "Настройка и запуск Zapret 2. Выберите готовые пресеты-конфиги (как раньше .bat), "
            "а при необходимости выполните тонкую настройку для каждой категории в разделе «Прямой запуск».",
            parent,
        )

        self._cert_install_thread: QThread | None = None
        self._cert_install_worker: _CertificateInstallWorker | None = None
        self._direct_launch_mode = "advanced"

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
            self._sync_direct_launch_mode_from_settings()
        except Exception:
            pass

    def _build_ui(self):
        # Быстрый доступ к документации
        docs_widget = QWidget()
        docs_row = QHBoxLayout(docs_widget)
        docs_row.setContentsMargins(0, 0, 0, 0)
        docs_row.setSpacing(0)
        docs_row.addStretch(1)

        self.docs_btn = ActionButton("Документация", "fa5s.book")
        self.docs_btn.setProperty("noDrag", True)
        self.docs_btn.setFixedHeight(36)
        self.docs_btn.clicked.connect(self._open_docs)
        docs_row.addWidget(self.docs_btn)

        self.add_widget(docs_widget)

        # Статус работы
        self.add_section_title("Статус работы")

        status_card = SettingsCard()
        status_layout = QHBoxLayout()
        status_layout.setSpacing(16)

        self.status_dot = PulsingDot()
        status_layout.addWidget(self.status_dot)

        status_text_widget = QWidget()
        status_text_widget.setStyleSheet("background: transparent;")
        status_text = QVBoxLayout(status_text_widget)
        status_text.setContentsMargins(0, 0, 0, 0)
        status_text.setSpacing(2)

        self.status_title = QLabel("Проверка...")
        self.status_title.setStyleSheet(
            """
            QLabel {
                color: #ffffff;
                font-size: 15px;
                font-weight: 600;
            }
            """
        )
        status_text.addWidget(self.status_title)

        self.status_desc = QLabel("Определение состояния процесса")
        self.status_desc.setStyleSheet(
            """
            QLabel {
                color: rgba(255, 255, 255, 0.6);
                font-size: 12px;
            }
            """
        )
        status_text.addWidget(self.status_desc)

        status_layout.addWidget(status_text_widget, 1)
        status_card.add_layout(status_layout)
        self.add_widget(status_card)

        self.add_spacing(16)

        # Управление
        self.add_section_title("Управление Zapret 2")

        control_card = SettingsCard()

        # Индикатор загрузки (бегающая полоска) - показываем рядом с кнопками управления
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet(PROGRESS_STYLE)
        self.progress_bar.setFixedHeight(4)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(0)
        self.progress_bar.setVisible(False)
        control_card.add_widget(self.progress_bar)

        self.loading_label = QLabel("")
        self.loading_label.setStyleSheet(
            """
            QLabel {
                color: rgba(255, 255, 255, 0.6);
                font-size: 12px;
                padding-top: 4px;
            }
            """
        )
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

        self.add_section_title("Активный пресет (стандартный набор стратегий из готового списка)")

        active_preset_card = SettingsCard()
        active_preset_layout = QHBoxLayout()
        active_preset_layout.setSpacing(12)

        self.active_preset_icon = QLabel()
        try:
            from ui.fluent_icons import fluent_pixmap

            self.active_preset_icon.setPixmap(fluent_pixmap("fa5s.star", 20))
        except Exception:
            self.active_preset_icon.setPixmap(qta.icon("fa5s.star", color="#60cdff").pixmap(20, 20))
        self.active_preset_icon.setFixedSize(24, 24)
        active_preset_layout.addWidget(self.active_preset_icon)

        active_preset_text_widget = QWidget()
        active_preset_text_widget.setStyleSheet("background: transparent;")
        active_preset_text_layout = QVBoxLayout(active_preset_text_widget)
        active_preset_text_layout.setContentsMargins(0, 0, 0, 0)
        active_preset_text_layout.setSpacing(2)

        self.active_preset_label = QLabel("Не выбран")
        self.active_preset_label.setStyleSheet(
            """
            QLabel {
                color: #ffffff;
                font-size: 14px;
                font-weight: 500;
            }
            """
        )
        self.active_preset_label.setWordWrap(True)
        self.active_preset_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        active_preset_text_layout.addWidget(self.active_preset_label)

        self.active_preset_desc = QLabel("Выберите пресет в разделе «Активный пресет»")
        self.active_preset_desc.setStyleSheet(
            """
            QLabel {
                color: rgba(255, 255, 255, 0.5);
                font-size: 11px;
            }
            """
        )
        active_preset_text_layout.addWidget(self.active_preset_desc)

        active_preset_layout.addWidget(active_preset_text_widget, 1)
        active_preset_card.add_layout(active_preset_layout)
        self.add_widget(active_preset_card)

        self.add_spacing(16)

        self.add_section_title("Хотите свою стратегию для каждого сайта? Перейдите во вкладку «Прямой запуск» чтобы изменить шаблонный пресет")

        strategy_card = SettingsCard()

        # Текст про выбор режима прямого запуска (в одном виджете с активными списками)
        mode_row = SettingsRow(
            "fa5s.sliders-h",
            "Режим прямого запуска",
            "Basic — без UI; send/syndata можно прописать в args стратегии. Advanced — Send/Syndata/фазы в UI",
        )

        mode_control = QWidget()
        mode_ctl_layout = QHBoxLayout(mode_control)
        mode_ctl_layout.setContentsMargins(0, 0, 0, 0)
        mode_ctl_layout.setSpacing(0)

        self._direct_launch_mode_basic_btn = QPushButton("Basic")
        self._direct_launch_mode_advanced_btn = QPushButton("Advanced")
        for btn in (self._direct_launch_mode_basic_btn, self._direct_launch_mode_advanced_btn):
            btn.setFixedHeight(28)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setCheckable(True)

        self._direct_launch_mode_basic_btn.clicked.connect(lambda: self._on_direct_launch_mode_selected("basic"))
        self._direct_launch_mode_advanced_btn.clicked.connect(lambda: self._on_direct_launch_mode_selected("advanced"))

        mode_ctl_layout.addWidget(self._direct_launch_mode_basic_btn)
        mode_ctl_layout.addWidget(self._direct_launch_mode_advanced_btn)

        mode_row.set_control(mode_control)
        strategy_card.add_widget(mode_row)

        try:
            self._sync_direct_launch_mode_from_settings()
        except Exception:
            pass

        strategy_layout = QHBoxLayout()
        strategy_layout.setSpacing(12)

        self.strategy_icon = QLabel()
        try:
            from ui.fluent_icons import fluent_pixmap

            self.strategy_icon.setPixmap(fluent_pixmap("fa5s.cog", 20))
        except Exception:
            self.strategy_icon.setPixmap(qta.icon("fa5s.cog", color="#60cdff").pixmap(20, 20))
        self.strategy_icon.setFixedSize(24, 24)
        strategy_layout.addWidget(self.strategy_icon)

        strategy_text_widget = QWidget()
        strategy_text_widget.setStyleSheet("background: transparent;")
        strategy_text_layout = QVBoxLayout(strategy_text_widget)
        strategy_text_layout.setContentsMargins(0, 0, 0, 0)
        strategy_text_layout.setSpacing(2)

        self.strategy_label = QLabel("Не выбрана")
        self.strategy_label.setStyleSheet(
            """
            QLabel {
                color: #ffffff;
                font-size: 14px;
                font-weight: 500;
            }
            """
        )
        self.strategy_label.setWordWrap(True)
        self.strategy_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        strategy_text_layout.addWidget(self.strategy_label)

        self.strategy_desc = QLabel("Выберите стратегию в разделе «Прямой запуск»")
        self.strategy_desc.setStyleSheet(
            """
            QLabel {
                color: rgba(255, 255, 255, 0.5);
                font-size: 11px;
            }
            """
        )
        strategy_text_layout.addWidget(self.strategy_desc)

        strategy_layout.addWidget(strategy_text_widget, 1)
        strategy_card.add_layout(strategy_layout)
        self.add_widget(strategy_card)

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

        advanced_desc = QLabel("⚠ Изменяйте только если знаете что делаете")
        advanced_desc.setStyleSheet("color: #ff9800; font-size: 11px; padding-bottom: 8px;")
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

        # Дополнительные действия
        self.add_section_title("Дополнительно")
        extra_card = SettingsCard()
        extra_layout = QHBoxLayout()
        extra_layout.setSpacing(8)
        self.test_btn = ActionButton("Тест соединения", "fa5s.wifi")
        extra_layout.addWidget(self.test_btn)
        self.folder_btn = ActionButton("Открыть папку", "fa5s.folder-open")
        extra_layout.addWidget(self.folder_btn)
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
            QMessageBox.critical(self, "Сертификат", f"Не удалось загрузить установщик сертификата:\n\n{e}")
            return

        thumbprint = "F507DDA6CB772F4332ECC2C5686623F39D9DA450"
        if is_certificate_installed(thumbprint):
            QMessageBox.information(self, "Сертификат", "Сертификат уже установлен.")
            return

        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Установка сертификата")
        msg_box.setIcon(QMessageBox.Icon.Warning)
        msg_box.setText("Установить корневой сертификат Zapret Developer?")
        msg_box.setInformativeText(
            "Это необязательно. После установки Windows будет доверять сертификатам, "
            "выпущенным этим центром сертификации, для текущего пользователя.\n\n"
            "Продолжить?"
        )
        msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg_box.setDefaultButton(QMessageBox.StandardButton.No)
        if msg_box.exec() != QMessageBox.StandardButton.Yes:
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
                    QMessageBox.information(self, "Сертификат", message or "Сертификат установлен")
                else:
                    self._set_status("Не удалось установить сертификат")
                    QMessageBox.critical(self, "Сертификат", message or "Не удалось установить сертификат")
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
        self._direct_launch_mode = self._get_direct_launch_mode_setting()
        self._update_direct_launch_mode_styles()

    def _update_direct_launch_mode_styles(self) -> None:
        if not hasattr(self, "_direct_launch_mode_basic_btn") or not hasattr(self, "_direct_launch_mode_advanced_btn"):
            return

        active_style = """
            QPushButton {
                background: #60cdff;
                border: none;
                color: #000000;
                font-size: 11px;
                font-weight: 600;
                padding: 0 12px;
            }
        """
        inactive_style = """
            QPushButton {
                background: rgba(255, 255, 255, 0.08);
                border: none;
                color: rgba(255, 255, 255, 0.7);
                font-size: 11px;
                padding: 0 12px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.12);
            }
        """

        left_radius = "border-top-left-radius: 6px; border-bottom-left-radius: 6px;"
        right_radius = "border-top-right-radius: 6px; border-bottom-right-radius: 6px;"

        mode = (getattr(self, "_direct_launch_mode", "advanced") or "advanced").strip().lower()
        if mode == "basic":
            self._direct_launch_mode_basic_btn.setStyleSheet(active_style.replace("}", left_radius + "}"))
            self._direct_launch_mode_basic_btn.setChecked(True)
            self._direct_launch_mode_advanced_btn.setStyleSheet(
                inactive_style.replace("QPushButton {", "QPushButton { " + right_radius)
            )
            self._direct_launch_mode_advanced_btn.setChecked(False)
        else:
            self._direct_launch_mode_basic_btn.setStyleSheet(
                inactive_style.replace("QPushButton {", "QPushButton { " + left_radius)
            )
            self._direct_launch_mode_basic_btn.setChecked(False)
            self._direct_launch_mode_advanced_btn.setStyleSheet(active_style.replace("}", right_radius + "}"))
            self._direct_launch_mode_advanced_btn.setChecked(True)

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
            QMessageBox.information(self, "Автозагрузка DPI", msg)
        finally:
            self._sync_program_settings()

    def _on_defender_toggled(self, disable: bool) -> None:
        import ctypes

        if not ctypes.windll.shell32.IsUserAnAdmin():
            QMessageBox.critical(
                self,
                "Требуются права администратора",
                "Для управления Windows Defender требуются права администратора.\n\n"
                "Перезапустите программу от имени администратора.",
            )
            self._set_toggle_checked(self.defender_toggle, not disable)
            return

        try:
            from altmenu.defender_manager import WindowsDefenderManager, set_defender_disabled

            manager = WindowsDefenderManager(status_callback=self._set_status)

            if disable:
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle("Отключение Windows Defender")
                msg_box.setIcon(QMessageBox.Icon.Warning)
                msg_box.setText("Вы действительно хотите отключить Windows Defender?\n\n")
                msg_box.setInformativeText(
                    "Отключение Windows Defender:\n"
                    "• Отключит защиту в реальном времени\n"
                    "• Отключит облачную защиту\n"
                    "• Отключит автоматическую отправку образцов\n"
                    "• Может потребовать перезагрузки для полного применения\n\n"
                )
                msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                msg_box.setDefaultButton(QMessageBox.StandardButton.No)

                if msg_box.exec() != QMessageBox.StandardButton.Yes:
                    self._set_toggle_checked(self.defender_toggle, False)
                    return

                self._set_status("Отключение Windows Defender...")
                success, count = manager.disable_defender()

                if success:
                    set_defender_disabled(True)
                    QMessageBox.information(
                        self,
                        "Windows Defender отключен",
                        "Windows Defender успешно отключен.\n"
                        f"Применено {count} настроек.\n\n"
                        "Для полного применения изменений может потребоваться перезагрузка.",
                    )
                else:
                    QMessageBox.critical(
                        self,
                        "Ошибка",
                        "Не удалось отключить Windows Defender.\n"
                        "Возможно, некоторые настройки заблокированы системой.",
                    )
                    self._set_toggle_checked(self.defender_toggle, False)
            else:
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle("Включение Windows Defender")
                msg_box.setIcon(QMessageBox.Icon.Question)
                msg_box.setText(
                    "Включить Windows Defender обратно?\n\n"
                    "Это восстановит защиту вашего компьютера."
                )
                msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                msg_box.setDefaultButton(QMessageBox.StandardButton.Yes)

                if msg_box.exec() != QMessageBox.StandardButton.Yes:
                    self._set_toggle_checked(self.defender_toggle, True)
                    return

                self._set_status("Включение Windows Defender...")
                success, count = manager.enable_defender()

                if success:
                    set_defender_disabled(False)
                    QMessageBox.information(
                        self,
                        "Windows Defender включен",
                        "Windows Defender успешно включен.\n"
                        f"Выполнено {count} операций.\n\n"
                        "Защита вашего компьютера восстановлена.",
                    )
                else:
                    QMessageBox.warning(
                        self,
                        "Частичный успех",
                        "Windows Defender включен частично.\n"
                        "Для полного восстановления может потребоваться перезагрузка.",
                    )

            self._set_status("Готово")

        except Exception as e:
            QMessageBox.critical(
                self,
                "Ошибка",
                f"Произошла ошибка при изменении настроек Windows Defender:\n{e}",
            )
        finally:
            self._sync_program_settings()

    def _on_max_blocker_toggled(self, enable: bool) -> None:
        try:
            from altmenu.max_blocker import MaxBlockerManager

            manager = MaxBlockerManager(status_callback=self._set_status)

            if enable:
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle("Блокировка MAX")
                msg_box.setIcon(QMessageBox.Icon.Information)
                msg_box.setText("Включить блокировку установки и работы программы MAX?\n\nЭто действие:")
                msg_box.setInformativeText(
                    "• Заблокирует запуск max.exe, max.msi и других файлов MAX\n"
                    "• Создаст файлы-блокировки в папках установки\n"
                    "• Добавит правила блокировки в Windows Firewall (при наличии прав)\n"
                    "• Заблокирует домены MAX в файле hosts\n\n"
                    "В итоге даже если мессенджер Max поставиться будет тёмный экран, в результате чего он будет выглядеть так, будто не может подключиться к своим серверам."
                )
                msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                msg_box.setDefaultButton(QMessageBox.StandardButton.Yes)

                if msg_box.exec() != QMessageBox.StandardButton.Yes:
                    self._set_toggle_checked(self.max_block_toggle, False)
                    return

                success, message = manager.enable_blocking()
                if success:
                    QMessageBox.information(self, "Блокировка включена", message)
                else:
                    QMessageBox.warning(self, "Ошибка", f"Не удалось полностью включить блокировку:\n{message}")
                    self._set_toggle_checked(self.max_block_toggle, False)
            else:
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle("Отключение блокировки MAX")
                msg_box.setIcon(QMessageBox.Icon.Question)
                msg_box.setText(
                    "Отключить блокировку программы MAX?\n\n"
                    "Это удалит все созданные блокировки и правила."
                )
                msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                msg_box.setDefaultButton(QMessageBox.StandardButton.No)

                if msg_box.exec() != QMessageBox.StandardButton.Yes:
                    self._set_toggle_checked(self.max_block_toggle, True)
                    return

                success, message = manager.disable_blocking()
                if success:
                    QMessageBox.information(self, "Блокировка отключена", message)
                else:
                    QMessageBox.warning(self, "Ошибка", f"Не удалось полностью отключить блокировку:\n{message}")

            self._set_status("Готово")

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка при переключении блокировки MAX:\n{e}")
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
            QMessageBox.warning(self, "Ошибка", f"Не удалось очистить кэш: {e}")
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
        self.progress_bar.setVisible(loading)
        self.loading_label.setVisible(loading and bool(text))
        self.loading_label.setText(text)

        self.start_btn.setEnabled(not loading)
        self.stop_winws_btn.setEnabled(not loading)
        self.stop_and_exit_btn.setEnabled(not loading)

        if loading:
            disabled_style = """
                QPushButton {
                    background: rgba(255, 255, 255, 0.03);
                    border: none;
                    border-radius: 6px;
                    color: rgba(255, 255, 255, 0.3);
                    padding: 0 24px;
                    font-size: 14px;
                    font-weight: 600;
                    font-family: 'Segoe UI Variable', 'Segoe UI', sans-serif;
                }
            """
            self.start_btn.setStyleSheet(disabled_style)
            self.stop_winws_btn.setStyleSheet(disabled_style)
            self.stop_and_exit_btn.setStyleSheet(disabled_style)
        else:
            self.start_btn._update_style()
            self.stop_winws_btn._update_style()
            self.stop_and_exit_btn._update_style()

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
                    for value in _LIST_FILE_ARG_RE.findall(args):
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
                    self.strategy_label.setToolTip("")
                else:
                    name = " • ".join(active_lists)
                    self.strategy_label.setToolTip("\n".join(active_lists))
        except Exception:
            pass

        if active_preset_name:
            self.active_preset_label.setText(active_preset_name)
            self.active_preset_label.setToolTip(active_preset_name)
            self.active_preset_desc.setText("Текущий активный пресет")
        else:
            self.active_preset_label.setText("Не выбран")
            self.active_preset_label.setToolTip("")
            self.active_preset_desc.setText("Выберите пресет в разделе «Активный пресет»")

        if name and name != "Автостарт DPI отключен":
            self.strategy_label.setText(name)
            self.strategy_desc.setText("Активные hostlist/ipset" if show_filter_lists else "Активная стратегия обхода")
        else:
            self.strategy_label.setText("Не выбрана")
            self.strategy_desc.setText("Выберите стратегию в разделе «Прямой запуск»")

    def _open_docs(self) -> None:
        try:
            from config.urls import DOCS_URL

            webbrowser.open(DOCS_URL)
        except Exception as e:
            QMessageBox.warning(self.window(), "Документация", f"Не удалось открыть документацию:\n{e}")
