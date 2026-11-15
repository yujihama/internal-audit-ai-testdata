# -*- coding: utf-8 -*-
"""実務データ編の共通部品: 帳票の汎用レイアウト、画面・写真・ログ、出力、正解表、検証、梱包"""
import os, re, sys, json, pickle, shutil, zipfile, subprocess, logging, datetime as dt
from collections import Counter
import numpy as np, cv2
import pymupdf as fitz
from PIL import Image, ImageDraw, ImageFont
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
import build as B, docs, degrade as dg
from build import PL, emit, emit_screen
from render import *
from common import *
from docs import DS, SL, dsd

N, A, U = '不備なし', '不備あり', '判断できない'
TR, DF, UR, LK, WL = 'ひっかけ', '不備', '判読不能', '証跡の不足', '文字情報の罠'
GR = (0.93, 0.93, 0.93)
RECALC = os.environ.get('XLSX_RECALC', 'recalc.py')      # 数式を再計算するスクリプト（LibreOffice を使う）の場所。環境変数 XLSX_RECALC で指定する


# ================= 準備 =================
def setup(name, key, fo, people, screen_title=''):
    B.NAME, B.OUT = name, f'{ROOT}/out/{name}'
    B.HARD, B.CLEAN, B.TMP = f'{B.OUT}/A_難版', f'{B.OUT}/B_対照版', f'{ROOT}/out/tmp_{key}'
    B.FO = dict(fo, X='共通資料')
    B.SCREEN_TITLE = screen_title
    B.MAN.clear(), B.CROPS.clear(), B.KV.clear()
    docs.SEC.update(people)
    for p in (B.OUT, B.TMP):
        shutil.rmtree(p, ignore_errors=True)
    for p in [B.TMP, f'{B.OUT}/正解'] + [f'{r}/{f}' for r in (B.HARD, B.CLEAN) for f in B.FO.values()]:
        os.makedirs(p)


def T(n):
    return f'{B.TMP}/src_{n}.pdf'


def set_other(g):
    """裏写りの加工で使う「裏面」の画像"""
    B.OTHER = B.raster(g.path, 0)


def fh(d, who, to='03-0155-2199'):
    return f'{d.year}/{d.month:02d}/{d.day:02d} {9 + d.day % 8}:{10 + d.day}  FROM:{who}   TO:{to}   P.001/001'


def digit(s, k=1):
    idx = [i for i, ch in enumerate(s) if ch.isdigit()]
    i = idx[min(k, len(idx) - 1)]
    return s[:i] + str((int(s[i]) + 3) % 10) + s[i + 1:]


# ================= 帳票の汎用レイアウト =================
def block(g, y, rows, x=12, w=None):
    w = w or g.W - 24
    for r in rows:
        k = r[0]
        if k == 'f':      # ('f', [(見出し, 値, キー, 手書き)], 見出し幅)
            fs, w1 = r[1], (r[2] if len(r) > 2 else 28)
            cw = w / len(fs)
            for i, f in enumerate(fs):
                lab, val, key, hand = (list(f) + [None, False])[:4]
                g.lv(x + i * cw, y, w1, cw - w1, 9, lab, val, 10, key=key, hand=hand)
            y += 9
        elif k == 'big':  # ('big', 見出し, 本文, キー, 高さ, {オプション})
            lab, text, key, h = r[1:5]
            o = r[5] if len(r) > 5 else {}
            w1 = o.get('w1', 28)
            g.rc(x, y, w1, h, fill=GR)
            g.t(x + 1.5, y + h / 2 + 1, lab, 8.5)
            g.rc(x + w1, y, w - w1, h)
            if text:
                g.para(x + w1 + 3, y + 6.5, text, o.get('n', int((w - w1 - 8) / 3.6)), o.get('sz', 10), o.get('f', 'G'), hand=o.get('hand', False))
            if key:
                g.box(key, x + w1 + 1, y + 1, w - w1 - 2, h - 2, o.get('val', (text or lab)[:24]))
            y += h
        elif k == 'tbl':  # ('tbl', 列, 行, {オプション})
            o = r[3] if len(r) > 3 else {}
            y = g.tbl(x, y, r[1], r[2], o.get('rh', 7.5), o.get('sz', 9.5), keys=o.get('keys'), hand=o.get('hand'), hsz=o.get('hsz'), hh=o.get('hh'),
                      f=o.get('f', 'G'))
        elif k == 'txt':  # ('txt', 本文, 文字サイズ, 1行の文字数)
            sz = r[2] if len(r) > 2 else 9
            y = g.para(x, y + 4.5, r[1], r[3] if len(r) > 3 and r[3] else int(w / (sz * 0.36)), sz, r[4] if len(r) > 4 else 'G') - 2
        elif k == 'h':    # 小見出し
            g.t(x, y + 5.5, r[1], 10.5, 'B')
            y += 7.5
        elif k == 'gap':
            y += r[1]
    return y


def form(path, title, no=None, formno=None, who=(), appr=(), rows=(), seed=0, land=False, tsz=16, nokey='k_no', aw=22):
    """標準的な帳票: 様式番号・番号・表題・作成者・承認欄・本体"""
    g = Pg(path, land=land, seed=seed)
    R = g.W - 12
    if formno:
        g.t(12, 12, formno, 7.5)
    if no:
        g.t(R, 12, no, 9.5, key=nokey, al='r')
    g.t(g.W / 2, 23, title, tsz, 'B', al='c')
    for i, l in enumerate(who):
        if isinstance(l, tuple):
            g.t(12, 37 + i * 7, l[0], 10, key=l[1])
        else:
            g.t(12, 37 + i * 7, l, 10)
    if appr:
        cols = []
        for a in appr:    # (見出し, 名前|None|'slash', 日付, キー)
            tt, nm, d, key = (list(a) + [None] * 4)[:4]
            cols.append((tt, 'slash', key, '斜線') if nm == 'slash' else ((tt, None, key, '空欄') if nm is None else (tt, DS(g, nm, d), key, dsd(nm, d))))
        g.appr(R - aw * len(cols), 30, cols, w=aw, h=21)
    y = max(37 + 7 * len(who) + 3, 62 if appr else 0)
    y = block(g, y, rows)
    return g, y


def logpdf(path, title, lines, seed=0, keys=None, per=62, sz=7.6, note=''):
    """ログを印刷した紙面（等幅風）"""
    g = Pg(path, seed=seed)
    keys = keys or {}
    for n in range(0, len(lines), per):
        if n:
            g.newpage()
        g.t(12, 12, title, 9, 'B')
        g.t(198, 12, f'{n // per + 1} / {(len(lines) - 1) // per + 1} ページ', 8, al='r')
        g.ln(12, 14, 198, 14, 0.3)
        for i, l in enumerate(lines[n:n + per]):
            g.t(12, 19.5 + i * 4.3, l, sz, 'G', key=keys.get(n + i))
        if note:
            g.t(12, 290, note, 7.5)
    return g.save()


# ================= 画面・写真 =================
def font(s, b=False):
    return ImageFont.truetype(fp('B' if b else 'G'), s)


def frame(sysname, title, W=1180, H=560, status=''):
    im = Image.new('RGB', (W, H), (236, 233, 216))
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, W, 28), fill=(10, 36, 106))
    d.text((10, 5), f'{sysname}  -  {title}', font=font(15), fill='white')
    d.rectangle((0, 28, W, 54), fill=(212, 208, 200))
    d.text((10, 34), 'ファイル(F)    編集(E)    照会(Q)    帳票(R)    ヘルプ(H)', font=font(13), fill='black')
    d.rectangle((0, H - 26, W, H), fill=(212, 208, 200))
    d.text((10, H - 21), status, font=font(13), fill='black')
    return im, d


def stable(d, x, y, cols, rows, boxes, kv, keys=None, rh=26, fs=14, shade=None):
    """画面上の一覧表。cols: (見出し, 幅px, 寄せ)"""
    keys = keys or {}
    cx = x
    for t, w, al in cols:
        d.rectangle((cx, y, cx + w, y + rh), fill=(212, 208, 200), outline=(110, 110, 110))
        d.text((cx + 5, y + 5), t, font=font(fs - 1), fill='black')
        cx += w
    for ri, r in enumerate(rows):
        y += rh
        cx = x
        for ci, ((t, w, al), v) in enumerate(zip(cols, r)):
            d.rectangle((cx, y, cx + w, y + rh), fill=(225, 225, 225) if shade and shade(r) else 'white', outline=(110, 110, 110))
            v = str(v)
            tw = d.textlength(v, font=font(fs))
            d.text((cx + (w - tw) / 2 if al == 'c' else (cx + w - tw - 6 if al == 'r' else cx + 5), y + 5), v, font=font(fs), fill='black')
            k = keys.get((ri, ci))
            if k:
                boxes[k] = (0, cx - 2, y - 2, cx + w + 2, y + rh + 2)
                kv[k] = v
            cx += w
    return y + rh


def sfield(d, x, y, label, val, boxes, kv, key=None, lw=220, vw=300, fs=15):
    """画面上の項目（見出し＋入力欄）"""
    d.text((x, y + 5), label, font=font(fs), fill='black')
    d.rectangle((x + lw, y, x + lw + vw, y + 30), fill='white', outline=(110, 110, 110))
    d.text((x + lw + 8, y + 6), str(val), font=font(fs), fill='black')
    if key:
        boxes[key] = (0, x + lw - 2, y - 2, x + lw + vw + 2, y + 32)
        kv[key] = str(val)
    return y + 40


def up(src, f):
    im, boxes, kv = src
    im = im.resize((int(im.width * f), int(im.height * f)), Image.LANCZOS)
    return im, {k: (b[0],) + tuple(v * f for v in b[1:]) for k, b in boxes.items()}, kv


def photo_bg(W, H, rng, base=(150, 140, 125)):
    """写真風の背景（濃淡のむら）"""
    a = np.zeros((H, W, 3), np.float32) + np.array(base, np.float32)
    lf = cv2.resize(rng.random((6, 8)).astype(np.float32), (W, H), interpolation=cv2.INTER_CUBIC)
    a *= (0.8 + 0.4 * lf)[..., None]
    a += rng.normal(0, 5, (H, W, 1)).astype(np.float32)
    return Image.fromarray(a.clip(0, 255).astype(np.uint8))


def emit_text(ck, name, text, kind, procs, ext='log'):
    folder = B.FO[ck]
    for root in (B.CLEAN, B.HARD):
        open(f'{root}/{folder}/{name}.{ext}', 'w', encoding='utf-8').write(text)
    B.man('B', folder, f'{name}.{ext}', kind, procs, layer='あり（テキストファイル）')
    B.man('A', folder, f'{name}.{ext}', kind, procs, ops='加工なし（テキストファイル）', layer='あり（テキストファイル）')


def finish(DT):
    pickle.dump(dict(MAN=B.MAN, DT=DT, KV=B.KV), open(f'{B.TMP}/state.pkl', 'wb'))
    f = ImageFont.truetype(fp('G'), 15)
    cells = []
    for doc, k, val, im in B.CROPS:
        h, w = im.shape[:2]
        sc = min(110 / h, 500 / w, 2.5)
        im = cv2.resize(im, (max(1, int(w * sc)), max(1, int(h * sc))))
        cell = Image.new('RGB', (520, 150), 'white')
        cell.paste(Image.fromarray(im), (4, 2))
        d = ImageDraw.Draw(cell)
        d.text((4, 114), f'{doc[:28]} {k}', font=f, fill=(0, 0, 160))
        d.text((4, 131), f'→ {val}'[:46], font=f, fill=(160, 0, 0))
        cells.append(cell)
    for n in range(0, len(cells), 55):
        sheet = Image.new('RGB', (520 * 5, 150 * 11), (200, 200, 200))
        for i, c in enumerate(cells[n:n + 55]):
            sheet.paste(c, ((i % 5) * 520, (i // 5) * 150))
        sheet.save(f'{B.TMP}/crops_{n // 55:02d}.png')
    tot = sum(os.path.getsize(os.path.join(r, x)) for r, _, fs in os.walk(B.HARD) for x in fs)
    print('files', len(B.MAN), 'crops', len(B.CROPS), 'hard MB', round(tot / 1e6, 1))


# ================= Excel・正解表 =================
FN = '游ゴシック'
HF = PatternFill('solid', fgColor='D9E1F2')
TH = Side(style='thin', color='999999')
BD = Border(left=TH, right=TH, top=TH, bottom=TH)


def sheet(wb, title, head, rows, widths, wrap=(), fmts=None, first=False):
    ws = wb.active if first else wb.create_sheet()
    ws.title = title
    ws.append(head)
    for r in rows:
        ws.append(list(r))
    for ci, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(ci)].width = w
    for c in ws[1]:
        c.font, c.fill, c.border = Font(name=FN, size=10, bold=True), HF, BD
        c.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
    for row in ws.iter_rows(min_row=2):
        for c in row:
            c.font = Font(name=FN, size=10)
            c.alignment = Alignment(vertical='top', wrap_text=(c.column in wrap))
            c.border = BD
            if fmts and c.column in fmts:
                c.number_format = fmts[c.column]
    ws.freeze_panes = 'A2'
    ws.auto_filter.ref = ws.dimensions
    return ws


def roll(v):
    return A if A in v else (U if U in v else N)


def book(sp, ST):
    """sp: 領域の定義（rcm, proc, fo, samples, premises, masters, answers）"""
    OUT, TMP = f'{ROOT}/out/{sp["name"]}', f'{ROOT}/out/tmp_{sp["key"]}'
    MAN = list(ST['MAN'])
    for fname, sheets, kind, procs in sp['masters']:   # 共通資料のExcel
        wb = Workbook()
        for i, (title, head, rows, widths, fmts) in enumerate(sheets):
            sheet(wb, title, head, rows, widths, fmts=fmts, first=(i == 0))
        for root in ('A_難版', 'B_対照版'):
            wb.save(f'{OUT}/{root}/共通資料/{fname}')
        for s in 'AB':
            MAN.append(dict(set=s, path=f'共通資料/{fname}', kind=kind, procs=procs, ops='加工なし（Excelの表）' if s == 'A' else '-', layer='あり（セルの値）', stage=1,
                            unread='-', impact='-', trap='-'))
    wb = Workbook()
    sheet(wb, 'リスクと統制', ['統制ID', '業務', 'リスク', '統制の内容', '頻度', '種別'], sp['rcm'], [8, 18, 40, 76, 12, 14], wrap=(3, 4), first=True)
    sheet(wb, '手続一覧', ['手続ID', '統制ID', '手続の種類', '手続の内容', '対象の証跡', '対象', '証跡フォルダ'], [list(p) + [sp['fo'][p[0]] + '、共通資料'] for p in sp['proc']],
          [8, 8, 22, 90, 44, 12, 28], wrap=(3, 4, 5, 7))
    sheet(wb, 'サンプル一覧', ['手続ID', '単位', '識別番号', '内容', '証跡ファイル名の先頭'], sp['samples'], [10, 24, 22, 50, 36], wrap=(4,))
    sheet(wb, '前提', ['項目', '内容'], sp['premises'], [20, 110], wrap=(2,))
    for root in ('A_難版', 'B_対照版'):
        wb.save(f'{OUT}/{root}/手続一覧.xlsx')
    for s in 'AB':
        MAN.append(dict(set=s, path='手続一覧.xlsx', kind='手続一覧（リスクと統制・手続・サンプル）', procs='全般', ops='加工なし（Excelの表）' if s == 'A' else '-', layer='あり（セルの値）',
                        stage=1, unread='-', impact='-', trap='-'))

    def files_for(stems, set_):
        out = []
        for st in stems:
            out += [m['path'] for m in MAN if m['set'] == set_ and os.path.basename(m['path']).startswith(st)]
        return sorted(set(out))

    ocr = json.load(open(f'{TMP}/ocr_ref.json')) if os.path.exists(f'{TMP}/ocr_ref.json') else []
    oc = {(r[0], r[1]): r for r in ocr}
    pt = {p[0]: p for p in sp['proc']}
    ans = sp['answers']
    prow, srow = [], []
    for a in ans:
        p = pt[a['id']]
        a['hard'], a['clean'] = roll([s[1] for s in a['S']]), roll([s[2] for s in a['S']])
        bad = '、'.join(f'{s[0]}（{s[1]}）' for s in a['S'] if s[1] != N) or '-'
        prow.append([a['id'], p[1], p[2], p[3], a['hard'], a['clean'], a.get('kind', '-'), a.get('diff', '-'), bad])
        for s in a['S']:
            fa = files_for(s[5], 'A')
            if not fa:
                print('対象ファイルなし', a['id'], s[0], s[5])
            srow.append([a['id'], p[2], s[0], s[6] if len(s) > 6 else '-', s[1], s[2], '、'.join(s[4]) or '-', s[3], '\n'.join(fa)])
    wb = Workbook()
    legend = [['この表の位置づけ', '検証対象（AI）には渡さない、答え合わせ用の資料'],
              ['A_難版', '可読性を難しくした証跡。FAX風、かすれ、傾き、撮影風、裏写り、行ずれ、誤った文字情報、判読不能箇所などを含む'],
              ['B_対照版', 'A_難版と同じ内容で、読みやすい版。A との結果の差が「読み取りに起因する誤り」に当たる'],
              ['正解の単位', 'サンプルのある手続はサンプルごと。全件や図が対象の手続は「検出すべき対象」ごと'],
              ['手続単位の正解の決め方', '単位に1件でも「不備あり」があれば手続は「不備あり」。それ以外で1件でも「判断できない」があれば「判断できない」。すべて「不備なし」なら「不備なし」'],
              ['可読性の段階', '1: 問題なく読める／2: 読みにくいが人は読める／3: 人でも読めない箇所がある'],
              ['判定への影響', '段階3のファイルのうち、読めない箇所が判定に必要な箇所かどうか。「あり」の場合、その単位の正解は「判断できない」'],
              ['仕込みの種類', '不備＝統制の逸脱／ひっかけ＝不備に見えるが正常／判読不能＝段階3が判定に必要な箇所にある／証跡の不足＝裏付資料がない／文字情報の罠＝PDFの文字情報が画像と異なる'],
              ['文字読取ソフトでの読取率（参考）', '一般的な文字読取ソフト（tesseract 日本語）で主要項目の値が読み取れた割合。難しさの目安であり、正解ではない'],
              ['注意', '会社名・人名・番号はすべて架空。実在のものと一致しても無関係']]
    sheet(wb, '読み方', ['項目', '説明'], legend, [30, 130], wrap=(2,), first=True)
    sheet(wb, '手続別の正解', ['手続ID', '統制ID', '手続の種類', '手続の内容', '正解（A_難版）', '正解（B_対照版）', '不備の内容', '見つけにくさ', '不備・判断不能の単位'], prow,
          [8, 8, 22, 80, 14, 14, 30, 12, 40], wrap=(3, 4, 7, 9))
    sheet(wb, '単位別の正解', ['手続ID', '手続の種類', '単位（サンプル・検出対象）', '相手先・対象', '正解（A_難版）', '正解（B_対照版）', '仕込みの種類', '根拠・注記', '対象ファイル（A_難版）'], srow,
          [8, 22, 24, 26, 14, 14, 20, 80, 52], wrap=(2, 4, 7, 8, 9))
    frow = []
    for m in MAN:
        o = oc.get((m['set'], m['path']))
        frow.append([{'A': 'A_難版', 'B': 'B_対照版'}[m['set']], m['path'], m['kind'], m['procs'], m['ops'], m['layer'], m['stage'], m['unread'], m['impact'], m['trap'],
                     (o[2] / o[3]) if o and o[3] else None, o[3] if o else None])
    frow.sort(key=lambda r: (r[0], r[1]))
    sheet(wb, 'ファイル別の可読性', ['版', 'ファイル', '文書の種類', '関係する手続', '画質の加工', '文字情報（コードでの取得）', '可読性の段階', '人でも読めない箇所', '判定への影響', '文字情報の罠',
                              '文字読取ソフトでの読取率（参考）', '読取率の対象項目数'], frow, [10, 50, 30, 14, 44, 40, 9, 36, 9, 50, 14, 10], wrap=(3, 5, 6, 8, 10), fmts={11: '0%'})
    n, np_, ns = len(frow) + 1, len(prow) + 1, len(srow) + 1
    f = "'ファイル別の可読性'"
    ws2 = wb.create_sheet('集計')
    ws2.append(['A_難版 の構成', '件数', '備考'])
    items = [('ファイル数', f'=COUNTIF({f}!A2:A{n},"A_難版")', ''), ('可読性 段階1', f'=COUNTIFS({f}!A2:A{n},"A_難版",{f}!G2:G{n},1)', '問題なく読める'),
             ('可読性 段階2', f'=COUNTIFS({f}!A2:A{n},"A_難版",{f}!G2:G{n},2)', '読みにくいが人は読める'), ('可読性 段階3', f'=COUNTIFS({f}!A2:A{n},"A_難版",{f}!G2:G{n},3)', '人でも読めない箇所がある'),
             ('　うち判定への影響あり', f'=COUNTIFS({f}!A2:A{n},"A_難版",{f}!I2:I{n},"あり")', 'その単位は「判断できない」が正解'),
             ('文字情報なし（画像のみ）', f'=COUNTIFS({f}!A2:A{n},"A_難版",{f}!F2:F{n},"なし*")', 'PDF・画像ファイル・Excel貼付'),
             ('文字情報あり（正しい）', f'=COUNTIFS({f}!A2:A{n},"A_難版",{f}!F2:F{n},"あり（正しい*")+COUNTIFS({f}!A2:A{n},"A_難版",{f}!F2:F{n},"あり（セル*")+COUNTIFS({f}!A2:A{n},"A_難版",{f}!F2:F{n},"あり（テキスト*")',
              '電子PDF・Excelの表・テキスト'),
             ('文字情報あり（誤りを含む）', f'=COUNTIFS({f}!A2:A{n},"A_難版",{f}!F2:F{n},"あり（誤り*")', ''), ('文字情報が混在', f'=COUNTIFS({f}!A2:A{n},"A_難版",{f}!F2:F{n},"混在*")', 'ページにより有無が異なる'),
             ('手続数', f"=COUNTA('手続別の正解'!A2:A{np_})", ''), ('　正解が不備なし（A_難版）', f"=COUNTIF('手続別の正解'!E2:E{np_},\"不備なし\")", ''),
             ('　正解が不備あり（A_難版）', f"=COUNTIF('手続別の正解'!E2:E{np_},\"不備あり\")", ''), ('　正解が判断できない（A_難版）', f"=COUNTIF('手続別の正解'!E2:E{np_},\"判断できない\")", ''),
             ('判定の単位の数', f"=COUNTA('単位別の正解'!A2:A{ns})", ''), ('　不備あり（A_難版）', f"=COUNTIF('単位別の正解'!E2:E{ns},\"不備あり\")", ''),
             ('　判断できない（A_難版）', f"=COUNTIF('単位別の正解'!E2:E{ns},\"判断できない\")", ''), ('　ひっかけを含む', f"=COUNTIF('単位別の正解'!G2:G{ns},\"*ひっかけ*\")", '不備に見えるが正常'),
             ('　文字情報の罠を含む', f"=COUNTIF('単位別の正解'!G2:G{ns},\"*文字情報の罠*\")", '')]
    for it in items:
        ws2.append(list(it))
    for row in ws2.iter_rows():
        for c in row:
            c.font, c.border = Font(name=FN, size=10, bold=(c.row == 1)), BD
            if c.row == 1:
                c.fill = HF
    for col, w in (('A', 34), ('B', 10), ('C', 44)):
        ws2.column_dimensions[col].width = w
    wb.save(f'{OUT}/正解/正解表.xlsx')
    js = dict(meta=dict(name=sp['name'], note='すべて架空のデータ', rule='単位に不備ありが1件でもあれば手続は不備あり。なければ、判断できないが1件でもあれば判断できない。それ以外は不備なし'),
              procedures=[dict(id=a['id'], control=pt[a['id']][1], type=pt[a['id']][2], text=pt[a['id']][3], answer_hard=a['hard'], answer_clean=a['clean'], deficiency=a.get('kind', '-'),
                               units=[dict(unit=s[0], answer_hard=s[1], answer_clean=s[2], tags=s[4], note=s[3], files_hard=files_for(s[5], 'A'), files_clean=files_for(s[5], 'B'))
                                      for s in a['S']]) for a in ans],
              files=[dict(m, ocr_rate=(round(oc[(m['set'], m['path'])][2] / oc[(m['set'], m['path'])][3], 3) if (m['set'], m['path']) in oc and oc[(m['set'], m['path'])][3] else None))
                     for m in MAN])
    json.dump(js, open(f'{OUT}/正解/正解.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    pickle.dump(dict(ans=ans, prow=prow, srow=srow, frow=frow, MAN=MAN), open(f'{TMP}/book.pkl', 'wb'))
    r = subprocess.run(['python3', RECALC, f'{OUT}/正解/正解表.xlsx', '90'], capture_output=True, text=True)
    print('  正解表の再計算:', 'OK' if '"success"' in r.stdout and '"total_errors": 0' in r.stdout else r.stdout[:300])
    print('  手続', dict(Counter(p[4] for p in prow)), '対照', dict(Counter(p[5] for p in prow)), '単位', len(srow), dict(Counter(s[4] for s in srow)))
    print('  段階(A)', dict(Counter(f[6] for f in frow if f[0] == 'A_難版')), 'files A', sum(1 for f in frow if f[0] == 'A_難版'), 'B', sum(1 for f in frow if f[0] == 'B_対照版'))


# ================= 検証 =================
class Ctx:
    """領域ごとの再計算で使う道具"""

    def __init__(s, sp):
        s.OUT, s.TMP = f'{ROOT}/out/{sp["name"]}', f'{ROOT}/out/tmp_{sp["key"]}'
        s.ST = pickle.load(open(f'{s.TMP}/state.pkl', 'rb'))
        s.BK = pickle.load(open(f'{s.TMP}/book.pkl', 'rb'))
        s.DT, s.KV = s.ST['DT'], s.ST['KV']
        s.errs, s.traps, s.calc = [], [], {}
        s.stems = {os.path.splitext(os.path.basename(m['path']))[0] for m in s.BK['MAN'] if m['set'] == 'B'}

    def chk(s, cond, msg):
        if not cond:
            s.errs.append(msg)

    def xl(s, name, si=0):
        ws = load_workbook(f'{s.OUT}/B_対照版/共通資料/{name}', data_only=True).worksheets[si]
        return [list(r) for r in ws.iter_rows(min_row=2, values_only=True)]

    def text(s, rel):
        return open(f'{s.OUT}/B_対照版/{rel}', encoding='utf-8').read()


num = lambda v: int(re.sub(r'[^\d\-]', '', str(v)))
fnum = lambda v: float(re.sub(r'[^\d\-\.]', '', str(v)))
who = lambda v: v.split()[1]
day = lambda v: v.date() if isinstance(v, dt.datetime) else v
SKIP = ('印', '斜線', '空欄', '署名', '手書き', 'ゴム', 'チェック')


def verify(sp, c):
    logging.disable(logging.CRITICAL)
    BK, KV, OUT, errs, chk = c.BK, c.KV, c.OUT, c.errs, c.chk
    imp = {m['path'] for m in BK['MAN'] if m['set'] == 'A' and m['impact'] == 'あり'}
    n = 0
    for a in BK['ans']:
        for s, row in zip(a['S'], [r for r in BK['srow'] if r[0] == a['id']]):
            k = (a['id'], s[0])
            hard = U if (c.calc.get(k) == N and k not in sp.get('noimpact', ()) and any(f in imp for f in row[8].split('\n'))) else c.calc.get(k)
            chk(c.calc.get(k) == s[2], f'対照版の正解が不一致 {k}: 再計算={c.calc.get(k)} 正解表={s[2]}')
            chk(hard == s[1], f'難版の正解が不一致 {k}: 期待={hard} 正解表={s[1]}')
            n += 1
    chk(n == len(c.calc), f'件数 {n} vs {len(c.calc)}')
    print(f'1. 正解の再計算: {n} 単位を照合。ひっかけの成立を確認: {len(c.traps)} 件')
    for t in c.traps:
        print('     -', t)
    norm = lambda s: re.sub(r'[\s　]', '', s)
    tot_ = hit_ = 0
    for m in BK['MAN']:
        stem = os.path.splitext(os.path.basename(m['path']))[0]
        if m['set'] != 'B' or not m['path'].endswith('.pdf') or stem not in KV:
            continue
        txt = norm(''.join(p.get_text() for p in fitz.open(f'{OUT}/B_対照版/{m["path"]}')))
        for k, v in KV[stem].items():
            if any(w in v for w in SKIP) or k.startswith('x_') or k in sp.get('nolayer', ()):
                continue
            tot_ += 1
            if norm(v) in txt:
                hit_ += 1
            else:
                errs.append(f'対照版の文字情報に値なし {stem} {k}={v}')
    print(f'2. 対照版の文字情報: {hit_}/{tot_} 項目を確認（印影・手書き風の欄は対象外）')
    nt = 0
    for m in BK['MAN']:
        if m['set'] == 'A' and m['trap'] != '-':
            p = f'{OUT}/A_難版/{m["path"]}'
            t1 = norm(''.join(pg.get_text() for pg in fitz.open(p)))
            t2 = norm(subprocess.run(['pdftotext', p, '-'], capture_output=True, text=True).stdout)
            for part in m['trap'].split('；'):
                new, old = norm(re.search(r'文字情報は「(.+?)」', part).group(1)), norm(re.search(r'画像は「(.+?)」', part).group(1))
                chk(new in t1 and new in t2 and new != old, f'罠の値が取り出せない {m["path"]} {new}')
                nt += 1
        if m['set'] == 'A' and m['layer'].startswith('なし') and m['path'].endswith('.pdf'):
            chk(''.join(pg.get_text() for pg in fitz.open(f'{OUT}/A_難版/{m["path"]}')).strip() == '', f'画像のみのはずが文字情報あり {m["path"]}')
    print(f'3. 文字情報の罠: {nt} 箇所を2種類の取り出し方法で確認')
    cnt = {}
    for root in ('A_難版', 'B_対照版'):
        for dp, _, fs in os.walk(f'{OUT}/{root}'):
            for f in fs:
                p = os.path.join(dp, f)
                ext = f.rsplit('.', 1)[1].lower()
                cnt[(root, ext)] = cnt.get((root, ext), 0) + 1
                try:
                    if ext == 'pdf':
                        assert len(fitz.open(p)) >= 1
                    elif ext in ('jpg', 'png'):
                        Image.open(p).verify()
                    elif ext == 'xlsx':
                        load_workbook(p).close()
                    else:
                        assert len(open(p, encoding='utf-8').read()) > 10
                except Exception as e:
                    errs.append(f'開けない {p}: {e}')
    sa = {os.path.splitext(m['path'])[0] for m in BK['MAN'] if m['set'] == 'A'}
    sb = {os.path.splitext(m['path'])[0] for m in BK['MAN'] if m['set'] == 'B'}
    chk(sa == sb, f'A/B の対応ずれ {sa ^ sb}')
    chk(sum(cnt.values()) == len(BK['MAN']), f'ファイル数 {sum(cnt.values())} と一覧 {len(BK["MAN"])} が不一致')
    print('4. ファイル:', {f'{k[0]}:{k[1]}': v for k, v in sorted(cnt.items())})
    print('結果:', 'すべて一致' if not errs else f'{len(errs)} 件の不一致')
    for e in errs[:40]:
        print('  NG', e)
    return not errs


# ================= README・プレビュー・ZIP =================
def pack(sp, scripts):
    OUT, TMP = f'{ROOT}/out/{sp["name"]}', f'{ROOT}/out/tmp_{sp["key"]}'
    BK = pickle.load(open(f'{TMP}/book.pkl', 'rb'))
    ocr = json.load(open(f'{TMP}/ocr_ref.json'))
    fr = [f for f in BK['frow'] if f[0] == 'A_難版']
    ev = [f for f in fr if not f[1].startswith('共通資料/') and f[1] != '手続一覧.xlsx']
    st = Counter(f[6] for f in ev)
    imp = sum(1 for f in ev if f[8] == 'あり')
    lay = Counter('なし（画像のみ）' if f[5].startswith('なし') else ('あり（誤りを含む）' if '誤り' in f[5] else ('混在' if f[5].startswith('混在') else 'あり（正しい）')) for f in fr)
    ext = Counter(f[1].rsplit('.', 1)[1] for f in fr)
    ra = sum(r[2] for r in ocr if r[0] == 'A') / max(1, sum(r[3] for r in ocr if r[0] == 'A'))
    rb = sum(r[2] for r in ocr if r[0] == 'B') / max(1, sum(r[3] for r in ocr if r[0] == 'B'))
    ops = Counter()
    for f in ev:
        for o in f[4].split('、'):
            ops[o.split('約')[0] if o.startswith('傾き') else o] += 1
    nunit = len(BK['srow'])
    rows = []
    for a, p in zip(BK['ans'], BK['prow']):
        tags = Counter(t for s in a['S'] for t in s[4])
        rows.append(f'| {a["id"]} | {p[2]} | {p[1]} | {len(a["S"])} | {p[4]} | {p[5]} | {"、".join(f"{k}{v}" for k, v in tags.items()) or "-"} |')
    nl = chr(10)
    md = f'''# {sp["title"]} 検証データ（小）

内部監査手続をAIで評価する仕組みの検証用データです。会社名・人名・番号はすべて架空です。

**注意：このREADMEと `正解/` フォルダには正解が書かれています。検証対象には渡さないでください。**

## 1. 構成

| フォルダ | 内容 | 用途 |
|---|---|---|
| `A_難版/` | 手続一覧、共通資料、証跡（可読性を難しくした版） | 検証対象への入力（本番想定） |
| `B_対照版/` | A と同じ内容で、読みやすい版 | 検証対象への入力（比較用） |
| `正解/` | 正解表.xlsx、正解.json | 答え合わせ用。検証対象には渡さない |
| `生成スクリプト（参考）/` | データを作ったプログラム | 規模の拡張や作り直しの参考 |

- A と B は、同じ統制・同じ取引・同じ不備を含みます。違いは証跡の読みやすさだけです。
- A と B の結果の差が「読み取りに起因する誤り」、B でも誤る分が「判断に起因する誤り」に当たります。

## 2. 題材と、この領域で試せること

{sp["intro"]}

| 手続 | 見る証跡 | 求められること |
|---|---|---|
{nl.join(f"| {a} | {b} | {c_} |" for a, b, c_ in sp["types"])}

- 統制 {len(sp["rcm"])}、手続 {len(sp["proc"])}、判定の単位 {nunit}

## 3. 正解の内訳

| 手続 | 種類 | 統制 | 単位数 | 正解（A_難版） | 正解（B_対照版） | 仕込み（件数） |
|---|---|---|---|---|---|---|
{nl.join(rows)}

- 手続単位の正解：単位に「不備あり」が1件でもあれば「不備あり」。なければ、「判断できない」が1件でもあれば「判断できない」。
- 仕込みの種類
  - 不備：{sp["defs"]}
  - ひっかけ：不備に見えるが正常（{sp["trapdesc"]}）
  - 判読不能：人でも読めない箇所が判定に必要な箇所にある（A のみ。B では「不備なし」）
  - 文字情報の罠：PDFから取り出せる文字情報が画像と異なる（A のみ）

## 4. 可読性（A_難版）

証跡 {len(ev)} ファイル（手続一覧と共通資料を除く）の内訳：

| 段階 | 状態 | ファイル数 |
|---|---|---|
| 1 | 問題なく読める | {st[1]} |
| 2 | 読みにくいが人は読める | {st[2]} |
| 3 | 人でも読めない箇所がある | {st[3]}（うち判定に影響あり {imp}） |

文字情報（プログラムでの取得）の内訳（全 {len(fr)} ファイル）：

| 種類 | ファイル数 |
|---|---|
{nl.join(f"| {k} | {v} |" for k, v in lay.most_common())}

- 形式：{"、".join(f"{k} {v}" for k, v in ext.most_common())}
- 画質の加工（重複あり）：{"、".join(f"{k} {v}" for k, v in ops.most_common() if not k.startswith("加工なし"))}
- 参考：一般的な文字読取ソフト（tesseract 日本語）で主要項目が読めた割合は、A_難版 {ra:.0%}、B_対照版 {rb:.0%}。難しさの目安です。
- 段階2の主要項目は、拡大して人が読めることを目視で確認しています。段階3の箇所と判定への影響は、正解表の「ファイル別の可読性」に記載しています。

## 5. 使い方

1. `A_難版/` の `手続一覧.xlsx` と証跡一式を検証対象に入力し、手続ごと・単位ごとの判定を得る。
2. `B_対照版/` でも同じことを行う。
3. `正解/正解表.xlsx`（または `正解.json`）と突き合わせる。見るべき点：不備の見逃し、指摘しすぎ（ひっかけ）、「判断できない」と言うべき場面での断定、文字情報の罠、計算の誤り。

## 6. 前提と制約

{nl.join("- " + x for x in sp["notes"])}
- 判定の基準は、共通資料の規程・基準・設計書に書いてあります。手続一覧には「何を確かめるか」だけを書いています。
- ファイル名は内容が分かる名前にしています。無関係な資料の混入はありません。
- 「人でも読めない」の線引きは作成者の目視によります。利用時に見直す余地があります。
- 印影・手書きは対照版でも画像または手書き風の書体です。
- 文書に埋め込んだフォントは SIL Open Font License のもの（BIZ UDゴシック／明朝、Yomogi、Zen Kurenaido、Klee One、DotGothic16）です。

## 7. 検証の記録

- 正解は、証跡に印字した値とデータから独立に再計算した結果と、{nunit} 単位すべて一致することを確認しています。
- ひっかけが意図どおり成立していること、対照版PDFの文字情報に主要項目の値が含まれること、難版の「文字情報の罠」が実際に取り出せることを確認しています。
- 全ファイルが開けること、A と B のファイルが1対1で対応することを確認しています。
'''
    open(f'{OUT}/README.md', 'w', encoding='utf-8').write(md)
    sd_ = f'{OUT}/生成スクリプト（参考）'
    shutil.rmtree(sd_, ignore_errors=True)
    os.makedirs(sd_)
    for f in ['common.py', 'render.py', 'degrade.py', 'build.py', 'docs.py', 'fw.py', 'run.py', 'ocr_ref.py'] + scripts:
        shutil.copy(f'{ROOT}/src/{f}', sd_)
    open(f'{sd_}/実行方法.txt', 'w', encoding='utf-8').write(
        f'実行: python run.py {sp["key"]}（証跡の生成 → 文字読取の参考値 → 正解表 → 検証 → 梱包 を順に行う）\n'
        '共通部品: common.py（暦・書式）、render.py（文書の描画）、degrade.py（画質の加工）、build.py（難版・対照版の出力）、fw.py（帳票の汎用レイアウト・正解表・検証）\n'
        'docs.py は販売プロセス版の帳票（印影の部品だけを使う）。実行には販売版の data.py / screens.py も同じフォルダに必要\n'
        '必要なもの: Python 3.11以降、reportlab / pymupdf / pillow / numpy / opencv-python-headless / openpyxl、tesseract（参考値のみ）、LibreOffice（正解表の再計算）\n'
        'フォント: Google Fonts の BIZ UDGothic(Regular/Bold)、BIZ UDMincho、Yomogi、Klee One、Zen Kurenaido、DotGothic16 を fonts/ に置く\n'
        '注意: 作業フォルダのパス（common.py の ROOT）は環境に合わせて書き換えること。乱数の種は固定のため、同じ内容が再生成される\n')
    W = 560
    f = ImageFont.truetype(fp('B'), 24)
    ims = []
    for p, pg, cap in sp['preview']:
        full = f'{OUT}/A_難版/{p}'
        if p.endswith('.pdf'):
            pm = fitz.open(full)[pg].get_pixmap(dpi=80)
            im = Image.frombytes('RGB', (pm.w, pm.h), pm.samples)
        else:
            im = Image.open(full).convert('RGB')
        im = im.resize((W, int(im.height * W / im.width)))
        c = Image.new('RGB', (W, 800), 'white')
        c.paste(im.crop((0, 0, W, min(im.height, 756))), (0, 44))
        d = ImageDraw.Draw(c)
        d.rectangle((0, 0, W, 42), fill=(30, 40, 70))
        d.text((10, 8), cap, font=f, fill='white')
        ims.append(c)
    nc = 4
    nr = (len(ims) + nc - 1) // nc
    sh = Image.new('RGB', (W * nc + 30, 810 * nr), (120, 120, 120))
    for i, c in enumerate(ims):
        sh.paste(c, ((i % nc) * (W + 10), (i // nc) * 810))
    sh.save(f'{ROOT}/out/プレビュー_{sp["key"]}_難版の例.png')
    zp = f'{ROOT}/out/{sp["name"]}.zip'
    if os.path.exists(zp):
        os.remove(zp)
    with zipfile.ZipFile(zp, 'w', zipfile.ZIP_DEFLATED) as z:
        for dp, _, fs in os.walk(OUT):
            for x in sorted(fs):
                full_ = os.path.join(dp, x)
                z.write(full_, os.path.join(sp['name'], os.path.relpath(full_, OUT)))
    shutil.copy(f'{OUT}/正解/正解表.xlsx', f'{ROOT}/out/正解表_{sp["key"]}.xlsx')
    print('zip MB', round(os.path.getsize(zp) / 1e6, 1), 'files', sum(len(fs) for _, _, fs in os.walk(OUT)), '| 証跡', len(ev), dict(st), '影響', imp, f'| OCR A {ra:.0%} B {rb:.0%}')


# ================= 図の部品 =================
def arrow(g, x1, y1, x2, y2, lw=0.6, dash=None, head=2.4, col=(0, 0, 0)):
    import math
    g.ln(x1, y1, x2, y2, lw, dash, col)
    a = math.atan2(y2 - y1, x2 - x1)
    for da in (2.65, -2.65):
        g.ln(x2, y2, x2 + head * math.cos(a + da), y2 + head * math.sin(a + da), lw, None, col)


def stampcell(g, name, x, y, d=8.5, key=None, date=None):
    """表のセルなどに置く小さな認印"""
    g.im(SL(g, name), x + g.rng.uniform(-0.6, 0.6), y + g.rng.uniform(-0.5, 0.5), d, d)
    if key:
        g.box(key, x - 1, y - 1, d + 2, d + 2, f'認印 {name}')
