# ui/pages/premium_page.py
"""Страница управления Premium подпиской"""

from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtWidgets import QWidget, QFrame, QLabel, QVBoxLayout, QHBoxLayout, QApplication, QSizePolicy

try:
    from qfluentwidgets import (
        LineEdit, MessageBox, InfoBar,
        BodyLabel, CaptionLabel, StrongBodyLabel, SubtitleLabel,
    )
    _HAS_FLUENT = True
except ImportError:
    from PyQt6.QtWidgets import (   # type: ignore[assignment]
        QLineEdit as LineEdit, QLabel as BodyLabel, QLabel as CaptionLabel,
        QLabel as StrongBodyLabel, QLabel as SubtitleLabel,
    )
    MessageBox = None
    InfoBar = None
    _HAS_FLUENT = False

import webbrowser

from .base_page import BasePage
from ui.compat_widgets import SettingsCard, ActionButton, RefreshButton
from ui.theme_semantic import get_semantic_palette


# ─────────────────────────────────────────────────────────────────────────────
# Worker thread
# ─────────────────────────────────────────────────────────────────────────────

class WorkerThread(QThread):
    """Поток для выполнения фоновых операций"""
    result_ready = pyqtSignal(object)
    error_occurred = pyqtSignal(str)

    def __init__(self, target, args=None):
        super().__init__()
        self.target = target
        self.args = args or ()

    def run(self):
        try:
            result = self.target(*self.args)
            self.result_ready.emit(result)
        except Exception as e:
            self.error_occurred.emit(str(e))


# ─────────────────────────────────────────────────────────────────────────────
# StatusCard — full-width subscription status display
# ─────────────────────────────────────────────────────────────────────────────

class StatusCard(QFrame):
    """Full-width subscription status card (no InfoBar dependency)."""

    _STATUS_CONFIG = {
        'active':  {'bg': '#1c2e24', 'fg': '#7ecb9a', 'icon': '✓'},
        'warning': {'bg': '#2a2516', 'fg': '#c8a96e', 'icon': '⚠'},
        'expired': {'bg': '#2a1e1e', 'fg': '#c98080', 'icon': '✕'},
        'neutral': {'bg': '#1a2030', 'fg': '#7aa8d4', 'icon': 'ℹ'},
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.setMinimumHeight(52)

        row = QHBoxLayout(self)
        row.setContentsMargins(14, 10, 14, 10)
        row.setSpacing(10)

        self._icon_lbl = QLabel()
        self._icon_lbl.setFixedWidth(22)
        self._icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._title_lbl = QLabel()
        self._detail_lbl = QLabel()

        row.addWidget(self._icon_lbl)
        row.addWidget(self._title_lbl)
        row.addSpacing(8)
        row.addWidget(self._detail_lbl)
        row.addStretch(1)

        self.set_status("Проверка...", "", "neutral")

    def set_status(self, text: str, details: str = "", status: str = "neutral"):
        cfg = self._STATUS_CONFIG.get(status, self._STATUS_CONFIG['neutral'])

        self._icon_lbl.setText(cfg['icon'])
        self._icon_lbl.setStyleSheet(
            f"color: {cfg['fg']}; font-size: 15px; font-weight: bold; background: transparent;"
        )

        self._title_lbl.setText(text)
        self._title_lbl.setStyleSheet(
            f"color: {cfg['fg']}; font-weight: 600; font-size: 13px; background: transparent;"
        )

        self._detail_lbl.setText(details)
        self._detail_lbl.setStyleSheet(
            "color: rgba(255,255,255,180); font-size: 13px; background: transparent;"
        )
        self._detail_lbl.setVisible(bool(details))

        self.setStyleSheet(f"""
            StatusCard {{
                background-color: {cfg['bg']};
                border: none;
                border-radius: 8px;
            }}
        """)


# ─────────────────────────────────────────────────────────────────────────────
# PremiumPage
# ─────────────────────────────────────────────────────────────────────────────

class PremiumPage(BasePage):
    """Страница управления Premium подпиской"""

    subscription_updated = pyqtSignal(bool, int)  # is_premium, days_remaining

    def __init__(self, parent=None):
        super().__init__("Premium", "Управление подпиской Zapret Premium", parent)

        self.checker = None
        self.RegistryManager = None
        self.current_thread = None

        self._build_ui()
        self._initialized = False

    # ── lifecycle ────────────────────────────────────────────────────────────

    def showEvent(self, event):
        super().showEvent(event)
        if not self._initialized:
            self._initialized = True
            self._init_checker()
            QTimer.singleShot(500, self._check_status)
            QTimer.singleShot(800, self._test_connection)

    def closeEvent(self, event):
        if self.current_thread and self.current_thread.isRunning():
            self.current_thread.quit()
            self.current_thread.wait()
        event.accept()

    # ── initialization ───────────────────────────────────────────────────────

    def _init_checker(self):
        try:
            from donater import DonateChecker, PremiumStorage
            self.checker = DonateChecker()
            self.RegistryManager = PremiumStorage
            self._update_device_info()
        except Exception as e:
            from log import log
            log(f"Ошибка инициализации PremiumPage checker: {e}", "ERROR")

    # ── UI construction ──────────────────────────────────────────────────────

    def _build_ui(self):
        # ─── Статус подписки ─────────────────────────────────────────────────
        self.add_section_title("Статус подписки")

        self.status_badge = StatusCard()
        self.add_widget(self.status_badge)

        self.days_label = SubtitleLabel("") if _HAS_FLUENT else BodyLabel("")
        self.days_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.add_widget(self.days_label)

        self.add_spacing(8)

        # ─── Привязка устройства ─────────────────────────────────────────────
        self.activation_section_title = self.add_section_title(
            "Привязка устройства", return_widget=True
        )

        self.activation_card = SettingsCard()

        self.instructions_label = BodyLabel(
            "1. Нажмите «Создать код»\n"
            "2. Отправьте код боту @zapretvpns_bot в Telegram (сообщением)\n"
            "3. Вернитесь сюда и нажмите «Проверить статус»"
        )
        self.instructions_label.setWordWrap(True)
        self.activation_card.add_widget(self.instructions_label)

        # Контейнер с кодом привязки (скрывается при активной подписке)
        self.key_input_container = QWidget()
        key_v = QVBoxLayout(self.key_input_container)
        key_v.setContentsMargins(0, 0, 0, 0)
        key_v.setSpacing(8)

        key_row = QHBoxLayout()
        key_row.setSpacing(8)

        self.key_input = LineEdit()
        self.key_input.setPlaceholderText("ABCD12EF")
        self.key_input.setReadOnly(True)
        key_row.addWidget(self.key_input, 1)

        self.activate_btn = ActionButton("Создать код", "fa5s.link", accent=True)
        self.activate_btn.clicked.connect(self._create_pair_code)
        key_row.addWidget(self.activate_btn)

        key_v.addLayout(key_row)

        self.activation_status = CaptionLabel("")
        self.activation_status.setWordWrap(True)
        key_v.addWidget(self.activation_status)

        self.activation_card.add_widget(self.key_input_container)
        self.add_widget(self.activation_card)

        self.add_spacing(8)

        # ─── Информация об устройстве ─────────────────────────────────────────
        self.add_section_title("Информация об устройстве")

        device_card = SettingsCard()

        self.device_id_label = CaptionLabel("ID устройства: загрузка...")
        self.saved_key_label = CaptionLabel("device token: —")
        self.last_check_label = CaptionLabel("Последняя проверка: —")
        self.server_status_label = CaptionLabel("Сервер: проверка...")

        labels_layout = QVBoxLayout()
        labels_layout.setSpacing(4)
        labels_layout.setContentsMargins(0, 0, 0, 0)
        labels_layout.addWidget(self.device_id_label)
        labels_layout.addWidget(self.saved_key_label)
        labels_layout.addWidget(self.last_check_label)
        labels_layout.addWidget(self.server_status_label)

        self.open_bot_btn = ActionButton("Открыть бота", "fa5b.telegram", accent=True)
        self.open_bot_btn.clicked.connect(self._open_extend_bot)

        row_layout = QHBoxLayout()
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.addLayout(labels_layout)
        row_layout.addStretch(1)
        row_layout.addWidget(self.open_bot_btn, 0, Qt.AlignmentFlag.AlignVCenter)
        device_card.add_layout(row_layout)

        self.add_widget(device_card)

        self.add_spacing(8)

        # ─── Действия ────────────────────────────────────────────────────────
        self.add_section_title("Действия")

        actions_card = SettingsCard()

        actions_row = QHBoxLayout()
        actions_row.setSpacing(8)

        self.refresh_btn = RefreshButton("Обновить статус")
        self.refresh_btn.clicked.connect(self._check_status)
        actions_row.addWidget(self.refresh_btn, 1)

        self.change_key_btn = ActionButton("Сбросить активацию", "fa5s.exchange-alt")
        self.change_key_btn.clicked.connect(self._change_key)
        actions_row.addWidget(self.change_key_btn, 1)

        self.test_btn = ActionButton("Проверить соединение", "fa5s.plug")
        self.test_btn.clicked.connect(self._test_connection)
        actions_row.addWidget(self.test_btn, 1)

        self.extend_btn = ActionButton("Продлить подписку", "fa5b.telegram", accent=True)
        self.extend_btn.clicked.connect(self._open_extend_bot)
        actions_row.addWidget(self.extend_btn, 1)

        actions_card.add_layout(actions_row)

        self.add_widget(actions_card)

    # ── helpers ──────────────────────────────────────────────────────────────

    def _set_activation_section_visible(self, visible: bool):
        if hasattr(self, "key_input_container"):
            self.key_input_container.setVisible(visible)

    def _update_device_info(self):
        if not self.checker:
            return
        try:
            self.device_id_label.setText(f"ID устройства: {self.checker.device_id[:16]}...")

            device_token = None
            try:
                device_token = self.RegistryManager.get_device_token()
            except Exception:
                pass

            pair_code = None
            try:
                pair_code = self.RegistryManager.get_pair_code()
            except Exception:
                pass

            parts = ["device token: ✅" if device_token else "device token: ❌"]
            if pair_code:
                parts.append(f"pair: {pair_code}")
            self.saved_key_label.setText(" | ".join(parts))

            last_check = self.RegistryManager.get_last_check()
            if last_check:
                self.last_check_label.setText(
                    f"Последняя проверка: {last_check.strftime('%d.%m.%Y %H:%M')}"
                )
            else:
                self.last_check_label.setText("Последняя проверка: —")
        except Exception as e:
            from log import log
            log(f"Ошибка обновления информации об устройстве: {e}", "DEBUG")

    def _open_extend_bot(self) -> None:
        try:
            from config.telegram_links import open_telegram_link
            open_telegram_link("zapretvpns_bot")
            return
        except Exception:
            try:
                webbrowser.open("https://t.me/zapretvpns_bot")
            except Exception as e:
                if InfoBar:
                    InfoBar.warning(
                        title="Ошибка",
                        content=f"Не удалось открыть Telegram: {e}",
                        parent=self.window(),
                    )

    # ── pair code ────────────────────────────────────────────────────────────

    def _create_pair_code(self):
        if not self.checker:
            self._init_checker()
            if not self.checker:
                self.activation_status.setText("❌ Ошибка инициализации")
                return

        self.activate_btn.setEnabled(False)
        self.activate_btn.setText("Создание...")
        self.activation_status.setText("🔄 Создаю код...")

        self.current_thread = WorkerThread(self.checker.pair_start)
        self.current_thread.result_ready.connect(self._on_pair_code_created)
        self.current_thread.error_occurred.connect(self._on_activation_error)
        self.current_thread.start()

    def _on_pair_code_created(self, result):
        try:
            success, message, code = result
        except Exception:
            success, message, code = False, "Неверный ответ", None

        self.activate_btn.setEnabled(True)
        self.activate_btn.setText("Создать код")

        if success:
            if code:
                self.key_input.setText(str(code))
                try:
                    QApplication.clipboard().setText(str(code))
                except Exception:
                    pass
            self.activation_status.setText(
                "✅ Код создан и скопирован. Отправьте его боту в Telegram."
            )
        else:
            self.activation_status.setText(f"❌ {message}")

    def _on_activation_error(self, error):
        self.activate_btn.setEnabled(True)
        self.activate_btn.setText("Создать код")
        self.activation_status.setText(f"❌ Ошибка: {error}")

    # ── status check ─────────────────────────────────────────────────────────

    def _check_status(self):
        if not self.checker:
            self._init_checker()
            if not self.checker:
                self.status_badge.set_status("Ошибка", "Не удалось инициализировать", "expired")
                return

        self.refresh_btn.set_loading(True)
        self.status_badge.set_status("Проверка...", "Подключение к серверу", "neutral")

        self.current_thread = WorkerThread(self.checker.check_device_activation)
        self.current_thread.result_ready.connect(self._on_status_complete)
        self.current_thread.error_occurred.connect(self._on_status_error)
        self.current_thread.start()

    def _on_status_complete(self, result):
        self.refresh_btn.set_loading(False)
        self._update_device_info()

        if result is None or not isinstance(result, dict):
            self.status_badge.set_status("Ошибка", "Неверный ответ сервера", "expired")
            return

        if 'activated' not in result:
            self.status_badge.set_status("Ошибка", "Неполный ответ", "expired")
            return

        try:
            is_premium = bool(result.get("is_premium", result.get("activated")))
            is_linked = bool(result.get("found"))
            semantic = get_semantic_palette()

            if is_premium:
                days_remaining = result.get('days_remaining')
                self._set_activation_section_visible(False)

                if days_remaining is not None:
                    if days_remaining > 30:
                        self.status_badge.set_status(
                            "Подписка активна", f"Осталось {days_remaining} дней", "active"
                        )
                        self.days_label.setText(f"Осталось дней: {days_remaining}")
                        self.days_label.setStyleSheet(f"color: {semantic.success};")
                    elif days_remaining > 7:
                        self.status_badge.set_status(
                            "Подписка активна", f"Осталось {days_remaining} дней", "warning"
                        )
                        self.days_label.setText(f"⚠️ Осталось дней: {days_remaining}")
                        self.days_label.setStyleSheet(f"color: {semantic.warning};")
                    else:
                        self.status_badge.set_status(
                            "Скоро истекает!", f"Осталось {days_remaining} дней", "warning"
                        )
                        self.days_label.setText(f"⚠️ Срочно продлите! Осталось: {days_remaining}")
                        self.days_label.setStyleSheet(f"color: {semantic.error};")
                    self.subscription_updated.emit(True, days_remaining)
                else:
                    self.status_badge.set_status(
                        "Подписка активна", result.get('status', ''), "active"
                    )
                    self.days_label.setText("")
                    self.subscription_updated.emit(True, 0)
            else:
                self._set_activation_section_visible(not is_linked)
                details = result.get('status', '') or (
                    "Продлите подписку в боте и нажмите «Обновить статус»."
                    if is_linked else
                    "Создайте код и привяжите устройство."
                )
                self.status_badge.set_status("Подписка не активна", details, "expired")
                self.days_label.setText("")
                self.subscription_updated.emit(False, 0)

        except Exception as e:
            self.status_badge.set_status("Ошибка", str(e), "expired")
            self._set_activation_section_visible(True)

    def _on_status_error(self, error):
        self.refresh_btn.set_loading(False)
        self.status_badge.set_status("Ошибка проверки", error, "expired")

    # ── connection test ───────────────────────────────────────────────────────

    def _test_connection(self):
        if not self.checker:
            self._init_checker()
            if not self.checker:
                self.server_status_label.setText("❌ Ошибка инициализации")
                return

        self.test_btn.setEnabled(False)
        self.test_btn.setText("Проверка...")
        self.server_status_label.setText("🔄 Проверка соединения...")

        self.current_thread = WorkerThread(self.checker.test_connection)
        self.current_thread.result_ready.connect(self._on_connection_test_complete)
        self.current_thread.error_occurred.connect(self._on_connection_test_error)
        self.current_thread.start()

    def _on_connection_test_complete(self, result):
        success, message = result
        self.test_btn.setEnabled(True)
        self.test_btn.setText("Проверить соединение")
        self.server_status_label.setText(f"{'✅' if success else '❌'} {message}")

    def _on_connection_test_error(self, error):
        self.test_btn.setEnabled(True)
        self.test_btn.setText("Проверить соединение")
        self.server_status_label.setText(f"❌ Ошибка: {error}")

    # ── reset activation ──────────────────────────────────────────────────────

    def _change_key(self):
        if MessageBox:
            box = MessageBox(
                "Подтверждение",
                "Сбросить активацию на этом устройстве?\n"
                "Будут удалены device token, offline-кэш и код привязки.\n"
                "Для восстановления потребуется повторная привязка в боте.",
                self.window(),
            )
            if not box.exec():
                return

        try:
            if self.checker:
                self.checker.clear_saved_key()
        except Exception:
            if self.RegistryManager:
                try:
                    self.RegistryManager.clear_device_token()
                    self.RegistryManager.clear_premium_cache()
                    self.RegistryManager.clear_pair_code()
                    self.RegistryManager.save_last_check()
                except Exception:
                    pass

        self.key_input.clear()
        self.activation_status.setText("")
        self._update_device_info()
        self.status_badge.set_status("Привязка сброшена", "Создайте новый код для привязки", "expired")
        self.days_label.setText("")
        self.days_label.setStyleSheet("")
        self._set_activation_section_visible(True)
        self.subscription_updated.emit(False, 0)
