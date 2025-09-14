# hosts/menu.py - Полная версия с визуальным выделением активных доменов
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QCheckBox, 
    QScrollArea, QWidget, QLabel, QFrame, QTreeWidget, QTreeWidgetItem,
    QDialogButtonBox, QMessageBox, QTabWidget, QGridLayout, QButtonGroup
)
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt6.QtGui import QFont, QIcon, QPalette, QColor, QBrush
from .proxy_domains import PROXY_DOMAINS
from log import log
from typing import Set, Dict, List

# Импортируем функции реестра
try:
    from config import get_active_hosts_domains, set_active_hosts_domains
except ImportError:
    log("Не удалось импортировать функции реестра для активных доменов", "⚠ WARNING")
    def get_active_hosts_domains(): return set()
    def set_active_hosts_domains(d): return False

# Категории доменов для удобной навигации
DOMAIN_CATEGORIES = {
    "🤖 ChatGPT & OpenAI": [
        "chatgpt.com",
        "ab.chatgpt.com",
        "auth.openai.com",
        "auth0.openai.com",
        "platform.openai.com",
        "cdn.oaistatic.com",
        "files.oaiusercontent.com",
        "cdn.auth0.com",
        "tcr9i.chat.openai.com",
        "webrtc.chatgpt.com",
        "android.chat.openai.com",
        "api.openai.com",
        "sora.com",
        "sora.chatgpt.com",
        "videos.openai.com",
        "us.posthog.com",
    ],
    
    "🧠 Google AI": [
        "gemini.google.com",
        "aistudio.google.com",
        "generativelanguage.googleapis.com",
        "alkalimakersuite-pa.clients6.google.com",
        "aitestkitchen.withgoogle.com",
        "aisandbox-pa.googleapis.com",
        "webchannel-alkalimakersuite-pa.clients6.google.com",
        "proactivebackend-pa.googleapis.com",
        "o.pki.goog",
        "labs.google",
        "notebooklm.google",
        "notebooklm.google.com",
    ],
    
    "🤖 Другие AI сервисы": [
        "claude.ai",
        "copilot.microsoft.com",
        "www.bing.com",
        "sydney.bing.com",
        "edgeservices.bing.com",
        "rewards.bing.com",
        "xsts.auth.xboxlive.com",
        "grok.com",
        "assets.grok.com",
        "accounts.x.ai",
        "elevenlabs.io",
        "api.us.elevenlabs.io",
        "elevenreader.io",
        "codeium.com",
        "inference.codeium.com",
        "api.individual.githubcopilot.com",
        "proxy.individual.githubcopilot.com",
        "deepl.com",
        "www.deepl.com",
        "s.deepl.com",
        "ita-free.www.deepl.com",
        "experimentation.deepl.com",
        "w.deepl.com",
        "login-wall.deepl.com",
        "gtm.deepl.com",
        "checkout.www.deepl.com",
    ],
    
    "📘 Facebook & Instagram": [
        "facebook.com",
        "www.facebook.com",
        "static.xx.fbcdn.net",
        "external-hel3-1.xx.fbcdn.net",
        "scontent-hel3-1.xx.fbcdn.net",
        "www.instagram.com",
        "instagram.com",
        "scontent.cdninstagram.com",
        "scontent-hel3-1.cdninstagram.com",
        "static.cdninstagram.com",
        "b.i.instagram.com",
        "z-p42-chat-e2ee-ig.facebook.com",
        "threads.com",
        "www.threads.com",
    ],
    
    "🎵 Spotify": [
        "api.spotify.com",
        "xpui.app.spotify.com",
        "appresolve.spotify.com",
        "login5.spotify.com",
        "gew1-spclient.spotify.com",
        "gew1-dealer.spotify.com",
        "spclient.wg.spotify.com",
        "api-partner.spotify.com",
        "aet.spotify.com",
        "www.spotify.com",
        "accounts.spotify.com",
        "spotifycdn.com",
        "open-exp.spotifycdn.com",
        "www-growth.scdn.co",
        "login.app.spotify.com",
        "encore.scdn.co",
        "accounts.scdn.co",
        "ap-gew1.spotify.com",
    ],
    
    "🎵 SoundCloud": [
        "soundcloud.com",
        "style.sndcdn.com",
        "a-v2.sndcdn.com",
        "secure.sndcdn.com",
    ],
    
    "🎮 Twitch": [
        "usher.ttvnw.net",
    ],
    
    "📺 Стриминговые сервисы": [
        "www.netflix.com",
        "netflix.com",
        "www.hulu.com",
        "hulu.com",
    ],
    
    "📝 Продуктивность": [
        "www.notion.so",
        "notion.so",
        "calendar.notion.so",
        "www.canva.com",
        "datalore.jetbrains.com",
        "plugins.jetbrains.com",
    ],
    
    "🔒 Приватность": [
        "protonmail.com",
        "mail.proton.me",
    ],
    
    "💻 Разработка": [
        "autodesk.com",
        "accounts.autodesk.com",
        "www.intel.com",
        "www.dell.com",
        "developer.nvidia.com",
        "www.aomeitech.com",
        "www.elgato.com",
    ],
    
    "🎯 Другие сервисы": [
        "www.tiktok.com",
        "truthsocial.com",
        "static-assets-1.truthsocial.com",
        "anilib.me",
        "ntc.party",
        "pump.fun",
        "frontend-api-v3.pump.fun",
        "images.pump.fun",
        "swap-api.pump.fun",
        "rutracker.org",
        "static.rutracker.cc",
    ],
    
    "🚫 Блокировка (казино)": [
        "1xbet.kz",
        "1xbet.com",
        "1xlite-06044.top",
        "only-fans.uk",
        "only-fans.me",
        "only-fans.wtf",
    ]
}

# Предустановленные наборы для быстрого выбора
PRESET_COLLECTIONS = {
    "AI Сервисы": [
        "chatgpt.com", "auth.openai.com", "platform.openai.com", "api.openai.com",
        "gemini.google.com", "aistudio.google.com", "notebooklm.google.com",
        "claude.ai", "copilot.microsoft.com", "www.bing.com",
        "grok.com", "deepl.com", "elevenlabs.io"
    ],
    "Социальные сети": [
        "facebook.com", "www.facebook.com", "instagram.com", "www.instagram.com",
        "threads.com", "www.threads.com", "www.tiktok.com", "truthsocial.com"
    ],
    "Музыка и медиа": [
        "spotify.com", "www.spotify.com", "api.spotify.com", "accounts.spotify.com",
        "soundcloud.com", "netflix.com", "hulu.com"
    ],
    "Работа и учеба": [
        "notion.so", "www.notion.so", "canva.com", "datalore.jetbrains.com",
        "plugins.jetbrains.com", "autodesk.com"
    ],
    "Минимальный набор": [
        "chatgpt.com", "instagram.com", "spotify.com", "notion.so"
    ]
}


class ModernButton(QPushButton):
    """Современная кнопка с анимацией"""
    def __init__(self, text, parent=None, primary=False):
        super().__init__(text, parent)
        self.primary = primary
        self._animation = QPropertyAnimation(self, b"color")
        self._animation.setDuration(200)
        self.setMinimumHeight(32)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
    def enterEvent(self, event):
        super().enterEvent(event)
        self.setProperty("hover", True)
        self.style().polish(self)
        
    def leaveEvent(self, event):
        super().leaveEvent(event)
        self.setProperty("hover", False)
        self.style().polish(self)


class StatusButton(QPushButton):
    """Кнопка с индикацией статуса"""
    def __init__(self, text, parent=None, is_active=False):
        super().__init__(text, parent)
        self.is_active = is_active
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setCheckable(True)
        self.setMinimumHeight(36)
        self.update_style()
        
    def set_active(self, active):
        """Устанавливает активное состояние"""
        self.is_active = active
        self.setProperty("is_active", active)
        self.update_style()
        
    def update_style(self):
        """Обновляет стиль в зависимости от состояния"""
        if self.is_active:
            self.setToolTip("✅ Сервис активен в hosts")
        else:
            self.setToolTip("➕ Нажмите для добавления в hosts")
        self.style().polish(self)


class CompactTreeWidget(QTreeWidget):
    """Компактный виджет дерева с современным стилем"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderHidden(True)
        self.setRootIsDecorated(True)
        self.setAnimated(True)
        self.setIndentation(15)
        self.setAlternatingRowColors(False)
        self.setUniformRowHeights(True)


class HostsSelectorDialog(QDialog):
    """Современный диалог выбора доменов с индикацией активных"""
    
    def __init__(self, parent=None, current_active_domains=None):
        super().__init__(parent)
        # Получаем активные домены из hosts файла
        self.current_active_domains = current_active_domains or set()
        # Получаем сохраненные активные домены из реестра
        self.saved_active_domains = get_active_hosts_domains()
        # Объединяем для полной картины
        self.all_active_domains = self.current_active_domains | self.saved_active_domains
        
        self.selected_domains = set()
        self.service_buttons = {}  # Словарь для хранения кнопок сервисов
        self.is_dark_theme = self._detect_dark_theme()
        
        # Переменные для Adobe
        self.adobe_callback = None
        self.is_adobe_active = False
        
        self.setWindowTitle("🌐 Менеджер разблокировки")
        self.setModal(True)
        self.setMinimumSize(650, 650)
        self.resize(720, 650)
        
        self.init_ui()
        self.apply_modern_styles()
        self.load_domains()
        self.update_service_buttons_state()
        
    def _detect_dark_theme(self):
        """Определяет, используется ли темная тема"""
        palette = self.palette()
        bg_color = palette.color(QPalette.ColorRole.Window)
        return bg_color.lightness() < 128
        
    def init_ui(self):
        """Инициализация интерфейса"""
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        # Компактный заголовок с индикаторами
        header_layout = QHBoxLayout()
        title_label = QLabel("Управление разблокировкой сервисов")
        title_label.setStyleSheet(f"""
            font-size: 14pt;
            font-weight: 600;
            color: {'#ffffff' if self.is_dark_theme else '#2c3e50'};
        """)
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        # Индикаторы статуса
        self.active_indicator = QLabel("● Активно: 0")
        self.active_indicator.setStyleSheet(f"""
            QLabel {{
                color: #3182ce;
                font-weight: bold;
                font-size: 10pt;
                padding: 0 5px;
            }}
        """)
        header_layout.addWidget(self.active_indicator)
        
        self.selected_indicator = QLabel("○ Выбрано: 0")
        self.selected_indicator.setStyleSheet(f"""
            QLabel {{
                color: {'#a0aec0' if self.is_dark_theme else '#718096'};
                font-weight: bold;
                font-size: 10pt;
                padding: 0 5px;
            }}
        """)
        header_layout.addWidget(self.selected_indicator)
        
        main_layout.addLayout(header_layout)
        
        # Информация о статусах
        info_frame = QFrame()
        info_frame.setStyleSheet(f"""
            QFrame {{
                background: {'#2d3748' if self.is_dark_theme else '#f0f9ff'};
                border: 1px solid {'#4a5568' if self.is_dark_theme else '#90cdf4'};
                border-radius: 6px;
                padding: 8px;
            }}
        """)
        info_layout = QHBoxLayout()
        info_layout.setSpacing(15)
        
        # Легенда статусов
        legend_items = [
            ("🔵", "Активно в hosts", "#3182ce"),
            ("⚪", "Не активно", "#718096"),
            ("✅", "Будет добавлено", "#48bb78"),
            ("❌", "Будет удалено", "#f56565")
        ]
        
        for icon, text, color in legend_items:
            item_layout = QHBoxLayout()
            item_layout.setSpacing(4)
            
            icon_label = QLabel(icon)
            icon_label.setStyleSheet(f"font-size: 12pt;")
            item_layout.addWidget(icon_label)
            
            text_label = QLabel(text)
            text_label.setStyleSheet(f"""
                color: {color};
                font-size: 9pt;
                font-weight: 500;
            """)
            item_layout.addWidget(text_label)
            
            info_layout.addLayout(item_layout)
            
        info_layout.addStretch()
        info_frame.setLayout(info_layout)
        main_layout.addWidget(info_frame)
        
        # Тонкая линия разделитель
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet(f"""
            QFrame {{
                border: 0px;
                background-color: {'#4a5568' if self.is_dark_theme else '#e0e0e0'};
                max-height: 1px;
            }}
        """)
        main_layout.addWidget(line)
        
        # Компактные табы
        self.tab_widget = QTabWidget()
        self.tab_widget.setDocumentMode(True)

        # Кнопки управления
        control_layout = QHBoxLayout()
        control_layout.setSpacing(8)
        
        select_all_btn = QPushButton("Выбрать все")
        select_all_btn.clicked.connect(self.select_all)
        control_layout.addWidget(select_all_btn)
        
        clear_btn = QPushButton("Очистить выбор")
        clear_btn.clicked.connect(self.deselect_all)
        control_layout.addWidget(clear_btn)
        
        control_layout.addStretch()
        main_layout.addLayout(control_layout)  # ← ИСПРАВЛЕНО: используем addLayout вместо addWidget

        # Вкладка с быстрым выбором
        quick_tab = self.create_quick_select_tab()
        self.tab_widget.addTab(quick_tab, "⚡ Быстрый выбор")
        
        # Вкладка с деревом категорий
        tree_tab = self.create_tree_tab()
        self.tab_widget.addTab(tree_tab, "📋 Все домены")
        
        main_layout.addWidget(self.tab_widget)
        
        # Adobe секция
        self.adobe_section = self.create_adobe_section()
        main_layout.addWidget(self.adobe_section)
        
        # Кнопки диалога
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        # Кнопка открытия hosts
        self.hosts_btn = QPushButton("📝 Hosts")
        self.hosts_btn.setToolTip("Открыть файл hosts")
        self.hosts_btn.clicked.connect(self.open_hosts_file)
        button_layout.addWidget(self.hosts_btn)
        
        # Кнопка сброса
        self.reset_btn = QPushButton("🔄 Сбросить")
        self.reset_btn.setToolTip("Вернуть текущее состояние")
        self.reset_btn.clicked.connect(self.reset_to_current)
        button_layout.addWidget(self.reset_btn)
        
        button_layout.addStretch()
        
        # Основные кнопки
        self.cancel_btn = QPushButton("Отмена")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        self.apply_btn = QPushButton("✅ Применить изменения")
        self.apply_btn.setObjectName("apply_btn")
        self.apply_btn.clicked.connect(self.accept)
        self.apply_btn.setDefault(True)
        button_layout.addWidget(self.apply_btn)
        
        main_layout.addLayout(button_layout)
        self.setLayout(main_layout)

    def create_quick_select_tab(self):
        """Создает вкладку быстрого выбора с индикацией статуса"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(8)
        
        # Сетка популярных сервисов
        services_grid = QGridLayout()
        services_grid.setSpacing(8)
        
        services = [
            ("🤖 ChatGPT", self.get_service_domains("chatgpt"), 0, 0),
            ("🧠 Gemini", self.get_service_domains("gemini"), 0, 1),
            ("🤖 Claude", ["claude.ai"], 0, 2),
            ("📱 Instagram", self.get_service_domains("instagram"), 1, 0),
            ("📘 Facebook", self.get_service_domains("facebook"), 1, 1),
            ("🎵 Spotify", self.get_service_domains("spotify"), 1, 2),
            ("📝 Notion", self.get_service_domains("notion"), 2, 0),
            ("🎥 Twitch", ["usher.ttvnw.net"], 2, 1),
            ("🔄 DeepL", self.get_service_domains("deepl"), 2, 2),
        ]
        
        for name, domains, row, col in services:
            # Проверяем, активен ли хотя бы один домен сервиса
            is_active = any(d in self.all_active_domains for d in domains)
            
            btn = StatusButton(name, is_active=is_active)
            btn.clicked.connect(lambda checked, d=domains, b=btn: self.toggle_service(d, b))
            
            # Сохраняем кнопку для последующего обновления
            self.service_buttons[name] = (btn, domains)
            
            services_grid.addWidget(btn, row, col)
            
        layout.addLayout(services_grid)
        
        # Разделитель
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet(f"""
            QFrame {{
                border: none;
                background: {'#4a5568' if self.is_dark_theme else '#e0e0e0'};
                max-height: 1px;
                margin: 10px 0;
            }}
        """)
        layout.addWidget(separator)
        
        # Предустановленные наборы
        presets_label = QLabel("Готовые наборы:")
        presets_label.setStyleSheet(f"""
            font-weight: 600;
            color: {'#a0aec0' if self.is_dark_theme else '#7f8c8d'};
            font-size: 9pt;
        """)
        layout.addWidget(presets_label)
        
        presets_layout = QHBoxLayout()
        presets_layout.setSpacing(8)
        
        presets = [
            ("🎯 Минимум", ["chatgpt.com", "instagram.com", "spotify.com"]),
            ("🤖 Все AI", self.get_all_ai_domains()),
            ("📱 Соцсети", self.get_all_social_domains()),
            ("✨ Популярное", self.get_popular_domains()),
        ]
        
        for preset_name, domains in presets:
            btn = QPushButton(preset_name)
            btn.clicked.connect(lambda checked, d=domains: self.apply_preset_domains(d))
            presets_layout.addWidget(btn)
            
        layout.addLayout(presets_layout)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
        
    def create_tree_tab(self):
        """Создает вкладку с деревом"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(5)
        
        # Дерево доменов
        self.tree_widget = CompactTreeWidget()
        self.tree_widget.itemChanged.connect(self.on_item_changed)
        layout.addWidget(self.tree_widget)
        
        widget.setLayout(layout)
        return widget
        
    def create_adobe_section(self):
        """Создает компактную секцию Adobe"""
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background: {'#2d3748' if self.is_dark_theme else '#f8f9fa'};
                border: 1px solid {'#4a5568' if self.is_dark_theme else '#dee2e6'};
                border-radius: 6px;
                padding: 8px;
            }}
        """)
        
        layout = QHBoxLayout()
        layout.setSpacing(10)
        
        icon_label = QLabel("🔒")
        icon_label.setStyleSheet("font-size: 16pt;")
        layout.addWidget(icon_label)
        
        text_label = QLabel("Adobe блокировка")
        text_label.setStyleSheet(f"""
            font-weight: 600;
            color: {'#e2e8f0' if self.is_dark_theme else '#495057'};
        """)
        layout.addWidget(text_label)
        
        layout.addStretch()
        
        self.adobe_btn = QPushButton("Настроить")
        self.adobe_btn.clicked.connect(self.show_adobe_menu)
        layout.addWidget(self.adobe_btn)
        
        frame.setLayout(layout)
        return frame
        
    def apply_modern_styles(self):
        """Применяет современные стили с учетом активных доменов"""
        # Основные цвета
        if self.is_dark_theme:
            bg_primary = "#1a202c"
            bg_secondary = "#2d3748"
            bg_hover = "#4a5568"
            text_primary = "#e2e8f0"
            text_secondary = "#a0aec0"
            accent = "#4299e1"
            accent_hover = "#3182ce"
            active_bg = "#2b6cb0"  # Синий для активных
            inactive_bg = "#4a5568"  # Серый для неактивных
        else:
            bg_primary = "#ffffff"
            bg_secondary = "#f7fafc"
            bg_hover = "#edf2f7"
            text_primary = "#2d3748"
            text_secondary = "#718096"
            accent = "#3182ce"
            accent_hover = "#2c5282"
            active_bg = "#3182ce"  # Синий для активных
            inactive_bg = "#cbd5e0"  # Серый для неактивных
            
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {bg_primary};
            }}
            
            QTabWidget {{
                border: 0px;
            }}
            
            QTabWidget::pane {{
                border: 0px; /* ← убираем границу полностью */
                background-color: {bg_secondary};
                padding: 10px;
            }}
            
            QTabBar::tab {{
                background-color: {bg_secondary};
                color: {text_secondary};
                padding: 8px 16px;
                margin-right: 4px;
                font-weight: 500;
                border: 0px;  /* ← добавляем это */
            }}
            
            QTabBar::tab:selected {{
                background-color: {bg_primary};
                color: {text_primary};
                font-weight: 600;
                border: none;  /* ← добавляем это */
            }}
            
            QTabBar::tab:hover {{
                background-color: {bg_hover};
            }}
            
            QPushButton {{
                background-color: {bg_secondary};
                color: {text_primary};
                border: 1px solid {bg_hover};
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: 500;
                min-width: 80px;
            }}
            
            QPushButton:hover {{
                background-color: {bg_hover};
                border-color: {accent};
            }}
            
            QPushButton:pressed {{
                background-color: {bg_hover};
            }}
            
            QPushButton#apply_btn {{
                background-color: {accent};
                color: white;
                border: none;
            }}
            
            QPushButton#apply_btn:hover {{
                background-color: {accent_hover};
            }}
            
            StatusButton {{
                border: 2px solid {inactive_bg};
                background-color: {bg_secondary};
                color: {text_primary};
            }}
            
            StatusButton[is_active="true"] {{
                border: 2px solid {active_bg};
                background-color: {active_bg};
                color: white;
                font-weight: 600;
            }}
            
            StatusButton:checked {{
                background-color: {accent};
                color: white;
                border-color: {accent};
            }}
            
            QTreeWidget {{
                background-color: {bg_secondary};
                border: 0px solid {bg_hover};
                border-radius: 6px;
                outline: none;
                color: {text_primary};
            }}
            
            QTreeWidget::item {{
                padding: 4px;
                border-radius: 4px;
            }}
            
            QTreeWidget::item:hover {{
                background-color: {bg_hover};
            }}
            
            QTreeWidget::item:selected {{
                background-color: {accent};
                color: white;
            }}
            
            QTreeWidget::indicator {{
                width: 16px;
                height: 16px;
            }}
            
            QTreeWidget::indicator:unchecked {{
                border: 2px solid {text_secondary};
                background-color: transparent;
                border-radius: 3px;
            }}
            
            QTreeWidget::indicator:checked {{
                border: 2px solid {accent};
                background-color: {accent};
                border-radius: 3px;
            }}
            
            QLabel {{
                color: {text_primary};
            }}
        """)
        
    def load_domains(self):
        """Загружает домены в дерево с индикацией активных"""
        all_domains = set(PROXY_DOMAINS.keys())
        categorized = set()
        
        for category_name, category_domains in DOMAIN_CATEGORIES.items():
            existing = [d for d in category_domains if d in all_domains]
            if existing:
                # Подсчитываем активные в категории
                active_count = len([d for d in existing if d in self.all_active_domains])
                category_text = f"{category_name} ({active_count}/{len(existing)})"
                
                category_item = QTreeWidgetItem([category_text])
                category_item.setFlags(category_item.flags() | Qt.ItemFlag.ItemIsAutoTristate)
                
                # Устанавливаем шрифт для категории
                font = QFont()
                font.setBold(True)
                category_item.setFont(0, font)
                
                # Цвет категории в зависимости от активных элементов
                if active_count > 0:
                    category_item.setForeground(0, QBrush(QColor("#3182ce")))
                
                for domain in existing:
                    # Индикатор статуса
                    if domain in self.all_active_domains:
                        domain_text = f"🔵 {domain}"
                    else:
                        domain_text = f"⚪ {domain}"
                        
                    domain_item = QTreeWidgetItem([domain_text])
                    domain_item.setFlags(domain_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                    
                    # Устанавливаем чекбокс в зависимости от текущего состояния
                    if domain in self.all_active_domains:
                        domain_item.setCheckState(0, Qt.CheckState.Checked)
                        # Выделяем активные домены цветом
                        domain_item.setForeground(0, QBrush(QColor("#3182ce")))
                    else:
                        domain_item.setCheckState(0, Qt.CheckState.Unchecked)
                    
                    domain_item.setData(0, Qt.ItemDataRole.UserRole, domain)
                    category_item.addChild(domain_item)
                    categorized.add(domain)
                
                self.tree_widget.addTopLevelItem(category_item)
                # Раскрываем категории с активными доменами
                if active_count > 0:
                    category_item.setExpanded(True)
                else:
                    category_item.setExpanded(False)
        
        # Некатегоризированные
        other = all_domains - categorized
        if other:
            active_count = len([d for d in other if d in self.all_active_domains])
            other_text = f"🎯 Другие ({active_count}/{len(other)})"
            other_item = QTreeWidgetItem([other_text])
            other_item.setFlags(other_item.flags() | Qt.ItemFlag.ItemIsAutoTristate)
            
            font = QFont()
            font.setBold(True)
            other_item.setFont(0, font)
            
            for domain in sorted(other):
                if domain in self.all_active_domains:
                    domain_text = f"🔵 {domain}"
                else:
                    domain_text = f"⚪ {domain}"
                    
                domain_item = QTreeWidgetItem([domain_text])
                domain_item.setFlags(domain_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                
                if domain in self.all_active_domains:
                    domain_item.setCheckState(0, Qt.CheckState.Checked)
                    domain_item.setForeground(0, QBrush(QColor("#3182ce")))
                else:
                    domain_item.setCheckState(0, Qt.CheckState.Unchecked)
                
                domain_item.setData(0, Qt.ItemDataRole.UserRole, domain)
                other_item.addChild(domain_item)
            
            self.tree_widget.addTopLevelItem(other_item)
            other_item.setExpanded(active_count > 0)
        
        self.update_indicators()
        
    def update_indicators(self):
        """Обновляет индикаторы статуса"""
        active_count = len(self.all_active_domains)
        selected_count = len(self.get_checked_domains())
        
        self.active_indicator.setText(f"● Активно: {active_count}")
        self.selected_indicator.setText(f"○ Выбрано: {selected_count}")
        
        # Обновляем текст кнопки применения
        if selected_count != active_count:
            if selected_count > active_count:
                self.apply_btn.setText(f"✅ Добавить {selected_count - active_count} доменов")
            elif selected_count < active_count:
                self.apply_btn.setText(f"❌ Удалить {active_count - selected_count} доменов")
            self.apply_btn.setEnabled(True)
        else:
            # Проверяем, есть ли различия в составе
            selected_domains = self.get_checked_domains()
            if selected_domains != self.all_active_domains:
                self.apply_btn.setText("🔄 Применить изменения")
                self.apply_btn.setEnabled(True)
            else:
                self.apply_btn.setText("✅ Изменений нет")
                self.apply_btn.setEnabled(False)
        
    def update_service_buttons_state(self):
        """Обновляет состояние кнопок сервисов"""
        for name, (btn, domains) in self.service_buttons.items():
            # Проверяем статус каждого сервиса
            is_active = any(d in self.all_active_domains for d in domains)
            is_selected = any(d in self.get_checked_domains() for d in domains)
            
            btn.set_active(is_active)
            btn.setChecked(is_selected)
            
    def on_item_changed(self, item, column):
        """Обработчик изменения состояния элемента"""
        # Обновляем текст элемента с индикатором
        if item.childCount() == 0:  # Это домен, не категория
            domain = item.data(0, Qt.ItemDataRole.UserRole)
            if domain:
                is_checked = item.checkState(0) == Qt.CheckState.Checked
                is_active = domain in self.all_active_domains
                
                # Обновляем текст с правильным индикатором
                if is_active:
                    if is_checked:
                        item.setText(0, f"🔵 {domain}")
                    else:
                        item.setText(0, f"❌ {domain}")  # Будет удален
                else:
                    if is_checked:
                        item.setText(0, f"✅ {domain}")  # Будет добавлен
                    else:
                        item.setText(0, f"⚪ {domain}")
                        
        self.update_indicators()
        self.update_service_buttons_state()
        
    def reset_to_current(self):
        """Сбрасывает выбор к текущему состоянию hosts"""
        # Восстанавливаем состояние из all_active_domains
        for i in range(self.tree_widget.topLevelItemCount()):
            category = self.tree_widget.topLevelItem(i)
            for j in range(category.childCount()):
                item = category.child(j)
                domain = item.data(0, Qt.ItemDataRole.UserRole)
                if domain:
                    if domain in self.all_active_domains:
                        item.setCheckState(0, Qt.CheckState.Checked)
                    else:
                        item.setCheckState(0, Qt.CheckState.Unchecked)
        
        self.update_indicators()
        self.update_service_buttons_state()
        
    def toggle_service(self, domains, button):
        """Переключает выбор сервиса"""
        # Определяем текущее состояние
        all_checked = all(self.is_domain_checked(d) for d in domains if d in PROXY_DOMAINS)
        
        # Переключаем
        for domain in domains:
            if domain in PROXY_DOMAINS:
                self.set_domain_checked(domain, not all_checked)
        
        self.update_indicators()
        self.update_service_buttons_state()
        
    def is_domain_checked(self, domain):
        """Проверяет, отмечен ли домен"""
        for i in range(self.tree_widget.topLevelItemCount()):
            category = self.tree_widget.topLevelItem(i)
            for j in range(category.childCount()):
                item = category.child(j)
                if item.data(0, Qt.ItemDataRole.UserRole) == domain:
                    return item.checkState(0) == Qt.CheckState.Checked
        return False
        
    def set_domain_checked(self, domain, checked):
        """Устанавливает состояние домена в дереве"""
        for i in range(self.tree_widget.topLevelItemCount()):
            category = self.tree_widget.topLevelItem(i)
            for j in range(category.childCount()):
                item = category.child(j)
                if item.data(0, Qt.ItemDataRole.UserRole) == domain:
                    item.setCheckState(0, Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
                    return
                    
    def apply_preset_domains(self, domains):
        """Применяет набор доменов"""
        # Сначала очищаем все
        self.deselect_all()
        # Затем выбираем нужные
        for domain in domains:
            if domain in PROXY_DOMAINS:
                self.set_domain_checked(domain, True)
        self.update_indicators()
        self.update_service_buttons_state()
        
    def select_all(self):
        """Выбирает все домены"""
        for i in range(self.tree_widget.topLevelItemCount()):
            self.tree_widget.topLevelItem(i).setCheckState(0, Qt.CheckState.Checked)
        self.update_indicators()
        self.update_service_buttons_state()
        
    def deselect_all(self):
        """Снимает выбор со всех доменов"""
        for i in range(self.tree_widget.topLevelItemCount()):
            self.tree_widget.topLevelItem(i).setCheckState(0, Qt.CheckState.Unchecked)
        self.update_indicators()
        self.update_service_buttons_state()
        
    def get_checked_domains(self) -> Set[str]:
        """Возвращает множество выбранных доменов"""
        checked = set()
        for i in range(self.tree_widget.topLevelItemCount()):
            category = self.tree_widget.topLevelItem(i)
            for j in range(category.childCount()):
                item = category.child(j)
                if item.checkState(0) == Qt.CheckState.Checked:
                    domain = item.data(0, Qt.ItemDataRole.UserRole)
                    if domain:
                        checked.add(domain)
        return checked
        
    def get_selected_domains(self) -> Set[str]:
        """Возвращает выбранные домены"""
        selected = self.get_checked_domains()
        # Сохраняем в реестр для следующего раза
        set_active_hosts_domains(selected)
        return selected
        
    # Вспомогательные методы для получения доменов
    def get_service_domains(self, service_name):
        """Получает домены для сервиса"""
        domains = []
        for domain in PROXY_DOMAINS.keys():
            if service_name.lower() in domain.lower():
                domains.append(domain)
        return domains[:5]  # Ограничиваем для компактности
        
    def get_all_ai_domains(self):
        """Получает все AI домены"""
        ai_domains = []
        for cat in ["🤖 ChatGPT & OpenAI", "🧠 Google AI", "🤖 Другие AI сервисы"]:
            if cat in DOMAIN_CATEGORIES:
                ai_domains.extend([d for d in DOMAIN_CATEGORIES[cat] if d in PROXY_DOMAINS])
        return ai_domains
        
    def get_all_social_domains(self):
        """Получает все домены соцсетей"""
        if "📘 Facebook & Instagram" in DOMAIN_CATEGORIES:
            return [d for d in DOMAIN_CATEGORIES["📘 Facebook & Instagram"] if d in PROXY_DOMAINS]
        return []
        
    def get_popular_domains(self):
        """Получает популярные домены"""
        return ["chatgpt.com", "instagram.com", "spotify.com", 
                "notion.so", "claude.ai", "gemini.google.com"]
    
    # Adobe методы
    def add_adobe_section(self, is_adobe_active, adobe_callback):
        """Устанавливает callback для Adobe секции"""
        self.adobe_callback = adobe_callback
        self.is_adobe_active = is_adobe_active
        
        # Обновляем текст кнопки Adobe в зависимости от статуса
        if hasattr(self, 'adobe_btn'):
            if is_adobe_active:
                self.adobe_btn.setText("🔓 Отключено")
                self.adobe_btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {'#dc3545' if not self.is_dark_theme else '#991b1b'};
                        color: white;
                        border: none;
                        padding: 8px 16px;
                        border-radius: 6px;
                        font-weight: 500;
                    }}
                    QPushButton:hover {{
                        background-color: {'#c82333' if not self.is_dark_theme else '#7f1d1d'};
                    }}
                """)
            else:
                self.adobe_btn.setText("🔒 Включить")
                self.adobe_btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {'#28a745' if not self.is_dark_theme else '#166534'};
                        color: white;
                        border: none;
                        padding: 8px 16px;
                        border-radius: 6px;
                        font-weight: 500;
                    }}
                    QPushButton:hover {{
                        background-color: {'#218838' if not self.is_dark_theme else '#14532d'};
                    }}
                """)

    def show_adobe_menu(self):
        """Показывает меню Adobe с учетом текущего состояния"""
        if hasattr(self, 'is_adobe_active'):
            if self.is_adobe_active:
                # Adobe активно, предлагаем отключить
                reply = QMessageBox.question(
                    self,
                    "Adobe блокировка",
                    "Блокировка Adobe активна.\n\nОтключить блокировку серверов Adobe?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.Yes:
                    if hasattr(self, 'adobe_callback'):
                        self.adobe_callback(False)
                        # Обновляем состояние кнопки
                        self.is_adobe_active = False
                        self.add_adobe_section(False, self.adobe_callback)
            else:
                # Adobe не активно, предлагаем включить
                reply = QMessageBox.question(
                    self,
                    "Adobe блокировка", 
                    "Включить блокировку серверов активации Adobe?\n\n"
                    "Это заблокирует:\n"
                    "• Серверы активации\n"
                    "• Проверку лицензий\n"
                    "• Обновления Adobe\n\n"
                    "⚠️ После применения перезапустите приложения Adobe!",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.Yes:
                    if hasattr(self, 'adobe_callback'):
                        self.adobe_callback(True)
                        # Обновляем состояние кнопки
                        self.is_adobe_active = True
                        self.add_adobe_section(True, self.adobe_callback)
        else:
            # Если состояние не установлено, показываем информацию
            self.show_adobe_info()

    def show_adobe_info(self):
        """Показывает информацию об Adobe"""
        QMessageBox.information(
            self,
            "Adobe блокировка",
            "Блокировка серверов активации Adobe позволяет:\n\n"
            "• Заблокировать проверку лицензий\n"
            "• Предотвратить деактивацию программ\n"
            "• Работать в офлайн режиме\n\n"
            "⚠️ Используйте только для тестирования!"
        )
        
    def open_hosts_file(self):
        """Открывает файл hosts"""
        try:
            import ctypes
            import os
            hosts_path = r"C:\Windows\System32\drivers\etc\hosts"
            
            if os.path.exists(hosts_path):
                ctypes.windll.shell32.ShellExecuteW(
                    None, "runas", "notepad.exe", hosts_path, None, 1
                )
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось открыть hosts: {str(e)}")
            
    def accept(self):
        """Обработчик применения"""
        self.selected_domains = self.get_selected_domains()
        
        if not self.selected_domains and self.all_active_domains:
            reply = QMessageBox.question(
                self,
                "Подтверждение",
                f"Вы собираетесь удалить все {len(self.all_active_domains)} активных доменов из hosts файла.\n\n"
                "Продолжить?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                return
                
        super().accept()