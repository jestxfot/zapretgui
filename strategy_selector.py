from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, 
                            QPushButton, QTextBrowser, QGroupBox, QSplitter)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont

from log import log
import os

class StrategySelector(QDialog):
    """Диалог для выбора стратегии с подробной информацией."""
    
    strategySelected = pyqtSignal(str, str)  # Сигнал: (strategy_id, strategy_name)
    
    def __init__(self, parent=None, strategy_manager=None, current_strategy_name=None):
        super().__init__(parent)
        self.strategy_manager = strategy_manager
        self.current_strategy_name = current_strategy_name
        self.selected_strategy_id = None
        self.selected_strategy_name = None
        
        self.setWindowTitle("Выбор стратегии обхода блокировок")
        self.resize(800, 500)  # Начальный размер окна
        
        self.init_ui()
        self.load_strategies()
        
        # Выбираем текущую стратегию, если она задана
        if current_strategy_name:
            self.select_strategy_by_name(current_strategy_name)
    
    def init_ui(self):
        """Инициализация интерфейса."""
        layout = QVBoxLayout(self)
        
        # Создаем разделитель (сплиттер)
        splitter = QSplitter(Qt.Horizontal)
        
        # Левая панель - список стратегий
        strategies_group = QGroupBox("Доступные стратегии")
        strategies_layout = QVBoxLayout(strategies_group)
        
        self.strategies_list = QListWidget()
        self.strategies_list.setMinimumWidth(250)
        self.strategies_list.currentRowChanged.connect(self.on_strategy_selected)
        strategies_layout.addWidget(self.strategies_list)
        
        # Кнопка обновления стратегий
        refresh_button = QPushButton("Обновить список стратегий")
        refresh_button.clicked.connect(self.refresh_strategies)
        strategies_layout.addWidget(refresh_button)
        
        # Правая панель - информация о стратегии
        info_group = QGroupBox("Информация о стратегии")
        info_layout = QVBoxLayout(info_group)
        
        # Заголовок стратегии
        self.strategy_title = QLabel("Выберите стратегию")
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(12)
        self.strategy_title.setFont(title_font)
        self.strategy_title.setAlignment(Qt.AlignCenter)
        info_layout.addWidget(self.strategy_title)
        
        # Детальная информация о стратегии
        self.strategy_info = QTextBrowser()
        self.strategy_info.setOpenExternalLinks(True)
        info_layout.addWidget(self.strategy_info)
        
        # Добавляем панели в сплиттер
        splitter.addWidget(strategies_group)
        splitter.addWidget(info_group)
        splitter.setSizes([250, 550])  # Начальное соотношение размеров
        
        layout.addWidget(splitter, 1)  # 1 - stretch factor
        
        # Кнопки внизу
        buttons_layout = QHBoxLayout()
        
        self.select_button = QPushButton("Выбрать стратегию")
        self.select_button.clicked.connect(self.accept)
        self.select_button.setEnabled(False)
        buttons_layout.addWidget(self.select_button)
        
        cancel_button = QPushButton("Отмена")
        cancel_button.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_button)
        
        layout.addLayout(buttons_layout)
    
    def load_strategies(self):
        """Загружает список стратегий."""
        self.strategies_list.clear()
        self.strategy_info.clear()
        self.strategy_title.setText("Выберите стратегию")
        self.select_button.setEnabled(False)
        
        try:
            if not self.strategy_manager:
                log("Менеджер стратегий не инициализирован", level="ERROR")
                self.strategy_info.setHtml("<p style='color:red'>Ошибка: менеджер стратегий не инициализирован</p>")
                return
            
            strategies = self.strategy_manager.get_strategies_list()
            if not strategies:
                log("Не удалось получить список стратегий", level="ERROR")
                self.strategy_info.setHtml("<p style='color:red'>Ошибка: не удалось получить список стратегий</p>")
                return
            
            # Сортируем стратегии по полю sort_order
            sorted_strategies = sorted(
                strategies.items(), 
                key=lambda x: (
                    # Первый критерий: sort_order (если есть)
                    x[1].get('sort_order', 999),
                    # Второй критерий: провайдер (если sort_order одинаковый)
                    x[1].get('provider', 'zzzz'),
                    # Третий критерий: название (если провайдеры одинаковые)
                    x[1].get('name', '')
                )
            )
            
            # Добавляем стратегии в список
            self.strategies_map = {}  # Для хранения соответствия индекса строки и ID стратегии
            for row, (strategy_id, strategy_info) in enumerate(sorted_strategies):
                display_name = strategy_info.get('name', strategy_id)
                provider = strategy_info.get('provider', 'universal')
                
                # Добавляем в список с информацией о порядке сортировки
                sort_order = strategy_info.get('sort_order', 999)
                if sort_order != 999:  # Если задан порядок сортировки
                    list_text = f"{sort_order}. {display_name} ({provider})"
                else:
                    list_text = f"{display_name} ({provider})"
                self.strategies_list.addItem(list_text)
                
                # Сохраняем соответствие
                self.strategies_map[row] = {'id': strategy_id, 'name': display_name}
            
            log(f"Загружено {len(strategies)} стратегий", level="INFO")
            
        except Exception as e:
            log(f"Ошибка при загрузке списка стратегий: {str(e)}", level="ERROR")
            self.strategy_info.setHtml(f"<p style='color:red'>Ошибка: {str(e)}</p>")
    
    def refresh_strategies(self):
        """Обновляет список стратегий."""
        try:
            if self.strategy_manager:
                # Запрашиваем свежие данные с сервера
                self.strategy_manager.get_strategies_list(force_update=True)
                # Перезагружаем список
                self.load_strategies()
                # Восстанавливаем выбор текущей стратегии, если она задана
                if self.current_strategy_name:
                    self.select_strategy_by_name(self.current_strategy_name)
        except Exception as e:
            log(f"Ошибка при обновлении списка стратегий: {str(e)}", level="ERROR")
    
    def on_strategy_selected(self, row):
        """Обрабатывает выбор стратегии в списке."""
        if row < 0 or row not in self.strategies_map:
            self.strategy_info.clear()
            self.strategy_title.setText("Выберите стратегию")
            self.select_button.setEnabled(False)
            return
        
        # Получаем ID выбранной стратегии
        strategy_id = self.strategies_map[row]['id']
        strategy_name = self.strategies_map[row]['name']
        
        # Сохраняем выбранную стратегию
        self.selected_strategy_id = strategy_id
        self.selected_strategy_name = strategy_name
        
        # Включаем кнопку выбора
        self.select_button.setEnabled(True)
        
        # Получаем информацию о стратегии
        try:
            strategies = self.strategy_manager.get_strategies_list()
            if strategy_id in strategies:
                strategy_info = strategies[strategy_id]
                
                # Устанавливаем заголовок
                self.strategy_title.setText(strategy_info.get('name', strategy_id))
                
                # Формируем HTML для отображения информации
                html = "<style>body {font-family: Arial; margin: 10px;}</style>"
                
                # Описание
                description = strategy_info.get('description', 'Описание отсутствует')
                html += f"<p><b>Описание:</b> {description}</p>"
                
                # Провайдер
                provider = strategy_info.get('provider', 'universal')
                html += f"<p><b>Оптимизировано для:</b> {provider}</p>"
                
                # Версия
                version = strategy_info.get('version', 'неизвестно')
                html += f"<p><b>Версия:</b> {version}</p>"
                
                # Автор
                author = strategy_info.get('author', 'неизвестно')
                html += f"<p><b>Автор:</b> {author}</p>"
                
                # Дата обновления
                updated = strategy_info.get('updated', 'неизвестно')
                html += f"<p><b>Обновлено:</b> {updated}</p>"
                
                # Файл
                file_path = strategy_info.get('file_path', 'неизвестно')
                html += f"<p><b>Файл:</b> {file_path}</p>"
                
                # Статус скачивания
                local_path = os.path.join(self.strategy_manager.local_dir, file_path)
                if os.path.exists(local_path):
                    html += "<p><b>Статус:</b> <span style='color:green'>Файл скачан и готов к использованию</span></p>"
                else:
                    html += "<p><b>Статус:</b> <span style='color:orange'>Файл будет скачан при выборе стратегии</span></p>"
                
                # Устанавливаем HTML
                self.strategy_info.setHtml(html)
            else:
                self.strategy_info.setHtml("<p style='color:red'>Информация о стратегии не найдена</p>")
        except Exception as e:
            log(f"Ошибка при получении информации о стратегии: {str(e)}", level="ERROR")
            self.strategy_info.setHtml(f"<p style='color:red'>Ошибка: {str(e)}</p>")
    
    def select_strategy_by_name(self, strategy_name):
        """Выбирает стратегию по имени."""
        for row, info in self.strategies_map.items():
            if info['name'] == strategy_name:
                self.strategies_list.setCurrentRow(row)
                break
    
    def accept(self):
        """Обрабатывает нажатие кнопки 'Выбрать стратегию'."""
        if self.selected_strategy_id and self.selected_strategy_name:
            # Эмитируем сигнал о выборе стратегии
            self.strategySelected.emit(self.selected_strategy_id, self.selected_strategy_name)
            super().accept()
        else:
            log("Попытка выбора стратегии без выбора в списке", level="WARNING")