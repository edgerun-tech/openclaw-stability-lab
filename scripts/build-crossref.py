#!/usr/bin/env python3
import sqlite3
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
DB = BASE / "orchestrator" / "state" / "controlplane.db"
OUT = BASE / "docs" / "findings" / "issue-crossref.md"


def confidence(verdict: str, seen: int) -> str:
    if seen >= 2 and verdict in ("reproducible", "not-reproducible"):
        return "Tier 2"
    if seen >= 1:
        return "Tier 1"
    return "Tier 0"


def main():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row

    rows = conn.execute(
        """
        SELECT j.issue_number, j.profile, j.status,
               r.verdict, r.commit_sha, r.report_path, r.logs_path, r.created_at
        FROM jobs j
        LEFT JOIN results r ON r.job_id = j.id
        ORDER BY j.issue_number ASC, r.created_at DESC
        """
    ).fetchall()

    latest = {}
    counts = {}
    for r in rows:
        key = (r["issue_number"], r["profile"])
        counts[key] = counts.get(key, 0) + (1 if r["verdict"] else 0)
        if key not in latest:
            latest[key] = r

    lines = [
        "# Issue Cross-Reference Board",
        "",
        "| Issue | Profile | Job Status | Latest Verdict | Confidence | Commit | Report | Logs |",
        "|---:|---|---|---|---|---|---|---|",
    ]

    for key in sorted(latest.keys()):
        r = latest[key]
        seen = counts.get(key, 0)
        v = r["verdict"] or ""
        conf = confidence(v, seen)
        commit = (r["commit_sha"] or "")[:10]
        report = r["report_path"] or ""
        logs = r["logs_path"] or ""
        lines.append(
            f"| {r['issue_number']} | {r['profile']} | {r['status']} | {v} | {conf} | {commit} | {report} | {logs} |"
        )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines) + "\n", encoding="utf8")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
