#!/bin/bash

echo "=============================="
echo "  Glamira Data Download Start "
echo "=============================="

TAR_FILE="glamira_ubl_oct_nov_2019.tar.gz"
BIN_FILE="ip2location.bin"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
RAW_DIR="$PROJECT_ROOT/data/raw"

echo "Creating data directory at: $RAW_DIR"
mkdir -p "$RAW_DIR"

if [ -f "$RAW_DIR/$TAR_FILE" ]; then
    echo "Skipping $TAR_FILE — already exists"
else
    echo "Downloading $TAR_FILE from GCS..."
    gcloud storage cp "gs://unigap/glamira-data/raw/Glamira UBL Oct-Nov 2019.tar.gz" "$RAW_DIR/$TAR_FILE"
fi

if [ -f "$RAW_DIR/$BIN_FILE" ]; then
    echo "Skipping $BIN_FILE — already exists"
else
    echo "Downloading $BIN_FILE from GCS..."
    gcloud storage cp "gs://unigap/glamira-data/raw/IP Country Region City.BIN" "$RAW_DIR/$BIN_FILE"
fi

if [ -d "$RAW_DIR/dump" ]; then
    echo "Skipping extraction — dump folder already exists"
else
    echo "Extracting $TAR_FILE..."
    tar -xzf "$RAW_DIR/$TAR_FILE" -C "$RAW_DIR"
fi

echo "Importing into MongoDB..."
mongorestore "$RAW_DIR/dump/"

echo "Done!"