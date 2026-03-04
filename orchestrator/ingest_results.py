#!/usr/bin/env python3
import json,glob,os,datetime

REPORT_GLOB='reports/**/report.json'
OUT='orchestrator/state/results.jsonl'

def main():
    now=datetime.datetime.now(datetime.timezone.utc).isoformat()
    reports=glob.glob(REPORT_GLOB, recursive=True)
    with open(OUT,'w') as f:
        for p in reports:
            r=json.load(open(p))
            row={
              'workItemId': f"issue-{r.get('issue')}",
              'runner': os.uname().nodename,
              'repo': r.get('repo','openclaw/openclaw'),
              'commit': r.get('commit','unknown'),
              'profile': r.get('profile','unknown'),
              'verdict': r.get('verdict','needs-more-info'),
              'startedAt': r.get('startedAt',now),
              'endedAt': r.get('endedAt',now),
              'artifacts': r.get('artifacts',[]),
            }
            f.write(json.dumps(row)+"\n")
    print(f"wrote {OUT} ({len(reports)} results)")

if __name__=='__main__':
    main()
