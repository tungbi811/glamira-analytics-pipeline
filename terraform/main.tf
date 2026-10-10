provider "google" {
  project = var.project_id
  region  = var.region
}

resource "google_project_service" "apis" {
  for_each = toset([
    "storage.googleapis.com",
    "bigquery.googleapis.com",
    "compute.googleapis.com", # VMs, firewalls
    "iam.googleapis.com",     # service accounts
    "iap.googleapis.com"      # Identity-Aware Proxy
  ])
  service = each.value
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

resource "google_service_account" "vm" {
  account_id   = "glamira-vm"
  display_name = "Glamira VM"
  depends_on   = [google_project_service.apis]
}

resource "google_storage_bucket_iam_member" "vm_gcs_admin" {
  bucket = google_storage_bucket.raw.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.vm.email}"
}

resource "google_bigquery_dataset_iam_member" "vm_bq_editor" {
  dataset_id = google_bigquery_dataset.raw.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = "serviceAccount:${google_service_account.vm.email}"
}

resource "google_project_iam_member" "vm_bq_user" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.vm.email}"
}