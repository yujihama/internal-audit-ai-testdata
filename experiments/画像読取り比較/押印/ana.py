"""追加検証（設定・自動の名簿・確信度・モデル間の照合）の集計"""
import ens,score,json,glob,collections
M=('gpt-6.2-sol','gpt-6.1-sol','gpt-6-sol')
def sub(tag,ids):   # 一部のページだけで集計
    c=collections.Counter()
    for pid in ids:
        f=glob.glob(f"results/{tag}__{pid}.json"); c.update(score.score(json.load(open(f[0]))['text'],pid)['cnt'])
    return f"全項目{100*c['全項目']/c['全項目_n']:5.1f} 誤読{c['誤読']:3d} 読めない{c['読めないと回答']:3d}"
ids=open('.xhigh_ids').read().strip().split(',')
print('## effort（6.1-sol、誤読が出た10ページ）')
for e in ('raw__effort-low','raw','raw__effort-high','raw__effort-xhigh'): print(f'  {e:20s}',sub('gpt-6.1-sol__'+e,ids))
def conf(m,th):   # 確信度が th 未満の項目を ■ にして採点
    c=collections.Counter()
    for pid in sorted(score.GT):
        p=score.parse(json.load(open(f"results/{m}__raw+conf__{pid}.json"))['text']) or []
        for o in p:
            for f in ens.F:
                try: v=float(o.get(f+'_確信度',0))
                except Exception: v=0
                if ens.ok(o.get(f)) and v<th: o[f]='■'
        c.update(score.score(json.dumps(p,ensure_ascii=False),pid)['cnt'])
    return f"全項目{100*c['全項目']/c['全項目_n']:5.1f} 誤読{c['誤読']:3d} 読めない{c['読めないと回答']+c['見落とし']:3d}"
for m in M:
    print('##',m)
    S=lambda lab,tags,need='all': ens.show('  '+lab,[m+'__'+t for t in tags],need)
    S('そのまま1回',['raw'],1); S('自動の名簿 1回',['raw+self'],1)
    S('自動の名簿 2通り（そのまま・前処理）が一致',['raw+self','auto+self'])
    S('自動の名簿2通り＋名簿なしそのまま が一致',['raw+self','auto+self','raw'])
    S('自動の名簿2通り＋名簿なし拡大 が一致',['raw+self','auto+self','up2'])
    S('自動の名簿2通り＋名簿なし3通り（5通り）が一致',['raw+self','auto+self','raw','auto','up2'])
    S('同上 5通り中4以上が一致',['raw+self','auto+self','raw','auto','up2'],4)
    S('（参考）名簿なし3通りが一致',['raw','auto','up2'])
    for th in (0,60,70,80,90,95): print(f'  確信度{th:3d}以上だけ採用                                       ',conf(m,th))
print('## 6.2-solを照合役にする（名簿なし）')
for m in M[1:]:
    ens.show(f'  {m} そのまま ＋ 6.2 そのまま が一致',[m+'__raw','gpt-6.2-sol__raw'],'all')
    ens.show(f'  {m} 自動の名簿 ＋ 6.2 自動の名簿 が一致',[m+'__raw+self','gpt-6.2-sol__raw+self'],'all')
    ens.show(f'  {m} 自動の名簿2通り ＋ 6.2 自動の名簿2通り が一致',[x+'__'+t for x in (m,'gpt-6.2-sol') for t in ('raw+self','auto+self')],'all')
