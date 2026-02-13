# ui/pages/help_page.py
"""Страница Справка - ссылки, руководства и новости"""

import os
import subprocess
import webbrowser

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QMessageBox, QSizePolicy
import qtawesome as qta

from .base_page import BasePage
from log import log


class HelpPage(BasePage):
    """Страница справки (внутри группы "О программе")"""

    def __init__(self, parent=None):
        super().__init__("Справка", "Руководства, ссылки и новости", parent)
        self._build_ui()

    def _build_ui(self):
        self._add_motto_block()
        self.add_spacing(6)

        # Ссылки
        self.add_section_title("Ссылки")

        # --- Документация ---
        docs_card = self._create_links_card("Документация")
        docs_layout = docs_card.layout()

        self._add_link_item(
            docs_layout,
            "fa5b.telegram",
            "Сайт-форум для новичков",
            "Авторизация через Telegram-бота",
            self._open_forum_for_beginners,
        )
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
            "Открыть инструкцию на сайте",
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
        self._add_link_item(
            news_layout,
            "fa5b.mastodon",
            "Mastodon профиль",
            "Новости в Fediverse",
            self._open_mastodon_profile,
        )
        self._add_link_item(
            news_layout,
            "fa5s.globe",
            "Bastyon профиль",
            "Новости в Bastyon",
            self._open_bastyon_profile,
        )

        self.add_widget(news_card)

    def _add_motto_block(self):
        """Добавляет крупный слоган и перевод в верхней части страницы"""
        motto_wrap = QFrame()
        motto_wrap.setStyleSheet(
            """
            QFrame {
                background: transparent;
                border: none;
            }
        """
        )

        motto_row = QHBoxLayout(motto_wrap)
        motto_row.setContentsMargins(0, 0, 0, 0)
        motto_row.setSpacing(0)

        motto_text_wrap = QFrame()
        motto_text_wrap.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        motto_text_wrap.setStyleSheet("QFrame { background: transparent; border: none; }")

        motto_text_layout = QVBoxLayout(motto_text_wrap)
        motto_text_layout.setContentsMargins(0, 0, 0, 0)
        motto_text_layout.setSpacing(2)

        motto_title = QLabel("keep thinking, keep searching, keep learning....")
        motto_title.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
        motto_title.setWordWrap(True)
        motto_title.setStyleSheet(
            """
            QLabel {
                color: rgba(235, 235, 235, 0.88);
                font-size: 25px;
                font-weight: 700;
                letter-spacing: 0.8px;
                font-family: 'Segoe UI Variable Display', 'Segoe UI', sans-serif;
            }
        """
        )

        motto_translate = QLabel("Продолжай думать, продолжай искать, продолжай учиться....")
        motto_translate.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
        motto_translate.setWordWrap(True)
        motto_translate.setStyleSheet(
            """
            QLabel {
                color: rgba(176, 176, 176, 0.85);
                font-size: 17px;
                font-style: italic;
                font-weight: 600;
                letter-spacing: 0.5px;
                font-family: 'Palatino Linotype', 'Book Antiqua', 'Georgia', serif;
                padding-top: 2px;
            }
        """
        )

        motto_cta = QLabel("Zapret2 - думай свободно, ищи смелее, учись всегда.")
        motto_cta.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
        motto_cta.setWordWrap(True)
        motto_cta.setStyleSheet(
            """
            QLabel {
                color: rgba(140, 140, 140, 0.9);
                font-size: 12px;
                letter-spacing: 1.1px;
                font-family: 'Segoe UI', sans-serif;
                text-transform: uppercase;
                padding-top: 6px;
            }
        """
        )

        motto_text_layout.addWidget(motto_title)
        motto_text_layout.addWidget(motto_translate)
        motto_text_layout.addWidget(motto_cta)

        motto_row.addWidget(motto_text_wrap, 1)
        self.add_widget(motto_wrap)

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

    def _open_forum_for_beginners(self):
        try:
            from config.telegram_links import open_telegram_link

            open_telegram_link("nozapretinrussia_bot")
            log("Открыт Telegram-бот: nozapretinrussia_bot", "INFO")
        except Exception as e:
            QMessageBox.warning(self.window(), "Ошибка", f"Не удалось открыть Telegram-бота:\n{e}")

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
            from config.urls import ANDROID_URL

            webbrowser.open(ANDROID_URL)
            log(f"Открыта инструкция Android: {ANDROID_URL}", "INFO")
        except Exception as e:
            QMessageBox.warning(self.window(), "Ошибка", f"Не удалось открыть инструкцию:\n{e}")

    def _open_telegram_news(self):
        try:
            from config.telegram_links import open_telegram_link

            open_telegram_link("bypassblock")
            log("Открыт Telegram: bypassblock", "INFO")
        except Exception as e:
            QMessageBox.warning(self.window(), "Ошибка", f"Не удалось открыть Telegram:\n{e}")

    def _open_mastodon_profile(self):
        try:
            url = "https://mastodon.social/@zapret"
            webbrowser.open(url)
            log(f"Открыт Mastodon: {url}", "INFO")
        except Exception as e:
            QMessageBox.warning(self.window(), "Ошибка", f"Не удалось открыть Mastodon:\n{e}")

    def _open_bastyon_profile(self):
        try:
            url = "https://bastyon.com/zapretgui"
            webbrowser.open(url)
            log(f"Открыт Bastyon: {url}", "INFO")
        except Exception as e:
            QMessageBox.warning(self.window(), "Ошибка", f"Не удалось открыть Bastyon:\n{e}")

    def _open_github(self):
        try:
            url = "https://github.com/youtubediscord/zapret"
            webbrowser.open(url)
            log(f"Открыт GitHub: {url}", "INFO")
        except Exception as e:
            QMessageBox.warning(self.window(), "Ошибка", f"Не удалось открыть GitHub:\n{e}")
