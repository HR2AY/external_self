#!/usr/bin/env python3
"""Start or reuse the local trajectory map when Personal Context is empty."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


SKILL_ROOT = Path(__file__).resolve().parent.parent
BUNDLED_APP = SKILL_ROOT / "assets" / "trajectory-app"
BUNDLED_DATA = BUNDLED_APP / "data" / "places.json"


def resolve_data_path(explicit: str | None) -> Path:
    candidates: list[Path] = []
    if explicit:
        candidates.append(Path(explicit))
    if os.environ.get("TRAJECTORY_PERSONAL_CONTEXT"):
        candidates.append(Path(os.environ["TRAJECTORY_PERSONAL_CONTEXT"]))

    cwd = Path.cwd().resolve()
    candidates.extend(parent / "data" / "places.json" for parent in (cwd, *cwd.parents))
    candidates.append(BUNDLED_DATA)
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    raise FileNotFoundError("Could not locate a trajectory data/places.json file")


def load_nodes(path: Path) -> list[dict[str, Any]]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, list):
        raise ValueError("FACT source must be a JSON array")
    return value


def state_path(data_path: Path) -> Path:
    digest = hashlib.sha256(str(data_path).encode("utf-8")).hexdigest()[:16]
    return Path(tempfile.gettempdir()) / f"external-self-map-{digest}.json"


def read_state(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else None
    except (OSError, ValueError, json.JSONDecodeError):
        return None


def url_is_ready(url: str, instance_token: str) -> bool:
    try:
        with urllib.request.urlopen(f"{url}/api/places", timeout=1.5) as response:
            value = json.loads(response.read().decode("utf-8"))
            return (
                response.status == 200
                and isinstance(value, list)
                and response.headers.get("X-Trajectory-Instance") == instance_token
            )
    except (OSError, ValueError, json.JSONDecodeError, urllib.error.URLError):
        return False


def available_port(preferred: int) -> int:
    for port in range(preferred, preferred + 30):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as candidate:
            try:
                candidate.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError("No local port is available for the trajectory map")


def ensure_dependencies(app_dir: Path) -> None:
    if (app_dir / "node_modules").is_dir():
        return
    npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
    if not npm:
        raise RuntimeError("Node.js and npm are required to start the trajectory map")
    subprocess.run([npm, "ci"], cwd=app_dir, check=True, stdout=sys.stderr, stderr=sys.stderr)


def start_server(
    app_dir: Path,
    data_path: Path,
    port: int,
    log_path: Path,
    instance_token: str,
) -> subprocess.Popen[bytes]:
    npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
    if not npm:
        raise RuntimeError("Node.js and npm are required to start the trajectory map")

    env = os.environ.copy()
    env["TRAJECTORY_DATA_FILE"] = str(data_path)
    env["TRAJECTORY_INSTANCE_TOKEN"] = instance_token
    command = [npm, "run", "dev", "--", "--host", "127.0.0.1", "--port", str(port), "--strictPort"]
    creationflags = 0
    start_new_session = os.name != "nt"
    if os.name == "nt":
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS

    log_handle = log_path.open("ab")
    try:
        return subprocess.Popen(
            command,
            cwd=app_dir,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            creationflags=creationflags,
            start_new_session=start_new_session,
        )
    finally:
        log_handle.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", help="Explicit Personal Context places.json path")
    parser.add_argument("--port", type=int, default=5173, help="Preferred local port")
    parser.add_argument("--force", action="store_true", help="Open the map even when trajectory nodes exist")
    args = parser.parse_args()

    try:
        data_path = resolve_data_path(args.data)
        nodes = load_nodes(data_path)
        if nodes and not args.force:
            print(json.dumps({
                "status": "trajectory-ready",
                "node_count": len(nodes),
                "trajectory_empty": False,
                "source": str(data_path),
                "map_required": False,
            }, ensure_ascii=False, indent=2))
            return 0

        runtime_state = state_path(data_path)
        previous = read_state(runtime_state)
        if (
            previous
            and isinstance(previous.get("url"), str)
            and isinstance(previous.get("instance_token"), str)
            and url_is_ready(previous["url"], previous["instance_token"])
        ):
            print(json.dumps({
                "status": "map-ready",
                "node_count": len(nodes),
                "trajectory_empty": len(nodes) == 0,
                "source": str(data_path),
                "map_required": True,
                "started": False,
                "reused": True,
                "url": previous["url"],
            }, ensure_ascii=False, indent=2))
            return 0

        ensure_dependencies(BUNDLED_APP)
        port = available_port(args.port)
        url = f"http://127.0.0.1:{port}"
        log_path = runtime_state.with_suffix(".log")
        instance_token = secrets.token_urlsafe(24)
        process = start_server(BUNDLED_APP, data_path, port, log_path, instance_token)
        runtime_state.write_text(json.dumps({
            "pid": process.pid,
            "url": url,
            "instance_token": instance_token,
            "source": str(data_path),
            "app": str(BUNDLED_APP),
            "log": str(log_path),
        }, ensure_ascii=False, indent=2), encoding="utf-8")

        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError(f"Trajectory map stopped during startup; inspect {log_path}")
            if url_is_ready(url, instance_token):
                print(json.dumps({
                    "status": "map-ready",
                    "node_count": len(nodes),
                    "trajectory_empty": len(nodes) == 0,
                    "source": str(data_path),
                    "map_required": True,
                    "started": True,
                    "reused": False,
                    "url": url,
                    "pid": process.pid,
                    "log": str(log_path),
                }, ensure_ascii=False, indent=2))
                return 0
            time.sleep(0.4)
        raise RuntimeError(f"Trajectory map did not become ready; inspect {log_path}")
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError, subprocess.CalledProcessError) as error:
        print(json.dumps({"status": "error", "error": str(error)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
