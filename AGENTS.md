# AGENTS.md — gemini-cli-mcp-slim

This file gives AI coding agents (Claude Code, Codex, Cursor, Gemini CLI, etc.)
the project-specific context required to work on this repository. Claude Code
reads it via `CLAUDE.md`, which is a one-line `@AGENTS.md` import shim.

## What this project is

A **thin bridge** that exposes Google's Gemini CLI to MCP clients (Claude Code,
Codex MCP, Cursor MCP, and other tools that speak MCP).

- **Inputs**: MCP tools (`consult_gemini`, `consult_gemini_with_files`, `web_search`)
- **Outputs**: argv-list subprocess invocation of the `gemini` CLI
  (the binary path is configurable via `$GEMINI_CMD`)

History management, caching, streaming, and similar higher-level features are
**deliberately not provided**. The killer feature is cross-repository analysis
via `directory` (cwd) + `include_directories`.

## Architectural decisions (load-bearing principles)

The author started this project from "**don't blindly route your prompts and
code through someone else's wrapper**." Recent supply-chain incidents
(`xz-utils` backdoor, `postmark-mcp` typosquat, npm `chalk`/`debug` compromise)
inform every design choice; **default toward auditability**.

- **Auditable**: the core implementation is a single file
  (`src/gemini_cli_mcp_slim/server.py`, ~290 lines) that anyone can read
  end-to-end in 30 minutes. If a feature would meaningfully grow this size,
  prefer **dropping or omitting** the feature over splitting the file.
- **Minimum dependencies**: `[project].dependencies` in `pyproject.toml` is
  **`mcp>=1.0.0` only**. Adding a direct dependency expands supply-chain
  surface; always check whether the standard library can do the job first.
- **Forward-compatible**: known flags are typed parameters; unknown / rare
  flags flow through `extra_args: string[]` verbatim. The server should not
  need to be re-released every time the upstream `gemini` CLI grows a new flag.
- **Transparent**: every subprocess invocation logs its full argv to stderr
  (`logger.info("exec %s ...")`).
- **No shell**: always use `asyncio.create_subprocess_exec` with an argv list.
  `shell=True` and string-concatenated commands are forbidden.
- **Configurable binary**: keep `$GEMINI_CMD` working so users can swap or
  wrap the `gemini` binary.

## Build / test / lint

`uv` is the local development driver (with `.venv/`); Docker is not used. CI
(`.github/workflows/ci.yml`) installs the same `optional-dependencies` groups
via `pip`, so local and CI use the same dependency set.

```bash
uv sync --extra test --extra dev      # local (uses uv.lock)
pip install -e ".[test,dev]"          # mirrors CI
.venv/bin/pytest tests/ -v
.venv/bin/ruff check .
.venv/bin/ruff format .
```

**Required before commit**: `pytest` and `ruff check` both green.
A type checker (`mypy` / `pyright`) is intentionally not configured at this
size — if you want to add one, first verify it does not conflict with the
"minimum dependencies" principle.

## Release flow

The package is published to PyPI via Trusted Publishing
(`.github/workflows/publish.yml`), triggered by pushing a `v*` tag.

- The single source of truth for the version is `pyproject.toml`'s
  `[project].version`. Bump it in the same PR as the change.
- `src/gemini_cli_mcp_slim/__init__.py` exposes `__version__` via
  `importlib.metadata`, so it follows `pyproject.toml` automatically.
- After merge: `git tag vX.Y.Z && git push origin vX.Y.Z`. The publish workflow
  picks it up.
- `CHANGELOG.md` follows Keep a Changelog; add a new entry per release.

## Common gotchas

### Never let the subprocess inherit the parent's stdin (this is fatal)

When the server runs over the **MCP stdio transport** (which is how every MCP
client launches it today), the parent process's stdin is the **JSON-RPC
channel**. If the gemini child inherits that stdin (`stdin=None`), the
JSON-RPC channel is corrupted and the server exits silently with `rc=0`
(clients see a "disconnected" MCP server).

- **Required**: pass `asyncio.subprocess.DEVNULL` whenever `stdin_text` is `None`.
- The full mechanism (Node.js applies `FIONBIO` on stdin; FIONBIO is set on the
  open file description and propagates to every FD that shares it, including
  the parent server's stdin FD) is documented in the inline "Why" comment in
  `src/gemini_cli_mcp_slim/server.py`.
- Regression test: `tests/test_subprocess_stdin_isolation.py`.

### Don't swallow `FileNotFoundError`

If `$GEMINI_CMD` points to an empty string or a non-existent path, return an
error dict (`ok: False`) that **includes the argv** so users can diagnose what
was attempted. Silently masking the exception removes any signal about why
the tool isn't working.

### Treat "add a direct dependency" as a re-think trigger

Per the "minimum dependencies" principle above, anything beyond `mcp` should
be weighed against a few dozen lines of standard-library code first.

## References

- Author's design notes (Japanese, Zenn):
  <https://zenn.dev/tksfjt1024/articles/ce256accbd3f81>
- Public docs: `README.md`
- License: `LICENSE` (MIT)
