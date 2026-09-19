from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

from forge_agent import __version__
from forge_agent.cli.setup import run_setup
from forge_agent.config import DEFAULTS, load_settings, save_user_config, user_config_path
from forge_agent.core.agent import Agent
from forge_agent.core.errors import ForgeError
from forge_agent.ui import TerminalUI


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="forge", description="Forge Agent: a local AI coding agent.")
    parser.add_argument("request", nargs="*", help="Request to execute; omit for interactive mode.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--provider", choices=["openai", "compatible", "groq", "anthropic", "gemini"])
    parser.add_argument("--model")
    parser.add_argument("--base-url", dest="api_base_url")
    parser.add_argument("--temperature", type=float)
    parser.add_argument("--max-tokens", type=int)
    parser.add_argument("--max-iterations", type=int)
    parser.add_argument("--max-repairs", type=int)
    parser.add_argument("--context-budget", type=int)
    parser.add_argument("--max-output-size", type=int)
    parser.add_argument("--max-file-size", type=int)
    parser.add_argument("--command-timeout", type=int)
    parser.add_argument("--cwd", "--workspace", dest="cwd", default=".")
    parser.add_argument("--yes", action="store_true", help="Approve review-level tool calls without prompting.")
    parser.add_argument("--dry-run", action="store_true", help="Show planned actions without modifying files or running commands.")
    parser.add_argument("--verbose", action="store_true", help="Show additional progress events.")
    parser.add_argument("--debug", action="store_true", help="Enable structured debug events on stderr.")
    return parser


def _config_command(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="forge config")
    parser.add_argument("--set", action="append", metavar="KEY=VALUE", help="Persist a non-secret setting.")
    args = parser.parse_args(argv)
    settings = load_settings()
    values: dict[str, object] = {}
    for item in args.set or []:
        if "=" not in item:
            parser.error("--set must use KEY=VALUE")
        key, value = item.split("=", 1)
        if key not in DEFAULTS:
            parser.error(f"Unknown or secret setting: {key}")
        values[key] = value
    if values:
        path = save_user_config(values)
        print(f"Saved non-secret settings to {path}")
        settings = load_settings()
    for key, value in settings.public_dict().items():
        print(f"{key}: {value}")
    return 0


def _doctor_command() -> int:
    settings = load_settings()
    print("Forge Agent Doctor")
    print(f"✓ Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    print(f"{'✓' if shutil.which('git') else '✗'} Git {'installed' if shutil.which('git') else 'not found'}")
    print(f"{'✓' if settings.cwd.is_dir() else '✗'} Current directory {'accessible' if settings.cwd.is_dir() else 'not accessible'}")
    config_state = "found" if user_config_path().is_file() else "using defaults"
    print(f"✓ Configuration {config_state}")
    print(f"{'✓' if settings.provider else '✗'} Provider configured: {settings.provider}")
    if settings.api_key_env:
        if settings.api_key:
            print("✓ Provider credential configured")
        else:
            print("✗ Provider credential not configured")
    else:
        print("✓ API key presence: provider does not require one")
    try:
        import httpx  # noqa: F401
        print("✓ httpx dependency available")
    except ImportError:
        print("✗ httpx dependency missing")
    return 0


def _models_command() -> int:
    print("Forge model providers")
    print("✓ openai       OpenAI chat completions")
    print("✓ compatible   OpenAI-compatible chat completions")
    print("✓ groq         Groq OpenAI-compatible transport (GROQ_API_KEY)")
    print("○ anthropic    Native transport planned")
    print("○ gemini       Native transport planned")
    return 0


def _tools_command() -> int:
    names = (
        "read_file", "write_file", "edit_file", "line_edit", "apply_patch", "delete_file", "move_file",
        "list_directory", "search_files", "search_text", "find_symbol", "run_command", "run_script", "run_tests",
        "git_status", "git_diff", "git_log", "git_branch", "git_show", "git_add", "git_commit",
        "run_linter", "run_formatter", "run_type_checker",
    )
    print("Forge tools")
    print("\n".join(f"- {name}" for name in names))
    print("- web_search (enabled only with FORGE_WEB_SEARCH_URL)")
    return 0


def _memory_command(cwd: str = ".") -> int:
    root = Path(cwd).expanduser().resolve()
    for path in (root / "FORGE.md", root / ".forge" / "project.md"):
        print(f"\n--- {path.relative_to(root)} ---")
        print(path.read_text(encoding="utf-8") if path.is_file() else "(not present)")
    return 0


def _status_command(cwd: str = ".") -> int:
    root = Path(cwd).expanduser().resolve()
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "status", "--short", "--branch"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        print(result.stdout or "(clean or not a Git repository)")
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        return 0 if result.returncode == 0 else 1
    except (OSError, subprocess.TimeoutExpired) as exc:
        print(f"Could not read Git status: {exc}", file=sys.stderr)
        return 1


def _should_run_setup() -> bool:
    settings = load_settings()
    if settings.provider in {"anthropic", "gemini"}:
        return True
    if not settings.api_key and settings.api_key_env:
        return True
    return False


def main(argv: list[str] | None = None) -> int:
    args_list = list(sys.argv[1:] if argv is None else argv)
    if args_list and args_list[0] == "config":
        return _config_command(args_list[1:])
    if args_list and args_list[0] == "doctor":
        return _doctor_command()
    if args_list and args_list[0] == "models":
        return _models_command()
    if args_list and args_list[0] == "tools":
        return _tools_command()
    if args_list and args_list[0] == "memory":
        return _memory_command(args_list[1] if len(args_list) > 1 else ".")
    if args_list and args_list[0] == "status":
        return _status_command(args_list[1] if len(args_list) > 1 else ".")
    if args_list and args_list[0] == "setup":
        return run_setup()
    if args_list and args_list[0] == "run":
        args_list = args_list[1:]
    parser = _parser()
    args = parser.parse_args(args_list)
    overrides = {
        "provider": args.provider,
        "model": args.model,
        "api_base_url": args.api_base_url,
        "temperature": args.temperature,
        "max_tokens": args.max_tokens,
        "max_iterations": args.max_iterations,
        "max_repair_attempts": args.max_repairs,
        "context_budget": args.context_budget,
        "max_output_size": args.max_output_size,
        "max_file_size": args.max_file_size,
        "command_timeout": args.command_timeout,
    }
    settings = load_settings(
        cwd=args.cwd,
        overrides=overrides,
        debug=args.debug or args.verbose,
        approve_all=args.yes,
        dry_run=args.dry_run,
    )
    if _should_run_setup() and not args_list:
        print("Forge is not configured yet. Starting setup...\n")
        return run_setup()
    ui = TerminalUI()
    request = " ".join(args.request).strip()
    if not request:
        ui.header(settings.model, settings.cwd)
        try:
            while True:
                request = ui.prompt()
                if not request:
                    continue
                if request in {"/exit", "/quit", "exit", "quit"}:
                    return 0
                try:
                    state = Agent(settings, ui=ui).run(request)
                    ui.response(state.final_response or "")
                except ForgeError as exc:
                    ui.error(str(exc))
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
    else:
        try:
            state = Agent(settings, ui=ui).run(request)
            ui.response(state.final_response or "")
            return 0 if not state.errors else 1
        except ForgeError as exc:
            ui.error(str(exc))
            return 1


if __name__ == "__main__":
    raise SystemExit(main())
