#!/usr/bin/env python3
"""
IC Design Flow Master Script – ACC4
====================================
Runs the complete flow:
  Step 1  RTL simulation      (iverilog + vvp)
  Step 2  Synthesis           (yosys)
  Step 3  Gate-level sim      (iverilog + vvp)
  Step 4  Place-and-Route     (pnr/pnr.py)
  Step 5  Static Timing       (sta/sta.py)
  Step 6  DRC                 (signoff/drc.py)
  Step 7  LVS                 (signoff/lvs.py)
  Step 8  GDS export          (gds/gds_export.py)

Usage:
  python3 flow.py [--from <step>] [--to <step>]
"""

import argparse, subprocess, sys, pathlib, time, os

ROOT = pathlib.Path(__file__).parent
os.chdir(ROOT)

GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

def banner(msg):
    print(f"\n{BOLD}{'─'*60}{RESET}")
    print(f"{BOLD}  {msg}{RESET}")
    print(f"{BOLD}{'─'*60}{RESET}")

def run(cmd, desc, log_file=None, **kwargs):
    banner(desc)
    print(f"  $ {' '.join(cmd)}\n")
    t0 = time.time()
    r  = subprocess.run(cmd, text=True, capture_output=False, **kwargs)
    dt = time.time() - t0
    ok = r.returncode == 0
    color = GREEN if ok else RED
    tag   = "PASS" if ok else "FAIL"
    print(f"\n  {color}[{tag}]{RESET}  elapsed {dt:.1f}s")
    if not ok:
        sys.exit(f"\nFlow aborted at: {desc}")
    return r

STEPS = [
    {
        "id": 1, "name": "RTL Simulation",
        "fn": lambda: (
            pathlib.Path("sim").mkdir(exist_ok=True),
            run(["iverilog", "-o", "sim/rtl_sim", "-g2012",
                 "rtl/tb_acc4.v", "rtl/acc4.v"],
                "1/8  RTL Simulation – compile"),
            run(["vvp", "sim/rtl_sim"],
                "1/8  RTL Simulation – run"),
        )
    },
    {
        "id": 2, "name": "Synthesis",
        "fn": lambda: run(
            ["yosys", "-s", "syn/synth.tcl"],
            "2/8  Synthesis (Yosys)"
        )
    },
    {
        "id": 3, "name": "Gate-level Simulation",
        "fn": lambda: (
            run(["iverilog", "-o", "sim/gl_sim", "-g2012",
                 "-I", "syn",
                 "rtl/tb_acc4.v", "syn/netlist.v", "syn/cells_sim.v"],
                "3/8  Gate-level Simulation – compile"),
            run(["vvp", "sim/gl_sim"],
                "3/8  Gate-level Simulation – run"),
        )
    },
    {
        "id": 4, "name": "Place-and-Route",
        "fn": lambda: run(
            ["python3", "pnr/pnr.py"],
            "4/8  Place-and-Route"
        )
    },
    {
        "id": 5, "name": "Static Timing Analysis",
        "fn": lambda: run(
            ["python3", "sta/sta.py"],
            "5/8  Static Timing Analysis"
        )
    },
    {
        "id": 6, "name": "DRC",
        "fn": lambda: run(
            ["python3", "signoff/drc.py"],
            "6/8  Design Rule Check (DRC)"
        )
    },
    {
        "id": 7, "name": "LVS",
        "fn": lambda: run(
            ["python3", "signoff/lvs.py"],
            "7/8  Layout vs. Schematic (LVS)"
        )
    },
    {
        "id": 8, "name": "GDS Export",
        "fn": lambda: run(
            ["python3", "gds/gds_export.py"],
            "8/8  GDSII Export"
        )
    },
]

def main():
    p = argparse.ArgumentParser(description="ACC4 IC design flow")
    p.add_argument("--from", dest="from_step", type=int, default=1,
                   help="Start from step N (1–8)")
    p.add_argument("--to",   dest="to_step",   type=int, default=8,
                   help="Stop after step N (1–8)")
    args = p.parse_args()

    print(f"\n{BOLD}ACC4 IC Design Flow  –  demo130 130nm{RESET}")
    print(f"Steps {args.from_step} – {args.to_step}\n")

    t_total = time.time()
    results = []
    for step in STEPS:
        if step["id"] < args.from_step:
            continue
        if step["id"] > args.to_step:
            break
        step["fn"]()
        results.append((step["id"], step["name"], "PASS"))

    dt = time.time() - t_total
    print(f"\n{BOLD}{'='*60}{RESET}")
    print(f"{BOLD}  FLOW COMPLETE  –  {dt:.1f}s total{RESET}")
    print(f"{BOLD}{'='*60}{RESET}")
    for sid, sname, status in results:
        color = GREEN if status == "PASS" else RED
        print(f"  Step {sid}  {sname:<30} {color}{status}{RESET}")

    print(f"\n{BOLD}Artefacts:{RESET}")
    for path in [
        "sim/rtl_sim.vcd", "syn/netlist.v", "syn/area_report.txt",
        "pnr/placed.json", "pnr/pnr_report.txt",
        "sta/timing_report.txt",
        "signoff/drc_report.txt", "signoff/lvs_report.txt",
        "gds/acc4.gds",
    ]:
        p_obj = ROOT / path
        mark  = GREEN+"✓"+RESET if p_obj.exists() else RED+"✗"+RESET
        size  = f"({p_obj.stat().st_size//1024+1} KB)" if p_obj.exists() else ""
        print(f"  {mark}  {path}  {size}")

if __name__ == "__main__":
    main()
