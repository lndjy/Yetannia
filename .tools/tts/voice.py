#!/usr/bin/env python3
"""Yetannia channel voice pipeline.

Text -> processed voiceover (mp3/wav), optional shot-based package with SRT + props.json.
Backend: edge-tts (free neural voices) + ffmpeg post chain (EQ / gentle compression / loudness).

Examples:
    python .tools/voice/voice.py --text "大家好，这里是耶坦尼娅频道。" --out voice.mp3
    python .tools/voice/voice.py --text "..." --preset podcast --srt --out voice.mp3
    python .tools/voice/voice.py --script script.json --outdir build/voice

Presets live in .tools/voice/presets.json; the default is the channel voice.
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
PRESETS_PATH = os.path.join(HERE, "presets.json")
CACHE_DIR = os.path.join(HERE, "cache")


def die(msg, code=1):
    print("ERROR: " + msg, file=sys.stderr)
    raise SystemExit(code)


def find_tool(env_name, candidates):
    if os.environ.get(env_name):
        return os.environ[env_name]
    for c in candidates:
        hit = shutil.which(c)
        if hit:
            return hit
    for c in candidates:
        for base in (
            os.path.join(os.environ.get("USERPROFILE", ""), ".local", "bin"),
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Python", "Python313", "Scripts"),
        ):
            p = os.path.join(base, c)
            if os.path.exists(p):
                return p
    # Repo-local ffmpeg (bundled under .tools/ffmpeg/).
    ff_root = os.path.join(REPO, ".tools", "ffmpeg")
    for c in candidates:
        if c.lower().replace(".exe", "") in ("ffmpeg", "ffprobe"):
            for root, _dirs, files in os.walk(ff_root):
                for f in files:
                    if f.lower() == c.lower().replace(".exe", "") + ".exe" or f.lower() == c.lower():
                        return os.path.join(root, f)
    die("找不到 {0}，请先安装（pip install edge-tts / ffmpeg）".format(env_name))


EDGE_TTS = None
FFMPEG = None
FFPROBE = None


def tools():
    global EDGE_TTS, FFMPEG, FFPROBE
    if EDGE_TTS is None:
        EDGE_TTS = find_tool("EDGE_TTS", ["edge-tts", "edge-tts.exe"])
        FFMPEG = find_tool("FFMPEG", ["ffmpeg", "ffmpeg.exe"])
        FFPROBE = find_tool("FFPROBE", ["ffprobe", "ffprobe.exe"])
    return EDGE_TTS, FFMPEG, FFPROBE


def load_config():
    with open(PRESETS_PATH, encoding="utf-8") as f:
        return json.load(f)


def resolve_preset(args):
    cfg = load_config()
    name = args.preset or cfg.get("default", "channel")
    presets = cfg.get("presets", {})
    if name not in presets:
        die("未知 preset: {0}（可用: {1}）".format(name, ", ".join(presets)))
    p = dict(presets[name])
    p["name"] = name
    if args.voice:
        p["voice"] = args.voice
    if args.rate:
        p["rate"] = args.rate
    if args.pitch:
        p["pitch"] = args.pitch
    if args.chain:
        p["chain"] = args.chain
    if args.lufs:
        p["lufs"] = str(args.lufs)
    return p


def run(cmd, echo=False):
    if echo:
        print("  $ " + subprocess.list2cmdline(cmd))
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise RuntimeError(
            "命令失败 ({0}): {1}\n{2}".format(r.returncode, subprocess.list2cmdline(cmd), (r.stderr or "")[-800:])
        )
    return r.stdout


def synth(text, preset, out_mp3, retries=3):
    """edge-tts one text chunk -> mp3."""
    edge = tools()[0]
    cmd = [edge, "--voice", preset["voice"], "--text", text, "--write-media", out_mp3]
    # Use the --opt=value form: edges like "-2%" would otherwise be parsed as an option.
    if preset.get("rate"):
        cmd.insert(3, "--rate=" + str(preset["rate"]))
    if preset.get("pitch"):
        cmd.insert(3, "--pitch=" + str(preset["pitch"]))
    last = None
    for i in range(retries):
        try:
            run(cmd)
            if os.path.exists(out_mp3) and os.path.getsize(out_mp3) > 0:
                return
        except Exception as e:  # network hiccup
            last = e
            time.sleep(1.5 * (i + 1))
    die("edge-tts 合成失败: {0}".format(last))


def post_chain(in_mp3, out_wav, chain):
    ff = tools()[1]
    af = chain or "anull"
    run([ff, "-y", "-hide_banner", "-loglevel", "error", "-i", in_mp3,
         "-af", af, "-ar", "48000", "-ac", "1", out_wav])


def loudness(in_wav, out_wav, lufs):
    ff = tools()[1]
    run([ff, "-y", "-hide_banner", "-loglevel", "error", "-i", in_wav,
         "-af", "loudnorm=I={0}:TP=-1.5:LRA=11".format(lufs),
         "-ar", "48000", "-ac", "1", out_wav])


def to_mp3(in_wav, out_mp3, bitrate="192k"):
    ff = tools()[1]
    run([ff, "-y", "-hide_banner", "-loglevel", "error", "-i", in_wav,
         "-codec:a", "libmp3lame", "-b:a", bitrate, "-ar", "48000", "-ac", "1", out_mp3])


def duration(path):
    ffprobe = tools()[2]
    out = run([ffprobe, "-v", "error", "-show_entries", "format=duration",
               "-of", "default=noprint_wrappers=1:nokey=1", path])
    return float(out.strip())


def silence_wav(path, seconds):
    ff = tools()[1]
    run([ff, "-y", "-hide_banner", "-loglevel", "error",
         "-f", "lavfi", "-i", "anullsrc=r=48000:cl=mono", "-t", str(seconds),
         "-c:a", "pcm_s16le", path])


def concat_wavs(parts, out_wav):
    ff = tools()[1]
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as f:
        for p in parts:
            f.write("file '" + p.replace("'", "'\\''") + "'\n")
        listfile = f.name
    try:
        run([ff, "-y", "-hide_banner", "-loglevel", "error",
             "-f", "concat", "-safe", "0", "-i", listfile,
             "-c:a", "pcm_s16le", "-ar", "48000", "-ac", "1", out_wav])
    finally:
        os.unlink(listfile)


def split_sentences(text):
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    parts = re.split(r"(?<=[。！？!?；;:\n])", text)
    out, buf = [], ""
    for p in parts:
        p = p.strip()
        if not p:
            continue
        buf += p
        if len(buf) >= 8:
            out.append(buf)
            buf = ""
    if buf:
        out.append(buf)
    return out


class ChunkCache:
    def __init__(self, preset):
        os.makedirs(CACHE_DIR, exist_ok=True)
        self.preset = preset

    def key(self, text):
        raw = json.dumps([self.preset["voice"], self.preset["rate"], self.preset["pitch"],
                          self.preset.get("chain", ""), text], ensure_ascii=False)
        return hashlib.sha1(raw.encode("utf-8")).hexdigest()

    def get(self, text):
        path = os.path.join(CACHE_DIR, self.key(text) + ".wav")
        if os.path.exists(path):
            return path
        tmp_mp3 = path + ".mp3"
        synth(text, self.preset, tmp_mp3)
        post_chain(tmp_mp3, path, self.preset.get("chain", ""))
        try:
            os.unlink(tmp_mp3)
        except OSError:
            pass
        return path


def render_text(args):
    preset = resolve_preset(args)
    text = args.text or (sys.stdin.read() if args.stdin else "")
    text = (text or "").strip()
    if not text:
        die("没有输入文本：用 --text 或 --stdin")
    cache = ChunkCache(preset)

    if not args.srt:
        # Single pass; edge-tts handles long text internally.
        work = tempfile.mkdtemp(prefix="voice-")
        try:
            mp3 = os.path.join(work, "raw.mp3")
            wav = os.path.join(work, "raw.wav")
            norm = os.path.join(work, "norm.wav")
            if len(text) <= 600:
                synth(text, preset, mp3)
                post_chain(mp3, wav, preset.get("chain", ""))
            else:
                # Command-line length guard: synthesize per sentence and concat.
                parts = [cache.get(s) for s in split_sentences(text)]
                concat_wavs(parts, wav)
            loudness(wav, norm, preset["lufs"])
            out = args.out or "voice.mp3"
            os.makedirs(os.path.dirname(os.path.abspath(out)) or ".", exist_ok=True)
            to_mp3(norm, out)
        finally:
            shutil.rmtree(work, ignore_errors=True)
        print("OK  {0}  preset={1}  voice={2}  {3:.2f}s".format(
            out, preset["name"], preset["voice"], duration(out)))
        return

    # Sentence mode: accurate SRT.
    chunks = []
    for s in split_sentences(text):
        chunks.append((s, cache.get(s)))
    work = tempfile.mkdtemp(prefix="voice-")
    try:
        parts, cues = [], []
        t = 0.0
        for s, wav in chunks:
            d = duration(wav)
            parts.append(wav)
            cues.append((t, t + d, s))
            t += d
        voice_wav = os.path.join(work, "voice.wav")
        concat_wavs(parts, voice_wav)
        norm = os.path.join(work, "norm.wav")
        loudness(voice_wav, norm, preset["lufs"])
        out = args.out or "voice.mp3"
        os.makedirs(os.path.dirname(os.path.abspath(out)) or ".", exist_ok=True)
        to_mp3(norm, out)
        srt_path = os.path.splitext(out)[0] + ".srt"
        write_srt(cues, srt_path)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    print("OK  {0} + {1}  preset={2}  voice={3}  {4:.2f}s".format(
        out, srt_path, preset["name"], preset["voice"], duration(out)))


def fmt_ts(sec):
    ms = int(round(sec * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return "{0:02d}:{1:02d}:{2:02d},{3:03d}".format(h, m, s, ms)


def write_srt(cues, path):
    lines = []
    for i, (a, b, text) in enumerate(cues, 1):
        lines.append(str(i))
        lines.append("{0} --> {1}".format(fmt_ts(a), fmt_ts(b)))
        lines.append(text)
        lines.append("")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines))


def render_script(args):
    preset = resolve_preset(args)
    try:
        with open(args.script, encoding="utf-8-sig") as f:
            data = json.load(f)
    except Exception as e:
        die("读不了脚本 JSON: {0}".format(e))
    if isinstance(data, list):
        shots = [{"narration": str(x)} for x in data]
        fps = 30
    else:
        shots = data.get("shots") or []
        fps = int(data.get("fps") or 30)
    if not shots:
        die("脚本里没有 shots")
    shots = [s for s in shots if (s.get("narration") or "").strip()]
    if not shots:
        die("脚本里没有非空旁白")
    outdir = os.path.abspath(args.outdir or "build/voice")
    audio_dir = os.path.join(outdir, "audio")
    os.makedirs(audio_dir, exist_ok=True)
    gap = float(args.gap if args.gap is not None else 0.35)
    cache = ChunkCache(preset)

    all_parts, props_shots, cues = [], [], []
    t = 0.0
    index = 0
    for shot in shots:
        narration = (shot.get("narration") or "").strip()
        if not narration:
            continue
        index += 1
        index_tag = "{0:02d}".format(index)
        work = tempfile.mkdtemp(prefix="voice-shot-")
        try:
            chunks = [(s, cache.get(s)) for s in split_sentences(narration)]
            parts = []
            for s, wav in chunks:
                parts.append(wav)
            shot_raw = os.path.join(work, "shot.wav")
            concat_wavs(parts, shot_raw)
            shot_norm = os.path.join(work, "shot-norm.wav")
            loudness(shot_raw, shot_norm, preset["lufs"])
            shot_mp3 = os.path.join(audio_dir, "shot-{0}.mp3".format(index_tag))
            to_mp3(shot_norm, shot_mp3)
            d = duration(shot_mp3)
        finally:
            shutil.rmtree(work, ignore_errors=True)

        start_frame = int(round(t * fps))
        props_shots.append({
            "index": index,
            "tag": index_tag,
            "text": narration,
            "file": "audio/shot-{0}.mp3".format(index_tag),
            "startFrame": start_frame,
            "durationFrames": int(round(d * fps)),
            "durationSeconds": round(d, 3),
        })
        # sentence-level cues for the srt (recompute from chunk durations in this shot)
        ct = t
        for s, wav in [(s, cache.get(s)) for s in split_sentences(narration)]:
            cd = duration(wav)
            cues.append((ct, ct + cd, s))
            ct += cd
        all_parts.append(shot_mp3)
        t += d
        if gap > 0 and index < len(shots):
            all_parts.append(None)  # marker for silence between shots
            t += gap

    # Concat everything (with silence gaps) into one voice track.
    work = tempfile.mkdtemp(prefix="voice-final-")
    try:
        wav_parts = []
        for i, p in enumerate(all_parts):
            if p is None:
                sil = os.path.join(work, "sil-{0}.wav".format(i))
                silence_wav(sil, gap)
                wav_parts.append(sil)
            else:
                wav_parts.append(p)
        voice_wav = os.path.join(work, "voice.wav")
        concat_wavs(wav_parts, voice_wav)
        norm = os.path.join(work, "voice-norm.wav")
        loudness(voice_wav, norm, preset["lufs"])
        voice_mp3 = os.path.join(outdir, "voice.mp3")
        to_mp3(norm, voice_mp3)
    finally:
        shutil.rmtree(work, ignore_errors=True)

    write_srt(cues, os.path.join(outdir, "subtitles.srt"))
    props = {
        "fps": fps,
        "preset": preset["name"],
        "voice": preset["voice"],
        "rate": preset["rate"],
        "pitch": preset["pitch"],
        "totalFrames": int(round(t * fps)),
        "totalSeconds": round(t, 3),
        "shots": props_shots,
    }
    with open(os.path.join(outdir, "props.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(props, f, ensure_ascii=False, indent=1)
    print("OK  {0}  shots={1}  total={2:.2f}s  preset={3}  voice={4}".format(
        outdir, len(props_shots), t, preset["name"], preset["voice"]))


def main():
    ap = argparse.ArgumentParser(description="Yetannia channel voice (edge-tts + ffmpeg)")
    ap.add_argument("--text", help="要合成的文本")
    ap.add_argument("--stdin", action="store_true", help="从 stdin 读文本")
    ap.add_argument("--out", help="输出 mp3（默认 voice.mp3）")
    ap.add_argument("--srt", action="store_true", help="同时输出逐句 SRT")
    ap.add_argument("--script", help="分镜脚本 JSON：{fps, shots:[{narration}]}")
    ap.add_argument("--outdir", help="脚本模式的输出目录")
    ap.add_argument("--gap", type=float, help="分镜间静音秒数（默认 0.35）")
    ap.add_argument("--preset", help="presets.json 里的 preset 名（默认 channel）")
    ap.add_argument("--voice", help="覆盖 edge-tts voice")
    ap.add_argument("--rate", help="覆盖语速，如 -2%")
    ap.add_argument("--pitch", help="覆盖音高，如 -6Hz")
    ap.add_argument("--chain", help="覆盖 ffmpeg 处理链")
    ap.add_argument("--lufs", help="覆盖响度目标，默认 -16")
    ap.add_argument("--list-presets", action="store_true", help="列出预设")
    args = ap.parse_args()

    if args.list_presets:
        cfg = load_config()
        for name, p in cfg.get("presets", {}).items():
            mark = " (default)" if name == cfg.get("default") else ""
            print("{0:10s} {1}{2}".format(name, p.get("label", ""), mark))
            print("           voice={0} rate={1} pitch={2}".format(p["voice"], p["rate"], p["pitch"]))
        return

    tools()
    if args.script:
        render_script(args)
    else:
        render_text(args)


if __name__ == "__main__":
    main()
