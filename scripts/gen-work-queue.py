#!/usr/bin/env python3
import json,sys
src='manifests/issue-batches.json'
out='config/issues.generated.txt'
obj=json.load(open(src))
lines=[]
for profile,issues in obj.get('profiles',{}).items():
    for i in issues:
        lines.append(f"{i} {profile}")
open(out,'w').write("\n".join(lines)+"\n")
print(f"wrote {out} ({len(lines)} tasks)")
