from PyQt6.QtWidgets import QVBoxLayout, QHBoxLayout, QWidget, QStackedWidget, QScrollArea, QFrame
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QGuiApplication

from qfluentwidgets import (
    MessageBoxBase, SubtitleLabel, BodyLabel, CaptionLabel, StrongBodyLabel,
    PushButton, PrimaryPushButton, TransparentPushButton,
    SegmentedWidget, CardWidget, HyperlinkButton,
)

from config import APP_VERSION
from config.urls import INFO_URL, BOLVAN_URL


class AboutDialog(MessageBoxBase):
    def __init__(self, parent=None):
        from tgram import get_client_id

        if parent and not parent.isWindow():
            parent = parent.window()
        super().__init__(parent)

        cid = get_client_id()
        self._cid = cid

        # === Заголовок ===
        header_layout = QHBoxLayout()
        titleLabel = SubtitleLabel("Zapret GUI", self.widget)
        versionLabel = CaptionLabel(f"Версия: {APP_VERSION}", self.widget)
        header_v = QVBoxLayout()
        header_v.setSpacing(2)
        header_v.addWidget(titleLabel)
        header_v.addWidget(versionLabel)
        header_layout.addLayout(header_v, 1)
        self.viewLayout.addLayout(header_layout)

        # === ID устройства ===
        id_card = CardWidget(self.widget)
        id_layout = QHBoxLayout(id_card)
        id_layout.setContentsMargins(12, 8, 12, 8)
        id_label = BodyLabel(f"ID устройства:", self.widget)
        id_value = StrongBodyLabel(cid, self.widget)
        id_value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        id_layout.addWidget(id_label)
        id_layout.addWidget(id_value, 1)
        self.viewLayout.addWidget(id_card)

        # === Tabs (SegmentedWidget + QStackedWidget) ===
        self.pivot = SegmentedWidget(self.widget)
        self.stackedWidget = QStackedWidget(self.widget)

        info_page = self._create_info_page()
        channels_page = self._create_channels_page()

        self.stackedWidget.addWidget(info_page)
        self.stackedWidget.addWidget(channels_page)

        self.pivot.addItem(routeKey="info", text="Информация",
                           onClick=lambda: self.stackedWidget.setCurrentIndex(0))
        self.pivot.addItem(routeKey="telegram", text="Телеграм",
                           onClick=lambda: self.stackedWidget.setCurrentIndex(1))
        self.pivot.setCurrentItem("info")

        self.viewLayout.addWidget(self.pivot)
        self.viewLayout.addWidget(self.stackedWidget, 1)

        # === Кнопки ===
        self.yesButton.setText("Закрыть")
        self.hideCancelButton()

        # Кнопка копирования ID — добавляем в buttonLayout перед yesButton
        self.copyIdButton = PushButton(self.widget)
        self.copyIdButton.setText("Копировать ID")
        self.copyIdButton.clicked.connect(lambda: self._copy_cid(cid))
        self.buttonLayout.insertWidget(0, self.copyIdButton, 1)

        self.widget.setMinimumSize(580, 520)

    def _create_info_page(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(4, 8, 4, 4)
        layout.setSpacing(8)

        items = [
            (f"Руководство пользователя", INFO_URL),
            ("Автор GUI: @bypassblock", "tg://resolve?domain=bypassblock"),
            (f"Автор Zapret: bol-van (GitHub)", BOLVAN_URL),
            ("Поддержка: @youtubenotwork", "tg://resolve?domain=youtubenotwork"),
        ]
        for text, url in items:
            btn = HyperlinkButton(url=url, text=text, parent=widget)
            layout.addWidget(btn)

        desc = BodyLabel(
            "Zapret GUI — графический интерфейс для утилиты обхода блокировок.\n"
            "Программа помогает настроить и управлять параметрами обхода.",
            widget,
        )
        desc.setWordWrap(True)
        layout.addWidget(desc)
        layout.addStretch()
        return widget

    def _create_channels_page(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(4, 8, 4, 4)
        layout.setSpacing(12)

        groups = [
            ("Папка с чатами", [
                ("Все наши каналы одним списком", "tg://addlist?slug=xjPs164MI7AxZWE6"),
            ]),
            ("Основные каналы", [
                ("Основная группа", "tg://resolve?domain=bypassblock&post=399"),
                ("Группа по блокировкам", "tg://resolve?domain=youtubenotwork"),
                ("Android и VPN сервисы", "tg://resolve?domain=zapretyoutubediscordvpn"),
                ("Популярные моды APK", "tg://resolve?domain=androidawesome"),
                ("Переходник (все каналы)", "tg://resolve?domain=runetvpnyoutubediscord"),
            ]),
            ("О Zapret", [
                ("Скачать Zapret (все версии)", "tg://resolve?domain=zapretnetdiscordyoutube"),
                ("Скачать Blockcheck", "tg://resolve?domain=zapretblockcheck"),
                ("Дорожная карта", "tg://resolve?domain=approundmap"),
                ("Помощь с настройками", "tg://resolve?domain=zaprethelp"),
                ("Вирусы в Запрете?", "tg://resolve?domain=zapretvirus"),
            ]),
            ("Боты", [
                ("ИИ помощник по обходу", "tg://resolve?domain=zapretbypass_bot"),
                ("Платный VPN от команды", "tg://resolve?domain=zapretvpns_bot"),
            ]),
        ]

        for group_title, links in groups:
            group_label = StrongBodyLabel(group_title, content)
            layout.addWidget(group_label)
            for text, url in links:
                btn = HyperlinkButton(url=url, text=text, parent=content)
                layout.addWidget(btn)

        layout.addStretch()
        scroll.setWidget(content)
        return scroll

    def _on_link_clicked(self, url: str):
        from config.telegram_links import open_telegram_url
        import webbrowser

        if url.startswith("tg://"):
            if url.startswith("tg://resolve?domain="):
                parts = url.replace("tg://resolve?", "").split("&")
                params = dict(p.split("=") for p in parts if "=" in p)
                domain = params.get("domain", "")
                post = params.get("post", "")
                https_url = f"https://t.me/{domain}/{post}" if post else f"https://t.me/{domain}"
            elif url.startswith("tg://addlist?slug="):
                slug = url.replace("tg://addlist?slug=", "")
                https_url = f"https://t.me/addlist/{slug}"
            else:
                https_url = url.replace("tg://", "https://t.me/")
            open_telegram_url(url, https_url)
        else:
            import webbrowser
            webbrowser.open(url)

    def _copy_cid(self, cid: str):
        QGuiApplication.clipboard().setText(cid)
        from qfluentwidgets import InfoBar, InfoBarPosition
        InfoBar.success(
            title="Скопировано",
            content="ID устройства скопирован в буфер обмена",
            parent=self.window(),
            duration=2000,
            position=InfoBarPosition.TOP,
        )
