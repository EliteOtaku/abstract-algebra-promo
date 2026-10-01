# -*- coding: utf-8 -*-
"""把 narration_S*.wav 按 narration_plan.json 铺到 150s 时间轴 → narration.wav (mono 48k)"""
import json, os, wave

import numpy as np

ROOT = r"D:\AI\AA-by-GLM"
SR = 48000
DUR = 150.0
N = int(SR * DUR)

with open(os.path.join(ROOT, "out", "audio", "narration_plan.json"), encoding="utf-8") as f:
    plan = json.load(f)

mix = np.zeros(N, np.float32)
for seg in plan["segments"]:
    path = os.path.join(ROOT, "out", "audio", f"narration_{seg['scene']}.wav")
    with wave.open(path, "rb") as w:
        assert w.getframerate() == SR, path
        pcm = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
    i0 = int(seg["start"] * SR)
    i1 = min(N, i0 + len(pcm))
    seg_pcm = pcm[: i1 - i0]
    fade = int(0.012 * SR)
    if len(seg_pcm) > fade * 2:
        seg_pcm[:fade] *= np.linspace(0, 1, fade)
        seg_pcm[-fade:] *= np.linspace(1, 0, fade)
    mix[i0:i1] += seg_pcm
    print(f"placed {seg['scene']} @ {seg['start']:.2f}s len={len(pcm)/SR:.2f}s")

mix *= 0.96 / max(1e-9, np.abs(mix).max())
with wave.open(os.path.join(ROOT, "out", "audio", "narration.wav"), "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mix * 32767).astype(np.int16).tobytes())
print("narration.wav done")
