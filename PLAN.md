# Plan

## Goal

Replace MasterDebater's `cellos-acp` integration with a small synchronous connector-plugin system. MasterDebater should call local harness CLIs directly for one-shot prompt execution: one prompt in, one text response out, then append the response to the transcript.

Initial supported connectors:

- `hermes` — expected shape: `hermes --profile <profile> -z <prompt>`
- `pi` — expected shape: `pi --model <model> -p <prompt>`
- `opencode` — expected shape: `opencode run --model <model> <prompt>`

Qwen, Codex, and other harnesses are deferred until their exact one-shot CLI contracts are confirmed.

## Acceptance Criteria

- `master.debater.py` no longer depends on `cellos-acp`, `acpx`, or Orchestra for normal debate turns.
- Each debater selects a connector by name in `config.yaml`.
- Connector calls are synchronous and return plain response text or a useful error.
- Plugins are intentionally thin: harness-specific config fields plus argv construction only.
- Core/shared connector code owns validation, subprocess execution, timeout handling, verbose logging, and error normalization.
- Existing behavior is preserved:
  - load `config.yaml`
  - alternate debaters
  - build persona-specific prompts
  - pass the full transcript into each prompt
  - append transcript lines immediately
  - resume from an existing transcript
  - support `--turns`, `--mod`, and `--verbose`
- Connector failures are recorded as `[ERROR: ...]` transcript entries.
- README and example configs document the connector system.
- `PLUGIN_CREATION.md` explains how to add future thin plugins.
- A real smoke test completes 5-10 turns with at least one available connector, or records an external harness blocker clearly.

## In Scope

- Add a `connectors/` package with a shared runner and one thin file per connector.
- Add `hermes`, `pi`, and `opencode` connectors after verifying their local CLI contracts.
- Replace `call_cellos_acp(...)` with connector loading/calling.
- Update config schema and examples.
- Update README.
- Add `PLUGIN_CREATION.md`.
- Fix speaker-name resume parsing for names containing spaces/punctuation.
- Add safe output path validation so config cannot write outside `debates/`.
- Add focused tests or inline checks for connector command construction and core behavior.

## Out of Scope

- Orchestra integration.
- `cellos-acp` compatibility.
- `acpx` compatibility.
- Direct provider API clients.
- Arbitrary shell command templates in config.
- Dynamic plugin loading from untrusted paths.
- Multi-step agent orchestration.
- Transcript summarization or context trimming.

## Key Design Decisions

- Use explicit, typed connector configs rather than arbitrary shell command templates.
- Build subprocess commands as argv lists; never use `shell=True`.
- Use an explicit connector registry first. Single-file plugins are easy to add without dynamic import complexity.
- Keep connector output handling centralized: trim stdout; on failure report stderr, then stdout, then exit code.
- Constrain transcript output to `debates/`.
- Treat transcript content as the source of truth; connectors should not own conversation state.
- Keep connector modules thin: no subprocess calls, no config-file reads, no transcript logic, no exits, no printing.
- Put required-field validation, binary lookup, subprocess execution, timeout handling, verbose logging, and error normalization in shared/core code.

## Proposed Config Shape

```yaml
topic: "Should cities ban private cars from downtown cores?"
output: debates/debate-01.md
common_prompt: "Answer in no more than three sentences."

debaters:
  agent_1:
    name: "Urbanist"
    connector: "hermes"
    profile: "mina"
    seed: "You support car-free downtowns."
    timeout: 300

  agent_2:
    name: "Commuter Advocate"
    connector: "pi"
    model: "gpt-5-mini"
    seed: "You oppose blanket car bans."
    timeout: 300
```

Connector-specific fields:

- `hermes`: requires `profile`
- `pi`: requires `model`
- `opencode`: requires `model`

## Files to Change

- `master.debater.py`
  - remove `call_cellos_acp(...)`
  - load/call configured connector
  - validate core config fields
  - fix speaker parsing and output path safety
- `connectors/__init__.py`
  - explicit registry and connector lookup/call function
- `connectors/base.py`
  - shared subprocess/error helper and connector validation helpers
- `connectors/hermes.py`
- `connectors/pi.py`
- `connectors/opencode.py`
- `PLUGIN_CREATION.md`
- `config.yaml`
- `config.example1.yaml`
- `config.example2.yaml`
- `config.example3.yaml`
- `README.md`
- Optional: `tests/` if lightweight

## Connector Plugin Interface

Plugins expose harness-specific facts and argv construction only:

```python
NAME = "hermes"
REQUIRED_FIELDS = ("profile",)


def build_argv(config: dict, prompt: str) -> list[str]:
    return ["hermes", "--profile", config["profile"], "-z", prompt]
```

For model-based harnesses:

```python
NAME = "pi"
REQUIRED_FIELDS = ("model",)


def build_argv(config: dict, prompt: str) -> list[str]:
    return ["pi", "--model", config["model"], "-p", prompt]
```

Plugins must not:

- call `subprocess.run`
- use `shell=True`
- read or write files
- parse transcripts
- read `config.yaml`
- print to stdout/stderr
- call `sys.exit`
- perform dynamic imports
- access secrets directly unless the harness CLI already handles auth externally

## Shared Connector Interface

Shared code in `connectors/base.py` should own common behavior:

```python
def validate_config(connector_name: str, config: dict, required_fields: tuple[str, ...]) -> str | None:
    ...


def run_argv(display_name: str, argv: list[str], timeout: int, verbose: bool = False) -> tuple[str, str | None]:
    ...
```

Registry code in `connectors/__init__.py` should provide the public connector call:

```python
def call_connector(name: str, config: dict, prompt: str, timeout: int, verbose: bool = False) -> tuple[str, str | None]:
    connector = CONNECTORS.get(name)
    if connector is None:
        return "", f"unknown connector: {name}"
    error = validate_config(name, config, connector.REQUIRED_FIELDS)
    if error:
        return "", error
    argv = connector.build_argv(config, prompt)
    return run_argv(name, argv, timeout, verbose)
```

## Error Handling Contract

All connector calls should return `(text, None)` or `("", error)`; they should not print or exit.

Error priority for failed commands:

1. `stderr.strip()`
2. `stdout.strip()`
3. `exit code <N>`

Timeout errors should include the configured timeout. Missing binary errors should name the missing command.

Verbose logging should show the executable and non-prompt options but should not print the full prompt unless a future explicit debug flag is added.

## Plugin Registry

Use explicit registry in `connectors/__init__.py`:

```python
from . import hermes, opencode, pi

CONNECTORS = {
    "hermes": hermes,
    "pi": pi,
    "opencode": opencode,
}
```

This avoids arbitrary file import and keeps security review straightforward.

## PLUGIN_CREATION.md Requirements

Create `PLUGIN_CREATION.md` as the contributor guide for future harness connectors. It should include:

- the purpose of connector plugins
- the required module interface: `NAME`, `REQUIRED_FIELDS`, `build_argv(config, prompt)`
- what belongs in a plugin vs shared/core code
- security rules: argv lists only, no shell strings, no subprocess, no file I/O, no secrets handling
- how to add the plugin to the explicit registry
- how to document connector-specific config fields
- how to test command construction with a fake CLI or inline check
- example skeleton plugin
- checklist for adding Qwen/Codex/future harnesses

## Task Breakdown

- [ ] Slice 0 — parallel-safe — Confirm Hermes CLI contract
  Scope: local CLI behavior only; no source edits.
  Stop when: `hermes --profile <profile> -z "Reply with exactly: ok"` is confirmed, or blocker recorded.
  Verify: run `hermes --help`/one tiny prompt if safe.
  Risk: P2 — command may differ by version.

- [ ] Slice 1 — parallel-safe — Confirm Pi CLI contract
  Scope: local CLI behavior only; no source edits.
  Stop when: `pi --model <model> -p "Reply with exactly: ok"` is confirmed, or blocker recorded.
  Verify: run `pi --help`/one tiny prompt if safe.
  Risk: P2 — command may differ by version.

- [ ] Slice 2 — parallel-safe — Confirm OpenCode CLI contract
  Scope: local CLI behavior only; no source edits.
  Stop when: `opencode run --model <model> "Reply with exactly: ok"` is confirmed, or blocker recorded.
  Verify: run `opencode --help`/one tiny prompt if safe.
  Risk: P2 — command may differ by version.

- [ ] Slice 3 — sequential — Add connector package and shared subprocess behavior
  Scope: `connectors/`.
  Depends on: enough Slice 0-2 evidence to implement at least one real connector; blocked if none can be confirmed.
  Stop when: registry, shared helper, and confirmed thin connector modules exist.
  Verify: fake-command checks or focused unit tests for success, nonzero, missing binary, timeout, empty stdout, unknown connector, and missing required fields.
  Risk: P2 — subprocess normalization.

- [ ] Slice 4 — sequential — Integrate connectors into debate loop
  Scope: `master.debater.py`.
  Depends on: Slice 3.
  Stop when: `call_cellos_acp(...)` is removed and debate turns call the configured connector.
  Verify: fake connector/CLI one-turn run.
  Risk: P1 — core behavior.

- [ ] Slice 5 — sequential — Update config schema and examples
  Scope: `master.debater.py`, `config.yaml`, `config.example*.yaml`.
  Depends on: Slice 4.
  Stop when: configs use `connector` fields and invalid configs fail clearly.
  Verify: config-load checks for valid examples and missing connector-specific fields.
  Risk: P2 — migration breakage.

- [ ] Slice 6 — sequential — Fix safety and resume issues
  Scope: `master.debater.py`.
  Can be bundled into Slice 4 if the change stays small.
  Stop when: speaker names with spaces resume correctly and output paths cannot escape `debates/`.
  Verify: inline checks for speaker parsing, moderator ignore, accepted/rejected output paths.
  Risk: P1 — resume correctness and file safety.

- [ ] Slice 7 — sequential — Add plugin authoring docs
  Scope: `PLUGIN_CREATION.md`.
  Depends on: Slice 3.
  Stop when: future connectors can be created without copying subprocess logic.
  Verify: skeleton matches actual connector interface and registry.
  Risk: P3 — docs accuracy.

- [ ] Slice 8 — sequential — Update README
  Scope: `README.md`.
  Depends on: Slices 3-7.
  Stop when: docs describe direct connector plugins and remove `cellos-acp`/`acpx` setup.
  Verify: README config example matches actual schema and links to `PLUGIN_CREATION.md`.
  Risk: P3 — docs accuracy.

- [ ] Slice 9 — sequential — Live Pi/Qwen smoke test
  Scope: local run only; generated transcript under `debates/`.
  Depends on: Slices 3-8.
  Stop when: a neutral debate topic completes exactly 5 turns using the `pi` connector with model `lmstudio/qwen/qwen3.8-27b`, or an external harness blocker is documented clearly.
  Required smoke config:
  - connector: `pi`
  - model: `lmstudio/qwen/qwen3.8-27b`
  - output: temporary transcript under `debates/`, such as `debates/pi-qwen-smoke-test.md`
  Verify:
  - `python3 master.debater.py --mod "Smoke test kickoff."`
  - `python3 master.debater.py --turns 5 --verbose`
  - transcript has header, moderator line, 10 debater responses, alternating speakers, and no `[ERROR:` lines
  Risk: P2 — depends on Pi, LM Studio/Qwen model availability, and credentials/config.

## Parallelization Check

- Slices 0, 1, and 2 are parallel-safe because they inspect separate CLI contracts and do not edit files.
- Slices 3-9 are sequential because they share public config schema, connector interface, docs, and generated transcript behavior.
- Slice 6 may be bundled with Slice 4 only if the builder keeps the patch small and focused; otherwise keep it separate.
- Slice 7 depends on the final connector interface from Slice 3.
- Review should happen once after Slices 3-8 are complete and focused checks pass.
- Main-session security review should happen after code review fixes and before commit.

## Tests / Checks

Minimum checks:

```bash
python3 -m py_compile master.debater.py connectors/*.py
```

Focused behavior checks:

- connector registry resolves known connectors and rejects unknown connectors
- connector-specific required fields fail clearly
- command construction uses argv lists
- plugins do not call subprocess directly
- missing binary returns useful error
- nonzero exit includes stderr or stdout
- timeout maps to useful error
- empty stdout maps to useful error
- speaker names with spaces are counted on resume
- moderator lines do not affect turn order
- `debates/debate-01.md` is accepted
- `../x.md` and absolute paths are rejected
- `PLUGIN_CREATION.md` skeleton matches implemented plugin interface

## Review and Security Gates

- Code-quality review after Slices 3-8 and focused checks pass.
- Main-session security review before commit.
- Security focus:
  - subprocess argv construction centralized in shared code
  - no `shell=True`
  - no arbitrary shell command templates
  - plugins do not run subprocess directly
  - config-controlled executable/options are constrained by explicit connector code
  - explicit connector registry only
  - output path validation under `debates/`
  - verbose/error leakage

## Smoke Test Rules

- Use a neutral, low-risk topic.
- Use the Pi harness with model `lmstudio/qwen/qwen3.8-27b` for the required live smoke test.
- Use a temporary transcript path under `debates/`, such as `debates/pi-qwen-smoke-test.md`.
- Avoid overwriting a user-valued transcript.
- If `config.yaml` must be changed for the smoke test, report that clearly before commit and decide whether to keep or revert it.
- A failed external harness call is acceptable only if the error is clear and attributable to harness setup, auth, model name, or missing binary.

## Risks

- Harness CLI contracts may differ by installed version.
- Some CLIs may emit status text around the model response.
- Some CLIs may stream output in ways that require cleanup.
- Long transcripts passed as command arguments may hit OS argument-length limits.
- Different harnesses may have different timeout semantics.
- `config.yaml` is local/user-specific; smoke-test edits should avoid overwriting useful user config without intent.

## Deferred Follow-up

- Add `qwen` connector after confirming exact one-shot syntax.
- Add `codex` connector after confirming exact one-shot syntax.
- Add prompt-file/stdin support for long transcripts if harnesses support it.
- Add connector-specific output cleaners if a harness emits wrappers/status text.
- Consider connector discovery only if the explicit registry becomes cumbersome.

## Recommended Next Action

Run Slices 0-2 in parallel: confirm Hermes, Pi, and OpenCode one-shot CLI contracts before connector implementation.
