# 抽象代数 · 变化之中，见永恒

全程序化生成的 **2 分 30 秒**抽象代数宣传片：视觉、配乐、旁白 100% 由代码产生，零素材、零第三方版权，任何一帧可精确复现。

> **[⬇ 下载成片 (v1.0, 145 MB)](https://github.com/EliteOtaku/abstract-algebra-promo/releases/latest)** ｜ 在线预览见 Release 页附件

## 六幕结构

| 幕 | 时间 | 数学主题 | 视觉 |
|---|---|---|---|
| S0 序章·微光 | 0:00–0:18 | — | 黑暗中一粒光苏醒，光环炸开转场 |
| S1 片名 | 0:18–0:30 | Z/nZ | 金色片名逐字点亮，同心环缓转 |
| S2 对称 | 0:30–0:54 | 二面体群 D₁₂ | 十二重雪花生长/旋转，星形弦点亮 |
| S3 结构 | 0:54–1:18 | Cayley 图 | BFS 式图绽放，脉冲光沿边流动 |
| S4 不变量 | 1:18–1:42 | 拧度 · Euler 示性数 | 三叶结拉扯但拧度 ≡ 3；多面体形变但 V−E+F=2 |
| S5 可能性 | 1:42–2:06 | 群阶 · 二十步定理 | 数字滚动至 4.3×10¹⁹，粒子凝成状态空间球 |
| S6 尾声·回流 | 2:06–2:30 | — | 星轨回流，slogan 落版 |

旁白为 Edge TTS 云健男声（纪录片腔），全文见 [设计规格](docs/superpowers/specs/2026-10-01-abstract-algebra-promo-design.md)。

## 技术管线

```
src/
├── gen_narration.py   # Edge TTS 旁白（超长自动提速，断网回退 Windows SAPI）
├── mix_narration.py   # 旁白按时间轴铺设 → narration.wav
├── gen_music.py       # 配乐合成：Pad / 低频脉冲 / 章节琶音 / Impact / 收束，72 BPM
└── video/
    ├── common.py      # 渲染引擎：辉光合成 / 文字精灵 / 矢量化粒子 / 暗角颗粒
    ├── scenes.py      # 六幕场景渲染器
    └── render.py      # 多进程逐帧渲染 → ffmpeg 管道 → H.264 + 混音
```

- **视觉**：numpy + Pillow 逐帧绘制，2× 超采样，近黑深空底 + 金青撞色 + 加性辉光 + 胶片颗粒；全片 seeded RNG。
- **音频**：48 kHz 立体声，旁白段自动 ducking −2.5 dB，loudnorm 归一至 −15 LUFS。

## 复现

```powershell
python -m venv .venv
.venv\Scripts\pip install numpy pillow imageio-ffmpeg edge-tts

.venv\Scripts\python src\gen_narration.py   # 1. 旁白（需联网）
.venv\Scripts\python src\mix_narration.py   # 2. 铺设时间轴
.venv\Scripts\python src\gen_music.py       # 3. 配乐
.venv\Scripts\python src\video\render.py --test   # 4a. 6fps 快速预览
.venv\Scripts\python src\video\render.py          # 4b. 全片 4500 帧（约 20 分钟）
```

产物在 `out/`（已 gitignore）：`video_noaudio.mp4` 为渲染直出，`abstract_algebra_promo.mp4` 需再执行响度归一：

```powershell
ffmpeg -i out\video_noaudio.mp4 -c:v libx264 -preset slow -crf 22 -pix_fmt yuv420p `
  -af "loudnorm=I=-15:TP=-1.2:LRA=11,aresample=48000" -c:a aac -b:a 192k `
  -movflags +faststart out\abstract_algebra_promo.mp4
```

## License

代码 MIT。成片视频可自由分享/二创（CC0 亦可，无任何附加条件）——它本来就是你的。
