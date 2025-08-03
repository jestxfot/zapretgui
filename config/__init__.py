#config/__init__.py
from .config import BIN_FOLDER, EXE_FOLDER, THEME_FOLDER, BAT_FOLDER, LISTS_FOLDER, LOGS_FOLDER, WINWS_EXE, ICON_PATH, ICON_TEST_PATH, OTHER_PATH, OTHER2_PATH, NETROGAT_PATH, NETROGAT2_PATH, STRATEGIES_FOLDER, WIDTH, HEIGHT, INDEXJSON_FOLDER, DEFAULT_STRAT, REG_LATEST_STRATEGY
from .build_info import APP_VERSION, CHANNEL
from .reg import reg, HKCU, get_last_strategy, set_last_strategy, get_dpi_autostart, set_dpi_autostart, get_strategy_autoload, set_strategy_autoload, get_remove_windows_terminal, set_remove_windows_terminal, set_auto_download_enabled, get_auto_download_enabled, get_subscription_check_interval, get_remove_github_api

__all__ = [
    # build_info.py
    'APP_VERSION',
    'CHANNEL',
    # config.py
    'THEME_FOLDER',
    'EXE_FOLDER',
    'BIN_FOLDER',
    'REG_LATEST_STRATEGY',
    'BAT_FOLDER',
    'LISTS_FOLDER',
    'LOGS_FOLDER',
    'INDEXJSON_FOLDER',
    'DEFAULT_STRAT',
    'WINWS_EXE',
    'ICON_PATH',
    'ICON_TEST_PATH',
    'OTHER_PATH',
    'OTHER2_PATH',
    'NETROGAT_PATH',
    'NETROGAT2_PATH',
    'STRATEGIES_FOLDER',
    'WIDTH',
    'HEIGHT',
    # reg.py
    'set_auto_download_enabled',
    'get_last_strategy',
    'set_last_strategy',
    'get_dpi_autostart',
    'set_dpi_autostart',
    'get_strategy_autoload',
    'set_strategy_autoload',
    'get_remove_windows_terminal',
    'set_remove_windows_terminal',
    'get_auto_download_enabled',
    'get_subscription_check_interval',
    'get_remove_github_api',
    'reg',
    'HKCU'
]