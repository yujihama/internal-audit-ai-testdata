"""押印の読み取り検証用のサンプルを作る：Cのページ画像、Dの押印の切り抜き（正解づくり用）"""
import pymupdf as fitz,json,os,re,collections,random
from PIL import Image
W=os.path.dirname(os.path.abspath(__file__)); S=W+'/samples'; os.makedirs(S,exist_ok=True)
HARD=('FAX受信風','粗い網点','低解像度','複写の繰り返し風','複写伝票風','スマホ撮影風','薄い・かすれ','暗い・コントラスト不足','印字かすれ','裏写り')
cand=[c for c in json.load(open(W+'/cand.json')) if c['ops'] and c['stage'] in (2,3) and any(h in c['ops'] for h in HARD)]
rng=random.Random(11); by=collections.defaultdict(list)
for c in cand: by[c['area']].append(c)
sel=[]
for area,cs in sorted(by.items()):
    rng.shuffle(cs); used=collections.Counter(); pick=[]
    while cs and len(pick)<6:      # 領域ごとに最大6ページ。劣化の種類がなるべく重ならないように選ぶ
        cs.sort(key=lambda c:(sum(used[h] for h in HARD if h in c['ops']),-len(c['stamps'])))
        c=cs.pop(0); pick.append(c)
        for h in HARD:
            if h in c['ops']: used[h]+=1
    sel+=pick
man=[]
for n,c in enumerate(sel):
    pid=f"p{n+1:02d}"
    cd=fitz.open(c['c']); pg=cd[c['page']]; ims=pg.get_images(full=True)
    if len(ims)==1:   # 画像だけのページは、埋め込まれた画像をそのままの画素数で取り出す
        pix=fitz.Pixmap(cd,ims[0][0])
        if pix.colorspace is None or pix.colorspace.n not in(1,3) or pix.alpha: pix=fitz.Pixmap(fitz.csRGB,pix)
        pix.save(f'{S}/{pid}.png'); im=Image.open(f'{S}/{pid}.png')
        if pg.rotation: im=im.rotate(-pg.rotation,expand=True); im.save(f'{S}/{pid}.png')   # 表示どおりの向きにする
    else: pg.get_pixmap(dpi=200).save(f'{S}/{pid}.png')
    dd=fitz.open(c['d']); dp=dd[c['page']]
    dp.get_pixmap(dpi=110).save(f'{S}/{pid}_clean.png')
    st=[]
    for k,r in enumerate(sorted(c['stamps'],key=lambda r:(round(r[1]/40),r[0]))):
        rr=fitz.Rect(r)*dp.rotation_matrix if dp.rotation else fitz.Rect(r)
        rr=fitz.Rect(r); pad=6
        clip=fitz.Rect(rr.x0-pad,rr.y0-pad,rr.x1+pad,rr.y1+pad)
        dp.get_pixmap(dpi=500,clip=clip).save(f'{S}/{pid}_s{k+1}.png')
        # 押印の近くの見出し（欄の名前）を探す手がかりとして、周りの文字も保存
        ctx=dp.get_text('text',clip=fitz.Rect(rr.x0-40,rr.y0-45,rr.x1+40,rr.y1+12)).split()
        st.append(dict(k=k+1,rect=r,ctx=ctx[:12]))
    w,h=Image.open(f'{S}/{pid}.png').size
    man.append(dict(id=pid,area=c['area'],doc=c['doc'],ops=c['ops'],stage=c['stage'],unread=c['unread'],remark=c['remark'],file=c['c'].split('datasets/')[1],page=c['page']+1,w=w,h=h,stamps=st))
    print(pid,c['area'],c['doc'],len(st),w,h,c['ops'],c['stage'],c['remark'] or '')
json.dump(man,open(W+'/manifest.json','w'),ensure_ascii=False,indent=1)
print(len(man),sum(len(m['stamps']) for m in man))
