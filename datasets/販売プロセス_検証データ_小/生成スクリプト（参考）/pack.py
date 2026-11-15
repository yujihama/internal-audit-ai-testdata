# -*- coding: utf-8 -*-
"""README の作成、プレビュー画像、ZIP 化"""
import os, pickle, shutil, zipfile, json
from collections import Counter
import pymupdf as fitz
from PIL import Image, ImageDraw, ImageFont
from common import *

NAME = '販売プロセス_検証データ_小'
OUT = f'{ROOT}/out/{NAME}'
BK = pickle.load(open(f'{ROOT}/out/tmp/book.pkl', 'rb'))
ocr = json.load(open(f'{ROOT}/out/tmp/ocr_ref.json'))
fr = [f for f in BK['frow'] if f[0] == 'A_難版']
ev = [f for f in fr if not f[1].startswith('共通資料/') and f[1] != '手続一覧.xlsx']
st = Counter(f[6] for f in ev)
lay = Counter('なし（画像のみ）' if f[5].startswith('なし') else ('あり（誤りを含む）' if '誤り' in f[5] else (
    'あり（文字化け）' if '文字化け' in f[5] else ('混在' if f[5].startswith('混在') else 'あり（正しい）'))) for f in fr)
ext = Counter(f[1].rsplit('.', 1)[1] for f in fr)
ra = sum(r[2] for r in ocr if r[0] == 'A') / sum(r[3] for r in ocr if r[0] == 'A')
rb = sum(r[2] for r in ocr if r[0] == 'B') / sum(r[3] for r in ocr if r[0] == 'B')
ops = Counter()
for f in ev:
    for o in f[4].split('、'):
        ops[o.split('約')[0] if o.startswith('傾き') else o] += 1

rows = []
for a, p in zip(BK['ans'], BK['prow']):
    tags = Counter(t for s in a['S'] for t in s[4])
    rows.append(f'| {a["id"]} | {p[1]} | {p[3]} | {p[4]} | {"、".join(f"{k}{v}" for k, v in tags.items()) or "-"} |')

md = f'''# 販売プロセス 検証データ（小）

内部監査手続をAIで評価する仕組みの検証用データです。会社名・人名・番号はすべて架空です。

**注意：このREADMEと `正解/` フォルダには正解が書かれています。検証対象には渡さないでください。**

## 1. 構成

| フォルダ | 内容 | 用途 |
|---|---|---|
| `A_難版/` | 手続一覧、共通資料、証跡（可読性を難しくした版） | 検証対象への入力（本番想定） |
| `B_対照版/` | A と同じ内容で、読みやすい版 | 検証対象への入力（比較用） |
| `正解/` | 正解表.xlsx、正解.json | 答え合わせ用。検証対象には渡さない |
| `生成スクリプト（参考）/` | データを作ったプログラム | 規模の拡張や作り直しの参考 |

- A と B は、同じ統制・同じ取引・同じ不備を含みます。違いは証跡の読みやすさだけです。
- A と B の結果の差が「読み取りに起因する誤り」、B でも誤る分が「判断に起因する誤り」に当たります。

## 2. 題材

- 会社：アオバ機工販売株式会社（産業部品の卸売、3月決算、売上は出荷基準）
- 評価対象期間：2025年4月1日〜2026年3月31日
- 統制 8、手続 13、判定の単位（手続×サンプル）56
- サンプル数は小規模版として縮小（都度の統制は5件、月次は3か月分、期末は6件）
- 売上明細は {len(pickle.load(open(f"{ROOT}/out/tmp/state.pkl", "rb"))["DT"]["rows"]):,} 行、取引先台帳は200社

## 3. 正解の内訳

| 手続 | 統制 | 正解（A_難版） | 正解（B_対照版） | 仕込み（件数） |
|---|---|---|---|---|
{chr(10).join(rows)}

- 手続単位の正解：サンプルに「不備あり」が1件でもあれば「不備あり」。なければ、「判断できない」が1件でもあれば「判断できない」。
- 仕込みの種類
  - 不備：統制の逸脱（承認欄が空、数量の不一致、事後承認、権限外の承認、期ズレ、形だけのレビュー）
  - ひっかけ：不備に見えるが正常（代理決裁と委任届、訂正注文書、値引率の境界値、未消込の理由記載 など）
  - 判読不能：人でも読めない箇所が判定に必要な箇所にある（A のみ。B では「不備なし」）
  - 証跡の不足・取り違え：別取引の申請書が入っている（A・B 共通）
  - 文字情報の罠：PDFから取り出せる文字情報が画像と異なる（A のみ）

## 4. 可読性（A_難版）

証跡 {len(ev)} ファイル（手続一覧と共通資料のExcelを除く）の内訳：

| 段階 | 状態 | ファイル数 |
|---|---|---|
| 1 | 問題なく読める | {st[1]} |
| 2 | 読みにくいが人は読める | {st[2]} |
| 3 | 人でも読めない箇所がある | {st[3]}（うち判定に影響あり 3） |

文字情報（プログラムでの取得）の内訳（全 {len(fr)} ファイル）：

| 種類 | ファイル数 |
|---|---|
{chr(10).join(f"| {k} | {v} |" for k, v in lay.most_common())}

- 形式：{"、".join(f"{k} {v}" for k, v in ext.most_common())}
- 画質の加工（重複あり）：{"、".join(f"{k} {v}" for k, v in ops.most_common() if k != "加工なし（電子的に作成されたPDF）" and not k.startswith("加工なし"))}
- 参考：一般的な文字読取ソフト（tesseract 日本語）で主要項目が読めた割合は、A_難版 {ra:.0%}、B_対照版 {rb:.0%}。難しさの目安です。
- 段階2の主要項目（金額・日付・印影など）は、拡大して人が読めることを目視で確認しています。段階3の箇所と判定への影響は、正解表の「ファイル別の可読性」に記載しています。

## 5. 使い方

1. `A_難版/` の `手続一覧.xlsx` と証跡一式を検証対象に入力し、手続ごと・サンプルごとの判定を得る。
2. `B_対照版/` でも同じことを行う。
3. `正解/正解表.xlsx`（または `正解.json`）と突き合わせる。見るべき点：
   - 不備の見逃し（不備あり → 不備なし）
   - 指摘しすぎ（ひっかけを不備と判定）
   - 「判断できない」と言うべき場面で断定していないか（判読不能、証跡の取り違え）
   - 文字情報の罠に引っかかっていないか（画像を見ずに文字情報だけで判定していないか）

## 6. 前提と制約

- 今回は「可読性」と「不備の埋め込み方」を動かした版です。量と複雑さは抑えています。
  - ファイル名は内容が分かる名前にしています（例：`C2_S1_注文書.pdf`）。
  - 無関係な資料の混入は、C5 の S3（別取引の返品申請書）の1件だけです。
- 入金消込の請求番号・請求額は、売上明細とは連動していません（入金明細と消込一覧の照合のみを想定）。
- 「人でも読めない」の線引きは作成者の目視によります。利用時に見直す余地があります。
- 印影は対照版でも画像です（文字情報には入りません）。
- 文書に埋め込んだフォントは SIL Open Font License のもの（BIZ UDゴシック／明朝、Yomogi、Zen Kurenaido、Klee One、DotGothic16）です。

## 7. 検証の記録

- 正解は、取引データから独立に再計算した結果と56件すべて一致することを確認しています。
- 対照版PDFの文字情報に主要項目の値が含まれること、難版の「文字情報の罠」が実際に取り出せることを確認しています。
- 全ファイルが開けること、A と B のファイルが1対1で対応することを確認しています。
'''
open(f'{OUT}/README.md', 'w', encoding='utf-8').write(md)

# 生成スクリプト
sd = f'{OUT}/生成スクリプト（参考）'
shutil.rmtree(sd, ignore_errors=True)
os.makedirs(sd)
for f in ('common.py', 'data.py', 'render.py', 'docs.py', 'screens.py', 'degrade.py', 'build.py', 'book.py', 'verify.py', 'ocr_ref.py', 'pack.py'):
    shutil.copy(f'{ROOT}/src/{f}', sd)
open(f'{sd}/実行方法.txt', 'w', encoding='utf-8').write(
    '実行順: build.py → ocr_ref.py（任意）→ book.py → verify.py → pack.py\n'
    '必要なもの: Python 3.11以降、reportlab / pymupdf / pillow / numpy / opencv-python-headless / openpyxl、tesseract（ocr_ref.py のみ）\n'
    'フォント: Google Fonts の BIZ UDGothic(Regular/Bold)、BIZ UDMincho、Yomogi、Klee One、Zen Kurenaido、DotGothic16 を fonts/ に置く\n'
    '注意: 作業フォルダのパス（common.py の ROOT）は環境に合わせて書き換えること。乱数の種は固定のため、同じ内容が再生成される\n'
    '規模の拡張: data.py のサンプル定義と build.py の加工の割り当て表（plans）を増やす\n')

# プレビュー
base = f'{OUT}/A_難版/'
items = [('C2_受注/C2_S1_注文書.pdf', 'FAX＋黒い帯（判読不能）'), ('C3_値引/C3_S3_値引申請書.jpg', '撮影＋光の反射'),
         ('C4_出荷・売上計上/C4_S4_物品受領書.pdf', '複写伝票＋水濡れ'), ('C1_与信限度額/C1_S3_与信申請書.pdf', '薄い＋傾き（不備あり）'),
         ('C1_与信限度額/C1_S2_信用調査報告書.pdf', '粗い網点＋誤った文字情報'), ('C5_返品・売上取消/C5_S1_売上取消伝票.pdf', '暗い＋うねり'),
         ('C5_返品・売上取消/C5_S4_返品申請書.pdf', '裏写り＋行ずれ＋汚れ'), ('C7_滞留債権/C7_2026-02_滞留一覧.jpg', '撮影（手書きコメント）')]
W = 560
f = ImageFont.truetype(fp('B'), 26)
ims = []
for p, cap in items:
    if p.endswith('.pdf'):
        pm = fitz.open(base + p)[0].get_pixmap(dpi=80)
        im = Image.frombytes('RGB', (pm.w, pm.h), pm.samples)
    else:
        im = Image.open(base + p).convert('RGB')
    im = im.resize((W, int(im.height * W / im.width)))
    c = Image.new('RGB', (W, 800), 'white')
    c.paste(im.crop((0, 0, W, min(im.height, 756))), (0, 44))
    d = ImageDraw.Draw(c)
    d.rectangle((0, 0, W, 42), fill=(30, 40, 70))
    d.text((10, 7), cap, font=f, fill='white')
    ims.append(c)
sheet = Image.new('RGB', (W * 4 + 30, 800 * 2 + 10), (120, 120, 120))
for i, c in enumerate(ims):
    sheet.paste(c, ((i % 4) * (W + 10), (i // 4) * 810))
sheet.save(f'{ROOT}/out/プレビュー_難版の例.png')

# ZIP
zp = f'{ROOT}/out/{NAME}.zip'
if os.path.exists(zp):
    os.remove(zp)
with zipfile.ZipFile(zp, 'w', zipfile.ZIP_DEFLATED) as z:
    for dp, _, fs in os.walk(OUT):
        for x in sorted(fs):
            full_ = os.path.join(dp, x)
            z.write(full_, os.path.join(NAME, os.path.relpath(full_, OUT)))
print('zip MB', round(os.path.getsize(zp) / 1e6, 1), 'files', sum(len(fs) for _, _, fs in os.walk(OUT)))
print(md[:200])
