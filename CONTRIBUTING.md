# Contributing to Forge Agent

## Development setup

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[test]"
python -m pytest -q
```

Keep provider transports, tools, permissions, context, and CLI concerns in their existing modules. New behavior should have deterministic tests and documentation.

## Pull requests

- Explain the user-facing behavior and safety implications.
- Include tests for changed behavior.
- Do not include API keys, credentials, private repository contents, or generated environments.
- Do not claim a provider or tool works unless it has a real implementation.