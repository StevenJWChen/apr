// 4-bit Adder-Accumulator (ACC4)
// Spec: spec/SPEC.md
module acc4 (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       en,
    input  wire [3:0] a,
    output reg  [3:0] acc,
    output reg        carry
);
    wire [4:0] sum = {1'b0, acc} + {1'b0, a};

    always @(posedge clk) begin
        if (!rst_n) begin
            acc   <= 4'b0;
            carry <= 1'b0;
        end else if (en) begin
            acc   <= sum[3:0];
            carry <= sum[4];
        end
    end
endmodule
