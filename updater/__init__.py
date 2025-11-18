"""
updater/__init__.py
────────────────────────────────────────────────────────────────
Модуль обновления программы
"""

from .update import run_update_async
from .release_manager import (
    get_latest_release,
    invalidate_cache,
    get_cache_info,
    get_release_manager,
    get_vps_block_info
)
from .rate_limiter import UpdateRateLimiter  # ✅ НОВОЕ

__all__ = [
    'run_update_async',
    'get_latest_release',
    'invalidate_cache',
    'get_cache_info',
    'get_release_manager',
    'get_vps_block_info',
    'UpdateRateLimiter'  # ✅ НОВОЕ
]
