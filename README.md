# MasterDebater

A simple way for two LLM agents to discuss a topic.  Use your existing agent orchestrated via [`cellos-acp`](https://github.com/lunarnexus/cellos-acp).

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

3. Install `cellos-acp` with `pipx`:

   ```bash
   pipx install git+https://github.com/lunarnexus/cellos-acp.git
   ```

4. Verify `cellos-acp` is available:

   ```bash
   cellos-acp list
   ```

5. (Optional) Create or clone Hermes profiles for your debaters:

   ```bash
   hermes profile create debater1 --clone
   hermes profile create debater2 --clone
   ```

   Then point `config.yaml` at those profile names with `hermes_profile`.

6. Edit `config.yaml` with your topic and debaters, then run:

   ```bash
   python3 master.debater.py --single-turn --verbose
   ```

## Architecture

```
config.yaml              ← topic, debaters, output path
master.debater.py        ← orchestrator
  ├─ Reads config
  ├─ Reads/writes transcript
  ├─ Alternates debaters
  └─ Calls cellos-acp via subprocess
debates/                 ← generated .md transcripts
```

The script calls `cellos-acp run --agent <name> --text --timeout <N> "<prompt>"` for each response. The full transcript is passed as context on every turn so each debater sees the complete conversation history.

## Dependencies

- Python 3.10+
- `pyyaml` (`pip install pyyaml`)
- `cellos-acp` (`pipx install git+https://github.com/lunarnexus/cellos-acp.git`)

## Setup

1. Install Python dependencies:

   ```bash
   pip install pyyaml
   ```

2. Install `cellos-acp`:

   ```bash
   pipx install git+https://github.com/lunarnexus/cellos-acp.git
   ```

3. Verify `cellos-acp` works:

   ```bash
   cellos-acp list
   ```

    Make sure your two agents are registered (opencode, hermes, etc.).

4. If you are using Hermes, create profiles for your debaters:

   ```bash
   hermes profile create debater1 --clone
   hermes profile create debater2 --clone
   ```

   Update each profile's model/provider settings as needed, then reference them in `config.yaml` via `hermes_profile`.

5. Edit `config.yaml` with your topic, debater definitions, and target `.md` filename.

## Config

`config.yaml`:

```yaml
topic: "AI will do more good than harm"
output: debates/debate-01.md

debaters:
  agent_1:
    name: "Sentinel"
    agent: "hermes"
    hermes_profile: "mina"
    seed: "You are Sentinel, a techno-optimist..."
    timeout: 120
  agent_2:
    name: "Aegis"
    agent: "hermes"
    hermes_profile: "mina"
    seed: "You are Aegis, a risk-analyst..."
    timeout: 120
```

**Fields:**

| Field | Required | Description |
|---|---|---|
| `topic` | Yes | The debate topic (appears in transcript header) |
| `output` | Yes | Path to the `.md` transcript file (relative to script dir) |
| `debaters` | Yes | Dict of debater definitions (min 2) |
| `debaters.<key>.name` | Yes | Display name (used in transcript) |
| `debaters.<key>.agent` | Yes | Registered cellos-acp agent name |
| `debaters.<key>.hermes_profile` | No | Hermes profile name (only applies when `agent: hermes`) |
| `debaters.<key>.seed` | Yes | Persona/role prompt for this debater |
| `debaters.<key>.timeout` | Yes | cellos-acp timeout in seconds |

## Usage

```bash
# Run one turn (both agents respond once)
python3 master.debater.py

# Run one turn with verbose output
python3 master.debater.py --single-turn --verbose

# Run 5 turns at once (10 responses)
python3 master.debater.py --total-turns 5
```

**Arguments:**

| Flag | Description |
|---|---|
| `--single-turn` | Run exactly 1 turn (default) |
| `--total-turns N` | Run N turns at once (both agents respond N times) |
| `--verbose`, `-v` | Show each cellos-acp call and response before writing |

One turn = both agents respond once (2 responses total).

## Transcript Format

The transcript is a plain `.md` file — human readable, git-trackable, Obsidian-compatible.

```markdown
# AI will do more good than harm

**Agent 1:** Sentinel (hermes / mina)
Seed: You are Sentinel, a techno-optimist...

**Agent 2:** Aegis (hermes / mina)
Seed: You are Aegis, a risk-analyst...

---

Sentinel: [opening remarks...]

Aegis: [response...]
```

Each invocation appends to the file. The script tracks state from the transcript itself — no separate state file needed.

## Error Handling

- If a cellos-acp call fails (timeout, crash, etc.), the error is appended to the transcript as `[ERROR: ...]`
- `--single-turn` mode: error is recorded, script continues with next debater
- `--total-turns` mode: error is recorded, **run stops immediately**
