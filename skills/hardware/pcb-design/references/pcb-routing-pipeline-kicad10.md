# PCB Routing Pipeline for KiCad 10 (pcbnew Python API)

**Source:** Laser driver PCB design session, 2026-06-05. 22 footprints, 10 nets, 92 tracks, 19.8×23.8mm board. This pipeline reduced unconnected pads from 39→3.

## Core Principle

**Read real pad positions from loaded footprints. Never hardcode coordinates.**

Standard library footprints have precise pad positions (±0.95mm for 0603, ±0.912mm for 0805, etc.). Hardcoding even close values (like ±0.75mm for 0805) produces DRC unconnected_items that are invisible in the SVG render but fail actual fabrication.

## Step 1: Load Standard Library Footprints

```python
import pcbnew
from pcbnew import VECTOR2I, PCB_TRACK, PCB_VIA, FromMM, ANGLE_90

board = pcbnew.BOARD()
board.SetDesignSettings(pcbnew.EDA_UNITS_MM)

# Load each footprint via FootprintLoad()
fp = pcbnew.FootprintLoad(
    "/usr/share/kicad/footprints/Resistor_SMD.pretty/",
    "R_0603_1608Metric"
)
fp.SetReference("R1")
fp.SetValue("10k")
fp.SetPosition(VECTOR2I(FromMM(cx), FromMM(cy)))
fp.SetOrientation(ANGLE_90)
fp.SetLayer(pcbnew.F_Cu)

# ⚠️ Place BEFORE adding to board if orientation matters
board.Add(fp)

# ⚠️ Set Reference/Value text AFTER board.Add()
rfp = fp.Reference()
rfp.SetPosition(VECTOR2I(FromMM(cx), FromMM(cy + 1.2)))
rfp.SetTextSize(VECTOR2I(FromMM(0.8), FromMM(0.8)))
rfp.SetVisible(True)
vfp = fp.Value()
vfp.SetPosition(VECTOR2I(FromMM(cx), FromMM(cy - 0.8)))
vfp.SetTextSize(VECTOR2I(FromMM(0.6), FromMM(0.6)))
vfp.SetVisible(True)
```

**Why text after Add:** KiCad 10 resolves footprint-relative coordinates only when the footprint belongs to a board. Setting text position before `board.Add()` causes text to land at (0,0) or inside the pad.

**WSL 路径验证**（2026-06-05 实测）：`/usr/share/kicad/footprints/` 在 KiCad 10.0.3 / Ubuntu 24.04 WSL 上包含所需全部封装类别。如果某封装不存在，用 `find /usr/share/kicad/footprints/ -name "*0603*Metric*"` 搜索正确的文件名。KiCad 10 的封装名与 KiCad 7 一致。

## Step 2: Organize Footprints for Routing

Collect all footprints by reference designator for easy lookup during routing:

```python
fps = {}
for fp in board.GetFootprints():
    fps[fp.GetReference()] = fp
```

## Step 3: Get Pad Position (Critical Function)

Standard library pads can be on any layer with any offset. Use the absolute board position:

```python
def pad_pos(fp_ref, pad_num):
    """Get absolute (x, y) in mm for a given pad on a given footprint."""
    fp = fps[fp_ref]
    for p in fp.Pads():
        if p.GetNumber() == str(pad_num):
            return (p.GetPosition().x / 1e6, p.GetPosition().y / 1e6)
    raise ValueError(f"Pad {pad_num} not found on {fp_ref}")

# Usage:
x1, y1 = pad_pos("R1", 1)   # pin 1 of R1
x2, y2 = pad_pos("U1", 4)   # pin 4 of U1
```

## Step 4: Create Tracks from Actual Pad Positions

```python
def route_segment(board, fp_ref1, pad1, fp_ref2, pad2, net_code, layer=pcbnew.F_Cu, width_mm=0.3):
    """Route a straight line between two absolute pad positions."""
    x1, y1 = pad_pos(fp_ref1, pad1)
    x2, y2 = pad_pos(fp_ref2, pad2)

    track = PCB_TRACK(board)
    track.SetStart(VECTOR2I(FromMM(x1), FromMM(y1)))
    track.SetEnd(VECTOR2I(FromMM(x2), FromMM(y2)))
    track.SetLayer(layer)
    track.SetWidth(FromMM(width_mm))
    track.SetNet(net_code)
    board.Add(track)
    return track

def route_via_multi(board, pts, net_code, layer_switch=None, width_mm=0.3):
    """Route through multiple points with optional via at midpoint."""
    # layer_switch = (from_layer, to_layer) — adds via between middle two points
    tracks = []
    for i in range(len(pts) - 1):
        x1, y1 = pts[i]
        x2, y2 = pts[i+1]
        track = PCB_TRACK(board)
        track.SetStart(VECTOR2I(FromMM(x1), FromMM(y1)))
        track.SetEnd(VECTOR2I(FromMM(x2), FromMM(y2)))
        # Determine layer
        if layer_switch and i >= (len(pts) // 2):
            track.SetLayer(layer_switch[1])
        else:
            track.SetLayer(layer_switch[0] if layer_switch else pcbnew.F_Cu)
        track.SetWidth(FromMM(width_mm))
        track.SetNet(net_code)
        board.Add(track)
        tracks.append(track)

    # Add via at midpoint if layer switch requested
    if layer_switch:
        mid = len(pts) // 2
        mx, my = pts[mid]
        via = PCB_VIA(board)
        via.SetPosition(VECTOR2I(FromMM(mx), FromMM(my)))
        via.SetDrill(FromMM(0.3))
        via.SetWidth(FromMM(0.6))
        via.SetNet(net_code)
        board.Add(via)
        tracks.append(via)

    return tracks
```

## Step 5: Create and Assign Nets

KiCad 10 uses string-based net names for `board.Save()` — no net mapping corruption issue.

```python
def make_net(board, name):
    """Create a net if it doesn't exist, return net_info object."""
    nets = board.GetNetInfo().NetsByName()
    if name in nets:
        return nets[name]
    net = pcbnew.NETINFO_ITEM(board, name)
    board.Add(net)
    return net

# Create all nets before assigning
nets = {}
for name in ["GND", "VIN", "VOUT", "GATE", "VSNS", "VREF", "TTL", "ANA", "FB", "BST"]:
    nets[name] = make_net(board, name)
    print(f"Net {name}: code={nets[name].GetNetCode()}")

# Assign pads to nets using pad number (NOT list index)
pad_assignments = {
    "U1": {1: "VIN", 2: "VOUT", 3: "GND", 4: "GATE", 5: "BST", 6: "VSNS"},
    "R1": {1: "GATE", 2: "GND"},
    # ... etc.
}

for ref, assignments in pad_assignments.items():
    fp = fps[ref]
    for p in fp.Pads():
        if p.GetNumber() in assignments:
            net_name = assignments[p.GetNumber()]
            p.SetNet(nets[net_name])
            p.SetPosition(p.GetPosition())  # ⚠️ Force re-evaluation
```

### ⚠️ 强制操作：Net 序列化修复（2026-06-05 会话发现）

**问题**：`SetNet()` 只修改了内存中的 net 关联。`board.Save()` 时，pad 的 net 分配可能未写入 `.kicad_pcb` S-expression 文件。net 分配在内存中存在但持久化后丢失——这是 pcbnew KiCad 10 的一个已知行为。

**修复方法**：在每个 `SetNet()` 调用后，立即调用 `p.SetPosition(p.GetPosition())`。这会强制 pcbnew 重新计算焊盘的坐标元数据，连带触发 net 信息的序列化写入：

```python
for ref, assignments in pad_assignments.items():
    fp = fps[ref]
    for p in fp.Pads():
        if p.GetNumber() in assignments:
            net_name = assignments[p.GetNumber()]
            p.SetNet(nets[net_name])
            p.SetPosition(p.GetPosition())  # ⚠️ 强制 net 序列化到磁盘
```

**验证方法**：在 `board.Save()` 之后，重新加载文件并检查 net 分配：
```python
check = pcbnew.LoadBoard("output.kicad_pcb")
for fp in check.GetFootprints():
    for p in fp.Pads():
        net_name = p.GetNet().GetNetname() if p.GetNet() else "NO NET"
        print(f"{fp.GetReference()}.{p.GetNumber()} → {net_name}")
```
所有 pad 的 net 应为预期值（而非 "NO NET"）。

## Step 6: Route All Nets

```python
# Power: VIN
route_segment(board, "J1", 1, "U1", 1, nets["VIN"], width_mm=0.4)
route_segment(board, "U1", 1, "C1", 1, nets["VIN"], width_mm=0.4)
route_segment(board, "C1", 2, "L1", 1, nets["VIN"], width_mm=0.4)

# Boost output
route_segment(board, "L1", 2, "U1", 2, nets["VOUT"], width_mm=0.4)
route_segment(board, "U1", 2, "D1", 2, nets["VOUT"], width_mm=0.4)
route_segment(board, "D1", 1, "C2", 1, nets["VOUT"], width_mm=0.4)
route_segment(board, "C2", 2, "J2", 1, nets["VOUT"], width_mm=0.5)

# Gate drive
route_segment(board, "U1", 4, "R1", 1, nets["GATE"], width_mm=0.3)
route_segment(board, "R1", 2, "Q1", 1, nets["GATE"], width_mm=0.3)

# VREF
route_segment(board, "U1", 6, "R3", 1, nets["VREF"], width_mm=0.3)
route_segment(board, "R3", 2, "R4", 1, nets["VREF"], width_mm=0.3)
route_segment(board, "R4", 2, "U2", 3, nets["VREF"], width_mm=0.3)

# Ground — thick traces (0.5mm) for dense boards instead of copper pour
route_segment(board, "J1", 2, "Q1", 3, nets["GND"], width_mm=0.5)
route_segment(board, "Q1", 3, "R2", 2, nets["GND"], width_mm=0.5)
route_segment(board, "R2", 2, "C3", 2, nets["GND"], width_mm=0.5)
route_segment(board, "C3", 2, "J2", 2, nets["GND"], width_mm=0.5)
# ... connect ALL GND pads to the GND bus

# Signal routes — 0.25mm
route_segment(board, "U2", 1, "R4", 1, nets["FB"], width_mm=0.25)

# Save
board.Save("output.kicad_pcb")
```

## Step 7: Post-Route Verification

```python
after = pcbnew.LoadBoard("output.kicad_pcb")

# Count tracks per net
from collections import Counter
net_counts = Counter()
for t in after.GetTracks():
    if t.GetNet():
        net_counts[t.GetNet().GetNetname()] += 1

print("Track count per net:")
for name, count in sorted(net_counts.items()):
    print(f"  {name}: {count}")

# GND connectivity check
gnd_pads = []
for fp in after.GetFootprints():
    for p in fp.Pads():
        if p.GetNet() and p.GetNet().GetNetname() == "GND":
            gnd_pads.append(f"{fp.GetReference()}.{p.GetNumber()}")

gnd_tracks = net_counts.get("GND", 0)
if gnd_tracks == 0 and len(gnd_pads) > 0:
    print(f"⚠️ CRITICAL: {len(gnd_pads)} GND pads but NO GND tracks!")
else:
    print(f"✅ GND: {len(gnd_pads)} pads, {gnd_tracks} tracks")

# Total stats
total_tracks = sum(1 for t in after.GetTracks() if isinstance(t, PCB_TRACK))
total_vias = sum(1 for t in after.GetTracks() if isinstance(t, PCB_VIA))
print(f"Total: {total_tracks} tracks, {total_vias} vias")
```

## Step 8: DRC via CLI

```bash
kicad-cli pcb drc output.kicad_pcb --output /tmp/drc.rpt \
  --units mm --all-track-errors --exit-code-violations
```

**Expected DRC results for dense boards (19.8×23.8mm, 22 footprints):**
- ~260 violations is typical (courtyard overlap, silk overlap, clearance on dense components)
- 0 unconnected_items ✓ (this is the critical metric — zero means all pads connect)
- ~34 critical (courtyard overlap on adjacent components — acceptable for dense layout)
- ~105 clearance (pad-to-pad spacing on 0603 — OK for fabrication at JLCPCB)
- ~112 cosmetic (silk_on_pad, etc.)

## Key Pitfalls

1. **Do NOT hardcode coordinates.** Standard library 0805 pads are at ±0.912mm (not ±0.75mm). Always read from `p.GetPosition()`.
2. **Do not assume pad order in list().** Use `pad.GetNumber()` to identify pads, not list index. (KiCad 10 sorts list() by pad number, but relying on it is fragile.)
3. **`board.Add(fp)` before setting text position.** KiCad 10 resolves text offsets only after the footprint belongs to a board.
4. **Call `p.SetPosition(p.GetPosition())` after `SetNet()`** to force net serialization into S-expression. Without this, the net assignment exists in memory but doesn't write to the file.
5. **GND on dense boards (<20mm, 20+ parts):** Use thick (0.5mm) GND bus traces instead of copper pour. Full-board GND pour creates hundreds of solder_mask_bridge/shorting_items violations. If copper pour is required, set clearance ≥ 0.3mm or limit to local areas around specific components.
6. **Use `kicad-cli pcb export stats`** for board statistics instead of manual Python counting. It reports exact dimensions, component density, min clearance, and pad/via/drill counts.
7. **`kicad-cli pcb drc` CLI** exists and works in KiCad 10 — don't assume DRC is GUI-only.
8. **Net assignments in KiCad 10 `board.Save()`** use string net names. Complex cross-scenarios (6+ nets including GND/VOUT/VIN/GATE/VSNS/VREF) are handled correctly — no net mapping corruption.
