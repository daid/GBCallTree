import re
import os
import json
import glob


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
        ('HEX', r'\$[0-9A-Fa-f]+'),
        ('GFX', r'\`[0-3]+'),
        ('BIN', r'\%[01]+'),
        ('ASSIGN', r':='),
        ('COMMENT', r';[^\n]*'),
        ('LABEL', r':+'),
        ('CURSOR', r'@'),
        ('DIRECTIVE', r'#[A-Za-z_]+'),
        ('STRING', '[a-zA-Z]?"[^"]*"'),
        ('ID', r'\.?[A-Za-z_][A-Za-z0-9_\.#]*'),
        ('OP', r'==|>=|<=|<<|>>|[+\-*/,\(\)!=<>\|&\^%]'),
        ('MACROPARAM', r'\\[0-9]+'),
        ('REFOPEN', r'\['),
        ('REFCLOSE', r'\]'),
        ('NEWLINE', r'\n'),
        ('SKIP', r'[ \t]+'),
        ('MISMATCH', r'.'),
    ]))

    def __init__(self, code):
        self.__tokens = []
        line_num = 1
        for mo in self.TOKEN_REGEX.finditer(code):
            kind = mo.lastgroup
            value = mo.group()
            if kind == 'MISMATCH':
                print(code.split("\n")[line_num-1])
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
                if kind == 'NEWLINE':
                    line_num += 1
        self.__tokens.append(Token('NEWLINE', '\n', line_num))

    def peek(self):
        return self.__tokens[0]

    def pop(self):
        return self.__tokens.pop(0)

    def expect(self, kind, value=None):
        pop = self.pop()
        if not pop.isA(kind, value):
            if value is not None:
                raise SyntaxError("%s != %s:%s" % (pop, kind, value))
            raise SyntaxError("%s != %s" % (pop, kind))
        return pop

    def __bool__(self):
        return bool(self.__tokens)

    def pushMacro(self, tokens, args):
        to_add = []
        for t in tokens:
            if t.isA('MACROPARAM'):
                if int(t.value[1:])-1 < len(args):
                    for a in args[int(t.value[1:])-1]:
                        a.line_nr = -1
                        to_add.append(a)
            elif t.isA('ID', '_NARG'):
                to_add.append(Token('NUMBER', len(args), -1))
            else:
                t.line_nr = -1
                to_add.append(t)
        self.__tokens = to_add + self.__tokens
