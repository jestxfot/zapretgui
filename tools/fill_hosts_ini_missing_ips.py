from __future__ import annotations

import argparse
from pathlib import Path


_SPECIAL_SECTIONS = {
    "dns",
    "static",
    "profiles",
    "selectedprofiles",
    "selectedstatic",
}

_MISSING_IP_MARKERS = {
    "-",
    "—",
    "none",
    "null",
    "off",
    "disabled",
    "откл",
    "откл.",
}


def _detect_hosts_ini_path() -> Path:
    root = Path(__file__).resolve().parent.parent
    local = root / "json" / "hosts.ini"
    return local


def _is_section_header(line: str) -> bool:
    s = (line or "").strip()
    return s.startswith("[") and s.endswith("]") and len(s) >= 3


def _parse_dns_profiles(lines: list[str]) -> list[str]:
    profiles: list[str] = []
    in_dns = False
    for raw in lines:
        line = raw.strip()
        if _is_section_header(line):
            in_dns = line[1:-1].strip().lower() == "dns"
            continue
        if not in_dns:
            continue
        if not line or line.startswith("#"):
            continue
        profiles.append(line)
    return profiles


def _infer_direct_profile_index(profile_names: list[str]) -> int | None:
    for i, name in enumerate(profile_names):
        s = (name or "").strip().lower()
        if not s:
            continue
        if "вкл. (активировать hosts)" in s or "no proxy" in s or "direct" in s:
            return i
    return None


def fill_missing_ips(text: str, profile_count: int, direct_idx: int | None) -> tuple[str, int, int]:
    lines = (text or "").splitlines(keepends=True)
    out: list[str] = []

    current_section: str | None = None
    changed_blocks = 0
    total_blocks = 0

    i = 0
    while i < len(lines):
        raw = lines[i]
        stripped = raw.strip()

        if _is_section_header(stripped):
            current_section = stripped[1:-1].strip()
            out.append(raw)
            i += 1
            continue

        if not current_section or current_section.strip().lower() in _SPECIAL_SECTIONS:
            out.append(raw)
            i += 1
            continue

        if not stripped or stripped.startswith("#"):
            out.append(raw)
            i += 1
            continue

        # Domain block: domain line, then up to N IP lines, ended by blank/comment/next section.
        domain_line = raw
        i += 1

        ip_values: list[str] = []
        while i < len(lines):
            nxt = lines[i]
            nxt_stripped = nxt.strip()
            if not nxt_stripped or nxt_stripped.startswith("#") or _is_section_header(nxt_stripped):
                break
            value = nxt_stripped
            if value.lower() in _MISSING_IP_MARKERS:
                value = ""
            ip_values.append(value)
            i += 1

        total_blocks += 1

        # Normalize length.
        if profile_count <= 0:
            out.append(domain_line)
            for v in ip_values:
                out.append((v if v else "-") + "\n")
            continue

        original = list(ip_values)
        if len(ip_values) < profile_count:
            ip_values.extend([""] * (profile_count - len(ip_values)))
        else:
            ip_values = ip_values[:profile_count]

        direct_ip = ""
        if direct_idx is not None and direct_idx < len(ip_values):
            direct_ip = (ip_values[direct_idx] or "").strip()

        fallback_default = next((v for v in ip_values if v and v.strip()), "")

        for idx in range(profile_count):
            if ip_values[idx]:
                continue
            if direct_ip and idx != direct_idx:
                ip_values[idx] = direct_ip
            elif fallback_default:
                ip_values[idx] = fallback_default

        if ip_values != (original + [""] * max(0, profile_count - len(original)))[
            :profile_count
        ]:
            changed_blocks += 1

        out.append(domain_line)
        for v in ip_values:
            out.append((v if v else "-") + "\n")

    return "".join(out), changed_blocks, total_blocks


def main() -> int:
    parser = argparse.ArgumentParser(description="Fill missing IP columns in hosts.ini catalog")
    parser.add_argument("--path", type=Path, default=None, help="Path to hosts.ini (defaults to project/json or ../zapret/json)")
    parser.add_argument("--no-backup", action="store_true", help="Do not create .bak copy before writing")
    args = parser.parse_args()

    path: Path = args.path if args.path else _detect_hosts_ini_path()
    if not path.exists():
        raise SystemExit(f"hosts.ini not found: {path}")

    text = path.read_text(encoding="utf-8", errors="replace")
    profiles = _parse_dns_profiles(text.splitlines())
    if not profiles:
        raise SystemExit("No [DNS] profiles found in hosts.ini")

    direct_idx = _infer_direct_profile_index(profiles)
    updated, changed_blocks, total_blocks = fill_missing_ips(text, len(profiles), direct_idx)

    if updated == text:
        print(f"No changes: {path}")
        return 0

    if not args.no_backup:
        backup = path.with_suffix(path.suffix + ".bak")
        if not backup.exists():
            backup.write_text(text, encoding="utf-8")
            print(f"Backup: {backup}")

    path.write_text(updated, encoding="utf-8")
    print(f"Updated: {path} (changed blocks: {changed_blocks}/{total_blocks})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
