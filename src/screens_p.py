# -*- coding: utf-8 -*-
"""購買システムの画面の写し、フローチャート（画像）"""
from PIL import Image, ImageDraw, ImageFont
from common import *

O_, X_ = '○', '－'
# ID, 氏名, 所属, 発注登録, 発注承認, 検収登録, マスタ登録, 支払作成, 支払承認, FB送信, 状態, 最終ログイン
USERS = [('U001', '藤本 浩二', '購買課', X_, O_, X_, X_, X_, X_, X_, '有効', '2026/03/31'), ('U002', '神崎 礼子', '購買部', X_, O_, X_, X_, X_, X_, X_, '有効', '2026/03/30'),
         ('U003', '早瀬 徹', '役員', X_, O_, X_, X_, X_, X_, X_, '有効', '2026/03/24'), ('U004', '大西 悠人', '購買課', O_, X_, X_, X_, X_, X_, X_, '有効', '2026/03/31'),
         ('U005', '福田 真由', '購買課', O_, X_, X_, X_, X_, X_, X_, '有効', '2026/03/31'), ('U006', '今井 涼', '購買課', O_, X_, X_, X_, X_, X_, X_, '有効', '2026/03/31'),
         ('U007', '野口 拓也', '購買課', O_, X_, X_, X_, X_, X_, X_, '有効', '2025/12/18'), ('U008', '柴田 恵', '購買課', O_, X_, X_, X_, X_, X_, X_, '無効', '2025/06/27'),
         ('U009', '矢野 翔', '物流課', X_, X_, O_, X_, X_, X_, X_, '有効', '2026/03/31'), ('U010', '北村 和也', '物流課', X_, X_, O_, X_, X_, X_, X_, '有効', '2026/03/31'),
         ('U011', '相馬 剛', '物流課', X_, X_, O_, X_, X_, X_, X_, '有効', '2026/03/27'), ('U012', '立花 奈央', '経理課', X_, X_, X_, O_, O_, X_, X_, '有効', '2026/03/31'),
         ('U013', '宮下 亮', '経理課', X_, X_, X_, O_, X_, X_, O_, '有効', '2026/03/31'), ('U014', '溝口 智子', '経理課', X_, X_, X_, X_, X_, O_, X_, '有効', '2026/03/31'),
         ('U015', '桑原 修', '経理部', X_, X_, X_, X_, X_, O_, X_, '有効', '2026/03/19'), ('U016', '永井 淳', '情報システム課', X_, X_, X_, X_, X_, X_, X_, '有効', '2026/03/17'),
         ('U017', '岡部 誠', '営業1課', X_, X_, X_, X_, X_, X_, X_, '有効', '2026/03/26'), ('U018', '西川 由美', '営業2課', X_, X_, X_, X_, X_, X_, X_, '有効', '2026/03/30'),
         ('U019', '河合 美咲', '営業2課', X_, X_, X_, X_, X_, X_, X_, '有効', '2026/03/31'), ('U020', '佐野 拓海', '営業1課', X_, X_, X_, X_, X_, X_, X_, '有効', '2026/03/31'),
         ('U021', '堀 大輔', '営業2課', X_, X_, X_, X_, X_, X_, X_, '有効', '2026/03/31'), ('ADM01', '三浦 航', '情報システム課', O_, O_, O_, O_, O_, O_, O_, '有効', '2026/03/31')]


def _f(s, b=False):
    return ImageFont.truetype(fp('B' if b else 'G'), s)


def _frame(title, W=1180, H=560, status='ログイン: ADM01（三浦 航）      2026/04/14 10:2'):
    im = Image.new('RGB', (W, H), (236, 233, 216))
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, W, 28), fill=(10, 36, 106))
    d.text((10, 5), f'購買管理システム AOBA-PROC  -  {title}', font=_f(15), fill='white')
    d.rectangle((0, 28, W, 54), fill=(212, 208, 200))
    d.text((10, 34), 'ファイル(F)    編集(E)    照会(Q)    帳票(R)    ヘルプ(H)', font=_f(13), fill='black')
    d.rectangle((0, H - 26, W, H), fill=(212, 208, 200))
    d.text((10, H - 21), status, font=_f(13), fill='black')
    return im, d


def users_screen(page, seed):
    im, d = _frame('利用者ID・権限一覧 [A0110]', status=f'ログイン: ADM01（三浦 航）      2026/04/14 10:2{seed % 10}      {page} / 2 ページ')
    cols = [('ユーザーID', 84), ('氏名', 120), ('所属', 150), ('発注登録', 84), ('発注承認', 84), ('検収登録', 84), ('マスタ登録', 96), ('支払作成', 84), ('支払承認', 84),
            ('FB送信', 76), ('状態', 66), ('最終ログイン', 116)]
    x0, y = 24, 70
    d.text((x0, y), f'対象：全利用者（22件）　表示 {(page - 1) * 11 + 1}〜{page * 11} 件目', font=_f(14), fill='black')
    y += 28
    cx = x0
    for t, w in cols:
        d.rectangle((cx, y, cx + w, y + 26), fill=(212, 208, 200), outline=(110, 110, 110))
        d.text((cx + 5, y + 5), t, font=_f(13), fill='black')
        cx += w
    boxes, kv = {}, {}
    for r in USERS[(page - 1) * 11:page * 11]:
        y += 26
        cx = x0
        for ci, (v, (t, w)) in enumerate(zip(r, cols)):
            bad = r[10] == '無効'
            d.rectangle((cx, y, cx + w, y + 26), fill=(225, 225, 225) if bad else 'white', outline=(110, 110, 110))
            f = _f(14)
            if 3 <= ci <= 9:
                tw = d.textlength(v, font=f)
                d.text((cx + (w - tw) / 2, y + 5), v, font=f, fill='black')
            else:
                d.text((cx + 5, y + 5), v, font=f, fill='black')
            key = {('U007', 1): 'k_ng', ('U007', 2): 'k_ng_dept', ('U007', 3): 'k_ng_reg', ('U007', 10): 'k_ng_state', ('U007', 11): 'k_ng_last',
                   ('U008', 1): 'k_sb', ('U008', 10): 'k_sb_state', ('ADM01', 0): 'k_adm', ('U004', 3): 'k_u4', ('U012', 7): 'k_u12', ('U014', 8): 'k_u14'}.get((r[0], ci))
            if key:
                boxes[key] = (0, cx - 2, y - 2, cx + w + 2, y + 28)
                kv[key] = v
            cx += w
    for i, t in enumerate(['前ページ(F7)', '次ページ(F8)', 'CSV出力(F9)', '閉じる(F12)']):
        d.rectangle((24 + i * 140, 470, 150 + i * 140, 502), fill=(212, 208, 200), outline=(90, 90, 90))
        d.text((34 + i * 140, 478), t, font=_f(13), fill='black')
    return im, boxes, kv


def setting_screen(seed):
    im, d = _frame('請求照合 条件設定 [P0910]', 1000, 600, 'ログイン: ADM01（三浦 航）      2026/04/14 10:41      照会モード')
    boxes, kv = {}, {}

    def field(x0, y0, label, val, w=220, key=None, lw=250):
        d.text((x0, y0 + 5), label, font=_f(14), fill='black')
        bx = x0 + lw
        d.rectangle((bx, y0, bx + w, y0 + 27), fill='white', outline=(120, 120, 120))
        d.text((bx + 6, y0 + 5), val, font=_f(15, True), fill='black')
        if key:
            boxes[key] = (0, bx - 2, y0 - 2, bx + w + 2, y0 + 29)
            kv[key] = val

    d.rectangle((20, 78, 980, 300), outline=(120, 120, 120))
    d.rectangle((32, 68, 190, 88), fill=(236, 233, 216))
    d.text((38, 69), '3点照合の条件', font=_f(14), fill='black')
    field(40, 100, '数量の許容差（請求数量－検収数量）', '0', 120, 'k_qtol', 330)
    field(40, 138, '単価の許容差（請求単価と発注単価）', '0.0 %', 120, 'k_ptol', 330)
    field(40, 176, '不一致の場合の処理', '支払保留（エラー E-2103 / E-2104）', 380, 'k_act', 330)
    field(40, 214, '支払保留の解除権限', '経理課長（U014）', 380, 'k_rel', 330)
    field(40, 252, '最終更新日／更新者', '2024/04/01　ADM01', 380, 'k_upd', 330)
    d.text((40, 322), '設定の変更履歴', font=_f(13), fill='black')
    cols = [('更新日', 150), ('項目', 260), ('変更前', 170), ('変更後', 170), ('更新者', 170)]
    yy, cx = 344, 40
    for t, w in cols:
        d.rectangle((cx, yy, cx + w, yy + 24), fill=(212, 208, 200), outline=(120, 120, 120))
        d.text((cx + 6, yy + 4), t, font=_f(13), fill='black')
        cx += w
    for r in [['2024/04/01', '数量の許容差', '5 %', '0', 'ADM01'], ['2024/04/01', '単価の許容差', '1.0 %', '0.0 %', 'ADM01']]:
        yy += 24
        cx = 40
        for v, (t, w) in zip(r, cols):
            d.rectangle((cx, yy, cx + w, yy + 24), fill='white', outline=(120, 120, 120))
            d.text((cx + 6, yy + 4), v, font=_f(13), fill='black')
            cx += w
    d.text((40, 430), '※ 2025年4月1日以降の変更履歴はありません。', font=_f(13), fill='black')
    boxes['k_hist'] = (0, 36, 426, 500, 452)
    kv['k_hist'] = '2025年4月1日以降の変更履歴はありません'
    return im, boxes, kv


def test_screen(seed):
    im, d = _frame('請求照合 入力 [P0420]（テスト環境）', 1000, 600, 'ログイン: TEST01（内部監査室 片岡）      2026/04/14 11:05      テスト環境')
    boxes, kv = {}, {}
    rows = [('発注番号', 'PO-TEST-0001'), ('品番', 'LG-15-400'), ('発注数量', '120'), ('検収数量（累計）', '100'), ('請求数量', '120'), ('発注単価', '11,900'),
            ('請求単価', '11,900')]
    for i, (a, b) in enumerate(rows):
        y0 = 80 + i * 36
        d.text((40, y0 + 5), a, font=_f(14), fill='black')
        d.rectangle((220, y0, 420, y0 + 27), fill='white', outline=(120, 120, 120))
        d.text((226, y0 + 5), b, font=_f(15, True), fill='black')
        if a in ('検収数量（累計）', '請求数量'):
            k = 'k_recv' if a.startswith('検収') else 'k_inv'
            boxes[k] = (0, 218, y0 - 2, 422, y0 + 29)
            kv[k] = b
    d.rectangle((470, 150, 950, 360), fill=(236, 233, 216), outline=(60, 60, 60), width=2)
    d.rectangle((470, 150, 950, 178), fill=(160, 30, 30))
    d.text((480, 155), 'エラー', font=_f(15), fill='white')
    d.text((490, 196), 'E-2103', font=_f(18, True), fill=(160, 30, 30))
    d.text((490, 230), '請求数量が検収数量を超えています。', font=_f(15), fill='black')
    d.text((490, 256), '（検収 100 ／ 請求 120）', font=_f(15), fill='black')
    d.text((490, 290), 'この請求は「支払保留」として登録されました。', font=_f(15, True), fill='black')
    d.rectangle((660, 320, 760, 348), fill=(212, 208, 200), outline=(90, 90, 90))
    d.text((694, 325), 'OK', font=_f(14), fill='black')
    boxes['k_err'] = (0, 474, 184, 946, 316)
    kv['k_err'] = 'E-2103 請求数量が検収数量を超えています／支払保留として登録'
    d.text((40, 360), '状態：支払保留', font=_f(15, True), fill=(160, 30, 30))
    boxes['k_state'] = (0, 36, 356, 240, 384)
    kv['k_state'] = '状態：支払保留'
    return im, boxes, kv


def flowchart(seed):
    W, H = 1400, 980
    im = Image.new('RGB', (W, H), 'white')
    d = ImageDraw.Draw(im)
    d.text((W / 2 - 190, 14), 'フローチャート（購買プロセス）', font=_f(26, True), fill='black')
    lanes = ['依頼部署', '購買課', '物流課', '経理課']
    lw, top = 330, 70
    for i, l in enumerate(lanes):
        x = 40 + i * lw
        d.rectangle((x, top, x + lw, H - 30), outline='black', width=2)
        d.rectangle((x, top, x + lw, top + 40), fill=(220, 226, 240), outline='black', width=2)
        tw = d.textlength(l, font=_f(20, True))
        d.text((x + (lw - tw) / 2, top + 8), l, font=_f(20, True), fill='black')
    boxes, kv = {}, {}

    def box(lane, row, text, ctl=None, key=None):
        x, y = 40 + lane * lw + 45, top + 70 + row * 104
        d.rectangle((x, y, x + 240, y + 62), fill=(255, 255, 240), outline='black', width=2)
        for li, t in enumerate(text.split('\n')):
            tw = d.textlength(t, font=_f(16))
            d.text((x + (240 - tw) / 2, y + 10 + li * 22), t, font=_f(16), fill='black')
        if ctl:
            d.ellipse((x + 205, y - 16, x + 262, y + 16), fill=(200, 30, 30))
            tw = d.textlength(ctl, font=_f(14, True))
            d.text((x + 233.5 - tw / 2, y - 9), ctl, font=_f(14, True), fill='white')
        if key:
            boxes[key] = (0, x - 4, y - 18, x + 266, y + 66)
            kv[key] = text.replace('\n', ' ') + (f'（{ctl}）' if ctl else '')
        return (x, y)

    def arrow(a, b):
        ax, ay = a[0] + 120, a[1] + 62
        bx, by = b[0] + 120, b[1]
        if abs(ax - bx) < 5:
            d.line((ax, ay, bx, by), fill='black', width=2)
        else:
            my = ay + 20
            d.line((ax, ay, ax, my, bx, my, bx, by), fill='black', width=2)
        d.polygon((bx - 7, by - 12, bx + 7, by - 12, bx, by), fill='black')

    b1 = box(0, 0, '購買依頼書の起票\n部署長の承認', '1', 'k_b1')
    b2 = box(1, 1, '見積の取得・比較\n（50万円以上）', '2', 'k_b2')
    b3 = box(1, 2, '発注の登録\n金額に応じた承認', '3', 'k_b3')
    b4 = box(1, 3, '注文書の送付', None)
    b5 = box(2, 4, '入荷・検収\n（発注担当者以外）', '5', 'k_b5')
    b6 = box(3, 5, '請求書の3点照合\n経理課長の承認', '6', 'k_b6')
    b7 = box(3, 6, '支払予定表の承認\nFB送信（別の担当者）', '7', 'k_b7')
    b8 = box(1, 6, '発注一覧の月次レビュー\n（分割発注の確認）', '4', 'k_b8')
    for a, b in [(b1, b2), (b2, b3), (b3, b4), (b4, b5), (b5, b6), (b6, b7)]:
        arrow(a, b)
    d.text((60, H - 24), '●印の番号は、業務記述書のNo（統制のあるステップ）に対応する。', font=_f(14), fill='black')
    return im, boxes, kv
