#!/usr/bin/env python3
"""Code analysis pipeline (phase 1): symbol index + dead code + duplicate code.

Usage:
  python orchestrator/code_analysis.py init-db
  python orchestrator/code_analysis.py ingest-repo --repo-path /path/to/repo --repo-name openclaw/openclaw
  python orchestrator/code_analysis.py analyze-dead --repo-name openclaw/openclaw
  python orchestrator/code_analysis.py analyze-dup --repo-name openclaw/openclaw
  python orchestrator/code_analysis.py render-summary --repo-name openclaw/openclaw
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "orchestrator" / "state"
DB = STATE / "analysis.db"
SUMMARY = ROOT / "docs" / "findings" / "code-analysis-summary.md"
JSON_OUT = STATE / "code-analysis.json"


def conn() -> sqlite3.Connection:
    STATE.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c


def init_db(c: sqlite3.Connection) -> None:
    c.executescript(
        """
        CREATE TABLE IF NOT EXISTS files (
          repo_name TEXT NOT NULL,
          path TEXT NOT NULL,
          language TEXT,
          sha1 TEXT,
          line_count INTEGER,
          PRIMARY KEY(repo_name, path)
        );

        CREATE TABLE IF NOT EXISTS symbols (
          repo_name TEXT NOT NULL,
          symbol_id TEXT PRIMARY KEY,
          file_path TEXT NOT NULL,
          kind TEXT NOT NULL,
          name TEXT NOT NULL,
          qualname TEXT NOT NULL,
          line_start INTEGER,
          line_end INTEGER,
          reference_count INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS findings (
          id TEXT PRIMARY KEY,
          repo_name TEXT NOT NULL,
          finding_type TEXT NOT NULL,
          severity TEXT NOT NULL,
          title TEXT NOT NULL,
          evidence_json TEXT NOT NULL,
          created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        """
    )
    c.commit()


def iter_code_files(repo_path: Path) -> Iterable[Path]:
    exts = {".py", ".ts", ".tsx", ".js", ".jsx"}
    for p in repo_path.rglob("*"):
        if not p.is_file():
            continue
        if any(part in {".git", "node_modules", "dist", "build", "coverage"} for part in p.parts):
            continue
        if p.suffix.lower() in exts:
            yield p


def lang_for(path: Path) -> str:
    if path.suffix == ".py":
        return "python"
    if path.suffix in {".ts", ".tsx"}:
        return "typescript"
    return "javascript"


def parse_python_symbols(src: str, rel: str) -> list[dict]:
    out = []
    try:
        tree = ast.parse(src)
    except Exception:
        return out

    class V(ast.NodeVisitor):
        stack: list[str] = []

        def _emit(self, kind: str, name: str, node: ast.AST):
            qual = ".".join(self.stack + [name]) if self.stack else name
            sid = hashlib.sha1(f"{rel}:{qual}:{kind}".encode()).hexdigest()[:20]
            out.append(
                {
                    "symbol_id": sid,
                    "file_path": rel,
                    "kind": kind,
                    "name": name,
                    "qualname": qual,
                    "line_start": getattr(node, "lineno", 0),
                    "line_end": getattr(node, "end_lineno", getattr(node, "lineno", 0)),
                }
            )

        def visit_ClassDef(self, node: ast.ClassDef):
            self._emit("class", node.name, node)
            self.stack.append(node.name)
            self.generic_visit(node)
            self.stack.pop()

        def visit_FunctionDef(self, node: ast.FunctionDef):
            self._emit("function", node.name, node)
            self.stack.append(node.name)
            self.generic_visit(node)
            self.stack.pop()

        visit_AsyncFunctionDef = visit_FunctionDef

    V().visit(tree)

    names = [n.id for n in ast.walk(tree) if isinstance(n, ast.Name)]
    freq = {}
    for n in names:
        freq[n] = freq.get(n, 0) + 1
    for s in out:
        s["reference_count"] = freq.get(s["name"], 0)
    return out


def ingest_repo(c: sqlite3.Connection, repo_name: str, repo_path: Path) -> None:
    init_db(c)
    c.execute("DELETE FROM files WHERE repo_name=?", (repo_name,))
    c.execute("DELETE FROM symbols WHERE repo_name=?", (repo_name,))

    file_count = 0
    sym_count = 0
    for p in iter_code_files(repo_path):
        rel = str(p.relative_to(repo_path))
        text = p.read_text(encoding="utf8", errors="ignore")
        sha = hashlib.sha1(text.encode("utf8", errors="ignore")).hexdigest()
        lines = text.count("\n") + 1
        c.execute(
            "INSERT OR REPLACE INTO files (repo_name,path,language,sha1,line_count) VALUES (?,?,?,?,?)",
            (repo_name, rel, lang_for(p), sha, lines),
        )
        file_count += 1

        if p.suffix == ".py":
            syms = parse_python_symbols(text, rel)
            for s in syms:
                c.execute(
                    """
                    INSERT OR REPLACE INTO symbols
                    (repo_name,symbol_id,file_path,kind,name,qualname,line_start,line_end,reference_count)
                    VALUES (?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        repo_name,
                        s["symbol_id"],
                        s["file_path"],
                        s["kind"],
                        s["name"],
                        s["qualname"],
                        s["line_start"],
                        s["line_end"],
                        s.get("reference_count", 0),
                    ),
                )
                sym_count += 1

    c.commit()
    print(json.dumps({"ingestedFiles": file_count, "ingestedSymbols": sym_count, "repo": repo_name}, indent=2))


def analyze_dead(c: sqlite3.Connection, repo_name: str) -> None:
    rows = c.execute(
        "SELECT * FROM symbols WHERE repo_name=? AND kind='function' AND reference_count <= 1 LIMIT 500",
        (repo_name,),
    ).fetchall()
    for r in rows:
        fid = hashlib.sha1(f"dead:{repo_name}:{r['symbol_id']}".encode()).hexdigest()[:20]
        c.execute(
            "INSERT OR REPLACE INTO findings (id,repo_name,finding_type,severity,title,evidence_json) VALUES (?,?,?,?,?,?)",
            (
                fid,
                repo_name,
                "dead-code",
                "medium",
                f"Possibly dead function: {r['qualname']}",
                json.dumps({"file": r["file_path"], "line": r["line_start"], "refCount": r["reference_count"]}),
            ),
        )
    c.commit()
    print(f"dead-code findings upserted: {len(rows)}")


def analyze_dup(c: sqlite3.Connection, repo_name: str, repo_path: Path, min_lines: int = 8) -> None:
    c.execute("DELETE FROM findings WHERE repo_name=? AND finding_type='duplicate-code'", (repo_name,))
    files = c.execute("SELECT path FROM files WHERE repo_name=?", (repo_name,)).fetchall()
    hashes: dict[str, list[dict]] = {}
    for f in files:
        path = f["path"]
        abs_path = repo_path / path
        if not abs_path.exists():
            continue
        content = abs_path.read_text(encoding="utf8", errors="ignore").splitlines()
        if len(content) < min_lines:
            continue
        for i in range(0, len(content) - min_lines + 1):
            window = "\n".join(content[i : i + min_lines]).strip()
            if not window:
                continue
            h = hashlib.sha1(window.encode()).hexdigest()[:16]
            hashes.setdefault(h, []).append({"file": path, "line": i + 1})

    count = 0
    for h, occ in hashes.items():
        files_set = {o["file"] for o in occ}
        if len(files_set) < 2:
            continue
        fid = hashlib.sha1(f"dup:{repo_name}:{h}".encode()).hexdigest()[:20]
        c.execute(
            "INSERT OR REPLACE INTO findings (id,repo_name,finding_type,severity,title,evidence_json) VALUES (?,?,?,?,?,?)",
            (
                fid,
                repo_name,
                "duplicate-code",
                "low",
                f"Duplicate code block in {len(files_set)} files",
                json.dumps({"hash": h, "occurrences": occ[:20]}),
            ),
        )
        count += 1
    c.commit()
    print(f"duplicate-code findings upserted: {count}")


def render_summary(c: sqlite3.Connection, repo_name: str) -> None:
    counts = c.execute(
        "SELECT finding_type, count(*) c FROM findings WHERE repo_name=? GROUP BY finding_type",
        (repo_name,),
    ).fetchall()
    by_type = {r["finding_type"]: r["c"] for r in counts}

    top = c.execute(
        "SELECT finding_type,severity,title,evidence_json FROM findings WHERE repo_name=? ORDER BY created_at DESC LIMIT 30",
        (repo_name,),
    ).fetchall()

    lines = [
        "# Code Analysis Summary",
        "",
        f"Repo: `{repo_name}`",
        "",
        "## Finding counts",
        "",
        "| Type | Count |",
        "|---|---:|",
    ]
    for k in sorted(by_type):
        lines.append(f"| {k} | {by_type[k]} |")

    lines += ["", "## Recent findings", "", "| Type | Severity | Title | Evidence |", "|---|---|---|---|"]
    for r in top:
        ev = r["evidence_json"].replace("|", "\\|")[:160]
        lines.append(f"| {r['finding_type']} | {r['severity']} | {r['title']} | `{ev}` |")

    SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY.write_text("\n".join(lines) + "\n")

    JSON_OUT.write_text(json.dumps({"repo": repo_name, "counts": by_type}, indent=2))
    print(f"wrote {SUMMARY} and {JSON_OUT}")


def main() -> None:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init-db")

    i = sub.add_parser("ingest-repo")
    i.add_argument("--repo-name", required=True)
    i.add_argument("--repo-path", required=True)

    d = sub.add_parser("analyze-dead")
    d.add_argument("--repo-name", required=True)

    u = sub.add_parser("analyze-dup")
    u.add_argument("--repo-name", required=True)
    u.add_argument("--repo-path", required=True)

    r = sub.add_parser("render-summary")
    r.add_argument("--repo-name", required=True)

    args = p.parse_args()
    c = conn()
    init_db(c)

    if args.cmd == "init-db":
        print(f"db ready: {DB}")
    elif args.cmd == "ingest-repo":
        ingest_repo(c, args.repo_name, Path(args.repo_path))
    elif args.cmd == "analyze-dead":
        analyze_dead(c, args.repo_name)
    elif args.cmd == "analyze-dup":
        analyze_dup(c, args.repo_name, Path(args.repo_path))
    elif args.cmd == "render-summary":
        render_summary(c, args.repo_name)


if __name__ == "__main__":
    main()
