# Security policy

Forge runs commands and edits files in a user's project. The permission layer reduces accidental destructive actions but is not an operating-system sandbox.

## Safety boundaries

- Project paths are normalized and traversal outside the workspace is rejected by default.
- Review-level writes, deletes, moves, patch applications, Git writes, network search, and risky shell commands require approval.
- Commands have timeouts and bounded output.
- Environment variables containing common secret markers are removed before shell tools run.
- Tool arguments are checked against each tool's declared schema before execution.
- Credential values and common `key=value` / `token=value` patterns are redacted from tool results, approval details, model messages, and final responses.
- Configured web-search responses are bounded before they reach the model.
- Repository files, including `FORGE.md`, are treated as untrusted input and cannot override system safety rules.
- API keys are read only from environment variables and are never written to memory or tool output.

## Reporting a vulnerability

Please report security issues privately to the project maintainers before opening a public issue. Include reproduction steps, affected versions, and a suggested mitigation when available. Do not include live credentials or private project contents.