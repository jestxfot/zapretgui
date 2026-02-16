# ui/pages/logs_page.py
"""Страница просмотра логов в реальном времени"""

from PyQt6.QtCore import Qt, QThread, QTimer, QVariantAnimation, QEasingCurve, pyqtSignal, QObject, QSettings, QEvent
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QApplication, QMessageBox,
    QSplitter, QTextEdit, QStackedWidget, QLineEdit, QFrame
)
from PyQt6.QtGui import QFont, QColor, QTextCharFormat
import qtawesome as qta
import os
import glob
import re
import threading
import queue
import html

from .base_page import BasePage, ScrollBlockingTextEdit
from ui.sidebar import SettingsCard, ActionButton
from ui.theme import get_theme_tokens
from log import log, global_logger, LOG_FILE, cleanup_old_logs
from log_tail import LogTailWorker
from config import LOGS_FOLDER, MAX_LOG_FILES, MAX_DEBUG_LOG_FILES
from launcher_common import get_current_runner

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


class WinwsOutputWorker(QObject):
    """Worker для чтения stdout/stderr от процесса winws"""
    new_output = pyqtSignal(str, str)  # (text, stream_type: 'stdout' | 'stderr')
    process_ended = pyqtSignal(int)     # exit_code
    finished = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._running = False
        self._process = None

    def set_process(self, process):
        """Устанавливает процесс для мониторинга"""
        self._process = process

    def run(self):
        """Читает вывод процесса в реальном времени"""
        self._running = True

        if not self._process:
            self.finished.emit()
            return

        def read_stream(stream, stream_type):
            """Читает поток в отдельном потоке"""
            try:
                while self._running and self._process.poll() is None:
                    line = stream.readline()
                    if line:
                        try:
                            text = line.decode('utf-8', errors='replace').rstrip()
                        except:
                            text = str(line).rstrip()
                        if text:
                            self.new_output.emit(text, stream_type)
                    elif not self._running:
                        break

                # Читаем оставшееся после завершения
                remaining = stream.read()
                if remaining:
                    try:
                        text = remaining.decode('utf-8', errors='replace').rstrip()
                    except:
                        text = str(remaining).rstrip()
                    if text:
                        for line in text.split('\n'):
                            if line.strip():
                                self.new_output.emit(line.strip(), stream_type)
            except Exception as e:
                log(f"Ошибка чтения {stream_type}: {e}", "DEBUG")

        # Запускаем чтение stdout и stderr в отдельных потоках
        stdout_thread = None
        stderr_thread = None

        if self._process.stdout:
            stdout_thread = threading.Thread(
                target=read_stream,
                args=(self._process.stdout, 'stdout'),
                daemon=True
            )
            stdout_thread.start()

        if self._process.stderr:
            stderr_thread = threading.Thread(
                target=read_stream,
                args=(self._process.stderr, 'stderr'),
                daemon=True
            )
            stderr_thread.start()

        # Ждём завершения процесса
        try:
            while self._running and self._process.poll() is None:
                QThread.msleep(100)

            # Ждём завершения потоков чтения
            if stdout_thread and stdout_thread.is_alive():
                stdout_thread.join(timeout=1.0)
            if stderr_thread and stderr_thread.is_alive():
                stderr_thread.join(timeout=1.0)

            if self._process.returncode is not None:
                self.process_ended.emit(self._process.returncode)

        except Exception as e:
            log(f"Ошибка мониторинга процесса: {e}", "DEBUG")

        self._running = False
        self.finished.emit()

    def stop(self):
        """Останавливает worker"""
        self._running = False


class SupportAuthWorker(QObject):
    """Poll ZapretHub auth code in background."""

    finished = pyqtSignal(bool, str)  # ok, error_message

    def __init__(self, code: str, parent=None):
        super().__init__(parent)
        self._code = (code or "").strip()

    def run(self):
        try:
            from tgram.tg_log_bot import poll_upload_code

            ok, err = poll_upload_code(self._code)
            self.finished.emit(bool(ok), str(err or ""))
        except Exception as e:
            self.finished.emit(False, str(e))


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

        self._tokens = get_theme_tokens()
        self._theme_apply_scheduled = False
        self._theme_apply_pending_when_hidden = False
        self._last_theme_apply_key: tuple[str, str, str] | None = None

        # Theme-dependent colors used in runtime status/output updates.
        self._winws_stdout_color = "#00ff88"
        self._winws_stderr_color = "#ff6b6b"
        self._winws_status_neutral = self._tokens.fg_muted
        self._winws_status_running = self._tokens.accent_hex
        self._winws_status_error = self._tokens.fg

        # References for theme refresh (icons/labels created as locals).
        self._warning_icon_label = None
        self._terminal_icon_label = None
        self._info_icon_label = None
        self._orchestra_icon_label = None
        self._orchestra_text_label = None

        # Winws output worker
        self._winws_thread = None
        self._winws_worker = None
        self._winws_lines_count = 0

        # Таймер для обновления статуса winws
        self._winws_status_timer = QTimer(self)
        self._winws_status_timer.timeout.connect(self._update_winws_status)

        self._logs_tab_initialized = False
        self._send_tab_initialized = False

        # qtawesome animations (e.g. qta.Spin) are not QAbstractAnimation; track state ourselves.
        self._refresh_spin_active = False
        self._ui_built = False

    def _ensure_ui_built(self) -> None:
        if self._ui_built:
            return
        self._ui_built = True
        self._build_ui()

    def changeEvent(self, event):
        if event.type() in (QEvent.Type.StyleChange, QEvent.Type.PaletteChange):
            try:
                if not self._ui_built:
                    self._theme_apply_pending_when_hidden = True
                    return super().changeEvent(event)
                tokens = get_theme_tokens()
                if self._build_theme_apply_key(tokens) == self._last_theme_apply_key:
                    return super().changeEvent(event)
                if not self.isVisible():
                    self._theme_apply_pending_when_hidden = True
                    return super().changeEvent(event)
                self._schedule_theme_apply()
            except Exception:
                pass
        super().changeEvent(event)

    def _build_theme_apply_key(self, tokens) -> tuple[str, str, str]:
        return (str(tokens.theme_name), str(tokens.accent_hex), str(tokens.font_family_qss))

    def _schedule_theme_apply(self) -> None:
        if self._theme_apply_scheduled:
            return
        self._theme_apply_scheduled = True
        QTimer.singleShot(0, self._apply_theme_debounced)

    def _apply_theme_debounced(self) -> None:
        self._theme_apply_scheduled = False
        if not self.isVisible():
            self._theme_apply_pending_when_hidden = True
            return
        self._apply_theme()

    def _apply_theme(self, theme_name: str | None = None, *, force: bool = False) -> None:
        tokens = get_theme_tokens(theme_name)
        theme_key = self._build_theme_apply_key(tokens)
        if not force and theme_key == self._last_theme_apply_key:
            return
        self._last_theme_apply_key = theme_key
        self._tokens = tokens

        # Tabs
        self._tab_style_active = (
            "QPushButton {"
            " background-color: transparent;"
            f" color: {tokens.accent_hex};"
            " border: none;"
            f" border-bottom: 2px solid {tokens.accent_hex};"
            " padding: 8px 16px;"
            " font-size: 12px;"
            " font-weight: 600;"
            f" font-family: {tokens.font_family_qss};"
            " }"
        )
        self._tab_style_inactive = (
            "QPushButton {"
            " background-color: transparent;"
            f" color: {tokens.fg_faint};"
            " border: none;"
            " border-bottom: 2px solid transparent;"
            " padding: 8px 16px;"
            " font-size: 12px;"
            " font-weight: 600;"
            f" font-family: {tokens.font_family_qss};"
            " }"
            "QPushButton:hover {"
            f" color: {tokens.fg_muted};"
            " }"
        )

        self._tab_icon_logs_active = qta.icon('fa5s.file-alt', color=tokens.accent_hex)
        self._tab_icon_send_active = qta.icon('fa5s.paper-plane', color=tokens.accent_hex)
        self._tab_icon_inactive = qta.icon('fa5s.file-alt', color=tokens.fg_faint)
        self._tab_icon_inactive_send = qta.icon('fa5s.paper-plane', color=tokens.fg_faint)
        self._update_tab_styles()

        # Controls
        if hasattr(self, "log_combo"):
            popup_bg = tokens.surface_bg if tokens.is_light else "rgba(45, 45, 48, 0.95)"
            self.log_combo.setStyleSheet(
                "QComboBox {"
                f" background-color: {tokens.surface_bg};"
                f" color: {tokens.fg_muted};"
                f" border: 1px solid {tokens.surface_border};"
                " border-radius: 8px;"
                " padding: 10px 14px;"
                " font-size: 12px;"
                " }"
                "QComboBox:hover {"
                f" background-color: {tokens.surface_bg_hover};"
                f" border-color: {tokens.surface_border_hover};"
                " }"
                "QComboBox::drop-down { border: none; padding-right: 10px; }"
                "QComboBox::down-arrow { image: none; width: 0; }"
                "QComboBox QAbstractItemView {"
                f" background-color: {popup_bg};"
                f" color: {tokens.fg};"
                f" border: 1px solid {tokens.surface_border};"
                " border-radius: 8px;"
                " padding: 4px;"
                " outline: none;"
                " }"
                "QComboBox QAbstractItemView::item {"
                " padding: 8px 12px;"
                " border-radius: 6px;"
                " margin: 2px 4px;"
                " }"
                "QComboBox QAbstractItemView::item:hover {"
                f" background-color: {tokens.surface_bg_hover};"
                " }"
                "QComboBox QAbstractItemView::item:selected {"
                f" background-color: {tokens.accent_soft_bg};"
                f" color: {tokens.accent_hex};"
                " }"
            )

        if hasattr(self, "refresh_btn"):
            self.refresh_btn.setStyleSheet(
                "QPushButton {"
                f" background-color: {tokens.surface_bg};"
                f" border: 1px solid {tokens.surface_border};"
                " border-radius: 8px;"
                " }"
                "QPushButton:hover {"
                f" background-color: {tokens.surface_bg_hover};"
                f" border-color: {tokens.surface_border_hover};"
                " }"
                "QPushButton:pressed {"
                f" background-color: {tokens.surface_bg_pressed};"
                " }"
            )

            self._refresh_icon_normal = qta.icon('fa5s.sync-alt', color=tokens.fg)
            self._refresh_icon_spinning = qta.icon(
                'fa5s.sync-alt',
                color=tokens.accent_hex,
                animation=self._refresh_spin_animation,
            )
            self.refresh_btn.setIcon(
                self._refresh_icon_spinning
                if bool(getattr(self, "_refresh_spin_active", False))
                else self._refresh_icon_normal
            )

        if hasattr(self, "info_label"):
            self.info_label.setStyleSheet(f"QLabel {{ color: {tokens.accent_hex}; font-size: 11px; }}")

        # Log area
        editor_bg = tokens.surface_bg if tokens.is_light else "rgba(0, 0, 0, 0.55)"
        editor_fg = tokens.fg if tokens.is_light else "rgba(245, 245, 245, 0.90)"
        if hasattr(self, "log_text"):
            self.log_text.setStyleSheet(
                "QTextEdit {"
                f" background-color: {editor_bg};"
                f" color: {editor_fg};"
                f" border: 1px solid {tokens.surface_border};"
                " border-radius: 6px;"
                " padding: 12px;"
                " font-family: 'Consolas', 'Courier New', monospace;"
                " font-size: 11px;"
                " line-height: 1.4;"
                " }"
            )

        if hasattr(self, "stats_label"):
            self.stats_label.setProperty("tone", "faint")
            self.stats_label.setStyleSheet("font-size: 10px; padding-top: 4px;")

        # Errors panel
        err_fg = "rgba(220, 38, 38, 0.92)" if tokens.is_light else "rgba(248, 113, 113, 0.95)"
        err_bg = "rgba(220, 38, 38, 0.08)" if tokens.is_light else "rgba(248, 113, 113, 0.10)"
        err_border = "rgba(220, 38, 38, 0.25)" if tokens.is_light else "rgba(248, 113, 113, 0.25)"

        if self._warning_icon_label is not None:
            try:
                self._warning_icon_label.setPixmap(qta.icon('fa5s.exclamation-triangle', color=err_fg).pixmap(16, 16))
            except Exception:
                pass

        if hasattr(self, "errors_count_label"):
            self.errors_count_label.setStyleSheet(f"QLabel {{ color: {err_fg}; font-size: 11px; font-weight: bold; }}")

        if hasattr(self, "errors_text"):
            self.errors_text.setStyleSheet(
                "QTextEdit {"
                f" background-color: {err_bg};"
                f" color: {err_fg};"
                f" border: 1px solid {err_border};"
                " border-radius: 6px;"
                " padding: 8px;"
                " font-family: 'Consolas', 'Courier New', monospace;"
                " font-size: 11px;"
                " }"
            )

        # winws panel
        if self._terminal_icon_label is not None:
            try:
                self._terminal_icon_label.setPixmap(qta.icon('fa5s.terminal', color=tokens.accent_hex).pixmap(16, 16))
            except Exception:
                pass

        self._winws_stdout_color = "rgba(21, 128, 61, 0.92)" if tokens.is_light else "#00ff88"
        self._winws_stderr_color = err_fg
        self._winws_status_neutral = tokens.fg_muted
        self._winws_status_running = tokens.accent_hex
        self._winws_status_error = err_fg

        if hasattr(self, "winws_text"):
            self.winws_text.setStyleSheet(
                "QTextEdit {"
                f" background-color: {editor_bg};"
                f" color: {editor_fg};"
                f" border: 1px solid {tokens.surface_border};"
                " border-radius: 6px;"
                " padding: 8px;"
                " font-family: 'Consolas', 'Courier New', monospace;"
                " font-size: 11px;"
                " }"
            )
            self._refresh_winws_status_style_only()

        # Send tab (exists only after lazy init)
        if self._info_icon_label is not None:
            try:
                self._info_icon_label.setPixmap(qta.icon('fa5s.info-circle', color=tokens.accent_hex).pixmap(14, 14))
            except Exception:
                pass

        if hasattr(self, "send_status_label"):
            self.send_status_label.setStyleSheet(f"color: {tokens.accent_hex}; font-size: 11px;")

        if hasattr(self, "problem_text"):
            self.problem_text.setStyleSheet(
                "QTextEdit {"
                f" background-color: {tokens.surface_bg};"
                f" color: {tokens.fg};"
                f" border: 1px solid {tokens.surface_border};"
                " border-radius: 8px;"
                " padding: 12px;"
                " font-size: 12px;"
                " }"
                "QTextEdit:focus {"
                f" border-color: {tokens.accent_hex};"
                f" background-color: {tokens.surface_bg_hover};"
                " }"
            )

        if hasattr(self, "tg_contact"):
            self.tg_contact.setStyleSheet(
                "QLineEdit {"
                f" background-color: {tokens.surface_bg};"
                f" color: {tokens.fg};"
                f" border: 1px solid {tokens.surface_border};"
                " border-radius: 8px;"
                " padding: 12px;"
                " font-size: 12px;"
                " }"
                "QLineEdit:focus {"
                f" border-color: {tokens.accent_hex};"
                f" background-color: {tokens.surface_bg_hover};"
                " }"
            )

    def _update_tab_styles(self) -> None:
        if not hasattr(self, "tab_logs_btn") or not hasattr(self, "tab_send_btn"):
            return

        idx = 0
        try:
            idx = self.stacked_widget.currentIndex()
        except Exception:
            idx = 0

        if idx == 0:
            self.tab_logs_btn.setStyleSheet(self._tab_style_active)
            self.tab_logs_btn.setIcon(getattr(self, "_tab_icon_logs_active", qta.icon('fa5s.file-alt')))
            self.tab_send_btn.setStyleSheet(self._tab_style_inactive)
            self.tab_send_btn.setIcon(getattr(self, "_tab_icon_inactive_send", qta.icon('fa5s.paper-plane')))
        else:
            self.tab_logs_btn.setStyleSheet(self._tab_style_inactive)
            self.tab_logs_btn.setIcon(getattr(self, "_tab_icon_inactive", qta.icon('fa5s.file-alt')))
            self.tab_send_btn.setStyleSheet(self._tab_style_active)
            self.tab_send_btn.setIcon(getattr(self, "_tab_icon_send_active", qta.icon('fa5s.paper-plane')))

    def _refresh_winws_status_style_only(self) -> None:
        try:
            cur = (self.winws_status_label.text() or "").strip()
        except Exception:
            cur = ""
        if not cur:
            self._set_winws_status("neutral", "")
            return

        if "PID:" in cur:
            self._set_winws_status("running", cur)
            return

        if "ошиб" in cur.lower():
            self._set_winws_status("error", cur)
            return

        self._set_winws_status("neutral", cur)

    def _set_winws_status(self, kind: str, text: str) -> None:
        if kind == "running":
            color = self._winws_status_running
        elif kind == "error":
            color = self._winws_status_error
        else:
            color = self._winws_status_neutral

        self.winws_status_label.setText(text)
        self.winws_status_label.setStyleSheet(f"QLabel {{ color: {color}; font-size: 11px; }}")
        
    def _build_ui(self):
        # ═══════════════════════════════════════════════════════════
        # Переключатель табов (ЛОГИ / ОТПРАВКА)
        # ═══════════════════════════════════════════════════════════
        tabs_container = QWidget()
        tabs_layout = QHBoxLayout(tabs_container)
        tabs_layout.setContentsMargins(0, 0, 0, 8)
        tabs_layout.setSpacing(0)

        self.tab_logs_btn = QPushButton()
        self.tab_logs_btn.setText(" ЛОГИ")
        self.tab_logs_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.tab_logs_btn.clicked.connect(lambda: self._switch_tab(0))
        tabs_layout.addWidget(self.tab_logs_btn)

        self.tab_send_btn = QPushButton()
        self.tab_send_btn.setText(" ОТПРАВКА")
        self.tab_send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.tab_send_btn.clicked.connect(lambda: self._switch_tab(1))
        tabs_layout.addWidget(self.tab_send_btn)

        tabs_layout.addStretch()

        # Styles are token-driven and set in _apply_theme().
        self._tab_style_active = ""
        self._tab_style_inactive = ""

        self.add_widget(tabs_container)

        # ═══════════════════════════════════════════════════════════
        # Стек страниц (ЛОГИ / ОТПРАВКА)
        # ═══════════════════════════════════════════════════════════
        self.stacked_widget = QStackedWidget()

        # Страница 1: Логи
        self._logs_page = QWidget()
        logs_layout = QVBoxLayout(self._logs_page)
        logs_layout.setContentsMargins(0, 0, 0, 0)
        logs_layout.setSpacing(16)

        self._build_logs_tab(logs_layout)

        # Страница 2: Отправка (лениво создаётся при первом переходе)
        self._send_page = QWidget()
        send_layout = QVBoxLayout(self._send_page)
        send_layout.setContentsMargins(0, 0, 0, 0)
        send_layout.setSpacing(16)
        self._send_layout = send_layout

        self.stacked_widget.addWidget(self._logs_page)
        self.stacked_widget.addWidget(self._send_page)

        self.add_widget(self.stacked_widget)

        # Apply token-driven styles once widgets exist.
        self._apply_theme()

    def _switch_tab(self, index: int):
        """Переключает между табами"""
        if index == 1 and not self._send_tab_initialized:
            self._send_tab_initialized = True
            try:
                self._build_send_tab(self._send_layout)
            except Exception as e:
                log(f"Ошибка построения вкладки отправки: {e}", "ERROR")

        self.stacked_widget.setCurrentIndex(index)

        self._update_tab_styles()

        if index == 1:
            # Обновляем видимость индикатора оркестратора
            self._update_orchestra_indicator()

    def _build_logs_tab(self, parent_layout):
        """Строит вкладку с логами"""
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
        self.log_combo.currentIndexChanged.connect(self._on_log_selected)
        row1.addWidget(self.log_combo, 1)
        
        self.refresh_btn = QPushButton()
        tokens = get_theme_tokens()
        self._refresh_icon_normal = qta.icon('fa5s.sync-alt', color=tokens.fg)
        self._refresh_spin_animation = qta.Spin(self.refresh_btn, interval=10, step=8)
        self._refresh_icon_spinning = qta.icon('fa5s.sync-alt', color=tokens.accent_hex, animation=self._refresh_spin_animation)
        self.refresh_btn.setIcon(self._refresh_icon_normal)
        self.refresh_btn.setFixedSize(36, 36)
        self.refresh_btn.setToolTip("Обновить список файлов")
        self.refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
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

        row2.addStretch()
        
        # Информационная строка
        self.info_label = QLabel()
        row2.addWidget(self.info_label)
        
        controls_main.addLayout(row2)
        
        controls_card.add_layout(controls_main)
        parent_layout.addWidget(controls_card)

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
        log_layout.addWidget(self.log_text)
        
        # Статистика внизу лог-карточки
        self.stats_label = QLabel()
        log_layout.addWidget(self.stats_label)
        
        log_card.add_layout(log_layout)
        parent_layout.addWidget(log_card)

        # ═══════════════════════════════════════════════════════════
        # Панель ошибок
        # ═══════════════════════════════════════════════════════════
        errors_card = SettingsCard()  # Без заголовка - добавим свой с иконкой
        errors_layout = QVBoxLayout()
        
        # Заголовок с иконкой и кнопкой очистки
        errors_header = QHBoxLayout()
        
        # Иконка предупреждения
        warning_icon = QLabel()
        self._warning_icon_label = warning_icon
        errors_header.addWidget(warning_icon)
        
        # Заголовок
        errors_title = QLabel("Ошибки и предупреждения")
        errors_title.setProperty("tone", "primary")
        errors_title.setStyleSheet("font-size: 14px; font-weight: 600;")
        errors_header.addWidget(errors_title)
        errors_header.addSpacing(16)
        
        self.errors_count_label = QLabel("Ошибок: 0")
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
        errors_layout.addWidget(self.errors_text)

        errors_card.add_layout(errors_layout)
        parent_layout.addWidget(errors_card)

        # ═══════════════════════════════════════════════════════════
        # Панель вывода winws.exe
        # ═══════════════════════════════════════════════════════════
        winws_card = SettingsCard()
        winws_layout = QVBoxLayout()

        # Заголовок с иконкой
        winws_header = QHBoxLayout()

        # Иконка терминала
        terminal_icon = QLabel()
        self._terminal_icon_label = terminal_icon
        winws_header.addWidget(terminal_icon)

        # Заголовок
        winws_title = QLabel("Вывод winws.exe")
        winws_title.setProperty("tone", "primary")
        winws_title.setStyleSheet("font-size: 14px; font-weight: 600;")
        winws_header.addWidget(winws_title)
        winws_header.addSpacing(16)

        # Статус процесса
        self.winws_status_label = QLabel("Процесс не запущен")
        winws_header.addWidget(self.winws_status_label)

        winws_header.addStretch()

        # Кнопка очистки
        self.clear_winws_btn = ActionButton("Очистить", "fa5s.trash")
        self.clear_winws_btn.clicked.connect(self._clear_winws_output)
        winws_header.addWidget(self.clear_winws_btn)

        winws_layout.addLayout(winws_header)

        # Текстовое поле для вывода winws
        self.winws_text = ScrollBlockingTextEdit()
        self.winws_text.setReadOnly(True)
        self.winws_text.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.winws_text.setFont(QFont("Consolas", 9))
        self.winws_text.setFixedHeight(150)
        winws_layout.addWidget(self.winws_text)

        winws_card.add_layout(winws_layout)
        parent_layout.addWidget(winws_card)

        # Счётчик ошибок
        self._errors_count = 0
        try:
            self.stats_label.setText("📊 Загрузка...")
        except Exception:
            pass

    def _build_send_tab(self, parent_layout):
        """Строит вкладку отправки лога"""
        import time
        import platform

        # ═══════════════════════════════════════════════════════════
        # Форма отправки
        # ═══════════════════════════════════════════════════════════
        send_card = SettingsCard("Отправка лога в техподдержку")
        send_layout = QVBoxLayout()
        send_layout.setSpacing(16)

        # Индикатор режима оркестратора (скрыт по умолчанию)
        self.orchestra_mode_container = QWidget()
        orchestra_layout = QHBoxLayout(self.orchestra_mode_container)
        orchestra_layout.setContentsMargins(12, 8, 12, 8)
        orchestra_layout.setSpacing(8)

        orchestra_icon = QLabel()
        orchestra_icon.setPixmap(qta.icon('fa5s.brain', color='#a855f7').pixmap(16, 16))
        self._orchestra_icon_label = orchestra_icon
        orchestra_layout.addWidget(orchestra_icon)

        orchestra_text = QLabel("Режим оркестратора активен — будут отправлены 2 файла")
        orchestra_text.setStyleSheet("color: #a855f7; font-size: 12px; font-weight: 600; background: transparent;")
        self._orchestra_text_label = orchestra_text
        orchestra_layout.addWidget(orchestra_text)
        orchestra_layout.addStretch()

        self.orchestra_mode_container.setStyleSheet("""
            QWidget {
                background-color: rgba(168, 85, 247, 0.15);
                border-radius: 8px;
            }
        """)
        self.orchestra_mode_container.setVisible(False)
        send_layout.addWidget(self.orchestra_mode_container)

        # Описание
        desc_label = QLabel(
            "Опишите проблему и оставьте контакты для обратной связи (необязательно):"
        )
        desc_label.setProperty("tone", "muted")
        desc_label.setStyleSheet("font-size: 12px;")
        desc_label.setWordWrap(True)
        send_layout.addWidget(desc_label)

        # Поле "Описание проблемы"
        problem_header = QLabel("Описание проблемы:")
        problem_header.setProperty("tone", "primary")
        problem_header.setStyleSheet("font-size: 12px; font-weight: 600;")
        send_layout.addWidget(problem_header)

        self.problem_text = QTextEdit()
        self.problem_text.setPlaceholderText(
            "Опишите, что не работает или какая ошибка возникает."
        )
        self.problem_text.setMaximumHeight(150)
        send_layout.addWidget(self.problem_text)

        # Поле "Telegram для связи"
        tg_header = QLabel("Telegram для связи (необязательно):")
        tg_header.setProperty("tone", "primary")
        tg_header.setStyleSheet("font-size: 12px; font-weight: 600;")
        send_layout.addWidget(tg_header)

        self.tg_contact = QLineEdit()
        self.tg_contact.setPlaceholderText("@username или ссылка на профиль")
        send_layout.addWidget(self.tg_contact)

        # Информация
        info_container = QWidget()
        info_layout = QHBoxLayout(info_container)
        info_layout.setContentsMargins(0, 8, 0, 8)

        info_icon = QLabel()
        self._info_icon_label = info_icon
        info_layout.addWidget(info_icon)

        info_text = QLabel(
            "Ваши данные будут отправлены только в канал техподдержки.\n"
            "Лог файл поможет разработчикам найти и исправить проблему."
        )
        info_text.setProperty("tone", "faint")
        info_text.setStyleSheet("font-size: 11px;")
        info_text.setWordWrap(True)
        info_layout.addWidget(info_text, 1)

        send_layout.addWidget(info_container)

        # Кнопка отправки
        buttons_row = QHBoxLayout()

        self.send_log_btn = ActionButton("Отправить лог", "fa5s.paper-plane")
        self.send_log_btn.clicked.connect(self._do_send_log)
        buttons_row.addWidget(self.send_log_btn)

        buttons_row.addStretch()

        # Статус отправки
        self.send_status_label = QLabel()
        buttons_row.addWidget(self.send_status_label)

        send_layout.addLayout(buttons_row)

        send_card.add_layout(send_layout)
        parent_layout.addWidget(send_card)

        # Растяжка чтобы форма была вверху
        parent_layout.addStretch()

        # Send tab is lazily built; apply current theme now.
        self._apply_theme(force=True)

    def _is_orchestra_mode(self) -> bool:
        """Проверяет, активен ли режим оркестратора"""
        try:
            from strategy_menu import get_strategy_launch_method
            return get_strategy_launch_method() == "orchestra"
        except Exception:
            return False

    def _get_orchestra_log_path(self) -> str:
        """
        Возвращает путь к логу оркестратора.

        Приоритет:
        1. Текущий активный лог (если оркестратор запущен)
        2. Последний сохранённый лог из истории
        """
        try:
            app = QApplication.instance()
            if app and hasattr(app, 'activeWindow'):
                main_window = app.activeWindow()
                if main_window and hasattr(main_window, 'orchestra_runner') and main_window.orchestra_runner:
                    runner = main_window.orchestra_runner

                    # 1. Пробуем текущий активный лог
                    if runner.current_log_id and runner.debug_log_path:
                        if os.path.exists(runner.debug_log_path):
                            return runner.debug_log_path

                    # 2. Если текущего нет - берём последний из истории
                    logs = runner.get_log_history()
                    if logs:
                        # Логи отсортированы по дате (новые первые)
                        latest_log = logs[0]
                        log_path = os.path.join(LOGS_FOLDER, latest_log['filename'])
                        if os.path.exists(log_path):
                            return log_path

        except Exception as e:
            log(f"Ошибка получения пути лога оркестратора: {e}", "DEBUG")

        # 3. Fallback: ищем любой orchestra_*.log в папке логов
        try:
            import glob as glob_module
            pattern = os.path.join(LOGS_FOLDER, "orchestra_*.log")
            log(f"Поиск лога оркестратора (fallback): {pattern}", "DEBUG")
            files = sorted(glob_module.glob(pattern), key=os.path.getmtime, reverse=True)
            log(f"Найдено файлов: {len(files)}", "DEBUG")
            if files:
                log(f"Найден лог оркестратора (fallback): {os.path.basename(files[0])}", "DEBUG")
                return files[0]
        except Exception as e:
            log(f"Ошибка fallback поиска лога: {e}", "DEBUG")

        log("Лог оркестратора не найден для отправки", "WARNING")
        return None

    def _update_orchestra_indicator(self):
        """Обновляет видимость индикатора режима оркестратора"""
        is_orchestra = self._is_orchestra_mode()
        self.orchestra_mode_container.setVisible(is_orchestra)

    def _do_send_log(self):
        """Отправляет лог в Telegram (из вкладки отправки)"""
        import time
        import platform

        try:
            settings = QSettings("Zapret2", "GUI")
            now = time.time()
            interval = 1 * 60  # 1 минута

            # Проверяем интервал
            last = settings.value("last_full_log_send", 0.0, type=float)

            if now - last < interval:
                remaining = int((interval - (now - last)) // 60) + 1
                QMessageBox.information(self, "Отправка логов",
                    f"Лог отправлялся недавно.\n"
                    f"Следующая отправка возможна через {remaining} мин.")
                return

            # Проверяем доступность панели поддержки и показываем реальную причину
            from tgram.tg_log_bot import get_bot_connection_info

            bot_ok, bot_error, bot_kind = get_bot_connection_info()
            if not bot_ok:
                details = (bot_error or "Неизвестная ошибка").strip()
                if len(details) > 250:
                    details = details[:250] + "…"
                title = "Панель не настроена" if bot_kind == "config" else "Панель недоступна"
                hint = (
                    "Проверьте настройки ZapretHub (бот/авторизация) или обратитесь к разработчику."
                    if bot_kind == "config"
                    else "Если доступ к панели заблокирован — включите VPN/DPI bypass и повторите."
                )
                QMessageBox.warning(self, title,
                    "Не удалось подключиться к панели поддержки для отправки логов.\n\n"
                    f"Причина: {details}\n\n"
                    f"{hint}"
                )
                return

            # Получаем данные из формы
            problem = self.problem_text.toPlainText().strip()
            telegram = self.tg_contact.text().strip()

            # Запоминаем время отправки
            settings.setValue("last_full_log_send", now)

            # Подготовка к отправке
            from tgram.tg_log_full import TgSendWorker
            from tgram.tg_log_delta import get_client_id
            from config.build_info import APP_VERSION

            # Используем текущий лог файл
            LOG_PATH = global_logger.log_file if hasattr(global_logger, 'log_file') else None

            if not LOG_PATH or not os.path.exists(LOG_PATH):
                QMessageBox.warning(self, "Ошибка", "Файл лога не найден")
                return

            # Проверяем режим оркестратора
            is_orchestra = self._is_orchestra_mode()
            orchestra_log_path = self._get_orchestra_log_path() if is_orchestra else None

            # Формируем подпись
            log_filename = os.path.basename(LOG_PATH)

            caption = f"📋 Ручная отправка лога\n"
            if is_orchestra:
                caption += f"🧠 Режим: Оркестратор\n"
            caption += f"📁 Файл: {log_filename}\n"
            caption += f"Zapret2 v{APP_VERSION}\n"
            caption += f"ID: {get_client_id()}\n"
            caption += f"Host: {platform.node()}\n"
            caption += f"Time: {time.strftime('%d.%m.%Y %H:%M:%S')}\n"

            if problem:
                caption += f"\n🔴 Проблема:\n{problem}\n"

            if telegram:
                caption += f"\n📱 Telegram: {telegram}\n"

            # Авторизация на отправку (одноразовый код, без сохранения токена)
            try:
                from tgram.tg_log_bot import request_upload_code

                ok, code, bot_username, bot_link = request_upload_code()
                if not ok or not code:
                    QMessageBox.warning(self, "Авторизация",
                        "Не удалось запросить код авторизации у ZapretHub.\n"
                        "Проверьте доступность панели и повторите.")
                    return

                bot_line = f"@{bot_username}" if bot_username else "бот поддержки"
                QMessageBox.information(self, "Авторизация поддержки",
                    "Для отправки логов нужно подтвердить код в Telegram.\n\n"
                    f"1) Откройте {bot_line}\n"
                    f"2) Отправьте ему код: {code}\n"
                    "3) Вернитесь сюда — отправка продолжится автоматически.\n\n"
                    f"Ссылка: {bot_link}"
                )

                self.send_log_btn.setEnabled(False)
                self.send_status_label.setText("🔐 Ожидание подтверждения кода...")

                self._auth_thread = QThread(self)
                self._auth_worker = SupportAuthWorker(code)
                self._auth_worker.moveToThread(self._auth_thread)
                self._auth_thread.started.connect(self._auth_worker.run)

                def _on_auth_done(auth_ok: bool, err_msg: str):
                    try:
                        self._auth_worker.deleteLater()
                    except Exception:
                        pass

                    if not auth_ok:
                        self.send_log_btn.setEnabled(True)
                        self.send_status_label.setText("❌ Код не подтверждён")
                        QMessageBox.warning(self, "Авторизация",
                            "Не удалось подтвердить код.\n\n"
                            f"Причина: {err_msg or 'Неизвестная ошибка'}")
                        return

                    # Continue sending with the existing prepared payload
                    if is_orchestra and orchestra_log_path:
                        self.send_status_label.setText("📤 Отправка 2 файлов (оркестратор)...")
                        self._send_orchestra_logs(LOG_PATH, orchestra_log_path, caption, problem, telegram, auth_code=code)
                    else:
                        self.send_status_label.setText("📤 Отправка лога...")
                        self._send_single_log(LOG_PATH, caption, auth_code=code)

                self._auth_worker.finished.connect(_on_auth_done)
                self._auth_worker.finished.connect(self._auth_thread.quit)
                self._auth_worker.finished.connect(self._auth_worker.deleteLater)
                self._auth_thread.finished.connect(self._auth_thread.deleteLater)
                self._auth_thread.start()
                return

            except Exception as e:
                QMessageBox.warning(self, "Авторизация", f"Ошибка авторизации: {e}")
                return

            # If we ever add a dev token path (Bearer), sending could continue here.

        except Exception as e:
            log(f"Ошибка отправки лога: {e}", "ERROR")
            self.send_log_btn.setEnabled(True)
            self.send_status_label.setText("❌ Ошибка")
            QMessageBox.warning(self, "Ошибка", f"Не удалось отправить лог:\n{e}")

    def _send_single_log(self, log_path: str, caption: str, auth_code: str | None = None):
        """Отправляет один файл лога"""
        from tgram.tg_log_full import TgSendWorker

        self._send_thread = QThread(self)
        self._send_worker = TgSendWorker(log_path, caption, use_log_bot=True, auth_code=auth_code)
        self._send_worker.moveToThread(self._send_thread)
        self._send_thread.started.connect(self._send_worker.run)

        def _on_done(ok: bool, extra_wait: float, error_msg: str = ""):
            self.send_log_btn.setEnabled(True)

            if ok:
                self.send_status_label.setText("✅ Лог отправлен!")
                self.send_status_label.setStyleSheet("color: #4ade80; font-size: 11px;")
                self.problem_text.clear()
                self.tg_contact.clear()
            else:
                short_error = error_msg[:50] + "..." if error_msg and len(error_msg) > 50 else error_msg
                self.send_status_label.setText(f"❌ {short_error or 'Ошибка отправки'}")
                self.send_status_label.setStyleSheet("color: #f87171; font-size: 11px;")
                if extra_wait > 0:
                    QMessageBox.warning(self, "Слишком часто",
                        f"Слишком частые запросы.\n"
                        f"Повторите через {int(extra_wait/60)} минут.")
                elif error_msg:
                    QMessageBox.warning(self, "Ошибка отправки",
                        f"Не удалось отправить лог.\n\n"
                        f"Причина: {error_msg}")
                else:
                    QMessageBox.warning(self, "Ошибка",
                        "Не удалось отправить лог.\n\n"
                        "Проверьте подключение к интернету.")

            self._send_worker.deleteLater()
            self._send_thread.quit()
            self._send_thread.wait()

        self._send_worker.finished.connect(_on_done)
        self._send_thread.start()

    def _send_orchestra_logs(self, app_log_path: str, orchestra_log_path: str, caption: str, problem: str, telegram: str, auth_code: str | None = None):
        """Отправляет два файла: лог приложения и лог оркестратора в топик 43927"""
        import time
        import platform
        from tgram.tg_log_full import TgSendWorker
        from tgram.tg_log_delta import get_client_id
        from config.build_info import APP_VERSION

        # Топик для логов оркестратора
        ORCHESTRA_TOPIC_ID = 43927

        # Счётчик успешных отправок
        self._orchestra_send_success = 0
        self._orchestra_send_total = 2
        self._orchestra_errors = []

        def _check_complete():
            """Проверяет завершение отправки всех файлов"""
            if self._orchestra_send_success + len(self._orchestra_errors) >= self._orchestra_send_total:
                self.send_log_btn.setEnabled(True)

                if self._orchestra_send_success == self._orchestra_send_total:
                    self.send_status_label.setText("✅ 2 файла отправлены!")
                    self.send_status_label.setStyleSheet("color: #4ade80; font-size: 11px;")
                    self.problem_text.clear()
                    self.tg_contact.clear()
                elif self._orchestra_send_success > 0:
                    self.send_status_label.setText(f"⚠️ Отправлено {self._orchestra_send_success} из 2")
                    self.send_status_label.setStyleSheet("color: #fbbf24; font-size: 11px;")
                else:
                    self.send_status_label.setText("❌ Ошибка отправки")
                    self.send_status_label.setStyleSheet("color: #f87171; font-size: 11px;")
                    if self._orchestra_errors:
                        QMessageBox.warning(self, "Ошибка отправки",
                            f"Не удалось отправить логи.\n\n"
                            f"Ошибки:\n" + "\n".join(self._orchestra_errors[:3]))

        # 1. Отправляем лог оркестратора (сырой debug) в топик 43927
        orchestra_filename = os.path.basename(orchestra_log_path)
        orchestra_caption = f"🧠 Лог оркестратора (debug)\n"
        orchestra_caption += f"📁 Файл: {orchestra_filename}\n"
        orchestra_caption += f"Zapret2 v{APP_VERSION}\n"
        orchestra_caption += f"ID: {get_client_id()}\n"
        orchestra_caption += f"Host: {platform.node()}\n"
        orchestra_caption += f"Time: {time.strftime('%d.%m.%Y %H:%M:%S')}\n"
        if problem:
            orchestra_caption += f"\n🔴 Проблема:\n{problem}\n"
        if telegram:
            orchestra_caption += f"\n📱 Telegram: {telegram}\n"

        self._send_thread1 = QThread(self)
        self._send_worker1 = TgSendWorker(orchestra_log_path, orchestra_caption, use_log_bot=True, topic_id=ORCHESTRA_TOPIC_ID, auth_code=auth_code)
        self._send_worker1.moveToThread(self._send_thread1)
        self._send_thread1.started.connect(self._send_worker1.run)

        def _on_orchestra_done(ok: bool, extra_wait: float, error_msg: str = ""):
            if ok:
                self._orchestra_send_success += 1
            else:
                self._orchestra_errors.append(f"Лог оркестратора: {error_msg or 'неизвестная ошибка'}")

            self._send_worker1.deleteLater()
            self._send_thread1.quit()
            self._send_thread1.wait()
            _check_complete()

        self._send_worker1.finished.connect(_on_orchestra_done)
        self._send_thread1.start()

        # 2. Отправляем лог приложения в тот же топик 43927
        app_filename = os.path.basename(app_log_path)
        app_caption = f"📋 Лог приложения\n"
        app_caption += f"🧠 Режим: Оркестратор (файл 2/2)\n"
        app_caption += f"📁 Файл: {app_filename}\n"
        app_caption += f"Zapret2 v{APP_VERSION}\n"
        app_caption += f"ID: {get_client_id()}\n"
        app_caption += f"Host: {platform.node()}\n"
        app_caption += f"Time: {time.strftime('%d.%m.%Y %H:%M:%S')}\n"
        if problem:
            app_caption += f"\n🔴 Проблема:\n{problem}\n"
        if telegram:
            app_caption += f"\n📱 Telegram: {telegram}\n"

        self._send_thread2 = QThread(self)
        self._send_worker2 = TgSendWorker(app_log_path, app_caption, use_log_bot=True, topic_id=ORCHESTRA_TOPIC_ID, auth_code=auth_code)
        self._send_worker2.moveToThread(self._send_thread2)
        self._send_thread2.started.connect(self._send_worker2.run)

        def _on_app_done(ok: bool, extra_wait: float, error_msg: str = ""):
            if ok:
                self._orchestra_send_success += 1
            else:
                self._orchestra_errors.append(f"Лог приложения: {error_msg or 'неизвестная ошибка'}")

            self._send_worker2.deleteLater()
            self._send_thread2.quit()
            self._send_thread2.wait()
            _check_complete()

        self._send_worker2.finished.connect(_on_app_done)
        self._send_thread2.start()
        
    def showEvent(self, event):
        """При показе страницы запускаем мониторинг"""
        super().showEvent(event)

        if not event.spontaneous() and not self._ui_built:
            self._ensure_ui_built()

        if self._theme_apply_pending_when_hidden:
            self._theme_apply_pending_when_hidden = False
            self._schedule_theme_apply()

        # Spontaneous showEvent = система восстановила окно (из трея/свёрнутого).
        # Не перезапускаем workers/таймеры при простом восстановлении окна.
        if event.spontaneous():
            return
        if not self._logs_tab_initialized:
            self._logs_tab_initialized = True
            # Делаем тяжелые операции после первого показа страницы, чтобы UI не "подвисал" при переходе.
            QTimer.singleShot(0, lambda: self._refresh_logs_list(run_cleanup=False))
            QTimer.singleShot(0, self._update_stats)
        self._start_tail_worker()
        self._start_winws_output_worker()
        # Таймер для проверки статуса каждые 2 секунды
        self._winws_status_timer.start(2000)

    def hideEvent(self, event):
        """При скрытии страницы останавливаем мониторинг"""
        super().hideEvent(event)
        self._stop_tail_worker()
        self._stop_winws_output_worker()
        self._winws_status_timer.stop()
        
    def _refresh_logs_list(self, *, run_cleanup: bool = True):
        """Обновляет список доступных лог-файлов"""
        # Запускаем анимацию вращения
        self.refresh_btn.setIcon(self._refresh_icon_spinning)
        self._refresh_spin_active = True
        self._refresh_spin_animation.start()
        
        self.log_combo.blockSignals(True)
        self.log_combo.clear()
        
        try:
            if run_cleanup:
                # Очищаем старые логи перед обновлением списка
                deleted, errors, total = cleanup_old_logs(LOGS_FOLDER, MAX_LOG_FILES)
                if deleted > 0:
                    log(f"🗑️ Удалено старых логов: {deleted} из {total}", "INFO")
                if errors:
                    log(f"⚠️ Ошибки при удалении логов: {errors[:3]}", "DEBUG")
            
            # Получаем оба формата логов
            log_files = []
            log_files.extend(glob.glob(os.path.join(LOGS_FOLDER, "zapret_log_*.txt")))
            log_files.extend(glob.glob(os.path.join(LOGS_FOLDER, "zapret_[0-9]*.log")))
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
        self._refresh_spin_active = False
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
            # Initial history: limit to recent tail to keep the page snappy on huge logs.
            self._worker = LogTailWorker(self.current_log_file, initial_chunk_chars=65536, initial_max_bytes=1024 * 1024)
            self._worker.moveToThread(self._thread)

            self._thread.started.connect(self._worker.run)
            self._worker.new_lines.connect(self._append_text)
            self._worker.finished.connect(self._thread.quit)
            self._worker.finished.connect(self._worker.deleteLater)
            self._thread.finished.connect(self._on_tail_thread_finished)
            self._thread.finished.connect(self._thread.deleteLater)

            self._thread.start()
        except Exception as e:
            log(f"Ошибка запуска log tail worker: {e}", "ERROR")

    def _on_tail_thread_finished(self):
        """Очищает ссылки на thread/worker после завершения, чтобы не дергать удалённые Qt-объекты."""
        self._thread = None
        self._worker = None
            
    def _stop_tail_worker(self, blocking: bool = False):
        """Останавливает worker (неблокирующий по умолчанию)"""
        worker = getattr(self, "_worker", None)
        thread = getattr(self, "_thread", None)

        if worker:
            try:
                worker.stop()
            except RuntimeError:
                # Qt-объект уже удалён
                self._worker = None
                worker = None

        if not thread:
            return

        try:
            running = bool(thread.isRunning())
        except RuntimeError:
            # Qt-объект уже удалён
            self._thread = None
            return

        if not running:
            return

        thread.quit()
        if not blocking:
            return

        # Блокирующий режим только при закрытии приложения
        if not thread.wait(2000):
            log("⚠ Log tail worker не завершился, принудительно завершаем", "WARNING")
            try:
                thread.terminate()
                thread.wait(500)
            except Exception:
                pass

    def _start_winws_output_worker(self):
        """Запускает worker для чтения вывода winws"""
        self._stop_winws_output_worker()

        # Получаем текущий runner и процесс
        runner = get_current_runner()
        if not runner:
            self._set_winws_status("neutral", "Процесс не запущен")
            return

        process = runner.get_process()
        if not process:
            self._set_winws_status("neutral", "Процесс не запущен")
            return

        # Обновляем статус
        strategy_info = runner.get_current_strategy_info()
        strategy_name = strategy_info.get('name', 'winws')
        # Обрезаем длинные названия стратегий
        if len(strategy_name) > 35:
            strategy_name = strategy_name[:32] + "..."
        pid = strategy_info.get('pid', '?')
        self._set_winws_status("running", f"PID: {pid} | {strategy_name}")

        try:
            self._winws_thread = QThread(self)
            self._winws_worker = WinwsOutputWorker()
            self._winws_worker.set_process(process)
            self._winws_worker.moveToThread(self._winws_thread)

            self._winws_thread.started.connect(self._winws_worker.run)
            self._winws_worker.new_output.connect(self._append_winws_output)
            self._winws_worker.process_ended.connect(self._on_winws_process_ended)
            self._winws_worker.finished.connect(self._winws_thread.quit)

            self._winws_thread.start()
        except Exception as e:
            log(f"Ошибка запуска winws output worker: {e}", "ERROR")

    def _stop_winws_output_worker(self, blocking: bool = False):
        """Останавливает worker чтения вывода winws (неблокирующий по умолчанию)"""
        try:
            if self._winws_worker:
                self._winws_worker.stop()
            if self._winws_thread and self._winws_thread.isRunning():
                self._winws_thread.quit()
                if blocking:
                    # Блокирующий режим только при закрытии приложения
                    if not self._winws_thread.wait(2000):
                        log("⚠ Winws output worker не завершился, принудительно завершаем", "WARNING")
                        try:
                            self._winws_thread.terminate()
                            self._winws_thread.wait(500)
                        except:
                            pass
                # Неблокирующий режим - поток остановится сам
        except Exception as e:
            log(f"Ошибка остановки winws output worker: {e}", "DEBUG")

    def _append_winws_output(self, text: str, stream_type: str):
        """Добавляет вывод winws в текстовое поле"""
        self._winws_lines_count += 1

        # Экранируем HTML-символы
        safe_text = html.escape(text)

        # Форматируем текст в зависимости от потока
        if stream_type == 'stderr':
            # stderr показываем красным
            formatted = f'<span style="color: {self._winws_stderr_color};">{safe_text}</span>'
        else:
            # stdout показываем зелёным
            formatted = f'<span style="color: {self._winws_stdout_color};">{safe_text}</span>'

        self.winws_text.append(formatted)

        # Автопрокрутка
        scrollbar = self.winws_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _on_winws_process_ended(self, exit_code: int):
        """Обработчик завершения процесса winws"""
        if exit_code == 0:
            self._set_winws_status("neutral", f"Процесс завершён (код: {exit_code})")
        else:
            self._set_winws_status("error", f"Процесс завершён с ошибкой (код: {exit_code})")

    def _update_winws_status(self):
        """Периодически проверяет статус процесса winws"""
        runner = get_current_runner()

        # Проверяем есть ли запущенный процесс
        if runner and runner.is_running():
            # Если worker не работает, запускаем его
            if not self._winws_thread or not self._winws_thread.isRunning():
                self._start_winws_output_worker()
        else:
            # Процесс не запущен - обновляем статус если worker не работает
            if not self._winws_thread or not self._winws_thread.isRunning():
                self._set_winws_status("neutral", "Процесс не запущен")

    def _clear_winws_output(self):
        """Очищает поле вывода winws"""
        self.winws_text.clear()
        self._winws_lines_count = 0
        self.info_label.setText("🧹 Вывод winws очищен")

    def _append_text(self, text: str):
        """Добавляет текст в лог"""
        if not text:
            return

        # Быстро вставляем текст одним куском (append по строкам сильно тормозит на больших логах).
        try:
            scrollbar = self.log_text.verticalScrollBar()
            was_at_bottom = scrollbar.value() >= (scrollbar.maximum() - 2)
        except Exception:
            was_at_bottom = True

        try:
            self.log_text.setUpdatesEnabled(False)
            cursor = self.log_text.textCursor()
            cursor.movePosition(cursor.MoveOperation.End)
            cursor.insertText(text)
            self.log_text.setTextCursor(cursor)
        finally:
            try:
                self.log_text.setUpdatesEnabled(True)
            except Exception:
                pass

        # Проверяем на ошибки только по новым строкам
        try:
            for line in text.splitlines():
                clean_line = (line or "").rstrip()
                if not clean_line:
                    continue
                if self._error_pattern.search(clean_line) and not self._exclude_pattern.search(clean_line):
                    self._add_error(clean_line)
        except Exception:
            pass

        if was_at_bottom:
            try:
                scrollbar = self.log_text.verticalScrollBar()
                scrollbar.setValue(scrollbar.maximum())
            except Exception:
                pass
        
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
            # Считаем оба формата логов
            # Основные логи приложения
            app_logs = glob.glob(os.path.join(LOGS_FOLDER, "zapret_log_*.txt"))
            app_logs.extend(glob.glob(os.path.join(LOGS_FOLDER, "zapret_[0-9]*.log")))
            # Debug логи winws2
            debug_logs = glob.glob(os.path.join(LOGS_FOLDER, "zapret_winws2_debug_*.log"))

            all_files = app_logs + debug_logs
            total_size = sum(os.path.getsize(f) for f in all_files) / 1024 / 1024

            self.stats_label.setText(
                f"📊 Логи: {len(app_logs)} (макс {MAX_LOG_FILES}) | "
                f"🔧 Debug: {len(debug_logs)} (макс {MAX_DEBUG_LOG_FILES}) | "
                f"💾 Размер: {total_size:.2f} MB"
            )
        except Exception as e:
            self.stats_label.setText(f"Ошибка статистики: {e}")
            
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
        """Очистка при закрытии - блокирующий режим"""
        self._stop_tail_worker(blocking=True)
        self._stop_winws_output_worker(blocking=True)
