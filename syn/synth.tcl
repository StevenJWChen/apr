# Yosys synthesis script for ACC4
# Usage: yosys -s syn/synth.tcl

# Read RTL
read_verilog rtl/acc4.v

# Elaborate
hierarchy -check -top acc4

# ── Technology-independent passes ────────────────────────
proc
opt
techmap
opt

# ── Expand SDFFE/ADFFE → simple $_DFF_P_ + MUX reset/enable ─
dfflegalize -cell $_DFF_P_ 0

# ── Map $_DFF_P_ to Liberty DFF cells ────────────────────
dfflibmap -liberty syn/cells.lib

# ── Map combinational logic to Liberty cells ─────────────
abc -liberty syn/cells.lib

# Clean up
clean -purge

# Reports
tee -o syn/area_report.txt stat -liberty syn/cells.lib

# Write synthesised netlist
write_verilog -noattr syn/netlist.v
