from __future__ import annotations

import os
import sys
import configparser
import threading
from dataclasses import dataclass
from pathlib import Path

from safe_construct import safe_construct


class _CaseConfigParser(configparser.ConfigParser):
    """ConfigParser that preserves option key casing."""

    def optionxform(self, optionstr: str) -> str:  # type: ignore[override]
        return optionstr

def _log(msg: str, level: str = "INFO") -> None:
    """Отложенный импорт log (PyQt6) чтобы модуль можно было импортировать без GUI."""
    try:
        from log import log as _log_impl  # type: ignore
        _log_impl(msg, level)
    except Exception:
        print(f"[{level}] {msg}")


@dataclass(frozen=True)
class HostsCatalog:
    dns_profiles: list[str]
    services: dict[str, dict[str, list[str]]]
    service_order: list[str]


_SPECIAL_SECTIONS = {
    "dns",
    # meta sections from older formats (must not be treated as services)
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

_CACHE_LOCK = threading.RLock()
_CACHE: HostsCatalog | None = None
_CACHE_TEXT: str | None = None
_CACHE_SIG: tuple[int, int] | None = None  # (mtime_ns, size)
_CACHE_PATH: Path | None = None
_MISSING_CATALOG_LOGGED: bool = False


def _get_app_root() -> Path:
    """
    Возвращает корень приложения для поиска внешних файлов.

    - В source-режиме: корень репозитория (рядом с папкой `hosts/`).
    - В exe-сборке (PyInstaller frozen): папка, где лежит exe.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    # hosts/proxy_domains.py -> hosts/ -> project root
    return Path(__file__).resolve().parent.parent


def _get_catalog_hosts_ini_candidates() -> list[Path]:
    """
    Каталог доменов/профилей (без настроек пользователя).

    Канонический путь: `<app_root>/json/hosts.ini`:
    - source: `<repo>/json/hosts.ini`
    - exe: `<exe_dir>/json/hosts.ini`
    """
    root = _get_app_root()

    return [
        root / "json" / "hosts.ini",
    ]


def _get_catalog_hosts_ini_path() -> Path:
    candidates = _get_catalog_hosts_ini_candidates()
    for p in candidates:
        if p.exists():
            return p
    return candidates[0]


def _get_user_hosts_ini_path() -> Path:
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata) / "zapret" / "user_hosts.ini"
    return Path.home() / ".config" / "zapret" / "user_hosts.ini"


def _parse_bool(value: str) -> bool:
    v = (value or "").strip().lower()
    return v in ("1", "true", "yes", "y", "on", "enabled", "enable")


def get_hosts_catalog_ini_path() -> Path:
    return _get_catalog_hosts_ini_path()


def get_user_hosts_ini_path() -> Path:
    return _get_user_hosts_ini_path()


def _parse_hosts_ini(text: str) -> HostsCatalog:
    dns_profiles: list[str] = []
    services: dict[str, dict[str, list[str]]] = {}
    service_order: list[str] = []

    current_section: str | None = None
    pending_domain: str | None = None
    pending_ips: list[str] = []

    def ensure_service(service_name: str) -> None:
        if service_name not in services:
            services[service_name] = {}
            service_order.append(service_name)

    def flush_domain() -> None:
        nonlocal pending_domain, pending_ips
        if not current_section:
            pending_domain = None
            pending_ips = []
            return

        sec = current_section.strip()
        if not sec or sec.lower() in _SPECIAL_SECTIONS:
            pending_domain = None
            pending_ips = []
            return

        if pending_domain:
            ensure_service(sec)
            services[sec][pending_domain] = list(pending_ips)
        pending_domain = None
        pending_ips = []

    def flush_section() -> None:
        flush_domain()

    for raw in (text or "").splitlines():
        line = raw.strip()

        # Comments / empty
        if not line or line.startswith("#"):
            # Empty line ends current domain block in service sections.
            if current_section and current_section.strip().lower() not in _SPECIAL_SECTIONS:
                flush_domain()
            continue

        # Section header
        if line.startswith("[") and line.endswith("]"):
            flush_section()
            current_section = line[1:-1].strip()
            continue

        if not current_section:
            continue

        sec_norm = current_section.strip().lower()
        if sec_norm == "dns":
            dns_profiles.append(line)
            continue

        # Service section: support both catalog format and raw hosts lines.
        #
        # 1) Catalog format:
        #    domain.tld
        #    ip_for_profile_0
        #    ip_for_profile_1
        #    ...
        #
        # 2) Raw hosts lines:
        #    1.2.3.4 domain.tld
        #
        # Raw hosts lines are treated as direct-only entries (IP only in the "direct" profile column).
        parts = line.split()
        if len(parts) >= 2:
            ip_candidate = parts[0].strip()
            host_candidate = parts[1].strip()
            if (
                ip_candidate.count(".") == 3
                and all(p.isdigit() for p in ip_candidate.split("."))
                and host_candidate
            ):
                # We are switching mode: raw hosts lines don't belong to the pending domain block.
                flush_domain()

                # Strict direct-only support: we only place the IP into the explicit "direct" profile column.
                direct_idx: int | None = None
                for i, profile_name in enumerate(dns_profiles):
                    if _is_direct_profile_name(profile_name):
                        direct_idx = i
                        break

                ips = [""] * len(dns_profiles)
                if direct_idx is not None and direct_idx < len(ips):
                    ips[direct_idx] = ip_candidate

                # Store raw-host entries under their section, so UI can toggle a whole group.
                sec = current_section.strip()
                if sec and sec.lower() not in _SPECIAL_SECTIONS:
                    ensure_service(sec)
                    services[sec][host_candidate] = ips
                continue

        # Service section: domain line then N IP lines
        if pending_domain is None:
            pending_domain = line
            pending_ips = []
        else:
            ip_value = line
            if ip_value.strip().lower() in _MISSING_IP_MARKERS:
                ip_value = ""
            pending_ips.append(ip_value)

    flush_section()

    return HostsCatalog(
        dns_profiles=dns_profiles,
        services=services,
        service_order=service_order,
    )


def _get_path_sig(path: Path) -> tuple[int, int] | None:
    try:
        st = path.stat()
        mtime_ns = getattr(st, "st_mtime_ns", None)
        if mtime_ns is None:
            mtime_ns = int(st.st_mtime * 1_000_000_000)
        return (int(mtime_ns), int(st.st_size))
    except Exception:
        return None


def _select_catalog_path() -> tuple[Path, list[Path], bool]:
    candidates = _get_catalog_hosts_ini_candidates()
    existing = [p for p in candidates if p.exists()]
    if existing:
        return (existing[0], candidates, True)
    return (candidates[0], candidates, False)


def _load_catalog() -> HostsCatalog:
    global _CACHE, _CACHE_TEXT, _CACHE_SIG, _CACHE_PATH, _MISSING_CATALOG_LOGGED

    with _CACHE_LOCK:
        path, candidates, exists = _select_catalog_path()

        if not exists:
            if not _MISSING_CATALOG_LOGGED:
                _log(
                    "hosts.ini не найден. Ожидается внешний файл по одному из путей: "
                    + " | ".join(str(p) for p in candidates),
                    "WARNING",
                )
                _MISSING_CATALOG_LOGGED = True
        else:
            _MISSING_CATALOG_LOGGED = False

        sig = _get_path_sig(path) if path.exists() else None
        if (
            _CACHE is not None
            and _CACHE_PATH is not None
            and _CACHE_SIG is not None
            and sig is not None
            and _CACHE_PATH == path
            and _CACHE_SIG == sig
        ):
            return _CACHE

        try:
            text = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
        except Exception as e:
            _log(f"Не удалось прочитать hosts.ini: {e}", "WARNING")
            text = ""

        _CACHE_TEXT = text
        _CACHE = _parse_hosts_ini(text)
        _CACHE_SIG = sig
        _CACHE_PATH = path
        return _CACHE


def invalidate_hosts_catalog_cache() -> None:
    global _CACHE, _CACHE_TEXT, _CACHE_SIG, _CACHE_PATH
    with _CACHE_LOCK:
        _CACHE = None
        _CACHE_TEXT = None
        _CACHE_SIG = None
        _CACHE_PATH = None


def get_hosts_catalog_signature() -> tuple[str, int, int] | None:
    """
    Возвращает сигнатуру текущего каталога hosts.ini: (path, mtime_ns, size).
    None если файл отсутствует/не читается.
    """
    path, _candidates, _exists = _select_catalog_path()
    if not path.exists():
        return None
    sig = _get_path_sig(path)
    if sig is None:
        return None
    mtime_ns, size = sig
    return (str(path), mtime_ns, size)


def get_hosts_catalog_text() -> str:
    """Возвращает сырой текст каталога hosts.ini (с учётом кэша/инвалидции)."""
    _load_catalog()
    with _CACHE_LOCK:
        return _CACHE_TEXT or ""


def get_dns_profiles() -> list[str]:
    return list(_load_catalog().dns_profiles)


def get_all_services() -> list[str]:
    return list(_load_catalog().service_order)

def get_service_domain_names(service_name: str) -> list[str]:
    """Возвращает список доменов сервиса (без привязки к профилю)."""
    cat = _load_catalog()
    domains = cat.services.get(service_name, {}) or {}
    return list(domains.keys())


def get_service_domains(service_name: str) -> dict[str, str]:
    """Домены сервиса (IP по умолчанию = профиль 0)."""
    cat = _load_catalog()
    domains = cat.services.get(service_name, {}) or {}
    out: dict[str, str] = {}
    for domain, ips in domains.items():
        if ips and ips[0]:
            out[domain] = ips[0]
    return out


def get_service_available_dns_profiles(service_name: str) -> list[str]:
    """
    Возвращает список DNS-профилей, доступных для сервиса.

    Профиль доступен если ДЛЯ КАЖДОГО домена сервиса есть IP на этом индексе.
    """
    cat = _load_catalog()
    domains = cat.services.get(service_name, {}) or {}
    if not domains:
        return []

    available: list[str] = []
    for profile_index, profile_name in enumerate(cat.dns_profiles):
        ok = True
        for ips in domains.values():
            if not ips or profile_index >= len(ips) or not ips[profile_index]:
                ok = False
                break
        if ok:
            available.append(profile_name)
    return available


def _is_direct_profile_name(profile_name: str) -> bool:
    name = (profile_name or "").strip().lower()
    if not name:
        return False
    return (
        "вкл. (активировать hosts)" in name
        or "no proxy" in name
        or "direct" in name
    )


def _infer_direct_profile_index(cat: HostsCatalog) -> int | None:
    # First try: by name (stable for user renames of other profiles).
    for i, profile_name in enumerate(cat.dns_profiles):
        if _is_direct_profile_name(profile_name):
            return i

    # Fallback: choose profile column with the most distinct IPs across the whole catalog.
    if not cat.dns_profiles:
        return None

    distinct: list[set[str]] = [set() for _ in cat.dns_profiles]
    for domains in (cat.services or {}).values():
        for ips in (domains or {}).values():
            for idx, ip in enumerate((ips or [])[: len(distinct)]):
                ip = (ip or "").strip()
                if ip:
                    distinct[idx].add(ip)

    best_idx = 0
    best_count = -1
    for idx, values in enumerate(distinct):
        if len(values) > best_count:
            best_count = len(values)
            best_idx = idx
    return best_idx


def _get_proxy_profile_indices(cat: HostsCatalog) -> list[int]:
    direct_idx = _infer_direct_profile_index(cat)
    if direct_idx is None:
        return list(range(len(cat.dns_profiles)))
    return [i for i in range(len(cat.dns_profiles)) if i != direct_idx]


def _service_has_proxy_ips(cat: HostsCatalog, service_name: str) -> bool:
    """
    True если у сервиса есть ХОТЯ БЫ ОДИН домен с IP в proxy/hide колонках.

    Proxy/hide колонки определяются автоматически (все профили кроме "direct"/"Вкл. (активировать hosts)").
    """
    domains = cat.services.get(service_name, {}) or {}
    if not domains:
        return False

    direct_idx = _infer_direct_profile_index(cat)
    proxy_indices = [i for i in range(len(cat.dns_profiles)) if direct_idx is None or i != direct_idx]
    if not proxy_indices:
        return False

    for ips in domains.values():
        direct_ip = ""
        if direct_idx is not None and ips and direct_idx < len(ips):
            direct_ip = (ips[direct_idx] or "").strip()
        for idx in proxy_indices:
            if not ips or idx >= len(ips):
                continue
            ip = (ips[idx] or "").strip()
            if not ip:
                continue
            # Do not treat copies of the "direct" column as proxy/hide IPs.
            if direct_ip and ip == direct_ip:
                continue
            return True
    return False


def get_service_has_geohide_ips(service_name: str) -> bool:
    """
    Back-compat API for UI: returns True if service has proxy/hide IPs.

    Note: historically this was tied to GeoHide DNS naming, but now detection is name-agnostic
    to support user-renamed DNS profile titles.
    """
    return _service_has_proxy_ips(_load_catalog(), service_name)


def get_service_domain_ip_map(service_name: str, profile_name: str) -> dict[str, str]:
    """Возвращает {domain: ip} для сервиса под выбранный профиль, или {} если профиль неполный."""
    cat = _load_catalog()
    if profile_name not in cat.dns_profiles:
        return {}
    profile_index = cat.dns_profiles.index(profile_name)

    domains = cat.services.get(service_name, {}) or {}
    out: dict[str, str] = {}
    for domain, ips in domains.items():
        if not ips or profile_index >= len(ips) or not ips[profile_index]:
            return {}
        out[domain] = ips[profile_index]
    return out


def load_user_hosts_selection() -> dict[str, str]:
    """
    Возвращает выбор пользователя: {service_name: profile_name}.

    Хранится отдельно от каталога доменов в `%APPDATA%/zapret/user_hosts.ini`.
    """
    user_path = get_user_hosts_ini_path()
    path = user_path
    migrate_to_new_path = False

    if not user_path.exists():
        # Back-compat: earlier builds could store the selection in `%APPDATA%/zapret/hosts.ini`.
        legacy_path = user_path.with_name("hosts.ini")
        if legacy_path.exists():
            try:
                with legacy_path.open("r", encoding="utf-8", errors="replace") as f:
                    sample = f.read(64 * 1024).lower()
                if "[profiles]" in sample or "[selectedprofiles]" in sample:
                    path = legacy_path
                    migrate_to_new_path = True
            except Exception:
                pass

    if not path.exists():
        return {}

    try:
        parser = safe_construct(_CaseConfigParser, strict=False)
        parser.read(path, encoding="utf-8")
    except Exception as e:
        _log(f"Не удалось прочитать user_hosts.ini: {e}", "WARNING")
        return {}

    section = None
    if parser.has_section("profiles"):
        section = "profiles"
    elif parser.has_section("SelectedProfiles"):
        # compatibility
        section = "SelectedProfiles"

    if not section:
        return {}

    out: dict[str, str] = {}
    for service_name, profile_name in parser.items(section):
        service_name = (service_name or "").strip()
        profile_name = (profile_name or "").strip()
        if service_name and profile_name:
            out[service_name] = profile_name

    if migrate_to_new_path and out:
        save_user_hosts_selection(out)
    return out


def save_user_hosts_selection(selected_profiles: dict[str, str]) -> bool:
    """Сохраняет выбор пользователя в `%APPDATA%/zapret/user_hosts.ini`."""
    path = get_user_hosts_ini_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)

        parser = safe_construct(_CaseConfigParser)
        parser["profiles"] = {}

        for service_name in sorted((selected_profiles or {}).keys(), key=lambda s: s.lower()):
            profile_name = (selected_profiles.get(service_name) or "").strip()
            service_name = (service_name or "").strip()
            if service_name and profile_name:
                parser["profiles"][service_name] = profile_name

        with path.open("w", encoding="utf-8") as f:
            f.write("# Zapret GUI: hosts selection\n")
            parser.write(f)
        return True
    except Exception as e:
        _log(f"Не удалось сохранить user_hosts.ini: {e}", "WARNING")
        return False


# ═══════════════════════════════════════════════════════════════
# UI hints (иконки/цвета) — без доменов и IP
# Формат: (иконка_qtawesome, название, цвет_иконки)
# ═══════════════════════════════════════════════════════════════

QUICK_SERVICES = [
    # AI сервисы
    ("fa5b.discord", "Discord TCP", "#5865f2"),
    ("fa5b.youtube", "YouTube TCP", "#ff0000"),
    ("fa5b.github", "GitHub TCP", "#181717"),
    ("fa5b.discord", "Discord Voice", "#5865f2"),
    ("mdi.robot", "ChatGPT", "#10a37f"),
    ("mdi.google", "Gemini", "#4285f4"),
    ("mdi.google", "Gemini AI", "#4285f4"),
    ("fa5s.brain", "Claude", "#cc9b7a"),
    ("fa5b.microsoft", "Copilot", "#00bcf2"),
    ("fa5b.twitter", "Grok", "#1da1f2"),
    ("fa5s.robot", "Manus", "#7c3aed"),
    # Соцсети
    ("fa5b.instagram", "Instagram", "#e4405f"),
    ("fa5b.facebook-f", "Facebook", "#1877f2"),
    ("mdi.at", "Threads", "#ffffff"),
    ("fa5b.tiktok", "TikTok", "#ff0050"),
    # Медиа и развлечения
    ("fa5b.spotify", "Spotify", "#1db954"),
    ("fa5s.film", "Netflix", "#e50914"),
    ("fa5b.twitch", "Twitch", "#9146ff"),
    ("fa5b.soundcloud", "SoundCloud", "#ff5500"),
    # Продуктивность
    ("fa5s.sticky-note", "Notion", "#ffffff"),
    ("fa5s.language", "DeepL", "#0f2b46"),
    ("fa5s.palette", "Canva", "#00c4cc"),
    ("fa5s.envelope", "ProtonMail", "#6d4aff"),
    # Разработка
    ("fa5s.microphone-alt", "ElevenLabs", "#ffffff"),
    ("fa5b.github", "GitHub Copilot", "#ffffff"),
    ("fa5s.code", "JetBrains", "#fe315d"),
    ("fa5s.bolt", "Codeium", "#09b6a2"),
    # Торренты
    ("fa5s.magnet", "RuTracker", "#3498db"),
    ("fa5s.magnet", "Rutor", "#e74c3c"),
    # Другое
    ("fa5s.images", "Pixabay", "#00ab6c"),
    ("fa5s.box-open", "Другое", "#6c757d"),
]
