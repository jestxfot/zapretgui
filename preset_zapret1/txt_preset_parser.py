from __future__ import annotations

"""TXT preset parser for Zapret 1.

This module is intentionally self-contained and does not depend on
``preset_zapret2`` modules.
"""

import os
import re
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path, PureWindowsPath
from typing import Dict, List, Optional, Tuple

from log import log


@dataclass
class CategoryBlock:
    category: str
    protocol: str
    filter_mode: str
    filter_file: str
    port: str
    args: str
    strategy_args: str = ""
    syndata_dict: Optional[Dict] = None

    def get_key(self) -> str:
        return f"{self.category}:{self.protocol}"


@dataclass
class PresetData:
    name: str = "Unnamed"
    active_preset: Optional[str] = None
    base_args: str = ""
    categories: List[CategoryBlock] = field(default_factory=list)
    raw_header: str = ""

    def get_category_block(self, category: str, protocol: str = "tcp") -> Optional[CategoryBlock]:
        for block in self.categories:
            if block.category == category and block.protocol == protocol:
                return block
        return None

    def deduplicate_categories(self) -> None:
        seen: dict[str, int] = {}
        unique: list[CategoryBlock | None] = []
        for block in self.categories:
            key = block.get_key()
            if key in seen:
                unique[seen[key]] = None
            seen[key] = len(unique)
            unique.append(block)
        self.categories = [b for b in unique if b is not None]


def extract_category_from_args(args: str) -> Tuple[str, str, str]:
    match = re.search(r"--(hostlist|ipset)=([^\s]+)", args)
    if not match:
        if re.search(r"--hostlist-domains=([^\s]+)", args):
            return ("unknown", "hostlist", "")
        if re.search(r"--ipset-ip=([^\s]+)", args):
            return ("unknown", "ipset", "")
        return ("unknown", "", "")

    filter_mode = match.group(1).strip().lower()
    filter_path = match.group(2).strip().strip('"').strip("'")
    filename = PureWindowsPath(filter_path).name
    stem = Path(filename).stem.lower()

    for suffix in ("-hosts", "-ips", "-ipset", "-hostlist", "_hosts", "_ips"):
        if stem.endswith(suffix):
            stem = stem[: -len(suffix)]
            break

    if stem.startswith("ipset-"):
        stem = stem[6:]

    return (stem or "unknown", filter_mode, filter_path)


def extract_protocol_and_port(args: str) -> Tuple[str, str]:
    tcp_match = re.search(r"--filter-tcp=([\d,\-\*]+)", args)
    if tcp_match:
        return ("tcp", tcp_match.group(1))

    udp_match = re.search(r"--filter-udp=([\d,\-\*]+)", args)
    if udp_match:
        return ("udp", udp_match.group(1))

    l7_match = re.search(r"--filter-l7=([^\s\n]+)", args)
    if l7_match:
        return ("udp", l7_match.group(1))

    return ("tcp", "443")


def extract_strategy_args(
    args: str,
    *,
    category_key: Optional[str] = None,
    filter_mode: Optional[str] = None,
) -> str:
    _ = (category_key, filter_mode)
    strategy_lines: list[str] = []
    for raw in (args or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("--filter-"):
            continue
        if line.startswith("--hostlist=") or line.startswith("--hostlist-domains="):
            continue
        if line.startswith("--hostlist-exclude="):
            continue
        if line.startswith("--ipset=") or line.startswith("--ipset-ip="):
            continue
        if line.startswith("--ipset-exclude="):
            continue
        strategy_lines.append(line)
    return "\n".join(strategy_lines)


def parse_preset_file(file_path: Path) -> PresetData:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Preset file not found: {path}")
    content = path.read_text(encoding="utf-8", errors="ignore")
    return parse_preset_content(content)


def parse_preset_content(content: str) -> PresetData:
    data = PresetData()
    lines = (content or "").splitlines()

    header_lines: list[str] = []
    content_start_idx = 0

    for i, raw in enumerate(lines):
        stripped = raw.strip()
        if stripped.startswith("#"):
            header_lines.append(raw)

            name_match = re.match(r"#\s*Preset:\s*(.+)", stripped, re.IGNORECASE)
            if name_match:
                data.name = name_match.group(1).strip()

            active_match = re.match(r"#\s*ActivePreset:\s*(.+)", stripped, re.IGNORECASE)
            if active_match:
                data.active_preset = active_match.group(1).strip()

            strategy_match = re.match(r"#\s*Strategy:\s*(.+)", stripped, re.IGNORECASE)
            if strategy_match and data.name == "Unnamed":
                data.name = strategy_match.group(1).strip()
            continue

        if not stripped:
            header_lines.append(raw)
            content_start_idx = i + 1
            continue

        content_start_idx = i
        break

    data.raw_header = "\n".join(header_lines)

    remaining = lines[content_start_idx:]

    first_filter_idx = None
    for i, raw in enumerate(remaining):
        stripped = raw.strip()
        if stripped.startswith("--filter-tcp") or stripped.startswith("--filter-udp") or stripped.startswith("--filter-l7"):
            first_filter_idx = i
            break

    if first_filter_idx is None:
        data.base_args = "\n".join(line.strip() for line in remaining if line.strip())
        return data

    base_lines = remaining[:first_filter_idx]
    data.base_args = "\n".join(line.strip() for line in base_lines if line.strip())

    block_lines = remaining[first_filter_idx:]
    blocks_raw: list[list[str]] = []
    current_block: list[str] = []

    for raw in block_lines:
        stripped = raw.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            continue
        if stripped == "--new":
            if current_block:
                blocks_raw.append(current_block)
                current_block = []
            continue
        current_block.append(stripped)

    if current_block:
        blocks_raw.append(current_block)

    for block_lines_list in blocks_raw:
        block_args = "\n".join(block_lines_list)
        category, mode, filter_file = extract_category_from_args(block_args)
        if not mode:
            mode = "hostlist"
        protocol, port = extract_protocol_and_port(block_args)
        strategy_args = extract_strategy_args(block_args, category_key=category, filter_mode=mode)

        data.categories.append(
            CategoryBlock(
                category=category,
                protocol=protocol,
                filter_mode=mode,
                filter_file=filter_file,
                port=port,
                args=block_args,
                strategy_args=strategy_args,
            )
        )

    data.deduplicate_categories()
    return data


def generate_preset_content(data: PresetData, include_header: bool = True) -> str:
    lines: list[str] = []

    if include_header:
        raw_header = str(getattr(data, "raw_header", "") or "").strip()
        if raw_header:
            lines.extend(raw_header.splitlines())
            if lines and lines[-1].strip():
                lines.append("")
        else:
            lines.append(f"# Preset: {data.name}")
            if data.active_preset:
                lines.append(f"# ActivePreset: {data.active_preset}")
            lines.append("")

    if data.base_args:
        for raw in data.base_args.splitlines():
            line = raw.strip()
            if line:
                lines.append(line)
        lines.append("")

    for i, block in enumerate(data.categories or []):
        for raw in (block.args or "").splitlines():
            line = raw.strip()
            if line:
                lines.append(line)
        if i < len(data.categories) - 1:
            lines.append("")
            lines.append("--new")
            lines.append("")

    return "\n".join(lines)


def generate_preset_file(data: PresetData, output_path: Path, atomic: bool = True) -> bool:
    path = Path(output_path)
    content = generate_preset_content(data)

    try:
        path.parent.mkdir(parents=True, exist_ok=True)

        if not atomic:
            path.write_text(content, encoding="utf-8")
            return True

        fd, temp_path = tempfile.mkstemp(suffix=".txt", prefix="preset_", dir=str(path.parent))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(content)

            try:
                os.replace(temp_path, str(path))
            except PermissionError as e:
                if os.name != "nt":
                    raise
                last_exc = e
                delay = 0.03
                for _ in range(15):
                    time.sleep(delay)
                    try:
                        os.replace(temp_path, str(path))
                        last_exc = None
                        break
                    except PermissionError as e2:
                        last_exc = e2
                        delay = min(delay * 1.6, 0.2)

                if last_exc is not None:
                    path.write_text(content, encoding="utf-8")
                    try:
                        if os.path.exists(temp_path):
                            os.unlink(temp_path)
                    except Exception:
                        pass
        except Exception:
            try:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
            except Exception:
                pass
            raise

        return True
    except Exception as e:
        log(f"Error writing V1 preset file {path}: {e}", "ERROR")
        return False
