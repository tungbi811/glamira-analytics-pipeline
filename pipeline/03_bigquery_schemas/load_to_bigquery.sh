#!/bin/bash
DATASET="glamira_raw"
PROJECT="project-07d9073d-6ad1-4f38-99e"

# Create dataset if it doesn't exist
bq mk --dataset --location=US ${PROJECT}:${DATASET}

# Load ip_locations
bq load \
  --source_format=NEWLINE_DELIMITED_JSON \
  --autodetect \
  --replace \
  ${PROJECT}:${DATASET}.ip_locations \
  "gs://unigap/glamira-data/processed/ip_locations/*.jsonl"

# Load product_details
bq load \
  --source_format=NEWLINE_DELIMITED_JSON \
  --autodetect \
  --replace \
  ${PROJECT}:${DATASET}.product_details \
  "gs://unigap/glamira-data/processed/product_details/*.jsonl"