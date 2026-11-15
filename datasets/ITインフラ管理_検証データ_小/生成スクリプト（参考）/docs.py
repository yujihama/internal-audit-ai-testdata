# -*- coding: utf-8 -*-
"""証跡の原本（読みやすい版）の様式"""
from common import *
from render import *

SEC = {'佐野': '営業1課', '森下': '営業1課', '小田': '営業1課', '岡部': '営業1課', '河合': '営業2課', '堀': '営業2課',
       '西川': '営業2課', '榊原': '営業部', '氷室': '役員', '立花': '経理課', '宮下': '経理課', '溝口': '経理課',
       '桑原': '経理部', '矢野': '物流課', '北村': '物流課'}
ICOLS = [('No', 8, 'c'), ('品番', 30, 'l'), ('品名', 62, 'l'), ('数量', 18, 'r'), ('単位', 12, 'c'), ('単価', 24, 'r'),
         ('金額', 32, 'r')]


def DS(g, name, date, q=None, col=RED):
    return dstamp(SEC[name], st(date), name, g.nrng, q if q is not None else g.rng.uniform(0.86, 0.98), col)


def SL(g, name, q=None):
    return seal(name, g.nrng, q if q is not None else g.rng.uniform(0.86, 0.98))


def dsd(name, date):
    return f'日付印 {name} {st(date)}'


def ol(o):
    return [(PROD[p][0], q, pr) for p, q, pr in o['lines']]


def item_rows(lines, n_min=5):
    rows, keys = [], {}
    for i, (code, q, pr) in enumerate(lines):
        p = PROD[PIDX[code]]
        rows.append([i + 1, code, p[1], yen(q), p[2], yen(pr), yen(q * pr)])
        keys.update({(i, 1): f'k_code{i + 1}', (i, 3): f'k_qty{i + 1}', (i, 5): f'k_price{i + 1}', (i, 6): f'k_amt{i + 1}'})
    while len(rows) < n_min:
        rows.append([''] * 7)
    return rows, keys


def co_block(g, x, y, sz=9):
    g.t(x, y, CO['name'], sz + 2, 'B')
    g.t(x, y + 5, f'{CO["zip"]} {CO["addr"]}', sz - 1.5)
    g.t(x, y + 9, f'TEL {CO["tel"]}　FAX {CO["fax"]}', sz - 1.5)


# ---------- C1 与信 ----------
def credit_app(path, DT, x, seed, hand=False):
    g = Pg(path, seed=seed)
    cu = DT['C'][x['c']]
    ka = KA[cu['sec']]
    g.t(12, 12, '様式 営-012（2024.4改訂）', 7.5)
    g.t(198, 12, f'申請番号　{x["no"]}', 9.5, key='k_no', al='r')
    g.t(105, 23, '与信限度額 設定・変更申請書', 16, 'B', al='c')
    g.t(12, 37, f'申請日　　{jd(x["app"])}', 10, key='k_appdate')
    g.t(12, 44, f'申請部署　営業部 {cu["sec"]}', 10)
    g.t(12, 51, f'起案者　　{full(cu["rep"])}', 10)
    by = x.get('bu_by', BU)
    bu = (DS(g, by, x['bu']), dsd(by, x['bu']) + ('（代）' if x.get('bu_by') else '')) if x['bu'] else ('slash', '斜線')
    yk = (DS(g, YK, x['yk']), dsd(YK, x['yk'])) if x['yk'] else ('slash', '斜線')
    g.appr(98, 30, [('起案', SL(g, cu['rep']), 'k_st_rep', f'印 {cu["rep"]}'),
                    ('所属長', DS(g, ka, x['ka']), 'k_st_ka', dsd(ka, x['ka'])),
                    ('営業部長', bu[0], 'k_st_bu', bu[1]), ('担当役員', yk[0], 'k_st_yk', yk[1]),
                    ('経理確認', DS(g, KRK, x['kr']), 'k_st_kr', dsd(KRK, x['kr']))])
    if x.get('bu_by'):
        g.hw(138.6, 40.2, '代', 13, 'K', col=(0.75, 0.1, 0.12))
    y = 62
    g.lv(12, y, 28, 65, 9, '取引先コード', cu['code'], hand=hand)
    g.lv(105, y, 28, 65, 9, '区分', x['kind'], hand=hand)
    g.lv(12, y + 9, 28, 158, 9, '取引先名', cu['name'], 11, key='k_cust', hand=hand)
    g.lv(12, y + 18, 28, 158, 9, '所在地', f'{cu["zip"]} {cu["addr"]}', key='x_addr', hand=hand)
    g.lv(12, y + 27, 28, 65, 9, '業種', cu['ind'], hand=hand)
    g.lv(105, y + 27, 28, 65, 9, '代表者', cu['ceo'], hand=hand)
    g.lv(12, y + 36, 28, 65, 10, '現行限度額', f'{yen(x["cur"])} 円', 11, hand=hand)
    g.lv(105, y + 36, 28, 65, 10, '申請限度額', f'{yen(x["req"])} 円', 12, key='k_amount', f='B', hand=hand)
    g.lv(12, y + 46, 28, 65, 9, '支払条件', '月末締め 翌月末日 振込')
    g.lv(105, y + 46, 28, 65, 9, '月間取引見込額', f'{yen(x["monthly"])} 円', hand=hand)
    g.lv(12, y + 55, 28, 158, 9, '信用調査', f'評点 {x["score"]} 点（{AGENCY}　{sd(x["rd"])} 調査）', key='k_score',
         hand=hand)
    g.rc(12, y + 64, 28, 34, fill=(0.93, 0.93, 0.93))
    g.t(13.5, y + 82, '申請理由', 8.5)
    g.rc(40, y + 64, 158, 34)
    g.para(43, y + 72, x['reason'], 39 if not hand else 30, 10, 'G', hand=hand)
    g.box('x_reason', 41, y + 65, 156, 32, '申請理由（判定に無関係）')
    g.lv(12, y + 98, 28, 158, 9, '添付書類', '■ 信用調査報告書　□ 決算書（直近2期）　□ 登記事項証明書　□ その他')
    g.t(12, y + 115, '※ 決裁区分は職務権限規程 別表1による。決裁が不要な欄には斜線を引くこと。', 8)
    g.t(12, y + 120, '※ 決裁後、経理課が取引先マスタへ限度額を登録する。登録は決裁完了後に行うこと。', 8)
    g.t(105, 285, CO['name'], 7.5, al='c')
    return g.save()


def credit_report(path, DT, x, seed):
    g = Pg(path, seed=seed)
    cu = DT['C'][x['c']]
    g.t(14, 16, AGENCY, 13, 'M')
    g.ln(14, 18.5, 196, 18.5, 1.0)
    g.t(196, 25, f'報告書番号　{x["rno"]}', 9.5, 'M', key='k_rno', al='r')
    g.t(196, 31, f'調査年月日　{jd(x["rd"])}', 9.5, 'M', key='k_rdate', al='r')
    g.t(105, 42, '企業信用調査報告書（要約版）', 16, 'M', al='c')
    g.t(14, 53, f'ご依頼主：{CO["name"]}　御中', 10.5, 'M')
    y = 60
    est = x['rd'].year - g.rng.randint(12, 55)
    rows = [('商号', cu['name'], 'k_cust'), ('所在地', f'{cu["zip"]} {cu["addr"]}', 'x_addr'), ('代表者', cu['ceo'], None),
            ('設立', f'{est}年{g.rng.randint(1, 12)}月', None), ('資本金', f'{yen(cu["cap"])}万円', 'x_cap'),
            ('従業員数', f'{cu["emp"]}名', None), ('業種', cu['ind'], None),
            ('年商（直近期）', f'{yen(cu["emp"] * g.rng.randint(22, 38))}百万円', None),
            ('主要取引銀行', f'ひかり中央銀行、{cu["addr"][:3]}みらい信用金庫', 'x_bank')]
    for i, (a, b, k) in enumerate(rows):
        g.lv(14, y + i * 8.5, 34, 148, 8.5, a, b, 10, key=k, f='M')
    y = y + len(rows) * 8.5 + 8
    g.rc(14, y, 60, 34, 0.8)
    g.t(44, y + 8, '総 合 評 点', 11, 'M', al='c')
    g.t(44, y + 25, str(x['score']), 34, 'M', key='k_score', al='c')
    g.t(62, y + 26, '点', 11, 'M')
    grade = 'B（やや良好）' if x['score'] >= 66 else ('C（普通）' if x['score'] >= 50 else 'D（要注意）')
    g.t(82, y + 9, f'信用程度：{grade}', 12, 'M', key='k_grade')
    g.t(82, y + 17, '評点の目安　86点以上 A（優良）／66〜85点 B（やや良好）／', 8.5, 'M')
    g.t(82, y + 22, '　　　　　　50〜65点 C（普通）／36〜49点 D（要注意）／35点以下 E（警戒）', 8.5, 'M')
    g.t(82, y + 30, '※ 評点は財務内容、支払状況、業歴、経営者、成長性等を総合的に評価したものです。', 8, 'M')
    y += 42
    g.t(14, y, '所　見', 11.5, 'M')
    g.ln(14, y + 2, 196, y + 2)
    note = (f'同社は{cu["ind"]}を主業とし、地場の中堅メーカー向けに安定した受注基盤を有する。'
            f'直近期は{"増収増益" if x["score"] >= 55 else "減収ながら黒字を確保"}。'
            f'{"借入依存度はやや高いが、取引銀行の支援姿勢に変化はみられない。" if x["score"] < 60 else "自己資本比率は業界平均を上回り、資金繰りに懸念はない。"}'
            f'支払振りは{"概ね良好" if x["score"] >= 52 else "一部に遅延の風評があり、取引条件の設定には留意を要する"}。'
            '主要仕入先との関係は良好で、代表者の業界経験も長い。今後は設備投資の回収状況と受注動向を注視する必要がある。')
    y2 = g.para(14, y + 9, note, 50, 10, 'M')
    g.box('x_note', 13, y + 3, 184, y2 - y - 2, '所見（判定に無関係）')
    g.ln(14, 272, 196, 272)
    g.t(14, 277, '本報告書は依頼主限りの資料であり、第三者への開示・複製を禁じます。', 8, 'M')
    g.t(14, 282, f'{AGENCY}　東京都千代田区神田東松下町98-7　TEL 03-0122-4400', 8, 'M', key='x_foot')
    return g.save()


def delegation(path, DT, seed):
    g = Pg(path, seed=seed)
    dl = DT['DELEG']
    g.t(12, 12, '様式 総-031', 7.5)
    g.t(105, 30, '決裁権限 委任届', 17, 'B', al='c')
    g.t(198, 44, f'届出日　{jd(dl["filed"])}', 10, key='k_filed', al='r')
    g.t(14, 56, '職務権限規程 第8条に基づき、下記のとおり決裁権限を委任します。', 10)
    rows = [('委任者', f'営業部長　{full(dl["frm"])}', 'k_from'), ('受任者', f'営業2課長　{full(dl["to"])}', 'k_to'),
            ('委任期間', f'{jd(dl["a"])} 〜 {jd(dl["b"])}', 'k_period'),
            ('委任する権限', '営業部長の決裁権限のうち、与信限度額の設定・変更', None),
            ('', '（3,000万円以下）および値引承認（15%超）', None), ('委任理由', dl['reason'], None)]
    for i, (a, b, k) in enumerate(rows):
        g.lv(14, 66 + i * 11, 36, 146, 11, a, b, 10.5, key=k)
    g.appr(118, 144, [('委任者', SL(g, dl['frm']), 'k_st_from', f'印 {dl["frm"]}'),
                      ('受任者', SL(g, dl['to']), 'k_st_to', f'印 {dl["to"]}'),
                      ('承認（担当役員）', DS(g, YK, dl['ok']), 'k_st_ok', dsd(YK, dl['ok']))], w=26)
    g.t(14, 182, '※ 委任期間中に受任者が決裁する場合は、決裁欄に「代」と記載のうえ押印すること。', 8.5)
    g.t(14, 187, '※ 本届は総務部で保管し、写しを経理課へ回付する。', 8.5)
    return g.save()


# ---------- C2 注文書・受注伝票 ----------
def po(path, DT, x, seed, lines=None, rev=None):
    cu = DT['C'][x['o']['c']]
    lines = lines or x['po_lines']
    style = x['style']
    g = Pg(path, seed=seed)
    tot = sum(q * pr for _, q, pr in lines)
    pod = rev or x['pod']
    seal_txt = cu['short'] + '株式会社'
    if style == 'A':
        g.t(105, 25, '注　文　書', 19, 'B', al='c')
        g.t(198, 36, f'注文番号：{x["pono"]}' + ('（訂正1）' if rev else ''), 10, key='k_pono', al='r')
        g.t(198, 42, f'発注日：{wd(pod)}', 10, key='k_pod', al='r')
        g.t(14, 44, f'{CO["name"]}　御中', 13, 'B')
        g.ln(14, 46, 100, 46, 0.8)
        g.t(118, 54, cu['name'], 11.5, 'B', key='k_cust')
        g.t(118, 60, f'{cu["zip"]} {cu["addr"]}', 8.5, key='x_addr')
        g.t(118, 65, f'TEL {cu["tel"]}　資材課　担当：{cu["pic"]}', 8.5)
        g.im(sqseal(seal_txt, g.nrng), 176, 46, 20, 20)
        g.t(14, 76, '下記のとおり注文いたします。', 10)
        g.rc(14, 80, 90, 11, 0.8)
        g.t(17, 87.5, '合計金額（税込）', 10)
        g.t(101, 87.5, f'￥{yen(int(tot * 1.1))}－', 13, 'B', key='k_total_tax', al='r')
        rows, keys = item_rows(lines, 6)
        y = g.tbl(12, 97, ICOLS, rows, 8, 10, keys=keys)
        for i, (a, b, k) in enumerate([('小計', tot, 'k_total'), ('消費税（10%）', int(tot * 0.1), None),
                                       ('合計', int(tot * 1.1), None)]):
            g.lv(118, y + i * 8, 48, 32, 8, a, '')
            g.t(196.5, y + i * 8 + 5.4, yen(b), 10, key=k, al='r')
        y += 30
        g.lv(12, y, 28, 158, 9, '希望納期', sd(x['due']), key='k_due')
        g.lv(12, y + 9, 28, 158, 9, '納入場所', f'{cu["addr"]}　本社工場 資材倉庫', 9, key='x_place')
        g.lv(12, y + 18, 28, 158, 9, '支払条件', '月末締め 翌月末日 銀行振込')
        g.rc(12, y + 27, 28, 24, fill=(0.93, 0.93, 0.93))
        g.t(13.5, y + 40, '備考', 8.5)
        g.rc(40, y + 27, 158, 24)
        note = ('納品時は注文番号を納品書に必ず記載してください。分納の場合は事前にご連絡ください。' if not rev else
                f'{md(x["pod"])}付 注文書の数量を訂正します（{x["po_lines"][0][1]}個 → {lines[0][1]}個）。先の注文書は破棄願います。')
        g.para(43, y + 34, note, 40, 9.5, 'G')
        g.box('x_note', 41, y + 28, 156, 22, '備考')
        if rev:
            g.im(tstamp('訂 正', g.nrng), 30, 14, 34, 13)
    elif style == 'B':
        g.t(18, 26, 'ご 注 文 書', 18, 'M')
        g.ln(14, 29, 196, 29, 1.2)
        g.t(196, 38, f'発注No.　{x["pono"]}', 10.5, 'M', key='k_pono', al='r')
        g.t(196, 44, f'発注日　{pod.year}.{pod.month}.{pod.day}', 10.5, 'M', key='k_pod', al='r')
        g.t(14, 42, '（注文先）', 9, 'M')
        g.t(14, 49, 'アオバ機工販売(株)　営業部 御中', 12, 'M')
        g.t(112, 58, '発注者', 9, 'M')
        g.t(126, 58, cu['name'], 11.5, 'M', key='k_cust')
        g.t(126, 64, cu['addr'], 9, 'M', key='x_addr')
        g.t(126, 69, f'電話 {cu["tel"]}　購買担当 {cu["pic"]}', 9, 'M')
        g.im(sqseal(seal_txt, g.nrng), 174, 50, 21, 21)
        g.t(14, 78, '毎度お世話になっております。下記の品目を発注いたしますので、ご手配のほどお願い申し上げます。', 9.5, 'M')
        cols = [('No.', 8, 'c'), ('品目コード', 30, 'l'), ('品目名・仕様', 56, 'l'), ('数量', 18, 'r'), ('単価(円)', 22, 'r'),
                ('金額(円)', 28, 'r'), ('希望納期', 24, 'c')]
        rows, keys = [], {}
        for i, (code, q, pr) in enumerate(lines):
            p = PROD[PIDX[code]]
            rows.append([i + 1, code, p[1], f'{yen(q)} {p[2]}', yen(pr), yen(q * pr), md(x['due'])])
            keys.update({(i, 1): f'k_code{i + 1}', (i, 3): f'k_qty{i + 1}', (i, 4): f'k_price{i + 1}', (i, 5): f'k_amt{i + 1}'})
        while len(rows) < 6:
            rows.append([''] * 7)
        y = g.tbl(12, 84, cols, rows, 9, 10, 'M', keys=keys, hfill=(1, 1, 1))
        g.t(140, y + 8, '合計（税抜）', 10.5, 'M')
        g.t(196, y + 8, f'{yen(tot)} 円', 12, 'M', key='k_total', al='r')
        g.ln(138, y + 10, 196, y + 10, 0.8)
        g.t(14, y + 22, '納 入 先：当社 第二工場 受入口（平日 9:00〜16:00）', 10, 'M', key='x_place')
        g.t(14, y + 29, '支払条件：月末締 翌月末 振込', 10, 'M')
        g.t(14, y + 38, '特記事項', 10, 'M')
        g.rc(14, y + 41, 182, 24)
        g.para(17, y + 48, '梱包は品目ごとに分け、現品票を貼付のこと。納期遅延が見込まれる場合は速やかに購買担当まで連絡願います。', 44, 9.5, 'M')
        g.box('x_note', 15, y + 42, 180, 22, '特記事項')
    else:  # C: 手書きの定型用紙
        g.t(105, 26, '注　文　書', 20, 'M', al='c')
        g.t(150, 38, 'No.', 10)
        g.hw(160, 38, x['pono'], 13, key='k_pono')
        g.ln(148, 40, 196, 40)
        g.hw(152, 48, f'{pod.year}年 {pod.month}月 {pod.day}日', 12, key='k_pod')
        g.hw(16, 50, 'アオバ機工販売', 15)
        g.t(74, 50, '御中', 12)
        g.ln(14, 52, 88, 52)
        g.t(110, 62, '（発注者）', 9)
        g.im(rstamp([cu['name'], cu['addr'], f'TEL {cu["tel"]}'], g.nrng, 0.9, BLUE, 620, 210, [50, 30, 30]), 116, 64, 62, 21)
        g.box('k_cust', 116, 64, 62, 21, cu['name'] + '（ゴム印）')
        g.im(sqseal(seal_txt, g.nrng), 176, 62, 19, 19)
        g.t(14, 92, '下記のとおり注文します。', 10)
        cols = [('品名・品番', 74, 'l'), ('数量', 22, 'r'), ('単価', 26, 'r'), ('金額', 32, 'r'), ('摘要', 32, 'l')]
        rows, keys = [], {}
        for i, (code, q, pr) in enumerate(lines):
            rows.append([f'{code} {PROD[PIDX[code]][1].split(" ")[0]}', f'{q}{PROD[PIDX[code]][2]}', yen(pr), yen(q * pr), ''])
            keys.update({(i, 0): f'k_code{i + 1}', (i, 1): f'k_qty{i + 1}', (i, 2): f'k_price{i + 1}', (i, 3): f'k_amt{i + 1}'})
        while len(rows) < 7:
            rows.append([''] * 5)
        y = g.tbl(12, 97, cols, rows, 11, 10, keys=keys, hand=True, hfill=(1, 1, 1))
        g.rc(12, y, 122, 11)
        g.t(73, y + 7.3, '合　計（税別）', 10, al='c')
        g.rc(134, y, 32, 11)
        g.rc(166, y, 32, 11)
        g.hw(141, y + 7.6, yen(tot), 13, key='k_total')
        g.t(14, y + 24, '納期', 10)
        g.hw(30, y + 24, f'{x["due"].month}/{x["due"].day} 必着', 13, key='k_due')
        g.ln(28, y + 26, 90, y + 26)
        g.t(100, y + 24, '納入場所', 10)
        g.hw(120, y + 24, '本社 第1工場', 13, key='x_place')
        g.ln(118, y + 26, 196, y + 26)
        g.t(14, y + 38, '備考', 10)
        g.rc(14, y + 41, 182, 26)
        g.hw(18, y + 51, '至急でお願いします。在庫ない場合はTEL下さい。', 12)
        g.hw(18, y + 61, f'担当 {cu["pic"]}', 12)
        g.box('x_note', 15, y + 42, 180, 24, '備考')
    return g.save()


def order_slip(path, DT, o, seed, pono='', note='', due=None):
    g = Pg(path, seed=seed)
    cu = DT['C'][o['c']]
    ka = KA[cu['sec']]
    g.t(105, 21, '受 注 伝 票', 16, 'B', al='c')
    g.t(12, 12, 'AOBA-SALES 受注管理 [J0110]', 7.5)
    g.t(198, 12, f'出力日時 {sd(o["od"])} {g.rng.randint(9, 17)}:{g.rng.randint(10, 59)}', 7.5, al='r')
    g.lv(12, 32, 30, 50, 9, '受注番号', o['jno'], 11, key='k_no', f='B')
    g.lv(12, 41, 30, 50, 9, '受注日', sd(o['od']), 11, key='k_date')
    g.lv(12, 50, 30, 100, 9, '取引先', f'{cu["code"]}　{cu["name"]}', key='k_cust')
    g.lv(12, 59, 30, 100, 9, '客先注文番号', pono or '（口頭・メール受注）', key='k_pono')
    g.lv(12, 68, 30, 40, 9, '納期', sd(due or add_bd(o['sd'], 1)))
    g.lv(82, 68, 22, 38, 9, '登録者', full(cu['rep']), key='k_reg')
    g.appr(152, 30, [('登録', DS(g, cu['rep'], o['od']), 'k_st_reg', dsd(cu['rep'], o['od'])),
                     ('承認（課長）', DS(g, ka, o['od']), 'k_st_app', dsd(ka, o['od']))], w=23, h=22)
    rows, keys = item_rows(ol(o), 5)
    y = g.tbl(12, 84, ICOLS, rows, 8, 10, keys=keys)
    tot = sum(q * pr for _, q, pr in o['lines'])
    for i, (a, b, k) in enumerate([('合計（税抜）', tot, 'k_total'), ('消費税（10%）', int(tot * 0.1), None),
                                   ('税込合計', int(tot * 1.1), None)]):
        g.lv(118, y + i * 8, 48, 32, 8, a, '')
        g.t(196.5, y + i * 8 + 5.4, yen(b), 10, key=k, al='r')
    y += 30
    g.rc(12, y, 30, 22, fill=(0.93, 0.93, 0.93))
    g.t(13.5, y + 12, '備考', 8.5)
    g.rc(42, y, 156, 22)
    g.para(45, y + 7, note or '納品書に客先注文番号を記載のこと。', 40, 9.5, 'G')
    g.box('x_note', 43, y + 1, 154, 20, '備考')
    g.t(12, y + 32, '※ 受注登録は、登録者以外の営業課長が注文書と照合のうえ承認する（販売管理規程 第9条）。', 8)
    g.t(105, 285, '1 / 1', 8, al='c')
    return g.save()


# ---------- C3 値引 ----------
def disc_app(path, DT, x, seed):
    g = Pg(path, seed=seed)
    o = x['o']
    cu = DT['C'][o['c']]
    ka = KA[cu['sec']]
    p, q, pr = o['lines'][0]
    g.t(12, 12, '様式 営-027', 7.5)
    g.t(198, 12, f'申請番号　{x["no"]}', 9.5, key='k_no', al='r')
    g.t(105, 23, '販売価格 値引申請書', 16, 'B', al='c')
    g.t(12, 37, f'申請日　　{jd(x["app"])}', 10, key='k_appdate')
    g.t(12, 44, f'申請部署　営業部 {cu["sec"]}', 10)
    g.t(12, 51, f'申請者　　{full(cu["rep"])}', 10)
    g.appr(129, 30, [('申請者', SL(g, cu['rep']), 'k_st_rep', f'印 {cu["rep"]}'),
                     ('営業課長', DS(g, ka, x['ka']) if x['ka'] else None, 'k_st_ka', dsd(ka, x['ka']) if x['ka'] else '（空欄）'),
                     ('営業部長', DS(g, BU, x['bu']) if x['bu'] else 'slash', 'k_st_bu', dsd(BU, x['bu']) if x['bu'] else '斜線')],
           w=23, h=22)
    y = 64
    g.lv(12, y, 30, 156, 9, '取引先', f'{cu["code"]}　{cu["name"]}', key='k_cust')
    g.lv(12, y + 9, 30, 156, 9, '品番・品名', f'{PROD[p][0]}　{PROD[p][1]}')
    g.lv(12, y + 18, 30, 63, 9, '数量', f'{yen(q)} {PROD[p][2]}')
    g.lv(105, y + 18, 30, 63, 9, '適用範囲', '今回受注分のみ')
    g.lv(12, y + 27, 30, 63, 10, '標準単価', f'{yen(x["std"])} 円', 11, key='k_std')
    g.lv(105, y + 27, 30, 63, 10, '申請単価', f'{yen(pr)} 円', 11, key='k_price', f='B')
    g.lv(12, y + 37, 30, 63, 10, '値引率', f'{x["rate"]:.1f} ％', 12, key='k_rate', f='B')
    g.lv(105, y + 37, 30, 63, 10, '値引総額', f'{yen((x["std"] - pr) * q)} 円', 11)
    g.rc(12, y + 47, 30, 28, fill=(0.93, 0.93, 0.93))
    g.t(13.5, y + 62, '申請理由', 8.5)
    g.rc(42, y + 47, 156, 28)
    g.para(45, y + 55, x['reason'], 38, 10, 'G')
    g.box('x_reason', 43, y + 48, 154, 26, '申請理由（判定に無関係）')
    g.rc(12, y + 75, 30, 20, fill=(0.93, 0.93, 0.93))
    g.t(13.5, y + 86, '競合・市況', 8.5)
    g.rc(42, y + 75, 156, 20)
    g.para(45, y + 83, f'競合品の提示価格は @{yen(int(pr * 0.985 // 10 * 10))} 円前後との情報あり（顧客購買担当より聴取）。', 38, 10, 'G')
    g.box('x_comp', 43, y + 76, 154, 18, '競合・市況')
    g.t(12, y + 104, '※ 値引率 5％超〜15％以内：営業課長の承認、15％超：営業部長の承認を要する（職務権限規程 別表1）。', 8)
    g.t(12, y + 109, '※ 承認は受注登録の前に得ること。5％以内は担当者の裁量とし、本申請は不要。', 8)
    return g.save()


# ---------- C4 / C8 出荷・受領 ----------
def ship_rec(path, DT, o, seed, note='', font='G'):
    g = Pg(path, seed=seed)
    cu = DT['C'][o['c']]
    who = ['矢野', '北村'][seed % 2]
    g.t(12, 12, 'AOBA-SALES 出荷管理 [S0310]', 7.5)
    g.t(105, 21, '出荷指示書 兼 出荷報告書', 15, 'B', al='c')
    g.lv(12, 32, 30, 52, 9, '出荷番号', o['sno'], 11, key='k_no', f='B')
    g.lv(12, 41, 30, 52, 9, '出荷指示日', sd(o['sid']), 11, key='k_sid', f=font)
    g.lv(12, 50, 30, 52, 9, '受注番号', o['jno'], 10, f=font)
    g.lv(12, 59, 30, 156, 9, '取引先', f'{cu["code"]}　{cu["name"]}', key='k_cust')
    g.lv(12, 68, 30, 156, 9, '納入先', f'{cu["zip"]} {cu["addr"]}', 9.5, key='x_addr')
    g.rc(104, 32, 94, 18, 0.9)
    g.t(107, 38, '出荷日（実績）', 9)
    g.t(151, 45.5, sd(o['sd']), 15, 'B', key='k_sd', al='c')
    cols = [('No', 8, 'c'), ('品番', 32, 'l'), ('品名', 70, 'l'), ('指示数量', 26, 'r'), ('出荷数量', 26, 'r'), ('単位', 24, 'c')]
    rows, keys = [], {}
    for i, (code, q, pr) in enumerate(ol(o)):
        pp = PROD[PIDX[code]]
        rows.append([i + 1, code, pp[1], yen(q), yen(q), pp[2]])
        keys.update({(i, 1): f'k_code{i + 1}', (i, 4): f'k_qty{i + 1}'})
    while len(rows) < 5:
        rows.append([''] * 6)
    y = g.tbl(12, 84, cols, rows, 8, 10, font, keys=keys)
    y += 6
    g.lv(12, y, 30, 40, 9, '個口数', f'{g.rng.randint(1, 6)} 個口')
    g.lv(12, y + 9, 30, 70, 9, '運送会社', CARRIER, key='x_carrier')
    g.lv(12, y + 18, 30, 70, 9, '送り状番号', f'{g.rng.randint(1000, 9999)}-{g.rng.randint(1000, 9999)}-{g.rng.randint(1000, 9999)}',
         key='x_slip', f=font)
    g.rc(12, y + 27, 30, 22, fill=(0.93, 0.93, 0.93))
    g.t(13.5, y + 39, '備考', 8.5)
    g.rc(42, y + 27, 70, 22)
    if note:
        g.para(44, y + 34, note, 17, 9.5, 'G')
    g.box('x_note', 43, y + 28, 68, 20, '備考')
    g.appr(122, y, [('出荷担当', DS(g, who, o['sd']), 'k_st_ship', dsd(who, o['sd']))], w=26, h=24)
    g.rc(152, y, 46, 5, fill=(0.93, 0.93, 0.93))
    g.t(175, y + 3.6, '運送会社 集荷印', 8, al='c')
    g.rc(152, y + 5, 46, 24)
    g.im(rstamp([CARRIER, f'集荷 {st(o["sd"])}', '芝浦営業所'], g.nrng, g.rng.uniform(0.86, 0.97), BLUE, 420, 250, [56, 66, 44]),
         158 + g.rng.uniform(-2, 2), y + 8 + g.rng.uniform(-1, 1), 33, 19.6)
    g.box('k_st_pick', 152, y + 5, 46, 24, f'集荷印 {st(o["sd"])}')
    g.t(12, y + 58, '※ 売上は出荷日（実績）をもって計上する（販売管理規程 第12条）。', 8)
    return g.save()


def receipt(path, DT, o, x, seed):
    g = Pg(path, seed=seed)
    cu = DT['C'][o['c']]
    g.t(105, 22, '物 品 受 領 書', 17, 'B', al='c')
    g.t(198, 33, f'納品書番号　{o["sno"]}', 10, key='k_no', al='r')
    g.t(198, 39, f'出荷日　{sd(o["sd"])}', 10, key='k_date', al='r')
    g.t(14, 40, f'{cu["name"]}　御中', 12.5, 'B', key='k_cust')
    g.ln(14, 42, 104, 42, 0.8)
    g.t(14, 48, f'{cu["zip"]} {cu["addr"]}', 8.5)
    co_block(g, 122, 52)
    g.t(14, 66, '下記のとおり納品いたしました。ご査収のうえ、受領印を押印して運送会社へお渡しください。', 9)
    cols = [('No', 8, 'c'), ('品番', 32, 'l'), ('品名', 72, 'l'), ('数量', 22, 'r'), ('単位', 14, 'c'), ('備考', 38, 'l')]
    rows, keys = [], {}
    for i, (code, q, pr) in enumerate(ol(o)):
        pp = PROD[PIDX[code]]
        rows.append([i + 1, code, pp[1], yen(q), pp[2], ''])
        keys.update({(i, 1): f'k_code{i + 1}', (i, 3): f'k_qty{i + 1}'})
    while len(rows) < 6:
        rows.append([''] * 6)
    y = g.tbl(12, 72, cols, rows, 9, 10.5, keys=keys)
    y += 8
    g.rc(12, y, 100, 6, fill=(0.93, 0.93, 0.93))
    g.t(14, y + 4.3, '備考・運送会社記入欄', 8.5)
    g.rc(12, y + 6, 100, 34)
    g.t(15, y + 14, f'運送会社：{CARRIER}', 9.5)
    g.t(15, y + 21, f'貴社注文番号：{g.rng.choice(["P", "K", "発"])}-{g.rng.randint(1000, 9999)}', 9.5)
    g.t(15, y + 28, f'受注番号：{o["jno"]}', 9.5)
    g.box('x_carrier', 13, y + 7, 98, 32, '備考・運送会社記入欄（判定に無関係）')
    g.rc(124, y, 74, 6, fill=(0.93, 0.93, 0.93))
    g.t(161, y + 4.3, '受領印（受領日・ご担当者名）', 8.5, al='c')
    g.rc(124, y + 6, 74, 34)
    if x['how'] == 'stamp':
        g.im(rstamp(['受　領', st(x['recv']), cu['short'][:6] + ' 資材課'], g.nrng, g.rng.uniform(0.86, 0.97), RED, 420, 270,
                    [62, 70, 40]), 142 + g.rng.uniform(-4, 4), y + 11 + g.rng.uniform(-2, 2), 38, 24.4)
        desc = f'受領印 {st(x["recv"])} {cu["short"]}'
    else:
        g.hw(130, y + 19, '受領しました', 15, 'Z')
        g.hw(132, y + 31, f'{x["recv"].month}/{x["recv"].day}　{cu["pic"]}', 17, 'Z')
        desc = f'手書き署名 {md(x["recv"])} {cu["pic"]}'
    g.box('k_recv', 124, y + 6, 74, 34, desc)
    g.t(12, y + 50, '（複写式 3枚目：物品受領書　当社控）', 8)
    return g.save()


# ---------- C5 返品・取消 ----------
def return_app(path, DT, r, seed):
    g = Pg(path, seed=seed)
    o = r['o']
    cu = DT['C'][o['c']]
    ka = KA[cu['sec']]
    who = ['矢野', '北村'][seed % 2]
    amt = r['q'] * r['pr']
    g.t(12, 12, '様式 営-033', 7.5)
    g.t(198, 12, f'返品番号　{r["hno"]}', 10, key='k_no', al='r')
    g.t(105, 23, '返品・売上取消 申請書', 16, 'B', al='c')
    g.t(12, 37, f'申請日　　{jd(r["app"])}', 10, key='k_appdate')
    g.t(12, 44, f'申請部署　営業部 {cu["sec"]}', 10)
    g.t(12, 51, f'申請者　　{full(cu["rep"])}', 10)
    g.appr(106, 30, [('申請者', SL(g, cu['rep']), 'k_st_rep', f'印 {cu["rep"]}'),
                     ('営業課長', DS(g, ka, r['ka']), 'k_st_ka', dsd(ka, r['ka'])),
                     ('営業部長', DS(g, BU, r['bu']) if r['bu'] else 'slash', 'k_st_bu', dsd(BU, r['bu']) if r['bu'] else '斜線'),
                     ('経理課長', DS(g, KRK, r['kr']), 'k_st_kr', dsd(KRK, r['kr']))], w=23, h=22)
    y = 64
    g.lv(12, y, 30, 156, 9, '取引先', f'{cu["code"]}　{cu["name"]}', key='k_cust')
    g.lv(12, y + 9, 30, 63, 9, '元売上番号', o['uno'], key='k_orig')
    g.lv(105, y + 9, 30, 63, 9, '元売上日', sd(o['ld']))
    g.lv(12, y + 18, 30, 156, 9, '品番・品名', f'{PROD[r["p"]][0]}　{PROD[r["p"]][1]}')
    g.lv(12, y + 27, 30, 63, 9, '返品数量', f'{yen(r["q"])} {PROD[r["p"]][2]}', key='k_qty')
    g.lv(105, y + 27, 30, 63, 9, '単価', f'{yen(r["pr"])} 円')
    g.lv(12, y + 36, 30, 63, 10, '返品金額（税抜）', f'{yen(amt)} 円', 12, key='k_amt', f='B')
    g.lv(105, y + 36, 30, 63, 10, '責任区分', r['resp'])
    g.rc(12, y + 46, 30, 26, fill=(0.93, 0.93, 0.93))
    g.t(13.5, y + 60, '返品理由', 8.5)
    g.rc(42, y + 46, 156, 26)
    g.para(45, y + 54, r['reason'], 38, 10, 'G')
    g.box('x_reason', 43, y + 47, 154, 24, '返品理由（判定に無関係）')
    g.lv(12, y + 72, 30, 63, 12, '返品受入日', sd(r['recv']), 11, key='k_recv')
    g.appr(150, y + 76, [('受入確認（物流）', DS(g, who, r['recv']), 'k_st_in', dsd(who, r['recv']))], w=30, h=22)
    g.rc(12, y + 84, 30, 22, fill=(0.93, 0.93, 0.93))
    g.t(13.5, y + 96, '備考', 8.5)
    g.rc(42, y + 84, 100, 22)
    g.para(45, y + 91, '現品は検品のうえ良品在庫へ戻入。' if r['resp'] == '顧客' else '現品は不適合品置場へ移動。原因は別途是正報告。', 24, 9.5, 'G')
    g.box('x_note', 43, y + 85, 98, 20, '備考')
    g.t(12, y + 116, '※ 返品金額 50万円以下：営業課長の承認、50万円超：営業部長の承認。いずれも経理課長の確認を要する', 8)
    g.t(12, y + 121, '　（職務権限規程 別表1）。承認は売上取消伝票の計上前に得ること。', 8)
    return g.save()


def cancel_slip(path, DT, r, seed):
    g = Pg(path, seed=seed)
    o = r['o']
    cu = DT['C'][o['c']]
    amt = r['q'] * r['pr']
    red = (0.78, 0.1, 0.12)
    g.t(12, 12, 'AOBA-SALES 売上管理 [U0420]', 7.5)
    g.t(105, 21, '売上取消伝票（赤伝）', 16, 'B', al='c', col=red)
    g.lv(12, 32, 30, 52, 9, '伝票番号', r['ano'], 11, key='k_no', f='B')
    g.lv(12, 41, 30, 52, 9, '計上日', sd(r['cd']), 11, key='k_date', f='B')
    g.lv(12, 50, 30, 100, 9, '取引先', f'{cu["code"]}　{cu["name"]}', key='k_cust')
    g.lv(12, 59, 30, 52, 9, '元売上番号', o['uno'], key='k_orig')
    g.lv(12, 68, 30, 52, 9, '返品申請番号', r['hno'], key='k_hp')
    g.lv(96, 68, 22, 34, 9, '起票者', full(r['by']), key='k_reg')
    g.appr(152, 30, [('起票', DS(g, r['by'], r['cd']), 'k_st_reg', dsd(r['by'], r['cd'])),
                     ('承認（経理課長）', DS(g, KRK, r['cd']), 'k_st_app', dsd(KRK, r['cd']))], w=23, h=22)
    cols = [('品番', 32, 'l'), ('品名', 70, 'l'), ('数量', 24, 'r'), ('単価', 26, 'r'), ('金額（税抜）', 34, 'r')]
    pp = PROD[r['p']]
    y = g.tbl(12, 84, cols, [[pp[0], pp[1], f'▲{yen(r["q"])}', yen(r['pr']), f'▲{yen(amt)}'], [''] * 5], 9, 10.5,
              keys={(0, 2): 'k_qty', (0, 4): 'k_amt'})
    g.lv(118, y, 46, 34, 8, '消費税（10%）', '')
    g.t(196.5, y + 5.4, f'▲{yen(int(amt * 0.1))}', 10, al='r')
    g.lv(118, y + 8, 46, 34, 8, '取消合計（税込）', '')
    g.t(196.5, y + 13.4, f'▲{yen(int(amt * 1.1))}', 10, al='r')
    y += 24
    g.rc(12, y, 30, 20, fill=(0.93, 0.93, 0.93))
    g.t(13.5, y + 11, '摘要', 8.5)
    g.rc(42, y, 156, 20)
    g.para(45, y + 7, f'返品受入に伴う売上取消（受入日 {sd(r["recv"])}）。請求は翌月請求書にて相殺する。', 40, 9.5, 'G')
    g.box('x_note', 43, y + 1, 154, 18, '摘要（判定に無関係）')
    g.t(12, y + 30, '※ 売上取消伝票は、起票者以外の経理課長が返品申請書と照合のうえ承認する（販売管理規程 第15条）。', 8)
    return g.save()


# ---------- C6 入金消込 ----------
def bank(path, DT, m, seed, two=False):
    g = Pg(path, seed=seed)
    rs = m['rows']
    C = DT['C']
    last = max(r['d'] for r in rs)
    cols = [('取引日', 24, 'c'), ('摘要', 20, 'c'), ('振込依頼人名', 82, 'l'), ('入金金額', 34, 'r'), ('備考', 26, 'l')]

    def head():
        g.t(14, 16, BANK, 13, 'M')
        g.t(196, 16, 'インターネットバンキング 照会結果', 8.5, 'M', al='r')
        g.ln(14, 18.5, 196, 18.5, 0.9)
        g.t(105, 28, '振込入金明細（期間指定照会）', 14, 'B', al='c')
        g.t(14, 37, '口座：普通預金 ＊＊＊4417　ｱｵﾊﾞｷｺｳﾊﾝﾊﾞｲ(ｶ', 9.5)
        me = (m['m'].replace(day=28) + dt.timedelta(days=5)).replace(day=1) - dt.timedelta(days=1)
        g.t(14, 43, f'対象期間：{sd(m["m"])} 〜 {sd(me)}', 9.5)
        g.t(196, 43, f'照会日時：{sd(add_bd(last, 1))} 09:1{seed % 10}', 9, al='r')

    allrows = [[sd(r['d']), '振込', hankaku(C[r['c']]['kana']), yen(r['pay']), ''] for r in rs]
    keys = {(i, 3): f'k_amt{i}' for i in (0, 12, len(rs) - 1)}
    head()
    if two:
        g.tbl(12, 50, cols, allrows[:14], 7.6, 10, keys={k: v for k, v in keys.items() if k[0] < 14})
        g.t(196, 285, '1 / 2', 8, al='r')
        g.newpage()
        head()
        y = g.tbl(12, 50, cols, allrows[14:], 7.6, 10, keys={(k[0] - 14, k[1]): v for k, v in keys.items() if k[0] >= 14})
    else:
        y = g.tbl(12, 50, cols, allrows, 7.6, 10, keys=keys)
    g.rc(12, y, 126, 9, fill=(0.93, 0.93, 0.93))
    g.t(75, y + 6, f'合　計（{len(rs)} 件）', 10, al='c')
    g.rc(138, y, 34, 9)
    g.t(170.5, y + 6, yen(sum(r['pay'] for r in rs)), 10.5, 'B', key='k_total', al='r')
    g.rc(172, y, 26, 9)
    g.t(14, 277, 'この明細はインターネットバンキングの照会結果を印刷したものです。残高証明としては使用できません。', 8, 'M')
    g.t(14, 282, 'ひかり中央銀行 芝浦支店　東京都港区芝浦九丁目97番1号　TEL 03-0155-7000', 8, 'M', key='x_foot')
    g.t(196, 285, '2 / 2' if two else '1 / 1', 8, al='r')
    return g.save()


def recon(path, DT, m, seed):
    g = Pg(path, land=True, seed=seed)
    rs = m['rows']
    C = DT['C']
    g.t(14, 16, f'入金消込一覧表（{m["m"].year}年{m["m"].month}月度）', 15, 'B')
    g.t(14, 24, f'経理課　作成日 {sd(m["made"])}', 9.5)
    g.t(14, 30, f'対象口座：{BANK} 普通 ＊＊＊4417', 9)
    g.appr(237, 6, [('作成', DS(g, m['by'], m['made']), 'k_st_made', dsd(m['by'], m['made'])),
                    ('承認（経理課長）', DS(g, KRK, m['ok']), 'k_st_ok', dsd(KRK, m['ok']))], w=23, h=21)
    cols = [('No', 8, 'c'), ('入金日', 20, 'c'), ('コード', 16, 'c'), ('取引先名', 62, 'l'), ('入金額', 26, 'r'),
            ('請求番号', 30, 'c'), ('請求額', 26, 'r'), ('差額', 16, 'r'), ('状態', 16, 'c'), ('備考', 49, 'l')]
    rows, keys = [], {}
    for i, r in enumerate(rs):
        diff = '' if r['bill'] is None else (yen(r['pay'] - r['bill']) if r['pay'] != r['bill'] else '0')
        rows.append([i + 1, sd(r['d']), C[r['c']]['code'], C[r['c']]['name'], yen(r['pay']), r['inv'],
                     '' if r['bill'] is None else yen(r['bill']), diff, r['state'], r['note']])
        if i in (0, 12, len(rs) - 1):
            keys[(i, 4)] = f'k_amt{i}'
        if r['state'] == '未消込':
            keys[(i, 8)] = 'k_um'
            keys[(i, 9)] = 'k_umnote'
    y = g.tbl(14, 36, cols, rows, 5.5, 8, keys=keys, hh=6)
    um = [r for r in rs if r['state'] == '未消込']
    g.t(14, y + 7, f'入金合計 {yen(sum(r["pay"] for r in rs))} 円（{len(rs)} 件）　／　消込済 '
                   f'{yen(sum(r["pay"] for r in rs if r["state"] == "消込済"))} 円（{len(rs) - len(um)} 件）　／　未消込 '
                   f'{yen(sum(r["pay"] for r in um))} 円（{len(um)} 件）', 10, 'B', key='k_total')
    g.t(14, y + 13, '※ 未消込の入金は理由を備考欄に記載し、翌月へ繰り越して管理する。月次の承認期限は翌月5営業日以内（販売管理規程 第16条）。', 8)
    return g.save()


# ---------- C7 滞留債権 ----------
def aging(path, DT, m, seed):
    g = Pg(path, land=True, seed=seed)
    C = DT['C']
    g.t(14, 16, f'売掛金滞留状況一覧（{m["m"].year}年{m["m"].month}月末現在）', 15, 'B')
    g.t(14, 24, f'経理課　作成日 {sd(m["made"])}　　対象：支払期日を30日超過した残高のある取引先', 9.5)
    g.appr(214, 6, [('作成（経理課）', DS(g, m['by'], m['made']), 'k_st_made', dsd(m['by'], m['made'])),
                    ('確認（経理課長）', DS(g, KRK, m['k']), 'k_st_k', dsd(KRK, m['k'])),
                    ('確認（営業部長）', DS(g, BU, m['b']), 'k_st_b', dsd(BU, m['b']))], w=23, h=21)
    cols = [('コード', 16, 'c'), ('取引先名', 54, 'l'), ('売掛金残高', 26, 'r'), ('期日内', 24, 'r'), ('1〜30日', 22, 'r'),
            ('31〜60日', 22, 'r'), ('61〜90日', 22, 'r'), ('90日超', 22, 'r'), ('原因・対応方針', 61, 'l')]
    x0, y, rh = 14, 38, 12
    cx = x0
    for tt, w, al in cols:
        g.rc(cx, y, w, 7, fill=(0.9, 0.9, 0.9))
        g.t(cx + w / 2, y + 4.8, tt, 8.5, al='c')
        cx += w
    y += 7
    tot = [0] * 6
    for i, r in enumerate(m['rows']):
        a = r['a']
        vals = [C[r['c']]['code'], C[r['c']]['name'], yen(sum(a))] + [yen(v) if v else '-' for v in a]
        tot = [t + v for t, v in zip(tot, [sum(a)] + a)]
        cx = x0
        for ci, (tt, w, al) in enumerate(cols):
            g.rc(cx, y, w, rh, fill=(1, 0.93, 0.93) if (ci == 7 and a[4]) else None)
            if ci < 8:
                k = f'k_c90_{i}' if (ci == 7 and a[4]) else None
                if al == 'r':
                    g.t(cx + w - 1.5, y + rh / 2 + 1.2, vals[ci], 9, key=k, al='r')
                elif al == 'c':
                    g.t(cx + w / 2, y + rh / 2 + 1.2, vals[ci], 9, al='c')
                else:
                    g.t(cx + 1.5, y + rh / 2 + 1.2, vals[ci], 8.5)
            else:
                if r['cm']:
                    if r.get('hand'):
                        for li, l in enumerate(wrap(r['cm'], 15)):
                            g.hw(cx + 1.5, y + 4.6 + li * 4.6, l, 10.5, 'Z')
                    else:
                        for li, l in enumerate(wrap(r['cm'], 22)):
                            g.t(cx + 1.5, y + 4.4 + li * 3.7, l, 7.6)
                if a[4]:
                    g.box(f'k_cm_{i}', cx, y, w, rh, r['cm'] or '（空欄）')
            cx += w
        y += rh
    cx = x0
    g.rc(cx, y, 70, 9, fill=(0.9, 0.9, 0.9))
    g.t(cx + 35, y + 6, '合　計', 9.5, al='c')
    cx += 70
    for v, w in zip(tot, [26, 24, 22, 22, 22, 22]):
        g.rc(cx, y, w, 9)
        g.t(cx + w - 1.5, y + 6, yen(v), 9, 'B', al='r')
        cx += w
    g.rc(cx, y, 61, 9)
    g.t(14, y + 17, '※ 90日超の滞留先は、原因と対応方針を必ず記載すること。経理課長および営業部長は記載内容を確認のうえ押印する（販売管理規程 第17条）。', 8)
    return g.save()


def memo(path, DT, m, seed):
    g = Pg(path, seed=seed)
    cu = DT['C'][[r for r in m['rows'] if r['a'][4]][0]['c']]
    g.t(105, 24, '滞留債権 対応記録', 16, 'B', al='c')
    g.t(14, 40, '取引先', 10)
    g.hw(34, 40, f'{cu["code"]} {cu["name"]}', 14, key='k_cust')
    g.ln(32, 42, 150, 42)
    g.t(14, 52, '対象月', 10)
    g.hw(34, 52, f'{m["m"].year}年{m["m"].month}月末 90日超', 14)
    g.ln(32, 54, 150, 54)
    cols = [('日付', 24, 'c'), ('対応内容', 128, 'l'), ('対応者', 30, 'c')]
    cx = 14
    for tt, w, al in cols:
        g.rc(cx, 62, w, 7, fill=(0.93, 0.93, 0.93))
        g.t(cx + w / 2, 66.8, tt, 9, al='c')
        cx += w
    ents = [('2/18', 'TEL。先方 経理部長と話す。支払保留は品質クレームが理由とのこと', '河合'),
            ('2/25', '技術部に不具合品の解析を依頼。結果は3/6頃の見込み', '河合'),
            ('3/2', '先方購買と訪問日を調整。3/12 14時で確定。技術部同行', '河合'),
            ('3/3', '経理 立花さんへ経過を連絡。一覧のコメント欄に記入', '河合')]
    y = 69
    for d1, tx, who in ents + [('', '', '')] * 4:
        cx = 14
        for w in (24, 128, 30):
            g.rc(cx, y, w, 17)
            cx += w
        if d1:
            g.hw(18, y + 10, d1, 14)
            for li, l in enumerate(wrap(tx, 26)):
                g.hw(40, y + 7 + li * 7, l, 12.5)
            g.hw(172, y + 10, who, 14)
        y += 17
    g.box('k_memo', 14, 69, 182, 68, '手書きの対応記録')
    return g.save()


# ---------- C8 期末 ----------
def cutoff(path, DT, seed):
    g = Pg(path, seed=seed)
    M = DT['C8M']
    g.t(105, 22, '期末売上計上時期確認表（2026年3月期）', 15, 'B', al='c')
    g.t(14, 36, '経理課', 10)
    g.t(14, 43, '確認対象：期末日（2026/03/31）前後3営業日の出荷のうち、', 9.5)
    g.t(14, 48.5, '　　　　　1件あたり税抜15万円以上の取引（全6件）', 9.5)
    g.appr(152, 30, [('作成', DS(g, M['by'], M['made']), 'k_st_made', dsd(M['by'], M['made'])),
                     ('承認（経理課長）', DS(g, KRK, M['ok']), 'k_st_ok', dsd(KRK, M['ok']))], w=23, h=22)
    cols = [('No', 8, 'c'), ('出荷番号', 28, 'c'), ('取引先名', 54, 'l'), ('金額（税抜）', 26, 'r'), ('出荷日', 22, 'c'),
            ('売上計上日', 22, 'c'), ('計上期', 14, 'c'), ('確認', 12, 'c')]
    rows, keys = [], {}
    for i, x in enumerate(DT['C8']):
        o = x['o']
        shown = o['sid'] if o['tag'] == 'C8S4' else o['sd']
        rows.append([i + 1, o['sno'], DT['C'][o['c']]['name'], yen(sum(q * pr for _, q, pr in o['lines'])), sd(shown),
                     sd(o['ld']), '当期' if o['ld'] <= D(2026, 3, 31) else '翌期', '○'])
        keys[(i, 4)] = f'k_sd{i + 1}'
        keys[(i, 5)] = f'k_ld{i + 1}'
    y = g.tbl(12, 64, cols, rows, 10, 9.5, keys=keys)
    g.t(14, y + 12, '確認方法：出荷報告書の出荷日と売上明細の計上日を照合した。', 10)
    g.t(14, y + 19, '確認結果：全件について、出荷日と同一の会計期間に売上が計上されていることを確認した。', 10)
    g.t(14, y + 32, '※ 本確認表は期末日後5営業日以内に経理課長の承認を得ること（販売管理規程 第18条）。', 8)
    return g.save()


# ---------- 共通資料 ----------
AUTH_ROWS = [('与信限度額の設定・変更', '500万円以下', '営業課長', '経理課長の確認を要する'),
             ('', '500万円超 3,000万円以下', '営業部長', '同上'), ('', '3,000万円超', '営業担当役員', '同上'),
             ('受注登録の承認', '全件', '営業課長', '登録者以外の者が承認する'),
             ('標準単価からの値引き', '5％以内', '営業担当者', '申請不要'), ('', '5％超 15％以内', '営業課長', '受注登録前に承認'),
             ('', '15％超', '営業部長', '同上'), ('返品・売上取消の承認', '50万円以下', '営業課長', '経理課長の確認を要する'),
             ('', '50万円超', '営業部長', '同上'), ('売上取消伝票の承認', '全件', '経理課長', '起票者以外の者が承認する'),
             ('入金消込一覧の承認', '月次', '経理課長', '翌月5営業日以内'),
             ('滞留債権レビュー', '月次', '経理課長・営業部長', '90日超は原因・対応方針を記載'),
             ('期末売上計上時期の確認', '期末', '経理課長', '期末日後5営業日以内')]
ROLE_ROWS = [('営業担当役員', '氷室 正人'), ('営業部長', '榊原 浩一'), ('営業1課長', '岡部 誠'), ('営業2課長', '西川 由美'),
             ('経理部長', '桑原 修'), ('経理課長', '溝口 智子')]
AUTH_TXT = [('第1条（目的）', '本規程は、当社の業務執行に関する決裁権限を定め、責任の所在を明確にすることを目的とする。'),
            ('第2条（適用範囲）', '本規程は、役員および全従業員に適用する。本抜粋は販売業務に関する部分を示す。'),
            ('第3条（決裁権者）', '決裁権者は別表1に定める。決裁権者は、自らが起案した事項を自ら決裁してはならない。'),
            ('第4条（決裁の時期）', '決裁は、対象となる取引または登録の実行前に得なければならない。やむを得ず事後となる場合は、その理由を記録し、上位者の承認を得る。'),
            ('第5条（上位者による決裁）', '上位の決裁権者は、下位の決裁権者の権限に属する事項を決裁することができる。'),
            ('第6条（決裁欄の記載）', '申請書の決裁欄のうち、決裁を要しない欄には斜線を引く。'),
            ('第7条（金額基準）', '金額基準は、消費税を除いた金額により判定する。分割して申請することにより基準を下回らせてはならない。'),
            ('第8条（権限の委任）', '決裁権者が出張、休暇等により不在となる場合は、あらかじめ「決裁権限委任届」により指名した者に権限を委任することができる。受任者が決裁する場合は、決裁欄に「代」と記載する。'),
            ('第9条（改廃）', '本規程の改廃は取締役会の決議による。')]
RULES = [('第1条（目的）', '本規程は、当社の販売業務の処理手続を定め、業務の適正かつ効率的な運営を図ることを目的とする。'),
         ('第2条（定義）', '本規程において販売業務とは、与信管理、受注、出荷、売上計上、請求、回収および債権管理に関する一連の業務をいう。'),
         ('第3条（所管）', '販売業務は営業部が所管し、売上計上、請求、回収の管理は経理部が所管する。出荷業務は物流課が行う。'),
         ('第4条（与信限度額）', '新規に取引を開始する場合、または既存取引先の限度額を変更する場合は、「与信限度額 設定・変更申請書」により決裁を得る。決裁権者は職務権限規程 別表1による。'),
         ('第5条（信用調査）', '与信限度額の申請にあたっては、申請日前6か月以内に取得した外部信用調査機関の報告書を添付し、評点を申請書に記載する。'),
         ('第6条（マスタ登録）', '経理課は、決裁が完了した申請書に基づき、取引先マスタへ限度額を登録する。決裁前の登録は認めない。'),
         ('第7条（限度額の超過）', '受注残高と売掛金残高の合計が限度額を超える場合、販売管理システムは出荷指示を保留する。'),
         ('第8条（受注）', '受注は、取引先の注文書その他の書面により内容を確認して登録する。口頭による受注は、取引先の担当者名と日時を備考欄に記録する。'),
         ('第9条（受注の承認）', '受注登録は、登録者以外の営業課長が注文書と照合のうえ承認する。注文内容に変更があった場合は、訂正後の注文書を入手して保管する。'),
         ('第10条（販売価格）', '販売価格は標準単価表による。標準単価からの値引きは、職務権限規程 別表1に定める承認を、受注登録の前に得なければならない。'),
         ('第11条（出荷）', '物流課は、出荷指示に基づき出荷を行い、出荷報告書に実際の出荷日と出荷数量を記録する。運送会社の集荷印を受ける。'),
         ('第12条（売上計上基準）', '売上は、商品を出荷した日（出荷報告書の出荷日（実績））をもって計上する。出荷指示日と実際の出荷日が異なる場合は、実際の出荷日による。'),
         ('第13条（物品受領書）', '営業部は、取引先の受領印または署名のある物品受領書を回収し、出荷の事実を確認する。'),
         ('第14条（返品）', '返品を受け入れる場合は、「返品・売上取消 申請書」により、職務権限規程 別表1に定める承認および経理課長の確認を得る。'),
         ('第15条（売上取消）', '経理課は、承認済みの申請書と返品受入の記録に基づき売上取消伝票を起票する。伝票は起票者以外の経理課長が承認する。'),
         ('第16条（入金消込）', '経理課は、銀行の入金明細と請求データを照合して消込を行い、月次で「入金消込一覧表」を作成する。経理課長は翌月5営業日以内に承認する。未消込の入金は理由を記載する。'),
         ('第17条（滞留債権）', '経理課は、月次で「売掛金滞留状況一覧」を作成する。支払期日を90日超過した債権については、原因と対応方針を記載し、経理課長および営業部長が確認する。'),
         ('第18条（期末の計上時期）', '経理課は、期末日前後の出荷取引について、売上の計上時期が適切であることを確認し、期末日後5営業日以内に経理課長の承認を得る。'),
         ('第19条（帳票の保存）', '本規程に定める帳票は、法令および文書管理規程に定める期間保存する。'),
         ('第20条（改廃）', '本規程の改廃は、営業部長および経理部長の協議を経て、担当役員が決裁する。')]


def authority(path, seed):
    g = Pg(path, seed=seed)
    g.t(105, 24, '職 務 権 限 規 程（販売関連抜粋）', 15, 'M', al='c')
    g.t(196, 33, '制定 2009年4月1日　最終改定 2024年4月1日', 8.5, 'M', al='r')
    y = 46
    for h, b in AUTH_TXT:
        g.t(16, y, h, 10.5, 'B')
        y = g.para(20, y + 6.5, b, 46, 10, 'M') + 4
    g.t(105, 285, '- 1 -', 8.5, 'M', al='c')
    g.newpage()
    g.t(14, 20, '別表1　決裁権限一覧（販売関連）', 12, 'B')
    cols = [('決裁事項', 50, 'l'), ('区分', 46, 'l'), ('決裁権者', 38, 'l'), ('備考', 52, 'l')]
    keys = {(0, 2): 'k_a1', (1, 2): 'k_a2', (2, 2): 'k_a3', (1, 1): 'k_a2r', (5, 2): 'k_a5', (6, 2): 'k_a6', (8, 2): 'k_a8'}
    y = g.tbl(12, 25, cols, AUTH_ROWS, 9, 9.5, 'M', keys=keys)
    g.t(14, y + 14, '別表2　役職者一覧（2025年4月1日現在）', 12, 'B')
    y = g.tbl(12, y + 19, [('役職', 60, 'l'), ('氏名', 60, 'l')], ROLE_ROWS, 9, 10, 'M',
              keys={(1, 1): 'k_r1', (2, 1): 'k_r2', (3, 1): 'k_r3'})
    g.t(14, y + 8, '※ 期中の異動はない（2026年3月31日現在）。', 8.5, 'M')
    g.t(105, 285, '- 2 -', 8.5, 'M', al='c')
    return g.save()


def rules(path, seed):
    g = Pg(path, seed=seed)
    g.t(105, 24, '販 売 管 理 規 程', 16, 'M', al='c')
    g.t(196, 33, '制定 2011年4月1日　最終改定 2024年10月1日', 8.5, 'M', al='r')
    y, pn = 46, 1
    for i, (h, b) in enumerate(RULES):
        need = 6.5 + len(wrap(b, 46)) * 6.2 + 4
        if y + need > 272:
            g.t(105, 285, f'- {pn} -', 8.5, 'M', al='c')
            g.newpage()
            pn += 1
            y = 26
        g.t(16, y, h, 10.5, 'B', key=f'k_art{i + 1}' if i + 1 in (12, 17) else None)
        y = g.para(20, y + 6.5, b, 46, 10, 'M') + 4
    g.t(105, 285, f'- {pn} -', 8.5, 'M', al='c')
    return g.save()
