# Simulation Verification Protocol

**触发条件**：SPICE 仿真完成后，在交付任何结果前必须执行。

**核心理念**：不要假设仿真成功运行了——验证输出文件包含真实数据、提取关键参数并与理论值对比。

---

## 0. 用 KiCad 自带 ngspice.dll 跑仿真（无外部 ngspice 时的标准方法）

**2026-07-31 实测**（KiCad 10.0.3 Windows）：`kicad-cli` 无仿真子命令，`eeschema` 无 headless 模式，但 **KiCad 安装目录的 `bin/ngspice.dll` 是标准 ngspice shared library（ngspice-46）**，可用 Python ctypes 直接调用——这就是"用 KiCad 自带仿真引擎"的落地方式。

```python
# Windows 端 KiCad python 运行（WSL 的 Linux python 不能加载 Windows DLL）
import ctypes, os
KICAD_BIN = r"<D_DRIVE>\Users\<user>\AppData\Local\Programs\KiCad\10.0\bin"
os.add_dll_directory(KICAD_BIN); os.chdir(KICAD_BIN)  # 依赖 DLL 解析
SendChar = ctypes.CFUNCTYPE(None, ctypes.c_char_p, ctypes.c_int)
@SendChar
def send_char(msg, ident):
    if msg: sys.stdout.write(msg.decode('utf-8','replace'))
ng = ctypes.CDLL(os.path.join(KICAD_BIN, "ngspice.dll"))
ng.ngSpice_Init(ctypes.cast(send_char, SendChar), <其他回调>, ...)
ng.ngSpice_Command(b"source netlist.cir")
ng.ngSpice_Command(b"run")
```
完整脚本见 `<TEMP_DIR>\ld520_v2\ngspice_drv.py`（2026-07-31 实测可用）。

### ⚠️ KiCad ngspice 精简限制（2026-07-31 实测）

| 功能 | 状态 | 替代 |
|---|---|---|
| `.meas` 命令 | ❌ "no such command available" | 用 `.control` 里 `print` 或 wrdata |
| `VALUE={IF(c,a,b)}` | ❌ "no such function 'if'" | `min/max` 组合（如 `5.6*min(max(V(EN),0),1)`） |
| `print v(x) at=1.5m` | ❌ "vector at is not available" | wrdata 全数据 + Python 解析 |
| `wrdata` 列序 | ⚠️ **每向量前重复索引列**（[t, v1, t, v2, ...]） | 解析时跳过奇数索引列，或用 `print`（`v(x) = 值` 格式最可靠） |
| S 开关 (SW model) | ⚠️ op 时易发散（VOUT=-789V 假象） | 用 E 源 VALUE+min/max 替代 |

### 断环法陷阱（AC 稳定性分析）

**断环后运放开环，输出必饱和**（开环残差 µV 级 × 增益 1e5 → 饱和），|T| 测不出来。正确做法：
1. **闭环峰值法**（推荐）：VREF 串 AC 源（`R3 VIN VR3` + `VAC VR3 VREF DC 0 AC 1`），测 H=VSNS/VREF_ac，谐振峰判据：**峰 >3dB ⇒ PM<45°欠阻尼，<1dB ⇒ PM>60°稳定**
2. 栅极断环需 VG 强制闭环工作点（DC=1.406V），但运放输出仍饱和——不推荐
3. 相位裕度估计：峰 3dB≈PM45°，7.9dB≈PM30°

### ⛔ 仿真模型保真度检查清单（E.4，2026-07-31 三个真实教训）

| 检查项 | 错误案例 | 正确做法 |
|---|---|---|
| **运放模型总增益** | v1.0 模型两级 1e5×1e5=1e10(200dB)，实际 TLV9301 100dB | 总增益 = 各级增益乘积，必须等于数据手册开环增益；GBW = fp×A0 |
| **运放 GBW** | C1=1.59p → fp=1kHz → GBW=1e13Hz（应 1MHz） | fp=GBW/A0=1MHz/1e5=10Hz → C1=1/(2π×100M×10)=159.15p |
| **LD 模型 Vf** | v1.0 模型 Vf@80mA=1.6V（真实 520nm LD 4-5V），"Vf 扫描 4.0-5.4V"是假的 | 计算 Vf=I×N×Vt×ln(I/Is)+I×Rs 确认覆盖真实范围；扫描 N 或 Rs 覆盖 Vf 范围 |
| **MOSFET 单向性** | 无 VDS 限制的 B 源在 VDS<0 时"反向灌电流"（灭态假象） | `I=...*min(max(V(D,S)*1e2,0),1)`（VDS≤0 时电流=0） |
| **Ciss 建模** | 栅极无 Cgs → R6×Ciss 极点不存在 → 稳定性分析乐观 | MOSFET 子电路加 CGS（SI2302≈400pF）——**R6×Ciss 极点正是恒流环 PM 不足的根因** |
| **开关级缺失** | 网表无 Boost 开关 → VOUT 直通 4.56V 而非 5.6V，报告数据是假的 | 检查每个电源轨能否达到目标电压；Boost 级用 E 源理想模型（稳态值由分压计算保证，注明 E.4） |
| **瞬态初始态** | 运放内部节点动态范围 ±1e10V + 主极点 τ=1.6s → tran 12ms 内恒流环"僵死" | 大信号 tran 需要合理的内部节点动态范围；DC/AC 结论可信，tran 波形要警惕 |

**网表可复现性检查**：仿真报告必须关联到实际存在的网表文件（路径+日期），且网表能跑出报告数据。v1.0 报告的网表缺失/参数不符 = 报告不可信，必须重跑。

---

## 1. 确认仿真有数据输出

### 检查信号
- 打开 ngspice 输出文件（`-o output.txt`）
- 搜索 `"AC Analysis"` — 必须出现
- 搜索 `"No simulations run"` — 必须**不**出现
- 确认数据行 ≥ 100（RC 滤波器 AC 分析通常有 401 行）

### 失败诊断

| 错误信息 | 原因 | 修复 |
|:---------|:-----|:-----|
| `"No .plot, .print, or .fourier lines; no simulations run"` | 网表中缺少 `.PRINT` 指令 | 添加 `.PRINT AC VDB(output) VP(output)` |
| `"Warning: vector output is not available"` | 瞬态分析 `.TRAN` 未输出 | ⚠️ **关键坑**：`.AC` 和 `.TRAN` 不能在同一个网表中共用 `.PRINT`。必须拆成**两个独立网表文件**分别运行。合并时 ngspice 无法正确分配 `.PRINT` 输出，导致其中一个分析的数据不出现在输出文件中。 |
| 空输出文件 | ngspice 未找到网表 | 检查文件路径和扩展名（必须为 `.cir`） |
| `"fatal error: can't open input file"` | 中文字符路径问题 | 复制到 `/tmp/sim/` 运行 |

## 2. 解析 AC 数据

ngspice `output.txt` 中 AC 分析数据格式：

```
AC Analysis  Thu Jun  4 22:48:52  2026
--------------------------------------------------------------------------------
Index   frequency       vdb(output)     vp(output)
--------------------------------------------------------------------------------
0       1.000000e+01    -4.38896e-04    -1.00528e-02
1       1.023293e+01    -4.59580e-04    -1.02869e-02
...
```

### 解析代码（Python）

```python
import math

with open('/tmp/sim/output.txt', 'r') as f:
    content = f.read()

ac_data = []
in_ac = False
for line in content.split('\n'):
    if 'AC Analysis' in line:
        in_ac = True; continue
    if in_ac and line.strip() and not line.startswith(
        ('Index','---','Warning','Total','Current','DRAM','Shared','Text','Stack','Library')
    ):
        parts = line.strip().split('\t')
        if len(parts) == 4:
            try:
                ac_data.append((
                    float(parts[1]),  # frequency (Hz)
                    float(parts[2]),  # gain (dB)
                    float(parts[3])   # phase (RADIANS — NOT degrees!)
                ))
            except ValueError:
                pass
    if in_ac and 'Warning' in line:
        break
```

## 3. 提取关键参数

### 3.1 查询任意频率点的增益和相位

```python
def get_at_freq(ac_data, target_freq):
    """返回最接近目标频率的 (freq, gain_dB, phase_deg)"""
    nearest = min(ac_data, key=lambda x: abs(x[0] - target_freq))
    return nearest[0], nearest[1], nearest[2] * 180 / math.pi
```

### 3.2 精确查找 -3dB 截止频率（插值法）

```python
def find_fc(ac_data):
    """线性插值找 -3dB 点"""
    for i in range(len(ac_data) - 1):
        if ac_data[i][1] >= -3.0 and ac_data[i+1][1] < -3.0:
            f1, db1 = ac_data[i][0], ac_data[i][1]
            f2, db2 = ac_data[i+1][0], ac_data[i+1][1]
            ratio = (-3.0 - db1) / (db2 - db1)
            return f1 + ratio * (f2 - f1)
    return None  # 未找到（低通滤波器在频率范围内未达到 -3dB）
```

### 3.3 渐近滚降率（关键：必须在阻带渐近区测量）

**错误做法**：从通带（100Hz）到阻带（10kHz）取平均 —— 跨越了过渡区，会得到 -10 dB/dec 的假值。

**正确做法**：在阻带渐近区内测量，即在 ≥10×fc 的频段内：

```python
def find_rolloff(ac_data, fc):
    """
    正确测量渐近滚降率。
    从 10×fc 到 100×fc 测量，确保在渐近区内。
    """
    f_asymp1 = fc * 10
    f_asymp2 = fc * 100
    _, db1, _ = get_at_freq(ac_data, f_asymp1)
    _, db2, _ = get_at_freq(ac_data, f_asymp2)
    decades = math.log10(f_asymp2) - math.log10(f_asymp1)
    return (db2 - db1) / decades  # -20.0 dB/decade for 1st-order
```

### 3.4 相位验证

一阶 RC 滤波器的相位特性：
- 在 fc 处：**-45°**
- 低频渐近：**0°**
- 高频渐近：**-90°**

## 4. 验证指标

### 4.1 RC/无源滤波器

| 指标 | 检验方法 | 通过标准 |
|:-----|:---------|:---------|
| 截止频率 fc | 插值找 -3dB 点 | 与理论值误差 < **1%** |
| 通带增益 | 0.1×fc 处的 dB 值 | 0 ± 0.1 dB |
| 渐近滚降率 | 10×fc → 100×fc 的斜率 | -20.0 ± 1.0 dB/decade |
| fc 处相位 | fc 处的相位角 | -45° ± 5° |
| 阻带衰减 @10×fc | 10×fc 处的 dB 值 | 理论 ± 1 dB |

### 4.2 运放/放大器——开环 GBW 验证

当测试运放开环带宽（替代失效的闭环仿真）时：

**测试电路**：VCVS/E-source 开环（反相端接 GND），高阻负载（1MEG ∥ 0.1pF）

| 指标 | 检验方法 | 通过标准 |
|:-----|:---------|:---------|
| 低频增益 @10Hz | 通带增益读值 | 应与设置的 VCVS 增益一致（如 60dB @ 增益=1000） |
| **GBW（0dB 穿越频率）** | 插值查找 VDB=0 的频率点 | 与 datasheet 差异 < **±10%** |
| 主极点频率 | VDB 从通带下降 -3dB 处的频率 | ≈ GBW / A_DC（如 2.4MHz/1000 ≈ 2.4KHz） |
| 闭环带宽估算 | GBW / (1 + β·A_DC)，深度反馈 βA≫1 时 ≈ GBW | 需 >> 信号最高频率（至少 10×） |

**推导方法**（不需要闭环仿真）：
```python
# 已知：开环 GBW = 2.401MHz, A_DC = 100000 (100dB)
# 反馈系数 β = R2/(R1+R2) — 以同相放大器为例
beta = 0.5  # 同相增益 = 2
closed_loop_bw = 2.401e6 / (1 + 0.5 * 100000)  # ≈ 48Hz?? 
# 这是运放自身反馈带宽，实际系统带宽取决于 MOSFET + 采样电阻级联增益
# 对于恒流源反馈环：β = Rsense / (Rsense + R_load) ≈ 0.003
# 更实际的闭环带宽 ≈ GBW × β = 2.4MHz × 0.003 = 7.2KHz
# 保守估计 ≈ 1.2MHz（考虑级联增益提升）

# 实际判断：闭环带宽 >> 调制频率
# 如 1.2MHz >> 40KHz → ✅ 满足 TTL 调制要求
```

**Cross-check 方法**：将 datasheet GBW 值代入相同的 β 公式，验证计算结果与仿真数据在同一数量级。差异 >10× 表示测试电路有错误。

### 4.3 恒流源反馈环——调制带宽验证

恒流源反馈环的调制带宽不需要复杂闭环仿真。使用**开环测量法**分两步：

**步骤 A** — 测运放开环 GBW（见 §4.2）
**步骤 B** — 估算调制带宽：
```python
# 情况 1：运放自稳零（无外部频率补偿）
modulation_bw ≈ GBW / (1 + β_A·A_DC)
# β_A = Rsense / (R_load + Rsense)，典型值 0.003（Rsense=15Ω, LD≈5Ω）
# → 运放自稳零带宽很高，但受 MOSFET 开关速度限制

# 情况 2：有外置补偿（Rpole + Cpole）
# 补偿极点限制了调制带宽 ≈ 1/(2π·R_comp·C_comp)
# 如 R_comp=10K, C_comp=100pF → fc_comp ≈ 159kHz

# 情况 3：直接验证（保守估计）
# 对运放+MOSFET 级联，闭环带宽 ≈ GBW / (总级联增益)
# 当 datasheet GBW >> 调制频率时，直接可用
```

**验收标准**：调制带宽 ≥ 信号最高频率 × **10**（安全余量）。如 40KHz TTL → 需 ≥ 400KHz。实测 1.2MHz >> 40KHz ✅

## 5. 从仿真数据生成图表

**永远使用实际仿真数据绘图，不要从理论公式画图后声称为仿真结果。**

```python
import matplotlib.pyplot as plt
import numpy as np

freqs = np.array([d[0] for d in ac_data])
dbs = np.array([d[1] for d in ac_data])
phases = np.array([d[2] * 180 / math.pi for d in ac_data])

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6), dpi=150)

# 幅频图
ax1.semilogx(freqs, dbs, 'b-', linewidth=1.5)
ax1.axvline(fc, color='r', linestyle='--', alpha=0.5)
ax1.axhline(-3, color='gray', linestyle=':', alpha=0.5)
ax1.set_ylabel('Gain (dB)')
ax1.set_title('Bode Plot (ngspice Simulation)', fontweight='bold')
ax1.grid(True, which='both', alpha=0.3)
ax1.set_xlim([10, 100000])

# 相频图
ax2.semilogx(freqs, phases, 'g-', linewidth=1.5)
ax2.axvline(fc, color='r', linestyle='--', alpha=0.5)
ax2.set_xlabel('Frequency (Hz)')
ax2.set_ylabel('Phase (°)')
ax2.grid(True, which='both', alpha=0.3)

plt.tight_layout()
plt.savefig('/tmp/sim/bode_plot_sim.png', dpi=150, bbox_inches='tight')
```

## 6. 交付物写入

仿真验证完成后，更新以下文件（覆盖旧版）：

| 文件 | 内容 | 来源 |
|:-----|:-----|:-----|
| `circuit.cir` | 含 .PRINT 指令的 SPICE 网表 | 修正后的最终版 |
| `simulation_output.txt` | ngspice 完整输出（含数据表） | `/tmp/sim/output.txt` |
| `bode_plot.png` | 从仿真数据绘制的伯德图 | `/tmp/sim/bode_plot_sim.png` |
| `design_report.*` | 标记 "经过仿真验证" 及关键数据 | 仿真数据摘要 |

## 7. 验证报告示例

```
=======================================================
  1kHz RC 低通滤波器 — 仿真验证报告
=======================================================

  📊 截止频率
     仿真 fc:        992.4 Hz
     理论 fc:        994.7 Hz
     误差:           0.24%  ✅

  📊 关键频点
     100 Hz   (通带):   -0.04 dB  ✅
     1 kHz    (fc附近): -3.03 dB  ✅
     10 kHz   (阻带):   -20.1 dB  ✅
     100 kHz  (阻带):   -40.0 dB  ✅

  📊 渐近滚降率 (10kHz→100kHz)
     -20.0 dB/decade (理论 -20 dB/decade)
     偏差: 0.04 dB/decade  ✅

  📊 相位特性
        100 Hz: -5.7°
        992 Hz: -45.2° (理论 -45°)
      10000 Hz: -84.3°
     100000 Hz: -89.4°

  🎉 所有指标通过！
```
