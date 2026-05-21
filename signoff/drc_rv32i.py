#!/usr/bin/env python3
"""
Design Rule Check for RV32I layout (demo130, 130 nm).

Reads pnr/placed_rv32i.json and pnr/routes_rv32i.json, checks:
  DRC-1  Cells outside core boundary
  DRC-2  Cell-to-cell spacing (adjacent cells in same row, O(n))
  DRC-3  Wire outside core
  DRC-4  Zero-length wire segments
  DRC-5  Minimum cell spacing from die edge
  DRC-6  Utilisation ceiling (<=80%)

Writes signoff/drc_rv32i_report.txt
"""

import json, pathlib, sys

ROOT = pathlib.Path(__file__).parent.parent
CORE_W, CORE_H = 300.0, 300.0
MIN_SPACING    = 0.5
EDGE_MARGIN    = 1.0
MAX_UTIL       = 80.0
ROW_H          = 4.0

def load(p):
    return json.loads(p.read_text())

def drc(placed, routes):
    violations = []
    total_area = 0.0

    # DRC-1 and DRC-5: per-cell boundary checks
    for c in placed:
        x1, y1 = c["x"], c["y"]
        x2, y2 = x1 + c["w"], y1 + c["h"]
        total_area += c["w"] * c["h"]
        if x1 < 0 or y1 < 0 or x2 > CORE_W or y2 > CORE_H:
            violations.append(f"DRC-1  {c['name']} outside core")
        if x1 < EDGE_MARGIN or y1 < EDGE_MARGIN or \
           x2 > CORE_W - EDGE_MARGIN or y2 > CORE_H - EDGE_MARGIN:
            violations.append(f"DRC-5  {c['name']} too close to die edge")

    # DRC-2: cell-to-cell spacing – O(n) by checking only row-neighbours.
    # Cells placed in left-to-right row order; adjacent pairs share the same row.
    for i in range(len(placed) - 1):
        a, b = placed[i], placed[i+1]
        if abs(a["y"] - b["y"]) < 1e-6:   # same row
            gap = b["x"] - (a["x"] + a["w"])
            if gap < MIN_SPACING - 1e-9:
                violations.append(
                    f"DRC-2  gap {gap:.3f} µm between {a['name']} and {b['name']} "
                    f"(min {MIN_SPACING})")

    # DRC-3 & DRC-4: wire checks
    for net, segs in routes.items():
        for x1, y1, x2, y2 in segs:
            length = abs(x2-x1) + abs(y2-y1)
            if length == 0:
                violations.append(f"DRC-4  zero-length segment on net {net}")
            for x, y in [(x1, y1), (x2, y2)]:
                if x < 0 or x > CORE_W or y < 0 or y > CORE_H:
                    violations.append(f"DRC-3  wire on {net} outside core ({x:.2f},{y:.2f})")

    # DRC-6: utilisation
    util = total_area / (CORE_W * CORE_H) * 100
    if util > MAX_UTIL:
        violations.append(f"DRC-6  utilisation {util:.1f}% exceeds max {MAX_UTIL}%")

    return violations, util

def main():
    placed_p = ROOT / "pnr" / "placed_rv32i.json"
    routes_p = ROOT / "pnr" / "routes_rv32i.json"
    for p in (placed_p, routes_p):
        if not p.exists():
            sys.exit(f"ERROR: {p} not found – run PnR first.")

    placed = load(placed_p)
    routes = load(routes_p)
    viols, util = drc(placed, routes)

    status = "CLEAN" if not viols else f"{len(viols)} VIOLATIONS"
    lines  = [
        "DRC Report – RV32I / demo130",
        "=" * 45,
        f"  Core           : {CORE_W} x {CORE_H} µm",
        f"  Cells checked  : {len(placed)}",
        f"  Nets checked   : {len(routes)}",
        f"  Utilisation    : {util:.2f} %",
        "-" * 45,
    ]
    if viols:
        lines += ["  Violations:"] + [f"    {v}" for v in viols[:20]]
        if len(viols) > 20:
            lines.append(f"    ... ({len(viols)-20} more violations not shown)")
    else:
        lines += ["  No violations found."]
    lines += ["=" * 45, f"DRC status : {status}"]
    report = "\n".join(lines) + "\n"

    (ROOT / "signoff" / "drc_rv32i_report.txt").write_text(report)
    print(report)
    if viols:
        sys.exit(1)

if __name__ == "__main__":
    main()
