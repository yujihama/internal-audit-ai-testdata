# -*- coding: utf-8 -*-
"""購買プロセスの証跡（読みやすい原本）その1: マスタ変更、見積・発注、検収・請求・支払"""
from common import *
from render import *
import docs
from docs import DS, SL, dsd, co_block, ICOLS
from data_p import *

docs.SEC.update(SECP)
GR_ = (0.93, 0.93, 0.93)


def hdr(g, title, form=None, no=None, key='k_no', sz=16):
    if form:
        g.t(12, 12, form, 7.5)
    if no:
        g.t(198, 12, no, 9.5, key=key, al='r')
    g.t(105, 23, title, sz, 'B', al='c')


def who(g, lines, y=37, x=12):
    for i, l in enumerate(lines):
        if isinstance(l, tuple):
            g.t(x, y + i * 7, l[0], 10, key=l[1])
        else:
            g.t(x, y + i * 7, l, 10)


def big(g, y, h, label, text, key, n=38, x=12, w1=30, w=186, hand=False, f='G'):
    g.rc(x, y, w1, h, fill=GR_)
    g.t(x + 1.5, y + h / 2 + 1, label, 8.5)
    g.rc(x + w1, y, w - w1, h)
    if text:
        g.para(x + w1 + 3, y + 7, text, n, 10, f, hand=hand)
    if key:
        g.box(key, x + w1 + 1, y + 1, w - w1 - 2, h - 2, label)


def totals(g, y, tot, keys=('k_total', None, 'k_gt'), labels=('合計（税抜）', '消費税（10%）', '税込合計'), x=118):
    for i, (a, b, k) in enumerate(zip(labels, (tot, int(tot * 0.1), int(tot * 1.1)), keys)):
        g.lv(x, y + i * 8, 48, 32, 8, a, '')
        g.t(196.5, y + i * 8 + 5.4, yen(b), 10, key=k, al='r')
    return y + 24


def irows(lines, n_min=4, sz=None):
    rows, keys = [], {}
    for i, (p, q, c) in enumerate(lines):
        rows.append([i + 1, PROD[p][0], PROD[p][1], yen(q), PROD[p][2], yen(c), yen(q * c)])
        keys.update({(i, 1): f'k_code{i + 1}', (i, 3): f'k_qty{i + 1}', (i, 5): f'k_price{i + 1}', (i, 6): f'k_amt{i + 1}'})
    while len(rows) < n_min:
        rows.append([''] * 7)
    return rows, keys


def vend(g, sup, x, y, f='G', seal=True, key='k_sup'):
    g.t(x, y, sup['name'], 11.5, 'B' if f == 'G' else f, key=key)
    g.t(x, y + 6, f'{sup["zip"]} {sup["addr"]}', 8.5, f)
    g.t(x, y + 11, f'TEL {sup["tel"]}　担当：{sup["pic"]}', 8.5, f)
    if seal:
        g.im(sqseal(sup['short'] + '株式会社', g.nrng, 0.9), x + 58, y - 8, 20, 20)


# ================= C1 仕入先マスタ変更 =================
def acct_app(path, DT, ch, seed):
    g = Pg(path, seed=seed)
    sup = DT['S'][ch['s']]
    hdr(g, '仕入先 振込口座変更申請書', '様式 経-018', f'申請番号　{ch["appno"]}')
    who(g, [(f'申請日　　{jd(ch["app"])}', 'k_appdate'), '申請部署　購買部 購買課', f'申請者　　{pf(sup["buyer"])}'])
    g.appr(129, 30, [('申請者', SL(g, sup['buyer']), 'k_st_rep', f'印 {sup["buyer"]}'),
                     ('購買課長', DS(g, KA, ch['ka']), 'k_st_ka', dsd(KA, ch['ka'])),
                     ('経理登録', DS(g, ch['by'], ch['reg']), 'k_st_reg', dsd(ch['by'], ch['reg']))], w=23, h=22)
    y = 64
    g.lv(12, y, 30, 156, 9, '仕入先', f'{sup["code"]}　{sup["name"]}', key='k_sup')
    g.lv(12, y + 9, 30, 156, 9, '変更前の口座', astr(ch['old']), key='k_old')
    g.lv(12, y + 18, 30, 156, 11, '変更後の口座', astr(ch['new']), 12, key='k_new', f='B')
    g.lv(12, y + 29, 30, 156, 9, '口座名義', hankaku(sup['kana']))
    big(g, y + 38, 18, '変更理由', ch['why'] + '（仕入先からの申し出による）。', 'x_reason')
    g.lv(12, y + 56, 30, 156, 9, '根拠資料', '■ 仕入先からの変更依頼書（社印あり）　□ その他')
    big(g, y + 65, 18, '本人確認', f'登録済みの電話番号（{sup["tel"]}）へ架電し、{sup["pic"]}様に変更の事実を確認した（{md(ch["app"])}）。', 'x_call')
    g.lv(12, y + 83, 30, 63, 9, 'マスタ登録日', sd(ch['reg']), 11, key='k_reg')
    g.t(12, y + 102, '※ 振込口座の変更は、仕入先の依頼書と本人確認を経て購買課長が承認し、経理課が登録する（購買管理規程 第6条）。', 8)
    g.t(12, y + 107, '※ 経理課長は、月次でマスタ変更ログと本申請書を照合する。', 8)
    return g.save()


def sup_letter(path, DT, ch, seed):
    g = Pg(path, seed=seed)
    sup = DT['S'][ch['s']]
    a = ch['new']
    g.t(196, 22, wd(ch['letter']), 10.5, 'M', key='k_date', al='r')
    g.t(16, 34, CO['name'], 12, 'M')
    g.t(16, 41, '購買部 御中', 12, 'M')
    g.t(118, 54, sup['name'], 12, 'M', key='k_sup')
    g.t(118, 60, f'{sup["zip"]} {sup["addr"]}', 9, 'M')
    g.t(118, 65, f'経理部　TEL {sup["tel"]}', 9, 'M')
    g.im(sqseal(sup['short'] + '株式会社', g.nrng, 0.9), 174, 46, 21, 21)
    g.t(105, 84, 'お振込先口座変更のお願い', 15, 'M', al='c')
    y = g.para(18, 98, '拝啓　時下ますますご清栄のこととお慶び申し上げます。平素は格別のお引き立てを賜り、厚く御礼申し上げます。'
                       f'さて、このたび弊社では{ch["why"]}、お振込先の口座を下記のとおり変更させていただくことになりました。'
                       'お手数をおかけいたしますが、次回のお支払い分より新口座へお振込みくださいますようお願い申し上げます。　敬具', 46, 10.5, 'M')
    g.box('x_greet', 16, 91, 180, y - 91, 'あいさつ文')
    g.t(105, y + 6, '記', 11, 'M', al='c')
    y += 12
    for i, (k, v, key) in enumerate([('新口座　銀行名', a['bank'], 'k_newbank'), ('　　　　支店名', a['br'], 'k_newbr'), ('　　　　預金種別', a['kind'], None),
                                     ('　　　　口座番号', a['no'], 'k_newno'), ('　　　　口座名義', hankaku(sup['kana']), None),
                                     ('旧口座', astr(ch['old']), 'k_old'), ('変更日', jd(add_bd(ch['letter'], 8)) + ' お支払い分より', None)]):
        g.lv(30, y + i * 9.5, 40, 110, 9.5, k, v, 12 if key == 'k_newno' else 10.5, key=key, f='M', fill=(1, 1, 1))
    g.t(180, y + 74, '以上', 10.5, 'M', al='r')
    g.t(16, y + 90, f'本件に関するお問い合わせ先：経理部 {sup["pic"]}（TEL {sup["tel"]}）', 9.5, 'M', key='x_contact')
    return g.save()


def m_check(path, DT, ck, seed):
    g = Pg(path, seed=seed)
    S = DT['S']
    hdr(g, f'仕入先マスタ変更 月次照合チェックリスト（{ck["y"]}年{ck["m"]}月分）', '様式 経-019', sz=13.5)
    who(g, ['経理課', '照合対象：仕入先マスタ変更ログ（当月分）と変更申請書'])
    g.appr(170, 30, [('照合（経理課長）', DS(g, '溝口', ck['ok']), 'k_st', dsd('溝口', ck['ok']))], w=26, h=22)
    g.lv(12, 64, 44, 40, 9, '当月の変更件数（全区分）', f'{ck["n"]} 件', 11, key='k_n')
    g.lv(105, 64, 44, 40, 9, 'うち振込口座変更', f'{len(ck["ac"])} 件', 11, key='k_cnt', f='B')
    g.t(12, 84, '振込口座変更の照合明細', 10, 'B')
    rows = [[l['no'], sd(l['d']), f'{S[l["s"]]["code"]} {S[l["s"]]["name"]}', l['app'], '一致'] for l in ck['ac']]
    keys = {(i, 0): f'k_log{i + 1}' for i in range(len(rows))}
    keys.update({(i, 3): f'k_app{i + 1}' for i in range(len(rows))})
    while len(rows) < 3:
        rows.append([''] * 5)
    y = g.tbl(12, 88, [('ログNo', 20, 'c'), ('変更日', 28, 'c'), ('仕入先', 84, 'l'), ('申請番号', 32, 'c'), ('照合結果', 22, 'c')], rows, 9, 10, keys=keys)
    g.lv(12, y + 8, 44, 142, 9, 'その他の変更', f'{ck["n"] - len(ck["ac"])} 件。すべて変更申請書の内容と一致。')
    g.lv(12, y + 17, 44, 142, 10, '照合結果', '不一致なし', 11, key='k_result', f='B')
    g.t(12, y + 38, '※ 経理課長は、翌月5営業日以内に当月のマスタ変更ログ全件を申請書と照合する（購買管理規程 第6条）。', 8)
    return g.save()


# ================= C2 見積比較・発注 =================
def quote(path, DT, x, vi, seed):
    si, price, due, incl, style, qd = x['v'][vi]
    sup = DT['S'][si]
    p = PIDX[x['item']]
    sub = price * x['qty']
    g = Pg(path, seed=seed)
    f = {'A': 'G', 'B': 'M', 'C': 'G'}[style]
    qno = f'{"QMR"[vi]}{qd.strftime("%y%m%d")}-{seed % 90 + 10}'
    g.t(105, 25, {'A': '御　見　積　書', 'B': 'お 見 積 書', 'C': '見　積　書'}[style], 18, 'B' if f == 'G' else 'M', al='c')
    g.t(198, 36, f'見積番号　{qno}', 10, f, key='k_qno', al='r')
    g.t(198, 42, f'見積日　{sd(qd) if style != "B" else wd(qd)}', 10, f, key='k_qdate', al='r')
    g.t(14, 44, f'{CO["name"]}　購買課 御中', 12.5, 'B' if f == 'G' else 'M')
    g.ln(14, 46, 108, 46, 0.8)
    vend(g, sup, 118, 56, f, key='k_vendor')
    g.t(14, 76, f'件名：{PROD[p][1]} {x["qty"]}{PROD[p][2]}', 10.5, f)
    g.rc(14, 81, 96, 12, 0.9)
    g.t(17, 89, '御見積金額（消費税込）' if incl else '御見積金額（税抜）', 10, f)
    g.t(107, 89.5, f'￥{yen(int(sub * 1.1) if incl else sub)}', 14, 'B', key='k_total', al='r')
    rows, keys = irows([(p, x['qty'], price)], 4)
    y = g.tbl(12, 99, ICOLS, rows, 8.5, 10, f, keys=keys)
    y = totals(g, y, sub, ('k_sub', 'k_tax', 'k_gt'), ('小計（税抜）', '消費税（10%）', '合計（税込）'))
    g.box('x_tot', 118, y - 24, 80, 24, '小計・消費税・合計')
    g.lv(12, y + 6, 30, 156, 9, '納期', due, key='k_due', f=f)
    g.lv(12, y + 15, 30, 156, 9, '有効期限', '見積日より30日間', f=f)
    g.lv(12, y + 24, 30, 156, 9, 'お支払条件', '貴社規定による', f=f)
    big(g, y + 33, 20, '備考', '価格は貴社指定場所渡し（運賃込み）。数量変更の際は再見積りとなります。', 'x_note', f=f)
    return g.save(), qno


def q_compare(path, DT, x, seed, qnos):
    g = Pg(path, seed=seed)
    S = DT['S']
    p = PIDX[x['item']]
    by = S[x['v'][x['sel']][0]]['buyer']
    no = f'MH-{x["od"].strftime("%y%m")}-{x["s"]:02d}'
    hdr(g, '見 積 比 較 表', '様式 購-007', f'比較表番号　{no}')
    who(g, [(f'作成日　　{jd(x["cmp"])}', 'k_date'), '作成部署　購買部 購買課', f'起票者　　{pf(by)}'])
    g.appr(152, 30, [('起票', DS(g, by, x['cmp']), 'k_st_rep', dsd(by, x['cmp'])), ('購買課長', DS(g, KA, x['cmp']), 'k_st_ka', dsd(KA, x['cmp']))], w=23, h=22)
    g.lv(12, 64, 30, 156, 9, '件名', f'{PROD[p][0]}　{PROD[p][1]}　{x["qty"]}{PROD[p][2]} の購入')
    g.lv(12, 73, 30, 156, 9, '依頼部署', x['dept'])
    shown = [x['err'].get(i, v[1] * x['qty']) for i, v in enumerate(x['v'])]
    order = sorted(range(len(shown)), key=lambda i: shown[i])
    rows, keys = [], {}
    for i, v in enumerate(x['v']):
        rows.append([S[v[0]]['name'], qnos[i], yen(shown[i]), v[2], order.index(i) + 1, '税込表示を税抜に換算' if v[3] else ''])
        keys.update({(i, 0): f'k_v{i + 1}', (i, 2): f'k_a{i + 1}', (i, 4): f'k_r{i + 1}'})
    y = g.tbl(12, 90, [('業者名', 58, 'l'), ('見積番号', 28, 'c'), ('見積金額（税抜）', 30, 'r'), ('納期', 26, 'c'), ('順位', 12, 'c'), ('備考', 32, 'l')],
              rows, 10, 10, keys=keys, hsz=8.5)
    sel = x['v'][x['sel']]
    g.lv(12, y + 8, 30, 156, 10, '選定業者', f'{S[sel[0]]["name"]}　（{yen(shown[x["sel"]])} 円）', 11, key='k_sel', f='B')
    g.lv(12, y + 18, 30, 156, 10, '選定理由', '納期を優先（別紙「選定理由書」のとおり）' if x.get('reason') else '最安値のため', 10.5, key='k_why')
    g.t(12, y + 40, '※ 税抜50万円以上の発注は、2社以上から見積を取得して本表を作成する。最安値の業者を選定することを原則とし、', 8)
    g.t(12, y + 45, '　 それ以外を選定する場合は選定理由書により購買部長の承認を得る（購買管理規程 第8条）。金額は税抜で比較する。', 8)
    return g.save()


def reason_doc(path, DT, x, seed):
    g = Pg(path, seed=seed)
    S = DT['S']
    by = S[x['v'][x['sel']][0]]['buyer']
    am = [v[1] * x['qty'] for v in x['v']]
    lo = min(range(len(am)), key=lambda i: am[i])
    hdr(g, '選 定 理 由 書', '様式 購-008')
    who(g, [f'作成日　　{jd(x["cmp"])}', '作成部署　購買部 購買課', f'起票者　　{pf(by)}'])
    g.appr(129, 30, [('起票', DS(g, by, x['cmp']), 'k_st_rep', dsd(by, x['cmp'])), ('購買課長', DS(g, KA, x['cmp']), 'k_st_ka', dsd(KA, x['cmp'])),
                     ('購買部長', DS(g, BU, x['reason']), 'k_st_bu', dsd(BU, x['reason']))], w=23, h=22)
    g.lv(12, 64, 36, 150, 9, '対象の見積比較表', f'MH-{x["od"].strftime("%y%m")}-{x["s"]:02d}', key='k_no')
    g.lv(12, 73, 36, 150, 10, '選定業者・金額', f'{S[x["v"][x["sel"]][0]]["name"]}　{yen(am[x["sel"]])} 円（税抜）', 10.5, key='k_sel')
    g.lv(12, 83, 36, 150, 10, '最安値の業者・金額', f'{S[x["v"][lo][0]]["name"]}　{yen(am[lo])} 円（税抜）', 10.5, key='k_low')
    g.lv(12, 93, 36, 150, 9, '価格差', f'{yen(am[x["sel"]] - am[lo])} 円', key='k_gap')
    big(g, 102, 34, '選定の理由',
        f'顧客への納入期限から逆算すると、当社への入荷は9月上旬までに必要である。最安値の業者は納期が{x["v"][lo][2]}であり間に合わない。'
        f'選定業者は{x["v"][x["sel"]][2]}で納入可能であるため、価格差を考慮しても選定が妥当と判断した。', 'k_text', n=36, w1=36)
    g.t(12, 148, '※ 最安値以外の業者を選定する場合は、本書により購買部長の承認を得ること（購買管理規程 第8条）。', 8)
    return g.save()


def po_doc(path, DT, o, seed, note=None):
    g = Pg(path, seed=seed)
    sup = DT['S'][o['s']]
    a = amt(o)
    g.t(12, 12, 'AOBA-PROC 発注管理 [P0210]', 7.5)
    g.t(105, 22, '注 文 書（控）', 16, 'B', al='c')
    g.lv(12, 32, 26, 44, 9, '発注番号', o['no'], 11, key='k_no', f='B')
    g.lv(12, 41, 26, 44, 9, '発注日', sd(o['od']), 11, key='k_date')
    g.lv(12, 50, 26, 44, 9, '依頼部署', o['dept'])
    g.appr(118, 30, [('起票', DS(g, o['by'], o['od']), 'k_st_rep', dsd(o['by'], o['od'])), ('購買課長', DS(g, KA, o['od']), 'k_st_ka', dsd(KA, o['od'])),
                     ('購買部長', DS(g, BU, o['od']) if a >= 1_000_000 else 'slash', 'k_st_bu', dsd(BU, o['od']) if a >= 1_000_000 else '斜線'),
                     ('担当役員', DS(g, YK, o['od']) if a >= 10_000_000 else 'slash', 'k_st_yk', dsd(YK, o['od']) if a >= 10_000_000 else '斜線')])
    g.lv(12, 62, 26, 160, 9, '仕入先', f'{sup["code"]}　{sup["name"]}　御中', 10.5, key='k_sup')
    rows, keys = irows(o['lines'], 4)
    y = g.tbl(12, 77, ICOLS, rows, 8.5, 10, keys=keys)
    y = totals(g, y, a)
    g.lv(12, y + 6, 26, 67, 9, '納期', sd(o['recs'][0][0]), key='k_due')
    g.lv(105, y + 6, 26, 67, 9, '支払条件', sup['terms'], 9)
    g.lv(12, y + 15, 26, 160, 9, '納入場所', '当社 物流センター（東京都大田区東糀谷九丁目88番1号）', 9.5, key='x_place')
    big(g, y + 24, 18, '備考', note if note is not None else (o['note'] or '納品書に当社発注番号を記載のこと。'), 'x_note', w1=26)
    g.t(12, y + 52, '※ 承認区分（税抜）：100万円未満 購買課長、100万円以上1,000万円未満 購買部長、1,000万円以上 担当役員（職務権限規程 別表1）。', 8)
    return g.save()


# ================= C3 発注一覧の月次レビュー =================
def review_book(path, DT, months, seed):
    g = Pg(path, seed=seed)
    for n, r in enumerate(months):
        if n:
            g.newpage()
        m = r['m']
        hit = r['hit']
        g.t(12, 12, '様式 購-021', 7.5)
        g.t(105, 23, f'発注一覧 月次レビュー記録（{r["y"]}年{m}月分）', 14.5, 'B', al='c')
        who(g, ['購買部 購買課', f'実施日　{jd(r["ok"])}'])
        g.appr(152, 30, [('実施（購買課長）', DS(g, KA, r['ok']), f'k{m}_st_ka', dsd(KA, r['ok'])),
                         ('報告（購買部長）', DS(g, BU, hit['bu']) if hit and hit['bu'] else 'slash', f'k{m}_st_bu', dsd(BU, hit['bu']) if hit and hit['bu'] else '斜線')],
               w=23, h=22)
        g.lv(12, 64, 40, 53, 9, '当月の発注件数', f'{yen(r["n"])} 件', 11, key=f'k{m}_n')
        g.lv(105, 64, 40, 53, 9, '発注金額合計（税抜）', f'{yen(r["total"])} 円', 10.5, key=f'k{m}_total')
        big(g, 73, 22, '抽出条件', '同一の仕入先・品番・依頼部署で、発注日が連続する3営業日以内にあり、各発注が100万円未満、合計が100万円以上となる発注の組。',
            None, n=36, w1=40)
        txt = 'なし' if not hit else f'1組（{"、".join(o["no"] for o in hit["g"])}）　合計 {yen(sum(amt(o) for o in hit["g"]))} 円'
        g.lv(12, 95, 40, 146, 10, '該当する組', txt, 10.5, key=f'k{m}_hit', f='B')
        big(g, 105, 28, '確認結果・対応', hit['txt'] if hit else '該当なしのため、対応不要。', f'k{m}_txt', n=36, w1=40)
        g.t(12, 144, '※ 購買課長は、翌月5営業日以内に当月の発注一覧を上記の条件で抽出し、該当があれば内容を確認する。分割発注と', 8)
        g.t(12, 149, '　 認められる場合は購買部長へ報告し、承認を得る（購買管理規程 第9条）。', 8)
        g.t(105, 285, f'- {n + 1} -', 8, al='c')
    return g.save()


# ================= C4 検収・請求・支払依頼 =================
def grn(path, DT, o, k, seed, note='外観・数量とも異常なし。'):
    g = Pg(path, seed=seed)
    sup = DT['S'][o['s']]
    rd, qs = o['recs'][k]
    g.t(12, 12, 'AOBA-PROC 検収管理 [P0310]', 7.5)
    g.t(105, 22, '検 収 報 告 書', 16, 'B', al='c')
    g.lv(12, 32, 26, 44, 9, '検収番号', o['sino'][k], 11, key='k_no', f='B')
    g.lv(12, 41, 26, 44, 9, '検収日', sd(rd), 11, key='k_date', f='B')
    g.lv(12, 50, 26, 44, 9, '発注番号', o['no'], 10.5, key='k_po')
    g.appr(152, 30, [('検収者', DS(g, o['insp'][k], rd), 'k_st_insp', dsd(o['insp'][k], rd)), ('物流課長', DS(g, '相馬', rd), 'k_st_ka', dsd('相馬', rd))], w=23, h=22)
    g.lv(12, 62, 26, 160, 9, '仕入先', f'{sup["code"]}　{sup["name"]}', 10.5, key='k_sup')
    cols = [('No', 8, 'c'), ('品番', 30, 'l'), ('品名', 56, 'l'), ('発注数量', 22, 'r'), ('今回検収数量', 26, 'r'), ('累計検収数量', 26, 'r'), ('合否', 18, 'c')]
    rows, keys = [], {}
    for i, (p, q, c) in enumerate(o['lines']):
        qq = qs[i] if qs else q
        cum = sum((r[1][i] if r[1] else q) for r in o['recs'][:k + 1])
        rows.append([i + 1, PROD[p][0], PROD[p][1], yen(q), yen(qq), yen(cum), '合格'])
        keys.update({(i, 1): f'k_code{i + 1}', (i, 3): f'k_ord{i + 1}', (i, 4): f'k_qty{i + 1}'})
    while len(rows) < 4:
        rows.append([''] * 7)
    y = g.tbl(12, 77, cols, rows, 9, 10.5, keys=keys, hsz=8.5)
    g.lv(12, y + 6, 26, 67, 9, '納品書番号', f'DN-{seed * 37 % 9000 + 1000}', key='x_dn')
    g.lv(105, y + 6, 26, 67, 9, '入荷場所', '物流センター 1番バース', key='x_place')
    big(g, y + 15, 18, '検収所見', note, 'x_note', w1=26)
    g.t(12, y + 42, '※ 検収は、発注担当者以外の物流課員が、注文書（控）と現品・納品書を照合して行う（購買管理規程 第11条）。', 8)
    return g.save()


def invoice(path, DT, o, lines, idate, seed, style='A'):
    g = Pg(path, seed=seed)
    sup = DT['S'][o['s']]
    f = 'G' if style == 'A' else 'M'
    sub = sum(q * c for _, q, c in lines)
    ino = f'{sup["code"][1:]}-{idate.strftime("%y%m")}-{seed % 900 + 100}'
    g.t(105, 25, '請　求　書' if style == 'A' else 'ご 請 求 書', 18, 'B' if f == 'G' else 'M', al='c')
    g.t(198, 36, f'請求書番号　{ino}', 10, f, key='k_no', al='r')
    g.t(198, 42, f'請求日　{sd(idate) if style == "A" else wd(idate)}', 10, f, key='k_date', al='r')
    g.t(14, 44, f'{CO["name"]}　御中', 12.5, 'B' if f == 'G' else 'M')
    g.ln(14, 46, 100, 46, 0.8)
    vend(g, sup, 118, 56, f)
    g.t(14, 74, '下記のとおりご請求申し上げます。', 10, f)
    g.rc(14, 79, 96, 12, 0.9)
    g.t(17, 87, 'ご請求金額（税込）', 10, f)
    g.t(107, 87.5, f'￥{yen(int(sub * 1.1))}', 14, 'B', key='k_total', al='r')
    cols = [('納品日', 22, 'c'), ('貴社注文番号', 30, 'c'), ('品番・品名', 62, 'l'), ('数量', 18, 'r'), ('単価', 22, 'r'), ('金額', 32, 'r')]
    rows, keys = [], {}
    for i, (p, q, c) in enumerate(lines):
        rows.append([md(o['recs'][0][0]), o['no'], f'{PROD[p][0]} {PROD[p][1].split(" ")[0]}', yen(q), yen(c), yen(q * c)])
        keys.update({(i, 1): f'k_po{i + 1}', (i, 3): f'k_qty{i + 1}', (i, 4): f'k_price{i + 1}', (i, 5): f'k_amt{i + 1}'})
    while len(rows) < 4:
        rows.append([''] * 6)
    y = g.tbl(12, 97, cols, rows, 9, 10, f, keys=keys)
    y = totals(g, y, sub, ('k_sub', 'k_tax', 'k_gt'), ('小計（税抜）', '消費税（10%）', 'ご請求金額（税込）'))
    a = sup['acct']
    big(g, y + 8, 22, 'お振込先', f'{a["bank"]} {a["br"]}　{a["kind"]} {a["no"]}　口座名義 {hankaku(sup["kana"])}。振込手数料は貴社にてご負担願います。', 'x_bank', f=f)
    g.t(14, y + 40, f'お支払期限：{sup["terms"]}', 9.5, f, key='x_term')
    return g.save(), ino


def pay_req(path, DT, o, ino, lines, x, seed, sik=0, who_='立花'):
    g = Pg(path, seed=seed)
    sup = DT['S'][o['s']]
    sub = sum(q * c for _, q, c in lines)
    due = x.get('pay') or D(x['chk'].year, x['chk'].month, 28)
    hdr(g, '請求書照合票 兼 支払依頼書', '様式 経-031')
    who(g, ['経理課', (f'照合日　{jd(x["chk"])}', 'k_date')])
    ad = x.get('app', x['chk'])
    g.appr(152, 30, [('照合（経理担当）', DS(g, who_, x['chk']), 'k_st_chk', dsd(who_, x['chk'])), ('承認（経理課長）', DS(g, '溝口', ad), 'k_st_app', dsd('溝口', ad))], w=23, h=22)
    y = 64
    g.lv(12, y, 34, 152, 9, '仕入先', f'{sup["code"]}　{sup["name"]}', key='k_sup')
    g.lv(12, y + 9, 34, 59, 9, '請求書番号', ino, key='k_inv')
    g.lv(105, y + 9, 34, 59, 10, '請求金額（税込）', f'{yen(int(sub * 1.1))} 円', 11.5, key='k_total', f='B')
    g.lv(12, y + 19, 34, 59, 9, '発注番号', o['no'], key='k_po')
    g.lv(105, y + 19, 34, 59, 9, '検収番号', o['sino'][sik], key='k_si')
    g.lv(12, y + 28, 34, 152, 9, '照合結果（数量）', '■ 請求数量は検収数量の範囲内　　□ 差異あり（支払保留）', key='k_cq')
    g.lv(12, y + 37, 34, 152, 9, '照合結果（単価）', '■ 発注単価（変更後を含む）と一致　□ 差異あり（支払保留）', key='k_cp')
    big(g, y + 46, 20, '差異・特記事項', x['diff'], 'k_diff', w1=34)
    g.lv(12, y + 66, 34, 59, 9, '計上額（税抜）', f'{yen(sub)} 円', key='k_sub')
    g.lv(105, y + 66, 34, 59, 9, '支払予定日', sd(due), key='k_due')
    g.t(12, y + 86, '※ 経理担当は、請求書を注文書（控）・検収報告書と照合する（3点照合）。請求数量が検収数量を超える場合、または単価が', 8)
    g.t(12, y + 91, '　 発注単価と異なる場合は支払を保留する。経理課長は照合結果を確認して承認する（購買管理規程 第12条）。', 8)
    return g.save()


def po_change(path, DT, x, seed):
    g = Pg(path, seed=seed)
    o = x['o']
    sup = DT['S'][o['s']]
    p, q, c = o['lines'][0]
    hdr(g, '注 文 変 更 書', '様式 購-012', f'変更番号　HK-{x["chg"].strftime("%y%m")}-07')
    who(g, [(f'変更日　　{jd(x["chg"])}', 'k_date'), '作成部署　購買部 購買課', f'起票者　　{pf(o["by"])}'])
    g.appr(152, 30, [('起票', DS(g, o['by'], x['chg']), 'k_st_rep', dsd(o['by'], x['chg'])), ('購買課長', DS(g, KA, x['chg']), 'k_st_ka', dsd(KA, x['chg']))], w=23, h=22)
    g.lv(12, 64, 30, 63, 9, '対象の発注番号', o['no'], 10.5, key='k_po', f='B')
    g.lv(105, 64, 30, 63, 9, '発注日', sd(o['od']))
    g.lv(12, 73, 30, 156, 9, '仕入先', f'{sup["code"]}　{sup["name"]}', key='k_sup')
    g.lv(12, 82, 30, 156, 9, '品番・品名', f'{PROD[p][0]}　{PROD[p][1]}　{q}{PROD[p][2]}')
    y = g.tbl(12, 97, [('変更項目', 46, 'c'), ('変更前', 70, 'c'), ('変更後', 70, 'c')],
              [['単価（税抜）', f'{yen(x["old"])} 円', f'{yen(c)} 円'], ['発注金額（税抜）', f'{yen(x["old"] * q)} 円', f'{yen(c * q)} 円']], 10, 11,
              keys={(0, 1): 'k_old', (0, 2): 'k_new', (1, 2): 'k_newamt'})
    big(g, y + 6, 22, '変更理由', '原材料価格の高騰に伴い、仕入先から価格改定の申入れがあったため（改定通知 10/10付）。数量・納期の変更はない。', 'x_reason')
    g.t(12, y + 40, '※ 発注後に単価・数量を変更する場合は、本書により購買課長（変更後の金額が100万円以上の場合は購買部長）の承認を得る。', 8)
    return g.save()


# ================= C5 支払 =================
def pay_plan(path, DT, b, seed):
    g = Pg(path, land=True, seed=seed)
    S = DT['S']
    g.t(14, 16, f'支払予定表（{jd(b["pd"])} 支払分）', 15, 'B')
    g.t(14, 24, f'経理課　作成日 {sd(b["made"])}　　対象：20日締め・翌月10日払いの仕入先（{sd(b["lo"])}〜{sd(b["hi"])} 検収分）', 9.5)
    g.appr(214, 6, [('作成', DS(g, b['by'], b['made']), 'k_st_made', dsd(b['by'], b['made'])), ('承認（経理課長）', DS(g, '溝口', b['ok']), 'k_st_ok', dsd('溝口', b['ok'])),
                    ('FB送信', DS(g, b['sender'], b['sent']), 'k_st_sent', dsd(b['sender'], b['sent']))], w=23, h=21)
    cols = [('No', 8, 'c'), ('コード', 14, 'c'), ('仕入先名', 56, 'l'), ('請求額（税込）', 28, 'r'), ('相殺額', 20, 'r'), ('支払額', 28, 'r'),
            ('振込先（銀行・支店）', 60, 'l'), ('種別', 12, 'c'), ('口座番号', 22, 'c'), ('備考', 21, 'l')]
    rows, keys = [], {}
    for i, r in enumerate(b['rows']):
        s = S[r['s']]
        rows.append([i + 1, s['code'], s['name'], yen(r['bill']), yen(r['off']) if r['off'] else '-', yen(r['pay']), f'{s["acct"]["bank"]} {s["acct"]["br"]}',
                     s['acct']['kind'], s['acct']['no'], '返品相殺' if r['off'] else ''])
        if i in (0, 5, len(b['rows']) - 1) or r['off']:
            keys.update({(i, 3): f'k_bill{i}', (i, 5): f'k_pay{i}', (i, 8): f'k_acct{i}'})
        if r['off']:
            keys[(i, 4)] = f'k_off{i}'
    y = g.tbl(14, 38, cols, rows, 8.2, 9, keys=keys, hh=7, hsz=8.5)
    g.rc(14, y, 78, 9, fill=(0.9, 0.9, 0.9))
    g.t(53, y + 6, f'合　計（{len(rows)} 件）', 9.5, al='c')
    cx = 92
    for v, w, k in [(sum(r['bill'] for r in b['rows']), 28, 'k_tbill'), (sum(r['off'] for r in b['rows']), 20, 'k_toff'), (sum(r['pay'] for r in b['rows']), 28, 'k_total')]:
        g.rc(cx, y, w, 9)
        g.t(cx + w - 1.5, y + 6, yen(v), 9.5, 'B', key=k, al='r')
        cx += w
    g.rc(cx, y, 115, 9)
    g.t(14, y + 17, '※ 支払額＝請求額－相殺額。振込先は仕入先マスタから自動で表示される。経理課長は請求書照合票と照合して承認し、FB送信は承認者以外が行う。', 8)
    return g.save()


def fb_result(path, DT, title, pd, rows, seed, sent=None, note=''):
    g = Pg(path, seed=seed)
    S = DT['S']
    g.t(14, 16, BANK, 13, 'M')
    g.t(196, 16, '法人インターネットバンキング', 8.5, 'M', al='r')
    g.ln(14, 18.5, 196, 18.5, 0.9)
    g.t(105, 28, title, 14, 'B', al='c')
    sent = sent or add_bd(pd, -2)
    g.t(14, 38, f'受付番号：{pd.strftime("%y%m%d")}-{seed * 7919 % 90000 + 10000}', 9.5, key='x_rno')
    g.t(14, 44, f'依頼人名：ｱｵﾊﾞｷｺｳﾊﾝﾊﾞｲ(ｶ　　引落口座：普通 ＊＊＊4417', 9.5)
    g.t(196, 38, f'受付日時：{sd(sent)} 14:{seed % 50 + 10}', 9, al='r')
    g.lv(14, 49, 28, 36, 9, '振込指定日', sd(pd), 11, key='k_pd', f='B')
    g.lv(80, 49, 20, 22, 9, '件数', f'{len(rows)} 件', 11, key='k_cnt', f='B')
    g.lv(124, 49, 26, 46, 9, '合計金額', f'{yen(sum(r[1] for r in rows))} 円', 11, key='k_total', f='B')
    cols = [('No', 8, 'c'), ('受取人名', 56, 'l'), ('銀行名', 40, 'l'), ('支店名', 28, 'l'), ('種別', 12, 'c'), ('口座番号', 20, 'c'), ('金額', 22, 'r')]
    tr, keys = [], {}
    for i, (s, v) in enumerate(rows):
        a = S[s]['acct']
        tr.append([i + 1, hankaku(S[s]['kana']), a['bank'], a['br'], a['kind'], a['no'], yen(v)])
        if i in (0, 5, len(rows) - 1):
            keys.update({(i, 6): f'k_amt{i}', (i, 5): f'k_acct{i}'})
    y = g.tbl(12, 64, cols, tr, 8, 9.5, keys=keys)
    g.t(14, y + 9, note or 'データ作成：KEI002（宮下）　承認：KEI001（溝口）　状態：受付済み', 9, key='x_ops')
    g.t(14, 277, 'この画面はインターネットバンキングの照会結果を印刷したものです。', 8, 'M')
    g.t(14, 282, 'ひかり中央銀行 芝浦支店　東京都港区芝浦九丁目97番1号　TEL 03-0155-7000', 8, 'M', key='x_foot')
    return g.save()
