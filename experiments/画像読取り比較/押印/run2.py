"""2段階の読み取り：(1)印影の位置を答えさせる (2)その部分を切り出して拡大し、読み直させる
使い方: run2.py モデル [smooth]   結果は「モデル__zoom」（smooth付きは __zoomS）として保存"""
import os,sys,json,io,time
import numpy as np,cv2
from concurrent.futures import ThreadPoolExecutor
from PIL import Image
import run,score
W=run.W; POS=W+'/results_pos'; os.makedirs(POS,exist_ok=True)
P1=run.PROMPT+'\n各要素に "位置" も入れてください：印影を囲む四角 [左, 上, 右, 下]。画像の左上を (0,0)、右下を (1000,1000) とした値です。'
P2="""同じ1ページの文書から、印影（はんこ）の周りを切り出して拡大した画像を {n} 枚、順に渡します。
それぞれの画像の中央付近にある印影を読み取り、JSONの配列だけ（{n} 要素、渡した順）を出力してください。各要素の項目：
- "種類": "日付印"（丸の中が3段で、上段が部署、中段が日付、下段が氏名）／"認印"（丸の中に氏名だけ）／"角印"／"その他"／"印影なし"
- "部署": 日付印の上段の文字。なければ ""
- "日付": 日付印の中段を見たまま（例：25.10.20）。なければ ""
- "氏名": 日付印の下段、または認印の文字。角印は彫られている文字
推測で補わず、どうしても読めない文字は ■ にしてください。"""
def png(im):
    b=io.BytesIO(); im.save(b,'PNG'); return b.getvalue(),'image/png'
def job(a):
    model,s,smooth=a; tag=model+('__zoomS' if smooth else '__zoom'); out=f"{run.RES}/{tag}__{s['id']}.json"
    if os.path.exists(out): return
    fn=run.call_or if '/' in model else run.call_openai
    im=Image.open(f"{W}/samples/{s['id']}.png").convert('RGB'); pf=f"{POS}/{model.replace('/','_')}__{s['id']}.json"
    try:
        t0=time.time()
        if os.path.exists(pf): t1,u1=json.load(open(pf))
        else:
            t1,u1=fn(model,[png(im)],P1); json.dump([t1,u1],open(pf,'w'),ensure_ascii=False)
        st=[x for x in (score.parse(t1) or []) if isinstance(x.get('位置'),list) and len(x['位置'])==4]
        if not st: json.dump(dict(model=model,var='zoom',id=s['id'],text=t1,usage=u1,sec=0,opts={}),open(out,'w'),ensure_ascii=False); return
        parts=[]
        for x in st:
            x0,y0,x1,y1=[float(v) for v in x['位置']]
            cx,cy=(x0+x1)/2000*im.width,(y0+y1)/2000*im.height
            r=max((x1-x0)/1000*im.width,(y1-y0)/1000*im.height,0.06*max(im.size))*1.1   # 位置のずれを見込んで広めに切る
            c=im.crop((int(cx-r),int(cy-r),int(cx+r),int(cy+r)))
            if smooth: c=Image.fromarray(cv2.GaussianBlur(np.array(c),(0,0),1.0))
            parts.append(png(c.resize((640,640),Image.LANCZOS)))
        t2,u2=fn(model,parts,P2.format(n=len(parts)))
        json.dump(dict(model=model,var='zoom',id=s['id'],text=t2,usage=u2,sec=round(time.time()-t0,1),opts={},pass1=t1),open(out,'w'),ensure_ascii=False)
    except Exception as e: print('FAIL',tag,s['id'],str(e)[:160],flush=True)
if __name__=="__main__":
    model=sys.argv[1]; smooth='smooth' in sys.argv
    with ThreadPoolExecutor(int(os.environ.get("CONC","8"))) as ex: list(ex.map(job,[(model,s,smooth) for s in run.MAN]))
    print('done',model)
