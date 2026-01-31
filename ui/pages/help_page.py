# ui/pages/help_page.py
"""Страница Справка - ссылки, руководства, поддержка"""

import os
import subprocess
import webbrowser

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QMessageBox
import qtawesome as qta

from .base_page import BasePage
from log import log


class HelpPage(BasePage):
    """Страница справки (внутри группы "О программе")"""

    def __init__(self, parent=None):
        super().__init__("Справка", "Руководства, ссылки и поддержка", parent)
        self._build_ui()

    def _build_ui(self):
        # Ссылки
        self.add_section_title("Ссылки")

        # --- Документация ---
        docs_card = self._create_links_card("Документация")
        docs_layout = docs_card.layout()

        self._add_link_item(
            docs_layout,
            "fa5s.info-circle",
            "Что это такое?",
            "Руководство и ответы на вопросы",
            self._open_info,
        )
        self._add_link_item(
            docs_layout,
            "fa5s.folder-open",
            "Папка с инструкциями",
            "Открыть локальную папку help",
            self._open_help_folder,
        )
        self._add_link_item(
            docs_layout,
            "fa5s.mobile-alt",
            "На Android (ByeByeDPI)",
            "Открыть PDF инструкцию",
            self._open_byedpi_pdf,
        )
        self._add_link_item(
            docs_layout,
            "fa5b.github",
            "GitHub",
            "Исходный код и документация",
            self._open_github,
        )

        self.add_widget(docs_card)
        self.add_spacing(8)

        # --- Поддержка ---
        support_card = self._create_links_card("Поддержка")
        support_layout = support_card.layout()

        self._add_link_item(
            support_layout,
            "fa5b.telegram",
            "Telegram поддержка",
            "Помощь и вопросы по использованию",
            self._open_telegram_support,
        )
        self._add_link_item(
            support_layout,
            "fa5b.discord",
            "Discord сервер",
            "Сообщество и живое общение",
            self._open_discord,
        )

        self.add_widget(support_card)
        self.add_spacing(8)

        # --- Новости ---
        news_card = self._create_links_card("Новости")
        news_layout = news_card.layout()

        self._add_link_item(
            news_layout,
            "fa5b.telegram",
            "Telegram канал",
            "Новости и обновления",
            self._open_telegram_news,
        )

        self.add_widget(news_card)

    def _create_links_card(self, title: str) -> QFrame:
        """Создаёт карточку для группы ссылок без рамки с собственным фоном"""
        card = QFrame()
        card.setStyleSheet(
            """
            QFrame {
                background: transparent;
                border: none;
            }
        """
        )

        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(4)

        header = QLabel(title)
        header.setStyleSheet(
            """
            QLabel {
                color: rgba(255, 255, 255, 0.5);
                font-size: 10px;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 1px;
                padding: 0px 4px 8px 4px;
                background: transparent;
                border: none;
            }
        """
        )
        layout.addWidget(header)
        return card

    def _add_link_item(self, layout, icon_name, title, desc, callback):
        """Добавляет кликабельный элемент ссылки без рамок"""
        link_widget = QPushButton()
        link_widget.setCursor(Qt.CursorShape.PointingHandCursor)
        link_widget.setStyleSheet(
            """
            QPushButton {
                background: transparent;
                border: none;
                border-radius: 6px;
                padding: 12px;
                text-align: left;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.05);
            }
            QPushButton:pressed {
                background: rgba(255, 255, 255, 0.08);
            }
        """
        )
        link_widget.clicked.connect(callback)

        link_layout = QHBoxLayout(link_widget)
        link_layout.setContentsMargins(0, 0, 0, 0)
        link_layout.setSpacing(12)

        link_icon = QLabel()
        link_icon.setPixmap(qta.icon(icon_name, color="#60cdff").pixmap(20, 20))
        link_icon.setFixedSize(24, 24)
        link_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        link_icon.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        link_layout.addWidget(link_icon)

        link_text_layout = QVBoxLayout()
        link_text_layout.setSpacing(0)
        link_text_layout.setContentsMargins(0, 0, 0, 0)

        link_title = QLabel(title)
        link_title.setStyleSheet("color: #60cdff; font-size: 12px; font-weight: 500;")
        link_title.setFixedHeight(16)
        link_title.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        link_text_layout.addWidget(link_title)

        link_desc = QLabel(desc)
        link_desc.setStyleSheet("color: rgba(255, 255, 255, 0.5); font-size: 10px;")
        link_desc.setFixedHeight(14)
        link_desc.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        link_text_layout.addWidget(link_desc)

        link_layout.addLayout(link_text_layout, 1)
        layout.addWidget(link_widget)

    def _open_info(self):
        try:
            from config.urls import INFO_URL

            webbrowser.open(INFO_URL)
            log(f"Открыта справка: {INFO_URL}", "INFO")
        except Exception as e:
            QMessageBox.warning(self.window(), "Ошибка", f"Не удалось открыть справку:\n{e}")

    def _open_help_folder(self):
        try:
            from config import HELP_FOLDER

            if os.path.exists(HELP_FOLDER):
                subprocess.Popen(f'explorer "{HELP_FOLDER}"')
                log(f"Открыта папка: {HELP_FOLDER}", "INFO")
            else:
                QMessageBox.warning(self.window(), "Ошибка", "Папка с инструкциями не найдена")
        except Exception as e:
            QMessageBox.warning(self.window(), "Ошибка", f"Не удалось открыть папку:\n{e}")

    def _open_byedpi_pdf(self):
        try:
            from config import HELP_FOLDER

            pdf_path = os.path.join(HELP_FOLDER, "ByeByeDPI - Что это такое.pdf")
            if not os.path.exists(pdf_path):
                QMessageBox.warning(
                    self.window(),
                    "Файл не найден",
                    f"PDF руководство не найдено:\n{pdf_path}",
                )
                return

            os.startfile(pdf_path)  # noqa: S606 - Windows only
            log(f"Открыт PDF: {pdf_path}", "INFO")
        except Exception as e:
            QMessageBox.warning(self.window(), "Ошибка", f"Не удалось открыть PDF:\n{e}")

    def _open_telegram_support(self):
        try:
            from config.telegram_links import open_telegram_link

            open_telegram_link("zaprethelp")
            log("Открыт Telegram: zaprethelp", "INFO")
        except Exception as e:
            QMessageBox.warning(self.window(), "Ошибка", f"Не удалось открыть Telegram:\n{e}")

    def _open_telegram_news(self):
        try:
            from config.telegram_links import open_telegram_link

            open_telegram_link("bypassblock")
            log("Открыт Telegram: bypassblock", "INFO")
        except Exception as e:
            QMessageBox.warning(self.window(), "Ошибка", f"Не удалось открыть Telegram:\n{e}")

    def _open_discord(self):
        try:
            url = "https://discord.gg/kkcBDG2uws"
            webbrowser.open(url)
            log(f"Открыт Discord: {url}", "INFO")
        except Exception as e:
            QMessageBox.warning(self.window(), "Ошибка", f"Не удалось открыть Discord:\n{e}")

    def _open_github(self):
        try:
            url = "https://github.com/youtubediscord/zapret"
            webbrowser.open(url)
            log(f"Открыт GitHub: {url}", "INFO")
        except Exception as e:
            QMessageBox.warning(self.window(), "Ошибка", f"Не удалось открыть GitHub:\n{e}")

