"""Tests for cli-shim"""
import os
import sys
import json
import shutil
import pytest

# Add parent dir to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from cli_shim import (
    strip_ansi,
    split_output,
    make_non_interactive,
    discover_json_flag,
    inject_json_flag,
    discover_manifest,
    is_agent_mode,
    run_shim,
    ShimResult,
    ANSI_ESCAPE,
)


class TestStripAnsi:
    def test_simple_color(self):
        assert strip_ansi("\x1b[31mHello\x1b[0m") == "Hello"
    
    def test_multiple_codes(self):
        assert strip_ansi("\x1b[1;31;40mBold Red\x1b[0m") == "Bold Red"
    
    def test_no_ansi(self):
        assert strip_ansi("Hello World") == "Hello World"
    
    def test_empty(self):
        assert strip_ansi("") == ""
    
    def test_cursor_movement(self):
        assert strip_ansi("\x1b[2J\x1b[HClear screen") == "Clear screen"


class TestSplitOutput:
    def test_agent_mode_strips_ansi(self):
        stdout, stderr = split_output("\x1b[31mData\x1b[0m", "\x1b[31mError\x1b[0m", True)
        assert stdout == "Data"
        assert stderr == "Error"
    
    def test_human_mode_keeps_ansi(self):
        stdout, stderr = split_output("\x1b[31mData\x1b[0m", "\x1b[31mError\x1b[0m", False)
        assert "\x1b[31m" in stdout
        assert "\x1b[31m" in stderr


class TestMakeNonInteractive:
    def test_npm(self):
        assert make_non_interactive(["npm", "install"]) == ["npm", "--yes", "install"]
    
    def test_gh(self):
        assert make_non_interactive(["gh", "pr", "list"]) == ["gh", "--yes", "pr", "list"]
    
    def test_pnpm(self):
        assert make_non_interactive(["pnpm", "add", "lodash"]) == ["pnpm", "--yes", "add", "lodash"]
    
    def test_gcloud(self):
        assert make_non_interactive(["gcloud", "app", "deploy"]) == ["gcloud", "--quiet", "app", "deploy"]
    
    def test_unknown_fallback(self):
        result = make_non_interactive(["mytool", "subcmd"])
        assert result == ["mytool", "--yes", "subcmd"]
    
    def test_already_has_flag(self):
        result = make_non_interactive(["npm", "--yes", "install"])
        assert result.count("--yes") == 1
    
    def test_empty(self):
        # Empty input returns empty (nothing to make non-interactive)
        assert make_non_interactive([]) == []
    
    def test_single_cmd(self):
        assert make_non_interactive(["npm"]) == ["npm", "--yes"]


class TestDiscoverJsonFlag:
    def test_gh(self):
        assert discover_json_flag(["gh", "pr", "list"]) == "--json"
    
    def test_kubectl(self):
        assert discover_json_flag(["kubectl", "get", "pods"]) == "-o=json"
    
    def test_already_present(self):
        assert discover_json_flag(["gh", "pr", "list", "--json"]) is None
    
    def test_unknown(self):
        assert discover_json_flag(["mytool"]) == "--json"
    
    def test_empty(self):
        assert discover_json_flag([]) == "--json"


class TestInjectJsonFlag:
    def test_simple(self):
        result = inject_json_flag(["gh", "pr", "list"], "--json")
        assert result == ["gh", "pr", "--json", "list"]
    
    def test_no_subcommand(self):
        result = inject_json_flag(["gh"], "--json")
        assert result == ["gh", "--json"]
    
    def test_flag_before_subcommand(self):
        # When first arg is a flag, insert after command name
        result = inject_json_flag(["gh", "--repo", "owner/repo", "pr", "list"], "--json")
        assert result == ["gh", "--json", "--repo", "owner/repo", "pr", "list"]


class TestDiscoverManifest:
    def test_git_manifest(self):
        import shutil
        git_path = shutil.which("git")
        if git_path:
            manifest = discover_manifest(git_path)
            assert manifest["name"] == "git"
            assert isinstance(manifest["commands"], list)
            assert len(manifest["commands"]) > 0
    
    def test_echo_manifest(self):
        echo_path = shutil.which("echo")
        if echo_path:
            manifest = discover_manifest(echo_path)
            assert manifest["name"] == "echo"


class TestIsAgentMode:
    def test_no_env(self):
        # Should return False in normal test environment
        for var in ["CLAUDECODE", "AI_AGENT", "OPENCLAW_AGENT", "CODEX_SESSION"]:
            os.environ.pop(var, None)
        assert is_agent_mode() is False
    
    def test_with_env(self):
        os.environ["CLAUDECODE"] = "1"
        try:
            assert is_agent_mode() is True
        finally:
            del os.environ["CLAUDECODE"]


class TestShimResult:
    def test_success(self):
        r = ShimResult(0, "output", "", ["echo", "output"])
        assert r.success is True
    
    def test_failure(self):
        r = ShimResult(1, "", "error", ["false"])
        assert r.success is False
    
    def test_to_dict(self):
        r = ShimResult(0, "out", "err", ["cmd"])
        d = r.to_dict()
        assert d["returncode"] == 0
        assert d["stdout"] == "out"
        assert d["stderr"] == "err"
        assert d["command"] == ["cmd"]
    
    def test_print_json(self, capsys):
        r = ShimResult(0, "hello", "", ["echo", "hello"])
        r.print_json()
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["success"] is True


class TestRunShim:
    def test_echo_command(self):
        result = run_shim(["echo", "hello world"], agent_mode=True, timeout=5)
        assert result.success is True
        assert "hello world" in result.stdout
    
    def test_false_command(self):
        result = run_shim(["false"], agent_mode=True, timeout=5)
        assert result.success is False
        assert result.returncode == 1
    
    def test_nonexistent_command(self):
        result = run_shim(["nonexistentcmd123"], agent_mode=True, timeout=5)
        assert result.returncode == 127
        assert "not found" in result.stderr
    
    def test_with_json_flag(self):
        # echo doesn't have JSON but shouldn't crash
        result = run_shim(["echo", '{"key": "value"}'], agent_mode=True, force_json=True, timeout=5)
        assert result.returncode == 0
    
    def test_non_interactive_flag(self):
        result = run_shim(["echo", "test"], agent_mode=True, non_interactive=True, timeout=5)
        assert result.success is True


class TestAnsiRegex:
    def test_matches_color(self):
        assert ANSI_ESCAPE.search("\x1b[31m") is not None
    
    def test_matches_cursor(self):
        assert ANSI_ESCAPE.search("\x1b[2J") is not None
    
    def test_no_match(self):
        assert ANSI_ESCAPE.search("normal text") is None


class TestExpandedCLIRegistry:
    def test_docker_json(self):
        assert discover_json_flag(["docker", "ps"]) == "--format=json"
class TestKnownCLIRegistry:
    def test_all_requested_clis_are_registered(self):
        from cli_shim import KNOWN_CLI_MAP

        expected = {
            "docker",
            "docker-compose",
            "kubectl",
            "helm",
            "kustomize",
            "aws",
            "gcloud",
            "az",
            "npm",
            "yarn",
            "pnpm",
            "pip",
            "cargo",
            "make",
            "cmake",
            "ninja",
        }

        assert expected.issubset(KNOWN_CLI_MAP)

    def test_package_managers(self):
        from cli_shim import KNOWN_CLI_MAP

        assert KNOWN_CLI_MAP["npm"] == "Package Manager"
        assert KNOWN_CLI_MAP["yarn"] == "Package Manager"
        assert KNOWN_CLI_MAP["pnpm"] == "Package Manager"
        assert KNOWN_CLI_MAP["pip"] == "Package Manager"
        assert KNOWN_CLI_MAP["cargo"] == "Package Manager"

    def test_build_tools(self):
        from cli_shim import KNOWN_CLI_MAP

        assert KNOWN_CLI_MAP["make"] == "Build Tool"
        assert KNOWN_CLI_MAP["cmake"] == "Build Tool"
        assert KNOWN_CLI_MAP["ninja"] == "Build Tool"
    def test_docker_compose_json(self):
        assert discover_json_flag(["docker-compose", "ps"]) == "--format=json"

    def test_kubernetes_clis_json(self):
        assert discover_json_flag(["kubectl", "get", "pods"]) == "-o=json"
        assert discover_json_flag(["helm", "list"]) == "--output=json"
        assert discover_json_flag(["kustomize", "build", "."]) == "--output=json"

    def test_cloud_clis_json(self):
        assert discover_json_flag(["aws", "ec2", "describe-instances"]) == "--output=json"
        assert discover_json_flag(["gcloud", "compute", "instances", "list"]) == "--format=json"
        assert discover_json_flag(["az", "vm", "list"]) == "--output=json"

    def test_package_managers_json(self):
        assert discover_json_flag(["npm", "list"]) == "--json"
        assert discover_json_flag(["yarn", "info"]) == "--json"
        assert discover_json_flag(["pnpm", "list"]) == "--json"
