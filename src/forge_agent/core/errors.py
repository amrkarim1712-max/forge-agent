class ForgeError(Exception):
    """Base error for expected Forge Agent failures."""


class ConfigurationError(ForgeError):
    pass


class ProviderError(ForgeError):
    pass


class UnsupportedProviderError(ProviderError):
    pass


class ToolError(ForgeError):
    pass


class PermissionDenied(ToolError):
    pass


class MaxIterationsReached(ForgeError):
    pass