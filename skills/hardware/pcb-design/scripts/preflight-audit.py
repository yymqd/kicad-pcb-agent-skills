#!/usr/bin/env python3
"""Pre-flight audit for PCB design toolchain.
Run before any PCB design work. Exits with non-zero if any critical check fails.
"""
import subprocess
import sys
import os

checks = []
failures = []

def check(name, cmd, critical=True):
    checks.append(name)
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        ok = r.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        ok = False
        r = None

    if ok:
        print(f"  ✅ {name}")
    elif critical:
        print(f"  ❌ {name} — CRITICAL")
        failures.append(name)
    else:
        print(f"  ⚠️  {name} — WARNING (non-critical)")
    return ok

def check_python_import(module_name, name=None):
    name = name or f"python3 -c 'import {module_name}'"
    checks.append(name)
    try:
        r = subprocess.run(
            [sys.executable, "-c", f"import {module_name}"],
            capture_output=True, text=True, timeout=10
        )
        ok = r.returncode == 0
    except FileNotFoundError:
        ok = False

    if ok:
        print(f"  ✅ {name}")
    elif True:  # critical
        print(f"  ❌ {name} — CRITICAL")
        failures.append(name)
    else:
        print(f"  ⚠️  {name} — WARNING")
    return ok

def check_version(name, cmd, keyword=None):
    checks.append(name)
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        ok = r.returncode == 0
        if ok and keyword:
            ok = keyword in r.stdout or keyword in r.stderr
        if ok:
            output = r.stdout.strip() or r.stderr.strip()
            first_line = output.split('\n')[0][:80]
            print(f"  ✅ {name}: {first_line}")
        else:
            print(f"  ❌ {name} — not found")
            failures.append(name)
    except FileNotFoundError:
        print(f"  ❌ {name} — command not found")
        failures.append(name)

print("=" * 60)
print("PCB Design Pre-Flight Audit")
print("=" * 60)

# --- KiCad ---
print("\n📦 KiCad:")
check_version("kicad-cli", ["kicad-cli", "--version"])
check_python_import("pcbnew", "python3 import pcbnew")

# KiCad version check (7 vs 8+)
try:
    r = subprocess.run(["kicad-cli", "--version"], capture_output=True, text=True, timeout=5)
    ver = (r.stdout or r.stderr).strip()
    if "7." in ver:
        print("  ℹ️  KiCad 7 detected — load references/kicad7-pcbnew-api.md for API differences")
    elif "10." in ver:
        print(f"  ℹ️  KiCad 10 detected — current stable (2026-06)")
    else:
        print(f"  ℹ️  KiCad {ver} detected")
except:
    pass

# --- SPICE ---
print("\n🔬 SPICE:")
check_version("ngspice", ["ngspice", "-v"], keyword="ngspice")
check_python_import("PySpice", "python3 import PySpice")

# PySpice version
try:
    r = subprocess.run([sys.executable, "-c", "import PySpice; print(PySpice.__version__)"],
                       capture_output=True, text=True, timeout=5)
    if r.returncode == 0:
        print(f"  🟦 PySpice version: {r.stdout.strip()}")
except:
    pass

# --- Python deps ---
print("\n🐍 Python packages:")
check_python_import("sexpdata", "python3 import sexpdata")
check_python_import("uuid", "python3 import uuid")
check_python_import("numpy", "python3 import numpy")

# --- System ---
print("\n🖥️  System:")
# KiCad footprint libraries
for fp_path in ["/usr/share/kicad/footprints"]:
    if os.path.isdir(fp_path):
        n = len(os.listdir(fp_path))
        print(f"  ✅ KiCad footprints: {fp_path} ({n} files)")
    else:
        print(f"  ⚠️  Footprint path {fp_path} not found (non-critical)")

print()
print("=" * 60)
if failures:
    print(f"❌ AUDIT FAILED — {len(failures)} critical check(s):")
    for f in failures:
        print(f"   - {f}")
    print(f"\n   Total checks: {len(checks)}, Failed: {len(failures)}")
    sys.exit(1)
else:
    print(f"✅ AUDIT PASSED — all {len(checks)} checks OK")
    sys.exit(0)
