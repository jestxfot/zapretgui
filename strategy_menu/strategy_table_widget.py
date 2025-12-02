# strategy_menu/strategy_table_widget.py

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QMenu
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QPoint, QEvent
from PyQt6.QtGui import QCursor

from log import log
from .table_builder import StrategyTableBuilder
from .hover_tooltip import tooltip_manager


class StrategyTableWidget(QWidget):
    """Виджет таблицы стратегий - минималистичный"""
    
    # Сигналы
    strategy_selected = pyqtSignal(str, str)
    strategy_applied = pyqtSignal(str, str)
    favorites_changed = pyqtSignal()  # Сигнал об изменении избранных
    
    def __init__(self, strategy_manager=None, parent=None):
        super().__init__(parent)
        self.strategy_manager = strategy_manager
        self.strategies_map = {}
        self.strategies_data = {}
        self.selected_strategy_id = None
        self.selected_strategy_name = None
        self._last_hover_row = -1
        
        self._init_ui()
    
    def _init_ui(self):
        """Инициализация интерфейса"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Подсказка
        hint = QLabel("💡 Клик - применить • Удержание - информация")
        hint.setStyleSheet("color: rgba(255, 255, 255, 0.4); font-size: 10px; padding: 6px 8px;")
        layout.addWidget(hint)
        
        # Статус
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: rgba(255, 255, 255, 0.5); font-size: 11px; padding: 4px 8px;")
        self.status_label.setFixedHeight(24)
        layout.addWidget(self.status_label)
        
        # Таблица
        self.table = StrategyTableBuilder.create_strategies_table()
        self.table.currentItemChanged.connect(self._on_item_selected)
        self.table.setEnabled(False)
        
        # Отслеживание мыши для hover tooltip
        self.table.setMouseTracking(True)
        self.table.viewport().setMouseTracking(True)
        self.table.viewport().installEventFilter(self)
        
        # Контекстное меню по ПКМ
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        
        # Двойной клик для показа информации
        self.table.doubleClicked.connect(self._on_double_click)
        
        layout.addWidget(self.table)
    
    def eventFilter(self, obj, event):
        """Фильтр событий для отслеживания hover"""
        if obj == self.table.viewport():
            if event.type() == QEvent.Type.MouseMove:
                pos = event.pos()
                item = self.table.itemAt(pos)
                
                if item:
                    row = item.row()
                    if row != self._last_hover_row and row in self.strategies_map:
                        self._last_hover_row = row
                        strategy_id = self.strategies_map[row]['id']
                        
                        if strategy_id in self.strategies_data:
                            # Показываем tooltip
                            global_pos = self.table.viewport().mapToGlobal(pos)
                            global_pos.setX(global_pos.x() + 20)
                            global_pos.setY(global_pos.y() + 15)
                            
                            tooltip_manager.show_tooltip(
                                global_pos,
                                self.strategies_data[strategy_id],
                                strategy_id,
                                delay=500
                            )
                else:
                    if self._last_hover_row != -1:
                        self._last_hover_row = -1
                        tooltip_manager.hide_tooltip(delay=100)
                        
            elif event.type() == QEvent.Type.Leave:
                self._last_hover_row = -1
                tooltip_manager.hide_tooltip(delay=150)
                
            elif event.type() == QEvent.Type.MouseButtonPress:
                tooltip_manager.hide_immediately()
                
        return super().eventFilter(obj, event)
    
    def populate_strategies(self, strategies):
        """Заполняет таблицу стратегиями"""
        self.strategies_data = strategies
        
        self.strategies_map = StrategyTableBuilder.populate_table(
            self.table, 
            strategies, 
            self.strategy_manager,
            favorite_callback=self._on_favorite_toggled
        )
            
        self.table.setEnabled(True)
        
        count = len(strategies)
        self.set_status(f"✅ {count} стратегий")
    
    def _on_favorite_toggled(self, strategy_id, is_favorite):
        """Обработчик переключения избранного через звезду"""
        # Перезаполняем таблицу чтобы избранные переместились вверх
        self.populate_strategies(self.strategies_data)
        # Уведомляем об изменении
        self.favorites_changed.emit()
    
    def _show_context_menu(self, pos: QPoint):
        """Показывает контекстное меню"""
        tooltip_manager.hide_immediately()
        
        item = self.table.itemAt(pos)
        if not item:
            return
        
        row = item.row()
        if row not in self.strategies_map:
            return
        
        strategy_id = self.strategies_map[row]['id']
        strategy_name = self.strategies_map[row]['name']
        
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: rgba(44, 44, 44, 0.98);
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 6px;
                padding: 2px;
            }
            QMenu::item {
                color: rgba(255, 255, 255, 0.85);
                padding: 4px 10px;
                border-radius: 3px;
                font-size: 11px;
                margin: 1px;
            }
            QMenu::item:selected {
                background-color: rgba(255, 255, 255, 0.08);
            }
            QMenu::separator {
                height: 1px;
                background: rgba(255, 255, 255, 0.05);
                margin: 2px 6px;
            }
        """)
        
        # Действия меню
        info_action = menu.addAction("ℹ️  Подробная информация")
        menu.addSeparator()
        apply_action = menu.addAction("▶️  Применить стратегию")
        
        if strategy_id in self.strategies_data:
            from strategy_menu import is_favorite_strategy
            is_fav = is_favorite_strategy(strategy_id, "bat")
            
            menu.addSeparator()
            if is_fav:
                fav_action = menu.addAction("☆  Убрать из избранных")
            else:
                fav_action = menu.addAction("★  Добавить в избранные")
        else:
            fav_action = None
        
        # Показываем меню
        action = menu.exec(self.table.viewport().mapToGlobal(pos))
        
        if action == info_action:
            self._show_strategy_info(strategy_id)
        elif action == apply_action:
            self.table.selectRow(row)
        elif action == fav_action and fav_action:
            from strategy_menu import toggle_favorite_strategy
            toggle_favorite_strategy(strategy_id, "bat")
            # Перезаполняем таблицу для обновления звезд
            self.populate_strategies(self.strategies_data)
            # Уведомляем об изменении избранных
            self.favorites_changed.emit()
    
    def _on_double_click(self, index):
        """Обработчик двойного клика - показ информации"""
        tooltip_manager.hide_immediately()
        row = index.row()
        if row in self.strategies_map:
            strategy_id = self.strategies_map[row]['id']
            self._show_strategy_info(strategy_id)
    
    def _show_strategy_info(self, strategy_id):
        """Показывает окно с информацией о стратегии"""
        if strategy_id not in self.strategies_data:
            return
        
        strategy_data = self.strategies_data[strategy_id]
        
        try:
            from .args_preview_dialog import preview_manager
            preview_manager.show_preview(self, strategy_id, strategy_data)
        except Exception as e:
            log(f"Ошибка показа информации о стратегии: {e}", "ERROR")
    
    def set_status(self, message, status_type="info"):
        """Устанавливает статус"""
        colors = {
            "info": "rgba(255, 255, 255, 0.5)",
            "success": "#4ade80",
            "warning": "#fbbf24",
            "error": "#f87171"
        }
        color = colors.get(status_type, colors["info"])
        
        self.status_label.setText(message)
        self.status_label.setStyleSheet(f"""
            QLabel {{
                color: {color};
                font-size: 11px;
                padding: 4px 8px;
            }}
        """)
    
    def _on_item_selected(self, current, previous):
        """Обработчик выбора - автоприменение"""
        tooltip_manager.hide_immediately()
        
        if current is None:
            self.selected_strategy_id = None
            self.selected_strategy_name = None
            return
        
        row = current.row()
        
        if row < 0 or row not in self.strategies_map:
            self.selected_strategy_id = None
            self.selected_strategy_name = None
            return
        
        self.selected_strategy_id = self.strategies_map[row]['id']
        self.selected_strategy_name = self.strategies_map[row]['name']
        
        # Эмитируем сигналы
        self.strategy_selected.emit(self.selected_strategy_id, self.selected_strategy_name)
        self.strategy_applied.emit(self.selected_strategy_id, self.selected_strategy_name)
        self.set_status(f"✅ {self.selected_strategy_name}", "success")
    
    def select_strategy_by_name(self, strategy_name):
        """Выбирает стратегию по имени"""
        for row, info in self.strategies_map.items():
            if info['name'] == strategy_name:
                self.table.selectRow(row)
                break
    
    def get_selected_strategy(self):
        """Возвращает ID и имя выбранной стратегии"""
        return self.selected_strategy_id, self.selected_strategy_name
    
    def hideEvent(self, event):
        """При скрытии виджета скрываем tooltip"""
        tooltip_manager.hide_immediately()
        super().hideEvent(event)
