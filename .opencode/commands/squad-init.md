---
description: Initialize orchestrated-squad state in the current project after confirming the intended runtime.
agent: planner
subtask: false
---


# Squad Init

Initialize the project for the Codex squad workflow.

1. Confirm the current directory is the intended project root.
2. Run `npx @gregori/orchestrated-squad@latest install --target codex --yes`.
3. Run `npx @gregori/orchestrated-squad@latest doctor`.
4. Report the created `.squad/config.yaml`, installed runtime artifacts and any failed doctor checks.

The installer is idempotent. Do not use `--no-init`: initialization must create
the local squad configuration and workflow directory.
