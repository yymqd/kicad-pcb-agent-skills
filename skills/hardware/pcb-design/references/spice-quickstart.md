# SPICE 仿真快速开始（2026-07-31 验证，520nm 激光驱动）

**直接跑 ngspice，不要折腾 KiCad GUI/原理图导出！**

## 验证过的流程

1. 用 WSL ngspice 45.2（与 KiCad 10 内置 ngspice.dll 同源）
2. `.control` + `wrdata out.csv v(x) v(y)` 导出数据（比 .PRINT 可靠）
3. wrdata 列格式：`[sweep, v(x), v(y), ...]`，解析时跳过首列
4. 运放用 gain=100 VCVS 无 clamp（不用 min/max 限幅）
5. TTL 开关验证用 `.DC VTTL 0 5`（比 TRAN 可靠，两态瞬间收敛）
6. 带宽用 datasheet GBW × 反馈系数计算，不依赖简化模型调参

## 不要做的事

- ❌ 不折腾 KiCad eeschema GUI 自动化画原理图（窗口 ref 漂移、act 协议复杂）
- ❌ 不折腾 kicad-cli 从原理图导网表（手写 .kicad_sch 极易格式错误）
- ❌ 不用 E-source `VALUE={min(max())}` 做 TRAN（导数不连续必崩）
- ❌ 不用高阻节点（100Meg）做 AC（ngspice 数值误差产生假第二极点）

## 验证过的网表模板（520nm 驱动，实验 1-5 全部通过）

```spice
* 第一行必须是注释！
.MODEL LED520 D(Is=1e-13 N=1.8 Rs=4.5 Vj=0.75)
VIN VIN 0 DC 5
VTTL TTL 0 DC 5
REN TTL EN 10k
RENPU EN 0 100k
EBOOST VOUT 0 VALUE={5.6*min(max((V(EN)-1.5)/0.1,0),1)}
RBOOST VOUT VIN 50
RSENSE VSNS 0 3.3
DLED VOUT LD_ANODE LED520
GMOS LD_ANODE VSNS GATE 0 VALUE={1.5*pow(max(V(GATE)-1.0,0),2)*min(max((V(LD_ANODE)-V(VSNS))/0.5,0),1)}
RDS LD_ANODE VSNS 1Meg
VCC VCC 0 DC 5
VREF_SRC VREF 0 DC 0.264
EOA GATE 0 VREF VSNS 100    ; gain=100 无 clamp
RGATE GATE 0 1Meg
CIN VIN 0 10u
COUT VOUT 0 22u
CBY VREF 0 0.1u
.control
dc vttl 0 5 0.5
wrdata out.csv v(ttl) v(en) v(vout) v(vsns)
.endc
.END
```

## 实验结果速查（520nm 驱动，全部通过）

| 实验 | 方法 | 结果 |
|---|---|---|
| DC 工作点 | .OP | 5.6V / 80mA ✅ |
| TTL 开关 | .DC VTTL 0 5 | 阈值 1.5-2.0V ✅ |
| 恒流线性度 | .DC VREF | 偏差 0.008% ✅ |
| VIN 抑制 | .DC VIN 4.5-5.5 | 波动 0% ✅ |
| LD Vf 稳定 | .OP 多次 | 偏差 0.005% ✅ |
| 调制带宽 | datasheet GBW | 452kHz, 11x 余量 ✅ |
