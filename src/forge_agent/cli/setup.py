"""Interactive first-run setup for the Forge CLI."""

from __future__ import annotations

import getpass
import os
from collections.abc import Callable

from forge_agent.config import load_settings, save_user_config


Input = Callable[[str], str]


def _ask(prompt: str, default: str, input_fn: Input) -> str:
    answer = input_fn(f"{prompt} [{default}]: ").strip()
    return answer or default


def run_setup(*, input_fn: Input = input, password_fn: Callable[[str], str] = getpass.getpass) -> int:
    """Run the interactive setup wizard without persisting credentials."""
    print("Forge Agent setup")
    print("=" * 18)
    print("Your API key is never written to the Forge config file.\n")

    provider = _ask("Provider (openai, groq, compatible)", "openai", input_fn).lower()
    while provider not in {"openai", "groq", "compatible"}:
        print("Choose openai, groq, or compatible.")
        provider = _ask("Provider", "openai", input_fn).lower()

    defaults = {
        "openai": ("gpt-4o-mini", "https://api.openai.com/v1", "OPENAI_API_KEY"),
        "groq": ("llama-3.3-70b-versatile", "https://api.groq.com/openai/v1", "GROQ_API_KEY"),
        "compatible": ("provider-model", "https://provider.example/v1", "FORGE_API_KEY"),
    }
    default_model, default_url, key_name = defaults[provider]
    model = _ask("Model", default_model, input_fn)
    base_url = _ask("API base URL", default_url, input_fn)

    save_user_config({"provider": provider, "model": model, "api_base_url": base_url})
    key = password_fn(f"{key_name} (leave blank to configure it later): ").strip()
    settings = load_settings(overrides={"provider": provider, "model": model, "api_base_url": base_url})

    print(f"\nSaved non-secret settings to your Forge config.")
    print("\nSet the API key in your current shell:")
    if key:
        if os.name == "nt":
            print(f'$env:{key_name} = "{key}"')
        else:
            print(f'export {key_name}="{key}"')
    else:
        print(f"Configure {key_name} before running Forge.")
    print("\nRun:")
    print("  forge doctor")
    print("  forge")
    print(f"\nSelected provider: {settings.provider}")
    return 0
