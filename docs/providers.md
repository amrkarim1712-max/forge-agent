# Providers

## Implemented

- **OpenAI**: real chat-completions transport using `OPENAI_API_KEY`.
- **OpenAI-compatible**: real chat-completions transport using `FORGE_API_KEY` and `FORGE_API_BASE_URL`.
- **Groq**: real OpenAI-compatible transport using `GROQ_API_KEY`, defaulting to `https://api.groq.com/openai/v1` and `llama-3.3-70b-versatile`. `FORGE_API_BASE_URL` and `FORGE_MODEL` can override those defaults.

## Planned

Anthropic and Gemini are recognized provider slots so the model boundary is ready for them, but native transports are intentionally not included in this MVP. Forge reports them as unsupported rather than pretending they work.