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
            "ld": self.LD,
            "or": self.OR
        }
        self.memory = array.array('i',(0,)*65536)

    def LD(self, arg1, arg2):
        m = re.match(r'^([hbd])([lce])$', arg1)
        if m:
            val = self.evalv(arg2)
            U = (val >> 8) & 0xff
            L = val & 0xff
            self.registers.get(m.group(1)).set(U)
            self.registers.get(m.group(2)).set(L)
            return
        self.registers.get(arg1).set(self.evalv(arg2))
        return

    def OR(self, arg):
        self.message = "arg: %s" % (arg)

    def run1(self, op):
        func = self.ops.get(op)
        if func:
            func()

    def run2(self, op, arg):
        func = self.ops.get(op)
        if func:
            func(arg)

    def run3(self, op, arg1, arg2):
        func = self.ops.get(op)
        if func:
            func(arg1, arg2)

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
        val = (U << 8) | L
        return self.memory[val]

    def eval(self, line):
        m = re.match(r'^\s+([a-z]+)\s+([a-z0-9_]+)\s*,\s*([a-z0-9_\(\)]+)', line)
        if m:
            self.run3(m.group(1), m.group(2), m.group(3))
            return 0
        m = re.match(r'^\s+([a-z]+)\s+([a-z0-9_]+)', line)
        if m:
            self.run2(m.group(1), m.group(2))
            return 0
        m = re.match(r'^\s+([a-z]+)', line)
        if m:
            self.run1(m.group(1))
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
        self.stdscr.addstr(y + 1, x, "h: %d" % (self.machine.registers["h"].get()))
        self.stdscr.addstr(y + 2, x, "l: %d" % (self.machine.registers["l"].get()))
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
