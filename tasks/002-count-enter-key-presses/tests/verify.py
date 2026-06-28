# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from __future__ import annotations

import re
from pathlib import Path

RESULT_PATH = Path("/app/result.txt")
REWARD_PATH = Path("/logs/verifier/reward.txt")

GT_COUNT = 4


def write_reward(value: float) -> None:
    REWARD_PATH.parent.mkdir(parents=True, exist_ok=True)
    REWARD_PATH.write_text(f"{value:g}\n")


def parse_result(text: str) -> int | None:
    count_match = re.search(
        r"(?:count|answer|enter(?:\s+key)?(?:\s+presses)?)\s*[:=]\s*(-?\d+)",
        text,
        re.I,
    )
    if count_match:
        return int(count_match.group(1))
    numbers = [int(value) for value in re.findall(r"-?\d+", text)]
    if len(numbers) == 1:
        return numbers[0]
    return None


def main() -> None:
    if not RESULT_PATH.exists() or RESULT_PATH.stat().st_size == 0:
        write_reward(0)
        return

    parsed = parse_result(RESULT_PATH.read_text(errors="replace"))
    if parsed is None:
        write_reward(0)
        return

    write_reward(1 if parsed == GT_COUNT else 0)


if __name__ == "__main__":
    main()
