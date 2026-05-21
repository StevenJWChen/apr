#!/usr/bin/env python3
"""
Layout vs. Schematic (LVS) check for ACC4.

Compares the placed netlist (layout view) against the synthesised
schematic (syn/netlist.v):
  - Cell instance count matches
  - Cell types match
  - Net connectivity matches (pin connections)

Writes signoff/lvs_report.txt
"""

import json, re, pathlib, sys

ROOT = pathlib.Path(__file__).parent.parent
KNOWN_CELLS = {"INV","BUF","NAND2","NOR2","AND2","OR2",
               "XOR2","XNOR2","MUX2","DFF"}

def parse_netlist(path):
    text = path.read_text()
    pat  = re.compile(r'\b(\w+)\s+(\w+)\s*\(([^;]*?)\)\s*;', re.S)
    cells = {}
    for m in pat.finditer(text):
        ctype, iname, pins_raw = m.group(1), m.group(2), m.group(3)
        if ctype not in KNOWN_CELLS:
            continue
        pin_map = {}
        for pm in re.finditer(r'\.(\w+)\(([^)]*)\)', pins_raw):
            pin_map[pm.group(1)] = pm.group(2).strip()
        cells[iname] = {"type": ctype, "pins": pin_map}
    return cells

def load_placed(path):
    data = json.loads(path.read_text())
    return {c["name"]: {"type": c["type"], "pins": c.get("pins", {})}
            for c in data}

def lvs(schematic, layout):
    errors = []

    # Check instance sets
    sch_names = set(schematic)
    lay_names = set(layout)

    for n in sch_names - lay_names:
        errors.append(f"LVS-1  Instance '{n}' in schematic but missing in layout")
    for n in lay_names - sch_names:
        errors.append(f"LVS-1  Instance '{n}' in layout but missing in schematic")

    # Check types and connectivity for common instances
    for name in sch_names & lay_names:
        sc = schematic[name]
        ly = layout[name]
        if sc["type"] != ly["type"]:
            errors.append(f"LVS-2  Type mismatch for '{name}': "
                          f"sch={sc['type']} lay={ly['type']}")
        for pin, net in sc["pins"].items():
            if pin not in ly["pins"]:
                errors.append(f"LVS-3  Pin '{pin}' missing on '{name}' in layout")
            elif ly["pins"][pin] != net:
                errors.append(f"LVS-3  Net mismatch on '{name}.{pin}': "
                               f"sch={net} lay={ly['pins'][pin]}")

    return errors

def main():
    netlist_p = ROOT / "syn" / "netlist.v"
    placed_p  = ROOT / "pnr" / "placed.json"
    for p in (netlist_p, placed_p):
        if not p.exists():
            sys.exit(f"ERROR: {p} not found.")

    schematic = parse_netlist(netlist_p)
    layout    = load_placed(placed_p)
    errors    = lvs(schematic, layout)

    status = "PASS" if not errors else f"FAIL ({len(errors)} errors)"
    lines  = [
        "LVS Report – ACC4 / demo130",
        "=" * 45,
        f"  Schematic cells : {len(schematic)}",
        f"  Layout cells    : {len(layout)}",
        "-" * 45,
    ]
    if errors:
        lines += ["  Errors:"] + [f"    {e}" for e in errors]
    else:
        lines += ["  Schematic matches layout."]
    lines += ["=" * 45, f"LVS status : {status}"]
    report = "\n".join(lines) + "\n"

    (ROOT / "signoff" / "lvs_report.txt").write_text(report)
    print(report)
    if errors:
        sys.exit(1)

if __name__ == "__main__":
    main()
