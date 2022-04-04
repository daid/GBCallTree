import re
import os
import json
import glob
import argparse
import shutil
from tokenizer import Tokenizer
from parser import parseExpr
from globals import DEFINES, MACROS, BASEPATH


class Block:
    def __init__(self, filename, linenr, label, prev):
        self.filename = filename
        self.linenr = linenr
        if label.startswith("."):
            self.label = prev.base_label + label
            self.base_label = prev.base_label
        else:
            self.label = label
            self.base_label = label
        self.instr = []
        self.next = None
        self.prev = prev
        if prev:
            prev.next = self
        self.instr = []
        self.uses = set()

    def addData(self, params):
        self.instr.append((None, params))

    def addInstr(self, value, params):
        self.instr.append((value, params))

BLOCKS = {}
cur_block = Block("", 0, "", None)
def processfile(f):
    global cur_block
    condition_list = [True]
    print(f"Processing: {f}")
    tok = Tokenizer(open(f, "rt").read())
    while tok:
        t = tok.pop()
        if t.isA('NEWLINE'):
            continue
        elif t.isA('ID', 'include'):
            filename = tok.expect('STRING').value
            if condition_list[-1]:
                if os.path.exists(os.path.join(BASEPATH, os.path.dirname(f), filename)):
                    processfile(os.path.join(BASEPATH, os.path.dirname(f), filename))
                else:
                    processfile(os.path.join(BASEPATH, filename))
            tok.expect('NEWLINE')
        elif t.isA('ID', 'incbin'):
            filename = tok.expect('STRING').value
            tok.expect('NEWLINE')
        elif t.isA('ID', 'IF'):
            res = parseExpr(tok) != 0
            condition_list.append(res and condition_list[-1])
            tok.expect('NEWLINE')
        elif t.isA('ID', 'ELIF'):
            res = parseExpr(tok)
            condition_list[-1] = (not condition_list[-1]) and condition_list[-2] and res
            tok.expect('NEWLINE')
        elif t.isA('ID', 'ELSE'):
            condition_list[-1] = (not condition_list[-1]) and condition_list[-2]
            tok.expect('NEWLINE')
        elif t.isA('ID', 'ENDC'):
            condition_list.pop()
            tok.expect('NEWLINE')
        elif t.isA('ID') and tok.peek().isA('ID', 'equs'):
            if condition_list[-1]:
                tok.pop()
                name = t.value
                DEFINES[name] = parseExpr(tok)
                print(name, "equs", DEFINES[name])
                tok.expect('NEWLINE')
            else:
                while not tok.pop().isA('NEWLINE'):
                    pass
        elif t.isA('ID') and t.value.upper() in {"DEF", "REDEF"}:
            if condition_list[-1]:
                t = tok.expect('ID')
                if tok.peek().isA('OP', '=') or tok.peek().isA('ID', 'equ'):
                    tok.pop()
                    DEFINES[t.value] = parseExpr(tok)
                    print(t.value, "=", DEFINES[t.value])
                elif tok.peek().isA('ID', 'equs'):
                    tok.pop()
                    DEFINES[t.value] = parseExpr(tok)
                    print(t.value, "equs", DEFINES[t.value])
                tok.expect('NEWLINE')
            else:
                while not tok.pop().isA('NEWLINE'):
                    pass
        elif t.isA('ID') and (tok.peek().isA('ID', 'equ') or tok.peek().isA('OP', '=')):
            if condition_list[-1]:
                tok.pop()
                DEFINES[t.value] = parseExpr(tok)
                print(t.value, "=", DEFINES[t.value])
                tok.expect('NEWLINE')
            else:
                while not tok.pop().isA('NEWLINE'):
                    pass
        elif t.isA('ID') and t.value.upper() in {'CHARMAP', 'SECTION', 'PUSHC', 'POPC', 'ASSERT', 'NEWCHARMAP', 'SETCHARMAP'}:
            while not tok.pop().isA('NEWLINE'):
                pass
        elif t.isA('ID', 'JP_TABLE'):
            cur_block.addInstr("JP_TABLE", [])
            while not tok.pop().isA('NEWLINE'):
                pass
        elif t.isA('ID') and t.value in MACROS:
            arg = []
            args = [arg]
            while not tok.peek().isA('NEWLINE'):
                if tok.peek().isA('OP', ','):
                    args.append([])
                    arg = args[-1];
                    tok.pop();
                else:
                    arg.append(tok.pop())
            tok.pop()
            if not args[-1]:
                args.pop()
            tok.pushMacro(MACROS[t.value], args)
            cur_block.addInstr("MACRO", [a for a in arg for arg in args])
        elif t.isA('ID') and (tok.peek().isA('LABEL') or t.value.startswith(".")):
            if tok.peek().isA('LABEL'):
                tok.pop()
            if tok.peek().isA('ID', 'macro'):
                macro = []
                tok.pop()
                tok.expect('NEWLINE')
                while True:
                    line = tok.popRawLine()
                    if line[2].upper().strip() == "ENDM":
                        break
                    macro.append((t.value, line[1], line[2]));
                MACROS[t.value] = macro
            elif condition_list[-1] and not re.match(r"\._[0-9A-F][0-9A-F]", t.value):
                cur_block = Block(f, t.line_nr, t.value, cur_block)
                assert cur_block.label not in BLOCKS, cur_block.label
                BLOCKS[cur_block.label] = cur_block
        elif t.isA('ID') and t.value.upper() in {'DB', 'DW', 'DS'}: # data
            params = []
            while not tok.peek().isA('NEWLINE'):
                params.append(tok.pop())
            tok.pop()
            cur_block.addData(params)
        elif t.isA('ID') and t.value.upper() in {'JP', 'JR', 'CALL', 'RST', 'RET', 'RETI', 'LD', 'LDH', 'LDI', 'LDD', 'ADD', 'ADC', 'SUB', 'SBC', 'AND', 'OR', 'XOR', 'NOP', 'CP', 'STOP', 'EI', 'DI', 'RRCA', 'INC', 'DEC', 'PUSH', 'POP', 'HALT', 'CPL', 'SLA', 'RL', 'RR', 'SWAP', 'RRA', 'SRL', 'RES', 'SET', 'BIT', 'DAA', 'SCF', 'CCF', 'RLA', 'SRA', 'RLCA', 'RLC', 'RRC'}:
            params = []
            while not tok.peek().isA('NEWLINE'):
                params.append(tok.pop())
            tok.pop()
            cur_block.addInstr(t.value, params)
        else:
            print(f"Unexpected: {t}")
            while not tok.pop().isA('NEWLINE'):
                pass

def isBlockEndingInstr(data):
    code, params = data
    if code is None:
        return True
    if code.upper() in {"RET", "RETI"}:
        return len(params) == 0
    if code.upper() in {"JR", "JP"} and len(params) > 0:
        return not params[0].isA('ID') or params[0].value.upper() not in {"Z", "C", "NZ", "NC"}
    return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('files', nargs='+')
    parser.add_argument('--basepath', default=os.getcwd())
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    BASEPATH = args.basepath
    for file in args.files:
        MACROS.clear()
        DEFINES.clear()
        DEFINES["VERSION"] = 0
        cur_block = Block("", 0, "", None)
        processfile(file)

    for label, block in BLOCKS.items():
        for instr, params in block.instr:
            for token in params:
                value = token.value
                if token.isA('ID') and value.startswith("."):
                    value = block.base_label + value
                if value in BLOCKS:
                    block.uses.add(BLOCKS[value])
        if not block.instr or not isBlockEndingInstr(block.instr[-1]):
            if block.next:
                block.uses.add(block.next)
    file_json = [{"f": filename, "l": len(open(filename, "rt").readlines())} for filename in sorted(set([block.filename for label, block in BLOCKS.items()]))]
    file_index = {d["f"]: idx for idx, d in enumerate(file_json)}
    block_json = [{"n": label, "f": file_index[block.filename], "l": block.linenr} for label, block in BLOCKS.items()]
    block_index = {d["n"]: idx for idx, d in enumerate(block_json)}
    for label, block in BLOCKS.items():
        if block.uses:
            block_json[block_index[label]]["u"] = [block_index[b.label] for b in block.uses]
    for f in file_json:
        f["f"] = os.path.relpath(f["f"], BASEPATH)
        os.makedirs(os.path.dirname(os.path.join(args.output, f["f"])), exist_ok=True)
        shutil.copy(os.path.join(BASEPATH, f["f"]), os.path.join(args.output, f["f"]))
    json.dump({"blocks": block_json, "files": file_json}, open(os.path.join(args.output, "calltree.json"), "wt"), separators=(',',':'))
