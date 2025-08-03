"""
build_tools/__init__.py - Инициализация пакета build_tools
"""

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
    def create_github_release(*args, **kwargs):
        return None
    
    def is_github_enabled():
        return False
    
    def get_github_config_info():
        return "Модуль недоступен"
    
    def test_github_connection(*args, **kwargs):
        return False
    
    GITHUB_CONFIG = {"enabled": False}
    GITHUB_AVAILABLE = False

# Экспортируем функции
__all__ = [
    'create_github_release',
    'is_github_enabled', 
    'get_github_config_info',
    'test_github_connection',
    'GITHUB_AVAILABLE'
]
