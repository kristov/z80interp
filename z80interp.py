#!/usr/bin/env python

import sys
import curses
import signal
import math
import re

class Z80Machine:
    def __init__(self):
        self.message = ""
        return
    def eval(self, line):
        m = re.match(r'^\s+([a-z]+\s+[a-z0-9_]+)\s*,\s*([a-z0-9_]+)', line)
        if m:
            op = m.group(1)
            arg1 = m.group(2)
            self.message = "op[%s] arg1[%s]" % (op, arg1)
            return 0
        m = re.match(r'^\s+([a-z]+\s+[a-z0-9_]+)', line)
        if m:
            op = m.group(1)
            self.message = "op[%s]" % (op)
            return 0
        m = re.match(r'^\s+([a-z]+)', line)
        if m:
            op = m.group(1)
            self.message = "op[%s]" % (op)
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
        m = re.match(r'^(\s+)([a-z]+)(\s+)([a-z0-9_]+)(\s*,\s*)([a-z0-9_]+)(\s*)(;.+)', line)
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
        m = re.match(r'^(\s+)([a-z]+)(\s+)([a-z0-9_]+)(\s*,\s*)([a-z0-9_]+)\s*', line)
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
        return [[self.CSPACE, line]]

    def step(self):
        not_found = 1
        while not_found:
            not_found = self.machine.eval(self.lines[self.line])
            if self.line + 1 == len(self.lines):
                return
            self.line += 1
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
#            self.stdscr.addstr(y, 0, line, color)
            y += 1
        if self.machine.message:
            self.stdscr.addstr(self.h, 0, self.machine.message)
        self.stdscr.refresh()

    def run(self):
        self.line = 0
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
