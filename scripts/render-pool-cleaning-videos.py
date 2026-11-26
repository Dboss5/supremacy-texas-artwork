#!/usr/bin/env python3
"""Render Supremacy pool-cleaning promos from approved repository photographs only."""
import argparse
import json
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "video-exports" / "pool-cleaning"
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
PHOTOS = [
    "pool-care/2026-11-25/backyard-pool-with-a-shallow-lounging-ledge.jpg",
    "pool-leak-detection/2026-11-25/curved-vinyl-pool-with-entry-steps.jpg",
    "pool-leak-detection/2026-11-25/pool-tile-waterline-and-coping.jpg",
]
SCENES = [
    ("POOL CLEANING", "Refresh your pool"),
    ("SKIM | BRUSH | VACUUM", "Keep surfaces looking their best"),
    ("SUPREMACY SERVICE", "Pool cleaning & maintenance | North Texas"),
]
FORMATS = {"vertical": (720, 1280), "landscape": (1280, 720), "square": (900, 900)}

def run(args):
    subprocess.run(args, check=True)

def render(format_name, width, height, fps=24):
    OUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as temp:
        temp = Path(temp)
        segments = []
        for index, (relpath, (title, subtitle)) in enumerate(zip(PHOTOS, SCENES)):
            path = ROOT / relpath
            if not path.is_file():
                raise FileNotFoundError(f"Required Supremacy GitHub image missing: {relpath}")
            titlefile = temp / f"title{index}.txt"
            subfile = temp / f"sub{index}.txt"
            titlefile.write_text(title, encoding="utf-8")
            subfile.write_text(subtitle, encoding="utf-8")
            segment = temp / f"scene{index}.mp4"
            title_size = int(width * (0.043 if format_name == "landscape" else 0.067))
            sub_size = int(width * (0.023 if format_name == "landscape" else 0.040))
            # Each frame comes only from a named photograph in the repository.
            # The gentle crop motion and brand-colored graphics are programmatic overlays.
            vf = ",".join([
                f"scale={width+100}:{height+100}:force_original_aspect_ratio=increase",
                f"crop={width}:{height}:x='50+25*sin(t/2)':y='50+18*cos(t/2)'",
                "eq=brightness=-0.07:saturation=1.08",
                f"drawbox=x=0:y={int(height*.67)}:w=iw:h={int(height*.33)}:color=0x183249@0.88:t=fill",
                f"drawbox=x={int(width*.067)}:y={int(height*.70)}:w={int(width*.17)}:h=5:color=0xE24A2A:t=fill",
                f"drawtext=fontfile={FONT}:textfile={titlefile}:fontsize={title_size}:fontcolor=white:x={int(width*.067)}:y={int(height*.735)}",
                f"drawtext=fontfile={FONT}:textfile={subfile}:fontsize={sub_size}:fontcolor=white:x={int(width*.067)}:y={int(height*.82)}",
                "fade=t=in:st=0:d=0.35",
                "fade=t=out:st=4.45:d=0.55",
                "format=yuv420p"
            ])
            run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                 "-loop", "1", "-framerate", str(fps), "-i", str(path),
                 "-t", "5", "-vf", vf, "-an", "-c:v", "libx264",
                 "-preset", "veryfast", "-crf", "21", "-r", str(fps),
                 "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(segment)])
            segments.append(segment)
        playlist = temp / "concat.txt"
        playlist.write_text("".join(f"file '{s}'\n" for s in segments), encoding="utf-8")
        destination = OUT / f"supremacy-pool-cleaning-{format_name}.mp4"
        run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "concat",
             "-safe", "0", "-i", str(playlist), "-c", "copy", "-movflags",
             "+faststart", str(destination)])
        print(destination)
        return destination

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--format", choices=[*FORMATS, "all"], default="all")
    args = parser.parse_args()
    selected = FORMATS if args.format == "all" else {args.format: FORMATS[args.format]}
    produced = [render(name, *dims) for name, dims in selected.items()]
    (OUT / "manifest.json").write_text(json.dumps({
        "title": "Supremacy pool cleaning & maintenance promotional videos",
        "image_sources": PHOTOS,
        "videos": [str(p.relative_to(ROOT)) for p in produced],
        "note": "Photos show pools and waterline detail; procedure captions are service descriptions, not claims that a cleaning procedure is depicted.",
        "audio": "none",
        "tool": "ffmpeg",
    }, indent=2) + "\n")

if __name__ == "__main__":
    main()
