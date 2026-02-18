# ui/pages/ipset_page.py
"""Страница управления IP-сетами"""

from PyQt6.QtCore import Qt, QTimer, QEvent
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QFrame)
from PyQt6.QtGui import QFont
import qtawesome as qta

try:
    from qfluentwidgets import StrongBodyLabel, BodyLabel, CaptionLabel, InfoBar
    _HAS_FLUENT_LABELS = True
except ImportError:
    StrongBodyLabel = QLabel; BodyLabel = QLabel; CaptionLabel = QLabel
    InfoBar = None
    _HAS_FLUENT_LABELS = False

from .base_page import BasePage
from ui.compat_widgets import SettingsCard, ActionButton
from ui.theme import get_theme_tokens
from log import log


class IpsetPage(BasePage):
    """Страница управления IP-сетами"""
    
    def __init__(self, parent=None):
        super().__init__("IPset", "Управление IP-адресами и подсетями", parent)
        self._applying_theme_styles = False
        self._theme_refresh_scheduled = False
        self._desc_label = None
        self._open_icon_label = None
        self._open_text_label = None
        self._build_ui()
        self._apply_theme()
        
    def _build_ui(self):
        """Строит UI страницы"""
        tokens = get_theme_tokens()
        
        # Описание
        desc_card = SettingsCard()
        desc = CaptionLabel(
            "IP-сеты содержат IP-адреса и подсети для обхода блокировок по IP.\n"
            "Используются когда блокировка происходит на уровне IP-адресов."
        )
        self._desc_label = desc
        desc.setStyleSheet(f"color: {tokens.fg_muted};")
        desc.setWordWrap(True)
        desc_card.add_widget(desc)
        self.layout.addWidget(desc_card)
        
        # Кнопки действий
        actions_card = SettingsCard("Действия")
        actions_layout = QVBoxLayout()
        actions_layout.setSpacing(8)
        
        # Открыть папку
        open_row = QWidget()
        open_layout = QHBoxLayout(open_row)
        open_layout.setContentsMargins(0, 0, 0, 0)
        
        open_icon = QLabel()
        self._open_icon_label = open_icon
        open_icon.setPixmap(qta.icon('fa5s.folder-open', color=tokens.accent_hex).pixmap(18, 18))
        open_layout.addWidget(open_icon)
        
        open_text = BodyLabel("Открыть папку IP-сетов")
        self._open_text_label = open_text
        open_text.setStyleSheet(f"color: {tokens.fg};")
        open_layout.addWidget(open_text, 1)
        
        self.open_ipset_btn = ActionButton("Открыть", "fa5s.external-link-alt")
        self.open_ipset_btn.setFixedHeight(32)
        self.open_ipset_btn.clicked.connect(self._open_ipset_folder)
        open_layout.addWidget(self.open_ipset_btn)
        
        actions_layout.addWidget(open_row)
        
        actions_card.add_layout(actions_layout)
        self.layout.addWidget(actions_card)
        
        # Информация о файлах
        info_card = SettingsCard("Информация")
        info_layout = QVBoxLayout()
        info_layout.setSpacing(8)
        
        self.files_info_label = CaptionLabel("Загрузка информации...")
        self.files_info_label.setStyleSheet(f"color: {tokens.fg_muted};")
        self.files_info_label.setWordWrap(True)
        info_layout.addWidget(self.files_info_label)
        
        info_card.add_layout(info_layout)
        self.layout.addWidget(info_card)
        
        # Загружаем информацию
        QTimer.singleShot(100, self._load_info)
        
        self.layout.addStretch()

    def _apply_theme(self) -> None:
        if self._applying_theme_styles:
            return
        self._applying_theme_styles = True
        try:
            tokens = get_theme_tokens()
            if self._desc_label is not None:
                self._desc_label.setStyleSheet(f"color: {tokens.fg_muted};")
            if self._open_icon_label is not None:
                self._open_icon_label.setPixmap(qta.icon('fa5s.folder-open', color=tokens.accent_hex).pixmap(18, 18))
            if self._open_text_label is not None:
                self._open_text_label.setStyleSheet(f"color: {tokens.fg};")
            if self.files_info_label is not None:
                self.files_info_label.setStyleSheet(f"color: {tokens.fg_muted};")
        finally:
            self._applying_theme_styles = False

    def _schedule_theme_refresh(self) -> None:
        if self._applying_theme_styles:
            return
        if self._theme_refresh_scheduled:
            return
        self._theme_refresh_scheduled = True
        QTimer.singleShot(0, self._on_debounced_theme_change)

    def _on_debounced_theme_change(self) -> None:
        self._theme_refresh_scheduled = False
        self._apply_theme()

    def changeEvent(self, event):  # noqa: N802 (Qt override)
        try:
            if event.type() in (QEvent.Type.StyleChange, QEvent.Type.PaletteChange):
                self._schedule_theme_refresh()
        except Exception:
            pass
        return super().changeEvent(event)
        
    def _open_ipset_folder(self):
        """Открывает папку IP-сетов"""
        try:
            from config import LISTS_FOLDER
            import os
            os.startfile(LISTS_FOLDER)
        except Exception as e:
            log(f"Ошибка открытия папки: {e}", "ERROR")
            if InfoBar is not None:
                InfoBar.error(title="Ошибка", content=f"Не удалось открыть папку:\n{e}", parent=self.window(), duration=5000)
            
    def _load_info(self):
        """Загружает информацию о файлах"""
        try:
            from config import LISTS_FOLDER
            import os
            
            if not os.path.exists(LISTS_FOLDER):
                self.files_info_label.setText("Папка не найдена")
                return
                
            # Ищем файлы с IP
            ipset_files = [f for f in os.listdir(LISTS_FOLDER) 
                          if f.endswith('.txt') and ('ip' in f.lower() or 'subnet' in f.lower())]
            
            total_ips = 0
            for f in ipset_files[:10]:
                try:
                    path = os.path.join(LISTS_FOLDER, f)
                    with open(path, 'r', encoding='utf-8', errors='ignore') as file:
                        total_ips += sum(1 for line in file if line.strip() and not line.startswith('#'))
                except:
                    pass
                    
            info = f"📁 Папка: {LISTS_FOLDER}\n"
            info += f"📄 IP-файлов: {len(ipset_files)}\n"
            info += f"🌐 Примерно IP/подсетей: {total_ips:,}"
            
            self.files_info_label.setText(info)
            
        except Exception as e:
            self.files_info_label.setText(f"Ошибка загрузки информации: {e}")
