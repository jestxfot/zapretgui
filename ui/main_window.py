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
    HomePage, ControlPage, HostlistPage, NetrogatPage, CustomDomainsPage, IpsetPage, BlobsPage, CustomIpSetPage, EditorPage, DpiSettingsPage,
    AutostartPage, NetworkPage, HostsPage, BlockcheckPage, AppearancePage, AboutPage, LogsPage, PremiumPage,
    HelpPage, ServersPage, ConnectionTestPage, DNSCheckPage, OrchestraPage, OrchestraLockedPage, OrchestraBlockedPage, OrchestraWhitelistPage, OrchestraRatingsPage,
    PresetConfigPage, StrategySortPage, Zapret2OrchestraStrategiesPage,
    Zapret2DirectControlPage, Zapret2StrategiesPageNew, StrategyDetailPage,
    Zapret1DirectStrategiesPage, BatStrategiesPage, PresetsPage, MyCategoriesPage
)

import qtawesome as qta
import sys, os
from config import APP_VERSION, CHANNEL, MIN_WIDTH
from ui.page_names import PageName, SectionName, SECTION_TO_PAGE

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
        target_widget.setMinimumWidth(MIN_WIDTH)
        
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

        # Hardening: clear any transient popups/grabs that could break hover/cursor
        # whenever the visible page changes (covers non-standard navigation paths too).
        try:
            self.pages_stack.currentChanged.connect(
                lambda idx: self._dismiss_transient_ui(reason=f"pages_stack_changed:{idx}")
            )
        except Exception:
            pass
        
        content_layout.addWidget(self.pages_stack)
        root.addWidget(content_area, 1)  # stretch=1 для растягивания
        
        # ────────────────────────────────────────────────────────────
        # СОВМЕСТИМОСТЬ СО СТАРЫМ КОДОМ
        # ────────────────────────────────────────────────────────────
        self._setup_compatibility_attrs()
        
        # Подключаем сигналы
        self._connect_page_signals()

        # Session memory: remember last opened direct_zapret2 category detail page.
        # (Used to restore context when re-opening the Strategies section.)
        if not hasattr(self, "_direct_zapret2_last_opened_category_key"):
            self._direct_zapret2_last_opened_category_key = None  # type: ignore[attr-defined]
        if not hasattr(self, "_direct_zapret2_restore_detail_on_open"):
            self._direct_zapret2_restore_detail_on_open = False  # type: ignore[attr-defined]
        
    def _create_pages(self):
        """Создает все страницы контента"""

        # Главная страница
        self.home_page = HomePage(self)
        self.pages_stack.addWidget(self.home_page)
        
        # Управление
        self.control_page = ControlPage(self)
        self.pages_stack.addWidget(self.control_page)

        # Zapret 2 Direct: управление (главная вкладка "Стратегии" для direct_zapret2)
        self.zapret2_direct_control_page = Zapret2DirectControlPage(self)
        self.pages_stack.addWidget(self.zapret2_direct_control_page)

        # Zapret 2 Direct стратегии (NEW UI)
        self.zapret2_strategies_page = Zapret2StrategiesPageNew(self)
        self.pages_stack.addWidget(self.zapret2_strategies_page)

        # Strategy Detail Page (for category drill-down)
        self.strategy_detail_page = StrategyDetailPage(self)
        self.pages_stack.addWidget(self.strategy_detail_page)

        # Zapret 2 Orchestra стратегии
        self.zapret2_orchestra_strategies_page = Zapret2OrchestraStrategiesPage(self)
        self.pages_stack.addWidget(self.zapret2_orchestra_strategies_page)

        # Zapret 1 Direct стратегии
        self.zapret1_strategies_page = Zapret1DirectStrategiesPage(self)
        self.pages_stack.addWidget(self.zapret1_strategies_page)

        # BAT стратегии
        self.bat_strategies_page = BatStrategiesPage(self)
        self.pages_stack.addWidget(self.bat_strategies_page)

        # Сортировка стратегий
        self.strategy_sort_page = StrategySortPage(self)
        self.pages_stack.addWidget(self.strategy_sort_page)

        # Конфиг preset-zapret2.txt
        self.preset_config_page = PresetConfigPage(self)
        self.pages_stack.addWidget(self.preset_config_page)

        # Мои категории (общий файл для direct режимов)
        self.my_categories_page = MyCategoriesPage(self)
        self.pages_stack.addWidget(self.my_categories_page)

        # Hostlist
        self.hostlist_page = HostlistPage(self)
        self.pages_stack.addWidget(self.hostlist_page)

        # IPset
        self.ipset_page = IpsetPage(self)
        self.pages_stack.addWidget(self.ipset_page)

        # Блобы - управление бинарными данными для Zapret 2
        self.blobs_page = BlobsPage(self)
        self.pages_stack.addWidget(self.blobs_page)

        # Редактор стратегий
        self.editor_page = EditorPage(self)
        self.pages_stack.addWidget(self.editor_page)

        # Настройки DPI
        self.dpi_settings_page = DpiSettingsPage(self)
        self.pages_stack.addWidget(self.dpi_settings_page)

        # Пресеты настроек (только direct_zapret2)
        self.presets_page = PresetsPage(self)
        self.pages_stack.addWidget(self.presets_page)

        # === МОИ СПИСКИ ===
        # Исключения netrogat.txt
        self.netrogat_page = NetrogatPage(self)
        self.pages_stack.addWidget(self.netrogat_page)

        # Мои домены - управление other2.txt
        self.custom_domains_page = CustomDomainsPage(self)
        self.pages_stack.addWidget(self.custom_domains_page)

        # Мои IP - управление my-ipset.txt
        self.custom_ipset_page = CustomIpSetPage(self)
        self.pages_stack.addWidget(self.custom_ipset_page)
        # === КОНЕЦ МОИ СПИСКИ ===

        # Автозапуск
        self.autostart_page = AutostartPage(self)
        self.pages_stack.addWidget(self.autostart_page)

        # Сеть
        self.network_page = NetworkPage(self)
        self.pages_stack.addWidget(self.network_page)

        # Диагностика соединения
        self.connection_page = ConnectionTestPage(self)
        self.pages_stack.addWidget(self.connection_page)

        # DNS подмена - подпункт диагностики
        self.dns_check_page = DNSCheckPage(self)
        self.pages_stack.addWidget(self.dns_check_page)

        # Hosts - разблокировка сервисов
        self.hosts_page = HostsPage(self)
        self.pages_stack.addWidget(self.hosts_page)

        # BlockCheck
        self.blockcheck_page = BlockcheckPage(self)
        self.pages_stack.addWidget(self.blockcheck_page)

        # Оформление
        self.appearance_page = AppearancePage(self)
        self.pages_stack.addWidget(self.appearance_page)

        # Premium
        self.premium_page = PremiumPage(self)
        self.pages_stack.addWidget(self.premium_page)

        # Логи
        self.logs_page = LogsPage(self)
        self.pages_stack.addWidget(self.logs_page)

        # Серверы обновлений
        self.servers_page = ServersPage(self)
        self.pages_stack.addWidget(self.servers_page)

        # О программе
        self.about_page = AboutPage(self)
        self.pages_stack.addWidget(self.about_page)

        # Справка (подпункт "О программе")
        self.help_page = HelpPage(self)
        self.pages_stack.addWidget(self.help_page)

        # Оркестр - автообучение (скрытая вкладка)
        self.orchestra_page = OrchestraPage(self)
        self.pages_stack.addWidget(self.orchestra_page)

        # Залоченные стратегии оркестратора (вместо Hostlist при оркестраторе)
        self.orchestra_locked_page = OrchestraLockedPage(self)
        self.pages_stack.addWidget(self.orchestra_locked_page)

        # Заблокированные стратегии оркестратора (вместо IPset при оркестраторе)
        self.orchestra_blocked_page = OrchestraBlockedPage(self)
        self.pages_stack.addWidget(self.orchestra_blocked_page)

        # Белый список оркестратора (вместо Исключений при оркестраторе)
        self.orchestra_whitelist_page = OrchestraWhitelistPage(self)
        self.pages_stack.addWidget(self.orchestra_whitelist_page)

        # История стратегий с рейтингами
        self.orchestra_ratings_page = OrchestraRatingsPage(self)
        self.pages_stack.addWidget(self.orchestra_ratings_page)

        # Реестр страниц по имени (для навигации без индексов)
        self.pages: dict[PageName, QWidget] = {
            PageName.HOME: self.home_page,
            PageName.CONTROL: self.control_page,
            PageName.ZAPRET2_DIRECT_CONTROL: self.zapret2_direct_control_page,
            PageName.ZAPRET2_DIRECT: self.zapret2_strategies_page,
            PageName.STRATEGY_DETAIL: self.strategy_detail_page,
            PageName.ZAPRET2_ORCHESTRA: self.zapret2_orchestra_strategies_page,
            PageName.ZAPRET1_DIRECT: self.zapret1_strategies_page,
            PageName.BAT_STRATEGIES: self.bat_strategies_page,
            PageName.STRATEGY_SORT: self.strategy_sort_page,
            PageName.PRESET_CONFIG: self.preset_config_page,
            PageName.MY_CATEGORIES: self.my_categories_page,
            PageName.HOSTLIST: self.hostlist_page,
            PageName.IPSET: self.ipset_page,
            PageName.BLOBS: self.blobs_page,
            PageName.EDITOR: self.editor_page,
            PageName.DPI_SETTINGS: self.dpi_settings_page,
            PageName.PRESETS: self.presets_page,
            PageName.NETROGAT: self.netrogat_page,
            PageName.CUSTOM_DOMAINS: self.custom_domains_page,
            PageName.CUSTOM_IPSET: self.custom_ipset_page,
            PageName.AUTOSTART: self.autostart_page,
            PageName.NETWORK: self.network_page,
            PageName.CONNECTION_TEST: self.connection_page,
            PageName.DNS_CHECK: self.dns_check_page,
            PageName.HOSTS: self.hosts_page,
            PageName.BLOCKCHECK: self.blockcheck_page,
            PageName.APPEARANCE: self.appearance_page,
            PageName.PREMIUM: self.premium_page,
            PageName.LOGS: self.logs_page,
            PageName.SERVERS: self.servers_page,
            PageName.ABOUT: self.about_page,
            PageName.HELP: self.help_page,
            PageName.ORCHESTRA: self.orchestra_page,
            PageName.ORCHESTRA_LOCKED: self.orchestra_locked_page,
            PageName.ORCHESTRA_BLOCKED: self.orchestra_blocked_page,
            PageName.ORCHESTRA_WHITELIST: self.orchestra_whitelist_page,
            PageName.ORCHESTRA_RATINGS: self.orchestra_ratings_page,
        }

    def get_page(self, name: PageName) -> QWidget:
        """Возвращает виджет страницы по имени"""
        return self.pages.get(name)

    def _dismiss_transient_ui(self, *, reason: str = "") -> None:
        """
        Best-effort cleanup of transient popup/tooltip/preview windows and
        input-grab/override-cursor states that can break hover/cursor updates.
        """
        try:
            from PyQt6.QtCore import Qt
            from PyQt6.QtWidgets import QApplication, QToolTip, QWidget
        except Exception:
            return

        cleaned: list[str] = []

        # If updates were left disabled, hover animations/cursor changes may appear "stuck".
        try:
            if not bool(self.updatesEnabled()):
                self.setUpdatesEnabled(True)
                cleaned.append("updatesEnabled")
        except Exception:
            pass

        # Native Qt tooltips
        try:
            QToolTip.hideText()
        except Exception:
            pass

        # App hover tooltips
        try:
            from ui.widgets.strategies_tooltip import strategies_tooltip_manager
            strategies_tooltip_manager.hide_immediately()
        except Exception:
            pass
        try:
            from strategy_menu.hover_tooltip import tooltip_manager
            tooltip_manager.hide_immediately()
        except Exception:
            pass

        # Preview popups (ArgsPreviewDialog used in multiple places)
        try:
            from strategy_menu.args_preview_dialog import preview_manager
            preview_manager.cleanup()
        except Exception:
            pass
        try:
            if hasattr(self, "strategy_detail_page"):
                self.strategy_detail_page._close_preview_dialog(force=True)  # type: ignore[attr-defined]
        except Exception:
            pass

        app = QApplication.instance()
        if not app:
            return

        # Clear stuck override cursor stack (e.g. WaitCursor).
        try:
            if QApplication.overrideCursor() is not None:
                cleaned.append("overrideCursor")
            while QApplication.overrideCursor() is not None:
                QApplication.restoreOverrideCursor()
        except Exception:
            pass

        # Release mouse/keyboard grabs if something grabbed input.
        try:
            mg = None
            for obj in (app, QApplication, QWidget):
                try:
                    mg = obj.mouseGrabber()  # type: ignore[attr-defined]
                    break
                except Exception:
                    continue
            if mg is not None:
                cleaned.append(f"mouseGrabber:{mg.__class__.__name__}")
                try:
                    mg.releaseMouse()
                except Exception:
                    pass
        except Exception:
            pass
        try:
            kg = None
            for obj in (app, QApplication, QWidget):
                try:
                    kg = obj.keyboardGrabber()  # type: ignore[attr-defined]
                    break
                except Exception:
                    continue
            if kg is not None:
                cleaned.append(f"keyboardGrabber:{kg.__class__.__name__}")
                try:
                    kg.releaseKeyboard()
                except Exception:
                    pass
        except Exception:
            pass

        # Close active popup widget(s) that may keep Qt in a "popup" mode and break hover.
        try:
            for _ in range(6):
                w = app.activePopupWidget()
                if not w:
                    break
                cleaned.append(f"activePopup:{w.__class__.__name__}")
                try:
                    w.hide()
                except Exception:
                    pass
                try:
                    w.close()
                except Exception:
                    pass
                try:
                    w.deleteLater()
                except Exception:
                    pass
        except Exception:
            pass

        # Also close any visible popup-like top-level windows (defensive).
        # Important: don't use a naive `bool(flags & Qt.WindowType.Popup)` check,
        # because `Qt.WindowType.Popup` includes the `Window` bit (value 0x9),
        # so `Window` would match too.
        try:
            try:
                main_win = self.window()
            except Exception:
                main_win = None
            for w in list(app.topLevelWidgets()):
                try:
                    if main_win is not None and w is main_win:
                        continue
                    if not w.isVisible():
                        continue
                    wt = w.windowType()
                    if wt in (Qt.WindowType.Popup, Qt.WindowType.ToolTip, Qt.WindowType.Tool):
                        cleaned.append(f"popupWindow:{w.__class__.__name__}")
                        try:
                            w.hide()
                        except Exception:
                            pass
                        try:
                            w.close()
                        except Exception:
                            pass
                        try:
                            w.deleteLater()
                        except Exception:
                            pass
                except Exception:
                    continue
        except Exception:
            pass

        if cleaned:
            try:
                from log import log
                suffix = f" ({reason})" if reason else ""
                log(f"Dismissed transient UI{suffix}: {', '.join(cleaned)}", "DEBUG")
            except Exception:
                pass

    def show_page(self, name: PageName) -> bool:
        """Переключает на указанную страницу. Возвращает True при успехе."""
        # Defensive: clear any transient popups/grabs that may break hover/cursor.
        try:
            self._dismiss_transient_ui(reason=f"show_page:{name}")
        except Exception:
            pass

        page = self.pages.get(name)
        if page:
            self.pages_stack.setCurrentWidget(page)
            return True
        return False

    def _setup_compatibility_attrs(self):
        """Создает атрибуты для совместимости со старым кодом"""
        
        # Основные кнопки - ссылки на реальные кнопки в страницах
        self.start_btn = self.home_page.start_btn
        self.stop_btn = self.home_page.stop_btn

        # Текущая стратегия (старый код ожидает QLabel на self.current_strategy_label).
        # В direct_zapret2 роль "главной" страницы управления переносится в раздел "Стратегии",
        # поэтому используем label от Zapret2DirectControlPage если он доступен.
        if hasattr(self, "zapret2_direct_control_page") and hasattr(self.zapret2_direct_control_page, "strategy_label"):
            self.current_strategy_label = self.zapret2_direct_control_page.strategy_label
        elif hasattr(self.control_page, "strategy_label"):
            self.current_strategy_label = self.control_page.strategy_label

        # Кнопки управления
        self.test_connection_btn = self.home_page.test_btn
        self.open_folder_btn = self.home_page.folder_btn

        # Кнопки о программе
        self.server_status_btn = self.about_page.update_btn
        self.subscription_btn = self.about_page.premium_btn
        
    def _connect_page_signals(self):
        """Подключает сигналы от страниц"""
        
        # Сигналы-прокси для основного класса
        self.start_clicked = self.home_page.start_btn.clicked
        self.stop_clicked = self.home_page.stop_btn.clicked
        self.theme_changed = self.appearance_page.theme_changed

        # Zapret 1 Direct сигналы
        if hasattr(self, 'zapret1_strategies_page') and hasattr(self.zapret1_strategies_page, 'strategy_selected'):
            self.zapret1_strategies_page.strategy_selected.connect(self._on_strategy_selected_from_page)

        # Zapret 2 Direct сигналы
        if hasattr(self, 'zapret2_strategies_page') and hasattr(self.zapret2_strategies_page, 'strategy_selected'):
            self.zapret2_strategies_page.strategy_selected.connect(self._on_strategy_selected_from_page)

        # Zapret 2 NEW UI - navigation signals
        if hasattr(self, 'zapret2_strategies_page') and hasattr(self.zapret2_strategies_page, 'open_category_detail'):
            self.zapret2_strategies_page.open_category_detail.connect(self._on_open_category_detail)

        # Strategy Detail Page signals
        if hasattr(self, 'strategy_detail_page'):
            if hasattr(self.strategy_detail_page, 'back_clicked'):
                self.strategy_detail_page.back_clicked.connect(self._on_strategy_detail_back)
            if hasattr(self.strategy_detail_page, 'strategy_selected'):
                self.strategy_detail_page.strategy_selected.connect(self._on_strategy_detail_selected)
            if hasattr(self.strategy_detail_page, 'filter_mode_changed'):
                self.strategy_detail_page.filter_mode_changed.connect(self._on_strategy_detail_filter_mode_changed)

        # Zapret 2 Orchestra сигналы
        if hasattr(self, 'zapret2_orchestra_strategies_page') and hasattr(self.zapret2_orchestra_strategies_page, 'strategy_selected'):
            self.zapret2_orchestra_strategies_page.strategy_selected.connect(self._on_strategy_selected_from_page)

        # BAT страница сигналы
        if hasattr(self, 'bat_strategies_page') and hasattr(self.bat_strategies_page, 'strategy_selected'):
            self.bat_strategies_page.strategy_selected.connect(self._on_strategy_selected_from_page)

        # Сигналы от страницы автозапуска
        self.autostart_page.autostart_enabled.connect(self._on_autostart_enabled)
        self.autostart_page.autostart_disabled.connect(self._on_autostart_disabled)
        self.autostart_page.navigate_to_dpi_settings.connect(self._navigate_to_dpi_settings)

        # Подключаем обновление темы для страницы автозапуска
        self.appearance_page.theme_changed.connect(self.autostart_page.on_theme_changed)

        # Дублируем кнопки на страницу управления
        self.control_page.start_btn.clicked.connect(self._proxy_start_click)
        self.control_page.stop_winws_btn.clicked.connect(self._proxy_stop_click)
        self.control_page.stop_and_exit_btn.clicked.connect(self._proxy_stop_and_exit)
        self.control_page.test_btn.clicked.connect(self._proxy_test_click)
        self.control_page.folder_btn.clicked.connect(self._proxy_folder_click)

        # Direct-zapret2: дублируем кнопки на главную вкладку "Стратегии".
        try:
            page = getattr(self, "zapret2_direct_control_page", None)
            if page is not None:
                page.start_btn.clicked.connect(self._proxy_start_click)
                page.stop_winws_btn.clicked.connect(self._proxy_stop_click)
                page.stop_and_exit_btn.clicked.connect(self._proxy_stop_and_exit)
                page.test_btn.clicked.connect(self._proxy_test_click)
                page.folder_btn.clicked.connect(self._proxy_folder_click)
        except Exception:
            pass
        
        # Подключаем кнопку Premium на главной странице
        if hasattr(self.home_page, 'premium_link_btn'):
            self.home_page.premium_link_btn.clicked.connect(self._open_subscription_dialog)

        # Подключаем навигацию по карточкам на главной странице
        self.home_page.navigate_to_control.connect(self._navigate_to_control)
        self.home_page.navigate_to_strategies.connect(self._navigate_to_strategies)
        self.home_page.navigate_to_autostart.connect(self.show_autostart_page)
        self.home_page.navigate_to_premium.connect(self._open_subscription_dialog)

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

        # Подключаем обновление PresetConfigPage при смене метода запуска
        self.dpi_settings_page.launch_method_changed.connect(self.preset_config_page.refresh_for_current_mode)

        # Подключаем сигналы от OrchestraPage
        if hasattr(self, 'orchestra_page'):
            self.orchestra_page.clear_learned_requested.connect(self._on_clear_learned_requested)

        # Связываем страницу сортировки со страницей стратегий (асинхронное обновление фильтров)
        if hasattr(self.zapret2_strategies_page, 'on_external_filters_changed'):
            self.strategy_sort_page.filters_changed.connect(
                self.zapret2_strategies_page.on_external_filters_changed
            )
        if hasattr(self.zapret2_strategies_page, 'on_external_sort_changed'):
            self.strategy_sort_page.sort_changed.connect(
                self.zapret2_strategies_page.on_external_sort_changed
            )

        # Подключаем сигналы от PresetsPage
        if hasattr(self, 'presets_page') and hasattr(self.presets_page, 'preset_switched'):
            self.presets_page.preset_switched.connect(self._on_preset_switched)

    def _on_preset_switched(self, preset_name: str):
        """Обработчик переключения пресета - перезапускает DPI если запущен"""
        from log import log
        log(f"Пресет переключен: {preset_name}", "INFO")

        # Перезапуск DPI если он запущен
        if hasattr(self, 'dpi_controller') and self.dpi_controller:
            if self.dpi_controller.is_running():
                log("DPI запущен - выполняем перезапуск после смены пресета", "INFO")
                self.dpi_controller.restart_dpi_async()

        # Асинхронно обновляем UI страниц, завязанных на preset-zapret2.txt
        self._schedule_refresh_after_preset_switch()

    def _schedule_refresh_after_preset_switch(self):
        """Обновляет страницы, которые читают настройки из активного пресета."""
        try:
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(0, self._refresh_pages_after_preset_switch)
        except Exception:
            # If Qt timer is unavailable, fallback to direct call.
            try:
                self._refresh_pages_after_preset_switch()
            except Exception:
                pass

    def _refresh_pages_after_preset_switch(self):
        """Перечитывает preset и обновляет зависимые страницы (без блокировки UI)."""
        from log import log

        # Стратегии (direct_zapret2) — обновить выборы/бейджи без перестроения реестра
        try:
            page = getattr(self, "zapret2_strategies_page", None)
            if page and hasattr(page, "refresh_from_preset_switch"):
                page.refresh_from_preset_switch()
        except Exception as e:
            log(f"Ошибка обновления zapret2_strategies_page после смены пресета: {e}", "DEBUG")

        # Детальная страница категории — если открыта, перечитать настройки/выбор из пресета
        try:
            detail = getattr(self, "strategy_detail_page", None)
            if detail and hasattr(detail, "refresh_from_preset_switch"):
                detail.refresh_from_preset_switch()
        except Exception as e:
            log(f"Ошибка обновления strategy_detail_page после смены пресета: {e}", "DEBUG")

        # Обновить краткое отображение "текущих стратегий" (если используется direct_zapret2)
        try:
            display_name = self._get_direct_strategy_summary()
            if display_name:
                self.update_current_strategy_display(display_name)
        except Exception as e:
            log(f"Ошибка обновления display стратегии после смены пресета: {e}", "DEBUG")

    def _on_clear_learned_requested(self):
        """Обработчик очистки данных обучения"""
        from log import log
        log("Запрошена очистка данных обучения", "INFO")
        if hasattr(self, 'orchestra_runner') and self.orchestra_runner:
            self.orchestra_runner.clear_learned_data()
            log("Данные обучения очищены", "INFO")

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
        from config import get_winws_exe_for_method, is_zapret2_mode
        
        # Очищаем службы WinDivert через Win API
        try:
            from utils.service_manager import cleanup_windivert_services
            cleanup_windivert_services()
            log("🧹 Службы WinDivert очищены", "DEBUG")
        except Exception as e:
            log(f"Ошибка очистки служб: {e}", "DEBUG")

        # Обновляем путь к exe в dpi_starter
        if hasattr(self, 'dpi_starter'):
            self.dpi_starter.winws_exe = get_winws_exe_for_method(method)
            if is_zapret2_mode(method):
                log(f"Переключение на winws2.exe ({method} режим)", "DEBUG")
            else:
                log("Переключение на winws.exe (BAT режим)", "DEBUG")
        
        # Помечаем StrategyRunner для пересоздания
        try:
            from launcher_common import invalidate_strategy_runner
            invalidate_strategy_runner()
        except Exception as e:
            log(f"Ошибка инвалидации StrategyRunner: {e}", "WARNING")
        
        # ✅ ЕСЛИ режим = direct_zapret2 → ТОЛЬКО создаем файл если не существует
        if method == "direct_zapret2":
            from preset_zapret2 import ensure_default_preset_exists
            ensure_default_preset_exists()
        # NOTE: Другие режимы (orchestra, zapret1, bat) НЕ используют preset-zapret2.txt
        
        # Перезагружаем страницы стратегий для нового режима
        if hasattr(self, 'zapret2_strategies_page') and hasattr(self.zapret2_strategies_page, 'reload_for_mode_change'):
            self.zapret2_strategies_page.reload_for_mode_change()
        if hasattr(self, 'zapret2_orchestra_strategies_page') and hasattr(self.zapret2_orchestra_strategies_page, 'reload_for_mode_change'):
            self.zapret2_orchestra_strategies_page.reload_for_mode_change()
        if hasattr(self, 'zapret1_strategies_page') and hasattr(self.zapret1_strategies_page, 'reload_for_mode_change'):
            self.zapret1_strategies_page.reload_for_mode_change()
        if hasattr(self, 'bat_strategies_page') and hasattr(self.bat_strategies_page, 'reload_for_mode_change'):
            self.bat_strategies_page.reload_for_mode_change()
        
        # Обновляем видимость подпунктов в группе "Стратегии" в сайдбаре
        if hasattr(self, 'side_nav') and hasattr(self.side_nav, 'update_strategies_submenu_visibility'):
            self.side_nav.update_strategies_submenu_visibility()
        elif hasattr(self, 'side_nav') and hasattr(self.side_nav, 'update_blobs_visibility'):
            # обратная совместимость
            self.side_nav.update_blobs_visibility()

        # Обновляем видимость вкладок оркестратора
        if hasattr(self, 'side_nav') and hasattr(self.side_nav, 'update_orchestra_visibility'):
            self.side_nav.update_orchestra_visibility()

        # Обновляем видимость вкладки "Пресеты"
        if hasattr(self, 'side_nav') and hasattr(self.side_nav, 'update_presets_visibility'):
            self.side_nav.update_presets_visibility()

        log(f"✅ Переключение на режим '{method}' завершено", "INFO")
        
        # Автоматически запускаем DPI с выбранными стратегиями
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(500, lambda: self._auto_start_after_method_switch(method))

        # UX: если пользователь меняет метод — логично показать страницу стратегий для этого метода.
        # Ограничиваемся случаями, когда пользователь уже находится в "стратегийной" зоне UI
        # (страницы стратегий/деталей/настроек DPI).
        try:
            self._redirect_to_strategies_page_for_method(method)
        except Exception as e:
            log(f"Ошибка UX-редиректа на страницу стратегий: {e}", "DEBUG")

    def _redirect_to_strategies_page_for_method(self, method: str) -> None:
        """Переводит на соответствующую страницу стратегий для текущего метода запуска."""
        from ui.page_names import PageName, SectionName

        current = None
        try:
            current = self.pages_stack.currentWidget() if hasattr(self, "pages_stack") else None
        except Exception:
            current = None

        strategies_context_pages = set()
        for attr in (
            "dpi_settings_page",
            "zapret2_strategies_page",
            "zapret2_orchestra_strategies_page",
            "zapret1_strategies_page",
            "bat_strategies_page",
            "strategy_detail_page",
            "strategy_sort_page",
        ):
            page = getattr(self, attr, None)
            if page is not None:
                strategies_context_pages.add(page)

        if current is not None and current not in strategies_context_pages:
            return

        if method == "orchestra":
            target_page = PageName.ORCHESTRA
        elif method == "direct_zapret2_orchestra":
            target_page = PageName.ZAPRET2_ORCHESTRA
        elif method == "direct_zapret2":
            target_page = PageName.ZAPRET2_DIRECT_CONTROL
        elif method == "direct_zapret1":
            target_page = PageName.ZAPRET1_DIRECT
        else:  # bat
            target_page = PageName.BAT_STRATEGIES

        self.show_page(target_page)
        if hasattr(self, "side_nav"):
            self.side_nav.set_section_by_name(SectionName.STRATEGIES, emit_signal=False)
    
    def _auto_start_after_method_switch(self, method: str):
        """Автоматически запускает DPI после переключения метода"""
        from log import log
        
        try:
            if not hasattr(self, 'dpi_controller') or not self.dpi_controller:
                log("DPI контроллер не найден для автозапуска", "WARNING")
                return
            
            if method == "orchestra":
                # Оркестр
                log(f"🚀 Автозапуск Оркестр", "INFO")
                self.dpi_controller.start_dpi_async(selected_mode=None, launch_method="orchestra")

            elif method == "direct_zapret2":
                # ✅ ТОЛЬКО ДЛЯ direct_zapret2 используем preset-zapret2.txt!
                from config import get_dpi_autostart
                if not get_dpi_autostart():
                    log("⏸️ direct_zapret2: автозагрузка DPI отключена", "INFO")
                    return

                from preset_zapret2 import get_active_preset_path, get_active_preset_name
                
                preset_path = get_active_preset_path()
                preset_name = get_active_preset_name() or "Default"
                
                if not preset_path.exists():
                    log(f"❌ Preset файл не найден: {preset_path}", "ERROR")
                    return
                
                selected_mode = {
                    'is_preset_file': True,
                    'name': f"Пресет: {preset_name}",
                    'preset_path': str(preset_path)
                }

                log(f"🚀 Автозапуск из preset файла: {preset_path}", "INFO")
                self.dpi_controller.start_dpi_async(selected_mode=selected_mode, launch_method=method)

            elif method in ("direct_zapret2_orchestra", "direct_zapret1"):
                # ✅ ДЛЯ ДРУГИХ РЕЖИМОВ - используем combine_strategies (НЕ preset файл!)
                from strategy_menu import get_direct_strategy_selections
                from launcher_common import combine_strategies

                selections = get_direct_strategy_selections()
                combined = combine_strategies(**selections)

                if method == "direct_zapret2_orchestra":
                    mode_name = "Оркестратор Z2"
                else:
                    mode_name = "Прямой Z1"

                selected_mode = {
                    'is_combined': True,
                    'name': mode_name,
                    'args': combined.get('args', ''),
                    'category_strategies': combined.get('category_strategies', {})
                }

                log(f"🚀 Автозапуск через динамические аргументы ({method})", "INFO")
                self.dpi_controller.start_dpi_async(selected_mode=selected_mode, launch_method=method)

            else:
                # BAT режим
                from config.reg import get_last_bat_strategy
                last_strategy = get_last_bat_strategy()

                if last_strategy and last_strategy != "Автостарт DPI отключен":
                    log(f"🚀 Автозапуск Zapret 1 (BAT): {last_strategy}", "INFO")
                    self.dpi_controller.start_dpi_async(selected_mode=last_strategy, launch_method="bat")
                    
                    # Обновляем GUI
                    if hasattr(self, 'current_strategy_name'):
                        self.current_strategy_name = last_strategy
                    
                    # Обновляем отображение на странице BAT стратегий
                    if hasattr(self, 'bat_strategies_page') and hasattr(self.bat_strategies_page, 'current_strategy_label'):
                        self.bat_strategies_page.current_strategy_label.setText(f"🎯 {last_strategy}")
                else:
                    log("⏸️ BAT режим: нет сохранённой стратегии для автозапуска", "INFO")
                    if hasattr(self, 'bat_strategies_page'):
                        if hasattr(self.bat_strategies_page, 'show_success'):
                            self.bat_strategies_page.show_success()
                        if hasattr(self.bat_strategies_page, 'current_strategy_label'):
                            self.bat_strategies_page.current_strategy_label.setText("Не выбрана")

            # Запускаем мониторинг процесса на соответствующей странице
            # (каждая страница стратегий имеет свой мониторинг)

        except Exception as e:
            log(f"Ошибка автозапуска после переключения режима: {e}", "ERROR")
            import traceback
            log(traceback.format_exc(), "DEBUG")
        
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

        # Единая логика выхода (как в трее): остановить DPI и выйти.
        if hasattr(self, "request_exit"):
            self.request_exit(stop_dpi=True)
            return

        # Fallback для старой архитектуры
        if hasattr(self, 'dpi_controller') and self.dpi_controller:
            self._closing_completely = True
            self.dpi_controller.stop_and_exit_async()
        else:
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
        self.show_page(PageName.PREMIUM)
        self.side_nav.set_section_by_name(SectionName.PREMIUM, emit_signal=False)
        
    def _on_section_changed(self, page_name: PageName):
        """Обработчик смены раздела в навигации

        Args:
            page_name: PageName страницы которую нужно показать (может быть None для collapsible групп)
        """
        # Если page_name is None - это клик на collapsible группу (например, Strategies)
        # В этом случае определяем целевую страницу динамически
        if page_name is None:
            # Предполагаем что это клик на группу Strategies
            try:
                from strategy_menu import get_strategy_launch_method
                method = get_strategy_launch_method()

                # Определяем целевую страницу по методу запуска
                if method == "orchestra":
                    target_page = PageName.ORCHESTRA
                elif method == "direct_zapret2_orchestra":
                    target_page = PageName.ZAPRET2_ORCHESTRA
                elif method == "direct_zapret2":
                    # In direct_zapret2, Strategies section defaults to "Управление".
                    target_page = PageName.ZAPRET2_DIRECT_CONTROL
                elif method == "direct_zapret1":
                    target_page = PageName.ZAPRET1_DIRECT
                else:  # bat
                    target_page = PageName.BAT_STRATEGIES

                self.show_page(target_page)
                return
            except Exception:
                # Fallback на Zapret 2 Direct
                self.show_page(PageName.ZAPRET2_DIRECT)
                return

        # Для остальных страниц - просто переключаем
        self.show_page(page_name)
    
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
            
    def _get_direct_strategy_summary(self, max_items: int = 2) -> str:
        """Возвращает 'топ-N категорий + +M ещё' для direct_* режимов."""
        try:
            from strategy_menu import get_direct_strategy_selections
            from strategy_menu.strategies_registry import registry

            selections = get_direct_strategy_selections() or {}
            active_names: list[str] = []
            for cat_key in registry.get_all_category_keys_by_command_order():
                sid = selections.get(cat_key, "none") or "none"
                if sid == "none":
                    continue
                info = registry.get_category_info(cat_key)
                active_names.append(getattr(info, "full_name", None) or cat_key)

            if not active_names:
                return "Не выбрана"
            if len(active_names) <= max_items:
                return " • ".join(active_names)
            return " • ".join(active_names[:max_items]) + f" +{len(active_names) - max_items} ещё"
        except Exception:
            return "Прямой запуск"

    def update_current_strategy_display(self, strategy_name: str):
        """Обновляет отображение текущей стратегии"""
        launch_method = None
        try:
            from strategy_menu import get_strategy_launch_method
            launch_method = get_strategy_launch_method()
            if launch_method in ("direct_zapret2", "direct_zapret2_orchestra", "direct_zapret1"):
                strategy_name = self._get_direct_strategy_summary()
        except Exception:
            pass

        self.control_page.update_strategy(strategy_name)
        try:
            page = getattr(self, "zapret2_direct_control_page", None)
            if page and hasattr(page, "update_strategy"):
                page.update_strategy(strategy_name)
        except Exception:
            pass

        # Обновляем на активных страницах стратегий (если метод есть)
        for page_attr in (
            'zapret2_direct_control_page',
            'zapret2_strategies_page',
            'zapret2_orchestra_strategies_page',
            'zapret1_strategies_page',
            'bat_strategies_page',
        ):
            page = getattr(self, page_attr, None)
            if page and hasattr(page, 'update_current_strategy'):
                page.update_current_strategy(strategy_name)

        # Для главной страницы: в режиме оркестратора не показываем список доменов/стратегий.
        if launch_method in ("orchestra", "direct_zapret2_orchestra"):
            self.home_page.strategy_card.set_value("Режим оркестратор", "Автообучение")
            return

        # Обычный режим: обрезаем длинное название
        display_name = strategy_name if strategy_name != "Автостарт DPI отключен" else "Не выбрана"
        if hasattr(self.home_page, '_truncate_strategy_name'):
            display_name = self.home_page._truncate_strategy_name(display_name)
        self.home_page.strategy_card.set_value(display_name, "Активная стратегия")
        
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
        try:
            from strategy_menu import get_strategy_launch_method
            launch_method = get_strategy_launch_method()
        except Exception:
            launch_method = "bat"

        sender = None
        try:
            sender = self.sender()
        except Exception:
            sender = None

        # direct_zapret2: Zapret2StrategiesPageNew emits (category_key, strategy_id).
        # Do NOT treat it as a single global "strategy", otherwise UI shows a phantom name.
        if launch_method == "direct_zapret2" and sender is getattr(self, "zapret2_strategies_page", None):
            category_key = strategy_id
            category_strategy_id = strategy_name
            log(f"Direct Zapret2 selection: {category_key} = {category_strategy_id}", "DEBUG")

            display_name = self._get_direct_strategy_summary()

            self.update_current_strategy_display(display_name)
            if hasattr(self, "parent_app"):
                try:
                    self.parent_app.current_strategy_name = display_name
                except Exception:
                    pass
            return

        log(f"Стратегия выбрана из страницы: {strategy_id} - {strategy_name}", "INFO")

        # Обновляем отображение
        self.update_current_strategy_display(strategy_name)

        # Вызываем обработчик в главном приложении если есть
        if hasattr(self, 'parent_app') and hasattr(self.parent_app, 'on_strategy_selected_from_dialog'):
            self.parent_app.on_strategy_selected_from_dialog(strategy_id, strategy_name)

    def _on_open_category_detail(self, category_key: str, current_strategy_id: str):
        """Handler for opening category detail page from StrategiesPage"""
        from log import log
        from strategy_menu.strategies_registry import registry

        try:
            # Defensive: close any transient popups/tooltips before switching pages.
            try:
                self._dismiss_transient_ui(reason="open_category_detail")
            except Exception:
                pass

            # Get category info
            category_info = registry.get_category_info(category_key)
            if not category_info:
                log(f"Category not found: {category_key}", "ERROR")
                return

            # Show the detail page with category data
            if hasattr(self.strategy_detail_page, 'show_category'):
                self.strategy_detail_page.show_category(
                    category_key,
                    category_info,
                    current_strategy_id
                )

            # Navigate to detail page
            self.show_page(PageName.STRATEGY_DETAIL)

            # Remember last opened category (session-only) for easier restore.
            try:
                self._direct_zapret2_last_opened_category_key = category_key
                self._direct_zapret2_restore_detail_on_open = True
            except Exception:
                pass

            log(f"Opened category detail: {category_key}", "DEBUG")

        except Exception as e:
            log(f"Error opening category detail: {e}", "ERROR")

    def _on_strategy_detail_back(self):
        """Handler for back button click in StrategyDetailPage"""
        from strategy_menu import get_strategy_launch_method

        # Navigate back to the appropriate strategies page
        method = get_strategy_launch_method()

        if method == "direct_zapret2_orchestra":
            self.show_page(PageName.ZAPRET2_ORCHESTRA)
        elif method == "direct_zapret2":
            self.show_page(PageName.ZAPRET2_DIRECT)
        elif method == "direct_zapret1":
            self.show_page(PageName.ZAPRET1_DIRECT)
        else:
            self.show_page(PageName.BAT_STRATEGIES)

    def _on_strategy_detail_selected(self, category_key: str, strategy_id: str):
        """Handler for strategy selection in StrategyDetailPage.
        Note: Uses (category_key, strategy_id) unlike _on_strategy_selected_from_page.
        """
        from log import log

        log(f"Strategy selected from detail: {category_key} = {strategy_id}", "INFO")

        # Update the parent StrategiesPage to reflect the selection
        if hasattr(self, 'zapret2_strategies_page') and hasattr(self.zapret2_strategies_page, 'apply_strategy_selection'):
            self.zapret2_strategies_page.apply_strategy_selection(category_key, strategy_id)

    def _on_strategy_detail_filter_mode_changed(self, category_key: str, filter_mode: str):
        """Keep main strategies page in sync with Hostlist/IPset toggle."""
        try:
            if hasattr(self, 'zapret2_strategies_page') and hasattr(self.zapret2_strategies_page, 'apply_filter_mode_change'):
                self.zapret2_strategies_page.apply_filter_mode_change(category_key, filter_mode)
        except Exception as e:
            from log import log
            log(f"Ошибка обновления filter_mode из StrategyDetailPage: {e}", "DEBUG")

    def init_autostart_page(self, app_instance, bat_folder: str, json_folder: str, strategy_name: str = None):
        """Инициализирует страницу автозапуска с необходимыми параметрами"""
        self.autostart_page.set_app_instance(app_instance)
        self.autostart_page.set_folders(bat_folder, json_folder)
        if strategy_name:
            self.autostart_page.set_strategy_name(strategy_name)
    
    def show_autostart_page(self):
        """Переключается на страницу автозапуска"""
        self.show_page(PageName.AUTOSTART)
        self.side_nav.set_section_by_name(SectionName.AUTOSTART, emit_signal=False)

    def show_hosts_page(self):
        """Переключается на страницу Hosts"""
        self.show_page(PageName.HOSTS)
        self.side_nav.set_section_by_name(SectionName.HOSTS, emit_signal=False)

    def show_servers_page(self):
        """Переключается на страницу серверов обновлений"""
        self.show_page(PageName.SERVERS)
        self.side_nav.set_section_by_name(SectionName.SERVERS, emit_signal=False)

    def _navigate_to_control(self):
        """Переключается на страницу управления"""
        try:
            from strategy_menu import get_strategy_launch_method
            if get_strategy_launch_method() == "direct_zapret2":
                # In direct_zapret2, "Управление" is a subtab of Strategies.
                self.show_page(PageName.ZAPRET2_DIRECT_CONTROL)
                self.side_nav.set_section_by_name(SectionName.STRATEGIES, emit_signal=False)
                return
        except Exception:
            pass

        self.show_page(PageName.CONTROL)
        self.side_nav.set_section_by_name(SectionName.CONTROL, emit_signal=False)

    def _navigate_to_strategies(self):
        """Переключается на страницу стратегий с учётом метода запуска"""
        from log import log

        try:
            from strategy_menu import get_strategy_launch_method
            method = get_strategy_launch_method()

            if method == "orchestra":
                target_page = PageName.ORCHESTRA
            elif method == "direct_zapret2_orchestra":
                target_page = PageName.ZAPRET2_ORCHESTRA  # Оркестратор Zapret 2 - отдельная страница
            elif method == "direct_zapret2":
                # Restore last opened category detail (session memory) to avoid losing context.
                last_key = None
                want_restore = False
                try:
                    last_key = getattr(self, "_direct_zapret2_last_opened_category_key", None)
                    want_restore = bool(getattr(self, "_direct_zapret2_restore_detail_on_open", False))
                except Exception:
                    last_key = None
                    want_restore = False

                if want_restore and last_key:
                    try:
                        from strategy_menu.strategies_registry import registry
                        category_info = registry.get_category_info(last_key)
                        if category_info and hasattr(self, "strategy_detail_page") and hasattr(self.strategy_detail_page, "show_category"):
                            # Get current selection from preset (source of truth).
                            try:
                                from preset_zapret2 import PresetManager
                                preset_manager = PresetManager()
                                selections = preset_manager.get_strategy_selections() or {}
                                current_strategy_id = selections.get(last_key, "none")
                            except Exception:
                                current_strategy_id = "none"

                            self.strategy_detail_page.show_category(last_key, category_info, current_strategy_id)
                            target_page = PageName.STRATEGY_DETAIL
                        else:
                            target_page = PageName.ZAPRET2_DIRECT_CONTROL
                    except Exception:
                        target_page = PageName.ZAPRET2_DIRECT_CONTROL
                else:
                    # Default landing for Strategies in direct_zapret2.
                    target_page = PageName.ZAPRET2_DIRECT_CONTROL
            elif method == "direct_zapret1":
                target_page = PageName.ZAPRET1_DIRECT
            else:  # bat
                target_page = PageName.BAT_STRATEGIES

            self.show_page(target_page)
        except Exception as e:
            log(f"Ошибка определения метода запуска стратегий: {e}", "ERROR")
            # Fallback на Zapret 2 Direct как самый распространённый
            self.show_page(PageName.ZAPRET2_DIRECT)

        # Highlight the section without re-triggering navigation (important when restoring STRATEGY_DETAIL).
        self.side_nav.set_section_by_name(SectionName.STRATEGIES, emit_signal=False)

    def _navigate_to_dpi_settings(self):
        """Переключается на страницу настроек DPI"""
        from log import log
        log("_navigate_to_dpi_settings called!", "DEBUG")
        # Используем новый API навигации
        self.show_page(PageName.DPI_SETTINGS)
        self.side_nav.set_section_by_name(SectionName.DPI_SETTINGS, emit_signal=False)
        log("Navigated to DPI settings page", "DEBUG")
