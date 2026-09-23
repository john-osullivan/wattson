# WATTSON — Olares Application Chart (Phase 0 skeleton)

Smallest possible private Olares app for WATTSON Phase 0
(`wattson-handoff/02-phased-implementation-plan.md`, "Olares application skeleton").

Proves, on this Olares host (1.12.6):

1. launches a test container — `alpine:3.20` heartbeat loop (one stdout line +
   one file write every 5 s);
2. persists application data — app `Data` volume (`drive/Data/wattson`) with the
   future layout `vault/ state/ config/`, heartbeat files in `state/`;
3. reaches the local inference backend — env-only wiring to the in-cluster
   service of `llamacppqwen3827bggufv3` (no model calls, no GPU requested);
4. exposes logs and a shell through Control Hub (pod Logs/Terminal) plus a
   web-terminal entrance on the desktop;
5. no user-facing WATTSON web UI, no GPU resources.

## Layout

| Path | Purpose |
|---|---|
| `Chart.yaml` / `OlaresManifest.yaml` / `values.yaml` | chart metadata, manifest (storage, env, workload, entrance), replica counts |
| `templates/wattson.yaml` | `wattson` Deployment: uid-1000 alpine heartbeat, `init-permissions` initContainer (non-recursive `chown` of `/data{,/vault,/state,/config}`), appData hostPath at `/data` |
| `templates/terminal.yaml` | headless-archetype web terminal (RBAC + `beclab/terminal:v0.0.8`) that execs into the `wattson` container; the app's one (visible, window) entrance. Runs with `--shell=sh` because the target container is alpine (no `bash`; the apiserver default shell `bash` exits 127) |

## Inference backend env (configure-only, no calls made)

| Var | Default | Notes |
|---|---|---|
| `WATTSON_MODEL_BASE_URL` | `http://download-svc.llamacppqwen3827bggufv3-shared.svc.cluster.local:8090/v1` | in-cluster route to the shared app `llamacppqwen3827bggufv3` (llama.cpp + Qwen3.8-27B, OpenAI-compatible `/v1`, Model Console `download-svc:8090`). Fallback (public entrance, only if in-cluster fails): `https://366ada1d.app.on.bigrock.dev/v1` |
| `WATTSON_MODEL_NAME` | `unsloth/Qwen3.8-27B-GGUF:UD-Q4_K_XL` | model name advertised by the backend |

Both are editable app env vars (`applyOnChange: true` → changing them in
Settings restarts the workload). The container prints them in every heartbeat
line so wiring is visible in logs; it never calls the endpoint.

## Deploy / upgrade loop (private app, source `upload`)

First deploy (already done for v0.0.1):

```bash
olares-cli chart lint   ./deploy/olares/wattson
olares-cli chart package ./deploy/olares/wattson        # -> wattson-<ver>.tgz
olares-cli market upload wattson-<ver>.tgz
olares-cli market install wattson -s upload --version <ver> --watch
```

Every re-deploy (chart exists → `upgrade`, never `install`):

```bash
# 1. edit chart, then bump the version TOGETHER (patch bump):
#    Chart.yaml version == OlaresManifest.yaml metadata.version
olares-cli chart lint ./deploy/olares/wattson
olares-cli chart package ./deploy/olares/wattson
olares-cli market upload wattson-<NEW>.tgz
olares-cli market upgrade wattson -s upload --version <NEW> --watch
olares-cli market status wattson -s upload
```

Teardown (removes the app; `--delete-data` also wipes `drive/Data/wattson`):

```bash
olares-cli market uninstall wattson --delete-data --watch
olares-cli market delete wattson --version <ver>
```

## Logs and shell

- **Control Hub → Applications → `wattson` → Pods** (namespace `wattson-app`):
  - **Logs**: pod row → `Logs` (container `wattson`) — heartbeat lines.
  - **Shell**: pod row → `Terminal` — interactive exec into the `wattson` container.
  - Same surface via CLI:
    `olares-cli cluster container logs wattson-app/<pod>/wattson`,
    `olares-cli cluster pod list -n wattson-app`.
  - Note: `olares-cli cluster pod exec` is gated at Olares ≥ 1.12.7; on this
    1.12.6 host use Control Hub Terminal or the desktop terminal below.
- **Desktop window**: `WATTSON Terminal` (visible entrance,
  `https://2a1f78fb.app.on.bigrock.dev`) — web terminal that execs into the
  `wattson` container (headless archetype).
- **Persisted data** browsable without exec:
  `olares-cli files ls drive/Data/wattson/state`
  (`heartbeat`, `heartbeat.log`, `restart-count`).

## Verified (2026-09-22, v0.0.1)

- `market status`: `running`; pods `wattson-*` 1/1, `terminal-*` 3/3 Running.
- Log excerpt (heartbeat, env wired):
  `[wattson] heartbeat seq=77 ts=2026-09-22T09:52:40Z model_base_url=http://download-svc.llamacppqwen3827bggufv3-shared.svc.cluster.local:8090/v1 model_name=unsloth/Qwen3.8-27B-GGUF:UD-Q4_K_XL`
- Persistence: `drive/Data/wattson/{vault,state,config}` created;
  `state/heartbeat` = `last_heartbeat=2026-09-22T09:52:45Z`;
  `state/restart-count` = `1` (increments per container start → proves
  persistence across restarts).
