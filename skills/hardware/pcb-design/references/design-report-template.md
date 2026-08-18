# Design Report Template (Markdown)

Use this template when generating a comprehensive PCB design report.
Translate to Chinese when the user communicates in Chinese.

## Template Structure

```markdown
# {Project Name} — Design & Build Guide

---

## 一、Circuit Theory

{Circuit diagram in ASCII art}
{Transfer function}
{Cutoff frequency calculation}
{Brief operating principle}

## 二、Design Parameters

| Parameter | Value |
|:----------|:------|
| Circuit type | ... |
| Cutoff frequency | ... |
| Roll-off rate | ... |
| Passband gain | ... |
| Phase shift | ... |

### Frequency Response

| Frequency | Gain | Note |
|:---------:|:----:|:-----|
| 100 Hz | -0.04 dB | Passband |
| 1 kHz | -3.00 dB | Cutoff |
| 10 kHz | -20.1 dB | Stop band |

## 三、PCB Layout

{ASCII layout/block diagram showing component placement}
{Signal flow description}

## 四、BOM

| # | Ref | Value | Package | Qty | Source |
|:-:|:---:|:------|:--------|:---:|:-------|
| 1 | R1 | 1.6kΩ | 0603 | 1 | LCSC/Basic |

## 五、KiCad Operations

### 5.1 Opening the Project
### 5.2 Viewing Schematic
### 5.3 Viewing PCB
### 5.4 Running DRC
### 5.5 Exporting Gerber

## 六、Fabrication (JLCPCB)

| Parameter | Value |
|:----------|:------|
| Layers | 2 |
| Thickness | 1.6mm |
| Surface | HASL |
| Quantity | 5-10 |
| Est. cost | ¥30-50 |

## 七、Soldering Guide

### Tools Needed
### Step-by-step
### Tips

## 八、Verification Test

| Test | Input | Expected | Measured |
|:----|:------|:---------|:---------|
| Passband | 100Hz, 1Vpp | ~1Vpp | ______ |
| Cutoff | ~1kHz, 1Vpp | ~0.707Vpp | ______ |
| Stopband | 10kHz, 1Vpp | ~0.1Vpp | ______ |

## 九、Output Files

| # | File | Size | Description |
|:--|:-----|:----:|:------------|
```

## DOCX Generation

For DOCX output, use python-docx with the following formatting guidelines:
- Font: 微软雅黑, 10.5pt body (WSL 上不可用，回退到 WenQuanYi Zen Hei)
- Heading colors: RGB(0x2F, 0x54, 0x96)
- Table headers: dark blue background (#2F5496), white text
- Table alt rows: light blue (#D6E4F0)
- ASCII circuit/PCB diagrams: Courier New, 8-9pt
- Saved to /tmp/ first, then shutil.copy2() to D: drive (WSL NTFS safety)

### Image embedding note (working pipeline)

**On WSL (KiCad 10.0.3, Ubuntu 24.04)**: SVG→PNG via **cairosvg 2.9.0 or rsvg-convert 2.58.0 works correctly** (2026-06-05 verified with vision_analyze — text, pads, tracks all legible). Use this pipeline:

```bash
# 1. Export from KiCad CLI
kicad-cli pcb export svg board.kicad_pcb -o /tmp/pcb_view.svg \
  --layers "F.Cu,F.SilkS,Edge.Cuts" --fit-page-to-board

# 2. Convert to PNG (cairosvg, scale=3.0 for 300dpi quality)
python3 -c "import cairosvg; cairosvg.svg2png(url='/tmp/pcb_view.svg', write_to='report/pcb_view.png', scale=3.0)"

# 3. Embed in DOCX
from docx.shared import Inches
doc.add_picture('report/pcb_view.png', width=Inches(5.5))
```

**KiCad 3D render** (preferred over GLB+trimesh):
```bash
kicad-cli pcb render board.kicad_pcb --output /tmp/render.png \
  --side top --width 1600 --height 1200 --quality high
```

⚠️ **Dense board limitation**: For very small boards (<25mm) with dense components (20+), `kicad-cli pcb render` may produce a nearly-empty green rectangle because the board is too small for the renderer to resolve individual components. In that case, fall back to `kicad-cli pcb export glb --include-tracks --include-pads --include-silkscreen` + trimesh rendering from a closer camera angle.

**Simulation plot embedding**: Bode plots generated from actual ngspice simulation data (matplotlib, dpi=150+) embed cleanly via `doc.add_picture()`. The 2-plot subfigure (gain + phase) at 150dpi, 10×6 inch yields ~100KB PNG — reasonable for a 10-page report.

```python
from docx import Document
from docx.shared import Pt, Inches, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import shutil

# Helper functions:
#   set_cell_shading(cell, color) — background
#   make_header_row(table, texts) — header row
#   add_table_row(table, texts) — data row
#   add_heading(text, level) — colored heading
#   add_para(text, bold, italic, size) — paragraph

doc = Document()
# ... build document ...

tmp = "/tmp/report.docx"
doc.save(tmp)
shutil.copy2(tmp, target_path)
```
