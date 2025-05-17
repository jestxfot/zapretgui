from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, 
                          QPushButton, QTextBrowser, QGroupBox, QSplitter, QListWidgetItem, QWidget, QApplication)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QBrush

from log import log
import os
import re

# Константы для меток стратегий
LABEL_RECOMMENDED = "recommended"
LABEL_CAUTION = "caution"
LABEL_EXPERIMENTAL = "experimental"
LABEL_STABLE = "stable"

# Настройки отображения меток
LABEL_COLORS = {
    LABEL_RECOMMENDED: "#007700",  # Зеленый для рекомендуемых
    LABEL_CAUTION: "#FF6600",      # Оранжевый для стратегий с осторожностью
    LABEL_EXPERIMENTAL: "#CC0000", # Красный для экспериментальных
    LABEL_STABLE: "#0055AA"        # Синий для стабильных
}

LABEL_TEXTS = {
    LABEL_RECOMMENDED: "РЕКОМЕНДУЕМ",
    LABEL_CAUTION: "С ОСТОРОЖНОСТЬЮ",
    LABEL_EXPERIMENTAL: "ЭКСПЕРИМЕНТАЛЬНАЯ",
    LABEL_STABLE: "СТАБИЛЬНАЯ"
}

MINIMUM_WIDTH_STRAG = 500  # Минимальная ширина списка доступных стратегий

MINIMUM_WIDTH = 1000 # Минимальная ширина окна
MINIMIM_HEIGHT = 700 # Минимальная высота окна

class ProviderHeaderItem(QListWidgetItem):
    """Специальный элемент для заголовка группы провайдера"""
    def __init__(self, provider_name):
        super().__init__(f"{provider_name}")
        # Делаем текст жирным
        font = self.font()
        font.setBold(True)
        self.setFont(font)
        # Устанавливаем цвет фона
        self.setBackground(QBrush(QColor(240, 240, 240)))
        # Устанавливаем флаги (не выбираемый)
        self.setFlags(Qt.ItemFlag.NoItemFlags)

class StrategyItem(QWidget):
    """Виджет для отображения элемента стратегии с цветной меткой"""
    def __init__(self, display_name, label=None, sort_order=None, parent=None):
        super().__init__(parent)
        
        # Создаем горизонтальный layout с увеличенными вертикальными отступами
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)  # Увеличиваем вертикальные отступы до 5px
        layout.setSpacing(8)
        
        # Основной текст стратегии
        text = ""
        if sort_order is not None and sort_order != 999:
            text = f"{sort_order}. "
        text += display_name
        
        # Создаем основную метку и задаем ей стиль
        self.main_label = QLabel(text)
        self.main_label.setWordWrap(False)
        # Увеличиваем минимальную высоту метки
        self.main_label.setMinimumHeight(20)
        # Устанавливаем вертикальное выравнивание по центру
        self.main_label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        # Устанавливаем стиль с нормальным размером шрифта
        self.main_label.setStyleSheet("font-size: 10pt; margin: 0; padding: 0;")
        layout.addWidget(self.main_label)
        
        # Добавляем метку если она задана
        if label and label in LABEL_TEXTS:
            self.tag_label = QLabel(LABEL_TEXTS[label])
            # Устанавливаем стиль для метки с фиксированным размером шрифта
            self.tag_label.setStyleSheet(
                f"color: {LABEL_COLORS[label]}; font-weight: bold; font-size: 9pt; margin: 0; padding: 0;"
            )
            self.tag_label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight)
            self.tag_label.setMinimumHeight(20)
            layout.addWidget(self.tag_label)
            layout.addStretch()  # Добавляем растяжение для выравнивания метки вправо
        
        # Устанавливаем минимальную высоту виджета
        self.setMinimumHeight(30)

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
        self.resize(MINIMUM_WIDTH, MINIMIM_HEIGHT)  # Начальный размер окна
        
        self.init_ui()
        self.load_strategies()
        
        # Выбираем текущую стратегию, если она задана
        if current_strategy_name:
            self.select_strategy_by_name(current_strategy_name)

    def auto_refresh_strategies(self):
        """Автоматически обновляет список стратегий при первом запуске."""
        try:
            # Используем механизм обновления без перезагрузки с сервера
            self.load_strategies()
            
            # Восстанавливаем выбор
            if self.current_strategy_name:
                self.select_strategy_by_name(self.current_strategy_name)
        except Exception as e:
            log(f"Ошибка при автообновлении списка стратегий: {str(e)}", level="WARNING")

    def init_ui(self):
        """Инициализация интерфейса."""
        layout = QVBoxLayout(self)
        
        # Добавляем информационный текст о стратегиях в верхней части
        info_text = QLabel(
            "Выберите стратегию обхода блокировок, если вам требуется сменить метод обхода. Подробнее о Zapret читайте в интернете.\n"
            "Стратегии с пометкой \"РЕКОМЕНДУЕМ\" были протестированы и показали наилучшие результаты.\n"
            "Для экспериментальных стратегий есть пометка \"С ОСТОРОЖНОСТЬЮ\"."
        )
        info_text.setWordWrap(True)
        info_text.setStyleSheet("padding: 10px; background-color: #3a3a3a; color: #ffffff; border-radius: 5px;")
        layout.addWidget(info_text)
        
        # Добавляем небольшой интервал
        layout.addSpacing(10)
        
        # Создаем разделитель (сплиттер)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Левая панель - список стратегий
        strategies_group = QGroupBox("Доступные стратегии")
        strategies_layout = QVBoxLayout(strategies_group)
        
        self.strategies_list = QListWidget()
        self.strategies_list.setMinimumWidth(MINIMUM_WIDTH_STRAG)
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
        self.strategy_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_layout.addWidget(self.strategy_title)
        
        # Детальная информация о стратегии
        self.strategy_info = QTextBrowser()
        self.strategy_info.setOpenExternalLinks(True)
        # Устанавливаем явные цвета текста и фона для совместимости с тёмной темой
        self.strategy_info.setStyleSheet("background-color: #333333; color: #ffffff;")
        info_layout.addWidget(self.strategy_info)
        
        # Добавляем панели в сплиттер
        splitter.addWidget(strategies_group)
        splitter.addWidget(info_group)
        splitter.setSizes([450, 550])  # Увеличиваем размер панели стратегий
        
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
            
            # Сортируем стратегии по провайдеру и полю sort_order
            sorted_strategies = sorted(
                strategies.items(), 
                key=lambda x: (
                    # Первый критерий: провайдер
                    x[1].get('provider', 'zzzz'),
                    # Второй критерий: sort_order (если есть)
                    x[1].get('sort_order', 999),
                    # Третий критерий: название
                    x[1].get('name', '')
                )
            )
            
            # Группируем стратегии по провайдерам
            provider_groups = {}
            for strategy_id, strategy_info in sorted_strategies:
                provider = strategy_info.get('provider', 'Универсальные')
                if provider not in provider_groups:
                    provider_groups[provider] = []
                provider_groups[provider].append((strategy_id, strategy_info))
            
            # Добавляем стратегии в список с разделителями по провайдерам
            self.strategies_map = {}  # Для хранения соответствия индекса строки и ID стратегии
            row = 0
            
            # Сортируем провайдеров
            providers = sorted(provider_groups.keys())
            
            # Перемещаем "Универсальные" в конец списка
            if "Универсальные" in providers:
                providers.remove("Универсальные")
                providers.append("Универсальные")
            
            for provider in providers:
                # Добавляем заголовок провайдера
                header_item = ProviderHeaderItem(provider)
                self.strategies_list.addItem(header_item)
                row += 1
                
                # Добавляем стратегии этого провайдера
                for strategy_id, strategy_info in provider_groups[provider]:
                    display_name = strategy_info.get('name', strategy_id)
                    
                    # Создаем элемент списка
                    item = QListWidgetItem()
                    self.strategies_list.addItem(item)
                    
                    # Создаем виджет с цветной меткой
                    label = strategy_info.get('label', None)
                    sort_order = strategy_info.get('sort_order', 999)
                    
                    # Создаем кастомный виджет с цветной меткой
                    item_widget = StrategyItem(
                        display_name=display_name,
                        label=label,
                        sort_order=sort_order if sort_order != 999 else None
                    )
                    
                    from PyQt6.QtCore import QSize
                    # Устанавливаем размер элемента списка и виджет
                    item.setSizeHint(QSize(self.strategies_list.width(), 30))
                    self.strategies_list.setItemWidget(item, item_widget)
                    
                    # Сохраняем соответствие
                    self.strategies_map[row] = {'id': strategy_id, 'name': display_name}
                    row += 1
            
            log(f"Загружено {len(strategies)} стратегий", level="INFO")

            # Принудительное обновление UI через несколько механизмов
            # 1. Обработка всех ожидающих событий приложения
            QApplication.processEvents()
            
            # 2. Обновление списка
            self.strategies_list.repaint()
            
            # 3. Повторная обработка событий
            QApplication.processEvents()
            
            # 4. Обновление с задержкой
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(100, self.update_all_items)
                
        except Exception as e:
            log(f"Ошибка при загрузке списка стратегий: {str(e)}", level="ERROR")
            self.strategy_info.setHtml(f"<p style='color:red'>Ошибка: {str(e)}</p>")

    def update_all_items(self):
        """Обновляет все элементы списка для принудительной отрисовки."""
        try:
            # Обновляем каждый элемент списка
            for i in range(self.strategies_list.count()):
                item = self.strategies_list.item(i)
                # Заставляем элемент перерисоваться
                widget = self.strategies_list.itemWidget(item)
                if widget:
                    widget.update()
            
            # Обновляем весь список
            self.strategies_list.update()
            self.strategies_list.repaint()
            
            # Обработка событий для правильного отображения
            QApplication.processEvents()
        except Exception as e:
            log(f"Ошибка при обновлении элементов списка: {str(e)}", level="WARNING")
            
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
        
        # Включаем кнопку выбора
        self.select_button.setEnabled(True)
        
        # Получаем информацию о стратегии
        try:
            strategies = self.strategy_manager.get_strategies_list()
            if strategy_id in strategies:
                strategy_info = strategies[strategy_id]
                
                # Устанавливаем заголовок
                title_text = strategy_info.get('name', strategy_id)
                
                # Добавляем метку к заголовку, если есть
                label = strategy_info.get('label', None)
                if label and label in LABEL_TEXTS:
                    title_text += f" [{LABEL_TEXTS[label]}]"
                    # Устанавливаем цвет заголовка согласно метке
                    label_color = LABEL_COLORS.get(label, "#000000")
                    self.strategy_title.setStyleSheet(f"color: {label_color};")
                else:
                    # Сбрасываем цвет на стандартный
                    self.strategy_title.setStyleSheet("")
                
                self.strategy_title.setText(title_text)
                
                # Формируем HTML для отображения информации с явными цветами
                html = "<style>body {font-family: Arial; margin: 10px; color: #ffffff; background-color: #333333;}</style>"
                
                # Метка (если есть) - добавляем с соответствующим цветом и стилем
                if label and label in LABEL_TEXTS:
                    html += f"<p style='text-align: center; padding: 5px; background-color: {LABEL_COLORS.get(label, '#000000')}; color: white; font-weight: bold;'>{LABEL_TEXTS[label]}</p>"
                
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
                    html += "<p><b>Статус:</b> <span style='color:#00ff00'>Файл скачан и готов к использованию</span></p>"
                else:
                    html += "<p><b>Статус:</b> <span style='color:#ffcc00'>Файл будет скачан при выборе стратегии</span></p>"

                # Порты и списки хостов
                html += "<hr>"
                html += "<h3>Технические детали:</h3>"
                
                # Порты
                ports = strategy_info.get('ports', [])
                if ports:
                    if isinstance(ports, list):
                        ports_str = ", ".join(map(str, ports))
                    else:
                        ports_str = str(ports)
                    html += f"<p><b>Используемые порты:</b> {ports_str}</p>"
                else:
                    html += "<p><b>Используемые порты:</b> НЕИЗВЕСТНО</p>"
                
                # Списки хостов
                host_lists = strategy_info.get('host_lists', [])
                if host_lists:
                    html += "<p><b>Используемые списки хостов:</b></p><ul>"
                    if isinstance(host_lists, list):
                        for host_list in host_lists:
                            html += f"<li>{host_list}</li>"
                    else:
                        html += f"<li>{host_lists}</li>"
                    html += "</ul>"
                else:
                    html += "<p><b>Используемые списки хостов:</b> НЕИЩВЕСТНО</p>"
                
                # Дополнительные технические детали
                use_https = strategy_info.get('use_https', True)
                html += f"<p><b>Использование HTTPS:</b> {'Да' if use_https else 'Нет'}</p>"
                
                fragments = strategy_info.get('fragments', False)
                if fragments:
                    html += f"<p><b>Фрагментирование пакетов:</b> Да</p>"
                
                ttl = strategy_info.get('ttl', None)
                if ttl:
                    html += f"<p><b>TTL:</b> {ttl}</p>"
                
                # После вывода технических деталей и перед заключительным примечанием
                ttl = strategy_info.get('ttl', None)
                if ttl:
                    html += f"<p><b>TTL:</b> {ttl}</p>"
                
                # Добавляем полную командную строку запуска
                html += "<hr>"
                html += "<h3>Аргументы командной строки:</h3>"

                command_args = strategy_info.get('command_args', None)

                def format_command_args(cmd_line):
                    """Форматирует командную строку для удобного отображения."""
                    # Добавляем переносы строк для улучшения читаемости
                    cmd_line = cmd_line.replace(" --", "<br>--")
                    # Выделяем разными цветами названия хостлистов и другие важные параметры
                    cmd_line = cmd_line.replace("--hostlist=", "--hostlist=<span style='color:#8cff66'>")
                    cmd_line = cmd_line.replace(".txt", ".txt</span>")
                    cmd_line = cmd_line.replace("--filter-tcp=", "--filter-tcp=<span style='color:#66ccff'>")
                    cmd_line = cmd_line.replace("--filter-udp=", "--filter-udp=<span style='color:#ff9966'>")
                    cmd_line = cmd_line.replace("--wf-tcp=", "--wf-tcp=<span style='color:#66ccff'>")
                    cmd_line = cmd_line.replace("--wf-udp=", "--wf-udp=<span style='color:#ff9966'>")
                    cmd_line = cmd_line.replace(" --new", " <span style='color:#ffcc00'>--new</span>")
                    return cmd_line

                if command_args:
                    # Используем предопределенные аргументы из JSON
                    formatted_args = format_command_args(command_args)
                    html += f"<div style='background-color: #222222; padding: 10px; overflow-x: auto; color: #ffff00; max-width: 100%; word-wrap: break-word;'>{formatted_args}</div>"
                else:
                    # Пытаемся прочитать аргументы из BAT-файла
                    try:
                        file_path = strategy_info.get('file_path', None)
                        if file_path:
                            local_path = os.path.join(self.strategy_manager.local_dir, file_path)
                            if os.path.exists(local_path):
                                with open(local_path, 'r', encoding='utf-8', errors='ignore') as f:
                                    bat_content = f.read()
                                    
                                    # Ищем VBScript блок, как в примере
                                    if '"%vbsSilent%" (' in bat_content:
                                        # Ищем все строки с "echo cmd = cmd ^& ""
                                        cmd_lines = re.findall(r'echo cmd = cmd \^& "(.*?)"', bat_content)
                                        
                                        if cmd_lines:
                                            # Собираем полную команду
                                            full_cmd = 'winws.exe'
                                            for line in cmd_lines:
                                                full_cmd += ' ' + line.replace('^&', '&').replace('""', '"')
                                            formatted_cmd = format_command_args(full_cmd)
                                            html += f"<div style='background-color: #222222; padding: 10px; overflow-x: auto; color: #ffff00; max-width: 100%; word-wrap: break-word;'>{formatted_cmd}</div>"
                                            # Ищем строку с winws.exe
                                            match = re.search(r'cmd = .+ \^& "(.+?)winws\.exe(.+?)("|\r?\n|$)', bat_content)
                                            if match:
                                                cmd_line = "winws.exe" + match.group(2).strip()
                                                html += f"<pre style='background-color: #222222; padding: 10px; overflow-x: auto; color: #ffff00;'>{cmd_line}</pre>"
                                            else:
                                                # Простой поиск любой строки с winws.exe и аргументами
                                                match = re.search(r'winws\.exe\s+(.+?)(\r?\n|$)', bat_content)
                                                if match:
                                                    cmd_line = "winws.exe " + match.group(1).strip()
                                                    html += f"<pre style='background-color: #222222; padding: 10px; overflow-x: auto; color: #ffff00;'>{cmd_line}</pre>"
                                                else:
                                                    html += "<p><i>Команда запуска не найдена в формате VBScript или CMD.</i></p>"
                                    else:
                                        # Простой поиск любой строки с winws.exe и аргументами
                                        match = re.search(r'winws\.exe\s+(.+?)(\r?\n|$)', bat_content)
                                        if match:
                                            cmd_line = "winws.exe " + match.group(1).strip()
                                            html += f"<pre style='background-color: #222222; padding: 10px; overflow-x: auto; color: #ffff00;'>{cmd_line}</pre>"
                                        else:
                                            html += "<p><i>Команда запуска не найдена в BAT-файле стратегии.</i></p>"
                            else:
                                html += "<p><i>BAT-файл стратегии будет скачан при выборе. Аргументы будут доступны после загрузки.</i></p>"
                        else:
                            html += "<p><i>Информация о файле стратегии отсутствует.</i></p>"
                    except Exception as e:
                        html += f"<p><i>Не удалось прочитать аргументы командной строки: {str(e)}</i></p>"
                
                # Продолжаем с заключительным примечанием
                html += "<hr>"
                html += "<p><i>Примечание: Вышеуказанные технические детали могут меняться при обновлении стратегии.</i></p>"
                
                # Устанавливаем HTML
                self.strategy_info.setHtml(html)
            else:
                self.strategy_info.setHtml("<p style='color:red'>Информация о стратегии не найдена</p>")
        except Exception as e:
            log(f"Ошибка при получении информации о стратегии: {str(e)}", level="ERROR")
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