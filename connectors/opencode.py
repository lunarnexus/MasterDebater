from __future__ import annotations

NAME = "opencode"
REQUIRED_FIELDS = ("model",)


def build_argv(config, prompt):
    return ["opencode", "run", "-m", str(config["model"]), prompt]
