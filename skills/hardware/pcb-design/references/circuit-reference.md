# Circuit Reference（电路参考速查）

## Filter Formulas

| Type | fc |
|---|---|
| RC Low-Pass | 1/(2πRC) |
| RC High-Pass | 1/(2πRC) |
| Sallen-Key LP | 1/(2π√(R1R2C1C2)) |
| LC Resonant | 1/(2π√(LC)) |

## PCB Stackup

| Layers | Stack | Impedance |
|---|---|---|
| 2 | Sig-GND | No control |
| 4 | Sig-GND-GND-Sig | Stripline |
| 6 | Sig-GND-Sig-Sig-GND-Sig | Multi-stripline |

## GND 连通性验证

**每次完成走线后必须验证：**

```python
after = pcbnew.LoadBoard(pcb_path)
gnd_count = sum(1 for t in after.GetTracks()
                if t.GetNet() and t.GetNet().GetNetname() == 'GND')
gnd_pads = []
for fp in after.GetFootprints():
    for p in fp.Pads():
        if p.GetNet() and p.GetNet().GetNetname() == 'GND':
            gnd_pads.append(f'{fp.GetReference()}.{p.GetNumber()}')
if gnd_count == 0 and len(gnd_pads) > 0:
    raise RuntimeError(f'CRITICAL: {len(gnd_pads)} GND pads but NO GND tracks!')
```

## ngspice 相位数据单位陷阱

**`ngspice` 的 `VP()` 输出单位为弧度（radians），不是角度（degrees）。**

```python
# ❌ 错误：直接使用仿真输出值
phase_100hz = -0.1002  # 当作角度 → 报告写 -0.1°

# ✅ 正确：弧度转角度
import math
phase_100hz_deg = -0.1002 * 180 / math.pi  # = -5.74°
```

验证方法：在截止频率处，一阶 RC 滤波器的理论相位 = -45°。如果仿真显示相位接近 -0.8° 而非 -45°，说明未做弧度转换（-0.788 rad × 180/π = -45.15° ✅）。

| 频率 | 仿真值 (rad) | 正确值 (°) | 错误值 (°) |
|:----|:-----------:|:----------:|:----------:|
| 100 Hz | -0.1002 | -5.74 | -0.10 ❌ |
| 1 kHz | -0.7880 | -45.15 | -0.79 ❌ |
| 10 kHz | -1.4716 | -84.31 | -1.47 ❌ |

## KiCad 10 board.Save() API 说明

**2026-06-05 实测**（KiCad 10.0.3, Ubuntu 24.04 WSL）：`board.Save()` 输出 S-expression 使用字符串 net 名，6 个不同 net（含 GND、VOUT、VIN、GATE、VSNS）的复杂交叉场景实测**全部正确**——无 net 映射错乱问题。不需要后处理修复。
