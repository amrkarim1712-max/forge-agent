# Forge Agent

Forge Agent is a portable, open-source, general-purpose AI coding agent that runs inside a project directory. It can inspect a repository, plan changes, use approved tools, edit files, run tests, repair failures, and report what it actually verified.

Forge is **not** a cybersecurity product. It is a software development assistant.

## Features

- Interactive and one-shot CLI: `forge` and `forge "request"`
- BYOK model access: users provide their own provider API key
- Real OpenAI, Groq, and OpenAI-compatible chat-completions transports
- Structured tool calls for reading, writing, editing, searching, commands, tests, and read-only Git
- Unified patches, line edits, file moves/deletes, symbol discovery, and Git write tools with approval
- Workspace path traversal protection
- Review prompts for file changes and risky shell commands
- Tool-schema validation and centralized secret redaction for command/tool output
- Deterministic, bounded repository context selection with ecosystem detection, ignore/secret filtering, and a lightweight code index
- Bounded agent iterations and repair attempts
- Automatic verification for tests, lint, type checks, and build scripts when available
- Dry-run mode, provider retries, `FORGE.md` project instructions, and optional configured web search
- `forge doctor`, structured debug events, and project memory at `.forge/project.md`

## Installation

Requires Python 3.11+.

```bash
./install.sh
# or:
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[test]"
```

## Configuration and BYOK

Forge does not ship an API key and does not provide inference for free. Set your own key in the environment:

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

For Groq, Forge selects the Groq endpoint and a supported default model automatically:

```bash
export FORGE_PROVIDER=groq
export GROQ_API_KEY="your-groq-key"
# Optional:
export FORGE_MODEL="llama-3.3-70b-versatile"
```

Groq uses the OpenAI-compatible tool-calling API. Override the endpoint only when using a compatible proxy:
`FORGE_API_BASE_URL=https://api.groq.com/openai/v1`.

Never commit keys, `.env` files, or private project data. See `.env.example` for variable names. `forge doctor` reports only whether a key is present, never its value.

## Usage

```bash
forge
forge "Explain how this repository works"
forge "Find the bug and run the tests"
forge --yes "Add a small feature"
forge --help
forge config
forge doctor
forge models
forge tools
forge memory
forge status
```

Without `--yes`, Forge asks before review-level file writes and risky commands. `--yes` is useful for a trusted local workflow.
Use `--dry-run` to inspect planned tool actions without changing files or running commands.

## Safety model

Forge keeps tool calls explicit and bounded. It rejects traversal outside the project root, caps file and command output, applies command timeouts, blocks a small set of clearly destructive commands, and asks for approval for writes and review-level commands. This is not a sandbox; run it with the OS permissions appropriate for the project.

## Architecture

See [docs/architecture.md](docs/architecture.md), [docs/tools.md](docs/tools.md), [docs/configuration.md](docs/configuration.md), [docs/providers.md](docs/providers.md), and [SECURITY.md](SECURITY.md).

## Development and testing

```bash
python -m pytest
python -m pip install -e ".[test]"
forge --help
forge doctor
```

The test suite uses a fake provider and never requires a paid API key.

## Current scope and roadmap

Implemented: explicit runtime phases, configuration budgets, OpenAI/Groq-compatible providers with transient retries, bounded context selection, ecosystem and symbol indexing, `FORGE.md` support, precise edits and unified patches, filesystem safety, command permissions, tests/lint/typecheck/build detection, repair attempts, read-only and approved Git operations, optional configured web search, CLI diagnostics, tests, and GitHub-ready packaging.

Planned: native Anthropic and Gemini transports, richer persistent memory workflows, advanced retrieval, and a fully orchestrated sub-agent runtime. Web search is available only when a real endpoint is explicitly configured.

## Contributing

Open an issue or pull request with a focused change, tests, and documentation updates. Keep provider code isolated, do not add secrets, and do not claim unsupported provider behavior.

## License

MIT. See [LICENSE](LICENSE).