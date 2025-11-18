# ui/help_dialog.py
import os
import webbrowser
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QFrame, QSpacerItem, QSizePolicy
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon, QFont
import qtawesome as qta

from config import CHANNEL
from ui.theme import RippleButton, BUTTON_STYLE, COMMON_STYLE
from utils import run_hidden
from log import log


class HelpDialog(QDialog):
    """Диалог справки с кнопками поддержки и документации"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Справка Zapret")
        self.setModal(True)
        self.setMinimumSize(450, 350)
        
        # Получаем информацию о текущей теме
        self.is_dark_theme = False
        self.is_pure_black = False
        self.is_amoled = False
        
        if parent and hasattr(parent, 'theme_manager'):
            theme_manager = parent.theme_manager
            current_theme = theme_manager.current_theme
            
            # Проверяем тип темы
            self.is_dark_theme = "Темная" in current_theme or "РКН" in current_theme
            self.is_pure_black = theme_manager._is_pure_black_theme(current_theme)
            self.is_amoled = theme_manager._is_amoled_theme(current_theme)
        
        # Применяем базовый стиль диалога в зависимости от темы
        self._apply_dialog_style()
        
        # Основной layout
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Заголовок
        title_label = QLabel("📚 Центр помощи Zapret")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet(self._get_title_style())
        layout.addWidget(title_label)
        
        # Разделитель
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet(self._get_line_style())
        layout.addWidget(line)
        
        # Описание
        description = QLabel(
            "Здесь вы можете получить помощь по использованию программы,\n"
            "обратиться в поддержку или изучить документацию."
        )
        description.setAlignment(Qt.AlignmentFlag.AlignCenter)
        description.setWordWrap(True)
        description.setStyleSheet(self._get_description_style())
        layout.addWidget(description)
        
        # Спейсер
        layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
        
        # === СЕКЦИЯ ДОКУМЕНТАЦИИ ===
        doc_section_label = QLabel("📖 Документация")
        doc_section_label.setStyleSheet(self._get_section_label_style())
        layout.addWidget(doc_section_label)
        
        # Кнопка открытия локальной папки help
        self.help_folder_btn = RippleButton(" Открыть папку с инструкциями", self, "0, 119, 255")
        self.help_folder_btn.setIcon(qta.icon('fa5s.folder-open', color='white'))
        self.help_folder_btn.setIconSize(QSize(18, 18))
        self.help_folder_btn.setStyleSheet(self._get_button_style("0, 119, 255"))
        self.help_folder_btn.setMinimumHeight(45)
        self.help_folder_btn.clicked.connect(self._open_help_folder)
        self.help_folder_btn.setToolTip(
            "Открыть локальную папку с инструкциями и руководствами"
        )
        layout.addWidget(self.help_folder_btn)
        
        # Кнопка Wiki (GitHub)
        self.wiki_btn = RippleButton(" Открыть Wiki на GitHub", self, "38, 38, 38")
        self.wiki_btn.setIcon(qta.icon('fa5b.github', color='white'))
        self.wiki_btn.setIconSize(QSize(18, 18))
        self.wiki_btn.setStyleSheet(self._get_button_style("38, 38, 38"))
        self.wiki_btn.setMinimumHeight(45)
        self.wiki_btn.clicked.connect(self._open_wiki)
        self.wiki_btn.setToolTip(
            "Открыть полную документацию на GitHub"
        )
        layout.addWidget(self.wiki_btn)
        
        # Спейсер
        layout.addSpacerItem(QSpacerItem(20, 15, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed))
        
        # === СЕКЦИЯ ПОДДЕРЖКИ ===
        support_section_label = QLabel("💬 Поддержка")
        support_section_label.setStyleSheet(self._get_section_label_style())
        layout.addWidget(support_section_label)
        
        # Кнопка Telegram канала
        self.telegram_btn = RippleButton(" Telegram канал поддержки", self, "0, 136, 204")
        self.telegram_btn.setIcon(qta.icon('fa5b.telegram-plane', color='white'))
        self.telegram_btn.setIconSize(QSize(18, 18))
        self.telegram_btn.setStyleSheet(self._get_button_style("0, 136, 204"))
        self.telegram_btn.setMinimumHeight(45)
        self.telegram_btn.clicked.connect(self._open_telegram)
        self.telegram_btn.setToolTip(
            "Перейти в официальный Telegram канал для получения помощи"
        )
        layout.addWidget(self.telegram_btn)
        
        # Кнопка Discord
        self.discord_btn = RippleButton(" Discord сервер", self, "88, 101, 242")
        self.discord_btn.setIcon(qta.icon('fa5b.discord', color='white'))
        self.discord_btn.setIconSize(QSize(18, 18))
        self.discord_btn.setStyleSheet(self._get_button_style("88, 101, 242"))
        self.discord_btn.setMinimumHeight(45)
        self.discord_btn.clicked.connect(self._open_discord)
        self.discord_btn.setToolTip(
            "Присоединиться к Discord серверу для общения с сообществом"
        )
        layout.addWidget(self.discord_btn)
        
        # Спейсер
        layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
        
        # Разделитель перед кнопкой закрытия
        line2 = QFrame()
        line2.setFrameShape(QFrame.Shape.HLine)
        line2.setStyleSheet(self._get_line_style())
        layout.addWidget(line2)
        
        # Кнопка закрытия
        close_btn = QPushButton("Закрыть")
        close_btn.setStyleSheet(self._get_close_button_style())
        close_btn.clicked.connect(self.close)
        
        close_layout = QHBoxLayout()
        close_layout.addStretch()
        close_layout.addWidget(close_btn)
        close_layout.addStretch()
        layout.addLayout(close_layout)
    
    def _apply_dialog_style(self):
        """Применяет стиль к диалогу в зависимости от темы"""
        if self.is_pure_black:
            # Полностью черная тема
            self.setStyleSheet("""
                QDialog {
                    background-color: #000000;
                    color: #ffffff;
                }
                QLabel {
                    color: #ffffff;
                    background-color: transparent;
                }
            """)
        elif self.is_amoled:
            # AMOLED тема
            self.setStyleSheet("""
                QDialog {
                    background-color: #000000;
                    color: #ffffff;
                }
                QLabel {
                    color: #ffffff;
                    background-color: transparent;
                }
            """)
        elif self.is_dark_theme:
            # Обычная темная тема
            self.setStyleSheet("""
                QDialog {
                    background-color: #2b2b2b;
                    color: #ffffff;
                }
                QLabel {
                    color: #ffffff;
                    background-color: transparent;
                }
            """)
        else:
            # Светлая тема
            self.setStyleSheet("""
                QDialog {
                    background-color: #f5f5f5;
                    color: #333333;
                }
                QLabel {
                    color: #333333;
                    background-color: transparent;
                }
            """)
    
    def _get_title_style(self):
        """Возвращает стиль для заголовка"""
        if self.is_dark_theme or self.is_pure_black or self.is_amoled:
            return """
                font-size: 18pt;
                font-weight: bold;
                color: #0099ff;
                padding: 10px;
                background-color: transparent;
            """
        else:
            return """
                font-size: 18pt;
                font-weight: bold;
                color: #0077ff;
                padding: 10px;
                background-color: transparent;
            """
    
    def _get_line_style(self):
        """Возвращает стиль для разделителя"""
        if self.is_pure_black:
            return "QFrame { color: #1a1a1a; }"
        elif self.is_amoled:
            return "QFrame { color: #222222; }"
        elif self.is_dark_theme:
            return "QFrame { color: #555555; }"
        else:
            return "QFrame { color: #d0d0d0; }"
    
    def _get_description_style(self):
        """Возвращает стиль для описания"""
        if self.is_dark_theme or self.is_pure_black or self.is_amoled:
            return "font-size: 10pt; color: #cccccc; padding: 10px; background-color: transparent;"
        else:
            return "font-size: 10pt; color: #666666; padding: 10px; background-color: transparent;"
    
    def _get_section_label_style(self):
        """Возвращает стиль для заголовков секций"""
        if self.is_dark_theme or self.is_pure_black or self.is_amoled:
            return "font-weight: bold; font-size: 11pt; color: #ffffff; background-color: transparent;"
        else:
            return "font-weight: bold; font-size: 11pt; color: #444444; background-color: transparent;"
    
    def _get_button_style(self, color):
        """Возвращает стиль для кнопок в зависимости от темы"""
        if self.is_pure_black:
            # Для полностью черной темы - серые кнопки
            return f"""
            QPushButton {{
                border: 1px solid #333333;
                background-color: rgb(32, 32, 32);
                color: #ffffff;
                border-radius: 6px;
                padding: 10px;
                font-weight: bold;
                font-size: 10pt;
                min-height: 35px;
            }}
            QPushButton:hover {{
                background-color: rgb(64, 64, 64);
                border: 1px solid #555555;
            }}
            QPushButton:pressed {{
                background-color: rgb(16, 16, 16);
                border: 1px solid #777777;
            }}
            """
        elif self.is_amoled:
            # Для AMOLED - почти черные кнопки с цветной подсветкой при наведении
            return f"""
            QPushButton {{
                border: none;
                background-color: rgb(16, 16, 16);
                color: #ffffff;
                border-radius: 6px;
                padding: 10px;
                font-weight: bold;
                font-size: 10pt;
                min-height: 35px;
            }}
            QPushButton:hover {{
                background-color: rgba({color}, 0.3);
                border: 1px solid rgba({color}, 0.5);
            }}
            QPushButton:pressed {{
                background-color: rgba({color}, 0.5);
            }}
            """
        else:
            # Обычный стиль
            return BUTTON_STYLE.format(color)
    
    def _get_close_button_style(self):
        """Возвращает стиль для кнопки закрытия"""
        if self.is_pure_black:
            return """
                QPushButton {
                    background-color: #1a1a1a;
                    border: 1px solid #333333;
                    color: #ffffff;
                    border-radius: 5px;
                    padding: 8px;
                    font-size: 10pt;
                    min-width: 100px;
                }
                QPushButton:hover {
                    background-color: #333333;
                    border: 1px solid #555555;
                }
            """
        elif self.is_amoled:
            return """
                QPushButton {
                    background-color: #0a0a0a;
                    border: 1px solid #222222;
                    color: #ffffff;
                    border-radius: 5px;
                    padding: 8px;
                    font-size: 10pt;
                    min-width: 100px;
                }
                QPushButton:hover {
                    background-color: #1a1a1a;
                    border: 1px solid #333333;
                }
            """
        elif self.is_dark_theme:
            return """
                QPushButton {
                    background-color: #3f3f3f;
                    border: 1px solid #555555;
                    color: #ffffff;
                    border-radius: 5px;
                    padding: 8px;
                    font-size: 10pt;
                    min-width: 100px;
                }
                QPushButton:hover {
                    background-color: #4f4f4f;
                }
            """
        else:
            return """
                QPushButton {
                    background-color: #f0f0f0;
                    border: 1px solid #d0d0d0;
                    color: #333333;
                    border-radius: 5px;
                    padding: 8px;
                    font-size: 10pt;
                    min-width: 100px;
                }
                QPushButton:hover {
                    background-color: #e0e0e0;
                }
            """

    def _open_help_folder(self):
        """Открывает папку help"""
        try:
            from config import HELP_FOLDER
            import subprocess
            if os.path.exists(HELP_FOLDER):
                subprocess.Popen(f'explorer "{HELP_FOLDER}"')
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Ошибка", f"Не удалось открыть папку: {e}")
    
    def _open_telegram(self):
        """Открывает Telegram канал поддержки"""
        try:
            # Определяем канал в зависимости от версии
            if CHANNEL == "test":
                telegram_url = "https://t.me/zaprethelp"
            else:
                telegram_url = "https://t.me/zaprethelp"
            
            webbrowser.open(telegram_url)
            log(f"Открыт Telegram канал: {telegram_url}", "INFO")
            
        except Exception as e:
            log(f"Ошибка при открытии Telegram: {e}", "❌ ERROR")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Ошибка", f"Не удалось открыть Telegram:\n{e}")
    
    def _open_discord(self):
        """Открывает Discord сервер"""
        try:
            discord_url = "https://discord.gg/kkcBDG2uws"  # Замените на реальный URL
            webbrowser.open(discord_url)
            log(f"Открыт Discord сервер: {discord_url}", "INFO")
            
        except Exception as e:
            log(f"Ошибка при открытии Discord: {e}", "❌ ERROR")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Ошибка", f"Не удалось открыть Discord:\n{e}")
    
    def _open_wiki(self):
        """Открывает Wiki на GitHub"""
        try:
            wiki_url = "https://github.com/youtubediscord/zapret"
            webbrowser.open(wiki_url)
            log(f"Открыта Wiki: {wiki_url}", "INFO")
            
        except Exception as e:
            log(f"Ошибка при открытии Wiki: {e}", "❌ ERROR")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Ошибка", f"Не удалось открыть Wiki:\n{e}")