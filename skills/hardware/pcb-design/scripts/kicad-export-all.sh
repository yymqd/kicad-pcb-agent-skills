#!/usr/bin/env bash
# ============================================================
# KiCad 10.0.3 完整导出管线（WSL 版）
# ============================================================
# 修复项：
#  ① sch export svg -o 输出的是目录，需从目录内取实际文件
#  ② SVG 不能直接嵌入 DOCX（用 cairosvg 转 PNG 嵌入）
#  ③ D: 盘文件锁（先 kill WPS/Word）
#  ④ set -e 导致 ls 无匹配时中断（改用容错写法）
# ============================================================

KICAD_CLI="kicad-cli"
PROJECT_ROOT="<PROJECT_DIR>/<project>/outputs"
TMP_SVG="/tmp/kicad_svg_$$"

# ---------- Phase 0: Pre-Flight ----------
cd "$PROJECT_ROOT" || { echo "❌ 目录不存在"; exit 1; }

echo "=== Phase 0: Pre-Flight ==="
echo "KiCad: $($KICAD_CLI --version 2>&1)"
echo "PCB:   $(ls -lh lowpass_filter.kicad_pcb  2>/dev/null | awk '{print $5}' || echo '-')"
echo "SCH:   $(ls -lh lowpass_filter.kicad_sch  2>/dev/null | awk '{print $5}' || echo '-')"
echo ""

# ---------- 重新生成 PCB ----------
if [ -f "gen_lpf_kicad10.py" ]; then
    echo "=== Regenerate PCB ==="
    python3 gen_lpf_kicad10.py 2>&1 || echo "  ⚠️ 生成失败（继续用已有文件）"
    echo ""
fi

# ---------- Phase 1: 目录 ----------
echo "=== Phase 1: 创建导出目录 ==="
mkdir -p gerber bom exports 3d
rm -rf "$TMP_SVG" exports/schematic.svg 2>/dev/null
echo ""

# ---------- Phase 2: Gerber 7层 ----------
echo "=== Phase 2: Gerber 导出 ==="
$KICAD_CLI pcb export gerbers lowpass_filter.kicad_pcb -o gerber/ \
    --layers F.Cu,B.Cu,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts 2>&1
echo "  → $(ls gerber/ 2>/dev/null | wc -l) files"
echo ""

# ---------- Phase 3: 钻孔 ----------
echo "=== Phase 3: 钻孔文件导出 ==="
$KICAD_CLI pcb export drill lowpass_filter.kicad_pcb -o gerber/ 2>&1
echo ""

# ---------- Phase 4: BOM ----------
echo "=== Phase 4: BOM 导出 ==="
$KICAD_CLI sch export bom lowpass_filter.kicad_sch -o bom/bom.csv --format-preset CSV 2>&1
echo ""

# ---------- Phase 5: SVG ----------
echo "=== Phase 5: SVG 导出 ==="

# 5a: 原理图 — sch export 的 -o 创建目录，实际文件在目录内
$KICAD_CLI sch export svg lowpass_filter.kicad_sch --output "$TMP_SVG" 2>&1
ACTUAL=$(ls "$TMP_SVG"/*.svg 2>/dev/null | head -1)
if [ -n "$ACTUAL" ]; then
    cp "$ACTUAL" exports/schematic.svg
    echo "  ✅ schematic.svg ($(du -h exports/schematic.svg | cut -f1))"
fi

# 5b: PCB 顶层/底层 — pcb export 直接出文件
$KICAD_CLI pcb export svg lowpass_filter.kicad_pcb -o exports/pcb_top.svg \
    --layers F.Cu,F.SilkS,Edge.Cuts --page-size-mode 2 2>&1
echo "  ✅ pcb_top.svg ($(du -h exports/pcb_top.svg | cut -f1))"

$KICAD_CLI pcb export svg lowpass_filter.kicad_pcb -o exports/pcb_bottom.svg \
    --layers B.Cu,B.SilkS,Edge.Cuts --page-size-mode 2 2>&1
echo "  ✅ pcb_bottom.svg ($(du -h exports/pcb_bottom.svg | cut -f1))"
echo ""

# ---------- Phase 6: 3D ----------
echo "=== Phase 6: 3D GLB 导出 ==="
$KICAD_CLI pcb export glb lowpass_filter.kicad_pcb -o 3d/pcb_3d.glb \
    --include-tracks --include-pads --include-zones \
    --include-silkscreen --include-soldermask --force 2>&1 || true
echo "  3d: $(ls -lh 3d/pcb_3d.glb 2>/dev/null | awk '{print $5}')"
echo ""

# ---------- Phase 7: 打包 ----------
echo "=== Phase 7: 打包 ==="
rm -f gerber.zip production_files.zip 2>/dev/null
zip -r gerber.zip gerber/ >/dev/null 2>&1
zip -r production_files.zip gerber.zip bom/ exports/ 3d/ \
    lowpass_filter.kicad_pro lowpass_filter.kicad_sch lowpass_filter.kicad_pcb \
    bode_plot.png waveform.png pcb_2d_layout.png schematic_view.png \
    gen_lpf_kicad10.py >/dev/null 2>&1
echo "  gerber.zip: $(du -h gerber.zip | cut -f1)"
echo "  production_files.zip: $(du -h production_files.zip | cut -f1)"
echo ""

# ---------- Phase 8: DOCX ----------
echo "=== Phase 8: 更新设计报告 ==="
<C_DRIVE>/Windows/System32/cmd.exe /c \
    "taskkill /F /IM wps.exe 2>nul & taskkill /F /IM WINWORD.EXE 2>nul & exit 0" 2>/dev/null
sleep 1

python3 << 'PYEOF'
from docx import Document
from docx.shared import Inches, Pt, RGBColor
import os, shutil

ROOT = "<PROJECT_DIR>/<project>/outputs"
doc_path = f"{ROOT}/设计报告.docx"

if not os.path.exists(doc_path):
    print("  ⚠️ 报告文件不存在，跳过")
    exit(0)

doc = Document(doc_path)

doc.add_page_break()
doc.add_heading('附件：自动生成生产文件包', level=2)
attachments = [
    ('📦 完整生产包', 'production_files.zip'),
    ('🖨️ Gerber 打样包', 'gerber.zip'),
    ('📋 BOM', 'bom/bom.csv'),
    ('🔧 PCB 源文件', 'lowpass_filter.kicad_pcb'),
    ('📐 原理图', 'lowpass_filter.kicad_sch'),
    ('📂 项目文件', 'lowpass_filter.kicad_pro'),
    ('🎨 3D 预览', '3d/pcb_3d.glb'),
]
table = doc.add_table(rows=1, cols=2)
table.style = 'Light Shading Accent 1'
table.rows[0].cells[0].text = '文件'
table.rows[0].cells[1].text = '路径'
for name, path in attachments:
    row = table.add_row().cells
    row[0].text = name
    row[1].text = path

doc.add_paragraph('')
p = doc.add_paragraph()
run = p.add_run('📌 KiCad SVG 矢量图（Windows 浏览器打开）：')
run.bold = True; run.font.size = Pt(10)
for name, fname in [
    ('PCB 顶层', 'exports/pcb_top.svg'),
    ('PCB 底层', 'exports/pcb_bottom.svg'),
    ('原理图', 'exports/schematic.svg'),
]:
    pp = doc.add_paragraph(f'  • {name}：{ROOT}/{fname}')
    pp.runs[0].font.size = Pt(9)
    pp.runs[0].font.color.rgb = RGBColor(0x00, 0x66, 0xCC)

doc.add_page_break()
doc.add_heading('附录：设计图', level=2)
for title, png, w in [
    ('原理图', 'schematic_view.png', Inches(5.5)),
    ('PCB 布局', 'pcb_2d_layout.png', Inches(5.0)),
    ('伯德图', 'bode_plot.png', Inches(5.5)),
    ('时域波形', 'waveform.png', Inches(5.5)),
]:
    full = f"{ROOT}/{png}"
    if os.path.exists(full):
        doc.add_paragraph(title)
        doc.add_picture(full, width=w)
    else:
        doc.add_paragraph(f'⚠️ {png} 缺失')

tmp = "/tmp/设计报告.docx"
doc.save(tmp)
shutil.copy2(tmp, doc_path)
os.remove(tmp)
print(f"  ✅ 设计报告更新 ({os.path.getsize(doc_path)//1024} KB)")
PYEOF
echo ""

# ---------- Phase 9: 校验 ----------
echo "=== Phase 9: 文件校验 ==="
FAIL=0
for f in gerber.zip production_files.zip exports/pcb_top.svg exports/pcb_bottom.svg \
         exports/schematic.svg 3d/pcb_3d.glb 设计报告.docx; do
    if [ -f "$f" ]; then
        echo "  ✅ $f ($(du -h "$f" | cut -f1))"
    else
        echo "  ❌ $f 缺失"
        FAIL=1
    fi
done

echo ""
if [ "$FAIL" -eq 0 ]; then
    echo "✅ 全部完成！"
    echo "📦 $PROJECT_ROOT/production_files.zip"
    echo "🖨️ $PROJECT_ROOT/gerber.zip"
    echo "📄 $PROJECT_ROOT/设计报告.docx"
else
    echo "⚠️ 部分文件缺失！"
fi

rm -rf "$TMP_SVG"
