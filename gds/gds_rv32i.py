#!/usr/bin/env python3
"""
GDSII export for RV32I core / demo130.

Reads pnr/placed_rv32i.json and pnr/routes_rv32i.json and writes
gds/rv32i.gds using the gdstk library.

For 7K+ cells, instance geometry is shared via gdstk.Reference cells
and per-cell instance labels are omitted to keep file size manageable.
"""

import json, pathlib, sys
import gdstk

ROOT = pathlib.Path(__file__).parent.parent

LYR = {
    "nwell"  : (1, 0),
    "active" : (2, 0),
    "poly"   : (3, 0),
    "contact": (4, 0),
    "m1"     : (5, 0),
    "via1"   : (6, 0),
    "m2"     : (7, 0),
    "m3"     : (8, 0),
    "text"   : (64, 0),
}

CORE_W, CORE_H = 300.0, 300.0
WIRE_W = 0.3

def make_cell_geometry(lib, ctype, width, height):
    cell = lib.new_cell(f"SC_{ctype}_{int(width*10)}x{int(height*10)}")
    nw_h = height * 0.55
    cell.add(gdstk.rectangle((0, height - nw_h), (width, height), *LYR["nwell"]))
    aw = width * 0.7
    cell.add(gdstk.rectangle((width*0.15, height*0.60), (width*0.15+aw, height*0.85), *LYR["active"]))
    cell.add(gdstk.rectangle((width*0.15, height*0.15), (width*0.15+aw, height*0.40), *LYR["active"]))
    n_gates = max(1, len(ctype) // 3)
    gate_pitch = width / (n_gates + 1)
    for i in range(n_gates):
        gx = gate_pitch * (i + 1)
        cell.add(gdstk.rectangle((gx-0.05, height*0.10), (gx+0.05, height*0.90), *LYR["poly"]))
    for cy in [height*0.25, height*0.72]:
        for i in range(max(1, int(width / 1.2))):
            cx = 0.3 + i * 1.0
            if cx + 0.15 < width:
                cell.add(gdstk.rectangle((cx, cy-0.08), (cx+0.15, cy+0.08), *LYR["contact"]))
    cell.add(gdstk.rectangle((0, height-0.18), (width, height), *LYR["m1"]))
    cell.add(gdstk.rectangle((0, 0), (width, 0.18), *LYR["m1"]))
    cell.add(gdstk.rectangle((width*0.4, height*0.45), (width*0.6, height*0.55), *LYR["m1"]))
    cell.add(gdstk.rectangle((0, 0), (width, height), *LYR["m1"]))
    cell.add(gdstk.Label(ctype, (width/2, height/2), layer=LYR["text"][0], texttype=LYR["text"][1]))
    return cell

def make_wire(x1, y1, x2, y2, layer):
    hw = WIRE_W / 2
    if x1 == x2:
        y1, y2 = min(y1,y2), max(y1,y2)
        return gdstk.rectangle((x1-hw, y1), (x1+hw, y2), *layer)
    else:
        x1, x2 = min(x1,x2), max(x1,x2)
        return gdstk.rectangle((x1, y1-hw), (x2, y1+hw), *layer)

def main():
    placed_p = ROOT / "pnr" / "placed_rv32i.json"
    routes_p = ROOT / "pnr" / "routes_rv32i.json"
    for p in (placed_p, routes_p):
        if not p.exists():
            sys.exit(f"ERROR: {p} not found – run PnR first.")

    placed = json.loads(placed_p.read_text())
    routes = json.loads(routes_p.read_text())

    lib = gdstk.Library("RV32I", unit=1e-6, precision=1e-9)
    top = lib.new_cell("RV32I_TOP")

    # Core boundary
    top.add(gdstk.rectangle((0, 0), (CORE_W, CORE_H), *LYR["m3"]))
    top.add(gdstk.Label("RV32I CORE", (CORE_W/2, CORE_H+1.0),
                        layer=LYR["text"][0], texttype=LYR["text"][1]))

    # Power stripes every 20 µm
    for x in range(10, int(CORE_W), 20):
        top.add(gdstk.rectangle((x-0.4, 0), (x+0.4, CORE_H), *LYR["m3"]))
        top.add(gdstk.rectangle((x+9.6, 0), (x+10.4, CORE_H), *LYR["m3"]))

    # Standard cells – share geometry via References
    sc_cache = {}
    print(f"Placing {len(placed)} cell references …")
    for cell in placed:
        ctype = cell["type"]
        key   = (ctype, cell["w"], cell["h"])
        if key not in sc_cache:
            sc_cache[key] = make_cell_geometry(lib, ctype, cell["w"], cell["h"])
        ref = gdstk.Reference(sc_cache[key], origin=(cell["x"], cell["y"]))
        top.add(ref)

    # Wires – sample every 10th net to limit file size for the demo
    print(f"Adding wire routes …")
    net_names = list(routes.keys())
    sampled   = net_names[::10]   # 10% of nets for visualisation
    for net in sampled:
        for x1, y1, x2, y2 in routes[net]:
            if abs(y2-y1) < 1e-9:
                top.add(make_wire(x1, y1, x2, y2, LYR["m1"]))
            else:
                top.add(make_wire(x1, y1, x2, y2, LYR["m2"]))
                top.add(gdstk.rectangle((x1-0.1, y1-0.1), (x1+0.1, y1+0.1), *LYR["via1"]))

    out = ROOT / "gds" / "rv32i.gds"
    lib.write_gds(str(out))
    size_kb = out.stat().st_size / 1024
    print(f"GDS written : {out}  ({size_kb:.1f} KB)")
    print(f"  Cells     : {len(lib.cells)}")
    print(f"  Top cell  : RV32I_TOP")
    print(f"  Unit      : 1 µm / 1 nm precision")

if __name__ == "__main__":
    main()
