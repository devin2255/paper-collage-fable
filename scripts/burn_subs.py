#!/usr/bin/env python3
"""Build ASS from storyboard/script lines + production-manifest timings, burn into final."""
from __future__ import annotations

import argparse
import json
import re
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


def ts(sec: float) -> str:
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = sec % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def load_lines(project: Path) -> list[list[str]]:
    script = (project / "script.md").read_text(encoding="utf-8")
    # Prefer numbered section under 分场旁白
    block = re.search(r"## 分场旁白\s*(.+?)(?:\n## |\Z)", script, re.S)
    text = block.group(1) if block else script
    lines: list[str] = []
    for m in re.finditer(r"^\s*\d+\.\s*(.+)$", text, re.M):
        lines.append(m.group(1).strip())
    if len(lines) < 5:
        raise SystemExit("need 5 numbered narration lines in script.md ## 分场旁白")
    # Split long lines for vertical readability
    split: list[list[str]] = []
    for line in lines[:5]:
        if len(line) > 18 and ("。" in line or "；" in line or "，" in line):
            parts = re.split(r"(?<=[。；，])", line)
            parts = [p for p in parts if p.strip()]
            if len(parts) >= 2:
                split.append(parts)
                continue
        split.append([line])
    return split


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", type=Path, default=Path("."))
    parser.add_argument(
        "--input",
        type=Path,
        default=None,
        help="nosub mp4 (default renders/final-nosub.mp4)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="final mp4 (default renders/final.mp4)",
    )
    args = parser.parse_args()
    project = args.project.resolve()
    man_path = project / "manifests" / "production-manifest.json"
    man = json.loads(man_path.read_text(encoding="utf-8"))
    texts = load_lines(project)

    events: list[tuple[float, float, str]] = []
    t0 = 0.0
    for i, sc in enumerate(man["scenes"]):
        wav = project / "assets" / "voice-final" / f"{i+1:02d}.wav"
        vd = probe_duration(wav)
        abs_voice = t0 + float(sc.get("voiceStart", 0.35))
        parts = texts[i]
        n = len(parts)
        chunk = vd / n
        for j, line in enumerate(parts):
            start = abs_voice + j * chunk
            end = min(abs_voice + (j + 1) * chunk, t0 + float(sc["duration"]) - 0.05)
            events.append((start, end, line))
        t0 += float(sc["duration"])

    ass = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Microsoft YaHei,52,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,4,1,2,80,80,260,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    for start, end, line in events:
        ass += f"Dialogue: 0,{ts(start)},{ts(end)},Default,,0,0,0,,{line}\n"

    ass_path = project / "assets" / "audio" / "subtitles.ass"
    ass_path.parent.mkdir(parents=True, exist_ok=True)
    ass_path.write_text(ass, encoding="utf-8-sig")

    nosub = args.input or (project / "renders" / "final-nosub.mp4")
    final = args.output or (project / "renders" / "final.mp4")
    if not nosub.exists():
        raise SystemExit(f"missing {nosub}")

    # Run from project root so relative ass= path works on Windows
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(nosub),
        "-vf",
        "ass=assets/audio/subtitles.ass",
        "-c:a",
        "copy",
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
        str(final),
    ]
    subprocess.check_call(cmd, cwd=str(project))
    print(f"wrote {final} duration={probe_duration(final):.3f} events={len(events)}")


if __name__ == "__main__":
    main()
