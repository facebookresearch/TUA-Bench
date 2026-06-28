# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from __future__ import annotations

import json
import struct
import traceback
import zlib
from pathlib import Path

import numpy as np

PLAN_PATH = Path("/app/input/task_plan.json")
REFERENCE_DIR = Path("/tests/reference/prostate_00_png_slices")

PLAN = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
OUTPUT_DIR = Path(str(PLAN["png_output_dir"]))
EXPECTED_SLICE_COUNT = int(PLAN.get("expected_slice_count", 15))
FILENAME_PATTERN = str(PLAN.get("slice_filename_pattern", "prostate_00_t2_slice_{index:02d}.png"))
SSIM_THRESHOLD = float(PLAN.get("ssim_threshold", 0.995))
NRMSE_THRESHOLD = float(PLAN.get("nrmse_threshold", 0.02))


def _expected_names() -> list[str]:
    return [FILENAME_PATTERN.format(index=i) for i in range(EXPECTED_SLICE_COUNT)]


def _assert_required_outputs() -> None:
    assert OUTPUT_DIR.exists(), f"Missing output directory: {OUTPUT_DIR}"
    assert OUTPUT_DIR.is_dir(), f"Expected a directory at: {OUTPUT_DIR}"

    png_files = sorted(path.name for path in OUTPUT_DIR.glob("*.png"))
    expected = _expected_names()
    assert png_files == expected, (
        f"Expected exactly {len(expected)} PNG files named {expected}; got {png_files}"
    )

    reference_files = sorted(path.name for path in REFERENCE_DIR.glob("*.png"))
    assert reference_files == expected, (
        f"Reference directory is incomplete; expected {expected}, got {reference_files}"
    )


def _read_chunks(data: bytes) -> tuple[dict[str, object], list[bytes]]:
    assert data.startswith(b"\x89PNG\r\n\x1a\n"), "File is not a PNG"
    offset = 8
    ihdr: dict[str, object] | None = None
    idat_parts: list[bytes] = []
    palette: bytes | None = None

    while offset < len(data):
        assert offset + 8 <= len(data), "Truncated PNG chunk header"
        length = struct.unpack(">I", data[offset : offset + 4])[0]
        chunk_type = data[offset + 4 : offset + 8]
        chunk_start = offset + 8
        chunk_end = chunk_start + length
        assert chunk_end + 4 <= len(data), f"Truncated PNG chunk {chunk_type!r}"
        chunk_data = data[chunk_start:chunk_end]
        offset = chunk_end + 4

        if chunk_type == b"IHDR":
            width, height, bit_depth, color_type, compression, filter_method, interlace = struct.unpack(
                ">IIBBBBB", chunk_data
            )
            ihdr = {
                "width": width,
                "height": height,
                "bit_depth": bit_depth,
                "color_type": color_type,
                "compression": compression,
                "filter_method": filter_method,
                "interlace": interlace,
            }
        elif chunk_type == b"PLTE":
            palette = chunk_data
        elif chunk_type == b"IDAT":
            idat_parts.append(chunk_data)
        elif chunk_type == b"IEND":
            break

    assert ihdr is not None, "PNG is missing IHDR"
    ihdr["palette"] = palette
    return ihdr, idat_parts


def _unfilter_scanlines(raw: bytes, width: int, height: int, channels: int, bit_depth: int) -> np.ndarray:
    assert bit_depth in (8, 16), f"Only 8-bit and 16-bit PNGs are supported, got {bit_depth}"
    bytes_per_sample = bit_depth // 8
    bytes_per_pixel = channels * bytes_per_sample
    row_bytes = width * bytes_per_pixel
    expected = height * (row_bytes + 1)
    assert len(raw) >= expected, f"PNG data is truncated: expected {expected} bytes, got {len(raw)}"

    rows = np.zeros((height, row_bytes), dtype=np.uint8)
    previous = np.zeros(row_bytes, dtype=np.uint8)
    offset = 0

    for y in range(height):
        filter_type = raw[offset]
        offset += 1
        current = np.frombuffer(raw[offset : offset + row_bytes], dtype=np.uint8)
        offset += row_bytes
        recon = np.empty(row_bytes, dtype=np.int32)

        for x in range(row_bytes):
            left = int(recon[x - bytes_per_pixel]) if x >= bytes_per_pixel else 0
            up = int(previous[x])
            upper_left = int(previous[x - bytes_per_pixel]) if x >= bytes_per_pixel else 0
            value = int(current[x])

            if filter_type == 0:
                predictor = 0
            elif filter_type == 1:
                predictor = left
            elif filter_type == 2:
                predictor = up
            elif filter_type == 3:
                predictor = (left + up) // 2
            elif filter_type == 4:
                p = left + up - upper_left
                pa = abs(p - left)
                pb = abs(p - up)
                pc = abs(p - upper_left)
                predictor = left if pa <= pb and pa <= pc else up if pb <= pc else upper_left
            else:
                raise AssertionError(f"Unsupported PNG filter type: {filter_type}")

            recon[x] = (value + predictor) & 0xFF

        rows[y] = recon.astype(np.uint8)
        previous = rows[y]

    return rows


def _read_png_luminance(path: Path) -> np.ndarray:
    assert path.exists(), f"Missing PNG: {path}"
    assert path.is_file(), f"Expected a file at: {path}"
    assert path.stat().st_size > 0, f"PNG is empty: {path}"

    ihdr, idat_parts = _read_chunks(path.read_bytes())
    width = int(ihdr["width"])
    height = int(ihdr["height"])
    bit_depth = int(ihdr["bit_depth"])
    color_type = int(ihdr["color_type"])
    assert int(ihdr["compression"]) == 0, "Unsupported PNG compression method"
    assert int(ihdr["filter_method"]) == 0, "Unsupported PNG filter method"
    assert int(ihdr["interlace"]) == 0, "Interlaced PNGs are not supported"

    channels_by_color = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}
    assert color_type in channels_by_color, f"Unsupported PNG color type: {color_type}"
    channels = channels_by_color[color_type]
    raw = zlib.decompress(b"".join(idat_parts))
    rows = _unfilter_scanlines(raw, width, height, channels, bit_depth)

    if bit_depth == 16:
        image = rows.reshape(height, width, channels, 2).astype(np.uint16)
        image = image[:, :, :, 0] * 256 + image[:, :, :, 1]
    else:
        image = rows.reshape(height, width, channels).astype(np.float64)
    image = image.astype(np.float64, copy=False)
    scale = float((1 << bit_depth) - 1)

    if color_type == 0:
        gray = image[:, :, 0]
    elif color_type == 2:
        gray = 0.299 * image[:, :, 0] + 0.587 * image[:, :, 1] + 0.114 * image[:, :, 2]
    elif color_type == 3:
        palette = ihdr.get("palette")
        assert isinstance(palette, bytes) and palette, "Palette PNG is missing PLTE"
        colors = np.frombuffer(palette, dtype=np.uint8).reshape(-1, 3).astype(np.float64)
        indices = image[:, :, 0].astype(np.int64)
        rgb = colors[indices]
        gray = 0.299 * rgb[:, :, 0] + 0.587 * rgb[:, :, 1] + 0.114 * rgb[:, :, 2]
        scale = 255.0
    elif color_type == 4:
        gray = image[:, :, 0]
    else:
        gray = 0.299 * image[:, :, 0] + 0.587 * image[:, :, 1] + 0.114 * image[:, :, 2]

    return np.clip(gray / scale, 0.0, 1.0)


def _affine_adjust(candidate: np.ndarray, reference: np.ndarray) -> np.ndarray:
    cand_flat = candidate.reshape(-1)
    ref_flat = reference.reshape(-1)
    cand_var = float(np.var(cand_flat))
    if cand_var < 1e-12:
        return candidate
    cov = float(np.mean((cand_flat - cand_flat.mean()) * (ref_flat - ref_flat.mean())))
    scale = cov / cand_var
    offset = float(ref_flat.mean() - scale * cand_flat.mean())
    return np.clip(scale * candidate + offset, 0.0, 1.0)


def _ssim(candidate: np.ndarray, reference: np.ndarray) -> float:
    candidate = candidate.astype(np.float64, copy=False)
    reference = reference.astype(np.float64, copy=False)
    mu_x = float(candidate.mean())
    mu_y = float(reference.mean())
    var_x = float(candidate.var())
    var_y = float(reference.var())
    cov_xy = float(np.mean((candidate - mu_x) * (reference - mu_y)))
    c1 = 0.01**2
    c2 = 0.03**2
    return ((2 * mu_x * mu_y + c1) * (2 * cov_xy + c2)) / (
        (mu_x**2 + mu_y**2 + c1) * (var_x + var_y + c2)
    )


def _nrmse(candidate: np.ndarray, reference: np.ndarray) -> float:
    mse = float(np.mean((candidate - reference) ** 2))
    dynamic_range = float(reference.max() - reference.min())
    if dynamic_range < 1e-8:
        dynamic_range = 1.0
    return float(np.sqrt(mse) / dynamic_range)


def _compare_slice(candidate_path: Path, reference_path: Path) -> dict[str, object]:
    candidate = _read_png_luminance(candidate_path)
    reference = _read_png_luminance(reference_path)
    assert candidate.shape == reference.shape, (
        f"{candidate_path.name}: shape mismatch, got {candidate.shape}, expected {reference.shape}"
    )

    adjusted = _affine_adjust(candidate, reference)
    ssim = _ssim(adjusted, reference)
    nrmse = _nrmse(adjusted, reference)
    passed = ssim >= SSIM_THRESHOLD and nrmse <= NRMSE_THRESHOLD
    return {
        "file": candidate_path.name,
        "shape": list(candidate.shape),
        "ssim": ssim,
        "nrmse": nrmse,
        "passed": passed,
    }


def test_png_slices_match_reference() -> None:
    _assert_required_outputs()
    results = [
        _compare_slice(OUTPUT_DIR / name, REFERENCE_DIR / name)
        for name in _expected_names()
    ]
    failures = [result for result in results if not result["passed"]]
    summary = {
        "slice_count": len(results),
        "ssim_threshold": SSIM_THRESHOLD,
        "nrmse_threshold": NRMSE_THRESHOLD,
        "min_ssim": min(float(result["ssim"]) for result in results),
        "max_nrmse": max(float(result["nrmse"]) for result in results),
        "failed_slice_count": len(failures),
        "failed_slices": failures[:20],
    }
    print(json.dumps(summary, indent=2, sort_keys=True), flush=True)
    assert not failures, "One or more exported PNG slices do not match the reference images"


def _main() -> int:
    try:
        test_png_slices_match_reference()
    except Exception:
        traceback.print_exc()
        return 1
    print("test_png_slices_match_reference: PASS", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
