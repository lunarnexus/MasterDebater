# MasterDebater

A simple way for two LLM agents to discuss a topic.

Each turn, both agents respond in alternation. The transcript grows as a plain `.md` file — you read it, watch the debate unfold, and decide when to stop. Use `--mod` to add moderator comments.

MasterDebater uses registry-backed connector plugins for Hermes, Pi, and OpenCode.

## Quick Start

1. Clone MasterDebater:

   ```bash
   git clone https://github.com/lunarnexus/MasterDebater.git
   cd MasterDebater
   ```

2. Install Python dependencies:

   ```bash
   pip install pyyaml
   ```

3. No extra agent bridge is required. Install the connector CLIs you plan to use:

   - Hermes
   - Pi
   - OpenCode

4. (Optional) Create or clone Hermes profiles for your debaters:

   ```bash
   hermes profile create debater1 --clone
   hermes profile create debater2 --clone
   ```

5. Edit `config.yaml` with your topic and debaters, then run:

   ```bash
   python3 master.debater.py --verbose
   ```

6. Optionally inject a moderator comment:

   ```bash
   python3 master.debater.py --mod "Stay focused on historical comparisons."
   ```

## Architecture

```
config.yaml              ← topic, debaters, output path
master.debater.py        ← orchestrator
connectors/              ← connector-backed agents
debates/                 ← generated .md transcripts
```

The orchestrator loads each debater’s connector, builds the prompt, and calls the connector CLI directly. The full transcript is passed as context on every turn so each debater sees the complete conversation history.

Transcript updates are written to disk immediately after each response, so long `--turns` runs can be monitored live and resumed from partial progress.

By default, each reply is printed in a compact one-line form as it arrives. With `--verbose`, the script prints the full appended transcript line for each response.

## Plugins

Connectors are registry-backed plugins keyed by connector name. Each plugin defines its CLI name and required config fields, then returns the argv used to launch the agent.

Examples:
- Hermes: `connector: "hermes"`, `profile: "mina"`
- Pi: `connector: "pi"`, `model: "lmstudio/qwen/qwen3.8-27b"`
- OpenCode: `connector: "opencode"`, `model: "lmstudio/qwen/qwen3.8-27b"`

If present, `PLUGIN_CREATION.md` is the authoring guide.

## Dependencies

- Python 3.10+
- `pyyaml` (`pip install pyyaml`)
- Hermes / Pi / OpenCode CLIs on your PATH

## Setup

1. Install Python dependencies:

   ```bash
   pip install pyyaml
   ```

2. If you are using Hermes, create profiles for your debaters:

   ```bash
   hermes profile create debater1 --clone
   hermes profile create debater2 --clone
   ```

3. Edit `config.yaml` with your topic, debater definitions, and target `.md` filename.

## Config

`config.yaml`:

```yaml
topic: "AI will do more good than harm"
output: debates/debate-01.md
common_prompt: "Search the internet if needed, challenge unsupported claims, and keep your answer brief."

debaters:
  agent_1:
    name: "Sentinel"
    connector: "hermes"
    profile: "mina"
    seed: "You are Sentinel, a techno-optimist..."
    timeout: 120
  agent_2:
    name: "Aegis"
    connector: "pi"
    model: "lmstudio/qwen/qwen3.8-27b"
    seed: "You are Aegis, a risk-analyst..."
    timeout: 120
```

**Fields:**

| Field | Required | Description |
|---|---|---|
| `topic` | Yes | Debate topic shown in the transcript header |
| `output` | Yes | Transcript `.md` path (relative to the script) |
| `common_prompt` | No | Shared instructions added to every prompt |
| `debaters` | Yes | Debater definitions (min 2) |
| `debaters.<key>.name` | Yes | Display name used in the transcript |
| `debaters.<key>.connector` | Yes | Connector plugin: `hermes`, `pi`, or `opencode` |
| `debaters.<key>.seed` | Yes | Persona / role prompt for this debater |
| `debaters.<key>.timeout` | Yes | Connector timeout in seconds |
| `debaters.<key>.profile` | Hermes only | Hermes profile name |
| `debaters.<key>.model` | Pi / OpenCode only | Model name passed to the connector |

## Usage

```bash
# Append one turn (both agents respond once)
python3 master.debater.py

# Append one turn with verbose output
python3 master.debater.py --turns 1 --verbose

# Append 5 turns at once (10 responses)
python3 master.debater.py --turns 5

# Inject a moderator comment without advancing the turn order
python3 master.debater.py --mod "Please address the strongest point from your opponent."
```

**Arguments:**

| Flag | Description |
|---|---|
| `--turns N` | Append N turns; defaults to 1 if omitted |
| `--mod TEXT` | Append a moderator comment without consuming a debater turn |
| `--verbose`, `-v` | Print each full transcript line as it is appended |

One turn = both agents respond once (2 responses total). Running the script again appends more turns to the existing transcript.

## Transcript Format

The transcript is a plain `.md` file — human readable, git-trackable, Obsidian-compatible.

```markdown
# AI will do more good than harm

**Agent 1:** Sentinel (hermes)

**Agent 2:** Aegis (pi)

---

Sentinel: [opening remarks...]

Aegis: [response...]
```

Each invocation appends to the file. The script tracks state from the transcript itself — no separate state file needed.

Moderator comments are appended and exit immediately; they do not advance the debater reply count or turn order.

## Error Handling

- If a connector call fails (timeout, crash, etc.), the error is appended to the transcript as `[ERROR: ...]`
- Single-turn append (`--turns 1` or default): error is recorded, script continues with the next debater
- Multi-turn append (`--turns N`, `N > 1`): error is recorded, **run stops immediately**
- For `--turns N` with `N > 1`, the run stops early on the first error
