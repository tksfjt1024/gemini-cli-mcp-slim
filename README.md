# gemini-cli-mcp-slim

A thin, auditable [MCP](https://modelcontextprotocol.io) server wrapping the [Gemini CLI](https://github.com/google-gemini/gemini-cli).

[![PyPI version](https://img.shields.io/pypi/v/gemini-cli-mcp-slim.svg)](https://pypi.org/project/gemini-cli-mcp-slim/)
[![Python versions](https://img.shields.io/pypi/pyversions/gemini-cli-mcp-slim.svg)](https://pypi.org/project/gemini-cli-mcp-slim/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CI](https://github.com/tksfjt1024/gemini-cli-mcp-slim/actions/workflows/ci.yml/badge.svg)](https://github.com/tksfjt1024/gemini-cli-mcp-slim/actions/workflows/ci.yml)

## Why

Existing Gemini MCP servers tend to either hide the underlying CLI behind opaque parameters or hard-code the supported flags so new gemini CLI options require code changes. This project takes a different approach:

- **Single file, ~290 lines** — auditable in one sitting
- **One third-party dependency** (`mcp`) — minimal supply-chain surface
- **Forward-compatible** — any new or uncommon gemini CLI flag is reachable via `extra_args` without touching this server
- **Configurable binary path** — `$GEMINI_CMD` lets you swap or wrap the gemini binary
- **Workspace-aware** — first-class `include_directories` so you can analyze multiple repositories from one invocation
- **Transparent** — every invocation logs the exact argv to stderr

## Installation

Requires the `gemini` CLI to be installed and on `$PATH` (or pointed to via `$GEMINI_CMD`).

```bash
# Run directly without installing
uvx gemini-cli-mcp-slim

# Install from PyPI
pip install gemini-cli-mcp-slim

# Run from GitHub HEAD
uvx --from git+https://github.com/tksfjt1024/gemini-cli-mcp-slim gemini-cli-mcp-slim
```

## Usage as an MCP server

### Claude Code

```bash
claude mcp add gemini-cli-mcp-slim uvx gemini-cli-mcp-slim
```

Or manually in `~/.claude.json`:

```json
{
  "mcpServers": {
    "gemini-cli-mcp-slim": {
      "type": "stdio",
      "command": "uvx",
      "args": ["gemini-cli-mcp-slim"]
    }
  }
}
```

### Other MCP clients

Any MCP-compatible client can launch the server via stdio:

```bash
uvx gemini-cli-mcp-slim
```

## Tools

### `consult_gemini`

Run a single Gemini CLI invocation with full forward-compatibility.

| Parameter             | Type     | Description                                                                          |
| --------------------- | -------- | ------------------------------------------------------------------------------------ |
| `query` (required)    | string   | Prompt sent verbatim to the gemini CLI                                               |
| `directory` (required)| string   | Working directory (gemini cwd, defines the default workspace root)                   |
| `model`               | string   | Model alias (`flash`, `pro`) or full model id                                        |
| `approval_mode`       | enum     | `default` / `auto_edit` / `yolo` / `plan`                                            |
| `include_directories` | string[] | Extra workspace directories (mapped to gemini `--include-directories`)               |
| `yolo`                | bool     | Pass `--yolo` (auto-approve all)                                                     |
| `sandbox`             | bool     | Pass `--sandbox`                                                                     |
| `extra_args`          | string[] | Raw CLI flags appended verbatim. Use to access new/uncommon gemini flags             |
| `env`                 | object   | Extra environment variables for the gemini subprocess                                |
| `timeout_seconds`     | int      | Subprocess timeout in seconds (default 600)                                          |

### `consult_gemini_with_files`

Same parameters as `consult_gemini` plus a `files: string[]` parameter. File paths are appended to the prompt as `@path` tokens (gemini's file reference syntax). Absolute paths inside `directory` are converted to relative `@`-paths.

### `web_search`

Convenience wrapper that prepends a "use your built-in web search" instruction to the query.

## Configuration

| Environment variable           | Default  | Purpose                                  |
| ------------------------------ | -------- | ---------------------------------------- |
| `GEMINI_CMD`                   | `gemini` | Path to the gemini CLI binary            |
| `GEMINI_CLI_MCP_SLIM_TIMEOUT`  | `600`    | Default subprocess timeout in seconds    |
| `GEMINI_CLI_MCP_SLIM_LOG_LEVEL`| `INFO`   | Logging level for stderr diagnostics     |

## Cross-repository analysis example

The killer feature: analyze multiple repositories from a single MCP invocation.

```jsonc
{
  "name": "consult_gemini",
  "arguments": {
    "query": "Compare the API surface between these services",
    "directory": "/path/to/service-a",
    "include_directories": [
      "/path/to/service-b",
      "/path/to/service-c"
    ],
    "model": "flash",
    "approval_mode": "plan"
  }
}
```

This launches gemini with `--include-directories=/path/to/service-b,/path/to/service-c`, giving the model read access to all three workspaces in one session.

## Forward-compatibility example

If a future gemini CLI release adds a new flag (say `--super-mode`), you can use it immediately without updating this server:

```jsonc
{
  "name": "consult_gemini",
  "arguments": {
    "query": "...",
    "directory": "...",
    "extra_args": ["--super-mode", "--some-other-new-flag"]
  }
}
```

## Comparison with alternatives

| Project                      | Lines | Deps              | `include_directories` | `extra_args` passthrough |
| ---------------------------- | ----- | ----------------- | --------------------- | ------------------------ |
| **gemini-cli-mcp-slim** (this) | ~290  | 1 (`mcp`)         | yes                   | yes                      |
| eLyiN/gemini-bridge          | ~400  | 1 (`mcp`)         | no                    | no                       |
| jamubc/gemini-mcp-tool       | (TS)  | many              | no                    | partial                  |

## Development

```bash
# Install dev dependencies
pip install -e ".[test,dev]"

# Lint
ruff check .

# Test
pytest
```

## License

[MIT](./LICENSE) © tksfjt1024
