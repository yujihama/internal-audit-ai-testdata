"""ページ画像を渡して、押印の一覧をJSONで答えさせる（同じ条件は再実行しない）"""
import os,sys,json,base64,time,httpx
from concurrent.futures import ThreadPoolExecutor
import variants
W=os.path.dirname(os.path.abspath(__file__)); RES=W+'/results'; os.makedirs(RES,exist_ok=True)
MAN=json.load(open(W+'/manifest.json'))
PROMPT="""この画像は業務文書のスキャンです。このページに押されている印影（はんこ）をすべて挙げてください。
JSONの配列だけを出力してください。印影1つにつき1要素で、次の項目を入れます。
- "欄": 印影がある欄の見出し（例：承認、作成、購買課長）。見出しがなければ ""
- "種類": "日付印"（丸の中が3段で、上段が部署、中段が日付、下段が氏名）／"認印"（丸の中に氏名だけ）／"角印"（四角い会社印）／"その他"
- "部署": 日付印の上段の文字。日付印でなければ ""
- "日付": 日付印の中段を見たまま（例：25.10.20）。日付印でなければ ""
- "氏名": 日付印の下段、または認印の文字。角印は彫られている文字
印影がない欄（空欄・斜線）は挙げないでください。印字された文字や手書きの文字は印影ではありません。
推測で補わず、どうしても読めない文字は ■ にしてください。"""
cli=httpx.Client(timeout=600)
def b64(by,mime): return f"data:{mime};base64,"+base64.b64encode(by).decode()
def call_openai(model,parts,prompt,detail=None,effort=None):
    content=[{"type":"input_text","text":prompt}]
    for by,mime in parts:
        c={"type":"input_image","image_url":b64(by,mime)}
        if detail: c["detail"]=detail
        content.append(c)
    body={"model":model,"input":[{"role":"user","content":content}],"max_output_tokens":12000}
    if effort: body["reasoning"]={"effort":effort}
    r=cli.post("https://api.openai.com/v1/responses",headers={"Authorization":"Bearer "+os.environ["OPENAI_API_KEY"]},json=body); j=r.json()
    if r.status_code!=200: raise RuntimeError(f"{r.status_code} {str(j)[:300]}")
    return "".join(c.get("text","") for o in j["output"] if o["type"]=="message" for c in o["content"]),j.get("usage",{})
def call_or(model,parts,prompt,**kw):
    content=[{"type":"text","text":prompt}]+[{"type":"image_url","image_url":{"url":b64(by,mime)}} for by,mime in parts]
    r=cli.post("https://openrouter.ai/api/v1/chat/completions",headers={"Authorization":"Bearer "+os.environ["OPENROUTER_API_KEY"]},
               json={"model":model,"messages":[{"role":"user","content":content}],"max_tokens":4000}); j=r.json()
    if r.status_code!=200 or "choices" not in j: raise RuntimeError(f"{r.status_code} {str(j)[:300]}")
    return j["choices"][0]["message"]["content"] or "",j.get("usage",{})
def job(a):
    model,var,s,opts=a
    tag=f"{model.replace('/','_')}__{var}"+"".join(f"__{k}-{v}" for k,v in sorted(opts.items()))
    out=f"{RES}/{tag}__{s['id']}.json"
    if os.path.exists(out): return
    o={k:v for k,v in opts.items() if k!='rep'}
    parts,prompt=variants.build(var,f"{W}/samples/{s['id']}.png",PROMPT)
    fn=call_or if '/' in model else call_openai
    for t in range(4):
        try:
            t0=time.time(); txt,us=fn(model,parts,prompt,**o)
            if not txt.strip(): raise RuntimeError("empty")
            json.dump(dict(model=model,var=var,opts=opts,id=s['id'],text=txt,usage=us,sec=round(time.time()-t0,1)),open(out,'w'),ensure_ascii=False); return
        except Exception as e: err=str(e); time.sleep(3*(t+1))
    print("FAIL",tag,s['id'],err[:160],flush=True)
if __name__=="__main__":
    model,var=sys.argv[1:3]; opts=dict(x.split('=') for x in sys.argv[3:])
    ids=opts.pop('ids',None); ss=[s for s in MAN if not ids or s['id'] in ids.split(',')]
    with ThreadPoolExecutor(int(os.environ.get("CONC","8"))) as ex: list(ex.map(job,[(model,var,s,opts) for s in ss]))
    print("done",model,var,opts,flush=True)
