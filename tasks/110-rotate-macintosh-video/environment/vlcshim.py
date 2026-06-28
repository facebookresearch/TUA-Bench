#!/usr/bin/env python3
# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

SCREEN_SIZE = {"width": 1280, "height": 720}
WINDOWED_SIZE = {"width": 960, "height": 540}
STATE_DIR = Path.home() / ".local" / "state" / "tua-vlc"
SESSION_PATH = STATE_DIR / "session.json"
WALLPAPER_PATH = STATE_DIR / "wallpaper.png"
VLCRC_PATH = Path.home() / ".config" / "vlc" / "vlcrc"
KNOWN_VALUE_FLAGS = {
    "--aout",
    "--extraintf",
    "--http-host",
    "--http-password",
    "--input-slave",
    "--intf",
    "--scene-format",
    "--scene-path",
    "--scene-prefix",
    "--scene-ratio",
    "--snapshot-format",
    "--snapshot-path",
    "--snapshot-prefix",
    "--sout",
    "--transform-type",
    "--video-filter",
    "--vout",
}
HELP_TEXT = '''VLC media player terminal shim for TUA OSWorld tasks

Persistent VLC config:
  ~/.config/vlc/vlcrc

Supported task-oriented commands:
  vlc [--fullscreen] [--start-time=N] <file-or-url>
  vlc --video-wallpaper --start-time=N <video-file>
  vlc --snapshot-path PATH --snapshot-prefix NAME --snapshot-format png --start-time=N <video-file>
  cvlc <video-file> --sout '#transcode{acodec=mp3}:std{access=file,mux=raw,dst=/path/output.mp3}' vlc://quit
  cvlc <video-file> --video-filter transform --transform-type 180 --sout '#transcode{vcodec=h264}:std{access=file,mux=mp4,dst=/path/output.mp4}' vlc://quit

This shim keeps the task terminal-first while preserving VLC-facing state for the verifier.
'''


def ensure_layout() -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    VLCRC_PATH.parent.mkdir(parents=True, exist_ok=True)
    VLCRC_PATH.touch(exist_ok=True)


def default_session() -> dict:
    return {
        "state": "stopped",
        "target": None,
        "target_type": None,
        "fullscreen": False,
        "start_time": 0.0,
        "stop_time": None,
        "screen_size": SCREEN_SIZE,
        "window_size": WINDOWED_SIZE,
    }


def load_session() -> dict:
    if not SESSION_PATH.exists():
        return default_session()
    try:
        return json.loads(SESSION_PATH.read_text(encoding="utf-8"))
    except Exception:
        return default_session()


def save_session(session: dict) -> None:
    SESSION_PATH.parent.mkdir(parents=True, exist_ok=True)
    SESSION_PATH.write_text(json.dumps(session, indent=2, sort_keys=True), encoding="utf-8")


def parse_float(raw: str | None, fallback: float = 0.0) -> float:
    if raw in {None, ""}:
        return fallback
    try:
        return float(raw)
    except ValueError:
        return fallback


def is_url(value: str | None) -> bool:
    if not value:
        return False
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"}


def parse_args(args: list[str]) -> dict:
    options = {
        "fullscreen": False,
        "play_and_pause": False,
        "start_time": 0.0,
        "stop_time": None,
        "video_wallpaper": False,
        "snapshot_path": None,
        "snapshot_prefix": "vlcsnap",
        "snapshot_format": "png",
        "scene_path": None,
        "scene_prefix": None,
        "scene_format": "png",
        "scene_ratio": None,
        "sout": None,
        "transform_type": None,
        "target": None,
    }
    index = 0
    while index < len(args):
        arg = args[index]
        if arg in {"-h", "--help"}:
            options["help"] = True
        elif arg == "--version":
            options["version"] = True
        elif arg in {"-f", "--fullscreen"}:
            options["fullscreen"] = True
        elif arg == "--play-and-pause":
            options["play_and_pause"] = True
        elif arg == "--video-wallpaper":
            options["video_wallpaper"] = True
        elif arg.startswith("--start-time="):
            options["start_time"] = parse_float(arg.split("=", 1)[1], 0.0)
        elif arg == "--start-time" and index + 1 < len(args):
            index += 1
            options["start_time"] = parse_float(args[index], 0.0)
        elif arg.startswith("--stop-time="):
            options["stop_time"] = parse_float(arg.split("=", 1)[1], None)
        elif arg == "--stop-time" and index + 1 < len(args):
            index += 1
            options["stop_time"] = parse_float(args[index], None)
        elif arg.startswith("--snapshot-path="):
            options["snapshot_path"] = arg.split("=", 1)[1]
        elif arg == "--snapshot-path" and index + 1 < len(args):
            index += 1
            options["snapshot_path"] = args[index]
        elif arg.startswith("--snapshot-prefix="):
            options["snapshot_prefix"] = arg.split("=", 1)[1]
        elif arg == "--snapshot-prefix" and index + 1 < len(args):
            index += 1
            options["snapshot_prefix"] = args[index]
        elif arg.startswith("--snapshot-format="):
            options["snapshot_format"] = arg.split("=", 1)[1]
        elif arg == "--snapshot-format" and index + 1 < len(args):
            index += 1
            options["snapshot_format"] = args[index]
        elif arg.startswith("--scene-path="):
            options["scene_path"] = arg.split("=", 1)[1]
        elif arg == "--scene-path" and index + 1 < len(args):
            index += 1
            options["scene_path"] = args[index]
        elif arg.startswith("--scene-prefix="):
            options["scene_prefix"] = arg.split("=", 1)[1]
        elif arg == "--scene-prefix" and index + 1 < len(args):
            index += 1
            options["scene_prefix"] = args[index]
        elif arg.startswith("--scene-format="):
            options["scene_format"] = arg.split("=", 1)[1]
        elif arg == "--scene-format" and index + 1 < len(args):
            index += 1
            options["scene_format"] = args[index]
        elif arg.startswith("--scene-ratio="):
            options["scene_ratio"] = parse_float(arg.split("=", 1)[1], None)
        elif arg == "--scene-ratio" and index + 1 < len(args):
            index += 1
            options["scene_ratio"] = parse_float(args[index], None)
        elif arg.startswith("--sout="):
            options["sout"] = arg.split("=", 1)[1]
        elif arg == "--sout" and index + 1 < len(args):
            index += 1
            options["sout"] = args[index]
        elif arg.startswith("--transform-type="):
            options["transform_type"] = arg.split("=", 1)[1]
        elif arg == "--transform-type" and index + 1 < len(args):
            index += 1
            options["transform_type"] = args[index]
        elif arg in KNOWN_VALUE_FLAGS and index + 1 < len(args):
            index += 1
        elif arg.startswith("-"):
            pass
        elif arg != "vlc://quit" and options["target"] is None:
            options["target"] = arg
        index += 1
    return options


def to_local_path(raw: str) -> Path:
    if raw.startswith("file://"):
        raw = urlparse(raw).path
    return Path(raw).expanduser()


def ffmpeg_frame(source: Path, output: Path, time_sec: float) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    command = ["ffmpeg", "-loglevel", "error", "-y"]
    if time_sec:
        command.extend(["-ss", str(time_sec)])
    command.extend(["-i", str(source), "-frames:v", "1", str(output)])
    subprocess.run(command, check=True)


def ffmpeg_audio(source: Path, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(source),
            "-vn",
            "-acodec",
            "libmp3lame",
            "-q:a",
            "2",
            str(output),
        ],
        check=True,
    )


def transform_filter(transform_type: str | None) -> str:
    mapping = {
        None: "null",
        "90": "transpose=1",
        "180": "hflip,vflip",
        "270": "transpose=2",
        "hflip": "hflip",
        "vflip": "vflip",
    }
    return mapping.get(transform_type, mapping[None])


def ffmpeg_video(source: Path, output: Path, transform_type: str | None) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "ffmpeg",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(source),
    ]
    video_filter = transform_filter(transform_type)
    if video_filter != "null":
        command.extend(["-vf", video_filter])
    command.extend(
        [
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "18",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            str(output),
        ]
    )
    subprocess.run(command, check=True)


def parse_sout_destination(raw: str | None) -> Path | None:
    if not raw:
        return None
    match = re.search(r"dst=(?:'([^']+)'|\"([^\"]+)\"|([^,}]+))", raw)
    if not match:
        return None
    value = next(group for group in match.groups() if group)
    return to_local_path(value)


def apply_snapshot(options: dict, target: Path) -> None:
    snapshot_dir = options["scene_path"] or options["snapshot_path"]
    if not snapshot_dir:
        return
    prefix = options["scene_prefix"] or options["snapshot_prefix"] or "vlcsnap"
    fmt = options["scene_format"] or options["snapshot_format"] or "png"
    output = Path(snapshot_dir).expanduser() / f"{prefix}.{fmt}"
    ffmpeg_frame(target, output, float(options["start_time"] or 0.0))


def apply_wallpaper(options: dict, target: Path) -> None:
    if not options["video_wallpaper"]:
        return
    ffmpeg_frame(target, WALLPAPER_PATH, float(options["start_time"] or 0.0))


def apply_sout(options: dict, target: Path) -> None:
    destination = parse_sout_destination(options["sout"])
    if destination is None:
        return
    if destination.suffix.lower() == ".mp3":
        ffmpeg_audio(target, destination)
    else:
        ffmpeg_video(target, destination, options.get("transform_type"))


def main(argv: list[str]) -> int:
    ensure_layout()
    options = parse_args(argv[1:])
    if options.get("help") or len(argv) == 1:
        print(HELP_TEXT)
        return 0
    if options.get("version"):
        print("VLC media player 3.0 terminal shim for TUA")
        return 0

    target_raw = options.get("target")
    target_path: Path | None = None
    if target_raw and not is_url(target_raw):
        target_path = to_local_path(target_raw)
        if not target_path.exists():
            print(f"Target does not exist: {target_path}", file=sys.stderr)
            return 1

    try:
        if target_path is not None:
            apply_wallpaper(options, target_path)
            apply_snapshot(options, target_path)
            apply_sout(options, target_path)
    except subprocess.CalledProcessError as exc:
        print(f"ffmpeg failed with exit code {exc.returncode}", file=sys.stderr)
        return exc.returncode

    session = load_session()
    if target_raw:
        session["state"] = "playing"
        session["target"] = str(target_path) if target_path is not None else target_raw
        session["target_type"] = "url" if is_url(target_raw) else "file"
    session["fullscreen"] = bool(options["fullscreen"])
    session["start_time"] = float(options["start_time"] or 0.0)
    session["stop_time"] = options["stop_time"]
    session["screen_size"] = SCREEN_SIZE
    session["window_size"] = SCREEN_SIZE if options["fullscreen"] else WINDOWED_SIZE
    save_session(session)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
