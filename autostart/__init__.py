"""
Модуль автозапуска Zapret.
Поддерживает: планировщик задач, службы Windows, реестр.
"""

from .service_api import (
    create_service,
    delete_service,
    start_service,
    stop_service,
    service_exists,
    create_zapret_service,
    create_bat_service,
)

from .autostart_service import (
    setup_service_for_strategy,
    remove_service,
    SERVICE_NAME as BAT_SERVICE_NAME,
)

from .autostart_direct_service import (
    setup_direct_service,
    remove_direct_service,
    check_direct_service_exists,
    SERVICE_NAME as DIRECT_SERVICE_NAME,
)

from .registry_check import (
    is_autostart_enabled,
    set_autostart_enabled,
)

from .autostart_exe import (
    setup_autostart_for_exe,
    remove_all_autostart_mechanisms,
)

from .checker import CheckerManager

__all__ = [
    # Service API
    'create_service',
    'delete_service', 
    'start_service',
    'stop_service',
    'service_exists',
    'create_zapret_service',
    'create_bat_service',
    
    # BAT mode service
    'setup_service_for_strategy',
    'remove_service',
    'BAT_SERVICE_NAME',
    
    # Direct mode service
    'setup_direct_service',
    'remove_direct_service',
    'check_direct_service_exists',
    'DIRECT_SERVICE_NAME',
    
    # Registry
    'is_autostart_enabled',
    'set_autostart_enabled',
    
    # EXE autostart
    'setup_autostart_for_exe',
    'remove_all_autostart_mechanisms',
    
    # Checker
    'CheckerManager',
]

