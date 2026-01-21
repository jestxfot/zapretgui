# preset_zapret2/strategy_inference.py
"""
Strategy ID inference from arguments.

This module provides functions to determine strategy_id from strategy arguments
when loading presets from files. This is needed because preset files store
args but not strategy_id, and UI needs to know which strategy is active.

Usage:
    from preset_zapret2.strategy_inference import infer_strategy_id_from_args

    strategy_id = infer_strategy_id_from_args(
        category_key="youtube",
        args="--lua-desync=multisplit:pos=1,midsld",
        protocol="tcp"
    )
"""

from typing import Dict, Optional


def normalize_args(args: str) -> str:
    """
    Normalizes strategy arguments for comparison.

    Normalization rules:
    - Strips whitespace from each line
    - Removes empty lines
    - Sorts lines (order doesn't matter)
    - Converts to lowercase (for case-insensitive comparison)

    Args:
        args: Raw strategy arguments (can be multiline)

    Returns:
        Normalized arguments string

    Example:
        Input:  "--lua-desync=multisplit:pos=1,midsld\n--lua-desync=disorder:pos=1"
        Output: "--lua-desync=disorder:pos=1\n--lua-desync=multisplit:pos=1,midsld"
    """
    if not args:
        return ""

    # Keep `--new` separators (some strategies are multi-block).
    blocks: list[list[str]] = [[]]
    for raw in args.strip().split("\n"):
        line = raw.strip()
        if not line:
            continue
        if line == "--new":
            blocks.append([])
            continue
        blocks[-1].append(line)

    # Sort lines inside each block (order inside block should not matter for matching)
    normalized_blocks = []
    for block in blocks:
        if not block:
            continue
        normalized_blocks.append("\n".join(sorted(block)).lower())

    return "\n--new\n".join(normalized_blocks)


def _get_strategy_type_for_category(category_key: str) -> Optional[str]:
    try:
        from .catalog import load_categories
        categories = load_categories()
        info = categories.get(category_key) or {}
        st = (info.get("strategy_type") or "").strip()
        return st or None
    except Exception:
        return None


def infer_strategy_id_from_args(
    category_key: str,
    args: str,
    protocol: str = "tcp"
) -> str:
    """
    Infers strategy_id from strategy arguments.

    This function is used when loading presets from files.
    Preset files contain args but not strategy_id.
    We need to reverse-lookup the strategy_id by comparing args.

    Algorithm:
    1. Normalize input args
    2. Get all strategies for the category
    3. For each strategy:
       - Get strategy["args"] (pure args, without base_filter)
       - Normalize
       - Compare with input
    4. Return first match or "none" if not found

    Args:
        category_key: Category name (e.g., "youtube", "discord")
        args: Strategy arguments from preset file
        protocol: Protocol ("tcp" or "udp") - used only for logging

    Returns:
        strategy_id if found, "none" otherwise

    Edge cases:
    - Empty args → "none"
    - Unknown category → "none"
    - No strategies for category → "none"
    - No matching strategy → "none" (not an error, just no match)

    Example:
        >>> infer_strategy_id_from_args(
        ...     "youtube",
        ...     "--lua-desync=multisplit:pos=1,midsld",
        ...     "tcp"
        ... )
        "youtube_tcp_split"
    """
    # Normalize input args
    normalized_input = normalize_args(args)

    # Empty args = none
    if not normalized_input:
        return "none"

    strategy_type = _get_strategy_type_for_category(category_key) or ("udp" if protocol == "udp" else "tcp")
    try:
        from .catalog import load_strategies
        strategies = load_strategies(strategy_type)
    except Exception:
        strategies = {}

    if not strategies:
        return "none"

    # Search for matching strategy
    for strategy_id, strategy_data in strategies.items():
        strategy_args = strategy_data.get("args", "")
        if not strategy_args:
            continue

        # Normalize strategy args
        normalized_strategy = normalize_args(strategy_args)

        # Compare
        if normalized_strategy == normalized_input:
            return strategy_id

    # Non-empty args that don't match any known strategy: keep category enabled in UI.
    return "custom"


def infer_strategy_ids_batch(
    categories: Dict[str, Dict[str, str]]
) -> Dict[str, str]:
    """
    Infers strategy_ids for multiple categories at once.

    Useful for bulk operations (e.g., loading entire preset).

    Args:
        categories: Dict of {category_key: {"tcp_args": "...", "udp_args": "..."}}

    Returns:
        Dict of {category_key: strategy_id}

    Note:
        For categories with both TCP and UDP, prefers TCP strategy_id.
        If TCP is empty or not found, tries UDP.
    """
    result = {}

    for cat_key, cat_data in categories.items():
        tcp_args = cat_data.get("tcp_args", "")
        udp_args = cat_data.get("udp_args", "")

        # Try TCP first
        if tcp_args:
            strategy_id = infer_strategy_id_from_args(cat_key, tcp_args, "tcp")
            if strategy_id != "none":
                result[cat_key] = strategy_id
                continue

        # Try UDP if TCP didn't work
        if udp_args:
            strategy_id = infer_strategy_id_from_args(cat_key, udp_args, "udp")
            result[cat_key] = strategy_id
        else:
            result[cat_key] = "none"

    return result
