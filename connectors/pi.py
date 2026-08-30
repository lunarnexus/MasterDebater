from __future__ import annotations

NAME = "pi"
REQUIRED_FIELDS = ("model",)


def build_argv(config, prompt):
    return ["pi", "--model", str(config["model"]), "-p", prompt]
