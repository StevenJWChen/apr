#!/usr/bin/env python3
"""
Static Timing Analysis for ACC4 / demo130.

Reads:
  syn/netlist.v   – gate-level netlist
  pnr/routes.json – wire routes (for wire delay estimation)

Computes:
  * Critical path through combinational logic between flip-flops
  * Setup / hold slack
  * Maximum achievable clock frequency

Writes:
  sta/timing_report.txt
"""

import json, re, pathlib, sys

ROOT = pathlib.Path(__file__).parent.parent

# Cell propagation delays (ns) from cells.lib (scalar values)
CELL_DELAY = {
    "INV":0.08,"BUF":0.10,"NAND2":0.10,"NOR2":0.12,
    "AND2":0.13,"OR2":0.14,"XOR2":0.18,"XNOR2":0.18,
    "MUX2":0.15,"DFF":0.25,
}
SETUP_TIME  = 0.20   # ns
HOLD_TIME   = 0.05   # ns
CLK_PERIOD  = 10.0   # ns (100 MHz target)
WIRE_DELAY_PER_UM = 0.002  # ns/µm (RC approximation)

# ── Parse netlist for cells ───────────────────────────────────────────────────
def parse_cells(path):
    text = path.read_text()
    pat  = re.compile(r'\b(\w+)\s+(\w+)\s*\([^;]*?\)\s*;', re.S)
    cells = []
    for m in pat.finditer(text):
        ct = m.group(1)
        if ct in CELL_DELAY:
            cells.append({"type": ct, "name": m.group(2)})
    return cells

# ── Compute total wire delay from routes ──────────────────────────────────────
def total_wire_delay(routes_path):
    if not routes_path.exists():
        return 0.0
    routes = json.loads(routes_path.read_text())
    total_um = 0.0
    for segs in routes.values():
        for x1, y1, x2, y2 in segs:
            total_um += abs(x2-x1) + abs(y2-y1)
    return total_um * WIRE_DELAY_PER_UM

# ── Critical path estimation ──────────────────────────────────────────────────
def critical_path(cells, wire_delay_ns):
    """
    Simplified model:
      comb path = sum of non-DFF cell delays (worst-case chain).
      Actual critical path = clock-to-Q + comb + setup.
    """
    comb_cells = [c for c in cells if c["type"] != "DFF"]
    dffs        = [c for c in cells if c["type"] == "DFF"]

    # Worst-case: all comb cells in series (pessimistic)
    comb_delay = sum(CELL_DELAY[c["type"]] for c in comb_cells)
    # Add wire delay distributed across path
    comb_delay += wire_delay_ns * 0.7   # ~70% on comb paths

    clk2q = CELL_DELAY["DFF"]
    data_arrival = clk2q + comb_delay
    data_required = CLK_PERIOD - SETUP_TIME

    setup_slack = data_required - data_arrival
    hold_slack  = clk2q - HOLD_TIME     # simplified

    fmax = 1000.0 / (data_arrival + SETUP_TIME)   # MHz

    return {
        "comb_cells"       : len(comb_cells),
        "dff_count"        : len(dffs),
        "clk2q_ns"         : round(clk2q, 3),
        "comb_delay_ns"    : round(comb_delay, 3),
        "wire_delay_ns"    : round(wire_delay_ns, 3),
        "data_arrival_ns"  : round(data_arrival, 3),
        "data_required_ns" : round(data_required, 3),
        "setup_slack_ns"   : round(setup_slack, 3),
        "hold_slack_ns"    : round(hold_slack, 3),
        "fmax_mhz"         : round(fmax, 1),
    }

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    netlist = ROOT / "syn" / "netlist.v"
    routes  = ROOT / "pnr" / "routes.json"
    if not netlist.exists():
        sys.exit("ERROR: syn/netlist.v not found.")

    cells   = parse_cells(netlist)
    wdel    = total_wire_delay(routes)
    cp      = critical_path(cells, wdel)

    status_setup = "PASS" if cp["setup_slack_ns"] >= 0 else "FAIL"
    status_hold  = "PASS" if cp["hold_slack_ns"]  >= 0 else "FAIL"

    report = f"""Static Timing Analysis Report – ACC4 / demo130
{'='*52}
Clock period target : {CLK_PERIOD:.1f} ns  ({1000/CLK_PERIOD:.0f} MHz)

Cell inventory
  Combinational cells : {cp['comb_cells']}
  Flip-flops          : {cp['dff_count']}

Critical path breakdown
  Clock-to-Q delay    : {cp['clk2q_ns']:.3f} ns
  Combinational delay : {cp['comb_delay_ns']:.3f} ns
  Wire delay          : {cp['wire_delay_ns']:.3f} ns
  ─────────────────────────────────────────────
  Data arrival time   : {cp['data_arrival_ns']:.3f} ns
  Data required time  : {cp['data_required_ns']:.3f} ns

Slack
  Setup slack : {cp['setup_slack_ns']:+.3f} ns  → {status_setup}
  Hold slack  : {cp['hold_slack_ns']:+.3f} ns  → {status_hold}

Performance
  Achievable Fmax     : {cp['fmax_mhz']:.1f} MHz
{'='*52}
Overall STA status : {"PASS" if status_setup=="PASS" and status_hold=="PASS" else "FAIL"}
"""
    (ROOT / "sta" / "timing_report.txt").write_text(report)
    print(report)

if __name__ == "__main__":
    main()
