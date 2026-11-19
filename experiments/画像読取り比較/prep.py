import json,glob,os,collections,random,sys
import fitz
from PIL import Image
REPO=os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','..')); OUT=os.path.dirname(os.path.abspath(__file__))+'/samples'
os.makedirs(OUT,exist_ok=True)
KEY={'低解像度':'lowres','FAX受信風':'fax','粗い網点':'halftone'}
cands=collections.defaultdict(list)
for f in sorted(glob.glob(REPO+"/datasets/*_小/正解/正解.json")):
    d=json.load(open(f)); base=os.path.dirname(os.path.dirname(f))
    B={os.path.splitext(x['path'])[0]:x for x in d['files'] if x['set']=='B'}
    for x in d['files']:
        if x['set']!='A' or x['stage']!=2: continue
        k=next((v for kk,v in KEY.items() if kk in x['ops']),None)
        b=B.get(os.path.splitext(x['path'])[0])
        if not k or not b or not b['path'].endswith('.pdf') or not b['layer'].startswith('あり（正しい'): continue
        cands[k].append(dict(area=os.path.basename(base).split('_')[0],a=base+'/A_難版/'+x['path'],b=base+'/B_対照版/'+b['path'],ops=x['ops'],kind=x['kind'],tess=x['ocr_rate']))
rng=random.Random(7); sel=[]
for k,n in (('lowres',7),('fax',10),('halftone',7)):
    c=cands[k]; rng.shuffle(c)
    # 業務領域が偏らないように順番に取る
    by=collections.defaultdict(list)
    for x in c: by[x['area']].append(x)
    pick=[]
    while len(pick)<min(n,len(c)):
        for a in sorted(by):
            if by[a] and len(pick)<n: pick.append(by[a].pop())
    for x in pick: x['cat']=k
    sel+=pick
man=[]
for i,x in enumerate(sel):
    sid=f"{i+1:02d}_{x['cat']}"
    if x['a'].endswith('.pdf'):
        d=fitz.open(x['a']); pg=d[0]; npg=len(d)
        ims=pg.get_images(full=True)
        # 画像だけのPDFは、埋め込まれた画像をそのままの画素数で取り出す
        if len(ims)==1:
            pix=fitz.Pixmap(d,ims[0][0])
            if pix.n>3 or pix.colorspace is None or pix.colorspace.n not in(1,3): pix=fitz.Pixmap(fitz.csRGB,pix)
            pix.save(f'{OUT}/{sid}.png'); src='embedded'
        else:
            pg.get_pixmap(dpi=200).save(f'{OUT}/{sid}.png'); src=f'render200({len(ims)}img)'
        img=f'{sid}.png'; rot=pg.rotation
    else:
        im=Image.open(x['a']); im.save(f'{OUT}/{sid}.jpg',quality=95) if False else None
        import shutil; shutil.copy(x['a'],f'{OUT}/{sid}.jpg'); img=f'{sid}.jpg'; src='file'; npg=1; rot=0
    bd=fitz.open(x['b']); gt=bd[0].get_text()
    bd[0].get_pixmap(dpi=100).save(f'{OUT}/{sid}_clean.png')
    w,h=Image.open(f'{OUT}/{img}').size
    man.append(dict(id=sid,img=img,w=w,h=h,src=src,pages=npg,bpages=len(bd),rot=rot,gt=gt,**x))
    print(sid,x['area'],x['kind'],w,h,src,npg,len(bd),rot,x['ops'],x['tess'],len(gt))
json.dump(man,open(OUT+'/manifest.json','w'),ensure_ascii=False,indent=1)
