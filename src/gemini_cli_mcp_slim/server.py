"""gemini_cli_mcp_slim: Thin, auditable MCP server wrapping the Gemini CLI.

Design goals:
  * Auditable: single file, ~200 lines, only one third-party dep (`mcp`).
  * Forward-compatible: any new gemini CLI flag is reachable via `extra_args`
    without server changes; the binary itself can be swapped via $GEMINI_CMD.
  * Safe: subprocess uses argv-list form (no shell), explicit cwd, hard timeout,
    explicit env merge. Each invocation logs the exact argv to stderr.
"""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

logger = logging.getLogger("gemini_cli_mcp_slim")

GEMINI_CMD = os.environ.get("GEMINI_CMD", "gemini")
DEFAULT_TIMEOUT = int(os.environ.get("GEMINI_CLI_MCP_SLIM_TIMEOUT", "600"))

server: Server = Server("gemini-cli-mcp-slim")


def _build_argv(
    *,
    query: str,
    model: str | None = None,
    approval_mode: str | None = None,
    include_directories: list[str] | None = None,
    yolo: bool = False,
    sandbox: bool = False,
    extra_args: list[str] | None = None,
) -> list[str]:
    argv: list[str] = [GEMINI_CMD, "--prompt", query]
    if model:
        argv += ["--model", model]
    if approval_mode:
        argv += ["--approval-mode", approval_mode]
    if include_directories:
        argv += ["--include-directories", ",".join(include_directories)]
    if yolo:
        argv.append("--yolo")
    if sandbox:
        argv.append("--sandbox")
    if extra_args:
        argv += list(extra_args)
    return argv


async def _run_gemini(
    *,
    cwd: str,
    argv: list[str],
    timeout: int,
    env_overrides: dict[str, str] | None = None,
    stdin_text: str | None = None,
) -> dict[str, Any]:
    cwd_path = Path(cwd).expanduser().resolve()
    if not cwd_path.is_dir():
        return {
            "ok": False,
            "error": f"directory does not exist: {cwd_path}",
            "argv": argv,
        }

    env = os.environ.copy()
    if env_overrides:
        env.update({k: str(v) for k, v in env_overrides.items()})

    logger.info("exec %s (cwd=%s, timeout=%ss)", argv, cwd_path, timeout)

    try:
        proc = await asyncio.create_subprocess_exec(
            *argv,
            cwd=str(cwd_path),
            stdin=asyncio.subprocess.PIPE if stdin_text is not None else None,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
    except FileNotFoundError as exc:
        return {"ok": False, "error": f"gemini binary not found: {exc}", "argv": argv}

    try:
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(stdin_text.encode() if stdin_text else None),
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        return {
            "ok": False,
            "error": f"timeout after {timeout}s",
            "argv": argv,
        }

    return {
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
        "stdout": stdout.decode("utf-8", errors="replace"),
        "stderr": stderr.decode("utf-8", errors="replace"),
        "argv": argv,
        "cwd": str(cwd_path),
    }


def _format_result(result: dict[str, Any]) -> str:
    if result["ok"]:
        return result["stdout"]
    parts = [f"[ERROR] {result.get('error', 'gemini failed')}"]
    if "returncode" in result:
        parts.append(f"returncode={result['returncode']}")
    if result.get("stderr"):
        parts.append(f"stderr:\n{result['stderr']}")
    parts.append(f"argv: {result.get('argv')}")
    if "cwd" in result:
        parts.append(f"cwd: {result['cwd']}")
    return "\n\n".join(parts)


_COMMON_PROPS: dict[str, Any] = {
    "query": {"type": "string", "description": "Prompt sent verbatim to gemini CLI."},
    "directory": {
        "type": "string",
        "description": "Working directory (gemini cwd). Defines the default workspace root.",
    },
    "model": {"type": "string", "description": "Model alias (flash, pro) or full model id."},
    "approval_mode": {
        "type": "string",
        "enum": ["default", "auto_edit", "yolo", "plan"],
        "description": "Maps to gemini --approval-mode.",
    },
    "include_directories": {
        "type": "array",
        "items": {"type": "string"},
        "description": (
            "Extra workspace directories. "
            "Maps to gemini --include-directories (comma-joined)."
        ),
    },
    "yolo": {"type": "boolean", "description": "Pass --yolo (auto-approve all)."},
    "sandbox": {"type": "boolean", "description": "Pass --sandbox."},
    "extra_args": {
        "type": "array",
        "items": {"type": "string"},
        "description": (
            "Raw CLI flags appended verbatim. "
            "Use to access new/uncommon gemini flags without updating this server."
        ),
    },
    "env": {
        "type": "object",
        "additionalProperties": {"type": "string"},
        "description": "Extra environment variables for the gemini subprocess.",
    },
    "timeout_seconds": {"type": "integer", "minimum": 10, "maximum": 3600},
}


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="consult_gemini",
            description=(
                "Run a single Gemini CLI invocation. Forward-compatible: unknown CLI flags can be "
                "passed via `extra_args`. The gemini binary path is configurable via $GEMINI_CMD."
            ),
            inputSchema={
                "type": "object",
                "properties": _COMMON_PROPS,
                "required": ["query", "directory"],
            },
        ),
        Tool(
            name="consult_gemini_with_files",
            description=(
                "Run Gemini with file references. "
                "Files inside `directory` (or its include_directories) "
                "are reachable via gemini's @-syntax appended to the query."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    **_COMMON_PROPS,
                    "files": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "File paths (absolute or relative to `directory`). "
                            "Appended as @path tokens to the prompt."
                        ),
                    },
                },
                "required": ["query", "directory", "files"],
            },
        ),
        Tool(
            name="web_search",
            description="Convenience wrapper that prepends a web-search instruction to the query.",
            inputSchema={
                "type": "object",
                "properties": _COMMON_PROPS,
                "required": ["query", "directory"],
            },
        ),
    ]


def _resolve_at_token(directory: str, file_path: str) -> str:
    p = Path(file_path)
    if p.is_absolute():
        try:
            rel = p.resolve().relative_to(Path(directory).expanduser().resolve())
            return f"@{rel}"
        except ValueError:
            return f"@{p}"
    return f"@{file_path}"


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    args = dict(arguments)
    query: str = args["query"]
    directory: str = args["directory"]
    timeout: int = int(args.get("timeout_seconds") or DEFAULT_TIMEOUT)

    if name == "consult_gemini_with_files":
        files = args.get("files") or []
        at_tokens = " ".join(_resolve_at_token(directory, f) for f in files)
        if at_tokens:
            query = f"{query}\n\n{at_tokens}"
    elif name == "web_search":
        query = (
            "Use your built-in web search capability to answer the following query. "
            "Cite sources where possible.\n\n" + query
        )
    elif name != "consult_gemini":
        return [TextContent(type="text", text=f"unknown tool: {name}")]

    argv = _build_argv(
        query=query,
        model=args.get("model"),
        approval_mode=args.get("approval_mode"),
        include_directories=args.get("include_directories"),
        yolo=bool(args.get("yolo", False)),
        sandbox=bool(args.get("sandbox", False)),
        extra_args=args.get("extra_args"),
    )

    result = await _run_gemini(
        cwd=directory,
        argv=argv,
        timeout=timeout,
        env_overrides=args.get("env"),
    )
    return [TextContent(type="text", text=_format_result(result))]


async def _amain() -> None:
    logging.basicConfig(
        level=os.environ.get("GEMINI_CLI_MCP_SLIM_LOG_LEVEL", "INFO"),
        format="[gemini-cli-mcp-slim] %(levelname)s %(message)s",
    )
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())


def main() -> None:
    asyncio.run(_amain())


if __name__ == "__main__":
    main()
