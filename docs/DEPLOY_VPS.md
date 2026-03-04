# VPS Deployment (Control Plane Only)

Recommended topology:

- VPS runs control plane + API + dashboard
- Workers run on separate machines and connect via `CONTROL_PLANE_URL`

## Services on control-plane host

- `openclaw-stability-controlplane.service` (requeue/render tick)
- `openclaw-stability-api.service` (HTTP API, default `127.0.0.1:8091`)
- `openclaw-stability-dashboard.service` (static dashboard, default `127.0.0.1:8088`)

## Caddy routes

- `openclaw.edgerun.tech/` -> dashboard (`127.0.0.1:8088`)
- `openclaw.edgerun.tech/api/*` -> API (`127.0.0.1:8091`)

## Worker env

```bash
export CONTROL_PLANE_URL=https://openclaw.edgerun.tech/api
```
