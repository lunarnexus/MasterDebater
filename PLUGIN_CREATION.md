# Connector Plugin Creation

## Purpose
Connector plugins are thin adapters that translate a connector config plus a prompt into a CLI argv list. Shared core handles validation, process execution, timeouts, and error formatting.

## Required module interface
Each plugin module must export:
- `NAME`: registry key
- `REQUIRED_FIELDS`: tuple of config keys the connector needs
- `build_argv(config, prompt)`: return a `list[str]`

Current implementations follow this shape in `connectors/hermes.py`, `connectors/pi.py`, and `connectors/opencode.py`.

## Plugin vs shared/core
Put in the plugin:
- connector-specific argv layout
- connector-specific flag names/order
- mapping config values to CLI flags

Put in shared/core:
- required-field validation
- subprocess execution
- timeout handling
- stdout/stderr/error normalization
- registry lookup and connector selection

## Security rules
- Build argv lists only.
- Do not build shell command strings.
- Do not call subprocess from a plugin.
- Do not read/write files from a plugin.
- Do not handle secrets in the plugin; accept already-loaded config values only.

## Registering a new plugin
1. Create `connectors/<name>.py` with the required interface.
2. Add it to the explicit connector registry used by core.
3. Add its required fields to config validation through `REQUIRED_FIELDS`.

## Documenting connector-specific config
Document each field near the connector entry in config docs:
- field name
- type
- whether required or optional
- meaning/default
- any CLI mapping notes

## Testing command construction
Use a fake CLI or a direct inline check:
- import the plugin module
- pass a minimal config dict and prompt
- assert the exact argv list
- if needed, point the registry at a dummy executable that prints argv

## Skeleton
```python
from __future__ import annotations

NAME = "example"
REQUIRED_FIELDS = ("model",)


def build_argv(config, prompt):
    return ["example-cli", "run", "--model", str(config["model"]), prompt]
```

## Checklist for Qwen / Codex / future harnesses
- [ ] choose a unique `NAME`
- [ ] define `REQUIRED_FIELDS`
- [ ] map config to argv only
- [ ] keep no shell, subprocess, or file I/O in the plugin
- [ ] register the module explicitly
- [ ] document connector-specific config fields
- [ ] add a construction test with a fake CLI or inline argv assertion
