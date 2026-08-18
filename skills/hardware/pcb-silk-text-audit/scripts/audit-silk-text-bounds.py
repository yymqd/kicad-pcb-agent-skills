#!/usr/bin/env python3
"""丝印文字板边越界审计 — 计算所有丝印文字包围盒 r_max，标出超边项。

用法: python audit-silk-text-bounds.py <board.kicad_pcb> [板半径mm] [安全边距mm]
默认板半径 7.0 (Ø14mm 圆板)，安全边距 0.1 → 安全线 6.9mm。
非圆板可传更大的板半径，或传 0 禁用半径判据（仅输出所有文字信息）。

判据: 每段文字 (PCB_TEXT + footprint 的 Reference/Value) 的包围盒 r_max
      r_max = hypot(|x| + w/2, |y| + h/2)，w = 字符数 × 0.62 × 字高
      r_max < 板半径 − 安全边距 才算板内。

教训 (2026-07-31): 文字中心在板内 ≠ 文字在板内。21字符×1.0mm 版本号中心 r=6.52
      看着板内，包围盒 r_max=12.21mm 远超 Ø14 板径，加工被铣掉。
      必须覆盖三类文字：板级 PCB_TEXT、footprint Reference、footprint Value
      （封装 Reference 默认在焊盘外侧 ~1.65mm，边缘测试点会直接落出板外）。

Windows 端: 用 KiCad 自带 python 运行，如
  <D_DRIVE>\\Users\\<user>\\AppData\\Local\\Programs\\KiCad\\10.0\\bin\\python.exe audit-silk-text-bounds.py board.kicad_pcb
"""
import sys
import math

try:
    import pcbnew
except ImportError:
    sys.exit("需要 KiCad pcbnew。Windows 用 <KiCad>/bin/python.exe，Linux 用 /usr/lib/python3/dist-packages")


def char_width_ratio():
    """KiCad 默认字体字符宽度 ≈ 0.62 × 字号高度（实测；保守可取 0.65）"""
    return 0.62


def audit(path, radius_mm, safe_margin_mm):
    board = pcbnew.LoadBoard(path)
    safe = radius_mm - safe_margin_mm if radius_mm else None
    ratio = char_width_ratio()
    texts = []
    issues = []

    # 1) 板级 PCB_TEXT
    for item in board.GetDrawings():
        if item.GetClass() == "PCB_TEXT" and item.IsVisible() and item.GetLayerName() == "F.Silkscreen":
            pos = item.GetPosition()
            x, y = pos.x / 1e6, pos.y / 1e6
            sx, sy = item.GetTextSize().x / 1e6, item.GetTextSize().y / 1e6
            txt = item.GetText()
            rot = item.GetTextAngle().AsDegrees() if hasattr(item.GetTextAngle(), "AsDegrees") else 0
            texts.append(("PCB_TEXT", txt[:30], x, y, sx, sy, rot, 0))

    # 2) footprint Reference + Value 字段
    for fp in board.GetFootprints():
        for field_name in ("Reference", "Value"):
            f = getattr(fp, field_name)()
            if not f.IsVisible() or f.GetLayerName() != "F.Silkscreen":
                continue
            pos = f.GetPosition()
            x, y = pos.x / 1e6, pos.y / 1e6
            sx, sy = f.GetTextSize().x / 1e6, f.GetTextSize().y / 1e6
            txt = f.GetText()
            rot = f.GetTextAngle().AsDegrees() if hasattr(f.GetTextAngle(), "AsDegrees") else 0
            texts.append((f"{fp.GetReference()}.{field_name}", txt[:30], x, y, sx, sy, rot, 0))

    # 计算包围盒 r_max
    for i, (label, txt, x, y, sx, sy, rot, _) in enumerate(texts):
        n = len(txt)
        w = n * sx * ratio
        h = sy
        if abs(rot % 180) == 90:
            w, h = h, w
        rmax = math.hypot(abs(x) + w / 2, abs(y) + h / 2)
        texts[i] = (label, txt, x, y, sx, sy, rot, rmax)

    texts.sort(key=lambda t: t[7], reverse=True)
    r_label = f"板半径 {radius_mm}mm, 安全线 {safe:.2f}mm" if safe else "无半径判据"
    print(f"=== {r_label} — 共 {len(texts)} 条丝印文字 ===")
    for label, txt, x, y, sx, sy, rot, rmax in texts:
        if safe and rmax > safe:
            flag = " ⚠️超边"
            issues.append(f"超边 {label} '{txt}' @({x:.2f},{y:.2f}) r_max={rmax:.2f}")
        elif safe and rmax > safe - 0.4:
            flag = "  ⚠️贴边"
        else:
            flag = "  ok"
        print(f"{flag} {label} '{txt}' @({x:+.2f},{y:+.2f}) 字{sx:.2f}×{sy:.2f} rot{rot} r_max={rmax:.2f}")

    print(f"\n=== 超边 {len(issues)} 条 ===")
    for i in issues:
        print(" ", i)
    return issues


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    path = sys.argv[1]
    radius = float(sys.argv[2]) if len(sys.argv) > 2 else 7.0
    margin = float(sys.argv[3]) if len(sys.argv) > 3 else 0.1
    audit(path, radius, margin)
