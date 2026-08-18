# KiCad 10.0.3 完整导出与生产文件管线（WSL 版）

## 适用环境

- KiCad 10.0.3（WSL + Windows 双版本一致）
- WSL Ubuntu 24.04，项目文件在 D: 盘（`<D_DRIVE>/...`）
- 输出 PNG：优先 kicad-cli SVG → cairosvg 转 PNG；失败时由 matplotlib 生成（bode_plot.png、waveform.png、schematic_view.png、pcb_2d_layout.png）
- SVG→PNG 在 WSL 上正常工作（cairosvg 2.9.0 + rsvg-convert 2.58.0 均通过实测）

## 已知限制与解决

| 问题 | 原因 | 解决 |
|:----|:-----|:-----|
| `sch export svg -o file.svg` 输出是目录 | KiCad 10.0.3 的 `-o` 解析策略：后缀 `.svg` 时创建目录，实际文件在目录内 | 输出到临时目录，再从目录中取实际 `.svg` 文件 |
| `doc.add_picture('file.svg')` 报错 | python-docx 不支持 SVG 格式 | 使用 cairosvg 转 PNG 再嵌入；SVG 作为外部文件引用 |
| `PermissionError: D:盘写文件 | WPS/Word 持有文件锁 | 先 `taskkill /F /IM wps.exe` 再 `shutil.copy2(tmp, target)` |
| 中文字符路径的 `terminal(workdir=...)` 报错 | Hermes 工具限制 | 用 `cd <D_DRIVE>/...` 代替 `workdir=` 参数 |
| BOM 为空（仅表头）| 原理图无元件数据 | .kicad_sch 文件不含组件时 BOM 正常为 0 行；如需完整 BOM 需先在原理图中放置元件 |

## 导出管线步骤

### Phase 0: 环境检查

```bash
kicad-cli --version                     # 确认 10.0.3
ls lowpass_filter.kicad_pcb              # PCB 文件存在
ls lowpass_filter.kicad_sch              # 原理图文件存在
```

### Phase 1: 创建目录

```bash
mkdir -p gerber bom exports 3d
```

### Phase 2: Gerber 7 层 + 钻孔

```bash
kicad-cli pcb export gerbers board.kicad_pcb -o gerber/ \
    --layers F.Cu,B.Cu,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts

kicad-cli pcb export drill board.kicad_pcb -o gerber/
```

### Phase 3: SVG 导出（关键修复点）

```bash
# 原理图：用目录输出法（-o 创建目录，实际文件在目录内）
TMP_SVG="/tmp/kicad_svg_$$"
kicad-cli sch export svg board.kicad_sch --output "$TMP_SVG"
cp "$TMP_SVG"/*.svg exports/schematic.svg

# PCB 顶层/底层：直接出文件（--page-size-mode 2 紧凑视图）
kicad-cli pcb export svg board.kicad_pcb -o exports/pcb_top.svg \
    --layers F.Cu,F.SilkS,Edge.Cuts --page-size-mode 2
kicad-cli pcb export svg board.kicad_pcb -o exports/pcb_bottom.svg \
    --layers B.Cu,B.SilkS,Edge.Cuts --page-size-mode 2
```

### Phase 4: BOM + 3D

```bash
kicad-cli sch export bom board.kicad_sch -o bom/bom.csv --format-preset CSV
kicad-cli pcb export glb board.kicad_pcb -o 3d/board.glb \
    --include-tracks --include-pads --include-zones \
    --include-silkscreen --include-soldermask --force
```

### Phase 5: 打包

```bash
zip -r gerber.zip gerber/
zip -r production_files.zip gerber.zip bom/ exports/ 3d/ \
    board.kicad_pro board.kicad_sch board.kicad_pcb \
    bode_plot.png waveform.png pcb_2d_layout.png schematic_view.png
```

### Phase 6: 更新设计报告（DOCX）

```python
from docx import Document
from docx.shared import Inches, Pt, RGBColor
import os, shutil

doc = Document('设计报告.docx')

# 附件表（引用的文件路径）
doc.add_heading('附件：生产文件包', level=2)
table = doc.add_table(rows=1, cols=2)
table.style = 'Light Shading Accent 1'
for name, path in [('📦 完整包','production_files.zip'),...]:
    row = table.add_row().cells
    row[0].text = name; row[1].text = path

# SVG 外部引用
p = doc.add_paragraph()
run = p.add_run('📌 KiCad SVG 矢量图（Windows 浏览器打开）：')
run.bold = True
for name, fname in [('PCB 顶层','exports/pcb_top.svg'),...]:
    doc.add_paragraph(f'  • {name}：{ROOT}/{fname}').runs[0].font.size = Pt(9)

# 嵌入 PNG
for title, png, w in [('原理图','schematic_view.png',Inches(5.5)),...]:
    doc.add_paragraph(title)
    doc.add_picture(os.path.join(ROOT, png), width=w)

# D: 盘文件锁防护
subprocess.run(['taskkill.exe','/F','/IM','wps.exe'], capture_output=True)
tmp = '/tmp/report.docx'
doc.save(tmp)
shutil.copy2(tmp, doc_path)
os.remove(tmp)
```

### Phase 7: 校验

```bash
for f in gerber.zip production_files.zip exports/pcb_top.svg \
         exports/pcb_bottom.svg exports/schematic.svg; do
    [ -f "$f" ] && echo "✅ $f" || echo "❌ $f"
done
```

## 完整脚本

完整可执行脚本见 `scripts/kicad-export-all.sh`（本 skill 的 scripts/ 目录下）。

## SVG 在 DOCX 中的处理原则

**绝对禁止：** 用 `doc.add_picture('file.svg')` — python-docx 不支持 SVG，会静默报错或写入空图。

**正确做法：**
1. 报告正文嵌入 matplotlib 生成的 PNG（原理图、PCB 布局、伯德图、波形）
2. KiCad 导出的高质量 SVG 作为外部附件引用，告知用户"在 Windows 浏览器中双击打开"
3. 如果用户要求报告内直接看到 KiCad 原生图 → 必须用 Windows 端工具转换 PNG，或告知用户这是 WSL 限制
