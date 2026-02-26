import os
import sys
from pathlib import Path

os.chdir(r"h:\Privacy\zapretgui")
sys.path.insert(0, r"h:\Privacy\zapretgui")

from preset_zapret2.preset_manager import PresetManager
manager = PresetManager()
manager._load_from_active_file = lambda: None
from preset_zapret2.txt_preset_parser import parse_preset_file

data = parse_preset_file(Path(r"h:\Privacy\zapretgui\alt1.txt"))
preset = manager._preset_from_data(data)

print("Zapret 2 Selections:")
sel = manager._selections_from_preset(preset)
for cat_key in sel:
    print(f"  {cat_key}")

