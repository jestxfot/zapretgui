# ui/pages/zapret2/user_presets_page.py
"""Zapret 2 Direct: user presets management."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal, QSize, QTimer, QFileSystemWatcher
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QFileDialog,
    QMessageBox,
)
import qtawesome as qta

from ui.pages.base_page import BasePage
from ui.sidebar import ActionButton, SettingsCard
from ui.pages.presets_page import PresetCard, _RevealFrame, _SegmentedChoice
from log import log


class Zapret2UserPresetsPage(BasePage):
    preset_switched = pyqtSignal(str)
    preset_created = pyqtSignal(str)
    preset_deleted = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(
            "Мои пресеты",
            "Здесь вы можете создавать, импортировать, экспортировать и переключать пользовательские пресеты. "
            "Официальные шаблоны находятся на отдельной странице.",
            parent,
        )

        self._preset_cards: list[PresetCard] = []
        self._manager = None

        self._file_watcher: Optional[QFileSystemWatcher] = None
        self._watcher_active = False
        self._watcher_reload_timer = QTimer(self)
        self._watcher_reload_timer.setSingleShot(True)
        self._watcher_reload_timer.timeout.connect(self._reload_presets_from_watcher)

        self._action_mode: Optional[str] = None  # "create" | "rename"
        self._rename_source_name: Optional[str] = None

        self._build_ui()
        self._load_presets()

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
        self._start_watching_presets()
        self._load_presets()

    def hideEvent(self, event):
        self._stop_watching_presets()
        super().hideEvent(event)

    def _start_watching_presets(self):
        try:
            if self._watcher_active:
                return

            from preset_zapret2 import get_presets_dir
            presets_dir = get_presets_dir()
            presets_dir.mkdir(parents=True, exist_ok=True)

            if not self._file_watcher:
                self._file_watcher = QFileSystemWatcher(self)
                self._file_watcher.directoryChanged.connect(self._on_presets_dir_changed)
                self._file_watcher.fileChanged.connect(self._on_preset_file_changed)

            dir_path = str(presets_dir)
            if dir_path not in self._file_watcher.directories():
                self._file_watcher.addPath(dir_path)

            self._watcher_active = True
            self._update_watched_preset_files()

        except Exception as e:
            log(f"Ошибка запуска мониторинга пресетов: {e}", "DEBUG")

    def _stop_watching_presets(self):
        try:
            if not self._watcher_active:
                return
            if self._file_watcher:
                directories = self._file_watcher.directories()
                files = self._file_watcher.files()
                if directories:
                    self._file_watcher.removePaths(directories)
                if files:
                    self._file_watcher.removePaths(files)
            self._watcher_active = False
        except Exception as e:
            log(f"Ошибка остановки мониторинга пресетов: {e}", "DEBUG")

    def _update_watched_preset_files(self):
        try:
            if not self._watcher_active or not self._file_watcher:
                return

            from preset_zapret2 import get_presets_dir
            presets_dir = get_presets_dir()

            current_files = self._file_watcher.files()
            if current_files:
                self._file_watcher.removePaths(current_files)

            preset_files: list[str] = []
            if presets_dir.exists():
                preset_files.extend([str(p) for p in presets_dir.glob("*.txt") if p.is_file()])
            if preset_files:
                self._file_watcher.addPaths(preset_files)

        except Exception as e:
            log(f"Ошибка обновления мониторинга пресетов: {e}", "DEBUG")

    def _on_presets_dir_changed(self, path: str):
        try:
            log(f"Обнаружены изменения в папке пресетов: {path}", "DEBUG")
            self._update_watched_preset_files()
            self._schedule_presets_reload()
        except Exception as e:
            log(f"Ошибка обработки изменений папки пресетов: {e}", "DEBUG")

    def _on_preset_file_changed(self, path: str):
        try:
            log(f"Обнаружены изменения в пресете: {Path(path).name}", "DEBUG")
            self._schedule_presets_reload()
        except Exception as e:
            log(f"Ошибка обработки изменений пресета: {e}", "DEBUG")

    def _schedule_presets_reload(self, delay_ms: int = 500):
        try:
            self._watcher_reload_timer.stop()
            self._watcher_reload_timer.start(delay_ms)
        except Exception as e:
            log(f"Ошибка планирования обновления пресетов: {e}", "DEBUG")

    def _reload_presets_from_watcher(self):
        if not self.isVisible():
            return
        self._load_presets()
        self._update_watched_preset_files()

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

        # Inline create/rename panel
        self._action_reveal = _RevealFrame(self)
        self._action_reveal_layout = QVBoxLayout(self._action_reveal)
        self._action_reveal_layout.setContentsMargins(0, 0, 0, 0)
        self._action_reveal_layout.setSpacing(0)

        self._action_card = SettingsCard("")
        self._action_card.setStyleSheet(
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
        self._action_card.main_layout.setSpacing(10)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(10)
        self._action_icon = QLabel()
        self._action_icon.setPixmap(qta.icon("fa5s.plus", color="#60cdff").pixmap(18, 18))
        self._action_icon.setFixedSize(22, 22)
        header.addWidget(self._action_icon)
        self._action_title = QLabel("")
        self._action_title.setStyleSheet(
            """
            QLabel {
                color: #ffffff;
                font-size: 14px;
                font-weight: 600;
                font-family: 'Segoe UI Variable', 'Segoe UI', sans-serif;
            }
            """
        )
        header.addWidget(self._action_title)
        header.addStretch(1)
        self._action_close_btn = QPushButton()
        self._action_close_btn.setIcon(qta.icon("fa5s.times", color="#ffffff"))
        self._action_close_btn.setIconSize(QSize(12, 12))
        self._action_close_btn.setFixedSize(28, 28)
        self._action_close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._action_close_btn.setStyleSheet(
            """
            QPushButton {
                background: rgba(255, 255, 255, 0.06);
                border: none;
                border-radius: 6px;
                color: rgba(255, 255, 255, 0.85);
            }
            QPushButton:hover { background: rgba(255, 255, 255, 0.10); }
            QPushButton:pressed { background: rgba(255, 255, 255, 0.14); }
            """
        )
        self._action_close_btn.clicked.connect(self._hide_inline_action)
        header.addWidget(self._action_close_btn)
        self._action_card.add_layout(header)

        self._action_subtitle = QLabel("")
        self._action_subtitle.setStyleSheet(
            """
            QLabel {
                color: rgba(255, 255, 255, 0.6);
                font-size: 12px;
            }
            """
        )
        self._action_subtitle.setWordWrap(True)
        self._action_card.add_widget(self._action_subtitle)

        self._rename_from_label = QLabel("")
        self._rename_from_label.setStyleSheet(
            """
            QLabel {
                color: rgba(255, 255, 255, 0.55);
                font-size: 12px;
            }
            """
        )
        self._rename_from_label.setWordWrap(True)
        self._rename_from_label.hide()
        self._action_card.add_widget(self._rename_from_label)

        name_row = QVBoxLayout()
        name_row.setSpacing(6)
        name_label = QLabel("Название")
        name_label.setStyleSheet("color: rgba(255, 255, 255, 0.75); font-size: 12px;")
        name_row.addWidget(name_label)
        self._name_input = QLineEdit()
        self._name_input.setPlaceholderText("Введите название пресета…")
        self._name_input.setStyleSheet(
            """
            QLineEdit {
                background-color: rgba(255, 255, 255, 0.06);
                border: none;
                border-radius: 8px;
                color: #ffffff;
                padding: 10px 12px;
                font-size: 13px;
                font-family: 'Segoe UI Variable', 'Segoe UI', sans-serif;
            }
            QLineEdit:focus {
                background-color: rgba(255, 255, 255, 0.08);
            }
            """
        )
        self._name_input.textChanged.connect(lambda: self._set_inline_error(""))
        self._name_input.returnPressed.connect(self._submit_inline_action)
        name_row.addWidget(self._name_input)
        self._action_card.add_layout(name_row)

        self._source_container = QWidget()
        source_row = QHBoxLayout(self._source_container)
        source_row.setContentsMargins(0, 4, 0, 0)
        source_row.setSpacing(12)
        source_label = QLabel("Создать на основе")
        source_label.setStyleSheet("color: rgba(255, 255, 255, 0.75); font-size: 12px;")
        source_row.addWidget(source_label)
        source_row.addStretch(1)
        self._create_source = _SegmentedChoice("Текущего активного", "current", "Пустого", "empty", self)
        source_row.addWidget(self._create_source)
        self._action_card.add_widget(self._source_container)

        self._action_error = QLabel("")
        self._action_error.setStyleSheet(
            """
            QLabel {
                color: #ff6b6b;
                font-size: 12px;
            }
            """
        )
        self._action_error.setWordWrap(True)
        self._action_error.hide()
        self._action_card.add_widget(self._action_error)

        actions = QHBoxLayout()
        actions.setContentsMargins(0, 6, 0, 0)
        actions.setSpacing(10)
        actions.addStretch(1)
        self._action_cancel_btn = self._create_main_button("Отмена", "fa5s.times", accent=False)
        self._action_cancel_btn.setFixedHeight(32)
        self._action_cancel_btn.clicked.connect(self._hide_inline_action)
        actions.addWidget(self._action_cancel_btn)
        self._action_submit_btn = self._create_main_button("Готово", "fa5s.check", accent=True)
        self._action_submit_btn.setFixedHeight(32)
        self._action_submit_btn.clicked.connect(self._submit_inline_action)
        actions.addWidget(self._action_submit_btn)
        self._action_card.add_layout(actions)

        self._action_reveal_layout.addWidget(self._action_card)
        self.add_widget(self._action_reveal)

        self.add_section_title("Пользовательские")
        self.presets_container = QWidget()
        self.presets_layout = QVBoxLayout(self.presets_container)
        self.presets_layout.setContentsMargins(0, 0, 0, 0)
        self.presets_layout.setSpacing(8)
        self.add_widget(self.presets_container)

        self.add_spacing(16)

        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(12)
        self.create_btn = self._create_main_button("Создать новый", "fa5s.plus", accent=True)
        self.create_btn.clicked.connect(self._on_create_clicked)
        buttons_layout.addWidget(self.create_btn)
        self.import_btn = self._create_main_button("Импорт из файла", "fa5s.file-import")
        self.import_btn.clicked.connect(self._on_import_clicked)
        buttons_layout.addWidget(self.import_btn)
        buttons_layout.addStretch(1)
        buttons_widget = QWidget()
        buttons_widget.setLayout(buttons_layout)
        self.add_widget(buttons_widget)

        self.layout.addStretch()

    def _create_main_button(self, text: str, icon_name: str, accent: bool = False) -> QPushButton:
        btn = QPushButton(text)

        icon_color = "#000000" if accent else "white"
        btn.setIcon(qta.icon(icon_name, color=icon_color))
        btn.setIconSize(QSize(16, 16))
        btn.setFixedHeight(36)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)

        if accent:
            btn.setStyleSheet(
                """
                QPushButton {
                    background-color: #60cdff;
                    border: none;
                    border-radius: 6px;
                    color: #000000;
                    padding: 0 20px;
                    font-size: 13px;
                    font-weight: 600;
                    font-family: 'Segoe UI Variable', 'Segoe UI', sans-serif;
                }
                QPushButton:hover {
                    background-color: rgba(96, 205, 255, 0.9);
                }
                QPushButton:pressed {
                    background-color: rgba(96, 205, 255, 0.7);
                }
                """
            )
        else:
            btn.setStyleSheet(
                """
                QPushButton {
                    background-color: rgba(255, 255, 255, 0.08);
                    border: none;
                    border-radius: 6px;
                    color: #ffffff;
                    padding: 0 20px;
                    font-size: 13px;
                    font-weight: 600;
                    font-family: 'Segoe UI Variable', 'Segoe UI', sans-serif;
                }
                QPushButton:hover {
                    background-color: rgba(255, 255, 255, 0.15);
                }
                QPushButton:pressed {
                    background-color: rgba(255, 255, 255, 0.20);
                }
                """
            )

        return btn

    def _clear_layout(self, layout: QVBoxLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _hide_inline_action(self):
        self._action_mode = None
        self._rename_source_name = None
        self._action_error.hide()
        self._action_error.setText("")
        self._action_reveal.set_open(False)

    def _set_inline_error(self, text: str):
        self._action_error.setText(text)
        self._action_error.setVisible(bool(text))

    def _show_inline_action_create(self):
        self._action_mode = "create"
        self._rename_source_name = None
        self._set_inline_error("")
        self._action_icon.setPixmap(qta.icon("fa5s.plus", color="#60cdff").pixmap(18, 18))
        self._action_title.setText("Создать новый пресет")
        self._action_subtitle.setText(
            "Сохраните текущие настройки как отдельный пресет, чтобы быстро переключаться между конфигурациями."
        )
        self._rename_from_label.hide()
        self._source_container.show()
        self._create_source.set_value("current", emit=False)
        self._name_input.clear()
        self._name_input.setPlaceholderText("Например: Игры / YouTube / Дом")
        self._action_submit_btn.setText("Создать")
        self._action_submit_btn.setIcon(qta.icon("fa5s.check", color="#000000"))
        self._action_reveal.set_open(True)
        self.ensureWidgetVisible(self._action_reveal)
        self._name_input.setFocus()

    def _show_inline_action_rename(self, current_name: str):
        self._action_mode = "rename"
        self._rename_source_name = current_name
        self._set_inline_error("")
        self._action_icon.setPixmap(qta.icon("fa5s.edit", color="#60cdff").pixmap(18, 18))
        self._action_title.setText("Переименовать пресет")
        self._action_subtitle.setText("Имя пресета отображается в списке и используется для переключения.")
        self._rename_from_label.setText(f"Текущее имя: {current_name}")
        self._rename_from_label.show()
        self._source_container.hide()
        self._name_input.setText(current_name)
        self._name_input.selectAll()
        self._name_input.setPlaceholderText("Новое имя…")
        self._action_submit_btn.setText("Переименовать")
        self._action_submit_btn.setIcon(qta.icon("fa5s.check", color="#000000"))
        self._action_reveal.set_open(True)
        self.ensureWidgetVisible(self._action_reveal)
        self._name_input.setFocus()

    def _submit_inline_action(self):
        mode = self._action_mode
        if mode not in ("create", "rename"):
            return

        name = self._name_input.text().strip()
        if not name:
            self._set_inline_error("Введите название.")
            return

        try:
            manager = self._get_manager()

            if mode == "create":
                if manager.preset_exists(name):
                    self._set_inline_error(f"Пресет '{name}' уже существует.")
                    return

                from_current = self._create_source.value() == "current"
                preset = manager.create_preset(name, from_current=from_current)
                if not preset:
                    self._set_inline_error("Не удалось создать пресет.")
                    return

                log(f"Создан пресет '{name}'", "INFO")
                self.preset_created.emit(name)
                self._hide_inline_action()
                self._load_presets()
                return

            if mode == "rename":
                old_name = self._rename_source_name
                if not old_name:
                    self._set_inline_error("Неизвестный пресет для переименования.")
                    return
                if name == old_name:
                    self._hide_inline_action()
                    return
                if manager.preset_exists(name):
                    self._set_inline_error(f"Пресет '{name}' уже существует.")
                    return

                if not manager.rename_preset(old_name, name):
                    self._set_inline_error("Не удалось переименовать пресет.")
                    return

                log(f"Пресет '{old_name}' переименован в '{name}'", "INFO")
                self._hide_inline_action()
                self._load_presets()
                return

        except Exception as e:
            log(f"Ошибка сохранения пресета: {e}", "ERROR")
            QMessageBox.critical(self, "Ошибка", f"Ошибка: {e}")

    def _on_create_clicked(self):
        if self._action_mode == "create" and self._action_reveal.isVisible():
            self._hide_inline_action()
        else:
            self._show_inline_action_create()

    def _on_import_clicked(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Импортировать пресет",
            "",
            "Preset files (*.txt);;All files (*.*)",
        )

        if not file_path:
            return

        try:
            manager = self._get_manager()
            name = Path(file_path).stem

            if manager.preset_exists(name):
                result = QMessageBox.question(
                    self,
                    "Пресет существует",
                    f"Пресет '{name}' уже существует. Импортировать с другим именем?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )
                if result == QMessageBox.StandardButton.Yes:
                    counter = 1
                    while manager.preset_exists(f"{name}_{counter}"):
                        counter += 1
                    name = f"{name}_{counter}"
                else:
                    return

            if manager.import_preset(Path(file_path), name):
                log(f"Импортирован пресет '{name}'", "INFO")
                self.preset_created.emit(name)
                self._load_presets()
            else:
                QMessageBox.warning(self, "Ошибка", "Не удалось импортировать пресет")

        except Exception as e:
            log(f"Ошибка импорта пресета: {e}", "ERROR")
            QMessageBox.critical(self, "Ошибка", f"Ошибка импорта: {e}")

    def _load_presets(self):
        try:
            manager = self._get_manager()
            preset_names = manager.list_presets()
            active_name = manager.get_active_preset_name()

            self.active_preset_label.setText(active_name or "Не выбран")

            for card in self._preset_cards:
                card.deleteLater()
            self._preset_cards.clear()

            self._clear_layout(self.presets_layout)

            user_items: list[PresetCard] = []
            for name in preset_names:
                preset = manager.load_preset(name)
                if not preset or preset.is_builtin:
                    continue

                card = PresetCard(
                    name=name,
                    description=preset.description,
                    modified=preset.modified,
                    is_active=(name == active_name),
                    is_builtin=False,
                    parent=self,
                )
                card.activate_clicked.connect(self._on_activate_preset)
                card.rename_clicked.connect(self._on_rename_preset)
                card.duplicate_clicked.connect(self._on_duplicate_preset)
                card.reset_clicked.connect(self._on_reset_preset)
                card.delete_clicked.connect(self._on_delete_preset)
                card.export_clicked.connect(self._on_export_preset)
                user_items.append(card)
                self._preset_cards.append(card)

            for card in user_items:
                self.presets_layout.addWidget(card)

            if not user_items:
                empty_label = QLabel("Нет пользовательских пресетов. Создайте новый или сделайте копию шаблона.")
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
                self.presets_layout.addWidget(empty_label)

        except Exception as e:
            log(f"Ошибка загрузки пресетов: {e}", "ERROR")

    def _on_activate_preset(self, name: str):
        try:
            manager = self._get_manager()

            if manager.switch_preset(name, reload_dpi=True):
                log(f"Активирован пресет '{name}'", "INFO")
                self.preset_switched.emit(name)
                self._load_presets()
            else:
                QMessageBox.warning(self, "Ошибка", f"Не удалось активировать пресет '{name}'")

        except Exception as e:
            log(f"Ошибка активации пресета: {e}", "ERROR")
            QMessageBox.critical(self, "Ошибка", f"Ошибка: {e}")

    def _on_rename_preset(self, name: str):
        if self._action_mode == "rename" and self._rename_source_name == name and self._action_reveal.isVisible():
            self._hide_inline_action()
        else:
            self._show_inline_action_rename(name)

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
                self._load_presets()
            else:
                QMessageBox.warning(self, "Ошибка", "Не удалось дублировать пресет")

        except Exception as e:
            log(f"Ошибка дублирования пресета: {e}", "ERROR")
            QMessageBox.critical(self, "Ошибка", f"Ошибка: {e}")

    def _on_reset_preset(self, name: str):
        try:
            manager = self._get_manager()

            if not manager.reset_preset_to_default_template(name):
                QMessageBox.warning(self, "Ошибка", "Не удалось сбросить пресет к настройкам Default")
                return

            log(f"Сброшен пресет '{name}' к Default", "INFO")
            self.preset_switched.emit(name)
            self._load_presets()

        except Exception as e:
            log(f"Ошибка сброса пресета: {e}", "ERROR")
            QMessageBox.critical(self, "Ошибка", f"Ошибка: {e}")

    def _on_delete_preset(self, name: str):
        try:
            manager = self._get_manager()

            if manager.delete_preset(name):
                log(f"Удалён пресет '{name}'", "INFO")
                self.preset_deleted.emit(name)
                self._load_presets()
            else:
                QMessageBox.warning(self, "Ошибка", "Не удалось удалить пресет")

        except Exception as e:
            log(f"Ошибка удаления пресета: {e}", "ERROR")
            QMessageBox.critical(self, "Ошибка", f"Ошибка: {e}")

    def _on_export_preset(self, name: str):
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Экспортировать пресет",
            f"{name}.txt",
            "Preset files (*.txt);;All files (*.*)",
        )

        if not file_path:
            return

        try:
            manager = self._get_manager()

            if manager.export_preset(name, Path(file_path)):
                log(f"Экспортирован пресет '{name}' в {file_path}", "INFO")
                QMessageBox.information(self, "Успех", f"Пресет экспортирован:\n{file_path}")
            else:
                QMessageBox.warning(self, "Ошибка", "Не удалось экспортировать пресет")

        except Exception as e:
            log(f"Ошибка экспорта пресета: {e}", "ERROR")
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
