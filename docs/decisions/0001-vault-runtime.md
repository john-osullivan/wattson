# ADR 0001 — Vault Runtime: Full Obsidian in a Container

Status: **Accepted (provisional — pending Sync + multi-day stability)**
Date: 2026-09-22
Deciders: WATTSON Phase 0 spike

## Context

Milestone M0 requires choosing the server-side vault runtime before
substantial vault tooling is written (design:
`wattson-handoff/reference/03-olares-and-vault-runtime.md`):

- **Option A — Full Obsidian Runtime**: Obsidian Linux desktop in the WATTSON
  container under Xvfb; full `obsidian` CLI, live MetadataCache, `eval`.
- **Option B — Headless Sync**: official `obsidian-headless` (`ob`) for sync;
  WATTSON owns all vault semantics itself.

The decision rule was empirical: try A first; choose it only if boringly
stable; otherwise fall back to B. The choice is reversible because all
WATTSON code targets the narrow Vault Runtime interface.

## Evidence (spike, 2026-09-22)

Scaffold: `spike/obsidian/` (Dockerfile, entrypoint, test vault, noVNC).
Image: ubuntu:24.04 + Obsidian 1.13.7 .deb + Xvfb + x11vnc + noVNC.

| Check | Result |
|---|---|
| Image build (`.deb` route) | PASS — no missing Electron libs |
| App launch under Xvfb, vault auto-open | PASS — first-run dialog bypassed by pre-seeding `obsidian.json` in the profile volume (`{"cli":true,"vaults":{...}}`) |
| CLI: vaults / create / read / tags / links / backlinks / unresolved / tasks / properties / search / rename / move | PASS — all verified against fixture vault |
| `eval` (arbitrary JS vs live app) | PASS — `app.metadataCache`, `app.vault` reachable |
| Daily Note ops (`daily:path/read/append`) | PASS — requires vault config `.obsidian/daily-notes.json` (`{"folder":"Daily Notes","format":"YYYY-MM-DD"}`) |
| noVNC browser view | PASS — `https://1f47cd9b0.app.on.bigrock.dev/__preview/6080/vnc.html` (nginx strips the `/__preview/6080/` prefix; bare websockify 404s behind the pod proxy) |
| Container restart survival | PASS — profile persists in named volume; fixed an Xvfb `/tmp/.X99-lock` stale-lock segfault in entrypoint |

## Decision

**Option A — Full Obsidian Runtime** for Phase 1.

Rationale: every operation in the Phase 0 checklist worked on first pass
after mechanical fixes; the CLI plus `eval` covers the entire vault
operations surface WATTSON needs (link resolution, Daily Note semantics,
rename-with-link-update, metadata as the user's clients see it). Option B
would require WATTSON to reimplement exactly this semantics layer.

## Conditions and mitigations (must hold / do)

1. **Sync not yet proven on the server.** Desktop Sync in a container is
   untested (needs user Obsidian credentials). This is the open gate on the
   ADR: if server-side desktop Sync is unstable, re-open the decision —
   possibly hybrid (Headless Sync for transport + full app for semantics,
   which the design permits since only one Sync mechanism may touch a vault
   at a time).
2. **Multi-day stability unproven.** Leave the spike (or successor) running
   through Phase 1; a crash loop or silent Sync stall re-opens the decision.
3. Operational rules captured from the spike:
   - docker builds on this pod need `--network=host` (bridge egress filtered);
   - Obsidian + CLI as root need `--no-sandbox`;
   - entrypoint must clear stale `/tmp/.X99-lock` before starting Xvfb;
   - pin the `.deb` version; the in-container update check fails (cosmetic);
   - pre-seed the profile volume so the vault opens without the trust dialog;
   - keep `.obsidian/daily-notes.json` in the vault or `daily:*` resolves to
     vault root.
4. 1.13.7 API drift: `metadataCache.getBacklinksForFile` returns
   `{"data":{}}` — use `resolvedLinks`; `getTags()` returns a tag→count map.
   Prefer CLI subcommands over `eval` where they exist; treat `eval` as the
   escape hatch.
5. The spike's noVNC/nginx prefix-strip setup is the pattern for any
   browser-visible surface behind the pod preview proxy.

## Consequences

- WATTSON Phase 1+ code targets the Vault Runtime interface implemented on
  top of the `obsidian` CLI (+ `eval` fallback), not on raw file parsing.
- The production OAC will carry the Obsidian image + profile/state/vault
  persistent volumes (skeleton already deployed at `deploy/olares/wattson/`).
- Inference connectivity for the app is settled separately: in-cluster
  `http://download-svc.llamacppqwen3827bggufv3-shared.svc.cluster.local:8090/v1`
  (model `unsloth/Qwen3.8-27B-GGUF:UD-Q4_K_XL`), already configured in the
  chart env.
