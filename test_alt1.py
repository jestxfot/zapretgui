import os
import sys
from pathlib import Path

os.chdir(r"h:\Privacy\zapretgui")
sys.path.insert(0, r"h:\Privacy\zapretgui")

alt1_content = """# Preset: alt1
# ActivePreset: alt1
# Created: 2026-02-19T00:00:00
# IconColor: #60cdff
# Description: Imported from bat/alt1.txt

--wf-tcp=80,443,6695-6705
--wf-udp=443,5056,27002,50000-50100

# === QUIC Discord ===
--filter-udp=443
--hostlist=lists/discord.txt
--dpi-desync=fake
--dpi-desync-repeats=6
--dpi-desync-fake-quic=bin/quic_initial_www_google_com.bin

# === Discord Voice ===
--new
--filter-udp=50000-50100
--ipset=lists/ipset-discord.txt
--dpi-desync=fake
--dpi-desync-any-protocol
--dpi-desync-cutoff=d3
--dpi-desync-repeats=6

# === HTTP (порт 80) ===
--new
--filter-tcp=80
--hostlist=lists/discord.txt
--ipset=lists/ipset-cloudflare.txt
--dpi-desync=fake,split2
--dpi-desync-autottl=2
--dpi-desync-fooling=md5sig

# === UDP порт 5056 ===
--new
--filter-udp=5056,27002
--dpi-desync-any-protocol
--dpi-desync=fake
--dpi-desync-repeats=6
--dpi-desync-cutoff=n15
--dpi-desync-fake-unknown-udp=bin/quic_initial_www_google_com.bin

# === HTTPS ===
--new
--filter-tcp=443
--hostlist-exclude=lists/netrogat.txt
--dpi-desync=fake,split
--dpi-desync-autottl=5
--dpi-desync-repeats=6
--dpi-desync-fooling=badseq
--dpi-desync-fake-tls=bin/tls_clienthello_www_google_com.bin

# === Discord TCP ===
--new
--filter-tcp=6695-6705
--dpi-desync=fake,split2
--dpi-desync-repeats=8
--dpi-desync-fooling=md5sig
--dpi-desync-autottl=2
--dpi-desync-fake-tls=bin/tls_clienthello_www_google_com.bin

# === QUIC ===
--new
--filter-udp=443
--ipset=lists/ipset-cloudflare.txt
--dpi-desync=fake
--dpi-desync-repeats=6
--dpi-desync-fake-quic=bin/quic_initial_www_google_com.bin
--new
"""

Path(r"h:\Privacy\zapretgui\alt1.txt").write_text(alt1_content, encoding="utf-8")

from preset_zapret2.txt_preset_parser import parse_preset_file
data = parse_preset_file(Path(r"h:\Privacy\zapretgui\alt1.txt"))
for b in data.categories:
    print(f"[{b.category}:{b.protocol}] -> {repr(b.strategy_args)}")
    
from preset_zapret1.preset_manager import PresetManagerV1
manager = PresetManagerV1()
preset = manager._load_from_active_file() # wait, I need to mock active preset path
manager._load_from_active_file = lambda: None # replace
manager._get_store = lambda: None
from preset_zapret1.preset_model import PresetV1, CategoryConfigV1
from preset_zapret1.strategy_inference import infer_strategy_id_from_args

preset = PresetV1(name="alt1", base_args="")
for block in data.categories:
    cat_name = block.category
    if cat_name not in preset.categories:
        preset.categories[cat_name] = CategoryConfigV1(name=cat_name, filter_mode=block.filter_mode)
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

print("\nSyndata/Strategy inference:")
for cat_name, cat in preset.categories.items():
    if cat.tcp_args and cat.tcp_args.strip():
        inferred = infer_strategy_id_from_args(
            category_key=cat_name, args=cat.tcp_args,
            protocol="tcp",
        )
        if inferred != "none":
            cat.strategy_id = inferred
            print(f" inferred {cat_name} TCP -> {inferred}")
            continue
    if cat.udp_args and cat.udp_args.strip():
        inferred = infer_strategy_id_from_args(
            category_key=cat_name, args=cat.udp_args,
            protocol="udp",
        )
        if inferred != "none":
            cat.strategy_id = inferred
            print(f" inferred {cat_name} UDP -> {inferred}")

print("\nFinal Selections:")
for key, cat in preset.categories.items():
    norm_key = str(key or "").strip().lower()
    sid = str(getattr(cat, "strategy_id", "") or "").strip().lower() or "none"
    if sid == "none":
        has_args = bool((getattr(cat, "tcp_args", "") or "").strip() or (getattr(cat, "udp_args", "") or "").strip())
        if has_args:
            sid = "custom"
    print(f"  {norm_key} -> {sid}")

