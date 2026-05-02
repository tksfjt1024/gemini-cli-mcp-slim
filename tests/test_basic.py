"""Pure-function tests for argv construction. Subprocess execution is not tested here."""

from gemini_cli_mcp_slim.server import GEMINI_CMD, _build_argv, _resolve_at_token


def test_build_argv_minimal():
    argv = _build_argv(query="hello")
    assert argv == [GEMINI_CMD, "--prompt", "hello"]


def test_build_argv_include_directories_comma_joined():
    argv = _build_argv(query="q", include_directories=["/a", "/b", "/c"])
    idx = argv.index("--include-directories")
    assert argv[idx + 1] == "/a,/b,/c"


def test_build_argv_extra_args_appended_verbatim():
    argv = _build_argv(query="q", extra_args=["--skip-trust", "--debug"])
    assert argv[-2:] == ["--skip-trust", "--debug"]


def test_build_argv_all_typed_flags_combine():
    argv = _build_argv(
        query="q",
        model="flash",
        approval_mode="plan",
        include_directories=["/x"],
        yolo=True,
        sandbox=True,
        extra_args=["--custom"],
    )
    for token in ("--model", "flash", "--approval-mode", "plan",
                  "--include-directories", "/x", "--yolo", "--sandbox", "--custom"):
        assert token in argv


def test_resolve_at_token_relative_path_unchanged():
    assert _resolve_at_token("/workspace", "src/app.py") == "@src/app.py"


def test_resolve_at_token_absolute_inside_workspace_made_relative(tmp_path):
    nested = tmp_path / "sub" / "file.py"
    nested.parent.mkdir(parents=True)
    nested.write_text("")
    token = _resolve_at_token(str(tmp_path), str(nested))
    assert token == "@sub/file.py"


def test_resolve_at_token_absolute_outside_workspace_kept_absolute(tmp_path):
    other = tmp_path.parent / "outside.py"
    token = _resolve_at_token(str(tmp_path), str(other))
    assert token.startswith("@/")
