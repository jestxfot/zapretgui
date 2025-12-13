# orchestra/__init__.py
"""
Модуль оркестратора автоматического обучения стратегий (circular).

Использует circular orchestrator из zapret-auto.lua:
- Автоматическая детекция блокировок (RST injection + silent drop)
- LOCK после 3 успехов на одной стратегии
- UNLOCK после 2 failures (автоматическое переобучение)
- Группировка субдоменов (googlevideo.com, youtube.com и т.д.)
"""

from .orchestra_runner import OrchestraRunner, DEFAULT_WHITELIST, REGISTRY_ORCHESTRA

__all__ = [
    'OrchestraRunner',
    'DEFAULT_WHITELIST',
    'REGISTRY_ORCHESTRA',
]
