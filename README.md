# Game Assistant

Game Assistant is a local-first, CLI-first rhythm-game training assistant under active development. It is intended to become a coach-only tool that helps players review evidence from their own play, understand weaknesses, and plan practice without playing the game for them.

This repository currently contains only the Python project foundation. Functional coaching, analysis, storage, intake, recommendation, reports, and game adapters are not implemented yet.

## Requirements

- CPython 3.11 or newer
- Windows or Linux

## Setup

Create and activate a virtual environment:

```bash
python -m venv .venv
```

On Windows:

```bash
.venv\Scripts\activate
```

On Linux:

```bash
. .venv/bin/activate
```

Install the project in editable mode:

```bash
python -m pip install -e .
```

## CLI

Show help through the installed console script:

```bash
game-assistant --help
```

Show the same help through the Python module:

```bash
python -m game_assistant --help
```

The CLI help is intentionally minimal while the project is in its foundation stage.

## Tests

Run the dependency-free standard-library test suite:

```bash
python -m unittest discover -s tests -v
```

## Product Boundaries

Game Assistant is designed to run locally on the user's machine. It must not require cloud hosting, private services, network access, CUDA, Ollama, game installations, or private data for the foundation commands and tests in this repository state.

The project is coach-only and non-cheat. It must not auto-play, modify game clients, bypass anti-cheat systems, read game memory, or provide unfair live assistance. Future features should stay limited to evidence-based review and training guidance from user-provided data.
