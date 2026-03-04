# Worker Onboarding Guide

This guide helps community contributors join the stability-lab worker pool safely.

## Prerequisites

- Linux/macOS machine (Linux recommended)
- Git + Python3 + Node 22 + pnpm
- A local clone of:
  - `edgerun-tech/openclaw-stability-lab`
  - `openclaw/openclaw`

## 1) Clone repos

```bash
git clone https://github.com/edgerun-tech/openclaw-stability-lab.git
cd openclaw-stability-lab

git clone https://github.com/openclaw/openclaw ../openclaw
```

## 2) Install OpenClaw deps

```bash
cd ../openclaw
corepack enable || true
corepack prepare pnpm@10.23.0 --activate || true
pnpm install --frozen-lockfile || pnpm install
```

## 3) Register worker + run loop

```bash
cd ../openclaw-stability-lab

export WORKER_ID=my-worker-001
export WORKER_PROFILES=channel-delivery,gateway-lifecycle,protocol-transport
export CORE_REPO=$(realpath ../openclaw)

./scripts/worker-loop.sh
```

## 4) Verify participation

- Check local `reports/` for new run outputs.
- Check `docs/findings/control-plane-board.md` for job status changes.

## Worker etiquette

- Do not auto-comment on upstream issues without human review.
- Keep logs/artifacts for traceability.
- Prefer reproducibility over speed.
