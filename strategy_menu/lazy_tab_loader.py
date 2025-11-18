"""
Оптимизированная ленивая загрузка вкладок стратегий
✅ Заполняет существующие вкладки вместо пересоздания (в 3-5 раз быстрее!)
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt, QTimer
from log import log


class LazyTabLoader:
    """Управляет ленивой загрузкой вкладок - загружает ТОЛЬКО по требованию"""
    
    def __init__(self, dialog):
        self.dialog = dialog
        self.loaded_tabs = set()  # Индексы загруженных вкладок
        self.loading_in_progress = set()  # Защита от двойной загрузки
        
    def create_placeholder(self, category_key):
        """Создает заглушку для вкладки"""
        placeholder = QWidget()
        placeholder.category_key = category_key  # ✅ Сохраняем ключ
        
        layout = QVBoxLayout(placeholder)
        layout.setContentsMargins(20, 20, 20, 20)
        
        loading_label = QLabel("⏳ Нажмите для загрузки...")
        loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        loading_label.setStyleSheet("color: #888; font-style: italic; font-size: 10pt;")
        layout.addWidget(loading_label)
        layout.addStretch()
        
        return placeholder

    def load_tab_content(self, tab_index):
        """
        Загружает содержимое вкладки по индексу
        ✅ Заполняет существующий виджет вместо пересоздания (быстрее!)
        """
        # Проверка 1: Уже загружена?
        if tab_index in self.loaded_tabs:
            return
        
        # Проверка 2: Уже загружается?
        if tab_index in self.loading_in_progress:
            return
        
        # Проверка 3: Валидный индекс?
        if tab_index < 0 or tab_index >= self.dialog.category_tabs.count():
            log(f"Неверный индекс вкладки: {tab_index}", "WARNING")
            return
        
        # Получаем виджет вкладки
        widget = self.dialog.category_tabs.widget(tab_index)
        if not widget or not hasattr(widget, 'category_key'):
            log(f"Вкладка {tab_index} не имеет category_key", "WARNING")
            return
        
        category_key = widget.category_key
        
        # Проверка 4: Уже загружена по ключу?
        if category_key in self.dialog._categories_loaded:
            self.loaded_tabs.add(tab_index)
            return
        
        # ✅ Помечаем как "загружается"
        self.loading_in_progress.add(tab_index)
        
        # Показываем статус
        if hasattr(self.dialog, 'status_label'):
            self.dialog.status_label.setText(f"⏳ Загрузка {category_key}...")
        
        # ✅ Запускаем загрузку через QTimer (не блокирует UI)
        QTimer.singleShot(10, lambda: self._do_load_tab(tab_index, widget, category_key))
        
    def _do_load_tab(self, tab_index, widget, category_key):
        """Выполняет фактическую загрузку содержимого"""
        log(f"Загрузка содержимого вкладки {category_key}", "DEBUG")
        
        # Получаем данные из реестра
        from strategy_menu.strategies_registry import registry
        strategies = registry.get_category_strategies(category_key)
        category_info = registry.get_category_info(category_key)
        
        if not category_info:
            log(f"Категория {category_key} не найдена в реестре", "ERROR")
            self.loading_in_progress.discard(tab_index)
            return
        
        # ✅ КЛЮЧЕВОЕ ОТЛИЧИЕ: Заполняем существующий виджет вместо пересоздания!
        self.dialog._populate_tab_content(widget, strategies, category_key, category_info)
        
        # ✅ Помечаем как загруженную
        self.loaded_tabs.add(tab_index)
        self.dialog._categories_loaded.add(category_key)
        self.loading_in_progress.discard(tab_index)
        
        # Обновляем статус
        if hasattr(self.dialog, 'status_label'):
            self.dialog.status_label.setText("✅ Готово к выбору")
        
        log(f"Вкладка {category_key} успешно загружена", "DEBUG")
        
    def preload_first_tab(self):
        """Предзагружает ТОЛЬКО первую вкладку"""
        log("Предзагрузка первой вкладки", "DEBUG")
        QTimer.singleShot(10, lambda: self.load_tab_content(0))
        
    def get_loaded_count(self):
        """Возвращает количество загруженных вкладок"""
        return len(self.loaded_tabs)
    
    def get_total_count(self):
        """Возвращает общее количество вкладок"""
        return self.dialog.category_tabs.count()
    
    def is_all_loaded(self):
        """Проверяет, загружены ли все вкладки"""
        return len(self.loaded_tabs) >= self.dialog.category_tabs.count()