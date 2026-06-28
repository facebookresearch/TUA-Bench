# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tarfile
import zipfile
import sys
from pathlib import Path
from xml.sax.saxutils import escape


TASK_SPEC = {'expected': {'rules': {'expected': ['深圳市福田区益田路5055号信息枢纽大厦西门一楼',
                                     '深圳市福田区福华三路111号北三门会展中心警务室',
                                     '深圳市福田区正义街1号',
                                     '福田区莲科路18号莲花一村警务室',
                                     '深圳市福田区彩云路2-8长城盛世家园一期C座一楼一期管理处旁边',
                                     '深圳市福田区香梅路2002-4号',
                                     '福田区水围村龙景楼一楼',
                                     '深圳市福田区梅林路与梅康路交汇处卓悦汇4号、5号门对面',
                                     '深圳市福田区福强路3028号金沙嘴大厦',
                                     '深圳市福田区天安数码城昌泰公寓一楼',
                                     '福田区泰然五路5号天安数码城9栋',
                                     '深圳市福田区振兴路108号',
                                     '深圳市福田区滨河大道2033号',
                                     '深圳市福田区上沙四十八栋一巷11',
                                     '深圳市福田区北环大道与香蜜湖路交汇处香蜜原著警务室',
                                     '深圳市福田区八卦路38号八卦岭派出所',
                                     '深圳市福田区宝能城市公馆B栋一楼竹园警务室',
                                     '深圳市福田区竹子林五路12号',
                                     '福田区福强路3028号金沙嘴大厦',
                                     '福田区彩云路2-8长城盛世家园一期C座一楼一期管理处旁边',
                                     '福田区益田路5055号信息枢纽大厦西门一楼',
                                     '福田区正义街1号',
                                     '福田区香梅路2002-4号',
                                     '福田区梅林路与梅康路交汇处卓悦汇4号、5号门对面',
                                     '福田区天安数码城昌泰公寓一楼',
                                     '福田区振兴路108号',
                                     '福田区滨河大道2033号',
                                     '福田区上沙四十八栋一巷11',
                                     '福田区北环大道与香蜜湖路交汇处香蜜原著警务室',
                                     '福田区八卦路38号八卦岭派出所',
                                     '福田区宝能城市公馆B栋一楼竹园警务室',
                                     '福田区竹子林五路12号']},
              'type': 'rule'},
 'result': {'dest': 'AllLocations.docx', 'path': '/app/AllLocations.docx', 'type': 'vm_file'},
 'slug': '086-futian-checkin-addresses'}
CACHE_DIR = Path("/tmp") / TASK_SPEC["slug"] / "oracle"
ROOT_OVERRIDE = os.environ.get("TUA_SANITY_ROOT")


def localize_path(path: str | Path) -> Path:
    raw = str(path)
    if ROOT_OVERRIDE:
        root = Path(ROOT_OVERRIDE)
        if raw.startswith("/app/"):
            return root / "app" / raw.removeprefix("/app/")
        if raw == "/app":
            return root / "app"
        if raw.startswith("/home/user/"):
            return root / "home" / "user" / raw.removeprefix("/home/user/")
        if raw == "/home/user":
            return root / "home" / "user"
    return Path(raw).expanduser()


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def rewrite_root_path_text(text: str) -> str:
    if not ROOT_OVERRIDE:
        return text
    home_root = str(localize_path("/home/user"))
    app_root = str(localize_path("/app"))
    text = text.replace(home_root, "__TUA_HOME_REAL__").replace(app_root, "__TUA_APP_REAL__")
    text = text.replace("/home/user/", "__TUA_HOME__/").replace("/home/user", "__TUA_HOME__")
    text = text.replace("/app/", "__TUA_APP__/").replace("/app", "__TUA_APP__")
    return (
        text.replace("__TUA_HOME__", home_root)
        .replace("__TUA_APP__", app_root)
        .replace("__TUA_HOME_REAL__", home_root)
        .replace("__TUA_APP_REAL__", app_root)
    )


def prepare_subprocess_command(command, shell: bool):
    if not ROOT_OVERRIDE:
        return command
    if shell:
        text = command if isinstance(command, str) else " ".join(str(part) for part in command)
        return rewrite_root_path_text(text)
    if isinstance(command, str):
        return rewrite_root_path_text(command)
    return [rewrite_root_path_text(str(part)) for part in command]


def subprocess_env(kwargs: dict) -> dict:
    env = os.environ.copy()
    env.update(kwargs.get("env", {}))
    if ROOT_OVERRIDE:
        home = str(localize_path("/home/user"))
        env["HOME"] = home
        local_bin = str(localize_path("/home/user/.local/bin"))
        python_bin = str(Path(sys.executable).resolve().parent)
        path_parts = [python_bin, local_bin]
        existing_path = env.get("PATH")
        if existing_path:
            path_parts.append(existing_path)
        env["PATH"] = ":".join(path_parts)
        python_paths = [
            str(localize_path("/home/user/.local/lib/python3.13/site-packages")),
            str(localize_path("/home/user/.local/lib/python3.12/site-packages")),
            str(localize_path("/home/user/.local/lib/python3.11/site-packages")),
        ]
        existing = env.get("PYTHONPATH")
        if existing:
            python_paths.append(existing)
        env["PYTHONPATH"] = os.pathsep.join(python_paths)
    return env


def subprocess_cwd(kwargs: dict) -> str | None:
    if kwargs.get("cwd") is not None:
        return kwargs["cwd"]
    if ROOT_OVERRIDE:
        return str(localize_path("/home/user"))
    return None


def resolve_subprocess_invocation(command, shell: bool):
    if shell:
        return prepare_subprocess_command(command, True), True
    if isinstance(command, list) and any(token in {"|", "||", "&&", ";", ">", ">>", "<", "2>", "2>>"} for token in command):
        return prepare_subprocess_command(" ".join(str(part) for part in command), True), True
    return prepare_subprocess_command(command, False), False


if ROOT_OVERRIDE:
    _ORIG_RUN = subprocess.run
    _ORIG_POPEN = subprocess.Popen
    _ORIG_CHECK_OUTPUT = subprocess.check_output

    def _patched_run(command, *args, **kwargs):
        shell = bool(kwargs.get("shell", False))
        command, shell = resolve_subprocess_invocation(command, shell)
        kwargs["shell"] = shell
        kwargs["env"] = subprocess_env(kwargs)
        kwargs["cwd"] = subprocess_cwd(kwargs)
        return _ORIG_RUN(command, *args, **kwargs)

    def _patched_popen(command, *args, **kwargs):
        shell = bool(kwargs.get("shell", False))
        command, shell = resolve_subprocess_invocation(command, shell)
        kwargs["shell"] = shell
        kwargs["env"] = subprocess_env(kwargs)
        kwargs["cwd"] = subprocess_cwd(kwargs)
        return _ORIG_POPEN(command, *args, **kwargs)

    def _patched_check_output(command, *args, **kwargs):
        shell = bool(kwargs.get("shell", False))
        command, shell = resolve_subprocess_invocation(command, shell)
        kwargs["shell"] = shell
        kwargs["env"] = subprocess_env(kwargs)
        kwargs["cwd"] = subprocess_cwd(kwargs)
        return _ORIG_CHECK_OUTPUT(command, *args, **kwargs)

    subprocess.run = _patched_run
    subprocess.Popen = _patched_popen
    subprocess.check_output = _patched_check_output


def fetch(url: str, dest_name: str) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    target = CACHE_DIR / dest_name
    if not target.exists():
        subprocess.run(
            ["curl", "-fL", "--retry", "3", "--retry-delay", "1", url, "-o", str(target)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    return target


def write_minimal_docx(path: Path, paragraphs: list[str]) -> None:
    document_body = "".join(
        f"<w:p><w:r><w:t>{escape(text)}</w:t></w:r></w:p>"
        for text in paragraphs
    )
    content_types = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>
"""
    package_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>
"""
    document_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    {document_body}
    <w:sectPr/>
  </w:body>
</w:document>
"""
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", package_rels)
        archive.writestr("word/document.xml", document_xml)


def main() -> int:
    output = localize_path("/app/AllLocations.docx")
    ensure_parent(output)
    write_minimal_docx(output, TASK_SPEC["expected"]["rules"]["expected"][:3])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
