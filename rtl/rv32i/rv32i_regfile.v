// RV32I 32x32 register file (x0 hardwired to 0)
module rv32i_regfile (
    input         clk,
    input  [4:0]  rs1, rs2, rd,
    input  [31:0] wdata,
    input         wen,
    output [31:0] rdata1,
    output [31:0] rdata2
);
    reg [31:0] rf [1:31];

    assign rdata1 = (rs1 == 5'd0) ? 32'd0 : rf[rs1];
    assign rdata2 = (rs2 == 5'd0) ? 32'd0 : rf[rs2];

    always @(posedge clk)
        if (wen && rd != 5'd0) rf[rd] <= wdata;
endmodule
