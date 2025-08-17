# strategy_menu/strategy_table_widget.py

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
                            QTableWidgetItem, QPushButton, QProgressBar, QLabel,
                            QMenu, QMessageBox, QApplication, QAbstractItemView, QHeaderView)
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QThread, QObject, QTimer
from PyQt6.QtGui import QAction, QFont, QColor, QBrush

from log import log
from .table_builder import StrategyTableBuilder
from .dialogs import StrategyInfoDialog
from .workers import StrategyFilesDownloader


class SingleDownloadWorker(QObject):
    """Воркер для скачивания одной стратегии"""
    finished = pyqtSignal(bool, str)
    
    def __init__(self, strategy_manager, strategy_id):
        super().__init__()
        self.strategy_manager = strategy_manager
        self.strategy_id = strategy_id
    
    def run(self):
        try:
            local_path = self.strategy_manager.download_single_strategy_bat(self.strategy_id)
            if local_path:
                self.finished.emit(True, f"Стратегия {self.strategy_id} успешно скачана")
            else:
                self.finished.emit(False, f"Не удалось скачать стратегию {self.strategy_id}")
        except Exception as e:
            self.finished.emit(False, f"Ошибка: {str(e)}")


class StrategyTableWidget(QWidget):
    """Виджет таблицы стратегий с полным функционалом"""
    
    # Сигналы
    strategy_selected = pyqtSignal(str, str)  # strategy_id, strategy_name
    strategy_double_clicked = pyqtSignal(str, str)  # strategy_id, strategy_name
    status_message = pyqtSignal(str, str)  # message, style
    
    def __init__(self, strategy_manager=None, parent=None):
        super().__init__(parent)
        self.strategy_manager = strategy_manager
        self.strategies_map = {}
        self.selected_strategy_id = None
        self.selected_strategy_name = None
        self.info_dialog = None
        self.is_downloading = False
        self.download_thread = None
        self.download_worker = None
        
        self._init_ui()
    
    def _init_ui(self):
        """Инициализация интерфейса"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        
        # Статус бар
        self.status_label = QLabel("🔄 Загрузка...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("font-weight: bold; color: #2196F3; font-size: 9pt; padding: 3px;")
        self.status_label.setFixedHeight(25)
        layout.addWidget(self.status_label)
        
        # Прогресс бар
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(20)
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #444;
                border-radius: 3px;
                text-align: center;
                background-color: #2a2a2a;
            }
            QProgressBar::chunk {
                background-color: #2196F3;
                border-radius: 2px;
            }
        """)
        # Скрываем прогресс бар по умолчанию
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Таблица стратегий
        self.table = StrategyTableBuilder.create_strategies_table()
        self.table.currentItemChanged.connect(self._on_item_selected)
        self.table.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.table.setEnabled(False)
        
        # Включаем контекстное меню
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        
        layout.addWidget(self.table)
        
        # Кнопки управления
        self._init_control_buttons(layout)
    
    def _init_control_buttons(self, parent_layout):
        """Инициализация кнопок управления"""
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(5)
        
        button_style = """
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
                border: 1px solid #2196F3;
            }
            QPushButton:pressed {
                background-color: #2a2a2a;
            }
            QPushButton:disabled {
                background-color: #2a2a2a;
                color: #666;
                border: 1px solid #333;
            }
        """
        
        self.refresh_button = QPushButton("🌐 Обновить")
        self.refresh_button.setFixedHeight(25)
        self.refresh_button.setStyleSheet(button_style)
        buttons_layout.addWidget(self.refresh_button)
        
        self.download_all_button = QPushButton("⬇️ Скачать все")
        self.download_all_button.setFixedHeight(25)
        self.download_all_button.setStyleSheet(button_style)
        buttons_layout.addWidget(self.download_all_button)
        
        self.info_button = QPushButton("ℹ️ Инфо")
        self.info_button.setEnabled(False)
        self.info_button.setFixedHeight(25)
        self.info_button.setStyleSheet(button_style)
        self.info_button.clicked.connect(self.show_strategy_info)
        buttons_layout.addWidget(self.info_button)
        
        buttons_layout.addStretch()
        parent_layout.addLayout(buttons_layout)
    
    def populate_strategies(self, strategies):
        """Заполняет таблицу стратегиями"""
        # Показываем прогресс во время заполнения
        self.set_progress_visible(True)
        self.set_status("📊 Заполнение таблицы...", "info")
        
        self.strategies_map = StrategyTableBuilder.populate_table(
            self.table, 
            strategies, 
            self.strategy_manager
        )
        self.table.setEnabled(True)
        
        # Обновляем статус
        count = len(strategies)
        self.set_status(f"✅ Загружено {count} стратегий", "success")
        
        # Обязательно скрываем прогресс после заполнения
        self.set_progress_visible(False)
    
    def set_status(self, message, status_type="info"):
        """Устанавливает статус"""
        styles = {
            "info": "font-weight: bold; color: #2196F3; font-size: 9pt; padding: 3px;",
            "success": "font-weight: bold; color: #4CAF50; font-size: 9pt; padding: 3px;",
            "warning": "font-weight: bold; color: #ff9800; font-size: 9pt; padding: 3px;",
            "error": "font-weight: bold; color: #f44336; font-size: 9pt; padding: 3px;"
        }
        
        self.status_label.setText(message)
        self.status_label.setStyleSheet(styles.get(status_type, styles["info"]))
        
        # Эмитируем сигнал для родительского окна
        self.status_message.emit(message, status_type)
    
    def set_progress_visible(self, visible):
        """Показывает/скрывает прогресс бар"""
        if self.progress_bar:
            self.progress_bar.setVisible(visible)
            if visible:
                self.progress_bar.setRange(0, 0)  # Неопределенный прогресс

            log(f"Прогресс бар: {'показан' if visible else 'скрыт'}", "DEBUG")
    
    def set_progress_value(self, value, max_value=100):
        """Устанавливает значение прогресса"""
        self.progress_bar.setRange(0, max_value)
        self.progress_bar.setValue(value)
    
    def _on_item_selected(self, current, previous):
        """Обработчик выбора элемента в таблице"""
        if current is None:
            self.selected_strategy_id = None
            self.selected_strategy_name = None
            self.info_button.setEnabled(False)
            return
        
        row = current.row()
        
        # Проверяем, что выбрана не строка провайдера
        if row < 0 or row not in self.strategies_map:
            self.selected_strategy_id = None
            self.selected_strategy_name = None
            self.info_button.setEnabled(False)
            return
        
        # Сохраняем выбранную стратегию
        self.selected_strategy_id = self.strategies_map[row]['id']
        self.selected_strategy_name = self.strategies_map[row]['name']
        
        # Включаем кнопку инфо
        self.info_button.setEnabled(True)
        
        # Эмитируем сигнал
        self.strategy_selected.emit(self.selected_strategy_id, self.selected_strategy_name)
    
    def _on_item_double_clicked(self, item):
        """Обработчик двойного клика"""
        if not item:
            return
        
        row = item.row()
        
        if row < 0 or row not in self.strategies_map:
            return
        
        strategy_id = self.strategies_map[row]['id']
        strategy_name = self.strategies_map[row]['name']
        
        self.strategy_double_clicked.emit(strategy_id, strategy_name)
    
    def _show_context_menu(self, position: QPoint):
        """Показывает контекстное меню"""
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
        
        # Создаем контекстное меню
        context_menu = QMenu(self)
        context_menu.setStyleSheet(self._get_context_menu_style())
        
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
            strategy_id = self.strategies_map[row]['id']
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
    
    def _get_context_menu_style(self):
        """Возвращает стили для контекстного меню"""
        # Здесь можно определить тему из родительского окна
        is_dark_theme = True  # По умолчанию темная
        
        if is_dark_theme:
            return """
            QMenu {
                background-color: #2a2a2a;
                color: #ffffff;
                border: 1px solid #444444;
                padding: 2px;  /* Уменьшено с 5px до 2px */
            }
            QMenu::item {
                padding: 3px 12px;  /* Уменьшено с 5px 20px до 3px 12px */
                border-radius: 2px;  /* Уменьшено с 3px */
                font-size: 9pt;  /* Добавлен меньший размер шрифта */
            }
            QMenu::item:selected {
                background-color: #3a3a3a;
            }
            QMenu::separator {
                height: 1px;
                background: #444444;
                margin: 2px 0;  /* Уменьшено с 5px до 2px */
            }
            """
        else:
            return """
            QMenu {
                background-color: #ffffff;
                color: #000000;
                border: 1px solid #cccccc;
                padding: 2px;  /* Уменьшено с 5px до 2px */
            }
            QMenu::item {
                padding: 3px 12px;  /* Уменьшено с 5px 20px до 3px 12px */
                border-radius: 2px;  /* Уменьшено с 3px */
                font-size: 9pt;  /* Добавлен меньший размер шрифта */
            }
            QMenu::item:selected {
                background-color: #e0e0e0;
            }
            QMenu::separator {
                height: 1px;
                background: #cccccc;
                margin: 2px 0;  /* Уменьшено с 5px до 2px */
            }
            """
    
    def show_strategy_info(self):
        """Показывает окно с информацией о стратегии"""
        if not self.selected_strategy_id:
            return
        
        if not self.info_dialog:
            self.info_dialog = StrategyInfoDialog(self, self.strategy_manager)
        
        self.info_dialog.display_strategy_info(self.selected_strategy_id, self.selected_strategy_name)
        self.info_dialog.show()
        self.info_dialog.raise_()
        self.info_dialog.activateWindow()
    
    def _copy_strategy_name(self):
        """Копирует имя стратегии в буфер обмена"""
        if self.selected_strategy_name:
            clipboard = QApplication.clipboard()
            clipboard.setText(self.selected_strategy_name)
            
            self.set_status(f"📋 Скопировано: {self.selected_strategy_name}", "success")
            
            # Сбрасываем статус через 2 секунды
            QTimer.singleShot(2000, lambda: self.set_status("✅ Готово", "success"))
    
    def _download_single_strategy(self, strategy_id):
        """Скачивает одну стратегию"""
        if self.is_downloading:
            QMessageBox.information(self, "Скачивание в процессе", 
                                "Дождитесь завершения текущего скачивания")
            return
        
        if not self.strategy_manager:
            QMessageBox.warning(self, "Ошибка", "Менеджер стратегий не инициализирован")
            return
        
        self.is_downloading = True
        
        # Обновляем UI
        self.set_status(f"⬇️ Скачивание стратегии {strategy_id}...", "info")
        self.set_progress_visible(True)
        
        # Скачиваем в отдельном потоке
        self.single_download_thread = QThread()
        self.single_download_worker = SingleDownloadWorker(self.strategy_manager, strategy_id)
        self.single_download_worker.moveToThread(self.single_download_thread)
        
        self.single_download_thread.started.connect(self.single_download_worker.run)
        self.single_download_worker.finished.connect(self._on_single_download_finished)
        self.single_download_worker.finished.connect(self.single_download_thread.quit)
        self.single_download_worker.finished.connect(self.single_download_worker.deleteLater)
        self.single_download_thread.finished.connect(self.single_download_thread.deleteLater)
        
        self.single_download_thread.start()
        
        log(f"Запуск скачивания стратегии {strategy_id}", "INFO")
    
    def _on_single_download_finished(self, success, message):
        """Обработчик завершения скачивания"""
        self.is_downloading = False
        self.set_progress_visible(False)
        
        if success:
            self.set_status(f"✅ {message}", "success")
            # Запрашиваем обновление таблицы
            if hasattr(self.parent(), 'load_local_strategies_only'):
                self.parent().load_local_strategies_only()
        else:
            self.set_status(f"❌ {message}", "error")
        
        log(message, "INFO" if success else "❌ ERROR")
    
    def download_all_strategies_async(self):
        """Скачивает все стратегии асинхронно"""
        if self.is_downloading:
            QMessageBox.information(self, "Скачивание в процессе", 
                                "Скачивание уже выполняется, подождите...")
            return
        
        if not self.strategy_manager:
            QMessageBox.warning(self, "Ошибка", "Менеджер стратегий не инициализирован")
            return
        
        strategies = self.strategy_manager.get_local_strategies_only()
        if not strategies:
            QMessageBox.information(self, "Нет стратегий", 
                                "Сначала обновите список стратегий из интернета")
            return
        
        self.is_downloading = True
        
        # Обновляем UI
        self.set_status("⬇️ Скачивание файлов стратегий...", "info")
        self.set_progress_visible(True)
        self.refresh_button.setEnabled(False)
        self.download_all_button.setEnabled(False)
        
        # Создаем поток для скачивания
        self.download_thread = QThread()
        self.download_worker = StrategyFilesDownloader(self.strategy_manager)
        self.download_worker.moveToThread(self.download_thread)
        
        self.download_thread.started.connect(self.download_worker.run)
        self.download_worker.progress.connect(self._update_download_progress)
        self.download_worker.finished.connect(self._on_download_finished)
        self.download_worker.finished.connect(self.download_thread.quit)
        self.download_worker.finished.connect(self.download_worker.deleteLater)
        self.download_thread.finished.connect(self.download_thread.deleteLater)
        
        self.download_thread.start()
        
        log("Запуск скачивания файлов стратегий", "INFO")
    
    def _update_download_progress(self, progress_percent, current_strategy):
        """Обновляет прогресс скачивания"""
        self.set_progress_value(progress_percent)
        self.set_status(f"⬇️ Скачивание: {current_strategy} ({progress_percent}%)", "info")
    
    def _on_download_finished(self, downloaded_count, total_count, error_message):
        """Обработчик завершения массового скачивания"""
        self.is_downloading = False
        self.set_progress_visible(False)
        
        # Включаем кнопки
        self.refresh_button.setEnabled(True)
        self.download_all_button.setEnabled(True)
        
        if error_message:
            self.set_status(f"❌ {error_message}", "error")
        elif total_count == 0:
            self.set_status("⚠️ Нет файлов для скачивания", "warning")
        else:
            self.set_status(f"✅ Скачано {downloaded_count}/{total_count} стратегий", "success")
            
            # Обновляем таблицу
            if hasattr(self.parent(), 'load_local_strategies_only'):
                self.parent().load_local_strategies_only()
        
        log(f"Асинхронное скачивание завершено: {downloaded_count}/{total_count}", "INFO")
    
    def select_strategy_by_name(self, strategy_name):
        """Выбирает стратегию по имени"""
        for row, info in self.strategies_map.items():
            if info['name'] == strategy_name:
                self.table.selectRow(row)
                break
    
    def get_selected_strategy(self):
        """Возвращает ID и имя выбранной стратегии"""
        return self.selected_strategy_id, self.selected_strategy_name
    
    def set_theme_manager(self, theme_manager):
        """Устанавливает менеджер тем для правильного стиля контекстного меню"""
        self.theme_manager = theme_manager