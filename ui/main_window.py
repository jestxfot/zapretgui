# ui/main_window.py
"""
Главное окно приложения в стиле Windows 11 Settings
"""
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget
)
from importlib import import_module

from ui.sidebar import SideNavBar
from ui.custom_titlebar import DraggableWidget
from config import MIN_WIDTH
from ui.page_names import PageName, SectionName


_PAGE_CLASS_SPECS: dict[PageName, tuple[str, str, str]] = {
    PageName.HOME: ("home_page", "ui.pages.home_page", "HomePage"),
    PageName.CONTROL: ("control_page", "ui.pages.control_page", "ControlPage"),
    PageName.ZAPRET2_DIRECT_CONTROL: (
        "zapret2_direct_control_page",
        "ui.pages.zapret2.direct_control_page",
        "Zapret2DirectControlPage",
    ),
    PageName.ZAPRET2_DIRECT: (
        "zapret2_strategies_page",
        "ui.pages.zapret2.direct_zapret2_page",
        "Zapret2StrategiesPageNew",
    ),
    PageName.STRATEGY_DETAIL: (
        "strategy_detail_page",
        "ui.pages.zapret2.strategy_detail_page",
        "StrategyDetailPage",
    ),
    PageName.ZAPRET2_ORCHESTRA: (
        "zapret2_orchestra_strategies_page",
        "ui.pages.zapret2_orchestra_strategies_page",
        "Zapret2OrchestraStrategiesPage",
    ),
    PageName.ZAPRET1_DIRECT: (
        "zapret1_strategies_page",
        "ui.pages.zapret1_direct_strategies_page",
        "Zapret1DirectStrategiesPage",
    ),
    PageName.BAT_STRATEGIES: ("bat_strategies_page", "ui.pages.bat_strategies_page", "BatStrategiesPage"),
    PageName.STRATEGY_SORT: ("strategy_sort_page", "ui.pages.strategy_sort_page", "StrategySortPage"),
    PageName.PRESET_CONFIG: ("preset_config_page", "ui.pages.preset_config_page", "PresetConfigPage"),
    PageName.MY_CATEGORIES: ("my_categories_page", "ui.pages.my_categories_page", "MyCategoriesPage"),
    PageName.HOSTLIST: ("hostlist_page", "ui.pages.hostlist_page", "HostlistPage"),
    PageName.BLOBS: ("blobs_page", "ui.pages.blobs_page", "BlobsPage"),
    PageName.EDITOR: ("editor_page", "ui.pages.editor_page", "EditorPage"),
    PageName.DPI_SETTINGS: ("dpi_settings_page", "ui.pages.dpi_settings_page", "DpiSettingsPage"),
    PageName.ZAPRET2_USER_PRESETS: (
        "zapret2_user_presets_page",
        "ui.pages.zapret2.user_presets_page",
        "Zapret2UserPresetsPage",
    ),
    PageName.NETROGAT: ("netrogat_page", "ui.pages.netrogat_page", "NetrogatPage"),
    PageName.CUSTOM_DOMAINS: ("custom_domains_page", "ui.pages.custom_domains_page", "CustomDomainsPage"),
    PageName.CUSTOM_IPSET: ("custom_ipset_page", "ui.pages.custom_ipset_page", "CustomIpSetPage"),
    PageName.AUTOSTART: ("autostart_page", "ui.pages.autostart_page", "AutostartPage"),
    PageName.NETWORK: ("network_page", "ui.pages.network_page", "NetworkPage"),
    PageName.CONNECTION_TEST: ("connection_page", "ui.pages.connection_page", "ConnectionTestPage"),
    PageName.DNS_CHECK: ("dns_check_page", "ui.pages.dns_check_page", "DNSCheckPage"),
    PageName.HOSTS: ("hosts_page", "ui.pages.hosts_page", "HostsPage"),
    PageName.BLOCKCHECK: ("blockcheck_page", "ui.pages.blockcheck_page", "BlockcheckPage"),
    PageName.APPEARANCE: ("appearance_page", "ui.pages.appearance_page", "AppearancePage"),
    PageName.PREMIUM: ("premium_page", "ui.pages.premium_page", "PremiumPage"),
    PageName.LOGS: ("logs_page", "ui.pages.logs_page", "LogsPage"),
    PageName.SERVERS: ("servers_page", "ui.pages.servers_page", "ServersPage"),
    PageName.ABOUT: ("about_page", "ui.pages.about_page", "AboutPage"),
    PageName.SUPPORT: ("support_page", "ui.pages.support_page", "SupportPage"),
    PageName.HELP: ("help_page", "ui.pages.help_page", "HelpPage"),
    PageName.ORCHESTRA: ("orchestra_page", "ui.pages.orchestra_page", "OrchestraPage"),
    PageName.ORCHESTRA_LOCKED: (
        "orchestra_locked_page",
        "ui.pages.orchestra_locked_page",
        "OrchestraLockedPage",
    ),
    PageName.ORCHESTRA_BLOCKED: (
        "orchestra_blocked_page",
        "ui.pages.orchestra_blocked_page",
        "OrchestraBlockedPage",
    ),
    PageName.ORCHESTRA_WHITELIST: (
        "orchestra_whitelist_page",
        "ui.pages.orchestra_whitelist_page",
        "OrchestraWhitelistPage",
    ),
    PageName.ORCHESTRA_RATINGS: (
        "orchestra_ratings_page",
        "ui.pages.orchestra_ratings_page",
        "OrchestraRatingsPage",
    ),
}

_PAGE_ALIASES: dict[PageName, PageName] = {
    PageName.IPSET: PageName.HOSTLIST,
    PageName.PRESETS: PageName.ZAPRET2_USER_PRESETS,
}

_EAGER_PAGE_NAMES: tuple[PageName, ...] = (
    # Критичные для первого кадра + сигналов InitializationManager.
    PageName.HOME,
    PageName.CONTROL,
    PageName.ZAPRET2_DIRECT_CONTROL,
    PageName.AUTOSTART,
    PageName.DPI_SETTINGS,
    PageName.PRESET_CONFIG,
    PageName.APPEARANCE,
    PageName.ABOUT,
    PageName.PREMIUM,
)

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
        self._page_signal_bootstrap_complete = False
        self._create_pages()

        content_layout.addWidget(self.pages_stack)
        root.addWidget(content_area, 1)  # stretch=1 для растягивания
        
        # ────────────────────────────────────────────────────────────
        # СОВМЕСТИМОСТЬ СО СТАРЫМ КОДОМ
        # ────────────────────────────────────────────────────────────
        self._setup_compatibility_attrs()
        
        # Подключаем сигналы
        self._connect_page_signals()
        self._page_signal_bootstrap_complete = True

        # Session memory: remember last opened direct_zapret2 category detail page.
        # (Used to restore context when re-opening the Strategies section.)
        if not hasattr(self, "_direct_zapret2_last_opened_category_key"):
            self._direct_zapret2_last_opened_category_key = None  # type: ignore[attr-defined]
        if not hasattr(self, "_direct_zapret2_restore_detail_on_open"):
            self._direct_zapret2_restore_detail_on_open = False  # type: ignore[attr-defined]
        
    def _create_pages(self):
        """Создает реестр страниц и инициализирует только критичные страницы."""
        import time as _time
        from log import log

        _t_pages_total = _time.perf_counter()

        self.pages: dict[PageName, QWidget] = {}
        self._page_aliases: dict[PageName, PageName] = dict(_PAGE_ALIASES)
        self._lazy_signal_connections: set[str] = set()

        for page_name in _EAGER_PAGE_NAMES:
            self._ensure_page(page_name)

        log(
            f"⏱ Startup: _create_pages core {( _time.perf_counter() - _t_pages_total ) * 1000:.0f}ms",
            "DEBUG",
        )

    def _resolve_page_name(self, name: PageName) -> PageName:
        return self._page_aliases.get(name, name)

    def _connect_signal_once(self, key: str, signal_obj, slot_obj) -> None:
        if key in self._lazy_signal_connections:
            return
        try:
            signal_obj.connect(slot_obj)
            self._lazy_signal_connections.add(key)
        except Exception:
            pass

    def _connect_strategy_sort_signal_bridges(self) -> None:
        sort_page = getattr(self, "strategy_sort_page", None)
        strategies_page = getattr(self, "zapret2_strategies_page", None)
        if sort_page is None or strategies_page is None:
            return

        if hasattr(strategies_page, "on_external_filters_changed") and hasattr(sort_page, "filters_changed"):
            self._connect_signal_once(
                "strategy_sort.filters_changed",
                sort_page.filters_changed,
                strategies_page.on_external_filters_changed,
            )

        if hasattr(strategies_page, "on_external_sort_changed") and hasattr(sort_page, "sort_changed"):
            self._connect_signal_once(
                "strategy_sort.sort_changed",
                sort_page.sort_changed,
                strategies_page.on_external_sort_changed,
            )

    def _connect_lazy_page_signals(self, page_name: PageName, page: QWidget) -> None:
        if page_name in (
            PageName.ZAPRET1_DIRECT,
            PageName.ZAPRET2_DIRECT,
            PageName.ZAPRET2_ORCHESTRA,
            PageName.BAT_STRATEGIES,
        ):
            if hasattr(page, "strategy_selected"):
                self._connect_signal_once(
                    f"strategy_selected.{page_name.name}",
                    page.strategy_selected,
                    self._on_strategy_selected_from_page,
                )

        if page_name == PageName.ZAPRET2_DIRECT and hasattr(page, "open_category_detail"):
            self._connect_signal_once(
                "z2_direct.open_category_detail",
                page.open_category_detail,
                self._on_open_category_detail,
            )

        if page_name == PageName.STRATEGY_DETAIL:
            if hasattr(page, "back_clicked"):
                self._connect_signal_once(
                    "strategy_detail.back_clicked",
                    page.back_clicked,
                    self._on_strategy_detail_back,
                )
            if hasattr(page, "strategy_selected"):
                self._connect_signal_once(
                    "strategy_detail.strategy_selected",
                    page.strategy_selected,
                    self._on_strategy_detail_selected,
                )
            if hasattr(page, "filter_mode_changed"):
                self._connect_signal_once(
                    "strategy_detail.filter_mode_changed",
                    page.filter_mode_changed,
                    self._on_strategy_detail_filter_mode_changed,
                )

        if page_name == PageName.ORCHESTRA and hasattr(page, "clear_learned_requested"):
            self._connect_signal_once(
                "orchestra.clear_learned_requested",
                page.clear_learned_requested,
                self._on_clear_learned_requested,
            )

        self._connect_strategy_sort_signal_bridges()

    def _ensure_page(self, name: PageName) -> QWidget | None:
        resolved_name = self._resolve_page_name(name)
        page = self.pages.get(resolved_name)
        if page is not None:
            return page

        spec = _PAGE_CLASS_SPECS.get(resolved_name)
        if spec is None:
            return None

        attr_name, module_name, class_name = spec
        try:
            module = import_module(module_name)
            page_cls = getattr(module, class_name)
            page = page_cls(self)
        except Exception as e:
            from log import log
            log(f"Ошибка lazy-инициализации страницы {resolved_name}: {e}", "ERROR")
            return None

        self.pages_stack.addWidget(page)
        self.pages[resolved_name] = page
        setattr(self, attr_name, page)

        # Legacy alias: keep old references to ipset_page valid.
        if resolved_name == PageName.HOSTLIST:
            self.ipset_page = page

        if bool(getattr(self, "_page_signal_bootstrap_complete", False)):
            self._connect_lazy_page_signals(resolved_name, page)

        return page

    def get_page(self, name: PageName) -> QWidget:
        """Возвращает виджет страницы по имени"""
        return self._ensure_page(name)

    def show_page(self, name: PageName) -> bool:
        """Переключает на указанную страницу. Возвращает True при успехе."""
        page = self._ensure_page(name)
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

        # Связываем сортировку и страницу стратегий, если обе уже созданы.
        self._connect_strategy_sort_signal_bridges()

        # Presets: subscribe to central PresetStore for all preset events.
        # This replaces per-page signal connections — all preset switches
        # (from any page/backend) trigger the same handler.
        try:
            from preset_zapret2.preset_store import get_preset_store
            store = get_preset_store()
            store.preset_switched.connect(self._on_preset_switched)
        except Exception:
            pass

        # Also watch the active preset file itself (preset-zapret2.txt).
        # This covers cases where the file changes WITHOUT a preset switch signal:
        # - editing strategies (rewrites preset-zapret2.txt)
        # - editing the active preset text in the GUI/notepad
        try:
            self._setup_active_preset_file_watcher()
        except Exception:
            pass

        # NOTE: zapret2_user_presets_page.preset_switched is no longer connected here.
        # The store.preset_switched signal above is the single source of truth;
        # the page signal was causing double DPI restarts.

    def _setup_active_preset_file_watcher(self) -> None:
        """Watches preset-zapret2.txt and refreshes dependent pages on change."""
        try:
            import os
            from PyQt6.QtCore import QFileSystemWatcher, QTimer
            from preset_zapret2 import get_active_preset_path

            watched_path = os.fspath(get_active_preset_path())
            if not watched_path:
                return

            watcher = getattr(self, "_active_preset_file_watcher", None)
            if watcher is None:
                watcher = QFileSystemWatcher(self)
                watcher.fileChanged.connect(self._on_active_preset_file_changed)
                self._active_preset_file_watcher = watcher

            timer = getattr(self, "_active_preset_file_refresh_timer", None)
            if timer is None:
                timer = QTimer(self)
                timer.setSingleShot(True)
                timer.timeout.connect(self._schedule_refresh_after_preset_switch)
                self._active_preset_file_refresh_timer = timer

            # Keep the canonical path so we can re-arm after atomic replaces.
            self._active_preset_file_path = watched_path

            # Ensure exactly this path is being watched.
            try:
                current = set(watcher.files() or [])
                desired = {watched_path}
                for p in (current - desired):
                    watcher.removePath(p)
                for p in (desired - current):
                    watcher.addPath(p)
            except Exception:
                try:
                    if watched_path not in (watcher.files() or []):
                        watcher.addPath(watched_path)
                except Exception:
                    pass
        except Exception:
            # Never break UI init due to watcher failures.
            return

    def _on_active_preset_file_changed(self, path: str) -> None:
        """Debounced handler for active preset file changes."""
        # QFileSystemWatcher can drop a file from watch list when it is replaced
        # atomically (temp file + os.replace). Re-add the path on every event.
        try:
            watcher = getattr(self, "_active_preset_file_watcher", None)
            desired = getattr(self, "_active_preset_file_path", None)
            if watcher is not None:
                rearm = (desired or path)
                if rearm and rearm not in (watcher.files() or []):
                    watcher.addPath(rearm)
        except Exception:
            pass

        try:
            timer = getattr(self, "_active_preset_file_refresh_timer", None)
            if timer is not None:
                # Debounce rapid writes (strategy editor / text editor saves).
                timer.start(200)
            else:
                self._schedule_refresh_after_preset_switch()
        except Exception:
            try:
                self._schedule_refresh_after_preset_switch()
            except Exception:
                pass

    def _on_preset_switched(self, preset_name: str):
        """Обработчик переключения пресета - перезапускает DPI если запущен"""
        from log import log
        log(f"Пресет переключен: {preset_name}", "INFO")

        # Direct Zapret2: preset switch updates preset-zapret2.txt.
        # StrategyRunnerV2 has hot-reload and will restart winws2.exe on file change.
        # Explicit restarts here cause races (double stop/start) and flaky "winws is running" detection
        # when user переключает пресеты быстро.
        try:
            from strategy_menu import get_strategy_launch_method

            method = (get_strategy_launch_method() or "").strip().lower()
        except Exception:
            method = ""

        if method in ("direct_zapret2", "direct_zapret2_orchestra"):
            # Best-effort: let unified reload handler stop DPI if preset has no active filters.
            try:
                from dpi.zapret2_core_restart import trigger_dpi_reload

                trigger_dpi_reload(self, reason="preset_switched")
            except Exception:
                pass
        else:
            # Other modes: restart, but debounce to avoid restart spam on rapid switching.
            self._schedule_dpi_restart_after_preset_switch()

        # Асинхронно обновляем UI страниц, завязанных на preset-zapret2.txt
        self._schedule_refresh_after_preset_switch()

    def _schedule_dpi_restart_after_preset_switch(self, delay_ms: int = 350) -> None:
        """Debounced DPI restart used for non-direct_zapret2 modes."""
        try:
            if not hasattr(self, 'dpi_controller') or not self.dpi_controller:
                return
            if not self.dpi_controller.is_running():
                return

            from PyQt6.QtCore import QTimer

            timer = getattr(self, "_preset_switch_restart_timer", None)
            if timer is None:
                timer = QTimer(self)
                timer.setSingleShot(True)
                timer.timeout.connect(self._restart_dpi_after_preset_switch)
                self._preset_switch_restart_timer = timer

            timer.start(max(0, int(delay_ms)))
        except Exception:
            # Never break preset switching due to restart scheduling errors.
            return

    def _restart_dpi_after_preset_switch(self) -> None:
        """Performs the actual restart after debounce timer."""
        from log import log

        try:
            if not hasattr(self, 'dpi_controller') or not self.dpi_controller:
                return
            if not self.dpi_controller.is_running():
                return

            log("DPI запущен - выполняем перезапуск после смены пресета (debounce)", "INFO")
            self.dpi_controller.restart_dpi_async()
        except Exception as e:
            log(f"Ошибка перезапуска DPI после смены пресета: {e}", "DEBUG")

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
        can_autostart = True
        if method == "direct_zapret2":
            from preset_zapret2 import ensure_default_preset_exists
            if not ensure_default_preset_exists():
                log(
                    "direct_zapret2: preset-zapret2.txt не создан (нет built-in шаблона Default). "
                    "Проверьте: %APPDATA%/zapret/presets/_builtin/Default.txt",
                    "ERROR",
                )
                try:
                    self.set_status("Ошибка: отсутствует Default.txt (built-in пресет)")
                except Exception:
                    pass
                can_autostart = False
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
        if can_autostart:
            QTimer.singleShot(500, lambda: self._auto_start_after_method_switch(method))
        else:
            log("Автозапуск DPI пропущен: не удалось подготовить preset-zapret2.txt", "WARNING")

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
            "zapret2_user_presets_page",
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

        # Для главной страницы всегда показываем именно метод запуска.
        if hasattr(self.home_page, "update_launch_method_card"):
            self.home_page.update_launch_method_card()
        
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
            # Get category info
            category_info = registry.get_category_info(category_key)
            if not category_info:
                log(f"Category not found: {category_key}", "ERROR")
                return

            # Show the detail page with category data
            detail_page = self._ensure_page(PageName.STRATEGY_DETAIL)
            if detail_page and hasattr(detail_page, 'show_category'):
                detail_page.show_category(
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
                        detail_page = self._ensure_page(PageName.STRATEGY_DETAIL)
                        if category_info and detail_page and hasattr(detail_page, "show_category"):
                            # Get current selection from preset (source of truth).
                            try:
                                from preset_zapret2 import PresetManager
                                preset_manager = PresetManager()
                                selections = preset_manager.get_strategy_selections() or {}
                                current_strategy_id = selections.get(last_key, "none")
                            except Exception:
                                current_strategy_id = "none"

                            detail_page.show_category(last_key, category_info, current_strategy_id)
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
