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
from config import APP_VERSION, CHANNEL

class MainWindowUI:
    """
    Чистый миксин-класс: создаёт только интерфейс, без бизнес-логики.
    """

    def build_ui(self: QWidget, width: int, height: int):
        # Проверяем, работаем ли мы с main_widget или напрямую с self
        target_widget = self
        if hasattr(self, 'main_widget'):
            target_widget = self.main_widget
        
        # Удаляем старый layout если есть
        old_layout = target_widget.layout()
        if old_layout is not None:
            while old_layout.count():
                item = old_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            QWidget().setLayout(old_layout)
        
        target_widget.setStyleSheet(STYLE_SHEET)
        target_widget.setMinimumSize(width, height)
        
        root = QVBoxLayout(target_widget)
        root.setContentsMargins(15, 15, 15, 15)
        root.setSpacing(10)

        # ---------- Заголовок ------------------------------------------
        title = f"Zapret GUI {APP_VERSION} ({CHANNEL})"
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

        # Списки для тематических элементов
        self.themed_buttons = []
        self.themed_labels = [self.current_strategy_label]

        # ---------- Кнопка выбора стратегии ----------------------------------
        self.select_strategy_btn = RippleButton(" Сменить пресет обхода блокировок", self, "0, 119, 255")
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

        # Создание основных кнопок
        self._create_main_buttons()
        
        # Создание стеков для переключения кнопок
        self._create_button_stacks()
        
        # Добавление стеков в сетку
        grid.addWidget(self.start_stop_stack, 0, 0)
        grid.addWidget(self.autostart_stack, 0, 1)

        # Создание дополнительных кнопок
        self._create_additional_buttons(grid)

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
        self._setup_signals()

    def _create_main_buttons(self):
        """Создает основные кнопки управления"""
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

        # Применяем стили и размеры
        buttons_config = [
            (self.start_btn, "54, 153, 70"),
            (self.stop_btn, "255, 93, 174"),
            (self.autostart_enable_btn, "54, 153, 70"),
            (self.autostart_disable_btn, "255, 93, 174")
        ]
        
        for button, color in buttons_config:
            button.setStyleSheet(BUTTON_STYLE.format(color))
            button.setMinimumHeight(BUTTON_HEIGHT)
            button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def _create_button_stacks(self):
        """Создает стеки для переключения кнопок"""
        # Стек для кнопок запуска/остановки (левая колонка)
        self.start_stop_stack = QStackedWidget()
        self.start_stop_stack.addWidget(self.start_btn)
        self.start_stop_stack.addWidget(self.stop_btn)
        self.start_stop_stack.setCurrentIndex(0)
        self.start_stop_stack.setMinimumHeight(BUTTON_HEIGHT)
        self.start_stop_stack.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        # Стек для кнопок автозапуска (правая колонка)
        self.autostart_stack = QStackedWidget()
        self.autostart_stack.addWidget(self.autostart_enable_btn)
        self.autostart_stack.addWidget(self.autostart_disable_btn)
        self.autostart_stack.setCurrentIndex(0)
        self.autostart_stack.setMinimumHeight(BUTTON_HEIGHT)
        self.autostart_stack.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def _create_additional_buttons(self, grid):
        """Создает дополнительные кнопки и добавляет их в сетку"""
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

        # Добавляем в themed_buttons только основные UI кнопки
        self.themed_buttons.extend([
            self.open_folder_btn,
            self.test_connection_btn,
            self.dns_settings_btn
        ])

        # Применяем стили
        self.open_folder_btn.setStyleSheet(BUTTON_STYLE.format("0, 119, 255"))
        self.test_connection_btn.setStyleSheet(BUTTON_STYLE.format("0, 119, 255"))
        self.subscription_btn.setStyleSheet(BUTTON_STYLE.format("224, 132, 0"))
        self.dns_settings_btn.setStyleSheet(BUTTON_STYLE.format("0, 119, 255"))
        self.proxy_button.setStyleSheet(BUTTON_STYLE.format("218, 165, 32"))
        self.update_check_btn.setStyleSheet(BUTTON_STYLE.format("38, 38, 38"))

        # Добавляем в сетку
        grid.addWidget(self.open_folder_btn, 2, 0)
        grid.addWidget(self.test_connection_btn, 2, 1)
        grid.addWidget(self.subscription_btn, 3, 0)
        grid.addWidget(self.dns_settings_btn, 3, 1)
        grid.addWidget(self.proxy_button, 4, 0, 1, 2)
        grid.addWidget(self.update_check_btn, 5, 0, 1, 2)

    def _setup_signals(self):
        """Настраивает сигналы-прокси для основного класса"""
        self.select_strategy_clicked = self.select_strategy_btn.clicked
        self.start_clicked = self.start_btn.clicked
        self.stop_clicked = self.stop_btn.clicked
        self.autostart_enable_clicked = self.autostart_enable_btn.clicked
        self.autostart_disable_clicked = self.autostart_disable_btn.clicked
        self.theme_changed = self.theme_combo.currentTextChanged