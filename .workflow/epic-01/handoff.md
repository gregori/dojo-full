# Handoff — Epic 01: Infrastructure & CD Pipeline

## Current Status
**All pipelines working, alembic initialized, database stamped at `f5889d99aeae`**
**Traefik ingress deployed, NodePorts 30737/30874 open in OCI security list**
**Terraform state synced to actual instance (64.181.185.18), lifecycle safeguard added**

## What Was Done

### Problem
The `cd-migrations.yml` workflow existed but could never work because:
1. `alembic/versions/` directory was empty — only had `__pycache__`
2. `.dockerignore` excluded `__pycache__` and `*.pyc`, so Docker didn't create `versions/` in the image
3. No migration files existed to run
4. Database had 13 tables (created by SQLAlchemy `create_all()`) but alembic had no tracking

### Fix
| Step | Detail |
|------|--------|
| `.gitkeep` | Created in `alembic/versions/` to preserve empty directory in Docker |
| Initial migration | `alembic revision --autogenerate -m "initial"` inside pod — produced empty migration (DB already matches models) |
| Database stamp | `alembic stamp f5889d99aeae` — marks current DB state as at head |
| Lint fix | Ruff found 5 errors (D415, W291, I001, F401×2) — all fixed in migration file |
| CI/CD | Commit `c6f224b` pushed → CI Backend ✅ → CD Deploy Backend ✅ → pods restarted |

### Pipeline Testing (cd-migrations.yml)
| Command | Result |
|---------|--------|
| `alembic current` | ✅ success → `f5889d99aeae (head)` |
| `alembic history` | ✅ success → `<base> -> f5889d99aeae (head), Initial migration.` |
| `alembic upgrade head` | ✅ success (no-op, DB already at head) |

### Pipeline workflow
The `cd-migrations.yml` workflow uses `appleboy/ssh-action@v1` to SSH into the k3s node and run `sudo k3s kubectl -n dojo exec deploy/dojo-backend -- alembic <command>`. It's triggered manually via `workflow_dispatch` with 4 options: `upgrade head`, `downgrade -1`, `current`, `history`.

### Relevant Files
- `.github/workflows/cd-migrations.yml` — the pipeline itself
- `dojo-app/backend/alembic/versions/.gitkeep` — preserves versions dir in Docker
- `dojo-app/backend/alembic/versions/f5889d99aeae_initial.py` — initial (empty) baseline migration
- `dojo-app/backend/.dockerignore` — excludes `__pycache__`/`*.pyc` (the reason versions/ wasn't copied)

## Key Decisions
- **Empty baseline migration**: Since DB already has all 13 tables matching the current models, `alembic revision --autogenerate` produces a no-op migration (`upgrade()` and `downgrade()` are both `pass`). This is correct — it serves as a baseline for future migrations
- **Manual stamp**: Database was stamped manually inside the pod. The stamp (`f5889d99aeae`) is stored in the `alembic_version` table in MySQL
- **`.gitkeep` over `.dockerignore` change**: Adding a `.dockerignore` exception for `versions/` would be fragile. `.gitkeep` is the standard approach to preserve empty directories in Git and Docker

## Next Steps / Open Questions
- Future migrations: developer creates migration file locally, commits to git, CI/CD rebuilds image, then runs `cd-migrations.yml` with `upgrade head` to apply
- The pipeline assumes `deploy/dojo-backend` exists — works with any pod in the deployment
- No e2e tests for the pipeline itself beyond manual validation done here

## Commits
- `07ec5e4` — feat: add initial alembic migration and .gitkeep for versions dir (failed CI — lint)
- `c6f224b` — fix: lint errors in initial migration file (passed CI/CD)

## Cluster State
- Node: `dojo-k8s-node-vnic` (64.181.185.18) | ARM64 | k3s v1.29.14
- Private IP: 10.0.1.8 / Public IP: 64.181.185.18 (sa-saopaulo-1)
- Pods: 5/5 Running (dojo-backend×2, dojo-frontend×2, mysql×1)
- Traefik HTTP NodePort: 30737, HTTPS NodePort: 30874
- Access URL: `http://64.181.185.18.sslip.io:30737/`
- Deploy-k8s workflow: ✅ (via CI SSH key)
- Terraform Apply: ✅ (security list rules applied)

---

# Instance Re-creation & Terraform State Sync

## Problem
The k3s node instance was recreated (old IP 136.248.122.244 → new IP 64.181.185.18) with a CI-generated SSH key, leaving:
- Terraform state pointing to old instance OCID — all future plans would fail
- SSH access broken for local key — only CI (`secrets.OCI_SSH_PRIVATE_KEY`) can connect
- Missing `lifecycle.ignore_changes` for metadata — local vs CI SSH key drift would force instance recreation on every local `terraform apply`

## Changes
| File | Change |
|------|--------|
| `dojo-infra/terraform/environments/prod/terraform.tfstate` | Imported new instance OCID (`ocid1.instance.oc1...`), removed 3 stale instances from state |
| `dojo-infra/terraform/modules/k8s_node/main.tf` | Added `lifecycle { ignore_changes = [metadata] }` to prevent SSH key drift from forcing recreation |
| `dojo-infra/terraform/environments/prod/backend.tf` | Commented-out S3 backend replaced by local backend with migration instructions |
| `dojo-infra/k8s/ingress.yaml` | Replaced nginx-based single ingress with two Traefik Ingress resources |
| `.github/workflows/deploy-k8s.yml` | Triggered manually to apply ingress to new instance |

## Key Decisions
- `lifecycle.ignore_changes` on `metadata` prevents CI key vs local key differences from destroying/recreating the instance
- Local Terraform backend kept (state committed to git); OCI Object Storage migration documented in comments but blocked by missing S3 credentials
- CI SSH key (`secrets.OCI_SSH_PRIVATE_KEY`) is the only key that can access the instance; local access requires manual key addition via OCI console

## CI/CD State
- Terraform Apply: ✅ on push to `dojo-infra/terraform/**` (last run on commit 5af871d)
- Deploy to K8s: ✅ on push to `dojo-infra/k8s/**` or manual dispatch (last run returned all pods healthy)
- Secrets: `K8S_NODE_PUBLIC_IP` updated to `64.181.185.18`

## Open Issues
- Local SSH access broken (CI key only). Fix: add local SSH public key to instance via OCI console serial console, or update Terraform user_data to include both keys
- Port 30737 may not be accessible from certain networks — test from a different network or use `portcheck.ing` to verify
- Traefik NodePorts (30737/30874) were pinned via HelmChartConfig on the old cluster; if the new cluster has different ports, a HelmChartConfig manifest needs to be added to `dojo-infra/k8s/`

## Relevant Files
- `dojo-infra/terraform/modules/k8s_node/main.tf` — lifecycle.ignore_changes safeguard
- `dojo-infra/terraform/environments/prod/backend.tf` — local backend with S3 migration docs
- `dojo-infra/terraform/environments/prod/terraform.tfstate` — synced with actual instance
- `dojo-infra/k8s/ingress.yaml` — two Traefik Ingress resources
- `.workflow/epic-01/handoff.md` — this file

## Commits
- `6b9ce88` — feat: expose Traefik NodePorts in security list and create Traefik ingress resources
- `5af871d` — fix: sync Terraform state with actual instance and add lifecycle safeguard

---

# Squad Runtime Initialization — 2026-07-19

## What Was Done
- Ran `npx @gregori/orchestrated-squad@latest install --target codex --yes` from `D:\dojo-full`.
- Updated Codex agent configuration under `.codex/agents/` and installed/updated the `squad-*` workflow skills under `.agents/skills/`.
- Created/updated `.squad/config.yaml`; the default configuration has manual work-item publishing and confirmation enabled.

## Verification
- `npx @gregori/orchestrated-squad@latest doctor` passed all checks:
  - Node `v24.1.0`
  - Codex, Claude, OpenCode, Devin, and VS Code runtime assets
  - Project root `D:\dojo-full`

## Decisions
- Initialization was performed idempotently over the existing `.workflow/epic-01` state; no epic or application code was changed.

## Open Questions
- None.

## Next Action
- Use the appropriate `squad-*` workflow skill for the next planned feature or review.
