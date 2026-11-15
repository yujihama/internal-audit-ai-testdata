# -*- coding: utf-8 -*-
"""証跡一式の生成: 対照版（読みやすい）と難版（可読性を落とした版）"""
import os, shutil, zlib, json, pickle
import numpy as np, cv2
import pymupdf as fitz
from PIL import Image, ImageDraw, ImageFont
from reportlab.pdfgen import canvas as rlcanvas
from email.message import EmailMessage
from email.utils import format_datetime
from common import *
import data, docs, screens, degrade as dg

NAME = '販売プロセス_検証データ_小'
OUT = f'{ROOT}/out/{NAME}'
HARD, CLEAN, TMP = f'{OUT}/A_難版', f'{OUT}/B_対照版', f'{ROOT}/out/tmp'
MAN, CROPS, KV = [], [], {}
SCREEN_TITLE = '取引先マスタ照会画面の写し（2026/05/12 経理課にて取得）'
FO = {'C1': 'C1_与信限度額', 'C2': 'C2_受注', 'C3': 'C3_値引', 'C4': 'C4_出荷・売上計上', 'C5': 'C5_返品・売上取消',
      'C6': 'C6_入金消込', 'C7': 'C7_滞留債権', 'C8': 'C8_期末売上計上', 'X': '共通資料'}
CONF = dict(zip('0O15862ー一工エ口ロ力カ二ニ夕タ千士土未末日円株社課受注大.,/-', 'O0lSBGZ一ー工エ口ロ力カ二ニ夕タ干土士末未曰丹抹杜諜愛往犬,.I一'))
CONF.update({'工': 'エ', 'エ': '工', '口': 'ロ', 'ロ': '口', '力': 'カ', 'カ': '力', '二': 'ニ', 'ニ': '二', '夕': 'タ', 'タ': '夕'})


class PL:
    def __init__(s, ops='', layer='none', fmt='pdf', dmg=(), wrong=None, vec=(), hdr=''):
        s.ops, s.layer, s.fmt, s.dmg, s.wrong, s.vec, s.hdr = ops, layer, fmt, list(dmg), wrong or {}, list(vec), hdr


def raster(pdf, pno):
    pix = fitz.open(pdf)[pno].get_pixmap(dpi=dg.DPI, alpha=False)
    return np.frombuffer(pix.samples, np.uint8).reshape(pix.h, pix.w, 3).copy()


def is_gray(img):
    return bool((img[..., 0] == img[..., 1]).all() and (img[..., 1] == img[..., 2]).all())


def enc(img, jq, path):
    """画像を保存（白黒2値はPNG、それ以外はJPEG）"""
    if is_gray(img) and len(np.unique(img[::7, ::7, 0])) <= 2:
        p = path + '.png'
        Image.fromarray(img[..., 0]).convert('1').save(p, optimize=True)
    else:
        p = path + '.jpg'
        (Image.fromarray(img[..., 0], 'L') if is_gray(img) else Image.fromarray(img)).save(p, quality=jq)
    return p


def psize(img, M):
    sc = float(np.sqrt(abs(np.linalg.det(M[:2, :2]))))
    return img.shape[1] / (dg.DPI * sc) * 72, img.shape[0] / (dg.DPI * sc) * 72, sc


def page_pdf(img, M, path, jq=62, spans=None, garbled=False):
    pw, ph, sc = psize(img, M)
    ip = enc(img, jq, path + '_i')
    if not spans:
        d = fitz.open()
        d.new_page(width=pw, height=ph).insert_image(fitz.Rect(0, 0, pw, ph), filename=ip)
        d.save(path, deflate=True)
        return
    c = rlcanvas.Canvas(path, pagesize=(pw, ph))
    c.drawImage(ip, 0, 0, pw, ph)
    for s in spans:
        p = M @ np.array([s['x'] * dg.DPI / 72, s['y'] * dg.DPI / 72, 1.0])
        x, y = p[0] / p[2] / (dg.DPI * sc) * 72, p[1] / p[2] / (dg.DPI * sc) * 72
        t = c.beginText()
        t.setTextRenderMode(3)
        t.setFont('Helvetica' if garbled else 'G', max(4, s['size']))
        t.setTextOrigin(x, ph - y)
        t.textOut(s['text'])
        c.drawText(t)
    c.save()


def get_spans(pdf, pno):
    out = []
    for b in fitz.open(pdf)[pno].get_text('dict')['blocks']:
        if b['type'] != 0:
            continue
        for l in b['lines']:
            for s in l['spans']:
                if s['text'].strip():
                    out.append(dict(x=s['origin'][0], y=s['origin'][1], size=s['size'], text=s['text']))
    return out


def corrupt(spans, rng, g, pno, wrong, p=0.07):
    hit = set()
    for s in spans:
        done = False
        for k, (old, new) in wrong.items():
            b = g.boxes.get(k)
            if b and b[0] == pno:
                x0, y0, x1, y1 = [v * 72 / 25.4 for v in b[1:]]
                if x0 - 2 <= s['x'] <= x1 + 2 and y0 - 2 <= s['y'] <= y1 + 2 and old in s['text']:
                    s['text'] = s['text'].replace(old, new)
                    hit.add(k)
                    done = True
        if done:
            continue
        o = []
        for ch in s['text']:
            r = rng.random()
            if r < p and ch in CONF:
                o.append(CONF[ch])
            elif r < p * 1.2:
                continue
            elif r < p * 1.35:
                o.append(ch + ' ')
            else:
                o.append(ch)
        s['text'] = ''.join(o)
    assert hit == set(wrong), (wrong, hit)
    order = list(range(len(spans)))
    for _ in range(len(spans) // 6):
        i, j = rng.integers(0, len(spans), 2)
        order[i], order[j] = order[j], order[i]
    return [spans[i] for i in order]


def garble(spans):
    for s in spans:
        s['text'] = ''.join(ch if ch == ' ' else chr(33 + (ord(ch) * 7 + 13) % 94) for ch in s['text'])
    return spans


def box_px(g, key, shrink=1.0):
    keys = key if isinstance(key, (list, tuple)) else [key]
    bs = [g.boxes[k] for k in keys]
    x0, y0, x1, y1 = min(b[1] for b in bs), min(b[2] for b in bs), max(b[3] for b in bs), max(b[4] for b in bs)
    cx, cy, w, h = (x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) * shrink, (y1 - y0) * shrink
    return bs[0][0], [dg.mm2px(v) for v in (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)]


def add_crops(doc, img, M, rotk, boxes, kv, checks, scale=1.0):
    for k in checks:
        if k not in boxes:
            continue
        x0, y0, x1, y1 = [v * scale for v in boxes[k]]
        pts = np.array([[x0, y0, 1], [x1, y0, 1], [x1, y1, 1], [x0, y1, 1]], float).T
        q = M @ pts
        q = q[:2] / q[2]
        a, b = max(0, int(q[0].min()) - 18), max(0, int(q[1].min()) - 18)
        c, d = min(img.shape[1], int(q[0].max()) + 18), min(img.shape[0], int(q[1].max()) + 18)
        if c - a < 4 or d - b < 4:
            continue
        CROPS.append((doc, k, kv.get(k, ''), np.rot90(img[b:d, a:c], -rotk).copy()))


LAY = {'none': 'なし（画像のみのPDF）', 'wrong': 'あり（誤りを含む。読取ソフトの誤認識を再現）', 'garbled': 'あり（文字化け）'}
FMT = {'jpg': 'なし（画像ファイル）', 'png': 'なし（画像ファイル）', 'xlsx': 'なし（Excelに画像を貼り付け）'}


def man(set_, folder, fname, kind, procs, ops='-', layer='', stage=1, unread='-', impact='-', trap='-'):
    MAN.append(dict(set=set_, path=f'{folder}/{fname}', kind=kind, procs=procs, ops=ops, layer=layer, stage=stage,
                    unread=unread, impact=impact, trap=trap))


def emit(ck, name, g, pl, kind, procs, checks=()):
    folder = FO[ck]
    os.makedirs(f'{CLEAN}/{folder}', exist_ok=True)
    os.makedirs(f'{HARD}/{folder}', exist_ok=True)
    KV[name] = {k: g.kv[k] for k in checks if k in g.kv}
    shutil.copy(g.path, f'{CLEAN}/{folder}/{name}.pdf')
    vl = 'あり（正しい。印影・手書きの有無は画像で確認が必要）'
    man('B', folder, name + '.pdf', kind, procs, layer=vl)
    if pl is None:
        shutil.copy(g.path, f'{HARD}/{folder}/{name}.pdf')
        man('A', folder, name + '.pdf', kind, procs, ops='加工なし（電子的に作成されたPDF）', layer=vl)
        return
    rng = np.random.default_rng(zlib.crc32(name.encode()))
    parts, descs = [], []
    for i in range(g.pno + 1):
        if i in pl.vec:
            parts.append(('vec', i))
            continue
        img = raster(g.path, i)
        boxes = {k: [dg.mm2px(v) for v in b[1:]] for k, b in g.boxes.items() if b[0] == i}
        glare = []
        for d in pl.dmg:
            kind_, key, rel, label = d[:4]
            shrink = d[4] if len(d) > 4 else 1.0
            if key is None:
                if i == 0:
                    img = dg.DMG[kind_][0](img, None, rng)
                continue
            if kind_ == 'glare':
                pn, bx = box_px(g, key, shrink)
                if pn == i:
                    glare.append(bx)
                continue
            if isinstance(key, tuple) and isinstance(key[0], (int, float)):
                pn, bx = 0, [dg.mm2px(v) for v in key]
            else:
                pn, bx = box_px(g, key, shrink)
            if pn == i:
                img = dg.DMG[kind_][0](img, bx, rng)
        ctx = dict(protect=[b for k, b in boxes.items() if k.startswith('k_')], faxhdr=pl.hdr, other=OTHER, glare=glare)
        img2, M, rotk, desc = dg.run_ops(img, pl.ops, rng, ctx)
        descs.append(desc)
        parts.append(('img', img2, M, rotk, i))
        add_crops(name, img2, M, rotk, boxes, g.kv, checks)
    ext = pl.fmt
    dst = f'{HARD}/{folder}/{name}.{ext}'
    if ext == 'jpg':
        assert len(parts) == 1
        Image.fromarray(parts[0][1]).save(dst, quality=82)
    else:
        doc = fitz.open()
        src = fitz.open(g.path)
        for n, pt in enumerate(parts):
            if pt[0] == 'vec':
                doc.insert_pdf(src, from_page=pt[1], to_page=pt[1])
                continue
            _, img2, M, rotk, i = pt
            spans = None
            if pl.layer == 'wrong':
                spans = corrupt(get_spans(g.path, i), rng, g, i, pl.wrong)
            elif pl.layer == 'garbled':
                spans = garble(get_spans(g.path, i))
            tp = f'{TMP}/{name}_{n}.pdf'
            page_pdf(img2, M, tp, jq=85 if not pl.ops else (72 if 'faded' in pl.ops or 'carbon' in pl.ops else 60),
                     spans=spans, garbled=pl.layer == 'garbled')
            doc.insert_pdf(fitz.open(tp))
        doc.save(dst, deflate=True, garbage=3)
    s3 = [d for d in pl.dmg if dg.DMG[d[0]][2] == 3]
    s2 = [dg.DMG[d[0]][1] for d in pl.dmg if dg.DMG[d[0]][2] == 2]
    ops = '、'.join([x for x in dict.fromkeys(descs) if x] + s2) or '画質の加工なし'
    if pl.vec:
        layer = f'混在（{"・".join(str(v + 1) for v in pl.vec)}ページ目は文字情報あり、他のページは画像のみ）'
    else:
        layer = FMT.get(ext) or LAY[pl.layer]
    trap = '；'.join(f'{g.kv[k]} の箇所：画像は「{o}」、文字情報は「{n}」' for k, (o, n) in pl.wrong.items()) or '-'
    man('A', folder, f'{name}.{ext}', kind, procs, ops=ops, layer=layer, stage=3 if s3 else (2 if pl.ops or s2 else 1),
        unread='、'.join(f'{d[3]}（{dg.DMG[d[0]][1]}）' for d in s3) or '-',
        impact=('あり' if any(d[2] for d in s3) else 'なし') if s3 else '-', trap=trap)


def emit_screen(ck, name, src, pl, kind, procs, checks):
    pil, boxes, kv = src
    folder = FO[ck]
    KV[name] = {k: kv[k] for k in checks if k in kv}
    pil.save(f'{CLEAN}/{folder}/{name}.png')
    man('B', folder, name + '.png', kind, procs, layer='なし（画像ファイル）')
    if pl is None:
        pil.save(f'{HARD}/{folder}/{name}.png')
        man('A', folder, name + '.png', kind, procs, ops='加工なし（画面の写しそのまま）', layer='なし（画像ファイル）')
        return
    rng = np.random.default_rng(zlib.crc32(name.encode()))
    img2, M, rotk, desc = dg.run_ops(np.array(pil), pl.ops, rng, {})
    bx = {k: list(b[1:]) for k, b in boxes.items()}
    add_crops(name, img2, M, rotk, bx, kv, checks)
    dst = f'{HARD}/{folder}/{name}.{pl.fmt}'
    if pl.fmt == 'xlsx':
        from openpyxl import Workbook
        from openpyxl.drawing.image import Image as XI
        from openpyxl.styles import Font
        tp = f'{TMP}/{name}.png'
        Image.fromarray(img2).save(tp)
        wb = Workbook()
        ws = wb.active
        ws.title = '画面'
        ws['A1'] = SCREEN_TITLE
        ws['A1'].font = Font(name='游ゴシック', size=10)
        ws.add_image(XI(tp), 'B3')
        wb.save(dst)
    else:
        Image.fromarray(img2).save(dst, quality=80) if pl.fmt == 'jpg' else Image.fromarray(img2).save(dst)
    man('A', folder, f'{name}.{pl.fmt}', kind, procs, ops=desc, layer=FMT[pl.fmt], stage=2)


def eml(ck, name, frm, to, cc, subj, body, when, kind, procs):
    m = EmailMessage()
    m['From'], m['To'], m['Subject'] = frm, to, subj
    if cc:
        m['Cc'] = cc
    m['Date'] = format_datetime(when)
    m['Message-ID'] = f'<{when.strftime("%Y%m%d%H%M%S")}.{zlib.crc32(name.encode()) % 100000}@aoba-kiko.example.co.jp>'
    m.set_content(body, charset='iso-2022-jp', cte='7bit')
    for root in (HARD, CLEAN):
        with open(f'{root}/{FO[ck]}/{name}.eml', 'wb') as f:
            f.write(m.as_bytes())
    for s in 'AB':
        man(s, FO[ck], name + '.eml', kind, procs, ops='加工なし（メールファイル）' if s == 'A' else '-',
            layer='あり（メール本文。文字コードはISO-2022-JP）')


def faxhdr(d, cu):
    return (f'{d.year}/{d.month:02d}/{d.day:02d} {9 + d.day % 8}:{10 + d.day}  FROM:{hankaku(cu["pkana"])} '
            f'{cu["tel"]}   TO:{CO["fax"]}   P.001/001')


def main():
    global OTHER
    for p in (OUT, TMP):
        shutil.rmtree(p, ignore_errors=True)
    for p in (HARD, CLEAN, TMP, f'{OUT}/正解'):
        os.makedirs(p)
    DT = data.build()
    C = DT['C']
    T = lambda n: f'{TMP}/src_{n}.pdf'
    docs.rules(T('rules'), 21)
    OTHER = raster(T('rules'), 0)
    IRR = False

    # ---- C1 与信 ----
    kA, kR, kS = ('k_amount', 'k_st_ka', 'k_st_bu', 'k_st_yk', 'k_st_kr', 'k_score'), ('k_cust', 'k_score', 'k_rdate'), ('k_limit', 'k_upd')
    plans = {
        1: (PL('copy+skew2', dmg=[('punch', None, IRR, ''), ('blotch', 'x_addr', IRR, '取引先の所在地')]),
            PL('fax', hdr='2025/04/23 10:12  FROM:ﾄｳﾄｼﾝﾖｳﾘｻｰﾁ 03-0122-4401   P.001/001'), PL('sslow', fmt='png')),
        2: (PL('photo', fmt='jpg', dmg=[('fold', None, IRR, '')]),
            PL('dither+skew2', layer='wrong', wrong={'k_score': ('61', '67')}), PL('ssphoto', fmt='jpg')),
        3: (PL('faded+skew3'), PL('show', dmg=[('water', 'x_note', IRR, '所見の文章')]), None),
        4: (PL('streak+rot90', layer='wrong'), PL('lowres', fmt='jpg', dmg=[('sticky', 'x_note', IRR, '所見の文章', 0.8)]),
            PL('sslow', fmt='xlsx')),
        5: (PL('copy'), None, PL('sslow', fmt='png'))}
    for x in DT['C1']:
        s = x['s']
        pa, pr, ps = plans[s]
        emit('C1', f'C1_S{s}_与信申請書', docs.credit_app(T(f'c1a{s}'), DT, x, 100 + s, hand=(s == 2)), pa, '与信申請書', 'P01,P02', kA)
        emit('C1', f'C1_S{s}_信用調査報告書', docs.credit_report(T(f'c1r{s}'), DT, x, 110 + s), pr, '信用調査報告書', 'P02', kR)
        emit_screen('C1', f'C1_S{s}_取引先マスタ画面', screens.master_screen(DT, x, s), ps, '取引先マスタ画面の写し', 'P01', kS)
    emit('C1', 'C1_S5_決裁権限委任届', docs.delegation(T('c1d'), DT, 120),
         PL('fax+skew1', hdr='2025/08/08 16:41  FROM:ｱｵﾊﾞｷｺｳ ｿｳﾑ 03-0155-2198   P.001/001'), '決裁権限委任届', 'P01',
         ('k_period', 'k_to', 'k_from', 'k_st_ok'))

    # ---- C2 受注 ----
    kP = ('k_cust', 'k_code1', 'k_qty1', 'k_price1', 'k_amt1', 'k_qty2', 'k_amt2', 'k_qty3', 'k_total')
    kO = ('k_no', 'k_date', 'k_qty1', 'k_price1', 'k_amt1', 'k_qty2', 'k_qty3', 'k_st_reg', 'k_st_app')
    plans = {
        1: (PL('fax', dmg=[('band', ['k_code1', 'k_amt1', 'k_code2', 'k_amt2'], True, '明細行（品番・数量・単価・金額）')]),
            PL('wavy+copy', dmg=[('fold', None, IRR, '')])),
        2: (PL('fax+skew2'), PL('copy+jitter', dmg=[('sticky', 'x_note', IRR, '備考欄')])),
        3: (PL('photo+shake', fmt='jpg'), None),
        4: (PL('faded', dmg=[('blotch', 'x_place', IRR, '納入場所')]), PL('streak+skew4')),
        5: (PL('', layer='garbled'), PL('dark+skew1', layer='wrong', wrong={'k_qty2': ('8', '3')}))}
    for x in DT['C2']:
        s, o = x['s'], x['o']
        cu = C[o['c']]
        pp, po_ = plans[s]
        if pp.ops.startswith('fax'):
            pp.hdr = faxhdr(x['pod'], cu)
        emit('C2', f'C2_S{s}_注文書', docs.po(T(f'c2p{s}'), DT, x, 200 + s), pp, '注文書', 'P03', kP)
        if x.get('rev'):
            emit('C2', f'C2_S{s}_訂正注文書', docs.po(T(f'c2v{s}'), DT, x, 210 + s, lines=docs.ol(o), rev=x['rev']),
                 PL('fax', hdr=faxhdr(x['rev'], cu)), '訂正注文書', 'P03', kP)
        emit('C2', f'C2_S{s}_受注伝票', docs.order_slip(T(f'c2o{s}'), DT, o, 220 + s, pono=x['pono'], due=x['due']), po_,
             '受注伝票', 'P03,P04', kO)

    # ---- C3 値引 ----
    kD = ('k_rate', 'k_std', 'k_price', 'k_st_ka', 'k_st_bu')
    plans = {
        1: (PL('wavy+skew2'), PL('fax', hdr='')),
        2: (PL('faded', dmg=[('water', 'x_reason', IRR, '申請理由', 0.8)]), PL('lowres+skew3', fmt='jpg')),
        3: (PL('photo', fmt='jpg', dmg=[('glare', ['k_st_ka', 'k_st_bu'], True, '営業課長・営業部長の承認欄')]), None),
        4: (PL('copy+skew1'), PL('dark+skew3')),
        5: (PL('jitter+rot180', layer='wrong', wrong={'k_rate': ('15.0', '18.0')},
               dmg=[('sticky', 'x_reason', IRR, '申請理由', 0.85)]), PL('show+skew3'))}
    for x in DT['C3']:
        s, o = x['s'], x['o']
        pa, po_ = plans[s]
        emit('C3', f'C3_S{s}_値引申請書', docs.disc_app(T(f'c3a{s}'), DT, x, 300 + s), pa, '値引申請書', 'P05', kD)
        emit('C3', f'C3_S{s}_受注伝票', docs.order_slip(T(f'c3o{s}'), DT, o, 310 + s, note=f'値引申請 {x["no"]} 適用。'), po_,
             '受注伝票', 'P05', ('k_no', 'k_date', 'k_price1', 'k_st_app'))

    # ---- C4 出荷・売上 ----
    kH = ('k_no', 'k_sid', 'k_sd', 'k_code1', 'k_qty1', 'k_qty2', 'k_st_pick')
    kV = ('k_no', 'k_date', 'k_qty1', 'k_qty2', 'k_recv')
    plans = {
        1: (PL('streak+jitter'), PL('carbon', dmg=[('water', 'x_carrier', IRR, '備考・運送会社記入欄', 0.7)])),
        2: (PL('fax+jitter', hdr=''), PL('photo', fmt='jpg')),
        3: (PL('dither', layer='wrong', wrong={'k_qty2': ('300', '800')}), PL('faded+skew4')),
        4: (PL('copy+skew2'), PL('carbon', dmg=[('water', 'k_recv', True, '受領印欄')])),
        5: (None, PL('copy', dmg=[('blotch', 'x_carrier', IRR, '備考・運送会社記入欄', 0.6)]))}
    for x in DT['C4']:
        s, o = x['s'], x['o']
        ph, pv = plans[s]
        emit('C4', f'C4_S{s}_出荷報告書', docs.ship_rec(T(f'c4h{s}'), DT, o, 400 + s), ph, '出荷報告書', 'P06', kH)
        emit('C4', f'C4_S{s}_物品受領書', docs.receipt(T(f'c4v{s}'), DT, o, x, 410 + s), pv, '物品受領書', 'P06', kV)

    # ---- C5 返品・取消 ----
    kRt = ('k_no', 'k_amt', 'k_st_ka', 'k_st_bu', 'k_st_kr')
    kCn = ('k_no', 'k_date', 'k_hp', 'k_amt', 'k_st_reg', 'k_st_app')
    plans = {
        1: (PL('fax+skew1', hdr='2025/05/29 11:08  FROM:ｱｵﾊﾞｷｺｳ ｴｲｷﾞｮｳ2 03-0155-2197   P.001/001',
               dmg=[('blotch', 'x_reason', IRR, '返品理由', 0.6)]), PL('wavy+dark')),
        2: (PL('photo', fmt='jpg'), PL('lowres', fmt='jpg')),
        3: (PL('copy'), PL('faded')),
        4: (PL('show+jitter', dmg=[('blotch', 'x_note', IRR, '備考欄', 0.7)]), None),
        5: (PL('dark+rot270', layer='wrong'), PL('carbon', dmg=[('water', 'x_note', IRR, '摘要欄')]))}
    for x in DT['C5']:
        s, r = x['s'], x['r']
        pa, pc = plans[s]
        ra = DT['RT']['C5SX'] if s == 3 else r   # S3 は別取引の申請書が入っている
        emit('C5', f'C5_S{s}_返品申請書', docs.return_app(T(f'c5a{s}'), DT, ra, 500 + s), pa,
             '返品申請書' + ('（別取引のもの）' if s == 3 else ''), 'P07', kRt)
        emit('C5', f'C5_S{s}_売上取消伝票', docs.cancel_slip(T(f'c5c{s}'), DT, r, 510 + s), pc, '売上取消伝票', 'P07,P08', kCn)

    # ---- C6 入金消込 ----
    def wrongamt(v):
        s = yen(v)
        i = 2 if s[1] == ',' else 1
        return s, s[:i] + str((int(s[i]) + 2) % 10) + s[i + 1:]

    for m in DT['C6']:
        s, tag = m['s'], m['m'].strftime('%Y-%m')
        n = len(m['rows'])
        kB = ('k_amt0', 'k_amt12', f'k_amt{n - 1}', 'k_total')
        kC = ('k_amt0', 'k_amt12', 'k_st_made', 'k_st_ok', 'k_um', 'k_umnote', 'k_total')
        gb = docs.bank(T(f'c6b{s}'), DT, m, 600 + s, two=(s == 1))
        gr = docs.recon(T(f'c6r{s}'), DT, m, 610 + s)
        pb, pr = {1: (PL('jitter', vec=[0]), PL('streak+skew2')),
                  2: (PL('fax', hdr='2025/11/04 09:26  FROM:ﾋｶﾘﾁﾕｳｵｳｷﾞﾝｺｳ ｼﾊﾞｳﾗ 03-0155-7001   P.001/001'), PL('photo', fmt='jpg')),
                  3: (PL('lowres', fmt='jpg', dmg=[('torn', (0, 264, 118, 297), IRR, '下端の注記・銀行の所在地')]),
                      PL('faded', layer='wrong', wrong={'k_amt12': wrongamt(m['rows'][12]['pay'])}))}[s]
        emit('C6', f'C6_{tag}_入金明細', gb, pb, '入金明細（銀行）', 'P09', kB)
        emit('C6', f'C6_{tag}_入金消込一覧', gr, pr, '入金消込一覧表', 'P09,P10', kC)

    # ---- C7 滞留債権 ----
    JST = dt.timezone(dt.timedelta(hours=9))
    for m in DT['C7']:
        s, tag = m['s'], m['m'].strftime('%Y-%m')
        ks = ['k_st_made', 'k_st_k', 'k_st_b'] + [f'k_c90_{i}' for i in range(12)] + [f'k_cm_{i}' for i in range(12)]
        ga = docs.aging(T(f'c7a{s}'), DT, m, 700 + s)
        emit('C7', f'C7_{tag}_滞留一覧', ga, {1: PL('copy'), 2: PL('wavy+skew3'), 3: PL('photo', fmt='jpg')}[s],
             '売掛金滞留状況一覧', 'P11', ks)
        ov = [r for r in m['rows'] if r['a'][4]]
        if s == 1:
            cu = C[ov[0]['c']]
            eml('C7', f'C7_{tag}_督促記録', f'{full("佐野")} <sano@aoba-kiko.example.co.jp>',
                f'{cu["name"]} 経理部 ご担当者様 <keiri@{cu["code"].lower()}.example.jp>',
                f'{full("立花")} <tachibana@aoba-kiko.example.co.jp>', 'お支払い遅延分の分割入金について（ご確認）',
                f'{cu["name"]}\n経理部 ご担当者様\n\nいつもお世話になっております。{CO["name"]} 営業部の佐野です。\n\n'
                f'8月27日にお電話でご相談いただきました、支払期日を過ぎているご請求分（合計 {yen(ov[0]["a"][4])}円）につきまして、\n'
                '下記のとおり分割でのお支払いとすることで承りました。\n\n  1回目 9月10日\n  2回目 10月10日\n  3回目 11月10日\n\n'
                '各回の金額は別途お送りする明細のとおりです。\nご入金が確認できない場合は、新規のご注文の出荷を保留させていただく場合がございます。\n'
                '何卒よろしくお願い申し上げます。\n\n-- \n' + f'{CO["name"]} 営業部 営業1課\n佐野 拓海\nTEL {CO["tel"]}\n',
                dt.datetime(2025, 8, 28, 10, 14, tzinfo=JST), '督促・対応記録（メール）', 'P11')
        elif s == 2:
            cu = C[[r for r in m['rows'] if r['a'][2] and not r['a'][4]][0]['c']]
            eml('C7', f'C7_{tag}_督促記録', f'{full("河合")} <kawai@aoba-kiko.example.co.jp>',
                f'{cu["name"]} 購買課 ご担当者様 <kobai@{cu["code"].lower()}.example.jp>', '',
                '10月分ご請求のお支払い予定のご確認',
                f'{cu["name"]}\n購買課 ご担当者様\n\nお世話になっております。{CO["name"]} 営業部の河合です。\n\n'
                '10月分のご請求につきまして、お支払い期日を過ぎておりますが、本日時点でご入金の確認ができておりません。\n'
                'お手数ですが、お支払いのご予定をお知らせいただけますでしょうか。\n行き違いの場合はご容赦ください。\n\n'
                '-- \n' + f'{CO["name"]} 営業部 営業2課\n河合 美咲\nTEL {CO["tel"]}\n',
                dt.datetime(2025, 11, 26, 15, 42, tzinfo=JST), '督促・対応記録（メール。90日超の先に関するものではない）', 'P11')
        else:
            emit('C7', f'C7_{tag}_対応記録', docs.memo(T('c7m'), DT, m, 720), PL('faded'), '督促・対応記録（手書き）', 'P11',
                 ('k_cust', 'k_memo'))

    # ---- C8 期末 ----
    emit('C8', 'C8_期末売上計上時期確認表', docs.cutoff(T('c8c'), DT, 800), PL('dark+skew1'), '期末売上計上時期確認表', 'P12,P13',
         ('k_st_made', 'k_st_ok', 'k_sd4', 'k_ld4', 'k_sd5'))
    plans = {1: PL('jitter+fax', hdr=''), 2: PL('copy', dmg=[('blotch', 'x_slip', IRR, '送り状番号')]), 3: PL('wavy+lowres', fmt='jpg'),
             4: PL('faded+skew2'), 5: PL('jitter', layer='wrong', wrong={'k_sd': ('2026/04/01', '2026/03/31')}), 6: None}
    for x in DT['C8']:
        s, o = x['s'], x['o']
        note = '3/31の集荷便に間に合わず、4/1午前便で出荷。' if s == 4 else ''
        emit('C8', f'C8_S{s}_出荷報告書', docs.ship_rec(T(f'c8h{s}'), DT, o, 810 + s, note=note), plans[s], '出荷報告書', 'P12', kH)

    # ---- 共通資料 ----
    emit('X', '職務権限規程', docs.authority(T('auth'), 20), PL('copy+skew1', vec=[0]), '職務権限規程（決裁権限一覧・役職者一覧）',
         'P01,P04,P05,P07', ('k_a1', 'k_a2', 'k_a2r', 'k_a3', 'k_a5', 'k_a6', 'k_a8', 'k_r1', 'k_r2', 'k_r3'))
    emit('X', '販売管理規程', docs.rules(T('rules'), 21), PL('show', vec=[0]), '販売管理規程', '全般', ('k_art12', 'k_art17'))

    pickle.dump(dict(MAN=MAN, DT=DT, KV=KV), open(f'{TMP}/state.pkl', 'wb'))
    # 確認用の切り出し一覧
    f = ImageFont.truetype(fp('G'), 15)
    cells = []
    for doc, k, val, im in CROPS:
        h, w = im.shape[:2]
        sc = min(110 / h, 500 / w, 2.5)
        im = cv2.resize(im, (max(1, int(w * sc)), max(1, int(h * sc))))
        cell = Image.new('RGB', (520, 150), 'white')
        cell.paste(Image.fromarray(im), (4, 2))
        d = ImageDraw.Draw(cell)
        d.text((4, 114), f'{doc[:26]} {k}', font=f, fill=(0, 0, 160))
        d.text((4, 131), f'→ {val}'[:44], font=f, fill=(160, 0, 0))
        cells.append(cell)
    per = 55
    for n in range(0, len(cells), per):
        sheet = Image.new('RGB', (520 * 5, 150 * 11), (200, 200, 200))
        for i, c in enumerate(cells[n:n + per]):
            sheet.paste(c, ((i % 5) * 520, (i // 5) * 150))
        sheet.save(f'{TMP}/crops_{n // per:02d}.png')
    print('files', len(MAN), 'crops', len(CROPS))
    tot = 0
    for root, _, fs in os.walk(HARD):
        tot += sum(os.path.getsize(os.path.join(root, x)) for x in fs)
    print('hard set MB', round(tot / 1e6, 1))


if __name__ == '__main__':
    main()
