# strategy_menu/strategy_table_widget_favorites.py

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
                            QTableWidgetItem, QPushButton, QProgressBar, QLabel,
                            QMenu, QMessageBox, QApplication, QAbstractItemView, 
                            QHeaderView, QToolButton)
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QThread, QObject, QTimer
from PyQt6.QtGui import QAction, QFont, QColor, QBrush

from log import log
from .table_builder import StrategyTableBuilder
from .dialogs import StrategyInfoDialog
from .workers import StrategyFilesDownloader
from .strategy_table_widget import SingleDownloadWorker, StrategyTableWidget


class FavoriteStrategyTableWidget(StrategyTableWidget):
    """Расширенный виджет таблицы стратегий с поддержкой избранных"""
    
    # Дополнительные сигналы
    favorites_changed = pyqtSignal(int)  # Количество избранных
    
    def __init__(self, strategy_manager=None, parent=None):
        super().__init__(strategy_manager, parent)
        self.favorites_count = 0
        self._add_favorites_ui()
    
    def _add_favorites_ui(self):
        """Добавляет UI элементы для избранных"""
        # Добавляем счетчик избранных в статус бар
        if hasattr(self, 'status_label'):
            # Создаем контейнер для статуса и счетчика избранных
            status_container = QWidget()
            status_layout = QHBoxLayout(status_container)
            status_layout.setContentsMargins(0, 0, 0, 0)
            status_layout.setSpacing(10)
            
            # Перемещаем существующий статус лейбл в контейнер
            self.status_label.setParent(None)
            status_layout.addWidget(self.status_label)
            
            # Добавляем счетчик избранных
            self.favorites_label = QLabel("")
            self.favorites_label.setStyleSheet(
                "font-weight: bold; color: #ffd700; font-size: 9pt; padding: 3px;"
            )
            self.favorites_label.setFixedHeight(25)
            status_layout.addWidget(self.favorites_label)
            
            status_layout.addStretch()
            
            # Вставляем контейнер на место статус лейбла
            parent_layout = self.layout()
            parent_layout.insertWidget(0, status_container)
    
    def populate_strategies(self, strategies):
        """Заполняет таблицу стратегиями с учетом избранных"""
        # Сортируем стратегии: избранные вверху
        sorted_strategies = self._sort_strategies_with_favorites(strategies)
        
        # Вызываем родительский метод с отсортированными стратегиями
        super().populate_strategies(sorted_strategies)
        
        # Обновляем счетчик избранных
        self._update_favorites_count()
        
        # Подсвечиваем избранные стратегии
        self._highlight_favorite_strategies()
    
    def _sort_strategies_with_favorites(self, strategies):
        """Сортирует стратегии: избранные сверху"""
        from strategy_menu import is_favorite_strategy
        
        # Разделяем на избранные и обычные
        favorites = {}
        regular = {}
        
        for strat_id, strat_data in strategies.items():
            # Для классического режима проверяем глобально (без категории)
            # is_favorite_strategy с category=None проверит во всех категориях
            if is_favorite_strategy(strat_id, category=None):
                favorites[strat_id] = strat_data
            else:
                regular[strat_id] = strat_data
        
        # Объединяем: сначала избранные, потом обычные
        sorted_strategies = {}
        sorted_strategies.update(favorites)
        sorted_strategies.update(regular)
        
        return sorted_strategies
    
    def _highlight_favorite_strategies(self):
        """Подсвечивает избранные стратегии в таблице"""
        from strategy_menu import is_favorite_strategy
        
        for row, strategy_info in self.strategies_map.items():
            strategy_id = strategy_info['id']
            
            # Для классического режима проверяем глобально
            if is_favorite_strategy(strategy_id, category=None):
                # Добавляем звездочку к названию
                name_item = self.table.item(row, 0)
                if name_item and not name_item.text().startswith("⭐"):
                    name_item.setText(f"⭐ {name_item.text()}")
                
                # Подсвечиваем строку золотистым цветом
                for col in range(self.table.columnCount()):
                    item = self.table.item(row, col)
                    if item:
                        # Светлый золотистый фон для избранных
                        item.setBackground(QBrush(QColor(50, 45, 20)))  # Темно-золотистый для темной темы

    def _toggle_favorite(self, strategy_id):
        """Переключает статус избранной стратегии"""
        from strategy_menu import toggle_favorite_strategy, is_favorite_strategy
        
        # Для классического режима используем категорию "classic" 
        # чтобы отделить от Direct режима
        CLASSIC_CATEGORY = "classic_strategies"
        
        was_favorite = is_favorite_strategy(strategy_id, CLASSIC_CATEGORY)
        toggle_favorite_strategy(strategy_id, CLASSIC_CATEGORY)
        
        # Находим строку стратегии
        for row, info in self.strategies_map.items():
            if info['id'] == strategy_id:
                name_item = self.table.item(row, 0)
                if name_item:
                    current_text = name_item.text()
                    
                    if was_favorite:
                        # Удаляем звездочку
                        if current_text.startswith("⭐ "):
                            name_item.setText(current_text[2:])
                        # Убираем подсветку
                        for col in range(self.table.columnCount()):
                            item = self.table.item(row, col)
                            if item:
                                item.setBackground(QBrush())  # Сброс фона
                    else:
                        # Добавляем звездочку
                        if not current_text.startswith("⭐"):
                            name_item.setText(f"⭐ {current_text}")
                        # Добавляем подсветку
                        for col in range(self.table.columnCount()):
                            item = self.table.item(row, col)
                            if item:
                                item.setBackground(QBrush(QColor(50, 45, 20)))
                
                break
        
        # Обновляем счетчик
        self._update_favorites_count()
        
        # Логируем действие
        action = "добавлена в" if not was_favorite else "удалена из"
        strategy_name = self.strategies_map.get(row, {}).get('name', strategy_id)
        log(f"Стратегия '{strategy_name}' {action} избранных", "INFO")
        
        # Уведомляем пользователя
        status_text = f"⭐ Добавлено в избранные" if not was_favorite else "☆ Удалено из избранных"
        self.set_status(status_text, "success")
        
        # Сбрасываем статус через 2 секунды
        QTimer.singleShot(2000, lambda: self.set_status("✅ Готово", "success"))

    def _update_favorites_count(self):
        """Обновляет счетчик избранных стратегий"""
        from strategy_menu import get_favorite_strategies
        
        # Для классического режима получаем избранные из категории "classic"
        CLASSIC_CATEGORY = "classic_strategies"
        favorites = get_favorite_strategies(CLASSIC_CATEGORY)
        
        # Считаем только те избранные, которые есть в текущем списке
        self.favorites_count = len([
            f for f in favorites 
            if any(info['id'] == f for info in self.strategies_map.values())
        ])
        
        if self.favorites_count > 0:
            self.favorites_label.setText(f"⭐ Избранных: {self.favorites_count}")
        else:
            self.favorites_label.setText("")
        
        self.favorites_changed.emit(self.favorites_count)
    
    def _show_context_menu(self, position: QPoint):
        """Показывает контекстное меню с опцией избранного"""
        if not self.table.isEnabled():
            return
        
        item = self.table.itemAt(position)
        if not item:
            return
        
        row = item.row()
        
        # Проверяем, что это не строка провайдера
        if row < 0 or row not in self.strategies_map:
            return
        
        # Если нет выбранной стратегии, выбираем ту, на которой кликнули
        if not self.selected_strategy_id:
            self.table.selectRow(row)
        
        strategy_id = self.strategies_map[row]['id']
        
        # Создаем контекстное меню
        context_menu = QMenu(self)
        context_menu.setStyleSheet(self._get_context_menu_style())
        
        # Добавить/удалить из избранных
        from strategy_menu import is_favorite_strategy
        is_favorite = is_favorite_strategy(strategy_id)
        
        favorite_action = QAction("⭐ Удалить из избранных" if is_favorite else "☆ Добавить в избранные", self)
        favorite_action.triggered.connect(lambda: self._toggle_favorite(strategy_id))
        context_menu.addAction(favorite_action)
        
        context_menu.addSeparator()
        
        # Подробная информация
        info_action = QAction("ℹ️ Подробная информация", self)
        info_action.triggered.connect(self.show_strategy_info)
        info_action.setEnabled(self.selected_strategy_id is not None)
        context_menu.addAction(info_action)
        
        context_menu.addSeparator()
        
        # Копировать имя
        copy_name_action = QAction("📋 Скопировать имя", self)
        copy_name_action.triggered.connect(self._copy_strategy_name)
        context_menu.addAction(copy_name_action)
        
        # Скачать/обновить
        if row in self.strategies_map and self.strategy_manager:
            strategies = self.strategy_manager.get_local_strategies_only()
            
            if strategy_id in strategies:
                version_status = self.strategy_manager.check_strategy_version_status(strategy_id)
                
                if version_status in ['not_downloaded', 'outdated']:
                    download_action = QAction("⬇️ Скачать/обновить", self)
                    download_action.triggered.connect(lambda: self._download_single_strategy(strategy_id))
                    context_menu.addAction(download_action)
        
        # Показываем меню
        global_pos = self.table.mapToGlobal(position)
        context_menu.exec(global_pos)
    
    def refresh_favorites(self):
        """Обновляет отображение избранных стратегий"""
        # Пересортировываем и перезаполняем таблицу
        if self.strategies_map:
            # Собираем текущие стратегии обратно в словарь
            current_strategies = {}
            for info in self.strategies_map.values():
                if 'id' in info and 'name' in info:
                    # Восстанавливаем структуру стратегии
                    current_strategies[info['id']] = {
                        'name': info['name'],
                        'description': info.get('description', ''),
                        'provider': info.get('provider', 'Unknown'),
                        'label': info.get('label', '')
                    }
            
            # Перезаполняем таблицу с учетом избранных
            self.populate_strategies(current_strategies)


class StrategyTableWithFavoritesFilter(FavoriteStrategyTableWidget):
    """Расширение с фильтром для показа только избранных"""
    
    def __init__(self, strategy_manager=None, parent=None):
        super().__init__(strategy_manager, parent)
        self._show_only_favorites = False
        self._all_strategies = {}
        self._add_filter_ui()
    
    def _add_filter_ui(self):
        """Добавляет UI для фильтрации избранных"""
        # Находим layout с кнопками
        buttons_layout = None
        for i in range(self.layout().count()):
            item = self.layout().itemAt(i)
            if item and item.layout():
                # Ищем layout с кнопками управления
                for j in range(item.layout().count()):
                    widget = item.layout().itemAt(j).widget()
                    if isinstance(widget, QPushButton) and widget.text() == "🌐 Обновить":
                        buttons_layout = item.layout()
                        break
        
        if buttons_layout:
            # Добавляем кнопку фильтра после кнопки "Инфо"
            self.filter_favorites_btn = QPushButton("⭐ Только избранные")
            self.filter_favorites_btn.setCheckable(True)
            self.filter_favorites_btn.setFixedHeight(25)
            self.filter_favorites_btn.setStyleSheet("""
                QPushButton {
                    background-color: #3a3a3a;
                    color: #ffffff;
                    border: 1px solid #555;
                    border-radius: 3px;
                    padding: 3px 10px;
                    font-size: 9pt;
                }
                QPushButton:hover {
                    background-color: #454545;
                    border: 1px solid #ffd700;
                }
                QPushButton:checked {
                    background-color: #4a4520;
                    border: 1px solid #ffd700;
                    color: #ffd700;
                }
            """)
            self.filter_favorites_btn.toggled.connect(self._toggle_favorites_filter)
            
            # Вставляем после кнопки "Инфо"
            buttons_layout.insertWidget(3, self.filter_favorites_btn)
    
    def _toggle_favorites_filter(self, checked):
        """Переключает фильтр избранных"""
        self._show_only_favorites = checked
        
        if checked:
            # Показываем только избранные
            from strategy_menu import get_favorite_strategies
            
            # Для классического режима используем категорию "classic"
            CLASSIC_CATEGORY = "classic_strategies"
            favorites = get_favorite_strategies(CLASSIC_CATEGORY)
            
            filtered_strategies = {
                sid: sdata 
                for sid, sdata in self._all_strategies.items() 
                if sid in favorites
            }
            
            if filtered_strategies:
                super().populate_strategies(filtered_strategies)
                self.set_status(f"⭐ Показаны только избранные ({len(filtered_strategies)})", "info")
            else:
                # Очищаем таблицу если нет избранных
                self.strategies_map.clear()
                self.table.setRowCount(0)
                self.set_status("⭐ Нет избранных стратегий", "warning")
        else:
            # Показываем все стратегии
            super().populate_strategies(self._all_strategies)
            self.set_status(f"✅ Показаны все стратегии ({len(self._all_strategies)})", "success")
    
    def populate_strategies(self, strategies):
        """Сохраняет все стратегии и заполняет таблицу"""
        self._all_strategies = strategies.copy()
        
        if self._show_only_favorites:
            # Если включен фильтр, показываем только избранные
            self._toggle_favorites_filter(True)
        else:
            super().populate_strategies(strategies)