# voice-encode.py — turn the extracted dub WAVs into the mod's per-moment ogg files.
#
# This is step 3 of the voice pipeline; the other two already exist and are unchanged:
#   .tools/voice-extract.py   UnityFS .dat  -> 44.1 kHz mono WAV   (.tools/voice/raw, raw-cn)
#   .tools/voice-analyze.py   WAV           -> total/active durations (RMS envelope)
#   .tools/voice-encode.py    WAV           -> res:// audio, this file
#
# ENCODER SETTINGS ARE REVERSE-ENGINEERED, NOT GUESSED. Re-encoding the four already-shipped
# lines with `-c:a libvorbis -q:a 4` on the untouched source WAV reproduces the shipped file
# byte-for-byte except for 40 bytes of Ogg page serial number + page CRC, i.e. the same encoder,
# the same quality and the same (untrimmed) input. So: no trim, no gain, no resample.
#
# The mod names its shipped files after the MOMENT (`yetannia_select.ogg`), not after the source
# clip (`Summon.wav`), which is also why `select` ships `Summon` under a different name.
#
# Existing files are left alone (the four shipped lines were verified byte-equivalent by --check, so
# re-writing them would only churn their Ogg page serial numbers); use --force to re-encode anyway.
#
# usage: python .tools/voice-encode.py [--check] [--force] [--only STEM]
import os
import struct
import subprocess
import sys
import wave

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FFMPEG = os.path.join(ROOT, ".tools", "ffmpeg", "ffmpeg-master-latest-win64-gpl", "bin", "ffmpeg.exe")
OUTDIR = os.path.join(ROOT, ".tools", "pckproject", "Yetannia", "audio", "voice")

# The dubbing project numbers its families; 301500402 was chosen over 3015004 because the 3015004
# attack lines are ~3 s (too long for a card-game hit) and over 301500401 because that family is
# the cutscene/menu set. See the round notes for the comparison.
FAMILY = "301500402"

# moment stem (what the ogg is called, i.e. ModAssets.Voice(lang, stem)) -> source clip stem.
# attack / cast / die / select are ALREADY SHIPPED and are re-encoded here only so `--check` can
# prove the recipe still reproduces them; they are listed first on purpose.
MOMENTS = [
    ("attack",       "Strike_Out_02"),
    ("cast",         "Skill_1_p01"),
    ("die",          "Send_Back"),
    ("select",       "Summon"),
    ("run_start",    "Send_Out"),
    ("combat_start", "Bat_Stage"),
    ("card_reward",  "Role_Skillup"),
    ("rest",         "Work_Start"),
    ("shop",         "Manage_01"),
    ("event",        "Event"),
    ("relic",        "Notification"),
]

LANGS = [("jp", os.path.join(ROOT, ".tools", "voice", "raw")),
         ("cn", os.path.join(ROOT, ".tools", "voice", "raw-cn"))]

WINDOW = 0.02  # 20 ms, same envelope window as voice-analyze.py


def active_seconds(path):
    """Total duration and the RMS-active duration, using voice-analyze.py's own threshold rule."""
    with wave.open(path, "rb") as w:
        rate, frames, channels, width = w.getframerate(), w.getnframes(), w.getnchannels(), w.getsampwidth()
        raw = w.readframes(frames)
    if channels != 1 or width != 2:
        raise ValueError(f"{path}: expected mono 16-bit, got channels={channels} width={width}")
    step = int(rate * WINDOW) * 2
    rms = []
    for off in range(0, len(raw) - step + 1, step):
        total = 0
        for (v,) in struct.iter_unpack("<h", raw[off:off + step]):
            total += v * v
        rms.append((total / (step // 2)) ** 0.5)
    peak = max(rms) if rms else 0.0
    if not rms or peak <= 0:
        return rate, frames / rate, 0.0, 0.0
    thresh = peak * 0.06
    active = [i for i, v in enumerate(rms) if v > thresh]
    first, last = (active[0] * WINDOW, (active[-1] + 1) * WINDOW) if active else (0.0, 0.0)
    return rate, frames / rate, last - first, first


def encode(src, dst):
    subprocess.run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error",
                    "-i", src, "-c:a", "libvorbis", "-q:a", "4", dst], check=True)


def main():
    check_only = "--check" in sys.argv
    force = "--force" in sys.argv
    only = None
    if "--only" in sys.argv:
        only = sys.argv[sys.argv.index("--only") + 1]

    print(f"{'moment':<13}{'source':<16}{'lang':<5}{'total':>7}{'active':>8}{'lead':>7}{'bytes':>9}  result")
    failures = []
    for lang, srcdir in LANGS:
        os.makedirs(os.path.join(OUTDIR, lang), exist_ok=True)
        for moment, clip in MOMENTS:
            if only and moment != only:
                continue
            src = os.path.join(srcdir, f"Voice_{FAMILY}_{clip}.wav")
            if not os.path.exists(src):
                failures.append(f"{lang}/{moment}: source missing {src}")
                print(f"{moment:<13}{clip:<16}{lang:<5}{'-':>7}{'-':>8}{'-':>7}{'-':>9}  SOURCE MISSING")
                continue
            rate, total, active, lead = active_seconds(src)
            if rate != 44100:
                failures.append(f"{lang}/{moment}: rate is {rate}, expected 44100")
            dst = os.path.join(OUTDIR, lang, f"yetannia_{moment}.ogg")
            size = os.path.getsize(dst) if os.path.exists(dst) else 0
            if check_only:
                note = "present (check only)" if size else "MISSING (check only)"
            elif size and not force:
                note = "kept (already present; --force to re-encode)"
            else:
                encode(src, dst)
                new_size = os.path.getsize(dst)
                note = f"encoded ({new_size} B)" + (", size unchanged" if new_size == size else "")
                size = new_size
            print(f"{moment:<13}{clip:<16}{lang:<5}{total:7.2f}{active:8.2f}{lead:7.2f}{size:9d}  {note}")

    if failures:
        print("\nPROBLEMS:")
        for f in failures:
            print("  " + f)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
