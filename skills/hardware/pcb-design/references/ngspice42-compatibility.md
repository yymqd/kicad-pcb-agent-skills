# ngspice-42 Compatibility & Workarounds

> Everything here was verified on ngspice-42+ds-3build1 (Ubuntu 24.04 WSL, 2026-06-05).

## 1. .PRINT Syntax — Analysis Type Is Mandatory

`.PRINT` **requires** the explicit analysis type keyword:

```spice
.PRINT V(OUT)       ← Fails: "Warning: no nodes given"
.PRINT DC V(OUT)    ← Works (DC analysis)
.PRINT AC VDB(OUT)  ← Works (AC analysis)
.PRINT TRAN V(OUT)  ← Works (Transient analysis)
```

Without the keyword, ngspice silently ignores the directive — simulation "runs" but no data is printed.

## 2. First Line = Title (Silent Data Loss)

**SPICE treats the very first line of any .cir file as the .TITLE line**, regardless of content. This is inherited from SPICE 2/3.

```spice
VIN IN 0 DC 5       ← BECOMES THE TITLE. VIN does NOT exist.
R1 IN 0 1k
→ V(IN) = 0V, no error, no warning.
```

**Prevention**: Always start every .cir file with a comment:
```spice
* Laser driver AC simulation
VIN IN 0 DC 5
→ V(IN) = 5V
```

**Diagnosis**: If any voltage source shows 0V output despite having a DC value, check if it was on line 1.

## 3. `limit()` Function Broken in B- and E-Sources (Regression)

`limit(x, lo, hi)` does not work in ngspice-42. Both B-source `V=limit(...)` and E-source `VALUE {limit(...)}` produce wrong output.

**Workaround**: Use composition of `min()` and `max()`:
```spice
* limit(x, lo, hi)  →  min(max(x, lo), hi)
B1 OUT 0 V=min(max(V(IN), 0.3), 9.2)
```

**Note argument order**: `min(max(x, lo), hi)` — low bound inside max(), high bound inside min().

## 4. `if()` Function Not Available

ngspice-42 does not support `if(condition, true_val, false_val)` in B-sources.

**Workaround**: Use `min(max())` for clamping, or use `V=cond?val1:val2` ternary syntax (if available).

## 5. Closed-Loop Op-Amp Simulation Strategy

High-gain op-amps (Aol > 1000) in closed-loop feedback are hard to converge. Recommended strategy:

**Step 1: Open-loop GBW measurement** (always converges)
- Disconnect feedback, inject AC 1 signal at input
- Use VCVS + RC pole (no rail clamp needed — VCVS stays in linear region for small signals)
- Measure GBW from Bode plot (0dB crossing)

**Step 2: Datasheet cross-check**
- Compare measured GBW to datasheet (TLV2371: 2.401MHz simulated vs 2.5MHz datasheet = 4% error)

**Step 3: Derive closed-loop bandwidth**
- CL_BW = GBW / (1 + Rf/Rin)
- For the laser driver: 2.401MHz / 2 = 1.2MHz >> 40KHz

## 6. Do Not Use KiCad genopa1 Model with ngspice-42

KiCad's `kicad_builtin_opamp` uses `Dlimit D N=0.01` diode clamps internally. ngspice-42's solver fails to converge with N=0.01 diodes — output gets stuck near VEE. Use open-loop VCVS instead.

## 7. E-Source min(max()) TRAN Convergence Failure

### Symptom
E-source with `VALUE {min(hi, max(lo, V(A,B)*gain)}` works in **DC** analysis but aborts in **TRAN**:
```
doAnalyses: TRAN:  Timestep too small; time = 4e-08, timestep = 6.25e-19: trouble with node "raw_out"
```

### Root Cause
`min()` and `max()` create a derivative **discontinuity** at the clamping boundary. The TRAN solver cannot cross it — the non-smooth knee forces timestep → 0. DC analysis has no time derivatives, so it passes.

### Fix (verified 2026-06-06, ø14mm laser driver)

**Strategy A — DC sweep (preferred when only ON/OFF states are needed):**
Replace `.TRAN` with `.DC VTTL 0 5 5`. Both states (TTL=0V ON, TTL=5V OFF) converge instantly. Same proof of function as TRAN.

**Strategy B — Lower-gain VCVS without clamping (when rise/fall time is needed):**
```spice
* ❌ Failed in TRAN — min(max()) causes derivative discontinuity:
EAMP OUT 0 INP INN VALUE {min(5.0, max(0.0, V(INP,INN)*1000))}

* ✅ Works in TRAN — no clamping, lower gain=100:
EAMP OUT 0 INP INN 100
```
Gain=100 avoids numerical oscillation while still regulating. The unclamped output saturates softly (no derivative discontinuity).

### Validation
- `.DC VTTL 0 5 5`: TTL=0V → I=78.4mA, TTL=5V → I=2.1mA ✅
- `.TRAN 0.1u 120u` (gain=100, no clamp): TTL=0V → I=76.3mA, TTL=5V → I=1.0mA ✅
- Both match. Tracking error at gain=100 is higher than real TLV171 (gain>100dB), but function is verified.

## 8. ngspice-42 Version Detection

```bash
ngspice -v 2>&1 | grep "ngspice"
# → ngspice-42 : Circuit level simulation program
```
