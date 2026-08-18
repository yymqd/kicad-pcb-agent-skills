# PCB Production Pipeline (KiCad 10 CLI + DOCX)

Complete automation from PCB file to delivery packages. Designed for WSL users targeting JLCPCB fabrication.

## Order of Operations (⚠️ 不可逆)

```
1. gen_pcb.py          → 生成/更新 lowpass_filter.kicad_pcb
2. kicad-cli export    → Gerber + Drill + BOM + SVG + GLB
3. SVG→PNG conversion → cairosvg/rsvg-convert
4. DOCX update         → python-docx 追加生产附录 + 高清设计图
5. Zip packaging       → gerber.zip + production_files.zip
6. Final validation    → 所有文件存在、非空、可打开
```

**关键**：Step 1 必须在 Step 2 之前。gen_pcb.py 会重新生成 .kicad_pcb，后续所有 export 基于最新版。

## Commands

### 1. Gerber（7层标准）

```bash
kicad-cli pcb export gerbers lowpass_filter.kicad_pcb \
  -o gerber/ --layers F.Cu,B.Cu,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts
```

### 2. 钻孔文件

```bash
kicad-cli pcb export drill lowpass_filter.kicad_pcb -o gerber/
```

### 3. BOM（CSV）

```bash
kicad-cli sch export bom lowpass_filter.kicad_sch \
  -o bom/bom.csv --format-preset CSV
```

### 4. SVG 导出

```bash
kicad-cli sch export svg lowpass_filter.kicad_sch -o exports/schematic.svg
kicad-cli pcb export svg lowpass_filter.kicad_pcb -o exports/pcb_top.svg \
  --layers F.Cu,F.SilkS,Edge.Cuts
kicad-cli pcb export svg lowpass_filter.kicad_pcb -o exports/pcb_bottom.svg \
  --layers B.Cu,B.SilkS,Edge.Cuts
```

### 5. 3D 模型

```bash
kicad-cli pcb export glb lowpass_filter.kicad_pcb -o 3d/pcb_3d.glb \
  --include-tracks --include-pads --include-zones \
  --include-silkscreen --include-soldermask \
  --include-inner-copper --force
```

### 6. SVG→PNG（KiCad 10.0.3 / WSL 实测正常）

**2026-06-05 实测**（KiCad 10.0.3, Ubuntu 24.04 WSL）：cairosvg 2.9.0 和 rsvg-convert 2.58.0 均能正确渲染 KiCad SVG，vision_analyze 确认文字/焊盘/走线清晰可读。**无须回退到 matplotlib。** 仅保留 SVG 原始文件在 exports/ 目录供 Windows 浏览器打开作为额外矢量备份。

```python
# ✅ 可靠路径（KiCad 10.0.3 + WSL实测通过）
import cairosvg
cairosvg.svg2png(url='exports/pcb_top.svg', write_to='exports/pcb_top.png', scale=3.0)
```

### 7. ZIP 打包

```bash
zip -r gerber.zip gerber/

zip -r production_files.zip gerber.zip bom/ exports/ 3d/ \
  lowpass_filter.kicad_pro lowpass_filter.kicad_sch lowpass_filter.kicad_pcb \
  simulation_output.txt circuit.cir gen_lpf_kicad10.py \
  bode_plot.png waveform.png
```

## DOCX 更新 — 生产附录追加

使用 python-docx 在现有设计报告末尾追加「生产文件包」章节和「高清设计图」附录。

**关键规则**：
1. 用 `Document(SRC)` 打开现有报告 → 追加内容 → `doc.save()` — 保留原有所有格式
2. 图片用 `doc.add_picture(path)` 嵌入，SIZE 统一 Inches(5.0-5.5)
3. **不要用 `.AlternativeText` 做图片替换** — python-docx 生成时不设 alt text
4. stylesWithEffects.xml 双绑问题：生成时保留 → 仅交付前剥离（见 office-document-specialist/references/docx-styles-with-effects-pitfall.md）

## 交付目录结构

```
outputs/
├── production_files.zip     完整生产包（含以下全部）
├── gerber.zip               Gerber + 钻孔文件
├── bom/bom.csv              CSV BOM
├── exports/
│   ├── schematic.png/svg    原理图
│   ├── pcb_top.png/svg      PCB 顶层
│   └── pcb_bottom.png/svg   PCB 底层
├── 3d/pcb_3d.glb            3D 模型
├── 设计报告.docx            报告（含生产附录+高清图）
└── lowpass_filter.*         源文件
```

## 验证清单

- [ ] Gerber 7层全部生成（F.Cu, B.Cu, F.SilkS, B.SilkS, F.Mask, B.Mask, Edge.Cuts）
- [ ] 钻孔文件 .drl 存在
- [ ] BOM CSV 包含全部元件
- [ ] SVG/PNG 文件非空（>1K）
- [ ] GLB 文件非空（>10K）
- [ ] production_files.zip 解压后文件完整
- [ ] DOCX 可被 Windows Word 打开（stylesWithEffects 已剥离）
- [ ] DOCX 嵌入图片数量正确
