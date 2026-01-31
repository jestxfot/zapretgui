from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.request import Request, urlopen

_IPV4_RE = re.compile(r"^(?:\d{1,3}\.){3}\d{1,3}$")


@dataclass(frozen=True)
class Catalog:
    dns_profiles: list[str]
    # services[service][domain] = list[str|None] of length == len(dns_profiles)
    services: dict[str, dict[str, list[str | None]]]


def _detect_geohide_dns_ips(lines: list[str]) -> list[str]:
    """
    Detect GeoHide DNS proxy IPs from the header of the GeoHide hosts file.

    Expected pattern:
      # Серверы ниже принадлежат GeoHide DNS:
      # 45.155.204.190
      # 95.182.120.241
    """
    for i, raw in enumerate(lines):
        line = (raw or "").strip().lower()
        if not line.startswith("#"):
            continue
        if "geohide dns" not in line:
            continue
        if "принадлежат" not in line and "belong" not in line:
            continue

        ips: list[str] = []
        for j in range(i + 1, min(i + 20, len(lines))):
            nxt = (lines[j] or "").strip()
            if not nxt.startswith("#"):
                break
            candidate = nxt.lstrip("#").strip()
            if _IPV4_RE.match(candidate):
                ips.append(candidate)
                continue
            if ips:
                break
        if ips:
            return ips
    return []


def _is_section_header_comment(text: str) -> bool:
    """
    Heuristic: treat comment lines like "# ChatGPT & Sora (OpenAI)" as a service header.

    We intentionally keep this permissive; non-service headers will just produce
    empty sections which are dropped.
    """
    s = (text or "").strip()
    if not s.startswith("#"):
        return False
    s = s.lstrip("#").strip()
    if not s:
        return False
    if s.lower().startswith("http"):
        return False
    # Skip obvious meta lines.
    meta_prefixes = (
        "последнее обновление",
        "домены взяты",
        "серверы ниже",
        "в итоговом hosts",
        "источники",
    )
    if s.lower().startswith(meta_prefixes):
        return False
    return True


def parse_hosts_as_catalog(
    text: str,
    *,
    profile_ips: list[str],
    profile_names: list[str] | None = None,
    include_non_profile_ips: bool = False,
    direct_profile_name: str = "Вкл. (активировать hosts)",
    warnings: list[str] | None = None,
) -> Catalog:
    if profile_names is None:
        profile_names = [f"DNS {ip}" for ip in profile_ips]
    if len(profile_names) != len(profile_ips):
        raise ValueError("profile_names must match profile_ips length")

    dns_profiles = list(profile_names)
    if include_non_profile_ips:
        dns_profiles.append(direct_profile_name)
    profile_count = len(dns_profiles)

    ip_to_profile_index = {ip: i for i, ip in enumerate(profile_ips)}
    direct_profile_index = len(profile_ips)

    services: dict[str, dict[str, list[str | None]]] = {}
    current_service = "Uncategorized"
    duplicate_overrides = 0

    for raw in (text or "").splitlines():
        line = (raw or "").strip()
        if not line:
            continue
        if line.startswith("#"):
            if _is_section_header_comment(line):
                current_service = line.lstrip("#").strip()
            continue

        parts = line.split()
        if len(parts) < 2:
            continue

        ip = parts[0].strip()
        domains = [p.strip().lower() for p in parts[1:] if p.strip() and not p.strip().startswith("#")]

        if not domains:
            continue

        # Skip common "noise" mappings by default.
        if ip in ("0.0.0.0", "127.0.0.1", "::1"):
            continue

        profile_index = ip_to_profile_index.get(ip)
        if profile_index is None:
            if not include_non_profile_ips:
                continue
            profile_index = direct_profile_index

        for domain in domains:
            if domain in ("localhost", "ip6-localhost"):
                continue

            svc = services.setdefault(current_service, {})
            entry = svc.get(domain)
            if entry is None:
                entry = [None] * profile_count
                svc[domain] = entry

            existing = entry[profile_index]
            if existing and existing != ip:
                duplicate_overrides += 1
                if warnings is not None and len(warnings) < 20:
                    warnings.append(
                        f"Duplicate mapping for {domain} in [{current_service}] / {dns_profiles[profile_index]}: "
                        f"{existing} -> {ip} (kept last)"
                    )

            entry[profile_index] = ip

    # Drop empty services.
    services = {k: v for k, v in services.items() if v}

    if warnings is not None and duplicate_overrides:
        warnings.insert(0, f"Duplicate overrides: {duplicate_overrides} (kept last)")

    return Catalog(dns_profiles=dns_profiles, services=services)


def _format_catalog_ini(catalog: Catalog) -> str:
    out: list[str] = []
    out.append("[DNS]")
    for name in catalog.dns_profiles:
        out.append(name)
    out.append("")

    # Stable ordering.
    for service_name in sorted(catalog.services.keys(), key=lambda s: s.lower()):
        out.append(f"[{service_name}]")
        domains = catalog.services[service_name]
        for domain in sorted(domains.keys()):
            out.append(domain)
            ips = domains[domain]
            for ip in ips:
                out.append(ip if ip else "-")
            out.append("")
        out.append("")

    return "\n".join(out).rstrip() + "\n"


def _read_input_text(input_arg: str) -> str:
    src = (input_arg or "").strip()
    if not src:
        return ""

    if src == "-":
        return sys.stdin.read()

    if src.startswith(("http://", "https://")):
        req = Request(src, headers={"User-Agent": "zapretgui-hosts-to-catalog"})
        with urlopen(req, timeout=30) as resp:
            data = resp.read()
        return data.decode("utf-8", errors="replace")

    path = Path(src)
    return path.read_text(encoding="utf-8", errors="replace")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Convert a hosts file (e.g. dns.geohide.ru) into zapretgui json/hosts.ini catalog format."
    )
    parser.add_argument(
        "--input",
        "-i",
        type=str,
        required=True,
        help="Path/URL to source hosts file, or '-' for stdin",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=None,
        help="Output path (default: stdout)",
    )
    parser.add_argument(
        "--geohide-auto",
        action="store_true",
        help="Auto-detect GeoHide DNS IPs from header comments (recommended for GeoHide file)",
    )
    parser.add_argument(
        "--profile-ip",
        action="append",
        default=[],
        help="Add a DNS profile IP (can be repeated). If not provided, use --geohide-auto.",
    )
    parser.add_argument(
        "--profile-name",
        action="append",
        default=[],
        help="Add a DNS profile name (can be repeated, must match count of --profile-ip).",
    )
    parser.add_argument(
        "--include-non-profile-ips",
        action="store_true",
        help="Also include IPs not matching profiles as an extra profile column (default off).",
    )

    args = parser.parse_args(argv)

    try:
        text = _read_input_text(args.input)
    except Exception as e:
        print(f"ERROR: cannot read {args.input}: {e}", file=sys.stderr)
        return 2

    lines = text.splitlines()

    profile_ips: list[str] = [str(x).strip() for x in (args.profile_ip or []) if str(x).strip()]
    if not profile_ips and args.geohide_auto:
        profile_ips = _detect_geohide_dns_ips(lines)

    if not profile_ips:
        print("ERROR: no profiles detected. Provide --profile-ip or --geohide-auto.", file=sys.stderr)
        return 2

    profile_names: list[str] | None = None
    if args.profile_name:
        if len(args.profile_name) != len(profile_ips):
            print("ERROR: --profile-name count must match --profile-ip count.", file=sys.stderr)
            return 2
        profile_names = list(args.profile_name)
    else:
        # Default: show IPs for clarity in UI
        profile_names = [f"GeoHide DNS ({ip})" if args.geohide_auto else f"DNS ({ip})" for ip in profile_ips]

    try:
        warnings: list[str] = []
        catalog = parse_hosts_as_catalog(
            text,
            profile_ips=profile_ips,
            profile_names=profile_names,
            include_non_profile_ips=bool(args.include_non_profile_ips),
            warnings=warnings,
        )
    except Exception as e:
        print(f"ERROR: parse failed: {e}", file=sys.stderr)
        return 2

    if warnings:
        for w in warnings:
            print(f"WARNING: {w}", file=sys.stderr)

    out_text = _format_catalog_ini(catalog)
    if args.output:
        try:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(out_text, encoding="utf-8")
        except Exception as e:
            print(f"ERROR: cannot write {args.output}: {e}", file=sys.stderr)
            return 2
    else:
        sys.stdout.write(out_text)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
