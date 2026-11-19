"""押印の読み取り結果を正解と突き合わせて採点する"""
import os,sys,json,re,glob,unicodedata,collections,itertools
from gt import GT
W=os.path.dirname(os.path.abspath(__file__)); MAN={m['id']:m for m in json.load(open(W+'/manifest.json'))}
def n(s): return re.sub(r'[\s　()（）印]','',unicodedata.normalize('NFKC',str(s or '')))
def nd(s):   # 日付は数字の並びにそろえる（2025.10.20 → 25.10.20、令和7年 → 25）
    v=[int(x) for x in re.findall(r'\d+',unicodedata.normalize('NFKC',str(s or '')))]
    if len(v)==3:
        if v[0]>=2000: v[0]-=2000
        elif v[0]<=10 and '令' in str(s) or 'R' in str(s).upper(): v[0]+=18
    return tuple(v)
def parse(t):
    m=re.search(r'\[.*\]',t,re.S)
    try: a=json.loads(m.group(0)) if m else []
    except Exception: return None
    return [x for x in a if isinstance(x,dict)]
def fields(g,o):
    """正解の印影1つと回答1つを比べて、項目ごとの (正誤) を返す"""
    if len(g)==3: return dict(部署=n(o.get('部署'))==n(g[0]),日付=nd(o.get('日付'))==nd(g[1]),氏名=n(o.get('氏名'))==n(g[2]))
    if g[0]=='角印': return dict(氏名=n(g[1]) in n(o.get('氏名')))
    return dict(氏名=n(o.get('氏名'))==n(g[0]))
def match(gs,os_):
    """正解と回答の対応づけ。合っている項目が最も多くなる組み合わせを選ぶ（順に確定）"""
    pairs=sorted(((sum(fields(g,o).values()),-abs(i-j),i,j) for i,g in enumerate(gs) for j,o in enumerate(os_)),reverse=True)
    ug,uo,res=set(),set(),{}
    for sc,_,i,j in pairs:
        if i in ug or j in uo: continue
        ug.add(i); uo.add(j); res[i]=j
    return res
def score(text,pid):
    gs=GT[pid]; os_=parse(text)
    r=dict(n=len(gs),found=0,bad=os_ is None,detail=[],cnt=collections.Counter())
    os_=os_ or []; r['found']=len(os_); mp=match(gs,os_)
    for i,g in enumerate(gs):
        o=os_[mp[i]] if i in mp else None
        f=fields(g,o) if o else {k:False for k in fields(g,{})}
        for k,v in f.items():
            r['cnt'][k+'_n']+=1; r['cnt'][k]+=v
            if not v:
                ans=(o or {}).get(k,'') if o else None
                kind='見落とし' if o is None else ('読めないと回答' if '■' in str(ans) or str(ans).strip()=='' else '誤読')
                r['cnt'][kind]+=1; r['detail'].append((pid,i+1,k,(g[0] if len(g)==3 and k=='部署' else g[1] if len(g)==3 and k=='日付' else g[-1]),ans,kind))
        r['cnt']['全項目_n']+=1; r['cnt']['全項目']+=all(f.values())
    return r
def load(pat=''):
    by=collections.defaultdict(list)
    for f in glob.glob(W+'/results/*.json'):
        d=json.load(open(f)); tag=os.path.basename(f).rsplit('__',1)[0]
        if pat in tag: by[tag].append(dict(d,**score(d['text'],d['id'])))
    return by
if __name__=="__main__":
    by=load(sys.argv[1] if len(sys.argv)>1 else '')
    print(f"{'条件':44s} 頁 印影全項目  氏名   日付   部署 | 個数一致 誤読 読めない 見落とし | 入力tok 秒")
    rows=[]
    for tag,rs in by.items():
        c=collections.Counter()
        for r in rs: c.update(r['cnt'])
        p=lambda k:100*c[k]/c[k+'_n'] if c[k+'_n'] else float('nan')
        it=sum((r['usage'].get('input_tokens') or r['usage'].get('prompt_tokens') or 0) for r in rs)/len(rs)
        rows.append((p('全項目'),f"{tag:44s} {len(rs):2d} {p('全項目'):7.1f} {p('氏名'):6.1f} {p('日付'):6.1f} {p('部署'):6.1f} | {sum(r['n']==r['found'] for r in rs):3d}/{len(rs)} {c['誤読']:5d} {c['読めないと回答']:6d} {c['見落とし']:6d}   | {it:6.0f} {sum(r['sec'] for r in rs)/len(rs):5.1f}"+(f"  JSON不正{sum(r['bad'] for r in rs)}" if any(r['bad'] for r in rs) else '')))
    for _,l in sorted(rows,reverse=True): print(l)
