# -*- coding: utf-8 -*-
"""共通: フォント、日付、会社・社員・商品・取引先の台帳（すべて架空）"""
import datetime as dt, random, unicodedata
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

ROOT = '/home/claude/work'
FD = ROOT + '/fonts'
FONTS = {'G': 'BIZUDGothic-Regular.ttf', 'B': 'BIZUDGothic-Bold.ttf', 'M': 'BIZUDMincho-Regular.ttf',
         'H': 'Yomogi-Regular.ttf', 'K': 'KleeOne-Regular.ttf', 'Z': 'ZenKurenaido-Regular.ttf',
         'D': 'DotGothic16-Regular.ttf'}
for _k, _f in FONTS.items():
    pdfmetrics.registerFont(TTFont(_k, f'{FD}/{_f}'))


def fp(k):
    return f'{FD}/{FONTS[k]}'


D = dt.date
HOL = {D(2025, 4, 29), D(2025, 5, 5), D(2025, 5, 6), D(2025, 7, 21), D(2025, 8, 11), D(2025, 9, 15), D(2025, 9, 23),
       D(2025, 10, 13), D(2025, 11, 3), D(2025, 11, 24), D(2025, 12, 29), D(2025, 12, 30), D(2025, 12, 31),
       D(2026, 1, 1), D(2026, 1, 2), D(2026, 1, 12), D(2026, 2, 11), D(2026, 2, 23), D(2026, 3, 20)}


def is_bd(d):
    return d.weekday() < 5 and d not in HOL


def add_bd(d, n):
    step = 1 if n >= 0 else -1
    for _ in range(abs(n)):
        d += dt.timedelta(days=step)
        while not is_bd(d):
            d += dt.timedelta(days=step)
    return d


def bd_count(a, b):
    """a の翌日から b までの営業日数"""
    n, d = 0, a
    while d < b:
        d += dt.timedelta(days=1)
        if is_bd(d):
            n += 1
    return n


def drange(a, b):
    d = a
    while d <= b:
        yield d
        d += dt.timedelta(days=1)


def sd(d): return d.strftime('%Y/%m/%d')
def jd(d): return f'{d.year}年{d.month}月{d.day}日'
def wd(d): return f'令和{d.year - 2018}年{d.month}月{d.day}日'
def st(d): return f'{d.year % 100}.{d.month}.{d.day}'
def md(d): return f'{d.month}/{d.day}'
def yen(n): return f'{n:,}'


_HK = {}
for _a, _b in zip('アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲンァィゥェォッャュョー',
                  'ｱｲｳｴｵｶｷｸｹｺｻｼｽｾｿﾀﾁﾂﾃﾄﾅﾆﾇﾈﾉﾊﾋﾌﾍﾎﾏﾐﾑﾒﾓﾔﾕﾖﾗﾘﾙﾚﾛﾜｦﾝｧｨｩｪｫｯｬｭｮｰ'):
    _HK[_a] = _b
_HK['゙'] = 'ﾞ'
_HK['゚'] = 'ﾟ'


def hankaku(s):
    return ''.join(_HK.get(ch, ch) for ch in unicodedata.normalize('NFD', s))


CO = dict(name='アオバ機工販売株式会社', short='アオバ機工販売', zip='〒108-0099',
          addr='東京都港区芝浦九丁目98番7号 アオバビル', tel='03-0155-2100', fax='03-0155-2199')
BANK = 'ひかり中央銀行 芝浦支店'
AGENCY = '東都信用リサーチ株式会社'
CARRIER = '関東急送便'

EMP = {'佐野': ('佐野 拓海', '営業1課'), '森下': ('森下 彩花', '営業1課'), '小田': ('小田 健吾', '営業1課'),
       '岡部': ('岡部 誠', '営業1課長'), '河合': ('河合 美咲', '営業2課'), '堀': ('堀 大輔', '営業2課'),
       '西川': ('西川 由美', '営業2課長'), '榊原': ('榊原 浩一', '営業部長'), '氷室': ('氷室 正人', '営業担当役員'),
       '立花': ('立花 奈央', '経理課'), '宮下': ('宮下 亮', '経理課'), '溝口': ('溝口 智子', '経理課長'),
       '桑原': ('桑原 修', '経理部長'), '矢野': ('矢野 翔', '物流課'), '北村': ('北村 和也', '物流課')}
REPS = {'営業1課': ['佐野', '森下', '小田'], '営業2課': ['河合', '堀']}
KA = {'営業1課': '岡部', '営業2課': '西川'}
BU, YK, KRK, KRB = '榊原', '氷室', '溝口', '桑原'


def full(n): return EMP[n][0]


PROD = [('BR-6204ZZ', '深溝玉軸受 6204ZZ', '個', 480), ('BR-6305DU', '深溝玉軸受 6305DDU', '個', 920),
        ('LB-20UU', 'リニアブッシュ 20UU', '個', 1850), ('CP-25A', 'フレキシブルカップリング φ25', '個', 6400),
        ('OR-P20-100', 'Oリング P20（100個入）', '袋', 1200), ('TB-XL150', 'タイミングベルト XL150', '本', 1350),
        ('SP-25B14', 'スプロケット 25B14', '個', 780), ('BU-1520', '無給油ブッシュ 15×20', '個', 260),
        ('SV-3120-5', '電磁弁 5ポート DC24V', '台', 7800), ('AC-20-50', 'エアシリンダ φ20×50st', '台', 9600),
        ('PS-M12-5', '近接センサ M12 検出5mm', '個', 4200), ('GM-60W-30', 'ギヤードモータ 60W 1/30', '台', 38500),
        ('BS-1605-300', 'ボールねじ 1605 L300', '本', 24800), ('LG-15-400', 'リニアガイド 15 L400', '本', 18600),
        ('HU-FK12', 'サポートユニット FK12', '個', 11200)]
PIDX = {p[0]: i for i, p in enumerate(PROD)}

_PRE = [('東雲', 'シノノメ'), ('大鷹', 'オオタカ'), ('青柳', 'アオヤギ'), ('白峰', 'シラミネ'), ('藤波', 'フジナミ'),
        ('桐生', 'キリュウ'), ('松葉', 'マツバ'), ('千早', 'チハヤ'), ('若狭', 'ワカサ'), ('八雲', 'ヤクモ'),
        ('朝霧', 'アサギリ'), ('高砂', 'タカサゴ'), ('常盤', 'トキワ'), ('富岡', 'トミオカ'), ('水無瀬', 'ミナセ'),
        ('鳴海', 'ナルミ'), ('霧島', 'キリシマ'), ('篠原', 'シノハラ'), ('日向', 'ヒュウガ'), ('柏木', 'カシワギ')]
_SUF = [('精機', 'セイキ'), ('工業', 'コウギョウ'), ('製作所', 'セイサクショ'), ('電機', 'デンキ'), ('機械', 'キカイ'),
        ('テクノ', 'テクノ'), ('エンジニアリング', 'エンジニアリング'), ('産業', 'サンギョウ'), ('金属', 'キンゾク'),
        ('製鋼', 'セイコウ')]
_CITY = [('東京都', '大田区'), ('神奈川県', '川崎市川崎区'), ('埼玉県', '川口市'), ('千葉県', '船橋市'),
         ('愛知県', '名古屋市港区'), ('大阪府', '東大阪市'), ('静岡県', '浜松市中央区'), ('群馬県', '太田市'),
         ('栃木県', '宇都宮市'), ('茨城県', '日立市'), ('長野県', '諏訪市'), ('新潟県', '燕市'),
         ('兵庫県', '尼崎市'), ('広島県', '福山市'), ('福岡県', '北九州市小倉北区')]
_TOWN = ['中央', '本町', '栄町', '東町', '西町', '南町', '北町', '緑町', '旭町', '幸町']
_AREA = {'東京都': '03', '神奈川県': '044', '埼玉県': '048', '千葉県': '047', '愛知県': '052', '大阪府': '06',
         '静岡県': '053', '群馬県': '0276', '栃木県': '028', '茨城県': '0294', '長野県': '0266', '新潟県': '0256',
         '兵庫県': '06', '広島県': '084', '福岡県': '093'}
_SEI = ['田中', '鈴木', '高橋', '渡辺', '伊藤', '山本', '中村', '小林', '加藤', '吉田', '山田', '佐々木', '松本', '井上',
        '木村', '林', '清水', '山崎', '池田', '橋本']
_MEI = ['一郎', '健一', '誠', '博', '隆', '浩', '修', '実', '学', '豊', '茂', '進', '明', '稔', '勝', '清', '正', '弘', '昭', '功']
_IND = ['産業機械製造', '金属加工', '自動車部品製造', '電子部品製造', '搬送装置製造', '工作機械製造', '食品機械製造',
        '設備保全・メンテナンス']


def gen_customers(rng):
    cs = []
    for p, (pk, pkk) in enumerate(_PRE):
        for s, (sk, skk) in enumerate(_SUF):
            i = p * 10 + s
            short = pk + sk
            name = ('株式会社' + short) if (p + s) % 3 != 1 else (short + '株式会社')
            kana = ('カ）' + pkk + skk) if (p + s) % 3 != 1 else (pkk + skk + '（カ')
            pref, city = _CITY[rng.randrange(len(_CITY))]
            addr = f'{pref}{city}{_TOWN[rng.randrange(10)]}{rng.randint(1, 5)}-{rng.randint(1, 28)}-{rng.randint(1, 19)}'
            sec = '営業1課' if i % 2 == 0 else '営業2課'
            reps = REPS[sec]
            rep = reps[(i // 2) % len(reps)]
            lim = rng.choice([100, 200, 300, 300, 500, 500, 800, 1000, 1500, 2000, 3000, 5000])
            start = D(rng.randint(1998, 2023), rng.randint(1, 12), rng.randint(1, 28))
            tel = f'{_AREA[pref]}-0{rng.randint(100, 199)}-{rng.randint(1000, 9999)}'
            cs.append(dict(i=i, code=f'T{1001 + i}', name=name, short=short, kana=kana, pkana=pkk + skk, addr=addr,
                           zip=f'〒{rng.randint(100, 899)}-00{rng.randint(10, 99)}', tel=tel, sec=sec, rep=rep,
                           limit=lim * 10000, start=start, ind=_IND[rng.randrange(len(_IND))],
                           ceo=_SEI[rng.randrange(20)] + ' ' + _MEI[rng.randrange(20)],
                           cap=rng.choice([1000, 2000, 3000, 4500, 5000, 8000, 9800]),
                           emp=rng.choice([18, 32, 45, 60, 85, 120, 150, 210, 320]),
                           pic=_SEI[rng.randrange(20)]))
    return cs
