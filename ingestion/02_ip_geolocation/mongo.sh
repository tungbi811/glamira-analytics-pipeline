#!/bin/bash
ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
source "$ROOT_DIR/.env"
mongosh "mongodb://${VM_EXTERNAL_IP}:27017/countly" "$1"
