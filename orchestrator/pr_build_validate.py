#!/usr/bin/env python3
"""PR build + analysis pipeline.

Indexes PR diffs/references and (optionally) runs lint/type/build on checked out PR heads.

Usage:
  python orchestrator/pr_build_validate.py --repo openclaw/openclaw --limit 5 --out orchestrator/state/pr-build-report.json
  python orchestrator/pr_build_validate.py --repo openclaw/openclaw --limit 3 --repo-path /path/to/openclaw --out orchestrator/state/pr-build-report.json
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any


def run(cmd: str, cwd: str | None = None, timeout: int = 1200) -> dict[str, Any]:
    p = subprocess.run(cmd, shell=True, cwd=cwd, text=True, capture_output=True, timeout=timeout)
    return {"cmd": cmd, "code": p.returncode, "stdout": p.stdout, "stderr": p.stderr}


def gh_json(path: str) -> Any:
    return json.loads(subprocess.check_output(f"gh api {path}", shell=True, text=True))


def detect_language(path: str) -> str:
    p = path.lower()
    if p.endswith(".ts") or p.endswith(".tsx"):
        return "typescript"
    if p.endswith(".js") or p.endswith(".jsx"):
        return "javascript"
    if p.endswith(".py"):
        return "python"
    if p.endswith(".go"):
        return "go"
    if p.endswith(".rs"):
        return "rust"
    if p.endswith(".md"):
        return "markdown"
    return "other"


def extract_refs_from_patch(patch: str) -> list[str]:
    if not patch:
        return []
    refs = set()
    refs.update(re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*\s*\(", patch))
    refs.update(re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*\s*:", patch))
    clean = sorted({r.rstrip("(:").strip() for r in refs if len(r.strip()) > 2})
    return clean[:25]


def parse_script_counts(text: str) -> dict[str, int]:
    low = text.lower()
    return {
        "errors": len(re.findall(r"\berror\b", low)),
        "warnings": len(re.findall(r"\bwarning\b", low)),
        "typescriptErrors": len(re.findall(r"ts\d{3,5}", text)),
        "eslintProblems": len(re.findall(r"eslint", low)),
    }


def choose_package_manager(repo_path: Path) -> str:
    if (repo_path / "pnpm-lock.yaml").exists():
        return "pnpm"
    if (repo_path / "yarn.lock").exists():
        return "yarn"
    return "npm"


def read_package_scripts(repo_path: Path) -> dict[str, str]:
    pkg = repo_path / "package.json"
    if not pkg.exists():
        return {}
    data = json.loads(pkg.read_text(encoding="utf8"))
    return data.get("scripts", {}) or {}


def run_repo_checks(repo_path: Path) -> dict[str, Any]:
    mgr = choose_package_manager(repo_path)
    scripts = read_package_scripts(repo_path)
    out: dict[str, Any] = {"manager": mgr, "scripts": list(scripts.keys()), "runs": []}

    if not scripts:
        out["skipped"] = "no-package-scripts"
        return out

    install_cmd = {"pnpm": "pnpm install --frozen-lockfile", "yarn": "yarn install --frozen-lockfile", "npm": "npm ci"}[mgr]
    out["runs"].append(run(install_cmd, cwd=str(repo_path), timeout=1800))

    for key in ["lint", "typecheck", "build", "test"]:
        if key not in scripts:
            continue
        cmd = {"pnpm": f"pnpm run {key}", "yarn": f"yarn {key}", "npm": f"npm run {key}"}[mgr]
        res = run(cmd, cwd=str(repo_path), timeout=2400)
        merged = (res.get("stdout", "") + "\n" + res.get("stderr", ""))[:120000]
        res["counts"] = parse_script_counts(merged)
        res["outputPreview"] = merged[-2000:]
        out["runs"].append(res)

    return out


def checkout_pr(repo_path: Path, pr_number: int) -> dict[str, Any]:
    return run(f"git fetch origin pull/{pr_number}/head:pr-{pr_number} && git checkout pr-{pr_number}", cwd=str(repo_path), timeout=600)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default="openclaw/openclaw")
    ap.add_argument("--limit", type=int, default=5)
    ap.add_argument("--repo-path", default="")
    ap.add_argument("--out", default="orchestrator/state/pr-build-report.json")
    args = ap.parse_args()

    pulls = gh_json(f"repos/{args.repo}/pulls?state=open&per_page=100")[: args.limit]
    report: dict[str, Any] = {"repo": args.repo, "limit": args.limit, "pullRequests": []}

    repo_path = Path(args.repo_path) if args.repo_path else None

    for p in pulls:
        num = p["number"]
        files = gh_json(f"repos/{args.repo}/pulls/{num}/files?per_page=100")
        lang_counts = Counter(detect_language(f.get("filename", "")) for f in files)
        refs = []
        for f in files:
            refs.extend(extract_refs_from_patch(f.get("patch", "") or ""))

        pr_entry: dict[str, Any] = {
            "number": num,
            "title": p.get("title", ""),
            "headSha": p.get("head", {}).get("sha", ""),
            "author": (p.get("user") or {}).get("login", ""),
            "changedFiles": len(files),
            "languageBreakdown": dict(lang_counts),
            "topCodeReferences": sorted(set(refs))[:40],
            "diffSummary": [
                {
                    "file": f.get("filename", ""),
                    "additions": f.get("additions", 0),
                    "deletions": f.get("deletions", 0),
                    "changes": f.get("changes", 0),
                    "status": f.get("status", ""),
                }
                for f in files[:40]
            ],
            "checks": {"mode": "diff-only", "runs": []},
        }

        if repo_path:
            co = checkout_pr(repo_path, num)
            if co["code"] == 0:
                checks = run_repo_checks(repo_path)
                pr_entry["checks"] = {"mode": "full", **checks}
            else:
                pr_entry["checks"] = {"mode": "checkout-failed", "error": co.get("stderr", "")[:600]}

        report["pullRequests"].append(pr_entry)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf8")

    md = [
        "# PR Build + Analysis Report",
        "",
        f"Repo: `{report['repo']}`",
        "",
        "| PR | Files | Languages | Check Mode |",
        "|---:|---:|---|---|",
    ]
    for pr in report["pullRequests"]:
        langs = ", ".join(f"{k}:{v}" for k, v in sorted(pr["languageBreakdown"].items(), key=lambda x: x[1], reverse=True)[:5])
        md.append(f"| {pr['number']} | {pr['changedFiles']} | {langs} | {pr['checks'].get('mode','diff-only')} |")

    md_path = out.parent.parent / "docs" / "findings" / "pr-build-report.md"
    # out parent is orchestrator/state, so go back to repo root
    repo_root = out.parent.parent.parent
    real_md = repo_root / "docs" / "findings" / "pr-build-report.md"
    real_md.parent.mkdir(parents=True, exist_ok=True)
    real_md.write_text("\n".join(md) + "\n", encoding="utf8")

    print(f"wrote {out}")
    print(f"wrote {real_md}")


if __name__ == "__main__":
    main()
