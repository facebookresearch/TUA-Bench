# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

TASK_SPEC = {
    "artifact_paths": ["/app/saa-format-guide.pptx"],
    "example_id": "ac9bb6cb-1888-43ab-81e4-a98a547918cd",
    "inputs": [
        {
            "dest": "saa-format-guide.pptx",
            "url": "https://huggingface.co/datasets/xlangai/ubuntu_osworld_file_cache/resolve/main/libreoffice_impress/ac9bb6cb-1888-43ab-81e4-a98a547918cd/saa-format-guide.pptx",
        }
    ],
    "instruction": "I am preparing a PPT in Libreoffice impress. The slide number is barely visible to me. Please help me change the color of the slide number to red?",
    "live_task": False,
    "metric_spec": {
        "expected": {"rules": {"color": "red"}, "type": "rule"},
        "func": "check_page_number_colors",
        "options": {},
        "result": "/app/saa-format-guide.pptx",
    },
    "oracle": {
        "code": "import zipfile\n"
        "import xml.etree.ElementTree as ET\n"
        "\n"
        'slide_master_name = "ppt/slideMasters/slideMaster1.xml"\n'
        "ns = {\n"
        '    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",\n'
        '    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",\n'
        "}\n"
        "\n"
        'with zipfile.ZipFile(output_path, "r") as archive:\n'
        "    members = {name: archive.read(name) for name in archive.namelist()}\n"
        "\n"
        "root = ET.fromstring(members[slide_master_name])\n"
        "target_shape = None\n"
        'for shape in root.findall(".//p:sp", ns):\n'
        '    if shape.find(".//p:ph[@type=\'sldNum\']", ns) is not None:\n'
        "        target_shape = shape\n"
        "        break\n"
        "if target_shape is None:\n"
        '    raise RuntimeError("Could not locate the slide number placeholder")\n'
        "\n"
        'tx_body = target_shape.find("p:txBody", ns)\n'
        "if tx_body is None:\n"
        '    tx_body = ET.SubElement(target_shape, "{%s}txBody" % ns["p"])\n'
        'paragraph = tx_body.find("a:p", ns)\n'
        "if paragraph is None:\n"
        '    paragraph = ET.SubElement(tx_body, "{%s}p" % ns["a"])\n'
        'run = ET.SubElement(paragraph, "{%s}r" % ns["a"])\n'
        'run_props = ET.SubElement(run, "{%s}rPr" % ns["a"])\n'
        'solid_fill = ET.SubElement(run_props, "{%s}solidFill" % ns["a"])\n'
        'ET.SubElement(solid_fill, "{%s}srgbClr" % ns["a"], {"val": "FF0000"})\n'
        'ET.SubElement(run, "{%s}t" % ns["a"]).text = ""\n'
        "\n"
        'members[slide_master_name] = ET.tostring(root, encoding="utf-8", xml_declaration=True)\n'
        'with zipfile.ZipFile(output_path, "w") as archive:\n'
        "    for name, data in members.items():\n"
        "        archive.writestr(name, data)\n",
        "mode": "python_inline",
    },
    "output_path": "/app/saa-format-guide.pptx",
    "slug": "063-red-slide-numbers",
}

import json
import logging
import os
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

logger = logging.getLogger("tua.impress.osworld")
logging.basicConfig(level=logging.INFO)

CACHE_DIR = Path("/tmp") / TASK_SPEC["slug"]


def get_app_dir() -> Path:
    return Path(os.environ.get("APP_DIR", "/app"))


def get_agent_home() -> Path:
    return Path(os.environ.get("AGENT_HOME", "/home/agent"))


def localize_path(path: str) -> Path:
    if path.startswith("/app/"):
        return get_app_dir() / path.removeprefix("/app/")
    if path.startswith("/home/agent/"):
        return get_agent_home() / path.removeprefix("/home/agent/")
    return Path(path)


def fetch_cloud_file(url: str, dest: str) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    target = CACHE_DIR / dest
    if not target.exists():
        subprocess.run(
            ["curl", "-fsSL", "--retry", "10", "--retry-all-errors", "--retry-delay", "2", url, "-o", str(target)],
            check=True,
        )
    return target


def materialize_inputs(app_dir: Path) -> None:
    app_dir.mkdir(parents=True, exist_ok=True)
    get_agent_home().mkdir(parents=True, exist_ok=True)
    for item in TASK_SPEC.get("inputs", []):
        destination = app_dir / item["dest"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not destination.exists():
            shutil.copyfile(fetch_cloud_file(item["url"], item["dest"]), destination)


def run_oracle(app_dir: Path, agent_home: Path) -> None:
    env = os.environ.copy()
    env["APP_DIR"] = str(app_dir)
    env["AGENT_HOME"] = str(agent_home)
    subprocess.run(
        ["bash", str(Path(__file__).resolve().parents[1] / "solution" / "solve.sh")],
        check=True,
        env=env,
    )


def check_page_number_colors(pptx_file: str, rules: dict) -> float:
    color = rules["color"]

    def parse_rgb(rgb_str):
        if rgb_str is None:
            return None
        rgb_str = rgb_str.lstrip("#")
        if len(rgb_str) != 6:
            return None
        try:
            return tuple(int(rgb_str[index:index + 2], 16) for index in range(0, 6, 2))
        except ValueError:
            return None

    def is_red(rgb_tuple, threshold=50):
        if rgb_tuple is None:
            return False
        r, g, b = rgb_tuple
        return r > g + threshold and r > b + threshold

    def is_blue(rgb_tuple, threshold=50):
        if rgb_tuple is None:
            return False
        r, g, b = rgb_tuple
        return b > g + threshold and b > r + threshold

    def is_green(rgb_tuple, threshold=50):
        if rgb_tuple is None:
            return False
        r, g, b = rgb_tuple
        return g > r + threshold and g > b + threshold

    def is_black(rgb_tuple, threshold=50):
        if rgb_tuple is None:
            return False
        r, g, b = rgb_tuple
        return r < threshold and g < threshold and b < threshold

    with zipfile.ZipFile(pptx_file, "r") as archive:
        slide_master_name = "ppt/slideMasters/slideMaster1.xml"
        with archive.open(slide_master_name) as slide_master_file:
            root = ET.parse(slide_master_file).getroot()

        namespaces = {
            "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
            "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
        }

        slide_number_ph = root.find('.//p:ph[@type="sldNum"]', namespaces)
        slide_color_val = None

        if slide_number_ph is not None:
            color_elem = slide_number_ph.find(".//a:solidFill//a:srgbClr", namespaces)
            if color_elem is not None:
                slide_color_val = color_elem.get("val")

        if slide_color_val is None:
            for ph in root.findall(".//p:ph", namespaces):
                if ph.get("type") in {"sldNum", "ftr", "dt"}:
                    color_elem = ph.find(".//a:solidFill//a:srgbClr", namespaces)
                    if color_elem is not None:
                        slide_color_val = color_elem.get("val")
                        break

        if slide_color_val is None:
            for color_elem in reversed(root.findall(".//a:rPr//a:solidFill//a:srgbClr", namespaces)):
                color_val = color_elem.get("val")
                if color_val and color_val != "000000":
                    slide_color_val = color_val
                    break

        if slide_color_val is None:
            color_elems = root.findall(".//a:solidFill//a:srgbClr", namespaces)
            for color_elem in reversed(color_elems):
                color_val = color_elem.get("val")
                if color_val and color_val != "000000":
                    slide_color_val = color_val
                    break
            if slide_color_val is None and color_elems:
                slide_color_val = color_elems[-1].get("val")

    rgb_tuple = parse_rgb(slide_color_val)
    if rgb_tuple is None:
        return 0.0

    if color == "red" and not is_red(rgb_tuple):
        return 0.0
    if color == "blue" and not is_blue(rgb_tuple):
        return 0.0
    if color == "green" and not is_green(rgb_tuple):
        return 0.0
    if color == "black" and not is_black(rgb_tuple):
        return 0.0
    return 1.0


def run_evaluation() -> float:
    metric_spec = TASK_SPEC["metric_spec"]
    if metric_spec["func"] != "check_page_number_colors":
        raise ValueError(f"Unsupported metric function: {metric_spec['func']}")

    result_path = str(localize_path(metric_spec["result"]))
    expected = metric_spec["expected"]
    if expected["type"] != "rule":
        raise ValueError(f"Unsupported expected spec: {expected}")
    return check_page_number_colors(result_path, expected["rules"])


def run_sanity() -> dict:
    with tempfile.TemporaryDirectory(prefix=f"{TASK_SPEC['slug']}-") as temp_dir:
        app_dir = Path(temp_dir) / "app"
        agent_home = Path(temp_dir) / "home" / "agent"
        previous_app_dir = os.environ.get("APP_DIR")
        previous_agent_home = os.environ.get("AGENT_HOME")
        os.environ["APP_DIR"] = str(app_dir)
        os.environ["AGENT_HOME"] = str(agent_home)
        try:
            materialize_inputs(app_dir)
            fail_score = run_evaluation()
            run_oracle(app_dir, agent_home)
            pass_score = run_evaluation()
        finally:
            if previous_app_dir is None:
                os.environ.pop("APP_DIR", None)
            else:
                os.environ["APP_DIR"] = previous_app_dir
            if previous_agent_home is None:
                os.environ.pop("AGENT_HOME", None)
            else:
                os.environ["AGENT_HOME"] = previous_agent_home
    return {"fail_score": fail_score, "pass_score": pass_score}


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--sanity":
        print(json.dumps(run_sanity(), sort_keys=True))
    else:
        print(run_evaluation())
