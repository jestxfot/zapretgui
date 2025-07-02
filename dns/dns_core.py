# dns_core.py
"""
Базовые утилиты и DNSManager.
Не содержит импортов PyQt и НЕ импортирует dns_force → никакого
кругового импорта.
"""
from __future__ import annotations

import json
import subprocess
import os
from functools import lru_cache
from typing import List, Tuple, Dict

from log import log


# ──────────────────────────────────────────────────────────────────────
#  Константы
# ──────────────────────────────────────────────────────────────────────
DEFAULT_EXCLUSIONS: list[str] = [
    # Виртуальные адаптеры
    "vmware", "outline-tap", "openvpn", "virtualbox", "hyper-v", "vmnet",
    # VPN
    "radmin vpn", "hamachi", "nordvpn", "expressvpn", "surfshark",
    "pritunl", "zerotier", "tailscale",
    # Системные / служебные
    "loopback", "teredo", "isatap", "6to4", "bluetooth",
    # Другое
    "docker", "wsl", "vethernet"
]


# ──────────────────────────────────────────────────────────────────────
#  Вспом-функции
# ──────────────────────────────────────────────────────────────────────
def _normalize_alias(alias: str) -> str:
    """
    Приводим InterfaceAlias к более-менее нормальному виду
    (убираем NBSP, LRM/RLM и т.д.)
    """
    if not isinstance(alias, str):
        return alias
    repl = (
        ('\u00A0', ' '),  # NBSP
        ('\u200E', ''),   # LRM
        ('\u200F', ''),   # RLM
        ('\t',     ' '),
    )
    for bad, good in repl:
        alias = alias.replace(bad, good)
    return alias.strip()


@lru_cache(maxsize=1)
def _get_dynamic_exclusions() -> list[str]:
    """
    Пока берём только DEFAULT_EXCLUSIONS.
    Если захотите динамику из реестра – добавьте здесь, НО избегайте
    импорта dns_force, чтобы снова не сделать петлю.
    """
    return [x.lower() for x in DEFAULT_EXCLUSIONS]


def refresh_exclusion_cache() -> None:
    """Сброс LRU-кэша (используйте после изменения списков)."""
    _get_dynamic_exclusions.cache_clear()


# ──────────────────────────────────────────────────────────────────────
#  DNSManager
# ──────────────────────────────────────────────────────────────────────
class DNSManager:
    """Работа с DNS-настройками Windows (+IPv6)"""

    # ----- инициализация WMI ------------------------------------------------
    def __init__(self):
        try:
            import wmi
            self.wmi_conn = wmi.WMI()
        except Exception:
            self.wmi_conn = None

    # ----- фильтрация адаптеров --------------------------------------------
    @staticmethod
    def should_ignore_adapter(name: str, description: str) -> bool:
        name = _normalize_alias(name)
        description = _normalize_alias(description)
        for pattern in _get_dynamic_exclusions():
            if pattern in name.lower() or pattern in description.lower():
                return True
        return False

    @staticmethod
    def get_network_adapters(include_ignored: bool = False,
                             include_disconnected: bool = True):
        """
        Старое имя-обёртка.  Просто переадресует на
        get_network_adapters_fast().
        """
        return DNSManager.get_network_adapters_fast(
            include_ignored=include_ignored,
            include_disconnected=include_disconnected
        )
    
    # ----- быстрый список адаптеров (WMI) ----------------------------------
    @staticmethod
    def get_network_adapters_fast(
            include_ignored: bool = False,
            include_disconnected: bool = True
        ) -> List[Tuple[str, str]]:
        """
        Возвращает [(InterfaceAlias, Description), …]
        """
        try:
            import wmi
            c = wmi.WMI()
            adapters: list[tuple[str, str]] = []

            for a in c.Win32_NetworkAdapter(PhysicalAdapter=True):
                if not a.NetConnectionID or not a.Description:
                    continue
                if not include_disconnected and a.NetConnectionStatus != 2:
                    continue

                alias_raw = a.NetConnectionID
                alias_norm = _normalize_alias(alias_raw)
                desc       = a.Description

                if include_ignored or not DNSManager.should_ignore_adapter(alias_norm, desc):
                    adapters.append((alias_raw, desc))
            return adapters

        except ImportError:
            # WMI не установлена – PowerShell fallback
            return DNSManager.get_network_adapters_powershell_fallback(
                include_ignored, include_disconnected
            )
        except Exception as e:
            log(f"WMI error → fallback: {e}", "DEBUG")
            return DNSManager.get_network_adapters_powershell_fallback(
                include_ignored, include_disconnected
            )

    # ----- fallback через PowerShell ---------------------------------------
    @staticmethod
    def get_network_adapters_powershell_fallback(
            include_ignored: bool = False,
            include_disconnected: bool = True
        ) -> List[Tuple[str, str]]:
        try:
            status_filter = '' if include_disconnected else ' | Where-Object {$_.Status -eq "Up"}'
            command = [
                'powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command',
                f'Get-NetAdapter{status_filter} | '
                'Select-Object Name,InterfaceDescription | ConvertTo-Json'
            ]
            res = subprocess.run(
                command, capture_output=True, text=True, timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            if res.returncode:
                log(f"PS adapter error: {res.stderr}", "DNS")
                return []

            objs = json.loads(res.stdout or '[]')
            if not isinstance(objs, list):
                objs = [objs]

            lst: list[tuple[str, str]] = []
            for o in objs:
                name_raw = o.get('Name', '')
                desc     = o.get('InterfaceDescription', '')
                name_norm = _normalize_alias(name_raw)

                if include_ignored or not DNSManager.should_ignore_adapter(name_norm, desc):
                    lst.append((name_raw, desc))
            return lst

        except Exception as e:
            log(f"adapter fallback exc: {e}", "DNS")
            return []

    # -----------------------------------------------------------------------
    #  Получение DNS-серверов одним запросом (IPv4 + IPv6)
    # -----------------------------------------------------------------------
    def get_all_dns_info_fast(self, adapter_names: list[str]) \
            -> dict[str, dict[str, list[str]]]:

        if not adapter_names:
            return {}

        adapter_list = "','" .join(adapter_names)

        # f-строка: вставляем adapter_list, остальные скобки не трогаем
        ps = fr'''
    [Console]::OutputEncoding=[System.Text.Encoding]::UTF8

    $adapters = @('{adapter_list}')
    $result   = @{{}}

    foreach ($a in $adapters) {{
        $adapterInfo = @{{ "ipv4" = @(); "ipv6" = @() }}

        # IPv4
        $dnsv4 = Get-DnsClientServerAddress -InterfaceAlias "$a" `
            -AddressFamily IPv4 -ErrorAction SilentlyContinue |
            Select -ExpandProperty ServerAddresses
        if (-not $dnsv4) {{
            $dnsv4 = Get-DnsClientServerAddress -InterfaceAlias "$a" `
                -AddressFamily IPv4 -PolicyStore PersistentStore -ErrorAction SilentlyContinue |
                Select -ExpandProperty ServerAddresses
        }}

        # IPv6
        $dnsv6 = Get-DnsClientServerAddress -InterfaceAlias "$a" `
            -AddressFamily IPv6 -ErrorAction SilentlyContinue |
            Select -ExpandProperty ServerAddresses
        if (-not $dnsv6) {{
            $dnsv6 = Get-DnsClientServerAddress -InterfaceAlias "$a" `
                -AddressFamily IPv6 -PolicyStore PersistentStore -ErrorAction SilentlyContinue |
                Select -ExpandProperty ServerAddresses
        }}

        if ($dnsv4) {{ $adapterInfo["ipv4"] = @($dnsv4) }}
        if ($dnsv6) {{ $adapterInfo["ipv6"] = @($dnsv6) }}

        $result[$a] = $adapterInfo
    }}

    $result | ConvertTo-Json -Depth 3
    '''

        try:
            run = subprocess.run(
                ['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass',
                '-Command', ps],
                capture_output=True, text=True, timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW, encoding='utf-8'
            )
            if run.returncode:
                raise RuntimeError(run.stderr)

            raw = json.loads(run.stdout or '{}')
            return { _normalize_alias(k): {"ipv4": v.get("ipv4", []),
                                        "ipv6": v.get("ipv6", [])}
                    for k, v in raw.items() }

        except Exception as e:
            log(f"bulk DNS PS err: {e}", "DNS")
            # fallback – по одному адаптеру
            return { n: {"ipv4": self.get_current_dns(n, "IPv4"),
                        "ipv6": self.get_current_dns(n, "IPv6")}
                    for n in adapter_names }
    
    # -----------------------------------------------------------------------
    #  Получить / установить DNS одного адаптера
    # -----------------------------------------------------------------------
    @staticmethod
    def get_current_dns(adapter_name: str, address_family: str = "IPv4") -> List[str]:
        """
        Вернёт список DNS для IPv4/IPv6 (или []).
        """
        adapter_esc = adapter_name.replace("'", "''")
        cmd = [
            'powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command',
            f'''
            try {{
                Get-DnsClientServerAddress -InterfaceAlias '{adapter_esc}' -AddressFamily {address_family} |
                    Select -Expand ServerAddresses
            }} catch {{}}
            '''
        ]
        res = subprocess.run(
            cmd, capture_output=True, text=True, timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        if res.returncode:
            return []
        return [x.strip() for x in res.stdout.splitlines() if x.strip()]

    # ---- Установка кастомного / сброс DNS ---------------------------------
    @staticmethod
    def set_custom_dns(
            adapter_name: str,
            primary_dns: str,
            secondary_dns: str | None = None,
            address_family: str = "IPv4"
        ) -> tuple[bool, str]:
        """
        Упрощённая установка.  Сначала пытаемся через netsh (IPv4),
        потом fallback → PowerShell.  Для IPv6 сразу PowerShell.
        """
        if address_family == "IPv4":
            ok, msg = DNSManager._set_ipv4_via_netsh(adapter_name, primary_dns, secondary_dns)
            if ok:  # успех
                return True, msg
            # fallback
            return DNSManager._set_ipv4_via_powershell(adapter_name, primary_dns, secondary_dns)
        else:
            return DNSManager._set_ipv6_via_powershell(adapter_name, primary_dns, secondary_dns)

    @staticmethod
    def set_auto_dns(adapter_name: str, address_family: str | None = None) -> tuple[bool, str]:
        """
        address_family = None  → сбросить и IPv4 и IPv6.
        """
        fam_flag = f"-AddressFamily {address_family}" if address_family else ""
        cmd = [
            'powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command',
            f"Set-DnsClientServerAddress -InterfaceAlias '{adapter_name}' {fam_flag} -ResetServerAddresses"
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, shell=False)
        if res.returncode:
            return False, res.stderr
        return True, "OK"

    # ---- утилита ----------------------------------------------------------
    @staticmethod
    def flush_dns_cache() -> tuple[bool, str]:
        run = subprocess.run(
            ['ipconfig', '/flushdns'],
            capture_output=True, text=True, shell=False
        )
        if run.returncode:
            return False, run.stderr
        return True, "cache flushed"

    # ----- внутренние helpers ---------------------------------------------
    @staticmethod
    def _set_ipv4_via_netsh(adapter, primary, secondary=None):
        try:
            cmd1 = f'netsh interface ipv4 set dnsservers "{adapter}" static {primary} primary'
            r1 = subprocess.run(cmd1, shell=True, capture_output=True, text=True, encoding='cp866')
            if r1.returncode:
                return False, r1.stderr
            if secondary:
                cmd2 = f'netsh interface ipv4 add dnsservers "{adapter}" {secondary} index=2'
                subprocess.run(cmd2, shell=True, capture_output=True, text=True, encoding='cp866')
            return True, "netsh OK"
        except Exception as e:
            return False, str(e)

    @staticmethod
    def _set_ipv4_via_powershell(adapter, primary, secondary=None):
        arr = f"@('{primary}','{secondary}')" if secondary else f"@('{primary}')"
        cmd = [
            'powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command',
            f"Set-DnsClientServerAddress -InterfaceAlias '{adapter}' -AddressFamily IPv4 -ServerAddresses {arr}"
        ]
        r = subprocess.run(cmd, capture_output=True, text=True)
        return (r.returncode == 0, r.stderr if r.returncode else "PS OK")

    @staticmethod
    def _set_ipv6_via_powershell(adapter, primary, secondary=None):
        arr = f"@('{primary}','{secondary}')" if secondary else f"@('{primary}')"
        cmd = [
            'powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command',
            f"Set-DnsClientServerAddress -InterfaceAlias '{adapter}' -AddressFamily IPv6 -ServerAddresses {arr}"
        ]
        r = subprocess.run(cmd, capture_output=True, text=True)
        return (r.returncode == 0, r.stderr if r.returncode else "PS OK")