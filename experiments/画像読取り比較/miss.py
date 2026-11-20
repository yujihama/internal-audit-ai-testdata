import sys,collections,score
rows=score.load(); tags=sys.argv[1:]
ids=sorted(score.MAN)
print('id          '+' '.join(f'{t[:22]:>22s}' for t in tags))
for i in ids:
    d={r['tag']:r for r in rows if r['id']==i}
    print(f'{i:12s}'+' '.join(f"{(str(d[t]['num'])+'/'+str(d[t]['num_n'])) if t in d else '-':>22s}" for t in tags))
for t in tags:
    print('\n##',t)
    for r in sorted((r for r in rows if r['tag']==t),key=lambda r:r['id']):
        if r['miss']: print(' ',r['id'],r['miss'])
