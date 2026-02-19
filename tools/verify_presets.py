"""Verify all V1 presets have correct --new count."""
import os
import re

presets_dir = os.path.join(os.path.dirname(__file__), "..", "preset_zapret1", "builtin_presets")
filter_re = re.compile(r'^--filter-(tcp|udp)=')
new_re = re.compile(r'^--new$')
problems = []

for fname in sorted(os.listdir(presets_dir)):
    if not fname.endswith(".txt"):
        continue
    fpath = os.path.join(presets_dir, fname)
    with open(fpath, encoding="utf-8") as f:
        lines = [l.strip() for l in f if l.strip()]

    filter_count = sum(1 for l in lines if filter_re.match(l))
    new_count = sum(1 for l in lines if new_re.match(l))

    if filter_count > 1:
        # Expected: new_count == filter_count (N-1 between sections + 1 after last)
        if new_count != filter_count:
            problems.append(f"{fname}: filters={filter_count}, --new={new_count}")
    elif filter_count == 1 and new_count > 0:
        problems.append(f"{fname}: filters={filter_count}, --new={new_count} (unexpected)")

if problems:
    print("PROBLEMS:")
    for p in problems:
        print(" ", p)
else:
    print(f"All {sum(1 for f in os.listdir(presets_dir) if f.endswith('.txt'))} presets OK")
