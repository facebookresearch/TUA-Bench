# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

FROM debian:bookworm

ENV DEBIAN_FRONTEND=noninteractive
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="/opt/venv/bin:/usr/local/bin:${PATH}"

RUN printf '%s\n' \
    'Acquire::Queue-Mode "access";' \
    'Acquire::http::Pipeline-Depth "0";' \
    'Acquire::https::Pipeline-Depth "0";' \
    'Acquire::Retries "5";' \
    'Acquire::http::Timeout "30";' \
    'Acquire::https::Timeout "30";' \
    > /etc/apt/apt.conf.d/99tua-network
RUN apt-get update && apt-get install -y \
    asciinema \
    ca-certificates \
    curl \
    jq \
    python3 \
    python3-venv \
    tmux \
    unzip \
    zip \
 && python3 -m venv "$VIRTUAL_ENV" \
 && "$VIRTUAL_ENV/bin/pip" install --upgrade pip \
 && "$VIRTUAL_ENV/bin/pip" install pytest==8.4.1 \
 && useradd -m -s /bin/bash agent \
 && mkdir -p /app /app/Desktop /app/Downloads /opt/reference /var/lib/tua-state /home/agent/.config/Code/User /home/agent/.vscode/extensions \
 && ln -sfn /app /home/user \
 && ln -sfn /app/Desktop /home/agent/Desktop \
 && ln -sfn /app/Downloads /home/agent/Downloads \
 && chown -R agent:agent /app /opt/reference /var/lib/tua-state /home/agent \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

RUN python3 - <<'PY'
from pathlib import Path

Path("/usr/local/bin/code").write_text('#!/usr/bin/env python3\nfrom __future__ import annotations\n\nimport json\nimport sys\nimport zipfile\nfrom pathlib import Path\n\nSTATE_PATH = Path("/var/lib/tua-state/vscode_state.json")\nSETTINGS_PATH = Path.home() / ".config" / "Code" / "User" / "settings.json"\nKEYBINDINGS_PATH = Path.home() / ".config" / "Code" / "User" / "keybindings.json"\nEXTENSIONS_DIR = Path.home() / ".vscode" / "extensions"\n\n\ndef default_state() -> dict:\n    return {\n        "installed_extensions": [],\n        "current_target": None,\n    }\n\n\ndef ensure_layout() -> None:\n    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)\n    KEYBINDINGS_PATH.parent.mkdir(parents=True, exist_ok=True)\n    EXTENSIONS_DIR.mkdir(parents=True, exist_ok=True)\n    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)\n    if not SETTINGS_PATH.exists():\n        SETTINGS_PATH.write_text("{}\\n", encoding="utf-8")\n    if not KEYBINDINGS_PATH.exists():\n        KEYBINDINGS_PATH.write_text("[]\\n", encoding="utf-8")\n\n\ndef load_state() -> dict:\n    ensure_layout()\n    if not STATE_PATH.exists():\n        return default_state()\n    try:\n        return json.loads(STATE_PATH.read_text(encoding="utf-8"))\n    except Exception:\n        return default_state()\n\n\ndef save_state(state: dict) -> None:\n    ensure_layout()\n    STATE_PATH.write_text(json.dumps(state, indent=2, sort_keys=True) + "\\n", encoding="utf-8")\n\n\ndef parse_extension_id(raw: str) -> str:\n    candidate = Path(raw).expanduser()\n    if candidate.is_file() and candidate.suffix.lower() == ".vsix":\n        try:\n            with zipfile.ZipFile(candidate) as archive:\n                manifest_name = None\n                for name in archive.namelist():\n                    if name.endswith("/package.json") or name == "extension/package.json":\n                        manifest_name = name\n                        break\n                if manifest_name:\n                    manifest = json.loads(archive.read(manifest_name).decode("utf-8"))\n                    publisher = manifest.get("publisher")\n                    name = manifest.get("name")\n                    if publisher and name:\n                        return f"{publisher}.{name}"\n        except Exception:\n            pass\n        if candidate.name == "test.vsix":\n            return "undefined_publisher.test"\n    return raw\n\n\ndef install_extension(state: dict, raw: str) -> int:\n    ext_id = parse_extension_id(raw)\n    installed = state.setdefault("installed_extensions", [])\n    if ext_id not in installed:\n        installed.append(ext_id)\n        ext_dir = EXTENSIONS_DIR / ext_id.replace("/", "_")\n        ext_dir.mkdir(parents=True, exist_ok=True)\n    save_state(state)\n    return 0\n\n\ndef list_extensions(state: dict) -> int:\n    for ext_id in sorted(state.get("installed_extensions", [])):\n        print(ext_id)\n    return 0\n\n\ndef set_current_target(state: dict, raw: str | None) -> int:\n    path = None if raw is None else str(Path(raw).expanduser().resolve())\n    if path is None:\n        state["current_target"] = None\n    else:\n        target_path = Path(path)\n        if target_path.suffix == ".code-workspace":\n            target_type = "workspace"\n        elif target_path.is_dir():\n            target_type = "folder"\n        else:\n            target_type = "file"\n        state["current_target"] = {"path": path, "type": target_type}\n    save_state(state)\n    return 0\n\n\ndef add_to_workspace(state: dict, raw: str) -> int:\n    current = state.get("current_target") or {}\n    if current.get("type") != "workspace":\n        print("No workspace file is currently open for --add", file=sys.stderr)\n        return 1\n\n    workspace_path = Path(current["path"])\n    try:\n        data = json.loads(workspace_path.read_text(encoding="utf-8"))\n    except Exception:\n        data = {}\n\n    folders = data.setdefault("folders", [])\n    relative = Path(raw).expanduser().resolve().relative_to(workspace_path.parent.resolve())\n    entry = {"path": str(relative)}\n    if entry not in folders:\n        folders.append(entry)\n    workspace_path.write_text(\n        json.dumps(data, indent=2, sort_keys=False) + "\\n",\n        encoding="utf-8",\n    )\n    save_state(state)\n    return 0\n\n\ndef main(argv: list[str]) -> int:\n    ensure_layout()\n    state = load_state()\n\n    if len(argv) == 1:\n        return set_current_target(state, None)\n\n    args = argv[1:]\n    if args == ["--help"] or args == ["-h"]:\n        print("TUA VS Code task shim")\n        print("Supported: code [path], code --install-extension EXT, code --list-extensions, code --add PATH")\n        return 0\n    if args == ["--version"]:\n        print("1.95.0")\n        return 0\n\n    if args[0] == "--list-extensions":\n        return list_extensions(state)\n\n    if args[0] == "--install-extension" and len(args) >= 2:\n        return install_extension(state, args[1])\n\n    filtered: list[str] = []\n    used_add = False\n    index = 0\n    while index < len(args):\n        arg = args[index]\n        if arg in {"--reuse-window", "--new-window", "--wait"}:\n            index += 1\n            continue\n        if arg == "--add" and index + 1 < len(args):\n            status = add_to_workspace(state, args[index + 1])\n            if status != 0:\n                return status\n            used_add = True\n            index += 2\n            continue\n        if arg.startswith("-"):\n            index += 1\n            continue\n        filtered.append(arg)\n        index += 1\n\n    if filtered:\n        return set_current_target(state, filtered[0])\n    if used_add:\n        return 0\n    return set_current_target(state, None)\n\n\nif __name__ == "__main__":\n    raise SystemExit(main(sys.argv))\n', encoding="utf-8")
PY
RUN chmod +x /usr/local/bin/code

USER agent
WORKDIR /app

RUN /bin/bash -lc 'set -euo pipefail && mkdir -p /app/project && mkdir -p /app/data1 && mkdir -p /app/data2 && mkdir -p /app && curl -fsSL --retry 3 --retry-delay 1 https://huggingface.co/datasets/xlangai/ubuntu_osworld_file_cache/resolve/main/vs_code/6ed0a554-cbee-4b44-84ea-fd6c042f4fe1/project.code-workspace -o /app/project.code-workspace && code /app/project.code-workspace'
