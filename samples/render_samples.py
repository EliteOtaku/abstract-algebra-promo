# -*- coding: utf-8 -*-
"""抽象代数宣传片 — 风格样张渲染
输出 4 张 1920x1080 静帧，验证「深空发光·金青」视觉体系。
"""
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1920, 1080
SS = 2                      # 2x 超采样抗锯齿
W2, H2 = W * SS, H * SS

# ---------- 调色板 ----------
BG      = (5, 8, 16)
GOLD    = (255, 200, 100)
GOLD_HI = (255, 234, 190)
CYAN    = (80, 214, 232)
CYAN_HI = (176, 246, 255)
VIOLET  = (150, 122, 255)
GRAY    = (152, 162, 178)

F_BOLD  = "C:/Windows/Fonts/msyhbd.ttc"
F_RGI   = "C:/Windows/Fonts/msyh.ttc"
F_NUM   = "C:/Windows/Fonts/arialbd.ttf"

def font(path, size):
    return ImageFont.truetype(path, int(size))

def canvas():
    return Image.new("RGB", (W2, H2), BG)

def composite(base, layers):
    """layers: [(PIL黑底亮字层, [(blur_radius, gain), ...]), ...] 加性发光合成"""
    out = np.asarray(base, dtype=np.float32).copy()
    for layer, passes in layers:
        for radius, gain in passes:
            b = layer.filter(ImageFilter.GaussianBlur(radius)) if radius > 0 else layer
            out += np.asarray(b, dtype=np.float32) * gain
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))

def finish(img, seed=7, grain=4.5):
    """暗角 + 胶片颗粒 + 降采样"""
    a = np.asarray(img, dtype=np.float32)
    h, w, _ = a.shape
    yy, xx = np.mgrid[0:h, 0:w]
    d = np.sqrt(((xx - w/2) / (w*0.62))**2 + ((yy - h/2) / (h*0.62))**2)
    vig = np.clip(1.04 - 0.5*np.clip(d - 0.35, 0, None)**1.5, 0.55, 1.04)[..., None]
    a *= vig
    a += np.random.default_rng(seed).normal(0, grain, a.shape)
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).resize((W, H), Image.LANCZOS)

def star_field(rng, n=260, rmax=1.15):
    """背景微光尘埃"""
    layer = Image.new("RGB", (W2, H2), (0, 0, 0))
    d = ImageDraw.Draw(layer)
    for _ in range(n):
        x, y = rng.uniform(0, W2), rng.uniform(0, H2)
        r = rng.uniform(0.8, 2.6) * SS
        b = rng.uniform(0.06, 0.30) ** 1.6
        col = (int(90 + 120*b), int(100 + 120*b), int(120 + 135*b))
        d.ellipse([x-r, y-r, x+r, y+r], fill=col)
    return layer

def chapter_marker(d, x, y, cn, en, color=GOLD):
    f1 = font(F_BOLD, 30*SS)
    f2 = font(F_NUM, 22*SS)
    d.rectangle([x, y, x + 56*SS, y + 5*SS], fill=color)
    d.text((x, y + 16*SS), cn, font=f1, fill=color)
    t = f"CHAPTER · {en}"
    xx = x
    for ch in t:
        d.text((xx, y + 62*SS), ch, font=f2, fill=(int(color[0]*0.6), int(color[1]*0.6), int(color[2]*0.6)))
        xx += d.textlength(ch, font=f2) + 3*SS

def text_tracked(d, y, s, f, fill, tracking=0, center_x=None):
    widths = [d.textlength(c, font=f) for c in s]
    total = sum(widths) + tracking * (len(s) - 1)
    x = (center_x - total/2) if center_x is not None else None
    for c, cw in zip(s, widths):
        if x is not None:
            d.text((x, y), c, font=f, fill=fill)
        else:
            d.text((None or 0, 0), "", font=f)  # never hit
        x = (x + cw + tracking) if x is not None else 0
    return total

def draw_tracked(d, x, y, s, f, fill, tracking=0):
    for c in s:
        d.text((x, y), c, font=f, fill=fill)
        x += d.textlength(c, font=f) + tracking

def grad_text(base, layer, y, s, f, c_top, c_bot, tracking=0, center_x=W2/2):
    """渐变大字：锐利本体贴 base，亮色副本贴 layer 作光源"""
    mask = Image.new("L", (W2, H2), 0)
    dm = ImageDraw.Draw(mask)
    widths = [dm.textlength(c, font=f) for c in s]
    total = sum(widths) + tracking*(len(s)-1)
    x = center_x - total/2
    for c, cw in zip(s, widths):
        dm.text((x, y), c, font=f, fill=255)
        x += cw + tracking
    bbox = mask.getbbox()
    if not bbox:
        return
    x0, y0, x1, y1 = bbox
    gh = max(y1 - y0, 1)
    t = np.linspace(0, 1, gh)[:, None]
    col = np.array(c_top, np.float32)[None, :]*(1-t) + np.array(c_bot, np.float32)[None, :]*t
    grad = np.zeros((H2, W2, 3), np.float32)
    grad[y0:y1, x0:x1] = np.broadcast_to(col[:, None, :], (gh, x1-x0, 3))
    gimg = Image.fromarray(grad.astype(np.uint8))
    layer.paste(gimg, (0, 0), mask)
    base.paste(gimg, (0, 0), mask)

# ============================================================
# 样张 1 — 对称：十二重旋转雪花
# ============================================================
def frame_symmetry():
    rng = np.random.default_rng(11)
    base = canvas()
    dust = star_field(rng)
    lay = Image.new("RGB", (W2, H2), (0, 0, 0))
    d = ImageDraw.Draw(lay)

    cx, cy = W2/2, H2*0.47
    R = 400*SS

    def rot(p, a):
        c, s = math.cos(a), math.sin(a)
        return (p[0]*c - p[1]*s, p[0]*s + p[1]*c)

    tips = []
    for k in range(12):
        a = k * math.pi / 6
        # 主枝：折线主干
        pts = [(0, 0), (0, -R*0.42), (-R*0.10, -R*0.55), (0, -R*0.66), (0, -R)]
        pts = [rot(p, a) for p in pts]
        d.line([(cx+p[0], cy+p[1]) for p in pts], fill=CYAN, width=int(2.6*SS))
        # 侧刺
        for t, ln in ((0.34, 0.16), (0.55, 0.11)):
            bx, by = 0, -R*t
            sp = [rot((bx, by), a), rot((bx + ln*R, by - ln*R*0.75), a)]
            d.line([(cx+p[0], cy+p[1]) for p in sp], fill=CYAN, width=int(1.8*SS))
        # 顶端菱形
        tp = rot((0, -R), a)
        tips.append((cx+tp[0], cy+tp[1]))
        s = 13*SS
        d.polygon([(tp[0], cy+tp[1]-cy-s), (tp[0]+s, cy+tp[1]-cy),
                   (tp[0], cy+tp[1]-cy+s), (tp[0]-s, cy+tp[1]-cy)], fill=GOLD)

    # 星形弦 {12/5}
    for k in range(12):
        p, q = tips[k], tips[(k+5) % 12]
        d.line([p, q], fill=(70, 120, 150), width=int(1.2*SS))
    # 内接六边形
    hexpts = [(cx + R*0.62*math.sin(k*math.pi/3), cy - R*0.62*math.cos(k*math.pi/3)) for k in range(6)]
    d.line(hexpts + [hexpts[0]], fill=(60, 130, 150), width=int(1.6*SS))
    # 外圈轨道（虚线）
    for k in range(72):
        a0, a1 = k*(2*math.pi/72), (k+0.55)*(2*math.pi/72)
        rr = R*1.16
        d.arc([cx-rr, cy-rr, cx+rr, cy+rr], math.degrees(a0), math.degrees(a1), fill=(60, 110, 130), width=int(1.4*SS))
    # 轨道游标
    mv = (cx + R*1.16*math.sin(2.1), cy - R*1.16*math.cos(2.1))
    d.ellipse([mv[0]-9*SS, mv[1]-9*SS, mv[0]+9*SS, mv[1]+9*SS], fill=GOLD_HI)
    # 中心核
    d.ellipse([cx-10*SS, cy-10*SS, cx+10*SS, cy+10*SS], fill=GOLD_HI)

    base = composite(base, [(dust, [(0, 1.0)])])
    base = composite(base, [(lay, [(14*SS, 0.55), (4*SS, 0.85), (0, 0.35)])])

    d2 = ImageDraw.Draw(base)
    chapter_marker(d2, 120*SS, 96*SS, "对称", "SYMMETRY")
    # 底部文案
    f_cap = font(F_BOLD, 44*SS)
    text = "对称，不是形状 —— 是动作"
    wpx = sum(d2.textlength(c, font=f_cap) for c in text)
    draw_tracked(d2, W2/2 - wpx/2, H2 - 148*SS, text, f_cap, GOLD_HI, tracking=4*SS)
    d2.line([W2/2-220*SS, H2-172*SS, W2/2+220*SS, H2-172*SS], fill=(90, 140, 160), width=int(1.5*SS))
    return finish(base, seed=21)

# ============================================================
# 样张 2 — 结构：Cayley 图绽放
# ============================================================
def frame_structure():
    rng = np.random.default_rng(23)
    base = canvas()
    dust = star_field(rng, n=220)
    lay = Image.new("RGB", (W2, H2), (0, 0, 0))
    d = ImageDraw.Draw(lay)

    cx, cy = W2/2, H2*0.47
    rings = [(0, 1), (120, 6), (235, 12), (355, 24), (480, 48)]
    scale = 0.80
    nodes = []           # nodes[i] = [(x,y), ...]
    for ri, (r, cnt) in enumerate(rings):
        rr, cc = r*scale*SS, cnt
        off = ri * 0.5 * (2*math.pi/cc if cc else 1)
        pts = []
        for j in range(cc):
            a = off + j*2*math.pi/cc
            jitter = rng.uniform(-6, 6)*SS if ri else 0
            pts.append((cx + (rr+jitter)*math.cos(a), cy + (rr+jitter)*math.sin(a)))
        nodes.append(pts)

    # 边：父子 + 环内弦
    for ri in range(1, len(nodes)):
        for j, p in enumerate(nodes[ri]):
            parent = nodes[ri-1][j // 2] if ri >= 2 else nodes[0][0]
            fade = max(0.25, 1.0 - ri*0.16)
            d.line([parent, p], fill=(int(CYAN[0]*fade*0.9), int(CYAN[1]*fade*0.9), int(CYAN[2]*fade*0.9)),
                   width=int(1.7*SS))
    for ri, pts in enumerate(nodes):
        n = len(pts)
        if n >= 12:
            for j in range(n):
                d.line([pts[j], pts[(j+2) % n]], fill=(46, 92, 112), width=int(1.1*SS))
    # 节点
    for ri, pts in enumerate(nodes):
        rad = (7.5 - ri*0.9)*SS
        for p in pts:
            d.ellipse([p[0]-rad, p[1]-rad, p[0]+rad, p[1]+rad], fill=GOLD if ri < 3 else (200, 180, 140))
    c0 = nodes[0][0]
    d.ellipse([c0[0]-12*SS, c0[1]-12*SS, c0[0]+12*SS, c0[1]+12*SS], fill=GOLD_HI)

    base = composite(base, [(dust, [(0, 1.0)])])
    base = composite(base, [(lay, [(13*SS, 0.5), (4*SS, 0.8), (0, 0.3)])])

    d2 = ImageDraw.Draw(base)
    chapter_marker(d2, 120*SS, 96*SS, "结构", "STRUCTURE")
    f_cap = font(F_BOLD, 44*SS)
    text = "把混乱的行动，蒸馏成干净的结构"
    wpx = sum(d2.textlength(c, font=f_cap) for c in text)
    draw_tracked(d2, W2/2 - wpx/2, H2 - 148*SS, text, f_cap, CYAN_HI, tracking=4*SS)
    d2.line([W2/2-260*SS, H2-172*SS, W2/2+260*SS, H2-172*SS], fill=(80, 130, 150), width=int(1.5*SS))
    return finish(base, seed=33)

# ============================================================
# 样张 3 — 片名字卡
# ============================================================
def frame_title():
    rng = np.random.default_rng(5)
    base = canvas()
    dust = star_field(rng, n=420)
    lay = Image.new("RGB", (W2, H2), (0, 0, 0))

    # 中央背后淡淡的同心环（钟面隐喻 Z/nZ）
    d = ImageDraw.Draw(lay)
    cx, cy = W2/2, H2*0.44
    for i, rr in enumerate((300, 390, 480)):
        a = 0.16 - i*0.04
        d.ellipse([cx-rr*SS, cy-rr*SS, cx+rr*SS, cy+rr*SS],
                  outline=(int(50*a*6), int(120*a*4), int(140*a*4)), width=int(1.4*SS))

    grad_text(base, lay, H2*0.30, "抽象代数", font(F_BOLD, 190*SS),
              GOLD_HI, (200, 140, 60), tracking=30*SS)

    base = composite(base, [(dust, [(0, 1.0)])])
    base = composite(base, [(lay, [(26*SS, 0.45), (9*SS, 0.65), (0, 0.28)])])

    d2 = ImageDraw.Draw(base)
    # 英文副题
    f_en = font(F_NUM, 30*SS)
    en = "THE  BEAUTY  OF  ABSTRACT  ALGEBRA"
    draw_tracked(d2, W2/2 - sum(d2.textlength(c, font=f_en) for c in en)/2, H2*0.30 + 250*SS,
                 en, f_en, (120, 150, 165), tracking=6*SS)
    # 中文 slogan
    f_sl = font(F_BOLD, 52*SS)
    sl = "变化之中，见永恒"
    draw_tracked(d2, W2/2 - sum(d2.textlength(c, font=f_sl) for c in sl)/2 - 6*SS, H2*0.66,
                 sl, f_sl, CYAN_HI, tracking=12*SS)
    # 菱形饰线
    y = H2*0.66 + 120*SS
    for sgn in (-1, 1):
        d2.line([W2/2 + sgn*90*SS, y, W2/2 + sgn*300*SS, y], fill=(90, 140, 160), width=int(1.4*SS))
    s = 8*SS
    d2.polygon([(W2/2, y-s), (W2/2+s, y), (W2/2, y+s), (W2/2-s, y)], fill=GOLD)
    return finish(base, seed=44, grain=3.8)

# ============================================================
# 样张 4 — 可能性：魔方状态球（4.3e19）
# ============================================================
def frame_statesphere():
    rng = np.random.default_rng(9)
    base = canvas()
    dust = star_field(rng, n=200)
    lay = Image.new("RGB", (W2, H2), (0, 0, 0))
    d = ImageDraw.Draw(lay)

    n = 2400
    i = np.arange(n) + 0.5
    phi = np.arccos(1 - 2*i/n)
    th = math.pi * (1 + 5**0.5) * i
    P = np.stack([np.cos(th)*np.sin(phi), np.sin(phi)*np.sin(theta_), np.cos(phi)], 1) \
        if False else np.stack([np.cos(th)*np.sin(phi), np.cos(phi), np.sin(th)*np.sin(phi)], 1)
    # 绕 Y 转 30°
    a = math.radians(30)
    Ry = np.array([[math.cos(a), 0, math.sin(a)], [0, 1, 0], [-math.sin(a), 0, math.cos(a)]])
    P = P @ Ry.T

    cx, cy, R, f = W2*0.66, H2*0.48, 280*SS, 2.2*SS
    zcam = 3.0
    z = P[:, 2]
    sx = cx + R * f * P[:, 0] / (zcam - z*0.55)
    sy = cy + R * f * P[:, 1] / (zcam - z*0.55)
    depth = (zcam - z*0.55)

    # 邻近连线（球面网格感）
    q = P[:900]
    D = np.sum((q[:, None, :] - q[None, :, :])**2, -1)
    np.fill_diagonal(D, 9e9)
    nb = np.argsort(D, 1)[:, :2]
    for pi in range(len(q)):
        zt = (q[pi, 2] + 1) / 2
        fade = 0.05 + 0.30 * zt
        for nj in nb[pi]:
            d.line([sx[pi], sy[pi], sx[nj], sy[nj]],
                   fill=(int(30+50*zt), int(70+90*zt), int(85+100*zt)), width=int(1.1*SS))

    # 节点：近处金亮、远处暗青
    order = np.argsort(-depth)
    for pi in order:
        zt = (P[pi, 2] + 1) / 2
        br = 0.25 + 0.75*zt
        rad = (1.1 + 2.6*zt) * SS
        col = (int(255*br), int(200*br), int(100*br)) if zt > 0.62 else (int(70*br), int(170*br), int(190*br))
        d.ellipse([sx[pi]-rad, sy[pi]-rad, sx[pi]+rad, sy[pi]+rad], fill=col)

    # 左侧逸散的混沌粒子（状态爆炸余韵）
    for _ in range(160):
        x = rng.uniform(W2*0.30, W2*0.56)
        y = rng.uniform(H2*0.18, H2*0.82)
        r = rng.uniform(0.8, 2.2)*SS
        b = rng.uniform(0.1, 0.5)
        d.ellipse([x-r, y-r, x+r, y+r], fill=(int(120*b), int(150*b), int(170*b)))

    base = composite(base, [(dust, [(0, 1.0)])])
    base = composite(base, [(lay, [(11*SS, 0.5), (3.5*SS, 0.85), (0, 0.3)])])

    d2 = ImageDraw.Draw(base)
    chapter_marker(d2, 120*SS, 96*SS, "可能性", "STATE SPACE")
    f_num = font(F_NUM, 56*SS)
    num = "43,252,003,274,489,856,000"
    draw_tracked(d2, 130*SS, H2*0.40, num, f_num, GOLD_HI, tracking=2*SS)
    f_cap = font(F_BOLD, 40*SS)
    draw_tracked(d2, 130*SS, H2*0.40 + 90*SS, "一个三阶魔方的全部状态", f_cap, (168, 180, 196), tracking=3*SS)
    draw_tracked(d2, 130*SS, H2*0.40 + 150*SS, "而群论，数得清它", f_cap, CYAN_HI, tracking=3*SS)
    return finish(base, seed=55)

if __name__ == "__main__":
    import os
    os.makedirs(r"D:\AI\AA-by-GLM\samples\out", exist_ok=True)
    for name, fn in [("1_symmetry", frame_symmetry), ("2_structure", frame_structure),
                     ("3_title", frame_title), ("4_state", frame_statesphere)]:
        img = fn()
        img.save(rf"D:\AI\AA-by-GLM\samples\out\{name}.png")
        print("done", name)
