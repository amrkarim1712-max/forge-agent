# Configuration

Forge uses this precedence order:

1. CLI flags
2. environment variables
3. `~/.config/forge/config.toml`
4. built-in defaults

OpenAI uses `OPENAI_API_KEY`. Never put that value in a tracked file.

Useful commands:

```bash
forge config
forge config --set model=gpt-4o-mini
forge doctor
forge --dry-run "Refactor the database layer"
forge --provider compatible --base-url https://your-endpoint/v1 --model your-model
```

Compatible providers use `FORGE_API_KEY` and `FORGE_API_BASE_URL`. Groq uses `GROQ_API_KEY` and automatically selects `https://api.groq.com/openai/v1` with `llama-3.3-70b-versatile` unless you override those settings:

```bash
export FORGE_PROVIDER=groq
export GROQ_API_KEY="your-groq-key"
export FORGE_MODEL="llama-3.3-70b-versatile"  # optional
```

The `anthropic` and `gemini` provider names are reserved architecture slots and fail clearly until native transports are implemented.

Additional controls include `FORGE_RETRY_ATTEMPTS`, `FORGE_RETRY_BACKOFF`, `FORGE_CONTEXT_BUDGET`, `FORGE_MAX_OUTPUT_SIZE`, `FORGE_MAX_FILE_SIZE`, `FORGE_TOOL_TIMEOUT`, and `FORGE_WEB_SEARCH_URL`. The web endpoint is disabled unless explicitly configured.

Place repository-specific conventions and verification instructions in `FORGE.md`. Forge treats that file as untrusted project input; it cannot override system safety rules.