import re
import os
import json
import glob

import globals


def replaceSymIn(m):
    value = m.group(1)
    if value in globals.DEFINES:
        return str(globals.DEFINES[value])
    print("Unknown symbol interpolation:", value)
    return ""


class Token:
    def __init__(self, kind, value, line_nr):
        self.kind = kind
        self.value = value
        self.line_nr = line_nr

    def isA(self, kind, value=None):
        if (isinstance(self.value, str)):
            return self.kind == kind and (value is None or value.upper() == self.value.upper())
        return self.kind == kind and (value is None or value == self.value)

    def __repr__(self):
        return "[%s:%s:%d]" % (self.kind, self.value, self.line_nr)


class Tokenizer:
    TOKEN_REGEX = re.compile('|'.join('(?P<%s>%s)' % pair for pair in [
        ('NUMBER', r'\d+(\.\d*)?'),
        ('HEX', r'[\$#][0-9A-Fa-f]+'),
        ('GFX', r'\`[0-3]+'),
        ('BIN', r'\%[01]+'),
        ('ASSIGN', r':='),
        ('COMMENT', r';[^\n]*'),
        ('LABEL', r':+'),
        ('CURSOR', r'@'),
        ('DIRECTIVE', r'#[A-Za-z_]+'),
        ('MACROARG', r'\\[0-9]'),
        ('STRING', '[a-zA-Z]?"(?:[^"]|\\")*"'),
        ('ID', r'\.?[A-Za-z_][A-Za-z0-9_\.#]*'),
        ('OP', r'&&|\|\||==|!=|>=|<=|<<|>>|[+\-*/,\(\)!=<>\|&\^%~]'),
        ('REFOPEN', r'\['),
        ('REFCLOSE', r'\]'),
        ('NEWLINE', r'\n'),
        ('SKIP', r'[ \t]+'),
        ('MISMATCH', r'.'),
    ]))

    def __init__(self, code):
        self.__lines = []
        self.__macros = []
        self.__counter = 0
        for line_num, line in enumerate(code.split("\n")):
            self.__lines.append(("", line_num + 1, line))
        self.__tokens = []

    def __decodeNextLine(self):
        if self.__macros:
            if not self.__macros[0][0]:
                self.__macros.pop(0)
                return self.__decodeNextLine()
            file, line_num, line = self.__macros[0][0].pop(0)
            while line.endswith('\\'):
                line = line[:-1] + self.__macros[0][0].pop(0)[2]
            args = self.__macros[0][1]
            def tstr(t):
                if t.kind == "STRING":
                    return "\"%s\"" % (t.value)
                return str(t.value)
            def f(m):
                m = m.group(0)
                if m == '\#':
                    return ", ".join(["".join([tstr(a) for a in arg]) for arg in args])
                if m == '\@':
                    self.__counter += 1
                    return "__%d" % (self.__counter)
                if args:
                    return "".join([tstr(a) for a in args[int(m[1:])-1]])
                return ""
            line = re.sub(r'\\[0-9#@]', f, line)
        else:
            file, line_num, line = self.__lines.pop(0)
            while line.endswith('\\'):
                line = line[:-1] + self.__lines.pop(0)[2]
        # print(file, line_num, line)
        line = re.sub(r'{([^}]+)}', replaceSymIn, line)
        for mo in self.TOKEN_REGEX.finditer(line):
            kind = mo.lastgroup
            value = mo.group()
            if kind == 'MISMATCH':
                print(line)
                raise RuntimeError("Syntax error on line: %d: %s\n%s", line_num, value)
            elif kind == 'SKIP':
                pass
            elif kind == 'COMMENT':
                pass
            else:
                if kind == 'NUMBER':
                    if '.' in value:
                        value = float(value)
                    else:
                        value = int(value)
                elif kind == 'HEX':
                    value = int(value[1:], 16)
                    kind = 'NUMBER'
                elif kind == 'GFX':
                    value = int(value[1:], 4)
                    kind = 'NUMBER'
                elif kind == 'BIN':
                    value = int(value[1:], 2)
                    kind = 'NUMBER'
                elif kind == 'STRING':
                    value = value[1:-1]
                self.__tokens.append(Token(kind, value, line_num))
        self.__tokens.append(Token('NEWLINE', '\n', line_num))

    def peek(self):
        if not self.__tokens:
            self.__decodeNextLine()
        return self.__tokens[0]

    def pop(self):
        if not self.__tokens:
            self.__decodeNextLine()
        return self.__tokens.pop(0)

    def popRawLine(self):
        assert not self.__tokens
        return self.__lines.pop(0)

    def expect(self, kind, value=None):
        pop = self.pop()
        if not pop.isA(kind, value):
            if value is not None:
                raise SyntaxError("%s != %s:%s" % (pop, kind, value))
            raise SyntaxError("%s != %s" % (pop, kind))
        return pop

    def __bool__(self):
        return bool(self.__lines) or bool(self.__tokens)

    def pushMacro(self, lines, args):
        self.__macros.insert(0, (lines.copy(), args))
        return

    def shiftMacroArgs(self, amount):
        for n in range(amount):
            self.__macros[0][1].pop(0)


if __name__ == "__main__":
    print("Testing tokenizer.")
    Tokenizer("$10").expect("NUMBER", 16)
    t = Tokenizer(";comment\n100")
    t.expect("NEWLINE")
    t.expect("NUMBER", 100)

    t = Tokenizer("._{TEST}_123")
    globals.DEFINES["TEST"] = "BLA"
    t.expect("ID", "._BLA_123")

    t = Tokenizer("")
    t.pushMacro([("", -1, r"\1"), ("", -1, r"\1")], [[Token("NUMBER", 1, -1)], [Token("NUMBER", 2, -1)]])
    t.expect("NUMBER", 1)
    t.expect("NEWLINE")
    t.shiftMacroArgs(1)
    t.expect("NUMBER", 2)
