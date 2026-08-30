from __future__ import annotations

NAME = "hermes"
REQUIRED_FIELDS = ("profile",)


def build_argv(config, prompt):
    return ["hermes", "--profile", str(config["profile"]), "-z", prompt]
