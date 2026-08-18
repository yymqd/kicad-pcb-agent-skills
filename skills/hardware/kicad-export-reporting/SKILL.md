---
name: kicad-export-reporting
description: KiCad 图形导出与报告制图（走线图/3D 渲染/SVG 颜色处理/Word 报告）。
trigger: "User asks to generate PCB images/reports from a KiCad board: routing/track maps (top/bottom), 3D renders, design reports (Word/Markdown), or export SVG/PNG with visible traces. Also triggers on '走线图/3D渲染图/设计报告' requests."
---

# KiCad 图形导出与报告制图

把 KiCad 板子产出为报告图片与文档。2026-07-31 520nmLD 项目实测（Ø14mm 双面板）。
合并自原 kicad-design-docs / kicad-visual-export / kicad-export-rendering。

**上游路由**: pcb-design（主 skill）在文档/交付阶段（管线 A）触发；本 skill 是聚焦 skill，只处理"从板子到图片/文档"。完整设计/审查回 pcb-design。

## 用户偏好（先记住，勿违背）

1. **走线图/3D 图必须由 kicad 生成**（`kicad-cli pcb export svg` / `pcb render`）——不要用 matplotlib 手画替代（用户明确否决过 matplotlib 版）
2. **双面走线图样式必须统一**：顶层 F.Cu 和底层 B.Cu 用同样的视觉语言（白/浅底 + 同色走线 #C83434 红）
3. **底层图镜像为底视角**：`PIL Image.transpose(Image.FLIP_LEFT_RIGHT)`（KiCad SVG 默认顶视角画 B.Cu）
4. 底层走线图不显示覆铜/过孔环（会显得"器件很多、乱"）；走线数据须与 pcbnew 实测一致
5. 覆铜真实视图用 3D 渲染展示（走线图与 3D 图互补）
6. Word 报告用 python-docx：中文字体必须设 `run._element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')`（仅设 font.name 中文不生效）

## 1. 双面走线图（kicad-cli SVG + 最小后处理）

### 导出命令
```bash
kicad-cli pcb export svg board.kicad_pcb -o top.svg --layers F.Cu,Edge.Cuts --page-size-mode 2 --fit-page-to-board
kicad-cli pcb export svg board.kicad_pcb -o bottom.svg --layers B.Cu,Edge.Cuts --page-size-mode 2 --fit-page-to-board
```

### ⚠️ 颜色问题（KiCad 10.0.3 实测）
- **F.Cu 走线**：`fill:#C83434`（深红）白底清晰 ✅
- **B.Cu 走线**：`stroke:#4D7FC4`（浅蓝）+ `stroke-width:0.2000` 白底几乎不可见 ❌ —— 用户会误判"底层没有走线"
- 同一 SVG 两种绘制方式（F.Cu fill 实心 / B.Cu stroke 描边），后处理必须分别处理

### 尝试过的 kicad 原生设置（全部无效，勿再试）
| 路径 | 结果 |
|---|---|
| `--theme <名/路径>`（KiCad Classic/自定义/默认） | 导出结果完全相同，未生效 |
| 用户主题文件 `%APPDATA%/kicad/10.0/colors/<name>.json`（`kicad_color_settings.pcb_editor.Layers` 注意 L 大写） | 不被 kicad-cli 加载 |
| `pcbnew.GetColorSettings(name)` API | 卡死 |
| 改 pcbnew.json `color_theme` | 只影响 GUI |

（后续 KiCad 版本可能修复 --theme；使用前先测。）

### SVG 结构（后处理依据）
- 走线组：`<g style="fill:none; stroke:#4D7FC4; stroke-width:0.2000;...">` 多 path（stroke 继承组色）
- **GND 覆铜是独立 path**：`<path style="fill:#4D7FC4; ...fill-rule:evenodd;">`——可能在 g 组内自带 style 覆盖组色，用 `evenodd` 特征递归识别删除
- 焊盘/过孔环：紫色 `stroke:#C872AB` 组 + circle
- 无背景 rect（透明）→ cairosvg 转 RGB 变黑，需插 `<rect width="100%" height="100%" fill="white"/>`
- 走线 stroke-width 0.2 低分辨率渲染丢失 → cairosvg scale≥6 或后处理加粗到 2.0
- 大量 path 不带 style——颜色从父级 `<g>` 继承

### 踩过的坑
- `--scale 10` 导出：坐标×10 但 viewBox 不变 → 内容出界被裁剪（渲染 0 像素）
- sed/正则改色失败：g 组嵌套 + 覆铜 path 自带 style
- 只改 fill 不改 stroke：B.Cu 走线是 stroke，改 fill 无效
- cairosvg 渲染细 stroke（0.2）几乎丢失 → 必须加粗到 2.0
- 渲染结果与源文件矛盾时：查 md5（可能缓存/旧文件）+ grep 残留颜色

### ✅ 正确修图流程（XML 解析，非正则）
```python
import xml.etree.ElementTree as ET
ET.register_namespace('', 'http://www.w3.org/2000/svg')
tree = ET.parse('bottom.svg'); root = tree.getroot()
# 1. 走线组: stroke:#4D7FC4 → #C83434, stroke-width 0.2 → 2.0
# 2. 删除其他 g 组（只保留含 #D0D2CD 的 Edge.Cuts 组）
# 3. 递归删除所有 style 含 evenodd 的 path（覆铜）: for p in root.iter()
# 4. <svg> 后插白色背景: <rect width="100%" height="100%" fill="white"/>
# 5. cairosvg.svg2png(bytestring=svg, scale=6.0)（scale≥6 保证走线可见）
```
**验证**：numpy 统计颜色占比——红 >0.3% 走线可见；白底 >60%；无 #4D7FC4 残留。

## 2. 3D 渲染

```bash
kicad-cli pcb render board.kicad_pcb -o render.png --side top --width 1600 --height 1600 --quality high
# 也可 --side bottom --width 1200 --height 1200
```

### 去丝印文字（kicad 原生：临时板副本隐藏丝印层）
kicad-cli render 无"关丝印"选项（--preset 预设系统未配置时无效）。**用临时副本**：
```python
import shutil, pcbnew
shutil.copy(src, dst)
b = pcbnew.LoadBoard(dst)
# 所有 'Silk' 层对象（板级 drawings / fp GraphicalItems / Reference / Value）
# SetLayer(pcbnew.F_Fab) 移走 —— 不要 Remove（Remove 触发 swig 容器失效）
b.Save(dst)   # 原板不动
```
注意：`PCB_SHAPE` 无 `SetVisible`；`board.Remove`/`fp.Remove` 后 GetTracks/Pads/GraphicalItems 全失效——先收集再删或一律 SetLayer 移走。

### 底层 3D 看不到走线 = 物理事实
B.Cu 走线被绿色阻焊层覆盖，任何渲染/实物都看不到铜线。展示走线用走线图，3D 图只展示外观。

## 3. 中文 Word 设计报告（python-docx）

- 中文字体：`style.element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')` + 每个 run 同样设置（set_cn 辅助函数）
- 文件被 Word 打开时 save() 抛 PermissionError → 存新版本号文件名（v2.2→v2.3→…），别反复重试；提醒用户关旧文件后清理
- 表格：`doc.add_table` + style `'Light Grid Accent 1'`，表头加粗 9.5pt、正文 9pt
- 图片：`doc.add_picture(path, width=Cm(9))` + `doc.paragraphs[-1].alignment = CENTER`
- 报告结构（15 章模板）：设计规格 → 系统架构(+原理图) → 元件清单(+布局坐标) → 参数计算(+危害分析表) → 仿真验证 → PCB 设计(+引脚功能+网络表) → 3D 渲染(顶/底) → 走线图(顶/底) → 制造信息 → 审计与修复 → 测试计划 → 已知妥协 → 需求追溯矩阵 → 版本历史 → 交付清单

## 4. matplotlib 示意图（无 EDA 原理图时的呈现）

- **中文字体陷阱**：WSL venv matplotlib 默认 DejaVu Sans 无中文字形 → 图内中文变方块 → 用英文标题（或装 Noto Sans CJK）
- 可用 matplotlib 手绘规范电路图（矩形/三角/线符号），基于电路连接定义绘制，替代正式 EDA 原理图；标注"网络表为权威定义"

## 5. ⛔ 手写 .kicad_sch 原理图文件不可行（教训）

从网络表手写 KiCad 10 原理图 S-expression（lib_symbols + symbol 实例 + net_label）调试 6 轮仍加载失败：语法细节多（`(pin_numbers (hide yes))`、lib_symbols 内 pin 无 uuid、实例 pin 带 uuid、图形/引脚分单元结构），空 symbol 也失败。
**结论**：原理图走 KiCad GUI 整理或验证过的生成工具链；网络表（电路连接定义.md）作数据源，matplotlib 画规范电路图用于报告。

## Pitfalls

1. 中文路径 → 导出/脚本放纯 ASCII 路径
2. 渲染/导出前先确认板文件已保存（渲染的是磁盘版本）
3. SVG 后处理必须 XML 解析，正则删组不可靠
4. docx 被占用 → 新版本号，不重试覆盖
5. matplotlib 图内避免中文（无 CJK 字体时）
