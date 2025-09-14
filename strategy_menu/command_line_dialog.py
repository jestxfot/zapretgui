"""
Диалог для отображения полной командной строки Zapret
"""

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                            QLabel, QMessageBox, QTextEdit, QApplication, QFileDialog)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QTextOption  # Добавили QTextOption
from datetime import datetime
import shlex
import os

from log import log
from config import WINWS_EXE


class CommandLineDialog(QDialog):
    """Диалог для показа и копирования полной командной строки"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_selector = parent
        self.command_line = None
        
        self.setWindowTitle("📋 Полная командная строка Zapret")
        self.setFixedSize(500, 500)
        self.setModal(True)
        
        self._init_ui()
        self._generate_command()
        
    def _init_ui(self):
        """Инициализирует интерфейс"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Заголовок
        title_label = QLabel("Полная командная строка для запуска winws.exe:")
        title_label.setStyleSheet("font-weight: bold; font-size: 10pt; color: #2196F3; margin-bottom: 5px;")
        layout.addWidget(title_label)
        
        # Информационная панель
        self.info_label = QLabel("Генерация командной строки...")
        self.info_label.setStyleSheet("color: #888; font-size: 9pt; margin-bottom: 10px;")
        layout.addWidget(self.info_label)
        
        # Текстовое поле с командной строкой
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setFont(QFont("Consolas", 9))
        self.text_edit.setStyleSheet("""
            QTextEdit {
                background: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #444;
                border-radius: 5px;
                padding: 10px;
                selection-background-color: #2196F3;
            }
            QScrollBar:vertical {
                width: 10px;
                background: #2a2a2a;
            }
            QScrollBar::handle:vertical {
                background: #555;
                border-radius: 5px;
            }
        """)
        self.text_edit.setWordWrapMode(QTextOption.WrapMode.WrapAnywhere)
        layout.addWidget(self.text_edit)
        
        # Кнопки
        self._create_buttons(layout)
        
        # Подсказка
        hint_label = QLabel("💡 Используйте её для запуска Zapret вручную из cmd")
        hint_label.setStyleSheet("color: #666; font-style: italic; margin-top: 5px;")
        hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint_label)
        
    def _create_buttons(self, layout):
        """Создает кнопки управления"""
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)
        
        # Кнопка копирования
        self.copy_button = QPushButton("📋 Копировать в буфер")
        self.copy_button.setMinimumHeight(35)
        self.copy_button.setEnabled(False)
        self.copy_button.setStyleSheet("""
            QPushButton {
                background: #2196F3;
                color: white;
                border-radius: 4px;
                padding: 8px 15px;
                font-weight: bold;
                font-size: 10pt;
            }
            QPushButton:hover:enabled {
                background: #1976D2;
            }
            QPushButton:pressed {
                background: #1565C0;
            }
            QPushButton:disabled {
                background: #666;
                color: #aaa;
            }
        """)
        self.copy_button.clicked.connect(self._copy_to_clipboard)
        buttons_layout.addWidget(self.copy_button)
        
        # Кнопка сохранения в файл
        self.save_button = QPushButton("💾 Сохранить в файл")
        self.save_button.setMinimumHeight(35)
        self.save_button.setEnabled(False)
        self.save_button.setStyleSheet("""
            QPushButton {
                background: #4CAF50;
                color: white;
                border-radius: 4px;
                padding: 8px 15px;
                font-weight: bold;
                font-size: 10pt;
            }
            QPushButton:hover:enabled {
                background: #45a049;
            }
            QPushButton:disabled {
                background: #666;
                color: #aaa;
            }
        """)
        self.save_button.clicked.connect(self._save_to_file)
        buttons_layout.addWidget(self.save_button)
        
        # Кнопка закрытия
        close_button = QPushButton("Закрыть")
        close_button.setMinimumHeight(35)
        close_button.setStyleSheet("""
            QPushButton {
                background: #444;
                color: white;
                border-radius: 4px;
                padding: 8px 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #555;
            }
        """)
        close_button.clicked.connect(self.accept)
        buttons_layout.addWidget(close_button)
        
        layout.addLayout(buttons_layout)
        
    def _generate_command(self):
        """Генерирует командную строку"""
        try:
            if not self.parent_selector:
                self._show_error("Нет родительского селектора")
                return
                
            if self.parent_selector.is_direct_mode:
                self._generate_direct_mode_command()
            else:
                self._generate_bat_mode_command()
                
        except Exception as e:
            log(f"Ошибка генерации командной строки: {e}", "ERROR")
            self._show_error(f"Ошибка генерации: {e}")
            
    def _generate_direct_mode_command(self):
        """Генерирует команду для Direct режима"""
        from strategy_menu.strategy_lists_separated import combine_strategies
        from strategy_menu.strategy_runner import (
            apply_allzone_replacement, 
            apply_game_filter_parameter, 
            apply_wssize_parameter
        )
        
        if not self.parent_selector.category_selections:
            self._show_error("Нет выбранных стратегий")
            return
            
        # Комбинируем стратегии
        combined = combine_strategies(
            self.parent_selector.category_selections.get('youtube'),
            self.parent_selector.category_selections.get('youtube_udp'),
            self.parent_selector.category_selections.get('googlevideo_tcp'),
            self.parent_selector.category_selections.get('discord'),
            self.parent_selector.category_selections.get('discord_voice_udp'),
            self.parent_selector.category_selections.get('rutracker_tcp'),
            self.parent_selector.category_selections.get('ntcparty_tcp'),
            self.parent_selector.category_selections.get('twitch_tcp'),
            self.parent_selector.category_selections.get('phasmophobia_udp'),
            self.parent_selector.category_selections.get('other'),
            self.parent_selector.category_selections.get('hostlist_80port'),
            self.parent_selector.category_selections.get('ipset'),
            self.parent_selector.category_selections.get('ipset_udp')
        )
        
        # Разбираем аргументы
        args = shlex.split(combined['args'])
        
        # Применяем модификаторы
        work_dir = os.path.dirname(os.path.dirname(WINWS_EXE))
        lists_dir = os.path.join(work_dir, "lists")
        
        args = apply_allzone_replacement(args)
        args = apply_game_filter_parameter(args, lists_dir)
        args = apply_wssize_parameter(args)
        
        # Разрешаем пути к файлам
        resolved_args = self._resolve_file_paths(args, work_dir)
        
        # Формируем полную команду
        cmd_parts = [WINWS_EXE] + resolved_args
        
        # Правильно экранируем аргументы с пробелами
        full_cmd_parts = []
        for arg in cmd_parts:
            if ' ' in arg and not (arg.startswith('"') and arg.endswith('"')):
                full_cmd_parts.append(f'"{arg}"')
            else:
                full_cmd_parts.append(arg)
        
        self.command_line = ' '.join(full_cmd_parts)
        
        # Обновляем UI
        self.text_edit.setPlainText(self.command_line)
        self.info_label.setText(
            f"Длина команды: {len(self.command_line)} символов | "
            f"Аргументов: {len(resolved_args)} | "
            f"Стратегия: {combined['description']}"
        )
        
        # Включаем кнопки
        self.copy_button.setEnabled(True)
        self.save_button.setEnabled(True)
        
    def _generate_bat_mode_command(self):
        """Генерирует команду для BAT режима"""
        # Для BAT режима показываем информационное сообщение
        info_text = """BAT режим: командная строка генерируется .bat файлом

В BAT режиме полная командная строка формируется внутри .bat файла выбранной стратегии.

Чтобы увидеть полную командную строку:
1. Откройте .bat файл стратегии в текстовом редакторе
2. Найдите строку начинающуюся с "%WINWS1%"
3. Или переключитесь на "Прямой запуск" в настройках

Путь к .bat файлам: strategies\\"""
        
        self.text_edit.setPlainText(info_text)
        self.info_label.setText("BAT режим - команда внутри .bat файла")
        
    def _resolve_file_paths(self, args, work_dir):
        """Разрешает относительные пути к файлам"""
        resolved = []
        lists_dir = os.path.join(work_dir, "lists")
        bin_dir = os.path.join(work_dir, "bin")
        
        for arg in args:
            if arg.startswith("--hostlist=") or arg.startswith("--ipset="):
                prefix, filename = arg.split("=", 1)
                filename = filename.strip('"')
                if not os.path.isabs(filename):
                    full_path = os.path.join(lists_dir, filename)
                    resolved.append(f'{prefix}={full_path}')
                else:
                    resolved.append(arg)
                    
            elif any(arg.startswith(p) for p in [
                "--dpi-desync-fake-tls=", "--dpi-desync-fake-quic=",
                "--dpi-desync-fake-syndata=", "--dpi-desync-fake-unknown-udp="
            ]):
                prefix, filename = arg.split("=", 1)
                if not filename.startswith("0x") and not filename.startswith("!") and not os.path.isabs(filename):
                    filename = filename.strip('"')
                    full_path = os.path.join(bin_dir, filename)
                    resolved.append(f'{prefix}={full_path}')
                else:
                    resolved.append(arg)
            else:
                resolved.append(arg)
        
        return resolved
        
    def _show_error(self, message):
        """Показывает сообщение об ошибке"""
        self.text_edit.setPlainText(f"❌ Ошибка: {message}")
        self.info_label.setText("Ошибка генерации командной строки")
        self.text_edit.setStyleSheet(self.text_edit.styleSheet() + """
            QTextEdit {
                color: #ff6666;
            }
        """)
        
    def _copy_to_clipboard(self):
        """Копирует командную строку в буфер обмена"""
        if not self.command_line:
            return
            
        clipboard = QApplication.clipboard()
        clipboard.setText(self.command_line)
        
        # Показываем уведомление
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setWindowTitle("Скопировано")
        msg.setText("Командная строка скопирована в буфер обмена!")
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.exec()
        
        log("Командная строка скопирована в буфер обмена", "INFO")
        
    def _save_to_file(self):
        """Сохраняет командную строку в файл"""
        if not self.command_line:
            return
            
        # Предлагаем имя файла
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        suggested_name = f"zapret_command_{timestamp}.txt"
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить командную строку",
            suggested_name,
            "Текстовые файлы (*.txt);;Командные файлы (*.cmd);;Все файлы (*.*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(f"REM Zapret командная строка\n")
                    f.write(f"REM Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    
                    if self.parent_selector.is_direct_mode:
                        strategy_name = "Комбинированная (Direct mode)"
                    else:
                        strategy_name = self.parent_selector.selected_strategy_name or "Неизвестная"
                    
                    f.write(f"REM Стратегия: {strategy_name}\n\n")
                    f.write(self.command_line)
                
                QMessageBox.information(self, "Сохранено", 
                                      f"Командная строка сохранена в:\n{file_path}")
                log(f"Командная строка сохранена в {file_path}", "INFO")
                
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", 
                                   f"Не удалось сохранить файл:\n{e}")
                log(f"Ошибка сохранения командной строки: {e}", "ERROR")


def show_command_line_dialog(parent_selector):
    """Вспомогательная функция для показа диалога"""
    dialog = CommandLineDialog(parent_selector)
    dialog.exec()