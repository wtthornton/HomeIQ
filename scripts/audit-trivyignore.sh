#!/usr/bin/env bash
# Audits .trivyignore against live Trivy scan data: any CVE/GHSA id that is
# both (a) listed in the ignorefile and (b) has a FixedVersion in at least
# one scanned image is fixable and must not be ignored. Prints each such id
# with the image(s) it is fixable in, one per line; exits 1 if any are
# found, 0 if the ignorefile is clean, 2 on a malformed run (empty image
# list, or any image scan producing no JSON).
set -euo pipefail

TRIVY_BIN="${TRIVY_BIN:-trivy}"
IGNOREFILE="${IGNOREFILE:-.trivyignore}"
IMAGES_FILE="${1:?usage: audit-trivyignore.sh <images-file>}"

if [[ ! -s "$IMAGES_FILE" ]]; then
    echo "audit-trivyignore: images file '$IMAGES_FILE' is empty" >&2
    exit 2
fi

workdir="$(mktemp -d)"
trap 'rm -rf "$workdir"' EXIT

fixable_file="$workdir/fixable.txt"
: > "$fixable_file"

scanned=0
total=0
while IFS= read -r img; do
    [[ -z "$img" ]] && continue
    total=$((total + 1))
    json="$workdir/$(echo "$img" | tr -c 'A-Za-z0-9' '_').json"
    if ! "$TRIVY_BIN" image --format json --severity CRITICAL,HIGH "$img" > "$json" 2>"$workdir/scan.err"; then
        echo "audit-trivyignore: scan failed for image '$img'" >&2
        cat "$workdir/scan.err" >&2
        exit 2
    fi
    if [[ ! -s "$json" ]]; then
        echo "audit-trivyignore: no JSON output for image '$img'" >&2
        exit 2
    fi
    jq -r --arg img "$img" '
        .Results[]?.Vulnerabilities[]?
        | select(.FixedVersion != "" and .FixedVersion != null)
        | [.VulnerabilityID, $img] | @tsv
    ' "$json" >> "$fixable_file"
    scanned=$((scanned + 1))
done < "$IMAGES_FILE"

if [[ "$scanned" -ne "$total" || "$scanned" -eq 0 ]]; then
    echo "audit-trivyignore: scanned $scanned of $total images" >&2
    exit 2
fi

ignored_ids="$workdir/ignored.txt"
grep -oE '^(CVE|GHSA)-[A-Za-z0-9-]+' "$IGNOREFILE" | sort -u > "$ignored_ids"

fixable_ids="$workdir/fixable_ids.txt"
cut -f1 "$fixable_file" | sort -u > "$fixable_ids"

hits="$workdir/hits.txt"
comm -12 "$fixable_ids" "$ignored_ids" > "$hits"

if [[ ! -s "$hits" ]]; then
    exit 0
fi

status=0
while IFS= read -r id; do
    imgs="$(awk -F'\t' -v id="$id" '$1 == id { print $2 }' "$fixable_file" | sort -u | paste -sd, -)"
    echo "${id} fixable-in: ${imgs}"
    status=1
done < "$hits"

exit "$status"
