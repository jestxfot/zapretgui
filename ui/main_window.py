# ui/main_window.py
"""
Главное окно приложения в стиле Windows 11 Settings
"""
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QComboBox, QFrame, QStackedWidget, QSizePolicy
)
from PyQt6.QtGui import QIcon, QFont

from ui.theme import THEMES, BUTTON_STYLE, COMMON_STYLE, BUTTON_HEIGHT, STYLE_SHEET
from ui.sidebar import SideNavBar, SettingsCard, ActionButton
from ui.pages import (
    HomePage, ControlPage, StrategiesPage, HostlistPage, IpsetPage, EditorPage, DpiSettingsPage,
    AutostartPage, NetworkPage, AppearancePage, AboutPage, LogsPage, PremiumPage
)

import qtawesome as qta
import sys, os
from config import APP_VERSION, CHANNEL


# Новый стиль для Windows 11 Settings
WIN11_STYLE = """
QWidget {
    font-family: 'Segoe UI Variable', 'Segoe UI', Arial, sans-serif;
    background-color: transparent;
}

/* Главный контейнер */
QFrame#mainContainer {
    background-color: rgba(32, 32, 32, 0.98);
    border-radius: 10px;
    border: 1px solid rgba(255, 255, 255, 0.08);
}

/* Область контента */
QWidget#contentArea {
    background-color: rgba(39, 39, 39, 0.95);
}

/* Скроллбары */
QScrollBar:vertical {
    background: rgba(255, 255, 255, 0.03);
    width: 8px;
    border-radius: 4px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background: rgba(255, 255, 255, 0.15);
    border-radius: 4px;
    min-height: 30px;
}

QScrollBar::handle:vertical:hover {
    background: rgba(255, 255, 255, 0.25);
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

/* Кастомный titlebar */
QWidget#customTitleBar {
    background-color: rgba(32, 32, 32, 0.98);
    border-top-left-radius: 10px;
    border-top-right-radius: 10px;
}

QLabel#titleLabel {
    color: #ffffff;
    font-size: 11px;
    font-weight: 500;
    background-color: transparent;
}

/* Прозрачный фон для контента */
QStackedWidget {
    background-color: transparent;
}

QFrame {
    background-color: transparent;
}
"""


class MainWindowUI:
    """
    Миксин-класс для создания UI главного окна в стиле Windows 11 Settings.
    """

    def build_ui(self: QWidget, width: int, height: int):
        """Строит UI с боковой навигацией и страницами контента"""
        
        # Определяем целевой виджет
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
            # ✅ Удаляем layout напрямую (НЕ через QWidget() - это создаёт призрачное окно!)
            old_layout.deleteLater()
        
        # Применяем стили
        target_widget.setStyleSheet(WIN11_STYLE)
        target_widget.setMinimumWidth(width)
        
        # Главный горизонтальный layout
        root = QHBoxLayout(target_widget)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        
        # ────────────────────────────────────────────────────────────
        # БОКОВАЯ ПАНЕЛЬ НАВИГАЦИИ
        # ────────────────────────────────────────────────────────────
        self.side_nav = SideNavBar(self)
        self.side_nav.section_changed.connect(self._on_section_changed)
        root.addWidget(self.side_nav)
        
        # ────────────────────────────────────────────────────────────
        # ОБЛАСТЬ КОНТЕНТА
        # ────────────────────────────────────────────────────────────
        content_area = QWidget(target_widget)  # ✅ Явный родитель
        content_area.setObjectName("contentArea")
        content_area.setStyleSheet("""
            QWidget#contentArea {
                background-color: rgba(32, 32, 32, 0.75);
                border-top-right-radius: 10px;
                border-bottom-right-radius: 10px;
            }
        """)
        
        content_layout = QVBoxLayout(content_area)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        
        # Стек страниц
        self.pages_stack = QStackedWidget()
        self.pages_stack.setStyleSheet("background-color: transparent;")
        
        # Создаем страницы
        self._create_pages()
        
        content_layout.addWidget(self.pages_stack)
        root.addWidget(content_area, 1)  # stretch=1 для растягивания
        
        # ────────────────────────────────────────────────────────────
        # СОВМЕСТИМОСТЬ СО СТАРЫМ КОДОМ
        # ────────────────────────────────────────────────────────────
        self._setup_compatibility_attrs()
        
        # Подключаем сигналы
        self._connect_page_signals()
        
    def _create_pages(self):
        """Создает все страницы контента"""
        
        # Главная страница (индекс 0)
        self.home_page = HomePage(self)
        self.pages_stack.addWidget(self.home_page)
        
        # Управление (индекс 1)
        self.control_page = ControlPage(self)
        self.pages_stack.addWidget(self.control_page)
        
        # Стратегии (индекс 2)
        self.strategies_page = StrategiesPage(self)
        self.pages_stack.addWidget(self.strategies_page)
        
        # Hostlist (индекс 3)
        self.hostlist_page = HostlistPage(self)
        self.pages_stack.addWidget(self.hostlist_page)
        
        # IPset (индекс 4)
        self.ipset_page = IpsetPage(self)
        self.pages_stack.addWidget(self.ipset_page)
        
        # Редактор стратегий (индекс 5)
        self.editor_page = EditorPage(self)
        self.pages_stack.addWidget(self.editor_page)
        
        # Настройки DPI (индекс 6)
        self.dpi_settings_page = DpiSettingsPage(self)
        self.pages_stack.addWidget(self.dpi_settings_page)
        
        # Автозапуск (индекс 7)
        self.autostart_page = AutostartPage(self)
        self.pages_stack.addWidget(self.autostart_page)
        
        # Сеть (индекс 8)
        self.network_page = NetworkPage(self)
        self.pages_stack.addWidget(self.network_page)
        
        # Оформление (индекс 9)
        self.appearance_page = AppearancePage(self)
        self.pages_stack.addWidget(self.appearance_page)
        
        # Premium (индекс 10)
        self.premium_page = PremiumPage(self)
        self.pages_stack.addWidget(self.premium_page)
        
        # Логи (индекс 11)
        self.logs_page = LogsPage(self)
        self.pages_stack.addWidget(self.logs_page)
        
        # О программе (индекс 12)
        self.about_page = AboutPage(self)
        self.pages_stack.addWidget(self.about_page)
        
    def _setup_compatibility_attrs(self):
        """Создает атрибуты для совместимости со старым кодом"""
        
        # Основные кнопки - ссылки на реальные кнопки в страницах
        self.start_btn = self.home_page.start_btn
        self.stop_btn = self.home_page.stop_btn
        
        # Кнопки управления
        # select_strategy_btn теперь скрытая заглушка (стратегии выбираются на странице)
        self.select_strategy_btn = self.strategies_page.select_strategy_btn
        self.test_connection_btn = self.home_page.test_btn
        self.open_folder_btn = self.home_page.folder_btn
        
        # Кнопки сети
        self.proxy_button = self.network_page.proxy_toggle_btn
        
        # Кнопки о программе
        self.server_status_btn = self.about_page.update_btn
        self.subscription_btn = self.about_page.premium_btn
        
        # Комбо-бокс темы
        self.theme_combo = self.appearance_page.theme_combo
        
        # Метка текущей стратегии
        self.current_strategy_label = self.strategies_page.current_strategy_label
        
        # Списки для тематических элементов
        self.themed_buttons = []
        self.themed_labels = [self.current_strategy_label]
        
    def _connect_page_signals(self):
        """Подключает сигналы от страниц"""
        
        # Сигналы-прокси для основного класса
        # select_strategy_clicked теперь не нужен - стратегии выбираются на странице
        self.start_clicked = self.home_page.start_btn.clicked
        self.stop_clicked = self.home_page.stop_btn.clicked
        self.theme_changed = self.appearance_page.theme_combo.currentTextChanged
        
        # Подключаем сигнал выбора стратегии из новой страницы
        if hasattr(self.strategies_page, 'strategy_selected'):
            self.strategies_page.strategy_selected.connect(self._on_strategy_selected_from_page)
        
        # Сигналы от страницы автозапуска
        self.autostart_page.autostart_enabled.connect(self._on_autostart_enabled)
        self.autostart_page.autostart_disabled.connect(self._on_autostart_disabled)
        
        # Дублируем кнопки на страницу управления
        self.control_page.start_btn.clicked.connect(self._proxy_start_click)
        self.control_page.stop_btn.clicked.connect(self._proxy_stop_click)
        self.control_page.test_btn.clicked.connect(self._proxy_test_click)
        self.control_page.folder_btn.clicked.connect(self._proxy_folder_click)
        
        # Подключаем кнопку Premium на главной странице
        if hasattr(self.home_page, 'premium_link_btn'):
            self.home_page.premium_link_btn.clicked.connect(self._open_subscription_dialog)
        
        # Подключаем кнопку "Управление подпиской" на странице оформления
        if hasattr(self.appearance_page, 'subscription_btn'):
            self.appearance_page.subscription_btn.clicked.connect(self._open_subscription_dialog)
        
        # Подключаем кнопку Premium на странице "О программе"
        if hasattr(self.about_page, 'premium_btn'):
            self.about_page.premium_btn.clicked.connect(self._open_subscription_dialog)
        
        # Подключаем сигнал обновления подписки от PremiumPage
        if hasattr(self.premium_page, 'subscription_updated'):
            self.premium_page.subscription_updated.connect(self._on_subscription_updated)
        
        # Подключаем смену метода запуска стратегий (от страницы настроек DPI)
        self.dpi_settings_page.launch_method_changed.connect(self._on_launch_method_changed)
        
        # Подключаем изменение фильтров - перезагружаем страницу стратегий
        if hasattr(self.dpi_settings_page, 'filters_changed'):
            self.dpi_settings_page.filters_changed.connect(self._on_filters_changed)
        
        # Для совместимости - если strategies_page также имеет сигнал
        if hasattr(self.strategies_page, 'launch_method_changed'):
            self.strategies_page.launch_method_changed.connect(self._on_launch_method_changed)
        
    def _on_filters_changed(self):
        """Обработчик изменения фильтров - перезагружаем страницу стратегий"""
        from log import log
        log("Фильтры изменены, перезагружаем страницу стратегий", "DEBUG")
        if hasattr(self, 'strategies_page') and hasattr(self.strategies_page, 'reload_for_mode_change'):
            self.strategies_page.reload_for_mode_change()
        
    def _on_launch_method_changed(self, method: str):
        """Обработчик смены метода запуска стратегий"""
        from PyQt6.QtWidgets import QMessageBox
        from log import log
        from config import WINWS_EXE, WINWS2_EXE
        
        log(f"Метод запуска изменён на: {method}", "INFO")
        
        # ✅ Обновляем путь к exe в dpi_starter
        if hasattr(self, 'dpi_starter'):
            if method == "direct":
                self.dpi_starter.winws_exe = WINWS2_EXE
                log(f"dpi_starter.winws_exe обновлён на: {WINWS2_EXE}", "INFO")
            else:
                self.dpi_starter.winws_exe = WINWS_EXE
                log(f"dpi_starter.winws_exe обновлён на: {WINWS_EXE}", "INFO")
        
        # ✅ Сбрасываем глобальный StrategyRunner чтобы он пересоздался с новым путём
        try:
            from strategy_menu.strategy_runner import reset_strategy_runner
            reset_strategy_runner()
            log("StrategyRunner сброшен для использования нового exe", "DEBUG")
        except Exception as e:
            log(f"Ошибка сброса StrategyRunner: {e}", "WARNING")
        
        # ✅ Перезагружаем страницу стратегий для нового режима
        if hasattr(self, 'strategies_page') and hasattr(self.strategies_page, 'reload_for_mode_change'):
            self.strategies_page.reload_for_mode_change()
            log("Страница стратегий перезагружена для нового режима", "DEBUG")
        
        # Показываем уведомление
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setWindowTitle("Метод запуска изменён")
        msg.setText(f"Метод запуска: {'Zapret 2 (рекомендуется)' if method == 'direct' else 'Zapret 1 (через .bat)'}")
        msg.setInformativeText("Перезапустите DPI для применения.")
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.exec()
        
    def _proxy_start_click(self):
        """Прокси для сигнала start от control_page"""
        self.home_page.start_btn.click()
        
    def _proxy_stop_click(self):
        """Прокси для сигнала stop от control_page"""
        self.home_page.stop_btn.click()
        
    def _proxy_test_click(self):
        """Прокси для теста соединения"""
        self.home_page.test_btn.click()
        
    def _proxy_folder_click(self):
        """Прокси для открытия папки"""
        self.home_page.folder_btn.click()
    
    def _open_subscription_dialog(self):
        """Переключается на страницу Premium"""
        # Индекс страницы Premium в sidebar
        # Главная(0), Управление(1), Стратегии(2), Hostlist(3), IPset(4), Настройки DPI(5),
        # Автозапуск(6), Сеть(7), Оформление(8), Premium(9), Логи(10), О программе(11)
        premium_index = 10
        self.side_nav.set_section(premium_index)
        
    def _on_section_changed(self, index: int):
        """Обработчик смены раздела в навигации"""
        self.pages_stack.setCurrentIndex(index)
        
    def _show_instruction(self):
        """Открывает PDF инструкцию по использованию Zapret"""
        try:
            from config import HELP_FOLDER
            from log import log
            
            pdf_path = os.path.join(HELP_FOLDER, "Как пользоваться Zapret.pdf")
            
            if not os.path.exists(pdf_path):
                log(f"PDF инструкция не найдена: {pdf_path}", "❌ ERROR")
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(
                    self,
                    "Файл не найден",
                    f"Инструкция не найдена:\n{pdf_path}"
                )
                return
            
            log(f"Открываем PDF инструкцию: {pdf_path}", "INFO")
            os.startfile(pdf_path)
            
        except Exception as e:
            from log import log
            log(f"Ошибка при открытии PDF инструкции: {e}", "❌ ERROR")

    def _show_premium_info(self):
        """Открывает PDF с информацией о Premium функциях"""
        try:
            from config import HELP_FOLDER
            from log import log
            
            pdf_path = os.path.join(HELP_FOLDER, "Всё о Zapret Premium и Zapret VPN (подробная инструкция).pdf")
            
            if not os.path.exists(pdf_path):
                log(f"PDF с тарифами не найден: {pdf_path}", "❌ ERROR")
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(
                    self,
                    "Файл не найден",
                    f"Информация о тарифах не найдена:\n{pdf_path}"
                )
                return
            
            log(f"Открываем PDF с тарифами: {pdf_path}", "INFO")
            
            if sys.platform == 'win32':
                os.startfile(pdf_path)
            else:
                from PyQt6.QtCore import QUrl
                from PyQt6.QtGui import QDesktopServices
                QDesktopServices.openUrl(QUrl.fromLocalFile(pdf_path))
            
        except Exception as e:
            from log import log
            log(f"Ошибка при открытии PDF с тарифами: {e}", "❌ ERROR")

    def _show_download_instruction(self):
        """Открывает PDF инструкцию по скачиванию"""
        try:
            from config import HELP_FOLDER
            from log import log
            
            pdf_path = os.path.join(HELP_FOLDER, "Как скачать Zapret.pdf")
            
            if not os.path.exists(pdf_path):
                log(f"PDF инструкция не найдена: {pdf_path}", "❌ ERROR")
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(
                    self,
                    "Файл не найден",
                    f"Инструкция не найдена:\n{pdf_path}"
                )
                return
            
            log(f"Открываем PDF инструкцию по скачиванию: {pdf_path}", "INFO")
            os.startfile(pdf_path)
            
        except Exception as e:
            from log import log
            log(f"Ошибка при открытии PDF инструкции: {e}", "❌ ERROR")

    # ────────────────────────────────────────────────────────────
    # МЕТОДЫ ОБНОВЛЕНИЯ UI (для совместимости со старым кодом)
    # ────────────────────────────────────────────────────────────
    
    def update_process_status(self, is_running: bool, strategy_name: str = None):
        """Обновляет статус процесса на всех страницах"""
        # Обновляем главную страницу
        self.home_page.update_dpi_status(is_running, strategy_name)
        
        # Обновляем страницу управления
        self.control_page.update_status(is_running)
        if strategy_name:
            self.control_page.update_strategy(strategy_name)
            
        # Обновляем старую метку статуса
        if is_running:
            self.process_status_value.setText("работает")
            self.process_status_value.setStyleSheet("color: #6ccb5f; font-size: 9pt;")
        else:
            self.process_status_value.setText("остановлен")
            self.process_status_value.setStyleSheet("color: #ff6b6b; font-size: 9pt;")
            
    def update_current_strategy_display(self, strategy_name: str):
        """Обновляет отображение текущей стратегии"""
        self.current_strategy_label.setText(strategy_name)
        self.strategies_page.update_current_strategy(strategy_name)
        self.control_page.update_strategy(strategy_name)
        self.home_page.strategy_card.set_value(
            strategy_name if strategy_name != "Автостарт DPI отключен" else "Не выбрана"
        )
        
    def update_autostart_display(self, enabled: bool, strategy_name: str = None):
        """Обновляет отображение статуса автозапуска"""
        self.home_page.update_autostart_status(enabled)
        self.autostart_page.update_status(enabled, strategy_name)
        
    def update_subscription_display(self, is_premium: bool, days: int = None):
        """Обновляет отображение статуса подписки"""
        self.home_page.update_subscription_status(is_premium, days)
        self.about_page.update_subscription_status(is_premium, days)
        
    def update_proxy_button_state(self):
        """Обновляет состояние кнопки proxy (hosts)"""
        try:
            from hosts.proxy_domains import is_domains_blocked
            is_blocked = is_domains_blocked()
            self.network_page.update_proxy_status(is_blocked)
        except Exception:
            pass
            
    def set_status_text(self, text: str, status: str = "neutral"):
        """Устанавливает текст статусной строки"""
        self.status_label.setText(text)
        self.home_page.set_status(text, status)
    
    def _on_autostart_enabled(self):
        """Обработчик включения автозапуска"""
        from log import log
        log("Автозапуск включён через страницу настроек", "INFO")
        self.update_autostart_display(True)
        
    def _on_autostart_disabled(self):
        """Обработчик отключения автозапуска"""
        from log import log
        log("Автозапуск отключён через страницу настроек", "INFO")
        self.update_autostart_display(False)
    
    def _on_subscription_updated(self, is_premium: bool, days_remaining: int):
        """Обработчик обновления статуса подписки"""
        from log import log
        log(f"Статус подписки обновлён: premium={is_premium}, days={days_remaining}", "INFO")
        self.update_subscription_display(is_premium, days_remaining if days_remaining > 0 else None)
    
    def _on_strategy_selected_from_page(self, strategy_id: str, strategy_name: str):
        """Обработчик выбора стратегии из новой страницы"""
        from log import log
        log(f"Стратегия выбрана из страницы: {strategy_id} - {strategy_name}", "INFO")
        
        # Обновляем отображение
        self.update_current_strategy_display(strategy_name)
        
        # Вызываем обработчик в главном приложении если есть
        if hasattr(self, 'parent_app') and hasattr(self.parent_app, 'on_strategy_selected_from_dialog'):
            self.parent_app.on_strategy_selected_from_dialog(strategy_id, strategy_name)
    
    def init_autostart_page(self, app_instance, bat_folder: str, json_folder: str, strategy_name: str = None):
        """Инициализирует страницу автозапуска с необходимыми параметрами"""
        self.autostart_page.set_app_instance(app_instance)
        self.autostart_page.set_folders(bat_folder, json_folder)
        if strategy_name:
            self.autostart_page.set_strategy_name(strategy_name)
    
    def show_autostart_page(self):
        """Переключается на страницу автозапуска"""
        self.side_nav.set_section(6)  # Индекс страницы автозапуска
