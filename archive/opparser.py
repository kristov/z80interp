#!/usr/bin/env python

import sys
import re
import sqlite3

one = re.compile(r'^([a-z]+)$')
two = re.compile(r'^([a-z]+)\s+([0-9a-z\+\(\)]+)$')
tre = re.compile(r'^([a-z]+)\s+([0-9a-z\+\(\)]+)\s*,\s*([0-9a-z\+\(\)\']+)$')
fur = re.compile(r'^([a-z]+)\s+([0-9a-z\+\(\)]+)\s*,\s*([0-9a-z\+\(\)\']+)\s*,\s*([0-9a-z\+\(\)\']+)$')
ref = re.compile(r'^\(([0-9a-z\+]+)\)')
xyr = re.compile(r'^(ix|iy)\+0x0e$')
reg = re.compile(r'^[abcdefhilmnoprspxyz]{1,3}$')
num = re.compile(r'^[0-7]{1}$')
rst = re.compile(r'^[0-9]{2}h$')
bop = re.compile(r'^(?:res|set|bit)$')

conn = sqlite3.connect('z80.db')
c = conn.cursor()

c.execute('''CREATE TABLE IF NOT EXISTS op (op_id INTEGER PRIMARY KEY, name TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS opd (opd_id INTEGER PRIMARY KEY, op_id INTEGER, nr_args INTEGER)''')
c.execute('''CREATE TABLE IF NOT EXISTS oparg (oparg_id INTEGER PRIMARY KEY, name TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS opd_oparg (opd_id INTEGER, oparg_id INTEGER, pos INTEGER, indirect INTEGER)''')
c.execute('''DELETE FROM opd''')
c.execute('''DELETE FROM opd_oparg''')

def get_oparg(c, arg):
    c.execute('SELECT oparg_id, name FROM oparg WHERE name = ?', (arg,))
    row = c.fetchone()
    if row:
        return row[0]
    c.execute('INSERT INTO oparg (name) VALUES (?)', (arg,))
    return c.lastrowid

def parse_arg(c, op, arg):
    isref = 0
    m = ref.match(arg)
    if m:
        isref = 1
        arg = m.group(1)
    if arg == "0x0e":
        return isref, get_oparg(c, "const8")
    if arg == "0x0f0f":
        return isref, get_oparg(c, "const16")
    if arg == "af'":
        return isref, get_oparg(c, arg)
    m = xyr.match(arg)
    if m:
        return isref, get_oparg(c, m.group(1) + "+const8")
    m = reg.match(arg)
    if m:
        return isref, get_oparg(c, arg)
    m = rst.match(arg)
    if m:
        return isref, get_oparg(c, arg)
    m = num.match(arg)
    if m:
        m = bop.match(op)
        if m:
            arg = "bit"
        else:
            arg = "num"
        return isref, get_oparg(c, arg)
    raise Exception(arg)

def get_op(c, op):
    c.execute('SELECT op_id, name FROM op WHERE name = ?', (op,))
    row = c.fetchone()
    if row:
        return row[0]
    c.execute('INSERT INTO op (name) VALUES (?)', (op,))
    return c.lastrowid

def get_opd(c, op_id, nr_args):
    c.execute('INSERT INTO opd (op_id, nr_args) VALUES (?,?)', (op_id, nr_args,))
    return c.lastrowid

def insert_opd_oparg(c, opd_id, oparg_id, pos, indirect):
    c.execute('''INSERT INTO opd_oparg (opd_id,oparg_id,pos,indirect) VALUES (?,?,?,?)''', (opd_id, oparg_id, pos, indirect,))
    return

for line in sys.stdin:
    line = line.strip()
    m = fur.match(line)
    if m:
        op_id = get_op(c, m.group(1))
        opd_id = get_opd(c, op_id, 3)
        isref1, arg1 = parse_arg(c, m.group(1), m.group(2))
        isref2, arg2 = parse_arg(c, m.group(1), m.group(3))
        isref3, arg3 = parse_arg(c, m.group(1), m.group(4))
        insert_opd_oparg(c, opd_id, arg1, 0, isref1)
        insert_opd_oparg(c, opd_id, arg2, 1, isref2)
        insert_opd_oparg(c, opd_id, arg3, 2, isref3)
        continue
    m = tre.match(line)
    if m:
        op_id = get_op(c, m.group(1))
        opd_id = get_opd(c, op_id, 2)
        isref1, arg1 = parse_arg(c, m.group(1), m.group(2))
        isref2, arg2 = parse_arg(c, m.group(1), m.group(3))
        insert_opd_oparg(c, opd_id, arg1, 0, isref1)
        insert_opd_oparg(c, opd_id, arg2, 1, isref2)
        continue
    m = two.match(line)
    if m:
        op_id = get_op(c, m.group(1))
        opd_id = get_opd(c, op_id, 1)
        isref1, arg1 = parse_arg(c, m.group(1), m.group(2))
        insert_opd_oparg(c, opd_id, arg1, 0, isref1)
        continue
    m = one.match(line)
    if m:
        op_id = get_op(c, m.group(1))
        opd_id = get_opd(c, op_id, 0)
        continue
    raise Exception(line)

conn.commit()
conn.close()
