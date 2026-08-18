# PCB Design: Mandatory Supply Voltage Check

## Why This Matters

SPICE behavioral op-amp models (VCVS, B-source, E-source) have **no VCC/VEE
supply pins**. They can simulate a TLV2371 at 9.5V perfectly — GBW checks out,
Bode plot looks beautiful — but the real IC's absolute maximum rating is 5.5V.
The simulation passes; the real board smokes on power-up.

## The TLV2371 → TLV2171 Case (2026-06-05)

- Circuit: Laser diode driver, low-side current sink with op-amp
- Design flaw: TLV2371 (Vmax=5.5V) powered from Boost output (9.5V)
- SPICE: Passed with flying colors (behavioral VCVS has no supply pins)
- Design review (Phase 5a): Caught the violation
- Fix: Replaced with TLV2171 (same SOT-23-5 pinout, Vmax=16V)

## Required Procedure

Every IC in the design must pass:

```python
Vmax = datasheet_value  # Absolute maximum rating
Vrail = actual_supply_voltage_in_circuit
margin = (Vmax - Vrail) / Vmax * 100

assert Vrail <= Vmax, f"{ic}: {Vrail}V > {Vmax}V — WILL DAMAGE!"
assert margin >= 20, f"{ic}: only {margin:.0f}% margin — <20%, risk!"
```

## Protection Circuit Patterns

Add to every board with external connectors:

| Protection | Method | Example |
|------------|--------|---------|
| Reverse polarity | Schottky diode GND→Vin | D2 SS12 across output |
| ESD on inputs | 100pF NP0 → GND per line | CE1/CE2/CE3 on VIN/TTL/ANA |
| ESD on outputs | 100pF NP0 → GND | CE4 on BST output |
| Current limit | Fuse or e-fuse | — |
| Output over-voltage | TVS diode | — |

## 7-Dimension Design Review Checklist

Before calling a design complete, audit:

1. **Circuit topology** — Boost correct? Current sink correct? TTL logic correct?
2. **Component ratings** — Supply voltage, power dissipation, current capability
3. **Thermal** — Rsense P=I²R, MOSFET conduction, IC self-heating
4. **PCB layout** — Board size, mounting holes, component density, signal routing
5. **Selection** — Correct IC variant, package compatibility
6. **DFM** — Min trace width/spacing, via size, edge clearance
7. **Consistency** — BOM vs PCB vs report values match
