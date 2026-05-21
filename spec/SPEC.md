# Design Specification: 4-bit Adder-Accumulator (ACC4)

## 1. Overview

ACC4 is a synchronous 4-bit adder-accumulator. On every rising clock edge the
current accumulator value is added to the input operand and the result is
stored back into the accumulator register.

## 2. Interface

| Port  | Direction | Width | Description                           |
|-------|-----------|-------|---------------------------------------|
| clk   | input     | 1     | Clock – active rising edge            |
| rst_n | input     | 1     | Active-low synchronous reset          |
| en    | input     | 1     | Accumulate enable                     |
| a     | input     | 4     | 4-bit unsigned operand                |
| acc   | output    | 4     | 4-bit accumulated result (lower bits) |
| carry | output    | 1     | Carry-out of the accumulation         |

## 3. Functional Description

```
On every rising edge of clk:
  if rst_n == 0:
    acc  <= 4'b0000
    carry <= 1'b0
  else if en == 1:
    {carry, acc} <= acc + a
```

## 4. Timing Requirements

| Parameter       | Min  | Typ  | Max  | Unit |
|-----------------|------|------|------|------|
| Clock frequency | -    | 100  | 200  | MHz  |
| Setup time      | -    | -    | 2    | ns   |
| Hold time       | 0.5  | -    | -    | ns   |

## 5. Power Budget

- Target technology: 130 nm (sky130-like cell models)
- Core voltage: 1.8 V
- Max dynamic power: 1 mW @ 100 MHz

## 6. Physical Constraints

- Core area ≤ 50 µm × 50 µm
- Metal layers: M1–M3
- Pin pitch: 5 µm
