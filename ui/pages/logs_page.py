# ui/pages/logs_page.py
"""Страница просмотра логов в реальном времени"""

from PyQt6.QtCore import Qt, QThread, QTimer, QVariantAnimation, QEasingCurve
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QComboBox, QApplication, QMessageBox,
    QSplitter, QTextEdit
)
from PyQt6.QtGui import QFont, QColor, QTextCharFormat
import qtawesome as qta
import os
import glob
import re

from .base_page import BasePage, ScrollBlockingTextEdit
from ui.sidebar import SettingsCard, ActionButton
from log import log, global_logger, LOG_FILE, cleanup_old_logs
from log_tail import LogTailWorker
from config import LOGS_FOLDER, MAX_LOG_FILES

# Паттерны для определения РЕАЛЬНЫХ ошибок (строгие)
ERROR_PATTERNS = [
    r'\[❌ ERROR\]',           # Наш формат ошибок
    r'\[❌ CRITICAL\]',        # Критические ошибки
    r'AttributeError:',        # Python ошибки атрибутов
    r'TypeError:',             # Python ошибки типов
    r'ValueError:',            # Python ошибки значений
    r'KeyError:',              # Python ошибки ключей
    r'ImportError:',           # Python ошибки импорта
    r'ModuleNotFoundError:',   # Python модуль не найден
    r'FileNotFoundError:',     # Файл не найден
    r'PermissionError:',       # Ошибка доступа
    r'OSError:',               # Ошибка ОС
    r'RuntimeError:',          # Ошибка выполнения
    r'UnboundLocalError:',     # Переменная не определена
    r'NameError:',             # Имя не определено
    r'IndexError:',            # Индекс за пределами
    r'ZeroDivisionError:',     # Деление на ноль
    r'RecursionError:',        # Переполнение рекурсии
    r'🔴 CRASH',               # Краш репорты
]

# Паттерны для ИСКЛЮЧЕНИЯ (не ошибки, хотя содержат ключевые слова)
EXCLUDE_PATTERNS = [
    r'Faulthandler enabled',   # Информация о включении faulthandler
    r'Crash handler установлен', # Информация об установке обработчика
    r'connection error:.*HTTPSConnectionPool',  # Сетевые ошибки VPS (не критично)
    r'connection error:.*HTTPConnectionPool',   # Сетевые ошибки VPS (не критично)
    r'\[POOL\].*ошибка',       # Ошибки пула серверов (fallback работает)
    r'Theme error:.*NoneType', # Ошибки темы при инициализации (временные)
]


class LogsPage(BasePage):
    """Страница просмотра логов"""
    
    def __init__(self, parent=None):
        super().__init__("Логи", "Просмотр логов приложения в реальном времени", parent)
        
        # Отключаем горизонтальную прокрутку страницы
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self._thread = None
        self._worker = None
        self.current_log_file = getattr(global_logger, "log_file", LOG_FILE)
        self._error_pattern = re.compile('|'.join(ERROR_PATTERNS))
        self._exclude_pattern = re.compile('|'.join(EXCLUDE_PATTERNS), re.IGNORECASE)
        
        self._build_ui()
        
    def _build_ui(self):
        # ═══════════════════════════════════════════════════════════
        # Панель управления (выбор файла + кнопки в 2 ряда)
        # ═══════════════════════════════════════════════════════════
        controls_card = SettingsCard("Управление логами")
        controls_main = QVBoxLayout()
        controls_main.setSpacing(12)
        
        # Ряд 1: выбор файла + кнопка обновления
        row1 = QHBoxLayout()
        row1.setSpacing(8)
        
        self.log_combo = QComboBox()
        self.log_combo.setMinimumWidth(350)
        self.log_combo.setStyleSheet("""
            QComboBox {
                background-color: rgba(255, 255, 255, 0.05);
                color: rgba(255, 255, 255, 0.7);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 8px;
                padding: 10px 14px;
                font-size: 12px;
            }
            QComboBox:hover {
                background-color: rgba(255, 255, 255, 0.08);
                border-color: rgba(255, 255, 255, 0.15);
            }
            QComboBox::drop-down {
                border: none;
                padding-right: 10px;
            }
            QComboBox::down-arrow {
                image: none;
                width: 0;
            }
            QComboBox QAbstractItemView {
                background-color: rgba(45, 45, 48, 0.95);
                color: rgba(255, 255, 255, 0.8);
                selection-background-color: rgba(96, 205, 255, 0.2);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                padding: 4px;
                outline: none;
            }
            QComboBox QAbstractItemView::item {
                padding: 8px 12px;
                border-radius: 6px;
                margin: 2px 4px;
            }
            QComboBox QAbstractItemView::item:hover {
                background-color: rgba(255, 255, 255, 0.08);
            }
            QComboBox QAbstractItemView::item:selected {
                background-color: rgba(96, 205, 255, 0.15);
                color: #60cdff;
            }
        """)
        self.log_combo.currentIndexChanged.connect(self._on_log_selected)
        row1.addWidget(self.log_combo, 1)
        
        self.refresh_btn = QPushButton()
        self._refresh_icon_normal = qta.icon('fa5s.sync-alt', color='#ffffff')
        self._refresh_spin_animation = qta.Spin(self.refresh_btn, interval=10, step=8)
        self._refresh_icon_spinning = qta.icon('fa5s.sync-alt', color='#60cdff', animation=self._refresh_spin_animation)
        self.refresh_btn.setIcon(self._refresh_icon_normal)
        self.refresh_btn.setFixedSize(36, 36)
        self.refresh_btn.setToolTip("Обновить список файлов")
        self.refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
                border-color: rgba(255, 255, 255, 0.15);
            }
            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 0.05);
            }
        """)
        self.refresh_btn.clicked.connect(self._refresh_logs_list)
        row1.addWidget(self.refresh_btn)
        
        controls_main.addLayout(row1)
        
        # Ряд 2: кнопки действий
        row2 = QHBoxLayout()
        row2.setSpacing(8)
        
        self.copy_btn = ActionButton("Копировать", "fa5s.copy")
        self.copy_btn.clicked.connect(self._copy_log)
        row2.addWidget(self.copy_btn)
        
        self.clear_btn = ActionButton("Очистить", "fa5s.eraser")
        self.clear_btn.clicked.connect(self._clear_view)
        row2.addWidget(self.clear_btn)
        
        self.folder_btn = ActionButton("Папка", "fa5s.folder-open")
        self.folder_btn.clicked.connect(self._open_folder)
        row2.addWidget(self.folder_btn)
        
        self.send_btn = ActionButton("Отправить", "fa5s.paper-plane")
        self.send_btn.clicked.connect(self._send_log)
        row2.addWidget(self.send_btn)
        
        row2.addStretch()
        
        # Информационная строка
        self.info_label = QLabel()
        self.info_label.setStyleSheet("""
            QLabel {
                color: #60cdff;
                font-size: 11px;
            }
        """)
        row2.addWidget(self.info_label)
        
        controls_main.addLayout(row2)
        
        controls_card.add_layout(controls_main)
        self.add_widget(controls_card)
        
        # ═══════════════════════════════════════════════════════════
        # Область логов
        # ═══════════════════════════════════════════════════════════
        log_card = SettingsCard("Содержимое")
        log_layout = QVBoxLayout()
        
        # Текстовое поле для логов (блокирует провал прокрутки)
        self.log_text = ScrollBlockingTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.log_text.setFont(QFont("Consolas", 9))
        self.log_text.setMinimumHeight(260)
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #3d3d3d;
                border-radius: 6px;
                padding: 12px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 11px;
                line-height: 1.4;
            }
            QScrollBar:vertical {
                background: #2d2d30;
                width: 10px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background: #5a5a5a;
                border-radius: 5px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background: #6a6a6a;
            }
        """)
        log_layout.addWidget(self.log_text)
        
        # Статистика внизу лог-карточки
        self.stats_label = QLabel()
        self.stats_label.setStyleSheet("""
            QLabel {
                color: #666;
                font-size: 10px;
                padding-top: 4px;
            }
        """)
        log_layout.addWidget(self.stats_label)
        
        log_card.add_layout(log_layout)
        self.add_widget(log_card)
        
        # ═══════════════════════════════════════════════════════════
        # Панель ошибок
        # ═══════════════════════════════════════════════════════════
        errors_card = SettingsCard()  # Без заголовка - добавим свой с иконкой
        errors_layout = QVBoxLayout()
        
        # Заголовок с иконкой и кнопкой очистки
        errors_header = QHBoxLayout()
        
        # Иконка предупреждения
        warning_icon = QLabel()
        warning_icon.setPixmap(qta.icon('fa5s.exclamation-triangle', color='#ff6b6b').pixmap(16, 16))
        errors_header.addWidget(warning_icon)
        
        # Заголовок
        errors_title = QLabel("Ошибки и предупреждения")
        errors_title.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 14px;
                font-weight: 600;
                font-family: 'Segoe UI Variable', 'Segoe UI', sans-serif;
            }
        """)
        errors_header.addWidget(errors_title)
        errors_header.addSpacing(16)
        
        self.errors_count_label = QLabel("Ошибок: 0")
        self.errors_count_label.setStyleSheet("""
            QLabel {
                color: #ff6b6b;
                font-size: 11px;
                font-weight: bold;
            }
        """)
        errors_header.addWidget(self.errors_count_label)
        
        errors_header.addStretch()
        
        self.clear_errors_btn = ActionButton("Очистить", "fa5s.trash")
        self.clear_errors_btn.clicked.connect(self._clear_errors)
        errors_header.addWidget(self.clear_errors_btn)
        
        errors_layout.addLayout(errors_header)
        
        # Текстовое поле для ошибок (блокирует провал прокрутки)
        self.errors_text = ScrollBlockingTextEdit()
        self.errors_text.setReadOnly(True)
        self.errors_text.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.errors_text.setFont(QFont("Consolas", 9))
        self.errors_text.setFixedHeight(100)
        self.errors_text.setStyleSheet("""
            QTextEdit {
                background-color: #2a1a1a;
                color: #ff8888;
                border: 1px solid #5a2a2a;
                border-radius: 6px;
                padding: 8px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 11px;
            }
            QScrollBar:vertical {
                background: #2d2d30;
                width: 10px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background: #5a3a3a;
                border-radius: 5px;
                min-height: 30px;
            }
        """)
        errors_layout.addWidget(self.errors_text)
        
        errors_card.add_layout(errors_layout)
        self.add_widget(errors_card)
        
        # Счётчик ошибок
        self._errors_count = 0
        
        # Инициализация
        self._refresh_logs_list()
        self._update_stats()
        
    def showEvent(self, event):
        """При показе страницы запускаем мониторинг"""
        super().showEvent(event)
        self._start_tail_worker()
        
    def hideEvent(self, event):
        """При скрытии страницы останавливаем мониторинг"""
        super().hideEvent(event)
        self._stop_tail_worker()
        
    def _refresh_logs_list(self):
        """Обновляет список доступных лог-файлов"""
        # Запускаем анимацию вращения
        self.refresh_btn.setIcon(self._refresh_icon_spinning)
        self._refresh_spin_animation.start()
        
        self.log_combo.blockSignals(True)
        self.log_combo.clear()
        
        try:
            # Очищаем старые логи перед обновлением списка
            deleted, errors, total = cleanup_old_logs(LOGS_FOLDER, MAX_LOG_FILES)
            if deleted > 0:
                log(f"🗑️ Удалено старых логов: {deleted} из {total}", "INFO")
            if errors:
                log(f"⚠️ Ошибки при удалении логов: {errors[:3]}", "DEBUG")
            
            log_pattern = os.path.join(LOGS_FOLDER, "zapret_log_*.txt")
            log_files = glob.glob(log_pattern)
            log_files.sort(key=os.path.getmtime, reverse=True)
            
            current_log = getattr(global_logger, "log_file", LOG_FILE)
            current_index = 0
            
            for i, log_path in enumerate(log_files):
                filename = os.path.basename(log_path)
                size_kb = os.path.getsize(log_path) / 1024
                
                # Помечаем текущий лог
                if log_path == current_log:
                    display = f"📍 {filename} ({size_kb:.1f} KB) - ТЕКУЩИЙ"
                    current_index = i
                else:
                    display = f"{filename} ({size_kb:.1f} KB)"
                
                self.log_combo.addItem(display, log_path)
            
            self.log_combo.setCurrentIndex(current_index)
            
        except Exception as e:
            log(f"Ошибка обновления списка логов: {e}", "ERROR")
        finally:
            self.log_combo.blockSignals(False)
            # Останавливаем анимацию через небольшую задержку для визуального эффекта
            QTimer.singleShot(500, self._stop_refresh_animation)
    
    def _stop_refresh_animation(self):
        """Останавливает анимацию кнопки обновления"""
        self._refresh_spin_animation.stop()
        self.refresh_btn.setIcon(self._refresh_icon_normal)
            
    def _on_log_selected(self, index):
        """Обработчик выбора лог-файла"""
        if index < 0:
            return
            
        log_path = self.log_combo.itemData(index)
        if log_path and log_path != self.current_log_file:
            self.current_log_file = log_path
            self._start_tail_worker()
            
    def _start_tail_worker(self):
        """Запускает worker для чтения лога"""
        self._stop_tail_worker()
        
        if not self.current_log_file or not os.path.exists(self.current_log_file):
            return
            
        self.log_text.clear()
        self.info_label.setText(f"📄 {os.path.basename(self.current_log_file)}")
        
        try:
            self._thread = QThread(self)
            self._worker = LogTailWorker(self.current_log_file)
            self._worker.moveToThread(self._thread)
            
            self._thread.started.connect(self._worker.run)
            self._worker.new_lines.connect(self._append_text)
            self._worker.finished.connect(self._thread.quit)
            
            self._thread.start()
        except Exception as e:
            log(f"Ошибка запуска log tail worker: {e}", "ERROR")
            
    def _stop_tail_worker(self):
        """Останавливает worker"""
        try:
            if self._worker:
                self._worker.stop()
            if self._thread and self._thread.isRunning():
                self._thread.quit()
                self._thread.wait(1000)
        except Exception:
            pass
            
    def _append_text(self, text: str):
        """Добавляет текст в лог"""
        # Разбиваем на строки (может прийти несколько строк сразу)
        lines = text.split('\n')
        
        for line in lines:
            clean_line = line.rstrip()
            if not clean_line:
                continue
                
            # Добавляем в основной лог
            self.log_text.append(clean_line)
            
            # Проверяем на ошибки — добавляем ТОЛЬКО эту строку
            # Но исключаем ложные срабатывания
            if self._error_pattern.search(clean_line) and not self._exclude_pattern.search(clean_line):
                self._add_error(clean_line)
        
        # Автопрокрутка вниз
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        
    def _copy_log(self):
        """Копирует содержимое лога в буфер"""
        text = self.log_text.toPlainText()
        if text:
            QApplication.clipboard().setText(text)
            self.info_label.setText("✅ Скопировано в буфер обмена")
        else:
            self.info_label.setText("⚠️ Лог пуст")
            
    def _clear_view(self):
        """Очищает вид (не файл)"""
        self.log_text.clear()
        self.info_label.setText("🧹 Вид очищен")
        
    def _open_folder(self):
        """Открывает папку с логами"""
        try:
            import subprocess
            subprocess.run(['explorer', LOGS_FOLDER], check=False)
        except Exception as e:
            log(f"Ошибка открытия папки: {e}", "ERROR")
            
    def _update_stats(self):
        """Обновляет статистику"""
        try:
            log_pattern = os.path.join(LOGS_FOLDER, "zapret_log_*.txt")
            log_files = glob.glob(log_pattern)
            
            total_size = sum(os.path.getsize(f) for f in log_files) / 1024 / 1024
            
            self.stats_label.setText(
                f"📊 Всего логов: {len(log_files)} | "
                f"💾 Общий размер: {total_size:.2f} MB | "
                f"🔧 Максимум файлов: {MAX_LOG_FILES}"
            )
        except Exception as e:
            self.stats_label.setText(f"Ошибка статистики: {e}")
            
    def _send_log(self):
        """Отправляет лог в Telegram"""
        try:
            # Получаем ссылку на главное окно и menubar
            main_window = self.window()
            if hasattr(main_window, 'menubar') and hasattr(main_window.menubar, 'send_log_to_tg_with_report'):
                main_window.menubar.send_log_to_tg_with_report()
            else:
                # Fallback: открываем папку с логами
                QMessageBox.information(
                    self, 
                    "Отправка логов",
                    "Функция отправки логов недоступна.\n"
                    "Вы можете вручную отправить файл из папки логов."
                )
                self._open_folder()
        except Exception as e:
            log(f"Ошибка отправки лога: {e}", "ERROR")
            QMessageBox.warning(self, "Ошибка", f"Не удалось отправить лог:\n{e}")
            
    def _add_error(self, text: str):
        """Добавляет ошибку в панель ошибок"""
        self._errors_count += 1
        self.errors_count_label.setText(f"Ошибок: {self._errors_count}")
        
        # Добавляем текст с временной меткой
        self.errors_text.append(text)
        
        # Автопрокрутка
        scrollbar = self.errors_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        
    def _clear_errors(self):
        """Очищает панель ошибок"""
        self.errors_text.clear()
        self._errors_count = 0
        self.errors_count_label.setText("Ошибок: 0")
        self.info_label.setText("🧹 Ошибки очищены")
            
    def cleanup(self):
        """Очистка при закрытии"""
        self._stop_tail_worker()

