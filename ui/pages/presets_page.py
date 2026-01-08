# ui/pages/presets_page.py
"""Страница управления пресетами настроек DPI"""

from datetime import datetime
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QPushButton, QLineEdit, QDialog,
    QDialogButtonBox, QRadioButton, QButtonGroup,
    QFileDialog, QMessageBox, QScrollArea, QSizePolicy
)
from PyQt6.QtGui import QFont
import qtawesome as qta

from .base_page import BasePage
from ui.sidebar import SettingsCard, ActionButton
from log import log


class PresetCard(QFrame):
    """Карточка пресета в стиле Windows 11"""

    # Сигналы
    activate_clicked = pyqtSignal(str)  # name
    rename_clicked = pyqtSignal(str)    # name
    duplicate_clicked = pyqtSignal(str) # name
    delete_clicked = pyqtSignal(str)    # name
    export_clicked = pyqtSignal(str)    # name

    def __init__(self, name: str, description: str = "", modified: str = "",
                 is_active: bool = False, is_builtin: bool = False, parent=None):
        super().__init__(parent)
        self.preset_name = name
        self._is_active = is_active
        self._is_builtin = is_builtin
        self._hovered = False

        self.setObjectName("presetCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self._build_ui(name, description, modified)
        self._update_style()

    def _build_ui(self, name: str, description: str, modified: str):
        """Строит UI карточки"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 14, 16, 14)
        main_layout.setSpacing(10)

        # Верхняя строка: иконка + название + бейдж активности
        top_row = QHBoxLayout()
        top_row.setSpacing(10)

        # Иконка (звезда для активного, папка для остальных)
        icon_name = "fa5s.star" if self._is_active else "fa5s.file-alt"
        icon_color = "#60cdff" if self._is_active else "rgba(255, 255, 255, 0.6)"
        self.icon_label = QLabel()
        self.icon_label.setPixmap(qta.icon(icon_name, color=icon_color).pixmap(20, 20))
        self.icon_label.setFixedSize(24, 24)
        top_row.addWidget(self.icon_label)

        # Название
        self.name_label = QLabel(name)
        self.name_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 15px;
                font-weight: 600;
                font-family: 'Segoe UI Variable', 'Segoe UI', sans-serif;
            }
        """)
        top_row.addWidget(self.name_label)

        top_row.addStretch()

        # Бейдж "Активен"
        if self._is_active:
            active_badge = QLabel("Активен")
            active_badge.setStyleSheet("""
                QLabel {
                    color: #000000;
                    background-color: #60cdff;
                    font-size: 10px;
                    font-weight: 600;
                    padding: 3px 8px;
                    border-radius: 4px;
                }
            """)
            top_row.addWidget(active_badge)

        # Бейдж "Встроенный"
        if self._is_builtin:
            builtin_badge = QLabel("Встроенный")
            builtin_badge.setStyleSheet("""
                QLabel {
                    color: rgba(255, 255, 255, 0.7);
                    background-color: rgba(255, 255, 255, 0.1);
                    font-size: 10px;
                    font-weight: 500;
                    padding: 3px 8px;
                    border-radius: 4px;
                }
            """)
            top_row.addWidget(builtin_badge)

        main_layout.addLayout(top_row)

        # Описание (если есть)
        if description:
            desc_label = QLabel(description)
            desc_label.setStyleSheet("""
                QLabel {
                    color: rgba(255, 255, 255, 0.6);
                    font-size: 12px;
                }
            """)
            desc_label.setWordWrap(True)
            main_layout.addWidget(desc_label)

        # Дата изменения
        if modified:
            try:
                # Парсим ISO формат и форматируем красиво
                dt = datetime.fromisoformat(modified.replace('Z', '+00:00'))
                formatted_date = dt.strftime("%d.%m.%Y %H:%M")
            except:
                formatted_date = modified

            date_label = QLabel(f"Изменён: {formatted_date}")
            date_label.setStyleSheet("""
                QLabel {
                    color: rgba(255, 255, 255, 0.4);
                    font-size: 11px;
                }
            """)
            main_layout.addWidget(date_label)

        # Кнопки действий
        buttons_row = QHBoxLayout()
        buttons_row.setSpacing(8)

        # Кнопка активации (только для неактивных)
        if not self._is_active:
            self.activate_btn = self._create_action_button("Активировать", "fa5s.check")
            self.activate_btn.clicked.connect(lambda: self.activate_clicked.emit(self.preset_name))
            buttons_row.addWidget(self.activate_btn)

        # Переименовать
        self.rename_btn = self._create_action_button("Переименовать", "fa5s.edit")
        self.rename_btn.clicked.connect(lambda: self.rename_clicked.emit(self.preset_name))
        buttons_row.addWidget(self.rename_btn)

        # Дублировать
        self.duplicate_btn = self._create_action_button("Дублировать", "fa5s.copy")
        self.duplicate_btn.clicked.connect(lambda: self.duplicate_clicked.emit(self.preset_name))
        buttons_row.addWidget(self.duplicate_btn)

        # Удалить (недоступно для активного и встроенных)
        if not self._is_active and not self._is_builtin:
            self.delete_btn = self._create_action_button("Удалить", "fa5s.trash")
            self.delete_btn.clicked.connect(lambda: self.delete_clicked.emit(self.preset_name))
            buttons_row.addWidget(self.delete_btn)

        # Экспорт
        self.export_btn = self._create_action_button("Экспорт", "fa5s.file-export")
        self.export_btn.clicked.connect(lambda: self.export_clicked.emit(self.preset_name))
        buttons_row.addWidget(self.export_btn)

        buttons_row.addStretch()
        main_layout.addLayout(buttons_row)

    def _create_action_button(self, text: str, icon_name: str) -> QPushButton:
        """Создает кнопку действия в нейтральном стиле"""
        btn = QPushButton(text)
        btn.setIcon(qta.icon(icon_name, color="white"))
        btn.setIconSize(QSize(14, 14))
        btn.setFixedHeight(28)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.08);
                border: none;
                border-radius: 4px;
                color: #ffffff;
                padding: 0 12px;
                font-size: 11px;
                font-weight: 500;
                font-family: 'Segoe UI Variable', 'Segoe UI', sans-serif;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.15);
            }
            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 0.20);
            }
        """)
        return btn

    def _update_style(self):
        """Обновляет стиль карточки"""
        if self._is_active:
            bg = "rgba(96, 205, 255, 0.08)"
            border = "rgba(96, 205, 255, 0.3)"
        elif self._hovered:
            bg = "rgba(255, 255, 255, 0.08)"
            border = "rgba(255, 255, 255, 0.15)"
        else:
            bg = "rgba(255, 255, 255, 0.04)"
            border = "rgba(255, 255, 255, 0.08)"

        self.setStyleSheet(f"""
            QFrame#presetCard {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 8px;
            }}
        """)

    def enterEvent(self, event):
        self._hovered = True
        self._update_style()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        self._update_style()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        """Двойной клик для активации"""
        if event.button() == Qt.MouseButton.LeftButton and not self._is_active:
            # Одиночный клик ничего не делает, используем кнопки
            pass
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        """Двойной клик активирует пресет"""
        if event.button() == Qt.MouseButton.LeftButton and not self._is_active:
            self.activate_clicked.emit(self.preset_name)
        super().mouseDoubleClickEvent(event)


class CreatePresetDialog(QDialog):
    """Диалог создания нового пресета"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Создать пресет")
        self.setFixedSize(400, 220)
        self.setStyleSheet("""
            QDialog {
                background-color: #1c1c1c;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Заголовок
        title = QLabel("Создать новый пресет")
        title.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 16px;
                font-weight: 600;
            }
        """)
        layout.addWidget(title)

        # Поле имени
        name_layout = QVBoxLayout()
        name_layout.setSpacing(6)

        name_label = QLabel("Название")
        name_label.setStyleSheet("color: rgba(255, 255, 255, 0.8); font-size: 12px;")
        name_layout.addWidget(name_label)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Введите название пресета...")
        self.name_input.setStyleSheet("""
            QLineEdit {
                background-color: rgba(255, 255, 255, 0.06);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 6px;
                color: #ffffff;
                padding: 10px 12px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 1px solid #60cdff;
                background-color: rgba(255, 255, 255, 0.08);
            }
        """)
        name_layout.addWidget(self.name_input)
        layout.addLayout(name_layout)

        # Выбор источника
        source_layout = QVBoxLayout()
        source_layout.setSpacing(8)

        source_label = QLabel("Создать на основе")
        source_label.setStyleSheet("color: rgba(255, 255, 255, 0.8); font-size: 12px;")
        source_layout.addWidget(source_label)

        self.source_group = QButtonGroup(self)

        self.from_current_radio = QRadioButton("Текущие настройки")
        self.from_current_radio.setChecked(True)
        self.from_current_radio.setStyleSheet("""
            QRadioButton {
                color: #ffffff;
                font-size: 12px;
            }
            QRadioButton::indicator {
                width: 16px;
                height: 16px;
            }
        """)
        self.source_group.addButton(self.from_current_radio, 1)
        source_layout.addWidget(self.from_current_radio)

        self.empty_radio = QRadioButton("Пустой пресет")
        self.empty_radio.setStyleSheet("""
            QRadioButton {
                color: #ffffff;
                font-size: 12px;
            }
        """)
        self.source_group.addButton(self.empty_radio, 2)
        source_layout.addWidget(self.empty_radio)

        layout.addLayout(source_layout)

        layout.addStretch()

        # Кнопки
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        buttons.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.08);
                border: none;
                border-radius: 4px;
                color: #ffffff;
                padding: 8px 24px;
                font-size: 12px;
                font-weight: 600;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.15);
            }
            QPushButton:default {
                background-color: #60cdff;
                color: #000000;
            }
            QPushButton:default:hover {
                background-color: rgba(96, 205, 255, 0.9);
            }
        """)
        layout.addWidget(buttons)

    def get_values(self):
        """Возвращает введенные значения"""
        return {
            'name': self.name_input.text().strip(),
            'from_current': self.from_current_radio.isChecked()
        }


class RenameDialog(QDialog):
    """Диалог переименования пресета"""

    def __init__(self, current_name: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Переименовать пресет")
        self.setFixedSize(350, 150)
        self.setStyleSheet("""
            QDialog {
                background-color: #1c1c1c;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Поле имени
        name_label = QLabel("Новое название")
        name_label.setStyleSheet("color: rgba(255, 255, 255, 0.8); font-size: 12px;")
        layout.addWidget(name_label)

        self.name_input = QLineEdit(current_name)
        self.name_input.setStyleSheet("""
            QLineEdit {
                background-color: rgba(255, 255, 255, 0.06);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 6px;
                color: #ffffff;
                padding: 10px 12px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 1px solid #60cdff;
            }
        """)
        self.name_input.selectAll()
        layout.addWidget(self.name_input)

        layout.addStretch()

        # Кнопки
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        buttons.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.08);
                border: none;
                border-radius: 4px;
                color: #ffffff;
                padding: 8px 24px;
                font-size: 12px;
                font-weight: 600;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.15);
            }
            QPushButton:default {
                background-color: #60cdff;
                color: #000000;
            }
            QPushButton:default:hover {
                background-color: rgba(96, 205, 255, 0.9);
            }
        """)
        layout.addWidget(buttons)

    def get_name(self) -> str:
        return self.name_input.text().strip()


class PresetsPage(BasePage):
    """Страница управления пресетами настроек"""

    # Сигналы
    preset_switched = pyqtSignal(str)   # При переключении пресета
    preset_created = pyqtSignal(str)    # При создании
    preset_deleted = pyqtSignal(str)    # При удалении

    def __init__(self, parent=None):
        super().__init__("Пресеты настроек", "Сохраняйте и переключайте наборы настроек DPI", parent)

        self._preset_cards = []  # Список карточек для обновления
        self._manager = None     # Lazy init

        self._build_ui()
        self._load_presets()

    def _get_manager(self):
        """Получает или создает PresetManager"""
        if self._manager is None:
            from presets import PresetManager
            self._manager = PresetManager(
                on_preset_switched=self._on_preset_switched_callback,
                on_dpi_reload_needed=self._on_dpi_reload_needed
            )
        return self._manager

    def _build_ui(self):
        """Строит UI страницы"""

        # Карточка с активным пресетом
        self.active_card = SettingsCard("Активный пресет")
        active_layout = QHBoxLayout()
        active_layout.setSpacing(12)

        # Иконка
        active_icon = QLabel()
        active_icon.setPixmap(qta.icon('fa5s.star', color='#60cdff').pixmap(20, 20))
        active_layout.addWidget(active_icon)

        # Название активного пресета
        self.active_preset_label = QLabel("Загрузка...")
        self.active_preset_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 14px;
                font-weight: 500;
            }
        """)
        active_layout.addWidget(self.active_preset_label)

        active_layout.addStretch()

        self.active_card.add_layout(active_layout)
        self.add_widget(self.active_card)

        self.add_spacing(12)

        # Секция "Все пресеты"
        self.add_section_title("Все пресеты")

        # Контейнер для карточек пресетов
        self.presets_container = QWidget()
        self.presets_layout = QVBoxLayout(self.presets_container)
        self.presets_layout.setContentsMargins(0, 0, 0, 0)
        self.presets_layout.setSpacing(8)

        self.add_widget(self.presets_container)

        self.add_spacing(16)

        # Кнопки внизу
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(12)

        # Создать новый
        self.create_btn = self._create_main_button("Создать новый", "fa5s.plus", accent=True)
        self.create_btn.clicked.connect(self._on_create_clicked)
        buttons_layout.addWidget(self.create_btn)

        # Импорт
        self.import_btn = self._create_main_button("Импорт из файла", "fa5s.file-import")
        self.import_btn.clicked.connect(self._on_import_clicked)
        buttons_layout.addWidget(self.import_btn)

        buttons_layout.addStretch()

        buttons_widget = QWidget()
        buttons_widget.setLayout(buttons_layout)
        self.add_widget(buttons_widget)

        self.layout.addStretch()

    def _create_main_button(self, text: str, icon_name: str, accent: bool = False) -> QPushButton:
        """Создает основную кнопку действия"""
        btn = QPushButton(text)

        icon_color = "#000000" if accent else "white"
        btn.setIcon(qta.icon(icon_name, color=icon_color))
        btn.setIconSize(QSize(16, 16))
        btn.setFixedHeight(36)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)

        if accent:
            btn.setStyleSheet("""
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
            """)
        else:
            btn.setStyleSheet("""
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
            """)

        return btn

    def _load_presets(self):
        """Загружает и отображает список пресетов"""
        try:
            manager = self._get_manager()
            preset_names = manager.list_presets()
            active_name = manager.get_active_preset_name()

            # Обновляем лейбл активного пресета
            if active_name:
                self.active_preset_label.setText(active_name)
            else:
                self.active_preset_label.setText("Не выбран")

            # Очищаем старые карточки
            for card in self._preset_cards:
                card.deleteLater()
            self._preset_cards.clear()

            # Создаем карточки для каждого пресета
            for name in preset_names:
                preset = manager.load_preset(name)
                if preset:
                    card = PresetCard(
                        name=name,
                        description=preset.description,
                        modified=preset.modified,
                        is_active=(name == active_name),
                        is_builtin=preset.is_builtin,
                        parent=self
                    )

                    # Подключаем сигналы
                    card.activate_clicked.connect(self._on_activate_preset)
                    card.rename_clicked.connect(self._on_rename_preset)
                    card.duplicate_clicked.connect(self._on_duplicate_preset)
                    card.delete_clicked.connect(self._on_delete_preset)
                    card.export_clicked.connect(self._on_export_preset)

                    self.presets_layout.addWidget(card)
                    self._preset_cards.append(card)

            # Если нет пресетов - показываем подсказку
            if not preset_names:
                empty_label = QLabel("Нет сохранённых пресетов. Создайте первый!")
                empty_label.setStyleSheet("""
                    QLabel {
                        color: rgba(255, 255, 255, 0.5);
                        font-size: 13px;
                        padding: 20px;
                    }
                """)
                empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.presets_layout.addWidget(empty_label)

        except Exception as e:
            log(f"Ошибка загрузки пресетов: {e}", "ERROR")

    def _on_create_clicked(self):
        """Обработчик создания нового пресета"""
        dialog = CreatePresetDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            values = dialog.get_values()
            name = values['name']
            from_current = values['from_current']

            if not name:
                QMessageBox.warning(self, "Ошибка", "Введите название пресета")
                return

            try:
                manager = self._get_manager()

                # Проверяем существование
                if manager.preset_exists(name):
                    QMessageBox.warning(self, "Ошибка", f"Пресет '{name}' уже существует")
                    return

                # Создаем пресет
                preset = manager.create_preset(name, from_current=from_current)

                if preset:
                    log(f"Создан пресет '{name}'", "INFO")
                    self.preset_created.emit(name)
                    self._load_presets()
                else:
                    QMessageBox.warning(self, "Ошибка", "Не удалось создать пресет")

            except Exception as e:
                log(f"Ошибка создания пресета: {e}", "ERROR")
                QMessageBox.critical(self, "Ошибка", f"Ошибка создания: {e}")

    def _on_import_clicked(self):
        """Обработчик импорта пресета"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Импортировать пресет",
            "",
            "Preset files (*.txt);;All files (*.*)"
        )

        if file_path:
            try:
                manager = self._get_manager()

                # Получаем имя из файла
                name = Path(file_path).stem

                # Проверяем существование
                if manager.preset_exists(name):
                    result = QMessageBox.question(
                        self, "Пресет существует",
                        f"Пресет '{name}' уже существует. Импортировать с другим именем?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                    )
                    if result == QMessageBox.StandardButton.Yes:
                        # Добавляем суффикс
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

    def _on_activate_preset(self, name: str):
        """Активирует пресет"""
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
        """Переименовывает пресет"""
        dialog = RenameDialog(name, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_name = dialog.get_name()

            if not new_name:
                QMessageBox.warning(self, "Ошибка", "Введите новое название")
                return

            if new_name == name:
                return  # Ничего не изменилось

            try:
                manager = self._get_manager()

                if manager.preset_exists(new_name):
                    QMessageBox.warning(self, "Ошибка", f"Пресет '{new_name}' уже существует")
                    return

                if manager.rename_preset(name, new_name):
                    log(f"Пресет '{name}' переименован в '{new_name}'", "INFO")
                    self._load_presets()
                else:
                    QMessageBox.warning(self, "Ошибка", "Не удалось переименовать пресет")

            except Exception as e:
                log(f"Ошибка переименования пресета: {e}", "ERROR")
                QMessageBox.critical(self, "Ошибка", f"Ошибка: {e}")

    def _on_duplicate_preset(self, name: str):
        """Дублирует пресет"""
        try:
            manager = self._get_manager()

            # Генерируем имя для копии
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

    def _on_delete_preset(self, name: str):
        """Удаляет пресет"""
        result = QMessageBox.question(
            self, "Удалить пресет?",
            f"Вы уверены, что хотите удалить пресет '{name}'?\n\nЭто действие нельзя отменить.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if result == QMessageBox.StandardButton.Yes:
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
        """Экспортирует пресет"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Экспортировать пресет",
            f"{name}.txt",
            "Preset files (*.txt);;All files (*.*)"
        )

        if file_path:
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
        """Колбэк при переключении пресета (из PresetManager)"""
        pass  # Сигнал уже эмитится из _on_activate_preset

    def _on_dpi_reload_needed(self):
        """Колбэк для перезапуска DPI"""
        try:
            # Ищем dpi_controller в родительских виджетах
            widget = self
            while widget:
                if hasattr(widget, 'dpi_controller'):
                    widget.dpi_controller.restart_dpi_async()
                    log("DPI перезапущен после смены пресета", "INFO")
                    return
                widget = widget.parent()

            # Альтернативный способ через QApplication
            from PyQt6.QtWidgets import QApplication
            for w in QApplication.topLevelWidgets():
                if hasattr(w, 'dpi_controller'):
                    w.dpi_controller.restart_dpi_async()
                    log("DPI перезапущен после смены пресета", "INFO")
                    return

            log("DPI контроллер не найден для перезапуска", "WARNING")

        except Exception as e:
            log(f"Ошибка перезапуска DPI: {e}", "ERROR")

    def refresh(self):
        """Обновляет список пресетов"""
        self._load_presets()
