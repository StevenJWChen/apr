#!/usr/bin/env python3
"""
GDSII export for ACC4.

Reads pnr/placed.json and pnr/routes.json and generates a real GDSII
file at gds/acc4.gds using the gdstk library.

Layer map (sky130-like):
  1  – N-well
  2  – Active (diffusion)
  3  – Poly
  4  – Contact
  5  – Metal-1 (M1, horizontal wires)
  6  – Via-1
  7  – Metal-2 (M2, vertical wires)
  8  – Metal-3 (M3, power stripes)
 64  – Text labels
"""

import json, pathlib, sys
import gdstk

ROOT = pathlib.Path(__file__).parent.parent

# Layer definitions
LYR = {
    "nwell"  : (1, 0),
    "active" : (2, 0),
    "poly"   : (3, 0),
    "contact": (4, 0),
    "m1"     : (5, 0),
    "via1"   : (6, 0),
    "m2"     : (7, 0),
    "m3"     : (8, 0),
    "text"   : (64,0),
}

CORE_W, CORE_H = 50.0, 50.0
WIRE_W = 0.3    # µm wire width

# Cell-type colour (represented as different active shapes for visual distinction)
CELL_COLOURS = {
    "DFF":  (0.40, 0.30),   # extra nwell band fraction
    "default": (0.20, 0.15),
}

def make_cell_geometry(lib, ctype, width, height):
    """Create a gdstk Cell with representative geometry for a standard cell."""
    cell = lib.new_cell(f"SC_{ctype}_{int(width*10)}x{int(height*10)}")

    # N-well (top half of cell)
    nw_h = height * 0.55
    cell.add(gdstk.rectangle((0, height - nw_h), (width, height), *LYR["nwell"]))

    # Active regions (PMOS top, NMOS bottom)
    aw = width * 0.7
    cell.add(gdstk.rectangle((width*0.15, height*0.60), (width*0.15+aw, height*0.85), *LYR["active"]))
    cell.add(gdstk.rectangle((width*0.15, height*0.15), (width*0.15+aw, height*0.40), *LYR["active"]))

    # Poly gates (number depends on cell type)
    n_gates = max(1, len(ctype) // 3)
    gate_pitch = width / (n_gates + 1)
    for i in range(n_gates):
        gx = gate_pitch * (i + 1)
        cell.add(gdstk.rectangle((gx-0.05, height*0.10), (gx+0.05, height*0.90), *LYR["poly"]))

    # Contacts
    for cy in [height*0.25, height*0.72]:
        for i in range(max(1, int(width / 1.2))):
            cx = 0.3 + i * 1.0
            if cx + 0.15 < width:
                cell.add(gdstk.rectangle((cx, cy-0.08), (cx+0.15, cy+0.08), *LYR["contact"]))

    # M1 power rails (VDD top, VSS bottom)
    cell.add(gdstk.rectangle((0, height-0.18), (width, height), *LYR["m1"]))
    cell.add(gdstk.rectangle((0, 0), (width, 0.18), *LYR["m1"]))

    # M1 output pin stub
    cell.add(gdstk.rectangle((width*0.4, height*0.45), (width*0.6, height*0.55), *LYR["m1"]))

    # Cell boundary outline (on M1 layer for clarity)
    cell.add(gdstk.rectangle((0, 0), (width, height), *LYR["m1"]))

    # Text label
    cell.add(gdstk.Label(ctype, (width/2, height/2), layer=LYR["text"][0], texttype=LYR["text"][1]))

    return cell

def make_wire(x1, y1, x2, y2, layer):
    """Return a rectangle representing a wire segment."""
    hw = WIRE_W / 2
    if x1 == x2:  # vertical → M2
        y1, y2 = min(y1,y2), max(y1,y2)
        return gdstk.rectangle((x1-hw, y1), (x1+hw, y2), *layer)
    else:           # horizontal → M1
        x1, x2 = min(x1,x2), max(x1,x2)
        return gdstk.rectangle((x1, y1-hw), (x2, y1+hw), *layer)

def main():
    placed_p = ROOT / "pnr" / "placed.json"
    routes_p = ROOT / "pnr" / "routes.json"
    for p in (placed_p, routes_p):
        if not p.exists():
            sys.exit(f"ERROR: {p} not found – run PnR first.")

    placed = json.loads(placed_p.read_text())
    routes = json.loads(routes_p.read_text())

    lib  = gdstk.Library("ACC4", unit=1e-6, precision=1e-9)
    top  = lib.new_cell("ACC4_TOP")

    # ── Core boundary ──────────────────────────────────────────────────────
    top.add(gdstk.rectangle((0, 0), (CORE_W, CORE_H), *LYR["m3"]))
    top.add(gdstk.Label("ACC4", (CORE_W/2, CORE_H+0.5), layer=LYR["text"][0], texttype=LYR["text"][1]))

    # ── Power stripes (M3) ─────────────────────────────────────────────────
    for x in range(5, int(CORE_W), 10):
        top.add(gdstk.rectangle((x-0.3, 0), (x+0.3, CORE_H), *LYR["m3"]))  # VDD
        top.add(gdstk.rectangle((x+4.7, 0), (x+5.3, CORE_H), *LYR["m3"])) # VSS

    # ── Standard cells ─────────────────────────────────────────────────────
    sc_cache = {}
    for cell in placed:
        ctype = cell["type"]
        key   = (ctype, cell["w"], cell["h"])
        if key not in sc_cache:
            sc_cache[key] = make_cell_geometry(lib, ctype, cell["w"], cell["h"])
        ref = gdstk.Reference(sc_cache[key], origin=(cell["x"], cell["y"]))
        top.add(ref)
        top.add(gdstk.Label(cell["name"],
                            (cell["x"]+cell["w"]/2, cell["y"]-0.3),
                            layer=LYR["text"][0], texttype=LYR["text"][1]))

    # ── Wires ──────────────────────────────────────────────────────────────
    for net, segs in routes.items():
        for x1, y1, x2, y2 in segs:
            # Horizontal on M1, vertical on M2
            if abs(y2-y1) < 1e-9:
                top.add(make_wire(x1, y1, x2, y2, LYR["m1"]))
            else:
                top.add(make_wire(x1, y1, x2, y2, LYR["m2"]))
                # Via at bend point
                top.add(gdstk.rectangle((x1-0.1, y1-0.1), (x1+0.1, y1+0.1), *LYR["via1"]))

    # ── Write GDS ──────────────────────────────────────────────────────────
    out = ROOT / "gds" / "acc4.gds"
    lib.write_gds(str(out))
    size_kb = out.stat().st_size / 1024
    print(f"GDS written : {out}  ({size_kb:.1f} KB)")
    print(f"  Cells     : {len(lib.cells)}")
    print(f"  Top cell  : ACC4_TOP")
    print(f"  Library   : {lib.name}")
    print(f"  Unit      : 1 µm / 1 nm precision")

if __name__ == "__main__":
    main()
