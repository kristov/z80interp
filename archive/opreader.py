#!/usr/bin/env python

import sys
import re
import sqlite3

conn = sqlite3.connect('z80.db')
c = conn.cursor()

opd = {}
for row in c.execute('SELECT od.opd_id, o.name, oa.name, odoa.pos, odoa.indirect FROM opd_oparg AS odoa JOIN opd AS od ON (od.opd_id = odoa.opd_id) JOIN op AS o ON (o.op_id = od.op_id) JOIN oparg AS oa ON (oa.oparg_id = odoa.oparg_id) ORDER BY od.opd_id, odoa.pos;'):
    rec = opd.setdefault(row[0],{"op": "", "args": []})
    rec["op"] = row[1]
    rec["args"].append([row[2], row[4]])

for op in sorted(opd):
    rec = opd[op]
    opn = rec["op"]
    args = rec["args"]
    argl = ",".join(map(lambda i: "(" + i[0] + ")" if i[1] else i[0], args))
    print "%s %s" % (opn, argl)

conn.close()
