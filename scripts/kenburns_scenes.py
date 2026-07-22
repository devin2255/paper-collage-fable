#!/usr/bin/env python3
"""Render Ken Burns MP4s for scene-01..05 from keyframes + voice durations."""
from __future__ import annotations

import argparse
import math
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
    parser.add_argument("--pad", type=float, default=1.2, help="seconds after voice")
    parser.add_argument("--width", type=int, default=1080)
    parser.add_argument("--height", type=int, default=1920)
    parser.add_argument("--fps", type=int, default=30)
    args = parser.parse_args()

    project = args.project.resolve()
    kf = project / "assets" / "keyframes"
    voice = project / "assets" / "voice-final"
    renders = project / "renders"
    renders.mkdir(parents=True, exist_ok=True)

    for i in range(1, 6):
        sid = f"{i:02d}"
        img = kf / f"scene-{sid}.png"
        wav = voice / f"{sid}.wav"
        out = renders / f"scene-{sid}.mp4"
        if not img.exists():
            raise SystemExit(f"missing {img}")
        if not wav.exists():
            raise SystemExit(f"missing {wav}")
        duration = round(probe_duration(wav) + args.pad, 3)
        frames = math.ceil(duration * args.fps)
        zf = "0.00012" if i == 5 else "0.00016"
        vf = (
            f"scale={args.width}:{args.height}:force_original_aspect_ratio=increase,"
            f"crop={args.width}:{args.height},"
            f"zoompan=z='min(zoom+{zf},1.03)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
            f":d={frames}:s={args.width}x{args.height}:fps={args.fps},format=yuv420p"
        )
        cmd = [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-loop",
            "1",
            "-i",
            str(img),
            "-vf",
            vf,
            "-t",
            str(duration),
            "-r",
            str(args.fps),
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(out),
        ]
        subprocess.check_call(cmd)
        print(f"ok {out.name} duration={probe_duration(out):.3f}")


if __name__ == "__main__":
    main()
