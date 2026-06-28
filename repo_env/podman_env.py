# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

import asyncio
import asyncio.subprocess
import hashlib
import os
import shlex
import shutil
import socket
import subprocess
from enum import Enum
from pathlib import Path

from harbor.environments.base import BaseEnvironment, ExecResult
from harbor.environments.docker.docker import (
    _sanitize_docker_compose_project_name,
    _sanitize_docker_image_name,
)
from harbor.models.task.config import EnvironmentConfig
from harbor.models.trial.config import ServiceVolumeConfig
from harbor.models.trial.paths import EnvironmentPaths, TrialPaths


class PodmanEnvironmentType(str, Enum):
    PODMAN = "podman"


class PodmanEnvironment(BaseEnvironment):
    """Minimal Podman backend for single-container Harbor tasks.

    This backend intentionally targets the common Harbor task shape used in this
    repo: an `environment/Dockerfile` with one main container. It does not try
    to emulate Harbor's Docker Compose backend.
    """
    _HOST_PORT_ID_BASE = 10000
    _HOST_PORT_ID_SPAN = 4000
    _DISPLAY_BASE = 99
    _CHROME_REMOTE_DEBUGGING_PORT_BASE = 1337

    def __init__(
        self,
        environment_dir: Path,
        environment_name: str,
        session_id: str,
        trial_paths: TrialPaths,
        task_env_config: EnvironmentConfig,
        keep_containers: bool = False,
        mounts_json: list[ServiceVolumeConfig] | None = None,
        *args,
        **kwargs,
    ):
        self._dockerfile_path = environment_dir / "Dockerfile"
        self._environment_docker_compose_path = environment_dir / "docker-compose.yaml"
        self._container_name = _sanitize_docker_compose_project_name(session_id)
        self._built_image_name = _sanitize_docker_image_name(f"hb__{environment_name}")
        self._runtime_image_name: str | None = None
        self._used_prebuilt_image = False
        self._task_port_id = self._allocate_task_port_id(session_id)
        self._display_number = self._DISPLAY_BASE + self._task_port_id
        self._chrome_remote_debugging_port = (
            self._CHROME_REMOTE_DEBUGGING_PORT_BASE + self._task_port_id
        )

        super().__init__(
            environment_dir=environment_dir,
            environment_name=environment_name,
            session_id=session_id,
            trial_paths=trial_paths,
            task_env_config=task_env_config,
            **kwargs,
        )

        self._keep_containers = keep_containers
        self._mounts_json = mounts_json or []

        if self._environment_docker_compose_path.exists():
            raise NotImplementedError(
                "PodmanEnvironment currently supports Dockerfile-based tasks only; "
                "task-local docker-compose.yaml is not supported."
            )

        self._validate_mounts()

    @classmethod
    def preflight(cls) -> None:
        if not shutil.which("podman"):
            raise SystemExit(
                "Podman is not installed or not on PATH. "
                "Please install Podman and try again."
            )
        try:
            subprocess.run(
                ["podman", "info"],
                capture_output=True,
                timeout=10,
                check=True,
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            raise SystemExit(
                "Podman is not ready. On macOS, ensure `podman machine init` has "
                "been run and `podman machine start` is active."
            ) from e

    @staticmethod
    def type() -> PodmanEnvironmentType:
        return PodmanEnvironmentType.PODMAN

    @property
    def is_mounted(self) -> bool:
        return False

    @property
    def supports_gpus(self) -> bool:
        return False

    @property
    def can_disable_internet(self) -> bool:
        return True

    def _validate_definition(self):
        if not self._dockerfile_path.exists() and not self.task_env_config.docker_image:
            raise FileNotFoundError(
                f"{self._dockerfile_path} not found and no prebuilt image configured. "
                "PodmanEnvironment requires either environment/Dockerfile or "
                "[environment].docker_image."
            )

    def _validate_mounts(self) -> None:
        for mount in self._mounts_json:
            if mount["type"] != "bind":
                raise NotImplementedError(
                    "PodmanEnvironment currently supports bind mounts only."
                )

    @staticmethod
    def _is_tcp_port_available(port: int) -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(("0.0.0.0", port))
            except OSError:
                return False
        return True

    def _allocate_task_port_id(self, session_id: str) -> int:
        digest = hashlib.blake2s(session_id.encode("utf-8"), digest_size=4).digest()
        start = int.from_bytes(digest, byteorder="big") % self._HOST_PORT_ID_SPAN

        for attempt in range(self._HOST_PORT_ID_SPAN):
            task_port_id = self._HOST_PORT_ID_BASE + (
                (start + attempt) % self._HOST_PORT_ID_SPAN
            )
            display_number = self._DISPLAY_BASE + task_port_id
            display_tcp_port = 6000 + display_number
            chrome_port = self._CHROME_REMOTE_DEBUGGING_PORT_BASE + task_port_id
            if self._is_tcp_port_available(display_tcp_port) and self._is_tcp_port_available(
                chrome_port
            ):
                return task_port_id

        raise RuntimeError(
            "Could not find available high ports for task display and Chrome debugging."
        )

    def _task_isolation_env(self) -> dict[str, str]:
        return {
            "TUA_BENCH_TASK_ID": str(self._task_port_id),
            "TUA_BENCH_TASK_PORT_ID": str(self._task_port_id),
            "TUA_BENCH_DISPLAY_ID": str(self._display_number),
            "DISPLAY": f":{self._display_number}",
            "TUA_CHROME_REMOTE_DEBUGGING_PORT": str(
                self._chrome_remote_debugging_port
            ),
            "REMOTE_DEBUGGING_URL": (
                f"http://127.0.0.1:{self._chrome_remote_debugging_port}"
            ),
        }

    def _validate_gpu_support(self):
        if self.task_env_config.gpus > 0:
            raise RuntimeError(
                f"Task requires {self.task_env_config.gpus} GPU(s) but podman "
                "support is not implemented in this backend."
            )

    def _validate_internet_config(self):
        return

    @staticmethod
    def _is_corrupt_build_cache_error(error: Exception) -> bool:
        message = str(error)
        return (
            "layer not known" in message
            and "cached image exists from a previous build" in message
        )

    async def _build_runtime_image(
        self,
        build_command: list[str],
        timeout_sec: int,
    ) -> None:
        try:
            await self._run_podman_command(
                build_command,
                timeout_sec=timeout_sec,
            )
        except RuntimeError as error:
            if not self._is_corrupt_build_cache_error(error):
                raise

            self.logger.warning(
                "Podman build cache lookup failed for %s; pruning builder cache and retrying without cache.",
                self.environment_name,
            )
            await self._run_podman_command(
                ["builder", "prune", "-f"],
                check=False,
            )
            if self._runtime_image_name is not None:
                await self._run_podman_command(
                    ["rmi", "-f", self._runtime_image_name],
                    check=False,
                )
            await self._run_podman_command(
                [build_command[0], "--no-cache", *build_command[1:]],
                timeout_sec=timeout_sec,
            )

    async def _run_podman_command(
        self,
        command: list[str],
        check: bool = True,
        timeout_sec: int | None = None,
    ) -> ExecResult:
        full_command = ["podman", *command]
        process = await asyncio.create_subprocess_exec(
            *full_command,
            env=os.environ.copy(),
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )

        try:
            if timeout_sec is not None:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout_sec,
                )
            else:
                stdout_bytes, stderr_bytes = await process.communicate()
        except asyncio.TimeoutError:
            process.terminate()
            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    process.communicate(),
                    timeout=5,
                )
            except asyncio.TimeoutError:
                process.kill()
                stdout_bytes, stderr_bytes = await process.communicate()
            raise RuntimeError(f"Command timed out after {timeout_sec} seconds")

        stdout = stdout_bytes.decode(errors="replace") if stdout_bytes else None
        stderr = stderr_bytes.decode(errors="replace") if stderr_bytes else None

        result = ExecResult(
            stdout=stdout,
            stderr=stderr,
            return_code=process.returncode or 0,
        )

        if check and result.return_code != 0:
            raise RuntimeError(
                f"Podman command failed for environment {self.environment_name}. "
                f"Command: {' '.join(full_command)}. "
                f"Return code: {result.return_code}. "
                f"Stdout: {result.stdout}. "
                f"Stderr: {result.stderr}."
            )

        return result

    def _run_mount_args(self) -> list[str]:
        args: list[str] = []
        for mount in self._mounts_json:
            source = mount["source"]
            target = mount["target"]
            spec = f"{source}:{target}"
            if mount.get("read_only"):
                spec += ":ro"
            args.extend(["-v", spec])
        return args

    async def _ensure_container_paths(self) -> None:
        await self.exec(
            (
                "mkdir -p /logs/agent /logs/verifier /logs/artifacts /tests /solution "
                "&& chmod 777 /logs /logs/agent /logs/verifier /logs/artifacts "
                "/tests /solution"
            ),
            user="root",
        )

    async def start(self, force_build: bool) -> None:
        self._used_prebuilt_image = bool(
            self.task_env_config.docker_image and not force_build
        )

        if self._used_prebuilt_image:
            assert self.task_env_config.docker_image is not None
            self._runtime_image_name = self.task_env_config.docker_image
            await self._run_podman_command(
                ["pull", self._runtime_image_name],
            )
        else:
            self._runtime_image_name = self._built_image_name
            build_command = ["build"]
            build_command.extend(
                [
                    "--tag",
                    self._runtime_image_name,
                    "--file",
                    str(self._dockerfile_path),
                    str(self.environment_dir),
                ]
            )
            await self._build_runtime_image(
                build_command,
                timeout_sec=int(self.task_env_config.build_timeout_sec),
            )

        await self._run_podman_command(
            ["rm", "-f", self._container_name],
            check=False,
        )

        run_command = [
            "run",
            "--detach",
            "--name",
            self._container_name,
            "--cpus",
            str(self.task_env_config.cpus),
            "--memory",
            f"{self.task_env_config.memory_mb}m",
        ]
        if not self.task_env_config.allow_internet:
            run_command.extend(["--network", "none"])
        for key, value in self._task_isolation_env().items():
            run_command.extend(["-e", f"{key}={value}"])
        for key, value in self._persistent_env.items():
            run_command.extend(["-e", f"{key}={value}"])
        run_command.extend(self._run_mount_args())
        run_command.extend(
            [
                self._runtime_image_name,
                "sleep",
                "infinity",
            ]
        )
        await self._run_podman_command(
            run_command,
        )
        await self._ensure_container_paths()

    async def stop(self, delete: bool):
        if self._keep_containers and delete:
            self.logger.warning(
                "Both `keep_containers` and `--delete` option are set. "
                "keep_containers takes precedence."
            )

        if self._keep_containers:
            await self._run_podman_command(
                ["stop", self._container_name],
                check=False,
            )
            return

        if delete:
            await self._run_podman_command(
                ["rm", "-f", self._container_name],
                check=False,
            )
            if not self._used_prebuilt_image and self._runtime_image_name:
                await self._run_podman_command(
                    ["rmi", "-f", self._runtime_image_name],
                    check=False,
                )
            return

        await self._run_podman_command(
            ["stop", self._container_name],
            check=False,
        )

    async def upload_file(self, source_path: Path | str, target_path: str):
        target_parent = str(Path(target_path).parent)
        await self.exec(f"mkdir -p {shlex.quote(target_parent)}", user="root")
        await self._run_podman_command(
            ["cp", str(source_path), f"{self._container_name}:{target_path}"]
        )

    async def upload_dir(self, source_dir: Path | str, target_dir: str):
        await self.exec(f"mkdir -p {shlex.quote(target_dir)}", user="root")
        await self._run_podman_command(
            ["cp", f"{source_dir}/.", f"{self._container_name}:{target_dir}"]
        )

    async def download_file(self, source_path: str, target_path: Path | str):
        target_path = Path(target_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        await self._run_podman_command(
            ["cp", f"{self._container_name}:{source_path}", str(target_path)]
        )

    async def download_dir(self, source_dir: str, target_dir: Path | str):
        target_dir = Path(target_dir)
        target_dir.mkdir(parents=True, exist_ok=True)
        await self._run_podman_command(
            ["cp", f"{self._container_name}:{source_dir}/.", str(target_dir)]
        )

    async def exec(
        self,
        command: str,
        cwd: str | None = None,
        env: dict[str, str] | None = None,
        timeout_sec: int | None = None,
        user: str | int | None = None,
    ) -> ExecResult:
        user = self._resolve_user(user)
        env = self._merge_env(env)

        script_parts: list[str] = []
        if cwd:
            script_parts.append(f"cd {shlex.quote(cwd)}")
        if env:
            script_parts.extend(
                f"export {key}={shlex.quote(str(value))}" for key, value in env.items()
            )
        script_parts.append(command)
        shell_command = " && ".join(script_parts)

        exec_command = ["exec"]
        if user is not None:
            exec_command.extend(["--user", str(user)])
        # Use a non-login shell so Podman preserves image-level ENV such as
        # PATH=/opt/venv/bin:..., which some verifiers rely on.
        exec_command.extend([self._container_name, "bash", "-c", shell_command])

        return await self._run_podman_command(
            exec_command,
            check=False,
            timeout_sec=timeout_sec,
        )

    async def attach(self) -> None:
        os.execvp(
            "podman",
            ["podman", "exec", "-it", self._container_name, "bash"],
        )
