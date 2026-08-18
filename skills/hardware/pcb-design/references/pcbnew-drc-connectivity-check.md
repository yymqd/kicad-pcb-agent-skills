# pcbnew DRC and Connectivity Check Patterns

Helper patterns for verifying board integrity using pcbnew Python API.

## GND Connectivity Check

Run after routing to verify no GND pad is floating:

```python
board = pcbnew.LoadBoard(pcb_path)
gnd_tracks = sum(1 for t in board.GetTracks() 
                 if t.GetNet() and t.GetNet().GetNetname() == "GND")
gnd_pads = sum(1 for fp in board.GetFootprints() 
               for p in fp.Pads()
               if p.GetNet() and p.GetNet().GetNetname() == "GND")
if gnd_tracks == 0 and gnd_pads > 0:
    raise RuntimeError("GND pads but NO GND tracks!")
```

## DRC CLI Invocation

```bash
kicad-cli pcb drc board.kicad_pcb --output /tmp/drc.rpt --units mm --all-track-errors
```

## DRC Results Parsing

```python
import re
from collections import Counter

with open("/tmp/drc.rpt") as f:
    content = f.read()

violations = Counter(re.findall(r'\[(\w+)\]', content))
print(f"Total violations: {sum(violations.values())}")
for vtype, count in violations.most_common():
    print(f"  {vtype}: {count}")

# Check unconnected items
m = re.search(r'Found (\d+) unconnected', content)
print(f"Unconnected: {m.group(1) if m else 'N/A'}")
```

## Get Actual Pad Positions

Standard library footprint pads have specific positions. Read them programmatically:

```python
for fp in board.GetFootprints():
    ref = fp.GetReference()
    for p in fp.Pads():
        x = p.GetPosition().x / 1e6  # nm -> mm
        y = p.GetPosition().y / 1e6
        net = p.GetNet().GetNetname() if p.GetNet() else ""
        print(f"{ref}.{p.GetNumber()}: ({x:.4f}, {y:.4f}) net={net}")
```

## Common Standard Footprint Pad Offsets

| Footprint | Pad 1 | Pad 2 | Notes |
|-----------|-------|-------|-------|
| R_0603_1608Metric | (-0.95, 0) | (0.95, 0) | Y-axis aligned |
| R_0805_2012Metric | (-0.912, 0) | (0.912, 0) | Wider than 0603 |
| C_0805_2012Metric | (-0.95, 0) | (0.95, 0) | Same as R_0603 |
| SOT-23-3 | varies | varies | Use GetPosition() |
| D_SOD-123 | ±1.65mm from center | | Along rotation axis |
| PinHeader_1x04_Horizontal | 0, -2, -4, -6mm from center | | Horizontal pins extend below board |
