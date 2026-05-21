#!/usr/bin/env python3
"""
Layout vs. Schematic (LVS) check for RV32I core / demo130.

Compares syn/netlist_rv32i.v (schematic) against pnr/placed_rv32i.json (layout).
Writes signoff/lvs_rv32i_report.txt.
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
    sch_names = set(schematic)
    lay_names = set(layout)

    missing_in_layout = sch_names - lay_names
    extra_in_layout   = lay_names - sch_names

    for n in sorted(missing_in_layout)[:10]:
        errors.append(f"LVS-1  '{n}' in schematic but missing in layout")
    if len(missing_in_layout) > 10:
        errors.append(f"LVS-1  ... ({len(missing_in_layout)-10} more missing)")

    for n in sorted(extra_in_layout)[:10]:
        errors.append(f"LVS-1  '{n}' in layout but missing in schematic")
    if len(extra_in_layout) > 10:
        errors.append(f"LVS-1  ... ({len(extra_in_layout)-10} more extra)")

    type_mismatches = 0
    pin_mismatches  = 0
    for name in sch_names & lay_names:
        sc, ly = schematic[name], layout[name]
        if sc["type"] != ly["type"]:
            type_mismatches += 1
        for pin, net in sc["pins"].items():
            if pin not in ly["pins"] or ly["pins"][pin] != net:
                pin_mismatches += 1

    if type_mismatches:
        errors.append(f"LVS-2  {type_mismatches} cell type mismatches")
    if pin_mismatches:
        errors.append(f"LVS-3  {pin_mismatches} pin/net connectivity mismatches")

    return errors

def main():
    netlist_p = ROOT / "syn" / "netlist_rv32i.v"
    placed_p  = ROOT / "pnr" / "placed_rv32i.json"
    for p in (netlist_p, placed_p):
        if not p.exists():
            sys.exit(f"ERROR: {p} not found.")

    schematic = parse_netlist(netlist_p)
    layout    = load_placed(placed_p)
    errors    = lvs(schematic, layout)

    status = "PASS" if not errors else f"FAIL ({len(errors)} error groups)"
    lines  = [
        "LVS Report – RV32I / demo130",
        "=" * 45,
        f"  Schematic cells : {len(schematic)}",
        f"  Layout cells    : {len(layout)}",
        "-" * 45,
    ]
    if errors:
        lines += ["  Errors:"] + [f"    {e}" for e in errors]
    else:
        lines += ["  Schematic matches layout – LVS CLEAN."]
    lines += ["=" * 45, f"LVS status : {status}"]
    report = "\n".join(lines) + "\n"

    (ROOT / "signoff" / "lvs_rv32i_report.txt").write_text(report)
    print(report)
    if errors:
        sys.exit(1)

if __name__ == "__main__":
    main()
