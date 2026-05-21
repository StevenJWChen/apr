#!/usr/bin/env python3
"""Render rv32i.gds to SVG + PNG."""

import pathlib, sys
import gdstk

ROOT = pathlib.Path(__file__).parent.parent

# Layer colours (same palette as acc4)
LAYER_STYLE = {
    (1, 0): ("2d6a4f", "52b788", 0.2),   # nwell    – green
    (2, 0): ("e76f51", "f4a261", 0.2),   # active   – orange
    (3, 0): ("457b9d", "a8dadc", 0.2),   # poly     – blue
    (4, 0): ("e9c46a", "f4d35e", 0.2),   # contact  – yellow
    (5, 0): ("264653", "2a9d8f", 0.3),   # m1       – teal
    (6, 0): ("e9c46a", "e9c46a", 0.2),   # via1     – yellow
    (7, 0): ("6a4c93", "c77dff", 0.3),   # m2       – purple
    (8, 0): ("8b0000", "ff4444", 0.5),   # m3       – red
    (64, 0): ("ffffff", "ffffff", 0.1),  # text     – white
}

SHAPE_STYLE = {
    (layer, dtype): {
        "fill": f"#{fill}",
        "stroke": f"#{stroke}",
        "stroke-width": str(sw),
    }
    for (layer, dtype), (fill, stroke, sw) in LAYER_STYLE.items()
    if layer != 64
}
LABEL_STYLE = {
    (64, 0): {"fill": "white", "font-size": "8px", "font-family": "monospace"},
}

def main():
    gds_path = ROOT / "gds" / "rv32i.gds"
    if not gds_path.exists():
        sys.exit("ERROR: gds/rv32i.gds not found.")

    lib = gdstk.read_gds(str(gds_path))
    top = lib.top_level()[0]

    svg_path = ROOT / "gds" / "rv32i_layout.svg"
    top.write_svg(
        str(svg_path),
        scaling=1.8,
        shape_style=SHAPE_STYLE,
        label_style=LABEL_STYLE,
        background="#111111",
        pad="2%",
    )
    print(f"SVG written: {svg_path}  ({svg_path.stat().st_size/1024:.1f} KB)")

    # Convert to PNG
    try:
        import cairosvg
        png_path = ROOT / "gds" / "rv32i_layout.png"
        cairosvg.svg2png(url=str(svg_path), write_to=str(png_path), scale=1.5)
        print(f"PNG written: {png_path}  ({png_path.stat().st_size/1024:.1f} KB)")
    except Exception as e:
        print(f"PNG conversion skipped: {e}")

if __name__ == "__main__":
    main()
