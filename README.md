# Forge Agent

Forge Agent is a portable, open-source, general-purpose AI coding agent that runs inside a project directory. It can inspect a repository, plan changes, use approved tools, edit files, run tests, and report bounded results.

Forge is not a cybersecurity product. It is a software development assistant.

## Python requirement

Python 3.11 or newer.

## Installation

The PyPI package name for this project is `forge-agent-ai`.

Install the package when it is published to PyPI:

```bash
python -m pip install forge-agent-ai
```

For local development in a checkout:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[dev]"
```

The repository helper script also installs the package in editable mode with test dependencies:

```bash
./install.sh
```

## CLI usage

```bash
forge --help
forge --version
forge doctor
forge models
forge tools
forge memory
forge status
```

The project is intentionally built so that the Python package import remains `forge_agent` while the CLI command remains `forge`.

## BYOK and provider configuration

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

For Groq:

```bash
export FORGE_PROVIDER=groq
export GROQ_API_KEY="your-groq-key"
export FORGE_MODEL="llama-3.3-70b-versatile"
```

Never commit API keys, `.env` files, or private project data. `forge doctor` reports only whether a key is present, never its value.

## Development and testing

```bash
python -m pip install -e ".[test]"
python -m pytest
```

## Building the package

```bash
python -m pip install --upgrade build
python -m build
```

This creates a wheel and a source distribution in `dist/`.

## Security and packaging hygiene

The project excludes local development and secret files from packaging. Do not include `.env`, API keys, `.venv`, caches, project memory, or generated build artifacts in the package or repository.

## License

MIT. See [LICENSE](LICENSE).
