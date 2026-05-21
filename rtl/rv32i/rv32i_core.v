// RV32I Single-Cycle Core
// Interfaces with external IMEM and DMEM (not synthesized here)
module rv32i_core (
    input         clk,
    input         rst_n,
    // Instruction memory (read-only)
    output [31:0] imem_addr,
    input  [31:0] imem_rdata,
    // Data memory
    output [31:0] dmem_addr,
    output [31:0] dmem_wdata,
    output [3:0]  dmem_wmask,
    output        dmem_wen,
    input  [31:0] dmem_rdata
);
    // ── Opcode constants ────────────────────────────────────
    localparam OP_LUI   = 7'h37, OP_AUIPC = 7'h17,
               OP_JAL   = 7'h6F, OP_JALR  = 7'h67,
               OP_BRANCH= 7'h63, OP_LOAD  = 7'h03,
               OP_STORE = 7'h23, OP_ALUI  = 7'h13,
               OP_ALU   = 7'h33;

    // ── ALU op encoding ─────────────────────────────────────
    localparam ALU_ADD=4'd0, ALU_SUB=4'd1, ALU_SLL=4'd2, ALU_SLT=4'd3,
               ALU_SLTU=4'd4, ALU_XOR=4'd5, ALU_SRL=4'd6, ALU_SRA=4'd7,
               ALU_OR=4'd8,  ALU_AND=4'd9, ALU_PASS=4'd10;

    // ── PC ──────────────────────────────────────────────────
    reg  [31:0] pc;
    assign imem_addr = pc;

    // ── Instruction decode ───────────────────────────────────
    wire [31:0] instr  = imem_rdata;
    wire [6:0]  opcode = instr[6:0];
    wire [4:0]  rd     = instr[11:7];
    wire [2:0]  funct3 = instr[14:12];
    wire [4:0]  rs1    = instr[19:15];
    wire [4:0]  rs2    = instr[24:20];
    wire [6:0]  funct7 = instr[31:25];

    // Immediate generation
    wire [31:0] imm_i = {{20{instr[31]}}, instr[31:20]};
    wire [31:0] imm_s = {{20{instr[31]}}, instr[31:25], instr[11:7]};
    wire [31:0] imm_b = {{19{instr[31]}}, instr[31], instr[7],
                         instr[30:25], instr[11:8], 1'b0};
    wire [31:0] imm_u = {instr[31:12], 12'b0};
    wire [31:0] imm_j = {{11{instr[31]}}, instr[31], instr[19:12],
                         instr[20], instr[30:21], 1'b0};

    // ── Register file ────────────────────────────────────────
    wire [31:0] rf_rdata1, rf_rdata2;
    reg  [31:0] rf_wdata;
    reg         rf_wen;

    rv32i_regfile u_rf (
        .clk    (clk),
        .rs1    (rs1),   .rdata1 (rf_rdata1),
        .rs2    (rs2),   .rdata2 (rf_rdata2),
        .rd     (rd),    .wdata  (rf_wdata),  .wen (rf_wen)
    );

    // ── ALU ─────────────────────────────────────────────────
    reg  [31:0] alu_a, alu_b;
    reg  [3:0]  alu_op;
    wire [31:0] alu_result;
    wire        alu_zero;

    rv32i_alu u_alu (
        .a (alu_a), .b (alu_b), .op (alu_op),
        .result (alu_result), .zero (alu_zero)
    );

    // ── ALU input / op decode ────────────────────────────────
    wire is_r  = (opcode == OP_ALU);
    wire is_i  = (opcode == OP_ALUI);
    wire is_sub = is_r && funct7[5];
    wire is_sra = (funct3 == 3'b101) && funct7[5];

    always @(*) begin
        // ALU A: PC (for AUIPC/JAL/JALR) or rs1
        alu_a = (opcode == OP_AUIPC) ? pc : rf_rdata1;
        // ALU B: immediate or rs2
        alu_b = (is_r) ? rf_rdata2 :
                (opcode == OP_LUI || opcode == OP_AUIPC) ? imm_u :
                (opcode == OP_STORE) ? imm_s : imm_i;
        // ALU op decode
        case (funct3)
            3'b000: alu_op = (is_sub)  ? ALU_SUB : ALU_ADD;
            3'b001: alu_op = ALU_SLL;
            3'b010: alu_op = ALU_SLT;
            3'b011: alu_op = ALU_SLTU;
            3'b100: alu_op = ALU_XOR;
            3'b101: alu_op = is_sra   ? ALU_SRA : ALU_SRL;
            3'b110: alu_op = ALU_OR;
            3'b111: alu_op = ALU_AND;
            default: alu_op = ALU_ADD;
        endcase
        // Opcodes that always use ADD or PASS regardless of funct3
        if (opcode == OP_LUI)    alu_op = ALU_PASS;
        if (opcode == OP_AUIPC)  alu_op = ALU_ADD;
        if (opcode == OP_JAL)    alu_op = ALU_ADD;
        if (opcode == OP_JALR)   alu_op = ALU_ADD;
        if (opcode == OP_LOAD)   alu_op = ALU_ADD; // addr = base + imm_i
        if (opcode == OP_STORE)  alu_op = ALU_ADD; // addr = base + imm_s
        if (opcode == OP_BRANCH) alu_op = ALU_ADD; // comparisons done separately
    end

    // ── Branch condition ─────────────────────────────────────
    wire [31:0] rs1v = rf_rdata1, rs2v = rf_rdata2;
    wire        br_eq  = (rs1v == rs2v);
    wire        br_lt  = ($signed(rs1v) < $signed(rs2v));
    wire        br_ltu = (rs1v < rs2v);

    reg taken;
    always @(*) begin
        case (funct3)
            3'b000: taken = br_eq;
            3'b001: taken = !br_eq;
            3'b100: taken = br_lt;
            3'b101: taken = !br_lt;
            3'b110: taken = br_ltu;
            3'b111: taken = !br_ltu;
            default: taken = 1'b0;
        endcase
    end

    // ── Data memory ──────────────────────────────────────────
    assign dmem_addr  = alu_result;
    assign dmem_wdata = rs2v;
    assign dmem_wen   = (opcode == OP_STORE);

    // Byte-write mask from funct3
    assign dmem_wmask = (opcode == OP_STORE) ?
        (funct3 == 3'b000 ? (4'b0001 << alu_result[1:0]) :
         funct3 == 3'b001 ? (4'b0011 << {alu_result[1], 1'b0}) :
                             4'b1111) : 4'b0000;

    // Load data with sign/zero extension
    wire [31:0] lb  = {{24{dmem_rdata[7]}},  dmem_rdata[7:0]};
    wire [31:0] lbu = {24'd0,                 dmem_rdata[7:0]};
    wire [31:0] lh  = {{16{dmem_rdata[15]}}, dmem_rdata[15:0]};
    wire [31:0] lhu = {16'd0,                 dmem_rdata[15:0]};
    wire [31:0] lw  =                         dmem_rdata;

    reg [31:0] load_data;
    always @(*) begin
        case (funct3)
            3'b000: load_data = lb;
            3'b001: load_data = lh;
            3'b010: load_data = lw;
            3'b100: load_data = lbu;
            3'b101: load_data = lhu;
            default: load_data = lw;
        endcase
    end

    // ── Writeback ────────────────────────────────────────────
    wire [31:0] pc_plus4 = pc + 32'd4;

    always @(*) begin
        rf_wen   = 1'b0;
        rf_wdata = 32'd0;
        case (opcode)
            OP_ALU, OP_ALUI, OP_LUI, OP_AUIPC: begin
                rf_wen   = 1'b1;
                rf_wdata = alu_result;
            end
            OP_LOAD: begin
                rf_wen   = 1'b1;
                rf_wdata = load_data;
            end
            OP_JAL, OP_JALR: begin
                rf_wen   = 1'b1;
                rf_wdata = pc_plus4;
            end
            default: ;
        endcase
    end

    // ── Next PC ──────────────────────────────────────────────
    wire [31:0] pc_branch = pc + imm_b;
    wire [31:0] pc_jal    = pc + imm_j;
    wire [31:0] pc_jalr   = {alu_result[31:1], 1'b0};

    reg [31:0] next_pc;
    always @(*) begin
        case (opcode)
            OP_JAL:    next_pc = pc_jal;
            OP_JALR:   next_pc = pc_jalr;
            OP_BRANCH: next_pc = taken ? pc_branch : pc_plus4;
            default:   next_pc = pc_plus4;
        endcase
    end

    // ── PC register ──────────────────────────────────────────
    always @(posedge clk) begin
        if (!rst_n) pc <= 32'd0;
        else        pc <= next_pc;
    end
endmodule
