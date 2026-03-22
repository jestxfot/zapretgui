# Preset System Architecture (preset_zapret2/)

## Overview

This module handles parsing, loading, saving, and managing winws2 preset files.
Presets are text files with command-line arguments separated by `--new` markers.

## Key Data Flow

```
Preset .txt file
  -> txt_preset_parser.py: parse_preset_content()
  -> PresetData (list of CategoryBlock)
  -> preset_storage.py: load_preset()
  -> Preset model (dict of CategoryConfig + _raw_blocks for lossless save)
  -> preset_manager.py: sync_preset_to_active_file()
  -> Written back to preset-zapret2.txt
```

## Files

| File | Purpose |
|------|---------|
| `txt_preset_parser.py` | Parses .txt preset files. Key functions: `parse_preset_content()`, `extract_category_from_args()`, `_canonicalize_list_category_key()`, `infer_category_key_from_args()`, `generate_preset_content()` |
| `preset_storage.py` | Load/save presets to disk. `load_preset()` converts PresetData -> Preset model |
| `preset_model.py` | Data models: `Preset`, `CategoryConfig`, `SyndataSettings` |
| `preset_manager.py` | High-level preset operations. `sync_preset_to_active_file()` writes preset, `set_strategy_selection()` changes a category's strategy |
| `catalog.py` | Loads categories.txt and strategy catalog files |
| `base_filter.py` | Builds `--filter-tcp/udp --hostlist/--ipset` lines from category definitions |
| `strategy_inference.py` | `infer_strategy_id_from_args()` — reverse-lookup strategy ID by comparing args against catalog |
| `preset_defaults.py` | Template management for new presets |

## Preset File Format

```
# Preset: Name
# ActivePreset: Name
# BuiltinVersion: 2.12

--lua-init=@lua/zapret-lib.lua     # Lua init
--ctrack-disable=0                  # Global settings
--wf-tcp-out=80,443                 # WinDivert filters
--blob=tls_google:@bin/...          # Named binary blobs

--filter-tcp=80,443                 # Block 1: YouTube TCP
--hostlist=lists/youtube.txt
--out-range=-d8
--lua-desync=multisplit:pos=2,midsld-2

--new                               # Separator

--filter-udp=443                    # Block 2: YouTube QUIC/UDP
--ipset=lists/ipset-youtube.txt
--payload=all
--lua-desync=fake:repeats=6:blob=fake_default_quic
```

## Category Detection Pipeline

When parsing a block, the system determines which category it belongs to:

1. **extract_categories_from_args()** — finds `--hostlist=`, `--ipset=`, `--hostlist-domains=` in block args
2. **extract_category_from_args()** — extracts category key from filename/domain:
   - `--hostlist=lists/youtube.txt` -> `youtube`
   - `--ipset=lists/ipset-youtube.txt` -> `youtube` (strips `ipset-` prefix)
   - `--hostlist-domains=googlevideo.com` -> `googlevideo`
3. **_canonicalize_list_category_key()** — maps to canonical key using categories.txt:
   - Checks protocol variant FIRST: `youtube + udp` -> `youtube_udp`
   - Falls back to exact match: `youtube` -> `youtube`
4. **infer_category_key_from_args()** — fallback: token-set matching against `base_filter` fields

## Lossless Save (Raw Block Preservation)

When a single category is changed via UI, `sync_preset_to_active_file(changed_category=...)` uses raw block preservation:

- `Preset._raw_blocks`: `[(set_of_cat_keys, protocol, raw_text), ...]` — stored at load time
- Only the changed category's block is regenerated
- All other blocks are written back as raw text (lossless)
- Shared blocks (one `--new` block with multiple `--hostlist=`) trigger fallback to full regeneration

## Categories Definition

Categories are defined in `dist/json/strategies/builtin/categories.txt` (deployed to `%APPDATA%\zapret\json\strategies\builtin\categories.txt`).

Each category has: `base_filter`, `base_filter_hostlist`, `base_filter_ipset`, `strategy_type` (tcp/udp), `command_group`, etc.

## Important Patterns

- TCP categories use `--hostlist=` (domain-based), UDP categories use `--ipset=` (IP-based)
- `--hostlist-domains=` is inline domain list (no file), used for single-domain categories
- One `--new` block can have multiple `--hostlist=` lines = multiple categories sharing one block
- `SyndataSettings` stores out-range/send/syndata params; restored from `syndata_dict` during load
- `strategy_args` in CategoryBlock has syndata/send/out-range STRIPPED — they go to `syndata_dict`

## Dev Testing

Categories.txt is NOT in the default catalog search path in dev environment. To test:
```python
import preset_zapret2.catalog as cat
from pathlib import Path
orig = cat._candidate_indexjson_dirs
def patched():
    yield str(Path('dist/json').resolve())
    yield from orig()
cat._candidate_indexjson_dirs = patched
cat._CACHED_PATHS = None
cat._CACHED_CATEGORIES = None
```
