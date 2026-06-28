#!/usr/bin/env python3
# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.


from __future__ import annotations

import argparse
import binascii
import ssl
import struct
import sys
import tarfile
import tempfile
import xml.etree.ElementTree as ET
import zlib
from html.parser import HTMLParser
from http.cookiejar import CookieJar
from pathlib import Path
from shutil import copyfile, copyfileobj
from urllib import parse, request


ROOT = Path(__file__).resolve().parents[1]
ARXIV_ROOT = ROOT / "tasks"

DRAWIO_SOURCE_URL = (
    "https://raw.githubusercontent.com/jgraph/drawio-diagrams/dev/blog/"
    "waypoint-shape.drawio"
)
DRAWIO_PAGE_ID = "wcKaEIRRbTOs9xtrrMNS"
DRAWIO_EXPORT_URL = "https://convert.diagrams.net/node/export"

DRAWIO_SOURCE_TARGET = (
    ARXIV_ROOT / "009-repair-org-chart-layout/environment/input/org_chart.drawio"
)
DRAWIO_PNG_TARGETS = [
    ARXIV_ROOT / "009-repair-org-chart-layout/solution/corporate_org_chart.png",
    ARXIV_ROOT
    / "009-repair-org-chart-layout/tests/reference/"
    "corporate_org_chart_reference.png",
]

MRI_ARCHIVE_FILE_ID = "1Ff7c21UksxyT4JfETjaarmuKEjdqe1-a"
MRI_ARCHIVE_CACHE = Path(tempfile.gettempdir()) / "Task05_Prostate.tar"
MRI_DATA_FILES = {
    "Task05_Prostate/imagesTr/prostate_00.nii.gz": [
        ARXIV_ROOT
        / "007-reconstruct-prostate-obj/environment/input/case_7f3a9c_mri.nii.gz",
        ARXIV_ROOT / "007-reconstruct-prostate-obj/input/case_7f3a9c_mri.nii.gz",
        ARXIV_ROOT
        / "019-prostate-red-overlay/environment/input/case_7f3a9c_mri.nii.gz",
        ARXIV_ROOT / "019-prostate-red-overlay/input/case_7f3a9c_mri.nii.gz",
        ARXIV_ROOT
        / "033-prostate-volume-est/environment/input/case_7f3a9c_mri.nii.gz",
        ARXIV_ROOT / "033-prostate-volume-est/input/case_7f3a9c_mri.nii.gz",
        ARXIV_ROOT
        / "050-mri-png-slices/environment/input/case_7f3a9c_mri.nii.gz",
        ARXIV_ROOT / "050-mri-png-slices/input/case_7f3a9c_mri.nii.gz",
    ],
    "Task05_Prostate/labelsTr/prostate_00.nii.gz": [
        ARXIV_ROOT
        / "007-reconstruct-prostate-obj/solution/reference/"
        "prostate_00_label_backup.nii.gz",
        ARXIV_ROOT
        / "007-reconstruct-prostate-obj/tests/reference/"
        "prostate_00_label_backup.nii.gz",
        ARXIV_ROOT
        / "019-prostate-red-overlay/solution/reference/"
        "prostate_00_label_backup.nii.gz",
        ARXIV_ROOT
        / "019-prostate-red-overlay/tests/reference/"
        "prostate_00_label_backup.nii.gz",
        ARXIV_ROOT
        / "054-prostate-label-obj/environment/input/case_7f3a9c_label.nii.gz",
        ARXIV_ROOT / "054-prostate-label-obj/input/case_7f3a9c_label.nii.gz",
    ],
}
MRI_PNG_SLICE_INPUT = (
    ARXIV_ROOT / "050-mri-png-slices/environment/input/case_7f3a9c_mri.nii.gz"
)
MRI_PNG_SLICE_FILENAMES = [
    f"prostate_00_t2_slice_{index:02d}.png" for index in range(15)
]
MRI_PNG_SLICE_DIRS = [
    ARXIV_ROOT
    / "050-mri-png-slices/solution/reference/prostate_00_png_slices",
    ARXIV_ROOT / "050-mri-png-slices/tests/reference/prostate_00_png_slices",
]
MRI_PNG_SLICE_TARGETS = [
    target_dir / filename
    for target_dir in MRI_PNG_SLICE_DIRS
    for filename in MRI_PNG_SLICE_FILENAMES
]

VIDEO_SHARD_URL = (
    "https://huggingface.co/datasets/facebook/PE-Video/resolve/main/"
    "test/000000.tar?download=true"
)
VIDEO_SHARD_CACHE = Path(tempfile.gettempdir()) / "PE-Video-test-000000.tar"
VIDEO_DATA_FILES = {
    "18585469.mp4": ARXIV_ROOT
    / "008-find-bird-chase-frames/environment/input/18585469.mp4",
    "85229750.mp4": ARXIV_ROOT
    / "002-count-enter-key-presses/environment/input/85229750.mp4",
}

FLOOR_PLAN_PNG_BASE_URL = (
    "https://huggingface.co/buckets/bebeberr/floor-plans/resolve"
)
FLOOR_PLAN_PNG_CACHE_DIR = (
    Path(tempfile.gettempdir()) / "real-estate-openstudio-comstock-pngs"
)
FLOOR_PLAN_TASK_ROOT = ARXIV_ROOT / "003-rebuild-energy-model"
FLOOR_PLAN_PNG_FILES = {
    "floorplan.png": [
        FLOOR_PLAN_TASK_ROOT / "environment/input/floorplan.png",
        FLOOR_PLAN_TASK_ROOT / "input/floorplan.png",
        FLOOR_PLAN_TASK_ROOT
        / "solution/reference/wa_building_100094_renders/floorplan.png",
    ],
    "3d_view_1.png": [
        FLOOR_PLAN_TASK_ROOT
        / "solution/reference/wa_building_100094_renders/3d_view_1.png",
    ],
    "3d_view_2.png": [
        FLOOR_PLAN_TASK_ROOT
        / "solution/reference/wa_building_100094_renders/3d_view_2.png",
    ],
    "3d_view_3.png": [
        FLOOR_PLAN_TASK_ROOT
        / "solution/reference/wa_building_100094_renders/3d_view_3.png",
    ],
}

COMSTOCK_TIMESERIES_PARQUET_URL = (
    "https://oedi-data-lake.s3.amazonaws.com/nrel-pds-building-stock/"
    "end-use-load-profiles-for-us-building-stock/2025/"
    "comstock_amy2018_release_3/timeseries_individual_buildings/"
    "by_state/upgrade=0/state=WA/100094-0.parquet"
)
COMSTOCK_TIMESERIES_PARQUET_CACHE = (
    Path(tempfile.gettempdir()) / "comstock-100094-0.parquet"
)
COMSTOCK_TIMESERIES_PARQUET_TARGETS = [
    ARXIV_ROOT / "024-wa-osm-to-idf/environment/input/building_timeseries.parquet",
    ARXIV_ROOT / "024-wa-osm-to-idf/input/building_timeseries.parquet",
]

CELL_PROFILER_BASE_URL = (
    "https://huggingface.co/buckets/bebeberr/cell-profiler/resolve"
)
CELL_PROFILER_CACHE_DIR = Path(tempfile.gettempdir()) / "cell-profiler"
CELL_PROFILER_TASK_NAMES = [
    "000-count-nuclei",
    "001-locate-nuclei-centers",
    "075-nuclei-locations",
    "114-nuclei-csv-open",
]
CELL_PROFILER_TIFF_FILES = {
    filename: [
        ARXIV_ROOT / task_name / input_root / "images" / filename
        for task_name in CELL_PROFILER_TASK_NAMES
        for input_root in ("environment/input", "input")
    ]
    for filename in ("1-162hrh2ax2.tif", "1-162hrhoe2.tif")
}


class DownloadFormParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_download_form = False
        self.action: str | None = None
        self.fields: dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = dict(attrs)
        if tag == "form" and attr_map.get("id") == "download-form":
            self.in_download_form = True
            self.action = attr_map.get("action")
        elif self.in_download_form and tag == "input":
            name = attr_map.get("name")
            if name:
                self.fields[name] = attr_map.get("value") or ""

    def handle_endtag(self, tag: str) -> None:
        if tag == "form":
            self.in_download_form = False


def ssl_context() -> ssl.SSLContext | None:
    try:
        import certifi
    except ImportError:
        return None
    return ssl.create_default_context(cafile=certifi.where())


def fetch(url: str) -> bytes:
    req = request.Request(url, headers={"User-Agent": "tua-bench-setup/1.0"})
    with request.urlopen(req, timeout=60, context=ssl_context()) as response:
        return response.read()


def google_drive_opener() -> request.OpenerDirector:
    return request.build_opener(
        request.HTTPCookieProcessor(CookieJar()),
        request.HTTPSHandler(context=ssl_context()),
    )


def google_drive_request(url: str) -> request.Request:
    return request.Request(url, headers={"User-Agent": "Mozilla/5.0"})


def copy_response_to_path(response, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp_target = target.with_suffix(target.suffix + ".tmp")
    with tmp_target.open("wb") as out:
        copyfileobj(response, out)
    tmp_target.replace(target)


def download_google_drive_file(file_id: str, target: Path) -> None:
    if target.exists():
        print(f"exists: {target}")
        return

    opener = google_drive_opener()
    url = f"https://drive.google.com/uc?export=download&id={file_id}"
    print(f"download: {url}")

    with opener.open(google_drive_request(url), timeout=120) as response:
        content_type = response.headers.get_content_type()
        if content_type != "text/html":
            copy_response_to_path(response, target)
            print(f"wrote: {target}")
            return

        html = response.read().decode("utf-8", errors="replace")

    parser = DownloadFormParser()
    parser.feed(html)
    if not parser.action:
        raise RuntimeError("Google Drive download confirmation form was not found")

    confirm_url = parser.action
    if parser.fields:
        confirm_url = f"{confirm_url}?{parse.urlencode(parser.fields)}"

    with opener.open(google_drive_request(confirm_url), timeout=120) as response:
        copy_response_to_path(response, target)
    print(f"wrote: {target}")


def download_url_to_file(url: str, target: Path) -> None:
    if target.exists():
        print(f"exists: {target}")
        return

    print(f"download: {url}")
    req = request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with request.urlopen(req, timeout=120, context=ssl_context()) as response:
        copy_response_to_path(response, target)
    print(f"wrote: {target}")


def extract_tar_member(tar: tarfile.TarFile, member_name: str, target: Path) -> None:
    if target.exists():
        print(f"exists: {target}")
        return

    source = tar.extractfile(member_name)
    if source is None:
        raise RuntimeError(f"Archive member is not a regular file: {member_name}")

    target.parent.mkdir(parents=True, exist_ok=True)
    with source, target.open("wb") as out:
        copyfileobj(source, out)
    print(f"wrote: {target}")


def copy_cached_file(source: Path, target: Path) -> None:
    if target.exists():
        print(f"exists: {target}")
        return

    target.parent.mkdir(parents=True, exist_ok=True)
    copyfile(source, target)
    print(f"wrote: {target}")


def downloaded_data_targets() -> list[Path]:
    targets = [DRAWIO_SOURCE_TARGET, *DRAWIO_PNG_TARGETS]
    targets.extend(
        target for target_list in MRI_DATA_FILES.values() for target in target_list
    )
    targets.extend(MRI_PNG_SLICE_TARGETS)
    targets.extend(VIDEO_DATA_FILES.values())
    targets.extend(
        target
        for target_list in FLOOR_PLAN_PNG_FILES.values()
        for target in target_list
    )
    targets.extend(COMSTOCK_TIMESERIES_PARQUET_TARGETS)
    targets.extend(
        target
        for target_list in CELL_PROFILER_TIFF_FILES.values()
        for target in target_list
    )
    return targets


def reset_downloaded_data() -> None:
    for target in downloaded_data_targets():
        if target.exists():
            target.unlink()
            print(f"removed: {target}")
        else:
            print(f"missing: {target}")


def ensure_mri_data() -> None:
    missing_targets = [
        target
        for targets in MRI_DATA_FILES.values()
        for target in targets
        if not target.exists()
    ]
    for targets in MRI_DATA_FILES.values():
        for target in targets:
            if target.exists():
                print(f"exists: {target}")

    if not missing_targets:
        return

    download_google_drive_file(MRI_ARCHIVE_FILE_ID, MRI_ARCHIVE_CACHE)
    with tarfile.open(MRI_ARCHIVE_CACHE) as tar:
        for member_name, targets in MRI_DATA_FILES.items():
            for target in targets:
                extract_tar_member(tar, member_name, target)


def png_chunk(chunk_type: bytes, payload: bytes) -> bytes:
    return (
        struct.pack(">I", len(payload))
        + chunk_type
        + payload
        + struct.pack(">I", binascii.crc32(chunk_type + payload) & 0xFFFFFFFF)
    )


def gray_png_bytes(pixels) -> bytes:
    height, width = pixels.shape
    raw = b"".join(b"\x00" + pixels[row].tobytes() for row in range(height))
    png = b"\x89PNG\r\n\x1a\n"
    png += png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 0, 0, 0, 0))
    png += png_chunk(b"IDAT", zlib.compress(raw, 6))
    png += png_chunk(b"IEND", b"")
    return png


def generate_mri_png_slices(source: Path) -> dict[str, bytes]:
    try:
        import nibabel as nib
        import numpy as np
    except ImportError as exc:
        raise RuntimeError(
            "Generating MRI PNG slice references requires nibabel and numpy. "
            "Run `uv sync` before `setup-env`."
        ) from exc

    data = np.asanyarray(nib.load(str(source)).dataobj)
    if data.ndim != 4 or data.shape[2] != len(MRI_PNG_SLICE_FILENAMES):
        raise RuntimeError(f"Unexpected MRI volume shape for PNG export: {data.shape}")

    volume = data[..., 0]
    slices = {}
    for index, filename in enumerate(MRI_PNG_SLICE_FILENAMES):
        oriented = np.rot90(volume[:, :, index], 1).astype(np.float64)
        pixels = np.rint(np.clip(oriented, 0, 977) / 977.0 * 255.0).astype(np.uint8)
        slices[filename] = gray_png_bytes(pixels)
    return slices


def ensure_mri_png_slices() -> None:
    missing_targets = [target for target in MRI_PNG_SLICE_TARGETS if not target.exists()]
    for target in MRI_PNG_SLICE_TARGETS:
        if target.exists():
            print(f"exists: {target}")

    if not missing_targets:
        return

    if not MRI_PNG_SLICE_INPUT.exists():
        raise RuntimeError(f"Missing MRI source for PNG export: {MRI_PNG_SLICE_INPUT}")

    slices = generate_mri_png_slices(MRI_PNG_SLICE_INPUT)
    for target in missing_targets:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(slices[target.name])
        print(f"wrote: {target}")


def ensure_video_data() -> None:
    missing_targets = [
        target for target in VIDEO_DATA_FILES.values() if not target.exists()
    ]
    for target in VIDEO_DATA_FILES.values():
        if target.exists():
            print(f"exists: {target}")

    if not missing_targets:
        return

    download_url_to_file(VIDEO_SHARD_URL, VIDEO_SHARD_CACHE)
    with tarfile.open(VIDEO_SHARD_CACHE) as tar:
        for member_name, target in VIDEO_DATA_FILES.items():
            extract_tar_member(tar, member_name, target)


def ensure_floor_plan_pngs() -> None:
    missing_targets = [
        target
        for targets in FLOOR_PLAN_PNG_FILES.values()
        for target in targets
        if not target.exists()
    ]
    for targets in FLOOR_PLAN_PNG_FILES.values():
        for target in targets:
            if target.exists():
                print(f"exists: {target}")

    if not missing_targets:
        return

    for filename, targets in FLOOR_PLAN_PNG_FILES.items():
        if all(target.exists() for target in targets):
            continue

        cache_target = FLOOR_PLAN_PNG_CACHE_DIR / filename
        url = f"{FLOOR_PLAN_PNG_BASE_URL}/{filename}?download=true"
        download_url_to_file(url, cache_target)
        for target in targets:
            copy_cached_file(cache_target, target)


def ensure_comstock_timeseries_parquet() -> None:
    missing_targets = [
        target
        for target in COMSTOCK_TIMESERIES_PARQUET_TARGETS
        if not target.exists()
    ]
    for target in COMSTOCK_TIMESERIES_PARQUET_TARGETS:
        if target.exists():
            print(f"exists: {target}")

    if not missing_targets:
        return

    download_url_to_file(
        COMSTOCK_TIMESERIES_PARQUET_URL, COMSTOCK_TIMESERIES_PARQUET_CACHE
    )
    for target in missing_targets:
        copy_cached_file(COMSTOCK_TIMESERIES_PARQUET_CACHE, target)


def ensure_cell_profiler_tiffs() -> None:
    missing_targets = [
        target
        for targets in CELL_PROFILER_TIFF_FILES.values()
        for target in targets
        if not target.exists()
    ]
    for targets in CELL_PROFILER_TIFF_FILES.values():
        for target in targets:
            if target.exists():
                print(f"exists: {target}")

    if not missing_targets:
        return

    for filename, targets in CELL_PROFILER_TIFF_FILES.items():
        if all(target.exists() for target in targets):
            continue

        cache_target = CELL_PROFILER_CACHE_DIR / filename
        url = f"{CELL_PROFILER_BASE_URL}/{filename}?download=true"
        download_url_to_file(url, cache_target)
        for target in targets:
            copy_cached_file(cache_target, target)


def extract_drawio_page(drawio_bytes: bytes, page_id: str) -> bytes:
    root = ET.fromstring(drawio_bytes)
    for diagram in root.findall("diagram"):
        if diagram.get("id") == page_id:
            out = ET.Element("mxfile", root.attrib)
            out.set("pages", "1")
            out.append(diagram)
            return ET.tostring(out, encoding="utf-8")
    raise RuntimeError(f"Could not find draw.io page id {page_id!r}")


def ensure_drawio_source() -> bytes:
    if DRAWIO_SOURCE_TARGET.exists():
        print(f"exists: {DRAWIO_SOURCE_TARGET}")
        return DRAWIO_SOURCE_TARGET.read_bytes()

    print(f"download: {DRAWIO_SOURCE_URL}")
    drawio_bytes = extract_drawio_page(fetch(DRAWIO_SOURCE_URL), DRAWIO_PAGE_ID)
    DRAWIO_SOURCE_TARGET.parent.mkdir(parents=True, exist_ok=True)
    DRAWIO_SOURCE_TARGET.write_bytes(drawio_bytes)
    print(f"wrote: {DRAWIO_SOURCE_TARGET}")
    return drawio_bytes


def export_drawio_png(drawio_bytes: bytes) -> bytes:
    body = parse.urlencode(
        {
            "format": "png",
            "xml": drawio_bytes.decode("utf-8"),
        }
    ).encode("utf-8")
    req = request.Request(
        DRAWIO_EXPORT_URL,
        data=body,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": "https://app.diagrams.net",
            "Referer": "https://app.diagrams.net/",
            "User-Agent": "Mozilla/5.0",
        },
    )
    with request.urlopen(req, timeout=120, context=ssl_context()) as response:
        png_bytes = response.read()

    if not png_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        raise RuntimeError("draw.io export did not return PNG data")
    return png_bytes


def ensure_drawio_pngs(drawio_bytes: bytes) -> None:
    missing_targets = [target for target in DRAWIO_PNG_TARGETS if not target.exists()]
    for target in DRAWIO_PNG_TARGETS:
        if target.exists():
            print(f"exists: {target}")

    if not missing_targets:
        return

    print(f"export: {DRAWIO_EXPORT_URL}")
    png_bytes = export_drawio_png(drawio_bytes)
    for target in missing_targets:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(png_bytes)
        print(f"wrote: {target}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download or reset generated benchmark data files."
    )
    parser.add_argument(
        "--reset",
        "--clean",
        action="store_true",
        dest="reset",
        help="delete files restored by this script from the repo and exit",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.reset:
        reset_downloaded_data()
        return 0

    drawio_bytes = ensure_drawio_source()
    ensure_drawio_pngs(drawio_bytes)
    ensure_mri_data()
    ensure_mri_png_slices()
    ensure_video_data()
    ensure_floor_plan_pngs()
    ensure_comstock_timeseries_parquet()
    ensure_cell_profiler_tiffs()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"setup_env.py: {exc}", file=sys.stderr)
        raise SystemExit(1)
