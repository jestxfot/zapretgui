# ────────────────────────────────────────────────────────────────────
#  __init__.py   (пакет dns_tools/…)
# ────────────────────────────────────────────────────────────────────
"""
Единая точка входа в библиотеку.

Доступны:
    DNSManager                 – низкоуровневые утилиты (без PyQt)
    DEFAULT_EXCLUSIONS         – список шаблонов «виртуальных» адаптеров
    refresh_exclusion_cache()  – сброс кэша исключений

    DNSForceManager            – менеджер «принудительного» DNS
    apply_force_dns_if_enabled – вспом. функция быстрого применения
    ensure_default_force_dns   – автосоздание ключа ForceDNS

    PREDEFINED_DNS             – словарь с готовыми наборами DNS

Все тяжёлые модули импортируются лениво (при первом обращении).
"""

from __future__ import annotations

import importlib
import sys
from types import ModuleType
from typing import Any
from dns.dns_core import DNSManager, DEFAULT_EXCLUSIONS, refresh_exclusion_cache, _normalize_alias
from dns.dns_force import DNSForceManager, apply_force_dns_if_enabled, ensure_default_force_dns
from dns.dns_dialog import DNSSettingsDialog, PREDEFINED_DNS

__all__: tuple[str, ...] = (
    "DNSManager",
    "DEFAULT_EXCLUSIONS",
    "refresh_exclusion_cache",
    "_normalize_alias",
    "DNSForceManager",
    "apply_force_dns_if_enabled",
    "ensure_default_force_dns",
    "PREDEFINED_DNS",
    "DNSSettingsDialog",
)

# Чтобы dir() показывал отложенные элементы
def __dir__() -> list[str]:
    return sorted(list(__all__) + list(globals().keys()))