# -*- coding: utf-8 -*-
"""六幕场景渲染器。每个场景: render(frame_np, tl, t_abs, fi)
frame_np: H2xW2x3 float32 加性画布（已含星野底）"""
import math

import numpy as np
from PIL import Image, ImageDraw

from common import (PAL, F_BOLD, F_REG, F_NUM, W2, H2, SS, FPS,
                    font, clamp01, ease_out, ease_io, smoothstep, rot2,
                    GlowComp, make_text, make_chapter, scatter, dust_layer,
                    draw_bar)

GOLD, GOLD_HI = PAL["GOLD"], PAL["GOLD_HI"]
CYAN, CYAN_HI = PAL["CYAN"], PAL["CYAN_HI"]
DIM = PAL["DIM"]
GRAY = PAL["GRAY"]

# ============ S0 序章·微光 ============
def s0(frame_np, tl, ta, fi):
    # 中心光粒：缓慢增强 + 微呼吸 + 多层光晕
    e = ease_io(tl / 18.0, 1.6)
    cx, cy = W2 / 2, H2 / 2
    glow = e * (0.75 + 0.25 * math.sin(ta * 1.7))
    # 三层光晕：外晕/中晕/核心
    scatter(frame_np, [cx], [cy], 90, np.array([[36 * glow, 42 * glow, 55 * glow]], np.float32))
    scatter(frame_np, [cx], [cy], 38, np.array([[120 * glow, 130 * glow, 150 * glow]], np.float32))
    r = (3 + 5 * e) * SS
    scatter(frame_np, [cx], [cy], r, np.array([np.array(GOLD_HI, np.float32) * glow], np.float32))
    # 末段光环炸开（17s 起）
    if tl > 16.6:
        k = (tl - 16.6) / 1.4
        rr = (60 + 1500 * ease_out(k, 2.2)) * SS
        n = 140
        angs = np.linspace(0, 2 * math.pi, n, endpoint=False)
        xs = cx + rr * np.cos(angs)
        ys = cy + rr * np.sin(angs)
        fade = (1 - k) ** 1.5
        cols = np.tile(np.array(CYAN, np.float32) * fade * 1.4, (n, 1))
        scatter(frame_np, xs, ys, 9, cols)

# ============ S1 片名 ============
_TITLE = None
def _title_sprites():
    global _TITLE
    if _TITLE is None:
        f = font(F_BOLD, 380)
        _TITLE = make_text("抽象代数", f, GOLD_HI, tracking=60, grad=(GOLD_HI, (200, 140, 60)))
    return _TITLE

_EN = None
def _en_sprite():
    global _EN
    if _EN is None:
        f = font(F_NUM, 56)
        _EN = make_text("THE  BEAUTY  OF  ABSTRACT  ALGEBRA", f, (120, 150, 165), tracking=14)
    return _EN

def s1(frame_np, tl, ta, fi):
    sp = _title_sprites()
    # 逐字亮起：0-2.4s 内四个字依次
    per = 0.55
    a_full = smoothstep(0.0, 2.6, tl)
    glow_gain = 0.8 + 0.35 * math.sin(ta * 2.2)
    sp.draw(frame_np, W2 / 2, H2 * 0.40, alpha=a_full, glow_gain=glow_gain)
    en = _en_sprite()
    en.draw(frame_np, W2 / 2, H2 * 0.40 + 250 * SS, alpha=smoothstep(2.2, 3.6, tl), glow_gain=0.7)
    # 背后同心环缓转（画在发光层）
    comp = GlowComp()
    # 环用 scatter 模拟：三圈虚线点
    for i, rr in enumerate((300, 390, 480)):
        n = 90
        base = ta * (0.05 + 0.02 * i)
        angs = np.linspace(0, 2 * math.pi, n, endpoint=False) + base
        xs = W2 / 2 + rr * SS * np.cos(angs)
        ys = H2 * 0.44 + rr * SS * np.sin(angs)
        b = 0.10 - 0.02 * i
        cols = np.tile(np.array([50 * b * 6, 110 * b * 4, 130 * b * 4], np.float32), (n, 1))
        scatter(frame_np, xs, ys, 5, cols)
    # 出白闪（10.8s 后）
    if tl > 10.8:
        k = clamp01((tl - 10.8) / 1.2)
        frame_np += (1 - k) ** 2 * 255 * 0.9

# ============ S2 对称 ============
def s2(frame_np, tl, ta, fi):
    cx, cy = W2 / 2, H2 * 0.47
    R = 400 * SS
    tilt = smoothstep(14.0, 22.0, tl)                      # 后段伪3D倾斜
    zoom = 1 + 0.16 * smoothstep(14.0, 24.0, tl)
    grow = ease_io(tl / 5.0, 2.2)                          # 枝干生长
    spin0 = smoothstep(4.5, 9.0, tl)                       # 开始旋转
    ang0 = 0.30 * ease_io((tl - 4.5) / 19.0, 1.4) if tl > 4.5 else 0.0
    ang0 += ta * 0.028 * spin0

    comp = GlowComp()
    lay = Image.new("RGB", (W2, H2), (0, 0, 0))
    d = ImageDraw.Draw(lay)

    tips = []
    for k in range(12):
        a = ang0 + k * math.pi / 6
        L = R * grow
        pts = [(0, 0), (0, -L * 0.42), (-L * 0.10, -L * 0.55), (0, -L * 0.66), (0, -L)]
        pts = [rot2(px_, py_, a) for px_, py_ in pts]
        pts = [(cx + p[0] * zoom, cy + p[1] * zoom * (1 - 0.16 * tilt)) for p in pts]
        d.line(pts, fill=CYAN, width=int(2.6 * SS))
        for tfrac, ln in ((0.34, 0.16), (0.55, 0.11)):
            bx, by = 0, -L * tfrac
            q1 = rot2(bx, by, a)
            q2 = rot2(bx + ln * L, by - ln * L * 0.75, a)
            d.line([(cx + q1[0] * zoom, cy + q1[1] * zoom * (1 - 0.16 * tilt)),
                    (cx + q2[0] * zoom, cy + q2[1] * zoom * (1 - 0.16 * tilt))],
                   fill=CYAN, width=int(1.8 * SS))
        tp = rot2(0, -L, a)
        px, py = cx + tp[0] * zoom, cy + tp[1] * zoom * (1 - 0.16 * tilt)
        tips.append((px, py, a))
        s = 13 * SS * zoom
        d.polygon([(px, py - s), (px + s, py), (px, py + s), (px - s, py)],
                  fill=GOLD if grow > 0.98 else GOLD_HI)

    # 星形弦：8s 后依次点亮
    if tl > 8.0:
        for k in range(12):
            lit = clamp01((tl - 8.0 - k * 0.22) / 0.8)
            if lit <= 0:
                continue
            p, q = tips[k], tips[(k + 5) % 12]
            col = (int(70 + 40 * lit), int(120 + 30 * lit), int(150 + 30 * lit))
            d.line([p[:2], q[:2]], fill=col, width=int(1.2 * SS))
    # 内接六边形 + 外圈轨道
    if grow > 0.95:
        hexpts = [(cx + R * 0.62 * zoom * math.sin(a + ang0), cy - R * 0.62 * zoom * (1 - 0.16 * tilt) * math.cos(a + ang0)) for a in [k * math.pi / 3 for k in range(6)]]
        d.line(hexpts + [hexpts[0]], fill=(60, 130, 150), width=int(1.6 * SS))
        rr = R * 1.16
        for k in range(72):
            a0 = k * (2 * math.pi / 72) + ang0
            a1 = a0 + 0.55 * (2 * math.pi / 72)
            steps = 6
            arc = [(cx + rr * zoom * math.sin(a0 + (a1 - a0) * i / steps),
                    cy - rr * zoom * (1 - 0.16 * tilt) * math.cos(a0 + (a1 - a0) * i / steps)) for i in range(steps + 1)]
            d.line(arc, fill=(60, 110, 130), width=int(1.4 * SS))
        # 游标
        ma = ta * 0.9 + 2.1
        mv = (cx + rr * zoom * math.sin(ma), cy - rr * zoom * (1 - 0.16 * tilt) * math.cos(ma))
        d.ellipse([mv[0] - 9 * SS, mv[1] - 9 * SS, mv[0] + 9 * SS, mv[1] + 9 * SS], fill=GOLD_HI)
    d.ellipse([cx - 10 * SS, cy - 10 * SS, cx + 10 * SS, cy + 10 * SS], fill=GOLD_HI)

    comp.add(lay, [(14 * SS, 0.55), (4 * SS, 0.85), (0, 0.35)])
    frame_np += comp.acc

    # 章节标记与底部字幕
    _chapter_badge(frame_np, "对称", "SYMMETRY", GOLD, alpha=smoothstep(0.4, 1.6, tl))
    cap = _cap("对称，不是形状 —— 是动作", GOLD_HI)
    cap.draw(frame_np, W2 / 2, H2 - 130 * SS, alpha=smoothstep(1.0, 2.6, tl) * (1 - smoothstep(21.5, 23.5, tl)), glow_gain=0.55)

# ============ S3 结构 ============
_CAY = None
def _cayley():
    """预生成 Cayley 图布局（BFS 5 层，每层 2^n，但 48 太密取 2^5=32 上限画 5 层）"""
    global _CAY
    if _CAY is None:
        rng = np.random.default_rng(23)
        rings = [(0, 1), (120, 6), (235, 12), (355, 24), (480, 46)]
        scale = 0.80
        nodes, layers = [], []
        for ri, (r, cnt) in enumerate(rings):
            rr, cc = r * scale * SS, cnt
            off = ri * 0.5 * (2 * math.pi / cc if cc else 1)
            pts = []
            for j in range(cc):
                a = off + j * 2 * math.pi / cc
                jit = rng.uniform(-6, 6) * SS if ri else 0
                pts.append((W2 / 2 + (rr + jit) * math.cos(a), H2 * 0.47 + (rr + jit) * math.sin(a)))
            nodes.append(pts)
            layers.append(ri)
        edges = []
        for ri in range(1, len(nodes)):
            for j, p in enumerate(nodes[ri]):
                parent = nodes[ri - 1][j // 2] if ri >= 2 else nodes[0][0]
                edges.append((parent, p, ri))
        _CAY = (nodes, edges)
    return _CAY

def s3(frame_np, tl, ta, fi):
    nodes, edges = _cayley()
    cx, cy = W2 / 2, H2 * 0.47
    pull = 1 - 0.22 * smoothstep(8.0, 24.0, tl)            # 镜头拉远
    sway = 0.06 * math.sin(ta * 0.4)

    lay = Image.new("RGB", (W2, H2), (0, 0, 0))
    d = ImageDraw.Draw(lay)
    # 边：按层生长
    for p, q, ri in edges:
        lit = clamp01((tl - ri * 1.35) / 0.9)
        if lit <= 0:
            continue
        x0, y0 = p
        x1, y1 = q
        x0, y0 = cx + (x0 - cx) * pull * (1 + sway * 0.2), cy + (y0 - cy) * pull
        x1, y1 = cx + (x1 - cx) * pull * (1 + sway * 0.2), cy + (y1 - cy) * pull
        fade = max(0.25, 1.0 - ri * 0.16) * lit
        d.line([x0, y0, x0 + (x1 - x0) * lit, y0 + (y1 - y0) * lit],
               fill=(int(CYAN[0] * fade * 0.9), int(CYAN[1] * fade * 0.9), int(CYAN[2] * fade * 0.9)),
               width=int(1.7 * SS))
    # 节点
    for ri, pts in enumerate(nodes):
        appear = clamp01((tl - ri * 1.35 - 0.4) / 0.8)
        if appear <= 0:
            continue
        rad = (7.5 - ri * 0.9) * SS * (0.5 + 0.5 * appear)
        for p in pts:
            x, y = cx + (p[0] - cx) * pull * (1 + sway * 0.2), cy + (p[1] - cy) * pull
            col = GOLD if ri < 3 else (200, 180, 140)
            d.ellipse([x - rad, y - rad, x + rad, y + rad], fill=col)
    c0 = nodes[0][0]
    d.ellipse([c0[0] - 12 * SS, c0[1] - 12 * SS, c0[1] * 0 + c0[0] + 12 * SS, c0[1] + 12 * SS], fill=GOLD_HI)

    comp = GlowComp()
    # 沿边脉冲光（矢量化 scatter）
    if tl > 3.0:
        n_p = 46
        rng = np.random.default_rng(fi)
        ei = rng.integers(0, len(edges), n_p)
        ph = rng.uniform(0, 1, n_p)
        for m in range(n_p):
            p, q, ri = edges[ei[m]]
            tt = (ph[m] + ta * 0.35) % 1.0
            x = p[0] + (q[0] - p[0]) * tt
            y = p[1] + (q[1] - p[1]) * tt
            x = cx + (x - cx) * pull
            y = cy + (y - cy) * pull
            b = (1 - ri * 0.13) * math.sin(tt * math.pi)
            scatter(frame_np, [x], [y], 7, np.array([[120 * b, 200 * b, 220 * b]], np.float32))
    comp.add(lay, [(13 * SS, 0.5), (4 * SS, 0.8), (0, 0.3)])
    frame_np += comp.acc

    _chapter_badge(frame_np, "结构", "STRUCTURE", CYAN_HI, alpha=smoothstep(0.4, 1.6, tl))
    cap = _cap("把混乱的行动，蒸馏成干净的结构", CYAN_HI)
    cap.draw(frame_np, W2 / 2, H2 - 130 * SS, alpha=smoothstep(1.0, 2.6, tl) * (1 - smoothstep(21.5, 23.5, tl)), glow_gain=0.55)

# ============ S4 不变量 ============
def s4(frame_np, tl, ta, fi):
    comp = GlowComp()
    lay = Image.new("RGB", (W2, H2), (0, 0, 0))
    d = ImageDraw.Draw(lay)

    # ---- 左：三叶结（标准参数式 + 呼吸形变，拓扑不变）----
    cxl, cyl = W2 * 0.30, H2 * 0.46
    stretch = 1.0 + 0.28 * math.sin(ta * 0.55)
    n = 560
    tt = np.linspace(0, 2 * math.pi, n, endpoint=False)
    # (sin t + 2 sin 2t, cos t - 2 cos 2t) 标准三叶结投影
    kx = np.sin(tt) + 2.0 * np.sin(2 * tt)
    ky = np.cos(tt) - 2.0 * np.cos(2 * tt)
    # 轻微扰动（随时间平滑，幅度小，不改变缠绕）
    kx += 0.12 * np.sin(3 * tt + ta * 0.8)
    ky += 0.12 * np.cos(4 * tt - ta * 0.6)
    x = cxl + kx * 78 * SS * stretch
    y = cyl + ky * 78 * SS * stretch
    pts = np.stack([x, y], 1)
    d.line([tuple(p) for p in pts[::2]], fill=CYAN, width=int(2.4 * SS))
    d.line([tuple(pts[-1]), tuple(pts[0])], fill=CYAN, width=int(2.4 * SS))
    comp.add(lay, [(12 * SS, 0.5), (3.5 * SS, 0.85), (0, 0.3)])
    frame_np += comp.acc

    # 拧度徽章（恒定）
    badge = _badge("拧度  ≡ 3", GOLD_HI)
    badge.draw(frame_np, cxl, cyl + 300 * SS, alpha=smoothstep(1.2, 2.4, tl), glow_gain=0.5)

    # ---- 右：立方体骨架连续形变 + Euler 公式 ----
    comp2 = GlowComp()
    lay2 = Image.new("RGB", (W2, H2), (0, 0, 0))
    d2 = ImageDraw.Draw(lay2)
    cxr, cyr = W2 * 0.72, H2 * 0.44
    size = 200 * SS
    morph = 0.5 + 0.5 * math.sin(ta * 0.42)          # 0=立方体 1=扭曲体
    verts = []
    for i in (-1, 1):
        for j in (-1, 1):
            for k in (-1, 1):
                vx, vy, vz = i * size, j * size, k * size
                vx += 60 * SS * morph * math.sin(2.1 * j + ta * 0.5)
                vy += 60 * SS * morph * math.sin(1.7 * k + ta * 0.45)
                verts.append((vx, vy, vz))
    faces = [(0, 1, 3, 2), (4, 5, 7, 6), (0, 1, 5, 4), (2, 3, 7, 6), (0, 2, 6, 4), (1, 3, 7, 5)]
    edges = set()
    for f in faces:
        for a, b in zip(f, f[1:] + f[:1]):
            edges.add((min(a, b), max(a, b)))
    ay, ax = ta * 0.22, 0.5 + 0.18 * math.sin(ta * 0.13)
    proj = []
    for vx, vy, vz in verts:
        vx, vz = rot2(vx, vz, ay)
        vy, vz = rot2(vy, vz, ax)
        f = 2.6 / (3.0 - vz / size)
        proj.append((cxr + vx * f, cyr + vy * f))
    for a, b in edges:
        d2.line([proj[a], proj[b]], fill=GOLD, width=int(2.4 * SS))
    for p in proj:
        d2.ellipse([p[0] - 5 * SS, p[1] - 5 * SS, p[0] + 5 * SS, p[1] + 5 * SS], fill=GOLD_HI)
    comp2.add(lay2, [(12 * SS, 0.5), (3.5 * SS, 0.85), (0, 0.3)])
    frame_np += comp2.acc

    eq = _eq_sprite()
    eq.draw(frame_np, cxr, cyr + 340 * SS, alpha=smoothstep(2.0, 3.4, tl), glow_gain=0.7)

    _chapter_badge(frame_np, "不变量", "INVARIANTS", GOLD, alpha=smoothstep(0.4, 1.6, tl))
    cap = _cap("变化之中，有些东西永远不变", GOLD_HI)
    cap.draw(frame_np, W2 / 2, H2 - 130 * SS, alpha=smoothstep(1.0, 2.6, tl) * (1 - smoothstep(21.5, 23.5, tl)), glow_gain=0.55)

_EQ = None
def _eq_sprite():
    global _EQ
    if _EQ is None:
        f = font(F_NUM, 88)
        _EQ = make_text("V - E + F = 2", f, GOLD_HI, tracking=6)
    return _EQ

# ============ S5 可能性 ============
_FB = None
def _fib_sphere():
    global _FB
    if _FB is None:
        n = 2400
        i = np.arange(n) + 0.5
        phi = np.arccos(1 - 2 * i / n)
        th = math.pi * (1 + 5 ** 0.5) * i
        P = np.stack([np.cos(th) * np.sin(phi), np.cos(phi), np.sin(th) * np.sin(phi)], 1)
        _FB = P.astype(np.float32)
    return _FB

def s5(frame_np, tl, ta, fi):
    P = _fib_sphere()
    cx, cy = W2 * 0.62, H2 * 0.48
    R = 300 * SS
    zcam = 3.0
    converge = ease_io((tl - 3.0) / 6.0, 2.0)          # 0=混沌 1=成球
    converge = clamp01(converge)
    a = math.radians(30 + ta * 3.0)                     # 缓转
    Ry = np.array([[math.cos(a), 0, math.sin(a)], [0, 1, 0], [-math.sin(a), 0, math.cos(a)]], np.float32)
    Prot = P @ Ry.T

    rng = np.random.default_rng(9000 + fi // 2)
    chaos = rng.normal(0, 1, P.shape).astype(np.float32) * np.array([1.7, 1.0, 1.0], np.float32)
    Pm = chaos * (1 - converge) + Prot * converge

    z = Pm[:, 2]
    depth = zcam - z * 0.55
    sx = cx + R * 2.2 * Pm[:, 0] / depth
    sy = cy + R * 2.2 * Pm[:, 1] / depth
    zt = ((z + 1) / 2).clip(0, 1)
    br = (0.25 + 0.75 * zt) * (0.35 + 0.65 * converge + 0.1)
    gold_mask = zt > 0.62
    cols = np.where(gold_mask[:, None],
                    np.stack([255 * br, 200 * br, 100 * br], 1),
                    np.stack([70 * br, 170 * br, 190 * br], 1))
    rad = 3 + 2.0 * zt
    for r0 in (2, 4, 6):                     # 三档半径批量散布
        m = ((rad.astype(int)) == r0)
        if m.any():
            scatter(frame_np, sx[m], sy[m], r0 + 2, cols[m].astype(np.float32) * 0.55)

    # 数字滚动（左侧）
    target = 43252003274489856000
    prog = ease_out(clamp01((tl - 2.0) / 9.0), 2.4)
    val = int(target * (1 - (1 - prog) ** 2))
    num = f"{val:,}"
    sp = _num_sprite(num)
    sp.draw(frame_np, 130 * SS + sp.w / 2, H2 * 0.36, alpha=0.92, glow_gain=0.6)
    for i, txt in enumerate(("一个三阶魔方的全部状态", "而群论，数得清它")):
        s = _cap_small(txt, GOLD_HI if i else GRAY)
        s.draw(frame_np, 130 * SS + s.w / 2, H2 * 0.36 + 78 * SS + i * 56 * SS,
               alpha=smoothstep(4.0 + i * 2.5, 5.6 + i * 2.5, tl), glow_gain=0.4)
    # 徽章
    if tl > 16.0:
        b = _badge("≤ 20 步回到原点", GOLD_HI)
        b.draw(frame_np, cx, cy + 350 * SS, alpha=smoothstep(16.0, 17.4, tl), glow_gain=0.8)

    _chapter_badge(frame_np, "可能性", "STATE SPACE", GOLD, alpha=smoothstep(0.4, 1.6, tl))

_NUM = {}
def _num_sprite(s):
    if s not in _NUM:
        if len(_NUM) > 40:          # 滚动阶段精灵缓存上限，防内存膨胀
            _NUM.clear()
        f = font(F_NUM, 108)
        _NUM[s] = make_text(s, f, GOLD_HI, tracking=4)
    return _NUM[s]

# ============ S6 尾声 ============
def s6(frame_np, tl, ta, fi):
    # 回流星轨：向中心汇聚
    cx, cy = W2 / 2, H2 * 0.44
    n = 900
    rng = np.random.default_rng(fi // 3)
    angs = rng.uniform(0, 2 * math.pi, n)
    r0 = rng.uniform(1.0, 2.4, n) * W2 * 0.75
    prog = ease_io(tl / 10.0, 1.8)
    rr = r0 * (1 - 0.86 * prog)
    xs = cx + rr * np.cos(angs + ta * 0.22)
    ys = cy + rr * np.sin(angs + ta * 0.22) * 0.9
    br = (0.25 + 0.75 * rng.uniform(0, 1, n)) * (0.4 + 0.6 * (1 - prog * 0.4))
    cols = np.stack([220 * br, 190 * br, 120 * br], 1).astype(np.float32)
    for r0 in (3, 5, 7):
        m = (rng.integers(0, 3, n) == {3: 0, 5: 1, 7: 2}[r0])
        if m.any():
            scatter(frame_np, xs[m], ys[m], r0, cols[m])

    # 片名重现
    sp = _title_sprites()
    alpha = smoothstep(6.0, 8.5, tl)
    if alpha > 0:
        sp.draw(frame_np, W2 / 2, H2 * 0.38, alpha=alpha, glow_gain=0.9 + 0.2 * math.sin(ta * 2.0))
    en = _en_sprite()
    en.draw(frame_np, W2 / 2, H2 * 0.38 + 270 * SS, alpha=smoothstep(7.2, 8.8, tl), glow_gain=0.6)
    # slogan
    sl = _slogan()
    sl.draw(frame_np, W2 / 2, H2 * 0.70, alpha=smoothstep(9.5, 11.5, tl), glow_gain=0.7)
    # 菱形饰线
    if tl > 11.0:
        a = smoothstep(11.0, 12.4, tl)
        y = H2 * 0.70 + 130 * SS
        ln = np.array([(cx - 300 * SS * a, y), (cx - 90 * SS, y)], np.float32)
        scatter(frame_np, np.linspace(ln[0, 0], ln[0, 1], 60), np.full(60, y), 3,
                np.tile(np.array([90, 140, 160], np.float32) * a, (60, 1)))
        scatter(frame_np, np.linspace(cx + 90 * SS, cx + 300 * SS * a, 60), np.full(60, y), 3,
                np.tile(np.array([90, 140, 160], np.float32) * a, (60, 1)))
        scatter(frame_np, [cx], [y], 8, np.tile(np.array(GOLD, np.float32) * a, (1, 1)))

    _chapter_badge(frame_np, "尾声", "COD A".replace(" ", ""), CYAN_HI, alpha=smoothstep(0.4, 1.6, tl))

_SL = None
def _slogan():
    global _SL
    if _SL is None:
        f = font(F_BOLD, 104)
        _SL = make_text("变化之中，见永恒", f, CYAN_HI, tracking=22)
    return _SL

# ============ 公共小件 ============
_BADGE_C = {}
def _badge(text, color):
    key = (text, color)
    if key not in _BADGE_C:
        f = font(F_BOLD, 64)
        _BADGE_C[key] = make_text(text, f, color, tracking=8)
    return _BADGE_C[key]

_CAPC = {}
def _cap(text, color):
    key = (text, color)
    if key not in _CAPC:
        f = font(F_BOLD, 88)
        _CAPC[key] = make_text(text, f, color, tracking=8)
    return _CAPC[key]

_CAPS = {}
def _cap_small(text, color):
    key = (text, color)
    if key not in _CAPS:
        f = font(F_BOLD, 76)
        _CAPS[key] = make_text(text, f, color, tracking=6)
    return _CAPS[key]

_CH = {}
def _chapter_badge(frame_np, cn, en, color, alpha=1.0):
    if alpha <= 0:
        return
    key = (cn, en)
    if key not in _CH:
        _CH[key] = make_chapter(cn, en, color)
    main, sub = _CH[key]
    x, y = 120 * SS, 96 * SS
    # 实体金条
    draw_bar(frame_np, x, y, color, alpha=alpha)
    main.draw(frame_np, x + main.w / 2, y + 40 * SS + main.h / 2, alpha=alpha, glow_gain=0.5 * alpha)
    sub.draw(frame_np, x + sub.w / 2, y + 84 * SS + sub.h / 2, alpha=alpha * 0.9, glow_gain=0.3 * alpha)

SCENE_FN = {
    "S0": s0, "S1": s1, "S2": s2, "S3": s3, "S4": s4, "S5": s5, "S6": s6,
}
