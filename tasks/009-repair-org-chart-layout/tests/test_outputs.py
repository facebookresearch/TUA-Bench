# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from __future__ import annotations

import base64
import os
import socket
from pathlib import Path
from urllib.parse import urlsplit

from google import genai
from google.genai import types as genai_types
from openai import OpenAI

PNG_PATH = Path("/app/corporate_org_chart.png")
REFERENCE_PATH = Path("/tests/reference/corporate_org_chart_reference.png")
RUNNING_IN_DOCKER = Path("/.dockerenv").exists()
RUNNING_IN_PODMAN = any(
    candidate.exists()
    for candidate in (Path("/run/.containerenv"), Path("/.containerenv"))
)
LLM_PROVIDER = os.getenv("TUA_BENCH_LLM_PROVIDER", "gemini").strip().lower()
MODEL = os.getenv(
    "TUA_BENCH_MODEL",
    "gemini-3.1-pro-preview" if LLM_PROVIDER == "gemini" else "gpt-5.4",
)
JUDGE_INSTRUCTIONS = """
You are grading a generated diagram image for a quick benchmark smoke test.
You may receive either a candidate image only, or a reference image followed by a
candidate image. If a reference is provided, use it to understand the intended
content and hierarchy, not to excuse visual defects in the candidate. Be lenient
on minor styling differences, but focus strictly on the requested criterion. For
defect checks, a single obvious defect should fail.
Return exactly two lines:
PASS or FAIL
<one short reason>
""".strip()
TARGET_DIAGRAM_DESCRIPTION = """
The target is a corporate organizational chart showing a hierarchical company
structure.

Expected boxes and hierarchy:
- Two yellow Co-Chairman boxes at the top jointly oversee a pink CEO box.
- CEO reports down to a pink COO box.
- COO oversees three executive branches: yellow CFO, green CTO, and blue CCO.
- CFO manages four light-yellow subordinate boxes: HR, Admin, Admin, and PR.
- CTO manages four green role boxes: Offshore Senior Front-end, Offshore Senior
  Back-end, System Admin, and Lead Front-End.
- Offshore Senior Front-end has a darker-green Offshore Junior Front-end below it.
- Offshore Senior Back-end has two darker-green Offshore Junior Back-end boxes below it.
- CCO manages five light-blue Content Specialist boxes.

Expected visual style:
- Pink for top leadership, yellow/cream for finance and administration, green
  for technology, and blue for content.
- Clean organization-chart reporting lines.
- No overlapped boxes.
- No jagged, messy, or visually broken connection lines.
""".strip()


def _build_gemini_thinking_config():
    thinking_config_cls = getattr(genai_types, "ThinkingConfig", None)
    thinking_level_enum = getattr(genai_types, "ThinkingLevel", None)
    thinking_level = getattr(thinking_level_enum, "HIGH", None)
    if thinking_config_cls is None or thinking_level is None:
        return None
    try:
        return thinking_config_cls(
            thinking_level=thinking_level,
            include_thoughts=False,
        )
    except TypeError:
        return None


GEMINI_THINKING_CONFIG = _build_gemini_thinking_config()


class JudgeLLM:
    def __init__(self, provider: str = LLM_PROVIDER, model: str = MODEL):
        self.provider = provider
        self.model = model

    def judge_candidate_against_reference(
        self,
        prompt: str,
        candidate_path: Path,
        reference_path: Path,
    ) -> str:
        if self.provider == "gemini":
            return self._judge_with_gemini(prompt, candidate_path, reference_path)
        if self.provider == "openai":
            return self._judge_with_openai(prompt, candidate_path, reference_path)
        raise ValueError(f"Unsupported judge provider: {self.provider}")

    def judge_candidate_only(self, prompt: str, candidate_path: Path) -> str:
        if self.provider == "gemini":
            return self._judge_candidate_only_with_gemini(prompt, candidate_path)
        if self.provider == "openai":
            return self._judge_candidate_only_with_openai(prompt, candidate_path)
        raise ValueError(f"Unsupported judge provider: {self.provider}")

    @staticmethod
    def _gemini_api_key() -> str:
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise RuntimeError(
                "Missing Gemini API key. Set GEMINI_API_KEY or GOOGLE_API_KEY."
            )
        return api_key

    @staticmethod
    def _gemini_http_options() -> genai_types.HttpOptions | None:
        api_base = os.getenv("GEMINI_API_BASE")
        if not api_base:
            return None
        return genai_types.HttpOptions(
            base_url=JudgeLLM._normalize_gemini_api_base(api_base)
        )

    @staticmethod
    def _normalize_gemini_api_base(api_base: str) -> str:
        parts = urlsplit(api_base)
        netloc = parts.netloc
        if parts.hostname in {"localhost", "127.0.0.1"}:
            port = f":{parts.port}" if parts.port is not None else ""
            if JudgeLLM._uses_host_network():
                netloc = f"127.0.0.1{port}"
            else:
                host_alias = JudgeLLM._container_host_alias()
                if host_alias is not None and JudgeLLM._host_resolves(host_alias):
                    netloc = f"{host_alias}{port}"
                elif host_alias is not None and parts.hostname == "localhost":
                    netloc = f"127.0.0.1{port}"
        path = parts.path.rstrip("/")
        for suffix in ("/v1alpha", "/v1beta", "/v1"):
            if path == suffix or path.endswith(suffix):
                path = path[: -len(suffix)]
                break

        rewritten = parts._replace(netloc=netloc, path=path).geturl()
        if rewritten != api_base:
            print(
                f"[judge_llm] rewrote GEMINI_API_BASE from {api_base} to {rewritten}",
                flush=True,
            )
        return rewritten

    @staticmethod
    def _uses_host_network() -> bool:
        value = os.getenv("TUA_BENCH_HOST_NETWORK", "").strip().lower()
        return value in {"1", "true", "yes"}

    @staticmethod
    def _host_resolves(host: str) -> bool:
        try:
            socket.getaddrinfo(host, None)
        except socket.gaierror:
            return False
        return True

    @staticmethod
    def _container_host_alias() -> str | None:
        runtime_override = os.getenv("TUA_BENCH_CONTAINER_RUNTIME", "").strip().lower()
        if runtime_override == "podman":
            return "host.containers.internal"
        if runtime_override == "docker":
            return "host.docker.internal"

        container_env = os.getenv("container", "").strip().lower()
        if "podman" in container_env:
            return "host.containers.internal"
        if "docker" in container_env:
            return "host.docker.internal"

        if RUNNING_IN_PODMAN:
            return "host.containers.internal"
        if RUNNING_IN_DOCKER:
            return "host.docker.internal"

        for cgroup_path in (Path("/proc/1/cgroup"), Path("/proc/self/cgroup")):
            try:
                cgroup_text = cgroup_path.read_text()
            except OSError:
                continue
            lowered = cgroup_text.lower()
            if "podman" in lowered or "libpod" in lowered:
                return "host.containers.internal"
            if "docker" in lowered:
                return "host.docker.internal"

        return None

    def _judge_with_gemini(
        self,
        prompt: str,
        candidate_path: Path,
        reference_path: Path,
    ) -> str:
        client = genai.Client(
            api_key=self._gemini_api_key(),
            http_options=self._gemini_http_options(),
        )
        response = client.models.generate_content(
            model=self.model,
            contents=[
                genai_types.Part.from_text(
                    text=(
                        f"{JUDGE_INSTRUCTIONS}\n\n{prompt}\n\n"
                        "First image: reference. Second image: candidate."
                    ),
                ),
                genai_types.Part.from_bytes(
                    data=reference_path.read_bytes(),
                    mime_type="image/png",
                ),
                genai_types.Part.from_bytes(
                    data=candidate_path.read_bytes(),
                    mime_type="image/png",
                ),
            ],
            config=genai_types.GenerateContentConfig(
                **(
                    {"temperature": 0}
                    if GEMINI_THINKING_CONFIG is None
                    else {
                        "temperature": 0,
                        "thinking_config": GEMINI_THINKING_CONFIG,
                    }
                )
            ),
        )
        return (response.text or "").strip()

    def _judge_candidate_only_with_gemini(
        self,
        prompt: str,
        candidate_path: Path,
    ) -> str:
        client = genai.Client(
            api_key=self._gemini_api_key(),
            http_options=self._gemini_http_options(),
        )
        response = client.models.generate_content(
            model=self.model,
            contents=[
                genai_types.Part.from_text(
                    text=f"{JUDGE_INSTRUCTIONS}\n\n{prompt}\n\nImage: candidate.",
                ),
                genai_types.Part.from_bytes(
                    data=candidate_path.read_bytes(),
                    mime_type="image/png",
                ),
            ],
            config=genai_types.GenerateContentConfig(
                **(
                    {"temperature": 0}
                    if GEMINI_THINKING_CONFIG is None
                    else {
                        "temperature": 0,
                        "thinking_config": GEMINI_THINKING_CONFIG,
                    }
                )
            ),
        )
        return (response.text or "").strip()

    def _judge_with_openai(
        self,
        prompt: str,
        candidate_path: Path,
        reference_path: Path,
    ) -> str:
        reference_url = "data:image/png;base64," + base64.b64encode(
            reference_path.read_bytes()
        ).decode("ascii")
        candidate_url = "data:image/png;base64," + base64.b64encode(
            candidate_path.read_bytes()
        ).decode("ascii")
        client = OpenAI()
        response = client.responses.create(
            model=self.model,
            instructions=JUDGE_INSTRUCTIONS,
            input=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": (
                                f"{prompt}\n\nFirst image: reference. "
                                "Second image: candidate."
                            ),
                        },
                        {
                            "type": "input_image",
                            "image_url": reference_url,
                            "detail": "auto",
                        },
                        {
                            "type": "input_image",
                            "image_url": candidate_url,
                            "detail": "auto",
                        },
                    ],
                }
            ],
            temperature=0,
            max_output_tokens=120,
        )
        return (response.output_text or "").strip()

    def _judge_candidate_only_with_openai(
        self,
        prompt: str,
        candidate_path: Path,
    ) -> str:
        candidate_url = "data:image/png;base64," + base64.b64encode(
            candidate_path.read_bytes()
        ).decode("ascii")
        client = OpenAI()
        response = client.responses.create(
            model=self.model,
            instructions=JUDGE_INSTRUCTIONS,
            input=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": f"{prompt}\n\nImage: candidate.",
                        },
                        {
                            "type": "input_image",
                            "image_url": candidate_url,
                            "detail": "auto",
                        },
                    ],
                }
            ],
            temperature=0,
            max_output_tokens=120,
        )
        return (response.output_text or "").strip()


JUDGE_LLM = JudgeLLM()


def _assert_pass(verdict: str) -> None:
    first_line = verdict.splitlines()[0].strip().upper() if verdict else ""
    label = first_line.split(maxsplit=1)[0].rstrip(":")
    assert label == "PASS", verdict


def _judge(prompt: str, label: str) -> str:
    verdict = JUDGE_LLM.judge_candidate_against_reference(
        prompt=prompt,
        candidate_path=PNG_PATH,
        reference_path=REFERENCE_PATH,
    )
    print(f"[{label}] provider={JUDGE_LLM.provider} model={JUDGE_LLM.model}", flush=True)
    print(f"[{label}] output:\n{verdict or '<empty>'}", flush=True)
    return verdict


def _judge_candidate_only(prompt: str, label: str) -> str:
    verdict = JUDGE_LLM.judge_candidate_only(
        prompt=prompt,
        candidate_path=PNG_PATH,
    )
    print(f"[{label}] provider={JUDGE_LLM.provider} model={JUDGE_LLM.model}", flush=True)
    print(f"[{label}] output:\n{verdict or '<empty>'}", flush=True)
    return verdict


def test_png_exists() -> None:
    assert PNG_PATH.exists(), f"Missing {PNG_PATH}"
    assert PNG_PATH.stat().st_size > 0, "PNG file is empty"
    assert REFERENCE_PATH.exists(), f"Missing verifier reference image: {REFERENCE_PATH}"
    assert REFERENCE_PATH.stat().st_size > 0, "Verifier reference image is empty"


def test_contains_all_target_boxes() -> None:
    test_png_exists()
    verdict = _judge(
        f"""
Target diagram specification:

{TARGET_DIAGRAM_DESCRIPTION}

Check only whether the candidate contains all target boxes. Pass only if the
candidate visibly includes:
- two Co-Chairman boxes
- CEO and COO
- CFO, CTO, and CCO
- HR, Admin, Admin, and PR under CFO
- Offshore Senior Front-end, Offshore Senior Back-end, System Admin, and Lead Front-End under CTO
- Offshore Junior Front-end and two Offshore Junior Back-end boxes under the senior offshore roles
- five Content Specialist boxes under CCO

Ignore minor color or spacing differences for this check.
""".strip(),
        "boxes_judge",
    )
    _assert_pass(verdict)


def test_connection_lines_are_not_jagged() -> None:
    test_png_exists()
    verdict = _judge_candidate_only(
        f"""
Target diagram specification:

{TARGET_DIAGRAM_DESCRIPTION}

Strictly check only the reporting connectors in the candidate image.

Pass only if the connectors form a tidy organization-chart tree: mostly
straight vertical/horizontal segments, clean shared trunks or buses from each
manager, and simple routing from each manager to direct reports.

Fail if you see any obvious connector-quality defect, including:
- stair-step or zig-zag routes with unnecessary repeated bends
- crooked, broken, disconnected, or fragmented line segments
- connectors that snake around boxes or take long confusing detours
- connectors that run through boxes, labels, or other unrelated branches
- connector clutter that makes reporting relationships ambiguous

Do not pass just because the labels are correct. Ignore the reference image's
line quality if it has imperfections; judge the candidate's connector routing
against the criteria above.
""".strip(),
        "connections_judge",
    )
    _assert_pass(verdict)


def test_boxes_do_not_overlap() -> None:
    test_png_exists()
    verdict = _judge_candidate_only(
        f"""
Target diagram specification:

{TARGET_DIAGRAM_DESCRIPTION}

Strictly check only for box collisions in the candidate image.

Pass only if every role is in its own distinct rectangle with visible separation
from neighboring role boxes, and every label is readable inside its own box.

Fail if you see any obvious layout collision, including:
- any two boxes overlapping, touching, or sharing visible area
- one box covering part of another box or its label
- labels or box borders drawn on top of another box
- dense lower-level boxes packed so tightly that separate boxes are not clearly
  distinguishable

Do not pass just because most boxes are readable. Ignore the reference image's
box spacing if it has imperfections; judge the candidate's box separation
against the criteria above.
""".strip(),
        "overlap_judge",
    )
    _assert_pass(verdict)


def test_overall_matches_requirement() -> None:
    test_png_exists()
    verdict = _judge(
        f"""
Target diagram specification:

{TARGET_DIAGRAM_DESCRIPTION}

Compare the candidate to the reference and the written specification overall.
Pass if the candidate is clearly a color-coded corporate organizational chart
with the requested hierarchy, department grouping, and readable reporting
relationships. Be lenient on exact dimensions, font, and small stylistic
differences. Fail overall if the candidate has obvious overlapping boxes,
unreadable labels, or messy connector routing, even if most required boxes are
present.
""".strip(),
        "overall_judge",
    )
    _assert_pass(verdict)
