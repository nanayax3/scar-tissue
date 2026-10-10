#!/usr/bin/env bash
# session_end.sh: SessionEnd hook. A session that ends backs itself up.
#
# Why: our archive only swept once a night. A long thread died mid-morning and
# for seven and a half hours that whole morning existed only as one raw
# transcript file. Nothing was lost that day, but one copy is not a copy.
#
# It does NOT do the backup itself. It starts whatever already does (a
# systemd unit, a script, rsync) without waiting, so the hook returns at once
# and the session can close in peace. One code path for the nightly run and
# this one, so they can't drift apart.
#
# Set SCAR_TISSUE_EXPORT to the command, e.g.
#   SCAR_TISSUE_EXPORT="systemctl --user start --no-block my-archive.service"
#   SCAR_TISSUE_EXPORT="nohup ~/bin/backup-transcripts.sh"
# Debounced, because some setups end sessions in bursts.
# Always exits 0: a hook on the way out must never be a session's last error.
set -uo pipefail
cat >/dev/null 2>&1 || true            # drain the hook's JSON

HERE="$(cd "$(dirname "$0")/.." && pwd)"
FAIL="$HERE/.hook-failures.log"
STAMP="${TMPDIR:-/tmp}/scar-tissue/session-end.stamp"
DEBOUNCE="${SCAR_TISSUE_EXPORT_DEBOUNCE:-300}"

{
  [[ -z "${SCAR_TISSUE_EXPORT:-}" ]] && exit 0
  [[ -e "$HERE/OFF" ]] && exit 0
  mkdir -p "$(dirname "$STAMP")"
  now=$(date +%s); last=$(cat "$STAMP" 2>/dev/null || echo 0)
  (( now - last < DEBOUNCE )) && exit 0
  echo "$now" > "$STAMP"
  bash -c "$SCAR_TISSUE_EXPORT" >/dev/null 2>&1 &
  disown
} 2>>"$FAIL" || printf '%s session_end.sh: exit %s\n' "$(date '+%Y-%m-%d %H:%M')" "$?" >> "$FAIL" 2>/dev/null

exit 0
