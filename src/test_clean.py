# -*- coding: utf-8 -*-
import os, sys
import pymupdf as fitz
from PIL import Image
import data, docs, screens

out = '/home/claude/work/out/test'
os.makedirs(out, exist_ok=True)
DT = data.build()
jobs = [('credit_app', lambda p: docs.credit_app(p, DT, DT['C1'][4], 1)),
        ('credit_app_h', lambda p: docs.credit_app(p, DT, DT['C1'][2], 2, hand=True)),
        ('credit_report', lambda p: docs.credit_report(p, DT, DT['C1'][0], 3)),
        ('deleg', lambda p: docs.delegation(p, DT, 4)),
        ('poA', lambda p: docs.po(p, DT, DT['C2'][3], 5, lines=docs.ol(DT['C2'][3]['o']), rev=DT['C2'][3]['rev'])),
        ('poB', lambda p: docs.po(p, DT, DT['C2'][1], 6)),
        ('poC', lambda p: docs.po(p, DT, DT['C2'][2], 7)),
        ('order', lambda p: docs.order_slip(p, DT, DT['C2'][4]['o'], 8, pono='発26-0058')),
        ('disc', lambda p: docs.disc_app(p, DT, DT['C3'][0], 9)),
        ('ship', lambda p: docs.ship_rec(p, DT, DT['C8'][3]['o'], 10, note='3/31の集荷便に間に合わず、4/1午前便で出荷。')),
        ('receipt', lambda p: docs.receipt(p, DT, DT['C4'][1]['o'], DT['C4'][1], 11)),
        ('receipt2', lambda p: docs.receipt(p, DT, DT['C4'][0]['o'], DT['C4'][0], 12)),
        ('return', lambda p: docs.return_app(p, DT, DT['C5'][1]['r'], 13)),
        ('cancel', lambda p: docs.cancel_slip(p, DT, DT['C5'][1]['r'], 14)),
        ('bank', lambda p: docs.bank(p, DT, DT['C6'][0], 15, two=True)),
        ('recon', lambda p: docs.recon(p, DT, DT['C6'][1], 16)),
        ('aging', lambda p: docs.aging(p, DT, DT['C7'][2], 17)),
        ('memo', lambda p: docs.memo(p, DT, DT['C7'][2], 18)),
        ('cutoff', lambda p: docs.cutoff(p, DT, 19)),
        ('auth', lambda p: docs.authority(p, 20)),
        ('rules', lambda p: docs.rules(p, 21))]
sel = sys.argv[1:] or [j[0] for j in jobs]
for name, fn in jobs:
    if name not in sel:
        continue
    p = f'{out}/{name}.pdf'
    fn(p)
    doc = fitz.open(p)
    for i, pg in enumerate(doc):
        pg.get_pixmap(dpi=int(os.environ.get('DPI', '70'))).save(f'{out}/{name}_{i}.png')
    print(name, len(doc), 'pages')
im, b, kv = screens.master_screen(DT, DT['C1'][1], 3)
im.save(f'{out}/screen.png')
