# -*- coding: utf-8 -*-
"""実務版の中身を目で確かめる: python rpeek.py <出力名> <幅> <列数> <ファイル>:<ページ(0始まり)> ...  （docx/xlsx は埋め込み画像の番号）"""
import sys, zipfile, io
import pymupdf as fitz
from PIL import Image
out, W, cols = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
cells = []
for a in sys.argv[4:]:
    p, n = a.rsplit(':', 1)
    n = int(n)
    if p.endswith(('.docx', '.xlsx')):
        z = zipfile.ZipFile(p)
        ms = sorted(x for x in z.namelist() if '/media/' in x)
        im = Image.open(io.BytesIO(z.read(ms[n]))).convert('RGB')
    elif p.endswith('.tif'):
        im = Image.open(p)
        im.seek(n)
        im = im.convert('RGB')
    else:
        pm = fitz.open(p)[n].get_pixmap(dpi=110)
        im = Image.frombytes('RGB', (pm.w, pm.h), pm.samples)
    cells.append(im.resize((W, int(im.height * W / im.width))))
H = max(c.height for c in cells)
rows = (len(cells) + cols - 1) // cols
sh = Image.new('RGB', (cols * (W + 8), rows * (H + 8)), (90, 90, 90))
for i, c in enumerate(cells):
    sh.paste(c, ((i % cols) * (W + 8), (i // cols) * (H + 8)))
sh.save(f'/home/claude/work/out/{out}.png')
print(sh.size)
