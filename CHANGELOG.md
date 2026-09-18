# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- None yet.

## [0.1.0] - 2026-03-24

### Added
- Universal Agent-Native CLI Adapter (`shim` console script).
- `--json` flag to auto-discover and inject known CLI JSON output flags.
- `--non-interactive` flag to append `--yes`, `--quiet`, or non-interactive options.
- `--manifest` flag to inspect and parse CLI capabilities from `--help` output.
- Automatic agent detection via environment variables (`CLAUDECODE`, `AI_AGENT`, etc.).
- ANSI escape code stripping on stdout for machine-readable output in agent mode.
- Clean machine-readable error reporting on stderr with dumb terminal emulation (`TERM=dumb`).
