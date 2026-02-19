#!/usr/bin/env python3
r"""Convert BAT strategy .txt files to Zapret 1 builtin presets.

One-time conversion tool. Reads .txt files from H:\Privacy\zapret\bat\,
parses winws.exe strategy blocks, adds --wf-tcp/--wf-udp capture filters,
sanitizes V2-only syntax, and writes to preset_zapret1/builtin_presets/.

Usage:
    python tools/convert_bat_to_presets.py
"""

import os
import re
import sys
from datetime import datetime
from pathlib import Path

BAT_DIR = Path(r"H:\Privacy\zapret\bat")
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "preset_zapret1" / "builtin_presets"

# V2-only args that winws (V1) doesn't support — remove from line
V2_ONLY_ARGS = {"--filter-l3=", "--filter-l7=", "--wf-tcp-out=", "--wf-udp-out=", "--lua-init="}

# Lines to skip entirely
SKIP_PATTERNS = {"@echo off", "@echo on", "rem ", "pause", "exit"}


def parse_ports_from_filter(line: str, protocol: str) -> set[str]:
    """Extract individual port specs from --filter-tcp=PORTS or --filter-udp=PORTS."""
    pattern = rf"--filter-{protocol}=([^\s]+)"
    match = re.search(pattern, line)
    if match:
        # Split comma-separated port specs to deduplicate
        return set(match.group(1).split(","))
    return set()


def extract_wf_ports(lines: list[str]) -> tuple[set[str], set[str]]:
    """Collect all TCP and UDP port specs across all strategy blocks."""
    tcp_ports = set()
    udp_ports = set()
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        tcp_ports.update(parse_ports_from_filter(stripped, "tcp"))
        udp_ports.update(parse_ports_from_filter(stripped, "udp"))
    return tcp_ports, udp_ports


def _sort_port_key(port: str) -> int:
    """Sort key for port specs — extract first numeric value for ordering."""
    m = re.match(r"(\d+)", port)
    return int(m.group(1)) if m else 0


def sanitize_line(line: str) -> str | None:
    """Sanitize a single strategy line. Returns None if line should be skipped."""
    stripped = line.strip()

    # Skip empty lines and comments
    if not stripped:
        return ""
    if stripped.startswith("#"):
        return stripped

    # Skip BAT-only commands
    lower = stripped.lower()
    for pat in SKIP_PATTERNS:
        if lower.startswith(pat):
            return None

    # Remove V2-only args from the line
    result = stripped
    for v2_arg in V2_ONLY_ARGS:
        # Remove the arg and its value (up to next space or end)
        result = re.sub(rf"\s*{re.escape(v2_arg)}[^\s]*", "", result)

    result = result.strip()
    if not result or result == "--new":
        return None

    return result


def convert_file(src_path: Path) -> str | None:
    """Convert a single BAT .txt file to preset format. Returns content or None."""
    try:
        raw = src_path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        print(f"  ERROR reading {src_path.name}: {e}")
        return None

    raw_lines = raw.splitlines()

    # Sanitize all lines
    clean_lines: list[str] = []
    for line in raw_lines:
        result = sanitize_line(line)
        if result is not None:
            clean_lines.append(result)

    # Remove leading/trailing empty lines
    while clean_lines and not clean_lines[0].strip():
        clean_lines.pop(0)
    while clean_lines and not clean_lines[-1].strip():
        clean_lines.pop()

    if not clean_lines:
        return None

    # Check if there are any actual strategy lines (non-comment, non-empty)
    has_strategy = any(
        l.strip() and not l.strip().startswith("#")
        for l in clean_lines
    )
    if not has_strategy:
        return None

    # Extract port specs for --wf-tcp/--wf-udp
    tcp_ports, udp_ports = extract_wf_ports(clean_lines)

    # Build --wf-tcp and --wf-udp lines
    wf_lines: list[str] = []
    if tcp_ports:
        wf_lines.append(f"--wf-tcp={','.join(sorted(tcp_ports, key=_sort_port_key))}")
    if udp_ports:
        wf_lines.append(f"--wf-udp={','.join(sorted(udp_ports, key=_sort_port_key))}")

    # If no ports found at all, default to 443
    if not wf_lines:
        wf_lines.append("--wf-tcp=443")
        wf_lines.append("--wf-udp=443")

    # Build preset name from filename
    name = src_path.stem

    # Build header
    header = f"""# Preset: {name}
# Created: 2026-02-19T00:00:00
# IconColor: #60cdff
# Description: Imported from bat/{src_path.name}"""

    # Combine: header + wf lines + blank line + strategy blocks
    parts = [header, ""]
    parts.extend(wf_lines)
    parts.append("")

    # Add strategy lines with proper --new separation
    prev_was_strategy = False
    for line in clean_lines:
        stripped = line.strip()
        if not stripped:
            # Empty line between blocks
            if prev_was_strategy:
                parts.append("")
            prev_was_strategy = False
            continue
        if stripped.startswith("#"):
            parts.append(stripped)
            prev_was_strategy = False
            continue
        # Strategy line
        parts.append(stripped)
        prev_was_strategy = True

    content = "\n".join(parts)
    # Ensure single trailing newline
    content = content.rstrip() + "\n"
    return content


def main():
    if not BAT_DIR.is_dir():
        print(f"ERROR: BAT directory not found: {BAT_DIR}")
        sys.exit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    txt_files = sorted(BAT_DIR.glob("*.txt"))
    print(f"Found {len(txt_files)} .txt files in {BAT_DIR}")

    converted = 0
    skipped = 0

    for src in txt_files:
        dest = OUTPUT_DIR / src.name
        # Skip Default.txt — it already exists
        if src.stem.lower() == "default":
            print(f"  SKIP (reserved name): {src.name}")
            skipped += 1
            continue

        content = convert_file(src)
        if content is None:
            print(f"  SKIP (empty after sanitize): {src.name}")
            skipped += 1
            continue

        dest.write_text(content, encoding="utf-8")
        converted += 1

    print(f"\nDone! Converted: {converted}, Skipped: {skipped}")
    print(f"Output: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
