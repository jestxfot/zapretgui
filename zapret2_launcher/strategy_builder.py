# zapret2_launcher/strategy_builder.py
"""
Strategy list builder for Zapret 2 (winws2.exe).

Full version WITH:
- --lua-init (Lua library loading)
- --wf-tcp-out= (V2 syntax)
- --wf-udp-out= (V2 syntax)
- --wf-tcp-in= (orchestra mode)
- --out-range support

This module is designed specifically for Zapret 2 (winws2.exe) and does NOT
support Zapret 1 (winws.exe). For V1 compatibility, use strategy_lists_v1.py.
"""

import re
import os
from log import log
from strategy_menu.strategies_registry import registry
from launcher_common.blobs import build_args_with_deduped_blobs


# ==================== COMMON UTILITIES ====================

def calculate_required_filters(category_strategies: dict) -> dict:
    """
    Automatically calculates required port filters based on selected categories.

    Uses filters_config.py to determine which filters are needed.

    Args:
        category_strategies: dict {category_key: strategy_id}

    Returns:
        dict with filter flags
    """
    from launcher_common.port_filters import get_filter_for_category, FILTERS

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

    log(f"[V2] Auto-detected filters: TCP=[80={filters.get('tcp_80')}, 443={filters.get('tcp_443')}, "
        f"6568={filters.get('tcp_6568')}, warp={filters.get('tcp_warp')}, all={filters.get('tcp_all_ports')}], "
        f"UDP=[443={filters.get('udp_443')}, all={filters.get('udp_all_ports')}], "
        f"raw=[discord={filters.get('raw_discord')}, stun={filters.get('raw_stun')}, wg={filters.get('raw_wireguard')}]", "DEBUG")

    return filters


def _apply_settings(args: str) -> str:
    """
    Applies all user settings to the command line.

    Handles:
    - --hostlist removal (apply to all sites)
    - --ipset removal (apply to all IPs)
    - Adding --wssize 1:6
    - Replacing other.txt with allzone.txt
    """
    from strategy_menu import (
        get_remove_hostlists_enabled,
        get_remove_ipsets_enabled,
        get_wssize_enabled,
        get_allzone_hostlist_enabled
    )

    result = args

    # ==================== ALLZONE REPLACEMENT ====================
    # Do this BEFORE removing hostlist so replacement works
    if get_allzone_hostlist_enabled():
        result = result.replace("--hostlist=other.txt", "--hostlist=allzone.txt")
        result = result.replace("--hostlist=other2.txt", "--hostlist=allzone.txt")
        log("[V2] Applied replacement other.txt -> allzone.txt", "DEBUG")

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

        result = _clean_spaces(result)
        log("[V2] Removed all --hostlist parameters", "DEBUG")

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

        result = _clean_spaces(result)
        log("[V2] Removed all --ipset parameters", "DEBUG")

    # ==================== WSSIZE ADDITION ====================
    if get_wssize_enabled():
        # Add --wssize 1:6 for TCP 443
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

            log("[V2] Added --wssize 1:6 parameter", "DEBUG")

    # ==================== FINAL CLEANUP ====================
    result = _clean_spaces(result)

    # Remove empty --new (if left after hostlist/ipset removal)
    result = re.sub(r'--new\s+--new', '--new', result)
    result = re.sub(r'\s+--new\s*$', '', result)  # Trailing --new
    result = re.sub(r'^--new\s+', '', result)  # Leading --new

    return result.strip()


def _clean_spaces(text: str) -> str:
    """Cleans multiple spaces"""
    return ' '.join(text.split())


# ==================== V2-SPECIFIC FUNCTIONS ====================

def _build_base_args_v2(
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
    is_orchestra: bool = False,
) -> str:
    """
    Builds base WinDivert arguments for Zapret 2.

    Features:
    - --lua-init for Lua library loading (required for Zapret 2)
    - --wf-tcp-out= / --wf-udp-out= (V2 syntax)
    - --wf-tcp-in= for orchestra mode

    Args:
        lua_init: Lua initialization string (--lua-init=@path --lua-init=@path ...)
        windivert_filter_folder: Path to WinDivert filter files
        tcp_80: Enable TCP port 80 filter
        tcp_443: Enable TCP port 443 filter
        tcp_6568: Enable TCP port 6568 (AnyDesk) filter
        tcp_warp: Enable TCP WARP ports filter (443, 853)
        tcp_all_ports: Enable TCP all ports (444-65535) filter
        udp_443: Enable UDP port 443 (QUIC) filter
        udp_all_ports: Enable UDP all ports (444-65535) filter
        raw_discord_media: Enable Discord media raw-part filter
        raw_stun: Enable STUN raw-part filter
        raw_wireguard: Enable WireGuard raw-part filter
        is_orchestra: If True, adds --wf-tcp-in= for orchestra mode

    Returns:
        Base arguments string for Zapret 2
    """
    parts = []

    # Lua initialization is REQUIRED for Zapret 2
    parts.append(lua_init)

    # === TCP ports - V2 syntax ===
    tcp_port_parts = []
    if tcp_80:
        tcp_port_parts.append("80")
    if tcp_443:
        tcp_port_parts.append("443,1080,2053,2083,2087,2096,8443")
    if tcp_warp:
        tcp_port_parts.append("853")
    if tcp_6568:
        tcp_port_parts.append("6568")
    if tcp_all_ports:
        tcp_port_parts.append("444-65535")

    if tcp_port_parts:
        tcp_ports_str = ','.join(tcp_port_parts)
        # Zapret 2 uses --wf-tcp-out= (NOT --wf-tcp= like V1)
        parts.append(f"--wf-tcp-out={tcp_ports_str}")
        # For orchestra mode, also intercept incoming TCP
        if is_orchestra:
            parts.append(f"--wf-tcp-in={tcp_ports_str}")

    # === UDP ports - V2 syntax ===
    udp_port_parts = []
    if udp_443:
        udp_port_parts.append("443")
    if udp_all_ports:
        udp_port_parts.append("444-65535")

    if udp_port_parts:
        udp_ports_str = ','.join(udp_port_parts)
        # Zapret 2 uses --wf-udp-out= (NOT --wf-udp= like V1)
        parts.append(f"--wf-udp-out={udp_ports_str}")

    # === Raw-part filters (CPU-efficient) ===
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
    log(f"[V2] Built base args (orchestra={is_orchestra}): TCP=[80={tcp_80}, 443={tcp_443}, all={tcp_all_ports}], "
        f"UDP=[443={udp_443}, all={udp_all_ports}], "
        f"raw=[discord={raw_discord_media}, stun={raw_stun}, wg={raw_wireguard}]", "DEBUG")

    return result


def _replace_out_range(args: str, value: int) -> str:
    """
    Replaces --out-range in strategy arguments (V2 only).

    Removes existing --out-range and inserts new one after --filter-tcp/--filter-udp.

    NOTE: --out-range is ONLY available in Zapret 2 (winws2.exe).
    Zapret 1 (winws.exe) does NOT support this option.

    Args:
        args: Strategy arguments string
        value: Out-range value (will be formatted as -d{value})

    Returns:
        Arguments with replaced --out-range
    """
    # Remove existing --out-range=...
    args = re.sub(r'--out-range=[^\s]+\s*', '', args)
    args = args.strip()

    # Insert new --out-range after --filter-tcp=... or --filter-udp=... or --filter-l7=...
    match = re.search(r'(--filter-(?:tcp|udp|l7)=[^\s]+)', args)
    if match:
        insert_pos = match.end()
        args = args[:insert_pos] + f" --out-range=-d{value}" + args[insert_pos:]
    else:
        # If no filter, add at the beginning
        args = f"--out-range=-d{value} {args}"

    return _clean_spaces(args)


def combine_strategies_v2(is_orchestra: bool = False, **kwargs) -> dict:
    """
    Combines strategies for Zapret 2 (winws2.exe).

    Full version with:
    - Lua library support (--lua-init)
    - V2 WinDivert syntax (--wf-tcp-out=, --wf-udp-out=)
    - Orchestra mode support (--wf-tcp-in=)
    - --out-range support

    Args:
        is_orchestra: If True, enables orchestra mode with --wf-tcp-in=
        **kwargs: Category selections {category_key: strategy_id}

    Returns:
        Combined strategy dict with 'args', 'name', 'description', etc.

    Applies all settings from UI:
    - Base arguments (windivert)
    - Debug log (if enabled)
    - Hostlist removal (if enabled)
    - Ipset removal (if enabled)
    - Wssize addition (if enabled)
    - other.txt -> allzone.txt replacement (if enabled)
    """

    # Determine category selections source
    if kwargs:
        log("[V2] Using provided category strategies", "DEBUG")
        category_strategies = kwargs
    else:
        log("[V2] Using default selections", "DEBUG")
        category_strategies = registry.get_default_selections()

    # ==================== BASE ARGUMENTS ====================
    from strategy_menu import get_debug_log_enabled
    from config import LUA_FOLDER, WINDIVERT_FILTER, LOGS_FOLDER

    # Lua libraries must be loaded first (REQUIRED for Zapret 2)
    # Load order is important:
    # 1. zapret-lib.lua - base functions
    # 2. zapret-antidpi.lua - desync functions
    # 3. zapret-auto.lua - auto-detection helpers
    # 4. custom_funcs.lua - user custom functions
    lua_lib_path = os.path.join(LUA_FOLDER, "zapret-lib.lua")
    lua_antidpi_path = os.path.join(LUA_FOLDER, "zapret-antidpi.lua")
    lua_auto_path = os.path.join(LUA_FOLDER, "zapret-auto.lua")
    custom_funcs_path = os.path.join(LUA_FOLDER, "custom_funcs.lua")
    # Paths WITHOUT quotes - subprocess.Popen with list of args handles paths correctly
    LUA_INIT = f'--lua-init=@{lua_lib_path} --lua-init=@{lua_antidpi_path} --lua-init=@{lua_auto_path} --lua-init=@{custom_funcs_path}'

    # Auto-detect required filters based on selected categories
    filters = calculate_required_filters(category_strategies)

    # Build base arguments from auto-detected filters (V2 syntax)
    base_args = _build_base_args_v2(
        LUA_INIT,
        WINDIVERT_FILTER,
        filters['tcp_80'],
        filters['tcp_443'],
        filters.get('tcp_6568', False),
        filters.get('tcp_warp', False),
        filters['tcp_all_ports'],
        filters['udp_443'],
        filters['udp_all_ports'],
        filters.get('raw_discord', False),
        filters.get('raw_stun', False),
        filters.get('raw_wireguard', False),
        is_orchestra,
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
            # Apply out-range for Discord and YouTube categories (V2 only!)
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
    # remove duplicates and move to the beginning of command line
    category_args_str = " ".join(category_args_parts)
    deduped_args = build_args_with_deduped_blobs([category_args_str])

    # Build final command line
    args_parts = []

    # ==================== DEBUG LOG ====================
    # Added at the beginning of command line if enabled
    if get_debug_log_enabled():
        from datetime import datetime
        from log.log import cleanup_old_logs
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = f"zapret_winws2_debug_{timestamp}.log"
        log_path = os.path.join(LOGS_FOLDER, log_filename)
        # Create logs folder if it doesn't exist
        os.makedirs(LOGS_FOLDER, exist_ok=True)
        # Clean up old logs (keep max 50)
        cleanup_old_logs(LOGS_FOLDER)
        args_parts.append(f"--debug=@{log_path}")
        log(f"[V2] Debug log enabled: {log_path}", "INFO")

    if base_args:
        args_parts.append(base_args)
    if deduped_args:
        args_parts.append(deduped_args)

    combined_args = " ".join(args_parts)

    # ==================== APPLY SETTINGS ====================
    combined_args = _apply_settings(combined_args)

    # ==================== FINALIZE ====================
    combined_description = " | ".join(descriptions) if descriptions else "Custom combination"

    log(f"[V2] Created combined strategy: {len(combined_args)} chars, {len(active_categories)} categories, "
        f"orchestra={is_orchestra}", "DEBUG")

    return {
        "name": "Combined Strategy (V2)",
        "description": combined_description,
        "version": "2.0",
        "provider": "universal",
        "author": "Combined",
        "updated": "2024",
        "all_sites": True,
        "args": combined_args,
        "_is_builtin": True,
        "_is_v2": True,
        "_is_orchestra": is_orchestra,
        "_active_categories": len(active_categories),
        **{f"_{key}_id": strategy_id for key, strategy_id in category_strategies.items()}
    }


# ==================== HELPER FUNCTIONS ====================

def get_strategy_display_name(category_key: str, strategy_id: str) -> str:
    """Gets display name for a strategy"""
    if strategy_id == "none":
        return "Disabled"

    return registry.get_strategy_name_safe(category_key, strategy_id)


def get_active_categories_count(category_strategies: dict) -> int:
    """Counts the number of active categories"""
    none_strategies = registry.get_none_strategies()
    count = 0

    for category_key, strategy_id in category_strategies.items():
        if strategy_id and strategy_id != none_strategies.get(category_key):
            count += 1

    return count


def validate_category_strategies(category_strategies: dict) -> list:
    """
    Validates selected strategies.
    Returns list of errors (empty if all ok).
    """
    errors = []

    for category_key, strategy_id in category_strategies.items():
        if not strategy_id:
            continue

        if strategy_id == "none":
            continue

        # Check category exists
        category_info = registry.get_category_info(category_key)
        if not category_info:
            errors.append(f"Unknown category: {category_key}")
            continue

        # Check strategy exists
        args = registry.get_strategy_args_safe(category_key, strategy_id)
        if args is None:
            errors.append(f"Strategy '{strategy_id}' not found in category '{category_key}'")

    return errors


# ==================== EXPORTS ====================

__all__ = [
    # Main function
    'combine_strategies_v2',

    # Filter calculation
    'calculate_required_filters',

    # Helper functions
    'get_strategy_display_name',
    'get_active_categories_count',
    'validate_category_strategies',

    # Internal (for testing)
    '_build_base_args_v2',
    '_replace_out_range',
    '_apply_settings',
    '_clean_spaces',
]
