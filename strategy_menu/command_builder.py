# strategy_menu/command_builder.py
"""
Command Builder Module
Централизованная сборка командной строки для winws/winws2.

Использование:
    from strategy_menu.command_builder import build_full_command, build_syndata_args

    result = build_full_command({"youtube": "strategy_1", "discord": "strategy_2"})
    args = result["args"]
"""

import re
import json
from typing import Optional

from .blobs import get_blobs

# ===================== HELPERS =====================

def clean_spaces(text: str) -> str:
    """Удаляет лишние пробелы"""
    return re.sub(r'\s+', ' ', text).strip()


def strip_payload_from_args(args: str) -> str:
    """Убирает --payload= из стратегии (для IPset категорий)"""
    return re.sub(r'--payload=[^\s]+\s*', '', args)


def replace_out_range(args: str, value: int) -> str:
    """Заменяет значение --out-range в аргументах"""
    return re.sub(r'--out-range=[^\s]+', f'--out-range=-d{value}', args)


def extract_payload(args: str) -> tuple[str, str]:
    """
    Извлекает --payload=... из строки аргументов.

    Args:
        args: строка аргументов стратегии

    Returns:
        tuple[str, str]: (payload_part, remaining_args)

    Example:
        extract_payload("--lua-desync=fake --payload=tls_client_hello --out-range=5")
        returns ("--payload=tls_client_hello", "--lua-desync=fake --out-range=5")
    """
    if not args:
        return ("", "")

    # Ищем --payload=...
    match = re.search(r'--payload=[^\s]+', args)
    if match:
        payload_part = match.group(0)
        remaining = re.sub(r'--payload=[^\s]+\s*', '', args)
        return (payload_part, clean_spaces(remaining))

    return ("", args)


# ===================== SYNDATA =====================

def build_syndata_args(category_key: str) -> str:
    """
    Собирает --lua-desync=syndata:... из настроек реестра.

    Returns:
        str: например "--lua-desync=syndata:blob=tls7:ip_ttl=5" или ""
    """
    try:
        import winreg
        for base_path in [r"Software\Zapret2DevReg", r"Software\Zapret2Reg"]:
            try:
                key_path = f"{base_path}\\CategorySyndata"
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
                    value, _ = winreg.QueryValueEx(key, category_key)
                    settings = json.loads(value)

                    if not settings.get("enabled", False):
                        return ""

                    parts = ["syndata"]

                    blob = settings.get("blob", "none")
                    if blob and blob != "none":
                        parts.append(f"blob={blob}")

                    tls_mod = settings.get("tls_mod", "none")
                    if tls_mod and tls_mod != "none":
                        parts.append(f"tls_mod={tls_mod}")

                    ip_ttl = settings.get("ip_ttl", 0)
                    if ip_ttl and ip_ttl > 0:
                        parts.append(f"ip_ttl={ip_ttl}")

                    tcp_flags = settings.get("tcp_flags_unset", "none")
                    if tcp_flags and tcp_flags != "none":
                        parts.append(f"tcp_flags_unset={tcp_flags}")

                    if len(parts) > 1:
                        return f"--lua-desync={':'.join(parts)}"
                    return "--lua-desync=syndata"
            except FileNotFoundError:
                continue
    except Exception:
        pass
    return ""


# ===================== CATEGORY ARGS =====================

def build_category_args(
    base_filter: str,
    strategy_args: str,
    category_key: str,
    strip_payload: bool = False
) -> str:
    """
    Собирает полную строку для категории:
    base_filter + payload + syndata + remaining_strategy_args

    Args:
        base_filter: фильтр категории (--filter-tcp=443 --hostlist=youtube.txt)
        strategy_args: техника стратегии (--lua-desync=multisplit...)
        category_key: ключ категории для syndata
        strip_payload: убрать --payload= (для IPset)

    Returns:
        str: полная командная строка для категории
    """
    syndata_args = build_syndata_args(category_key)

    # Извлекаем payload из strategy_args
    payload_part, remaining_strategy_args = extract_payload(strategy_args)

    if strip_payload:
        payload_part = ""

    parts = []
    if base_filter:
        parts.append(base_filter)
    if payload_part:
        parts.append(payload_part)
    if syndata_args:
        parts.append(syndata_args)
    if remaining_strategy_args:
        parts.append(remaining_strategy_args)

    return " ".join(parts)


# ===================== PREVIEW =====================

def preview_syndata(category_key: str) -> str:
    """Возвращает превью syndata для отображения в UI"""
    args = build_syndata_args(category_key)
    if not args:
        return "Syndata: выключено"
    return f"Syndata: {args}"


# ===================== FILTER MODE =====================

def get_filter_mode(category_key: str) -> str:
    """
    Получает режим фильтрации для категории из реестра.

    Returns:
        "hostlist" или "ipset"
    """
    try:
        import winreg
        from config import REGISTRY_PATH
        key_path = f"{REGISTRY_PATH}\\CategoryFilterMode"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
            value, _ = winreg.QueryValueEx(key, category_key)
            if value == "ipset":
                return "ipset"
            return "hostlist"
    except:
        return "hostlist"
