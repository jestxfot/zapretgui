import os
import sys

from pathlib import Path
os.chdir(r"h:\Privacy\zapretgui")
sys.path.insert(0, r"h:\Privacy\zapretgui")

from preset_zapret1.preset_manager import PresetManagerV1
from preset_zapret1.preset_storage import get_active_preset_path_v1, get_presets_dir_v1, get_preset_path_v1
import shutil

manager = PresetManagerV1()

active_path = get_active_preset_path_v1()
if not active_path.exists():
    print("No active preset found v1")
else:
    print("Active Preset exists at:", active_path)
    
preset = manager.get_active_preset()
if preset:
    print("Parsed preset successfully:", preset.name)
    selections = manager.get_strategy_selections()
    print("Selections:")
    for k, v in selections.items():
        print(f"  {k}: {v}")
    
    print("\nCategories details:")
    for k, v in preset.categories.items():
        print(f"  {k}: tcp_args={repr(v.tcp_args)} udp_args={repr(v.udp_args)}")
else:
    print("Failed to get active preset")
