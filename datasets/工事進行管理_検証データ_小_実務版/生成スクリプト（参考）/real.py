# -*- coding: utf-8 -*-
"""実務版の共通エンジン: 既存の証跡を「実務で受け取る形」に組み替える（中身は同じ。渡し方だけを変える）
  C_実務版_難 … A_難版 を組み替えたもの／D_実務版_対照 … B_対照版 を組み替えたもの
  セットごとの計画は r_<key>.py（R という辞書）に書く"""
import csv, email, email.policy
from email.message import EmailMessage
from email.utils import format_datetime
from docx import Document
from docx.shared import Cm, Pt
from openpyxl.drawing.image import Image as XI
from fw import *

MM = 72 / 25.4
SETS = {'C': ('C_実務版_難', 'A_難版'), 'D': ('D_実務版_対照', 'B_対照版')}
i_ = lambda stem, **o: (stem, o)
BLANK, COVER = 'n_白紙', 'n_送付状'
FONTKEY = [('Bold', 'B'), ('Gothic', 'G'), ('Mincho', 'M'), ('Yomogi', 'H'), ('Klee', 'K'), ('Kurenaido', 'Z'), ('Dot', 'D')]
TORN = ('torn', (0, 264, 118, 297), False, '下端の余白')


class V:
    """加工済みのPDFを emit に渡すための入れ物"""

    def __init__(s, path):
        s.path, s.boxes, s.kv = path, {}, {}
        s.pno = len(fitz.open(path)) - 1


def stamps(path, pn=0):
    """ページ内の印影（画像）の位置。左上から順"""
    pg = fitz.open(path)[pn]
    rs = [r for im in pg.get_images(full=True) for r in pg.get_image_rects(im[0])]
    return sorted(rs, key=lambda r: (round(r.y0 / 80), r.x0))


def edit_pdf(src, dst, edits=(), strip=(), mark=None, at=(120, 14), msz=13, drop=()):
    """対照版のPDFを加工して別の版を作る: 文字の書き換え、印影の消去、注記の追加、ページの削除"""
    doc = fitz.open(src)
    edits = [(tuple(e) + (False,))[:3] for e in edits]      # (元の文字, 新しい文字, 完全一致のみ)
    hit = {old: 0 for old, _, _ in edits}
    for pg in doc:
        todo = []
        for old, new, exact in edits:
            for b in pg.get_text('dict')['blocks']:
                for l in b.get('lines', []):
                    for sp in l['spans']:
                        if (sp['text'].strip() == old) if exact else (old in sp['text']):
                            pg.add_redact_annot(fitz.Rect(sp['bbox']), fill=False)
                            todo.append((sp['origin'], sp['size'], sp['text'].replace(old, new), sp['font'], sp['color']))
                            hit[old] += 1
        if todo:
            pg.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE, graphics=0)
            for org, size, text, fn, col in todo:
                k = next((v for s_, v in FONTKEY if s_ in fn), 'G')
                pg.insert_text(org, text, fontsize=size, fontname='f' + k, fontfile=fp(k), color=[((col >> 16) & 255) / 255, ((col >> 8) & 255) / 255, (col & 255) / 255])
    assert all(hit.values()), f'書き換え対象が見つからない {hit}'
    st = stamps(src)
    for i in strip:
        r = st[i]
        doc[0].draw_rect(fitz.Rect(r.x0 - 1, r.y0 - 1, r.x1 + 1, r.y1 + 1), color=None, fill=(1, 1, 1))
    if mark:
        doc[0].insert_text((at[0] * MM, at[1] * MM), mark, fontsize=msz, fontname='fB', fontfile=fp('B'), color=(0.75, 0.05, 0.05))
    for pn in sorted(drop, reverse=True):
        doc.delete_page(pn)
    doc.save(dst)
    return V(dst)


def simple_cover(path, to, frm, date, lines):
    g, y = form(path, '資料送付のご案内', who=[to, date, frm],
                rows=[('gap', 8), ('txt', 'ご依頼のありました資料を、下記のとおり送付いたします。原本は当部署で保管しています。', 10.5), ('gap', 4),
                      ('tbl', [('No', 14, 'c'), ('資料', 120, 'l'), ('枚数', 52, 'c')], [[str(i + 1), a, b] for i, (a, b) in enumerate(lines)], dict(rh=10, sz=10.5)), ('gap', 4),
                      ('txt', '※ スキャンの都合上、順番が前後しているものがあります。ご了承ください。', 9.5)])
    return g.save()


def blank_page(path):
    g = Pg(path, seed=9)
    g.ln(5, 5, 5.02, 5.02, 0.01, col=(1, 1, 1))
    return g.save()


def table_print(path, title, cols, rows, per=45, rh=4.05, sz=7.2, land=True, foot=''):
    """大量ページの帳票（システムからの出力）"""
    n = (len(rows) + per - 1) // per
    g = Pg(path, land=land, seed=5)
    for pi in range(n):
        if pi:
            g.newpage()
        g.t(12, 10, title, 9, 'B')
        g.t(g.W - 12, 10, f'{pi + 1} / {n} ページ', 8, al='r')
        part = rows[pi * per:(pi + 1) * per]
        g.tbl(12, 13, cols, part, rh, sz, hh=5, hsz=7.5, lw=0.2)
        if pi == n - 1 and foot:
            g.t(12, 13 + 5 + len(part) * rh + 5, foot, 8.5, 'B')
    return g.save()


# ---------------- 組み替え ----------------
def find(R, src_set, stem):
    for base in (f'{ROOT}/out/{R["src"]}/{src_set}', f'{ROOT}/out/{R["src"]}_素材/{src_set}'):
        for dp, _, fs in os.walk(base):
            for f in fs:
                if os.path.splitext(f)[0] == stem:
                    p = os.path.join(dp, f)
                    if f.endswith('.xlsx') and stem in R.get('ximg', ()):      # Excel に貼り付けた画面の写し → 元の画像を使う
                        p = f'{ROOT}/out/{R["tmp"]}/{stem}.png'
                    return p
    raise FileNotFoundError(stem)


def add_page(doc, path, rot=0, pages=None):
    if path.endswith('.pdf'):
        s = fitz.open(path)
        idx = pages if pages is not None else list(range(len(s)))
        for i in idx:
            doc.insert_pdf(s, from_page=i, to_page=i, rotate=rot if rot else -1)
        return len(idx)
    if path.endswith(('.log', '.txt')):     # テキストは印刷した形（等幅）でページにする
        tp = path + '.print.pdf'
        logpdf(tp, os.path.basename(path), open(path, encoding='utf-8').read().splitlines(), per=60, sz=8)
        return add_page(doc, tp, rot, pages)
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


def npages(p):
    return len(fitz.open(p)) if p.endswith('.pdf') else 1


def make(R, set_):
    odir, sset = SETS[set_]
    OUT, TMPX, F = f'{ROOT}/out/{R["name"]}', f'{ROOT}/out/tmp_r_{R["key"]}', R['F']
    base = f'{OUT}/{odir}'
    MAPR = []
    for fo, fname, kind, items, desc in R['PLAN']:
        os.makedirs(f'{base}/{F[fo]}', exist_ok=True)
        dst, rel = f'{base}/{F[fo]}/{fname}', f'{F[fo]}/{fname}'
        srcs = [(find(R, sset, st), st, o) for st, o in items]
        if kind in ('pdf', 'encpdf'):
            doc, pno = fitz.open(), 1
            for p, st, o in srcs:
                n = add_page(doc, p, o.get('rot', 0), o.get('pages'))
                MAPR.append([rel, f'{pno}ページ' if n == 1 else f'{pno}〜{pno + n - 1}ページ', st, o.get('note', '')])
                pno += n
            if kind == 'encpdf':
                doc.save(dst, encryption=fitz.PDF_ENCRYPT_AES_256, user_pw='Kx-2603-' + R['key'], owner_pw='owner-9f3a', deflate=True)
            else:
                doc.save(dst, deflate=True, garbage=4)
        elif kind == 'copy':
            p, st, o = srcs[0]
            shutil.copy(p, dst)
            MAPR.append([rel, '全体', st, o.get('note', '')])
        elif kind == 'tif':
            ims = []
            for p, st, o in srcs:
                a = len(ims)
                for im in to_imgs(p, 200):
                    ims.append(im.convert('L').point(lambda v: 255 if v > 150 else 0).convert('1') if o.get('bw', True) else im.convert('L'))
                MAPR.append([rel, f'{a + 1}ページ' if len(ims) == a + 1 else f'{a + 1}〜{len(ims)}ページ', st, o.get('note', '')])
            ims[0].save(dst, save_all=True, append_images=ims[1:], compression='group4' if ims[0].mode == '1' else 'tiff_deflate', dpi=(200, 200))
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
                    para = d.add_paragraph(o.get('cap', '①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳'[k]) if n == first else '（つづき）')
                    para.runs[0].font.size = Pt(9)
                    d.add_picture(tp, width=Cm(16.5) if im.width < im.height * 1.2 else Cm(17))
                MAPR.append([rel, f'{first}番目の画像' if n == first else f'{first}〜{n}番目の画像', st, o.get('note', '')])
            d.save(dst)
        elif kind == 'xlsx':
            wb = Workbook()
            wb.remove(wb.active)
            pos, cnt = {}, {}
            for p, st, o in srcs:
                ws = wb[o['sheet']] if o['sheet'] in wb.sheetnames else wb.create_sheet(o['sheet'])
                row = pos.get(o['sheet'], 1)
                cnt[o['sheet']] = cnt.get(o['sheet'], 0) + 1
                ws.cell(row=row, column=1, value=o.get('memo', '')).font = Font(name='游ゴシック', size=10)
                for im in to_imgs(p, 150):
                    sc = min(1.0, 980 / im.width)
                    tp = f'{TMPX}/{set_}_{st}_{row}.png'
                    im.save(tp)
                    xi = XI(tp)
                    xi.width, xi.height = int(im.width * sc), int(im.height * sc)
                    ws.add_image(xi, f'B{row + 2}')
                    row += 4 + xi.height // 20
                pos[o['sheet']] = row
                MAPR.append([rel, f'{o["sheet"]} の{cnt[o["sheet"]]}番目の画像', st, o.get('note', '')])
            wb.save(dst)
        elif kind == 'eml':
            ml = R['EML'][fname]
            m = EmailMessage()
            m['From'], m['To'], m['Subject'] = ml['frm'], ml['to'], ml['subject']
            m['Date'] = format_datetime(ml['date'].replace(tzinfo=dt.timezone(dt.timedelta(hours=9))))
            m.set_content(ml['body'])
            for p, st, o in srcs:
                ext = os.path.splitext(p)[1]
                m.add_attachment(open(p, 'rb').read(), maintype='application' if ext == '.pdf' else 'image', subtype='pdf' if ext == '.pdf' else ext[1:].replace('jpg', 'jpeg'), filename=f'{o["name"]}{ext}')
                MAPR.append([rel, f'添付ファイル {o["name"]}{ext}', st, o.get('note', '')])
            open(dst, 'wb').write(m.as_bytes(policy=email.policy.SMTP))
    os.makedirs(f'{base}/共通資料', exist_ok=True)
    for f in R.get('COPY', ()):
        shutil.copy(f'{ROOT}/out/{R["src"]}/{sset}/共通資料/{f}', f'{base}/共通資料/{f}')
        MAPR.append([f'共通資料/{f}', '全体', os.path.splitext(f)[0], ''])
    for xf, cf in R.get('CSV', ()):
        rows = [list(r) for r in load_workbook(f'{ROOT}/out/{R["src"]}/{sset}/共通資料/{xf}').worksheets[0].iter_rows(values_only=True)]
        with open(f'{base}/共通資料/{cf}', 'w', encoding='cp932', newline='') as fh_:
            w = csv.writer(fh_, lineterminator='\r\n')
            for r in rows:
                w.writerow([v.strftime('%Y/%m/%d') if hasattr(v, 'strftime') else ('' if v is None else v) for v in r])
        MAPR.append([f'共通資料/{cf}', '全体', os.path.splitext(xf)[0], 'Excel ではなく CSV（文字コードは Shift_JIS。先頭のシートのみ）'])
    wb = load_workbook(f'{ROOT}/out/{R["src"]}/{sset}/手続一覧.xlsx')      # 手続一覧: ファイル名・フォルダの手がかりを外す
    for ws in wb.worksheets:
        for c in range(ws.max_column, 0, -1):
            h = str(ws.cell(row=1, column=c).value or '')
            if 'フォルダ' in h or 'ファイル' in h:
                ws.delete_cols(c)
        if ws.title == '前提':
            for row in ws.iter_rows(min_row=2):
                if row[0].value in R.get('PREM', {}):
                    row[1].value = R['PREM'][row[0].value]
            ws.append(['受領資料', '被監査部署から受領した資料は「受領資料」フォルダに、提出元・提出日ごとに入っている。ファイル名は受領時のまま'])
            for c in ws[ws.max_row]:
                c.font, c.border, c.alignment = Font(name=FN, size=10), BD, Alignment(vertical='top', wrap_text=True)
        ws.auto_filter.ref = ws.dimensions
    wb.save(f'{base}/手続一覧.xlsx')
    return MAPR


# ---------------- 正解表 ----------------
def norm_book(R):
    BK = pickle.load(open(f'{ROOT}/out/{R["tmp"]}/book.pkl', 'rb'))
    out = []
    for a, p in zip(BK['ans'], BK['prow']):
        rs = [x for x in BK['srow'] if x[0] == a['id']]
        if R.get('fmt') == 'sales':
            us = [dict(unit=r[1], hard=r[3], clean=r[4], note=r[6], files=r[7]) for r in rs]
            out.append(dict(id=a['id'], ctl=p[1], type=R.get('TYPE', {}).get(a['id'], '閲覧・突合'), hard=p[3], clean=p[4], units=us))
        else:
            us = [dict(unit=r[2], hard=r[4], clean=r[5], note=r[7], files=r[8]) for r in rs]
            out.append(dict(id=a['id'], ctl=p[1], type=p[2], hard=p[4], clean=p[5], units=us))
    return BK, out


def variations(R):
    P = R['PLAN']
    fl = lambda cond: '、'.join(dict.fromkeys(f for _, f, k, items, _ in P if cond(k, items))) or '-'
    has = lambda w: (lambda k, items: any(w in o.get('note', '') for _, o in items))
    eff = lambda w: '；'.join(f'{k[0]} {k[1]} が「判断できない」に変わる' for k, v in R['OVR'].items() if v[0] == w) or 'なし'
    var = [['ファイル名', '受領資料の全ファイル', 'スキャナ・複合機の既定名、日時だけの名前、「資料1」「Book1」など。名前から中身が分からない', 'なし'],
           ['フォルダ', '受領資料', '手続別ではなく、提出元・提出日ごとのフォルダ。1つの手続の証跡が複数のフォルダ・ファイルに分かれる', 'なし'],
           ['束ね（複数の証跡を1ファイルに）', fl(lambda k, items: k == 'pdf' and len(items) > 1), '複数のサンプル・文書の種類が1つのPDFに入っている。順不同のものがある', 'なし'],
           ['向き・白紙・送付状・無関係な資料', fl(lambda k, items: any(w in o.get('note', '') for _, o in items for w in ('上下が逆', '白紙', '送付状', '無関係'))), '証跡ではないページを見分け、向きの違うページも読む', 'なし'],
           ['版違い（正しい版がある）', fl(has('版違い')), '承認済みの最終版・現行版を選べるか。古い版・案で判定すると誤る', 'なし（正しい版を使えば同じ）'],
           ['大量ページ', fl(has('大量ページ')), '長い資料から該当の箇所を探す', 'なし'],
           ['Officeへの貼り付け', fl(lambda k, items: k in ('docx', 'xlsx')), 'セルや本文の文字ではなく、埋め込まれた画像を取り出して読む', 'なし'],
           ['拡張子・入れ物', fl(lambda k, items: k in ('tif', 'zip', 'eml')) + ''.join(f'、{c}' for _, c in R.get('CSV', ())), '入れ物（TIFF・ZIP・メールの添付・CSV）を開いて中の証跡を取り出す', 'なし'],
           ['最終版がない（作成中の版のみ）', fl(has('作成中の版のみ')), '「作成中（承認前）」の版しか提出されていない', eff('draft')],
           ['ページの欠落', fl(has('欠落')), '綴りや複数ページの資料から必要なページが抜けている', eff('missing')],
           ['開けないファイル', fl(has('開けない')), 'パスワード付きのPDF。パスワードは提供されていない', eff('locked')]]
    return [v for v in var if v[1] != '-']


def book(R, MAPC):
    OUT = f'{ROOT}/out/{R["name"]}'
    BK, PR = norm_book(R)
    loc = {}
    for rel, pos, st, note in MAPC:
        loc.setdefault(st, []).append(f'{rel}（{pos}）')
    stem = lambda p: os.path.splitext(os.path.basename(p))[0]
    prow, srow = [], []
    for p in PR:
        us = []
        for u in p['units']:
            k = (p['id'], u['unit'])
            c_, d_ = (U, U) if k in R['OVR'] else (u['hard'], u['clean'])
            note = u['note'] + ('\n【実務版】' + R['OVR'][k][1] if k in R['OVR'] else '') + ('\n【実務版】' + R['ADD'][k][0] if k in R.get('ADD', {}) else '')
            where = []
            for f in u['files'].split('\n'):
                st0 = stem(f)
                if st0 == '手続一覧':
                    continue
                st = R.get('REPL', {}).get(st0, st0)
                if st in loc:
                    where += loc[st]
                elif st0 in R.get('REMOVED', {}):
                    where.append(f'（提出なし）{st0}：{R["REMOVED"][st0]}')
                else:
                    where.append(f'（所在なし）{st}')
            for st in (R['ADD'][k][1] if k in R.get('ADD', {}) else []) + R.get('ALSO', {}).get(p['id'], []) + R.get('ALSO', {}).get(k, []):
                where += loc[st]
            chg = '正解が変わる（判断できない）' if k in R['OVR'] else ('版違いあり（正解は同じ）' if k in R.get('ADD', {}) else '-')
            srow.append([p['id'], p['type'], u['unit'], c_, d_, u['hard'], u['clean'], chg, note, '\n'.join(dict.fromkeys(where))])
            us.append((c_, d_))
        ph, pc = roll([x[0] for x in us]), roll([x[1] for x in us])
        prow.append([p['id'], p['ctl'], p['type'], ph, pc, p['hard'], p['clean'], '変わる' if (ph, pc) != (p['hard'], p['clean']) else '同じ'])
    kind = {stem(m['path']): (m['kind'], m['procs']) for m in BK['MAN'] if m['set'] == 'A'}
    ex = dict({COVER: ('送付状（証跡ではない）', '-'), BLANK: ('白紙', '-')}, **R.get('EXTRA', {}))
    mrow = [[rel, pos, ex.get(st, kind.get(st, ('', '')))[0], ex.get(st, kind.get(st, ('', '')))[1], st if not st.startswith(('v_', 'n_', 'L_')) else '（個別版にはない）', note] for rel, pos, st, note in MAPC]
    var = variations(R)
    wb = Workbook()
    legend = [['この表の位置づけ', '検証対象（AI）には渡さない、答え合わせ用の資料'],
              ['実務版とは', f'「{R["src"]}」と同じ統制・取引・不備を、実務で受け取る形（ファイル名・束ね方・版・入れ物）に組み替えたもの。証跡の中身は同じ'],
              ['C_実務版_難', 'A_難版（読みにくい証跡）を組み替えたもの。A との結果の差が「渡し方に起因する誤り」に当たる'],
              ['D_実務版_対照', 'B_対照版（読みやすい証跡）を組み替えたもの。B との差が「渡し方」、C との差が「読み取り」に起因する誤りに当たる'],
              ['正解が変わる単位', '渡し方の変化のうち「最終版がない・ページの欠落・開けないファイル」は、正解を「判断できない」に変える。それ以外は個別版（A・B）と同じ正解'],
              ['所在の対応表', '実務版の各ファイルのどのページ（シート・添付）が、個別版のどの証跡に当たるかの対応。誤りの原因（探せなかった／読めなかった／判断を誤った）の切り分けに使う'],
              ['手続単位の正解の決め方', '単位に1件でも「不備あり」があれば手続は「不備あり」。それ以外で1件でも「判断できない」があれば「判断できない」'],
              ['注意', '会社名・人名・番号・メールアドレスはすべて架空']]
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
    js = dict(meta=dict(name=R['name'], base=R['src'], note='すべて架空のデータ。証跡の中身は個別版と同じで、渡し方だけを変えている'),
              procedures=[dict(id=p[0], type=p[2], answer_C=p[3], answer_D=p[4], answer_A=p[5], answer_B=p[6]) for p in prow],
              units=[dict(id=s[0], unit=s[2], answer_C=s[3], answer_D=s[4], answer_A=s[5], answer_B=s[6], change=s[7], note=s[8], location=s[9].split('\n')) for s in srow],
              mapping=[dict(file=m[0], position=m[1], doc=m[2], procs=m[3], original=m[4], remark=m[5]) for m in mrow], variations=[dict(kind=v[0], files=v[1], what=v[2], effect=v[3]) for v in var])
    json.dump(js, open(f'{OUT}/正解/正解.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    r = subprocess.run(['python3', RECALC, f'{OUT}/正解/正解表_実務版.xlsx', '90'], capture_output=True, text=True)
    print('正解表の再計算:', 'OK' if '"total_errors": 0' in r.stdout else r.stdout[:200])
    return BK, prow, srow, mrow, var


# ---------------- 検証 ----------------
def verify(R, MAPS, BK, srow):
    OUT = f'{ROOT}/out/{R["name"]}'
    errs = []
    chk = lambda c, m: errs.append(m) if not c else None
    stem = lambda p: os.path.splitext(os.path.basename(p))[0]
    ev = {stem(m['path']) for m in BK['MAN'] if m['set'] == 'A' and m['path'] != '手続一覧.xlsx'}
    for set_, MAPR in MAPS.items():
        odir, sset = SETS[set_]
        used = [r[2] for r in MAPR]
        dup = [u for u, n in Counter(u for u in used if u in ev).items() if n > 1 and u not in R.get('DUP', ())]
        chk(not dup, f'{set_}: 同じ証跡が2か所にある {dup}')
        miss = ev - set(used)
        chk(miss == set(R.get('REMOVED', {})), f'{set_}: 所在のない証跡 {miss ^ set(R.get("REMOVED", {}))}')
        for fo, fname, kind, items, desc in R['PLAN']:
            p = f'{OUT}/{odir}/{R["F"][fo]}/{fname}'
            try:
                exp = sum(len(o['pages']) if o.get('pages') else (npages(find(R, sset, st)) if not find(R, sset, st).endswith(('.log', '.txt')) else None or 0) for st, o in items)
                if kind == 'pdf':
                    d = fitz.open(p)
                    if not any(find(R, sset, st).endswith(('.log', '.txt')) for st, o in items):
                        chk(len(d) == exp and not d.needs_pass, f'ページ数 {fname} {len(d)} vs {exp}')
                elif kind == 'encpdf':
                    d = fitz.open(p)
                    chk(d.needs_pass and not d.authenticate(''), f'パスワードなしで開ける {fname}')
                elif kind == 'tif':
                    chk(Image.open(p).n_frames == exp, f'TIFF のページ数 {fname}')
                elif kind == 'zip':
                    z = zipfile.ZipFile(p)
                    chk(z.testzip() is None and len(z.namelist()) == len(items), f'ZIP {fname}')
                elif kind == 'docx':
                    chk(len(Document(p).inline_shapes) == exp, f'Word の画像数 {fname}')
                elif kind == 'xlsx':
                    wb = load_workbook(p)
                    chk(sum(len(ws._images) for ws in wb.worksheets) == exp, f'Excel の画像数 {fname}')
                elif kind == 'eml':
                    m = email.message_from_bytes(open(p, 'rb').read(), policy=email.policy.default)
                    att = list(m.iter_attachments())
                    chk(len(att) == len(items) and all(len(a.get_payload(decode=True)) > 5000 for a in att), f'メールの添付 {fname}')
                elif kind == 'copy':
                    chk(os.path.getsize(p) > 100, f'空のファイル {fname}')
            except Exception as e:
                errs.append(f'開けない {p}: {e}')
        for xf, cf in R.get('CSV', ()):
            rows = list(csv.reader(open(f'{OUT}/{odir}/共通資料/{cf}', encoding='cp932')))
            chk(len(rows) > 5, f'CSV の行数 {cf}')
        nf = sum(len(fs) for _, _, fs in os.walk(f'{OUT}/{odir}'))
        chk(nf == len(R['PLAN']) + len(R.get('COPY', ())) + len(R.get('CSV', ())) + 1, f'{set_}: ファイル数 {nf}')
        print(f'{set_}: ファイル {nf}、所在の対応 {len(MAPR)} 行、証跡 {len(set(u for u in used if u in ev))}/{len(ev)}（除外 {len(R.get("REMOVED", {}))}）')
    norm = lambda s: re.sub(r'[\s　]', '', s)
    loc = {r[2]: r[0] for r in MAPS['C']}
    kept, lost = 0, []
    for m in BK['MAN']:
        if m['set'] == 'A' and m['trap'] != '-':
            st = stem(m['path'])
            cp = f'{OUT}/{SETS["C"][0]}/{loc[st]}'
            try:
                if cp.endswith('.zip'):
                    z = zipfile.ZipFile(cp)
                    nm = [o['name'] for _, f, k, items, _ in R['PLAN'] if f == os.path.basename(cp) for s2, o in items if s2 == st][0]
                    d = fitz.open(stream=z.read(nm + '.pdf'), filetype='pdf')
                else:
                    d = fitz.open(cp)
                txt = norm(''.join(pg.get_text() for pg in d))
                ok = all(norm(re.search(r'文字情報は「(.+?)」', part).group(1)) in txt for part in m['trap'].split('；'))
            except Exception:
                ok = False
            kept += ok
            if not ok:
                lost.append(st)
    chk(not lost, f'束ねた後に文字情報の罠が消えた {lost}')
    chk(sum(1 for s in srow if s[7].startswith('正解が変わる')) == len(R['OVR']), '正解が変わる単位の数')
    chk(sum(1 for s in srow if s[7].startswith('版違い')) == len([k for k in R.get('ADD', {}) if k not in R['OVR']]), '版違いのある単位の数')
    chk(not any('（所在なし）' in s[9] for s in srow), '所在なしの単位: ' + str([(s[0], s[2]) for s in srow if '（所在なし）' in s[9]]))
    print(f'文字情報の罠: {kept} 箇所が束ねた後も取り出せる')
    print('結果:', 'すべて一致' if not errs else f'{len(errs)} 件の不一致')
    for e in errs[:30]:
        print('  NG', e)
    return not errs


# ---------------- README・プレビュー・ZIP ----------------
def tree_panel(base, W=560, H=800):
    im = Image.new('RGB', (W, H), 'white')
    d = ImageDraw.Draw(im)
    f, fb = font(15), font(15, True)
    y = 6
    for dp, ds, fs in sorted(os.walk(base)):
        rel = os.path.relpath(dp, base)
        if rel != '.' and (fs or rel == '受領資料'):
            d.text((8 + 14 * rel.count('/'), y), rel.split('/')[-1] + '/', font=fb, fill=(20, 40, 110))
            y += 20
        for x in sorted(fs):
            if y < H - 20:
                d.text((8 + 14 * (rel.count('/') + (rel != '.')), y), x[:44], font=f, fill='black')
                y += 19
    return im


def pack(R, prow, srow, mrow, var):
    OUT, nl = f'{ROOT}/out/{R["name"]}', chr(10)
    cnt = lambda i: {k: [p[i] for p in prow].count(k) for k in (N, A, U)}
    c_, d_ = cnt(3), cnt(4)
    base = f'{OUT}/{SETS["C"][0]}'
    ext = Counter(os.path.splitext(f)[1][1:] for _, _, fs in os.walk(base) for f in fs)
    nrec = sum(len(fs) for dp, _, fs in os.walk(f'{base}/受領資料'))
    chg = [s for s in srow if s[7].startswith('正解が変わる')]
    ver = [s for s in srow if s[7].startswith('版違い')]
    md = f'''# {R["title"]} 検証データ（小）実務版

「{R["src"]}」と同じ統制・取引・不備を、**実務で受け取る形**に組み替えた版です。証跡の中身は同じで、渡し方（ファイル名・束ね方・版・入れ物）だけを変えています。

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

- A と C、B と D の差が「渡し方に起因する誤り」です。C と D の差が「読み取りに起因する誤り」です。

## 2. 入力の形

- `手続一覧.xlsx`：リスクと統制・手続・サンプル。個別版にあった証跡のフォルダ・ファイル名の手がかりの列はありません。
- `共通資料/`：規程・基準、データ
- `受領資料/`：提出元・提出日ごとのフォルダに {nrec} ファイル。個別版の証跡はすべてこの中に入っています。
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
- 判定の単位は {len(srow)}（個別版と同じ）。渡し方で正解が変わるのは {len(chg)} 単位（{"、".join(f"{s[0]} {s[2]}" for s in chg)}）で、いずれも「判断できない」になります。
- 版違いのある単位（{"、".join(f"{s[0]} {s[2]}" for s in ver) or "なし"}）は、承認済みの最終版・現行版で判定すれば個別版と同じ正解です。

## 5. 使い方

1. `C_実務版_難/`（または `D_実務版_対照/`）をフォルダごと検証対象に入力する。
2. `正解/正解表_実務版.xlsx` の「単位別の正解」と突き合わせる。
3. 誤った単位は「証跡の所在（実務版）」と「所在の対応表」で、どのファイルの何ページ目を見るべきだったかを確かめる。原因を「探せなかった／読めなかった／判断を誤った」に分けられます。

## 6. 前提と制約

- 同じ文書に複数の版がある場合、承認済みの最終版・現行版を証跡とします。この前提は手続一覧には書いていません（検証対象が判断する想定）。
- 「作成中の版しかない」「ページが抜けている」「開けない」は、不備ではなく「判断できない」を正解にしています。追加の提出を求めるべき場面だからです。
- 版どうしが食い違い、どちらが正しいか決められない、という型は入れていません。正解が一意に決まらないためです。
- Word・Excel に貼った画像は、元の証跡を画像にしたものです。
{nl.join("- " + x for x in R.get("NOTES", []))}
- メールアドレス・社名・人名はすべて架空です。
'''
    open(f'{OUT}/README.md', 'w', encoding='utf-8').write(md)
    sd_ = f'{OUT}/生成スクリプト（参考）'
    shutil.rmtree(sd_, ignore_errors=True)
    os.makedirs(sd_)
    for f in ('real.py', f'r_{R["key"]}.py', 'fw.py'):
        shutil.copy(f'{ROOT}/src/{f}', sd_)
    open(f'{sd_}/実行方法.txt', 'w', encoding='utf-8').write(
        f'前提: 「{R["src"]}」を先に生成しておく\n実行: python r_{R["key"]}.py（素材の生成 → 組み替え → 正解表 → 検証 → 梱包）\n'
        f'組み替えの内容は r_{R["key"]}.py の PLAN（出力ファイルごとの中身と順番）を書き換えると変えられる\n追加で必要なもの: python-docx\n')
    W = 560
    f = font(24, True)
    cells = [(tree_panel(base), 'フォルダとファイル名')]
    for rel, pno, cap in R['PREVIEW']:
        pm = fitz.open(f'{base}/{rel}')[pno].get_pixmap(dpi=80)
        cells.append((Image.frombytes('RGB', (pm.w, pm.h), pm.samples), cap))
    sh = Image.new('RGB', (W * 4 + 30, 810 * ((len(cells) + 3) // 4)), (120, 120, 120))
    for i, (im, cap) in enumerate(cells):
        im = im.resize((W, int(im.height * W / im.width)))
        c = Image.new('RGB', (W, 800), 'white')
        c.paste(im.crop((0, 0, W, min(im.height, 756))), (0, 44))
        d = ImageDraw.Draw(c)
        d.rectangle((0, 0, W, 42), fill=(30, 40, 70))
        d.text((10, 8), cap, font=f, fill='white')
        sh.paste(c, ((i % 4) * (W + 10), (i // 4) * 810))
    sh.save(f'{ROOT}/out/プレビュー_{R["key"]}_実務版.png')
    zp = f'{ROOT}/out/{R["name"]}.zip'
    if os.path.exists(zp):
        os.remove(zp)
    with zipfile.ZipFile(zp, 'w', zipfile.ZIP_DEFLATED) as z:
        for dp, _, fs in os.walk(OUT):
            for x in sorted(fs):
                full_ = os.path.join(dp, x)
                z.write(full_, os.path.join(R['name'], os.path.relpath(full_, OUT)))
    shutil.copy(f'{OUT}/正解/正解表_実務版.xlsx', f'{ROOT}/out/正解表_{R["key"]}_実務版.xlsx')
    print('zip MB', round(os.path.getsize(zp) / 1e6, 1), '受領資料', nrec, '拡張子(C)', dict(ext), '手続 C', c_, 'D', d_, '変わる単位', len(chg))


def material_setup(R, people=None):
    """素材（版違い・無関係・大量ページ）を出力する場所を用意する"""
    setup(R['src'] + '_素材', 'm_' + R['key'], {'N': 'new'}, people or {})
    return f'{ROOT}/out/{R["src"]}/B_対照版'


def run(R, material):
    material()
    for p in (f'{ROOT}/out/{R["name"]}', f'{ROOT}/out/tmp_r_{R["key"]}'):
        shutil.rmtree(p, ignore_errors=True)
        os.makedirs(p)
    MAPS = {s: make(R, s) for s in SETS}
    BK, prow, srow, mrow, var = book(R, MAPS['C'])
    if verify(R, MAPS, BK, srow):
        pack(R, prow, srow, mrow, var)
