resource "google_compute_instance" "vm" {
  name         = "glamira-vm"
  machine_type = "e2-standard-2"
  zone         = "${var.region}-a"
  tags         = ["glamira-vm"]
  allow_stopping_for_update = true
  boot_disk {
    initialize_params {
      image = "ubuntu-os-cloud/ubuntu-2204-lts"
      size  = 100
      type  = "pd-balanced"
    }
  }
  network_interface {
    subnetwork = google_compute_subnetwork.private.id
    access_config {}
  }
  service_account {
    email  = google_service_account.vm.email
    scopes = ["cloud-platform"]
  }
}