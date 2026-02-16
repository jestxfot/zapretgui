# ui/pages/about_page.py
"""Страница О программе - версия, подписка, информация"""

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame
import qtawesome as qta

from .base_page import BasePage
from ui.sidebar import SettingsCard, ActionButton
from ui.theme import get_theme_tokens
from log import log


class AboutPage(BasePage):
    """Страница О программе"""
    
    def __init__(self, parent=None):
        super().__init__("О программе", "Версия, подписка и информация", parent)
        
        self._build_ui()
        
    def _build_ui(self):
        from config import APP_VERSION
        tokens = get_theme_tokens()
        card_style = f"""
            QFrame#settingsCard {{
                background-color: {tokens.surface_bg};
                border: none;
                border-radius: 8px;
            }}
        """
        
        # Информация о версии
        self.add_section_title("Версия")
        
        version_card = SettingsCard()
        version_card.setStyleSheet(card_style)
        
        version_layout = QHBoxLayout()
        version_layout.setSpacing(16)
        
        # Иконка
        icon_label = QLabel()
        icon_label.setPixmap(qta.icon('fa5s.shield-alt', color=tokens.accent_hex).pixmap(40, 40))
        icon_label.setFixedSize(48, 48)
        version_layout.addWidget(icon_label)
        
        # Текст
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        
        name_label = QLabel("Zapret 2 GUI")
        name_label.setStyleSheet(f"""
            QLabel {{
                color: {tokens.fg};
                font-size: 16px;
                font-weight: 600;
            }}
        """)
        text_layout.addWidget(name_label)
        
        version_label = QLabel(f"Версия {APP_VERSION}")
        version_label.setStyleSheet(f"""
            QLabel {{
                color: {tokens.fg_muted};
                font-size: 12px;
            }}
        """)
        text_layout.addWidget(version_label)
        
        version_layout.addLayout(text_layout, 1)
        
        # Кнопка для перехода на страницу обновлений
        self.update_btn = ActionButton("Настройка обновлений", "fa5s.sync-alt")
        self.update_btn.setFixedHeight(36)
        version_layout.addWidget(self.update_btn)
        
        version_card.add_layout(version_layout)
        self.add_widget(version_card)

        self.add_spacing(16)

        # ID устройства
        self.add_section_title("Устройство")

        device_card = SettingsCard()
        device_card.setStyleSheet(card_style)

        device_layout = QHBoxLayout()
        device_layout.setSpacing(16)

        device_icon = QLabel()
        device_icon.setPixmap(qta.icon('fa5s.key', color=tokens.accent_hex).pixmap(20, 20))
        device_icon.setFixedSize(24, 24)
        device_layout.addWidget(device_icon)

        try:
            from tgram import get_client_id

            client_id = get_client_id()
        except Exception:
            client_id = ""

        device_text_layout = QVBoxLayout()
        device_text_layout.setSpacing(2)

        device_title = QLabel("ID устройства")
        device_title.setStyleSheet(f"color: {tokens.fg}; font-size: 13px; font-weight: 500;")
        device_text_layout.addWidget(device_title)

        self.client_id_label = QLabel(client_id or "—")
        self.client_id_label.setStyleSheet(f"color: {tokens.fg_muted}; font-size: 12px;")
        self.client_id_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        device_text_layout.addWidget(self.client_id_label)

        device_layout.addLayout(device_text_layout, 1)

        copy_btn = ActionButton("Копировать ID", "fa5s.copy")
        copy_btn.setFixedHeight(36)
        copy_btn.clicked.connect(lambda: self._copy_client_id())
        device_layout.addWidget(copy_btn)

        device_card.add_layout(device_layout)
        self.add_widget(device_card)
        
        self.add_spacing(16)
        
        # Подписка
        self.add_section_title("Подписка")
        
        sub_card = SettingsCard()
        sub_card.setStyleSheet(card_style)
        
        sub_layout = QVBoxLayout()
        sub_layout.setSpacing(12)
        
        # Статус подписки
        sub_status_layout = QHBoxLayout()
        sub_status_layout.setSpacing(8)
        
        self.sub_status_icon = QLabel()
        self.sub_status_icon.setPixmap(qta.icon('fa5s.user', color=tokens.fg_faint).pixmap(18, 18))
        self.sub_status_icon.setFixedSize(22, 22)
        sub_status_layout.addWidget(self.sub_status_icon)
        
        self.sub_status_label = QLabel("Free версия")
        self.sub_status_label.setStyleSheet(f"color: {tokens.fg}; font-size: 13px; font-weight: 500;")
        sub_status_layout.addWidget(self.sub_status_label, 1)
        
        sub_layout.addLayout(sub_status_layout)
        
        sub_desc = QLabel(
            "Подписка Zapret Premium открывает доступ к дополнительным темам, "
            "приоритетной поддержке и VPN-сервису."
        )
        sub_desc.setStyleSheet(f"color: {tokens.fg_muted}; font-size: 11px;")
        sub_desc.setWordWrap(True)
        sub_layout.addWidget(sub_desc)
        
        sub_btns = QHBoxLayout()
        sub_btns.setSpacing(8)
        
        self.premium_btn = ActionButton("Premium и VPN", "fa5s.star", accent=True)
        self.premium_btn.setFixedHeight(36)
        sub_btns.addWidget(self.premium_btn)
        
        sub_btns.addStretch()
        sub_layout.addLayout(sub_btns)
        
        sub_card.add_layout(sub_layout)
        self.add_widget(sub_card)

    def _copy_client_id(self) -> None:
        try:
            cid = ""
            try:
                cid = self.client_id_label.text().strip() if hasattr(self, "client_id_label") else ""
            except Exception:
                cid = ""
            if not cid or cid == "—":
                return

            QGuiApplication.clipboard().setText(cid)
            # Не спамим уведомлениями: достаточно обновить статус если доступно
            if hasattr(self.parent_app, "set_status"):
                self.parent_app.set_status("ID скопирован")
        except Exception as e:
            log(f"Ошибка копирования ID: {e}", "DEBUG")
        
    def update_subscription_status(self, is_premium: bool, days: int | None = None):
        """Обновляет отображение статуса подписки"""
        tokens = get_theme_tokens()
        if is_premium:
            self.sub_status_icon.setPixmap(qta.icon('fa5s.star', color='#ffc107').pixmap(18, 18))
            if days:
                self.sub_status_label.setText(f"Premium (осталось {days} дней)")
            else:
                self.sub_status_label.setText("Premium активен")
        else:
            self.sub_status_icon.setPixmap(qta.icon('fa5s.user', color=tokens.fg_faint).pixmap(18, 18))
            self.sub_status_label.setText("Free версия")
    
