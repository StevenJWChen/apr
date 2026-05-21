#!/usr/bin/env python3
"""
Place-and-Route engine for RV32I core (demo130, 130 nm).

Reads syn/netlist_rv32i.v, places 7K+ cells in a 300x300 um core,
routes nets with L-shaped segments, and writes:
  pnr/placed_rv32i.json
  pnr/routes_rv32i.json
  pnr/pnr_rv32i_report.txt
"""

import json, re, sys, pathlib

ROOT = pathlib.Path(__file__).parent.parent

TECH = {
    "site_width" : 1.0,
    "site_height": 4.0,
    "h_pitch"    : 0.5,
    "v_pitch"    : 0.5,
    "cell_sizes" : {
        "INV":1,"BUF":1,"NAND2":1,"NOR2":1,
        "AND2":2,"OR2":2,"XOR2":3,"XNOR2":3,
        "MUX2":2,"DFF":4,
    },
}
CORE_W  = 300.0
CORE_H  = 300.0
MARGIN  = 2.0
CELL_SP = 0.5

def parse_netlist(path):
    text = path.read_text()
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

def place(cells):
    placed = []
    x, y   = MARGIN, MARGIN
    row_h  = TECH["site_height"]
    max_x  = CORE_W - MARGIN
    for cell in cells:
        w = TECH["cell_sizes"][cell["type"]] * TECH["site_width"]
        if x + w > max_x:
            x  = MARGIN
            y += row_h + CELL_SP
        placed.append({**cell, "x": round(x, 3), "y": round(y, 3),
                       "w": round(w, 3), "h": row_h})
        x += w + CELL_SP
    return placed

def extract_nets(placed):
    nets = {}
    for cell in placed:
        cx = cell["x"] + cell["w"] / 2
        cy = cell["y"] + cell["h"] / 2
        for pin, net in cell["pins"].items():
            if not net:
                continue
            nets.setdefault(net, []).append((cell["name"], pin, cx, cy))
    return nets

def route_net(driver_x, driver_y, sinks):
    segs = []
    ox, oy = driver_x, driver_y
    for sx, sy in sinks:
        h = (round(ox,3), round(oy,3), round(sx,3), round(oy,3))
        v = (round(sx,3), round(oy,3), round(sx,3), round(sy,3))
        if abs(h[2]-h[0]) + abs(h[3]-h[1]) > 1e-6:
            segs.append(h)
        if abs(v[2]-v[0]) + abs(v[3]-v[1]) > 1e-6:
            segs.append(v)
        ox, oy = sx, sy
    return segs

def route(nets):
    routes = {}
    for net, conns in nets.items():
        if len(conns) < 2:
            continue
        _, _, dx, dy = conns[0]
        sinks = [(cx, cy) for _, _, cx, cy in conns[1:]]
        routes[net] = route_net(dx, dy, sinks)
    return routes

def stats(placed, routes):
    total_area = sum(c["w"] * c["h"] for c in placed)
    util = total_area / (CORE_W * CORE_H) * 100
    total_wl = sum(
        abs(x2-x1) + abs(y2-y1)
        for segs in routes.values()
        for x1, y1, x2, y2 in segs
    )
    return {
        "cells"          : len(placed),
        "util_pct"       : round(util, 2),
        "wire_length_um" : round(total_wl, 2),
        "core_wh"        : (CORE_W, CORE_H),
        "nets_routed"    : len(routes),
    }

def main():
    netlist = ROOT / "syn" / "netlist_rv32i.v"
    if not netlist.exists():
        sys.exit("ERROR: syn/netlist_rv32i.v not found – run synthesis first.")

    print("Parsing netlist …")
    cells = parse_netlist(netlist)
    if not cells:
        sys.exit("ERROR: no standard cells found in netlist.")
    print(f"  {len(cells)} cells found.")

    print("Placing cells …")
    placed = place(cells)

    print("Extracting nets …")
    nets = extract_nets(placed)

    print(f"Routing {len(nets)} nets …")
    routes = route(nets)

    s = stats(placed, routes)

    out = ROOT / "pnr"
    (out / "placed_rv32i.json").write_text(json.dumps(placed, indent=2))
    (out / "routes_rv32i.json").write_text(json.dumps(routes, indent=2))

    report = (
        f"Place-and-Route Report – RV32I / demo130\n"
        f"{'='*45}\n"
        f"  Cells placed       : {s['cells']}\n"
        f"  Core area          : {CORE_W} x {CORE_H} µm\n"
        f"  Cell area utilisa. : {s['util_pct']} %\n"
        f"  Total wire length  : {s['wire_length_um']} µm\n"
        f"  Nets routed        : {s['nets_routed']}\n"
        f"{'='*45}\n"
        f"Status : COMPLETE\n"
    )
    (out / "pnr_rv32i_report.txt").write_text(report)
    print(report)

if __name__ == "__main__":
    main()
