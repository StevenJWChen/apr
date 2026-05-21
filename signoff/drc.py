#!/usr/bin/env python3
"""
Design Rule Check (DRC) for ACC4 layout.

Reads pnr/placed.json and pnr/routes.json, checks:
  DRC-1  Cells outside core boundary
  DRC-2  Cell-to-cell spacing violation (< 0.5 µm)
  DRC-3  Wire outside core
  DRC-4  Wire width check (routes must have non-zero length)
  DRC-5  Minimum cell spacing from die edge (> 1 µm)
  DRC-6  Utilisation ceiling (≤ 80 %)

Writes signoff/drc_report.txt
"""

import json, pathlib, sys

ROOT = pathlib.Path(__file__).parent.parent
CORE_W, CORE_H = 50.0, 50.0
MIN_SPACING    = 0.5    # µm between cell bounding boxes
EDGE_MARGIN    = 1.0    # µm from die edge
MAX_UTIL       = 80.0   # %

def load(p):
    return json.loads(p.read_text())

def drc(placed, routes):
    violations = []

    total_area = 0.0
    for c in placed:
        x1, y1 = c["x"], c["y"]
        x2, y2 = x1 + c["w"], y1 + c["h"]
        total_area += c["w"] * c["h"]

        # DRC-1: outside core
        if x1 < 0 or y1 < 0 or x2 > CORE_W or y2 > CORE_H:
            violations.append(f"DRC-1  {c['name']} outside core ({x1:.2f},{y1:.2f}–{x2:.2f},{y2:.2f})")

        # DRC-5: edge margin
        if x1 < EDGE_MARGIN or y1 < EDGE_MARGIN or \
           x2 > CORE_W - EDGE_MARGIN or y2 > CORE_H - EDGE_MARGIN:
            violations.append(f"DRC-5  {c['name']} too close to die edge")

    # DRC-2: cell-cell spacing
    for i, a in enumerate(placed):
        for b in placed[i+1:]:
            ax1,ay1,ax2,ay2 = a["x"],a["y"],a["x"]+a["w"],a["y"]+a["h"]
            bx1,by1,bx2,by2 = b["x"],b["y"],b["x"]+b["w"],b["y"]+b["h"]
            gap_x = max(0.0, max(bx1-ax2, ax1-bx2))
            gap_y = max(0.0, max(by1-ay2, ay1-by2))
            if gap_x == 0 and gap_y < MIN_SPACING:
                violations.append(
                    f"DRC-2  spacing {gap_y:.3f} µm between {a['name']} and {b['name']} (min {MIN_SPACING})")

    # DRC-3 & DRC-4: wire checks
    for net, segs in routes.items():
        for x1,y1,x2,y2 in segs:
            length = abs(x2-x1) + abs(y2-y1)
            if length == 0:
                violations.append(f"DRC-4  zero-length wire segment on net {net}")
            for x,y in [(x1,y1),(x2,y2)]:
                if x < 0 or x > CORE_W or y < 0 or y > CORE_H:
                    violations.append(f"DRC-3  wire on net {net} outside core ({x:.2f},{y:.2f})")

    # DRC-6: utilisation
    util = total_area / (CORE_W * CORE_H) * 100
    if util > MAX_UTIL:
        violations.append(f"DRC-6  utilisation {util:.1f}% exceeds max {MAX_UTIL}%")

    return violations, util

def main():
    placed_p = ROOT / "pnr" / "placed.json"
    routes_p = ROOT / "pnr" / "routes.json"
    for p in (placed_p, routes_p):
        if not p.exists():
            sys.exit(f"ERROR: {p} not found – run PnR first.")

    placed  = load(placed_p)
    routes  = load(routes_p)
    viols, util = drc(placed, routes)

    status = "CLEAN" if not viols else f"{len(viols)} VIOLATIONS"
    lines  = [
        "DRC Report – ACC4 / demo130",
        "=" * 45,
        f"  Core           : {CORE_W} x {CORE_H} µm",
        f"  Cells checked  : {len(placed)}",
        f"  Nets checked   : {len(routes)}",
        f"  Utilisation    : {util:.2f} %",
        "-" * 45,
    ]
    if viols:
        lines += ["  Violations:"] + [f"    {v}" for v in viols]
    else:
        lines += ["  No violations found."]
    lines += ["=" * 45, f"DRC status : {status}"]
    report = "\n".join(lines) + "\n"

    (ROOT / "signoff" / "drc_report.txt").write_text(report)
    print(report)
    if viols:
        sys.exit(1)

if __name__ == "__main__":
    main()
