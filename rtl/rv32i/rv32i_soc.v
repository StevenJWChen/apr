// RV32I SoC – core + IMEM (ROM) + DMEM (word-addressed RAM)
// IMEM: 256 words (1 KB), DMEM: 256 words (1 KB)
module rv32i_soc #(
    parameter IMEM_FILE = "prog.hex"
) (
    input clk,
    input rst_n
);
    // ── Instruction memory ──────────────────────────────────
    reg [31:0] imem [0:255];
    initial $readmemh(IMEM_FILE, imem);

    wire [31:0] imem_addr, imem_rdata;
    assign imem_rdata = imem[imem_addr[9:2]];

    // ── Data memory (word-addressed) ────────────────────────
    // Word address = byte_addr >> 2  (all accesses must be word-aligned)
    reg  [31:0] dmem [0:255];
    wire [31:0] dmem_addr, dmem_wdata;
    wire [3:0]  dmem_wmask;
    wire        dmem_wen;
    wire [31:0] dmem_rdata;

    assign dmem_rdata = dmem[dmem_addr[9:2]];

    always @(posedge clk)
        if (dmem_wen) dmem[dmem_addr[9:2]] <= dmem_wdata;

    // ── Core ─────────────────────────────────────────────────
    rv32i_core u_core (
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
endmodule
