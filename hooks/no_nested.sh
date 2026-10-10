#!/usr/bin/env bash
# no_nested.sh: PreToolUse guard (matcher: Bash). Stops a session from
# launching the Claude Code CLI itself.
#
# Why: running the CLI from inside a session doesn't run a subcommand. It can
# start a whole new LIVE session in the working directory, and that one loads
# CLAUDE.md, wakes up, and acts in the world: writes to memory, messages people.
# It happened to us through an innocent-looking "show me the config" command.
#
# Allowed: --version / -v / --help / -h, which print and exit.
#
# Known false positive, and we've decided to live with it: it doesn't parse
# shell quoting, so a | inside a quoted pattern followed by the binary's name
# (grep -E "foo|<name> code") looks like a pipe into the CLI and gets blocked.
# Annoying for a second. Rephrase the pattern. Missing a real launch would be worse.
# Exit 2 blocks the tool call and shows the message to the model.

raw="$(cat)"
[ -z "$raw" ] && exit 0
cmd="$(printf '%s' "$raw" | python3 -c "
import sys, json
try: print(json.load(sys.stdin).get('tool_input', {}).get('command', ''))
except Exception: print('')
" 2>/dev/null)"
[ -z "$cmd" ] && exit 0

T='cla''ude'   # split so this file doesn't match itself when grepped

if printf '%s' "$cmd" | grep -Eq "(^|[;&|(]|&&|\|\||\bsudo\b|\bnohup\b|\benv\b)[[:space:]]*([^[:space:]]*/)?${T}(\.exe)?([[:space:]]|$)"; then
    if printf '%s' "$cmd" | grep -Eq "([^[:space:]]*/)?${T}(\.exe)?[[:space:]]+(--version|-v|--help|-h)([[:space:]]|$)"; then
        exit 0
    fi
    cat >&2 << 'EOF'
Blocked: launching the CLI from inside a session can start a full LIVE nested
session that loads CLAUDE.md and acts in the world.
Instead: read ~/.claude.json or ~/.claude/settings.json for config, use
`command -v` to find the binary, and --version is allowed.
EOF
    exit 2
fi
exit 0
