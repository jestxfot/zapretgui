# ui/pages/help_page.py
"""Страница Справка - ссылки, руководства и новости"""

import os
import subprocess
import webbrowser

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QSizePolicy

try:
    from qfluentwidgets import (
        HyperlinkCard, PushSettingCard, SettingCardGroup,
        FluentIcon, InfoBar,
    )
    _HAS_FLUENT = True
except ImportError:
    _HAS_FLUENT = False
    FluentIcon = None
    InfoBar = None

from .base_page import BasePage
from ui.theme import get_theme_tokens
from log import log


class HelpPage(BasePage):
    """Страница справки (внутри группы «О программе»)"""

    def __init__(self, parent=None):
        super().__init__("Справка", "Руководства, ссылки и новости", parent)
        self._build_ui()

    # ──────────────────────────────────────────────────────────────────────────
    # UI
    # ──────────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        self._add_motto_block()
        self.add_spacing(6)
        self.add_section_title("Ссылки")

        try:
            from config.urls import INFO_URL, ANDROID_URL
        except Exception:
            INFO_URL = ""
            ANDROID_URL = ""

        if not _HAS_FLUENT:
            return

        # ── Документация ──────────────────────────────────────────────────────
        docs_group = SettingCardGroup("Документация", self.content)

        forum_card = PushSettingCard(
            "Открыть", FluentIcon.SEND,
            "Сайт-форум для новичков",
            "Авторизация через Telegram-бота",
        )
        forum_card.clicked.connect(self._open_forum_for_beginners)

        info_card = HyperlinkCard(
            INFO_URL, "Открыть",
            FluentIcon.INFO,
            "Что это такое?",
            "Руководство и ответы на вопросы",
        )

        folder_card = PushSettingCard(
            "Открыть", FluentIcon.FOLDER,
            "Папка с инструкциями",
            "Открыть локальную папку help",
        )
        folder_card.clicked.connect(self._open_help_folder)

        android_card = HyperlinkCard(
            ANDROID_URL, "Открыть",
            FluentIcon.PHONE,
            "На Android (ByeByeDPI)",
            "Открыть инструкцию на сайте",
        )

        github_card = HyperlinkCard(
            "https://github.com/youtubediscord/zapret", "Открыть",
            FluentIcon.GITHUB,
            "GitHub",
            "Исходный код и документация",
        )

        docs_group.addSettingCards([forum_card, info_card, folder_card, android_card, github_card])
        self.add_widget(docs_group)
        self.add_spacing(8)

        # ── Новости ───────────────────────────────────────────────────────────
        news_group = SettingCardGroup("Новости", self.content)

        telegram_card = PushSettingCard(
            "Открыть", FluentIcon.MEGAPHONE,
            "Telegram канал",
            "Новости и обновления",
        )
        telegram_card.clicked.connect(self._open_telegram_news)

        mastodon_card = HyperlinkCard(
            "https://mastodon.social/@zapret", "Открыть",
            FluentIcon.GLOBE,
            "Mastodon профиль",
            "Новости в Fediverse",
        )

        bastyon_card = HyperlinkCard(
            "https://bastyon.com/zapretgui", "Открыть",
            FluentIcon.GLOBE,
            "Bastyon профиль",
            "Новости в Bastyon",
        )

        news_group.addSettingCards([telegram_card, mastodon_card, bastyon_card])
        self.add_widget(news_group)

    def _add_motto_block(self):
        """Добавляет крупный слоган и перевод в верхней части страницы"""
        tokens = get_theme_tokens()
        motto_wrap = QFrame()
        motto_wrap.setStyleSheet("QFrame { background: transparent; border: none; }")

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
            f"QLabel {{ color: {tokens.fg}; font-size: 25px; font-weight: 700; "
            f"letter-spacing: 0.8px; "
            f"font-family: 'Segoe UI Variable Display', 'Segoe UI', sans-serif; }}"
        )

        motto_translate = QLabel("Продолжай думать, продолжай искать, продолжай учиться....")
        motto_translate.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
        motto_translate.setWordWrap(True)
        motto_translate.setStyleSheet(
            f"QLabel {{ color: {tokens.fg_muted}; font-size: 17px; font-style: italic; "
            f"font-weight: 600; letter-spacing: 0.5px; "
            f"font-family: 'Palatino Linotype', 'Book Antiqua', 'Georgia', serif; "
            f"padding-top: 2px; }}"
        )

        motto_cta = QLabel("Zapret2 - думай свободно, ищи смелее, учись всегда.")
        motto_cta.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
        motto_cta.setWordWrap(True)
        motto_cta.setStyleSheet(
            f"QLabel {{ color: {tokens.fg_faint}; font-size: 12px; letter-spacing: 1.1px; "
            f"font-family: 'Segoe UI', sans-serif; text-transform: uppercase; "
            f"padding-top: 6px; }}"
        )

        motto_text_layout.addWidget(motto_title)
        motto_text_layout.addWidget(motto_translate)
        motto_text_layout.addWidget(motto_cta)

        motto_row.addWidget(motto_text_wrap, 1)
        self.add_widget(motto_wrap)

    # ──────────────────────────────────────────────────────────────────────────
    # Callbacks
    # ──────────────────────────────────────────────────────────────────────────

    def _open_info(self):
        try:
            from config.urls import INFO_URL
            webbrowser.open(INFO_URL)
            log(f"Открыта справка: {INFO_URL}", "INFO")
        except Exception as e:
            if InfoBar:
                InfoBar.warning(title="Ошибка", content=f"Не удалось открыть справку:\n{e}", parent=self.window())

    def _open_forum_for_beginners(self):
        try:
            from config.telegram_links import open_telegram_link
            open_telegram_link("nozapretinrussia_bot")
            log("Открыт Telegram-бот: nozapretinrussia_bot", "INFO")
        except Exception as e:
            if InfoBar:
                InfoBar.warning(title="Ошибка", content=f"Не удалось открыть Telegram-бота:\n{e}", parent=self.window())

    def _open_help_folder(self):
        try:
            from config import HELP_FOLDER
            if os.path.exists(HELP_FOLDER):
                subprocess.Popen(f'explorer "{HELP_FOLDER}"')
                log(f"Открыта папка: {HELP_FOLDER}", "INFO")
            else:
                if InfoBar:
                    InfoBar.warning(title="Ошибка", content="Папка с инструкциями не найдена", parent=self.window())
        except Exception as e:
            if InfoBar:
                InfoBar.warning(title="Ошибка", content=f"Не удалось открыть папку:\n{e}", parent=self.window())

    def _open_byedpi_pdf(self):
        try:
            from config.urls import ANDROID_URL
            webbrowser.open(ANDROID_URL)
            log(f"Открыта инструкция Android: {ANDROID_URL}", "INFO")
        except Exception as e:
            if InfoBar:
                InfoBar.warning(title="Ошибка", content=f"Не удалось открыть инструкцию:\n{e}", parent=self.window())

    def _open_telegram_news(self):
        try:
            from config.telegram_links import open_telegram_link
            open_telegram_link("bypassblock")
            log("Открыт Telegram: bypassblock", "INFO")
        except Exception as e:
            if InfoBar:
                InfoBar.warning(title="Ошибка", content=f"Не удалось открыть Telegram:\n{e}", parent=self.window())

    def _open_github(self):
        try:
            url = "https://github.com/youtubediscord/zapret"
            webbrowser.open(url)
            log(f"Открыт GitHub: {url}", "INFO")
        except Exception as e:
            if InfoBar:
                InfoBar.warning(title="Ошибка", content=f"Не удалось открыть GitHub:\n{e}", parent=self.window())
