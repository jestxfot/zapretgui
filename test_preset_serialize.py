import os
import sys

sys.path.insert(0, os.path.abspath('.'))

from preset_zapret2.txt_preset_parser import parse_preset_file, generate_preset_content
from preset_zapret2.preset_defaults import get_default_template_content

def run_test():
    content = get_default_template_content()
    print("Original length:", len(content))
    
    # Save to dummy
    with open("dummy.txt", "w", encoding="utf-8") as f:
        f.write(content)
        
    preset = parse_preset_file("dummy.txt")
    
    generated = generate_preset_content(preset)
    
    with open("dummy_out.txt", "w", encoding="utf-8") as f:
        f.write(generated)
        
    import subprocess
    subprocess.run(["fc", "dummy.txt", "dummy_out.txt"], shell=True)
    
if __name__ == "__main__":
    run_test()
