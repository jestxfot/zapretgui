# preset_zapret1/preset_manager.py
"""High-level preset manager for Zapret 1 (direct_zapret1) mode."""

import os
import re
import shutil
from datetime import datetime
from pathlib import Path
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
        from preset_zapret2.txt_preset_parser import parse_preset_file
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
                from strategy_menu.strategies_registry import get_current_strategy_set
                current_strategy_set = get_current_strategy_set()
            except Exception:
                current_strategy_set = None

            try:
                from preset_zapret2.strategy_inference import infer_strategy_id_from_args
                for cat_name, cat in preset.categories.items():
                    if cat.tcp_args and cat.tcp_args.strip():
                        inferred = infer_strategy_id_from_args(
                            category_key=cat_name, args=cat.tcp_args,
                            protocol="tcp", strategy_set=current_strategy_set,
                        )
                        if inferred != "none":
                            cat.strategy_id = inferred
                            continue
                    if cat.udp_args and cat.udp_args.strip():
                        inferred = infer_strategy_id_from_args(
                            category_key=cat_name, args=cat.udp_args,
                            protocol="udp", strategy_set=current_strategy_set,
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
            from preset_zapret2.txt_preset_parser import parse_preset_content, generate_preset_file

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
        from preset_zapret2.txt_preset_parser import PresetData, CategoryBlock, generate_preset_file

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
                    from config import MAIN_DIRECTORY
                    filter_file = _os.path.normpath(_os.path.join(MAIN_DIRECTORY, filter_file_relative))
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

    def get_strategy_selections(self) -> dict:
        preset = self.get_active_preset()
        if not preset:
            return {}
        return {key: cat.strategy_id for key, cat in preset.categories.items()}

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
