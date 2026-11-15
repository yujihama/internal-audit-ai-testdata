# -*- coding: utf-8 -*-
"""目視確認用: 指定フォルダのファイルを並べた一覧画像を作る。 python peek.py <NAME> <A|B> <出力名> <幅> <列数> [部分一致...]"""
import sys, os
import pymupdf as fitz
from PIL import Image
from common import ROOT
name, st, out, W, nc = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]), int(sys.argv[5])
pats = sys.argv[6:]
base = f'{ROOT}/out/{name}/{"A_難版" if st == "A" else "B_対照版"}'
ims = []
for dp, _, fs in sorted(os.walk(base)):
    for f in sorted(fs):
        p = os.path.join(dp, f)
        if pats and not any(x in p for x in pats):
            continue
        if f.endswith('.pdf'):
            for pg in fitz.open(p):
                pm = pg.get_pixmap(dpi=110)
                ims.append(Image.frombytes('RGB', (pm.w, pm.h), pm.samples))
        elif f.endswith(('.jpg', '.png')):
            ims.append(Image.open(p).convert('RGB'))
cells = []
for im in ims:
    im = im.resize((W, int(im.height * W / im.width)))
    cells.append(im)
H = max(c.height for c in cells)
nr = (len(cells) + nc - 1) // nc
sh = Image.new('RGB', (W * nc + 10 * (nc - 1), (H + 10) * nr), (90, 90, 90))
for i, c in enumerate(cells):
    sh.paste(c, ((i % nc) * (W + 10), (i // nc) * (H + 10)))
sh.save(f'{ROOT}/out/{out}.png')
print(len(cells), sh.size)
