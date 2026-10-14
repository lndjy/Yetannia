# voice-extract.py — pull the AudioClips out of 《千年之旅》's voice bundles.
#
# The .dat files the user supplied are not raw audio: each one starts with the UnityFS magic and is a
# Unity 2019.4.40f1 AssetBundle holding a single AudioClip. UnityPy decodes the clip (FMOD sample
# bank inside the bundle) and hands back playable WAV bytes.
#
# usage: python .tools/voice-extract.py <srcDir> <outDir> [nameFilter]
import os
import sys

import UnityPy

src = sys.argv[1]
out = sys.argv[2]
needle = sys.argv[3] if len(sys.argv) > 3 else ""

os.makedirs(out, exist_ok=True)

done = 0
failed = []
for name in sorted(os.listdir(src)):
    if not name.lower().endswith(".dat"):
        continue
    if needle and needle.lower() not in name.lower():
        continue
    path = os.path.join(src, name)
    stem = os.path.splitext(name)[0]
    try:
        env = UnityPy.load(path)
        got = 0
        for obj in env.objects:
            if obj.type.name != "AudioClip":
                continue
            clip = obj.read()
            samples = clip.samples
            if not isinstance(samples, dict) or not samples:
                failed.append((name, "no samples"))
                continue
            for key, data in samples.items():
                # UnityPy returns WAV for formats it can decode, and the raw payload otherwise.
                ext = ".wav" if data[:4] == b"RIFF" else ".bin"
                target = os.path.join(out, f"{stem}{'' if got == 0 else '_' + str(got)}{ext}")
                with open(target, "wb") as fh:
                    fh.write(data)
                print(f"  {name}  ->  {os.path.basename(target)}  {len(data)} B  "
                      f"clipName={getattr(clip, 'm_Name', '?')}  freq={getattr(clip, 'm_Frequency', '?')}")
                got += 1
        if got == 0 and not any(f[0] == name for f in failed):
            failed.append((name, "no AudioClip in bundle"))
        done += 1
    except Exception as exc:  # noqa: BLE001 - report, do not abort the batch
        failed.append((name, f"{type(exc).__name__}: {exc}"))

print(f"\nbundles processed: {done}")
if failed:
    print(f"problems: {len(failed)}")
    for name, why in failed:
        print(f"  {name}: {why}")
