# strategy_menu/preset_configuration_zapret2/__init__.py
"""
Preset Configuration Zapret2 - централизованный модуль для управления настройками DPI.

Структура:
    - registry_settings.py    - CRUD для реестра (save/load)
    - sync.py                 - Координация: save → regenerate → restart
    - command_builder         - Сборка командной строки winws
    - preset_regenerator.py   - Генерация preset-zapret2.txt
    - strategy_selections.py  - Управление выбором стратегий для категорий

Использование:
    # Простой способ - применить настройку и перезапустить DPI
    from strategy_menu.preset_configuration_zapret2 import sync
    sync.apply_filter_mode("youtube", "ipset")
    sync.apply_out_range("youtube", {"mode": "n", "value": 10})
    sync.apply_syndata("youtube", {"enabled": True, ...})

    # Прямая работа с реестром (без перезапуска DPI)
    from strategy_menu.preset_configuration_zapret2 import registry_settings as rs
    rs.save_filter_mode("youtube", "ipset")
    mode = rs.load_filter_mode("youtube")

    # Сборка командной строки
    from strategy_menu.preset_configuration_zapret2 import command_builder
    result = command_builder.build_full_command({...})

    # Генерация preset файла
    from strategy_menu.preset_configuration_zapret2 import preset_regenerator
    preset_regenerator.regenerate()

    # Управление выбором стратегий
    from strategy_menu.preset_configuration_zapret2 import strategy_selections
    strategy_selections.set("youtube", "multisplit_tls")
    selections = strategy_selections.get_all()

Инициализация (в main.py):
    from strategy_menu.preset_configuration_zapret2 import sync
    sync.set_regenerate_callback(regenerate_preset_file)
    sync.set_restart_callback(lambda cat, strat: dpi_controller.start_dpi_async())
    sync.set_get_current_strategy_callback(get_current_strategy_for_category)
"""

# Реэкспорт подмодулей
from . import registry_settings
from . import sync
from . import command_builder  # Теперь здесь!
from . import preset_regenerator
from . import strategy_selections

# Быстрый доступ к основным функциям
from .sync import (
    apply_filter_mode,
    apply_out_range,
    apply_syndata,
    apply_setting,
    apply_multiple,
    reset_and_apply,
    set_regenerate_callback,
    set_restart_callback,
    set_get_current_strategy_callback,
)

from .registry_settings import (
    save_filter_mode,
    load_filter_mode,
    save_out_range,
    load_out_range,
    save_syndata,
    load_syndata,
    save_sort_order,
    load_sort_order,
    reset_category_settings,
    FILTER_MODE_DEFAULT,
    OUT_RANGE_DEFAULT,
    SYNDATA_DEFAULT,
)

from .preset_regenerator import (
    regenerate,
    write_preset,
    read_preset,
    get_preset_path,
    exists,
)

from .strategy_selections import (
    get,
    set,
    get_all,
    set_all,
    clear_all,
    invalidate_cache,
)

__all__ = [
    # Submodules
    'registry_settings',
    'sync',
    'command_builder',
    'preset_regenerator',
    'strategy_selections',

    # Sync functions (main API)
    'apply_filter_mode',
    'apply_out_range',
    'apply_syndata',
    'apply_setting',
    'apply_multiple',
    'reset_and_apply',
    'set_regenerate_callback',
    'set_restart_callback',
    'set_get_current_strategy_callback',

    # Registry functions (direct access)
    'save_filter_mode',
    'load_filter_mode',
    'save_out_range',
    'load_out_range',
    'save_syndata',
    'load_syndata',
    'save_sort_order',
    'load_sort_order',
    'reset_category_settings',

    # Defaults
    'FILTER_MODE_DEFAULT',
    'OUT_RANGE_DEFAULT',
    'SYNDATA_DEFAULT',

    # Preset regenerator functions
    'regenerate',
    'write_preset',
    'read_preset',
    'get_preset_path',
    'exists',

    # Strategy selections functions
    'get',
    'set',
    'get_all',
    'set_all',
    'clear_all',
    'invalidate_cache',
]
