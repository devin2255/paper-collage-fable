#!/usr/bin/env python3
"""Write production-manifest.json from rendered scenes + voice files."""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


def probe_duration(path: Path) -> float:
    out = subprocess.check_output(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=nk=1:nw=1",
            str(path),
        ],
        text=True,
    ).strip()
    return float(out)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", type=Path, default=Path("."))
    args = parser.parse_args()
    project = args.project.resolve()
    renders = project / "renders"
    voice = project / "assets" / "voice-final"

    sfx_defaults = [
        [{"file": "../assets/audio/whoosh-short.mp3", "at": 0.15, "volume": 0.14}],
        [{"file": "../assets/audio/click-soft.mp3", "at": 2.0, "volume": 0.12}],
        [{"file": "../assets/audio/whoosh-short.mp3", "at": 1.5, "volume": 0.16}],
        [{"file": "../assets/audio/whoosh-short.mp3", "at": 1.2, "volume": 0.16}],
        [{"file": "../assets/audio/chime.mp3", "at": 0.0, "volume": 0.16}],
    ]

    scenes = []
    for i in range(1, 6):
        sid = f"{i:02d}"
        mp4 = renders / f"scene-{sid}.mp4"
        wav = voice / f"{sid}.wav"
        if not mp4.exists() or not wav.exists():
            raise SystemExit(f"missing {mp4} or {wav}")
        d = probe_duration(mp4)
        sfx = sfx_defaults[i - 1]
        if i == 5:
            sfx[0]["at"] = max(0.2, d - 1.0)
        scenes.append(
            {
                "video": f"../renders/scene-{sid}.mp4",
                "sourceDuration": d,
                "duration": d,
                "voice": f"../assets/voice-final/{sid}.wav",
                "voiceStart": 0.35,
                "sfx": sfx,
            }
        )

    man = {
        "width": 1080,
        "height": 1920,
        "fps": 30,
        "crf": 18,
        "voiceGain": 1.15,
        "music": "../assets/audio/underscore.mp3",
        "musicVolume": 0.06,
        "ducking": {
            "enabled": True,
            "threshold": 0.02,
            "ratio": 6,
            "attackMs": 20,
            "releaseMs": 280,
        },
        "targetLufs": -16,
        "truePeak": -1.5,
        "scenes": scenes,
    }
    out = project / "manifests" / "production-manifest.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(man, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {out} total={sum(s['duration'] for s in scenes):.3f}s")


if __name__ == "__main__":
    main()
