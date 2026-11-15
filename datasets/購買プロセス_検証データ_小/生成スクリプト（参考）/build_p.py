# -*- coding: utf-8 -*-
"""購買プロセス: 証跡一式の生成（対照版と難版）"""
import os, shutil, pickle
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont
import build as B
from build import PL, emit, emit_screen
from common import *
import data_p as dp, docs_p as d1, docs_p2 as d2, screens_p as sp, degrade as dg

NAME = '購買プロセス_検証データ_小'
B.NAME, B.OUT = NAME, f'{ROOT}/out/{NAME}'
B.HARD, B.CLEAN, B.TMP = f'{B.OUT}/A_難版', f'{B.OUT}/B_対照版', f'{ROOT}/out/tmp_p'
B.FO = {'F1': '01_仕入先マスタ変更', 'F2': '02_見積比較・発注', 'F3': '03_発注一覧レビュー', 'F4': '04_検収・請求照合', 'F5': '05_支払', 'F6': '06_残高確認',
        'F7': '07_月次購買実績', 'F8': '08_ウォークスルー', 'F9': '09_ヒアリング', 'F10': '10_システム権限・設定', 'X': '共通資料'}
B.SCREEN_TITLE = '利用者ID・権限一覧の画面の写し（2026/04/14 情報システム課にて取得）'
IRR = False


def digit(s, k=1):
    """数字列の途中の1桁を別の数字に変える"""
    idx = [i for i, ch in enumerate(s) if ch.isdigit()]
    i = idx[min(k, len(idx) - 1)]
    return s[:i] + str((int(s[i]) + 3) % 10) + s[i + 1:]


def up(src, f):
    """画面の写しを拡大（高解像度の画面を想定）"""
    im, boxes, kv = src
    im = im.resize((int(im.width * f), int(im.height * f)), Image.LANCZOS)
    return im, {k: (b[0],) + tuple(v * f for v in b[1:]) for k, b in boxes.items()}, kv


def main():
    for p in (B.OUT, B.TMP):
        shutil.rmtree(p, ignore_errors=True)
    for p in [B.TMP, f'{B.OUT}/正解'] + [f'{r}/{f}' for r in (B.HARD, B.CLEAN) for f in B.FO.values()]:
        os.makedirs(p)
    DT = dp.build()
    S = DT['S']
    T = lambda n: f'{B.TMP}/src_{n}.pdf'
    d2.rules_p(T('rules'), 21)
    B.OTHER = B.raster(T('rules'), 0)
    fh = lambda d, who: f'{d.year}/{d.month:02d}/{d.day:02d} {9 + d.day % 8}:{10 + d.day}  FROM:{who}   TO:03-0155-2199   P.001/001'
    sfax = lambda d, s: fh(d, f'{hankaku(s["pkana"])} {s["tel"]}')

    # ---- F1 仕入先マスタ変更 ----
    pa = [PL('copy+skew2', dmg=[('blotch', 'x_call', IRR, '本人確認の記載', 0.6)]), PL('photo', fmt='jpg'), PL('faded+skew3', dmg=[('water', 'x_reason', IRR, '変更理由', 0.8)]),
          None, PL('fax+jitter', hdr=fh(D(2026, 2, 19), 'ｱｵﾊﾞｷｺｳ ｺｳﾊﾞｲ 03-0155-2196'))]
    pl = [None, PL('show+skew2', dmg=[('water', 'x_greet', IRR, 'あいさつ文', 0.8)]), PL('lowres', fmt='jpg', dmg=[('blotch', 'k_newno', True, '新口座の口座番号')]),
          PL('streak+skew3', dmg=[('blotch', 'x_contact', IRR, '問い合わせ先')]), PL('dither')]
    ok = [c for c in DT['CH'] if c['ok']]
    for n, c in enumerate(ok):
        sup = S[c['s']]
        if n == 0:
            pl[0] = PL('fax', hdr=sfax(c['letter'], sup))
        if n == 3:
            pa[3] = PL('dark+rot90', layer='wrong', wrong={'k_new': (c['new']['no'], digit(c['new']['no'], 3))})
        emit('F1', f'01_口座変更申請書_{c["appno"]}', d1.acct_app(T(f'f1a{n}'), DT, c, 100 + n), pa[n], '振込口座変更申請書', 'P01',
             ('k_no', 'k_sup', 'k_new', 'k_st_ka', 'k_st_reg', 'k_reg'))
        emit('F1', f'01_変更依頼書_{sup["code"]}', d1.sup_letter(T(f'f1l{n}'), DT, c, 110 + n), pl[n], '仕入先からの口座変更依頼書', 'P01',
             ('k_sup', 'k_newbank', 'k_newbr', 'k_newno'))
    pc = [PL('wavy+copy'), None, PL('streak+skew4'), PL('faded'), PL('jitter+fax', hdr=fh(D(2026, 3, 4), 'ｱｵﾊﾞｷｺｳ ｹｲﾘ 03-0155-2195'))]
    for n, ck in enumerate(DT['CK']):
        emit('F1', f'01_月次照合チェックリスト_{ck["y"]}-{ck["m"]:02d}', d1.m_check(T(f'f1c{n}'), DT, ck, 120 + n), pc[n], 'マスタ変更 月次照合チェックリスト', 'P01',
             ('k_n', 'k_cnt', 'k_log1', 'k_app1', 'k_result', 'k_st'))

    # ---- F2 見積比較・発注 ----
    kq = ('k_vendor', 'k_total', 'k_qty1', 'k_price1', 'k_amt1', 'k_sub', 'k_due')
    kc = ('k_v1', 'k_a1', 'k_r1', 'k_v2', 'k_a2', 'k_r2', 'k_v3', 'k_a3', 'k_r3', 'k_sel', 'k_why', 'k_st_ka')
    kp = ('k_no', 'k_date', 'k_sup', 'k_qty1', 'k_price1', 'k_total', 'k_st_ka', 'k_st_bu', 'k_st_yk')
    plans = {1: ([PL('fax'), PL('copy+skew1', layer='wrong', wrong={'k_price1': ('1,140', '1,040')})], PL('wavy+dark'), PL('faded', dmg=[('blotch', 'x_place', IRR, '納入場所')])),
             2: ([PL('lowres', fmt='jpg', dmg=[('sticky', 'x_note', IRR, '備考欄', 0.85)]), PL('fax+skew2'), PL('photo', fmt='jpg')], PL('copy'), None),
             3: ([PL('streak+skew2'), PL('fax'), PL('dark', dmg=[('sticky', 'x_note', IRR, '備考欄', 0.85)])], PL('photo', fmt='jpg'), PL('jitter')),
             4: ([PL('dither'), None, PL('copy', dmg=[('blotch', ['k_total'], IRR, '御見積金額（明細行から再計算できる）', 1.0), ('blotch', 'x_tot', IRR, '小計・消費税・合計（明細行から再計算できる）', 0.9)])],
                 PL('faded+skew2', layer='wrong'), PL('carbon'))}
    for x in DT['Q']:
        s = x['s']
        pq, pcmp, ppo = plans[s]
        qnos = []
        for vi, v in enumerate(x['v']):
            if pq[vi] is not None and pq[vi].ops.startswith('fax'):
                pq[vi].hdr = sfax(v[5], S[v[0]])
            g, qno = d1.quote(T(f'f2q{s}{vi}'), DT, x, vi, 200 + s * 10 + vi)
            qnos.append(qno)
            emit('F2', f'02_S{s}_見積書_{vi + 1}', g, pq[vi], '見積書', 'P02', kq)
        emit('F2', f'02_S{s}_見積比較表', d1.q_compare(T(f'f2c{s}'), DT, x, 250 + s, qnos), pcmp, '見積比較表', 'P02', kc)
        if x.get('reason'):
            emit('F2', f'02_S{s}_選定理由書', d1.reason_doc(T(f'f2r{s}'), DT, x, 260 + s), PL('show+skew3'), '選定理由書', 'P02', ('k_sel', 'k_low', 'k_gap', 'k_st_bu'))
        emit('F2', f'02_S{s}_注文書', d1.po_doc(T(f'f2p{s}'), DT, x['o'], 270 + s), ppo, '注文書（控）', 'P02,P03', kp)

    # ---- F3 発注一覧レビュー ----
    pr = [PL('fax', hdr=fh(D(2025, 7, 7), 'ｱｵﾊﾞｷｺｳ ｺｳﾊﾞｲ 03-0155-2196')), PL('wavy+skew2'), PL('dark', vec=[0]), PL('faded+skew3')]
    for qn in range(4):
        ms = DT['RV'][qn * 3:qn * 3 + 3]
        ks = [f'k{r["m"]}_{k}' for r in ms for k in ('n', 'total', 'hit', 'st_ka', 'st_bu')]
        emit('F3', f'03_発注レビュー記録_2025年度第{qn + 1}四半期', d1.review_book(T(f'f3r{qn}'), DT, ms, 300 + qn), pr[qn], '発注一覧 月次レビュー記録', 'P04', ks)

    # ---- F4 検収・請求照合 ----
    kg = ('k_no', 'k_date', 'k_po', 'k_code1', 'k_ord1', 'k_qty1', 'k_qty2', 'k_st_insp')
    ki = ('k_no', 'k_total', 'k_po1', 'k_qty1', 'k_price1', 'k_amt1', 'k_qty2', 'k_price2', 'k_sub')
    kr = ('k_inv', 'k_total', 'k_po', 'k_si', 'k_diff', 'k_st_chk', 'k_st_app')
    plans = {1: (PL('copy'), PL('streak+jitter'), PL('fax', layer='none', dmg=[('blotch', 'x_bank', IRR, '振込先の記載', 0.6)]), PL('wavy+skew2')),
             2: (None, PL('faded+skew4'), PL('lowres+skew3', fmt='jpg'), PL('copy+jitter')),
             3: (PL('dark+skew1'), PL('photo', fmt='jpg'), PL('show', dmg=[('blotch', 'x_term', IRR, '支払期限の記載')]), PL('faded')),
             4: (PL('jitter'), PL('carbon', dmg=[('water', ['k_qty1', 'k_qty2'], True, '今回検収数量の欄')]), PL('dither+skew2'), PL('photo', fmt='jpg'))}
    for x in DT['M']:
        s, o = x['s'], x['o']
        ppo, pg, pi, prq = plans[s]
        lines = [(p, (o['recs'][0][1][i] if o['recs'][0][1] else q), c) for i, (p, q, c) in enumerate(o['lines'])]
        o0 = dict(o, lines=[(p, q, x['old']) for p, q, _ in o['lines']]) if x.get('old') else o   # 注文書（控）は発行時点（単価改定の前）の内容
        emit('F4', f'04_S{s}_注文書', d1.po_doc(T(f'f4p{s}'), DT, o0, 400 + s, note='納品書に当社発注番号を記載のこと。'), ppo, '注文書（控）', 'P05', kp)
        if x.get('chg'):
            emit('F4', f'04_S{s}_注文変更書', d1.po_change(T(f'f4h{s}'), DT, x, 440 + s), PL('fax+skew1', hdr=fh(x['chg'], 'ｱｵﾊﾞｷｺｳ ｺｳﾊﾞｲ 03-0155-2196')), '注文変更書', 'P05',
                 ('k_po', 'k_date', 'k_old', 'k_new', 'k_st_ka'))
        emit('F4', f'04_S{s}_検収報告書', d1.grn(T(f'f4g{s}'), DT, o, 0, 410 + s, note='分納（1回目）。残り20個は9月上旬に入荷予定。' if s == 2 else '外観・数量とも異常なし。'),
             pg, '検収報告書', 'P05', kg)
        g, ino = d1.invoice(T(f'f4i{s}'), DT, o, lines, x['inv'], 420 + s, 'A' if s % 2 else 'B')
        if s == 1:
            a = yen(lines[0][1] * lines[0][2])
            pi.layer, pi.wrong, pi.hdr = 'wrong', {'k_amt1': (a, digit(a, 0))}, sfax(add_bd(x['inv'], 2), S[o['s']])
        emit('F4', f'04_S{s}_請求書', g, pi, '請求書', 'P05', ki)
        emit('F4', f'04_S{s}_請求書照合票', d1.pay_req(T(f'f4r{s}'), DT, o, ino, lines, x, 430 + s, who_=['立花', '宮下'][s % 2]), prq, '請求書照合票 兼 支払依頼書', 'P05', kr)

    # ---- F5 支払 ----
    for b in DT['PAY']:
        n = len(b['rows'])
        tag = b['pd'].strftime('%Y-%m-%d')
        tot = yen(sum(r['pay'] for r in b['rows']))
        kpl = ['k_st_made', 'k_st_ok', 'k_st_sent', 'k_tbill', 'k_toff', 'k_total'] + [f'k_{k}{i}' for i in range(n) for k in ('bill', 'off', 'pay', 'acct')]
        pp, pf_ = {1: (PL('copy+skew1'), PL('fax', hdr=fh(b['sent'], 'ﾋｶﾘﾁﾕｳｵｳｷﾞﾝｺｳ ｼﾊﾞｳﾗ 03-0155-7001'))),
                   2: (PL('faded', layer='wrong', wrong={'k_total': (tot, digit(tot, 1))}), PL('lowres', fmt='jpg', dmg=[('torn', (0, 264, 118, 297), IRR, '下端の注記・銀行の所在地')]))}[b['n']]
        emit('F5', f'05_支払予定表_{tag}', d1.pay_plan(T(f'f5p{b["n"]}'), DT, b, 500 + b['n']), pp, '支払予定表', 'P06', kpl)
        emit('F5', f'05_振込受付結果_{tag}', d1.fb_result(T(f'f5f{b["n"]}'), DT, '総合振込 受付結果（照会）', b['pd'], [(r['s'], r['pay']) for r in b['rows']], 510 + b['n'], b['sent']),
             pf_, '総合振込 受付結果（銀行）', 'P06', ('k_pd', 'k_cnt', 'k_total', 'k_amt0', 'k_amt5', f'k_amt{n - 1}', 'k_acct0'))

    # ---- F6 残高確認 ----
    for s, c in DT['CF'].items():
        if c['kind'] == 'transit':
            c['why'] = f'3/30出荷分（貴社注文 {c["po"]["no"]}）を当社は3月の売上に計上しています'
            c['cause'] = f'未達。仕入先は3/30出荷時に売上計上、当社は4/2に検収（{c["po"]["sino"][0]}、税込{yen(c["delta"])}円）'
            c['ev'] = '期後の検収報告書'
        elif c['kind'] == 'credit':
            c['why'] = f'3/31付で値引（{yen(c["delta"])}円）を処理済みです。値引通知書をご参照ください'
            c['cause'] = f'仕入先は3/31付で値引（税込{yen(c["delta"])}円）を処理済み。当社は4月に処理'
            c['ev'] = '値引通知書'
        elif c['kind'] == 'noans':
            c['cause'] = f'未回答。代替手続として、4/30の支払（振込明細）で3月末残高と同額の支払を確認'
            c['ev'] = '期後の振込明細'
    reps = [s for s in DT['top8'] if DT['CF'][s]['kind'] != 'noans']
    pool = {'ok': [PL('fax'), PL('photo', fmt='jpg'), PL('jitter+fax'), PL('dark', dmg=[('blotch', 'x_pic', IRR, '担当者名')]),
                   PL('lowres', fmt='jpg', dmg=[('blotch', 'x_pic', IRR, '担当者名')])], 'transit': [PL('copy+skew2')], 'credit': [PL('faded+skew3')]}
    nok = 0
    for s in reps:
        c = DT['CF'][s]
        p = pool[c['kind']].pop(0)
        if p.ops.endswith('fax'):
            p.hdr = sfax(c['back'], S[s])
        if c['kind'] == 'ok':
            nok += 1
            if nok == 3:
                p.layer, p.wrong = 'wrong', {'k_ours': (yen(c['ours']), digit(yen(c['ours']), 1))}
        emit('F6', f'06_残高確認回答書_{S[s]["code"]}', d2.confirm_reply(T(f'f6c{s}'), DT, c, 600 + c['rank']), p, '残高確認書（仕入先の回答）', 'P07',
             ('k_sup', 'k_ours', 'k_chk', 'k_ans', 'k_why', 'k_seal'))
    emit('F6', '06_差異調整表', d2.recon_sheet(T('f6r'), DT, 620), PL('streak+skew2'), '残高確認 差異調整表', 'P07',
         ['k_st_made', 'k_st_ok', 'k_concl'] + [f'k_{k}{i}' for i in range(8) for k in ('ours', 'ans', 'diff', 'cause')])
    emit('F6', '06_発送管理表', d2.send_list(T('f6s'), DT, 621), PL('dark'), '残高確認状 発送管理表', 'P07,P08', [f'k_{k}{i}' for i in (0, 2, 7) for k in ('code', 'bal', 'state')])
    for s, c in DT['CF'].items():
        if c['kind'] == 'transit':
            emit('F6', f'06_期後の検収報告書_{S[s]["code"]}', d1.grn(T('f6g'), DT, c['po'], 0, 622), PL('fax', hdr=fh(D(2026, 4, 2), 'ｱｵﾊﾞｷｺｳ ﾌﾞﾂﾘﾕｳ 03-0155-2194')),
                 '期後の検収報告書（未達の裏付け）', 'P07', ('k_no', 'k_date', 'k_po', 'k_qty1', 'k_st_insp'))
        elif c['kind'] == 'credit':
            emit('F6', f'06_値引通知書_{S[s]["code"]}', d2.credit_note(T('f6n'), DT, c, 623), PL('show+skew2'), '値引通知書（仕入先発行）', 'P07', ('k_no', 'k_date', 'k_amt'))
        elif c['kind'] == 'noans':
            emit('F6', f'06_期後の振込明細_{S[s]["code"]}', d1.fb_result(T('f6f'), DT, '振込明細（照会・抜粋）', c['paid'], [(s, c['ours'])], 624,
                                                                 note='※ 2026年4月30日支払分のうち、当該仕入先の明細を抜粋して照会したもの。'),
                 PL('copy'), '期後の振込明細（代替手続）', 'P07', ('k_pd', 'k_total', 'k_amt0'))

    # ---- F7 月次購買実績 ----
    for n, rp in enumerate(DT['REP']):
        ks = ['k_st_made', 'k_st_ok', 'k_total'] + [f'k_{k}{i}' for i in range(10) for k in ('cur', 'prev', 'rate', 'cm') if rp['rows'][i]['need'] or i in (0, 9)]
        if n == 1:
            i = [r['s'] for r in rp['rows']].index(DT['SA'])
            v = yen(rp['rows'][i]['cur'])
            p = PL('faded', layer='wrong', wrong={f'k_cur{i}': (v, digit(v, 1))})
        else:
            p = [PL('photo', fmt='jpg'), None, PL('copy+skew1')][n]
        emit('F7', f'07_月次購買実績報告書_{rp["y"]}-{rp["m"]:02d}', d2.m_report(T(f'f7m{n}'), DT, rp, 700 + n), p, '月次購買実績報告書', 'P09', ks)

    # ---- F8 ウォークスルー ----
    x = DT['WT']
    o = x['o']
    emit('F8', '08_業務記述書', d2.narrative(T('f8n'), 800), PL('show+skew2'), '業務記述書（購買プロセス）', 'P10', ('k_step1', 'k_step3', 'k_step5', 'k_step6', 'k_step7'))
    emit_screen('F8', '08_フローチャート', up(sp.flowchart(801), 1.8), PL('photo', fmt='jpg'), 'フローチャート（図）', 'P10', ('k_b1', 'k_b3', 'k_b5', 'k_b6', 'k_b7'))
    emit('F8', '08_購買依頼書', d2.p_req(T('f8q'), DT, x, 802), PL('fax+skew1', hdr=fh(x['req'], 'ｱｵﾊﾞｷｺｳ ｴｲｷﾞﾖｳ2 03-0155-2197')), '購買依頼書', 'P10', ('k_date', 'k_qty', 'k_st_head', 'k_st_recv'))
    emit('F8', '08_注文書', d1.po_doc(T('f8p'), DT, o, 803), PL('copy', dmg=[('blotch', 'x_place', IRR, '納入場所')]), '注文書（控）', 'P10', kp)
    emit('F8', '08_検収報告書', d1.grn(T('f8g'), DT, o, 0, 804), PL('jitter'), '検収報告書', 'P10', kg)
    g, ino = d1.invoice(T('f8i'), DT, o, o['lines'], x['inv'], 805, 'A')
    emit('F8', '08_請求書', g, PL('faded+skew2', dmg=[('water', 'x_bank', IRR, '振込先の記載', 0.8)]), '請求書', 'P10', ki)
    emit('F8', '08_請求書照合票', d1.pay_req(T('f8r'), DT, o, ino, o['lines'], x, 806), PL('streak'), '請求書照合票 兼 支払依頼書', 'P10', kr + ('k_due',))
    emit('F8', '08_振込明細', d1.fb_result(T('f8f'), DT, '振込明細（照会・抜粋）', x['pay'], [(o['s'], int(dp.amt(o) * 1.1))], 807,
                                        note='※ 2025年12月26日支払分のうち、当該仕入先の明細を抜粋して照会したもの。データ作成：KEI002（宮下）　承認：KEI001（溝口）'),
         None, '振込明細（銀行）', 'P10', ('k_pd', 'k_total', 'k_amt0'))

    # ---- F9 ヒアリング ----
    emit('F9', '09_ヒアリング記録', d2.interview(T('f9i'), DT, 900), PL('copy+skew1'), 'ヒアリング記録', 'P11', ('k_a1', 'k_ev1', 'k_a2', 'k_ev2', 'k_st_ack'))
    emit('F9', '09_仕入先評価結果一覧', d2.eval_list(T('f9e'), DT, 901), PL('fax', hdr=fh(D(2026, 4, 15), 'ｱｵﾊﾞｷｺｳ ｺｳﾊﾞｲ 03-0155-2196')), '仕入先評価結果一覧', 'P11',
         ('k_cnt', 'k_last', 'k_lastname', 'k_st_ka', 'k_st_bu'))

    # ---- F10 システム権限・設定 ----
    ku = ('k_ng', 'k_ng_dept', 'k_ng_reg', 'k_ng_state', 'k_ng_last', 'k_sb', 'k_sb_state', 'k_u4', 'k_adm', 'k_u12', 'k_u14')
    emit_screen('F10', '10_利用者権限一覧_1', up(sp.users_screen(1, 1), 1.5), PL('ssphoto', fmt='jpg'), '利用者ID・権限一覧（画面の写し 1/2）', 'P12', ku)
    emit_screen('F10', '10_利用者権限一覧_2', sp.users_screen(2, 2), PL('sslow', fmt='xlsx'), '利用者ID・権限一覧（画面の写し 2/2）', 'P12', ku)
    emit('F10', '10_人事異動一覧', d2.hr_moves(T('f10h'), 1000), PL('fax+skew2', hdr=fh(D(2026, 4, 14), 'ｱｵﾊﾞｷｺｳ ｼﾞﾝｼﾞ 03-0155-2193')), '人事異動・退職者一覧', 'P12',
         ('k_sb_d', 'k_sb', 'k_sb_k', 'k_ng_d', 'k_ng', 'k_ng_to'))
    emit('F10', '10_特権ID管理台帳', d2.priv_ledger(T('f10p'), 1001), PL('faded'), '特権ID管理台帳', 'P12', ('k_id', 'k_user', 'k_term', 'k_log', 'k_st_ka', 'k_st_yk'))
    emit('F10', '10_権限棚卸記録', d2.access_review(T('f10a'), 1002), PL('copy'), '利用者権限 棚卸記録', 'P12', ('k_date', 'k_cnt', 'k_result', 'k_st_bu'))
    emit_screen('F10', '10_照合条件設定画面', sp.setting_screen(3), PL('sslow', fmt='png'), '請求照合の条件設定（画面の写し）', 'P13', ('k_qtol', 'k_ptol', 'k_act', 'k_upd', 'k_hist'))
    emit_screen('F10', '10_照合テスト結果画面', sp.test_screen(4), None, '請求照合のテスト結果（画面の写し）', 'P13', ('k_recv', 'k_inv', 'k_err', 'k_state'))

    # ---- 共通資料 ----
    emit('X', '購買管理規程', d2.rules_p(T('rules'), 21), PL('copy+skew1', vec=[0]), '購買管理規程', '全般', ('k_art8', 'k_art9', 'k_art16', 'k_art17'))
    emit('X', '職務権限規程', d2.authority_p(T('auth'), 22), PL('scan'), '職務権限規程（購買関連の決裁権限・役職者一覧）', 'P03,P10', ('k_a1', 'k_a2r', 'k_a2', 'k_a3', 'k_a4', 'k_r1', 'k_r2', 'k_r5'))

    for o_ in DT['O']:
        pass
    DT.pop('groups')
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
    per = 55
    for n in range(0, len(cells), per):
        sheet = Image.new('RGB', (520 * 5, 150 * 11), (200, 200, 200))
        for i, c in enumerate(cells[n:n + per]):
            sheet.paste(c, ((i % 5) * 520, (i // 5) * 150))
        sheet.save(f'{B.TMP}/crops_{n // per:02d}.png')
    tot = sum(os.path.getsize(os.path.join(r, x)) for r, _, fs in os.walk(B.HARD) for x in fs)
    print('files', len(B.MAN), 'crops', len(B.CROPS), 'hard MB', round(tot / 1e6, 1))


if __name__ == '__main__':
    main()
