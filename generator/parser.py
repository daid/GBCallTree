import re
import os
import json
import glob
from globals import DEFINES


def parseExpr(tok):
    return parseAddSub(tok)
def parseAddSub(tok):
    t = parseFactor(tok)
    p = tok.peek()
    if p.isA('OP', '+'):
        tok.pop()
        return t + parseAddSub(tok)
    if p.isA('OP', '-'):
        tok.pop()
        return int(t) - parseAddSub(tok)
    if p.isA('OP', '&'):
        tok.pop()
        return t & parseAddSub(tok)
    if p.isA('OP', '|'):
        tok.pop()
        return t | parseAddSub(tok)
    if p.isA('OP', '^'):
        tok.pop()
        return t ^ parseAddSub(tok)
    return t
def parseFactor(tok):
    t = parseShift(tok)
    p = tok.peek()
    if p.isA('OP', '*'):
        tok.pop()
        return t * parseFactor(tok)
    if p.isA('OP', '/'):
        tok.pop()
        return t // parseFactor(tok)
    if p.isA('OP', '%'):
        tok.pop()
        return t % parseFactor(tok)
    return t
def parseShift(tok):
    t = parseCompare(tok)
    p = tok.peek()
    if p.isA('OP', '>>'):
        tok.pop()
        return t >> parseShift(tok)
    if p.isA('OP', '<<'):
        tok.pop()
        return t << parseShift(tok)
    return t
def parseCompare(tok):
    t = parseUnary(tok)
    p = tok.peek()
    if p.isA('OP', '=='):
        tok.pop()
        return t == parseCompare(tok)
    if p.isA('OP', '>='):
        tok.pop()
        return t >= parseCompare(tok)
    if p.isA('OP', '<='):
        tok.pop()
        return t <= parseCompare(tok)
    if p.isA('OP', '>'):
        tok.pop()
        return t > parseCompare(tok)
    if p.isA('OP', '<'):
        tok.pop()
        return t < parseCompare(tok)
    return t
def parseUnary(tok):
    p = tok.peek()
    if p.isA('OP', '-'):
        tok.pop()
        return -parseUnary(tok)
    if p.isA('OP', '!'):
        tok.pop()
        return not parseUnary(tok)
    if p.isA('OP', '('):
        tok.pop()
        res = parseExpr(tok)
        tok.expect('OP', ')')
        return res
    return parseValue(tok)
def parseValue(tok):
    global DEFINES
    t = tok.pop()
    if t.isA('ID', 'DEF'):
        tok.expect('OP', '(')
        t = tok.expect('ID')
        tok.expect('OP', ')')
        return t.value in DEFINES
    if t.isA('ID', 'STRLEN'):
        tok.expect('OP', '(')
        t = str(parseExpr(tok))
        tok.expect('OP', ')')
        return len(t)
    if t.isA('ID', 'STRCMP'):
        tok.expect('OP', '(')
        s1 = str(parseExpr(tok))
        tok.expect('OP', ',')
        s2 = str(parseExpr(tok))
        tok.expect('OP', ')')
        if s1 < s2:
            return -1
        if s1 > s2:
            return 1
        return 0
    if t.isA('ID', 'STRSUB'):
        tok.expect('OP', '(')
        s = str(parseExpr(tok))
        tok.expect('OP', ',')
        start = parseExpr(tok)
        length = len(s)
        if tok.peek().isA('OP', ','):
            tok.pop()
            length = parseExpr(tok)
        tok.expect('OP', ')')
        return s[start-1:start+length-1]
    if t.isA('ID') and t.value in {'HIGH', 'LOW'}:
        tok.expect('OP', '(')
        res = parseExpr(tok)
        tok.expect('OP', ')')
        return res
    if t.isA('NUMBER'):
        return t.value
    if t.isA('CURSOR'):
        return 0
    if t.isA('ID') and t.value in DEFINES:
        return DEFINES[t.value]
    if t.isA('STRING'):
        return 0
    if t.isA('ID'):
        print('?', t)
        return 0;
    raise SyntaxError(t)
