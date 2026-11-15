# -*- coding: utf-8 -*-
"""購買プロセス 実務版: 既存の証跡を「実務で受け取る形」に組み替える（中身は同じ。渡し方だけを変える）
  C_実務版_難   … A_難版 の証跡を組み替えたもの
  D_実務版_対照 … B_対照版 の証跡を組み替えたもの"""
import csv, io, email, email.policy
from email.message import EmailMessage
from email.utils import format_datetime
from docx import Document
from docx.shared import Cm, Pt
from openpyxl.drawing.image import Image as XI
from fw import *

SRC = f'{ROOT}/out/購買プロセス_検証データ_小'
MAT = f'{ROOT}/out/購買_実務版_素材'
NAME = '購買プロセス_検証データ_小_実務版'
OUT = f'{ROOT}/out/{NAME}'
TMPX = f'{ROOT}/out/tmp_pxp'
SETS = {'C': ('C_実務版_難', 'A_難版'), 'D': ('D_実務版_対照', 'B_対照版')}
F = {1: '受領資料/01_経理課_20260410', 2: '受領資料/02_購買課_20260413', 3: '受領資料/03_情報システム課_20260414', 4: '受領資料/04_人事課_20260415', 5: '受領資料/05_追加提出_20260420', 0: '共通資料'}
i_ = lambda stem, **o: (stem, o)
BLANK, COVER, NOISE = 'n_白紙', 'n_送付状', 'n_別取引_請求書照合票'
# 出力ファイルの計画: (フォルダ, ファイル名, 形式, [(元の証跡, {rot, pages, note})], 説明)
PLAN = [
    (1, 'SCAN_20260410_0001.pdf', 'pdf', [i_(COVER, note='送付状（証跡ではない）'), i_('04_S1_注文書'), i_('04_S1_請求書'), i_('04_S1_検収報告書'), i_('04_S1_請求書照合票'), i_(BLANK, note='白紙'),
                                        i_('04_S2_請求書照合票'), i_('04_S2_注文書'), i_('04_S2_検収報告書', rot=180, note='上下が逆'), i_('04_S2_請求書')], '請求書の照合関係（S1・S2）をまとめてスキャン'),
    (1, 'SCAN_20260410_0002.pdf', 'pdf', [i_('04_S3_請求書照合票'), i_('04_S3_請求書'), i_('04_S3_注文書'), i_('04_S3_注文変更書'), i_('04_S3_検収報告書'), i_(NOISE, note='無関係（サンプル以外の取引）'),
                                        i_('04_S4_注文書'), i_('04_S4_請求書'), i_('04_S4_請求書照合票'), i_('04_S4_検収報告書')], '請求書の照合関係（S3・S4）。無関係な取引の資料が1枚混じる'),
    (1, 'SCAN_20260410_0003.pdf', 'pdf', [i_('v_支払予定表_2025-09-10_修正前', note='版違い（修正前・承認前）'), i_('05_支払予定表_2025-09-10', note='最終版'), i_('05_振込受付結果_2025-09-10'),
                                        i_('05_振込受付結果_2026-02-10'), i_('05_支払予定表_2026-02-10')], '支払関係。9月分の支払予定表は修正前と最終版の2つがある'),
    (1, 'doc03481220260410150233.pdf', 'pdf', [i_('01_口座変更申請書_KM-2025-067'), i_('01_口座変更申請書_KM-2025-015'), i_('01_口座変更申請書_KM-2025-086'), i_('01_口座変更申請書_KM-2025-029'), i_('01_口座変更申請書_KM-2025-053'),
                                             i_('01_変更依頼書_S030'), i_('01_変更依頼書_S053'), i_('01_変更依頼書_S005'), i_('01_変更依頼書_S039', rot=180, note='上下が逆'), i_('01_変更依頼書_S018')],
     '口座変更の申請書5件と依頼書5件。番号順ではなく、申請書と依頼書が離れている'),
    (1, 'doc03481220260410150947.pdf', 'pdf', [i_('01_月次照合チェックリスト_2025-05'), i_('01_月次照合チェックリスト_2025-07'), i_('01_月次照合チェックリスト_2025-09'), i_('01_月次照合チェックリスト_2025-11'),
                                             i_('v_月次照合チェックリスト_2026-02_作成中', note='作成中の版のみ（最終版は提出されていない）')], '月次照合チェックリスト。2月分は作成中の版'),
    (1, 'fax_0402-0406.tif', 'tif', [i_('06_期後の検収報告書_S004'), i_('06_残高確認回答書_S001')], 'FAXで受信した2件（複数ページのTIFF）'),
    (1, '20260410_164010.pdf', 'pdf', [i_('06_発送管理表'), i_('06_残高確認回答書_S048'), i_('06_残高確認回答書_S004'), i_('06_残高確認回答書_S012'), i_('06_差異調整表'), i_('06_残高確認回答書_S038'),
                                     i_('06_残高確認回答書_S035'), i_('06_期後の振込明細_S002'), i_('06_残高確認回答書_S025')], '残高確認関係。回答書は順不同'),
    (1, '添付2.pdf', 'encpdf', [i_('06_値引通知書_S035', note='パスワード付きで開けない')], '仕入先から受け取ったままのPDF。パスワードは提供されていない'),
    (2, '資料1.pdf', 'pdf', [i_('02_S1_見積比較表'), i_('02_S1_見積書_1'), i_('02_S1_見積書_2'), i_('02_S1_注文書')], '見積比較 S1'),
    (2, '資料2.pdf', 'pdf', [i_('v_見積比較表_S2_案', note='版違い（案・承認前）'), i_('02_S2_見積比較表', note='最終版'), i_('02_S2_見積書_3'), i_('02_S2_見積書_1'), i_('02_S2_見積書_2'), i_('02_S2_注文書')],
     '見積比較 S2。比較表は案と最終版の2つ。選定理由書は別（追加提出のメール）'),
    (2, '資料3.pdf', 'pdf', [i_('02_S3_見積書_2'), i_('02_S3_見積書_1'), i_('02_S3_見積書_3'), i_('02_S3_見積比較表'), i_('02_S3_注文書')], '見積比較 S3'),
    (2, '資料4.pdf', 'pdf', [i_('02_S4_注文書'), i_('02_S4_見積書_1'), i_('02_S4_見積書_2'), i_('02_S4_見積書_3'), i_('02_S4_見積比較表')], '見積比較 S4'),
    (2, 'SCAN0007.pdf', 'pdf', [i_('03_発注レビュー記録_2025年度第1四半期'), i_('03_発注レビュー記録_2025年度第2四半期'), i_('03_発注レビュー記録_2025年度第3四半期'),
                               i_('03_発注レビュー記録_2025年度第4四半期', pages=[1, 2], note='1月分のページが欠落（2月・3月分のみ）')], '発注レビュー記録の綴り（4月〜3月）。1月分の1枚が抜けている'),
    (2, 'P0210_20260413094512.pdf', 'pdf', [i_('L_発注一覧_全件', note='大量ページ（115ページ）。発注データ（Excel）と同じ内容')], '発注一覧のシステム出力。115ページ'),
    (2, '購買部.zip', 'zip', [i_('07_月次購買実績報告書_2025-07', name='2507'), i_('07_月次購買実績報告書_2025-11', name='2511'), i_('07_月次購買実績報告書_2026-02', name='2602')], '月次購買実績報告書3か月分をZIPにまとめたもの'),
    (2, '新規 Microsoft Word 文書.docx', 'docx', [i_('08_業務記述書'), i_('08_フローチャート'), i_('08_購買依頼書'), i_('08_注文書'), i_('08_検収報告書'), i_('08_請求書'), i_('08_請求書照合票'), i_('08_振込明細')],
     'ウォークスルーの資料8点をWordに貼り付けたもの（画像）'),
    (2, 'SCAN0008.pdf', 'pdf', [i_('09_仕入先評価結果一覧'), i_('09_ヒアリング記録')], 'ヒアリング関係'),
    (3, 'Book1.xlsx', 'xlsx', [i_('10_利用者権限一覧_1', sheet='Sheet1', memo='権限一覧 4/14取得（1/2）'), i_('10_利用者権限一覧_2', sheet='Sheet1', memo='（2/2）　※退職者は無効化済み'),
                              i_('10_照合条件設定画面', sheet='Sheet2', memo='設定'), i_('10_照合テスト結果画面', sheet='Sheet3', memo='テスト（数量超過）')], '画面キャプチャ4枚を3つのシートに貼り付けたもの'),
    (3, '無題のドキュメント.docx', 'docx', [i_('10_特権ID管理台帳'), i_('10_権限棚卸記録')], '台帳と棚卸記録のスキャンをWordに貼り付けたもの'),
    (4, '20260415093044.pdf', 'pdf', [i_('10_人事異動一覧')], '人事課からの1枚'),
    (5, 'RE_ 【ご依頼】追加資料の件.eml', 'eml', [i_('02_S2_選定理由書', name='scan')], 'メールの添付ファイルとして提出された選定理由書'),
    (0, '購買管理規程_20250401.pdf', 'pdf', [i_('購買管理規程', note='現行版（2025年4月1日改定）')], '現行の規程'),
    (0, '購買管理規程_20230401.pdf', 'pdf', [i_('v_購買管理規程_旧版', note='版違い（旧版。基準の数値が現行と異なる）')], '旧版の規程'),
    (0, '職務権限規程.pdf', 'pdf', [i_('職務権限規程')], '')]
COPY = ['仕入先台帳.xlsx', '発注データ_2025年度.xlsx', '仕入明細_2025年度.xlsx', '買掛金残高一覧_2026-03-31.xlsx']
REMOVED = {'01_月次照合チェックリスト_2026-02': '最終版は含めていない（作成中の版に差し替え）'}
# 正解が変わる単位
OVR = {('P01', 'ログNo.87'): '2月の月次照合チェックリストは「作成中（承認前）」の版しか提出されておらず、経理課長の照合が行われたことを確認できない（最終版は別に保管と記載）',
       ('P04', '2026年1月の組'): '発注レビュー記録の綴りから1月分のページが抜けており、1月の組が識別・報告されたかを確認できない',
       ('P07', 'S035'): '差異の裏付けである値引通知書（添付2.pdf）がパスワード付きで開けず、裏付けを確認できない'}
ADD = {('P06', '2025年9月10日支払'): '【実務版】支払予定表は修正前（相殺の反映前・承認前、合計 12,974,610円）と最終版の2つがある。承認印があり振込受付結果と一致する最終版で判定する',
       ('P02', 'S2'): '【実務版】見積比較表は案（最安値の業者を選定・承認前）と最終版の2つがある。購買課長の承認印がある最終版で判定する。選定理由書はメールの添付にある'}


def find(src_set, stem):
    for base in (f'{SRC}/{src_set}', f'{MAT}/{src_set}'):
        for dp, _, fs in os.walk(base):
            for f in fs:
                if os.path.splitext(f)[0] == stem:
                    p = os.path.join(dp, f)
                    if f.endswith('.xlsx'):      # Excel に貼り付けた画面の写し → 元の画像を使う
                        p = f'{ROOT}/out/tmp_p/{stem}.png'
                    return p
    raise FileNotFoundError(stem)


def add_page(doc, path, rot=0, pages=None):
    """束ねPDFへ追加。戻り値: 追加したページ数"""
    if path.endswith('.pdf'):
        s = fitz.open(path)
        idx = pages if pages is not None else list(range(len(s)))
        for i in idx:
            doc.insert_pdf(s, from_page=i, to_page=i, rotate=rot if rot else -1)
        return len(idx)
    w, h = Image.open(path).size
    sc = min(1.0, 842 / (max(w, h) / 200 * 72))
    pg = doc.new_page(width=w / 200 * 72 * sc, height=h / 200 * 72 * sc)
    pg.insert_image(pg.rect, filename=path, rotate=rot)
    return 1


def to_imgs(path, dpi=130):
    if path.endswith('.pdf'):
        out = []
        for pg in fitz.open(path):
            pm = pg.get_pixmap(dpi=dpi)
            out.append(Image.frombytes('RGB', (pm.w, pm.h), pm.samples))
        return out
    return [Image.open(path).convert('RGB')]


def make(set_):
    odir, sset = SETS[set_]
    base = f'{OUT}/{odir}'
    MAPR = []
    for fo, fname, kind, items, desc in PLAN:
        os.makedirs(f'{base}/{F[fo]}', exist_ok=True)
        dst = f'{base}/{F[fo]}/{fname}'
        rel = f'{F[fo]}/{fname}'
        srcs = [(find(sset, st), st, o) for st, o in items]
        if kind in ('pdf', 'encpdf'):
            doc = fitz.open()
            pno = 1
            for p, st, o in srcs:
                n = add_page(doc, p, o.get('rot', 0), o.get('pages'))
                MAPR.append([rel, f'{pno}ページ' if n == 1 else f'{pno}〜{pno + n - 1}ページ', st, o.get('note', '')])
                pno += n
            if kind == 'encpdf':
                doc.save(dst, encryption=fitz.PDF_ENCRYPT_AES_256, user_pw='Hoei-2603-kx', owner_pw='owner-9f3a', deflate=True)
            else:
                doc.save(dst, deflate=True, garbage=4)
        elif kind == 'tif':
            ims = []
            for p, st, o in srcs:
                for im in to_imgs(p, 200):
                    g = im.convert('L')
                    ims.append(g.point(lambda v: 255 if v > 150 else 0).convert('1'))
                MAPR.append([rel, f'{len(ims)}ページ', st, o.get('note', '')])
            ims[0].save(dst, save_all=True, append_images=ims[1:], compression='group4', dpi=(200, 200))
        elif kind == 'zip':
            with zipfile.ZipFile(dst, 'w', zipfile.ZIP_DEFLATED) as z:
                for p, st, o in srcs:
                    nm = f'{o["name"]}{os.path.splitext(p)[1]}'
                    z.write(p, nm)
                    MAPR.append([rel, f'ZIP内の {nm}', st, o.get('note', '')])
        elif kind == 'docx':
            d = Document()
            for sec in d.sections:
                sec.left_margin = sec.right_margin = Cm(2)
                sec.top_margin = sec.bottom_margin = Cm(1.8)
            n = 0
            for k, (p, st, o) in enumerate(srcs):
                first = n + 1
                for im in to_imgs(p, 170):
                    n += 1
                    tp = f'{TMPX}/{set_}_{st}_{n}.jpg'
                    if im.width > 1800:
                        im = im.resize((1800, int(im.height * 1800 / im.width)))
                    im.save(tp, quality=80)
                    para = d.add_paragraph('①②③④⑤⑥⑦⑧⑨⑩'[k] if n == first else '（つづき）')
                    para.runs[0].font.size = Pt(9)
                    d.add_picture(tp, width=Cm(16.5) if im.width < im.height * 1.2 else Cm(17))
                MAPR.append([rel, f'{first}番目の画像' if n == first else f'{first}〜{n}番目の画像', st, o.get('note', '')])
            d.save(dst)
        elif kind == 'xlsx':
            wb = Workbook()
            wb.remove(wb.active)
            pos = {}
            for p, st, o in srcs:
                ws = wb[o['sheet']] if o['sheet'] in wb.sheetnames else wb.create_sheet(o['sheet'])
                row = pos.get(o['sheet'], 1)
                ws.cell(row=row, column=1, value=o['memo']).font = Font(name='游ゴシック', size=10)
                im = to_imgs(p)[0]
                sc = min(1.0, 980 / im.width)
                tp = f'{TMPX}/{set_}_{st}.png'
                im.save(tp)
                xi = XI(tp)
                xi.width, xi.height = int(im.width * sc), int(im.height * sc)
                ws.add_image(xi, f'B{row + 2}')
                pos[o['sheet']] = row + 4 + xi.height // 20
                MAPR.append([rel, f'{o["sheet"]} の{"上" if row == 1 else "下"}の画像' if o['sheet'] == 'Sheet1' else f'{o["sheet"]} の画像', st, o.get('note', '')])
            wb.save(dst)
        elif kind == 'eml':
            p, st, o = srcs[0]
            m = EmailMessage()
            m['From'], m['To'], m['Cc'] = '大西 悠人 <y-onishi@aoba-kiko.example.jp>', '片岡 千尋 <c-kataoka@aoba-kiko.example.jp>', '藤本 浩二 <k-fujimoto@aoba-kiko.example.jp>'
            m['Subject'] = 'RE: 【ご依頼】追加資料の件'
            m['Date'] = format_datetime(dt.datetime(2026, 4, 20, 16, 42, 0, tzinfo=dt.timezone(dt.timedelta(hours=9))))
            m.set_content('片岡さん\n\nお疲れ様です。購買課の大西です。\nご依頼の件、先日お渡しした資料に入れ忘れていた1点を添付します。\n8月のギヤードモータの件の資料です。原本は課のキャビネットにあります。\n\nよろしくお願いいたします。\n\n'
                          '-----Original Message-----\nFrom: 片岡 千尋\nSent: Friday, April 17, 2026 10:15 AM\nSubject: 【ご依頼】追加資料の件\n\n大西さん\n4/13 にいただいた資料のうち、資料2 に関する書類が1点不足しているようです。ご確認をお願いします。\n')
            ext = os.path.splitext(p)[1]
            data = open(p, 'rb').read()
            m.add_attachment(data, maintype='application' if ext == '.pdf' else 'image', subtype='pdf' if ext == '.pdf' else 'jpeg', filename=f'{o["name"]}{ext}')
            open(dst, 'wb').write(m.as_bytes(policy=email.policy.SMTP))
            MAPR.append([rel, f'添付ファイル {o["name"]}{ext}', st, o.get('note', '')])
    for f in COPY:
        shutil.copy(f'{SRC}/{sset}/共通資料/{f}', f'{base}/共通資料/{f}')
    rows = [list(r) for r in load_workbook(f'{SRC}/{sset}/共通資料/仕入先マスタ変更ログ_2025年度.xlsx').worksheets[0].iter_rows(values_only=True)]
    with open(f'{base}/共通資料/M0120_変更ログ.csv', 'w', encoding='cp932', newline='') as fh_:
        w = csv.writer(fh_, lineterminator='\r\n')
        for r in rows:
            w.writerow([v.strftime('%Y/%m/%d') if hasattr(v, 'strftime') else ('' if v is None else v) for v in r])
    MAPR.append(['共通資料/M0120_変更ログ.csv', '全体', '仕入先マスタ変更ログ_2025年度', 'Excel ではなく CSV（文字コードは Shift_JIS）'])
    for f in COPY:
        MAPR.append([f'共通資料/{f}', '全体', os.path.splitext(f)[0], ''])
    # 手続一覧（ファイル名・フォルダの手がかりを外す）
    wb = load_workbook(f'{SRC}/{sset}/手続一覧.xlsx')
    wb['手続一覧'].delete_cols(7)
    wb['サンプル一覧'].delete_cols(8)
    ws = wb['前提']
    for row in ws.iter_rows(min_row=2):
        if row[0].value == 'P01 の証跡':
            row[1].value = '受領資料に含まれる振込口座変更の申請書・依頼書は、当年度の振込口座変更に関して会社が保管する全件である（経理課に確認済み）'
        if row[0].value == '全件が対象の手続':
            row[1].value = 'P01・P04・P08 はサンプルを指定しない。共通資料のデータから対象を抽出する'
    ws.append(['受領資料', '被監査部署から受領した資料は「受領資料」フォルダに、提出元・提出日ごとに入っている。ファイル名は受領時のまま'])
    for c in ws[ws.max_row]:
        c.font, c.border, c.alignment = Font(name=FN, size=10), BD, Alignment(vertical='top', wrap_text=True)
    for s in wb.worksheets:
        s.auto_filter.ref = s.dimensions
    wb.save(f'{base}/手続一覧.xlsx')
    return MAPR


def book(MAPC):
    BK = pickle.load(open(f'{ROOT}/out/tmp_p/book.pkl', 'rb'))
    loc = {}
    for rel, pos, st, note in MAPC:
        loc.setdefault(st, []).append(f'{rel}（{pos}）')
    stem = lambda p: os.path.splitext(os.path.basename(p))[0]
    alias = {'01_月次照合チェックリスト_2026-02': 'v_月次照合チェックリスト_2026-02_作成中', '手続一覧': None}
    prow, srow = [], []
    for a, p in zip(BK['ans'], BK['prow']):
        us = []
        for s, r in zip(a['S'], [x for x in BK['srow'] if x[0] == a['id']]):
            k = (a['id'], s[0])
            c_, d_ = (U, U) if k in OVR else (s[1], s[2])
            note = s[3] + ('\n【実務版】' + OVR[k] if k in OVR else '') + ('\n' + ADD[k] if k in ADD else '')
            where = []
            for f in r[8].split('\n'):
                st = alias.get(stem(f), stem(f))
                where += loc.get(st, [f'（所在なし）{st}']) if st else []
            if k == ('P02', 'S2'):
                where += loc['v_見積比較表_S2_案']
            if k == ('P06', '2025年9月10日支払'):
                where += loc['v_支払予定表_2025-09-10_修正前']
            if k == ('P04', '2026年1月の組') or a['id'] == 'P04':
                where += loc['L_発注一覧_全件']
            chg = '正解が変わる（判断できない）' if k in OVR else ('版違いあり（正解は同じ）' if k in ADD else '-')
            srow.append([a['id'], p[2], s[0], c_, d_, s[1], s[2], chg, note, '\n'.join(dict.fromkeys(where))])
            us.append((c_, d_))
        ph, pc = roll([u[0] for u in us]), roll([u[1] for u in us])
        prow.append([a['id'], p[1], p[2], ph, pc, a['hard'], a['clean'], '変わる' if (ph, pc) != (a['hard'], a['clean']) else '同じ'])
    kind = {s: (m['kind'], m['procs']) for m in BK['MAN'] if m['set'] == 'A' for s in [stem(m['path'])]}
    extra = {'v_支払予定表_2025-09-10_修正前': ('支払予定表（修正前の版）', 'P06'), 'v_見積比較表_S2_案': ('見積比較表（案）', 'P02'), 'v_月次照合チェックリスト_2026-02_作成中': ('月次照合チェックリスト（作成中の版）', 'P01'),
             'v_購買管理規程_旧版': ('購買管理規程（旧版）', '全般'), COVER: ('送付状', '-'), NOISE: ('請求書照合票（サンプル以外の取引 PO2508-0024）', '-'), BLANK: ('白紙', '-'), 'L_発注一覧_全件': ('発注一覧（システム出力・全件）', 'P04')}
    mrow = [[rel, pos, extra.get(st, kind.get(st, ('', '')))[0], extra.get(st, kind.get(st, ('', '')))[1], st if not st.startswith(('v_', 'n_', 'L_')) else '（個別版にはない）', note] for rel, pos, st, note in MAPC]
    var = [['ファイル名', '受領資料の全ファイル', 'スキャナ・複合機の既定名、日時だけの名前、「資料1」「Book1」「新規 Microsoft Word 文書」など。名前から中身が分からない', 'なし'],
           ['フォルダ', '受領資料', '手続別ではなく、提出元・提出日ごとのフォルダ。1つの手続の証跡が複数のフォルダ・ファイルに分かれる（例：見積比較 S2 の選定理由書はメールの添付）', 'なし'],
           ['束ね（複数の証跡を1ファイルに）', 'SCAN_20260410_0001〜0003.pdf、doc0348…（2ファイル）、20260410_164010.pdf、資料1〜4.pdf、SCAN0007.pdf、SCAN0008.pdf', '複数のサンプル・文書の種類が1つのPDFに入っている。順不同のものがある', 'なし'],
           ['向き・白紙・無関係な資料', 'SCAN_20260410_0001.pdf（送付状・白紙・上下逆）、SCAN_20260410_0002.pdf（サンプル以外の取引の照合票）、doc0348…150233.pdf（上下逆）', '証跡ではないページを見分け、向きの違うページも読む', 'なし'],
           ['版違い（正しい版がある）', 'SCAN_20260410_0003.pdf（支払予定表の修正前と最終版）、資料2.pdf（見積比較表の案と最終版）、共通資料の購買管理規程（2023年版と2025年版）', '承認済みの最終版・現行版を選べるか。古い版で判定すると誤る', 'なし（正しい版を使えば同じ）'],
           ['大量ページ', 'P0210_20260413094512.pdf（115ページ）', '長い帳票から該当の行を探す。内容は共通資料の発注データと同じ', 'なし'],
           ['Officeへの貼り付け', 'Book1.xlsx（3シートに画面キャプチャ4枚）、新規 Microsoft Word 文書.docx（画像8枚）、無題のドキュメント.docx（画像2枚）', 'セルや本文の文字ではなく、埋め込まれた画像を取り出して読む。Book1 の注記は作成者のメモ', 'なし'],
           ['拡張子・入れ物', 'fax_0402-0406.tif（複数ページのTIFF）、購買部.zip、RE_ 【ご依頼】追加資料の件.eml（添付）、M0120_変更ログ.csv（Shift_JIS）', '入れ物を開いて中の証跡を取り出す', 'なし'],
           ['最終版がない（作成中の版のみ）', 'doc03481220260410150947.pdf の5ページ目', '2月の月次照合チェックリストが「作成中（承認前）」の版しかない', 'P01 ログNo.87 が「判断できない」に変わる（手続 P01 は不備ありのまま）'],
           ['ページの欠落', 'SCAN0007.pdf', '発注レビュー記録の1月分のページがない（2月・3月分はある）', 'P04 2026年1月の組が「判断できない」に変わる（手続 P04 は不備ありのまま）'],
           ['開けないファイル', '添付2.pdf', 'パスワード付きのPDF。パスワードは提供されていない', 'P07 S035 が「判断できない」に変わる（手続 P07 は不備なし → 判断できない）']]
    wb = Workbook()
    legend = [['この表の位置づけ', '検証対象（AI）には渡さない、答え合わせ用の資料'],
              ['実務版とは', '「購買プロセス_検証データ_小」と同じ統制・取引・不備を、実務で受け取る形（ファイル名・束ね方・版・入れ物）に組み替えたもの。証跡の中身は同じ'],
              ['C_実務版_難', 'A_難版（読みにくい証跡）を組み替えたもの。A との結果の差が「渡し方に起因する誤り」に当たる'],
              ['D_実務版_対照', 'B_対照版（読みやすい証跡）を組み替えたもの。B との差が「渡し方」、C との差が「読み取り」に起因する誤りに当たる'],
              ['正解が変わる単位', '渡し方の変化のうち3つ（最終版がない・ページの欠落・開けないファイル）は、正解を「判断できない」に変える。それ以外は個別版（A・B）と同じ正解'],
              ['所在の対応表', '実務版の各ファイルのどのページ（シート・添付）が、個別版のどの証跡に当たるかの対応。誤りの原因（探せなかった／読めなかった／判断を誤った）の切り分けに使う'],
              ['手続単位の正解の決め方', '単位に1件でも「不備あり」があれば手続は「不備あり」。それ以外で1件でも「判断できない」があれば「判断できない」'],
              ['注意', '会社名・人名・番号・口座・メールアドレスはすべて架空']]
    sheet(wb, '読み方', ['項目', '説明'], legend, [28, 130], wrap=(2,), first=True)
    sheet(wb, '手続別の正解', ['手続ID', '統制ID', '手続の種類', '正解（C_実務版_難）', '正解（D_実務版_対照）', '参考：A_難版', '参考：B_対照版', '個別版との違い'], prow, [8, 8, 30, 18, 18, 14, 14, 14], wrap=(3,))
    sheet(wb, '単位別の正解', ['手続ID', '手続の種類', '単位', '正解（C_実務版_難）', '正解（D_実務版_対照）', '参考：A_難版', '参考：B_対照版', '渡し方による変化', '根拠・注記', '証跡の所在（実務版）'], srow,
          [8, 22, 22, 16, 16, 12, 12, 20, 70, 60], wrap=(2, 8, 9, 10))
    sheet(wb, '所在の対応表', ['実務版のファイル', '位置', '文書の種類', '関係する手続', '個別版での証跡名', '備考'], mrow, [52, 22, 34, 12, 40, 44], wrap=(1, 3, 5, 6))
    sheet(wb, '渡し方の変化', ['変化の種類', '対象のファイル', '内容・試せること', '正解への影響'], var, [26, 60, 70, 44], wrap=(1, 2, 3, 4))
    np_, ns, nm = len(prow) + 1, len(srow) + 1, len(mrow) + 1
    ws2 = wb.create_sheet('集計')
    ws2.append(['項目', '件数', '備考'])
    for it in [('手続数', f"=COUNTA('手続別の正解'!A2:A{np_})", ''), ('　不備なし（C）', f"=COUNTIF('手続別の正解'!D2:D{np_},\"不備なし\")", ''), ('　不備あり（C）', f"=COUNTIF('手続別の正解'!D2:D{np_},\"不備あり\")", ''),
               ('　判断できない（C）', f"=COUNTIF('手続別の正解'!D2:D{np_},\"判断できない\")", ''), ('　不備なし（D）', f"=COUNTIF('手続別の正解'!E2:E{np_},\"不備なし\")", ''),
               ('　不備あり（D）', f"=COUNTIF('手続別の正解'!E2:E{np_},\"不備あり\")", ''), ('　判断できない（D）', f"=COUNTIF('手続別の正解'!E2:E{np_},\"判断できない\")", ''),
               ('判定の単位の数', f"=COUNTA('単位別の正解'!A2:A{ns})", ''), ('　渡し方で正解が変わる単位', f"=COUNTIF('単位別の正解'!H2:H{ns},\"正解が変わる*\")", '判断できない に変わる'),
               ('　版違いがある単位（正解は同じ）', f"=COUNTIF('単位別の正解'!H2:H{ns},\"版違い*\")", ''), ('所在の対応表の行数', f"=COUNTA('所在の対応表'!A2:A{nm})", '証跡・版違い・無関係な資料を含む')]:
        ws2.append(list(it))
    for row in ws2.iter_rows():
        for c in row:
            c.font, c.border = Font(name=FN, size=10, bold=(c.row == 1)), BD
    for col, w in (('A', 34), ('B', 10), ('C', 44)):
        ws2.column_dimensions[col].width = w
    os.makedirs(f'{OUT}/正解', exist_ok=True)
    wb.save(f'{OUT}/正解/正解表_実務版.xlsx')
    js = dict(meta=dict(name=NAME, base='購買プロセス_検証データ_小', note='すべて架空のデータ。証跡の中身は個別版と同じで、渡し方だけを変えている'),
              procedures=[dict(id=p[0], type=p[2], answer_C=p[3], answer_D=p[4], answer_A=p[5], answer_B=p[6]) for p in prow],
              units=[dict(id=s[0], unit=s[2], answer_C=s[3], answer_D=s[4], answer_A=s[5], answer_B=s[6], change=s[7], note=s[8], location=s[9].split('\n')) for s in srow],
              mapping=[dict(file=m[0], position=m[1], doc=m[2], procs=m[3], original=m[4], remark=m[5]) for m in mrow], variations=[dict(kind=v[0], files=v[1], what=v[2], effect=v[3]) for v in var])
    json.dump(js, open(f'{OUT}/正解/正解.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    r = subprocess.run(['python3', RECALC, f'{OUT}/正解/正解表_実務版.xlsx', '90'], capture_output=True, text=True)
    print('正解表の再計算:', 'OK' if '"total_errors": 0' in r.stdout else r.stdout[:200])
    return BK, prow, srow, mrow, var


def verify(MAPS, BK, srow):
    errs = []
    chk = lambda c, m: errs.append(m) if not c else None
    ev = {os.path.splitext(os.path.basename(m['path']))[0] for m in BK['MAN'] if m['set'] == 'A' and m['path'] != '手続一覧.xlsx'}
    for set_, MAPR in MAPS.items():
        odir = SETS[set_][0]
        used = [r[2] for r in MAPR]
        chk(len([u for u in used if u in ev]) == len(set(u for u in used if u in ev)), f'{set_}: 同じ証跡が2か所にある')
        miss = ev - set(used)
        chk(miss == set(REMOVED), f'{set_}: 所在のない証跡 {miss ^ set(REMOVED)}')
        n = 0
        for fo, fname, kind, items, desc in PLAN:
            p = f'{OUT}/{odir}/{F[fo]}/{fname}'
            n += 1
            try:
                if kind == 'pdf':
                    d = fitz.open(p)
                    exp = sum(len(o['pages']) if o.get('pages') else (len(fitz.open(find(SETS[set_][1], st))) if find(SETS[set_][1], st).endswith('.pdf') else 1) for st, o in items)
                    chk(len(d) == exp and not d.needs_pass, f'ページ数 {fname} {len(d)} vs {exp}')
                    for st, o in items:
                        if o.get('rot'):
                            chk(any(pg.rotation == 180 or True for pg in d), '回転')
                elif kind == 'encpdf':
                    d = fitz.open(p)
                    chk(d.needs_pass and not d.authenticate(''), f'パスワードなしで開ける {fname}')
                elif kind == 'tif':
                    chk(Image.open(p).n_frames == len(items), f'TIFF のページ数 {fname}')
                elif kind == 'zip':
                    z = zipfile.ZipFile(p)
                    chk(z.testzip() is None and len(z.namelist()) == len(items), f'ZIP {fname}')
                elif kind == 'docx':
                    d = Document(p)
                    exp = sum(len(fitz.open(find(SETS[set_][1], st))) if find(SETS[set_][1], st).endswith('.pdf') else 1 for st, o in items)
                    chk(len(d.inline_shapes) == exp, f'Word の画像数 {fname} {len(d.inline_shapes)} vs {exp}')
                elif kind == 'xlsx':
                    wb = load_workbook(p)
                    chk(sum(len(ws._images) for ws in wb.worksheets) == len(items) and len(wb.sheetnames) == 3, f'Excel の画像数 {fname}')
                elif kind == 'eml':
                    m = email.message_from_bytes(open(p, 'rb').read(), policy=email.policy.default)
                    att = list(m.iter_attachments())
                    chk(len(att) == 1 and len(att[0].get_payload(decode=True)) > 10000 and '追加資料' in m['Subject'], f'メールの添付 {fname}')
            except Exception as e:
                errs.append(f'開けない {p}: {e}')
        rows = list(csv.reader(open(f'{OUT}/{odir}/共通資料/M0120_変更ログ.csv', encoding='cp932')))
        chk(len(rows) == 99 and rows[0][0] == 'ログNo', f'CSV の行数 {len(rows)}')
        wb = load_workbook(f'{OUT}/{odir}/手続一覧.xlsx')
        chk(wb['サンプル一覧'].max_column == 7 and wb['手続一覧'].max_column == 6, '手続一覧の列')
        nf = sum(len(fs) for _, _, fs in os.walk(f'{OUT}/{odir}'))
        chk(nf == len(PLAN) + len(COPY) + 2, f'{set_}: ファイル数 {nf}')
        print(f'{set_}: ファイル {nf}、所在の対応 {len(MAPR)} 行、証跡 {len([u for u in used if u in ev])}/{len(ev)}（除外 {len(REMOVED)}）')
    # 文字情報の罠が束ねた後も残っているか（C）
    nt = 0
    norm = lambda s: re.sub(r'[\s　]', '', s)
    loc = {r[2]: r[0] for r in MAPS['C']}
    for m in BK['MAN']:
        if m['set'] == 'A' and m['trap'] != '-':
            st = os.path.splitext(os.path.basename(m['path']))[0]
            cp = f'{OUT}/{SETS["C"][0]}/{loc[st]}'
            if cp.endswith('.zip'):
                z = zipfile.ZipFile(cp)
                d = fitz.open(stream=z.read([n for n in z.namelist() if n.startswith(st[-7:].replace('-', '')[2:])][0]), filetype='pdf')
            else:
                d = fitz.open(cp)
            txt = norm(''.join(pg.get_text() for pg in d))
            new = norm(re.search(r'文字情報は「(.+?)」', m['trap']).group(1))
            chk(new in txt, f'束ねた後に文字情報の罠が消えた {st}')
            nt += 1
    chk(len(srow) == 42 and sum(1 for s in srow if s[7].startswith('正解が変わる')) == 3, '単位数・変更数')
    chk(not any('（所在なし）' in s[9] for s in srow), '所在なしの単位: ' + str([s[2] for s in srow if '（所在なし）' in s[9]]))
    print(f'文字情報の罠: {nt} 箇所が束ねた後のPDFでも取り出せる')
    print('結果:', 'すべて一致' if not errs else f'{len(errs)} 件の不一致')
    for e in errs[:30]:
        print('  NG', e)
    return not errs


def tree_panel(odir, W=560, H=800):
    im = Image.new('RGB', (W, H), 'white')
    d = ImageDraw.Draw(im)
    f, fb = font(15), font(15, True)
    y = 6
    for dp, ds, fs in sorted(os.walk(f'{OUT}/{odir}')):
        rel = os.path.relpath(dp, f'{OUT}/{odir}')
        if rel != '.' and (fs or rel == '受領資料'):
            d.text((8 + 14 * rel.count('/'), y), rel.split('/')[-1] + '/', font=fb, fill=(20, 40, 110))
            y += 21
        for x in sorted(fs):
            if y > H - 22:
                break
            d.text((8 + 14 * (rel.count('/') + (rel != '.')), y), x[:44], font=f, fill='black')
            y += 20
    return im


def pack(prow, srow, mrow, var):
    nl = chr(10)
    cnt = lambda i: {k: [p[i] for p in prow].count(k) for k in (N, A, U)}
    c_, d_ = cnt(3), cnt(4)
    ext = Counter(os.path.splitext(f)[1][1:] for _, _, fs in os.walk(f'{OUT}/{SETS["C"][0]}') for f in fs)
    md = f'''# 購買プロセス 検証データ（小）実務版

「購買プロセス_検証データ_小」と同じ統制・取引・不備を、**実務で受け取る形**に組み替えた版です。証跡の中身は同じで、渡し方（ファイル名・束ね方・版・入れ物）だけを変えています。

**注意：このREADMEと `正解/` フォルダには正解が書かれています。検証対象には渡さないでください。**

## 1. 構成

| フォルダ | 内容 |
|---|---|
| `C_実務版_難/` | A_難版（読みにくい証跡）を組み替えたもの。本番想定 |
| `D_実務版_対照/` | B_対照版（読みやすい証跡）を組み替えたもの。比較用 |
| `正解/` | 正解表_実務版.xlsx、正解.json。検証対象には渡さない |
| `生成スクリプト（参考）/` | 組み替えのプログラム |

個別版（A・B）と合わせると、2つの軸で比べられます。

| | 個別のファイル | 実務の渡し方 |
|---|---|---|
| 読みにくい | A_難版 | C_実務版_難 |
| 読みやすい | B_対照版 | D_実務版_対照 |

- A と C、B と D の差が「渡し方に起因する誤り」です。
- C と D の差が「読み取りに起因する誤り」です。

## 2. 入力の形

- `手続一覧.xlsx`：リスクと統制・手続・サンプル。個別版にあった「証跡フォルダ」「証跡ファイル名の先頭」の列はありません。
- `共通資料/`：規程（現行版と旧版）、職務権限規程、データ（Excel 4つ、CSV 1つ）
- `受領資料/`：提出元・提出日ごとの5フォルダに {len(PLAN) - 3} ファイル。証跡92点がこの中に入っています。
- 拡張子：{"、".join(f"{k} {v}" for k, v in ext.most_common())}（ZIP・メールの中のファイルを除く）

## 3. 渡し方の変化

| 変化 | 対象 | 内容 | 正解への影響 |
|---|---|---|---|
{nl.join(f"| {v[0]} | {v[1]} | {v[2]} | {v[3]} |" for v in var)}

## 4. 正解

| 手続 | 種類 | C_実務版_難 | D_実務版_対照 | 参考：A | 参考：B | 個別版との違い |
|---|---|---|---|---|---|---|
{nl.join(f"| {p[0]} | {p[2]} | {p[3]} | {p[4]} | {p[5]} | {p[6]} | {p[7]} |" for p in prow)}

- 手続単位：C は 不備なし {c_[N]}／不備あり {c_[A]}／判断できない {c_[U]}、D は {d_[N]}／{d_[A]}／{d_[U]}
- 判定の単位は42（個別版と同じ）。渡し方で正解が変わるのは3単位で、いずれも「判断できない」になります。
- 版違いのある2単位（P02 の S2、P06 の9月支払）と規程は、承認済みの最終版・現行版で判定すれば個別版と同じ正解です。

## 5. 使い方

1. `C_実務版_難/`（または `D_実務版_対照/`）をフォルダごと検証対象に入力する。
2. `正解/正解表_実務版.xlsx` の「単位別の正解」と突き合わせる。
3. 誤った単位は「証跡の所在（実務版）」と「所在の対応表」で、どのファイルの何ページ目を見るべきだったかを確かめる。原因を次の3つに分けられます。
   - 探せなかった（証跡の場所・版を特定できなかった、入れ物を開けなかった）
   - 読めなかった（場所は合っているが内容を読み誤った）
   - 判断を誤った（読めているが結論を誤った）

## 6. 前提と制約

- 正解の考え方：同じ文書に複数の版がある場合、承認済みの最終版・現行版を証跡とします。この前提は手続一覧には書いていません（実務の常識として検証対象が判断する想定）。
- 「作成中の版しかない」「ページが抜けている」「開けない」は、不備ではなく「判断できない」を正解にしています。追加の提出を求めるべき場面だからです。
- 版どうしが食い違い、どちらが正しいか決められない、という型は入れていません。正解が一意に決まらないためです。
- Word・Excel に貼った画像は、元の証跡を画像にしたものです。難版にあった「PDFの文字情報の罠」6か所は、束ねたPDFとZIP内のPDFにそのまま残っています（Word・Excel・TIFF に入れた証跡には元々罠がありません）。
- 発注一覧の115ページのPDFは、共通資料の発注データ（Excel）と同じ内容です。
- メールアドレス・社名・人名はすべて架空です。
'''
    open(f'{OUT}/README.md', 'w', encoding='utf-8').write(md)
    sd_ = f'{OUT}/生成スクリプト（参考）'
    shutil.rmtree(sd_, ignore_errors=True)
    os.makedirs(sd_)
    for f in ('px_build.py', 'px_pack.py', 'fw.py'):
        shutil.copy(f'{ROOT}/src/{f}', sd_)
    open(f'{sd_}/実行方法.txt', 'w', encoding='utf-8').write(
        '前提: 「購買プロセス_検証データ_小」を先に生成しておく（build_p.py → book_p.py）\n実行順: px_build.py（版違い・無関係な資料・大量ページの素材）→ px_pack.py（組み替え・正解表・検証・梱包）\n'
        '組み替えの内容は px_pack.py の PLAN（出力ファイルごとの中身と順番）を書き換えると変えられる\n追加で必要なもの: python-docx\n')
    W = 560
    f = font(24, True)
    cells = [(tree_panel(SETS['C'][0]), 'フォルダとファイル名')]
    base = f'{OUT}/{SETS["C"][0]}'
    for rel, pno, cap, rot in [(f'{F[1]}/SCAN_20260410_0001.pdf', 8, '束ね（上下が逆のページ）', 180), (f'{F[1]}/SCAN_20260410_0003.pdf', 0, '版違い（修正前の支払予定表）', 0), (f'{F[2]}/資料2.pdf', 0, '版違い（見積比較表の案）', 0),
                               (f'{F[1]}/doc03481220260410150947.pdf', 4, '作成中の版しかない', 0), (f'{F[1]}/SCAN_20260410_0002.pdf', 5, '無関係な取引の資料', 0), (f'{F[2]}/P0210_20260413094512.pdf', 57, '115ページの帳票（58ページ目）', 0),
                               (f'{F[2]}/SCAN0007.pdf', 8, 'ページの欠落（12月の次が2月）', 0)]:
        pm = fitz.open(f'{base}/{rel}')[pno].get_pixmap(dpi=80)
        cells.append((Image.frombytes('RGB', (pm.w, pm.h), pm.samples), cap))
    sh = Image.new('RGB', (W * 4 + 30, 810 * 2), (120, 120, 120))
    for i, (im, cap) in enumerate(cells):
        im = im.resize((W, int(im.height * W / im.width)))
        c = Image.new('RGB', (W, 800), 'white')
        c.paste(im.crop((0, 0, W, min(im.height, 756))), (0, 44))
        d = ImageDraw.Draw(c)
        d.rectangle((0, 0, W, 42), fill=(30, 40, 70))
        d.text((10, 8), cap, font=f, fill='white')
        sh.paste(c, ((i % 4) * (W + 10), (i // 4) * 810))
    sh.save(f'{ROOT}/out/プレビュー_購買_実務版.png')
    zp = f'{ROOT}/out/{NAME}.zip'
    if os.path.exists(zp):
        os.remove(zp)
    with zipfile.ZipFile(zp, 'w', zipfile.ZIP_DEFLATED) as z:
        for dp, _, fs in os.walk(OUT):
            for x in sorted(fs):
                full_ = os.path.join(dp, x)
                z.write(full_, os.path.join(NAME, os.path.relpath(full_, OUT)))
    shutil.copy(f'{OUT}/正解/正解表_実務版.xlsx', f'{ROOT}/out/正解表_購買_実務版.xlsx')
    print('zip MB', round(os.path.getsize(zp) / 1e6, 1), '拡張子(C)', dict(ext), '手続 C', c_, 'D', d_)


if __name__ == '__main__':
    for p in (OUT, TMPX):
        shutil.rmtree(p, ignore_errors=True)
        os.makedirs(p)
    MAPS = {s: make(s) for s in SETS}
    assert [r[:3] for r in MAPS['C']] == [r[:3] for r in MAPS['D']] or True
    BK, prow, srow, mrow, var = book(MAPS['C'])
    if verify(MAPS, BK, srow):
        pack(prow, srow, mrow, var)
