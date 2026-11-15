# -*- coding: utf-8 -*-
"""システム画面の写し（取引先マスタ照会）"""
from PIL import Image, ImageDraw, ImageFont
from common import *


def master_screen(DT, x, seed):
    cu = DT['C'][x['c']]
    W, H = 1000, 640
    im = Image.new('RGB', (W, H), (236, 233, 216))
    d = ImageDraw.Draw(im)
    f = lambda s, b=False: ImageFont.truetype(fp('B' if b else 'G'), s)
    d.rectangle((0, 0, W, 28), fill=(10, 36, 106))
    d.text((10, 5), '販売管理システム AOBA-SALES  -  取引先マスタ照会 [M0210]', font=f(15), fill='white')
    d.rectangle((0, 28, W, 54), fill=(212, 208, 200))
    d.text((10, 34), 'ファイル(F)    編集(E)    照会(Q)    帳票(R)    ヘルプ(H)', font=f(13), fill='black')
    boxes, kv = {}, {}

    def field(x0, y0, label, val, w=260, key=None, bold=False, lw=130):
        d.text((x0, y0 + 5), label, font=f(14), fill='black')
        bx = x0 + lw
        d.rectangle((bx, y0, bx + w, y0 + 27), fill='white', outline=(120, 120, 120))
        d.text((bx + 6, y0 + 5), val, font=f(15, bold), fill='black')
        if key:
            boxes[key] = (0, bx - 2, y0 - 2, bx + w + 2, y0 + 29)
            kv[key] = val

    field(30, 75, '取引先コード', cu['code'], 120)
    field(30, 110, '取引先名', cu['name'], 420, 'k_cust')
    field(30, 145, 'カナ名', hankaku(cu['kana']), 420)
    field(30, 180, '所在地', cu['addr'], 420)
    field(30, 215, '担当課', cu['sec'], 160)
    field(520, 215, '担当者', full(cu['rep']), 200)
    field(30, 250, '取引状態', '取引中', 120)
    field(520, 250, '取引開始日', sd(cu['start']), 160)
    d.rectangle((20, 300, W - 20, 500), outline=(120, 120, 120))
    d.rectangle((32, 290, 120, 310), fill=(236, 233, 216))
    d.text((38, 291), '与信情報', font=f(14), fill='black')
    field(40, 322, '与信限度額', yen(x['req']) + ' 円', 220, 'k_limit', True)
    field(520, 322, '限度額更新日', sd(x['md']), 160, 'k_upd', True)
    field(40, 357, '更新者', full('宮下'), 220)
    field(520, 357, '申請番号', x['no'], 160, 'k_no')
    d.text((40, 398), '限度額変更履歴', font=f(13), fill='black')
    cols = [('更新日', 150), ('変更前（円）', 180), ('変更後（円）', 180), ('更新者', 160), ('申請番号', 200)]
    rows = [[sd(x['md']), yen(x['cur']), yen(x['req']), full('宮下'), x['no']]]
    if x['kind'] == '増額':
        rows.append([sd(D(x['md'].year - 2, 4, 11)), '0', yen(x['cur']), full('立花'), f'YS-{x["md"].year - 2}-019'])
    yy = 418
    cx = 40
    for t, w in cols:
        d.rectangle((cx, yy, cx + w, yy + 22), fill=(212, 208, 200), outline=(120, 120, 120))
        d.text((cx + 6, yy + 3), t, font=f(13), fill='black')
        cx += w
    for r in rows:
        yy += 22
        cx = 40
        for v, (t, w) in zip(r, cols):
            d.rectangle((cx, yy, cx + w, yy + 22), fill='white', outline=(120, 120, 120))
            d.text((cx + 6, yy + 3), v, font=f(13), fill='black')
            cx += w
    for i, t in enumerate(['照会(F5)', '前へ(F7)', '次へ(F8)', '印刷(F9)', '閉じる(F12)']):
        d.rectangle((40 + i * 130, 530, 150 + i * 130, 562), fill=(212, 208, 200), outline=(90, 90, 90))
        d.text((52 + i * 130, 538), t, font=f(13), fill='black')
    d.rectangle((0, H - 26, W, H), fill=(212, 208, 200))
    d.text((10, H - 21), f'ログイン: 宮下 亮      2026/05/12 10:4{seed % 10}      照会モード', font=f(13), fill='black')
    return im, boxes, kv
