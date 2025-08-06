# strategy_menu/selector.py

import sys
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, 
                          QPushButton, QTextBrowser, QGroupBox, QSplitter, QListWidgetItem, QWidget, QApplication,
                          QTableWidget, QTableWidgetItem, QToolButton, QSizePolicy, QProgressBar, QHeaderView, QCheckBox, QAbstractItemView,
                          QTabWidget, QRadioButton, QButtonGroup)
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
LABEL_WARP = "warp"

# Настройки отображения меток
LABEL_COLORS = {
    LABEL_RECOMMENDED: "#00B900",  # Зеленый для рекомендуемых
    LABEL_CAUTION: "#FF6600",      # Оранжевый для стратегий с осторожностью
    LABEL_EXPERIMENTAL: "#CC0000", # Красный для экспериментальных
    LABEL_STABLE: "#006DDA",       # Синий для стабильных
    LABEL_WARP: "#EE850C"          # Оранжевый для WARP
}

LABEL_TEXTS = {
    LABEL_RECOMMENDED: "РЕКОМЕНДУЕМ",
    LABEL_CAUTION: "С ОСТОРОЖНОСТЬЮ",
    LABEL_EXPERIMENTAL: "ЭКСПЕРИМЕНТАЛЬНАЯ",
    LABEL_STABLE: "СТАБИЛЬНАЯ",
    LABEL_WARP: "WARP"
}

MINIMUM_WIDTH_STRAG = 800  # Увеличиваем ширину для таблицы
MINIMUM_WIDTH = 900  # Уменьшаем минимальную ширину основного окна
MINIMIM_HEIGHT = 700  # Минимальная высота окна

class StrategyInfoDialog(QDialog):
    """Отдельное окно для отображения подробной информации о стратегии."""
    
    def __init__(self, parent=None, strategy_manager=None):
        super().__init__(parent)
        self.strategy_manager = strategy_manager
        self.setWindowTitle("Информация о стратегии")
        self.resize(800, 600)
        self.init_ui()
    
    def init_ui(self):
        """Инициализация интерфейса окна информации."""
        layout = QVBoxLayout(self)
        
        # Заголовок стратегии
        self.strategy_title = QLabel("Информация о стратегии")
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(14)
        self.strategy_title.setFont(title_font)
        self.strategy_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.strategy_title)
        
        # Детальная информация о стратегии
        self.strategy_info = QTextBrowser()
        self.strategy_info.setOpenExternalLinks(True)
        # Устанавливаем явные цвета текста и фона для совместимости с тёмной темой
        self.strategy_info.setStyleSheet("background-color: #333333; color: #ffffff;")
        layout.addWidget(self.strategy_info)
        
        # Кнопка закрытия
        close_button = QPushButton("Закрыть")
        close_button.clicked.connect(self.close)
        layout.addWidget(close_button)
    
    def display_strategy_info(self, strategy_id, strategy_name):
        """Отображает информацию о выбранной стратегии."""
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
                    html += f"<p style='text-align: center; padding: 8px; background-color: {LABEL_COLORS.get(label, '#000000')}; color: white; font-weight: bold; font-size: 14px; border-radius: 5px;'>{LABEL_TEXTS[label]}</p>"
                
                # Описание
                description = strategy_info.get('description', 'Описание отсутствует')
                html += f"<h3>Описание</h3><p>{description}</p>"
                
                # Основная информация
                html += "<h3>Основная информация</h3>"
                
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
                if self.strategy_manager:
                    local_path = os.path.join(self.strategy_manager.local_dir, file_path)
                    if os.path.exists(local_path):
                        html += "<p><b>Статус:</b> <span style='color:#00ff00; font-weight: bold;'>✓ Файл скачан и готов к использованию</span></p>"
                    else:
                        html += "<p><b>Статус:</b> <span style='color:#ffcc00; font-weight: bold;'>⚠ Файл будет скачан при выборе стратегии</span></p>"

                # Технические детали
                html += "<hr><h3>Технические детали</h3>"
                
                # Порты
                ports = strategy_info.get('ports', [])
                if ports:
                    if isinstance(ports, list):
                        ports_str = ", ".join(map(str, ports))
                    else:
                        ports_str = str(ports)
                    html += f"<p><b>Используемые порты:</b> {ports_str}</p>"
                else:
                    html += "<p><b>Используемые порты:</b> 80, 443 (по умолчанию)</p>"
                
                # Списки хостов
                host_lists = strategy_info.get('host_lists', [])
                if host_lists:
                    html += "<p><b>Используемые списки хостов:</b></p><ul style='margin-left: 20px;'>"
                    if isinstance(host_lists, list):
                        for host_list in host_lists:
                            html += f"<li>{host_list}</li>"
                    else:
                        html += f"<li>{host_lists}</li>"
                    html += "</ul>"
                else:
                    html += "<p><b>Используемые списки хостов:</b> <span style='color:#00ff00; font-weight: bold;'>• ВСЕ САЙТЫ</span></p>"
                
                # Дополнительные технические детали
                use_https = strategy_info.get('use_https', True)
                html += f"<p><b>Использование HTTPS:</b> {'Да' if use_https else 'Нет'}</p>"
                
                fragments = strategy_info.get('fragments', False)
                if fragments:
                    html += f"<p><b>Фрагментирование пакетов:</b> Да</p>"
                
                ttl = strategy_info.get('ttl', None)
                if ttl:
                    html += f"<p><b>TTL:</b> {ttl}</p>"
                
                # Командная строка
                html += "<hr><h3>Аргументы командной строки</h3>"

                command_args = strategy_info.get('command_args', None)

                def format_command_args(cmd_line):
                    """Форматирует командную строку для удобного отображения."""
                    # Добавляем переносы строк для улучшения читаемости
                    cmd_line = cmd_line.replace(" --", "<br>&nbsp;&nbsp;--")
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
                    html += f"<div style='background-color: #222222; padding: 15px; overflow-x: auto; color: #ffff00; border-radius: 5px; font-family: monospace; word-wrap: break-word;'>{formatted_args}</div>"
                else:
                    # Пытаемся прочитать аргументы из BAT-файла
                    try:
                        file_path = strategy_info.get('file_path', None)
                        if file_path and self.strategy_manager:
                            local_path = os.path.join(self.strategy_manager.local_dir, file_path)
                            if os.path.exists(local_path):
                                with open(local_path, 'r', encoding='utf-8', errors='ignore') as f:
                                    bat_content = f.read()
                                    
                                    # Ищем VBScript блок
                                    if '"%vbsSilent%" (' in bat_content:
                                        # Ищем все строки с "echo cmd = cmd ^& ""
                                        cmd_lines = re.findall(r'echo cmd = cmd \^& "(.*?)"', bat_content)
                                        
                                        if cmd_lines:
                                            # Собираем полную команду
                                            full_cmd = 'winws.exe'
                                            for line in cmd_lines:
                                                full_cmd += ' ' + line.replace('^&', '&').replace('""', '"')
                                            formatted_cmd = format_command_args(full_cmd)
                                            html += f"<div style='background-color: #222222; padding: 15px; overflow-x: auto; color: #ffff00; border-radius: 5px; font-family: monospace; word-wrap: break-word;'>{formatted_cmd}</div>"
                                        else:
                                            html += "<p><i>Команда запуска не найдена в формате VBScript.</i></p>"
                                    else:
                                        # Простой поиск любой строки с winws.exe и аргументами
                                        match = re.search(r'winws\.exe\s+(.+?)(\r?\n|$)', bat_content)
                                        if match:
                                            cmd_line = "winws.exe " + match.group(1).strip()
                                            formatted_cmd = format_command_args(cmd_line)
                                            html += f"<div style='background-color: #222222; padding: 15px; overflow-x: auto; color: #ffff00; border-radius: 5px; font-family: monospace; word-wrap: break-word;'>{formatted_cmd}</div>"
                                        else:
                                            html += "<p><i>Команда запуска не найдена в BAT-файле.</i></p>"
                            else:
                                html += "<p><i>BAT-файл стратегии будет скачан при выборе. Аргументы будут доступны после загрузки.</i></p>"
                        else:
                            html += "<p><i>Информация о файле стратегии отсутствует.</i></p>"
                    except Exception as e:
                        html += f"<p><i>Не удалось прочитать аргументы командной строки: {str(e)}</i></p>"
                
                # Заключительное примечание
                html += "<hr><p style='font-style: italic; color: #cccccc;'>Примечание: Технические детали могут изменяться при обновлении стратегии.</p>"
                
                # Устанавливаем HTML
                self.strategy_info.setHtml(html)
            else:
                self.strategy_info.setHtml("<p style='color:red; text-align: center;'>Информация о стратегии не найдена</p>")
        except Exception as e:
            log(f"Ошибка при получении информации о стратегии: {str(e)}", level="❌ ERROR")
            self.strategy_info.setHtml(f"<p style='color:red; text-align: center;'>Ошибка: {str(e)}</p>")

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
    """Виджет для отображения элемента стратегии с цветной меткой и статусом версии"""
    def __init__(self, display_name, label=None, strategy_number=None, version_status=None, parent=None):
        super().__init__(parent)
        
        # Создаем горизонтальный layout с увеличенными вертикальными отступами
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)  # Увеличиваем вертикальные отступы до 5px
        layout.setSpacing(8)
        
        # Основной текст стратегии
        text = ""
        if strategy_number is not None:
            text = f"{strategy_number}. "
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
        
        # Добавляем статус версии если есть
        if version_status and version_status != 'current':
            version_text = ""
            version_color = ""
            
            if version_status == 'outdated':
                version_text = "ОБНОВИТЬ"
                version_color = "#FF6600"  # Оранжевый
            elif version_status == 'not_downloaded':
                version_text = "НЕ СКАЧАНА"
                version_color = "#CC0000"  # Красный
            elif version_status == 'unknown':
                version_text = "?"
                version_color = "#888888"  # Серый
                
            if version_text:
                self.version_label = QLabel(version_text)
                self.version_label.setStyleSheet(
                    f"color: {version_color}; font-weight: bold; font-size: 8pt; margin: 0; padding: 2px 4px; "
                    f"border: 1px solid {version_color}; border-radius: 3px;"
                )
                self.version_label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignCenter)
                self.version_label.setMinimumHeight(16)
                layout.addWidget(self.version_label)
        
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
            
        layout.addStretch()  # Добавляем растяжение для выравнивания меток вправо
        
        # Устанавливаем минимальную высоту виджета
        self.setMinimumHeight(30)

class StrategySelector(QDialog):
    """Асинхронный диалог для выбора стратегии с подробной информацией."""
    
    strategySelected = pyqtSignal(str, str)  # Сигнал: (strategy_id, strategy_name)
    
    def __init__(self, parent=None, strategy_manager=None, current_strategy_name=None):
        super().__init__(parent)
        self.strategy_manager = strategy_manager
        self.current_strategy_name = current_strategy_name
        self.selected_strategy_id = None
        self.selected_strategy_name = None
        self.info_dialog = None
        
        # Флаги для предотвращения множественных операций
        self.is_loading_strategies = False
        self.is_downloading = False
        
        # Потоки для асинхронных операций
        self.loader_thread = None
        self.loader_worker = None
        self.download_thread = None
        self.download_worker = None
        
        # ✅ НОВОЕ: Определяем источник данных
        from config import get_strategy_launch_method
        self.launch_method = get_strategy_launch_method()
        self.is_direct_mode = (self.launch_method == "direct")
        
        self.setWindowTitle("Выбор стратегии обхода блокировок")
        self.resize(MINIMUM_WIDTH, MINIMIM_HEIGHT)
        self.setModal(False)
        
        self.init_ui()
        
        # ✅ ЗАГРУЖАЕМ СТРАТЕГИИ В ЗАВИСИМОСТИ ОТ РЕЖИМА
        if self.is_direct_mode:
            self.load_builtin_strategies()
        else:
            self.load_local_strategies_only()

    def load_builtin_strategies(self):
        """✅ ОБНОВЛЕННЫЙ: Загружает встроенные стратегии из strategy_definitions.py"""
        try:
            self.status_label.setText("📦 Переключение на встроенные стратегии...")
            self.status_label.setStyleSheet("font-weight: bold; color: #2196F3; padding: 5px;")
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 0)  # Неопределенный прогресс
            
            # Небольшая задержка для плавности UI
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(100, self._load_builtin_strategies_impl)
            
        except Exception as e:
            log(f"Ошибка загрузки встроенных стратегий: {e}", "❌ ERROR")
            self.status_label.setText(f"❌ Ошибка: {e}")
            self.status_label.setStyleSheet("font-weight: bold; color: #f44336; padding: 5px;")
            self.progress_bar.setVisible(False)

    def _load_builtin_strategies_impl(self):
        """✅ НОВЫЙ: Внутренний метод для загрузки встроенных стратегий"""
        try:
            # Импортируем встроенные стратегии
            from strategy_menu.strategy_definitions import get_all_strategies
            strategies = get_all_strategies()
            
            if strategies:
                self.status_label.setText(f"✅ Загружено {len(strategies)} встроенных стратегий")
                self.status_label.setStyleSheet("font-weight: bold; color: #4CAF50; padding: 5px;")
                
                # Конвертируем формат для совместимости
                converted_strategies = self.convert_builtin_to_index_format(strategies)
                self.populate_strategies_table(converted_strategies)
                
                self.strategies_table.setEnabled(True)
                self.refresh_button.setEnabled(True)
                # Скрываем кнопку скачивания для встроенных стратегий
                self.download_all_button.setVisible(False)
                
                # Выбираем текущую стратегию
                if self.current_strategy_name:
                    self.select_strategy_by_name(self.current_strategy_name)
                    
                log(f"Встроенные стратегии загружены: {len(strategies)} элементов", "INFO")
            else:
                self.status_label.setText("⚠️ Встроенные стратегии не найдены")
                self.status_label.setStyleSheet("font-weight: bold; color: #ff9800; padding: 5px;")
                
        except Exception as e:
            log(f"Ошибка загрузки встроенных стратегий: {e}", "❌ ERROR")
            self.status_label.setText(f"❌ Ошибка: {e}")
            self.status_label.setStyleSheet("font-weight: bold; color: #f44336; padding: 5px;")
        
        finally:
            self.progress_bar.setVisible(False)

    def load_local_strategies_only(self):
        """✅ ОБНОВЛЕННЫЙ: Загружает только локальные стратегии без интернета"""
        # Обновляем UI
        self.status_label.setText("📂 Переключение на .bat стратегии...")
        self.status_label.setStyleSheet("font-weight: bold; color: #2196F3; padding: 5px;")
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        
        # Небольшая задержка для плавности UI
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(100, self._load_local_strategies_impl)

    def _load_local_strategies_impl(self):
        """✅ НОВЫЙ: Внутренний метод для загрузки локальных стратегий"""
        try:
            # Загружаем только локальные стратегии
            strategies = self.strategy_manager.get_local_strategies_only()
            
            if strategies:
                self.status_label.setText(f"✅ Загружено {len(strategies)} локальных стратегий")
                self.status_label.setStyleSheet("font-weight: bold; color: #4CAF50; padding: 5px;")
                self.populate_strategies_table(strategies)
                self.strategies_table.setEnabled(True)
                self.refresh_button.setEnabled(True)
                self.download_all_button.setEnabled(True)
                self.download_all_button.setVisible(True)
                
                # Выбираем текущую стратегию
                if self.current_strategy_name:
                    self.select_strategy_by_name(self.current_strategy_name)
                    
                log(f"Локальные .bat стратегии загружены: {len(strategies)} элементов", "INFO")
            else:
                self.status_label.setText("⚠️ Локальные стратегии не найдены. Нажмите 'Обновить' для загрузки из интернета")
                self.status_label.setStyleSheet("font-weight: bold; color: #ff9800; padding: 5px;")
                self.refresh_button.setEnabled(True)
                self.download_all_button.setVisible(True)
                
        except Exception as e:
            log(f"Ошибка загрузки локальных стратегий: {e}", "❌ ERROR")
            self.status_label.setText(f"❌ Ошибка: {e}")
            self.status_label.setStyleSheet("font-weight: bold; color: #f44336; padding: 5px;")
            self.refresh_button.setEnabled(True)
            self.download_all_button.setVisible(True)
        
        finally:
            self.progress_bar.setVisible(False)

    def convert_builtin_to_index_format(self, builtin_strategies):
        """Конвертирует формат встроенных стратегий в формат index.json для совместимости"""
        converted = {}
        
        for strategy_id, strategy_data in builtin_strategies.items():
            converted[strategy_id] = {
                'name': strategy_data.get('name', strategy_id),
                'description': strategy_data.get('description', ''),
                'version': strategy_data.get('version', '1.0'),
                'provider': strategy_data.get('provider', 'universal'),
                'author': strategy_data.get('author', 'Unknown'),
                'updated': strategy_data.get('updated', '2024'),
                'label': strategy_data.get('label', 'stable'),
                'ports': strategy_data.get('ports', [80, 443]),
                'host_lists': self.extract_host_lists_from_builtin(strategy_data),
                'fragments': strategy_data.get('fragments', False),
                'use_https': strategy_data.get('use_https', True),
                'all_sites': strategy_data.get('all_sites', False),
                # Специальное поле для встроенных стратегий
                '_is_builtin': True,
                '_args': strategy_data.get('args', [])
            }
        
        return converted

    def extract_host_lists_from_builtin(self, strategy_data):
        """Извлекает список хостлистов из аргументов встроенной стратегии"""
        args = strategy_data.get('args', [])
        host_lists = []
        
        for arg in args:
            if arg.startswith('--hostlist='):
                filename = arg.split('=', 1)[1]
                if filename not in host_lists:
                    host_lists.append(filename)
            elif arg.startswith('--ipset='):
                filename = arg.split('=', 1)[1]
                if filename not in host_lists:
                    host_lists.append(filename)
        
        # Если нет хостлистов, считаем что для всех сайтов
        if not host_lists:
            return ['ВСЕ САЙТЫ']
        
        return host_lists

    def _on_toggle_description(self, checked: bool):
        self.desc_widget.setVisible(checked)
        self.toggle_btn.setArrowType(
            Qt.ArrowType.DownArrow if checked else Qt.ArrowType.RightArrow)

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Создаем виджет с вкладками
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # Вкладка 1: Список стратегий
        self.strategies_tab = QWidget()
        self._init_strategies_tab()
        self.tab_widget.addTab(self.strategies_tab, "Стратегии")
        
        # Вкладка 2: Настройки
        self.settings_tab = QWidget()
        self._init_settings_tab()
        self.tab_widget.addTab(self.settings_tab, "Настройки запуска")
        
        # ✅ СОЗДАЕМ КНОПКИ СНАЧАЛА
        self.buttons_layout = QHBoxLayout()
        
        self.select_button = QPushButton("✅ Выбрать стратегию")
        self.select_button.clicked.connect(self.accept)
        self.select_button.setEnabled(False)
        self.buttons_layout.addWidget(self.select_button)
        
        self.cancel_button = QPushButton("❌ Отмена")
        self.cancel_button.clicked.connect(self.reject)
        self.buttons_layout.addWidget(self.cancel_button)
        
        # ✅ СОЗДАЕМ КОНТЕЙНЕР ДЛЯ КНОПОК
        self.buttons_widget = QWidget()
        self.buttons_widget.setLayout(self.buttons_layout)
        layout.addWidget(self.buttons_widget)
        
        # ✅ ПОДКЛЮЧАЕМ ОБРАБОТЧИК ТОЛЬКО ПОСЛЕ СОЗДАНИЯ ВСЕХ ЭЛЕМЕНТОВ
        self.tab_widget.currentChanged.connect(self._on_tab_changed)

    def _on_tab_changed(self, index):
        """✅ МАКСИМАЛЬНО БЕЗОПАСНЫЙ: Обработчик смены вкладок"""
        # Проверяем все необходимые атрибуты
        required_attrs = ['buttons_widget', 'select_button', 'cancel_button']
        for attr in required_attrs:
            if not hasattr(self, attr) or getattr(self, attr) is None:
                log(f"Атрибут {attr} еще не создан, пропускаем обработку", "DEBUG")
                return
        
        try:
            if index == 0:  # Вкладка "Стратегии"
                self.buttons_widget.setVisible(True)
                log("Переключение на вкладку 'Стратегии' - показываем кнопки", "DEBUG")
            elif index == 1:  # Вкладка "Настройки запуска"
                self.buttons_widget.setVisible(False)
                log("Переключение на вкладку 'Настройки' - скрываем кнопки", "DEBUG")
            else:
                log(f"Неизвестная вкладка с индексом {index}", "DEBUG")
        except Exception as e:
            log(f"Ошибка в _on_tab_changed: {e}", "❌ ERROR")
            # Не пробрасываем исключение дальше, чтобы не крашить приложение

    def _init_strategies_tab(self):
        """Инициализирует вкладку со списком стратегий"""
        layout = QVBoxLayout(self.strategies_tab)

        # ────────── Заголовок + мини-кнопка ──────────
        header = QWidget()
        header_lay = QHBoxLayout(header)
        header_lay.setContentsMargins(0, 0, 0, 0)
        header_lay.setSpacing(4)

        self.toggle_btn = QToolButton()
        self.toggle_btn.setCheckable(True)
        self.toggle_btn.setChecked(False)                           # скрыто по умолч.
        self.toggle_btn.setArrowType(Qt.ArrowType.RightArrow)
        self.toggle_btn.setToolButtonStyle(
            Qt.ToolButtonStyle.ToolButtonIconOnly)                  # ← только иконка
        self.toggle_btn.setFixedSize(18, 18)
        self.toggle_btn.setStyleSheet("QToolButton{border:none;padding:0;}")

        title_lbl = QLabel("Описание")                              # подпись (по желанию)
        title_lbl.setStyleSheet("font-weight:bold;")

        header_lay.addWidget(self.toggle_btn)
        header_lay.addWidget(title_lbl)
        header_lay.addStretch()

        layout.addWidget(header)

        # ────────── Описание (сначала скрыто) ──────────
        self.desc_widget = QWidget()
        self.desc_widget.setVisible(False)                          # вот оно – скрываем
        self.desc_widget.setSizePolicy(QSizePolicy.Policy.Expanding,
                                       QSizePolicy.Policy.Preferred)

        desc_lay = QVBoxLayout(self.desc_widget)
        desc_lay.setContentsMargins(0, 0, 0, 0)

        info_text = QLabel(
            "Выберите стратегию обхода блокировок, если вам требуется сменить метод обхода. "
            "Подробнее о Zapret читайте в интернете.\n"
            "Стратегии с пометкой «ВСЕ САЙТЫ» не нуждаются в добавлении своих сайтов — "
            "они по умолчанию работают со всеми сайтами (для них доступны только исключения).\n"
            "Стратегии с пометкой «РЕКОМЕНДУЕМ» были протестированы и показали наилучшие результаты.\n"
            "Для экспериментальных стратегий есть пометка «С ОСТОРОЖНОСТЬЮ». "
            "Галочка «Все сайты» означает, что стратегия работает для всех сайтов."
        )
        info_text.setWordWrap(True)
        info_text.setStyleSheet("""
            padding:10px;
            background:#3a3a3a;
            color:#fff;
            border-radius:5px;
        """)
        desc_lay.addWidget(info_text)

        layout.addWidget(self.desc_widget)
        layout.addSpacing(3)

        # ────────── Статус + прогрессбар ──────────
        self.status_label = QLabel("🔄 Загрузка списка стратегий...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet(
            "font-weight:bold;color:#2196F3;padding:5px;")
        layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setStyleSheet("""
            QProgressBar{border:2px solid grey;border-radius:5px;text-align:center;}
            QProgressBar::chunk{background:#4CAF50;width:20px;}
        """)
        layout.addWidget(self.progress_bar)

        # ────────── Подключаем сигнал ──────────
        self.toggle_btn.toggled.connect(self._on_toggle_description)
        
        # Группа стратегий
        strategies_group = QGroupBox("Доступные стратегии")
        strategies_layout = QVBoxLayout(strategies_group)
        
        self.strategies_table = QTableWidget()
        self.strategies_table.setMinimumWidth(MINIMUM_WIDTH_STRAG)
        self.strategies_table.setColumnCount(4)
        self.strategies_table.setHorizontalHeaderLabels(["Название стратегии", "Все сайты", "Статус", "Метка"])
        
        # Настройки таблицы
        self.strategies_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.strategies_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.strategies_table.verticalHeader().setVisible(False)
        
        # Настройки колонок
        header = self.strategies_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        
        self.strategies_table.setColumnWidth(1, 150)
        self.strategies_table.setColumnWidth(2, 100)
        self.strategies_table.setColumnWidth(3, 150)
        
        # Подключаем сигналы
        self.strategies_table.currentItemChanged.connect(self.on_strategy_selected)
        self.strategies_table.itemDoubleClicked.connect(self.on_strategy_double_clicked)
        
        # Изначально отключаем таблицу
        self.strategies_table.setEnabled(False)
        
        strategies_layout.addWidget(self.strategies_table)
        
        # Кнопки управления
        buttons_row = QHBoxLayout()
        
        self.refresh_button = QPushButton("🌐 Обновить список из интернета")
        self.refresh_button.clicked.connect(self.refresh_strategies_async)
        self.refresh_button.setToolTip("Загрузить актуальный список стратегий с сервера")
        buttons_row.addWidget(self.refresh_button)
        
        self.download_all_button = QPushButton("⬇️ Скачать все стратегии")
        self.download_all_button.clicked.connect(self.download_all_strategies_async)
        buttons_row.addWidget(self.download_all_button)
        
        self.info_button = QPushButton("ℹ️ Подробная информация")
        self.info_button.clicked.connect(self.show_strategy_info)
        self.info_button.setEnabled(False)
        buttons_row.addWidget(self.info_button)
        
        buttons_row.addStretch()
        strategies_layout.addLayout(buttons_row)
        
        layout.addWidget(strategies_group)

    def _init_settings_tab(self):
        """✅ ОБНОВЛЕННЫЙ: Инициализирует вкладку настроек"""
        layout = QVBoxLayout(self.settings_tab)
        
        # ✅ ДОБАВЛЯЕМ ЗАГОЛОВОК
        title_label = QLabel("Выберите метод запуска стратегий")
        title_font = title_label.font()
        title_font.setBold(True)
        title_font.setPointSize(12)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("margin: 10px; color: #2196F3;")
        layout.addWidget(title_label)
        
        # Группа выбора метода запуска
        method_group = QGroupBox("Метод запуска стратегий")
        method_layout = QVBoxLayout(method_group)
        
        self.method_button_group = QButtonGroup()
        
        # Радиокнопка для старого метода
        self.bat_method_radio = QRadioButton("Классический метод (через .bat файлы)")
        self.bat_method_radio.setToolTip(
            "Использует .bat файлы для запуска стратегий.\n"
            "Загружает стратегии из интернета.\n"
            "Может показывать окна консоли при запуске."
        )
        self.method_button_group.addButton(self.bat_method_radio, 0)
        method_layout.addWidget(self.bat_method_radio)
        
        # Радиокнопка для нового метода
        self.direct_method_radio = QRadioButton("Прямой запуск (рекомендуется)")
        self.direct_method_radio.setToolTip(
            "Запускает встроенные стратегии напрямую из Python.\n"
            "Не требует интернета, все стратегии включены в программу.\n"
            "Полностью скрытый запуск без окон консоли."
        )
        self.method_button_group.addButton(self.direct_method_radio, 1)
        method_layout.addWidget(self.direct_method_radio)
        
        # Загружаем сохраненную настройку
        from config import get_strategy_launch_method
        current_method = get_strategy_launch_method()
        if current_method == "direct":
            self.direct_method_radio.setChecked(True)
        else:
            self.bat_method_radio.setChecked(True)
        
        # ✅ ОБРАБОТЧИК ИЗМЕНЕНИЯ МЕТОДА - АВТОМАТИЧЕСКОЕ ОБНОВЛЕНИЕ
        self.method_button_group.buttonClicked.connect(self._on_method_changed)
        
        layout.addWidget(method_group)
        
        # ✅ ОБНОВЛЕННАЯ информация о методах
        info_text = QLabel(
            "• Прямой запуск: использует встроенные стратегии, не требует интернета\n"
            "• Классический метод: загружает стратегии из интернета в виде .bat файлов\n"
            "• При смене метода список стратегий обновится автоматически"
        )
        info_text.setWordWrap(True)
        info_text.setStyleSheet("padding: 15px; background: #3a3a3a; border-radius: 5px; margin: 10px;")
        layout.addWidget(info_text)
        
        # ✅ ДОБАВЛЯЕМ УВЕДОМЛЕНИЕ ОБ АВТОМАТИЧЕСКОМ ОБНОВЛЕНИИ
        auto_update_note = QLabel(
            "💡 Изменения применяются мгновенно без подтверждения"
        )
        auto_update_note.setAlignment(Qt.AlignmentFlag.AlignCenter)
        auto_update_note.setStyleSheet(
            "padding: 10px; background: #2196F3; color: white; "
            "border-radius: 5px; font-weight: bold; margin: 10px;"
        )
        layout.addWidget(auto_update_note)
        
        layout.addStretch()

    def _on_method_changed(self, button):
        """✅ ОБНОВЛЕННЫЙ: Обработчик изменения метода запуска с автоматическим обновлением списка"""
        from config import set_strategy_launch_method
        
        old_method = self.launch_method
        
        if button == self.direct_method_radio:
            set_strategy_launch_method("direct")
            self.launch_method = "direct"
            self.is_direct_mode = True
            log("Выбран прямой метод запуска стратегий", "INFO")
            
            # ✅ АВТОМАТИЧЕСКИ ПЕРЕЗАГРУЖАЕМ СПИСОК СТРАТЕГИЙ
            if old_method != "direct":
                log("Переключение на встроенные стратегии...", "INFO")
                self.download_all_button.setVisible(False)
                self.load_builtin_strategies()
                
                # Автоматически переключаемся на вкладку стратегий для просмотра изменений
                self.tab_widget.setCurrentIndex(0)
            
        else:
            set_strategy_launch_method("bat")
            self.launch_method = "bat"
            self.is_direct_mode = False
            log("Выбран классический метод запуска через .bat", "INFO")
            
            # ✅ АВТОМАТИЧЕСКИ ПЕРЕЗАГРУЖАЕМ СПИСОК СТРАТЕГИЙ
            if old_method != "bat":
                log("Переключение на .bat стратегии...", "INFO")
                self.download_all_button.setVisible(True)
                self.load_local_strategies_only()
                
                # Автоматически переключаемся на вкладку стратегий для просмотра изменений
                self.tab_widget.setCurrentIndex(0)

    def on_strategy_double_clicked(self, item):
        """Обрабатывает двойной клик на стратегии - сразу выбирает её."""
        if not item:
            return
            
        row = item.row()
        
        # Проверяем, что выбрана не строка провайдера
        if row < 0 or row not in self.strategies_map:
            return
        
        # Получаем ID выбранной стратегии
        self.selected_strategy_id = self.strategies_map[row]['id']
        self.selected_strategy_name = self.strategies_map[row]['name']
        
        # Сразу применяем выбор
        self.accept()

    def load_strategies_async(self, force_update=False):
        """✅ Асинхронно загружает список стратегий."""
        if self.is_loading_strategies:
            return
        
        self.is_loading_strategies = True
        
        # Обновляем UI
        self.status_label.setText("🔄 Загрузка списка стратегий...")
        self.status_label.setStyleSheet("font-weight: bold; color: #2196F3; padding: 5px;")
        self.progress_bar.setVisible(True)
        self.strategies_table.setEnabled(False)
        self.refresh_button.setEnabled(False)
        self.download_all_button.setEnabled(False)
        
        from PyQt6.QtCore import QObject, QThread, pyqtSignal
        # Создаем worker для загрузки
        class StrategyListLoader(QObject):
            finished = pyqtSignal(dict, str)  # strategies_dict, error_message
            progress = pyqtSignal(str)        # status_message
            
            def __init__(self, strategy_manager, force_update=False): # ✅ ДОБАВЛЯЕМ force_update
                super().__init__()
                self.strategy_manager = strategy_manager
                self.force_update = force_update  # ✅ СОХРАНЯЕМ флаг
            
        
            def run(self):
                try:
                    if self.force_update:
                        self.progress.emit("Принудительное обновление с сервера...")
                        # ✅ Принудительно обновляем с сервера
                        strategies = self.strategy_manager.get_strategies_list(force_update=True)
                    else:
                        # Проверяем настройки автозагрузки
                        from config import get_strategy_autoload
                        if get_strategy_autoload():
                            self.progress.emit("Обновление индекса стратегий...")
                            strategies = self.strategy_manager.get_strategies_list(force_update=True)
                        else:
                            self.progress.emit("Загрузка локального кэша...")
                            strategies = self.strategy_manager.get_strategies_list(force_update=False)
                    
                    self.progress.emit("Обработка списка стратегий...")
                    
                    if strategies:
                        self.finished.emit(strategies, "")
                    else:
                        self.finished.emit({}, "Список стратегий пуст")
                        
                except Exception as e:
                    error_msg = f"Ошибка загрузки: {str(e)}"
                    log(error_msg, "❌ ERROR")
                    self.finished.emit({}, error_msg)
        
        # ✅ Создаем отдельный поток
        self.loader_thread = QThread()
        # ✅ ПЕРЕДАЕМ оба параметра
        self.loader_worker = StrategyListLoader(self.strategy_manager, force_update)
        self.loader_worker.moveToThread(self.loader_thread)
        
        # Подключаем сигналы
        self.loader_thread.started.connect(self.loader_worker.run)
        self.loader_worker.progress.connect(self.update_loading_status)
        self.loader_worker.finished.connect(self.on_strategies_loaded)
        self.loader_worker.finished.connect(self.loader_thread.quit)
        self.loader_worker.finished.connect(self.loader_worker.deleteLater)
        self.loader_thread.finished.connect(self.loader_thread.deleteLater)
        
        # Запускаем поток
        self.loader_thread.start()
        
        from log import log
        log(f"Запуск асинхронной загрузки списка стратегий (force_update={force_update})", "INFO")

    def update_loading_status(self, message):
        """Обновляет статус загрузки."""
        self.status_label.setText(f"🔄 {message}")

    def on_strategies_loaded(self, strategies, error_message):
        """Обрабатывает результат асинхронной загрузки стратегий."""
        self.is_loading_strategies = False
        
        try:
            if error_message:
                # Показываем ошибку
                self.status_label.setText(f"❌ {error_message}")
                self.status_label.setStyleSheet("font-weight: bold; color: #f44336; padding: 5px;")
                self.progress_bar.setVisible(False)
                
                # Включаем кнопку обновления для повтора
                self.refresh_button.setEnabled(True)
                return
            
            if not strategies:
                self.status_label.setText("⚠️ Список стратегий пуст")
                self.status_label.setStyleSheet("font-weight: bold; color: #ff9800; padding: 5px;")
                self.progress_bar.setVisible(False)
                self.refresh_button.setEnabled(True)
                return
            
            # Успешная загрузка
            self.status_label.setText(f"✅ Загружено {len(strategies)} стратегий")
            self.status_label.setStyleSheet("font-weight: bold; color: #4CAF50; padding: 5px;")
            self.progress_bar.setVisible(False)
            
            # Заполняем таблицу
            self.populate_strategies_table(strategies)
            
            # Включаем элементы управления
            self.strategies_table.setEnabled(True)
            self.refresh_button.setEnabled(True)
            self.download_all_button.setEnabled(True)
            
            # Выбираем текущую стратегию, если она задана
            if self.current_strategy_name:
                self.select_strategy_by_name(self.current_strategy_name)
            
            from log import log
            log(f"Асинхронная загрузка стратегий завершена: {len(strategies)} элементов", "INFO")
            
        except Exception as e:
            from log import log
            log(f"Ошибка при обработке загруженных стратегий: {e}", "❌ ERROR")
            self.status_label.setText(f"❌ Ошибка обработки: {e}")
            self.status_label.setStyleSheet("font-weight: bold; color: #f44336; padding: 5px;")
            self.progress_bar.setVisible(False)

    def populate_strategies_table(self, strategies):
        """Заполняет таблицу стратегиями."""
        self.strategies_table.setRowCount(0)
        
        # Создаем словарь для сопоставления строк таблицы с ID стратегий
        self.strategies_map = {}
        
        # Группируем стратегии по провайдерам
        providers = {}
        for strategy_id, strategy_info in strategies.items():
            provider = strategy_info.get('provider', 'universal')
            if provider not in providers:
                providers[provider] = []
            providers[provider].append((strategy_id, strategy_info))
        
        # ✅ ИЗМЕНЕНО: убираем сортировку, оставляем порядок как в JSON
        sorted_providers = sorted(providers.items())
        # Убрано: for provider, strategies_list in sorted_providers:
        #             strategies_list.sort(key=lambda x: x[1].get('name', ''))
        
        # Подсчитываем общее количество строк
        total_rows = sum(1 + len(strategies_list) for provider, strategies_list in sorted_providers)
        self.strategies_table.setRowCount(total_rows)
        
        current_row = 0
        
        for provider, strategies_list in sorted_providers:
            # Добавляем заголовок провайдера
            provider_name = self.get_provider_display_name(provider)
            provider_item = QTableWidgetItem(f"📡 {provider_name}")
            
            # Стиль для заголовка провайдера
            provider_font = provider_item.font()
            provider_font.setBold(True)
            provider_font.setPointSize(11)
            provider_item.setFont(provider_font)
            provider_item.setBackground(QBrush(QColor(70, 70, 70)))
            provider_item.setForeground(QBrush(QColor(255, 255, 255)))
            provider_item.setFlags(Qt.ItemFlag.NoItemFlags)
            
            self.strategies_table.setItem(current_row, 0, provider_item)
            self.strategies_table.setSpan(current_row, 0, 1, 4)
            current_row += 1
            
            # ✅ ИЗМЕНЕНО: добавляем нумерацию стратегий начиная с 1 для каждого провайдера
            # Оставляем порядок как в JSON
            strategy_number = 1
            for strategy_id, strategy_info in strategies_list:
                # Сохраняем соответствие строки и стратегии
                self.strategies_map[current_row] = {
                    'id': strategy_id,
                    'name': strategy_info.get('name', strategy_id)
                }
                
                # Заполняем строку таблицы, передавая номер стратегии
                self.populate_strategy_row(current_row, strategy_id, strategy_info, strategies, strategy_number)
                current_row += 1
                strategy_number += 1

    def populate_strategy_row(self, row, strategy_id, strategy_info, strategies_cache=None, strategy_number=None):
        """✅ ОБНОВЛЕННЫЙ: Заполняет одну строку таблицы данными стратегии."""
        
        strategy_name = strategy_info.get('name', strategy_id)
        if strategy_number is not None:
            display_name = f"   {strategy_number}. {strategy_name}"
        else:
            display_name = f"   {strategy_name}"
        
        name_item = QTableWidgetItem(display_name)
        self.strategies_table.setItem(row, 0, name_item)
        
        # Все сайты (галочка)
        all_sites = self.is_strategy_for_all_sites(strategy_info)
        all_sites_item = QTableWidgetItem("✓" if all_sites else "")
        all_sites_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.strategies_table.setItem(row, 1, all_sites_item)
        
        # ✅ СТАТУС - для встроенных стратегий всегда OK
        if strategy_info.get('_is_builtin', False):
            status_text = "✓ ОК"
            status_style = "color: #00C800; font-weight: bold;"
        else:
            # Оригинальная логика для BAT стратегий
            version_status = None
            if self.strategy_manager:
                version_status = self.strategy_manager.check_strategy_version_status(strategy_id, strategies_cache)
            
            status_text = "✓"
            status_style = "color: #00C800; font-weight: bold;"
            
            if version_status == 'outdated':
                status_text = "ОБНОВИТЬ"
                status_style = "color: #FF6600; font-weight: bold;"
            elif version_status == 'not_downloaded':
                status_text = "НЕ СКАЧАНА"
                status_style = "color: #CC0000; font-weight: bold;"
            elif version_status == 'unknown':
                status_text = "?"
                status_style = "color: #888888; font-weight: bold;"
        
        # Создаем виджет для статуса
        status_widget = QWidget()
        status_layout = QHBoxLayout(status_widget)
        status_label = QLabel(status_text)
        status_label.setStyleSheet(status_style)
        status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status_layout.addWidget(status_label)
        status_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status_layout.setContentsMargins(0, 0, 0, 0)
        
        self.strategies_table.setCellWidget(row, 2, status_widget)
        
        # Метка стратегии (остается без изменений)
        label = strategy_info.get('label', None)
        if label and label in LABEL_TEXTS:
            label_color_hex = LABEL_COLORS[label]
            label_style = f"color: {label_color_hex}; font-weight: bold;"
            
            label_widget = QWidget()
            label_layout = QHBoxLayout(label_widget)
            label_label = QLabel(LABEL_TEXTS[label])
            label_label.setStyleSheet(label_style)
            label_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label_layout.addWidget(label_label)
            label_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label_layout.setContentsMargins(0, 0, 0, 0)
            
            self.strategies_table.setCellWidget(row, 3, label_widget)
        else:
            empty_widget = QWidget()
            self.strategies_table.setCellWidget(row, 3, empty_widget)

    def refresh_strategies_async(self):
        """✅ ОБНОВЛЕННЫЙ МЕТОД: Загружает стратегии в зависимости от режима"""
        if self.is_loading_strategies:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(self, "Обновление в процессе", 
                                "Обновление уже выполняется, подождите...")
            return
        
        # ✅ ПРОВЕРЯЕМ РЕЖИМ ЗАПУСКА
        from config import get_strategy_launch_method
        current_method = get_strategy_launch_method()
        
        if current_method == "direct":
            # Для прямого режима просто перезагружаем встроенные
            self.is_direct_mode = True
            self.download_all_button.setVisible(False)
            self.load_builtin_strategies()
            return
        else:
            # Для BAT режима загружаем из интернета
            self.is_direct_mode = False
            self.download_all_button.setVisible(True)
        
        # Оригинальная логика для BAT режима
        self.is_loading_strategies = True
        
        # Обновляем UI
        self.status_label.setText("🌐 Загрузка стратегий из интернета...")
        self.status_label.setStyleSheet("font-weight: bold; color: #2196F3; padding: 5px;")
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.strategies_table.setEnabled(False)
        self.refresh_button.setEnabled(False)
        self.download_all_button.setEnabled(False)
        
        # Остальная логика как раньше...
        from PyQt6.QtCore import QObject, QThread, pyqtSignal
        
        class InternetStrategyLoader(QObject):
            finished = pyqtSignal(dict, str)
            progress = pyqtSignal(str)
            
            def __init__(self, strategy_manager):
                super().__init__()
                self.strategy_manager = strategy_manager
            
            def run(self):
                try:
                    self.progress.emit("Подключение к серверу...")
                    strategies = self.strategy_manager.download_strategies_index_from_internet()
                    
                    if strategies:
                        self.finished.emit(strategies, "")
                    else:
                        self.finished.emit({}, "Не удалось загрузить стратегии")
                        
                except Exception as e:
                    error_msg = f"Ошибка загрузки: {str(e)}"
                    log(error_msg, "❌ ERROR")
                    self.finished.emit({}, error_msg)
        
        # Остальная логика создания потока...
        self.loader_thread = QThread()
        self.loader_worker = InternetStrategyLoader(self.strategy_manager)
        self.loader_worker.moveToThread(self.loader_thread)
        
        self.loader_thread.started.connect(self.loader_worker.run)
        self.loader_worker.progress.connect(self.update_loading_status)
        self.loader_worker.finished.connect(self.on_strategies_loaded)
        self.loader_worker.finished.connect(self.loader_thread.quit)
        self.loader_worker.finished.connect(self.loader_worker.deleteLater)
        self.loader_thread.finished.connect(self.loader_thread.deleteLater)
        
        self.loader_thread.start()
        log("Запуск загрузки стратегий из интернета", "INFO")

    def download_all_strategies_async(self):
        """✅ ОБНОВЛЕННЫЙ МЕТОД: Скачивает .bat файлы стратегий"""
        if self.is_downloading:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(self, "Скачивание в процессе", 
                                "Скачивание уже выполняется, подождите...")
            return
        
        if not self.strategy_manager:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Ошибка", "Менеджер стратегий не инициализирован")
            return
        
        # Проверяем, есть ли стратегии для скачивания
        strategies = self.strategy_manager.get_local_strategies_only()
        if not strategies:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(self, "Нет стратегий", 
                                "Сначала обновите список стратегий из интернета")
            return
        
        self.is_downloading = True
        
        # Обновляем UI
        self.status_label.setText("⬇️ Скачивание файлов стратегий...")
        self.status_label.setStyleSheet("font-weight: bold; color: #2196F3; padding: 5px;")
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 100)
        self.download_all_button.setEnabled(False)
        self.refresh_button.setEnabled(False)
        
        from PyQt6.QtCore import QObject, QThread, pyqtSignal
        
        class StrategyFilesDownloader(QObject):
            finished = pyqtSignal(int, int, str)  # downloaded_count, total_count, error_message
            progress = pyqtSignal(int, str)       # progress_percent, current_strategy
            
            def __init__(self, strategy_manager):
                super().__init__()
                self.strategy_manager = strategy_manager
            
            def run(self):
                try:
                    strategies = self.strategy_manager.get_local_strategies_only()
                    if not strategies:
                        self.finished.emit(0, 0, "Список стратегий пуст")
                        return
                    
                    downloaded_count = 0
                    total_count = 0
                    
                    # Подсчитываем файлы для скачивания
                    for strategy_id, strategy_info in strategies.items():
                        if strategy_info.get('file_path'):
                            # Проверяем, нужно ли скачивать
                            version_status = self.strategy_manager.check_strategy_version_status(strategy_id)
                            if version_status in ['not_downloaded', 'outdated']:
                                total_count += 1
                    
                    if total_count == 0:
                        self.finished.emit(0, 0, "Все файлы актуальны")
                        return
                    
                    current_file = 0
                    
                    for strategy_id, strategy_info in strategies.items():
                        file_path = strategy_info.get('file_path')
                        if file_path:
                            version_status = self.strategy_manager.check_strategy_version_status(strategy_id)
                            if version_status in ['not_downloaded', 'outdated']:
                                current_file += 1
                                strategy_name = strategy_info.get('name', strategy_id)
                                
                                # Обновляем прогресс
                                progress_percent = int((current_file / total_count) * 100)
                                self.progress.emit(progress_percent, strategy_name)
                                
                                try:
                                    # Используем новый метод для скачивания
                                    local_path = self.strategy_manager.download_single_strategy_bat(strategy_id)
                                    if local_path:
                                        downloaded_count += 1
                                        log(f"Скачан файл стратегии: {file_path}", "INFO")
                                    else:
                                        log(f"Не удалось скачать файл: {file_path}", "⚠ WARNING")
                                except Exception as e:
                                    log(f"Ошибка при скачивании {file_path}: {e}", "⚠ WARNING")
                    
                    self.finished.emit(downloaded_count, total_count, "")
                    
                except Exception as e:
                    error_msg = f"Ошибка скачивания: {str(e)}"
                    log(error_msg, "❌ ERROR")
                    self.finished.emit(0, 0, error_msg)
        
        # Создаем отдельный поток
        self.download_thread = QThread()
        self.download_worker = StrategyFilesDownloader(self.strategy_manager)
        self.download_worker.moveToThread(self.download_thread)
        
        # Подключаем сигналы
        self.download_thread.started.connect(self.download_worker.run)
        self.download_worker.progress.connect(self.update_download_progress)
        self.download_worker.finished.connect(self.on_download_finished)
        self.download_worker.finished.connect(self.download_thread.quit)
        self.download_worker.finished.connect(self.download_worker.deleteLater)
        self.download_thread.finished.connect(self.download_thread.deleteLater)
        
        # Запускаем поток
        self.download_thread.start()
        
        log("Запуск скачивания файлов стратегий", "INFO")

    def update_download_progress(self, progress_percent, current_strategy):
        """Обновляет прогресс скачивания."""
        self.progress_bar.setValue(progress_percent)
        self.status_label.setText(f"⬇️ Скачивание: {current_strategy} ({progress_percent}%)")

    def on_download_finished(self, downloaded_count, total_count, error_message):
        """Обрабатывает завершение скачивания."""
        self.is_downloading = False
        
        # Скрываем прогресс
        self.progress_bar.setVisible(False)
        
        # Включаем кнопки
        self.download_all_button.setEnabled(True)
        self.refresh_button.setEnabled(True)
        
        if error_message:
            self.status_label.setText(f"❌ {error_message}")
            self.status_label.setStyleSheet("font-weight: bold; color: #f44336; padding: 5px;")
        elif total_count == 0:
            self.status_label.setText("⚠️ Нет файлов для скачивания")
            self.status_label.setStyleSheet("font-weight: bold; color: #ff9800; padding: 5px;")
        else:
            self.status_label.setText(f"✅ Скачано {downloaded_count}/{total_count} стратегий")
            self.status_label.setStyleSheet("font-weight: bold; color: #4CAF50; padding: 5px;")
            
            # Обновляем таблицу для отображения новых статусов
            self.load_strategies_async()
        
        from log import log
        log(f"Асинхронное скачивание завершено: {downloaded_count}/{total_count}", "INFO")

    def closeEvent(self, event):
        """Безопасное закрытие диалога."""
        if self.is_loading_strategies or self.is_downloading:
            from PyQt6.QtWidgets import QMessageBox
            reply = QMessageBox.question(
                self, 
                "Операция в процессе",
                "Выполняется загрузка или скачивание стратегий.\n"
                "Закрыть окно и прервать операцию?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # Прерываем потоки
                if self.loader_thread and self.loader_thread.isRunning():
                    self.loader_thread.terminate()
                    self.loader_thread.wait(2000)
                    
                if self.download_thread and self.download_thread.isRunning():
                    self.download_thread.terminate()
                    self.download_thread.wait(2000)
                    
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()
    
    def is_strategy_for_all_sites(self, strategy_info):
        """✅ ОБНОВЛЕННЫЙ: Проверяет, предназначена ли стратегия для всех сайтов."""
        
        # ✅ Для встроенных стратегий используем специальное поле
        if strategy_info.get('_is_builtin', False):
            return strategy_info.get('all_sites', False)
        
        # Оригинальная логика для BAT стратегий
        host_lists = strategy_info.get('host_lists', [])
        if isinstance(host_lists, list):
            for host_list in host_lists:
                if 'all' in str(host_list).lower() or 'все' in str(host_list).lower():
                    return True
        elif isinstance(host_lists, str):
            if 'all' in host_lists.lower() or 'все' in host_lists.lower():
                return True
        
        # Проверяем по описанию
        description = strategy_info.get('description', '').lower()
        if 'все сайты' in description or 'всех сайтов' in description or 'all sites' in description:
            return True
            
        # Проверяем по названию
        name = strategy_info.get('name', '').lower()
        if 'все сайты' in name or 'всех сайтов' in name or 'all sites' in name:
            return True
            
        return strategy_info.get('all_sites', False)
    
    def get_provider_display_name(self, provider):
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

    def on_strategy_selected(self, current, previous):
        """Обрабатывает выбор стратегии в таблице."""
        if current is None:
            self.select_button.setEnabled(False)
            self.info_button.setEnabled(False)
            return
        
        row = current.row()
        
        # Проверяем, что выбрана не строка провайдера
        if row < 0 or row not in self.strategies_map:
            self.select_button.setEnabled(False)
            self.info_button.setEnabled(False)
            return
        
        # Получаем ID выбранной стратегии
        strategy_id = self.strategies_map[row]['id']
        strategy_name = self.strategies_map[row]['name']
        
        # Сохраняем выбранную стратегию
        self.selected_strategy_id = strategy_id
        self.selected_strategy_name = strategy_name
        
        # Включаем кнопки
        self.select_button.setEnabled(True)
        self.info_button.setEnabled(True)

    def show_strategy_info(self):
        """Показывает окно с подробной информацией о стратегии."""
        if not self.selected_strategy_id:
            return
        
        if not self.info_dialog:
            self.info_dialog = StrategyInfoDialog(self, self.strategy_manager)
        
        self.info_dialog.display_strategy_info(self.selected_strategy_id, self.selected_strategy_name)
        self.info_dialog.show()
        self.info_dialog.raise_()
        self.info_dialog.activateWindow()

    def select_strategy_by_name(self, strategy_name):
        """Выбирает стратегию по имени."""
        for row, info in self.strategies_map.items():
            if info['name'] == strategy_name:
                self.strategies_table.selectRow(row)
                break
    
    def accept(self):
        """Обрабатывает нажатие кнопки 'Выбрать стратегию'."""
        if self.selected_strategy_id and self.selected_strategy_name:
            # Эмитируем сигнал о выборе стратегии
            self.strategySelected.emit(self.selected_strategy_id, self.selected_strategy_name)
            
            # ✅ ЗАКРЫВАЕМ ОКНО БЕЗ БЛОКИРОВКИ
            self.close()  # Вместо super().accept()
            
            log(f"Выбрана стратегия: {self.selected_strategy_name} (ID: {self.selected_strategy_id})", "INFO")
        else:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Выбор стратегии", "Пожалуйста, выберите стратегию из списка")
            log("Попытка выбора стратегии без выбора в списке", level="⚠ WARNING")

    def reject(self):
        """Обрабатывает нажатие кнопки 'Отмена'."""
        # ✅ ЗАКРЫВАЕМ ОКНО БЕЗ БЛОКИРОВКИ
        self.close()  # Вместо super().reject()
        log("Диалог выбора стратегии отменен пользователем", "INFO")