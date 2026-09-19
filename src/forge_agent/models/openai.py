from .compatible import OpenAICompatibleProvider


class OpenAIProvider(OpenAICompatibleProvider):
    """OpenAI's chat completions API, isolated behind the provider interface."""