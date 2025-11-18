# ui/main_window.py
from PyQt6.QtCore import Qt, QEvent
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QComboBox, QSpacerItem, QSizePolicy, QFrame, QStackedWidget
)
from PyQt6.QtGui import QIcon, QFont, QMouseEvent
from PyQt6.QtCore import QSize

from ui.theme import (THEMES, BUTTON_STYLE, COMMON_STYLE, BUTTON_HEIGHT,
                      STYLE_SHEET, RippleButton, DualActionRippleButton)

import qtawesome as qta, sys, os
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

        # ✅ ДОБАВЛЯЕМ: Делаем label кликабельным
        self.current_strategy_label.setCursor(Qt.CursorShape.WhatsThisCursor)  # Курсор вопроса
        self.current_strategy_label.installEventFilter(self)  # Устанавливаем фильтр событий

        root.addWidget(self.current_strategy_label)

        # Списки для тематических элементов
        self.themed_buttons = []
        self.themed_labels = [self.current_strategy_label]

        # ---------- Кнопка выбора стратегии ----------------------------------
        self.select_strategy_btn = DualActionRippleButton(" Если не открывается то что тебе нужно - тыкай", self, "0, 119, 255")
        self.select_strategy_btn.setIcon(qta.icon('fa5s.cog', color='white'))
        self.select_strategy_btn.setIconSize(QSize(16, 16))
        self.select_strategy_btn.setStyleSheet(BUTTON_STYLE.format("0, 119, 255"))
        self.select_strategy_btn.set_right_click_callback(self._show_instruction)
        self.select_strategy_btn.setToolTip("Левый клик - открыть настройки\nПравый клик - открыть инструкцию (PDF)")
        self.themed_buttons.append(self.select_strategy_btn)
        root.addWidget(self.select_strategy_btn)

        # ---------- Grid-кнопки ----------------------------------------
        grid = QGridLayout()
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        grid.setSpacing(10)
        grid.setContentsMargins(0, 0, 0, 0)  # Убираем отступы у самого grid
        self.button_grid = grid

        # Создание основных кнопок
        self._create_main_buttons()

        # ✅ НОВАЯ СТРУКТУРА: Добавляем кнопки напрямую в grid (БЕЗ стеков!)
        # Строка 0, колонка 0 - кнопки запуска/остановки (накладываются друг на друга)
        grid.addWidget(self.start_btn, 0, 0)
        grid.addWidget(self.stop_btn, 0, 0)  # Та же ячейка! Qt позволяет это

        # Строка 0, колонка 1 - кнопки автозапуска (накладываются друг на друга)
        grid.addWidget(self.autostart_enable_btn, 0, 1)
        grid.addWidget(self.autostart_disable_btn, 0, 1)  # Та же ячейка!

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

    def eventFilter(self, obj, event: QEvent) -> bool:
        """Обработчик событий для кликабельных элементов"""
        if obj == self.current_strategy_label:
            if event.type() == QEvent.Type.MouseButtonPress:
                mouse_event = event
                if mouse_event.button() == Qt.MouseButton.LeftButton:
                    # Анимируем кнопку, чтобы привлечь внимание
                    self._show_wrong_click_warning()
                    return True  # Событие обработано
            elif event.type() == QEvent.Type.Enter:
                # При наведении показываем подсказку
                self.current_strategy_label.setToolTip(
                    "Это текущая стратегия.\n"
                    "Для изменения используйте кнопку ниже! 👇"
                )
        
        # ✅ ИСПРАВЛЕНИЕ: Возвращаем False для необработанных событий
        return False  # Пропускаем событие дальше

    def _show_wrong_click_warning(self):
        """Показывает предупреждение и подсвечивает правильную кнопку"""
        from PyQt6.QtWidgets import QMessageBox
        from PyQt6.QtCore import QTimer
        
        # Показываем сообщение
        msg = QMessageBox(self)
        msg.setWindowTitle("АТАТА! Не ломай меня! Не туда! 😅")
        msg.setText("Вы нажали на ТЕКСТ с названием стратегии!")
        msg.setInformativeText(
            "Это просто информационная надпись.\n\n"
            "Для смены стратегии нажмите на КНОПКУ:\n"
            "🔧 «Если не открывается то что тебе нужно - тыкай»\n\n" 
            "Она замигает для Вас! ✨"
        )
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.exec()
        
        # Анимируем кнопку выбора стратегии
        if hasattr(self, 'select_strategy_btn'):
            # Сохраняем оригинальный стиль
            original_style = self.select_strategy_btn.styleSheet()
            
            # Функция мигания
            def blink(count=0):
                if count >= 6:  # 3 мигания
                    self.select_strategy_btn.setStyleSheet(original_style)
                    return
                
                if count % 2 == 0:
                    # Подсвечиваем красным
                    self.select_strategy_btn.setStyleSheet(
                        original_style + 
                        "QPushButton { border: 3px solid red; background-color: rgba(255, 0, 0, 0.2); }"
                    )
                else:
                    # Возвращаем обычный вид
                    self.select_strategy_btn.setStyleSheet(original_style)
                
                QTimer.singleShot(300, lambda: blink(count + 1))
            
            # Запускаем анимацию
            blink()

    def _show_instruction(self):
        """Открывает PDF инструкцию по использованию Zapret"""
        try:
            from config import HELP_FOLDER
            import os
            from log import log
            
            # Путь к PDF файлу
            pdf_path = os.path.join(HELP_FOLDER, "Как пользоваться Zapret.pdf")
            
            # Проверяем существование файла
            if not os.path.exists(pdf_path):
                log(f"PDF инструкция не найдена: {pdf_path}", "❌ ERROR")
                
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(
                    self,
                    "Файл не найден",
                    f"Инструкция не найдена:\n{pdf_path}\n\n"
                    "Пожалуйста, переустановите программу или обратитесь в поддержку."
                )
                return
            
            # Открываем PDF файл
            log(f"Открываем PDF инструкцию: {pdf_path}", "INFO")
            os.startfile(pdf_path)
            
            log("PDF инструкция успешно открыта", "✅ SUCCESS")
            
        except Exception as e:
            log(f"Ошибка при открытии PDF инструкции: {e}", "❌ ERROR")
            
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(
                self,
                "Ошибка",
                f"Не удалось открыть инструкцию:\n{str(e)}\n\n"
                "Попробуйте открыть файл вручную из папки Help."
            )

    def _show_premium_info(self):
        """Открывает PDF с информацией о Premium функциях и тарифах"""
        try:
            from config import HELP_FOLDER
            import os
            import sys
            from log import log
            
            # Путь к PDF файлу
            pdf_path = os.path.join(HELP_FOLDER, "Всё о Zapret Premium и Zapret VPN (подробная инструкция).pdf")
            
            # Проверяем существование файла
            if not os.path.exists(pdf_path):
                log(f"PDF с тарифами не найден: {pdf_path}", "❌ ERROR")
                
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(
                    self,
                    "Файл не найден",
                    f"Информация о тарифах не найдена:\n{pdf_path}\n\n"
                    "Пожалуйста, переустановите программу или обратитесь в поддержку."
                )
                return
            
            # Открываем PDF файл
            log(f"Открываем PDF с тарифами: {pdf_path}", "INFO")
            
            # Используем os.startfile для Windows
            if sys.platform == 'win32':
                os.startfile(pdf_path)
            else:
                # Для других ОС используем QDesktopServices
                from PyQt6.QtCore import QUrl
                from PyQt6.QtGui import QDesktopServices
                QDesktopServices.openUrl(QUrl.fromLocalFile(pdf_path))
            
            log("PDF с тарифами Premium успешно открыт", "✅ SUCCESS")
            
        except Exception as e:
            log(f"Ошибка при открытии PDF с тарифами: {e}", "❌ ERROR")
            
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(
                self,
                "Ошибка",
                f"Не удалось открыть информацию о тарифах:\n{str(e)}\n\n"
                "Попробуйте открыть файл вручную из папки Help."
            )

    def _show_download_instruction(self):
        """Открывает PDF инструкцию по скачиванию Zapret GUI"""
        try:
            from config import HELP_FOLDER
            import os
            from log import log
            
            # Путь к PDF файлу
            pdf_path = os.path.join(HELP_FOLDER, "Как скачать Zapret.pdf")
            
            # Проверяем существование файла
            if not os.path.exists(pdf_path):
                log(f"PDF инструкция не найдена: {pdf_path}", "❌ ERROR")
                
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(
                    self,
                    "Файл не найден",
                    f"Инструкция не найдена:\n{pdf_path}\n\n"
                    "Пожалуйста, переустановите программу или обратитесь в поддержку."
                )
                return
            
            # Открываем PDF файл
            log(f"Открываем PDF инструкцию по скачиванию: {pdf_path}", "INFO")
            os.startfile(pdf_path)
            
            log("PDF инструкция по скачиванию успешно открыта", "✅ SUCCESS")
            
        except Exception as e:
            log(f"Ошибка при открытии PDF инструкции: {e}", "❌ ERROR")
            
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(
                self,
                "Ошибка",
                f"Не удалось открыть инструкцию:\n{str(e)}\n\n"
                "Попробуйте открыть файл вручную из папки Help."
            )

    def _create_main_buttons(self):
        """Создает основные кнопки управления"""
        self.start_btn = RippleButton(" Запустить Zapret", self, "54, 153, 70")
        self.start_btn.setIcon(qta.icon('fa5s.play', color='white'))
        self.start_btn.setIconSize(QSize(16, 16))
        self.start_btn.setStyleSheet(BUTTON_STYLE.format("54, 153, 70"))
        self.start_btn.setMinimumHeight(BUTTON_HEIGHT)
        self.start_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        
        self.stop_btn = RippleButton(" Остановить Zapret", self, "255, 93, 174")
        self.stop_btn.setIcon(qta.icon('fa5s.stop', color='white'))
        self.stop_btn.setIconSize(QSize(16, 16))
        self.stop_btn.setStyleSheet(BUTTON_STYLE.format("255, 93, 174"))
        self.stop_btn.setMinimumHeight(BUTTON_HEIGHT)
        self.stop_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        # По умолчанию скрыта
        self.stop_btn.hide()
        
        self.autostart_enable_btn = RippleButton(" Вкл. автозапуск", self, "54, 153, 70")
        self.autostart_enable_btn.setIcon(qta.icon('fa5s.check', color='white'))
        self.autostart_enable_btn.setIconSize(QSize(16, 16))
        self.autostart_enable_btn.setStyleSheet(BUTTON_STYLE.format("54, 153, 70"))
        self.autostart_enable_btn.setMinimumHeight(BUTTON_HEIGHT)
        self.autostart_enable_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        
        self.autostart_disable_btn = RippleButton(" Выкл. автозапуск", self, "255, 93, 174")
        self.autostart_disable_btn.setIcon(qta.icon('fa5s.times', color='white'))
        self.autostart_disable_btn.setIconSize(QSize(16, 16))
        self.autostart_disable_btn.setStyleSheet(BUTTON_STYLE.format("255, 93, 174"))
        self.autostart_disable_btn.setMinimumHeight(BUTTON_HEIGHT)
        self.autostart_disable_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        # По умолчанию скрыта
        self.autostart_disable_btn.hide()

    def _create_additional_buttons(self, grid):
        """Создает дополнительные кнопки и добавляет их в сетку"""
        self.open_folder_btn = RippleButton(" Папка Zapret", self, "0, 119, 255")
        self.open_folder_btn.setIcon(qta.icon('fa5s.folder-open', color='white'))
        self.open_folder_btn.setIconSize(QSize(16, 16))
        self.open_folder_btn.setStyleSheet(BUTTON_STYLE.format("0, 119, 255"))
        self.open_folder_btn.setMinimumHeight(BUTTON_HEIGHT)
        self.open_folder_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        
        self.test_connection_btn = RippleButton(" Тест соединения", self, "0, 119, 255")
        self.test_connection_btn.setIcon(qta.icon('fa5s.wifi', color='white'))
        self.test_connection_btn.setIconSize(QSize(16, 16))
        self.test_connection_btn.setStyleSheet(BUTTON_STYLE.format("0, 119, 255"))
        self.test_connection_btn.setMinimumHeight(BUTTON_HEIGHT)
        self.test_connection_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.subscription_btn = DualActionRippleButton(' Premium и VPN', self, "224, 132, 0")
        self.subscription_btn.setIcon(qta.icon('fa5s.user-check', color='white'))
        self.subscription_btn.setIconSize(QSize(16, 16))
        self.subscription_btn.set_right_click_callback(self._show_premium_info)
        self.subscription_btn.setToolTip(
            "Левый клик - управление подпиской\n"
            "Правый клик - открыть информацию о тарифах (PDF)"
        )
        self.subscription_btn.setStyleSheet(BUTTON_STYLE.format("224, 132, 0"))
        self.subscription_btn.setMinimumHeight(BUTTON_HEIGHT)
        self.subscription_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.dns_settings_btn = RippleButton(" Настройка DNS", self, "0, 119, 255")
        self.dns_settings_btn.setIcon(qta.icon('fa5s.network-wired', color='white'))
        self.dns_settings_btn.setIconSize(QSize(16, 16))
        self.dns_settings_btn.setStyleSheet(BUTTON_STYLE.format("0, 119, 255"))
        self.dns_settings_btn.setMinimumHeight(BUTTON_HEIGHT)
        self.dns_settings_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        
        self.proxy_button = RippleButton(" Разблокировать популярные сервисы", self, "218, 165, 32")
        self.proxy_button.setIcon(qta.icon('fa5s.unlock', color='white'))
        self.proxy_button.setIconSize(QSize(16, 16))
        self.proxy_button.setStyleSheet(BUTTON_STYLE.format("218, 165, 32"))
        self.proxy_button.setMinimumHeight(BUTTON_HEIGHT)
        self.proxy_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        
        self.help_btn = RippleButton(" Справка", self, "76, 175, 80")
        self.help_btn.setIcon(qta.icon('fa5s.question-circle', color='white'))
        self.help_btn.setIconSize(QSize(16, 16))
        self.help_btn.setStyleSheet(BUTTON_STYLE.format("76, 175, 80"))
        self.help_btn.setMinimumHeight(BUTTON_HEIGHT)
        self.help_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.help_btn.setToolTip(
            "Открыть центр помощи\n"
            "• Документация\n"
            "• Поддержка в Telegram\n"
            "• Локальные инструкции"
        )
        
        self.server_status_btn = DualActionRippleButton(" Обновления", self, "38, 38, 38")
        self.server_status_btn.setIcon(qta.icon('fa5s.sync-alt', color='white'))
        self.server_status_btn.setIconSize(QSize(16, 16))
        self.server_status_btn.setStyleSheet(BUTTON_STYLE.format("38, 38, 38"))
        self.server_status_btn.setMinimumHeight(BUTTON_HEIGHT)
        self.server_status_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.server_status_btn.set_right_click_callback(self._show_download_instruction)
        self.server_status_btn.setToolTip(
            "Левый клик - показать статус серверов обновлений\n"
            "Правый клик - открыть инструкцию по скачиванию (PDF)\n\n"
            "• Проверить доступность серверов\n"
            "• Посмотреть последние версии\n"
            "• Запустить обновление"
        )
        
        # Добавляем в themed_buttons
        self.themed_buttons.extend([
            self.open_folder_btn,
            self.test_connection_btn,
            self.dns_settings_btn,
            self.help_btn
        ])

        # Добавляем в сетку (начинаем со строки 2, т.к. строки 0-1 заняты)
        grid.addWidget(self.open_folder_btn, 2, 0)
        grid.addWidget(self.test_connection_btn, 2, 1)
        grid.addWidget(self.subscription_btn, 3, 0)
        grid.addWidget(self.dns_settings_btn, 3, 1)
        grid.addWidget(self.proxy_button, 4, 0, 1, 2)  # На 2 колонки
        grid.addWidget(self.help_btn, 5, 0)
        grid.addWidget(self.server_status_btn, 5, 1)

    def _setup_signals(self):
        """Настраивает сигналы-прокси для основного класса"""
        self.select_strategy_clicked = self.select_strategy_btn.clicked
        self.start_clicked = self.start_btn.clicked
        self.stop_clicked = self.stop_btn.clicked
        self.autostart_enable_clicked = self.autostart_enable_btn.clicked
        self.autostart_disable_clicked = self.autostart_disable_btn.clicked
        self.theme_changed = self.theme_combo.currentTextChanged