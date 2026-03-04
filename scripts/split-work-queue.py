#!/usr/bin/env python3
import argparse,math
p=argparse.ArgumentParser()
p.add_argument('--input',default='config/issues.generated.txt')
p.add_argument('--shards',type=int,required=True)
p.add_argument('--index',type=int,required=True)
p.add_argument('--output',default='config/issues.shard.txt')
a=p.parse_args()
lines=[l.strip() for l in open(a.input) if l.strip() and not l.startswith('#')]
chunk=math.ceil(len(lines)/a.shards) if a.shards>0 else len(lines)
start=a.index*chunk
end=min(len(lines),start+chunk)
sel=lines[start:end]
open(a.output,'w').write("\n".join(sel)+("\n" if sel else ""))
print(f"wrote {a.output} with {len(sel)} tasks from {len(lines)} total")
