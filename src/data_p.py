# -*- coding: utf-8 -*-
"""購買プロセス: 取引データと仕込み（すべて架空）"""
from common import *
from common import _CITY, _TOWN, _AREA, _SEI

FY0, FY1 = D(2025, 4, 1), D(2026, 3, 31)
EMPP = {'大西': ('大西 悠人', '購買課'), '福田': ('福田 真由', '購買課'), '今井': ('今井 涼', '購買課'),
        '野口': ('野口 拓也', '営業1課（2025/10/1付で購買課から異動）'), '柴田': ('柴田 恵', '購買課（2025/6/30退職）'),
        '藤本': ('藤本 浩二', '購買課長'), '神崎': ('神崎 礼子', '購買部長'), '早瀬': ('早瀬 徹', '管理担当役員'),
        '矢野': ('矢野 翔', '物流課'), '北村': ('北村 和也', '物流課'), '相馬': ('相馬 剛', '物流課長'),
        '立花': ('立花 奈央', '経理課'), '宮下': ('宮下 亮', '経理課'), '溝口': ('溝口 智子', '経理課長'), '桑原': ('桑原 修', '経理部長'),
        '三浦': ('三浦 航', '情報システム課'), '永井': ('永井 淳', '情報システム課長'), '片岡': ('片岡 千尋', '内部監査室'),
        '岡部': ('岡部 誠', '営業1課長'), '西川': ('西川 由美', '営業2課長')}
SECP = {'大西': '購買課', '福田': '購買課', '今井': '購買課', '野口': '購買課', '藤本': '購買課', '神崎': '購買部', '早瀬': '役員',
        '矢野': '物流課', '北村': '物流課', '相馬': '物流課', '立花': '経理課', '宮下': '経理課', '溝口': '経理課', '桑原': '経理部',
        '三浦': '情シス', '永井': '情シス', '片岡': '監査室', '岡部': '営業1課', '西川': '営業2課'}
BUYERS, KA, BU, YK = ['大西', '福田', '今井'], '藤本', '神崎', '早瀬'


def pf(n): return EMPP[n][0]


def approver(amt): return KA if amt < 1_000_000 else (BU if amt < 10_000_000 else YK)


_PRE = [('三葉', 'ミツバ'), ('北辰', 'ホクシン'), ('栄和', 'エイワ'), ('大栄', 'ダイエイ'), ('信濃', 'シナノ'), ('武蔵野', 'ムサシノ'),
        ('豊栄', 'ホウエイ'), ('東陽', 'トウヨウ'), ('協立', 'キョウリツ'), ('日進', 'ニッシン'), ('旭光', 'キョッコウ'), ('山吹', 'ヤマブキ')]
_SUF = [('ベアリング', 'ベアリング', ['BR-6204ZZ', 'BR-6305DU', 'LB-20UU', 'BU-1520']),
        ('精工', 'セイコウ', ['CP-25A', 'SP-25B14', 'BS-1605-300', 'LG-15-400', 'HU-FK12']),
        ('制御機器', 'セイギョキキ', ['SV-3120-5', 'AC-20-50', 'OR-P20-100']), ('電子', 'デンシ', ['PS-M12-5', 'GM-60W-30']),
        ('工機', 'コウキ', ['TB-XL150', 'GM-60W-30', 'LG-15-400'])]
_BANK = ['ひかり中央銀行', 'しらさぎ銀行', 'あかつき銀行', '北斗みらい信用金庫']
_BR = ['本店営業部', '駅前支店', '中央支店', '東支店', '工業団地支店', '港支店', '西支店']


def acct(rng):
    return dict(bank=rng.choice(_BANK), br=rng.choice(_BR), kind=rng.choice(['普通', '普通', '当座']), no=str(rng.randint(1000000, 9999999)))


def astr(a): return f'{a["bank"]} {a["br"]} {a["kind"]} {a["no"]}'


def gen_suppliers(rng):
    S = []
    for p, (pk, pkk) in enumerate(_PRE):
        for s, (sk, skk, prods) in enumerate(_SUF):
            i = p * 5 + s
            short = pk + sk
            front = (p + s) % 2 == 0
            pref, city = _CITY[rng.randrange(len(_CITY))]
            S.append(dict(i=i, code=f'S{i + 1:03d}', name=('株式会社' + short) if front else (short + '株式会社'), short=short,
                          kana=('カ）' + pkk + skk) if front else (pkk + skk + '（カ'), pkana=pkk + skk,
                          addr=f'{pref}{city}{_TOWN[rng.randrange(10)]}{rng.randint(1, 5)}-{rng.randint(1, 28)}-{rng.randint(1, 19)}',
                          zip=f'〒{rng.randint(100, 899)}-00{rng.randint(10, 99)}',
                          tel=f'{_AREA[pref]}-0{rng.randint(100, 199)}-{rng.randint(1000, 9999)}', buyer=BUYERS[i % 3], t20=(s == 0),
                          terms='20日締め 翌月10日払い' if s == 0 else '月末締め 翌月末日払い', acct=acct(rng),
                          prods=[PIDX[c] for c in prods], f=rng.uniform(0.97, 1.03), pic=_SEI[rng.randrange(20)]))
    return S


def cost(sup, p): return int(round(PROD[p][3] * 0.64 * sup['f'] / 10) * 10)


def amt(o): return sum(q * c for _, q, c in o['lines'])


def build():
    rng = random.Random(20261115)
    S = gen_suppliers(rng)
    bds = [d for d in drange(FY0, D(2026, 4, 30)) if is_bd(d)]
    bi = {d: n for n, d in enumerate(bds)}
    O = []
    for d in [x for x in bds if x <= FY1]:
        for _ in range(rng.randint(18, 24)):
            si = min(59, int(60 * rng.random() ** 1.5))
            sup = S[si]
            p = rng.choice(sup['prods'])
            c = cost(sup, p)
            q = rng.choice([200, 300, 500, 800]) if c < 1000 else (rng.choice([20, 30, 40, 60, 80]) if c < 8000 else rng.choice([4, 6, 8, 10, 15, 20]))
            r = rng.random()
            if r < 0.035:
                q *= rng.choice([3, 4, 5, 6])
            elif r < 0.038:
                q *= rng.choice([15, 20])
            O.append(dict(od=d, s=si, lines=[(p, q, c)], dept=rng.choice(['営業1課', '営業2課', '物流課']), tag=None, note='',
                          recs=[(add_bd(d, rng.randint(3, 9)), None)]))

    def po(tag, s, od, lines, recs, dept='営業1課', note=''):
        assert is_bd(od) and all(is_bd(r[0]) for r in recs), tag
        o = dict(od=od, s=s, lines=[(PIDX[a], q, c if c else cost(S[s], PIDX[a])) for a, q, c in lines], dept=dept, tag=tag, note=note, recs=recs)
        O.append(o)
        return o

    # 見積比較（C2）
    Q = [dict(s=1, item='LB-20UU', qty=800, sel=0, err={}, cmp=D(2025, 6, 5), od=D(2025, 6, 6), dept='物流課',
              v=[(6, 1080, '受注後10日', False, 'A', D(2025, 6, 3)), (36, 1140, '受注後7日', False, 'B', D(2025, 6, 4))]),
         dict(s=2, item='GM-60W-30', qty=90, sel=2, err={}, cmp=D(2025, 8, 21), od=D(2025, 8, 22), dept='営業2課', reason=D(2025, 8, 22),
              v=[(8, 25670, '受注後6週間', False, 'B', D(2025, 8, 19)), (18, 24220, '受注後8週間', False, 'A', D(2025, 8, 20)),
                 (16, 25170, '受注後2週間', False, 'C', D(2025, 8, 20))]),
         dict(s=3, item='BS-1605-300', qty=80, sel=0, err={1: 1_524_000}, cmp=D(2025, 10, 23), od=D(2025, 10, 24), dept='営業1課',
              v=[(27, 17250, '受注後3週間', False, 'A', D(2025, 10, 21)), (37, 15675, '受注後3週間', False, 'B', D(2025, 10, 22)),
                 (47, 17625, '受注後2週間', False, 'C', D(2025, 10, 22))]),
         dict(s=4, item='LG-15-400', qty=250, sel=2, err={}, cmp=D(2026, 1, 22), od=D(2026, 1, 23), dept='営業2課',
              v=[(9, 12320, '受注後4週間', False, 'A', D(2026, 1, 20)), (19, 12600, '受注後3週間', False, 'B', D(2026, 1, 21)),
                 (49, 12040, '受注後4週間', True, 'C', D(2026, 1, 21))])]
    for x in Q:
        vs = x['v'][x['sel']]
        x['o'] = po(f'C2S{x["s"]}', vs[0], x['od'], [(x['item'], x['qty'], vs[1])], [(add_bd(x['od'], 12), None)], x['dept'],
                    f'見積比較表 MH-{x["od"].strftime("%y%m")}-{x["s"]:02d}')
    # 分割発注（C3）
    G = dict(
        T1=[po('T1a', 7, D(2025, 6, 18), [('AC-20-50', 100, 0)], [(D(2025, 6, 26), None)], '営業1課', '受注引当 JU2506-0412'),
            po('T1b', 7, D(2025, 6, 18), [('AC-20-50', 90, 0)], [(D(2025, 6, 26), None)], '営業1課', '受注引当 JU2506-0398')],
        A=[po('Aa', 13, D(2025, 9, 10), [('GM-60W-30', 38, 0)], [(D(2025, 9, 19), None)], '営業2課'),
           po('Ab', 13, D(2025, 9, 10), [('GM-60W-30', 39, 0)], [(D(2025, 9, 19), None)], '営業2課'),
           po('Ac', 13, D(2025, 9, 10), [('GM-60W-30', 37, 0)], [(D(2025, 9, 22), None)], '営業2課')],
        B=[po('Ba', 21, D(2026, 1, 14), [('LG-15-400', 80, 0)], [(D(2026, 1, 23), None)], '物流課'),
           po('Bb', 21, D(2026, 1, 15), [('LG-15-400', 75, 0)], [(D(2026, 1, 26), None)], '物流課')])
    for k, g in G.items():
        assert all(amt(o) < 1_000_000 for o in g) and sum(amt(o) for o in g) >= 1_000_000, k
    # 3点照合（C4）とウォークスルー（C8）
    c24 = cost(S[24], PIDX['TB-XL150'])
    M = [dict(s=1, o=po('C4S1', 2, D(2025, 5, 19), [('SV-3120-5', 40, 0), ('OR-P20-100', 200, 0)], [(D(2025, 5, 27), None)]),
              inv=D(2025, 5, 31), chk=D(2025, 6, 10), diff='なし'),
         dict(s=2, o=po('C4S2', 11, D(2025, 8, 4), [('LG-15-400', 120, 0)], [(D(2025, 8, 12), [100]), (D(2025, 9, 2), [20])], '営業2課'),
              inv=D(2025, 8, 31), chk=D(2025, 9, 9), diff='分納。今回請求は検収済みの100個分（残20個は未検収・未請求）'),
         dict(s=3, o=po('C4S3', 24, D(2025, 10, 7), [('TB-XL150', 500, c24 + 40)], [(D(2025, 10, 21), None)], '物流課', '単価改定あり（注文変更書 2025/10/14）'),
              inv=D(2025, 10, 31), chk=D(2025, 11, 11), diff='単価改定あり（注文変更書 2025/10/14）。変更後単価と一致', chg=D(2025, 10, 14),
              old=c24),
         dict(s=4, o=po('C4S4', 33, D(2025, 12, 2), [('PS-M12-5', 60, 0), ('GM-60W-30', 8, 0)], [(D(2025, 12, 10), None)]),
              inv=D(2025, 12, 31), chk=D(2026, 1, 13), diff='なし')]
    WT = dict(o=po('WT', 41, D(2025, 11, 5), [('CP-25A', 100, 0)], [(D(2025, 11, 13), None)], '営業2課'), req=D(2025, 11, 4),
              inv=D(2025, 11, 30), chk=D(2025, 12, 9), app=D(2025, 12, 10), pay=D(2025, 12, 26), diff='なし')
    for x in M + [WT]:
        assert is_bd(x['chk'])

    # --- 分割発注に当たる自然発生の組を解消（仕込み以外に該当が出ないようにする） ---
    emb = {id(o) for g in G.values() for o in g}

    def groups(orders):
        by = {}
        for o in orders:
            if len(o['lines']) == 1 and amt(o) < 1_000_000:
                by.setdefault((o['s'], o['lines'][0][0], o['dept']), []).append(o)
        out = []
        for k, v in by.items():
            v.sort(key=lambda o: o['od'])
            i, n = 0, len(v)
            while i < n:
                j = i
                while j + 1 < n and bi[v[j + 1]['od']] - bi[v[i]['od']] <= 2:
                    j += 1
                if j > i and sum(amt(o) for o in v[i:j + 1]) >= 1_000_000:
                    out.append(v[i:j + 1])
                    i = j + 1
                else:
                    i += 1
        return out

    for g in G.values():   # 仕込みの近くにある同条件の発注は別の日へ移す
        k = (g[0]['s'], g[0]['lines'][0][0], g[0]['dept'])
        for o in O:
            if id(o) not in emb and (o['s'], o['lines'][0][0], o['dept']) == k and abs(bi[o['od']] - bi[g[0]['od']]) <= 5:
                o['od'] = add_bd(o['od'], 8 if o['od'] >= g[0]['od'] else -8)
                o['od'] = max(FY0, min(FY1, o['od']))
                while not is_bd(o['od']):
                    o['od'] += dt.timedelta(days=1)
                o['recs'] = [(add_bd(o['od'], 5), None)]
    for _ in range(40):
        gs = [g for g in groups(O) if not all(id(o) in emb for o in g)]
        if not gs:
            break
        for g in gs:
            nat = [o for o in g if id(o) not in emb and not o['tag']]
            if not nat:
                raise AssertionError('tagged order in natural group')
            o = max(nat, key=amt)
            p, q, c = o['lines'][0]
            o['lines'] = [(p, max(1, q // 2), c)]
    # --- 月次実績の急増（C7）: 上位10社のうち2社に大口を追加 ---
    def monthly(orders):
        t = {}
        for o in orders:
            for rd, qs in o['recs']:
                if rd <= FY1:
                    a = sum((qs[i] if qs else q) * c for i, (_, q, c) in enumerate(o['lines']))
                    t[(o['s'], rd.year, rd.month)] = t.get((o['s'], rd.year, rd.month), 0) + a
        return t

    used = {2, 11, 24, 33, 41, 6, 16, 27, 49, 7, 13, 21, 4, 17, 29, 38, 52, 44, 8, 18, 36, 37, 47, 9, 19}
    t0 = monthly(O)
    fy = {}
    for (s, y, m), v in t0.items():
        fy[s] = fy.get(s, 0) + v
    cand = [s for s in sorted(fy, key=lambda s: -fy[s])[:10] if s not in used and not S[s]['t20']]
    SA, SB = cand[1], cand[3]
    for k, (s, dates) in enumerate([(SA, [D(2025, 11, 6), D(2025, 11, 12), D(2025, 11, 18)]), (SB, [D(2026, 2, 4), D(2026, 2, 12), D(2026, 2, 18)])]):
        p = max(S[s]['prods'], key=lambda p: PROD[p][3])
        c = cost(S[s], p)
        for j, rd in enumerate(dates):
            q = int([2_900_000, 3_400_000, 2_600_000][j] / c)
            O.append(dict(od=add_bd(rd, -8), s=s, lines=[(p, q, c)], dept='営業1課', tag=f'SP{k}{j}', note='大型案件向け一括手配', recs=[(rd, None)]))

    # --- 買掛金残高と残高確認（C6） ---
    def balances(orders):
        b = {}
        for o in orders:
            for rd, qs in o['recs']:
                lo = D(2026, 2, 21) if S[o['s']]['t20'] else D(2026, 3, 1)
                if lo <= rd <= FY1:
                    a = sum((qs[i] if qs else q) * c for i, (_, q, c) in enumerate(o['lines']))
                    b[o['s']] = b.get(o['s'], 0) + a
        return {s: int(v * 1.1) for s, v in b.items()}

    bal = balances(O)
    top8 = sorted(bal, key=lambda s: -bal[s])[:8]
    noans = [s for s in top8[2:7] if not S[s]['t20']][0]
    rest = [s for s in top8 if s != noans]
    CF = {}
    for n, s in enumerate(top8):
        CF[s] = dict(s=s, rank=n + 1, ours=bal[s], kind='noans' if s == noans else ('transit' if s == rest[1] else ('credit' if s == rest[4] else 'ok')))
    for s, c in CF.items():
        if c['kind'] == 'transit':
            p = S[s]['prods'][0]
            cc = cost(S[s], p)
            q = max(1, int(560_000 / cc))
            c['po'] = po('CUT', s, D(2026, 3, 25), [(PROD[p][0], q, cc)], [(D(2026, 4, 2), None)], '物流課')
            c['ship'] = D(2026, 3, 30)
            c['delta'] = int(q * cc * 1.1)
            c['ans'] = c['ours'] + c['delta']
        elif c['kind'] == 'credit':
            c['delta'] = 132_000
            c['ans'] = c['ours'] - 132_000
        elif c['kind'] == 'ok':
            c['ans'] = c['ours']
        else:
            c['ans'] = None
            c['paid'] = D(2026, 4, 30)
        c['back'] = None if c['kind'] == 'noans' else add_bd(D(2026, 4, 6), (c['rank'] * 3) % 7)

    while any(any(o.get('tag') == 'CUT' for o in g) for g in groups(O)):
        c = [c for c in CF.values() if c['kind'] == 'transit'][0]
        p, q, cc = c['po']['lines'][0]
        q = max(1, int(q * 0.8))
        c['po']['lines'] = [(p, q, cc)]
        c['delta'] = int(q * cc * 1.1)
        c['ans'] = c['ours'] + c['delta']
    GR = groups(O)
    assert len(GR) == 3 and all(all(id(o) in emb for o in g) for g in GR), len(GR)

    # --- 採番 ---
    rng.shuffle(O)
    O.sort(key=lambda o: o['od'])
    cnt = {}
    for o in O:
        k = o['od'].strftime('%y%m')
        cnt[k] = cnt.get(k, 0) + 1
        o['no'] = f'PO{k}-{cnt[k]:04d}'
        o['by'] = S[o['s']]['buyer']
        o['app'] = approver(amt(o))
    R = [(rd, o, qs) for o in O for rd, qs in o['recs']]
    R.sort(key=lambda r: r[0])
    cnt = {}
    for n, (rd, o, qs) in enumerate(R):
        k = rd.strftime('%y%m')
        cnt[k] = cnt.get(k, 0) + 1
        o.setdefault('sino', []).append(f'SI{k}-{cnt[k]:04d}')
        o.setdefault('insp', []).append(['矢野', '北村'][n % 2])
    T = {o['tag']: o for o in O if o['tag']}
    porows, sirows = [], []
    for o in O:
        sup = S[o['s']]
        for li, (p, q, c) in enumerate(o['lines'], 1):
            porows.append([o['no'], li, o['od'], sup['code'], sup['name'], PROD[p][0], PROD[p][1], q, c, q * c, o['dept'], pf(o['by']),
                           pf(o['app']), o['od'], o['recs'][0][0], o['note']])
    for rd, o, qs in R:
        if rd > FY1:
            continue
        sup = S[o['s']]
        k = [r[0] for r in o['recs']].index(rd)
        for li, (p, q, c) in enumerate(o['lines'], 1):
            qq = qs[li - 1] if qs else q
            sirows.append([o['sino'][k], li, rd, sup['code'], sup['name'], PROD[p][0], PROD[p][1], qq, c, qq * c, o['no'], pf(o['insp'][k]), pf(o['by'])])
    sirows.sort(key=lambda r: (r[2], r[0], r[1]))
    bal = balances(O)
    assert sorted(bal, key=lambda s: -bal[s])[:8] == top8 and all(CF[s]['ours'] == bal[s] for s in top8)

    # --- 月次購買実績報告（C7） ---
    mt = monthly(O)
    fy = {}
    for (s, y, m), v in mt.items():
        fy[s] = fy.get(s, 0) + v
    top10 = sorted(fy, key=lambda s: -fy[s])[:10]
    assert SA in top10 and SB in top10
    REP = []
    cm_up = ['顧客の設備更新案件に伴う仕入の増加', '主要顧客からの受注増に伴う仕入の増加', '在庫補充のための発注が当月の検収に集中', '新規案件の立ち上がりに伴う仕入の増加']
    cm_dn = ['前月に検収が集中した反動による減少', '主要顧客の生産調整に伴う仕入の減少', '在庫水準の見直しによる発注の抑制', '前月の大型案件の仕入が一巡したことによる減少']
    for (y, m) in [(2025, 7), (2025, 11), (2026, 2)]:
        py, pm = (y, m - 1) if m > 1 else (y - 1, 12)
        rows = []
        for s in top10:
            cur, prev = mt.get((s, y, m), 0), mt.get((s, py, pm), 0)
            rate = (cur - prev) / prev * 100
            need = abs(rate) >= 30 and abs(cur - prev) >= 3_000_000
            r = dict(s=s, cur=cur, prev=prev, rate=rate, shown=rate, need=need, cm='')
            if need:
                r['cm'] = '大型案件（自動倉庫向け）の一括仕入によるもの' if (s == SA and m == 11) else (cm_up if cur > prev else cm_dn)[(s + m) % 4]
            if s == SB and m == 2:
                assert need, ('SB', rate, cur - prev)
                r['shown'] = rate - 30.0 if rate - 30.0 < 30 else rate / 10
                r['cm'] = ''
                r['bad'] = True
            rows.append(r)
        oc = sum(v for (s, yy, mm), v in mt.items() if (yy, mm) == (y, m) and s not in top10)
        op = sum(v for (s, yy, mm), v in mt.items() if (yy, mm) == (py, pm) and s not in top10)
        REP.append(dict(y=y, m=m, rows=rows, oc=oc, op=op, made=add_bd(D(y + (m == 12), m % 12 + 1, 1), 3), ok=add_bd(D(y + (m == 12), m % 12 + 1, 1), 5)))
    assert any(r['need'] and r['s'] == SA for r in REP[1]['rows'])

    # --- 仕入先マスタ変更ログ（C1） ---
    CH = []
    for n, (s, d1) in enumerate([(4, D(2025, 5, 13)), (17, D(2025, 7, 8)), (29, D(2025, 9, 17)), (38, D(2025, 11, 11)), (52, D(2026, 2, 17))]):
        old = dict(S[s]['acct'])
        new = acct(rng)
        S[s]['acct'] = new
        CH.append(dict(s=s, app=d1, ka=add_bd(d1, 1), reg=add_bd(d1, 2), old=old, new=new, by=['立花', '宮下'][n % 2], ok=True,
                       letter=add_bd(d1, -4), why=['取引銀行の見直しのため', '支店統廃合に伴う変更', '経理部門の移転に伴う変更', '取引銀行の見直しのため', '社名変更に伴う口座名義の変更'][n]))
    old = dict(S[44]['acct'])
    S[44]['acct'] = acct(rng)
    CH.append(dict(s=44, reg=D(2025, 11, 20), old=old, new=S[44]['acct'], by='宮下', ok=False))
    LOG = [dict(d=c['reg'], s=c['s'], kind='振込口座変更', a=astr(c['old']), b=astr(c['new']), by=c['by'], ch=c) for c in CH]
    for _ in range(92):
        d = bds[rng.randrange(0, bi[FY1])]
        s = rng.randrange(60)
        k = rng.choice(['担当者変更', '担当者変更', '住所変更', '電話番号変更', 'メールアドレス変更'])
        if k == '担当者変更':
            a, b = S[s]['pic'], _SEI[rng.randrange(20)]
        elif k == '住所変更':
            a, b = S[s]['addr'], f'{S[s]["addr"][:6]}{_TOWN[rng.randrange(10)]}{rng.randint(1, 5)}-{rng.randint(1, 28)}-{rng.randint(1, 19)}'
        elif k == '電話番号変更':
            a, b = S[s]['tel'], S[s]['tel'][:-4] + str(rng.randint(1000, 9999))
        else:
            a, b = f'order@{S[s]["code"].lower()}.example.jp', f'sales@{S[s]["code"].lower()}.example.jp'
        LOG.append(dict(d=d, s=s, kind=k, a=a, b=b, by=rng.choice(['立花', '宮下']), ch=None))
    LOG.sort(key=lambda l: (l['d'], l['kind']))
    k = 0
    for n, l in enumerate(LOG, 1):
        l['no'] = n
        if l['ch'] is not None and not l['ch']['ok']:
            l['app'] = ''
        else:
            k += 1
            l['app'] = f'KM-2025-{k:03d}'
        if l['ch'] is not None:
            l['ch']['logno'], l['ch']['appno'] = n, l['app']
    CK = []
    for (y, m) in [(2025, 5), (2025, 7), (2025, 9), (2025, 11), (2026, 2)]:
        ls = [l for l in LOG if (l['d'].year, l['d'].month) == (y, m)]
        ac = [l for l in ls if l['kind'] == '振込口座変更' and l['ch']['ok']]
        CK.append(dict(y=y, m=m, n=len(ls), ac=ac, real=len([l for l in ls if l['kind'] == '振込口座変更']),
                       ok=add_bd(D(y + (m == 12), m % 12 + 1, 1) - dt.timedelta(days=1), 3)))

    # --- 支払（C5）: 20日締め先、10日払い ---
    PAY = []
    for bn, (pd, lo, hi, off) in enumerate([(D(2025, 9, 10), D(2025, 7, 21), D(2025, 8, 20), (15, 33_000)),
                                            (D(2026, 2, 10), D(2025, 12, 21), D(2026, 1, 20), (30, 55_000))]):
        rows = []
        for s in range(0, 60, 5):
            v = sum(r[9] for r in sirows if r[3] == S[s]['code'] and lo <= r[2] <= hi)
            if v:
                bill = int(v * 1.1)
                o = off[1] if s == off[0] else 0
                rows.append(dict(s=s, bill=bill, off=o, pay=bill - o))
        PAY.append(dict(n=bn + 1, pd=pd, lo=lo, hi=hi, rows=rows, made=add_bd(pd, -4), ok=add_bd(pd, -3), sent=add_bd(pd, -2), by='立花', sender='宮下'))

    # --- 発注一覧の月次レビュー記録（C3） ---
    RV = []
    for n in range(12):
        y, m = (2025, 4 + n) if n < 9 else (2026, n - 8)
        ms = [o for o in O if (o['od'].year, o['od'].month) == (y, m)]
        RV.append(dict(y=y, m=m, n=len(ms), total=sum(amt(o) for o in ms), ok=add_bd(D(y + (m == 12), m % 12 + 1, 1) - dt.timedelta(days=1), 4), hit=None))
    RV[2]['hit'] = dict(g=G['T1'], txt='それぞれ別の受注に対応する発注で、購買依頼書も別。分割には当たらないと判断した。', bu=None)
    RV[9]['hit'] = dict(g=G['B'], txt='在庫切れへの対応で2回に分けて発注したもの。合計が100万円以上となるため購買部長へ報告し、事後承認を得た。', bu=D(2026, 2, 6))
    EV = [dict(s=s, q=rng.randint(3, 5), d=rng.randint(3, 5), p=rng.randint(2, 5)) for s in sorted(fy, key=lambda s: -fy[s])[:20]]
    return dict(S=S, O=O, T=T, porows=porows, sirows=sirows, Q=Q, G=G, GR=GR, M=M, WT=WT, bal=bal, top8=top8, CF=CF, REP=REP, top10=top10,
                SA=SA, SB=SB, CH=CH, LOG=LOG, CK=CK, PAY=PAY, RV=RV, EV=EV, groups=groups, bi=bi)


if __name__ == '__main__':
    d = build()
    S = d['S']
    print('発注', len(d['O']), '発注行', len(d['porows']), '仕入明細行', len(d['sirows']), 'ログ', len(d['LOG']))
    for k, g in d['G'].items():
        print(k, [(o['no'], o['od'], amt(o), o['app']) for o in g], sum(amt(o) for o in g))
    for t in ('C2S1', 'C2S2', 'C2S3', 'C2S4', 'C4S1', 'C4S2', 'C4S3', 'C4S4', 'WT', 'CUT'):
        o = d['T'][t]
        print(t, o['no'], o['od'], S[o['s']]['name'], amt(o), o['app'], o['sino'], o['recs'])
    for s in d['top8']:
        c = d['CF'][s]
        print('CF', c['rank'], S[s]['name'], S[s]['t20'], c['ours'], c['kind'], c.get('ans'), c.get('delta'))
    for rp in d['REP']:
        print(rp['y'], rp['m'], [(S[r['s']]['short'], round(r['rate'], 1), r['cur'] - r['prev'], r['need'], round(r['shown'], 1), bool(r['cm'])) for r in rp['rows'] if r['need'] or abs(r['rate']) >= 30])
    print('SA', S[d['SA']]['name'], 'SB', S[d['SB']]['name'])
    for c in d['CH']:
        print('CH', c['logno'], c['appno'], S[c['s']]['name'], c['reg'], c['ok'])
    for c in d['CK']:
        print('CK', c['y'], c['m'], c['n'], len(c['ac']), c['real'], c['ok'])
    for p in d['PAY']:
        print('PAY', p['pd'], len(p['rows']), sum(r['pay'] for r in p['rows']), [(S[r['s']]['short'], r['off']) for r in p['rows'] if r['off']])
    for r in d['RV']:
        print('RV', r['y'], r['m'], r['n'], r['total'], r['ok'], bool(r['hit']))
