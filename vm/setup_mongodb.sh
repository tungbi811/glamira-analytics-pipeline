#!/usr/bin/env bash
# Install MongoDB on the VM, create users, and turn on authentication.
# Safe to re-run: each step checks whether it's already done.
#
# Usage (on the VM, from the repo root, as a normal user with sudo):
#   cp .env.example .env   # fill in values, once
#   bash vm/setup_mongodb.sh
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
MONGO_VERSION="8.0"
MONGO_DB="${MONGO_DB:-glamira}"
CONF="/etc/mongod.conf"

: "${MONGO_ADMIN_PASSWORD:?Set MONGO_ADMIN_PASSWORD in .env}"
: "${MONGO_USER:?Set MONGO_USER in .env}"
: "${MONGO_PASSWORD:?Set MONGO_PASSWORD in .env}"

# --- Helpers ------------------------------------------------------
log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

wait_for_mongod() {
  for _ in {1..30}; do
    mongosh --quiet --eval 'db.runCommand({ ping: 1 }).ok' >/dev/null 2>&1 && return 0
    sleep 1
  done
  log "ERROR: mongod did not start, see: sudo journalctl -u mongod -n 30"
  exit 1
}

# --- Step 0: kernel check -----------------------------------------
# MongoDB 8 crashes on kernel 6.19+ (SERVER-121912). Fail early with a clear message.
kernel=$(uname -r | cut -d. -f1,2)
if [[ "$(printf '%s\n' "$kernel" "6.19" | sort -V | head -1)" == "6.19" ]]; then
  log "ERROR: kernel $kernel is not supported by MongoDB $MONGO_VERSION, use Ubuntu 22.04"
  exit 1
fi

# --- Step 1: install ----------------------------------------------
if command -v mongod >/dev/null; then
  log "MongoDB already installed, skipping"
else
  log "Installing MongoDB $MONGO_VERSION"
  codename=$(lsb_release -cs)
  keyring="/usr/share/keyrings/mongodb-server-$MONGO_VERSION.gpg"

  sudo apt-get update -q
  sudo apt-get install -y -q gnupg curl
  curl -fsSL "https://www.mongodb.org/static/pgp/server-$MONGO_VERSION.asc" \
    | sudo gpg --dearmor --yes -o "$keyring"
  echo "deb [ arch=amd64,arm64 signed-by=$keyring ] https://repo.mongodb.org/apt/ubuntu $codename/mongodb-org/$MONGO_VERSION multiverse" \
    | sudo tee "/etc/apt/sources.list.d/mongodb-org-$MONGO_VERSION.list" >/dev/null
  sudo apt-get update -q
  sudo apt-get install -y -q mongodb-org
fi

# --- Step 2: start on boot ----------------------------------------
sudo systemctl enable --now mongod
wait_for_mongod
log "mongod is running"

# --- Step 3: users + auth -----------------------------------------
if grep -q '^  authorization: enabled' "$CONF"; then
  log "Authorization already enabled, skipping user setup"
else
  # Auth is still off, so we can create users without logging in.
  # mongosh reads passwords from process.env, so they never appear in `ps`.
  log "Creating users: admin, $MONGO_USER"
  mongosh --quiet --eval "
    const admin = db.getSiblingDB('admin');
    if (!admin.getUser('admin')) {
      admin.createUser({ user: 'admin', pwd: process.env.MONGO_ADMIN_PASSWORD, roles: ['userAdminAnyDatabase'] });
    }
    if (!admin.getUser(process.env.MONGO_USER)) {
      admin.createUser({ user: process.env.MONGO_USER, pwd: process.env.MONGO_PASSWORD,
                         roles: [{ role: 'readWrite', db: '$MONGO_DB' }] });
    }
  "

  log "Enabling authorization in $CONF"
  sudo sed -i 's/^#security:/security:\n  authorization: enabled/' "$CONF"
  sudo systemctl restart mongod
  wait_for_mongod
fi

# --- Step 4: verify -----------------------------------------------
mongosh --quiet \
  --username "$MONGO_USER" --password "$MONGO_PASSWORD" \
  --authenticationDatabase admin \
  --eval 'db.runCommand({ ping: 1 }).ok' >/dev/null
log "Verified: $MONGO_USER can log in"

log "Done"
