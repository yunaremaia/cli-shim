# cli-shim

> Universal Agent-Native CLI Adapter — makes legacy CLIs agent-friendly

`cli-shim` wraps any command-line tool and makes it safe and predictable for AI agents (Claude Code, Codex, Cursor, OpenClaw, Hermes, etc.) to use.

## The Problem

AI agents increasingly call CLI tools, but most CLIs were designed for humans:

- **Interactive prompts** block agents that can't type into a TTY
- **Color codes and ANSI noise** pollute structured output
- **No `--json` flag** means agents must parse human-readable tables
- **Inconsistent output** between agents and humans wastes tokens

Cloudflare rebuilt Wrangler, HuggingFace rebuilt `hf`, and Railway tracks specific gaps — all confirming this is a real, widespread problem. `cli-shim` solves it universally.

## Install

```bash
pip install cli-shim
```

## Usage

```bash
# Wrap any command for agent use
shim railway service create --env production

# Force JSON output (auto-discovers the right flag)
shim --json gh pr list --repo owner/repo

# Make non-interactive (auto-adds --yes, --quiet, etc.)
shim --non-interactive terraform apply

# Discover what a CLI supports
shim --manifest kubectl
# → {"commands": [...], "json_flag": "-o=json", ...}
```

## Features

| Feature | What it does |
|---------|--------------|
| `--json` | Auto-discovers and injects the CLI's JSON flag |
| `--non-interactive` | Adds `--yes`/`--quiet` flags to prevent prompts |
| `--manifest` | Parses `--help` to discover capabilities |
| Agent auto-detect | Sets mode when `CLAUDECODE`, `AI_AGENT`, etc. are set |
| ANSI stripping | Separates data (stdout) from decoration (stderr) |
| Clean errors | Machine-readable error output on stderr |

## How It Works

1. Detects if running inside an agent (env vars) or human terminal
2. Looks up the command in a known-CLI registry for flags
3. Injects `--json` / `--yes` / `--quiet` as needed
4. Runs with `TERM=dumb` to prevent fancy output
5. Strips ANSI from stdout in agent mode (keeps it for humans)

## Supported CLIs

The known-CLI registry includes common tools with known agent-friendly output flags:

- **Docker:** `docker`, `docker-compose`
- **Kubernetes:** `kubectl`, `helm`, `kustomize`
- **Cloud providers:** `aws`, `gcloud`, `az`
- **Package managers:** `npm`, `yarn`, `pnpm`, `pip`, `cargo`
- **Build tools:** `make`, `cmake`, `ninja`
- **Infrastructure:** `terraform`, `pulumi`
- **Other CLIs:** `gh`, `railway`, `vercel`, `netlify`, `stripe`, `linear`, `jira`, `databricks`

JSON output flags are configured only for CLIs that provide a supported JSON output option. Tools without a standard JSON output flag remain available through the known-CLI registry without an invented JSON flag.

## Examples

```bash
# In an agent context, auto-detects and normalizes:
export CLAUDECODE=1
shim gh pr list --repo vercel/ai
# → Pure JSON on stdout, clean stderr

# Force non-interactive for Terraform:
shim --non-interactive terraform apply -auto-approve

# Discover Railway capabilities:
shim --manifest railway
# → {"name": "railway", "commands": [...], "json_flag": "--json"}
```

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, architecture details, and a step-by-step guide on adding new CLIs to the registry.

## License

MIT — Yunare Maia, 2026
