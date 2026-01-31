"""
Редактор конфига preset-zapret2.txt - Windows 11 Fluent Design
Поддержка hot-reload через автосохранение с debounce
"""

import os
import subprocess
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPlainTextEdit, QPushButton, QWidget,
    QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QRectF
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QLinearGradient, QBrush, QPen, QFont

from log import log


class PresetEditorDialog(QDialog):
    """Редактор конфига preset-zapret2.txt - Fluent Design"""

    AUTOSAVE_DELAY_MS = 1000  # Задержка автосохранения (debounce)

    def __init__(self, preset_path: str, parent=None):
        super().__init__(parent)

        self.preset_path = preset_path
        self._has_unsaved_changes = False
        self._is_loading = False  # Флаг для предотвращения срабатывания автосохранения при загрузке

        # Таймер для debounce автосохранения
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.timeout.connect(self._save_file)

        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setModal(False)

        # Анимация появления
        self.opacity_animation = QPropertyAnimation(self, b"windowOpacity")
        self.opacity_animation.setDuration(150)
        self.opacity_animation.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._init_ui()
        self._load_file()
        self.setWindowOpacity(0.0)

    def _init_ui(self):
        """Инициализация интерфейса"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)

        # Контейнер
        self.container = QWidget()
        self.container.setObjectName("fluentContainer")

        # Тень
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(30)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 8)
        self.container.setGraphicsEffect(shadow)

        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(16, 12, 16, 16)
        container_layout.setSpacing(12)

        # === Заголовок ===
        header = QHBoxLayout()
        header.setSpacing(8)

        title_label = QLabel("Редактор конфига")
        title_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 14px;
                font-weight: 600;
            }
        """)
        header.addWidget(title_label, 1)

        # Кнопка закрытия
        close_btn = QPushButton("×")
        close_btn.setFixedSize(28, 28)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self._close_dialog)
        close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: rgba(255,255,255,0.5);
                border: none;
                font-size: 20px;
                font-weight: 400;
                border-radius: 4px;
            }
            QPushButton:hover {
                background: rgba(255,255,255,0.1);
                color: #fff;
            }
        """)
        header.addWidget(close_btn)
        container_layout.addLayout(header)

        # === Путь к файлу ===
        path_label = QLabel(self.preset_path)
        path_label.setStyleSheet("""
            QLabel {
                color: rgba(255,255,255,0.4);
                font-size: 10px;
                font-family: 'Cascadia Code', 'Consolas', monospace;
            }
        """)
        path_label.setWordWrap(True)
        container_layout.addWidget(path_label)

        # === Текстовое поле ===
        self.text_edit = QPlainTextEdit()
        self.text_edit.setStyleSheet("""
            QPlainTextEdit {
                background: rgba(0, 0, 0, 0.3);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 6px;
                color: #d4d4d4;
                font-family: 'Cascadia Code', 'Consolas', monospace;
                font-size: 12px;
                padding: 12px;
                selection-background-color: rgba(96, 205, 255, 0.3);
            }
            QScrollBar:vertical {
                width: 8px;
                background: transparent;
            }
            QScrollBar::handle:vertical {
                background: rgba(255,255,255,0.2);
                border-radius: 4px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(255,255,255,0.3);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar:horizontal {
                height: 8px;
                background: transparent;
            }
            QScrollBar::handle:horizontal {
                background: rgba(255,255,255,0.2);
                border-radius: 4px;
                min-width: 30px;
            }
            QScrollBar::handle:horizontal:hover {
                background: rgba(255,255,255,0.3);
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
            }
        """)

        # Шрифт
        font = QFont("Cascadia Code", 12)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.text_edit.setFont(font)

        # Размеры
        self.text_edit.setMinimumSize(580, 380)

        # Подключаем автосохранение
        self.text_edit.textChanged.connect(self._on_text_changed)

        container_layout.addWidget(self.text_edit)

        # === Статус-бар ===
        status_layout = QHBoxLayout()
        status_layout.setSpacing(8)

        self.status_label = QLabel("Загружено")
        self.status_label.setStyleSheet("""
            QLabel {
                color: rgba(255,255,255,0.5);
                font-size: 11px;
            }
        """)
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        container_layout.addLayout(status_layout)

        # === Кнопки ===
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(8)

        # Кнопка перезагрузки
        reload_btn = QPushButton("Перезагрузить")
        reload_btn.setFixedHeight(32)
        reload_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        reload_btn.clicked.connect(self._load_file)
        reload_btn.setStyleSheet(self._get_button_style())
        buttons_layout.addWidget(reload_btn)

        buttons_layout.addStretch()

        # Кнопка открытия в редакторе
        open_btn = QPushButton("Открыть в редакторе")
        open_btn.setFixedHeight(32)
        open_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        open_btn.clicked.connect(self._open_in_editor)
        open_btn.setStyleSheet(self._get_button_style())
        buttons_layout.addWidget(open_btn)

        container_layout.addLayout(buttons_layout)

        # === Подсказка ===
        hint = QLabel("Изменения сохраняются автоматически • ESC — закрыть")
        hint.setStyleSheet("color: rgba(255,255,255,0.25); font-size: 10px;")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        container_layout.addWidget(hint)

        main_layout.addWidget(self.container)

        # Размер окна
        self.setFixedSize(620, 520)

    def _get_button_style(self) -> str:
        """Возвращает стиль кнопки"""
        return """
            QPushButton {
                background-color: rgba(255, 255, 255, 0.08);
                border: none;
                border-radius: 4px;
                color: #ffffff;
                padding: 0 16px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.12);
            }
            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 0.06);
            }
        """

    def paintEvent(self, event):
        """Рисуем Fluent фон"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.container.geometry()
        path = QPainterPath()
        path.addRoundedRect(QRectF(rect), 12, 12)

        # Градиент фона
        gradient = QLinearGradient(0, rect.top(), 0, rect.bottom())
        gradient.setColorAt(0, QColor(48, 48, 48, 252))
        gradient.setColorAt(1, QColor(36, 36, 36, 252))
        painter.fillPath(path, QBrush(gradient))

        # Рамка
        painter.setPen(QPen(QColor(255, 255, 255, 15), 1))
        painter.drawPath(path)

    def _load_file(self):
        """Загружает содержимое файла в текстовое поле"""
        self._is_loading = True
        try:
            if os.path.exists(self.preset_path):
                with open(self.preset_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.text_edit.setPlainText(content)
                self._update_status("Загружено", success=True)
                log(f"PresetEditorDialog: загружен файл {self.preset_path}")
            else:
                self.text_edit.setPlainText("")
                self._update_status("Файл не найден", error=True)
                log(f"PresetEditorDialog: файл не найден {self.preset_path}", "WARNING")
        except Exception as e:
            self._update_status(f"Ошибка загрузки: {e}", error=True)
            log(f"PresetEditorDialog: ошибка загрузки {e}", "ERROR")
        finally:
            self._is_loading = False
            self._has_unsaved_changes = False

    def _save_file(self):
        """Сохраняет содержимое в файл"""
        try:
            content = self.text_edit.toPlainText()

            # Создаём директорию если не существует
            dir_path = os.path.dirname(self.preset_path)
            if dir_path and not os.path.exists(dir_path):
                os.makedirs(dir_path)

            with open(self.preset_path, 'w', encoding='utf-8') as f:
                f.write(content)

            self._has_unsaved_changes = False
            self._update_status("Сохранено", success=True)
            log(f"PresetEditorDialog: файл сохранён {self.preset_path}")
        except Exception as e:
            self._update_status(f"Ошибка сохранения: {e}", error=True)
            log(f"PresetEditorDialog: ошибка сохранения {e}", "ERROR")

    def _on_text_changed(self):
        """Запускает таймер автосохранения (debounce)"""
        if self._is_loading:
            return

        self._has_unsaved_changes = True
        self._update_status("Изменено...", pending=True)

        # Перезапускаем таймер (debounce)
        self._save_timer.stop()
        self._save_timer.start(self.AUTOSAVE_DELAY_MS)

    def _update_status(self, text: str, success: bool = False, error: bool = False, pending: bool = False):
        """Обновляет статус-бар"""
        if error:
            color = "#f87171"  # Красный
        elif success:
            color = "#4ade80"  # Зелёный
        elif pending:
            color = "#fbbf24"  # Жёлтый
        else:
            color = "rgba(255,255,255,0.5)"

        self.status_label.setText(text)
        self.status_label.setStyleSheet(f"""
            QLabel {{
                color: {color};
                font-size: 11px;
            }}
        """)

    def _open_in_editor(self):
        """Открывает файл в системном редакторе"""
        try:
            # Сохраняем изменения перед открытием
            if self._has_unsaved_changes:
                self._save_file()

            # Открываем в системном редакторе
            if os.name == 'nt':  # Windows
                os.startfile(self.preset_path)
            else:
                subprocess.run(['xdg-open', self.preset_path])

            log(f"PresetEditorDialog: открыт в редакторе {self.preset_path}")
        except Exception as e:
            self._update_status(f"Ошибка открытия: {e}", error=True)
            log(f"PresetEditorDialog: ошибка открытия в редакторе {e}", "ERROR")

    def show_animated(self, pos=None):
        """Показывает диалог с анимацией"""
        if pos:
            self.move(pos)
        self.show()
        self.opacity_animation.setStartValue(0.0)
        self.opacity_animation.setEndValue(1.0)
        self.opacity_animation.start()

    def _close_dialog(self):
        """Закрывает диалог с сохранением"""
        # Сохраняем если есть несохранённые изменения
        if self._has_unsaved_changes:
            self._save_timer.stop()
            self._save_file()

        self._hide_animated()

    def _hide_animated(self):
        """Скрывает диалог с анимацией"""
        self.opacity_animation.setStartValue(1.0)
        self.opacity_animation.setEndValue(0.0)
        self.opacity_animation.finished.connect(self._on_hide_finished)
        self.opacity_animation.start()

    def _on_hide_finished(self):
        """Вызывается после завершения анимации скрытия"""
        try:
            self.opacity_animation.finished.disconnect(self._on_hide_finished)
        except:
            pass
        self.hide()
        self.close()

    def keyPressEvent(self, event):
        """Обработка нажатий клавиш"""
        if event.key() == Qt.Key.Key_Escape:
            self._close_dialog()
        elif event.key() == Qt.Key.Key_S and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            # Ctrl+S - принудительное сохранение
            self._save_timer.stop()
            self._save_file()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event):
        """Обработка закрытия окна"""
        if self._has_unsaved_changes:
            self._save_timer.stop()
            self._save_file()
        event.accept()


# === Вспомогательная функция для открытия редактора ===

def open_preset_editor(preset_path: str, parent=None, center_on_parent: bool = True):
    """
    Открывает редактор конфига.

    Args:
        preset_path: Путь к файлу preset-zapret2.txt
        parent: Родительский виджет
        center_on_parent: Центрировать относительно родителя

    Returns:
        PresetEditorDialog: Экземпляр диалога
    """
    dialog = PresetEditorDialog(preset_path, parent)

    if center_on_parent and parent:
        # Центрируем относительно родителя
        parent_rect = parent.geometry()
        dialog_size = dialog.size()
        x = parent_rect.x() + (parent_rect.width() - dialog_size.width()) // 2
        y = parent_rect.y() + (parent_rect.height() - dialog_size.height()) // 2
        dialog.show_animated(dialog.pos().__class__(x, y))
    else:
        dialog.show_animated()

    return dialog
