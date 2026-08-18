# KiCad Export for Report Images

## Goal

Generate schematic and PCB layout images from KiCad and embed them directly in the design report (`.docx` / `.md`). **The user must not need to open KiCad to see the design.**

## Primary Path: kicad-cli SVG → cairosvg PNG

### Schematic
```bash
kicad-cli sch export svg project.kicad_sch --output /tmp/schematic.svg
/tmp/svg_venv/bin/python3 -c "
import cairosvg
cairosvg.svg2png(url='/tmp/schematic.svg', write_to='outputs/schematic_view.png', scale=3.0)
"
```

### PCB Layout (multilayer composite)
```bash
kicad-cli pcb export svg project.kicad_pcb --output /tmp/pcb_view.svg \
  --layers "F.Cu,F.SilkS,Edge.Cuts"
/tmp/svg_venv/bin/python3 -c "
import cairosvg
cairosvg.svg2png(url='/tmp/pcb_view.svg', write_to='outputs/pcb_view.png', scale=3.0)
"
```

**cairosvg 安装**：
```bash
python3 -m venv /tmp/svg_venv
/tmp/svg_venv/bin/pip install cairosvg
```

## ⚠️ Known Pitfalls on WSL

### Problem 0: KiCad SVG → PNG rendering on WSL

**2026-06-05 实测**（KiCad 10.0.3, Ubuntu 24.04 WSL）：cairosvg 2.9.0 和 rsvg-convert 2.58.0 均能正常渲染 KiCad SVG，vision_analyze 确认文字/焊盘/走线清晰可读。如果遇到渲染问题（旧系统或旧版本），降级到 matplotlib 回退方案。

### Fallback: matplotlib (the only reliable option on WSL)

Use the verified code templates below. After generating, always run `vision_analyze` to confirm the image is non-blank and readable.

#### Template A: 2D PCB Layout (verified 2026-06-05)

```python
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle

def gen_pcb_layout(board_w=20, board_h=15, track_segments=None,
                   smd_pads=None, tht_pads=None, labels=None, title=''):
    """
    track_segments: [(x1,y1,x2,y2, color), ...]
    smd_pads: [(x,y,w,h, ref), ...]
    tht_pads: [(x,y,r, ref), ...]
    labels: [(x,y,text, color, fontsize), ...]
    """
    fig, ax = plt.subplots(figsize=(8,6), facecolor='#1a1a2e')
    ax.set_facecolor('#1a3a1a')

    # Board
    ax.add_patch(Rectangle((0,0), board_w, board_h, fill=False,
                           edgecolor='white', lw=2.5))

    # Tracks (gold)
    for x1,y1,x2,y2 in track_segments or []:
        ax.plot([x1,x2],[y1,y2], color='#daa520', lw=4, solid_capstyle='round')

    # SMD pads (silver rectangles)
    for x,y,w,h in smd_pads or []:
        ax.add_patch(Rectangle((x-w/2,y-h/2), w, h,
                    facecolor='#c0c0c0', edgecolor='#888'))

    # THT pads (silver circles)
    for x,y,r in tht_pads or []:
        ax.add_patch(Circle((x,y), r, facecolor='#c0c0c0', edgecolor='#888'))

    # Labels
    for x,y,txt,clr,fs in labels or []:
        ax.text(x,y,txt,color=clr,fontsize=fs,ha='center',fontweight='bold')

    ax.set_aspect('equal'); ax.axis('off')
    if title: ax.set_title(title, color='white', fontsize=13, pad=15)
    plt.savefig('/tmp/pcb_layout.png', dpi=200, bbox_inches='tight',
                facecolor='#1a1a2e')
    return '/tmp/pcb_layout.png'
```

#### Template B: Schematic (verified for RC filter circuits)

```python
def gen_schematic(output_path='/tmp/schematic.png'):
    """Draw RC low-pass filter schematic."""
    fig, ax = plt.subplots(figsize=(8,4), facecolor='white')
    ax.set_facecolor('white')

    # Signal flow: left-to-right
    # ... draw wires, resistor symbol, capacitor symbol, labels ...

    ax.set_xlim(0,10); ax.set_ylim(0,5)
    ax.axis('off')
    plt.savefig(output_path, dpi=200, bbox_inches='tight', facecolor='white')
```

#### Template C: 3D Preview (GLB → trimesh)

```python
# Step 1: Export GLB from KiCad
import subprocess
subprocess.run([
    'kicad-cli', 'pcb', 'export', 'glb', pcb_path,
    '-o', '/tmp/board.glb',
    '--include-tracks', '--include-pads', '--include-zones',
    '--include-silkscreen', '--include-soldermask', '--force'
], check=True)

# Step 2: Render with trimesh + matplotlib
import trimesh, numpy as np
import matplotlib; matplotlib.use('Agg')
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import matplotlib.pyplot as plt

scene = trimesh.load('/tmp/board.glb')
# Group by component type
board_g, pads_g, silk_g, copper_g = [], [], [], []
for n,g in scene.geometry.items():
    k=n.lower()
    if 'pcb' in k: board_g.append(g)
    elif 'pad' in k: pads_g.append(g)
    elif 'silk' in k: silk_g.append(g)
    elif 'copper' in k: copper_g.append(g)

fig = plt.figure(figsize=(10,7), facecolor='#0f0f1a')
ax = fig.add_subplot(111, projection='3d', facecolor='#0f0f1a')

for gl,fc,ec,a in [
    (board_g,'#2a5a2a','#1a3a1a',0.95),
    (copper_g,'#b8860b','#8a6508',0.65),
    (pads_g,'#d0d0d0','#999',0.95),
    (silk_g,'#ffffff','#ccc',0.95)]:
    for g in gl:
        ax.add_collection3d(Poly3DCollection(g.vertices[g.faces],
            alpha=a, facecolor=fc, edgecolor=ec, lw=0.1))

# Auto-zoom
all_v = np.vstack([g.vertices for g in board_g+pads_g+copper_g+silk_g])
xs,ys,zs = all_v[:,0], all_v[:,1], all_v[:,2]
cx,cy,cz = xs.mean(), ys.mean(), zs.mean()
r = max(np.ptp(xs),np.ptp(ys))*0.55
ax.set_xlim(cx-r,cx+r); ax.set_ylim(cy-r,cy+r)
ax.set_zlim(cz-0.5,cz+0.5)
for a in [ax.xaxis,ax.yaxis,ax.zaxis]:
    a.pane.set_facecolor('#1a1a2e'); a.pane.set_alpha(0.1); a.set_visible(False)
ax.grid(False); ax.view_init(elev=25, azim=-60)
plt.savefig('/tmp/pcb_3d.png', dpi=200, bbox_inches='tight', facecolor='#0f0f1a')
```

**Note on 3D quality**: Small boards (<30mm) may not show pad/silk details clearly in matplotlib's 3D renderer. Recommend user also views in KiCad (F9).

### Post-generation quality check

Always call `vision_analyze` after generating any report image:
```
vision_analyze(image_url='/tmp/generated.png', 
               question='能看到元件标注、走线和焊盘吗？文字是否清晰无重叠？')
```
If labels are illegible or overlapping, adjust coordinates and regenerate.

### Problem 4: PyMuPDF from PDF
KiCad PDF exports the board at ~35×11 pts on an A4 page. When rendered directly, the board is invisible.

**Fix**: Find content bounds and clip:
```python
import fitz
doc = fitz.open('/tmp/board.pdf')
page = doc[0]
# Find content bounding box
min_x, min_y, max_x, max_y = ..., ..., ..., ...
clip = fitz.Rect(min_x-5, min_y-5, max_x+5, max_y+5)
pix = page.get_pixmap(matrix=fitz.Matrix(5, 5), clip=clip)
pix.save('output.png')
```

## Fallback: matplotlib (when KiCad export fails)

When cairosvg/PyMuPDF both fail to render KiCad exports correctly on WSL, generate equivalent visualization using matplotlib. **This is an acknowledged WSL limitation — the KiCad export would work on a system with a display server.**

### Schematic (matplotlib)
Draw using `patches.Circle`, `ax.plot` for wires, `ax.text` for labels. Include:
- ✅ White background (`fig.patch.set_facecolor('white')`)
- ✅ Outer border (`patches.Rectangle(... edgecolor='#555' ...)`)
- ✅ Circuit title
- ✅ Component symbols (resistor = zigzag, capacitor = parallel plates)
- ✅ All labels (R1, C1, J1, J2, VIN, VOUT, GND)
- ✅ Parameter values (1.6k, 100nF)
- ✅ Formula/notes

### PCB Layout (matplotlib)
Draw using `patches.Rectangle` for board, `ax.plot` for traces, `patches.Circle` for pads. Include:
- ✅ PCB green background (`ax.set_facecolor('#1a5c2a')`)
- ✅ Gray/light gray surroundings to frame the board
- ✅ White board outline border
- ✅ Yellow traces (F.Cu routing)
- ✅ Component rectangles (R1 pink, C1 green)
- ✅ All labels (J1/J2 with IN/OUT, R1 with 1.6k, C1 with 100nF)
- ✅ Dimension annotation (board size)
- ✅ Title

### Verifying image quality
After generating, always call `vision_analyze` and ask:
- "有无背景板？有无外边框？所有文字是否可读且无重叠？"

If any label is illegible or overlaps, adjust coordinates in the matplotlib script and regenerate.

## Embedding in DOCX

```python
from docx import Document
from docx.shared import Inches
doc = Document('report.docx')
for i, p in enumerate(doc.paragraphs):
    # Find the paragraph that should contain the image
    if '电路原理图' in p.text:
        next_p = doc.paragraphs[i+1]
        run = next_p.add_run()
        run.add_picture('schematic_view.png', width=Inches(4.5))
        break
doc.save('report.docx')
```
