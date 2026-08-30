#!/usr/bin/env python3
"""MasterDebater — two-LLM debate via connector plugins.

Usage:
    python3 master.debater.py                          # append 1 turn (default)
    python3 master.debater.py --turns 3                # append 3 turns
    python3 master.debater.py --mod "Stay on topic."   # add moderator comment
    python3 master.debater.py --turns 1 --verbose      # 1 turn, show details
"""

import argparse
import re
import sys
from pathlib import Path

import yaml

from connectors import ConnectorError, REGISTRY, call_connector, require_fields


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

    if "common_prompt" in cfg and not isinstance(cfg["common_prompt"], str):
        print("ERROR: config.common_prompt must be a string.")
        sys.exit(1)

    if not isinstance(cfg["output"], str):
        print("ERROR: config.output must be a string.")
        sys.exit(1)

    for key, d in debaters.items():
        for field in ("name", "connector", "seed", "timeout"):
            if field not in d:
                print(f"ERROR: debater '{key}' missing field '{field}'")
                sys.exit(1)
        if not isinstance(d["timeout"], (int, float)) or d["timeout"] <= 0:
            print(f"ERROR: debater '{key}' timeout must be a positive number.")
            sys.exit(1)
        connector_name = d["connector"]
        connector = REGISTRY.get(connector_name)
        if connector is None:
            print(f"ERROR: debater '{key}' has unknown connector '{connector_name}'")
            sys.exit(1)
        try:
            require_fields(d, connector.REQUIRED_FIELDS)
        except ConnectorError as e:
            print(f"ERROR: debater '{key}' {e}")
            sys.exit(1)

    return cfg


def create_header(cfg):
    """Build the transcript header (topic + agent definitions)."""
    lines = [f"# {cfg['topic']}", ""]
    for i, (_, d) in enumerate(cfg["debaters"].items(), 1):
        lines.append(f"**Agent {i}:** {d['name']} ({d['connector']})")
        lines.append("")
    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def parse_conversation_state(transcript_text, participating_speakers):
    """Return the last participating speaker and count of participating replies."""
    in_replies = False
    spoke_last = participating_speakers[-1]
    response_count = 0
    speakers = sorted(participating_speakers, key=len, reverse=True)
    for line in transcript_text.splitlines():
        line = line.rstrip()
        if not line:
            continue
        if line == "---":
            in_replies = True
            continue
        if not in_replies:
            continue
        for speaker in speakers:
            prefix = f"{speaker}: "
            if line.startswith(prefix):
                spoke_last = speaker
                response_count += 1
                break
    return spoke_last, response_count


def build_prompt(seed, transcript_text, common_prompt=""):
    """Build the prompt for a single debater turn."""
    common_prompt_block = f"Common instructions: {common_prompt}\n\n" if common_prompt else ""
    return f"""\
You are a participant in a debate.

{common_prompt_block}Your role: {seed}

Current debate transcript:
{transcript_text}

It is your turn. Respond.
"""


def format_response_preview(response_line, limit=140):
    """Return a compact single-line preview for console output."""
    preview = " ".join(response_line.split())
    if len(preview) <= limit:
        return preview
    return preview[: limit - 3] + "..."



def validate_output_path(output_value):
    output_path = (SCRIPT_DIR / output_value).resolve()
    debates_root = (SCRIPT_DIR / "debates").resolve()
    if output_path == debates_root or debates_root not in output_path.parents:
        print("ERROR: output path must be a file under debates/")
        sys.exit(1)
    if output_path.suffix == "" or output_path.name == "":
        print("ERROR: output path must be a file under debates/")
        sys.exit(1)
    return output_path


def append_transcript_line(output_path, transcript_text, line):
    """Append a single conversation line and persist immediately."""
    transcript_text += line + "\n\n"
    output_path.write_text(transcript_text)
    return transcript_text


def main():
    parser = argparse.ArgumentParser(description="MasterDebater — two-LLM debate")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--turns", type=int, default=None, metavar="N",
                       help="Append N turns (both agents each respond N times)")
    group.add_argument("--mod", type=str, default=None, metavar="TEXT",
                       help="Append a moderator comment to the transcript")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show connector call details")
    args = parser.parse_args()

    num_turns = args.turns if args.turns is not None else 1
    if num_turns < 1:
        print("ERROR: --turns must be at least 1.")
        sys.exit(1)

    cfg = load_config()
    output_path = validate_output_path(cfg["output"])
    common_prompt = cfg.get("common_prompt", "")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    transcript_text = ""
    if output_path.exists():
        transcript_text = output_path.read_text()
    else:
        transcript_text = create_header(cfg)

    if args.mod is not None:
        transcript_text = append_transcript_line(output_path, transcript_text, f"Moderator: {args.mod}")
        print(f"Moderator comment appended: {output_path}")
        sys.exit(0)

    debater_keys = list(cfg["debaters"].keys())
    participant_names = [cfg["debaters"][key]["name"] for key in debater_keys]
    num_debaters = len(debater_keys)

    spoke_last, reply_count = parse_conversation_state(transcript_text, participant_names)
    next_speaker_idx = (participant_names.index(spoke_last) + 1) % num_debaters

    responses_to_generate = num_turns * num_debaters

    new_responses = []
    error_stopped = False

    for i in range(responses_to_generate):
        speaker_idx = (next_speaker_idx + i) % num_debaters
        key = debater_keys[speaker_idx]
        d = cfg["debaters"][key]

        prompt = build_prompt(d["seed"], transcript_text, common_prompt)
        text, error = call_connector(
            d["connector"], d, prompt, d["timeout"], args.verbose
        )

        if error:
            response_line = f"{d['name']}: [ERROR: {error}]"
            new_responses.append(response_line)
            transcript_text = append_transcript_line(output_path, transcript_text, response_line)
            error_stopped = True
            if num_turns > 1:
                break
        else:
            response_line = f"{d['name']}: {text}"
            new_responses.append(response_line)
            transcript_text = append_transcript_line(output_path, transcript_text, response_line)

        if args.verbose:
            print(f"\n{response_line}\n")
        else:
            print(f"{format_response_preview(response_line)}\n")

    total_replies = reply_count + len(new_responses)
    turns_done = total_replies // num_debaters
    print(f"Turns complete: {turns_done}")
    print(f"Responses: {total_replies} ({num_debaters} debaters x {turns_done} turns)")
    print(f"Transcript: {output_path}")
    if error_stopped:
        print("(Stopped early due to error)")


if __name__ == "__main__":
    main()
