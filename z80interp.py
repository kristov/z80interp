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
            "sub1": self.SUB,
            "ret0": self.RET
        }
        self.patterns = [
            re.compile(r'^\s+(ccf|cpd|cpdr|cpi|cpir|cpl|daa|di|ei|exx|halt|ind|indr|ini|inir|ldd|lddr|ldi|ldir|neg|nop|otdr|otir|outd|outi|ret|reti|retn|rla|rlca|rld|rra|rrca|rrd|scf)$'),
            re.compile(r'^\s+(adc|sbc)\s+(hl)\s*,\s*(bc|de|hl|sp)$'),
            re.compile(r'^\s+(adc|add|sbc)\s+(a)\s*,\s*(\(hl\))$'),
            re.compile(r'^\s+(adc|add|sbc)\s+(a)\s*,\s*(\(ix\+[a-z0-9\_]+\))$'),
            re.compile(r'^\s+(adc|add|sbc)\s+(a)\s*,\s*(\(iy\+[a-z0-9\_]+\))$'),
            re.compile(r'^\s+(adc|add|sbc)\s+(a)\s*,\s*([a-z0-9\_]+)$'),
            re.compile(r'^\s+(adc|add|sbc)\s+(a)\s*,\s*(a|b|c|d|e|h|l|ixh|ixl|iyh|iyl)$'),
            re.compile(r'^\s+(add)\s+(hl|ix|iy)\s*,\s*(bc|de|hl|sp)$'),
            re.compile(r'^\s+(add)\s+(ix)\s*,\s*(ix)$'),
            re.compile(r'^\s+(add)\s+(iy)\s*,\s*(iy)$'),
            re.compile(r'^\s+(and|cp|or|sub|xor)\s+(\(hl\))$'),
            re.compile(r'^\s+(and|cp|or|sub|xor)\s+(\(ix\+[a-z0-9\_]+\))$'),
            re.compile(r'^\s+(and|cp|or|sub|xor)\s+(\(iy\+[a-z0-9\_]+\))$'),
            re.compile(r'^\s+(and|cp|or|sub|xor)\s+([a-z0-9\_]+)$'),
            re.compile(r'^\s+(and|cp|or|sub|xor)\s+(a|b|c|d|e|h|l|ixh|ixl|iyh|iyl)$'),
            re.compile(r'^\s+(bit|res|set)\s+([0-7])\s*,\s*(\(hl\))$'),
            re.compile(r'^\s+(bit|res|set)\s+([0-7])\s*,\s*(\(ix\+[a-z0-9\_]+\))$'),
            re.compile(r'^\s+(bit|res|set)\s+([0-7])\s*,\s*(\(iy\+[a-z0-9\_]+\))$'),
            re.compile(r'^\s+(bit|res|set)\s+([0-7])\s*,\s*(\(ix\+[a-z0-9\_]+\))\s*,\s*(a|b|c|d|e|h|l)$'),
            re.compile(r'^\s+(bit|res|set)\s+([0-7])\s*,\s*(\(iy\+[a-z0-9\_]+\))\s*,\s*(a|b|c|d|e|h|l)$'),
            re.compile(r'^\s+(bit|res|set)\s+([0-7])\s*,\s*(a|b|c|d|e|h|l)$'),
            re.compile(r'^\s+(call|jp)\s+([a-z0-9\_]+)$'),
            re.compile(r'^\s+(call|jp)\s+(c|m|nc|nz|p|pe|po|z)\s*,\s*([a-z0-9\_]+)$'),
            re.compile(r'^\s+(dec|inc)\s+(\(hl\))$'),
            re.compile(r'^\s+(dec|inc)\s+(\(ix\+[a-z0-9\_]+\))$'),
            re.compile(r'^\s+(dec|inc)\s+(\(iy\+[a-z0-9\_]+\))$'),
            re.compile(r'^\s+(dec|inc)\s+(a|b|c|d|e|h|l|ixh|ixl|iyh|iyl|bc|de|sp|hl|ix|iy)$'),
            re.compile(r'^\s+(djnz|jr)\s+([a-z0-9\_]+)$'),
            re.compile(r'^\s+(ex)\s+(\(sp\))\s*,\s*(hl|ix|iy)$'),
            re.compile(r'^\s+(ex)\s+(af)\s*,\s*(af\')$'),
            re.compile(r'^\s+(ex)\s+(de)\s*,\s*(hl)$'),
            re.compile(r'^\s+(im)\s+([0-2])$'),
            re.compile(r'^\s+(in)\s+(\(c\))$'),
            re.compile(r'^\s+(in)\s+(a)\s*,\s*(\([a-z0-9\_]+\))$'),
            re.compile(r'^\s+(in)\s+(a|b|c|d|e|h|l)\s*,\s*(\(c\))$'),
            re.compile(r'^\s+(jp)\s+(\(hl\)|\(ix\)|\(iy\))$'),
            re.compile(r'^\s+(jr)\s+(c|nc|nz|z)\s*,\s*([a-z0-9\_]+)$'),
            re.compile(r'^\s+(ld)\s+(\([a-z0-9\_]+\))\s*,\s*(a)$'),
            re.compile(r'^\s+(ld)\s+(\([a-z0-9\_]+\))\s*,\s*(bc|de|hl|ix|iy|sp)$'),
            re.compile(r'^\s+(ld)\s+(\(bc\)|\(de\))\s*,\s*(a)$'),
            re.compile(r'^\s+(ld)\s+(\(hl\))\s*,\s*([a-z0-9\_]+)$'),
            re.compile(r'^\s+(ld)\s+(\(hl\))\s*,\s*(a|b|c|d|e|h|l)$'),
            re.compile(r'^\s+(ld)\s+(\(ix\+[a-z0-9\_]+\))\s*,\s*([a-z0-9\_]+)$'),
            re.compile(r'^\s+(ld)\s+(\(ix\+[a-z0-9\_]+\))\s*,\s*(a|b|c|d|e|h|l)$'),
            re.compile(r'^\s+(ld)\s+(\(iy\+[a-z0-9\_]+\))\s*,\s*([a-z0-9\_]+)$'),
            re.compile(r'^\s+(ld)\s+(\(iy\+[a-z0-9\_]+\))\s*,\s*(a|b|c|d|e|h|l)$'),
            re.compile(r'^\s+(ld)\s+(a)\s*,\s*(\([a-z0-9\_]+\))$'),
            re.compile(r'^\s+(ld)\s+(a)\s*,\s*(\(bc\)|\(de\))$'),
            re.compile(r'^\s+(ld)\s+(a)\s*,\s*(a|b|c|d|e|h|l|ixh|ixl|iyh|iyl|i|r)$'),
            re.compile(r'^\s+(ld)\s+(a|b|c|d|e|h|l)\s*,\s*(\(hl\))$'),
            re.compile(r'^\s+(ld)\s+(a|b|c|d|e|h|l)\s*,\s*(\(ix\+[a-z0-9\_]+\))$'),
            re.compile(r'^\s+(ld)\s+(a|b|c|d|e|h|l)\s*,\s*(\(iy\+[a-z0-9\_]+\))$'),
            re.compile(r'^\s+(ld)\s+(a|b|c|d|e|h|l)\s*,\s*([a-z0-9\_]+)$'),
            re.compile(r'^\s+(ld)\s+(b|c|d|e|h)\s*,\s*(a|b|c|d|e|h|l|ixh|ixl|iyh|iyl)$'),
            re.compile(r'^\s+(ld)\s+(l)\s*,\s*(a|b|c|d|e|h|l)$'),
            re.compile(r'^\s+(ld)\s+(bc|de|hl|ix|iy|sp)\s*,\s*(\([a-z0-9\_]+\))$'),
            re.compile(r'^\s+(ld)\s+(bc|de|hl|ix|iy|sp)\s*,\s*([a-z0-9\_]+)$'),
            re.compile(r'^\s+(ld)\s+(ixh|ixl|iyh|iyl)\s*,\s*(a|b|c|d|e)$'),
            re.compile(r'^\s+(ld)\s+(ixh|ixl)\s*,\s*(ixh|ixl)$'),
            re.compile(r'^\s+(ld)\s+(iyh|iyl)\s*,\s*(iyh|iyl)$'),
            re.compile(r'^\s+(ld)\s+(ixh|ixl|iyh|iyl)\s*,\s*([a-z0-9\_]+)$'),
            re.compile(r'^\s+(ld)\s+(i|r)\s*,\s*(a)$'),
            re.compile(r'^\s+(ld)\s+(sp)\s*,\s*(hl|ix|iy)$'),
            re.compile(r'^\s+(out)\s+(\([a-z0-9\_]+\))\s*,\s*(a)$'),
            re.compile(r'^\s+(out)\s+(\(c\))\s*,\s*(0)$'),
            re.compile(r'^\s+(out)\s+(\(c\))\s*,\s*(a|b|c|d|e|h|l)$'),
            re.compile(r'^\s+(pop|push)\s+(af|bc|de|hl|ix|iy)$'),
            re.compile(r'^\s+(ret)\s+(c|m|nc|nz|p|pe|po|z)$'),
            re.compile(r'^\s+(rl|rlc|rr|rrc|sla|sll|sra|srl)\s+(\(hl\))$'),
            re.compile(r'^\s+(rl|rlc|rr|rrc|sla|sll|sra|srl)\s+(\(ix\+[a-z0-9\_]+\))$'),
            re.compile(r'^\s+(rl|rlc|rr|rrc|sla|sll|sra|srl)\s+(\(iy\+[a-z0-9\_]+\))$'),
            re.compile(r'^\s+(rl|rlc|rr|rrc|sla|sll|sra|srl)\s+(\(ix\+[a-z0-9\_]+\))\s*,\s*(a|b|c|d|e|h|l)$'),
            re.compile(r'^\s+(rl|rlc|rr|rrc|sla|sll|sra|srl)\s+(\(iy\+[a-z0-9\_]+\))\s*,\s*(a|b|c|d|e|h|l)$'),
            re.compile(r'^\s+(rl|rlc|rr|rrc|sla|sll|sra|srl)\s+(a|b|c|d|e|h|l)$'),
            re.compile(r'^\s+(rst)\s+(00h|08h|10h|18h|20h|28h|30h|38h)$'),
        ]
        self.memory = array.array('i',(0,)*65536)

    def LD(self, args):
        self.parseargs(args)
        return

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
        return
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
        if arg1[0] == "REG16":
            # TODO
            return

    def SUB(self, arg1):
        return

    def JP1(self, arg1):
        self.message = "JP1 (%s)" % (arg1[0])
        return

    def JP2(self, arg1, arg2):
        self.message = "JP2 (%s %s)" % (arg1[0], arg2[0])
        return

    def RET(self):
        return

    def darg(self, arg):
        val = arg[1]
        if re.match(r'^(?:c|m|nc|nz|p|pe|po|z)$', val):
            return ['FLAG', val]
        if re.match(r'^(?:a|b|c|d|e|h|l|ixh|ixl|iyh|iyl)$', val):
            return ['REG8', val]
        if re.match(r'^(?:af|bc|de|hl|ix|iy|sp)$', val):
            return ['REG16', val]
        if re.match(r'^(?:0|1|2|3|4|5|6|7)$', val):
            return ['BIT', val]
        if re.match(r'^0x[0-9a-f]{2}$', val):
            return ['CONST8', int(val, 16)]
        if re.match(r'^0x[0-9a-f]{4}$', val):
            return ['CONST16', int(val, 16)]
        m = re.match(r'^([0-9a-f]{2})h$', val)
        if m:
            return ['CONST8', int("0x" + val, 16)]
        m = re.match(r'^([0-9a-f]{4})h$', val)
        if m:
            return ['CONST16', int("0x" + val, 16)]
        if re.match(r'^i(?:x|y)\+0x[0-9a-f]{2}$', val):
            return ['INHEX8', val]
        if re.match(r'^i(?:x|y)\+[0-9a-f]{2}h$', val):
            return ['INHEX8', val]
            #return ["CONST8", int(arg, 16)]
            #val = int(arg, 16)
            #U = (val >> 8) & 0xff
            #L = val & 0xff
            #return ["CONST16", U, L]
            #val = self.getvar(arg)
            #if not val:
            #    return ["LABEL", arg]
            #U = (val >> 8) & 0xff
            #L = val & 0xff
            #return ["CONST16", U, L]
        self.message = "NOPE: %s %s" % (arg[0], val)

    def getvar(self, var):
        val = self.vars.get(var)
        if val:
            return val
        self.message = "var: %s not found" % (var)

    def getop(self, op):
        func = self.ops.get(op)
        if func:
            return func
        self.message = "unknown op: %s" % (op)

    def decode0(self, op):
        op = op[1] + "0"
        func = self.getop(op)
        if func:
            func()

    def decode1(self, op, arg1):
        op = op[1] + "1"
        func = self.getop(op)
        if func:
            args = self.parseargs(op, [arg1])
            func(args)

    def decode2(self, op, arg1, arg2):
        op = op[1] + "2"
        func = self.getop(op)
        if func:
            args = self.parseargs(op, [arg1, arg2])
            func(args)

    def set_var(self, name, val):
        m = re.match(r'^0x([0-9a-f]+)$', val)
        if m:
            val = int(val, 16)
        self.vars[name] = val

    def deref(self, reg1, reg2):
        U = self.registers.get(reg1).get()
        L = self.registers.get(reg2).get()
        return (U << 8) | L

    def eval(self, line):
        idx = 0
        matches = ()
        found = None
        for pattern in self.patterns:
            found = pattern.match(line)
            if not found:
                idx += 1
                continue
            matches = found.groups()
            self.message = "%d" % (len(matches))
            break
        if not found:
            raise Exception(line)
        return 0

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
