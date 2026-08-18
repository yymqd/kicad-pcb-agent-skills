---
name: pcb-design
description: Complete PCB design automation for Hermes Agent. Natural language to circuit/KiCad/PCB workflow — schematic capture, SPICE simulation, component selection, PCB layout, EMC checks, BOM management, and Gerber export.
trigger: "User asks to design a circuit or PCB, mentions KiCad, schematic, layout, routing, EMC, BOM, Gerber, or fabrication. Also triggers on: user asking how you would design a specific circuit/board, or any conceptual planning question about a circuit/PCB — load BEFORE formulating any plan, not after."
---

# pcb-design — PCB Design Agent

Full-stack PCB design automation. Turn natural language descriptions into production-ready KiCad files.

## ⛔ 核心铁律（MANDATORY — 每次操作前先读，违反 = 该次交付有缺陷）

**铁律 1：每步操作先查手册，再动手。**
- 任何 KiCad 操作（CLI/MCP/API）动手前，先读对应操作手册：
  `<KICAD_MCP_SERVER_DIR>\docs\` 下的
  PCB_DESIGN_WORKFLOW / SCHEMATIC_TOOLS_REFERENCE / ROUTING_TOOLS_REFERENCE /
  EXPORT_TOOLS_REFERENCE / WINDOWS_TROUBLESHOOTING
- 或本 skill `references/` 对应文件、`kicad-cli xxx --help`、官方文档
- 不查手册 = 凭记忆 = 高风险 = 违反 MANDATORY

**铁律 2：每完成一个工序，先审计，审计通过才进下一步。**
- 工序粒度 = 单个操作（一次布线、一次导出、一次选型），不是整个 Phase
- 每个工序完成后：`[审计证据] → [再审计证据(独立方法)] → [判定]` 三段式输出
- 判定未通过 → 修复 → 重新审计 → 才允许进入下一个工序
- Phase 级门控表（Phase 0-9 → A-N 审查类）见下方「强制阶段门控协议」
- 审计执行细节见「审计协议 v3.1」（期望值溯源、再审计方法库、双分类输出）

## Prerequisites

- **KiCad 7.0+** installed (`kicad-cli --version` to verify)
  - **Current stable**: KiCad **10.0.5** (as of 2026-08)
  - **Windows 安装路径**: `<KICAD_DIR>\`
  - **kicad-cli 路径**: `<KICAD_DIR>\bin\kicad-cli.exe`
  - **KiCad 7 vs 8/9/10 API differences are significant** — see `references/kicad7-pcbnew-api.md`
  - **WSL 升级路径**：WSL Ubuntu 24.04 apt 默认仅提供 KiCad 7.0.11。要升级到 10.0.3，使用官方 PPA：
    ```bash
    sudo add-apt-repository --yes ppa:kicad/kicad-10.0-releases
    sudo apt update
    sudo apt install --install-recommends kicad
    kicad-cli --version   # 验证：10.0.3
    ```
    PPA 会自动替换 apt 旧版本，无需先卸载。升级后旧的 apt 源记录会保留但 PPA 版本优先级更高。
  - Windows 推荐直接装最新版 → 从 KiCad 官网或国内镜像下载（见 `references/kicad-download-china.md`）
  - **从 WSL 调用 Windows KiCad CLI** 见 `references/wsl-windows-kicad-bridge.md`
- Python packages: `PySpice`（注意大小写，import 用 `PySpice` 不是 `pyspice`）, `sexpdata`
- Ngspice: `sudo apt install ngspice`（WSL 用 apt，Windows 用官方安装包）
- （可选）mixelpixx/KiCAD-MCP-Server for full PCB automation（KiCad 8+ 专用）

## ⛔ 核心执行路线（MANDATORY — 违反 = 该次交付有缺陷）

**KiCad 执行优先级（2026-06-05 确立，基于 WSL Wayland 环境）：**

```
kicad-cli 能做的         → kicad-cli 做
kicad-cli 做不了的       → pcbnew Python 模块（KiCad 官方 API）做
GUI 交互操作             → 鼠标点击可行(xdotool click ✅)，键盘事件被拦截(key/shortcut ❌)
```

### kicad-cli 可用命令一览

| 命令 | 用途 |
|:-----|:-----|
| `kicad-cli pcb drc <file>` | DRC |
| `kicad-cli pcb export gerbers <file>` | Gerber |
| `kicad-cli pcb export svg <file>` | 预览图 |
| `kicad-cli pcb export pdf <file>` | PDF |
| `kicad-cli pcb export stats <file>` | 统计报告 |
| `kicad-cli pcb export pos <file>` | 位置表 |
| `kicad-cli pcb export glb <file>` | 3D 模型 |
| `kicad-cli pcb render <file>` | 3D 渲染 |
| `kicad-cli pcb export drill <file>` | 钻孔 |
| `kicad-cli pcb upgrade <file>` | 升级格式 |

### pcbnew Python 模块适用场景

`/usr/lib/python3/dist-packages/pcbnew.py` 是 KiCad 自带的 Python 绑定，和 GUI 共用同一套底层代码。它不是第三方脚本。用在 kicad-cli 覆盖不了的场景：

- 创建板文件、摆放元件、布线（`BOARD`、`FOOTPRINT`、`PCB_TRACK`）
- 加载标准库封装（`FootprintLoad()`）
- 分配网络（`PAD.SetNet()`）
- 操作覆铜（`ZONE`）
- 导出 DSN 自动布线文件（`ExportSpecctraDSN()`）

### 🚫 禁止的操作

- 不要尝试用 xdotool/xte/wtype 发送键盘事件自动化 KiCad GUI（Wayland 下按键事件被拦截）。鼠标点击(xdotool click)可行但仅在非模态窗口时有效，优先走 pcbnew/kicad-cli
- 不要让用户手动操作 GUI（"你在 KiCad 中按 F7"——这是违规）
- 不要从零创建裸焊盘封装替代标准库封装（用 `FootprintLoad()`）
- **绝不自己写脚本去做 KiCad 该做的事** — 所有能让 kicad-cli 或 pcbnew 完成的操作，必须交给它们。自行编写坐标计算、走线生成、数据验证脚本属于违规。pcbnew Python 模块本身不是违规——它是 KiCad 的官方 API——但在它上面再包一层自己的逻辑（比如硬编码坐标、手动算焊盘位置）就是违规。

## 设计审查清单（MANDATORY — 交付前逐项执行）

### 核心思维模型

```
EVERY PIN  ×  EVERY PART  ×  EVERY NET  ×  EVERY CONNECTION
 每个引脚      每个元件       每个网络       每个接口
```

### 使用规则

1. **每次审查从 A 到 N 逐类执行，不跳类、不跳项**
2. 每项标记 ✅ 通过、❌ 失败、N/A 不适用
3. **通过标准**：每项的"判据"列定义了明确的可量化边界。不可量化的检查（如"走线是否美观"）不属于审查范畴
4. **数据来源**：所有判据必须有可追溯的来源（数据手册页码、行业标准编号、计算结果）
5. **通过条件**：**所有项标记 ✅ 或 N/A**，任何一项 ❌ 必须修复后才能声称设计完成
6. **⛔ 铁律：每次审查从头实际执行每项，不能相信前一轮的结果。** 一个项目可能经过多轮审查，但每一轮都必须从 A.1 开始逐项实际验证——"上次查过了"不是跳过项的理由。不实际执行就标记 ✅ = 这个审查体系形同虚设。
7. 审查中发现 checklist 未覆盖的新问题类型，**立即追加到对应类中**

### ⛔ 审计协议 v3.1（2026-07-31 两次执行后完善 — MANDATORY）

**背景**：v3.0/v3.1 两次执行暴露 6 个缺陷：审计者猜期望值导致假阳性（D1 极性被误判接反）、再审计方法未预定义形同虚设、审计者错误与设计缺陷混计、数据源缺失无分级处理、门控粒度没写死、差异处理顺序未规定。以下 A-F 为强制的审计执行规则：

**A. 期望值溯源铁律（防审计者污染结论）**
- 审计中构造的**每个期望值**（引脚号、网络归属、元件值、极性、参数、阈值）必须标注来源：手册页码 / 权威源（TI/Vishay 官方页、立创规格页）/ 独立复算
- **无来源的期望 = 无效断言** → 先查手册再判定。禁止"凭经验猜"期望值
- 案例：R2 再审计猜 MT3608/TLV9301 引脚号 → 6 网络拓扑假性 ❌、D1"疑似接反"假阳性；手册校正后全部正确

**B. 再审计方法库（每项必须独立再审计）**
- 每项审计完成后必须再审计，**再审计方法必须与首查方法不同**（不同工具/不同公式/不同数据源/发散扫描/跨源交叉）
- 预定义方法库：①手册原文复核（翻页找原始段落）②独立复算（不引用设计文档的公式路径）③第三工具提取（S-expression 解析 vs pcbnew API）④发散扫描（清单外维度）⑤跨源交叉（PCB↔BOM↔网表↔手册）⑥官方/第三方规格页（立创、TI、JLC 官网）
- **三段式输出**：`[审计证据] → [再审计证据(独立方法)] → [判定]`，三段缺一不可，缺失即未完成该审计项，**禁止进入下一项**（串行门控）

**C. 双分类输出（防假阳性/假阴性污染）**
- 审计发现分两类记录：**Design Defect**（设计缺陷）与 **Audit Error**（审计自身错误：猜期望、方法缺陷、数据错位）
- Audit Error 只校正期望并重测，**不计入设计缺陷统计**；但必须记录（含校正后的重测结果）

**D. 数据源完整性分级（S0 前置）**
- 审计前先做数据源完整性检查，按关键度分级：
  - **关键缺失**（需求文档、原理图）：原理图缺失 = 结构性缺陷，**必须显式标注**（"PCB 为唯一电路定义"），建议补原理图；需求缺失 = 阻断审计
  - **非关键缺失**（器件手册）：走降级策略——权威第三方数据（TI/立创官方页）+ **不确定度标注**，且大应力余量（≥3x）方可放行
- 手册获取状态动态跟踪：一旦补获（如 TLV9301 61 页 TI 手册），降级解除并复核

**E. 差异处理顺序（假阳性防护）**
- 再审计发现差异时，**先验证审计者期望是否正确（查手册/权威源），再判定设计是否错误**
- 顺序固定：①校正期望 ②重测 ③若仍差异 → 判设计缺陷。禁止直接判 ❌

**F. 闸门判定与妥协管理**
- 验收闸门：决策缺失=0、依据缺失=0、层间冲突=0、数据源完整性达标
- 任何 ❌ 必须修复或转为**受控妥协**（含：影响量化 + 复审触发条件 + 过期时间），裸记录不算受控
- 闸门未全绿时不得声称"设计完成"，只能声称"满足功能要求 + 遗留受控项"

---

### A — 需求回溯

| 编号 | 检查项 | 判据/标准 | 数据来源 |
|:----:|:-------|:----------|:---------|
| A.1 | 规格书逐条对照 | 每一条需求有对应的设计实现，无遗漏 | 规格书 PDF |
| A.2 | 设计指标量化 | "自适应""可调"等模糊描述有明确的数值范围 | 设计文档 |
| A.3 | 未明确的需求 | 工作温度、寿命、认证要求已定义或标注"待定" | 产品定义 |

### B — 电路拓扑

| 编号 | 检查项 | 判据/标准 | 数据来源 |
|:----:|:-------|:----------|:---------|
| B.1 | 拓扑选型理由 | 所选电路拓扑有明确的技术理由（效率/成本/尺寸） | 设计笔记 |
| B.2 | 标准应用电路对照 | 每颗 IC 的外围电路与数据手册典型应用差异 ≤ 1 个元件 | 数据手册典型应用图 |
| B.3 | 上电时序 | 各电压轨建立顺序符合 IC 要求，无锁定/冲突 | 数据手册 Power-Up Sequence |
| B.4 | 故障模式分析 | 每个关键器件短路/开路时，电路不会损坏其他元件或造成安全隐患 | 电路分析 |
| B.5 | 保护电路完整性 | 每个外部接口至少有一种保护（ESD/过流/反接） | ESD 标准 IEC 61000-4-2 |
| B.6 | 去耦旁路 | 每颗 IC 至少有一个 100nF 去耦电容，距电源引脚 < 5mm | 数据手册 Layout Guide |

### C — 元件选型

| 编号 | 检查项 | 判据/标准 | 数据来源 |
|:----:|:-------|:----------|:---------|
| C.1 | IC 每引脚电压 < ABS MAX | 供电/输入/使能引脚电压 < 数据手册 Absolute Maximum Ratings | 数据手册 §Absolute Max |
| C.2 | IC 每引脚电流 < 额定 | 输出驱动电流 < 数据手册额定值 × 0.8 | 数据手册 Electrical Characteristics |
| C.3 | 晶体管 Pin-to-Pad 对照 | 封装 pad 编号 vs 数据手册引脚定义完全一致 | 数据手册 Pin Configuration + KiCad 封装 |
| C.3a | **⛔ 预期值独立性审查** | 审计脚本中的"期望值"不能来自被审代码本身——必须从数据手册独立提取后写入审计脚本。如果审计脚本和被审代码都错了同一个数，审查形同虚设 | 数据手册 + 独立验证（不相干的第三来源，如封装库文档） |
| C.4 | 电阻功率降额 | I²R < 封装额定功率 × 0.8 | 封装规格（0603=0.1W, 0805=0.125W, 1206=0.5W）|
| C.5 | 电容耐压降额 | Vmax × 1.5 < 电容额定电压 | 电容规格书 |
| C.6 | 电感饱和电流 | I_peak < I_sat × 0.8 | 电感规格书 |
| C.7 | 工作温度范围 | 所有元件的额定温度覆盖产品目标温度范围 | 各元件数据手册 |
| C.8 | 物料可采购性 | 元件在目标代工厂（JLCPCB/LCSC）基础库中或可扩展库下单 | LCSC 网站 |
| C.9 | 采购料号 | BOM 中已标注 LCSC# 或 MPN | LCSC / 供应商网站 |

### D — 电路参数

| 编号 | 检查项 | 判据/标准 | 数据来源 |
|:----:|:-------|:----------|:---------|
| D.1 | DC-DC 输出电压 | Vout = Vref × (1+Rtop/Rbot)，误差 < ±5% | 数据手册 FB 电压 |
| D.2 | DC-DC 电感值 | L = Vin×D / (fsw×ΔI)，ΔI < 0.4×Iin | 数据手册电感选型 |
| D.3 | DC-DC 补偿 | 环路补偿网络按数据手册计算步骤执行 | 数据手册 Compensation |
| D.4 | 恒流/限流设定 | I = Vref / Rsense，在目标值 ±10% 内 | 设计计算 |
| D.5 | 分压/偏置网络 | Vout = Vin × R2/(R1+R2)，考虑 R 容差 | 电阻分压公式 |
| D.6 | 滤波器截止频率 | fc = 1/(2πRC)，与信号频率相差至少 10× | 滤波器设计 |
| D.7 | 反馈补偿 | 运放反馈环检查是否需要补偿电容（Ccomp） | 运放数据手册 Stability |

### E — 仿真验证

| 编号 | 检查项 | 判据/标准 | 数据来源 |
|:----:|:-------|:----------|:---------|
| E.1 | DC 工作点 | 仿真中所有节点电压不超过器件额定值的 90% | 数据手册 + 仿真报告 |
| E.2 | AC 频率响应 | 闭环带宽 > 目标频率 × 3，相位裕度 > 45° | 仿真报告 |
| E.3 | 瞬态响应 | 上电过冲 < 10%，稳定时间 < 1ms | 仿真报告 |
| E.4 | 模型保真度 | 仿真模型与真实器件的差异已列明（如运放无 VCC 引脚） | 模型说明 |
| E.5 | 最坏情况分析 | 元件容差 ±5%/±1%/±20% 下，输出变化 < 目标值 ±15% | 蒙特卡洛或极值分析 |

### F — PCB 布局

| 编号 | 检查项 | 判据/标准 | 数据来源 |
|:----:|:-------|:----------|:---------|
| F.1 | 板框尺寸 | 与规格一致，误差 < ±0.1mm | 规格书 |
| F.2 | 安装孔 | 位置/直径/间隙正确，螺丝头不覆盖元件 | 机械图纸 |
| F.3 | 功率回路面积 | Boost 开关回路面积 < 100mm² | PCB 布局 |
| F.4 | 敏感信号隔离 | 小信号走线距开关节点 > 1mm | PCB 布局 |
| F.5 | 参考面完整性 | GND 层无长缝隙（长度 > 2mm 即视为断裂） | PCB 布局 |
| F.6 | 去耦电容位置 | 每颗去耦电容距对应 IC 电源引脚 < 5mm | PCB 布局 |
| F.7 | 走线宽度 | 载流 = k × w × (ΔT)^0.5，IPC 2151 标准 | IPC 2151 |
| F.8 | 走线间距 | > 制造商最小间距（常规 0.1mm） | JLCPCB 能力 |
| F.9 | 过孔参数 | 孔径 > 0.3mm，焊盘 > 0.6mm | JLCPCB 能力 |
| F.10 | 丝印可读性 | 位号不重叠、不遮挡焊盘，字号 > 0.6mm | 目检 |
| F.11 | 极性标注 | 二极管、电解电容等有极性标记 | 目检 |
| F.12 | 禁布区检查 | 安装孔/板边 0.5mm 内无元件、无走线 | PCB 布局 |
| F.13 | 版本标识 | 丝印层包含板号/版本/日期 | 目检 |

### G — 热设计

| 编号 | 检查项 | 判据/标准 | 数据来源 |
|:----:|:-------|:----------|:---------|
| G.1 | 热点识别 | 功耗最大的 3 个器件的温升 < 额定温度 - 20°C | 热计算 |
| G.2 | 散热铜皮 | 功率器件对应层有大面积铜皮（> 50mm²） | PCB 布局 |
| G.3 | 热过孔 | 功率器件下方有 ≥ 4 个热过孔到散热层 | PCB 布局 |
| G.4 | 热串扰 | 发热器件距电解电容等热敏元件 > 5mm | PCB 布局 |

### H — 信号完整性 & 电源完整性

| 编号 | 检查项 | 判据/标准 | 数据来源 |
|:----:|:-------|:----------|:---------|
| H.1 | 高速信号 | tr > 1ns 时无需阻抗匹配；tr < 1ns 时需控阻抗 | SI 分析 |
| H.2 | 电源纹波 | DC-DC 输出纹波 < 负载纹波容忍度 × 0.5 | 数据手册 + 仿真 |
| H.3 | PDN 阻抗 | DC 电阻 = 0.5mm 线宽 × 长度，AC 阻抗 < 目标 Ztarget | PDN 分析 |
| H.4 | 串扰 | 平行走线长度 > 3cm 时需评估串扰 | SI 分析 |

### I — EMC/EMI

| 编号 | 检查项 | 判据/标准 | 数据来源 |
|:----:|:-------|:----------|:---------|
| I.1 | 开关节点面积 | Boost SW 节点铜皮面积最小化（< 10mm²） | PCB 布局 |
| I.2 | 输入/输出滤波 | DC-DC 输入/输出有足够容量的滤波电容 | 数据手册 Input/Output Cap |
| I.3 | 屏蔽 | 辐射超标时需屏蔽罩（低速设计通常 N/A） | EMC 测试 |
| I.4 | 板边清空 | 走线距板边 > 3× 线宽 | PCB 布局 |

### J — 可制造性 (DFM)

| 编号 | 检查项 | 判据/标准（JLCPCB） | 数据来源 |
|:----:|:-------|:--------------------|:---------|
| J.1 | 最小线宽 | > 0.1mm | JLCPCB 能力 |
| J.2 | 最小间距 | > 0.1mm | JLCPCB 能力 |
| J.3 | 最小过孔孔径 | > 0.3mm（机械钻）/ > 0.2mm（激光钻）| JLCPCB 能力 |
| J.4 | 最小过孔焊盘 | > 0.6mm（外径）| JLCPCB 能力 |
| J.5 | 元件间距 | > 0.3mm（贴片元件之间）| JLCPCB 装配能力 |
| J.6 | 板边间距 | 走线/铜皮距板边 > 0.3mm | JLCPCB 能力 |

### K — 可测试性 (DFT) & 可装配性 (DFA)

| 编号 | 检查项 | 判据/标准 | 数据来源 |
|:----:|:-------|:----------|:---------|
| K.1 | 测试点 | 关键信号（电源、反馈、输出）有测试焊盘或通孔 | PCB 布局 |
| K.2 | 调试接口 | 板载调试接口（如 ISP、UART）的引脚位置可访问 | 设计规划 |
| K.3 | 装配指引 | 元件极性/方向已标注于丝印，或附装配图 | 目检/文档 |
| K.4 | 上板测试步骤 | 关键信号的预期波形/电压已记录在测试文档中 | 测试计划 |
| K.5 | 元件方向一致性 | 同类型元件方向一致（如所有电阻 0° 或 90°）| 目检 |
| K.6 | 拼板/V-cut | 小板(< 50×50mm)需拼板，V-cut 位置标注 | DFM 规则 |
| K.7 | Mark 点 | SMT 贴片需 ≥ 3 个 fiducial mark（对角排列）| IPC 标准 |

### L — 文档 & 一致性

| 编号 | 检查项 | 判据/标准 | 数据来源 |
|:----:|:-------|:----------|:---------|
| L.1 | BOM = PCB = 报告 | 三者的元件值、封装、数量完全一致 | 交叉检查 |
| L.2 | Gerber 完整性 | 输出层数 = 设计层数，钻孔文件存在 | kicad-cli 导出日志 |
| L.3 | 生产说明 | 特殊工艺、叠层结构、阻抗要求已书面说明 | 生产文档 |
| L.4 | 仿真与实际差异说明 | 模型中做了哪些简化已列明 | 仿真报告 |
| L.5 | Gerber vs PCB 一致性 | PCB 修改后已重新导出 Gerber，未使用旧文件 | 文件时间戳 |

### O — 设计报告审计

| 编号 | 检查项 | 判据/标准 | 数据来源 |
|:----:|:-------|:----------|:---------|
| **O.1 内容完整性** | | | |
| O.1.1 | 章节完整 | 至少包含：电路原理、设计参数、PCB布局、BOM、打样指引、文件清单、测试验证（有仿真的需包含仿真章节） | 目检 |
| O.1.2 | 电路原理描述 | 含拓扑说明、各模块功能描述 | 目检 |
| O.1.3 | BOM 表完整 | 所有元件（含新增保护/补偿元件）都在表中，无遗漏 | 对照 PCB 元件清单 |
| | | | |
| **O.2 数据准确性** | | | |
| O.2.1 | BOM 值与 PCB 一致 | 报告中每个元件的型号/值/封装与 PCB 文件完全相同 | 交叉检查 |
| O.2.2 | 仿真数据真实 | 报告的仿真结果（GBW、带宽等）与实际仿真输出一致，非凭空填写 | 仿真报告 |
| O.2.3 | 参数表可复现 | 报告中每个计算公式代入实际值可得报告中结果 | 手动代入验证 |
| O.2.4 | IC 型号最新 | 报告中所有 IC 型号为最终版本（如 TLV2171 非 TLV2371） | 对照 BOM |
| | | | |
| **O.3 一致性** | | | |
| O.3.1 | BOM 数量一致 | 正文中声明的元件数与 BOM 表内行数一致 | 计数对比 |
| O.3.2 | 文件大小一致 | 报告中列出的文件大小与实际文件差异 < 10% | `ls -la` vs 报告 |
| O.3.3 | 元件位号一致 | 报告中描述的功能模块对应的位号与 PCB 丝印一致 | 对照 PCB |
| | | | |
| **O.4 图片质量** | | | |
| O.4.1 | 图片嵌入有效 | 所有 `add_picture()` 对应的实际图片文件存在且非空 | 检查文件系统 |
| O.4.2 | 图片分辨率 | 图片不模糊、文字可读（DPI ≥ 150） | 目检 |
| O.4.3 | 图片与内容对应 | 图片标题/上下文说明与图片内容一致 | 目检 |
| | | | |
| **O.5 格式规范性** | | | |
| O.5.1 | 无空表/空行 | 所有表格无空行、无空单元格 | 逐表检查 |
| O.5.2 | 标题层级正确 | 一级标题(一)、二级标题(1.1)、三级标题(1.1.1)嵌套合理 | 目检 |
| O.5.3 | 无开发过程内容 | 不含 FMEA、设计修正记录、审查问题等过程性内容 | 全文搜索关键词 |
| O.5.4 | 无过时数据 | 不含已被修正的旧值（如 TLV2371、4.7μH、0805） | 全文搜索 |
| | | | |
| **O.6 可读性** | | | |
| O.6.1 | 术语一致 | 全文对同一元件/信号的称呼一致（不混用 BST/BOOST/VOUT） | 目检 |
| O.6.2 | 单位规范 | 全文中英单位混用（mm/mil, Ω/R）统一 | 目检 |
| O.6.3 | 无 AI 痕迹 | 无"当然""值得注意的是""综上所述"等填充语 | 目检 |
| | | | |
| **O.7 文件完整性** | | | |
| O.7.1 | DOCX 可打开 | ZIP 结构完整，`word/document.xml` 解析合法 | `unzip -l` 验证 |
| O.7.2 | stylesWithEffects | 工作版保留，交付版剥离（按 `office-document-specialist` 规范）| 检查 ZIP 内容 |
| O.7.3 | 嵌入式图片数量正确 | 报告的图片数与实际嵌入数一致 | 检查 word/media/ |

### M — 设计评审签收

| 编号 | 检查项 | 确认 |
|:----:|:-------|:-----|
| M.1 | 以上所有 A-O 项已逐项执行 | □ 全部 ✅ 或 N/A |
| M.2 | 未通过项已记录并计划修复 | □ 清单附后 |
| M.3 | 设计版本号 | ___ |
| M.4 | 审查日期 | ___ |
| M.5 | 设计者 | ___ |

### N — 本次设计发现的新问题（追加到对应类中）

| 新增问题 | 归入类 | 解决方案 |
|:---------|:------|:---------|
| | | |

**每次审查从 A 到 O 逐类执行，不跳类、不跳项。** 每类完成后标记 ✅ 才能进入下一类。

如果在审查中发现 checklist 未覆盖的新问题类型，**立即追加到对应层中**——这种积累就是质量控制体系的进化。

## ⛔ 强制阶段门控协议（MANDATORY — 不可跳过）

**⚠️ 最大坑：回答概念性问题前不加载本 skill。** 用户问"你怎么设计这个电路"或"你的思路是什么"时，不要凭经验直接回答——必须先加载本 skill，因为它包含已验证的模板、已知 KiCad 版本 API 差异、以及完整的 12 阶段门控流程。先回答再补看 skill = 浪费用户时间纠正你。**加载 skill 之后再组织答复，不是反过来。**

**设计过程中，A-O 审查清单的对应类必须在对应 Phase 中完成，而不是留到最后一次性检查。**

```
Phase         对应完成审查类         说明
─────        ──────────────         ─────────────────────
Phase 0:     环境审计               工具链可用
Phase 1:     A(需求) + B(拓扑)      设计开始前明确需求和拓扑
Phase 1b:    查已有配方             复用已验证设计
Phase 2:     C(元件选型)            选型时即查引脚/应力/采购
Phase 3:     D(参数) + E(仿真)      仿真前确认参数，仿真后验证
Phase 4:     B(拓扑)交叉检查        原理图与设计一致
Phase 5:     F(布局) + G(热)        布局阶段考虑散热/隔离
Phase 5b:    J(DFM)                导出前查可制造性
Phase 6:     I(EMC)                 布局后确认 EMC
Phase 7:     C(采购)交叉检查        确认 BOM 可采购
Phase 8:     K(测试) + L(文档)      完成文档/测试准备
Phase 9:     M(签收) + N(积累)      最终签收 + 经验入库
```

**未通过当前 Phase 对应审查类之前，不得进入下一 Phase。**

**在开始任何 PCB 设计工作之前，必须将以下 todo 写入 todo list，逐项完成，每项完成并验证后才进入下一项。**

```
TODO:
[ ] Phase 0: Pre-Flight Audit（环境检查，全部通过才能继续）
[ ] Phase 1: Specification（规格确定）
[ ] Phase 1b: Verified Recipe Memory（查已有配方）
[ ] Phase 2: Component Selection（元件选型）
[ ] Phase 3: SPICE Simulation（仿真 + 数据验证 + 图表生成）
[ ] Phase 4: Schematic Creation（原理图 + ERC）
[ ] Phase 5: PCB Layout（布局 + 走线 + 铺铜 + DRC）
### Phase 5a: Design Review（强制 — 使用本章开头的 A-O 审查清单）

在 Phase 5 走线/DRC 结束后，Phase 5b Gerber 导出前，必须执行本章开头 **A-O 设计审查清单** 中当前 Phase 对应的审查类（至少包含 C、D、E、F、G 中未在前面 Phase 完成的项）。

审查清单就在本章上方 — **A(需求回溯) 到 N(经验积累)**，每项有明确判据和来源。逐项执行，不得跳过。

**⛔ 设计审查中的"六不"铁律（违反 = 该次交付有缺陷）：**
1. **不给用户布置任务** — "你打开 KiCad 按 F7"、"你去设置里打开"之类的表述全部违规。能用 kicad-cli 做的用 kicad-cli，不能用 kicad-cli 的用 pcbnew，所有事在 CLI 环境内完成。
2. **不让仿真代替审查** — 行为模型没有 VCC 引脚，运放在 9.5V 下仿真照样通过但实物上电即烧。SPICE 和审查是两条腿，缺一不可。
3. **不跳过 SOT-23 引脚检查** — 每只晶体管的 pad 编号 vs 数据手册引脚定义必须逐只对照，这是最容易被忽略、出问题后最难定位的错误。
4. **不跳过供电电压 ABS MAX 检查** — 每个 IC 的每个供电/使能引脚必须逐个查数据手册，这是本设计中发现的最严重错误类型。
5. **不跳过信号链追溯** — 分配完 pad 网络后，追溯每只晶体管的完整信号路径（源头→Gate→Source→负载），确认体二极管方向正确、电流通路符合预期。只检查 pad 编号不够——2026-06-06 案例中 pad 编号"看起来都对"但整条链从上到下全接反了。
6. **不一次审查就收工** — 用户要求"全面系统审计"时，一次 A→O 审查不够。首次审查易漏（自指循环陷阱/电感纹波/引脚交叉）。正确模式是：用首次审查发现的问题修正后，用独立来源的预期值做第二轮审查。至少两轮，多轮直到零发现。用 scripts/a-o-audit.py 辅助。


**⛔ 这条审查不能由 SPICE 仿真代替。** 行为模型（VCVS/B-source）没有 VCC/VEE 引脚，运放在 9.5V 下仿真照样通过——但实物上电即烧。SPICE 验证功能行为，设计审查验证物理约束。两条腿都要走。

**常见审查失败模式：**
1. **最大电流** — R4/R5 分压 + Rsense → I_max 与规格书对比
2. **功率耗散** — 每个功率元件的封装额定值是否足够
3. **逻辑方向** — 控制信号上拉/下拉方向是否与规格一致
4. **⛔ 电压额定值** — 每个 IC 供电电压是否在 ABS MAX 以内（最常遗漏）
5. **⛔ 晶体管引脚分配** — SOT-23/SOT-23-3 等小封装 pad 编号 vs 数据手册，引脚分配必须从数据手册独立提取，不能从被审代码反推。
6. **⛔ 自指循环陷阱** — 审计脚本的"期望值"不能抄自被审代码。如果审计脚本说"期望 Q1.pad1=OUT"而代码写的是 `assign(q1, {"1": OUT,...})`，那检查的不是"Q1 接对了没有"，而是"Q1 的代码和注释一致不一致"。必须从数据手册独立提取期望值写入审计脚本。

   案例（2026-06-06）：审计检查 Q1 晶体管时，期望值完全来自错误代码中的命名约定，审计结果全是 ✅，但实际引脚分配与数据手册不符。根因：审计脚本期望值不是从数据手册推导的，而是从被审代码复制拼写的自我验证。

   **⛔ 这条审查不能由 SPICE 仿真代替。** 行为模型（VCVS/B-source）没有 VCC/VEE 引脚，运放在 9.5V 下仿真照样通过——但实物上电即烧。SPICE 验证功能行为，设计审查验证物理约束。两条腿都要走。见 Phase 3 `⚠️ SPICE Behavioral Model 核心约束`。

另见 `references/design-review-checklist.md` §6。

完整检查清单见 `references/design-review-checklist.md`。任何一项不通过 → 回 Phase 5 修复 → 重新 DRC → 重新设计审查 → 才进入 Phase 5b。

### Phase 5b: Gerber 导出（打样文件）

**⚠️ 再生顺序铁律**：如果 Phase 5a 设计审查发现了缺陷并修正了 PCB，则必须按序重做：修正 PCB → 重新 DRC → 重新设计审查 → 重新 export（Gerber/钻孔/SVG/PDF/GLB） → 重新 render（3D图） → 重新 BOM → 重新 zip 生产包 → 重新生成设计报告。zip 和报告是静态快照，不会自动跟踪 PCB 变更。

generate Gerber and drill files:
[ ] Phase 8: Documentation（设计报告）
[ ] Phase 9: 交付前检查清单（不可跳过的最终审查）
```

**门控规则（违反 = 该次交付有缺陷）：**
1. **顺序执行** — Phase N 未完成验证，不得进入 Phase N+1
2. **每步验证** — 每完成一个 Phase，执行该 Phase 的验证步骤，通过后标记 todo 为 completed
3. **零跳过** — 没有任何 Phase 可以标注为"不适用"或"跳过"。如果确实不适用（比如无源滤波器没有 EMC 检查），必须在 todo 中明确注明理由并验证
4. **交付前必须回头检查每个 Phase 的 todo 都是 completed**，缺任何一项不得回复"已完成"

## Image Export Protocol（2026-06-05 实测更新）

**核心原则：** 报告中的电路图优先从 KiCad CLI 导出 SVG → cairosvg 转 PNG。KiCad 10.0.3 (WSL Ubuntu 24.04) 上 **cairosvg 2.9.0 和 rsvg-convert 2.58.0 均能正常渲染**（2026-06-05 实测，vision_analyze 确认文字/焊盘/走线清晰可读）。当 SVG→PNG 失败时（如旧系统），降级到 matplotlib 等效图。

### 图片管线（推荐路径）

**主路径：kicad-cli SVG → cairosvg PNG**
```bash
# PCB 多层合成 SVG → PNG
kicad-cli pcb export svg board.kicad_pcb -o /tmp/pcb_view.svg \
  --layers "F.Cu,F.SilkS,Edge.Cuts" --page-size-mode 2 --fit-page-to-board
python3 -c "import cairosvg; cairosvg.svg2png(url='/tmp/pcb_view.svg', write_to='report/pcb_view.png', scale=3.0)"

# 原理图 SVG → PNG（sch export 的 -o 创建目录，取目录内实际文件）
kicad-cli sch export svg project.kicad_sch --output /tmp/sch_svg/
mv /tmp/sch_svg/*.svg /tmp/schematic.svg
python3 -c "import cairosvg; cairosvg.svg2png(url='/tmp/schematic.svg', write_to='report/schematic.png', scale=3.0)"
```

**验证**：生成后必须用 `vision_analyze` 确认图片有效，提问：'能看到元件标注、走线和焊盘吗？文字是否清晰？'

**⚠️ 密布局板 3D 渲染局限**：<25mm 小板上密集排布 20+ 元件时，`kicad-cli pcb render` 可能产生一个近空白绿色矩形（渲染距离无法自动适应密布局）。此时：改用 `kicad-cli pcb export glb --include-tracks --include-pads --include-silkscreen --include-soldermask` 导出 GLB，然后用 trimesh 从更近的相机角度渲染，或者直接使用 PCB 2D SVG 预览（cairosvg 转换）做报告封面图。

**回退方案（当 cairosvg 渲染失败时）**：用 matplotlib 生成等效原理图和 2D PCB 布局图。模板代码见 `references/kicad-export-for-report.md` > Fallback: matplotlib。

**3D 预览**（可选）：
- **首选用 `kicad-cli pcb render`**（KiCad 原生光线追踪渲染器，输出 PNG/JPEG）：
  ```bash
  kicad-cli pcb render board.kicad_pcb --output /tmp/pcb_3d.png --width 1600 --height 1200 \
    --side top --quality high
  ```
  支持 `--side top|bottom|left|right|front|back`，`--quality basic|high`，`--background transparent|opaque`。`--preset` 选择预设渲染配置。
- GLB 导出（KiCad 10.0.3 支持 `--board-only`，不崩溃）：`kicad-cli pcb export glb board.kicad_pcb --include-tracks --include-pads --include-silkscreen --include-soldermask -o /tmp/board.glb`
- 小 PCB（<30mm）的 3D 渲染细节有限，建议在 KiCad GUI 中按 F9 查看原生 3D。matplotlib 3D 渲染代码见 `references/kicad-export-for-report.md`。

### 图片嵌入规范

**⚠️ SVG 不能直接嵌入 DOCX**：python-docx 的 `add_picture()` 方法不支持 SVG 格式。必须先转换为 PNG（cairosvg 或 rsvg-convert）再通过 `add_picture()` 嵌入。

| 要求 | 原理图 | PCB 布局图 | 3D 预览 |
|:----|:-------|:-----------|:--------|
| 背景色 | 白色 `#ffffff` | 深绿 `#1a3a1a` 或黑 `#0f0f1a` | 深色 `#0f0f1a` |
| 外边框 | 浅灰 | 白色 | 无 |
| 文字 | 黑色，无重叠 | 白色，无重叠 | 白色标题 |
| 生成后验证 | vision_analyze | vision_analyze | vision_analyze |

## kicad-cli 快速命令参考

**所有 kicad-cli 命令一览**（完整文档见 `references/kicad-cli-commands.md`）：

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
| 项目创建 | `kicad-cli project new` ❌ **不存在于 KiCad 10** — 手动写 `.kicad_pro` JSON 文件或用模板 |
| 项目同步 | `kicad-cli project sync-symbol-lib project.kicad_pro` |

**注意**：`sch export svg -o` 参数是**目录**不是文件（KiCad 自身行为），实际 SVG 在目录内以项目名命名。`pcb export svg -o` 是**文件**。

## Autonomous Design Mode

当用户描述项目需求但没有给出具体参数时（如"我想做一个吉他效果器"），自动执行：

1. `web_search("{项目} typical signal frequency range specifications")`
2. `web_search("{项目} recommended filter cutoff frequency / supply voltage")`
3. 根据搜索结果自主决定：电路类型、目标 fc、供电电压
4. 解释选择理由，然后直接跑完整流水线，**不问用户要参数**

**绝不能跳过 web search。** 即使你知道答案也必须展示实时研究过程。

## Workflow: Natural Language to PCB

（执行路径优先级见上方「⛔ 核心执行路线」——kicad-cli → pcbnew API → GUI 鼠标点击，永不手工构造 S-expression/猜坐标）


**用户明确要求：** GUI 能做的事绝不交给用户手动做。所有 `kicad-cli` 能完成的（DRC/导出/渲染/统计）都必须在 pipeline 中自动完成。`pcbnew API` 能完成的布局布线也必须在 pipeline 中完成。**交付物 = 开箱可用的完整板文件 + 打样文件 + 报告。** 任何"你打开 KiCad 按 F7"或"你在 GUI 中调整"的表述 = 违规，用户每次都会打回来。

### Phase 0: Pre-Flight Audit（强制，每步前执行）

在开始任何 PCB 设计工作前，先执行完整环境审计：

```bash
# 核心组件检查
kicad-cli --version                    # KiCad 版本
python3 -c "import pcbnew; print('pcbnew OK')"  # pcbnew 是否可用
ngspice -v                             # SPICE 可用
python3 -c "import PySpice; print('PySpice OK')"  # PySpice（注意大小写）
which kicad-cli || echo "kicad-cli missing"

# 封装库检查
ls /usr/share/kicad/footprints/ 2>/dev/null | head -5

# 清除残留 KiCad GUI 进程（防止旧窗口干扰）
pkill -0 pcbnew 2>/dev/null && pkill -9 pcbnew 2>/dev/null; pkill -0 kicad 2>/dev/null && pkill -9 kicad 2>/dev/null; true

# KiCad 首次启动向导检查（防止 pcbnew GUI 加载时被阻塞）
if grep -q '"first_run_shown": false' ~/.config/kicad/10.0/kicad.json 2>/dev/null; then
  echo "⚠️ KiCad first-run wizard enabled — patching to skip"
  sed -i 's/"first_run_shown": false/"first_run_shown": true/g' ~/.config/kicad/10.0/*.json
fi
```

**审计失败处理**：逐项修复，不跳过。修复后重新审计全部通过才进入 Phase 1。

### Phase 1: Specification

**前置：读取规格文档**
如果规格来自本地 PDF/web 页面，按以下优先级读取：
1. `web_extract(urls=[...])` — 适用于网络 URL 或纯文本 PDF
2. `python3 -c "import fitz; doc=fitz.open('path.pdf'); print(doc[0].get_text())"` — 适用于本地 PDF（PyMuPDF，无法被 web_extract 读取时）
3. 如果两者都不可用，用 `terminal(pdftotext ...)` 或 `terminal(mutool draw ...)`

**⚠️ 铁律：PDF 中已有的参数绝不问用户。** 提取全文后遍历所有数字/范围/条件——提取电压、电流、频率、增益、尺寸等所有关键参数到设计参数表中。用户上传 PDF 而不是口头描述，就是因为它已经写清楚了。向用户问 PDF 已写明的参数 = 信任损失。

**步骤：**
1. **Circuit type identification**: RC filters, opamp circuits, power supplies, MCU systems, RF circuits
2. **Autonomous decision** (if user gave vague spec): web search → choose circuit type + fc + V supply
3. **Parameter extraction**: V/I/frequency/gain/topology — 对照 PDF 逐行核对，不漏参数。**遍历 PDF 中每个数字**——输入电压、输出电压范围、电流、频率、上升时间、尺寸、孔径、间距——全部提取到设计参数表中。不要"看一眼大概"就跳过。每一个数字都决定一个元件或约束。
4. **Component calculation**: Prefer E24 series for practical RC filters
5. **Memory search**: Check session history + memory for verified recipes with same topology, similar frequency, footprint, and component source
6. **Reference design lookup**

**⚠️ 关键子步骤：方案自检（Phase 1 完成后、向用户展示前强制执行）**

写出设计方案后，在展示给用户之前，必须自行核查：
- [ ] 方案覆盖了 PDF/需求文档中每一条技术要求
- [ ] **不要向用户询问PDF中已明确写明的参数。** 如果PDF写了"输出电压4.0~6.0V自适应"，就不要问"负载电压是多少"——答案已经在PDF里。所有参数应从PDF中提取，而不是让用户替你再读一遍。违反此规则 = 用户信任损失。
- [ ] 存在矛盾的约束已识别并注明（如尺寸 vs 元件数、电压范围 vs 拓扑选择）
- [ ] 高度/尺寸/接口等物理约束的可行性已验证（算数值）
- [ ] 有理由说明为何选择此拓扑而非替代方案（如「必须 Boost 因为 Vf > Vin」）
- [ ] 待确认项已明确列出（不替用户做决定）

核查不通过 → 先修方案再展示。用户说"你自己核查一下"意味着你跳过了此步骤。

**⚠️ 审计方法：当用户要求检查/审计 skill 或设计方案时，"全面系统的审视检查"意味着必须遍历全部相关文件的每个章节，逐一验证每个断言/参数/代码行——抽样验证几个点是不够的。抽几个点检查 = 没检查。**

### Phase 1b: Verified Recipe Memory

每次成功设计后，保存配方到 memory：
```
Recipe: RC_LOWPASS fc=1kHz
R=1kΩ C=100nF (E24)
fc_actual=1591Hz Error=0.004%
Footprint=0402 Source=JLCPCB
Simulation: PySpice PASS
```
下次同类设计优先复用已知配方，不再重新计算。

### Phase 2: Component Selection

**⚠️ ⛔ 铁律：选择 IC 前必须做供电电压合规检查。** 这是整个设计中**最容易被忽视、后果最严重的错误**——上电即烧毁。见下方 §2.1 和 §2.5。

#### 2.1 供电电压审查（强制，每颗 IC 都要做）

```python
# 对每个 IC 执行：
checks = [
    # (IC_name, Vmax_from_datasheet, actual_rail_voltage)
    ("TLV2371",  5.5, 9.5),    # ❌ — Boost 9.5V > 5.5V max
    ("SGM6601",  5.5, 5.0),    # ✅ — VIN 5V ≤ 5.5V
    ("NE555",    16,  9.5),    # ✅ — 9.5V ≤ 16V, 41% margin
]

for name, vmax, vactual in checks:
    margin = (vmax - vactual) / vmax * 100
    if margin < 20:
        print(f"⚠️ {name}: {vactual}V / {vmax}V = {margin:.0f}% margin — <20%, risk!")
    if vactual > vmax:
        print(f"❌ {name}: {vactual}V > {vmax}V — WILL DAMAGE!")
```

**规则**：
- 实际供电电压必须 ≤ IC 数据手册的绝对最大额定值，且留 ≥20% 余量（含纹波、容差、瞬态过冲）
- 特别警惕：**从 Boost/Buck 输出端取电的 IC**——转换输出往往是板上最高电压
- 误判案例：某 CMOS op-amp datasheet 标 VDD=2.7~5.5V，实际接 Boost 输出 9.5V → 上电即烧

#### 2.2 功率耗散审查（强制，每个功率元件都要做）

```python
# 对每个可能耗散功率的元件
# Rsense: P = I²R = 0.2² × 15 = 0.6W
# 封装额定值 vs 80% 安全线
pkg_ratings = {"0603": 0.1, "0805": 0.125, "1206": 0.5, "2512": 1.0}
actual_power = 0.6
for pkg, rated in pkg_ratings.items():
    safe = rated * 0.8
    status = "✅" if actual_power <= safe else "❌"
    print(f"{status} {pkg}: {actual_power:.1f}W ≤ {safe:.1f}W (80% of {rated}W)")
```

**规则**：
- 实际功率 ≤ 封装额定功率的 80%（安全余量覆盖焊接降额、温度升额）
- 包装器/电位器：按最大可能值计算，不按标称值
- 电感：Isat ≥ I_peak × 1.2
- 二极管：VRRM ≥ V_reverse × 2（覆盖开关尖峰）

**封装升级路径**：当 P > 80% 封装额定值时，按 0603→0805→1206→1210→2512 升级，或用多只并联分担功率。

#### 2.3 保护电路设计模式

**每种电路拓扑至少应配备以下基础保护**：

| 保护类型 | 实现 | 适用场景 | 案例 |
|---------|------|---------|------|
| **反接保护** | SS12 肖特基二极管跨接在输入端（GND→Vin） | 任何有外部电源输入的电路，防止用户接反极性 | D2 (GND→BST) |
| **ESD 保护** | 100pF NP0 电容对 GND | 每个外部接口（模拟输入、数字控制、电源输入） | CE1/VIN, CE2/CTRL, CE3/ANA → GND |
| **过流保护** | 串联保险丝或 PMOS 电子熔断器 | 大功率输出（>1A），或外接排针供电口 | — |
| **输出缓启动** | RC 滤波器在驱动器输出端 | 容性负载、敏感负载（防止上电浪涌击穿） | — |

**布局经验**：
- 保护元件**必须靠近接口/接插件放置**，不在保护环节中间走长线后加保护
- ESD 电容走线到 GND 必须 <5mm，过孔直接到 GND 平面
- 反接保护二极管的电流能力 ≥ 输入电流 × 2

#### 2.4 选型信息来源优先级

| 层级 | 来源 | 用途 |
|:----|:-----|:-----|
| 1 | 数据手册（PDF） | 所有关键参数：Vmax、Imax、Pmax、封装、工作温度 |
| 2 | LCSC 库存 | 选型可用性、价格、基础库/扩展库区分（JLCPCB） |
| 3 | DigiKey / Mouser | 数据手册快捷访问、替代型号 |
| 4 | element14 / 得捷 | 最后一档，交叉验证价格 |

**铁律**：数据手册参数 > 任何二次来源。不能用 LCSC 的摘要参数替代手册。

#### 2.5 工作电压余量速查表

| IC 类型 | 典型 Vmax | 使用建议 |
|---------|----------|---------|
| TLV2371 (CMOS op-amp) | 5.5V | 只能用在 3.3-5V 轨，绝对不要接 Boost 输出 |
| TLV2171 (CMOS op-amp, 16V) | 16V | 适合 5-12V 轨，推荐替代 TLV2371 用于更高电压轨 |
| LM358 (BJT op-amp) | 32V | 可用在 5-24V |
| NE555 (timer) | 16V | 通用 5-12V |
| SGM6601 (boost) | 5.5V | 只能由 VIN 供电 |
| ATmega328P (MCU) | 5.5V | 5V 或 3.3V 供电 |
| MAX232 (RS-232) | 5.5V | 5V 专用 |

**判据**：选择 IC 时，先确定板上最高可用轨电压，然后找 Vmax 大于该轨 × 1.25 的 IC。如果找不到，加 LDO 降压或选更高耐压的替代型号。

### Phase 3: SPICE Simulation

Auto-generate testbenches for detected subcircuits using Ngspice (preferred) or PySpice.

#### ⚠️ 关键坑：.PRINT 指令缺失

**.AC 和 .TRAN 分析命令本身不产生可打印输出。** 必须显式添加 `.PRINT` 指令才能让 ngspice 输出数据。

**错误写法（运行但不输出数据）：**
```spice
.AC DEC 100 10 100000
.TRAN 1u 5m 0 1u
```
ngspice 输出文件显示 `"No .plot, .print, or .fourier lines; no simulations run"` — 分析已执行但无数据吐出。

**正确写法：**
```spice
.AC DEC 100 10 100000
.PRINT AC VDB(output) VP(output)
.TRAN 1u 5m 0 1u
.PRINT TRAN V(input) V(output)

#### ⚠️ 关键坑：第一行 = TITLE（ngspice-42）

**网表第一行的任何元件定义都会被 ngspice-42 当作标题静默消费掉。** 这不是报错，是 SPICE 继承性行为——第一行等价于 `.TITLE` 行。不会出现任何错误提示，但该元件完全不存在于仿真中。

```spice
* ❌ 第一行放 VREF —— 被当标题吃掉，VREF 不存在
VREF VREF 0 DC 1.5 AC 1
RSNS VSNS 0 0.1
→ V(VSNS)=0，因为 VSNS 对 GND 悬空

* ✅ 第一行放注释或空行
* Circuit AC test — TITLE line
VREF VREF 0 DC 1.5 AC 1
RSNS VSNS 0 0.1
→ V(VSNS)=0.15，正确运行 ✅
```

**诊断方法**：检查任何不应该为 0 的节点电压——如果 V(VREF)=0（DC 1.5V），说明 VREF 被吃掉了。

**预防**：永远以 `* 描述` 或 `.TITLE 描述` 开头。`.cir` 文件第一行是注释，不是代码。

#### ⚠️ 关键坑：AC 分析输出全零（VCVS 工作点饱和）

当 AC 分析运行成功（输出 400+ 行数据）但所有增益值为 `0.000000e+00` 且无任何警告时，根因通常是 **VCVS 输出饱和在电源轨外**。

**原理**：ngspice 的 `.AC` 分析是 DC 工作点上的小信号线性化。如果 V(out)_DC = +150kV（VCVS 无轨限，增益 1000），则小信号增益 ≈ 0。

**诊断**：
```python
# 检查 DC 工作点：任一节点电压 > 10V（超过电源轨）即饱和
if abs(V_out_DC) > 10:
    print("⚠️ VCVS 饱和！AC 分析无效")
```

**修法**：不要在 VCVS 上加 MIN/MAX 轨限（会导致另一种失真——轨限点处小信号增益为零）。改用一个更简单的方法：**开环测量法**。

```spice
* 限幅器：注意 ngspice-42 中 limit() 已损坏 (回归bug)
* 用 min(max()) 替代：min(max(x, lo), hi) == limit(x, lo, hi)
VCLAMP OUT 0 IN 0 1000
RCLAMP OUT 0 1MEG
* 如果限幅由 E-source 完成，用 min(max()) 替换：
* EAMP OUT 0 IN 0 VALUE {min(5.0, max(0.0, V(IN)*1000))}  ; 限幅 0-5V
```

If you are correcting a user: DO NOT present min/max as equivalent to limit. It is — but a user reading min(max()) will see a workaround, not authored SPICE. Use neutral language: "ngspice-42 has a known regression in the limit() built-in. Here is a drop-in replacement using min and max, which converge everywhere limit() fails."
CP OUT 0 0.1p
.AC DEC 100 10 10MEG
.PRINT AC VDB(OUT) VP(OUT)
```

开环时 VCVS 输出在线性区内，AC 小信号分析正确。读出 GBW（0dB 穿越频率），再推导闭环带宽：闭环带宽 ≈ GBW / (1 + βA)，深度反馈下 ≈ GBW。详见 `references/spice-simulation-pitfalls.md` > "开环运放带宽测量法"。

#### 反馈控制环 AC 分析（电源反馈回路）

当分析 buck/boost 开关电源的反馈环调制带宽时（如 PWM 调制频率验证），**不能用升压/降压转换器的完整 SPICE 仿真来验证带宽**——开关模型会带来巨大的收敛问题。而是**单独分析反馈控制环**：

**拓扑**：VREF(AC信号) → 误差放大器(VCVS) → MOSFET(门极) → 采样电阻 Rsense → VSNS(反馈量)

**关键概念**：
- VREF 加 AC 1V 小信号叠加在直流偏置上
- VSNS 是采样电阻上的电压 = I_load × Rsense
- AC 分析测量 V(VSNS)/V(VREF) 得出闭环调制带宽
- 放大器直流增益决定了 I_load 对 VREF 的跟踪精度

**网表示例**（恒流/恒压控制环 AC 分析）：
```spice
VREF VREF 0 DC 1.5 AC 1            ; AC 叠加直流偏置
VIN VIN 0 5                         ; 电源
* 误差放大器（增益 A=1000，惯性补偿 1us）
EAMP GATE 0 VREF VSNS 1000
RP GATE 0 1MEG
* 串联小阻值电阻模拟放大器输出阻抗
RAMP GATE_DRV GATE 1
CP COMP GATE_DRV 0 100p            ; 补偿 ~1.6us 时间常数，防止数值振荡
; 补偿电容取值方法详见 references/feedback-compensation-design.md
* 采样电阻（模拟负载）
RSNS VSNS 0 0.1                    ; 电流采样：V(VSNS) = I_load × 0.1Ω
.AC DEC 100 10 100k
.PRINT AC VDB(VSNS) VP(VSNS)
```

**带宽判定**：VDB(VSNS) 从通带下降 -3dB 对应的频率点即为调制带宽。

即使都加了 `.PRINT`，AC 和 TRAN 混合在一个网表文件中时，ngspice 可能只输出其中一个分析的数据，另一个报 `"vector output is not available or has zero length"`。

**解决方案：分离成两个独立的网表文件**
```
ac_analysis.cir: 只放 .AC + .PRINT AC
tran_analysis.cir: 只放 .TRAN + .PRINT TRAN
```
分别运行：
```bash
ngspice -b ac_analysis.cir -o ac_out.txt
ngspice -b tran_analysis.cir -o tran_out.txt
```

#### 开环运放带宽测量法（当闭环 SPICE 不收敛时）

闭环恒流/恒压反馈环路中，运放(VCVS)+MOSFET+采样电阻三级级联增益极易导致 SPICE 不收敛。此时**不要花时间调试闭环 VC VS 限制器**——直接切换到开环测量：

**流程**：
1. 断开反馈：运放反相输入端接 GND（不接反馈采样电压）
2. 同相输入端加 AC 1V 小信号（叠加在 DC 偏置上）
3. 输出端接高阻负载（1MEG + 0.1pF 对 GND）
4. .AC 扫频 10Hz-10MHz
5. 从 Bode 图中读取：DC 增益、-3dB 极点频率、GBW（0dB 穿越点）
6. 计算闭环带宽 = GBW / (1 + βA)，深度反馈下 ≈ GBW

**实战验证**（典型 CMOS op-amp 模型）：
- DC 增益 = 99.3dB ≈ 92,000 V/V
- 主导极点 = 28Hz
- GBW = 2.401MHz（手册 2.5MHz，误差 4% ✅）
- 闭环 -3dB 带宽 = 1.2MHz

**不需要闭环 SPICE 验证！** 用 GBW 计算足够证明调制带宽满足要求。

#### ⚠️ SPICE Behavioral Model 核心约束（高频失败模式）

**这是整个 SPICE 仿真中最容易被忽视的限制——它骗过你的概率最高。**

**核心事实**：VCVS、B-source、E-source 等行为模型的运放/放大器中**没有 VCC/VEE 电源引脚**。这意味着：

| SPICE 能检查什么 | SPICE 不能检查什么 |
|:-----------------|:------------------|
| 小信号增益、带宽、相位裕度 | ❌ **供电电压是否超过 IC 的绝对最大额定值** |
| 闭环反馈稳定性、响应时间 | ❌ 轨-轨输入/输出范围限制 |
| 传递函数、截止频率 | ❌ 功耗、结温、降额 |
| 与 datasheet GBW 的一致性（开环可验证） | ❌ 共模/差模输入电压范围 |

**典型灾难路径**：
1. 把某 CMOS op-amp（Vmax=5.5V）接在 Boost 输出 9.5V 上
2. 行为模型没有 VCC 引脚 → VCC 不存在 → SPICE 无从得知运放被过压供电
3. AC 仿真完美通过（GBW=2.4MHz ✅）
4. 用户打样焊接 → **上电即烧毁运放**

⛔ **SPICE 仿真通过 ≠ 设计安全。** 行为模型验证的是**功能行为**，不是**物理约束**。

**正确的双通道验证策略**：

```
通道 1 — SPICE 仿真（Phase 3）
   → 验证：增益、带宽、稳定性、响应时间
   → 工具：VCVS/B-source 行为模型 + 开环 GBW 测量
   → 限制：无电源引脚，无物理约束检查

通道 2 — 设计审查（Phase 5a，不可跳过）
   → 验证：供电电压余量（§2.1）、功率降额（§2.2）、保护电路（§2.3）
   → 工具：对照 datasheet 逐 IC 检查 + 速查表（§2.5）
   → 限制：无仿真，纯人工（或 scripted）核对

两个通道正交互补。通过通道 1 不自动通过通道 2。
```

**详见**：
- Phase 2 §2.1（供电电压审查）、§2.5（工作电压速查表）
- Phase 5a 电压额定值审查
- Detection table row: `IC supply voltage exceeded`

**KiCad genopa1 模型（内置电源引脚）的兼容性问题**

KiCad 的符号库自带 `genopa1` 运算放大器模型（包含 VCC/VEE 电源引脚，是行为模型的正确替代方案），但在 ngspice-42 上实测存在收敛问题：

```spice
* genopa1 模型（KiCad 内置）
XU1 VOUT 0 0 VSNS VCC VEE genopa1 params:
+ A0=100000 GBW=2.5MEG SR=2.5MEG  ; 开环增益/带宽/压摆率
+ VCC=5 VEE=0   ; 电源轨
*
; 此模型在 ngspice-42 上不收敛（Dlimit D N=0.01 二极管钳位与求解器冲突）
; 输出被钳在近 0V → 闭环无法调节 → 输出电压 ≈ VEE
```

**根因**：`genopa1` 内部使用 `Dlimit D N=0.01` 二极管钳位限制输出幅值，ngspice-42 的求解器在这种情况下收敛不到正确工作点。

**推荐方案（2026-06-05 实测验证）：**

| 场景 | 推荐方案 | 说明 |
|:-----|:---------|:------|
| 需要电源引脚检查 | **开环 VCVS 测量 GBW**（行为模型，不闭环） | 无收敛问题，GBW 与 datasheet 误差 <5% |
| 需要闭环仿真验证响应时间 | **降压增益 + 补偿**：增益 100-1000 + RC 补偿 | 防止高增益数值振荡 |
| 小信号 AC 带宽 | **VCVS 开环 GBW → 数学推导闭环带宽** | GBW / (1 + βA)，深度反馈下 ≈ GBW |
| 瞬态/开关行为 | **分段验证**：DC 扫态 → 固定偏置 → 信号叠加 | 不用完整闭环仿真 |
| 真正需要电源引脚模型 | **Vendor SPICE 模型**（来自 TI/ADI/Maxim 官网） | 最准确，但需下载转换 |

**总之**：不要花时间调试 genopa1 在 ngspice-42 上的收敛问题——它不工作的概率太高。使用 VCVS 开环测量 GBW + datasheet 电源轨检查才是可靠路线。

#### ⚠️ SPICE 收敛问题排查

当仿真不收敛（singular matrix、NaN、数字噪声）时，对照以下清单排查：

| 现象 | 根因 | 修法 |
|:-----|:-----|:------|
| 二极管模型指数溢出 | `IS` 太小 + 无 `RS` → `exp(Vf/Vt)` 溢出 | 加 `RS` 参数（如 `RS=20`）或用等效电阻替代负载 |
| MOSFET 不导通 | W/L 太小，无法通过目标电流 | 计算 `Id = 0.5*KP*(W/L)*(VGS-VTO)^2`，增大 W |
| 闭环瞬态振荡 | 运放模型增益太高 → 硬开关 | 降增益至 100 或开环验证 |
| 瞬态 t=0 崩溃 | `.IC` 与工作点不一致 | 先用 `.DC` 扫工作点，再用正确值设 `.IC` |
| V(VSNS) 全程数值噪声 | 无直流通路或二极管模型饱和 | 用等效电阻替代负载诊断 |
| 运放(VCVS)+MOSFET 反馈环路不收敛 | 高增益运放(>1000) + MOSFET + 采样电阻 = 三级级联增益，数值噪声被放大到 NaN | (1) 用理想电流源先验证核心环路 (2) 瞬态分析中将运放增益降至 100-1000 (3) 加 Rpole+Cpole 补偿(~1us 时间常数) (4) 仍失败则改为 DC 扫描验证，用 datasheet GBW 作为带宽保证 |
| **E-source min(max()) transient 收敛失败** | `EAMP OUT 0 A B VALUE {min(5, max(0, V(A,B)*1000))}` 在 DC 分析中正常，在 TRAN 中因钳位边界导数不连续而崩溃（timestep too small） | **改用 DC 扫描验证恒流/开关状态**：`.DC VTTL 0 5 5` 即可给出 TTL=0V（ON）和 TTL=5V（OFF）两个工作点的完整数据。只需要开关功能的恒流源不需要 TRAN 仿真。只在需要开关速度/上冲数据时才重回 TRAN，且使用低增益(100)无钳位模型。 |

详细排查步骤和模型参数见 `references/spice-simulation-pitfalls.md`

#### SPICE 仿真执行流程

1. **写 .cir 文件** — 包含 .PRINT 指令（见上方）
2. **运行 ngspice**：
   ```bash
   ngspice -b circuit.cir -o output.txt
   ```
3. **验证输出** — 打开 output.txt，确认包含 `"AC Analysis"` 表头和数据行，不含 `"No simulations run"` 警告
4. **提取关键数据** — 从 output.txt 解析 AC 分析表，提取 -3dB 截止频率、通带增益、阻带衰减、滚降率、相位
5. **验证指标**（见下方验收标准表）
6. **从仿真数据重新生成图表** — 使用实际仿真数据生成伯德图和波形图，**不要从理论公式画图假装是仿真结果**

#### 仿真数据提取与验证算法

```python
# 从 ngspice output.txt 解析 AC 分析数据
ac_data = []
in_ac = False
for line in output_text.split('\n'):
    if 'AC Analysis' in line:
        in_ac = True; continue
    if in_ac and line.strip() and not line.startswith(('Index','---','Warning','Total')):
        parts = line.strip().split('\t')
        if len(parts) == 4:
            ac_data.append((float(parts[1]), float(parts[2]), float(parts[3])))

# 找 -3dB 点（增益从 -3dB 以上穿越到以下）
for i in range(len(ac_data)-1):
    if ac_data[i][1] >= -3.0 and ac_data[i+1][1] < -3.0:
        f1, db1 = ac_data[i]; f2, db2 = ac_data[i+1]
        ratio = (-3.0 - db1) / (db2 - db1)
        fc = f1 + ratio * (f2 - f1)  # 插值

# 渐近滚降率：在至少 1 倍频程（最好是 1 个十倍频程）的阻带内测量
# 从 10×fc 到 100×fc（或最接近的仿真点）
db_10fc = ... ; db_100fc = ...
rolloff = (db_100fc - db_10fc) / log10(10)  # -20.0 dB/decade
```

#### 验收标准

| 子电路 | 测试 | 验收标准 | 测量方法 |
|:-------|:-----|:---------|:---------|
| RC_LOWPASS | 截止频率 | <1% 误差 | 插值查找 -3dB 点 |
| RC_HIGHPASS | 截止频率 | <1% 误差 | 插值查找 -3dB 点 |
| VOLTAGE_DIVIDER | 分压比 | <1% 误差 | 低频增益 |
| OPAMP_GAIN | 增益 | <5% 误差 | 通带增益 |
| LC_RESONANT | 谐振频率 | <5% 误差 | 峰值搜索 |
| 滚降率（LPF/HPF）| 渐近滚降 | <1 dB/decade | 10×fc 到 100×fc |
| **相位验证** | **fc 处相位 ≈ -45°** | **±5°** | **弧度转角度验证：`deg = rad × 180/π`** |

#### 中文字符路径问题

当输出目录包含中文字符（如 `<PROJECT_DIR>\...`）时，`terminal(workdir=...)` 会拒绝包含中文字符的路径。解决方案：将 .cir 复制到 `/tmp/sim/` 运行，结果复制回目标目录。

```python
import shutil, os
os.makedirs('/tmp/sim', exist_ok=True)
shutil.copy2(cir_path, '/tmp/sim/circuit.cir')
# 在 /tmp/sim 下运行 ngspice（无 workdir 限制）
# 结果复制回目标目录
shutil.copy2('/tmp/sim/output.txt', target_dir / 'simulation_output.txt')
```

完整的数据解析、验证、图表生成流程详见 `references/simulation-verification-protocol.md`。

### Phase 4: Schematic Creation
Generate `.kicad_sch` files using S-expression (sexpdata library):
1. Create project: `kicad-cli project new`
2. Add components with values + footprints
3. Wire nets and label
4. Run ERC
5. Annotate references

### ⛔ 铁律：哪些算"用 KiCad"，哪些不算

pcbnew Python API 是 KiCad 的官方语言绑定，调用它 = 用 KiCad。但关键区别在于**读 KiCad 数据 vs 从零创建数据**：

| ✅ 用 KiCad（可接受） | ❌ 不是用 KiCad（禁止） |
|:------------------------|:-------------------------|
| `FootprintLoad()` 加载标准封装 | `PAD(fp)` 自建裸焊盘 |
| `p.GetPosition().x/1e6` 读实际坐标 | 硬编码 `tr(14.0,15.5,...)` 猜坐标 |
| `PCB_TRACK(b)` 创建走线 | 手工构造 S-expression 字符串 |
| `PCB_VIA(b)` 创建过孔 | 绕过 KiCad 类直接写文件 |
| `board.Save()` 保存 | — |
| `kicad-cli pcb drc / export` | — |

**读了实际坐标再用 PCB_TRACK 是 KiCad 内部的布线流程**——不是"自己写脚本"。不加验证直接猜坐标才是违规。

### 优先级链（KiCad 操作路径）

```
最优先: kicad-cli pcb drc / export / dsn    ← CLI，最可靠
其次:   pcbnew API (FootprintLoad + 真实坐标)  ← KiCad 内部库
再次:   xdotool 鼠标点击 GUI（WSLg 下有限可行）
绝不:   手工构造 S-expression / PAD(fp) 裸焊盘  ← 不是用 KiCad
```

### Phase 5: PCB Layout
- **⚠️ 必须使用 KiCad 标准库封装（FootprintLoad()）创建元件，绝不要手工创建裸焊盘封装。** 裸焊盘没有丝印外形框、没有 Courtyard、没有 3D 模型、无法通过 DRC。每次 PCB 设计都必须：`fp = pcbnew.FootprintLoad('/usr/share/kicad/footprints/Resistor_SMD.pretty/', 'R_0603_1608Metric')`。所有常用封装的库路径见下方参考。
- **圆形板框（Ømm）**：用 `SHAPE_T_CIRCLE` 创建圆形 Edge.Cuts：
  ```python
  edge = PCB_SHAPE(board)
  edge.SetShape(SHAPE_T_CIRCLE)
  edge.SetCenter(VECTOR2I(FromMM(CX), FromMM(CY)))  # 圆心
  edge.SetEnd(VECTOR2I(FromMM(CX+R), FromMM(CY)))    # 圆周上一点
  edge.SetLayer(pcbnew.Edge_Cuts)
  edge.SetWidth(FromMM(0.15))
  board.Add(edge)
  ```
- **极小板边缘连接（<20mm 直径）**：用 `TestPoint_Pad_D1.5mm`（TestPoint.pretty）替代排针连接器。每个测试点占 1.5mm 圆焊盘，焊工可直接焊线。比排针节省 70%+ 面积。适合 Ø14mm 等极小圆形板。用法：
  ```python
  tp = place(board, "TestPoint.pretty", "TestPoint_Pad_D1.5mm",
             "TP1", "VIN", edge_x, edge_y)
  assign(tp, {"1": net_vins})
  ```
- **自动布线（Specctra DSN/SES）**：KiCad 通过 `ExportSpecctraDSN` / `ImportSpecctraSES` 支持标准自动布线接口。流程：
  1. 摆放元件后、布线前，导出 DSN：`pcbnew.ExportSpecctraDSN(board, '/tmp/board.dsn')`
  2. 用 Freerouting 或其他 DSN 兼容布线器布完后，得到 `.ses` 文件
  3. 导入结果：`pcbnew.ImportSpecctraSES(board, '/tmp/board.ses')`
  4. Freerouting 安装：`wget https://github.com/freerouting/freerouting/releases/download/v1.9.0/freerouting-1.9.0.jar`；运行：`java -jar freerouting-1.9.0.jar --di board.dsn --do board.ses`
  5. 国内网络可使用 ghproxy.com 镜像下载 Freerouting
- Place components by function blocks
- Route critical traces (power, clock, differential)
- **⚠️ GND 走线强制验证** — 所有 GND 焊盘必须有通向 GND 层的走线或铜皮。用脚本检查 GND 走线数量 > 0。GND 浮空 = 电路没有回路，效果等于开路。
- **添加 GND 覆铜**：使用 `ZONE(board)` 创建顶层和底层 GND 铜皮，覆盖板内区域（留 0.5mm 板边间隙）。
- **创建 KiCad 项目文件**：生成 `.kicad_pro` 和 `.kicad_prl` 文件，让用户可双击打开。
- **完成所有工作，不留给用户 GUI 步骤。** 所有能用 pcbnew/kicad-cli 完成的操作都必须自动完成（元件放置、走线、覆铜、Gerber 导出、BOM）。GUI-only 操作（F9 3D 预览、F7 DRC）只作为补充验证提及，不作为"需要用户做的事"列出。
- **DRC**：使用 `kicad-cli pcb drc` 命令运行完整设计规则检查：
  ```bash
  kicad-cli pcb drc board.kicad_pcb --output drc_report.rpt --all-track-errors --units mm --severity-error --exit-code-violations
  ```
  参数：`--all-track-errors`(全部走线错误) `--units mm`(公制) `--severity-error`(仅错误) `--exit-code-violations`(有违规时退出码非零)。输出格式：`report`(文本) 或 `json`。`--refill-zones` 在检查前重新填充覆铜。`--severity-all` 报告全部(含 warning)。

  如果 DRC 报告大量 `shorting_items`/`solder_mask_bridge` 错误，通常是 GND 覆铜间隙不当——调整 ZONE clearance 或缩小覆铜边界。
- Run DRC (KiCad GUI: F7; CLI: `kicad-cli pcb drc board.kicad_pcb --output report.rpt --units mm --all-track-errors`)
- Generate Gerber

**pcbnew API 稳定性说明**：KiCad 7 的 pcbnew Python API 在某些操作上不稳定（zone 段错误、pad Drill API 不匹配、S-expression 格式要求严格）。如果使用 KiCad 7，当 pcbnew API 在 3 次尝试后仍然报错时，切换到直接写 S-expression 字符串的方式（见 `references/kicad7-pcbnew-api.md` > 实战坑）。

**⚠️ KiCad 10: Reference/Value 丝印文字位置必须在 board.Add(fp) 之后设置**
```python
# ✅ 正确顺序：先加元件再设文字（用板坐标）
board.Add(fp)
rfp = fp.Reference()
rfp.SetPosition(VECTOR2I(FromMM(cx), FromMM(cy + 1.2)))
rfp.SetTextSize(VECTOR2I(FromMM(0.8), FromMM(0.8)))
rfp.SetVisible(True)
...
```
**原因**：KiCad 10 的 `FOOTPRINT.Reference()` 只有在 footprint 已属于一个 board 后才能正确解析坐标偏移。

**⚠️ ⛔ 铁律：必须使用 KiCad 标准库封装，禁止创建裸焊盘 footprint。**
使用 `pcbnew.FootprintLoad()` 从 KiCad 标准封装库加载：
```python
# ✅ 正确：从标准库加载
fp = pcbnew.FootprintLoad("Resistor_SMD.pretty/", "R_0603_1608Metric")
fp.SetReference("R1"); fp.SetValue("1k")
fp.SetLayer(pcbnew.F_Cu)
fp.SetPosition(VECTOR2I(FromMM(cx), FromMM(cy)))
board.Add(fp)

# ❌ 错误：自建裸焊盘（无丝印/3D/courtyard）
# smd(fp, "1", -0.75, 0, 1.2, 0.7, ...)  ← 禁止
```
标准库封装自带：丝印外形框 / 3D 模型 / Courtyard / 标准焊盘尺寸

**⚠️ ⛔ 铁律：走线坐标必须从标准库封装的实际焊盘位置读取**
禁止硬编码走线坐标。用 `fp.Pads()` 读取真实焊盘绝对坐标：
```python
# ✅ 正确：读取实际焊盘位置
for fp in board.GetFootprints():
    for p in fp.Pads():
        x = p.GetPosition().x / 1e6   # 绝对坐标 (mm)
        y = p.GetPosition().y / 1e6
# 然后用这些坐标创建 PCB_TRACK

# ❌ 错误：硬编码猜测坐标（导致 DRC 未连接错误）
```
标准库 0805 焊盘在 ±0.912mm（非 ±0.75mm）。硬编码必然对不上真实焊盘。

**⚠️ 密布局 GND 覆铜注意事项**
<20mm 板（22+元件）：全板 GND 铜皮产生大量 solder_mask_bridge / shorting_items 错误。
- 优先方案：厚走线(0.5mm)构建 GND 总线，不覆铜
- 如需覆铜：设 clearance ≥ 0.3mm 或使用局部区域覆铜

**Net 分配验证**：KiCad 10 中 `list(fp.Pads())` **已按焊盘编号排序**（2026-06-05 实测），但仍建议用焊盘编号 `pad.GetNumber()` 匹配后分配 net，而非依赖列表索引。

**⚠️ Net 序列化坑**：`SetNet()` 只修改了内存中的 net 关联，`board.Save()` 可能不会将其写入 S-expression 文件。必须在每个 `SetNet()` 后调用 `p.SetPosition(p.GetPosition())`，强制 pcbnew 重新计算焊盘位置元数据并触发 net 序列化。不这样做会导致 net 分配在内存中存在但保存后全丢失。

**走线顺序策略（密布局板）**：按以下优先级路由，避免 DRC unconnected_items：
1. **电源网（VIN、VOUT）优先** — 宽走线 0.4-0.5mm，受元件位置约束最大
2. **关键信号（GATE、FB）次之** — 0.3mm，反馈路径需最短
3. **GND 总线最后** — 0.5mm 粗走线连接所有剩余焊盘。在 <25mm 板（20+ 元件）上，**不要使用全板铜皮**——GND pours 会产生数百个 solder_mask_bridge/shorting_items 违规。改用 0.5mm GND 总线。铺铜只在 clearance ≥0.3mm 或局部区域时使用。

验证走线数：`all_tracks = sum(1 for t in board.GetTracks() if isinstance(t, pcbnew.PCB_TRACK))`

### Phase 6: EMC Pre-Compliance (44 rules)
| Category | Count | Focus |
|---|---|---|
| Ground Plane | 5 | Voids, stitching, slots |
| Decoupling | 3 | Per-IC caps, distance |
| I/O Filtering | 2 | ESD, cable shielding |
| Clock Routing | 3 | Edge distance, length |
| PDN Impedance | 4 | Target Z, resonance |
| Differential Pair | 4 | Skew, spacing |
| Board Edge | 3 | Clearance |
| Switching | 3 | Loop area, snubber |

### Phase 7: BOM & Fabrication

**BOM 生成方法选择：**

| 场景 | 方法 | 命令/参考 |
|:-----|:-----|:----------|
| 有完整 KiCad 项目（sch + pcb） | `kicad-cli sch export bom` | 标准 CLI 命令 |
| **pcbnew API 生成的板，无 schematic** | **pcbnew Python API 直接从板文件读取** | `references/pcbnew-bom-generation.md` |
| 手工 PCB（非 KiCad） | CSV 手写 | — |

**pcbnew-based BOM（当无 schematic 时）**：遍历 `board.GetFootprints()`，读取 `fp.GetReference()`/`fp.GetValue()`/`fp.GetFPID()`，输出 CSV。支持分组合并（相同值+封装的元件归为一行）、位置坐标、层信息。见 `references/pcbnew-bom-generation.md`。

**JLCPCB**: LCSC Cxxxxx codes, basic/extended parts, rotation offsets
**PCBWay**: MPN-based, turnkey assembly, larger boards

**JLCPCB 下单默认参数（已验证适用于小批量打样）：**

| 参数 | 推荐值 | 说明 |
|:----|:-------|:-----|
| 层数 | 2 层 | 双面板，成本最低 |
| 板厚 | 1.6mm | 标准 FR-4 |
| 铜厚 | 1 oz | 标准铜厚 |
| 表面处理 | HASL（喷锡） | 最便宜选项 |
| 阻焊颜色 | 绿色 | 5片约 ¥20-30（含运费 ¥30-50） |
| 数量 | 5-10 片 | 交期 3-5 天 |

**发货前必须先生成 Gerber + 钻孔文件**（见 Phase 5 或 `kicad-cli pcb export` 命令）并打包为 .zip 上传。

**BOM 格式**：文本/CSV 格式，包含完整 LCSC 编号方便采购。基础库元件无附加费用。

### Phase 8: Documentation
1. Design overview + specs
2. **Schematic image** — 优先用 `kicad-cli sch export svg` 导出原理图 → cairosvg 转 PNG 嵌入报告。若 cairosvg 渲染失败，用 matplotlib 生成等效原理图。
3. **PCB layout image** — 优先用 `kicad-cli pcb export svg` 导出 → cairosvg 转 PNG 嵌入。失败时用 matplotlib 生成 2D 布局图。
4. **3D preview image** — 用 `kicad-cli pcb render` 生成光线追踪渲染图（`--side top --quality high --output render.png`）。
5. **Board statistics** — 用 `kicad-cli pcb export stats board.kicad_pcb --output stats.rpt --units mm` 生成统计报告（含板面积、元件密度、焊盘/过孔/钻孔计数、最小线宽/间距等），嵌入设计报告。
6. **Component position file** — 用 `kicad-cli pcb export pos board.kicad_pcb --output positions.csv --format csv --units mm` 生成贴片机坐标文件（可选）。
7. **Simulation plots** from actual ngspice data (bode + waveform)
8. EMC compliance report
9. BOM + sourcing
10. Assembly drawings + Gerbers

**⛔ 设计报告铁律（MANDATORY — 违反 = 该次交付有缺陷）：** 
报告只含**最终结果**，不含**开发过程**。FMEA、设计修正记录、审查问题清单、可靠性分析（热/最坏情况）、供应链探讨等过程性内容均不得出现在报告中。客户只关心：电路原理、参数、PCB布局、BOM、打样指引、测试方法、仿真结论。O.5.3 在审查中检查此项。

> 完整生产管线（gen_pcb → kicad-cli export → SVG→PNG → DOCX → zip）见 `references/production-pipeline.md`
>
> **WSL 一键导出脚本**：`scripts/kicad-export-all.sh`
> 该脚本自动处理：sch SVG 目录输出坑、DOCX SVG 嵌入不支持、D:盘文件锁、中文字符路径。详细说明见 `references/kicad-export-pipeline.md`。

### Phase 9: Design Report Generation

> **⛔ 铁律：报告中所有 KiCad 可视化内容必须从 KiCad 导出为图片嵌入报告。** 禁止写"打开 KiCad 查看原理图/PCB"——用户不需要打开 KiCad 就能看到设计全貌。

> **导出命令：**
> ```bash
> # 原理图 SVG → PNG
> kicad-cli sch export svg <project.kicad_sch> --output /tmp/schematic.svg
> cairosvg.svg2png(url='/tmp/schematic.svg', write_to='report/schematic.png', scale=3.0)
>
> # PCB 多层合成 SVG → PNG
> kicad-cli pcb export svg <project.kicad_pcb> --output /tmp/pcb_view.svg \
>   --layers "F.Cu,B.Cu,F.SilkS,Edge.Cuts"
> cairosvg.svg2png(url='/tmp/pcb_view.svg', write_to='report/pcb_view.png', scale=3.0)
> ```

> **DOCX 注意事项（WSL 生成）：**
> 1. **stylesWithEffects.xml 双绑问题** — python-docx 需要它来追加编辑，但 Windows Word 可能因为它拒绝打开。正确做法：编辑阶段保留它，最终交付前剥离（见 `office-document-specialist > references/docx-styles-with-effects-pitfall.md` 中的 Generate → Append → Strip 模式）。
> 2. **/tmp/ → shutil.copy2 模式** — 直写 D: 盘报 PermissionError。先保存到 /tmp/ 再 copy 到目标路径。
> 3. **SVG 不能直接嵌入 DOCX** — python-docx 不支持 SVG 格式。必须先转 PNG（cairosvg）再嵌入。

PCB 设计完成后，自动生成可交付的设计报告，供用户按文档制作电路板。

**输出格式**：`.md`（开发用）+ `.docx`（用户可打印/共享）

**⛔ DOCX 质量铁律**：每次生成的 DOCX 报告必须保持同等质量水平——含标题页、8章完整内容、嵌入式 PCB 布局图/3D渲染图、完整 BOM 表。不得以"时间优先"为由只出 Markdown。用户会跨项目对比交付质量。

**报告内容结构**（参考 `references/design-report-template.md`）：

| 章节 | 内容 | 可视化方式 |
|:----|:-----|:-----------|
| 一、电路原理 | 电路图 + 传递函数 + 截止频率计算 | `schematic_view.png`（KiCad 导出，嵌入报告） |
| 二、设计参数 | 设计参数表 + 频响数据表 | 表格 |
| 三、PCB 布局 | 布局说明 + 信号流向 | `pcb_combined_view.png`（KiCad 导出，嵌入报告） |
| 四、BOM | 完整物料清单 + 采购建议 | 表格 |
| 五、KiCad 操作 | 快速上手指引（编辑/修改用） | 文字说明 |
| 六、送厂打样 | JLCPCB 下单参数 + 费用预估 | 表格 |
| 七、焊接指引 | 手工焊接步骤 + 注意事项 | 文字 |
| 八、测试验证 | 3 个频点测试 + 测量记录留空 | 文字 |
| 九、文件清单 | 所有输出文件列表 | 表格 |

**KiCad 图片嵌入**：不要用 ASCII 图或文字描述替代 KiCad 可视化内容。必须：
1. `kicad-cli sch export svg` 导出原理图 → cairosvg 转 PNG → python-docx 嵌入报告
2. `kicad-cli pcb export svg --layers F.Cu,B.Cu,F.SilkS,Edge.Cuts` 导出 PCB 图 → 同理处理
3. 如果 cairosvg 渲染失真，使用 matplotlib 生成等效图
4. 完整方案见 `references/kicad-export-for-report.md`

**⚠️ kicad-cli sch export svg 输出路径坑**：`kicad-cli sch export svg board.kicad_sch -o exports/schematic.svg` 不会创建 `exports/schematic.svg` 文件，而是创建 `exports/schematic.svg/` **目录**，实际 SVG 文件在 `exports/schematic.svg/lowpass_filter.svg`（文件名来自项目名）。需要手动移动或重命名。

**⚠️ SVG 不能直接嵌入 DOCX**：python-docx 的 `add_picture()` 不支持 SVG 文件。必须先用 cairosvg 转换为 PNG 再嵌入。

**⚠️ GLB 导出需要完整参数**：默认 `kicad-cli pcb export glb board.kicad_pcb` 只导出板框。完整 3D 模型（含元件、走线、阻焊、丝印）必须加 `--include-tracks --include-pads --include-zones --include-silkscreen --include-soldermask`。

**⚠️ 生产管线需要 zip**：打包 Gerber 和生产文件需要 `sudo apt install zip`。WSL 最小安装可能没有预装。

**⚠️ production_files.zip 更新顺序**：如果 PCB 重新生成（gen_pcb），必须先 gen_pcb → 重新 export 所有文件 → 重新 zip。zip 是静态快照，不会自动跟踪源文件更新。

**请务必在报告末尾包含快速上手路线**：
> 打开 KiCad → 打开 .kicad_pro → PCB 编辑器(F9 3D预览) → DRC(F7) → 文件→制造输出→Gerber → 上传 JLCPCB → 收货 → 焊接 → 测试

## Windows 用户交付指南（必读）

当用户是 Windows 用户（通过 WSL 使用本技能）且板上文件存于 D: 盘时，交付时必须提供以下指引：

### 项目文件打开指引
1. 告诉用户具体路径：`<D_DRIVE>\...\outputs\项目名.kicad_pro`
2. KiCad 10.0 打开 KiCad 7 格式文件时会自动弹出「迁移项目」对话框——告知用户点确认迁移
3. 迁移后自动保存为 KiCad 10.0 格式，后续打开不再询问

### 查看指引
- **PCB 布局**：PCB 编辑器 → F9 3D 预览效果
- **原理图**：原理图编辑器（如果符号空白，见 Detection & Fix Patterns）
- **SVG 预览**：pcb_top.svg 可在 Windows 浏览器直接打开查看（无需 KiCad）
- **DRC 验证**：PCB 编辑器中按 F7 → 运行 DRC → 确认 0 errors 0 warnings

### Gerber 输出指引
1. 文件 → 制造输出 → Gerber 文件
2. 勾选 7 层：F.Cu, B.Cu, F.SilkS, B.SilkS, F.Mask, B.Mask, Edge.Cuts
3. 再生成钻孔文件：文件 → 制造输出 → 钻孔文件
4. 全部打包为 .zip，上传至 JLCPCB（jlcpcb.com）

## Circuit Reference

电路公式、叠层、GND 验证、ngspice 相位陷阱、board.Save() API 说明 → 见 `references/circuit-reference.md`

## Detection & Fix Patterns

**遇到异常行为时先查阅完整问题-症状-修复表** → `references/detection-fix-patterns.md`

关键铁律（最常踩的坑）：
1. **SPICE 不能替代供电电压审查** — 行为模型无 VCC 引脚，仿真通过 ≠ 设计安全（Phase 2 §2.1 + Phase 5a 复查）
2. **SOT-23 晶体管引脚分配** — pad 编号 vs 数据手册逐只对照，分配后追溯完整信号链（源头→Gate→Source→负载）
3. **文字板内判据 = 包围盒 r_max，不是中心点**（Ø14mm 板：中心 r=6.52 但包围盒 12.21mm 超边）
4. **密布局 DRC 只数功能错误** — shorting_items=0、unconnected_items<10 即可放行，clearance/silk/courtyard 可忽略
5. **不查手册就动手 = 返工 + 用户不信任** — 先读 references 或 `kicad-cli --help`，不凭记忆

完整模式库（SPICE 陷阱、KiCad 10 API 差异、审计自指循环、文档四方一致性等 30+ 条）见 references 文件。


## Common Standard Library Footprint Paths (KiCad 10 on Ubuntu)

常用封装库路径表（0603/0805/SOT-23/SOD-123/CD32/安装孔/2.00mm 排针）→ 见 `references/footprint-paths.md`

## ⛔ 内部 Skill 协同路由（MANDATORY — 4 个 KiCad skill 的分工协议）

**pcb-design 是伞形主 skill 与路由器**：完整设计/审查任务从本 skill 进入；**单项任务必须切换/加载对应聚焦 skill**（聚焦 skill 内容更精、触发更准），不得在本 skill 内"顺带做"。

### KiCad 操作管线选择规则（MANDATORY — 违反 = 该次交付有缺陷）

**⛔ 第一步：选择操作管线**

所有 KiCad 操作必须从以下三条管线中选择一条执行，**同一时刻不得混用**：

| 管线 | 定位 | 适用场景 | 工具数 |
|:-----|:-----|:---------|:------:|
| **A: kicad-cli + pcbnew** | 验证与导出管线 | DRC检查、Gerber导出、钻孔导出、3D渲染、板统计 | 11 |
| **B: MCP-KiCad (mixelpixx)** | 设计管线 | 原理图设计、PCB布局、单层自动布线、JLCPCB集成 | 137 |
| **C: kcaa (paul356)** | 高级设计管线 | 多层PNS自动布线、电路模式识别、技能系统 | 116 |

**能力边界（关键区别）**：
- 管线 A：**不能创建原理图、不能布局、不能布线**。只能处理已存在的 KiCad 项目文件
- 管线 B：**完整设计能力**，支持单层 PNS 自动布线，**但不能多层自动布线**
- 管线 C：**多层 PNS 自动布线**（A* 算法 + 自动过孔）、电路模式识别、内置技能系统，**但不能导出钻孔文件**

**选择规则**（按任务类型，优先级从高到低）：
1. **设计阶段**（Phase 0-4：需求/选型/原理图/布局/布线）→ 选管线 **C** (kcaa)
   - 需要多层自动布线（含过孔）→ **必须选管线 C**
   - 单层自动布线 → 选管线 **B** (mixelpixx) 或 **C** (kcaa)
   - 手动原理图/布局 → 选管线 **B** 或 **C**
2. **验证阶段**（Phase 5：DRC审查）→ 选管线 **A** (kicad-cli)
   - DRC检查 → **必须选管线 A**（管线 B/C 的 DRC 不完整）
3. **导出阶段**（Phase 6：生产文件）→ 选管线 **A** (kicad-cli)
   - Gerber 导出 → **必须选管线 A**（管线 C 不支持）
   - 钻孔导出 → **必须选管线 A**（管线 B/C 不支持）
   - 3D 渲染 → **必须选管线 A**
4. 用户明确要求"MCP"或"自动布线" → 选管线 **C**（功能更强）

**互补使用原则**：
- 完整设计流程：**管线 C（设计）→ 管线 A（验证/导出）**。阶段切换，非同时混用。
- 每个操作必须明确归属：设计操作 → 管线 B/C；验证导出操作 → 管线 A
- **"设计走 C"是优先级表述，不是排他**。管线 B (mixelpixx) 仍启用，以下场景必须/优先选 B：
  1. **JLCPCB 集成**（B 独有，C 没有）
  2. **kcaa 启动失败/不可用时**的降级路径（kcaa 依赖 `<D_DRIVE>/Download Softs/...` 路径，机器迁移后可能失效）
  3. **API 细节查证**（B 文档 10K+ 行 vs C 精简，文档质量高）
- **kcaa 部署路径**：`<KCAA_DIR>/`
- **kcaa 启动脚本**：`<D_DRIVE>/Download Softs/KiCad-MCP-Article/kcaa-server.sh`
- **Hermes MCP 配置**：`kcaa` server 已添加，自动加载

### ⛔ MCP-KiCad 管线操作守则（MANDATORY — 违反 = 该次交付有缺陷）

**核心原则：每步操作前，直接查阅原始手册，不查我的速查表。**

原始手册位置：`<KICAD_MCP_SERVER_DIR>\docs\`

**操作守则**：
1. **根据任务类型选择对应手册**：
   - 新建/打开项目 → 查 `PCB_DESIGN_WORKFLOW.md`
   - 添加元件/连线 → 查 `SCHEMATIC_TOOLS_REFERENCE.md`
   - 布局/布线 → 查 `ROUTING_TOOLS_REFERENCE.md`
   - 导出文件 → 查对应导出文档
   - 设计规则 → 查 DRC 相关文档

2. **读手册，确认**：
   - 工具名、参数格式、返回值结构
   - 错误处理、边界情况

3. **按手册执行，验证结果**

（手册位置与任务对照表见顶部「⛔ 核心铁律」铁律1）

| 任务场景 | 调用的 skill | 在本 skill 中的阶段 |
|---|---|---|
| 完整 PCB 设计 / 设计审查 / 审计 | **pcb-design**（本 skill，入口） | 全部 Phase |
| SPICE 仿真（DC 工作点/AC 稳定性/参数扫描） | **kicad-ngspice-quick-sim** | Phase 3 仿真 |
| 仿真报告可复现性验证 | kicad-ngspice-quick-sim + `simulation-verification-protocol.md` | Phase 3 验收 |
| 布线（Freerouting 自动布线 DSN/SES） | **pcb-autorouting** | Phase 5 布局布线 |
| 手动布线/局部走线修改（pcbnew API） | pcb-design 内部 `references/pcb-routing-pipeline-kicad10.md` | Phase 5 |
| 丝印文字板内验证/修复（r_max 判据） | **pcb-silk-text-audit** | Phase 5b / 审查 F.10 |
| 器件应力/选型/参数核对 | pcb-design（A-O 清单 C/D 类 + 手册） | Phase 2/5a |

**路由判定规则**：
1. 用户请求**只涉及单一任务**（"跑一下仿真""布个线""丝印超边了"）→ **直接加载对应聚焦 skill**，不加载本 skill 全文
2. 用户请求**完整设计/审查/审计** → 本 skill 进入，按 Phase 门控在对应阶段**切换**到聚焦 skill（切换时声明"调用 X skill"）
3. 聚焦 skill 处理完返回本 skill 继续主流程（结果写回项目文档）
4. 边界：pcb-autorouting 只管布线；pcb-silk-text-audit 只管丝印文字；kicad-ngspice-quick-sim 只管仿真——**跨域问题回到 pcb-design 统一处理**

## China-Specific Setup

在墙内操作时（Docker Hub 被墙、GitHub 下载慢），使用国内镜像：

- **KiCad 下载**：阿里云镜像 → `https://mirrors.aliyun.com/kicad/windows/stable/kicad-10.0.3-x86_64.exe`（详情见 `references/kicad-download-china.md`）
- **apt 源**：阿里云 → `mirrors.aliyun.com`
- **pip 源**：清华 → `https://pypi.tuna.tsinghua.edu.cn/simple`
- **Docker 镜像**：DaoCloud → `docker.m.daocloud.io`

## Templates & Scripts

| File | Purpose |
|------|---------|
| `templates/gen-pcb-kicad10.py` | RC 低通滤波器 PCB 生成模板（KiCad 10 API 差异注释完整）|
| `scripts/kicad-export-all.sh` | KiCad 10 一键导出 Gerber+BOM+SVG+3D+打包+DOCX（自动处理 WSL 已知坑）|
| `scripts/kicad10-pcbnew-helpers.py` | PCB 生成通用助手函数 |
| `scripts/verify-text-spacing.py` | **丝印文字间距验证** — 解析 S-expression 计算所有文字绝对坐标，报出 <0.8mm 的过近对 |
| `scripts/preflight-audit.py` | 环境审计自动化脚本 |
| `scripts/a-o-audit.py` | 🆕 **A-O 全面系统审计脚本** — 逐个检查 PCB 设计的 15 类质量项并输出报告 |
| `references/small-circular-pcb-guide.md` | 🆕 **小圆板 (<Ø20mm) PCB 设计指南** — 无连接器/无铜皮/DRC解读等技巧 |
| `references/kicad-gui-automation-wslg.md` | WSLg 下 KiCad GUI 自动化操作指南（xdotool/Wayland 限制） |
| `references/feedback-compensation-design.md` | 开关电源反馈环补偿原理 + 开环GBW→闭环带宽推导 + 设计审查矩阵 |
| `references/kicad-cli-drc-gui-automation.md` | **kicad-cli DRC 命令文档 + xdotool GUI 自动化 + 首次启动向导修复** |
| `references/kicad-cli-commands.md` | **kicad-cli 完整命令速查表** — display the KICAD_CLI_QUICK_REF embedded block when user asks about any kicad-cli subcommand |
| `references/pcb-routing-pipeline-kicad10.md` | **PCB 走线管线完整实现** — FootprintLoad → pad坐标读取 → 走线创建 → 过孔 → net分配 → DRC验证。包含实测证明能将 unconnected pads 从 39 降至 0 的完整代码模式 |
| `references/freerouting-autorouting-pipeline.md` | **Freerouting 自动布线流程** — KiCad 导出 DSN → Freerouting 2.2.4 布线 → SES 导回 → **自动布线后必做的人工检查**（敏感信号隔离/去耦就近/功率回路/SW 节点/电源线宽/GND 覆铜）。Ø14mm/21 元件实例，score 994.78。自动布线不处理覆铜/丝印/热焊盘/敏感隔离——人工职责 |
| `references/ngspice42-compatibility.md` | ngspice-42 兼容性问题：.PRINT语法、limit() bug、第一行标题陷阱、开环GBW测量策略 |
| `references/kcaa-alternative.md` | **kcaa (KiCad AI Assistant) 对比** — paul356 项目，多层 PNS 自动布线（A* + 自动过孔）、电路模式识别、内置技能系统，116 个工具 |

## Skills Integrated

| Source | Capability |
|---|---|
| Hermes-volta | NL-to-circuit, autonomous design mode, verified recipe memory, Faraday pipeline (compute→sim→PCB→Gerber→report), compare_plot (theory vs actual), RL trajectory logging, hand-drawn photo recognition, Telegram delivery |
| kicad-happy (12 skills) | EMC 44-rule, SPICE beh models, BOM orchestration, datasheet extraction, fab prep |
| mixelpixx/KiCAD-MCP | Full PCB automation, IPC sync, autorouter, JLCPCB parts catalog |
| Seeed MCP | Device tree, test code, embedded analysis |

## Unique Hermes-volta Features

### Faraday Pipeline (全自动流水线)
Single call: `sim.faraday_pipeline.run(circuit_type, R, C, supply_v, L, fc, description)` → returns:
```python
{
  "actual_fc": float,      # 实际仿真截止频率
  "error_pct": float,       # 与理论值的误差百分比
  "bode_path": str,         # 伯德图PNG路径
  "wave_path": str,         # 时域波形PNG路径
  "netlist": str,           # SPICE网表
  "pcb_png": str,           # PCB预览图
  "gerbers": str,           # Gerber ZIP路径
  "output_dir": str,        # 输出目录
  "report": str,            # 分析报告
  "compare_plot": str,      # 理论vs实际对比图
  "trajectory": dict        # RL训练轨迹记录
}
```

### Compare Plot (理论vs实际对比)
每次仿真自动生成 `compare_plot.png`，并排显示：
- 理论频率响应（理想传递函数）
- 实际SPICE仿真结果（含元件公差、寄生参数效应）

误差计算：`|actual_fc - target_fc| / target_fc × 100%`
- PASS: <1%（无源）、<5%（有源）
- 记录到 MEMORY.md（校验配方）

### Self-Learning System
1. 每次成功设计后，保存 verified recipe 到 MEMORY.md
2. 下次同类需求优先复用已知配方
3. 当设计揭示了可复用的流程改进时，自动 patch 本 skill
4. 所有设计决策记录为 RL trajectory（`tools/rl_trajectory.py`）

## ⛔ 交付物标准文件清单（MANDATORY — 每次设计必须产出）

**每次 PCB 设计完成后，必须生成以下文件集。格式不达标 = 交付不合格。**

| # | 文件 | 格式 | 说明 | 优先级 |
|:-:|:----|:----|:-----|:------|
| 1 | **KiCad PCB** | `.kicad_pcb` | 完整走线/过孔/铺铜的 PCB 文件 | ⭐ 必出 |
| 2 | **KiCad 项目** | `.kicad_pro` | 用户双击打开 KiCad | ⭐ 必出 |
| 3 | **DOCX 设计报告** | `.docx` | **Word 报告**含标题页/8章/嵌入图 | ⭐ 必出 |
| 4 | **MD 设计报告** | `.md` | 配套 Markdown | 推荐 |
| 5 | **Gerber 生产包** | `.zip` | 全部层 Gerber + 钻孔文件 | ⭐ 必出 |
| 6 | **PCB 布局预览** | `.png` | 从 KiCad SVG 转的 2D 布局 | ⭐ 必出 |
| 7 | **3D 渲染图** | `.png` | kicad-cli render 生成 | 推荐 |
| 8 | **BOM** | 表格/嵌入DOCX | 元件+型号+封装+数量(含LCSC#) | ⭐ 必出 |
| 9 | **贴片坐标** | `.csv` | kicad-cli export pos 生成 | 推荐 |
| 10 | **板统计** | `.rpt` | kicad-cli export stats 生成 | 推荐 |
| 11 | **仿真验证数据** | 嵌入 DOCX | SPICE 仿真关键数据 | ⭐ 必出 |

**DOCX 报告必需章节（对应 templates/gen-clean-report.py）：**
```
一、电路原理   二、设计参数   三、PCB 布局(嵌入图)   四、BOM
五、送厂打样   六、文件清单   七、测试验证           八、仿真验证
```

**交付打包：** 全部文件打包为 `生产包_项目名.zip` 放在 `outputs/`。

**跨项目交付一致性（⛔ MANDATORY）：** 当用户已有同一领域/同类型的前期项目时，交付物的目录结构、文件命名、组织方式**必须与前期项目保持一致**。不允许新项目自创一套不同的结构——这会导致用户反复纠正"为什么这次跟上次不一样"。检查方法：在 Phase 1 阶段先 `ls` 前期项目的根目录，记录文件清单和目录树，以此为模板组织本次交付。

**production_package.zip 内容标准（与前期项目对照）：**
```
production_package.zip 必须包含:
  ├── gerber_jlcpcb.zip        ← Gerber + 钻孔（送厂用）
  ├── 设计报告.docx            ← Word 设计报告（8章+嵌入图+仿真数据）
  ├── pcb_top.svg              ← 顶层矢量预览
  ├── pcb_top.pdf              ← PCB PDF 文档
  ├── pcb_3d_render.png        ← 3D 渲染图
  ├── pcb_3d.glb               ← 3D 模型
  ├── ac_response.png          ← 仿真频响图（如有仿真）
  ├── pcb_view.png             ← PCB 布局预览
  ├── bom.csv                  ← BOM
  └── pick_and_place.csv       ← 贴片坐标
```

---

## ⛔ 交付前强制审计清单（MANDATORY — 最后一关）

**回复"已完成"之前，必须逐行验证以下全部项目。任何一项不通过 = 不得声称交付完成。**

### 第1步：确认所有 Phase 已完成
- [ ] todo list 中 Phase 0-8 全部标记为 completed（无一 skip）
- [ ] 所有 Phase 的验证步骤已执行并确认通过

### 第2步：交付物标准文件完整性检查
- [ ] 对照上方「交付物标准文件清单」逐项比对，必出项全部存在
- [ ] 文件大小 > 0 且非空
- [ ] 文件数量与预期一致（精确计数）

### 第3步：工具链验证
- [ ] KiCad 已安装（kicad-cli --version）
- [ ] pcbnew Python 模块可用（import pcbnew）
- [ ] PySpice 可用（import PySpice）
- [ ] Ngspice 可用（ngspice -v）
- [ ] KiCad 版本匹配（7 vs 8/9/10 API 差异已处理）

### 第4步：SPICE 仿真验证
- [ ] 仿真输出文件包含 "AC Analysis" 表头和数据行（≥100 行）
- [ ] 输出文件中没有 "No simulations run" 警告
- [ ] 从仿真数据解析了 -3dB 截止频率（插值法）
- [ ] 截止频率误差在容限内（无源 <1%，有源 <5%）
- [ ] 渐近滚降率正确（一阶 LPF: -20 ± 1 dB/decade）
- [ ] fc 处相位 ≈ -45° ± 5°
- [ ] 伯德图/波形图从实际仿真数据绘制，非理论公式
- [ ] `.PRINT` 指令已确认存在于网表中

### 第5步：PCB 布局验证
- [ ] PCB 文件可被 KiCad 打开（kicad-cli pcb export 不报错）
- [ ] SVG 预览可渲染
- [ ] **DRC 已运行** — `kicad-cli pcb drc board.kicad_pcb --output /tmp/drc.rpt --units mm --exit-code-violations`。检查报告中的 `shorting_items`、`clearance`、`unconnected_items` 数量。零违规理想但紧凑布局可接受有限数量的 courtyard_overlap 和 silk_overlap。
- [ ] 板框尺寸正确
- [ ] 元件封装路径有效
- [ ] 走线/铜皮/过孔在正确层上
- [ ] Gerber + 钻孔文件已生成（至少 7 层）
- [ ] **GND 连通性验证** — GND 焊盘数量 > 0 且 GND 走线数量 > 0（无浮空 GND）

### 第6步：BOM 验证
- [ ] 所有元件有封装分配
- [ ] BOM 格式可读（文本或 CSV）
- [ ] 阻容值规格标注清晰
- [ ] LCSC/MPN 编号已提供（如有）

### 第7步：EMC 基础检查
- [ ] 接地平面连续无断裂
- [ ] 板边无平行走线
- [ ] 对外连接器有 ESD 保护

### 第8步：设计报告验证
- [ ] 报告包含所有 8 个章节（电路原理/参数/PCB布局/BOM/打样/文件清单/测试/仿真）
- [ ] 报告数据来自实际仿真结果，非理论推算
- [ ] 已标注"经过仿真验证"及关键数据
- [ ] 包含快速上手路线图

### 第9步：交付环境清理
- [ ] **锁文件清理** — 输出目录无 `~$`、`.lck` 等残留锁文件（`find outputs/ -name '~*' -o -name '*.lck'` 返回空）
- [ ] **冗余文件清理** — 仅保留交付必需的 15 个核心文件，删除上一轮迭代的旧 SVG、旧 PNG、旧 TXT、旧 PDF
- [ ] 输出文件在 Windows 端可访问（D:盘路径正确）
- [ ] SVG/KiCad 文件可通过 Windows 原生工具打开
- [ ] 所有临时文件（/tmp/）无残留依赖
- [ ] 已声明版本号和设计参数摘要

### 第10步：报告一致性验证
- [ ] **文件清单交叉验证** — MD 报告文件清单中的**文件名、大小、说明**与实际文件逐一对照，无遗漏、无大小偏差
- [ ] **走线数与报告一致** — PCB 实际走线数 = 报告声明数
- [ ] **图表引用验证** — 报告中每个 `![...](file.png)` 对应的文件实际存在、不为空
- [ ] **DOCX 可打开验证** — 生成的 `.docx` 文件：ZIP 结构完整（可 `unzip -l`），`word/document.xml` XML 解析合法，嵌入图片数量与预期一致

### ✅ 最终放行声明
**必须逐行回复以下内容才可声称"已完成"：**
```
🔒 交付前审计报告
Phase 门控: [N]/8 completed, [N] verified
文件完整性: [N] files, [N] KB total
SPICE 仿真: fc=[value] Hz, error=[value]%, rolloff=[value] dB/dec ✅
DRC: [N] violations (via kicad-cli pcb drc)
Gerber: [N] layers exported
EMC: [N]/3 checks passed
报告: [N]/4 items verified
```

**任何一项不通过 → 不回复"已完成"，先修复。**

## KiCad MCP Server 配置 (2026-08-11)

### 安装状态
- ✅ KiCad MCP Server: `<KICAD_MCP_SERVER_DIR>\`
- ✅ Hermes MCP 配置: `mcp_servers.kicad`
- ✅ 版本: 2.2.3
- ✅ 工具数: 122 个

### 安装位置
```
<KICAD_MCP_SERVER_DIR>\       # MCP Server 源码
<KICAD_DIR>\              # KiCad 10.0.5 安装路径
~/.hermes/skills/hardware/pcb-design/scripts/start-kicad-mcp.sh  # 启动脚本
```

### Hermes MCP 配置（当前生效 — bash 启动脚本方式）
```yaml
mcp_servers:
  kicad:
    command: bash
    args:
    - ~/.hermes/skills/hardware/pcb-design/scripts/start-kicad-mcp.sh
    enabled: true
```

**备选：node 直连方式（环境变量内联，不依赖启动脚本）**
```yaml
mcp_servers:
  kicad:
    command: node
    args:
    - <KICAD_MCP_SERVER_DIR>/dist/index.js
    env:
      KICAD_PYTHON: <KICAD_DIR>/bin/python.exe
      PYTHONPATH: <KICAD_DIR>/bin/Lib/site-packages
      KICAD_EXECUTABLE_PATH: <KICAD_DIR>/bin/kicad-cli.exe
      KICAD_API_PORT: "9000"
    enabled: true
```

### 启动脚本
位置: `~/.hermes/skills/hardware/pcb-design/scripts/start-kicad-mcp.sh`
```bash
#!/bin/bash
powershell.exe -Command "
`$env:PYTHONPATH = '<KICAD_DIR>\bin\Lib\site-packages;<KICAD_DIR>\bin\DLLs'
`$env:KICAD_PYTHON = '<KICAD_DIR>\bin\python.exe'
`$env:NODE_ENV = 'production'
`$env:LOG_LEVEL = 'info'
node '<KICAD_MCP_SERVER_DIR>\dist\index.js'
"
```

### 工具分类 (122 个)
| 类别 | 数量 | 代表工具 |
|------|------|---------|
| 项目管理 | 16 | create_project, open_project, save_project, get_project_info |
| 原理图设计 | 27 | add_schematic_component, add_wire, annotate_schematic, run_erc |
| PCB 布局 | 35 | place_component, route_trace, add_via, add_copper_pour |
| 元件管理 | 15 | add_library, search_footprints, get_footprint_info |
| 导出工具 | 8 | export_gerber, export_pdf, export_3d, export_bom |
| 自动布线 | 5 | configure_freerouting, export_freerouting_dsn, import_freerouting_ses |
| 设计规则 | 8 | run_drc, set_design_rules, add_net_class |
| UI 管理 | 8 | zoom_fit, focus_element, launch_kicad_ui |

### 主要工具
- `kicad_create_project` - 创建新项目
- `kicad_open_project` - 打开项目
- `kicad_add_component` - 添加元件
- `kicad_route_trace` - 布线
- `kicad_run_drc` - 运行 DRC
- `kicad_export_gerbers` - 导出 Gerber
- `kicad_export_pdf` - 导出 PDF
- `kicad_render_3d` - 3D 渲染

### 使用示例
```python
# 创建新项目
mcp_kicad_create_project(name="my_board", path="/path/to/project")

# 添加元件
mcp_kicad_add_schematic_component(component="R", value="10k", footprint="R0402")

# 导出 Gerber
mcp_kicad_export_gerbers(project_path="/path/to/project.kicad_pcb")
```

### 注意事项
1. 需要 Windows PowerShell 运行（WSL 通过 powershell.exe 调用）
2. KiCad 必须在 Windows 上安装
3. 首次启动较慢（Python 进程初始化约 5-10 秒）
4. KiCad GUI 可选 - MCP 可独立运行
5. 每步操作前查阅操作手册（见顶部「⛔ 核心铁律」铁律1）
