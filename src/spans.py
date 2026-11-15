# -*- coding: utf-8 -*-
"""対照版PDFの文字（位置・フォント）と印影の位置を表示する: python spans.py <PDFのパス> [部分一致]"""
import sys
import pymupdf as fitz
doc = fitz.open(sys.argv[1])
key = sys.argv[2] if len(sys.argv) > 2 else None
for pn, pg in enumerate(doc):
    print(f'--- page {pn + 1} / {len(doc)}  {pg.rect.width:.0f}x{pg.rect.height:.0f}')
    for im in pg.get_images(full=True):
        for r in pg.get_image_rects(im[0]):
            print(f'  [img] {r.x0:.0f},{r.y0:.0f},{r.x1:.0f},{r.y1:.0f}')
    for b in pg.get_text('dict')['blocks']:
        for l in b.get('lines', []):
            for sp in l['spans']:
                if key is None or key in sp['text']:
                    print(f"  {sp['bbox'][0]:.0f},{sp['bbox'][1]:.0f} {sp['font'][:14]:14s} {sp['size']:.1f} | {sp['text']}")
