"""Add --new before each --filter-tcp/udp section (except first and last) in V1 presets.
Also adds --new after the LAST filter section's args (before EOF), per user request.
"""
import os
import re

presets_dir = os.path.join(os.path.dirname(__file__), "..", "preset_zapret1", "builtin_presets")
filter_re = re.compile(r'^--filter-(tcp|udp)=', re.IGNORECASE)

total_patched = 0
total_already_ok = 0
total_skipped = 0

for fname in sorted(os.listdir(presets_dir)):
    if not fname.endswith(".txt"):
        continue
    fpath = os.path.join(presets_dir, fname)

    with open(fpath, encoding="utf-8") as f:
        lines = f.readlines()

    filter_count = sum(1 for l in lines if filter_re.match(l.strip()))

    if filter_count <= 1:
        total_skipped += 1
        continue

    new_lines = []
    first_filter_seen = False

    for i, line in enumerate(lines):
        stripped = line.strip()
        if filter_re.match(stripped):
            if not first_filter_seen:
                first_filter_seen = True
                new_lines.append(line)
            else:
                # Check if --new already present before this filter
                prev_real = None
                for j in range(i - 1, -1, -1):
                    if lines[j].strip():
                        prev_real = lines[j].strip()
                        break
                if prev_real != "--new":
                    new_lines.append("--new\n")
                new_lines.append(line)
        else:
            new_lines.append(line)

    # Add --new after the last non-empty content line (before final blank lines)
    # Find last non-empty line index
    last_content_idx = None
    for i in range(len(new_lines) - 1, -1, -1):
        if new_lines[i].strip():
            last_content_idx = i
            break

    if last_content_idx is not None and new_lines[last_content_idx].strip() != "--new":
        # Insert --new after last content, before any trailing blanks
        new_lines.insert(last_content_idx + 1, "--new\n")

    if new_lines != lines:
        with open(fpath, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
        total_patched += 1
    else:
        total_already_ok += 1

print(f"Patched: {total_patched}, Already OK: {total_already_ok}, Skipped (<=1 filter): {total_skipped}")
