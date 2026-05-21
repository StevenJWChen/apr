# ACC4 IC Design Flow – Makefile
.PHONY: all rtl_sim syn gl_sim pnr sta drc lvs gds clean

all: gds

rtl_sim:
	@mkdir -p sim
	iverilog -o sim/rtl_sim -g2012 rtl/tb_acc4.v rtl/acc4.v
	vvp sim/rtl_sim

syn: rtl_sim
	yosys -s syn/synth.tcl

gl_sim: syn
	iverilog -o sim/gl_sim -g2012 -I syn rtl/tb_acc4.v syn/netlist.v syn/cells_sim.v
	vvp sim/gl_sim

pnr: gl_sim
	python3 pnr/pnr.py

sta: pnr
	python3 sta/sta.py

drc: sta
	python3 signoff/drc.py

lvs: drc
	python3 signoff/lvs.py

gds: lvs
	python3 gds/gds_export.py

clean:
	rm -rf sim/*.vcd sim/rtl_sim sim/gl_sim
	rm -f  syn/netlist.v syn/area_report.txt
	rm -f  pnr/placed.json pnr/routes.json pnr/pnr_report.txt
	rm -f  sta/timing_report.txt
	rm -f  signoff/drc_report.txt signoff/lvs_report.txt
	rm -f  gds/acc4.gds
