#!/usr/bin/env python

import sys
import curses
import signal
import math
import re

class Z80Machine:
    def __init__(self):
        return
    def eval(self, line):
        return
    def parse(self, line):
        m = re.match( r'^(\s+)([a-z]+)(\s+)([a-z]+)(\s*,\s*)([a-z0-9_]+)', line)
        if m:
            return [
                ['space', m.group(1)],
                ['cmd', m.group(2)],
                ['space', m.group(3)],
                ['cmd', m.group(4)],
                ['space', m.group(5)],
                ['arg', m.group(6)]
            ]
        return []

class Z80Interp:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        curses.noecho()
        curses.cbreak()
        self.h, self.w = self.stdscr.getmaxyx()
        self.h -= 1
        self.machine = Z80Machine()

    def init_colors(self):
         curses.init_pair(1, self.foreground, self.background)
         curses.init_pair(2, curses.COLOR_CYAN, self.background)
         curses.init_pair(3, curses.COLOR_GREEN, self.background)
         curses.init_pair(4, curses.COLOR_MAGENTA, self.background)
         curses.init_pair(5, curses.COLOR_YELLOW, self.foreground)
         self.CSPACE = 1
         self.CCOMMENT = 2
         self.CLABEL = 3
         self.CARG = 4

    def step(self):
        self.machine.eval(self.lines[self.line])
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
        self.stdscr.addstr(self.h, 0, "%d -> %d" % (miny, maxy), curses.A_REVERSE)
        for idx in range(miny, maxy):
            if idx >= len(self.lines):
                break
            line = self.lines[idx]
            data = self.machine.parse(line)
            if data:
                for part in data:
                    ...
            color = curses.A_NORMAL
            if self.line == idx:
                color = curses.A_REVERSE
            self.stdscr.addstr(y, 0, line, color)
            y += 1
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
