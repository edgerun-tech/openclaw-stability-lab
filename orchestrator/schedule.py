#!/usr/bin/env python3
import json, datetime, os

INP='orchestrator/state/work-items.jsonl'
OUT='orchestrator/state/assignments.jsonl'
RUNNERS=[
  {'name':'desktop-10.13.37.2','labels':['linux','stability-lab','heavy']},
  {'name':'local-default','labels':['linux','stability-lab','light']},
]


def pick_runner(profile):
    if profile in ('channel-delivery','gateway-lifecycle'):
        return RUNNERS[0]['name']
    return RUNNERS[1]['name']


def main(limit=50):
    now=datetime.datetime.now(datetime.timezone.utc).isoformat()
    rows=[json.loads(l) for l in open(INP) if l.strip()]
    count=0
    with open(OUT,'w') as f:
        for r in rows:
            if r['status']!='new':
                continue
            a={
              'workItemId': r['id'],
              'issue': r['number'],
              'profile': r['profile'],
              'runner': pick_runner(r['profile']),
              'leaseUntil': now,
              'status':'assigned',
              'createdAt': now,
            }
            f.write(json.dumps(a)+"\n")
            count+=1
            if count>=limit:
                break
    print(f"wrote {OUT} ({count} assignments)")

if __name__=='__main__':
    main()
