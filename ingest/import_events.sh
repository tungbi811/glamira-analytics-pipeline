#!/usr/bin/env bash
# Import the Glamira event dump (41M docs) from GCS into MongoDB.
# Safe to re-run: exits early if the collection is already complete.
#
# Usage (on the VM, from the repo root):
#   cp .env.example .env   # fill in values, once
#   bash ingest/import_events.sh
set -euo pipefail

# --- Load .env from the repo root, if present ----------------------
ENV_FILE="$(cd "$(dirname "$0")/.." && pwd)/.env"
if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck source=/dev/null
  source "$ENV_FILE"
  set +a
fi

# --- Config -------------------------------------------------------
ARCHIVE="glamira_ubl_2019.tar.gz"
DATA_DIR="$HOME/data"
DB="${MONGO_DB:-glamira}"
COLLECTION="summary"
EXPECTED_DOCS=41432473

: "${GCS_BUCKET:?Set GCS_BUCKET in .env}"
: "${MONGO_USER:?Set MONGO_USER in .env}"
: "${MONGO_PASSWORD:?Set MONGO_PASSWORD in .env}"

# --- Helpers ------------------------------------------------------
log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

count_docs() {
  mongosh --quiet \
    --username "$MONGO_USER" --password "$MONGO_PASSWORD" \
    --authenticationDatabase admin \
    --eval "db.getSiblingDB('$DB').getCollection('$COLLECTION').estimatedDocumentCount()"
}

# --- Step 0: already imported? ------------------------------------
count=$(count_docs)
if [[ "$count" -eq "$EXPECTED_DOCS" ]]; then
  log "$DB.$COLLECTION already has $count docs, nothing to do"
  exit 0
fi
log "$DB.$COLLECTION has $count docs, expected $EXPECTED_DOCS: importing"

# --- Step 1: download archive from GCS ----------------------------
mkdir -p "$DATA_DIR"

if [[ -f "$DATA_DIR/$ARCHIVE" ]]; then
  log "Archive already downloaded, skipping"
else
  log "Downloading $ARCHIVE"
  gcloud storage cp "$GCS_BUCKET/source/$ARCHIVE" "$DATA_DIR/"
fi

# --- Step 2: extract ----------------------------------------------
if [[ -d "$DATA_DIR/dump" ]]; then
  log "Dump already extracted, skipping"
else
  log "Extracting $ARCHIVE"
  tar -xzf "$DATA_DIR/$ARCHIVE" -C "$DATA_DIR"
fi

# --- Step 3: restore into MongoDB ---------------------------------
# Password goes in a temp config file so it doesn't show up in `ps`
# during the long-running restore. The trap deletes it on exit.
conf=$(mktemp)
trap 'rm -f "$conf"' EXIT
printf 'password: "%s"\n' "$MONGO_PASSWORD" > "$conf"

log "Restoring into $DB.$COLLECTION (takes 1-2 hours)"
mongorestore \
  --username "$MONGO_USER" --authenticationDatabase admin \
  --config "$conf" \
  --nsFrom "countly.summary" --nsTo "$DB.$COLLECTION" \
  --drop \
  "$DATA_DIR/dump/"

# --- Step 4: verify -----------------------------------------------
count=$(count_docs)
if [[ "$count" -ne "$EXPECTED_DOCS" ]]; then
  log "ERROR: expected $EXPECTED_DOCS docs, found $count"
  exit 1
fi
log "Verified: $count docs"

# --- Step 5: free disk --------------------------------------------
log "Removing extracted dump and archive (original stays in GCS)"
rm -rf "${DATA_DIR:?}/dump" "${DATA_DIR:?}/${ARCHIVE:?}"

log "Done"
