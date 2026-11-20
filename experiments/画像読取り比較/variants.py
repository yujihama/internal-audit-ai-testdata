"""モデルに渡す前の画像の加工方法。build() は [(画像バイト列, 種類)], 指示文 を返す
名前は + でつなげて組み合わせる。例: smooth+up2+tile2x3+strict"""
import io
import numpy as np, cv2
from PIL import Image
def png(im):
    b=io.BytesIO(); im.save(b,'PNG'); return b.getvalue(),'image/png'
STRICT="\n\n注意：会社名・住所・郵便番号・電話番号・型番・番号・金額は、一般知識やもっともらしさで補正せず、1文字ずつ画像に見えるとおりに書いてください。数字は桁を1つずつ確認してください。"
TILE="\n\n（同じ1ページを、重なりを持たせて{n}枚に分割した画像を、左上から右下の順に渡します。重なり部分の重複は1回だけ書き、ページ全体を1つの書き起こしにまとめてください。）"
def tiles(im,nx,ny,ov=0.12):
    w,h=im.size
    if w>h: nx,ny=ny,nx          # 横長のページは分割の向きを入れ替える
    tw=w/(nx-(nx-1)*ov); th=h/(ny-(ny-1)*ov); out=[]
    for j in range(ny):
        for i in range(nx):
            x=int(i*tw*(1-ov)); y=int(j*th*(1-ov))
            out.append(im.crop((x,y,min(w,int(x+tw)+1),min(h,int(y+th)+1))))
    return out
def build(var,path,prompt):
    steps=var.split('+')
    if steps==['raw']:
        return [(open(path,'rb').read(),'image/png' if path.endswith('.png') else 'image/jpeg')],prompt
    im=Image.open(path).convert('RGB'); parts=None
    for s in steps:
        if s=='raw': pass
        elif s=='strict': prompt+=STRICT
        elif s.startswith('up'):      # 拡大（なめらかに補間）
            f=float(s[2:]); im=im.resize((int(im.width*f),int(im.height*f)),Image.LANCZOS)
        elif s.startswith('down'):    # 長辺を指定の画素数に縮小
            m=int(s[4:]); f=m/max(im.size); im=im.resize((int(im.width*f),int(im.height*f)),Image.LANCZOS) if f<1 else im
        elif s=='smooth':             # 網点や白黒2値のざらつきをならす（グレー化＋軽いぼかし）
            g=cv2.cvtColor(np.array(im),cv2.COLOR_RGB2GRAY); g=cv2.GaussianBlur(g,(0,0),1.1); im=Image.fromarray(g).convert('RGB')
        elif s=='median':             # ごま塩ノイズを消す
            g=cv2.cvtColor(np.array(im),cv2.COLOR_RGB2GRAY); g=cv2.medianBlur(g,3); im=Image.fromarray(g).convert('RGB')
        elif s=='contrast':           # 明るさのむらをならしてコントラストを上げる
            g=cv2.cvtColor(np.array(im),cv2.COLOR_RGB2GRAY); g=cv2.createCLAHE(2.0,(8,8)).apply(g); im=Image.fromarray(g).convert('RGB')
        elif s=='auto':               # 画像の状態を見て加工を自動で選ぶ
            g=cv2.cvtColor(np.array(im),cv2.COLOR_RGB2GRAY)
            ink=g<215; b=(g<128).astype(np.uint8)
            mid=(g[ink]>=40).mean() if ink.any() else 1.0   # インク部分に中間の濃さがどれだけあるか
            iso=(b!=cv2.medianBlur(b,3)).mean()             # 孤立した点の多さ
            binary=mid<0.2 or iso>0.04                      # 白黒2値（FAX）または網点
            if binary: im=Image.fromarray(cv2.GaussianBlur(g,(0,0),1.1)).convert('RGB')
            if max(im.size)<1500: im=im.resize((im.width*2,im.height*2),Image.LANCZOS)   # 小さい画像は2倍に拡大
        elif s.startswith('tile'):
            nx,ny=map(int,s[4:].split('x')); parts=tiles(im,nx,ny); prompt+=TILE.format(n=len(parts))
        else: raise ValueError(s)
    return [png(p) for p in (parts or [im])],prompt
