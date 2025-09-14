from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTextBrowser, QPushButton, QLabel
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QDesktopServices
from PyQt6.QtCore import QUrl

class PremiumDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Premium функции Zapret")
        self.setModal(True)
        self.setMinimumSize(700, 600)
        
        # Основной layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Заголовок
        title = QLabel("Premium функции")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Текст с информацией - используем QTextBrowser вместо QTextEdit
        info_text = QTextBrowser()  # ← ИЗМЕНЕНО
        info_text.setReadOnly(True)
        info_text.setOpenExternalLinks(False)  # Отключаем автоматическое открытие
        info_text.setHtml("""
        <style>
            body { font-family: Arial, sans-serif; line-height: 1.6; }
            h2 { color: #0077ff; margin-top: 20px; }
            h3 { color: #333; margin-top: 15px; }
            .highlight { background-color: #7a5d00; padding: 10px; border-radius: 5px; margin: 10px 0; }
            .premium-badge { 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 3px 8px;
                border-radius: 3px;
                font-weight: bold;
            }
            ul { margin-left: 20px; }
            li { margin: 5px 0; }
        </style>
        
        <p><b>Zapret полностью бесплатная программа</b> и такой всегда будет оставаться. 
        Однако многие пользователи хотят отплатить нам за наш труд. И это правильно. 
        Мы даём такую <b>ДОБРОВОЛЬНУЮ</b> возможность всем нашим пользователям.</p>
        
        <div class="highlight">
        <p>⚠️ <b>Важно:</b> Все дополнительные функции являются необязательными и 
        НЕ влияют на работу программы - это наш принцип, которого мы придерживаемся 
        и всегда будем защищать.</p>
        </div>
        
        <p>Вы уже сильно экономите используя нашу программу вместо VPN!</p>
        
        <hr>
        
        <h2>🎯 Уровень "Запретик"</h2>
        <ul>
            <li>✨ Доступно дополнительные AMOLED темы + тема "РКН ТЯН"</li>
            <li>🏆 Плашка <span class="premium-badge">Premium</span> прямо в программе</li>
            <li>🎨 Доступно создание тем на заказ</li>
            <li>💬 Доступен элитный VIP чат с создателем</li>
            <li>🚀 Приоритетная техническая поддержка</li>
            <li>⚙️ Индивидуальная настройка под ваши нужды</li>
            <li><i>Дополнительные функции в следующих обновлениях...</i></li>
        </ul>
        
        <h3>Дополнительные темы:</h3>
        <p>AMOLED темы для экономии батареи и стильного внешнего вида, 
        а также эксклюзивная тема "РКН ТЯН"</p>
        
        <hr>
        
        <h2>🚀 Уровень "MasterVLESS"</h2>
        <p><b>Включает все функции уровня "Запретик" + дополнительно:</b></p>
        <ul>
            <li>🌐 Выдаёт личный VPN сервер через протокол VLESS</li>
            <li>🗺️ Обход всех GEO-ограничений (ChatGPT, Twitch и т.д.)</li>
            <li>⚡ Безлимитная скорость (почти не режется)</li>
            <li>🎮 Низкий пинг (подходит для игр)</li>
            <li>🤖 Доступны сервисы: deepl.com, все ИИ сервисы, notebooklm.google, 
                chatgpt.com, brawl stars и многое другое!</li>
            <li>📱 Безлимитное количество устройств (Windows, Android, iOS и т.д.)</li>
        </ul>
        
        <h3>Скорость интернета:</h3>
        <p>Скорость практически не режется, подходит для стриминга, 
        игр и загрузки больших файлов.</p>
        
        <hr>
        
        <div class="highlight" style="background-color: #004d12;">
        <p>💳 <b>Оплатить подписку Вы можете в нашем боте:</b><br>
        <a href="https://t.me/zapretvpns_bot">https://t.me/zapretvpns_bot</a><br>
        Там же доступны актуальные цены.</p>
        </div>
        """)
        
        # Обработка кликов по ссылкам
        info_text.anchorClicked.connect(self.open_link)
        
        layout.addWidget(info_text)
        
        # Кнопки действий
        button_layout = QVBoxLayout()
        button_layout.setSpacing(10)
        
        # Кнопка перехода к боту
        telegram_btn = QPushButton("🔗 Открыть Telegram бот для оплаты")
        telegram_btn.clicked.connect(lambda: self.open_link(QUrl("https://t.me/zapretvpns_bot")))
        telegram_btn.setMinimumHeight(40)
        telegram_btn.setStyleSheet("""
            QPushButton {
                background-color: rgb(0, 136, 204);
                color: white;
                border: none;
                border-radius: 5px;
                font-weight: bold;
                font-size: 11pt;
            }
            QPushButton:hover {
                background-color: rgb(0, 116, 174);
            }
            QPushButton:pressed {
                background-color: rgb(0, 96, 144);
            }
        """)
        button_layout.addWidget(telegram_btn)
        
        # Кнопка закрытия
        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.accept)
        close_btn.setMinimumHeight(35)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: rgb(100, 100, 100);
                color: white;
                border: none;
                border-radius: 5px;
                font-weight: bold;
                font-size: 10pt;
            }
            QPushButton:hover {
                background-color: rgb(80, 80, 80);
            }
            QPushButton:pressed {
                background-color: rgb(60, 60, 60);
            }
        """)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
    
    def open_link(self, url):
        """Открывает ссылку в браузере"""
        if isinstance(url, QUrl):
            QDesktopServices.openUrl(url)
        else:
            QDesktopServices.openUrl(QUrl(url))