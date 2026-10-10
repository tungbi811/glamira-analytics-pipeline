resource "google_compute_network" "vpc" {
  name                    = "glamira-vpc"
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "private" {
  name          = "glamira-subnet"
  ip_cidr_range = "10.10.0.0/24"
  region        = var.region
  network       = google_compute_network.vpc.id
}

resource "google_compute_firewall" "ssh_iap" {
  name          = "glamira-ssh-iap"
  network       = google_compute_network.vpc.name
  direction     = "INGRESS"
  source_ranges = ["35.235.240.0/20"]
  target_tags   = ["glamira-vm"]
  allow {
    protocol = "tcp"
    ports    = ["22"]
  }
}
