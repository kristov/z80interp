#!/usr/bin/env python

import sys
import curses
import signal
import math
import re
import collections
import array


class Z80Reg:
    """For storing the current and past values for a register"""

    def __init__(self):
        self.history = collections.deque([0xff], 100)

    def set(self, value):
        """Set the value in a register with history"""
        self.history.appendleft(value)

    def get(self):
        """Gets the latest value in a register"""
        return self.history[0]

class Z80Machine:
    """Runnable instance of a Z80 CPU"""

    def __init__(self):
        self.message = ""
        self.vars = {}
        self.registers = {
            "a": Z80Reg(),
            "f": Z80Reg(),
            "b": Z80Reg(),
            "c": Z80Reg(),
            "d": Z80Reg(),
            "e": Z80Reg(),
            "h": Z80Reg(),
            "l": Z80Reg()
        }
        self.ops = {
            "ld2": self.LD,
            "or1": self.OR,
            "inc1": self.INC,
            "dec1": self.DEC,
            "jp1": self.JP1,
            "jp2": self.JP2,
            "sub1": self.SUB1,
            "ret0": self.RET0
        }
        self.memory = array.array('i',(0,)*65536)
        self.pat = {
            "hex8": re.compile(r'^0x[0-9a-f]{2}$'),
            "hex16": re.compile(r'^0x[0-9a-f]{4}$'),
            "idrr16": re.compile(r'^\(([hbd])([lce])\)$'),
            "idrc16": re.compile(r'^\((0x[0-9a-f]{4})\)$'),
            "reg8": re.compile(r'^[afbcdehl]$'),
            "reg16": re.compile(r'^([hbd])([lce])$'),
            "label": re.compile(r'^[a-z0-9_]+')
        }

    def LD(self, arg1, arg2):
        if arg1[0] == "REG16":
            if arg2[0] == "REG16": # ld hl,de
                self.registers.get(arg1[1]).set(self.registers.get(arg2[1]))
                self.registers.get(arg1[2]).set(self.registers.get(arg2[2]))
                return
            if arg2[0] == "IDRC16": # ld hl,(**)
                L = self.memory[arg2[1]]
                U = self.memory[arg2[1] + 1]
                self.registers.get(arg1[1]).set(U)
                self.registers.get(arg1[2]).set(L)
                return
            if arg2[0] == "CONST16": # ld hl,**
                self.registers.get(arg1[1]).set(arg2[1])
                self.registers.get(arg1[2]).set(arg2[2])
                return
        if arg1[0] == "IDRR16":
            if arg2[0] == "REG8": # ld (hl),a
                addr = self.deref(arg1[1], arg1[2])
                self.memory[addr] = self.registers.get(arg2[1])
                return
            if arg2[0] == "CONST8": # ld (hl),*
                addr = self.deref(arg1[1], arg1[2])
                self.memory[addr] = arg2[1]
                return
        if arg1[0] == "IDRC16":
            if arg2[0] == "REG8": # ld (**),a
                self.memory[arg2[1]] = self.registers.get(arg2[1])
                return
            if arg2[0] == "REG16": # ld (**),hl
                U = self.registers.get(arg2[1])
                L = self.registers.get(arg2[2])
                self.memory[arg1[1]] = (U << 8) | L
                return
        if arg1[0] == "REG8":
            if arg2[0] == "REG8": # ld l,a
                self.registers.get(arg1[1]).set(self.registers.get(arg2[1]).get())
                return
            if arg2[0] == "IDRR16": # ld a,(hl)
                addr = self.deref(arg2[1], arg2[2])
                self.registers.get(arg1[1]).set(self.memory[addr])
                return
            if arg2[0] == "IDRC16": # ld a,(**)
                self.registers.get(arg1[1]).set(self.memory[arg2[1]])
                return
            if arg2[0] == "CONST8": # ld a,*
                self.registers.get(arg1[1]).set(arg2[1])
                return
        self.message = "invald LD (%s %s)" % (arg1[0], arg2[0])
        return

    def OR(self, arg1):
        if arg1[0] == "REG8": # or b
            areg = self.registers.get("a")
            val = self.registers.get(arg1[1]).get()
            areg.set(areg.get()|val)
            # if zero set zero flag
            return
        if arg1[0] == "INDIR": # or (hl)
            addr = self.deref(arg1[1], arg1[2])
            val = self.memory[addr]
            a = self.get_reg("a")|val
            self.set_reg("a", a)
            return
        self.message = "invald OR (%s)" % (arg[0])

    def INC(self, arg1):
        if arg1[0] == "REG8":
            val = self.registers.get(arg1[1]).get()
            val += 1
            self.registers.get(arg1[1]).set(val)
            return
        if arg1[0] == "REG16":
            # TODO
            return
        return

    def DEC(self, arg1):
        if arg1[0] == "REG8":
            val = self.registers.get(arg1[1]).get()
            val -= 1
            self.registers.get(arg1[1]).set(val)
            return

    def SUB(self, arg1):
        return

    def JP1(self, arg1):
        return

    def JP2(self, arg1, arg2):
        return

    def darg(self, arg):
        if self.pat["reg8"].match(arg):
            return ['REG8', arg]
        m = self.pat["reg16"].match(arg)
        if m:
            return ['REG16', m.group(1), m.group(2)]
        if self.pat["hex8"].match(arg):
            return ["CONST8", int(arg, 16)]
        if self.pat["hex16"].match(arg):
            val = int(arg, 16)
            U = (val >> 8) & 0xff
            L = val & 0xff
            return ["CONST16", U, L]
        m = self.pat["idrr16"].match(arg)
        if m:
            return ["IDRR16", m.group(1), m.group(2)]
        m = self.pat["idrc16"].match(arg)
        if m:
            return ["IDRC16", m.group(1)]
        if self.pat["label"].match(arg):
            val = self.getvar(arg)
            if not val:
                return ["LABEL", arg]
            U = (val >> 8) & 0xff
            L = val & 0xff
            return ["CONST16", U, L]
        return ["ERROR", arg]

    def getvar(self, var):
        val = self.vars.get(var)
        if val:
            return val
        self.message = "var: %s not found" % (var)

    def getop(self, op, argc):
        op = op + argc
        func = self.ops.get(op)
        if func:
            return func
        self.message = "unknown op: %s" % (op)

    def decode0(self, op):
        func = self.getop(op, "0")
        if func:
            func()

    def decode1(self, op, arg):
        func = self.getop(op, "1")
        if func:
            func(self.darg(arg))

    def decode2(self, op, arg1, arg2):
        func = self.getop(op, "2")
        if func:
            func(self.darg(arg1), self.darg(arg2))

    def set_var(self, name, val):
        m = re.match(r'^0x([0-9a-f]+)$', val)
        if m:
            val = int(val, 16)
        self.vars[name] = val

    def evalv(self, val):
        m = re.match(r'^0x([0-9a-f]+)$', val)
        if m:
            return int(m.group(1), 16)
        m = re.match(r'\(([hbd])([lce])\)', val)
        if m:
            return self.deref(m.group(1), m.group(2))
        var = self.vars.get(val)
        if var:
            return var
        return val

    def deref(self, reg1, reg2):
        U = self.registers.get(reg1).get()
        L = self.registers.get(reg2).get()
        return (U << 8) | L

    def eval(self, line):
        m = re.match(r'^\s+([a-z]+)\s+([a-z0-9_]+)\s*,\s*([a-z0-9_\(\)]+)', line)
        if m:
            self.decode2(m.group(1), m.group(2), m.group(3))
            return 0
        m = re.match(r'^\s+([a-z]+)\s+([a-z0-9_]+)', line)
        if m:
            self.decode1(m.group(1), m.group(2))
            return 0
        m = re.match(r'^\s+([a-z]+)', line)
        if m:
            self.decode0(m.group(1))
            return 0
        m = re.match(r'^([a-z0-9_]+):\s+equ\s+([a-z0-9]+)$', line)
        if m:
            self.set_var(m.group(1), m.group(2))
            return 0
        self.message = ""
        return 1

class Z80Interp:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        curses.noecho()
        curses.cbreak()
        curses.curs_set(0)
        curses.start_color()
        curses.use_default_colors()
        self.h, self.w = self.stdscr.getmaxyx()
        self.h -= 1
        self.machine = Z80Machine()
        self.init_colors()

    def init_colors(self):
         curses.init_pair(1, curses.COLOR_WHITE, -1)
         curses.init_pair(2, curses.COLOR_CYAN, -1)
         curses.init_pair(3, curses.COLOR_GREEN, -1)
         curses.init_pair(4, curses.COLOR_YELLOW, -1)
         curses.init_pair(5, curses.COLOR_MAGENTA, -1)
         self.CSPACE = 1
         self.CCOMMENT = 2
         self.CLABEL = 3
         self.CCMD = 4
         self.CARG = 5

    def parse(self, line):
        m = re.match(r'^(\s+)([a-z]+)(\s+)([a-z0-9_]+)(\s*,\s*)([a-z0-9_\(\)]+)(\s*)(;.+)', line)
        if m:
            return [
                [self.CSPACE, m.group(1)],
                [self.CCMD, m.group(2)],
                [self.CSPACE, m.group(3)],
                [self.CCMD, m.group(4)],
                [self.CSPACE, m.group(5)],
                [self.CARG, m.group(6)],
                [self.CSPACE, m.group(7)],
                [self.CCOMMENT, m.group(8)]
            ]
        m = re.match(r'^(\s+)([a-z]+)(\s+)([a-z0-9_]+)(\s*,\s*)([a-z0-9_\(\)]+)', line)
        if m:
            return [
                [self.CSPACE, m.group(1)],
                [self.CCMD, m.group(2)],
                [self.CSPACE, m.group(3)],
                [self.CCMD, m.group(4)],
                [self.CSPACE, m.group(5)],
                [self.CARG, m.group(6)]
            ]
        m = re.match(r'^(\s+)([a-z]+)(\s+)([a-z0-9_]+)\s*', line)
        if m:
            return [
                [self.CSPACE, m.group(1)],
                [self.CCMD, m.group(2)],
                [self.CSPACE, m.group(3)],
                [self.CCMD, m.group(4)]
            ]
        m = re.match(r'^([a-z0-9_]+)(:)$', line)
        if m:
            return [
                [self.CLABEL, m.group(1)],
                [self.CCMD, m.group(2)]
            ]
        m = re.match(r'^([a-z0-9_]+)(:\s+equ\s+)([a-z0-9]+)$', line)
        if m:
            return [
                [self.CLABEL, m.group(1)],
                [self.CCMD, m.group(2)],
                [self.CARG, m.group(3)]
            ]
        return [[self.CSPACE, line]]

    def eval(self):
        return self.machine.eval(self.lines[self.line])

    def step(self):
        not_found = 1
        while not_found:
            self.line += 1
            not_found = self.eval()
            if self.line + 1 == len(self.lines):
                return
        return

    def key_press(self, c):
        if c == ord('s'):
            self.step()

    def calc_file_view(self):
        hh = int(self.h / 2)
        if (self.line <= hh):
            miny = 0
            maxy = self.h
        else:
            miny = self.line - hh
            maxy = miny + self.h
        return miny, maxy

    def draw_registers(self):
        x = self.w - 10
        y = 0
        self.stdscr.addstr(y + 0, x, "a: %d" % (self.machine.registers["a"].get()))
        self.stdscr.addstr(y + 1, x, "f: %d" % (self.machine.registers["f"].get()))
        self.stdscr.addstr(y + 2, x, "b: %d" % (self.machine.registers["b"].get()))
        self.stdscr.addstr(y + 3, x, "c: %d" % (self.machine.registers["c"].get()))
        self.stdscr.addstr(y + 4, x, "d: %d" % (self.machine.registers["d"].get()))
        self.stdscr.addstr(y + 5, x, "e: %d" % (self.machine.registers["e"].get()))
        self.stdscr.addstr(y + 6, x, "h: %d" % (self.machine.registers["h"].get()))
        self.stdscr.addstr(y + 7, x, "l: %d" % (self.machine.registers["l"].get()))
        return

    def draw(self):
        y = 0
        miny, maxy = self.calc_file_view()
        self.stdscr.clear()
        for idx in range(miny, maxy):
            if idx >= len(self.lines):
                break
            line = self.lines[idx]
            data = self.parse(line)
            color = curses.A_NORMAL
            if self.line == idx:
                color = curses.A_REVERSE
            if data:
                x = 0
                for part in data:
                    self.stdscr.addstr(y, x, part[1], curses.color_pair(part[0])|color)
                    x += len(part[1])
            y += 1
        if self.machine.message:
            self.stdscr.addstr(self.h, 0, self.machine.message)
        self.draw_registers()
        self.stdscr.refresh()

    def run(self):
        self.line = 0
        self.eval()
        self.draw()
        while True:
            c = self.stdscr.getch()
            if c == ord('q'):
                break
            self.key_press(c)
            self.draw()

    def run_file(self, filename):
        with open(filename) as f:
            self.lines = [line.rstrip() for line in f]
        self.run()

def siginth(signal_received, frame):
    sys.exit(0)

def main(stdscr):
    z8i = Z80Interp(stdscr)
    signal.signal(signal.SIGINT, siginth)
    filename = sys.argv[1]
    z8i.run_file(filename)

curses.wrapper(main)
