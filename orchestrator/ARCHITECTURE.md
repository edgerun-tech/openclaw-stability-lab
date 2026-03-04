# Stability Lab Orchestrator Architecture

## Components

1. **GitHub Ingestor**
   - Pulls issues/PR metadata from GitHub API
   - Normalizes to work items (`issue`, `pr`, `check`)
   - Categorizes by profile (`channel-delivery`, `gateway-lifecycle`, `protocol-transport`, etc.)

2. **Scheduler**
   - Reads unassigned work items
   - Assigns jobs to runner pools/machines (labels/capabilities)
   - Emits assignments with lease/timeout

3. **Runner**
   - Executes profile harness on assigned target
   - Produces report + logs + commit SHA

4. **Result Ingestor**
   - Validates reports against schema
   - Updates work item status (`passed`, `failed`, `needs-info`)
   - Emits summary artifacts

5. **Evidence Publisher**
   - Produces issue-comment drafts (human-gated)
   - Stores reproducibility history

## Storage (v1)

- JSONL files in `orchestrator/state/`
  - `work-items.jsonl`
  - `assignments.jsonl`
  - `results.jsonl`

## Migration path (v2)

- Move state to SQLite/Postgres without changing interfaces.
