# MasterDebater

A simple way for two LLM agents to discuss a topic. Uses [`acpx`](https://github.com/openclaw/acpx) one-shot exec mode to call any ACP-compatible agent.

Each turn, both agents respond in alternation. The transcript grows as a plain `.md` file — you read it, watch the debate unfold, and decide when to stop.

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

3. Install `acpx` globally:

   ```bash
   npm install -g acpx@latest
   ```

4. Verify `acpx` is available:

   ```bash
   acpx --help
   ```

5. (Optional) Ensure your target agents (Hermes, OpenCode, Claude Code, etc.) are installed.

6. Edit `config.yaml` with your topic and debaters, then run:

   ```bash
   python3 master.debater.py --verbose
   ```

7. Optionally inject a moderator comment:

   ```bash
   python3 master.debater.py --mod "Stay focused on historical comparisons."
   ```

## Architecture

```
config.yaml              <-- topic, debaters, output path
master.debater.py        <-- orchestrator
  +-- Reads config
  +-- Reads/writes transcript
  +-- Alternates debaters
  +-- Calls acpx exec via subprocess
debates/                 <-- generated .md transcripts
```

The script calls `acpx --agent <cmd> exec --timeout <N> --format text "<prompt>"` for each response. The full transcript is passed as context on every turn so each debater sees the complete conversation history.

Transcript updates are written to disk immediately after each response, so long `--total-turns` runs can be monitored live and resumed from partial progress.

By default, each reply is printed in a compact one-line form as it arrives. With `--verbose`, the script prints the full appended transcript line for each response.

## Dependencies

- Python 3.10+
- `pyyaml` (`pip install pyyaml`)
- `acpx` (`npm install -g acpx@latest`)
- Node.js 22+ (required by acpx)

## Setup

1. Install Python dependencies:

   ```bash
   pip install pyyaml
   ```

2. Install `acpx`:

   ```bash
   npm install -g acpx@latest
   ```

3. Verify `acpx` works:

   ```bash
   acpx --help
   ```

   Ensure your target agents (Hermes, OpenCode, Claude Code, etc.) are installed.

4. Edit `config.yaml` with your topic, debater definitions, and target `.md` filename.

## Config

`config.yaml`:

```yaml
topic: "AI will do more good than harm"
output: debates/debate-01.md
common_prompt: "Search the internet if needed, challenge unsupported claims, and keep your answer brief."

debaters:
  agent_1:
    name: "Sentinel"
    agent: "hermes acp -p debater1"
    seed: "You are Sentinel, a techno-optimist..."
    timeout: 120
  agent_2:
    name: "Aegis"
    agent: "hermes acp -p debater2"
    seed: "You are Aegis, a risk-analyst..."
    timeout: 120
```

**Fields:**

| Field | Required | Description |
|---|---|---|
| `topic` | Yes | The debate topic (appears in transcript header) |
| `output` | Yes | Path to the `.md` transcript file (relative to script dir) |
| `common_prompt` | No | Shared instructions applied to every debater prompt |
| `debaters` | Yes | Dict of debater definitions (min 2) |
| `debaters.<key>.name` | Yes | Display name (used in transcript) |
| `debaters.<key>.agent` | Yes | Full agent command passed to acpx via `--agent` (e.g. `hermes acp -p mina` or `opencode acp`) |
| `debaters.<key>.seed` | Yes | Persona/role prompt for this debater |
| `debaters.<key>.timeout` | Yes | acpx timeout in seconds |

## Usage

```bash
# Append one turn (both agents respond once)
python3 master.debater.py

# Append one turn with verbose output
python3 master.debater.py --turns 1 --verbose

# Append 5 turns at once (10 responses)
python3 master.debater.py --turns 5

# Inject a moderator comment without consuming a debater turn
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

The transcript is a plain `.md` file -- human readable, git-trackable, Obsidian-compatible.

```markdown
# AI will do more good than harm

**Agent 1:** Sentinel (hermes acp -p debater1)
Seed: You are Sentinel, a techno-optimist...

**Agent 2:** Aegis (hermes acp -p debater2)
Seed: You are Aegis, a risk-analyst...

---

Sentinel: [opening remarks...]
Aegis: [response...]
```

Each invocation appends to the file. The script tracks state from the transcript itself -- no separate state file needed.

Moderator comments are part of the visible conversation, but they do not affect which debater speaks next.

## Error Handling

- If an acpx call fails (timeout, crash, etc.), the error is appended to the transcript as `[ERROR: ...]`
- Single-turn append (`--turns 1` or default): error is recorded, script continues with the next debater
- Multi-turn append (`--turns N`, `N > 1`): error is recorded, **run stops immediately**
