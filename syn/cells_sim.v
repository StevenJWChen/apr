// Behavioural simulation models for demo130 standard cells
`timescale 1ns/1ps

module INV  (input A, output Y); assign #0.08 Y = ~A; endmodule
module BUF  (input A, output Y); assign #0.10 Y =  A; endmodule
module NAND2(input A, B, output Y); assign #0.10 Y = ~(A & B); endmodule
module NOR2 (input A, B, output Y); assign #0.12 Y = ~(A | B); endmodule
module AND2 (input A, B, output Y); assign #0.13 Y =  A & B;  endmodule
module OR2  (input A, B, output Y); assign #0.14 Y =  A | B;  endmodule
module XOR2 (input A, B, output Y); assign #0.18 Y =  A ^ B;  endmodule
module XNOR2(input A, B, output Y); assign #0.18 Y = ~(A ^ B); endmodule
module MUX2 (input A, B, S, output Y); assign #0.15 Y = S ? B : A; endmodule

module DFF (
    input      CLK,
    input      D,
    output reg Q,
    output     QN
);
    assign QN = ~Q;
    always @(posedge CLK) Q <= D;
endmodule
