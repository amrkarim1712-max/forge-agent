# Architecture

Forge Agent is a provider-independent state machine around these boundaries:

1. **Configuration** loads non-secret preferences from defaults, `~/.config/forge/config.toml`, environment variables, and CLI overrides. Budgets and dry-run are explicit settings.
2. **Context** discovers a project root, filters ignored/secrets/binary files, detects ecosystems, indexes symbols/imports, and selects bounded relevant text.
3. **Model** implements a common provider interface. OpenAI and OpenAI-compatible chat completions are real transports with transient retries; unsupported native providers fail clearly.
4. **Tools** expose structured functions for filesystem, terminal, quality checks, web research, and Git. Review-level actions go through approval before execution.

The runtime transitions through `INITIALIZE`, `INSPECT`, `UNDERSTAND`, `PLAN`, `EXECUTE`, `VERIFY`, `REPAIR`, and a terminal `COMPLETE`, `BLOCKED`, or `FAILED` state. It sends tool definitions to the model, executes returned calls, feeds results back into the conversation, and stops at a bounded iteration count. Changed projects receive detected verification checks and a limited repair loop.

```text
request
  -> inspect/context/index
  -> plan
  -> model + approved tools
  -> verify tests/lint/typecheck/build
  -> repair (bounded) or complete/blocked/failed
```