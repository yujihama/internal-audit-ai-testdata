"""C（読みにくい実務版）の押印があるページを洗い出す。押印の位置は D（読みやすい版）のPDFから取る"""
import pymupdf as fitz,glob,os,json,re,collections,sys
R=os.environ.get('REPO',os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','..','..')))+'/datasets'
out=[]
for d in sorted(glob.glob(R+'/*_実務版')):
    area=os.path.basename(d).split('_')[0]
    ans=json.load(open(d+'/正解/正解.json')); base=json.load(open(d.replace('_実務版','')+'/正解/正解.json'))
    A={os.path.splitext(os.path.basename(x['path']))[0]:x for x in base['files'] if x['set']=='A'}
    mp={}
    for m in ans['mapping']:
        g=re.match(r'(\d+)ページ',m['position'])
        if g: mp[(m['file'],int(g.group(1)))]=m
    for f in sorted(glob.glob(d+'/C_実務版_難/受領資料/**/*.pdf',recursive=True)):
        g=f.replace('C_実務版_難','D_実務版_対照')
        if not os.path.exists(g): continue
        c=fitz.open(f); dd=fitz.open(g)
        if c.needs_pass or dd.needs_pass or len(c)!=len(dd): continue
        rel=f.split('C_実務版_難/')[1]
        for i,p in enumerate(dd):
            st=[[r.x0,r.y0,r.x1,r.y1] for im in p.get_images(full=True) for r in p.get_image_rects(im[0]) if r.width<120 and r.height<120]
            if not st: continue
            m=mp.get((rel,i+1),{}); a=A.get(m.get('original',''),{})
            out.append(dict(area=area,c=f,d=g,page=i,stamps=st,doc=m.get('doc'),orig=m.get('original'),remark=m.get('remark'),ops=a.get('ops'),stage=a.get('stage'),unread=a.get('unread'),crot=c[i].rotation,drot=p.rotation,cimgs=len(c[i].get_images())))
json.dump(out,open('cand.json','w'),ensure_ascii=False,indent=1)
print(len(out)); cnt=collections.Counter()
for o in out:
    for x in (o['ops'] or '不明').split('、'): cnt[re.sub(r'（.*|約.*','',x)]+=1
print(cnt.most_common()); print(collections.Counter((o['area'],o['stage']) for o in out))
print(collections.Counter(o['remark'] for o in out).most_common(12))
