#!/usr/bin/env bash
# R-773: يطبّق قاعدة main على الخادم من tools/github/main_ruleset.json (المصدر الوحيد).
# ينشئها إن غابت، ويحدّثها بالاسم نفسه إن وُجدت. يتطلب gh مصادقًا بصلاحية إدارة المستودع.
set -euo pipefail
REPO="${1:-reeveero-tech/sovereign_ai}"
HERE="$(cd "$(dirname "$0")" && pwd)"
SPEC="$HERE/main_ruleset.json"
NAME="$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["name"])' "$SPEC")"
ID="$(gh api "repos/$REPO/rulesets" --jq ".[] | select(.name == \"$NAME\") | .id" | head -1)"
if [ -n "$ID" ]; then
  gh api -X PUT "repos/$REPO/rulesets/$ID" --input "$SPEC" --jq '.id|tostring + " updated"'
else
  gh api -X POST "repos/$REPO/rulesets" --input "$SPEC" --jq '.id|tostring + " created"'
fi
