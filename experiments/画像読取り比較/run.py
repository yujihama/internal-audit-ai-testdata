"""画像の書き起こしを各モデルに依頼し、結果をファイルに保存する（同じ条件は再実行しない）"""
import os,sys,json,base64,time,io,httpx
from concurrent.futures import ThreadPoolExecutor
from PIL import Image
import variants
W=os.path.dirname(os.path.abspath(__file__)); RES=W+'/results'; os.makedirs(RES,exist_ok=True)
MAN=json.load(open(W+'/samples/manifest.json'))
PROMPT="この画像は業務文書のスキャンです。文書に書かれている文字を、上から順に、見たとおりにすべて書き起こしてください。表は行ごとに書いてください。推測で補わず、どうしても読めない文字は ■ にしてください。書き起こし以外の説明は不要です。"
cli=httpx.Client(timeout=600)
def b64(img_bytes,mime): return f"data:{mime};base64,"+base64.b64encode(img_bytes).decode()
def call_openai(model,parts,prompt,detail=None,effort=None):
    content=[{"type":"input_text","text":prompt}]
    for by,mime in parts:
        if mime=='application/pdf': content.append({"type":"input_file","filename":"document.pdf","file_data":b64(by,mime)}); continue
        c={"type":"input_image","image_url":b64(by,mime)}
        if detail: c["detail"]=detail
        content.append(c)
    body={"model":model,"input":[{"role":"user","content":content}],"max_output_tokens":20000}
    if effort: body["reasoning"]={"effort":effort}
    r=cli.post("https://api.openai.com/v1/responses",headers={"Authorization":"Bearer "+os.environ["OPENAI_API_KEY"]},json=body)
    j=r.json()
    if r.status_code!=200: raise RuntimeError(f"{r.status_code} {str(j)[:300]}")
    txt="".join(c.get("text","") for o in j["output"] if o["type"]=="message" for c in o["content"])
    return txt,j.get("usage",{})
def call_or(model,parts,prompt,**kw):
    content=[{"type":"text","text":prompt}]+[{"type":"image_url","image_url":{"url":b64(by,mime)}} for by,mime in parts]
    r=cli.post("https://openrouter.ai/api/v1/chat/completions",headers={"Authorization":"Bearer "+os.environ["OPENROUTER_API_KEY"]},
               json={"model":model,"messages":[{"role":"user","content":content}],"max_tokens":6000})
    j=r.json()
    if r.status_code!=200 or "choices" not in j: raise RuntimeError(f"{r.status_code} {str(j)[:300]}")
    return j["choices"][0]["message"]["content"] or "",j.get("usage",{})
def job(a):
    model,var,s,opts=a
    tag=f"{model.replace('/','_')}__{var}" + "".join(f"__{k}-{v}" for k,v in sorted(opts.items()))
    out=f"{RES}/{tag}__{s['id']}.json"
    if os.path.exists(out): return
    opts={k:v for k,v in opts.items() if k!='rep'}   # rep は繰り返し回数の目印（保存名にだけ使う）
    if var=='pdf':   # 画像にせず、元のPDFファイルをそのまま渡す
        if not s['a'].endswith('.pdf'): return
        parts,prompt=[(open(s['a'],'rb').read(),'application/pdf')],PROMPT.replace('この画像は','このPDFは')
    else: parts,prompt=variants.build(var,W+'/samples/'+s['img'],PROMPT)
    fn=call_or if '/' in model else call_openai
    for t in range(4):
        try:
            t0=time.time(); txt,us=fn(model,parts,prompt,**opts)
            if not txt.strip(): raise RuntimeError("empty")
            json.dump(dict(model=model,var=var,opts=opts,id=s['id'],text=txt,usage=us,sec=round(time.time()-t0,1),nparts=len(parts)),open(out,'w'),ensure_ascii=False); return
        except Exception as e:
            err=str(e); time.sleep(3*(t+1))
    print("FAIL",tag,s['id'],err[:200],flush=True)
if __name__=="__main__":
    # 使い方: run.py モデル 加工名 [detail=..] [effort=..] [ids=01,02]
    model,var=sys.argv[1:3]; opts=dict(x.split('=') for x in sys.argv[3:])
    ids=opts.pop('ids',None); ss=[s for s in MAN if not ids or s['id'][:2] in ids.split(',')]
    with ThreadPoolExecutor(int(os.environ.get("CONC","8"))) as ex: list(ex.map(job,[(model,var,s,opts) for s in ss]))
    print("done",model,var,opts,flush=True)
