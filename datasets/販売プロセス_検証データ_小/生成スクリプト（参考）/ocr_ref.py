# -*- coding: utf-8 -*-
"""参考: 従来型の文字読取ソフト（tesseract）で主要項目がどの程度読めるか"""
import os, sys, pickle, subprocess, re, json
from concurrent.futures import ThreadPoolExecutor
import pymupdf as fitz
from PIL import Image
ROOT='/home/claude/work'; OUT=f'{ROOT}/out/販売プロセス_検証データ_小'; TMP=f'{ROOT}/out/tmp/ocr'
os.makedirs(TMP,exist_ok=True)
st=pickle.load(open(f'{ROOT}/out/tmp/state.pkl','rb'))
def norm(s): return re.sub(r'[\s　,，.．:：/／\-ー―－（）()]','',s)
def ocr(job):
    set_,path=job
    full=f'{OUT}/{"A_難版" if set_=="A" else "B_対照版"}/{path}'
    stem=os.path.splitext(os.path.basename(path))[0]
    if stem not in st['KV'] or not path.lower().endswith(('.pdf','.jpg','.png')): return None
    txt=''
    imgs=[]
    if path.endswith('.pdf'):
        d=fitz.open(full)
        for i,p in enumerate(d):
            ip=f'{TMP}/{set_}_{stem}_{i}.png'; p.get_pixmap(dpi=200).save(ip); imgs.append(ip)
    else: imgs=[full]
    for ip in imgs:
        r=subprocess.run(['tesseract',ip,'-','-l','jpn','--psm','1'],capture_output=True,text=True)
        if r.returncode!=0 or not r.stdout.strip():
            r=subprocess.run(['tesseract',ip,'-','-l','jpn','--psm','6'],capture_output=True,text=True)
        txt+=r.stdout
    t=norm(txt)
    vals=[v for k,v in st['KV'][stem].items() if v and not any(w in v for w in ('印','斜線','空欄','署名','手書き','ゴム'))]
    hit=sum(1 for v in vals if norm(v) in t)
    return (set_,path,hit,len(vals))
jobs=[(m['set'],m['path']) for m in st['MAN']]
with ThreadPoolExecutor(4) as ex: res=[r for r in ex.map(ocr,jobs) if r]
json.dump(res,open(f'{ROOT}/out/tmp/ocr_ref.json','w'),ensure_ascii=False)
for s in 'AB':
    h=sum(r[2] for r in res if r[0]==s); n=sum(r[3] for r in res if r[0]==s)
    print(s,h,n,round(h/max(1,n),3))
