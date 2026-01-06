# ui/pages/preset_config_page.py
"""Страница редактора конфига preset-zapret1.txt / preset-zapret2.txt"""

import os
import subprocess
from datetime import datetime

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
)
from PyQt6.QtGui import QFont
import qtawesome as qta
import psutil

from .base_page import BasePage, ScrollBlockingPlainTextEdit
from config import MAIN_DIRECTORY
from config.config import ZAPRET2_MODES, ZAPRET1_DIRECT_MODES
from strategy_menu import get_strategy_launch_method
from log import log


class PresetConfigPage(BasePage):
    """Страница редактора конфига preset-zapret1.txt / preset-zapret2.txt"""

    def __init__(self, parent=None):
        # Сначала определяем путь к файлу, чтобы использовать в subtitle
        self._preset_path, self._preset_display_name = self._get_current_preset_path()

        super().__init__("Конфиг запуска", f"Редактор {self._preset_display_name}", parent)

        self._is_loading = False
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.timeout.connect(self._save_file)

        self._last_mtime = 0  # Для отслеживания изменений файла

        self._build_ui()
        self._setup_shortcuts()
        self._load_file()

        # Таймер для проверки статуса winws.exe/winws2.exe и изменений файла
        self._status_timer = QTimer(self)
        self._status_timer.timeout.connect(self._on_timer_tick)
        self._status_timer.start(1000)  # Каждую секунду
        self._update_winws_status()  # Начальная проверка

    def _get_current_preset_path(self) -> tuple[str, str]:
        """Returns (preset_path, display_name) based on current mode"""
        method = get_strategy_launch_method()
        if method in ZAPRET2_MODES or method == "direct_zapret2_orchestra":
            return (os.path.join(MAIN_DIRECTORY, "preset-zapret2.txt"), "preset-zapret2.txt (Zapret 2)")
        elif method in ZAPRET1_DIRECT_MODES or method == "direct_zapret1":
            return (os.path.join(MAIN_DIRECTORY, "preset-zapret1.txt"), "preset-zapret1.txt (Zapret 1)")
        else:
            # BAT mode or other - default to Zapret 2
            return (os.path.join(MAIN_DIRECTORY, "preset-zapret2.txt"), "preset-zapret2.txt (Zapret 2)")

    def refresh_for_current_mode(self):
        """Called when strategy launch method changes - reloads correct preset file"""
        new_path, new_display = self._get_current_preset_path()
        if new_path != self._preset_path:
            # Save pending changes to old file first
            if self._save_timer.isActive():
                self._save_timer.stop()
                self._save_file()

            # Switch to new file
            self._preset_path = new_path
            self._preset_display_name = new_display
            self._load_file()
            self._update_title_label()

    def _update_title_label(self):
        """Update subtitle to show which file is being edited"""
        if hasattr(self, 'subtitle_label'):
            self.subtitle_label.setText(f"Редактор {self._preset_display_name}")

    def _build_ui(self):
        """Строит UI страницы"""

        # Панель кнопок
        buttons_widget = QWidget()
        buttons_layout = QHBoxLayout(buttons_widget)
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.setSpacing(8)

        # Кнопка "Открыть в блокноте"
        self.notepad_btn = QPushButton()
        self.notepad_btn.setIcon(qta.icon("mdi.open-in-new", color="white"))
        self.notepad_btn.setText("Открыть в блокноте")
        self.notepad_btn.setFixedHeight(32)
        self.notepad_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.08);
                border: none;
                border-radius: 4px;
                color: #ffffff;
                padding: 0 16px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover { background-color: rgba(255, 255, 255, 0.15); }
            QPushButton:pressed { background-color: rgba(255, 255, 255, 0.20); }
        """)
        self.notepad_btn.clicked.connect(self._open_in_notepad)
        buttons_layout.addWidget(self.notepad_btn)

        buttons_layout.addStretch()
        self.layout.addWidget(buttons_widget)

        # Редактор
        self.editor = ScrollBlockingPlainTextEdit()
        self.editor.setFont(QFont("Consolas", 11))
        self.editor.setStyleSheet("""
            QPlainTextEdit {
                background-color: rgba(30, 30, 30, 0.95);
                color: #e0e0e0;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 6px;
                padding: 12px;
                selection-background-color: rgba(96, 205, 255, 0.3);
            }
        """)
        self.editor.setMinimumHeight(400)
        self.editor.textChanged.connect(self._on_text_changed)
        self.layout.addWidget(self.editor, 1)

        # Статус-бар
        self.status_label = QLabel()
        self.status_label.setStyleSheet("""
            QLabel {
                color: rgba(255, 255, 255, 0.5);
                font-size: 11px;
                padding-top: 8px;
            }
        """)
        self.layout.addWidget(self.status_label)

    def _setup_shortcuts(self):
        """Настраивает горячие клавиши"""
        # Ctrl+S для сохранения (уже работает автоматически)
        pass

    def _load_file(self):
        """Загружает файл с диска, создаёт если не существует"""
        self._is_loading = True
        try:
            if not os.path.exists(self._preset_path):
                # Create empty file with comment header
                with open(self._preset_path, 'w', encoding='utf-8') as f:
                    f.write(f"# {self._preset_display_name}\n# Add your winws arguments here, one per line\n\n")
                log(f"Создан новый файл: {self._preset_path}", "INFO")

            with open(self._preset_path, 'r', encoding='utf-8') as f:
                content = f.read()
            self.editor.setPlainText(content)
            self._last_mtime = os.path.getmtime(self._preset_path)
            self._update_status("Загружено")
        except Exception as e:
            log(f"Ошибка загрузки {os.path.basename(self._preset_path)}: {e}", "ERROR")
            self._update_status(f"Ошибка: {e}")
        finally:
            self._is_loading = False

    def _on_text_changed(self):
        """Обработчик изменения текста"""
        if self._is_loading:
            return

        # Debounce сохранения - 1 секунда
        self._save_timer.stop()
        self._save_timer.start(1000)
        self._update_status("Изменения...")

    def _save_file(self):
        """Сохраняет файл на диск"""
        try:
            content = self.editor.toPlainText()
            with open(self._preset_path, 'w', encoding='utf-8') as f:
                f.write(content)

            self._last_mtime = os.path.getmtime(self._preset_path)
            now = datetime.now().strftime("%H:%M:%S")
            self._update_status(f"Сохранено {now}")
            log(f"Сохранен {os.path.basename(self._preset_path)}", "DEBUG")

        except Exception as e:
            log(f"Ошибка сохранения {os.path.basename(self._preset_path)}: {e}", "ERROR")
            self._update_status(f"Ошибка: {e}")

    def _open_in_notepad(self):
        """Открывает файл в блокноте"""
        try:
            # Сначала сохраняем текущие изменения
            if self._save_timer.isActive():
                self._save_timer.stop()
                self._save_file()

            subprocess.Popen(['notepad.exe', self._preset_path])
            log(f"Открыт {os.path.basename(self._preset_path)} в блокноте", "DEBUG")

        except Exception as e:
            log(f"Ошибка открытия в блокноте: {e}", "ERROR")
            self._update_status(f"Ошибка открытия: {e}")

    def _update_status(self, text: str):
        """Обновляет статус-бар (статус файла + процесса)"""
        self._file_status = text
        self._refresh_status_label()

    def _update_winws_status(self):
        """Проверяет статус winws.exe/winws2.exe и обновляет статус-бар"""
        # Определяем какой процесс искать в зависимости от режима
        method = get_strategy_launch_method()
        if method in ZAPRET2_MODES or method == "direct_zapret2_orchestra":
            expected_process = "winws2.exe"
        else:
            expected_process = "winws.exe"

        try:
            for proc in psutil.process_iter(['name', 'pid']):
                try:
                    proc_name = proc.info['name']
                    if proc_name and proc_name.lower() in ('winws.exe', 'winws2.exe'):
                        pid = proc.info['pid']
                        self._process_status = f"✅ {proc_name} (PID: {pid})"
                        self._refresh_status_label()
                        return
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
            self._process_status = f"⚫ {expected_process} не запущен"
        except Exception as e:
            self._process_status = f"❓ Ошибка: {e}"
        self._refresh_status_label()

    def _refresh_status_label(self):
        """Обновляет лейбл статуса с обоими статусами"""
        file_status = getattr(self, '_file_status', '')
        process_status = getattr(self, '_process_status', '⏳ Проверка...')
        self.status_label.setText(f"{file_status}  •  {process_status}")

    def _on_timer_tick(self):
        """Обработчик таймера - проверяет статус процесса и изменения файла"""
        self._update_winws_status()
        self._check_file_changed()

    def _check_file_changed(self):
        """Проверяет изменился ли файл извне и перезагружает если да"""
        try:
            if not os.path.exists(self._preset_path):
                return

            current_mtime = os.path.getmtime(self._preset_path)
            if self._last_mtime and current_mtime != self._last_mtime:
                # Файл изменился извне - перезагружаем
                self._load_file()
                self._update_status("Обновлено")
            self._last_mtime = current_mtime
        except Exception:
            pass
