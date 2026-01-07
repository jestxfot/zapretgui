# strategy_menu/table_builder.py

from PyQt6.QtWidgets import (QTableWidget, QTableWidgetItem, QWidget,
                            QHBoxLayout, QLabel, QPushButton, QMenu)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor, QBrush, QCursor

from launcher_common.constants import LABEL_TEXTS, LABEL_COLORS

# Цвета подсветки рейтинга стратегий (полупрозрачные)
RATING_COLORS = {
    'working': QColor(74, 222, 128, 40),   # Зелёный полупрозрачный rgba(74, 222, 128, 0.15)
    'broken': QColor(248, 113, 113, 40),   # Красный полупрозрачный rgba(248, 113, 113, 0.15)
}


class ScrollBlockingTableWidget(QTableWidget):
    """QTableWidget который не пропускает прокрутку к родителю"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        # Запрещаем перетаскивание окна при взаимодействии с таблицей
        self.setProperty("noDrag", True)
    
    def wheelEvent(self, event):
        scrollbar = self.verticalScrollBar()
        delta = event.angleDelta().y()
        
        # Если прокручиваем вверх и уже в начале - блокируем
        if delta > 0 and scrollbar.value() == scrollbar.minimum():
            event.accept()
            return
        
        # Если прокручиваем вниз и уже в конце - блокируем
        if delta < 0 and scrollbar.value() == scrollbar.maximum():
            event.accept()
            return
        
        super().wheelEvent(event)
        event.accept()


class StrategyTableBuilder:
    """Класс для построения и заполнения таблиц стратегий."""
    
    @staticmethod
    def create_strategies_table():
        """Создает и настраивает таблицу стратегий - современный стиль."""
        table = ScrollBlockingTableWidget()
        table.setColumnCount(3)  # Звезда, Стратегия, Метка
        table.setHorizontalHeaderLabels(["", "СТРАТЕГИЯ", "МЕТКА"])
        
        # Настройки таблицы
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        table.verticalHeader().setVisible(False)
        table.setAlternatingRowColors(False)
        table.setShowGrid(False)
        table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        
        # Современный минималистичный стиль
        table.setStyleSheet("""
            QTableWidget {
                background-color: #1a1a1a;
                border: none;
                outline: none;
                selection-background-color: transparent;
            }
            QTableWidget::item {
                padding: 4px 8px;
                color: rgba(255, 255, 255, 0.85);
                border: none;
            }
            QTableWidget::item:hover {
                background-color: rgba(255, 255, 255, 0.05);
            }
            QTableWidget::item:selected {
                background-color: rgba(96, 205, 255, 0.12);
                color: #60cdff;
            }
            QHeaderView::section {
                background-color: #1a1a1a;
                color: rgba(255, 255, 255, 0.45);
                font-weight: 600;
                font-size: 11px;
                padding: 10px 8px;
                border: none;
                border-bottom: 1px solid rgba(255, 255, 255, 0.08);
                text-transform: uppercase;
                letter-spacing: 1px;
            }
            QHeaderView::section:first {
                padding-left: 12px;
            }
            QScrollBar:vertical {
                width: 6px;
                background: transparent;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 0.12);
                border-radius: 3px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(255, 255, 255, 0.2);
            }
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical,
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {
                height: 0px;
                background: none;
            }
        """)
        
        # Настройка колонок
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, header.ResizeMode.Fixed)    # Звезда
        header.setSectionResizeMode(1, header.ResizeMode.Stretch)  # Стратегия
        header.setSectionResizeMode(2, header.ResizeMode.Fixed)    # Метка
        
        table.setColumnWidth(0, 48)   # Звезда
        table.setColumnWidth(2, 130)  # Метка
        table.verticalHeader().setDefaultSectionSize(42)
        
        return table
    
    @staticmethod
    def populate_table(table, strategies, strategy_manager=None, favorite_callback=None, category_key="bat", skip_grouping=False):
        """Заполняет таблицу стратегиями.

        Args:
            table: QTableWidget для заполнения
            strategies: Словарь стратегий {id: info}
            strategy_manager: Менеджер стратегий (опционально)
            favorite_callback: Callback при изменении избранного
            category_key: Ключ категории (bat, json_tcp и т.д.)
            skip_grouping: Если True, не группировать по провайдерам (для сортировки по имени)
        """
        from strategy_menu import get_favorite_strategies

        table.setRowCount(0)
        strategies_map = {}

        # Сохраняем category_key в таблице для использования в обработчиках
        table.category_key = category_key
        table.favorite_callback = favorite_callback

        # === РЕЖИМ БЕЗ ГРУППИРОВКИ (для сортировки по имени) ===
        # При skip_grouping=True показываем ВСЕ стратегии в исходном порядке словаря
        if skip_grouping:
            total_rows = len(strategies)
            table.setRowCount(total_rows)

            current_row = 0
            strategy_number = 1

            for strategy_id, strategy_info in strategies.items():
                strategies_map[current_row] = {
                    'id': strategy_id,
                    'name': strategy_info.get('name') or strategy_id
                }

                StrategyTableBuilder.populate_row(
                    table, current_row, strategy_id,
                    strategy_info, strategy_number, category_key
                )

                current_row += 1
                strategy_number += 1

            return strategies_map

        # === ОБЫЧНЫЙ РЕЖИМ С ГРУППИРОВКОЙ ===

        # Получаем список избранных
        favorites_list = get_favorite_strategies(category_key) or []
        favorites_set = set(favorites_list)

        # Разделяем на избранные и остальные, сохраняя порядок
        favorite_strategies = {}
        regular_strategies = {}

        for strategy_id, strategy_info in strategies.items():
            if strategy_id in favorites_set:
                favorite_strategies[strategy_id] = strategy_info
            else:
                regular_strategies[strategy_id] = strategy_info

        # Группируем обычные по провайдерам
        providers = {}
        for strategy_id, strategy_info in regular_strategies.items():
            provider = strategy_info.get('provider', 'universal')
            if provider not in providers:
                providers[provider] = []
            providers[provider].append((strategy_id, strategy_info))

        sorted_providers = sorted(providers.items())

        # Подсчитываем строки
        total_rows = 0
        if favorite_strategies:
            total_rows += 1 + len(favorite_strategies)  # Заголовок + избранные
        total_rows += sum(1 + len(strategies_list)
                        for provider, strategies_list in sorted_providers)
        table.setRowCount(total_rows)

        current_row = 0

        # === ИЗБРАННЫЕ (вверху) ===
        if favorite_strategies:
            bg_color = QColor(40, 35, 20)  # Тёплый золотистый оттенок

            # Колонка 0: Звезда в заголовке (по центру)
            star_item = QTableWidgetItem("*")
            star_item.setBackground(QBrush(bg_color))
            star_item.setForeground(QBrush(QColor(255, 193, 7)))
            star_item.setFont(QFont("Segoe UI", 12))
            star_item.setTextAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
            star_item.setFlags(Qt.ItemFlag.NoItemFlags)
            table.setItem(current_row, 0, star_item)

            # Колонка 1: Заголовок избранных
            fav_header_item = QTableWidgetItem(f"Избранные ({len(favorite_strategies)})")
            fav_header_font = QFont("Segoe UI", 10)
            fav_header_font.setBold(True)
            fav_header_item.setFont(fav_header_font)
            fav_header_item.setBackground(QBrush(bg_color))
            fav_header_item.setForeground(QBrush(QColor(255, 193, 7)))
            fav_header_item.setFlags(Qt.ItemFlag.NoItemFlags)
            table.setItem(current_row, 1, fav_header_item)

            # Колонка 2: Пустая
            empty_item = QTableWidgetItem("")
            empty_item.setBackground(QBrush(bg_color))
            empty_item.setFlags(Qt.ItemFlag.NoItemFlags)
            table.setItem(current_row, 2, empty_item)

            table.setRowHeight(current_row, 36)
            current_row += 1

            # Добавляем избранные стратегии
            fav_number = 1
            for strategy_id, strategy_info in favorite_strategies.items():
                strategies_map[current_row] = {
                    'id': strategy_id,
                    'name': strategy_info.get('name') or strategy_id
                }

                StrategyTableBuilder.populate_row(
                    table, current_row, strategy_id,
                    strategy_info, fav_number, category_key
                )

                current_row += 1
                fav_number += 1

        # === ОСТАЛЬНЫЕ СТРАТЕГИИ (по провайдерам) ===
        for provider, strategies_list in sorted_providers:
            provider_name = StrategyTableBuilder.get_provider_display_name(provider)
            bg_color = QColor(28, 28, 28)

            # Колонка 0: Пустая ячейка для звезды
            empty_star_item = QTableWidgetItem("")
            empty_star_item.setBackground(QBrush(bg_color))
            empty_star_item.setFlags(Qt.ItemFlag.NoItemFlags)
            table.setItem(current_row, 0, empty_star_item)

            # Колонка 1: Заголовок провайдера
            provider_item = QTableWidgetItem(f"= {provider_name}")
            provider_font = QFont("Segoe UI", 10)
            provider_font.setBold(True)
            provider_item.setFont(provider_font)
            provider_item.setBackground(QBrush(bg_color))
            provider_item.setForeground(QBrush(QColor(255, 255, 255, 140)))
            provider_item.setFlags(Qt.ItemFlag.NoItemFlags)
            table.setItem(current_row, 1, provider_item)

            # Колонка 2: Пустая ячейка
            empty_label_item = QTableWidgetItem("")
            empty_label_item.setBackground(QBrush(bg_color))
            empty_label_item.setFlags(Qt.ItemFlag.NoItemFlags)
            table.setItem(current_row, 2, empty_label_item)

            table.setRowHeight(current_row, 36)
            current_row += 1

            strategy_number = 1
            for strategy_id, strategy_info in strategies_list:
                strategies_map[current_row] = {
                    'id': strategy_id,
                    'name': strategy_info.get('name') or strategy_id
                }
                
                StrategyTableBuilder.populate_row(
                    table, current_row, strategy_id, 
                    strategy_info, strategy_number, category_key
                )
                
                current_row += 1
                strategy_number += 1
        
        return strategies_map
    
    @staticmethod
    def populate_row(table, row, strategy_id, strategy_info, strategy_number=None, category_key="bat"):
        """Заполняет одну строку таблицы."""
        from strategy_menu import get_strategy_rating

        table.setRowHeight(row, 42)

        # Получаем рейтинг стратегии для подсветки (с учетом category_key)
        rating = get_strategy_rating(strategy_id, category_key)
        rating_bg = RATING_COLORS.get(rating) if rating else None

        # Колонка 0: Звезда избранного
        star_widget = StrategyTableBuilder.create_favorite_star(
            table, strategy_id, category_key
        )
        # Если есть рейтинг, добавляем фоновый цвет виджету
        if rating_bg:
            star_widget.setStyleSheet(f"background: rgba({rating_bg.red()}, {rating_bg.green()}, {rating_bg.blue()}, {rating_bg.alpha() / 255:.2f});")
        table.setCellWidget(row, 0, star_widget)

        # Колонка 1: Имя стратегии
        strategy_name = strategy_info.get('name') or strategy_id
        display_name = f"{strategy_number}. {strategy_name}"

        all_sites = StrategyTableBuilder.is_strategy_for_all_sites(strategy_info)
        if all_sites:
            display_name += " [ВСЕ]"

        name_item = QTableWidgetItem(display_name)
        name_item.setFont(QFont("Segoe UI", 10))
        # Подсветка рейтинга
        if rating_bg:
            name_item.setBackground(QBrush(rating_bg))
        table.setItem(row, 1, name_item)

        # Колонка 2: Метка + формат файла
        label = strategy_info.get('label') or None
        format_label = strategy_info.get('format_label')  # TXT или BAT

        label_widget = StrategyTableBuilder.create_label_with_format(
            label, format_label, rating_bg
        )
        table.setCellWidget(row, 2, label_widget)
    
    @staticmethod
    def create_label_with_format(label, format_label, rating_bg=None):
        """Создает виджет с меткой и форматом файла (TXT/BAT)."""
        container = QWidget()
        if rating_bg:
            container.setStyleSheet(f"background: rgba({rating_bg.red()}, {rating_bg.green()}, {rating_bg.blue()}, {rating_bg.alpha() / 255:.2f});")
        else:
            container.setStyleSheet("background: transparent;")

        layout = QHBoxLayout(container)
        layout.setContentsMargins(4, 6, 8, 6)
        layout.setSpacing(6)

        # Метка формата файла (TXT/BAT)
        if format_label:
            format_color = "#4ade80" if format_label == "TXT" else "#60a5fa"  # Зелёный для TXT, синий для BAT
            format_lbl = QLabel(format_label)
            format_lbl.setStyleSheet(f"""
                QLabel {{
                    color: {format_color};
                    font-weight: 600;
                    font-size: 9px;
                    padding: 3px 6px;
                    border: 1px solid {format_color};
                    border-radius: 3px;
                    background: transparent;
                }}
            """)
            format_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(format_lbl)

        # Основная метка (recommended, deprecated, etc.)
        if label and label in LABEL_TEXTS:
            label_text = QLabel(LABEL_TEXTS[label])
            label_color = LABEL_COLORS[label]
            label_text.setStyleSheet(f"""
                QLabel {{
                    color: #ffffff;
                    font-weight: 600;
                    font-size: 10px;
                    padding: 5px 10px;
                    border: none;
                    border-radius: 4px;
                    background-color: {label_color};
                }}
            """)
            label_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(label_text)

        layout.addStretch()
        layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        return container

    @staticmethod
    def create_label_widget(label, rating_bg=None):
        """Создает виджет метки (устаревший, используйте create_label_with_format)."""
        label_widget = QWidget()
        if rating_bg:
            label_widget.setStyleSheet(f"background: rgba({rating_bg.red()}, {rating_bg.green()}, {rating_bg.blue()}, {rating_bg.alpha() / 255:.2f});")
        else:
            label_widget.setStyleSheet("background: transparent;")
        label_layout = QHBoxLayout(label_widget)
        label_layout.setContentsMargins(4, 6, 8, 6)
        label_layout.setSpacing(0)

        label_text = QLabel(LABEL_TEXTS[label])
        label_color = LABEL_COLORS[label]

        label_text.setStyleSheet(f"""
            QLabel {{
                color: #ffffff;
                font-weight: 600;
                font-size: 10px;
            padding: 5px 10px;
                border: none;
            border-radius: 4px;
                background-color: {label_color};
            }}
        """)
        label_text.setAlignment(Qt.AlignmentFlag.AlignCenter)

        label_layout.addWidget(label_text)
        label_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        return label_widget
    
    @staticmethod
    def create_favorite_star(table, strategy_id, category_key):
        """Создает виджет звезды избранного."""
        from strategy_menu import is_favorite_strategy, toggle_favorite_strategy
        
        is_favorite = is_favorite_strategy(strategy_id, category_key)
        
        # Контейнер
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        layout = QHBoxLayout(container)
        layout.setContentsMargins(4, 0, 0, 0)
        layout.setSpacing(0)
        
        # Кнопка-звезда
        star_btn = QPushButton()
        star_btn.setFixedSize(26, 26)
        star_btn.setCheckable(True)
        star_btn.setChecked(is_favorite)
        star_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        star_btn.setFont(QFont("Segoe UI Symbol", 14))
        
        # Сохраняем данные в кнопке
        star_btn.strategy_id = strategy_id
        star_btn.category_key = category_key
        star_btn.table = table
        star_btn.is_favorite = is_favorite
        
        def update_star_style(btn):
            if btn.is_favorite:
                btn.setText("★")
                btn.setToolTip("Убрать из избранных")
                btn.setStyleSheet("""
                    QPushButton {
                        border: none;
                        background: transparent;
                        color: #ffc107;
                        font-size: 18px;
                        padding: 0;
                        margin: 0;
                    }
                    QPushButton:hover {
                        color: #ffca28;
                        background: rgba(255, 193, 7, 0.15);
                        border-radius: 13px;
                    }
                    QPushButton:pressed {
                        color: #ffb300;
                    }
                """)
            else:
                btn.setText("☆")
                btn.setToolTip("Добавить в избранные")
                btn.setStyleSheet("""
                    QPushButton {
                        border: none;
                        background: transparent;
                        color: rgba(255, 255, 255, 0.2);
                        font-size: 18px;
                        padding: 0;
                        margin: 0;
                    }
                    QPushButton:hover {
                        color: #ffc107;
                        background: rgba(255, 193, 7, 0.1);
                        border-radius: 13px;
                    }
                    QPushButton:pressed {
                        color: #ffb300;
                    }
                """)
        
        def on_star_clicked():
            new_state = toggle_favorite_strategy(star_btn.strategy_id, star_btn.category_key)
            star_btn.is_favorite = new_state
            star_btn.setChecked(new_state)
            update_star_style(star_btn)
            
            # Вызываем callback если есть
            if hasattr(star_btn.table, 'favorite_callback') and star_btn.table.favorite_callback:
                star_btn.table.favorite_callback(star_btn.strategy_id, new_state)
        
        update_star_style(star_btn)
        star_btn.clicked.connect(on_star_clicked)
        
        layout.addWidget(star_btn)
        layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        
        return container
    
    @staticmethod
    def is_strategy_for_all_sites(strategy_info):
        """Проверяет, предназначена ли стратегия для всех сайтов."""
        if strategy_info.get('_is_builtin', False):
            return strategy_info.get('all_sites', False)
        
        host_lists = strategy_info.get('host_lists', [])
        if isinstance(host_lists, list):
            for host_list in host_lists:
                if 'all' in str(host_list).lower() or 'все' in str(host_list).lower():
                    return True
        elif isinstance(host_lists, str):
            if 'all' in host_lists.lower() or 'все' in host_lists.lower():
                return True
        
        description = strategy_info.get('description') or ''
        if 'все сайты' in description.lower() or 'всех сайтов' in description.lower():
            return True
            
        name = strategy_info.get('name') or ''
        if 'все сайты' in name.lower() or 'всех сайтов' in name.lower():
            return True
            
        return strategy_info.get('all_sites', False)
    
    @staticmethod
    def get_provider_display_name(provider):
        """Возвращает читаемое название провайдера."""
        provider_names = {
            'universal': 'Универсальные',
            'rostelecom': 'Ростелеком', 
            'mts': 'МТС',
            'megafon': 'МегаФон',
            'tele2': 'Теле2',
            'beeline': 'Билайн',
            'yota': 'Yota',
            'tinkoff': 'Тинькофф Мобайл',
            'other': 'Другие провайдеры'
        }
        return provider_names.get(provider, provider.title())
