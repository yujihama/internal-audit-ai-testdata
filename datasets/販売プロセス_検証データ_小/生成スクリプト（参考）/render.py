# -*- coding: utf-8 -*-
"""紙面を組むための部品: ページ、表、承認欄、印影"""
import random
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from common import fp

RED = (188, 28, 34)
BLUE = (40, 60, 150)
PEN = (0.08, 0.12, 0.42)
BLK = (0.1, 0.1, 0.1)


def wrap(text, n):
    out, cur, w = [], '', 0.0
    for ch in text:
        cw = 0.5 if ord(ch) < 0x2000 or 0xFF61 <= ord(ch) <= 0xFF9F else 1.0
        if ch == '\n' or w + cw > n:
            out.append(cur)
            cur, w = '', 0.0
            if ch == '\n':
                continue
        cur += ch
        w += cw
    if cur:
        out.append(cur)
    return out


class Pg:
    def __init__(s, path, land=False, seed=0):
        s.W, s.H = (297.0, 210.0) if land else (210.0, 297.0)
        s.c = canvas.Canvas(path, pagesize=(s.W * mm, s.H * mm))
        s.path, s.boxes, s.kv, s.pno = path, {}, {}, 0
        s.rng = random.Random(seed)
        s.nrng = np.random.default_rng(seed)

    def y(s, v):
        return (s.H - v) * mm

    def t(s, x, y, txt, sz=10, f='G', key=None, al='l', col=(0, 0, 0), rot=0):
        txt = str(txt)
        c = s.c
        c.setFont(f, sz)
        c.setFillColorRGB(*col)
        w = pdfmetrics.stringWidth(txt, f, sz) / mm
        x0 = x - w if al == 'r' else (x - w / 2 if al == 'c' else x)
        if rot:
            c.saveState()
            c.translate(x0 * mm, s.y(y))
            c.rotate(rot)
            c.drawString(0, 0, txt)
            c.restoreState()
        else:
            c.drawString(x0 * mm, s.y(y), txt)
        h = sz * 0.3528
        if key:
            s.box(key, x0 - 1, y - h - 0.6, w + 2, h * 1.3 + 1.2, txt)
        return w

    def hw(s, x, y, txt, sz=13, f='H', col=PEN, key=None, jit=1.0):
        """手書き風（1文字ずつ揺らす）"""
        x0 = x
        for ch in str(txt):
            w = pdfmetrics.stringWidth(ch, f, sz) / mm
            s.t(x, y + s.rng.uniform(-0.35, 0.35) * jit, ch, sz * s.rng.uniform(0.94, 1.06), f, col=col,
                rot=s.rng.uniform(-4, 4) * jit)
            x += w * s.rng.uniform(0.9, 1.02)
        h = sz * 0.3528
        if key:
            s.box(key, x0 - 1, y - h - 1, x - x0 + 2, h * 1.4 + 2, txt)
        return x - x0

    def box(s, key, x, y, w, h, val=''):
        s.boxes[key] = (s.pno, x, y, x + w, y + h)
        s.kv[key] = val

    def ln(s, x1, y1, x2, y2, lw=0.4, dash=None, col=(0, 0, 0)):
        c = s.c
        c.setLineWidth(lw)
        c.setStrokeColorRGB(*col)
        c.setDash(dash or [])
        c.line(x1 * mm, s.y(y1), x2 * mm, s.y(y2))
        c.setDash([])

    def rc(s, x, y, w, h, lw=0.4, fill=None, col=(0, 0, 0)):
        c = s.c
        c.setLineWidth(lw)
        c.setStrokeColorRGB(*col)
        if fill is not None:
            c.setFillColorRGB(*fill)
            c.rect(x * mm, s.y(y + h), w * mm, h * mm, stroke=1, fill=1)
        else:
            c.rect(x * mm, s.y(y + h), w * mm, h * mm, stroke=1, fill=0)

    def im(s, pil, x, y, w, h):
        s.c.drawImage(ImageReader(pil), x * mm, s.y(y + h), w * mm, h * mm, mask='auto')

    def para(s, x, y, text, n, sz=10, f='M', lead=None, hand=False):
        lead = lead or sz * 0.3528 * 1.75
        for i, l in enumerate(wrap(text, n)):
            if hand:
                s.hw(x, y + i * lead, l, sz, 'H')
            else:
                s.t(x, y + i * lead, l, sz, f)
        return y + len(wrap(text, n)) * lead

    def lv(s, x, y, w1, w2, h, label, val, sz=10, key=None, f='G', hand=False, fill=(0.93, 0.93, 0.93)):
        """見出しセル＋値セル"""
        s.rc(x, y, w1, h, fill=fill)
        s.t(x + 1.5, y + h / 2 + 8 * 0.13, label, 8.5, 'G')
        s.rc(x + w1, y, w2, h)
        if val not in ('', None):
            if hand:
                s.hw(x + w1 + 2.5, y + h / 2 + sz * 0.15, val, sz + 2, 'H', key=key)
            else:
                s.t(x + w1 + 2, y + h / 2 + sz * 0.13, val, sz, f, key=key)

    def tbl(s, x, y, cols, rows, rh=7, sz=9, f='G', hh=None, keys=None, hfill=(0.9, 0.9, 0.9), lw=0.4, hand=None,
            hsz=None):
        hh = hh or rh
        hsz = hsz or min(sz, 9)
        cx = x
        for (tt, w, al) in cols:
            s.rc(cx, y, w, hh, lw, fill=hfill)
            s.t(cx + w / 2, y + hh / 2 + hsz * 0.13, tt, hsz, 'G', al='c')
            cx += w
        yy = y + hh
        for ri, r in enumerate(rows):
            cx = x
            for ci, (tt, w, al) in enumerate(cols):
                s.rc(cx, yy, w, rh, lw)
                v = r[ci] if ci < len(r) else ''
                if v not in ('', None):
                    k = keys.get((ri, ci)) if keys else None
                    base = yy + rh / 2 + sz * 0.13
                    if hand and (hand is True or ci in hand):
                        wv = pdfmetrics.stringWidth(str(v), 'H', sz + 2) / mm
                        xx = cx + w - 2 - wv if al == 'r' else (cx + (w - wv) / 2 if al == 'c' else cx + 2)
                        s.hw(xx, base + 0.3, v, sz + 2, 'H', key=k)
                    elif al == 'r':
                        s.t(cx + w - 1.5, base, v, sz, f, key=k, al='r')
                    elif al == 'c':
                        s.t(cx + w / 2, base, v, sz, f, key=k, al='c')
                    else:
                        s.t(cx + 1.5, base, v, sz, f, key=k)
                cx += w
            yy += rh
        return yy

    def appr(s, x, y, cols, w=20, h=20, hh=5, d=15.0):
        """承認欄。cols: (見出し, 印影画像|'slash'|None, キー, 期待値の説明)"""
        for i, col in enumerate(cols):
            tt, spec, key, desc = (list(col) + [None, ''])[:4]
            cx = x + i * w
            s.rc(cx, y, w, hh, fill=(0.93, 0.93, 0.93))
            s.t(cx + w / 2, y + hh / 2 + 8 * 0.13, tt, 8, 'G', al='c')
            s.rc(cx, y + hh, w, h)
            if spec == 'slash':
                s.ln(cx + w, y + hh, cx, y + hh + h, 0.4)
            elif spec is not None:
                dd = d * spec.size[0] / 260.0
                s.im(spec, cx + (w - dd) / 2 + s.rng.uniform(-1.5, 1.5), y + hh + (h - dd) / 2 + s.rng.uniform(-1.5, 1.5),
                     dd, dd * spec.size[1] / spec.size[0])
            if key:
                s.box(key, cx, y + hh, w, h, desc)

    def newpage(s):
        s.c.showPage()
        s.pno += 1

    def save(s):
        s.c.save()
        return s


# ---------------- 印影 ----------------
def _finish(im, q, rng, rot):
    a = np.array(im).astype(np.float32)
    h, w = a.shape[:2]
    lf = cv2.resize(rng.random((5, 5)).astype(np.float32), (w, h), interpolation=cv2.INTER_CUBIC)
    hf = rng.random((h, w)).astype(np.float32)
    m = np.clip(q + (lf - 0.5) * (1.3 - q), 0.12, 1.0)
    m = m * (hf > (1 - q) * 0.45)
    a[..., 3] *= m
    im = Image.fromarray(a.clip(0, 255).astype(np.uint8), 'RGBA')
    return im.rotate(rot, resample=Image.BICUBIC, expand=True)


def _ctext(d, cx, cy, txt, font, col):
    b = d.textbbox((0, 0), txt, font=font)
    d.text((cx - (b[2] + b[0]) / 2, cy - (b[3] + b[1]) / 2), txt, font=font, fill=col + (255,))


def seal(name, rng, q=0.9, col=RED, S=260):
    """認印（丸・縦書き）"""
    im = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse((12, 12, S - 12, S - 12), outline=col + (255,), width=9)
    if len(name) == 1:
        _ctext(d, S / 2, S / 2, name, ImageFont.truetype(fp('M'), int(S * 0.5)), col)
    else:
        f = ImageFont.truetype(fp('M'), int(S * 0.34))
        for i, ch in enumerate(name[:2]):
            _ctext(d, S / 2, S * 0.32 + i * S * 0.36, ch, f, col)
    return _finish(im, q, rng, rng.uniform(-9, 9))


def dstamp(top, date, bottom, rng, q=0.9, col=RED, S=260):
    """日付印（丸・3段）"""
    im = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    r = S / 2 - 12
    d.ellipse((12, 12, S - 12, S - 12), outline=col + (255,), width=8)
    for yy in (S * 0.37, S * 0.63):
        dx = (r * r - (yy - S / 2) ** 2) ** 0.5
        d.line((S / 2 - dx, yy, S / 2 + dx, yy), fill=col + (255,), width=6)
    _ctext(d, S / 2, S * 0.25, top, ImageFont.truetype(fp('G'), int(S * (0.15 if len(top) <= 3 else 0.12))), col)
    _ctext(d, S / 2, S * 0.5, date, ImageFont.truetype(fp('B'), int(S * (0.19 if len(date) <= 7 else 0.165))), col)
    _ctext(d, S / 2, S * 0.755, bottom, ImageFont.truetype(fp('G'), int(S * (0.17 if len(bottom) <= 2 else 0.13))), col)
    return _finish(im, q, rng, rng.uniform(-10, 10))


def rstamp(lines, rng, q=0.85, col=RED, W=420, H=250, sizes=None):
    """角形の受領印など"""
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle((8, 8, W - 8, H - 8), outline=col + (255,), width=8)
    n = len(lines)
    for i, l in enumerate(lines):
        sz = (sizes or [int(H * 0.62 / n)] * n)[i]
        _ctext(d, W / 2, H * (i + 0.5) / n * 0.86 + H * 0.07, l, ImageFont.truetype(fp('G'), sz), col)
    for i in range(1, n):
        yy = H * i / n * 0.86 + H * 0.07
        d.line((8, yy, W - 8, yy), fill=col + (255,), width=4)
    return _finish(im, q, rng, rng.uniform(-6, 6))


def sqseal(text, rng, q=0.85, col=RED, S=300):
    """角印（会社印）。3列に均等割り付け"""
    im = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle((8, 8, S - 8, S - 8), outline=col + (255,), width=10)
    text = text + ('之印' if len(text) % 3 == 1 else '印')
    n = len(text)
    per = [n // 3 + (1 if i < n % 3 else 0) for i in range(3)]
    cw = (S - 40) / 3
    k = 0
    for ci, m in enumerate(per):
        ch_h = (S - 40) / m
        f = ImageFont.truetype(fp('M'), int(min(cw, ch_h) * 0.9))
        for r in range(m):
            _ctext(d, 20 + (2 - ci) * cw + cw / 2, 20 + r * ch_h + ch_h / 2, text[k], f, col)
            k += 1
    return _finish(im, q, rng, rng.uniform(-4, 4))


def tstamp(text, rng, q=0.9, col=RED, H=110):
    f = ImageFont.truetype(fp('B'), int(H * 0.6))
    W = int(f.getlength(text) + H * 0.7)
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle((5, 5, W - 5, H - 5), outline=col + (255,), width=7)
    _ctext(d, W / 2, H / 2, text, f, col)
    return _finish(im, q, rng, rng.uniform(-8, 8))
