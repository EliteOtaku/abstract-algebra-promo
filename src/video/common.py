# -*- coding: utf-8 -*-
"""公共渲染引擎：调色板 / 缓动 / 辉光合成 / 文字精灵 / 粒子散布 / 后处理"""
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

FPS = 30
W, H = 1920, 1080
SS = 2
W2, H2 = W * SS, H * SS

PAL = dict(
    BG=(5, 8, 16),
    GOLD=(255, 200, 100), GOLD_HI=(255, 234, 190),
    CYAN=(80, 214, 232), CYAN_HI=(176, 246, 255),
    VIOLET=(150, 122, 255),
    GRAY=(152, 162, 178),
    DIM=(60, 110, 130),
)
F_BOLD = "C:/Windows/Fonts/msyhbd.ttc"
F_REG = "C:/Windows/Fonts/msyh.ttc"
F_NUM = "C:/Windows/Fonts/arialbd.ttf"

_font_cache = {}
def font(path, size):
    key = (path, int(size))
    if key not in _font_cache:
        _font_cache[key] = ImageFont.truetype(path, int(size))
    return _font_cache[key]

# ---------------- 缓动 ----------------
def clamp01(x):
    return max(0.0, min(1.0, x))

def ease_out(t, k=3.0):
    t = clamp01(t)
    return 1 - (1 - t) ** k

def ease_io(t, k=2.0):
    t = clamp01(t)
    return t ** k / (t ** k + (1 - t) ** k)

def pulse(t, period, duty=0.5):
    ph = (t / period) % 1.0
    return 1.0 if ph < duty else 0.0

def smoothstep(a, b, x):
    t = clamp01((x - a) / (b - a))
    return t * t * (3 - 2 * t)

def rot2(x, y, ang):
    c, s = math.cos(ang), math.sin(ang)
    return x * c - y * s, x * s + y * c

# ---------------- 辉光合成 ----------------
def fast_blur(img, radius):
    """大半径模糊用降采样近似，视觉等效但快一个量级"""
    r = int(radius)
    if r <= 6:
        return img.filter(ImageFilter.GaussianBlur(r))
    k = 3
    small = img.resize((max(1, img.width // k), max(1, img.height // k)), Image.BILINEAR)
    return small.filter(ImageFilter.GaussianBlur(max(1, r // k))).resize(img.size, Image.BICUBIC)

class GlowComp:
    """加性辉光合成器：accumulate = Σ blur(layer)*gain，首次 add 按层尺寸分配"""
    def __init__(self):
        self.acc = None

    def add(self, layer_img, passes):
        if self.acc is None:
            self.acc = np.zeros((layer_img.height, layer_img.width, 3), dtype=np.float32)
        for radius, gain in passes:
            b = fast_blur(layer_img, radius) if radius > 0 else layer_img
            self.acc += np.asarray(b, dtype=np.float32) * gain

    def result(self):
        return Image.fromarray(np.clip(self.acc, 0, 255).astype(np.uint8))

# ---------------- 文字精灵 ----------------
class TextSprite:
    """预渲染文字：sharp（黑底彩色文字）+ 覆盖率掩码 + glow（发光源）。
    绘制时按覆盖率混合，背景透过精灵透明区，不会带黑框。"""
    def __init__(self, sharp_rgb, glow_rgb):
        self.sharp = sharp_rgb                      # HxWx3 float32 0..255
        self.glow = glow_rgb
        self.h, self.w = sharp_rgb.shape[:2]
        lum = sharp_rgb.max(2, keepdims=True)
        self.cov = np.clip(lum / 72.0, 0, 1)        # 覆盖率：文字实体≈1，边缘渐变

    def draw(self, base_np, cx, cy, alpha=1.0, glow_gain=1.0):
        x0 = int(cx - self.w / 2); y0 = int(cy - self.h / 2)
        x1, y1 = x0 + self.w, y0 + self.h
        bx0, by0 = max(0, x0), max(0, y0)
        bx1, by1 = min(base_np.shape[1], x1), min(base_np.shape[0], y1)
        if bx1 <= bx0 or by1 <= by0:
            return
        sx0, sy0 = bx0 - x0, by0 - y0
        region = base_np[by0:by1, bx0:bx1]
        sh = self.sharp[sy0:sy0 + by1 - by0, sx0:sx0 + bx1 - bx0]
        cov = self.cov[sy0:sy0 + by1 - by0, sx0:sx0 + bx1 - bx0] * alpha
        base_np[by0:by1, bx0:bx1] = region * (1 - cov) + sh * cov
        if glow_gain > 0 and alpha > 0:
            base_np[by0:by1, bx0:bx1] += self.glow[sy0:sy0 + by1 - by0, sx0:sx0 + bx1 - bx0] * (alpha * glow_gain)


def _render_text_layer(size, draw_fn):
    lay = Image.new("RGB", size, (0, 0, 0))
    d = ImageDraw.Draw(lay)
    draw_fn(d, lay)
    return lay


def make_text(text, fnt, fill, tracking=0.0, grad=None):
    """返回 TextSprite；grad=(top_color, bottom_color) 时做渐变"""
    tmp = Image.new("RGB", (8, 8))
    dm = ImageDraw.Draw(tmp)
    widths = [dm.textlength(c, font=fnt) for c in text]
    asc, desc = fnt.getmetrics()
    tw = int(sum(widths) + tracking * max(0, len(text) - 1)) + 8
    th = asc + desc + 8

    def _draw(d, lay):
        x = 4.0
        for c, cw in zip(text, widths):
            d.text((x, 4), c, font=fnt, fill=fill)
            x += cw + tracking

    sharp_lay = _render_text_layer((tw, th), _draw)
    if grad:
        arr = np.asarray(sharp_lay, dtype=np.float32)
        lum = arr.max(2)
        ys, xs = np.nonzero(lum > 8)
        if len(ys) == 0:
            sharp = arr
        else:
            y0, y1 = ys.min(), ys.max()
            gh = y1 - y0 + 1
            t = np.linspace(0, 1, gh)[:, None, None]
            gradmap = (np.array(grad[0], np.float32) * (1 - t) + np.array(grad[1], np.float32) * t)
            arr[y0:y1 + 1] = arr[y0:y1 + 1] / (arr[y0:y1 + 1].max(2, keepdims=True) + 1e-6) * gradmap
        sharp_lay = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    sharp = np.asarray(sharp_lay, dtype=np.float32)
    glow = sharp * 0.9
    return TextSprite(sharp, glow)


def make_chapter(cn, en, color):
    """章节标记：金条 + 中文 + 英文小字，返回 TextSprite 组 (主 sprite, 相对布局)"""
    f1 = font(F_BOLD, 60)
    f2 = font(F_NUM, 42)
    main = make_text(cn, f1, color, tracking=6)
    sub = make_text("CHAPTER · " + en, f2,
                    (int(color[0] * .62), int(color[1] * .62), int(color[2] * .62)), tracking=6)
    return main, sub


# ---------------- 粒子散布（矢量化） ----------------
_SPR = {}
def _sprite(radius):
    key = int(radius)
    if key not in _SPR:
        r = max(1, key)
        yy, xx = np.mgrid[-r:r + 1, -r:r + 1].astype(np.float32)
        q = np.sqrt(xx ** 2 + yy ** 2) / r
        k = np.exp(-(q ** 2) / (2 * 0.45 ** 2))
        taper = np.clip((1 - q) / 0.3, 0, 1) ** 1.5      # 边界处归零，消除方框感
        k = k * taper
        _SPR[key] = (k / k.max()).astype(np.float32)
    return _SPR[key]

def scatter(acc, xs, ys, radius, colors):
    """acc: HxWx3 float32；xs,ys: 像素坐标数组；colors: Nx3 0..255
    用高斯小sprite加性散布，比 PIL ellipse + 全屏模糊快得多"""
    k = _sprite(radius)
    r = k.shape[0] // 2
    Hh, Ww = acc.shape[:2]
    xi = np.round(xs).astype(np.int64)
    yi = np.round(ys).astype(np.int64)
    ok = (xi >= r) & (xi < Ww - r) & (yi >= r) & (yi < Hh - r)
    xi, yi, cols = xi[ok], yi[ok], colors[ok]
    if len(xi) == 0:
        return
    vals = cols[:, None, None, :] * k[None, :, :, None]          # N x K x K x 3
    ys_ix = yi[:, None] + np.arange(-r, r + 1)[None, :]
    xs_ix = xi[:, None] + np.arange(-r, r + 1)[None, :]
    flat = (ys_ix[:, :, None] * Ww + xs_ix[:, None, :]).ravel()  # N x K x K
    np.add.at(acc.reshape(-1, 3), flat.ravel(), vals.reshape(-1, 3))

# ---------------- 星野 ----------------
_dust_cache = {}
def dust_layer(seed=7, n=420):
    key = (seed, n)
    if key not in _dust_cache:
        rng = np.random.default_rng(seed)
        lay = Image.new("RGB", (W2, H2), (0, 0, 0))
        d = ImageDraw.Draw(lay)
        for _ in range(n):
            x, y = rng.uniform(0, W2), rng.uniform(0, H2)
            r = rng.uniform(0.8, 2.4) * SS
            b = rng.uniform(0.07, 0.34) ** 1.6
            d.ellipse([x - r, y - r, x + r, y + r],
                      fill=(int(90 + 120 * b), int(100 + 120 * b), int(120 + 135 * b)))
        _dust_cache[key] = lay
    return _dust_cache[key]

# ---------------- 实体小条（章节金条） ----------------
_BAR = {}
def bar_sprite(color):
    key = tuple(color)
    if key not in _BAR:
        bw, bh = 56 * SS, 5 * SS
        img = Image.new("RGB", (bw + 24, bh + 24), (0, 0, 0))
        dd = ImageDraw.Draw(img)
        dd.rectangle([12, 12, 12 + bw, 12 + bh], fill=color)
        img = img.filter(ImageFilter.GaussianBlur(3))
        _BAR[key] = np.asarray(img, dtype=np.float32)
    return _BAR[key]

def draw_bar(frame_np, x, y, color, alpha=1.0):
    sp = bar_sprite(color) * alpha
    h, w = sp.shape[:2]
    frame_np[y:y + h, x:x + w] += sp

# ---------------- 后处理 ----------------
_VIG = None
def _vignette():
    global _VIG
    if _VIG is None:
        h, w = H2, W2
        yy, xx = np.mgrid[0:h:2, 0:w:2].astype(np.float32)
        d = np.sqrt(((xx - w / 2) / (w * 0.62)) ** 2 + ((yy - h / 2) / (h * 0.62)) ** 2)
        v = np.clip(1.04 - 0.5 * np.clip(d - 0.35, 0, None) ** 1.5, 0.55, 1.04)
        _VIG = np.repeat(np.repeat(v, 2, 0), 2, 1)[..., None]
    return _VIG

def finish(img_np, frame_idx, grain=4.2):
    """暗角 + 降采样 + 输出域胶片颗粒；img_np: H2xW2x3 float32"""
    a = img_np * _vignette()
    img = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).resize((W, H), Image.LANCZOS)
    arr = np.asarray(img, dtype=np.float32)
    rng = np.random.default_rng((frame_idx * 2654435761) % (2 ** 32))
    arr += rng.normal(0, grain, arr.shape).astype(np.float32)
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))

# ---------------- 场景表 ----------------
SCENES = [
    ("S0", 0.0, 18.0), ("S1", 18.0, 30.0), ("S2", 30.0, 54.0),
    ("S3", 54.0, 78.0), ("S4", 78.0, 102.0), ("S5", 102.0, 126.0),
    ("S6", 126.0, 150.0),
]
CUTS = [18.0, 30.0, 54.0, 78.0, 102.0, 126.0]
TOTAL = 150.0

def scene_of(t):
    for name, a, b in SCENES:
        if a <= t < b:
            return name, t - a, b - a
    return SCENES[-1][0], t - SCENES[-1][1], SCENES[-1][2] - SCENES[-1][1]
