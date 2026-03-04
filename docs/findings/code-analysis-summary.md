# Code Analysis Summary

Repo: `edgerun-tech/openclaw-stability-lab`

## Finding counts

| Type | Count |
|---|---:|
| dead-code | 44 |

## Recent findings

| Type | Severity | Title | Evidence |
|---|---|---|---|
| dead-code | medium | Possibly dead function: Handler.do_GET | `{"file": "orchestrator/control_plane_api.py", "line": 25, "refCount": 0}` |
| dead-code | medium | Possibly dead function: Handler.do_POST | `{"file": "orchestrator/control_plane_api.py", "line": 31, "refCount": 0}` |
| dead-code | medium | Possibly dead function: main | `{"file": "orchestrator/control_plane_api.py", "line": 77, "refCount": 1}` |
| dead-code | medium | Possibly dead function: run | `{"file": "orchestrator/ingest_github.py", "line": 7, "refCount": 1}` |
| dead-code | medium | Possibly dead function: classify | `{"file": "orchestrator/ingest_github.py", "line": 11, "refCount": 1}` |
| dead-code | medium | Possibly dead function: main | `{"file": "orchestrator/ingest_github.py", "line": 22, "refCount": 1}` |
| dead-code | medium | Possibly dead function: pick_runner | `{"file": "orchestrator/schedule.py", "line": 12, "refCount": 1}` |
| dead-code | medium | Possibly dead function: main | `{"file": "orchestrator/schedule.py", "line": 18, "refCount": 1}` |
| dead-code | medium | Possibly dead function: conn | `{"file": "orchestrator/code_analysis.py", "line": 29, "refCount": 1}` |
| dead-code | medium | Possibly dead function: iter_code_files | `{"file": "orchestrator/code_analysis.py", "line": 74, "refCount": 1}` |
| dead-code | medium | Possibly dead function: lang_for | `{"file": "orchestrator/code_analysis.py", "line": 85, "refCount": 1}` |
| dead-code | medium | Possibly dead function: parse_python_symbols | `{"file": "orchestrator/code_analysis.py", "line": 93, "refCount": 1}` |
| dead-code | medium | Possibly dead function: parse_python_symbols.V._emit | `{"file": "orchestrator/code_analysis.py", "line": 103, "refCount": 0}` |
| dead-code | medium | Possibly dead function: parse_python_symbols.V.visit_ClassDef | `{"file": "orchestrator/code_analysis.py", "line": 118, "refCount": 0}` |
| dead-code | medium | Possibly dead function: parse_python_symbols.V.visit_FunctionDef | `{"file": "orchestrator/code_analysis.py", "line": 124, "refCount": 1}` |
| dead-code | medium | Possibly dead function: ingest_repo | `{"file": "orchestrator/code_analysis.py", "line": 143, "refCount": 1}` |
| dead-code | medium | Possibly dead function: analyze_dead | `{"file": "orchestrator/code_analysis.py", "line": 188, "refCount": 1}` |
| dead-code | medium | Possibly dead function: analyze_dup | `{"file": "orchestrator/code_analysis.py", "line": 210, "refCount": 1}` |
| dead-code | medium | Possibly dead function: render_summary | `{"file": "orchestrator/code_analysis.py", "line": 251, "refCount": 1}` |
| dead-code | medium | Possibly dead function: main | `{"file": "orchestrator/code_analysis.py", "line": 288, "refCount": 1}` |
| dead-code | medium | Possibly dead function: main | `{"file": "orchestrator/ingest_results.py", "line": 7, "refCount": 1}` |
| dead-code | medium | Possibly dead function: run | `{"file": "orchestrator/pr_intel.py", "line": 37, "refCount": 1}` |
| dead-code | medium | Possibly dead function: load_open_pulls | `{"file": "orchestrator/pr_intel.py", "line": 88, "refCount": 1}` |
| dead-code | medium | Possibly dead function: load_open_issues | `{"file": "orchestrator/pr_intel.py", "line": 106, "refCount": 1}` |
| dead-code | medium | Possibly dead function: related_prs | `{"file": "orchestrator/pr_intel.py", "line": 123, "refCount": 1}` |
| dead-code | medium | Possibly dead function: issue_candidates | `{"file": "orchestrator/pr_intel.py", "line": 154, "refCount": 1}` |
| dead-code | medium | Possibly dead function: issue_campaigns | `{"file": "orchestrator/pr_intel.py", "line": 192, "refCount": 1}` |
| dead-code | medium | Possibly dead function: main | `{"file": "orchestrator/pr_intel.py", "line": 226, "refCount": 1}` |
| dead-code | medium | Possibly dead function: priority_for_issue | `{"file": "orchestrator/control_plane.py", "line": 49, "refCount": 1}` |
| dead-code | medium | Possibly dead function: connect | `{"file": "orchestrator/control_plane.py", "line": 62, "refCount": 1}` |
