#!/usr/bin/env python3
import json, subprocess, datetime, hashlib

OUT='orchestrator/state/work-items.jsonl'


def run(cmd):
    return subprocess.check_output(cmd, shell=True, text=True)


def classify(title, body):
    text=(title+' '+(body or '')).lower()
    if any(k in text for k in ['feishu','whatsapp','slack','discord','duplicate','drops replies']):
        return 'channel-delivery'
    if any(k in text for k in ['gateway','restart','disconnect','stale-socket','launchctl']):
        return 'gateway-lifecycle'
    if any(k in text for k in ['protocol','websocket','transport','function calling']):
        return 'protocol-transport'
    return 'protocol-transport'


def main():
    now=datetime.datetime.now(datetime.timezone.utc).isoformat()
    raw=run("gh api --paginate repos/openclaw/openclaw/issues?state=open&per_page=100")
    items=json.loads(raw)
    with open(OUT,'w') as f:
        for it in items:
            if 'pull_request' in it:
                continue
            profile=classify(it.get('title',''), it.get('body',''))
            wid=hashlib.sha1(f"issue:{it['number']}:{profile}".encode()).hexdigest()[:16]
            row={
                'id': wid,
                'kind':'issue',
                'source':'openclaw/openclaw',
                'number':it['number'],
                'title':it.get('title',''),
                'profile':profile,
                'status':'new',
                'priority':1,
                'labels':[l['name'] for l in it.get('labels',[])],
                'createdAt':now,
                'updatedAt':now,
            }
            f.write(json.dumps(row)+"\n")
    print(f"wrote {OUT}")

if __name__=='__main__':
    main()
