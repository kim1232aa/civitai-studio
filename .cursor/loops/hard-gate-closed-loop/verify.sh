#!/usr/bin/env bash
# Exit 0 only when §3 closed-loop + §1.5 Seko paired evidence pack is complete.
# Canon: docs/00-IRON-RULES.md. Boss: reuse existing Seko baselines (no re-capture).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
BASE="$ROOT/docs/review-shots/closed-loop"
if [[ ! -d "$BASE" ]]; then
  echo "FAIL: missing $BASE"
  exit 1
fi

# §7: empty canvas / stamp-only / login does NOT count as Seko contrast
seko_is_valid_contrast() {
  local f="$1"
  local b
  b=$(basename "$f" | tr '[:upper:]' '[:lower:]')
  case "$b" in
    *empty*|*stamp*|*login*) return 1 ;;
  esac
  return 0
}

resolve_seko() {
  local dir="$1" m="$2"
  local p="$dir/seko-baseline-same-flow.png"
  if [[ -s "$p" ]] && seko_is_valid_contrast "$p"; then echo "$p"; return 0; fi
  local ref
  ref=$(grep -iE '^seko_baseline_path:' "$m" | head -1 | sed 's/^[^:]*:[[:space:]]*//' || true)
  if [[ -n "${ref:-}" ]]; then
    if [[ "$ref" != /* ]]; then ref="$ROOT/$ref"; fi
    if [[ -s "$ref" ]]; then
      if seko_is_valid_contrast "$ref"; then echo "$ref"; return 0; fi
      echo "FAIL: Seko baseline is empty/stamp/login (not §7 contrast): $ref" >&2
      return 1
    fi
  fi
  for hit in /workspace/docs/review-shots/s7-seko-03-composer.png \
             /workspace/docs/review-shots/s7-seko-06-writeback.png \
             /workspace/docs/review-shots/s7-seko-04-t2i.png \
             /workspace/docs/review-shots/s7-seko-02-card.png; do
    if [[ -s "$hit" ]] && seko_is_valid_contrast "$hit"; then echo "$hit"; return 0; fi
  done
  return 1
}

found=0
shopt -s nullglob
for dir in "$BASE"/*/; do
  [[ -d "$dir" ]] || continue
  base="$(basename "$dir")"
  [[ "$base" == _* ]] && continue
  m="$dir/MANIFEST.md"
  [[ -f "$m" ]] || continue

  need=(
    "provider:"
    "sample_id:"
    "job_id:"
    "original_prompt: yes"
    "curl_generate: no"
    "short_or_sfw_prompt: no"
    "writeback_original_card: yes"
    "hard_refresh_ok: yes"
    "seko_paired_contrast: yes"
  )
  ok=1
  for k in "${need[@]}"; do
    if ! grep -qiF "$k" "$m"; then
      echo "FAIL: $m missing declaration: $k"
      ok=0
    fi
  done

  for f in composer-mounted.png outbound-or-job.png card-after-gen.png card-after-hard-refresh.png local-contrast-same-flow.png; do
    p="$dir$f"
    if [[ ! -s "$p" ]]; then
      echo "FAIL: missing/empty shot $p"
      ok=0
    fi
  done

  if ! resolve_seko "$dir" "$m" >/dev/null; then
    echo "FAIL: missing/invalid Seko baseline (pack file, seko_baseline_path, or non-empty s7-seko-*.png)"
    ok=0
  fi

  if grep -qiE 'short_or_sfw_prompt:[[:space:]]*yes|curl_generate:[[:space:]]*yes|writeback_original_card:[[:space:]]*no|hard_refresh_ok:[[:space:]]*no|seko_paired_contrast:[[:space:]]*no' "$m"; then
    echo "FAIL: $m declares a disqualifying gate"
    ok=0
  fi

  if [[ -s "$dir/card-after-gen.png" && -s "$dir/card-after-hard-refresh.png" ]]; then
    h1=$(md5sum "$dir/card-after-gen.png" | awk '{print $1}')
    h2=$(md5sum "$dir/card-after-hard-refresh.png" | awk '{print $1}')
    if [[ "$h1" == "$h2" ]]; then
      echo "FAIL: card-after-gen.png and card-after-hard-refresh.png are identical (hard refresh not evidenced)"
      ok=0
    fi
  fi
  if [[ -s "$dir/composer-mounted.png" && -s "$dir/outbound-or-job.png" ]]; then
    h3=$(md5sum "$dir/composer-mounted.png" | awk '{print $1}')
    h4=$(md5sum "$dir/outbound-or-job.png" | awk '{print $1}')
    if [[ "$h3" == "$h4" ]]; then
      echo "FAIL: composer-mounted.png and outbound-or-job.png are identical (need distinct shots)"
      ok=0
    fi
  fi

  if [[ $ok -eq 1 ]]; then
    echo "PASS pack: $dir"
    found=1
  fi
done

if [[ $found -eq 0 ]]; then
  echo "FAIL: closed-loop count still 0 / no valid §3+§1.5 evidence pack"
  exit 1
fi
echo "OK: §3 closed loop + §1.5 Seko paired contrast verified"
exit 0
