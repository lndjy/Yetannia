# voice-analyze.py — where does the speech actually start and end?
#
# The extracted lines are longer than a card-game SFX should be, and the first question is how much of
# that is trailing silence rather than speech. Measuring the RMS envelope answers it without listening,
# and trimming to the active region is lossless with respect to the recording.
#
# usage: python .tools/voice-analyze.py <dir> [nameFilter]
import os
import struct
import sys
import wave

d = sys.argv[1]
needle = sys.argv[2] if len(sys.argv) > 2 else ""

WINDOW = 0.02  # 20 ms


def envelope(path):
    with wave.open(path, "rb") as w:
        rate = w.getframerate()
        n = w.getnframes()
        raw = w.readframes(n)
    step = int(rate * WINDOW) * 2  # 16-bit mono
    rms = []
    for off in range(0, len(raw) - step + 1, step):
        chunk = raw[off:off + step]
        total = 0
        for (v,) in struct.iter_unpack("<h", chunk):
            total += v * v
        rms.append((total / (step // 2)) ** 0.5)
    return rate, n, rms


peak_overall = 0.0
rows = []
for name in sorted(os.listdir(d)):
    if not name.lower().endswith(".wav") or needle.lower() not in name.lower():
        continue
    rate, n, rms = envelope(os.path.join(d, name))
    peak = max(rms) if rms else 0
    peak_overall = max(peak_overall, peak)
    rows.append((name, rate, n, rms, peak))

for name, rate, n, rms, peak in rows:
    # Threshold relative to this clip's own peak so a quiet take is not read as silence.
    thresh = max(peak * 0.06, peak_overall * 0.02)
    active = [i for i, v in enumerate(rms) if v > thresh]
    total = n / rate
    if active:
        first, last = active[0] * WINDOW, (active[-1] + 1) * WINDOW
    else:
        first = last = 0.0
    print(f"{name.replace('Voice_', '').replace('.wav', ''):<44} "
          f"total={total:5.2f}s  active={last - first:5.2f}s  "
          f"lead={first:4.2f}s  tail={total - last:5.2f}s  "
          f"peakRMS={peak / peak_overall * 100:5.1f}%")
