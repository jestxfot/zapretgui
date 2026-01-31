# ui/pages/zapret2/preset_templates_page.py
"""Zapret 2 Direct: built-in preset templates (read-only)."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QMessageBox
import qtawesome as qta

from ui.pages.base_page import BasePage
from ui.sidebar import ActionButton, SettingsCard
from ui.pages.presets_page import PresetCard
from log import log


class Zapret2PresetTemplatesPage(BasePage):
    """Templates page for direct_zapret2."""

    preset_switched = pyqtSignal(str)
    preset_created = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(
            "Шаблоны пресетов",
            "Официальные пресеты — это шаблоны (их нельзя изменить). "
            "Вы можете активировать шаблон или сделать копию, чтобы редактировать её.",
            parent,
        )
        self._manager = None
        self._preset_cards: list[PresetCard] = []

        self._build_ui()
        self._load_templates()

    def _get_manager(self):
        if self._manager is None:
            from preset_zapret2 import PresetManager

            self._manager = PresetManager(
                on_preset_switched=self._on_preset_switched_callback,
                on_dpi_reload_needed=self._on_dpi_reload_needed,
            )
        return self._manager

    def showEvent(self, event):
        super().showEvent(event)
        self._load_templates()

    def _build_ui(self):
        # Telegram configs link
        configs_card = SettingsCard()
        configs_card.setStyleSheet(
            """
            QFrame#settingsCard {
                background-color: rgba(255, 255, 255, 0.03);
                border: none;
                border-radius: 8px;
            }
            QFrame#settingsCard:hover {
                background-color: rgba(255, 255, 255, 0.06);
                border: none;
            }
            """
        )
        configs_layout = QHBoxLayout()
        configs_layout.setSpacing(12)

        configs_icon = QLabel()
        configs_icon.setPixmap(qta.icon("fa5b.telegram", color="#60cdff").pixmap(18, 18))
        configs_layout.addWidget(configs_icon)

        configs_title = QLabel(
            "Вы можете обмениваться категориями друг с другом\n"
            "в нашей существующей группе по конфигам (это обычные txt файлы)"
        )
        configs_title.setStyleSheet("color: rgba(255,255,255,0.85); font-size: 13px; font-weight: 600;")
        configs_layout.addWidget(configs_title)

        configs_layout.addStretch(1)

        get_configs_btn = ActionButton("Получить конфиги", "fa5s.external-link-alt", accent=True)
        get_configs_btn.setFixedHeight(36)
        get_configs_btn.clicked.connect(self._open_new_configs_post)
        configs_layout.addWidget(get_configs_btn)

        configs_card.add_layout(configs_layout)
        self.add_widget(configs_card)

        self.add_spacing(12)

        # Active preset card
        self.active_card = SettingsCard("Активный пресет")
        self.active_card.setStyleSheet(
            """
            QFrame#settingsCard {
                background-color: rgba(255, 255, 255, 0.04);
                border: none;
                border-radius: 8px;
            }
            QFrame#settingsCard:hover {
                background-color: rgba(255, 255, 255, 0.08);
                border: none;
            }
            """
        )
        active_layout = QHBoxLayout()
        active_layout.setSpacing(12)
        active_icon = QLabel()
        active_icon.setPixmap(qta.icon("fa5s.star", color="#60cdff").pixmap(20, 20))
        active_layout.addWidget(active_icon)
        self.active_preset_label = QLabel("Загрузка...")
        self.active_preset_label.setStyleSheet(
            """
            QLabel {
                color: #ffffff;
                font-size: 14px;
                font-weight: 500;
            }
            """
        )
        active_layout.addWidget(self.active_preset_label)
        active_layout.addStretch(1)
        self.active_card.add_layout(active_layout)
        self.add_widget(self.active_card)

        self.add_spacing(12)

        self.add_section_title("Шаблоны")
        self.templates_container = QWidget()
        self.templates_layout = QVBoxLayout(self.templates_container)
        self.templates_layout.setContentsMargins(0, 0, 0, 0)
        self.templates_layout.setSpacing(8)
        self.add_widget(self.templates_container)

        self.layout.addStretch()

    def _clear_layout(self, layout: QVBoxLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _load_templates(self):
        try:
            manager = self._get_manager()
            preset_names = manager.list_presets()
            active_name = manager.get_active_preset_name()

            self.active_preset_label.setText(active_name or "Не выбран")

            for card in self._preset_cards:
                card.deleteLater()
            self._preset_cards.clear()

            self._clear_layout(self.templates_layout)

            items: list[PresetCard] = []
            for name in preset_names:
                preset = manager.load_preset(name)
                if not preset or not preset.is_builtin:
                    continue
                card = PresetCard(
                    name=name,
                    description=preset.description,
                    modified=preset.modified,
                    is_active=(name == active_name),
                    is_builtin=True,
                    parent=self,
                )
                card.activate_clicked.connect(self._on_activate_preset)
                card.duplicate_clicked.connect(self._on_duplicate_preset)
                items.append(card)
                self._preset_cards.append(card)

            for card in items:
                self.templates_layout.addWidget(card)

            if not items:
                empty_label = QLabel("Нет встроенных шаблонов.")
                empty_label.setStyleSheet(
                    """
                    QLabel {
                        color: rgba(255, 255, 255, 0.5);
                        font-size: 13px;
                        padding: 20px;
                    }
                    """
                )
                empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.templates_layout.addWidget(empty_label)

        except Exception as e:
            log(f"Ошибка загрузки шаблонов пресетов: {e}", "ERROR")

    def _on_activate_preset(self, name: str):
        try:
            manager = self._get_manager()
            if manager.switch_preset(name, reload_dpi=True):
                log(f"Активирован пресет '{name}'", "INFO")
                self.preset_switched.emit(name)
                self._load_templates()
            else:
                QMessageBox.warning(self, "Ошибка", f"Не удалось активировать пресет '{name}'")
        except Exception as e:
            log(f"Ошибка активации пресета: {e}", "ERROR")
            QMessageBox.critical(self, "Ошибка", f"Ошибка: {e}")

    def _on_duplicate_preset(self, name: str):
        try:
            manager = self._get_manager()

            counter = 1
            new_name = f"{name} (копия)"
            while manager.preset_exists(new_name):
                counter += 1
                new_name = f"{name} (копия {counter})"

            if manager.duplicate_preset(name, new_name):
                log(f"Пресет '{name}' дублирован как '{new_name}'", "INFO")
                self.preset_created.emit(new_name)
                self._load_templates()
            else:
                QMessageBox.warning(self, "Ошибка", "Не удалось дублировать пресет")
        except Exception as e:
            log(f"Ошибка дублирования пресета: {e}", "ERROR")
            QMessageBox.critical(self, "Ошибка", f"Ошибка: {e}")

    def _on_preset_switched_callback(self, name: str):
        _ = name

    def _on_dpi_reload_needed(self):
        try:
            widget = self
            while widget:
                if hasattr(widget, "dpi_controller"):
                    widget.dpi_controller.restart_dpi_async()
                    log("DPI перезапущен после смены пресета", "INFO")
                    return
                widget = widget.parent()

            from PyQt6.QtWidgets import QApplication
            for w in QApplication.topLevelWidgets():
                if hasattr(w, "dpi_controller"):
                    w.dpi_controller.restart_dpi_async()
                    log("DPI перезапущен после смены пресета", "INFO")
                    return
        except Exception as e:
            log(f"Ошибка перезапуска DPI: {e}", "ERROR")

    def _open_new_configs_post(self):
        try:
            from config.telegram_links import open_telegram_link

            open_telegram_link("zaprethelp", post=66952)
        except Exception as e:
            log(f"Ошибка открытия Telegram: {e}", "ERROR")
            QMessageBox.warning(self.window(), "Ошибка", f"Не удалось открыть Telegram:\n{e}")
