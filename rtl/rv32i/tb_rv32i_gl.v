// Gate-level testbench for RV32I core
// Wraps the synthesised rv32i_core inside a behavioural SoC
`timescale 1ns/1ps
module tb_rv32i_gl;
    reg clk, rst_n;

    // Behavioural memories for GL sim (core is now a netlist)
    reg  [31:0] imem [0:255];
    reg  [31:0] dmem [0:255];
    initial begin
        $readmemh("rtl/rv32i/prog.hex", imem);
        // zero-initialise DMEM
        begin : init_dm integer i; for (i=0; i<256; i=i+1) dmem[i] = 32'b0; end
    end

    wire [31:0] imem_addr, imem_rdata;
    wire [31:0] dmem_addr, dmem_wdata;
    wire [3:0]  dmem_wmask;
    wire        dmem_wen;
    wire [31:0] dmem_rdata;

    assign imem_rdata = imem[imem_addr[9:2]];
    assign dmem_rdata = dmem[dmem_addr[9:2]];

    always @(posedge clk)
        if (dmem_wen) dmem[dmem_addr[9:2]] <= dmem_wdata;

    // Synthesised core
    rv32i_core dut (
        .clk        (clk),
        .rst_n      (rst_n),
        .imem_addr  (imem_addr),
        .imem_rdata (imem_rdata),
        .dmem_addr  (dmem_addr),
        .dmem_wdata (dmem_wdata),
        .dmem_wmask (dmem_wmask),
        .dmem_wen   (dmem_wen),
        .dmem_rdata (dmem_rdata)
    );

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

    localparam TIMEOUT = 500;

    initial begin
        rst_n = 0;
        repeat(4) @(posedge clk);
        rst_n = 1;

        repeat(TIMEOUT) @(posedge clk);
        cycle = TIMEOUT;

        $display("GL sim ran %0d cycles", cycle);

        check32(dmem[0], 32'd55,  "fib(10)=55  @ dmem[0]");
        check32(dmem[1], 32'd34,  "fib(9)=34   @ dmem[1]");
        check32(dmem[2], 32'd220, "55<<2=220   @ dmem[2]");
        check32(dmem[3], 32'd42,  "jal_test=42 @ dmem[3]");

        if (errors == 0)
            $display("\n=== GL SIM PASSED (%0d cycles) ===", cycle);
        else
            $display("\n=== GL SIM FAILED (%0d errors) ===", errors);
        $finish;
    end
endmodule
