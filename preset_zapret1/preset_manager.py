# preset_zapret1/preset_manager.py
"""High-level preset manager for Zapret 1 (direct_zapret1) mode."""

import os
import re
import shutil
from datetime import datetime
from pathlib import Path, PureWindowsPath
from typing import Callable, Dict, List, Optional

from log import log

from .preset_model import (
    CategoryConfigV1,
    DEFAULT_PRESET_ICON_COLOR,
    PresetV1,
    normalize_preset_icon_color_v1,
    validate_preset_v1,
)
from .preset_storage import (
    delete_preset_v1,
    get_active_preset_name_v1,
    get_active_preset_path_v1,
    get_preset_path_v1,
    get_presets_dir_v1,
    list_presets_v1,
    load_preset_v1,
    preset_exists_v1,
    rename_preset_v1,
    save_preset_v1,
    set_active_preset_name_v1,
)


class PresetManagerV1:
    """High-level manager for Zapret 1 preset operations."""

    def __init__(
        self,
        on_preset_switched: Optional[Callable[[str], None]] = None,
        on_dpi_reload_needed: Optional[Callable[[], None]] = None,
    ):
        self.on_preset_switched = on_preset_switched
        self.on_dpi_reload_needed = on_dpi_reload_needed
        self._active_preset_cache: Optional[PresetV1] = None
        self._active_preset_mtime: float = 0.0

    @staticmethod
    def _get_store():
        from .preset_store import get_preset_store_v1
        return get_preset_store_v1()

    def list_presets(self) -> List[str]:
        return self._get_store().get_preset_names()

    def preset_exists(self, name: str) -> bool:
        return self._get_store().preset_exists(name)

    def get_preset_count(self) -> int:
        return len(self._get_store().get_preset_names())

    def load_preset(self, name: str) -> Optional[PresetV1]:
        return self._get_store().get_preset(name)

    def load_all_presets(self) -> List[PresetV1]:
        store = self._get_store()
        all_presets = store.get_all_presets()
        return [all_presets[n] for n in sorted(all_presets.keys(), key=lambda s: s.lower())]

    def save_preset(self, preset: PresetV1) -> bool:
        errors = validate_preset_v1(preset)
        if errors:
            log(f"V1 preset validation failed: {errors}", "WARNING")
        result = save_preset_v1(preset)
        if result:
            self.invalidate_preset_cache(preset.name)
        return result

    def get_active_preset_name(self) -> Optional[str]:
        try:
            return self._get_store().get_active_preset_name()
        except Exception:
            return get_active_preset_name_v1()

    def get_active_preset(self) -> Optional[PresetV1]:
        if self._active_preset_cache is not None:
            current_mtime = self._get_active_file_mtime()
            if current_mtime == self._active_preset_mtime and current_mtime > 0:
                return self._active_preset_cache

        preset = self._load_from_active_file()
        if not preset:
            name = get_active_preset_name_v1()
            if name and preset_exists_v1(name):
                preset = load_preset_v1(name)

        if preset:
            self._active_preset_cache = preset
            self._active_preset_mtime = self._get_active_file_mtime()

        return preset

    def _load_from_active_file(self) -> Optional[PresetV1]:
        from .txt_preset_parser import parse_preset_file
        from .preset_model import PresetV1, CategoryConfigV1

        active_path = get_active_preset_path_v1()
        if not active_path.exists():
            return None

        try:
            data = parse_preset_file(active_path)
            name = data.active_preset or data.name
            if name == "Unnamed":
                name = "Current"

            preset = PresetV1(name=name, base_args=data.base_args)
            preset.icon_color = self._extract_icon_color_from_header(data.raw_header)

            for block in data.categories:
                cat_name = block.category
                if cat_name not in preset.categories:
                    preset.categories[cat_name] = CategoryConfigV1(
                        name=cat_name,
                        filter_mode=block.filter_mode,
                    )
                cat = preset.categories[cat_name]
                if block.protocol == "tcp":
                    cat.tcp_args = block.strategy_args
                    cat.tcp_port = block.port
                    cat.tcp_enabled = True
                    cat.filter_mode = block.filter_mode
                elif block.protocol == "udp":
                    cat.udp_args = block.strategy_args
                    cat.udp_port = block.port
                    cat.udp_enabled = True
                    if not cat.filter_mode:
                        cat.filter_mode = block.filter_mode

            # Infer strategy_id
            try:
                from .strategy_inference import infer_strategy_id_from_args
                for cat_name, cat in preset.categories.items():
                    if cat.tcp_args and cat.tcp_args.strip():
                        inferred = infer_strategy_id_from_args(
                            category_key=cat_name, args=cat.tcp_args,
                            protocol="tcp",
                        )
                        if inferred != "none":
                            cat.strategy_id = inferred
                            continue
                    if cat.udp_args and cat.udp_args.strip():
                        inferred = infer_strategy_id_from_args(
                            category_key=cat_name, args=cat.udp_args,
                            protocol="udp",
                        )
                        if inferred != "none":
                            cat.strategy_id = inferred
            except Exception:
                pass

            return preset
        except Exception as e:
            log(f"Error loading V1 active file: {e}", "ERROR")
            return None

    @staticmethod
    def _extract_icon_color_from_header(header: str) -> str:
        for line in (header or "").splitlines():
            match = re.match(r"#\s*(?:IconColor|PresetIconColor):\s*(.+)", line.strip(), re.IGNORECASE)
            if match:
                return normalize_preset_icon_color_v1(match.group(1).strip())
        return DEFAULT_PRESET_ICON_COLOR

    def _get_active_file_mtime(self) -> float:
        try:
            active_path = get_active_preset_path_v1()
            if active_path.exists():
                return os.path.getmtime(str(active_path))
            return 0.0
        except Exception:
            return 0.0

    def _invalidate_active_preset_cache(self) -> None:
        self._active_preset_cache = None
        self._active_preset_mtime = 0.0

    def invalidate_preset_cache(self, name: Optional[str] = None) -> None:
        store = self._get_store()
        if name is None:
            store.refresh()
        else:
            store.notify_preset_saved(name)

    def _notify_list_changed(self) -> None:
        self._get_store().notify_presets_changed()

    def switch_preset(self, name: str, reload_dpi: bool = True) -> bool:
        preset_path = get_preset_path_v1(name)
        active_path = get_active_preset_path_v1()

        if not preset_path.exists():
            log(f"Cannot switch V1: preset '{name}' not found", "ERROR")
            return False

        try:
            temp_path = active_path.with_suffix('.tmp')
            shutil.copy2(preset_path, temp_path)
            self._add_active_preset_marker(temp_path, name)

            import time
            try:
                os.replace(str(temp_path), str(active_path))
            except PermissionError:
                last_exc = None
                delay = 0.03
                fallback_tmp = None
                for _ in range(15):
                    time.sleep(delay)
                    try:
                        os.replace(str(temp_path), str(active_path))
                        last_exc = None
                        break
                    except PermissionError as e2:
                        last_exc = e2
                        delay = min(delay * 1.6, 0.2)
                if last_exc is not None:
                    # Atomic fallback: write to a second temp, then replace
                    import tempfile
                    try:
                        fd, fallback_tmp = tempfile.mkstemp(
                            dir=str(active_path.parent), suffix='.tmp2',
                        )
                        os.close(fd)
                        shutil.copy2(str(temp_path), fallback_tmp)
                        os.replace(fallback_tmp, str(active_path))
                    except Exception:
                        # Last resort: direct copy (non-atomic but better than crash)
                        shutil.copyfile(str(temp_path), str(active_path))
                        try:
                            if fallback_tmp:
                                os.unlink(fallback_tmp)
                        except Exception:
                            pass
                    try:
                        temp_path.unlink()
                    except Exception:
                        pass

            set_active_preset_name_v1(name)
            self._invalidate_active_preset_cache()
            self._get_store().notify_preset_switched(name)

            log(f"Switched V1 to preset '{name}'", "INFO")

            if self.on_preset_switched:
                self.on_preset_switched(name)
            if reload_dpi and self.on_dpi_reload_needed:
                self.on_dpi_reload_needed()

            return True

        except Exception as e:
            log(f"Error switching V1 preset: {e}", "ERROR")
            temp_path = active_path.with_suffix('.tmp')
            if temp_path.exists():
                temp_path.unlink()
            return False

    def _add_active_preset_marker(self, file_path: Path, preset_name: str) -> None:
        try:
            content = file_path.read_text(encoding='utf-8')
            lines = content.split('\n')
            active_idx = None
            for i, line in enumerate(lines):
                if line.strip().lower().startswith('# activepreset:'):
                    active_idx = i
                    break
            if active_idx is not None:
                lines[active_idx] = f"# ActivePreset: {preset_name}"
            else:
                insert_idx = 0
                for i, line in enumerate(lines):
                    if line.strip().lower().startswith('# preset:'):
                        insert_idx = i + 1
                        break
                lines.insert(insert_idx, f"# ActivePreset: {preset_name}")
            file_path.write_text('\n'.join(lines), encoding='utf-8')
        except Exception as e:
            log(f"Error adding V1 active preset marker: {e}", "WARNING")

    def create_preset(self, name: str, from_current: bool = True) -> Optional[PresetV1]:
        if preset_exists_v1(name):
            log(f"Cannot create V1: preset '{name}' already exists", "WARNING")
            return None
        try:
            if from_current:
                current = self._load_from_active_file()
                if current:
                    current.name = name
                    current.created = datetime.now().isoformat()
                    current.modified = datetime.now().isoformat()
                    if save_preset_v1(current):
                        self._notify_list_changed()
                        log(f"Created V1 preset '{name}' from current", "INFO")
                        return current
                    return None
                else:
                    return self.create_default_preset(name)
            else:
                return self.create_default_preset(name)
        except Exception as e:
            log(f"Error creating V1 preset: {e}", "ERROR")
            return None

    def create_default_preset(self, name: str = "Default") -> Optional[PresetV1]:
        if preset_exists_v1(name):
            log(f"Cannot create V1: preset '{name}' already exists", "WARNING")
            return None
        try:
            from .preset_defaults import get_builtin_preset_content_v1
            from .txt_preset_parser import parse_preset_content, generate_preset_file

            template = get_builtin_preset_content_v1("Default")
            if not template:
                log("No V1 default template found", "ERROR")
                return None

            data = parse_preset_content(template)
            data.name = name
            data.active_preset = None
            now = datetime.now().isoformat()
            icon_color = self._extract_icon_color_from_header(data.raw_header)
            data.raw_header = f"""# Preset: {name}
# Created: {now}
# Modified: {now}
# IconColor: {icon_color}
# Description: """

            dest_path = get_preset_path_v1(name)
            if not generate_preset_file(data, dest_path, atomic=True):
                return None

            self._notify_list_changed()
            log(f"Created V1 preset '{name}' from default template", "INFO")
            return self.load_preset(name)
        except Exception as e:
            log(f"Error creating V1 default preset: {e}", "ERROR")
            return None

    def delete_preset(self, name: str) -> bool:
        active_name = get_active_preset_name_v1()
        if active_name == name:
            log(f"Cannot delete active V1 preset '{name}'", "WARNING")
            return False
        result = delete_preset_v1(name)
        if result:
            self._notify_list_changed()
        return result

    def rename_preset(self, old_name: str, new_name: str) -> bool:
        if rename_preset_v1(old_name, new_name):
            if get_active_preset_name_v1() == old_name:
                set_active_preset_name_v1(new_name)
            self._notify_list_changed()
            return True
        return False

    def sync_preset_to_active_file(self, preset: PresetV1) -> bool:
        """Writes preset directly to preset-zapret1.txt."""
        import os as _os
        from .txt_preset_parser import PresetData, CategoryBlock, generate_preset_file

        active_path = get_active_preset_path_v1()

        try:
            data = PresetData(
                name=preset.name,
                active_preset=preset.name,
                base_args=preset.base_args,
            )

            icon_color = normalize_preset_icon_color_v1(getattr(preset, "icon_color", DEFAULT_PRESET_ICON_COLOR))
            preset.icon_color = icon_color
            data.raw_header = f"""# Preset: {preset.name}
# ActivePreset: {preset.name}
# Modified: {datetime.now().isoformat()}
# IconColor: {icon_color}"""

            for cat_name, cat in preset.categories.items():
                if cat.tcp_enabled and cat.has_tcp():
                    filter_file_relative = cat.get_hostlist_file() if cat.filter_mode == "hostlist" else cat.get_ipset_file()
                    filter_file = filter_file_relative.replace("\\", "/")
                    args_lines = [f"--filter-tcp={cat.tcp_port}"]
                    if cat.filter_mode in ("hostlist", "ipset"):
                        args_lines.append(f"--{cat.filter_mode}={filter_file}")
                    for raw in cat.tcp_args.splitlines():
                        line = raw.strip()
                        if line:
                            args_lines.append(line)
                    block = CategoryBlock(
                        category=cat_name, protocol="tcp",
                        filter_mode=cat.filter_mode, filter_file="",
                        port=cat.tcp_port, args='\n'.join(args_lines),
                        strategy_args=cat.tcp_args,
                    )
                    data.categories.append(block)

                if cat.udp_enabled and cat.has_udp():
                    filter_file_relative = cat.get_ipset_file() if cat.filter_mode == "ipset" else cat.get_hostlist_file()
                    from config import MAIN_DIRECTORY
                    filter_file = _os.path.normpath(_os.path.join(MAIN_DIRECTORY, filter_file_relative))
                    args_lines = [f"--filter-udp={cat.udp_port}"]
                    if cat.filter_mode in ("hostlist", "ipset"):
                        args_lines.append(f"--{cat.filter_mode}={filter_file}")
                    for raw in cat.udp_args.splitlines():
                        line = raw.strip()
                        if line:
                            args_lines.append(line)
                    block = CategoryBlock(
                        category=cat_name, protocol="udp",
                        filter_mode=cat.filter_mode, filter_file="",
                        port=cat.udp_port, args='\n'.join(args_lines),
                        strategy_args=cat.udp_args,
                    )
                    data.categories.append(block)

            data.deduplicate_categories()
            success = generate_preset_file(data, active_path, atomic=True)

            if success:
                self._invalidate_active_preset_cache()
                log("Synced V1 preset to active file", "DEBUG")
                if self.on_dpi_reload_needed:
                    self.on_dpi_reload_needed()

            return success

        except PermissionError as e:
            log(f"Cannot write V1 preset file: {e}", "ERROR")
            raise
        except Exception as e:
            log(f"Error syncing V1 preset to active file: {e}", "ERROR")
            return False

    @staticmethod
    def _render_template_for_preset(raw_template: str, target_name: str) -> str:
        """Rewrites # Preset / # ActivePreset headers for target preset name."""
        text = (raw_template or "").replace("\r\n", "\n").replace("\r", "\n")
        lines = text.split("\n")

        header_end = 0
        for i, raw in enumerate(lines):
            stripped = raw.strip()
            if stripped and not stripped.startswith("#"):
                header_end = i
                break
        else:
            header_end = len(lines)

        header = lines[:header_end]
        body = lines[header_end:]

        out_header: list[str] = []
        saw_preset = False
        saw_active = False

        for raw in header:
            stripped = raw.strip().lower()
            if stripped.startswith("# preset:"):
                out_header.append(f"# Preset: {target_name}")
                saw_preset = True
                continue
            if stripped.startswith("# activepreset:"):
                out_header.append(f"# ActivePreset: {target_name}")
                saw_active = True
                continue
            out_header.append(raw.rstrip("\n"))

        if not saw_preset:
            out_header.insert(0, f"# Preset: {target_name}")
        if not saw_active:
            insert_idx = 1 if out_header and out_header[0].strip().lower().startswith("# preset:") else 0
            out_header.insert(insert_idx, f"# ActivePreset: {target_name}")

        return "\n".join(out_header + body).rstrip("\n") + "\n"

    def reset_preset_to_default_template(
        self,
        preset_name: str,
        *,
        make_active: bool = True,
        sync_active_file: bool = True,
        emit_switched: bool = True,
        invalidate_templates: bool = True,
    ) -> bool:
        """Force-resets a preset to matching content from presets_v1_template/."""
        from .preset_defaults import (
            get_template_content_v1,
            get_default_template_content_v1,
            get_builtin_preset_content_v1,
            get_builtin_base_from_copy_name_v1,
            invalidate_templates_cache_v1,
        )

        name = (preset_name or "").strip()
        if not name:
            return False

        try:
            if not preset_exists_v1(name):
                log(f"Cannot reset V1: preset '{name}' not found", "ERROR")
                return False

            if invalidate_templates:
                try:
                    invalidate_templates_cache_v1()
                except Exception:
                    pass

            template_content = get_template_content_v1(name)
            if not template_content:
                base = get_builtin_base_from_copy_name_v1(name)
                if base:
                    template_content = get_template_content_v1(base)
            if not template_content:
                template_content = get_default_template_content_v1()
            if not template_content:
                template_content = get_builtin_preset_content_v1("Default")
            if not template_content:
                log(
                    "Cannot reset V1 preset: no templates found. "
                    "Expected at least one file in presets_v1_template/.",
                    "ERROR",
                )
                return False

            rendered_content = self._render_template_for_preset(template_content, name)

            preset_path = get_preset_path_v1(name)
            try:
                preset_path.parent.mkdir(parents=True, exist_ok=True)
                preset_path.write_text(rendered_content, encoding="utf-8")
            except PermissionError as e:
                log(f"Cannot write V1 preset file (locked?): {e}", "ERROR")
                raise
            except Exception as e:
                log(f"Error writing reset V1 preset '{name}': {e}", "ERROR")
                return False

            self.invalidate_preset_cache(name)

            do_sync = bool(sync_active_file)
            if do_sync and not make_active:
                try:
                    current_active = (get_active_preset_name_v1() or "").strip().lower()
                except Exception:
                    current_active = ""
                if current_active != name.lower():
                    do_sync = False

            if make_active:
                set_active_preset_name_v1(name)
                self._invalidate_active_preset_cache()

            if do_sync:
                try:
                    active_path = get_active_preset_path_v1()
                    active_path.parent.mkdir(parents=True, exist_ok=True)
                    active_path.write_text(rendered_content, encoding="utf-8")
                    self._invalidate_active_preset_cache()
                    if self.on_dpi_reload_needed:
                        self.on_dpi_reload_needed()
                except PermissionError as e:
                    log(f"Cannot write V1 active preset file (locked?): {e}", "ERROR")
                    raise
                except Exception as e:
                    log(f"Error syncing reset V1 preset '{name}' to active file: {e}", "ERROR")
                    return False

            if make_active:
                if emit_switched:
                    self._get_store().notify_preset_switched(name)
                    if self.on_preset_switched:
                        try:
                            self.on_preset_switched(name)
                        except Exception:
                            pass
                else:
                    try:
                        self._get_store().notify_active_name_changed()
                    except Exception:
                        pass

            return True

        except Exception as e:
            log(f"Error resetting V1 preset '{name}' to template: {e}", "ERROR")
            return False

    def reset_active_preset_to_default_template(self) -> bool:
        """Resets currently active V1 preset to its matching template."""
        active_name = (self.get_active_preset_name() or "").strip()
        if not active_name:
            return False
        return self.reset_preset_to_default_template(
            active_name,
            make_active=True,
            sync_active_file=True,
            emit_switched=True,
            invalidate_templates=True,
        )

    def reset_all_presets_to_default_templates(self) -> tuple[int, int, list[str]]:
        """Resets all V1 presets to templates and reapplies the active one."""
        from .preset_defaults import invalidate_templates_cache_v1, ensure_v1_templates_copied_to_presets

        success_count = 0
        total_count = 0
        failed: list[str] = []

        try:
            try:
                invalidate_templates_cache_v1()
                ensure_v1_templates_copied_to_presets()
            except Exception as e:
                log(f"V1 bulk reset: template refresh error: {e}", "DEBUG")

            try:
                self.invalidate_preset_cache(None)
            except Exception:
                pass

            names = sorted(self.list_presets(), key=lambda s: s.lower())
            total_count = len(names)
            if not names:
                return (0, 0, [])

            original_active = (self.get_active_preset_name() or "").strip()
            if original_active and original_active in names:
                names = [n for n in names if n != original_active] + [original_active]

            for name in names:
                ok = self.reset_preset_to_default_template(
                    name,
                    make_active=False,
                    sync_active_file=False,
                    emit_switched=False,
                    invalidate_templates=False,
                )
                if ok:
                    success_count += 1
                else:
                    failed.append(name)

            active_name = (original_active or (self.get_active_preset_name() or "")).strip()
            if active_name:
                if not self.switch_preset(active_name, reload_dpi=False):
                    log(f"V1 bulk reset: failed to re-apply active preset '{active_name}'", "WARNING")

            return (success_count, total_count, failed)
        except Exception as e:
            log(f"V1 bulk reset error: {e}", "ERROR")
            return (success_count, total_count, failed)

    def set_strategy_selection(self, category_key: str, strategy_id: str, save_and_sync: bool = True) -> bool:
        category_key = str(category_key or "").strip().lower()
        preset = self.get_active_preset()
        if not preset:
            log("Cannot set V1 strategy: no active preset", "WARNING")
            return False

        if category_key not in preset.categories:
            preset.categories[category_key] = CategoryConfigV1(name=category_key)

        preset.categories[category_key].strategy_id = strategy_id
        self._update_category_args_from_strategy(preset, category_key, strategy_id)
        preset.touch()

        if save_and_sync:
            return self._save_and_sync_preset(preset)
        return True

    @staticmethod
    def _selection_id_from_category(cat: CategoryConfigV1) -> str:
        """Return stable selection id for UI from category config."""
        sid = str(getattr(cat, "strategy_id", "") or "").strip().lower() or "none"
        if sid == "none":
            has_args = bool((getattr(cat, "tcp_args", "") or "").strip() or (getattr(cat, "udp_args", "") or "").strip())
            if has_args:
                # Args exist but strategy id couldn't be matched -> treat as custom.
                return "custom"
        return sid

    @staticmethod
    def _legacy_alias_targets(category_key: str, cat: CategoryConfigV1) -> list[str]:
        """Map legacy Zapret1 category keys to current registry categories."""
        key = str(category_key or "").strip().lower()
        has_tcp = bool((cat.tcp_args or "").strip())
        has_udp = bool((cat.udp_args or "").strip())

        targets: list[str] = []

        # Old classic Zapret1 keys.
        if key == "discord" and has_tcp:
            targets.append("discord_tcp")
        elif key == "discord_voice" and has_udp:
            targets.append("discord_voice_udp")
        elif key == "udp" and has_udp:
            targets.extend(["ipset_udp", "ipset_udp_all"])
        elif key == "http80" and has_tcp:
            targets.append("hostlist_80port")
        elif key == "youtube":
            if has_tcp:
                targets.append("youtube")
            if has_udp:
                targets.append("youtube_udp")
        elif key == "googlevideo" and has_tcp:
            targets.append("googlevideo_tcp")
        elif key == "google" and has_tcp:
            targets.append("google_tcp")

        # Legacy list-based keys from older presets.
        if key in ("list-google", "list_google") and has_tcp:
            targets.extend(["googlevideo_tcp", "google_tcp"])

        if key in ("list-general", "list_general", "general"):
            if has_tcp:
                targets.append("other")
            if has_udp:
                targets.append("youtube_udp")

        if key in ("all", "ipset-all", "ipset_all"):
            if has_tcp:
                targets.extend(["ipset", "ipset_all"])
            if has_udp:
                targets.extend(["ipset_udp", "ipset_udp_all"])

        # Deduplicate preserving order.
        unique: list[str] = []
        seen: set[str] = set()
        for t in targets:
            if t and t not in seen:
                seen.add(t)
                unique.append(t)
        return unique

    @staticmethod
    def _is_udp_protocol(protocol: str) -> bool:
        value = str(protocol or "").upper()
        return any(token in value for token in ("UDP", "QUIC", "L7", "RAW"))

    @staticmethod
    def _resolve_filter_file_path(filter_file: str) -> Path | None:
        raw = str(filter_file or "").strip().strip('"').strip("'")
        if not raw:
            return None

        if raw.startswith("@"):
            raw = raw[1:].strip()
        if not raw:
            return None

        win_path = PureWindowsPath(raw)

        candidates: list[Path] = []
        try:
            from config import MAIN_DIRECTORY

            main_dir = Path(MAIN_DIRECTORY)
        except Exception:
            main_dir = Path.cwd()

        path_obj = Path(win_path)
        if path_obj.is_absolute():
            candidates.append(path_obj)
        else:
            candidates.append(main_dir / path_obj)
            candidates.append(main_dir / "lists" / win_path.name)
            candidates.append(path_obj)

        for candidate in candidates:
            try:
                if candidate.exists() and candidate.is_file():
                    return candidate
            except Exception:
                continue

        return candidates[0] if candidates else None

    @staticmethod
    def _read_filter_text(filter_file: str) -> str:
        path = PresetManagerV1._resolve_filter_file_path(filter_file)
        if path is None:
            return ""
        try:
            return path.read_text(encoding="utf-8", errors="ignore").lower()
        except Exception:
            return ""

    def _infer_targets_from_filter_source(
        self,
        *,
        filter_mode: str,
        filter_file: str,
        protocol: str,
        known_keys: set[str],
        category_protocols: dict[str, str],
    ) -> list[str]:
        mode = str(filter_mode or "").strip().lower()
        proto_udp = self._is_udp_protocol(protocol)

        filename = PureWindowsPath(str(filter_file or "")).name.lower()
        stem = Path(filename).stem.lower()
        content = self._read_filter_text(filter_file)
        haystack = f"{stem}\n{content}"

        targets: list[str] = []

        # IPSet "all" profiles are intentionally broad and should map to broad groups.
        if mode == "ipset" and "all" in stem:
            if proto_udp:
                targets.extend(["ipset_udp", "ipset_udp_all"])
            else:
                targets.extend(["ipset", "ipset_all"])

        # Legacy list names from old Zapret1 presets.
        if mode == "hostlist" and stem in ("list-google", "list_google", "google"):
            targets.extend(["googlevideo_tcp", "youtube", "google_tcp"])
        if mode == "hostlist" and stem in ("list-general", "list_general", "general"):
            if proto_udp:
                targets.extend(["youtube_udp", "discord_voice_udp"])
            else:
                targets.extend(["other", "youtube", "googlevideo_tcp"])

        # Heuristics by list/ipset file name and content.
        keyword_map: tuple[tuple[tuple[str, ...], tuple[str, ...]], ...] = (
            (("googlevideo",), ("googlevideo_tcp",)),
            (("youtube", "youtu.be"), ("youtube", "youtube_udp")),
            (("google",), ("google_tcp",)),
            (("discord",), ("discord_tcp", "discord_voice_udp", "udp_discord", "update_discord")),
            (("telegram",), ("telegram_tcp",)),
            (("whatsapp",), ("whatsapp_tcp",)),
            (("facebook",), ("facebook_tcp",)),
            (("instagram",), ("instagram_tcp",)),
            (("twitter", "x.com"), ("twitter_tcp",)),
            (("github",), ("github_tcp",)),
            (("twitch",), ("twitch_tcp",)),
            (("steam",), ("steam_tcp",)),
            (("soundcloud",), ("soundcloud_tcp",)),
            (("rutracker",), ("rutracker_tcp",)),
            (("rutor",), ("rutor_tcp",)),
            (("roblox",), ("roblox_tcp", "roblox_udp")),
            (("amazon",), ("amazon_tcp", "amazon_udp")),
            (("claude",), ("claude_tcp",)),
            (("warp",), ("warp_tcp",)),
            (("speedtest",), ("speedtest_tcp",)),
            (("other", "blacklist", "general"), ("other",)),
        )

        for keywords, mapped in keyword_map:
            if any(keyword in haystack for keyword in keywords):
                targets.extend(mapped)

        # Fallback for generic files with no clear marker.
        if not targets and mode == "hostlist" and "general" in stem:
            if proto_udp:
                targets.append("youtube_udp")
            else:
                targets.append("other")

        # Keep only existing categories with matching protocol.
        filtered: list[str] = []
        seen: set[str] = set()
        for target in targets:
            if not target or target in seen or target not in known_keys:
                continue

            cat_proto = category_protocols.get(target, "")
            if cat_proto:
                if self._is_udp_protocol(cat_proto) != proto_udp:
                    continue

            seen.add(target)
            filtered.append(target)

        return filtered

    def _infer_selection_overrides_from_active_file(
        self,
        raw: dict[str, str],
        known_keys: set[str],
        category_protocols: dict[str, str],
    ) -> dict[str, str]:
        """Infer visible category selections from hostlist/ipset filters in active preset."""
        try:
            from .txt_preset_parser import parse_preset_file
        except Exception:
            return {}

        source_path = get_active_preset_path_v1()
        if not source_path.exists():
            active_name = get_active_preset_name_v1()
            if active_name and preset_exists_v1(active_name):
                source_path = get_preset_path_v1(active_name)

        if not source_path.exists():
            return {}

        try:
            data = parse_preset_file(source_path)
        except Exception:
            return {}

        overrides: dict[str, str] = {}
        for block in (data.categories or []):
            block_key = str(getattr(block, "category", "") or "").strip().lower()
            sid = raw.get(block_key, "none")
            if sid == "none" and str(getattr(block, "strategy_args", "") or "").strip():
                sid = "custom"
            if sid == "none":
                continue

            targets = self._infer_targets_from_filter_source(
                filter_mode=str(getattr(block, "filter_mode", "") or ""),
                filter_file=str(getattr(block, "filter_file", "") or ""),
                protocol=str(getattr(block, "protocol", "") or ""),
                known_keys=known_keys,
                category_protocols=category_protocols,
            )
            for target in targets:
                if overrides.get(target, "none") == "none":
                    overrides[target] = sid

        return overrides

    def get_strategy_selections(self) -> dict:
        preset = self.get_active_preset()
        if not preset:
            return {}

        raw: dict[str, str] = {}
        for key, cat in (preset.categories or {}).items():
            norm_key = str(key or "").strip().lower()
            if not norm_key:
                continue
            raw[norm_key] = self._selection_id_from_category(cat)

        try:
            from strategy_menu.strategies_registry import registry

            known_keys = set((registry.categories or {}).keys())
            category_protocols = {
                key: str(getattr(info, "protocol", "") or "")
                for key, info in (registry.categories or {}).items()
            }
        except Exception:
            return raw

        # Keep direct keys and add compatibility aliases for legacy presets.
        resolved: dict[str, str] = {}
        for key, sid in raw.items():
            if key in known_keys:
                resolved[key] = sid

        # Parser-based compatibility for legacy list-google/list-general/ipset-all blocks.
        inferred = self._infer_selection_overrides_from_active_file(
            raw=raw,
            known_keys=known_keys,
            category_protocols=category_protocols,
        )
        for key, sid in inferred.items():
            if resolved.get(key, "none") == "none":
                resolved[key] = sid

        for key, cat in (preset.categories or {}).items():
            norm_key = str(key or "").strip().lower()
            if not norm_key:
                continue
            sid = raw.get(norm_key, "none")
            for target in self._legacy_alias_targets(norm_key, cat):
                if target in known_keys:
                    resolved.setdefault(target, sid)

        # Keep unknown keys too (for compatibility with old callers).
        for key, sid in raw.items():
            resolved.setdefault(key, sid)

        return resolved

    def _update_category_args_from_strategy(self, preset: PresetV1, category_key: str, strategy_id: str) -> None:
        cat = preset.categories.get(category_key)
        if not cat:
            return
        if strategy_id == "none":
            cat.tcp_args = ""
            cat.udp_args = ""
            return

        from preset_zapret2.catalog import load_categories
        from preset_zapret1.strategies_loader import load_v1_strategies

        categories = load_categories()
        category_info = categories.get(category_key) or {}

        strategies = load_v1_strategies(category_key)
        args = (strategies.get(strategy_id) or {}).get("args", "") or ""

        if args:
            protocol = (category_info.get("protocol") or "").upper()
            is_udp = any(t in protocol for t in ("UDP", "QUIC", "L7", "RAW"))
            if is_udp:
                cat.udp_args = args
                cat.tcp_args = ""
            else:
                cat.tcp_args = args
                cat.udp_args = ""

    def _save_and_sync_preset(self, preset: PresetV1) -> bool:
        if preset.name and preset.name != "Current":
            save_preset_v1(preset)
            self.invalidate_preset_cache(preset.name)
        return self.sync_preset_to_active_file(preset)

    def ensure_presets_dir(self) -> Path:
        return get_presets_dir_v1()

    def get_active_preset_path(self) -> Path:
        return get_active_preset_path_v1()
