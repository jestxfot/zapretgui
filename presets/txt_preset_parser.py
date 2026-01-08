# presets/txt_preset_parser.py
"""
Parser for Zapret 2 txt preset files.

Parses preset-zapret2.txt into structured data and back.
Supports:
- Base args (lua-init, wf-*, blob=*)
- Category blocks separated by --new
- Category detection from --hostlist/--ipset
- Protocol detection from --filter-tcp/--filter-udp
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

from log import log


@dataclass
class CategoryBlock:
    """
    Represents a single category block in preset file.

    A block starts with --filter-tcp or --filter-udp and ends before --new or EOF.
    Category is extracted from --hostlist=xxx.txt or --ipset=xxx.txt.

    Attributes:
        category: Category name extracted from hostlist/ipset (e.g., "youtube", "discord")
        protocol: "tcp" or "udp" - from --filter-tcp/--filter-udp
        filter_mode: "hostlist" or "ipset" - which filter type is used
        filter_file: Full filename from filter (e.g., "youtube.txt")
        port: Port number from filter (e.g., "443")
        args: Full argument string for this block (including filter and strategy args)
        strategy_args: Just the strategy part (--lua-desync=... or --dpi-desync=...)
    """
    category: str
    protocol: str  # "tcp" or "udp"
    filter_mode: str  # "hostlist" or "ipset"
    filter_file: str  # "youtube.txt"
    port: str  # "443"
    args: str  # Full args string for the block
    strategy_args: str = ""  # Just strategy part (--lua-desync=...)

    def get_key(self) -> str:
        """Returns unique key for this block: category:protocol"""
        return f"{self.category}:{self.protocol}"


@dataclass
class PresetData:
    """
    Represents parsed preset file data.

    Attributes:
        name: Preset name from # Preset: line
        active_preset: Active preset name from # ActivePreset: line (for preset-zapret2.txt)
        base_args: Arguments before first --filter-* (lua-init, wf-*, blob=*)
        categories: List of category blocks
        raw_header: Raw header lines (comments at start)
        is_builtin: Whether this is a built-in preset (from # Builtin: line)
    """
    name: str = "Unnamed"
    active_preset: Optional[str] = None
    base_args: str = ""
    categories: List[CategoryBlock] = field(default_factory=list)
    raw_header: str = ""
    is_builtin: bool = False

    def get_category_block(self, category: str, protocol: str = "tcp") -> Optional[CategoryBlock]:
        """
        Finds category block by category name and protocol.

        Args:
            category: Category name (e.g., "youtube")
            protocol: "tcp" or "udp"

        Returns:
            CategoryBlock if found, None otherwise
        """
        for block in self.categories:
            if block.category == category and block.protocol == protocol:
                return block
        return None

    def get_all_categories(self) -> List[str]:
        """Returns list of unique category names"""
        return list(set(block.category for block in self.categories))

    def has_category(self, category: str) -> bool:
        """Checks if preset has this category (any protocol)"""
        return any(block.category == category for block in self.categories)


def extract_category_from_args(args: str) -> Tuple[str, str, str]:
    """
    Extracts category name, filter mode and filter file from args.

    Supports:
    - --hostlist=youtube.txt -> ("youtube", "hostlist", "youtube.txt")
    - --hostlist=youtube-hosts.txt -> ("youtube", "hostlist", "youtube-hosts.txt")
    - --ipset=discord.txt -> ("discord", "ipset", "discord.txt")
    - --hostlist=lists/youtube.txt -> ("youtube", "hostlist", "lists/youtube.txt")

    Args:
        args: Argument string to parse

    Returns:
        Tuple of (category, filter_mode, filter_file) or ("unknown", "", "")
    """
    # Match --hostlist=path/file.txt or --ipset=path/file.txt
    # Extract just the filename part for category detection
    match = re.search(r'--(hostlist|ipset)=([^\s]+)', args)
    if not match:
        return ("unknown", "", "")

    filter_mode = match.group(1)  # "hostlist" or "ipset"
    filter_path = match.group(2)  # full path or just filename

    # Get just the filename (remove path)
    filter_file = Path(filter_path).name

    # Extract category from filename (remove extension and common suffixes)
    # youtube.txt -> youtube
    # youtube-hosts.txt -> youtube
    # discord-ips.txt -> discord
    base_name = Path(filter_file).stem  # Remove .txt

    # Remove common suffixes
    suffixes_to_remove = ['-hosts', '-ips', '-ipset', '-hostlist', '_hosts', '_ips']
    category = base_name
    for suffix in suffixes_to_remove:
        if category.endswith(suffix):
            category = category[:-len(suffix)]
            break

    # Remove ipset- prefix (common for ipset files)
    # e.g., ipset-youtube.txt -> youtube
    if category.startswith('ipset-'):
        category = category[6:]  # Remove 'ipset-'

    return (category.lower(), filter_mode, filter_path)


def extract_protocol_and_port(args: str) -> Tuple[str, str]:
    """
    Extracts protocol and port from filter args.

    Args:
        args: Argument string

    Returns:
        Tuple of (protocol, port) - e.g., ("tcp", "443") or ("udp", "443")
    """
    # Check for --filter-tcp=port or --filter-udp=port
    tcp_match = re.search(r'--filter-tcp=(\d+)', args)
    if tcp_match:
        return ("tcp", tcp_match.group(1))

    udp_match = re.search(r'--filter-udp=(\d+)', args)
    if udp_match:
        return ("udp", udp_match.group(1))

    return ("tcp", "443")  # Default


def extract_strategy_args(args: str) -> str:
    """
    Extracts just the strategy arguments from block args.

    Removes --filter-*, --hostlist=*, --ipset=* to get just the strategy.

    Args:
        args: Full block arguments

    Returns:
        Strategy arguments only (e.g., "--lua-desync=multisplit:pos=1,midsld")
    """
    lines = args.strip().split('\n')
    strategy_lines = []

    for line in lines:
        line = line.strip()
        if not line:
            continue
        # Skip filter and hostlist/ipset lines
        if line.startswith('--filter-') or line.startswith('--hostlist=') or line.startswith('--ipset='):
            continue
        strategy_lines.append(line)

    return '\n'.join(strategy_lines)


def parse_preset_file(file_path: Path) -> PresetData:
    """
    Parses txt preset file into PresetData structure.

    File format:
    ```
    # Preset: My Config
    # ActivePreset: my_config

    --lua-init=@lua/zapret-lib.lua
    --wf-tcp-out=443
    --blob=tls7:@bin/tls_clienthello_7.bin

    --filter-tcp=443
    --hostlist=youtube.txt
    --lua-desync=multisplit:pos=1,midsld

    --new

    --filter-udp=443
    --hostlist=youtube.txt
    --lua-desync=fake:blob=quic1
    ```

    Args:
        file_path: Path to preset file

    Returns:
        PresetData with parsed content

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If file format is invalid
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"Preset file not found: {file_path}")

    try:
        content = file_path.read_text(encoding='utf-8')
    except Exception as e:
        log(f"Error reading preset file {file_path}: {e}", "ERROR")
        raise

    return parse_preset_content(content)


def parse_preset_content(content: str) -> PresetData:
    """
    Parses preset content string into PresetData.

    Args:
        content: Raw preset file content

    Returns:
        PresetData with parsed content
    """
    data = PresetData()

    lines = content.split('\n')

    # Phase 1: Parse header comments
    header_lines = []
    content_start_idx = 0

    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith('#'):
            header_lines.append(line)

            # Extract preset name
            name_match = re.match(r'#\s*Preset:\s*(.+)', stripped, re.IGNORECASE)
            if name_match:
                data.name = name_match.group(1).strip()

            # Extract active preset
            active_match = re.match(r'#\s*ActivePreset:\s*(.+)', stripped, re.IGNORECASE)
            if active_match:
                data.active_preset = active_match.group(1).strip()

            # Also check "Strategy:" for compatibility
            strategy_match = re.match(r'#\s*Strategy:\s*(.+)', stripped, re.IGNORECASE)
            if strategy_match and data.name == "Unnamed":
                data.name = strategy_match.group(1).strip()

            # Extract builtin flag
            builtin_match = re.match(r'#\s*Builtin:\s*(.+)', stripped, re.IGNORECASE)
            if builtin_match:
                data.is_builtin = builtin_match.group(1).strip().lower() in ('true', 'yes', '1')

        elif stripped:
            # First non-comment, non-empty line
            content_start_idx = i
            break
        else:
            # Empty line in header
            header_lines.append(line)
            content_start_idx = i + 1

    data.raw_header = '\n'.join(header_lines)

    # Phase 2: Split into base_args and category blocks
    # Base args = everything before first --filter-* line
    # Category blocks = separated by --new

    remaining_lines = lines[content_start_idx:]

    # Find first --filter-* to split base_args
    first_filter_idx = None
    for i, line in enumerate(remaining_lines):
        stripped = line.strip()
        if stripped.startswith('--filter-tcp') or stripped.startswith('--filter-udp'):
            first_filter_idx = i
            break

    if first_filter_idx is None:
        # No category blocks, all is base_args
        data.base_args = '\n'.join(line for line in remaining_lines if line.strip())
        return data

    # Split base_args
    base_lines = remaining_lines[:first_filter_idx]
    data.base_args = '\n'.join(line.strip() for line in base_lines if line.strip())

    # Phase 3: Parse category blocks
    block_lines = remaining_lines[first_filter_idx:]

    # Split by --new
    blocks_raw = []
    current_block = []

    for line in block_lines:
        stripped = line.strip()
        if stripped == '--new':
            if current_block:
                blocks_raw.append(current_block)
                current_block = []
        elif stripped:
            current_block.append(stripped)

    # Don't forget last block
    if current_block:
        blocks_raw.append(current_block)

    # Parse each block
    for block_lines_list in blocks_raw:
        block_args = '\n'.join(block_lines_list)

        # Extract category info
        category, filter_mode, filter_file = extract_category_from_args(block_args)
        protocol, port = extract_protocol_and_port(block_args)
        strategy_args = extract_strategy_args(block_args)

        block = CategoryBlock(
            category=category,
            protocol=protocol,
            filter_mode=filter_mode,
            filter_file=filter_file,
            port=port,
            args=block_args,
            strategy_args=strategy_args
        )

        data.categories.append(block)

    log(f"Parsed preset '{data.name}': {len(data.categories)} category blocks", "DEBUG")

    return data


def generate_preset_content(data: PresetData, include_header: bool = True) -> str:
    """
    Generates preset file content from PresetData.

    Args:
        data: PresetData structure
        include_header: Whether to include header comments

    Returns:
        Generated preset file content
    """
    lines = []

    # Header
    if include_header:
        lines.append(f"# Preset: {data.name}")
        if data.active_preset:
            lines.append(f"# ActivePreset: {data.active_preset}")
        if data.is_builtin:
            lines.append("# Builtin: true")
        lines.append("")

    # Base args
    if data.base_args:
        for line in data.base_args.split('\n'):
            if line.strip():
                lines.append(line.strip())
        lines.append("")

    # Category blocks
    for i, block in enumerate(data.categories):
        # Add block args
        for line in block.args.split('\n'):
            if line.strip():
                lines.append(line.strip())

        # Add --new separator (except for last block)
        if i < len(data.categories) - 1:
            lines.append("")
            lines.append("--new")
            lines.append("")

    return '\n'.join(lines)


def generate_preset_file(data: PresetData, output_path: Path, atomic: bool = True) -> bool:
    """
    Generates and writes preset file from PresetData.

    Uses atomic write (temp file + rename) for safety.

    Args:
        data: PresetData structure
        output_path: Path to write file
        atomic: Use atomic write (temp + rename)

    Returns:
        True if successful
    """
    import os
    import tempfile

    output_path = Path(output_path)
    content = generate_preset_content(data)

    try:
        # Ensure directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if atomic:
            # Atomic write: write to temp file, then rename
            fd, temp_path = tempfile.mkstemp(
                suffix='.txt',
                prefix='preset_',
                dir=output_path.parent
            )
            try:
                with os.fdopen(fd, 'w', encoding='utf-8') as f:
                    f.write(content)

                # Atomic rename (on Windows, need to remove target first)
                if output_path.exists():
                    output_path.unlink()
                os.rename(temp_path, output_path)

            except Exception:
                # Cleanup temp file on error
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                raise
        else:
            # Direct write
            output_path.write_text(content, encoding='utf-8')

        log(f"Preset file written: {output_path}", "DEBUG")
        return True

    except Exception as e:
        log(f"Error writing preset file {output_path}: {e}", "ERROR")
        return False


def update_category_in_preset(
    file_path: Path,
    category: str,
    protocol: str,
    new_strategy_args: str
) -> bool:
    """
    Updates strategy arguments for a specific category in preset file.

    Preserves file structure, only modifies the strategy args for the category.

    Args:
        file_path: Path to preset file
        category: Category name (e.g., "youtube")
        protocol: "tcp" or "udp"
        new_strategy_args: New strategy arguments

    Returns:
        True if updated successfully
    """
    try:
        data = parse_preset_file(file_path)

        # Find the block
        block = data.get_category_block(category, protocol)
        if not block:
            log(f"Category {category}:{protocol} not found in preset", "WARNING")
            return False

        # Rebuild block args with new strategy
        new_args_lines = []

        # Keep filter line
        if protocol == "tcp":
            new_args_lines.append(f"--filter-tcp={block.port}")
        else:
            new_args_lines.append(f"--filter-udp={block.port}")

        # Keep hostlist/ipset line
        if block.filter_mode and block.filter_file:
            new_args_lines.append(f"--{block.filter_mode}={block.filter_file}")

        # Add new strategy args
        for line in new_strategy_args.strip().split('\n'):
            if line.strip():
                new_args_lines.append(line.strip())

        block.args = '\n'.join(new_args_lines)
        block.strategy_args = new_strategy_args.strip()

        # Write back
        return generate_preset_file(data, file_path)

    except Exception as e:
        log(f"Error updating category in preset: {e}", "ERROR")
        return False
