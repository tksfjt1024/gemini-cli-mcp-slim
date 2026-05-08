# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.1] - 2026-05-08

### Fixed
- Critical: subprocess `stdin` was inheriting the parent stdin, which over the
  MCP stdio transport corrupted the JSON-RPC channel and silently killed the
  server (rc=0) under parallel invocation. The child now uses
  `asyncio.subprocess.DEVNULL` when no stdin payload is provided.
  See `CLAUDE.md` "Common gotchas" and `tests/test_subprocess_stdin_isolation.py`
  for the FIONBIO file-description propagation mechanism behind this.

### Added
- `tests/test_subprocess_stdin_isolation.py`: regression tests guarding the
  stdin DEVNULL invariant and a light parallel smoke test.
- `AGENTS.md`: cross-agent project guide (architectural decisions, build/test
  commands, release flow, common gotchas). Follows the agents.md convention
  (Linux Foundation Agentic AI Foundation), readable by Claude Code, Codex,
  Cursor, and other AI coding agents.
- `CLAUDE.md`: one-line `@AGENTS.md` import shim so Claude Code reads the
  same project guide without duplication.
- `.gitignore`: per-developer Claude Code state per the Anthropic SDK
  convention (`CLAUDE.local.md`, `.claude/worktrees/`,
  `.claude/settings.local.json`, `.claude/agent-memory-local/`). Shared
  `.claude/` config (settings, rules, skills, agents, commands) stays tracked
  when added.
- `__version__` exposed from the package root via `importlib.metadata`.

### Changed
- `README.md`: line-count references updated from `~270` to `~290` to match
  the current `server.py`.

## [0.1.0] - 2026-05-02

### Added
- Initial release.
- MCP tools: `consult_gemini`, `consult_gemini_with_files`, `web_search`.
- Forward-compatible `extra_args` passthrough for unknown gemini CLI flags.
- `$GEMINI_CMD` for swapping the gemini binary path.

[Unreleased]: https://github.com/tksfjt1024/gemini-cli-mcp-slim/compare/v0.1.1...HEAD
[0.1.1]: https://github.com/tksfjt1024/gemini-cli-mcp-slim/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/tksfjt1024/gemini-cli-mcp-slim/releases/tag/v0.1.0
