#!/bin/bash

THIS_DIR="$(dirname "$(realpath "${BASH_SOURCE[0]}")")"
RESUME_GENERATOR="${RESUME_GENERATOR:-resume-generator}"

for profile_path in "$THIS_DIR/profiles/"*.yml; do
  profile=$(basename "$profile_path" .yml)
  "$RESUME_GENERATOR" render \
    --home-dir "$THIS_DIR" \
    --profile "$profile" \
    --markdown \
    --html \
    "$THIS_DIR/output/$profile"
done
