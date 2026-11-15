# -*- coding: utf-8 -*-
"""検証（購買）: 証跡に印字した値とExcelデータから正解を独立に再計算し、正解表と突き合わせる。ファイルの健全性も確認する"""
import os, re, pickle, subprocess, sys, logging, datetime as dt
import pymupdf as fitz
from PIL import Image
from openpyxl import load_workbook
from common import *
from data_p import amt
import screens_p as sp

logging.disable(logging.CRITICAL)
NAME = '購買プロセス_検証データ_小'
OUT, TMP = f'{ROOT}/out/{NAME}', f'{ROOT}/out/tmp_p'
ST = pickle.load(open(f'{TMP}/state.pkl', 'rb'))
BK = pickle.load(open(f'{TMP}/book.pkl', 'rb'))
DT, KV = ST['DT'], ST['KV']
S = DT['S']
N, A, U = '不備なし', '不備あり', '判断できない'
errs = []


def chk(cond, msg):
    if not cond:
        errs.append(msg)


num = lambda s: int(re.sub(r'[^\d\-]', '', s))
who = lambda s: s.split()[1]
day = lambda v: v.date() if isinstance(v, dt.datetime) else v
stems = {os.path.splitext(os.path.basename(m['path']))[0] for m in BK['MAN'] if m['set'] == 'B'}


def xl(name):
    ws = load_workbook(f'{OUT}/B_対照版/共通資料/{name}', data_only=True).worksheets[0]
    return [list(r) for r in ws.iter_rows(min_row=2, values_only=True)]


calc, traps = {}, []
# ---- P01 口座変更（ログ全件 → 申請書・依頼書・チェックリスト） ----
log = [r for r in xl('仕入先マスタ変更ログ_2025年度.xlsx') if r[4] == '振込口座変更']
chk(len(log) == 6, f'口座変更の件数 {len(log)}')
for no, d, code, name, kind, a, b, by, app in log:
    d = day(d)
    ok = bool(app)
    if ok:
        k1, k2, k3 = KV.get(f'01_口座変更申請書_{app}'), KV.get(f'01_変更依頼書_{code}'), KV.get(f'01_月次照合チェックリスト_{d.year}-{d.month:02d}')
        ok = None not in (k1, k2, k3) and k1['k_new'] == b and '藤本' in k1['k_st_ka'] and code in k1['k_sup'] and all(k2[x] in b for x in ('k_newbank', 'k_newbr', 'k_newno')) \
            and k3['k_app1'] == app and k3['k_log1'] == str(no)
    else:
        chk(not any(code in s for s in stems if s.startswith('01_変更依頼書')), f'申請のない変更に依頼書がある {code}')
    calc[('P01', f'ログNo.{no}')] = N if ok else A
mst = {r[0]: r for r in xl('仕入先台帳.xlsx')}
for no, d, code, name, kind, a, b, by, app in log:   # 台帳は変更後の口座になっているか
    chk(all(str(mst[code][i]) in b for i in (8, 9, 11)), f'台帳の口座がログの変更後と不一致 {code}')

# ---- P02 見積比較（再計算）・P03 発注承認 ----
for x in DT['Q']:
    s, nq = x['s'], len(x['v'])
    kq = [KV[f'02_S{s}_見積書_{i + 1}'] for i in range(nq)]
    true = [num(k['k_sub']) for k in kq]
    for i, k in enumerate(kq):
        chk(num(k['k_qty1']) * num(k['k_price1']) == true[i], f'見積書の再計算 S{s}-{i + 1}')
        if num(k['k_total']) != true[i]:
            chk(num(k['k_total']) == int(true[i] * 1.1), f'税込表示の見積 S{s}-{i + 1}')
            traps.append(f'P02 S{s}: 見積書{i + 1}は税込表示')
    kc = KV[f'02_S{s}_見積比較表']
    shown = [num(kc[f'k_a{i + 1}']) for i in range(nq)]
    chk(all(kc[f'k_v{i + 1}'] == kq[i]['k_vendor'] for i in range(nq)), f'比較表の業者名 S{s}')
    low = kq[true.index(min(true))]['k_vendor']
    sel = kc['k_sel'].split('　')[0]
    ok = shown == true
    if ok and sel != low:
        kr = KV.get(f'02_S{s}_選定理由書')
        ok = kr is not None and '神崎' in kr['k_st_bu'] and sel in kr['k_sel'] and low in kr['k_low']
        traps.append(f'P02 S{s}: 最安値以外を選定（選定理由書あり）')
    calc[('P02', f'S{s}')] = N if ok else A
    kp = KV[f'02_S{s}_注文書']
    a = num(kp['k_total'])
    chk(a == amt(x['o']) and sel in kp['k_sup'], f'注文書の金額・仕入先 S{s}')
    need = ['k_st_ka'] + (['k_st_bu'] if a >= 1_000_000 else []) + (['k_st_yk'] if a >= 10_000_000 else [])
    calc[('P03', f'S{s}')] = N if all('日付印' in kp[n] for n in need) else A

# ---- P04 分割発注（発注データ全件から抽出し直す） ----
po = xl('発注データ_2025年度.xlsx')
chk(len(po) == len(DT['porows']), '発注データの行数')
tot = {}
for r in po:
    tot[r[0]] = tot.get(r[0], 0) + r[9]
by = {}
for r in po:
    if tot[r[0]] < 1_000_000:
        by.setdefault((r[3], r[5], r[10]), []).append((day(r[2]), r[0], r[9]))
bdays = [d for d in drange(D(2025, 4, 1), D(2026, 3, 31)) if is_bd(d)]
bix = {d: i for i, d in enumerate(bdays)}
found = []
for key, v in by.items():
    v.sort()
    for i in range(len(v)):
        w = [o for o in v[i:] if bix[o[0]] - bix[v[i][0]] <= 2]
        if len({o[1] for o in w}) >= 2 and sum(o[2] for o in w) >= 1_000_000:
            g = frozenset(o[1] for o in w)
            if not any(g <= f[1] for f in found):
                found.append((w[0][0], g, sum(o[2] for o in w)))
chk(len(found) == 3, f'分割発注に当たる組の数 {len(found)}')
hitm = set()
for d0, g, total in found:
    q = ((d0.month - 4) % 12) // 3 + 1
    hit = KV[f'03_発注レビュー記録_2025年度第{q}四半期'][f'k{d0.month}_hit']
    ok = hit != 'なし' and all(n in hit for n in g) and num(hit.split('合計')[1]) == total
    calc[('P04', f'{d0.year}年{d0.month}月の組')] = N if ok else A
    hitm.add(d0.month)
    if ok and '神崎' not in KV[f'03_発注レビュー記録_2025年度第{q}四半期'][f'k{d0.month}_st_bu']:
        traps.append(f'P04 {d0.month}月: 抽出されたが分割ではないと確認')
for q in range(1, 5):
    for k, v in KV[f'03_発注レビュー記録_2025年度第{q}四半期'].items():
        if k.endswith('_hit') and int(k[1:].split('_')[0]) not in hitm:
            chk(v == 'なし', f'該当のない月に抽出の記載 {k}')

# ---- P05 3点照合の再実施 ----
for x in DT['M']:
    s = x['s']
    kp, kg, ki, kr, kh = (KV.get(f'04_S{s}_{n}') for n in ('注文書', '検収報告書', '請求書', '請求書照合票', '注文変更書'))
    price = num(kh['k_new']) if kh else num(kp['k_price1'])
    ok = num(ki['k_qty1']) <= num(kg['k_qty1']) and num(ki['k_price1']) == price and '溝口' in kr['k_st_app'] and who(kr['k_st_chk']) != who(kr['k_st_app'])
    ok = ok and kg['k_po'] == kp['k_no'] == ki['k_po1'] == kr['k_po'] and kr['k_si'] == kg['k_no'] and kr['k_inv'] in ki['k_no'] and num(kr['k_total']) == num(ki['k_total'])
    if 'k_qty2' in ki:
        ok = ok and num(ki['k_qty2']) <= num(kg['k_qty2']) and num(ki['k_price2']) == x['o']['lines'][1][2]
    if kh:
        chk(num(kp['k_price1']) == num(kh['k_old']) != num(ki['k_price1']) and '藤本' in kh['k_st_ka'], f'単価改定のひっかけ S{s}')
        traps.append(f'P05 S{s}: 請求単価は注文書と異なるが注文変更書と一致')
    if num(kg['k_qty1']) < num(kg['k_ord1']):
        chk(num(ki['k_qty1']) == num(kg['k_qty1']), f'分納のひっかけ S{s}')
        traps.append(f'P05 S{s}: 分納（検収済みの分だけ請求）')
    calc[('P05', f'S{s}')] = N if ok else A

# ---- P06 支払（再計算・照合） ----
si = xl('仕入明細_2025年度.xlsx')
chk(len(si) == len(DT['sirows']), '仕入明細の行数')
for b in DT['PAY']:
    tag = b['pd'].strftime('%Y-%m-%d')
    kp, kf = KV[f'05_支払予定表_{tag}'], KV[f'05_振込受付結果_{tag}']
    n = len(b['rows'])
    ok = True
    for i, r in enumerate(b['rows']):
        code = S[r['s']]['code']
        bill = int(sum(x[9] for x in si if x[3] == code and b['lo'] <= day(x[2]) <= b['hi']) * 1.1)
        ok = ok and bill == r['bill'] and r['pay'] == r['bill'] - r['off']
        if f'k_bill{i}' in kp:
            ok = ok and num(kp[f'k_bill{i}']) == r['bill'] and num(kp[f'k_pay{i}']) == r['pay'] and kp[f'k_acct{i}'] == str(mst[code][11])
        if f'k_amt{i}' in kf:
            ok = ok and num(kf[f'k_amt{i}']) == r['pay']
        if r['off']:
            traps.append(f'P06 {tag}: 相殺 {r["off"]:,}円')
    total = sum(r['pay'] for r in b['rows'])
    ok = ok and num(kp['k_total']) == total == num(kf['k_total']) and num(kf['k_cnt']) == n and kf['k_acct0'] == kp['k_acct0'] and kf['k_pd'] == sd(b['pd'])
    ok = ok and len({who(kp[k]) for k in ('k_st_made', 'k_st_ok', 'k_st_sent')}) == 3
    calc[('P06', f'{b["pd"].year}年{b["pd"].month}月{b["pd"].day}日支払')] = N if ok else A

# ---- P07 残高確認・P08 対象の網羅性 ----
bal = {r[0]: r[3] for r in xl('買掛金残高一覧_2026-03-31.xlsx')}
chk(len(bal) == 60, '残高一覧の件数')
kr = KV['06_差異調整表']
for i, s in enumerate(DT['top8']):
    c, code = DT['CF'][s], S[s]['code']
    ours = num(kr[f'k_ours{i}'])
    chk(ours == bal[code] == c['ours'], f'帳簿残高 {code}')
    if kr[f'k_ans{i}'] == '未回答':
        ka = KV.get(f'06_期後の振込明細_{code}')
        ok = ka is not None and num(ka['k_total']) == ours and f'06_残高確認回答書_{code}' not in stems and ka['k_pd'] > '2026/03/31'
        traps.append(f'P07 {code}: 未回答（代替手続あり）')
    else:
        kc = KV[f'06_残高確認回答書_{code}']
        diff = num(kr[f'k_ans{i}']) - ours
        ok = num(kc['k_ours']) == ours and diff == num(kr[f'k_diff{i}'])
        if diff == 0:
            ok = ok and 'ありません' in kc['k_chk']
        else:
            ok = ok and 'あります' in kc['k_chk'] and num(kc['k_ans']) == ours + diff
            if diff > 0:
                kg = KV.get(f'06_期後の検収報告書_{code}')
                ok = ok and kg is not None and kg['k_date'] > '2026/03/31' and kg['k_po'] == c['po']['no'] and int(amt(c['po']) * 1.1) == diff and kg['k_no'] in kr[f'k_cause{i}']
                chk(not any(r[10] == c['po']['no'] for r in si), '未達の仕入が当年度の仕入明細に入っている')
                traps.append(f'P07 {code}: 未達（期後の検収報告書あり）')
            else:
                kn = KV.get(f'06_値引通知書_{code}')
                ok = ok and kn is not None and num(kn['k_amt']) == -diff
                traps.append(f'P07 {code}: 値引（値引通知書あり）')
    ok = ok and '溝口' in kr['k_st_ok']
    calc[('P07', code)] = N if ok else A
top = sorted(bal.items(), key=lambda kv: -kv[1])
ks = KV['06_発送管理表']
ok = [c for c, _ in top[:8]] == [S[s]['code'] for s in DT['top8']] and top[7][1] > top[8][1] and all(ks[f'k_code{i}'] == top[i][0] and num(ks[f'k_bal{i}']) == top[i][1] for i in (0, 2, 7))
calc[('P08', '全件')] = N if ok else A

# ---- P09 月次購買実績（仕入明細から再集計） ----
mt, fy = {}, {}
for r in si:
    d = day(r[2])
    mt[(r[3], d.year, d.month)] = mt.get((r[3], d.year, d.month), 0) + r[9]
    fy[r[3]] = fy.get(r[3], 0) + r[9]
chk([c for c, _ in sorted(fy.items(), key=lambda kv: -kv[1])[:10]] == [S[s]['code'] for s in DT['top10']], '上位10社')
for rp in DT['REP']:
    y, m = rp['y'], rp['m']
    py, pm = (y, m - 1) if m > 1 else (y - 1, 12)
    k = KV[f'07_月次購買実績報告書_{y}-{m:02d}']
    bad, near = False, 0
    for i, r in enumerate(rp['rows']):
        code = S[r['s']]['code']
        cur, prev = mt.get((code, y, m), 0), mt.get((code, py, pm), 0)
        chk(cur == r['cur'] and prev == r['prev'], f'月次集計 {y}-{m} {code}')
        rate = (cur - prev) / prev * 100
        need = abs(rate) >= 30 and abs(cur - prev) >= 3_000_000
        shown = r['shown']
        if f'k_rate{i}' in k:
            chk(num(k[f'k_cur{i}']) == cur and num(k[f'k_prev{i}']) == prev, f'報告書の金額 {y}-{m} {code}')
            shown = float(k[f'k_rate{i}'].replace('%', '').replace('+', ''))
        if abs(shown - rate) > 0.06:
            bad = True
        if need:
            chk(f'k_cm{i}' in k, f'基準超の行の記録なし {y}-{m} {code}')
            if k[f'k_cm{i}'] == '（空欄）':
                bad = True
            else:
                chk(('増加' in k[f'k_cm{i}'] or '一括仕入' in k[f'k_cm{i}'] or '集中' in k[f'k_cm{i}']) == (cur > prev) or '反動' in k[f'k_cm{i}'], f'原因の向きが増減と合わない {y}-{m} {code}')
        elif abs(rate) >= 30:
            near += 1
    if not bad and near and not any(r['need'] for r in rp['rows']):
        traps.append(f'P09 {y}-{m}: 増減率は基準以上だが増減額が基準未満の先が{near}社')
    total = sum(v for (c, yy, mm), v in mt.items() if (yy, mm) == (y, m))
    chk(num(k['k_total']) == total, f'報告書の合計 {y}-{m}')
    calc[('P09', f'{y}年{m}月度')] = N if (not bad and '神崎' in k['k_st_ok']) else A

# ---- P10 ウォークスルー ----
x = DT['WT']
o = x['o']
kq, kp, kg, ki, kr, kf = (KV[f'08_{n}'] for n in ('購買依頼書', '注文書', '検収報告書', '請求書', '請求書照合票', '振込明細'))
a = num(kp['k_total'])
ok = '日付印' in kq['k_st_head'] and '藤本' in kp['k_st_ka'] and a < 1_000_000 and who(kg['k_st_insp']) != o['by'] and num(ki['k_qty1']) <= num(kg['k_qty1']) \
    and num(ki['k_price1']) == num(kp['k_price1']) and '溝口' in kr['k_st_app'] and who(kr['k_st_chk']) != who(kr['k_st_app']) \
    and num(kf['k_total']) == num(ki['k_total']) == int(a * 1.1) and kf['k_pd'] == kr['k_due'] and kg['k_po'] == kp['k_no'] == ki['k_po1'] == kr['k_po'] == o['no']
ok = ok and x['req'] <= o['od'] <= o['recs'][0][0] <= x['inv'] <= x['chk'] <= x['app'] <= x['pay']
calc[('P10', '取引1件')] = N if ok else A

# ---- P11 質問と裏付け ----
ke = KV.get('09_仕入先評価結果一覧')
calc[('P11', '質問1')] = N if (ke and ke['k_last'] == '20' and '神崎' in ke['k_st_bu'] and len(DT['EV']) == 20) else A
calc[('P11', '質問2')] = U if not any('緊急発注' in s for s in stems) else N   # 裏付資料が提出されていない

# ---- P12 アクセス権 ----
kh = KV['10_人事異動一覧']
sb = [u for u in sp.USERS if u[1] == kh['k_sb']][0]
ng = [u for u in sp.USERS if u[1] == kh['k_ng']][0]
calc[('P12', '退職者（柴田）')] = N if sb[10] == '無効' else A
calc[('P12', '異動者（野口）')] = N if (ng[10] == '無効' or (ng[2] == kh['k_ng_to'] and all(v != '○' for v in ng[3:10]))) else A
chk(ng[11] > kh['k_ng_d'], '異動後のログインの記録')
conf = [u[0] for u in sp.USERS if u[10] == '有効' and any(u[i] == '○' and u[j] == '○' for i, j in ((3, 4), (3, 5), (7, 8)))]
kl = KV['10_特権ID管理台帳']
calc[('P12', '権限の併有')] = N if (conf == [kl['k_id']] and '日付印' in kl['k_st_ka'] and '日付印' in kl['k_st_yk']) else A
if conf:
    traps.append(f'P12: 権限を併せ持つのは特権ID {conf[0]} のみ（台帳で管理）')

# ---- P13 自動統制 ----
ks, kt = KV['10_照合条件設定画面'], KV['10_照合テスト結果画面']
ok = num(ks['k_qtol']) == 0 and ks['k_ptol'].startswith('0.0') and '保留' in ks['k_act'] and 'ありません' in ks['k_hist'] and num(kt['k_inv']) > num(kt['k_recv']) and '保留' in kt['k_state']
calc[('P13', '設定・テスト')] = N if ok else A

# ---- 正解表との突き合わせ ----
imp = {m['path'] for m in BK['MAN'] if m['set'] == 'A' and m['impact'] == 'あり'}
n = 0
for a in BK['ans']:
    for s, row in zip(a['S'], [r for r in BK['srow'] if r[0] == a['id']]):
        k = (a['id'], s[0])
        hard = U if (calc.get(k) == N and any(f in imp for f in row[8].split('\n'))) else calc.get(k)
        chk(calc.get(k) == s[2], f'対照版の正解が不一致 {k}: 再計算={calc.get(k)} 正解表={s[2]}')
        chk(hard == s[1], f'難版の正解が不一致 {k}: 期待={hard} 正解表={s[1]}')
        n += 1
chk(n == len(calc), f'件数 {n} vs {len(calc)}')
print(f'1. 正解の再計算: {n} 単位を照合。ひっかけの成立を確認: {len(traps)} 件')
for t in traps:
    print('     -', t)

# ---- 2. 対照版PDFの文字情報に主要項目の値が入っているか ----
norm = lambda s: re.sub(r'[\s　]', '', s)
tot_ = hit_ = 0
for m in BK['MAN']:
    stem = os.path.splitext(os.path.basename(m['path']))[0]
    if m['set'] != 'B' or not m['path'].endswith('.pdf') or stem not in KV:
        continue
    txt = norm(''.join(p.get_text() for p in fitz.open(f'{OUT}/B_対照版/{m["path"]}')))
    for k, v in KV[stem].items():
        if any(w in v for w in ('印', '斜線', '空欄', '署名', '手書き', 'ゴム', 'チェック')) or v in ('回答1', '回答2'):   # 後者は欄の名前（値ではない）
            continue
        tot_ += 1
        if norm(v) in txt:
            hit_ += 1
        else:
            errs.append(f'対照版の文字情報に値なし {stem} {k}={v}')
print(f'2. 対照版の文字情報: {hit_}/{tot_} 項目を確認（印影・手書き風の欄は対象外）')

# ---- 3. 難版の「文字情報の罠」が実際に取り出せるか ----
nt = 0
for m in BK['MAN']:
    if m['set'] == 'A' and m['trap'] != '-':
        p = f'{OUT}/A_難版/{m["path"]}'
        t1 = norm(''.join(pg.get_text() for pg in fitz.open(p)))
        t2 = norm(subprocess.run(['pdftotext', p, '-'], capture_output=True, text=True).stdout)
        for part in m['trap'].split('；'):
            new = norm(re.search(r'文字情報は「(.+?)」', part).group(1))
            old = norm(re.search(r'画像は「(.+?)」', part).group(1))
            chk(new in t1 and new in t2, f'罠の値が取り出せない {m["path"]} {new}')
            chk(new != old, f'罠の値が画像と同じ {m["path"]}')
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
                    load_workbook(p).close()
            except Exception as e:
                errs.append(f'開けない {p}: {e}')
sa = {os.path.splitext(m['path'])[0] for m in BK['MAN'] if m['set'] == 'A'}
sb_ = {os.path.splitext(m['path'])[0] for m in BK['MAN'] if m['set'] == 'B'}
chk(sa == sb_, f'A/B の対応ずれ {sa ^ sb_}')
for m in BK['MAN']:
    chk(os.path.exists(f'{OUT}/{"A_難版" if m["set"] == "A" else "B_対照版"}/{m["path"]}'), f'一覧にあるがファイルなし {m["path"]}')
disk = sum(v for v in cnt.values())
chk(disk == len(BK['MAN']), f'ファイル数 {disk} と一覧 {len(BK["MAN"])} が不一致')
print('4. ファイル:', {f'{k[0]}:{k[1]}': v for k, v in sorted(cnt.items())})

# ---- 5. サンプルがExcelデータに存在するか ----
pos, sis = {r[0] for r in po}, {r[0] for r in si}
for tag, o_ in DT['T'].items():
    chk(o_['no'] in pos and tot[o_['no']] == amt(o_), f'発注データにサンプルなし {tag}')
    for k, (rd, qs) in enumerate(o_['recs']):
        chk((o_['sino'][k] in sis) == (rd <= D(2026, 3, 31)), f'仕入明細とサンプルの対応 {tag}')
print(f'5. Excelデータ: 発注 {len(po)} 行・仕入明細 {len(si)} 行・変更ログ {len(xl("仕入先マスタ変更ログ_2025年度.xlsx"))} 行。サンプル取引 {len(DT["T"])} 件の存在と金額を確認')
print('結果:', 'すべて一致' if not errs else f'{len(errs)} 件の不一致')
for e in errs[:40]:
    print('  NG', e)
sys.exit(1 if errs else 0)
