"""書き起こし結果を正解テキストと突き合わせて採点する"""
import os,sys,json,re,glob,unicodedata,difflib,collections
W=os.path.dirname(os.path.abspath(__file__))
MAN={s['id']:s for s in json.load(open(W+'/samples/manifest.json'))}
def norm(s):
    s=unicodedata.normalize('NFKC',s)
    s=s.replace('￥','¥').replace('\\','¥')
    return re.sub(r'[\s,.:;/\-ー―─－—–_|()\[\]「」『』、。・*#`~〜～∼¥%〒■]','',s).upper().replace('O','0')
def hard_tokens(gt):
    # 数字を含むまとまり（金額・日付・番号・型番）。監査で読み違えると困る項目
    t=[]
    for line in unicodedata.normalize('NFKC',gt).split('\n'):
        for tok in re.split(r'[\s　:：]+',line):
            n=norm(tok)
            if re.search(r'\d',n) and len(n)>=3: t.append(n)
    return t
def score(text,gt):
    o=norm(text)
    hs=hard_tokens(gt); hit=sum(1 for h in hs if h in o)
    lines=[norm(l) for l in gt.split('\n')]; lines=[l for l in lines if len(l)>=2]
    lhit=sum(1 for l in lines if l in o)
    g=norm(gt)
    sm=difflib.SequenceMatcher(None,g,o,autojunk=False)
    match=sum(b.size for b in sm.get_matching_blocks())
    return dict(num=hit,num_n=len(hs),line=lhit,line_n=len(lines),ch=match,ch_n=len(g),miss=[h for h in hs if h not in o])
def load():
    rows=[]
    for f in glob.glob(W+'/results/*.json'):
        r=json.load(open(f)); s=MAN[r['id']]
        tag=os.path.basename(f).rsplit('__',1)[0]
        rows.append(dict(tag=tag,cat=s['cat'],**r,**score(r['text'],s['gt'])))
    return rows
if __name__=="__main__":
    rows=load(); pat=sys.argv[1] if len(sys.argv)>1 else ''
    by=collections.defaultdict(list)
    for r in rows:
        if pat in r['tag']: by[r['tag']].append(r)
    print(f"{'条件':62s} n  数字項目  行一致  文字一致 | lowres fax halftone | 入力tok 秒")
    def pc(rs,k): 
        n=sum(r[k+'_n'] for r in rs); return 100*sum(r[k] for r in rs)/n if n else float('nan')
    for tag,rs in sorted(by.items(),key=lambda kv:-pc(kv[1],'num')):
        cats=' '.join(f"{pc([r for r in rs if r['cat']==c],'num'):5.1f}" for c in('lowres','fax','halftone'))
        it=sum((r['usage'].get('input_tokens') or r['usage'].get('prompt_tokens') or 0) for r in rs)/len(rs)
        print(f"{tag:62s} {len(rs):2d} {pc(rs,'num'):6.1f} {pc(rs,'line'):6.1f} {pc(rs,'ch'):6.1f}   | {cats} | {it:6.0f} {sum(r['sec'] for r in rs)/len(rs):5.1f}")
