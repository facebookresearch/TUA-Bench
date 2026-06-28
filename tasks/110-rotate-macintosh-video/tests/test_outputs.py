# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

TASK_SPEC = {'expected': {'dest': '1984_Apple_Macintosh_Commercial_gold.mp4',
              'type': 'cloud_file',
              'url': 'https://huggingface.co/datasets/xlangai/ubuntu_osworld_file_cache/resolve/main/vlc/aa4b5023-aef6-4ed9-bdc9-705f59ab9ad6/1984_Apple_Macintosh_Commercial.mp4'},
 'inputs': [{'path': '/home/agent/Desktop/flipped_1984_Apple_Macintosh_Commercial.mp4',
             'url': 'https://huggingface.co/datasets/xlangai/ubuntu_osworld_file_cache/resolve/main/vlc/aa4b5023-aef6-4ed9-bdc9-705f59ab9ad6/flipped_1984_Apple_Macintosh_Commercial.mp4'}],
 'metric_func': 'compare_videos',
 'metric_options': {},
 'result': {'dest': '1984_Apple_Macintosh_Commercial.mp4',
            'path': '/home/agent/1984_Apple_Macintosh_Commercial.mp4',
            'type': 'vm_file'},
 'slug': '110-rotate-macintosh-video'}

import json
import logging
import os
import subprocess
from pathlib import Path
from typing import Dict
from urllib.parse import urlparse
from xml.etree import ElementTree

import cv2
import imagehash
import librosa
import numpy as np
from PIL import Image
from fastdtw import fastdtw
from scipy.spatial.distance import cosine
from skimage.metrics import structural_similarity as ssim

logger = logging.getLogger("tua.vlc.osworld")
logging.basicConfig(level=logging.INFO)

LIMITATION_PHRASES = [
    "does not",
    "doesn't",
    "cannot",
    "can't",
    "not possible",
    "infeasible",
    "missing",
    "without",
    "unsupported",
    "unavailable",
    "not available",
    "not offered",
]
CACHE_DIR = Path("/tmp") / TASK_SPEC["slug"]
DEFAULT_SCREEN_SIZE = {"width": 1280, "height": 720}
DEFAULT_WINDOW_SIZE = {"width": 960, "height": 540}


def get_app_dir() -> Path:
    return Path(os.environ.get("APP_DIR", "/app"))


def get_agent_home() -> Path:
    return Path(os.environ.get("AGENT_HOME", "/home/agent"))


def get_state_dir() -> Path:
    return Path(
        os.environ.get(
            "TUA_VLC_STATE_DIR",
            str(get_agent_home() / ".local" / "state" / "tua-vlc"),
        )
    )


def localize_path(path: str) -> Path:
    if path.startswith("/app/"):
        return get_app_dir() / path.removeprefix("/app/")
    if path.startswith("/home/user/"):
        return get_agent_home() / path.removeprefix("/home/user/")
    if path.startswith("/home/agent/"):
        return get_agent_home() / path.removeprefix("/home/agent/")
    if path.startswith("file://"):
        return Path(urlparse(path).path)
    return Path(path).expanduser()


def fetch_cloud_file(url: str, dest: str) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    target = CACHE_DIR / dest
    if not target.exists():
        subprocess.run(
            ["curl", "-fL", "--retry", "3", "--retry-delay", "1", url, "-o", str(target)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    return target


def load_session() -> dict:
    path = get_state_dir() / "session.json"
    if not path.exists():
        return {
            "state": "stopped",
            "target": None,
            "target_type": None,
            "fullscreen": False,
            "screen_size": DEFAULT_SCREEN_SIZE,
            "window_size": DEFAULT_WINDOW_SIZE,
        }
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {
            "state": "stopped",
            "target": None,
            "target_type": None,
            "fullscreen": False,
            "screen_size": DEFAULT_SCREEN_SIZE,
            "window_size": DEFAULT_WINDOW_SIZE,
        }


def build_status_xml(dest_name: str) -> Path:
    session = load_session()
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    output = CACHE_DIR / dest_name

    root = ElementTree.Element("root")
    state_element = ElementTree.SubElement(root, "state")
    state_element.text = session.get("state", "stopped")
    information = ElementTree.SubElement(root, "information")
    category = ElementTree.SubElement(information, "category", {"name": "meta"})

    target = session.get("target")
    if target:
        basename = os.path.basename(target)
        info_pairs = [
            ("filename", basename),
            ("title", basename),
            ("name", basename),
        ]
        if session.get("target_type") == "url":
            info_pairs.extend(
                [
                    ("url", target),
                    ("URI", target),
                    ("location", target),
                ]
            )
        else:
            info_pairs.extend(
                [
                    ("uri", f"file://{target}"),
                    ("location", target),
                ]
            )

        for name, value in info_pairs:
            node = ElementTree.SubElement(category, "info", {"name": name})
            node.text = value

    output.write_bytes(ElementTree.tostring(root, encoding="utf-8"))
    return output


def get_vlc_playing_info(config: Dict[str, str]):
    return str(build_status_xml(config["dest"]))


def get_vlc_config(config: Dict[str, str]):
    return str(get_agent_home() / ".config" / "vlc" / config["dest"])


def get_vm_screen_size(config: dict):
    session = load_session()
    return session.get("screen_size", DEFAULT_SCREEN_SIZE)


def get_vm_window_size(config: dict):
    session = load_session()
    if session.get("fullscreen"):
        return session.get("screen_size", DEFAULT_SCREEN_SIZE)
    return session.get("window_size", DEFAULT_WINDOW_SIZE)


def get_vm_wallpaper(config: dict):
    wallpaper = get_state_dir() / "wallpaper.png"
    if not wallpaper.exists() or wallpaper.stat().st_size == 0:
        return None
    return str(wallpaper)


def is_vlc_playing(actual_status_path: str, rule: Dict[str, str]) -> float:
    with open(actual_status_path, "rb") as file:
        actual_status = file.read().decode("utf-8")

    tree = ElementTree.fromstring(actual_status)
    status = tree.find("state").text
    logger.info("VLC Status: %s", status)
    if status == "playing":
        if rule["type"] == "file_name":
            file_paths = [
                'information/category[@name="meta"]/info[@name="filename"]',
                'information/category[@name="meta"]/info[@name="title"]',
                'information/category[@name="meta"]/info[@name="uri"]',
                'information/category[@name="meta"]/info[@name="location"]',
                'information/category[@name="meta"]/info[@name="name"]',
            ]

            file_info = None
            for path in file_paths:
                element = tree.find(path)
                if element is not None and element.text:
                    file_info = element.text
                    break

            if file_info:
                expected_filename = rule["file_name"]
                actual_basename = os.path.basename(file_info)
                if actual_basename == expected_filename:
                    return 1
                if file_info.endswith(expected_filename):
                    return 1
                if expected_filename in file_info:
                    if file_info.endswith("/" + expected_filename) or file_info.endswith(
                        "\\" + expected_filename
                    ):
                        return 1
                logger.warning(
                    "File name mismatch - Expected: %s, Found: %s",
                    expected_filename,
                    file_info,
                )
                return 0
            logger.warning(
                "Could not find file information in VLC status XML for rule: %s",
                rule,
            )
            return 0
        if rule["type"] == "url":
            url_paths = [
                'information/category[@name="meta"]/info[@name="url"]',
                'information/category[@name="meta"]/info[@name="URI"]',
                'information/category[@name="meta"]/info[@name="location"]',
                'information/category[@name="meta"]/info[@name="title"]',
                'information/category[@name="meta"]/info[@name="filename"]',
                'information/category[@name="Stream 0"]/info[@name="Codec"]',
                'information/category[@name="Stream 0"]/info[@name="Type"]',
                'information/category[@name="Stream 0"]/info[@name="Language"]',
            ]

            file_info = None
            logger.debug("Looking for URL: %s", rule["url"])

            for path in url_paths:
                element = tree.find(path)
                if element is not None and element.text:
                    file_info = element.text
                    logger.debug("Found URL info at %s: %s", path, file_info)
                    break

            if file_info:
                expected_url = rule["url"]
                if expected_url in file_info or file_info.endswith(expected_url):
                    return 1
                try:
                    expected_parsed = urlparse(expected_url)
                    expected_filename = os.path.basename(expected_parsed.path)
                    if file_info == expected_filename:
                        logger.info(
                            "URL filename match - Expected URL: %s, VLC shows filename: %s",
                            expected_url,
                            file_info,
                        )
                        return 1
                    if "://" in file_info:
                        actual_parsed = urlparse(file_info)
                        if (
                            expected_parsed.netloc == actual_parsed.netloc
                            and expected_parsed.path in actual_parsed.path
                        ):
                            return 1
                except Exception as exc:
                    logger.debug("URL parsing error: %s", exc)

                logger.warning("URL mismatch - Expected: %s, Found: %s", expected_url, file_info)
                return 0
            logger.warning("Could not find URL information in VLC status XML for rule: %s", rule)
            return 0
        logger.error("Unknown type: %s", rule["type"])
        return 0
    return 0


def is_vlc_recordings_folder(actual_config_path: str, rule: Dict[str, str]) -> float:
    with open(actual_config_path, "rb") as file:
        config_file = file.read().decode("utf-8")

    expected_recording_file_path = rule["recording_file_path"]

    try:
        for line in config_file.split("\\n"):
            if line.startswith("#") or not line.strip():
                continue
            if "input-record-path" in line:
                current_path = line.split("=")[-1].strip()
                if current_path == expected_recording_file_path:
                    return 1
                return 0
        return 0
    except FileNotFoundError:
        logger.error("VLC configuration file not found.")
        return 0
    except Exception as exc:
        logger.error("An error occurred: %s", exc)
        return 0


def is_vlc_fullscreen(actual_window_size, screen_size):
    if screen_size is None or actual_window_size is None:
        return 0
    if (
        actual_window_size["width"] == screen_size["width"]
        and actual_window_size["height"] == screen_size["height"]
    ):
        return 1
    return 0


def compare_images(image1_path, image2_path, **options):
    if not image1_path or not image2_path:
        return 0

    base_score = options.get("reference_base_result", None)

    image1 = Image.open(image1_path).convert("L")
    image2 = Image.open(image2_path).convert("L")

    image1_size = image1.size
    image2_size = image2.size
    new_size = min(image1_size, image2_size)

    image1 = image1.resize(new_size, Image.Resampling.LANCZOS)
    image2 = image2.resize(new_size, Image.Resampling.LANCZOS)

    image1_array = np.array(image1)
    image2_array = np.array(image2)

    similarity_index = ssim(image1_array, image2_array)

    epsilon = 0.01
    if base_score is not None:
        if similarity_index >= base_score + epsilon:
            return (similarity_index - base_score) / (1 - base_score)
        return 0
    return similarity_index


def compare_audios(audio_path_1, audio_path_2):
    if not audio_path_1 or not audio_path_2:
        return 0

    y1, y2 = None, None
    try:
        y1, sr1 = librosa.load(audio_path_1)
    except Exception:
        logger.warning(
            "Could not load audio from %s. It might be empty or corrupt.",
            os.path.basename(audio_path_1),
        )

    try:
        y2, sr2 = librosa.load(audio_path_2)
    except Exception:
        logger.warning(
            "Could not load audio from %s. It might be empty or corrupt.",
            os.path.basename(audio_path_2),
        )

    is_y1_bad = (y1 is None) or (y1.shape[0] == 0)
    is_y2_bad = (y2 is None) or (y2.shape[0] == 0)

    if is_y1_bad and is_y2_bad:
        logger.info("Both audio files are empty or corrupt. Considering them perfectly similar.")
        return 1.0

    if is_y1_bad or is_y2_bad:
        logger.warning("One audio file is empty/corrupt, the other is not. Similarity is 0.")
        return 0.0

    try:
        logger.info("Audio 1 (%s): sr=%s, len=%s", os.path.basename(audio_path_1), sr1, len(y1))
        logger.info("Audio 2 (%s): sr=%s, len=%s", os.path.basename(audio_path_2), sr2, len(y2))
        mfcc1 = librosa.feature.mfcc(y=y1, sr=sr1)
        mfcc2 = librosa.feature.mfcc(y=y2, sr=sr2)
    except Exception as exc:
        logger.error("Error during MFCC extraction: %s", exc)
        return 0.0

    mfcc1 = librosa.util.normalize(mfcc1, axis=1)
    mfcc2 = librosa.util.normalize(mfcc2, axis=1)
    logger.info("MFCCs normalized.")

    dist_func = lambda x, y: cosine(x, y)
    distance, path = fastdtw(mfcc1.T, mfcc2.T, dist=dist_func)
    logger.info("DTW distance: %.4f, Path length: %s", distance, len(path))

    if len(path) == 0:
        normalized_distance = np.inf
    else:
        normalized_distance = distance / len(path)
    logger.info("Normalized DTW distance: %.4f", normalized_distance)

    similarity = np.exp(-normalized_distance)
    return similarity


def compare_videos(video_path1, video_path2, max_frames_to_check=100, threshold=5):
    if not video_path1 or not video_path2:
        return 0

    cap1 = cv2.VideoCapture(video_path1)
    cap2 = cv2.VideoCapture(video_path2)

    frames_checked = 0
    mismatch_count = 0

    while frames_checked < max_frames_to_check:
        ret1, frame1 = cap1.read()
        ret2, frame2 = cap2.read()

        if not ret1 or not ret2:
            return 1.0 if ret1 == ret2 else 0.0

        frame1 = Image.fromarray(cv2.cvtColor(frame1, cv2.COLOR_BGR2RGB))
        frame2 = Image.fromarray(cv2.cvtColor(frame2, cv2.COLOR_BGR2RGB))

        hash1 = imagehash.phash(frame1)
        hash2 = imagehash.phash(frame2)

        frames_checked += 1
        if hash1 - hash2 > threshold:
            mismatch_count += 1
            if mismatch_count > threshold:
                return 0.0

    return 1.0


def check_qt_bgcone(actual_config_path, rule):
    with open(actual_config_path, "rb") as file:
        config_file = file.read().decode("utf-8")

    expected_qt_bgcone = rule["expected_qt_bgcone"]
    if isinstance(expected_qt_bgcone, int):
        expected_qt_bgcone = str(expected_qt_bgcone)

    try:
        qt_bgcone = "1"
        for line in config_file.split("\\n"):
            if "qt-bgcone=" in line:
                qt_bgcone = line.split("=")[-1].strip()

        if qt_bgcone == expected_qt_bgcone:
            return 1
        return 0
    except FileNotFoundError:
        logger.error("VLC configuration file not found.")
        return 0
    except Exception as exc:
        logger.error("An error occurred: %s", exc)
        return 0


def check_qt_max_volume(actual_config_path, rule):
    with open(actual_config_path, "rb") as file:
        config_file = file.read().decode("utf-8")

    expected_qt_max_volume = rule["expected_qt_max_volume"]
    if isinstance(expected_qt_max_volume, int):
        expected_qt_max_volume = str(expected_qt_max_volume)

    try:
        qt_max_volume = "125"
        for line in config_file.split("\\n"):
            if "qt-max-volume=" in line:
                qt_max_volume = line.split("=")[-1].strip()

        if qt_max_volume == expected_qt_max_volume:
            return 1
        return 0
    except FileNotFoundError:
        logger.error("VLC configuration file not found.")
        return 0
    except Exception as exc:
        logger.error("An error occurred: %s", exc)
        return 0


def check_qt_minimal_view(actual_config_path, rule):
    with open(actual_config_path, "rb") as file:
        config_file = file.read().decode("utf-8")

    expected_qt_minimal_view = rule["expected_qt_minimal_view"]
    if isinstance(expected_qt_minimal_view, int):
        expected_qt_minimal_view = str(expected_qt_minimal_view)

    try:
        qt_minimal_view = "0"
        for line in config_file.split("\\n"):
            if "qt-minimal-view=" in line:
                qt_minimal_view = line.split("=")[-1].strip()

        if qt_minimal_view == expected_qt_minimal_view:
            return 1
        return 0
    except FileNotFoundError:
        logger.error("VLC configuration file not found.")
        return 0
    except Exception as exc:
        logger.error("An error occurred: %s", exc)
        return 0


def check_qt_slider_colours(actual_config_path, rule):
    with open(actual_config_path, "rb") as file:
        config_file = file.read().decode("utf-8")

    try:
        qt_slider_colours = "153;210;153;20;210;20;255;199;15;245;39;29"
        for line in config_file.split("\\n"):
            if "qt-slider-colours" in line:
                qt_slider_colours = line.split("=")[-1].strip()

        if rule["type"] == "match":
            expected_qt_slider_colours = rule["expected_qt_slider_colours"]
            if qt_slider_colours == expected_qt_slider_colours:
                return 1
            return 0
        if rule["type"] == "blackish":
            def is_color_blackish(rgb_values, threshold=100):
                return all(value < threshold for value in rgb_values)

            def parse_qt_slider_colours(colours_string):
                values = [int(x) for x in colours_string.split(";")]
                colors = list(zip(values[0::3], values[1::3], values[2::3]))
                return colors

            colors = parse_qt_slider_colours(qt_slider_colours)

            for color in colors:
                if not is_color_blackish(color):
                    return 0
            return 1
    except FileNotFoundError:
        logger.error("VLC configuration file not found.")
        return 0
    except Exception as exc:
        logger.error("An error occurred: %s", exc)
        return 0
    return 0


def check_global_key_play_pause(actual_config_path, rule):
    with open(actual_config_path, "rb") as file:
        config_file = file.read().decode("utf-8")

    expected_global_key_play_pause = rule["expected_global_key_play_pause"]
    if isinstance(expected_global_key_play_pause, int):
        expected_global_key_play_pause = str(expected_global_key_play_pause)

    try:
        global_key_play_pause = "0"
        for line in config_file.split("\\n"):
            if "global-key-play-pause=" in line:
                global_key_play_pause = "0" if line.split("=")[-1].strip() == "" else "1"

        if global_key_play_pause == expected_global_key_play_pause:
            return 1
        return 0
    except FileNotFoundError:
        logger.error("VLC configuration file not found.")
        return 0
    except Exception as exc:
        logger.error("An error occurred: %s", exc)
        return 0


def check_one_instance_when_started_from_file(actual_config_path, rule):
    with open(actual_config_path, "rb") as file:
        config_file = file.read().decode("utf-8")

    expected_one_instance_when_started_from_file = rule["expected_one_instance_when_started_from_file"]
    if isinstance(expected_one_instance_when_started_from_file, int):
        expected_one_instance_when_started_from_file = str(
            expected_one_instance_when_started_from_file
        )

    try:
        one_instance_when_started_from_file = "1"
        for line in config_file.split("\\n"):
            if "one-instance-when-started-from-file=" in line:
                one_instance_when_started_from_file = line.split("=")[-1].strip()

        if one_instance_when_started_from_file == expected_one_instance_when_started_from_file:
            return 1
        return 0
    except FileNotFoundError:
        logger.error("VLC configuration file not found.")
        return 0
    except Exception as exc:
        logger.error("An error occurred: %s", exc)
        return 0


def check_play_and_exit(actual_config_path, rule):
    with open(actual_config_path, "rb") as file:
        config_file = file.read().decode("utf-8")

    expected_play_and_exit = rule["expected_play_and_exit"]
    if isinstance(expected_play_and_exit, int):
        expected_play_and_exit = str(expected_play_and_exit)

    try:
        play_and_exit = "0"
        for line in config_file.split("\\n"):
            if "play-and-exit=" in line:
                play_and_exit = line.split("=")[-1].strip()
        return 1 if play_and_exit == expected_play_and_exit else 0
    except FileNotFoundError:
        logger.error("VLC configuration file not found.")
        return 0
    except Exception as exc:
        logger.error("An error occurred: %s", exc)
        return 0


def check_infeasible_response(path: str, required_terms):
    if not path:
        return 0.0
    file_path = Path(path)
    if not file_path.exists():
        return 0.0

    text = file_path.read_text(encoding="utf-8").strip()
    if not text:
        return 0.0

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines or lines[0].lower() != "infeasible":
        return 0.0

    reason = " ".join(lines[1:]).lower()
    if not reason:
        return 0.0

    if not all(term in reason for term in required_terms):
        return 0.0

    if not any(phrase in reason for phrase in LIMITATION_PHRASES):
        return 0.0

    return 1.0


def resolve_state(spec):
    if spec is None:
        return None
    state_type = spec["type"]
    if state_type == "rule":
        return spec["rules"]
    if state_type == "cloud_file":
        return str(fetch_cloud_file(spec["url"], spec["dest"]))
    if state_type == "vm_file":
        path = localize_path(spec["path"])
        return str(path) if path.exists() and path.stat().st_size > 0 else None
    if state_type == "vlc_config":
        return get_vlc_config(spec)
    if state_type == "vlc_playing_info":
        return get_vlc_playing_info(spec)
    if state_type == "vm_screen_size":
        return get_vm_screen_size(spec)
    if state_type == "vm_window_size":
        return get_vm_window_size(spec)
    if state_type == "vm_wallpaper":
        return get_vm_wallpaper(spec)
    raise ValueError(f"Unsupported state type: {state_type}")


def evaluate() -> float:
    metric_func = TASK_SPEC["metric_func"]
    result_state = resolve_state(TASK_SPEC.get("result"))
    expected_state = resolve_state(TASK_SPEC.get("expected"))
    options = TASK_SPEC.get("metric_options", {})

    try:
        if metric_func == "check_infeasible_response":
            return float(check_infeasible_response(result_state, options["required_terms"]))
        metric = globals()[metric_func]
        if expected_state is None:
            return float(metric(result_state, **options))
        return float(metric(result_state, expected_state, **options))
    except Exception as exc:
        logger.error("Evaluation failed: %s", exc)
        return 0.0


if __name__ == "__main__":
    print(evaluate())
