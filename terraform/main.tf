provider "google" {
  project = var.project_id
  region  = var.region
}

resource "google_project_service" "apis" {
  for_each = toset(["storage.googleapis.com", "bigquery.googleapis.com"])
  service  = each.value
}

resource "google_storage_bucket" "raw" {
  name                        = "${var.project_id}-raw"
  location                    = var.region
  uniform_bucket_level_access = true
  force_destroy               = false
  depends_on                  = [google_project_service.apis]
}

resource "google_bigquery_dataset" "raw" {
  dataset_id = "raw"
  location   = var.region
  depends_on = [google_project_service.apis]
}

moved {
  from = google_project_service.storage
  to   = google_project_service.apis["storage.googleapis.com"]
}