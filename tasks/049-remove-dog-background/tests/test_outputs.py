# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

import logging
import os
from pathlib import Path

import numpy as np
from PIL import Image
from skimage.metrics import structural_similarity as ssim

APP_DIR = Path(os.getenv("TUA_APP_DIR", "/app"))
PNG_PATH = APP_DIR / "dog_without_background.png"
REFERENCE_PATH = Path(
    os.getenv(
        "TUA_REFERENCE_PATH",
        "/tmp/tua-049-remove-dog-background/dog_cutout_gold.png",
    )
)

def structure_check_by_ssim(img1, img2, threshold=0.9):
    """Check if two images are approximately the same by SSIM"""
    min_size = 7
    if img1.width < min_size or img1.height < min_size or \
       img2.width < min_size or img2.height < min_size:
        logging.warning(f"image too small for ssim: {img1.size} vs {img2.size}")
        return False

    if img1.mode != 'RGB':
        img1 = img1.convert('RGB')
    if img2.mode != 'RGB':
        img2 = img2.convert('RGB')

    # Now both images are in RGB mode, so they should have the same number of channels (3)
    # But we still need to check the size (though the caller should have checked)
    if img1.size != img2.size:
        # If the sizes are different, we cannot compare, return False
        logging.debug(f"Images have different sizes: {img1.size} vs {img2.size}")
        return False

    array1 = np.array(img1)
    array2 = np.array(img2)
    # They should have the same shape now, but double check
    if array1.shape != array2.shape:
        logging.debug(f"Images have different shapes after conversion: {array1.shape} vs {array2.shape}")
        return False

    # Determine the window size for SSIM
    min_dim = min(array1.shape[0], array1.shape[1])
    if min_dim < 7:
        # If the smallest dimension is less than 7, set win_size to the next smaller odd number
        win_size = min_dim if min_dim % 2 == 1 else min_dim - 1
        if win_size < 1:
            logging.debug("Image too small for SSIM computation (min dimension < 1)")
            return False
    else:
        win_size = 7  # default

    try:
        # For newer versions of skimage, we use channel_axis, for older versions, multichannel
        # We try to use the newer way first, then fall back to the old way
        try:
            # Newer versions (channel_axis is available)
            similarity = ssim(array1, array2, win_size=win_size, channel_axis=2)
        except TypeError:
            # Older versions use multichannel
            similarity = ssim(array1, array2, win_size=win_size, multichannel=True)
    except Exception as e:
        logging.error(f"SSIM computation failed: {e}")
        return False

    logging.debug("SSIM: %s", similarity)
    return similarity >= threshold


def check_structure_sim(src_path, tgt_path):
    """
    Check if the structure of the two images are similar
    gimp:2a729ded-3296-423d-aec4-7dd55ed5fbb3
    """
    if src_path is None or tgt_path is None:
        return 0.

    try:
        img_src = Image.open(src_path)
        img_tgt = Image.open(tgt_path)

        if img_src.size != img_tgt.size:
            logging.debug(f"size different: src_path: {src_path}, tgt_path: {tgt_path}")
            return 0.0

        structure_same = structure_check_by_ssim(img_src, img_tgt)
        return 1.0 if structure_same else 0.0

    except Exception as e:
        logging.error(f"check_structure_sim error: {str(e)}")
        return 0.0


def test_output_matches_osworld_check_structure_sim():
    assert (
        check_structure_sim(REFERENCE_PATH, PNG_PATH) == 1.0
    ), "Output does not satisfy OSWorld check_structure_sim"
