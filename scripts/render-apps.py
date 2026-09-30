#!/usr/bin/env python3
"""Render every Argo CD Application in Kubernetes/argocd/apps the way Argo CD would.

Writes one multi-document YAML file per Application to the output directory so
CI can validate exactly what gets deployed. Sources from other repositories
(workloads that live in their own repo) are skipped; those repos validate
their own manifests.

    scripts/render-apps.py [--out rendered] [--kube-version 1.34.1]
"""
import argparse
import fnmatch
import pathlib
import re
import subprocess
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
APPS_DIR = ROOT / "Kubernetes" / "argocd" / "apps"
THIS_REPO = "github.com/jstrebeck/Homelab-Configuration"


def is_this_repo(url):
    return THIS_REPO in url.removesuffix(".git")


def expand_braces(pattern):
    """'{a.yaml,b.yaml}' -> ['a.yaml', 'b.yaml'] (Argo CD's directory.include syntax)."""
    m = re.search(r"\{([^{}]*)\}", pattern)
    if not m:
        return [pattern]
    head, tail = pattern[: m.start()], pattern[m.end():]
    return [p for opt in m.group(1).split(",") for p in expand_braces(head + opt + tail)]


def run(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd)}\n{result.stderr}")
    return result.stdout


def render_helm(app, source, value_refs, kube_version):
    name = source.get("helm", {}).get("releaseName", app["metadata"]["name"])
    repo, chart = source["repoURL"], source["chart"]
    if repo.startswith("http"):
        cmd = ["helm", "template", name, chart, "--repo", repo]
    else:  # OCI registry, as Argo CD writes it (no scheme)
        cmd = ["helm", "template", name, f"oci://{repo}/{chart}"]
    cmd += [
        "--version", source["targetRevision"],
        "--namespace", app["spec"]["destination"]["namespace"],
        "--kube-version", kube_version,
        "--include-crds",
    ]
    for vf in source.get("helm", {}).get("valueFiles", []):
        ref, _, rel = vf.partition("/")
        if not ref.startswith("$") or ref[1:] not in value_refs:
            raise RuntimeError(f"unsupported valueFile {vf}")
        path = ROOT / rel
        if not path.exists():
            raise RuntimeError(f"valueFile {vf} does not exist")
        cmd += ["-f", str(path)]
    return run(cmd)


def render_git(source):
    path = ROOT / source["path"]
    if not path.is_dir():
        raise RuntimeError(f"path {source['path']} does not exist")
    if (path / "kustomization.yaml").exists():
        return run(["kubectl", "kustomize", str(path)])
    include = source.get("directory", {}).get("include", "*.yaml")
    patterns = expand_braces(include)
    files = sorted(
        f for f in path.iterdir()
        if f.suffix in (".yaml", ".yml") and any(fnmatch.fnmatch(f.name, p) for p in patterns)
    )
    if not files:
        raise RuntimeError(f"no manifests in {source['path']} match {include}")
    return "\n---\n".join(f.read_text() for f in files)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="rendered")
    parser.add_argument("--kube-version", default="1.34.1")
    args = parser.parse_args()

    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    failures = 0

    for file in sorted(APPS_DIR.glob("*.yaml")):
        for doc in yaml.safe_load_all(file.read_text()):
            if not doc or doc.get("kind") != "Application":
                continue
            name = doc["metadata"]["name"]
            spec = doc["spec"]
            sources = spec.get("sources") or [spec["source"]]
            value_refs = {s["ref"] for s in sources if "ref" in s}
            rendered = []
            try:
                for s in sources:
                    if "ref" in s:
                        continue
                    if "chart" in s:
                        rendered.append(render_helm(doc, s, value_refs, args.kube_version))
                    elif is_this_repo(s["repoURL"]):
                        rendered.append(render_git(s))
                    else:
                        print(f"skip  {name}: source in {s['repoURL']}")
            except RuntimeError as e:
                failures += 1
                print(f"FAIL  {name}: {e}", file=sys.stderr)
                continue
            if rendered:
                (out / f"{name}.yaml").write_text("\n---\n".join(rendered))
                print(f"ok    {name}")

    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
