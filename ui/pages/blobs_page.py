# ui/pages/blobs_page.py
"""Страница управления блобами (Zapret 2 / Direct режим)"""

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QFrame, QMessageBox, QLineEdit,
    QPushButton, QFileDialog, QDialog, QFormLayout,
    QComboBox, QSizePolicy
)
from PyQt6.QtGui import QFont
import qtawesome as qta
import os

from .base_page import BasePage
from ui.sidebar import SettingsCard, ActionButton
from ui.theme import get_theme_tokens, get_card_gradient_qss
from log import log


class BlobItemWidget(QFrame):
    """Виджет одного блоба в списке"""
    
    deleted = pyqtSignal(str)  # имя блоба
    
    def __init__(self, name: str, info: dict, parent=None):
        super().__init__(parent)
        self.blob_name = name
        self.blob_info = info

        self._tokens = get_theme_tokens()
        self._current_qss = ""
        self._applying_theme_styles = False
        self._theme_refresh_scheduled = False

        self._icon_label = None
        self._name_label = None
        self._user_badge = None
        self._desc_label = None
        self._value_label = None
        self._status_label = None
        self._delete_btn = None

        # Политика размера: предпочитает минимальную ширину
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        self._build_ui()
        
    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(12)
        
        # Иконка типа
        self._icon_label = QLabel()
        layout.addWidget(self._icon_label)
        
        # Информация о блобе
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        
        # Имя + метка пользовательского
        name_layout = QHBoxLayout()
        name_layout.setSpacing(6)
        
        self._name_label = QLabel(self.blob_name)
        name_layout.addWidget(self._name_label)
        
        if self.blob_info.get("is_user"):
            self._user_badge = QLabel("пользовательский")
            self._user_badge.setStyleSheet("""
                QLabel {
                    color: #ffc107;
                    font-size: 10px;
                    background: rgba(255, 193, 7, 0.15);
                    padding: 2px 6px;
                    border-radius: 3px;
                }
            """)
            name_layout.addWidget(self._user_badge)
        
        name_layout.addStretch()
        info_layout.addLayout(name_layout)
        
        # Описание
        desc = self.blob_info.get("description", "")
        if desc:
            self._desc_label = QLabel(desc)
            self._desc_label.setWordWrap(True)
            info_layout.addWidget(self._desc_label)
        
        # Значение (путь или hex)
        value = self.blob_info.get("value", "")
        if value:
            if value.startswith("@"):
                # Показываем только имя файла для путей
                display_value = os.path.basename(value[1:])
            else:
                display_value = value[:50] + "..." if len(value) > 50 else value
            
            value_label = QLabel(display_value)
            self._value_label = value_label
            info_layout.addWidget(self._value_label)
        
        layout.addLayout(info_layout, 1)
        
        # Статус существования файла
        if self.blob_info.get("type") == "file":
            if self.blob_info.get("exists", True):
                self._status_label = QLabel("✓")
                self._status_label.setStyleSheet("color: #6ccb5f; font-size: 14px;")
                self._status_label.setToolTip("Файл найден")
            else:
                self._status_label = QLabel("✗")
                self._status_label.setStyleSheet("color: #ff6b6b; font-size: 14px;")
                self._status_label.setToolTip("Файл не найден")
            layout.addWidget(self._status_label)
        
        # Кнопка удаления (только для пользовательских)
        if self.blob_info.get("is_user"):
            self._delete_btn = QPushButton()
            self._delete_btn.setIcon(qta.icon('fa5s.trash-alt', color='#ff6b6b'))
            self._delete_btn.setFixedSize(28, 28)
            self._delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self._delete_btn.setStyleSheet("""
                QPushButton {
                    background: rgba(255, 107, 107, 0.1);
                    border: none;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background: rgba(255, 107, 107, 0.25);
                }
            """)
            self._delete_btn.clicked.connect(self._on_delete)
            layout.addWidget(self._delete_btn)

        self._apply_theme()

    def refresh_theme(self) -> None:
        self._tokens = get_theme_tokens()
        self._apply_theme()

    def changeEvent(self, event):  # noqa: N802 (Qt override)
        try:
            from PyQt6.QtCore import QEvent

            if event.type() in (QEvent.Type.StyleChange, QEvent.Type.PaletteChange):
                self._schedule_theme_refresh()
        except Exception:
            pass
        return super().changeEvent(event)

    def _schedule_theme_refresh(self) -> None:
        if self._applying_theme_styles:
            return
        if self._theme_refresh_scheduled:
            return
        self._theme_refresh_scheduled = True
        QTimer.singleShot(0, self._on_debounced_theme_change)

    def _on_debounced_theme_change(self) -> None:
        self._theme_refresh_scheduled = False
        self.refresh_theme()

    def _apply_theme(self) -> None:
        if self._applying_theme_styles:
            return

        self._applying_theme_styles = True
        try:
            tokens = self._tokens or get_theme_tokens("Темная синяя")

            qss = f"""
                BlobItemWidget {{
                    background: {tokens.surface_bg};
                    border: 1px solid {tokens.surface_border};
                    border-radius: 6px;
                    padding: 8px;
                }}
                BlobItemWidget:hover {{
                    background: {tokens.surface_bg_hover};
                    border: 1px solid {tokens.surface_border_hover};
                }}
            """
            if qss != self._current_qss:
                self._current_qss = qss
                self.setStyleSheet(qss)

            if self._name_label is not None:
                self._name_label.setStyleSheet(
                    f"color: {tokens.fg}; font-size: 13px; font-weight: 600;"
                )
            if self._desc_label is not None:
                self._desc_label.setStyleSheet(
                    f"color: {tokens.fg_muted}; font-size: 11px;"
                )
            if self._value_label is not None:
                self._value_label.setStyleSheet(
                    f"color: {tokens.fg_faint}; font-size: 10px; font-family: Consolas;"
                )

            if self._icon_label is not None:
                if self.blob_info.get("type") == "hex":
                    icon_name = "fa5s.hashtag"
                    icon_color = "#ffc107"
                else:
                    icon_name = "fa5s.file"
                    icon_color = tokens.accent_hex
                try:
                    self._icon_label.setPixmap(qta.icon(icon_name, color=icon_color).pixmap(16, 16))
                except Exception:
                    self._icon_label.setPixmap(qta.icon("fa5s.file", color=tokens.accent_hex).pixmap(16, 16))
        finally:
            self._applying_theme_styles = False
            
    def _on_delete(self):
        """Запрос на удаление блоба"""
        reply = QMessageBox.question(
            self.window(),
            "Удаление блоба",
            f"Удалить пользовательский блоб '{self.blob_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.deleted.emit(self.blob_name)


class AddBlobDialog(QDialog):
    """Диалог добавления нового блоба в стиле Windows 11"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Добавить блоб")
        self.setFixedWidth(420)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self._applying_theme_styles = False
        self._theme_refresh_scheduled = False
        self._current_container_qss = ""

        self._container = None
        self._title_label = None
        self._close_btn = None
        self._field_labels = []
        self._input_widgets = []
        self._browse_btn = None
        self._cancel_btn = None
        self._save_btn = None

        self._build_ui()

        self._apply_theme()
        
    def _build_ui(self):
        # Основной контейнер с тенью
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        
        container = QFrame()
        container.setObjectName("dialogContainer")
        self._container = container
        
        layout = QVBoxLayout(container)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 16, 20, 16)
        
        # Заголовок с кнопкой закрытия
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 8)
        
        title = QLabel("Добавить блоб")
        self._title_label = title
        header.addWidget(title)
        header.addStretch()
        
        close_btn = QPushButton("×")
        self._close_btn = close_btn
        close_btn.setFixedSize(24, 24)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.reject)
        header.addWidget(close_btn)
        
        layout.addLayout(header)
        
        # Стили применяются через _apply_theme()
        
        # Имя блоба
        name_label = QLabel("Имя")
        self._field_labels.append(name_label)
        layout.addWidget(name_label)
        
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Латиница, цифры, подчеркивания")
        self._input_widgets.append(self.name_edit)
        self.name_edit.setFixedHeight(32)
        layout.addWidget(self.name_edit)
        
        # Тип
        type_label = QLabel("Тип")
        self._field_labels.append(type_label)
        layout.addWidget(type_label)
        
        self.type_combo = QComboBox()
        self.type_combo.addItem("Файл (.bin)", "file")
        self.type_combo.addItem("Hex значение", "hex")
        self._input_widgets.append(self.type_combo)
        self.type_combo.setFixedHeight(32)
        self.type_combo.currentIndexChanged.connect(self._on_type_changed)
        layout.addWidget(self.type_combo)
        
        # Значение
        value_label = QLabel("Значение")
        self._field_labels.append(value_label)
        layout.addWidget(value_label)
        
        self.value_widget = QWidget()
        value_layout = QHBoxLayout(self.value_widget)
        value_layout.setContentsMargins(0, 0, 0, 0)
        value_layout.setSpacing(6)
        
        self.value_edit = QLineEdit()
        self.value_edit.setPlaceholderText("Путь к файлу")
        self._input_widgets.append(self.value_edit)
        self.value_edit.setFixedHeight(32)
        value_layout.addWidget(self.value_edit, 1)
        
        self.browse_btn = QPushButton("...")
        self._browse_btn = self.browse_btn
        self.browse_btn.setFixedSize(32, 32)
        self.browse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.browse_btn.clicked.connect(self._browse_file)
        value_layout.addWidget(self.browse_btn)
        
        layout.addWidget(self.value_widget)
        
        # Описание
        desc_label = QLabel("Описание (опционально)")
        self._field_labels.append(desc_label)
        layout.addWidget(desc_label)
        
        self.desc_edit = QLineEdit()
        self.desc_edit.setPlaceholderText("Краткое описание блоба")
        self._input_widgets.append(self.desc_edit)
        self.desc_edit.setFixedHeight(32)
        layout.addWidget(self.desc_edit)
        
        # Отступ перед кнопками
        layout.addSpacing(8)
        
        # Кнопки
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(8)
        buttons_layout.addStretch()
        
        cancel_btn = QPushButton("Отмена")
        self._cancel_btn = cancel_btn
        cancel_btn.setFixedHeight(28)
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_btn)
        
        save_btn = QPushButton("Добавить")
        self._save_btn = save_btn
        save_btn.setFixedHeight(28)
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.clicked.connect(self._save)
        buttons_layout.addWidget(save_btn)
        
        layout.addLayout(buttons_layout)
        main_layout.addWidget(container)

    def changeEvent(self, event):  # noqa: N802 (Qt override)
        try:
            from PyQt6.QtCore import QEvent

            if event.type() in (QEvent.Type.StyleChange, QEvent.Type.PaletteChange):
                self._schedule_theme_refresh()
        except Exception:
            pass
        return super().changeEvent(event)

    def _schedule_theme_refresh(self) -> None:
        if self._applying_theme_styles:
            return
        if self._theme_refresh_scheduled:
            return
        self._theme_refresh_scheduled = True
        QTimer.singleShot(0, self._on_debounced_theme_change)

    def _on_debounced_theme_change(self) -> None:
        self._theme_refresh_scheduled = False
        self._apply_theme()

    def _apply_theme(self) -> None:
        if self._applying_theme_styles:
            return

        self._applying_theme_styles = True
        try:
            tokens = get_theme_tokens()
            container_bg = get_card_gradient_qss(tokens.theme_name)

            if self._container is not None:
                qss = (
                    "QFrame#dialogContainer {"
                    f"background: {container_bg};"
                    f"border: 1px solid {tokens.surface_border};"
                    "border-radius: 8px;"
                    "}"
                )
                if qss != self._current_container_qss:
                    self._current_container_qss = qss
                    self._container.setStyleSheet(qss)

            if self._title_label is not None:
                self._title_label.setStyleSheet(
                    f"color: {tokens.fg}; font-size: 15px; font-weight: 600; font-family: 'Segoe UI Variable', 'Segoe UI', sans-serif;"
                )

            if self._close_btn is not None:
                self._close_btn.setStyleSheet(
                    f"""
                    QPushButton {{
                        background: transparent;
                        border: none;
                        border-radius: 4px;
                        color: {tokens.fg_muted};
                        font-size: 18px;
                        font-weight: 400;
                    }}
                    QPushButton:hover {{
                        background: {tokens.surface_bg_hover};
                        color: {tokens.fg};
                    }}
                    """
                )

            label_style = f"color: {tokens.fg_muted}; font-size: 12px; margin-bottom: 4px;"
            for label in list(self._field_labels or []):
                try:
                    label.setStyleSheet(label_style)
                except Exception:
                    pass

            input_style = f"""
                QLineEdit, QComboBox {{
                    background: {tokens.surface_bg};
                    border: 1px solid {tokens.surface_border};
                    border-radius: 4px;
                    padding: 6px 10px;
                    color: {tokens.fg};
                    font-size: 13px;
                    font-family: 'Segoe UI Variable', 'Segoe UI', sans-serif;
                }}
                QLineEdit:focus, QComboBox:focus {{
                    border: 1px solid rgba({tokens.accent_rgb_str}, 0.60);
                    background: {tokens.surface_bg_hover};
                }}
                QLineEdit::placeholder {{
                    color: {tokens.fg_faint};
                }}
                QComboBox::drop-down {{
                    border: none;
                    width: 20px;
                }}
                QComboBox::down-arrow {{
                    image: none;
                    border-left: 4px solid transparent;
                    border-right: 4px solid transparent;
                    border-top: 5px solid {tokens.fg_muted};
                    margin-right: 8px;
                }}
                QComboBox QAbstractItemView {{
                    background: {container_bg};
                    color: {tokens.fg};
                    border: 1px solid {tokens.surface_border};
                    border-radius: 4px;
                    selection-background-color: {tokens.accent_soft_bg_hover};
                    selection-color: {tokens.fg};
                    outline: none;
                }}
            """
            for widget in list(self._input_widgets or []):
                try:
                    widget.setStyleSheet(input_style)
                except Exception:
                    pass

            if self._browse_btn is not None:
                self._browse_btn.setStyleSheet(
                    f"""
                    QPushButton {{
                        background: {tokens.surface_bg};
                        border: 1px solid {tokens.surface_border};
                        border-radius: 4px;
                        color: {tokens.fg_muted};
                        font-size: 14px;
                    }}
                    QPushButton:hover {{
                        background: {tokens.surface_bg_hover};
                        border-color: {tokens.surface_border_hover};
                        color: {tokens.fg};
                    }}
                    """
                )

            if self._cancel_btn is not None:
                self._cancel_btn.setStyleSheet(
                    f"""
                    QPushButton {{
                        background: {tokens.surface_bg};
                        border: 1px solid {tokens.surface_border};
                        border-radius: 4px;
                        padding: 0 16px;
                        color: {tokens.fg};
                        font-size: 12px;
                        font-weight: 500;
                        font-family: 'Segoe UI Variable', 'Segoe UI', sans-serif;
                    }}
                    QPushButton:hover {{
                        background: {tokens.surface_bg_hover};
                        border-color: {tokens.surface_border_hover};
                    }}
                    """
                )

            if self._save_btn is not None:
                self._save_btn.setStyleSheet(
                    f"""
                    QPushButton {{
                        background: {tokens.accent_hex};
                        border: none;
                        border-radius: 4px;
                        padding: 0 20px;
                        color: rgba(245, 245, 245, 0.95);
                        font-size: 12px;
                        font-weight: 600;
                        font-family: 'Segoe UI Variable', 'Segoe UI', sans-serif;
                    }}
                    QPushButton:hover {{
                        background: {tokens.accent_hover_hex};
                    }}
                    QPushButton:pressed {{
                        background: {tokens.accent_pressed_hex};
                    }}
                    """
                )
        finally:
            self._applying_theme_styles = False
    
    def mousePressEvent(self, event):
        """Перетаскивание окна"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
    
    def mouseMoveEvent(self, event):
        """Перетаскивание окна"""
        if event.buttons() == Qt.MouseButton.LeftButton and hasattr(self, '_drag_pos'):
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
        
    def _on_type_changed(self, index):
        """Переключение типа блоба"""
        blob_type = self.type_combo.currentData()
        self.browse_btn.setVisible(blob_type == "file")
        if blob_type == "hex":
            self.value_edit.setPlaceholderText("Hex значение (например: 0x0E0E0F0E)")
        else:
            self.value_edit.setPlaceholderText("Путь к .bin файлу")
            
    def _browse_file(self):
        """Выбор файла"""
        from config import BIN_FOLDER
        
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите файл блоба",
            BIN_FOLDER,
            "Binary files (*.bin);;All files (*.*)"
        )
        if file_path:
            # Если файл в BIN_FOLDER - сохраняем относительный путь
            if file_path.startswith(BIN_FOLDER):
                file_path = os.path.relpath(file_path, BIN_FOLDER)
            self.value_edit.setText(file_path)
            
    def _save(self):
        """Валидация и сохранение"""
        name = self.name_edit.text().strip()
        value = self.value_edit.text().strip()
        
        # Валидация имени
        if not name:
            QMessageBox.warning(self, "Ошибка", "Введите имя блоба")
            return
            
        import re
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', name):
            QMessageBox.warning(
                self, "Ошибка", 
                "Имя должно начинаться с буквы и содержать только латиницу, цифры и подчеркивания"
            )
            return
            
        # Валидация значения
        if not value:
            QMessageBox.warning(self, "Ошибка", "Введите значение блоба")
            return
            
        blob_type = self.type_combo.currentData()
        if blob_type == "hex" and not value.startswith("0x"):
            QMessageBox.warning(self, "Ошибка", "Hex значение должно начинаться с 0x")
            return
            
        self.accept()
        
    def get_data(self) -> dict:
        """Возвращает данные нового блоба"""
        return {
            "name": self.name_edit.text().strip(),
            "type": self.type_combo.currentData(),
            "value": self.value_edit.text().strip(),
            "description": self.desc_edit.text().strip()
        }


class BlobsPage(BasePage):
    """Страница управления блобами"""
    
    def __init__(self, parent=None):
        super().__init__("Блобы", "Управление бинарными данными для стратегий", parent)
        self._applying_theme_styles = False
        self._theme_refresh_scheduled = False

        self._desc_label = None
        self._filter_icon_label = None

        self._build_ui()

        self._apply_theme()
        
    def _build_ui(self):
        """Строит UI страницы"""
        
        # Описание
        desc_card = SettingsCard()
        desc = QLabel(
            "Блобы — это бинарные данные (файлы .bin или hex-значения), "
            "используемые в стратегиях для имитации TLS/QUIC пакетов.\n"
            "Вы можете добавлять свои блобы для кастомных стратегий."
        )
        self._desc_label = desc
        desc.setWordWrap(True)
        desc_card.add_widget(desc)
        self.layout.addWidget(desc_card)
        
        # Панель действий
        actions_card = SettingsCard()
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(8)
        
        # Кнопка добавления
        self.add_btn = ActionButton("Добавить блоб", "fa5s.plus")
        self.add_btn.clicked.connect(self._add_blob)
        actions_layout.addWidget(self.add_btn)
        
        # Кнопка перезагрузки
        self.reload_btn = ActionButton("Обновить", "fa5s.sync-alt")
        self.reload_btn.clicked.connect(self._reload_blobs)
        actions_layout.addWidget(self.reload_btn)
        
        # Открыть папку bin
        self.open_folder_btn = ActionButton("Папка bin", "fa5s.folder-open")
        self.open_folder_btn.clicked.connect(self._open_bin_folder)
        actions_layout.addWidget(self.open_folder_btn)
        
        # Открыть JSON
        self.open_json_btn = ActionButton("Открыть JSON", "fa5s.file-code")
        self.open_json_btn.clicked.connect(self._open_json)
        actions_layout.addWidget(self.open_json_btn)
        
        actions_layout.addStretch()
        actions_card.add_layout(actions_layout)
        
        # Счётчик под кнопками
        self.count_label = QLabel("")
        actions_card.add_widget(self.count_label)
        
        self.layout.addWidget(actions_card)
        
        # Фильтр поиска
        filter_card = SettingsCard()
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(8)
        
        filter_icon = QLabel()
        self._filter_icon_label = filter_icon
        filter_layout.addWidget(filter_icon)
        
        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("Фильтр по имени...")
        self.filter_edit.textChanged.connect(self._filter_blobs)
        filter_layout.addWidget(self.filter_edit, 1)
        
        filter_card.add_layout(filter_layout)
        self.layout.addWidget(filter_card)
        
        # Контейнер для блобов
        self.blobs_container = QWidget()
        self.blobs_container.setStyleSheet("background: transparent;")
        self.blobs_container.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        self.blobs_layout = QVBoxLayout(self.blobs_container)
        self.blobs_layout.setContentsMargins(0, 0, 0, 0)
        self.blobs_layout.setSpacing(6)
        
        self.layout.addWidget(self.blobs_container)
        
        # Загружаем блобы
        QTimer.singleShot(100, self._load_blobs)

    def changeEvent(self, event):  # noqa: N802 (Qt override)
        try:
            from PyQt6.QtCore import QEvent

            if event.type() in (QEvent.Type.StyleChange, QEvent.Type.PaletteChange):
                self._schedule_theme_refresh()
        except Exception:
            pass
        return super().changeEvent(event)

    def _schedule_theme_refresh(self) -> None:
        if self._applying_theme_styles:
            return
        if self._theme_refresh_scheduled:
            return
        self._theme_refresh_scheduled = True
        QTimer.singleShot(0, self._on_debounced_theme_change)

    def _on_debounced_theme_change(self) -> None:
        self._theme_refresh_scheduled = False
        self._apply_theme()

    def _apply_theme(self) -> None:
        if self._applying_theme_styles:
            return

        self._applying_theme_styles = True
        try:
            tokens = get_theme_tokens()

            if self._desc_label is not None:
                self._desc_label.setStyleSheet(
                    f"color: {tokens.fg_muted}; font-size: 13px;"
                )

            if hasattr(self, "count_label") and self.count_label is not None:
                self.count_label.setStyleSheet(
                    f"color: {tokens.fg_faint}; font-size: 11px; padding-top: 4px;"
                )

            if self._filter_icon_label is not None:
                self._filter_icon_label.setPixmap(
                    qta.icon('fa5s.search', color=tokens.fg_faint).pixmap(14, 14)
                )

            if hasattr(self, "filter_edit") and self.filter_edit is not None:
                self.filter_edit.setStyleSheet(
                    f"""
                    QLineEdit {{
                        background: {tokens.surface_bg};
                        border: 1px solid {tokens.surface_border};
                        border-radius: 4px;
                        padding: 6px 12px;
                        color: {tokens.fg};
                        font-size: 13px;
                    }}
                    QLineEdit:hover {{
                        background: {tokens.surface_bg_hover};
                        border-color: {tokens.surface_border_hover};
                    }}
                    QLineEdit:focus {{
                        border: 1px solid {tokens.accent_hex};
                        background: {tokens.surface_bg_hover};
                    }}
                    QLineEdit::placeholder {{
                        color: {tokens.fg_faint};
                    }}
                    """
                )

            # Update section headers + blob items.
            if hasattr(self, "blobs_layout") and self.blobs_layout is not None:
                for i in range(self.blobs_layout.count()):
                    item = self.blobs_layout.itemAt(i)
                    w = item.widget() if item else None
                    if w is None:
                        continue
                    if isinstance(w, BlobItemWidget):
                        try:
                            w.refresh_theme()
                        except Exception:
                            pass
                    elif isinstance(w, QLabel):
                        section = w.property("blobSection")
                        if section == "user":
                            w.setStyleSheet(
                                "color: #ffc107; font-size: 12px; font-weight: 600; padding: 8px 4px 4px 4px;"
                            )
                        elif section == "system":
                            w.setStyleSheet(
                                f"color: {tokens.fg_faint}; font-size: 12px; font-weight: 600; padding: 12px 4px 4px 4px;"
                            )
                        elif section == "error":
                            w.setStyleSheet("color: #ff6b6b; font-size: 13px;")
        finally:
            self._applying_theme_styles = False
        
    def _load_blobs(self):
        """Загружает и отображает список блобов"""
        try:
            from launcher_common.blobs import get_blobs_info
            
            # Очищаем контейнер
            while self.blobs_layout.count():
                item = self.blobs_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            
            blobs_info = get_blobs_info()
            
            # Разделяем на пользовательские и системные
            user_blobs = {k: v for k, v in blobs_info.items() if v.get("is_user")}
            system_blobs = {k: v for k, v in blobs_info.items() if not v.get("is_user")}
            
            # Секция пользовательских блобов
            if user_blobs:
                user_header = QLabel(f"★ Пользовательские ({len(user_blobs)})")
                user_header.setProperty("blobSection", "user")
                self.blobs_layout.addWidget(user_header)
                
                for name, info in sorted(user_blobs.items()):
                    item = BlobItemWidget(name, info)
                    item.deleted.connect(self._delete_blob)
                    self.blobs_layout.addWidget(item)
            
            # Секция системных блобов
            if system_blobs:
                system_header = QLabel(f"Системные ({len(system_blobs)})")
                system_header.setProperty("blobSection", "system")
                self.blobs_layout.addWidget(system_header)
                
                for name, info in sorted(system_blobs.items()):
                    item = BlobItemWidget(name, info)
                    self.blobs_layout.addWidget(item)
            
            # Обновляем счётчик
            total = len(blobs_info)
            user_count = len(user_blobs)
            self.count_label.setText(f"{total} блобов ({user_count} пользовательских)")

            # Refresh styles for newly created widgets.
            self._apply_theme()
            
        except Exception as e:
            log(f"Ошибка загрузки блобов: {e}", "ERROR")
            import traceback
            log(traceback.format_exc(), "DEBUG")
            
            error_label = QLabel(f"❌ Ошибка загрузки: {e}")
            error_label.setProperty("blobSection", "error")
            self.blobs_layout.addWidget(error_label)

            self._apply_theme()
            
    def _filter_blobs(self, text: str):
        """Фильтрует блобы по тексту"""
        text = text.lower()
        for i in range(self.blobs_layout.count()):
            item = self.blobs_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                if isinstance(widget, BlobItemWidget):
                    # Показываем если имя или описание содержит текст
                    match = (text in widget.blob_name.lower() or 
                            text in widget.blob_info.get("description", "").lower())
                    widget.setVisible(match)
                elif isinstance(widget, QLabel):
                    # Заголовки секций - показываем всегда
                    pass
                    
    def _add_blob(self):
        """Открывает диалог добавления блоба"""
        dialog = AddBlobDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            try:
                from launcher_common.blobs import save_user_blob
                
                if save_user_blob(data["name"], data["type"], data["value"], data["description"]):
                    log(f"Добавлен блоб: {data['name']}", "INFO")
                    self._load_blobs()  # Перезагружаем список
                else:
                    QMessageBox.warning(self, "Ошибка", "Не удалось сохранить блоб")
                    
            except Exception as e:
                log(f"Ошибка добавления блоба: {e}", "ERROR")
                QMessageBox.warning(self, "Ошибка", f"Не удалось добавить блоб:\n{e}")
                
    def _delete_blob(self, name: str):
        """Удаляет пользовательский блоб"""
        try:
            from launcher_common.blobs import delete_user_blob
            
            if delete_user_blob(name):
                log(f"Удалён блоб: {name}", "INFO")
                self._load_blobs()  # Перезагружаем список
            else:
                QMessageBox.warning(self, "Ошибка", f"Не удалось удалить блоб '{name}'")
                
        except Exception as e:
            log(f"Ошибка удаления блоба: {e}", "ERROR")
            QMessageBox.warning(self, "Ошибка", f"Не удалось удалить блоб:\n{e}")
            
    def _reload_blobs(self):
        """Перезагружает блобы из JSON"""
        try:
            from launcher_common.blobs import reload_blobs
            reload_blobs()
            self._load_blobs()
            log("Блобы перезагружены", "INFO")
        except Exception as e:
            log(f"Ошибка перезагрузки блобов: {e}", "ERROR")
            
    def _open_bin_folder(self):
        """Открывает папку bin"""
        try:
            from config import BIN_FOLDER
            os.startfile(BIN_FOLDER)
        except Exception as e:
            log(f"Ошибка открытия папки: {e}", "ERROR")
            QMessageBox.warning(self, "Ошибка", f"Не удалось открыть папку:\n{e}")
            
    def _open_json(self):
        """Открывает файл blobs.json в редакторе"""
        try:
            from config import INDEXJSON_FOLDER
            json_path = os.path.join(INDEXJSON_FOLDER, "blobs.json")
            os.startfile(json_path)
        except Exception as e:
            log(f"Ошибка открытия JSON: {e}", "ERROR")
            QMessageBox.warning(self, "Ошибка", f"Не удалось открыть файл:\n{e}")
