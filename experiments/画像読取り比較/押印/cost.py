"""目印ファイルより後に保存された実行結果から、使ったトークン数と推定額を出す（sol系: 入力$2・出力$10／100万トークン）"""
import glob,json,os,collections
W=os.path.dirname(os.path.abspath(__file__)); t0=os.path.getmtime(W+'/.budget_start'); c=collections.defaultdict(lambda:[0,0,0]); 
for f in glob.glob(W+'/results/gpt-*.json'):
    if os.path.getmtime(f)<t0: continue
    r=json.load(open(f)); u=r['usage']; tag=os.path.basename(f).rsplit('__',1)[0]; x=c[tag]; x[0]+=1; x[1]+=u.get('input_tokens',0); x[2]+=u.get('output_tokens',0)
tot=0
for tag,x in sorted(c.items()):
    d=(x[1]*2+x[2]*10)/1e6; tot+=d; print(f'{tag:40s} {x[0]:3d}回 入力{x[1]/1e3:7.0f}k 出力{x[2]/1e3:6.0f}k  ${d:.2f}')
print(f'累計の推定額 ${tot:.2f}')
