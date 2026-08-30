from __future__ import annotations

import shutil
import subprocess
from typing import Mapping


class ConnectorError(ValueError):
    pass


def require_fields(config: Mapping[str, object], required_fields: tuple[str, ...]) -> None:
    missing = [field for field in required_fields if field not in config]
    if missing:
        raise ConnectorError(f"missing required connector fields: {', '.join(missing)}")


def run_argv(display_name: str, argv: list[str], timeout: int, verbose: bool = False) -> tuple[str, str | None]:
    if not argv:
        return "", f"{display_name} connector returned an empty command"

    executable = argv[0]
    if shutil.which(executable) is None:
        return "", f"{executable} not found (is it installed?)"

    if verbose:
        print(f"\n{'='*60}")
        print(" ".join(argv[:-1]) if len(argv) > 1 else argv[0])
        print(f"{'='*60}")

    try:
        result = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        text = result.stdout.strip()
        if result.returncode != 0:
            error = result.stderr.strip() or text or f"exit code {result.returncode}"
            return "", error
        if not text:
            return "", "(empty response)"
        return text, None
    except subprocess.TimeoutExpired:
        return "", f"timed out after {timeout}s"
    except Exception as e:
        return "", str(e)
