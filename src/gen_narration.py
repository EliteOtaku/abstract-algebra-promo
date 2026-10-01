# -*- coding: utf-8 -*-
"""生成旁白音频：Edge TTS（云健），失败回退 Windows SAPI。
输出 out/audio/narration_S*.wav（48kHz 单声道 PCM16）+ narration_plan.json
"""
import asyncio, json, math, os, subprocess, sys, wave

import imageio_ffmpeg
import numpy as np

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
ROOT = r"D:\AI\AA-by-GLM"
OUT = os.path.join(ROOT, "out", "audio")
os.makedirs(OUT, exist_ok=True)

VOICE = "zh-CN-YunjianNeural"
RATE_FALLBACKS = ["+0%", "+8%", "+16%", "+24%"]

# (scene, 旁白起始时间=场景起点+lead, 文本)
SEGMENTS = [
    ("S0", 1.0, "每一个结构，都藏着一种美。看不见，却处处都在。这部片子，献给数学里最抽象、也最自由的分支——抽象代数。"),
    ("S2", 1.5, "你见过雪花吗？十二重旋转——把整个图形转过来，它和原来一模一样。数学家说：对称不是一种形状，而是一个动作。而这些动作放在一起，就构成了一个「群」。"),
    ("S3", 1.5, "群，是所有变化的语法。转动魔方、洗一副牌、解一次方程——动作千变万化，骨子里是同一套结构。把每个动作画成一个点，把每一步运算画成一条线，混乱就蒸馏成了秩序。"),
    ("S4", 1.5, "代数学家最迷恋的，是变化中不变的东西。一个结，无论怎么拉扯，它的拧度不变；一个多面体，无论怎么变形，顶点减棱加面，永远等于二。这叫不变量——刻在宇宙里的常数。"),
    ("S5", 1.5, "一个三阶魔方，有四千三百亿亿种状态，人力无法枚举。但群论可以证明：从任何状态出发，最多二十步，就能回到原点。"),
    ("S6", 2.0, "抽象，不是逃离世界，而是更高地俯瞰世界。当你看清了变化，也就看见了永恒。抽象代数——变化之中，见永恒。"),
]
SCENE_START = {"S0": 0.0, "S2": 30.0, "S3": 54.0, "S4": 78.0, "S5": 102.0, "S6": 126.0}
SCENE_END   = {"S0": 18.0, "S2": 54.0, "S3": 78.0, "S4": 102.0, "S5": 126.0, "S6": 149.2}


def trim_tail(pcm, sr, keep=0.28, thresh_db=-45):
    """裁掉尾部静音，保留 keep 秒余韵"""
    win = int(sr * 0.05)
    n = len(pcm) // win
    env = np.abs(pcm[: n * win].reshape(n, win)).max(1)
    db = 20 * np.log10(env + 1e-6)
    loud = np.where(db > thresh_db)[0]
    if len(loud) == 0:
        return pcm
    end = min(len(pcm), (loud[-1] + 1) * win + int(sr * keep))
    return pcm[:end]


def measure_and_normalize(mp3_path, wav_path):
    """mp3 → 48k mono wav，返回时长"""
    cmd = [FFMPEG, "-y", "-i", mp3_path, "-ar", "48000", "-ac", "1",
           "-sample_fmt", "s16", wav_path]
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.decode(errors="ignore")[-400:])
    with wave.open(wav_path, "rb") as w:
        sr, nfr = w.getframerate(), w.getnframes()
    return nfr / sr


async def edge_gen(text, rate, path):
    import edge_tts
    c = edge_tts.Communicate(text, VOICE, rate=rate, volume="+0%")
    await c.save(path)


def sapi_gen(text, path):
    """Windows SAPI 中文回退（Kangkang/Huihui）"""
    ps = f'''
Add-Type -AssemblyName System.Speech
$s = New-Object System.Speech.Synthesis.SpeechSynthesizer
$s.SetOutputToWaveFile("{path.replace(chr(92), '/')}")
$names = $s.GetInstalledVoices() | ForEach-Object {{ $_.VoiceInfo.Name }}
$zh = $names | Where-Object {{ $_ -match "Kangkang|Huihui|Yaoyao" }} | Select-Object -First 1
if ($zh) {{ $s.SelectVoice($zh) }}
$s.Rate = 0
$s.Speak("{text.replace('"', '')}")
$s.Dispose()
'''
    r = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True)
    if r.returncode != 0 or not os.path.exists(path):
        raise RuntimeError(r.stderr.decode(errors="ignore")[-300:])


async def main():
    plan, used_fallback = [], False
    for scene, lead, text in SEGMENTS:
        deadline = SCENE_END[scene] - (SCENE_START[scene] + lead) - 0.6
        ok = False
        for rate in RATE_FALLBACKS:
            mp3 = os.path.join(OUT, f"_tmp_{scene}.mp3")
            try:
                await edge_gen(text, rate, mp3)
                src = mp3
            except Exception as e:
                print(f"[edge-tts fail {scene} rate={rate}] {type(e).__name__}: {e}", flush=True)
                continue
            dur = measure_and_normalize(src, os.path.join(OUT, f"_raw_{scene}.wav"))
            if dur <= deadline or rate == RATE_FALLBACKS[-1]:
                ok = True
                break
        if not ok:
            used_fallback = True
            wav_tmp = os.path.join(OUT, f"_sapi_{scene}.wav")
            sapi_gen(text, wav_tmp)
            dur = measure_and_normalize(wav_tmp, os.path.join(OUT, f"_raw_{scene}.wav"))
        raw = os.path.join(OUT, f"_raw_{scene}.wav")
        with wave.open(raw, "rb") as w:
            sr = w.getframerate()
            pcm = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
        pcm = trim_tail(pcm, sr)
        final = os.path.join(OUT, f"narration_{scene}.wav")
        with wave.open(final, "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
            w.writeframes((np.clip(pcm, -1, 1) * 32767).astype(np.int16).tobytes())
        dur = len(pcm) / sr
        start = SCENE_START[scene] + lead
        overflow = max(0.0, dur - deadline)
        plan.append(dict(scene=scene, start=round(start, 2), dur=round(dur, 2),
                         end=round(start + dur, 2), deadline=round(deadline, 2),
                         overflow=round(overflow, 2)))
        print(f"{scene}: start={start:6.2f}s  dur={dur:6.2f}s  (slot {deadline:5.2f}s)  {'OVERFLOW!' if overflow > 0 else 'ok'}", flush=True)
        for f in (os.path.join(OUT, f"_tmp_{scene}.mp3"), raw, os.path.join(OUT, f"_sapi_{scene}.wav")):
            if os.path.exists(f):
                os.remove(f)
    with open(os.path.join(OUT, "narration_plan.json"), "w", encoding="utf-8") as f:
        json.dump(dict(voice="edge-tts:" + VOICE if not used_fallback else "sapi-fallback",
                       segments=plan), f, ensure_ascii=False, indent=1)
    print("fallback:", used_fallback)

if __name__ == "__main__":
    asyncio.run(main())
