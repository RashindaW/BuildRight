#!/usr/bin/env bash
# Manual HF Spaces sync helper for the continuous-improvement loop.
#
#   export HF_SPACE=<user>/<space>          # e.g. rashi/buildright
#   export HF_TOKEN=hf_xxx                   # a WRITE token (only needed for push)
#
#   ./scripts/hf.sh push     # deploy current branch  -> Space main (HF rebuilds)
#   ./scripts/hf.sh pull     # bring HF-side edits down into the current branch
#   ./scripts/hf.sh status   # show the configured remote
#
# Source of truth is your local/GitHub repo; HF is a deploy target. Pull from HF
# only to reconcile edits made in the HF web editor.
set -euo pipefail

: "${HF_SPACE:?Set HF_SPACE=<user>/<space>}"
AUTH=""
[ -n "${HF_TOKEN:-}" ] && AUTH="user:${HF_TOKEN}@"
REMOTE_URL="https://${AUTH}huggingface.co/spaces/${HF_SPACE}"

# (Re)point the 'space' remote without leaking the token into git config.
git remote remove space 2>/dev/null || true
git remote add space "https://huggingface.co/spaces/${HF_SPACE}"

case "${1:-}" in
  push)
    echo "Deploying $(git rev-parse --abbrev-ref HEAD) -> HF Space ${HF_SPACE} (main)…"
    git push "${REMOTE_URL}" HEAD:main
    echo "Done. HF is rebuilding: https://huggingface.co/spaces/${HF_SPACE}"
    ;;
  pull)
    echo "Pulling HF Space ${HF_SPACE} (main) into $(git rev-parse --abbrev-ref HEAD)…"
    git pull "${REMOTE_URL}" main
    ;;
  status)
    git remote -v | grep space || echo "no 'space' remote"
    ;;
  *)
    echo "usage: HF_SPACE=user/space ./scripts/hf.sh {push|pull|status}" >&2
    exit 2
    ;;
esac
