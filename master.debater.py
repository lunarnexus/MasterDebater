#!/usr/bin/env python3
"""MasterDebater — two-LLM debate via cellos-acp.

Usage:
    python3 master.debater.py                          # 1 turn (default)
    python3 master.debater.py --single-turn            # 1 turn
    python3 master.debater.py --total-turns 5          # 5 turns at once
    python3 master.debater.py --single-turn --verbose  # 1 turn, show details
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

import yaml


SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_FILE = SCRIPT_DIR / "config.yaml"


def load_config():
    """Load and validate config.yaml."""
    with open(CONFIG_FILE) as f:
        cfg = yaml.safe_load(f)

    required = {"topic", "output", "debaters"}
    missing = required - set(cfg.keys())
    if missing:
        print(f"ERROR: config.yaml missing keys: {missing}")
        sys.exit(1)

    debaters = cfg["debaters"]
    if len(debaters) < 2:
        print("ERROR: config needs at least 2 debaters.")
        sys.exit(1)

    for key, d in debaters.items():
        for field in ("name", "agent", "seed", "timeout"):
            if field not in d:
                print(f"ERROR: debater '{key}' missing field '{field}'")
                sys.exit(1)

    return cfg


def create_header(cfg):
    """Build the transcript header (topic + agent definitions)."""
    lines = [f"# {cfg['topic']}", ""]
    for i, (key, d) in enumerate(cfg["debaters"].items(), 1):
        lines.append(f"**Agent {i}:** {d['name']} ({d['agent']})")
        lines.append(f"Seed: {d['seed']}")
        lines.append("")
    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def parse_replies(transcript_text):
    """Extract reply lines from transcript. Returns list of (name, text) tuples."""
    in_replies = False
    replies = []
    for line in transcript_text.splitlines():
        line = line.rstrip()
        if not line:
            continue
        if line == "---":
            in_replies = True
            continue
        if not in_replies:
            continue
        m = re.match(r"^([A-Za-z][A-Za-z0-9_-]*):\s+(.*)$", line)
        if m:
            replies.append((m.group(1), m.group(2)))
    return replies


def build_prompt(seed, transcript_text):
    """Build the prompt for a single debater turn."""
    return f"""\
You are a participant in a debate.

Your role: {seed}

Current debate transcript:
{transcript_text}

It is your turn. Respond.
"""


def call_cellos_acp(agent_name, timeout, prompt, verbose=False, hermes_profile=None):
    """Call cellos-acp via subprocess. Returns (text, error)."""
    cmd = ["cellos-acp", "run", "--agent", agent_name, "--text", "--timeout", str(timeout)]
    if hermes_profile:
        cmd.extend(["--hermes-profile", hermes_profile])
    cmd.append(prompt)
    if verbose:
        print(f"\n{'='*60}")
        print(f"cellos-acp --agent {agent_name} --timeout {timeout}")
        print(f"{'='*60}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout + 30,
        )
        text = result.stdout.strip()
        if result.returncode != 0:
            error = result.stderr.strip() or f"exit code {result.returncode}"
            return "", error
        if not text:
            return "", "(empty response)"
        return text, None
    except subprocess.TimeoutExpired:
        return "", f"timed out after {timeout + 30}s"
    except FileNotFoundError:
        return "", "cellos-acp not found (is it installed?)"
    except Exception as e:
        return "", str(e)


def main():
    parser = argparse.ArgumentParser(description="MasterDebater — two-LLM debate")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--single-turn", action="store_true", help="Run exactly one turn (default)")
    group.add_argument("--total-turns", type=int, default=None, metavar="N",
                       help="Run N turns (both agents each respond N times)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show cellos-acp call details")
    args = parser.parse_args()

    if args.total_turns is not None:
        num_turns = args.total_turns
    else:
        num_turns = 1

    cfg = load_config()
    output_path = SCRIPT_DIR / cfg["output"]

    output_path.parent.mkdir(parents=True, exist_ok=True)

    transcript_text = ""
    if output_path.exists():
        transcript_text = output_path.read_text()
    else:
        transcript_text = create_header(cfg)

    replies = parse_replies(transcript_text)
    reply_count = len(replies)

    debater_keys = list(cfg["debaters"].keys())
    num_debaters = len(debater_keys)

    total_responses_needed = num_turns * num_debaters
    remaining_replies = total_responses_needed - reply_count
    if remaining_replies <= 0:
        print(f"Already have {reply_count} replies ({reply_count // num_debaters} turns). No more needed.")
        sys.exit(0)

    new_responses = []
    error_stopped = False

    for i in range(remaining_replies):
        speaker_idx = (reply_count + i) % num_debaters
        key = debater_keys[speaker_idx]
        d = cfg["debaters"][key]

        prompt = build_prompt(d["seed"], transcript_text)
        text, error = call_cellos_acp(
            d["agent"], d["timeout"], prompt, args.verbose,
            d.get("hermes_profile")
        )

        if error:
            response_line = f"{d['name']}: [ERROR: {error}]"
            if args.total_turns is not None:
                new_responses.append(response_line)
                transcript_text += response_line + "\n\n"
                error_stopped = True
                break
            else:
                new_responses.append(response_line)
                transcript_text += response_line + "\n\n"
        else:
            response_line = f"{d['name']}: {text}"
            new_responses.append(response_line)
            transcript_text += response_line + "\n\n"

        if args.verbose:
            print(f"\n>>> {d['name']} replied ({len(text)} chars)\n")

    output_path.write_text(transcript_text)

    total_replies = len(replies) + len(new_responses)
    turns_done = total_replies // num_debaters
    print(f"Turns complete: {turns_done}")
    print(f"Responses: {total_replies} ({num_debaters} debaters x {turns_done} turns)")
    print(f"Transcript: {output_path}")
    if error_stopped:
        print("(Stopped early due to error)")


if __name__ == "__main__":
    main()
