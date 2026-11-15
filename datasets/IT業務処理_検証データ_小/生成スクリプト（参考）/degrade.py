# -*- coding: utf-8 -*-
"""可読性を落とす加工。各関数は (画像, 座標変換行列) を返す。画像は RGB uint8、基準は200dpi"""
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont
from common import fp

DPI = 200
I3 = np.eye(3)


def mm2px(v):
    return v * DPI / 25.4


def lfn(h, w, cell, rng):
    s = rng.random((max(2, h // cell + 2), max(2, w // cell + 2))).astype(np.float32)
    return cv2.resize(s, (w, h), interpolation=cv2.INTER_CUBIC).clip(0, 1)


def jpeg(img, q):
    ok, buf = cv2.imencode('.jpg', cv2.cvtColor(img, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, int(q)])
    return cv2.cvtColor(cv2.imdecode(buf, cv2.IMREAD_COLOR), cv2.COLOR_BGR2RGB)


def pmask(h, w, ctx, pad=28, sig=40):
    m = np.zeros((h, w), np.float32)
    for (x0, y0, x1, y1) in ctx.get('protect', []):
        m[max(0, int(y0 - pad)):int(y1 + pad), max(0, int(x0 - pad)):int(x1 + pad)] = 1
    return cv2.GaussianBlur(m, (0, 0), sig) if m.any() else m


def inkgray(img):
    """白黒化（朱肉や青インクも黒く写る複写機・FAXの挙動に寄せる）"""
    return 0.5 * cv2.cvtColor(img, cv2.COLOR_RGB2GRAY).astype(np.float32) + 0.5 * img.min(axis=2).astype(np.float32)


def g2rgb(g):
    return cv2.cvtColor(np.clip(g, 0, 255).astype(np.uint8), cv2.COLOR_GRAY2RGB)


# ---------------- ページ全体の加工 ----------------
def op_skew(img, rng, ctx, deg):
    h, w = img.shape[:2]
    M = cv2.getRotationMatrix2D((w / 2, h / 2), deg, 1.0)
    M[0, 2] += rng.uniform(-10, 10)
    M[1, 2] += rng.uniform(-10, 10)
    bv = (45, 45, 45) if abs(deg) >= 1.5 else (252, 252, 252)
    out = cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=bv)
    return out, np.vstack([M, [0, 0, 1]])


def op_scan(img, rng, ctx):
    out = img.astype(np.float32) * 0.975 + rng.normal(0, 4, img.shape[:2])[..., None]
    return op_skew(np.clip(out, 0, 255).astype(np.uint8), rng, ctx, rng.uniform(-0.7, 0.7))


def op_fax(img, rng, ctx):
    h, w = img.shape[:2]
    g = inkgray(img)
    s = cv2.resize(g, (w // 2, h // 2), interpolation=cv2.INTER_AREA).astype(np.float32)
    s += rng.normal(0, 13, s.shape)
    b = (s > rng.uniform(150, 170)).astype(np.uint8) * 255
    n = rng.random(b.shape)
    b[n < 0.0022] = 0
    b[n > 0.9972] = 255
    for _ in range(int(rng.integers(2, 5))):
        y = int(rng.integers(60, b.shape[0] - 60))
        b[y:y + int(rng.integers(1, 3)), :] = 255
    if rng.random() < 0.5:
        x = int(rng.integers(30, b.shape[1] - 30))
        b[:, x:x + 1] = 0
    pil = Image.fromarray(b)
    d = ImageDraw.Draw(pil)
    d.rectangle((0, 0, b.shape[1], 19), fill=255)
    d.text((14, 2), ctx.get('faxhdr', ''), font=ImageFont.truetype(fp('D'), 14), fill=0)
    out = cv2.resize(np.array(pil), (w, h), interpolation=cv2.INTER_NEAREST)
    return g2rgb(out), I3


def op_faded(img, rng, ctx):
    h, w = img.shape[:2]
    k = rng.uniform(0.38, 0.48)
    mult = np.maximum(0.6 + 0.7 * lfn(h, w, 260, rng), 1.12 * pmask(h, w, ctx))
    out = 255 - (255 - img.astype(np.float32)) * (k * mult)[..., None]
    out = cv2.GaussianBlur(out, (0, 0), 0.7) + rng.normal(0, 2.5, (h, w))[..., None]
    out = out * np.array([1.0, 0.985, 0.935])
    return np.clip(out, 0, 255).astype(np.uint8), I3


def op_copy(img, rng, ctx):
    h, w = img.shape[:2]
    g = cv2.GaussianBlur(inkgray(img), (0, 0), 0.9)
    g = 255 / (1 + np.exp(-(g - rng.uniform(165, 186)) / 13))
    out = cv2.erode(g.astype(np.uint8), np.ones((2, 2), np.uint8)).astype(np.float32)
    void = cv2.dilate((rng.random((h, w)) < 0.0016).astype(np.uint8), np.ones((2, 2), np.uint8))
    out[void > 0] = 250
    n = rng.random((h, w))
    out[n < 0.0012] = 30
    out -= np.clip(cv2.GaussianBlur((rng.random((h, w)) < 0.00025).astype(np.float32), (0, 0), 1.6) * 900, 0, 255)
    edge = np.ones((h, w), np.float32)
    edge[:, :90] *= np.linspace(0.45, 1, 90)[None, :]
    edge[:70, :] *= np.linspace(0.6, 1, 70)[:, None]
    out = out * 0.94 * edge + rng.normal(0, 5, (h, w))
    return g2rgb(out), I3


def op_photo(img, rng, ctx):
    h, w = img.shape[:2]
    s = 0.8
    H2, W2 = int(h * s * 1.10), int(w * s * 1.12)
    base = np.array(ctx.get('desk', [(118, 92, 66), (70, 72, 78), (176, 170, 158)][int(rng.integers(0, 3))]), np.float32)
    desk = base + (lfn(H2, W2, 6, rng)[..., None] - 0.5) * 22 + (lfn(H2, W2, 300, rng)[..., None] - 0.5) * 30
    mx, my = W2 * 0.06, H2 * 0.05
    j = lambda a: rng.uniform(-a, a)
    dst = np.float32([[mx + j(W2 * 0.03), my + j(H2 * 0.025)], [W2 - mx + j(W2 * 0.03), my + j(H2 * 0.025)],
                      [W2 - mx + j(W2 * 0.03), H2 - my + j(H2 * 0.025)], [mx + j(W2 * 0.03), H2 - my + j(H2 * 0.025)]])
    Hm = cv2.getPerspectiveTransform(np.float32([[0, 0], [w, 0], [w, h], [0, h]]), dst)
    pre = cv2.GaussianBlur(img, (0, 0), 0.6)
    page = cv2.warpPerspective(pre, Hm, (W2, H2), flags=cv2.INTER_LINEAR).astype(np.float32)
    m = (cv2.warpPerspective(np.full((h, w), 255, np.uint8), Hm, (W2, H2)).astype(np.float32) / 255)[..., None]
    out = desk * (1 - m) + page * m * 0.97
    yy, xx = np.mgrid[0:H2, 0:W2].astype(np.float32)
    ang = rng.uniform(0, 2 * np.pi)
    light = 0.80 + 0.24 * ((xx / W2 - 0.5) * np.cos(ang) + (yy / H2 - 0.5) * np.sin(ang) + 0.5)
    cx, cy = rng.uniform(0.1, 0.9) * W2, float(rng.choice([0.03, 0.97])) * H2
    light *= 1 - 0.30 * np.exp(-(((xx - cx) / (W2 * 0.35)) ** 2 + ((yy - cy) / (H2 * 0.2)) ** 2))
    out = out * light[..., None] * np.array([1.03, 1.0, 0.9])
    for (x0, y0, x1, y1) in ctx.get('glare', []):
        q = Hm @ np.array([[x0, x1, x1, x0], [y0, y0, y1, y1], [1, 1, 1, 1.0]])
        q = q[:2] / q[2]
        cx, cy = q[0].mean(), q[1].mean()
        rx, ry = (q[0].max() - q[0].min()) / 2 * 1.2, (q[1].max() - q[1].min()) / 2 * 1.4
        gm = np.clip(1.7 * np.exp(-(((xx - cx) / rx) ** 4 + ((yy - cy) / ry) ** 4)), 0, 1)
        gm = np.maximum(gm, 0.5 * np.exp(-(((xx - cx) / (rx * 2.2)) ** 2 + ((yy - cy) / (ry * 0.5)) ** 2)))
        out = out + (255 - out) * gm[..., None]
    out = cv2.GaussianBlur(out, (0, 0), rng.uniform(0.8, 1.15)) + rng.normal(0, 4, (H2, W2, 1))
    return jpeg(np.clip(out, 0, 255).astype(np.uint8), rng.integers(40, 56)), Hm


def op_show(img, rng, ctx):
    h, w = img.shape[:2]
    other = ctx.get('other')
    if other is None:
        other = np.roll(img, int(rng.integers(150, 500)), axis=0)
    o = cv2.resize(cv2.cvtColor(other, cv2.COLOR_RGB2GRAY), (w, h))[:, ::-1]
    ink = (255 - cv2.GaussianBlur(o, (0, 0), 1.0).astype(np.float32)) * rng.uniform(0.34, 0.44)
    out = (img.astype(np.float32) - ink[..., None]) * np.array([0.985, 0.97, 0.92]) + rng.normal(0, 3, (h, w))[..., None]
    return op_skew(np.clip(out, 0, 255).astype(np.uint8), rng, ctx, rng.uniform(-0.8, 0.8))


def op_lowres(img, rng, ctx):
    s = rng.uniform(0.41, 0.46)
    small = cv2.resize(img, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
    return jpeg(small, rng.integers(16, 24)), np.diag([s, s, 1.0])


def op_carbon(img, rng, ctx):
    h, w = img.shape[:2]
    f = img.astype(np.float32)
    r, g, b = f[..., 0], f[..., 1], f[..., 2]
    keep = (((r > 140) & (g < 115) & (b < 115)) | ((b > r + 40) & (b > 90))).astype(np.float32)
    keep = cv2.GaussianBlur(cv2.dilate(keep, np.ones((3, 3), np.uint8)), (0, 0), 0.8)[..., None]
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY).astype(np.float32)
    ink = np.where(gray > 225, 0, (255 - gray) / 255.0).astype(np.float32)
    press = np.maximum(0.38 + 0.6 * lfn(h, w, 140, rng), 0.85 * pmask(h, w, ctx))
    ink = cv2.GaussianBlur(ink, (0, 0), 0.8) * press
    ink = np.clip(ink + np.roll(ink, (2, 3), (0, 1)) * 0.3, 0, 1)
    dust = cv2.GaussianBlur((rng.random((h, w)) < 0.0006).astype(np.float32), (0, 0), 1.2) * 2.0
    ink = np.clip(ink + dust, 0, 1)[..., None] * 0.85
    out = np.array([252, 240, 236], np.float32) * (1 - ink) + np.array([72, 62, 150], np.float32) * ink
    out = out * (1 - keep) + np.minimum(f, np.array([252, 240, 236], np.float32)) * keep
    out += rng.normal(0, 3, (h, w))[..., None]
    return np.clip(out, 0, 255).astype(np.uint8), I3


def op_rot(img, rng, ctx, k):
    h, w = img.shape[:2]
    out = np.ascontiguousarray(np.rot90(img, k))
    M = {1: np.array([[0, 1, 0], [-1, 0, w - 1], [0, 0, 1.0]]), 2: np.array([[-1, 0, w - 1], [0, -1, h - 1], [0, 0, 1.0]]),
         3: np.array([[0, -1, h - 1], [1, 0, 0], [0, 0, 1.0]])}[k]
    return out, M


def op_wavy(img, rng, ctx):
    h, w = img.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    dx = rng.uniform(4, 8) * np.sin(yy / rng.uniform(140, 220) + rng.uniform(0, 6)) + (lfn(h, w, 300, rng) - 0.5) * 10
    dy = rng.uniform(3, 6) * np.sin(xx / rng.uniform(200, 320) + rng.uniform(0, 6))
    out = cv2.remap(img, xx + dx, yy + dy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(255, 255, 255))
    return out, I3


def op_jitter(img, rng, ctx):
    out = img.copy()
    h, y = img.shape[0], 0
    prot = np.zeros(h, bool)
    for (x0, y0, x1, y1) in ctx.get('protect', []):
        prot[max(0, int(y0) - 6):int(y1) + 6] = True
    while y < h:
        t = int(rng.integers(12, 48))
        s = int(round(rng.normal(0, 2.2)))
        if rng.random() < 0.08:
            s = int(rng.integers(-16, 17))
        if prot[y:y + t].any():
            s = int(np.clip(s, -1, 1))
        if s:
            out[y:y + t] = np.roll(img[y:y + t], s, axis=1)
        y += t
    return out, I3


def op_shake(img, rng, ctx):
    k = int(rng.integers(5, 8))
    ang, c = rng.uniform(0, np.pi), (k - 1) / 2
    ker = np.zeros((k, k), np.float32)
    for i in np.linspace(-c, c, k * 3):
        ker[int(round(c + i * np.sin(ang))), int(round(c + i * np.cos(ang)))] = 1
    return cv2.filter2D(img, -1, ker / ker.sum()), I3


def op_streak(img, rng, ctx):
    h, w = img.shape[:2]
    m = np.zeros(w, np.float32)
    for _ in range(int(rng.integers(4, 8))):
        x, wd = int(rng.integers(60, w - 60)), int(rng.integers(5, 26))
        m[x:x + wd] = np.maximum(m[x:x + wd], rng.uniform(0.6, 0.95))
    m = cv2.GaussianBlur(m[None, :], (0, 0), 2)[0]
    m2 = m[None, :] * (1 - 0.72 * np.clip(pmask(h, w, ctx, 12, 10), 0, 1)) * (0.75 + 0.25 * lfn(h, w, 200, rng))
    out = 255 - (255 - img.astype(np.float32)) * (1 - m2[..., None])
    out = out * 0.975 + rng.normal(0, 4, (h, w))[..., None]
    return np.clip(out, 0, 255).astype(np.uint8), I3


def op_dark(img, rng, ctx):
    h, w = img.shape[:2]
    g = inkgray(img)
    out = (g * 0.5 + 12) * (0.78 + 0.42 * lfn(h, w, 400, rng))
    out = cv2.GaussianBlur(out, (0, 0), 0.6) + rng.normal(0, 10, (h, w))
    return g2rgb(out), I3


def op_dither(img, rng, ctx):
    h, w = img.shape[:2]
    g = cv2.resize(inkgray(img), (w // 2, h // 2), interpolation=cv2.INTER_AREA).astype(np.float32)
    g = 255 - (255 - g) * 0.8 - 22 + rng.normal(0, 6, g.shape)
    pil = Image.fromarray(np.clip(g, 0, 255).astype(np.uint8)).convert('1')
    out = cv2.resize(np.array(pil).astype(np.uint8) * 255, (w, h), interpolation=cv2.INTER_NEAREST)
    return g2rgb(out), I3


# 画面の写し用
def op_sslow(img, rng, ctx):
    s = rng.uniform(0.6, 0.68)
    small = cv2.resize(img, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
    return jpeg(small, rng.integers(24, 34)), np.diag([s, s, 1.0])


def op_ssphoto(img, rng, ctx):
    h, w = img.shape[:2]
    f = img.astype(np.float32)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    f *= (0.9 + 0.1 * np.sin(yy * 2.1 + xx * 0.02))[..., None]
    f *= (0.94 + 0.06 * np.sin(xx * 3.14))[..., None]
    H2, W2 = h + 160, w + 200
    pad = np.full((H2, W2, 3), 18, np.float32)
    pad[80:80 + h, 100:100 + w] = f * 0.92 + 14
    j = lambda a: rng.uniform(-a, a)
    dst = np.float32([[40 + j(30), 30 + j(25)], [W2 - 40 + j(30), 30 + j(25)], [W2 - 40 + j(30), H2 - 30 + j(25)],
                      [40 + j(30), H2 - 30 + j(25)]])
    Hm = cv2.getPerspectiveTransform(np.float32([[0, 0], [W2, 0], [W2, H2], [0, H2]]), dst)
    out = cv2.warpPerspective(pad, Hm, (W2, H2), flags=cv2.INTER_LINEAR, borderValue=(25, 22, 20))
    Y, X = np.mgrid[0:H2, 0:W2].astype(np.float32)
    cx, cy = rng.uniform(0.2, 0.8) * W2, rng.uniform(0.8, 0.95) * H2
    out += 40 * np.exp(-(((X - cx) / (W2 * 0.2)) ** 2 + ((Y - cy) / (H2 * 0.08)) ** 2))[..., None]
    out = cv2.GaussianBlur(out, (0, 0), rng.uniform(0.7, 1.0)) * np.array([0.97, 1.0, 1.05]) + rng.normal(0, 4, (H2, W2, 1))
    T = np.array([[1, 0, 100], [0, 1, 80], [0, 0, 1.0]])
    return jpeg(np.clip(out, 0, 255).astype(np.uint8), rng.integers(38, 52)), Hm @ T


OPS = {'scan': op_scan, 'fax': op_fax, 'faded': op_faded, 'copy': op_copy, 'photo': op_photo, 'show': op_show,
       'lowres': op_lowres, 'carbon': op_carbon, 'sslow': op_sslow, 'ssphoto': op_ssphoto, 'wavy': op_wavy,
       'jitter': op_jitter, 'shake': op_shake, 'streak': op_streak, 'dark': op_dark, 'dither': op_dither}
OPJ = {'scan': '通常のスキャン（軽いノイズ）', 'fax': 'FAX受信風（粗い・白黒2値・線抜け）', 'faded': '薄い・かすれ（むらあり）',
       'copy': '複写の繰り返し風（濃い・文字つぶれ・ごみ）', 'photo': 'スマホ撮影風（台形ゆがみ・影・ぼけ）', 'show': '裏写り',
       'lowres': '低解像度＋強い圧縮', 'carbon': '複写伝票風（青い薄い転写・濃淡むら）', 'sslow': '画面の写しを縮小＋強い圧縮',
       'ssphoto': '画面をスマホで撮影（縞模様・反射）', 'wavy': '紙のうねり（文字列が波打つ）', 'jitter': '送りムラ（行が左右にずれる）',
       'shake': '手ぶれ', 'streak': '印字かすれ（縦の白い筋）', 'dark': '暗い・コントラスト不足・ざらつき', 'dither': '粗い網点（FAX写真モード風）'}


def run_ops(img, spec, rng, ctx):
    """spec 例: 'faded+skew3' 'scan+rot90'。戻り値: 画像, 変換行列, 回転回数, 説明"""
    M, rotk, desc = I3.copy(), 0, []
    for name in [s for s in spec.split('+') if s]:
        if name.startswith('skew'):
            deg = float(name[4:]) * (1 if rng.random() < 0.5 else -1)
            img, m = op_skew(img, rng, ctx, deg)
            desc.append(f'傾き約{abs(deg):g}度')
        elif name.startswith('rot'):
            k = {'rot90': 1, 'rot180': 2, 'rot270': 3}[name]
            img, m = op_rot(img, rng, ctx, k)
            rotk += k
            desc.append({1: '90度回転（横倒し）', 2: '上下逆さま', 3: '270度回転（横倒し）'}[k])
        else:
            img, m = OPS[name](img, rng, ctx)
            desc.append(OPJ[name])
        M = m @ M
    return img, M, rotk % 4, '、'.join(desc)


# ---------------- 局所的な損傷（200dpiの原本座標で適用） ----------------
def _soft(h, w, box, sig, grow=0):
    x0, y0, x1, y1 = [int(v) for v in box]
    m = np.zeros((h, w), np.float32)
    m[max(0, y0 - grow):y1 + grow, max(0, x0 - grow):x1 + grow] = 1
    return cv2.GaussianBlur(m, (0, 0), sig)


def d_blotch(img, box, rng):
    h, w = img.shape[:2]
    x0, y0, x1, y1 = box
    cx, cy, rx, ry = (x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) / 2 * 1.3, (y1 - y0) / 2 * 1.35
    pts = [(cx + rx * rng.uniform(0.82, 1.12) * np.cos(a), cy + ry * rng.uniform(0.82, 1.12) * np.sin(a))
           for a in np.linspace(0, 2 * np.pi, 48, endpoint=False)]
    m = np.zeros((h, w), np.float32)
    cv2.fillPoly(m, [np.int32(pts)], 1.0)
    m = cv2.GaussianBlur(m, (0, 0), 5)[..., None] * (0.9 + 0.1 * rng.random((h, w, 1)))
    return np.clip(img * (1 - m) + 18 * m, 0, 255).astype(np.uint8)


def d_water(img, box, rng):
    h, w = img.shape[:2]
    m = _soft(h, w, box, 14, 10)
    blur = cv2.GaussianBlur(img, (0, 0), 12).astype(np.float32)
    dx = (lfn(h, w, 40, rng) - 0.5) * 60
    dy = (lfn(h, w, 40, rng) - 0.5) * 60
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    blur = cv2.remap(blur, xx + dx, yy + dy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    wet = (255 - (255 - blur) * 0.5) * np.array([0.97, 0.93, 0.83])
    out = img * (1 - m[..., None]) + wet * m[..., None]
    ring = np.exp(-((m - 0.45) / 0.07) ** 2)[..., None]
    out = out * (1 - 0.22 * ring) + np.array([120, 95, 60]) * 0.22 * ring
    return np.clip(out, 0, 255).astype(np.uint8)


def d_torn(img, box, rng):
    """左下の角が破れて欠損（box は三角形の外接矩形）"""
    x0, y0, x1, y1 = box
    n = 16
    hyp = [(x0 + (x1 - x0) * t + rng.uniform(-12, 12), y0 + (y1 - y0) * t + rng.uniform(-12, 12)) for t in np.linspace(0, 1, n)]
    poly = np.int32([(x0 - 5, y0)] + hyp + [(x1, y1 + 5), (x0 - 5, y1 + 5)])
    m = np.zeros(img.shape[:2], np.float32)
    cv2.fillPoly(m, [poly], 1.0)
    sh = cv2.GaussianBlur(m, (0, 0), 6)[..., None]
    out = img.astype(np.float32) * (1 - 0.35 * sh)
    return np.where(m[..., None] > 0.5, 38, out).clip(0, 255).astype(np.uint8)


def d_sticky(img, box, rng, text='あとで確認'):
    x0, y0, x1, y1 = [int(v) for v in box]
    w, h = x1 - x0, y1 - y0
    note = Image.new('RGBA', (w, h), (255, 232, 110, 255))
    d = ImageDraw.Draw(note)
    f = ImageFont.truetype(fp('H'), max(26, min(46, h // 4)))
    for i, l in enumerate(text.split('\n')):
        d.text((18, 14 + i * (f.size + 10)), l, font=f, fill=(30, 40, 120, 255))
    note = note.rotate(rng.uniform(-4, 4), expand=True, resample=Image.BICUBIC)
    pil = Image.fromarray(img).convert('RGBA')
    sh = Image.new('RGBA', note.size, (0, 0, 0, 60))
    sh.putalpha(note.getchannel('A').point(lambda v: 60 if v else 0))
    pil.alpha_composite(sh, (max(0, x0 + 5), max(0, y0 + 7)))
    pil.alpha_composite(note, (max(0, x0), max(0, y0)))
    return np.array(pil.convert('RGB'))


def d_glare(img, box, rng):
    h, w = img.shape[:2]
    x0, y0, x1, y1 = box
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    cx, cy, rx, ry = (x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) / 2 * 1.15, (y1 - y0) / 2 * 1.3
    m = np.clip(1.55 * np.exp(-(((xx - cx) / rx) ** 4 + ((yy - cy) / ry) ** 4)), 0, 1)[..., None]
    return np.clip(img + (255 - img) * m, 0, 255).astype(np.uint8)


def d_band(img, box, rng):
    out = img.copy()
    x0, y0, x1, y1 = [int(v) for v in box]
    row = out[y0 - 6:y0 - 5].copy()
    out[y0 - 6:y1 + 6] = row
    y = y0 - 6
    while y < y1 + 6:
        t = int(rng.integers(3, 16))
        if rng.random() < 0.6:
            out[y:y + t] = 0
        y += t + int(rng.integers(1, 9))
    return out


def d_stain(img, box, rng):
    h, w = img.shape[:2]
    x0, y0, x1, y1 = box
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    cx, cy, r = (x0 + x1) / 2, (y0 + y1) / 2, max(x1 - x0, y1 - y0) / 2
    dist = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / r
    a = (0.13 * (dist < 1) + 0.34 * np.exp(-((dist - 1) / 0.05) ** 2))[..., None]
    return np.clip(img * (1 - a) + np.array([112, 78, 40]) * a, 0, 255).astype(np.uint8)


def d_marker(img, box, rng):
    x0, y0, x1, y1 = [int(v) for v in box]
    out = img.astype(np.float32)
    out[y0:y1, x0:x1] *= np.array([1.0, 0.95, 0.42])
    return out.astype(np.uint8)


def d_punch(img, box, rng):
    out = img.copy()
    h = img.shape[0]
    for cy in (h / 2 - mm2px(40), h / 2 + mm2px(40)):
        cv2.circle(out, (int(mm2px(8.5)), int(cy)), int(mm2px(3)), (35, 35, 35), -1)
    return out


def d_fold(img, box, rng):
    h, w = img.shape[:2]
    y = (box[1] + box[3]) / 2 if box else h * rng.uniform(0.45, 0.55)
    yy = np.arange(h, dtype=np.float32)[:, None]
    a = 0.16 * np.exp(-((yy - y) / 14) ** 2) + 0.3 * np.exp(-((yy - y) / 1.5) ** 2)
    return np.clip(img * (1 - a[..., None]), 0, 255).astype(np.uint8)


DMG = {'blotch': (d_blotch, '黒い汚れ', 3), 'water': (d_water, '水濡れ・にじみ', 3), 'torn': (d_torn, '破れ・欠損', 3),
       'sticky': (d_sticky, '付箋の貼付', 3), 'glare': (d_glare, '撮影時の光の反射（白飛び）', 3),
       'band': (d_band, 'FAX送信不良の黒い帯', 3), 'stain': (d_stain, '染み（下の文字は読める）', 2),
       'marker': (d_marker, '蛍光ペン', 2), 'punch': (d_punch, 'パンチ穴', 2), 'fold': (d_fold, '折り目', 2)}
