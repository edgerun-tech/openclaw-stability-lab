#!/usr/bin/env python3
import json,sqlite3
from pathlib import Path

BASE=Path(__file__).resolve().parents[1]
DB=BASE/'orchestrator/state/controlplane.db'
OUT=BASE/'docs/findings/materialized-views.json'

conn=sqlite3.connect(DB)
conn.row_factory=sqlite3.Row

views={}
views['worker_capacity']=[dict(r) for r in conn.execute("""
  SELECT COALESCE(runner_id,'unknown') as runner,
         SUM(CASE WHEN verdict='reproducible' THEN 1 ELSE 0 END) as repro_count,
         SUM(CASE WHEN verdict='not-reproducible' THEN 1 ELSE 0 END) as nonrepro_count,
         COUNT(*) as total
  FROM results
  GROUP BY COALESCE(runner_id,'unknown')
  ORDER BY total DESC
""")]

views['issue_latest_status']=[dict(r) for r in conn.execute("""
  SELECT issue_number, profile, status,
         MAX(updated_at) as updated_at
  FROM jobs
  GROUP BY issue_number, profile, status
  ORDER BY updated_at DESC
  LIMIT 500
""")]

views['pr_tracks']=[]
tracks=BASE/'tracks'
if tracks.exists():
  for f in tracks.glob('pr-*/track.json'):
    try:
      views['pr_tracks'].append(json.loads(f.read_text()))
    except Exception:
      pass

OUT.write_text(json.dumps(views,indent=2),encoding='utf8')
print(f'wrote {OUT}')
