# -*- coding: utf-8 -*-
"""渲染主驱动：多进程逐帧渲染 → mjpeg 管道 → ffmpeg H.264 + 旁白/音乐混装。
用法:
  python render.py --test            # 6fps 抽样快速预览
  python render.py                   # 全片 30fps
  python render.py --frames 300-420  # 指定帧区间(调试)
"""
import argparse, math, multiprocessing as mp, os, subprocess, sys, time

import imageio_ffmpeg
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import W, H, FPS, TOTAL, CUTS, finish, dust_layer, scene_of
import scenes

FF = imageio_ffmpeg.get_ffmpeg_exe()
ROOT = r"D:\AI\AA-by-GLM"
FRAME_OFF = 0.05          # 场景起点白闪时长(半)
FRAME_W = 0.68            # 白闪总宽

def compose_frame(fi):
    t = fi / FPS
    name, tl, dur = scene_of(t)
    base = dust_layer()
    acc = np.asarray(base, dtype=np.float32).copy()
    acc += np.array([5, 8, 16], np.float32)          # 深空底色
    scenes.SCENE_FN[name](acc, tl, t, fi)
    # 剪切点白闪
    fl = 0.0
    for c in CUTS:
        dt = t - c
        if -FRAME_W / 2 <= dt <= FRAME_W / 2:
            fl = max(fl, math.cos(dt / FRAME_W * math.pi) ** 2)
    if fl > 0:
        acc += fl * 210
    # 末尾淡黑
    if t > TOTAL - 0.8:
        k = (t - (TOTAL - 0.8)) / 0.8
        acc *= (1 - k)
    img = finish(acc, fi)
    return fi, img.tobytes()


def _worker(args):
    return compose_frame(args)


def raw_size(fps):
    return W, H


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", action="store_true", help="6fps 抽样预览")
    ap.add_argument("--frames", type=str, default=None, help="如 300-420")
    ap.add_argument("--out", type=str, default=None)
    ap.add_argument("--procs", type=int, default=max(1, (os.cpu_count() or 8) - 1))
    args = ap.parse_args()

    fps = 6 if args.test else FPS
    total_frames = int(TOTAL * fps)
    lo, hi = 0, total_frames
    if args.frames:
        a, b = args.frames.split("-")
        lo, hi = int(a), int(b)

    out = args.out or os.path.join(ROOT, "out", "preview_test.mp4" if args.test else "video_noaudio.mp4")
    narr = os.path.join(ROOT, "out", "audio", "narration.wav")
    music = os.path.join(ROOT, "out", "audio", "music.wav")

    cmd = [FF, "-y", "-f", "image2pipe", "-vcodec", "mjpeg", "-r", str(fps), "-i", "-"]
    if not args.test and os.path.exists(narr) and os.path.exists(music):
        cmd += ["-i", narr, "-i", music,
                "-filter_complex",
                f"[1:a]apad,atrim=0:{TOTAL},pan=stereo|c0=c0|c1=c0[n];"
                f"[2:a]atrim=0:{TOTAL}[m];"
                f"[n][m]amix=inputs=2:duration=first:dropout_transition=0,alimiter=limit=0.95[a]"]
    cmd += ["-map", "0:v"]
    if not args.test and "-i" in cmd[1:]:
        cmd += ["-map", "[a]", "-c:a", "aac", "-b:a", "192k"]
    cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", "18",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-r", str(fps), out]

    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE,
                            stderr=subprocess.PIPE, stdout=subprocess.DEVNULL)
    t0 = time.time()
    done = 0
    if args.frames:
        for fi in range(lo, hi):
            _, jpg = compose_frame(fi)
            buf = Image.frombytes("RGB", (W, H), jpg)
            buf.save(proc.stdin, "JPEG", quality=92)
            done += 1
    else:
        with mp.Pool(args.procs) as pool:
            for fi, jpg in pool.imap(_worker, range(lo, hi), chunksize=8):
                buf = Image.frombytes("RGB", (W, H), jpg)
                buf.save(proc.stdin, "JPEG", quality=92)
                done += 1
                if done % 60 == 0:
                    el = time.time() - t0
                    eta = el / done * (hi - lo - done)
                    print(f"frame {done}/{hi-lo}  {el:.0f}s elapsed, ETA {eta/60:.1f}min", flush=True)
    proc.stdin.close()
    err = proc.stderr.read().decode(errors="ignore")
    proc.wait()
    if proc.returncode != 0:
        print(err[-1600:])
        sys.exit(1)
    print(f"DONE {out}  frames={done}  {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
