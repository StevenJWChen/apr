# RV32I test program – Fibonacci + basic ISA coverage
# After running: dmem[0] = fib(10)=55, dmem[4] = fib(9)=34
# Also exercises: R-type, I-type, branch, load, store, LUI, AUIPC, JAL

        addi  x1, x0, 0       # x1 = 0 = fib(0)
        addi  x2, x0, 1       # x2 = 1 = fib(1)
        addi  x3, x0, 9       # x3 = 9 iterations → fib(10)=55

loop:
        add   x4, x1, x2      # x4 = fib(n) = fib(n-2) + fib(n-1)
        mv    x1, x2           # x1 = old fib(n-1)
        mv    x2, x4           # x2 = new fib(n)
        addi  x3, x3, -1      # counter--
        bne   x3, x0, loop    # loop if counter != 0

        # x2 = fib(10) = 55, x1 = fib(9) = 34
        sw    x2, 0(x0)        # dmem[0]  = 55
        sw    x1, 4(x0)        # dmem[4]  = 34

        # Exercise LUI / AUIPC / shifts
        lui   x5, 1            # x5 = 0x00001000
        addi  x5, x5, -1      # x5 = 0x00000FFF
        slli  x6, x2, 2       # x6 = 55 << 2 = 220
        srli  x7, x6, 1       # x7 = 110
        srai  x8, x6, 1       # x8 = 110 (positive, same)
        xor   x9, x5, x6      # x9 = 0xFFF ^ 220
        and   x10, x5, x6     # x10 = x5 & x6
        or    x11, x5, x6     # x11 = x5 | x6
        sw    x6, 8(x0)        # dmem[8]  = 220

        # Load back and verify
        lw    x12, 0(x0)       # x12 = dmem[0] = 55
        lw    x13, 4(x0)       # x13 = 34
        lw    x14, 8(x0)       # x14 = 220

        # JAL/JALR test: x16 initialised to 0, should stay 0 if addi below is skipped
        addi  x16, x0, 0       # x16 = 0 (sentinel)
        jal   x15, skip        # x15 = PC+4, jump to skip
        addi  x16, x0, 0xFF   # should be skipped

skip:
        addi  x17, x0, 42     # x17 = 42
        sw    x17, 12(x0)      # dmem[12] = 42

done:
        jal   x0, done         # halt (infinite loop)
