#!/usr/bin/env bash
# TAP-5291: forced-refresh flags must stay opt-in.
#
# The 2026-08-10 measurement found `--pull always --force-recreate` had been
# the DEFAULT in both start-stack entry points, silently turning every stack
# start into a full re-pull. The fix moved them behind STACK_REFRESH=1.
#
# Branch-aware static check (comments stripped before matching):
#   - Only the exact sanctioned guard opens an opt-in branch:
#       sh : if [[ "${STACK_REFRESH:-0}" == "1" ]]; then
#       ps1: if ($env:STACK_REFRESH -eq "1") {
#     A loosened conditional (e.g. -ne "__never__") is NOT recognized, so
#     flags inside it are flagged.
#   - A literal flag is legal only on a refresh-variable assignment line
#     inside that branch. sh tracks if/fi as words across `;`-separated
#     segments (one-liner `if ...; then ...; fi` included; code after a
#     closing `fi` on the same line counts as outside), counts keywords on
#     a string-stripped copy (an `if` inside a log message does not nest),
#     and skips heredoc bodies (unterminated heredoc fails CLOSED, and
#     here-strings/arithmetic `<<` are not treated as heredocs); ps1
#     tracks brace depth.
#   - Known limits of the static approach, deliberate: a `#` inside a
#     quoted sh string still truncates that line (N8); an unbalanced
#     brace inside a ps1 string literal confuses the depth counter (N6);
#     multi-line string literals are not modeled. These need a real
#     parser; the check targets accidental drift, and every ordinary
#     idiom is handled and mutation-tested.
#
# Usage: check-stack-refresh-optin.sh [file ...]
#   Defaults to scripts/start-stack.sh and scripts/start-stack.ps1.
set -euo pipefail

fail=0

check_sh() {
  awk '
    function wcount(s, re,   n, tmp) {
      tmp = s; n = 0
      while (match(tmp, re)) { n++; tmp = substr(tmp, RSTART + RLENGTH) }
      return n
    }
    {
      raw = $0
      if (in_heredoc) {
        stripped = raw; sub(/^[[:space:]]*/, "", stripped)
        if (stripped == hd_end) in_heredoc = 0
        next
      }
      # Comment must start the line or follow whitespace — $# and ${#var}
      # are parameter expansions, not comments.
      line = raw; sub(/(^|[[:space:]])#.*$/, "", line)
      # Here-strings and arithmetic are not heredocs; neutralize both
      # before opener detection so cat<<EOS (no space) still detects.
      hline = line; gsub(/<<</, " HERESTRING ", hline)
      gsub(/\$\(\([^)]*\)\)/, " ARITH ", hline)
      if (match(hline, /[[:space:]]*<<-?['\''"]?[A-Za-z_][A-Za-z_0-9]*/)) {
        hd_end = substr(hline, RSTART, RLENGTH)
        sub(/[[:space:]]*<<-?['\''"]?/, "", hd_end)
        in_heredoc = 1
        # the rest of this line still gets evaluated below
      }
      # Keyword counting runs on a string-stripped copy so "checking if x"
      # in a log message cannot inflate the nesting. Regexes as strings: a
      # /regex/ constant passed as a function arg degrades to a boolean.
      kline = line
      gsub(/"[^"]*"/, "\"\"", kline)
      gsub(/'\''[^'\'']*'\''/, "", kline)
      nif = wcount(kline, "(^|[;&|[:space:]])if([[:space:]]|$)")
      nfi = wcount(kline, "(^|[;[:space:]])fi([;[:space:]]|$)")
      here = in_guard
      closed = 0
      if (!in_guard && line ~ /if[[:space:]]+\[\[[[:space:]]+"\$\{STACK_REFRESH:-0\}"[[:space:]]+==[[:space:]]+"1"[[:space:]]+\]\]/) {
        here = 1
        depth = nif - nfi
        if (depth <= 0) closed = 1; else in_guard = 1
      } else if (in_guard) {
        depth += nif - nfi
        if (depth <= 0) { in_guard = 0; closed = 1 }
      }
      if (line ~ /--pull always|--force-recreate/) {
        # A line that closes the branch may still carry code AFTER the
        # closing fi — that segment is outside the branch.
        in_tail = 0
        if (closed) {
          tail = kline
          if (sub(/.*[;[:space:]]fi([;[:space:]]|$)/, "", tail) || sub(/^fi([;[:space:]]|$)/, "", tail)) {
            # tail is string-stripped; re-check the raw tail for flags by
            # aligning on the last fi in the original line instead.
            rtail = line
            if (!sub(/.*[;[:space:]]fi([;[:space:]]|$)/, "", rtail)) sub(/^fi([;[:space:]]|$)/, "", rtail)
            if (rtail ~ /--pull always|--force-recreate/) in_tail = 1
          }
        }
        if (!here || in_tail || line !~ /refresh_flags=/) {
          printf "::error file=%s,line=%d::forced-refresh flag outside the sanctioned STACK_REFRESH branch: %s\n", FILENAME, FNR, $0
          bad = 1
        }
      }
    }
    END {
      if (in_heredoc) {
        printf "::error file=%s::unterminated heredoc — check aborted early, refusing to pass\n", FILENAME
        bad = 1
      }
      exit bad
    }
  ' "$1"
}

check_ps1() {
  awk '
    { line = $0; sub(/#.*$/, "", line) }
    !in_guard && line ~ /if[[:space:]]*\(\$env:STACK_REFRESH[[:space:]]+-eq[[:space:]]+"1"\)[[:space:]]*\{/ {
      in_guard = 1
      depth = gsub(/\{/, "{", line) - gsub(/\}/, "}", line)
      if (depth <= 0) in_guard = 0
      next
    }
    in_guard {
      depth += gsub(/\{/, "{", line) - gsub(/\}/, "}", line)
      if (depth <= 0) { in_guard = 0 }
    }
    line ~ /--pull|--force-recreate/ {
      if (!in_guard || line !~ /\$refreshArgs[[:space:]]*=/) {
        printf "::error file=%s,line=%d::forced-refresh flag outside the sanctioned STACK_REFRESH branch: %s\n", FILENAME, FNR, $0
        bad = 1
      }
    }
    END { exit bad }
  ' "$1"
}

check_file() {
  local file=$1
  if [[ ! -f "$file" ]]; then
    echo "::error file=$file::start-stack script missing — refresh opt-in unverifiable"
    fail=1
    return
  fi
  case "$file" in
    *.ps1) check_ps1 "$file" || fail=1 ;;
    *)     check_sh "$file" || fail=1 ;;
  esac
}

files=("$@")
if [[ ${#files[@]} -eq 0 ]]; then
  files=(scripts/start-stack.sh scripts/start-stack.ps1)
fi
for f in "${files[@]}"; do
  check_file "$f"
done

if [[ $fail -ne 0 ]]; then
  echo "FAIL: forced-refresh flags must appear only as refresh-variable assignments inside the STACK_REFRESH opt-in branch."
  exit 1
fi
echo "OK: refresh flags are opt-in only in: ${files[*]}"
