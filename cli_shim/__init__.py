"""
cli-shim: Universal Agent-Native CLI Adapter
Makes legacy CLI tools agent-friendly with clean output, auto-prompts, and JSON normalization.

Public: MIT License, signed "Yunare Maia"
"""

__version__ = "0.1.0"

import os
import sys
import json
import re
import subprocess
import shutil
from typing import Optional, Dict, List, Any


# ─── Agent Environment Detection ────────────────────────────────────────────

AGENT_ENV_VARS = ["CLAUDECODE", "AI_AGENT", "OPENCLAW_AGENT", "CODEX_SESSION", "HERMES_CRON"]
JSON_FLAGS = ["--json", "--output=json", "-j", "-ojson", "--format=json"]
NON_INTERACTIVE_FLAGS = ["--yes", "--non-interactive", "-y", "--no-input", "--quiet", "-q"]
ANSI_ESCAPE = re.compile(r'\x1b\[[0-9;]*[mGKHF]|\x1b\[.*?[a-zA-Z]|\x1b\[2J|\x1b\[H')


def is_agent_mode() -> bool:
    """Detect if running inside an AI agent context."""
    return any(os.environ.get(var) for var in AGENT_ENV_VARS)


def is_interactive_terminal() -> bool:
    """Check if stdin/stdout are connected to a terminal."""
    return sys.stdin.isatty() and sys.stdout.isatty()


# ─── Output Normalization ──────────────────────────────────────────────────

def strip_ansi(text: str) -> str:
    """Remove ANSI escape sequences from text."""
    return ANSI_ESCAPE.sub('', text)


def split_output(raw_stdout: str, raw_stderr: str, agent_mode: bool) -> tuple:
    """
    Normalize CLI output:
    - Pure data → stdout (for agent parsing)
    - ANSI-decorated tables/progress → stderr (for humans)
    - Errors → stderr
    """
    clean_stdout = strip_ansi(raw_stdout) if agent_mode else raw_stdout
    clean_stderr = strip_ansi(raw_stderr) if agent_mode else raw_stderr
    return clean_stdout, clean_stderr
    # Known CLI registry
KNOWN_CLI_MAP = {
    "docker": "Docker",
    "docker-compose": "Docker",
    "kubectl": "Kubernetes",
    "helm": "Kubernetes",
    "kustomize": "Kubernetes",
    "aws": "Cloud",
    "gcloud": "Cloud",
    "az": "Cloud",
    "npm": "Package Manager",
    "yarn": "Package Manager",
    "pnpm": "Package Manager",
    "pip": "Package Manager",
    "cargo": "Package Manager",
    "make": "Build Tool",
    "cmake": "Build Tool",
    "ninja": "Build Tool",
}

# ─── Interactive Prompt Handling ────────────────────────────────────────────

def make_non_interactive(cmd: List[str]) -> List[str]:
    """
    Return command with non-interactive flags inserted after the subcommand.
    Uses known flags from a small registry, falls back to --yes.
    """
    # Map of base commands to their non-interactive flag
    NON_INTERACTIVE_MAP = {
        "npm": ["--yes"],
        "pnpm": ["--yes"],
        "yarn": ["--non-interactive"],
        "brew": ["--yes"],
        "apt": ["-y"],
        "apt-get": ["-y"],
        "gh": ["--yes"],
        "gcloud": ["--quiet"],
        "kubectl": ["--yes"],
        "helm": ["--yes"],
        "docker": [],  # No global non-interactive flag
        "railway": ["--yes"],
        "vercel": ["--yes"],
        "netlify": ["--yes"],
        "terraform": ["-auto-approve"],
        "docker-compose": [],
    }
    
    if not cmd:
        return []
    
    base = cmd[0]
    # Handle paths like /usr/bin/gh
    base_name = os.path.basename(base)
    
    flags = NON_INTERACTIVE_MAP.get(base_name, ["--yes"])
    
    # Find insertion point: after first argument (subcommand)
    if len(cmd) >= 2:
        # Don't add if already present
        existing_flags = set(cmd[1:])
        new_flags = [f for f in flags if f not in existing_flags]
        return [cmd[0]] + new_flags + cmd[1:]
    return cmd + flags


# ─── JSON Output Discovery ──────────────────────────────────────────────────

def discover_json_flag(cmd: List[str]) -> Optional[str]:
    """
    Try to find the JSON output flag for a CLI.
    Returns the flag to insert, or None.
    """
    base = os.path.basename(cmd[0]) if cmd else ""
    
    # Known JSON flags per CLI
    JSON_MAP = {
        "gh": "--json",
        "kubectl": "-o=json",
        "docker": "--format=json",
        "docker-compose": "--format=json",
        "npm": "--json",
        "yarn": "--json",
        "pnpm": "--json",
        "gcloud": "--format=json",
        "aws": "--output=json",
        "az": "--output=json",
        "helm": "--output=json",
        "kustomize": "--output=json",
        "terraform": "-json",
        "pulumi": "--json",
        "railway": "--json",
        "vercel": "--json",
        "netlify": "--json",
        "stripe": "--json",
        "linear": "--json",
        "jira": "--json",
        "databricks": "--output=JSON",
    }
    
    if base in JSON_MAP:
        flag = JSON_MAP[base]
        # Check if already present
        if flag not in cmd:
            return flag
    
    # Fallback: try --json
    if "--json" not in cmd:
        return "--json"
    
    return None


def inject_json_flag(cmd: List[str], flag: str) -> List[str]:
    """Insert JSON flag into command after the subcommand."""
    if not cmd:
        return cmd
    
    # Insert after first arg (subcommand) if exists
    if len(cmd) >= 2 and not cmd[1].startswith("-"):
        return [cmd[0], cmd[1]] + [flag] + cmd[2:]
    return [cmd[0], flag] + cmd[1:]


# ─── CLI Manifest Discovery ─────────────────────────────────────────────────

def discover_manifest(cmd_path: str) -> Dict[str, Any]:
    """
    Try to discover CLI capabilities by parsing --help output.
    Returns a structured manifest.
    """
    manifest = {
        "name": os.path.basename(cmd_path),
        "path": cmd_path,
        "commands": [],
        "json_flag": None,
        "non_interactive_flag": None,
        "help_text": "",
    }
    
    # Try --help
    try:
        result = subprocess.run(
            [cmd_path, "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        help_text = result.stdout + result.stderr
        manifest["help_text"] = help_text[:2000]  # Truncate
        
        # Extract commands from common help patterns
        # Pattern: "Commands:" or "Available Commands:" followed by indented list
        cmd_patterns = [
            r'(?:Commands|Available Commands|SUBCOMMANDS):\s*\n((?:\s+\S+.*\n)+)',
            r'^\s{2,}(\S+)\s{2,}.*$',  # Generic indented subcommand
        ]
        
        for pattern in cmd_patterns:
            matches = re.findall(pattern, help_text, re.MULTILINE)
            if matches:
                first = matches[0]
                if isinstance(first, tuple):
                    # Multi-line block match
                    block = first[0] if first else ""
                    for line in block.strip().split('\n'):
                        cmd_match = re.match(r'\s+(\S+)', line)
                        if cmd_match:
                            manifest["commands"].append({
                                "name": cmd_match.group(1),
                                "description": line.strip(),
                            })
                else:
                    for m in matches:
                        if isinstance(m, str):
                            manifest["commands"].append({
                                "name": m,
                                "description": "",
                            })
                break
        
        # Detect JSON flag in help
        json_hint_patterns = [
            r'(--json\b|-o=json\b|--output=json\b|--format=json\b)',
            r'(output format).*?(json)',
            r'JSON\s+output',
        ]
        for pat in json_hint_patterns:
            m = re.search(pat, help_text, re.IGNORECASE)
            if m:
                manifest["json_flag"] = m.group(1) if m.lastindex else "--json"
                break
        
        # Detect non-interactive flag
        non_int_patterns = [
            r'(--yes\b|-y\b|--non-interactive\b|--no-input\b|--quiet\b)',
        ]
        for pat in non_int_patterns:
            m = re.search(pat, help_text)
            if m:
                manifest["non_interactive_flag"] = m.group(1)
                break
        
    except (subprocess.TimeoutExpired, FileNotFoundError, PermissionError):
        pass
    
    return manifest


# ─── Execution Engine ───────────────────────────────────────────────────────

class ShimResult:
    def __init__(self, returncode: int, stdout: str, stderr: str, command: List[str]):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        self.command = command
    
    @property
    def success(self) -> bool:
        return self.returncode == 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "command": self.command,
            "returncode": self.returncode,
            "success": self.success,
            "stdout": self.stdout,
            "stderr": self.stderr,
        }
    
    def print_json(self):
        print(json.dumps(self.to_dict(), indent=2, ensure_ascii=False))
    
    def print_human(self):
        if self.stdout:
            print(self.stdout, end='')
        if self.stderr:
            print(self.stderr, end='', file=sys.stderr)


def run_shim(
    cmd: List[str],
    agent_mode: Optional[bool] = None,
    force_json: bool = False,
    non_interactive: bool = False,
    dry_run: bool = False,
    timeout: int = 120,
) -> ShimResult:
    """
    Execute a command with agent-friendly normalization.
    
    Args:
        cmd: Command and arguments to execute
        agent_mode: Override auto-detection
        force_json: Force JSON output flag if CLI supports it
        non_interactive: Auto-add non-interactive flags
        timeout: Execution timeout in seconds
    """
    if agent_mode is None:
        agent_mode = is_agent_mode() or not is_interactive_terminal()
    
    # Apply non-interactive mode
    if non_interactive:
        cmd = make_non_interactive(cmd)
    
    # Inject JSON flag
    if force_json:
        json_flag = discover_json_flag(cmd)
        if json_flag:
            cmd = inject_json_flag(cmd, json_flag)
    
    # Dry-run mode: print command without execution
    if dry_run:
        print(" ".join(cmd))
        return ShimResult(0, "", "", cmd)
    
    # Resolve command path
    cmd_path = shutil.which(cmd[0]) if cmd else None
    if not cmd_path:
        return ShimResult(127, "", f"Command not found: {cmd[0]}", cmd)
    
    # Execute
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env={**os.environ, "TERM": "dumb"},  # Dumb terminal = no fancy output
        )
        
        stdout, stderr = split_output(result.stdout, result.stderr, agent_mode)
        
        return ShimResult(result.returncode, stdout, stderr, cmd)
    
    except subprocess.TimeoutExpired:
        return ShimResult(124, "", f"Command timed out after {timeout}s", cmd)
    except Exception as e:
        return ShimResult(1, "", str(e), cmd)


# ─── CLI Entry Point ────────────────────────────────────────────────────────

def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        prog="shim",
        description="Universal Agent-Native CLI Adapter — makes legacy CLIs agent-friendly",
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    parser.add_argument(
        "--json", "-j",
        action="store_true",
        default=False,
        help="Force JSON output if the CLI supports it",
    )
    parser.add_argument(
        "--non-interactive", "-y",
        action="store_true",
        default=False,
        help="Auto-add non-interactive flags to prevent prompts",
    )
    parser.add_argument(
        "--manifest", "-m",
        action="store_true",
        default=False,
        help="Discover and output CLI manifest (JSON schema of capabilities)",
    )
    parser.add_argument(
        "--agent-mode",
        action="store_true",
        default=None,
        help="Force agent mode (auto-detected if not set)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=120,
        help="Command timeout in seconds (default: 120)",
    )
    parser.add_argument(
        "--raw",
        action="store_true",
        default=False,
        help="Raw output (no normalization, for humans)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Print command without executing",
    )
    parser.add_argument(
        "command",
        nargs=argparse.REMAINDER,
        help="Command to wrap (e.g., shim --json gh pr list)",
    )
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Strip leading -- if present (argparse quirk)
    cmd = args.command
    if cmd and cmd[0] == "--":
        cmd = cmd[1:]
    
    if not cmd:
        print("Error: no command provided", file=sys.stderr)
        sys.exit(1)
    
    # Manifest mode
    if args.manifest:
        cmd_path = shutil.which(cmd[0])
        if not cmd_path:
            print(json.dumps({"error": f"Command not found: {cmd[0]}"}), file=sys.stderr)
            sys.exit(127)
        manifest = discover_manifest(cmd_path)
        print(json.dumps(manifest, indent=2, ensure_ascii=False))
        sys.exit(0)
    
    # Run the command
    result = run_shim(
        cmd,
        agent_mode=args.agent_mode if args.agent_mode is not None else None,
        force_json=args.json,
        non_interactive=args.non_interactive,
        dry_run=args.dry_run,
        timeout=args.timeout,
    )
    
    # Output
    if args.json or (is_agent_mode() and not args.raw):
        result.print_json()
    else:
        result.print_human()
    
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
