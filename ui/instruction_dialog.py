from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton, QLabel
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

class InstructionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Инструкция по выбору пресета")
        self.setModal(True)
        self.setMinimumSize(600, 500)
        
        # Основной layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Заголовок
        title = QLabel("Как выбрать правильный пресет обхода блокировок")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Текст инструкции
        instruction_text = QTextEdit()
        instruction_text.setReadOnly(True)
        instruction_text.setHtml("""
        <h3>Рекомендации по выбору пресета:</h3>
        
        <p><b>1. Базовый пресет</b><br>
        Подходит для большинства пользователей. Обеспечивает стабильную работу 
        с минимальным влиянием на скорость интернета.</p>
        
        <p><b>2. Агрессивный пресет</b><br>
        Используйте если базовый пресет не работает. Может снизить скорость 
        соединения, но обходит более сложные блокировки.</p>
        
        <p><b>3. Максимальный пресет</b><br>
        Для самых сложных случаев блокировки. Значительно влияет на скорость, 
        но обходит практически все типы блокировок.</p>
        
        <p><b>4. Пользовательский пресет</b><br>
        Для опытных пользователей. Позволяет настроить параметры вручную.</p>
        
        <hr>
        
        <h3>Порядок действий:</h3>
        <ol>
            <li>Нажмите кнопку "Сменить пресет обхода блокировок"</li>
            <li>Выберите подходящий пресет из списка</li>
            <li>Нажмите "Применить"</li>
            <li>Перезапустите Zapret если он был запущен</li>
        </ol>
        
        <hr>
        
        <h3>Советы:</h3>
        <ul>
            <li>Начните с базового пресета</li>
            <li>Если сайты не открываются, попробуйте более агрессивный пресет</li>
            <li>После смены пресета обязательно перезапустите Zapret</li>
            <li>Проверьте работу с помощью кнопки "Тест соединения"</li>
        </ul>
        
        <p><i>Совет: для быстрого доступа к этой инструкции нажмите правой 
        кнопкой мыши на кнопку смены пресета.</i></p>
        """)
        layout.addWidget(instruction_text)
        
        # Кнопка закрытия
        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.accept)
        close_btn.setMinimumHeight(35)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: rgb(0, 119, 255);
                color: white;
                border: none;
                border-radius: 5px;
                font-weight: bold;
                font-size: 10pt;
            }
            QPushButton:hover {
                background-color: rgb(0, 100, 220);
            }
            QPushButton:pressed {
                background-color: rgb(0, 80, 180);
            }
        """)
        layout.addWidget(close_btn)