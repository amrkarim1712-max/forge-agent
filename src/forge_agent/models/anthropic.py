from forge_agent.core.errors import UnsupportedProviderError


class AnthropicProvider:
    def __init__(self, *args, **kwargs):
        raise UnsupportedProviderError(
            "Anthropic is an architectural provider slot, but its native transport is not implemented in this MVP."
        )