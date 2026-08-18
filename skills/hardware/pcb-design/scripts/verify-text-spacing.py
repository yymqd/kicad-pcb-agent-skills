#!/usr/bin/env python3
"""Verify silkscreen text spacing in a KiCad 10 PCB file.

Usage: python3 verify-text-spacing.py <path/to/board.kicad_pcb> [min_distance_mm]

Parses the S-expression, computes absolute text positions,
and reports text pairs closer than min_distance_mm (default: 0.8).
"""
import re, sys, math

def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "<PROJECT_DIR>/<project>/laser_driver.kicad_pcb"
    min_d = float(sys.argv[2]) if len(sys.argv) > 2 else 0.8

    with open(path) as f:
        lines = f.readlines()

    results = []  # (ref, val, fx, fy, rdx, rdy, vdx, vdy)
    i = 0
    while i < len(lines):
        if '(footprint' in lines[i] and '""' in lines[i]:
            fx = fy = None
            for j in range(i+1, min(i+5, len(lines))):
                m = re.search(r'\(at ([\d.-]+) ([\d.-]+)', lines[j])
                if m: fx, fy = float(m.group(1)), float(m.group(2)); break
            if fx is None: i += 1; continue

            ref = rdx = rdy = vdx = vdy = None
            j = i + 1
            while j < len(lines):
                if '(footprint' in lines[j] and j > i+1: break
                m = re.search(r'\(property "Reference" "(\w+)"', lines[j])
                if m:
                    ref = m.group(1)
                    if j+1 < len(lines):
                        m2 = re.search(r'\(at ([\d.-]+) ([\d.-]+)', lines[j+1])
                        if m2: rdx, rdy = float(m2.group(1)), float(m2.group(2))
                m = re.search(r'\(property "Value" "([^"]*)"', lines[j])
                if m and j+1 < len(lines):
                    m2 = re.search(r'\(at ([\d.-]+) ([\d.-]+)', lines[j+1])
                    if m2: vdx, vdy = float(m2.group(1)), float(m2.group(2))
                j += 1
            if ref: results.append((ref, fx, fy, rdx or 0, rdy or 0, vdx or 0, vdy or 0))
            i = j
        else: i += 1

    # Build text position pairs
    texts = []
    for ref, fx, fy, rdx, rdy, vdx, vdy in results:
        if ref.startswith('MT'): continue
        texts.append((ref, 'ref', fx + rdx, fy + rdy))
        texts.append((ref, 'val', fx + vdx, fy + vdy))

    issues = []
    for i, (r1, l1, x1, y1) in enumerate(texts):
        for j, (r2, l2, x2, y2) in enumerate(texts):
            if r1 >= r2: continue
            d = math.hypot(x1 - x2, y1 - y2)
            if d < min_d:
                issues.append((d, r1, l1, r2, l2, x1, y1, x2, y2))

    issues.sort(key=lambda x: x[0])

    print(f"共 {len(results)} 个非安装孔元件")
    print(f"最小间距: {min_d:.1f}mm")
    print(f"间距<{min_d:.1f}mm 的文字对: {len(issues)}")
    for d, r1, l1, r2, l2, x1, y1, x2, y2 in issues:
        print(f"  {r1}.{l1}({x1:.1f},{y1:.1f}) ↔ {r2}.{l2}({x2:.1f},{y2:.1f}): {d:.2f}mm")

    if not issues:
        print("✅ 全部合格！")

if __name__ == '__main__':
    main()
