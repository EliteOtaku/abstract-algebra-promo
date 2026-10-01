# -*- coding: utf-8 -*-
"""配乐合成：72 BPM 深空氛围五层体系 → out/audio/music.wav（48kHz 立体声）
层：Pad(全程) / 低频脉冲(S3-S5) / 章节琶音(S2-S5) / 转场Impact / 尾声收束
旁白时段自动 ducking -2.5dB。
"""
import json, math, os, wave

import numpy as np

SR = 48000
DUR = 150.0
N = int(SR * DUR)
ROOT = r"D:\AI\AA-by-GLM"
BEAT = 60.0 / 72.0          # 0.8333s
EIGHTH = BEAT / 2

# 场景边界（秒）
SB = {"S0": (0, 18), "S1": (18, 30), "S2": (30, 54), "S3": (54, 78),
      "S4": (78, 102), "S5": (102, 126), "S6": (126, 150)}

# 每幕和弦（Hz 数组，低→高）
CHORDS = {
    "S0": [110.00, 164.81, 246.94, 329.63],        # Am9 开放
    "S1": [87.31, 130.81, 174.61, 220.00],         # F
    "S2": [130.81, 196.00, 261.63, 392.00],        # C
    "S3": [98.00, 146.83, 196.00, 293.66],         # G
    "S4": [82.41, 123.47, 164.81, 246.94],         # Em
    "S5": [87.31, 130.81, 174.61, 220.00],         # F
    "S6": [110.00, 138.59, 164.81, 220.00],        # A 大（Picardy）
}


def t_axis():
    return np.arange(N, dtype=np.float64) / SR


def env_scene(t, scene, fade=3.0):
    """该幕和弦的起恰包络（进入时 3s 淡入）"""
    a, b = SB[scene]
    e = np.clip((t - a) / fade, 0, 1)
    e *= np.clip((b - t) / 0.8, 0, 1)
    return e


def add_tone(buf, t0, freq, dur, gain, tau, pan=0.0, partials=1):
    """在 buf[L]/buf[R] 上叠加一个衰减音（可带分音），t0 秒处开始"""
    i0 = int(t0 * SR)
    n = min(int(dur * SR), N - i0)
    if n <= 20:
        return
    tt = np.arange(n) / SR
    w = np.zeros(n)
    for k in range(1, partials + 1):
        w += np.sin(2 * np.pi * freq * k * tt + 0.13 * k) / (k ** 1.7)
    w *= np.exp(-tt / tau) * gain
    gl, gr = math.sqrt(0.5 * (1 - pan)), math.sqrt(0.5 * (1 + pan))
    buf[0][i0:i0 + n] += w * gl * 2 ** 0.5
    buf[1][i0:i0 + n] += w * gr * 2 ** 0.5


def render_pad(t):
    """深空 Pad：每幕和弦交叉淡化 + 分音失谐 + 慢呼吸"""
    out = np.zeros(N)
    for sc, tones in CHORDS.items():
        e = env_scene(t, sc, fade=3.5)
        if e.max() <= 0:
            continue
        acc = np.zeros(N)
        for f in tones:
            for det in (-0.0012, 0.0012):
                ph = 2 * np.pi * f * (1 + det) * t + hash((sc, f, det)) % 628 / 100.0
                for k in range(1, 5):
                    acc += np.sin(ph * k + 0.31 * k) / (k ** 1.8)
        out += acc * e
    breath = 1 + 0.15 * np.sin(2 * np.pi * 0.08 * t)
    return out * 0.05 * breath


def render_pulse_simple(t):
    out = np.zeros(N)
    for sc in ("S3", "S4", "S5"):
        a, b = SB[sc]
        root = CHORDS[sc][0] / 2
        for i in range(int((b - a) / BEAT)):
            t0 = a + i * BEAT
            i0 = int(t0 * SR)
            n = min(int(0.9 * SR), N - i0)
            if n <= 20:
                continue
            tt = np.arange(n) / SR
            w = np.sin(2 * np.pi * root * tt * np.exp(-tt * 0.9)) * np.exp(-tt / 0.30) * 0.32
            out[i0:i0 + n] += w
    return out


def render_arps(t):
    out = [np.zeros(N), np.zeros(N)]
    # S2 镜像琶音
    tones = CHORDS["S2"]
    pattern = [0, 1, 2, 3, 2, 1]
    a, b = SB["S2"]
    for i in range(int((b - a) / EIGHTH)):
        deg = pattern[i % len(pattern)]
        add_tone(out, a + i * EIGHTH, tones[deg % 4] * (2 if deg >= 4 else 1),
                 0.8, 0.15, 0.30, pan=0.55 * (1 if i % 2 else -1), partials=2)
    # S3 上行
    tones = CHORDS["S3"]
    ext = tones + [tones[0] * 2, tones[1] * 2]
    a, b = SB["S3"]
    for i in range(int((b - a) / EIGHTH)):
        add_tone(out, a + i * EIGHTH, ext[i % 6], 0.7, 0.13, 0.28,
                 pan=0.5 * (1 if i % 2 else -1), partials=2)
    # S4 钟声双音
    tones = CHORDS["S4"]
    a, b = SB["S4"]
    for i in range(int((b - a) / (BEAT * 2))):
        t0 = a + i * BEAT * 2
        add_tone(out, t0, tones[2], 2.2, 0.11, 1.1, pan=-0.3, partials=3)
        add_tone(out, t0 + 0.02, tones[3], 2.2, 0.09, 1.1, pan=0.3, partials=3)
    # S5 十六分 shimmer
    rng = np.random.default_rng(7)
    tones = np.array(CHORDS["S5"])
    a, b = SB["S5"]
    n16 = int((b - a) / (EIGHTH / 2))
    for i in range(n16):
        f = float(rng.choice(tones) * rng.choice([2, 2, 4]))
        add_tone(out, a + i * EIGHTH / 2, f, 0.35, 0.075, 0.10,
                 pan=float(rng.uniform(-0.7, 0.7)), partials=1)
    return out[0] + out[1]


def render_impacts():
    out = [np.zeros(N), np.zeros(N)]
    hits = [18.0, 30.0, 54.0, 78.0, 102.0, 126.0]
    amp = {18.0: 0.55, 30.0: 0.60, 54.0: 0.45, 78.0: 0.42, 102.0: 0.50, 126.0: 0.55}
    rng = np.random.default_rng(11)
    for h in hits:
        i0 = int(h * SR)
        n = min(int(2.2 * SR), N - i0)
        tt = np.arange(n) / SR
        f = 150 * np.exp(-tt * 2.6) + 38
        boom = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt / 0.9) * amp[h]
        noise = rng.normal(0, 1, n) * np.exp(-tt / 0.22) * amp[h] * 0.5
        k = 10
        noise = np.convolve(noise, np.ones(k) / k, mode="same")   # 简易低通
        # 立体声展宽：噪声左右去相关
        nz2 = rng.normal(0, 1, n) * np.exp(-tt / 0.22) * amp[h] * 0.5
        nz2 = np.convolve(nz2, np.ones(k) / k, mode="same")
        out[0][i0:i0 + n] += boom + noise
        out[1][i0:i0 + n] += boom + nz2
    return out[0] + out[1]


def render_ending(t):
    """138-149 尾声 A 大和弦涌起，147 后全片淡出在主混统一做"""
    a, b = 138.0, 149.0
    e = np.clip((t - a) / 5.0, 0, 1) ** 2 * np.clip((b - t) / 1.2, 0, 1)
    out = np.zeros(N)
    for f, g in [(220.0, 1.0), (277.18, 0.8), (329.63, 0.9), (440.0, 0.7), (659.26, 0.4)]:
        out += np.sin(2 * np.pi * f * t + 0.5) * g
    return out * e * 0.045


def duck_gain(plan_path):
    env = np.ones(N)
    if not os.path.exists(plan_path):
        return env
    with open(plan_path, encoding="utf-8") as f:
        plan = json.load(f)
    for seg in plan["segments"]:
        s, e = seg["start"] - 0.35, seg["end"] + 0.45
        i0, i1 = max(0, int(s * SR)), min(N, int(e * SR))
        r = int(0.45 * SR)
        env[i0:i1] = 0.75
        env[max(0, i0 - r):i0] = np.linspace(1, 0.75, min(r, i0))
        env[i1:min(N, i1 + r)] = np.linspace(0.75, 1, min(r, N - i1))
    return env


def main():
    t = t_axis()
    print("pad...", flush=True)
    pad = render_pad(t)
    print("pulse...", flush=True)
    music = pad + render_pulse_simple(t)
    print("arps...", flush=True)
    music += render_arps(t)
    print("impacts...", flush=True)
    music += render_impacts()
    print("ending...", flush=True)
    music += render_ending(t)
    music *= duck_gain(os.path.join(ROOT, "out", "audio", "narration_plan.json"))
    music *= np.clip(t / 4.0, 0, 1)                       # 淡入
    music *= np.clip((149.6 - t) / 2.6, 0, 1)             # 淡出
    # 立体声：Haas 微展宽
    d = int(0.011 * SR)
    L = music.copy()
    R = np.concatenate([np.zeros(d), music[:-d]])
    mix = np.stack([L, R], 1)
    mix = np.tanh(mix * 1.1)
    mix *= 0.92 / max(1e-9, np.abs(mix).max())
    pcm = (mix * 32767).astype(np.int16)
    with wave.open(os.path.join(ROOT, "out", "audio", "music.wav"), "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    print(f"music.wav 写出完成 {DUR}s, peak={np.abs(mix).max():.3f}")


if __name__ == "__main__":
    main()
