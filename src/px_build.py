# -*- coding: utf-8 -*-
"""購買プロセス 実務版の素材: 版違いの文書、無関係な資料、送付状、白紙、大量ページの帳票"""
import copy
from fw import *
import data_p as dp, docs_p as d1, docs_p2 as d2

NAME, KEY = '購買_実務版_素材', 'px'
MM = 72 / 25.4


def rework(g, blank=(), mark=None, at=(120, 14)):
    """保存済みのPDFに手を入れる: 承認欄を空欄に戻す、注記を入れる"""
    doc = fitz.open(g.path)
    for k in blank:
        pn, x0, y0, x1, y1 = g.boxes[k]
        doc[pn].draw_rect(fitz.Rect(x0 * MM + 1, y0 * MM + 1, x1 * MM - 1, y1 * MM - 1), color=None, fill=(1, 1, 1))
        g.kv[k] = '空欄'
    if mark:
        doc[0].insert_text((at[0] * MM, at[1] * MM), mark, fontsize=13, fontname='jb', fontfile=fp('B'), color=(0.75, 0.05, 0.05))
        g.kv['k_mark'] = mark
        g.boxes['k_mark'] = (0, at[0] - 1, at[1] - 5.5, at[0] + len(mark) * 4.7, at[1] + 2)
    tmp = g.path + '.tmp'
    doc.save(tmp)
    doc.close()
    os.replace(tmp, g.path)
    return g


def po_list(path, DT):
    """発注一覧の印刷（全件・大量ページ）"""
    rows = DT['porows']
    per = 45
    n = (len(rows) + per - 1) // per
    g = Pg(path, land=True, seed=5)
    cols = [('発注番号', 26, 'c'), ('行', 8, 'c'), ('発注日', 22, 'c'), ('コード', 14, 'c'), ('仕入先名', 56, 'l'), ('品番', 28, 'l'), ('数量', 14, 'r'), ('単価', 18, 'r'), ('金額（税抜）', 24, 'r'), ('依頼部署', 18, 'c'),
            ('起票', 16, 'c'), ('承認', 16, 'c'), ('備考', 13, 'l')]
    for pi in range(n):
        if pi:
            g.newpage()
        g.t(12, 10, 'P0210 発注一覧　対象：2025/04/01〜2026/03/31（全件）', 9, 'B')
        g.t(285, 10, f'出力日時 2026/04/13 09:45　出力者 大西　{pi + 1} / {n} ページ', 8, al='r')
        part = rows[pi * per:(pi + 1) * per]
        g.tbl(12, 13, cols, [[r[0], r[1], sd(r[2]), r[3], r[4], r[5], yen(r[7]), yen(r[8]), yen(r[9]), r[10], r[11].split()[0] if ' ' in r[11] else r[11][:2], r[12].split()[0] if ' ' in r[12] else r[12][:2],
                               '＊' if r[15] else ''] for r in part], 4.05, 7.2, hh=5, hsz=7.5, lw=0.2)
        if pi == n - 1:
            g.t(12, 13 + 5 + len(part) * 4.05 + 5, f'合計 {len(rows):,} 行　発注金額合計 {sum(r[9] for r in rows):,} 円　　＊＝備考あり（発注データを参照）', 8.5, 'B')
    return g.save()


def build():
    setup(NAME, KEY, {'N': 'new'}, {})
    DT = dp.build()
    set_other(d2.rules_p(T('rules'), 21))
    # 1. 支払予定表（2025/9/10 支払分）の修正前の版: 返品相殺の反映前。承認・FB送信の前
    b2 = copy.deepcopy(DT['PAY'][0])
    for r in b2['rows']:
        if r['off']:
            r['off'], r['pay'] = 0, r['bill']
    b2['made'] = add_bd(b2['made'], -1)
    g = rework(d1.pay_plan(T('v_pay'), DT, b2, 990), ('k_st_ok', 'k_st_sent'), '修正前（返品相殺の反映前）', (120, 30))
    emit('N', 'v_支払予定表_2025-09-10_修正前', g, PL('faded+skew1'), '支払予定表（修正前の版）', 'P06', ('k_total', 'k_toff', 'k_mark', 'k_st_ok'))
    # 2. 見積比較表 S2 の案: 最安値の業者を選定する内容。購買課長の承認前
    x = DT['Q'][1]
    qnos = [d1.quote(T(f'q{vi}'), DT, x, vi, 200 + 20 + vi)[1] for vi in range(3)]
    x2 = {k: v for k, v in x.items() if k != 'reason'}
    x2['sel'], x2['cmp'] = 1, D(2025, 8, 20)
    g = rework(d1.q_compare(T('v_cmp'), DT, x2, 992, qnos), ('k_st_ka',), '（案）', (150, 22))
    emit('N', 'v_見積比較表_S2_案', g, PL('copy+skew2'), '見積比較表（案）', 'P02', ('k_sel', 'k_why', 'k_mark', 'k_st_ka'))
    # 3. 月次照合チェックリスト 2026年2月の作成中の版（最終版は提出されていない）
    ck = [c for c in DT['CK'] if (c['y'], c['m']) == (2026, 2)][0]
    g = rework(d1.m_check(T('v_chk'), DT, ck, 993), ('k_st',), '作成中（承認前）　※最終版は経理課で保管', (62, 32))
    emit('N', 'v_月次照合チェックリスト_2026-02_作成中', g, PL('faded'), '月次照合チェックリスト（作成中の版）', 'P01', ('k_cnt', 'k_log1', 'k_mark', 'k_st'))
    # 4. 購買管理規程の旧版（2023年4月改定）: 基準の数値が現行と異なる
    old = [(h, b.replace('税抜50万円以上の発注', '税抜100万円以上の発注').replace('連続する3営業日以内', '連続する5営業日以内').replace('上位8社', '上位5社').replace('±30％以上', '±50％以上')) for h, b in d2.RULES_P]
    assert sum(a != b for a, b in zip(old, d2.RULES_P)) == 4
    g = d2.rules_p(T('v_rules'), 21, rev='制定 2012年4月1日　最終改定 2023年4月1日', rules=old)
    emit('N', 'v_購買管理規程_旧版', g, PL('copy+skew2'), '購買管理規程（旧版・2023年4月改定）', '全般', ('k_rev', 'k_art8', 'k_art9'))
    # 5. 送付状（表紙）
    g, y = form(T('cover'), '資料送付のご案内', who=['内部監査室　御中', '2026年4月10日', '経理部 経理課　立花'],
                rows=[('gap', 8), ('txt', 'ご依頼のありました資料を、下記のとおり送付いたします。原本は経理課で保管しています。', 10.5), ('gap', 4),
                      ('tbl', [('No', 14, 'c'), ('資料', 120, 'l'), ('枚数', 52, 'c')], [['1', '3月ご依頼分（請求書の照合関係）　4件分一式', '本紙を含め 20 枚'], ['2', '支払関係', '別ファイル'], ['3', 'マスタ変更関係', '別ファイル']],
                       dict(rh=10, sz=10.5)), ('gap', 4), ('txt', '※ スキャンの都合上、順番が前後しているものがあります。ご了承ください。', 9.5)])
    emit('N', 'n_送付状', g.save(), PL('copy'), '送付状（表紙）', '-', ())
    # 6. 無関係な資料: サンプル以外の取引の請求書照合票
    o = [o for o in DT['O'] if not o['tag'] and len(o['lines']) == 1 and o['od'].month == 8 and o['recs'][0][0] <= D(2025, 8, 29) and 300_000 < dp.amt(o) < 900_000][3]
    g = d1.pay_req(T('noise'), DT, o, f'{o["s"] + 1:03d}-2508-611', o['lines'], dict(chk=D(2025, 9, 9), diff='なし'), 994, who_='宮下')
    emit('N', 'n_別取引_請求書照合票', g, PL('wavy'), '請求書照合票（サンプル以外の取引）', '-', ('k_po', 'k_total'))
    # 7. 白紙
    g = Pg(T('blank'), seed=9)
    g.ln(5, 5, 5.02, 5.02, 0.01, col=(1, 1, 1))
    emit('N', 'n_白紙', g.save(), PL('scan'), '白紙', '-', ())
    # 8. 大量ページ: 発注一覧の印刷（電子的に出力したPDF。難版・対照版とも同じ）
    g = po_list(T('polist'), DT)
    emit('N', 'L_発注一覧_全件', g, None, '発注一覧（システムからの出力・全件）', 'P04', ())
    print('発注一覧のページ数', g.pno + 1, '別取引', o['no'])
    return dict(noise_po=o['no'], pages=g.pno + 1, old_rules=[(a[0], b[1]) for a, b in zip(d2.RULES_P, old) if a != b])


if __name__ == '__main__':
    DT = build()
    finish(DT)
