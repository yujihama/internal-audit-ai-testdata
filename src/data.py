# -*- coding: utf-8 -*-
"""取引データとサンプル（不備の仕込みを含む）の定義"""
from common import *


def P(code): return PIDX[code]


def build():
    rng = random.Random(20251115)
    C = gen_customers(rng)
    orders = []
    for d in [x for x in drange(D(2025, 3, 25), D(2026, 4, 8)) if is_bd(x)]:
        for _ in range(rng.randint(90, 106)):
            c = min(199, int(200 * rng.random() ** 1.6))
            p = rng.randrange(len(PROD))
            std = PROD[p][3]
            q = rng.choice([50, 100, 100, 200, 300, 500]) if std < 1500 else (
                rng.choice([5, 10, 10, 20, 30, 40, 60]) if std < 12000 else rng.choice([1, 2, 2, 4, 6, 10]))
            pr = int(round(std * (1 - rng.choice([0] * 8 + [0.03, 0.05]))))
            s = add_bd(d, rng.choice([1, 1, 2, 2, 3, 3, 4, 5]))
            orders.append(dict(od=d, sid=s, sd=s, ld=s, c=c, lines=[(p, q, pr)], tag=None))

    def so(tag, c, od, sdate, lines, sid=None, ld=None):
        for x in (od, sdate, sid or sdate, ld or sdate):
            assert is_bd(x), (tag, x)
        orders.append(dict(od=od, sid=sid or sdate, sd=sdate, ld=ld or sdate, c=c,
                           lines=[(P(a), q, pr) for a, q, pr in lines], tag=tag))

    # C2 受注
    so('C2S1', 5, D(2025, 6, 12), D(2025, 6, 16), [('BR-6204ZZ', 200, 480), ('BU-1520', 500, 260)])
    so('C2S2', 30, D(2025, 7, 8), D(2025, 7, 10), [('SP-25B14', 110, 780)])
    so('C2S3', 59, D(2025, 9, 3), D(2025, 9, 5), [('PS-M12-5', 30, 4200), ('SV-3120-5', 6, 7800)])
    so('C2S4', 102, D(2025, 11, 18), D(2025, 11, 20), [('LB-20UU', 60, 1850)])
    so('C2S5', 177, D(2026, 1, 20), D(2026, 1, 23),
       [('GM-60W-30', 4, 38500), ('HU-FK12', 8, 11200), ('BS-1605-300', 4, 24800)])
    # C3 値引
    so('C3S1', 21, D(2025, 5, 22), D(2025, 5, 26), [('AC-20-50', 20, 8448)])
    so('C3S2', 64, D(2025, 7, 16), D(2025, 7, 18), [('AC-20-50', 12, 8832)])
    so('C3S3', 93, D(2025, 8, 28), D(2025, 9, 1), [('GM-60W-30', 10, 30800)])
    so('C3S4', 140, D(2025, 9, 16), D(2025, 9, 19), [('SV-3120-5', 40, 7020)])
    so('C3S5', 189, D(2025, 12, 10), D(2025, 12, 12), [('BS-1605-300', 6, 21080)])
    # C4 出荷・売上
    so('C4S1', 8, D(2025, 4, 18), D(2025, 4, 22), [('TB-XL150', 50, 1350)])
    so('C4S2', 73, D(2025, 6, 25), D(2025, 6, 27), [('LG-15-400', 6, 18600), ('HU-FK12', 6, 11200)])
    so('C4S3', 116, D(2025, 9, 5), D(2025, 9, 9), [('OR-P20-100', 30, 1200), ('BU-1520', 300, 260)])
    so('C4S4', 151, D(2025, 11, 10), D(2025, 11, 12), [('CP-25A', 15, 6400)])
    so('C4S5', 194, D(2026, 2, 13), D(2026, 2, 17), [('BR-6305DU', 120, 920), ('BR-6204ZZ', 300, 480)])
    # C5 返品の元売上
    so('C5O1', 17, D(2025, 5, 8), D(2025, 5, 12), [('PS-M12-5', 60, 4200)])
    so('C5O2', 52, D(2025, 6, 27), D(2025, 7, 1), [('GM-60W-30', 24, 38500)])
    so('C5O3', 99, D(2025, 9, 4), D(2025, 9, 8), [('CP-25A', 50, 6400)])
    so('C5O4', 146, D(2025, 10, 30), D(2025, 11, 4), [('BU-1520', 400, 260)])
    so('C5O5', 183, D(2026, 1, 8), D(2026, 1, 13), [('LG-15-400', 40, 18600)])
    so('C5OX', 123, D(2025, 9, 2), D(2025, 9, 4), [('LB-20UU', 50, 1850)])
    # C8 期末前後
    so('C8S1', 36, D(2026, 3, 26), D(2026, 3, 30), [('SV-3120-5', 25, 7800)])
    so('C8S2', 81, D(2026, 3, 27), D(2026, 3, 31), [('HU-FK12', 30, 11200)])
    so('C8S3', 110, D(2026, 3, 27), D(2026, 3, 31), [('BR-6305DU', 400, 920)])
    so('C8S4', 157, D(2026, 3, 27), D(2026, 4, 1), [('GM-60W-30', 16, 38500)], sid=D(2026, 3, 31), ld=D(2026, 3, 31))
    so('C8S5', 62, D(2026, 3, 30), D(2026, 4, 1), [('AC-20-50', 20, 9600)])
    so('C8S6', 199, D(2026, 3, 31), D(2026, 4, 2), [('LG-15-400', 10, 18600)])

    rng.shuffle(orders)
    orders.sort(key=lambda o: o['od'])
    cnt = {}
    for o in orders:
        k = o['od'].strftime('%y%m')
        cnt[k] = cnt.get(k, 0) + 1
        o['jno'] = f'JU{k}-{cnt[k]:04d}'
    ship = [o for o in orders if D(2025, 4, 1) <= o['sid'] <= D(2026, 4, 10)]
    ship.sort(key=lambda o: o['sid'])
    cnt = {}
    for o in ship:
        k = o['sid'].strftime('%y%m')
        cnt[k] = cnt.get(k, 0) + 1
        o['sno'] = f'SH{k}-{cnt[k]:04d}'
        o['uno'] = f'UR{k}-{cnt[k]:04d}'
    T = {o['tag']: o for o in ship if o['tag']}

    # 返品・売上取消
    rets = []
    pool = [o for o in ship if not o['tag'] and o['sd'] <= D(2026, 3, 10)]
    for o in rng.sample(pool, 90):
        p, q, pr = o['lines'][0]
        rq = q if rng.random() < 0.3 else max(1, q // rng.choice([2, 3, 4]))
        app = add_bd(o['sd'], rng.randint(5, 15))
        rets.append(dict(o=o, p=p, q=rq, pr=pr, app=app, cd=add_bd(app, rng.randint(2, 4)), tag=None))

    def R(tag, otag, q, app, ka, bu, kr, recv, cd, reason, resp):
        o = T[otag]
        p, _, pr = o['lines'][0]
        for x in (app, ka, kr, recv, cd) + ((bu,) if bu else ()):
            assert is_bd(x), (tag, x)
        rets.append(dict(o=o, p=p, q=q, pr=pr, app=app, ka=ka, bu=bu, kr=kr, recv=recv, cd=cd, tag=tag,
                         reason=reason, resp=resp))

    R('C5S1', 'C5O1', 30, D(2025, 5, 27), D(2025, 5, 28), None, D(2025, 5, 29), D(2025, 5, 30), D(2025, 5, 30),
      '型式誤り（当社の出荷ミス）。正規品は別途出荷済み。', '当社')
    R('C5S2', 'C5O2', 20, D(2025, 7, 22), D(2025, 7, 23), D(2025, 7, 24), D(2025, 7, 25), D(2025, 7, 28),
      D(2025, 7, 28), '顧客側の設計変更に伴う特別返品。未開封品に限り受入れる。', '顧客')
    R('C5S3', 'C5O3', 36, D(2025, 9, 24), D(2025, 9, 25), None, D(2025, 9, 26), D(2025, 9, 29), D(2025, 9, 29),
      '外径公差の不良（当社の検査漏れ）。代替品を手配済み。', '当社')
    R('C5SX', 'C5OX', 20, D(2025, 9, 22), D(2025, 9, 24), None, D(2025, 9, 25), D(2025, 9, 26), D(2025, 9, 26),
      '顧客の数量誤発注。未使用品のため受入れる。', '顧客')
    R('C5S4', 'C5O4', 200, D(2025, 11, 19), D(2025, 11, 20), None, D(2025, 11, 21), D(2025, 11, 25),
      D(2025, 11, 25), '数量の過剰出荷（当社のピッキングミス）。', '当社')
    R('C5S5', 'C5O5', 35, D(2026, 1, 27), D(2026, 1, 28), D(2026, 1, 29), D(2026, 1, 30), D(2026, 2, 2),
      D(2026, 2, 2), '外観不良（ロット不良）。仕入先へ求償予定。', '当社')
    rets.sort(key=lambda r: r['cd'])
    cnt = {}
    for r in rets:
        k = r['cd'].strftime('%y%m')
        cnt[k] = cnt.get(k, 0) + 1
        r['ano'] = f'AK{k}-{cnt[k]:04d}'
    for n, r in enumerate(sorted(rets, key=lambda r: r['app']), 1):
        r['hno'] = f'HP-2025-{n:03d}'
        r['by'] = ['立花', '宮下'][n % 2]
    RT = {r['tag']: r for r in rets if r['tag']}

    # 売上明細
    rows = []
    for o in ship:
        cu = C[o['c']]
        for li, (p, q, pr) in enumerate(o['lines'], 1):
            rows.append([o['uno'], li, '売上', o['ld'], cu['code'], cu['name'], PROD[p][0], PROD[p][1], q, pr, q * pr,
                         o['jno'], o['sno'], full(cu['rep']), ''])
    for r in rets:
        o = r['o']
        cu = C[o['c']]
        rows.append([r['ano'], 1, '取消', r['cd'], cu['code'], cu['name'], PROD[r['p']][0], PROD[r['p']][1], -r['q'],
                     r['pr'], -r['q'] * r['pr'], o['jno'], '', full(cu['rep']), o['uno']])
    rows.sort(key=lambda r: (r[3], r[0], r[1]))

    # C1 与信
    C1 = [dict(s=1, c=12, kind='新規', cur=0, req=3_000_000, score=54, rd=D(2025, 4, 22), app=D(2025, 5, 14),
               ka=D(2025, 5, 15), bu=None, yk=None, kr=D(2025, 5, 16), md=D(2025, 5, 19), monthly=800_000,
               reason='搬送装置向けの軸受・ブッシュ類について新規に引合いを受けたもの。初回は少額から開始し、取引実績を見て見直す。'),
          dict(s=2, c=47, kind='増額', cur=5_000_000, req=12_000_000, score=61, rd=D(2025, 6, 10), app=D(2025, 6, 23),
               ka=D(2025, 6, 24), bu=D(2025, 6, 25), yk=None, kr=D(2025, 6, 26), md=D(2025, 6, 27), monthly=3_500_000,
               reason='新工場ライン増設に伴い、ギヤードモータおよびリニアガイドの受注が増加する見込みのため。直近12か月の支払遅延なし。'),
          dict(s=3, c=88, kind='新規', cur=0, req=8_000_000, score=49, rd=D(2025, 7, 18), app=D(2025, 8, 4),
               ka=D(2025, 8, 5), bu=None, yk=None, kr=D(2025, 8, 6), md=D(2025, 8, 7), monthly=2_400_000,
               reason='既存取引先からの紹介。設備更新案件で電磁弁・エアシリンダの一括受注が見込まれる。早期の口座開設を要する。'),
          dict(s=4, c=131, kind='増額', cur=20_000_000, req=35_000_000, score=68, rd=D(2025, 9, 19),
               app=D(2025, 10, 6), ka=D(2025, 10, 7), bu=D(2025, 10, 8), yk=D(2025, 10, 10), kr=D(2025, 10, 14),
               md=D(2025, 10, 15), monthly=11_000_000,
               reason='下期の大型案件（自動倉庫向け部品一式）の受注内示あり。現行限度額では出荷停止となるおそれがあるため増額する。'),
          dict(s=5, c=164, kind='新規', cur=0, req=10_000_000, score=57, rd=D(2025, 7, 30), app=D(2025, 8, 18),
               ka=D(2025, 8, 19), bu=D(2025, 8, 20), bu_by='西川', yk=None, kr=D(2025, 8, 21), md=D(2025, 8, 22),
               monthly=3_000_000,
               reason='食品機械メーカーとの新規取引。ボールねじ・サポートユニットを中心に継続受注が見込まれる。')]
    for n, x in enumerate(C1):
        x['no'] = f'YS-2025-{[31, 52, 78, 104, 85][n]:03d}'
        x['rno'] = f'TR-{x["rd"].strftime("%y%m")}-{[4417, 5120, 6033, 7718, 6291][n]}'
        for k in ('app', 'ka', 'bu', 'yk', 'kr', 'md'):
            assert x[k] is None or is_bd(x[k]), (x['s'], k)
        C[x['c']]['limit'] = x['req']
        if x['kind'] == '新規':
            C[x['c']]['start'] = x['md']
    DELEG = dict(frm='榊原', to='西川', a=D(2025, 8, 18), b=D(2025, 8, 22), filed=D(2025, 8, 8), ok=D(2025, 8, 8),
                 reason='夏季休暇取得のため')

    # C2 注文書の内容（受注伝票との差は S2 のみ）
    C2 = [dict(s=1, tag='C2S1', style='A', pono='P-250611-07', pod=D(2025, 6, 11), po_lines=None, due=D(2025, 6, 17)),
          dict(s=2, tag='C2S2', style='B', pono='発25-0733', pod=D(2025, 7, 8), po_lines=[('SP-25B14', 100, 780)],
               due=D(2025, 7, 11)),
          dict(s=3, tag='C2S3', style='C', pono='K-1192', pod=D(2025, 9, 2), po_lines=None, due=D(2025, 9, 8)),
          dict(s=4, tag='C2S4', style='A', pono='PO-2511-0456', pod=D(2025, 11, 17),
               po_lines=[('LB-20UU', 40, 1850)], due=D(2025, 11, 21), rev=D(2025, 11, 18)),
          dict(s=5, tag='C2S5', style='B', pono='発26-0058', pod=D(2026, 1, 20), po_lines=None, due=D(2026, 1, 26))]
    for x in C2:
        o = T[x['tag']]
        x['o'] = o
        if x['po_lines'] is None:
            x['po_lines'] = [(PROD[p][0], q, pr) for p, q, pr in o['lines']]
        x['appd'] = o['od']

    # C3 値引
    C3 = [dict(s=1, tag='C3S1', app=D(2025, 5, 20), ka=None, bu=None, reason='競合他社（同等品）の提示価格に対抗するため。年間契約を条件とする。'),
          dict(s=2, tag='C3S2', app=D(2025, 7, 14), ka=D(2025, 7, 15), bu=None, reason='継続取引先からの値下げ要請。数量まとめ発注への切替を条件に応じる。'),
          dict(s=3, tag='C3S3', app=D(2025, 8, 25), ka=D(2025, 8, 26), bu=D(2025, 8, 27), reason='旧型番の在庫処分。次期モデル切替に伴う特別価格。'),
          dict(s=4, tag='C3S4', app=D(2025, 9, 16), ka=D(2025, 9, 18), bu=None, reason='他社からの切替案件。初回導入価格として提示する。'),
          dict(s=5, tag='C3S5', app=D(2025, 12, 8), ka=D(2025, 12, 9), bu=None, reason='年末のまとめ発注に対する数量値引き。')]
    for n, x in enumerate(C3):
        o = T[x['tag']]
        x['o'] = o
        p, q, pr = o['lines'][0]
        x['std'] = PROD[p][3]
        x['rate'] = round((1 - pr / PROD[p][3]) * 100, 1)
        x['no'] = f'NB-2025-{[41, 77, 96, 112, 158][n]:03d}'
    C4 = [dict(s=1, tag='C4S1', recv=D(2025, 4, 23), how='stamp'), dict(s=2, tag='C4S2', recv=D(2025, 6, 30), how='sign'),
          dict(s=3, tag='C4S3', recv=D(2025, 9, 10), how='stamp'), dict(s=4, tag='C4S4', recv=D(2025, 11, 13), how='stamp'),
          dict(s=5, tag='C4S5', recv=D(2026, 2, 18), how='stamp')]
    for x in C4:
        x['o'] = T[x['tag']]
    C5 = [dict(s=n, r=RT[f'C5S{n}']) for n in range(1, 6)]
    C8 = [dict(s=n, o=T[f'C8S{n}']) for n in range(1, 7)]
    C8M = dict(made=D(2026, 4, 3), by='宮下', ok=D(2026, 4, 6))

    # C6 入金消込
    C6 = []
    for mi, (m1, okd, by) in enumerate([(D(2025, 6, 1), D(2025, 7, 3), '立花'), (D(2025, 10, 1), D(2025, 11, 6), '宮下'),
                                        (D(2026, 1, 1), D(2026, 2, 4), '立花')]):
        days = [d for d in drange(m1, (m1.replace(day=28) + dt.timedelta(days=5)).replace(day=1) - dt.timedelta(days=1))
                if is_bd(d)]
        payd = [d for d in days if d.day in (10, 20, 25)] * 3 + days[-2:] * 6 + days
        pm = (m1 - dt.timedelta(days=1)).strftime('%y%m')
        invs = rng.sample(range(1, 1800), 25)
        rs = []
        for i in range(24):
            amt = rng.randint(6, 290) * 11000
            rs.append(dict(d=rng.choice(payd), c=rng.randrange(200), inv=f'INV-{pm}-{invs[i]:04d}', bill=amt, pay=amt,
                           state='消込済', note=''))
        for i in rng.sample(range(24), 2):
            fee = rng.choice([660, 880])
            rs[i]['pay'] = rs[i]['bill'] - fee
            rs[i]['note'] = '振込手数料差引（支払手数料で処理）'
        if mi == 1:
            rs.append(dict(d=D(2025, 10, 30), c=44, inv='', bill=None, pay=385_000, state='未消込',
                           note='該当請求なし。先方へ照会中（10/31）'))
        else:
            amt = rng.randint(6, 290) * 11000
            rs.append(dict(d=rng.choice(payd), c=rng.randrange(200), inv=f'INV-{pm}-{invs[24]:04d}', bill=amt, pay=amt,
                           state='消込済', note=''))
        rs.sort(key=lambda r: r['d'])
        C6.append(dict(s=mi + 1, m=m1, rows=rs, made=add_bd(okd, -1), by=by, ok=okd))

    # C7 滞留債権
    def aging(cs, over):
        out = []
        for c in cs:
            a = [rng.randint(3, 60) * 55000, rng.choice([0, 0, rng.randint(2, 20) * 44000]),
                 rng.choice([0, rng.randint(2, 12) * 33000]), 0, 0]
            if c in over.get(60, []):
                a[3] = rng.randint(3, 15) * 27500
            if c in over.get(90, []):
                a[4] = rng.randint(4, 18) * 38500
                a[3] = rng.choice([0, rng.randint(2, 8) * 27500])
            out.append(dict(c=c, a=a, cm=''))
        return out

    m8 = aging([3, 26, 41, 58, 67, 90, 119, 135, 172], {60: [41, 119], 90: [26, 135]})
    m8[1]['cm'] = '先方の資金繰り悪化による。9/10から3回の分割入金で合意（営業 佐野）'
    m8[7]['cm'] = '検収遅延によるもの。9月末の一括入金を先方経理に確認済み'
    m8[2]['cm'] = '請求書の再発行を依頼され対応済み。9/20入金予定'
    m11 = aging([9, 26, 55, 70, 84, 108, 127, 160, 191], {60: [55, 160], 90: [84, 127]})
    m2 = aging([14, 38, 70, 97, 127, 142, 168, 180], {60: [38], 90: [142]})
    m2[5]['cm'] = '品質クレーム未解決のため支払保留。3/12に技術部同行で訪問予定（河合）'
    m2[5]['hand'] = True
    m2[1]['cm'] = '2月分と合算で3/20振込予定との回答あり'
    m2[1]['hand'] = True
    C7 = [dict(s=1, m=D(2025, 8, 31), rows=m8, made=D(2025, 9, 2), by='立花', k=D(2025, 9, 3), b=D(2025, 9, 4)),
          dict(s=2, m=D(2025, 11, 30), rows=m11, made=D(2025, 12, 2), by='宮下', k=D(2025, 12, 3), b=D(2025, 12, 4)),
          dict(s=3, m=D(2026, 2, 28), rows=m2, made=D(2026, 3, 3), by='立花', k=D(2026, 3, 4), b=D(2026, 3, 5))]

    return dict(C=C, orders=ship, T=T, rets=rets, RT=RT, rows=rows, C1=C1, DELEG=DELEG, C2=C2, C3=C3, C4=C4, C5=C5,
                C6=C6, C7=C7, C8=C8, C8M=C8M)


if __name__ == '__main__':
    d = build()
    print('売上明細 行数', len(d['rows']), '取引先', len(d['C']), '取消', len(d['rets']))
    for t in sorted(d['T']):
        o = d['T'][t]
        print(t, o['jno'], o['sno'], o['od'], o['sid'], o['sd'], o['ld'], d['C'][o['c']]['name'], d['C'][o['c']]['sec'],
              sum(q * pr for _, q, pr in o['lines']))
    for r in d['rets']:
        if r['tag']:
            print(r['tag'], r['hno'], r['ano'], r['app'], r['cd'], r['q'] * r['pr'], r['by'])
    for x in d['C3']:
        print('C3', x['s'], x['no'], x['std'], x['o']['lines'][0][2], x['rate'])
    for x in d['C1']:
        cu = d['C'][x['c']]
        print('C1', x['s'], cu['name'], cu['sec'], cu['rep'], x['req'])
