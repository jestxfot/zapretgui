# ui/main_window.py
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
from log import log
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
        self.open_folder_btn = RippleButton(" Папка Zapret", self, "0, 119, 255")
        self.open_folder_btn.setIcon(qta.icon('fa5s.folder-open', color='white'))
        self.open_folder_btn.setIconSize(QSize(16, 16))
        
        self.test_connection_btn = RippleButton(" Тест соединения", self, "0, 119, 255")
        self.test_connection_btn.setIcon(qta.icon('fa5s.wifi', color='white'))
        self.test_connection_btn.setIconSize(QSize(16, 16))

        self.subscription_btn = RippleButton(' Premium и VPN', self, "224, 132, 0")
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
        🆕 Теперь учитывает полностью черную тему.
        """
        if not hasattr(self, 'proxy_button'):
            return
            
        # Если состояние не передано, пытаемся определить его через hosts_manager
        if is_active is None and hasattr(self, 'hosts_manager'):
            is_active = self.hosts_manager.is_proxy_domains_active()
        elif is_active is None:
            is_active = False
        
        # 🆕 Проверяем, используется ли полностью черная тема
        is_pure_black = False
        if (hasattr(self, 'theme_manager') and 
            hasattr(self.theme_manager, '_is_pure_black_theme')):
            current_theme = getattr(self.theme_manager, 'current_theme', '')
            is_pure_black = self.theme_manager._is_pure_black_theme(current_theme)
        
        if is_pure_black:
            # Для полностью черной темы используем темно-серые цвета
            button_states = {
                True: {  # Когда proxy активен (нужно отключить)
                    'text': 'Отключить доступ к ChatGPT, Spotify, Twitch',
                    'color': "64, 64, 64",  # Темно-серый
                    'icon': 'fa5s.lock'
                },
                False: {  # Когда proxy неактивен (нужно включить)
                    'text': 'Разблокировать ChatGPT, Spotify, Twitch и др.',
                    'color': "96, 96, 96",  # Чуть светлее серый
                    'icon': 'fa5s.unlock'
                }
            }
            
            # Специальный стиль для полностью черной темы
            from ui.theme import BUTTON_STYLE
            pure_black_style = """
            QPushButton {{
                border: 1px solid #444444;
                background-color: rgb({0});
                color: #ffffff;
                border-radius: 6px;
                padding: 10px;
                font-weight: bold;
                font-size: 10pt;
                min-height: 35px;
            }}
            QPushButton:hover {{
                background-color: rgb(128, 128, 128);
                border: 1px solid #666666;
            }}
            QPushButton:pressed {{
                background-color: rgb(32, 32, 32);
                border: 1px solid #888888;
            }}
            """
            
            state = button_states[is_active]
            self.proxy_button.setText(f" {state['text']}")
            self.proxy_button.setStyleSheet(pure_black_style.format(state['color']))
            
        else:
            # Обычная логика для всех остальных тем
            button_states = {
                True: {
                    'text': 'Отключить доступ к ChatGPT, Spotify, Twitch',
                    'color': "255, 93, 174",
                    'icon': 'fa5s.lock'
                },
                False: {
                    'text': 'Разблокировать ChatGPT, Spotify, Twitch и др.',
                    'color': "218, 165, 32",
                    'icon': 'fa5s.unlock'
                }
            }
            
            state = button_states[is_active]
            self.proxy_button.setText(f" {state['text']}")
            
            from ui.theme import BUTTON_STYLE
            self.proxy_button.setStyleSheet(BUTTON_STYLE.format(state['color']))
        
        # Общая логика для иконки
        import qtawesome as qta
        from PyQt6.QtCore import QSize
        state = button_states[is_active]
        self.proxy_button.setIcon(qta.icon(state['icon'], color='white'))
        self.proxy_button.setIconSize(QSize(16, 16))
        
        # Логируем изменение состояния
        try:
            status = "активна" if is_active else "неактивна"
            theme_info = " (полностью черная тема)" if is_pure_black else ""
            log(f"Состояние кнопки proxy обновлено: разблокировка {status}{theme_info}", "DEBUG")
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
                'full_text': 'Отключить доступ к ChatGPT, Spotify, Twitch',
                'short_text': 'Отключить разблокировку',
                'color': "255, 93, 174",
                'icon': 'fa5s.lock',
                'tooltip': 'Нажмите чтобы отключить разблокировку сервисов через hosts-файл'
            },
            'disabled_state': {
                'full_text': 'Разблокировать ChatGPT, Spotify, Twitch и др.',
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
        Теперь делегирует в ThemeHandler если он доступен.
        """
        # Если theme_handler доступен, используем его
        if hasattr(self, 'theme_handler') and self.theme_handler is not None:
            self.theme_handler.update_available_themes()
            return
        
        # Fallback - старая логика
        current_theme = self.theme_combo.currentText()
        
        # Временно отключаем сигналы чтобы избежать лишних срабатываний
        self.theme_combo.blockSignals(True)
        
        # Очищаем и заполняем заново
        self.theme_combo.clear()
        self.theme_combo.addItems(available_themes)
        
        # Применяем стили для заблокированных элементов
        self._apply_theme_combo_styles()
        
        # Восстанавливаем выбор, если тема доступна
        clean_current = current_theme
        if hasattr(self, 'theme_manager'):
            clean_current = self.theme_manager.get_clean_theme_name(current_theme)
        
        for theme in available_themes:
            clean_theme = theme
            if hasattr(self, 'theme_manager'):
                clean_theme = self.theme_manager.get_clean_theme_name(theme)
            if clean_theme == clean_current:
                self.theme_combo.setCurrentText(theme)
                break
        else:
            # Если текущая тема недоступна, выбираем первую доступную
            if available_themes:
                # Ищем первую незаблокированную тему
                for theme in available_themes:
                    if "(заблокировано)" not in theme and "(Premium)" not in theme:
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
        # Проверяем, что theme_handler инициализирован
        if hasattr(self, 'theme_handler') and self.theme_handler is not None:
            self.theme_handler.update_theme_combo_styles()
        else:
            # Fallback для случаев когда theme_handler еще не инициализирован
            log("theme_handler не инициализирован, используем fallback стили", "DEBUG")
            try:
                from ui.theme import COMMON_STYLE
                style = f"""
                QComboBox {{
                    {COMMON_STYLE}
                    text-align: center;
                    font-size: 10pt;
                    padding: 5px;
                    border: 1px solid #ccc;
                    border-radius: 4px;
                }}
                """
                if hasattr(self, 'theme_combo'):
                    self.theme_combo.setStyleSheet(style)
            except Exception as e:
                log(f"Ошибка применения fallback стилей: {e}", "❌ ERROR")

    def update_title_with_subscription_status(self, is_premium: bool = False, current_theme: str = None, 
                                            days_remaining: Optional[int] = None, is_auto_renewal: bool = False):
        """
        🆕 ОБНОВЛЕННАЯ ВЕРСИЯ: Обновляет заголовок окна с информацией о подписке и автопродлении.
        
        Args:
            is_premium: True если пользователь имеет премиум подписку
            current_theme: Текущая тема интерфейса
            days_remaining: Количество дней до окончания подписки (None для автопродления)
            is_auto_renewal: True если подписка автопродлевается
        """
        # Обновляем системный заголовок окна с информацией о подписке
        base_title = f'Zapret v{APP_VERSION}'
        
        if is_premium:
            # Формируем текст премиум статуса для заголовка окна
            if is_auto_renewal:
                premium_text = " [PREMIUM - автопродление]"
                log("Отображаем автопродление в заголовке окна", "DEBUG")
            elif days_remaining is not None:
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
            log(f"Заголовок окна обновлен: {full_title}", "DEBUG")
        else:
            # Для бесплатной версии просто показываем базовый заголовок
            self.setWindowTitle(base_title)
        
        # Обновляем title_label с цветным статусом (без дней)
        base_label_title = "Zapret GUI"
        
        # Правильно определяем текущую тему
        actual_current_theme = current_theme
        if not actual_current_theme and hasattr(self, 'theme_manager'):
            actual_current_theme = getattr(self.theme_manager, 'current_theme', None)
        
        if is_premium:
            # Получаем цвет индикатора с учетом темы и автопродления
            premium_color = self._get_premium_indicator_color(actual_current_theme, is_auto_renewal)
            
            # Формируем индикатор с учетом автопродления
            if is_auto_renewal:
                premium_indicator = f'<span style="color: {premium_color}; font-weight: bold;"> [PREMIUM ∞]</span>'
                log("Отображаем символ автопродления в title_label", "DEBUG")
            else:
                premium_indicator = f'<span style="color: {premium_color}; font-weight: bold;"> [PREMIUM]</span>'
            
            full_label_title = f"{base_label_title}{premium_indicator}"
            self.title_label.setText(full_label_title)
            self.title_label.setStyleSheet(f"{COMMON_STYLE} font-size: 20pt; font-weight: bold;")
        else:
            # Для бесплатной версии показываем [FREE] с цветом адаптированным под тему
            free_color = self._get_free_indicator_color(actual_current_theme)
            free_indicator = f'<span style="color: {free_color}; font-weight: bold;"> [FREE]</span>'
            full_free_label_title = f"{base_label_title}{free_indicator}"
            self.title_label.setText(full_free_label_title)
            self.title_label.setStyleSheet(f"{COMMON_STYLE} font-size: 20pt; font-weight: bold;")

    def _get_free_indicator_color(self, current_theme: str = None):
        """
        🆕 ИСПРАВЛЕННАЯ версия: Возвращает цвет для индикатора [FREE] на основе текущей темы.
        """
        try:
            # Получаем текущую тему
            theme_name = current_theme
            if not theme_name and hasattr(self, 'theme_manager'):
                theme_name = getattr(self.theme_manager, 'current_theme', None)
            
            if not theme_name:
                return "#000000"
            
            # 🆕 Специальная обработка для полностью черной темы
            if theme_name == "Полностью черная":
                return "#ffffff"  # Белый цвет для полностью черной темы
            
            # Определяем цвет на основе названия темы
            if (theme_name.startswith("Темная") or 
                theme_name == "РКН Тян" or 
                theme_name.startswith("AMOLED")):
                return "#BBBBBB"
            elif theme_name.startswith("Светлая"):
                return "#000000"
            else:
                return "#000000"
                
        except Exception as e:
            log(f"Ошибка определения цвета FREE индикатора: {e}", "❌ ERROR")
            return "#000000"

    def _get_premium_indicator_color(self, current_theme: str = None, is_auto_renewal: bool = False):
        """
        🆕 ОБНОВЛЕННАЯ версия: Возвращает цвет для индикатора премиум статуса с учетом автопродления.
        
        Args:
            current_theme: Текущая тема интерфейса
            is_auto_renewal: True если подписка автопродлевается
        """
        try:
            # Получаем текущую тему
            theme_name = current_theme
            if not theme_name and hasattr(self, 'theme_manager'):
                theme_name = getattr(self.theme_manager, 'current_theme', None)
            
            if not theme_name:
                # Для автопродления используем золотой цвет, для обычного - зеленый
                return "#FFD700" if is_auto_renewal else "#4CAF50"
            
            # 🆕 Специальная обработка для полностью черной темы
            if theme_name == "Полностью черная":
                if is_auto_renewal:
                    log("Применяем золотой цвет для автопродления в полностью черной теме", "DEBUG")
                    return "#FFD700"  # Золотой для автопродления
                else:
                    log("Применяем белый цвет для обычного PREMIUM в полностью черной теме", "DEBUG")
                    return "#ffffff"  # Белый цвет для обычного премиума
            
            # Для остальных тем определяем цвет на основе button_color
            try:
                from ui.theme import THEMES
                if theme_name in THEMES:
                    theme_info = THEMES[theme_name]
                    button_color = theme_info.get("button_color", "0, 119, 255")
                    
                    # Для автопродления всегда используем золотой независимо от темы
                    if is_auto_renewal:
                        log(f"Цвет автопродления для темы {theme_name}: #FFD700", "DEBUG")
                        return "#FFD700"
                    
                    # Преобразуем RGB в hex для обычного премиума
                    if ',' in button_color:
                        try:
                            rgb_values = [int(x.strip()) for x in button_color.split(',')]
                            hex_color = f"#{rgb_values[0]:02x}{rgb_values[1]:02x}{rgb_values[2]:02x}"
                            log(f"Цвет PREMIUM индикатора для темы {theme_name}: {hex_color}", "DEBUG")
                            return hex_color
                        except (ValueError, IndexError):
                            return "#FFD700" if is_auto_renewal else "#4CAF50"
            except ImportError:
                pass
            
            # Fallback цвета
            return "#FFD700" if is_auto_renewal else "#4CAF50"
            
        except Exception as e:
            log(f"Ошибка определения цвета PREMIUM индикатора: {e}", "❌ ERROR")
            return "#FFD700" if is_auto_renewal else "#4CAF50"

    def update_subscription_button_text(self, is_premium: bool = False, is_auto_renewal: bool = False, 
                                      days_remaining: Optional[int] = None):
        """
        🆕 НОВАЯ ФУНКЦИЯ: Обновляет текст кнопки подписки с учетом статуса автопродления.
        
        Args:
            is_premium: True если пользователь имеет премиум подписку
            is_auto_renewal: True если подписка автопродлевается
            days_remaining: Количество дней до окончания подписки
        """
        if not hasattr(self, 'subscription_btn'):
            return
        
        if is_premium:
            if is_auto_renewal:
                button_text = " Premium ∞ (автопродление)"
                log("Кнопка подписки: отображаем автопродление", "DEBUG")
            elif days_remaining is not None:
                if days_remaining > 0:
                    button_text = f" Premium ({days_remaining} дн.)"
                elif days_remaining == 0:
                    button_text = " Premium (истекает сегодня)"
                else:
                    button_text = " Premium истёк"
            else:
                button_text = " Premium активен"
        else:
            button_text = " Premium и VPN"
        
        self.subscription_btn.setText(button_text)
        log(f"Текст кнопки подписки обновлен: {button_text.strip()}", "DEBUG")

    def get_subscription_status_text(self, is_premium: bool = False, is_auto_renewal: bool = False, 
                                   days_remaining: Optional[int] = None) -> str:
        """
        🆕 НОВАЯ ФУНКЦИЯ: Возвращает форматированный текст статуса подписки.
        
        Args:
            is_premium: True если пользователь имеет премиум подписку
            is_auto_renewal: True если подписка автопродлевается
            days_remaining: Количество дней до окончания подписки
            
        Returns:
            str: Форматированный текст статуса
        """
        if not is_premium:
            return "Подписка: Бесплатная версия"
        
        if is_auto_renewal:
            return "Подписка: Premium (автопродление)"
        elif days_remaining is not None:
            if days_remaining > 0:
                return f"Подписка: Premium (осталось {days_remaining} дн.)"
            elif days_remaining == 0:
                return "Подписка: Premium (истекает сегодня)"
            else:
                return "Подписка: Premium (истекла)"
        else:
            return "Подписка: Premium"

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