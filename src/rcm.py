# -*- coding: utf-8 -*-
"""各領域の RCM（1シート）を作る。
元の手続一覧.xlsx（リスクと統制・手続一覧・サンプル一覧・前提）を1つの表にまとめ、
RCM として足りない属性（予防／発見、実施者など）を補う。正解に関わる記載は入れない。
  実行: python rcm.py  →  out/RCM/RCM_<領域>.xlsx"""
import math, os, re, unicodedata
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

ROOT = '/home/claude/work'
FN = '游ゴシック'
BIZ = '営業日：土曜・日曜・祝日と、12/29〜1/2 を除く日'

# 統制ごとの補足: (予防／発見, 実施部署・実施者)。販売は元の表にあるため実施方法だけ補う
CTL = {
    '購買プロセス': {
        'C1': ('予防・発見', '購買課長（承認）、経理課（登録）、経理課長（月次の照合）'), 'C2': ('予防', '購買課、購買部長'), 'C3': ('予防', '購買課長、購買部長、担当役員'),
        'C4': ('発見', '購買課長、購買部長'), 'C5': ('予防', '経理担当者、経理課長'), 'C6': ('予防', '経理担当者、経理課長'), 'C7': ('発見', '経理課、経理課長'),
        'C8': ('発見', '購買課長、購買部長'), 'C9': ('発見', '購買課、購買部長'), 'C10': ('予防・発見', '情報システム課'), 'C11': ('予防', 'システム（購買管理システム AOBA-PROC）')},
    'ITインフラ管理': {
        'N1': ('予防・発見', '情報システム課、情報システム課長'), 'N2': ('予防', '情報システム課'), 'N3': ('発見', '情報システム課の担当者、情報システム課長'),
        'N4': ('発見', '情報システム課、担当役員（リスク受容）'), 'N5': ('予防', '情報システム課')},
    'IT業務処理': {
        'A1': ('予防', 'システム（販売管理システム AOBA-SALES）'), 'A2': ('発見', '経理課の担当者、経理課長'), 'A3': ('発見', '経理課の担当者、経理課長'),
        'A4': ('予防', '情報システム課長、業務部門長'), 'A5': ('予防', 'システム（販売管理システム AOBA-SALES）')},
    '製造プロセス': {
        'M1': ('予防', '製造課、製造課長'), 'M2': ('発見', '検査員、品質保証課長、製造部長'), 'M3': ('発見', '作業者、班長、原価担当、製造課長'),
        'M4': ('予防', '製造課長、製造部長'), 'M5': ('発見', '作業者、班長')},
    '実地棚卸': {
        'W1': ('予防', '物流課（原票の発行・回収の担当）'), 'W2': ('発見', '物流課長'), 'W3': ('発見', '集計担当、照合担当（集計担当とは別の者）'),
        'W4': ('発見', '物流課長、経理課長'), 'W5': ('予防・発見', 'カウント担当（2名1組）、経理課の立会者')},
    '工事進行管理': {
        'K1': ('発見', '経理担当、経理課長'), 'K2': ('発見', '現場代理人、工事課長、工事部長'), 'K3': ('予防', '工事課、工事部長'),
        'K4': ('予防', '現場代理人、工事課長'), 'K5': ('予防', '工事台帳の登録担当者')},
}
# アサーション（統制ごと）。財務報告に直結しない統制は「－」とする
IT = '－（IT全般統制）'
ASR = {
    '販売プロセス': {'C1': '評価の妥当性', 'C2': '実在性、評価の妥当性', 'C3': '評価の妥当性', 'C4': '実在性、期間配分の適切性', 'C5': '実在性、網羅性', 'C6': '実在性、網羅性', 'C7': '評価の妥当性', 'C8': '期間配分の適切性'},
    '購買プロセス': {'C1': '実在性、権利と義務の帰属', 'C2': '評価の妥当性', 'C3': '実在性、権利と義務の帰属', 'C4': '実在性、権利と義務の帰属', 'C5': '実在性、評価の妥当性', 'C6': '実在性、評価の妥当性', 'C7': '網羅性、評価の妥当性',
               'C8': '実在性、網羅性', 'C9': '実在性、権利と義務の帰属', 'C10': IT, 'C11': '実在性、評価の妥当性'},
    'ITインフラ管理': {'N1': IT, 'N2': IT, 'N3': IT, 'N4': IT, 'N5': IT},
    'IT業務処理': {'A1': '評価の妥当性', 'A2': '網羅性、評価の妥当性', 'A3': '網羅性、期間配分の適切性', 'A4': IT, 'A5': '評価の妥当性'},
    '製造プロセス': {'M1': '実在性、評価の妥当性', 'M2': '－（品質に関する業務上の統制）', 'M3': '評価の妥当性', 'M4': '実在性、評価の妥当性', 'M5': '－（設備保全に関する業務上の統制）'},
    '実地棚卸': {'W1': '実在性、網羅性', 'W2': '網羅性', 'W3': '実在性、網羅性', 'W4': '実在性、評価の妥当性', 'W5': '実在性'},
    '工事進行管理': {'K1': '評価の妥当性、期間配分の適切性', 'K2': '期間配分の適切性', 'K3': '評価の妥当性、期間配分の適切性', 'K4': '実在性、評価の妥当性', 'K5': '実在性、権利と義務の帰属'},
}
# 販売は手続の種類が元の表にないため補う
PTYPE = {'P01': '決裁権限の確認', 'P02': '添付資料との突合', 'P03': '注文書との照合', 'P04': '承認の確認', 'P05': '承認と時期の確認', 'P06': '出荷・受領・計上の照合', 'P07': '承認と時期の確認',
         'P08': '承認の確認', 'P09': '入金の網羅性の照合', 'P10': '承認と時期の確認', 'P11': 'レビューの確認', 'P12': '計上時期の確認', 'P13': '承認と時期の確認'}
# サンプルの列の見出し（販売。統制ごとに識別番号の意味が違う）
SLEG = {'C1': '申請番号', 'C2': '受注番号｜客先注文番号', 'C3': '値引申請番号｜受注番号', 'C4': '出荷番号｜売上番号', 'C5': '売上取消伝票番号｜返品番号', 'C8': '出荷番号｜売上番号'}
# 備考（手続ごと）。手続を行うのに必要な前提だけを書く
NOTE = {
    '販売プロセス': {
        'P01': '決裁の区分は、共通資料の職務権限規程による。', 'P04': '承認の区分は、共通資料の職務権限規程による。', 'P05': '標準単価は共通資料の標準単価表、承認の区分は職務権限規程による。',
        'P06': '売上明細は共通資料のデータを使う。', 'P07': '承認の区分は、共通資料の職務権限規程による。', 'P12': '売上明細は共通資料のデータを使う。'},
    '購買プロセス': {
        'P01': 'サンプルの指定なし（全件）。共通資料のデータから対象を抽出する。\n提出された振込口座変更の申請書・依頼書は、当年度の振込口座変更に関して会社が保管する全件である（経理課に確認済み）。',
        'P02': '相見積の要否は税抜金額で判定する。', 'P03': '承認区分は税抜金額で判定する。', 'P04': f'サンプルの指定なし（全件）。共通資料のデータから対象を抽出する。\n{BIZ}',
        'P08': 'サンプルの指定なし（全件）。共通資料のデータから対象を抽出する。', 'P09': '仕入明細は共通資料のデータを使う。', 'P11': BIZ, 'P12': BIZ},
    'ITインフラ管理': {
        'I02': 'サーバ一覧は共通資料のデータを使う。', 'I03': BIZ, 'I04': '診断報告書（SB-2510-118）の受領日は2025年10月15日。期限はこの日から数える。'},
    'IT業務処理': {
        'S01': '請求明細データ（共通資料）の行金額・税抜合計・消費税・請求額は、システムが計算した値。数量・単価・得意先ランクは入力値として正しいものとする。',
        'S02': BIZ, 'S03': BIZ, 'S04': BIZ},
    '製造プロセス': {
        'F01': '部品表は共通資料を使う。', 'F02': '検査基準書は共通資料を使う。', 'F03': '提出された作業日報には、サンプルの指図の作業期間（11/4〜11/7、12/8〜12/10）の全日分が含まれている。',
        'F05': '稼働日：土曜・日曜・祝日と、12/27〜1/4 を除く日'},
    '実地棚卸': {
        'T01': '棚卸原票は回収後の写し（1枚に4票ずつ）。', 'T02': '棚卸原票は回収後の写し（1枚に4票ずつ）。', 'T03': '棚卸原票は回収後の写し（1枚に4票ずつ）。',
        'T04': '帳簿在庫一覧（共通資料）は、棚卸日時点の帳簿数量（差異による修正の前）。単価は原価。', 'T05': '現物の写真は、立会者が撮影した箱ラベルの写真を想定した合成画像。'},
    '工事進行管理': {
        'C01': '売上は工事の進み具合に応じて計上する。進捗度は原価の比率（発生原価÷見積総原価）で求める。\n対象の3件は、いずれも当期に着工し、前期までの売上の計上はない。\n金額はすべて税抜。',
        'C02': '出来高報告書の進捗率は、工種ごとの作業の進み具合（工事の管理用）。売上の計算に使う進捗度（原価の比率）とは別のもの。', 'C03': '金額はすべて税抜。',
        'C04': '金額は税抜（請求書の合計欄を除く）。', 'C05': '金額はすべて税抜。'},
}
BASIS = {'販売プロセス': '共通資料の「販売管理規程」「職務権限規程」に定める', '購買プロセス': '共通資料の「購買管理規程」「職務権限規程」に定める'}
ORDER = ['販売プロセス', '購買プロセス', 'ITインフラ管理', 'IT業務処理', '製造プロセス', '実地棚卸', '工事進行管理']
COLS = [('プロセス', 12), ('サブプロセス', 14), ('リスクNo', 7), ('リスクの内容', 30), ('アサーション', 18), ('統制No', 7), ('統制の内容', 46), ('予防／発見', 11), ('実施方法', 15), ('頻度', 12), ('実施部署・実施者', 22),
        ('手続No', 7), ('手続の種類', 20), ('手続の内容', 60), ('サンプル数', 12), ('サンプル（対象）', 72), ('想定証跡', 30), ('備考', 40)]
GROUPS = [('RCM（リスクと統制）', 1, 11), ('手続', 12, 16), ('想定証跡', 17, 17), ('備考', 18, 18)]


def fmt(v):
    if v is None:
        return ''
    if hasattr(v, 'strftime'):
        return v.strftime('%Y/%m/%d')
    if isinstance(v, (int, float)):
        return f'{v:,.0f}円'
    return str(v).strip()


SOVR = {('販売プロセス', 'P13'): '期末売上計上時期確認表（1件）'}      # 統制のサンプルとは別のものを見る手続


def samples(name, wb, pid, cid):
    if (name, pid) in SOVR:
        return SOVR[(name, pid)]
    ws = wb['サンプル一覧']
    hd = [c.value for c in ws[1]]
    keep = [i for i, h in enumerate(hd) if 'ファイル' not in str(h)]
    rows = [[r[i] for i in keep] for r in ws.iter_rows(min_row=2, values_only=True)]
    key = cid if hd[0] == '統制ID' else pid
    mine = [r for r in rows if key in re.split('[・、]', str(r[0]))]
    out = []
    for r in mine:
        unit, rest = fmt(r[1]), r[2:]
        parts = [unit]
        for v in rest:
            s = fmt(v)
            month = hasattr(v, 'strftime') and ('月度' in unit or '月末' in unit or '支払' in unit or re.fullmatch(r'\d{4}年\d{1,2}月', unit))
            if s and s not in parts and not month:
                parts.append(s)
        out.append('｜'.join(parts))
    if not out:
        return ''
    if name == '販売プロセス' and cid in SLEG:
        out.insert(0, f'（サンプル｜{SLEG[cid]}｜取引先｜日付｜金額（税抜））')
    elif name == '購買プロセス' and any(mine[0][2:4]):      # 元の表の見出しをそのまま使う（空の列は除く）
        leg = ['単位'] + [h for i, h in enumerate(['識別番号1', '識別番号2', '相手先・内容', '日付', '金額（円）'], 2) if any(r[i] not in (None, '') for r in mine)]
        out.insert(0, '（' + '｜'.join(leg) + '）')
    return '\n'.join(out)


def build(name):
    wb = load_workbook(f'{ROOT}/out/{name}_検証データ_小/A_難版/手続一覧.xlsx')
    rc, pr = wb['リスクと統制'], wb['手続一覧']
    ch, ph = [c.value for c in rc[1]], [c.value for c in pr[1]]
    ctl = {r[0]: dict(zip(ch, r)) for r in rc.iter_rows(min_row=2, values_only=True)}
    prem = {r[0]: r[1] for r in wb['前提'].iter_rows(min_row=2, values_only=True)}
    rows = []
    for r in pr.iter_rows(min_row=2, values_only=True):
        p = dict(zip(ph, r))
        pid, cid = p['手続ID'], p['統制ID']
        c = ctl.get(cid)
        if c is None:      # プロセス全体を追う手続（ウォークスルー）
            head = [name, '全体（購買依頼〜支払）', '－', '（プロセス全体の整備状況）', '－', cid, '業務記述書・フローチャートに記載された統制（購買依頼の承認、発注承認、発注担当者以外による検収、3点照合と承認、支払）', '－', '－', '－', '－']
        else:
            if name == '販売プロセス':
                kind, how, who = c['種別'], '手作業', c['実施部署']
            else:
                (kind, who), how = CTL[name][cid], c['種別']
            freq = '都度（自動）' if c['頻度'] == '自動' else c['頻度']
            head = [name, c['業務'], 'R' + re.sub(r'\D', '', cid), c['リスク'], ASR[name][cid], cid, c['統制の内容'], kind, how, freq, who]
        text = p['手続の内容'].replace('「サンプル一覧」', '「サンプル（対象）」の列')
        cnt = p.get('対象') or p.get('サンプル')
        smp = samples(name, wb, pid, cid) or f'{cnt}（サンプルの指定なし）'
        rows.append(head + [pid, p.get('手続の種類') or PTYPE[pid], text, cnt, smp, p['対象の証跡'], NOTE[name].get(pid, '')])
    meta = [('対象会社', prem['対象会社']), ('棚卸日' if '棚卸日' in prem else '評価対象期間', prem.get('棚卸日') or prem['評価対象期間']), ('判定の区分', prem['判定の区分']),
            ('判定の基準', BASIS.get(name) or prem['判定の基準'])]
    if '営業日' in prem and name != '製造プロセス':
        meta.append(('営業日', prem['営業日']))
    if 'サンプル数' in prem:
        meta.append(('サンプル数', prem['サンプル数']))
    return meta, rows


def width(s):
    return sum(2 if unicodedata.east_asian_width(ch) in 'FWA' else 1 for ch in s)


def write(name, meta, rows, path):
    wb = Workbook()
    ws = wb.active
    ws.title = 'RCM'
    side = Side(style='thin', color='808080')
    bd = Border(left=side, right=side, top=side, bottom=side)
    ws['A1'] = f'リスクコントロールマトリクス（RCM）　{name}'
    ws['A1'].font = Font(name=FN, size=14, bold=True)
    for i, (k, v) in enumerate(meta):
        a, b = ws.cell(row=2 + i, column=1, value=k), ws.cell(row=2 + i, column=2, value=v)
        a.font, b.font = Font(name=FN, size=10, bold=True), Font(name=FN, size=10)
    g0 = 9                          # 見出し1行目（区分）。どの領域も同じ行にそろえる（前提は2〜7行目）
    h0 = g0 + 1                     # 見出し2行目（列名）
    fills = ['DDEBF7', 'E2EFDA', 'FFF2CC', 'EDEDED']
    for (g, a, b), fc in zip(GROUPS, fills):
        ws.cell(row=g0, column=a, value=g)
        if b > a:
            ws.merge_cells(start_row=g0, start_column=a, end_row=g0, end_column=b)
        else:               # 列が1つだけの区分は、見出しを縦につなげる
            ws.merge_cells(start_row=g0, start_column=a, end_row=h0, end_column=a)
        for col in range(a, b + 1):
            for row in (g0, h0):
                c = ws.cell(row=row, column=col)
                c.fill, c.border = PatternFill('solid', fgColor=fc), bd
                c.font, c.alignment = Font(name=FN, size=10, bold=True), Alignment(horizontal='center', vertical='center', wrap_text=True)
    single = {a for _, a, b in GROUPS if a == b}
    for j, (h, w) in enumerate(COLS, 1):
        if j not in single:
            ws.cell(row=h0, column=j, value=h)
        ws.column_dimensions[get_column_letter(j)].width = w
    ws.row_dimensions[g0].height, ws.row_dimensions[h0].height = 20, 30
    for i, r in enumerate(rows):
        lines = 1
        for j, v in enumerate(r, 1):
            c = ws.cell(row=h0 + 1 + i, column=j, value=v)
            c.font, c.border = Font(name=FN, size=10), bd
            c.alignment = Alignment(vertical='top', wrap_text=True, horizontal='center' if COLS[j - 1][0] in ('リスクNo', '統制No', '手続No', '予防／発見', '頻度', 'サンプル数') else 'left')
            per = max(4, COLS[j - 1][1] - 1)
            lines = max(lines, sum(max(1, math.ceil(width(x) / per)) for x in str(v or '').split('\n')))
        ws.row_dimensions[h0 + 1 + i].height = min(409, lines * 17 + 6)
    ws.freeze_panes = ws.cell(row=h0 + 1, column=1)
    ws.auto_filter.ref = f'A{h0}:{get_column_letter(len(COLS))}{h0 + len(rows)}'
    ws.page_setup.orientation, ws.page_setup.paperSize = 'landscape', ws.PAPERSIZE_A3
    ws.page_setup.fitToWidth, ws.page_setup.fitToHeight = 1, 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.print_title_rows = f'{g0}:{h0}'
    wb.save(path)
    return h0


if __name__ == '__main__':
    os.makedirs(f'{ROOT}/out/RCM', exist_ok=True)
    for n in ORDER:
        meta, rows = build(n)
        h0 = write(n, meta, rows, f'{ROOT}/out/RCM/RCM_{n}.xlsx')
        print(n, '手続', len(rows), '見出しの行', h0, '統制', len({r[5] for r in rows}))
