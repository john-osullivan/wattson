# Reference — Olares and Vault Runtime

## 1. Olares as the Default Machine

Olares One is the primary environment for:

- development;
- local inference;
- testing;
- eventual always-on WATTSON execution.

This avoids dependence on one laptop being open and keeps the project accessible through a browser.

---

## 2. Development Surfaces

### Code Server

Use as the normal browser IDE:

- direct file editing;
- search;
- Git;
- extensions;
- tests;
- integrated terminal.

### OpenCode

Use as a coding agent operating against the same repository.

The repository should live in a UserData location visible to both applications, for example:

```text
Home/Code/wattson
```

Olares applications are sandboxed and do not automatically share arbitrary files. Each application needs explicit access to required Home directories through its Olares manifest.

### Control Hub

Use for runtime operations:

- inspect namespaces/pods;
- logs;
- container shell;
- storage;
- network;
- jobs;
- environment variables.

The Control Hub Terminal is a **host/root administration shell**, not the normal WATTSON development shell.

References:

- https://www.olares.com/docs/manual/olares/controlhub/
- https://www.olares.com/docs/manual/olares/controlhub/manage-container
- https://www.olares.com/docs/manual/olares/controlhub/terminal

---

## 3. Olares Application Packaging

WATTSON eventually becomes a private Olares Application Chart.

Conceptual structure:

```text
deploy/olares/wattson/
  Chart.yaml
  OlaresManifest.yaml
  values.yaml
  templates/
    deployment.yaml
    service.yaml
    ...
```

Current Olares application packaging extends Helm.

`OlaresManifest.yaml` defines:

- app metadata;
- entrances;
- AppData/UserData/AppCommon/external permissions;
- workload replica counts;
- system integration;
- accelerator declarations if needed.

The Kubernetes templates define actual containers, images, volumes, environment, commands, services, probes, etc.

Container images define which executables are installed.

References:

- https://www.olares.com/docs/developer/develop/
- https://www.olares.com/docs/developer/develop/package/chart
- https://www.olares.com/docs/developer/develop/package/manifest

---

## 4. Expected Runtime Dependencies

A WATTSON runtime image may contain:

- Node.js;
- Python;
- `jq`;
- `just` or application-specific task tooling as appropriate;
- Knap;
- WATTSON application code;
- either:
  - full Obsidian desktop + Obsidian CLI + virtual display dependencies, or
  - `obsidian-headless`.

Do not install both Sync mechanisms against the same vault.

WATTSON should generally not request direct GPU resources if it calls an already-running inference backend over the local Olares network.

---

# 5. Vault Runtime Interface

The rest of WATTSON should target a narrow conceptual interface.

Examples:

```text
readNote(path)
writeNote(path, content)
createNote(path, content)
moveNote(from, to)
listNotes()
search(query)
resolveLink(linkText, sourcePath?)
getLinks(path)
getBacklinks(path)
getTags(path?)
getTasks(scope?)
getTodayDailyNote()
```

Not every method must exist at first.

The interface prevents the full-Obsidian experiment from becoming a system-wide dependency before it is proven.

---

# 6. Option A — Full Obsidian Runtime

## Shape

```text
WATTSON app/container
  ├── virtual X display
  ├── Obsidian desktop
  ├── Obsidian Sync
  ├── `obsidian` CLI
  ├── WATTSON worker
  └── Knap
```

Obsidian CLI currently requires a running desktop application.

Reference:
https://obsidian.md/help/cli

## Potential leverage

The CLI currently exposes operations including:

- today's Daily Note;
- note creation;
- templates;
- property operations;
- tags/counts;
- tasks;
- search;
- links;
- backlinks;
- unresolved links;
- orphan/dead-end analysis;
- move/rename;
- developer `eval`.

`obsidian eval` may provide a route to the running application's JavaScript API and MetadataCache where the predefined commands are insufficient.

## Why this could be valuable

It avoids gradually creating a second implementation of Obsidian vault semantics.

Examples:

- rename a canonical note and let Obsidian update links according to its settings;
- ask Obsidian which file a link resolves to;
- retrieve actual configured Daily Note behavior;
- query the same metadata interpretation seen by the user's Obsidian clients.

## Risks to validate

- Electron/Xvfb stability;
- resource cost;
- startup ordering;
- CLI registration in a container;
- profile/config persistence;
- Sync behavior over days;
- application updates;
- plugin behavior in a virtual display environment.

---

# 7. Option B — Obsidian Headless Sync

## Shape

```text
WATTSON app
  ├── `ob sync --continuous`
  ├── local vault directory
  ├── WATTSON vault library
  ├── WATTSON worker
  └── Knap
```

`obsidian-headless` is explicitly designed for agents/automation.

Reference:
https://obsidian.md/help/sync/headless

## Strength

Operational simplicity.

## Limitation

`ob` provides Sync operations, not the full `obsidian` CLI's graph and application semantics.

WATTSON must therefore own any additional Markdown parsing/indexing behavior it needs.

---

# 8. Phase-0 Selection Test

Build the smallest possible experimental runtime and evaluate full Obsidian first.

Test:

```text
start virtual display
start Obsidian
open test vault
configure Sync
run representative CLI commands
exercise eval
edit from phone
observe server
write/rename from server
observe phone
restart container
repeat
leave running for several days
```

Choose full Obsidian only if it is boringly stable.

Fallback to Headless Sync if operation feels fragile.

This is an intentionally reversible choice.

---

# 9. Runtime Inspection

For a deployed Olares WATTSON app:

1. Open Control Hub.
2. Navigate to WATTSON's namespace/workload/pod.
3. Open the relevant container.
4. Use the container shell or logs.

That shell sees the binaries actually installed in the container image.

For host-level Kubernetes debugging, use Control Hub's host terminal or SSH, but keep this separate from normal application operation.

---

# 10. Persistent Data

Keep application state explicit.

Likely persistent categories:

```text
vault/
state/
  wattson.sqlite
config/
  generated schemas or runtime configuration
logs/   (only if not using stdout/cluster logging)
```

Do not store durable vault data only in an ephemeral container layer.

If full Obsidian is used, its profile/config/credentials must also live on persistent storage.

---

# 11. Local Inference Connectivity

Treat the existing Qwen service as another Olares-hosted dependency.

WATTSON configuration should identify it through a model-provider endpoint rather than embedding deployment details.

For example:

```text
WATTSON_MODEL_PROVIDER=local
WATTSON_LOCAL_BASE_URL=...
WATTSON_LOCAL_MODEL=...
```

Exact Olares service/provider permissions should be defined from the actual installed inference application during implementation.
