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

from ui.theme import THEMES, BUTTON_STYLE, COMMON_STYLE, BUTTON_HEIGHT
from ui.sidebar import SideNavBar, SettingsCard, ActionButton
from ui.custom_titlebar import DraggableWidget
from ui.pages import (
    HomePage, ControlPage, StrategiesPage, HostlistPage, NetrogatPage, CustomDomainsPage, IpsetPage, BlobsPage, CustomIpSetPage, EditorPage, DpiSettingsPage,
    AutostartPage, NetworkPage, HostsPage, BlockcheckPage, AppearancePage, AboutPage, LogsPage, PremiumPage,
    ServersPage, ConnectionTestPage, DNSCheckPage
)

import qtawesome as qta
import sys, os
from config import APP_VERSION, CHANNEL

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
        
        # ⚠️ НЕ применяем inline стили - они будут из темы QApplication
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
        self.side_nav.pin_state_changed.connect(self._on_sidebar_pin_changed)
        root.addWidget(self.side_nav)
        
        # Сохраняем ссылку на layout для управления плавающим режимом
        self._root_layout = root
        
        # ────────────────────────────────────────────────────────────
        # ОБЛАСТЬ КОНТЕНТА (с поддержкой перетаскивания окна)
        # ────────────────────────────────────────────────────────────
        content_area = DraggableWidget(target_widget)  # ✅ Позволяет перетаскивать окно за пустые области
        content_area.setObjectName("contentArea")
        # ⚠️ НЕ применяем inline стили - они будут из темы QApplication
        
        content_layout = QVBoxLayout(content_area)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        
        # Стек страниц
        self.pages_stack = QStackedWidget()
        # ⚠️ НЕ применяем inline стили - они будут из темы QApplication
        
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
        
        # Блобы - управление бинарными данными для Zapret 2 (индекс 5)
        self.blobs_page = BlobsPage(self)
        self.pages_stack.addWidget(self.blobs_page)
        
        # Редактор стратегий (индекс 6)
        self.editor_page = EditorPage(self)
        self.pages_stack.addWidget(self.editor_page)
        
        # Настройки DPI (индекс 7)
        self.dpi_settings_page = DpiSettingsPage(self)
        self.pages_stack.addWidget(self.dpi_settings_page)
        
        # === МОИ СПИСКИ ===
        # Исключения netrogat.txt (индекс 8)
        self.netrogat_page = NetrogatPage(self)
        self.pages_stack.addWidget(self.netrogat_page)
        
        # Мои домены - управление other2.txt (индекс 9)
        self.custom_domains_page = CustomDomainsPage(self)
        self.pages_stack.addWidget(self.custom_domains_page)
        
        # Мои IP - управление my-ipset.txt (индекс 10)
        self.custom_ipset_page = CustomIpSetPage(self)
        self.pages_stack.addWidget(self.custom_ipset_page)
        # === КОНЕЦ МОИ СПИСКИ ===
        
        # Автозапуск (индекс 11)
        self.autostart_page = AutostartPage(self)
        self.pages_stack.addWidget(self.autostart_page)
        
        # Сеть (индекс 12)
        self.network_page = NetworkPage(self)
        self.pages_stack.addWidget(self.network_page)

        # Диагностика соединения (индекс 13)
        self.connection_page = ConnectionTestPage(self)
        self.pages_stack.addWidget(self.connection_page)
        
        # DNS подмена - подпункт диагностики (индекс 14)
        self.dns_check_page = DNSCheckPage(self)
        self.pages_stack.addWidget(self.dns_check_page)
        
        # Hosts - разблокировка сервисов (индекс 15)
        self.hosts_page = HostsPage(self)
        self.pages_stack.addWidget(self.hosts_page)
        
        # BlockCheck (индекс 16)
        self.blockcheck_page = BlockcheckPage(self)
        self.pages_stack.addWidget(self.blockcheck_page)
        
        # Оформление (индекс 17)
        self.appearance_page = AppearancePage(self)
        self.pages_stack.addWidget(self.appearance_page)
        
        # Premium (индекс 18)
        self.premium_page = PremiumPage(self)
        self.pages_stack.addWidget(self.premium_page)
        
        # Логи (индекс 19)
        self.logs_page = LogsPage(self)
        self.pages_stack.addWidget(self.logs_page)
        
        # Серверы обновлений (индекс 20)
        self.servers_page = ServersPage(self)
        self.pages_stack.addWidget(self.servers_page)
        
        # О программе (индекс 21)
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
        
        # Кнопки о программе
        self.server_status_btn = self.about_page.update_btn
        self.subscription_btn = self.about_page.premium_btn
        
        # Метка текущей стратегии
        self.current_strategy_label = self.strategies_page.current_strategy_label
        
    def _connect_page_signals(self):
        """Подключает сигналы от страниц"""
        
        # Сигналы-прокси для основного класса
        # select_strategy_clicked теперь не нужен - стратегии выбираются на странице
        self.start_clicked = self.home_page.start_btn.clicked
        self.stop_clicked = self.home_page.stop_btn.clicked
        self.theme_changed = self.appearance_page.theme_changed
        
        # Подключаем сигнал выбора стратегии из новой страницы
        if hasattr(self.strategies_page, 'strategy_selected'):
            self.strategies_page.strategy_selected.connect(self._on_strategy_selected_from_page)
        
        # Сигналы от страницы автозапуска
        self.autostart_page.autostart_enabled.connect(self._on_autostart_enabled)
        self.autostart_page.autostart_disabled.connect(self._on_autostart_disabled)
        
        # Дублируем кнопки на страницу управления
        self.control_page.start_btn.clicked.connect(self._proxy_start_click)
        self.control_page.stop_winws_btn.clicked.connect(self._proxy_stop_click)
        self.control_page.stop_and_exit_btn.clicked.connect(self._proxy_stop_and_exit)
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
        
        # Подключаем сигнал обновления со страницы серверов
        # Обновления управляются напрямую на странице servers_page
    
    def _on_filters_changed(self):
        """Обработчик изменения фильтров - перезагружаем страницу стратегий"""
        from log import log
        log("Фильтры изменены, перезагружаем страницу стратегий", "DEBUG")
        if hasattr(self, 'strategies_page') and hasattr(self.strategies_page, 'reload_for_mode_change'):
            self.strategies_page.reload_for_mode_change()
        
    def _on_launch_method_changed(self, method: str):
        """Обработчик смены метода запуска стратегий"""
        from log import log
        from config import WINWS_EXE, WINWS2_EXE
        
        log(f"🔄 Метод запуска изменён на: {method}", "INFO")
        
        # ⚠️ СНАЧАЛА ОСТАНАВЛИВАЕМ ВСЕ ПРОЦЕССЫ winws*.exe через Win API
        if hasattr(self, 'dpi_starter') and self.dpi_starter.check_process_running_wmi(silent=True):
            log("🛑 Останавливаем все процессы winws*.exe перед переключением режима...", "INFO")
            
            try:
                from utils.process_killer import kill_winws_all
                
                # Принудительно завершаем все процессы через Win API
                killed = kill_winws_all()
                
                if killed:
                    log("✅ Все процессы winws*.exe остановлены через Win API", "INFO")
                else:
                    log("Процессы winws*.exe не найдены", "DEBUG")
                
                # Очищаем службу WinDivert
                if hasattr(self, 'dpi_starter'):
                    self.dpi_starter.cleanup_windivert_service()
                
                # Обновляем UI после остановки
                if hasattr(self, 'ui_manager'):
                    self.ui_manager.update_ui_state(running=False)
                if hasattr(self, 'process_monitor_manager'):
                    self.process_monitor_manager.on_process_status_changed(False)
                
                # Небольшая пауза для гарантии остановки
                import time
                time.sleep(0.2)
                
            except Exception as e:
                log(f"Ошибка остановки через Win API: {e}", "WARNING")
        
        # Сразу переключаемся без ожидания
        self._complete_method_switch(method)
    
    def _complete_method_switch(self, method: str):
        """Завершает переключение метода после остановки процесса"""
        from log import log
        from config import WINWS_EXE, WINWS2_EXE
        
        # ✅ Очищаем службы WinDivert через Win API
        try:
            from utils.service_manager import cleanup_windivert_services
            cleanup_windivert_services()
            log("🧹 Службы WinDivert очищены", "DEBUG")
        except Exception as e:
            log(f"Ошибка очистки служб: {e}", "DEBUG")
        
        # ✅ Обновляем путь к exe в dpi_starter
        if hasattr(self, 'dpi_starter'):
            if method == "direct":
                self.dpi_starter.winws_exe = WINWS2_EXE
                log("Переключение на winws2.exe (Direct режим)", "DEBUG")
            else:
                self.dpi_starter.winws_exe = WINWS_EXE
                log("Переключение на winws.exe (BAT режим)", "DEBUG")
        
        # ✅ Помечаем StrategyRunner для пересоздания
        try:
            from strategy_menu.strategy_runner import invalidate_strategy_runner
            invalidate_strategy_runner()
        except Exception as e:
            log(f"Ошибка инвалидации StrategyRunner: {e}", "WARNING")
        
        # ✅ Перезагружаем страницу стратегий для нового режима
        if hasattr(self, 'strategies_page') and hasattr(self.strategies_page, 'reload_for_mode_change'):
            self.strategies_page.reload_for_mode_change()
        
        # ✅ Обновляем видимость вкладки "Блобы" в сайдбаре
        if hasattr(self, 'side_nav') and hasattr(self.side_nav, 'update_blobs_visibility'):
            self.side_nav.update_blobs_visibility()
        
        log(f"✅ Переключение на режим '{method}' завершено", "INFO")
        
        # ✅ Автоматически запускаем DPI с выбранными стратегиями
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(500, lambda: self._auto_start_after_method_switch(method))
    
    def _auto_start_after_method_switch(self, method: str):
        """Автоматически запускает DPI после переключения метода"""
        from log import log
        
        try:
            if not hasattr(self, 'dpi_controller') or not self.dpi_controller:
                log("DPI контроллер не найден для автозапуска", "WARNING")
                return
            
            # Показываем спиннер на странице стратегий
            if hasattr(self, 'strategies_page'):
                self.strategies_page.show_loading()
            
            if method == "direct":
                # Zapret 2 - Direct режим
                from strategy_menu import get_direct_strategy_selections
                from strategy_menu.strategy_lists_separated import combine_strategies
                
                selections = get_direct_strategy_selections()
                combined = combine_strategies(**selections)
                
                # Формируем данные для запуска
                selected_mode = {
                    'is_combined': True,
                    'name': 'Прямой запуск',
                    'args': combined.get('args', ''),
                    'category_strategies': combined.get('category_strategies', {})
                }
                
                log(f"🚀 Автозапуск Zapret 2 (Direct) после переключения режима", "INFO")
                self.dpi_controller.start_dpi_async(selected_mode=selected_mode)
                
                # Обновляем GUI
                if hasattr(self, 'current_strategy_label'):
                    self.current_strategy_label.setText("Прямой запуск")
                if hasattr(self, 'current_strategy_name'):
                    self.current_strategy_name = "Прямой запуск"
                
                # Обновляем отображение на странице стратегий
                if hasattr(self, 'strategies_page'):
                    self.strategies_page._update_current_strategies_display()
                
            else:
                # Zapret 1 - BAT режим (отдельный ключ реестра)
                from config.reg import get_last_bat_strategy
                
                last_strategy = get_last_bat_strategy()
                
                if last_strategy and last_strategy != "Автостарт DPI отключен":
                    log(f"🚀 Автозапуск Zapret 1 (BAT): {last_strategy}", "INFO")
                    self.dpi_controller.start_dpi_async(selected_mode=last_strategy)
                    
                    # Обновляем GUI
                    if hasattr(self, 'current_strategy_label'):
                        self.current_strategy_label.setText(last_strategy)
                    if hasattr(self, 'current_strategy_name'):
                        self.current_strategy_name = last_strategy
                    
                    # Обновляем отображение на странице стратегий
                    if hasattr(self, 'strategies_page'):
                        self.strategies_page.current_strategy_label.setText(f"🎯 {last_strategy}")
                else:
                    log("⏸️ BAT режим: нет сохранённой стратегии для автозапуска", "INFO")
                    if hasattr(self, 'strategies_page'):
                        self.strategies_page.show_success()
                        self.strategies_page.current_strategy_label.setText("Не выбрана")
            
            # Запускаем мониторинг процесса
            if hasattr(self, 'strategies_page'):
                self.strategies_page._start_process_monitoring()
                
        except Exception as e:
            log(f"Ошибка автозапуска после переключения режима: {e}", "ERROR")
            import traceback
            log(traceback.format_exc(), "DEBUG")
            if hasattr(self, 'strategies_page'):
                self.strategies_page.show_success()
        
    def _proxy_start_click(self):
        """Прокси для сигнала start от control_page"""
        self.home_page.start_btn.click()
        
    def _proxy_stop_click(self):
        """Прокси для сигнала stop от control_page"""
        self.home_page.stop_btn.click()
    
    def _proxy_stop_and_exit(self):
        """Остановка winws и закрытие программы"""
        from log import log
        log("Остановка winws и закрытие программы...", "INFO")
        
        # Используем dpi_controller для корректной остановки и выхода
        if hasattr(self, 'dpi_controller') and self.dpi_controller:
            self._closing_completely = True
            self.dpi_controller.stop_and_exit_async()
        else:
            # Fallback - просто останавливаем и выходим
            self.home_page.stop_btn.click()
            from PyQt6.QtWidgets import QApplication
            QApplication.quit()
        
    def _proxy_test_click(self):
        """Прокси для теста соединения"""
        self.home_page.test_btn.click()
        
    def _proxy_folder_click(self):
        """Прокси для открытия папки"""
        self.home_page.folder_btn.click()
    
    def _open_subscription_dialog(self):
        """Переключается на страницу Premium (донат)"""
        index = self.pages_stack.indexOf(self.premium_page)
        if index >= 0:
            self.side_nav.set_page(index)
        
    def _on_section_changed(self, index: int):
        """Обработчик смены раздела в навигации"""
        self.pages_stack.setCurrentIndex(index)
    
    def _on_sidebar_pin_changed(self, is_pinned: bool):
        """Обработчик смены режима закрепления сайдбара"""
        from log import log
        
        if is_pinned:
            # Закреплённый режим - сайдбар часть layout (фиксированная ширина)
            log("Сайдбар закреплён", "DEBUG")
            self.side_nav.setMinimumWidth(self.side_nav.EXPANDED_WIDTH)
            self.side_nav.setMaximumWidth(self.side_nav.EXPANDED_WIDTH)
        else:
            # Плавающий режим - снимаем ограничения для анимации
            log("Сайдбар откреплён (плавающий режим)", "DEBUG")
            self.side_nav.setMinimumWidth(0)
            self.side_nav.setMaximumWidth(16777215)  # QWIDGETSIZE_MAX
        
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
            
    def update_current_strategy_display(self, strategy_name: str):
        """Обновляет отображение текущей стратегии"""
        self.current_strategy_label.setText(strategy_name)
        self.strategies_page.update_current_strategy(strategy_name)
        self.control_page.update_strategy(strategy_name)
        
        # Для главной страницы обрезаем длинное название
        display_name = strategy_name if strategy_name != "Автостарт DPI отключен" else "Не выбрана"
        if hasattr(self.home_page, '_truncate_strategy_name'):
            display_name = self.home_page._truncate_strategy_name(display_name)
        self.home_page.strategy_card.set_value(display_name)
        
    def update_autostart_display(self, enabled: bool, strategy_name: str = None):
        """Обновляет отображение статуса автозапуска"""
        self.home_page.update_autostart_status(enabled)
        self.autostart_page.update_status(enabled, strategy_name)
        
    def update_subscription_display(self, is_premium: bool, days: int = None):
        """Обновляет отображение статуса подписки"""
        self.home_page.update_subscription_status(is_premium, days)
        self.about_page.update_subscription_status(is_premium, days)
        
            
    def set_status_text(self, text: str, status: str = "neutral"):
        """Устанавливает текст статусной строки"""
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
        
        # ✅ Обновляем премиум функции в галерее тем
        if hasattr(self, 'appearance_page') and self.appearance_page:
            self.appearance_page.set_premium_status(is_premium)
            log(f"Галерея тем обновлена: premium={is_premium}", "DEBUG")
        
        # ✅ Управляем гирляндой и снежинками
        if hasattr(self, 'garland'):
            from config.reg import get_garland_enabled
            should_show = is_premium and get_garland_enabled()
            self.garland.set_enabled(should_show)
            if not is_premium:
                self.garland.set_enabled(False)
            log(f"Гирлянда: visible={should_show}", "DEBUG")
        
        if hasattr(self, 'snowflakes'):
            from config.reg import get_snowflakes_enabled
            should_show = is_premium and get_snowflakes_enabled()
            self.snowflakes.set_enabled(should_show)
            if not is_premium:
                self.snowflakes.set_enabled(False)
            log(f"Снежинки: visible={should_show}", "DEBUG")
    
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
        index = self.pages_stack.indexOf(self.autostart_page)
        if index >= 0:
            self.side_nav.set_page(index)
        
    def show_hosts_page(self):
        """Переключается на страницу Hosts"""
        index = self.pages_stack.indexOf(self.hosts_page)
        if index >= 0:
            self.side_nav.set_page(index)
        
    def show_servers_page(self):
        """Переключается на страницу серверов обновлений"""
        index = self.pages_stack.indexOf(self.servers_page)
        if index >= 0:
            self.side_nav.set_page(index)
