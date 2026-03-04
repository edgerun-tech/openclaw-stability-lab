#!/usr/bin/env python3
import argparse
import datetime as dt
import json
import os
import sqlite3
import subprocess
import sys
import uuid
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE_DIR = ROOT / "orchestrator" / "state"
DB_PATH = STATE_DIR / "controlplane.db"
BOARD_PATH = ROOT / "docs" / "findings" / "control-plane-board.md"
PR_INTEL_PATH = ROOT / "orchestrator" / "state" / "pr-intel.json"


def worker_alias(worker_id: str) -> str:
    adjectives = ["amber","brisk","calm","crisp","daring","ember","gentle","keen","lucky","mellow","nova","quiet","rapid","solar","tidal","vivid"]
    animals = ["otter","falcon","lynx","heron","fox","orca","kite","panda","wolf","finch","badger","ibis","raven","tiger","koala","yak"]
    h = hashlib.sha1(worker_id.encode("utf8")).digest()
    return f"{adjectives[h[0] % len(adjectives)]}-{animals[h[1] % len(animals)]}-{h[2] % 100:02d}"

def display_path(path: str | None) -> str:
    if not path:
        return ""
    # avoid leaking host filesystem layout/IP-like identifiers
    parts = str(path).strip().split("/")
    if len(parts) >= 2:
        return "/".join(parts[-2:])
    return parts[-1]

def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def load_pr_intel() -> dict:
    if PR_INTEL_PATH.exists():
        try:
            return json.loads(PR_INTEL_PATH.read_text(encoding="utf8"))
        except Exception:
            return {}
    return {}


def connect() -> sqlite3.Connection:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS workers (
          id TEXT PRIMARY KEY,
          profiles_json TEXT NOT NULL,
          last_seen TEXT NOT NULL,
          status TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS jobs (
          id TEXT PRIMARY KEY,
          source_repo TEXT NOT NULL,
          issue_number INTEGER NOT NULL,
          title TEXT,
          profile TEXT NOT NULL,
          status TEXT NOT NULL,
          priority INTEGER NOT NULL DEFAULT 1,
          lease_owner TEXT,
          lease_until TEXT,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          UNIQUE(source_repo, issue_number, profile)
        );

        CREATE TABLE IF NOT EXISTS results (
          id TEXT PRIMARY KEY,
          job_id TEXT NOT NULL,
          runner_id TEXT NOT NULL,
          verdict TEXT NOT NULL,
          commit_sha TEXT,
          report_path TEXT,
          logs_path TEXT,
          created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS events (
          id TEXT PRIMARY KEY,
          event_type TEXT NOT NULL,
          payload_json TEXT NOT NULL,
          created_at TEXT NOT NULL
        );
        """
    )
    conn.commit()


def emit_event(conn: sqlite3.Connection, event_type: str, payload: dict) -> None:
    conn.execute(
        "INSERT INTO events (id,event_type,payload_json,created_at) VALUES (?,?,?,?)",
        (str(uuid.uuid4()), event_type, json.dumps(payload), now_iso()),
    )


def classify_profile(title: str, body: str) -> str:
    t = f"{title}\n{body or ''}".lower()
    if any(k in t for k in ["feishu", "whatsapp", "slack", "discord", "queued", "duplicate", "drops replies"]):
        return "channel-delivery"
    if any(k in t for k in ["gateway", "restart", "disconnect", "stale-socket", "launchctl"]):
        return "gateway-lifecycle"
    return "protocol-transport"


def gh_json(cmd: str):
    out = subprocess.check_output(cmd, shell=True, text=True)
    return json.loads(out)


def ingest_openclaw(conn: sqlite3.Connection, limit: int) -> None:
    data = gh_json("gh api --paginate repos/openclaw/openclaw/issues?state=open&per_page=100")
    count = 0
    for item in data:
        if "pull_request" in item:
            continue
        profile = classify_profile(item.get("title", ""), item.get("body") or "")
        now = now_iso()
        conn.execute(
            """
            INSERT INTO jobs (id,source_repo,issue_number,title,profile,status,priority,created_at,updated_at)
            VALUES (?,?,?,?,?,'queued',1,?,?)
            ON CONFLICT(source_repo,issue_number,profile) DO UPDATE SET
              title=excluded.title,
              updated_at=excluded.updated_at
            """,
            (
                f"issue-{item['number']}-{profile}",
                "openclaw/openclaw",
                item["number"],
                item.get("title", ""),
                profile,
                now,
                now,
            ),
        )
        count += 1
        if limit and count >= limit:
            break
    emit_event(conn, "ingest.completed", {"count": count})
    conn.commit()
    print(f"ingested {count} issues")


def register_worker(conn: sqlite3.Connection, worker_id: str, profiles: list[str]) -> None:
    now = now_iso()
    conn.execute(
        """
        INSERT INTO workers (id,profiles_json,last_seen,status)
        VALUES (?,?,?,?)
        ON CONFLICT(id) DO UPDATE SET profiles_json=excluded.profiles_json,last_seen=excluded.last_seen,status='online'
        """,
        (worker_id, json.dumps(profiles), now, "online"),
    )
    emit_event(conn, "worker.registered", {"worker": worker_id, "profiles": profiles})
    conn.commit()


def claim_job(conn: sqlite3.Connection, worker_id: str, lease_seconds: int) -> dict | None:
    row = conn.execute("SELECT profiles_json FROM workers WHERE id=?", (worker_id,)).fetchone()
    if not row:
        raise SystemExit(f"worker not registered: {worker_id}")
    profiles = json.loads(row["profiles_json"])
    if not profiles:
        return None

    placeholders = ",".join(["?"] * len(profiles))
    now = now_iso()
    job = conn.execute(
        f"""
        SELECT * FROM jobs
        WHERE status='queued' AND profile IN ({placeholders})
        ORDER BY priority DESC, updated_at ASC
        LIMIT 1
        """,
        profiles,
    ).fetchone()
    if not job:
        return None

    lease_until = (dt.datetime.now(dt.timezone.utc) + dt.timedelta(seconds=lease_seconds)).isoformat()
    conn.execute(
        "UPDATE jobs SET status='running', lease_owner=?, lease_until=?, updated_at=? WHERE id=?",
        (worker_id, lease_until, now, job["id"]),
    )
    emit_event(conn, "job.claimed", {"job": job["id"], "worker": worker_id})
    conn.commit()
    return dict(job)


def submit_result(
    conn: sqlite3.Connection,
    job_id: str,
    worker_id: str,
    verdict: str,
    commit_sha: str,
    report_path: str,
    logs_path: str,
) -> None:
    now = now_iso()
    conn.execute(
        "INSERT INTO results (id,job_id,runner_id,verdict,commit_sha,report_path,logs_path,created_at) VALUES (?,?,?,?,?,?,?,?)",
        (str(uuid.uuid4()), job_id, worker_id, verdict, commit_sha, report_path, logs_path, now),
    )
    new_status = "done" if verdict == "not-reproducible" else "failed"
    conn.execute(
        "UPDATE jobs SET status=?, updated_at=? WHERE id=?",
        (new_status, now, job_id),
    )
    emit_event(conn, "job.result", {"job": job_id, "worker": worker_id, "verdict": verdict})
    conn.commit()


def requeue_expired(conn: sqlite3.Connection) -> int:
    now = now_iso()
    rows = conn.execute("SELECT id FROM jobs WHERE status='running' AND lease_until < ?", (now,)).fetchall()
    for r in rows:
        conn.execute(
            "UPDATE jobs SET status='queued', lease_owner=NULL, lease_until=NULL, updated_at=? WHERE id=?",
            (now, r["id"]),
        )
        emit_event(conn, "job.requeued", {"job": r["id"]})
    conn.commit()
    return len(rows)


def render_board(conn: sqlite3.Connection) -> None:
    BOARD_PATH.parent.mkdir(parents=True, exist_ok=True)
    pr_intel = load_pr_intel()
    counts = conn.execute("SELECT status, count(*) c FROM jobs GROUP BY status").fetchall()
    by_status = {r["status"]: r["c"] for r in counts}
    workers = conn.execute("SELECT id, status, last_seen, profiles_json FROM workers ORDER BY last_seen DESC LIMIT 50").fetchall()
    latest = conn.execute(
        """
        SELECT j.issue_number,j.profile,j.status,r.verdict,r.commit_sha,r.created_at,r.runner_id,r.report_path,r.logs_path
        FROM jobs j
        LEFT JOIN results r ON r.job_id=j.id
        ORDER BY COALESCE(r.created_at,j.updated_at) DESC
        LIMIT 80
        """
    ).fetchall()

    generated = now_iso()
    lines = [
        "# Stability Lab Control Plane Board",
        "",
        f"Generated: {generated}",
        "",
        "## Job status",
        "",
        "| Status | Count |",
        "|---|---:|",
    ]
    for s in ["queued", "running", "done", "failed", "needs-info"]:
        lines.append(f"| {s} | {by_status.get(s,0)} |")

    lines += ["", "## Workers", "", "| Worker | Status | Last Seen | Profiles |", "|---|---|---|---|"]
    for w in workers:
        lines.append(f"| {worker_alias(w['id'])} | {w['status']} | {w['last_seen']} | {w['profiles_json']} |")

    lines += ["", "## Recent results", "", "| Issue | Profile | Job Status | Verdict | Runner | Commit | When | Report | Logs |", "|---:|---|---|---|---|---|---|---|---|"]
    for r in latest:
        lines.append(
            f"| {r['issue_number']} | {r['profile']} | {r['status']} | {r['verdict'] or ''} | {worker_alias(r['runner_id'] or 'unknown')} | {(r['commit_sha'] or '')[:10]} | {r['created_at'] or ''} | {display_path(r['report_path'])} | {display_path(r['logs_path'])} |"
        )

    lines += ["", "## PR intelligence", ""]
    if pr_intel:
        lines.append(f"Source repo: `{pr_intel.get('repo', 'unknown')}`")
        lines.append(f"Open PRs: **{pr_intel.get('openPulls', 0)}** | Open issues: **{pr_intel.get('openIssues', 0)}**")
        lines.append("")
        lines.append("### Top campaigns")
        lines.append("")
        lines.append("| Campaign | Category | Tier | Policy | Confidence | Issues |")
        lines.append("|---|---|---|---|---:|---|")
        for c in pr_intel.get("campaigns", [])[:10]:
            issues = ", ".join(f"#{n}" for n in c.get("issues", []))
            lines.append(f"| {c.get('campaignId','')} | {c.get('category','')} | {c.get('tier','')} | {c.get('policy','')} | {c.get('confidence',0)} | {issues} |")
    else:
        lines.append("No PR intelligence artifact found yet.")

    BOARD_PATH.write_text("\n".join(lines) + "\n", encoding="utf8")

    # Also emit a lightweight HTML dashboard so root URL isn't a directory listing.
    html_path = BOARD_PATH.parent / "index.html"
    html = [
        "<!doctype html>",
        "<html class='dark'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>",
        "<title>OpenClaw Stability Dashboard</title>",
        "<script src='https://cdn.tailwindcss.com'></script>",
        "</head><body class='bg-zinc-950 text-zinc-100'>",
        "<div class='max-w-7xl mx-auto px-4 py-8'>",
        "<h1 class='text-2xl font-bold mb-2'>OpenClaw Stability Dashboard</h1>",
        f"<p class='text-zinc-400 mb-4'><b>Generated:</b> {generated}</p>",
        "<div class='grid grid-cols-2 md:grid-cols-5 gap-3 mb-8'>" + "".join([f"<div class='rounded-xl border border-zinc-800 bg-zinc-900 p-3'><div class='text-zinc-400 text-xs uppercase'>{k}</div><div class='text-2xl font-semibold'>{by_status.get(k,0)}</div></div>" for k in ["queued","running","done","failed","needs-info"]]) + "</div>",
        "<h2 class='text-xl font-semibold mb-2'>Workers</h2>",
        "<div class='overflow-x-auto mb-8'><table class='min-w-full text-sm border border-zinc-800'><thead class='bg-zinc-900'><tr><th class='p-2 text-left'>Worker</th><th class='p-2 text-left'>Status</th><th class='p-2 text-left'>Last Seen</th><th class='p-2 text-left'>Profiles</th></tr></thead><tbody>",
    ]
    for w in workers:
        html.append(f"<tr class='border-t border-zinc-800'><td class='p-2'>{worker_alias(w['id'])}</td><td class='p-2'>{w['status']}</td><td class='p-2'>{w['last_seen']}</td><td class='p-2'><code>{w['profiles_json']}</code></td></tr>")
    html += ["</tbody></table></div>", "<h2 class='text-xl font-semibold mb-2'>Recent Results</h2>", "<div class='overflow-x-auto'><table class='min-w-full text-sm border border-zinc-800'><thead class='bg-zinc-900'><tr><th class='p-2 text-left'>Issue</th><th class='p-2 text-left'>Profile</th><th class='p-2 text-left'>Status</th><th class='p-2 text-left'>Verdict</th><th class='p-2 text-left'>Runner</th><th class='p-2 text-left'>Commit</th><th class='p-2 text-left'>When</th><th class='p-2 text-left'>Report</th><th class='p-2 text-left'>Logs</th></tr></thead><tbody>"]
    for r in latest:
        html.append(f"<tr class='border-t border-zinc-800'><td class='p-2'>{r['issue_number']}</td><td class='p-2'>{r['profile']}</td><td class='p-2'>{r['status']}</td><td class='p-2'>{r['verdict'] or ''}</td><td class='p-2'>{worker_alias(r['runner_id'] or 'unknown')}</td><td class='p-2'>{(r['commit_sha'] or '')[:10]}</td><td class='p-2'>{r['created_at'] or ''}</td><td class='p-2'>{display_path(r['report_path'])}</td><td class='p-2'>{display_path(r['logs_path'])}</td></tr>")
    html += ["</tbody></table></div>"]

    html += ["<h2 class='text-xl font-semibold mt-8 mb-2'>PR Intelligence</h2>"]
    if pr_intel:
        html += [
            "<div class='grid grid-cols-1 md:grid-cols-2 gap-3 mb-4'>",
            f"<div class='rounded-xl border border-zinc-800 bg-zinc-900 p-3'><div class='text-zinc-400 text-xs uppercase'>Repo</div><div class='text-base font-semibold'>{pr_intel.get('repo','unknown')}</div></div>",
            f"<div class='rounded-xl border border-zinc-800 bg-zinc-900 p-3'><div class='text-zinc-400 text-xs uppercase'>Open PRs / Open Issues</div><div class='text-base font-semibold'>{pr_intel.get('openPulls',0)} / {pr_intel.get('openIssues',0)}</div></div>",
            "</div>",
            "<div class='overflow-x-auto'><table class='min-w-full text-sm border border-zinc-800'><thead class='bg-zinc-900'><tr><th class='p-2 text-left'>Campaign</th><th class='p-2 text-left'>Category</th><th class='p-2 text-left'>Tier</th><th class='p-2 text-left'>Policy</th><th class='p-2 text-left'>Confidence</th><th class='p-2 text-left'>Issues</th></tr></thead><tbody>",
        ]
        for c in pr_intel.get("campaigns", [])[:10]:
            issues = ", ".join(f"#{n}" for n in c.get("issues", []))
            html.append(f"<tr class='border-t border-zinc-800'><td class='p-2'>{c.get('campaignId','')}</td><td class='p-2'>{c.get('category','')}</td><td class='p-2'>{c.get('tier','')}</td><td class='p-2'>{c.get('policy','')}</td><td class='p-2'>{c.get('confidence',0)}</td><td class='p-2'>{issues}</td></tr>")
        html += ["</tbody></table></div>"]
    else:
        html += ["<p class='text-zinc-400'>No PR intelligence artifact found yet.</p>"]

    html += ["<p class='mt-6 text-zinc-400'><a class='underline' href='control-plane-board.md'>Markdown board</a> · <a class='underline' href='issue-crossref.md'>Issue cross-reference</a> · <a class='underline' href='pr-intel-board.md'>PR intel board</a></p>", "</div></body></html>"]
    html_path.write_text("\n".join(html), encoding="utf8")
    print(f"wrote {BOARD_PATH} and {html_path}")


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init-db")

    s = sub.add_parser("ingest-openclaw")
    s.add_argument("--limit", type=int, default=200)

    s = sub.add_parser("register-worker")
    s.add_argument("--worker", required=True)
    s.add_argument("--profiles", required=True, help="comma-separated")

    s = sub.add_parser("claim-job")
    s.add_argument("--worker", required=True)
    s.add_argument("--lease-seconds", type=int, default=1800)

    s = sub.add_parser("submit-result")
    s.add_argument("--job-id", required=True)
    s.add_argument("--worker", required=True)
    s.add_argument("--verdict", required=True)
    s.add_argument("--commit", default="")
    s.add_argument("--report", default="")
    s.add_argument("--logs", default="")

    sub.add_parser("requeue-expired")
    sub.add_parser("render-board")

    args = p.parse_args()
    conn = connect()
    init_db(conn)

    if args.cmd == "init-db":
        print(f"db ready: {DB_PATH}")
    elif args.cmd == "ingest-openclaw":
        ingest_openclaw(conn, args.limit)
    elif args.cmd == "register-worker":
        register_worker(conn, args.worker, [p.strip() for p in args.profiles.split(",") if p.strip()])
    elif args.cmd == "claim-job":
        job = claim_job(conn, args.worker, args.lease_seconds)
        print(json.dumps(job or {}, indent=2))
    elif args.cmd == "submit-result":
        submit_result(conn, args.job_id, args.worker, args.verdict, args.commit, args.report, args.logs)
        print("ok")
    elif args.cmd == "requeue-expired":
        n = requeue_expired(conn)
        print(f"requeued {n}")
    elif args.cmd == "render-board":
        render_board(conn)


if __name__ == "__main__":
    main()
