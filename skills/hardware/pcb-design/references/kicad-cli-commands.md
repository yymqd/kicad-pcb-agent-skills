# kicad-cli 快速命令参考（KiCad 10.0+）

## 汇总

所有命令汇总：

| 用途 | 命令 |
|------|------|
| PCB DRC 检查 | `kicad-cli pcb drc board.kicad_pcb -o report.rpt --units mm --all-track-errors --exit-code-violations` |
| SVG 导出（PCB 布局） | `kicad-cli pcb export svg board.kicad_pcb -o /tmp/pcb.svg --layers "F.Cu,F.SilkS,Edge.Cuts" --fit-page-to-board` |
| PDF 导出（PCB 布局） | `kicad-cli pcb export pdf board.kicad_pcb -o /tmp/pcb.pdf --layers "F.Cu,B.Cu,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts"` |
| 3D 渲染 | `kicad-cli pcb render board.kicad_pcb -o /tmp/render.png --side top --width 1600 --height 1200 --quality high` |
| 3D GLB 导出 | `kicad-cli pcb export glb board.kicad_pcb -o /tmp/board.glb --include-tracks --include-pads --include-zones --include-silkscreen --include-soldermask` |
| Gerber 导出 | `kicad-cli pcb export gerbers board.kicad_pcb -o /tmp/gerber/ --common-layers` |
| 钻孔文件 | `kicad-cli pcb export drill board.kicad_pcb -o /tmp/gerber/` |
| 元件位置 CSV | `kicad-cli pcb export pos board.kicad_pcb -o positions.csv --format csv --units mm --bottom-negative --side front` |
| 板统计 | `kicad-cli pcb export stats board.kicad_pcb -o stats.rpt --units mm` |
| 原理图 SVG | `kicad-cli sch export svg board.kicad_sch -o /tmp/svg_out/` |
| 版本升级 | `kicad-cli pcb upgrade board.kicad_pcb` |
| 项目创建 | `kicad-cli project new --name project_name --output /tmp/` |
| 项目同步 | `kicad-cli project sync-symbol-lib project.kicad_pro` |

## pcb drc

```bash
kicad-cli pcb drc <file.kicad_pcb> [options]
```

**选项**：
- `--output <path>` — 输出文件路径（默认 stdout）
- `--format report|json` — 输出格式（默认 report 文本）
- `--units mm|in|mil` — 单位
- `--all-track-errors` — 全部走线错误（默认只报每个网络第一条）
- `--severity-error|warning|all` — 过滤级别（默认 error）
- `--exit-code-violations` — 有违规时退出码非零（用于 CI）
- `--refill-zones` — 检查前重新填充覆铜（处理 stale zone 数据）
- `--save-board` — 检查后保存板（和 --refill-zones 搭配使用）

## pcb export svg

```bash
kicad-cli pcb export svg <file.kicad_pcb> -o <path> [options]
```

**选项**：
- `--layers "F.Cu,F.SilkS,Edge.Cuts"` — 要包含的层
- `--page-size-mode 2` — 2=适应板框, 0=A4, 1=用户定义
- `--fit-page-to-board` — 页面适应板框大小
- `--exclude-dnp` — 排除 Do-Not-Populate 元件

**注意**：`pcb export svg -o` 的路径是**文件**（区别于 sch export svg）。

## pcb render

**KiCad 原生光线追踪渲染器**。无需 trimesh/matplotlib 等第三方库。

```bash
kicad-cli pcb render <file.kicad_pcb> -o <output.png> [options]
```

**选项**：
- `--side top|bottom|left|right|front|back` — 视角方向
- `--width <px> --height <px>` — 输出分辨率
- `--quality basic|high` — 渲染质量（basic 较快）
- `--background transparent|opaque` — 背景
- `--preset <name>` — 预设配置（字符串键值对配置）
- `--center` — 居中模型（默认自动居中）

## pcb export gerbers

```bash
kicad-cli pcb export gerbers <file.kicad_pcb> -o <output_dir/>
```

**选项**：
- `--common-layers` — 使用通用层名（F_Cu, B_Cu 等）
- `--no-x2` — 不使用 X2 格式（与某些打样厂兼容性）
- `--subtract-soldermask-from-silk` — 丝印避开阻焊开口

## pcb export glb

```bash
kicad-cli pcb export glb <file.kicad_pcb> -o <output.glb> [options]
```

**选项**：
- `--board-only` — 仅板框（无元件）
- `--include-tracks` — 包含走线
- `--include-pads` — 包含焊盘
- `--include-zones` — 包含覆铜区
- `--include-silkscreen` — 包含丝印层
- `--include-soldermask` — 包含阻焊层
- `--include-edges` — 包含板边
- `--subst-models` — 用 3D 封装模型替代（需要封装库有 3D 文件）

## sch export svg

```bash
kicad-cli sch export svg <board.kicad_sch> -o <output_dir/>
```

**⚠️ `-o` 路径是目录不是文件！** 实际 SVG 文件以项目名命名在该目录下。
例如：`kicad-cli sch export svg project.kicad_sch -o /tmp/svg_out/` 创建 `/tmp/svg_out/project.svg`。
需要手动移动：
```bash
mv /tmp/svg_out/*.svg /tmp/schematic.svg
```

## project new

```bash
kicad-cli project new --name <name> --output <dir/>
```

创建项目骨架（`.kicad_pro` + `.kicad_sch` + `.kicad_pcb` 空文件）。
必须配合 `--name` 参数，不能省略。`--output` 指定目录。

## 典型管线（单板设计完整输出）

```bash
# 0. 创建项目（可选，可以用已生成的文件）
kicad-cli project new --name laser_driver --output /tmp/

# 1. DRC 验证
kicad-cli pcb drc laser_driver.kicad_pcb -o drc.rpt --units mm --all-track-errors

# 2. Gerber 钻孔
kicad-cli pcb export gerbers laser_driver.kicad_pcb -o gerber/
kicad-cli pcb export drill laser_driver.kicad_pcb -o gerber/

# 3. SVG 预览（PCB 布局）
kicad-cli pcb export svg laser_driver.kicad_pcb -o exports/pcb_top.svg \
  --layers "F.Cu,F.SilkS,Edge.Cuts" --fit-page-to-board

# 4. 3D 渲染
kicad-cli pcb render laser_driver.kicad_pcb -o exports/pcb_3d.png \
  --side top --quality high

# 5. 3D GLB 模型
kicad-cli pcb export glb laser_driver.kicad_pcb -o exports/pcb_3d.glb \
  --include-tracks --include-pads --include-silkscreen --include-soldermask

# 6. 板统计
kicad-cli pcb export stats laser_driver.kicad_pcb -o exports/board_stats.rpt --units mm

# 7. 元件位置
kicad-cli pcb export pos laser_driver.kicad_pcb -o exports/positions.csv \
  --format csv --units mm --bottom-negative

# 8. 打包打样文件
zip -j gerber.zip gerber/*

# 9. SVG → PNG（用于报告嵌入）
python3 -c "import cairosvg; cairosvg.svg2png(url='exports/pcb_top.svg', write_to='exports/pcb_top.png', scale=3.0)"
```

## 注意事项

1. **Gerber 文件名 = 层名**：`laser_driver-F_Cu.gbr`, `laser_driver-B_Cu.gbr` 等。钻孔文件名为 `laser_driver.drl`。Gerber zip 前确保所有 7 层都存在。
2. **渲染时机**：先 Save 再 render，否则渲染的是保存前的版本。
3. **SVG→PNG**：WSL 上用 `cairosvg` (pip install) 或 `rsvg-convert` (apt install librsvg2-bin)。
4. **`kicad-cli` 不支持**：布局摆放（place）、布线（route）和覆铜（zone fill）——这些必须通过 pcbnew Python API 完成。
5. **路径中文字符**：将输入输出限制在 `/tmp/` 下，避免中文字符路径导致 terminal workdir 报错。
