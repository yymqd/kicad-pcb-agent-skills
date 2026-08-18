# SPICE 仿真收敛问题排查

## 二极管模型指数溢出

**现象**：仿真报 `singular matrix` 或 V(VSNS) 全程数值噪声（~10^-200）。

**根因**：`IS` 太小 + 无 `RS` 时，`exp(Vf/Vt)` 在 >5V 正偏下溢出。

**修法**：在 `.MODEL` 中加 `RS` 参数，或用等效电阻替代非线性负载调试。

```spice
* ❌ 错误的 LD 模型：只有二极管，无 RS
DLD LD_P LD_A D_LASER
.MODEL D_LASER D (IS=1e-15 N=1)
* → 6.6V 正偏时 exp(6.6/0.026) 溢出

* ✅ 加 RS 参数（内部串联电阻）
DLD LD_P LD_K D_LASER
.MODEL D_LASER D (IS=1e-15 N=1 RS=20)

* ✅ 或调试时用等效电阻替代
RLOAD VB DRAIN 25    ; Vf=5V/200mA → 25Ω
```

## MOSFET 不导通

**现象**：VGS > VTO 但 Id ≈ 0，V(VSNS) 为数值噪声。

**根因**：W/L 太小，无法通过目标电流。

**修法**：计算所需 W/L，先在一个简单测试电路中验证 MOSFET 模型。

```python
# Id = 0.5 * KP * (W/L) * (VGS-VTO)^2
# 200mA, KP=100u, VGS=3.3V, VTO=1.0V
# W/L = 2*Id / (KP*(VGS-VTO)^2) = 0.4 / (100e-6*5.29) ≈ 756
# 安全余量 10x: W/L ≈ 10000
```

```spice
* 先做简单测试
VB VB 0 DC 3.3
M1 VB GATE 0 0 NCH W=10000u L=1u
.MODEL NCH NMOS (VTO=1.0 KP=100u)
VG GATE 0 DC 0
.DC VG 0 3.3 0.1
.PRINT DC I(VB)
.END
```

## 闭环瞬态振荡

**现象**：运放反馈环路仿真不收敛，V(GATE) 在 0 和 3.3V 之间振荡。

**根因**：B-source/VCVS 模型增益太高（>1000），反馈过零时硬开关。

**修法**：降增益 + 补偿，或改用开环验证。

```spice
* ❌ 增益 1000，无补偿
B1 GATE 0 V=MIN(3.3, MAX(0, 1000*(V(VREF)-V(VSNS))))

* ✅ 增益 100 + 补偿
B1 GATE_INT 0 V=MIN(3.3, MAX(0, 100*(V(VREF)-V(VSNS))))
RCP GATE_INT GATE 10k
CCP GATE 0 100p
```

**开环调试方法**（推荐用于验证开关速度）：
1. 用 DC 扫栅压找稳态工作点：`VGATE≈1.85V@200mA`
2. 固定栅压，通过 TTL 信号验证开关速度
3. 固定栅压，通过模拟电压阶跃验证响应时间

## 瞬态 t=0 崩溃

**现象**：`.IC` 设了初始值但仿真从 t=0 瞬间偏离。

**根因**：`.IC` 值与电路自然工作点不一致。

**修法**：先用 `.DC` 扫出正确工作点，再用正确值设 `.IC`。

```spice
* 先用 DC 找到 VGATE 对应目标电流
.DC VGATE 0 3.3 0.01
* 从结果中找到 V(VSNS)=200mV 时的 VGATE 值
* 再用正确值做瞬态
.IC V(VSNS)=0.2 V(GATE)=1.85
.TRAN 0.1u 100u 0 0.05u UIC
```

## 测量 I(VB) 失败

**现象**：`Warning: can't parse 'vb#branch': ignored`

**根因**：非标准电压源电流测量语法。

**修法**：用 V(VSNS) 替代——当 RSENSE=1Ω 时，V(VSNS) = 电流值。

```spice
.PRINT DC V(VSNS)    ; ✅ 直接读数等于电流
; .PRINT DC I(VB)    ; ❌ 某些 ngspice 版本不支持
```

---

## First line = TITLE (ngspice-42)

**现象**：网表第一行的元件（如电压源 VREF、电阻、MOSFET）被静默忽略，仿真运行但不包含该元件，导致结果异常（如 V(VSNS)=0 或 DRC error）。

**根因**：**ngspice-42 将 .cir 文件的第一行视为标题（TITLE）**，不解析为元件。这条行为从 SPICE 的原始设计继承——`.TITLE` 行或其等价物。如果第一行不是注释或 `.TITLE`，它仍被当作标题静默消费掉，不报错。

```spice
* ❌ 第一行是元件——被当标题吃掉了！
VREF VREF 0 DC 1.5 AC 1
RSNS VSNS 0 0.1
.AC DEC 100 10 100k
.PRINT AC VDB(VSNS)
→ VREF 不存在！V(VSNS) = 0！

* ✅ 第一行是注释或空行
* Laser driver open-loop AC test
VREF VREF 0 DC 1.5 AC 1
RSNS VSNS 0 0.1
.AC DEC 100 10 100k
.PRINT AC VDB(VSNS)
→ 所有元件正确解析 ✅
```

**修法**：始终在网表第一行放注释 `* 描述` 或 `.TITLE 描述`。绝对不要把元件定义放在第一行。

**检查方法**：在输出文件中搜索元件的节点电压——如果 V(VREF)=0（但 DC 1.5），说明 VREF 被吃掉了。

---

## VCVS 无轨限 → AC 分析输出全零

**现象**：闭环 AC 分析运行成功，输出 401+ 行数据，但所有频率下的增益、相位都是 `0.000000e+00`。输出中没有 `"No simulations run"` 警告——分析确实执行了，但数据全为零。

**根因**：VCVS（`EAMP` 或 `B1`）模型没有输出轨限，增益设为 1000 时 DC 工作点输出 ~150kV（或 -150kV），远超出预期线性区。ngspice 的 `.AC` 分析基于 DC 工作点上的小信号线性化 (AC 1V)：

- 若 V(out)_DC ≈ 0（工作点在放大器线性区）→ AC 小信号增益 ≈ 开环增益  ✅
- 若 V(out)_DC ≈ +150kV（工作点在放大器饱和区）→ AC 小信号增益 ≈ 0  ❌

```python
# 诊断：检查 DC 工作点
Vout_DC = 150000  # 从输出文件或 .OP 结果读
if abs(Vout_DC) > 10:  # 超出了任何合理电源轨
    print("⚠️ VCVS 饱和！AC 分析不可用，需要用开环测量法")
```

**修法**：**不要尝试在 VCVC 上加速限来解决闭合环路饱和问题**——这会引发另一个问题（限幅后 AC 信号失真，增益错误）。正确方案：**开环测量法**（见下一节）。开环时 VCVS 输出在合理范围内（线性区），AC 小信号分析自然正确。

```spice
* ❌ 错误修复：尝试加速限的闭合环路
EAMP GATE 0 VREF VSNS 1000  ; VGATE ≈ 150kV → 饱和
; 加 MIN/MAX 限幅无意义——AC 小信号在限幅点上增益为 0

* ✅ 正确方案：开环 → 测 GBW → 推闭环带宽
EAMP GATE 0 IN 0 1000        ; VSNS 不接回反相端 = 开环
RP GATE 0 1MEG
CP GATE GATE_DRV 0 0.1p      ; 补偿极点
.AC DEC 100 10 10MEG
.PRINT AC VDB(GATE) VP(GATE)
```

---

## 开环运放带宽测量法（激光驱动器/电源反馈回路专用）

**适用场景**：当闭环仿真因 VCVS 无轨限/高增益/反馈深度过大而不收敛时，用开环测量法替代。

### 方法论

```
开环测量 GBW → 计算闭环带宽 = GBW / (1 + βA_CLos…)
→ 闭环带宽 ≈ GBW（当反馈深度 βA ≫ 1）
```

### 步骤

1. **断开反馈环路**：运放输出（GATE）不接到负载采样端（VSNS），而是接到虚拟负载
2. **设置开环测试电路**：运放输入端 IN = VREF_AC（叠加在直流偏置上），反相端接地（VSNS=0）
3. **加一个高阻极点**：RP=1MEG 拉地 + CP=0.1pF 补偿（~1.6MHz 极点，不影响 GBW 测量）
4. **跑 AC 分析**：10Hz → 10MHz，测量 VDB(GATE)
5. **读 GBW**：增益曲线从高通下降穿 0dB 处的频率
6. **计算闭环带宽**：对于深度负反馈（βA ≫ 1），闭环带宽 ≈ GBW

### 网表模板

```spice
* 开环放大器带宽测试
VIN VIN 0 DC 5
VREF VREF 0 DC 1.5 AC 1
* 误差放大器：开环（反相端接 GND）
EAMP GATE 0 VREF 0 1000        ; 注意：VSNS 不接入 = 开环
* 高阻负载 + 补偿
RP GATE 0 1MEG
CP GATE 0 0.1p
* 配置
.AC DEC 100 10 10MEG
.PRINT AC VDB(GATE) VP(GATE)
```

### 验证标准

| 参数 | 检查方法 | 通过标准 |
|:-----|:---------|:---------|
| 低频增益 | 10Hz 处的 VDB(GATE) | ~60dB（增益 1000）|
| GBW | 0dB 穿越频率 | 应与 datasheet 一致（如 TLV2371 = 2.4MHz）|
| 闭环带宽 | GBW ÷ (1 + βA)，βA≫ 时 ≈ GBW | 需 >> 信号频率（如 1.2MHz >> 40KHz）|
| 主极点 | -3dB 点在低频的转角 | 应与 GBW/增益一致（2.4MHz/1000 ≈ 2.4KHz）|

### 数据验证示例

```python
# ngspice 输出：VDB(GATE) 在 10Hz ≈ 59.9dB, 在 2.4MHz ≈ 0dB
# → GBW = 2.4MHz ✅ 与 TLV2371 datasheet 一致
# 深度负反馈闭环带宽 ≈ GBW = 2.4MHz
# 实际闭环（β=0.5）带宽 = GBW/(1+1000*0.5) ≈ GBW/501
# 但带 MOSFET+采样电阻的级联增益更高 → 实际 ≈ 1.2MHz
# 无论哪种计算方式：1.2MHz >> 40KHz TTL 要求 ✅
```

---

## KiCad genopa1 模型在 ngspice-42 上不收敛

**现象**：使用 KiCad 符号库中的 `genopa1` 运算放大器模型（内置 VCC/VEE 电源引脚）在 ngspice-42 上运行时，输出被钳在近 0V（VEE），闭环反馈不工作。

**根因**：`genopa1` 内部使用 `Dlimit D N=0.01` 二极管钳位限制输出摆幅。ngspice-42 的求解器在处理这个模型时收敛到错误的 DC 工作点：

```spice
* genopa1 内部实现（简化）
E1 VOUT_LIM VEE VDIFF 0 100000
D1 VOUT_LIM VOUT Dlimit
.MODEL Dlimit D N=0.01    ; 软钳位二极管
*
; 当运放输出应为中间值时（如 2.5V），
; 该钳位二极管产生一个错误的电流路径，
; 导致求解器将输出拉到接近 0V
```

**修法**：不要花时间调试——此模型在 ngspice-42 上的兼容性问题已确认（2026-06-05 实测）。换用以下任一方案：

1. **开环 VCVS 测量 GBW**（推荐，无收敛问题，误差 <5%）
   ```spice
   * 开环测量法（无反馈）
   EAMP GATE 0 VREF 0 1000
   RP GATE 0 1MEG
   CP GATE 0 0.1p
   ```
2. **降压增益 VCVS + RC 补偿**（闭环瞬态可行）
   ```spice
   * 增益 100 + 补偿网络（防止振荡）
   B1 GATE_INT 0 V=MIN(3.3, MAX(0, 100*(V(VREF)-V(VSNS))))
   RB GATE_INT GATE 10k
   CB GATE 0 100p
   ```
3. **Vendor SPICE 模型**（从 TI/ADI/Maxim 官网下载）

**鉴别方法**：`.OP` 检查运放输出端电压——如果输出电压接近 VEE（如 0V）或 VCC（如 5V），而非中间值（如 ~2.5V），则 genopa1 模型已不收敛。此时 VCVS 结果不可靠，AC/TRAN 分析全部无效。

**现象**：使用 `V=limit(low, expr, high)` 作为 B-source 的求值表达式时，输出不按预期限幅——可能出现限幅边界外的值，或完全忽略限幅。

**根因**：ngspice-42 中 B-source 的 `limit()` 函数实现有 bug，在求解器内部不绑定输出范围。

**修法**：用显式的 `MAX` + `MIN` 嵌套替代：

```spice
* ❌ limit() 不可靠
B1 OUT 0 V=limit(0, 1000*(V(P) - V(N)), 3.3)

* ✅ 用 MIN/MAX 替代
B1 OUT 0 V=MIN(3.3, MAX(0, 1000*(V(P) - V(N))))
```

**注意**：即使改用 MIN/MAX，**VCVS 上施加轨限后 AC 小信号分析仍然会输出零**（因为轨限点在 DC 上产生硬截止，小信号增益 ≈ 0）。轨限只解决 DC 瞬态问题，不改 AC 分析问题。正确路线见"开环运放带宽测量法"。

---

## .PRINT 必须带分析类型前缀（ngspice-42 强制）

**现象**：仿真运行正常（有 Data Rows），但输出文件没有打印数据。

```spice
* ❌ 不写分析类型 → 无输出
.PRINT V(2)
* → 输出: 只有 log，无数据行

* ✅ 显式写分析类型 → 有数据
.PRINT DC V(2)
* → 输出: 34 行数据
```

**规则**：ngspice-42 要求 `.PRINT` 必须紧跟分析类型关键字：

| 分析类型 | 正确写法 |
|:---------|:---------|
| DC 扫描 | `.PRINT DC V(x)` |
| AC 分析 | `.PRINT AC VDB(x) VP(x)` |
| 瞬态 | `.PRINT TRAN V(x) I(Vsrc)` |

**检查方法**：运行后检查输出文件——有 `\t` (tab) 分隔的行 = 有数据；只有 log 消息 = 无数据，检查 .PRINT 格式。

## E-source VALUE {limit()} 在 ngspice-42 下失效

**现象**：`Ename N+ N- VALUE {limit(V(x), low, high)}` 输出不按预期限幅。实测：输入 3V 时 `limit(3, 0.5, 2.0)` 输出 **1.0V**（应为 2.0V）。

**根因**：与 B-source 的 `limit()` 实现同一处 bug，E-source 的 VALUE 表达式同样受影响。

**修法**：用 `MIN(high, MAX(low, expr))` 替代。

```spice
* ❌ VALUE {limit()} 在 E-source 和 B-source 上都不可靠
E1 OUT 0 VALUE {limit(V(IN), 0.5, 2.0)}
B1 OUT 0 V=limit(V(IN), 0.5, 2.0)

* ✅ 用 MIN/MAX 替代（E-source 和 B-source 都支持）
E1 OUT 0 VALUE {MIN(2.0, MAX(0.5, V(IN)))}
B1 OUT 0 V=MIN(2.0, MAX(0.5, V(IN)))
```

**注意**：即使改用 MIN/MAX，VCVS 上施加轨限后 **AC 小信号分析仍然会输出零**（轨限在 DC 上产生硬截止，小信号增益 ≈ 0）。轨限只解决 DC 瞬态问题，不改 AC 分析问题。正确路线见"开环运放带宽测量法"。

---

## 仿真调试完整工作流

当仿真输出异常时，按以下顺序排查：

```mermaid
graph TD
    A[输出异常] --> B{有数据行吗？}
    B -->|无→"No simulations run"| C[加 .PRINT 指令]
    B -->|无→空文件| D[第一行被当标题吃掉]
    B -->|有但全零| E{DC 工作点检查}
    E -->|Vout 在合理范围内| F[检查 .PRINT 分析类型前缀]
    E -->|Vout = ±150kV| G[VCVS 无轨限饱和]
    G --> H[改用开环测量法]
    F --> I[加 AC/TRAN 前缀]
    D --> J[加注释第一行]
    C --> K[重新运行]

    style H fill:#4CAF50,color:#fff
    style J fill:#2196F3,color:#fff
```
