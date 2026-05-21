#!/usr/bin/env python3
"""
Minimal RV32I assembler – supports the instructions used in prog.s
Usage: python3 assemble.py prog.s prog.hex
"""
import sys, re

def sign_extend(val, bits):
    if val >= (1 << (bits-1)):
        val -= (1 << bits)
    return val

def encode_r(funct7, rs2, rs1, funct3, rd, opcode):
    return ((funct7&0x7F)<<25)|((rs2&0x1F)<<20)|((rs1&0x1F)<<15)|\
           ((funct3&0x7)<<12)|((rd&0x1F)<<7)|(opcode&0x7F)

def encode_i(imm12, rs1, funct3, rd, opcode):
    imm12 &= 0xFFF
    return (imm12<<20)|((rs1&0x1F)<<15)|((funct3&0x7)<<12)|\
           ((rd&0x1F)<<7)|(opcode&0x7F)

def encode_s(imm12, rs2, rs1, funct3, opcode):
    imm12 &= 0xFFF
    return (((imm12>>5)&0x7F)<<25)|((rs2&0x1F)<<20)|((rs1&0x1F)<<15)|\
           ((funct3&0x7)<<12)|((imm12&0x1F)<<7)|(opcode&0x7F)

def encode_b(offset, rs2, rs1, funct3, opcode):
    o = offset & 0x1FFF
    b12=(o>>12)&1; b11=(o>>11)&1; b10_5=(o>>5)&0x3F; b4_1=(o>>1)&0xF
    return (b12<<31)|(b10_5<<25)|((rs2&0x1F)<<20)|((rs1&0x1F)<<15)|\
           ((funct3&0x7)<<12)|(b4_1<<8)|(b11<<7)|(opcode&0x7F)

def encode_u(imm20, rd, opcode):
    return ((imm20&0xFFFFF)<<12)|((rd&0x1F)<<7)|(opcode&0x7F)

def encode_j(offset, rd, opcode):
    o = offset & 0x1FFFFF
    b20=(o>>20)&1; b10_1=(o>>1)&0x3FF; b11=(o>>11)&1; b19_12=(o>>12)&0xFF
    return (b20<<31)|(b19_12<<12)|(b11<<20)|(b10_1<<21)|\
           ((rd&0x1F)<<7)|(opcode&0x7F)

REG = {f'x{i}':i for i in range(32)}
REG.update({'zero':0,'ra':1,'sp':2,'gp':3,'tp':4,
            't0':5,'t1':6,'t2':7,'s0':8,'fp':8,'s1':9,
            'a0':10,'a1':11,'a2':12,'a3':13,'a4':14,'a5':15,
            'a6':16,'a7':17,'s2':18,'s3':19,'s4':20,'s5':21,
            's6':22,'s7':23,'s8':24,'s9':25,'s10':26,'s11':27,
            't3':28,'t4':29,'t5':30,'t6':31})

def r(s): return REG[s.strip()]
def imm(s):
    s=s.strip()
    return int(s,16) if s.startswith('0x') or s.startswith('-0x') else int(s)

def parse_mem(s):
    m=re.match(r'(-?\d+)\((\w+)\)',s.strip())
    return int(m.group(1)), REG[m.group(2)]

def assemble(src_path, out_path):
    lines = open(src_path).readlines()
    # First pass: collect labels
    labels = {}
    pc = 0
    for line in lines:
        line = re.sub(r'#.*','',line).strip()
        if not line: continue
        if line.endswith(':'):
            labels[line[:-1]] = pc
        elif ':' in line and not line.startswith('.'):
            lbl, rest = line.split(':',1)
            labels[lbl.strip()] = pc
            if rest.strip(): pc += 4
        else:
            pc += 4

    # Second pass: encode
    instructions = []
    pc = 0
    for line in lines:
        line = re.sub(r'#.*','',line).strip()
        if not line: continue
        if line.endswith(':') or (line.split(':')[0].strip() in labels and ':' in line):
            if ':' in line:
                line = line.split(':',1)[1].strip()
            if not line: continue
        parts = re.split(r'[\s,]+', line.strip(), maxsplit=1)
        op = parts[0].lower()
        args = [a.strip() for a in re.split(r',',parts[1])] if len(parts)>1 else []

        enc = None
        if op == 'add':
            enc = encode_r(0,r(args[2]),r(args[1]),0,r(args[0]),0x33)
        elif op == 'sub':
            enc = encode_r(0x20,r(args[2]),r(args[1]),0,r(args[0]),0x33)
        elif op in ('sll','slt','sltu','xor','srl','sra','or','and'):
            f3={'sll':1,'slt':2,'sltu':3,'xor':4,'srl':5,'sra':5,'or':6,'and':7}[op]
            f7=0x20 if op=='sra' else 0
            enc = encode_r(f7,r(args[2]),r(args[1]),f3,r(args[0]),0x33)
        elif op == 'addi':
            enc = encode_i(imm(args[2]),r(args[1]),0,r(args[0]),0x13)
        elif op in ('slti','sltiu','xori','ori','andi'):
            f3={'slti':2,'sltiu':3,'xori':4,'ori':6,'andi':7}[op]
            enc = encode_i(imm(args[2]),r(args[1]),f3,r(args[0]),0x13)
        elif op == 'slli':
            enc = encode_i(imm(args[2])&0x1F,r(args[1]),1,r(args[0]),0x13)
        elif op in ('srli','srai'):
            shamt=imm(args[2])&0x1F
            f7=0x20 if op=='srai' else 0
            enc = encode_i((f7<<5)|shamt,r(args[1]),5,r(args[0]),0x13)
        elif op == 'lui':
            enc = encode_u(imm(args[1]),r(args[0]),0x37)
        elif op == 'auipc':
            enc = encode_u(imm(args[1]),r(args[0]),0x17)
        elif op == 'lw':
            off,base=parse_mem(args[1])
            enc = encode_i(off,base,2,r(args[0]),0x03)
        elif op == 'lh':
            off,base=parse_mem(args[1])
            enc = encode_i(off,base,1,r(args[0]),0x03)
        elif op == 'lb':
            off,base=parse_mem(args[1])
            enc = encode_i(off,base,0,r(args[0]),0x03)
        elif op == 'lhu':
            off,base=parse_mem(args[1])
            enc = encode_i(off,base,5,r(args[0]),0x03)
        elif op == 'lbu':
            off,base=parse_mem(args[1])
            enc = encode_i(off,base,4,r(args[0]),0x03)
        elif op == 'sw':
            off,base=parse_mem(args[1])
            enc = encode_s(off,r(args[0]),base,2,0x23)
        elif op == 'sh':
            off,base=parse_mem(args[1])
            enc = encode_s(off,r(args[0]),base,1,0x23)
        elif op == 'sb':
            off,base=parse_mem(args[1])
            enc = encode_s(off,r(args[0]),base,0,0x23)
        elif op in ('beq','bne','blt','bge','bltu','bgeu'):
            f3={'beq':0,'bne':1,'blt':4,'bge':5,'bltu':6,'bgeu':7}[op]
            tgt=labels.get(args[2].strip(), None)
            offset=imm(args[2]) if tgt is None else (tgt-pc)
            enc = encode_b(offset,r(args[1]),r(args[0]),f3,0x63)
        elif op == 'jal':
            tgt=labels.get(args[1].strip(), None)
            offset=imm(args[1]) if tgt is None else (tgt-pc)
            enc = encode_j(offset,r(args[0]),0x6F)
        elif op == 'jalr':
            off,base=parse_mem(args[1]) if '(' in args[1] else (imm(args[1]),r(args[2]) if len(args)>2 else 0)
            enc = encode_i(off,base,0,r(args[0]),0x67)
        elif op == 'mv':
            enc = encode_i(0,r(args[1]),0,r(args[0]),0x13)
        elif op == 'li':
            enc = encode_i(imm(args[1]),0,0,r(args[0]),0x13)
        elif op == 'nop':
            enc = encode_i(0,0,0,0,0x13)  # addi x0,x0,0
        else:
            print(f'Unknown: {op}', file=sys.stderr)
            enc = 0

        instructions.append((pc, enc))
        pc += 4

    with open(out_path,'w') as f:
        for _, enc in instructions:
            f.write(f'{enc & 0xFFFFFFFF:08x}\n')
    print(f'Assembled {len(instructions)} instructions → {out_path}')

if __name__ == '__main__':
    assemble(sys.argv[1], sys.argv[2])
