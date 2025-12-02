# ui/pages/__init__.py
"""Страницы контента для главного окна"""

from .home_page import HomePage
from .control_page import ControlPage
from .strategies_page import StrategiesPage
from .hostlist_page import HostlistPage
from .ipset_page import IpsetPage
from .editor_page import EditorPage
from .dpi_settings_page import DpiSettingsPage
from .autostart_page import AutostartPage
from .network_page import NetworkPage
from .appearance_page import AppearancePage
from .about_page import AboutPage
from .logs_page import LogsPage
from .premium_page import PremiumPage

__all__ = [
    'HomePage',
    'ControlPage', 
    'StrategiesPage',
    'HostlistPage',
    'IpsetPage',
    'EditorPage',
    'DpiSettingsPage',
    'AutostartPage',
    'NetworkPage',
    'AppearancePage',
    'AboutPage',
    'LogsPage',
    'PremiumPage'
]

