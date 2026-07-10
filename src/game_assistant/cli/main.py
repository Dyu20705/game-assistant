"""Minimal command-line entry point for Game Assistant."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

DESCRIPTION = (
    "Game Assistant is a local-first, coach-only rhythm-game training "
    "assistant under active development."
)


def build_parser() -> argparse.ArgumentParser:
    return argparse.ArgumentParser(
        prog="game-assistant",
        description=DESCRIPTION,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    parser.parse_args(argv)
    return 0
