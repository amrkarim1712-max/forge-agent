# Forge Agent

Forge Agent is a portable, open-source AI coding agent for local software projects. It can inspect a repository, plan edits, use approved tools, run tests, and report what it actually verified.

Forge is not a cybersecurity product. It is a software development assistant.

## Features

- Interactive and one-shot CLI: `forge` and `forge "request"`
- BYOK model access with your own provider API key
- OpenAI, Groq, and OpenAI-compatible model transports
- Structured tools for reading, writing, searching, running commands, and Git operations
- Workspace path protections and approval checks for risky actions
- Deterministic repository context selection and bounded repair loops
- Optional `FORGE.md` project instructions and dry-run mode
- `forge doctor`, `forge models`, `forge tools`, `forge memory`, and `forge status`

## Requirements

- Python 3.11+
- Git for repository status and Git-based tools

## Installation

For local development:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[test]"
```

Or use the repository helper:

```bash
./install.sh
```

## Configuration and BYOK

Forge does not ship an API key and does not provide inference for free. Set your own key and model in the environment:

```bash
export OPENAI_API_KEY="your-key"
export FORGE_MODEL="gpt-4o-mini"
```

For an OpenAI-compatible endpoint:

```bash
export FORGE_PROVIDER=compatible
export FORGE_API_KEY="your-key"
export FORGE_API_BASE_URL="https://provider.example/v1"
export FORGE_MODEL="provider-model"
```

For Groq:

```bash
export FORGE_PROVIDER=groq
export GROQ_API_KEY="your-groq-key"
export FORGE_MODEL="llama-3.3-70b-versatile"
```

Never commit API keys, `.env` files, or private project data. See `.env.example` for variable names. `forge doctor` reports only whether a key is present, never its value.

## Quick start

```bash
forge --help
forge doctor
forge "Explain how this repository works"
forge --yes "Add a small feature"
forge --dry-run "Check for a bug and run the relevant tests"
```

Without `--yes`, Forge asks before review-level file writes and risky commands. `--dry-run` shows the planned actions without modifying files or running commands.

## Safety model

Forge keeps tool calls explicit and bounded. It rejects traversal outside the project root, caps output sizes, applies command timeouts, and prompts before review-level writes and risky shell actions. This is not a sandbox; run it with the OS permissions appropriate for your project.

## Development and testing

```bash
python -m pip install -e ".[test]"
python -m pytest
```

The test suite uses a fake provider and does not require a paid API key.

## Building the package

```bash
python -m pip install --upgrade build
python -m build
```

This creates a wheel and a source distribution in `dist/`.

## Project structure

- `src/forge_agent/` — main Python package
- `tests/` — automated tests
- `docs/` — architecture and usage documentation
- `install.sh` — local development installer

## Contributing

Open an issue or pull request with a focused change, tests, and documentation updates. Keep provider code isolated, do not add secrets, and do not claim unsupported provider behavior.

## License

MIT. See [LICENSE](LICENSE).
