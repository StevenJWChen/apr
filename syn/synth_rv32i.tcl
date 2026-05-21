# Yosys synthesis script for RV32I core (no memories)
# Usage: yosys -s syn/synth_rv32i.tcl

read_verilog rtl/rv32i/rv32i_alu.v
read_verilog rtl/rv32i/rv32i_regfile.v
read_verilog rtl/rv32i/rv32i_core.v

hierarchy -check -top rv32i_core

proc
opt
memory          ; # expand register-file array to FF primitives
techmap
opt

# Expand complex FFs to $_DFF_P_ + MUX (reset/enable logic)
dfflegalize -cell $_DFF_P_ 0

# Map FFs to Liberty DFF
dfflibmap -liberty syn/cells.lib

# Map combinational logic to Liberty cells
abc -liberty syn/cells.lib

clean -purge

tee -o syn/area_rv32i.txt stat -liberty syn/cells.lib

write_verilog -noattr syn/netlist_rv32i.v
