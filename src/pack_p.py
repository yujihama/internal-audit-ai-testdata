# -*- coding: utf-8 -*-
"""購買プロセス: README の作成、プレビュー画像、ZIP 化"""
import os, pickle, shutil, zipfile, json
from collections import Counter
import pymupdf as fitz
from PIL import Image, ImageDraw, ImageFont
from common import *

NAME = '購買プロセス_検証データ_小'
OUT, TMP = f'{ROOT}/out/{NAME}', f'{ROOT}/out/tmp_p'
BK = pickle.load(open(f'{TMP}/book.pkl', 'rb'))
ST = pickle.load(open(f'{TMP}/state.pkl', 'rb'))
ocr = json.load(open(f'{TMP}/ocr_ref.json'))
fr = [f for f in BK['frow'] if f[0] == 'A_難版']
ev = [f for f in fr if not f[1].startswith('共通資料/') and f[1] != '手続一覧.xlsx']
st = Counter(f[6] for f in ev)
imp = sum(1 for f in ev if f[8] == 'あり')
lay = Counter('なし（画像のみ）' if f[5].startswith('なし') else ('あり（誤りを含む）' if '誤り' in f[5] else (
    'あり（文字化け）' if '文字化け' in f[5] else ('混在' if f[5].startswith('混在') else 'あり（正しい）'))) for f in fr)
ext = Counter(f[1].rsplit('.', 1)[1] for f in fr)
ra = sum(r[2] for r in ocr if r[0] == 'A') / sum(r[3] for r in ocr if r[0] == 'A')
rb = sum(r[2] for r in ocr if r[0] == 'B') / sum(r[3] for r in ocr if r[0] == 'B')
ops = Counter()
for f in ev:
    for o in f[4].split('、'):
        ops[o.split('約')[0] if o.startswith('傾き') else o] += 1
nunit = len(BK['srow'])
rows = []
for a, p in zip(BK['ans'], BK['prow']):
    tags = Counter(t for s in a['S'] for t in s[4])
    rows.append(f'| {a["id"]} | {p[2]} | {p[1]} | {len(a["S"])} | {p[4]} | {p[5]} | {"、".join(f"{k}{v}" for k, v in tags.items()) or "-"} |')
DT = ST['DT']

md = f'''# 購買プロセス 検証データ（小）

内部監査手続をAIで評価する仕組みの検証用データです。会社名・人名・番号・口座はすべて架空です。

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

## 2. 販売プロセス版との違い（手続の種類）

販売プロセス版は「証跡を見て、承認や一致を確かめる」手続が中心でした。今回は手続の種類を広げています。

| 種類 | 手続 | 求められること |
|---|---|---|
| 全件の突合（データ → 証憑） | P01 | Excelのログから対象を自分で抽出し、申請書がそろっているか確かめる |
| 再計算 | P02・P06 | 見積金額や支払額を計算し直す（税込・税抜の換算、相殺を含む） |
| 閲覧（承認の確認） | P03 | 金額に応じた承認者の印を確かめる（販売版と同じ型。比較用） |
| 全件データ分析 | P04 | 約5,000行の発注データから、条件に合う発注の組を探す |
| 再実施 | P05 | 注文書・検収報告書・請求書の照合を自分でやり直す |
| 外部確認の結果の検討 | P07 | 仕入先の回答と帳簿の差異について、原因と裏付けを確かめる |
| 再集計（網羅性） | P08 | 残高一覧を並べ替え、確認対象が正しく選ばれているか確かめる |
| 分析的手続 | P09 | 仕入明細を月別に集計し直し、増減率と基準への当てはめを確かめる |
| ウォークスルー | P10 | 取引1件を依頼から支払まで追い、業務記述書どおりか確かめる |
| 質問と裏付け | P11 | 口頭の回答が資料で裏付けられるか確かめる |
| アクセス権の検査 | P12 | 画面の写しと人事異動一覧を突き合わせる |
| 自動統制の確認 | P13 | 設定画面とテスト結果の画面を確かめる |

## 3. 題材

- 会社：アオバ機工販売株式会社（産業部品の卸売、3月決算、仕入は検収基準）
- 評価対象期間：2025年4月1日〜2026年3月31日
- 統制 11、手続 13、判定の単位 {nunit}
- 共通資料のデータ（Excel）：発注データ {len(DT["porows"]):,} 行、仕入明細 {len(DT["sirows"]):,} 行、仕入先台帳 60社、買掛金残高一覧 60社、仕入先マスタ変更ログ {len(DT["LOG"])} 行
- サンプル数は小規模版として縮小（都度の統制は4件、月次は3か月分）

## 4. 正解の内訳

| 手続 | 種類 | 統制 | 単位数 | 正解（A_難版） | 正解（B_対照版） | 仕込み（件数） |
|---|---|---|---|---|---|---|
{chr(10).join(rows)}

- 手続単位の正解：単位に「不備あり」が1件でもあれば「不備あり」。なければ、「判断できない」が1件でもあれば「判断できない」。
- 正解の単位：サンプルのある手続はサンプルごと。全件が対象の手続（P01・P04）は「検出すべき対象」ごと。
- 仕込みの種類
  - 不備（5件）：承認のない口座変更、見積比較表の転記誤り、分割発注の見逃し、基準を超える増減の原因記載漏れ、異動者の権限の残存
  - ひっかけ：不備に見えるが正常（選定理由書のある最安値以外の選定、税込表示の見積、分納、単価改定、相殺、未達・値引・未回答、基準未満の増減、特権ID など）
  - 判読不能：人でも読めない箇所が判定に必要な箇所にある（A のみ。B では「不備なし」）
  - 証跡の不足：回答を裏付ける資料が提出されていない（A・B 共通で「判断できない」）
  - 文字情報の罠：PDFから取り出せる文字情報が画像と異なる（A のみ）

## 5. 可読性（A_難版）

証跡 {len(ev)} ファイル（手続一覧と共通資料を除く）の内訳：

| 段階 | 状態 | ファイル数 |
|---|---|---|
| 1 | 問題なく読める | {st[1]} |
| 2 | 読みにくいが人は読める | {st[2]} |
| 3 | 人でも読めない箇所がある | {st[3]}（うち判定に影響あり {imp}） |

文字情報（プログラムでの取得）の内訳（全 {len(fr)} ファイル）：

| 種類 | ファイル数 |
|---|---|
{chr(10).join(f"| {k} | {v} |" for k, v in lay.most_common())}

- 形式：{"、".join(f"{k} {v}" for k, v in ext.most_common())}
- 画質の加工（重複あり）：{"、".join(f"{k} {v}" for k, v in ops.most_common() if not k.startswith("加工なし"))}
- 参考：一般的な文字読取ソフト（tesseract 日本語）で主要項目が読めた割合は、A_難版 {ra:.0%}、B_対照版 {rb:.0%}。難しさの目安です。
- 段階2の主要項目（金額・日付・印影など）は、拡大して人が読めることを目視で確認しています。段階3の箇所と判定への影響は、正解表の「ファイル別の可読性」に記載しています。
- 共通資料のExcel（発注データなど）は、A・B とも加工していません。全件データの分析そのものの正しさを見るためです。

## 6. 使い方

1. `A_難版/` の `手続一覧.xlsx` と証跡一式を検証対象に入力し、手続ごと・単位ごとの判定を得る。
2. `B_対照版/` でも同じことを行う。
3. `正解/正解表.xlsx`（または `正解.json`）と突き合わせる。見るべき点：
   - 不備の見逃し（不備あり → 不備なし）。特に、自分で対象を探す必要がある P01・P04・P09
   - 指摘しすぎ（ひっかけを不備と判定）
   - 「判断できない」と言うべき場面で断定していないか（判読不能、裏付資料の不足）
   - 文字情報の罠に引っかかっていないか（画像を見ずに文字情報だけで判定していないか）
   - 計算の誤り（再計算・再集計の結果そのものが合っているか）

## 7. 前提と制約

- P01・P04・P08・P09 は、Excelのデータを集計・抽出しないと判定できません。検証対象が表計算やプログラムを実行できない場合、この4手続は「読み取り」や「判断」とは別の理由で誤る可能性があります。結果を分けて見てください。
- P01 の申請書・依頼書は「会社が保管する全件」という前提です（手続一覧の「前提」シートに記載）。申請書がない変更は「不備あり」が正解です。
- 営業日は、土日・祝日と 12/29〜1/2 を除く日です（手続一覧の「前提」シートに記載）。
- 発注データの単価は最新（単価改定後）の値です。P05 の S3 の注文書（控）は発行時点の単価のままです。
- 仕入先台帳の口座は期末時点（変更後）の内容です。
- 金額は、発注・仕入・月次実績が税抜、請求・支払・買掛金残高が税込です。
- ファイル名は内容が分かる名前にしています（例：`04_S1_請求書.pdf`）。無関係な資料の混入はありません。
- 「人でも読めない」の線引きは作成者の目視によります。利用時に見直す余地があります。
- 印影は対照版でも画像です（文字情報には入りません）。
- 文書に埋め込んだフォントは SIL Open Font License のもの（BIZ UDゴシック／明朝、Yomogi、Zen Kurenaido、Klee One、DotGothic16）です。

## 8. 検証の記録

- 正解は、証跡に印字した値とExcelのデータから独立に再計算した結果と、{nunit} 単位すべて一致することを確認しています（分割発注の組は発注データ全件から抽出し直し、月次の増減は仕入明細から集計し直しています）。
- ひっかけが意図どおり成立していること（例：請求単価が注文書と異なり、注文変更書と一致する）を確認しています。
- 対照版PDFの文字情報に主要項目の値が含まれること、難版の「文字情報の罠」が実際に取り出せることを確認しています。
- 全ファイルが開けること、A と B のファイルが1対1で対応することを確認しています。
'''
open(f'{OUT}/README.md', 'w', encoding='utf-8').write(md)

# 生成スクリプト
sd_ = f'{OUT}/生成スクリプト（参考）'
shutil.rmtree(sd_, ignore_errors=True)
os.makedirs(sd_)
for f in ('common.py', 'render.py', 'degrade.py', 'build.py', 'data_p.py', 'docs_p.py', 'docs_p2.py', 'screens_p.py', 'build_p.py', 'ocr_ref.py', 'book_p.py', 'verify_p.py', 'pack_p.py'):
    shutil.copy(f'{ROOT}/src/{f}', sd_)
open(f'{sd_}/実行方法.txt', 'w', encoding='utf-8').write(
    '実行順: build_p.py → ocr_ref.py 購買プロセス_検証データ_小 tmp_p（任意）→ book_p.py → verify_p.py → pack_p.py\n'
    '共通部品: common.py（暦・書式）、render.py（文書の描画）、degrade.py（画質の加工）、build.py（難版・対照版の出力）は販売プロセス版と共通\n'
    '必要なもの: Python 3.11以降、reportlab / pymupdf / pillow / numpy / opencv-python-headless / openpyxl、tesseract（ocr_ref.py のみ）\n'
    'フォント: Google Fonts の BIZ UDGothic(Regular/Bold)、BIZ UDMincho、Yomogi、Klee One、Zen Kurenaido、DotGothic16 を fonts/ に置く\n'
    '注意: 作業フォルダのパス（common.py の ROOT）は環境に合わせて書き換えること。乱数の種は固定のため、同じ内容が再生成される\n'
    '注意: book_p.py を実行し直した後は、正解表.xlsx の「集計」シートの数式を表計算ソフトで再計算すること\n'
    '規模の拡張: data_p.py のサンプル定義と build_p.py の加工の割り当て表（plans）を増やす\n')

# プレビュー
base = f'{OUT}/A_難版/'
items = [('01_仕入先マスタ変更/01_変更依頼書_S030.jpg', 0, '粗い＋汚れ（口座番号が読めない）'), ('02_見積比較・発注/02_S3_見積比較表.jpg', 0, '撮影（転記誤りの不備）'),
         ('03_発注一覧レビュー/03_発注レビュー記録_2025年度第2四半期.pdf', 2, 'うねり＋傾き（見逃しの不備）'), ('04_検収・請求照合/04_S4_検収報告書.pdf', 0, '複写伝票＋水濡れ（判読不能）'),
         ('06_残高確認/06_残高確認回答書_S004.pdf', 0, '濃い複写＋傾き（差異の回答）'), ('07_月次購買実績/07_月次購買実績報告書_2026-02.pdf', 0, '濃い複写（増減率の不備）'),
         ('10_システム権限・設定/10_利用者権限一覧_1.jpg', 0, '画面をスマホで撮影（権限の不備）'), ('08_ウォークスルー/08_フローチャート.jpg', 0, '撮影（フローチャート）')]
W = 560
f = ImageFont.truetype(fp('B'), 25)
ims = []
for p, pg, cap in items:
    if p.endswith('.pdf'):
        pm = fitz.open(base + p)[pg].get_pixmap(dpi=80)
        im = Image.frombytes('RGB', (pm.w, pm.h), pm.samples)
    else:
        im = Image.open(base + p).convert('RGB')
    im = im.resize((W, int(im.height * W / im.width)))
    c = Image.new('RGB', (W, 800), 'white')
    c.paste(im.crop((0, 0, W, min(im.height, 756))), (0, 44))
    d = ImageDraw.Draw(c)
    d.rectangle((0, 0, W, 42), fill=(30, 40, 70))
    d.text((10, 8), cap, font=f, fill='white')
    ims.append(c)
sheet = Image.new('RGB', (W * 4 + 30, 800 * 2 + 10), (120, 120, 120))
for i, c in enumerate(ims):
    sheet.paste(c, ((i % 4) * (W + 10), (i // 4) * 810))
sheet.save(f'{ROOT}/out/プレビュー_購買_難版の例.png')

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
print(md[md.index('## 4.'):md.index('## 6.')])
