# build_tools/__init__.py

# Optional local .env support (no hard dependency).
import os
from typing import Optional

# Пытаемся импортировать GitHub функции
try:
    from .github_release import (
        create_github_release, 
        is_github_enabled, 
        get_github_config_info,
        test_github_connection
    )
    GITHUB_AVAILABLE = True
except ImportError:
    # Если github_release.py недоступен, создаем заглушки
    def create_github_release(*args, **kwargs) -> Optional[str]:
        return None
    
    def is_github_enabled() -> bool:
        return False
    
    def get_github_config_info() -> str:
        return "Модуль недоступен"
    
    def test_github_connection(*args, **kwargs) -> bool:
        return False
    
    GITHUB_CONFIG = {"enabled": False}
    GITHUB_AVAILABLE = False

# Telegram API credentials are provided via env/.env (do not store in repo).
TELEGRAM_API_ID = os.getenv("TELEGRAM_API_ID") or os.getenv("ZAPRET_TELEGRAM_API_ID")
TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH") or os.getenv("ZAPRET_TELEGRAM_API_HASH")

# Экспортируем функции
__all__ = [
    'create_github_release',
    'is_github_enabled', 
    'get_github_config_info',
    'test_github_connection',
    'GITHUB_AVAILABLE',
    'TELEGRAM_API_HASH',
    'TELEGRAM_API_ID',
]
