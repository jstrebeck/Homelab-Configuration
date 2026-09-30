"""KServe storage initializer for MLflow registry URIs.

Usage (KServe passes both arguments): initializer.py <storage-uri> <dest-dir>

    models:/<name>@<alias>     resolve the alias at pod start
    models:/<name>/<version>   a fixed version

Resolves the URI against the MLflow tracking server in $MLFLOW_TRACKING_URI and
downloads the model's files through the server's artifact proxy
(--serve-artifacts), so no object-store credentials are needed. Standard
library only: the MLflow client is not used because its parallel downloader
can stall and leave zero-filled files behind.

Besides the model files it writes to <dest-dir>:
  mlflow-model.json    what was resolved (name, alias, version, run, tags)
  model-settings.json  {"parameters": {"version": "<n>"}} unless the model
                       ships one, so MLServer reports the registry version as
                       `model_version` in every V2 response
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, NoReturn

TIMEOUT = float(os.environ.get("MLFLOW_HTTP_TIMEOUT", "30"))
ATTEMPTS = 4
URI = re.compile(r"^models:/(?P<name>[^/@]+)(?:@(?P<alias>[^/]+)|/(?P<version>\d+))/?$")
PROXY = re.compile(r"^mlflow-artifacts:(?://[^/]*)?/?(?P<path>.*)$")


def log(event: str, **fields: Any) -> None:
    print(json.dumps({"event": event, **fields}), flush=True)


def fail(message: str) -> NoReturn:
    log("error", message=message)
    sys.exit(1)


def request(url: str) -> urllib.request.Request:
    req = urllib.request.Request(url)
    if token := os.environ.get("MLFLOW_TRACKING_TOKEN"):
        req.add_header("Authorization", f"Bearer {token}")
    return req


def with_retries(what: str, fn: Any) -> Any:
    for attempt in range(1, ATTEMPTS + 1):
        try:
            return fn()
        except urllib.error.HTTPError as exc:
            if exc.code < 500 or attempt == ATTEMPTS:
                body = exc.read().decode(errors="replace")[:300]
                fail(f"{what}: HTTP {exc.code} {body}")
        except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
            if attempt == ATTEMPTS:
                fail(f"{what}: {exc}")
        time.sleep(2**attempt)
        log("retry", what=what, attempt=attempt + 1)
    raise AssertionError("unreachable")


def get_json(base: str, endpoint: str, **params: str) -> Any:
    url = f"{base}{endpoint}?{urllib.parse.urlencode(params)}"

    def call() -> Any:
        with urllib.request.urlopen(request(url), timeout=TIMEOUT) as resp:
            return json.load(resp)

    return with_retries(f"GET {endpoint}", call)


def list_files(base: str, path: str) -> list[tuple[str, int]]:
    """All files under an artifact path, as (relative path, size), recursively."""
    out: list[tuple[str, int]] = []
    listing = get_json(base, "/api/2.0/mlflow-artifacts/artifacts", path=path)
    for entry in listing.get("files", []):
        rel = entry["path"]
        if entry.get("is_dir"):
            out += [(f"{rel}/{sub}", size) for sub, size in list_files(base, f"{path}/{rel}")]
        else:
            out.append((rel, int(entry.get("file_size", -1))))
    return out


def download(base: str, src: str, dest: Path, expected_size: int) -> None:
    url = f"{base}/api/2.0/mlflow-artifacts/artifacts/{urllib.parse.quote(src)}"
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".part")

    def call() -> None:
        with urllib.request.urlopen(request(url), timeout=TIMEOUT) as resp, tmp.open("wb") as fh:
            while chunk := resp.read(1 << 20):
                fh.write(chunk)

    with_retries(f"download {src}", call)
    size = tmp.stat().st_size
    if expected_size >= 0 and size != expected_size:
        fail(f"download {src}: got {size} bytes, expected {expected_size}")
    tmp.rename(dest)


def main(argv: list[str]) -> None:
    if len(argv) != 3:
        fail("usage: initializer.py <models:/name@alias|models:/name/version> <dest-dir>")
    uri, dest = argv[1], Path(argv[2])
    base = os.environ.get("MLFLOW_TRACKING_URI", "").rstrip("/")
    if not base.startswith(("http://", "https://")):
        fail("MLFLOW_TRACKING_URI must be set to the MLflow server's http(s) URL")
    match = URI.match(uri)
    if not match:
        fail(f"unsupported storage URI {uri!r}; expected models:/<name>@<alias> or /<version>")
    name, alias, version = match["name"], match["alias"], match["version"]

    if alias:
        mv = get_json(base, "/api/2.0/mlflow/registered-models/alias", name=name, alias=alias)
    else:
        mv = get_json(base, "/api/2.0/mlflow/model-versions/get", name=name, version=version)
    mv = mv["model_version"]
    version = str(mv["version"])
    log("resolved", uri=uri, name=name, alias=alias, version=version, run_id=mv.get("run_id"))

    artifact_uri = get_json(
        base, "/api/2.0/mlflow/model-versions/get-download-uri", name=name, version=version
    )["artifact_uri"]
    proxied = PROXY.match(artifact_uri)
    if not proxied:
        fail(f"{artifact_uri!r} is not served by the MLflow artifact proxy (mlflow-artifacts:/)")
    root = proxied["path"].strip("/")

    files = list_files(base, root)
    if not any(Path(rel).name == "MLmodel" for rel, _ in files):
        fail(f"no MLmodel under {artifact_uri}")
    dest.mkdir(parents=True, exist_ok=True)
    total = 0
    for rel, size in files:
        download(base, f"{root}/{rel}", dest / rel, size)
        total += max(size, 0)
    log("downloaded", files=len(files), bytes=total, dest=str(dest))

    tags = {t["key"]: t["value"] for t in mv.get("tags", [])}
    (dest / "mlflow-model.json").write_text(
        json.dumps(
            {
                "name": name,
                "alias": alias,
                "version": version,
                "run_id": mv.get("run_id"),
                "source": mv.get("source"),
                "artifact_uri": artifact_uri,
                "tags": tags,
            },
            indent=2,
        )
    )
    settings = dest / "model-settings.json"
    if not settings.exists():
        settings.write_text(json.dumps({"parameters": {"version": version}}))
    log("done", name=name, version=version)


if __name__ == "__main__":
    main(sys.argv)
