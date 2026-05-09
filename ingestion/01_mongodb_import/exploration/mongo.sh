#!/bin/bash
ROOT_DIR="$(cd "$(dirname "$0")/../../.." && pwd)"
source "$ROOT_DIR/.env"
MONGO_URI="mongodb://${VM_EXTERNAL_IP}:27017/countly"
script="$1"
output="results/$(basename "$script" .js).txt"
mongosh "$MONGO_URI" "$script" > "$output"
echo "Saved to $output"
