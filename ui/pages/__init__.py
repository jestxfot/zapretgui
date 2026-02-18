# ui/pages/__init__.py
"""Страницы контента для главного окна"""

from .home_page import HomePage
from .control_page import ControlPage
from .strategies_page_base import StrategiesPageBase
from .zapret2_orchestra_strategies_page import Zapret2OrchestraStrategiesPage
from .zapret1_direct_strategies_page import Zapret1DirectStrategiesPage
from .bat_strategies_page import BatStrategiesPage
from .zapret2 import (
    Zapret2DirectControlPage,
    Zapret2StrategiesPageNew,
    Zapret2UserPresetsPage,
    StrategyDetailPage,
)
from .hostlist_page import HostlistPage
from .ipset_page import IpsetPage
from .blobs_page import BlobsPage
from .dpi_settings_page import DpiSettingsPage
from .autostart_page import AutostartPage
from .network_page import NetworkPage
from .hosts_page import HostsPage
from .appearance_page import AppearancePage
from .about_page import AboutPage
from .support_page import SupportPage
from .help_page import HelpPage
from .logs_page import LogsPage
from .premium_page import PremiumPage
from .blockcheck_page import BlockcheckPage
from .servers_page import ServersPage  # ✅ НОВАЯ СТРАНИЦА
from .custom_domains_page import CustomDomainsPage  # Страница управления other.txt
from .custom_ipset_page import CustomIpSetPage  # Страница управления my-ipset.txt
from .netrogat_page import NetrogatPage  # Страница управления netrogat.txt
from .connection_page import ConnectionTestPage
from .dns_check_page import DNSCheckPage
from .diagnostics_tab_page import DiagnosticsTabPage
from .orchestra_page import OrchestraPage
from .orchestra_locked_page import OrchestraLockedPage
from .orchestra_blocked_page import OrchestraBlockedPage
from .orchestra_whitelist_page import OrchestraWhitelistPage
from .orchestra_ratings_page import OrchestraRatingsPage
from .preset_config_page import PresetConfigPage
from .presets_page import PresetsPage

__all__ = [
    'HomePage',
    'ControlPage',
    'Zapret2OrchestraStrategiesPage',
    'StrategiesPageBase',
    'Zapret1DirectStrategiesPage',
    'BatStrategiesPage',
    'Zapret2StrategiesPageNew',  # Новая страница Zapret2 из zapret2/
    'Zapret2DirectControlPage',  # Управление для direct_zapret2 (вкладка внутри "Стратегии")
    'Zapret2UserPresetsPage',  # Пользовательские пресеты (direct_zapret2)
    'StrategyDetailPage',  # Страница детального просмотра стратегии
    'HostlistPage',
    'IpsetPage',
    'BlobsPage',  # Управление блобами для Zapret 2
    'DpiSettingsPage',
    'AutostartPage',
    'NetworkPage',
    'HostsPage',
    'AppearancePage',
    'AboutPage',
    'SupportPage',
    'HelpPage',
    'LogsPage',
    'PremiumPage',
    'BlockcheckPage',
    'ServersPage',  # ✅ НОВАЯ СТРАНИЦА
    'CustomDomainsPage',  # Страница управления other.txt
    'CustomIpSetPage',  # Страница управления my-ipset.txt
    'NetrogatPage',  # Страница управления netrogat.txt
    'ConnectionTestPage',
    'DNSCheckPage',  # Страница проверки DNS подмены
    'DiagnosticsTabPage',  # Объединённая страница диагностики с вкладками
    'OrchestraPage',  # Страница оркестратора автообучения
    'OrchestraLockedPage',  # Страница залоченных стратегий оркестратора
    'OrchestraBlockedPage',  # Страница заблокированных стратегий оркестратора
    'OrchestraWhitelistPage',  # Страница белого списка оркестратора
    'OrchestraRatingsPage',  # Страница истории стратегий с рейтингами
    'PresetConfigPage',  # Страница редактора preset-zapret2.txt
    'PresetsPage',  # Страница управления пресетами (только direct_zapret2)
]
