# strategy_menu/table_builder.py

from PyQt6.QtWidgets import (QTableWidget, QTableWidgetItem, QWidget, 
                            QHBoxLayout, QLabel)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor, QBrush

from .constants import LABEL_TEXTS, LABEL_COLORS


class StrategyTableBuilder:
    """Класс для построения и заполнения таблиц стратегий."""
    
    @staticmethod
    def create_strategies_table():
        """Создает и настраивает таблицу стратегий."""
        table = QTableWidget()
        table.setColumnCount(3)
        table.setHorizontalHeaderLabels(["Стратегия", "Статус", "Метка"])
        
        # Настройки таблицы
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        table.verticalHeader().setVisible(False)
        table.setAlternatingRowColors(True)
        
        # Стиль таблицы
        table.setStyleSheet("""
            QTableWidget {
                background-color: #2a2a2a;
                alternate-background-color: #333333;
                gridline-color: #444;
                selection-background-color: #2196F3;
                border: 1px solid #444;
                border-radius: 3px;
            }
            QTableWidget::item {
                padding: 2px;
                color: #ffffff;
            }
            QTableWidget::item:selected {
                background-color: #2196F3;
                color: #ffffff;
            }
            QHeaderView::section {
                background-color: #3a3a3a;
                color: #ffffff;
                font-weight: bold;
                padding: 4px;
                border: none;
                border-bottom: 2px solid #2196F3;
            }
        """)
        
        # Настройка колонок
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, header.ResizeMode.Stretch)
        header.setSectionResizeMode(1, header.ResizeMode.Fixed)
        header.setSectionResizeMode(2, header.ResizeMode.Fixed)
        
        table.setColumnWidth(1, 80)
        table.setColumnWidth(2, 100)
        
        table.verticalHeader().setDefaultSectionSize(25)
        
        return table
    
    @staticmethod
    def populate_table(table, strategies, strategy_manager=None):
        """Заполняет таблицу стратегиями."""
        table.setRowCount(0)
        strategies_map = {}
        
        # Группируем по провайдерам
        providers = {}
        for strategy_id, strategy_info in strategies.items():
            provider = strategy_info.get('provider', 'universal')
            if provider not in providers:
                providers[provider] = []
            providers[provider].append((strategy_id, strategy_info))
        
        sorted_providers = sorted(providers.items())
        
        # Подсчитываем строки
        total_rows = sum(1 + len(strategies_list) 
                        for provider, strategies_list in sorted_providers)
        table.setRowCount(total_rows)
        
        current_row = 0
        
        for provider, strategies_list in sorted_providers:
            # Заголовок провайдера
            provider_name = StrategyTableBuilder.get_provider_display_name(provider)
            provider_item = QTableWidgetItem(f"📡 {provider_name}")
            
            provider_font = provider_item.font()
            provider_font.setBold(True)
            provider_font.setPointSize(9)
            provider_item.setFont(provider_font)
            provider_item.setBackground(QBrush(QColor(70, 70, 70)))
            provider_item.setForeground(QBrush(QColor(255, 255, 255)))
            provider_item.setFlags(Qt.ItemFlag.NoItemFlags)
            
            table.setItem(current_row, 0, provider_item)
            table.setSpan(current_row, 0, 1, 3)
            current_row += 1
            
            strategy_number = 1
            for strategy_id, strategy_info in strategies_list:
                strategies_map[current_row] = {
                    'id': strategy_id,
                    'name': strategy_info.get('name', strategy_id)
                }
                
                # Заполняем строку
                StrategyTableBuilder.populate_row(
                    table, current_row, strategy_id, 
                    strategy_info, strategy_manager, strategy_number
                )
                
                current_row += 1
                strategy_number += 1
        
        return strategies_map
    
    @staticmethod
    def populate_row(table, row, strategy_id, strategy_info, 
                    strategy_manager=None, strategy_number=None):
        """Заполняет одну строку таблицы."""
        # Имя стратегии
        strategy_name = strategy_info.get('name', strategy_id)
        display_name = f"  {strategy_number}. {strategy_name}"
        
        all_sites = StrategyTableBuilder.is_strategy_for_all_sites(strategy_info)
        if all_sites:
            display_name += " [ВСЕ]"
        
        name_item = QTableWidgetItem(display_name)
        name_item.setFont(QFont("Arial", 9))
        table.setItem(row, 0, name_item)
        
        # Статус
        if strategy_info.get('_is_builtin', False):
            status_text = "✓ ОК"
            status_color = "#00C800"
        else:
            # Определяем статус для BAT стратегий
            version_status = None
            if strategy_manager:
                version_status = strategy_manager.check_strategy_version_status(strategy_id)
            
            if version_status == 'outdated':
                status_text = "ОБНОВ"
                status_color = "#FF6600"
            elif version_status == 'not_downloaded':
                status_text = "НЕТ"
                status_color = "#CC0000"
            elif version_status == 'unknown':
                status_text = "?"
                status_color = "#888888"
            else:
                status_text = "✓ ОК"
                status_color = "#00C800"
        
        # Создаем виджет для статуса
        status_widget = QWidget()
        status_layout = QHBoxLayout(status_widget)
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_label = QLabel(status_text)
        status_label.setStyleSheet(
            f"color: {status_color}; font-weight: bold; font-size: 8pt;"
        )
        status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status_layout.addWidget(status_label)
        status_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        table.setCellWidget(row, 1, status_widget)
        
        # Метка
        label = strategy_info.get('label', None)
        if label and label in LABEL_TEXTS:
            label_widget = QWidget()
            label_layout = QHBoxLayout(label_widget)
            label_layout.setContentsMargins(0, 0, 0, 0)
            
            label_text = QLabel(LABEL_TEXTS[label])
            label_color = LABEL_COLORS[label]
            
            label_text.setStyleSheet(f"""
                QLabel {{
                    color: {label_color};
                    font-weight: bold;
                    font-size: 8pt;
                    padding: 1px 4px;
                    border: 1px solid {label_color};
                    border-radius: 3px;
                    background-color: {label_color}20;
                }}
            """)
            label_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            label_layout.addWidget(label_text)
            label_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            table.setCellWidget(row, 2, label_widget)
        else:
            empty_widget = QWidget()
            table.setCellWidget(row, 2, empty_widget)
    
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
        
        description = strategy_info.get('description', '').lower()
        if 'все сайты' in description or 'всех сайтов' in description:
            return True
            
        name = strategy_info.get('name', '').lower()
        if 'все сайты' in name or 'всех сайтов' in name:
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