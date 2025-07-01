from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QComboBox, QSpacerItem, QSizePolicy, QFrame, QStackedWidget
)
from PyQt6.QtGui import QIcon, QFont
from PyQt6.QtCore import QSize

from ui.theme import (THEMES, BUTTON_STYLE, COMMON_STYLE, BUTTON_HEIGHT,
                      STYLE_SHEET, RippleButton)

import qtawesome as qta
from typing import Optional
from pathlib import Path

from config import APP_VERSION, CHANNEL # build_info moved to config/__init__.py

class MainWindowUI:
    """
    Миксин-класс: создаёт интерфейс, ничего не знает о логике.
    """

    def build_ui(self: QWidget, width: int, height: int):
        self.setStyleSheet(STYLE_SHEET)
        self.setMinimumSize(width, height)

        root = QVBoxLayout(self)
        root.setContentsMargins(15, 15, 15, 15)
        root.setSpacing(10)

        # ---------- Заголовок ------------------------------------------
        title = f"Zapret GUI {APP_VERSION} ({CHANNEL})"     # итоговая подпись
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet(f"{COMMON_STYLE} font-size: 20pt; font-weight: bold;")
        root.addWidget(self.title_label, alignment=Qt.AlignmentFlag.AlignCenter)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("QFrame { color: #e0e0e0; }")
        root.addWidget(line)

        # ---------- Предупреждение о Касперском ------------------------
        kaspersky_warning = self._create_kaspersky_warning()
        if kaspersky_warning:
            root.addWidget(kaspersky_warning)

        # ---------- Статус программы -----------------------------------
        proc_lbl = QLabel("Статус программы:")
        proc_lbl.setStyleSheet("font-weight: bold; font-size: 10pt;")
        self.process_status_value = QLabel("проверка…")
        self.process_status_value.setStyleSheet("font-size: 10pt;")

        proc_lay = QHBoxLayout()
        proc_lay.addWidget(proc_lbl)
        proc_lay.addWidget(self.process_status_value)
        proc_lay.addStretch()
        root.addLayout(proc_lay)

        # ---------- Текущая стратегия ----------------------------------
        cur_hdr = QLabel("Текущая стратегия:")
        cur_hdr.setStyleSheet(f"{COMMON_STYLE} font-weight: bold; font-size: 11pt;")
        cur_hdr.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(cur_hdr)

        self.current_strategy_label = QLabel("Автостарт DPI отключен")
        self.current_strategy_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.current_strategy_label.setWordWrap(True)
        self.current_strategy_label.setMinimumHeight(40)
        self.current_strategy_label.setStyleSheet(
            f"{COMMON_STYLE} font-weight: bold; font-size: 12pt;")
        root.addWidget(self.current_strategy_label)

        self.themed_buttons = []
        # Добавляем метку стратегии в список тематических элементов
        self.themed_labels = [self.current_strategy_label]

        # ---------- Текущая стратегия ----------------------------------
        self.select_strategy_btn = RippleButton(" Сменить стратегию обхода блокировок", self, "0, 119, 255")
        self.select_strategy_btn.setIcon(qta.icon('fa5s.cog', color='white'))
        self.select_strategy_btn.setIconSize(QSize(16, 16))
        self.select_strategy_btn.setStyleSheet(BUTTON_STYLE.format("0, 119, 255"))
        self.themed_buttons.append(self.select_strategy_btn)
        root.addWidget(self.select_strategy_btn)

        # ---------- Grid-кнопки ----------------------------------------
        grid = QGridLayout()
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        grid.setSpacing(10)
        self.button_grid = grid

        # ---------- Grid-кнопки ----------------------------------------
        self.start_btn = RippleButton(" Запустить Zapret", self, "54, 153, 70")
        self.start_btn.setIcon(qta.icon('fa5s.play', color='white'))
        self.start_btn.setIconSize(QSize(16, 16))
        
        self.stop_btn = RippleButton(" Остановить Zapret", self, "255, 93, 174")
        self.stop_btn.setIcon(qta.icon('fa5s.stop', color='white'))
        self.stop_btn.setIconSize(QSize(16, 16))
        
        self.autostart_enable_btn = RippleButton(" Вкл. автозапуск", self, "54, 153, 70")
        self.autostart_enable_btn.setIcon(qta.icon('fa5s.check', color='white'))
        self.autostart_enable_btn.setIconSize(QSize(16, 16))
        
        self.autostart_disable_btn = RippleButton(" Выкл. автозапуск", self, "255, 93, 174")
        self.autostart_disable_btn.setIcon(qta.icon('fa5s.times', color='white'))
        self.autostart_disable_btn.setIconSize(QSize(16, 16))


        for b, c in ((self.start_btn, "54, 153, 70"),
                     (self.stop_btn, "255, 93, 174"),
                     (self.autostart_enable_btn, "54, 153, 70"),
                     (self.autostart_disable_btn, "255, 93, 174")):
            b.setStyleSheet(BUTTON_STYLE.format(c))

        # ✅ НОВОЕ: Создаем стеки для переключения кнопок
        # Стек для кнопок запуска/остановки (левая колонка)
        self.start_stop_stack = QStackedWidget()
        self.start_stop_stack.addWidget(self.start_btn)      # индекс 0
        self.start_stop_stack.addWidget(self.stop_btn)       # индекс 1
        self.start_stop_stack.setCurrentIndex(0)  # По умолчанию показываем кнопку запуска

        # Стек для кнопок автозапуска (правая колонка)
        self.autostart_stack = QStackedWidget()
        self.autostart_stack.addWidget(self.autostart_enable_btn)   # индекс 0
        self.autostart_stack.addWidget(self.autostart_disable_btn)  # индекс 1
        self.autostart_stack.setCurrentIndex(0)  # По умолчанию показываем кнопку включения

        # ✅ НОВОЕ: Добавляем стеки в сетку вместо отдельных кнопок
        grid.addWidget(self.start_stop_stack, 0, 0)    # Левая колонка
        grid.addWidget(self.autostart_stack, 0, 1)     # Правая колонка

        # Остальные кнопки добавляем как обычно
        self.open_folder_btn = RippleButton(" Открыть папку Zapret", self, "0, 119, 255")
        self.open_folder_btn.setIconSize(QSize(16, 16))
        
        self.test_connection_btn = RippleButton(" Тест соединения", self, "0, 119, 255")
        self.test_connection_btn.setIcon(qta.icon('fa5s.wifi', color='white'))
        self.test_connection_btn.setIconSize(QSize(16, 16))

        self.subscription_btn = RippleButton(' Premium подписка', self, "224, 132, 0")
        self.subscription_btn.setIcon(qta.icon('fa5s.user-check', color='white'))
        self.subscription_btn.setIconSize(QSize(16, 16))

        self.dns_settings_btn = RippleButton(" Настройка DNS", self, "0, 119, 255")
        self.dns_settings_btn.setIcon(qta.icon('fa5s.network-wired', color='white'))
        self.dns_settings_btn.setIconSize(QSize(16, 16))
        
        self.proxy_button = RippleButton(" Разблокировать популярные сервисы", self, "218, 165, 32")
        self.proxy_button.setIcon(qta.icon('fa5s.unlock', color='white'))
        self.proxy_button.setIconSize(QSize(16, 16))
        
        self.update_check_btn = RippleButton(" Проверить обновления", self, "38, 38, 38")
        self.update_check_btn.setIcon(qta.icon('fa5s.sync-alt', color='white'))
        self.update_check_btn.setIconSize(QSize(16, 16))


        self.themed_buttons.append(self.open_folder_btn)
        self.themed_buttons.append(self.test_connection_btn)
        self.themed_buttons.append(self.dns_settings_btn)

        self.open_folder_btn.setStyleSheet(BUTTON_STYLE.format("0, 119, 255"))
        self.test_connection_btn.setStyleSheet(BUTTON_STYLE.format("0, 119, 255"))
        self.subscription_btn.setStyleSheet(BUTTON_STYLE.format("224, 132, 0"))
        self.dns_settings_btn.setStyleSheet(BUTTON_STYLE.format("0, 119, 255"))
        self.proxy_button.setStyleSheet(BUTTON_STYLE.format("218, 165, 32"))
        self.update_check_btn.setStyleSheet(BUTTON_STYLE.format("38, 38, 38"))

        grid.addWidget(self.open_folder_btn, 2, 0)
        grid.addWidget(self.test_connection_btn, 2, 1)
        grid.addWidget(self.subscription_btn, 3, 0)
        grid.addWidget(self.dns_settings_btn, 3, 1)
        grid.addWidget(self.proxy_button, 4, 0, 1, 2)
        grid.addWidget(self.update_check_btn, 5, 0, 1, 2)
        

        root.addLayout(grid)

        # ---------- Тема оформления -----------------------------------
        theme_lbl = QLabel("Тема оформления:")
        theme_lbl.setStyleSheet(f"{COMMON_STYLE} font-size: 10pt;")
        root.addWidget(theme_lbl, alignment=Qt.AlignmentFlag.AlignCenter)

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(THEMES.keys())
        self.theme_combo.setStyleSheet(f"{COMMON_STYLE} text-align: center; font-size: 10pt;")
        root.addWidget(self.theme_combo)

        # ---------- Статус-строка -------------------------------------
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("font-size: 9pt; color: #666;")
        root.addWidget(self.status_label)

        root.addItem(QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        # ---------- сигналы-прокси (для main.py) ----------------------
        self.select_strategy_clicked = self.select_strategy_btn.clicked
        self.start_clicked = self.start_btn.clicked
        self.stop_clicked = self.stop_btn.clicked
        self.autostart_enable_clicked = self.autostart_enable_btn.clicked
        self.autostart_disable_clicked = self.autostart_disable_btn.clicked
        self.theme_changed = self.theme_combo.currentTextChanged

    def update_proxy_button_state(self, is_active: bool = None):
        """
        Обновляет состояние кнопки разблокировки в зависимости от наличия записей в hosts.
        
        Args:
            is_active: Состояние активности proxy доменов. Если None, то будет определено автоматически.
        """
        if not hasattr(self, 'proxy_button'):
            return
            
        # Если состояние не передано, пытаемся определить его через hosts_manager
        if is_active is None and hasattr(self, 'hosts_manager'):
            is_active = self.hosts_manager.is_proxy_domains_active()
        elif is_active is None:
            # Если hosts_manager недоступен, используем состояние по умолчанию
            is_active = False
        
        # Конфигурация состояний кнопки
        button_states = {
            True: {  # Когда proxy активен (нужно отключить)
                'text': 'Отключить доступ к ChatGPT, Spotify, Notion',
                'color': "255, 93, 174",  # Красноватый
                'icon': 'fa5s.lock'       # Иконка замка (заблокировано)
            },
            False: {  # Когда proxy неактивен (нужно включить)
                'text': 'Разблокировать ChatGPT, Spotify, Notion и др.',
                'color': "218, 165, 32",  # Золотистый
                'icon': 'fa5s.unlock'     # Иконка разблокировки
            }
        }
        
        state = button_states[is_active]
        
        # Обновляем текст кнопки
        self.proxy_button.setText(f" {state['text']}")
        
        # Обновляем стиль кнопки
        self.proxy_button.setStyleSheet(BUTTON_STYLE.format(state['color']))
        
        # Обновляем иконку
        self.proxy_button.setIcon(qta.icon(state['icon'], color='white'))
        
        # Логируем изменение состояния
        try:
            from log import log
            status = "активна" if is_active else "неактивна"
            log(f"Состояние кнопки proxy обновлено: разблокировка {status}", "DEBUG")
        except ImportError:
            pass
        
    def get_proxy_button_config(self):
        """
        Возвращает конфигурацию для различных состояний кнопки proxy.
        Полезно для других частей приложения.
        
        Returns:
            dict: Конфигурация состояний кнопки
        """
        return {
            'enabled_state': {
                'full_text': 'Отключить доступ к ChatGPT, Spotify, Notion',
                'short_text': 'Отключить разблокировку',
                'color': "255, 93, 174",
                'icon': 'fa5s.lock',
                'tooltip': 'Нажмите чтобы отключить разблокировку сервисов через hosts-файл'
            },
            'disabled_state': {
                'full_text': 'Разблокировать ChatGPT, Spotify, Notion и др.',
                'short_text': 'Разблокировать сервисы',
                'color': "218, 165, 32",
                'icon': 'fa5s.unlock',
                'tooltip': 'Нажмите чтобы разблокировать популярные сервисы через hosts-файл'
            }
        }

    def set_proxy_button_loading(self, is_loading: bool, text: str = ""):
        """
        Устанавливает состояние загрузки для кнопки proxy.
        
        Args:
            is_loading: True если идет процесс загрузки/обработки
            text: Текст для отображения во время загрузки
        """
        if not hasattr(self, 'proxy_button'):
            return
            
        if is_loading:
            loading_text = text if text else "Обработка..."
            self.proxy_button.setText(f" {loading_text}")
            self.proxy_button.setEnabled(False)
            self.proxy_button.setIcon(qta.icon('fa5s.spinner', color='white'))
            # Можно добавить анимацию вращения иконки
        else:
            self.proxy_button.setEnabled(True)
            # Восстанавливаем нормальное состояние
            self.update_proxy_button_state()

    def update_theme_combo(self, available_themes):
        """
        Обновляет список доступных тем в комбо-боксе с учетом подписки.
        
        Args:
            available_themes: Список доступных тем для текущего пользователя
        """
        current_theme = self.theme_combo.currentText()
        
        # Временно отключаем сигналы чтобы избежать лишних срабатываний
        self.theme_combo.blockSignals(True)
        
        # Очищаем и заполняем заново
        self.theme_combo.clear()
        self.theme_combo.addItems(available_themes)
        
        # Применяем стили для заблокированных элементов
        #self._apply_theme_combo_styles()
        
        # Восстанавливаем выбор, если тема доступна
        clean_current = current_theme.replace(" (заблокировано)", "")
        for theme in available_themes:
            clean_theme = theme.replace(" (заблокировано)", "")
            if clean_theme == clean_current:
                self.theme_combo.setCurrentText(theme)
                break
        else:
            # Если текущая тема недоступна, выбираем первую доступную
            if available_themes:
                # Ищем первую незаблокированную тему
                for theme in available_themes:
                    if "(заблокировано)" not in theme:
                        self.theme_combo.setCurrentText(theme)
                        break
                else:
                    # Если все темы заблокированы (не должно происходить), выбираем первую
                    self.theme_combo.setCurrentText(available_themes[0])
        
        # Включаем сигналы обратно
        self.theme_combo.blockSignals(False)
        
        # Если произошло изменение темы, сигнализируем об этом
        new_theme = self.theme_combo.currentText()
        if new_theme != current_theme:
            self.theme_changed.emit(new_theme)

    def _apply_theme_combo_styles(self):
        """Применяет стили к комбо-боксу тем для выделения заблокированных элементов"""
        # Создаем CSS стили для комбо-бокса
        style = f"""
        QComboBox {{
            {COMMON_STYLE}
            text-align: center;
            font-size: 10pt;
            padding: 5px;
            border: 1px solid #ccc;
            border-radius: 4px;
        }}
        
        QComboBox::drop-down {{
            border: none;
            width: 20px;
        }}
        
        QComboBox::down-arrow {{
            width: 12px;
            height: 12px;
        }}
        
        QComboBox QAbstractItemView {{
            selection-background-color: #007ACC;
            selection-color: white;
            border: 1px solid #ccc;
        }}
        
        QComboBox QAbstractItemView::item {{
            padding: 8px;
            border-bottom: 1px solid #eee;
        }}
        
        QComboBox QAbstractItemView::item:contains("заблокировано") {{
            color: #888888;
            background-color: #f5f5f5;
            font-style: italic;
        }}
        
        QComboBox QAbstractItemView::item:contains("заблокировано"):hover {{
            background-color: #e8e8e8;
            color: #666666;
        }}
        """
        
        self.theme_combo.setStyleSheet(style)

    def update_title_with_subscription_status(self, is_premium: bool = False, current_theme: str = None, days_remaining: Optional[int] = None):
        """
        Обновляет заголовок окна с информацией о днях подписки и title_label с цветным статусом.
        
        Args:
            is_premium: True если подписка активна
            current_theme: Текущая тема (если не указана, берется из theme_manager)
            days_remaining: Количество дней до окончания подписки (None если бессрочная)
        """
        # Обновляем системный заголовок окна с информацией о днях
        base_title = f'Zapret v{APP_VERSION}'
        
        if is_premium:
            # Формируем текст премиум статуса для заголовка окна
            if days_remaining is not None:
                if days_remaining > 0:
                    premium_text = f" [PREMIUM - {days_remaining} дн.]"
                elif days_remaining == 0:
                    premium_text = " [PREMIUM - истекает сегодня]"
                else:
                    premium_text = " [PREMIUM - истекла]"
            else:
                premium_text = " [PREMIUM]"
                
            full_title = f"{base_title}{premium_text}"
            self.setWindowTitle(full_title)
        else:
            # Для бесплатной версии просто показываем базовый заголовок
            self.setWindowTitle(base_title)
        
        # Обновляем title_label с цветным статусом (без дней)
        base_label_title = "Zapret GUI"
        
        if is_premium:
            # Получаем цвет кнопок текущей темы для премиум индикатора
            premium_color = self._get_premium_indicator_color(current_theme)
            premium_indicator = f'<span style="color: {premium_color}; font-weight: bold;"> [PREMIUM]</span>'
            full_label_title = f"{base_label_title}{premium_indicator}"
            self.title_label.setText(full_label_title)
            self.title_label.setStyleSheet(f"{COMMON_STYLE} font-size: 20pt; font-weight: bold;")
        else:
            # Для бесплатной версии показываем [FREE] с цветом адаптированным под тему
            free_color = self._get_free_indicator_color(current_theme)
            free_indicator = f'<span style="color: {free_color}; font-weight: bold;"> [FREE]</span>'
            full_free_label_title = f"{base_label_title}{free_indicator}"
            self.title_label.setText(full_free_label_title)
            self.title_label.setStyleSheet(f"{COMMON_STYLE} font-size: 20pt; font-weight: bold;")

    def _get_free_indicator_color(self, current_theme: str = None):
        """
        Возвращает цвет для индикатора [FREE] на основе текущей темы.
        Белый для темных тем, черный для светлых тем.
        
        Args:
            current_theme: Текущая тема (если не указана, берется из реестра)
        
        Returns:
            str: Hex цвет для индикатора [FREE]
        """
        try:
            # Импортируем здесь чтобы избежать циклических импортов
            from ui.theme import THEMES, get_selected_theme
            
            # Получаем текущую тему
            theme_name = current_theme if current_theme else get_selected_theme()
            
            if not theme_name or theme_name not in THEMES:
                # Fallback к черному если тема неизвестна
                return "#000000"
            
            # Определяем цвет на основе названия темы
            if theme_name.startswith("Темная") or theme_name == "РКН Тян":
                # Для темных тем используем белый цвет
                return "#BBBBBB"
            elif theme_name.startswith("Светлая"):
                # Для светлых тем используем черный цвет
                return "#000000"
            else:
                # Fallback для неизвестных тем
                return "#000000"
                
        except Exception as e:
            # В случае любой ошибки возвращаем черный
            return "#000000"
    
    def _get_premium_indicator_color(self, current_theme: str = None):
        """
        Возвращает цвет для индикатора премиум статуса на основе текущей темы.
        
        Args:
            current_theme: Текущая тема (если не указана, берется из реестра)
        
        Returns:
            str: Hex цвет для индикатора
        """
        try:
            # Импортируем здесь чтобы избежать циклических импортов
            from ui.theme import THEMES, get_selected_theme
            
            # Получаем текущую тему
            theme_name = current_theme if current_theme else get_selected_theme()
            
            if not theme_name or theme_name not in THEMES:
                # Fallback к зеленому если тема неизвестна
                return "#4CAF50"
            
            theme_info = THEMES[theme_name]
            button_color = theme_info.get("button_color", "0, 119, 255")
            
            # Преобразуем RGB в hex
            if ',' in button_color:
                try:
                    rgb_values = [int(x.strip()) for x in button_color.split(',')]
                    hex_color = f"#{rgb_values[0]:02x}{rgb_values[1]:02x}{rgb_values[2]:02x}"
                    return hex_color
                except (ValueError, IndexError):
                    return "#4CAF50"  # Fallback
            
            return "#4CAF50"  # Fallback если формат неожиданный
            
        except Exception as e:
            # В случае любой ошибки возвращаем зеленый
            return "#4CAF50"
        
    def _get_premium_indicator_color(self, current_theme: str = None):
        """
        Возвращает цвет для индикатора премиум статуса на основе текущей темы.
        
        Args:
            current_theme: Текущая тема (если не указана, берется из реестра)
        
        Returns:
            str: Hex цвет для индикатора
        """
        try:
            # Импортируем здесь чтобы избежать циклических импортов
            from ui.theme import THEMES, get_selected_theme
            
            # Получаем текущую тему
            theme_name = current_theme if current_theme else get_selected_theme()
            
            if not theme_name or theme_name not in THEMES:
                # Fallback к зеленому если тема неизвестна
                return "#4CAF50"
            
            theme_info = THEMES[theme_name]
            button_color = theme_info.get("button_color", "0, 119, 255")
            
            # Преобразуем RGB в hex
            if ',' in button_color:
                try:
                    rgb_values = [int(x.strip()) for x in button_color.split(',')]
                    hex_color = f"#{rgb_values[0]:02x}{rgb_values[1]:02x}{rgb_values[2]:02x}"
                    return hex_color
                except (ValueError, IndexError):
                    return "#4CAF50"  # Fallback
            
            return "#4CAF50"  # Fallback если формат неожиданный
            
        except Exception as e:
            # В случае любой ошибки возвращаем зеленый
            return "#4CAF50"

    def _check_kaspersky_antivirus(self):
        """
        Проверяет наличие антивируса Касперского в системе.
        
        Returns:
            bool: True если Касперский обнаружен, False если нет
        """
        #return True
        try:
            import subprocess
            import os
            
            # Проверяем наличие процессов Касперского
            kaspersky_processes = [
                'avp.exe', 'kavfs.exe', 'klnagent.exe', 'ksde.exe',
                'kavfswp.exe', 'kavfswh.exe', 'kavfsslp.exe'
            ]
            
            # Получаем список запущенных процессов
            try:
                result = subprocess.run(['tasklist'], capture_output=True, text=True, shell=True)
                if result.returncode == 0:
                    running_processes = result.stdout.lower()
                    
                    for process in kaspersky_processes:
                        if process.lower() in running_processes:
                            return True
            except Exception:
                pass
            
            # Проверяем папки установки Касперского
            kaspersky_paths = [
                r'C:\Program Files\Kaspersky Lab',
                r'C:\Program Files (x86)\Kaspersky Lab',
                r'C:\Program Files\Kaspersky Security',
                r'C:\Program Files (x86)\Kaspersky Security'
            ]
            
            for path in kaspersky_paths:
                if os.path.exists(path) and os.path.isdir(path):
                    try:
                        # Проверяем, что папка не пустая
                        dir_contents = os.listdir(path)
                        if dir_contents:
                            # Дополнительно проверяем наличие исполняемых файлов или подпапок
                            for item in dir_contents:
                                item_path = os.path.join(path, item)
                                if os.path.isdir(item_path) or item.lower().endswith(('.exe', '.dll')):
                                    return True
                    except (PermissionError, OSError):
                        # Если нет доступа к папке, но она существует - считаем что Касперский есть
                        return True
            
            # Если ни один процесс не найден и папки пустые/не найдены, считаем что Касперского нет
            return False
            
        except Exception as e:
            # В случае ошибки считаем, что Касперского нет
            return False

    def _create_kaspersky_warning(self):
        """
        Создает компактный виджет с предупреждением о Касперском.
        
        Returns:
            QWidget: Виджет с предупреждением или None если Касперский не обнаружен
        """
        if not self._check_kaspersky_antivirus():
            return None
        
        from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton
        from PyQt6.QtCore import Qt
        
        # Создаем основной фрейм
        warning_frame = QFrame()
        warning_frame.setFrameStyle(QFrame.Shape.Box)
        warning_frame.setStyleSheet("""
            QFrame {
                background-color: #FFF3CD;
                border: 1px solid #FFEAA7;
                border-radius: 4px;
                padding: 2px;
                margin: 0px;
            }
        """)
        
        layout = QHBoxLayout(warning_frame)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)
        
        # Иконка предупреждения
        warning_icon = QLabel()
        warning_icon.setText("⚠")
        warning_icon.setStyleSheet("font-size: 14px; color: #F39C12;")
        layout.addWidget(warning_icon)
        
        # Текст предупреждения (компактный)
        warning_text = QLabel()
        warning_text.setText("Kaspersky может блокировать Zapret. Добавьте в исключения.")
        warning_text.setStyleSheet("""
            QLabel {
                color: #856404;
                font-size: 9pt;
                background: transparent;
                border: none;
            }
        """)
        layout.addWidget(warning_text, 1)
        
        # Кнопка закрытия
        dismiss_btn = QPushButton("✕")
        dismiss_btn.setFixedSize(16, 16)
        dismiss_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                color: #856404;
                font-size: 10pt;
                padding: 0px;
            }
            QPushButton:hover {
                color: #F39C12;
            }
        """)
        dismiss_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        
        def close_warning():
            """Закрывает предупреждение и удаляет его из layout"""
            if warning_frame.parent():
                parent_layout = warning_frame.parent().layout()
                if parent_layout:
                    parent_layout.removeWidget(warning_frame)
                
                # Находим главное окно через self (MainWindowUI)
                main_window = self
                while hasattr(main_window, 'parent') and main_window.parent():
                    main_window = main_window.parent()
                
                # Принудительно обновляем размеры
                if hasattr(main_window, 'adjustSize'):
                    main_window.adjustSize()
                if hasattr(main_window, 'updateGeometry'):
                    main_window.updateGeometry()
            
            warning_frame.deleteLater()
        
        dismiss_btn.clicked.connect(close_warning)
        layout.addWidget(dismiss_btn)
        
        return warning_frame

    def get_hosts_path() -> Path:
        """
        Возвращает абсолютный путь к файлу hosts на той букве диска,
        где реально установлена Windows.
        """
        import os
        import ctypes
        from ctypes import wintypes

        # 1. Пробуем переменную среды — самый простой и быстрый способ
        sys_root = os.getenv("SystemRoot")
        if sys_root and Path(sys_root).exists():
            return Path(sys_root, "System32", "drivers", "etc", "hosts")

        # 2. Если почему-то переменной нет — берём через WinAPI
        GetSystemWindowsDirectoryW = ctypes.windll.kernel32.GetSystemWindowsDirectoryW
        GetSystemWindowsDirectoryW.argtypes = [wintypes.LPWSTR, wintypes.UINT]
        GetSystemWindowsDirectoryW.restype  = wintypes.UINT

        buf = ctypes.create_unicode_buffer(260)
        if GetSystemWindowsDirectoryW(buf, len(buf)):
            return Path(buf.value, "System32", "drivers", "etc", "hosts")

        # 3. Фолбэк на C:\Windows (маловероятно, но пусть будет)
        return Path(r"C:\Windows\System32\drivers\etc\hosts")