`timescale 1ns/1ps
module tb_rv32i;
    reg clk, rst_n;

    rv32i_soc #(.IMEM_FILE("rtl/rv32i/prog.hex")) dut (.clk(clk), .rst_n(rst_n));

    initial clk = 0;
    always #5 clk = ~clk;

    integer errors = 0;
    integer cycle  = 0;

    task check32;
        input [31:0] got, exp;
        input [255:0] label;
        begin
            if (got !== exp) begin
                $display("FAIL [%0s]: got=%0d exp=%0d", label, got, exp);
                errors = errors + 1;
            end else
                $display("PASS [%0s]: %0d", label, got);
        end
    endtask

    // done: jal x0, done is the last instruction (PC=0x68)
    localparam DONE_PC = 32'h6C;   // done: jal x0, done (28 instr * 4 = 0x70 - 4 = 0x6C)
    localparam TIMEOUT = 5000;

    initial begin
        $dumpfile("sim/rv32i_sim.vcd");
        $dumpvars(0, tb_rv32i);

        rst_n = 0;
        repeat(4) @(posedge clk);
        rst_n = 1;

        while (dut.u_core.pc !== DONE_PC && cycle < TIMEOUT) begin
            @(posedge clk);
            cycle = cycle + 1;
        end

        if (cycle >= TIMEOUT) begin
            $display("TIMEOUT at cycle %0d, PC=0x%h", cycle, dut.u_core.pc);
            errors = errors + 1;
        end else begin
            $display("Halted at PC=0x%h after %0d cycles", dut.u_core.pc, cycle);
        end

        // dmem is word-addressed: dmem[0]=addr0, dmem[1]=addr4, dmem[2]=addr8, dmem[3]=addr12
        check32(dut.dmem[0], 32'd55,  "fib(10)=55 @ dmem[0]");
        check32(dut.dmem[1], 32'd34,  "fib(9)=34  @ dmem[1]");
        check32(dut.dmem[2], 32'd220, "55<<2=220  @ dmem[2]");
        check32(dut.dmem[3], 32'd42,  "jal_test=42@ dmem[3]");

        // x16 should be 0 (jal skipped that addi)
        check32(dut.u_core.u_rf.rf[16], 32'd0, "x16=0 (jal-skipped)");

        if (errors == 0)
            $display("\n=== RV32I SIM PASSED (%0d cycles) ===", cycle);
        else
            $display("\n=== RV32I SIM FAILED (%0d errors) ===", errors);
        $finish;
    end
endmodule
