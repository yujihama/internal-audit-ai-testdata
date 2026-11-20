"""複数の実行結果を突き合わせ、一致した項目だけ採用する（一致しなければ ■）。
使い方: ens.py 必要な一致数 条件1 条件2 ...   （一致数に all と書くと全員一致）"""
import sys,json,glob,os,collections
import score
F=('部署','日付','氏名')
def key(f,v): return score.nd(v) if f=='日付' else score.n(v)
def ok(v): return v is not None and str(v).strip()!='' and '■' not in str(v)
def combine(lists,need):
    """lists: 実行ごとの印影リスト。印影は並び順で対応させる"""
    n=max(len(l) for l in lists); out=[]
    for i in range(n):
        o={}
        for f in F:
            vals=[l[i].get(f) if i<len(l) else None for l in lists]
            if all(str(v or '').strip()=='' for v in vals): o[f]=''; continue     # 全員が「この項目はない」
            c=collections.Counter(key(f,v) for v in vals if ok(v))
            top=c.most_common(1)
            if top and top[0][1]>=need and len(c)==1 or (top and top[0][1]>=need and need<len(lists) and (len(c)==1 or c.most_common(2)[1][1]<top[0][1])):
                o[f]=next(v for v in vals if ok(v) and key(f,v)==top[0][0])
            else: o[f]='■'
        out.append(o)
    return out
def run(tags,need):
    tot=collections.Counter(); pages=0
    for pid in sorted(score.GT):
        lists=[]
        for t in tags:
            fs=glob.glob(f"{score.W}/results/{t}__{pid}.json")
            p=score.parse(json.load(open(fs[0]))['text']) if fs else None
            if p is not None: lists.append(p)
        if len(lists)<len(tags): continue
        k=len(lists) if need=='all' else int(need)
        r=score.score(json.dumps(combine(lists,k),ensure_ascii=False),pid); tot.update(r['cnt']); pages+=1
    nf=tot['氏名_n']+tot['日付_n']+tot['部署_n']; cf=tot['氏名']+tot['日付']+tot['部署']
    return dict(pages=pages,full=100*tot['全項目']/max(1,tot['全項目_n']),field=100*cf/max(1,nf),name=100*tot['氏名']/max(1,tot['氏名_n']),mis=tot['誤読'],unk=tot['読めないと回答']+tot['見落とし'],nf=nf)
def show(label,tags,need):
    r=run(tags,need); print(f"{label:58s} 頁{r['pages']:2d} 全項目{r['full']:5.1f} 項目{r['field']:5.1f} 氏名{r['name']:5.1f} | 誤読{r['mis']:3d} 読めない{r['unk']:3d} /{r['nf']}")
    return r
if __name__=="__main__":
    show(' + '.join(sys.argv[2:]),sys.argv[2:],sys.argv[1])
