`timescale 1ns/1ps
module tb_acc4;
    reg        clk, rst_n, en;
    reg  [3:0] a;
    wire [3:0] acc;
    wire       carry;

    acc4 dut (.*);

    // 10 ns clock
    initial clk = 0;
    always #5 clk = ~clk;

    // Reference model
    reg  [4:0] ref_acc;
    integer    errors = 0;

    task check;
        input [3:0] exp_acc;
        input       exp_carry;
        input [63:0] label;
        begin
            #1; // small delta after rising edge
            if (acc !== exp_acc || carry !== exp_carry) begin
                $display("FAIL [%0d]: acc=%b carry=%b  exp acc=%b carry=%b",
                         label, acc, carry, exp_acc, exp_carry);
                errors = errors + 1;
            end else begin
                $display("PASS [%0d]: acc=%0d carry=%0d", label, acc, carry);
            end
        end
    endtask

    integer i;
    initial begin
        $dumpfile("sim/rtl_sim.vcd");
        $dumpvars(0, tb_acc4);

        rst_n = 0; en = 0; a = 0;
        @(posedge clk); @(posedge clk);

        // Release reset
        rst_n = 1;
        check(0, 0, 1);

        // Accumulate 3 three times: 3, 6, 9 (carry=0)
        en = 1; a = 4'd3;
        @(posedge clk); check(4'd3,  0, 2);
        @(posedge clk); check(4'd6,  0, 3);
        @(posedge clk); check(4'd9,  0, 4);

        // Accumulate 10: 9+10=19 => acc=3, carry=1
        a = 4'd10;
        @(posedge clk); check(4'd3, 1, 5);

        // Accumulate 4: 3+4=7, carry clears
        a = 4'd4;
        @(posedge clk); check(4'd7, 0, 6);

        // en=0: value held
        en = 0;
        @(posedge clk); check(4'd7, 0, 7);

        // Synchronous reset while running
        en = 1; a = 4'd15;
        @(posedge clk); // 7+15=22 => acc=6,carry=1
        rst_n = 0;
        @(posedge clk); check(4'd0, 0, 8);
        rst_n = 1;

        // All-ones: 15+15=30 => acc=14,carry=1
        a = 4'd15;
        @(posedge clk); check(4'd15, 0, 9);
        @(posedge clk); check(4'd14, 1, 10);

        if (errors == 0)
            $display("\n=== RTL SIM PASSED (%0d checks) ===", 10);
        else
            $display("\n=== RTL SIM FAILED (%0d errors) ===", errors);

        $finish;
    end
endmodule
