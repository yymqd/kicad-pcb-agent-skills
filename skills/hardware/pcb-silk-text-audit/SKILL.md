---
name: pcb-silk-text-audit
description: PCB silk text bounds audit — r_max, not center point.
trigger: "User asks to place, move, or verify silkscreen text on a PCB (版本号/丝印/位号/Reference/Value), especially on small (<Ø20mm) or circular boards, or when DRC shows silk issues and text may be milled off the board edge."
---

# PCB 丝印文字板内验证（Silkscreen Text Bounds Audit）

**上游路由**: 由 pcb-design（伞形主 skill）在 Phase 5b/审查 F.10 触发；本 skill 是聚焦 skill，只处理丝印文字包围盒审计。完整设计/审查回 pcb-design。

## ⛔ 核心铁律：文字板内判据 = 包围盒 r_max，不是文字中心点

**文字中心在板内 ≠ 文字在板内。** 2026-07-31 真实案例（Ø14mm 圆板）：版本号 21 字符 × 1.0mm 字号，中心放 (-3.5,-5.5) 距圆心 r=6.52mm "看着板内"，但文字总宽 ≈ 13mm，包围盒最外角 **r_max = 12.21mm** —— 远超 7mm 板半径，加工时整段被铣掉。多个历史版本（v9/v10/v11）全部踩同一坑，因为**只验证了文字中心点半径**。

## 包围盒计算

- **字符宽度 ≈ 0.62 × 字号高度**（KiCad 默认字体实测；保守取 0.65）
- 水平放置：`w = 字符数 × 0.62 × 字高`，`r_max = hypot(|x| + w/2, |y| + h/2)`
- 旋转 ±90° 时宽高互换（`w, h = h, w`）
- **判据：r_max < 板半径 − 安全边距**（Ø14mm 板取 6.9mm 安全线，即文字最外缘离板边 ≥0.1mm）

## 审计必须覆盖三类文字

1. 板级 `PCB_TEXT`（版本号、注释）
2. 每个 footprint 的 **Reference** 字段
3. 每个 footprint 的 **Value** 字段

⚠️ **封装 Reference/Value 字段默认位置在焊盘外侧 ~1.65mm**（如 TestPoint_Pad_D1.5mm），边缘测试点的 ref 会直接落出板外（实例：TP5.Ref 中心 r=7.21mm，r_max=7.97）。DRC 的 silk_edge_clearance 只覆盖部分情形，**文字包围盒审计是确定性验证**，不可省。

## 长版本号处理（小圆板）

Ø14mm 板上 >10 字符、字号 ≥1.0mm 的水平文字**必然超边**（板直径才 14mm）。处理配方：

- 拆成两条 PCB_TEXT：板号 + 版本（如 `520nmLD` @(0,-4.3) + `v2.0` @(0,-5.2)）
- 字号降到 0.8mm（12 字符 × 0.8 × 0.62 ≈ 6mm 宽可放下）
- 日期移出丝印（保留在报告/文件名中）；0.6mm 丝印目检已困难，仅 ≤8 字符可考虑

## 修复手法

- TP 的 Reference/Value 超边 → 移到焊盘**朝圆心方向** 1.0–1.5mm 处，保持与焊盘的关联可读
- 移动后必须重新审计 r_max 全绿 → 重跑 DRC → **重新导出 Gerber**（Gerber 是静态快照，不会自动跟踪 PCB 变更；F_Silkscreen.gto 大小变化可佐证已更新）

## 执行步骤

1. 审计：`python scripts/audit-silk-text-bounds.py <board.kicad_pcb> [板半径] [安全边距]`
   （Windows 端用 `<KiCad>/bin/python.exe` 跑，WSL 端 pcbnew 不可用）
2. 修复：移动/拆分/缩字号，直到审计输出 `0 条超边`
3. DRC：`kicad-cli pcb drc --format json --severity-all`，**放行标准只看功能级**：`shorting_items=0`、`unconnected_items=0`；`silk_overlap`/`silk_over_copper`/`clearance` 在密布局小板上接受（制造级违规，目检可读即可——用户明确认可此标准）
4. 重新导出 Gerber + 钻孔 + 打包 zip（时间戳必须晚于 PCB 保存时间）

## Pitfalls

- **只移中心点不动字号/文字内容** → 超边依旧（本次 v10/v11 失败根因）
- **盲目"恢复到上次良好状态"** → 上次状态可能从未验证过包围盒（v9 假象），恢复前先审计目标快照
- **审计脚本漏掉 footprint 字段** → TP ref/value 超边漏网（本次 6 条超边中 5 条是字段类）
- **逐条微调位置易陷入泥潭**（用户明确反感反复微调）→ 一次性把**全部**超边文字批量朝圆心放置（TP ref/value → 焊盘朝圆心方向 1.0–1.5mm；版本号 → 拆条/缩字号），然后**单次重审计**收敛到 0；不要一条一条试坐标。判定优先级：文字超边=实质问题必须修；silk_overlap/silk_over_copper=制造级违规接受即可，不要为它们继续调位置
- 并行调用多个工具时 `DaemonThreadPoolExecutor` 报错 → 改为串行单次调用
- 版本号文字在 PCB 上旋转 90° 竖排通常更糟（高度 = 字符数 × 字高，21 字符 × 1mm = 21mm）

## 支持文件

- `scripts/audit-silk-text-bounds.py` — 圆板丝印文字包围盒审计脚本（可传板半径/安全边距参数）

## 关联

- `pcb-design` skill（用户自有，含 small-circular-pcb-guide.md 参考）覆盖同类 PCB 工作流；本 skill 是其丝印验证缺口的独立落点。若 `pcb-design` 被 `hermes curator adopt` 接管，应将本节合并回其 `references/small-circular-pcb-guide.md` §6。
