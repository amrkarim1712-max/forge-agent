from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from forge_agent.config import Settings
from forge_agent.context import ContextManager
from forge_agent.context.index import CodeIndex
from forge_agent.core.events import EventLogger
from forge_agent.core.prompts import SYSTEM_PROMPT, user_prompt
from forge_agent.core.state import AgentState
from forge_agent.security import redact_data, redact_text
from forge_agent.models import ModelProvider, create_provider
from forge_agent.planning import Planner, Verifier
from forge_agent.ui import ApprovalManager, TerminalUI
from forge_agent.tools.filesystem import register_filesystem_tools
from forge_agent.tools.git import register_git_tools
from forge_agent.tools.registry import ToolRegistry
from forge_agent.tools.terminal import register_terminal_tools
from forge_agent.tools.tests import register_test_tool
from forge_agent.tools.web import register_web_tool
from forge_agent.core.state import AgentPhase


class Agent:
    def __init__(
        self,
        settings: Settings,
        *,
        provider: ModelProvider | None = None,
        ui: TerminalUI | None = None,
        approval: ApprovalManager | None = None,
    ) -> None:
        self.settings = settings
        self.provider = provider or create_provider(settings)
        self.ui = ui or TerminalUI()
        self.approval = approval or ApprovalManager(settings.approve_all)
        self.events = EventLogger(settings.debug)
        self.registry = ToolRegistry()
        context = ContextManager(settings.cwd, max_chars=settings.context_budget)
        register_filesystem_tools(
            self.registry,
            settings.cwd,
            max_file_size=settings.max_file_size,
            max_output_size=settings.max_output_size,
            dry_run=settings.dry_run,
            symbol_index=context.index,
        )
        register_terminal_tools(
            self.registry,
            settings.cwd,
            settings.command_timeout,
            max_output_size=settings.max_output_size,
            dry_run=settings.dry_run,
        )
        register_git_tools(self.registry, settings.cwd, dry_run=settings.dry_run, max_output_size=settings.max_output_size)
        register_test_tool(self.registry, settings.cwd, settings.command_timeout)
        if settings.web_search_url:
            register_web_tool(self.registry, settings.web_search_url, timeout=settings.tool_timeout)

    def _tool_call_message(self, response) -> dict[str, Any]:
        return redact_data({
            "role": "assistant",
            "content": response.content or None,
            "tool_calls": [
                {
                    "id": call.id,
                    "type": "function",
                    "function": {"name": call.name, "arguments": json.dumps(call.arguments)},
                }
                for call in response.tool_calls
            ],
        })

    def run(self, request: str) -> AgentState:
        context_manager = ContextManager(self.settings.cwd, max_chars=self.settings.context_budget)
        context, relevant = context_manager.build(request)
        state = AgentState(
            request=request,
            cwd=self.settings.cwd,
            relevant_files=relevant,
            current_objective=request,
            provider_name=self.settings.provider,
            model_name=self.settings.model,
            context_budget=self.settings.context_budget,
            output_budget=self.settings.max_tokens,
        )
        state.transition(AgentPhase.INSPECT)
        state.plan = Planner().create(request)
        if state.plan:
            state.pending_steps = list(state.plan.steps)
            state.transition(AgentPhase.PLAN)
        plan_text = state.plan.render() if state.plan else None
        state.messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt(request, context, plan_text)},
        ]
        self.events.emit("agent.started", project=str(self.settings.cwd))
        if state.plan:
            self.ui.status("Planning...")
            self.ui.status(state.plan.render())
        self.ui.status("Inspecting project...")
        state.transition(AgentPhase.UNDERSTAND)

        repair_attempts = 0
        while state.iteration < self.settings.max_iterations:
            state.iteration += 1
            state.transition(AgentPhase.EXECUTE)
            self.events.emit("model.request", iteration=state.iteration)
            try:
                response = self.provider.generate(
                    state.messages,
                    self.registry.definitions(),
                    temperature=self.settings.temperature,
                    max_tokens=self.settings.max_tokens,
                )
            except Exception as exc:
                safe_error = redact_text(str(exc))
                state.errors.append(safe_error)
                state.final_response = f"I could not contact the configured model provider: {safe_error}"
                state.transition(AgentPhase.FAILED)
                self.events.emit("agent.completed", success=False, error=str(exc))
                return state
            self.events.emit("model.response", iteration=state.iteration, tool_calls=len(response.tool_calls))

            if response.tool_calls:
                state.transition(AgentPhase.EXECUTE)
                state.messages.append(self._tool_call_message(response))
                for call in response.tool_calls:
                    state.tool_calls.append(redact_data({"id": call.id, "name": call.name, "arguments": call.arguments}))
                    spec = self.registry.get(call.name)
                    if spec is None:
                        result = {"ok": False, "error": f"Unknown tool: {call.name}"}
                    else:
                        decision = spec.permission
                        if call.name == "run_command":
                            decision = self.registry.permissions.classify_command(str(call.arguments.get("command", "")))
                        allowed = self.approval.allows(decision, call.name, json.dumps(redact_data(call.arguments)))
                        if not allowed:
                            result = {"ok": False, "error": "Tool call was not approved by the user."}
                            state.transition(AgentPhase.BLOCKED)
                        else:
                            self.events.emit("tool.started", tool=call.name)
                            self.ui.status(self._status_for_tool(call.name, call.arguments))
                            result = self.registry.execute(call.name, call.arguments)
                            self.events.emit("tool.completed" if result.get("ok") else "tool.failed", tool=call.name)
                            if result.get("ok") and call.name in {"write_file", "edit_file", "line_edit", "apply_patch", "delete_file", "move_file"}:
                                file_path = result.get("result", {}).get("path")
                                if file_path and not result.get("result", {}).get("dry_run"):
                                    state.changed_files.add(str(file_path))
                    result = redact_data(result)
                    state.tool_results.append(result)
                    state.messages.append({
                        "role": "tool",
                        "tool_call_id": call.id,
                        "content": json.dumps(result),
                    })
                continue

            state.final_response = redact_text(response.content.strip()) or "The model returned no final response."
            if state.changed_files:
                state.transition(AgentPhase.VERIFY)
                self.events.emit("verification.started")
                verification = Verifier(
                    self.settings.cwd,
                    self.settings.command_timeout,
                    max_output_size=self.settings.max_output_size,
                ).run()
                self.events.emit("verification.completed", passed=verification.passed)
                state.verification_results = [
                    {
                        "category": check.category,
                        "command": check.command,
                        "passed": check.passed,
                        "output": check.output,
                        "errors": check.errors,
                    }
                    for check in verification.checks
                ]
                if not verification.passed and repair_attempts < self.settings.max_repair_attempts:
                    repair_attempts += 1
                    state.repair_attempts = repair_attempts
                    state.transition(AgentPhase.REPAIR)
                    failure = (
                        f"Automatic verification failed using `{verification.command}`.\n"
                        f"Errors: {redact_data(verification.errors)}\nOutput:\n{redact_text(verification.output)}\n"
                        "Inspect the failure and repair it with the available tools. Do not claim success yet."
                    )
                    state.messages.append({"role": "user", "content": failure})
                    self.ui.status(f"Verification failed; repair attempt {repair_attempts}/{self.settings.max_repair_attempts}...")
                    continue
                if not verification.passed:
                    state.errors.extend(redact_data(verification.errors))
                    state.final_response += f"\n\nVerification failed: {redact_data(verification.errors)}"
                    state.transition(AgentPhase.FAILED)
                else:
                    state.transition(AgentPhase.COMPLETE)
            else:
                state.transition(AgentPhase.COMPLETE)
            self.events.emit("agent.completed", success=state.phase == AgentPhase.COMPLETE)
            return state

        state.errors.append(f"Maximum iteration count reached ({self.settings.max_iterations}).")
        state.final_response = "I stopped because the maximum agent iteration count was reached."
        state.transition(AgentPhase.FAILED)
        self.events.emit("agent.completed", success=False, error="max_iterations")
        return state

    @staticmethod
    def _status_for_tool(name: str, arguments: dict[str, Any]) -> str:
        labels = {
            "read_file": "Reading",
            "write_file": "Writing",
            "edit_file": "Editing",
            "list_directory": "Listing",
            "search_files": "Searching",
            "run_command": "Running command",
            "run_tests": "Running tests",
            "git_status": "Checking Git status",
            "git_diff": "Reviewing Git diff",
            "git_log": "Reading Git history",
        }
        suffix = arguments.get("path") or arguments.get("command") or ""
        return f"{labels.get(name, name)} {suffix}".strip()