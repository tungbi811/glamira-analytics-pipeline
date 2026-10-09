provider "google" {
  project = var.project_id
  region  = var.region
}

resource "google_project_service" "storage" {
  service = "storage.googleapis.com"
}

resource "google_storage_bucket" "raw" {
  name                        = "${var.project_id}-raw"
  location                    = var.region
  uniform_bucket_level_access = true
  force_destroy               = false
  depends_on                  = [google_project_service.storage]
}