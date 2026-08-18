# Feedback Loop Compensation Design

## Constant-Current Source (CCS) Compensation

### Problem Statement

A laser diode driver uses: VREF → VCVS(error amp, gain>>1000) → MOSFET(gate) → Rsense(feedback). The 3-stage cascade (amp → MOSFET → sense) creates a high-gain feedback loop that is prone to:

- **SPICE convergence failure** — singular matrix / NaN during closed-loop transient analysis
- **Numerical oscillation** — high gain amplifies numerical noise
- **Zero small-signal AC gain** — DC operating point hits rail before AC analysis linearizes

### 补偿原则（Compensation Principle）

在误差放大器输出端（门极驱动）对 GND 加一个电容 C_comp，形成一个 RC 低通极点：

```
EAMP (gain A) ──R_amp──┬── GATE_DRV ── MOSFET ── Rsense ── VSNS
                        │
                       C_comp
                        │
                       GND
```

- 放大器输出电阻（R_amp ≈ 1Ω） + C_comp 形成一个极点：**fp = 1 / (2π × R_amp × C_comp)**
- 这个极点降低了高频增益，使反馈环路在穿越频率前获得足够相位裕度
- 同时也让 SPICE 求解器更容易收敛（缓解了高频增益带来的数值噪声放大）

### 补偿电容取值经验

| 目标带宽 | C_comp 范围 | 典型 RC 时间常数 |
|:---------|:-----------|:-----------------|
| TTL 40KHz 调制 | 10-100pF | 1μs — 40KHz 周期 25μs |
| 高保真音频 (<20KHz) | 100pF-1nF | 10μs |
| DC-only（无调制） | 1nF 或以上 | 100μs+ |

**激光驱动器实测**（2026-06-05, TLV2171, Rsense=0.1Ω）：
- C_comp = 100pF → fp ≈ 1.6MHz（远高于 40KHz，不影响调制带宽）
- 环路稳定性：通过开环 Bode 图确认 DC gain=99.3dB, GBW=2.4MHz
- 闭环 -3dB 带宽 ≈ 1.2MHz >> 40KHz ✅

### 补偿电容不适用场景

| 场景 | 为什么不行 | 替代方案 |
|:-----|:----------|:---------|
| 需要 >1MHz 调制带宽 | 补偿极点限制了带宽 | 用开环 GBW 推导，不在闭环调补偿 |
| 多极点反馈网络 | 单极点补偿可能不够 | 双极点/超前滞后补偿 |
| 开关电源反馈补偿 | 需要 Type II/III 补偿 | 用开关电源专用的补偿网络 |

## 开环 Bode → 闭环带宽推导

当闭环 SPICE 仿真不收敛时，用以下方法验证带宽：

### 步骤

1. **断开反馈**：断开放大器反相端与采样电压的连接，将反相端接地
2. **开路负载**：输出端接 1MΩ || 0.1pF 到 GND（高阻负载）
3. **AC 激励**：同相端加 DC 偏置 + AC 1V 小信号
4. **扫频**：.AC DEC 100 10 10MEG
5. **读取 GBW**：从 Bode 图找 0dB 穿越频率点
6. **计算闭环带宽**：深度负反馈下，闭环 -3dB 带宽 ≈ GBW

### 理论依据

一阶运放模型的开环传递函数：
- A(s) = A_DC / (1 + s/ωp)
- 单位增益带宽（GBW）= A_DC × fp
- 闭环 -3dB 带宽（单位增益）≈ GBW

### 验证标准

| 参数 | 判定 | 来源 |
|:-----|:-----|:-----|
| GBW vs datasheet | 误差 < 5% | 开环 AC 仿真 |
| DC 增益 | > 80dB | 开环 AC 仿真 |
| 闭环带宽 vs 调制频率 | 带宽 ≥ 5 × 调制频率 | GBW / (1 + βA) |
| 相位裕度（如可测）| > 45° | 开环 AC 仿真 |

**不需要闭环 SPICE。开环 GBW 足够。** 详见 `pcb-design/SKILL.md` > Phase 3 > 开环运放带宽测量法。

## 7 维设计审查（Design Review Matrix）

### 审查维度

| # | 维度 | 检查内容 | 典型失败案例 |
|:-:|:-----|:---------|:------------|
| 1 | 供电电压 | 每颗 IC 的 Vmax ≥ 实际供电电压 × 1.25 | TLV2371(5.5V) on 9.5V Boost rail |
| 2 | 功率耗散 | 每个功率元件 P_actual ≤ P_rated × 0.8 | Rsense 0.6W in 1206(0.5W) |
| 3 | 电流能力 | MOSFET/Ic ≥ I_max × 1.5, 电感 Isat ≥ I_peak × 1.2 | — |
| 4 | 逻辑方向 | 控制信号上拉/下拉与规格一致 | TTL enable pull-up to GND (wrong: should be VIN) |
| 5 | 保护完整性 | 反接/ESD/过流保护是否覆盖每个外部接口 | 缺 D2 反接保护、缺 CE1-3 ESD 电容 |
| 6 | EMC 合规 | 接地连续、板边无平行线、ESD 到口 | — |
| 7 | PCB 布局 | 走线顺序、GND 连通性、补偿靠近 IC | GND 浮空 = 无回路 |

### 审查顺序

```
供电电压       → 最严重（烧毁）
功率耗散       → 次严重（过热/I²R烧毁）
电流能力       → 功能性
逻辑方向       → 功能性（与控制信号有关）
保护完整性     → 长期可靠性
EMC 合规       → 合规性
PCB 布局       → 可制造性
```

**理由**：烧毁 > 过热 > 功能异常 > 长期失效 > 合规 > 制造。按此顺序审查，确保最严重的错误在第 1 次遍历就被抓住，不因为审查疲劳错过。
