// RV32I ALU
module rv32i_alu (
    input  [31:0] a,
    input  [31:0] b,
    input  [3:0]  op,
    output reg [31:0] result,
    output        zero
);
    localparam ADD  = 4'd0, SUB  = 4'd1, SLL  = 4'd2, SLT  = 4'd3,
               SLTU = 4'd4, XOR  = 4'd5, SRL  = 4'd6, SRA  = 4'd7,
               OR   = 4'd8, AND  = 4'd9, PASS = 4'd10;

    assign zero = (result == 32'd0);

    always @(*) begin
        case (op)
            ADD:  result = a + b;
            SUB:  result = a - b;
            SLL:  result = a << b[4:0];
            SLT:  result = ($signed(a) < $signed(b)) ? 32'd1 : 32'd0;
            SLTU: result = (a < b) ? 32'd1 : 32'd0;
            XOR:  result = a ^ b;
            SRL:  result = a >> b[4:0];
            SRA:  result = $signed(a) >>> b[4:0];
            OR:   result = a | b;
            AND:  result = a & b;
            PASS: result = b;
            default: result = a + b;
        endcase
    end
endmodule
