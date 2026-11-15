# -*- coding: utf-8 -*-
"""検証: データから正解を独立に再計算して正解表と突き合わせる。ファイルの健全性も確認する"""
import os, re, pickle, subprocess, json, email, sys, logging
import pymupdf as fitz
from PIL import Image
from openpyxl import load_workbook
from common import *

logging.disable(logging.CRITICAL)
NAME = '販売プロセス_検証データ_小'
OUT = f'{ROOT}/out/{NAME}'
ST = pickle.load(open(f'{ROOT}/out/tmp/state.pkl', 'rb'))
BK = pickle.load(open(f'{ROOT}/out/tmp/book.pkl', 'rb'))
DT, KV = ST['DT'], ST['KV']
C = DT['C']
N, A, U = '不備なし', '不備あり', '判断できない'
errs = []


def chk(cond, msg):
    if not cond:
        errs.append(msg)


# ---- 1. 正解の独立再計算（対照版＝内容そのものの正解） ----
calc = {}
dl = DT['DELEG']
for x in DT['C1']:
    need = '課長' if x['req'] <= 5_000_000 else ('部長' if x['req'] <= 30_000_000 else '役員')
    if need == '課長':
        ok = x['ka'] is not None
    elif need == '部長':
        ok = x['bu'] is not None and (x.get('bu_by') is None or (x['bu_by'] == dl['to'] and dl['a'] <= x['bu'] <= dl['b'] and dl['ok'] <= dl['a']))
    else:
        ok = x['yk'] is not None
    last = max(d for d in (x['ka'], x['bu'], x['yk'], x['kr']) if d)
    ok = ok and last <= x['md'] and C[x['c']]['limit'] == x['req']
    calc[('P01', f'S{x["s"]}')] = N if ok else A
    calc[('P02', f'S{x["s"]}')] = N if 0 <= (x['app'] - x['rd']).days <= 183 else A
for x in DT['C2']:
    o = x['o']
    po = [(PROD[p][0], q, pr) for p, q, pr in o['lines']] if x.get('rev') else x['po_lines']
    calc[('P03', f'S{x["s"]}')] = N if po == [(PROD[p][0], q, pr) for p, q, pr in o['lines']] else A
    calc[('P04', f'S{x["s"]}')] = N if C[o['c']]['rep'] != KA[C[o['c']]['sec']] else A
for x in DT['C3']:
    r, od = x['rate'], x['o']['od']
    ok = True if r <= 5 else ((x['ka'] is not None and x['ka'] <= od) if r <= 15 else (x['bu'] is not None and x['bu'] <= od))
    calc[('P05', f'S{x["s"]}')] = N if ok else A
led = {}
for r in DT['rows']:
    led.setdefault(r[0], []).append(r)
for x in DT['C4']:
    o = x['o']
    rows = led[o['uno']]
    ok = all(r[3] == o['sd'] for r in rows) and [(r[6], r[8]) for r in rows] == [(PROD[p][0], q) for p, q, _ in o['lines']] and x['recv'] >= o['sd']
    calc[('P06', f'S{x["s"]}')] = N if ok else A
for x in DT['C5']:
    r = x['r']
    amt = r['q'] * r['pr']
    ok = r['ka'] is not None and r['kr'] is not None and (amt <= 500_000 or r['bu'] is not None)
    ok = ok and max(d for d in (r['ka'], r['bu'], r['kr']) if d) <= r['cd']
    calc[('P07', f'S{x["s"]}')] = U if x['s'] == 3 else (N if ok else A)   # S3 は申請書が別取引（証跡の取り違え）
    calc[('P08', f'S{x["s"]}')] = N if r['by'] != KRK else A
    chk(led[r['ano']][0][10] == -amt and led[r['ano']][0][3] == r['cd'], f'ledger cancel {r["ano"]}')
for m in DT['C6']:
    sid = f'{m["m"].year}年{m["m"].month}月度'
    calc[('P09', sid)] = N if all(r['state'] == '消込済' or r['note'] for r in m['rows']) else A
    me = (m['m'].replace(day=28) + dt.timedelta(days=5)).replace(day=1) - dt.timedelta(days=1)
    calc[('P10', sid)] = N if (m['by'] != KRK and 1 <= bd_count(me, m['ok']) <= 5 and is_bd(m['ok'])) else A
for m in DT['C7']:
    calc[('P11', f'{m["m"].year}年{m["m"].month}月末')] = N if all(r['cm'] for r in m['rows'] if r['a'][4]) else A
fy = lambda d: d <= D(2026, 3, 31)
for x in DT['C8']:
    o = x['o']
    chk(all(r[3] == o['ld'] for r in led[o['uno']]), f'ledger date {o["uno"]}')
    calc[('P12', f'S{x["s"]}')] = N if fy(o['sd']) == fy(o['ld']) else A
calc[('P13', '確認表')] = N if 1 <= bd_count(D(2026, 3, 31), DT['C8M']['ok']) <= 5 else A
hard_over = {('P03', 'S1'): U, ('P05', 'S3'): U, ('P06', 'S4'): U}   # 判定に必要な箇所が判読不能
n = 0
for a in BK['ans']:
    for s in a['S']:
        k = (a['id'], s[0])
        chk(calc.get(k) == s[2], f'対照版の正解が不一致 {k}: 再計算={calc.get(k)} 正解表={s[2]}')
        chk(hard_over.get(k, calc.get(k)) == s[1], f'難版の正解が不一致 {k}: 期待={hard_over.get(k, calc.get(k))} 正解表={s[1]}')
        n += 1
chk(n == len(calc), f'件数 {n} vs {len(calc)}')
print(f'1. 正解の再計算: {n} 件を照合')

# ---- 2. 対照版PDFの文字情報に主要項目の値が入っているか ----
norm = lambda s: re.sub(r'[\s　]', '', s)
tot = hit = 0
for m in BK['MAN']:
    stem = os.path.splitext(os.path.basename(m['path']))[0]
    if m['set'] != 'B' or not m['path'].endswith('.pdf') or stem not in KV:
        continue
    txt = norm(''.join(p.get_text() for p in fitz.open(f'{OUT}/B_対照版/{m["path"]}')))
    for k, v in KV[stem].items():
        if any(w in v for w in ('印', '斜線', '空欄', '署名', '手書き', 'ゴム')):
            continue
        tot += 1
        if norm(v) in txt:
            hit += 1
        elif '注文書' not in stem and '対応記録' not in stem and '与信申請書' not in stem and '滞留一覧' not in stem:
            errs.append(f'対照版の文字情報に値なし {stem} {k}={v}')
print(f'2. 対照版の文字情報: {hit}/{tot} 項目を確認（手書き風の欄は対象外）')

# ---- 3. 難版の「文字情報の罠」が実際に取り出せるか ----
nt = 0
for m in BK['MAN']:
    if m['set'] == 'A' and m['trap'] != '-':
        p = f'{OUT}/A_難版/{m["path"]}'
        t1 = norm(''.join(pg.get_text() for pg in fitz.open(p)))
        t2 = norm(subprocess.run(['pdftotext', p, '-'], capture_output=True, text=True).stdout)
        for part in m['trap'].split('；'):
            new = norm(re.search(r'文字情報は「(.+?)」', part).group(1))
            chk(new in t1 and new in t2, f'罠の値が取り出せない {m["path"]} {new}')
            nt += 1
    if m['set'] == 'A' and m['layer'].startswith('なし') and m['path'].endswith('.pdf'):
        t = ''.join(pg.get_text() for pg in fitz.open(f'{OUT}/A_難版/{m["path"]}')).strip()
        chk(t == '', f'画像のみのはずが文字情報あり {m["path"]}')
print(f'3. 文字情報の罠: {nt} 箇所を2種類の取り出し方法で確認')

# ---- 4. 全ファイルが開けるか、A と B の対応 ----
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
                    load_workbook(p, read_only=True).close()
                elif ext == 'eml':
                    msg = email.message_from_bytes(open(p, 'rb').read())
                    assert 'アオバ機工販売' in msg.get_payload(decode=True).decode(msg.get_content_charset())
            except Exception as e:
                errs.append(f'開けない {p}: {e}')
sa = {os.path.splitext(m['path'])[0] for m in BK['MAN'] if m['set'] == 'A'}
sb = {os.path.splitext(m['path'])[0] for m in BK['MAN'] if m['set'] == 'B'}
chk(sa == sb, f'A/B の対応ずれ {sa ^ sb}')
for m in BK['MAN']:
    chk(os.path.exists(f'{OUT}/{"A_難版" if m["set"] == "A" else "B_対照版"}/{m["path"]}'), f'一覧にあるがファイルなし {m["path"]}')
print('4. ファイル:', {f'{k[0]}:{k[1]}': v for k, v in sorted(cnt.items())})

# ---- 5. サンプルが売上明細に存在するか ----
for tag, o in DT['T'].items():
    rows = led[o['uno']]
    chk(len(rows) == len(o['lines']) and sum(r[10] for r in rows) == sum(q * pr for _, q, pr in o['lines']), f'ledger {tag}')
print(f'5. 売上明細: {len(DT["rows"])} 行、サンプル取引 {len(DT["T"])} 件の金額・行数を確認')
print('結果:', 'すべて一致' if not errs else f'{len(errs)} 件の不一致')
for e in errs[:40]:
    print('  NG', e)
sys.exit(1 if errs else 0)
