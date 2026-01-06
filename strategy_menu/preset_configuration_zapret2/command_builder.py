# strategy_menu/preset_configuration_zapret2/command_builder.py
"""
Command Builder Module
Centralised module for building winws/winws2 command lines.

Usage:
    from strategy_menu.preset_configuration_zapret2 import command_builder

    # Or directly:
    from strategy_menu.preset_configuration_zapret2.command_builder import build_full_command

    result = build_full_command({"youtube": "yt_strategy_1", "discord": "ds_default"})
"""

import re
import os
import json
from typing import Optional

from log import log
from strategy_menu.blobs import get_blobs, build_args_with_deduped_blobs


# ===================== HELPERS =====================

def clean_spaces(text: str) -> str:
    """Removes extra whitespace"""
    return re.sub(r'\s+', ' ', text).strip()


def strip_payload_from_args(args: str) -> str:
    """Removes --payload= from strategy (for IPset categories)"""
    return re.sub(r'--payload=[^\s]+\s*', '', args)


def replace_out_range(args: str, value: int) -> str:
    """Replaces --out-range value in arguments"""
    return re.sub(r'--out-range=[^\s]+', f'--out-range=-d{value}', args)


def extract_payload(args: str) -> tuple[str, str]:
    """
    Extracts --payload=... from argument string.

    Args:
        args: strategy argument string

    Returns:
        tuple[str, str]: (payload_part, remaining_args)

    Example:
        extract_payload("--lua-desync=fake --payload=tls_client_hello --out-range=5")
        returns ("--payload=tls_client_hello", "--lua-desync=fake --out-range=5")
    """
    if not args:
        return ("", "")

    # Find --payload=...
    match = re.search(r'--payload=[^\s]+', args)
    if match:
        payload_part = match.group(0)
        remaining = re.sub(r'--payload=[^\s]+\s*', '', args)
        return (payload_part, clean_spaces(remaining))

    return ("", args)


# ===================== SYNDATA =====================

def build_syndata_args(category_key: str) -> str:
    """
    Builds --lua-desync=syndata:... from registry settings.

    Returns:
        str: e.g. "--lua-desync=syndata:blob=tls7:ip_ttl=5" or ""
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
    Builds full string for category:
    base_filter + payload + syndata + remaining_strategy_args

    Args:
        base_filter: category filter (--filter-tcp=443 --hostlist=youtube.txt)
        strategy_args: strategy technique (--lua-desync=multisplit...)
        category_key: category key for syndata
        strip_payload: remove --payload= (for IPset)

    Returns:
        str: full command line for category
    """
    syndata_args = build_syndata_args(category_key)

    # Extract payload from strategy_args
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
    """Returns syndata preview for UI display"""
    args = build_syndata_args(category_key)
    if not args:
        return "Syndata: disabled"
    return f"Syndata: {args}"


# ===================== FILTER MODE =====================

def get_filter_mode(category_key: str) -> str:
    """
    Gets filter mode for category from registry.

    Returns:
        "hostlist" or "ipset"
    """
    try:
        import winreg
        from config import REGISTRY_PATH
        from log import log
        key_path = f"{REGISTRY_PATH}\\CategoryFilterMode"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
            value, _ = winreg.QueryValueEx(key, category_key)
            result = "ipset" if value == "ipset" else "hostlist"
            log(f"[command_builder.get_filter_mode] {category_key}: raw='{value}' -> result='{result}'", "DEBUG")
            return result
    except Exception as e:
        from log import log
        log(f"[command_builder.get_filter_mode] {category_key}: exception={e}, returning 'hostlist'", "DEBUG")
        return "hostlist"


# ===================== FILTER CALCULATION =====================

def calculate_required_filters(category_strategies: dict) -> dict:
    """
    Automatically calculates required filters based on selected categories.

    Uses filters_config.py to determine which filters are needed.

    Args:
        category_strategies: dict {category_key: strategy_id}

    Returns:
        dict with filter flags
    """
    from strategy_menu.filters_config import get_filter_for_category, FILTERS
    from strategy_menu.strategies_registry import registry

    # Initialize all filters as False
    filters = {key: False for key in FILTERS.keys()}

    none_strategies = registry.get_none_strategies()

    for category_key, strategy_id in category_strategies.items():
        # Skip inactive categories
        if not strategy_id:
            continue
        none_id = none_strategies.get(category_key)
        if strategy_id == none_id or strategy_id == "none":
            continue

        # Get category info
        category_info = registry.get_category_info(category_key)
        if not category_info:
            continue

        # Get required filters via config
        required_filters = get_filter_for_category(category_info)
        for filter_key in required_filters:
            filters[filter_key] = True

    log(f"Auto-detected filters: TCP=[80={filters.get('tcp_80')}, 443={filters.get('tcp_443')}, 6568={filters.get('tcp_6568')}, warp={filters.get('tcp_warp')}, all={filters.get('tcp_all_ports')}], "
        f"UDP=[443={filters.get('udp_443')}, all={filters.get('udp_all_ports')}], "
        f"raw=[discord={filters.get('raw_discord')}, stun={filters.get('raw_stun')}, wg={filters.get('raw_wireguard')}]", "DEBUG")

    return filters


# ===================== BASE ARGS BUILDING =====================

def _build_base_args_from_filters(
    lua_init: str,
    windivert_filter_folder: str,
    tcp_80: bool,
    tcp_443: bool,
    tcp_6568: bool,
    tcp_warp: bool,
    tcp_all_ports: bool,
    udp_443: bool,
    udp_all_ports: bool,
    raw_discord_media: bool,
    raw_stun: bool,
    raw_wireguard: bool,
) -> str:
    """
    Builds base WinDivert arguments from individual filters.

    Logic:
    - TCP ports are intercepted entirely via --wf-tcp-out
    - UDP ports are intercepted entirely via --wf-udp-out (high CPU load!)
    - Raw-part filters intercept only specific packets (save CPU)
    """
    parts = [lua_init]

    # === TCP ports ===
    tcp_port_parts = []
    if tcp_80:
        tcp_port_parts.append("80")
    if tcp_443:
        tcp_port_parts.append("443")
    if tcp_warp:
        tcp_port_parts.append("853")
    if tcp_6568:
        tcp_port_parts.append("6568")
    if tcp_all_ports:
        tcp_port_parts.append("444-65535")

    if tcp_port_parts:
        parts.append(f"--wf-tcp-out={','.join(tcp_port_parts)}")

    # === UDP ports ===
    udp_port_parts = []
    if udp_443:
        udp_port_parts.append("443")
    if udp_all_ports:
        udp_port_parts.append("444-65535")

    if udp_port_parts:
        parts.append(f"--wf-udp-out={','.join(udp_port_parts)}")

    # === Raw-part filters (save CPU) ===
    # These filters intercept only specific packets by signature

    if raw_discord_media:
        filter_path = os.path.join(windivert_filter_folder, "windivert_part.discord_media.txt")
        parts.append(f"--wf-raw-part=@{filter_path}")

    if raw_stun:
        filter_path = os.path.join(windivert_filter_folder, "windivert_part.stun.txt")
        parts.append(f"--wf-raw-part=@{filter_path}")

    if raw_wireguard:
        filter_path = os.path.join(windivert_filter_folder, "windivert_part.wireguard.txt")
        parts.append(f"--wf-raw-part=@{filter_path}")

    result = " ".join(parts)
    log(f"Built base args: TCP=[80={tcp_80}, 443={tcp_443}, all={tcp_all_ports}], "
        f"UDP=[443={udp_443}, all={udp_all_ports}], "
        f"raw=[discord={raw_discord_media}, stun={raw_stun}, wg={raw_wireguard}]", "DEBUG")

    return result


# ===================== SETTINGS APPLICATION =====================

def _apply_settings(args: str) -> str:
    """
    Applies all user settings to command line.

    Handles:
    - Remove --hostlist (apply to all sites)
    - Remove --ipset (apply to all IPs)
    - Add --wssize 1:6
    - Replace other.txt with allzone.txt
    """
    from strategy_menu import (
        get_remove_hostlists_enabled,
        get_remove_ipsets_enabled,
        get_wssize_enabled,
        get_allzone_hostlist_enabled
    )

    result = args

    # ==================== ALLZONE REPLACEMENT ====================
    # Do BEFORE hostlist removal so replacement works
    if get_allzone_hostlist_enabled():
        result = result.replace("--hostlist=other.txt", "--hostlist=allzone.txt")
        result = result.replace("--hostlist=other2.txt", "--hostlist=allzone.txt")
        log("Applied replacement other.txt -> allzone.txt", "DEBUG")

    # ==================== HOSTLIST REMOVAL ====================
    if get_remove_hostlists_enabled():
        # Remove all hostlist variants
        patterns = [
            r'--hostlist-domains=[^\s]+',
            r'--hostlist-exclude=[^\s]+',
            r'--hostlist=[^\s]+',
        ]
        for pattern in patterns:
            result = re.sub(pattern, '', result)

        # Clean extra spaces
        result = clean_spaces(result)
        log("Removed all --hostlist parameters", "DEBUG")

    # ==================== IPSET REMOVAL ====================
    if get_remove_ipsets_enabled():
        # Remove all ipset variants
        patterns = [
            r'--ipset-ip=[^\s]+',
            r'--ipset-exclude=[^\s]+',
            r'--ipset=[^\s]+',
        ]
        for pattern in patterns:
            result = re.sub(pattern, '', result)

        # Clean extra spaces
        result = clean_spaces(result)
        log("Removed all --ipset parameters", "DEBUG")

    # ==================== WSSIZE ADDITION ====================
    if get_wssize_enabled():
        # Add --wssize 1:6 for TCP 443
        # Find place after base arguments
        if "--wssize" not in result:
            # Insert after --wf-* arguments
            if "--wf-" in result:
                # Find end of wf arguments
                wf_end = 0
                for match in re.finditer(r'--wf-[^\s]+=[^\s]+', result):
                    wf_end = max(wf_end, match.end())

                if wf_end > 0:
                    result = result[:wf_end] + " --wssize 1:6" + result[wf_end:]
                else:
                    result = "--wssize 1:6 " + result
            else:
                result = "--wssize 1:6 " + result

            log("Added parameter --wssize 1:6", "DEBUG")

    # ==================== FINAL CLEANUP ====================
    result = clean_spaces(result)

    # Remove empty --new (if remaining after hostlist/ipset removal)
    result = re.sub(r'--new\s+--new', '--new', result)
    result = re.sub(r'\s+--new\s*$', '', result)  # Trailing --new
    result = re.sub(r'^--new\s+', '', result)  # Leading --new

    return result.strip()


# ===================== OUT-RANGE REPLACEMENT =====================

def _replace_out_range(args: str, value: int) -> str:
    """
    Replaces --out-range in strategy arguments.
    Removes existing --out-range and inserts new one after --filter-tcp/--filter-udp.
    """
    # Remove existing --out-range=...
    args = re.sub(r'--out-range=[^\s]+\s*', '', args)
    args = args.strip()

    # Insert new --out-range after --filter-tcp=... or --filter-udp=...
    # Find pattern --filter-tcp=... or --filter-udp=...
    match = re.search(r'(--filter-(?:tcp|udp|l7)=[^\s]+)', args)
    if match:
        insert_pos = match.end()
        args = args[:insert_pos] + f" --out-range=-d{value}" + args[insert_pos:]
    else:
        # If no filter, add at beginning
        args = f"--out-range=-d{value} {args}"

    return clean_spaces(args)


# ===================== MAIN FUNCTION =====================

def build_full_command(category_strategies: dict = None, **kwargs) -> dict:
    """
    Combines selected strategies into one command line with proper order.

    Applies all UI settings:
    - Base arguments (windivert)
    - Debug log (if enabled)
    - Remove hostlist (if enabled)
    - Remove ipset (if enabled)
    - Add wssize (if enabled)
    - Replace other.txt with allzone.txt (if enabled)

    Args:
        category_strategies: dict {category_key: strategy_id}
        **kwargs: alternative way to pass category selections

    Returns:
        dict with args, name, description, _active_categories, etc.
    """
    from strategy_menu.strategies_registry import registry

    # Determine category selections source
    if category_strategies is not None:
        log("Using category_strategies dict for build_full_command", "DEBUG")
    elif kwargs:
        log("Using kwargs for build_full_command", "DEBUG")
        category_strategies = kwargs
    else:
        log("Using default selections", "DEBUG")
        category_strategies = registry.get_default_selections()

    # ==================== BASE ARGUMENTS ====================
    from strategy_menu import get_debug_log_enabled
    from config import LUA_FOLDER, WINDIVERT_FILTER, LOGS_FOLDER

    # Lua libraries must load first (required for Zapret 2)
    # Load order is important:
    # 1. zapret-lib.lua - base functions
    # 2. zapret-antidpi.lua - desync functions
    # 3. custom_funcs.lua - user functions
    lua_lib_path = os.path.join(LUA_FOLDER, "zapret-lib.lua")
    lua_antidpi_path = os.path.join(LUA_FOLDER, "zapret-antidpi.lua")
    custom_funcs_path = os.path.join(LUA_FOLDER, "custom_funcs.lua")
    # Paths WITHOUT quotes - subprocess.Popen with list of args handles paths correctly
    LUA_INIT = f'--lua-init=@{lua_lib_path} --lua-init=@{lua_antidpi_path} --lua-init=@{custom_funcs_path}'

    # Automatically determine required filters by selected categories
    filters = calculate_required_filters(category_strategies)

    # Build base arguments from auto-detected filters
    base_args = _build_base_args_from_filters(
        LUA_INIT,
        WINDIVERT_FILTER,
        filters['tcp_80'],
        filters['tcp_443'],
        filters['tcp_6568'],
        filters['tcp_warp'],
        filters['tcp_all_ports'],
        filters['udp_443'],
        filters['udp_all_ports'],
        filters['raw_discord'],
        filters['raw_stun'],
        filters['raw_wireguard'],
    )

    # ==================== COLLECT ACTIVE CATEGORIES ====================
    category_keys_ordered = registry.get_all_category_keys_by_command_order()
    none_strategies = registry.get_none_strategies()

    # Collect active categories with their arguments
    active_categories = []  # [(category_key, args, category_info), ...]
    descriptions = []

    # Load out-range settings
    from strategy_menu import get_out_range_discord, get_out_range_youtube
    out_range_discord = get_out_range_discord()
    out_range_youtube = get_out_range_youtube()

    for category_key in category_keys_ordered:
        strategy_id = category_strategies.get(category_key)

        if not strategy_id:
            continue

        # Skip "none" strategies
        none_id = none_strategies.get(category_key)
        if strategy_id == none_id:
            continue

        # Get full arguments via registry (base_filter + technique)
        args = registry.get_strategy_args_safe(category_key, strategy_id)
        if args:
            # Replace out-range for Discord and YouTube categories
            if category_key == "discord" and out_range_discord > 0:
                args = _replace_out_range(args, out_range_discord)
            elif category_key == "discord_voice" and out_range_discord > 0:
                args = _replace_out_range(args, out_range_discord)
            elif category_key == "youtube" and out_range_youtube > 0:
                args = _replace_out_range(args, out_range_youtube)

            category_info = registry.get_category_info(category_key)
            active_categories.append((category_key, args, category_info))

            # Add to description
            strategy_name = registry.get_strategy_name_safe(category_key, strategy_id)
            if category_info:
                descriptions.append(f"{category_info.full_name}: {strategy_name}")

    # ==================== BUILD COMMAND LINE ====================
    # Collect category arguments with --new separators
    category_args_parts = []

    for i, (category_key, args, category_info) in enumerate(active_categories):
        category_args_parts.append(args)

        # Add --new only if:
        # 1. Category requires separator (needs_new_separator=True)
        # 2. And this is NOT the last active category
        is_last = (i == len(active_categories) - 1)
        if category_info and category_info.needs_new_separator and not is_last:
            category_args_parts.append("--new")

    # Deduplicate blobs: extract all --blob=... from categories,
    # remove duplicates and move to beginning of command line
    category_args_str = " ".join(category_args_parts)
    deduped_args = build_args_with_deduped_blobs([category_args_str])

    # Build final command line
    args_parts = []

    # ==================== DEBUG LOG ====================
    # Added at beginning of command line if enabled
    if get_debug_log_enabled():
        from datetime import datetime
        from log.log import cleanup_old_logs
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = f"zapret_winws2_debug_{timestamp}.log"
        log_path = os.path.join(LOGS_FOLDER, log_filename)
        # Create logs folder if it doesn't exist
        os.makedirs(LOGS_FOLDER, exist_ok=True)
        # Clean old logs (keep max 50)
        cleanup_old_logs(LOGS_FOLDER)
        args_parts.append(f"--debug=@{log_path}")
        log(f"Debug log enabled: {log_path}", "INFO")

    if base_args:
        args_parts.append(base_args)
    if deduped_args:
        args_parts.append(deduped_args)

    combined_args = " ".join(args_parts)

    # ==================== APPLY SETTINGS ====================
    combined_args = _apply_settings(combined_args)

    # ==================== FINALIZATION ====================
    combined_description = " | ".join(descriptions) if descriptions else "Custom combination"

    log(f"Created combined strategy: {len(combined_args)} chars, {len(active_categories)} categories", "DEBUG")

    return {
        "name": "Combined Strategy",
        "description": combined_description,
        "version": "1.0",
        "provider": "universal",
        "author": "Combined",
        "updated": "2024",
        "all_sites": True,
        "args": combined_args,
        "_is_builtin": True,
        "_active_categories": len(active_categories),
        **{f"_{key}_id": strategy_id for key, strategy_id in category_strategies.items()}
    }
