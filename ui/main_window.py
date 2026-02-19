# ui/main_window.py
"""
Главное окно приложения — навигация через qfluentwidgets FluentWindow.

Все страницы добавляются через addSubInterface() вместо ручного SideNavBar + QStackedWidget.
Бизнес-логика (сигналы, обработчики) сохранена без изменений.
"""
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QWidget
from importlib import import_module


try:
    from qfluentwidgets import (
        NavigationItemPosition, FluentIcon,
    )
    HAS_FLUENT = True
except ImportError:
    HAS_FLUENT = False

from ui.page_names import PageName, SectionName

# ---------------------------------------------------------------------------
# Page class specs — UNCHANGED from original
# ---------------------------------------------------------------------------

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
    PageName.ZAPRET1_DIRECT_CONTROL: (
        "zapret1_direct_control_page",
        "ui.pages.zapret1.direct_control_page",
        "Zapret1DirectControlPage",
    ),
    PageName.ZAPRET1_DIRECT: (
        "zapret1_strategies_page",
        "ui.pages.zapret1.direct_zapret1_page",
        "Zapret1StrategiesPage",
    ),
    PageName.ZAPRET1_USER_PRESETS: (
        "zapret1_user_presets_page",
        "ui.pages.zapret1.user_presets_page",
        "Zapret1UserPresetsPage",
    ),
    PageName.ZAPRET1_STRATEGY_DETAIL: (
        "zapret1_strategy_detail_page",
        "ui.pages.zapret1.strategy_detail_page_v1",
        "Zapret1StrategyDetailPage",
    ),
    PageName.PRESET_CONFIG: ("preset_config_page", "ui.pages.preset_config_page", "PresetConfigPage"),
    PageName.HOSTLIST: ("hostlist_page", "ui.pages.hostlist_page", "HostlistPage"),
    PageName.BLOBS: ("blobs_page", "ui.pages.blobs_page", "BlobsPage"),
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
    PageName.HOSTS: ("hosts_page", "ui.pages.hosts_page", "HostsPage"),
    PageName.BLOCKCHECK: ("blockcheck_page", "ui.pages.blockcheck_page", "BlockcheckPage"),
    PageName.DIAGNOSTICS_TAB: ("diagnostics_tab_page", "ui.pages.diagnostics_tab_page", "DiagnosticsTabPage"),
    PageName.APPEARANCE: ("appearance_page", "ui.pages.appearance_page", "AppearancePage"),
    PageName.PREMIUM: ("premium_page", "ui.pages.premium_page", "PremiumPage"),
    PageName.LOGS: ("logs_page", "ui.pages.logs_page", "LogsPage"),
    PageName.SERVERS: ("servers_page", "ui.pages.servers_page", "ServersPage"),
    PageName.ABOUT: ("about_page", "ui.pages.about_page", "AboutPage"),
    PageName.SUPPORT: ("support_page", "ui.pages.support_page", "SupportPage"),
    PageName.HELP: ("help_page", "ui.pages.help_page", "HelpPage"),
    PageName.ORCHESTRA: ("orchestra_page", "ui.pages.orchestra_page", "OrchestraPage"),
    PageName.ORCHESTRA_SETTINGS: (
        "orchestra_settings_page",
        "ui.pages.orchestra",
        "OrchestraSettingsPage",
    ),
}

_PAGE_ALIASES: dict[PageName, PageName] = {
    PageName.IPSET: PageName.HOSTLIST,
    PageName.PRESETS: PageName.ZAPRET2_USER_PRESETS,
}

_EAGER_PAGE_NAMES: tuple[PageName, ...] = (
    PageName.HOME,
    PageName.CONTROL,
    PageName.ZAPRET2_DIRECT_CONTROL,
    PageName.ZAPRET1_DIRECT_CONTROL,
    PageName.AUTOSTART,
    PageName.DPI_SETTINGS,
    PageName.PRESET_CONFIG,
    PageName.APPEARANCE,
    PageName.ABOUT,
    PageName.PREMIUM,
)


# ---------------------------------------------------------------------------
# Navigation icon mapping (SectionName/PageName -> FluentIcon)
# ---------------------------------------------------------------------------
_NAV_ICONS = {
    PageName.HOME: FluentIcon.HOME if HAS_FLUENT else None,
    PageName.CONTROL: FluentIcon.COMMAND_PROMPT if HAS_FLUENT else None,
    PageName.ZAPRET2_DIRECT_CONTROL: FluentIcon.GAME if HAS_FLUENT else None,
    PageName.AUTOSTART: FluentIcon.POWER_BUTTON if HAS_FLUENT else None,
    PageName.NETWORK: FluentIcon.WIFI if HAS_FLUENT else None,
    PageName.DIAGNOSTICS_TAB: FluentIcon.SPEED_HIGH if HAS_FLUENT else None,
    PageName.CONNECTION_TEST: FluentIcon.SPEED_HIGH if HAS_FLUENT else None,
    PageName.DNS_CHECK: FluentIcon.SEARCH if HAS_FLUENT else None,
    PageName.HOSTS: FluentIcon.GLOBE if HAS_FLUENT else None,
    PageName.BLOCKCHECK: FluentIcon.CODE if HAS_FLUENT else None,
    PageName.APPEARANCE: FluentIcon.PALETTE if HAS_FLUENT else None,
    PageName.PREMIUM: FluentIcon.HEART if HAS_FLUENT else None,
    PageName.LOGS: FluentIcon.HISTORY if HAS_FLUENT else None,
    PageName.ABOUT: FluentIcon.INFO if HAS_FLUENT else None,
    PageName.DPI_SETTINGS: FluentIcon.SETTING if HAS_FLUENT else None,
    PageName.PRESET_CONFIG: FluentIcon.EDIT if HAS_FLUENT else None,
    PageName.HOSTLIST: FluentIcon.BOOK_SHELF if HAS_FLUENT else None,
    PageName.BLOBS: FluentIcon.CLOUD if HAS_FLUENT else None,
    PageName.NETROGAT: FluentIcon.REMOVE_FROM if HAS_FLUENT else None,
    PageName.CUSTOM_DOMAINS: FluentIcon.ADD if HAS_FLUENT else None,
    PageName.CUSTOM_IPSET: FluentIcon.ADD if HAS_FLUENT else None,
    PageName.ZAPRET2_USER_PRESETS: FluentIcon.FOLDER if HAS_FLUENT else None,
    PageName.SERVERS: FluentIcon.UPDATE if HAS_FLUENT else None,
    PageName.SUPPORT: FluentIcon.CHAT if HAS_FLUENT else None,
    PageName.HELP: FluentIcon.HELP if HAS_FLUENT else None,
    PageName.ORCHESTRA: FluentIcon.MUSIC if HAS_FLUENT else None,
    PageName.ORCHESTRA_SETTINGS: FluentIcon.SETTING if HAS_FLUENT else None,
    PageName.ZAPRET2_DIRECT: FluentIcon.PLAY if HAS_FLUENT else None,
    PageName.ZAPRET2_ORCHESTRA: FluentIcon.ROBOT if HAS_FLUENT else None,
    PageName.ZAPRET1_DIRECT_CONTROL: FluentIcon.GAME if HAS_FLUENT else None,
    PageName.ZAPRET1_DIRECT: FluentIcon.PLAY if HAS_FLUENT else None,
    PageName.ZAPRET1_USER_PRESETS: FluentIcon.FOLDER if HAS_FLUENT else None,
}

# Russian labels for navigation
_NAV_LABELS = {
    PageName.HOME: "Главная",
    PageName.CONTROL: "Управление",
    PageName.ZAPRET2_DIRECT_CONTROL: "Управление Zapret 2",
    PageName.AUTOSTART: "Автозапуск",
    PageName.NETWORK: "Сеть",
    PageName.DIAGNOSTICS_TAB: "Диагностика",
    PageName.CONNECTION_TEST: "Диагностика",
    PageName.DNS_CHECK: "DNS подмена",
    PageName.HOSTS: "Редактор файла hosts",
    PageName.BLOCKCHECK: "BlockCheck",
    PageName.APPEARANCE: "Оформление",
    PageName.PREMIUM: "Донат",
    PageName.LOGS: "Логи",
    PageName.ABOUT: "О программе",
    PageName.DPI_SETTINGS: "Сменить режим DPI",
    PageName.PRESET_CONFIG: "Конфиг пресета",
    PageName.HOSTLIST: "Листы",
    PageName.BLOBS: "Блобы",
    PageName.NETROGAT: "Исключения",
    PageName.CUSTOM_DOMAINS: "Мои hostlist",
    PageName.CUSTOM_IPSET: "Мои ipset",
    PageName.ZAPRET2_USER_PRESETS: "Мои пресеты",
    PageName.SERVERS: "Обновления",
    PageName.SUPPORT: "Поддержка",
    PageName.HELP: "Справка",
    PageName.ORCHESTRA: "Оркестратор",
    PageName.ORCHESTRA_SETTINGS: "Настройки оркестратора",
    PageName.ZAPRET2_DIRECT: "Прямой запуск",
    PageName.ZAPRET2_ORCHESTRA: "Стратегии",
    PageName.ZAPRET1_DIRECT_CONTROL: "Управление Zapret 1",
    PageName.ZAPRET1_DIRECT: "Стратегии Z1",
    PageName.ZAPRET1_USER_PRESETS: "Мои пресеты Z1",
}


class MainWindowUI:
    """
    Mixin: creates pages and registers them with FluentWindow navigation.
    """

    def build_ui(self, width: int, height: int):
        """Build UI: create pages and populate FluentWindow navigation sidebar.

        Note: window geometry (size/position) is restored in __init__ via
        restore_window_geometry() before this is called — do NOT resize here,
        that would overwrite the saved geometry.
        """
        self.pages: dict[PageName, QWidget] = {}
        self._page_aliases: dict[PageName, PageName] = dict(_PAGE_ALIASES)
        self._lazy_signal_connections: set[str] = set()

        self._page_signal_bootstrap_complete = False
        self._create_pages()

        # Register pages in navigation sidebar
        self._init_navigation()

        # Wire up signals
        self._connect_page_signals()
        self._page_signal_bootstrap_complete = True

        # Backward-compat attrs
        self._setup_compatibility_attrs()

        # Session memory
        if not hasattr(self, "_direct_zapret2_last_opened_category_key"):
            self._direct_zapret2_last_opened_category_key = None
        if not hasattr(self, "_direct_zapret2_restore_detail_on_open"):
            self._direct_zapret2_restore_detail_on_open = False

    # ------------------------------------------------------------------
    # Navigation setup (FluentWindow sidebar)
    # ------------------------------------------------------------------

    def _init_navigation(self):
        """Populate FluentWindow's NavigationInterface with pages.

        Flat layout — no tree hierarchy, no expand/collapse groups.
        All items are top-level; mode-specific items are simply hidden/shown
        via setVisible() in _sync_nav_visibility() with no parent-size hacks.
        """
        if not HAS_FLUENT:
            return

        POS_SCROLL = NavigationItemPosition.SCROLL

        self._nav_items: dict = {}

        def _add(page_name, position=POS_SCROLL):
            page = self._ensure_page(page_name)
            if page is None:
                return
            icon = _NAV_ICONS.get(page_name, FluentIcon.APPLICATION)
            text = _NAV_LABELS.get(page_name, page_name.name)
            if not page.objectName():
                page.setObjectName(page.__class__.__name__)
            item = self.addSubInterface(page, icon, text, position=position)
            if item is not None:
                self._nav_items[page_name] = item

        nav = self.navigationInterface  # shorthand

        # ── Верхние ──────────────────────────────────────────────────────────
        _add(PageName.HOME)
        _add(PageName.CONTROL)
        _add(PageName.ZAPRET2_DIRECT_CONTROL)
        _add(PageName.ZAPRET1_DIRECT_CONTROL) # только direct_zapret1

        # ── Точки входа в режим стратегий (одна видна за раз) ────────────────
        _add(PageName.ORCHESTRA)             # только orchestra
        _add(PageName.ZAPRET2_ORCHESTRA)     # только direct_zapret2_orchestra

        # ── Стратегии (под-раздел) ────────────────────────────────────────────
        nav.addItemHeader("Настройки Запрета", POS_SCROLL)
        _add(PageName.ZAPRET2_DIRECT)           # direct only
        _add(PageName.PRESET_CONFIG)            # zapret1 and zapret2 only
        _add(PageName.ZAPRET2_USER_PRESETS)     # zapret2 only
        _add(PageName.HOSTLIST)
        _add(PageName.ORCHESTRA_SETTINGS)       # orchestra only (tabbed: locked/blocked/whitelist/ratings)
        _add(PageName.DPI_SETTINGS)

        # BLOBS removed from nav — accessible via direct_control_page card

        # ── Система ───────────────────────────────────────────────────────────
        nav.addItemHeader("Система", POS_SCROLL)
        _add(PageName.AUTOSTART)
        _add(PageName.NETWORK)

        # ── Диагностика ───────────────────────────────────────────────────────
        nav.addItemHeader("Диагностика", POS_SCROLL)
        _add(PageName.DIAGNOSTICS_TAB)
        _add(PageName.HOSTS)
        _add(PageName.BLOCKCHECK)

        # ── Оформление / Донат / Логи ─────────────────────────────────────────
        nav.addItemHeader("Оформление", POS_SCROLL)
        _add(PageName.APPEARANCE)
        _add(PageName.PREMIUM)
        _add(PageName.LOGS)
        _add(PageName.ABOUT)

        # Pages NOT in navigation — reachable only via show_page() / switchTo()
        for hidden in (
            PageName.STRATEGY_DETAIL,
            PageName.BLOBS,
            PageName.ZAPRET1_DIRECT,
            PageName.ZAPRET1_USER_PRESETS,
            PageName.ZAPRET1_STRATEGY_DETAIL,
        ):
            page = self.pages.get(hidden)
            if page is not None:
                if not page.objectName():
                    page.setObjectName(page.__class__.__name__)
                self.stackedWidget.addWidget(page)

        self.navigationInterface.setMinimumExpandWidth(700)

        # Apply initial visibility immediately — flat items need no parent refresh.
        self._sync_nav_visibility()

    def _sync_nav_visibility(self, method: str | None = None) -> None:
        """Show/hide mode-specific navigation items.

        With a flat (non-tree) navigation layout this reduces to plain
        setVisible() calls — no parent fixed-size management needed.
        """
        if not getattr(self, '_nav_items', None):
            return

        if method is None:
            try:
                from strategy_menu import get_strategy_launch_method
                method = (get_strategy_launch_method() or "").strip().lower()
            except Exception:
                method = "direct_zapret2"
        if not method:
            method = "direct_zapret2"

        from ui.nav_mode_config import get_nav_visibility
        targets = get_nav_visibility(method)

        for page_name, should_show in targets.items():
            item = self._nav_items.get(page_name)
            if item is not None:
                item.setVisible(should_show)

    # ------------------------------------------------------------------
    # Page creation (lazy + eager) — UNCHANGED logic
    # ------------------------------------------------------------------

    def _create_pages(self):
        """Create page registry and initialize critical pages eagerly."""
        import time as _time
        from log import log

        _t_pages_total = _time.perf_counter()

        for page_name in _EAGER_PAGE_NAMES:
            self._ensure_page(page_name)

        log(
            f"⏱ Startup: _create_pages core {(_time.perf_counter() - _t_pages_total) * 1000:.0f}ms",
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

    def _connect_lazy_page_signals(self, page_name: PageName, page: QWidget) -> None:
        if page_name in (
            PageName.ZAPRET1_DIRECT,
            PageName.ZAPRET2_DIRECT,
            PageName.ZAPRET2_ORCHESTRA,
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

        if page_name in (PageName.ZAPRET2_DIRECT, PageName.ZAPRET2_USER_PRESETS, PageName.BLOBS) and hasattr(page, "back_clicked"):
            self._connect_signal_once(
                f"back_to_control.{page_name.name}",
                page.back_clicked,
                lambda: self.show_page(PageName.ZAPRET2_DIRECT_CONTROL),
            )

        if page_name in (PageName.ZAPRET1_DIRECT, PageName.ZAPRET1_USER_PRESETS) and hasattr(page, "back_clicked"):
            self._connect_signal_once(
                f"back_to_z1_control.{page_name.name}",
                page.back_clicked,
                lambda: self.show_page(PageName.ZAPRET1_DIRECT_CONTROL),
            )

        if page_name == PageName.ZAPRET1_DIRECT and hasattr(page, "category_clicked"):
            self._connect_signal_once(
                "z1_direct.category_clicked",
                page.category_clicked,
                self._open_zapret1_category_detail,
            )

        if page_name == PageName.ZAPRET1_STRATEGY_DETAIL:
            if hasattr(page, "back_clicked"):
                self._connect_signal_once(
                    "z1_strategy_detail.back_clicked",
                    page.back_clicked,
                    lambda: self.show_page(PageName.ZAPRET1_DIRECT),
                )
            if hasattr(page, "strategy_selected"):
                self._connect_signal_once(
                    "z1_strategy_detail.strategy_selected",
                    page.strategy_selected,
                    self._on_z1_strategy_detail_selected,
                )

        if page_name == PageName.ZAPRET1_DIRECT_CONTROL:
            if hasattr(page, "navigate_to_strategies"):
                self._connect_signal_once(
                    "z1_control.navigate_to_strategies",
                    page.navigate_to_strategies,
                    lambda: self.show_page(PageName.ZAPRET1_DIRECT),
                )
            if hasattr(page, "navigate_to_presets"):
                self._connect_signal_once(
                    "z1_control.navigate_to_presets",
                    page.navigate_to_presets,
                    lambda: self.show_page(PageName.ZAPRET1_USER_PRESETS),
                )

        if page_name == PageName.STRATEGY_DETAIL:
            if hasattr(page, "back_clicked"):
                self._connect_signal_once(
                    "strategy_detail.back_clicked",
                    page.back_clicked,
                    self._on_strategy_detail_back,
                )
            if hasattr(page, "navigate_to_root"):
                self._connect_signal_once(
                    "strategy_detail.navigate_to_root",
                    page.navigate_to_root,
                    lambda: self.show_page(PageName.ZAPRET2_DIRECT_CONTROL),
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

        # Ensure objectName for FluentWindow
        if not page.objectName():
            page.setObjectName(page.__class__.__name__)

        self.pages[resolved_name] = page
        setattr(self, attr_name, page)

        # Legacy alias
        if resolved_name == PageName.HOSTLIST:
            self.ipset_page = page

        if bool(getattr(self, "_page_signal_bootstrap_complete", False)):
            self._connect_lazy_page_signals(resolved_name, page)
            # For late-created pages, add to stacked widget
            if hasattr(self, 'stackedWidget'):
                self.stackedWidget.addWidget(page)

        return page

    def get_page(self, name: PageName) -> QWidget:
        return self._ensure_page(name)

    def show_page(self, name: PageName) -> bool:
        """Switch to the given page. Works with FluentWindow's switchTo()."""
        page = self._ensure_page(name)
        if page is None:
            return False
        try:
            self.switchTo(page)
        except Exception:
            # Fallback for pages not registered in nav
            if hasattr(self, 'stackedWidget'):
                self.stackedWidget.setCurrentWidget(page)
        return True

    # ------------------------------------------------------------------
    # Compatibility attributes
    # ------------------------------------------------------------------

    def _setup_compatibility_attrs(self):
        """Create attributes for backward-compatibility with old code."""
        self.start_btn = self.home_page.start_btn
        self.stop_btn = self.home_page.stop_btn

        if hasattr(self, "zapret2_direct_control_page") and hasattr(self.zapret2_direct_control_page, "strategy_label"):
            self.current_strategy_label = self.zapret2_direct_control_page.strategy_label
        elif hasattr(self.control_page, "strategy_label"):
            self.current_strategy_label = self.control_page.strategy_label

        self.test_connection_btn = self.home_page.test_btn
        self.open_folder_btn = self.home_page.folder_btn
        self.server_status_btn = self.about_page.update_btn
        self.subscription_btn = self.about_page.premium_btn

        # Expose diagnostics sub-pages for backward-compat (cleanup, focus etc.)
        if PageName.DIAGNOSTICS_TAB in self.pages:
            _diag = self.pages[PageName.DIAGNOSTICS_TAB]
            self.connection_page = _diag.connection_page
            self.dns_check_page  = _diag.dns_check_page
        if PageName.HOSTS in self.pages:
            self.hosts_page = self.pages[PageName.HOSTS]


    # ------------------------------------------------------------------
    # Signal connections — UNCHANGED from original
    # ------------------------------------------------------------------

    def _connect_page_signals(self):
        """Wire up signals from pages."""

        self.start_clicked = self.home_page.start_btn.clicked
        self.stop_clicked = self.home_page.stop_btn.clicked
        # theme_changed replaced by display_mode_changed (theme selection removed)
        if hasattr(self.appearance_page, 'display_mode_changed'):
            self.display_mode_changed = self.appearance_page.display_mode_changed
        elif hasattr(self.appearance_page, 'theme_changed'):
            self.display_mode_changed = self.appearance_page.theme_changed

        # Zapret 2 Direct signals
        if hasattr(self, 'zapret2_strategies_page') and hasattr(self.zapret2_strategies_page, 'strategy_selected'):
            self.zapret2_strategies_page.strategy_selected.connect(self._on_strategy_selected_from_page)

        if hasattr(self, 'zapret2_strategies_page') and hasattr(self.zapret2_strategies_page, 'open_category_detail'):
            self.zapret2_strategies_page.open_category_detail.connect(self._on_open_category_detail)

        if hasattr(self, 'strategy_detail_page'):
            if hasattr(self.strategy_detail_page, 'back_clicked'):
                self.strategy_detail_page.back_clicked.connect(self._on_strategy_detail_back)
            if hasattr(self.strategy_detail_page, 'navigate_to_root'):
                self.strategy_detail_page.navigate_to_root.connect(
                    lambda: self.show_page(PageName.ZAPRET2_DIRECT_CONTROL)
                )
            if hasattr(self.strategy_detail_page, 'strategy_selected'):
                self.strategy_detail_page.strategy_selected.connect(self._on_strategy_detail_selected)
            if hasattr(self.strategy_detail_page, 'filter_mode_changed'):
                self.strategy_detail_page.filter_mode_changed.connect(self._on_strategy_detail_filter_mode_changed)

        if hasattr(self, 'zapret2_orchestra_strategies_page') and hasattr(self.zapret2_orchestra_strategies_page, 'strategy_selected'):
            self.zapret2_orchestra_strategies_page.strategy_selected.connect(self._on_strategy_selected_from_page)

        self.autostart_page.autostart_enabled.connect(self._on_autostart_enabled)
        self.autostart_page.autostart_disabled.connect(self._on_autostart_disabled)
        self.autostart_page.navigate_to_dpi_settings.connect(self._navigate_to_dpi_settings)

        # Connect display mode change to autostart page theme refresh
        if hasattr(self.appearance_page, 'display_mode_changed'):
            self.appearance_page.display_mode_changed.connect(
                lambda _mode: self.autostart_page.on_theme_changed()
            )
        elif hasattr(self.appearance_page, 'theme_changed'):
            self.appearance_page.theme_changed.connect(self.autostart_page.on_theme_changed)

        # Connect background preset change
        if hasattr(self.appearance_page, 'background_preset_changed'):
            self.appearance_page.background_preset_changed.connect(self._on_background_preset_changed)

        self.control_page.start_btn.clicked.connect(self._proxy_start_click)
        self.control_page.stop_winws_btn.clicked.connect(self._proxy_stop_click)
        self.control_page.stop_and_exit_btn.clicked.connect(self._proxy_stop_and_exit)
        self.control_page.test_btn.clicked.connect(self._proxy_test_click)
        self.control_page.folder_btn.clicked.connect(self._proxy_folder_click)

        try:
            page = getattr(self, "zapret2_direct_control_page", None)
            if page is not None:
                page.start_btn.clicked.connect(self._proxy_start_click)
                page.stop_winws_btn.clicked.connect(self._proxy_stop_click)
                page.stop_and_exit_btn.clicked.connect(self._proxy_stop_and_exit)
                page.test_btn.clicked.connect(self._proxy_test_click)
                page.folder_btn.clicked.connect(self._proxy_folder_click)
                if hasattr(page, 'navigate_to_presets'):
                    page.navigate_to_presets.connect(
                        lambda: self.show_page(PageName.ZAPRET2_USER_PRESETS))
                if hasattr(page, 'navigate_to_direct_launch'):
                    page.navigate_to_direct_launch.connect(
                        lambda: self.show_page(PageName.ZAPRET2_DIRECT))
                if hasattr(page, 'navigate_to_blobs'):
                    page.navigate_to_blobs.connect(
                        lambda: self.show_page(PageName.BLOBS))
                if hasattr(page, 'direct_mode_changed'):
                    page.direct_mode_changed.connect(self._on_direct_mode_changed)
        except Exception:
            pass

        # Zapret 1 Direct Control page — start/stop buttons
        try:
            z1_page = getattr(self, "zapret1_direct_control_page", None)
            if z1_page is not None:
                if hasattr(z1_page, 'start_btn'):
                    z1_page.start_btn.clicked.connect(self._proxy_start_click)
                if hasattr(z1_page, 'stop_winws_btn'):
                    z1_page.stop_winws_btn.clicked.connect(self._proxy_stop_click)
                if hasattr(z1_page, 'stop_and_exit_btn'):
                    z1_page.stop_and_exit_btn.clicked.connect(self._proxy_stop_and_exit)
                if hasattr(z1_page, 'test_btn'):
                    z1_page.test_btn.clicked.connect(self._proxy_test_click)
                if hasattr(z1_page, 'folder_btn'):
                    z1_page.folder_btn.clicked.connect(self._proxy_folder_click)
        except Exception:
            pass

        # Back nav from subpages (Мои пресеты / Прямой запуск / Блобы → Управление)
        for _back_attr in ("zapret2_user_presets_page", "zapret2_strategies_page", "blobs_page"):
            _back_page = getattr(self, _back_attr, None)
            if _back_page is not None and hasattr(_back_page, "back_clicked"):
                try:
                    _back_page.back_clicked.connect(
                        lambda: self.show_page(PageName.ZAPRET2_DIRECT_CONTROL))
                except Exception:
                    pass

        if hasattr(self.home_page, 'premium_link_btn'):
            self.home_page.premium_link_btn.clicked.connect(self._open_subscription_dialog)

        self.home_page.navigate_to_control.connect(self._navigate_to_control)
        self.home_page.navigate_to_strategies.connect(self._navigate_to_strategies)
        self.home_page.navigate_to_autostart.connect(self.show_autostart_page)
        self.home_page.navigate_to_premium.connect(self._open_subscription_dialog)
        if hasattr(self.home_page, 'navigate_to_dpi_settings'):
            self.home_page.navigate_to_dpi_settings.connect(
                lambda: self.show_page(PageName.DPI_SETTINGS))

        if hasattr(self.appearance_page, 'subscription_btn'):
            self.appearance_page.subscription_btn.clicked.connect(self._open_subscription_dialog)

        if hasattr(self.appearance_page, 'background_refresh_needed'):
            self.appearance_page.background_refresh_needed.connect(self._on_background_refresh_needed)

        if hasattr(self.appearance_page, 'opacity_changed'):
            self.appearance_page.opacity_changed.connect(self._on_opacity_changed)

        if hasattr(self.appearance_page, 'mica_changed'):
            self.appearance_page.mica_changed.connect(self._on_mica_changed)

        if hasattr(self.about_page, 'premium_btn'):
            self.about_page.premium_btn.clicked.connect(self._open_subscription_dialog)

        if hasattr(self.about_page, 'update_btn'):
            self.about_page.update_btn.clicked.connect(lambda: self.show_page(PageName.SERVERS))

        if hasattr(self.premium_page, 'subscription_updated'):
            self.premium_page.subscription_updated.connect(self._on_subscription_updated)

        self.dpi_settings_page.launch_method_changed.connect(self._on_launch_method_changed)
        self.dpi_settings_page.launch_method_changed.connect(self.preset_config_page.refresh_for_current_mode)

        if hasattr(self, 'orchestra_page'):
            self.orchestra_page.clear_learned_requested.connect(self._on_clear_learned_requested)

        try:
            from preset_zapret2.preset_store import get_preset_store
            store = get_preset_store()
            store.preset_switched.connect(self._on_preset_switched)
        except Exception:
            pass

        try:
            from preset_zapret1.preset_store import get_preset_store_v1
            store_v1 = get_preset_store_v1()
            store_v1.preset_switched.connect(self._on_preset_switched)
        except Exception:
            pass

        try:
            self._setup_active_preset_file_watcher()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # All handler methods — PRESERVED from original
    # ------------------------------------------------------------------

    def _on_direct_mode_changed(self, mode: str):
        """Force rebuild of Прямой запуск page on next show."""
        page = getattr(self, "zapret2_strategies_page", None)
        if page and hasattr(page, "_strategy_set_snapshot"):
            page._strategy_set_snapshot = None

    def _on_background_refresh_needed(self):
        """Re-applies window background (called when tinted_bg or accent changes)."""
        try:
            from ui.theme import apply_window_background
            apply_window_background(self.window())
        except Exception:
            pass

    def _on_background_preset_changed(self, preset: str):
        """Apply new background preset to the window."""
        try:
            from ui.theme import apply_window_background
            apply_window_background(self.window(), preset=preset)
        except Exception:
            pass

    def _on_opacity_changed(self, value: int):
        """Apply window opacity from appearance_page slider."""
        win = self.window()
        if hasattr(win, 'set_window_opacity'):
            win.set_window_opacity(value)

    def _on_mica_changed(self, enabled: bool):
        """Save Mica setting and re-apply window background."""
        try:
            from config.reg import set_mica_enabled
            set_mica_enabled(enabled)
        except Exception:
            pass
        try:
            from ui.theme import apply_window_background
            apply_window_background(self.window())
        except Exception:
            pass

    def _setup_active_preset_file_watcher(self) -> None:
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

            self._active_preset_file_path = watched_path

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
            return

    def _on_active_preset_file_changed(self, path: str) -> None:
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
                timer.start(200)
            else:
                self._schedule_refresh_after_preset_switch()
        except Exception:
            try:
                self._schedule_refresh_after_preset_switch()
            except Exception:
                pass

    def _on_preset_switched(self, preset_name: str):
        from log import log
        log(f"Пресет переключен: {preset_name}", "INFO")

        try:
            from strategy_menu import get_strategy_launch_method
            method = (get_strategy_launch_method() or "").strip().lower()
        except Exception:
            method = ""

        if method in ("direct_zapret2", "direct_zapret2_orchestra"):
            try:
                from dpi.zapret2_core_restart import trigger_dpi_reload
                trigger_dpi_reload(self, reason="preset_switched")
            except Exception:
                pass
        else:
            self._schedule_dpi_restart_after_preset_switch()

        self._schedule_refresh_after_preset_switch()

    def _schedule_dpi_restart_after_preset_switch(self, delay_ms: int = 350) -> None:
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
            return

    def _restart_dpi_after_preset_switch(self) -> None:
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
        try:
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(0, self._refresh_pages_after_preset_switch)
        except Exception:
            try:
                self._refresh_pages_after_preset_switch()
            except Exception:
                pass

    def _refresh_pages_after_preset_switch(self):
        from log import log

        try:
            page = getattr(self, "zapret2_strategies_page", None)
            if page and hasattr(page, "refresh_from_preset_switch"):
                page.refresh_from_preset_switch()
        except Exception as e:
            log(f"Ошибка обновления zapret2_strategies_page после смены пресета: {e}", "DEBUG")

        try:
            detail = getattr(self, "strategy_detail_page", None)
            if detail and hasattr(detail, "refresh_from_preset_switch"):
                detail.refresh_from_preset_switch()
        except Exception as e:
            log(f"Ошибка обновления strategy_detail_page после смены пресета: {e}", "DEBUG")

        # Zapret 1 pages
        try:
            z1_page = getattr(self, "zapret1_strategies_page", None)
            if z1_page and hasattr(z1_page, "reload_for_mode_change"):
                z1_page.reload_for_mode_change()
        except Exception as e:
            log(f"Ошибка обновления zapret1_strategies_page после смены пресета: {e}", "DEBUG")

        try:
            z1_ctrl = getattr(self, "zapret1_direct_control_page", None)
            if z1_ctrl and hasattr(z1_ctrl, "_refresh_preset_name"):
                z1_ctrl._refresh_preset_name()
        except Exception as e:
            log(f"Ошибка обновления zapret1_direct_control_page после смены пресета: {e}", "DEBUG")

        try:
            display_name = self._get_direct_strategy_summary()
            if display_name:
                self.update_current_strategy_display(display_name)
        except Exception as e:
            log(f"Ошибка обновления display стратегии после смены пресета: {e}", "DEBUG")

    def _on_clear_learned_requested(self):
        from log import log
        log("Запрошена очистка данных обучения", "INFO")
        if hasattr(self, 'orchestra_runner') and self.orchestra_runner:
            self.orchestra_runner.clear_learned_data()
            log("Данные обучения очищены", "INFO")

    def _on_launch_method_changed(self, method: str):
        from log import log
        from config import WINWS_EXE, WINWS2_EXE

        log(f"Метод запуска изменён на: {method}", "INFO")

        if hasattr(self, 'dpi_starter') and self.dpi_starter.check_process_running_wmi(silent=True):
            log("Останавливаем все процессы winws*.exe перед переключением режима...", "INFO")

            try:
                from utils.process_killer import kill_winws_all
                killed = kill_winws_all()
                if killed:
                    log("Все процессы winws*.exe остановлены через Win API", "INFO")
                if hasattr(self, 'dpi_starter'):
                    self.dpi_starter.cleanup_windivert_service()
                if hasattr(self, 'ui_manager'):
                    self.ui_manager.update_ui_state(running=False)
                if hasattr(self, 'process_monitor_manager'):
                    self.process_monitor_manager.on_process_status_changed(False)
                import time
                time.sleep(0.2)
            except Exception as e:
                log(f"Ошибка остановки через Win API: {e}", "WARNING")

        self._complete_method_switch(method)

    def _complete_method_switch(self, method: str):
        from log import log
        from config import get_winws_exe_for_method, is_zapret2_mode

        try:
            from utils.service_manager import cleanup_windivert_services
            cleanup_windivert_services()
        except Exception:
            pass

        if hasattr(self, 'dpi_starter'):
            self.dpi_starter.winws_exe = get_winws_exe_for_method(method)

        try:
            from launcher_common import invalidate_strategy_runner
            invalidate_strategy_runner()
        except Exception as e:
            log(f"Ошибка инвалидации StrategyRunner: {e}", "WARNING")

        can_autostart = True
        if method == "direct_zapret2":
            from preset_zapret2 import ensure_default_preset_exists
            if not ensure_default_preset_exists():
                log("direct_zapret2: preset-zapret2.txt не создан", "ERROR")
                try:
                    self.set_status("Ошибка: отсутствует Default.txt (built-in пресет)")
                except Exception:
                    pass
                can_autostart = False

        elif method == "direct_zapret1":
            try:
                from preset_zapret1 import ensure_default_preset_exists_v1
                if not ensure_default_preset_exists_v1():
                    log("direct_zapret1: preset-zapret1.txt не создан", "ERROR")
                    can_autostart = False
            except Exception as e:
                log(f"direct_zapret1: ошибка инициализации пресета: {e}", "WARNING")

        # Reload strategy pages
        for attr in ('zapret2_strategies_page', 'zapret2_orchestra_strategies_page',
                     'zapret1_strategies_page'):
            page = getattr(self, attr, None)
            if page and hasattr(page, 'reload_for_mode_change'):
                page.reload_for_mode_change()

        log(f"Переключение на режим '{method}' завершено", "INFO")

        try:
            self._sync_nav_visibility(method)
        except Exception:
            pass

        from PyQt6.QtCore import QTimer
        if can_autostart:
            QTimer.singleShot(500, lambda: self._auto_start_after_method_switch(method))

        try:
            self._redirect_to_strategies_page_for_method(method)
        except Exception:
            pass

    def _redirect_to_strategies_page_for_method(self, method: str) -> None:
        from ui.page_names import PageName

        current = None
        try:
            current = self.stackedWidget.currentWidget() if hasattr(self, "stackedWidget") else None
        except Exception:
            current = None

        strategies_context_pages = set()
        for attr in (
            "dpi_settings_page", "zapret2_user_presets_page", "zapret2_strategies_page",
            "zapret2_orchestra_strategies_page", "zapret1_direct_control_page",
            "zapret1_strategies_page", "zapret1_user_presets_page", "strategy_detail_page",
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
            target_page = PageName.ZAPRET1_DIRECT_CONTROL
        else:
            target_page = PageName.CONTROL

        self.show_page(target_page)

    def _auto_start_after_method_switch(self, method: str):
        from log import log

        try:
            if not hasattr(self, 'dpi_controller') or not self.dpi_controller:
                return

            if method == "orchestra":
                log("Автозапуск Оркестр", "INFO")
                self.dpi_controller.start_dpi_async(selected_mode=None, launch_method="orchestra")

            elif method == "direct_zapret2":
                from config import get_dpi_autostart
                if not get_dpi_autostart():
                    return

                from preset_zapret2 import get_active_preset_path, get_active_preset_name

                preset_path = get_active_preset_path()
                preset_name = get_active_preset_name() or "Default"

                if not preset_path.exists():
                    return

                selected_mode = {
                    'is_preset_file': True,
                    'name': f"Пресет: {preset_name}",
                    'preset_path': str(preset_path)
                }
                self.dpi_controller.start_dpi_async(selected_mode=selected_mode, launch_method=method)

            elif method == "direct_zapret2_orchestra":
                from strategy_menu import get_direct_strategy_selections
                from launcher_common import combine_strategies

                selections = get_direct_strategy_selections()
                combined = combine_strategies(**selections)

                selected_mode = {
                    'is_combined': True,
                    'name': "Оркестратор Z2",
                    'args': combined.get('args', ''),
                    'category_strategies': combined.get('category_strategies', {})
                }
                self.dpi_controller.start_dpi_async(selected_mode=selected_mode, launch_method=method)

            elif method == "direct_zapret1":
                from config import get_dpi_autostart
                if not get_dpi_autostart():
                    return

                from preset_zapret1 import get_active_preset_path_v1, get_active_preset_name_v1

                preset_path = get_active_preset_path_v1()
                preset_name = get_active_preset_name_v1() or "Default"

                if not preset_path.exists():
                    return

                selected_mode = {
                    'is_preset_file': True,
                    'name': f"Пресет Z1: {preset_name}",
                    'preset_path': str(preset_path)
                }
                self.dpi_controller.start_dpi_async(selected_mode=selected_mode, launch_method=method)

        except Exception as e:
            log(f"Ошибка автозапуска после переключения режима: {e}", "ERROR")

    def _proxy_start_click(self):
        self.home_page.start_btn.click()

    def _proxy_stop_click(self):
        self.home_page.stop_btn.click()

    def _proxy_stop_and_exit(self):
        from log import log
        log("Остановка winws и закрытие программы...", "INFO")
        if hasattr(self, "request_exit"):
            self.request_exit(stop_dpi=True)
            return
        if hasattr(self, 'dpi_controller') and self.dpi_controller:
            self._closing_completely = True
            self.dpi_controller.stop_and_exit_async()
        else:
            self.home_page.stop_btn.click()
            from PyQt6.QtWidgets import QApplication
            QApplication.quit()

    def _proxy_test_click(self):
        self.home_page.test_btn.click()

    def _proxy_folder_click(self):
        self.home_page.folder_btn.click()

    def _open_subscription_dialog(self):
        self.show_page(PageName.PREMIUM)

    def _get_direct_strategy_summary(self, max_items: int = 2) -> str:
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

        for page_attr in (
            'zapret2_direct_control_page', 'zapret2_strategies_page',
            'zapret2_orchestra_strategies_page', 'zapret1_direct_control_page',
            'zapret1_strategies_page',
        ):
            page = getattr(self, page_attr, None)
            if page and hasattr(page, 'update_current_strategy'):
                page.update_current_strategy(strategy_name)

        if hasattr(self.home_page, "update_launch_method_card"):
            self.home_page.update_launch_method_card()

    def update_autostart_display(self, enabled: bool, strategy_name: str = None):
        self.home_page.update_autostart_status(enabled)
        self.autostart_page.update_status(enabled, strategy_name)

    def update_subscription_display(self, is_premium: bool, days: int = None):
        self.home_page.update_subscription_status(is_premium, days)
        self.about_page.update_subscription_status(is_premium, days)

    def set_status_text(self, text: str, status: str = "neutral"):
        self.home_page.set_status(text, status)

    def _on_autostart_enabled(self):
        from log import log
        log("Автозапуск включён через страницу настроек", "INFO")
        self.update_autostart_display(True)

    def _on_autostart_disabled(self):
        from log import log
        log("Автозапуск отключён через страницу настроек", "INFO")
        self.update_autostart_display(False)

    def _on_subscription_updated(self, is_premium: bool, days_remaining: int):
        from log import log
        log(f"Статус подписки обновлён: premium={is_premium}, days={days_remaining}", "INFO")
        self.update_subscription_display(is_premium, days_remaining if days_remaining > 0 else None)

        if hasattr(self, 'appearance_page') and self.appearance_page:
            self.appearance_page.set_premium_status(is_premium)

    def _on_strategy_selected_from_page(self, strategy_id: str, strategy_name: str):
        from log import log
        try:
            from strategy_menu import get_strategy_launch_method
            launch_method = get_strategy_launch_method()
        except Exception:
            launch_method = "direct_zapret2"

        sender = None
        try:
            sender = self.sender()
        except Exception:
            sender = None

        if launch_method == "direct_zapret2" and sender is getattr(self, "zapret2_strategies_page", None):
            display_name = self._get_direct_strategy_summary()
            self.update_current_strategy_display(display_name)
            if hasattr(self, "parent_app"):
                try:
                    self.parent_app.current_strategy_name = display_name
                except Exception:
                    pass
            return

        log(f"Стратегия выбрана из страницы: {strategy_id} - {strategy_name}", "INFO")
        self.update_current_strategy_display(strategy_name)

        if hasattr(self, 'parent_app') and hasattr(self.parent_app, 'on_strategy_selected_from_dialog'):
            self.parent_app.on_strategy_selected_from_dialog(strategy_id, strategy_name)

    def _on_open_category_detail(self, category_key: str, current_strategy_id: str):
        from log import log
        from strategy_menu.strategies_registry import registry

        try:
            category_info = registry.get_category_info(category_key)
            if not category_info:
                return

            detail_page = self._ensure_page(PageName.STRATEGY_DETAIL)
            if detail_page and hasattr(detail_page, 'show_category'):
                detail_page.show_category(category_key, category_info, current_strategy_id)

            self.show_page(PageName.STRATEGY_DETAIL)

            try:
                self._direct_zapret2_last_opened_category_key = category_key
                self._direct_zapret2_restore_detail_on_open = True
            except Exception:
                pass
        except Exception as e:
            log(f"Error opening category detail: {e}", "ERROR")

    def _on_strategy_detail_back(self):
        from strategy_menu import get_strategy_launch_method
        method = get_strategy_launch_method()

        if method == "direct_zapret2_orchestra":
            self.show_page(PageName.ZAPRET2_ORCHESTRA)
        elif method == "direct_zapret2":
            self.show_page(PageName.ZAPRET2_DIRECT)
        elif method == "direct_zapret1":
            self.show_page(PageName.ZAPRET1_DIRECT_CONTROL)
        else:
            self.show_page(PageName.CONTROL)

    def _on_strategy_detail_selected(self, category_key: str, strategy_id: str):
        from log import log
        log(f"Strategy selected from detail: {category_key} = {strategy_id}", "INFO")
        if hasattr(self, 'zapret2_strategies_page') and hasattr(self.zapret2_strategies_page, 'apply_strategy_selection'):
            self.zapret2_strategies_page.apply_strategy_selection(category_key, strategy_id)

    def _on_strategy_detail_filter_mode_changed(self, category_key: str, filter_mode: str):
        try:
            if hasattr(self, 'zapret2_strategies_page') and hasattr(self.zapret2_strategies_page, 'apply_filter_mode_change'):
                self.zapret2_strategies_page.apply_filter_mode_change(category_key, filter_mode)
        except Exception:
            pass

    # ── Zapret 1 strategy detail ────────────────────────────────────────────

    def _open_zapret1_category_detail(self, category_key: str, category_info: dict) -> None:
        from log import log
        try:
            detail_page = self._ensure_page(PageName.ZAPRET1_STRATEGY_DETAIL)
            if detail_page is None:
                log("ZAPRET1_STRATEGY_DETAIL page not found", "ERROR")
                return

            from preset_zapret1 import PresetManagerV1

            def _reload_dpi():
                try:
                    page = getattr(self, "zapret1_direct_control_page", None)
                    if page and hasattr(page, "_reload_dpi"):
                        page._reload_dpi()
                except Exception:
                    pass

            manager = PresetManagerV1(on_dpi_reload_needed=_reload_dpi)
            detail_page.set_category(category_key, category_info, manager)
            self.show_page(PageName.ZAPRET1_STRATEGY_DETAIL)
        except Exception as e:
            log(f"Error opening V1 category detail: {e}", "ERROR")

    def _on_z1_strategy_detail_selected(self, category_key: str, strategy_id: str) -> None:
        from log import log
        log(f"V1 strategy detail selected: {category_key} = {strategy_id}", "INFO")
        # Обновить субтитры карточек на странице списка категорий
        page = getattr(self, "zapret1_strategies_page", None)
        if page and hasattr(page, "_refresh_subtitles"):
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(100, page._refresh_subtitles)

    def show_autostart_page(self):
        self.show_page(PageName.AUTOSTART)

    def show_hosts_page(self):
        self.show_page(PageName.HOSTS)

    def show_servers_page(self):
        self.show_page(PageName.SERVERS)

    def _navigate_to_control(self):
        try:
            from strategy_menu import get_strategy_launch_method
            if get_strategy_launch_method() == "direct_zapret2":
                self.show_page(PageName.ZAPRET2_DIRECT_CONTROL)
                return
        except Exception:
            pass
        self.show_page(PageName.CONTROL)

    def _navigate_to_strategies(self):
        from log import log

        try:
            from strategy_menu import get_strategy_launch_method
            method = get_strategy_launch_method()

            if method == "orchestra":
                target_page = PageName.ORCHESTRA
            elif method == "direct_zapret2_orchestra":
                target_page = PageName.ZAPRET2_ORCHESTRA
            elif method == "direct_zapret2":
                last_key = getattr(self, "_direct_zapret2_last_opened_category_key", None)
                want_restore = bool(getattr(self, "_direct_zapret2_restore_detail_on_open", False))

                if want_restore and last_key:
                    try:
                        from strategy_menu.strategies_registry import registry
                        category_info = registry.get_category_info(last_key)
                        detail_page = self._ensure_page(PageName.STRATEGY_DETAIL)
                        if category_info and detail_page and hasattr(detail_page, "show_category"):
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
                    target_page = PageName.ZAPRET2_DIRECT_CONTROL
            elif method == "direct_zapret1":
                target_page = PageName.ZAPRET1_DIRECT_CONTROL
            else:
                target_page = PageName.CONTROL

            self.show_page(target_page)
        except Exception as e:
            log(f"Ошибка определения метода запуска стратегий: {e}", "ERROR")
            self.show_page(PageName.ZAPRET2_DIRECT)

    def _navigate_to_dpi_settings(self):
        self.show_page(PageName.DPI_SETTINGS)

