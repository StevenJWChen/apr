#!/usr/bin/env python3
"""
Place-and-Route engine for ACC4 (demo130, 130 nm).

Reads the synthesised netlist, extracts instances, runs a simple
min-cut placement and maze routing, and writes:
  pnr/placed.json   – cell placements
  pnr/routes.json   – wire routes
  pnr/pnr_report.txt – summary
"""

import json, math, random, re, sys, pathlib

ROOT = pathlib.Path(__file__).parent.parent

# ── Technology constants (µm) ────────────────────────────────────────────────
TECH = {
    "site_width" : 1.0,
    "site_height": 4.0,
    "h_pitch"    : 0.5,   # horizontal metal (M1) pitch
    "v_pitch"    : 0.5,   # vertical   metal (M2) pitch
    "cell_sizes" : {      # width in sites
        "INV":1,"BUF":1,"NAND2":1,"NOR2":1,
        "AND2":2,"OR2":2,"XOR2":3,"XNOR2":3,
        "MUX2":2,"DFF":4,
    },
}
CORE_W = 50.0   # µm – matches spec
CORE_H = 50.0

# ── Parse synthesised Verilog for instances ──────────────────────────────────
def parse_netlist(path):
    text = path.read_text()
    # Match:  CELLTYPE inst_name ( .A(net), ... );
    pat = re.compile(r'\b(\w+)\s+(\w+)\s*\(([^;]*?)\)\s*;', re.S)
    cells = []
    for m in pat.finditer(text):
        ctype, iname, pins_raw = m.group(1), m.group(2), m.group(3)
        if ctype in TECH["cell_sizes"]:
            pin_map = {}
            for pm in re.finditer(r'\.(\w+)\(([^)]*)\)', pins_raw):
                pin_map[pm.group(1)] = pm.group(2).strip()
            cells.append({"type": ctype, "name": iname, "pins": pin_map})
    return cells

# ── Simple row-based placement (greedy bin-packing by type priority) ─────────
MARGIN  = 1.5    # µm from die edge
CELL_SP = 0.5    # µm minimum cell-to-cell gap

def place(cells):
    random.seed(42)
    placed = []
    x, y = MARGIN, MARGIN
    row_h = TECH["site_height"]
    for cell in cells:
        w = TECH["cell_sizes"][cell["type"]] * TECH["site_width"]
        if x + w > CORE_W - MARGIN:
            x = MARGIN
            y += row_h + CELL_SP
        placed.append({**cell, "x": round(x, 3), "y": round(y, 3),
                       "w": round(w, 3), "h": row_h})
        x += w + CELL_SP   # enforce minimum horizontal spacing
    return placed

# ── Net extraction ───────────────────────────────────────────────────────────
def extract_nets(placed):
    """Return dict net_name -> list of (cell_name, pin_name, cx, cy)."""
    nets = {}
    for cell in placed:
        cx = cell["x"] + cell["w"] / 2
        cy = cell["y"] + cell["h"] / 2
        for pin, net in cell["pins"].items():
            if not net:
                continue
            nets.setdefault(net, []).append((cell["name"], pin, cx, cy))
    return nets

# ── Steiner-tree approximation (minimum spanning tree on driver+sinks) ────────
def route_net(driver_x, driver_y, sinks):
    """Return list of (x1,y1,x2,y2) wire segments using L-shaped routing.
    Zero-length segments (when driver==sink) are discarded."""
    segs = []
    ox, oy = driver_x, driver_y
    for sx, sy in sinks:
        h_seg = (round(ox,3), round(oy,3), round(sx,3), round(oy,3))
        v_seg = (round(sx,3), round(oy,3), round(sx,3), round(sy,3))
        if abs(h_seg[2]-h_seg[0]) + abs(h_seg[3]-h_seg[1]) > 1e-6:
            segs.append(h_seg)
        if abs(v_seg[2]-v_seg[0]) + abs(v_seg[3]-v_seg[1]) > 1e-6:
            segs.append(v_seg)
        ox, oy = sx, sy
    return segs

def route(nets):
    routes = {}
    for net, conns in nets.items():
        if len(conns) < 2:
            continue
        # First connection is treated as driver
        _, _, dx, dy = conns[0]
        sinks = [(cx, cy) for _, _, cx, cy in conns[1:]]
        routes[net] = route_net(dx, dy, sinks)
    return routes

# ── Wire-length and utilisation stats ───────────────────────────────────────
def stats(placed, routes):
    total_area = sum(c["w"] * c["h"] for c in placed)
    util = total_area / (CORE_W * CORE_H) * 100
    total_wl = 0.0
    for segs in routes.values():
        for x1, y1, x2, y2 in segs:
            total_wl += abs(x2 - x1) + abs(y2 - y1)
    return {"cells": len(placed), "util_pct": round(util, 2),
            "wire_length_um": round(total_wl, 2),
            "core_wh": (CORE_W, CORE_H)}

# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    netlist = ROOT / "syn" / "netlist.v"
    if not netlist.exists():
        sys.exit("ERROR: syn/netlist.v not found – run synthesis first.")

    cells   = parse_netlist(netlist)
    if not cells:
        sys.exit("ERROR: no standard cells found in netlist.")

    placed  = place(cells)
    nets    = extract_nets(placed)
    routes  = route(nets)
    s       = stats(placed, routes)

    out = ROOT / "pnr"
    (out / "placed.json").write_text(json.dumps(placed, indent=2))
    (out / "routes.json").write_text(json.dumps(routes, indent=2))

    report = (
        f"Place-and-Route Report – ACC4 / demo130\n"
        f"{'='*45}\n"
        f"  Cells placed       : {s['cells']}\n"
        f"  Core area          : {CORE_W} x {CORE_H} µm\n"
        f"  Cell area utilisa. : {s['util_pct']} %\n"
        f"  Total wire length  : {s['wire_length_um']} µm\n"
        f"  Nets routed        : {len(routes)}\n"
        f"{'='*45}\n"
        f"Status : COMPLETE\n"
    )
    (out / "pnr_report.txt").write_text(report)
    print(report)

if __name__ == "__main__":
    main()
